"use strict";
window.initializeParallelLayout=function(){
 const main=document.querySelector('main[data-screen="main"],main[data-screen="result"]');if(!main)return;
 const grid=main.querySelector('.board-layout'),column=main.querySelector('.settings-column'),player=main.querySelector('#player-panel'),info=main.querySelector('#information-panel');
 const footer=main.querySelector('.phase-footer');
 const panes=Array.from(main.querySelectorAll('[data-settings-pane]'));
 const table=player.querySelector('.player-table'),scroll=player.querySelector('.table-scroll');
 scroll.scrollLeft=Number(main.dataset.tableScroll||0);
 function refresh(){
  if(!main.isConnected)return;
  document.querySelector('.page-shell').style.paddingBottom=(footer.getBoundingClientRect().height+(document.querySelector('[data-calculation-tree]')?0:16))+'px';
  const active=panes.find(p=>p.open);grid.classList.toggle('settings-open',!!active);
  if(innerWidth>=1040){const height=info.offsetHeight+14+player.offsetHeight;column.style.maxHeight='none';if(active){const body=active.querySelector('.settings-body');body.style.maxHeight='none';const chrome=column.offsetHeight-body.offsetHeight;body.style.maxHeight=Math.max(80,height-chrome)+'px';}column.style.maxHeight=height+'px';}
  else {column.style.maxHeight='none';panes.forEach(p=>p.querySelector('.settings-body').style.maxHeight='320px');}
  const headers=Array.from(table.tHead.rows[0].cells).filter(c=>!c.hidden);table.style.setProperty('--numeric-columns',headers.length-4);
  table.querySelectorAll('[data-co-details] td').forEach(cell=>cell.colSpan=headers.length);
  table.querySelectorAll('[data-table-results], [data-night-reports] td:last-child, [data-private-results]').forEach(cell=>cell.colSpan=headers.length-2);
  const font=getComputedStyle(table.querySelector('td strong')||table),canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');ctx.font=font.font;
  const numeric=headers.slice(3,-1),minima=numeric.map(h=>Math.ceil(Math.max(41,...Array.from(table.querySelectorAll('tbody tr[data-player]')).map(row=>{const cell=row.cells[h.cellIndex],strong=cell?.querySelector('.probability');const text=cell?.classList.contains('action-rates')?cell.textContent.trim():strong?.textContent;return text?ctx.measureText(text).width+8:0;}))));
  const total=minima.reduce((a,b)=>a+b,0);table.style.setProperty('--numeric-total',total+'px');
  const style=getComputedStyle(table),fixed=['--id-width','--name-width','--status-width','--co-width'].reduce((a,v)=>a+parseFloat(style.getPropertyValue(v)),0),extra=Math.max(0,scroll.clientWidth-fixed-total)/numeric.length;
  numeric.forEach((h,i)=>h.style.width=(minima[i]+extra)+'px');

 }
 const schedule=()=>requestAnimationFrame(refresh);window.refreshParallelLayout=schedule;
 panes.forEach(p=>p.addEventListener('toggle',()=>{if(p.open)panes.forEach(other=>{if(other!==p)other.open=false;});schedule();}));
 main.querySelector('[data-collapse-settings]')?.addEventListener('click',()=>{panes.forEach(p=>p.open=false);schedule();});
 main.querySelectorAll('[data-scroll-to]').forEach(b=>b.addEventListener('click',()=>{
  if(b.dataset.scrollTo!=='page-top'){document.getElementById(b.dataset.scrollTo)?.scrollIntoView({block:'start',behavior:'smooth'});return;}
  // Scroll the page/outer scroll owner, preserving Table and Tree internal pan.
  window.scrollTo({top:0,behavior:'smooth'});
  for(let owner=main;owner&&owner!==document.scrollingElement;owner=owner.parentElement){
   if(owner.scrollHeight>owner.clientHeight&&/auto|scroll/.test(getComputedStyle(owner).overflowY))owner.scrollTo({top:0,behavior:'smooth'});
  }
 }));
 const observer=new ResizeObserver(schedule);observer.observe(info);observer.observe(player);observer.observe(footer);
 const mutations=new MutationObserver(schedule);mutations.observe(main.querySelector('#strategy-editor'),{childList:true,subtree:true});
 window.addEventListener('resize',schedule);
 // Removed Boards must not keep observers or window listeners alive.
 const removed=new MutationObserver(()=>{if(!main.isConnected){observer.disconnect();mutations.disconnect();removed.disconnect();window.removeEventListener('resize',schedule);}});removed.observe(document.body,{childList:true,subtree:true});
 schedule();
};
