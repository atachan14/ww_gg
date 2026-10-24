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
 app=create_app({'SECRET_KEY':'input-option-browser-only','HYBRID_TABLE_PREVIEW':True,'PERSISTENT_TREE_PREVIEW':True,'GAME_TREE_PREVIEW':True,'ANONYMOUS_OWNERSHIP_PREVIEW':True,'NAVIGATION_DIRECTORY':str(Path(directory)/'navigation')})
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
 const requests=[];await call('Network.enable');ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.requestWillBeSent'){const r=m.params.request;requests.push({path:new URL(r.url).pathname,mode:new URLSearchParams(r.postData||'').get('preview_mode'),t:Date.now()});}});
 const pause=ms=>new Promise(r=>setTimeout(r,ms)),count=()=>requests.filter(r=>r.path==='/table-preview').length;
 const mode=async value=>evaluate(`(()=>{const x=document.querySelector('#display-input-calculation');x.value=${JSON.stringify(value)};x.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const probe=async query=>evaluate(`fetch('/_test/preview-control${query||''}').then(r=>r.json())`);
 const snapshot=()=>evaluate(`JSON.stringify(boardTableDraft.snapshot())`);
 const selected=()=>evaluate(`document.querySelector('#display-input-calculation').value`);
 const setup=async()=>{await navigate('__BASE__/');await evaluate(`fetch('/start',{method:'POST',body:new URLSearchParams({citizens:'3',seers:'1',wolves:'1',day:'random',night:'random',fake_reports:'random',win_cutoff:'0'})})`);await navigate('__BASE__/main');await wait(()=>evaluate(`document.querySelector('main')?.dataset.tableInitialized==='true'`),8000);};
 const fill=async()=>evaluate(`(()=>{const co=document.querySelector('[data-table-co="1"]');co.value='seer';co.dispatchEvent(new Event('change',{bubbles:true}));const t=document.querySelector('[data-table-target="1:1"]'),c=document.querySelector('[data-table-color="1:1"]');t.value='2';t.dispatchEvent(new Event('change',{bubbles:true}));c.value='white';c.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const rates=()=>evaluate(`Array.from(document.querySelectorAll('#information-panel .probability[data-fraction],.player-table .probability[data-fraction]')).map(x=>x.dataset.fraction)`);
 const roleRates=()=>evaluate(`Array.from(document.querySelectorAll('.player-table td[data-value-cell]')).filter(x=>!['dawn','final'].includes(x.dataset.valueCell)).flatMap(x=>Array.from(x.querySelectorAll('[data-fraction]')).map(e=>e.dataset.fraction))`);
 const previewDone=()=>wait(()=>evaluate(`document.querySelector('[data-table-preview-status]').textContent==='プレビュー'`),8000);
 await setup();assert.equal(await selected(),'roles');
 console.log('STAGE default and legacy migration');
 for(const [old,next] of [['false','off'],['true','all']]){await evaluate(`localStorage.setItem('ww_gg.input-calculation',${JSON.stringify(old)})`);await navigate('__BASE__/main');assert.equal(await selected(),next);assert.equal(await evaluate(`localStorage.getItem('ww_gg.input-calculation')`),next);}
 await evaluate(`localStorage.removeItem('ww_gg.input-calculation')`);await navigate('__BASE__/main');assert.equal(await selected(),'roles');
 await evaluate(`document.querySelector('[data-status-target="3"]').click()`);const selection=await evaluate(`document.querySelector('input[name="target"]:checked')?.value`);
 const initial=count();await fill();const input=await snapshot();await pause(70);assert.equal(count(),initial,'debounce fired early');await previewDone();const exactRoles=await roleRates();assert.ok(exactRoles.length>10);
 assert.equal(await evaluate(`document.querySelector('#village-rate').textContent`),'未計算');assert.equal(await evaluate(`document.querySelectorAll('[data-win-horizon] [data-fraction]').length`),0);
 console.log('STAGE role-only complete');
 await mode('all');await previewDone();assert.deepEqual(await roleRates(),exactRoles);assert.ok(await evaluate(`document.querySelectorAll('[data-win-horizon] [data-fraction]').length`)>0);
 await evaluate(`document.querySelector('[data-table-color="1:1"]').focus()`);await mode('roles');await previewDone();assert.equal(await evaluate(`document.activeElement.dataset.tableColor`),'1:1');assert.equal(await snapshot(),input);assert.equal(await evaluate(`document.querySelector('input[name="target"]:checked')?.value`),selection);
 await mode('off');const offCount=count();for(const next of ['roles','all','off','all','roles','off'])await mode(next);await pause(260);assert.equal(count(),offCount,'Off/timer transition leaked preview');
 console.log('STAGE active All to roles');
 await probe('?slow=1');const beforeCancel=(await probe()).cancelled;await mode('all');await wait(async()=> (await probe()).active,5000);const cancelAt=Date.now();await mode('roles');await wait(async()=> (await probe()).cancelled>beforeCancel,5000);const cancelMs=Date.now()-cancelAt;await previewDone();assert.equal(await evaluate(`document.querySelector('#village-rate').textContent`),'未計算');assert.deepEqual(await roleRates(),exactRoles);
 // Role-only work is cancellable too, even before its posterior is returned.
 await mode('off');const beforeRoleCancel=(await probe()).cancelled;await mode('roles');await wait(async()=> (await probe()).active,5000);await mode('off');await wait(async()=> (await probe()).cancelled>beforeRoleCancel,5000);assert.equal(await snapshot(),input);await probe('?slow=0');
 console.log('STAGE late All reply must not replace roles');
 // Delay delivery of an already-computed valid All response outside the queue.
 // The next role-only frame wins even if transport cancellation cannot retract it.
 const beforeLate=(await probe()).finished;
 await evaluate(`window.__optionFetch=window.fetch;window.fetch=(input,init={})=>{const p=new URLSearchParams(init.body);const result=window.__optionFetch(input,init);return String(input)==='/table-preview'&&p.get('preview_mode')==='all'?result.then(r=>new Promise(resolve=>setTimeout(()=>resolve(r),600))):result;};`);
 await mode('all');await wait(async()=> (await probe()).finished>beforeLate,5000);await mode('roles');await previewDone();await pause(650);assert.equal(await evaluate(`document.querySelector('#village-rate').textContent`),'未計算');assert.deepEqual(await roleRates(),exactRoles);await evaluate(`window.fetch=window.__optionFetch`);
 console.log('STAGE Off save and errors');
 await mode('off');const beforeOff=count();await pause(250);assert.equal(count(),beforeOff);await probe('?fail=1');await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('[data-table-preview-status]').textContent.includes('test save failure')`),5000);assert.equal(await snapshot(),input);
 const root=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence!==${JSON.stringify(root)}&&!boardTableDraft.isDirty()`),8000);const reference=await rates();assert.ok(reference.length>10);
 for(const next of ['roles','all']){console.log('STAGE Update '+next);await setup();await mode(next);await fill();await previewDone();const root=await evaluate(`document.querySelector('main').dataset.navigationOccurrence`);await evaluate(`document.querySelector('[data-table-update]').click()`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence!==${JSON.stringify(root)}&&!boardTableDraft.isDirty()`),8000);assert.deepEqual(await rates(),reference);assert.equal(await selected(),next);}
 await navigate('__BASE__/main');assert.equal(await selected(),'all');await mode('roles');await navigate('__BASE__/main');assert.equal(await selected(),'roles');
 await evaluate(`document.querySelector('[data-settings-pane="display"]').open=true`);await fs.writeFile('.artifacts/input-option-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await fs.writeFile('.artifacts/input-option-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate(`BoardNavigation.send('back')`);await wait(()=>evaluate(`document.querySelector('main').dataset.navigationOccurrence==='h0'`),8000);await navigate('__BASE__/main');assert.equal(await selected(),'roles');
 await navigate('__BASE__/help/operations/display');assert.ok(await evaluate(`document.querySelector('.help-article').innerText.includes('初期設定は「役職率まで」')`));
 assert.deepEqual(errors,[]);assert.ok(!requests.some(x=>x.path==='/table-preview'&&x.mode==='off'));
 console.log(JSON.stringify({defaultRoles:true,legacyMigration:true,offNoRequests:true,rolesNoWinRates:true,allRoleRatesEqual:true,cancelMs,allToRoles:true,staleIgnored:true,draftSelectionFocus:true,saveErrorRetained:true,updateRatesEqual:reference.length,persistReloadCurrent:true,previewModes:[...new Set(requests.filter(x=>x.path==='/table-preview').map(x=>x.mode))],errors}));await call('Browser.close',{},null).catch(()=>{});
""".replace('__BASE__',base)
 try:
  probe_file=Path(directory)/'check.cjs';probe_file.write_text(prefix+body+suffix,encoding='utf-8')
  result=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(probe_file)],timeout=65)
  assert result.returncode==0,result.returncode
  assert not app.extensions['calculation_jobs'].active
 finally:server.shutdown();server.server_close();thread.join(3)
