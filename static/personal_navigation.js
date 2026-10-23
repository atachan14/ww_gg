"use strict";
(()=>{
 let context=null,generation=0,restoring=false;
 const storageKey='wwgg-personal-navigation';
 const save=()=>{try{if(context)sessionStorage.setItem(storageKey,JSON.stringify(context));else sessionStorage.removeItem(storageKey);}catch(_){}};
 const activate=(next,notify=true)=>{context=next;generation++;save();if(notify)document.dispatchEvent(new CustomEvent('personal-view-change'));};
 async function request(operation,extra={}){
  if(!context)throw Error('Personal view is not selected');
  const before=context,version=generation;
  const response=await fetch('/private-navigation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...extra,operation,view:before.view,public_revision:before.public_revision})});
  const result=await response.json();if(!response.ok)throw Object.assign(Error(result.error),{detail:result});
  if(version!==generation)throw new DOMException('View changed','AbortError');
  if(result.private_view){context={view:result.private_view,public_revision:result.public_revision};save();}
  return result;
 }
 async function install(result){
  if(result.private_view)activate({view:result.private_view,public_revision:result.public_revision},false);else activate(null,false);
  await window.BoardNavigation.install(result);
 }
 async function exit(){const result=await request('public');await install(result);document.dispatchEvent(new CustomEvent('personal-view-change'));}
 function bind(){
  const seed=document.querySelector('#personal-navigation-seed');
  if(!seed)return;
  if(seed.dataset.bound)return;seed.dataset.bound='1';
  const projection=JSON.parse(seed.textContent);
  activate({view:projection.view,public_revision:projection.public_revision},false);
  const main=seed.closest('main');main.dataset.personalNavigation='1';
  // This projection is a private cursor, not a public evidence editor.
  main.querySelectorAll('input,select,textarea,button').forEach(control=>{if(!control.closest('[data-calculation-tree]')&&!control.matches('[data-personal-public]')&&!control.closest('#display-options-form')&&control.getAttribute('form')!=='display-options-form'&&!control.matches('[name="probability-format"]'))control.disabled=true;});
  main.querySelectorAll('[data-scroll-to]').forEach(button=>button.disabled=false);
  const current=context.view.history.current,row=context.view.history.rows.find(row=>row.key===current);
  const back=main.querySelector('#back-button'),forward=main.querySelector('#advance-button');
  if(back)back.disabled=!row?.parent;
  if(forward)forward.disabled=!context.view.history.forward[current];
  if(projection.table){
   const probability=value=>{const node=document.createElement('strong'),formats=window.ProbabilityDisplay.formats(value);node.className='probability';node.dataset.fraction=formats.fraction;node.dataset.percent=formats.percent;let format;try{format=localStorage.getItem('ww_gg.probability-format');}catch(_){}node.textContent=window.ProbabilityDisplay.text(value,format);return node;};
   for(const player of projection.table.players){
    const row=main.querySelector(`tr[data-player="${player.id}"]`);
    for(const cell of row.querySelectorAll('[data-value-cell]')){
     const key=cell.dataset.valueCell;cell.replaceChildren();
     if(key in player.probabilities)cell.append(probability(player.probabilities[key]));
     else if(player[key])cell.append(probability(player[key].village),' / ',probability(player[key].wolf));
     else cell.textContent='?';
    }
   }
   for(const kind of ['dawn','final']){const cell=main.querySelector(`[data-value-cell="${kind}"]`);if(cell)cell.closest('table').tHead.rows[0].cells[cell.cellIndex].textContent=kind==='dawn'?'能力使用後・次の昼まで 村 / 狼':'能力使用後・最終 村 / 狼';}
  }
  main.querySelector('[data-table-scope]').textContent=({hunter:'狩人',seer:'占い師'}[context.view.role]||context.view.role)+' '+context.view.players.join(',')+' の視点';
  main.querySelector('[data-personal-public]').onclick=()=>exit().catch(error=>{main.querySelector('[data-personal-scope]').append(error.message);});
 }
 async function cold(){
  bind();if(context||restoring)return;
  let stored;try{stored=JSON.parse(sessionStorage.getItem(storageKey)||'null');}catch(_){}
  if(!stored)return;restoring=true;activate(stored,false);
  try{await install(await request('restore'));document.dispatchEvent(new CustomEvent('personal-view-change'));}
  catch(_){activate(null);}
  finally{restoring=false;}
 }
 window.PersonalNavigation={activate,request,install,exit,get context(){return context;},get generation(){return generation;}};
 document.addEventListener('navigation-board-change',bind);
 document.addEventListener('DOMContentLoaded',cold);
})();
