import makeWASocket, {Browsers, BufferJSON, DisconnectReason, downloadMediaMessage, fetchLatestBaileysVersion, initAuthCreds, jidNormalizedUser, makeCacheableSignalKeyStore, proto} from '@whiskeysockets/baileys'
import pino from 'pino'
import QRCode from 'qrcode'
import {clearCompanyAuth, companyInbound, companyLinked, companyRuntimeState, loadCompanyAuth, ninaErrorDetails, storeCompanyAuth} from './nina_api.js'

const lifecycle=pino({level:process.env.LOG_LEVEL||'info',base:undefined})
const quiet=lifecycle.child({component:'baileys-company'},{level:process.env.BAILEYS_LOG_LEVEL||'warn'})
export const companySessions=new Map()
export const companyRestorationDiagnostics=new Map()
const revive=value=>JSON.parse(JSON.stringify(value),BufferJSON.reviver)
const flatten=value=>JSON.parse(JSON.stringify(value,BufferJSON.replacer))
const normalizedJid=value=>value?jidNormalizedUser(String(value)):''
const unwrap=message=>message?.ephemeralMessage?.message||message?.viewOnceMessage?.message||message?.viewOnceMessageV2?.message||message||{}
const textOf=(message={})=>{const value=unwrap(message);return value.conversation||value.extendedTextMessage?.text||''}
const captionOf=message=>{const value=unwrap(message);return value.imageMessage?.caption||value.documentMessage?.caption||''}
const quotedTextOf=message=>{const value=unwrap(message),context=value.extendedTextMessage?.contextInfo||value.imageMessage?.contextInfo||value.documentMessage?.contextInfo||value.audioMessage?.contextInfo;return String(textOf(context?.quotedMessage)||captionOf(context?.quotedMessage)||'').trim().slice(0,1000)}
const MEDIA_LIMITS={audio:16*1024*1024,image:10*1024*1024,document:20*1024*1024}
const ALLOWED_MIMES={audio:new Set(['audio/aac','audio/mp4','audio/mpeg','audio/ogg','audio/opus','audio/wav','audio/webm','audio/x-m4a']),image:new Set(['image/jpeg','image/png','image/webp']),document:new Set(['application/csv','application/json','application/pdf','application/rtf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/xml','text/csv','text/html','text/markdown','text/plain','text/rtf','text/xml'])}
const baseMime=value=>String(value||'').split(';',1)[0].trim().toLowerCase()
const numberValue=value=>{try{return Number(value?.toString?.()??value??0)}catch{return 0}}
function mediaOf(message={}){
  const value=unwrap(message)
  if(value.audioMessage)return{kind:'audio',node:value.audioMessage,mime_type:String(value.audioMessage.mimetype||'audio/ogg'),filename:value.audioMessage.ptt?'voice.ogg':'audio',caption:''}
  if(value.imageMessage)return{kind:'image',node:value.imageMessage,mime_type:String(value.imageMessage.mimetype||'image/jpeg'),filename:'image',caption:String(value.imageMessage.caption||'')}
  if(value.documentMessage)return{kind:'document',node:value.documentMessage,mime_type:String(value.documentMessage.mimetype||''),filename:String(value.documentMessage.fileName||'document'),caption:String(value.documentMessage.caption||'')}
  return null
}
const unsupportedChat=jid=>jid==='status@broadcast'||jid.endsWith('@broadcast')||jid.endsWith('@g.us')||jid.endsWith('@newsletter')
const normalizeStoredKey=(type,value)=>type==='app-state-sync-key'&&value?proto.Message.AppStateSyncKeyData.fromObject(value):value
export function reconnectDelay(code){return[DisconnectReason.loggedOut,DisconnectReason.badSession,DisconnectReason.connectionReplaced,DisconnectReason.multideviceMismatch,DisconnectReason.forbidden].includes(code)?null:(code===DisconnectReason.restartRequired?250:5000)}
export const restoredQrIsInvalid=(restoring,qr)=>Boolean(restoring&&qr)
export async function createCompanyQr(restoring,qr,encoder=QRCode.toString){
  if(restoredQrIsInvalid(restoring,qr))return{accepted:false,qr_svg:''}
  return{accepted:true,qr_svg:await encoder(qr,{type:'svg',margin:1,width:300})}
}
function closeDetails(error){const value=Number(error?.output?.statusCode??error?.data?.reason??error?.statusCode);return{status_code:Number.isFinite(value)?value:0,error_class:String(error?.name||'Error').slice(0,80)}}
async function settle(operation,message,workspaceId){try{await operation}catch(error){lifecycle.error({workspace_id:workspaceId,...ninaErrorDetails(error)},message)}}
const diagnostic=workspaceId=>{if(!companyRestorationDiagnostics.has(workspaceId))companyRestorationDiagnostics.set(workspaceId,{restoration_state:'idle',last_error_class:'',restore_attempt:0,last_connected_at:''});return companyRestorationDiagnostics.get(workspaceId)}
const disconnectClassification=code=>code===DisconnectReason.loggedOut?'logged_out':reconnectDelay(code)===null?'invalid_auth':'temporary_failure'

export async function processCompanyMessageUpsert(state,socket,event,api=companyInbound,log=lifecycle,download=downloadMediaMessage){
  const type=String(event?.type||'')
  if(type!=='notify'){log.info({workspace_id:state.workspaceId,ignored_reason:'not_live_notify'},'company WhatsApp message ignored');return 0}
  if(state.status!=='connected'){log.info({workspace_id:state.workspaceId,ignored_reason:'not_connected'},'company WhatsApp message ignored');return 0}
  let processed=0
  for(const item of event.messages||[]){
    const key=item.key||{},id=String(key.id||''),remote=normalizedJid(key.remoteJid),alternate=normalizedJid(key.remoteJidAlt)
    const sender=remote.endsWith('@lid')&&alternate.endsWith('@s.whatsapp.net')?alternate:remote
    log.info({workspace_id:state.workspaceId,from_me:Boolean(key.fromMe),has_remote_alt:Boolean(alternate)},'company WhatsApp external message received')
    let ignored=''
    if(!id)ignored='missing_message_id'
    else if(state.sent.delete(id))ignored='nina_outbound_echo'
    else if(key.fromMe)ignored='from_company_account'
    else if(!remote||unsupportedChat(remote)||(alternate&&unsupportedChat(alternate)))ignored='unsupported_chat'
    else if(!(sender.endsWith('@s.whatsapp.net')||sender.endsWith('@lid')))ignored='unsupported_identity'
    const text=textOf(item.message).trim(),media=mediaOf(item.message),quoted_text=quotedTextOf(item.message)
    if(!ignored&&!text&&!media)ignored='no_supported_content'
    if(ignored){log.info({workspace_id:state.workspaceId,ignored_reason:ignored},'company WhatsApp message ignored');continue}
    let mediaPayload
    if(media){
      const mime=baseMime(media.mime_type),declared=numberValue(media.node?.fileLength),limit=MEDIA_LIMITS[media.kind]
      if(!ALLOWED_MIMES[media.kind]?.has(mime)){log.info({workspace_id:state.workspaceId,media_kind:media.kind,ignored_reason:'unsupported_media_type'},'company WhatsApp media rejected');await sendSafeReply(state,socket,remote,'Šis faila veids netiek atbalstīts.',log);continue}
      if(declared>limit){log.info({workspace_id:state.workspaceId,media_kind:media.kind,ignored_reason:'media_too_large'},'company WhatsApp media rejected');await sendSafeReply(state,socket,remote,'Šis fails ir pārāk liels drošai apstrādei.',log);continue}
      try{
        const buffer=await download(item,'buffer',{}, {logger:quiet,reuploadRequest:socket.updateMediaMessage})
        if(!Buffer.isBuffer(buffer)||!buffer.length||buffer.length>limit){await sendSafeReply(state,socket,remote,'Šo failu nevarēju droši apstrādāt.',log);continue}
        mediaPayload={kind:media.kind,mime_type:media.mime_type,filename:media.filename,caption:media.caption,size:buffer.length,data_base64:buffer.toString('base64')}
        log.info({workspace_id:state.workspaceId,media_kind:media.kind,media_bytes:buffer.length},'company WhatsApp media downloaded')
      }catch(error){log.warn({workspace_id:state.workspaceId,media_kind:media.kind,error_class:String(error?.name||'Error').slice(0,80)},'company WhatsApp media download failed');await sendSafeReply(state,socket,remote,'Failu saņēmu, bet lejupielāde neizdevās.',log);continue}
    }
    let result
    try{result=await api({workspace_id:state.workspaceId,message_id:id,sender_jid:sender,text,quoted_text,...(mediaPayload?{media:mediaPayload}:{})})}catch(error){lifecycle.error({workspace_id:state.workspaceId,...ninaErrorDetails(error)},'company WhatsApp inbound API failed');continue}
    const accepted=Boolean(result?.accepted),reply=String(result?.reply||'').trim()
    log.info({workspace_id:state.workspaceId,inbound_accepted:accepted},'company WhatsApp inbound API completed')
    if(!accepted||!reply){log.info({workspace_id:state.workspaceId,reply_generated:false},'company WhatsApp reply not generated');continue}
    log.info({workspace_id:state.workspaceId,reply_generated:true,reply_chars:reply.length},'company WhatsApp reply generated')
    try{const sent=await socket.sendMessage(remote,{text:reply}),sentId=String(sent?.key?.id||'');if(sentId){state.sent.add(sentId);if(state.sent.size>200)state.sent.delete(state.sent.values().next().value)}log.info({workspace_id:state.workspaceId,reply_sent:true},'company WhatsApp reply sent');processed+=1}catch(error){log.warn({workspace_id:state.workspaceId,error_class:String(error?.name||'Error').slice(0,80)},'company WhatsApp reply send failed')}
  }
  return processed
}

async function sendSafeReply(state,socket,remote,text,log){
  try{const sent=await socket.sendMessage(remote,{text}),id=String(sent?.key?.id||'');if(id)state.sent.add(id);log.info({workspace_id:state.workspaceId,reply_sent:true},'company WhatsApp safe media reply sent')}catch(error){log.warn({workspace_id:state.workspaceId,error_class:String(error?.name||'Error').slice(0,80)},'company WhatsApp safe media reply failed')}
}

export async function createCompanyAuthState(workspaceId,load=loadCompanyAuth,store=storeCompanyAuth,options={}){
  let saved
  try{saved=await load(workspaceId)}
  catch(error){if(options.allowMissing&&Number(error?.status)===404)saved={};else throw error}
  const creds=saved.creds?revive(saved.creds):initAuthCreds()
  let queue=Promise.resolve();const enqueue=job=>{const next=queue.then(job,job);queue=next.catch(()=>{});return next}
  const keys={get:async(type,ids)=>Object.fromEntries(ids.map(id=>{const stored=saved[`key:${type}:${id}`];return[id,stored===undefined?null:normalizeStoredKey(type,revive(stored))]})),set:async data=>{const writes={};for(const[type,values]of Object.entries(data))for(const[id,value]of Object.entries(values||{})){const key=`key:${type}:${id}`;writes[key]=value===null?null:flatten(value);if(value===null)delete saved[key];else saved[key]=writes[key]}await enqueue(()=>store(workspaceId,writes))}}
  return{restored:Boolean(saved.creds),state:{creds,keys:makeCacheableSignalKeyStore(keys,quiet)},saveCreds:()=>enqueue(()=>store(workspaceId,{creds:flatten(creds)})),flush:()=>queue}
}

export async function startCompanySession(workspaceId,sessionToken,options={}){
  await stopCompanySession(workspaceId,false)
  if(options.resetAuth&&sessionToken)await clearCompanyAuth(workspaceId)
  const restoring=!sessionToken,diag=diagnostic(workspaceId)
  diag.restore_attempt+=1;diag.restoration_state=restoring?'auth_loading':'pairing';diag.last_error_class=''
  lifecycle.info({workspace_id:workspaceId,restore_attempt:diag.restore_attempt,restoring},'company WhatsApp restore attempt started')
  let auth
  try{auth=await createCompanyAuthState(workspaceId,loadCompanyAuth,storeCompanyAuth,{allowMissing:!restoring})}catch(error){const status=Number(error?.status||0),classification=status===404?'no_auth_records':(status===409?'invalid_auth':'backend_unavailable');diag.restoration_state=classification;diag.last_error_class=classification;lifecycle.error({workspace_id:workspaceId,restore_attempt:diag.restore_attempt,...ninaErrorDetails(error),classification},'company WhatsApp auth load failed');throw error}
  const selected=await fetchLatestBaileysVersion()
  if(restoring&&!auth.restored){diag.restoration_state='invalid_auth';diag.last_error_class='company_auth_missing';throw new Error('company_auth_missing')}
  const state={workspaceId,sessionToken,socket:null,qrSvg:'',status:'connecting',sent:new Set(),retryTimer:null,closed:false,qrSequence:0}
  companySessions.set(workspaceId,state);lifecycle.info({workspace_id:workspaceId},'company WhatsApp session started')
  if(restoring){diag.restoration_state='reconnecting';await companyRuntimeState(workspaceId,'reconnecting')}
  const socket=makeWASocket({auth:auth.state,version:selected.version,browser:Browsers.ubuntu('NinaOS Company'),logger:quiet,emitOwnEvents:false,syncFullHistory:false,markOnlineOnConnect:false,shouldIgnoreJid:jid=>unsupportedChat(String(jid||''))})
  lifecycle.info({workspace_id:workspaceId,restore_attempt:diag.restore_attempt,stored_auth:auth.restored},'company WhatsApp socket created')
  state.socket=socket
  socket.ev.on('creds.update',()=>{lifecycle.info({workspace_id:workspaceId},'company WhatsApp credential update persistence started');void settle(auth.saveCreds(),'company WhatsApp credential persistence failed',workspaceId)})
  socket.ev.on('connection.update',update=>{void settle((async()=>{
    const details=closeDetails(update.lastDisconnect?.error)
    lifecycle.info({workspace_id:workspaceId,connection_state:String(update.connection||'none'),has_qr:Boolean(update.qr),status_code:details.status_code},'company WhatsApp connection update')
    if(update.qr){const qr=await createCompanyQr(restoring,update.qr);if(!qr.accepted){state.status='logged_out';state.qrSvg='';state.closed=true;diag.restoration_state='invalid_auth';diag.last_error_class='stored_auth_rejected';await companyRuntimeState(workspaceId,'invalid_auth');lifecycle.warn({workspace_id:workspaceId,classification:'invalid_auth'},'company WhatsApp restored auth rejected without exposing QR')}else{state.qrSvg=qr.qr_svg;state.qrSequence+=1;lifecycle.info({workspace_id:workspaceId,qr_sequence:state.qrSequence},'company WhatsApp QR generated')}}
    if(update.connection==='open'){await auth.flush();state.status='connected';state.qrSvg='';diag.restoration_state='connected';diag.last_error_class='';diag.last_connected_at=new Date().toISOString();const jid=normalizedJid(socket.user?.id||auth.state.creds.me?.id||''),digits=jid.split(':')[0].split('@')[0],masked=digits.length>4?`${'*'.repeat(Math.min(8,digits.length-4))}${digits.slice(-4)}`:'Linked account';await persistCompanyConnected(workspaceId,sessionToken,{masked_identity:masked});lifecycle.info({workspace_id:workspaceId,classification:'connected'},'company WhatsApp connected')}
    if(update.connection==='close'){const delay=reconnectDelay(details.status_code),classification=disconnectClassification(details.status_code),terminal=delay===null;state.qrSvg='';state.status=classification==='logged_out'?'logged_out':'connecting';diag.restoration_state=classification;diag.last_error_class=details.error_class;lifecycle.warn({workspace_id:workspaceId,...details,classification,reconnect_delay_ms:delay},'company WhatsApp disconnected');await auth.flush().catch(()=>{});if(terminal)await companyRuntimeState(workspaceId,classification);else if(!state.closed&&companySessions.get(workspaceId)===state){await companyRuntimeState(workspaceId,'reconnecting');lifecycle.info({workspace_id:workspaceId,retry_ms:delay},'company WhatsApp socket retry scheduled');state.retryTimer=setTimeout(()=>startCompanySession(workspaceId,sessionToken,{resetAuth:false}).catch(error=>lifecycle.error({workspace_id:workspaceId,...ninaErrorDetails(error)},'company WhatsApp socket retry failed')),delay)}}
  })(),'company WhatsApp connection update failed',workspaceId)})
  socket.ev.on('messages.upsert',event=>{void settle(processCompanyMessageUpsert(state,socket,event),'company WhatsApp message processing failed',workspaceId)})
  return publicCompanyStatus(workspaceId)
}
export async function persistCompanyConnected(workspaceId,sessionToken,identity,linked=companyLinked,runtimeState=companyRuntimeState){
  if(sessionToken)await linked(workspaceId,sessionToken,identity)
  return runtimeState(workspaceId,'connected')
}
export function publicCompanyStatus(workspaceId){const state=companySessions.get(workspaceId);return state?{status:state.status,qr_svg:state.qrSvg}:{status:'disconnected',qr_svg:''}}
export function publicCompanyDiagnostics(workspaceId){const value=diagnostic(workspaceId);return{restoration_state:value.restoration_state,last_error_class:value.last_error_class,restore_attempt:value.restore_attempt,last_connected_at:value.last_connected_at}}
export async function stopCompanySession(workspaceId,logout=true){const state=companySessions.get(workspaceId);companySessions.delete(workspaceId);if(!state?.socket)return;state.closed=true;if(state.retryTimer)clearTimeout(state.retryTimer);try{if(logout)await state.socket.logout();else state.socket.end(undefined)}catch(_){}}
export async function restoreCompanySessions(workspaceIds=[],starter=startCompanySession){
  const results=await Promise.allSettled(workspaceIds.map(id=>starter(id,'')))
  let failed=false
  results.forEach((result,index)=>{if(result.status==='rejected'){failed=true;lifecycle.error({workspace_id:workspaceIds[index],...ninaErrorDetails(result.reason)},'company WhatsApp restore failed')}})
  if(failed)throw new Error('company_restore_incomplete')
}
