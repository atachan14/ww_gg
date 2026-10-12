"use strict";

function updateTargetPreview(root = document, target = null) {
  const preview = root.querySelector('[data-target-preview]');
  if (!preview) return;
  const selected = Array.from(root.querySelectorAll('input[name="target"]')).find(input =>
    !input.disabled && (target === null ? input.checked : input.value === target));
  preview.textContent = `${preview.dataset.actionLabel}：${selected ? `Player${selected.value}` : '未選択'}`;
}

function initializeCOEditor() {
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
    document.querySelectorAll(".probability").forEach((element) => {
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
}

function initializeLiveClaims() {
  const form = document.querySelector('#action-form');
  if (!form || !document.querySelector('.co-select:not(:disabled), .report-select:not(:disabled)')) return;
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
    document.querySelectorAll('#advance-button, #strategy-button, #back-button').forEach(b => b.disabled = true);
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
 const seed=JSON.parse(seedNode.textContent),root=document.querySelector('#system-log');
 const rows=root.querySelector('[data-public-rows]'),mode=root.querySelector('[data-public-mode]'),status=root.querySelector('[data-public-status]');
 let replacing=null,legacyKey=null,busy=false;
 document.querySelector('#public-log-draft-form').addEventListener('submit',event=>event.preventDefault());
 const option=(value,label)=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;};
 function field(row,key,values,value){const label=document.createElement('label');label.textContent={kind:'種類',player:'発言者',role:'CO',day:'取得日',target:'対象',color:'結果'}[key];const select=document.createElement('select');select.dataset.publicField=key;select.setAttribute('form','public-log-draft-form');values.forEach(v=>select.append(option(v[0],v[1])));select.value=value??'';label.append(select);row.append(label);return select;}
 function add(e={}){const row=document.createElement('div');row.className='public-draft-row';row.dataset.publicRow='';
 const kind=field(row,'kind',[['co','CO'],['seer','占い結果'],['medium','霊能結果']],e.kind||'co');
 field(row,'player',[['','未選択'],...Array.from({length:seed.players},(_,i)=>[i+1,`Player ${i+1}`])],e.player);
 field(row,'role',[['','未選択'],...seed.roles.map(r=>[r,{villager:'市民',seer:'占い師',medium:'霊能',hunter:'狩人',wolf:'狼'}[r]])],e.role);
 field(row,'day',Array.from({length:seed.day},(_,i)=>[i+1,`Day ${i+1}`]),e.day||seed.day);
 field(row,'target',[['','未選択'],...Array.from({length:seed.players},(_,i)=>[i+1,`Player ${i+1}`])],e.target);
 field(row,'color',[['','未選択'],['white','白'],['black','黒']],e.color);
 const refresh=()=>{row.querySelector('[data-public-field=role]').parentElement.hidden=kind.value!=='co';['day','target','color'].forEach(k=>row.querySelector(`[data-public-field=${k}]`).parentElement.hidden=kind.value==='co');};kind.addEventListener('change',refresh);refresh();
 const remove=document.createElement('button');remove.type='button';remove.textContent='行を削除';remove.addEventListener('click',()=>{row.remove();});row.append(remove);rows.append(row);}
 function payload(){const p={mode:mode.value,events:Array.from(rows.children).map(row=>{const get=k=>row.querySelector(`[data-public-field=${k}]`).value;const e={kind:get('kind'),player:Number(get('player'))};return e.kind==='co'?{...e,role:get('role')}:{...e,day:Number(get('day')),target:Number(get('target')),color:get('color')};}),...(replacing===null?{}:{replace:replacing})};return legacyKey?{legacy:{key:legacyKey,event:p.events[0]}}:p;}
 function load(p){legacyKey=p?.legacy?.key??null;if(legacyKey)p={mode:'single',events:[p.legacy.event]};rows.replaceChildren();mode.value=p?.mode||'single';replacing=p?.replace??null;(p?.events||[{}]).forEach(add);root.querySelector('[data-public-edit-label]').textContent=replacing===null?'新規公開':`バッチ #${replacing} の訂正（公開位置を維持）`;}
 async function send(operation,p){if(busy)return;busy=true;root.querySelectorAll('button').forEach(b=>b.disabled=true);try{const body=new URLSearchParams({revision:String(seed.revision),operation,payload:JSON.stringify(p)});const r=await fetch('/public-log',{method:'POST',body});const data=await r.json().catch(()=>({error:'保存容量を超えたか、応答が確認できません。'}));if(!r.ok)throw Error(data.error);if(operation==='publish'){location.reload();return;}status.textContent=operation==='draft'?'下書きを保存しました。計算は変わりません。':'下書きを取り消しました。';if(operation==='cancel')load(null);}catch(e){status.textContent=e.message;}finally{busy=false;root.querySelectorAll('button').forEach(b=>b.disabled=false);}}
 root.querySelector('[data-public-add]').addEventListener('click',()=>{if(legacyKey){status.textContent='旧結果の訂正は一件ずつ行います。';return;}mode.value='simultaneous';add();});
 root.querySelector('[data-public-save]').addEventListener('click',()=>send('draft',payload()));
 root.querySelector('[data-public-cancel]').addEventListener('click',()=>send('cancel',{}));
 root.querySelector('[data-public-confirm]').addEventListener('click',()=>send('publish',payload()));
 root.querySelectorAll('[data-public-edit]').forEach(b=>b.addEventListener('click',()=>{const batch=seed.log.batches.find(x=>x.id===Number(b.dataset.publicEdit));load({mode:batch.mode,events:batch.events,replace:batch.id});}));
 root.querySelectorAll('[data-public-delete]').forEach(b=>b.addEventListener('click',()=>{status.textContent='依存する結果が残る削除は拒否されます。';send('publish',{delete:Number(b.dataset.publicDelete)});}));
 root.querySelectorAll('[data-legacy-edit]').forEach(b=>b.addEventListener('click',()=>{const e=JSON.parse(b.dataset.legacyEdit);load({legacy:{key:{kind:e.kind,player:e.player,day:e.day,target:e.target},event:e}});status.textContent='旧結果の訂正です。新たな公開順は作りません。';}));
 root.querySelectorAll('[data-legacy-delete]').forEach(b=>b.addEventListener('click',()=>send('publish',{delete_legacy:{key:JSON.parse(b.dataset.legacyDelete)}})));
 load(seed.draft?.revision===seed.revision?seed.draft.payload:null);
}
