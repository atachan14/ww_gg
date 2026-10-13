const {chromium}=require('playwright'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({baseURL:process.env.WW_GG_TEST_URL||'http://127.0.0.1:8772'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const setup=async(disclosure)=>{
  await context.request.post('/start',{form:{citizens:'3',wolves:'1',seers:'1',day:'max',night:'random',initial_seer:'normal',seer_disclosure:disclosure}});
  await page.goto('/main');const revision=await page.locator('#action-form input[name="revision"]').inputValue();
  const published=await context.request.post('/table-publish',{form:{revision,payload:JSON.stringify({claims:['seer','latent','latent','latent','latent'],seers:[{day:1,reporter:1,target:2,color:'white'}],mediums:[]})}});
  assert(published.ok(),await published.text());await page.reload();
  await page.locator('[data-status-target="5"]').click();await page.locator('#advance-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 };
 const view=async()=>{await page.locator('[data-viewpoint-role="seer"]').click();await page.locator('tr[data-player="1"]').click();await page.waitForFunction(()=>document.querySelector('main').dataset.viewpointMode==='viewing');};
 const viewing=()=>page.waitForFunction(()=>document.querySelector('main').dataset.viewpointMode==='viewing');
 await setup('all');const publicCells=await page.locator('[data-value-cell]').allTextContents();
 const cookie=()=>context.cookies().then(v=>v.find(c=>c.name==='session').value);const before=await cookie();
 await view();assert.equal(await page.locator('[data-private-target="1"]').inputValue(),'2');assert.equal(await page.locator('[data-private-color="1"]').inputValue(),'white');
 for(const id of [3,4])assert(/\d+(\.\d+)?% \/ \d+(\.\d+)?%/.test(await page.locator(`tr[data-player="${id}"] [data-value-cell="final"]`).textContent()));
 assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="final"]').textContent(),'—');
 assert(await page.locator('#advance-button').isDisabled());
 if(process.env.WW_GG_SEER_SCREENSHOT)await page.screenshot({path:process.env.WW_GG_SEER_SCREENSHOT,fullPage:true});
 await page.locator('[data-private-color="1"]').selectOption('black');await viewing();assert((await page.locator('[data-viewpoint-status]').textContent()).startsWith('不整合'));
 await page.locator('[data-private-color="1"]').selectOption('white');await viewing();assert.equal(await cookie(),before);
 await page.locator('[data-viewpoint-role="public"]').click();assert.deepEqual(await page.locator('[data-value-cell]').allTextContents(),publicCells);
 await setup('none');await view();assert((await page.locator('[data-viewpoint-status]').textContent()).includes('なし開示'));
 assert.equal(await page.locator('tr[data-player="3"] [data-value-cell="final"]').textContent(),'未対応');
 // Requested five-player example: two seer COs, same initial white target.
 const multi=async()=>{
  await context.request.post('/start',{form:{citizens:'2',wolves:'2',seers:'1',day:'max',night:'random',initial_seer:'normal'}});
  await page.goto('/main');const revision=await page.locator('#action-form input[name="revision"]').inputValue();
  const response=await context.request.post('/table-publish',{form:{revision,payload:JSON.stringify({claims:['seer','seer','latent','latent','latent'],seers:[1,2].map(reporter=>({day:1,reporter,target:3,color:'white'})),mediums:[]})}});
  assert(response.ok(),await response.text());await page.reload();
 };
 await multi();if(await page.locator('[data-status-target="1"]').getAttribute('aria-pressed')!=='true')await page.locator('[data-status-target="1"]').click();
 await page.locator('#advance-button').click();await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});
 await page.locator('[data-viewpoint-role="seer"]').click();await page.locator('tr[data-player="2"]').click();await viewing();
 for(const id of [4,5])assert.equal(await page.locator(`tr[data-player="${id}"] [data-value-cell="final"]`).textContent(),'87.5% / 12.5%');
 if(process.env.WW_GG_MULTI_SCREENSHOT)await page.screenshot({path:process.env.WW_GG_MULTI_SCREENSHOT,fullPage:true});
 await multi();await page.locator('[data-status-target="3"]').click();await page.locator('#advance-button').click();await page.waitForSelector('main[data-screen="result"]');
 assert.equal(await page.locator('#board-viewpoint-seed').count(),0);
 // Real mixed-count Board: known wolf CO2, initial white3, execute7.
 const seven=async(target)=>{
  await context.request.post('/start',{form:{citizens:'4',wolves:'2',seers:'1',day:'max',night:'max',initial_seer:'normal'}});
  await page.goto('/main');const revision=await page.locator('#action-form input[name="revision"]').inputValue();
  const response=await context.request.post('/table-publish',{form:{revision,payload:JSON.stringify({claims:['seer','wolf','latent','latent','latent','latent','latent'],seers:[{day:1,reporter:1,target:3,color:'white'}],mediums:[]})}});
  assert(response.ok(),await response.text());await page.reload();await page.locator(`[data-status-target="${target}"]`).click();await page.locator('#advance-button').click();
  await page.waitForSelector('#board-viewpoint-seed',{state:'attached'});await view();
 };
 await seven(7);
 for(const id of [2,4,5,6])assert.equal(await page.locator(`tr[data-player="${id}"] [data-value-cell="final"]`).textContent(),'50% / 50%');
 await seven(3);
 for(const id of [2,4,5,6,7])assert.equal(await page.locator(`tr[data-player="${id}"] [data-value-cell="final"]`).textContent(),'33.33% / 66.67%');
 assert.deepEqual(errors,[]);await browser.close();console.log('Edge seer: prior scopes, double-CO same-white 7/8, terminal branch, actual 7-player mixed-count 1/2 and two-live-wolf 1/3 comparisons: PASS');
})().catch(e=>{console.error(e);process.exit(1);});
