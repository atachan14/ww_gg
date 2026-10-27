const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(process.env.WWGG_TEST_PERSONAL_SOURCE||'static/personal_navigation.js','utf8');
function fixture(browser=false){
 const stored={view:{role:'seer',revision:0},public_revision:0},events={},notices=[];let release,reject,resolveReady,rejectReady,calls=0;
 const ready=new Promise((a,b)=>{resolveReady=a;rejectReady=b;});ready.catch(()=>{});
 const window={BoardNavigation:{install(){throw Error('stale restore must never install');}}};if(browser)window.BrowserHistory={ready,personal:stored};
 const document={querySelector:()=>null,addEventListener:(name,fn)=>events[name]=fn,dispatchEvent:e=>notices.push(e.type)};
 const fetch=()=>{calls++;return new Promise((a,b)=>{release=a;reject=b;});};
 vm.runInNewContext(source,{window,document,fetch,sessionStorage:{getItem:()=>JSON.stringify(stored),setItem(){},removeItem(){}},DOMException,CustomEvent:class{constructor(type){this.type=type;}},JSON,Error});
 return {window,notices,start:()=>events.DOMContentLoaded(),release:()=>release(new Response(JSON.stringify({private_view:stored.view,public_revision:0}),{headers:{'Content-Type':'application/json'}})),fail:()=>reject(Error('old restore failed')),resolveReady,rejectReady,get calls(){return calls;}};
}
test('old failed cold restore cannot clear a newer selected observer',async()=>{const f=fixture(),done=f.start(),newer={view:{role:'wolf',revision:2},public_revision:0};f.window.PersonalNavigation.activate(newer);f.fail();await done;assert.equal(f.window.PersonalNavigation.context,newer);assert.equal(f.window.PersonalNavigation.generation,2);});
test('old successful restore rejected by generation cannot clear a newer observer',async()=>{const f=fixture(),done=f.start(),newer={view:{role:'hunter',revision:1},public_revision:0};f.window.PersonalNavigation.activate(newer);f.release();await done;assert.equal(f.window.PersonalNavigation.context,newer);});
test('failure of the current restore still clears its own failed context',async()=>{const f=fixture(),done=f.start();f.fail();await done;assert.equal(f.window.PersonalNavigation.context,null);});
test('browser public restoration failure does not leak an unhandled personal restore',async()=>{const f=fixture(true),done=f.start();f.rejectReady(Error('storage failed'));await done;assert.equal(f.calls,0);assert.equal(f.window.PersonalNavigation.context,null);});
test('new selection while public restoration is pending prevents a cold overwrite',async()=>{const f=fixture(true),done=f.start(),newer={view:{role:'seer',revision:3},public_revision:1};f.window.PersonalNavigation.activate(newer);f.resolveReady();await done;assert.equal(f.calls,0);assert.equal(f.window.PersonalNavigation.context,newer);});
