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

 // Keep at least 26px clear after the 22px collapsed arrow before a track. Only the
 // first trunk of siblings from the same source can share a vertical track.
 function wiring(entries,columnCount){
  const gaps=Array.from({length:columnCount},()=>[]),edges=[],incoming=new Map();
  for(const from of entries)for(const edge of from.children){const connection={from,to:edge.item,probability:edge.probability,original:edge,route:[from,...edge.route,edge.item],tracks:[]};edges.push(connection);if(!incoming.has(edge.item))incoming.set(edge.item,[]);incoming.get(edge.item).push(connection);
   for(let i=0;i<connection.route.length-1;i++){const column=connection.route[i].column,key=i===0?from:connection;let track=gaps[column].indexOf(key);if(track<0){track=gaps[column].length;gaps[column].push(key);}connection.tracks.push(track);}
  }
  const labelWidth=p=>Math.max(12,String(p).length*6+4),reserve=Math.max(32,...edges.map(e=>labelWidth(e.probability)+16));
  const widths=gaps.map(tracks=>48+Math.max(1,tracks.length)*12+reserve);
  function draw(offsets,columns){
   const stubs=entries.filter(n=>n.closedContinuation).map(n=>({from:n,points:[[n.x+n.width,n.cy],[n.x+n.width+22,n.cy]]})),labels=[];
   for(const edge of edges){edge.route=[edge.from,...edge.original.route,edge.to];const points=[[edge.from.x+edge.from.width,edge.from.cy]],peers=incoming.get(edge.to),port=peers.length>1?(peers.indexOf(edge)/(peers.length-1)-.5)*16:0;
    for(let i=0;i<edge.route.length-1;i++){const a=edge.route[i],b=edge.route[i+1],column=a.column,x=offsets[column]+columns[column],track=x+48+edge.tracks[i]*12,y=i===edge.route.length-2?b.cy+port:b.cy;
     points.push([track,points.at(-1)[1]],[track,y],[offsets[b.column],y]);if(i<edge.route.length-2)points.push([offsets[b.column]+columns[b.column],y]);
    }
    edge.points=points.filter((p,i)=>!i||p[0]!==points[i-1][0]||p[1]!==points[i-1][1]);
   }
   // Prefer labels near their destination, after the split, and avoid other
   // wires and labels. Dense convergences can use earlier free segments.
   const segments=points=>points.slice(1).map((p,i)=>({a:points[i],b:p}));
   const intersects=(r,s)=>{const [a,b]=[s.a,s.b];return a[0]===b[0]?a[0]>r.x&&a[0]<r.x+r.width&&Math.max(a[1],b[1])>r.y&&Math.min(a[1],b[1])<r.y+r.height:a[1]>r.y&&a[1]<r.y+r.height&&Math.max(a[0],b[0])>r.x&&Math.min(a[0],b[0])<r.x+r.width;};
   const rectangles=entries.map(n=>({x:n.x-2,y:n.cy-15.5,width:n.width+4,height:n.ownHeight+4}));
   for(const edge of edges){if(edge.probability===null)continue;const width=labelWidth(edge.probability),candidates=[];
    for(const segment of segments(edge.points).reverse()){const [a,b]=[segment.a,segment.b];if(a[1]!==b[1]||b[0]-a[0]<width+4)continue;for(const y of [a[1]-18,a[1]+4])candidates.push({x:b[0]-width-2,y,width,height:14});}
    const obstacles=edges.filter(e=>e!==edge).flatMap(e=>segments(e.points)).concat(stubs.flatMap(s=>segments(s.points)));
    edge.label=candidates.find(r=>!rectangles.concat(labels).some(b=>r.x<b.x+b.width&&r.x+r.width>b.x&&r.y<b.y+b.height&&r.y+r.height>b.y)&&!obstacles.some(s=>intersects(r,s)))||candidates.at(-1);
    if(edge.label)labels.push(edge.label);
   }
   return {edges,stubs};
  }
  return {widths,draw};
 }
 return {arrange,wiring};
});
