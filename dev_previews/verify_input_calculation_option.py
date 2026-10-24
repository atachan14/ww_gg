"""Isolated real-browser preview preference contracts; ephemeral test controls only."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic,sleep
import subprocess
from werkzeug.serving import make_server
from flask import request,jsonify
from app import create_app
from werewolf.calculation_budget import tick,CalculationCancelled
from build_vercel import build
build()
with TemporaryDirectory() as directory:
 app=create_app({'SECRET_KEY':'input-option-browser-only','HYBRID_TABLE_PREVIEW':True,'PERSISTENT_TREE_PREVIEW':True,'GAME_TREE_PREVIEW':True,'NAVIGATION_DIRECTORY':str(Path(directory)/'navigation')})
 control={'slow':False,'active':False,'cancelled':0,'finished':0,'fail':False}
 original=app.view_functions['table_preview'];publish=app.view_functions['table_publish']
 def preview():
  control['active']=True
  try:
   if control['slow']:
    end=monotonic()+.5
    while monotonic()<end:tick(0);sleep(.002)
   return original()
  except CalculationCancelled:
   control['cancelled']+=1;raise
  finally:control['active']=False;control['finished']+=1
 def save():
  if control['fail']:
   control['fail']=False;return jsonify(error='test save failure'),503
  return publish()
 app.view_functions['table_preview']=preview;app.view_functions['table_publish']=save
 @app.get('/_test/preview-control')
 def configure():
  if 'slow' in request.args:control['slow']=request.args['slow']=='1'
  if 'fail' in request.args:control['fail']=request.args['fail']=='1'
  return jsonify(control)
 server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f'http://127.0.0.1:{server.server_port}'
 s=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf-8');prefix=s.split("  const kind=process.argv[2]")[0];suffix=s[s.index(' }finally{if(ws)'):]
 body=r"""
 const requests=[];await call('Network.enable');ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.requestWillBeSent')requests.push({path:new URL(m.params.request.url).pathname,t:Date.now()});});
 const pause=ms=>new Promise(r=>setTimeout(r,ms)),count=()=>requests.filter(r=>r.path==='/table-preview').length;
 const toggle=async enabled=>evaluate(`(()=>{const x=document.querySelector('#display-input-calculation');x.checked=${enabled};x.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const probe=async query=>evaluate(`fetch('/_test/preview-control${query||''}').then(r=>r.json())`);
 const snapshot=()=>evaluate(`JSON.stringify(boardTableDraft.snapshot())`);
 const dirty=()=>evaluate(`boardTableDraft.isDirty()`);
 const setup=async()=>{await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);await navigate('__BASE__/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`));};
 const fill=async()=>evaluate(`(()=>{const co=document.querySelector('[data-table-co="1"]');co.value='seer';co.dispatchEvent(new Event('change',{bubbles:true}));const t=document.querySelector('[data-table-target="1:1"]'),c=document.querySelector('[data-table-color="1:1"]');t.value='2';t.dispatchEvent(new Event('change',{bubbles:true}));c.value='white';c.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const rates=()=>evaluate(`Array.from(document.querySelectorAll('#information-panel .probability[data-fraction],.player-table .probability[data-fraction]')).map(x=>x.dataset.fraction)`);
 await setup();assert.equal(await evaluate(`document.querySelector('#display-input-calculation').checked`),false);
 await evaluate(`document.querySelector('[data-status-target="3"]').click()`);const selection=await evaluate(`document.querySelector('input[name="target"]:checked')?.value`);
 const initial=count();await fill();const input=await snapshot();await pause(320);assert.equal(count(),initial,'Off sent input preview');assert.ok(await dirty());
 const offState=await evaluate(`document.querySelector('#village-rate').textContent`);assert.equal(offState,'未計算');
 await evaluate(`document.querySelector('[data-table-color="1:1"]').focus()`);await toggle(true);await pause(80);assert.equal(count(),initial,'debounce fired early');
 assert.equal(await evaluate(`document.activeElement.dataset.tableColor`),'1:1');
 await wait(()=>count()>initial);await wait(()=>evaluate(`document.querySelector('[data-table-preview-status]').textContent==='プレビュー'`));
 assert.equal(await snapshot(),input);assert.equal(await evaluate(`document.querySelector('input[name="target"]:checked')?.value`),selection);
 // Timer cancellation and repeated toggles leave the draft intact and send nothing.
 await toggle(false);const stoppedCount=count();for(let i=0;i<3;i++){await toggle(true);await toggle(false);}await pause(260);assert.equal(count(),stoppedCount);assert.equal(await snapshot(),input);
 // Exercise actual request-owned server stop while a preview is executing.
 await probe('?slow=1');const beforeCancel=(await probe()).cancelled;await toggle(true);await wait(async()=> (await probe()).active,5000);const cancelAt=Date.now();await toggle(false);await wait(async()=> (await probe()).cancelled>beforeCancel,5000);const cancelMs=Date.now()-cancelAt;assert.equal(await snapshot(),input);assert.equal(await evaluate(`document.querySelector('#village-rate').textContent`),'未計算');
 // Force a late response despite a deliberately ignored AbortSignal. Generation
 // guards must still prevent it being installed after Off.
 const beforeLate=(await probe()).finished;
 await evaluate(`window.__optionFetch=window.fetch;window.fetch=(input,init={})=>String(input)==='/table-preview'?window.__optionFetch(input,{...init,signal:undefined}):window.__optionFetch(input,init);`);
 await toggle(true);await wait(async()=> (await probe()).active,5000);await toggle(false);await wait(async()=> (await probe()).finished>beforeLate);await pause(60);
 assert.equal(await evaluate(`document.querySelector('#village-rate').textContent`),'未計算');assert.equal(await snapshot(),input);
 await evaluate(`window.fetch=window.__optionFetch`);await probe('?slow=0');
 // Failed save is not a disposable preview; inputs remain available for retry.
 await probe('?fail=1');await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('[data-table-preview-status]').textContent.includes('test save failure')`));assert.equal(await snapshot(),input);assert.ok(await dirty());
 const root=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);await evaluate(`document.querySelector('[data-table-update]').click()`);
 await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence!==${JSON.stringify(root)}&&!boardTableDraft.isDirty()`));const offRates=await rates();assert.ok(offRates.length>10);assert.equal(await evaluate(`document.querySelector('#display-input-calculation').checked`),false);
 // Same public update with On must produce exactly the same displayed values.
 await setup();await toggle(true);await fill();await wait(()=>evaluate(`document.querySelector('[data-table-preview-status]').textContent==='プレビュー'`));
 const onRoot=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence!==${JSON.stringify(onRoot)}&&!boardTableDraft.isDirty()`));assert.deepEqual(await rates(),offRates);
 await navigate('__BASE__/main');assert.equal(await evaluate(`document.querySelector('#display-input-calculation').checked`),true);
 await evaluate(`document.querySelector('[data-settings-pane="display"]').open=true`);
 await fs.writeFile('.artifacts/input-option-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await fs.writeFile('.artifacts/input-option-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await navigate('__BASE__/help/operations/display');assert.ok(await evaluate(`document.querySelector('.help-article').innerText.includes('180ms')`));assert.ok(await evaluate(`document.querySelector('[data-book="operations-display"]').getAttribute('aria-current')==='page'`));
 assert.deepEqual(errors,[]);console.log(JSON.stringify({defaultOff:true,offNoPreview:true,onDebounced:true,cancelMs,draftSelectionFocus:true,lateResultIgnored:true,saveErrorRetained:true,updateRatesEqual:offRates.length,persisted:true,previewRequests:count(),errors}));await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe_file=Path(directory)/'check.cjs';probe_file.write_text(prefix+body+suffix,encoding='utf-8')
  result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe_file)],timeout=65)
  assert result.returncode==0,result.returncode
  assert not app.extensions['calculation_jobs'].active
 finally:server.shutdown();server.server_close();thread.join(3)
