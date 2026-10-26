"use strict";
(() => {
 let busy=false,generation=0,controller=null;
 const main=()=>document.querySelector('main[data-navigation-occurrence]');
 function applyValues(doc){
  const scroll={x:window.scrollX,y:window.scrollY},anchor=document.activeElement,anchorTop=anchor&&anchor!==document.body?anchor.getBoundingClientRect().top:null;
  const remote=typeof doc==='string'?new DOMParser().parseFromString(doc,'text/html'):doc;
  const overview=document.querySelector('#information-panel'),next=remote.querySelector('#information-panel');if(overview&&next)overview.innerHTML=next.innerHTML;
  for(const row of document.querySelectorAll('.player-table tr[data-player]')){const source=remote.querySelector('.player-table tr[data-player="'+row.dataset.player+'"]');if(!source)continue;for(const cell of row.querySelectorAll('[data-value-cell]')){const value=source.querySelector('[data-value-cell="'+cell.dataset.valueCell+'"]');if(value)cell.innerHTML=value.innerHTML;}}
  const groups=document.querySelector('[data-hybrid-groups]'),nextGroups=remote.querySelector('[data-hybrid-groups]');groups?.remove();if(nextGroups)document.querySelector('#action-form')?.append(nextGroups.cloneNode(true));
  const fraction=document.querySelector('[name="probability-format"]:checked')?.value==='fraction';document.querySelectorAll('.probability[data-fraction]').forEach(e=>{e.textContent=fraction?e.dataset.fraction:e.dataset.percent;});
  window.refreshParallelLayout?.();if(anchorTop!==null&&anchor.isConnected)window.scrollBy(0,anchor.getBoundingClientRect().top-anchorTop);else window.scrollTo(scroll.x,scroll.y);
 }
 function stopCalculation(){++generation;controller?.abort();controller=null;}
 async function calculate(){
  const root=main();if(!root||window.PersonalNavigation?.context||root.dataset.navigationCalculation==='complete'||window.boardTableDraft?.isDirty())return;
  stopCalculation();const run=generation,occurrence=root.dataset.navigationOccurrence,revision=root.dataset.navigationRevision;
  const live=event=>run===generation&&root.isConnected&&root===main()&&root.dataset.navigationOccurrence===occurrence&&root.dataset.navigationRevision===revision&&(!event||(event.occurrence===occurrence&&String(event.revision)===revision&&String(event.request_id)===String(run)));
  controller=new AbortController();root.dataset.navigationCalculation='running';const note=root.querySelector('[data-navigation-calculation-status]');if(note)note.textContent='勝率計算中';root.querySelector('[data-navigation-retry]')?.setAttribute('hidden','');
  try{
   const query=new URLSearchParams({occurrence,revision,request_id:String(run),details:new URL(location.href).searchParams.get('details')||'0'});const response=await fetch('/navigation/calculation?'+query,{headers:{Accept:'application/x-ndjson'},signal:controller.signal});
   const result=await window.readCalculationResponse(response,event=>{if(live(event)&&!window.boardTableDraft?.isDirty()){applyValues(event.html);root.dataset.navigationRoles='ready';document.dispatchEvent(new CustomEvent('navigation-roles-ready',{detail:event}));}},event=>{if(live(event))window.showCalculationPosition?.(event);});
   if(!live(result))return;if(!response.ok)throw Error(result.error);
   if(!window.boardTableDraft?.isDirty()){
    applyValues(result.html);
    const remote=new DOMParser().parseFromString(result.html,'text/html'),advance=root.querySelector('#advance-button'),next=remote.querySelector('#advance-button');if(advance&&next)advance.disabled=next.disabled;
    if(root.querySelector('#action-form')?.dataset.manualSelection!=='true'){
     for(const input of root.querySelectorAll('input[name="target"]'))input.checked=!!remote.querySelector('input[name="target"][value="'+input.value+'"]')?.checked;
     window.updateTargetPreview?.();
    }
   }
   if(!window.boardTableDraft?.isDirty())window.boardTableDraft?.refreshBaseline?.();
   root.dataset.navigationCalculation=result.value_complete?'complete':'blocked';root.dataset.navigationDetails=result.details_complete?'complete':'pending';
   const status=root.querySelector('[data-navigation-calculation-status]');if(status)status.textContent=result.value_complete?'':'勝率未計算';
   document.dispatchEvent(new CustomEvent('navigation-calculation-complete',{detail:result}));
   if(result.value_complete)document.dispatchEvent(new CustomEvent('navigation-board-change',{detail:{calculation_complete:true}}));
  }catch(error){if(live()&&error.name!=='AbortError'){root.dataset.navigationCalculation='failed';const note=root.querySelector('[data-navigation-calculation-status]');if(note)note.textContent='勝率未計算：'+error.message;root.querySelector('[data-navigation-retry]')?.removeAttribute('hidden');}}
  finally{if(run===generation)controller=null;}
 }
 async function install(result){
  stopCalculation();const old=main();if(!old||!result.html)throw Error('Current Board response is missing');
  const doc=new DOMParser().parseFromString(result.html,'text/html'),next=doc.querySelector('main');
  if(!next)throw Error('Current Board response is invalid');
  const scroll={x:window.scrollX,y:window.scrollY},focused=document.activeElement;
  const focusKey=focused?.dataset.tableCo?['data-table-co',focused.dataset.tableCo]:focused?.dataset.tableTarget?['data-table-target',focused.dataset.tableTarget]:focused?.id?['id',focused.id]:null;
  // A Current change remounts its controls, but the public Panel roots and Tree
  // retain their DOM identity; calculation-only updates never remount controls.
  for(const selector of ['#information-panel','#player-panel','.phase-footer']){const panel=old.querySelector(selector),replacement=next.querySelector(selector);if(panel&&replacement){panel.replaceChildren(...replacement.childNodes);for(const attr of [...panel.attributes])if(!replacement.hasAttribute(attr.name))panel.removeAttribute(attr.name);for(const attr of replacement.attributes)panel.setAttribute(attr.name,attr.value);replacement.replaceWith(panel);}}
  const tree=old.querySelector('[data-calculation-tree]');
  window.boardTableDraft?.suspend?.();
  if(tree)next.querySelector('[data-calculation-tree]')?.replaceWith(tree);
  old.replaceWith(next);document.title=doc.title;
  bind();window.initializeUI?.();if(focusKey)next.querySelector('['+focusKey[0]+'="'+CSS.escape(focusKey[1])+'"]')?.focus({preventScroll:true});window.scrollTo(scroll.x,scroll.y);
  document.dispatchEvent(new CustomEvent('navigation-board-change',{detail:result}));if(next.dataset.navigationCalculation==='pending')calculate();
 }
 async function send(operation,payload={}){
  if(busy)return;busy=true;
  try{
   if(window.PersonalNavigation?.context){const result=await window.PersonalNavigation.request(operation==='advance'?'forward':operation);await window.PersonalNavigation.install(result);return result;}
   const response=await fetch('/navigation/'+operation,{method:'POST',headers:{'Content-Type':'application/json','X-WW-Staged':'1'},body:JSON.stringify({revision:Number(main().dataset.navigationRevision),...payload})});
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
   send(operation==='back'?'phase-back':'phase-next',payload).catch(error=>{const status=document.querySelector('[data-table-preview-status]');if(status)status.textContent=error.message;});
  },true);
 }
 window.BoardNavigation={install,send,applyValues,calculate};document.addEventListener('DOMContentLoaded',()=>{bind();if(main()?.dataset.navigationCalculation==='pending')calculate();});
 document.addEventListener('click',event=>{if(event.target.closest('[data-navigation-retry]'))calculate();});
 document.addEventListener('board-table-dirty',()=>{if(controller){stopCalculation();if(main())main().dataset.navigationCalculation='paused';}});
 document.addEventListener('board-table-clean',()=>{if(['paused','failed'].includes(main()?.dataset.navigationCalculation))calculate();});
 document.addEventListener('personal-view-loading',stopCalculation);
})();
