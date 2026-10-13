/* Read-only viewpoint navigation. Data/evaluation stays outside this controller. */
(() => {
  window.createBoardViewpointController = ({root, roles, load, restore, show, onError=()=>{}}) => {
    const table=root.querySelector('.player-table');
    const rows=[...table.querySelectorAll('tr[data-player]')];
    const buttons=[...root.querySelectorAll('[data-viewpoint-role]')];
    let role=null, selected=[], mode='public', version=0, abort=null, savedControls=null;
    const originalRows=new Map(rows.map(row=>[row,{tabindex:row.getAttribute('tabindex'),label:row.getAttribute('aria-label')} ]));
    const setAttribute=(node,key,value)=>value===null?node.removeAttribute(key):node.setAttribute(key,value);
    const lock=()=>{
      if(savedControls)return;
      savedControls=new Map([...root.querySelectorAll('input,select,textarea,button:not([data-viewpoint-role])')].map(control=>[control,control.disabled]));
      savedControls.forEach((_,control)=>{control.disabled=true;});
    };
    const unlock=()=>{savedControls?.forEach((disabled,control)=>{if(control.isConnected)control.disabled=disabled;});savedControls=null;};
    const fits=(ids)=>roles[role]?.combinations.some(combination=>ids.every(id=>combination.includes(id)));
    const paint=()=>{
      root.dataset.viewpointMode=mode;
      for(const button of buttons){
        const key=button.dataset.viewpointRole,active=(key==='public'?!role:key===role);
        button.setAttribute('aria-pressed',String(active));
        button.textContent=key==='public'?'全体':`${roles[key].label}${active?`（${selected.length}/${roles[key].required}）`:''}`;
      }
      for(const row of rows){
        const id=Number(row.dataset.player), chosen=selected.includes(id);
        const candidate=mode==='selecting'&&(chosen||fits([...selected,id]));
        row.classList.toggle('viewpoint-selected',chosen);
        row.classList.toggle('viewpoint-candidate',candidate);
        row.classList.toggle('viewpoint-unavailable',mode==='selecting'&&!candidate);
        row.querySelector('[data-viewpoint-check]')?.remove();
        if(chosen){const check=document.createElement('span');check.dataset.viewpointCheck='';check.textContent='✓ ';check.setAttribute('aria-hidden','true');row.querySelector('.player-name').prepend(check);}
        if(mode==='selecting'){
          row.tabIndex=candidate?0:-1;row.setAttribute('aria-label',`Player ${id}${chosen?' 選択済み':candidate?' 選択可能':' 選択不可'}`);
        }else{const original=originalRows.get(row);setAttribute(row,'tabindex',original.tabindex);setAttribute(row,'aria-label',original.label);}
      }
      root.dispatchEvent(new CustomEvent('viewpointchange',{detail:{mode,role,selected:[...selected]}}));
    };
    const reset=()=>{version++;abort?.abort();abort=null;role=null;selected=[];mode='public';restore();unlock();paint();};
    const begin=key=>{
      version++;abort?.abort();abort=null;
      if(key==='public'){reset();return;}
      if(!roles[key])return;
      restore();lock();role=key;selected=[];mode='selecting';paint();
    };
    const loadSelected=async()=>{
      abort?.abort();
      mode='loading';paint();const revision=++version;abort=new AbortController();
      try{
        const result=await load({role,players:[...selected],signal:abort.signal});
        if(revision!==version||!root.isConnected)return;
        // Adapter must supply private-view values; public win rates must not be reused.
        show(result);mode='viewing';paint();
      }catch(error){
        if(revision!==version||error.name==='AbortError')return;
        mode='selecting';paint();onError(error);
      }
    };
    const choose=id=>{
      if(mode!=='selecting')return;
      const next=selected.includes(id)?selected.filter(p=>p!==id):[...selected,id];
      if(!fits(next))return;
      selected=next;paint();
      if(selected.length===roles[role].required)loadSelected();
    };
    const click=event=>{
      const row=event.target.closest('tr[data-player]');
      if(!row||!table.contains(row)||mode==='public')return;
      event.preventDefault();event.stopImmediatePropagation();
      if(mode==='selecting')choose(Number(row.dataset.player));
    };
    const keydown=event=>{if(mode==='selecting'&&event.target.matches('tr[data-player]')&&['Enter',' '].includes(event.key)){event.preventDefault();choose(Number(event.target.dataset.player));}};
    table.addEventListener('click',click,true);table.addEventListener('keydown',keydown,true);
    const handlers=new Map(buttons.map(button=>{const handler=()=>begin(button.dataset.viewpointRole);button.addEventListener('click',handler);return[button,handler];}));
    paint();
    return {getState:()=>({mode,role,selected:[...selected]}),refresh:()=>{if(role&&selected.length===roles[role].required)loadSelected();},reset,destroy:()=>{reset();table.removeEventListener('click',click,true);table.removeEventListener('keydown',keydown,true);handlers.forEach((handler,button)=>button.removeEventListener('click',handler));}};
  };
})();
