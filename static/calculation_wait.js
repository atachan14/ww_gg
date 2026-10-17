"use strict";
(() => {
  let pending=0, savedInert=false;
  const note=document.createElement('div');note.className='calculation-wait';note.hidden=true;
  note.setAttribute('role','status');note.setAttribute('aria-live','polite');
  note.textContent='計算中です。条件により最大約5分かかります。通信を閉じてもサーバーの計算はすぐには止まりません。';
  document.body.append(note);
  function show(){if(pending++===0){const main=document.querySelector('main');if(main){savedInert=main.inert;main.inert=true;}note.hidden=false;document.body.setAttribute('aria-busy','true');}}
  function hide(){pending=Math.max(0,pending-1);if(!pending){const main=document.querySelector('main');if(main)main.inert=savedInert;note.hidden=true;document.body.removeAttribute('aria-busy');}}
  const nativeFetch=window.fetch;
  window.fetch=async function(input,init){
    const url=new URL(input instanceof Request?input.url:String(input),location.href);
    const method=(init?.method||input?.method||'GET').toUpperCase();
    const calculating=url.origin===location.origin&&method==='POST';
    if(!calculating)return nativeFetch.apply(this,arguments);
    if(pending)throw Error('計算中です。現在の応答をお待ちください。');
    show();try{return await nativeFetch.apply(this,arguments);}finally{hide();}
  };
  document.addEventListener('submit',event=>{
    if(event.defaultPrevented||event.target.method?.toLowerCase()!=='post')return;
    if(pending){event.preventDefault();return;}show();
  });
  window.addEventListener('pageshow',event=>{if(event.persisted){pending=1;hide();}});
})();
