// SPDX-License-Identifier: GPL-3.0-only
// The World Map's expansion views (CHIM Progress Tracker): Solstheim shares the exterior grid with Vvardenfell, Mournhold has no
// exterior of its own and gets a map screen of its own (its districts and rooms). Pure functions (no DOM): world-map.html draws
// what they return. tests/test_expansion_views.js runs them with node. Everything is derived from the tracker data that is
// loaded (cells with an island, `interior_rooms`): a build whose data holds no Bloodmoon or Tribunal content has no such view.
//
// Three counts everywhere: done (in the game and passed), partial (converted somewhere, not done or not in the game yet),
// missing (the rest; rooms set aside count as missing, and are named in the text).
(function (root) {
  const WORLD = 'world', MOURNHOLD = 'mournhold';
  const DONE_STATES = new Set(['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested',
    'audits_passed', 'sea_in_game']);
  const PARTIAL_STATES = new Set(['converted_unmeasured', 'converted_failing', 'hull_policy_pending', 'not_in_build']);
  const DONE_BUCKETS = new Set(['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested',
    'audits_passed', 'empty_sea']);
  const SOLSTHEIM = 2;
  // Mournhold's districts as the presented data folder gives them: exterior cells of island 3 (tools/cell_progress.py
  // MOURNHOLD_ISLAND, chim-head.js LANDS), counted as Mournhold's cells beside its rooms, never as Vvardenfell's.
  const MOURNHOLD_ISLAND = 3;
  const ISLAND_NAMES = {1: 'Vvardenfell', 2: 'Solstheim', 3: 'Mournhold'};
  const num = v => Number(v || 0).toLocaleString('en-US');
  const rate = (done, total) => total ? Math.round(1000 * done / total) / 10 : 0;
  const zero = () => ({done: 0, partial: 0, missing: 0, total: 0, rate: 0});
  function close(c) { c.total = c.done + c.partial + c.missing; c.rate = rate(c.done, c.total); return c; }
  function add(c, kind) { c[kind]++; return c; }

  // ---- exterior cells (the grid) -------------------------------------------------------------------------------------
  // A cell of an island's map: land, empty sea or sea in the game; the open ocean and the settled squares beyond the world's
  // edge are not counted (the tracker never counts them as done or as work left).
  function counted(c) {
    if (!c || !c.chim) return false;
    const st = c.chim.state, b = c.chim.bucket;
    if (st === 'settled' || st === 'ocean' || b === 'ocean') return false;
    return !!c.land || b === 'empty_sea' || st === 'sea_in_game';
  }
  // done / partial / missing of one cell. Grouped data (chim.state) says where the cell stands in the newest build; older data
  // has the audit bucket only. A Solstheim cell that has a CHIM conversion but is not in the build yet is partial; without one it
  // is missing, whatever the audits of an old run said.
  function cellClass(c) {
    const ch = c.chim, st = ch.state;
    if (st) {
      if (DONE_STATES.has(st)) return 'done';
      if (PARTIAL_STATES.has(st)) return 'partial';
      if (st === 'solstheim') return ch.converted ? 'partial' : 'missing';
      return 'missing';
    }
    if (DONE_BUCKETS.has(ch.bucket)) return 'done';
    return ch.converted ? 'partial' : 'missing';
  }
  const islandName = (doc, i) => {
    const row = ((doc && doc.headline && doc.headline.islands) || []).find(r => r.island === i);
    return (row && row.name) || ISLAND_NAMES[i] || ('island ' + i);
  };
  // {islands: [{island, name, done, partial, missing, total, rate}], total} over the counted cells with an island.
  function exteriorCounts(doc) {
    const by = new Map(), all = zero();
    for (const c of Object.values((doc && doc.cells) || {})) {
      if (!counted(c) || !c.island) continue;
      if (!by.has(c.island)) by.set(c.island, Object.assign(zero(), {island: c.island, name: islandName(doc, c.island)}));
      const k = cellClass(c);
      add(by.get(c.island), k); add(all, k);
    }
    const islands = [...by.values()].sort((a, b) => a.island - b.island).map(close);
    return {islands, total: close(all)};
  }

  // ---- rooms (the interiors) -----------------------------------------------------------------------------------------
  // No room is set aside (ROOMS-SET-ASIDE-NOT-BUILT-67): a room no door leads to is a room to build, a district built as
  // open terrain is in the game; only a state this page does not know falls to "set aside".
  // ROOM_GROUP is tools/cell_progress_rooms.py GROUPS by state; its in-game states are also the ready rooms of the
  // readiness count below (READY_ROOM_STATES), so a green tile and the count never disagree (TRACKER-ROOM-MAPS-NOT-READY-67).
  const ROOM_GROUP = {on_chim_rooms: 'in_game', room_map: 'in_game', district: 'in_game', converted: 'not_in_game',
    not_started: 'not_in_game', test_cell: 'not_in_game', teleport_only: 'not_in_game', no_entrance: 'not_in_game'};
  const roomGroup = r => r.group || ROOM_GROUP[r.state] || 'set_aside';
  function roomClass(r) {
    if (roomGroup(r) === 'in_game') return 'done';
    return r.state === 'converted' ? 'partial' : 'missing';
  }
  function roomCounts(rooms) {
    const c = zero();
    c.set_aside = 0;
    for (const r of rooms) { add(c, roomClass(r)); if (roomGroup(r) === 'set_aside') c.set_aside++; }
    return close(c);
  }
  // The expansion a room belongs to: by its master file, else by its island.
  function roomSet(r) {
    if (r.master === 'Tribunal.esm' || r.island === 'Mournhold') return 'tribunal';
    if (r.master === 'Bloodmoon.esm' || r.island === 'Solstheim') return 'bloodmoon';
    return 'base';
  }
  const roomsOf = doc => (doc && doc.interior_rooms && Array.isArray(doc.interior_rooms.rooms)) ? doc.interior_rooms.rooms : [];
  const mournholdRooms = doc => roomsOf(doc).filter(r => roomSet(r) === 'tribunal');
  // A district of Mournhold: an interior cell that acts like an exterior (the door graph's `behaves_exterior` reason).
  const isDistrict = r => r.state === 'district' || !!r.behaves_exterior || (r.reasons || []).includes('behaves_exterior');

  // ---- completion per expansion, beside the base game ----------------------------------------------------------------
  // {id, label, present, done, partial, missing, total, rate, cells, rooms} for the base game, Bloodmoon and Tribunal; an
  // expansion with no cells and no rooms in the data is `present: false` (the page hides it).
  function completion(doc) {
    const ext = exteriorCounts(doc), cells = {base: zero(), bloodmoon: zero(), tribunal: zero()}, rooms = {base: [], bloodmoon: [], tribunal: []};
    for (const i of ext.islands) {
      const set = cells[i.island === SOLSTHEIM ? 'bloodmoon' : i.island === MOURNHOLD_ISLAND ? 'tribunal' : 'base'];
      for (const k of ['done', 'partial', 'missing']) set[k] += i[k];
      close(set);
    }
    for (const r of roomsOf(doc)) rooms[roomSet(r)].push(r);
    const labels = {base: 'Vvardenfell (base game)', bloodmoon: 'Solstheim (Bloodmoon)', tribunal: 'Mournhold (Tribunal)'};
    return ['base', 'bloodmoon', 'tribunal'].map(id => {
      const rc = roomCounts(rooms[id]), cc = cells[id];
      const row = {id, label: labels[id], cells: cc, rooms: rc,
        done: cc.done + rc.done, partial: cc.partial + rc.partial, missing: cc.missing + rc.missing};
      row.total = row.done + row.partial + row.missing; row.rate = rate(row.done, row.total);
      row.present = row.total > 0;
      return row;
    });
  }
  const countText = c => 'done ' + num(c.done) + ' · partial ' + num(c.partial) + ' · missing ' + num(c.missing);
  function rateText(row) { return row.label + ': ' + row.rate.toFixed(1) + ' % (' + num(row.done) + ' of ' + num(row.total) + ')'; }

  // ---- the views -----------------------------------------------------------------------------------------------------
  // [{id, label, kind, counts, text}] in order; the map view always (with Solstheim in its name when the data has it), the
  // Mournhold view only when the data has Tribunal rooms.
  // Three panes, one per map: Vvardenfell (the base game), Solstheim (Bloodmoon: the same grid framed on the island, with its
  // rooms) and Mournhold (Tribunal: a screen of its own). Each pane has its own counts; a pane whose content the data lacks is
  // not offered.
  const bloodmoonRooms = doc => roomsOf(doc).filter(r => roomSet(r) === 'bloodmoon');
  const PANE_ISLAND = {vvardenfell: 1, solstheim: SOLSTHEIM};
  // Is a cell drawn and counted in a map pane (island 1 also takes the cells with no island, which the counts skip)?
  const inPane = (c, pane) => pane === WORLD || (PANE_ISLAND[pane] === 1 ? !c.island || c.island === 1 : c.island === PANE_ISLAND[pane]);
  // The cell box [x0, y0, x1, y1] of a map pane, or null.
  function paneBounds(doc, pane) {
    let b = null;
    for (const c of Object.values((doc && doc.cells) || {})) {
      if (!inPane(c, pane) || typeof c.x !== 'number') continue;
      b = b ? [Math.min(b[0], c.x), Math.min(b[1], c.y), Math.max(b[2], c.x), Math.max(b[3], c.y)] : [c.x, c.y, c.x, c.y];
    }
    return b;
  }
  function views(doc) {
    const out = [], ext = exteriorCounts(doc);
    const isl = id => ext.islands.find(i => i.island === id);
    const vv = isl(1), so = isl(SOLSTHEIM);
    if (vv && vv.total) out.push({id: 'vvardenfell', label: 'Vvardenfell', sub: 'base game', kind: 'cells', unit: 'cells', counts: vv,
      text: countText(vv) + ' of ' + num(vv.total) + ' cells'});
    const br = bloodmoonRooms(doc);
    if ((so && so.total) || br.length) {
      const rc = roomCounts(br), c = so || zero();
      out.push({id: 'solstheim', label: 'Solstheim', sub: 'Bloodmoon', kind: 'cells', unit: 'cells', counts: c, rooms: rc,
        text: countText(c) + ' of ' + num(c.total) + ' cells' + (rc.total ? ' · rooms: ' + countText(rc) + ' of ' + num(rc.total) : '')});
    }
    const mr = mournholdRooms(doc), mc = isl(MOURNHOLD_ISLAND);
    if (mr.length || (mc && mc.total)) {
      const rc = roomCounts(mr);
      out.push({id: MOURNHOLD, label: 'Mournhold', sub: 'Tribunal', kind: 'rooms', unit: 'rooms', counts: rc,
        ...(mc && mc.total ? {cells: mc} : {}),
        text: countText(rc) + ' of ' + num(rc.total) + ' rooms' + (rc.set_aside ? ' (' + num(rc.set_aside) + ' set aside, counted as missing)' : '') +
          (mc && mc.total ? ' · cells: ' + countText(mc) + ' of ' + num(mc.total) : '')});
    }
    return out;
  }
  // The view to show: the wanted one when it exists in the data, else the first.
  function pick(list, want) { return (list.find(v => v.id === want) || list[0] || {}).id || null; }

  // ---- the Mournhold screen ------------------------------------------------------------------------------------------
  // Districts as large tiles in a row (wrapping), then every other room as a small square, ordered by state then name. Tiles
  // are {x, y, w, h, room, district}; `height` is the total.
  const DISTRICT_W = 150, DISTRICT_H = 64, ROOM = 14, GAP = 4, PAD = 8, HEAD = 22;
  const STATE_ORDER = ['on_chim_rooms', 'room_map', 'district', 'converted', 'not_started', 'test_cell', 'teleport_only', 'no_entrance', 'hard_case'];
  const stateRank = s => { const i = STATE_ORDER.indexOf(s); return i < 0 ? STATE_ORDER.length : i; };
  function mournholdLayout(rooms, width) {
    const w = Math.max(width || 600, DISTRICT_W + 2 * PAD);
    const districts = rooms.filter(isDistrict).sort((a, b) => stateRank(a.state) - stateRank(b.state) || a.name.localeCompare(b.name));
    const rest = rooms.filter(r => !isDistrict(r)).sort((a, b) => stateRank(a.state) - stateRank(b.state) || a.name.localeCompare(b.name));
    const tiles = [];
    let x = PAD, y = PAD + HEAD;
    const heads = {districts: {y: PAD, text: 'Districts that act like an exterior'}};
    for (const r of districts) {
      if (x + DISTRICT_W > w - PAD && x > PAD) { x = PAD; y += DISTRICT_H + GAP; }
      tiles.push({x, y, w: DISTRICT_W, h: DISTRICT_H, room: r, district: true});
      x += DISTRICT_W + GAP;
    }
    if (districts.length) y += DISTRICT_H + GAP * 3; else y = PAD;
    heads.rooms = {y, text: 'Rooms'};
    y += HEAD; x = PAD;
    for (const r of rest) {
      if (x + ROOM > w - PAD && x > PAD) { x = PAD; y += ROOM + GAP; }
      tiles.push({x, y, w: ROOM, h: ROOM, room: r, district: false});
      x += ROOM + GAP;
    }
    if (!districts.length) delete heads.districts;
    return {width: w, height: y + (rest.length ? ROOM : 0) + PAD, tiles, heads};
  }
  function hit(layout, px, py) {
    for (const t of layout.tiles) if (px >= t.x && px < t.x + t.w && py >= t.y && py < t.y + t.h) return t;
    return null;
  }

  // ---- the unified readiness count per land (TOOLKIT-EXPANSION-COMPLETION-67) ---------------------------------------
  // The tracker ingest writes it (tools/master_completion.py readiness(), the data's `readiness` key) and every view draws
  // that. Older data without the key: computeReadiness() counts it here by the same rules, and tests/test_master_completion.py
  // checks that both give the same numbers on the same data. Ready = in the game on CHIM, the same for every land.
  // -2: a room map of our own counts ready and is named as a special interior; data written as -1 is counted again here
  const READY_FORMAT = 'aw-land-readiness-2';
  const LANDS = [{id: 'vvardenfell', name: 'Vvardenfell', game: 'Morrowind (main game)', master: 'Morrowind.esm', island: 1},
    {id: 'solstheim', name: 'Solstheim', game: 'Bloodmoon', master: 'Bloodmoon.esm', island: 2},
    {id: 'mournhold', name: 'Mournhold', game: 'Tribunal', master: 'Tribunal.esm', island: 3}];
  const READY_TEXT = 'Ready = in the game on CHIM, the same for every land. Open terrain: the land\'s exterior cells of land or ' +
    'empty sea (open ocean and cells beyond the world\'s edge are not counted), ready when the newest ingested ' +
    'build holds the cell on CHIM and no audit of it failed. Rooms: every interior cell, counted for the land ' +
    'of its master, ready when it is in the game: on CHIM rooms, or as a room map of our own (special ' +
    'interiors, named under the count); a district the land presents as open terrain is counted once, under ' +
    'open terrain. Everything else is not ready, with its reason; a room no door leads to is a room still to ' +
    'build, never left out.';
  const CELL_REASONS = {solstheim: 'not in the game yet (Solstheim)', not_started: 'not started',
    not_in_build: 'converted, not in the newest build', empty_sea: 'empty sea, not in the newest build',
    ocean: 'open sea, not in the newest build', converted_failing: 'converted, failing audits',
    not_converted: 'not converted (tried, could not finish)', hull_policy_pending: 'hull policy pending'};
  // as tools/master_completion.py READY_ROOM_STATES: the in-game states of ROOM_GROUP (on CHIM rooms, a room map of our
  // own, a district); SPECIAL_ROOM_STATES: the ready rooms named as special interiors, never a reason
  const READY_ROOM_STATES = Object.keys(ROOM_GROUP).filter(s => ROOM_GROUP[s] === 'in_game');
  const SPECIAL_ROOM_STATES = ['room_map'];
  const SPECIAL_TEXT = 'special interiors, in the game as room maps of our own';
  const ROOM_REASONS = {converted: 'converted, not in the game yet',
    not_started: 'not started',
    teleport_only: 'still to build: no door leads there, a script or a dialogue line sends the player there',
    no_entrance: 'still to build: no door leads there, and no script or dialogue line names it',
    test_cell: 'still to build: no door leads there, a developers\' test cell', hard_case: 'still to build: set aside as a hard case'};
  const LEADS = {door: 'a door', teleport: 'a door from a room that a script or a dialogue line sends the player to',
    teleport_only: 'a script or a dialogue line sends the player there; no door leads in',
    unreachable: 'nothing found: no door, and no script or dialogue line names it'};
  // one decimal, rounded half up on whole numbers (as tools/master_completion.py pct)
  const readyPct = (r, t) => t ? Math.floor((2000 * r + t) / (2 * t)) / 10 : 0;
  const figure = (r, t) => ({ready: r, total: t, percent: readyPct(r, t)});
  const cmp = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  function landOfRoom(r) {
    if (r.master === 'Tribunal.esm' || r.island === 'Mournhold') return 'mournhold';
    if (r.master === 'Bloodmoon.esm' || r.island === 'Solstheim') return 'solstheim';
    return 'vvardenfell';
  }
  const terrainCounted = c => !!(c && c.island) && (!!c.land || (c.chim || {}).bucket === 'empty_sea');
  const cellReady = c => (c.chim || {}).group === 'in_game';
  function reasonRows(rows, labels) {
    const order = Object.keys(labels), by = new Map();
    for (const [reason, item] of rows) { if (!by.has(reason)) by.set(reason, []); by.get(reason).push(item); }
    const rank = k => { const i = order.indexOf(k); return i < 0 ? order.length : i; };
    return [...by.entries()].sort((a, b) => rank(a[0]) - rank(b[0]) || cmp(a[0], b[0])).map(([k, v]) => ({reason: k,
      label: labels[k] || k.replace(/_/g, ' '), count: v.length, items: v.sort((a, b) => cmp(a.name || '', b.name || '') || cmp(a.id, b.id))}));
  }
  function computeReadiness(doc) {
    const cells = (doc && doc.cells) || {}, rooms = roomsOf(doc), names = {};
    const lands = LANDS.map(land => {
      const mine = Object.entries(cells).filter(([, c]) => c.island === land.island && terrainCounted(c));
      names[land.id] = new Set(mine.filter(([, c]) => c.name).map(([, c]) => String(c.name).toLowerCase()));
      const ready = mine.filter(([, c]) => cellReady(c)).length;
      const notReady = reasonRows(mine.filter(([, c]) => !cellReady(c)).map(([k, c]) => [(c.chim || {}).state || 'not_started', {id: k, name: c.name || ''}]), CELL_REASONS);
      return {id: land.id, name: land.name, game: land.game, master: land.master, island: land.island, terrain: Object.assign(figure(ready, mine.length), {not_ready: notReady})};
    });
    for (const land of lands) {
      const rs = rooms.filter(r => landOfRoom(r) === land.id), terr = names[land.id];
      const asTerrain = rs.filter(r => terr.has(String(r.name).toLowerCase())).map(r => r.name).sort(cmp);
      const counted = rs.filter(r => !terr.has(String(r.name).toLowerCase()));
      const ready = counted.filter(r => READY_ROOM_STATES.includes(r.state)).length;
      const notReady = reasonRows(counted.filter(r => !READY_ROOM_STATES.includes(r.state)).map(r => [r.state || 'not_started',
        {id: r.id, name: r.name, access: r.access == null ? null : r.access, leads: LEADS[r.access || ''] || r.access || '', reasons: (r.reasons || []).slice()}]), ROOM_REASONS);
      const special = counted.filter(r => SPECIAL_ROOM_STATES.includes(r.state)).map(r => r.name).sort(cmp);
      land.rooms = Object.assign(figure(ready, counted.length), {not_ready: notReady, as_terrain: asTerrain, special});
      land.total = figure(land.terrain.ready + land.rooms.ready, land.terrain.total + land.rooms.total);
    }
    const all = {};
    for (const k of ['terrain', 'rooms', 'total']) all[k] = figure(lands.reduce((n, l) => n + l[k].ready, 0), lands.reduce((n, l) => n + l[k].total, 0));
    return {format: READY_FORMAT, definition: READY_TEXT, lands, all, build: ((doc && doc.headline) || {}).in_game_label == null ? null : doc.headline.in_game_label};
  }
  // The data's own readiness when the ingest wrote it, else counted here by the same rules; null without tracker data.
  function readiness(doc) {
    if (!doc) return null;
    if (doc.readiness && doc.readiness.format === READY_FORMAT) return doc.readiness;
    return doc.cells ? computeReadiness(doc) : null;
  }
  // The land of a room for the room list (interior-tracker.js listHtml opts.byLand): its land's name, and whether it is
  // one of the districts counted as open terrain.
  function landGrouping(ready) {
    const asTerrain = new Set(), label = {};
    for (const l of (ready && ready.lands) || []) { label[l.id] = l.name; for (const n of (l.rooms && l.rooms.as_terrain) || []) asTerrain.add(n); }
    return {landOf: r => ({key: label[landOfRoom(r)] || landOfRoom(r), label: label[landOfRoom(r)] || landOfRoom(r)}), asTerrain,
      counts: Object.fromEntries(((ready && ready.lands) || []).map(l => [l.name, l.rooms]))};
  }

  const api = {WORLD, MOURNHOLD, counted, cellClass, exteriorCounts, roomClass, roomCounts, roomSet, mournholdRooms, isDistrict, completion, bloodmoonRooms, inPane, paneBounds,
    countText, rateText, views, pick, mournholdLayout, hit, DISTRICT_W, DISTRICT_H, ROOM,
    READY_FORMAT, LANDS, READY_TEXT, READY_ROOM_STATES, SPECIAL_ROOM_STATES, SPECIAL_TEXT, landOfRoom, readiness, computeReadiness,
    readyPct, landGrouping};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindViews = api;
})(typeof window !== 'undefined' ? window : this);
