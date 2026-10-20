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
   const entries=[],edges=[],counts=new Map();let maxPhase=3;
   function visit(id,parent,incoming,path=new Set()){
    const d=nodes.get(id);if(!d)return;const phase=(d.column_day-1)*2+(d.column_phase==='night'?1:0),row=counts.get(phase)||0;counts.set(phase,row+1);maxPhase=Math.max(maxPhase,phase);
    const item={id,d,phase,row,incoming};entries.push(item);if(parent)edges.push([parent,item]);if(path.has(id))return;const next=new Set([...path,id]);for(const a of d.actions||[])for(const branch of a.branches){const exact=branch.variants.find(v=>displayPath.includes(v.node));visit(exact?exact.node:branch.node,item,{a,branch},next);}
   }
   visit(rootId,null,null);const canvas=el('div',undefined,'compact-tree-canvas');canvas.style.width=((maxPhase+1)*190)+'px';canvas.style.height=(60+Math.max(...counts.values())*62)+'px';
   for(let phase=0;phase<=maxPhase;phase++){const h=el('h3',`Day${Math.floor(phase/2)+1}${phase%2?'夜':'昼'}`,'compact-tree-phase phase-heading');h.style.left=(phase*190+6)+'px';canvas.append(h);}
   for(const item of entries){const {d}=item,x=item.phase*190+6,y=46+item.row*62;item.x=x;item.y=y;
    const row=el('article',undefined,`tree-item compact-tree-item ${d.winner||''}`);row.dataset.treeItem=d.node;row.classList.toggle('current',d.node===currentNode);row.dataset.phase=`${d.column_day}-${d.column_phase}`;row.style.left=x+'px';row.style.top=y+'px';
    const main=el('button',`B${d.node} · ${d.alive.length}人 · 村 ${d.village_win}`,'compact-tree-select');main.type='button';main.onclick=()=>select(d.node);
    const go=el('button','→','compact-tree-go');go.type='button';go.disabled=root.dataset.treeNavigation!=='1';go.title='このBoardをCurrentにする';go.setAttribute('aria-label',`B${d.node}へ遷移`);go.onclick=async e=>{e.stopPropagation();if(busy)return;busy=true;go.disabled=true;try{const response=await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({snapshot,node:d.node})}),result=await response.json();if(!response.ok)throw Error(result.error);if(new URL(result.url,location.origin).href===location.href)location.reload();else location.assign(result.url);}catch(error){status.textContent=error.message;go.disabled=false;busy=false;}};row.append(main,go);canvas.append(row);
    if(item.incoming){const {a,branch}=item.incoming;const label=el('span',`${a.label.startsWith('処刑')?'処刑':'襲撃'}${a.multiplicity>1?' ×'+a.multiplicity:''} · ${mass(a.policy_probability,branch.probability)}`,'compact-tree-edge');label.title=`選択確率 ${a.policy_probability} / 観測確率 ${branch.probability} / 同型Board ${branch.variants.map(v=>'B'+v.node).join(' / ')}`;label.style.left=x+'px';label.style.top=(y-17)+'px';canvas.append(label);}
   }
   const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('width',String((maxPhase+1)*190));svg.setAttribute('height',canvas.style.height);svg.classList.add('compact-tree-lines');
   const defs=document.createElementNS(ns,'defs'),marker=document.createElementNS(ns,'marker');marker.id='compact-tree-arrow';for(const[k,v]of Object.entries({viewBox:'0 0 10 10',refX:'9',refY:'5',markerWidth:'5',markerHeight:'5',orient:'auto'}))marker.setAttribute(k,v);const tip=document.createElementNS(ns,'path');tip.setAttribute('d','M0 0 L10 5 L0 10 Z');marker.append(tip);defs.append(marker);svg.append(defs);
   for(const [from,to] of edges){const path=document.createElementNS(ns,'path'),x=from.x+172,y=from.y+13,u=to.x,v=to.y+13;path.setAttribute('d',`M${x},${y} H${x+8} V${v} H${u}`);path.setAttribute('marker-end','url(#compact-tree-arrow)');svg.append(path);}canvas.prepend(svg);content.replaceChildren(canvas);
  }
  function unavailable(error){status.textContent=error.message;root.querySelector('.tree-flow-frame').hidden=true;inspector.hidden=true;const box=el('div',undefined,'tree-unavailable');box.dataset.treeUnavailable='1';if(error.detail?.actual){const c=error.detail.actual.counts;box.append(el('p',`現在の配役：市民${c.citizens}・占い${c.seers}・霊能${c.mediums}・狩人${c.hunters}・狼${c.wolves}`));}for(const issue of error.detail?.issues||[])box.append(el('p',issue));if(error.detail?.supported_route)box.append(el('p',error.detail.supported_route));const link=el('a','TOPで現在の設定を確認');link.href='/';box.append(link);content.parentElement.after(box);}
  (async()=>{try{const d=await load(null,true);rootId=d.node;render();status.textContent='';inspector.replaceChildren();}catch(e){unavailable(e);}})();
 }
 const init=()=>document.querySelectorAll('[data-calculation-tree]').forEach(mount);new MutationObserver(init).observe(document.documentElement,{childList:true,subtree:true});init();
})();
