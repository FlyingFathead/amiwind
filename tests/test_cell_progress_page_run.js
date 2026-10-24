// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_cell_progress.py with node: runs world-map.html's script against DOM stubs, feeds it a tracker JSON and
// draws, fits, zooms: a runtime error in the page (a blank map) fails here. Arguments: toolkit folder, cell-progress.json.
const fs = require('fs'), vm = require('vm');
const kit = process.argv[2], dataFile = process.argv[3];
const mk = () => {
  const target = function () {};
  const store = {};
  const p = new Proxy(target, {
    get(t, k) {
      if (k === Symbol.toPrimitive) return () => 0;
      if (k === 'getContext') return () => ctx;
      if (k === 'getBoundingClientRect') return () => ({left: 0, top: 100, width: store.w || 900, height: 600});
      if (k === 'checked') return store.checked || false;
      if (k === 'clientWidth') return 900;
      if (k === 'clientHeight') return 600;
      if (k === 'offsetWidth') return 900;
      if (k === 'options') return [];
      if (k === 'style') return store.style || (store.style = {});
      if (k === 'classList') return {add() {}, remove() {}, toggle() {}};
      if (k in store) return store[k];
      if (k === 'then') return undefined;
      if (k === 'measureText') return () => ({width: 10});
      return mk();
    },
    set(t, k, v) { store[k] = v; return true; },
    apply() { return mk(); },
  });
  return p;
};
const ctx = mk();
const doc = {getElementById: (id) => { const e = mk(); return e; }, createElement: () => mk(), addEventListener() {}, querySelector: () => mk(), querySelectorAll: () => [], body: mk()};
const win = {innerHeight: 900, innerWidth: 1250, scrollY: 0, devicePixelRatio: 2, addEventListener() {}, localStorage: {getItem: () => null, setItem() {}},
  location: {search: ''}, ChimLegend: null};
const sandbox = Object.assign(win, {document: doc, window: win, console, setTimeout, clearTimeout, setInterval() { return 0; }, clearInterval() {},
  URLSearchParams, location: {search: '', href: ''}, fetch: () => Promise.reject(new Error('no fetch')), ResizeObserver: undefined, Image: function () {},
  navigator: {}, parent: {postMessage() {}}, requestAnimationFrame: f => 0, Intl, Math, JSON, Map, Set, Array, Object, Number, String, Date, isFinite, parseInt, parseFloat});
const context = vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(kit + '/chim-legend.js', 'utf8'), context);
// The interior tracker block (panel-fold.js, interior-tracker.js), as the page loads them.
for (const f of ['panel-fold.js', 'interior-tracker.js']) if (fs.existsSync(kit + '/' + f)) vm.runInContext(fs.readFileSync(kit + '/' + f, 'utf8'), context);
const html = fs.readFileSync(kit + '/world-map.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let code = scripts[scripts.length - 1];
code += '\n;globalThis.__t = {draw, get view() { return view; }, geometry, setChim, get layout() { return layout; }, zoomAt, viewFit, get itIr() { return itIr; }, get itEntr() { return itEntr; }, chimOverview, LAYERS, chimLegend, legendHtml, chimCls};';
try { vm.runInContext(code, context); } catch (e) { console.log('LOAD ERROR', e.stack.split('\n').slice(0, 4).join('\n')); process.exit(1); }
const T = context.__t;
try {
  const d = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
  T.setChim(d, 'test');
  T.draw();
  console.log('layout', JSON.stringify(T.layout && {cssW: T.layout.cssW, cssH: T.layout.cssH, f: +T.layout.f.toFixed(3)}), 'view', JSON.stringify(T.view));
  T.zoomAt(1.6, 100, 100); T.draw(); console.log('zoomed', JSON.stringify(T.view));
  T.viewFit(); console.log('fit', JSON.stringify(T.view));
  // Interiors: with them the block, the side panel counts and the entrance layer are made; without them (older data) nothing is.
  if (d.interior_rooms) {
    const IT = context.AmiWindInteriors;
    if (!T.itIr || T.itIr.rooms.length !== d.interior_rooms.rooms.length) throw new Error('interior tracker not loaded');
    if (!T.chimOverview().includes('<h3>Interiors</h3>')) throw new Error('no interiors in the side panel');
    T.LAYERS.find(l => l.id === 'interiors').on = true; T.draw();
    const html = IT.listHtml(T.itIr, '');
    console.log('interiors', IT.titleLine(T.itIr), '· entrance cells', T.itEntr.size, '· list rows', (html.match(/<tr data-room=/g) || []).length);
  } else if (T.itIr) throw new Error('interiors made up from data without them');
} catch (e) { console.log('RUN ERROR', e.stack.split('\n').slice(0, 6).join('\n')); process.exit(1); }
const assert = require('assert');
assert.ok(T.layout.cssW === 900 && T.layout.cssH >= 420, 'the map fills the stage width and is at least 420 px high');
assert.strictEqual(T.view.z, 1);
// grouped data (TOOLKIT-LEGEND-STATES-UNCLEAR-48): three group headers, zero states in the "More states" fold-out
const dd = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
if (dd.headline.groups && dd.headline.states) {
  const rows = T.chimLegend(), heads = rows.filter(r => r[3] === 'head').map(r => r[1]);
  assert.ok(heads[0].startsWith('In the game: ') && heads[1].startsWith('Not in the game yet: ') && heads[2].startsWith('Beyond the world'), heads.join(' | '));
  assert.ok(heads[3].startsWith('Accounted for: '));
  const more = rows.filter(r => r[3] === 'more').map(r => r[2]);
  for (const k of more) assert.strictEqual(dd.headline.states[k.replace('chim:status:', '')], 0, k);
  const html = T.legendHtml(rows);
  assert.ok(html.includes('More states (' + more.length + ' with no cells now)') && html.includes('id="legmorebox" hidden'));
  for (const c of Object.values(dd.cells)) assert.strictEqual(T.chimCls(c), c.chim.state);
  console.log('grouped legend rows ok');
}
console.log('page run ok');
