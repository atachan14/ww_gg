"use strict";
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.TreeExpansion=factory();})(typeof globalThis==='object'?globalThis:this,()=>{
 function create(){const open=new Set(),pending=new Map();return {
  isOpen:id=>open.has(id),
  toggle(id){if(open.has(id)){for(const key of open)if(key===id||key.startsWith(id+'/'))open.delete(key);return false;}open.add(id);return true;},
  load(key,fetch){if(pending.has(key))return pending.get(key);const request=Promise.resolve().then(fetch).finally(()=>{if(pending.get(key)===request)pending.delete(key);});pending.set(key,request);return request;},
  project(item,id='root'){item.key=id;item.expandable=item.children.length>0||!!item.lazy;item.expanded=item.expandable&&open.has(id);const children=item.children.map((edge,index)=>({...edge,item:this.project(edge.item,id+'/'+edge.item.kind+':'+(edge.item.id??index)+':'+index)}));item.children=item.expanded?children:[];item.height=Math.max(44,item.children.reduce((height,edge)=>height+edge.item.height,0)+Math.max(0,item.children.length-1)*14);return item;}
 };}
 return {create,isDrag:(start,end)=>!!start&&Math.hypot(end.clientX-start.clientX,end.clientY-start.clientY)>5};
});
