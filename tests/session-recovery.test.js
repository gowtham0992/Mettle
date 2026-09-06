const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/mettle/web/static/app.js', 'utf8');

test('expired session offers sign-in, not a destructive replacement or generic retry', async () => {
  const elements = Object.fromEntries(['loading','error','errorTitle','errorMessage','property','conditionLabel','progressLabel','cadence','demoDriver','retry'].map(k => [k, {}]));
  let signedIn = 0;
  const context = vm.createContext({elements, activeWorkflowTarget:'agentcore', beginLogin:async()=>{signedIn++;}});
  vm.runInContext(source.slice(source.indexOf('function showError('), source.indexOf('function showInlineWorkflowError(')), context);
  vm.runInContext('showError({code:"sign_in_required"})', context);
  assert.equal(elements.retry.textContent, 'Sign in to resume');
  assert.equal(elements.property.textContent, 'Recovery awaiting sign-in');
  assert.equal(elements.loading.hidden, true);
  assert.equal(elements.demoDriver.hidden, true);
  await vm.runInContext('retryHandler()', context);
  assert.equal(signedIn, 1);
});

test('expired token stops before any authenticated network request', async () => {
  let cleared = false;
  const context = vm.createContext({accessToken:null, tokenIsCurrent:()=>false, clearAuth:()=>{cleared=true;}, fetch:()=>{throw new Error('must not send');}});
  vm.runInContext(source.slice(source.indexOf('async function request('), source.indexOf('function startFreshRecoveryFromError(')), context);
  await assert.rejects(vm.runInContext('request("/api/agentcore/workflows/example")', context), e=>e.code==='sign_in_required');
  assert.equal(cleared,true);
});
