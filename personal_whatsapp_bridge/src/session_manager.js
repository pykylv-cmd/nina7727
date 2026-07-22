import makeWASocket, {Browsers, BufferJSON, DisconnectReason, fetchLatestBaileysVersion, initAuthCreds, jidNormalizedUser, makeCacheableSignalKeyStore, proto} from '@whiskeysockets/baileys'
import pino from 'pino'
import QRCode from 'qrcode'
import {clearAuth, inbound, linked, loadAuth, ninaErrorDetails, storeAuth} from './nina_api.js'

const lifecycle = pino({level:process.env.LOG_LEVEL || 'info',base:undefined})
const quiet = lifecycle.child({component:'baileys'},{level:process.env.BAILEYS_LOG_LEVEL || 'warn'})
export const sessions = new Map()

function revive(value) { return JSON.parse(JSON.stringify(value), BufferJSON.reviver) }
function flatten(value) { return JSON.parse(JSON.stringify(value, BufferJSON.replacer)) }
function textOf(message={}) { return message.conversation || message.extendedTextMessage?.text || '' }
function normalizedJid(value) { return value ? jidNormalizedUser(String(value)) : '' }
function unsupportedChat(jid) { return jid === 'status@broadcast' || jid.endsWith('@broadcast') || jid.endsWith('@g.us') || jid.endsWith('@newsletter') }
export function ownerJids(socketUser={},credsMe={}) {
  return new Set([socketUser.id,socketUser.lid,credsMe.id,credsMe.lid].map(normalizedJid).filter(Boolean))
}
export function normalizeStoredKey(type,value) { return type === 'app-state-sync-key' && value ? proto.Message.AppStateSyncKeyData.fromObject(value) : value }
export function disconnectDetails(error) {
  const rawCode=error?.output?.statusCode ?? error?.data?.reason ?? error?.statusCode
  const parsed=Number(rawCode)
  return {statusCode:Number.isFinite(parsed)?parsed:0,errorClass:String(error?.name || error?.constructor?.name || 'Error').slice(0,80),message:String(error?.message || error?.output?.payload?.message || 'connection closed').replace(/[\r\n]+/g,' ').slice(0,180)}
}
export function reconnectDelay(statusCode) {
  if ([DisconnectReason.loggedOut,DisconnectReason.badSession,DisconnectReason.connectionReplaced,DisconnectReason.multideviceMismatch,DisconnectReason.forbidden].includes(statusCode)) return null
  return statusCode === DisconnectReason.restartRequired ? 250 : 5000
}
export async function resolveWhatsAppVersion(fetcher=fetchLatestBaileysVersion) {
  const result=await fetcher()
  return {version:result.version,isLatest:Boolean(result.isLatest)}
}
export async function settleNonFatal(operation,onError=()=>{}) {
  try { await operation; return true } catch(error) { onError(error); return false }
}
function logInternalFailure(error,message) { lifecycle.error(ninaErrorDetails(error),message) }

export async function processMessageUpsert(state,socket,event,api=inbound,log=lifecycle) {
  const type=String(event?.type || '')
  if (type !== 'notify') { log.info({workspace_id:state.workspaceId,upsert_type:type,ignored_reason:'not_live_notify'},'personal WhatsApp message ignored'); return 0 }
  if (state.status !== 'connected') { log.info({workspace_id:state.workspaceId,upsert_type:type,ignored_reason:'not_connected'},'personal WhatsApp message ignored'); return 0 }
  let processed=0
  for (const item of event.messages || []) {
    const key=item.key || {};const id=String(key.id || '');const remote=normalizedJid(key.remoteJid);const alternate=normalizedJid(key.remoteJidAlt)
    log.info({workspace_id:state.workspaceId,upsert_type:type,from_me:Boolean(key.fromMe),has_remote_alt:Boolean(alternate)},'personal WhatsApp message received')
    let ignored=''
    if (!id) ignored='missing_message_id'
    else if (state.sent.delete(id)) ignored='nina_outbound_echo'
    else if (!remote || unsupportedChat(remote) || (alternate && unsupportedChat(alternate))) ignored='unsupported_chat'
    else if (!key.fromMe) ignored='not_owner_message'
    else if (!state.ownJids.has(remote) && !state.ownJids.has(alternate)) ignored='not_owner_self_chat'
    const text=textOf(item.message).trim()
    if (!ignored && !text) ignored='no_supported_text'
    if (ignored) { log.info({workspace_id:state.workspaceId,ignored_reason:ignored},'personal WhatsApp message ignored'); continue }
    let result
    try { result=await api({workspace_id:state.workspaceId,message_id:id,chat_jid:state.primaryJid,text,is_group:false}) }
    catch(error) { logInternalFailure(error,'personal WhatsApp inbound API failed'); continue }
    const accepted=Boolean(result?.accepted);const reply=String(result?.reply || '').trim()
    log.info({workspace_id:state.workspaceId,inbound_accepted:accepted},'personal WhatsApp inbound API completed')
    if (!accepted || !reply) { log.info({workspace_id:state.workspaceId,reply_generated:false},'personal WhatsApp reply not generated'); continue }
    log.info({workspace_id:state.workspaceId,reply_generated:true,reply_chars:reply.length},'personal WhatsApp reply generated')
    try {
      const sent=await socket.sendMessage(remote,{text:reply});const sentId=String(sent?.key?.id || '')
      if(sentId) { state.sent.add(sentId);if(state.sent.size>200) state.sent.delete(state.sent.values().next().value) }
      log.info({workspace_id:state.workspaceId,reply_sent:true},'personal WhatsApp reply sent');processed+=1
    } catch(error) { log.warn({workspace_id:state.workspaceId,error_class:String(error?.name || 'Error').slice(0,80)},'personal WhatsApp reply send failed') }
  }
  return processed
}

async function authState(workspaceId) {
  const saved = await loadAuth(workspaceId)
  const creds = saved.creds ? revive(saved.creds) : initAuthCreds()
  let writeQueue=Promise.resolve()
  const enqueue=job=>{const next=writeQueue.then(job,job);writeQueue=next.catch(()=>{});return next}
  const keys = {
    get: async (type, ids) => Object.fromEntries(ids.map(id => {
      const stored=saved[`key:${type}:${id}`]
      return [id,stored === undefined ? null : normalizeStoredKey(type,revive(stored))]
    })),
    set: async data => {
      const writes = {}
      for (const [type, values] of Object.entries(data)) for (const [id, value] of Object.entries(values || {})) {
        const key=`key:${type}:${id}`; writes[key] = value === null ? null : flatten(value)
        if(value === null) delete saved[key]; else saved[key]=writes[key]
      }
      await enqueue(()=>storeAuth(workspaceId,writes))
    }
  }
  lifecycle.info({workspace_id:workspaceId,auth_records:Object.keys(saved).length,registered:Boolean(creds.registered)},'personal WhatsApp auth loaded')
  return {state:{creds,keys:makeCacheableSignalKeyStore(keys,quiet)},saveCreds:()=>enqueue(()=>storeAuth(workspaceId,{creds:flatten(creds)})),flush:()=>writeQueue}
}

export async function startSession(workspaceId, sessionToken, options={}) {
  await stopSession(workspaceId, false)
  if (options.resetAuth && sessionToken) {
    const cleared=await clearAuth(workspaceId)
    lifecycle.info({workspace_id:workspaceId,records_cleared:cleared},'personal WhatsApp fresh pairing auth reset')
  }
  const auth = await authState(workspaceId)
  const selected=await resolveWhatsAppVersion()
  lifecycle.info({workspace_id:workspaceId,wa_version:selected.version.join('.'),latest_version:selected.isLatest},'personal WhatsApp socket starting')
  const state = {workspaceId,sessionToken,socket:null,qrSvg:'',status:'connecting',primaryJid:'',ownJids:new Set(),sent:new Set(),retryTimer:null,closed:false,qrSequence:0}
  sessions.set(workspaceId, state)
  const socket = makeWASocket({auth:auth.state,version:selected.version,browser:Browsers.ubuntu('NinaOS'),logger:quiet,emitOwnEvents:false,syncFullHistory:false,markOnlineOnConnect:false,shouldIgnoreJid:jid=>jid.endsWith('@g.us')})
  state.socket = socket
  socket.ev.on('creds.update',()=>{void settleNonFatal(auth.saveCreds(),error=>logInternalFailure(error,'personal WhatsApp credential persistence failed'))})
  socket.ev.on('connection.update',update=>{void settleNonFatal((async()=>{
    if (update.qr) {
      state.qrSvg=await QRCode.toString(update.qr,{type:'svg',margin:1,width:300});state.qrSequence+=1
      lifecycle.info({workspace_id:workspaceId,qr_sequence:state.qrSequence,registered:Boolean(auth.state.creds.registered)},'personal WhatsApp QR generated')
    }
    if (update.connection === 'open') {
      state.status='connected';state.qrSvg='';state.primaryJid=normalizedJid(socket.user?.id || auth.state.creds.me?.id || '');state.ownJids=ownerJids(socket.user || {},auth.state.creds.me || {})
      const digits=state.primaryJid.split(':')[0].split('@')[0]; const masked=digits.length>4?`${'*'.repeat(Math.min(8,digits.length-4))}${digits.slice(-4)}`:'Linked account'
      if(sessionToken) await linked(workspaceId,sessionToken,{jid:state.primaryJid,display_name:socket.user?.name || '',masked_identity:masked})
      lifecycle.info({workspace_id:workspaceId},'personal WhatsApp connected')
    }
    if (update.connection === 'close') {
      const details=disconnectDetails(update.lastDisconnect?.error)
      const delay=reconnectDelay(details.statusCode)
      state.qrSvg=''
      state.status=details.statusCode === DisconnectReason.restartRequired ? 'connecting' : (details.statusCode === DisconnectReason.loggedOut ? 'logged_out' : 'connection_lost')
      lifecycle.warn({workspace_id:workspaceId,status_code:details.statusCode,error_class:details.errorClass,error_message:details.message,reconnect_delay_ms:delay},'personal WhatsApp connection closed')
      await auth.flush().catch(()=>lifecycle.error({workspace_id:workspaceId},'personal WhatsApp auth flush failed'))
      if (delay !== null && !state.closed && sessions.get(workspaceId) === state) {
        state.retryTimer=setTimeout(()=>startSession(workspaceId,sessionToken,{resetAuth:false}).catch(error=>lifecycle.error({workspace_id:workspaceId,error_class:String(error?.name || 'Error').slice(0,80),error_message:String(error?.message || 'restart failed').slice(0,180)},'personal WhatsApp restart failed')),delay)
      }
    }
  })(),error=>logInternalFailure(error,'personal WhatsApp connection update failed'))})
  socket.ev.on('messages.upsert',event=>{void settleNonFatal(processMessageUpsert(state,socket,event),error=>logInternalFailure(error,'personal WhatsApp message processing failed'))})
  return publicStatus(workspaceId)
}

export function publicStatus(workspaceId) {
  const s=sessions.get(workspaceId); return s ? {status:s.status,qr_svg:s.qrSvg} : {status:'disconnected',qr_svg:''}
}
export async function stopSession(workspaceId, logout=true) {
  const state=sessions.get(workspaceId); sessions.delete(workspaceId)
  if (!state?.socket) return
  state.closed=true
  if(state.retryTimer) clearTimeout(state.retryTimer)
  try { if(logout) await state.socket.logout(); else state.socket.end(undefined) } catch (_) {}
}
export async function restoreSessions(workspaceIds=[], starter=startSession) {
  await Promise.all(workspaceIds.map(workspaceId=>starter(workspaceId,'').catch(error=>{
    lifecycle.error({workspace_id:workspaceId,...ninaErrorDetails(error)},'personal WhatsApp restore failed')
  })))
}
