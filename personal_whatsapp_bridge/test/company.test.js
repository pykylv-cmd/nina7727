import test from 'node:test'
import assert from 'node:assert/strict'
import {companyRestorationDiagnostics,companySessions,createCompanyAuthState,processCompanyMessageUpsert,publicCompanyDiagnostics,publicCompanyStatus,reconnectDelay,restoreCompanySessions,restoredQrIsInvalid,stopCompanySession} from '../src/company_session_manager.js'
import {DisconnectReason} from '@whiskeysockets/baileys'
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
test('company voice note and regular audio use shared media inbound',async()=>{
  for(const ptt of [true,false]){
    const calls=[]
    const item={key:{id:`audio-${ptt}`,remoteJid:'37120000001@s.whatsapp.net',fromMe:false},message:{audioMessage:{mimetype:'audio/ogg; codecs=opus',ptt,fileLength:4}}}
    await processCompanyMessageUpsert(state(),{sendMessage:async()=>({key:{id:'reply'}}),updateMediaMessage(){}},{type:'notify',messages:[item]},async payload=>{calls.push(payload);return{accepted:true,reply:'ok'}},quiet,async()=>Buffer.from('opus'))
    assert.equal(calls[0].media.kind,'audio');assert.equal(calls[0].media.data_base64,Buffer.from('opus').toString('base64'))
  }
})
test('company images preserve optional caption and use media inbound',async()=>{
  for(const caption of ['','Kas ir attēlā?']){
    const calls=[],item={key:{id:`image-${caption}`,remoteJid:'37120000001@s.whatsapp.net'},message:{imageMessage:{mimetype:'image/jpeg',caption,fileLength:3}}}
    await processCompanyMessageUpsert(state(),{sendMessage:async()=>({key:{id:'reply'}}),updateMediaMessage(){}},{type:'notify',messages:[item]},async payload=>{calls.push(payload);return{accepted:true,reply:'vision'}},quiet,async()=>Buffer.from('img'))
    assert.equal(calls[0].media.kind,'image');assert.equal(calls[0].media.caption,caption)
  }
})
test('company supported document and quoted context reach shared inbound',async()=>{
  const calls=[],item={key:{id:'doc',remoteJid:'37120000001@s.whatsapp.net'},message:{documentMessage:{mimetype:'application/pdf',fileName:'work.pdf',fileLength:3,contextInfo:{quotedMessage:{conversation:'Earlier'}}}}}
  await processCompanyMessageUpsert(state(),{sendMessage:async()=>({key:{id:'reply'}}),updateMediaMessage(){}},{type:'notify',messages:[item]},async payload=>{calls.push(payload);return{accepted:true,reply:'saved'}},quiet,async()=>Buffer.from('pdf'))
  assert.equal(calls[0].media.kind,'document');assert.equal(calls[0].quoted_text,'Earlier')
})
test('company media sender identities remain isolated',async()=>{
  const calls=[]
  const messages=['37120000001','37120000002'].map((sender,index)=>({key:{id:`image-${index}`,remoteJid:`${sender}@s.whatsapp.net`},message:{imageMessage:{mimetype:'image/jpeg',fileLength:3}}}))
  await processCompanyMessageUpsert(state(),{sendMessage:async()=>({key:{id:'reply'}}),updateMediaMessage(){}},{type:'notify',messages},async payload=>{calls.push(payload);return{accepted:true,reply:'vision'}},quiet,async()=>Buffer.from('img'))
  assert.deepEqual(calls.map(value=>value.sender_jid),['37120000001@s.whatsapp.net','37120000002@s.whatsapp.net'])
})
test('company rejects unsupported and oversized media before download',async()=>{
  let calls=0,downloads=0,sends=0
  const items=[
    {key:{id:'bad',remoteJid:'37120000001@s.whatsapp.net'},message:{documentMessage:{mimetype:'application/x-msdownload',fileLength:2}}},
    {key:{id:'large',remoteJid:'37120000001@s.whatsapp.net'},message:{imageMessage:{mimetype:'image/jpeg',fileLength:11*1024*1024}}},
  ]
  await processCompanyMessageUpsert(state(),{sendMessage:async()=>{sends+=1;return{key:{id:`safe-${sends}`}}}},{type:'notify',messages:items},async()=>{calls+=1},quiet,async()=>{downloads+=1})
  assert.equal(calls,0);assert.equal(downloads,0);assert.equal(sends,2)
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
    restoreCompanySessions(['company'],async(id,token)=>{restored.push(`company:${id}:${token}`)}),
    Promise.resolve().then(()=>restored.push('personal:independent')),
  ])
  assert.deepEqual(restored.sort(),['company:company:','personal:independent'])
})
test('company auth persists credentials and incremental keys across restart',async()=>{
  const database={creds:{registered:true},'key:session:old':{value:'old'}},writes=[]
  const load=async()=>structuredClone(database)
  const store=async(_workspace,records)=>{writes.push(structuredClone(records));for(const[key,value]of Object.entries(records)){if(value===null)delete database[key];else database[key]=structuredClone(value)}}
  const first=await createCompanyAuthState('company',load,store)
  await first.state.keys.set({session:{fresh:{value:'new'}}})
  first.state.creds.registered=true
  await first.saveCreds()
  await first.flush()
  const restored=await createCompanyAuthState('company',load,store)
  assert.equal(restored.restored,true)
  assert.deepEqual(await restored.state.keys.get('session',['old','fresh']),{old:{value:'old'},fresh:{value:'new'}})
  assert.equal(writes.some(value=>value.creds?.registered===true),true)
})
test('restored Company auth creates socket state from stored credentials without pairing data',async()=>{
  const stored={creds:{registered:true,me:{id:'masked@s.whatsapp.net'}},'key:session:one':{value:'saved'}}
  const auth=await createCompanyAuthState('company',async()=>structuredClone(stored),async()=>{})
  assert.equal(auth.restored,true)
  assert.equal(auth.state.creds.registered,true)
  assert.deepEqual(await auth.state.keys.get('session',['one']),{one:{value:'saved'}})
})
test('ordinary restart never creates a pairing QR while invalid credentials require pairing',()=>{
  assert.equal(restoredQrIsInvalid(true,'provider-qr'),true)
  assert.equal(restoredQrIsInvalid(false,'provider-qr'),false)
  assert.equal(reconnectDelay(DisconnectReason.loggedOut),null)
  assert.equal(reconnectDelay(DisconnectReason.badSession),null)
  assert.notEqual(reconnectDelay(DisconnectReason.restartRequired),null)
})
test('Company restoration diagnostics expose lifecycle state without auth values',()=>{
  companyRestorationDiagnostics.set('company',{restoration_state:'connected',last_error_class:'',restore_attempt:2,last_connected_at:'2026-01-01T00:00:00Z',credential:'never'})
  assert.deepEqual(publicCompanyDiagnostics('company'),{restoration_state:'connected',last_error_class:'',restore_attempt:2,last_connected_at:'2026-01-01T00:00:00Z'})
})
