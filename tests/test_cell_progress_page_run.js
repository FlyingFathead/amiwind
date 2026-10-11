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
const html = fs.readFileSync(kit + '/world-map.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let code = scripts[scripts.length - 1];
code += '\n;globalThis.__t = {draw, get view() { return view; }, geometry, setChim, get layout() { return layout; }, zoomAt, viewFit};';
try { vm.runInContext(code, context); } catch (e) { console.log('LOAD ERROR', e.stack.split('\n').slice(0, 4).join('\n')); process.exit(1); }
const T = context.__t;
try {
  const d = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
  T.setChim(d, 'test');
  T.draw();
  console.log('layout', JSON.stringify(T.layout && {cssW: T.layout.cssW, cssH: T.layout.cssH, f: +T.layout.f.toFixed(3)}), 'view', JSON.stringify(T.view));
  T.zoomAt(1.6, 100, 100); T.draw(); console.log('zoomed', JSON.stringify(T.view));
  T.viewFit(); console.log('fit', JSON.stringify(T.view));
} catch (e) { console.log('RUN ERROR', e.stack.split('\n').slice(0, 6).join('\n')); process.exit(1); }
const assert = require('assert');
assert.ok(T.layout.cssW === 900 && T.layout.cssH >= 420, 'the map fills the stage width and is at least 420 px high');
assert.strictEqual(T.view.z, 1);
console.log('page run ok');
