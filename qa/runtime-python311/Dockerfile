# Offline inputs are the exact, already-installed CI images (linux/amd64).
# Python 3.11.2, Node 22.23.3, git and tar come from the reviewed tools image.
# Lua 5.1.5-8.1+b3 and lua-cjson 2.1.0+dfsg-2.1 come from the existing 3.9 runtime.
# No apt install, registry lookup, or mutable package index is needed.
FROM homensai-vpn-python39@sha256:077393380406ae72cf73ce67ed8b0352e10ff7827330b1241631010d6112f150 AS lua
FROM local-dev-tools@sha256:0b4418ddd722b07b92fe44d180df10fe252e105cd85ff830040e77b0fb34e3a7
COPY --from=lua /usr/bin/lua5.1 /usr/bin/luac5.1 /usr/bin/
COPY --from=lua /usr/lib/x86_64-linux-gnu/liblua5.1-cjson.so.0.0.0 /usr/lib/x86_64-linux-gnu/lua/5.1/cjson.so
COPY --from=lua /usr/share/lua/5.1/cjson/util.lua /usr/share/lua/5.1/cjson/util.lua
RUN test "$(python3 --version)" = 'Python 3.11.2' \
    && test "$(node --version)" = 'v22.23.3' \
    && lua5.1 -e "assert(_VERSION == 'Lua 5.1'); assert(require('cjson').decode('{\"ok\":true}').ok)" \
    && luac5.1 -v && git --version && tar --version
WORKDIR /work
