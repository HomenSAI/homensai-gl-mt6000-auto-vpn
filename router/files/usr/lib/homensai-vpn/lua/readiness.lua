-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- readiness.lua: system_readiness.snapshot (Python) in Lua for the Lua monitor's status (owner request 31 Oct 2026:
-- the System readiness page showed "waiting" for ever while Auto ran, because the Lua monitor never published this
-- field). Same codes, states, board allowlist and bounds as system_readiness.py; read-only, never a permission.
--   snapshot(sys, settings, now, memo) -> {time, board, checks, config_free_bytes, config_storage_writable,
--                                          preparation, native_permission='not_assessed', scope}
-- sys (monitor_io.platform_sys() or a test fake): lstat, read(path,maximum) (raises above maximum), dir, exec,
--   executable(path) (exists, not a directory, X_OK), is_file(path) (regular file, symlinks followed),
--   readlink(path), storage(path) -> free bytes|nil, writable true|false|nil, path_env() -> $PATH,
--   preparation(settings) -> the platform.preparation_snapshot record.
-- memo (a table the caller keeps): the board answer of `ubus call system board` once it succeeded (a constant of
-- the device; one child process per monitor process, not one per refresh).
-- Deviations, by design:
--   PYTHON-39-MINIMUM: Python judges its own interpreter. Lua finds python3 on PATH (absent -> fail) and reads its
--     version from the python3 -> python3.N link or the python3.N binaries beside it (N >= 9 -> pass, lower ->
--     fail, none found -> unknown). No Python process is started.
--   A board field that is a JSON object or array (never seen from ubus) is 'unknown' instead of Python's repr.
local canon=require('canon')
local py=require('py')

local M={}
local NULL=canon.null
M.DEFAULT_PATH='/usr/sbin:/usr/bin:/sbin:/bin'
M.RPC_PLUGIN='/usr/libexec/rpcd/homensai-vpn'
M.CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt'
M.CONFIG='/etc/config'
M.MIN_FREE=1048576
M.SCOPE='Dependencies only; native Start performs authoritative certification and lease checks.'

-- shutil.which(name): the first executable PATH entry
function M.which(sys,name)
  local path=(sys.path_env and sys.path_env()) or M.DEFAULT_PATH
  for dir in string.gmatch(path,'[^:]+') do
    local candidate=dir..'/'..name
    if sys.executable(candidate) then return candidate end
  end
  return nil
end

function M.python_state(sys)
  local binary=M.which(sys,'python3')
  if not binary then return 'fail' end
  local minor=nil
  local target=sys.readlink and sys.readlink(binary) or nil
  if type(target)=='string' then minor=tonumber(string.match(target,'python3%.(%d+)$')) end
  if not minor then
    local dir=string.match(binary,'^(.*)/[^/]*$') or '/'
    for _,name in ipairs(sys.dir(dir) or {}) do
      local n=tonumber(string.match(name,'^python3%.(%d+)$'))
      if n and sys.executable(dir..'/'..name) and (minor==nil or n>minor) then minor=n end
    end
  end
  if not minor then return 'unknown' end
  return minor>=9 and 'pass' or 'fail'
end

local function board_text(value,limit)
  if type(value)=='table' and value~=NULL and not canon.is_float(value) then return nil end
  return py.prefix(py.str(value),limit)
end

-- ubus call system board: model/board_name/openwrt of an object reply; anything else leaves them unknown
function M.board(sys,memo)
  if memo and memo.board then
    local copy={};for k,v in pairs(memo.board) do copy[k]=v end
    return copy,true
  end
  local board={model='unknown',board_name='unknown',firmware='unknown',openwrt='unknown'}
  local complete=false
  pcall(function()
    local rc,out=sys.exec({'ubus','call','system','board'},{timeout=3})
    if rc~=0 or type(out)~='string' or #out>32768 then return end
    local ok,data=pcall(canon.decode,out)
    if not ok or not canon.is_object(data) then return end
    for _,key in ipairs({'model','board_name'}) do
      local value=data[key];if value==nil then value='unknown' end
      board[key]=board_text(value,96) or 'unknown'
    end
    local release=data.release;if release==nil then release=canon.object() end
    if not canon.is_object(release) then return end
    local version=release.version;if version==nil then version='unknown' end
    board.openwrt=board_text(version,64) or 'unknown'
    complete=true
  end)
  if complete and memo then
    memo.board={model=board.model,board_name=board.board_name,openwrt=board.openwrt}
  end
  return board,complete
end

function M.firmware(sys)
  local ok,value=pcall(function()
    local text=sys.read('/etc/glversion',256)
    if type(text)~='string' or string.find(text,'[\128-\255]') then return nil end
    text=string.match(text,'^[%s]*(.-)[%s]*$')
    if #text>=1 and #text<=96 and not string.find(text,'[^A-Za-z0-9 ._+~-]') then return text end
    return nil
  end)
  return ok and value or nil
end

function M.snapshot(sys,settings,now,memo)
  local checks=canon.array()
  local function add(code,state) checks[#checks+1]=canon.object({code=code,state=state}) end
  add('PYTHON-39-MINIMUM',M.python_state(sys))
  for _,binary in ipairs({'ubus','uci','lua','ip'}) do
    add('DEPENDENCY-'..string.upper(binary),M.which(sys,binary) and 'pass' or 'fail')
  end
  add('RPC-PLUGIN',sys.is_file(M.RPC_PLUGIN) and 'pass' or 'fail')
  add('CA-BUNDLE',sys.is_file(M.CA_BUNDLE) and 'pass' or 'fail')
  local board=M.board(sys,memo)
  board.firmware=M.firmware(sys) or 'unknown'
  local free,writable=nil,nil
  if sys.storage then
    local ok,f,w=pcall(sys.storage,M.CONFIG)
    if ok then free,writable=f,w end
  end
  local state
  if writable==false then state='fail'
  elseif free==nil or writable==nil then state='unknown'
  elseif free>=M.MIN_FREE then state='pass'
  else state='fail' end
  add('CONFIG-STORAGE-FREE',state)
  local preparation
  local okp,value=pcall(sys.preparation,settings)
  if okp and type(value)=='table' then preparation=value
  else preparation={scope='persistent-mt3000-preparation',state='unknown',checks={},native_permission=false,external_lan_verified=false} end
  local prep=canon.object()
  for k,v in pairs(preparation) do prep[k]=v end
  local rows=canon.array()
  for i,row in ipairs(preparation.checks or {}) do rows[i]=canon.object({code=row.code,state=row.state}) end
  prep.checks=rows
  return canon.object({time=canon.float(canon.number(now) or now),board=canon.object(board),checks=checks,
    config_free_bytes=free==nil and NULL or free,config_storage_writable=writable==nil and NULL or writable,
    preparation=prep,native_permission='not_assessed',scope=M.SCOPE})
end

return M
