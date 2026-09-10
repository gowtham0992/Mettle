const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/mettle/web/static/app.js', 'utf8');
function harness(response, current = true) {
  const calls = [], links = [], cleared = [];
  const context = vm.createContext({
    accessToken: 'synthetic-test-token', tokenIsCurrent: () => current,
    clearAuth: () => cleared.push(true),
    fetch: async (path, options) => { calls.push({path, options}); return response; },
    URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}},
    document: {body: {append() {}}, createElement: () => {
      const link = {click() {links.push(this);}, remove() {}}; return link;
    }}, window: {setTimeout() {}}, showToast() {},
  });
  vm.runInContext(source.slice(source.indexOf('async function request('), source.indexOf('function startFreshRecoveryFromError(')), context);
  return {context, calls, links, cleared};
}
const path = '/api/agentcore/workflows/test-workflow/packet.pdf';
test('approved PDF downloads with authorization without leaving the recovery', async () => {
  const h = harness({ok:true, status:200, headers:{get: ()=>'application/pdf'}, blob:async()=>({})});
  await h.context.downloadApprovedPacket(path);
  assert.equal(h.calls[0].options.headers.Authorization, 'Bearer synthetic-test-token');
  assert.equal(h.calls[0].options.cache, 'no-store');
  assert.equal(h.links[0].download, 'mettle-reinspection-packet.pdf');
  assert.equal(h.links[0].href, 'blob:test');
});
test('expired session does not start a packet download', async () => {
  const h = harness({}, false);
  await assert.rejects(h.context.downloadApprovedPacket(path), {code:'sign_in_required'});
  assert.equal(h.calls.length, 0);
  assert.equal(h.links.length, 0);
});
test('server session expiry and JSON errors never download a bogus PDF', async () => {
  const expired = harness({status:401});
  await assert.rejects(expired.context.downloadApprovedPacket(path), {code:'sign_in_required'});
  assert.equal(expired.cleared.length, 1);
  const failed = harness({ok:false, status:409, headers:{get: ()=>'application/json'}, json:async()=>({error:{message:'Approval required'}})});
  await assert.rejects(failed.context.downloadApprovedPacket(path), /Approval required/);
  assert.equal(failed.links.length, 0);
  const unexpected = harness({ok:true, status:200, headers:{get: ()=>'application/json'}, json:async()=>({})});
  await assert.rejects(unexpected.context.downloadApprovedPacket(path), /did not return a PDF/);
  assert.equal(unexpected.links.length, 0);
});
