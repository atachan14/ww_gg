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
  const columns=new Map();
  entries.forEach((item,index)=>{item.order=index;item.ownHeight=Math.max(row,item.ownHeight||row);if(!columns.has(item.column))columns.set(item.column,[]);columns.get(item.column).push(item);});
  // All links point to a later stage. A shared descendant is a single entry,
  // not a repeated subtree reservation. No old centers or spans are reused.
  for(const column of [...columns.keys()].sort((a,b)=>b-a)){
   const rows=columns.get(column);
   for(const item of rows){const centers=item.children.map(edge=>edge.item.cy);item.cy=centers.length?(Math.min(...centers)+Math.max(...centers))/2:13.5;}
   rows.sort((a,b)=>a.cy-b.cy||a.order-b.order);pack(rows,gap);
  }
  const shift=padding-Math.min(...entries.map(item=>item.cy-13.5));
  for(const item of entries){item.cy+=shift;item.span=[item.cy-13.5,item.cy-13.5+item.ownHeight];}
  return Math.max(...entries.map(item=>item.span[1]));
 }
 return {arrange};
});
