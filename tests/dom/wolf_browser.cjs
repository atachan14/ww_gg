const {chromium}=require('playwright'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({baseURL:process.env.WW_GG_TEST_URL||'http://127.0.0.1:8772'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const response=await context.request.post('/start',{form:{citizens:'4',wolves:'1',day:'max',night:'max'}});assert(response.ok());
 await page.goto('/main');await page.locator('[data-status-target="5"]').click();await page.locator('#advance-button').click();
 await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 const publicValues=await page.locator('[data-value-cell]').allTextContents();
 const cookie=()=>context.cookies().then(v=>v.find(c=>c.name==='session').value);const before=await cookie();
 const wolf=page.locator('[data-viewpoint-role="wolf"]'),all=page.locator('[data-viewpoint-role="public"]');
 const viewing=()=>page.waitForFunction(()=>document.querySelector('main').dataset.viewpointMode==='viewing');
 const value=id=>page.locator(`tr[data-player="${id}"] [data-value-cell="final"]`).textContent();
 await wolf.click();await page.locator('tr[data-player="2"] .player-name').click();await viewing();
 assert.equal(await value(1),'100% / 0%');assert.equal(await value(3),'0% / 100%');assert.equal(await value(4),'0% / 100%');
 assert.equal(await value(2),'—');assert.equal(await value(5),'—');
 assert(await page.locator('#advance-button').isDisabled());
 assert((await page.locator('[data-table-scope]').textContent()).includes('狼視点'));
 if(process.env.WW_GG_WOLF_SCREENSHOT)await page.screenshot({path:process.env.WW_GG_WOLF_SCREENSHOT,fullPage:true});
 await wolf.click();await page.locator('tr[data-player="3"]').click();await viewing();
 assert.equal(await value(2),'0% / 100%');assert.equal(await cookie(),before);
 // Cancel during a delayed calculation; no stale final rates survive restoration.
 await page.route('**/private-view',async route=>{const response=await route.fetch();await new Promise(r=>setTimeout(r,100));await route.fulfill({response});});
 await wolf.click();await page.locator('tr[data-player="2"]').click();await all.click();await page.waitForTimeout(200);
 assert.equal(await page.locator('main').getAttribute('data-viewpoint-mode'),'public');
 assert.deepEqual(await page.locator('[data-value-cell]').allTextContents(),publicValues);
 assert.equal(await cookie(),before);assert.deepEqual(errors,[]);
 await browser.close();console.log('Edge wolf final: literal 0/100 comparison, roster change, locks, public identity, delayed response cancellation: PASS');
})().catch(e=>{console.error(e);process.exit(1);});
