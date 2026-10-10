// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit's shared header: the gold AmiWind logo, "Toolkit" with "Last updated with AmiWind vX" under it, and the page's
// own name as a subtitle. index.html keeps its markup exactly (logo, Toolkit, the World / Local / 3D Inspector buttons); this
// is the same logo block for every Toolkit page opened on its own. Embedded pages (inside index.html) show nothing: the
// index header is already above them. tests/test_cell_progress.py checks that the logo block here and in index.html agree.
//   AmiWindToolkitHeader.mount('World Map', '#pagetitle')   adds the header at the top of the page, hides the old title
// The logo address can be replaced before mount (window.AW_LOGO_SRC), as the standalone inspector export does with a data URI.
(function (root) {
  const VERSION_TEXT = 'Last updated with AmiWind v0.0.33';      // set by hand when the Toolkit is next updated, as in index.html
  const LOGO = '../resources/media/AmiWind_logo_name_only.png';
  const NOTE = 'Everything here runs in your browser. Views of the world are made from your own Morrowind files and build output ' +
    'on your machine; nothing is uploaded.';
  const CSS = '.awhead{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:8px 16px;border-bottom:1px solid #345;' +
    'background:#162433;color:#edf3fa;font:14px system-ui,sans-serif}.awhead img{height:46px;width:auto}' +
    '.awhead h1{font-size:24px;margin:0 6px 0 -4px;font-weight:700;color:#e8c46a;letter-spacing:.5px;line-height:1.1;white-space:normal}' +
    '.awhead h1 small{display:block;font-size:11px;font-weight:400;color:#9fb3c8;letter-spacing:0}' +
    '.awhead .awsub{font-size:18px;color:#ffe28a}.awhead .awnote{color:#9fb3c8;font-size:12px;margin-left:auto;flex:1 1 260px;min-width:0;' +
    'max-width:520px;text-align:right;line-height:1.35}@media (max-width:820px){.awhead .awnote{flex-basis:100%;max-width:none;text-align:left;margin-left:0}}';
  function esc(t) { return String(t).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch])); }
  function markup(subtitle) {
    return '<img src="' + esc(root.AW_LOGO_SRC || LOGO) + '" alt="AmiWind" onerror="this.style.display=\'none\'">' +
      '<h1>Toolkit<small title="Set by hand when the Toolkit is next updated">' + esc(VERSION_TEXT) + '</small></h1>' +
      (subtitle ? '<span class="awsub">' + esc(subtitle) + '</span>' : '') + '<span class="awnote">' + esc(NOTE) + '</span>';
  }
  function mount(subtitle, hide) {
    if (root.parent !== root || !root.document) return false;      // embedded: the index header is above
    if (!root.document.body) { root.document.addEventListener('DOMContentLoaded', () => mount(subtitle, hide)); return true; }
    const style = root.document.createElement('style'); style.textContent = CSS; root.document.head.appendChild(style);
    const bar = root.document.createElement('div'); bar.className = 'awhead'; bar.innerHTML = markup(subtitle);
    root.document.body.insertBefore(bar, root.document.body.firstChild);
    root.document.documentElement.style.setProperty('--awh', bar.offsetHeight + 'px');       // pages that size to the window subtract it
    for (const sel of [].concat(hide || [])) for (const el of root.document.querySelectorAll(sel)) el.style.display = 'none';
    return true;
  }
  // A page without a script of its own to call mount from names itself on the tag:
  //   <script src="header.js" data-subtitle="3D Map Inspector" data-hide="header h1"></script>
  const tag = typeof document !== 'undefined' && document.currentScript;
  if (tag && tag.dataset && tag.dataset.subtitle) mount(tag.dataset.subtitle, tag.dataset.hide || '');
  const api = {VERSION_TEXT, LOGO, NOTE, markup, mount};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindToolkitHeader = api;
})(typeof window !== 'undefined' ? window : this);
