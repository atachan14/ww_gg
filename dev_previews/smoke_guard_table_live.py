"""Fresh browser profile against the normal local WW_GG server."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
body=r"""
 await navigate('http://127.0.0.1:18821/');
 await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'2',seers:'1',hunters:'1',wolves:'1',day:'random',night:'random',win_cutoff:'0',fake_reports:'random'})})`);
 await evaluate(`(async()=>{const before=await(await fetch('/navigation')).json();const response=await fetch('/navigation/advance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:before.revision,target:3})});if(!response.ok)throw Error(await response.text());})()`);
 await navigate('http://127.0.0.1:18821/main');
 await wait(()=>evaluate(`document.querySelector('[data-viewpoint-role="hunter"]')`));
 const publicCursor=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);
 await evaluate(`document.querySelector('[data-viewpoint-role="hunter"]').click();document.querySelector('tr[data-player="4"] .player-name').click()`);
 await wait(()=>evaluate(`PersonalNavigation.context?.view.players[0]===4`),90000);
 const tree=await evaluate(`PersonalNavigation.request('tree',{expand:true})`);assert.equal(tree.evaluation_trace.owner,'evaluator');
 const arrival=Object.values(tree.items).find(row=>row.day_start&&row.alive.length===4);assert.ok(arrival);
 await evaluate(`(async()=>{const result=await PersonalNavigation.request('current',{node:${JSON.stringify(arrival.node)},snapshot:${JSON.stringify(tree.snapshot)}});await PersonalNavigation.install(result);})()`);
 await wait(()=>evaluate(`document.querySelector('#personal-navigation-seed')&&document.querySelector('#phase-title').textContent.includes('2')`));
 await evaluate(`document.querySelector('[data-personal-public]').click()`);await wait(()=>evaluate(`!PersonalNavigation.context&&!document.querySelector('#personal-navigation-seed')`));
 assert.equal(await evaluate(`document.querySelector('main').dataset.navigationOccurrence`),publicCursor);assert.deepEqual(errors,[]);
 console.log('PASS normal18821 actual game/Table hunter input -> evaluator Tree -> private Day2 Current -> unchanged public Current');
 await call('Browser.close',{},null).catch(()=>{});
"""
with TemporaryDirectory() as directory:
 probe=Path(directory)/'smoke.cjs';probe.write_text(prefix+body+suffix,encoding='utf-8');subprocess.run(['node',str(probe)],check=True,timeout=180)
