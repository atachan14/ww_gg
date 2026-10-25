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
 const timings={};const stage=async(name,fn)=>{const t=Date.now();const r=await fn();timings[name]=Date.now()-t;console.log(name,timings[name]);return r;};
 await stage('start',async()=>{await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',mediums:'1',seers:'1',wolves:'2',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})})`);await navigate('__BASE__/main');});
 const request=async(op,payload)=>evaluate(`(async()=>{const state=await(await fetch('/navigation')).json();const r=await fetch('/navigation/${op}',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:state.revision,...${JSON.stringify(payload)}})});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d;})()`);
 await stage('public-input',()=>request('public-input',{claims:['seer','seer','medium','latent','latent','latent','latent'],reports:[{player:1,acquired_day:1,published_day:1,target:3,color:'white'},{player:2,acquired_day:1,published_day:1,target:3,color:'white'}]}));
 for(const key of ['h1~0','h1~3'])await stage('expand-'+key,async()=>{const out=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=${key}&expand=1&format=public-tree');const d=await r.json();return {status:r.status,error:d.error};})()`);assert.equal(out.status,200,JSON.stringify(out));});
 await stage('night-current',()=>request('phase-next',{target:4}));
 await stage('night-tree',async()=>{const out=await evaluate(`(async()=>{const r=await fetch('/game-tree?node=h2~0&expand=1&format=public-tree');return {status:r.status,text:await r.text()};})()`);assert.equal(out.status,200);assert.ok(!out.text.includes('Count and joint distribution disagree'));});
 await stage('render',()=>navigate('__BASE__/main'));await wait(()=>evaluate(`!!document.querySelector('main')&&!!window.BoardNavigation`));
 assert.ok(!await evaluate(`document.body.innerText.includes('Count and joint distribution disagree')`));
 await fs.writeFile('.artifacts/count-joint-tree-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 assert.deepEqual(errors,[]);console.log(JSON.stringify({timings,errors,nightCurrent:true,treeExpansion:true}));await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe=Path(directory)/'check.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe)],timeout=180);assert result.returncode==0,result.returncode
 finally:server.shutdown();server.server_close();thread.join(3)
