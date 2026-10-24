// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_legend_groups.py with node: the grouped legend (TOOLKIT-LEGEND-STATES-UNCLEAR-48) of chim-legend.js and the
// grouped headline chips of chim-head.js, against an ingested tracker file. Arguments: toolkit folder, cell-progress.json.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const kit = process.argv[2];
const L = require(path.resolve(kit, 'chim-legend.js'));
const H = require(path.resolve(kit, 'chim-head.js'));
const d = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const h = d.headline;

// the same layout in both scripts (the index page loads chim-head.js alone)
const lay = L.groupLayout(h);
assert.deepStrictEqual(H.layout(h), lay);
assert.deepStrictEqual(lay.groups.map(g => g.id), ['in_game', 'not_in_game', 'settled']);
assert.deepStrictEqual(lay.groups.map(g => g.title), ['In the game', 'Not in the game yet', "Beyond the world's edge: settled"]);
assert.deepStrictEqual(lay.groups.map(g => g.count), [h.groups.in_game, h.groups.not_in_game, h.groups.settled]);
assert.strictEqual(lay.accounted, h.groups.in_game + h.groups.settled);
// a state with cells is on its group's row; a state at 0 waits in "More states"
for (const g of lay.groups) for (const [k, n] of g.rows) assert.ok(n > 0 && h.states[k] === n, k);
for (const [k, n] of lay.more) assert.ok(n === 0 && !h.states[k], k);
const shown = lay.groups.flatMap(g => g.rows.map(r => r[0])), more = lay.more.map(r => r[0]);
assert.deepStrictEqual([...shown, ...more].sort(), L.GROUPS.flatMap(g => g[2]).sort());
assert.ok(shown.includes('sea_in_game') && shown.includes('settled'));
assert.ok(more.includes('hull_policy_pending') && more.includes('complete'));
// a state comes back to the main row by itself once it has cells
const h2 = JSON.parse(JSON.stringify(h)); h2.states.hull_policy_pending = 3;
assert.ok(L.groupLayout(h2).groups[1].rows.some(r => r[0] === 'hull_policy_pending'));
assert.ok(!L.groupLayout(h2).more.some(r => r[0] === 'hull_policy_pending'));
// older data without the groups: no layout (the flat chips are drawn as before)
assert.strictEqual(L.groupLayout({ocean: 3}), null);
assert.strictEqual(H.layout({ocean: 3}), null);

// the chips' markup: three headers, settled with the maintainer's hover text, the fold-out closed by default
const html = H.groupsHtml(h, null);
for (const t of ['In the game <b>', 'Not in the game yet <b>', 'Beyond the world&#39;s edge: settled <b>'.replace('&#39;', "'")]) assert.ok(html.includes(t), t);
assert.ok(html.includes('data-bucket="settled"'));
assert.ok(html.includes(L.SETTLED_TEXT.replace(/"/g, '&quot;')));
assert.ok(/class="chimmorebtn" aria-expanded="false">▸ More states \(\d+ with no cells now\)/.test(html));
assert.ok(html.includes('accounted for: ' + lay.accounted.toLocaleString() + ' of ' + lay.cells.toLocaleString()));
assert.ok(!html.includes('shared ocean chunk made'));
// every grouped state has a chip text and colour
for (const s of L.GROUPS.flatMap(g => g[2])) assert.ok(H.STATE_PARTS[s], s);
// presets: "In the game" and "Not in the game yet" tick exactly their groups
const ing = L.presetState('ingame', 'v0.0.48');
assert.deepStrictEqual(L.STATUSES.filter(s => !ing.off.includes(L.statusKey(s))).sort(), [...L.IN_GAME].sort());
const left = L.presetState('workleft', 'v0.0.48');
assert.deepStrictEqual(L.STATUSES.filter(s => !left.off.includes(L.statusKey(s))).sort(), [...L.NOT_IN_GAME].sort());
assert.ok(!L.presetState('notstarted').off.includes(L.statusKey('solstheim')));
console.log('legend groups ok');
