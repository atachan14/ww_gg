"use strict";
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.TreeExpansion=factory();})(typeof globalThis==='object'?globalThis:this,()=>{
 function create(){const open=new Set(),pending=new Map(),runs=new Map(),items=new Map();let projected=new Map();return {
  isOpen:id=>open.has(id),
  toggle(id){if(open.has(id)){
   open.delete(id);const descendants=new Set(),collect=item=>{if(!item||descendants.has(item.key))return;descendants.add(item.key);for(const edge of item.next||[])collect(edge.item);};collect(items.get(id));
   const visible=new Set(),visit=item=>{if(!item||visible.has(item.key))return;visible.add(item.key);if(open.has(item.key))for(const edge of item.next||[])visit(edge.item);};visit(items.get('root'));
   for(const key of open)if((key.startsWith(id+'/')||descendants.has(key))&&!visible.has(key))open.delete(key);
   for(const [root,run] of runs)if([...run.paths].some(key=>key===id||((key.startsWith(id+'/')||descendants.has(key))&&!visible.has(key))))runs.delete(root);return false;
  }open.add(id);return true;},
  load(key,fetch){if(pending.has(key))return pending.get(key);const request=Promise.resolve().then(fetch).finally(()=>{if(pending.get(key)===request)pending.delete(key);});pending.set(key,request);return request;},
  item:id=>items.get(id),
  async chain(root,ensure,refresh){const run={paths:new Set([root])};runs.set(root,run);const live=()=>runs.get(root)===run&&open.has(root);let id=root;
   try{while(live()){let item=items.get(id);if(!item)return;run.paths.add(id);
    if(item.lazy){await ensure(item);if(!live())return;refresh();item=items.get(id);if(!item){id=root;continue;}if(item.lazy)return;}
    if(item.next.length!==1)return;const child=item.next[0].item;if(!child.expandable)return;id=child.key;run.paths.add(id);open.add(id);refresh();
   }}finally{if(runs.get(root)===run)runs.delete(root);}
  },
  project(item,id='root'){if(id==='root'){items.clear();projected=new Map();}if(projected.has(item))return projected.get(item);projected.set(item,item);if(item.shared)id='public:'+item.id;item.key=id;item.expandable=item.children.length>0||!!item.lazy;item.expanded=item.expandable&&open.has(id);const children=item.children.map((edge,index)=>({...edge,item:this.project(edge.item,id+'/'+edge.item.kind+':'+(edge.item.id??index)+':'+index)}));item.next=children;item.closedContinuation=item.expandable&&!item.expanded;items.set(id,item);item.children=item.expanded?children:[];item.height=Math.max(44,item.children.reduce((height,edge)=>height+edge.item.height,0)+Math.max(0,item.children.length-1)*14);return item;}
 };}
 return {create,isDrag:(start,end)=>!!start&&Math.hypot(end.clientX-start.clientX,end.clientY-start.clientY)>5};
});
