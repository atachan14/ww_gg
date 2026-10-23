"""Isolated production-widget harness for the finite personal night scope.

No normal app route is added. Automatic traversal of unported later adapters is
paused in this harness; exact full-game evaluation is unchanged and already done.
"""
from pathlib import Path
from types import SimpleNamespace
from hashlib import sha256
import json,subprocess,tempfile,threading
from flask import Flask,request,jsonify
from werkzeug.serving import make_server
from tests import test_personal_evaluated_records as fixture
from werewolf.seer_intervention import SeerObserver
from werewolf.navigation_game import NavigationGame
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.public_convergence import state_key
from unittest.mock import patch

repo=Path.cwd()
def context(kind,warm=True):
 c,public,node,mass=fixture.PersonalEvaluatedRecordTests().personal(kind)
 e=c._ClosedCalculation__engine
 if warm:e.solve(*node.read(),physical=node.read().physical);e.evaluation_graph.personal_program(node.read(),node.groups)
 doc=SimpleNamespace(game=NavigationGame(node),data=c.data,revision=0)
 return SimpleNamespace(c=c,base=node,e=e,doc=doc,tree=NavigationTree(doc))
contexts={k:context(k) for k in ('intervention','black-intervention')};active=['intervention']
app=Flask(__name__,static_folder=str(repo/'static'))
def current():return contexts[active[0]]
def state():
 x=current();v=NavigationCurrent(x.doc.game);s=v.source;record=x.e.evaluation_graph.personal_program(x.base.read(),x.base.groups)
 return dict(view=active[0],day=s.public.day,alive=list(s.public.alive),owner=s.observer.actor,target=getattr(s.observer,'target',None),snapshot=x.tree.snapshot,identity=v.identity,revision=x.doc.revision,node=x.tree.current_key(),hash=sha256(repr(state_key(s)).encode()).hexdigest(),public_base=sha256(repr(x.base.read().public_state).encode()).hexdigest(),policy=sha256(repr(record.policies).encode()).hexdigest())
@app.get('/fixture')
def page():
 return """<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'><link rel='stylesheet' href='/static/styles.css'><main class='page-shell'><section class='panel tree-placeholder' data-calculation-tree data-tree-navigation='1'><h2>GameTree</h2><p data-tree-status></p><figure class='tree-flow-frame flow-frame' tabindex='0'><div data-tree-content class='tree-flowchart'></div></figure></section></main><footer class='phase-footer'>Personal record verification</footer><script src='/static/probability_display.js'></script><script src='/static/tree_viewport.js'></script><script src='/static/tree_expansion.js'></script><script>const originalCreate=TreeExpansion.create;TreeExpansion.create=()=>{const s=originalCreate();s.auto=async()=>{};return s;};</script><script src='/static/tree_layout.js'></script><script src='/static/calculation_tree.js'></script>"""
@app.get('/state')
def get_state():return jsonify(state())
@app.post('/switch')
def switch():
 key=request.json['view']
 if key not in contexts:return jsonify(error='Unknown fixture view'),400
 active[0]=key;return jsonify(state())
@app.get('/game-tree')
def tree_read():
 x=current()
 if request.args.get('snapshot') not in (None,x.tree.snapshot):return jsonify(error='Different observer snapshot'),409
 with patch.object(x.e,'solve',side_effect=AssertionError('widget requested extra evaluation')),patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('widget generated night')),patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('widget replayed public flow')):
  return jsonify(x.tree.read(request.args.get('node'),request.args.get('expand')=='1'))
@app.post('/game-tree/current')
def select():
 x=current()
 if request.form.get('snapshot')!=x.tree.snapshot or int(request.form['revision'])!=x.doc.revision:return jsonify(error='Stale personal view'),409
 x.tree.select(request.form['node']);x.doc.revision+=1;return jsonify(url='/fixture')
@app.post('/back')
def back():current().doc.game.back();current().doc.revision+=1;return jsonify(state())
@app.post('/forward')
def forward():current().doc.game.forward();current().doc.revision+=1;return jsonify(state())
@app.post('/restore')
def restore():
 old=current();saved=json.loads(json.dumps(old.doc.game.export()));fresh=context(active[0],False)
 fresh.doc.game=NavigationGame.restore(fresh.base,saved);fresh.doc.revision=old.doc.revision+1;fresh.tree=NavigationTree(fresh.doc);contexts[active[0]]=fresh
 return jsonify(state())

with tempfile.TemporaryDirectory(prefix='wwgg-personal-widget-') as directory:
 server=make_server('127.0.0.1',0,app,threaded=True);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  original=Path('dev_previews/verify_role_stages.cjs').read_text(encoding='utf8');prefix=original.split("  const kind=process.argv[2]")[0];suffix=original[original.index(' }finally{if(ws)'):]
  body="""
  await navigate('http://127.0.0.1:18821/fixture');await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`));
  const read=async()=>evaluate(`(async()=>{return(await fetch('/state')).json()})()`);const white=await read();assert.equal(white.target,4);
  await evaluate(`document.querySelector('[data-tree-toggle]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').innerText.includes('護衛位置')`));
  const tree=await evaluate(`(async()=>{return(await fetch('/game-tree?expand=1')).json()})()`);assert.equal(tree.evaluation_trace.owner,'evaluator');assert.equal(tree.evaluation_trace.ability_program,'factored-evaluated-flow');
  const arrival=Object.values(tree.items).find(r=>r.day_start&&r.alive.length===4&&r.public_updates?.length);assert.ok(arrival);const update=arrival.public_updates[0].node;
  const select=async node=>evaluate(`(async()=>{const s=await(await fetch('/state')).json();const r=await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({node:${JSON.stringify(node)},snapshot:s.snapshot,revision:String(s.revision)})});if(!r.ok)throw Error(await r.text());})()`);
  await select(arrival.node);let s=await read();assert.equal(s.day,2);assert.equal(s.alive.length,4);assert.equal(s.target,4);
  await select(update);const after=await read();assert.equal(after.day,2);assert.equal(after.target,4);
  await evaluate(`fetch('/back',{method:'POST'})`);await evaluate(`fetch('/forward',{method:'POST'})`);assert.equal((await read()).hash,after.hash);
  await evaluate(`fetch('/restore',{method:'POST'})`);const cold=await read();assert.equal(cold.hash,after.hash);assert.equal(cold.identity,after.identity);assert.equal(cold.snapshot,after.snapshot);
  await evaluate(`fetch('/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({view:'black-intervention'})})`);await navigate('http://127.0.0.1:18821/fixture');await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete'`));
  const black=await read();assert.equal(black.target,2);assert.notEqual(black.snapshot,white.snapshot);assert.notEqual(black.identity,white.identity);assert.equal(black.public_base,white.public_base);assert.equal(black.policy,white.policy);
  assert.equal(await evaluate(`(async()=>{return(await fetch('/game-tree?snapshot='+${JSON.stringify(white.snapshot)})).status})()`),409);
  await evaluate(`document.querySelector('[data-tree-toggle]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);await wait(()=>evaluate(`document.querySelector('[data-calculation-tree]').innerText.includes('護衛位置')`));
  await fs.writeFile('.artifacts/personal-record-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await fs.writeFile('.artifacts/personal-record-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await evaluate(`fetch('/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({view:'intervention'})})`);const again=await read();assert.equal(again.hash,cold.hash);assert.equal(again.target,4);
  assert.deepEqual(errors,[]);console.log('personal widget PASS: production Tree, white/black switch, stale snapshot409, shared Q/policy, scoped Current/back/forward/cold restore');await call('Browser.close',{},null).catch(()=>{});
"""
  probe=Path(directory)/'verify.cjs';probe.write_text((prefix+body+suffix).replace('http://127.0.0.1:18821','http://127.0.0.1:'+str(server.server_port)),encoding='utf8');subprocess.run(['node',str(probe)],check=True)
 finally:server.shutdown();server.server_close();worker.join()
