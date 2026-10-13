// Real Edge integration test; run against the isolated --dawn-board preview.
const {chromium}=require('playwright'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({baseURL:process.env.WW_GG_TEST_URL||'http://127.0.0.1:8772'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const start=async data=>{const r=await context.request.post('/start',{form:data});assert(r.ok());await page.goto('/main');};
 const base={citizens:'5',wolves:'1',seers:'1',day:'random',night:'random',initial_seer:'normal'};
 await start(base);
 assert.equal(await page.locator('[data-viewpoint-role]').count(),0);
 await page.locator('[data-status-target="7"]').click();await page.locator('#advance-button').click();
 await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 assert.equal(await page.locator('#system-log').count(),0);
 const publicCells=await page.locator('[data-value-cell]').allTextContents();
 const publicSnapshot=()=>page.locator('#player-panel .table-scroll > .player-table').evaluate(table=>{const clone=table.cloneNode(true);clone.querySelectorAll('[style]').forEach(n=>n.removeAttribute('style'));return clone.innerHTML;});
 const publicHtml=await publicSnapshot();
 const cookie=()=>context.cookies().then(all=>all.find(c=>c.name==='session').value);
 const before=await cookie();
 const seer=page.locator('[data-viewpoint-role="seer"]'),all=page.locator('[data-viewpoint-role="public"]');
 const viewing=()=>page.waitForFunction(()=>document.querySelector('main').dataset.viewpointMode==='viewing');
 await seer.click();assert.equal(await seer.textContent(),'占い視点（0/1）');
 assert(await page.locator('#advance-button').isDisabled());assert(await page.locator('[data-status-target="2"]').isDisabled());
 await page.locator('tr[data-player="1"] .player-name').click();await viewing();
 assert.equal(await page.locator('[data-private-details="1:seer"]').count(),1);
 assert.equal(await page.locator('tr[data-player="1"] [data-value-cell="seer"]').textContent(),'100%');
 const target=page.locator('[data-private-target="1"]'),color=page.locator('[data-private-color="1"]');
 await target.selectOption('2');await viewing();await color.selectOption('black');await viewing();
 assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="wolf"]').textContent(),'100%');
 assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="final"]').textContent(),'未対応');
 assert.equal(await cookie(),before);
 assert.equal(await page.evaluate(()=>[...new FormData(document.querySelector('#action-form')).keys()].some(k=>k.includes('private'))),false);
 // Secret remains available after contradictory input and can be corrected.
 await target.selectOption('3');await viewing();
 await all.click();assert.deepEqual(await page.locator('[data-value-cell]').allTextContents(),publicCells);
 assert.equal(await publicSnapshot(),publicHtml);
 await seer.click();await page.locator('tr[data-player="1"]').click();await viewing();
 assert.equal(await target.inputValue(),'3');assert.equal(await color.inputValue(),'black');
 // Repeated role clicks cancel selection; stale private response cannot win.
 await page.route('**/private-view',async route=>{const response=await route.fetch();await new Promise(r=>setTimeout(r,100));await route.fulfill({response});});
 await target.selectOption('2');await all.click();await page.waitForTimeout(200);
 assert.equal(await page.locator('main').getAttribute('data-viewpoint-mode'),'public');
 assert.deepEqual(await page.locator('[data-value-cell]').allTextContents(),publicCells);
 await seer.click();await seer.click();assert.equal(await seer.textContent(),'占い視点（0/1）');await all.click();
 await page.unroute('**/private-view');
 await page.reload();await seer.click();await page.locator('tr[data-player="1"]').click();await viewing();
 assert.equal(await target.inputValue(),'2');assert.equal(await color.inputValue(),'black');
 // Public observation revises this Board; private draft survives the revision.
 await all.click();await page.locator('[data-status-target="3"]').click();
 await page.waitForSelector('[data-status-target="3"][aria-pressed="true"]');
 await seer.click();await page.locator('tr[data-player="1"]').click();await viewing();
 assert.equal(await target.inputValue(),'2');assert.equal(await color.inputValue(),'black');
 await all.click();await page.locator('#advance-button').click();await page.waitForSelector('main:not([data-night-board])');
 assert.equal(await page.locator('[data-viewpoint-role]').count(),0);
 await page.locator('#back-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 await seer.click();await page.locator('tr[data-player="1"]').click();await viewing();
 assert.equal(await target.inputValue(),'2');assert.equal(await color.inputValue(),'black');
 await all.click();await page.locator('#back-button').click();await page.waitForSelector('main:not([data-night-board])');
 assert.equal(await page.locator('[data-viewpoint-role]').count(),0);
 // Invalid true evidence stays visibly inconsistent, with editable secret controls.
 await start({...base,initial_seer:'random_white'});
 await page.locator('[data-status-target="7"]').click();await page.locator('#advance-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 await seer.click();await page.locator('tr[data-player="1"]').click();await viewing();
 await target.selectOption('2');await viewing();await color.selectOption('black');await viewing();
 assert((await page.locator('[data-viewpoint-status]').textContent()).startsWith('不整合'));
 assert(await color.isEnabled());assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="wolf"]').textContent(),'不整合');
 await color.selectOption('white');await viewing();
 assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="wolf"]').textContent(),'0%');
 await all.click();
 // Uncertain hunter now has uniform-bite guard values, and no invented past guard.
 await start({citizens:'3',wolves:'1',hunters:'1',day:'random',night:'random'});
 await page.locator('[data-status-target="5"]').click();await page.locator('#advance-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 assert.equal(await page.locator('[data-viewpoint-role="seer"]').count(),0);
 await page.locator('[data-viewpoint-role="hunter"]').click();await page.locator('tr[data-player="1"]').click();await viewing();
 assert.equal(await page.locator('tr[data-player="1"] [data-value-cell="hunter"]').textContent(),'100%');
 assert.equal(await page.locator('[data-private-details] select').count(),0);
 assert(await page.locator('tr[data-player="2"] [data-value-cell="dawn"] .probability').count());
 await all.click();
 // A dead initial wolf remains selectable when there are two wolves.
 await start({citizens:'5',wolves:'2',day:'random',night:'random'});
 await page.locator('[data-status-target="1"]').click();await page.locator('#advance-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 await page.locator('[data-viewpoint-role="wolf"]').click();
 await page.locator('tr[data-player="1"]').click();await page.locator('tr[data-player="2"]').click();await viewing();
 assert.equal(await page.locator('tr[data-player="1"] [data-value-cell="wolf"]').textContent(),'100%');
 assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="dawn"]').textContent(),'—');
 const snap=process.env.WW_GG_TEST_SCREENSHOT;if(snap)await page.screenshot({path:snap,fullPage:true});
 await all.click();
 assert.deepEqual(errors,[]);await browser.close();console.log('Real Edge: night mount, locks, secret recalculation/correction, public identity, reselect, stale response, reload, revision retention, day/night/back, hunter unsupported, dead wolf: PASS');
})().catch(e=>{console.error(e);process.exit(1);});
