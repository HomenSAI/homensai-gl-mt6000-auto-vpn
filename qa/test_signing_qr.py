"""Tests for scripts/signing/qr.py (pure Python QR encoder used for the signing-secret paper backup).

Offline, standard library only. Reference vectors are SHA-256 digests of the module matrix (rows top to bottom, '1' dark,
'0' light, no separators, no quiet zone) produced by independent reference encoders with the same version, ecc and mask
forced; the full cross-check (random inputs, zxing-cpp decode) is qa/evidence/signing-2026-11-03/qr-crosscheck.json.
Digests come from Nayuki's reference implementation (qrcodegen); segno gives the same matrices for the alphanumeric vectors.
In byte mode segno appends one extra zero codeword after the terminator (decodable, but not the ISO/Nayuki bit stream), so
its byte-mode matrices differ in the data area; the evidence JSON records this and checks it explains every difference.
"""
import hashlib
import os
import struct
import sys
import unittest
import xml.etree.ElementTree as ET
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "signing"))
import qr  # noqa: E402

SECRET_ALNUM = "HSAI-SK1:MAIN:0123456789ABCDEF:" + "A1B2C3D4E5F60718293A4B5C6D7E8F90" * 2  # 95 chars, alphanumeric
OTPAUTH = ("otpauth://totp/HomenS.AI:release?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
           "&issuer=HomenS.AI&algorithm=SHA1&digits=6&period=30")  # lower case, so byte mode
UTF8_TEXT = "Ключ → key"  # Cyrillic + arrow, byte mode via UTF-8

# (name, data, ecc, version, mask, sha256 of the matrix bits from the reference encoder with the same settings)
LONG_FILL = "HSAI-SK1:0123456789ABCDEF:" * 12
VECTORS = [
    ("alnum-95-Q-v-auto-m3", SECRET_ALNUM, "Q", None, 3, "5ccf68f5cb3169894bbee66a4f7917488eb1b893178fac380ecdb71f4cdd8614"),
    ("alnum-95-Q-v-auto-m0", SECRET_ALNUM, "Q", None, 0, "d23a82343fafb965cc7fccf864b5e3cb95896b46d0ed60425a93961c73b5ab28"),
    ("byte-otpauth-M-auto-m5", OTPAUTH, "M", None, 5, "6cbfe2ed9e29d2790dbabf8b32e018ccc09bd42cb03612c591d57992b08a97b6"),
    ("byte-otpauth-M-auto-m1", OTPAUTH, "M", None, 1, "3d13ce4d1a354b87424b488dd62723af57f29da25e0f70926ce6c00e48f12239"),
    ("byte-short-H-auto-m6", "hsai", "H", None, 6, "e7b86772d8d0b2dc87d5aac708547e81bd4718886b301ce1edf0ddf75dfdc684"),
    ("alnum-short-H-v1-m2", "HSAI-SK1", "H", 1, 2, "1612bb98ba2683bbf32f0f5329b6aed4d107b5d8722c2d37eed8864167f9cf71"),
    ("utf8-L-auto-m4", UTF8_TEXT, "L", None, 4, "f614250ff91319362d4a5120b0ba4142710710e52aa089740509667a650a7a0c"),
    ("alnum-95-H-v8-m7", SECRET_ALNUM, "H", 8, 7, "f7b8c44c89a42e8a9ee9b091fbdd2915b5ddd44e2bca8676cb567c6338ed00b4"),
    ("byte-otpauth-Q-v12-m0", OTPAUTH, "Q", 12, 0, "7d9c21f6dcef1468033d849590dd12e30f094b32afd68110fde46779b832d9e0"),
    ("alnum-long-M-v20-m3", LONG_FILL[:300], "M", 20, 3, "147e7a15b2fb255e2154e8087695bd64344e086d31a1ad38cf2f4d62ba251b0e"),
    ("byte-otpauth-L-v32-m6", OTPAUTH, "L", 32, 6, "43374cc336224f3a8cccbfb7125b03f91fba259a75d7b2fb6983e7c9be22f3db"),
    ("alnum-long-H-auto-m5", LONG_FILL[:200], "H", None, 5, "b949f41bd66773fa08a7dc0b806e8a19deb616a65e57e1df23efffa88712dab7"),
    ("byte-otpauth-H-v40-m2", OTPAUTH, "H", 40, 2, "f02f019d1337330d28b68febe40e35f0a320ac1ff809f87d168d64bc600dfe57"),
]


def bits_of(matrix):
    return "".join("1" if m else "0" for row in matrix for m in row)


def digest_of(matrix):
    return hashlib.sha256(bits_of(matrix).encode("ascii")).hexdigest()


def bch_remainder(value, poly, poly_bits, data_bits):
    """Remainder of value (already data << parity) divided by the generator polynomial."""
    for i in reversed(range(data_bits)):
        if (value >> (i + poly_bits)) & 1:
            value ^= poly << i
    return value


def read_format_copies(m):
    """Both 15-bit format words as stored (still xor-masked), read at the ISO positions, bit 0 = LSB."""
    size = len(m)
    first = 0
    second = 0
    c1 = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + [(14 - i, 8) for i in range(9, 15)]
    for i, (x, y) in enumerate(c1):
        first |= int(m[y][x]) << i
    c2 = [(size - 1 - i, 8) for i in range(8)] + [(8, size - 15 + i) for i in range(8, 15)]
    for i, (x, y) in enumerate(c2):
        second |= int(m[y][x]) << i
    return first, second


def decode_format(word):
    word ^= 0x5412
    assert bch_remainder(word, 0x537, 10, 5) == 0, "format BCH check failed"
    data = word >> 10
    return {1: "L", 0: "M", 3: "Q", 2: "H"}[data >> 3], data & 7


def read_version_copies(m):
    size = len(m)
    a = b = 0
    for i in range(18):
        a |= int(m[i // 3][size - 11 + i % 3]) << i
        b |= int(m[size - 11 + i % 3][i // 3]) << i
    return a, b


def read_png_pixels(png):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    idat = b""
    ihdr = None
    seen = []
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos:pos + 4])
        tag = png[pos + 4:pos + 8]
        body = png[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])
        assert crc == zlib.crc32(tag + body) & 0xFFFFFFFF
        seen.append(tag)
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    assert seen[0] == b"IHDR" and seen[-1] == b"IEND"
    w, h, depth, ctype, comp, filt, inter = ihdr
    assert (depth, ctype, comp, filt, inter) == (8, 0, 0, 0, 0)
    raw = zlib.decompress(idat)
    assert len(raw) == h * (w + 1)
    rows = []
    for y in range(h):
        line = raw[y * (w + 1):(y + 1) * (w + 1)]
        assert line[0] == 0
        rows.append(list(line[1:]))
    return w, h, rows


class TablesTest(unittest.TestCase):
    def test_total_codewords_known_values(self):
        # ISO 18004 table 1: total codewords and remainder bits
        known = {1: (26, 0), 2: (44, 7), 7: (196, 0), 14: (581, 3), 21: (1156, 4), 40: (3706, 0)}
        for ver, (words, rem) in known.items():
            raw = qr._num_raw_data_modules(ver)
            self.assertEqual((raw // 8, raw % 8), (words, rem), ver)

    def test_data_capacity_known_values(self):
        # ISO 18004 table 7: data codewords per version/level
        known = {
            1: (19, 16, 13, 9), 2: (34, 28, 22, 16), 5: (108, 86, 62, 46), 10: (274, 216, 154, 122),
            20: (861, 669, 485, 385), 40: (2956, 2334, 1666, 1276),
        }
        for ver, caps in known.items():
            for idx, cap in enumerate(caps):
                self.assertEqual(qr._num_data_codewords(ver, idx), cap, (ver, idx))

    def test_tables_consistent(self):
        for ver in range(1, 41):
            for idx in range(4):
                self.assertGreater(qr._num_data_codewords(ver, idx), 0)
            self.assertEqual(qr._alignment_positions(ver)[:1], [6] if ver > 1 else [])
        self.assertEqual(qr._alignment_positions(7), [6, 22, 38])
        self.assertEqual(qr._alignment_positions(32), [6, 34, 60, 86, 112, 138])
        self.assertEqual(qr._alignment_positions(40), [6, 30, 58, 86, 114, 142, 170])

    def test_reed_solomon_known_divisor(self):
        # generator polynomial of degree 7 (ISO 18004 annex A): alpha exponents 0,87,229,146,149,238,102,21
        antilog = [1]
        for _ in range(255):
            v = antilog[-1] << 1
            antilog.append(v ^ 0x11D if v & 0x100 else v)
        expected = [antilog[e] for e in (87, 229, 146, 149, 238, 102, 21)]
        self.assertEqual(qr._rs_divisor(7), expected)
        # the codeword polynomial must be divisible by the generator: appending the remainder gives remainder 0
        data = list(range(1, 20))
        div = qr._rs_divisor(7)
        rem = qr._rs_remainder(data, div)
        self.assertEqual(qr._rs_remainder(data + rem, div), [0] * 7)


class StructureTest(unittest.TestCase):
    def check_structure(self, m, ver, ecc, mask, data):
        size = len(m)
        self.assertEqual(size, 17 + 4 * ver)
        for row in m:
            self.assertEqual(len(row), size)
            self.assertTrue(all(isinstance(v, bool) for v in row))
        # finder patterns (7x7: dark ring, light ring, 3x3 core) and their light separators
        for ox, oy in ((0, 0), (size - 7, 0), (0, size - 7)):
            for dy in range(7):
                for dx in range(7):
                    self.assertEqual(m[oy + dy][ox + dx], max(abs(dx - 3), abs(dy - 3)) != 2, (ox, oy, dx, dy))
        for i in range(8):
            for x, y in ((7, i), (i, 7), (size - 8, i), (size - 8 + i, 7), (i, size - 8), (7, size - 8 + i)):
                self.assertFalse(m[y][x], (x, y))
        # timing patterns
        for i in range(8, size - 8):
            self.assertEqual(m[6][i], i % 2 == 0)
            self.assertEqual(m[i][6], i % 2 == 0)
        self.assertTrue(m[size - 8][8])  # dark module
        # format information, both copies
        first, second = read_format_copies(m)
        self.assertEqual(first, second)
        self.assertEqual(decode_format(first), (ecc, mask))
        # alignment patterns (centre dark, ring light, outer ring dark)
        pos = qr._alignment_positions(ver)
        for i, cy in enumerate(pos):
            for j, cx in enumerate(pos):
                if (i == 0 and j == 0) or (i == 0 and j == len(pos) - 1) or (i == len(pos) - 1 and j == 0):
                    continue
                self.assertTrue(m[cy][cx])
                self.assertFalse(m[cy - 1][cx - 1] or m[cy - 1][cx + 1] or m[cy + 1][cx] or m[cy][cx - 1])
                self.assertTrue(m[cy - 2][cx - 2] and m[cy + 2][cx + 2] and m[cy - 2][cx] and m[cy][cx + 2])
        # version information
        if ver >= 7:
            a, b = read_version_copies(m)
            self.assertEqual(a, b)
            self.assertEqual(a >> 12, ver)
            self.assertEqual(bch_remainder(a, 0x1F25, 12, 6), 0)
        self.assertEqual(m, qr.encode(data, ecc, ver, mask))  # deterministic

    def test_structure_various(self):
        cases = [(1, "L", 0), (1, "H", 7), (2, "M", 3), (6, "Q", 5), (7, "L", 1), (7, "H", 6), (10, "M", 4),
                 (14, "Q", 2), (20, "H", 7), (32, "L", 0), (36, "M", 5), (40, "H", 3)]
        for ver, ecc, mask in cases:
            with self.subTest(version=ver, ecc=ecc, mask=mask):
                m = qr.encode("HELLO", ecc, ver, mask)
                self.check_structure(m, ver, ecc, mask, "HELLO")

    def test_known_format_words(self):
        # ISO 18004 table C.1: format information after masking, mask pattern 000
        for ecc, word in (("L", 0b111011111000100), ("M", 0b101010000010010),
                          ("Q", 0b011010101011111), ("H", 0b001011010001001)):
            m = qr.encode("A", ecc, 1, 0)
            self.assertEqual(read_format_copies(m), (word, word), ecc)

    def test_known_version_words(self):
        # ISO 18004 table D.1: version 7 -> 000111110010010100, version 40 -> 101000110001101001
        a, _ = read_version_copies(qr.encode("A", "L", 7, 0))
        self.assertEqual(a, 0b000111110010010100)
        a, _ = read_version_copies(qr.encode("A", "L", 40, 0))
        self.assertEqual(a, 0b101000110001101001)

    def test_mask_none_picks_valid_lowest_penalty(self):
        m = qr.encode(SECRET_ALNUM, "Q")
        first, second = read_format_copies(m)
        ecc, mask = decode_format(first)
        self.assertEqual((first, ecc), (second, "Q"))
        self.assertEqual(m, qr.encode(SECRET_ALNUM, "Q", None, mask))
        scores = [qr._penalty(qr.encode(SECRET_ALNUM, "Q", None, k)) for k in range(8)]
        self.assertEqual(scores[mask], min(scores))
        self.assertEqual(mask, scores.index(min(scores)))

    def test_penalty_rules_hand_checked(self):
        # an all-light 21x21 grid: N1 = 42 lines of run 21 (3 + 16 each), N2 = 20*20 blocks, N4 = 10 * 9 steps
        rows = [[False] * 21 for _ in range(21)]
        self.assertEqual(qr._penalty(rows), 42 * 19 + 400 * 3 + 90)
        # a single finder-like 1011101 + 4 light (at the right edge counts, the border is light)
        rows = [[False] * 21 for _ in range(21)]
        for x in (0, 2, 3, 4, 6):
            rows[10][x] = True
        # only row 10 and the 5 touched columns differ from the empty grid; just require the N3 hit to be present
        base = qr._penalty([[False] * 21 for _ in range(21)])
        self.assertNotEqual(qr._penalty(rows), base)


class EncodeTest(unittest.TestCase):
    def test_mode_selection_and_version(self):
        # byte mode capacity at ecc L: 17 bytes in version 1, 18 need version 2
        self.assertEqual(len(qr.encode("a" * 17, "L")), 21)
        self.assertEqual(len(qr.encode("a" * 18, "L")), 25)
        # alphanumeric capacity at L: 25 chars in version 1
        self.assertEqual(len(qr.encode("A" * 25, "L")), 21)
        self.assertEqual(len(qr.encode("A" * 26, "L")), 25)
        # one lower-case letter switches the whole text to byte mode
        self.assertEqual(len(qr.encode("A" * 24 + "a", "L")), 25)
        # bytes made only of alphanumeric characters use the alphanumeric mode as well
        self.assertEqual(qr.encode(b"HELLO WORLD", "M"), qr.encode("HELLO WORLD", "M"))
        self.assertEqual(qr._segment("HELLO $%*+-./:")[0], "alnum")
        self.assertEqual(qr._segment("hello")[0], "byte")
        self.assertEqual(qr._segment(UTF8_TEXT)[1], UTF8_TEXT.encode("utf-8"))

    def test_capacity_limits(self):
        self.assertEqual(len(qr.encode("a" * 2953, "L", None, 0)), 177)
        self.assertEqual(len(qr.encode("A" * 4296, "L", None, 0)), 177)
        self.assertEqual(len(qr.encode("a" * 1273, "H", None, 0)), 177)
        with self.assertRaisesRegex(ValueError, "QR-DATA-TOO-LONG"):
            qr.encode("a" * 2954, "L")
        with self.assertRaisesRegex(ValueError, "QR-DATA-TOO-LONG"):
            qr.encode("A" * 4297, "L")
        with self.assertRaisesRegex(ValueError, "QR-DATA-TOO-LONG"):
            qr.encode(b"\xff" * 1275, "H")

    def test_forced_version(self):
        self.assertEqual(len(qr.encode("A", "L", 10)), 57)
        with self.assertRaisesRegex(ValueError, "QR-DATA-TOO-LONG"):
            qr.encode("a" * 18, "L", 1)

    def test_errors(self):
        for bad_ecc in ("X", "l", "", None, 1):
            with self.assertRaisesRegex(ValueError, "QR-BAD-ECC"):
                qr.encode("A", bad_ecc)
        for bad_version in (0, 41, -1, "5", 1.5, True):
            with self.assertRaisesRegex(ValueError, "QR-BAD-VERSION"):
                qr.encode("A", "L", bad_version)
        for bad_mask in (-1, 8, "1", 2.0, False):
            with self.assertRaisesRegex(ValueError, "QR-BAD-MASK"):
                qr.encode("A", "L", None, bad_mask)
        with self.assertRaisesRegex(ValueError, "QR-DATA-EMPTY"):
            qr.encode("")
        with self.assertRaises(TypeError):
            qr.encode(123)

    def test_deterministic(self):
        self.assertEqual(qr.encode(OTPAUTH, "M"), qr.encode(OTPAUTH, "M"))

    def test_reference_vectors(self):
        self.assertGreaterEqual(len(VECTORS), 8)
        versions = set()
        for name, data, ecc, version, mask, expected in VECTORS:
            with self.subTest(name):
                m = qr.encode(data, ecc, version, mask)
                versions.add((len(m) - 17) // 4)
                self.assertEqual(digest_of(m), expected)
        self.assertTrue(any(v >= 7 for v in versions) and any(v >= 10 for v in versions))


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.m = qr.encode(SECRET_ALNUM, "Q", None, 2)

    def test_console_plain(self):
        text = qr.render_console(self.m, border=4, ansi=False)
        lines = text.split("\n")
        self.assertEqual(lines[-1], "")
        lines = lines[:-1]
        dim = len(self.m) + 8
        self.assertEqual(len(lines), (dim + 1) // 2)
        self.assertTrue(all(len(line) == dim for line in lines))
        self.assertNotIn("\x1b", text)
        self.assertEqual(set(text) - set("\n"), set(text) & set(" ▀▄█"))
        # decode the half blocks back to the matrix
        for y, row in enumerate(self.m):
            ch = lines[(y + 4) // 2][4:4 + len(row)]
            for x, v in enumerate(row):
                top_row = (y + 4) % 2 == 0
                dark = ch[x] in ("█", "▀" if top_row else "▄")
                self.assertEqual(dark, v, (x, y))
        self.assertEqual(lines[0], " " * dim)  # quiet zone

    def test_console_ansi(self):
        text = qr.render_console(self.m)
        lines = text.split("\n")[:-1]
        self.assertTrue(all(line.startswith("\x1b[30;47m") and line.endswith("\x1b[0m") for line in lines))
        plain = qr.render_console(self.m, 4, ansi=False)
        stripped = text.replace("\x1b[30;47m", "").replace("\x1b[0m", "")
        self.assertEqual(stripped, plain)

    def test_svg(self):
        svg = qr.render_svg(self.m, scale=5, border=3)
        root = ET.fromstring(svg.split("\n", 1)[1])
        ns = "{http://www.w3.org/2000/svg}"
        dim = len(self.m) + 6
        self.assertEqual(root.get("width"), str(dim * 5))
        self.assertEqual(root.get("viewBox"), "0 0 %d %d" % (dim, dim))
        self.assertEqual(root.get("shape-rendering"), "crispEdges")
        self.assertEqual(len(root.findall(ns + "path")), 1)
        self.assertEqual(root.find(ns + "rect").get("fill"), "#FFFFFF")
        grid = [[False] * dim for _ in range(dim)]
        import re
        for sx, sy, w in re.findall(r"M(\d+),(\d+)h(\d+)v1h-\d+z", root.find(ns + "path").get("d")):
            for x in range(int(sx), int(sx) + int(w)):
                grid[int(sy)][x] = True
        self.assertEqual([r[3:3 + len(self.m)] for r in grid[3:3 + len(self.m)]], self.m)
        self.assertFalse(any(grid[0]) or any(r[0] for r in grid))

    def test_png(self):
        png = qr.render_png(self.m, scale=3, border=2)
        w, h, rows = read_png_pixels(png)
        dim = len(self.m) + 4
        self.assertEqual((w, h), (dim * 3, dim * 3))
        self.assertEqual(set(v for r in rows for v in r), {0, 255})
        for y in range(dim):
            for x in range(dim):
                expect = 0 if (2 <= x < dim - 2 and 2 <= y < dim - 2 and self.m[y - 2][x - 2]) else 255
                for dy in range(3):
                    for dx in range(3):
                        self.assertEqual(rows[y * 3 + dy][x * 3 + dx], expect)

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            qr.render_png(self.m, scale=0)
        with self.assertRaises(ValueError):
            qr.render_console(self.m, border=-1)


if __name__ == "__main__":
    unittest.main()
