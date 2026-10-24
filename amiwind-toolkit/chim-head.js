// SPDX-License-Identifier: GPL-3.0-only
// The CHIM Progress Tracker's headline, shared by the Toolkit page (index.html) and the World Map page run on its own.
// ChimHead.render(el, headline, history, onPick, picked): "<island> Done: <done> of <cells> (<pct> %)" with cell/terrain complete, other islands separately, the breakdown
// below it (every number picks those cells on the map) and a small history line (passed cells per day).
// Data with the legend groups (tools/cell_progress.py classify, TOOLKIT-LEGEND-STATES-UNCLEAR-48) draws the chips under three
// headers: In the game, Not in the game yet, Beyond the world's edge: settled. A chip whose count is 0 waits in the "More
// states" fold-out and comes back by itself when it has cells. Older data draws the flat row of chips as before.
// A cell is successful when it is converted and every measured audit passed; unmeasured audits are counted apart and
// never as passed. Nothing here reads game data: it only draws the numbers it is given.
(function (root) {
  const esc = t => String(t).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
  const PARTS = [
    ['complete', 'cell complete', '#7dffa6'],
    ['terrain_complete', 'terrain complete', '#7dffa6'],
    ['complete_unlit', 'cell complete, awaiting lighting', 'repeating-linear-gradient(135deg,#7dffa6 0 4px,#00e5ff 4px 7px)'],
    ['terrain_complete_unlit', 'terrain complete, awaiting lighting', 'repeating-linear-gradient(135deg,#7dffa6 0 4px,#00e5ff 4px 7px)'],
    ['approved', 'maintainer-approved', '#ffd23f'],
    ['playtested', 'playtested', '#2ec4b6'],
    ['audits_passed', 'passed (something deferred)', '#46c37b'],
    ['converted_failing', 'converted, failing audits', '#e5484d'],
    ['not_converted', 'not converted (tried, could not finish)', '#c2185b'],
    ['converted_unmeasured', 'converted, nothing measured', '#6ea4df'],
    ['not_started', 'not started', '#8a9bad'],
    ['empty_sea', 'empty sea', '#2f7fa6'],
    ['sea_in_game', 'sea, in the game (CHIM)', 'repeating-linear-gradient(135deg,#2f7fa6 0 4px,#7dffa6 4px 7px)'],
    ['ocean', 'open ocean, not counted as done (shared ocean chunk made, not yet placed)', '#c0c6cc'],
    ['hull_policy_pending', 'hull policy pending', '#b07ae0'],
  ];
  // The grouped chips: state -> [label, colour, hover text]. The colours are the map's (world-map.html CHIM_BUCKETS).
  const STRIPES = (a, b) => 'repeating-linear-gradient(135deg,' + a + ' 0 4px,' + b + ' 4px 7px)';
  const SETTLED_GREY = '#5a626b';
  const SETTLED_TEXT = "No cell exists here in the original game data. AmiWind's edge current turns the player back before this point, so there is nothing to build.";
  const STATE_PARTS = {
    complete: ['cell complete', '#7dffa6', 'Everything converted, every audit passed, lit like the original'],
    terrain_complete: ['terrain complete', '#7dffa6', 'Everything but actors converted, every audit passed, lit'],
    complete_unlit: ['cell complete, awaiting lighting', STRIPES('#7dffa6', '#00e5ff'), 'Cell complete except the lighting audit'],
    terrain_complete_unlit: ['terrain complete, awaiting lighting', STRIPES('#7dffa6', '#00e5ff'), 'Terrain complete except the lighting audit'],
    approved: ['maintainer-approved', '#ffd23f', 'In the game and approved by the maintainer'],
    playtested: ['playtested', '#2ec4b6', 'In the game and playtested'],
    audits_passed: ['passed (something deferred)', '#46c37b', 'In the game; every measured audit passed, something placed is still deferred'],
    converted_unmeasured: ['in the game, nothing measured', '#6ea4df', 'In the newest build; no audit measured yet'],
    sea_in_game: ['sea, in the game', STRIPES('#2f7fa6', '#7dffa6'), 'Sea cells the newest build holds: empty sea and open water the game defines'],
    solstheim: ['Solstheim (Bloodmoon)', '#7f6fb0', 'Solstheim, the Bloodmoon island: not in the game yet'],
    not_started: ['not started', '#8a9bad', 'Cells the game defines that the conversion has not reached yet'],
    not_in_build: ['converted, not in the newest build', '#4f6f93', 'Converted cells the newest ingested build does not hold'],
    empty_sea: ['empty sea, not in the newest build', '#2f7fa6', 'Sea cells measured empty that the newest build does not hold'],
    ocean: ['open sea, not in the newest build', '#c0c6cc', 'Open sea the game defines (a cell record without LAND) that the newest build does not hold'],
    converted_failing: ['converted, failing audits', '#e5484d', 'At least one audit failed or the conversion reported an error'],
    not_converted: ['not converted (tried, could not finish)', '#c2185b', 'The conversion was tried and could not finish the cell'],
    hull_policy_pending: ['hull policy pending', '#b07ae0', 'Converted; only a standing-hull chain deeper than the limit is left'],
    settled: ['settled', SETTLED_GREY, SETTLED_TEXT],
  };
  const GROUP_HINTS = {in_game: 'What the newest ingested build ships', not_in_game: 'Work left',
    settled: SETTLED_TEXT + ' Counted toward "accounted for", never toward the cells in the game.'};
  const MORE_KEY = 'amiwind-chim-more-1', OPEN = '\u25be', CLOSED = '\u25b8';
  function moreOpen() { try { return root.localStorage.getItem(MORE_KEY) === 'open'; } catch (_) { return false; } }
  function setMoreOpen(v) { try { root.localStorage.setItem(MORE_KEY, v ? 'open' : 'closed'); } catch (_) { /* no storage: lasts until reload */ } }
  const CSS = '.chimgroups{display:flex;flex-direction:column;gap:4px;width:100%}.chimgroup{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}' +
    '.chimgh{font-size:12px;font-weight:600;color:#9fb3c8;min-width:13em}.chimgh b{color:#edf3fa}.chimmore .chimmorebtn{background:none;border:0;color:#9fb3c8;padding:2px 5px}' +
    '.chimmore .chimparts[hidden]{display:none!important}.chimgroup[data-group="settled"] button i{opacity:.55}';
  const fmt = n => (n || 0).toLocaleString();
  function chip(k, n, picked, extra) {
    const [t, c, tip] = STATE_PARTS[k] || [k, '#3a4f66', ''];
    return '<button type="button" data-bucket="' + k + '" aria-pressed="' + (picked === k ? 'true' : 'false') + '" title="' + esc(tip + (extra || '') + '. Click to highlight these cells on the map.') +
      '"><i style="background:' + c + '"></i>' + esc(t) + ' <b>' + fmt(n) + '</b></button>';
  }
  // The grouped chips (layout from ChimLegend.groupLayout's rule, repeated here so the index page needs no other script).
  const GROUPS = [['in_game', 'In the game', ['complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved', 'playtested', 'audits_passed', 'converted_unmeasured', 'sea_in_game']],
    ['not_in_game', 'Not in the game yet', ['solstheim', 'not_started', 'not_in_build', 'empty_sea', 'ocean', 'converted_failing', 'not_converted', 'hull_policy_pending']],
    ['settled', "Beyond the world's edge: settled", ['settled']]];
  function layout(h) {
    if (!h || !h.groups || !h.states) return null;
    const out = {groups: [], more: []};
    for (const [id, title, states] of GROUPS) {
      const rows = [];
      for (const s of states) { const n = h.states[s] || 0; if (n) rows.push([s, n]); else out.more.push([s, 0, id]); }
      out.groups.push({id, title, count: h.groups[id] || 0, rows});
    }
    out.accounted = h.groups.accounted_for || 0; out.cells = h.groups.cells || 0;
    return out;
  }
  function groupsHtml(h, picked) {
    const g = layout(h);
    const titles = Object.fromEntries(GROUPS.map(([id, t]) => [id, t]));
    const open = moreOpen();
    return '<span class="chimgroups">' + g.groups.map(x => '<span class="chimgroup" data-group="' + x.id + '"><span class="chimgh" title="' + esc(GROUP_HINTS[x.id]) + '">' + esc(x.title) +
      ' <b>' + fmt(x.count) + '</b></span><span class="chimparts">' + (x.rows.length ? x.rows.map(([k, n]) => chip(k, n, picked)).join('') : '<span class="chimnote">none</span>') + '</span></span>').join('') +
      (g.more.length ? '<span class="chimgroup chimmore"><button type="button" class="chimmorebtn" aria-expanded="' + open + '">' + (open ? OPEN : CLOSED) + ' More states (' + g.more.length +
        ' with no cells now)</button><span class="chimparts"' + (open ? '' : ' hidden') + '>' + g.more.map(([k, n, id]) => chip(k, n, picked, ' (' + titles[id] + ')')).join('') + '</span></span>' : '') +
      '<span class="chimnote" title="In the game plus settled: every cell whose fate is known">accounted for: ' + fmt(g.accounted) + ' of ' + fmt(g.cells) + ' cells (in the game ' +
      fmt(g.groups[0].count) + ' + settled ' + fmt(g.groups[2].count) + '; settled cells never count as in the game)</span></span>';
  }
  function spark(history) {
    const pts = (history || []).filter(h => h && h.land_cells);
    if (pts.length < 2) return '';
    const W = 90, H = 20, max = Math.max(1, ...pts.map(h => h.passed)), n = pts.length;
    const xy = pts.map((h, i) => (i * (W - 4) / (n - 1) + 2).toFixed(1) + ',' + (H - 2 - (H - 4) * h.passed / max).toFixed(1));
    return '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="passed cells per day">' +
      '<polyline points="' + xy.join(' ') + '" fill="none" stroke="#46c37b" stroke-width="1.6"/></svg>';
  }
  // Island-wide lighting line (tools/cell_lighting.py): lit is required for both completion levels.
  function lightLine(lt) {
    if (!lt || !lt.status) return '';
    const s = lt.status, r = lt.reach || {};
    return '<span class="chimnote" title="A cell is only complete when it is lit like the original">lighting: lit ' + (s.lit || 0).toLocaleString() +
      ' · partial ' + (s.partial || 0).toLocaleString() + ' · unlit ' + (s.unlit || 0).toLocaleString() + ' · lights baked ' + (r.baked || 0).toLocaleString() +
      ', night lamps only ' + (r.lamp_table || 0).toLocaleString() + ', not represented ' + (r.none || 0).toLocaleString() + '</span>';
  }
  function render(el, h, history, onPick, picked) {
    if (!el) return;
    const doc = el.ownerDocument;
    if (doc && doc.head && !doc.getElementById('chim-head-css')) {
      const st = doc.createElement('style'); st.id = 'chim-head-css'; st.textContent = CSS; doc.head.appendChild(st);
    }
    if (!h) { el.innerHTML = ''; el.hidden = true; return; }
    el.hidden = false;
    const grouped = !!(h.groups && h.states);
    const isl = (h.islands || []).find(i => i.island === 1) || {done: h.passed, cells: h.land_cells, percent: h.percent, complete: 0, terrain_complete: 0};
    const pct = (+isl.percent).toFixed(1) + ' %';
    const others = (h.islands || []).filter(i => i.island !== 1).map(i => esc(i.name) + ': ' + (i.done ? i.done.toLocaleString() + ' of ' + i.cells.toLocaleString() + ' done' : 'not started') + ', ' + i.cells.toLocaleString() + ' cells').join(' · ');
    const hist = (history || []).slice(-5).map(x => esc(x.date.slice(5, 10)) + ' ' + x.passed).join(' · ');
    el.innerHTML = '<span class="chimtitle">' + esc(isl.name || 'CHIM cells') + ' <b>Done: ' + isl.done.toLocaleString() + ' of ' + isl.cells.toLocaleString() +
      ' (' + pct + ')</b> · cell complete ' + (isl.complete || 0).toLocaleString() + ' · terrain complete ' + (isl.terrain_complete || 0).toLocaleString() +
      ' · awaiting lighting ' + ((isl.complete_unlit || 0) + (isl.terrain_complete_unlit || 0)).toLocaleString() +
      (isl.eligible != null ? ' · <b>eligible for ' + esc(h.eligible_release || 'next release') + ': ' + isl.eligible.toLocaleString() + '</b>' : '') +
      (others ? ' · ' + others : '') +
      (grouped ? ' · <b>in the game: ' + fmt(h.groups.in_game) + '</b>' + (h.in_game_build ? ' (' + esc(h.in_game_build) + ')' : '') + ' · accounted for ' + fmt(h.groups.accounted_for) + ' of ' + fmt(h.groups.cells) : '') +
      '</span>' + (grouped ? groupsHtml(h, picked) : '<span class="chimparts">' +
      PARTS.filter(([k]) => k !== 'sea_in_game' || h.sea_in_game != null).map(([k, t, c]) => '<button type="button" data-bucket="' + k + '" aria-pressed="' + (picked === k ? 'true' : 'false') +
        '" title="Highlight these cells on the map"><i style="background:' + c + '"></i>' + esc(t) + ' <b>' + (h[k] || 0).toLocaleString() +
        '</b></button>').join('') +
      '</span>') + lightLine(h.lighting) + '<span class="chimnote">unmeasured audits on ' + (h.with_unmeasured_audits || 0) + ' converted cell' +
      (h.with_unmeasured_audits === 1 ? '' : 's') + ' (never counted as passed)</span>' +
      (hist ? '<span class="chimhist" title="Passed cells per day, last five days">' + spark(history) + ' ' + hist + '</span>' : '');
    for (const b of el.querySelectorAll('button[data-bucket]')) b.onclick = () => onPick && onPick(b.dataset.bucket);
    const more = el.querySelector('.chimmorebtn');
    if (more) more.onclick = () => {
      const open = more.getAttribute('aria-expanded') !== 'true';
      setMoreOpen(open);
      more.setAttribute('aria-expanded', open ? 'true' : 'false');
      more.textContent = (open ? OPEN : CLOSED) + more.textContent.slice(1);
      more.nextElementSibling.hidden = !open;
    };
  }
  const api = {render, PARTS, STATE_PARTS, GROUPS, SETTLED_TEXT, SETTLED_GREY, layout, groupsHtml, MORE_KEY};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ChimHead = api;
})(typeof window !== 'undefined' ? window : this);
