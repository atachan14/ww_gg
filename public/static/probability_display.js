"use strict";
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.ProbabilityDisplay=factory();})(typeof globalThis==='object'?globalThis:this,()=>{
 const formats=value=>{const [n,d='1']=String(value).split('/');return {fraction:String(value),percent:String(Math.round(Number(n)/Number(d)*10000)/100)+'%'};};
 const text=(value,mode)=>formats(value)[mode==='fraction'?'fraction':'percent'];
 return {formats,text};
});
