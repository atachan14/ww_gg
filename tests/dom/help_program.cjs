const {chromium}=require('playwright'),assert=require('assert'),path=require('path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({baseURL:process.env.WW_GG_TEST_URL||'http://127.0.0.1:18801'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1280,375]){
  await page.setViewportSize({width,height:900});
  for(const slug of ['','current','model','flow','reference','verification','design','terms']){
   const r=await page.goto('/help/program/'+slug);assert(r.ok());
   assert.equal(await page.locator('h1').count(),1);assert(await page.locator('#program-content').isVisible());
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`body overflow: ${width} ${slug}`);
  }
  await page.goto('/help/program/flow');
  await page.screenshot({path:path.resolve('../help-program-'+width+'.png'),fullPage:true});
 }
 await page.goto('/help/program/');
 for(let i=0;i<5;i++){await page.keyboard.press('Tab');if(await page.locator('.program-skip').evaluate(e=>e===document.activeElement))break;}
 assert(await page.locator('.program-skip').evaluate(e=>e===document.activeElement));
 await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'program-content');
 const plain=await browser.newContext({javaScriptEnabled:false});const nojs=await plain.newPage();
 await nojs.goto((process.env.WW_GG_TEST_URL||'http://127.0.0.1:18801')+'/help/program/verification');
 assert((await nojs.locator('#eq-five').textContent()).includes('7/15'));
 assert.deepEqual(errors,[]);await browser.close();console.log('HELP: desktop/mobile, local overflow, keyboard skip, JS-free formula, no page errors: PASS');
})().catch(e=>{console.error(e);process.exit(1)});
