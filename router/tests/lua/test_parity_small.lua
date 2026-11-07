-- Small Python/Lua parity rules (F-48, B5-06 D18 and D21).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=require('canon')
local identity=require('identity')
local A=require('auto')

t.test('D18: a numeric .anonymous of 1 or 1.0 is anonymous like Python `in (True,\'1\')`; 0 and other values are not',function()
  t.eq(identity.anonymous(true),true);t.eq(identity.anonymous('1'),true)
  t.eq(identity.anonymous(1),true);t.eq(identity.anonymous(canon.float(1.0)),true)
  t.eq(identity.anonymous(0),false);t.eq(identity.anonymous(false),false);t.eq(identity.anonymous('true'),false);t.eq(identity.anonymous(nil),false)
  local named=canon.object({['.name']='cfg0123ab',['.anonymous']=1,['.type']='rule',enabled='1',via='wgclient1'})
  t.truthy(string.find(identity.section_id(named,canon.object({})),'^a_'),'a content-derived id, not the section name')
  named['.anonymous']=false
  t.eq(identity.section_id(named,canon.object({})),'cfg0123ab')
end)

t.test('D21: a router-probed proof scope without the router-probed pair mode is LAN-TRIAL-REQUIRED, as in the Python loop',function()
  local env=t.env()
  env.backend.settings.pair_auto_mode='external-lan'
  env.run.fs.write_atomic(env.runtime..'/status.json','{"samples":[],"profiles":[]}')
  local ctx={last_return=0,consumed=canon.object({}),last_attempt=0}
  A.iteration(env,ctx)
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq(status.error_type,'Refused')
  t.eq(status.state,'BLOCKED');t.eq(status.blockers,{'LAN-TRIAL-REQUIRED'})
end)

t.run()
