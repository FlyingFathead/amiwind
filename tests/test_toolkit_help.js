// SPDX-License-Identifier: GPL-3.0-only
// TOOLKIT-HELP-BUTTON-INERT-64: the round "?" in the Toolkit header is a button that opens a help panel for its page; Escape or a
// click outside closes it. DOM-free: a small stand-in document that keeps the listeners and the panel.
const assert = require('assert'), fs = require('fs'), path = require('path');
const kit = path.join(__dirname, '..', 'amiwind-toolkit');
const listeners = {};
const mk = tag => ({tag, attrs: {}, children: [], className: '', style: {}, innerHTML: '', contains(x) { return x === this || this.children.includes(x); },
  setAttribute(k, v) { this.attrs[k] = String(v); }, getAttribute(k) { return this.attrs[k]; }, remove() { this.removed = true; }, focus() { this.focused = true; },
  appendChild(c) { this.children.push(c); return c; }, querySelector() { return {onclick: null}; }});
global.window = global;
const doc = {head: mk('head'), body: mk('body'), createElement: mk, getElementById: () => null,
  addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); }, removeEventListener(t, f) { listeners[t] = (listeners[t] || []).filter(x => x !== f); }};
global.document = doc;
const H = require(path.join(kit, 'header.js'));
// every page key has its help, and a docs file that exists
for (const [subtitle, key] of Object.entries(H.KEYS)) {
  const h = H.HELP[key];
  assert(h && h[0] && h[1] && h[2].length, 'help for ' + subtitle);
  assert(fs.existsSync(path.join(__dirname, '..', 'docs', h[3])), 'docs page ' + h[3]);
}
// the markup holds a real button
assert(/<button type="button" class="awnote"[^>]*aria-label="Help for this page"[^>]*>\?<\/button>/.test(H.markup('World Map')), 'the ? is a button');
assert(!/<span class="awnote"/.test(H.markup('World Map')), 'no inert span');
// open, close with Escape
const anchor = mk('button');
const panel = H.help('inspector', anchor);
assert(panel && panel.className === 'awhelp' && /POLYCOUNT_INSPECTOR\.md/.test(panel.innerHTML) && anchor.getAttribute('aria-expanded') === 'true');
assert(listeners.keydown && listeners.keydown.length === 1 && listeners.mousedown.length === 1);
listeners.keydown[0]({key: 'Escape', preventDefault() {}});
assert(panel.removed && anchor.getAttribute('aria-expanded') === 'false' && !(listeners.keydown || []).length, 'Escape closes it');
// open, close with a click outside; a click on the button itself toggles
const p2 = H.help('world', anchor);
listeners.mousedown[0]({target: p2});
assert(!p2.removed, 'a click inside stays');
listeners.mousedown[0]({target: mk('div')});
assert(p2.removed, 'a click outside closes it');
const p3 = H.help('monitor', anchor);
assert(H.help('monitor', anchor) === null && p3.removed, 'the second press on the button closes it');
// every page has a help target
const need = {'index.html': 'id="helpbtn"', 'world-map.html': "AmiWindToolkitHeader.mount('World Map')", 'map-inspector.html': 'data-subtitle="3D Map Inspector"',
  'monitor.html': "AmiWindToolkitHeader.mount('Monitor')", 'mesh-compare.html': "AmiWindToolkitHeader.mount('Mesh Compare')", 'seam-check.html': 'data-subtitle="Seam Check"'};
for (const [file, needle] of Object.entries(need)) assert(fs.readFileSync(path.join(kit, file), 'utf8').includes(needle), file + ' has its help target: ' + needle);
console.log('PASS toolkit help: a real button on every page, one help panel per page, Escape and outside click close it');
