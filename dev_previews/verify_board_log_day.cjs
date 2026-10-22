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
  assert.equal(await evaluate(`(async()=>{const r=await fetch('/navigation');return r.status})()`),400);
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})});})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`));
  const choose=async target=>{await evaluate(`(()=>{const r=document.querySelector('input[name="target"][value="${target}"]');r.click();document.querySelector('#advance-button').click();})()`);};

  const logs=()=>evaluate(`(()=>{const seed=JSON.parse(document.querySelector('#public-log-seed').textContent);return {day:seed.day,visible:[...document.querySelectorAll('#system-log .board-log-item')].filter(e=>!e.hidden&&getComputedStyle(e).display!=='none').map(e=>({day:e.dataset.logDay||e.getAttribute('aria-label').match(/Day([0-9]+)/)?.[1],text:e.textContent,markup:e.outerHTML})),claims:seed.claims,seers:seed.seers};})()`);
  const publish=async(entries,expected)=>{
   await evaluate(`(()=>{const co=document.querySelector('[data-table-co="1"]');co.value='seer';co.dispatchEvent(new Event('change',{bubbles:true}));for(const [day,target,color]of ${JSON.stringify(entries)}){const t=document.querySelector('[data-table-target="'+day+':1"]');t.value=String(target);t.dispatchEvent(new Event('change',{bubbles:true}));const c=document.querySelector('[data-table-color="'+day+':1"]');c.value=color;c.dispatchEvent(new Event('change',{bubbles:true}));}})()`);
   await wait(()=>evaluate(`!document.querySelector('[data-table-update]').disabled&&document.querySelector('[data-table-preview-status]').textContent==='\u30d7\u30ec\u30d3\u30e5\u30fc'`));await evaluate(`document.querySelector('[data-table-update]').click()`);
   await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence===${JSON.stringify(expected)}&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  };
  await publish([[1,3,'white']],'h1');const day1=await logs();assert.equal(day1.visible.length,1);assert.equal(day1.visible[0].day,'1');
  await choose(3);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  await choose(4);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  const pre=await logs();assert.equal(pre.day,2);assert.equal(pre.visible.length,0);assert.equal(pre.claims[0],'seer');assert.equal(pre.seers[0].day,1);
  await publish([[2,4,'white']],'h4');const day2=await logs();assert.equal(day2.visible.length,1);assert.equal(day2.visible[0].day,'2');
  await evaluate(`document.querySelector('#system-log').scrollIntoView({block:'center'})`);await fs.writeFile('.artifacts/board-log-day-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await evaluate(`document.querySelector('#back-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));assert.equal((await logs()).visible.length,0);
  await publish([[2,2,'black']],'h5');const alternative=await logs();assert.equal(alternative.visible.length,1);
  await evaluate(`window.BoardNavigation.send('move',{occurrence:'h4'})`);const restored=await logs();assert.equal(restored.seers.find(r=>r.day===2).color,'white');assert.equal(restored.visible.length,1);
  await evaluate(`window.BoardNavigation.send('move',{occurrence:'h1'})`);assert.equal((await logs()).visible[0].day,'1');
  await evaluate(`window.BoardNavigation.send('move',{occurrence:'h0'})`);assert.equal((await logs()).visible.length,0);

  // Revisit the existing hidden root and create another history branch, without a reset.
  await choose(3);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h6'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  await choose(4);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h7'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  await publish([[1,3,'white'],[2,4,'white']],'h8');const delayed=await logs();assert.equal(delayed.visible.length,1);assert.equal(delayed.visible[0].day,'2');
  const delayedDates=await evaluate(`([...document.querySelectorAll('#system-log .board-log-item:not([hidden]) [data-log-acquired-day]')].map(e=>[e.dataset.logAcquiredDay,e.dataset.logPublishedDay]))`);
  assert.deepEqual(delayedDates,[['1','2'],['2','2']]);
  await fs.writeFile('.artifacts/board-log-day-browser.json',JSON.stringify({day1,pre,day2,alternative,restored,delayed,delayedDates,errors},null,2));console.log(JSON.stringify({day1:day1.visible.length,pre:pre.visible.length,day2:day2.visible.length,delayedDates,errors}));assert.deepEqual(errors,[]);
  await call('Browser.close',{},null).catch(()=>{});
 }finally{if(ws)ws.close();if(child.exitCode===null)child.kill();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
