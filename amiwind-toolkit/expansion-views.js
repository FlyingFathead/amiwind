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
  const ISLAND_NAMES = {1: 'Vvardenfell', 2: 'Solstheim'};
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
  const roomGroup = r => r.group || ({on_chim_rooms: 'in_game', room_map: 'in_game', converted: 'not_in_game', not_started: 'not_in_game'}[r.state] || 'set_aside');
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
  const isDistrict = r => (r.reasons || []).includes('behaves_exterior');

  // ---- completion per expansion, beside the base game ----------------------------------------------------------------
  // {id, label, present, done, partial, missing, total, rate, cells, rooms} for the base game, Bloodmoon and Tribunal; an
  // expansion with no cells and no rooms in the data is `present: false` (the page hides it).
  function completion(doc) {
    const ext = exteriorCounts(doc), cells = {base: zero(), bloodmoon: zero(), tribunal: zero()}, rooms = {base: [], bloodmoon: [], tribunal: []};
    for (const i of ext.islands) {
      const set = cells[i.island === SOLSTHEIM ? 'bloodmoon' : 'base'];
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
    const mr = mournholdRooms(doc);
    if (mr.length) {
      const rc = roomCounts(mr);
      out.push({id: MOURNHOLD, label: 'Mournhold', sub: 'Tribunal', kind: 'rooms', unit: 'rooms', counts: rc,
        text: countText(rc) + ' of ' + num(rc.total) + ' rooms' + (rc.set_aside ? ' (' + num(rc.set_aside) + ' set aside, counted as missing)' : '')});
    }
    return out;
  }
  // The view to show: the wanted one when it exists in the data, else the first.
  function pick(list, want) { return (list.find(v => v.id === want) || list[0] || {}).id || null; }

  // ---- the Mournhold screen ------------------------------------------------------------------------------------------
  // Districts as large tiles in a row (wrapping), then every other room as a small square, ordered by state then name. Tiles
  // are {x, y, w, h, room, district}; `height` is the total.
  const DISTRICT_W = 150, DISTRICT_H = 64, ROOM = 14, GAP = 4, PAD = 8, HEAD = 22;
  const STATE_ORDER = ['on_chim_rooms', 'room_map', 'converted', 'not_started', 'hard_case', 'test_cell', 'teleport_only', 'no_entrance'];
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

  const api = {WORLD, MOURNHOLD, counted, cellClass, exteriorCounts, roomClass, roomCounts, roomSet, mournholdRooms, isDistrict, completion, bloodmoonRooms, inPane, paneBounds,
    countText, rateText, views, pick, mournholdLayout, hit, DISTRICT_W, DISTRICT_H, ROOM};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindViews = api;
})(typeof window !== 'undefined' ? window : this);
