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

// release (version) filter
assert.strictEqual(L.relOk('', cell('complete')), true);
assert.strictEqual(L.relOk('__none', cell('complete')), true);
assert.strictEqual(L.relOk('__any', cell('complete')), false);
const rel = cell('complete', {release: {name: 'v0.0.34'}});
assert.strictEqual(L.relOk('v0.0.34', rel), true);
assert.strictEqual(L.relOk('v0.0.33', rel), false);
assert.strictEqual(L.relOk('__none', rel), false);
assert.strictEqual(L.visible(new Set(), 'v0.0.33', 'status', rel), false);

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
