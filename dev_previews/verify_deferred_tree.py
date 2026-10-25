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
 const timings={},requests=[];await call('Network.enable');await call('Performance.enable');ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.requestWillBeSent'&&m.params.request.url.includes('/game-tree'))requests.push(m.params.request.url);});
 const stage=async(name,fn)=>{const t=Date.now();const r=await fn();timings[name]=Date.now()-t;console.log(name,timings[name]);return r;};
 await stage('start',async()=>{await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',mediums:'1',seers:'1',wolves:'2',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})})`);await navigate('__BASE__/main');});
 await stage('public-input',()=>evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const r=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,claims:['seer','seer','medium','latent','latent','latent','latent'],reports:[{player:1,acquired_day:1,published_day:1,target:3,color:'white'},{player:2,acquired_day:1,published_day:1,target:3,color:'white'}]})});if(!r.ok)throw Error(await r.text());return r.status;})()`));
 const fetchTree=async node=>evaluate(`(async()=>{const r=await fetch('/game-tree?expand=1&format=public-tree&defer_analysis=1&node='+encodeURIComponent(${JSON.stringify(node)}));const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d;})()`);
 const first=await stage('day-root',()=>fetchTree('h1~0'));const night=await stage('day1-night',()=>fetchTree('h1~3'));
 let candidate=null;const queue=Object.values(night.items||{}).filter(x=>x.day===2&&x.phase==='day'&&x.public_current!==false&&!x.counterfactual&&!x.winner),seen=new Set();
 for(let i=0;i<queue.length&&seen.size<12;i++){const item=queue[i];if(seen.has(item.node)||item.win_certificate)continue;seen.add(item.node);const d=await stage('day2-expand-'+seen.size,()=>fetchTree(item.node));candidate=Object.values(d.items||{}).find(x=>x.day===2&&x.phase==='night'&&x.public_current!==false&&!x.counterfactual&&!x.winner&&!x.win_certificate);if(candidate)break;queue.push(...Object.values(d.items||{}).filter(x=>x.day===2&&x.phase==='day'&&x.public_current!==false&&!x.counterfactual&&!x.winner));}
 assert.ok(candidate,'No bounded Day2 night found');const expanded=await stage('day2-night',()=>fetchTree(candidate.node));
 await stage('Current',()=>evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const r=await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({node:${JSON.stringify(candidate.node)},snapshot:${JSON.stringify(expanded.snapshot)},revision:before.revision})});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));await BoardNavigation.install(d);return r.status;})()`));
 await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`),45000);await evaluate(`document.querySelector('#tree-reserved').scrollIntoView()`);
 const currentVisible=await evaluate(`!!document.querySelector('.tree-item.current .compact-tree-select')`);console.log('currentVisible',currentVisible);const beforeAnalysis=requests.length;await evaluate(`(document.querySelector('.tree-item.current .compact-tree-select')||document.querySelector('.compact-tree-board .compact-tree-select')).click()`);await wait(()=>evaluate(`document.querySelector('.tree-inline-distribution')?.textContent.length>5`));await wait(()=>Promise.resolve(requests.slice(beforeAnalysis).some(url=>new URL(url).searchParams.get('analysis')==='1')));
 const metrics=(await call('Performance.getMetrics')).metrics.filter(m=>['ScriptDuration','LayoutDuration','TaskDuration','RecalcStyleDuration'].includes(m.name));
 assert.ok(!await evaluate(`document.body.innerText.includes('Count and joint distribution disagree')`));assert.deepEqual(errors,[]);
 await fs.writeFile('.artifacts/deferred-tree-browser.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 console.log(JSON.stringify({timings,target:candidate.node,currentVisible,metrics,treeRequests:requests.length,deferredRequests:requests.filter(u=>u.includes('defer_analysis=1')).length,analysisRequests:requests.filter(u=>new URL(u).searchParams.get('analysis')==='1').length,errors}));await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe=Path(directory)/'check.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe)],timeout=240);assert result.returncode==0,result.returncode
 finally:server.shutdown();server.server_close();thread.join(3)
