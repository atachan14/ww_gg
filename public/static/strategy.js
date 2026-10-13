"use strict";
window.initializeStrategyEditor = function () {
  const root = document.querySelector('#strategy-editor');
  if (!root) return;
  const seed = JSON.parse(root.dataset.seed), form = root.closest('form'), dialog = form.querySelector('.strategy-dialog');
  const clone = v => JSON.parse(JSON.stringify(v));
  let co = clone(seed.co), policy = {disclosure_common:'all',seer_disclosure:'inherit',medium_disclosure:'inherit',seer_position:['unvisited','uniform'],...clone(seed.policy)}, model = seed.model, context, draft, opener;
  const labels = {village:'共通',wolfCommon:'共通',villager:'市民',medium:'霊能者',seer:'占い師',hunter:'狩人',wolf:'狼'};
  const options = {fakeable:'騙れる役職',co:'COのお約束',result:'可能な結果騙り'};
  const definitions = {fakeable:[['all','すべて'],...seed.roles.map(r=>[r,labels[r]])],co:[['filled','対抗が埋まったらCCO'],['counter','対抗が出たらCCO'],['dayX','X日にCO'],['blackX','黒をX人見つけたらCO']],result:[['all','すべて'],['white','白と報告'],['black','黒と報告']]};
  // Gray X parameters are a local preview, never serialized to a calculation policy.
  window.strategyPreviews ??= {};
  const savedPreview = window.strategyPreviews[seed.board_key] || {};
  let preview = clone(savedPreview.preview||{}), candidateParams = clone(savedPreview.params||{});
  const name = (o,id) => definitions[o].find(x=>x[0]===id)?.[1] || id;
  const parent = s => s==='wolf'?'wolfCommon':seed.roles.includes(s)?'village':null;
  const supported = id => ['filled','counter'].includes(id);
  const html = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const button = (attr,text,disabled=false) => `<button type="button" ${attr} ${disabled?'disabled':''}>${text}</button>`;
  function rows(s,o,c=co) {
    if (o==='co') {
      const common = c.common.map(id=>({id,key:'i:'+id,inherited:true,source:'village',enabled:!c.roles[s]?.disabled.includes(id)}));
      const local = (s==='village'?c.common:c.roles[s]?.local||[]).map(id=>({id,key:'l:'+id,source:s,enabled:true}));
      return (s==='village'?local:s==='wolf'||s==='wolfCommon'?[]:common.concat(local)).concat((preview[s]||[]).map(id=>({id,key:'p:'+id,source:s,enabled:false,preview:true})));
    }
    if (o==='fakeable' && seed.roles.includes(s)) return [{id:s,key:'truth',source:s,truth:true,enabled:true},...(s==='wolf'?[{id:'all',key:'fixed',source:s,enabled:true,fixed:true}]:[])];

    if (o==='result' && s==='wolf' && seed.roles.includes('medium')) return [{id:'all',key:'fixed',source:s,enabled:true,fixed:true,report:true}];
    return [];
  }
  const inactive = r => !r.enabled;
  function chip(s,o,r) { return `<div class="item-chip ${inactive(r)?'off':''}" data-strategy-inactive="${inactive(r)}"><span class="chip-title">${html(r.id==='dayX'?(candidateParams[s+'|'+r.id]??2)+' 日にCO':r.id==='blackX'?'黒を '+(candidateParams[s+'|'+r.id]??1)+' 人見つけたらCO':name(o,r.id))}</span>${r.truth?'<span class="source truth">真</span>':`<span class="source">${r.source==='village'?'村共通':labels[r.source]}</span>`}${r.fixed||r.truth?'':r.inherited?button(`data-outer-toggle="${s}|${r.id}"`,r.enabled?'無効化':'有効化',seed.finished):button(`data-outer-remove="${s}|${r.id}"`,'×',seed.finished)}</div>`; }
  function modelSelector() {
    return `<label class="exclusive-field">盤面評価<select data-exclusive="model" ${seed.model_locked||seed.finished?'disabled':''}><option value="group" ${model==='group'?'selected':''}>COグループ方式</option><option value="equal" ${model==='equal'?'selected':''}>全配役一様方式</option></select></label>`;
  }
  function itemSpec(s,o) {
    const scalar=(title,key,candidates,ordered=false,disabled=false)=>({title,key,candidates,ordered,disabled,min:1,max:1,values:[String(key==='model'?model:policy[key]??'max')],supported:candidates.map(([id])=>id)});
    if(o==='position'&&['village','wolfCommon'].includes(s))return scalar(s==='village'?'処刑位置':'噛み位置',s==='village'?'day':'night',[['max','期待勝率最大化'],['random','均等化']],true);
    if(o==='position'&&s==='seer')return {title:'占い位置',key:'seer_position',ordered:true,min:2,max:2,fixed:true,values:clone(policy.seer_position),candidates:[['unvisited','未占い'],['uniform','均等化']],supported:['unvisited','uniform']};
    if(o==='selfbite')return scalar('自噛み','include_self_bite',[['false','行わない'],['true','行う']],false,!seed.allow_self_bite);
    if(o==='report')return scalar('結果騙りの報告方針','fake_reports',[['max','期待勝率最大化'],['random','均等化']]);
    if(o!=='disclose')return null;
    if(!['village','seer','medium','hunter'].includes(s))return null;
    const key=s==='village'?'disclosure_common':s+'_disclosure';
    return {title:'CO後の結果開示',key,ordered:false,min:1,max:1,
      disabled:s==='hunter'||s==='seer'&&!seed.future_available,
      values:s==='hunter'?['unsupported']:[String(policy[key])],
      candidates:[...(s==='village'?[]:[['inherit',`共通（${policy.disclosure_common==='all'?'すべて':'なし'}）`]]),['none','なし'],['all','すべて'],['white','白結果を開示'],['black','黒結果を開示']],
      supported:['inherit','none','all']};
  }
  function itemBlock(s,o) {
    const spec=itemSpec(s,o);if(!spec)return '';
    const label=id=>spec.candidates.find(x=>x[0]===id)?.[1]||'未対応';
    return `<section class="option-block" data-item-mode="${spec.ordered?'ordered':'unordered'}"><div class="option-head"><h4>${spec.title}</h4>${button(`data-open="${s}|${o}"`,'追加 / 編集',seed.finished||spec.disabled)}</div><div class="strategy-items ${spec.ordered?'ordered-items':''}">${spec.values.map((id,i)=>`<div class="item-chip ${spec.disabled?'off':''}">${spec.ordered?`<span class="item-order">${i+1}</span>`:''}<span class="chip-title">${html(label(id))}</span></div>`).join('')}</div></section>`;
  }
  function itemPanels(ordered,selected,available) {
    return `<div class="split-panels" data-item-mode="${ordered?'ordered':'unordered'}"><details class="split-panel" open><summary>選択中</summary><div class="panel-content">${selected||'<p class="detail-empty">未選択</p>'}</div></details><details class="split-panel" open><summary>未選択</summary><div class="panel-content">${available||'<p class="detail-empty">候補なし</p>'}</div></details></div>`;
  }
  function renderPolicyItems() {
    const spec=itemSpec(context.s,context.o),selected=draft.items;
    const label=id=>spec.candidates.find(x=>x[0]===id)?.[1]||id;
    const cards=selected.map((id,i)=>`<article class="candidate-card"><div class="candidate-head">${spec.ordered?`<span class="item-order">${i+1}</span>`:''}<span>${html(label(id))}</span></div><div class="candidate-actions">${spec.ordered?button(`data-item-up="${id}" aria-label="${html(label(id))}を上へ"`,'↑',spec.fixed||i===0)+button(`data-item-down="${id}" aria-label="${html(label(id))}を下へ"`,'↓',spec.fixed||i===selected.length-1):''}${button(`data-item-remove="${id}"`,'削除',spec.fixed)}</div></article>`).join('');
    const available=spec.candidates.filter(([id])=>!selected.includes(id)).map(([id,label])=>`<div class="available-row ${spec.supported.includes(id)?'':'inactive-item'}"><span>${html(label)}</span>${button(`data-item-add="${id}"`,'← 追加',spec.fixed||selected.length>=spec.max||!spec.supported.includes(id))}</div>`).join('');
    dialog.querySelector('.overlay-body').innerHTML=itemPanels(spec.ordered,cards,available);
  }
  function scope(s) {
    const common=s==='village'||s==='wolfCommon';
    const opts=s==='wolf'&&seed.roles.includes('medium')?['fakeable','co','result']:['fakeable','co'];
    return `<details class="scope-section" data-disclosure data-scope="${s}"><summary>${labels[s]}${s==='hunter'?'（未対応）':''}</summary><div class="scope-body">${itemBlock(s,'position')}${s==='wolfCommon'?itemBlock(s,'selfbite'):''}${itemBlock(s,'disclose')}${s==='wolf'&&seed.roles.includes('medium')?itemBlock(s,'report'):''}${opts.map(o=>`<section class="option-block" data-item-mode="unordered"><div class="option-head"><h4>${options[o]}</h4>${button(`data-open="${s}|${o}"`,'追加 / 編集',seed.finished)}</div>${rows(s,o).map(r=>chip(s,o,r)).join('')||'<p class="empty-option">未選択</p>'}</section>`).join('')}</div></details>`;
  }
  function renderOuter() {
    const remembered=root.closest('main').dataset.strategyDisclosures;
    const opened = new Set(root.children.length?[...root.querySelectorAll('details[open]')].map(e=>e.dataset.scope||e.dataset.team):JSON.parse(remembered||'[]'));
    const first = !root.children.length && !remembered;
    root.innerHTML=`<div class="evaluation">${modelSelector()}</div><details class="team-section" data-disclosure data-team="village" ${first||opened.has('village-team')?'open':''}><summary class="village-text">村陣営</summary>${['village',...seed.roles.filter(r=>r!=='wolf')].map(scope).join('')}</details><details class="team-section" data-disclosure data-team="wolf" ${first||opened.has('wolf-team')?'open':''}><summary class="wolf-text">狼陣営</summary>${['wolfCommon','wolf'].map(scope).join('')}</details>`;
    root.querySelectorAll('[data-scope]').forEach(e=>e.open=opened.has(e.dataset.scope));
    // Keep the team keys distinct from the wolf role.
    root.querySelectorAll('[data-team]').forEach(e=>{e.dataset.scope=e.dataset.team+'-team';if(!first)e.open=opened.has(e.dataset.scope);});
  }
  function sync() {
    for (const [key,value] of Object.entries({model,day:policy.day,night:policy.night,include_self_bite:policy.include_self_bite?'1':'0',fake_reports:policy.fake_reports||'max',disclosure_common:policy.disclosure_common,seer_disclosure:policy.seer_disclosure,medium_disclosure:policy.medium_disclosure,seer_position:JSON.stringify(policy.seer_position),strategy_ui:JSON.stringify(co)})) form.querySelector(`[name="${key}"]`).value=value;
  }
  function applyOuter() { sync(); form.dispatchEvent(new Event('strategychange')); }
  function remove(s,id,c=co) {if(s==='village'){c.common=c.common.filter(x=>x!==id);Object.values(c.roles).forEach(r=>r.disabled=r.disabled.filter(x=>x!==id));}else c.roles[s].local=c.roles[s].local.filter(x=>x!==id);}
  function toggle(s,id,c=co) {const row=c.roles[s];row.disabled=row.disabled.includes(id)?row.disabled.filter(x=>x!==id):[...row.disabled,id];}
  root.addEventListener('change',e=>{if(e.target.dataset.exclusive==='model'&&!seed.model_locked&&!seed.finished){model=e.target.value;applyOuter();}});
  root.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.open){opener=b;const[s,o]=b.dataset.open.split('|');context={s,o};const spec=itemSpec(s,o);draft={items:spec?clone(spec.values):null,co:clone(co),preview:clone(preview),params:clone(candidateParams),report:policy.fake_reports||'max'};dialog.querySelector('#strategy-dialog-title').textContent=spec?.title||options[o];dialog.querySelector('[data-editor-context]').textContent=(s==='village'?'村共通':s==='wolfCommon'?'狼共通':labels[s]||'共通');renderOverlay();dialog.showModal();dialog.querySelector('h2').focus();}else if(b.dataset.outerToggle){const[s,id]=b.dataset.outerToggle.split('|');toggle(s,id);applyOuter();}else if(b.dataset.outerRemove){const[s,id]=b.dataset.outerRemove.split('|');if(supported(id)){remove(s,id);applyOuter();}else{preview[s]=(preview[s]||[]).filter(x=>x!==id);window.strategyPreviews[seed.board_key]={preview:clone(preview),params:clone(candidateParams)};renderOuter();}}});
  function renderOverlay() {
    if(itemSpec(context.s,context.o)){renderPolicyItems();return;}
    const {s,o}=context;
    // Preview rows are copied separately so Cancel restores candidate parameter edits.
    const saved=preview;preview=draft.preview;let selected=rows(s,o,draft.co);preview=saved;
    const used=selected.map(r=>r.id),all=selected.some(r=>r.id==='all'&&r.enabled);
    const avail=definitions[o].filter(([id])=>!used.includes(id)&&!(o==='fakeable'&&id===s)&&!(id==='blackX'&&!['village','medium'].includes(s)));
    const fixedOption=o!=='co'||s==='wolf'||s==='wolfCommon';
    function parameter(r) {if(r.id==='dayX'||r.id==='blackX'){const key=s+'|'+r.id;return `<label class="inline-condition">${r.id==='blackX'?'黒を ':''}<input type="number" min="1" max="9" value="${html(draft.params[key]??(r.id==='dayX'?2:1))}" data-preview-param="${key}" aria-label="${r.id==='dayX'?'COの日数':'黒を見つけた人数'}">${r.id==='dayX'?' 日にCO':' 人見つけたらCO'}</label>`;}return html(name(o,r.id));}
    function card(r){const gray=!r.enabled||r.fixed&&!r.report||r.truth;return `<article class="candidate-card ${gray?'inactive-item':''}" data-key="${r.key}"><div class="candidate-head"><span class="item-name">${parameter(r)}</span><span class="source">${r.truth?'真':r.inherited?'村共通から継承':labels[s]}</span></div><div class="candidate-actions">${r.truth||r.fixed?'':r.inherited?button(`data-toggle="${r.id}"`,r.enabled?'無効化':'有効化'):button(`data-remove="${r.id}"`,'削除')}</div></article>`;}
    const available=avail.map(([id])=>{const available=!fixedOption&&supported(id),x=!supported(id)&&o==='co'&&!fixedOption;return `<div class="available-row ${!available||all?'inactive-item':''}"><div class="available-name">${parameter({id})}</div>${button(`data-add="${id}"`,'← 追加',!available&&!x)}</div>`;}).join('');
    dialog.querySelector('.overlay-body').innerHTML=itemPanels(false,selected.map(card).join(''),available);
  }
  dialog.querySelector('.overlay-body').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const{s,o}=context;const spec=itemSpec(s,o);if(spec){if(spec.disabled||spec.fixed)return;if(b.dataset.itemUp||b.dataset.itemDown){const index=draft.items.indexOf(b.dataset.itemUp||b.dataset.itemDown),next=index+(b.dataset.itemUp?-1:1);if(spec.ordered&&index>=0&&next>=0&&next<draft.items.length)[draft.items[index],draft.items[next]]=[draft.items[next],draft.items[index]];}else if(b.dataset.itemRemove)draft.items=draft.items.filter(id=>id!==b.dataset.itemRemove);else if(b.dataset.itemAdd&&spec.supported.includes(b.dataset.itemAdd)&&draft.items.length<spec.max&&!draft.items.includes(b.dataset.itemAdd))draft.items.push(b.dataset.itemAdd);renderOverlay();return;}if(b.dataset.add){const id=b.dataset.add;if(o!=='co'||['wolf','wolfCommon'].includes(s))return;if(supported(id)){if(s==='village'){draft.co.common.push(id);for(const row of Object.values(draft.co.roles))row.local=row.local.filter(x=>x!==id);}else draft.co.roles[s].local.push(id);}else (draft.preview[s]??=[]).push(id);}else if(b.dataset.remove){const id=b.dataset.remove;if(supported(id))remove(s,id,draft.co);else draft.preview[s]=draft.preview[s].filter(x=>x!==id);}else if(b.dataset.toggle)toggle(s,b.dataset.toggle,draft.co);renderOverlay();});
  dialog.querySelector('.overlay-body').addEventListener('input',e=>{if(e.target.dataset.previewParam)draft.params[e.target.dataset.previewParam]=Number(e.target.value);});
  function close(apply) {
    if(apply){
      const spec=itemSpec(context.s,context.o);
      if(spec&&(draft.items.length<spec.min||draft.items.length>spec.max||draft.items.some(id=>!spec.supported.includes(id))||new Set(draft.items).size!==draft.items.length||spec.fixed&&JSON.stringify(draft.items)!==JSON.stringify(spec.values))){dialog.querySelector('.overlay-error').textContent=spec.max===1?'項目を1つ選択してください。':'対応している順序・項目を選択してください。';return;}
      if(Object.values(draft.params).some(x=>!Number.isInteger(x)||x<1||x>9)){dialog.querySelector('.overlay-error').textContent='Xは1〜9の整数にしてください。';return;}
      if(spec){policy[spec.key]=spec.key==='include_self_bite'?draft.items[0]==='true':spec.key==='seer_position'?clone(draft.items):draft.items[0];}
      co=draft.co;preview=draft.preview;candidateParams=draft.params;window.strategyPreviews[seed.board_key]={preview:clone(preview),params:clone(candidateParams)};sync();
    }
    dialog.close();dialog.querySelector('.overlay-error').textContent='';const key=opener.dataset.open;if(apply){renderOuter();root.querySelector(`[data-open="${key}"]`)?.focus();applyOuter();}else opener.focus();draft=null;
  }
  dialog.querySelector('[data-editor-cancel]').addEventListener('click',()=>close(false));
  dialog.querySelector('[data-editor-apply]').addEventListener('click',()=>close(true));
  dialog.addEventListener('cancel',e=>e.preventDefault());
  dialog.addEventListener('keydown',e=>{if(e.key==='Escape')e.preventDefault();});
  renderOuter();sync();
};
