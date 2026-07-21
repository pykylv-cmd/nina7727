import test from 'node:test'; import assert from 'node:assert/strict'
import {disconnectDetails,normalizeStoredKey,reconnectDelay,resolveWhatsAppVersion,settleNonFatal} from '../src/session_manager.js'
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
