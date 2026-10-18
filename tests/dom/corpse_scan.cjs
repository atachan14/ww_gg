const {chromium}=require('playwright'),assert=require('assert'),fs=require('fs'),zlib=require('zlib');
function game(c){const v=c.find(x=>x.name==='session').value,p=v.split('.'),b=Buffer.from(p[v.startsWith('.')?1:0],'base64url');return JSON.parse((v.startsWith('.')?zlib.inflateSync(b):b).toString()).game;}
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{const c=await browser.newContext({baseURL:'http://127.0.0.1:18801'}),page=await c.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
const post=async(url,form,status)=>{const r=await c.request.post(url,{form,maxRedirects:0});assert.equal(r.status(),status,`${url}: ${await r.text()}`);};
await post('/start',{citizens:'3',mediums:'0',seers:'1',hunters:'0',wolves:'1',day:'random',night:'random',fake_reports:'random',initial_seer:'random_white'},303);
let g=game(await c.cookies());const claims=['seer','seer','latent','latent','latent'];
await post('/table-publish',{revision:String(g.revision),board_id:g.public_log.board_id,payload:JSON.stringify({claims,seers:[1,2].map(reporter=>({day:1,reporter,target:3,color:'white'})),mediums:[]})},200);
g=game(await c.cookies());await post('/advance',{revision:String(g.revision),target:'4',day:'random',night:'random'},303);
g=game(await c.cookies());await post('/dawn-report',{revision:String(g.revision),board_id:g.public_log.board_id,mode:'deaths',deaths:'5'},303);
g=game(await c.cookies());await post('/dawn-advance',{revision:String(g.revision),board_id:g.public_log.board_id},303);
g=game(await c.cookies());const payload={claims,seers:[1,2].flatMap(day=>[1,2].map(reporter=>({day,reporter,target:day===1?3:4,color:'white'}))),mediums:[]};
await post('/table-publish',{revision:String(g.revision),board_id:g.public_log.board_id,payload:JSON.stringify(payload)},200);
await page.goto('/main');await page.waitForFunction(()=>document.querySelector('#village-rate')?.dataset.fraction==='1/3',null,{timeout:15000});
const selector=page.locator('[data-table-target="2:1"]');assert.equal(await selector.inputValue(),'4');assert(await selector.locator('option[value="4"]').count());
fs.mkdirSync('.artifacts/corpse-browser',{recursive:true});await page.screenshot({path:'.artifacts/corpse-browser/white-corpse.png',fullPage:true});
const before=game(await c.cookies());await post('/advance',{revision:String(before.revision),target:'1',day:'random',night:'random'},303);assert.deepStrictEqual(game(await c.cookies()).seer_inputs,before.seer_inputs);
assert.deepStrictEqual(errors,[]);const result={isolatedHeadlessEdge:true,backend:'Python server; no Pyodide',corpseOptionRetained:true,corpseSelected:true,publicWin:'1/3',ownerLaterDeathRetainsPublishedResults:true,http:200,errors};fs.writeFileSync('benchmarks/player_match_groups/corpse-browser-results.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));await c.close();}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
