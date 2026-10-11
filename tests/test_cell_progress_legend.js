// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_cell_progress.py with node: the World Map legend filter (amiwind-toolkit/chim-legend.js).
const assert = require('assert');
const path = require('path');
const L = require(path.resolve(process.argv[2]));

const cell = (bucket, extra) => Object.assign({x: 0, y: 0, chim: {bucket}, audits: {}, release: null, lighting: null}, extra || {});

// checkbox filtering: an unticked status row hides (dims) exactly those cells
const off = new Set([L.statusKey('not_started')]);
assert.strictEqual(L.visible(off, '', 'status', cell('not_started')), false);
assert.strictEqual(L.visible(off, '', 'status', cell('complete')), true);
assert.strictEqual(L.visible(new Set(), '', 'status', cell('not_started')), true);
// lighting rows are keyed by the lighting status; a scale colouring (ring) has no rows, so nothing is hidden
assert.strictEqual(L.visible(new Set(['chim:lighting:unlit']), '', 'lighting', cell('complete', {lighting: {status: 'unlit'}})), false);
assert.strictEqual(L.visible(new Set(['chim:lighting:unlit']), '', 'ring', cell('complete', {lighting: {status: 'unlit'}})), true);

// presets set the ticks; every preset round-trips; a hand tick makes it Custom
for (const p of L.presets('v0.0.34')) {
  const st = L.presetState(p.id, 'v0.0.34');
  assert.strictEqual(L.matchPreset(st, 'v0.0.34'), p.id, p.id);
}
assert.strictEqual(L.presets('v0.0.34')[1].name, 'Eligible for v0.0.34');
const elig = L.presetState('eligible', 'v0.0.34');
assert.ok(!elig.off.includes(L.statusKey('empty_sea')), 'eligible includes empty sea');
assert.ok(elig.off.includes(L.statusKey('not_started')));
assert.ok(!elig.off.includes(L.statusKey('complete_unlit')));
const prob = L.presetState('problems', 'v0.0.34');
assert.deepStrictEqual(L.STATUSES.filter(s => !prob.off.includes(L.statusKey(s))).sort(), ['converted_failing', 'hull_policy_pending', 'not_converted']);
assert.deepStrictEqual(L.presetState('awaiting').off.length, L.STATUSES.length - 2);
assert.strictEqual(L.presetState('lighting').colour, 'lighting');
// the lava layer (docs/LAVA.md): rows keyed by the lava status; a cell without lava has no row, so nothing hides it
assert.strictEqual(L.presetState('lava').colour, 'lava');
assert.strictEqual(L.visible(new Set(['chim:lava:molten']), '', 'lava', cell('complete', {lava: {status: 'molten'}})), false);
assert.strictEqual(L.visible(new Set(['chim:lava:molten']), '', 'lava', cell('complete', {lava: {status: 'converted'}})), true);
assert.strictEqual(L.visible(new Set(['chim:lava:molten']), '', 'lava', cell('complete', {lava: {status: 'none'}})), true);
assert.strictEqual(L.presetState('release').rel, '__any');
const hand = {colour: 'status', off: elig.off.concat([L.statusKey('complete')]), rel: ''};
assert.strictEqual(L.matchPreset(hand, 'v0.0.34'), 'custom');
assert.strictEqual(L.matchPreset({colour: 'ring', off: [], rel: ''}, 'v0.0.34'), 'custom');

// open ocean: silver, distinct from the gold plan, not part of the eligible set
assert.strictEqual(L.OCEAN_SILVER, '#c0c6cc');
assert.ok(![L.PLAN_GOLD, L.PLAN_LATER].includes(L.OCEAN_SILVER));
assert.ok(elig.off.includes(L.statusKey('ocean')), 'the eligible preset hides the open ocean');
assert.ok(!L.ELIGIBLE.includes('ocean'));
assert.ok(L.OCEAN_TEXT.startsWith('Open ocean: shared ocean chunk made, not yet placed in the game'));

// release (version) filter
assert.strictEqual(L.relOk('', cell('complete')), true);
assert.strictEqual(L.relOk('__none', cell('complete')), true);
assert.strictEqual(L.relOk('__any', cell('complete')), false);
const rel = cell('complete', {release: {name: 'v0.0.34'}});
assert.strictEqual(L.relOk('v0.0.34', rel), true);
assert.strictEqual(L.relOk('v0.0.33', rel), false);
assert.strictEqual(L.relOk('__none', rel), false);
assert.strictEqual(L.visible(new Set(), 'v0.0.33', 'status', rel), false);

// release plan layer (tools/cell_progress_plan.py): gold = planned for the NEXT release, whatever it is called
const pc = (tier, extra) => cell('complete', {plan: Object.assign({release: tier === 'later' ? 'v0.0.37' : 'v0.0.36', state: 'planned', since: 'T', source: 'owner', tier}, extra || {})});
assert.strictEqual(L.PLAN_GOLD, '#e8c46a');                                      // the gold of the Toolkit header
assert.strictEqual(L.planColour(pc('next')), L.PLAN_GOLD);
assert.strictEqual(L.planColour(pc('later')), L.PLAN_LATER);
assert.notStrictEqual(L.PLAN_LATER, L.PLAN_GOLD);
assert.strictEqual(L.planColour(pc('shipped')), null);                           // shipped cells keep their status colours
assert.strictEqual(L.planColour(cell('complete')), null);
const plans = [{release: 'v0.0.36', shipped: false, next: true, planned: 3, complete: 1, awaiting_lighting: 1, failing: 0, hull_policy_pending: 1, not_started: 0, title: 'T36'},
  {release: 'v0.0.37', shipped: false, next: false, planned: 2, complete: 0, awaiting_lighting: 0, failing: 1, hull_policy_pending: 0, not_started: 1},
  {release: null, shipped: false, next: false, planned: 90, complete: 0, awaiting_lighting: 0, failing: 0, hull_policy_pending: 0, not_started: 90}];
const rows = L.planRows(plans);
assert.deepStrictEqual(rows.map(r => r[2]), ['chim:plan:next', 'chim:plan:later']);
assert.ok(rows[0][1].startsWith('Planned for v0.0.36 (next release)'), rows[0][1]);
assert.ok(rows[1][1].startsWith('Planned for v0.0.37 (later)'));
assert.deepStrictEqual(L.planRows([]), [], 'no legend rows without a plan');
assert.deepStrictEqual(L.planRows([{release: 'v0.0.35', shipped: true, planned: 5}]), [], 'nothing upcoming = no rows');
// the shipped release drops out; the next one takes the gold with no code change
assert.strictEqual(L.planRows([{release: 'v0.0.36', shipped: true, next: false, planned: 3}, {release: 'v0.0.37', shipped: false, next: true, planned: 2}])[0][1].slice(0, 20), 'Planned for v0.0.37 ');
const tab = L.planTable(plans);
assert.deepStrictEqual(tab[tab.length - 1], ['TOTALS', '', 5, 1, 1, 1, 1, 1, 0]);
assert.strictEqual(tab.length, 3);
const tabO = L.planTable(plans.map(r => Object.assign({}, r, {ocean: r.planned === 3 ? 2 : 0})), 867);
assert.deepStrictEqual(tabO[tabO.length - 2], ['TOTALS', '', 5, 1, 1, 1, 1, 1, 2]);
assert.strictEqual(tabO[tabO.length - 1][0], 'OPEN OCEAN (silver, not counted as done)');   // its own totals row
assert.strictEqual(tabO[tabO.length - 1][8], 867);
assert.strictEqual(tabO.length, 4);
assert.strictEqual(tab[0][0], 'v0.0.36 - T36');
assert.deepStrictEqual(L.planTable([]), []);
// the plan colouring is a row set of its own; filter by plan release
assert.strictEqual(L.cellKey('plan', pc('next')), 'chim:plan:next');
assert.strictEqual(L.cellKey('plan', cell('complete')), 'chim:plan:other');
assert.strictEqual(L.visible(new Set(['chim:plan:next']), '', 'plan', pc('next')), false);
assert.strictEqual(L.visible(new Set(['chim:plan:next']), '', 'plan', pc('later')), true);
assert.strictEqual(L.relOk('plan:v0.0.36', pc('next')), true);
assert.strictEqual(L.relOk('plan:v0.0.36', pc('later')), false);
assert.strictEqual(L.relOk('__planned', pc('later')), true);
assert.strictEqual(L.relOk('__planned', cell('complete')), false);
// the preset appears only when a plan exists, and round-trips
assert.ok(!L.presets('v0.0.36').some(p => p.id === 'plan'));
const pp = L.presets('v0.0.36', 'v0.0.36').find(p => p.id === 'plan');
assert.strictEqual(pp.name, 'Planned for v0.0.36 (gold)');
assert.strictEqual(L.matchPreset(L.presetState('plan', 'v0.0.36', 'v0.0.36'), 'v0.0.36', 'v0.0.36'), 'plan');
// the cell panel line shows the core keys and every unknown key
assert.strictEqual(L.planLine(null), 'not in any release plan');
const line = L.planLine(pc('next', {district: 'canton', weight: 3}).plan);
assert.ok(line.startsWith('Plan: v0.0.36 (planned, next release)') && line.includes('district canton') && line.includes('weight 3'), line);

// map viewport (TOOLKIT-MAP-SCALING-36): fills the width, window height below the controls, never under 420 px; island fitted
const g = {w: 820, h: 1100};
let ml = L.mapLayout(900, 1000, 300, g, 2);
assert.strictEqual(ml.cssW, 900);                                                // the full stage width, not a narrow box
assert.strictEqual(ml.cssH, 688);                                                // 1000 - 300 - 12
assert.ok(Math.abs(ml.f - Math.min(900 / 820, 688 / 1100)) < 1e-9);
assert.ok(g.w * ml.f <= ml.cssW + 1e-6 && g.h * ml.f <= ml.cssH + 1e-6, 'the whole island fits at zoom 1');
assert.ok(Math.abs(ml.vw * ml.f - ml.cssW) < 1e-6 && Math.abs(ml.ratio - ml.f * 2) < 1e-9);
ml = L.mapLayout(900, 700, 650, g, 1);                                           // controls open in a short window
assert.strictEqual(ml.cssH, L.MAP_MIN_H);
ml = L.mapLayout(343, 812, 400, g, 3);                                           // phone: the stage width, no wider
assert.strictEqual(ml.cssW, 343);
ml = L.mapLayout(900, 1000, 300, {w: 0, h: 0}, 1);
assert.strictEqual(ml.f, 1);
ml = L.mapLayout(820, undefined, NaN, {w: 820, h: 820}, undefined);               // no window size known: still a usable box
assert.strictEqual(ml.cssH, L.MAP_MIN_H);
assert.ok(Number.isFinite(ml.f) && Number.isFinite(ml.ratio));
// fit centres the island; no view can leave the map outside the box; zoom keeps the point under the cursor fixed
ml = L.mapLayout(900, 1000, 300, g, 1);
const v = {z: 3, x: 99, y: -99999};
L.fitView(v, g, ml.vw, ml.vh);
assert.strictEqual(v.z, 1);
assert.ok(Math.abs(v.y) < 1e-9 || v.y >= 0, 'a map that fits is centred');
assert.ok(Math.abs(v.x - (ml.vw - g.w) / 2) < 1e-9 && Math.abs(v.y - (ml.vh - g.h) / 2) < 1e-9);
Object.assign(v, {z: 4, x: -500, y: -700});
const px0 = (300 - v.x) / v.z, py0 = (200 - v.y) / v.z;                          // the map point under the cursor (300, 200)
L.zoomAt(v, 1.25, 300, 200, g, ml.vw, ml.vh);
assert.strictEqual(v.z, 5);
assert.ok(Math.abs((300 - v.x) / v.z - px0) < 1e-6 && Math.abs((200 - v.y) / v.z - py0) < 1e-6, 'zoom is around the cursor');
for (let i = 0; i < 40; i++) L.zoomAt(v, 1.25, 10, 10, g, ml.vw, ml.vh);
assert.strictEqual(v.z, L.MAX_ZOOM);
assert.ok(v.x <= 0 && v.x >= ml.vw - g.w * v.z && v.y <= 0 && v.y >= ml.vh - g.h * v.z, 'zoomed in: the edges hold');
v.x = 5000; v.y = 5000; L.clampView(v, g, ml.vw, ml.vh);
assert.ok(v.x === 0 && v.y === 0);
for (let i = 0; i < 60; i++) L.zoomAt(v, 1 / 1.25, ml.vw / 2, ml.vh / 2, g, ml.vw, ml.vh);
assert.strictEqual(v.z, L.MIN_ZOOM);
assert.ok(Math.abs(v.x - (ml.vw - g.w * v.z) / 2) < 1e-9, 'zoomed out: centred');
// ring numbers hide below a zoom level instead of overlapping
assert.strictEqual(L.ringLabelsVisible(23.9), false);
assert.strictEqual(L.ringLabelsVisible(24), true);

// compare layer
const rank = {not_started: 0, complete: 7};
assert.strictEqual(L.compareClass(cell('complete'), {status: 'not_started'}, rank), 'better');
assert.strictEqual(L.compareClass(cell('not_started'), {status: 'complete'}, rank), 'worse');
assert.strictEqual(L.compareClass(cell('complete'), {status: 'complete'}, rank), 'same');
assert.strictEqual(L.compareClass(null, {status: 'complete'}, rank), 'missing');
assert.strictEqual(L.compareClass(cell('complete'), undefined, rank), 'missing');

// remembered per viewer: localStorage wrapped in try/catch, never throws
const mem = {}; const storage = {setItem: (k, v) => { mem[k] = v; }, getItem: k => mem[k] || null};
L.save(storage, {colour: 'status', off: ['chim:status:not_started'], rel: 'v0.0.34'});
assert.deepStrictEqual(L.load(storage), {colour: 'status', off: ['chim:status:not_started'], rel: 'v0.0.34'});
const broken = {setItem: () => { throw new Error('blocked'); }, getItem: () => { throw new Error('blocked'); }};
L.save(broken, {colour: 'status', off: [], rel: ''});
assert.strictEqual(L.load(broken), null);
assert.strictEqual(L.load({getItem: () => '{not json'}), null);
// the status strip: green within two intervals, amber when stale, grey when off or final, red on a load error
const base = {now: 100000, updated: 95000, interval: 10000, auto: true, finished: false, error: false};
assert.deepStrictEqual(L.stripState(base), {dot: 'green', label: 'live'});
assert.strictEqual(L.stripState(Object.assign({}, base, {updated: 100000 - 20000})).dot, 'green');       // exactly two intervals
assert.deepStrictEqual(L.stripState(Object.assign({}, base, {updated: 100000 - 20001})), {dot: 'amber', label: 'stale'});
assert.deepStrictEqual(L.stripState(Object.assign({}, base, {updated: null})), {dot: 'amber', label: 'waiting for data'});
assert.deepStrictEqual(L.stripState(Object.assign({}, base, {auto: false})), {dot: 'grey', label: 'auto-update off'});
assert.deepStrictEqual(L.stripState(Object.assign({}, base, {finished: true})), {dot: 'grey', label: 'final'});
assert.deepStrictEqual(L.stripState(Object.assign({}, base, {finished: true, auto: false})), {dot: 'grey', label: 'final'});
assert.deepStrictEqual(L.stripState(Object.assign({}, base, {error: true, finished: true})), {dot: 'red', label: 'load error'});   // an error shows first
assert.strictEqual(L.agoText(4000), '4 s ago');
assert.strictEqual(L.agoText(-5), '0 s ago');
assert.strictEqual(L.agoText(125000), '2 min 5 s ago');
assert.strictEqual(L.agoText(7500000), '2 h 5 min ago');
console.log('legend ok');
