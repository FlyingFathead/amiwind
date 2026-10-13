// SPDX-License-Identifier: GPL-3.0-only
// The World Map's legend filter for the CHIM Progress Tracker: which legend rows are ticked, the preset pull-down, the
// release (version) filter and the compare layer. Pure functions (no DOM): world-map.html draws the controls and calls these,
// and tests/test_cell_progress.py runs them with node. A row that is unticked DIMS its cells (the same dimming the status
// chips and the "Show" filter use), so the island stays readable around what you picked.
(function (root) {
  // Every CHIM status, in legend order. Keys of the legend rows are 'chim:status:<status>'.
  const STATUSES = ['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested',
    'audits_passed', 'converted_failing', 'not_converted', 'converted_unmeasured', 'not_started', 'empty_sea', 'hull_policy_pending', 'ocean'];
  // Eligible for the next release: every passed status plus empty and open sea (tools/cell_progress.py ELIGIBLE_SELECT).
  const ELIGIBLE = ['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested', 'audits_passed', 'empty_sea'];
  const AWAITING = ['complete_unlit', 'terrain_complete_unlit'];
  const PROBLEMS = ['converted_failing', 'not_converted', 'hull_policy_pending'];
  const statusKey = s => 'chim:status:' + s;
  const STORE = 'amiwind-chim-legend-1';
  // The map viewport (TOOLKIT-MAP-SCALING-36). The canvas fills the stage width and the window height below the controls (never
  // under MAP_MIN_H); the whole island fits it at zoom 1 (f = CSS pixels per base map pixel); the view (z, x, y) is kept in base
  // map pixels of a "virtual canvas" vw x vh, so pan, zoom and hit tests need no other scale. No inner scrollbars.
  const MAP_MIN_H = 420, MAP_MIN_W = 160, MIN_ZOOM = 0.2, MAX_ZOOM = 16, RING_LABEL_MIN_PX = 24;
  function mapLayout(availW, innerH, docTop, g, dpr) {
    const cssW = Math.max(MAP_MIN_W, Math.floor(availW) || MAP_MIN_W);
    const room = Math.floor(innerH - docTop - 12);
    const cssH = Math.max(MAP_MIN_H, Number.isFinite(room) ? room : MAP_MIN_H);
    const f = g.w > 0 && g.h > 0 ? Math.min(cssW / g.w, cssH / g.h) : 1;
    return {cssW, cssH, f, vw: cssW / f, vh: cssH / f, ratio: f * (dpr || 1)};
  }
  // Keep the map inside the viewport: smaller than it, it is centred; larger, it cannot be dragged off its edges.
  function clampView(v, g, vw, vh) {
    v.z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, v.z));
    const mw = g.w * v.z, mh = g.h * v.z;
    v.x = mw <= vw ? (vw - mw) / 2 : Math.min(0, Math.max(vw - mw, v.x));
    v.y = mh <= vh ? (vh - mh) / 2 : Math.min(0, Math.max(vh - mh, v.y));
    return v;
  }
  // Zoom by factor f around the point (cx, cy) of the virtual canvas (the cursor, or the viewport centre for the buttons).
  function zoomAt(v, f, cx, cy, g, vw, vh) {
    const z = v.z;
    v.z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z * f));
    v.x = cx - (cx - v.x) * v.z / z; v.y = cy - (cy - v.y) * v.z / z;
    return clampView(v, g, vw, vh);
  }
  function fitView(v, g, vw, vh) { v.z = 1; v.x = v.y = 0; return clampView(v, g, vw, vh); }
  const ringLabelsVisible = cellPx => cellPx >= RING_LABEL_MIN_PX;
  // The release plan (tools/cell_progress_plan.py): cell.plan = {release, state, since, source, tier, ...any other key}.
  // tier: 'next' = planned for the upcoming release (the lowest plan release that has not shipped), 'later' = a release after
  // that, 'shipped'. Gold is the gold of the Toolkit header (header.js h1), so it always means "planned for the next release".
  const PLAN_GOLD = '#e8c46a', PLAN_LATER = '#f6ebc4';
  // Open ocean cells (no LAND, one shared ocean chunk): drawn silver, never counted as done (TRACKER-OCEAN-COUNTED-DONE-36).
  const OCEAN_SILVER = '#c0c6cc', OCEAN_TEXT = 'Open ocean: shared ocean chunk made, not yet placed in the game';
  const PLAN_CORE = ['release', 'state', 'since', 'source', 'tier'];
  const planTier = c => (c.plan && c.plan.tier) || null;
  const planColour = c => planTier(c) === 'next' ? PLAN_GOLD : planTier(c) === 'later' ? PLAN_LATER : null;
  // The legend rows of the plan colouring, generated from the data; empty without a plan ("when available").
  // Each row: [colour, text, key].
  function planRows(plans) {
    const rel = (plans || []).filter(r => r.release && !r.shipped && !r.documentation_only);
    if (!rel.length) return [];
    const rows = [];
    for (const r of rel) {
      rows.push([r.next ? PLAN_GOLD : PLAN_LATER, 'Planned for ' + r.release + (r.next ? ' (next release)' : ' (later)') + ': ' + r.planned.toLocaleString() + ' cells',
        r.next ? 'chim:plan:next' : 'chim:plan:later']);
    }
    return rows.filter((r, i) => rows.findIndex(x => x[2] === r[2]) === i);
  }
  // Per-release count rows plus a TOTALS row: [name, state, planned, complete, awaiting lighting, failing, hull pending, not started, open ocean].
  function planTable(plans, oceanTotal) {
    const rows = (plans || []).filter(r => r.release).map(r => [r.release + (r.title ? ' - ' + r.title : ''),
      r.documentation_only ? 'documentation only' : r.shipped ? 'shipped' : r.next ? 'next' : 'later', r.planned, r.complete, r.awaiting_lighting, r.failing, r.hull_policy_pending, r.not_started, r.ocean || 0]);
    if (!rows.length) return [];
    const tot = ['TOTALS', ''];
    for (let i = 2; i < 9; i++) tot.push(rows.reduce((a, r) => a + r[i], 0));
    const out = rows.concat([tot]);
    // The open ocean has a totals row of its own: island-wide, silver, and not part of the done figures above.
    if (oceanTotal != null) out.push(['OPEN OCEAN (silver, not counted as done)', '', '', '', '', '', '', '', oceanTotal]);
    return out;
  }
  // One text line for the cell panel: every key of the plan record is shown, unknown ones too.
  function planLine(plan) {
    if (!plan) return 'not in any release plan';
    if (plan.documentation_only) return 'Superseded geometry plan for ' + plan.release + ': this release changed documentation, not game content. Cell inclusion is recorded separately.';
    const extra = Object.keys(plan).filter(k => !PLAN_CORE.includes(k)).sort().map(k => k + ' ' + (typeof plan[k] === 'object' ? JSON.stringify(plan[k]) : plan[k]));
    return 'Plan: ' + plan.release + ' (' + plan.state + (plan.tier === 'next' ? ', next release' : plan.tier === 'later' ? ', later release' : '') + ')' +
      (plan.since ? ' · since ' + plan.since : '') + (plan.source ? ' · by ' + plan.source : '') + (extra.length ? ' · ' + extra.join(' · ') : '');
  }

  // The presets. `on` = the statuses left ticked (null = all); colour = the colouring it switches to; rel = release filter.
  function presets(release, planNext) {
    return [
      {id: 'everything', name: 'Everything', on: null, colour: 'status', rel: ''},
      {id: 'eligible', name: 'Eligible for ' + (release || 'the next release'), on: ELIGIBLE, colour: 'status', rel: ''},
      {id: 'awaiting', name: 'Awaiting lighting', on: AWAITING, colour: 'status', rel: ''},
      {id: 'problems', name: 'Problems only (failed, not converted, hull pending)', on: PROBLEMS, colour: 'status', rel: ''},
      {id: 'notstarted', name: 'Not started', on: ['not_started'], colour: 'status', rel: ''},
      {id: 'lighting', name: 'Lighting (the lighting layer)', on: null, colour: 'lighting', rel: ''},
      {id: 'lava', name: 'Lava (the lava layer: mapped / converted)', on: null, colour: 'lava', rel: ''},
      {id: 'release', name: 'Release content (cells assigned to a release)', on: null, colour: 'status', rel: '__any'},
    ].concat(planNext ? [{id: 'plan', name: 'Planned for ' + planNext + ' (gold)', on: null, colour: 'plan', rel: ''}] : []);
  }
  // The state a preset sets: {colour, off: [legend keys unticked], rel}.
  function presetState(id, release, planNext) {
    const p = presets(release, planNext).find(x => x.id === id);
    if (!p) return null;
    const off = p.on ? STATUSES.filter(s => !p.on.includes(s)).map(statusKey) : [];
    return {colour: p.colour, off: off.sort(), rel: p.rel};
  }
  // The preset id a state equals, or 'custom'.
  function matchPreset(state, release, planNext) {
    const off = [...state.off].sort().join('|');
    for (const p of presets(release, planNext)) {
      const s = presetState(p.id, release, planNext);
      if (s.colour === state.colour && s.rel === (state.rel || '') && s.off.join('|') === off) return p.id;
    }
    return 'custom';
  }
  // Release filter: '' all, '__any' assigned to some release, '__none' unassigned, otherwise a release name.
  function relOk(filter, cell) {
    if (filter === '__planned') return !!cell.plan;
    if (filter && filter.startsWith('plan:')) return !!cell.plan && cell.plan.release === filter.slice(5);
    const name = cell.release ? cell.release.name : null;
    if (!filter) return true;
    if (filter === '__any') return !!name;
    if (filter === '__none') return !name;
    return name === filter;
  }
  // The legend key of a cell under a colouring (null = that colouring is a scale, not a set of rows).
  function cellKey(mode, c, compare) {
    if (mode === 'status') return statusKey(c.chim.bucket);
    if (mode === 'plan') return 'chim:plan:' + (planTier(c) || 'other');
    if (mode === 'lighting') return 'chim:lighting:' + ((c.lighting && c.lighting.status) || 'not_measured');
    if (mode === 'lava') return c.lava && c.lava.status !== 'none' ? 'chim:lava:' + c.lava.status : null;
    if (mode === 'legacy') return c.legacy ? 'chim:grade:' + c.legacy.grade : null;
    if (mode === 'compare') return 'chim:compare:' + (compare || 'missing');
    if (mode && mode.startsWith('audit:')) return 'chim:audit:' + ((c.audits[mode.slice(6)] || {status: 'not_measured'}).status);
    return null;
  }
  function visible(off, filter, mode, c, compare) {
    const k = cellKey(mode, c, compare);
    return (!k || !off.has(k)) && relOk(filter, c);
  }
  // Compare layer: your cell against the reference cell: same / better / worse / missing (no such cell in your data).
  function compareClass(mine, ref, rank) {
    if (!mine || !ref) return 'missing';
    const a = rank[mine.chim.bucket] || 0, b = rank[ref.status] || 0;
    return a === b ? 'same' : a > b ? 'better' : 'worse';
  }
  // The status strip above the map: one state dot for the data's freshness. Red = the last load failed; grey = auto-update off or
  // the build finished ("final"); green = updated within two intervals; amber = older (stale) or still waiting for the first data.
  function stripState(o) {
    if (o.error) return {dot: 'red', label: 'load error'};
    if (o.finished) return {dot: 'grey', label: 'final'};
    if (!o.auto) return {dot: 'grey', label: 'auto-update off'};
    if (o.updated == null) return {dot: 'amber', label: 'waiting for data'};
    return o.now - o.updated <= 2 * o.interval ? {dot: 'green', label: 'live'} : {dot: 'amber', label: 'stale'};
  }
  function agoText(ms) {
    const s = Math.max(0, Math.round(ms / 1000));
    if (s < 60) return s + ' s ago';
    if (s < 3600) return Math.floor(s / 60) + ' min ' + (s % 60) + ' s ago';
    return Math.floor(s / 3600) + ' h ' + Math.floor(s % 3600 / 60) + ' min ago';
  }
  function save(storage, state) {
    try { storage.setItem(STORE, JSON.stringify({off: [...state.off], rel: state.rel || '', colour: state.colour})); } catch (_) { /* private window */ }
  }
  function load(storage) {
    try {
      const s = JSON.parse(storage.getItem(STORE) || 'null');
      if (s && Array.isArray(s.off)) return {off: s.off.filter(x => typeof x === 'string'), rel: typeof s.rel === 'string' ? s.rel : '', colour: s.colour || 'status'};
    } catch (_) { /* unreadable: start clean */ }
    return null;
  }
  const api = {MAP_MIN_H, MIN_ZOOM, MAX_ZOOM, mapLayout, clampView, zoomAt, fitView, ringLabelsVisible, OCEAN_SILVER, OCEAN_TEXT, PLAN_GOLD, PLAN_LATER, planTier, planColour, planRows, planTable, planLine, STATUSES, ELIGIBLE, AWAITING, PROBLEMS, statusKey, presets, presetState, matchPreset, relOk, cellKey, visible, compareClass, stripState, agoText, save, load, STORE};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ChimLegend = api;
})(typeof window !== 'undefined' ? window : this);
