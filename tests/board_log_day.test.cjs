const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const text=fs.readFileSync('static/app.js','utf8'),source=text.slice(text.indexOf('function initializeBoardLog('),text.indexOf('function initializeUI('));
test('day filtering supports cached markup and leaves the evidence seed intact',()=>{
 const seed={textContent:JSON.stringify({day:2,seers:[{day:1,reporter:1,target:3,color:'white'}]})},original=seed.textContent;
 const row=(day,dataset={})=>({dataset,hidden:false,getAttribute:()=>`Day${day} public`});
 const rows=[row(1),row(2),row(1,{logDay:'2'})];const root={querySelector:s=>s==='#system-log'?{querySelectorAll:()=>rows}:seed};
 const context={};vm.createContext(context);vm.runInContext(source,context);context.initializeBoardLog(root);
 assert.deepEqual(rows.map(r=>r.hidden),[true,false,false]);assert.equal(seed.textContent,original);
 seed.textContent=JSON.stringify({day:1});context.initializeBoardLog(root);assert.deepEqual(rows.map(r=>r.hidden),[false,true,true]);
});
