"""QR Code (ISO/IEC 18004 Model 2) encoder and renderers, pure Python 3.9+ standard library.

Used to show a release-signing SECRET as a QR code for a paper backup or a password-manager scan, so it must be exact:
the structure follows the well-known reference algorithm by Nayuki (raw data modules, per-version ECC tables, Reed-Solomon
over GF(256)/0x11D, block interleaving, zigzag placement, BCH format/version bits), and the output is cross-checked
module for module against the independent `segno` encoder and decoded with `zxing-cpp`
(qa/evidence/signing-2026-11-03/qr-crosscheck.json). Not constant time and not hardened against side channels: it runs
only on the owner's PC to draw a code on screen or on paper.

Scope: versions 1..40, ECC levels L/M/Q/H, alphanumeric mode (0-9 A-Z space $ % * + - . / :) when every character
qualifies, otherwise byte mode (UTF-8 for str; bytes made only of those characters also use alphanumeric mode, empty data
is refused). No numeric/kanji/ECI/structured-append/Micro QR, and no automatic ECC
boosting: the requested level is always the level used.

encode(data, ecc='M', version=None, mask=None) returns rows of bool, True = dark module, without the quiet zone.
Automatic mask choice scores the eight masks with the four ISO penalty rules (runs of 5+, 2x2 blocks, strict 1:1:3:1:1
finder-like patterns with 4 light modules on one side, dark/light balance) and takes the lowest score, first wins on tie.
"""
import itertools
import struct
import zlib

ALPHANUMERIC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"
_ALNUM_INDEX = {c: i for i, c in enumerate(ALPHANUMERIC)}

# Format-info code of each ECC level (2 bits) and index into the tables below.
_ECC_FORMAT = {"L": 1, "M": 0, "Q": 3, "H": 2}
_ECC_INDEX = {"L": 0, "M": 1, "Q": 2, "H": 3}

# Index 0 of each row is padding for "version 0" (invalid).
_ECC_CODEWORDS_PER_BLOCK = (
    (None, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (None, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    (None, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (None, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
)
_NUM_ERROR_CORRECTION_BLOCKS = (
    (None, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    (None, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    (None, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    (None, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
)

# Penalty weights of ISO 18004 section 7.8.3.
_N1, _N2, _N3, _N4 = 3, 3, 40, 10
_PAD_BYTES = (0xEC, 0x11)


def _num_raw_data_modules(ver):
    """Data + ECC modules of a version (all modules minus function patterns), remainder bits included."""
    result = (16 * ver + 128) * ver + 64
    if ver >= 2:
        num_align = ver // 7 + 2
        result -= (25 * num_align - 10) * num_align - 55
        if ver >= 7:
            result -= 36
    return result


def _num_data_codewords(ver, ecc_index):
    return (_num_raw_data_modules(ver) // 8
            - _ECC_CODEWORDS_PER_BLOCK[ecc_index][ver] * _NUM_ERROR_CORRECTION_BLOCKS[ecc_index][ver])


def _alignment_positions(ver):
    if ver == 1:
        return []
    num_align = ver // 7 + 2
    step = 26 if ver == 32 else (ver * 4 + num_align * 2 + 1) // (num_align * 2 - 2) * 2
    result = [ver * 4 + 10 - i * step for i in range(num_align - 1)] + [6]  # size - 7 downwards, then the fixed 6
    result.reverse()
    return result


def _char_count_bits(mode, ver):
    table = {"alnum": (9, 11, 13), "byte": (8, 16, 16)}[mode]
    return table[(ver + 7) // 17]  # 1-9, 10-26, 27-40


def _get_bit(x, i):
    return (x >> i) & 1


# ---- Reed-Solomon over GF(2^8) with polynomial 0x11D ---------------------------------------------------------------

def _gf_multiply(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


# Log/antilog tables built from the bitwise multiply above (generator 2); only used to speed up long messages.
_EXP = [1] * 510
for _i in range(1, 255):
    _EXP[_i] = _gf_multiply(_EXP[_i - 1], 2)
for _i in range(255, 510):
    _EXP[_i] = _EXP[_i - 255]
_LOG = [0] * 256
for _i in range(255):
    _LOG[_EXP[_i]] = _i


def _rs_divisor(degree):
    """Coefficients (highest term first, leading 1 omitted) of prod (x - 2^i), i = 0..degree-1."""
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_multiply(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_multiply(root, 0x02)
    return result


def _rs_remainder(data, divisor):
    result = [0] * len(divisor)
    log_div = [(_LOG[c] if c else -1) for c in divisor]
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        if factor:
            lf = _LOG[factor]
            for i, ld in enumerate(log_div):
                if ld >= 0:
                    result[i] ^= _EXP[ld + lf]
    return result


# ---- data bit stream -----------------------------------------------------------------------------------------------

def _segment(data):
    """Return (mode, payload, character count). Alphanumeric when every character qualifies, else byte mode."""
    if isinstance(data, str):
        if data and all(c in _ALNUM_INDEX for c in data):
            return "alnum", data, len(data)
        raw = data.encode("utf-8")
    elif isinstance(data, (bytes, bytearray, memoryview)):
        raw = bytes(data)
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            text = ""
        if text and all(c in _ALNUM_INDEX for c in text):
            return "alnum", text, len(text)
    else:
        raise TypeError("QR-DATA-TYPE: data must be str or bytes")
    return "byte", raw, len(raw)


def _segment_bits(mode, payload, count, ver):
    """Bit list of one segment: mode indicator, character count, data."""
    bits = []

    def put(value, length):
        bits.extend((value >> i) & 1 for i in reversed(range(length)))

    cc_bits = _char_count_bits(mode, ver)
    if count >= (1 << cc_bits):
        return None
    if mode == "byte":
        put(0x4, 4)
        put(count, cc_bits)
        for b in payload:
            put(b, 8)
    else:
        put(0x2, 4)
        put(count, cc_bits)
        for i in range(0, count - 1, 2):
            put(_ALNUM_INDEX[payload[i]] * 45 + _ALNUM_INDEX[payload[i + 1]], 11)
        if count % 2:
            put(_ALNUM_INDEX[payload[-1]], 6)
    return bits


def _build_codewords(bits, capacity_bits):
    """Terminator, byte alignment and 0xEC/0x11 padding; returns the data codewords."""
    bits = list(bits)
    bits.extend([0] * min(4, capacity_bits - len(bits)))
    bits.extend([0] * (-len(bits) % 8))
    out = []
    for i in range(0, len(bits), 8):
        v = 0
        for bit in bits[i:i + 8]:
            v = (v << 1) | bit
        out.append(v)
    pad = 0
    while len(out) * 8 < capacity_bits:
        out.append(_PAD_BYTES[pad & 1])
        pad += 1
    return out


def _add_ecc_and_interleave(data, ver, ecc_index):
    num_blocks = _NUM_ERROR_CORRECTION_BLOCKS[ecc_index][ver]
    block_ecc_len = _ECC_CODEWORDS_PER_BLOCK[ecc_index][ver]
    raw_codewords = _num_raw_data_modules(ver) // 8
    num_short_blocks = num_blocks - raw_codewords % num_blocks
    short_block_len = raw_codewords // num_blocks
    blocks = []
    divisor = _rs_divisor(block_ecc_len)
    k = 0
    for i in range(num_blocks):
        dat = data[k:k + short_block_len - block_ecc_len + (0 if i < num_short_blocks else 1)]
        k += len(dat)
        ecc = _rs_remainder(dat, divisor)
        if i < num_short_blocks:
            dat = dat + [0]  # placeholder so all blocks have equal length; skipped when interleaving
        blocks.append(dat + ecc)
    result = []
    for i in range(len(blocks[0])):
        for j, blk in enumerate(blocks):
            if i != short_block_len - block_ecc_len or j >= num_short_blocks:
                result.append(blk[i])
    return result


# ---- matrix --------------------------------------------------------------------------------------------------------

class _Grid:
    """Module matrix plus the function-pattern mask; coordinates are (x = column, y = row)."""

    def __init__(self, ver):
        self.ver = ver
        self.size = ver * 4 + 17
        self.mod = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]
        self._draw_function_patterns()

    def set_fn(self, x, y, dark):
        self.mod[y][x] = dark
        self.fn[y][x] = True

    def _draw_function_patterns(self):
        size = self.size
        for i in range(size):  # timing patterns
            self.set_fn(6, i, i % 2 == 0)
            self.set_fn(i, 6, i % 2 == 0)
        self._finder(3, 3)
        self._finder(size - 4, 3)
        self._finder(3, size - 4)
        pos = _alignment_positions(self.ver)
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if not ((i == 0 and j == 0) or (i == 0 and j == n - 1) or (i == n - 1 and j == 0)):
                    self._alignment(pos[i], pos[j])
        self.draw_format_bits("L", 0)  # dummy, reserves the cells; real bits are drawn per mask
        self._draw_version()

    def _finder(self, cx, cy):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                dist = max(abs(dx), abs(dy))
                x, y = cx + dx, cy + dy
                if 0 <= x < self.size and 0 <= y < self.size:
                    self.set_fn(x, y, dist not in (2, 4))

    def _alignment(self, cx, cy):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                self.set_fn(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)

    def draw_format_bits(self, ecc, mask):
        data = _ECC_FORMAT[ecc] << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412  # 15 bits
        size = self.size
        for i in range(0, 6):
            self.set_fn(8, i, bool(_get_bit(bits, i)))
        self.set_fn(8, 7, bool(_get_bit(bits, 6)))
        self.set_fn(8, 8, bool(_get_bit(bits, 7)))
        self.set_fn(7, 8, bool(_get_bit(bits, 8)))
        for i in range(9, 15):
            self.set_fn(14 - i, 8, bool(_get_bit(bits, i)))
        for i in range(0, 8):
            self.set_fn(size - 1 - i, 8, bool(_get_bit(bits, i)))
        for i in range(8, 15):
            self.set_fn(8, size - 15 + i, bool(_get_bit(bits, i)))
        self.set_fn(8, size - 8, True)  # the always-dark module

    def _draw_version(self):
        if self.ver < 7:
            return
        rem = self.ver
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        bits = self.ver << 12 | rem  # 18 bits
        for i in range(18):
            bit = bool(_get_bit(bits, i))
            a = self.size - 11 + i % 3
            b = i // 3
            self.set_fn(a, b, bit)
            self.set_fn(b, a, bit)

    def draw_codewords(self, data):
        """Zigzag placement of the interleaved codewords; remainder bits stay light."""
        size = self.size
        i = 0
        right = size - 1
        while right >= 1:
            if right == 6:
                right = 5  # skip the vertical timing column
            for vert in range(size):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = size - 1 - vert if upward else vert
                    if not self.fn[y][x] and i < len(data) * 8:
                        self.mod[y][x] = bool(_get_bit(data[i >> 3], 7 - (i & 7)))
                        i += 1
            right -= 2
        assert i == len(data) * 8


_MASKS = (
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)


def _masked(grid, ecc, mask):
    """New module matrix with the data mask applied and the format bits for (ecc, mask) drawn."""
    size = grid.size
    fn = grid.fn
    rule = _MASKS[mask]
    rows = [[grid.mod[y][x] ^ (not fn[y][x] and rule(x, y)) for x in range(size)] for y in range(size)]
    saved = grid.mod
    grid.mod = rows
    grid.draw_format_bits(ecc, mask)
    grid.mod = saved
    return rows


def _penalty(rows):
    size = len(rows)
    score = 0
    strings = ["".join("1" if m else "0" for m in row) for row in rows]
    cols = ["".join(s[x] for s in strings) for x in range(size)]
    pad = "0000"
    p1, p2 = "1011101" + pad, pad + "1011101"
    for line in strings + cols:
        # N1: runs of 5 or more same-coloured modules
        for _, grp in itertools.groupby(line):
            n = len(list(grp))
            if n >= 5:
                score += _N1 + n - 5
        # N3: 1:1:3:1:1 pattern next to 4 light modules; outside the symbol counts as light
        padded = pad + line + pad
        for pat in (p1, p2):
            at = padded.find(pat)
            while at != -1:
                score += _N3
                at = padded.find(pat, at + 1)
    # N2: 2x2 blocks of one colour
    for y in range(size - 1):
        a, b = strings[y], strings[y + 1]
        for x in range(size - 1):
            if a[x] == a[x + 1] == b[x] == b[x + 1]:
                score += _N2
    # N4: balance of dark modules, 10 points per started 5% step away from 50%
    dark = sum(s.count("1") for s in strings)
    total = size * size
    k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
    return score + k * _N4


def encode(data, ecc="M", version=None, mask=None):
    """Encode data (str or bytes) as a QR Code; returns rows of bool (True = dark), no quiet zone."""
    if ecc not in _ECC_INDEX:
        raise ValueError("QR-BAD-ECC: ecc must be one of L, M, Q, H")
    if version is not None and not (isinstance(version, int) and not isinstance(version, bool) and 1 <= version <= 40):
        raise ValueError("QR-BAD-VERSION: version must be 1..40")
    if mask is not None and not (isinstance(mask, int) and not isinstance(mask, bool) and 0 <= mask <= 7):
        raise ValueError("QR-BAD-MASK: mask must be 0..7")
    mode, payload, count = _segment(data)
    if count == 0:
        raise ValueError("QR-DATA-EMPTY")
    ecc_index = _ECC_INDEX[ecc]
    candidates = range(1, 41) if version is None else (version,)
    for ver in candidates:
        bits = _segment_bits(mode, payload, count, ver)
        capacity_bits = _num_data_codewords(ver, ecc_index) * 8
        if bits is not None and len(bits) <= capacity_bits:
            break
    else:
        raise ValueError("QR-DATA-TOO-LONG")
    codewords = _build_codewords(bits, capacity_bits)
    grid = _Grid(ver)
    grid.draw_codewords(_add_ecc_and_interleave(codewords, ver, ecc_index))
    if mask is not None:
        return _masked(grid, ecc, mask)
    best, best_score = None, None
    for m in range(8):
        rows = _masked(grid, ecc, m)
        score = _penalty(rows)
        if best_score is None or score < best_score:
            best, best_score = rows, score
    return best


# ---- renderers -----------------------------------------------------------------------------------------------------

def _padded(matrix, border):
    size = len(matrix)
    if border < 0:
        raise ValueError("border must be >= 0")
    blank = [False] * (size + 2 * border)
    side = [False] * border
    return [blank] * border + [side + list(map(bool, r)) + side for r in matrix] + [blank] * border


def render_console(matrix, border=4, ansi=True):
    """Two module rows per text line with half blocks; ansi=True forces black on white (scannable on dark themes)."""
    rows = _padded(matrix, border)
    width = len(rows[0])
    if len(rows) % 2:
        rows.append([False] * width)
    glyph = {(False, False): " ", (True, False): "▀", (False, True): "▄", (True, True): "█"}
    lines = []
    for y in range(0, len(rows), 2):
        line = "".join(glyph[(rows[y][x], rows[y + 1][x])] for x in range(width))
        lines.append("\x1b[30;47m" + line + "\x1b[0m" if ansi else line)
    return "\n".join(lines) + "\n"


def render_svg(matrix, scale=8, border=4):
    """Standalone SVG: white background rect and one <path> of horizontal dark runs."""
    rows = _padded(matrix, border)
    dim = len(rows)
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < dim:
            if row[x]:
                start = x
                while x < dim and row[x]:
                    x += 1
                parts.append("M%d,%dh%dv1h-%dz" % (start, y, x - start, x - start))
            else:
                x += 1
    px = dim * scale
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 %d %d" width="%d" height="%d" '
            'shape-rendering="crispEdges">\n'
            '<rect width="100%%" height="100%%" fill="#FFFFFF"/>\n'
            '<path d="%s" fill="#000000"/>\n</svg>\n') % (dim, dim, px, px, "".join(parts))


def _png_chunk(tag, body):
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)


def render_png(matrix, scale=8, border=4):
    """8-bit grayscale PNG (0 = dark, 255 = light), each module scale x scale pixels."""
    if scale < 1:
        raise ValueError("scale must be >= 1")
    rows = _padded(matrix, border)
    dim = len(rows)
    px = dim * scale
    raw = bytearray()
    for row in rows:
        line = b"\x00" + b"".join((b"\x00" if m else b"\xff") * scale for m in row)  # filter type 0
        raw += line * scale
    ihdr = struct.pack(">IIBBBBB", px, px, 8, 0, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _png_chunk(b"IEND", b""))
