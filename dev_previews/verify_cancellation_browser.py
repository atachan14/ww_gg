"""Ephemeral real browser + local threaded server; no user cookie/profile."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import subprocess,json
from werkzeug.serving import make_server
from app import create_app
from build_vercel import build
build()
app=create_app({'SECRET_KEY':'isolated-cancellation-browser-only','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':2})
server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
s=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=s.split("  const kind=process.argv[2]")[0];suffix=s[s.index(' }finally{if(ws)'):]
body=r"""
 const requests=[],assets=[];await call('Network.enable');ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.requestWillBeSent'){const r=m.params.request;requests.push({url:new URL(r.url).pathname,accept:r.headers.Accept||r.headers.accept,t:Date.now()});}if(m.method==='Network.responseReceived'&&m.params.response.url.includes('/static/'))assets.push(m.params.response.status);});
 await navigate('__BASE__/');
 await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',mediums:'1',seers:'1',hunters:'1',wolves:'2',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);
 await navigate('__BASE__/main');
 await wait(()=>requests.some(x=>x.url==='/main'&&x.accept==='application/x-ndjson'),5000).catch(e=>{console.log(JSON.stringify(requests));throw e;});
 await new Promise(r=>setTimeout(r,150));const cancelAt=Date.now();
 await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',mediums:'0',hunters:'0',wolves:'1',day:'max',night:'max'})})`);
 const latestReady=Date.now()-cancelAt;
 assert.ok(requests.some(x=>x.url==='/calculation-cancel'),'no explicit stop request');
 await navigate('__BASE__/main');
 await wait(()=>evaluate(`document.querySelector('[data-value-cell="final"]')?.hasAttribute('data-fraction')||document.querySelector('#village-rate')?.dataset.fraction==='7/15'`));
 const rate=await evaluate(`document.querySelector('#village-rate')?.dataset.fraction`);assert.equal(rate,'7/15');
 // Repeated immediate cancellation must leave the UI queue reusable.
 const repeats=await evaluate(`(async()=>{const seed=JSON.parse(document.querySelector('#public-log-seed').textContent),results=[],requests=[];let previous;
 for(let i=0;i<3;i++){previous?.abort();const c=new AbortController();previous=c;const payload={claims:['seer','latent','latent','latent','latent'],seers:[{day:1,reporter:1,target:2+i,color:'white'}],mediums:[]};
 requests.push(fetch('/table-preview',{method:'POST',signal:c.signal,headers:{Accept:'application/x-ndjson'},body:new URLSearchParams({revision:String(seed.revision),board_id:seed.board_id,request_id:String(i),payload:JSON.stringify(payload)})}).then(r=>readCalculationResponse(r)).then(r=>r.event).catch(e=>e.name));await Promise.resolve();}
 return Promise.all(requests);})()`);
 assert.deepEqual(repeats,['AbortError','AbortError','complete']);
 const status=await evaluate(`(async()=>{const r=await fetch('/main',{headers:{Accept:'application/x-ndjson'}});const result=await readCalculationResponse(r);return {status:r.status,complete:result.event};})()`);assert.equal(status.status,200);assert.equal(status.complete,'complete');
 await fs.writeFile('.artifacts/cancellation-browser.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 assert.deepEqual(errors,[]);assert.deepEqual(assets.filter(x=>x>=400),[]);console.log(JSON.stringify({latestReadyMs:latestReady,cancelRequests:requests.filter(x=>x.url==='/calculation-cancel').length,repeats,rate,errors}));
 await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
try:
 with TemporaryDirectory() as directory:
  probe=Path(directory)/'check.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8')
  result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe)],timeout=70)
  assert result.returncode==0,result.returncode
 assert not app.extensions['calculation_jobs'].active, 'request workers still registered'
 print('worker_registry_empty=true')
finally:server.shutdown();server.server_close();thread.join(3)
