// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit's shared header: the gold AmiWind logo, "Toolkit" with "Last updated with AmiWind vX" under it, and the page's
// own name as a subtitle. index.html keeps its markup exactly (logo, Toolkit, the World / Local / 3D Inspector buttons); this
// is the same logo block for every Toolkit page opened on its own. Embedded pages (inside index.html) show nothing: the
// index header is already above them. tests/test_cell_progress.py checks that the logo block here and in index.html agree.
//   AmiWindToolkitHeader.mount('World Map', '#pagetitle')   adds the header at the top of the page, hides the old title
// The logo address can be replaced before mount (window.AW_LOGO_SRC), as the standalone inspector export does with a data URI.
(function (root) {
  const VERSION_TEXT = 'Last updated with AmiWind v0.0.65';     // set by hand when the Toolkit is next updated, as in index.html
  const LOGO = '../resources/media/AmiWind_logo_name_only.png';
  const NOTE = 'Everything here runs in your browser. Views of the world are made from your own Morrowind files and build output ' +
    'on your machine; nothing is uploaded.';
  const CSS = '.awhead{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:8px 16px;border-bottom:1px solid #345;' +
    'background:#162433;color:#edf3fa;font:14px system-ui,sans-serif}.awhead img{height:46px;width:auto}' +
    '.awhead h1{font-size:24px;margin:0 6px 0 -4px;font-weight:700;color:#e8c46a;letter-spacing:.5px;line-height:1.1;white-space:normal}' +
    '.awhead h1 small{display:block;font-size:11px;font-weight:400;color:#9fb3c8;letter-spacing:0}' +
    '.awhead .awsub{font-size:18px;color:#ffe28a}.awhead .awnote{margin-left:auto;display:inline-flex;align-items:center;' +
    'justify-content:center;width:18px;height:18px;border:1px solid #6f8193;border-radius:50%;color:#8a9bad;font-size:12px;font-weight:700;' +
    'cursor:pointer;user-select:none;flex:0 0 auto}.awhead .awnote:hover{color:#edf3fa;border-color:#9fb3c8}' +
    '.awhead button.awnote{background:none;padding:0;font-family:inherit}' +
    '.awhead h1 .awnote{margin:0 0 0 10px;vertical-align:middle;position:relative;top:-2px;line-height:1}';
  function esc(t) { return String(t).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch])); }
  // The "?" is a real button: click, Enter or Space opens a small help panel for the page (what it shows, its controls, a link to its
  // docs page); Esc or a click outside closes it (TOOLKIT-HELP-BUTTON-INERT-64). HELP: page key -> [title, what it shows, controls, docs file].
  const DOCS = 'https://github.com/FlyingFathead/amiwind/blob/main/docs/';
  const HELP = {
    world: ['World Map', 'The map of the game world, coloured by how far the conversion has come, with the CHIM Progress Tracker headline above it.',
      ['Click a cell to select it; shift-click or shift-drag selects several.', 'Drag pans; + / - / fit / reset zoom; the wheel scrolls the page (turn on "wheel zoom", or hold Ctrl or Alt, to zoom the map with it).',
        'Colour by, Layers and the colour legend choose what the cells show; Controls and Collapse all fold the control blocks.'], 'AMIWIND_TOOLKIT.md'],
    local: ['Local view', 'One cell and the places it reaches, with its map, rooms and counts.',
      ['Pick a cell on the World tab, then open Local.', 'Show in 3D opens its map in the 3D Inspector.'], 'AMIWIND_TOOLKIT.md'],
    inspector: ['3D Map Inspector (Polycount inspector)', 'A compiled map, a CHIM world or a CHIM room in 3D, with its faces, drawing and collision figures.',
      ['Open BSP / CHIM / JSON, or pick a map, or name a room (?room=NAME) on a served build.', 'Fly or orbit the camera; the heat switch colours by faces or collision.', 'Copy JSON exports the view; its "program.version" is the AmiWind version.'], 'POLYCOUNT_INSPECTOR.md'],
    monitor: ['Monitor', 'A build as it runs: stages, cores in use, logs and recent results, read only.',
      ['Pick a run to follow its stages and logs.', 'The machine view lists the jobs using the cores.'], 'AMIWIND_TOOLKIT.md'],
    meshes: ['Mesh Compare', 'Two exports of the same mesh side by side (original and converted).',
      ['Pick two exports from the list.', 'Both views turn together.'], 'AMIWIND_TOOLKIT.md'],
    seam: ['Seam Check', 'The seams where neighbouring cells join, checked on a map.', ['Open a map or a cell pair to inspect its joins.'], 'AMIWIND_TOOLKIT.md']};
  const KEYS = {'World Map': 'world', 'Local': 'local', '3D Map Inspector': 'inspector', 'Monitor': 'monitor', 'Mesh Compare': 'meshes', 'Seam Check': 'seam'};
  const HELP_CSS = '.awhelp{position:fixed;top:64px;right:16px;z-index:2147483000;width:min(420px,calc(100vw - 32px));max-height:calc(100vh - 80px);overflow:auto;' +
    'background:#162433;color:#edf3fa;border:1px solid #6a85a3;border-radius:8px;padding:12px 16px;box-shadow:0 6px 24px #000a;font:14px/1.5 system-ui,sans-serif}' +
    '.awhelp h2{font-size:16px;margin:0 0 6px;color:#ffe28a}.awhelp p{margin:0 0 6px}.awhelp ul{margin:0 0 8px;padding-left:18px}.awhelp a{color:#8bd5ff}' +
    '.awhelp button{float:right;background:#203346;color:#edf3fa;border:1px solid #456;border-radius:5px;padding:2px 8px;cursor:pointer}' +
    '.awhelp .small{font-size:12px}';
  let helpPanel = null, helpAnchor = null;
  function closeHelp() {
    if (!helpPanel) return;
    helpPanel.remove(); helpPanel = null;
    if (helpAnchor) { helpAnchor.setAttribute('aria-expanded', 'false'); try { helpAnchor.focus(); } catch (_) { /* gone */ } }
    root.document.removeEventListener('keydown', onHelpKey, true); root.document.removeEventListener('mousedown', onHelpOutside, true);
  }
  function onHelpKey(e) { if (e.key === 'Escape') { e.preventDefault(); closeHelp(); } }
  function onHelpOutside(e) { if (helpPanel && !helpPanel.contains(e.target) && e.target !== helpAnchor) closeHelp(); }
  // help(key, anchor): open (or, when open, close) the panel for a page key (world, local, inspector, monitor, meshes, seam).
  function help(key, anchor) {
    const doc = root.document;
    if (helpPanel) { const was = helpAnchor; closeHelp(); if (was === anchor) return null; }
    const h = HELP[key] || HELP.world;
    if (!doc.getElementById('aw-help-css')) { const st = doc.createElement('style'); st.id = 'aw-help-css'; st.textContent = HELP_CSS; doc.head.appendChild(st); }
    const p = doc.createElement('div');
    p.className = 'awhelp'; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', 'Help: ' + h[0]); p.tabIndex = -1;
    p.innerHTML = '<button type="button" class="awhelpclose" aria-label="Close help">Close</button><h2>' + esc(h[0]) + '</h2><p>' + esc(h[1]) + '</p><ul>' +
      h[2].map(t => '<li>' + esc(t) + '</li>').join('') + '</ul><p><a href="' + DOCS + h[3] + '" target="_blank" rel="noopener">Read more: docs/' + esc(h[3]) + '</a></p><p class="small" style="font-size:12px;color:#9fb3c8">' + esc(NOTE) + '</p>';
    doc.body.appendChild(p);
    helpPanel = p; helpAnchor = anchor || null;
    if (anchor) anchor.setAttribute('aria-expanded', 'true');
    p.querySelector('.awhelpclose').onclick = closeHelp;
    doc.addEventListener('keydown', onHelpKey, true); doc.addEventListener('mousedown', onHelpOutside, true);
    try { p.focus(); } catch (_) { /* no focus */ }
    return p;
  }
  function markup(subtitle) {
    return '<img src="' + esc(root.AW_LOGO_SRC || LOGO) + '" alt="AmiWind" onerror="this.style.display=\'none\'">' +
      '<h1>Toolkit<button type="button" class="awnote" title="' + esc(NOTE) + '" aria-label="Help for this page" aria-haspopup="dialog" aria-expanded="false">?</button>' +
      '<small title="Set by hand when the Toolkit is next updated">' + esc(VERSION_TEXT) + '</small></h1>' +
      (subtitle ? '<span class="awsub">' + esc(subtitle) + '</span>' : '');
  }
  function mount(subtitle, hide) {
    if (root.parent !== root || !root.document) return false;      // embedded: the index header is above
    if (!root.document.body) { root.document.addEventListener('DOMContentLoaded', () => mount(subtitle, hide)); return true; }
    const style = root.document.createElement('style'); style.textContent = CSS; root.document.head.appendChild(style);
    const bar = root.document.createElement('div'); bar.className = 'awhead'; bar.innerHTML = markup(subtitle);
    root.document.body.insertBefore(bar, root.document.body.firstChild);
    const helpBtn = bar.querySelector('.awnote');
    if (helpBtn) helpBtn.onclick = () => help(KEYS[subtitle] || 'world', helpBtn);       // a button: click, Enter and Space all arrive here
    root.document.documentElement.style.setProperty('--awh', bar.offsetHeight + 'px');       // pages that size to the window subtract it
    for (const sel of [].concat(hide || [])) for (const el of root.document.querySelectorAll(sel)) el.style.display = 'none';
    return true;
  }
  // A page without a script of its own to call mount from names itself on the tag:
  //   <script src="header.js" data-subtitle="3D Map Inspector" data-hide="header h1"></script>
  const tag = typeof document !== 'undefined' && document.currentScript;
  if (tag && tag.dataset && tag.dataset.subtitle) mount(tag.dataset.subtitle, tag.dataset.hide || '');
  const api = {VERSION_TEXT, LOGO, NOTE, markup, mount, help, HELP, KEYS};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindToolkitHeader = api;
})(typeof window !== 'undefined' ? window : this);
