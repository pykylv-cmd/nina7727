import http from 'node:http'
import {publicStatus, restoreSessions, startSession, stopSession} from './session_manager.js'
import {publicCompanyStatus, restoreCompanySessions, startCompanySession, stopCompanySession} from './company_session_manager.js'
import {activeCompanyWorkspaces, activeWorkspaces} from './nina_api.js'
import {ninaErrorDetails} from './nina_api.js'

const token=process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN || ''
const port=Number(process.env.PORT || 8080)
function reply(res,status,payload){res.writeHead(status,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(payload))}
const server=http.createServer(async(req,res)=>{
  if(req.url==='/health') return reply(res,200,{ok:true})
  if(!token || req.headers.authorization!==`Bearer ${token}`) return reply(res,401,{ok:false})
  let body=''; for await(const part of req){body+=part;if(body.length>65536)return reply(res,413,{ok:false})}
  let data={}; try{data=body?JSON.parse(body):{}}catch{return reply(res,400,{ok:false})}
  const workspace=String(data.workspace_id||'')
  if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(workspace)) return reply(res,400,{ok:false})
  try{
    if(req.method==='POST'&&req.url==='/v1/sessions') return reply(res,200,await startSession(workspace,String(data.session_token||''),{resetAuth:true}))
    if(req.method==='POST'&&req.url==='/v1/status') return reply(res,200,publicStatus(workspace))
    if(req.method==='POST'&&req.url==='/v1/disconnect'){await stopSession(workspace,true);return reply(res,200,{ok:true})}
    if(req.method==='POST'&&req.url==='/v1/company/sessions') return reply(res,200,await startCompanySession(workspace,String(data.session_token||''),{resetAuth:true}))
    if(req.method==='POST'&&req.url==='/v1/company/status') return reply(res,200,publicCompanyStatus(workspace))
    if(req.method==='POST'&&req.url==='/v1/company/disconnect'){await stopCompanySession(workspace,true);return reply(res,200,{ok:true})}
    return reply(res,404,{ok:false})
  }catch(_){return reply(res,503,{ok:false,error:'bridge_operation_failed'})}
})
server.listen(port,'0.0.0.0')
activeWorkspaces().then(ids=>restoreSessions(ids)).catch(error=>console.error(JSON.stringify({event:'personal WhatsApp active-session lookup failed',...ninaErrorDetails(error)})))
activeCompanyWorkspaces().then(ids=>restoreCompanySessions(ids)).catch(error=>console.error(JSON.stringify({event:'company WhatsApp active-session lookup failed',...ninaErrorDetails(error)})))
