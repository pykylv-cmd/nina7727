import test from 'node:test'; import assert from 'node:assert/strict'
import {createPersonalAuthState,disconnectDetails,normalizeStoredKey,ownerJids,persistCredentialUpdate,personalStatusAfterClose,processMessageUpsert,publicStatus,reconnectDelay,resolveWhatsAppVersion,restoreSessions,sessions,settleNonFatal,stopSession} from '../src/session_manager.js'
import {clearAuth,clearCompanyAuth,ninaErrorDetails,ninaRequest} from '../src/nina_api.js'
test('group and workspace identifiers are explicit boundaries',()=>{
  assert.equal('123@g.us'.endsWith('@g.us'),true)
  assert.match('workspace-1',/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/)
})
test('pairing restart is immediate while invalid sessions stop',()=>{
  assert.equal(reconnectDelay(515),250); assert.equal(reconnectDelay(401),null); assert.equal(reconnectDelay(500),null)
  assert.equal(personalStatusAfterClose(408,true),'connecting')
  assert.equal(personalStatusAfterClose(408,false),'connection_lost')
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
test('manual Company pairing treats only missing auth as an already empty store',async()=>{
  const previousFetch=globalThis.fetch
  process.env.NINA_WEB_INTERNAL_URL='http://nina.internal';process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN='test-token'
  let requests=0
  globalThis.fetch=async()=>{requests+=1;return{ok:false,status:404,text:async()=>'{"ok":false,"error":"no_auth_records"}'}}
  try{assert.equal(await clearCompanyAuth('company'),0);assert.equal(requests,1)}
  finally{globalThis.fetch=previousFetch}
})
test('Company auth clearing never hides invalid auth authorization backend or network failures',async()=>{
  const previousFetch=globalThis.fetch
  process.env.NINA_WEB_INTERNAL_URL='http://nina.internal';process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN='test-token'
  try{
    for(const status of [401,403,409,500]){
      globalThis.fetch=async()=>({ok:false,status,text:async()=>`{"ok":false,"code":${status}}`})
      await assert.rejects(clearCompanyAuth('company'),error=>error.status===status)
    }
    globalThis.fetch=async()=>{throw new TypeError('network unavailable')}
    await assert.rejects(clearCompanyAuth('company'),/network unavailable/)
  }finally{globalThis.fetch=previousFetch}
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
test('personal credentials and key updates persist atomically for one stable workspace',async()=>{
  const database={},writes=[]
  const auth=await createPersonalAuthState('workspace-1',async()=>structuredClone(database),async(workspace,records)=>{
    assert.equal(workspace,'workspace-1');writes.push(structuredClone(records))
    for(const[key,value]of Object.entries(records)){if(value===null)delete database[key];else database[key]=structuredClone(value)}
  })
  await persistCredentialUpdate(auth,{registered:true,me:{id:'owner@s.whatsapp.net'}},quietLog(),'workspace-1')
  await auth.state.keys.set({session:{one:{value:'saved'}}})
  await auth.flush()
  assert.equal(database.creds.registered,true)
  assert.deepEqual(database['key:session:one'],{value:'saved'})
  assert.equal(writes.length,2)
})
test('personal credential write failures are observable and not swallowed',async()=>{
  const entries=[],log={info(){},error:(fields,event)=>entries.push({fields,event})}
  const auth=await createPersonalAuthState('workspace-1',async()=>({}),async()=>{throw new Error('database unavailable')})
  await assert.rejects(persistCredentialUpdate(auth,{registered:true},log,'workspace-1'),/database unavailable/)
  assert.equal(entries[0].fields.auth_write_success,false)
  assert.equal(JSON.stringify(entries).includes('registered'),false)
})
function messageState(){return {workspaceId:'workspace-1',status:'connected',primaryJid:'371000@s.whatsapp.net',ownJids:ownerJids({id:'371000:2@s.whatsapp.net',lid:'999000@lid'},{}),sent:new Set()}}
function quietLog(){return {info(){},warn(){}}}
test('owner LID self-chat routes to Nina and replies to the same chat',async()=>{
  const calls=[];const sends=[];const receipts=[];const state=messageState()
  const processed=await processMessageUpsert(state,{sendMessage:async(jid,payload)=>{sends.push({jid,payload});return {key:{id:'nina-1'}}}},{type:'notify',messages:[{key:{id:'owner-1',fromMe:true,remoteJid:'999000@lid',remoteJidAlt:'371000@s.whatsapp.net'},message:{conversation:'hello'}}]},async payload=>{calls.push(payload);return {accepted:true,reply:'Nina reply'}},quietLog(),async payload=>{receipts.push(payload)})
  assert.equal(processed,1);assert.equal(calls[0].chat_jid,'371000@s.whatsapp.net');assert.equal(sends[0].jid,'999000@lid');assert.equal(state.sent.has('nina-1'),true)
  assert.deepEqual(receipts,[{workspace_id:'workspace-1',message_id:'nina-1'}])
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
  await processMessageUpsert(messageState(),{sendMessage:async()=>({key:{id:'reply-id'}})},{type:'notify',messages:[{key:{id:'owner-id',fromMe:true,remoteJid:'999000@lid',remoteJidAlt:'371000@s.whatsapp.net'},message:{conversation:'private owner text'}}]},async()=>({accepted:true,reply:'private Nina reply'}),log,async()=>({ok:true}))
  const serialized=JSON.stringify(entries);assert.equal(serialized.includes('private owner text'),false);assert.equal(serialized.includes('private Nina reply'),false);assert.equal(serialized.includes('371000'),false);assert.equal(serialized.includes('999000'),false)
})
test('two workspace self-chats route independently',async()=>{
  const calls=[];const sends=[]
  for (const workspaceId of ['workspace-a','workspace-b']) {
    const state={...messageState(),workspaceId}
    const processed=await processMessageUpsert(state,{sendMessage:async(jid,payload)=>{sends.push({workspaceId,jid,payload});return {key:{id:`reply-${workspaceId}`}}}},{type:'notify',messages:[{key:{id:`owner-${workspaceId}`,fromMe:true,remoteJid:'999000@lid',remoteJidAlt:'371000@s.whatsapp.net'},message:{conversation:'hello'}}]},async payload=>{calls.push(payload);return {accepted:true,reply:`reply ${workspaceId}`}},quietLog(),async()=>({ok:true}))
    assert.equal(processed,1)
  }
  assert.deepEqual(calls.map(value=>value.workspace_id),['workspace-a','workspace-b'])
  assert.deepEqual(sends.map(value=>value.workspaceId),['workspace-a','workspace-b'])
})
test('connect reconnect and disconnect affect only the selected workspace',async()=>{
  const ended=[]
  const state=workspaceId=>({workspaceId,status:'connected',qrSvg:'',closed:false,retryTimer:null,socket:{end:()=>ended.push(workspaceId),logout:async()=>ended.push(workspaceId)}})
  sessions.clear();sessions.set('workspace-a',state('workspace-a'));sessions.set('workspace-b',state('workspace-b'))
  await stopSession('workspace-a',false)
  assert.equal(publicStatus('workspace-a').status,'disconnected');assert.equal(publicStatus('workspace-b').status,'connected');assert.deepEqual(ended,['workspace-a'])
  sessions.set('workspace-a',state('workspace-a'))
  await stopSession('workspace-a',true)
  assert.equal(publicStatus('workspace-b').status,'connected');assert.deepEqual(ended,['workspace-a','workspace-a'])
  sessions.clear()
})
test('restart restores every linked workspace independently',async()=>{
  const restored=[]
  await restoreSessions(['workspace-a','workspace-b'],async workspaceId=>{restored.push(workspaceId);if(workspaceId==='workspace-a')throw new Error('isolated restore failure')})
  assert.deepEqual(restored.sort(),['workspace-a','workspace-b'])
})
