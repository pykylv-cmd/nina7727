const base = () => (process.env.NINA_WEB_INTERNAL_URL || '').replace(/\/$/, '')
const token = () => process.env.NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN || ''

export async function ninaRequest(path, payload) {
  if (!base() || !token()) throw new Error('bridge_configuration_missing')
  const response = await fetch(base() + path, {
    method: 'POST', headers: {'content-type':'application/json', authorization:`Bearer ${token()}`},
    body: JSON.stringify(payload)
  })
  if (!response.ok) throw new Error(`nina_internal_${response.status}`)
  return response.json()
}

export async function loadAuth(workspaceId) {
  return (await ninaRequest('/internal/personal-whatsapp/auth/load', {workspace_id:workspaceId})).records || {}
}
export async function storeAuth(workspaceId, records) {
  return ninaRequest('/internal/personal-whatsapp/auth/store', {workspace_id:workspaceId, records})
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
