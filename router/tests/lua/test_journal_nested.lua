-- F-39 (07.11.2026): the Lua journal reader validates the nested records like native_switch.validate_journal
-- (vendor identities, pair_transition metadata, restore steps). The cases and their verdicts are shared with
-- tests/test_journal_nested_parity.py (tests/journal_nested_cases.json, verdicts from the Python reader).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local journal=require('journal')

local function read_file(path) local f=assert(io.open(path,'rb'));local text=f:read('*a');f:close();return text end
local CASES=canon.decode(read_file(t.here..'/../journal_nested_cases.json')).cases

t.test('the Lua reader agrees with the Python reader on every shared nested case',function()
  t.eq(#CASES>=40,true,'the shared cases are present')
  for _,c in ipairs(CASES) do
    local ok,err=pcall(journal.validate,c.journal)
    if ok~=c.accept then
      error(c.name..': Lua '..(ok and 'accepts' or 'refuses ('..tostring(type(err)=='table' and err.code or err)..')')
            ..' but Python '..(c.accept and 'accepts' or 'refuses'),0)
    end
    if not ok then t.eq(type(err)=='table' and err.code,'JOURNAL-INTEGRITY-FAILED',c.name) end
  end
end)

t.test('a checksum-valid journal with a malformed nested record is refused by parse()',function()
  for _,c in ipairs(CASES) do
    local envelope=canon.object({schema=1,data=c.journal,sha256=canon.sha256(canon.encode(c.journal))})
    local ok=pcall(journal.parse,canon.encode(envelope))
    t.eq(ok,c.accept,c.name)
  end
end)

t.run()
