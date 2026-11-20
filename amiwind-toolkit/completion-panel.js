// SPDX-License-Identifier: GPL-3.0-only
// The World Map's completion panel per game (TOOLKIT-EXPANSION-COMPLETION-67): for Tribunal (Mournhold), Bloodmoon (Solstheim)
// and Morrowind (Vvardenfell), by number: the cells and rooms, the scripts by state, the variables, the things placed by kind,
// the start scripts and the load doors. Every count opens the list behind it. The numbers are the tracker data's own
// (`readiness` and `completion`, written by tools/master_completion.py during the ingest); what no source measures yet says
// "not measured yet" with the work item that will measure it, never a guess. Pure functions (no DOM): world-map.html puts
// the HTML in its panel and opens a list when its count is clicked. tests/test_completion_panel.js runs them with node.
(function (root) {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const num = v => Number(v || 0).toLocaleString('en-US');
  const ORDER = ['mournhold', 'solstheim', 'vvardenfell'];
  const GAMES = {mournhold: 'Tribunal', solstheim: 'Bloodmoon', vvardenfell: 'Morrowind'};
  const TODO = 'MOURNHOLD-STATE-TRACKING-PARITY-67';
  const KIND_LABELS = {people: 'People', creatures: 'Creatures', items: 'Items', containers: 'Containers', doors: 'Doors',
    activators: 'Activators', lights: 'Lights'};
  const fig = f => num(f.ready) + ' of ' + num(f.total) + ' (' + (+f.percent).toFixed(1) + ' %)';
  const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const nm = (todo, why) => '<span class="cpnm" title="' + esc(why || 'No source in the tracker data measures this yet') + '">not measured yet</span> <span class="muted">(' + esc(todo || TODO) + ')</span>';

  // The games the panel offers, in order (Tribunal first): [{id, game, land}] of the masters the data has.
  function masters(completion, ready) {
    const lands = ((ready && ready.lands) || []);
    return ORDER.filter(id => lands.some(l => l.id === id)).map(id => {
      const l = lands.find(x => x.id === id);
      return {id, game: GAMES[id], land: l.name};
    });
  }
  // A count that opens its list: the number links to the list's own block below the table.
  function link(listId, n) { return n ? '<a href="#' + esc(listId) + '" class="cplink" data-cplist="' + esc(listId) + '">' + num(n) + '</a>' : num(n); }
  function listBlock(listId, title, items, line) {
    if (!items || !items.length) return '';
    return '<details class="cplist" id="' + esc(listId) + '"><summary>' + esc(title) + ' (' + num(items.length) + ')</summary><ul>' +
      items.map(i => '<li>' + line(i) + '</li>').join('') + '</ul></details>';
  }
  // The panel of one game: a table (what, count, source) and the lists its counts open.
  function panelHtml(completion, ready, id) {
    const land = ((ready && ready.lands) || []).find(l => l.id === id);
    if (!land) return '<p class="muted">No tracker data for this game.</p>';
    const m = ((completion && completion.masters) || []).find(x => x.id === id) || null;
    const p = 'cp-' + id + '-', rows = [], lists = [];
    const row = (what, count, source, cls) => rows.push('<tr' + (cls ? ' class="' + cls + '"' : '') + '><td class="l">' + what + '</td><td class="l">' + count + '</td><td class="l muted">' + source + '</td></tr>');
    const head = text => rows.push('<tr class="cphead"><th class="l" colspan="3">' + esc(text) + '</th></tr>');
    // 1. cells and rooms (the unified count)
    head('1. Cells and rooms (ready = in the game on CHIM)');
    const tNot = [].concat(...land.terrain.not_ready.map(r => r.items.map(i => Object.assign({reason: r.label}, i))));
    row('Open terrain (exterior cells) ready', fig(land.terrain) + (tNot.length ? ' · not ready ' + link(p + 'terrain', tNot.length) : ''), 'tracker data: every cell\'s state in the newest ingested build');
    lists.push(listBlock(p + 'terrain', 'Open terrain not ready', tNot, i => esc(i.name || 'cell') + ' <span class="muted">(cell ' + esc(i.id) + '; ' + esc(i.reason) + ')</span>'));
    const rNot = [].concat(...land.rooms.not_ready.map(r => r.items.map(i => Object.assign({reason: r.label}, i))));
    row('Rooms (interiors) ready', fig(land.rooms) + (rNot.length ? ' · not ready ' + link(p + 'rooms', rNot.length) : ''), 'tracker data: the door graph\'s rooms and the rooms the newest build holds');
    lists.push(listBlock(p + 'rooms', 'Rooms not ready, by name', rNot, i => esc(i.name) + ' <span class="muted">(' + esc(i.reason) + (i.leads && i.access !== 'door' ? '; what leads there: ' + esc(i.leads) : '') + ')</span>'));
    // the special interiors: ready rooms (in the count) in the game as room maps of our own, named from the data, never a
    // reason (TRACKER-ROOM-MAPS-NOT-READY-67)
    const special = land.rooms.special || [];
    if (special.length) {
      row('&nbsp;&nbsp;ready, special interiors (room maps of our own)', link(p + 'special', special.length), 'in the game as a room map of our own, not on CHIM rooms');
      lists.push(listBlock(p + 'special', 'Special interiors, in the game as room maps of our own', special.map(n => ({name: n})), i => esc(i.name)));
    }
    for (const r of land.rooms.not_ready) row('&nbsp;&nbsp;' + esc(r.label), link(p + 'rooms', r.count), 'the room\'s state');
    const asT = land.rooms.as_terrain || [];
    if (asT.length) {
      row('Districts counted once, as open terrain', link(p + 'asterrain', asT.length), 'a room whose name is one of the land\'s open-terrain cells');
      lists.push(listBlock(p + 'asterrain', 'Districts counted as open terrain', asT.map(n => ({name: n})), i => esc(i.name)));
    }
    row('<b>Total ready</b>', '<b>' + fig(land.total) + '</b>', 'open terrain + rooms');
    // 2. scripts
    head('2. Scripts of ' + GAMES[id] + ' (' + (land.master || '') + ')');
    const sc = m && m.scripts;
    if (sc) {
      row('Used in the original game', num(sc.used) + ' of ' + num(sc.all) + ' script records', 'MWScript tracker, measured ' + esc(sc.measured || '?') + ' (AmiWind v' + esc(sc.version || '?') + ')');
      for (const s of sc.states) {
        if (!s.count) continue;
        const lid = p + 'scripts-' + slug(s.state);
        row('&nbsp;&nbsp;' + esc(s.label), link(lid, s.count), s.state === 'inert' ? 'never runs in the original either: not counted as used' : 'the state worked out from the interpreter\'s function table');
        lists.push(listBlock(lid, 'Scripts: ' + s.label, s.items, i => esc(i.id) + (i.missing && i.missing.length ? ' <span class="muted">(lacks ' + esc(i.missing.join(', ')) + ')</span>' : (i.why ? ' <span class="muted">(' + esc(i.why) + ')</span>' : ''))));
      }
    } else row('Scripts by state', nm(TODO, 'This tracker data has no completion section: run the tracker ingest with this Toolkit\'s tools'), 'MWScript tracker');
    // 3. variables
    head('3. Variables');
    row('Globals of ' + GAMES[id], nm(TODO), 'no measuring step counts them yet');
    row('Journal topics of ' + GAMES[id], nm(TODO), 'no measuring step counts them yet');
    row('Carried and kept by the save\'s state table', nm(TODO), 'no measuring step reads the save\'s tables yet');
    // 4. placed things
    head('4. Things placed, by kind (in ' + land.name + '\'s own cells)');
    const pl = m && m.placed, orig = pl && pl.original;
    if (orig) {
      rows.push('<tr><th class="l">Kind</th><th class="l">Placed in the original</th><th class="l">In the game · keyed in the save\'s change list · aimable</th></tr>');
      for (const k of Object.keys(KIND_LABELS)) if (orig[k] != null) row(esc(KIND_LABELS[k]), num(orig[k]), nm(pl.todo) + (pl.gap ? ' <span class="muted">known gap ' + esc(pl.gap) + '</span>' : ''));
      row('Source', 'census of the original masters', 'every placement of the land\'s cells, the three masters merged as the game merges them');
    } else row('Placed things by kind', nm(TODO, 'This tracker data has no census'), 'census');
    // 5. start scripts
    head('5. Start scripts');
    const st = sc ? sc.start : null;
    if (st && st.length) for (const s of st) row(esc(s.id), esc(s.label), esc(s.why || 'started when the game starts'));
    else if (sc) row('Start scripts', 'none of its own', 'MWScript tracker');
    else row('Start scripts', nm(TODO), 'MWScript tracker');
    // 6. exits and entrances
    head('6. Exits and entrances');
    const d = m && m.doors;
    if (d && d.load_doors != null) {
      row('Load doors in its cells', num(d.load_doors), 'census door records of the original');
      row('&nbsp;&nbsp;with a load door back', num(d.with_way_back), 'the place a door leads to has a door back');
      row('&nbsp;&nbsp;one way', link(p + 'oneway', d.one_way.length), 'no door back found in the census');
      lists.push(listBlock(p + 'oneway', 'Load doors with no door back', d.one_way, i => esc(i.from) + ' &rarr; ' + esc(i.to)));
    } else row('Load doors', nm(TODO, 'This tracker data has no census door records'), 'census');
    row('Verified in the build\'s door tables', nm(TODO, 'The tracker data does not read the image\'s door tables yet'), d && d.gap ? 'known gap ' + esc(d.gap) : '');
    const nd = (d && d.rooms_no_door) || [].concat(...land.rooms.not_ready.map(r => r.items)).filter(i => (i.access || 'door') !== 'door');
    row('Rooms no door leads to (rooms still to build)', link(p + 'nodoor', nd.length), 'the door graph: what leads there');
    lists.push(listBlock(p + 'nodoor', 'Rooms no door leads to, and what leads there', nd, i => esc(i.name) + ' <span class="muted">(' + esc(i.leads || i.access || '') + ')</span>'));
    return '<h3>' + esc(GAMES[id]) + ': ' + esc(land.name) + '</h3><p class="muted">Every count opens the list behind it. ' +
      esc((ready && ready.definition) || '') + (ready && ready.build ? ' Counted against ' + esc(ready.build) + '.' : '') + '</p>' +
      '<table class="mt cptable"><tbody>' + rows.join('') + '</tbody></table>' + lists.join('');
  }
  // The switch above the panel: one button per game, Tribunal first.
  function switchHtml(list, current) {
    return list.map(g => '<button type="button" data-cp="' + esc(g.id) + '" aria-pressed="' + (g.id === current) + '">' + esc(g.game) + ' (' + esc(g.land) + ')</button>').join('');
  }
  const api = {ORDER, GAMES, TODO, masters, panelHtml, switchHtml};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AmiWindCompletion = api;
})(typeof window !== 'undefined' ? window : this);
