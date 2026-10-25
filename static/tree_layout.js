"use strict";
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.TreeLayout=factory();})(typeof globalThis==='object'?globalThis:this,()=>{
 // Elements must already be attached. Read intrinsic widths together, write
 // every final width together, then read wrapped heights together. No DOM
 // write may interleave a measurement phase and force a layout per Item.
 function measure(entries,headings,{row=44,cache=null}={}){
  const widths=headings.map(h=>Math.ceil(h.getBoundingClientRect().width));
  const pending=[];
  for(const item of entries){
   let metric=cache?.get(item.element);
   if(!metric){metric={intrinsic:Math.max(Math.ceil(item.element.getBoundingClientRect().width),Math.ceil((item.element.querySelector('.tree-win-corner')?.getBoundingClientRect().width||0)+2))};cache?.set(item.element,metric);}
   widths[item.column]=Math.max(widths[item.column],metric.intrinsic,Math.ceil(item.panel?.getBoundingClientRect().width||0));pending.push([item,metric]);
  }
  for(const [item] of pending){const width=widths[item.column]+'px';if(item.element.style.width!==width)item.element.style.width=width;if(item.panel)item.panel.style.width=width;}
  for(const [item,metric] of pending){const width=widths[item.column];if(!cache||metric.width!==width){metric.height=item.element.getBoundingClientRect().height;metric.width=width;}item.cardHeight=metric.height;item.ownHeight=Math.max(row,item.cardHeight+(item.panel?8+item.panel.getBoundingClientRect().height:0));}
  return widths;
 }
 function arrange(entries,{row=44,gap=14,padding=12}={}){
  // A skipped ability column still needs a visible lane. Without these routing
  // slots, a long edge can pass directly behind an unrelated collapsed Item.
  const proxies=new Map(entries.map(item=>[item,{column:item.column,ownHeight:Math.max(row,item.ownHeight||row),children:[],incoming:0,shared:!!item.shared} ])),all=[];
  for(const item of entries)for(const edge of item.children){
   const route=[];let parent=proxies.get(item);
   for(let column=item.column+1;column<edge.item.column;column++){
    const slot={column,ownHeight:row,children:[],incoming:1};route.push(slot);parent.children.push({item:slot});parent=slot;
   }
   const target=proxies.get(edge.item);target.incoming++;parent.children.push({item:target});edge.route=route;
  }
  // Visit original edges in their semantic order, including their empty-column
  // footprint. Shared destinations are visited once, never used to sort rows.
  const seen=new Set();function visit(item){if(seen.has(item))return;seen.add(item);all.push(item);for(const edge of item.children)visit(edge.item);}visit(proxies.get(entries[0]));
  const columns=new Map();for(const item of all){if(!columns.has(item.column))columns.set(item.column,[]);columns.get(item.column).push(item);}
  // First-child chains share a starting row. Shared Boards start independent
  // blocks, so their future expansion cannot reorder the incoming branches.
  const owner=new Map(all.map(item=>[item,item]));function find(item){const parent=owner.get(item);if(parent===item)return item;const root=find(parent);owner.set(item,root);return root;}
  for(const item of all){const first=item.children[0]?.item;if(first&&first.incoming===1&&!first.shared)owner.set(find(first),find(item));}
  const blocks=new Map();for(const item of all){const root=find(item);if(!blocks.has(root))blocks.set(root,{top:padding,next:new Map(),pending:0});}
  // Only original per-column order and measured occupied heights constrain
  // spacing. Longest paths remove all slack; no centers or barycenters exist.
  for(const rows of columns.values())for(let i=1;i<rows.length;i++){const before=blocks.get(find(rows[i-1])),after=blocks.get(find(rows[i])),distance=rows[i-1].ownHeight+gap;if(!before.next.has(after))after.pending++;before.next.set(after,Math.max(before.next.get(after)||0,distance));}
  const ready=[...blocks.values()].filter(block=>!block.pending);for(let i=0;i<ready.length;i++){const block=ready[i];for(const [next,distance] of block.next){next.top=Math.max(next.top,block.top+distance);if(!--next.pending)ready.push(next);}}
  for(const item of all)item.cy=blocks.get(find(item)).top+13.5;
  for(const item of entries){item.cy=proxies.get(item).cy;item.span=[item.cy-13.5,item.cy-13.5+Math.max(row,item.ownHeight||row)];}
  return Math.max(...all.map(item=>item.cy-13.5+item.ownHeight));
 }

 // Wiring consumes final geometry only. No per-edge track allocation, port
 // displacement, widening, or label obstacle search changes the node layout.
 function connect(entries,offsets,widths){
  const edges=entries.flatMap(from=>from.children.map(edge=>({from,to:edge.item,probability:edge.probability,route:[from,...edge.route.map(slot=>({...slot,x:offsets[slot.column],width:widths[slot.column]})),edge.item]}))),incoming=new Map(),joins=new Map();
  for(const edge of edges)incoming.set(edge.to,(incoming.get(edge.to)||0)+1);
  for(const edge of edges){const start=edge.from.x+edge.from.width,points=[[start,edge.from.cy]];let d=`M${start},${edge.from.cy}`;
   for(let i=1;i<edge.route.length;i++){const a=edge.route[i-1],b=edge.route[i],last=i===edge.route.length-1,merge=last&&incoming.get(edge.to)>1,x=a.x+a.width,guard=x+20,end=b.x-(merge?14:0),mid=(guard+end)/2;
    d+=` H${mid} V${b.cy} H${end}`;points.push([mid,a.cy],[mid,b.cy],[end,b.cy]);
    if(!last){d+=` H${b.x+b.width}`;points.push([b.x+b.width,b.cy]);}
    else if(merge)joins.set(edge.to,{to:edge.to,x:end,y:b.cy,d:`M${end},${b.cy} H${b.x}`});
   }
   edge.d=d;edge.points=points;edge.merging=incoming.get(edge.to)>1;edge.arrow=incoming.get(edge.to)===1;
   const branch=edge.from.children.length>1,next=edge.route[1];edge.label={x:branch?next.x-30:start+2,y:(branch?next.cy:edge.from.cy)-17};
  }
  const groups=new Map();for(const edge of edges){const key=edge.merging?'merge:'+edge.to.key:'split:'+edge.from.key;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(edge);}
  return {edges,strokes:[...groups.values()],joins:[...joins.values()],stubs:entries.filter(n=>n.closedContinuation).map(from=>({from,d:`M${from.x+from.width},${from.cy} h12`,x:from.x+from.width+12,y:from.cy}))};
 }
 return {arrange,connect,measure};
});
