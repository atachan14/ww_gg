const test=require('node:test'),assert=require('node:assert/strict');
const {measure,arrange}=require('../static/tree_layout.js');
function element(id,events,{natural=100,content=100,line=20,corner=null}={}){
 let width=null;const style={};Object.defineProperty(style,'width',{get:()=>width===null?'':width+'px',set:v=>{events.push(['write',id]);width=parseFloat(v);}});
 return {style,getBoundingClientRect(){events.push(['read',id]);const w=width??natural;return {width:w,height:line*Math.ceil(content/w)};},querySelector:()=>corner};
}
function fixture(events){
 const headings=[element('h0',events,{natural:90}),element('h1',events,{natural:100.2})];
 const corner=element('corner',events,{natural:100});
 const rows=[{column:0,element:element('a',events,{natural:120,content:350,corner}),panel:element('panel',events,{natural:240,content:600,line:30}),children:[]},{column:0,element:element('b',events,{natural:80,content:60,line:22}),children:[]},{column:1,element:element('c',events,{natural:160,content:550,line:18}),children:[]},{column:1,element:element('d',events,{natural:260,content:260}),children:[]}];
 return {rows,headings};
}
test('batched measurements retain exact column widths and wrapped card/panel heights',()=>{
 const events=[],{rows,headings}=fixture(events);assert.deepEqual(measure(rows,headings),[240,260]);
 assert.deepEqual(rows.map(x=>x.cardHeight),[40,22,54,20]);assert.deepEqual(rows.map(x=>x.ownHeight),[138,44,54,44]);
 const first=events.findIndex(x=>x[0]==='write'),last=events.findLastIndex(x=>x[0]==='write');
 assert.ok(events.slice(0,first).every(x=>x[0]==='read'));assert.ok(events.slice(first,last+1).every(x=>x[0]==='write'));assert.ok(events.slice(last+1).every(x=>x[0]==='read'));
 arrange([{column:-1,ownHeight:44,children:rows.map(item=>({item}))},...rows]);assert.ok(rows[1].span[0]>=rows[0].span[1]+14);assert.ok(rows[3].span[0]>=rows[2].span[1]+14);
});
test('hundreds of rows keep one write phase and two read phases',()=>{
 const events=[],headings=[element('header',events)],rows=Array.from({length:400},(_,i)=>({column:0,element:element(String(i),events,{natural:80+i%40,content:140+i%100})}));
 measure(rows,headings);const phases=events.reduce((a,x)=>{if(a.at(-1)!==x[0])a.push(x[0]);return a;},[]);
 assert.deepEqual(phases,['read','write','read']);assert.equal(events.filter(x=>x[0]==='write').length,400);assert.equal(events.filter(x=>x[0]==='read').length,801);
});
test('repeat and changed panel size are measured afresh without reordered entries or stale heights',()=>{
 const events=[],{rows,headings}=fixture(events),order=rows.map(x=>x.element);measure(rows,headings);rows[0].panel=element('expanded',events,{natural:240,content:2400,line:30});
 measure(rows,headings);assert.equal(rows[0].ownHeight,348);assert.deepEqual(rows.map(x=>x.element),order);
 rows[0].panel=null;measure(rows,headings);assert.deepEqual(rows.map(x=>x.cardHeight),[40,22,54,20]);assert.equal(rows[0].ownHeight,44);
});
