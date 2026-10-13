const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('assert');
const root=process.cwd()+'/';
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{url:'https://example.test/main',runScripts:'outside-only'}),w=dom.window,d=w.document;
w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};
const seed=JSON.parse(d.querySelector('#strategy-editor').dataset.seed);seed.future_available=true;seed.allow_self_bite=true;if(!seed.roles.includes('medium'))seed.roles.push('medium');d.querySelector('#strategy-editor').dataset.seed=JSON.stringify(seed);
w.eval(fs.readFileSync(root+'static/strategy.js','utf8'));w.initializeStrategyEditor();
const click=s=>{const el=d.querySelector(s);assert(el,s);el.click()};
const value=k=>d.querySelector(`input[name="${k}"]`).value;
const original=value('disclosure_common');
assert(!d.querySelector('[data-exclusive="disclosure_common"]'));
click('[data-open="village|disclose"]');click('[data-item-remove="all"]');
click('[data-editor-apply]');assert(d.querySelector('.strategy-dialog').open);assert.equal(value('disclosure_common'),original);
click('[data-item-add="none"]');click('[data-editor-cancel]');assert.equal(value('disclosure_common'),original);
click('[data-open="village|disclose"]');click('[data-item-remove="all"]');click('[data-item-add="none"]');click('[data-editor-apply]');assert.equal(value('disclosure_common'),'none');
assert(d.querySelector('[data-scope="seer"]').textContent.includes('共通（なし）'));
click('[data-open="village|disclose"]');assert(d.querySelector('[data-item-add="white"]').disabled);assert(d.querySelector('[data-item-add="black"]').disabled);click('[data-item-remove="none"]');click('[data-item-add="all"]');click('[data-editor-apply]');assert.equal(value('disclosure_common'),'all');

assert.equal(d.querySelectorAll('#strategy-editor select').length,1);
assert(d.querySelector('[data-exclusive="model"]'));
const changeItem=(scope,option,old,next,key,expected)=>{click(`[data-open="${scope}|${option}"]`);click(`[data-item-remove="${old}"]`);click(`[data-item-add="${next}"]`);click('[data-editor-apply]');assert.equal(value(key),expected);};
changeItem('village','position','max','random','day','random');
changeItem('wolfCommon','position','max','random','night','random');
changeItem('wolfCommon','selfbite','false','true','include_self_bite','1');
changeItem('wolf','report','max','random','fake_reports','random');
changeItem('seer','disclose','inherit','none','seer_disclosure','none');
changeItem('village','disclose','all','none','disclosure_common','none');assert.equal(value('seer_disclosure'),'none');
changeItem('seer','disclose','none','inherit','seer_disclosure','inherit');
click('[data-open="seer|position"]');assert.equal(d.querySelector('.overlay-body [data-item-mode]').dataset.itemMode,'ordered');assert.equal(d.querySelectorAll('.overlay-body .candidate-card').length,2);assert(d.querySelector('[data-item-remove="unvisited"]').disabled);assert(d.querySelector('[data-item-down="unvisited"]').disabled);click('[data-editor-apply]');assert.equal(value('seer_position'),'["unvisited","uniform"]');
// Unordered inherited conditions retain their original adapter and cancel semantics.
click('[data-open="village|co"]');assert.equal(d.querySelector('.overlay-body [data-item-mode]').dataset.itemMode,'unordered');click('[data-add="counter"]');click('[data-editor-cancel]');assert(!JSON.parse(value('strategy_ui')).common.includes('counter'));
click('[data-open="village|co"]');click('[data-add="counter"]');click('[data-editor-apply]');assert(JSON.parse(value('strategy_ui')).common.includes('counter'));
click('[data-open="seer|co"]');click('[data-toggle="counter"]');click('[data-editor-apply]');assert(JSON.parse(value('strategy_ui')).roles.seer.disabled.includes('counter'));
click('[data-open="wolf|fakeSeer"]');assert(d.querySelector('[data-item-add="max"]').disabled);click('[data-item-remove="noncontradictory"]');click('[data-editor-cancel]');assert.equal(value('fake_seer_policy'),'["noncontradictory","uniform"]');
click('[data-open="wolf|fakeSeer"]');click('[data-item-remove="noncontradictory"]');click('[data-editor-apply]');assert.equal(value('fake_seer_policy'),'["uniform"]');
click('[data-open="wolf|fakeSeer"]');click('[data-item-add="noncontradictory"]');click('[data-editor-apply]');assert(d.querySelector('.strategy-dialog').open);assert.equal(value('fake_seer_policy'),'["uniform"]');click('[data-item-up="noncontradictory"]');click('[data-editor-apply]');assert.equal(value('fake_seer_policy'),'["noncontradictory","uniform"]');
const model=d.querySelector('[data-exclusive="model"]');model.value='equal';model.dispatchEvent(new w.Event('change',{bubbles:true}));assert.equal(value('model'),'equal');
if(seed.roles.includes('hunter')){
 click('[data-open="hunter|position"]');assert.equal(d.querySelector('.overlay-body [data-item-mode]').dataset.itemMode,'ordered');
 assert(d.querySelector('[data-item-add="max"]').disabled);click('[data-item-remove="uniform"]');click('[data-editor-apply]');
 assert(d.querySelector('.strategy-dialog').open);assert.equal(value('guard_position'),'["uniform"]');click('[data-editor-cancel]');
 click('[data-open="hunter|position"]');click('[data-editor-apply]');assert.equal(value('guard_position'),'["uniform"]');
}
console.log('All supported Item adapters, ordered/unordered shared panels, cancel, inheritance and model selector: PASS');w.close();

// Finished boards lock edits; model locking and unavailable policies remain respected.
for (const flags of [{finished:true},{model_locked:true,allow_self_bite:false,future_available:false}]) {
 const testDom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{url:'https://example.test/main',runScripts:'outside-only'});
 const win=testDom.window,doc=win.document,editor=doc.querySelector('#strategy-editor');
 editor.dataset.seed=JSON.stringify({...JSON.parse(editor.dataset.seed),...flags});
 win.eval(fs.readFileSync(root+'static/strategy.js','utf8'));win.initializeStrategyEditor();
 assert(doc.querySelector('[data-exclusive="model"]').disabled);
 if(flags.finished)assert([...doc.querySelectorAll('#strategy-editor [data-open]')].every(el=>el.disabled));
 else {assert(doc.querySelector('[data-open="wolfCommon|selfbite"]').disabled);assert(doc.querySelector('[data-open="seer|disclose"]').disabled);assert(doc.querySelector('[data-open="wolf|fakeSeer"]').disabled);}
 testDom.window.close();
}
console.log('Finished/model-locked/unavailable policies: PASS');
