"""Isolated browser smoke for the supported seer Table evaluator adapter."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from werkzeug.serving import make_server
from app import create_app
from tests.test_seer_table_records import SeerTableRecordTests
import subprocess,sys
with TemporaryDirectory() as directory:
 hiddenhunterseer='--seer-hidden-hunter' in sys.argv;hiddenhunterwolf='--wolf-hidden-hunter' in sys.argv;hidden='--hidden' in sys.argv or hiddenhunterseer;maximum='--max' in sys.argv;multiwolf='--multiwolf' in sys.argv;hunterwolf='--wolf-hunter' in sys.argv or hiddenhunterwolf;maxwolf='--wolf-max' in sys.argv;wolf='--wolf' in sys.argv or multiwolf or hunterwolf or maxwolf
 if maximum:
  from tests.test_max_seer_records import MaxSeerRecordTests
  from werewolf.navigation_store import NavigationDocument
  calculation,_=MaxSeerRecordTests().night();public=NavigationDocument(calculation.data);public.game.action(3)
 elif wolf:
  if hiddenhunterwolf:
   from tests.test_hidden_hunter_wolf_table import HiddenHunterWolfTableTests
   public=HiddenHunterWolfTableTests().document()
  else:
   from tests.test_wolf_table_records import WolfTableRecordTests
   public=WolfTableRecordTests().max_document() if maxwolf else WolfTableRecordTests().hunter_document() if hunterwolf else WolfTableRecordTests().multi_document() if multiwolf else WolfTableRecordTests().document()
 elif hiddenhunterseer:
  from tests.test_hidden_hunter_seer_table import HiddenHunterSeerTableTests
  public=HiddenHunterSeerTableTests().document()
 else:public=SeerTableRecordTests().hidden_document() if hidden else SeerTableRecordTests().document()

 before=public.export()
 app=create_app(dict(TESTING=True,SECRET_KEY='isolated-seer-table',PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
 app.extensions['navigation_store'].get=lambda *_:public
 server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
  suffix=suffix.replace(' }finally{if(ws)', ' }finally{if(ws?.readyState===1){try{ws.send(JSON.stringify({id:999999,method:"Browser.close"}));}catch(_){}}await new Promise(resolve=>setTimeout(resolve,250));if(ws)',1)
  body=r"""
  await navigate('http://127.0.0.1:18821/');
  await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'4',seers:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('[data-viewpoint-role="seer"]')`));
  await evaluate(`document.querySelector('[data-viewpoint-role="seer"]').click();document.querySelector('tr[data-player="1"] .player-name').click()`);
  await wait(()=>evaluate(`PersonalNavigation.context?.view.role==='seer'`),90000);
  const tree=await evaluate(`PersonalNavigation.request('tree',{expand:true})`);
  assert.equal(tree.evaluation_trace.owner,'evaluator');
  const arrival=Object.entries(tree.items).find(([key,row])=>row.day_start&&row.alive.length===4&&!row.counterfactual);assert.ok(arrival);
  await evaluate(`(async()=>{const r=await PersonalNavigation.request('current',{node:${JSON.stringify(arrival[0])}});await PersonalNavigation.install(r);})()`);
  await wait(()=>evaluate(`document.querySelector('#personal-navigation-seed')&&PersonalNavigation.context?.view.history.current!=='h0'`));
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('#personal-navigation-seed')&&PersonalNavigation.context?.view.role==='seer'`),90000);
  await evaluate(`(async()=>{await PersonalNavigation.install(await PersonalNavigation.request('back'));})()`);
  await wait(()=>evaluate(`PersonalNavigation.context?.view.history.current==='h0'`));
  await evaluate(`document.querySelector('[data-personal-public]').click()`);
  await wait(()=>evaluate(`!PersonalNavigation.context`),90000);
  await evaluate(`document.querySelector('[data-viewpoint-role="seer"]').click();document.querySelector('tr[data-player="1"] .player-name').click()`);
  await wait(()=>evaluate(`PersonalNavigation.context?.view.role==='seer'`),90000);
  assert.deepEqual(errors,[]);console.log('PASS seer Table->recorded Tree->Current->cold restore->back->public->seer view');
  await call('Browser.close',{},null).catch(()=>{});
"""
  if wolf:
   body=body.replace('[data-viewpoint-role="seer"]','[data-viewpoint-role="wolf"]').replace('tr[data-player="1"]','tr[data-player="4"]')
   body=body.replace("view.role==='seer'","view.role==='wolf'")
   body=body.replace('PASS seer Table','PASS wolf Table').replace('->seer view','->wolf view')
  if hunterwolf:
   body=body.replace("citizens:'4',seers:'1',wolves:'1'","citizens:'2',seers:'1',hunters:'1',wolves:'1'")
   body=body.replace('PASS wolf Table','PASS hunter wolf Table deathless Current')
  if hiddenhunterseer:
   body=body.replace("citizens:'4',seers:'1',wolves:'1'", "citizens:'2',seers:'1',hunters:'1',wolves:'1'")
   body=body.replace("row.day_start&&row.alive.length===4", "row.public_current&&row.column_day===2&&row.column_phase==='day'&&row.alive.length===4")
   body=body.replace('PASS seer Table','PASS hunter hidden seer Table')
  if hiddenhunterwolf:
   body=body.replace("row.day_start&&row.alive.length===4", "row.public_current&&row.column_day===2&&row.column_phase==='day'&&row.alive.length===4")
   marker="  assert.deepEqual(errors,[]);"
   extra=r"""  const ordinary=await evaluate(`PersonalNavigation.request('tree',{expand:true})`);
  const casualty=Object.entries(ordinary.items).find(([key,row])=>row.public_current&&row.column_day===2&&row.column_phase==='day'&&row.alive.length===3);assert.ok(casualty);
  await evaluate(`(async()=>{await PersonalNavigation.install(await PersonalNavigation.request('current',{node:${JSON.stringify(casualty[0])}}));})()`);
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`!!document.querySelector('#personal-navigation-seed')&&PersonalNavigation.context?.view.role==='wolf'&&document.querySelector('main')?.dataset.tableInitialized==='true'`),90000);
  assert.equal(await evaluate(`PersonalNavigation.context.view.players.includes(4)`),true);
  const restored=await evaluate(`PersonalNavigation.request('tree',{expand:false})`);assert.equal(restored.items[restored.current_node].alive.length,3);assert.ok(restored.public_claims.every(c=>c==='latent'));
"""
   body=body.replace(marker,extra+marker)
   body=body.replace('PASS hunter wolf Table deathless Current','PASS all-hidden hunter wolf Table deathless and death Current')
  if multiwolf:
   body=body.replace("wolves:'1'","wolves:'2'")
   body=body.replace('row.alive.length===4','row.alive.length===5')
   select="document.querySelector('tr[data-player=\"4\"] .player-name').click()"
   body=body.replace(select,select+";document.querySelector('tr[data-player=\"5\"] .player-name').click()")
   marker="  assert.deepEqual(errors,[]);"
   extra=r"""  assert.deepEqual(await evaluate(`PersonalNavigation.context.view.players`),[4,5]);
  await evaluate(`document.querySelector('[data-viewpoint-role="public"]').click()`);await wait(()=>evaluate(`!PersonalNavigation.context`),90000);
  await evaluate(`document.querySelector('[data-viewpoint-role="wolf"]').click();document.querySelector('tr[data-player="4"] .player-name').click();document.querySelector('tr[data-player="6"] .player-name').click()`);
  await wait(()=>evaluate(`PersonalNavigation.context?.view.players.includes(6)`),90000);
  const alternate=await evaluate(`PersonalNavigation.request('tree',{expand:true})`);assert.notEqual(alternate.snapshot,tree.snapshot);
  assert.equal(await evaluate(`!!document.querySelector('tr[data-player="6"] [data-value-cell="final"] .probability')`),false);
  assert.equal(await evaluate(`!!document.querySelector('tr[data-player="5"] [data-value-cell="final"] .probability')`),true);
"""
   body=body.replace(marker,extra+marker)
   body=body.replace('PASS wolf Table','PASS multiwolf Table alternate-pack isolation')
  if maximum or maxwolf:
   body=body.replace("day:'random',night:'random',fake_reports:'random'","day:'max',night:'max',fake_reports:'max'")
   body=body.replace("assert.equal(tree.evaluation_trace.owner,'evaluator');","assert.equal(tree.evaluation_trace.owner,'evaluator');assert.ok(Object.values(tree.items).some(row=>row.counterfactual));")
   body=body.replace('PASS seer Table','PASS MAX seer Table')
  if hidden:
   body=body.replace('tr[data-player="1"]','tr[data-player="2"]')
   marker="  await wait(()=>evaluate(`PersonalNavigation.context?.view.role==='seer'`),90000);"
   evidence=r"""  await wait(()=>evaluate(`document.querySelector('[data-private-details="2:seer"] [data-private-target="1"]')`));
  await evaluate(`(()=>{const row=document.querySelector('[data-private-details="2:seer"]');row.querySelector('[data-private-target="1"]').value='4';const color=row.querySelector('[data-private-color="1"]');color.value='white';color.dispatchEvent(new Event('change',{bubbles:true}));})()`);
"""
   body=body.replace(marker,evidence+marker,1)
   body=body.replace('PASS seer Table','PASS hidden seer Table')
  probe=Path(directory)/'verify.cjs';probe.write_text((prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port)),encoding='utf-8')
  subprocess.run(['node',str(probe)],check=True,timeout=180)
  assert public.export()==before,'public history changed'
 finally:server.shutdown();server.server_close();worker.join()
