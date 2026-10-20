const {chromium}=require('playwright'),assert=require('assert'),fs=require('fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),results=[];
 try{
 for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]){
  const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const base=process.env.WW_GG_TEST_URL||'http://127.0.0.1:18801';
  assert.equal((await context.request.post(base+'/start',{form:{players:'5',day:'max',night:'max'}})).status(),200);
  await page.goto(base+'/main');
  assert.equal(await page.locator('#village-rate').getAttribute('data-fraction'),'7/15');
  await page.locator('[data-scroll-to="tree-reserved"]').click();
  await page.locator('[data-tree-open]').click();
  await page.waitForSelector('[data-tree-node="0"]');
  let root=page.locator('[data-tree-content] > [data-tree-node]');
  assert((await root.textContent()).includes('名前付きの枝は未展開'));
  await root.locator('[data-tree-expand="0"]').click();
  await root.locator(':scope > .tree-action').first().waitFor();
  let action=root.locator(':scope > .tree-action').first();await action.locator(':scope > summary').click();
  assert((await action.textContent()).includes('MAX同点採用 1/5'));
  const branch=action.locator(':scope > .tree-branch').filter({hasText:'継続（狼生存）'});
  assert((await branch.textContent()).includes('4/5'));
  await branch.locator(':scope > button').click();
  let night=branch.locator(':scope > [data-tree-node]');await night.waitFor();
  assert((await night.locator('h3').first().textContent()).includes('夜'));
  await night.locator(':scope > details > summary').first().click();
  assert((await night.locator('.tree-board tr').nth(1).textContent()).includes('死亡'));
  await night.locator(':scope > [data-tree-expand]').click();
  let bite=branch.locator(':scope > [data-tree-node] > .tree-action').first();await bite.waitFor();await bite.locator(':scope > summary').click();
  await bite.locator(':scope > .tree-branch > button').click();
  let day=bite.locator(':scope > .tree-branch > [data-tree-node]');await day.waitFor();
  assert((await day.locator('h3').first().textContent()).includes('2日目 昼'));
  await day.locator(':scope > [data-tree-expand]').click();
  let execute=bite.locator(':scope > .tree-branch > [data-tree-node] > .tree-action').first();await execute.waitFor();await execute.locator(':scope > summary').click();
  let victory=execute.locator(':scope > .tree-branch').filter({hasText:'村勝利'});await victory.locator(':scope > button').click();
  await victory.locator('[data-tree-node]').waitFor();assert((await victory.textContent()).includes('村勝率 1 (100.00%)'));
  const original=(await (await context.request.get(base+'/game-tree')).json());assert.equal(original.history.length,0);assert.equal(original.village_win,'7/15');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:`.artifacts/game-tree-${name}.png`,fullPage:true});
  await page.reload();await page.locator('[data-tree-open]').click();await page.waitForSelector('[data-tree-node="0"]');
  assert((await page.locator('[data-tree-content]').textContent()).includes('保存した計算結果を再利用'));
  assert.deepEqual(errors,[]);results.push({name,width,height,terminal_reached:true,baseline:'7/15',no_page_errors:true,no_global_overflow:true,snapshot_preserved:true,reload_reused:true});
  await context.close();
 }
 fs.writeFileSync('.artifacts/game-tree-browser.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
