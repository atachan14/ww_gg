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
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})});})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`));
  const choose=async target=>{await evaluate(`(()=>{const r=document.querySelector('input[name="target"][value="${target}"]');r.click();document.querySelector('#advance-button').click();})()`);};
  await choose(1);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h1'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  await choose(2);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));

  await evaluate(`(()=>{const co=document.querySelector('[data-table-co="3"]');co.value='seer';co.dispatchEvent(new Event('change',{bubbles:true}));for(const [day,target,color]of [[1,4,'white'],[2,5,'black']]){const t=document.querySelector('[data-table-target="'+day+':3"]');t.value=String(target);t.dispatchEvent(new Event('change',{bubbles:true}));const c=document.querySelector('[data-table-color="'+day+':3"]');c.value=color;c.dispatchEvent(new Event('change',{bubbles:true}));}})()`);
  await wait(()=>evaluate(`!document.querySelector('[data-table-update]').disabled`));await evaluate(`document.querySelector('[data-table-update]').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  const counts=()=>evaluate(`({board:document.querySelectorAll('[data-tree-item="h2~0"]').length,manual:document.querySelectorAll('[data-tree-item="h3~0"]').length,incoming:[...document.querySelectorAll('[data-edge-target="public:h2~0"]')].map(e=>e.dataset.edgeProbability),paths:[...document.querySelectorAll('.compact-tree-lines path')].map(e=>e.getAttribute('d'))})`);
  assert.equal((await counts()).board,1);
  const toggle=async()=>{await evaluate(`document.querySelector('[data-tree-toggle="public:h2~0"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);await new Promise(r=>setTimeout(r,150));};
  if(!await evaluate(`document.querySelector('[data-tree-toggle="public:h2~0"]').getAttribute('aria-expanded')==='true'`))await toggle();
  await wait(async()=> (await counts()).manual===1);
  await evaluate(`document.querySelector('[data-tree-item="h2~0"] .compact-tree-select').click()`);
  await wait(()=>evaluate(`document.querySelector('[data-distribution-for="h2~0"]')?.querySelectorAll(':scope>.tree-distribution-branch,:scope>.tree-distribution-leaf').length===2`));
  const state=await counts();assert.equal(state.board,1);assert.equal(state.manual,1);assert.equal(state.incoming.length,6);assert.ok(state.paths.every(p=>!/[CQSLTA]/i.test(p)));
  const api=await evaluate(`(async()=>{const n=await(await fetch('/game-tree?node=h1~0&expand=1')).json(),rows=[];function walk(s){rows.push(...(s.leaves||[]));for(const b of s.branches||[])walk(b.children);}walk(n.night_stages);const d=await(await fetch('/game-tree?node=h2~0&analysis=1')).json();return {ids:rows.map(r=>r.node),probabilities:rows.map(r=>r.probability),distribution:d.distribution.map(r=>r.probability),bundle:d.public_bundle};})()`);
  assert.equal(api.ids.length,6);assert.ok(api.ids.every(k=>k==='h2~0'));assert.equal(api.bundle,true);assert.deepEqual(api.distribution,['1/2','1/2']);
  await evaluate(`(()=>{document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'});const f=document.querySelector('.tree-flow-frame'),b=document.querySelector('[data-tree-item="h2~0"]');f.scrollLeft=Math.max(0,parseFloat(b.style.left)-850);f.scrollTop=0;})()`);
  await fs.writeFile('.artifacts/bound-sharing-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await toggle();assert.equal((await counts()).manual,0);assert.equal((await counts()).board,1);await toggle();assert.equal((await counts()).manual,1);
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,200));assert.equal((await counts()).board,1);assert.equal((await counts()).manual,1);
  await evaluate(`(()=>{const f=document.querySelector('.tree-flow-frame'),b=document.querySelector('[data-tree-item="h2~0"]');f.scrollLeft=parseFloat(b.style.left)-60;})()`);
  await fs.writeFile('.artifacts/bound-sharing-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await evaluate(`document.querySelector('[data-tree-item="h2~0"] .compact-tree-go').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  if(!await evaluate(`document.querySelector('[data-tree-toggle="public:h2~0"]').getAttribute('aria-expanded')==='true'`))await toggle();
  await evaluate(`document.querySelector('[data-tree-item="h3~0"] .compact-tree-go').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  const posterior=await evaluate(`document.querySelector('[data-player="3"] [data-value-cell="seer"] [data-fraction]').dataset.fraction`);assert.equal(posterior,'1/3');
  await fs.writeFile('.artifacts/bound-sharing-browser.json',JSON.stringify({origin:'http://127.0.0.1:18821',board:state.board,manual:state.manual,incoming:state.incoming,api,posterior,errors},null,2));console.log(JSON.stringify({board:state.board,manual:state.manual,incoming:state.incoming,api,posterior,errors}));assert.deepEqual(errors,[]);
  await call('Browser.close',{},null).catch(()=>{});
 }finally{if(ws)ws.close();if(child.exitCode===null)child.kill();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
