const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/mettle/web/static/app.js', 'utf8');
function element(tag, cls, text='') {
  return {tag, textContent:text, children:[], isConnected:true,
    append(...items){this.children.push(...items);},
    replaceChildren(...items){this.children=items;}, remove(){this.isConnected=false;}};
}
async function render(request) {
  const accept = {textContent:'Accept proof', disabled:false, isConnected:true};
  const host = element('section');
  const ctx = vm.createContext({node:element, request, activeWorkflowId:'test-workflow', activeWorkflowTarget:'agentcore'});
  vm.runInContext(source.slice(source.indexOf('const evidencePhotoRequests ='),source.indexOf('function setTourIsolation(')),ctx);
  ctx.host=host; ctx.decisions={querySelectorAll:()=>[accept]};
  vm.runInContext('renderEvidencePhoto(host, {assessment_id:"evidence-one",citation_id:"1"}, decisions)',ctx);
  assert.equal(accept.disabled,true);
  await new Promise(resolve=>setImmediate(resolve));
  return {host,accept};
}
test('manual acceptance waits for the actual image to load',async()=>{
  const {host,accept}=await render(async path=>{assert.match(path,/^\/api\/agentcore\/workflows\/test-workflow\/evidence\/evidence-one\/photo$/);return {image_base64:'/9j/AAAA'};});
  const img=host.children.find(n=>n.tag==='img');
  assert.equal(img.src,'data:image/jpeg;base64,/9j/AAAA');
  assert.equal(accept.disabled,true);
  img.onload();
  assert.equal(accept.disabled,false);
});
test('failed photo retrieval leaves acceptance disabled and offers retry',async()=>{
  const {host,accept}=await render(async()=>{throw new Error('Sign in to resume your recovery.');});
  assert.equal(accept.disabled,true);
  assert.equal(host.children.some(n=>n.tag==='img'),false);
  assert.equal(host.children.at(-1).textContent,'Retry photo');
});
test('non-JPEG response cannot become an executable image URL',async()=>{
  const {host,accept}=await render(async()=>({image_base64:'data:image/svg+xml,<svg onload=alert(1)>'}));
  assert.equal(accept.disabled,true);
  assert.equal(host.children.some(n=>n.tag==='img'),false);
});
