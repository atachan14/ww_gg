"""Ephemeral browser verification; never restart the user's preview or use its store."""
from pathlib import Path
import subprocess,tempfile,threading
from werkzeug.serving import make_server
from app import create_app

def main():
 with tempfile.TemporaryDirectory(prefix='wwgg-manual-test-') as directory:
  app=create_app(dict(GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory,SESSION_COOKIE_NAME='wwgg_current_local_18821'))
  server=make_server('127.0.0.1',0,app,threaded=True)
  worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
  try:
   script=Path('dev_previews/verify_delayed_co.cjs').read_text(encoding='utf-8')
   script=script.replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port))
   # Additional exact reproduction via the real Table controls.
   marker="  // First-day none supplies"
   addition=r"""
  await evaluate(`(async()=>{await fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'max',night:'max',fake_reports:'max',win_cutoff:'1'})});})()`);
  await navigate('http://127.0.0.1:PORT/main');await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`));
  await choose(1);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h1'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  await choose(2);await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h2'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  await evaluate(`(()=>{const co=document.querySelector('[data-table-co="3"]');co.value='seer';co.dispatchEvent(new Event('change',{bubbles:true}));for(const [day,target,color]of [[1,4,'white'],[2,5,'black']]){const t=document.querySelector('[data-table-target="'+day+':3"]');t.value=String(target);t.dispatchEvent(new Event('change',{bubbles:true}));const c=document.querySelector('[data-table-color="'+day+':3"]');c.value=color;c.dispatchEvent(new Event('change',{bubbles:true}));}})()`);
  await wait(()=>evaluate(`!document.querySelector('[data-table-update]').disabled`));await evaluate(`document.querySelector('[data-table-update]').click()`);
  await wait(()=>evaluate(`document.querySelector('main')?.dataset.navigationOccurrence==='h3'&&document.querySelector('[data-calculation-tree]')?.dataset.navigationUpdate==='complete'`));
  const reported=await evaluate(`(async()=>{const n=await(await fetch('/navigation')).json();return {seer:document.querySelector('[data-player="3"] [data-value-cell="seer"] [data-fraction]').dataset.fraction,wolf:document.querySelector('[data-player="3"] [data-value-cell="wolf"] [data-fraction]').dataset.fraction,manual:n.occurrences.find(r=>r.key==='h3').selection_weight};})()`);
  assert.equal(reported.seer,'1/3');assert.equal(reported.wolf,'2/3');assert.equal(reported.manual,'0');
  await fs.writeFile('.artifacts/manual-role-table.json',JSON.stringify({reported,errors},null,2));
""".replace('PORT',str(server.server_port))
   script=script.replace(marker,addition+marker)
   probe=Path(directory)/'verify.cjs';probe.write_text(script,encoding='utf-8')
   subprocess.run(['node',str(probe)],check=True)
  finally:
   server.shutdown();server.server_close();worker.join()
if __name__=='__main__':main()
