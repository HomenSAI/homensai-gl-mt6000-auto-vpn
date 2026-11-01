/* HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
 * canon_fuzz.c: libFuzzer harness for router/native/canon_c.c (decode/decode_keys/encode) built with ASan+UBSan.
 * Each input is handed to canon_fuzz.lua's check(), which runs canon.lua's own Lua decoder and the C decoder and
 * aborts the process when they disagree (accept/reject, error text, decoded value or re-encoded text).
 * Build/run: qa/external/fuzz/run.sh (inside homensai-vpn-qa-external:20261101). Stock Lua 5.1.5, not LNUM.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

int luaopen_canon_c(lua_State *L);
static lua_State *L;
static int check_ref;

int LLVMFuzzerInitialize(int *argc, char ***argv)
{
    const char *script = getenv("CANON_FUZZ_LUA");
    (void)argc;
    (void)argv;
    L = luaL_newstate();
    luaL_openlibs(L);
    lua_getglobal(L, "package");
    lua_getfield(L, -1, "preload");
    lua_pushcfunction(L, luaopen_canon_c);
    lua_setfield(L, -2, "canon_c");
    lua_pop(L, 2);
    if (!script || luaL_dofile(L, script)) {
        fprintf(stderr, "canon_fuzz: cannot load %s: %s\n", script ? script : "(CANON_FUZZ_LUA unset)",
                script ? lua_tostring(L, -1) : "");
        abort();
    }
    check_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    return 0;
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    static unsigned n;
    lua_rawgeti(L, LUA_REGISTRYINDEX, check_ref);
    lua_pushlstring(L, (const char *)data, size);
    if (lua_pcall(L, 1, 0, 0) != 0) {
        fprintf(stderr, "canon_fuzz: MISMATCH: %s\n", lua_tostring(L, -1));
        abort();
    }
    if (++n % 256 == 0) lua_gc(L, LUA_GCCOLLECT, 0);
    return 0;
}
