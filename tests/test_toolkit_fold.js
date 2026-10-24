// SPDX-License-Identifier: GPL-3.0-only
// Run by tests/test_toolkit_fold.py with node: amiwind-toolkit/panel-fold.js against a tiny DOM stub. Argument: the helper's path.
const assert = require('assert');
function make() {
  const n = {children: [], classes: new Set(), attrs: {}, id: '', hidden: false,
    setAttribute(k, v) { this.attrs[k] = v; },
    get firstChild() { return this.children[0] || null; },
    get nextSibling() { return null; },
    insertBefore(x, ref) { const i = ref ? this.children.indexOf(ref) : -1; if (i < 0) this.children.push(x); else this.children.splice(i, 0, x); return x; }};
  n.classList = {add: c => n.classes.add(c), toggle: (c, on) => { on ? n.classes.add(c) : n.classes.delete(c); }};
  return n;
}
const doc = {head: {appendChild() {}}, getElementById: () => null, createElement: () => make()};
const src = require('fs').readFileSync(process.argv[2], 'utf8');
function run(storage) {
  const win = {document: doc, localStorage: storage};
  const blocks = [make(), make()], all = make();
  const api = new Function('module', 'window', src + '\nreturn module.exports;')({exports: {}}, win);
  const h = api.init({key: 'k', allButton: all, blocks: [{el: blocks[0], id: 'a', title: 'A'}, {el: blocks[1], id: 'b', label: 'B'}]});
  return {blocks, all, h};
}
// Blocked storage (every access throws): the page still works, everything starts open, toggling does not throw.
let t = run({getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }});
assert.ok(t.blocks.every(b => !b.classes.has('folded')), 'open by default');
assert.strictEqual(t.all.textContent, 'Collapse all');
t.all.onclick();
assert.ok(t.blocks.every(b => b.classes.has('folded')));
assert.strictEqual(t.all.textContent, 'Expand all');
assert.strictEqual(t.blocks[0].children[0].attrs['aria-expanded'], 'false');
assert.strictEqual(t.blocks[0].children[0].textContent, '▸');
t.all.onclick();
assert.strictEqual(t.blocks[0].children[0].textContent, '▾');
// A remembered state is restored; an unreadable one is ignored.
const mem = {k: JSON.stringify({a: 'closed'})};
t = run({getItem: k => mem[k] || null, setItem: (k, v) => { mem[k] = v; }});
assert.ok(t.blocks[0].classes.has('folded') && !t.blocks[1].classes.has('folded'));
t.blocks[1].children[0].onclick();
assert.deepStrictEqual(JSON.parse(mem.k), {a: 'closed', b: 'closed'});
t = run({getItem: () => '{not json', setItem() {}});
assert.ok(t.blocks.every(b => !b.classes.has('folded')));
console.log('fold ok');
