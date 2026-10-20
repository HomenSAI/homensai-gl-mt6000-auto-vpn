-- Recovery candidate only. Inserted into one exact SHA256-pinned vendor helper.
-- No environment marker is trusted, and no subprocess is created for detection.
local hbwa_reload_context
local hbwa_firewall_before
local function hbwa_snapshot(cursor)
    local output, size, sections = {}, 0, 0
    local function item(kind, value)
        if type(value) ~= "string" or #value > 65536 then error("snapshot value") end
        size = size + #value + 24
        if size > 1048576 then error("snapshot size") end
        output[#output + 1] = kind .. #value .. ":" .. value .. ";"
    end
    cursor:foreach("firewall", nil, function(section)
        sections = sections + 1
        if sections > 1024 then error("snapshot sections") end
        item("section", section[".name"])
        item("type", section[".type"])
        local keys = {}
        for key in pairs(section) do
            if type(key) ~= "string" then error("snapshot key") end
            if key:sub(1, 1) ~= "." then keys[#keys + 1] = key end
        end
        if #keys > 256 then error("snapshot options") end
        table.sort(keys)
        for _, key in ipairs(keys) do
            item("key", key)
            local value = section[key]
            if type(value) == "string" then item("string", value)
            elseif type(value) == "table" then
                local count = 0
                for index in pairs(value) do
                    count = count + 1
                    if type(index) ~= "number" or index < 1 or index ~= math.floor(index) then error("snapshot list") end
                end
                if count ~= #value or count > 1024 then error("snapshot list") end
                item("list", tostring(count))
                for _, member in ipairs(value) do item("member", member) end
            else error("snapshot type") end
        end
    end)
    if sections == 0 then error("snapshot missing") end
    return table.concat(output)
end
local function hbwa_read(path)
    local file = io.open(path, "r")
    if not file then return nil end
    local value = file:read(4097)
    file:close()
    if not value or #value > 4096 then return nil end
    return value
end

local function hbwa_stat(pid)
    local value = hbwa_read("/proc/" .. pid .. "/stat")
    if not value then return nil end
    local actual, rest = value:match("^(%d+) %b() (.+)$")
    if not actual or (pid ~= "self" and actual ~= pid) then return nil end
    local fields = {}
    for field in rest:gmatch("%S+") do fields[#fields + 1] = field end
    if not fields[2] or not fields[2]:match("^%d+$")
        or not fields[20] or not fields[20]:match("^%d+$") then return nil end
    return {pid = actual, parent = fields[2], started = fields[20]}
end

local function hbwa_context()
    local ok, fs = pcall(require, "nixio.fs")
    if not ok or type(fs.readlink) ~= "function" or type(fs.dir) ~= "function" then return nil end
    local own = hbwa_stat("self")
    if not own then return nil end
    local child, seen, pid = nil, {}, own.parent
    local include = 'config() { echo "You cannot use UCI in firewall includes!" >&2; exit 1; }; . /usr/bin/rtp2.sh'
    for depth = 1, 32 do
        if pid == "0" or seen[pid] then return nil end
        seen[pid] = true
        local before = hbwa_stat(pid)
        local command = hbwa_read("/proc/" .. pid .. "/cmdline")
        local exe = fs.readlink("/proc/" .. pid .. "/exe")
        local after = hbwa_stat(pid)
        if not before or not after or before.parent ~= after.parent or before.started ~= after.started
            or not command or command:sub(-1) ~= "\0" or type(exe) ~= "string" then return nil end
        local args = {}
        for value in command:gmatch("([^%z]*)%z") do args[#args + 1] = value end
        local base = (args[1] or ""):match("([^/]+)$")
        if exe == "/sbin/fw3" or exe == "/usr/sbin/fw3" or base == "fw3" then
            if (exe ~= "/sbin/fw3" and exe ~= "/usr/sbin/fw3") or base ~= "fw3" then return nil end
            local action
            for index = 2, #args do
                local value = args[index]
                if value == "start" or value == "restart" or value == "reload" then
                    if action then return nil end
                    action = value
                elseif value ~= "-q" and value ~= "-4" and value ~= "-6" then return nil end
            end
            if not action or not child or (child.exe ~= "/bin/busybox" and child.exe ~= "/bin/sh"
                and child.exe ~= "/bin/ash") then return nil end
            local shell = (child.args[1] or ""):match("([^/]+)$")
            if (shell ~= "sh" and shell ~= "ash") or #child.args ~= 3 or child.args[2] ~= "-c"
                or child.args[3]:gsub("%s+$", "") ~= include then return nil end
            return "nested"
        end
        child = {exe = exe, args = args}
        if pid == "1" then
            local descriptors = fs.dir("/proc/self/fd")
            if type(descriptors) ~= "function" then return nil end
            local count = 0
            for descriptor in descriptors do
                if descriptor ~= "." and descriptor ~= ".." then
                    count = count + 1
                    if count > 256 or not descriptor:match("^%d+$") then return nil end
                    local target = fs.readlink("/proc/self/fd/" .. descriptor)
                    if type(target) ~= "string" then return nil end
                    target = target:gsub(" %(deleted%)$", "")
                    if target == "/tmp/lock/procd_firewall.lock" or target == "/var/lock/procd_firewall.lock"
                        or target == "/var/run/fw3.lock" or target == "/tmp/run/fw3.lock" then return nil end
                end
            end
            if count == 0 then return nil end
            return "direct"
        end
        pid = before.parent
    end
    return nil
end
