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

  const n=Number(process.argv[2]||8);
  await navigate('http://127.0.0.1:18821/');assert.equal(await evaluate(`(async()=>{const r=await fetch('/navigation');return r.status})()`),400);
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:String(${n}-2),seers:'1',wolves:'1',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})});})()`);
  await navigate('http://127.0.0.1:18821/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h0'&&document.querySelector('main')?.dataset.tableInitialized==='true'`));
  const choose=async(target,expected)=>{await evaluate(`(()=>{const r=document.querySelector('input[name="target"][value="${target}"]');r.click();document.querySelector('#advance-button').click();})()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence===${JSON.stringify(expected)}&&document.querySelector('main')?.dataset.tableInitialized==='true'`));};
  await choose(n,'h1');await choose(2,'h2');
  const result=await evaluate(`(async()=>{const nav=await(await fetch('/navigation')).json(),current=await(await fetch('/game-tree?node=h2~0')).json();const response=await fetch('/game-tree?node=h1~0&expand=1'),night=await response.json();const ids=[];function walk(s){ids.push(...(s?.leaves||[]).map(r=>r.node));for(const b of s?.branches||[])walk(b.children);}walk(night.night_stages);return {nav:{phase:nav.board.phase,day:nav.board.day,alive:nav.board.alive,path:nav.path},current:{value:current.village_win,alive:current.alive,node:current.node},stage:{status:response.status,ids,unsupported:night.unsupported,budget:night.budget_kind,pending:night.pending},treeStatus:document.querySelector('[data-calculation-tree]').dataset.treeAuto};})()`);
  assert.equal(result.nav.day,2);assert.equal(result.nav.phase,'day');assert.equal(result.nav.alive.length,n-2);assert.ok(!result.nav.alive.includes(n)&&!result.nav.alive.includes(2));assert.equal(result.current.value,n===8?'3/8':'19/35');assert.equal(result.stage.status,200);assert.equal(result.stage.ids.length,6);assert.equal(new Set(result.stage.ids).size,1);
  await evaluate(`document.querySelector('#back-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h1'`));
  await evaluate(`document.querySelector('#advance-button').click()`);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'`));
  await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'})`);await fs.writeFile('.artifacts/count-'+n+'-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await new Promise(r=>setTimeout(r,200));assert.equal(await evaluate(`document.querySelectorAll('[data-player]').length`),n);
  await fs.writeFile('.artifacts/count-'+n+'-browser.json',JSON.stringify({n,result,errors},null,2));console.log(JSON.stringify({n,result,errors}));assert.deepEqual(errors,[]);await call('Browser.close',{},null).catch(()=>{});
 }finally{if(ws)ws.close();if(child.exitCode===null)child.kill();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
