"use strict";
(() => {
  const nativeFetch=window.fetch, writes=[], reads=new Map();let active=null, sequence=0, nativeSubmission=false;
  const status=document.createElement('aside');status.className='calculation-status';status.hidden=true;
  const note=document.createElement('div');note.className='calculation-wait';note.hidden=true;status.append(note);
  const mountStatus=()=>{if(!status.isConnected)document.body.prepend(status);};
  note.setAttribute('role','status');note.setAttribute('aria-live','polite');
  const aborted=()=>new DOMException('Superseded client request','AbortError');
  function paint(){
    mountStatus();
    const busy=nativeSubmission||!!active||writes.length>0||reads.size>0;note.hidden=!busy;
    note.textContent=nativeSubmission?'入力を送信しました。画面の更新を待っています。':active&&['/table-publish','/public-log'].includes(active.key)?'入力を保存しています。変更は保持しています。':active?.cancelled?'前の計算の終了待ちです。最新の入力は保持しています。':'計算中です。入力は編集できます。';
    status.hidden=!busy&&position.hidden;
    if(busy)document.body.setAttribute('aria-busy','true');else document.body.removeAttribute('aria-busy');
  }
  // These are transport guards, not server cancellation or mathematical deadlines.
  const TRANSPORT_DEADLINE_MS=330000, STREAM_IDLE_MS=45000, transportFailures=new WeakMap();
  const cancelBody=body=>{if(body&&!body.locked)body.cancel().catch(()=>{});};
  async function drainCalculationStream(response,onChunk,onLiveness){
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    const terminal=line=>{if(!line.trim())return false;const event=JSON.parse(line);if(['heartbeat','position','position-unavailable'].includes(event.event))onLiveness();return ['complete','error','redirect'].includes(event.event);};
    try{while(true){const {value,done}=await reader.read();onChunk();buffer+=decoder.decode(value,{stream:!done});let pos;while((pos=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,pos);buffer=buffer.slice(pos+1);if(terminal(line))return;}if(done){if(buffer.trim())terminal(buffer);return;}}}
    finally{reader.cancel().catch(()=>{});reader.releaseLock();}
  }
  async function pump(){
    if(active)return;
    let task=writes.shift();
    if(!task&&reads.size){task=[...reads.values()].at(-1);reads.delete(task.key);}
    if(!task){paint();return;}
    if(task.cancelled){pump();return;}
    active=task;paint();
    const transport=new AbortController();let failure=null,idle=null;
    task.stop=()=>{
      if(!task.readonly||task.stopping)return;
      task.stopping=true;
      // Ask the owning server worker to stop at its next cooperative check.
      // Only abort transport after acknowledgement; writes remain serialized.
      nativeFetch.call(window,'/calculation-cancel',{method:'POST',body:new URLSearchParams({calculation_id:task.id}),credentials:'same-origin'})
        .then(response=>{if(response.ok)transport.abort();})
        .catch(()=>{}); // On unavailable cancellation keep the slot until EOF.
    };
    const expire=kind=>{failure=Object.assign(new Error(kind==='idle'?'計算の通信が停止しました。入力は保持しています。再計算してください。':'計算の通信が時間切れになりました。入力は保持しています。処理結果を確認してください。'),{name:'CalculationTransportTimeout'});transport.abort();};
    const deadline=setTimeout(()=>expire('deadline'),TRANSPORT_DEADLINE_MS);
    const armIdle=()=>{clearTimeout(idle);idle=setTimeout(()=>expire('idle'),STREAM_IDLE_MS);};
    try{
      // The server receives the request ID before computation. Cancellation
      // uses a separate unqueued request and the same session owner.
      const signal=transport.signal;
      const input=task.input instanceof Request?new Request(task.input,{signal}):task.input;
      const headers=new Headers(task.init.headers||(input instanceof Request?input.headers:undefined));
      if(task.readonly)headers.set('X-WW-Calculation-ID',task.id);
      const response=await nativeFetch.call(window,input,{...task.init,headers,signal});
      const streaming=response.headers.get('content-type')?.includes('application/x-ndjson');
      task.response=response;transportFailures.set(response,()=>failure||(task.cancelled?aborted():null));
      if(streaming){
        const copy=response.clone();
        if(!task.cancelled)task.resolve(response);else cancelBody(response.body);
        await drainCalculationStream(copy,()=>{if(idle!==null)armIdle();},armIdle);
      }else await response.clone().arrayBuffer();
      if(!streaming&&!task.cancelled)task.resolve(response);
    }catch(error){if(!task.cancelled)task.reject(failure||error);}
    finally{clearTimeout(deadline);clearTimeout(idle);task.detach();active=null;queueMicrotask(pump);}
  }
  window.fetch=function(input,init={}){
    const url=new URL(input instanceof Request?input.url:String(input),location.href);
    const method=(init.method||(input instanceof Request?input.method:'GET')).toUpperCase();
    const streaming=new Headers(init.headers||(input instanceof Request?input.headers:undefined)).get('Accept')==='application/x-ndjson';
    const treeRead=url.pathname==='/game-tree'&&method==='GET';
    if(url.origin!==location.origin||(method!=='POST'&&!streaming&&!treeRead))return nativeFetch.apply(this,arguments);
    const readonly=treeRead||['/main','/table-preview','/private-view','/comparison','/navigation/calculation'].includes(url.pathname);
    const signal=init.signal||(input instanceof Request?input.signal:null);
    return new Promise((resolve,reject)=>{
      const task={input,init,key:treeRead?url.pathname+url.search:url.pathname,readonly,id:readonly?crypto.randomUUID().replaceAll('-',''):null,resolve,reject,cancelled:false,sequence:++sequence,detach:()=>{}};
      const cancel=()=>{if(task.cancelled)return;task.cancelled=true;cancelBody(task.response?.body);if(reads.get(task.key)===task)reads.delete(task.key);reject(aborted());task.stop?.();paint();};
      task.cancel=cancel;
      if(signal?.aborted){cancel();return;}
      signal?.addEventListener('abort',cancel,{once:true});task.detach=()=>signal?.removeEventListener('abort',cancel);
      if(active?.readonly&&(!readonly||!treeRead&&(active.key===task.key||['/main','/navigation/calculation'].includes(active.key))))active.cancel();
      if(readonly){const old=reads.get(task.key);if(old){old.cancel();old.detach();}reads.set(task.key,task);}
      else writes.push(task); // Accepted edits/saves are never discarded/coalesced.
      paint();pump();
    });
  };
  const position=document.createElement('p');position.className='calculation-position';position.hidden=true;position.setAttribute('role','status');
  status.append(position);
  let positionRun=null;
  window.hideCalculationPosition=run=>{if(!run||run===positionRun){position.hidden=true;positionRun=null;position.textContent='';position.title='';delete position.dataset.runId;delete position.dataset.sampleId;paint();}};
  window.showCalculationPosition=event=>{
    if(document.hidden||nativeSubmission)return;
    if(!Array.isArray(event.path)||!event.path.length||event.path.length>12||!Number.isInteger(event.depth)||event.depth<event.path.length||event.path.some(step=>!Number.isInteger(step.day)||step.day<1||!['day','night'].includes(step.phase)))return;
    mountStatus();status.hidden=false;
    const current=event.path?.at(-1);if(!current)return;
    const viewLabel={public:'公開',wolf:'人狼本人',seer:'占い本人',hunter:'狩人本人'}[event.view];if(!viewLabel)return;
    positionRun=event.run_id;position.hidden=false;
    position.textContent=`探索位置［${viewLabel}］：Day ${current.day} ${current.phase==='day'?'昼':'夜'}・呼出し深さ ${event.depth}（進捗率ではありません）`;
    position.dataset.runId=event.run_id;position.dataset.sampleId=String(event.sample_id);
    position.title='採取時の評価呼出し経路（保存履歴ではありません）：'+event.path.map(step=>`Day ${step.day} ${step.phase==='day'?'昼':'夜'}`).join(' → ');
  };
  document.addEventListener('visibilitychange',()=>{if(document.hidden)window.hideCalculationPosition();});
  for(const name of ['change','strategychange','viewpointchange','board-table-dirty'])document.addEventListener(name,()=>window.hideCalculationPosition(),true);
  window.addEventListener('pagehide',()=>window.hideCalculationPosition());
  window.readCalculationResponse=async(response,onRoles=()=>{},onPosition=()=>{})=>{
    if(!response.headers.get('content-type')?.includes('application/x-ndjson'))return response.json();
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',complete=null,roles=false,identity=null,redirected=false;
    const consume=line=>{if(!line.trim())return;const event=JSON.parse(line);
      if(event.event==='error')throw Error(event.error||'計算が完了しませんでした。');
      if(event.event==='redirect'){redirected=true;location.assign(event.url);return;}
      if(event.event==='roles'){if(roles||complete)throw Error('計算応答の順序が不正です。');roles=true;identity={run_id:event.run_id,board_id:event.board_id,revision:event.revision,view:event.view,request_id:event.request_id};onRoles(event);}
      else if(event.event==='position-unavailable'){if(identity&&event.run_id===identity.run_id)window.hideCalculationPosition(event.run_id);}
      else if(event.event==='position'){if(identity&&!complete&&event.run_id===identity.run_id&&event.board_id===identity.board_id&&event.revision===identity.revision&&event.view===identity.view&&event.request_id===identity.request_id)onPosition(event);}
      else if(event.event==='complete'){if(complete)throw Error('計算応答が重複しました。');complete=event;}
    };
    try{while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let pos;while((pos=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,pos));buffer=buffer.slice(pos+1);if(complete||redirected)break;}if(done||complete||redirected)break;}if(!complete&&!redirected)consume(buffer);}
    catch(error){throw transportFailures.get(response)?.()||error;}
    finally{reader.cancel().catch(()=>{});reader.releaseLock();if(identity?.run_id)window.hideCalculationPosition(identity.run_id);}
    if(!complete)throw transportFailures.get(response)?.()||Error('計算応答が途中で終了しました。入力は保持されています。');return complete;
  };
  document.addEventListener('submit',event=>{
    if(!event.defaultPrevented&&event.target.method?.toLowerCase()==='post'){
      nativeSubmission=true;window.hideCalculationPosition();event.target.inert=true;paint();
    }
  });
})();
