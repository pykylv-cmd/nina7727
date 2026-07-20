import makeWASocket, {BufferJSON, DisconnectReason, initAuthCreds, jidNormalizedUser, makeCacheableSignalKeyStore} from '@whiskeysockets/baileys'
import pino from 'pino'
import QRCode from 'qrcode'
import {inbound, linked, loadAuth, storeAuth} from './nina_api.js'

const quiet = pino({level: process.env.LOG_LEVEL || 'warn'})
const sessions = new Map()

function revive(value) { return JSON.parse(JSON.stringify(value), BufferJSON.reviver) }
function flatten(value) { return JSON.parse(JSON.stringify(value, BufferJSON.replacer)) }
function textOf(message={}) { return message.conversation || message.extendedTextMessage?.text || '' }

async function authState(workspaceId) {
  const saved = await loadAuth(workspaceId)
  const creds = saved.creds ? revive(saved.creds) : initAuthCreds()
  const keys = {
    get: async (type, ids) => Object.fromEntries(ids.filter(id => saved[`key:${type}:${id}`] !== undefined).map(id => [id, revive(saved[`key:${type}:${id}`])])),
    set: async data => {
      const writes = {}
      for (const [type, values] of Object.entries(data)) for (const [id, value] of Object.entries(values || {})) {
        const key=`key:${type}:${id}`; writes[key] = value === null ? null : flatten(value)
        if(value === null) delete saved[key]; else saved[key]=writes[key]
      }
      await storeAuth(workspaceId, writes)
    }
  }
  return {state:{creds, keys:makeCacheableSignalKeyStore(keys, quiet)}, saveCreds:()=>storeAuth(workspaceId,{creds:flatten(creds)})}
}

export async function startSession(workspaceId, sessionToken) {
  await stopSession(workspaceId, false)
  const auth = await authState(workspaceId)
  const state = {workspaceId, sessionToken, socket:null, qrSvg:'', status:'connecting', ownJid:'', sent:new Set()}
  sessions.set(workspaceId, state)
  const socket = makeWASocket({auth:auth.state, logger:quiet, printQRInTerminal:false, syncFullHistory:false, markOnlineOnConnect:false, shouldIgnoreJid:jid=>jid.endsWith('@g.us')})
  state.socket = socket
  socket.ev.on('creds.update', auth.saveCreds)
  socket.ev.on('connection.update', async update => {
    if (update.qr) state.qrSvg = await QRCode.toString(update.qr,{type:'svg',margin:1,width:300})
    if (update.connection === 'open') {
      state.status='connected'; state.qrSvg=''; state.ownJid=jidNormalizedUser(socket.user?.id || '')
      const digits=state.ownJid.split(':')[0].split('@')[0]; const masked=digits.length>4?`${'*'.repeat(Math.min(8,digits.length-4))}${digits.slice(-4)}`:'Linked account'
      if(sessionToken) await linked(workspaceId,sessionToken,{jid:state.ownJid,display_name:socket.user?.name || '',masked_identity:masked})
    }
    if (update.connection === 'close') {
      const code=update.lastDisconnect?.error?.output?.statusCode
      state.status = code === DisconnectReason.loggedOut ? 'logged_out' : 'connection_lost'
      if (code !== DisconnectReason.loggedOut && sessions.get(workspaceId) === state) setTimeout(()=>startSession(workspaceId,sessionToken).catch(()=>{}),5000)
    }
  })
  socket.ev.on('messages.upsert', async ({messages,type}) => {
    if (type !== 'notify' || state.status !== 'connected') return
    for (const item of messages) {
      const jid=item.key?.remoteJid || ''; const id=item.key?.id || ''
      if (!id || state.sent.delete(id) || jid.endsWith('@g.us') || jid !== state.ownJid) continue
      const text=textOf(item.message).trim(); if (!text) continue
      try {
        const result=await inbound({workspace_id:workspaceId,message_id:id,chat_jid:jid,text,is_group:false})
        if (result.reply) { const sent=await socket.sendMessage(jid,{text:result.reply}); if(sent?.key?.id) state.sent.add(sent.key.id) }
      } catch (_) { quiet.warn({workspace_id:workspaceId},'personal WhatsApp inbound delivery failed') }
    }
  })
  return publicStatus(workspaceId)
}

export function publicStatus(workspaceId) {
  const s=sessions.get(workspaceId); return s ? {status:s.status,qr_svg:s.qrSvg} : {status:'disconnected',qr_svg:''}
}
export async function stopSession(workspaceId, logout=true) {
  const state=sessions.get(workspaceId); sessions.delete(workspaceId)
  if (!state?.socket) return
  try { if(logout) await state.socket.logout(); else state.socket.end(undefined) } catch (_) {}
}
export async function restoreSessions(workspaceIds=[]) { for (const id of workspaceIds) await startSession(id,'').catch(()=>{}) }
