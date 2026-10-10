// SPDX-License-Identifier: GPL-3.0-only
// The World Map's legend filter for the CHIM Progress Tracker: which legend rows are ticked, the preset pull-down, the
// release (version) filter and the compare layer. Pure functions (no DOM): world-map.html draws the controls and calls these,
// and tests/test_cell_progress.py runs them with node. A row that is unticked DIMS its cells (the same dimming the status
// chips and the "Show" filter use), so the island stays readable around what you picked.
(function (root) {
  // Every CHIM status, in legend order. Keys of the legend rows are 'chim:status:<status>'.
  const STATUSES = ['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested',
    'audits_passed', 'converted_failing', 'not_converted', 'converted_unmeasured', 'not_started', 'empty_sea', 'hull_policy_pending'];
  // Eligible for the next release: every passed status plus empty sea (tools/cell_progress.py ELIGIBLE_SELECT).
  const ELIGIBLE = ['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested', 'audits_passed', 'empty_sea'];
  const AWAITING = ['complete_unlit', 'terrain_complete_unlit'];
  const PROBLEMS = ['converted_failing', 'not_converted', 'hull_policy_pending'];
  const statusKey = s => 'chim:status:' + s;
  const STORE = 'amiwind-chim-legend-1';

  // The presets. `on` = the statuses left ticked (null = all); colour = the colouring it switches to; rel = release filter.
  function presets(release) {
    return [
      {id: 'everything', name: 'Everything', on: null, colour: 'status', rel: ''},
      {id: 'eligible', name: 'Eligible for ' + (release || 'the next release'), on: ELIGIBLE, colour: 'status', rel: ''},
      {id: 'awaiting', name: 'Awaiting lighting', on: AWAITING, colour: 'status', rel: ''},
      {id: 'problems', name: 'Problems only (failed, not converted, hull pending)', on: PROBLEMS, colour: 'status', rel: ''},
      {id: 'notstarted', name: 'Not started', on: ['not_started'], colour: 'status', rel: ''},
      {id: 'lighting', name: 'Lighting (the lighting layer)', on: null, colour: 'lighting', rel: ''},
      {id: 'lava', name: 'Lava (the lava layer: mapped / converted)', on: null, colour: 'lava', rel: ''},
      {id: 'release', name: 'Release content (cells assigned to a release)', on: null, colour: 'status', rel: '__any'},
    ];
  }
  // The state a preset sets: {colour, off: [legend keys unticked], rel}.
  function presetState(id, release) {
    const p = presets(release).find(x => x.id === id);
    if (!p) return null;
    const off = p.on ? STATUSES.filter(s => !p.on.includes(s)).map(statusKey) : [];
    return {colour: p.colour, off: off.sort(), rel: p.rel};
  }
  // The preset id a state equals, or 'custom'.
  function matchPreset(state, release) {
    const off = [...state.off].sort().join('|');
    for (const p of presets(release)) {
      const s = presetState(p.id, release);
      if (s.colour === state.colour && s.rel === (state.rel || '') && s.off.join('|') === off) return p.id;
    }
    return 'custom';
  }
  // Release filter: '' all, '__any' assigned to some release, '__none' unassigned, otherwise a release name.
  function relOk(filter, cell) {
    const name = cell.release ? cell.release.name : null;
    if (!filter) return true;
    if (filter === '__any') return !!name;
    if (filter === '__none') return !name;
    return name === filter;
  }
  // The legend key of a cell under a colouring (null = that colouring is a scale, not a set of rows).
  function cellKey(mode, c, compare) {
    if (mode === 'status') return statusKey(c.chim.bucket);
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
  const api = {STATUSES, ELIGIBLE, AWAITING, PROBLEMS, statusKey, presets, presetState, matchPreset, relOk, cellKey, visible, compareClass, stripState, agoText, save, load, STORE};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ChimLegend = api;
})(typeof window !== 'undefined' ? window : this);
