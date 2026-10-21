"use strict";
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.TreeViewport=factory();})(typeof globalThis==='object'?globalThis:this,()=>{
 const MIN=.5,MAX=2.5;
 function zoomAt(view,point,delta){const scale=Math.min(MAX,Math.max(MIN,view.scale*Math.exp(-delta*.002))),ratio=scale/view.scale;return {scale,left:(view.left+point.x)*ratio-point.x,top:(view.top+point.y)*ratio-point.y};}
 function wheelDelta(event,height){if(event.ctrlKey||event.metaKey)return null;const delta=event.deltaY||event.deltaX||0;return delta?delta*(event.deltaMode===1?16:event.deltaMode===2?height:1):null;}
 return {MIN,MAX,zoomAt,wheelDelta,areaHeight:(viewport,footer)=>Math.max(0,viewport-footer)};
});
