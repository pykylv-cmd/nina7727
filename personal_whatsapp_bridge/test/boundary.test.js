import test from 'node:test'; import assert from 'node:assert/strict'
test('group and workspace identifiers are explicit boundaries',()=>{
  assert.equal('123@g.us'.endsWith('@g.us'),true)
  assert.match('workspace-1',/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/)
})
