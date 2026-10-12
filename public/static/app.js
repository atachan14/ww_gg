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
  function refreshSetupPresets() {
    if (!setupPresets) return;
    const matches = (presets, values) => Object.entries(presets).find(([, preset]) =>
      Object.entries(preset.values).every(([key, value]) => values[key] === value))?.[0] || 'custom';
    const counts = Object.fromEntries(Object.entries(castInputs).map(([key, input]) => [key, input.value === '' ? null : Number(input.value)]));
    castPreset.value = matches(setupPresets.cast, counts);
    rulePreset.value = matches(setupPresets.rules, {allow_self_bite: ruleInput.value === '1' ? true : ruleInput.value === '0' ? false : null});
  }
  if (setupPresets) {
    castPreset.addEventListener('change', () => {
      const preset = setupPresets.cast[castPreset.value];
      if (preset) Object.entries(preset.values).forEach(([key, value]) => { castInputs[key].value = value; });
      updateCast();
    });
    rulePreset.addEventListener('change', () => {
      const preset = setupPresets.rules[rulePreset.value];
      if (preset) ruleInput.value = preset.values.allow_self_bite ? '1' : '0';
      refreshSetupPresets();
    });
    ruleInput.addEventListener('change', refreshSetupPresets);
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
    document.querySelector('#villager-count').innerHTML = `${village}<small>人</small>`;
    document.querySelector('#wolf-summary').innerHTML = `${wolves.value}<small>人</small>`;
    document.querySelector('#total-count').innerHTML = `${total}人<small>（最大9人）</small>`;
    const valid = [citizens, mediums, wolves, seers, hunters].every(input => input.value !== "" && Number.isInteger(Number(input.value)) && Number(input.value) >= 0 && input.checkValidity()) && total >= 1 && total <= 9 && (total <= 2 || Number(wolves.value) >= 1 && Number(wolves.value) < village);
    const validation = document.querySelector('#cast-validation');
    validation.textContent = valid ? '' : '合計1〜9人。3人以上では狼より村陣営が多い配役にしてください。';
    validation.hidden = valid;
    document.querySelector('form[action$="/start"] button[type="submit"]').disabled = !valid;
    const mediumSettings=document.querySelector('[data-medium-calculation]');
    if (mediumSettings) mediumSettings.hidden = Number(mediums.value) === 0;
    document.querySelectorAll('[data-role-calculation]').forEach(e=>e.hidden=Number(e.dataset.roleCalculation==='seers'?seers.value:hunters.value)===0);
  }
  if (citizens && mediums && wolves) {
    for (const input of [citizens, mediums, wolves, seers, hunters]) input.addEventListener('input', updateCast);
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
