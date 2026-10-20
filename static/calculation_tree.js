"use strict";
(()=>{
 const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 function mass(a,b){const pair=x=>x.split('/').map(BigInt),[an,ad=1n]=pair(a),[bn,bd=1n]=pair(b);let n=an*bn,d=ad*bd,x=n,y=d;while(y){const r=x%y;x=y;y=r;}n/=x;d/=x;return d===1n?String(n):`${n}/${d}`;}
 function mount(root){
  if(root.dataset.treeBound)return;root.dataset.treeBound='1';root.querySelector('.tree-conditions').textContent='項目：村勝率 ／ 矢印：枝の確率';
  const content=root.querySelector('[data-tree-content]'),status=root.querySelector('[data-tree-status]'),inspector=root.querySelector('[data-tree-inspector]');
  const nodes=new Map();let snapshot=null,rootId=null,busy=false,currentNode='0',displayPath=[];
  function keep(d){if(!d.column_phase){d.column_day=1+Math.floor(d.history.length/2);d.column_phase=d.history.length%2?'night':'day';}const old=nodes.get(d.node);nodes.set(d.node,old?.actions&&!d.actions?{...d,actions:old.actions}:d);for(const item of Object.values(d.items||{}))keep(item);}
  async function load(id,expand=false){const q=new URLSearchParams();if(id!==null)q.set('node',id);if(snapshot)q.set('snapshot',snapshot);if(expand)q.set('expand','1');const current=new URL(location.href).searchParams.get('current');if(current)q.set('current',current);const response=await fetch('/game-tree?'+q,{cache:'no-store'}),d=await response.json();if(!response.ok)throw Object.assign(Error(d.error),{detail:d});snapshot=d.snapshot;currentNode=d.current_node||'0';displayPath=d.display_path||[];keep(d);return d;}
  function inspect(d){inspector.replaceChildren(el('span',`B${d.node} · 生存 ${d.alive.map(p=>'P'+p).join(' ')}${d.history.length?' · '+d.history.map(e=>`${e.phase==='day'?'処刑':'襲撃'}P${e.target}`).join(' → '):''}`));root.querySelectorAll('.tree-item').forEach(e=>e.classList.toggle('selected',e.dataset.treeItem===d.node));}
  async function select(id){if(busy)return;busy=true;try{let d=nodes.get(id);if(!d.winner&&!d.actions){d=await load(id,true);render();}inspect(d);}catch(e){status.textContent=e.message;}finally{busy=false;}}
  function render(){
   const entries=[],links=[],counts=new Map();let maxPhase=3;
   const xFor=column=>Math.floor(column/2)*510+(column%2?190:0)+6;
   function entry(column,data){const row=counts.get(column)||0;counts.set(column,row+1);const item={column,row,x:xFor(column),y:48+row*42,...data};entries.push(item);return item;}
   function visit(id,path=new Set()){
    const d=nodes.get(id);if(!d)return null;const phase=(d.column_day-1)*2+(d.column_phase==='night'?1:0);maxPhase=Math.max(maxPhase,phase);const board=entry(phase*2,{kind:'board',id,d});if(path.has(id))return board;const next=new Set([...path,id]);
    for(const action of d.actions||[]){
     let execution=null;
     if(d.phase==='day'){execution=entry(phase*2+1,{kind:'action',text:action.targets.join(',')+'を処刑',title:action.members.map(m=>m.target+'を処刑').join(' / ')});links.push([board,execution,null]);}
     for(const branch of action.branches){
      const exact=branch.variants.find(v=>displayPath.includes(v.node)),child=visit(exact?exact.node:branch.node,next);if(!child)continue;
      if(execution){links.push([execution,child,mass(action.policy_probability,branch.probability)]);continue;}
      const traces=branch.joint_actions?.length?branch.joint_actions:[{label:'襲撃（占い履歴未表示）',probability:branch.probability,multiplicity:action.multiplicity,members:[]}];
      for(const trace of traces){const title='代替組合せ（各組合せの襲撃者は1人）\n'+trace.members.map(m=>m.label+' · '+mass(action.policy_probability,m.probability)).join('\n')+(branch.trace_pending?'\n'+branch.trace_pending:'');const item=entry(phase*2+1,{kind:'action',text:trace.label+(trace.multiplicity>1?'（同型'+trace.multiplicity+'）':''),title,trace});links.push([board,item,null],[item,child,mass(action.policy_probability,trace.probability)]);}
     }
    }
    return board;
   }
   visit(rootId);const columns=2*(maxPhase+1),canvas=el('div',undefined,'compact-tree-canvas'),width=(maxPhase+1)*510,height=72+Math.max(...counts.values())*42;canvas.style.width=width+'px';canvas.style.height=height+'px';
   for(let column=0;column<columns;column++){const phase=Math.floor(column/2),text=column%2?(phase%2?'能力':'処刑'):`Day${Math.floor(phase/2)+1}${phase%2?'夜':'昼'}`;const h=el('h3',text,'compact-tree-phase phase-heading'+(column%2?' action-heading':''));h.style.left=xFor(column)+'px';h.style.width=(column%2?302:172)+'px';h.dataset.column=column;canvas.append(h);}
   for(const item of entries){
    if(item.kind==='action'){const row=el('div',item.text,'compact-action-item');row.dataset.actionColumn=item.column;row.style.left=item.x+'px';row.style.top=item.y+'px';row.title=item.title;row.onclick=()=>inspector.replaceChildren(el('span',item.title));canvas.append(row);continue;}
    const {d}=item,row=el('article',undefined,`tree-item compact-tree-item ${d.winner||''}`);row.dataset.treeItem=d.node;row.classList.toggle('current',d.node===currentNode);row.dataset.phase=`${d.column_day}-${d.column_phase}`;row.dataset.column=item.column;row.style.left=item.x+'px';row.style.top=item.y+'px';
    const main=el('button',`B${d.node} · ${d.alive.length}人 · 村 ${d.village_win}`,'compact-tree-select');main.type='button';main.onclick=()=>select(d.node);
    const go=el('button','→','compact-tree-go');go.type='button';go.disabled=root.dataset.treeNavigation!=='1';go.title='このBoardをCurrentにする';go.setAttribute('aria-label',`B${d.node}へ遷移`);go.onclick=async e=>{e.stopPropagation();if(busy)return;busy=true;go.disabled=true;try{const response=await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({snapshot,node:d.node})}),result=await response.json();if(!response.ok)throw Error(result.error);if(new URL(result.url,location.origin).href===location.href)location.reload();else location.assign(result.url);}catch(error){status.textContent=error.message;go.disabled=false;busy=false;}};row.append(main,go);canvas.append(row);
   }
   const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('width',String(width));svg.setAttribute('height',String(height));svg.classList.add('compact-tree-lines');const defs=document.createElementNS(ns,'defs'),marker=document.createElementNS(ns,'marker');marker.id='compact-tree-arrow';for(const[k,v]of Object.entries({viewBox:'0 0 10 10',refX:'9',refY:'5',markerWidth:'5',markerHeight:'5',orient:'auto'}))marker.setAttribute(k,v);const tip=document.createElementNS(ns,'path');tip.setAttribute('d','M0 0 L10 5 L0 10 Z');marker.append(tip);defs.append(marker);svg.append(defs);
   const fanout=new Map();for(const [from,to,p] of links)if(p!==null)fanout.set(from,(fanout.get(from)||0)+1);
   for(const [from,to,probability] of links){const path=document.createElementNS(ns,'path'),x=from.x+(from.kind==='action'?302:172),y=from.y+13,u=to.x,v=to.y+13;path.setAttribute('d',`M${x},${y} H${x+8} V${v} H${u}`);path.setAttribute('marker-end','url(#compact-tree-arrow)');svg.append(path);if(probability!==null){const label=el('span',probability,'compact-tree-edge');const single=from.kind==='action'&&fanout.get(from)===1;label.style.left=(single?from.x+262:u+3)+'px';label.style.top=(single?from.y-15:v-29)+'px';label.dataset.edgeProbability=probability;canvas.append(label);}}
   canvas.prepend(svg);content.replaceChildren(canvas);
  }
  function unavailable(error){status.textContent=error.message;root.querySelector('.tree-flow-frame').hidden=true;inspector.hidden=true;const box=el('div',undefined,'tree-unavailable');box.dataset.treeUnavailable='1';if(error.detail?.actual){const c=error.detail.actual.counts;box.append(el('p',`現在の配役：市民${c.citizens}・占い${c.seers}・霊能${c.mediums}・狩人${c.hunters}・狼${c.wolves}`));}for(const issue of error.detail?.issues||[])box.append(el('p',issue));if(error.detail?.supported_route)box.append(el('p',error.detail.supported_route));const link=el('a','TOPで現在の設定を確認');link.href='/';box.append(link);content.parentElement.after(box);}
  (async()=>{try{const d=await load(null,true);rootId=d.node;render();status.textContent='';inspector.replaceChildren();}catch(e){unavailable(e);}})();
 }
 const init=()=>document.querySelectorAll('[data-calculation-tree]').forEach(mount);new MutationObserver(init).observe(document.documentElement,{childList:true,subtree:true});init();
})();
