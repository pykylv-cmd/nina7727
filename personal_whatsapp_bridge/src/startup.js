import {ninaErrorDetails} from './nina_api.js'

const restoreRetryMs=()=>Number(process.env.NINA_BRIDGE_RESTORE_RETRY_MS || 5000)

export async function initializeCompanySessions(lookup,restore,schedule=setTimeout,log=console){
  try{
    const ids=await lookup()
    await restore(ids)
    log.info(JSON.stringify({event:'company WhatsApp restoration initialized',workspace_count:ids.length}))
    return true
  }catch(error){
    const retryMs=restoreRetryMs()
    log.error(JSON.stringify({event:'company WhatsApp active-session lookup failed',...ninaErrorDetails(error),retry_ms:retryMs}))
    schedule(()=>{void initializeCompanySessions(lookup,restore,schedule,log)},retryMs)
    return false
  }
}
