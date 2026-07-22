import test from 'node:test'; import assert from 'node:assert/strict'
import {disconnectDetails,normalizeStoredKey,ownerJids,processMessageUpsert,reconnectDelay,resolveWhatsAppVersion,settleNonFatal} from '../src/session_manager.js'
import {clearAuth,ninaErrorDetails,ninaRequest} from '../src/nina_api.js'
test('group and workspace identifiers are explicit boundaries',()=>{
  assert.equal('123@g.us'.endsWith('@g.us'),true)
  assert.match('workspace-1',/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/)
})
test('pairing restart is immediate while invalid sessions stop',()=>{
  assert.equal(reconnectDelay(515),250); assert.equal(reconnectDelay(401),null); assert.equal(reconnectDelay(500),null)
})
test('disconnect diagnostics are sanitized and stable',()=>{
  const value=disconnectDetails({name:'Boom',message:'Connection Failure\nsecret-looking-tail',output:{statusCode:515}})
  assert.deepEqual(value,{statusCode:515,errorClass:'Boom',message:'Connection Failure secret-looking-tail'})
})
test('stored app-state keys restore the Baileys protocol type',()=>{
  const value=normalizeStoredKey('app-state-sync-key',{keyData:Buffer.from([1,2])})
  assert.deepEqual([...value.keyData],[1,2])
})
test('current WhatsApp version selection is injectable and exact',async()=>{
  const value=await resolveWhatsAppVersion(async()=>({version:[2,3000,123],isLatest:true}))
  assert.deepEqual(value,{version:[2,3000,123],isLatest:true})
})
test('fresh pairing clears every persisted auth record without exposing values',async()=>{
  const previousFetch=globalThis.fetch; const requests=[]
  process.env.NINA_WEB_INTERNAL_URL='http://nina.internal';process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN='test-token'
  globalThis.fetch=async(url,options)=>{requests.push({url,body:JSON.parse(options.body)});const payload=requests.length===1?{records:{creds:{registered:false},'key:session:1':{private:'hidden'}}}:{ok:true};return {ok:true,text:async()=>JSON.stringify(payload)}}
  try { assert.equal(await clearAuth('workspace-1'),2) } finally { globalThis.fetch=previousFetch }
  assert.deepEqual(requests[1].body.records,{creds:null,'key:session:1':null})
})
test('internal 400 captures endpoint and body without exposing request values',async()=>{
  const previousFetch=globalThis.fetch;process.env.NINA_WEB_INTERNAL_URL='http://nina.internal';process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN='test-token'
  globalThis.fetch=async()=>({ok:false,status:400,text:async()=>'{"ok":false}'})
  try { await assert.rejects(ninaRequest('/internal/personal-whatsapp/auth/store',{workspace_id:'workspace-1',records:{creds:{private:'never-log'}}}),error=>{
    assert.deepEqual(ninaErrorDetails(error),{endpoint:'/internal/personal-whatsapp/auth/store',status:400,response_body:'{"ok":false}',error_class:'NinaInternalError',error_message:'nina_internal_400'});assert.deepEqual(error.requestKeys,['workspace_id','records']);assert.equal(JSON.stringify(error).includes('never-log'),false);return true
  }) } finally { globalThis.fetch=previousFetch }
})
test('transient internal failures settle without an unhandled rejection',async()=>{
  let observed='';const ok=await settleNonFatal(Promise.reject(new Error('nina_internal_400')),error=>{observed=error.message})
  assert.equal(ok,false);assert.equal(observed,'nina_internal_400')
})
function messageState(){return {workspaceId:'workspace-1',status:'connected',primaryJid:'371000@s.whatsapp.net',ownJids:ownerJids({id:'371000:2@s.whatsapp.net',lid:'999000@lid'},{}),sent:new Set()}}
function quietLog(){return {info(){},warn(){}}}
test('owner LID self-chat routes to Nina and replies to the same chat',async()=>{
  const calls=[];const sends=[];const state=messageState()
  const processed=await processMessageUpsert(state,{sendMessage:async(jid,payload)=>{sends.push({jid,payload});return {key:{id:'nina-1'}}}},{type:'notify',messages:[{key:{id:'owner-1',fromMe:true,remoteJid:'999000@lid',remoteJidAlt:'371000@s.whatsapp.net'},message:{conversation:'hello'}}]},async payload=>{calls.push(payload);return {accepted:true,reply:'Nina reply'}},quietLog())
  assert.equal(processed,1);assert.equal(calls[0].chat_jid,'371000@s.whatsapp.net');assert.equal(sends[0].jid,'999000@lid');assert.equal(state.sent.has('nina-1'),true)
})
test('Nina outbound echo is ignored on re-ingest',async()=>{
  const state=messageState();state.sent.add('nina-1');let called=false
  await processMessageUpsert(state,{sendMessage:async()=>{throw new Error('must not send')}},{type:'notify',messages:[{key:{id:'nina-1',fromMe:true,remoteJid:'999000@lid',remoteJidAlt:'371000@s.whatsapp.net'},message:{conversation:'Nina reply'}}]},async()=>{called=true},quietLog())
  assert.equal(called,false)
})
test('external contacts never reach Nina',async()=>{
  let called=false;await processMessageUpsert(messageState(),{},{type:'notify',messages:[{key:{id:'external-1',fromMe:true,remoteJid:'888000@s.whatsapp.net'},message:{conversation:'hello'}}]},async()=>{called=true},quietLog());assert.equal(called,false)
})
test('groups broadcasts and status never reach Nina',async()=>{
  let calls=0;const api=async()=>{calls+=1};const messages=['123@g.us','status@broadcast','123@broadcast'].map((remoteJid,index)=>({key:{id:`blocked-${index}`,fromMe:true,remoteJid},message:{conversation:'hello'}}))
  await processMessageUpsert(messageState(),{}, {type:'notify',messages},api,quietLog());assert.equal(calls,0)
})
test('self-chat lifecycle logs contain no message text or account identifiers',async()=>{
  const entries=[];const log={info:(fields,event)=>entries.push({fields,event}),warn:(fields,event)=>entries.push({fields,event})}
  await processMessageUpsert(messageState(),{sendMessage:async()=>({key:{id:'reply-id'}})},{type:'notify',messages:[{key:{id:'owner-id',fromMe:true,remoteJid:'999000@lid',remoteJidAlt:'371000@s.whatsapp.net'},message:{conversation:'private owner text'}}]},async()=>({accepted:true,reply:'private Nina reply'}),log)
  const serialized=JSON.stringify(entries);assert.equal(serialized.includes('private owner text'),false);assert.equal(serialized.includes('private Nina reply'),false);assert.equal(serialized.includes('371000'),false);assert.equal(serialized.includes('999000'),false)
})
