"use strict";
window.initializeParallelLayout=function(){
 const main=document.querySelector('main[data-screen="main"],main[data-screen="result"]');if(!main)return;
 const grid=main.querySelector('.board-layout'),column=main.querySelector('.settings-column'),player=main.querySelector('#player-panel'),info=main.querySelector('#information-panel');
 const panes=Array.from(main.querySelectorAll('[data-settings-pane]'));
 const table=player.querySelector('.player-table'),scroll=player.querySelector('.table-scroll');
 scroll.scrollLeft=Number(main.dataset.tableScroll||0);
 function refresh(){
  if(!main.isConnected)return;
  const active=panes.find(p=>p.open);grid.classList.toggle('settings-open',!!active);
  if(innerWidth>=1040){const height=info.offsetHeight+14+player.offsetHeight;column.style.maxHeight='none';if(active){const body=active.querySelector('.settings-body');body.style.maxHeight='none';const chrome=column.offsetHeight-body.offsetHeight;body.style.maxHeight=Math.max(80,height-chrome)+'px';}column.style.maxHeight=height+'px';}
  else {column.style.maxHeight='none';panes.forEach(p=>p.querySelector('.settings-body').style.maxHeight='320px');}
  const headers=Array.from(table.tHead.rows[0].cells).filter(c=>!c.hidden);table.style.setProperty('--numeric-columns',headers.length-5);
  const font=getComputedStyle(table.querySelector('td strong')),canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');ctx.font=font.font;
  const numeric=headers.slice(4,-1),minima=numeric.map(h=>Math.ceil(Math.max(41,...Array.from(table.tBodies[0].rows).map(row=>{const strong=row.cells[h.cellIndex]?.querySelector('.probability');return strong?ctx.measureText(strong.textContent).width+4:0;}))));
  const total=minima.reduce((a,b)=>a+b,0);table.style.setProperty('--numeric-total',total+'px');
  const style=getComputedStyle(table),fixed=['--id-width','--name-width','--status-width','--co-width','--target-width'].reduce((a,v)=>a+parseFloat(style.getPropertyValue(v)),0),extra=Math.max(0,scroll.clientWidth-fixed-total)/numeric.length;
  numeric.forEach((h,i)=>h.style.width=(minima[i]+extra)+'px');

 }
 const schedule=()=>requestAnimationFrame(refresh);window.refreshParallelLayout=schedule;
 panes.forEach(p=>p.addEventListener('toggle',()=>{if(p.open)panes.forEach(other=>{if(other!==p)other.open=false;});schedule();}));
 main.querySelector('[data-collapse-settings]').addEventListener('click',()=>{panes.forEach(p=>p.open=false);schedule();});
 main.querySelectorAll('[data-scroll-to]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.scrollTo)?.scrollIntoView({block:'start',behavior:'smooth'})));
 const observer=new ResizeObserver(schedule);observer.observe(info);observer.observe(player);
 const mutations=new MutationObserver(schedule);mutations.observe(main.querySelector('#strategy-editor'),{childList:true,subtree:true});
 window.addEventListener('resize',schedule);
 // Removed Boards must not keep observers or window listeners alive.
 const removed=new MutationObserver(()=>{if(!main.isConnected){observer.disconnect();mutations.disconnect();removed.disconnect();window.removeEventListener('resize',schedule);}});removed.observe(document.body,{childList:true,subtree:true});
 schedule();
};
