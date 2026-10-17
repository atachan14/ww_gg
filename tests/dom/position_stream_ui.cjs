const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('assert');
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({baseURL:'http://127.0.0.1:18801',viewport:{width:390,height:950}});
await context.addInitScript(()=>{
 const real=window.fetch;window.rolesGates=[];window.intervalCalls=0;const interval=window.setInterval;window.setInterval=function(...args){window.intervalCalls++;return interval.apply(this,args);};window.testHidden=false;Object.defineProperty(document,'hidden',{get:()=>window.testHidden});
 window.fetch=async function(input,init){const response=await real.call(this,input,init);
 if(!response.headers.get('content-type')?.includes('application/x-ndjson'))return response;
 const path=new URL(input instanceof Request?input.url:String(input),location.href).pathname;
 const reader=response.body.getReader(),decoder=new TextDecoder();let held=false,buffer='';
 return new Response(new ReadableStream({async start(controller){try{
 while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
 if(!held){const pos=buffer.indexOf('\n');if(pos>=0){const bufferFirst=buffer.slice(0,pos+1);controller.enqueue(new TextEncoder().encode(bufferFirst));buffer=buffer.slice(pos+1);held=true;const identity=JSON.parse(bufferFirst),gate={path,identity,count:0};gate.emit=overrides=>{const event={event:'position',run_id:identity.run_id,view:identity.view,board_id:identity.board_id,revision:identity.revision,request_id:identity.request_id,sample_id:++gate.count,depth:4,path:[{day:1,phase:'day'},{day:2,phase:'night'}],...overrides};controller.enqueue(new TextEncoder().encode(JSON.stringify(event)+'\n'));};window.rolesGates.push(gate);await new Promise(resolve=>gate.release=resolve);if(gate.fail)throw Error('fixture stream failure');}}
 if(held&&buffer){controller.enqueue(new TextEncoder().encode(buffer));buffer='';}if(done)break;
 }controller.close();}catch(error){controller.error(error);}finally{reader.releaseLock();}}}),{status:response.status,headers:response.headers});
 };
});
const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
const gate=path=>page.waitForFunction(path=>window.rolesGates?.some(x=>x.path===path&&x.release&&!x.used),path);
const emit=(path,overrides={})=>page.evaluate(({path,overrides})=>window.rolesGates.find(x=>x.path===path&&!x.used).emit(overrides),{path,overrides});
const release=(path,fail=false)=>page.evaluate(({path,fail})=>{const g=window.rolesGates.find(x=>x.path===path&&!x.used);g.used=true;g.fail=fail;g.release();},{path,fail});
const shown=()=>page.waitForSelector('.calculation-position:not([hidden])');
const hidden=()=>page.waitForFunction(()=>!document.querySelector('.calculation-position')||document.querySelector('.calculation-position').hidden);
await context.request.post('/start',{form:{citizens:'3',mediums:'1',wolves:'1',day:'max',night:'max'}});
await page.goto('/main');await gate('/main');await page.waitForSelector('[data-table-co="1"]');
await emit('/main');await shown();assert((await page.locator('.calculation-position').textContent()).includes('進捗率ではありません'));assert(!(await page.locator('.calculation-position').textContent()).includes('%'));
// The status survives the loading-main replacement and remains visible after scroll.
for(const width of [1366,390,320]){
 await page.setViewportSize({width,height:width===320?600:950});
 for(const bottom of [false,true]){
  await page.evaluate(bottom=>scrollTo({top:bottom?document.documentElement.scrollHeight:0,behavior:'instant'}),bottom);
  const geometry=await page.evaluate(()=>{const e=document.querySelector('.calculation-status'),p=document.querySelector('.calculation-position'),r=e.getBoundingClientRect(),pr=p.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,width:innerWidth,height:innerHeight,positionTop:pr.top,positionBottom:pr.bottom,sticky:getComputedStyle(e).position,pointer:getComputedStyle(e).pointerEvents,intercepts:e.contains(document.elementFromPoint(r.left+5,r.top+5)),overflow:document.documentElement.scrollWidth>innerWidth};});
  assert.equal(geometry.sticky,'sticky');assert.equal(geometry.pointer,'none');assert(!geometry.intercepts);assert(!geometry.overflow);
  assert(geometry.top>=0&&geometry.bottom<=geometry.height&&geometry.left>=0&&geometry.right<=geometry.width,JSON.stringify(geometry));
  assert(geometry.positionTop>=geometry.top&&geometry.positionBottom<=geometry.bottom);
 }
}
await page.setViewportSize({width:390,height:950});await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));
await emit('/main',{event:'position-unavailable'});await hidden();await emit('/main');await shown();
assert(await page.locator('[data-table-co="2"]').isEnabled());assert.equal(await page.locator('main').evaluate(e=>e.inert),false);
const sample=await page.locator('.calculation-position').getAttribute('data-sample-id');await emit('/main',{revision:999});await page.waitForTimeout(30);assert.equal(await page.locator('.calculation-position').getAttribute('data-sample-id'),sample);
await page.evaluate(()=>{window.testHidden=true;document.dispatchEvent(new Event('visibilitychange'));});await hidden();await emit('/main');await page.waitForTimeout(30);await hidden();
await page.evaluate(()=>{window.testHidden=false;document.dispatchEvent(new Event('visibilitychange'));});await emit('/main');await shown();
await page.locator('[data-table-co="1"]').selectOption('medium');await hidden();await emit('/main');await page.waitForTimeout(30);await hidden();await release('/main');
await gate('/table-preview');await emit('/table-preview');await shown();const oldRun=await page.locator('.calculation-position').getAttribute('data-run-id');await release('/table-preview',true);await hidden();assert.equal(await page.locator('[data-table-co="1"]').inputValue(),'medium');
await page.locator('[data-table-co="2"]').selectOption('villager');await gate('/table-preview');await emit('/table-preview',{run_id:oldRun});await page.waitForTimeout(30);await hidden();await emit('/table-preview');await shown();await release('/table-preview');await hidden();
// Private selection generations must exclude public and previous own-view positions.
await context.request.post('/start',{form:{citizens:'4',wolves:'1',day:'max',night:'max'}});
const state=await context.request.get('/main');const html=await state.text();const revision=html.match(/name="revision" value="(\d+)"/)[1];
await context.request.post('/advance',{form:{revision,target:'1',day:'max',night:'max'}});
await page.goto('/main');await gate('/main');await page.waitForSelector('[data-viewpoint-role="wolf"]');await release('/main');await page.waitForSelector('#village-rate[data-fraction="1/3"]');
await page.locator('[data-viewpoint-role="wolf"]').click();await page.locator('tr[data-player="2"]').click();await gate('/private-view');await emit('/private-view');await shown();assert((await page.locator('.calculation-position').textContent()).includes('狼本人'));
assert.equal(await page.locator('#village-rate').getAttribute('data-fraction'),'1/3');await page.locator('[data-viewpoint-role="public"]').click();await hidden();await emit('/private-view');await page.waitForTimeout(30);await hidden();await release('/private-view');
assert.equal(await page.evaluate(()=>window.intervalCalls),0);assert.deepEqual(errors,[]);
console.log(JSON.stringify({nonblocking:true,statusVisibleWhileScrolling:true,positionNotPercentage:true,staleRevisionRejected:true,staleRunRejected:true,hiddenStopsDOMAndNoIntervals:true,reeditHidesOldPosition:true,failureAndCompleteClear:true,privatePublicGenerationIsolated:true,errors}));await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
