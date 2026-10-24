// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_cell_progress.py with node: the interior tracker of the World map (amiwind-toolkit/interior-tracker.js) and the
// default-closed blocks of panel-fold.js. Synthetic rooms only. Arguments: toolkit folder [, a real cell-progress.json to check
// that the list, the counts and the entrance cells are made from it].
const fs = require('fs'), assert = require('assert'), path = require('path');
const kit = process.argv[2], dataFile = process.argv[3];
const IT = require(path.resolve(kit, 'interior-tracker.js'));

const room = (id, island, state, extra) => Object.assign({id, name: id, island, state, master: 'Morrowind.esm', reasons: [], batch: null,
  entrance: null, settlement: null}, extra || {});
const doc = {interior_rooms: {headline: {Vvardenfell: {total: 4, groups: {in_game: 1, not_in_game: 2, set_aside: 1}}, none: {total: 2, groups: {in_game: 0, not_in_game: 0, set_aside: 2}}},
  rooms: [
    room('Town, Inn', 'Vvardenfell', 'room_map', {entrance: '1,2', settlement: 'Town', batch: 1}),
    room('Town, Shop', 'Vvardenfell', 'not_started', {entrance: '1,2', settlement: 'Town', batch: 1}),
    room('Town, Cellar', 'Vvardenfell', 'not_started', {entrance: '1,2', settlement: 'Town', batch: 2}),
    room('Grotto', 'Vvardenfell', 'hard_case', {entrance: '5,5', reasons: ['water']}),
    room('ToddTest', 'none', 'test_cell', {reasons: ['unreachable'], batch: 31}),
    room('Vor Lair, Interior', 'none', 'no_entrance', {master: 'Bloodmoon.esm', reasons: ['unreachable'], batch: 'later: Solstheim'})]}};

// older data: no interiors, nothing drawn
assert.strictEqual(IT.section({cells: {}}), null);
assert.strictEqual(IT.section(null), null);
assert.strictEqual(IT.overviewHtml(null), '');
assert.strictEqual(IT.entranceCells(null).size, 0);

const ir = IT.section(doc);
assert.deepStrictEqual(IT.counts(ir), {total: 6, in_game: 1, not_in_game: 2, set_aside: 3});
assert.strictEqual(IT.titleLine(ir), '6 rooms · in the game 1 · not in the game yet 2 · set aside 3');

// grouped by island, then by entrance; the rooms with no entrance area are their own group at the end
const g = IT.grouped(ir, ir.rooms);
assert.deepStrictEqual(g.map(x => [x.island, x.rooms]), [['Vvardenfell', 4], ['none', 2]]);
assert.deepStrictEqual(g[0].entrances.map(e => [e.label, e.cell, e.rooms.map(r => r.name)]),
  [['Town (cell 1, 2)', '1,2', ['Town, Cellar', 'Town, Inn', 'Town, Shop']], ['Wilderness (cell 5, 5)', '5,5', ['Grotto']]]);
assert.strictEqual(g[1].label, 'No entrance area');
assert.strictEqual(g[1].entrances[0].cell, null);

// search over name, ID, state, batch and reasons
assert.deepStrictEqual(IT.filter(ir, 'town shop').map(r => r.id), ['Town, Shop']);
assert.deepStrictEqual(IT.filter(ir, 'test cell').map(r => r.id), ['ToddTest']);
assert.deepStrictEqual(IT.filter(ir, 'later: solstheim').map(r => r.id), ['Vor Lair, Interior']);
assert.deepStrictEqual(IT.filter(ir, 'water').map(r => r.id), ['Grotto']);
assert.strictEqual(IT.filter(ir, '').length, 6);

// the list: a room with an entrance cell is clickable (data-cell); the no-entrance rooms are not
const html = IT.listHtml(ir, '');
assert.ok(html.includes('data-room="Town, Inn" data-cell="1,2"'));
assert.ok(html.includes('data-room="ToddTest">'));
assert.ok(html.includes('Set aside: no entrance, no script'));
assert.ok(html.indexOf('data-island="none"') > html.indexOf('data-island="Vvardenfell"'));
assert.ok(!html.includes(' open>'), 'the groups start closed');
assert.ok(IT.listHtml(ir, 'grotto').includes(' open>'), 'a search opens the groups that match');
assert.ok(IT.listHtml(ir, 'nothing like this').includes('No room matches'));
assert.ok(IT.listHtml({rooms: [room('<b>', 'Vvardenfell', 'not_started')]}, '').includes('&lt;b&gt;'), 'names are escaped');

// the side panel: one short row per island
const ov = IT.overviewHtml(ir);
assert.ok(ov.includes('<td class="l">No entrance area</td><td>2</td><td>0</td><td>0</td><td>2</td>'));
const sortedKeys = IT.overviewHtml(Object.assign({}, ir, {headline: {none: ir.headline.none, Vvardenfell: ir.headline.Vvardenfell}}));
assert.ok(sortedKeys.indexOf('Vvardenfell') < sortedKeys.indexOf('No entrance area'), 'islands in order, no entrance area last');

// the map layer: one entry per entrance cell, coloured by the most common state (a tie goes further from the game)
const ent = IT.entranceCells(ir);
assert.deepStrictEqual([...ent.keys()].sort(), ['1,2', '5,5']);
assert.strictEqual(ent.get('1,2').state, 'not_started');
assert.strictEqual(ent.get('1,2').rooms, 3);
assert.strictEqual(ent.get('5,5').colour, IT.COLOURS.hard_case);
const tie = IT.entranceCells({rooms: [room('a', 'Vvardenfell', 'room_map', {entrance: '0,0'}), room('b', 'Vvardenfell', 'not_started', {entrance: '0,0'})]});
assert.strictEqual(tie.get('0,0').state, 'not_started');
assert.strictEqual(IT.legendRows(ir).length, IT.STATES.length);

// panel-fold.js: a block with closed: true starts closed, and once opened stays open (remembered as 'open')
{
  const store = {};
  global.window = undefined;
  const mkEl = id => { const kids = []; return {id, firstChild: null, classList: {cls: new Set(), add(c) { this.cls.add(c); }, toggle(c, on) { if (on) this.cls.add(c); else this.cls.delete(c); }},
    insertBefore(n) { kids.push(n); return n; }, kids}; };
  const fakeDoc = {head: {appendChild() {}}, getElementById: () => null,
    createElement: () => ({setAttribute(k, v) { this[k] = v; }, textContent: '', className: ''})};
  const root = {document: fakeDoc, localStorage: {getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; }}};
  const src = fs.readFileSync(path.resolve(kit, 'panel-fold.js'), 'utf8');
  const Fold = new Function('window', 'module', src + '\nreturn window.AmiWindFold;')(root, undefined);
  let r = Fold.init({key: 'k', blocks: [{el: mkEl('a'), id: 'a', title: 'A', closed: true}, {el: mkEl('b'), id: 'b', title: 'B'}]});
  assert.strictEqual(r.blocks[0].folded, true, 'closed by default');
  assert.strictEqual(r.blocks[1].folded, false, 'other blocks keep starting open');
  r.blocks[0].btn.onclick();
  assert.deepStrictEqual(JSON.parse(store.k), {a: 'open'});
  r = Fold.init({key: 'k', blocks: [{el: mkEl('a'), id: 'a', title: 'A', closed: true}]});
  assert.strictEqual(r.blocks[0].folded, false, 'opened once: remembered open');
}

if (dataFile) {
  const real = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
  const rir = IT.section(real);
  assert.ok(rir, 'the tracker data has interior_rooms');
  const c = IT.counts(rir), groups = IT.grouped(rir, rir.rooms);
  assert.strictEqual(c.in_game + c.not_in_game + c.set_aside, c.total);
  assert.strictEqual(groups.reduce((n, x) => n + x.rooms, 0), rir.rooms.length, 'every room is in the list');
  const listed = IT.listHtml(rir, '');
  assert.strictEqual((listed.match(/<tr data-room=/g) || []).length, rir.rooms.length, 'one row per room');
  const none = groups.find(x => x.island === IT.NO_ISLAND);
  console.log('real data:', IT.titleLine(rir), '| islands', groups.map(x => x.label + ' ' + x.rooms + ' (' + x.entrances.length + ' entrances)').join(', '),
    '| entrance cells', IT.entranceCells(rir).size, '| no entrance area', none ? none.rooms : 0, '| list', listed.length, 'chars');
  if (none) console.log('no entrance area:', none.entrances[0].rooms.map(r => r.name + ' [' + r.state + ', ' + IT.batchText(r.batch) + ']').join('; '));
}
console.log('interior tracker ok');
