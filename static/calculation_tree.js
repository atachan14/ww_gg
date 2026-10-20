'use strict';
(()=>{
 const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
 const fraction=x=>{const[a,b=1]=x.split('/').map(Number);return `${x} (${(100*a/b).toFixed(1)}%)`;};
 function mount(root){
  if(root.dataset.treeBound)return;root.dataset.treeBound='1';
  const content=root.querySelector('[data-tree-content]'),status=root.querySelector('[data-tree-status]'),inspector=root.querySelector('[data-tree-inspector]');
  const nodes=new Map();let snapshot=null,rootId=null;
  function keep(d){const old=nodes.get(d.node);nodes.set(d.node,old?.actions&&!d.actions?{...d,actions:old.actions}:d);for(const item of Object.values(d.items||{}))keep(item);}
  async function load(id,expand=false){const q=new URLSearchParams();if(id!==null)q.set('node',id);if(snapshot)q.set('snapshot',snapshot);if(expand)q.set('expand','1');const r=await fetch('/game-tree?'+q,{cache:'no-store'});const d=await r.json();if(!r.ok)throw Object.assign(Error(d.error||'計算を取得できません。'),{detail:d});snapshot=d.snapshot;keep(d);return d;}
  function inspect(d){
   inspector.replaceChildren(el('h3',`Board ${d.node} / ${d.day}日目${d.phase==='day'?'昼':'夜'}`),el('p',d.viewpoint),el('p',`村 ${fraction(d.village_win)} / 狼 ${fraction(d.wolf_win)}`));
   const table=el('table');table.className='tree-board';let tr=el('tr');['Player','生存','公開Q 狼','公開Q 占','物理P 狼'].forEach(x=>tr.append(el('th',x)));table.append(tr);
   d.players.forEach(p=>{tr=el('tr');[p.player,p.alive?'生存':'死亡',p.wolf_probability,p.seer_probability,p.physical_wolf_probability].forEach(x=>tr.append(el('td',String(x))));table.append(tr);});inspector.append(table);
   inspector.append(el('p',d.history.map(e=>`${e.day}日目${e.phase==='day'?'処刑':'襲撃'} P${e.target}`).join(' → ')||'初日'),el('p',d.reports.map(r=>`占P${r.player}→P${r.target} ${r.color}（取得${r.acquired_day}日/公開${r.published_day}日）`).join(' / ')||'公開占い結果なし'),el('p',`昼${d.policy.day} / 夜${d.policy.night} / 自噛み${d.rules.allow_self_bite?'あり':'なし'}`));
  }
  async function expand(id){status.textContent='実際の枝と一致グループを評価中…';try{await load(id,true);render();status.textContent='Boardを選択して確認できます。線の確率はまとめた択に対する条件付き確率です。';}catch(e){status.textContent=e.message;}}
  function tree(id,path=new Set()){
   const d=nodes.get(id),cluster=el('div',undefined,'flow-cluster');if(!d)return cluster;
   const card=el('article',undefined,`tree-item ${d.winner==='village'?'terminal':d.winner==='wolf'?'loss':''}`);card.dataset.treeItem=id;
   const select=el('button',`${d.day}日目 ${d.phase==='day'?'昼':'夜'} / Board ${id}`,'tree-item-title');select.type='button';select.addEventListener('click',()=>inspect(d));card.append(select);
   card.append(el('p',d.winner?(d.winner==='village'?'村勝利':'狼勝利'):`生存${d.alive.length}人`),el('strong',`村勝率 ${fraction(d.village_win)}`),el('small',d.reused?'評価済み・同値再利用':'終局まで評価済み'));
   if(!d.winner&&!d.actions){const more=el('button','先の枝を表示');more.type='button';more.dataset.treeExpand=id;more.addEventListener('click',()=>expand(id));card.append(more);}
   cluster.append(card);return cluster;
  }

  function render(){
   const entries=[],links=[];const phaseRows=new Map();let maxPhase=3;
   function visit(id,parent,incoming,path=new Set()){
    const d=nodes.get(id);if(!d)return;
    const phase=(d.day-1)*2+(d.phase==='night'?1:0);maxPhase=Math.max(maxPhase,phase);
    const row=phaseRows.get(phase)||0;phaseRows.set(phase,row+1);const entry={id,d,phase,row,incoming};entries.push(entry);if(parent)links.push([parent,entry]);
    if(path.has(id))return;const next=new Set([...path,id]);
    for(const a of d.actions||[])for(const branch of a.branches)visit(branch.shown||branch.node,entry,{a,branch},next);
   }
   visit(rootId,null,null);
   const grid=el('div',undefined,'phase-grid');grid.style.gridTemplateColumns=`repeat(${maxPhase+1},270px)`;
   for(let i=0;i<=maxPhase;i++){const h=el('h3',`Day${Math.floor(i/2)+1}${i%2?'夜':'昼'}`,'phase-heading');h.style.gridColumn=i+1;h.style.gridRow=1;grid.append(h);}
   for(const item of entries){
    const cell=el('div',undefined,'phase-cell');cell.style.gridColumn=item.phase+1;cell.style.gridRow=item.row+2;cell.dataset.phase=`${item.d.day}-${item.d.phase}`;
    if(item.incoming){const {a,branch}=item.incoming;const edge=el('div',undefined,'phase-edge');edge.append(el('strong',a.label),el('small',`一致する択 ×${a.multiplicity} / 選択確率 ${a.policy_probability}`),el('span',`${branch.observation} ${fraction(branch.probability)} / 成員Board ×${branch.variants.length}`));
     if(branch.variants.length>1){const choose=el('select');choose.setAttribute('aria-label','一致グループ内の成員Board');for(const v of branch.variants){const o=el('option',`P${v.target} / Board ${v.node}`);o.value=v.node;choose.append(o);}choose.value=item.id;choose.onchange=async()=>{try{const picked=await load(choose.value);branch.shown=picked.node;render();inspect(picked);}catch(e){status.textContent=e.message;}};edge.append(choose);}cell.append(edge);}
    cell.append(tree(item.id).firstElementChild);grid.append(cell);item.cell=cell;
   }
   content.replaceChildren(grid);
   requestAnimationFrame(()=>{
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.classList.add('phase-connectors');svg.setAttribute('width',grid.scrollWidth);svg.setAttribute('height',grid.scrollHeight);const defs=document.createElementNS(ns,'defs'),marker=document.createElementNS(ns,'marker');marker.id='tree-arrow';marker.setAttribute('viewBox','0 0 10 10');marker.setAttribute('refX','9');marker.setAttribute('refY','5');marker.setAttribute('markerWidth','6');marker.setAttribute('markerHeight','6');marker.setAttribute('orient','auto');const tip=document.createElementNS(ns,'path');tip.setAttribute('d','M0 0 L10 5 L0 10 Z');tip.style.fill='#7a8d9b';marker.append(tip);defs.append(marker);svg.append(defs);
    const bounds=grid.getBoundingClientRect();for(const [from,to] of links){const a=from.cell.querySelector('.tree-item').getBoundingClientRect(),b=to.cell.getBoundingClientRect();const line=document.createElementNS(ns,'path');const x=a.right-bounds.left,y=(a.top+a.bottom)/2-bounds.top,u=b.left-bounds.left,v=b.top-bounds.top+12;line.setAttribute('d',`M${x},${y} H${x+12} V${v} H${u+4}`);line.setAttribute('marker-end','url(#tree-arrow)');svg.append(line);}grid.prepend(svg);
   });
  }
  function unavailable(error){
   status.textContent=error.message;root.querySelector('.tree-flow-frame').hidden=true;inspector.hidden=true;
   const box=el('div',undefined,'tree-unavailable');box.dataset.treeUnavailable='1';box.setAttribute('role','note');
   const d=error.detail||{};
   for(const issue of d.issues||[])box.append(el('p',issue));
   if(d.actual){const a=d.actual,mode=x=>x==='max'?'最大勝率':'ランダム',first={random_white:'ランダム白',normal:'通常',none:'なし'};box.append(el('p',`現在の方針：昼 ${mode(a.policy.day)} / 夜 ${mode(a.policy.night)} / 狼の霊能騙り報告 ${mode(a.policy.fake_reports)}。初日占い ${first[a.rules.initial_seer]}。保存履歴 ${a.history_steps}手。`));}
   if(d.supported_route)box.append(el('p',d.supported_route));
   box.append(el('p','保存Board・配役・方針は変更していません。'));
   const link=el('a','TOPで現在の設定を確認');link.href='/';box.append(link);content.parentElement.after(box);
  }
  (async()=>{try{const d=await load(null,true);rootId=d.node;render();inspect(d);status.textContent=d.fixture+' 方針は保存入力どおりです。';}catch(e){unavailable(e);}})();
 }
 const init=()=>document.querySelectorAll('[data-calculation-tree]').forEach(mount);new MutationObserver(init).observe(document.documentElement,{childList:true,subtree:true});init();
})();
