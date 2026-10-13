/* Mount private navigation without writing public forms, cookies or logs. */
(() => {
 window.initializeBoardPrivateTable=()=>{
  const seedNode=document.querySelector('#board-viewpoint-seed');
  if(!seedNode||seedNode.dataset.initialized)return;
  seedNode.dataset.initialized='true';
  const root=seedNode.closest('main'),seed=JSON.parse(seedNode.textContent),table=root.querySelector('.player-table');
  const status=root.querySelector('[data-viewpoint-status]');
  const scope=root.querySelector('[data-table-scope]'),publicScope=scope?.textContent;
  let storage=null;try{storage=window.sessionStorage;}catch(_){}
  const store=window.createBoardPrivateDraftStore({boardId:seed.board_id,revision:seed.revision,storage,scopeRevision:false});
  const cells=[...table.querySelectorAll('[data-value-cell]')],original=new Map(cells.map(c=>[c,c.innerHTML]));
  const headers=new Map(['dawn','final'].map(key=>{
   const cell=table.querySelector(`[data-value-cell="${key}"]`);
   const header=table.tHead.rows[0].cells[cell.cellIndex];return[header,header.innerHTML];
  }));
  const pending=message=>{for(const cell of cells){cell.textContent=message;cell.removeAttribute('title');}};
  const restore=()=>{
   table.querySelectorAll('[data-private-details]').forEach(row=>row.remove());
   original.forEach((html,cell)=>{cell.innerHTML=html;cell.removeAttribute('title');});
   headers.forEach((html,cell)=>{cell.innerHTML=html;});status.textContent='';if(scope)scope.textContent=publicScope;
   window.refreshParallelLayout?.();
  };
  const probability=(value)=>{
   const node=document.createElement('strong');node.className='probability';
   const [n,d='1']=value.split('/');const percent=String(Math.round(Number(n)/Number(d)*10000)/100)+'%';
   node.dataset.fraction=value;node.dataset.percent=percent;
   let fraction=false;try{fraction=localStorage.getItem('ww_gg.probability-format')==='fraction';}catch(_){}
   node.textContent=fraction?value:percent;return node;
  };
  const heading=()=>{
   for(const kind of ['dawn','final']){
    const cell=table.querySelector(`[data-value-cell="${kind}"]`);
    if(cell)table.tHead.rows[0].cells[cell.cellIndex].textContent=kind==='dawn'?'能力使用時・次の朝まで 村 / 狼':'能力使用時・最終 村 / 狼';
   }
  };
  let controller;
  const mountSecret=(role,player)=>{
   const draft=store.open({player,role,claims:[seed.claims[player-1]],publicResults:seed.public_results});
   if(!table.querySelector(`[data-private-details="${player}:${role}"]`)){
    const row=window.renderBoardPrivateRow({table,player,role,label:role==='seer'?'占い師':'狩人',
     slots:role==='seer'?seed.slots[String(player)]:[],draft,onChange:edit=>{store.edit(edit);controller.refresh();}});
    if(role==='hunter')row.querySelector('[data-private-results]').textContent='護衛履歴の入力・能力計算は未対応です。';
   }
   return draft.results;
  };
  root.addEventListener('viewpointchange',event=>{
   const {mode,role,selected}=event.detail;
   if(mode==='public')return;
   if(scope)scope.textContent=`${seed.roles[role].label}（公開情報＋秘密情報）`;
   heading();
   if(mode==='selecting'){
    pending('選択中');status.textContent=`${seed.roles[role].label}：行をクリックして ${seed.roles[role].required}人選択してください。死亡済みの狼仲間も選択できます。`;
   }else if(mode==='loading'){
    pending('計算中');status.textContent='私的情報で再計算中です。BoardOverviewの勝率は公開情報の計算です。';
   }
  });
  controller=window.createBoardViewpointController({root,roles:seed.roles,restore,
   load:async({role,players,signal})=>{
    const results=role==='wolf'?[]:mountSecret(role,players[0]);
    const response=await fetch('/private-view',{method:'POST',signal,body:new URLSearchParams({
     revision:String(seed.revision),board_id:seed.board_id,payload:JSON.stringify({role,players,results})})});
    const result=await response.json();if(!response.ok)throw Error(result.error);
    if(result.board_id!==seed.board_id||result.revision!==seed.revision)throw Error('Boardが変更されています。再読み込みしてください。');
    return result;
   },
   show:result=>{
    for(const player of result.players){
     const row=table.querySelector(`tr[data-player="${player.id}"]`);
     for(const cell of row.querySelectorAll('[data-value-cell]')){
      const key=cell.dataset.valueCell;cell.replaceChildren();
      if(key in player.probabilities)cell.append(probability(player.probabilities[key]));
      else if(player[key])cell.append(probability(player[key].village),' / ',probability(player[key].wolf));
      else{cell.textContent=controller.getState().role==='wolf'&&!player.legal?'—':'未対応';cell.title=result.reason;}
     }
    }
    status.textContent=`${result.reason} ${controller.getState().role==='wolf'?'能力先の比較用です。':'秘密欄だけ編集できます。'} 公開CO・公開ログは変更しません。BoardOverviewは公開情報の勝率です。`;
    window.refreshParallelLayout?.();
   },
   onError:error=>{pending('不整合');status.textContent=`不整合：${error.message} 秘密欄を修正するか「全体」で戻ってください。`;}
  });
  root.boardViewpointController=controller;root.boardPrivateDraftStore=store;
 };
 document.addEventListener('DOMContentLoaded',window.initializeBoardPrivateTable);
})();
