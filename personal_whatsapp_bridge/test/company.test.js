import test from 'node:test'
import assert from 'node:assert/strict'
import {companySessions,processCompanyMessageUpsert,publicCompanyStatus,restoreCompanySessions,stopCompanySession} from '../src/company_session_manager.js'
import {publicStatus,sessions,stopSession} from '../src/session_manager.js'

const quiet={info(){},warn(){}}
const state=()=>({workspaceId:'ninaos_company',status:'connected',sent:new Set()})
const message=(remoteJid,id='incoming',fromMe=false)=>({key:{id,remoteJid,fromMe},message:{conversation:'private text'}})

test('company mode accepts external private messages and replies to origin',async()=>{
  const calls=[],sends=[]
  const processed=await processCompanyMessageUpsert(state(),{sendMessage:async(jid,payload)=>{sends.push({jid,payload});return{key:{id:'outbound-1'}}}},{type:'notify',messages:[message('37120000001@s.whatsapp.net')]},async payload=>{calls.push(payload);return{accepted:true,reply:'Nina reply'}},quiet)
  assert.equal(processed,1);assert.equal(calls[0].sender_jid,'37120000001@s.whatsapp.net');assert.equal(sends[0].jid,'37120000001@s.whatsapp.net')
})
test('company mode ignores fromMe, groups, status, broadcast and newsletters',async()=>{
  let calls=0;const api=async()=>{calls+=1}
  const blocked=[message('37120000001@s.whatsapp.net','own',true),message('1@g.us','group'),message('status@broadcast','status'),message('1@broadcast','broadcast'),message('1@newsletter','news')]
  await processCompanyMessageUpsert(state(),{}, {type:'notify',messages:blocked},api,quiet)
  assert.equal(calls,0)
})
test('company outbound echo never loops',async()=>{
  const value=state();value.sent.add('outbound-1');let calls=0
  await processCompanyMessageUpsert(value,{}, {type:'notify',messages:[message('37120000001@s.whatsapp.net','outbound-1',true)]},async()=>{calls+=1},quiet)
  assert.equal(calls,0);assert.equal(value.sent.size,0)
})
test('company LID message uses phone alternate for stable identity but replies to LID chat',async()=>{
  const calls=[],sends=[],item=message('999000@lid','lid-message')
  item.key.remoteJidAlt='37120000001@s.whatsapp.net'
  await processCompanyMessageUpsert(state(),{sendMessage:async jid=>{sends.push(jid);return{key:{id:'reply'}}}},{type:'notify',messages:[item]},async payload=>{calls.push(payload);return{accepted:true,reply:'reply'}},quiet)
  assert.equal(calls[0].sender_jid,'37120000001@s.whatsapp.net');assert.equal(sends[0],'999000@lid')
})
test('company and personal session registries never collide',async()=>{
  const ended=[]
  sessions.clear();companySessions.clear()
  sessions.set('same-workspace',{workspaceId:'same-workspace',status:'connected',socket:{end:()=>ended.push('personal')},closed:false,retryTimer:null})
  companySessions.set('same-workspace',{workspaceId:'same-workspace',status:'connected',socket:{end:()=>ended.push('company')},closed:false,retryTimer:null})
  await stopCompanySession('same-workspace',false)
  assert.equal(publicStatus('same-workspace').status,'connected');assert.equal(publicCompanyStatus('same-workspace').status,'disconnected');assert.deepEqual(ended,['company'])
  companySessions.set('same-workspace',{workspaceId:'same-workspace',status:'connected',socket:{end:()=>ended.push('company')},closed:false,retryTimer:null})
  await stopSession('same-workspace',false)
  assert.equal(publicCompanyStatus('same-workspace').status,'connected');assert.deepEqual(ended,['company','personal'])
  companySessions.clear()
})
test('company and personal restores are independently invocable',async()=>{
  const restored=[]
  await Promise.all([
    restoreCompanySessions(['company'],async id=>{restored.push(`company:${id}`)}),
    Promise.resolve().then(()=>restored.push('personal:independent')),
  ])
  assert.deepEqual(restored.sort(),['company:company','personal:independent'])
})
