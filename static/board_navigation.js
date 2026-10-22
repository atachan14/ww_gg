"use strict";
(() => {
 let busy=false;
 const main=()=>document.querySelector('main[data-navigation-occurrence]');
 async function install(result){
  const old=main();if(!old||!result.html)throw Error('Current Board response is missing');
  const doc=new DOMParser().parseFromString(result.html,'text/html'),next=doc.querySelector('main');
  if(!next)throw Error('Current Board response is invalid');
  const tree=old.querySelector('[data-calculation-tree]');
  window.boardTableDraft?.suspend?.();
  if(tree)next.querySelector('[data-calculation-tree]')?.replaceWith(tree);
  old.replaceWith(next);document.title=doc.title;
  bind();window.initializeUI?.();
  document.dispatchEvent(new CustomEvent('navigation-board-change',{detail:result}));
 }
 async function send(operation,payload={}){
  if(busy)return;busy=true;
  try{
   const response=await fetch('/navigation/'+operation,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:Number(main().dataset.navigationRevision),...payload})});
   const result=await response.json();if(!response.ok)throw Error(result.error);await install(result);return result;
  }finally{busy=false;}
 }
 function bind(){const root=main();if(!root||root.dataset.navigationBound)return;root.dataset.navigationBound='1';
  root.addEventListener('submit',event=>{
   const form=event.target,path=new URL(form.action,location.href).pathname;
   if(!['/advance','/back'].includes(path))return;
   event.preventDefault();event.stopImmediatePropagation();
   if(window.boardTableDraft?.isDirty()){document.querySelector('[data-table-preview-status]').textContent='先に更新またはキャンセルしてください';return;}
   if(!form.checkValidity()){form.reportValidity();return;}
   const values=new FormData(form),operation=path==='/back'?'back':'advance',payload=operation==='advance'?{target:Number(values.get('target')),reuse_forward:form.dataset.manualSelection!=='true'}:{};
   send(operation,payload).catch(error=>{const status=document.querySelector('[data-table-preview-status]');if(status)status.textContent=error.message;});
  },true);
 }
 window.BoardNavigation={install,send};document.addEventListener('DOMContentLoaded',bind);
})();
