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
  function exclusive(label,key,values,disabled=false) {const value=key==='model'?model:String(policy[key]??'max');return `<label class="exclusive-field">${label}<select data-exclusive="${key}" ${disabled||seed.finished?'disabled':''}>${values.map(([v,l])=>`<option value="${v}" ${value===v?'selected':''}>${l}</option>`).join('')}</select></label>`;}
  function disclosure(s) {
    if(s==='hunter')return `<label class="exclusive-field">CO後の結果開示<select disabled><option>未対応</option></select></label>`;
    if(!['village','seer','medium'].includes(s))return '';
    const common=s==='village',key=common?'disclosure_common':s+'_disclosure',supported=s!=='seer'||seed.future_available;
    const inherited=policy.disclosure_common==='all'?'すべて':'なし';
    return exclusive('CO後の結果開示',key,[...(common?[]:[['inherit',`共通（${inherited}）`]]),['none','なし'],['all','すべて']],!supported);
  }
  function scope(s) {
    const common=s==='village'||s==='wolfCommon';
    const opts=s==='wolf'&&seed.roles.includes('medium')?['fakeable','co','result']:['fakeable','co'];
    const position=s==='seer'?`<div class="exclusive-field" data-seer-position>占い位置<ol class="strategy-filter-order">${policy.seer_position.map(id=>`<li data-filter="${id}">${id==='unvisited'?'未占い':'均等化'}</li>`).join('')}</ol></div>`:'';
    return `<details class="scope-section" data-disclosure data-scope="${s}"><summary>${labels[s]}${s==='hunter'?'（未対応）':''}</summary><div class="scope-body">${common?exclusive(s==='village'?'処刑位置':'噛み位置',s==='village'?'day':'night',[['max','期待勝率最大化'],['random','均等化']]):''}${s==='wolfCommon'?exclusive('自噛み','include_self_bite',[['false','行わない'],['true','行う']],!seed.allow_self_bite):''}${disclosure(s)}${position}${opts.map(o=>`<section class="option-block"><div class="option-head"><h4>${options[o]}</h4>${button(`data-open="${s}|${o}`,'追加 / 編集',seed.finished)}</div>${rows(s,o).map(r=>chip(s,o,r)).join('')||'<p class="empty-option">未選択</p>'}</section>`).join('')}</div></details>`;
  }
  function renderOuter() {
    const remembered=root.closest('main').dataset.strategyDisclosures;
    const opened = new Set(root.children.length?[...root.querySelectorAll('details[open]')].map(e=>e.dataset.scope||e.dataset.team):JSON.parse(remembered||'[]'));
    const first = !root.children.length && !remembered;
    root.innerHTML=`<div class="evaluation">${exclusive('盤面評価','model',[['group','COグループ方式'],['equal','全配役一様方式']],seed.model_locked)}</div><details class="team-section" data-disclosure data-team="village" ${first||opened.has('village-team')?'open':''}><summary class="village-text">村陣営</summary>${['village',...seed.roles.filter(r=>r!=='wolf')].map(scope).join('')}</details><details class="team-section" data-disclosure data-team="wolf" ${first||opened.has('wolf-team')?'open':''}><summary class="wolf-text">狼陣営</summary>${['wolfCommon','wolf'].map(scope).join('')}</details>`;
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
  root.addEventListener('change',e=>{const key=e.target.dataset.exclusive;if(!key)return;if(key==='model')model=e.target.value;else policy[key]=key==='include_self_bite'?e.target.value==='true':e.target.value;if(key==='disclosure_common')renderOuter();applyOuter();});
  root.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.open){opener=b;const[s,o]=b.dataset.open.split('|');context={s,o};draft={co:clone(co),preview:clone(preview),params:clone(candidateParams),report:policy.fake_reports||'max'};dialog.querySelector('#strategy-dialog-title').textContent=options[o];dialog.querySelector('[data-editor-context]').textContent=(s==='village'?'村共通':s==='wolfCommon'?'狼共通':labels[s]);renderOverlay();dialog.showModal();dialog.querySelector('h2').focus();}else if(b.dataset.outerToggle){const[s,id]=b.dataset.outerToggle.split('|');toggle(s,id);applyOuter();}else if(b.dataset.outerRemove){const[s,id]=b.dataset.outerRemove.split('|');if(supported(id)){remove(s,id);applyOuter();}else{preview[s]=(preview[s]||[]).filter(x=>x!==id);window.strategyPreviews[seed.board_key]={preview:clone(preview),params:clone(candidateParams)};renderOuter();}}});
  function renderOverlay() {
    const {s,o}=context;
    // Preview rows are copied separately so Cancel restores candidate parameter edits.
    const saved=preview;preview=draft.preview;let selected=rows(s,o,draft.co);preview=saved;
    const used=selected.map(r=>r.id),all=selected.some(r=>r.id==='all'&&r.enabled);
    const avail=definitions[o].filter(([id])=>!used.includes(id)&&!(o==='fakeable'&&id===s)&&!(id==='blackX'&&!['village','medium'].includes(s)));
    const fixedOption=o!=='co'||s==='wolf'||s==='wolfCommon';
    function parameter(r) {if(r.id==='dayX'||r.id==='blackX'){const key=s+'|'+r.id;return `<label class="inline-condition">${r.id==='blackX'?'黒を ':''}<input type="number" min="1" max="9" value="${html(draft.params[key]??(r.id==='dayX'?2:1))}" data-preview-param="${key}" aria-label="${r.id==='dayX'?'COの日数':'黒を見つけた人数'}">${r.id==='dayX'?' 日にCO':' 人見つけたらCO'}</label>`;}return html(name(o,r.id));}
    function card(r){const gray=!r.enabled||r.fixed&&!r.report||r.truth;return `<article class="candidate-card ${gray?'inactive-item':''}" data-key="${r.key}"><div class="candidate-head"><span class="item-name">${parameter(r)}</span><span class="source">${r.truth?'真':r.inherited?'村共通から継承':labels[s]}</span></div><div class="candidate-actions">${r.truth||r.fixed?'':r.inherited?button(`data-toggle="${r.id}"`,r.enabled?'無効化':'有効化'):button(`data-remove="${r.id}"`,'削除')}</div>${r.report?`<label class="parameter">報告方針<select data-report><option value="max" ${draft.report==='max'?'selected':''}>期待勝率最大化</option><option value="random" ${draft.report==='random'?'selected':''}>均等化</option></select></label>`:''}</article>`;}
    dialog.querySelector('.overlay-body').innerHTML=`<div class="split-panels"><details class="split-panel" open><summary>選択中</summary><div class="panel-content">${selected.map(card).join('')||'<p class="detail-empty">未選択</p>'}</div></details><details class="split-panel" open><summary>未選択</summary><div class="panel-content">${avail.map(([id])=>{const available=!fixedOption&&supported(id),x=!supported(id)&&o==='co'&&!fixedOption;return `<div class="available-row ${!available||all?'inactive-item':''}"><div class="available-name">${parameter({id})}</div>${button(`data-add="${id}"`,'← 追加',!available&&!x)}</div>`;}).join('')||'<p class="detail-empty">候補なし</p>'}</div></details></div>`;
  }
  dialog.querySelector('.overlay-body').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const{s,o}=context;if(b.dataset.add){const id=b.dataset.add;if(o!=='co'||['wolf','wolfCommon'].includes(s))return;if(supported(id)){if(s==='village'){draft.co.common.push(id);for(const row of Object.values(draft.co.roles))row.local=row.local.filter(x=>x!==id);}else draft.co.roles[s].local.push(id);}else (draft.preview[s]??=[]).push(id);}else if(b.dataset.remove){const id=b.dataset.remove;if(supported(id))remove(s,id,draft.co);else draft.preview[s]=draft.preview[s].filter(x=>x!==id);}else if(b.dataset.toggle)toggle(s,b.dataset.toggle,draft.co);renderOverlay();});
  dialog.querySelector('.overlay-body').addEventListener('input',e=>{if(e.target.dataset.previewParam)draft.params[e.target.dataset.previewParam]=Number(e.target.value);});
  dialog.querySelector('.overlay-body').addEventListener('change',e=>{if(e.target.hasAttribute('data-report'))draft.report=e.target.value;});
  function close(apply) {
    if(apply){if(Object.values(draft.params).some(x=>!Number.isInteger(x)||x<1||x>9)){dialog.querySelector('.overlay-error').textContent='Xは1〜9の整数にしてください。';return;}co=draft.co;preview=draft.preview;candidateParams=draft.params;window.strategyPreviews[seed.board_key]={preview:clone(preview),params:clone(candidateParams)};policy.fake_reports=draft.report;sync();}
    dialog.close();dialog.querySelector('.overlay-error').textContent='';const key=opener.dataset.open;if(apply){renderOuter();root.querySelector(`[data-open="${key}"]`)?.focus();applyOuter();}else opener.focus();draft=null;
  }
  dialog.querySelector('[data-editor-cancel]').addEventListener('click',()=>close(false));
  dialog.querySelector('[data-editor-apply]').addEventListener('click',()=>close(true));
  dialog.addEventListener('cancel',e=>e.preventDefault());
  dialog.addEventListener('keydown',e=>{if(e.key==='Escape')e.preventDefault();});
  renderOuter();sync();
};
