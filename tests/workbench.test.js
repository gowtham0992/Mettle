const test = require('node:test');
const assert = require('node:assert/strict');
const {selectedCitation,recoverySummary} = require('../src/mettle/web/static/workbench.js');

test('explicit accepted correction stays selected while another correction is open',()=>{
  const data={citations:[{citation_id:'1',stage:'ready'},{citation_id:'2',stage:'awaiting_evidence'}]};
  assert.equal(selectedCitation(data,'1').citation_id,'1');
});
test('invalid correction links fall back to open work and empty recoveries are safe',()=>{
  assert.equal(selectedCitation({citations:[]},'anything'),null);
  assert.equal(selectedCitation({citations:[{citation_id:'1',stage:'ready'},{citation_id:'2',stage:'awaiting_evidence'}]},'missing').citation_id,'2');
});
test('held recovery takes priority over a ready-looking packet',()=>{
  const summary=recoverySummary({citations:[{stage:'ready'}],judgments:[],recovery_hold:true,packet_status:'blocked',source_mode:'workflow'});
  assert.match(summary.title,/operator/);
  assert.equal(summary.background,'Recovery safely held.');
});
test('evidence readiness never implies final approval',()=>{
  const data={citations:[{stage:'ready'}],judgments:[],packet_status:'blocked',source_mode:'workflow'};
  assert.match(recoverySummary(data).title,/last look/);
  assert.equal(recoverySummary({...data,packet_status:'approved'}).title,'The handoff is ready.');
});
test('sample activity is not presented as a scheduled cloud run',()=>{
  const data={citations:[{stage:'awaiting_evidence'}],judgments:[],source_mode:'sample',packet_status:'blocked'};
  assert.equal(recoverySummary(data).background,'Recorded sample activity.');
  assert.equal(recoverySummary({...data,source_mode:'workflow',automation_status:'scheduled'}).background,'Your next check is scheduled.');
});
