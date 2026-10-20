'use strict';
(() => {
  const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
  const fraction=x=>{const [a,b=1]=x.split('/').map(Number);return `${x} (${(100*a/b).toFixed(2)}%)`;};
  function mount(root){
    if(root.dataset.treeBound)return;root.dataset.treeBound='1';
    const content=root.querySelector('[data-tree-content]'),status=root.querySelector('[data-tree-status]');
    let snapshot=null;
    async function load(node,expand=false){
      const q=new URLSearchParams();if(node!==null)q.set('node',node);if(snapshot)q.set('snapshot',snapshot);if(expand)q.set('expand','1');
      const response=await fetch('/game-tree?'+q,{headers:{Accept:'application/json'},cache:'no-store'});
      const data=await response.json();if(!response.ok)throw Error(data.error||'評価を取得できませんでした。');
      snapshot=data.snapshot;return data;
    }
    function draw(data){
      const box=el('div',undefined,'calculation-tree-node');box.dataset.treeNode=data.node;
      box.append(el('h3',`${data.day}日目 ${data.phase==='day'?'昼':'夜'}${data.winner?'・'+(data.winner==='village'?'村勝利':'狼勝利'):''}`));
      box.append(el('p',data.viewpoint),el('p',data.policy_basis),el('p',`村勝率 ${fraction(data.village_win)} ／ 狼勝率 ${fraction(data.wolf_win)}`));
      const state=el('p',`終局評価済み${data.reused?'・保存した計算結果を再利用':''} ／ ${data.expansion==='computed'?'枝展開済み':'名前付きの枝は未展開'}`);state.dataset.treeEvaluation=data.evaluation;box.append(state);
      const board=el('details');board.append(el('summary','このBoardを見る'));
      const table=el('table');table.className='tree-board';const head=el('tr');['Player','生存','初期配役の狼率'].forEach(t=>head.append(el('th',t)));table.append(head);
      data.players.forEach(p=>{const tr=el('tr');[String(p.player),p.alive?'生存':'死亡',fraction(p.wolf_probability)].forEach(t=>tr.append(el('td',t)));table.append(tr);});board.append(table);
      board.append(el('p',data.history.length?data.history.map(e=>`${e.day}日目${e.phase==='day'?'処刑':'襲撃'} Player${e.target}`).join(' → '):'初日・行動履歴なし'));
      board.append(el('p',`昼 ${data.policy.day} ／ 夜 ${data.policy.night} ／ 自噛み ${data.rules.allow_self_bite?'あり':'なし'}`));box.append(board);
      if(!data.winner&&data.actions===null){
        const open=el('button','実評価の枝を展開');open.type='button';open.dataset.treeExpand=data.node;box.append(open);
        open.addEventListener('click',async()=>{open.disabled=true;status.textContent='このBoardの実計算を実行しています。';try{const next=await load(data.node,true);box.replaceWith(draw(next));status.textContent='枝を評価しました。各行動を開いて次のBoardへ進めます。';}catch(e){status.textContent=e.message;open.disabled=false;}});
      }
      for(const action of data.actions||[]){
        const detail=el('details',undefined,'tree-action');const summary=el('summary',`${action.label}：村 ${fraction(action.village_win)}${action.selected?' ／ '+(data.mode==='max'?'MAX同点採用':'均等採用')+' '+action.policy_probability:' ／ 非採用'}`);detail.append(summary);
        for(const branch of action.branches){
          const child=el('div',undefined,'tree-branch');child.append(el('p',`${branch.observation} ／ 条件付き確率 ${fraction(branch.probability)}`));
          const inspect=el('button','次のBoardを見る');inspect.type='button';inspect.dataset.treeChild=branch.node;child.append(inspect);detail.append(child);
          inspect.addEventListener('click',async()=>{inspect.disabled=true;try{child.append(draw(await load(branch.node)));inspect.remove();status.textContent='実際に評価した次のBoardです。ゲームの保存盤面は変更していません。';}catch(e){inspect.disabled=false;status.textContent=e.message;}});
        }
        box.append(detail);
      }
      return box;
    }
    root.querySelector('[data-tree-open]').addEventListener('click',async event=>{event.currentTarget.disabled=true;status.textContent='Boardの計算を読み込んでいます。';snapshot=null;try{const data=await load(null);content.replaceChildren(draw(data));status.textContent=data.method;}catch(e){status.textContent=e.message;}finally{event.target.disabled=false;}});
  }
  const initialize=()=>document.querySelectorAll('[data-calculation-tree]').forEach(mount);
  new MutationObserver(initialize).observe(document.documentElement,{childList:true,subtree:true});initialize();
})();
