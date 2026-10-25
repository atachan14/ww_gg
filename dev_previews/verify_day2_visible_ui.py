"""Bounded normal-UI seven-player Day2-night regression and phase timings."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import subprocess
from werkzeug.serving import make_server
from app import create_app
from build_vercel import build
build()
# Profiling below is process-local to this isolated preview only.
with TemporaryDirectory() as directory:
 app=create_app({'SECRET_KEY':'day2-ui-test-only','HYBRID_TABLE_PREVIEW':True,'PERSISTENT_TREE_PREVIEW':True,'GAME_TREE_PREVIEW':True,'ANONYMOUS_OWNERSHIP_PREVIEW':True,'NAVIGATION_DIRECTORY':directory})
 server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'

 from flask import request
 from time import perf_counter
 from threading import local
 import json
 from werewolf.navigation_tree import NavigationTree
 from werewolf.calculation_tree import CalculationTree
 from werewolf.information_set_forecast import InformationSetForecast
 probe_context=local();records=[]
 @app.before_request
 def probe_begin():
  probe_context.row=({'node':request.args.get('node'),'expand':request.args.get('expand'),'url':request.full_path,'started':perf_counter(),'solve_calls':0,'solve_depth':0} if request.path=='/game-tree' else None)
 def wrapped(cls,name,metric):
  original=getattr(cls,name)
  def timed(self,*args,**kwargs):
   row=getattr(probe_context,'row',None);started=perf_counter()
   try:return original(self,*args,**kwargs)
   finally:
    if row is not None:row[metric]=row.get(metric,0)+perf_counter()-started
  setattr(cls,name,timed)
 wrapped(NavigationTree,'read','navigation_read_s')
 wrapped(CalculationTree,'expand','expand_s')
 wrapped(CalculationTree,'value','value_s')
 solve=InformationSetForecast.solve
 def traced_solve(self,*args,**kwargs):
  row=getattr(probe_context,'row',None)
  if row is None:return solve(self,*args,**kwargs)
  row['solve_calls']+=1;row['solve_depth']+=1;started=perf_counter()
  try:return solve(self,*args,**kwargs)
  finally:
   row['solve_depth']-=1
   if not row['solve_depth']:row['solve_outer_s']=row.get('solve_outer_s',0)+perf_counter()-started
 InformationSetForecast.solve=traced_solve
 dumps=app.json.dumps
 def traced_json(*args,**kwargs):
  started=perf_counter();out=dumps(*args,**kwargs);row=getattr(probe_context,'row',None)
  if row is not None:row['json_s']=row.get('json_s',0)+perf_counter()-started
  return out
 app.json.dumps=traced_json
 @app.after_request
 def probe_end(response):
  row=getattr(probe_context,'row',None)
  if row is not None:
   row['active_s']=perf_counter()-row.pop('started');row['status']=response.status_code;row['bytes']=response.content_length;row.pop('solve_depth',None);records.append(row)
  return response
 s=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=s.split("  const kind=process.argv[2]")[0];suffix=s[s.index(' }finally{if(ws)'):]
 body=r"""
 const events=new Map(),timings={};await call('Network.enable');await call('Performance.enable');
 ws.addEventListener('message',event=>{const m=JSON.parse(event.data),p=m.params;if(m.method==='Network.requestWillBeSent'&&new URL(p.request.url).pathname==='/game-tree')events.set(p.requestId,{url:p.request.url,start:p.timestamp,wall:Date.now()});if(m.method==='Network.responseReceived'&&events.has(p.requestId))Object.assign(events.get(p.requestId),{headers:p.timestamp,status:p.response.status});if(m.method==='Network.loadingFinished'&&events.has(p.requestId))Object.assign(events.get(p.requestId),{end:p.timestamp,bytes:p.encodedDataLength});if(m.method==='Network.loadingFailed'&&events.has(p.requestId))Object.assign(events.get(p.requestId),{end:p.timestamp,failed:p.errorText});});
 const stage=async(name,fn)=>{const t=Date.now(),r=await fn();timings[name]=Date.now()-t;console.log(name,timings[name]);return r;};
 await stage('start',async()=>{await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',mediums:'1',seers:'1',wolves:'2',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})})`);await navigate('__BASE__/main');});

 await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`),10000);
 await stage('initial Tree ready',()=>wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'&&document.querySelectorAll('.compact-tree-board').length>0`),30000));
 await evaluate(`(()=>{const option=document.querySelector('#display-input-calculation');option.value='off';option.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 for(const [p,role] of [[1,'seer'],[2,'seer'],[3,'medium']]){console.log('fill CO',p);await evaluate(`(()=>{const co=document.querySelector('[data-table-co="${p}"]');co.value=${JSON.stringify(role)};co.dispatchEvent(new Event('change',{bubbles:true}));})()`);if(p<3){await wait(()=>evaluate(`!!document.querySelector('[data-table-target="1:${p}"]')`),10000);await evaluate(`(()=>{const t=document.querySelector('[data-table-target="1:${p}"]'),c=document.querySelector('[data-table-color="1:${p}"]');t.value='3';t.dispatchEvent(new Event('change',{bubbles:true}));c.value='white';c.dispatchEvent(new Event('change',{bubbles:true}));})()`);}}
 const old=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);
 await stage('Table Update',async()=>{await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence!==${JSON.stringify(old)}&&!boardTableDraft.isDirty()`),180000);});
 const publicValues=await evaluate(`Array.from(document.querySelectorAll('#information-panel .probability[data-fraction],.player-table .probability[data-fraction]')).map(e=>e.dataset.fraction)`);
 const before=(await call('Performance.getMetrics')).metrics;const metrics=()=>call('Performance.getMetrics');
 const origin=Date.now(),manualOwner=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);const carryIn=[...events.values()].filter(x=>!x.end);
 await evaluate(`(()=>{window.__uiProbe={longTasks:[],layoutCalls:0,seenCards:new WeakSet(),createdCards:0,layoutFunctions:{}};for(const name of ['measure','arrange','connect']){const original=TreeLayout[name];TreeLayout[name]=(...args)=>{const t=performance.now();if(name==='measure'){__uiProbe.layoutCalls++;for(const row of args[0])if(!__uiProbe.seenCards.has(row.element)){__uiProbe.seenCards.add(row.element);__uiProbe.createdCards++;}}try{return original(...args);}finally{__uiProbe.layoutFunctions[name]=(__uiProbe.layoutFunctions[name]||0)+performance.now()-t;}};}try{new PerformanceObserver(list=>{for(const x of list.getEntries())if(__uiProbe.longTasks.length<200)__uiProbe.longTasks.push({start:x.startTime,duration:x.duration});}).observe({type:'longtask',buffered:true});}catch(_){} })()`);
 let outcome='bounded-timeout',lastCount=-1,unchanged=Date.now(),state;const deadline=origin+120000;
 while(Date.now()<deadline){state=await evaluate(`(()=>{const r=document.querySelector('[data-calculation-tree]');return {navigation:r.dataset.navigationUpdate,auto:r.dataset.treeAuto,status:r.querySelector('[data-tree-status]').textContent,boards:r.querySelectorAll('.compact-tree-board').length,day2Night:r.querySelectorAll('.compact-tree-board[data-phase="2-night"]').length,actualDay2Night:[...r.querySelectorAll('.compact-tree-board[data-phase="2-night"]')].filter(e=>e.dataset.treeItem.startsWith(${JSON.stringify(manualOwner)}+'~')||e.dataset.treeItem.startsWith(${JSON.stringify(manualOwner)}+'@')).length,currentVisible:!!r.querySelector('.tree-item.current')};})()`);if(state.boards!==lastCount){lastCount=state.boards;unchanged=Date.now();}const active=[...events.values()].filter(x=>x.wall>=origin&&!x.end);if(state.navigation==='error'){outcome='error';break;}if(state.navigation==='complete'&&!state.boards&&!active.length&&Date.now()-unchanged>2000){outcome='empty-render';break;}if(state.navigation==='complete'&&state.actualDay2Night>0&&state.currentVisible&&!active.length&&Date.now()-unchanged>1200){outcome='stable';break;}await new Promise(r=>setTimeout(r,400));}
 timings.visible=Date.now()-origin;const after=(await metrics()).metrics,delta=after.filter(x=>['ScriptDuration','LayoutDuration','RecalcStyleDuration','TaskDuration'].includes(x.name)).map(x=>({name:x.name,seconds:x.value-(before.find(y=>y.name===x.name)?.value||0)}));
 const rows=[...events.values()].filter(x=>x.wall>=origin).map(x=>({...x,seconds:x.end?x.end-x.start:null}));const counts={};for(const x of rows){const key=new URL(x.url).searchParams.get('node')||'root';counts[key]=(counts[key]||0)+1;}
 const screenshot=await evaluate(`(()=>{document.querySelector('#tree-reserved').scrollIntoView();const e=document.querySelector('.compact-tree-board[data-phase="2-night"]'),f=document.querySelector('.tree-flow-frame');if(e){const scale=Number(document.querySelector('#tree-reserved').dataset.treeZoom||1);f.scrollLeft=parseFloat(e.style.left)*scale-f.clientWidth/3;f.scrollTop=parseFloat(e.style.top)*scale-f.clientHeight/3;}return !!e;})()`);await evaluate(`new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);await fs.writeFile('.artifacts/day2-ui-visible.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 const result={outcome,timings,state,screenshot,carryIn:carryIn.map(x=>({url:x.url,seconds:x.end?x.end-x.start:null})),requestCount:rows.length,completed:rows.filter(x=>x.end).length,duplicates:Object.entries(counts).filter(x=>x[1]>1),slowest:rows.filter(x=>x.seconds!==null).sort((a,b)=>b.seconds-a.seconds).slice(0,10),rendering:await evaluate('({layoutCalls:__uiProbe.layoutCalls,createdCards:__uiProbe.createdCards,layoutFunctions:__uiProbe.layoutFunctions})'),browserMetrics:delta,longTasks:await evaluate('__uiProbe.longTasks'),errors};await fs.writeFile('.artifacts/day2-ui-browser.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));assert.equal(outcome,'stable');assert.equal(state.currentVisible,true);assert.ok(state.actualDay2Night>0);assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('#information-panel .probability[data-fraction],.player-table .probability[data-fraction]')).map(e=>e.dataset.fraction)`),publicValues);assert.deepEqual(errors,[]);
 function geometry(){return evaluate(`(()=>{const rows=[...document.querySelectorAll('.compact-tree-item')];const columns=new Map();for(const r of rows){const x=r.style.left;if(!columns.has(x))columns.set(x,[]);columns.get(x).push(r);}let overlap=false;for(const rows of columns.values()){rows.sort((a,b)=>parseFloat(a.style.top)-parseFloat(b.style.top));for(let i=1;i<rows.length;i++)if(rows[i].getBoundingClientRect().top<rows[i-1].getBoundingClientRect().bottom-.5)overlap=true;}return {overlap,keys:rows.map(r=>r.dataset.treeKey)};})()`);}
 const desktopGeometry=await geometry();assert.equal(desktopGeometry.overlap,false);
 await evaluate(`document.querySelector('.compact-tree-item.current .compact-tree-select').click()`);await wait(()=>evaluate(`!!document.querySelector('.tree-inline-distribution [data-fraction]')`));await wait(()=>Promise.resolve([...events.values()].some(x=>new URL(x.url).searchParams.get('analysis')==='1'&&x.end&&x.status===200)));await evaluate(`new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await evaluate(`new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);const narrowGeometry=await geometry();assert.equal(narrowGeometry.overlap,false);assert.deepEqual(narrowGeometry.keys,desktopGeometry.keys);
 const beforeZoom=await evaluate(`JSON.stringify([...document.querySelectorAll('.compact-tree-item')].map(e=>[e.dataset.treeKey,e.style.left,e.style.top,e.style.width]))`),scale=await evaluate(`Number(document.querySelector('[data-calculation-tree]').dataset.treeZoom)`),rect=await evaluate(`(()=>{const r=document.querySelector('.tree-flow-frame').getBoundingClientRect();return {x:r.left+Math.min(200,r.width/2),y:r.top+Math.min(160,r.height/2)};})()`);
 await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:rect.x,y:rect.y,deltaX:0,deltaY:-100,modifiers:2});await evaluate(`new Promise(r=>requestAnimationFrame(r))`);assert.ok(await evaluate(`Number(document.querySelector('[data-calculation-tree]').dataset.treeZoom)>${scale}`));assert.equal(await evaluate(`JSON.stringify([...document.querySelectorAll('.compact-tree-item')].map(e=>[e.dataset.treeKey,e.style.left,e.style.top,e.style.width]))`),beforeZoom);
 await fs.writeFile('.artifacts/day2-ui-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));console.log(JSON.stringify({desktopNoOverlap:true,narrowNoOverlap:true,stableOrder:true,inlinePanel:true,zoomWorldGeometry:true}));
 // A repaint at non-unit zoom must keep world geometry and retain unchanged DOM.
 const reused=await evaluate(`(()=>{const before=[...document.querySelectorAll('.compact-tree-item')],geometry=before.map(e=>[e.dataset.treeKey,e.style.left,e.style.top,e.style.width]);document.dispatchEvent(new Event('probability-format-change'));const after=[...document.querySelectorAll('.compact-tree-item')];return {same:before.every((e,i)=>e===after[i]),geometry:JSON.stringify(geometry)===JSON.stringify(after.map(e=>[e.dataset.treeKey,e.style.left,e.style.top,e.style.width]))};})()`);assert.deepEqual(reused,{same:true,geometry:true});
 await evaluate(`document.querySelector('.compact-tree-item.current .compact-tree-go').click()`);await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'&&!document.querySelector('.compact-tree-item.current .compact-tree-go')?.disabled`),30000);assert.equal((await geometry()).overlap,false);
 // Delay an already completed response across a newer Current update. It must not paint an error or stale analysis.
 await evaluate(`(()=>{const original=window.fetch;window.__analysisReady=false;window.__releaseAnalysis=null;window.fetch=async(...args)=>{const response=await original(...args);if(String(args[0]).includes('analysis=1')&&!window.__releaseAnalysis){await new Promise(resolve=>{window.__releaseAnalysis=resolve;window.__analysisReady=true;});}return response;};window.__restoreFetch=()=>{window.fetch=original;};document.querySelector('.compact-tree-board:not(.current) .compact-tree-select').click();})()`);await wait(()=>evaluate(`window.__analysisReady`),30000);
 await evaluate(`document.querySelector('.compact-tree-item.current .compact-tree-go').click()`);await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'&&!document.querySelector('.compact-tree-item.current .compact-tree-go')?.disabled`),30000);
 await evaluate(`__releaseAnalysis();__restoreFetch()`);await evaluate(`new Promise(r=>setTimeout(r,200))`);assert.equal(await evaluate(`document.querySelector('[data-tree-status]').textContent`),'');assert.equal(await evaluate(`document.querySelector('.tree-inline-distribution')?.textContent.includes('View changed')`),false);
 // Manual root collapse must stay closed; reopening exposes only the existing chain.
 const collapsed=await evaluate(`(()=>{const hit=document.querySelector('.compact-tree-toggle[aria-expanded="true"]');window.__manualToggle=hit.dataset.treeToggle;hit.dispatchEvent(new MouseEvent('click',{bubbles:true}));return document.querySelectorAll('.compact-tree-item').length;})()`);assert.equal(collapsed,1);
 await evaluate(`new Promise(r=>setTimeout(r,200))`);assert.equal(await evaluate(`document.querySelectorAll('.compact-tree-item').length`),1);
 await evaluate(`document.querySelector('[data-tree-toggle="'+CSS.escape(__manualToggle)+'"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);await evaluate(`new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);assert.ok(await evaluate(`document.querySelectorAll('.compact-tree-item').length>1`));assert.equal((await geometry()).overlap,false);
 await call('Emulation.clearDeviceMetricsOverride');await call('Page.reload');await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'&&!!document.querySelector('.compact-tree-item.current')`),60000);assert.deepEqual(errors,[]);console.log(JSON.stringify({sameDOM:reused.same,zoomRepaint:reused.geometry,currentNavigation:true,manualCollapse:true,manualReopen:true,reload:true,staleResponse:true}));await call('Browser.close' ,{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe=Path(directory)/'check.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe)],timeout=330);assert result.returncode==0,result.returncode
 finally:
  Path('.artifacts/day2-ui-server.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
  server.shutdown();server.server_close();thread.join(3)
