"""Bounded isolated public-navigation stages, lifecycle and failure browser check."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread,Event,Lock
from time import monotonic,sleep
import subprocess,json
from werkzeug.serving import make_server
from flask import jsonify
from app import create_app
from werewolf.closed_calculation import _Node
from werewolf.calculation_budget import tick,CalculationCancelled
from build_vercel import build
build()
with TemporaryDirectory() as directory:
 app=create_app(dict(SECRET_KEY='staged-probe-only',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
 release=Event();lock=Lock();probe=dict(hold=False,started=0,cancelled=0,fail=False)
 original=_Node.forecast
 def forecast(node):
  with lock:hold=probe['hold'] and any(c!='latent' for c in node.read().public.claims);fail=probe['fail'];probe['fail']=False;probe['started']+=int(hold)
  if fail:raise ValueError('probe calculation failure')
  deadline=monotonic()+25
  try:
   while hold and not release.is_set():
    tick(0)
    if monotonic()>deadline:raise ValueError('probe release timeout')
    sleep(.01)
   return original(node)
  except CalculationCancelled:
   with lock:probe['cancelled']+=1
   raise
 _Node.forecast=forecast
 @app.get('/_probe')
 def read_probe():return jsonify(probe)
 @app.get('/_probe/<action>')
 def change_probe(action):
  if action=='hold':release.clear();probe['hold']=True
  elif action=='release':release.set();probe['hold']=False
  elif action=='fail':probe['fail']=True;release.set();probe['hold']=False
  return jsonify(probe)
 server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f'http://127.0.0.1:{server.server_port}'
 common=Path('dev_previews/verify_role_stages.cjs').read_text();prefix=common.split("  const kind=process.argv[2]")[0];suffix=common[common.index(' }finally{if(ws)'):]
 body=r"""
 await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'2',mediums:'1',seers:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);const initial=Date.now();await navigate('__BASE__/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));await wait(()=>evaluate(`document.querySelector('main').dataset.navigationCalculation==='complete'&&document.querySelector('[data-calculation-tree]').dataset.treeAuto==='complete'`),30000);console.log('initial completed',Date.now()-initial);
 await evaluate(`(()=>{const option=document.querySelector('#display-input-calculation');option.value='off';option.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 for(const player of [1,2]){await evaluate(`(()=>{const e=document.querySelector('[data-table-co="${player}"]');e.value='seer';e.dispatchEvent(new Event('change',{bubbles:true}));})()`);await wait(()=>evaluate(`!!document.querySelector('[data-table-target="1:${player}"]')`));await evaluate(`(()=>{const t=document.querySelector('[data-table-target="1:${player}"]'),c=document.querySelector('[data-table-color="1:${player}"]');t.value='3';t.dispatchEvent(new Event('change',{bubbles:true}));c.value='white';c.dispatchEvent(new Event('change',{bubbles:true}));})()`);}
 await evaluate(`fetch('/_probe/hold')`);const adopted=Date.now();await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence==='h1'&&document.querySelector('main').dataset.navigationCalculation==='running'&&!!document.querySelector('[data-pending-current]')`),10000);assert.ok(Date.now()-adopted<10000);assert.ok(await evaluate(`document.querySelectorAll('[data-value-cell="seer"] [data-fraction]').length>0`));assert.equal(await evaluate(`document.querySelector('#village-rate')?.dataset.fraction`),undefined);
 await evaluate(`window.__stable={panel:document.querySelector('#information-panel'),table:document.querySelector('#player-panel'),tree:document.querySelector('[data-calculation-tree]'),co:document.querySelector('[data-table-co="1"]')};__stable.co.focus();window.scrollTo(0,200);window.__scroll=window.scrollY;window.__anchor=__stable.co.getBoundingClientRect().top;`);await evaluate(`fetch('/_probe/release')`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationCalculation==='complete'&&document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`),30000);assert.equal(await evaluate(`__stable.co===document.querySelector('[data-table-co="1"]')&&document.activeElement===__stable.co&&__stable.tree===document.querySelector('[data-calculation-tree]')&&__stable.panel===document.querySelector('#information-panel')&&__stable.table===document.querySelector('#player-panel')`),true);const scrollState=await evaluate('({before:__scroll,after:scrollY,max:document.scrollingElement.scrollHeight-innerHeight,anchorBefore:__anchor,anchorAfter:__stable.co.getBoundingClientRect().top})');console.log('scroll',JSON.stringify(scrollState));assert.ok(Math.abs(scrollState.anchorAfter-scrollState.anchorBefore)<=1,JSON.stringify(scrollState));const values=await evaluate(`Array.from(document.querySelectorAll('#information-panel [data-fraction],[data-value-cell] [data-fraction]')).map(e=>e.dataset.fraction)`);console.log(JSON.stringify({adoptionBeforeWin:true,rolesBeforeWin:true,stableInputs:true,focus:true,scroll:true}));
 // A failed calculation must not undo or misreport the accepted public input.
 await evaluate(`fetch('/_probe/fail')`);await evaluate(`(()=>{const e=document.querySelector('[data-table-co="3"]');e.value='medium';e.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-table-update]').click();})()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence==='h2'&&document.querySelector('main').dataset.navigationCalculation==='failed'`),15000);assert.equal(await evaluate(`document.querySelector('[data-navigation-retry]').hidden`),false);assert.equal(await evaluate(`document.querySelector('[data-table-preview-status]').textContent.includes('保存できません')`),false);const revision=await evaluate(`document.querySelector('main').dataset.navigationRevision`);await evaluate(`document.querySelector('[data-navigation-retry]').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationCalculation==='complete'&&document.querySelector('[data-calculation-tree]').dataset.navigationUpdate==='complete'`),30000);assert.equal(await evaluate(`document.querySelector('main').dataset.navigationRevision`),revision);assert.equal(await evaluate(`__stable.panel===document.querySelector('#information-panel')&&__stable.table===document.querySelector('#player-panel')`),true);
 // Superseded long evaluation releases its worker and cannot overwrite a newer Current.
 await evaluate(`fetch('/_probe/hold')`);await evaluate(`(()=>{const e=document.querySelector('[data-table-co="4"]');e.value='villager';e.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-table-update]').click();})()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence==='h3'&&document.querySelector('main').dataset.navigationCalculation==='running'`),15000);await evaluate(`document.querySelector('[data-tree-item="h2~0"] .compact-tree-go').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence==='h2'&&document.querySelector('main').dataset.navigationCalculation==='complete'`),15000);assert.ok(await evaluate(`fetch('/_probe').then(r=>r.json()).then(x=>x.cancelled>0)`));const beforeReject=await evaluate(`document.querySelector('main').dataset.navigationRevision`);
 // Three truthful-or-wolf seer claims cannot fit one seer/one wolf; no valid Current is appended.
 await evaluate(`(()=>{const e=document.querySelector('[data-table-co="4"]');e.value='seer';e.dispatchEvent(new Event('change',{bubbles:true}));})()`);await wait(()=>evaluate(`!!document.querySelector('[data-table-target="1:4"]')`));await evaluate(`(()=>{const t=document.querySelector('[data-table-target="1:4"]'),c=document.querySelector('[data-table-color="1:4"]');t.value='3';t.dispatchEvent(new Event('change',{bubbles:true}));c.value='white';c.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-table-update]').click();})()`);await wait(()=>evaluate(`document.querySelector('[data-table-preview-status]').textContent.includes('保存できません')`),10000);assert.equal(await evaluate(`document.querySelector('main').dataset.navigationOccurrence`),'h2');assert.equal(await evaluate(`document.querySelector('main').dataset.navigationRevision`),beforeReject);await evaluate(`document.querySelector('[data-table-cancel]').click()`);console.log(JSON.stringify({oldWorkerCancelled:true,newCurrentNotOverwritten:true,contradictionNotAdopted:true}));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await evaluate(`new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);assert.ok(await evaluate(`document.querySelector('#player-panel').getBoundingClientRect().width<=innerWidth+1`));assert.deepEqual(errors,[]);console.log(JSON.stringify({failureAfterAdoption:true,retrySameRevision:true,stablePanelRoots:true,narrow:true}));await call('Browser.close',{},null).catch(()=>{});
 """.replace('__BASE__',base)
 try:
  script=Path(directory)/'probe.cjs';script.write_text(prefix+body+suffix,encoding='utf-8');result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(script)],timeout=150);assert result.returncode==0
 finally:
  _Node.forecast=original;release.set();server.shutdown();server.server_close();thread.join(3)
