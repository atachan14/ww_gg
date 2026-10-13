"use strict";

function updateTargetPreview(root = document, target = null) {
  const preview = root.querySelector('[data-target-preview]');
  if (!preview) return;
  const selected = Array.from(root.querySelectorAll('input[name="target"]')).find(input =>
    !input.disabled && (target === null ? input.checked : input.value === target));
  preview.textContent = `${preview.dataset.actionLabel}：${selected ? `Player${selected.value}` : '未選択'}`;
}

function initializeCOEditor() {
  if(document.querySelector('main[data-hybrid-table]'))return;
  const main = document.querySelector('main[data-screen="main"], main[data-screen="result"]');
  if (!main) return;
  const storageKey = 'ww-gg-co-display';
  let saved = {};
  try { saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}'); } catch (_) {}
  const opened = new Set(JSON.parse(main.dataset.coExpanded || JSON.stringify(saved.game === main.dataset.coGame && Array.isArray(saved.players) ? saved.players : [])));
  const save = () => {
    const players = Array.from(main.querySelectorAll('[data-co-toggle][aria-expanded="true"]')).map(button => button.dataset.coToggle);
    try { sessionStorage.setItem(storageKey, JSON.stringify({game:main.dataset.coGame, players})); } catch (_) {}
  };
  const show = (button, expanded) => {
    button.setAttribute('aria-expanded', String(expanded));
    main.querySelectorAll(`[data-co-details="${button.dataset.coToggle}"]`).forEach(row => row.hidden = !expanded);
    const arrow = button.querySelector('.co-arrow');
    if (arrow) arrow.textContent = expanded ? '▾' : '▸';
    window.refreshParallelLayout?.();
  };
  main.querySelectorAll('[data-co-toggle]').forEach(button => {
    show(button, opened.has(button.dataset.coToggle));
    button.addEventListener('click', () => { show(button, button.getAttribute('aria-expanded') !== 'true'); save(); });
  });
  save();
  main.querySelectorAll('[data-co-add]:not(:disabled)').forEach(button => button.addEventListener('click', () => {
    const picker = main.querySelector(`[data-co-picker="${button.dataset.coAdd}"]`);
    picker.hidden = !picker.hidden;
    if (!picker.hidden) picker.focus();
    window.refreshParallelLayout?.();
  }));
  main.querySelectorAll('[data-co-remove]:not(:disabled)').forEach(button => button.addEventListener('click', () => {
    const select = main.querySelector(`[name="co_${button.dataset.coRemove}"]`);
    select.value = 'latent';
    select.dispatchEvent(new Event('change', {bubbles:true}));
  }));
}

function initializeUI() {
  const formatInputs = document.querySelectorAll('input[name="probability-format"]');
  let probabilityFormat = "percent";
  try {
    if (localStorage.getItem("ww_gg.probability-format") === "fraction") probabilityFormat = "fraction";
  } catch (_) { /* Display still works if browser storage is unavailable. */ }

  function applyProbabilityFormat() {
    document.querySelectorAll(".probability[data-fraction][data-percent]").forEach((element) => {
      element.textContent = probabilityFormat === "fraction" ? element.dataset.fraction : element.dataset.percent;
    });
    formatInputs.forEach((input) => { input.checked = input.value === probabilityFormat; });
    window.refreshParallelLayout?.();
  }

  formatInputs.forEach((input) => {
    input.addEventListener("change", () => {
      probabilityFormat = input.value;
      try { localStorage.setItem("ww_gg.probability-format", probabilityFormat); } catch (_) {}
      applyProbabilityFormat();
    });
  });
  applyProbabilityFormat();


  document.querySelectorAll("form[data-submit-once]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!event.submitter?.formNoValidate && !form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
        return;
      }
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = "true";
      Array.from(form.elements).filter(e=>e.matches('button[type="submit"]')).forEach((button) => {
        button.disabled = true;
      });
    });
  });

  document.querySelectorAll('input[name="target"]').forEach((radio) => {
    radio.addEventListener("click", () => { radio.form.dataset.manualSelection = "true"; });
    radio.addEventListener("change", () => {
      radio.form.dataset.manualSelection = "true";
      updateTargetPreview(document, radio.value);
    });
  });

  updateTargetPreview();

  const presetSeed = document.querySelector('#setup-presets');
  const setupPresets = presetSeed ? JSON.parse(presetSeed.textContent) : null;
  const castPreset = document.querySelector('#cast-preset');
  const rulePreset = document.querySelector('#rule-preset');
  const castInputs = Object.fromEntries(['citizens', 'mediums', 'seers', 'hunters', 'wolves'].map(key => [key, document.querySelector(`input[name="${key}"]`)]));
  const ruleInput = document.querySelector('#allow-self-bite');
  const initialSeerInput=document.querySelector('#first-seer');
  function refreshSetupPresets() {
    if (!setupPresets) return;
    const matches = (presets, values) => Object.entries(presets).find(([, preset]) =>
      Object.entries(preset.values).every(([key, value]) => values[key] === value))?.[0] || 'custom';
    const counts = Object.fromEntries(Object.entries(castInputs).map(([key, input]) => [key, input.value === '' ? null : Number(input.value)]));
    castPreset.value = matches(setupPresets.cast, counts);
    if (document.activeElement !== rulePreset) rulePreset.value = matches(setupPresets.rules, {allow_self_bite: ruleInput.value === '1' ? true : ruleInput.value === '0' ? false : null,initial_seer:initialSeerInput.value});
  }
  if (setupPresets) {
    castPreset.addEventListener('change', () => {
      const preset = setupPresets.cast[castPreset.value];
      if (preset) Object.entries(preset.values).forEach(([key, value]) => { castInputs[key].value = value; });
      updateCast();
    });
    rulePreset.addEventListener('change', () => {
      const preset = setupPresets.rules[rulePreset.value];
      if (preset) {ruleInput.value = preset.values.allow_self_bite ? '1' : '0';initialSeerInput.value=preset.values.initial_seer;}
      refreshSetupPresets();
    });
    rulePreset.addEventListener('blur',refreshSetupPresets);
    ruleInput.addEventListener('change', refreshSetupPresets);
    initialSeerInput.addEventListener('change',refreshSetupPresets);
  }

  const citizens = document.querySelector('#citizen-count');
  const mediums = document.querySelector('#medium-count');
  const wolves = document.querySelector('#wolf-count');
  const seers = document.querySelector('#seer-count');
  const hunters = document.querySelector('#hunter-count');
  function updateCast() {
    refreshSetupPresets();
    const village = Number(citizens.value) + Number(mediums.value) + Number(seers.value) + Number(hunters.value);
    const total = village + Number(wolves.value);
    const experimental = Number(seers.value)>0;
    wolves.max = experimental ? '9' : '4';
    document.querySelector('#villager-count').innerHTML = `${village}<small>人</small>`;
    document.querySelector('#wolf-summary').innerHTML = `${wolves.value}<small>人</small>`;
    document.querySelector('#total-count').innerHTML = `${total}人<small>（最大9人）</small>`;
    const valid = [citizens, mediums, wolves, seers, hunters].every(input => input.value !== "" && Number.isInteger(Number(input.value)) && Number(input.value) >= 0 && input.checkValidity()) && total >= 1 && total <= 9 && (experimental || total <= 2 || Number(wolves.value) >= 1 && Number(wolves.value) < village);
    const validation = document.querySelector('#cast-validation');
    validation.textContent = valid ? '' : experimental ? '合計1～9人、各役職0～9人の配役にしてください。' : '合計1～9人。3人以上では狼より村陣営が多い配役にしてください。';
    validation.hidden = valid;
    document.querySelector('form[action$="/start"] button[type="submit"]').disabled = !valid;
    const mediumSettings=document.querySelector('[data-medium-calculation]');
    if (mediumSettings) mediumSettings.hidden = Number(mediums.value) === 0;
    document.querySelectorAll('[data-role-calculation]').forEach(e=>e.hidden=Number(e.dataset.roleCalculation==='seers'?seers.value:hunters.value)===0);
  }
  if (citizens && mediums && wolves) {
    for (const input of [citizens, mediums, wolves, seers, hunters]) input.addEventListener('input', updateCast);
    document.querySelector('#seer-mode')?.addEventListener('change', updateCast);
    updateCast();
  }
  const permission = document.querySelector('#allow-self-bite');
  const inclusion = document.querySelector('#include-self-bite');
  if (permission && inclusion) permission.addEventListener('change', () => {
    const permitted = permission.type === "checkbox" ? permission.checked : permission.value === "1";
    inclusion.disabled = !permitted;
    if (!permitted) inclusion.value = "0";
  });

  const breakdown = document.querySelector('.role-breakdown-toggle');
  if (breakdown) {
    const main = document.querySelector('main');
    const cells = Array.from(document.querySelectorAll('[data-role-detail]'));
    cells.forEach((cell,index) => cell.id = `role-detail-${index}`);
    breakdown.setAttribute('aria-controls', cells.map(cell => cell.id).join(' '));
    const apply = () => {
      const expanded = main.dataset.roleDetails !== 'false';
      breakdown.setAttribute('aria-expanded', String(expanded));
      breakdown.querySelector('[data-breakdown-arrow]').textContent = expanded ? '▾' : '▸';
      document.querySelectorAll('[data-role-detail]').forEach(cell => cell.hidden = !expanded);
      const option=document.querySelector('#display-role-details');if(option) option.checked=expanded;
      window.refreshParallelLayout?.();
    };
    breakdown.addEventListener('click', () => {
      main.dataset.roleDetails = breakdown.getAttribute('aria-expanded') === 'true' ? 'false' : 'true';
      apply();
    });
    const option=document.querySelector('#display-role-details');
    option?.addEventListener('change',()=>{main.dataset.roleDetails=String(option.checked);apply();});
    apply();
  }

  initializeCOEditor();
  window.initializeStrategyEditor?.();
  window.initializeParallelLayout?.();
  initializeLiveClaims();
  initializePublicLog();
  window.initializeBoardTable?.();
}

function initializeLiveClaims() {
  const form = document.querySelector('#action-form');
  if (!form || (!document.querySelector('#strategy-editor') && !document.querySelector('.co-select:not(:disabled), .report-select:not(:disabled)'))) return;
  let running = false;
  let pending = false;
  let version = 0;
  let blocked = false;
  form.addEventListener('submit', event => {
    if (blocked) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  const status = document.createElement('p');
  status.className = 'hint';
  status.setAttribute('role', 'status');
  document.querySelector('#information-panel').append(status);
  const disableProgress = () => {
    blocked = true;
    document.querySelectorAll('#advance-button, #strategy-button, #back-button,[data-table-co],[data-table-details] select,[data-table-update],[data-table-cancel],[data-public-open],[data-public-edit],[data-public-delete]').forEach(b => b.disabled = true);
    document.querySelectorAll('.probability').forEach(p => {
      p.textContent = '—';
      delete p.dataset.fraction;
      delete p.dataset.percent;
    });
    document.querySelectorAll('input[name="probability-format"]').forEach(p => p.disabled = true);
  };
  const update = async () => {
    pending = true;
    version += 1;
    disableProgress();
    status.className = 'hint';
    status.setAttribute('role', 'status');
    status.textContent = '再計算しています。Phaseは進めません。';
    if (running) return;
    running = true;
    while (pending) {
      pending = false;
      const sentVersion = version;
      try {
        const response = await fetch(document.querySelector('#strategy-button').formAction, {
          method: 'POST', body: (() => { const data = new FormData(form); if (form.dataset.manualSelection !== 'true') data.delete('target'); return data; })(), credentials: 'same-origin',
          headers: {'Accept': 'text/html'}
        });
        const html = new DOMParser().parseFromString(await response.text(), 'text/html');
        const revision = html.querySelector('#action-form input[name="revision"]');
        if (!revision) throw new Error('画面を再読込してから入力してください。');
        document.querySelectorAll('input[name="revision"]').forEach(input => input.value = revision.value);
        if (sentVersion !== version) continue;
        if (!response.ok) {
          status.className = 'error';
          status.setAttribute('role', 'alert');
          status.textContent = html.querySelector('[role="alert"]')?.textContent || 'COを確認してください。';
          // Keep the edited claims and target; old results remain hidden.
          continue;
        }
        const main = html.querySelector('main');
        if (!main || main.dataset.screen !== 'main') throw new Error('画面を再読込してから入力してください。');
        const selected = form.dataset.manualSelection === 'true' ? form.querySelector('input[name="target"]:checked')?.value : null;
        if (selected) {
          main.querySelector("#action-form").dataset.manualSelection = "true";
          main.querySelectorAll('input[name="target"]').forEach(input => input.checked = input.value === selected);
          updateTargetPreview(main, selected);
        }
        main.dataset.coExpanded=JSON.stringify(Array.from(document.querySelectorAll('[data-co-toggle][aria-expanded="true"]')).map(button=>button.dataset.coToggle));
        main.dataset.strategyDisclosures=JSON.stringify(Array.from(document.querySelectorAll('#strategy-editor details[open]')).map(e=>e.dataset.scope));
        document.querySelectorAll('[data-settings-pane]').forEach(e=>{main.querySelector(`[data-settings-pane="${e.dataset.settingsPane}"]`).open=e.open;});
        const scroll=document.querySelector('#player-panel .table-scroll');main.dataset.tableScroll=String(scroll.scrollLeft);
        document.querySelectorAll('details[data-disclosure]').forEach((details, index) => {
          const replacement = main.querySelectorAll('details[data-disclosure]')[index];
          if (replacement) replacement.open = details.open;
        });
        main.dataset.roleDetails = document.querySelector('main').dataset.roleDetails || 'true';
        document.querySelector('main').replaceWith(main);
        initializeUI();
      } catch (error) {
        if (sentVersion === version) {
          status.className = 'error';
          status.setAttribute('role', 'alert');
          status.textContent = '再計算できませんでした。「再計算」で再試行するか、画面を再読込してください。';
        }
      }
    }
    running = false;
    if (form.isConnected) document.querySelector('#strategy-button').disabled = false;
  };
  form.querySelectorAll('.co-select:not(:disabled), .report-select:not(:disabled), #day-strategy:not(:disabled), #night-strategy:not(:disabled), #include-self-bite:not(:disabled), #fake-reports:not(:disabled), .co-conditions input[type=checkbox]:not(:disabled)').forEach(input => {
    input.addEventListener('change', update);
  });
  form.addEventListener('strategychange', update);
  document.querySelector('#strategy-button').addEventListener('click', event => {
    event.preventDefault();
    update();
  });
}

initializeUI();

window.addEventListener("pageshow", (event) => {
  if (event.persisted) window.location.reload();
});

function initializePublicLog() {
  const seedNode=document.querySelector('#public-log-seed');if(!seedNode)return;
  const seed=JSON.parse(seedNode.textContent),root=document.querySelector('#system-log'),dialog=root.querySelector('#board-log-dialog');
  const rows=root.querySelector('[data-public-rows]'),status=root.querySelector('[data-public-status]'),editor=root.querySelector('[data-public-editor]'),picker=root.querySelector('[data-legacy-picker]'),mode=root.querySelector('[data-public-mode]');
  const labels={villager:'市民',seer:'占い師',medium:'霊能',hunter:'狩人',wolf:'狼'};
  let disabledStates=new Map();
  let saved=seed.draft?.revision===seed.revision&&seed.draft.board_id===seed.board_id?seed.draft.payload:null,editing=null,legacyKey=null,busy=false,navigating=false,contextDay=seed.day,contextPhase=seed.phase,returnFocus=null;
  document.querySelector('#public-log-draft-form').addEventListener('submit',event=>event.preventDefault());
  document.addEventListener('board-table-dirty',()=>{saved=null;});
  function field(row,key,labelText,values,value='') {
    const label=document.createElement('label');label.textContent=labelText;
    const select=document.createElement('select');select.dataset.publicField=key;select.setAttribute('form','public-log-draft-form');
    for(const [v,text] of values){const option=document.createElement('option');option.value=v;option.textContent=text;select.append(option);}
    if(value!==''&&!values.some(v=>String(v[0])===String(value))){const option=document.createElement('option');option.value=value;option.textContent='不正な値';select.append(option);}
    select.value=value??'';label.append(select);row.append(label);return select;
  }
  function playersAvailable(){return editing===null?seed.alive:Array.from({length:seed.players},(_,i)=>i+1).filter(p=>!seed.targets.slice(0,seed.log.batches.find(b=>b.id===editing)?.slot??0).includes(p));}
  function refreshTargets(row,selected=null) {
    const get=k=>row.querySelector(`[data-public-field=${k}]`),kind=get('result').value,player=Number(get('player').value),day=Number(get('day').value),target=get('target'),old=selected??target.value;
    const scan=Array.from({length:seed.players},(_,i)=>i+1).filter(p=>!seed.targets.slice(0,Math.max(0,2*(day-1)-1)).includes(p)&&p!==player);
    let eligible=kind==='medium'?(day>1&&seed.targets[2*day-4]?[seed.targets[2*day-4]]:[]):scan;
    if(legacyKey)eligible=kind==='medium'?[legacyKey.target]:scan;
    target.replaceChildren();for(const [value,text] of [['','未選択'],...Array.from(new Set(eligible)).map(p=>[p,`Player${p}`])]){const option=document.createElement('option');option.value=value;option.textContent=text;target.append(option);}
    if(old!==''&&!eligible.includes(Number(old))){const option=document.createElement('option');option.value=old;option.textContent=`Player${old}（確認）`;target.append(option);}
    target.value=old;
    for(const key of ['day','target','color'])get(key).parentElement.hidden=kind==='';
  }
  function refreshPlayers(){root.querySelector('[data-public-add]').disabled=busy||!!legacyKey||rows.children.length>=27;}
  function addRow(data={}) {
    const row=document.createElement('div');row.className='board-log-draft-row';row.dataset.publicRow='';
    const actor=field(row,'player','Player',[['','未選択'],...playersAvailable().map(p=>[p,`Player${p}`])],data.player||'');
    field(row,'role','CO',[['','変更しない'],...seed.roles.map(r=>[r,labels[r]])],data.role??'').title='CO撤回は未対応';
    const result=field(row,'result','結果',[['','追加しない'],...(seed.roles.includes('seer')?[['seer','占い結果']]:[]),...(seed.roles.includes('medium')?[['medium','霊能結果']]:[])],data.result??'');
    const day=field(row,'day','取得日',[[contextDay,`Day${contextDay}`]],data.day??contextDay);day.disabled=true;day.title='取得日と公開日は同じ昼のみ';
    field(row,'target','対象',[['','未選択']],data.target||'');field(row,'color','白黒',[['','未選択'],['white','白'],['black','黒']],data.color??'');
    if(legacyKey)result.disabled=true;
    const remove=document.createElement('button');remove.type='button';remove.className='board-log-row-remove';remove.textContent='×';remove.setAttribute('aria-label','この行を削除');remove.addEventListener('click',()=>{row.remove();refreshPlayers();});row.append(remove);
    if(legacyKey){actor.disabled=true;result.disabled=true;row.querySelector('[data-public-field=role]').disabled=true;remove.disabled=true;}
    day.addEventListener('change',()=>refreshTargets(row));actor.addEventListener('change',()=>{refreshTargets(row);refreshPlayers();});result.addEventListener('change',()=>refreshTargets(row));rows.append(row);refreshTargets(row,data.target||'');refreshPlayers();
  }
  function load(payload) {
    editing=payload?.replace??null;legacyKey=payload?.legacy?.key??null;
    const batch=seed.log.batches.find(b=>b.id===editing);contextDay=legacyKey?.day??batch?.day??seed.day;contextPhase=batch?.phase??seed.phase;mode.value=payload?.mode??batch?.mode??'single';
    rows.replaceChildren();picker.hidden=true;editor.hidden=false;status.textContent='';
    const events=legacyKey?[payload.legacy.event]:payload?.events??[];const grouped=[];
    for(const e of events){let row=e.kind==='co'&&e.player<1?null:grouped.findLast(r=>r.player===e.player&&(e.kind==='co'?!r.coSeen:!r.result));if(!row){row={player:e.player};grouped.push(row);}if(e.kind==='co'){row.role=e.role;row.coSeen=true;}else Object.assign(row,{result:e.kind,day:e.day,target:e.target,color:e.color});}
    (grouped.length?grouped:[{}]).forEach(addRow);
    root.querySelector('#board-log-dialog-title').textContent=legacyKey?'旧結果を訂正':editing===null?'公開を追加':`Day${contextDay}の公開を訂正`;
    root.querySelector('[data-public-confirm]').hidden=false;root.querySelector('[data-public-save]').hidden=false;
  }
  function payload(forDraft=false) {
    const events=[],seen=new Set();
    for(const row of rows.children){const get=k=>row.querySelector(`[data-public-field=${k}]`).value,player=Number(get('player')),role=get('role'),kind=get('result');
      if(!forDraft&&player<1)throw Error('Playerを選んでください。');
      if(role)events.push({kind:'co',player,role});
      if(kind){if(forDraft&&!role&&player<1)events.push({kind:'co',player,role:''});events.push({kind,player,day:Number(get('day')),target:Number(get('target')),color:get('color')});}
      if(!role&&!kind){if(!forDraft)throw Error('COまたは結果を追加してください。');events.push({kind:'co',player,role:''});}
    }
    for(const e of events){if(forDraft&&(e.player<1||e.kind==='co'&&!e.role))continue;const key=e.kind==='co'?`co-${e.player}`:`${e.kind}-${e.day}-${e.player}-${e.kind==='medium'?e.target:''}`;if(seen.has(key))throw Error('同じCO・結果が重複しています。');seen.add(key);}
    if(!forDraft&&!events.length)throw Error('Playerの行を追加してください。');
    if(events.length>27)throw Error('一度の公開は27件以内にしてください。');
    if(!forDraft&&events.some(e=>e.kind!=='co'&&(!e.target||!e.color)))throw Error('結果の対象と白黒を揃えてください。');
    if(legacyKey)return {legacy:{key:legacyKey,event:events.find(e=>e.kind!=='co')}};
    const batchMode=events.length>1?'simultaneous':mode.value;return {mode:batchMode,events,...(editing===null?{}:{replace:editing})};
  }
  function open(payload=null){if(busy)return;returnFocus=document.activeElement;load(payload);dialog.showModal();rows.querySelector('select:not(:disabled)')?.focus();}
  function close(){if(busy)return;dialog.close();status.textContent='';returnFocus?.focus();}
  async function send(operation,p) {
    if(busy)return;busy=true;disabledStates=new Map(Array.from(root.querySelectorAll('button,input,select')).map(e=>[e,e.disabled]));for(const e of disabledStates.keys())e.disabled=true;
    try{const response=await fetch('/public-log',{method:'POST',body:new URLSearchParams({revision:String(seed.revision),board_id:seed.board_id,operation,payload:JSON.stringify(p)})});const data=await response.json().catch(()=>({error:'保存できませんでした。入力を確認してください。'}));if(!response.ok)throw Error(data.error);
      if(operation==='publish'){navigating=true;location.reload();return;}
      saved=p;busy=false;dialog.close();returnFocus?.focus();
    }catch(error){if(!dialog.open){dialog.showModal();}status.textContent=error.message;}
    finally{if(!navigating){busy=false;for(const [e,disabled] of disabledStates)e.disabled=disabled;refreshPlayers();if(seed.finished)root.querySelector('[data-public-open]').disabled=true;}}
  }
  root.querySelector('[data-public-open]').addEventListener('click',()=>open(saved));
  root.querySelector('[data-public-add]').addEventListener('click',()=>addRow());
  root.querySelectorAll('[data-public-close],[data-public-cancel]').forEach(b=>b.addEventListener('click',close));
  root.querySelector('[data-public-save]').addEventListener('click',()=>{try{send('draft',payload(true));}catch(e){status.textContent=e.message;}});
  root.querySelector('[data-public-confirm]').addEventListener('click',()=>{try{send('publish',payload());}catch(e){status.textContent=e.message;}});
  root.querySelectorAll('[data-public-edit]').forEach(b=>b.addEventListener('click',()=>{const batch=seed.log.batches.find(x=>x.id===Number(b.dataset.publicEdit));open({mode:batch.mode,events:batch.events,replace:batch.id});}));
  root.querySelectorAll('[data-public-delete]').forEach(b=>b.addEventListener('click',()=>{const batch=seed.log.batches.find(x=>x.id===Number(b.dataset.publicDelete));load({mode:batch.mode,events:batch.events,replace:batch.id});send('publish',{delete:batch.id});}));
  root.querySelectorAll('[data-legacy-open]').forEach(button=>button.addEventListener('click',()=>{returnFocus=button;editing=null;legacyKey=null;status.textContent='';editor.hidden=true;picker.hidden=false;picker.replaceChildren();root.querySelector('#board-log-dialog-title').textContent='旧結果';
    for(const kind of ['seer','medium'])for(const r of seed.log[kind==='seer'?'base_seer':'base_medium']){const line=document.createElement('div');line.className='board-log-legacy-choice';const text=document.createElement('span');text.textContent=`Player${r.reporter} / Day${r.day} / ${kind==='seer'?'占い':'霊能'}:Player${r.target??'?' }=${r.color==='white'?'白':r.color==='black'?'黒':'未完了'}`;line.append(text);const key={kind,player:r.reporter,day:r.day,target:r.target};const edit=document.createElement('button');edit.type='button';edit.textContent='訂正';edit.dataset.legacyEdit='';edit.addEventListener('click',()=>{load({legacy:{key,event:{...key,color:r.color}}});rows.querySelector('select:not(:disabled)')?.focus();});line.append(edit);const remove=document.createElement('button');remove.type='button';remove.textContent='削除';remove.dataset.legacyDelete='';remove.addEventListener('click',()=>send('publish',{delete_legacy:{key}}));line.append(remove);picker.append(line);}
    const note=document.createElement('p');note.className='hint';note.textContent='旧COの削除・撤回は未対応です。';picker.append(note);root.querySelector('[data-public-confirm]').hidden=true;root.querySelector('[data-public-save]').hidden=true;dialog.showModal();
  }));
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  let outside=false;dialog.addEventListener('pointerdown',event=>{const r=dialog.getBoundingClientRect();outside=event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom;});dialog.addEventListener('click',event=>{const r=dialog.getBoundingClientRect();if(outside&&(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom))close();outside=false;});
  // No editor controls are mounted in the permanent log. Restore drafts on open.
}
