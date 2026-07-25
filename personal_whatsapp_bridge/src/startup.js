import {backendDescriptor,ninaErrorDetails} from './nina_api.js'

const baseRetryMs=()=>Math.max(1000,Math.min(Number(process.env.NINA_BRIDGE_RESTORE_RETRY_MS||5000),30000))
export const boundedRestoreDelay=attempt=>Math.min(30000,baseRetryMs()*2**Math.min(Math.max(0,attempt-1),4))

export async function initializeCompanySessions(lookup,restore,schedule=setTimeout,log=console,attempt=1){
  log.info(JSON.stringify({event:'company WhatsApp active workspace lookup started',backend_url:backendDescriptor(),restore_attempt:attempt}))
  try{
    const ids=await lookup()
    log.info(JSON.stringify({event:'company WhatsApp active workspace lookup completed',workspace_ids:ids,workspace_count:ids.length,restore_attempt:attempt}))
    await restore(ids)
    log.info(JSON.stringify({event:'company WhatsApp restoration initialized',workspace_count:ids.length,restore_attempt:attempt}))
    return true
  }catch(error){
    const retryMs=boundedRestoreDelay(attempt),details=ninaErrorDetails(error)
    log.error(JSON.stringify({event:'company WhatsApp restoration failed',backend_url:backendDescriptor(),...details,classification:details.endpoint?'backend_unavailable':'temporary_failure',restore_attempt:attempt,retry_ms:retryMs}))
    log.info(JSON.stringify({event:'company WhatsApp restoration retry scheduled',restore_attempt:attempt+1,retry_ms:retryMs}))
    schedule(()=>{void initializeCompanySessions(lookup,restore,schedule,log,attempt+1)},retryMs)
    return false
  }
}
