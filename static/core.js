"use strict";
// v0.8 screen in the v0.6 layout. The server is stateless; games, boards and results live in IndexedDB (docs/redesign/tree.md).
(() => {
 const defaults = JSON.parse(document.getElementById('strategy-defaults').textContent);
 const app = document.getElementById('app');
 const ROLE = {villager: '市民', medium: '霊能', seer: '占い師', wolf: '人狼'};
 const COLOR = {white: '白', black: '黒'};
 const SEER_STAGE = {undetermined: '未確定', unseen: '未占い', latent: '潜伏', half_white: '片白', uniform: '均等'};
 const FAKE_STAGE = {no_contradiction: '破綻しない報告', uniform: '均等'};
 const STRATEGY = () => ({wolf_claims: ['seer', 'medium'], co_on_saturation: true, co_on_black: true, disclose_black: true,
  disclose_all: true, seer_target: [...defaults.seer_target], fake_report: [...defaults.fake_report], bite: 'max', execution: 'max'});

 let db = null, game = null, flash = '', inflight = null, calculating = null, draft = {}, editingStrategy = null;
 let target = null, breakdown = true, backgroundPaused = false;
 const panes = {display: false, rules: false, strategy: false};
 let fractions = false;
 try { fractions = localStorage.getItem('ww_gg.probability-format') === 'fraction'; } catch (_) {}

 // --- small helpers -----------------------------------------------------------
 function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
   if (key === 'class') node.className = value;
   else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
   else if (key in node && !key.includes('-')) node[key] = value;
   else node.setAttribute(key, value);
  }
  node.append(...children.flat(3).filter(child => child !== null && child !== undefined && child !== false));
  return node;
 }
 function fraction(text) { const [n, d = '1'] = String(text).split('/'); return Number(n) / Number(d); }
 function show(text) {
  if (text === undefined || text === null) return '—';
  return fractions ? String(text) : (Math.round(fraction(text) * 10000) / 100) + '%';
 }
 function addFractions(values) {
  let n = 0n, d = 1n;
  for (const value of values) {
   const [a, b = '1'] = String(value).split('/');
   n = n * BigInt(b) + BigInt(a) * d; d *= BigInt(b);
  }
  let x = n < 0n ? -n : n, y = d;
  while (y) [x, y] = [y, x % y];
  n /= x || 1n; d /= x || 1n;
  return d === 1n ? String(n) : `${n}/${d}`;
 }
 function complement(text) {
  const [n, d = '1'] = String(text).split('/');
  return addFractions(['1', `${-BigInt(n)}/${d}`]);
 }
 const probability = (value, cls = '') => el('strong', {class: 'probability ' + cls}, show(value));
 const players = () => game.cast.villager + game.cast.seer + game.cast.medium + game.cast.wolf;
 const nodeOf = id => game.nodes[id];
 const current = () => nodeOf(game.current);
 // Board numbers follow the order the Tree first shows them, as in v0.6.
 const shownNumber = node => { game.shown ??= 0; node.shown ??= game.shown++; return node.shown; };
 const isContradiction = node => Boolean(node.failure && node.failure.kind === 'contradiction');

 const actLabel = act => act.kind === 'co' ? `P${act.player} ${ROLE[act.role]}CO` : `P${act.player}→P${act.target} ${COLOR[act.color]}`;
 function eventLabel(event) {
  if (event.kind === 'exec') return `P${event.player}を処刑`;
  if (event.kind === 'bite') return `P${event.player}を噛み`;
  return event.acts.length ? event.acts.map(actLabel).join(' / ') : '更新なし';
 }
 const actKey = act => act.kind === 'co' ? `co:${act.player}:${act.role}` : `report:${act.player}:${act.target}:${act.color}`;
 const eventKey = event => event.kind === 'col' ? 'col:' + event.acts.map(actKey).sort().join(',') : `${event.kind}:${event.player}`;
 const dayOf = log => 1 + log.filter(event => event.kind === 'bite').length;
 const isNight = log => { const last = log[log.length - 1]; return Boolean(last && last.kind === 'exec'); };
 const phaseText = log => `Day ${dayOf(log)} · ${isNight(log) ? '夜' : '昼'}`;
 function publicState(log) {
  const alive = new Set(Array.from({length: players()}, (_, i) => i + 1)), claims = {}, deaths = {}, columns = [];
  let day = 1;
  for (const event of log) {
   if (event.kind === 'col') {
    columns.push({day, event});
    for (const act of event.acts) if (act.kind === 'co') claims[act.player] = act.role;
   } else {
    alive.delete(event.player);
    deaths[event.player] = `D${day} ${event.kind === 'exec' ? '処刑' : '襲撃'}`;
    if (event.kind === 'bite') day++;
   }
  }
  return {alive, claims, deaths, columns};
 }
 const sameStrategy = (a, b) => JSON.stringify(a) === JSON.stringify(b);
 function castText(cast) {
  const total = cast.villager + cast.seer + cast.medium + cast.wolf;
  return `${total}人村:` + Object.keys(ROLE).filter(role => cast[role]).map(role => ROLE[role] + cast[role]).join(' · ');
 }

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
  fetch('/calculation-cancel', {method: 'POST', keepalive: true, body: new URLSearchParams({calculation_id: inflight.token})}).catch(() => {});
  inflight = null;
 }
 const newToken = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
 async function request(node, scope) {
  const token = newToken(), controller = new AbortController();
  inflight = {token, controller};
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
  const owner = game, mine = calculating = node.id, live = () => calculating === mine && game === owner;
  render();
  try {
   if (!node.read && !node.result) {
    const read = await request(node, 'read');
    if (!live()) return;
    if (read.status !== 200) return failed(node, read);
    node.read = read.data;
    render();
   }
   const full = await request(node, 'full');
   if (!live()) return;
   if (full.status !== 200) return failed(node, full);
   const {children = [], ...result} = full.data;
   node.result = result;
   node.village = result.win_rates.village;
   node.expanded = true;
   for (const {event, result: known} of children) {
    const child = childFor(node, event, result.branches.find(branch => eventKey(branch.event) === eventKey(event)));
    if (!child.result) Object.assign(child, {result: known, village: known.win_rates.village, failure: null});
   }
   calculating = null;
   save();
   render();
   next();
  } catch (error) {
   if (error.name === 'AbortError') return;
   calculating = null;
   node.failure = {kind: 'network', message: '通信できません: ' + error.message};
   backgroundPaused = true;
   render();
  }
 }
 function failed(node, {status, data}) {
  if (status === 499) return;
  calculating = null;
  if (status === 422) node.failure = {kind: 'contradiction', message: '盤面が戦略と矛盾しています(役職の候補が残りません)。'};
  else if (status === 503) { node.failure = {kind: 'pending', message: node.result ? 'この先の Board は未計算: 時間か作業量の上限に達しました。' : '未計算: 時間か作業量の上限に達しました。'}; backgroundPaused = true; }
  else node.failure = {kind: 'invalid', message: data.error || '計算できません'};
  save();
  render();
  next();
 }
 // Calculated one at a time, Current first. A Board's calculation also fills its direct children,
 // so a Board already known from its parent only runs when its own children are needed.
 function next() {
  if (calculating || !game || backgroundPaused) return;
  const pending = visibleBoards().find(node => !node.settled && !node.failure && (!node.result || (!node.expanded && (node.open || node === current()))));
  if (pending) calculate(pending);
 }
 function select(id) {
  game.current = id;
  nodeOf(id).visited = true;
  draft = {}; editingStrategy = null; target = null; backgroundPaused = false;
  for (let at = nodeOf(id); at && at.parent; at = nodeOf(at.parent)) nodeOf(at.parent).open = true;
  save();
  const node = current();
  if (node.settled || node.result || isContradiction(node)) {
   if (calculating) cancelInflight();
   render();
   next();
  } else calculate(node);
 }

 // --- tree model --------------------------------------------------------------
 function addChild(parent, fields) {
  const id = 'b' + game.next++;
  game.nodes[id] = {id, parent: parent.id, children: [], log: parent.log, strategy: parent.strategy, probability: '0', open: false, ...fields};
  parent.children.push(id);
  return game.nodes[id];
 }
 function childFor(parent, event, branch) {
  const key = eventKey(event), source = parent.result || parent.read;
  const known = parent.children.map(nodeOf).find(child => child.eventKey === key && sameStrategy(child.strategy, parent.strategy));
  if (known) { if (branch) known.probability = branch.probability; return known; }
  const ends = event.player !== undefined && source ? source.action_ends[event.player] : null;
  const ended = ends && (fraction(ends.village) || fraction(ends.wolf)) ? ends : null;
  return addChild(parent, {label: eventLabel(event), event, eventKey: key, log: [...parent.log, event],
   probability: branch ? branch.probability : '0', ends: ended, settled: Boolean(ended && addFractions([ends.village, ends.wolf]) === '1')});
 }
 function followEvent(parent, event) {
  const source = parent.result || parent.read;
  const branch = source && source.branches.find(item => eventKey(item.event) === eventKey(event));
  parent.open = true;
  select(childFor(parent, event, branch).id);
 }
 function ensureBranches(node) {
  const source = node.result || node.read;
  if (source) for (const branch of source.branches) childFor(node, branch.event, branch);
 }
 // Same public position, same rate and same probability: one action card, as in the v0.6 Tree.
 function publicPosition(node, player) {
  return node.log.flatMap(event => event.kind === 'col' ? event.acts : [])
   .filter(act => act.player === player || act.target === player)
   .map(act => act.kind === 'co' ? 'co' + act.role : (act.player === player ? 'from' + act.color : 'to' + act.color)).sort();
 }
 function positionKey(node, player, source) {
  return JSON.stringify([publicPosition(node, player), (source.action_rates || {})[player], source.action_ends[player]]);
 }
 const actionKey = (node, child, source) => child.probability === '0' || !source ? 'single:' + child.id : child.probability + positionKey(node, child.event.player, source);
 // A lone CO by players in the same position, with the same role rates and the same win rate after it.
 const loneCo = child => child.event && child.event.kind === 'col' && child.event.acts.length === 1 && child.event.acts[0].kind === 'co' ? child.event.acts[0] : null;
 const coPosition = (node, player, source) => JSON.stringify([publicPosition(node, player), source.role_rates[player]]);
 function columnKey(node, child, source) {
  const act = loneCo(child);
  return act && source && child.village && child.probability !== '0' ? JSON.stringify([act.role, coPosition(node, act.player, source), child.village]) : 'single:' + child.id;
 }
 function childGroups(node, children, keyOf) {
  const source = node.result || node.read, onPath = new Set();
  for (let at = current(); at; at = at.parent ? nodeOf(at.parent) : null) onPath.add(at.id);
  const visited = child => onPath.has(child.id) || child.open || child.visited;
  const groups = [], byKey = new Map();
  for (const child of children) {
   const key = keyOf(node, child, source);
   if (!byKey.has(key)) { byKey.set(key, {members: []}); groups.push(byKey.get(key)); }
   byKey.get(key).members.push(child);
  }
  return groups.flatMap(group => {
   const seen = group.members.filter(visited);
   if (seen.length <= 1) return [{members: group.members, representative: seen[0] || group.members[0]}];
   const rest = group.members.filter(member => !seen.includes(member) || member === seen[0]);
   return [{members: rest, representative: seen[0]}, ...seen.slice(1).map(member => ({members: [member], representative: member}))];
  });
 }
 function actionLabel(group, kind) {
  const verb = kind === 'exec' ? '処刑' : '噛み';
  if (group.members.length === 1) return `${group.members[0].event.player}を${verb}`;
  const list = group.members.map(child => child.event.player).sort((a, b) => a - b)
   .map(player => player === group.representative.event.player ? `(${player})` : player).join(',');
  return `[${list}]から${verb}`;
 }
 // The core sends one column for the players it can rename freely; those players stay in the label.
 function columnLabel(node, group, siblings) {
  const child = group.representative, act = loneCo(child), source = node.result || node.read;
  if (!act || !source || child.probability === '0') return child.label;
  const state = publicState(node.log), explicit = new Set(siblings.map(loneCo).filter(item => item && item.role === act.role).map(item => item.player));
  const same = [...state.alive].filter(player => !state.claims[player] && !explicit.has(player) && coPosition(node, player, source) === coPosition(node, act.player, source));
  const list = [...group.members.map(member => loneCo(member).player), ...same].sort((a, b) => a - b);
  return list.length > 1 ? `[${list.map(player => player === act.player ? `(P${player})` : `P${player}`).join(',')}] ${ROLE[act.role]}CO` : child.label;
 }
 function visibleBoards() {
  const out = [];
  const walk = node => {
   out.push(node);
   if (!node.open) return;
   ensureBranches(node);
   const children = node.children.map(nodeOf);
   for (const group of childGroups(node, children.filter(item => !item.event || item.event.kind === 'col'), columnKey)) walk(group.representative);
   for (const kind of ['exec', 'bite']) {
    const acts = children.filter(item => item.event && item.event.kind === kind);
    for (const group of childGroups(node, acts, actionKey)) if (!group.representative.settled) walk(group.representative);
   }
  };
  walk(nodeOf('b0'));
  return [current(), ...out.filter(node => node !== current())];
 }

 // --- tree view (v0.6 columns, laid out by tree_layout.js) ------------------------
 function buildTree() {
  const entries = [], columnKeys = new Set();
  const place = (item, column) => { item.columnKey = column; columnKeys.add(column); entries.push(item); return item; };
  const boardCard = (node, depth, label = node.label) => {
   const day = dayOf(node.log), night = isNight(node.log);
   const update = node.parent && (!node.event || node.event.kind === 'col');
   const manual = node.parent && node.probability === '0';
   const article = el('article', {class: `tree-item compact-tree-item compact-tree-board${update ? ' compact-tree-update' : ''}${manual ? ' manual' : ''}${node.id === game.current ? ' current' : ''}`});
   article.dataset.treeItem = node.id;
   if (node.village) article.append(el('span', {class: 'probability tree-win-corner'}, show(node.village)));
   else if (node.failure) article.append(el('span', {class: 'probability tree-win-corner'}, isContradiction(node) ? '矛盾' : '未計算'));
   const main = el('button', {type: 'button', class: 'compact-tree-select', 'aria-expanded': String(Boolean(node.open)),
    onclick: () => { node.open = !node.open; save(); render(); next(); }});
   if (update) for (const line of (label || '').split(' / ')) main.append(el('span', {class: 'tree-log-row'}, line));
   else main.textContent = `B${shownNumber(node)} · ${publicState(node.log).alive.size}人`;
   article.append(main, el('button', {type: 'button', class: 'compact-tree-go', title: 'このBoardをCurrentにする', 'aria-label': `${(node.label || '').split(' / ')[0]} B${shownNumber(node)}へ遷移`, onclick: () => select(node.id)}, '→'));
   return place({key: node.id, element: article, children: [], node}, `${day}-${night ? 'n' : 'd'}-${depth}`);
  };
  const leaf = (key, text, cls, columnKey, onclick) => place({key, children: [], element: el('article', {class: `tree-item compact-tree-item compact-tree-board settled ${cls}`},
   el('button', {type: 'button', class: 'compact-tree-select', onclick}, text))}, columnKey);
  const build = (node, depth, label) => {
   const item = boardCard(node, depth, label);
   if (!node.open) return item;
   ensureBranches(node);
   const children = node.children.map(nodeOf), day = dayOf(node.log), night = isNight(node.log);
   const columns = children.filter(c => !c.event || c.event.kind === 'col');
   for (const group of childGroups(node, columns, columnKey)) item.children.push({item: build(group.representative, depth + 1, columnLabel(node, group, columns)), probability: addFractions(group.members.map(member => member.probability))});
   for (const kind of ['exec', 'bite']) {
    const acts = children.filter(c => c.event && c.event.kind === kind);
    for (const group of childGroups(node, acts, actionKey)) {
     const child = group.representative, manual = child.probability === '0';
     const action = place({key: `${node.id}:act:${child.id}`, children: [], element: el('button', {type: 'button',
      class: `tree-item compact-tree-item compact-action-item${manual ? ' manual' : ''}`, onclick: () => select(child.id)}, actionLabel(group, kind))}, `${day}-${night ? 'n' : 'd'}-act`);
     item.children.push({item: action, probability: addFractions(group.members.map(member => member.probability))});
     const nextColumn = kind === 'exec' ? `${day}-n-0` : `${day + 1}-d-0`;
     if (child.ends) {
      if (fraction(child.ends.village)) action.children.push({probability: child.ends.village, item: leaf(`${child.id}:v`, '決着 · 村勝利', 'village', nextColumn, () => select(child.id))});
      if (fraction(child.ends.wolf)) action.children.push({probability: child.ends.wolf, item: leaf(`${child.id}:w`, '決着 · 狼勝利', 'wolf', nextColumn, () => select(child.id))});
     }
     if (!child.settled) action.children.push({probability: child.ends ? complement(addFractions([child.ends.village, child.ends.wolf])) : '1', item: build(child, 0)});
    }
   }
   return item;
  };
  build(nodeOf('b0'), 0);
  return {entries, columnKeys};
 }
 function columnOrder(keys) {
  const rank = key => { const [day, phase, depth] = key.split('-'); return Number(day) * 2 + (phase === 'n' ? 1 : 0) + (depth === 'act' ? 0.9 : Number(depth) * 0.01); };
  return [...keys].sort((a, b) => rank(a) - rank(b));
 }
 function renderTree(frame) {
  const {entries, columnKeys} = buildTree(), order = columnOrder(columnKeys), index = new Map(order.map((key, i) => [key, i]));
  for (const item of entries) item.column = index.get(item.columnKey);
  const canvas = el('div', {class: 'compact-tree-canvas'}), headers = el('div', {class: 'compact-tree-headers'}), headings = [], groups = new Map();
  order.forEach((key, i) => {
   const [day, phase, depth] = key.split('-'), night = phase === 'n';
   headings.push(el('h3', {class: 'compact-tree-phase phase-heading'}, depth === 'act' ? (night ? '襲撃位置' : '処刑位置') : depth === '0' ? `Day${day}${night ? '夜' : '昼'}` : `更新${depth}`));
   const groupKey = day + phase;
   if (!groups.has(groupKey)) groups.set(groupKey, {night, start: i, end: i});
   groups.get(groupKey).end = i;
  });
  for (const group of groups.values()) { group.element = el('div', {class: 'compact-phase-group' + (group.night ? ' night' : '')}); headers.append(group.element); }
  headers.append(...headings);
  canvas.append(...entries.map(item => item.element));
  frame.replaceChildren(el('div', {class: 'tree-flowchart'}, headers, canvas));
  const widths = window.TreeLayout.measure(entries, headings), height = window.TreeLayout.arrange(entries), offsets = [];
  let width = 6;
  widths.forEach((columnWidth, i) => { offsets.push(width); headings[i].style.left = width + 'px'; headings[i].style.width = columnWidth + 'px'; width += columnWidth + 64; });
  for (const group of groups.values()) { group.element.style.left = (offsets[group.start] - 3) + 'px'; group.element.style.width = (offsets[group.end] + widths[group.end] - offsets[group.start] + 6) + 'px'; }
  headers.style.width = width + 'px';
  canvas.style.width = width + 'px';
  canvas.style.height = (height + 24) + 'px';
  for (const item of entries) {
   item.x = offsets[item.column]; item.width = widths[item.column];
   item.element.style.left = item.x + 'px'; item.element.style.top = (item.cy - 13.5) + 'px';
  }
  const routed = window.TreeLayout.connect(entries, offsets, widths), ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('width', String(width)); svg.setAttribute('height', String(height + 24)); svg.classList.add('compact-tree-lines');
  for (const edge of routed.edges) {
   const path = document.createElementNS(ns, 'path');
   path.setAttribute('d', edge.d);
   if (edge.probability === '0') path.classList.add('manual');
   svg.append(path);
   const label = el('span', {class: 'compact-tree-edge'}, String(edge.probability));
   label.style.left = edge.label.x + 'px'; label.style.top = edge.label.y + 'px';
   canvas.append(label);
  }
  canvas.prepend(svg);
 }

 // --- strategy editor ---------------------------------------------------------
 function orderEditor(title, labels, list, onchange) {
  const names = Object.keys(labels).filter(name => name !== 'uniform');
  const chosen = list.filter(name => name !== 'uniform');
  const change = value => onchange([...value, 'uniform']);
  return el('div', {class: 'strategy-section'},
   el('h4', {}, title),
   [...chosen, ...names.filter(name => !chosen.includes(name))].map(name => {
    const position = chosen.indexOf(name);
    return el('div', {class: 'order-item'},
     el('input', {type: 'checkbox', checked: position >= 0, 'aria-label': labels[name],
      onchange: event => change(event.target.checked ? [...chosen, name] : chosen.filter(item => item !== name))}),
     el('span', {}, labels[name]),
     position > 0 ? el('button', {type: 'button', class: 'secondary', 'aria-label': labels[name] + ' を上へ', onclick: () => {
      const value = [...chosen]; value.splice(position, 1); value.splice(position - 1, 0, name); change(value); }}, '↑') : null);
   }),
   el('div', {class: 'order-item muted'}, '最後は均等'));
 }
 function strategyEditor(strategy, onchange) {
  const change = patch => onchange({...strategy, ...patch});
  const check = (key, label) => el('label', {class: 'checkbox-label'}, el('input', {type: 'checkbox', checked: strategy[key],
   onchange: event => change({[key]: event.target.checked})}), el('span', {}, label));
  const claim = (role, label) => el('label', {class: 'checkbox-label'}, el('input', {type: 'checkbox', checked: strategy.wolf_claims.includes(role),
   onchange: event => change({wolf_claims: event.target.checked ? [...strategy.wolf_claims, role] : strategy.wolf_claims.filter(item => item !== role)})}),
   el('span', {}, label));
  const choice = (key, label) => el('label', {class: 'strategy-row'}, el('span', {}, label), el('select', {onchange: event => change({[key]: event.target.value})},
   ['max', 'uniform'].map(value => el('option', {value, selected: strategy[key] === value}, value === 'max' ? '最大化' : '等確率'))));
  return [
   el('div', {class: 'strategy-section'}, el('h4', {}, 'CO可能性(狼陣営)'), claim('seer', '占い師を騙れる'), claim('medium', '霊能を騙れる')),
   el('div', {class: 'strategy-section'}, el('h4', {}, '約束(読む)'), check('co_on_saturation', 'CO: 対抗飽和直後'), check('co_on_black', 'CO: 黒取得直後'), check('disclose_black', '開示: 黒取得直後に黒')),
   el('div', {class: 'strategy-section'}, el('h4', {}, '想定(読まない)'), check('disclose_all', '開示: 取得直後にすべて')),
   orderEditor('占い位置', SEER_STAGE, strategy.seer_target, value => change({seer_target: value})),
   orderEditor('偽の報告', FAKE_STAGE, strategy.fake_report, value => change({fake_report: value})),
   el('div', {class: 'strategy-section'}, choice('bite', '噛み位置'), choice('execution', '処刑位置'))];
 }

 // --- shared parts --------------------------------------------------------------
 function pane(key, title, ...body) {
  return el('details', {open: panes[key], ontoggle: event => {
   if (panes[key] === event.target.open) return;
   panes[key] = event.target.open;
   const layout = event.target.closest('.board-layout');
   if (layout) layout.classList.toggle('settings-open', Object.values(panes).some(Boolean));
  }}, el('summary', {}, title), el('div', {class: 'settings-body'}, body));
 }
 function displayPane() {
  const option = (value, label) => el('label', {}, el('input', {type: 'radio', name: 'probability-format', value, checked: fractions === (value === 'fraction'), onchange: () => {
   fractions = value === 'fraction';
   try { localStorage.setItem('ww_gg.probability-format', value); } catch (_) {}
   render();
  }}), ' ' + label);
  return pane('display', '表示', el('fieldset', {class: 'format-switch'}, el('legend', {}, '表示形式'), option('percent', '％'), option('fraction', '分数')));
 }
 const footer = (...parts) => el('footer', {class: 'phase-footer'}, el('div', {class: 'footer-inner'}, parts));
 const phaseButton = (text, props, previous = false) => el('button', {type: 'button', class: previous ? 'secondary' : 'primary', ...props},
  previous ? [el('span', {'aria-hidden': 'true'}, '←'), ' ' + text] : [text + ' ', el('span', {'aria-hidden': 'true'}, '→')]);

 // --- TOP ---------------------------------------------------------------------
 const setup = {cast: {villager: 3, medium: 1, seer: 1, wolf: 2}, rules: {self_bite: false, first_night: 'random_white'}, strategy: STRATEGY()};
 async function startGame() {
  const id = 'g' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const created = {id, created: Date.now(), cast: {...setup.cast}, rules: {...setup.rules}, next: 1, current: 'b0',
   nodes: {b0: {id: 'b0', parent: null, children: [], log: [], strategy: JSON.parse(JSON.stringify(setup.strategy)), probability: '1', open: true, label: '初期盤面'}}};
  await store('readwrite', games => games.put(created));
  location.hash = id;
 }
 async function topView() {
  const saved = (await store('readonly', games => games.getAll())).sort((a, b) => b.created - a.created);
  const count = (role, max) => el('label', {class: 'role-count-row'}, el('span', {}, ROLE[role]), el('input', {type: 'number', min: role === 'wolf' ? 1 : 0, max, value: setup.cast[role], required: true,
   onchange: event => { setup.cast[role] = Number(event.target.value); render(); }}));
  const {cast} = setup, total = cast.villager + cast.seer + cast.medium + cast.wolf;
  const valid = total <= 9 && cast.wolf >= 1 && total > 2 * cast.wolf && cast.seer <= 1 && cast.medium <= 1;
  const rules = pane('rules', 'ルール',
   el('label', {class: 'checkbox-label'}, el('input', {type: 'checkbox', checked: setup.rules.self_bite, onchange: event => { setup.rules.self_bite = event.target.checked; }}), el('span', {}, '自噛みあり')),
   el('label', {class: 'strategy-row'}, el('span', {}, '初日の占い'), el('select', {onchange: event => { setup.rules.first_night = event.target.value; }},
    [['random_white', 'ランダム白'], ['divine', 'あり'], ['none', 'なし']].map(([value, label]) => el('option', {value, selected: setup.rules.first_night === value}, label)))));
  return [
   el('main', {'data-screen': 'top'},
    el('p', {class: 'eyebrow'}, 'TOP'),
    el('p', {class: 'hint calculation-estimate'}, '新しい計算の芯につないだ画面です。計算時間は配役・履歴で変わり、1回の計算は最大約5分です。履歴はこのブラウザーの中にだけ保存します。'),
    el('div', {class: 'top-grid'},
     el('section', {class: 'panel cast-panel', 'aria-labelledby': 'game-cast-title'},
      el('div', {class: 'panel-heading setup-heading'}, el('h2', {id: 'game-cast-title'}, '配役')),
      el('div', {class: 'role-columns'},
       el('section', {class: 'role-column'}, el('h3', {}, '村陣営'), count('villager', 9), count('medium', 1), count('seer', 1)),
       el('section', {class: 'role-column'}, el('h3', {}, '狼陣営'), count('wolf', 4))),
      el('div', {class: 'cast-grid cast-summary'},
       el('div', {class: 'cast-card village'}, el('span', {}, '村陣営'), el('strong', {}, String(total - cast.wolf), el('small', {}, '人'))),
       el('div', {class: 'cast-card wolf'}, el('span', {}, '狼陣営'), el('strong', {}, String(cast.wolf), el('small', {}, '人'))),
       el('div', {class: 'cast-card total'}, el('span', {}, '合計'), el('strong', {}, total + '人', el('small', {}, '(最大9人)')))),
      el('p', {class: valid ? 'hint' : 'hint error', id: 'cast-validation'}, '合計9人まで。人狼より人間が多い配役にしてください。占い師と霊能は各1人まで。')),
     el('aside', {class: 'settings-column', 'aria-label': '設定'},
      el('section', {class: 'settings-group', 'aria-label': 'Game設定'}, el('header', {}, 'Game'), displayPane(), rules),
      el('section', {class: 'settings-group', 'aria-label': 'Board設定'}, el('header', {}, 'Board ', el('span', {}, 'Day 1 · 昼')),
       pane('strategy', '戦略', strategyEditor(setup.strategy, value => { setup.strategy = value; render(); }))))),
    saved.length ? el('section', {class: 'panel history-panel'}, el('h2', {}, 'このブラウザーの履歴'),
     el('ul', {class: 'saved-list'}, saved.map(item => el('li', {},
      el('span', {}, castText(item.cast) + ` (${Object.keys(item.nodes).length} Board)`), el('span', {class: 'muted'}, new Date(item.created).toLocaleString('ja-JP')),
      el('button', {type: 'button', class: 'secondary', onclick: () => { location.hash = item.id; }}, '開く'),
      el('button', {type: 'button', class: 'secondary', onclick: async () => { if (confirm('この履歴を消します。元に戻せません。')) { await store('readwrite', games => games.delete(item.id)); render(); } }}, '消す'))))) : null),
   footer(el('a', {class: 'footer-help', href: '/help'}, 'HELP'), el('div', {class: 'phase-buttons'}, phaseButton('Day1・昼へ', {disabled: !valid, onclick: startGame})))];
 }

 // --- MAIN --------------------------------------------------------------------
 function draftColumn(state) {
  const acts = [];
  for (const player of state.alive) {
   const entry = draft[player] || {};
   if (entry.co && !state.claims[player]) acts.push({kind: 'co', player, role: entry.co});
   if (entry.target && (state.claims[player] || entry.co)) acts.push({kind: 'report', player, target: Number(entry.target), color: entry.color || 'white'});
  }
  return {kind: 'col', acts};
 }
 function logView(node, state) {
  const today = state.columns.filter(item => item.day === dayOf(node.log));
  const lines = item => {
   if (!item.event.acts.length) return el('div', {class: 'board-log-line'}, el('span', {class: 'board-log-token'}, '更新なし'));
   const byPlayer = new Map();
   for (const act of item.event.acts) { if (!byPlayer.has(act.player)) byPlayer.set(act.player, []); byPlayer.get(act.player).push(act); }
   return [...byPlayer].map(([player, acts]) => el('div', {class: 'board-log-line'},
    el('span', {class: 'board-log-token board-log-player'}, `Player${player}`), el('span', {}, 'が'),
    acts.map(act => el('span', {class: 'board-log-token'}, act.kind === 'co' ? `CO:${ROLE[act.role]}`
     : `${state.claims[player] === 'medium' ? '霊能' : '占い'} Day${item.day}:Player${act.target}=${COLOR[act.color]}`))));
  };
  return el('section', {class: 'board-log', 'aria-labelledby': 'system-log-title'},
   el('header', {}, el('h3', {id: 'system-log-title'}, 'BoardLog')),
   el('div', {class: 'board-log-list'}, today.map(item => el('div', {class: 'board-log-item'}, lines(item)))));
 }
 // As in v0.6: the first choice is the lowest numbered player the strategy can choose.
 function chosenTarget(node, kind) {
  if (target) return target;
  if (!kind || !node.result) return null;
  const players = node.result.branches.filter(branch => branch.event.kind === kind).map(branch => branch.event.player);
  return players.length ? Math.min(...players) : null;
 }
 function tableView(node, source, editable, state) {
  const roles = ['villager', 'medium', 'seer'].filter(role => game.cast[role]);
  const stage = source ? source.stage : null, kind = stage === 'closed' ? 'exec' : stage === 'night' ? 'bite' : null;
  const rates = node.result ? node.result.action_rates : {}, detail = roles.length > 1;
  const loading = () => el('span', {class: 'muted'}, '…');
  const village = row => addFractions(['villager', 'medium', 'seer'].map(role => row[role]));
  const rows = [], chosen = chosenTarget(node, kind);
  for (let player = 1; player <= players(); player++) {
   const alive = state.alive.has(player), row = source ? source.role_rates[player] : null, entry = draft[player] ||= {};
   const claim = state.claims[player], ends = source ? source.action_ends[player] : null, rate = rates[player];
   const statusCell = !alive ? el('span', {class: 'status dead'}, state.deaths[player])
    : kind ? el('button', {type: 'button', class: 'status-choice', disabled: !ends, 'aria-pressed': String(chosen === player), onclick: () => { target = player; render(); }},
     chosen === player ? `D${dayOf(node.log)} ${kind === 'exec' ? '処刑' : '襲撃'}` : '生存')
    : el('span', {class: 'status alive'}, '生存');
   const roleChoices = ['seer', 'medium'].filter(role => game.cast[role]), shownRole = claim || entry.co;
   rows.push(el('tr', {class: alive ? '' : 'executed', 'data-player': player},
    el('td', {class: 'index'}, String(player)),
    el('td', {class: 'player-name'}, `Player ${player}`),
    el('td', {'data-col': 'co'}, editable && alive && !claim
     ? el('select', {class: 'co-select', 'aria-label': `Player ${player}のCO`, onchange: event => { entry.co = event.target.value; render(); }},
      el('option', {value: ''}, '--'), roleChoices.map(role => el('option', {value: role, selected: entry.co === role}, ROLE[role])))
     : el('span', {}, claim ? ROLE[claim] : '--')),
    el('td', {class: 'village-text'}, row ? probability(village(row)) : loading()),
    detail && breakdown ? roles.map(role => el('td', {'data-role-detail': ''}, row ? probability(row[role]) : loading())) : null,
    el('td', {class: 'wolf-text'}, row ? probability(row.wolf) : loading()),
    el('td', {class: 'action-rates'}, ends ? [el('span', {class: 'village-text'}, probability(ends.village)), ' / ', el('span', {class: 'wolf-text'}, probability(ends.wolf))] : alive && kind ? '—' : ''),
    el('td', {class: 'action-rates'}, rate !== undefined ? [el('span', {class: 'village-text'}, probability(rate)), ' / ', el('span', {class: 'wolf-text'}, probability(complement(rate)))]
     : alive && kind ? el('span', {class: 'muted'}, node.result ? '—' : '未計算') : ''),
    el('td', {'data-col': 'status'}, statusCell)));
   // As in v0.6: a claimed role always shows its results, and today's report is entered on the same line.
   if (shownRole) {
    const past = state.columns.flatMap(item => item.event.acts.filter(act => act.kind === 'report' && act.player === player)
     .map(act => el('span', {class: 'co-day'}, `D${item.day} P${act.target}=${COLOR[act.color]}`)));
    const targets = Array.from({length: players()}, (_, i) => i + 1).filter(other => other !== player);
    rows.push(el('tr', {class: 'co-detail-row'}, el('td', {}), el('td', {colSpan: 7 + (detail && breakdown ? roles.length : 0)}, el('div', {class: 'co-line'},
     el('span', {class: 'co-role-label'}, ROLE[shownRole]),
     past.length ? el('div', {class: 'co-timeline'}, past) : null,
     editable && alive ? [el('select', {'aria-label': `Player ${player}の報告先`, onchange: event => { entry.target = event.target.value; render(); }},
       el('option', {value: ''}, '報告なし'), targets.map(other => el('option', {value: other, selected: Number(entry.target) === other}, `Player${other}`))),
      el('select', {'aria-label': `Player ${player}の報告の色`, onchange: event => { entry.color = event.target.value; render(); }},
       Object.keys(COLOR).map(color => el('option', {value: color, selected: (entry.color || 'white') === color}, COLOR[color])))] : !past.length ? el('span', {class: 'co-ability-note'}, '結果なし') : null))));
   }
  }
  const toggle = detail ? el('button', {type: 'button', class: 'role-breakdown-toggle', 'aria-expanded': String(breakdown), 'aria-label': '村陣営の役職内訳を開閉', onclick: () => { breakdown = !breakdown; render(); }},
   '村陣営 ', el('span', {'aria-hidden': 'true'}, breakdown ? '▾' : '▸')) : '村陣営';
  return el('div', {class: 'table-scroll'}, el('table', {class: 'player-table'},
   el('thead', {}, el('tr', {},
    el('th', {}, '#'), el('th', {}, '名前'), el('th', {'data-col': 'co'}, 'CO'), el('th', {}, toggle),
    detail && breakdown ? roles.map(role => el('th', {'data-role-detail': ''}, ROLE[role])) : null,
    el('th', {}, '人狼', el('small', {}, '狼陣営')), el('th', {}, '今日中勝率', el('small', {}, '村 / 狼')), el('th', {}, '期待勝率', el('small', {}, '村 / 狼')), el('th', {'data-col': 'status'}, '生死'))),
   el('tbody', {}, rows)));
 }
 function mainView() {
  const node = current(), state = publicState(node.log), source = node.result || node.read;
  const last = node.log[node.log.length - 1];
  const dayEnded = last && (last.kind === 'exec' || (last.kind === 'col' && !last.acts.length));
  const blocked = node.settled || isContradiction(node), editable = !blocked && !dayEnded;
  const running = calculating === node.id;
  const stage = source ? source.stage : null, kind = stage === 'closed' ? 'exec' : stage === 'night' ? 'bite' : null;
  const card = (cls, name, value) => el('div', {class: 'rate-card ' + cls}, el('small', {}, `${node.settled ? '最終勝率' : '現在勝率'} · ${name}`),
   value !== null ? el('strong', {class: 'probability', id: cls + '-rate'}, show(value)) : el('strong', {class: 'muted', id: cls + '-rate'}, running ? '計算中…' : '未計算'));
  const wolves = source && !node.settled ? Object.entries(source.alive_wolves).map(([count, p]) => [el('strong', {}, `${count}w `), probability(p), ' ']) : null;
  const information = el('section', {class: 'panel information-panel', id: 'information-panel', 'aria-labelledby': 'board-overview-title phase-title'},
   el('div', {class: 'information-head'},
    el('div', {}, el('p', {class: 'eyebrow', id: 'board-overview-title'}, 'BoardOverview'), el('h1', {id: 'phase-title'}, node.settled ? '決着結果' : phaseText(node.log)))),
   el('div', {class: 'overview-facts'}, el('span', {}, '生存 ', el('strong', {}, state.alive.size + '人')), wolves ? el('span', {}, '生存人狼 ', wolves) : null),
   el('div', {class: 'rate-cards'},
    card('village', '村陣営', node.settled ? node.ends.village : node.result ? node.result.win_rates.village : null),
    card('wolf', '狼陣営', node.settled ? node.ends.wolf : node.result ? node.result.win_rates.wolf : null)),
   node.settled ? el('p', {class: 'result-note'}, 'すべての可能性で決着しました。') : null,
   node.ends && !node.settled ? el('p', {class: 'hint'}, `この行動で決着: 村 ${show(node.ends.village)} / 狼 ${show(node.ends.wolf)}。上の値は決着しなかった場合です。`) : null,
   node.failure ? el('p', {class: isContradiction(node) ? 'error' : 'hint', role: 'alert'}, node.failure.message) : null,
   el('div', {class: 'calc-controls'},
    running ? el('button', {type: 'button', class: 'secondary', onclick: () => { cancelInflight(); backgroundPaused = true; render(); }}, '計算を止める') : null,
    !running && !blocked && (!node.result || !node.expanded) ? el('button', {type: 'button', class: 'secondary', onclick: () => { backgroundPaused = false; calculate(node); }}, '再計算') : null));
  const column = draftColumn(state), chosen = chosenTarget(node, kind);
  const player = blocked ? null : el('section', {class: 'panel player-panel', id: 'player-panel', 'aria-labelledby': 'players-title'},
   el('div', {class: 'panel-heading'}, el('h2', {class: 'board-section-label', id: 'players-title'}, 'BoardInfo'), el('span', {class: 'muted'}, '現在Boardの公開情報')),
   logView(node, state),
   el('div', {class: 'board-table-heading'}, el('h3', {class: 'board-child-title', id: 'board-table-title'}, 'BoardTable'),
    editable ? [el('button', {type: 'button', class: column.acts.length ? 'primary' : '', disabled: !column.acts.length, onclick: () => followEvent(node, column)}, '更新'),
     el('button', {type: 'button', class: 'secondary', onclick: () => followEvent(node, {kind: 'col', acts: []})}, '更新なし')] : null),
   tableView(node, source, editable, state),
   source && source.stage === 'open' && source.branches.length ? el('div', {class: 'update-list'}, el('span', {class: 'muted'}, '起こり得る更新:'),
    source.branches.map(branch => el('button', {type: 'button', class: 'secondary', onclick: () => followEvent(node, branch.event)}, `${eventLabel(branch.event)} (${show(branch.probability)})`))) : null);
  const strategy = editingStrategy || node.strategy, changed = !sameStrategy(strategy, node.strategy);
  const settings = el('aside', {class: 'settings-column', 'aria-label': '設定'},
   el('section', {class: 'settings-group', 'aria-label': 'Game設定'}, el('header', {}, 'Game'), displayPane(),
    pane('rules', 'ルール', el('p', {}, `自噛み: ${game.rules.self_bite ? 'あり' : 'なし'}`), el('p', {}, `初日の占い: ${{random_white: 'ランダム白', divine: 'あり', none: 'なし'}[game.rules.first_night]}`))),
   el('section', {class: 'settings-group', 'aria-label': 'Board設定'}, el('header', {}, 'Board ', el('span', {}, phaseText(node.log))),
    pane('strategy', '戦略', strategyEditor(strategy, value => { editingStrategy = value; render(); }),
     el('div', {class: 'strategy-apply-row'},
      el('button', {type: 'button', class: changed ? 'primary' : '', disabled: !changed, onclick: () => {
       const child = addChild(node, {label: '戦略を変更', strategy: editingStrategy, eventKey: 'strategy:' + Date.now()});
       node.open = true; select(child.id); }}, '更新'),
      changed ? el('button', {type: 'button', class: 'secondary', onclick: () => { editingStrategy = null; render(); }}, 'キャンセル') : null))));
  const tree = el('section', {class: 'panel tree-placeholder core-tree', id: 'tree-reserved', 'aria-label': 'GameTree'},
   el('h2', {class: 'board-section-label'}, 'GameTree'),
   el('figure', {class: 'tree-flow-frame flow-frame', tabIndex: 0, 'aria-label': 'GameTree Boardフローチャート・横スクロール可能'}));
  const jump = (id, text) => el('button', {type: 'button', onclick: () => document.getElementById(id)?.scrollIntoView()}, text);
  const parent = node.parent ? nodeOf(node.parent) : null;
  const previous = !parent ? el('button', {type: 'button', class: 'secondary settings-return', onclick: () => { cancelInflight(); location.hash = ''; }}, el('span', {'aria-hidden': 'true'}, '←'), ' ゲーム設定に戻る')
   : phaseButton(isNight(parent.log) === isNight(node.log) && dayOf(parent.log) === dayOf(node.log) ? '前のBoardへ' : `Day${dayOf(parent.log)}・${isNight(parent.log) ? '夜' : '昼'}へ`, {id: 'back-button', onclick: () => select(parent.id)}, true);
  const bar = footer(
   el('nav', {'aria-label': '画面内の移動'}, el('a', {class: 'footer-help', href: '/help'}, 'HELP'), jump('page-top', 'BoardOverview'), jump('player-panel', 'BoardInfo'), jump('tree-reserved', 'GameTree')),
   el('div', {class: 'phase-buttons'},
    !blocked && kind ? el('span', {'data-target-preview': ''}, `${kind === 'exec' ? '処刑' : '襲撃'}:${chosen ? 'Player' + chosen : '未選択'}`) : null,
    previous,
    !blocked ? phaseButton(kind === 'bite' ? `Day${dayOf(node.log) + 1}・昼へ` : `Day${dayOf(node.log)}・夜へ`, {id: 'advance-button', disabled: !chosen, onclick: () => followEvent(node, {kind, player: chosen})}) : null));
  return [el('main', {'data-screen': node.settled ? 'result' : 'main'},
   el('p', {class: 'cast-line', id: 'game-cast'}, el('span', {}, '配役'), ' ' + castText(game.cast)),
   el('div', {class: 'board-layout' + (Object.values(panes).some(Boolean) ? ' settings-open' : '')}, information, player, settings), tree), bar];
 }

 // --- render ------------------------------------------------------------------
 let renderId = 0;
 async function render() {
  const version = ++renderId;
  const frameBefore = app.querySelector('.tree-flow-frame'), scrollLeft = frameBefore ? frameBefore.scrollLeft : 0, scrollTop = frameBefore ? frameBefore.scrollTop : 0;
  const active = document.activeElement, focusLabel = active && active.getAttribute ? active.getAttribute('aria-label') : null;
  const view = game ? mainView() : await topView();
  if (version !== renderId) return;
  app.replaceChildren(...(flash ? [el('p', {class: 'error', role: 'alert'}, flash)] : []), ...view.filter(Boolean));
  const frame = app.querySelector('.tree-flow-frame');
  if (frame) { renderTree(frame); frame.scrollLeft = scrollLeft; frame.scrollTop = scrollTop; }
  document.title = (game ? (current().settled ? '決着画面' : phaseText(current().log)) : 'TOP') + ' | ww_gg';
  if (focusLabel) for (const node of app.querySelectorAll('[aria-label]')) if (node.getAttribute('aria-label') === focusLabel) { node.focus({preventScroll: true}); break; }
 }
 async function route() {
  const id = location.hash.slice(1);
  cancelInflight();
  game = id ? await store('readonly', games => games.get(id)) || null : null;
  draft = {}; editingStrategy = null; target = null; backgroundPaused = false;
  if (id && !game) { flash = 'この履歴は見つかりません。'; location.hash = ''; }
  await render();
  if (game) { const node = current(); if (!node.settled && !node.result && !node.failure) calculate(node); else next(); }
 }
 window.addEventListener('hashchange', route);
 window.addEventListener('pagehide', cancelInflight);
 openDb().then(database => { db = database; return route(); }).catch(error => {
  app.replaceChildren(el('p', {class: 'error', role: 'alert'}, '履歴の保存先を開けません: ' + error.message));
 });
})();
