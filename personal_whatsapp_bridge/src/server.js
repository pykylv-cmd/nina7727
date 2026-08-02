import http from 'node:http'
import {publicStatus, restoreSessions, sendReminder, startSession, stopSession} from './session_manager.js'
import {publicCompanyDiagnostics, publicCompanyStatus, restoreCompanySessions, sendCompanyReminder, startCompanySession, stopCompanySession} from './company_session_manager.js'
import {activeCompanyWorkspaces, activeWorkspaces} from './nina_api.js'
import {ninaErrorDetails} from './nina_api.js'
import {initializeCompanySessions} from './startup.js'

const token=process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN || ''
const port=Number(process.env.PORT || 8080)
const bridgeCompatibility=()=>({
  application_version:'personal-whatsapp-bridge@1.0.0',
  database_compatibility_version:null,
  internal_api_compatibility_version:1,
  service_role:'happy-education:whatsapp-bridge',
  commit_identifier:String(process.env.RAILWAY_GIT_COMMIT_SHA||process.env.NINA_COMMIT_SHA||'unknown').replace(/[^A-Za-z0-9._-]/g,'').slice(0,64)||'unknown'
})
function reply(res,status,payload){res.writeHead(status,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(payload))}
const server=http.createServer(async(req,res)=>{
  if(req.url==='/health') return reply(res,200,{ok:true})
  if(!token || req.headers.authorization!==`Bearer ${token}`) return reply(res,401,{ok:false})
  if(req.method==='GET'&&req.url==='/v1/compatibility') return reply(res,200,{ok:true,runtime:bridgeCompatibility()})
  let body=''; for await(const part of req){body+=part;if(body.length>65536)return reply(res,413,{ok:false})}
  let data={}; try{data=body?JSON.parse(body):{}}catch{return reply(res,400,{ok:false})}
  const workspace=String(data.workspace_id||'')
  if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(workspace)) return reply(res,400,{ok:false})
  try{
    if(req.method==='POST'&&req.url==='/v1/sessions') return reply(res,200,await startSession(workspace,String(data.session_token||''),{resetAuth:true}))
    if(req.method==='POST'&&req.url==='/v1/status') return reply(res,200,publicStatus(workspace))
    if(req.method==='POST'&&req.url==='/v1/outbound') return reply(res,200,await sendReminder(workspace,String(data.delivery_id||''),String(data.text||'')))
    if(req.method==='POST'&&req.url==='/v1/disconnect'){await stopSession(workspace,true);return reply(res,200,{ok:true})}
    if(req.method==='POST'&&req.url==='/v1/company/sessions') return reply(res,200,await startCompanySession(workspace,String(data.session_token||''),{resetAuth:true}))
    if(req.method==='POST'&&req.url==='/v1/company/status') return reply(res,200,publicCompanyStatus(workspace))
    if(req.method==='POST'&&req.url==='/v1/company/outbound') return reply(res,200,await sendCompanyReminder(workspace,String(data.delivery_id||''),String(data.recipient_jid||''),String(data.text||'')))
    if(req.method==='POST'&&req.url==='/v1/company/diagnostics') return reply(res,200,publicCompanyDiagnostics(workspace))
    if(req.method==='POST'&&req.url==='/v1/company/disconnect'){await stopCompanySession(workspace,true);return reply(res,200,{ok:true})}
    return reply(res,404,{ok:false})
  }catch(_){return reply(res,503,{ok:false,error:'bridge_operation_failed'})}
})
server.listen(port,'0.0.0.0')
activeWorkspaces().then(ids=>restoreSessions(ids)).catch(error=>console.error(JSON.stringify({event:'personal WhatsApp active-session lookup failed',...ninaErrorDetails(error)})))
void initializeCompanySessions(activeCompanyWorkspaces,restoreCompanySessions)
