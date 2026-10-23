"""Fresh browser profile against the normal local WW_GG server."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys
original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
suffix=suffix.replace(' }finally{if(ws)', ' }finally{if(ws?.readyState===1){try{ws.send(JSON.stringify({id:999999,method:"Browser.close"}));}catch(_){}}await new Promise(resolve=>setTimeout(resolve,250));if(ws)',1)
body=r"""
 const co=__CO__,timings={};
 async function stage(name,work,limit=330000){
  console.log('BEGIN',name,new Date().toISOString());const began=Date.now();let timer;
  try{const value=await Promise.race([work(),new Promise((_,reject)=>timer=setTimeout(()=>reject(Error('stage '+name+' exceeded '+limit+'ms')),limit))]);timings[name]=Date.now()-began;console.log('DONE',name,timings[name]+'ms');return value;}
  catch(error){console.error('FAILED_STAGE',name,'elapsed_ms',Date.now()-began,'errors',JSON.stringify(errors.slice(-3)));throw error;}
  finally{clearTimeout(timer);}
 }
 await stage('setup',async()=>{
  await navigate('http://127.0.0.1:18821/');
  await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'2',seers:'1',hunters:'1',wolves:'1',day:'random',night:'random',win_cutoff:'0',fake_reports:'random',initial_seer:'random_white'})})`);
  if(co)await evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const response=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,claims:['seer','latent','latent','latent','latent'],reports:[{acquired_day:1,published_day:1,player:1,target:2,color:'white'}]})});if(!response.ok)throw Error(await response.text());})()`);
  await evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const response=await fetch('/navigation/advance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,target:3})});if(!response.ok)throw Error(await response.text());})()`);
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('[data-viewpoint-role="hunter"]')&&document.querySelector('main')?.boardViewpointController`));
 });
 const publicCursor=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);
 const publicHunterRate=await evaluate(`document.querySelector('tr[data-player="4"] [data-value-cell="hunter"]').textContent.trim()`);
 await stage('Table_input',async()=>{
  await evaluate(`document.querySelector('[data-viewpoint-role="hunter"]').click();document.querySelector('tr[data-player="4"] .player-name').click()`);
  console.log('CONTROLLER',await evaluate(`document.querySelector('main').boardViewpointController.getState()`));
  await wait(()=>evaluate(`PersonalNavigation.context?.view.players[0]===4||document.querySelector('main').boardViewpointController.getState().mode==='viewing'`),325000);
  assert.ok(await evaluate(`PersonalNavigation.context`),'private result absent: '+await evaluate(`document.querySelector('[data-viewpoint-status]').textContent`));
 });
 const detail=await stage('Tree_projection',async()=>{
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),325000);
  return evaluate(`(async()=>{const tree=await PersonalNavigation.request('tree',{expand:true});const rows=Object.values(tree.items),eligible=row=>row.column_day===2&&row.column_phase==='day'&&row.alive.length===4&&row.public_current!==false&&!row.snapshot_only;const arrival=rows.find(row=>eligible(row)&&row.day_start)||rows.find(eligible);return {owner:tree.evaluation_trace.owner,node:arrival?.node,snapshot:tree.snapshot,items:rows.length,candidates:rows.filter(row=>row.column_day===2).slice(0,6).map(row=>({day:row.column_day,phase:row.column_phase,alive:row.alive.length,start:!!row.day_start,current:row.public_current,pending:row.pending}))};})()`);
 });
 assert.equal(detail.owner,'evaluator');assert.ok(detail.node,JSON.stringify(detail.candidates));console.log('TREE_ITEMS',detail.items);
 await stage('Current_Table',async()=>{
  await evaluate(`(async()=>{const result=await PersonalNavigation.request('current',{node:${JSON.stringify(detail.node)},snapshot:${JSON.stringify(detail.snapshot)}});await PersonalNavigation.install(result);})()`);
  await wait(()=>evaluate(`document.querySelector('#personal-navigation-seed')&&document.querySelector('#phase-title').textContent.includes('2')`));
 });
 await stage('cold_restore',async()=>{
  const privateCurrent=await evaluate(`PersonalNavigation.context.view.history.current`);
  await navigate('http://127.0.0.1:18821/main');
  await wait(()=>evaluate(`document.querySelector('#personal-navigation-seed')&&PersonalNavigation.context?.view.history.current===${JSON.stringify(privateCurrent)}`),325000);
 });
 await stage('public_return',async()=>{
  await evaluate(`document.querySelector('[data-personal-public]').click()`);
  await wait(()=>evaluate(`!PersonalNavigation.context&&!document.querySelector('#personal-navigation-seed')`));
  assert.equal(await evaluate(`document.querySelector('main').dataset.navigationOccurrence`),publicCursor);
  await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`),325000);
  assert.equal(await evaluate(`PersonalNavigation.context`),null);
  assert.equal(await evaluate(`document.querySelector('tr[data-player="4"] [data-value-cell="hunter"]').textContent.trim()`),publicHunterRate);
  const publicSnapshot=await evaluate(`(async()=>{return(await(await fetch('/game-tree')).json()).snapshot;})()`);
  assert.notEqual(publicSnapshot,detail.snapshot);
  assert.equal(await evaluate(`(async()=>{return(await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({snapshot:${JSON.stringify(detail.snapshot)},node:${JSON.stringify(publicCursor+'~0')},revision:document.querySelector('main').dataset.navigationRevision})})).status;})()`),409);
  assert.ok(await evaluate(`document.querySelectorAll('[data-tree-item]').length>1`));
 });
 assert.deepEqual(errors,[]);console.log('PASS',co?'CO':'all-hidden',JSON.stringify(timings));
 await call('Browser.close',{},null).catch(()=>{});
""".replace('__CO__','true' if '--co' in sys.argv else 'false')
with TemporaryDirectory() as directory:
 probe=Path(directory)/'smoke.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');subprocess.run(['node',str(probe)],check=True,timeout=1800)
