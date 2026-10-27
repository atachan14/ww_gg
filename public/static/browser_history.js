"use strict";
(() => {
 const nativeFetch=window.fetch.bind(window),seedNode=document.getElementById('browser-history-seed');
 if(!seedNode)return;
 const seed=JSON.parse(seedNode.textContent),initialMain=document.querySelector('main'),restoreNote=document.createElement('p');restoreNote.setAttribute('role','status');restoreNote.textContent='ブラウザー履歴を復元中です';if(initialMain){initialMain.hidden=true;initialMain.before(restoreNote);}let state=null,db=null,resolveReady,rejectReady;
 const ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});ready.catch(()=>{});
 const abort=()=>new DOMException('Browser history changed','AbortError');
 function open(){return new Promise((resolve,reject)=>{const r=indexedDB.open('wwgg-browser-history-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('games',{keyPath:'game'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.onblocked=()=>reject(Error('Browser history storage is blocked'));});}
 function read(){return new Promise((resolve,reject)=>{const t=db.transaction('games','readonly'),r=t.objectStore('games').get(seed.game);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
 function save(result,expected){return new Promise((resolve,reject)=>{
  const t=db.transaction('games','readwrite'),s=t.objectStore('games'),r=s.get(seed.game);let updated=null,stale=false;
  r.onsuccess=()=>{const old=r.result;
   if(old&&old.token!==expected&&old.token!==result.browser_history){stale=true;t.abort();return;}
   const numbers={...(old?.numbers||{})};function label(value){if(!value||typeof value!=='object')return;if(value.node&&Object.hasOwn(value,'board_number')){numbers[value.node]??=Object.keys(numbers).length;value.board_number=numbers[value.node];}for(const child of Object.values(value))label(child);}label(result);
   updated={game:seed.game,numbers,token:result.browser_history,revision:result.browser_revision,routes:{...(old?.token===result.browser_history?old.routes:{}),...(result.browser_routes||{})}};s.put(updated);
  };
  t.oncomplete=()=>resolve(updated);t.onerror=()=>reject(t.error||Error('Browser history could not be saved'));t.onabort=()=>reject(stale?abort():t.error||Error('Browser history save was aborted'));
 });}
 function route(url){return url.origin===location.origin&&(['/navigation','/navigation/calculation','/game-tree','/game-tree/current','/table-preview','/table-publish'].includes(url.pathname)||/^\/navigation\/(move|back|forward|advance|phase-back|phase-next|public-input)$/.test(url.pathname));}
 async function unframe(response){
  if(response.headers.get('X-WW-Browser-Stream')!=='1')return response;
  const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',ended=false;
  async function event(){for(;;){const newline=pending.indexOf('\n');if(newline>=0){const line=pending.slice(0,newline);pending=pending.slice(newline+1);if(line)return JSON.parse(line);continue;}if(ended)return null;const part=await reader.read();pending+=decoder.decode(part.value||new Uint8Array(),{stream:!part.done});ended=part.done;}}
  let head;while((head=await event())&&head.event!=='browser-headers'){}if(!head)throw Error('Browser calculation ended without a response');
  const stream=new ReadableStream({async pull(controller){try{let item;while((item=await event())){if(item.event==='browser-chunk'){controller.enqueue(Uint8Array.from(atob(item.data),c=>c.charCodeAt(0)));return;}}controller.close();}catch(error){controller.error(error);}},cancel(reason){return reader.cancel(reason);}});
  return new Response(stream,{status:head.status,headers:head.headers});
 }
 async function wire(url,options={},bootstrap=false){
  if(!bootstrap)await ready;
  const before=state.token,headers=new Headers(options.headers||{});let body=options.body||'';
  if(body instanceof FormData){body=new URLSearchParams(body).toString();headers.set('Content-Type','application/x-www-form-urlencoded');}
  else if(body instanceof URLSearchParams){body=body.toString();headers.set('Content-Type','application/x-www-form-urlencoded');}
  if(typeof body!=='string')throw Error('Unsupported browser operation body');
  const keys=url.searchParams.getAll('node');if(url.pathname==='/game-tree/current'){const key=new URLSearchParams(body).get('node');if(key)keys.push(key);}
  const routes={};for(const key of keys){if(state.routes[key])routes[key]=state.routes[key];else if(!key.endsWith('~0'))throw Error('Tree route is unavailable; reload the Tree');}
  headers.set('Content-Type','application/json');headers.set('X-WW-Browser-Stream','1');
  const response=await unframe(await nativeFetch('/browser-history/request',{...options,method:'POST',headers,body:JSON.stringify({url:url.pathname+url.search,method:options.method||'GET',body,content_type:options.body instanceof FormData||options.body instanceof URLSearchParams?'application/x-www-form-urlencoded':new Headers(options.headers||{}).get('Content-Type')||'',token:before,routes})}));
  if(response.headers.get('Content-Type')?.includes('application/x-ndjson'))return response;
  if(!response.headers.get('Content-Type')?.includes('application/json'))return response;
  const result=await response.json();if(state.token!==before&&state.token!==result.browser_history)throw abort();
  if(response.ok&&result.browser_history){state=await save(result,before);}
  return new Response(JSON.stringify(result),{status:response.status,statusText:response.statusText,headers:response.headers});
 }
 window.fetch=(input,options={})=>{const url=new URL(typeof input==='string'?input:input.url,location.href);return route(url)?wire(url,options):nativeFetch(input,options);};
 window.BrowserHistory={ready};
 document.addEventListener('DOMContentLoaded',async()=>{
  try{
   db=await open();state=await read()||{game:seed.game,token:seed.token,revision:seed.revision,routes:{}};
   const response=await wire(new URL('/navigation',location.href),{headers:{'X-WW-Staged':'1'}},true),result=await response.json();
   if(!response.ok)throw Error(result.error);await window.BoardNavigation.install(result);const shown=document.querySelector('main');if(shown)shown.hidden=false;restoreNote.remove();resolveReady();
  }catch(error){restoreNote.textContent='ブラウザー履歴を復元・保存できません：'+error.message;rejectReady(error);const note=document.querySelector('[data-navigation-calculation-status]');if(note)note.textContent='ブラウザー履歴を復元・保存できません：'+error.message;}
 });
 window.addEventListener('pagehide',()=>document.dispatchEvent(new Event('board-table-dirty')));
})();
