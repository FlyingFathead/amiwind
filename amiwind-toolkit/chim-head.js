// SPDX-License-Identifier: GPL-3.0-only
// The CHIM Progress Tracker's headline, shared by the Toolkit page (index.html) and the World Map page run on its own.
// ChimHead.render(el, headline, history, onPick, picked): "<island> Done: <done> of <cells> (<pct> %)" with cell/terrain complete, other islands separately, the breakdown
// below it (every number picks those cells on the map) and a small history line (passed cells per day).
// A cell is successful when it is converted and every measured audit passed; unmeasured audits are counted apart and
// never as passed. Nothing here reads game data: it only draws the numbers it is given.
(function () {
  const esc = t => String(t).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
  const PARTS = [
    ['complete', 'cell complete', '#7dffa6'],
    ['terrain_complete', 'terrain complete', '#7dffa6'],
    ['approved', 'owner-approved', '#ffd23f'],
    ['playtested', 'playtested', '#2ec4b6'],
    ['audits_passed', 'passed (something deferred)', '#46c37b'],
    ['converted_failing', 'converted, failing audits', '#e5484d'],
    ['not_converted', 'not converted (tried, could not finish)', '#c2185b'],
    ['converted_unmeasured', 'converted, nothing measured', '#6ea4df'],
    ['not_started', 'not started', '#8a9bad'],
    ['empty_sea', 'empty sea', '#2f7fa6'],
    ['hull_policy_pending', 'hull policy pending', '#b07ae0'],
  ];
  function spark(history) {
    const pts = (history || []).filter(h => h && h.land_cells);
    if (pts.length < 2) return '';
    const W = 90, H = 20, max = Math.max(1, ...pts.map(h => h.passed)), n = pts.length;
    const xy = pts.map((h, i) => (i * (W - 4) / (n - 1) + 2).toFixed(1) + ',' + (H - 2 - (H - 4) * h.passed / max).toFixed(1));
    return '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="passed cells per day">' +
      '<polyline points="' + xy.join(' ') + '" fill="none" stroke="#46c37b" stroke-width="1.6"/></svg>';
  }
  function render(el, h, history, onPick, picked) {
    if (!el) return;
    if (!h) { el.innerHTML = ''; el.hidden = true; return; }
    el.hidden = false;
    const isl = (h.islands || []).find(i => i.island === 1) || {done: h.passed, cells: h.land_cells, percent: h.percent, complete: 0, terrain_complete: 0};
    const pct = (+isl.percent).toFixed(1) + ' %';
    const others = (h.islands || []).filter(i => i.island !== 1).map(i => esc(i.name) + ': ' + (i.done ? i.done.toLocaleString() + ' of ' + i.cells.toLocaleString() + ' done' : 'not started') + ', ' + i.cells.toLocaleString() + ' cells').join(' · ');
    const hist = (history || []).slice(-5).map(x => esc(x.date.slice(5, 10)) + ' ' + x.passed).join(' · ');
    el.innerHTML = '<span class="chimtitle">' + esc(isl.name || 'CHIM cells') + ' <b>Done: ' + isl.done.toLocaleString() + ' of ' + isl.cells.toLocaleString() +
      ' (' + pct + ')</b> · cell complete ' + (isl.complete || 0).toLocaleString() + ' · terrain complete ' + (isl.terrain_complete || 0).toLocaleString() +
      (others ? ' · ' + others : '') + '</span><span class="chimparts">' +
      PARTS.map(([k, t, c]) => '<button type="button" data-bucket="' + k + '" aria-pressed="' + (picked === k ? 'true' : 'false') +
        '" title="Highlight these cells on the map"><i style="background:' + c + '"></i>' + esc(t) + ' <b>' + (h[k] || 0).toLocaleString() +
        '</b></button>').join('') +
      '</span><span class="chimnote">unmeasured audits on ' + (h.with_unmeasured_audits || 0) + ' converted cell' +
      (h.with_unmeasured_audits === 1 ? '' : 's') + ' (never counted as passed)</span>' +
      (hist ? '<span class="chimhist" title="Passed cells per day, last five days">' + spark(history) + ' ' + hist + '</span>' : '');
    for (const b of el.querySelectorAll('button[data-bucket]')) b.onclick = () => onPick && onPick(b.dataset.bucket);
  }
  window.ChimHead = {render, PARTS};
})();
