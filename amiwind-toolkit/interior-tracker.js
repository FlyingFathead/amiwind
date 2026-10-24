// SPDX-License-Identifier: GPL-3.0-only
// The World Map's interior tracker (CHIM Progress Tracker, interiors): every interior cell of the game as a room with its
// state, from the tracker data's `interior_rooms` key (tools/cell_progress_rooms.py). Pure functions (no DOM): world-map.html
// puts the HTML they return in the foldable "Interior tracker" block under the map, the short counts in the side panel, and
// colours the exterior cells that hold an entrance on the "Interiors" layer. tests/test_interior_tracker.js runs them with
// node. Data without interiors (older tracker files) gives null / empty results, and the page hides the block.
(function (root) {
  // The states in legend order, and their colours (the chip colours of the list and the map layer).
  const STATES = ['on_chim_rooms', 'room_map', 'converted', 'not_started', 'hard_case', 'test_cell', 'teleport_only', 'no_entrance'];
  const COLOURS = {on_chim_rooms: '#7dffa6', room_map: '#46c37b', converted: '#6ea4df', not_started: '#3a4f66',
    hard_case: '#b07ae0', test_cell: '#8a96a8', teleport_only: '#e0a040', no_entrance: '#c2185b'};
  const LABELS = {on_chim_rooms: 'In the game on CHIM rooms', room_map: 'In the game as a room map', converted: 'Converted, not in the game yet',
    not_started: 'Not started', hard_case: 'Set aside: hard case', test_cell: 'Set aside: test cell', teleport_only: 'Set aside: teleport only',
    no_entrance: 'Set aside: no entrance, no script'};
  // The three groups of the legend.
  const GROUPS = [{id: 'in_game', label: 'In the game', states: ['on_chim_rooms', 'room_map']},
    {id: 'not_in_game', label: 'Not in the game yet', states: ['converted', 'not_started']},
    {id: 'set_aside', label: 'Set aside, with a reason', states: ['hard_case', 'test_cell', 'teleport_only', 'no_entrance']}];
  const ISLANDS = ['Vvardenfell', 'Solstheim', 'Mournhold'];
  const NO_ISLAND = 'none', NO_ISLAND_LABEL = 'No entrance area';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const num = v => Number(v || 0).toLocaleString('en-US');

  // The interiors section of a tracker document, or null (older data).
  function section(doc) {
    const ir = doc && doc.interior_rooms;
    return ir && Array.isArray(ir.rooms) ? ir : null;
  }
  const groupsOf = ir => (ir && ir.groups && ir.groups.length ? ir.groups : GROUPS);
  const labelOf = (ir, st) => (ir && ir.labels && ir.labels[st]) || LABELS[st] || st;
  const groupOfState = (ir, st) => (groupsOf(ir).find(g => g.states.includes(st)) || {}).id || 'not_in_game';
  // Rooms per group over every island: {in_game, not_in_game, set_aside, total}.
  function counts(ir) {
    const out = {total: 0};
    for (const g of groupsOf(ir)) out[g.id] = 0;
    for (const r of (ir && ir.rooms) || []) { out[groupOfState(ir, r.state)]++; out.total++; }
    return out;
  }
  // The title line of the block: always shown, folded or not.
  function titleLine(ir) {
    const c = counts(ir);
    return num(c.total) + ' rooms · ' + groupsOf(ir).map(g => g.label.replace(', with a reason', '').toLowerCase() + ' ' + num(c[g.id])).join(' · ');
  }
  const islandLabel = (ir, i) => i === NO_ISLAND ? NO_ISLAND_LABEL : ((ir && ir.islands && ir.islands[i]) || i);
  const batchText = b => b == null ? 'none (set aside)' : (typeof b === 'number' ? 'batch ' + b : String(b));
  // Where a room is entered from: the town or place of its exterior door, else the exterior cell.
  function entranceKey(r) {
    if (r.island === NO_ISLAND) return 'none';
    if (r.entrance) return 'cell:' + r.entrance;
    return 'script';
  }
  function entranceLabel(r) {
    if (r.island === NO_ISLAND) return NO_ISLAND_LABEL;
    if (r.entrance) return (r.settlement || r.region || 'Wilderness') + ' (cell ' + r.entrance.replace(',', ', ') + ')';
    return 'Reached by script (no exterior door)';
  }
  const roomText = (ir, r) => [r.name, r.id, r.island, islandLabel(ir, r.island), r.master, r.settlement, r.region, r.entrance, r.state,
    labelOf(ir, r.state), batchText(r.batch), ...(r.reasons || []).map(x => x.replace(/_/g, ' ')), r.our_map].filter(Boolean).join(' ').toLowerCase();
  // The rooms whose text holds every word of the query.
  function filter(ir, query) {
    const rooms = (ir && ir.rooms) || [];
    const toks = String(query || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
    return toks.length ? rooms.filter(r => { const t = roomText(ir, r); return toks.every(k => t.includes(k)); }) : rooms.slice();
  }
  // Islands in order (the data's keys may come back sorted): Vvardenfell, Solstheim, Mournhold, any other, no entrance area last.
  const islandRank = i => i === NO_ISLAND ? 99 : ISLANDS.includes(i) ? ISLANDS.indexOf(i) : 50;
  const islandOrder = (a, b) => islandRank(a) - islandRank(b) || a.localeCompare(b);
  // [{island, label, rooms, entrances: [{key, label, cell, rooms}]}]: islands in order, then the rooms with no entrance area
  // as their own group at the end; entrances by name, rooms by name.
  function grouped(ir, rooms) {
    const isl = new Map();
    for (const r of rooms) {
      const i = r.island || NO_ISLAND;
      if (!isl.has(i)) isl.set(i, new Map());
      const m = isl.get(i), k = entranceKey(r);
      if (!m.has(k)) m.set(k, {key: k, label: entranceLabel(r), cell: r.island !== NO_ISLAND && r.entrance ? r.entrance : null, rooms: []});
      m.get(k).rooms.push(r);
    }
    const order = [...isl.keys()].sort(islandOrder);
    const byName = (a, b) => a.name.localeCompare(b.name);
    return order.map(i => ({island: i, label: islandLabel(ir, i), rooms: [...isl.get(i).values()].reduce((n, e) => n + e.rooms.length, 0),
      entrances: [...isl.get(i).values()].sort((a, b) => (a.key === 'script') - (b.key === 'script') || a.label.localeCompare(b.label))
        .map(e => Object.assign(e, {rooms: e.rooms.sort(byName)}))}));
  }
  const chip = (ir, st) => '<span class="itchip" style="border-color:' + (COLOURS[st] || '#888') + '"><i style="background:' + (COLOURS[st] || '#888') + '"></i>' + esc(labelOf(ir, st)) + '</span>';
  function stateCounts(ir, rooms) {
    const c = {};
    for (const r of rooms) c[r.state] = (c[r.state] || 0) + 1;
    return STATES.filter(s => c[s]).map(s => '<span class="itn" title="' + esc(labelOf(ir, s)) + '"><i style="background:' + COLOURS[s] + '"></i>' + c[s] + '</span>').join('');
  }
  function roomRow(ir, r) {
    return '<tr data-room="' + esc(r.id) + '"' + (r.entrance && r.island !== NO_ISLAND ? ' data-cell="' + esc(r.entrance) + '" class="itgo" title="Show the entrance cell on the map"' : '') + '>' +
      '<td class="l">' + esc(r.name) + '</td><td class="l">' + chip(ir, r.state) + '</td><td class="l">' + esc(batchText(r.batch)) + '</td>' +
      '<td class="l">' + esc((r.reasons || []).map(x => x.replace(/_/g, ' ')).join(', ') || '–') + '</td><td class="l">' + esc(r.master || '') + '</td></tr>';
  }
  // The list under the map: island > entrance > rooms (each a <details>; all open while a query filters the list).
  function listHtml(ir, query) {
    const rooms = filter(ir, query), open = String(query || '').trim() ? ' open' : '';
    if (!rooms.length) return '<p class="muted">No room matches.</p>';
    const head = '<table class="mt itrooms"><thead><tr><th class="l">Room (cell ID)</th><th class="l">State</th><th class="l">Batch</th><th class="l">Reasons</th><th class="l">Master</th></tr></thead><tbody>';
    return '<p class="muted">' + num(rooms.length) + ' of ' + num(ir.rooms.length) + ' rooms. Click a room to show its entrance cell on the map.</p>' +
      grouped(ir, rooms).map(g => '<details class="itisland" data-island="' + esc(g.island) + '"' + open + '><summary><b>' + esc(g.label) + '</b> · ' + num(g.rooms) + ' rooms ' + stateCounts(ir, [].concat(...g.entrances.map(e => e.rooms))) +
        (g.island === NO_ISLAND ? ' <span class="muted">no door from any exterior leads to these; each keeps its own state</span>' : '') + '</summary>' +
        g.entrances.map(e => '<details class="itentrance"' + open + (e.cell ? ' data-cell="' + esc(e.cell) + '"' : '') + '><summary>' + esc(e.label) + ' · ' + e.rooms.length + ' ' + stateCounts(ir, e.rooms) + '</summary>' +
          head + e.rooms.map(r => roomRow(ir, r)).join('') + '</tbody></table></details>').join('') + '</details>').join('');
  }
  // The side panel: per island, one line of the three groups (short; the list under the map is the main view).
  function overviewHtml(ir) {
    if (!ir) return '';
    const head = ir.headline || {}, gs = groupsOf(ir);
    const rows = Object.keys(head).sort(islandOrder).map(i => '<tr><td class="l">' + esc(islandLabel(ir, i)) + '</td><td>' + num(head[i].total) + '</td>' +
      gs.map(g => '<td>' + num((head[i].groups || {})[g.id] != null ? head[i].groups[g.id] : g.states.reduce((n, s) => n + (head[i][s] || 0), 0)) + '</td>').join('') + '</tr>').join('');
    return '<h3>Interiors</h3><p class="muted">' + esc(titleLine(ir)) + '. The room list is under the map (Interior tracker).</p>' +
      '<table class="mt"><thead><tr><th class="l">Island</th><th>Rooms</th>' + gs.map(g => '<th>' + esc(g.label.replace(', with a reason', '')) + '</th>').join('') + '</tr></thead><tbody>' + rows + '</tbody></table>';
  }
  // The exterior cells that hold an entrance: 'x,y' -> {rooms, states: {state: n}, state (the most common; a tie goes to the
  // state further from the game), colour}.
  function entranceCells(ir) {
    const out = new Map();
    for (const r of (ir && ir.rooms) || []) {
      if (!r.entrance || r.island === NO_ISLAND) continue;
      const e = out.get(r.entrance) || {rooms: 0, states: {}};
      e.rooms++; e.states[r.state] = (e.states[r.state] || 0) + 1; out.set(r.entrance, e);
    }
    for (const e of out.values()) {
      let best = null;
      for (const s of STATES) if (e.states[s] && (best == null || e.states[s] >= e.states[best])) best = s;
      e.state = best; e.colour = COLOURS[best];
    }
    return out;
  }
  // Legend rows of the Interiors layer: [colour, text].
  const legendRows = ir => STATES.map(s => [COLOURS[s], labelOf(ir, s)]);
  const api = {STATES, COLOURS, LABELS, GROUPS, NO_ISLAND, section, counts, titleLine, filter, grouped, listHtml, overviewHtml, entranceCells, legendRows, batchText};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindInteriors = api;
})(typeof window !== 'undefined' ? window : this);
