"use strict";
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.TreeLayout=factory();})(typeof globalThis==='object'?globalThis:this,()=>{
 // Solve top[i+1] >= top[i] + height[i] + gap with the least squared
 // displacement from the children's centers (isotonic regression).
 function pack(rows,gap){
  const blocks=[];let offset=0;
  for(let i=0;i<rows.length;i++){
   const item=rows[i],block={start:i,end:i,sum:item.cy-13.5-offset,count:1};
   item.offset=offset;blocks.push(block);offset+=item.ownHeight+gap;
   while(blocks.length>1){const b=blocks.at(-1),a=blocks.at(-2);if(a.sum/a.count<=b.sum/b.count)break;blocks.splice(-2,2,{start:a.start,end:b.end,sum:a.sum+b.sum,count:a.count+b.count});}
  }
  for(const block of blocks)for(let i=block.start;i<=block.end;i++)rows[i].cy=block.sum/block.count+rows[i].offset+13.5;
 }
 function arrange(entries,{row=44,gap=14,padding=12}={}){
  // A skipped ability column still needs a visible lane. Without these routing
  // slots, a long edge can pass directly behind an unrelated collapsed Item.
  const proxies=new Map(entries.map(item=>[item,{column:item.column,ownHeight:Math.max(row,item.ownHeight||row),children:[]} ])),all=[...proxies.values()];
  for(const item of entries)for(const edge of item.children){
   const route=[];let parent=proxies.get(item);
   for(let column=item.column+1;column<edge.item.column;column++){
    const slot={column,ownHeight:row,children:[]};all.push(slot);route.push(slot);parent.children.push({item:slot});parent=slot;
   }
   parent.children.push({item:proxies.get(edge.item)});edge.route=route;
  }
  const columns=new Map();
  all.forEach((item,index)=>{item.order=index;if(!columns.has(item.column))columns.set(item.column,[]);columns.get(item.column).push(item);});
  // All links point to a later stage. Shared descendants remain one entry.
  // Process final children before every ancestor, without old subtree spacers.
  for(const column of [...columns.keys()].sort((a,b)=>b-a)){
   const rows=columns.get(column);
   for(const item of rows){const centers=item.children.map(edge=>edge.item.cy);item.cy=centers.length?(Math.min(...centers)+Math.max(...centers))/2:13.5;}
   rows.sort((a,b)=>a.cy-b.cy||a.order-b.order);pack(rows,gap);
  }
  const shift=padding-Math.min(...all.map(item=>item.cy-13.5));
  for(const item of all)item.cy+=shift;
  for(const item of entries){item.cy=proxies.get(item).cy;item.span=[item.cy-13.5,item.cy-13.5+Math.max(row,item.ownHeight||row)];}
  return Math.max(...all.map(item=>item.cy-13.5+item.ownHeight));
 }

 return {arrange};
});
