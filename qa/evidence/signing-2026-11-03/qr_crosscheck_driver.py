"""Cross-check driver for scripts/signing/qr.py against two independent encoders and one independent decoder:
qrcodegen (Nayuki's reference implementation, PyPI), segno, and zxing-cpp (decoder).

Run inside a throwaway container with the worktree mounted read-only (see "how_run" in qr-crosscheck.json):
  pip install segno qrcodegen zxing-cpp pillow
  python qr_crosscheck_driver.py WORKTREE OUT.json                    # full run, writes the evidence JSON
  python qr_crosscheck_driver.py WORKTREE - --print-vectors           # prints reference SHA-256 for the test VECTORS

(a) matrix equality for random inputs, ecc levels, versions 1..40 and all 8 masks, with version and mask forced, and again
    with the version left automatic (smallest version must be the same);
(b) mask=None: our automatic choice must equal the references forced to that mask and have the lowest penalty; whether it is
    the same mask the references pick on their own is only recorded (several masks are valid);
(c) render_png decoded by zxing-cpp must return exactly the encoded text/bytes.

segno quirk found by this check: its encoder appends one extra all-zero codeword after the terminator whenever the
terminator ends exactly on a byte boundary, which is always the case in byte mode (4 + 8k bits + 4 terminator bits). The
symbol stays decodable but its bit stream is not the ISO/Nayuki/zxing one. qrcodegen is therefore the exact reference, and
segno is checked both strictly and against an emulation of that quirk (qr._build_codewords wrapped to add the zero
codeword); a segno difference that the quirk does not explain counts as a mismatch.
"""
import hashlib
import io
import json
import os
import random
import sys

worktree = sys.argv[1]
sys.path.insert(0, os.path.join(worktree, "scripts", "signing"))
sys.path.insert(0, os.path.join(worktree, "qa"))
import qr  # noqa: E402
import qrcodegen  # noqa: E402
import segno  # noqa: E402

SEED = 20261103
ECCS = "LMQH"
BYTE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789:/?=&._-@ ABCDEFéЖ中€"
print_vectors = "--print-vectors" in sys.argv
DIV = int(os.environ.get("QR_QUICK_DIV", "1"))  # >1 only for quick smoke runs; the evidence run uses 1


def bits_hash(rows):
    return hashlib.sha256("".join("1" if m else "0" for row in rows for m in row).encode("ascii")).hexdigest()


def seg_mode(data):
    return "alphanumeric" if qr._segment(data)[0] == "alnum" else "byte"


def segno_matrix(data, mode, ecc, version, mask):
    kw = dict(error=ecc, version=version, mask=mask, micro=False, boost_error=False, mode=mode)
    if mode == "byte":
        kw["encoding"] = "utf-8"
    code = segno.make(data, **kw)
    return [[bool(v) for v in row] for row in code.matrix], code


def nayuki_matrix(data, ecc, version, mask):
    """Matrix from Nayuki's reference implementation, same mode rule, no ECC boosting."""
    q = qrcodegen.QrCode
    level = {"L": q.Ecc.LOW, "M": q.Ecc.MEDIUM, "Q": q.Ecc.QUARTILE, "H": q.Ecc.HIGH}[ecc]
    if isinstance(data, str) and qr._segment(data)[0] == "alnum":
        seg = qrcodegen.QrSegment.make_alphanumeric(data)
    else:
        seg = qrcodegen.QrSegment.make_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    lo, hi = (1, 40) if version is None else (version, version)
    code = q.encode_segments([seg], level, lo, hi, -1 if mask is None else mask, False)
    size = code.get_size()
    return [[code.get_module(x, y) for x in range(size)] for y in range(size)], code


_strict_build = qr._build_codewords


def _segno_quirk_build(bits, capacity_bits):
    """Emulation of segno: after the terminator add 8 - len % 8 zero bits (a whole zero codeword when already aligned)."""
    bits = list(bits)
    bits.extend([0] * min(4, capacity_bits - len(bits)))
    if len(bits) < capacity_bits:
        bits.extend([0] * (8 - len(bits) % 8))
    bits = bits[:capacity_bits]
    out = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    while len(out) * 8 < capacity_bits:
        out.append((0xEC, 0x11)[(len(out) - len(bits) // 8) & 1])
    return out


def encode_segno_quirk(data, ecc, version, mask):
    qr._build_codewords = _segno_quirk_build
    try:
        return qr.encode(data, ecc, version, mask)
    finally:
        qr._build_codewords = _strict_build


class Tally:
    """Compare cases against both references and keep the counters."""

    def __init__(self, mismatches):
        self.mismatches = mismatches
        self.n = self.nayuki_equal = self.segno_equal = self.segno_quirk_equal = 0

    def check(self, kind, data, ecc, version, mask, ours):
        self.n += 1
        ref, ref_code = nayuki_matrix(data, ecc, version, mask)
        if ours == ref:
            self.nayuki_equal += 1
        else:
            self.mismatches.append({"kind": kind + "/qrcodegen", "data": data, "ecc": ecc, "version": version, "mask": mask})
        theirs, code = segno_matrix(data, seg_mode(data), ecc, version, mask)
        if theirs == ours:
            self.segno_equal += 1
        elif theirs == encode_segno_quirk(data, ecc, version, mask):
            self.segno_quirk_equal += 1
        else:
            self.mismatches.append({"kind": kind + "/segno-unexplained", "data": data, "ecc": ecc, "version": version, "mask": mask})
        return ref_code, code

    def summary(self):
        return {"cases": self.n, "equal_to_qrcodegen": self.nayuki_equal, "equal_to_segno_strict": self.segno_equal,
                "equal_to_segno_with_extra_zero_codeword_quirk": self.segno_quirk_equal}


def fits(data, ecc, version):
    try:
        qr.encode(data, ecc, version, 0)
        return True
    except ValueError:
        return False


def random_data(rng, kind, max_units):
    n = rng.randint(1, max(1, max_units))
    if kind == "alnum":
        return "".join(rng.choice(qr.ALPHANUMERIC) for _ in range(n))
    if kind == "ascii":
        return "".join(rng.choice(BYTE_ALPHABET[:44]) for _ in range(n))
    return "".join(rng.choice(BYTE_ALPHABET) for _ in range(n))  # includes multi-byte UTF-8


def fixed_vectors(mismatches, report):
    import test_signing_qr as t
    out = []
    for name, data, ecc, version, mask, expected in t.VECTORS:
        ref, _ = nayuki_matrix(data, ecc, version, mask)
        seg, _ = segno_matrix(data, seg_mode(data), ecc, version, mask)
        ours = qr.encode(data, ecc, version, mask)
        row = {"name": name, "qrcodegen_sha256": bits_hash(ref), "segno_sha256": bits_hash(seg), "ours_sha256": bits_hash(ours),
               "embedded_in_test": expected, "segno_equal": seg == ours,
               "segno_equal_with_quirk": seg == encode_segno_quirk(data, ecc, version, mask)}
        row["ok"] = ours == ref and bits_hash(ref) == expected and (row["segno_equal"] or row["segno_equal_with_quirk"])
        out.append(row)
        if print_vectors:
            print(name, bits_hash(ref), "segno_equal=%s" % row["segno_equal"])
        elif not row["ok"]:
            mismatches.append({"kind": "vector", "name": name})
    report["fixed_vectors"] = out


def main():
    import zxingcpp
    import PIL
    from PIL import Image
    rng = random.Random(SEED)
    mismatches = []
    report = {"seed": SEED}
    fixed_vectors(mismatches, report)
    if print_vectors:
        return

    # (a) forced version + forced mask, plus automatic version
    forced, auto_ver = Tally(mismatches), Tally(mismatches)
    by_mode = {"alphanumeric": 0, "byte-ascii": 0, "byte-utf8": 0}
    by_ecc = {e: 0 for e in ECCS}
    by_version = {}
    by_mask = {k: 0 for k in range(8)}
    for i in range(1400 // DIV):
        ver = rng.randint(1, 20) if i < 1100 // DIV else rng.randint(21, 40)
        ecc, mask = rng.choice(ECCS), rng.randint(0, 7)
        kind = rng.choice(("alnum", "ascii", "utf8"))
        if i < 64:  # make sure every ecc x mask corner is touched at low versions
            ecc, mask, ver = ECCS[i % 4], i // 4 % 8, 1 + i % 20
        cap = qr._num_data_codewords(ver, qr._ECC_INDEX[ecc]) * (1.6 if kind == "alnum" else 1.0)
        data = random_data(rng, kind, int(cap))
        while not fits(data, ecc, ver) and len(data) > 1:
            data = data[:max(1, len(data) - max(1, len(data) // 8))]
        forced.check("forced", data, ecc, ver, mask, qr.encode(data, ecc, ver, mask))
        label = "alphanumeric" if seg_mode(data) == "alphanumeric" else ("byte-ascii" if data.isascii() else "byte-utf8")
        by_mode[label] += 1
        by_ecc[ecc] += 1
        by_version[ver] = by_version.get(ver, 0) + 1
        by_mask[mask] += 1
        ours = qr.encode(data, ecc, None, mask)  # version left to the encoders: smallest fitting version
        _, code = auto_ver.check("auto-version", data, ecc, None, mask, ours)
        if len(ours) != 17 + 4 * code.version:
            mismatches.append({"kind": "auto-version/size", "data": data, "ecc": ecc})
    report["a_forced_version_and_mask"] = dict(forced.summary(), by_mode=by_mode, by_ecc=by_ecc, by_mask=by_mask,
                                               versions_covered=sorted(by_version),
                                               cases_per_version={str(k): by_version[k] for k in sorted(by_version)})
    report["a_smallest_version"] = auto_ver.summary()

    # (b) automatic mask
    tally_b = Tally(mismatches)
    same_nayuki = same_segno = 0
    for i in range(500 // DIV):
        ecc = rng.choice(ECCS)
        data = random_data(rng, rng.choice(("alnum", "ascii", "utf8")), rng.choice((10, 40, 120, 400)))
        if not fits(data, ecc, None):
            data = data[:60]
        ours = qr.encode(data, ecc)
        scores = [qr._penalty(qr.encode(data, ecc, None, k)) for k in range(8)]
        mask = scores.index(min(scores))
        tally_b.check("auto-mask", data, ecc, None, mask, ours)
        if ours != qr.encode(data, ecc, None, mask):
            mismatches.append({"kind": "auto-mask/not-lowest-penalty", "data": data, "ecc": ecc})
        same_nayuki += int(nayuki_matrix(data, ecc, None, None)[0] == ours)
        same_segno += int(segno_matrix(data, seg_mode(data), ecc, None, None)[1].mask == mask)
    report["b_auto_mask"] = dict(tally_b.summary(), same_mask_as_qrcodegen_own_choice=same_nayuki,
                                 same_mask_as_segno_own_choice=same_segno,
                                 note="other choices are still valid codes: equal to the references forced to that mask and lowest by our penalty")

    # (c) decode PNG output with zxing-cpp
    decoded_by_ecc = {e: 0 for e in ECCS}
    versions_c = set()
    cases_c = 0
    secret_like = ["HSAI-SK1:MAIN:%s:%s" % (os.urandom(8).hex().upper(), os.urandom(32).hex().upper()) for _ in range(20)]
    for i in range(500 // DIV):
        ecc = rng.choice(ECCS)
        if i < len(secret_like):
            data = secret_like[i]
        elif i < len(secret_like) + 12:  # a few large symbols (versions up to 40)
            ecc = "L"
            data = bytes(rng.randrange(256) for _ in range(rng.choice((700, 1200, 2000, 2900))))
        else:
            kind = rng.choice(("alnum", "ascii", "utf8", "bytes"))
            if kind == "bytes":
                data = bytes(rng.randrange(256) for _ in range(rng.randint(1, 120)))
            else:
                data = random_data(rng, kind, rng.choice((8, 30, 100, 300, 600)))
        m = qr.encode(data, ecc, None, None if i % 3 else rng.randint(0, 7))
        img = Image.open(io.BytesIO(qr.render_png(m, scale=6 if len(m) < 100 else 4, border=4)))
        assert img.mode == "L"
        res = zxingcpp.read_barcodes(img)
        raw = data if isinstance(data, bytes) else data.encode("utf-8")
        ok = len(res) == 1 and bytes(res[0].bytes) == raw and res[0].format == zxingcpp.BarcodeFormat.QRCode
        if ok and isinstance(data, str):
            ok = res[0].text == data
        if ok:
            decoded_by_ecc[ecc] += 1
        else:
            mismatches.append({"kind": "decode", "data": data if isinstance(data, str) else data.hex(), "ecc": ecc,
                               "got": [r.text for r in res]})
        cases_c += 1
        versions_c.add((len(m) - 17) // 4)
    report["c_zxing_png_roundtrip"] = {"cases": cases_c, "exact_roundtrips": sum(decoded_by_ecc.values()),
                                       "by_ecc": decoded_by_ecc, "versions_covered": sorted(versions_c),
                                       "secret_shaped_inputs": len(secret_like)}

    report["mismatches"] = len(mismatches)
    report["mismatch_details"] = mismatches[:20]
    report["segno_quirk"] = ("segno appends an extra all-zero codeword after the terminator when the terminator ends on a byte "
                             "boundary (always in byte mode); decodable but not the ISO/Nayuki/zxing bit stream; qrcodegen is the "
                             "exact reference and segno is accepted only if equal strictly or equal under that emulated quirk")
    try:
        import importlib.metadata as md
        tools = {n: md.version(n) for n in ("segno", "qrcodegen", "zxing-cpp", "pillow")}
    except Exception:  # pragma: no cover
        tools = {"segno": getattr(segno, "__version__", None), "pillow": PIL.__version__}
    tools.update(python=sys.version.split()[0], image=os.environ.get("QR_IMAGE", ""))
    report["tools"] = tools
    report["how_run"] = ("docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v WORKTREE:/work:ro -v OUT:/out python:3.12-slim sh -c "
                         "'pip install segno qrcodegen zxing-cpp pillow && python -I /work/qa/evidence/signing-2026-11-03/"
                         "qr_crosscheck_driver.py /work /out/qr-crosscheck.json'")
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("fixed_vectors", "how_run")}, indent=1, ensure_ascii=False)[:3500])
    sys.exit(1 if mismatches else 0)


main()
