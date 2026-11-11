// SPDX-License-Identifier: GPL-3.0-only
// TOOLKIT-HEADLINE-ROWS-INLINE-64: the tracker headline draws one block element per land and one for the build (Firefox ran
// inline spans into one line). DOM-free: the element is a stand-in that keeps the innerHTML it is given.
const assert = require('assert'), path = require('path');
const H = require(path.join(__dirname, '..', 'amiwind-toolkit', 'chim-head.js'));
const headline = {
  eligible_release: 'v0.0.64', in_game_label: 'v0.0.64-dev3 (bf2743fa)', in_game_build: 'run',
  groups: {in_game: 1409, not_in_game: 0, settled: 749, accounted_for: 2158, cells: 2311}, states: {complete_unlit: 13},
  islands: [{island: 1, cells: 1390, done: 1390, percent: 100, complete: 0, terrain_complete: 0, complete_unlit: 13, terrain_complete_unlit: 804, eligible: 1390},
            {island: 2, cells: 144, done: 0, percent: 0}]};
const styles = [];
const doc = {head: {appendChild: s => styles.push(s)}, getElementById: () => null, createElement: () => ({})};
const el = {ownerDocument: doc, innerHTML: '', hidden: true, querySelectorAll: () => [], querySelector: () => null};
H.render(el, headline, [], () => {}, null);
const html = el.innerHTML;
const rows = html.match(/<div class="chimrow"[^>]*>.*?<\/div>/g) || [];
assert.strictEqual(rows.length, 4, 'one row per land (3) and one for the build: ' + rows.length);
assert(/Vvardenfell/.test(rows[0]) && /Solstheim/.test(rows[1]) && /Mournhold/.test(rows[2]) && /In the game/.test(rows[3]));
assert(!/<span class="chimrow/.test(html), 'rows are never inline spans');
assert(/^<div class="chimrows chimtitle">/.test(html), 'the rows sit in one group that stays the page title');
for (const row of rows) assert.strictEqual((row.match(/<div/g) || []).length, 1, 'a row holds no further block');
assert(/\.chimrows \.chimrow\{display:block/.test(H.CSS) && /\.chimrows\{display:block;flex:0 0 100%/.test(H.CSS), 'the layout CSS ships with the script');
// the rule under the four rows: one element at the end of the group, positioned against the headline box so it spans the window
assert(/<div class="chimrule"><\/div><\/div>/.test(html), 'a rule closes the group');
assert(html.indexOf('chimrule') > html.lastIndexOf('class="chimrow"') && html.indexOf('chimrule') < html.indexOf('chimgroups'), 'the rule sits under the rows, before the chips');
assert(/\.chimrows \.chimrule\{position:absolute;left:0;right:0;height:0;border-top:1px solid var\(--line,#345\)\}/.test(H.CSS), 'the rule is window wide and in the page header line colour');
assert(/#chimhead\{position:relative;padding-left:16px;padding-right:16px\}/.test(H.CSS), 'the headline keeps the page header 16px side padding');
assert(styles.length === 1 && /chimrow/.test(styles[0].textContent), 'the CSS is injected into the page');
// land rows: the heading holds the land and its main figure, each other figure is its own indented line; long rows wrap
assert(/Vvardenfell \(main game\): <b>Done: 1,390 of 1,390 \(100\.0 %\)<\/b>/.test(rows[0]) && (rows[0].match(/class="chimdetail"/g) || []).length === 3, 'heading plus three detail lines');
assert(/\.chimrows \.chimdetail\{display:block;margin-left:1\.6em/.test(H.CSS) && /white-space:normal;overflow-wrap:anywhere/.test(H.CSS), 'indented lines, rows wrap');
// the summary under the rows folds as one block, kept in localStorage with every access guarded
assert(/class="chimsumbtn"/.test(html) && /class="chimsummary">/.test(html), 'a fold button and one summary block');
const chimHeadPath = require.resolve(path.join(__dirname, '..', 'amiwind-toolkit', 'chim-head.js'));
const store = {}; global.window = {localStorage: {getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; }}};
delete require.cache[chimHeadPath];
const H2 = require(chimHeadPath);
assert.strictEqual(H2.summaryFolded(), false);
const sum = {hidden: false}, btn = {attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }}, node = {querySelector: s => (s === '.chimsummary' ? sum : btn)};
H2.setSummary(node, true);
assert(sum.hidden === true && btn.attrs['aria-expanded'] === 'false' && store[H2.SUM_KEY] === 'closed', 'folding hides the block and is remembered');
H2.setSummary(node, false);
assert(sum.hidden === false && store[H2.SUM_KEY] === 'open', 'unfolding shows it again');
global.window = {localStorage: {getItem() { throw Error('blocked'); }, setItem() { throw Error('blocked'); }}};
delete require.cache[chimHeadPath];
const H3 = require(chimHeadPath);
assert.strictEqual(H3.summaryFolded(), false, 'blocked storage: the page is fine without it');
H3.setSummary(node, true);
assert.strictEqual(H3.summaryFolded(), true, 'and the choice lasts until reload');
console.log('PASS chim headline rows: one block element per land and one for the build, layout CSS shipped with chim-head.js');
