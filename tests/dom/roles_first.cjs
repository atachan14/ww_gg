const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('assert');
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({baseURL:'http://127.0.0.1:18801',viewport:{width:390,height:950}});
await context.addInitScript(()=>{
 const real=window.fetch;window.rolesGates=[];
 window.fetch=async function(input,init){const response=await real.call(this,input,init);
 if(!response.headers.get('content-type')?.includes('application/x-ndjson'))return response;
 const path=new URL(input instanceof Request?input.url:String(input),location.href).pathname;
 const reader=response.body.getReader(),decoder=new TextDecoder();let held=false,buffer='';
 return new Response(new ReadableStream({async start(controller){try{
 while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
 if(!held){const pos=buffer.indexOf('\n');if(pos>=0){controller.enqueue(new TextEncoder().encode(buffer.slice(0,pos+1)));buffer=buffer.slice(pos+1);held=true;const gate={path};window.rolesGates.push(gate);await new Promise(resolve=>gate.release=resolve);if(gate.fail)throw Error('fixture stream failure');}}
 if(held&&buffer){controller.enqueue(new TextEncoder().encode(buffer));buffer='';}if(done)break;
 }controller.close();}catch(error){controller.error(error);}finally{reader.releaseLock();}}}),{status:response.status,headers:response.headers});
 };
});
const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
const gate=path=>page.waitForFunction(path=>window.rolesGates?.some(x=>x.path===path&&x.release&&!x.used),path);
const release=(path,fail=false)=>page.evaluate(({path,fail})=>{const g=window.rolesGates.find(x=>x.path===path&&x.release&&!x.used);if(!g)throw Error('missing gate');g.used=true;g.fail=fail;g.release();},{path,fail});
await context.request.post('/start',{form:{citizens:'3',mediums:'1',wolves:'1',day:'max',night:'max'}});
await page.goto('/main');await gate('/main');await page.waitForSelector('[data-table-co="1"]');
assert(await page.locator('tr[data-player="1"] [data-value-cell="wolf"] .probability').getAttribute('data-fraction')==='1/5');
assert.equal(await page.locator('#village-rate[data-fraction]').count(),0);
await release('/main');await page.waitForSelector('#village-rate[data-fraction="7/15"]');
// A draft edited after initial roles must survive the obsolete final event.
await page.reload();await gate('/main');await page.waitForSelector('[data-table-co="1"]');
await page.locator('[data-table-co="1"]').selectOption('medium');await release('/main');
await gate('/table-preview');await page.waitForSelector('tr[data-player="1"] [data-value-cell="medium"] .probability[data-fraction="1"]');
assert.equal(await page.locator('[data-table-co="1"]').inputValue(),'medium');
await release('/table-preview',true);await page.waitForFunction(()=>document.querySelector('[data-table-preview-status]').textContent.includes('fixture stream failure'));
assert.equal(await page.locator('tr[data-player="1"] [data-value-cell="medium"] .probability').getAttribute('data-fraction'),'1');
assert.equal(await page.locator('[data-table-co="1"]').inputValue(),'medium');
// A new game does not inherit that unsaved declaration.
await context.request.post('/start',{form:{citizens:'4',wolves:'1',day:'max',night:'max'}});
const state=await context.request.get('/main');const html=await state.text();const revision=html.match(/name="revision" value="(\d+)"/)[1];
await context.request.post('/advance',{form:{revision,target:'1',day:'max',night:'max'}});
await page.goto('/main');await gate('/main');await page.waitForSelector('[data-viewpoint-role="wolf"]');await release('/main');await page.waitForSelector('#village-rate[data-fraction="1/3"]');
const publicRate=await page.locator('#village-rate').getAttribute('data-fraction');
await page.locator('[data-viewpoint-role="wolf"]').click();await page.locator('tr[data-player="2"]').click();await gate('/private-view');
await page.waitForSelector('tr[data-player="2"] [data-value-cell="wolf"] .probability[data-fraction="1"]');
assert.equal(await page.locator('#village-rate').getAttribute('data-fraction'),publicRate);
await release('/private-view',true);await page.waitForFunction(()=>document.querySelector('[data-viewpoint-status]').textContent.includes('fixture stream failure'));
assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="wolf"] .probability').getAttribute('data-fraction'),'1');
await page.locator('[data-viewpoint-role="public"]').click();assert.equal(await page.locator('#village-rate').getAttribute('data-fraction'),publicRate);
assert.equal(await page.locator('tr[data-player="2"] [data-value-cell="wolf"] .probability').getAttribute('data-fraction'),'1/4');
assert.deepEqual(errors,[]);console.log(JSON.stringify({initialRolesBeforeWins:true,obsoleteInitialIgnored:true,draftPreservedAfterStreamFailure:true,privateRolesBeforeWins:true,privateFailureKeepsRoles:true,publicUnchanged:true,errors}));
await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
