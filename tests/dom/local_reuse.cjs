const {chromium}=require('playwright'),assert=require('assert'),fs=require('fs'),path=require('path'),zlib=require('zlib');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'.artifacts/local-reuse-browser');fs.mkdirSync(out,{recursive:true});
function game(cookies){const v=cookies.find(c=>c.name==='session').value,p=v.split('.');const raw=Buffer.from(p[v.startsWith('.')?1:0],'base64url');return JSON.parse((v.startsWith('.')?zlib.inflateSync(raw):raw).toString()).game;}
async function rows(page){return page.locator('tr[data-player]').evaluateAll(xs=>xs.map(r=>({id:+r.dataset.player,...Object.fromEntries(['village','citizen','medium','seer','wolf'].map(k=>[k,r.querySelector(`[data-value-cell="${k}"] [data-fraction]`)?.dataset.fraction])),dawn:[...r.querySelectorAll('[data-value-cell="dawn"] [data-fraction]')].map(e=>e.dataset.fraction),final:[...r.querySelectorAll('[data-value-cell="final"] [data-fraction]')].map(e=>e.dataset.fraction)})));}
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const context=await browser.newContext({baseURL:process.env.WW_GG_TEST_URL||'http://127.0.0.1:18801'}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const start=await context.request.post('/start',{form:{citizens:'3',mediums:'1',seers:'1',hunters:'0',wolves:'2',day:'max',night:'max',fake_reports:'max',initial_seer:'random_white'},maxRedirects:0});assert.equal(start.status(),303);
 const g=game(await context.cookies()),payload={claims:['seer','seer','medium','latent','latent','latent','latent'],seers:[1,2].map(p=>({day:1,reporter:p,target:4,color:'white'})),mediums:[]};
 const publish=await context.request.post('/table-publish',{form:{revision:String(g.revision),board_id:g.public_log.board_id,payload:JSON.stringify(payload)}});assert.equal(publish.status(),200);
 const begun=Date.now();await page.goto('/main');await page.waitForFunction(()=>document.querySelector('#village-rate')?.dataset.fraction==='17/36',null,{timeout:60000});
 const initial=await rows(page),reference=JSON.parse(fs.readFileSync(path.join(root,'benchmarks/player_match_groups/actual-seven-extended-retirement.json'),'utf8')).result.table;
 const expected=reference.map(r=>({id:r.id,village:r.village_probability,citizen:r.citizen_probability,medium:r.medium_probability,seer:r.extra_probabilities.seer,wolf:r.wolf_probability,dawn:[r.by_dawn.village_win,r.by_dawn.wolf_win],final:[r.action.village_win,r.action.wolf_win]}));assert.deepStrictEqual(initial,expected);
 await page.screenshot({path:path.join(out,'initial-seven.png'),fullPage:true});
 const cold=await browser.newContext({baseURL:'http://127.0.0.1:18801',storageState:await context.storageState()}),other=await cold.newPage();await other.goto('/main');await other.waitForFunction(()=>document.querySelector('#village-rate')?.dataset.fraction==='17/36',null,{timeout:60000});assert.deepStrictEqual(await rows(other),initial);await cold.close();
 await page.locator('[data-table-target="1:1"]').selectOption('5',{force:true});await page.locator('[data-table-target="1:2"]').selectOption('5',{force:true});
 await page.waitForFunction(()=>document.querySelector('tr[data-player="5"] [data-value-cell="wolf"] [data-fraction]')?.dataset.fraction==='0',null,{timeout:60000});
 const interimFinal=await page.locator('tr[data-player="5"] [data-value-cell="final"] [data-fraction]').count();assert.equal(interimFinal,0,'roles frame must clear old action values');
 await page.waitForFunction(()=>document.querySelector('tr[data-player="5"] [data-value-cell="final"] .village-text [data-fraction]')?.dataset.fraction==='4/15',null,{timeout:60000});
 const edited=await rows(page),swapped=expected.map(r=>r.id===4?{...expected[4],id:4}:r.id===5?{...expected[3],id:5}:r);assert.deepStrictEqual(edited,swapped);assert.equal(await page.locator('#village-rate').getAttribute('data-fraction'),'17/36');
 const saved=game(await context.cookies());assert(saved.seer_inputs.every(r=>r.target===4),'preview must not publish');assert.deepStrictEqual(errors,[]);
 await page.screenshot({path:path.join(out,'draft-white-five.png'),fullPage:true});
 const result={isolatedHeadlessEdge:true,initialAllNumericCellsMatch:true,coldBrowserSameCookieMatches:true,editedRolesBeforeContinuation:true,staleActionCellsCleared:true,editedAllNumericCellsMatchRenamedReference:true,previewDidNotPublish:true,terminal:'17/36',seconds:(Date.now()-begun)/1000,errors};
 fs.writeFileSync(path.join(root,'benchmarks/player_match_groups/local-browser-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));await context.close();
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
