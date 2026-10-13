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
 assert.deepEqual(errors,[]);await browser.close();console.log('Edge seer: CO/all numeric comparison, first-copy past results, visited target exclusion, contradiction correction, public identity, none Pending: PASS');
})().catch(e=>{console.error(e);process.exit(1);});
