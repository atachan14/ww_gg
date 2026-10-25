"""Ephemeral real-browser Footer branch navigation; no existing browser session."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import subprocess
from werkzeug.serving import make_server
from app import create_app
from build_vercel import build
build()
with TemporaryDirectory() as directory:
 app=create_app({'SECRET_KEY':'phase-footer-browser-only','HYBRID_TABLE_PREVIEW':True,'PERSISTENT_TREE_PREVIEW':True,'GAME_TREE_PREVIEW':True,'ANONYMOUS_OWNERSHIP_PREVIEW':True,'NAVIGATION_DIRECTORY':directory})
 server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
 s=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=s.split("  const kind=process.argv[2]")[0];suffix=s[s.index(' }finally{if(ws)'):]
 body=r"""
 const requests=[],assets=[];await call('Network.enable');ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.requestWillBeSent')requests.push(new URL(m.params.request.url).pathname);if(m.method==='Network.responseReceived'&&m.params.response.url.includes('/static/'))assets.push(m.params.response.status);});
 const current=()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence`);
 const nav=async(op,payload={})=>evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const r=await fetch('/navigation/${op}',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,...${JSON.stringify(payload)}})});const d=await r.json();if(!r.ok)throw Error(d.error);await BoardNavigation.install(d);return d.current.occurrence;})()`);
 const clean=async()=>{assert.equal(await evaluate(`document.querySelectorAll('.phase-footer a[href="/help"]').length`),0);assert.ok(await evaluate(`!!document.querySelector('header a[href="/help"]')`));};
 const setup=async()=>{await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);await navigate('__BASE__/main');await wait(()=>evaluate(`!!window.BoardNavigation&&document.querySelector('main')?.dataset.navigationBound==='1'`));};
 const advance=async target=>{const old=await current();if(target)await evaluate(`document.querySelector('[data-status-target="${target}"]').click()`);await evaluate(`document.querySelector('#advance-button').click()`);await wait(async()=>await current()!==old,8000);return current();};
 const back=async expected=>{await evaluate(`document.querySelector('#back-button').click()`);await wait(async()=>await current()===expected,8000);};
 await setup();await clean();assert.equal(await evaluate(`!!document.querySelector('#back-button')`),false);
 const report=(player,target,day=1,published=1)=>({acquired_day:day,published_day:published,player,target,color:'white'});
 const a=await nav('public-input',{claims:['seer','latent','latent','latent','latent'],reports:[report(1,3)]});
 const a2=await nav('public-input',{claims:['seer','seer','latent','latent','latent'],reports:[report(1,3),report(2,4)]});await clean();assert.equal(await evaluate(`!!document.querySelector('#back-button')`),false);assert.ok(await evaluate(`document.querySelector('#advance-button').textContent.includes('Day1・夜')`));
 const night=await advance(5);await clean();await nav('move',{occurrence:'h0'});const b=await nav('public-input',{claims:['latent','seer','latent','latent','latent'],reports:[report(2,4)]});await nav('move',{occurrence:night});await back(a2);assert.notEqual(await current(),b);const countBefore=await evaluate(`fetch('/navigation').then(r=>r.json()).then(d=>d.occurrences.length)`);assert.equal(await advance(),night);assert.equal(await evaluate(`fetch('/navigation').then(r=>r.json()).then(d=>d.occurrences.length)`),countBefore);
 // The Overview footer command targets the document top, retaining internal pan.
 await wait(()=>evaluate(`document.querySelector('.tree-flow-frame')?.scrollWidth>0`));const pan=await evaluate(`(()=>{const f=document.querySelector('.tree-flow-frame');f.scrollLeft=30;return f.scrollLeft;})()`);await evaluate(`window.scrollTo(0,document.body.scrollHeight)`);await wait(()=>evaluate('scrollY>100'));await evaluate(`document.querySelector('[data-scroll-to="page-top"]').click()`);await wait(()=>evaluate('scrollY<2'),3000);assert.equal(await evaluate(`document.querySelector('.tree-flow-frame').scrollLeft`),pan);
 console.log('STAGE ancestor/parallel/top passed');
 await setup();await advance(3);const n=await current();await advance(4);const first=await nav('public-input',{claims:['seer','latent','latent','latent','latent'],reports:[report(1,2,1,2)]});const latest=await nav('public-input',{claims:['latent','latent','latent','latent','latent'],reports:[report(1,2,1,2)]});await nav('move',{occurrence:n});assert.equal(await advance(),latest);await clean();assert.ok(await evaluate(`document.querySelector('#back-button').textContent.includes('Day1・夜')`));assert.ok(await evaluate(`document.querySelector('#advance-button').textContent.includes('Day2・夜')`));await navigate('__BASE__/main');assert.equal(await current(),latest);await back(n);await advance();assert.equal(await current(),latest);
 await fs.writeFile('.artifacts/phase-footer-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await fs.writeFile('.artifacts/phase-footer-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 assert.ok(requests.includes('/navigation/phase-back'));assert.ok(requests.includes('/navigation/phase-next'));assert.deepEqual(assets.filter(s=>s>=400),[]);assert.deepEqual(errors,[]);console.log(JSON.stringify({A:a,Afinal:a2,B:b,night,latestDay2:latest,previousAncestry:true,nextLatest:true,noSamePhase:true,topScroll:true,internalPan:true,reload:true,footerHelpAbsent:true,errors}));await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe=Path(directory)/'check.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe)],timeout=65);assert result.returncode==0,result.returncode
 finally:server.shutdown();server.server_close();thread.join(3)
