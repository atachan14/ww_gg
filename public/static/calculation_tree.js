"use strict";
(()=>{
 const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const targetLabel=(targets,action,representative=targets[0])=>(targets.length>1?'['+[...targets].sort((a,b)=>a-b).map(p=>p===representative?'('+p+')':p).join(',')+']から':targets[0]+'を')+action;
 // Also format labels already cached by a running local server.
 const groupLabel=label=>label.replace(/(\d+)[（(]or(\d+(?:or\d+)*)[）)]を/g,(_,first,rest)=>'['+[first,...rest.split('or')].join(',')+']から');
 function mass(a,b){const pair=x=>x.split('/').map(BigInt),[an,ad=1n]=pair(a),[bn,bd=1n]=pair(b);let n=an*bn,d=ad*bd,x=n,y=d;while(y){const r=x%y;x=y;y=r;}n/=x;d/=x;return d===1n?String(n):`${n}/${d}`;}
 function mount(root){
  if(root.dataset.treeBound)return;root.dataset.treeBound='1';
  root.querySelectorAll('.tree-conditions,.compact-tree-legend,[data-tree-inspector]').forEach(e=>e.remove());
  const content=root.querySelector('[data-tree-content]'),status=root.querySelector('[data-tree-status]');
  let pausedForView=false;let expansion=window.TreeExpansion.create();const nodes=new Map(),frame=root.querySelector('.tree-flow-frame');let snapshot=null,rootId=null,busy=false,currentNode='0',displayPath=[],renderVersion=0;
  const viewport=window.TreeViewport,headerViewport=el('div',undefined,'tree-header-viewport');headerViewport.dataset.treeHeader='';frame.before(headerViewport);
  let scale=1,worldWidth=0,worldHeight=0,scene=null,headerScene=null;
  const rowCache=new Map(),measurementCache=new WeakMap();let loadGeneration=0,serverBatchSize=1,batchDisabled=false;
  const refresh=window.TreeExpansion.createRefresh({project:()=>render(undefined,true),paint:()=>render(),alive:()=>root.isConnected&&!pausedForView&&rootId!==null});
  const cancelRender=()=>refresh.cancel(),flushRender=()=>refresh.flush(),refreshModel=()=>refresh.update();
  async function autoExpand(options){const generation=loadGeneration;try{await expansion.auto('root',entry=>expansion.load(loadGeneration+':'+entry.d.node,()=>load(entry.d.node,true)),refreshModel,{...options,batchSize:window.PersonalNavigation?.context?1:serverBatchSize,ensureMany:loadBatch,alive:()=>generation===loadGeneration&&options.alive()});if(generation!==loadGeneration)throw new DOMException('Tree changed','AbortError');}finally{if(generation===loadGeneration)flushRender();}}
  const distributions=new Map(),analysisOpen=new Set(),accordionOpen=new Set(),analysisErrors=new Map();
  function win(value,cls=''){const node=el('span',undefined,'probability '+cls),formatted=window.ProbabilityDisplay.formats(value);node.dataset.fraction=formatted.fraction;node.dataset.percent=formatted.percent;let mode=document.querySelector('[name="probability-format"]:checked')?.value;try{mode ||= localStorage.getItem('ww_gg.probability-format');}catch(_){}node.textContent=window.ProbabilityDisplay.text(value,mode);return node;}
  document.addEventListener('probability-format-change',()=>{if(root.isConnected&&rootId!==null)render();});

  async function openAnalysis(d,id=d.node){
   d=nodes.get(d.node)||d;
   if(analysisOpen.has(id)){analysisOpen.delete(id);render();return;}
   analysisOpen.add(id);render();
   if(d.snapshot_only||distributions.has(id))return;
   try{const data=await expansion.load(loadGeneration+':analysis:'+id,()=>load(id,false,true));if(data.distribution)distributions.set(id,data.distribution);if(root.isConnected)render();}
   catch(error){if(error.name!=='AbortError'){analysisErrors.set(id,error.message);if(root.isConnected)render();}}
  }
  function inlineAnalysis(item){
   const d=item.d,rows=distributions.get(item.id)||d.distribution||(d.compositions||[]).map(c=>({id:c.node,label:c.label,probability:c.probability,village_win:nodes.get(c.node)?.village_win??null,children:[]}));
   const panel=el('section',undefined,'tree-inline-distribution');panel.setAttribute('aria-label','秘密状態の分布');panel.dataset.distributionFor=item.id;
   function append(parent,rows){for(const row of rows){const key=item.id+'/'+row.id,content=()=>{const fragment=document.createDocumentFragment();fragment.append(row.probability+'['+row.label);if(row.village_win!=null){fragment.append('・');fragment.append(win(row.village_win));}fragment.append(']');return fragment;};
    if(row.children?.length){const details=el('details',undefined,'tree-distribution-branch'),summary=el('summary');summary.append(content());details.dataset.distributionPath=key;details.open=accordionOpen.has(key);summary.onclick=event=>{event.preventDefault();event.stopPropagation();if(accordionOpen.has(key))accordionOpen.delete(key);else accordionOpen.add(key);render(item.key);root.querySelector('[data-distribution-path="'+CSS.escape(key)+'"]>summary')?.focus({preventScroll:true});};details.append(summary);const children=el('div',undefined,'tree-distribution-children');append(children,row.children);details.append(children);parent.append(details);}
    else {const leaf=el('div',undefined,'tree-distribution-leaf');leaf.append(content());parent.append(leaf);}
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
  let footer=document.querySelector('.phase-footer');
  function fitArea(){const footerHeight=footer?.getBoundingClientRect().height||0,height=window.visualViewport?.height||window.innerHeight;root.style.setProperty('--tree-footer-height',footerHeight+'px');root.closest('.page-shell')?.style.setProperty('--tree-footer-height',footerHeight+'px');root.style.height=viewport.areaHeight(height,footerHeight)+'px';if(scene)applyView();}
  const footerObserver=new ResizeObserver(fitArea);if(footer)footerObserver.observe(footer);window.addEventListener('resize',fitArea);window.visualViewport?.addEventListener('resize',fitArea);fitArea();
  function keep(d){if(!d.column_phase){d.column_day=1+Math.floor(d.history.length/2);d.column_phase=d.history.length%2?'night':'day';}const old=nodes.get(d.node);nodes.set(d.node,old?.actions&&!d.actions?{...d,actions:old.actions}:d);for(const item of Object.values(d.items||{}))keep(item);}
  async function load(id,expand=false,analysis=false){const q=new URLSearchParams();if(id!==null)q.set('node',id);if(snapshot)q.set('snapshot',snapshot);if(expand)q.set('expand','1');if(analysis)q.set('analysis','1');const current=new URL(location.href).searchParams.get('current');if(current)q.set('current',current);const scope=window.PersonalNavigation,version=scope?.generation,generation=loadGeneration;let d;if(scope?.context)d=await scope.request('tree',{node:id,expand,analysis,snapshot});else{q.set('format','public-tree');q.set('defer_analysis','1');const response=await fetch('/game-tree?'+q,{cache:'no-store'});d=await response.json();assertLive(version,generation);if(!response.ok)throw Object.assign(Error(d.error),{detail:d});}return accept(d,version,generation);}
  function assertLive(version,generation){if(version!==window.PersonalNavigation?.generation||generation!==loadGeneration||!root.isConnected)throw new DOMException('View changed','AbortError');}
  function accept(d,version,generation){assertLive(version,generation);serverBatchSize=d.tree_batch_size||1;snapshot=d.snapshot;if(d.navigation_revision!==undefined)root.dataset.navigationRevision=d.navigation_revision;currentNode=d.current_node||'0';displayPath=d.display_path||[];keep(d);return d;}
  async function loadBatch(entries){
   const generation=loadGeneration,version=window.PersonalNavigation?.generation,ids=new Map(entries.map(entry=>[generation+':'+entry.d.node,entry.d.node]));
   return expansion.loadMany([...ids.keys()],async keys=>{
    const single=async()=>{const rows=[];for(const key of keys){assertLive(version,generation);rows.push(await load(ids.get(key),true));refreshModel();}return rows;};if(batchDisabled)return single();
    const q=new URLSearchParams({snapshot,expand:'1',format:'public-tree',defer_analysis:'1'});for(const key of keys)q.append('node',ids.get(key));
    const response=await fetch('/game-tree?'+q,{cache:'no-store'}),data=await response.json();assertLive(version,generation);if(response.status===503&&['work','time'].includes(data.budget_kind)&&keys.length>1){batchDisabled=true;return single();}if(!response.ok)throw Object.assign(Error(data.error),{detail:data});
    const rows=data.batch||[data];if(rows.length!==keys.length||rows.some((row,i)=>row.node!==ids.get(keys[i])))throw Error('Incomplete Tree batch');
    return rows.map(row=>accept(row,version,generation));
   });
  }
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
   try{await expansion.chain(item.key,entry=>expansion.load(loadGeneration+':'+entry.d.node,()=>load(entry.d.node,true)),()=>{if(root.isConnected){status.textContent='';render(item.key);}});}
   catch(error){if(error.name!=='AbortError'&&root.isConnected&&expansion.isOpen(item.key))status.textContent=error.message;}
  }

  function render(anchorId,projectOnly=false){
   if(!projectOnly)cancelRender();
   const version=projectOnly?renderVersion:++renderVersion,oldLeft=projectOnly?0:frame.scrollLeft,oldTop=projectOnly?0:frame.scrollTop,oldAnchor=anchorId?root.querySelector(`[data-tree-key="${anchorId}"]`):null,anchorRect=oldAnchor?.getBoundingClientRect();
   const entries=[],links=[],ROW=44,GAP=14;let maxPhase=3;
   const native=[...nodes.values()].some(d=>d.native_mode),publication=[...nodes.values()].some(d=>(d.public_claims||[]).some(c=>c==='seer'||c==='medium')),timeline=nodes.get(rootId)?.input_timeline;
   const phaseRoles=new Map();
   function rolesAt(phase){
    if(phaseRoles.has(phase))return phaseRoles.get(phase);
    const at=d=>(d.column_day-1)*2+(d.column_phase==='night'?1:0);
    let rows=[...nodes.values()].filter(d=>!d.winner&&at(d)===phase);
    if(!rows.length)rows=[...nodes.values()].filter(d=>!d.winner&&at(d)===phase-1);
    // Lazy Board summaries carry roster counts, not evaluated ability columns.
    rows=rows.filter(d=>d.night_stages||d.ability_choices);
    const counts={seerCount:Math.max(0,...rows.map(d=>d.stage_roles?.seers??Math.max(0,...(d.compositions||[]).map(c=>c.counts?.seers||0)))),mediumCount:Math.max(0,...rows.map(d=>d.stage_roles?.mediums||0)),hunterCount:Math.max(0,...rows.map(d=>d.stage_roles?.hunters||0))};
    phaseRoles.set(phase,counts);return counts;
   }
   const phaseUpdates=Object.assign({},...[...nodes.values()].map(d=>d.navigation_phase_updates||{}));
   const updateCount=phase=>native?Math.max(phase===0?(timeline?.updates.length||0):(publication?1:0),Number(phaseUpdates[phase]||0)):0;
   const dayWidth=phase=>(native?2:3)+updateCount(phase),nightWidth=phase=>{const {mediumCount,seerCount,hunterCount}=rolesAt(phase);return 3+mediumCount+2*seerCount+hunterCount;};
   const base=phase=>{let start=0;for(let p=0;p<phase;p++)start+=p%2?nightWidth(p):dayWidth(p);return start;};
   function make(kind,column,data,children=[]){return {kind,column,...data,children,height:Math.max(ROW,children.reduce((h,c)=>h+c.item.height,0)+Math.max(0,children.length-1)*GAP)};}
   function choices(d,path,reach){
    if(d.winner)return [];
    if(d.cutoff_marker&&d.actions===null){
     const marker=d.cutoff_marker,phase=(marker.day-1)*2;maxPhase=Math.max(maxPhase,phase);
     return [{probability:null,item:make('cutoff',base(phase)+dayWidth(phase)-1,{text:marker.label,title:'',explanatory:true})}];
    }
    const phase=(d.column_day-1)*2+(d.column_phase==='night'?1:0),{seerCount,mediumCount,hunterCount}=rolesAt(phase),column=base(phase)+(native?1+(d.phase==='day'?updateCount(phase):0):2);
    if(d.phase==='night'&&d.night_stages){
     const walk=(stage,index,parentReach)=>{
      if(native&&stage.branches?.length&&stage.branches.every(b=>b.kind==='publication')){
       const leaves=[];const gather=s=>{if(s.leaves)leaves.push(...s.leaves);else for(const b of s.branches||[])gather(b.children);};gather(stage);
       const first=leaves.find(leaf=>nodes.get(leaf.node)?.day_arrival);
       if(first)return [{probability:'1',item:build(first.node,path,undefined,parentReach,first.context_node)}];
      }
      if(stage.leaves)return stage.leaves.map(leaf=>{const exact=(leaf.variants||[]).find(v=>displayPath.includes(v.node));return {probability:leaf.probability,item:build(exact?exact.node:leaf.node,path,undefined,mass(parentReach,leaf.probability),leaf.context_node)};}).filter(x=>x.item);
      return (stage.branches||[]).map(branch=>{const reach=mass(parentReach,branch.probability),position=d.night_stages.method==='evaluation-recorded-v1'?mediumCount+2*seerCount+hunterCount+(branch.kind==='death_notice'?1:0):branch.stage_column??(branch.kind==='wolf_target'?2*seerCount:branch.kind==='death_notice'?2*seerCount+1:branch.kind==='publication'?2*seerCount+2:index);
       // Separate records may omit unused roles; align their actual stages in the phase union.
       const local=d.stage_roles||{mediums:mediumCount,seers:seerCount,hunters:hunterCount},effective=['ability_dead','ability_reduced'].includes(branch.kind)?branch.value:branch.kind;
       const shift=d.night_stages.method==='anonymous-relational-v1'?(effective==='medium_result'?0:mediumCount-local.mediums+(effective==='seer_target'||effective==='seer_result'?0:2*(seerCount-local.seers)+(effective==='guard_target'?0:hunterCount-local.hunters))):0;
       const image=(branch.images||[]).find(image=>image.children&&image.nodes.some(id=>displayPath.includes(id)));
       const descendants=walk(image?image.children:branch.children,index+1,reach);
       return {probability:branch.probability,item:make('action',column+position+shift,{text:branch.label,title:(native?'同時行動 / 夜内の到達 '+branch.mass:'\u540c\u6642\u884c\u52d5 / \u5230\u9054 '+reach)+' / \u62ec\u5f27\u306f\u4ee3\u8868\u914d\u7f6e\u3002\u80fd\u529b\u8005\u3068\u5bfe\u8c61\u306f\u540c\u3058\u540d\u524d\u7f6e\u63db\u306b\u5f93\u3044\u307e\u3059\u3002'},descendants)};
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
      const children=scan.results?scan.results.map(result=>({probability:result.probability,item:make('action',column+1,{text:result.label,title:'\u5360\u3044\u5e2b\u306e\u975e\u516c\u958b\u7d50\u679c\u3002\u4eba\u72fc\u306e\u65b9\u7b56\u306f\u7d50\u679c\u3092\u89b3\u6e2c\u3059\u308b\u524d\u306b\u6c7a\u5b9a\u3002 / \u5230\u9054 '+mass(scanReach,result.probability)},attacks(result.attacks,mass(scanReach,result.probability)))})):attacks(scan.attacks,scanReach);
      return {probability:scan.probability,item:make('action',column,{text:scan.label,title:'\u540c\u6642\u884c\u52d5\u3092\u8868\u793a\u9806\u306b\u5206\u3051\u3066\u3044\u307e\u3059\u3002'},children)};
     });
    }
    return (d.actions||[]).map(action=>({probability:action.policy_probability,item:make('action',d.phase==='night'?column+2*seerCount:column,{text:d.phase==='day'?targetLabel(action.targets,'処刑',action.representative??action.targets[0]):groupLabel(action.label),title:(d.ability_pending?d.ability_pending+'\n':'')+action.members.map(m=>m.target+' · '+m.policy_mass).join(' / ')},action.branches.map(branch=>{const exact=branch.variants.find(v=>displayPath.includes(v.node));return {probability:branch.probability,item:build(exact?exact.node:branch.node,path,branch.outcome_label,mass(reach,mass(action.policy_probability,branch.probability)))};}).filter(x=>x.item))}));
   }
   const sharedBoards=new Map();
   function updated(d,label,column,path,reach){
    const identity='updated:'+d.node;
    if(d.public_bundle&&sharedBoards.has(identity))return sharedBoards.get(identity);
    const next=new Set([...path,d.node]),item=make('board',column,{d,id:d.node,text:label,update:true,sharedIdentity:!!d.public_bundle,contexts:new Set(),lazy:!d.winner&&!d.win_certificate&&!d.actions},path.has(d.node)?[]:choices(d,next,reach));
    if(d.public_bundle)sharedBoards.set(identity,item);return item;
   }
   function build(id,path=new Set(),arrival,reach='1',context){
    const d=nodes.get(id);if(!d)return null;
    const phase=(d.column_day-1)*2+(d.column_phase==='night'?1:0);maxPhase=Math.max(maxPhase,phase);
    if(native&&d.public_updates){
     if(sharedBoards.has(id))return sharedBoards.get(id);
     const next=new Set([...path,id]),children=[...d.public_updates.map(update=>{const after=nodes.get(update.node);return after?{probability:update.probability,item:updated(after,update.label,base(phase)+1,next,mass(reach,update.probability))}:null;}).filter(Boolean),...(d.manual_updates||[]).map(update=>({probability:update.probability,item:build(update.node,next,undefined,reach)})).filter(e=>e.item)];
     const item=make('board',base(phase),{d,id,sharedIdentity:true,contexts:new Set()},path.has(id)?[]:children);sharedBoards.set(id,item);return item;
    }
    if(native&&d.day_arrival){
     const a=d.day_arrival;if(nodes.has(a.id)&&a.id!==id)return build(a.id,path,arrival,reach,context);if(sharedBoards.has(a.id))return sharedBoards.get(a.id);
     const children=a.updates.map(update=>{const after=nodes.get(update.node);return after?{probability:update.probability,item:updated(after,update.label,base(phase)+1,path,mass(reach,update.probability))}:null;}).filter(Boolean);
     const item=make('board',base(phase),{d:a.state,id:a.id,sharedIdentity:true,contexts:new Set(context?[context]:[])},children);sharedBoards.set(a.id,item);return item;
    }
    if(native&&id===rootId&&timeline?.updates.length){
     const rows=timeline.updates;let tail=updated(d,rows[rows.length-1].label,base(phase)+rows.length,path,reach);
     for(let i=rows.length-2;i>=0;i--)tail=make('board',base(phase)+i+1,{d:rows[i].state,id:rows[i].state.node,text:rows[i].label,update:true},[{probability:null,item:tail}]);
     return make('board',base(phase),{d:timeline.before,id:timeline.before.node},[{probability:null,item:tail}]);
    }
    if(native&&d.public_bundle&&sharedBoards.has(id)){const item=sharedBoards.get(id);if(context)item.contexts.add(context);return item;}
    if(native){const next=new Set([...path,id]),children=path.has(id)?[]:[...choices(d,next,reach),...(d.manual_updates||[]).map(update=>({probability:update.probability,item:build(update.node,next,undefined,reach)})).filter(edge=>edge.item)],item=make('board',base(phase)+(d.navigation_depth||0),{d,id,arrival,text:d.navigation_label,update:!!d.navigation_label,shared:!!d.public_bundle,contexts:new Set(context?[context]:[]),lazy:!d.winner&&!d.win_certificate&&!d.actions},children);if(d.public_bundle)sharedBoards.set(id,item);return item;}
    if(d.cutoff_marker&&d.actions===null)return make('board',base(phase),{d,id,arrival},path.has(id)?[]:choices(d,new Set([...path,id]),reach));
    const next=new Set([...path,id]),compositions=d.compositions||[{node:id,label:'内訳未取得',probability:'1'}];
    const children=path.has(id)?[]:compositions.map(composition=>{const c=nodes.get(composition.node)||d;return {probability:composition.probability,item:make('composition',base(phase)+1,{d:c,id:c.node,text:composition.label,hideGo:c.node===id,lazy:!c.winner&&!c.actions},choices(c,next,mass(reach,composition.probability)))};});
    return make('board',base(phase),{d,id,arrival,lazy:!d.winner&&!d.win_certificate&&!d.compositions?.length},children);
   }
   const complete=build(rootId);if(!complete)return;const tree=expansion.project(complete);if(projectOnly)return;
   const seen=new Set();function collect(item){if(seen.has(item))return;seen.add(item);entries.push(item);for(const child of item.children){collect(child.item);links.push([item,child.item,child.probability,child]);}}collect(tree);
   const occupied=new Set(entries.map(item=>item.column)),columnMap=new Map();let columns=0;
   const canvas=scene||el('div',undefined,'compact-tree-canvas'),headers=el('div',undefined,'compact-tree-headers'),headings=[],selectionHeads=[];canvas.style.height=(tree.height+24)+'px';canvas.style.transform='';if(canvas.parentElement!==content)content.replaceChildren(canvas);canvas.querySelectorAll('.compact-tree-lines,.compact-tree-edge,.tree-inline-distribution').forEach(e=>e.remove());const visibleKeys=new Set(entries.map(item=>item.key));for(const child of [...canvas.children])if(!visibleKeys.has(child.dataset.treeKey))child.remove();headerViewport.replaceChildren(headers);scene=canvas;headerScene=headers;
   for(let phase=0;phase<=maxPhase;phase++){
    const {seerCount,mediumCount,hunterCount}=rolesAt(phase),start=base(phase),night=phase%2,labels=[`Day${Math.floor(phase/2)+1}${night?'夜':'昼'}`,...(native?[]:['内訳']),...(night?[...Array.from({length:mediumCount},(_,i)=>'霊能結果'+(mediumCount>1?i+1:'')),...Array.from({length:seerCount},(_,i)=>['占い位置'+(seerCount>1?i+1:''),'占い結果'+(seerCount>1?i+1:'')]).flat(),...Array.from({length:hunterCount},(_,i)=>'護衛位置'+(hunterCount>1?i+1:'')),'襲撃位置',...(native?['死亡通知']:[])]:[...Array(updateCount(phase)).fill('盤面更新'),'処刑位置'])];
    const first=columns,abilityStart=native?1:2,abilityEnd=abilityStart+mediumCount+2*seerCount+hunterCount;
    const visible=labels.map((text,index)=>({text,index})).filter(({index})=>!native||!night||index<abilityStart||index>=abilityEnd||occupied.has(start+index));
    const group=el('div',undefined,'compact-phase-group'+(night?' night':''));group.dataset.phaseGroup=phase;headers.append(group);selectionHeads.push({element:group,start:first,end:first+visible.length-1});
    visible.forEach(({text,index})=>{const column=columns++;columnMap.set(start+index,column);const h=el('h3',text,'compact-tree-phase phase-heading'+(index>1?' action-heading':''));h.dataset.column=column;h.dataset.phase=phase;headers.append(h);headings.push(h);});
   }
   // Closed alternatives must not reserve empty ability columns for visible paths.
   for(const item of entries)item.column=columnMap.get(item.column);
   const panelMaxWidth=analysisOpen.size?Math.min(420,Math.max(220,frame.clientWidth-40)):0;
   let previousRow=null;let probabilityMode='';try{probabilityMode=localStorage.getItem('ww_gg.probability-format')||'';}catch(_){}
   for(const item of entries){
    const signature=JSON.stringify([item.kind,item.text,item.arrival,item.update,item.hideGo,item.id,item.d?.node,item.d?.board_number,item.d?.alive?.length,item.d?.winner,item.d?.snapshot_only,item.d?.village_win,item.d?.public_current,item.title,item.d?.column_day,item.d?.column_phase,root.dataset.treeNavigation,document.querySelector('[name="probability-format"]:checked')?.value,probabilityMode]);
    const cached=rowCache.get(item.key);let row;if(cached?.signature===signature)row=cached.row;else{ if(item.kind==='action'||item.kind==='cutoff'){row=el('div',item.text,'compact-action-item');row.dataset.actionColumn=item.column;row.title=item.title;if(item.kind==='cutoff')row.dataset.cutoffMarker='';}
    else{const {d}=item;row=el('article',undefined,`tree-item compact-tree-item ${d.winner||''}`);if(item.kind==='board'||!item.hideGo)row.dataset.treeItem=d.node;else row.dataset.treeComposition=d.node;row.classList.toggle('current',d.node===currentNode);row.dataset.phase=`${d.column_day}-${d.column_phase}`;row.dataset.column=item.column;
     const main=el('button',item.update?undefined:(item.kind==='composition'?item.text:(item.arrival?item.arrival+' · ':'')+(d.snapshot_only?'昼開始':`B${d.board_number??d.node}`)+` · ${d.alive.length}人`),'compact-tree-select');if(item.update){row.classList.add('compact-tree-update');for(const line of item.text.split(' / '))main.append(el('span',line,'tree-log-row'));}if(item.kind==='board')row.classList.add('compact-tree-board');if(d.village_win!=null){if(item.kind==='board')row.append(win(d.village_win,'tree-win-corner'));else{main.append(' \u00b7 \u6751 ');main.append(win(d.village_win));}};main.type='button';main.onclick=()=>{inspect(d);openAnalysis(d,item.id);};main.disabled=item.kind!=='board';if(item.kind==='board')main.setAttribute('aria-haspopup','dialog');const go=el('button','→','compact-tree-go');go.type='button';go.disabled=root.dataset.treeNavigation!=='1'||d.public_current===false;go.title='このBoardをCurrentにする';go.setAttribute('aria-label',`B${d.board_number??d.node}へ遷移`);go.onclick=async e=>{e.stopPropagation();if(busy)return;busy=true;go.disabled=true;try{let result;if(window.PersonalNavigation?.context){result=await window.PersonalNavigation.request('current',{snapshot,node:d.node});await window.PersonalNavigation.install(result);busy=false;return;}const response=await fetch('/game-tree/current',{method:'POST',headers:{'X-WW-Staged':'1'},body:new URLSearchParams({snapshot,node:d.node,...(root.dataset.navigationRevision!==undefined?{revision:root.dataset.navigationRevision}:{})})});result=await response.json();if(!response.ok)throw Error(result.error);if(result.html&&window.BoardNavigation){await window.BoardNavigation.install(result);busy=false;}else if(new URL(result.url,location.origin).href===location.href)location.reload();else location.assign(result.url);}catch(error){status.textContent=error.message;go.disabled=false;busy=false;}};row.append(main);if(!item.hideGo&&item.kind==='board'&&d.public_current!==false)row.append(go);}
    if(item.kind!=='action')row.querySelectorAll('button').forEach(guardDragClick);if(cached)cached.row.remove();rowCache.set(item.key,{signature,row});}row.classList.toggle('current',item.d?.node===currentNode);const go=row.querySelector('.compact-tree-go');if(go)go.disabled=root.dataset.treeNavigation!=='1'||item.d?.public_current===false;row.dataset.treeKey=item.key;if(item.kind==='action')row.dataset.actionColumn=item.column;else row.dataset.column=item.column;if(item.span)row.dataset.span=item.span.join(',');item.element=row;const before=previousRow?previousRow.nextSibling:canvas.firstChild;if(before!==row)canvas.insertBefore(row,before);previousRow=row;
    if(item.kind==='board'&&analysisOpen.has(item.id)){const panel=inlineAnalysis(item);panel.style.maxWidth=panelMaxWidth+'px';canvas.append(panel);item.panel=panel;}
   }
   // The same intrinsic columns and final wrapped heights, measured in batches.
   const widths=window.TreeLayout.measure(entries,headings,{row:ROW,cache:measurementCache});
   tree.height=window.TreeLayout.arrange(entries,{row:ROW,gap:GAP,padding:12});
   for(const item of entries){item.cardTop=item.cy-13.5;item.cy=item.cardTop+item.cardHeight/2;item.span=[item.cardTop,item.cardTop+item.ownHeight];}
   const offsets=[];let width=6;for(let i=0;i<columns;i++){offsets.push(width);headings[i].style.left=width+'px';headings[i].style.width=widths[i]+'px';width+=widths[i]+64;}headers.style.width=width+'px';canvas.style.width=width+'px';for(const h of selectionHeads){h.element.style.left=(offsets[h.start]-3)+'px';h.element.style.width=(offsets[h.end]+widths[h.end]-offsets[h.start]+6)+'px';}
   for(const item of entries){item.x=offsets[item.column];item.width=widths[item.column];item.element.style.left=item.x+'px';item.element.style.width=item.width+'px';if(item.panel){item.panel.style.left=item.x+'px';item.panel.style.width=item.width+'px';}}
   canvas.style.height=(tree.height+24)+'px';
   for(const item of entries){item.element.style.top=item.cardTop+'px';item.element.dataset.center=String(item.cy);if(item.panel)item.panel.style.top=(item.cardTop+item.cardHeight+8)+'px';}
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
  document.addEventListener('personal-view-loading',()=>{if(root.isConnected){pausedForView=true;cancelRender();expansion.cancel();}});
  document.addEventListener('personal-view-change',async()=>{
   if(!root.isConnected)return;
   pausedForView=false;++loadGeneration;rowCache.clear();scene?.replaceChildren();cancelRender();expansion.cancel();expansion=window.TreeExpansion.create();nodes.clear();distributions.clear();analysisOpen.clear();accordionOpen.clear();analysisErrors.clear();snapshot=null;rootId=null;++renderVersion;
   try{const d=await load(null,true);rootId=d.node;frame.hidden=false;headerViewport.hidden=false;render();await autoExpand({current:currentNode,path:displayPath,alive:()=>root.isConnected&&!pausedForView});status.textContent='';root.dataset.treeAuto='complete';}
   catch(error){if(error.name!=='AbortError')status.textContent=error.message;}
  });
  document.addEventListener('navigation-board-change',async event=>{
   if(!root.isConnected)return;++loadGeneration;cancelRender();expansion.cancel();root.dataset.navigationRevision=root.closest('main').dataset.navigationRevision;if(pendingCurrent())return;root.querySelector('[data-pending-current]')?.remove();root.dataset.navigationUpdate='loading';
   const oldFooter=footer;footer=document.querySelector('.phase-footer');if(oldFooter)footerObserver.unobserve(oldFooter);if(footer)footerObserver.observe(footer);fitArea();
   try{
    const collapse=event.detail?.collapse_owner;
    if(collapse){const entry=[...root.querySelectorAll('[data-tree-item]')].find(e=>e.dataset.treeItem===collapse);if(entry&&expansion.isOpen(entry.dataset.treeKey))expansion.toggle(entry.dataset.treeKey);}
    const updated=await load(rootId,true);rootId=updated.node;render();
    await autoExpand({current:currentNode,path:displayPath,onlyPathUntilCurrent:!!collapse,alive:()=>root.isConnected&&!pausedForView});
    status.textContent='';root.dataset.navigationUpdate='complete';root.dataset.treeAuto='complete';root.setAttribute('aria-busy','false');
   }catch(error){if(error.name!=='AbortError'){status.textContent=error.message;root.dataset.navigationUpdate='error';}}
  });
  let pan=null;
  frame.addEventListener('pointerdown',event=>{if(pan||event.button!==0||event.target.closest('button,a,input,select,textarea,.compact-tree-item,.compact-action-item,.compact-tree-edge,.phase-heading,.compact-tree-toggle,.tree-inline-distribution'))return;pan={id:event.pointerId,x:event.clientX,y:event.clientY,left:frame.scrollLeft,top:frame.scrollTop};frame.setPointerCapture(event.pointerId);frame.classList.add('is-panning');event.preventDefault();});
  frame.addEventListener('pointermove',event=>{if(!pan||pan.id!==event.pointerId)return;frame.scrollLeft=pan.left-(event.clientX-pan.x);frame.scrollTop=pan.top-(event.clientY-pan.y);event.preventDefault();});
  function endPan(event){if(!pan||pan.id!==event.pointerId)return;const id=pan.id;pan=null;frame.classList.remove('is-panning');if(frame.hasPointerCapture(id))frame.releasePointerCapture(id);}
  for(const type of ['pointerup','pointercancel','lostpointercapture'])frame.addEventListener(type,endPan);
  let measuredWidth=root.getBoundingClientRect().width;new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(width===measuredWidth)return;measuredWidth=width;if(rootId!==null&&root.isConnected)render();}).observe(root);
  function pendingCurrent(){
   const main=root.closest('main'),pending=main?.dataset.navigationCalculation;if(!pending||pending==='complete')return false;
   root.dataset.navigationUpdate='pending';root.dataset.treeAuto='pending';status.textContent='勝率計算中';
   let marker=root.querySelector('[data-pending-current]');if(!marker){marker=el('article',undefined,'tree-item');marker.dataset.pendingCurrent='';root.querySelector('h2').after(marker);}
   marker.textContent='Current '+main.dataset.navigationOccurrence+' → 計算中';root.querySelectorAll('.compact-tree-item.current').forEach(e=>e.classList.remove('current'));return true;
  }
  function unavailable(error){status.textContent=error.message;root.querySelector('.tree-flow-frame').hidden=true;headerViewport.hidden=true;const box=el('div',undefined,'tree-unavailable');box.dataset.treeUnavailable='1';if(error.detail?.actual){const c=error.detail.actual.counts;box.append(el('p',`現在の配役：市民${c.citizens}・占い${c.seers}・霊能${c.mediums}・狩人${c.hunters}・人狼${c.wolves}`));}for(const issue of error.detail?.issues||[])box.append(el('p',issue));if(error.detail?.supported_route)box.append(el('p',error.detail.supported_route));const link=el('a','TOPで現在の設定を確認');link.href='/';box.append(link);content.parentElement.after(box);}
  (async()=>{
   if(pendingCurrent())return;
   try{const d=await load(null,true);rootId=d.node;render();}catch(e){if(e.name!=='AbortError')unavailable(e);return;}
   root.dataset.treeAuto='loading';root.setAttribute('aria-busy','true');
   try{await autoExpand({current:currentNode,path:displayPath,onlyPathUntilCurrent:displayPath.length>1&&root.dataset.navigationRevision!==undefined,alive:()=>root.isConnected&&!pausedForView});if(root.isConnected){status.textContent='';root.dataset.treeAuto='complete';}}
   catch(e){if(root.isConnected&&e.name!=='AbortError'){status.textContent=e.message;root.dataset.treeAuto='error';}}
   finally{root.setAttribute('aria-busy','false');}
  })();
 }
 const init=()=>document.querySelectorAll('[data-calculation-tree]').forEach(mount);new MutationObserver(init).observe(document.documentElement,{childList:true,subtree:true});init();
})();
