import test from 'node:test'
import assert from 'node:assert/strict'

process.env.NINA_BRIDGE_RESTORE_RETRY_MS='1'
const {initializeCompanySessions}=await import('../src/startup.js')

test('company startup retries active-workspace discovery and restores without pairing',async()=>{
  let lookups=0
  const restored=[]
  const scheduled=[]
  const log={info(){},error(){}}
  const lookup=async()=>{lookups+=1;if(lookups===1)throw new Error('web starting');return['company-a']}
  const schedule=callback=>scheduled.push(callback)
  assert.equal(await initializeCompanySessions(lookup,async ids=>restored.push(...ids),schedule,log),false)
  assert.equal(scheduled.length,1)
  await scheduled[0]()
  assert.deepEqual(restored,['company-a'])
})

test('company startup retries when auth restoration is temporarily unavailable',async()=>{
  let restores=0
  const scheduled=[]
  const log={info(){},error(){}}
  const restore=async()=>{restores+=1;if(restores===1)throw new Error('auth backend starting')}
  assert.equal(await initializeCompanySessions(async()=>['company-a'],restore,callback=>scheduled.push(callback),log),false)
  await scheduled[0]()
  assert.equal(restores,2)
})
