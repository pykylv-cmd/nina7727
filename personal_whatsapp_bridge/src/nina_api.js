const base = () => (process.env.NINA_WEB_INTERNAL_URL || '').replace(/\/$/, '')
const token = () => process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN || ''

function safeResponseBody(raw) {
  try {
    const parsed=JSON.parse(raw || '{}')
    return JSON.stringify(Object.fromEntries(['ok','error','code'].filter(key=>parsed[key] !== undefined).map(key=>[key,parsed[key]]))).slice(0,240)
  } catch { return String(raw || '').replace(/[\r\n]+/g,' ').slice(0,240) }
}

export class NinaInternalError extends Error {
  constructor(path,status,responseBody,requestKeys=[]) {
    super(`nina_internal_${status}`);this.name='NinaInternalError';this.endpoint=path;this.status=status;this.responseBody=responseBody;this.requestKeys=requestKeys
  }
}

export function ninaErrorDetails(error) {
  return {endpoint:String(error?.endpoint || ''),status:Number(error?.status || 0),response_body:String(error?.responseBody || '').slice(0,240),error_class:String(error?.name || 'Error').slice(0,80),error_message:String(error?.message || 'internal request failed').replace(/[\r\n]+/g,' ').slice(0,180)}
}

export async function ninaRequest(path, payload) {
  if (!base() || !token()) throw new Error('bridge_configuration_missing')
  const response = await fetch(base() + path, {
    method: 'POST', headers: {'content-type':'application/json', authorization:`Bearer ${token()}`},
    body: JSON.stringify(payload)
  })
  const raw=await response.text()
  if (!response.ok) throw new NinaInternalError(path,response.status,safeResponseBody(raw),Object.keys(payload || {}))
  return raw ? JSON.parse(raw) : {}
}

export async function loadAuth(workspaceId) {
  return (await ninaRequest('/internal/personal-whatsapp/auth/load', {workspace_id:workspaceId})).records || {}
}
export async function storeAuth(workspaceId, records) {
  return ninaRequest('/internal/personal-whatsapp/auth/store', {workspace_id:workspaceId, records})
}
export async function clearAuth(workspaceId) {
  const records = await loadAuth(workspaceId)
  const removals = Object.fromEntries(Object.keys(records).map(key => [key, null]))
  if (Object.keys(removals).length) await storeAuth(workspaceId, removals)
  return Object.keys(removals).length
}
export async function linked(workspaceId, sessionToken, identity) {
  return ninaRequest('/internal/personal-whatsapp/linked', {workspace_id:workspaceId, session_token:sessionToken, identity})
}
export async function inbound(payload) {
  return ninaRequest('/internal/personal-whatsapp/inbound', payload)
}
export async function activeWorkspaces() {
  return (await ninaRequest('/internal/personal-whatsapp/active', {})).workspace_ids || []
}
export async function loadCompanyAuth(workspaceId) {
  return (await ninaRequest('/internal/company-whatsapp/auth/load', {workspace_id:workspaceId})).records || {}
}
export async function storeCompanyAuth(workspaceId, records) {
  return ninaRequest('/internal/company-whatsapp/auth/store', {workspace_id:workspaceId, records})
}
export async function clearCompanyAuth(workspaceId) {
  const records = await loadCompanyAuth(workspaceId)
  const removals = Object.fromEntries(Object.keys(records).map(key => [key, null]))
  if (Object.keys(removals).length) await storeCompanyAuth(workspaceId, removals)
  return Object.keys(removals).length
}
export async function companyLinked(workspaceId, sessionToken, identity) {
  return ninaRequest('/internal/company-whatsapp/linked', {workspace_id:workspaceId, session_token:sessionToken, identity})
}
export async function companyInbound(payload) {
  return ninaRequest('/internal/company-whatsapp/inbound', payload)
}
export async function activeCompanyWorkspaces() {
  return (await ninaRequest('/internal/company-whatsapp/active', {})).workspace_ids || []
}
