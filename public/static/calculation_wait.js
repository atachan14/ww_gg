"use strict";
(() => {
  const nativeFetch=window.fetch, writes=[], reads=new Map();let active=null, sequence=0, nativeSubmission=false;
  const note=document.createElement('div');note.className='calculation-wait';note.hidden=true;
  note.setAttribute('role','status');note.setAttribute('aria-live','polite');
  const aborted=()=>new DOMException('Superseded client request','AbortError');
  function paint(){
    if(!note.isConnected){const estimate=document.querySelector('.calculation-estimate');if(estimate)estimate.after(note);else document.body.append(note);}
    const busy=nativeSubmission||!!active||writes.length>0||reads.size>0;note.hidden=!busy;
    note.textContent=nativeSubmission?'送信済みの入力を反映中です。画面の確定をお待ちください。':active&&['/table-publish','/public-log'].includes(active.key)?'保存を確定しています。入力は保持されています。確定後に編集を続けられます。':'計算中も入力を編集できます。最新入力は進行中の応答後に計算します。1回の計算は最大約5分。通信の取消はサーバー計算の即時停止ではありません。';
    if(busy)document.body.setAttribute('aria-busy','true');else document.body.removeAttribute('aria-busy');
  }
  async function pump(){
    if(active)return;
    let task=writes.shift();
    if(!task&&reads.size){task=[...reads.values()].at(-1);reads.delete(task.key);}
    if(!task){paint();return;}
    if(task.cancelled){pump();return;}
    active=task;paint();
    try{
      // Caller abort invalidates its result. Keep the actual request alive and
      // retain this slot until its body drains; Abort is not server cancellation.
      const signal=new AbortController().signal;
      const input=task.input instanceof Request?new Request(task.input,{signal}):task.input;
      const response=await nativeFetch.call(window,input,{...task.init,signal});
      const streaming=response.headers.get('content-type')?.includes('application/x-ndjson');
      if(streaming&&!task.cancelled)task.resolve(response);
      await response.clone().arrayBuffer();
      if(!streaming&&!task.cancelled)task.resolve(response);
    }catch(error){if(!task.cancelled)task.reject(error);}
    finally{task.detach();active=null;queueMicrotask(pump);}
  }
  window.fetch=function(input,init={}){
    const url=new URL(input instanceof Request?input.url:String(input),location.href);
    const method=(init.method||(input instanceof Request?input.method:'GET')).toUpperCase();
    const streaming=new Headers(init.headers||(input instanceof Request?input.headers:undefined)).get('Accept')==='application/x-ndjson';
    if(url.origin!==location.origin||(method!=='POST'&&!streaming))return nativeFetch.apply(this,arguments);
    const readonly=['/main','/table-preview','/private-view','/comparison'].includes(url.pathname);
    const signal=init.signal||(input instanceof Request?input.signal:null);
    return new Promise((resolve,reject)=>{
      const task={input,init,key:url.pathname,resolve,reject,cancelled:false,sequence:++sequence,detach:()=>{}};
      const cancel=()=>{if(task.cancelled)return;task.cancelled=true;if(reads.get(task.key)===task)reads.delete(task.key);reject(aborted());paint();};
      task.cancel=cancel;
      if(signal?.aborted){cancel();return;}
      signal?.addEventListener('abort',cancel,{once:true});task.detach=()=>signal?.removeEventListener('abort',cancel);
      if(readonly){const old=reads.get(task.key);if(old){old.cancel();old.detach();}reads.set(task.key,task);}
      else writes.push(task); // Accepted edits/saves are never discarded/coalesced.
      paint();pump();
    });
  };
  window.readCalculationResponse=async(response,onRoles=()=>{})=>{
    if(!response.headers.get('content-type')?.includes('application/x-ndjson'))return response.json();
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',complete=null,roles=false;
    const consume=line=>{if(!line.trim())return;const event=JSON.parse(line);
      if(event.event==='error')throw Error(event.error||'計算が完了しませんでした。');
      if(event.event==='redirect'){location.assign(event.url);return;}
      if(event.event==='roles'){if(roles||complete)throw Error('計算応答の順序が不正です。');roles=true;onRoles(event);}
      else if(event.event==='complete'){if(complete)throw Error('計算応答が重複しました。');complete=event;}
    };
    try{while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let pos;while((pos=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,pos));buffer=buffer.slice(pos+1);}if(done)break;}consume(buffer);}
    finally{reader.releaseLock();}
    if(!complete)throw Error('計算応答が途中で終了しました。入力は保持されています。');return complete;
  };
  document.addEventListener('submit',event=>{
    if(!event.defaultPrevented&&event.target.method?.toLowerCase()==='post'){
      nativeSubmission=true;event.target.inert=true;paint();
    }
  });
})();
