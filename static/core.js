"use strict";
// v0.8 screen. The server is stateless; games, boards and results live in IndexedDB (docs/redesign/tree.md).
(() => {
 const defaults = JSON.parse(document.getElementById('strategy-defaults').textContent);
 const app = document.getElementById('app');
 const ROLE = {villager: '市民', seer: '占い師', medium: '霊能', wolf: '人狼'};
 const COLOR = {white: '白', black: '黒'};
 const SEER_STAGE = {undetermined: '未確定', unseen: '未占い', latent: '潜伏', half_white: '片白', uniform: '均等'};
 const FAKE_STAGE = {no_contradiction: '破綻しない報告', uniform: '均等'};
 const STRATEGY = () => ({wolf_claims: ['seer', 'medium'], co_on_saturation: true, co_on_black: true, disclose_black: true,
  disclose_all: true, seer_target: [...defaults.seer_target], fake_report: [...defaults.fake_report], bite: 'max', execution: 'max'});

 let db = null, game = null, flash = '', inflight = null, calculating = null, draft = {}, editingStrategy = null;
 let fractions = false;
 try { fractions = localStorage.getItem('ww_gg.core.fractions') === '1'; } catch (_) {}

 // --- small helpers -----------------------------------------------------------
 function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
   if (key === 'class') node.className = value;
   else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
   else if (key in node) node[key] = value;
   else node.setAttribute(key, value);
  }
  node.append(...children.flat().filter(child => child !== null && child !== undefined && child !== false));
  return node;
 }
 function fraction(text) { const [n, d = '1'] = String(text).split('/'); return Number(n) / Number(d); }
 function show(text) {
  if (text === undefined || text === null) return '—';
  return fractions ? String(text) : (Math.round(fraction(text) * 10000) / 100) + '%';
 }
 const players = () => game.cast.villager + game.cast.seer + game.cast.medium + game.cast.wolf;
 const P = n => 'P' + n;
 const nodeOf = id => game.nodes[id];
 const current = () => nodeOf(game.current);

 function eventLabel(event) {
  if (event.kind === 'exec') return '処刑 ' + P(event.player);
  if (event.kind === 'bite') return '噛み ' + P(event.player);
  if (!event.acts.length) return '更新なし';
  return event.acts.map(act => act.kind === 'co' ? `${P(act.player)} ${ROLE[act.role]}CO`
   : `${P(act.player)}→${P(act.target)} ${COLOR[act.color]}`).join('、');
 }
 const actKey = act => act.kind === 'co' ? `co:${act.player}:${act.role}` : `report:${act.player}:${act.target}:${act.color}`;
 const eventKey = event => event.kind === 'col' ? 'col:' + event.acts.map(actKey).sort().join(',') : `${event.kind}:${event.player}`;
 function dayOf(log) { return 1 + log.filter(event => event.kind === 'bite').length; }
 function phaseLabel(log) {
  const last = log[log.length - 1];
  return `Day ${dayOf(log)} ${last && last.kind === 'exec' ? '夜' : '昼'}`;
 }
 function publicState(log) {
  const alive = new Set(Array.from({length: players()}, (_, i) => i + 1)), claims = {}, reports = {};
  for (const event of log) {
   if (event.kind === 'col') for (const act of event.acts) {
    if (act.kind === 'co') claims[act.player] = act.role;
    else (reports[act.player] ||= []).push(act);
   } else alive.delete(event.player);
  }
  return {alive, claims, reports};
 }
 const sameStrategy = (a, b) => JSON.stringify(a) === JSON.stringify(b);

 // --- storage -----------------------------------------------------------------
 function openDb() {
  return new Promise((resolve, reject) => {
   const request = indexedDB.open('wwgg-core-v08', 1);
   request.onupgradeneeded = () => request.result.createObjectStore('games', {keyPath: 'id'});
   request.onsuccess = () => resolve(request.result);
   request.onerror = () => reject(request.error);
   request.onblocked = () => reject(Error('保存先が使えません'));
  });
 }
 function store(mode, work) {
  return new Promise((resolve, reject) => {
   const tx = db.transaction('games', mode), request = work(tx.objectStore('games'));
   tx.oncomplete = () => resolve(request.result);
   tx.onerror = () => reject(tx.error);
   tx.onabort = () => reject(tx.error);
  });
 }
 function save() {
  if (!db || !game) return Promise.resolve();
  const copy = JSON.parse(JSON.stringify(game));
  return store('readwrite', games => games.put(copy)).catch(error => { flash = '履歴を保存できません: ' + error.message; render(); });
 }

 // --- calculation -------------------------------------------------------------
 function cancelInflight() {
  calculating = null;
  if (!inflight) return;
  inflight.controller.abort();
  const form = new URLSearchParams({calculation_id: inflight.token});
  fetch('/calculation-cancel', {method: 'POST', body: form}).catch(() => {});
  inflight = null;
 }
 function newToken() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
 }
 async function request(node, scope) {
  const token = newToken(), controller = new AbortController();
  inflight = {token, controller, node: node.id};
  const response = await fetch('/core/board' + (scope === 'read' ? '?scope=read' : ''), {
   method: 'POST', signal: controller.signal,
   headers: {'Content-Type': 'application/json', 'X-WW-Calculation-ID': token},
   body: JSON.stringify({cast: game.cast, rules: game.rules, strategy: node.strategy, log: node.log})});
  const data = await response.json().catch(() => ({error: '応答を読めません'}));
  if (inflight && inflight.token === token) inflight = null;
  return {status: response.status, data};
 }
 async function calculate(node) {
  cancelInflight();
  node.failure = null;
  calculating = node.id;
  render();
  try {
   if (!node.read) {
    const read = await request(node, 'read');
    if (game.current !== node.id) return;
    if (read.status !== 200) return failed(node, read);
    node.read = read.data;
    save();
    render();
   }
   const full = await request(node, 'full');
   if (game.current !== node.id) return;
   if (full.status !== 200) return failed(node, full);
   node.result = full.data;
   node.village = full.data.win_rates.village;
   calculating = null;
   save();
   render();
  } catch (error) {
   if (error.name === 'AbortError') return;
   calculating = null;
   node.failure = {kind: 'network', message: '通信できません: ' + error.message};
   render();
  }
 }
 function failed(node, {status, data}) {
  if (status === 499) return;
  calculating = null;
  if (status === 422) node.failure = {kind: 'contradiction', message: '盤面が戦略と矛盾しています(役職の候補が残りません)。'};
  else if (status === 503) node.failure = {kind: 'pending', message: '未計算: 時間か作業量の上限に達しました。'};
  else node.failure = {kind: 'invalid', message: data.error || '計算できません'};
  save();
  render();
 }
 function select(id) {
  game.current = id;
  draft = {};
  editingStrategy = null;
  for (let at = nodeOf(id); at && at.parent; at = nodeOf(at.parent)) nodeOf(at.parent).open = true;
  save();
  const node = current();
  render();
  if (node.settled || node.result) cancelInflight();
  else calculate(node);
 }

 // --- tree --------------------------------------------------------------------
 function addChild(parent, fields) {
  const id = 'b' + game.next++;
  game.nodes[id] = {id, parent: parent.id, children: [], log: parent.log, strategy: parent.strategy, probability: '0', open: false, ...fields};
  parent.children.push(id);
  return game.nodes[id];
 }
 function followEvent(parent, event) {
  const key = eventKey(event), source = parent.result || parent.read;
  const known = parent.children.map(nodeOf).find(child => child.eventKey === key && sameStrategy(child.strategy, parent.strategy));
  if (known) return select(known.id);
  const branch = source && source.branches.find(item => eventKey(item.event) === key);
  const ends = event.player !== undefined && source ? source.action_ends[event.player] : null;
  const settled = ends && fraction(ends.village) + fraction(ends.wolf) === 1 ? ends : null;
  const child = addChild(parent, {label: eventLabel(event), event, eventKey: key, log: [...parent.log, event],
   probability: branch ? branch.probability : '0', ends: ends && (fraction(ends.village) || fraction(ends.wolf)) ? ends : null, settled: Boolean(settled)});
  parent.open = true;
  select(child.id);
 }
 function ensureBranches(node) {
  const source = node.result || node.read;
  if (!source) return;
  for (const branch of source.branches) {
   const key = eventKey(branch.event);
   const child = node.children.map(nodeOf).find(item => item.eventKey === key && sameStrategy(item.strategy, node.strategy));
   if (child) { child.probability = branch.probability; continue; }
   const ends = branch.event.player !== undefined ? source.action_ends[branch.event.player] : null;
   addChild(node, {label: eventLabel(branch.event), event: branch.event, eventKey: key, log: [...node.log, branch.event],
    probability: branch.probability, ends: ends && (fraction(ends.village) || fraction(ends.wolf)) ? ends : null,
    settled: Boolean(ends && fraction(ends.village) + fraction(ends.wolf) === 1)});
  }
 }
 function treeView(id) {
  const node = nodeOf(id);
  ensureBranches(node);
  const auto = Number(node.probability) !== 0 && node.probability !== '0' || !node.parent;
  const card = el('button', {type: 'button', class: 'tree-card' + (id === game.current ? ' current' : '') + (auto ? '' : ' manual'), onclick: () => select(id)},
   el('b', {}, node.label),
   el('span', {class: 'muted'}, phaseLabel(node.log) + ' · ' + (node.parent ? '分岐 ' + show(node.probability) : '起点')),
   el('br'),
   node.settled ? el('span', {}, `決着 村 ${show(node.ends.village)} / 狼 ${show(node.ends.wolf)}`)
    : el('span', {}, '村 ' + (node.village ? show(node.village) : (node.failure && node.failure.kind === 'contradiction' ? '矛盾' : '未計算'))));
  const toggle = node.children.length ? el('button', {type: 'button', class: 'toggle', 'aria-expanded': String(Boolean(node.open)),
   'aria-label': (node.open ? '閉じる ' : '開く ') + node.label, onclick: () => { node.open = !node.open; save(); render(); }}, node.open ? '−' : '+') : null;
  const item = el('div', {class: 'tree-item'}, toggle, card);
  if (!node.open || !node.children.length) return el('div', {class: 'tree-node'}, item);
  return el('div', {class: 'tree-node'}, item, el('div', {class: 'tree-children'}, node.children.map(treeView)));
 }

 // --- strategy editor ---------------------------------------------------------
 function orderEditor(title, labels, list, onchange) {
  const names = Object.keys(labels).filter(name => name !== 'uniform');
  const chosen = list.filter(name => name !== 'uniform');
  const change = next => onchange([...next, 'uniform']);
  return el('div', {},
   el('h3', {}, title),
   [...chosen, ...names.filter(name => !chosen.includes(name))].map(name => {
    const position = chosen.indexOf(name);
    return el('div', {class: 'order-item'},
     el('input', {type: 'checkbox', checked: position >= 0, 'aria-label': labels[name],
      onchange: event => change(event.target.checked ? [...chosen, name] : chosen.filter(item => item !== name))}),
     el('span', {}, labels[name]),
     position > 0 ? el('button', {type: 'button', 'aria-label': labels[name] + ' を上へ', onclick: () => {
      const next = [...chosen]; next.splice(position, 1); next.splice(position - 1, 0, name); change(next); }}, '↑') : null);
   }),
   el('div', {class: 'order-item muted'}, '最後は均等'));
 }
 function strategyEditor(strategy, onchange) {
  const change = patch => onchange({...strategy, ...patch});
  const check = (key, label) => el('label', {class: 'check'}, el('input', {type: 'checkbox', checked: strategy[key],
   onchange: event => change({[key]: event.target.checked})}), el('span', {}, label));
  const claim = (role, label) => el('label', {class: 'check'}, el('input', {type: 'checkbox', checked: strategy.wolf_claims.includes(role),
   onchange: event => change({wolf_claims: event.target.checked ? [...strategy.wolf_claims, role] : strategy.wolf_claims.filter(item => item !== role)})}),
   el('span', {}, label));
  const choice = (key, label) => el('label', {class: 'row'}, el('span', {}, label), el('select', {onchange: event => change({[key]: event.target.value})},
   ['max', 'uniform'].map(value => el('option', {value, selected: strategy[key] === value}, value === 'max' ? '最大化' : '等確率'))));
  return el('div', {},
   el('h3', {}, 'CO可能性(狼陣営)'), claim('seer', '占い師を騙れる'), claim('medium', '霊能を騙れる'),
   el('h3', {}, '約束(読む)'), check('co_on_saturation', 'CO: 対抗飽和直後'), check('co_on_black', 'CO: 黒取得直後'), check('disclose_black', '開示: 黒取得直後に黒'),
   el('h3', {}, '想定(読まない)'), check('disclose_all', '開示: 取得直後にすべて'),
   orderEditor('占い位置', SEER_STAGE, strategy.seer_target, value => change({seer_target: value})),
   orderEditor('偽の報告', FAKE_STAGE, strategy.fake_report, value => change({fake_report: value})),
   choice('bite', '噛み'), choice('execution', '処刑'));
 }

 // --- TOP ---------------------------------------------------------------------
 let setup = {cast: {villager: 3, seer: 1, medium: 1, wolf: 2}, rules: {self_bite: false, first_night: 'random_white'}, strategy: STRATEGY()};
 async function startGame() {
  const id = 'g' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  game = {id, created: Date.now(), cast: {...setup.cast}, rules: {...setup.rules}, next: 1, current: 'b0',
   nodes: {b0: {id: 'b0', parent: null, children: [], log: [], strategy: JSON.parse(JSON.stringify(setup.strategy)), probability: '1', open: true, label: '初期盤面'}}};
  await save();
  location.hash = id;
  select('b0');
 }
 function castText(cast) {
  const total = cast.villager + cast.seer + cast.medium + cast.wolf;
  return `${total}人村: ` + Object.keys(ROLE).filter(role => cast[role]).map(role => ROLE[role] + cast[role]).join(' · ');
 }
 async function topView() {
  const saved = (await store('readonly', games => games.getAll())).sort((a, b) => b.created - a.created);
  const numberInput = (role, max) => el('label', {class: 'row'}, el('span', {}, ROLE[role]), el('input', {type: 'number', min: role === 'wolf' ? 1 : 0, max, value: setup.cast[role],
   onchange: event => { setup.cast[role] = Number(event.target.value); render(); }}));
  const total = setup.cast.villager + setup.cast.seer + setup.cast.medium + setup.cast.wolf;
  const valid = total <= 9 && setup.cast.wolf >= 1 && total > 2 * setup.cast.wolf && setup.cast.seer <= 1 && setup.cast.medium <= 1;
  return [
   el('section', {class: 'panel'}, el('h1', {}, 'TOP'),
    el('p', {class: 'muted'}, '新しい計算の芯(wwcore)につないだ画面です。今の範囲は市民・占い師・霊能・人狼。履歴はこのブラウザーの中にだけ保存します。'),
    el('div', {class: 'grid'},
     el('div', {},
      el('h2', {}, '配役'), numberInput('villager', 9), numberInput('seer', 1), numberInput('medium', 1), numberInput('wolf', 4),
      el('p', {class: valid ? 'muted' : 'error'}, `合計 ${total}人。最大9人で、人狼より人間が多い配役にしてください。占い師と霊能は各1人まで。`),
      el('h2', {}, 'ルール'),
      el('label', {class: 'check'}, el('input', {type: 'checkbox', checked: setup.rules.self_bite, onchange: event => { setup.rules.self_bite = event.target.checked; }}), el('span', {}, '自噛みあり')),
      el('label', {class: 'row'}, el('span', {}, '初日の占い'), el('select', {onchange: event => { setup.rules.first_night = event.target.value; }},
       [['random_white', 'ランダム白'], ['divine', 'あり'], ['none', 'なし']].map(([value, label]) => el('option', {value, selected: setup.rules.first_night === value}, label)))),
      el('div', {class: 'row'}, el('button', {type: 'button', class: 'primary', disabled: !valid, onclick: startGame}, 'Day 1 昼へ'))),
     el('div', {}, el('h2', {}, '戦略の初期値'), strategyEditor(setup.strategy, value => { setup.strategy = value; render(); })))),
   saved.length ? el('section', {class: 'panel'}, el('h2', {}, 'このブラウザーの履歴'),
    el('ul', {class: 'saved'}, saved.map(item => el('li', {},
     el('span', {}, castText(item.cast) + ` (${Object.keys(item.nodes).length} Board)`), el('span', {class: 'muted'}, new Date(item.created).toLocaleString('ja-JP')),
     el('button', {type: 'button', onclick: () => { location.hash = item.id; }}, '開く'),
     el('button', {type: 'button', onclick: async () => { if (confirm('この履歴を消します。元に戻せません。')) { await store('readwrite', games => games.delete(item.id)); render(); } }}, '消す'))))) : null];
 }

 // --- MAIN --------------------------------------------------------------------
 function draftColumn(node, state) {
  const acts = [];
  for (const player of state.alive) {
   const entry = draft[player] || {};
   if (entry.co && !state.claims[player]) acts.push({kind: 'co', player, role: entry.co});
   if (entry.target && entry.color && (state.claims[player] || entry.co)) acts.push({kind: 'report', player, target: Number(entry.target), color: entry.color});
  }
  return {kind: 'col', acts};
 }
 function tableView(node, source, editable, state) {
  const count = players(), action = source ? source.stage : null;
  const rates = node.result ? node.result.action_rates : {};
  const best = Object.values(rates).length ? Math.max(...Object.values(rates).map(fraction)) : null;
  const bestWolf = Object.values(rates).length ? Math.min(...Object.values(rates).map(fraction)) : null;
  const rows = [];
  for (let player = 1; player <= count; player++) {
   const alive = state.alive.has(player), row = source ? source.role_rates[player] : null, entry = draft[player] ||= {};
   const claimed = state.claims[player], claim = claimed || entry.co;
   const reports = (state.reports[player] || []).map(act => `${P(act.target)}${COLOR[act.color]}`).join(' ');
   const target = action === 'closed' || action === 'night' ? player : null, rate = rates[player];
   const target_ok = target && alive && (source.action_ends[player] !== undefined);
   const mark = rate === undefined ? '' : (action === 'closed' ? fraction(rate) === best : fraction(rate) === bestWolf) ? ' best' : '';
   const cells = [
    el('td', {}, P(player) + (alive ? '' : ' 死亡')),
    el('td', {}, claimed ? ROLE[claimed] + 'CO' : (editable && alive ? el('select', {'aria-label': P(player) + ' のCO', onchange: event => { entry.co = event.target.value; render(); }},
     [['', '—'], ['seer', '占い師CO'], ['medium', '霊能CO']].filter(([value]) => !value || game.cast[value]).map(([value, label]) => el('option', {value, selected: (entry.co || '') === value}, label))) : '')),
    el('td', {}, [reports, editable && alive && claim ? el('span', {class: 'row'},
     el('select', {'aria-label': P(player) + ' の報告先', onchange: event => { entry.target = event.target.value; render(); }},
      el('option', {value: ''}, '報告なし'), Array.from({length: count}, (_, i) => i + 1).filter(other => other !== player).map(other => el('option', {value: other, selected: Number(entry.target) === other}, P(other)))),
     el('select', {'aria-label': P(player) + ' の報告の色', onchange: event => { entry.color = event.target.value; render(); }},
      Object.keys(COLOR).map(color => el('option', {value: color, selected: (entry.color || (entry.color = 'white')) === color}, COLOR[color])))) : null].filter(Boolean)),
    ...Object.keys(ROLE).filter(role => game.cast[role]).map(role => el('td', {}, row ? show(row[role]) : '…')),
    el('td', {class: mark.trim()}, rate !== undefined ? show(rate) : ''),
    el('td', {}, target_ok ? el('button', {type: 'button', onclick: () => followEvent(node, {kind: action === 'closed' ? 'exec' : 'bite', player})}, action === 'closed' ? '処刑' : '噛み') : '')];
   rows.push(el('tr', {class: alive ? '' : 'dead'}, cells));
  }
  const heading = action === 'night' ? '噛んだときの村の勝率' : action === 'closed' ? '処刑したときの村の勝率' : '行動ごとの村の勝率';
  return el('div', {class: 'table-wrap'}, el('table', {},
   el('thead', {}, el('tr', {}, ['Player', 'CO', '報告', ...Object.keys(ROLE).filter(role => game.cast[role]).map(role => ROLE[role]), heading, ''].map(text => el('th', {}, text)))),
   el('tbody', {}, rows)));
 }
 function mainView() {
  const node = current(), state = publicState(node.log), source = node.result || node.read;
  const last = node.log[node.log.length - 1];
  const dayEnded = last && (last.kind === 'exec' || (last.kind === 'col' && !last.acts.length));
  const editable = !node.settled && !dayEnded && !(node.failure && node.failure.kind === 'contradiction');
  const running = calculating === node.id;
  const overview = el('section', {class: 'panel', id: 'overview'},
   el('h1', {}, node.settled ? '決着' : phaseLabel(node.log)),
   el('p', {class: 'muted'}, castText(game.cast) + ' · 生存 ' + state.alive.size + '人 · ' + node.label),
   node.settled ? el('div', {class: 'rates'},
     el('div', {class: 'rate village'}, el('small', {}, '村陣営'), el('strong', {}, show(node.ends.village))),
     el('div', {class: 'rate wolf'}, el('small', {}, '狼陣営'), el('strong', {}, show(node.ends.wolf))))
    : el('div', {class: 'rates'},
     el('div', {class: 'rate village'}, el('small', {}, '村陣営の勝率'), el('strong', {id: 'village-rate'}, node.result ? show(node.result.win_rates.village) : running ? '計算中…' : '未計算')),
     el('div', {class: 'rate wolf'}, el('small', {}, '狼陣営の勝率'), el('strong', {id: 'wolf-rate'}, node.result ? show(node.result.win_rates.wolf) : running ? '計算中…' : '未計算'))),
   node.ends && !node.settled ? el('p', {class: 'muted'}, `この行動で決着: 村 ${show(node.ends.village)} / 狼 ${show(node.ends.wolf)}。下の値は決着しなかった場合です。`) : null,
   node.failure ? el('p', {class: node.failure.kind === 'contradiction' ? 'error' : 'muted', role: 'alert'}, node.failure.message) : null,
   el('div', {class: 'row'},
    running ? el('button', {type: 'button', onclick: () => { cancelInflight(); render(); }}, '計算を止める') : null,
    !running && !node.settled && !node.result && !(node.failure && node.failure.kind === 'contradiction') ? el('button', {type: 'button', onclick: () => calculate(node)}, '勝率を計算') : null,
    node.parent ? el('button', {type: 'button', onclick: () => select(node.parent)}, '← 親の Board') : null,
    el('button', {type: 'button', onclick: () => { cancelInflight(); game = null; location.hash = ''; render(); }}, 'TOP に戻る')));
  const column = draftColumn(node, state);
  const table = node.settled || (node.failure && node.failure.kind === 'contradiction') ? null : el('section', {class: 'panel'},
   el('h2', {}, 'BoardTable'), tableView(node, source, editable, state),
   editable ? el('div', {class: 'row'},
    el('button', {type: 'button', class: 'primary', disabled: !column.acts.length, onclick: () => followEvent(node, column)}, '更新(この内容の Board を作る)'),
    el('button', {type: 'button', onclick: () => followEvent(node, {kind: 'col', acts: []})}, '更新なし')) : null,
   el('p', {class: 'muted'}, source && source.stage === 'open' ? '約束や想定で更新が起こり得る盤面です。下の分岐か「更新なし」から処刑に進みます。' : ''));
  const branches = source && source.branches.length ? el('section', {class: 'panel'}, el('h2', {}, node.result ? '分岐' : '分岐(計算できた分)'),
   el('ul', {class: 'branches'}, source.branches.map(branch => el('li', {},
    el('button', {type: 'button', onclick: () => followEvent(node, branch.event)}, eventLabel(branch.event)),
    el('span', {class: 'muted'}, show(branch.probability)))))) : null;
  const log = node.log.length ? el('section', {class: 'panel'}, el('h2', {}, 'BoardLog'), el('ol', {class: 'log'}, node.log.map(event => el('li', {}, eventLabel(event))))) : null;
  const strategy = editingStrategy || node.strategy;
  const changed = !sameStrategy(strategy, node.strategy);
  const strategyPanel = el('section', {class: 'panel'}, el('h2', {}, 'BoardStrategy'),
   strategyEditor(strategy, value => { editingStrategy = value; render(); }),
   el('div', {class: 'row'},
    el('button', {type: 'button', class: 'primary', disabled: !changed, onclick: () => {
     const child = addChild(node, {label: '戦略を変更', strategy: editingStrategy, eventKey: 'strategy:' + Date.now()});
     node.open = true; select(child.id); }}, '更新(この戦略の Board を作る)'),
    changed ? el('button', {type: 'button', onclick: () => { editingStrategy = null; render(); }}, 'キャンセル') : null));
  const tree = el('section', {class: 'panel', id: 'tree'}, el('h2', {}, 'GameTree'),
   el('p', {class: 'muted'}, '点線は手動更新(分岐 0%)。クリックした Board を Current にします。'),
   el('div', {class: 'tree-frame'}, treeView('b0')));
  return [el('div', {class: 'grid'}, el('div', {}, overview, table, branches, log), strategyPanel), tree];
 }

 // --- render ------------------------------------------------------------------
 let renderId = 0;
 async function render() {
  const version = ++renderId;
  const view = game ? mainView() : await topView();
  if (version !== renderId) return;
  const focusLabel = document.activeElement && document.activeElement.getAttribute && document.activeElement.getAttribute('aria-label');
  app.replaceChildren(...(flash ? [el('p', {class: 'error', role: 'alert'}, flash)] : []), ...view.filter(Boolean));
  if (focusLabel) for (const node of app.querySelectorAll('[aria-label]')) if (node.getAttribute('aria-label') === focusLabel) { node.focus({preventScroll: true}); break; }
 }
 async function route() {
  const id = location.hash.slice(1);
  cancelInflight();
  game = id ? await store('readonly', games => games.get(id)) || null : null;
  draft = {}; editingStrategy = null;
  if (id && !game) { flash = 'この履歴は見つかりません。'; location.hash = ''; }
  await render();
  if (game) { const node = current(); if (!node.settled && !node.result && !(node.failure && node.failure.kind === 'contradiction')) calculate(node); }
 }
 const format = document.getElementById('fraction-format');
 format.checked = fractions;
 format.addEventListener('change', () => {
  fractions = format.checked;
  try { localStorage.setItem('ww_gg.core.fractions', fractions ? '1' : '0'); } catch (_) {}
  render();
 });
 window.addEventListener('hashchange', route);
 window.addEventListener('pagehide', cancelInflight);
 openDb().then(database => { db = database; return route(); }).catch(error => {
  app.replaceChildren(el('p', {class: 'error', role: 'alert'}, '履歴の保存先を開けません: ' + error.message));
 });
})();
