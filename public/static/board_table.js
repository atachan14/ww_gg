/* Unpublished table editor: one ephemeral batch, latest-response-only preview. */
(() => {
 const initialize=()=>{
  const main=document.querySelector('main[data-hybrid-table]'),update=document.querySelector('[data-table-update]');if(!main||main.dataset.tableInitialized)return;main.dataset.tableInitialized='true';
  const seed=JSON.parse(document.querySelector('#public-log-seed').textContent),status=document.querySelector('[data-table-preview-status]');
  const normalize=value=>{const next=JSON.parse(JSON.stringify(value));for(const key of ['seers','mediums'])next[key].sort((a,b)=>a.day-b.day||a.reporter-b.reporter||(a.target??0)-(b.target??0));return next;};
  const baseline=normalize({claims:seed.claims,seers:seed.seers,mediums:seed.mediums});
  const baseDocument=new DOMParser().parseFromString(document.documentElement.outerHTML,'text/html');
  const conflicts=document.querySelectorAll('[data-public-open],[data-public-edit],[data-public-delete],[data-legacy-open],#advance-button,#back-button,#strategy-button,[data-settings-pane="strategy"] input,[data-settings-pane="strategy"] select');
  const draft=window.createBoardDeclarationDraft(baseline,{update,cancel:document.querySelector('[data-table-cancel]'),conflictingButtons:conflicts});
  let version=0,timer,controller,lastPreview=null,rendering=false,navigating=false,clearedSavedDraft=false,clearSavedPromise=Promise.resolve();
  const labels={latent:'--',villager:'市民',seer:'占い師',medium:'霊能',hunter:'狩人',wolf:'狼'};
  const clone=x=>JSON.parse(JSON.stringify(x));
  const selectors=[];const roleStash=new Map();
  const storageKey=`wwgg-table-draft:${main.dataset.coGame}:${seed.board_id}`;
  let recovered=null;try{const saved=JSON.parse(sessionStorage.getItem(storageKey)||'null');if(saved?.revision===seed.revision&&saved.board_id===seed.board_id&&saved.inherited_revision===seed.inherited_revision)recovered=saved.snapshot;else sessionStorage.removeItem(storageKey);}catch(_){}
  if(!recovered&&seed.draft?.revision===seed.revision&&seed.draft.board_id===seed.board_id&&seed.draft.payload?.events&&!seed.draft.payload.replace){
    recovered=clone(baseline);
    for(const e of seed.draft.payload.events){
      if(!Number.isInteger(e.player)||e.player<1||e.player>seed.players)continue;
      if(e.kind==='co'&&seed.roles.includes(e.role))recovered.claims[e.player-1]=e.role;
      if(e.kind==='seer'||e.kind==='medium'){
        const list=recovered[e.kind==='seer'?'seers':'mediums'];const key=r=>r.day===e.day&&r.reporter===e.player&&(e.kind==='seer'||r.target===e.target);
        const old=list.findIndex(key);const row={day:e.day,reporter:e.player,target:e.target??null,color:e.color??null};if(old<0)list.push(row);else list[old]=row;
      }
    }
  }
  const option=(select,value,label)=>{const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o);};
  const select=(values,value,onchange)=>{const e=document.createElement('select');e.setAttribute('form','public-log-draft-form');for(const [v,l] of values)option(e,v,l);e.value=value??'';e.addEventListener('change',()=>{if(!rendering)onchange(e.value);});return e;};
  const mutate=fn=>{const next=draft.snapshot();fn(next);draft.edit(normalize(next));};
  const showWaiting=text=>{
    document.querySelectorAll('#information-panel .probability,.player-table tr[data-player] .probability').forEach(e=>{e.textContent=text;e.removeAttribute('data-fraction');e.removeAttribute('data-percent');});
    document.querySelectorAll('.overview-facts strong').forEach(e=>{e.textContent=text;});
    const groups=document.querySelector('[data-hybrid-groups]');if(groups)groups.hidden=true;
    document.querySelectorAll('[data-hybrid-groups] .probability').forEach(e=>{e.textContent=text;e.removeAttribute('data-fraction');e.removeAttribute('data-percent');});
  };
  const apply=doc=>{
    document.querySelector('#information-panel').innerHTML=doc.querySelector('#information-panel').innerHTML;
    for(const row of document.querySelectorAll('.player-table tr[data-player]')){
      const remote=doc.querySelector(`.player-table tr[data-player="${row.dataset.player}"]`);if(!remote)continue;
      for(const cell of row.querySelectorAll('[data-value-cell]')){const source=remote.querySelector(`[data-value-cell="${cell.dataset.valueCell}"]`);if(source)cell.innerHTML=source.innerHTML;}
    }
    const old=document.querySelector('[data-hybrid-groups]'),next=doc.querySelector('[data-hybrid-groups]');
    if(old)old.remove();if(next)document.querySelector('#action-form').append(next.cloneNode(true));
    const fraction=document.querySelector('[name="probability-format"]:checked')?.value==='fraction';
    document.querySelectorAll('.probability[data-fraction]').forEach(e=>{e.textContent=fraction?e.dataset.fraction:e.dataset.percent;});
  };
  const renderDetails=(player,host,role)=>{
    host.replaceChildren();host.closest('tr').hidden=!['seer','medium'].includes(role);
    if(!['seer','medium'].includes(role))return;
    host.closest('tr').querySelector('[data-table-role-label]').textContent=labels[role];
    const current=draft.snapshot();
    if(role==='seer')for(let day=1;day<=seed.day;day++){
      const row=current.seers.find(r=>r.day===day&&r.reporter===player)||{day,reporter:player,target:null,color:null};
      const span=document.createElement('span');span.className='co-day';span.append(`Day${day}: `);
      const dead=seed.targets.slice(0,day===1?0:2*day-3);const targets=Array.from({length:seed.players},(_,i)=>i+1).filter(p=>p!==player&&!dead.includes(p));
      const change=(key,value)=>mutate(next=>{if(key==='color'&&!value){next.seers=next.seers.filter(x=>!(x.day===day&&x.reporter===player));return;}let r=next.seers.find(x=>x.day===day&&x.reporter===player);if(!r){r={...row};next.seers.push(r);}r[key]=key==='target'?(value?Number(value):null):(value||null);if(r.target===null&&r.color===null)next.seers=next.seers.filter(x=>x!==r);});
      const target=select([['','対象'],...targets.map(p=>[String(p),`Player${p}`])],row.target,(v)=>change('target',v));target.dataset.tableTarget=`${day}:${player}`;
      target.disabled=seed.finished||!seed.alive.includes(player);
      const color=select([['','未公開'],['white','白'],['black','黒']],row.color,v=>{change('color',v);if(!v){render();document.querySelector(`[data-table-color="${day}:${player}"]`)?.focus();}});color.disabled=seed.finished||!seed.alive.includes(player);color.dataset.tableColor=`${day}:${player}`;span.append(target,color);host.append(span);
    }
    const mediumSlots=Array.from({length:Math.max(0,seed.day-1)},(_,i)=>[i+2,player,seed.targets[2*i]]);
    if(role==='medium'){const none=document.createElement('span');none.textContent='Day1: --';host.append(none);}
    if(role==='medium')for(const [day,p,target] of mediumSlots){if(p!==player||!target)continue;
      const row=current.mediums.find(r=>r.day===day&&r.reporter===player&&r.target===target);const span=document.createElement('span');span.className='co-day';span.append(`Day${day}: Player${target} `);
      const color=select([['','未公開'],['white','白'],['black','黒']],row?.color,v=>mutate(next=>{next.mediums=next.mediums.filter(r=>!(r.day===day&&r.reporter===player&&r.target===target));if(v)next.mediums.push({day,reporter:player,target,color:v});}));color.dataset.tableMedium=`${day}:${player}:${target}`;color.disabled=seed.finished||!seed.alive.includes(player);span.append(color);host.append(span);
    }
  };
  const render=()=>{
    rendering=true;const current=draft.snapshot();
    for(const {player,picker,host,row,detail} of selectors){picker.value=current.claims[player-1];if(['seer','medium'].includes(picker.value))row.after(detail);else detail.remove();renderDetails(player,host,picker.value);}
    rendering=false;window.refreshParallelLayout?.();
  };
  for(const row of document.querySelectorAll('.player-table tr[data-player]')){
    const player=Number(row.dataset.player),cell=row.querySelector('[data-col="co"]');cell.replaceChildren();
    const picker=select([['latent','--'],...seed.roles.map(r=>[r,labels[r]])],baseline.claims[player-1],value=>{
      mutate(next=>{const before=next.claims[player-1];
      if(before==='seer'||before==='medium')roleStash.set(`${player}:${before}`,clone(next[before==='seer'?'seers':'mediums'].filter(r=>r.reporter===player)));
      next.claims[player-1]=value;if(before==='seer'&&value!=='seer')next.seers=next.seers.filter(r=>r.reporter!==player);if(before==='medium'&&value!=='medium')next.mediums=next.mediums.filter(r=>r.reporter!==player);
      if(value==='seer'||value==='medium'){const key=value==='seer'?'seers':'mediums';const rows=roleStash.get(`${player}:${value}`)||(baseline.claims[player-1]===value?baseline[key].filter(r=>r.reporter===player):[]);if(!next[key].some(r=>r.reporter===player))next[key].push(...clone(rows));}
      });render();
    });picker.dataset.tableCo=String(player);picker.disabled=seed.finished||!seed.alive.includes(player);cell.append(picker);
    const detail=document.createElement('tr');detail.className='co-detail-row';detail.dataset.tableDetails=String(player);const spacer=document.createElement('td'),roleCell=document.createElement('td'),td=document.createElement('td');roleCell.dataset.tableRoleLabel='';roleCell.className='co-role-label';td.dataset.tableResults='';td.colSpan=row.cells.length-2;const host=document.createElement('div');host.className='co-line';td.append(host);detail.append(spacer,roleCell,td);row.after(detail);selectors.push({player,picker,host,row,detail});
  }
  const preview=async id=>{
    controller=new AbortController();try{
      const response=await fetch('/table-preview',{method:'POST',signal:controller.signal,body:new URLSearchParams({revision:String(seed.revision),board_id:seed.board_id,request_id:String(id),payload:JSON.stringify(draft.snapshot())})});const data=await response.json();
      if(id!==version||!draft.isDirty())return;
      if(!response.ok)throw Error(data.error);if(String(data.request_id)!==String(id)||data.revision!==seed.revision||data.board_id!==seed.board_id)return;
      apply(new DOMParser().parseFromString(data.html,'text/html'));lastPreview=clone(draft.snapshot());status.textContent='プレビュー';
    }catch(e){if(id===version&&e.name!=='AbortError'){const inconsistent=e.message.includes('全開示')||e.message.includes('整合する配役');showWaiting(inconsistent?'不整合':'入力待ち');status.textContent=`${inconsistent?'不整合':'プレビュー・入力待ち'}: ${e.message}`;}}
  };
  if(seed.finished){render();window.boardTableDraft=draft;return;}
  draft.onChange(({dirty,busy})=>{
    if(navigating)return;
    version++;clearTimeout(timer);controller?.abort();lastPreview=null;
    if(busy)return;
    if(!dirty){try{sessionStorage.removeItem(storageKey);}catch(_){}apply(baseDocument);status.textContent='';return;}
    try{sessionStorage.setItem(storageKey,JSON.stringify({revision:seed.revision,board_id:seed.board_id,inherited_revision:seed.inherited_revision,snapshot:draft.snapshot()}));}catch(_){}
    document.dispatchEvent(new CustomEvent('board-table-dirty'));
    if(seed.draft&&!clearedSavedDraft){clearedSavedDraft=true;clearSavedPromise=fetch('/public-log',{method:'POST',body:new URLSearchParams({revision:String(seed.revision),board_id:seed.board_id,operation:'cancel',payload:'{}'})}).then(async r=>{if(!r.ok)throw Error((await r.json()).error);});clearSavedPromise.catch(e=>{status.textContent=e.message;});}
    showWaiting('計算中');status.textContent='プレビュー・計算中';const id=version;timer=setTimeout(()=>preview(id),180);
  });
  update.addEventListener('click',async()=>{
    try{await draft.submit(async(current)=>{
      clearTimeout(timer);controller?.abort();await clearSavedPromise;const response=await fetch('/table-publish',{method:'POST',body:new URLSearchParams({revision:String(seed.revision),board_id:seed.board_id,payload:JSON.stringify(current)})});const data=await response.json();if(!response.ok)throw Error(data.error);try{sessionStorage.removeItem(storageKey);}catch(_){}navigating=true;location.reload();return current;
    });}catch(e){status.textContent=`保存できません: ${e.message}`;}
  });
  document.querySelector('#action-form').addEventListener('submit',event=>{if(draft.isDirty()){event.preventDefault();event.stopImmediatePropagation();status.textContent='先に更新またはキャンセルしてください。';}},true);
  document.querySelectorAll('form[action="/back"]').forEach(form=>form.addEventListener('submit',event=>{if(draft.isDirty()){event.preventDefault();event.stopImmediatePropagation();}},true));
  document.querySelector('[data-table-cancel]').addEventListener('click',()=>{roleStash.clear();render();});
  render();if(recovered){draft.edit(normalize(recovered));render();}window.boardTableDraft=draft;
 };
 window.initializeBoardTable=initialize;
 document.addEventListener('DOMContentLoaded',initialize);
})();
