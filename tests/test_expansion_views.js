// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_cell_progress.py with node: the expansion views of the World map (amiwind-toolkit/expansion-views.js).
// Synthetic cells and rooms only. Argument: toolkit folder.
const assert = require('assert'), path = require('path');
const V = require(path.resolve(process.argv[2], 'expansion-views.js'));

const cell = (x, y, island, state, extra) => ({x, y, island, land: true, chim: Object.assign({state, bucket: 'not_started', converted: false}, extra || {})});
const room = (id, island, state, master, extra) => Object.assign({id, name: id, island, state, master: master || 'Morrowind.esm', reasons: [], batch: null}, extra || {});
const cells = {};
const put = c => { cells[c.x + ',' + c.y] = c; };
put(cell(0, 0, 1, 'complete'));
put(cell(1, 0, 1, 'audits_passed'));
put(cell(2, 0, 1, 'not_in_build', {bucket: 'audits_passed', converted: true}));
put(cell(3, 0, 1, 'not_started'));
put(Object.assign(cell(4, 0, 1, 'sea_in_game'), {land: false, chim: {state: 'sea_in_game', bucket: 'empty_sea'}}));
put(Object.assign(cell(5, 0, 1, 'ocean'), {land: false, chim: {state: 'ocean', bucket: 'ocean'}}));
put(Object.assign(cell(6, 0, 1, 'settled'), {land: false, chim: {state: 'settled', bucket: 'not_started'}}));
put(cell(-23, 20, 2, 'solstheim', {converted: true}));            // the first Solstheim test frame: converted, not in the build
put(cell(-22, 20, 2, 'solstheim'));
put(cell(-21, 20, 2, 'solstheim'));
const doc = {headline: {islands: [{island: 1, name: 'Vvardenfell'}, {island: 2, name: 'Solstheim'}]}, cells,
  interior_rooms: {rooms: [
    room('Balmora, Inn', 'Vvardenfell', 'on_chim_rooms'),
    room('Balmora, Shop', 'Vvardenfell', 'not_started'),
    room('Mournhold, Great Bazaar', 'Mournhold', 'not_started', 'Tribunal.esm', {reasons: ['behaves_exterior']}),
    room('Mournhold, Temple Courtyard', 'Mournhold', 'converted', 'Tribunal.esm', {reasons: ['behaves_exterior']}),
    room('Mournhold, Temple', 'Mournhold', 'not_started', 'Tribunal.esm'),
    room('Mournhold, Hall', 'Mournhold', 'room_map', 'Tribunal.esm'),
    room('Old Mournhold, Test', 'none', 'test_cell', 'Tribunal.esm'),
    room('Raven Rock, Bar', 'Solstheim', 'not_started', 'Bloodmoon.esm')]}};

// cells: settled squares and the open ocean are not counted; sea in the game is done; a converted Solstheim cell is partial
const ext = V.exteriorCounts(doc);
assert.deepStrictEqual(ext.islands.map(i => [i.name, i.done, i.partial, i.missing, i.total]), [['Vvardenfell', 3, 1, 1, 5], ['Solstheim', 0, 1, 2, 3]]);
assert.deepStrictEqual([ext.total.done, ext.total.partial, ext.total.missing, ext.total.total], [3, 2, 3, 8]);
assert.strictEqual(ext.islands[0].rate, 60);

// rooms: in the game = done, converted = partial, the rest (set aside included) = missing
const mr = V.mournholdRooms(doc);
assert.strictEqual(mr.length, 5);
const rc = V.roomCounts(mr);
assert.deepStrictEqual([rc.done, rc.partial, rc.missing, rc.total, rc.set_aside], [1, 1, 3, 5, 1]);
assert.deepStrictEqual(mr.filter(V.isDistrict).map(r => r.name).sort(), ['Mournhold, Great Bazaar', 'Mournhold, Temple Courtyard']);

// views: the map view is named after the islands the data holds; Mournhold is offered when Tribunal rooms are there
let v = V.views(doc);
assert.deepStrictEqual(v.map(x => x.id), ['vvardenfell', 'solstheim', 'mournhold']);
assert.deepStrictEqual(v.map(x => x.label), ['Vvardenfell', 'Solstheim', 'Mournhold']);
assert.strictEqual(v[0].text, 'done 3 · partial 1 · missing 1 of 5 cells');      // Vvardenfell's cells only
assert.ok(v[1].text.startsWith('done 0 · partial 1 · missing 2 of 3 cells · rooms: done 0 · partial 0 · missing 1 of 1'), v[1].text);
assert.ok(v[2].text.includes('of 5 rooms') && v[2].text.includes('1 set aside'), v[2].text);
assert.strictEqual(V.pick(v, 'mournhold'), 'mournhold');
assert.strictEqual(V.pick(v, 'gone'), 'vvardenfell');
// each map pane frames and draws its own island
assert.deepStrictEqual(V.paneBounds(doc, 'vvardenfell'), [0, 0, 6, 0]);
assert.deepStrictEqual(V.paneBounds(doc, 'solstheim'), [-23, 20, -21, 20]);
assert.strictEqual(V.paneBounds(doc, 'mournhold'), null);
assert.ok(V.inPane(cells['0,0'], 'vvardenfell') && !V.inPane(cells['0,0'], 'solstheim') && V.inPane(cells['-23,20'], 'solstheim') && !V.inPane(cells['-23,20'], 'vvardenfell'));
assert.deepStrictEqual(V.bloodmoonRooms(doc).map(r => r.name), ['Raven Rock, Bar']);
assert.strictEqual(V.pick([], 'world'), null);

// a build without the expansions: no Solstheim cells, no Tribunal rooms: one view, no expansion rate
const plain = {headline: {islands: [{island: 1, name: 'Vvardenfell'}]}, cells: {'0,0': cells['0,0'], '3,0': cells['3,0']},
  interior_rooms: {rooms: [room('Balmora, Inn', 'Vvardenfell', 'on_chim_rooms')]}};
v = V.views(plain);
assert.deepStrictEqual(v.map(x => [x.id, x.label]), [['vvardenfell', 'Vvardenfell']]);
assert.deepStrictEqual(V.completion(plain).map(r => [r.id, r.present]), [['base', true], ['bloodmoon', false], ['tribunal', false]]);
assert.deepStrictEqual(V.views({cells: {}}), []);
assert.deepStrictEqual(V.views(null), []);

// completion per game: cells and rooms together
const comp = V.completion(doc), by = Object.fromEntries(comp.map(r => [r.id, r]));
assert.deepStrictEqual([by.base.done, by.base.partial, by.base.missing, by.base.total], [4, 1, 2, 7]);
assert.deepStrictEqual([by.bloodmoon.done, by.bloodmoon.partial, by.bloodmoon.missing, by.bloodmoon.total, by.bloodmoon.rate], [0, 1, 3, 4, 0]);
assert.deepStrictEqual([by.tribunal.done, by.tribunal.partial, by.tribunal.missing, by.tribunal.total, by.tribunal.rate], [1, 1, 3, 5, 20]);
assert.strictEqual(V.rateText(by.tribunal), 'Mournhold (Tribunal): 20.0 % (1 of 5)');

// the Mournhold screen: districts first, then the rooms by state; every room is a tile, none overlaps, all inside the width
const L = V.mournholdLayout(mr, 400);
assert.strictEqual(L.tiles.length, 5);
assert.strictEqual(L.tiles.filter(t => t.district).length, 2);
for (const t of L.tiles) assert.ok(t.x >= 0 && t.x + t.w <= L.width && t.y + t.h <= L.height, t.room.name);
for (let i = 0; i < L.tiles.length; i++) for (let j = i + 1; j < L.tiles.length; j++) {
  const a = L.tiles[i], b = L.tiles[j];
  assert.ok(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y, 'tiles overlap');
}
const t0 = L.tiles[0];
assert.strictEqual(V.hit(L, t0.x + 1, t0.y + 1), t0);
assert.strictEqual(V.hit(L, -5, -5), null);
// many rooms wrap onto rows of the width
const many = Array.from({length: 103}, (_, i) => room('R' + i, 'Mournhold', i % 2 ? 'converted' : 'not_started', 'Tribunal.esm'));
const LM = V.mournholdLayout(many, 400);
assert.strictEqual(LM.tiles.length, 103);
assert.ok(LM.tiles.every(t => t.x + t.w <= 400), 'rooms wrap inside the width');
assert.ok(!('districts' in LM.heads), 'no district heading without districts');
console.log('expansion views ok');
