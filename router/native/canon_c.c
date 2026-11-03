/* HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
 * canon_c.c: the hot path of canon.lua in C, a Lua 5.1 module (luaopen_canon_c):
 *   encode(v), decode(text), decode_keys(text, keys) -- byte-identical text, the same values (and number
 *   subtypes), the same accept/reject decisions and the same decode error texts as canon.lua;
 *   sha256(text) -- lower-case hex.
 * canon.lua hands its null/array/object/float markers to init() once and checks the module against its own Lua
 * code before using it; without the module (or with HOMENSAI_CANON_C=0) the Lua code runs unchanged.
 * Built against the headers of the Lua that loads it: OpenWrt's Lua 5.1.5 carries the LNUM patch (lua_Integer is
 * a 32-bit int, numbers have an integer subtype); decode() then gives the subtypes tonumber() gives there.
 * Encode errors carry no "canon.lua:NNN:" position prefix (the text after it is the same).
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"

#if defined(__GNUC__)
#define CANON_EXPORT __attribute__((visibility("default")))
#else
#define CANON_EXPORT
#endif

#define CANON_C_API 1
#define TWO53 9007199254740992.0

static char KEY_NULL, KEY_ARRAY, KEY_OBJECT, KEY_FLOAT;

/* ---------------------------------------------------------------------------------------------------------------
 * growable buffer in a Lua userdata (no leak when an error unwinds)
 * ------------------------------------------------------------------------------------------------------------- */
typedef struct {
    lua_State *L;
    char *p;
    size_t n, cap;
    int slot;
} Buf;

static void buf_need(Buf *b, size_t more)
{
    size_t cap;
    char *p;
    if (b->cap - b->n >= more) return;
    cap = b->cap ? b->cap : 4096;
    while (cap - b->n < more) {
        if (cap > ((size_t)-1) / 4) luaL_error(b->L, "canon: out of memory");
        cap *= 2;
    }
    p = (char *)lua_newuserdata(b->L, cap);
    if (b->n) memcpy(p, b->p, b->n);
    lua_replace(b->L, b->slot);
    b->p = p;
    b->cap = cap;
}

static void buf_add(Buf *b, const char *s, size_t n)
{
    if (!n) return; /* F5: b->p may still be NULL, and memcpy(NULL, s, 0) is undefined */
    buf_need(b, n);
    memcpy(b->p + b->n, s, n);
    b->n += n;
}

#define buf_lit(b, s) buf_add((b), (s), sizeof(s) - 1)

static void buf_char(Buf *b, char c)
{
    if (b->n == b->cap) buf_need(b, 1);
    b->p[b->n++] = c;
}

/* markers from the registry; refuses when init() was not called */
static int push_marker(lua_State *L, char *key)
{
    lua_pushlightuserdata(L, key);
    lua_rawget(L, LUA_REGISTRYINDEX);
    if (lua_type(L, -1) != LUA_TTABLE) return luaL_error(L, "canon_c: init() not called");
    return lua_gettop(L);
}

/* ---------------------------------------------------------------------------------------------------------------
 * UTF-8 / WTF-8 (canon.lua codepoint())
 * ------------------------------------------------------------------------------------------------------------- */
/* code point at s[i] (0-based), its length in *len; -1 when invalid. surrogates accepts ED A0..BF (WTF-8). */
static long codepoint(const unsigned char *s, size_t n, size_t i, int surrogates, size_t *len)
{
    unsigned b = s[i], lo, hi, k, extra;
    long cp;
    if (b < 0x80) { *len = 1; return (long)b; }
    if (b >= 0xC2 && b <= 0xDF) { extra = 1; cp = b - 0xC0; }
    else if (b >= 0xE0 && b <= 0xEF) { extra = 2; cp = b - 0xE0; }
    else if (b >= 0xF0 && b <= 0xF4) { extra = 3; cp = b - 0xF0; }
    else return -1;
    lo = 0x80; hi = 0xBF;
    if (b == 0xE0) lo = 0xA0;
    else if (b == 0xED && !surrogates) hi = 0x9F;
    else if (b == 0xF0) lo = 0x90;
    else if (b == 0xF4) hi = 0x8F;
    for (k = 1; k <= extra; k++) {
        unsigned c;
        if (i + k >= n) return -1;
        c = s[i + k];
        if (c < (k == 1 ? lo : 0x80) || c > (k == 1 ? hi : 0xBF)) return -1;
        cp = cp * 64 + (long)(c - 0x80);
    }
    *len = extra + 1;
    return cp;
}

static int valid_utf8(const unsigned char *s, size_t n)
{
    size_t i = 0, len;
    while (i < n) {
        if (s[i] < 0x80) { i++; continue; }
        if (codepoint(s, n, i, 0, &len) < 0) return 0;
        i += len;
    }
    return 1;
}

static void utf8_char(Buf *b, long cp)
{
    char t[4];
    if (cp < 0x80) { buf_char(b, (char)cp); return; }
    if (cp < 0x800) {
        t[0] = (char)(0xC0 + cp / 64); t[1] = (char)(0x80 + cp % 64);
        buf_add(b, t, 2);
        return;
    }
    if (cp < 0x10000) {
        t[0] = (char)(0xE0 + cp / 4096); t[1] = (char)(0x80 + cp / 64 % 64); t[2] = (char)(0x80 + cp % 64);
        buf_add(b, t, 3);
        return;
    }
    t[0] = (char)(0xF0 + cp / 262144); t[1] = (char)(0x80 + cp / 4096 % 64);
    t[2] = (char)(0x80 + cp / 64 % 64); t[3] = (char)(0x80 + cp % 64);
    buf_add(b, t, 4);
}

/* ---------------------------------------------------------------------------------------------------------------
 * repr(float): canon.lua's search (the same printf/strtod results as the Lua that loads the module)
 * ------------------------------------------------------------------------------------------------------------- */
/* x>0 printed with p significant digits ("%.*e"): digits (no point), exponent */
static int printed(double x, int p, char *digits, int *exp)
{
    char s[64];
    const char *q;
    int nd = 0;
    snprintf(s, sizeof s, "%.*e", p - 1, x);
    q = s;
    digits[nd++] = *q++;
    if (*q == '.') q++;
    while (*q >= '0' && *q <= '9') digits[nd++] = *q++;
    digits[nd] = 0;
    *exp = (int)strtol(q + 1, NULL, 10); /* q points at 'e' */
    return nd;
}

/* correctly rounded p significant digits of x>0, from its 17 printed digits d17/e17: rounding those again is exact
 * unless the dropped part reads exactly 5000..., where the 17 digits may themselves be rounded: then printf again. */
static int scientific(double x, const char *d17, int e17, int p, char *digits, int *exp)
{
    int i, up;
    memcpy(digits, d17, (size_t)p);
    digits[p] = 0;
    *exp = e17;
    if (p == 17) return p;
    if (d17[p] != '5') up = d17[p] > '5';
    else {
        for (i = p + 1; i < 17 && d17[i] == '0'; i++) {}
        if (i == 17) return printed(x, p, digits, exp);
        up = 1;
    }
    if (up) {
        i = p - 1;
        while (i >= 0 && digits[i] == '9') digits[i--] = '0';
        if (i < 0) { digits[0] = '1'; (*exp)++; } else digits[i]++;
    }
    return p;
}

static const double POW10[23] = {1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
                                 1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22};

/* tonumber(d.ddd e exp): an integer below 2^53 times or over an exact power of ten is one correctly rounded IEEE
 * operation, the value strtod gives (Clinger's fast path); the rest goes through strtod. */
static double value_of(const char *digits, int nd, int exp)
{
    char s[64];
    int k = exp - (nd - 1);
    if (nd <= 15 && k >= -22 && k <= 22) {
        double v = 0;
        int i;
        for (i = 0; i < nd; i++) v = v * 10 + (digits[i] - '0');
        return k >= 0 ? v * POW10[k] : v / POW10[-k];
    }
    snprintf(s, sizeof s, "%c.%.*se%d", digits[0], nd - 1, digits + 1, exp);
    return strtod(s, NULL);
}

/* the adjacent decimal with the same number of digits */
static void step(char *digits, int nd, int *exp, int direction)
{
    int i;
    if (direction > 0) {
        i = nd - 1;
        while (i >= 0 && digits[i] == '9') digits[i--] = '0';
        if (i < 0) { digits[0] = '1'; (*exp)++; return; } /* rest already '0' */
        digits[i]++;
    } else {
        int pow10 = digits[0] == '1';
        for (i = 1; i < nd && pow10; i++) pow10 = digits[i] == '0';
        if (pow10) { memset(digits, '9', (size_t)nd); (*exp)--; return; }
        i = nd - 1;
        while (digits[i] == '0') digits[i--] = '9';
        digits[i]--;
    }
}

/* canon.lua's round p: the correctly rounded p digits, else their neighbour on the other side of x; 0 if neither
 * gives x back */
static int round_trip(double x, const char *d17, int e17, int p, char *digits, int *exp)
{
    int nd = scientific(x, d17, e17, p, digits, exp), oexp;
    double near = value_of(digits, nd, *exp);
    char other[32];
    if (near == x) return nd;
    memcpy(other, digits, (size_t)nd + 1);
    oexp = *exp;
    step(other, nd, &oexp, near < x ? 1 : -1);
    if (value_of(other, nd, oexp) != x) return 0;
    memcpy(digits, other, (size_t)nd + 1);
    *exp = oexp;
    return nd;
}

/* canon.lua tries p=1..17 and keeps the first p that gives x back. Whether p does is monotonic in p (the p+1
 * correctly rounded digits are at least as close as any p-digit decimal, and the neighbour step covers the other
 * side of x), so the first p is found by bisection: 4-5 rounds instead of up to 17. */
static int shortest(lua_State *L, double x, char *digits, int *exp)
{
    char d17[32];
    int lo = 1, hi = 17, nd, e17;
    printed(x, 17, d17, &e17);
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (round_trip(x, d17, e17, mid, digits, exp)) hi = mid; else lo = mid + 1;
    }
    nd = round_trip(x, d17, e17, lo, digits, exp);
    if (!nd) return luaL_error(L, "canon: no round-trip digits");
    return nd;
}

/* The monitor re-encodes thousands of unchanged numbers every pass: a small direct-mapped memo of the text (pure
 * function of the bits; zero is never looked up). 2048 entries, 80 KB. */
#define REPR_SLOTS 2048
static struct {
    double x;
    unsigned char n;
    char text[31];
} repr_memo[REPR_SLOTS];

static void repr_float(Buf *b, double x)
{
    char digits[32], out[64];
    int nd, exp, point, k = 0;
    uint64_t bits;
    unsigned slot;
    if (x != x || isinf(x)) luaL_error(b->L, "canon: float is not finite");
    if (x == 0) {
        if (signbit(x)) buf_lit(b, "-0.0"); else buf_lit(b, "0.0");
        return;
    }
    memcpy(&bits, &x, sizeof bits);
    slot = (unsigned)((bits * 0x9E3779B97F4A7C15ull) >> 53) & (REPR_SLOTS - 1);
    if (repr_memo[slot].x == x && repr_memo[slot].n) {
        buf_add(b, repr_memo[slot].text, repr_memo[slot].n);
        return;
    }
    if (x < 0) { out[k++] = '-'; x = -x; }
    nd = shortest(b->L, x, digits, &exp);
    while (nd > 1 && digits[nd - 1] == '0') nd--;
    point = exp + 1; /* Python format_float_short: exponent form when decpt <= -4 or decpt > 16 */
    if (point > -4 && point <= 16) {
        if (point <= 0) {
            out[k++] = '0'; out[k++] = '.';
            while (point++ < 0) out[k++] = '0';
            memcpy(out + k, digits, (size_t)nd); k += nd;
        } else if (point >= nd) {
            memcpy(out + k, digits, (size_t)nd); k += nd;
            while (point-- > nd) out[k++] = '0';
            out[k++] = '.'; out[k++] = '0';
        } else {
            memcpy(out + k, digits, (size_t)point); k += point;
            out[k++] = '.';
            memcpy(out + k, digits + point, (size_t)(nd - point)); k += nd - point;
        }
    } else {
        int e = point - 1;
        out[k++] = digits[0];
        if (nd > 1) { out[k++] = '.'; memcpy(out + k, digits + 1, (size_t)nd - 1); k += nd - 1; }
        k += snprintf(out + k, sizeof out - (size_t)k, "e%c%02d", e < 0 ? '-' : '+', e < 0 ? -e : e);
    }
    buf_add(b, out, (size_t)k);
    if (k < (int)sizeof repr_memo[slot].text) {
        memcpy(&repr_memo[slot].x, &bits, sizeof bits);
        memcpy(repr_memo[slot].text, out, (size_t)k);
        repr_memo[slot].n = (unsigned char)k;
    }
}

/* ---------------------------------------------------------------------------------------------------------------
 * encode
 * ------------------------------------------------------------------------------------------------------------- */
typedef struct {
    lua_State *L;
    Buf b;
    int null_i, array_i, object_i, float_i;
} Enc;

static unsigned char PLAIN[256]; /* 1: byte written as is inside a string */

static void u_escape(char *t, long cp) /* \u%04x */
{
    static const char HEX[] = "0123456789abcdef";
    t[0] = '\\';
    t[1] = 'u';
    t[2] = HEX[(cp >> 12) & 15];
    t[3] = HEX[(cp >> 8) & 15];
    t[4] = HEX[(cp >> 4) & 15];
    t[5] = HEX[cp & 15];
}

static void quote(Buf *b, const unsigned char *s, size_t n)
{
    size_t i = 0, run;
    while (i < n && PLAIN[s[i]]) i++;
    buf_need(b, n + 2);
    b->p[b->n++] = '"';
    if (i == n) {
        memcpy(b->p + b->n, s, n);
        b->n += n;
        b->p[b->n++] = '"';
        return;
    }
    i = 0;
    while (i < n) {
        size_t len;
        long cp;
        char t[16];
        run = i;
        while (run < n && PLAIN[s[run]]) run++;
        if (run > i) { buf_add(b, (const char *)s + i, run - i); i = run; }
        if (i >= n) break;
        cp = codepoint(s, n, i, 1, &len);
        if (cp < 0) luaL_error(b->L, "canon: string is not UTF-8");
        switch (cp) {
        case 8: buf_lit(b, "\\b"); break;
        case 9: buf_lit(b, "\\t"); break;
        case 10: buf_lit(b, "\\n"); break;
        case 12: buf_lit(b, "\\f"); break;
        case 13: buf_lit(b, "\\r"); break;
        case 34: buf_lit(b, "\\\""); break;
        case 92: buf_lit(b, "\\\\"); break;
        default:
            if (cp < 0x10000) {
                u_escape(t, cp);
                buf_add(b, t, 6);
            } else {
                long v = cp - 0x10000;
                u_escape(t, 0xD800 + v / 1024);
                u_escape(t + 6, 0xDC00 + v % 1024);
                buf_add(b, t, 12);
            }
        }
        i += len;
    }
    buf_char(b, '"');
}

static void encode_number(Buf *b, double x)
{
    char t[400];
    if (x != x || isinf(x)) luaL_error(b->L, "canon: number is not finite");
    if (x == floor(x)) {
        if (fabs(x) > TWO53) luaL_error(b->L, "canon: integer beyond 2^53");
        if (x == 0) { buf_char(b, '0'); return; }
        buf_add(b, t, (size_t)snprintf(t, sizeof t, "%.0f", x));
        return;
    }
    repr_float(b, x);
}

typedef struct {
    const char *s;
    size_t len;
} Key;

static int key_cmp(const void *pa, const void *pb)
{
    const Key *a = (const Key *)pa, *b = (const Key *)pb;
    size_t n = a->len < b->len ? a->len : b->len;
    int c = memcmp(a->s, b->s, n);
    if (c) return c;
    return a->len < b->len ? -1 : a->len > b->len;
}

enum { K_ARRAY, K_OBJECT, K_FLOAT };

static void encode_value(Enc *e, int idx, int depth)
{
    lua_State *L = e->L;
    Buf *b = &e->b;
    int kind;
    if (depth > 200) luaL_error(L, "canon: nesting too deep");
    if (lua_rawequal(L, idx, e->null_i)) { buf_lit(b, "null"); return; }
    switch (lua_type(L, idx)) {
    case LUA_TBOOLEAN:
        if (lua_toboolean(L, idx)) buf_lit(b, "true"); else buf_lit(b, "false");
        return;
    case LUA_TNUMBER:
        encode_number(b, (double)lua_tonumber(L, idx));
        return;
    case LUA_TSTRING: {
        size_t n;
        const char *s = lua_tolstring(L, idx, &n);
        quote(b, (const unsigned char *)s, n);
        return;
    }
    case LUA_TTABLE:
        break;
    default:
        luaL_error(L, "canon: cannot encode %s", luaL_typename(L, idx));
    }
    luaL_checkstack(L, 6, "canon: nesting too deep");
    if (lua_getmetatable(L, idx)) { /* getmetatable() of Lua: __metatable when the metatable has one */
        lua_pushliteral(L, "__metatable");
        lua_rawget(L, -2);
        if (!lua_isnil(L, -1)) lua_replace(L, -2); else lua_pop(L, 1);
        if (lua_rawequal(L, -1, e->array_i)) kind = K_ARRAY;
        else if (lua_rawequal(L, -1, e->object_i)) kind = K_OBJECT;
        else if (lua_rawequal(L, -1, e->float_i)) kind = K_FLOAT;
        else kind = -1;
        lua_pop(L, 1);
        if (kind < 0) luaL_error(L, "canon: unsupported table");
    } else {
        size_t count = 0;
        lua_pushnil(L);
        while (lua_next(L, idx)) { count++; lua_pop(L, 1); }
        if (!count) luaL_error(L, "canon: empty table without canon.array/object");
        kind = count == lua_objlen(L, idx) ? K_ARRAY : K_OBJECT;
    }
    if (kind == K_FLOAT) {
        lua_getfield(L, idx, "value");
        if (lua_type(L, -1) != LUA_TNUMBER) luaL_error(L, "canon: float value is not a number");
        repr_float(b, (double)lua_tonumber(L, -1));
        lua_pop(L, 1);
    } else if (kind == K_ARRAY) {
        size_t n = lua_objlen(L, idx), i;
        buf_char(b, '[');
        for (i = 1; i <= n; i++) {
            if (i > 1) buf_char(b, ',');
            lua_rawgeti(L, idx, (int)i);
            encode_value(e, lua_gettop(L), depth + 1);
            lua_pop(L, 1);
        }
        buf_char(b, ']');
    } else {
        Key small[8], *keys = small;
        size_t count = 0, i;
        lua_pushnil(L);
        while (lua_next(L, idx)) {
            if (lua_type(L, -2) != LUA_TSTRING) luaL_error(L, "canon: object key is not a string");
            count++;
            lua_pop(L, 1);
        }
        if (count > sizeof small / sizeof small[0]) {
            if (count > ((size_t)-1) / sizeof(Key)) luaL_error(L, "canon: out of memory");
            keys = (Key *)lua_newuserdata(L, count * sizeof(Key)); /* stays on the stack below the values */
        } else {
            lua_pushnil(L);
        }
        i = 0;
        lua_pushnil(L);
        while (lua_next(L, idx)) { /* the strings stay alive: the table keeps its keys */
            keys[i].s = lua_tolstring(L, -2, &keys[i].len);
            i++;
            lua_pop(L, 1);
        }
        qsort(keys, count, sizeof(Key), key_cmp);
        buf_char(b, '{');
        for (i = 0; i < count; i++) {
            if (i > 0) buf_char(b, ',');
            quote(b, (const unsigned char *)keys[i].s, keys[i].len);
            buf_char(b, ':');
            lua_pushlstring(L, keys[i].s, keys[i].len);
            lua_rawget(L, idx);
            encode_value(e, lua_gettop(L), depth + 1);
            lua_pop(L, 1);
        }
        buf_char(b, '}');
        lua_pop(L, 1); /* keys userdata or nil */
    }
}

/* json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=True, allow_nan=False) */
static int l_encode(lua_State *L)
{
    Enc e;
    lua_settop(L, 1);
    e.L = L;
    e.null_i = push_marker(L, &KEY_NULL);
    e.array_i = push_marker(L, &KEY_ARRAY);
    e.object_i = push_marker(L, &KEY_OBJECT);
    e.float_i = push_marker(L, &KEY_FLOAT);
    lua_pushnil(L);
    e.b.L = L;
    e.b.p = NULL;
    e.b.n = e.b.cap = 0;
    e.b.slot = lua_gettop(L);
    encode_value(&e, 1, 0);
    lua_pushlstring(L, e.b.p ? e.b.p : "", e.b.n);
    return 1;
}

/* ---------------------------------------------------------------------------------------------------------------
 * decode: positions are 1-based as in canon.lua, so the error texts are the same
 * ------------------------------------------------------------------------------------------------------------- */
typedef struct {
    lua_State *L;
    const unsigned char *s;
    size_t n;
    Buf b;
    int null_i, array_i, object_i, float_i;
} Dec;

static int fail(Dec *d, size_t i, const char *what)
{
    char t[160];
    snprintf(t, sizeof t, "canon: %s at byte %lu", what, (unsigned long)i);
    lua_pushstring(d->L, t);
    return lua_error(d->L);
}

#define AT(d, i) ((i) >= 1 && (i) <= (d)->n ? (int)(d)->s[(i)-1] : -1)
#define DIGIT(c) ((c) >= '0' && (c) <= '9')

static unsigned char STOP[256]; /* bytes that end a plain string run: 0..31, '"', '\\' */

static size_t skip(Dec *d, size_t i)
{
    while (i <= d->n) {
        unsigned char c = d->s[i - 1];
        if (c != ' ' && c != '\t' && c != '\n' && c != '\r') return i;
        i++;
    }
    return d->n + 1;
}

static size_t digits_end(Dec *d, size_t i) /* string.find(s,'[^0-9]',i) or #s+1 */
{
    while (i <= d->n && DIGIT(d->s[i - 1])) i++;
    return i;
}

static long hex4(Dec *d, size_t i)
{
    long v = 0;
    size_t k;
    if (i < 1 || i + 3 > d->n) return -1;
    for (k = 0; k < 4; k++) {
        int c = d->s[i - 1 + k];
        if (c >= '0' && c <= '9') v = v * 16 + (c - '0');
        else if (c >= 'a' && c <= 'f') v = v * 16 + (c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') v = v * 16 + (c - 'A' + 10);
        else return -1;
    }
    return v;
}

/* the integer canon.lua keeps: tonumber(raw), then 0 for any zero. Under LNUM tonumber() gives an integer only for
 * an unsigned decimal up to 2^31-1 (lua_str2ul: "-5" overflows to a double, "-0" is 0); floats stay doubles. */
static void push_integer(lua_State *L, const char *raw, double x)
{
#ifdef LUA_TINT
    if (x == 0 || (raw[0] != '-' && x <= 2147483647.0)) {
        lua_pushinteger(L, (lua_Integer)(int)x);
        return;
    }
#else
    (void)raw;
    if (x == 0) x = 0; /* Python int('-0') is 0 */
#endif
    lua_pushnumber(L, (lua_Number)x);
}

static size_t parse_string(Dec *d, size_t i) /* s[i]=='"'; pushes the string */
{
    const unsigned char *s = d->s;
    size_t j;
    i++;
    j = i;
    while (j <= d->n && !STOP[s[j - 1]]) j++;
    if (j > d->n) fail(d, i, "unterminated string");
    if (s[j - 1] == '"') {
        lua_pushlstring(d->L, (const char *)s + i - 1, j - i);
        return j + 1;
    }
    d->b.n = 0;
    for (;;) {
        int c, e;
        j = i;
        while (j <= d->n && !STOP[s[j - 1]]) j++;
        if (j > d->n) fail(d, i, "unterminated string");
        if (j > i) buf_add(&d->b, (const char *)s + i - 1, j - i);
        c = s[j - 1];
        if (c == '"') {
            lua_pushlstring(d->L, d->b.p, d->b.n);
            return j + 1;
        }
        if (c != '\\') fail(d, j, "invalid control character");
        e = AT(d, j + 1);
        if (e != 'u') {
            char text;
            switch (e) {
            case '"': text = '"'; break;
            case '\\': text = '\\'; break;
            case '/': text = '/'; break;
            case 'b': text = '\b'; break;
            case 'f': text = '\f'; break;
            case 'n': text = '\n'; break;
            case 'r': text = '\r'; break;
            case 't': text = '\t'; break;
            default: fail(d, j, "invalid escape"); text = 0;
            }
            buf_char(&d->b, text);
            i = j + 2;
        } else {
            long cp = hex4(d, j + 2);
            if (cp < 0) fail(d, j, "invalid \\uXXXX escape");
            i = j + 6;
            if (cp >= 0xD800 && cp <= 0xDBFF && AT(d, i) == '\\' && AT(d, i + 1) == 'u') {
                long low = hex4(d, i + 2);
                if (low < 0) fail(d, i, "invalid \\uXXXX escape");
                if (low >= 0xDC00 && low <= 0xDFFF) {
                    cp = 0x10000 + (cp - 0xD800) * 1024 + (low - 0xDC00);
                    i += 6;
                }
            }
            utf8_char(&d->b, cp);
        }
    }
}

static size_t parse_number(Dec *d, size_t i)
{
    size_t j = i, len, mag;
    int c, isfloat = 0;
    char small[64], *raw = small;
    double x;
    if (AT(d, j) == '-') j++;
    c = AT(d, j);
    if (c == '0') j++;
    else if (c >= '1' && c <= '9') j = digits_end(d, j);
    else fail(d, i, "invalid value");
    if (AT(d, j) == '.' && DIGIT(AT(d, j + 1))) { isfloat = 1; j = digits_end(d, j + 1); }
    c = AT(d, j);
    if (c == 'e' || c == 'E') {
        size_t k = j + 1;
        int sign = AT(d, k);
        if (sign == '+' || sign == '-') k++;
        if (DIGIT(AT(d, k))) { isfloat = 1; j = digits_end(d, k); }
    }
    len = j - i;
    if (len >= sizeof small) {
        d->b.n = 0;
        buf_need(&d->b, len + 1);
        raw = d->b.p;
    }
    memcpy(raw, d->s + i - 1, len);
    raw[len] = 0;
    x = strtod(raw, NULL);
    if (isfloat) {
        if (x != x || isinf(x)) fail(d, i, "nonfinite number");
        lua_createtable(d->L, 0, 1);
        lua_pushnumber(d->L, (lua_Number)x);
        lua_setfield(d->L, -2, "value");
        lua_pushvalue(d->L, d->float_i);
        lua_setmetatable(d->L, -2);
        return j;
    }
    mag = raw[0] == '-' ? 1 : 0; /* compare the digits: strtod already rounded 2^53+1 */
    if (len - mag > 16 || (len - mag == 16 && memcmp(raw + mag, "9007199254740992", 16) > 0))
        fail(d, i, "integer beyond 2^53");
    push_integer(d->L, raw, x);
    return j;
}

static size_t parse_value(Dec *d, size_t i, int depth)
{
    lua_State *L = d->L;
    int c;
    if (depth > 64) fail(d, i, "nesting limit");
    i = skip(d, i);
    c = AT(d, i);
    if (c == '{') {
        int t;
        luaL_checkstack(L, 4, "canon: nesting limit");
        lua_newtable(L);
        t = lua_gettop(L);
        i = skip(d, i + 1);
        if (AT(d, i) != '}') {
            for (;;) {
                int e;
                if (AT(d, i) != '"') fail(d, i, "expected property name");
                i = parse_string(d, i);
                i = skip(d, i);
                if (AT(d, i) != ':') fail(d, i, "expected colon");
                lua_pushvalue(L, -1);
                lua_rawget(L, t);
                if (!lua_isnil(L, -1)) fail(d, i, "duplicate field");
                lua_pop(L, 1);
                i = parse_value(d, i + 1, depth + 1);
                lua_rawset(L, t);
                i = skip(d, i);
                e = AT(d, i);
                if (e == '}') break;
                if (e != ',') fail(d, i, "expected , or }");
                i = skip(d, i + 1);
            }
        }
        lua_pushvalue(L, d->object_i);
        lua_setmetatable(L, t);
        return i + 1;
    }
    if (c == '[') {
        int t, n = 0;
        luaL_checkstack(L, 4, "canon: nesting limit");
        lua_newtable(L);
        t = lua_gettop(L);
        i = skip(d, i + 1);
        if (AT(d, i) != ']') {
            for (;;) {
                int e;
                i = parse_value(d, i, depth + 1);
                lua_rawseti(L, t, ++n);
                i = skip(d, i);
                e = AT(d, i);
                if (e == ']') break;
                if (e != ',') fail(d, i, "expected , or ]");
                i = i + 1;
            }
        }
        lua_pushvalue(L, d->array_i);
        lua_setmetatable(L, t);
        return i + 1;
    }
    if (c == '"') return parse_string(d, i);
    if (i + 3 <= d->n) {
        const char *p = (const char *)d->s + i - 1;
        if (!memcmp(p, "null", 4)) { lua_pushvalue(L, d->null_i); return i + 4; }
        if (!memcmp(p, "true", 4)) { lua_pushboolean(L, 1); return i + 4; }
        if (i + 4 <= d->n && !memcmp(p, "false", 5)) { lua_pushboolean(L, 0); return i + 5; }
    }
    return parse_number(d, i);
}

/* skip_value(s,i,depth): the index after one JSON value, validated exactly as parse_value() does (the same errors at
 * the same bytes) but without building it; decode_keys() accepts what decode() accepts (canon.lua skip_value) */
static size_t skip_string(Dec *d, size_t i) /* s[i]=='"'; parse_string() without the text */
{
    const unsigned char *s = d->s;
    i++;
    for (;;) {
        int c, e;
        size_t j = i;
        while (j <= d->n && !STOP[s[j - 1]]) j++;
        if (j > d->n) fail(d, i, "unterminated string");
        c = s[j - 1];
        if (c == '"') return j + 1;
        if (c != '\\') fail(d, j, "invalid control character");
        e = AT(d, j + 1);
        if (e != 'u') {
            if (e != '"' && e != '\\' && e != '/' && e != 'b' && e != 'f' && e != 'n' && e != 'r' && e != 't')
                fail(d, j, "invalid escape");
            i = j + 2;
        } else {
            long cp = hex4(d, j + 2);
            if (cp < 0) fail(d, j, "invalid \\uXXXX escape");
            i = j + 6;
            if (cp >= 0xD800 && cp <= 0xDBFF && AT(d, i) == '\\' && AT(d, i + 1) == 'u') {
                long low = hex4(d, i + 2);
                if (low < 0) fail(d, i, "invalid \\uXXXX escape");
                if (low >= 0xDC00 && low <= 0xDFFF) i += 6;
            }
        }
    }
}

static size_t skip_value(Dec *d, size_t i, int depth)
{
    lua_State *L = d->L;
    int c;
    if (depth > 64) fail(d, i, "nesting limit");
    i = skip(d, i);
    c = AT(d, i);
    if (c == '{') {
        int t;
        luaL_checkstack(L, 4, "canon: nesting limit");
        lua_newtable(L); /* the names seen, for "duplicate field" */
        t = lua_gettop(L);
        i = skip(d, i + 1);
        if (AT(d, i) != '}') {
            for (;;) {
                int e;
                if (AT(d, i) != '"') fail(d, i, "expected property name");
                i = parse_string(d, i);
                i = skip(d, i);
                if (AT(d, i) != ':') fail(d, i, "expected colon");
                lua_pushvalue(L, -1);
                lua_rawget(L, t);
                if (!lua_isnil(L, -1)) fail(d, i, "duplicate field");
                lua_pop(L, 1);
                lua_pushboolean(L, 1);
                lua_rawset(L, t);
                i = skip_value(d, i + 1, depth + 1);
                i = skip(d, i);
                e = AT(d, i);
                if (e == '}') break;
                if (e != ',') fail(d, i, "expected , or }");
                i = skip(d, i + 1);
            }
        }
        lua_pop(L, 1);
        return i + 1;
    }
    if (c == '[') {
        i = skip(d, i + 1);
        if (AT(d, i) != ']') {
            for (;;) {
                int e;
                i = skip_value(d, i, depth + 1);
                i = skip(d, i);
                e = AT(d, i);
                if (e == ']') break;
                if (e != ',') fail(d, i, "expected , or ]");
                i = i + 1;
            }
        }
        return i + 1;
    }
    if (c == '"') return skip_string(d, i);
    if (i + 3 <= d->n) {
        const char *p = (const char *)d->s + i - 1;
        if (!memcmp(p, "null", 4) || !memcmp(p, "true", 4)) return i + 4;
        if (i + 4 <= d->n && !memcmp(p, "false", 5)) return i + 5;
    }
    i = parse_number(d, i);
    lua_pop(L, 1);
    return i;
}

static void dec_start(lua_State *L, Dec *d, int base)
{
    size_t n;
    if (lua_type(L, 1) != LUA_TSTRING) {
        lua_pushstring(L, "canon: text expected");
        lua_error(L);
    }
    lua_settop(L, base);
    d->L = L;
    d->s = (const unsigned char *)lua_tolstring(L, 1, &n);
    d->n = n;
    d->null_i = push_marker(L, &KEY_NULL);
    d->array_i = push_marker(L, &KEY_ARRAY);
    d->object_i = push_marker(L, &KEY_OBJECT);
    d->float_i = push_marker(L, &KEY_FLOAT);
    lua_pushnil(L);
    d->b.L = L;
    d->b.p = NULL;
    d->b.n = d->b.cap = 0;
    d->b.slot = lua_gettop(L);
    if (n >= 3 && !memcmp(d->s, "\357\273\277", 3)) fail(d, 1, "unexpected UTF-8 BOM");
    if (!valid_utf8(d->s, n)) fail(d, 1, "invalid UTF-8");
}

/* agent.read_json() of the file text (json.loads with its hooks) */
static int l_decode(lua_State *L)
{
    Dec d;
    size_t i;
    dec_start(L, &d, 1);
    i = parse_value(&d, 1, 0);
    i = skip(&d, i);
    if (i <= d.n) fail(&d, i, "extra data");
    return 1;
}

/* decode() of a top-level object keeping only the fields named in keys (a set); the others skipped */
static int l_decode_keys(lua_State *L)
{
    Dec d;
    size_t i;
    int obj, seen;
    dec_start(L, &d, 2);
    i = skip(&d, 1);
    if (AT(&d, i) != '{') fail(&d, i, "expected object");
    lua_newtable(L);
    obj = lua_gettop(L);
    lua_newtable(L);
    seen = lua_gettop(L);
    i = skip(&d, i + 1);
    if (AT(&d, i) == '}') i = i + 1;
    else {
        for (;;) {
            int e, wanted;
            if (AT(&d, i) != '"') fail(&d, i, "expected property name");
            i = parse_string(&d, i);
            i = skip(&d, i);
            if (AT(&d, i) != ':') fail(&d, i, "expected colon");
            lua_pushvalue(L, -1);
            lua_rawget(L, seen);
            if (lua_toboolean(L, -1)) fail(&d, i, "duplicate field");
            lua_pop(L, 1);
            lua_pushvalue(L, -1);
            lua_pushboolean(L, 1);
            lua_rawset(L, seen);
            lua_pushvalue(L, -1);
            lua_gettable(L, 2);
            wanted = lua_toboolean(L, -1);
            lua_pop(L, 1);
            if (wanted) {
                i = parse_value(&d, i + 1, 1);
                lua_rawset(L, obj);
            } else {
                lua_pop(L, 1);
                i = skip_value(&d, i + 1, 1);
            }
            i = skip(&d, i);
            e = AT(&d, i);
            if (e == '}') { i = i + 1; break; }
            if (e != ',') fail(&d, i, "expected , or }");
            i = skip(&d, i + 1);
        }
    }
    i = skip(&d, i);
    if (i <= d.n) fail(&d, i, "extra data");
    lua_pushvalue(L, d.object_i);
    lua_setmetatable(L, obj);
    lua_pushvalue(L, obj);
    return 1;
}

/* ---------------------------------------------------------------------------------------------------------------
 * SHA-256 (FIPS 180-4)
 * ------------------------------------------------------------------------------------------------------------- */
static const uint32_t K256[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static void sha_block(uint32_t h[8], const unsigned char *p)
{
    uint32_t w[64], a, b, c, d, e, f, g, k, t1, t2;
    int i;
    for (i = 0; i < 16; i++)
        w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
    for (i = 16; i < 64; i++) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = h[0]; b = h[1]; c = h[2]; d = h[3]; e = h[4]; f = h[5]; g = h[6]; k = h[7];
    for (i = 0; i < 64; i++) {
        t1 = k + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        k = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += k;
}

static int l_sha256(lua_State *L)
{
    static const char HEX[] = "0123456789abcdef";
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    unsigned char tail[128];
    char out[64];
    size_t n, i, rest;
    uint64_t bits;
    const unsigned char *s = (const unsigned char *)luaL_checklstring(L, 1, &n);
    for (i = 0; i + 64 <= n; i += 64) sha_block(h, s + i);
    rest = n - i;
    memset(tail, 0, sizeof tail);
    memcpy(tail, s + i, rest);
    tail[rest] = 0x80;
    bits = (uint64_t)n * 8;
    rest = rest + 1 + 8 <= 64 ? 64 : 128;
    for (i = 0; i < 8; i++) tail[rest - 1 - i] = (unsigned char)(bits >> (8 * i));
    sha_block(h, tail);
    if (rest == 128) sha_block(h, tail + 64);
    for (i = 0; i < 32; i++) {
        unsigned v = (unsigned)(h[i / 4] >> (24 - 8 * (i % 4))) & 0xff;
        out[2 * i] = HEX[v >> 4];
        out[2 * i + 1] = HEX[v & 15];
    }
    lua_pushlstring(L, out, 64);
    return 1;
}

/* ---------------------------------------------------------------------------------------------------------------
 * init and module
 * ------------------------------------------------------------------------------------------------------------- */
/* The integer API of this build must be the one of the running Lua (LNUM int32 on OpenWrt, ptrdiff_t stock):
 * a module built for the other one would truncate or misread integers, so init() refuses it. */
static int abi_ok(lua_State *L)
{
    int ok;
#ifdef LUA_TINT
    lua_pushinteger(L, (lua_Integer)-5);
    ok = lua_tonumber(L, -1) == -5.0 && lua_isinteger(L, -1);
    lua_pop(L, 1);
#else
    lua_pushinteger(L, (lua_Integer)((sizeof(lua_Integer) > 4) ? (lua_Integer)1 << 31 : 5));
    ok = lua_tonumber(L, -1) == ((sizeof(lua_Integer) > 4) ? 2147483648.0 : 5.0);
    lua_pop(L, 1);
#endif
    lua_pushnumber(L, 0.5);
    ok = ok && lua_tonumber(L, -1) == 0.5;
    lua_pop(L, 1);
    return ok;
}

/* init(null, array_mt, object_mt, float_mt, api): true when this module serves that API */
static int l_init(lua_State *L)
{
    char *keys[4] = {&KEY_NULL, &KEY_ARRAY, &KEY_OBJECT, &KEY_FLOAT};
    int i;
    for (i = 1; i <= 4; i++) luaL_checktype(L, i, LUA_TTABLE);
    if (lua_tonumber(L, 5) != CANON_C_API || !abi_ok(L)) {
        lua_pushboolean(L, 0);
        return 1;
    }
    for (i = 0; i < 4; i++) {
        lua_pushlightuserdata(L, keys[i]);
        lua_pushvalue(L, i + 1);
        lua_rawset(L, LUA_REGISTRYINDEX);
    }
    lua_pushboolean(L, 1);
    return 1;
}

static const luaL_Reg FUNCTIONS[] = {
    {"init", l_init},
    {"encode", l_encode},
    {"decode", l_decode},
    {"decode_keys", l_decode_keys},
    {"sha256", l_sha256},
    {NULL, NULL}};

CANON_EXPORT int luaopen_canon_c(lua_State *L)
{
    int c;
    for (c = 0; c < 256; c++) {
        PLAIN[c] = c >= 0x20 && c <= 0x7E && c != '"' && c != '\\';
        STOP[c] = c < 0x20 || c == '"' || c == '\\';
    }
    lua_newtable(L);
    luaL_register(L, NULL, FUNCTIONS);
    lua_pushnumber(L, CANON_C_API);
    lua_setfield(L, -2, "API");
    return 1;
}
