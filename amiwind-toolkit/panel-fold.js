// SPDX-License-Identifier: GPL-3.0-only
// Collapsible control blocks for the Toolkit pages (World Map, Monitor), shared by both.
//   AmiWindFold.init({key, blocks: [{el, id, title (shown) or label (name for assistive tech only, when the block shows its own title), closed, onChange}], allButton, onChange})
// Each block gets a triangle button (U+25B8 collapsed / U+25BE open; a button with aria-expanded) before its title. A closed block
// hides everything in it except the triangle, its title and any child marked class "foldkeep": nothing is removed from the page, so
// hidden controls keep their values. The state of every block is remembered per page under `key` in localStorage; every storage
// access is guarded, so a page with blocked storage still works (everything starts open, as before). A block with closed: true
// starts closed until it is opened once (then 'open' is remembered for it). allButton is a button that
// reads "Collapse all" while any block is open and "Expand all" once all are closed.
(function (root) {
  const OPEN = '▾', CLOSED = '▸';
  const CSS = '.foldbtn{background:none;border:0;color:#edf3fa;font:inherit;font-size:14px;line-height:1;padding:2px 5px;cursor:pointer;border-radius:4px}' +
    '.foldbtn:hover{background:#203346}.foldtitle{font-weight:600;color:#9fb3c8}' +
    '.foldblock.folded>:not(.foldbtn):not(.foldtitle):not(.foldkeep){display:none!important}' +
    '.foldrule{border:0;border-top:1px solid #345;margin:0}';
  function load(key) {
    try { const v = JSON.parse(root.localStorage.getItem(key) || 'null'); if (v && typeof v === 'object') return v; } catch (_) { /* no storage */ }
    return {};
  }
  function save(key, closed) {
    try { root.localStorage.setItem(key, JSON.stringify(closed)); } catch (_) { /* no storage: the choice lasts until the page closes */ }
  }
  function init(opts) {
    const doc = root.document;
    if (doc && doc.head && !doc.getElementById('panel-fold-css')) {
      const st = doc.createElement('style'); st.id = 'panel-fold-css'; st.textContent = CSS; doc.head.appendChild(st);
    }
    const closed = load(opts.key), blocks = [];
    const anyOpen = () => blocks.some(b => !b.folded);
    function label() { if (opts.allButton) opts.allButton.textContent = anyOpen() ? 'Collapse all' : 'Expand all'; }
    function apply(b, folded, user) {
      b.folded = folded;
      b.el.classList.toggle('folded', folded);
      b.btn.setAttribute('aria-expanded', folded ? 'false' : 'true');
      b.btn.setAttribute('aria-label', (folded ? 'Expand ' : 'Collapse ') + b.title);
      b.btn.textContent = folded ? CLOSED : OPEN;
      if (b.onChange) b.onChange(!folded, user);
    }
    function remember() {
      const rec = {};
      for (const b of blocks) if (b.folded) rec[b.id] = 'closed'; else if (b.closedByDefault) rec[b.id] = 'open';
      save(opts.key, rec);
    }
    for (const spec of opts.blocks) {
      if (!spec.el) continue;
      const b = {el: spec.el, id: spec.id, title: spec.label || spec.title || spec.id, onChange: spec.onChange, folded: false,
        closedByDefault: !!spec.closed};
      b.el.classList.add('foldblock');
      b.btn = doc.createElement('button'); b.btn.type = 'button'; b.btn.className = 'foldbtn';
      if (b.el.id) b.btn.setAttribute('aria-controls', b.el.id);
      b.btn.onclick = () => { apply(b, !b.folded, true); remember(); label(); if (opts.onChange) opts.onChange(); };
      let first = b.el.firstChild;
      b.el.insertBefore(b.btn, first);
      if (spec.title) {
        const t = doc.createElement('b'); t.className = 'foldtitle'; t.textContent = spec.title;
        b.el.insertBefore(t, b.btn.nextSibling);
      }
      blocks.push(b);
      apply(b, closed[b.id] ? closed[b.id] === 'closed' : b.closedByDefault, false);
    }
    if (opts.allButton) opts.allButton.onclick = () => {
      const fold = anyOpen();
      for (const b of blocks) apply(b, fold, true);
      remember(); label(); if (opts.onChange) opts.onChange();
    };
    label();
    return {blocks, anyOpen};
  }
  const api = {init, OPEN, CLOSED, CSS};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindFold = api;
})(typeof window !== 'undefined' ? window : this);
