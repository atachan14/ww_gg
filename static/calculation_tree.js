"use strict";
(()=>{
 const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const targetLabel=(targets,action)=>(targets.length>1?'['+targets.map((p,i)=>i===0?'('+p+')':p).join(',')+']から':targets[0]+'を')+action;
 // Also format labels already cached by a running local server.
 const groupLabel=label=>label.replace(/(\d+)[（(]or(\d+(?:or\d+)*)[）)]を/g,(_,first,rest)=>'['+[first,...rest.split('or')].join(',')+']から');
 function mass(a,b){const pair=x=>x.split('/').map(BigInt),[an,ad=1n]=pair(a),[bn,bd=1n]=pair(b);let n=an*bn,d=ad*bd,x=n,y=d;while(y){const r=x%y;x=y;y=r;}n/=x;d/=x;return d===1n?String(n):`${n}/${d}`;}
 function mount(root){
  if(root.dataset.treeBound)return;root.dataset.treeBound='1';
  root.querySelectorAll('.tree-conditions,.compact-tree-legend,[data-tree-inspector]').forEach(e=>e.remove());
  const content=root.querySelector('[data-tree-content]'),status=root.querySelector('[data-tree-status]');
  const expansion=window.TreeExpansion.create(),nodes=new Map(),frame=root.querySelector('.tree-flow-frame');let snapshot=null,rootId=null,busy=false,currentNode='0',displayPath=[],renderVersion=0;
  const viewport=window.TreeViewport,headerViewport=el('div',undefined,'tree-header-viewport');headerViewport.dataset.treeHeader='';frame.before(headerViewport);
  let scale=1,worldWidth=0,worldHeight=0,scene=null,headerScene=null;
  const distributions=new Map(),analysisOpen=new Set(),accordionOpen=new Set(),analysisErrors=new Map();
  async function openAnalysis(d,id=d.node){
   if(analysisOpen.has(id)){analysisOpen.delete(id);render();return;}
   analysisOpen.add(id);render();
   if(d.snapshot_only||distributions.has(id))return;
   try{const data=await expansion.load('analysis:'+id,()=>load(id,false,true));if(data.distribution)distributions.set(id,data.distribution);if(root.isConnected)render();}
   catch(error){analysisErrors.set(id,error.message);if(root.isConnected)render();}
  }
  function inlineAnalysis(item){
   const d=item.d,rows=distributions.get(item.id)||d.distribution||(d.compositions||[]).map(c=>({id:c.node,label:c.label,probability:c.probability,village_win:(nodes.get(c.node)||d).village_win,children:[]}));
   const panel=el('section',undefined,'tree-inline-distribution');panel.setAttribute('aria-label','秘密状態の分布');panel.dataset.distributionFor=item.id;
   function append(parent,rows){for(const row of rows){const text=row.probability+'['+row.label+(row.village_win!==undefined?'・'+row.village_win:'')+']',key=item.id+'/'+row.id;
    if(row.children?.length){const details=el('details',undefined,'tree-distribution-branch'),summary=el('summary',text);details.dataset.distributionPath=key;details.open=accordionOpen.has(key);summary.onclick=event=>{event.preventDefault();event.stopPropagation();if(accordionOpen.has(key))accordionOpen.delete(key);else accordionOpen.add(key);render(item.key);root.querySelector('[data-distribution-path="'+CSS.escape(key)+'"]>summary')?.focus({preventScroll:true});};details.append(summary);const children=el('div',undefined,'tree-distribution-children');append(children,row.children);details.append(children);parent.append(details);}
    else parent.append(el('div',text,'tree-distribution-leaf'));
   }}
   append(panel,rows);if(analysisErrors.has(item.id))panel.append(el('div',analysisErrors.get(item.id)));return panel;
  }
  function syncHeader(){if(headerScene)headerScene.style.transform=`translateX(${-frame.scrollLeft}px) scale(${scale})`;}
  function applyView(){if(!scene)return;scene.style.transform=`scale(${scale})`;content.style.width=(worldWidth*scale)+'px';content.style.height=(worldHeight*scale)+'px';headerViewport.style.height=(36*scale)+'px';headerViewport.style.width=(frame.clientWidth+2*frame.clientLeft)+'px';root.dataset.treeZoom=String(scale);syncHeader();}
  function zoom(point,delta){if(!scene)return;const next=viewport.zoomAt({scale,left:frame.scrollLeft,top:frame.scrollTop},point,delta);scale=next.scale;++renderVersion;applyView();frame.scrollLeft=next.left;frame.scrollTop=next.top;syncHeader();}
  function wheel(event){viewport.captureWheel(event,frame.clientHeight,delta=>{const rect=frame.getBoundingClientRect();zoom({x:Math.max(0,event.clientX-rect.left-frame.clientLeft),y:Math.max(0,event.clientY-rect.top-frame.clientTop)},delta);});}
  root.addEventListener('wheel',wheel,{passive:false});
  frame.addEventListener('scroll',syncHeader,{passive:true});
  frame.addEventListener('keydown',event=>{if(event.ctrlKey||event.metaKey||event.target!==frame)return;const delta=event.key==='+'||event.key==='='?-100:event.key==='-'?100:event.key==='0'?Math.log(scale)/.002:null;if(delta===null)return;event.preventDefault();zoom({x:frame.clientWidth/2,y:frame.clientHeight/2},delta);});
  const footer=document.querySelector('.phase-footer');
  function fitArea(){const footerHeight=footer?.getBoundingClientRect().height||0,height=window.visualViewport?.height||window.innerHeight;root.style.setProperty('--tree-footer-height',footerHeight+'px');root.closest('.page-shell')?.style.setProperty('--tree-footer-height',footerHeight+'px');root.style.height=viewport.areaHeight(height,footerHeight)+'px';if(scene)applyView();}
  if(footer)new ResizeObserver(fitArea).observe(footer);window.addEventListener('resize',fitArea);window.visualViewport?.addEventListener('resize',fitArea);fitArea();
  function keep(d){if(!d.column_phase){d.column_day=1+Math.floor(d.history.length/2);d.column_phase=d.history.length%2?'night':'day';}const old=nodes.get(d.node);nodes.set(d.node,old?.actions&&!d.actions?{...d,actions:old.actions}:d);for(const item of Object.values(d.items||{}))keep(item);}
  async function load(id,expand=false,analysis=false){const q=new URLSearchParams();if(id!==null)q.set('node',id);if(snapshot)q.set('snapshot',snapshot);if(expand)q.set('expand','1');if(analysis)q.set('analysis','1');const current=new URL(location.href).searchParams.get('current');if(current)q.set('current',current);const response=await fetch('/game-tree?'+q,{cache:'no-store'}),d=await response.json();if(!response.ok)throw Object.assign(Error(d.error),{detail:d});snapshot=d.snapshot;currentNode=d.current_node||'0';displayPath=d.display_path||[];keep(d);return d;}
  function inspect(d){root.querySelectorAll('.tree-item').forEach(e=>e.classList.toggle('selected',e.dataset.treeItem===d.node));}
  function guardDragClick(button){let start=null,moved=false;
   button.addEventListener('pointerdown',event=>{start={clientX:event.clientX,clientY:event.clientY};moved=false;});
   button.addEventListener('pointermove',event=>{moved ||= window.TreeExpansion.isDrag(start,event);});
   button.addEventListener('pointercancel',()=>{moved=true;});
   button.addEventListener('click',event=>{const dragged=moved||window.TreeExpansion.isDrag(start,event);start=null;moved=false;if(event.detail&&dragged){event.preventDefault();event.stopImmediatePropagation();}},true);
  }
  async function toggle(item){
   if(!item.expandable)return;
   const opened=expansion.toggle(item.key);render(item.key);
   if(!opened)return;
   try{await expansion.chain(item.key,entry=>expansion.load(entry.d.node,()=>load(entry.d.node,true)),()=>{if(root.isConnected){status.textContent='';render(item.key);}});}
   catch(error){if(root.isConnected&&expansion.isOpen(item.key))status.textContent=error.message;}
  }

  function render(anchorId){
   const version=++renderVersion,oldLeft=frame.scrollLeft,oldTop=frame.scrollTop,oldAnchor=anchorId?root.querySelector(`[data-tree-key="${anchorId}"]`):null,anchorRect=oldAnchor?.getBoundingClientRect();
   const entries=[],links=[],ROW=44,GAP=14;let maxPhase=3;
   const seerCount=Math.max(0,...[...nodes.values()].map(d=>d.stage_roles?.seers||Math.max(0,...(d.compositions||[]).map(c=>c.counts?.seers||0)))),native=[...nodes.values()].some(d=>d.native_mode),publication=[...nodes.values()].some(d=>(d.public_claims||[]).some(c=>c==='seer'||c==='medium')),timeline=nodes.get(rootId)?.input_timeline;
   const updateCount=phase=>native?(phase===0?(timeline?.updates.length||0):(publication?1:0)):0;
   const dayWidth=phase=>(native?2:3)+updateCount(phase),nightWidth=(native?3:3)+2*seerCount;
   const base=phase=>{let start=0;for(let p=0;p<phase;p++)start+=p%2?nightWidth:dayWidth(p);return start;};
   function make(kind,column,data,children=[]){return {kind,column,...data,children,height:Math.max(ROW,children.reduce((h,c)=>h+c.item.height,0)+Math.max(0,children.length-1)*GAP)};}
   function choices(d,path,reach){
    if(d.winner)return [];
    const phase=(d.column_day-1)*2+(d.column_phase==='night'?1:0),column=base(phase)+(native?1+(d.phase==='day'?updateCount(phase):0):2);
    if(d.phase==='night'&&d.night_stages){
     const walk=(stage,index,parentReach)=>{
      if(native&&stage.branches?.length&&stage.branches.every(b=>b.kind==='publication')){
       const leaves=[];const gather=s=>{if(s.leaves)leaves.push(...s.leaves);else for(const b of s.branches||[])gather(b.children);};gather(stage);
       const first=leaves.find(leaf=>nodes.get(leaf.node)?.day_arrival);
       if(first)return [{probability:'1',item:build(first.node,path,undefined,parentReach,first.context_node)}];
      }
      if(stage.leaves)return stage.leaves.map(leaf=>{const exact=(leaf.variants||[]).find(v=>displayPath.includes(v.node));return {probability:leaf.probability,item:build(exact?exact.node:leaf.node,path,undefined,mass(parentReach,leaf.probability),leaf.context_node)};}).filter(x=>x.item);
      return (stage.branches||[]).map(branch=>{const reach=mass(parentReach,branch.probability),position=branch.kind==='wolf_target'?2*seerCount:branch.kind==='death_notice'?2*seerCount+1:branch.kind==='publication'?2*seerCount+2:index;
       const image=(branch.images||[]).find(image=>image.children&&image.nodes.some(id=>displayPath.includes(id)));
       const descendants=walk(image?image.children:branch.children,index+1,reach);
       return {probability:branch.probability,item:make('action',column+position,{text:branch.label,title:(native?'同時行動 / 夜内の到達 '+branch.mass:'\u540c\u6642\u884c\u52d5 / \u5230\u9054 '+reach)+' / \u62ec\u5f27\u306f\u4ee3\u8868\u914d\u7f6e\u3002\u80fd\u529b\u8005\u3068\u5bfe\u8c61\u306f\u540c\u3058\u540d\u524d\u7f6e\u63db\u306b\u5f93\u3044\u307e\u3059\u3002'},descendants)};
      });
     };
     return walk(d.night_stages,0,reach);
    }
    if(d.phase==='night'&&d.ability_choices){
     return d.ability_choices.map(scan=>{
      const scanReach=mass(reach,scan.probability);
      const attacks=(rows,resultReach)=>rows.map(attack=>{const attackReach=mass(resultReach,attack.probability||attack.policy_probability);
       const outcomes=attack.branches.map(branch=>{const exact=(branch.variants||[]).find(v=>displayPath.includes(v.node));return {probability:branch.probability,item:build(exact?exact.node:branch.node,path,branch.observation,mass(attackReach,branch.probability))};}).filter(x=>x.item);
       return {probability:attack.probability||attack.policy_probability,item:make('action',column+2,{text:attack.label,title:'\u540c\u6642\u884c\u52d5 / \u5230\u9054 '+attackReach+' / \u6761\u4ef6\u4ed8\u304d '+attack.conditional_probability},outcomes)};
      });
      const children=scan.results?scan.results.map(result=>({probability:result.probability,item:make('action',column+1,{text:result.label,title:'\u5360\u3044\u5e2b\u306e\u975e\u516c\u958b\u7d50\u679c\u3002\u72fc\u306e\u65b9\u7b56\u306f\u7d50\u679c\u3092\u89b3\u6e2c\u3059\u308b\u524d\u306b\u6c7a\u5b9a\u3002 / \u5230\u9054 '+mass(scanReach,result.probability)},attacks(result.attacks,mass(scanReach,result.probability)))})):attacks(scan.attacks,scanReach);
      return {probability:scan.probability,item:make('action',column,{text:scan.label,title:'\u540c\u6642\u884c\u52d5\u3092\u8868\u793a\u9806\u306b\u5206\u3051\u3066\u3044\u307e\u3059\u3002'},children)};
     });
    }
    return (d.actions||[]).map(action=>({probability:action.policy_probability,item:make('action',d.phase==='night'?column+2*seerCount:column,{text:d.phase==='day'?targetLabel(action.targets,'処刑'):groupLabel(action.label),title:(d.ability_pending?d.ability_pending+'\n':'')+action.members.map(m=>m.target+' · '+m.policy_mass).join(' / ')},action.branches.map(branch=>{const exact=branch.variants.find(v=>displayPath.includes(v.node));return {probability:branch.probability,item:build(exact?exact.node:branch.node,path,branch.outcome_label,mass(reach,mass(action.policy_probability,branch.probability)))};}).filter(x=>x.item))}));
   }
   const sharedBoards=new Map();
   function updated(d,label,column,path,reach){
    const identity='updated:'+d.node;
    if(d.public_bundle&&sharedBoards.has(identity))return sharedBoards.get(identity);
    const next=new Set([...path,d.node]),item=make('board',column,{d,id:d.node,text:label,update:true,shared:!!d.public_bundle,contexts:new Set(),lazy:!d.winner&&!d.actions},path.has(d.node)?[]:choices(d,next,reach));
    if(d.public_bundle)sharedBoards.set(identity,item);return item;
   }
   function build(id,path=new Set(),arrival,reach='1',context){
    const d=nodes.get(id);if(!d)return null;
    const phase=(d.column_day-1)*2+(d.column_phase==='night'?1:0);maxPhase=Math.max(maxPhase,phase);
    if(native&&d.day_arrival){
     const a=d.day_arrival;if(sharedBoards.has(a.id))return sharedBoards.get(a.id);
     const children=a.updates.map(update=>{const after=nodes.get(update.node);return after?{probability:update.probability,item:updated(after,update.label,base(phase)+1,path,mass(reach,update.probability))}:null;}).filter(Boolean);
     const item=make('board',base(phase),{d:a.state,id:a.id,shared:true,contexts:new Set(context?[context]:[])},children);sharedBoards.set(a.id,item);return item;
    }
    if(native&&id===rootId&&timeline?.updates.length){
     const rows=timeline.updates;let tail=updated(d,rows[rows.length-1].label,base(phase)+rows.length,path,reach);
     for(let i=rows.length-2;i>=0;i--)tail=make('board',base(phase)+i+1,{d:rows[i].state,id:rows[i].state.node,text:rows[i].label,update:true},[{probability:null,item:tail}]);
     return make('board',base(phase),{d:timeline.before,id:timeline.before.node},[{probability:null,item:tail}]);
    }
    if(native&&d.public_bundle&&sharedBoards.has(id)){const item=sharedBoards.get(id);if(context)item.contexts.add(context);return item;}
    if(native){const next=new Set([...path,id]),item=make('board',base(phase),{d,id,arrival,shared:!!d.public_bundle,contexts:new Set(context?[context]:[]),lazy:!d.winner&&!d.actions},path.has(id)?[]:choices(d,next,reach));if(d.public_bundle)sharedBoards.set(id,item);return item;}
    const next=new Set([...path,id]),compositions=d.compositions||[{node:id,label:'内訳未取得',probability:'1'}];
    const children=path.has(id)?[]:compositions.map(composition=>{const c=nodes.get(composition.node)||d;return {probability:composition.probability,item:make('composition',base(phase)+1,{d:c,id:c.node,text:composition.label,hideGo:c.node===id,lazy:!c.winner&&!c.actions},choices(c,next,mass(reach,composition.probability)))};});
    return make('board',base(phase),{d,id,arrival,lazy:!d.winner&&!d.compositions?.length},children);
   }
   const complete=build(rootId);if(!complete)return;const tree=expansion.project(complete);
   const seen=new Set();function collect(item){if(seen.has(item))return;seen.add(item);entries.push(item);for(const child of item.children){collect(child.item);links.push([item,child.item,child.probability,child]);}}collect(tree);
   const columns=base(maxPhase+1),canvas=el('div',undefined,'compact-tree-canvas'),headers=el('div',undefined,'compact-tree-headers'),headings=[],selectionHeads=[];canvas.style.height=(tree.height+24)+'px';content.replaceChildren(canvas);headerViewport.replaceChildren(headers);scene=canvas;headerScene=headers;
   for(let phase=0;phase<=maxPhase;phase++){
    const start=base(phase),night=phase%2,labels=[`Day${Math.floor(phase/2)+1}${night?'夜':'昼'}`,...(native?[]:['内訳']),...(night?[...Array.from({length:seerCount},(_,i)=>['占い位置'+(seerCount>1?i+1:''),'占い結果'+(seerCount>1?i+1:'')]).flat(),'襲撃位置',...(native?['死亡通知']:[])]:[...Array(updateCount(phase)).fill('盤面更新'),'処刑位置'])];
    const group=el('div',undefined,'compact-phase-group'+(night?' night':''));group.dataset.phaseGroup=phase;headers.append(group);selectionHeads.push({element:group,start,end:start+labels.length-1});
    labels.forEach((text,index)=>{const h=el('h3',text,'compact-tree-phase phase-heading'+(index>1?' action-heading':''));h.dataset.column=start+index;h.dataset.phase=phase;headers.append(h);headings.push(h);});
   }
   for(const item of entries){
    let row;if(item.kind==='action'){row=el('div',item.text,'compact-action-item');row.dataset.actionColumn=item.column;row.title=item.title;}
    else{const {d}=item;row=el('article',undefined,`tree-item compact-tree-item ${d.winner||''}`);if(item.kind==='board'||!item.hideGo)row.dataset.treeItem=d.node;else row.dataset.treeComposition=d.node;row.classList.toggle('current',d.node===currentNode);row.dataset.phase=`${d.column_day}-${d.column_phase}`;row.dataset.column=item.column;
     const main=el('button',item.update?item.text+(d.village_win==null?'':' · 村 '+d.village_win):(item.kind==='composition'?item.text+' · 村 '+d.village_win:(item.arrival?item.arrival+' · ':'')+(d.snapshot_only?'昼開始':`B${d.node}`)+` · ${d.alive.length}人`+(d.village_win==null?'':' · 村 '+d.village_win)),'compact-tree-select');main.type='button';main.onclick=()=>{inspect(d);openAnalysis(d,item.id);};main.disabled=item.kind!=='board';if(item.kind==='board')main.setAttribute('aria-haspopup','dialog');const go=el('button','→','compact-tree-go');go.type='button';go.disabled=root.dataset.treeNavigation!=='1'||d.public_current===false;go.title='このBoardをCurrentにする';go.setAttribute('aria-label',`B${d.node}へ遷移`);go.onclick=async e=>{e.stopPropagation();if(busy)return;busy=true;go.disabled=true;try{const response=await fetch('/game-tree/current',{method:'POST',body:new URLSearchParams({snapshot,node:d.node})}),result=await response.json();if(!response.ok)throw Error(result.error);if(new URL(result.url,location.origin).href===location.href)location.reload();else location.assign(result.url);}catch(error){status.textContent=error.message;go.disabled=false;busy=false;}};row.append(main);if(!item.hideGo&&item.kind==='board'&&d.public_current!==false)row.append(go);}
    if(item.kind!=='action')row.querySelectorAll('button').forEach(guardDragClick);row.dataset.treeKey=item.key;row.style.top=(item.cy-13.5)+'px';row.dataset.center=String(item.cy);if(item.span)row.dataset.span=item.span.join(',');item.element=row;canvas.append(row);
    item.ownHeight=ROW;
    if(item.kind==='board'&&analysisOpen.has(item.id)){const panel=inlineAnalysis(item);panel.style.maxWidth=Math.min(420,Math.max(220,frame.clientWidth-40))+'px';canvas.append(panel);item.panel=panel;item.ownHeight=ROW+8+panel.getBoundingClientRect().height;}
   }
   const widths=headings.map(h=>Math.ceil(h.getBoundingClientRect().width));for(const item of entries)widths[item.column]=Math.max(widths[item.column],Math.ceil(item.element.getBoundingClientRect().width),Math.ceil(item.panel?.getBoundingClientRect().width||0));
   // Measure wrapping at final content widths before either placement or wiring.
   for(const item of entries){item.element.style.width=widths[item.column]+'px';if(item.panel){item.panel.style.width=widths[item.column]+'px';item.ownHeight=ROW+8+item.panel.getBoundingClientRect().height;}}
   tree.height=window.TreeLayout.arrange(entries,{row:ROW,gap:GAP,padding:12});
   const offsets=[];let width=6;for(let i=0;i<columns;i++){offsets.push(width);headings[i].style.left=width+'px';headings[i].style.width=widths[i]+'px';width+=widths[i]+64;}headers.style.width=width+'px';canvas.style.width=width+'px';for(const h of selectionHeads){h.element.style.left=(offsets[h.start]-3)+'px';h.element.style.width=(offsets[h.end]+widths[h.end]-offsets[h.start]+6)+'px';}
   for(const item of entries){item.x=offsets[item.column];item.width=widths[item.column];item.element.style.left=item.x+'px';item.element.style.width=item.width+'px';if(item.panel){item.panel.style.left=item.x+'px';item.panel.style.width=item.width+'px';}}
   canvas.style.height=(tree.height+24)+'px';
   for(const item of entries){item.element.style.top=(item.cy-13.5)+'px';item.element.dataset.center=String(item.cy);if(item.panel)item.panel.style.top=(item.cy+21.5)+'px';}
   const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('width',String(width));svg.setAttribute('height',String(tree.height+24));svg.classList.add('compact-tree-lines');const arrows=new Map(),routed=window.TreeLayout.connect(entries,offsets,widths);
   function path(d,source,target,stub=false){const halo=document.createElementNS(ns,'path');halo.setAttribute('d',d);halo.style.stroke='white';halo.style.strokeWidth='4';svg.append(halo);const line=document.createElementNS(ns,'path');line.setAttribute('d',d);if(source)line.dataset.treeEdgeSource=source.key;if(target)line.dataset.treeEdgeTarget=target.key;if(stub)line.dataset.treeStub=source.key;svg.append(line);}
   for(const group of routed.strokes)path(group.map(edge=>edge.d).join(' '),group.length===1?group[0].from:null,group.every(edge=>edge.to===group[0].to)?group[0].to:null);
   for(const edge of routed.edges){if(edge.arrow)arrows.set(edge.to.x+','+edge.to.cy,[edge.to.x,edge.to.cy]);if(edge.probability!==null){const label=el('span',edge.probability,'compact-tree-edge');label.style.left=edge.label.x+'px';label.style.top=edge.label.y+'px';label.dataset.edgeProbability=edge.probability;label.dataset.edgeSource=edge.from.key;label.dataset.edgeTarget=edge.to.key;canvas.append(label);}}
   for(const join of routed.joins){path(join.d,null,join.to);arrows.set(join.to.x+','+join.y,[join.to.x,join.y]);}
   for(const stub of routed.stubs){path(stub.d,stub.from,null,true);arrows.set(stub.x+','+stub.y,[stub.x,stub.y]);}
   for(const item of entries)if(item.expandable){const x=item.x+item.width,y=item.cy,hit=document.createElementNS(ns,'rect');hit.classList.add('compact-tree-toggle');hit.dataset.treeToggle=item.key;hit.setAttribute('x',String(x-2));hit.setAttribute('y',String(y-13));hit.setAttribute('width','28');hit.setAttribute('height','26');hit.setAttribute('role','button');hit.setAttribute('tabindex','0');hit.setAttribute('aria-label',(item.text||'B'+item.id)+'の分岐');hit.setAttribute('aria-expanded',String(item.expanded));guardDragClick(hit);hit.addEventListener('click',event=>{event.stopPropagation();toggle(item);});hit.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();toggle(item);}});svg.append(hit);}
   for(const [x,y] of arrows.values()){const tip=document.createElementNS(ns,'polygon');tip.setAttribute('points',`${x-5},${y-3} ${x},${y} ${x-5},${y+3}`);tip.setAttribute('fill','#94aa9e');svg.append(tip);}canvas.prepend(svg);worldWidth=width;worldHeight=tree.height+24;applyView();frame.scrollLeft=oldLeft;frame.scrollTop=oldTop;syncHeader();
   requestAnimationFrame(()=>{if(version!==renderVersion)return;if(anchorId){const target=root.querySelector(`[data-tree-key="${anchorId}"]`);if(!target)return;const rect=target.getBoundingClientRect();if(anchorRect){frame.scrollLeft+=rect.left-anchorRect.left;frame.scrollTop+=rect.top-anchorRect.top;syncHeader();}else{frame.scrollLeft=Math.max(0,parseFloat(target.style.left)*scale-frame.clientWidth/2);frame.scrollTop=Math.max(0,parseFloat(target.dataset.center)*scale-frame.clientHeight/2);syncHeader();}}});
  }
  let pan=null;
  frame.addEventListener('pointerdown',event=>{if(pan||event.button!==0||event.target.closest('button,a,input,select,textarea,.compact-tree-item,.compact-action-item,.compact-tree-edge,.phase-heading,.compact-tree-toggle,.tree-inline-distribution'))return;pan={id:event.pointerId,x:event.clientX,y:event.clientY,left:frame.scrollLeft,top:frame.scrollTop};frame.setPointerCapture(event.pointerId);frame.classList.add('is-panning');event.preventDefault();});
  frame.addEventListener('pointermove',event=>{if(!pan||pan.id!==event.pointerId)return;frame.scrollLeft=pan.left-(event.clientX-pan.x);frame.scrollTop=pan.top-(event.clientY-pan.y);event.preventDefault();});
  function endPan(event){if(!pan||pan.id!==event.pointerId)return;const id=pan.id;pan=null;frame.classList.remove('is-panning');if(frame.hasPointerCapture(id))frame.releasePointerCapture(id);}
  for(const type of ['pointerup','pointercancel','lostpointercapture'])frame.addEventListener(type,endPan);
  let measuredWidth=root.getBoundingClientRect().width;new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(width===measuredWidth)return;measuredWidth=width;if(rootId!==null&&root.isConnected)render();}).observe(root);
  function unavailable(error){status.textContent=error.message;root.querySelector('.tree-flow-frame').hidden=true;headerViewport.hidden=true;const box=el('div',undefined,'tree-unavailable');box.dataset.treeUnavailable='1';if(error.detail?.actual){const c=error.detail.actual.counts;box.append(el('p',`現在の配役：市民${c.citizens}・占い${c.seers}・霊能${c.mediums}・狩人${c.hunters}・狼${c.wolves}`));}for(const issue of error.detail?.issues||[])box.append(el('p',issue));if(error.detail?.supported_route)box.append(el('p',error.detail.supported_route));const link=el('a','TOPで現在の設定を確認');link.href='/';box.append(link);content.parentElement.after(box);}
  (async()=>{
   try{const d=await load(null,true);rootId=d.node;render();}catch(e){unavailable(e);return;}
   root.dataset.treeAuto='loading';root.setAttribute('aria-busy','true');
   try{await expansion.auto('root',entry=>expansion.load(entry.d.node,()=>load(entry.d.node,true)),()=>{if(root.isConnected)render();},{current:currentNode,path:displayPath,alive:()=>root.isConnected});if(root.isConnected){status.textContent='';root.dataset.treeAuto='complete';}}
   catch(e){if(root.isConnected){status.textContent=e.message;root.dataset.treeAuto='error';}}
   finally{root.setAttribute('aria-busy','false');}
  })();
 }
 const init=()=>document.querySelectorAll('[data-calculation-tree]').forEach(mount);new MutationObserver(init).observe(document.documentElement,{childList:true,subtree:true});init();
})();
