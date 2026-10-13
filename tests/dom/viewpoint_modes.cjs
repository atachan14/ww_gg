const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('assert');
(async()=>{
 const dom=new JSDOM(`<main><table class="player-table"><tbody>${[1,2,3,4].map(id=>`<tr data-player="${id}"><td class="player-name">Player${id}</td><td><button class="co">CO</button></td><td><button class="life" ${id===1?'disabled':''}>生死</button></td></tr>`).join('')}</tbody></table><button data-viewpoint-role="public">全体</button><button data-viewpoint-role="wolf">狼視点</button><button id="next">進む</button></main>`,{runScripts:'outside-only'});
 const w=dom.window,d=w.document;w.eval(fs.readFileSync('static/board_viewpoint.js','utf8'));
 let loads=[],shown=[],restored=0,resolve,edited=0;
 d.querySelectorAll('.life,.co').forEach(b=>b.addEventListener('click',()=>edited++));
 const controller=w.createBoardViewpointController({root:d.querySelector('main'),roles:{wolf:{label:'狼視点',required:2,combinations:[[1,2],[2,3]]}},load:args=>{loads.push(args);return new Promise(r=>resolve=r)},restore:()=>restored++,show:r=>shown.push(r)});
 const wolf=d.querySelector('[data-viewpoint-role="wolf"]'),all=d.querySelector('[data-viewpoint-role="public"]');
 wolf.click();assert.equal(wolf.textContent,'狼視点（0/2）');assert(d.querySelector('#next').disabled);assert(d.querySelector('.co').disabled);
 const row=id=>d.querySelector(`tr[data-player="${id}"]`);
 row(4).click();assert.equal(controller.getState().selected.length,0);
 row(1).click();assert.equal(wolf.textContent,'狼視点（1/2）');assert(row(1).classList.contains('viewpoint-selected'));row(1).click();assert.equal(controller.getState().selected.length,0);
 row(1).click();row(2).click();assert.equal(loads.length,1);assert.equal(controller.getState().mode,'loading');
 all.click();resolve({stale:true});await new Promise(r=>setImmediate(r));assert.equal(shown.length,0);assert(!d.querySelector('#next').disabled);assert(d.querySelector('.life').disabled);
 wolf.click();row(2).click();row(3).dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));resolve({win:'private'});await new Promise(r=>setImmediate(r));assert.equal(controller.getState().mode,'viewing');assert.equal(shown.length,1);
 row(2).click();assert.equal(controller.getState().mode,'viewing');assert.equal(edited,0);assert(d.querySelector('.co').disabled);
 wolf.click();assert.equal(controller.getState().mode,'selecting');assert.equal(controller.getState().selected.length,0);
 controller.destroy();assert.equal(controller.getState().mode,'public');assert(!d.querySelector('.co').disabled);dom.window.close();console.log('Viewpoint modes, locks, full-row selection, dead teammate, impossible candidates, stale responses: PASS');
})().catch(error=>{console.error(error);process.exit(1)});
