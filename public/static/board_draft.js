/* Shared public-declaration draft; does not mutate committed model or acquisitions. */
(() => {
  const copy = value => JSON.parse(JSON.stringify(value));
  const canonical = value => {
    if (Array.isArray(value)) return value.map(canonical);
    if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
    return value;
  };
  const signature = value => JSON.stringify(canonical(value));
  window.createBoardDeclarationDraft = (committed, controls = {}) => {
    let base = copy(committed), current = copy(committed), busy = false;
    const blocked = Array.from(controls.conflictingButtons || []);
    const original = new Map(blocked.map(button => [button, button.disabled]));
    const listeners = new Set();
    const dirty = () => signature(base) !== signature(current);
    const refresh = () => {
      const changed = dirty();
      if (controls.update) { controls.update.disabled = busy || !changed; controls.update.classList.toggle('primary', changed); }
      if (controls.cancel) { controls.cancel.hidden = !changed; controls.cancel.disabled = busy; }
      blocked.forEach(button => { button.dataset.draftBlocked = String(changed || busy); button.disabled = original.get(button) || changed || busy || button.dataset.noTarget === 'true'; });
      listeners.forEach(listener => listener({ dirty: changed, busy }));
    };
    const api = {
      snapshot: () => copy(current), committed: () => copy(base), isDirty: dirty,
      edit: next => { if (busy) throw Error('Draft submission in progress'); current = copy(next); refresh(); },
      cancel: () => { if (busy) return; current = copy(base); refresh(); },
      onChange: listener => { listeners.add(listener); return () => listeners.delete(listener); },
      submit: async publish => {
        if (busy || !dirty()) return false;
        busy = true; refresh();
        try {
          // Caller builds one validated atomic event batch; no private-ledger writes here.
          const accepted = await publish(copy(current), copy(base));
          if (!accepted) throw Error('Publication did not confirm committed state');
          base = copy(accepted); current = copy(accepted); return true;
        } finally { busy = false; refresh(); }
      }
    };
    if (controls.cancel) controls.cancel.addEventListener('click', api.cancel);
    refresh(); return api;
  };
})();
