/* Private evidence row; callers provide valid past-day slots and target lists. */
(() => {
 window.renderBoardPrivateRow=({table,player,role,label,slots,draft,onChange})=>{
  const owner=table.querySelector(`tr[data-player="${player}"]`);if(!owner)throw Error('Missing private row owner');
  table.querySelector(`[data-private-details="${player}:${role}"]`)?.remove();
  const row=document.createElement('tr');row.dataset.privateDetails=`${player}:${role}`;row.className='co-detail-row private-detail-row';
  const spacer=document.createElement('td'),name=document.createElement('td'),cell=document.createElement('td');
  name.textContent=`秘密情報 · ${label}`;cell.dataset.privateResults='';cell.colSpan=[...table.tHead.rows[0].cells].filter(c=>!c.hidden).length-2;
  row.append(spacer,name,cell);
  let current=JSON.parse(JSON.stringify(draft.results));
  const select=(values,value,description)=>{const control=document.createElement('select');control.setAttribute('aria-label',description);control.setAttribute('form','private-information-form');for(const [v,text]of values){const option=document.createElement('option');option.value=v;option.textContent=text;control.append(option);}control.value=value??'';return control;};
  for(const slot of slots){
   const existing=current.find(r=>r.day===slot.day)||{day:slot.day,target:null,color:null};
   const group=document.createElement('span');group.className='co-day';group.append(role==='hunter'?`D${slot.day}夜 護衛先：`:`Day${slot.day}：`);
   const target=select([['','対象'],...slot.targets.map(id=>[String(id),`Player${id}`])],existing.target,`秘密情報 Player${player} Day${slot.day} 対象`);
   const color=select([['','未入力'],['white','白'],['black','黒']],existing.color,`秘密情報 Player${player} Day${slot.day} 結果`);
   target.dataset.privateTarget=String(slot.day);color.dataset.privateColor=String(slot.day);
   const change=()=>{current=current.filter(r=>r.day!==slot.day);if(target.value||color.value)current.push({day:slot.day,target:target.value?Number(target.value):null,color:color.value||null});current.sort((a,b)=>a.day-b.day);onChange({player,role,results:JSON.parse(JSON.stringify(current))});};
   target.addEventListener('change',change);color.addEventListener('change',change);group.append(target);if(role!=='hunter')group.append(color);cell.append(group);
  }
  let anchor=owner;while(anchor.nextElementSibling?.matches('[data-table-details],[data-co-details],[data-night-reports]'))anchor=anchor.nextElementSibling;
  anchor.after(row);window.refreshParallelLayout?.();return row;
 };
})();
