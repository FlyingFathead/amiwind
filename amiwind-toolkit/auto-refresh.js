// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit's auto-refresh: a page served by tools/toolkit_serve.py asks /amiwind-toolkit/version.json every 30 seconds
// (the commit served, the version line, the tracker data's last write) and reloads itself when any of them changes, so
// the page in front of you is always the newest. The pages keep the viewer's state in the browser (zoom, pan, selected
// pane: chim-legend.js save/load), so a reload puts everything back; a short note says a newer version was loaded.
// Off when the page is opened from a file (no server to ask) and when the server has no stamp (404).
// AutoRefresh.changed(old, new) is the same rule as tools/toolkit_stamp.py changed().
(function (root) {
  const FORMAT = 'aw-toolkit-stamp-1', WATCHED = ['commit', 'version', 'line', 'ingest'];
  const EVERY_MS = 30000, NOTE_KEY = 'amiwind-toolkit-reloaded-1', STAMP_KEY = 'amiwind-toolkit-stamp-1';
  function same(a, b) { return JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b); }
  function changed(oldStamp, newStamp) {
    if (!oldStamp || typeof oldStamp !== 'object' || !newStamp || newStamp.format !== FORMAT) return false;
    return WATCHED.some(k => !same(oldStamp[k], newStamp[k]));
  }
  function what(oldStamp, newStamp) {
    const parts = [];
    if (!same(oldStamp.commit, newStamp.commit) || !same(oldStamp.version, newStamp.version)) parts.push('the Toolkit' + (newStamp.version ? ' (AmiWind ' + newStamp.version + ')' : ''));
    if (!same(oldStamp.ingest, newStamp.ingest)) parts.push('the tracker data');
    if (!parts.length) parts.push('the Toolkit');
    return parts.join(' and ');
  }
  function store(kind) { try { return root[kind]; } catch (_) { return null; } }
  function showNote(doc) {
    const s = store('sessionStorage'); let text = null;
    try { text = s && s.getItem(NOTE_KEY); if (s) s.removeItem(NOTE_KEY); } catch (_) { text = null; }
    if (!text || !doc || !doc.body) return;
    const el = doc.createElement('div');
    el.setAttribute('role', 'status');
    el.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99999;background:#12304a;color:#edf3fa;border:1px solid #46c37b;border-radius:6px;padding:8px 12px;font:13px system-ui,sans-serif;max-width:80vw';
    el.textContent = text;
    doc.body.appendChild(el);
    root.setTimeout(() => el.remove(), 8000);
  }
  function start(win, fetchFn) {
    const loc = win.location;
    if (!loc || !/^https?:$/.test(loc.protocol)) return null;           // opened from a file: nothing to ask
    let known = null, timer = null;
    const url = new URL('version.json', loc.href).href;
    async function poll() {
      try {
        const r = await fetchFn(url, {cache: 'no-store'});
        if (!r.ok) { if (r.status === 404 && timer) { win.clearInterval(timer); timer = null; } return; }
        const now = await r.json();
        if (!now || now.format !== FORMAT) return;
        if (known && changed(known, now)) {
          try { win.sessionStorage.setItem(NOTE_KEY, 'A newer version of ' + what(known, now) + ' was loaded.'); } catch (_) { /* no storage: the page just reloads */ }
          loc.reload();
          return;
        }
        known = now;
      } catch (_) { /* server busy or gone: try again next time */ }
    }
    poll();
    timer = win.setInterval(poll, EVERY_MS);
    return {poll, stop: () => timer && win.clearInterval(timer)};
  }
  const api = {FORMAT, WATCHED, EVERY_MS, changed, what, start};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else if (root.document) {
    root.AutoRefresh = api;
    showNote(root.document);
    start(root, root.fetch.bind(root));
  }
})(typeof window !== 'undefined' ? window : this);
