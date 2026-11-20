// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_master_completion.py with node (TOOLKIT-EXPANSION-COMPLETION-67): the Toolkit's side of the unified
// readiness count and the completion panel. Arguments: toolkit folder, a tracker doc (JSON) holding `readiness` and
// `completion` as tools/master_completion.py wrote them. Prints one JSON line: the readiness the page counts by itself from
// the same doc without those keys (the Python test compares it with the generator's), then PASS.
const fs = require('fs'), assert = require('assert'), path = require('path');
const kit = process.argv[2], doc = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const EV = require(path.resolve(kit, 'expansion-views.js')), H = require(path.resolve(kit, 'chim-head.js'));
const CP = require(path.resolve(kit, 'completion-panel.js')), IT = require(path.resolve(kit, 'interior-tracker.js'));

// the data's own readiness is used as it is; without it the page counts the same by itself
assert.strictEqual(EV.readiness(doc), doc.readiness, 'the generator\'s readiness is drawn, never recounted');
const bare = Object.assign({}, doc); delete bare.readiness; delete bare.completion;
const counted = EV.readiness(bare);
assert.strictEqual(EV.readiness(null), null);
assert.strictEqual(EV.readyPct(1, 3), 33.3); assert.strictEqual(EV.readyPct(1, 8), 12.5); assert.strictEqual(EV.readyPct(0, 0), 0);

// the headline: one row per land with the same three columns, one for all lands, then the build
const rows = H.headRows(doc.headline, null, doc.readiness);
assert.strictEqual(rows.length, 5, 'three lands, all lands, the build: ' + rows.length);
for (const l of doc.readiness.lands) {
  const r = rows[doc.readiness.lands.indexOf(l)].html;
  const f = x => x.ready.toLocaleString() + ' of ' + x.total.toLocaleString() + ' (' + x.percent.toFixed(1) + ' %)';
  for (const part of ['terrain', 'rooms', 'total']) assert(r.includes(f(l[part])), l.id + ' ' + part + ': ' + r);
  assert(/open terrain ready <b>.*rooms ready <b>.*total ready <b>/.test(r), 'the same three columns for every land');
}
assert(/^<b>All lands<\/b>: open terrain ready/.test(rows[3].html), 'all lands together in the same three columns');
assert(/In the game:/.test(rows[4].html), 'the build row stays last');
assert(rows[0].title === doc.readiness.definition, 'the definition is the row\'s help text');
assert(/audits \(open terrain\): Fully approved cells:/.test(rows[0].html), 'the approval and lighting audit figures stay, on their own line');
// without readiness the old rows are drawn (older pages)
assert.strictEqual(H.headRows(doc.headline, null, null).length, 4);

// the completion panel: Tribunal first, every count a link to its list, the gaps named
const games = CP.masters(doc.completion, doc.readiness);
assert.deepStrictEqual(games.map(g => g.id), ['mournhold', 'solstheim', 'vvardenfell']);
const html = CP.panelHtml(doc.completion, doc.readiness, 'mournhold');
const links = [...html.matchAll(/data-cplist="([^"]+)"/g)].map(m => m[1]);
assert(links.length > 0, 'counts are links');
for (const id of links) assert(html.includes('<details class="cplist" id="' + id + '">'), 'every link has its list: ' + id);
assert(html.includes('not measured yet'), 'what nothing measures says so');
assert(html.includes('MOURNHOLD-STATE-TRACKING-PARITY-67'), 'with the item that will measure it');
const mh = doc.readiness.lands.find(l => l.id === 'mournhold');
assert(html.includes('Districts counted once, as open terrain') === (mh.rooms.as_terrain.length > 0));
// a panel with no completion section (older data) still draws the count and says what is missing
const old = CP.panelHtml(null, doc.readiness, 'mournhold');
assert(old.includes('Rooms (interiors) ready') && old.includes('not measured yet'));

// the room list grouped by land holds the rooms of the land's count, the districts named
const grp = EV.landGrouping(doc.readiness);
const ir = IT.section(doc);
const listed = IT.grouped(ir, ir.rooms, grp);
for (const l of doc.readiness.lands) {
  const g = listed.find(x => x.island === l.name);
  const n = g ? g.rooms : 0;
  assert.strictEqual(n, l.rooms.total + l.rooms.as_terrain.length, l.name + ': the list holds the land\'s rooms and its districts');
}
assert(!listed.some(g => g.island === 'none'), 'no-entrance rooms sit in their land\'s group');
const lh = IT.listHtml(ir, '', {byLand: grp});
if (mh.rooms.as_terrain.length) assert(lh.includes('counted once, as open terrain'), 'the list says why its count differs');

console.log(JSON.stringify(counted));
console.log('PASS completion panel: unified readiness rows, panel links, room list by land');
