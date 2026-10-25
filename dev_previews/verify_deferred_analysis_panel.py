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
 app=create_app({'SECRET_KEY':'phase-footer-browser-only','HYBRID_TABLE_PREVIEW':True,'PERSISTENT_TREE_PREVIEW':True,'GAME_TREE_PREVIEW':True,'ANONYMOUS_OWNERSHIP_PREVIEW':False,'NAVIGATION_DIRECTORY':directory})
 server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
 s=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=s.split("  const kind=process.argv[2]")[0];suffix=s[s.index(' }finally{if(ws)'):]
 body=r"""
 const responses=[];await call('Network.enable');ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.responseReceived'&&new URL(m.params.response.url).searchParams.get('analysis')==='1')responses.push(m.params.response.url);});
 await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);await navigate('__BASE__/main');
 await evaluate(`(async()=>{const b=await(await fetch('/navigation')).json();const r=await fetch('/navigation/advance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:b.revision,target:1})});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));await BoardNavigation.install(d);})()`);
 await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`));await evaluate(`document.querySelector('#tree-reserved').scrollIntoView()`);await wait(()=>evaluate(`!!document.querySelector('.tree-item.current .compact-tree-select')`));await evaluate(`document.querySelector('.tree-item.current .compact-tree-select').click()`);
 await wait(()=>Promise.resolve(responses.length));await wait(()=>evaluate(`document.querySelector('.tree-inline-distribution')?.querySelectorAll('[data-fraction="1/3"]').length===2`));
 assert.ok(responses.every(u=>u.includes('defer_analysis=1')));assert.deepEqual(errors,[]);console.log(JSON.stringify({currentVisible:true,explicitAnalysis:true,exactConditionalValues:'1/3,1/3',deferredAnalysisFlag:true,errors}));await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe=Path(directory)/'check.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe)],timeout=240);assert result.returncode==0,result.returncode
 finally:server.shutdown();server.server_close();thread.join(3)
