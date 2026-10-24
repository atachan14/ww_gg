"""Cookie-isolated actual browser checks for the optional public Tree payload."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from werkzeug.serving import make_server
from app import create_app
import subprocess

SCRIPT=r"""
const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[],tree=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('response',async r=>{if(r.url().includes('/game-tree?')){const d=await r.json();tree.push({url:r.url(),d});}});
  const base=process.argv[2];
  await page.request.post(base+'/start',{form:{citizens:'3',seers:'1',wolves:'1',day:'max',night:'max',fake_reports:'max',win_cutoff:'0'}});
  let start=Date.now();await page.goto(base+'/main');
  await page.waitForFunction(()=>document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete',null,{timeout:60000});
  console.log(JSON.stringify({phase:'initial-public-auto',ms:Date.now()-start,cards:await page.locator('[data-tree-item]').count()}));
  assert(tree.length>0);assert(tree.every(r=>new URL(r.url).searchParams.get('format')==='public-tree'));
  for(const {d} of tree)for(const row of [d,...Object.values(d.items||{})])for(const field of ['players','rules','policy','method','viewpoint'])assert(!(field in row));
  assert(await page.locator('[data-tree-item]').count()>1);
  await page.locator('.compact-tree-board .compact-tree-select').first().click();
  await page.waitForSelector('[data-distribution-for]');
  await page.locator('.compact-tree-board .compact-tree-select').first().click();
  await page.waitForSelector('[data-distribution-for]',{state:'detached'});
  const target=page.locator('.compact-tree-board .compact-tree-go:not(:disabled)').nth(1);
  assert(await target.count());
  await target.click();await page.waitForLoadState('networkidle');
  await page.waitForFunction(()=>document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete',null,{timeout:60000});
  const current=await page.evaluate(()=>fetch('/navigation').then(r=>r.json()));assert.notEqual(current.current.occurrence,'h0');
  await page.reload();await page.waitForFunction(()=>document.querySelector('[data-calculation-tree]')?.dataset.treeAuto==='complete',null,{timeout:60000});
  const restored=await page.evaluate(()=>fetch('/navigation').then(r=>r.json()));assert.equal(restored.current.occurrence,current.current.occurrence);
  await page.setViewportSize({width:390,height:844});
  await page.locator('[data-calculation-tree]').scrollIntoViewIfNeeded();
  const bounds=await page.locator('[data-calculation-tree]').boundingBox();
  await page.mouse.move(bounds.x+Math.min(bounds.width/2,150),bounds.y+100);
  const old=await page.locator('[data-calculation-tree]').getAttribute('data-tree-zoom');
  await page.keyboard.down('Control');await page.mouse.wheel(0,-150);await page.keyboard.up('Control');
  await page.waitForTimeout(100);
  const zoom=await page.locator('[data-calculation-tree]').getAttribute('data-tree-zoom');assert(Number(zoom)>Number(old));
  await page.mouse.wheel(0,100);await page.waitForTimeout(100);
  assert.equal(await page.locator('[data-calculation-tree]').getAttribute('data-tree-zoom'),zoom);
  assert.equal(errors.length,0,errors.join(';'));
  console.log(JSON.stringify({phase:'PASS',coverage:'compact public requests, automatic Tree, inline analysis, actual Current click, reload, narrow viewport, Ctrl zoom and ordinary wheel',requests:tree.length,errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
"""
with TemporaryDirectory() as directory:
 app=create_app(dict(TESTING=True,SECRET_KEY='public-tree-response-browser',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
 server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  script=Path(directory)/'verify.cjs';script.write_text(SCRIPT,encoding='utf-8')
  completed=subprocess.run(['C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(script),'http://127.0.0.1:'+str(server.server_port)],timeout=150)
  if completed.returncode:raise SystemExit(completed.returncode)
 finally:server.shutdown();worker.join(timeout=5)
