"""Bounded actual-browser verification of serialized seven-player MAX Current."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from werkzeug.serving import make_server
from app import create_app
import subprocess,json
from time import perf_counter
with TemporaryDirectory() as directory:
 app=create_app(dict(TESTING=True,SECRET_KEY='seven-max-record-browser',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
 setup_start=perf_counter()
 from tests.test_max_hidden_count_records import MaxHiddenCountRecordsTests
 from werewolf.navigation_tree import NavigationTree
 from werewolf.navigation_store import NavigationDocument
 fixture=MaxHiddenCountRecordsTests();public=fixture.document();public.game.action(6);view=NavigationTree(public);shown=view.read(view.current_key(),True)
 key=next(row['node'] for row in fixture.leaves(shown['night_stages']) if not shown['items'][row['node']]['winner']);view.select(key)
 public=NavigationDocument.restore(json.loads(json.dumps(public.export())))
 app.extensions['navigation_store'].get=lambda *_:public
 print(json.dumps(dict(phase='seed-and-serialized-cold-restore',seconds=round(perf_counter()-setup_start,3))),flush=True)
 server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
  suffix=suffix.replace(' }finally{if(ws)', ' }finally{if(ws?.readyState===1){try{ws.send(JSON.stringify({id:999999,method:"Browser.close"}));}catch(_){}}await new Promise(resolve=>setTimeout(resolve,250));if(ws)',1)
  body=r"""
 await call('Page.addScriptToEvaluateOnNewDocument',{source:`window.__treePerformance={layoutCalls:0,layoutMs:0,longTasks:[]};new PerformanceObserver(list=>{for(const e of list.getEntries())window.__treePerformance.longTasks.push(e.duration);}).observe({type:'longtask',buffered:true});Object.defineProperty(window,'TreeLayout',{configurable:true,set(value){for(const key of ['arrange','connect']){const original=value[key];value[key]=function(...args){const t=performance.now();try{return original.apply(this,args);}finally{window.__treePerformance.layoutCalls++;window.__treePerformance.layoutMs+=performance.now()-t;}};}Object.defineProperty(window,'TreeLayout',{value,writable:true,configurable:true});}});`});
 let last=Date.now();const mark=phase=>{const now=Date.now();console.log(JSON.stringify({phase,seconds:(now-last)/1000}));last=now;};
 await navigate('http://127.0.0.1:18821/');
 await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',mediums:'1',wolves:'2',day:'max',night:'max',fake_reports:'max',win_cutoff:'0'})})`);
 await navigate('http://127.0.0.1:18821/main');mark('main-response-and-assets');
 await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),120000);mark('full-auto-tree');
 console.log(JSON.stringify({phase:'browser-metrics',...await evaluate(`({...window.__treePerformance,treeRequests:performance.getEntriesByType('resource').filter(e=>e.name.includes('/game-tree')).map(e=>({path:new URL(e.name).pathname+new URL(e.name).search,ms:e.duration,bytes:e.encodedBodySize})),cards:document.querySelectorAll('[data-tree-item]').length})`)}));
 const current=await evaluate(`fetch('/navigation').then(r=>r.json())`);assert.equal(current.board.day,2);assert.equal(current.board.alive.length,5);assert.ok(!current.board.alive.includes(6));
 const result=await evaluate(`fetch('/game-tree?expand=1').then(r=>r.json())`);assert.equal(result.village_win,'8/35');
 assert.equal(await evaluate(`Array.from(document.querySelectorAll('.phase-heading')).some(e=>/霊能結果|占い位置|占い結果/.test(e.textContent))`),false);
 mark('Current-and-root-verification');
 await evaluate(`document.querySelector('[data-calculation-tree]').scrollIntoView({block:'start'});new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
 await fs.writeFile(path.resolve('.artifacts/max-hidden-seven-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{captureBeyondViewport:false})).data,'base64'));
 assert.deepEqual(errors,[]);console.log('PASS original seven MAX serialized-cold Day2 Current -> full auto Tree/no irrelevant columns/root8/35; no JS errors');
 await call('Browser.close',{},null).catch(()=>{});
"""
  probe=Path(directory)/'verify.cjs';probe.write_text((prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port)),encoding='utf-8');subprocess.run(['node',str(probe)],check=True,timeout=180)
 finally:server.shutdown();server.server_close();worker.join()
