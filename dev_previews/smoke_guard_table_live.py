"""Fresh browser profile against the normal local WW_GG server."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys
original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
body=r"""
 await navigate('http://127.0.0.1:18821/');
 await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'2',seers:'1',hunters:'1',wolves:'1',day:'random',night:'random',win_cutoff:'0',fake_reports:'random',initial_seer:'random_white'})})`);
 await evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const response=await fetch('/navigation/public-input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,claims:['seer','latent','latent','latent','latent'],reports:[{acquired_day:1,published_day:1,player:1,target:2,color:'white'}]})});if(!response.ok)throw Error(await response.text());})()`);
 await evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const response=await fetch('/navigation/advance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,target:3})});if(!response.ok)throw Error(await response.text());})()`);
 await navigate('http://127.0.0.1:18821/main');
 await wait(()=>evaluate(`document.querySelector('[data-viewpoint-role="hunter"]')&&document.querySelector('main')?.boardViewpointController`));
 console.log('READY real Table controller');
 const publicCursor=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);
 await evaluate(`document.querySelector('[data-viewpoint-role="hunter"]').click();document.querySelector('tr[data-player="4"] .player-name').click()`);
 console.log('SELECTED',await evaluate(`document.querySelector('main').boardViewpointController.getState()`));
 await wait(()=>evaluate(`PersonalNavigation.context?.view.players[0]===4||document.querySelector('main').boardViewpointController.getState().mode==='viewing'`),90000).catch(async error=>{throw Error(error.message+'; browser errors='+JSON.stringify(errors)+'; state='+JSON.stringify(await evaluate(`({mode:document.querySelector('main').boardViewpointController.getState(),status:document.querySelector('[data-viewpoint-status]').textContent})`)));});
 assert.ok(await evaluate(`PersonalNavigation.context`),'private result absent: '+await evaluate(`document.querySelector('[data-viewpoint-status]').textContent`));
 const tree=await evaluate(`PersonalNavigation.request('tree',{expand:true})`);assert.equal(tree.evaluation_trace.owner,'evaluator');
 const arrival=Object.values(tree.items).find(row=>row.day_start&&row.alive.length===4);assert.ok(arrival);
 await evaluate(`(async()=>{const result=await PersonalNavigation.request('current',{node:${JSON.stringify(arrival.node)},snapshot:${JSON.stringify(tree.snapshot)}});await PersonalNavigation.install(result);})()`);
 await wait(()=>evaluate(`document.querySelector('#personal-navigation-seed')&&document.querySelector('#phase-title').textContent.includes('2')`));
 await evaluate(`document.querySelector('[data-personal-public]').click()`);await wait(()=>evaluate(`!PersonalNavigation.context&&!document.querySelector('#personal-navigation-seed')`));
 assert.equal(await evaluate(`document.querySelector('main').dataset.navigationOccurrence`),publicCursor);assert.deepEqual(errors,[]);
 console.log('PASS normal18821 actual game/Table hunter input -> evaluator Tree -> private Day2 Current -> unchanged public Current');
 await call('Browser.close',{},null).catch(()=>{});
"""
if '--co' not in sys.argv:body='\n'.join(line for line in body.splitlines() if "fetch('/navigation/public-input'" not in line)
with TemporaryDirectory() as directory:
 probe=Path(directory)/'smoke.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');subprocess.run(['node',str(probe)],check=True,timeout=180)
