// Isolated Edge/CDP verification against only the authorized local preview.
const {spawn}=require('node:child_process'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const profile=await fs.mkdtemp(path.join(os.tmpdir(),'wwgg-navigation-edge-'));
 const child=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions','--disable-background-networking','--disable-component-update','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
 let ws,session,sequence=0;const pending=new Map(),errors=[];
 async function wait(fn,ms=45000){const end=Date.now()+ms;let last;while(Date.now()<end){try{last=await fn();if(last)return last;}catch(e){last=e;}await new Promise(r=>setTimeout(r,100));}throw Error('Timed out: '+String(last));}
 try{
  const lines=await wait(async()=>{try{return (await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).trim().split('\n');}catch(_){return null;}});
  ws=new WebSocket('ws://127.0.0.1:'+lines[0]+lines[1]);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
  ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text+': '+(m.params.exceptionDetails.exception?.description||''));});
  const call=(method,params={},sid=session)=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sid?{sessionId:sid}:{})}));});
  const target=await call('Target.createTarget',{url:'about:blank'},null);session=(await call('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
  await call('Runtime.enable');await call('Page.enable');
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
  const navigate=async url=>{await call('Page.navigate',{url});const expected=new URL(url);await wait(()=>evaluate('location.origin==='+JSON.stringify(expected.origin)+'&&location.pathname==='+JSON.stringify(expected.pathname)+'&&document.readyState==="complete"'));};
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await navigate('http://127.0.0.1:18821/');
  await evaluate(`(async()=>{const r=await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',wolves:'1',seers:'1',day:'max',night:'max',fake_reports:'max'})});return r.status;})()`);
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`));
  const baseline=await evaluate(`(()=>{window.__savedTree=document.querySelector('[data-calculation-tree]');window.__savedTree.dataset.verificationIdentity='same-tree';return {occ:document.querySelector('main').dataset.navigationOccurrence,cards:document.querySelectorAll('.tree-item').length,body:document.querySelector('main').innerText.slice(0,400)}})()`);
  assert.equal(baseline.occ,'h0');assert.ok(baseline.cards>3);
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  await fs.writeFile('.artifacts/navigation-initial.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  // Actual BoardTable target selection and Footer submit, not a synthetic API-only move.
  await evaluate(`(()=>{const radio=document.querySelector('input[name="target"][value="3"]');radio.checked=true;radio.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#advance-button').click();})()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h1'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  const advanced=await evaluate(`({same:document.querySelector('[data-calculation-tree]')===window.__savedTree,occ:document.querySelector('main').dataset.navigationOccurrence,treeCards:[...document.querySelectorAll('.tree-item')].map(e=>e.textContent),status:document.querySelector('[data-tree-status]').textContent})`);
  assert.equal(advanced.same,true);assert.equal(advanced.occ,'h1');
  await evaluate(`document.querySelector('#back-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h0'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  // Exercise the established CO cell controls and report fields.
  await evaluate(`(()=>{const picker=document.querySelector('[data-table-co="1"]');picker.value='seer';picker.dispatchEvent(new Event('change',{bubbles:true}));const target=document.querySelector('[data-table-target="1:1"]');target.value='3';target.dispatchEvent(new Event('change',{bubbles:true}));const color=document.querySelector('[data-table-color="1:1"]');color.value='white';color.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await wait(()=>evaluate(`document.querySelector('[data-table-update]')?.disabled===false`));
  await evaluate(`document.querySelector('[data-table-update]').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  const updated=await evaluate(`({same:document.querySelector('[data-calculation-tree]')===window.__savedTree,labels:[...document.querySelectorAll('.tree-item')].map(e=>e.textContent),status:document.querySelector('[data-tree-status]').textContent,oldRow:document.querySelectorAll('[data-legacy-open]').length})`);
  assert.equal(updated.same,true);assert.ok(updated.labels.some(s=>s.includes('占い師CO')));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  const viewport=await evaluate(`(()=>{const f=document.querySelector('.tree-flow-frame'),r=f.getBoundingClientRect();return {x:r.left+120,y:r.top+180,scale:Number(window.__savedTree.dataset.treeZoom),left:f.scrollLeft,top:f.scrollTop,page:scrollY}})()`);
  await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:viewport.x,y:viewport.y,deltaX:0,deltaY:-100,modifiers:2});
  await wait(()=>evaluate(`Number(window.__savedTree.dataset.treeZoom)>${viewport.scale}`));
  const zoomed=await evaluate(`({scale:Number(window.__savedTree.dataset.treeZoom),page:scrollY,dpr:devicePixelRatio})`);assert.equal(zoomed.page,viewport.page);
  await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:viewport.x,y:viewport.y,deltaX:0,deltaY:-150,modifiers:0});
  await wait(()=>evaluate(`scrollY<${viewport.page}`));
  const wheel=await evaluate(`({page:scrollY,left:document.querySelector('.tree-flow-frame').scrollLeft,top:document.querySelector('.tree-flow-frame').scrollTop})`);
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  const panel=await evaluate(`(()=>{document.querySelector('.compact-tree-select').click();return true;})()`);
  await wait(()=>evaluate(`!!document.querySelector('.tree-inline-distribution')`));
  await fs.writeFile('.artifacts/navigation-after-footer.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  const geometry=await evaluate(`({headers:[...document.querySelectorAll('.phase-heading')].map(e=>e.textContent),items:document.querySelectorAll('.tree-item').length,panel:document.querySelector('.tree-inline-distribution').getBoundingClientRect().toJSON(),footer:document.querySelector('.phase-footer').getBoundingClientRect().height,area:window.__savedTree.getBoundingClientRect().height})`);
  // Closed old continuation can still be reopened and selected publicly.
  await evaluate(`(()=>{const f=document.querySelector('.tree-flow-frame');f.scrollLeft=0;f.scrollTop=0;const item=[...document.querySelectorAll('.compact-action-item')].find(e=>e.textContent.includes('[1,2,(3),4,5]'));if(!item)throw Error('Chosen representative label missing');const hit=[...document.querySelectorAll('[data-tree-toggle]')].find(h=>h.dataset.treeToggle===item.dataset.treeKey);hit.dispatchEvent(new MouseEvent('click',{bubbles:true}));})()`);
  await wait(()=>evaluate(`!!document.querySelector('[data-tree-item^="h0@h1~"] .compact-tree-go')`));
  await evaluate(`document.querySelector('[data-tree-item^="h0@h1~"] .compact-tree-go').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'`));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  const terminal=await evaluate(`({same:document.querySelector('[data-calculation-tree]')===window.__savedTree,forward:!!document.querySelector('#advance-button'),back:document.querySelector('#back-button')?.textContent})`);assert.equal(terminal.same,true);assert.equal(terminal.forward,false);assert.ok(terminal.back.includes('Day1'));
  await evaluate(`document.querySelector('#back-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h0'`));await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  const panPoint=await evaluate(`(()=>{const f=document.querySelector('.tree-flow-frame'),r=f.getBoundingClientRect();f.scrollLeft=120;f.scrollTop=30;return {x:r.left+90,y:r.top+r.height-100,left:f.scrollLeft,top:f.scrollTop}})()`);
  await call('Input.dispatchMouseEvent',{type:'mousePressed',x:panPoint.x,y:panPoint.y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:panPoint.x-50,y:panPoint.y-40,button:'left',buttons:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:panPoint.x-50,y:panPoint.y-40,button:'left',clickCount:1});
  const panned=await evaluate(`({left:document.querySelector('.tree-flow-frame').scrollLeft,top:document.querySelector('.tree-flow-frame').scrollTop,occ:document.querySelector('main').dataset.navigationOccurrence})`);assert.ok(panned.left>panPoint.left);assert.equal(panned.occ,'h0');
  await evaluate(`(()=>{const radio=document.querySelector('input[name="probability-format"][value="fraction"]');radio.checked=true;radio.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  const formatted=await evaluate(`({same:document.querySelector('[data-calculation-tree]')===window.__savedTree,win:document.querySelector('.tree-item .probability')?.textContent,left:document.querySelector('.tree-flow-frame').scrollLeft})`);assert.equal(formatted.same,true);assert.equal(formatted.left,panned.left);assert.ok(formatted.win.includes('/'));
  const nightAligned=await evaluate(`(()=>{const cards=[...document.querySelectorAll('.tree-item[data-phase="1-night"]')].filter(e=>!e.classList.contains('compact-tree-update'));return cards.length>0&&cards.every(e=>document.querySelector('.phase-heading[data-column="'+e.dataset.column+'"]')?.textContent==='Day1夜');})()`);assert.equal(nightAligned,true);
  // A real editable day-start Board advances through its one public update.
  const startGo=await evaluate(`(()=>{const go=document.querySelector('[data-tree-item*="~start:arrival:"] .compact-tree-go');if(!go)throw Error('Editable day-start Current missing');go.click();return true;})()`);
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'&&document.querySelector('main').dataset.navigationOccurrence!=='h0'`));
  const dayStart=await evaluate(`(async()=>{const r=await (await fetch('/navigation')).json();return {current:r.current,board:r.board};})()`);assert.equal(dayStart.board.day,2);
  await evaluate(`document.querySelector('#advance-button').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence!==${JSON.stringify(dayStart.current.occurrence)}&&document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  const published=await evaluate(`(async()=>{const r=await (await fetch('/navigation')).json();return {current:r.current,board:r.board};})()`);assert.deepEqual(published.board,dayStart.board);assert.notEqual(published.current.occurrence,dayStart.current.occurrence);
  await evaluate(`document.querySelector('#back-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence===${JSON.stringify(dayStart.current.occurrence)}&&document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  await evaluate(`document.querySelector('#advance-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence===${JSON.stringify(published.current.occurrence)}&&document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:400,deviceScaleFactor:1,mobile:false});await new Promise(r=>setTimeout(r,250));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  const vertical=await evaluate(`(()=>{const f=document.querySelector('.tree-flow-frame'),r=f.getBoundingClientRect();f.scrollTop=0;return {x:r.left+75,y:r.bottom-35,max:f.scrollHeight-f.clientHeight,top:f.scrollTop};})()`);
  if(vertical.max>30){await call('Input.dispatchMouseEvent',{type:'mousePressed',x:vertical.x,y:vertical.y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:vertical.x,y:vertical.y-25,button:'left',buttons:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:vertical.x,y:vertical.y-25,button:'left',clickCount:1});vertical.after=await evaluate(`document.querySelector('.tree-flow-frame').scrollTop`);assert.ok(vertical.after>vertical.top);}
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,300));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  await fs.writeFile('.artifacts/navigation-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await fs.writeFile('.artifacts/navigation-browser-probe.json',JSON.stringify({baseline,advanced,updated,zoomed,wheel,geometry,terminal,panned,formatted,nightAligned,dayStart,published,vertical,errors},null,2));
  console.log(JSON.stringify({baseline,advanced,updated,zoomed,wheel,geometry,terminal,panned,formatted,nightAligned,dayStart,published,vertical,errors}));assert.deepEqual(errors,[]);
  await call('Browser.close',{},null).catch(()=>{});
 }finally{if(ws)ws.close();if(child.exitCode===null)child.kill();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
