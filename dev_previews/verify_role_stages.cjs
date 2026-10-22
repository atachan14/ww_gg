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


  const kind=process.argv[2]||'hunter';
  await navigate('http://127.0.0.1:18821/');assert.equal(await evaluate(`(async()=>{return (await fetch('/navigation')).status})()`),400);
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'${kind==='medium'?3:2}',seers:'0',mediums:'${kind==='medium'?1:0}',hunters:'${kind==='hunter'?1:0}',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})});})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));
  await evaluate(`(()=>{const original=window.fetch;window.fetch=async(...args)=>{const r=await original(...args);if(!r.ok)window.__httpFailure=await r.clone().text();return r;};})()`);
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),180000);
  const choose=async target=>{await evaluate(`document.querySelector('[data-status-target="${target}"]').click();document.querySelector('#advance-button').click()`);await wait(()=>evaluate(`window.__httpFailure||document.querySelector('main')?.dataset.navigationOccurrence==='h1'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));assert.equal(await evaluate('window.__httpFailure'),undefined);};
  await choose(3);
  const result=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h1~0&expand=1'),tree=await r.json(),leaves=[],kinds=new Set();function walk(s,p=1){for(const l of s?.leaves||[])leaves.push(l);for(const b of s?.branches||[]){kinds.add(b.kind);walk(b.children);}}walk(tree.night_stages);return {status:r.status,method:tree.night_stages?.method,stats:tree.night_stages?.stats,kinds:[...kinds],leaves,items:tree.items,headers:document.querySelector('[data-calculation-tree]').innerText};})()`);
  assert.equal(result.status,200);assert.equal(result.method,'anonymous-relational-v1');assert.ok(result.kinds.includes(kind==='hunter'?'guard_target':'medium_result'));assert.ok(result.kinds.includes('death_notice'));assert.ok(result.leaves.length);assert.equal(result.stats.ability_adapters,true);assert.ok(result.stats.relational_families<result.stats.named_prior_atoms);
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.innerText.includes('${kind==='hunter'?'護衛位置':'霊能結果'}')`));
  const headers=await evaluate(`document.querySelector('[data-calculation-tree]').innerText`);assert.ok(headers.includes(kind==='hunter'?'護衛位置':'霊能結果'));
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`),180000);
  const candidate=result.leaves.find(l=>result.items[l.node]?.alive?.length===(kind==='hunter'?3:3))||result.leaves[0];
  // Select a real rendered public Current button, preserving normal navigation.
  await wait(()=>evaluate(`!!document.querySelector('[data-tree-item="${candidate.node}"] .compact-tree-go')`));
  await evaluate(`document.querySelector('[data-tree-item="${candidate.node}"] .compact-tree-go').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'&&document.querySelector('main')?.dataset.navigationOccurrence==='h2'`));
  const analysis=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h1~0&analysis=1');return {status:r.status,data:await r.json()};})()`);assert.equal(analysis.status,200);assert.ok(analysis.data.distribution.length);
  const nav=await evaluate(`(async()=>{return await(await fetch('/navigation')).json()})()`);assert.equal(nav.board.day,2);
  await wait(()=>evaluate(`!!document.querySelector('[data-tree-item="h2~0"] .compact-tree-select')`));
  await evaluate(`document.querySelector('[data-tree-item="h2~0"] .compact-tree-select').click()`);await wait(()=>evaluate(`!!document.querySelector('[data-distribution-for="h2~0"]')`));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);
  await fs.writeFile('.artifacts/role-'+kind+'-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,200));
  await fs.writeFile('.artifacts/role-'+kind+'-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await fs.writeFile('.artifacts/role-'+kind+'-browser.json',JSON.stringify({status:result.status,kinds:result.kinds,leaves:result.leaves.length,nav,errors},null,2));assert.deepEqual(errors,[]);console.log(kind+' browser passed');await call('Browser.close',{},null).catch(()=>{});
 }finally{if(ws)ws.close();if(child.exitCode===null)child.kill();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
