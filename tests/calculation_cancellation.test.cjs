
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),crypto=require('node:crypto').webcrypto;
function fixture(){
 const events=[],listeners={},document={hidden:false,body:{prepend(){},setAttribute(){},removeAttribute(){}},createElement(){return {hidden:false,dataset:{},setAttribute(){},append(){},isConnected:true};},addEventListener(name,fn){listeners[name]=fn;}};
 let first=true,release;const nativeFetch=(input,init={})=>{
  const url=new URL(String(input),'http://localhost');
  if(url.pathname==='/calculation-cancel'){events.push('cancel-ack');return Promise.resolve(new Response('{}'));}
  events.push(url.pathname);
  if(first){first=false;const token=new Headers(init.headers).get('X-WW-Calculation-ID');if(url.pathname==='/table-preview')assert.match(token,/^[a-f0-9]{32}$/);return new Promise((resolve,reject)=>{release=()=>resolve(new Response('{}'));init.signal.addEventListener('abort',()=>{events.push('transport-abort');reject(new DOMException('stopped','AbortError'));});});}
  return Promise.resolve(new Response('{}'));
 };
 const window={fetch:nativeFetch,addEventListener(){}};
 vm.runInNewContext(fs.readFileSync('static/calculation_wait.js','utf8'),{window,document,location:new URL('http://localhost/main'),URL,URLSearchParams,Headers,Request,Response,DOMException,AbortController,TextDecoder,crypto,setTimeout,clearTimeout,queueMicrotask});
 return {window,events,release:()=>release()};
}
test('caller cancellation acknowledges server stop before next queued read starts',async()=>{
 const f=fixture(),controller=new AbortController();
 const old=f.window.fetch('/table-preview',{method:'POST',signal:controller.signal}).catch(e=>e.name);
 controller.abort();const next=f.window.fetch('/table-preview',{method:'POST'});
 assert.equal(await old,'AbortError');await next;
 assert.deepEqual(f.events,['/table-preview','cancel-ack','transport-abort','/table-preview']);
});
test('new save cancels obsolete computation, but accepted saves never cancel one another',async()=>{
 const f=fixture();const old=f.window.fetch('/table-preview',{method:'POST'}).catch(e=>e.name);
 const one=f.window.fetch('/table-publish',{method:'POST'}),two=f.window.fetch('/public-log',{method:'POST'});
 await Promise.all([old,one,two]);assert.deepEqual(f.events,['/table-preview','cancel-ack','transport-abort','/table-publish','/public-log']);
});
test('aborting a queued read does not cancel the active accepted write',async()=>{
 const f=fixture(),save=f.window.fetch('/table-publish',{method:'POST'}),controller=new AbortController();
 const read=f.window.fetch('/table-preview',{method:'POST',signal:controller.signal}).catch(e=>e.name);controller.abort();
 // The fixture's token assertion applies only to readonly calculations.
 f.release();await save;assert.equal(await read,'AbortError');assert.deepEqual(f.events,['/table-publish']);
});
