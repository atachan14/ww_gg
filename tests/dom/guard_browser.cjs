// Real Edge, isolated localhost preview. No external account or public writes.
const {chromium}=require('playwright'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({baseURL:process.env.WW_GG_TEST_URL||'http://127.0.0.1:8772'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const cookie=()=>context.cookies().then(cs=>cs.find(c=>c.name==='session').value);
 const post=async(url,extra)=>{
  const form=await page.locator('#action-form').evaluate(f=>({revision:f.elements.revision.value,...(document.querySelector('main').dataset.boardId?{board_id:document.querySelector('main').dataset.boardId}:{})}));
  const r=await context.request.post(url,{form:{...form,...extra}});assert(r.ok(),await r.text());
 };
 await context.request.post('/start',{form:{citizens:'3',hunters:'1',wolves:'1',day:'max',night:'random'}});
 await page.goto('/main');
 assert(await page.locator('[data-value-cell="final"] .probability').count());
 await post('/public-log',{operation:'publish',payload:JSON.stringify({mode:'simultaneous',events:[{kind:'co',player:1,role:'hunter'}]})});
 await page.reload();
 await page.locator('#strategy-editor').evaluate(el=>el.closest('details').open=true);
 await page.locator('#strategy-editor [data-scope="hunter"]').evaluate(el=>el.open=true);
 await page.locator('[data-open="hunter|position"]').click();
 assert.equal(await page.locator('#strategy-dialog-title').textContent(),'護衛位置');
 assert(await page.locator('[data-item-add="max"]').isDisabled());
 await page.locator('[data-editor-apply]').click();
 assert.equal(await page.locator('[name="guard_position"]').inputValue(),'["uniform"]');
 await page.locator('[data-status-target="5"]').click();await page.locator('#advance-button').click();
 await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 assert.equal(await page.locator('#system-log').count(),0);
 const hunter=page.locator('[data-viewpoint-role="hunter"]'),all=page.locator('[data-viewpoint-role="public"]');
 const viewing=()=>page.waitForFunction(()=>document.querySelector('main').dataset.viewpointMode==='viewing');
 const select=async()=>{await hunter.click();await page.locator('tr[data-player="1"] .player-name').click();await viewing();};
 const before=await cookie();
 await select();assert(await page.locator('#advance-button').isDisabled());
 assert.equal(await page.locator('[data-private-color]').count(),0);
 assert.equal(await page.locator('[data-private-target]').count(),0); // No completed guard yet.
 assert(await page.locator('tr[data-player="2"] [data-value-cell="final"] .probability').count());
 assert.equal(await cookie(),before);await all.click();
 await post('/dawn-report',{mode:'none'});await page.reload();
 assert(await page.locator('#advance-button').isEnabled());
 await page.locator('#advance-button').click();await page.waitForSelector('main:not([data-night-board])');
 assert.equal(await page.locator('[data-viewpoint-role]').count(),0);
 await page.reload();assert.equal(await page.locator('main[data-night-board]').count(),0);
 await page.locator('[data-status-target="4"]').click();await page.locator('#advance-button').click();
 await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 const publicCells=await page.locator('[data-value-cell]').allTextContents(),publicCookie=await cookie();
 await select();
 const target=page.locator('[data-private-target="1"]');
 assert.equal(await page.locator('[data-private-color]').count(),0);
 assert(await target.locator('option[value="4"]').count()); // Past target remains available after D2 execution.
 await target.selectOption('2');await viewing();
 assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="wolf"]').textContent(),'0%');
 assert.equal(await page.locator('tr[data-player="3"] [data-value-cell="wolf"]').textContent(),'100%');
 assert.equal(await cookie(),publicCookie);
 assert.equal(await page.locator('#action-form').evaluate(f=>[...new FormData(f).keys()].some(k=>k.includes('private'))),false);
 await all.click();assert.deepEqual(await page.locator('[data-value-cell]').allTextContents(),publicCells);
 await select();assert.equal(await target.inputValue(),'2');
 await target.selectOption('4');await viewing(); // Dead target is valid on its original night.
 assert(!(await page.locator('[data-viewpoint-status]').textContent()).startsWith('不整合'));
 await all.click();await page.reload();await select();assert.equal(await target.inputValue(),'4');
 await page.route('**/private-view',async route=>{const response=await route.fetch();await new Promise(r=>setTimeout(r,100));await route.fulfill({response});});
 await target.selectOption('2');await all.click();await page.waitForTimeout(200);
 assert.equal(await page.locator('main').getAttribute('data-viewpoint-mode'),'public');
 assert.deepEqual(await page.locator('[data-value-cell]').allTextContents(),publicCells);
 await page.unroute('**/private-view');await hunter.click();await hunter.click();
 assert((await hunter.textContent()).includes('0/1'));await all.click();
 await page.locator('#back-button').click();await page.waitForSelector('main:not([data-night-board])');
 await page.locator('#back-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 assert.equal(await page.locator('[data-private-target]').count(),0);
 assert.deepEqual(errors,[]);await browser.close();
 console.log('Real Edge guard: ordered strategy, known/unknown scope, values, no-death/reload/back, target-only secrets, original night dead target, no public cookie/form changes, reselect, stale response: PASS');
})().catch(e=>{console.error(e);process.exit(1)});
