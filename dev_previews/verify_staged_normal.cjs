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
 await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',mediums:'1',seers:'1',wolves:'2',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})})`);
 const initial=Date.now();await navigate('http://127.0.0.1:18821/main');
 await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationCalculation==='complete'&&document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),90000);
 const initialMs=Date.now()-initial;
 await evaluate(`(()=>{const e=document.querySelector('#display-input-calculation');e.value='off';e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 for(const player of [1,2]){
 await evaluate(`(()=>{const e=document.querySelector('[data-table-co="${player}"]');e.value='seer';e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await wait(()=>evaluate(`!!document.querySelector('[data-table-target="1:${player}"]')`));
 await evaluate(`(()=>{const t=document.querySelector('[data-table-target="1:${player}"]'),c=document.querySelector('[data-table-color="1:${player}"]');t.value='3';t.dispatchEvent(new Event('change',{bubbles:true}));c.value='white';c.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 }
 await evaluate(`(()=>{const e=document.querySelector('[data-table-co="3"]');e.value='medium';e.dispatchEvent(new Event('change',{bubbles:true}));window.__stages={};new MutationObserver(()=>{const m=document.querySelector('main'),s=m?.dataset.navigationCalculation;if(m?.dataset.navigationOccurrence==='h1'){if(!__stages.adopted)__stages.adopted=performance.now();if(s==='complete'&&!__stages.complete)__stages.complete=performance.now();}}).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-navigation-calculation']});window.__updateStart=performance.now();document.querySelector('[data-table-update]').click();})()`);
 await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h1'`),15000);
 assert.ok(await evaluate(`document.querySelectorAll('[data-value-cell="seer"] [data-fraction]').length>0`));
 await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationCalculation==='complete'`),160000);
 const win=await evaluate(`({adoptionMs:__stages.adopted-__updateStart,winMs:__stages.complete-__updateStart,value:document.querySelector('#village-rate')?.dataset.fraction})`);
 assert.equal(win.value,'89/224');
 await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),90000);
 const tree=await evaluate(`({totalMs:performance.now()-__updateStart,cards:document.querySelectorAll('[data-tree-item]').length})`);
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await evaluate(`new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
 assert.ok(await evaluate(`document.querySelector('#player-panel').getBoundingClientRect().width<=innerWidth+1`));
 await fs.writeFile('.artifacts/navigation-final-normal.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const before=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationCalculation==='complete'`),20000);assert.equal(await evaluate(`document.querySelector('main').dataset.navigationOccurrence`),before);assert.equal(await evaluate(`document.querySelector('#village-rate')?.dataset.fraction`),'89/224');
 assert.deepEqual(errors,[]);console.log(JSON.stringify({initialMs,...win,...tree,reload:true,narrow:true,errors}));await call('Browser.close',{},null).catch(()=>{});
 }finally{if(ws)ws.close();if(child.exitCode===null)child.kill();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
