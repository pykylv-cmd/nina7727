import test from 'node:test'
import assert from 'node:assert/strict'

import {sendReminder,sessions} from '../src/session_manager.js'
import {companySessions,sendCompanyReminder} from '../src/company_session_manager.js'

test('personal reminder sends once and reuses delivery result',async()=>{
  const sends=[]
  sessions.set('workspace-personal',{status:'connected',primaryJid:'371000@s.whatsapp.net',sent:new Set(),socket:{sendMessage:async(jid,payload)=>{sends.push({jid,payload});return{key:{id:'personal-reminder-1'}}}}})
  const first=await sendReminder('workspace-personal','reminder:one','Reminder text')
  const second=await sendReminder('workspace-personal','reminder:one','Reminder text')
  assert.equal(first.duplicate,false)
  assert.equal(second.duplicate,true)
  assert.equal(sends.length,1)
  sessions.delete('workspace-personal')
})

test('company reminder sends to validated recipient once',async()=>{
  const sends=[]
  companySessions.set('workspace-company',{status:'connected',sent:new Set(),socket:{sendMessage:async(jid,payload)=>{sends.push({jid,payload});return{key:{id:'company-reminder-1'}}}}})
  const first=await sendCompanyReminder('workspace-company','reminder:two','37120000001@s.whatsapp.net','Reminder text')
  const second=await sendCompanyReminder('workspace-company','reminder:two','37120000001@s.whatsapp.net','Reminder text')
  assert.equal(first.duplicate,false)
  assert.equal(second.duplicate,true)
  assert.deepEqual(sends.map(item=>item.jid),['37120000001@s.whatsapp.net'])
  companySessions.delete('workspace-company')
})

test('company reminder rejects unsafe or missing recipient',async()=>{
  companySessions.set('workspace-company',{status:'connected',sent:new Set(),socket:{sendMessage:async()=>{throw new Error('must not send')}}})
  await assert.rejects(()=>sendCompanyReminder('workspace-company','reminder:three','1@g.us','Reminder text'),/invalid_outbound_reminder/)
  companySessions.delete('workspace-company')
})
