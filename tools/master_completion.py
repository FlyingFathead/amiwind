# SPDX-License-Identifier: GPL-3.0-only
"""The unified readiness count per land and the completion panel per master (TOOLKIT-EXPANSION-COMPLETION-67).

One definition of "ready", the same for every land, written by the tracker ingest (tools/cell_progress.py) into its data
as `readiness` and `completion`; the Toolkit (amiwind-toolkit/expansion-views.js readiness(), chim-head.js,
completion-panel.js) and the generated page docs/chim/PROGRESS_TRACKER.md (tools/cell_progress_state.py) draw these
numbers and never count on their own. Pure functions over data the tracker already holds: nothing is measured here.

READY (READY_TEXT below says it in plain words):
  open terrain  a land's exterior cells of land or empty sea (the open ocean and the cells beyond the world's edge are
                not counted). Ready: the newest ingested build holds it on CHIM and no audit of it failed (the cell's
                legend group is "in the game").
  rooms         every interior cell of the game, counted for the land of its master (Tribunal: Mournhold, Bloodmoon:
                Solstheim, the base game: Vvardenfell; a base-game room on Solstheim counts for Solstheim). Ready: in the
                game, the in-game group of tools/cell_progress_rooms.py: on CHIM rooms, as a room map of our own, or as
                a district. The room maps of our own (the opening sequence's Imperial Prison Ship and Seyda Neen,
                Census and Excise Office today) are special interiors: ready, and named under the count (`special`,
                the rows whose state is room_map; TRACKER-ROOM-MAPS-NOT-READY-67). A room the game presents as the
                land's open terrain (Mournhold's districts) is counted once, under open terrain
                (TRACKER-DISTRICTS-COUNTED-TWICE-67).
  not ready     everything else, each with its reason: converted but not in the game yet, not started, and a room no
                door leads to: still to build, with what leads there (ROOMS-SET-ASIDE-NOT-BUILT-67); it is never left
                out of the count.

The completion panel per master (Tribunal, Bloodmoon, Morrowind) adds, from the same data and the MWScript tracker
(docs/mwscript-features.json, its states worked out again by tools/mwscript_features.py): the scripts by state, each
by name; the start scripts; the things placed in the original by kind (the census counts of the land's cells); the load
doors in its cells and whether each has a way back (the census door records). What no source measures yet is None,
named with the TODO item that will measure it (NOT_MEASURED), never a guess.
"""
import collections
import json
from pathlib import Path

# -2: a room map of our own counts ready and is named as a special interior (TRACKER-ROOM-MAPS-NOT-READY-67); data
# written as -1 counted it not ready, so every reader counts such data again by the rules below
FORMAT = 'aw-land-readiness-2'
COMPLETION_FORMAT = 'aw-master-completion-1'
NOT_MEASURED = 'MOURNHOLD-STATE-TRACKING-PARITY-67'
SCRIPTS_FORMAT = 'aw-script-summary-1'
SCRIPTS_TEXT = ('Scripts, from the MWScript tracker: used = the scripts of the game file that the original game runs; '
                'run = run by the interpreter; AmiWind adaptation = AmiWind\'s own code does the script\'s work, '
                'feature complete (every step of the script); not yet = everything else. Scripts not used in the '
                'original game never run there either and are never counted toward completion. Effect in play: of '
                'the functions the scripts call, how many have the original\'s effect in full, in part or none, and '
                'how many have something seen in play; a script that runs is not yet a script that plays as the '
                'original.')
LANDS = (
    {'id': 'vvardenfell', 'name': 'Vvardenfell', 'game': 'Morrowind (main game)', 'master': 'Morrowind.esm', 'island': 1,
     'set': 'vvardenfell'},
    {'id': 'solstheim', 'name': 'Solstheim', 'game': 'Bloodmoon', 'master': 'Bloodmoon.esm', 'island': 2,
     'set': 'bloodmoon'},
    {'id': 'mournhold', 'name': 'Mournhold', 'game': 'Tribunal', 'master': 'Tribunal.esm', 'island': 3,
     'set': 'tribunal'},
)
MASTER_ORDER = ('mournhold', 'solstheim', 'vvardenfell')      # the completion panel: Tribunal first
READY_TEXT = ('Ready = in the game on CHIM, the same for every land. Open terrain: the land\'s exterior cells of land or '
              'empty sea (open ocean and cells beyond the world\'s edge are not counted), ready when the newest ingested '
              'build holds the cell on CHIM and no audit of it failed. Rooms: every interior cell, counted for the land '
              'of its master, ready when it is in the game: on CHIM rooms, or as a room map of our own (special '
              'interiors, named under the count); a district the land presents as open terrain is counted once, under '
              'open terrain. Everything else is not ready, with its reason; a room no door leads to is a room still to '
              'build, never left out.')
CELL_REASONS = {'solstheim': 'not in the game yet (Solstheim)', 'not_started': 'not started',
                'not_in_build': 'converted, not in the newest build', 'empty_sea': 'empty sea, not in the newest build',
                'ocean': 'open sea, not in the newest build', 'converted_failing': 'converted, failing audits',
                'not_converted': 'not converted (tried, could not finish)', 'hull_policy_pending': 'hull policy pending'}
# Ready rooms = the in-game group of tools/cell_progress_rooms.py GROUPS, the states the Toolkit's tiles draw green: on
# CHIM rooms with a way in, a room map of our own, or a district the district module built as open terrain (when the
# data has no presented cell to count it under the terrain). The Toolkit's expansion-views.js READY_ROOM_STATES is the
# same list; tests/test_master_completion.py keeps the three in step. 'room_map' was left out on 19 November 2026
# (f87deed76, b82bd6693), which counted the opening sequence's two rooms not ready (TRACKER-ROOM-MAPS-NOT-READY-67).
READY_ROOM_STATES = ('on_chim_rooms', 'room_map', 'district')
# Special interiors: ready rooms in the game as a room map of our own, not on CHIM rooms; named under the count, never a
# reason (the rows whose state is room_map, whatever the data holds)
SPECIAL_ROOM_STATES = ('room_map',)
SPECIAL_TEXT = 'special interiors, in the game as room maps of our own'
ROOM_REASONS = {'converted': 'converted, not in the game yet',
                'not_started': 'not started',
                'teleport_only': 'still to build: no door leads there, a script or a dialogue line sends the player there',
                'no_entrance': 'still to build: no door leads there, and no script or dialogue line names it',
                'test_cell': 'still to build: no door leads there, a developers\' test cell',
                'hard_case': 'still to build: set aside as a hard case'}
LEADS = {'door': 'a door', 'teleport': 'a door from a room that a script or a dialogue line sends the player to',
         'teleport_only': 'a script or a dialogue line sends the player there; no door leads in',
         'unreachable': 'nothing found: no door, and no script or dialogue line names it'}
KINDS = (('people', 'NPC_'), ('creatures', 'CREA'), ('items', 'ITEM'), ('containers', 'CONT'), ('doors', 'DOOR'),
         ('activators', 'ACTI'), ('lights', 'LIGH'))
KIND_CONTENTS = {'NPC_': 'npcs', 'CREA': 'creatures', 'ITEM': 'items', 'CONT': 'containers', 'DOOR': 'doors',
                 'ACTI': 'activators', 'LIGH': 'lights'}


def pct(ready, total):
    """Percent with one decimal, rounded half up on whole numbers (the same in Python and in the Toolkit's script)."""
    return (2000 * ready + total) // (2 * total) / 10.0 if total else 0.0


def figure(ready, total):
    return {'ready': ready, 'total': total, 'percent': pct(ready, total)}


def land_of_room(r):
    """The land a room counts for: its master's land; a base-game room on Solstheim counts for Solstheim."""
    if r.get('master') == 'Tribunal.esm' or r.get('island') == 'Mournhold':
        return 'mournhold'
    if r.get('master') == 'Bloodmoon.esm' or r.get('island') == 'Solstheim':
        return 'solstheim'
    return 'vvardenfell'


def terrain_counted(c):
    """An exterior cell of a land's open terrain: on an island, land or empty sea."""
    ch = c.get('chim') or {}
    return bool(c.get('island')) and (bool(c.get('land')) or ch.get('bucket') == 'empty_sea')


def cell_ready(c):
    return (c.get('chim') or {}).get('group') == 'in_game'


def _reasons(rows, labels):
    """[{reason, label, count, items}] in a fixed order (labels' order), from [(reason, item)]."""
    by = collections.OrderedDict()
    for reason, item in rows:
        by.setdefault(reason, []).append(item)
    order = list(labels)
    return [{'reason': k, 'label': labels.get(k, k.replace('_', ' ')), 'count': len(v),
             'items': sorted(v, key=lambda i: (i.get('name') or '', i['id']))}
            for k, v in sorted(by.items(), key=lambda kv: (order.index(kv[0]) if kv[0] in order else len(order), kv[0]))]


def readiness(doc):
    """{format, definition, lands: [{id, name, game, master, island, terrain, rooms, total}], all} of a tracker doc."""
    cells = (doc or {}).get('cells') or {}
    rooms = ((doc or {}).get('interior_rooms') or {}).get('rooms') or []
    lands, terrain_names = [], {}
    for land in LANDS:
        mine = [(k, c) for k, c in cells.items() if c.get('island') == land['island'] and terrain_counted(c)]
        terrain_names[land['id']] = {(c.get('name') or '').casefold() for _, c in mine if c.get('name')}
        ready = sum(1 for _, c in mine if cell_ready(c))
        not_ready = _reasons([((c.get('chim') or {}).get('state') or 'not_started', {'id': k, 'name': c.get('name') or ''})
                              for k, c in mine if not cell_ready(c)], CELL_REASONS)
        lands.append(dict({k: land[k] for k in ('id', 'name', 'game', 'master', 'island')},
                          terrain=dict(figure(ready, len(mine)), not_ready=not_ready)))
    by_id = {x['id']: x for x in lands}
    grouped = collections.defaultdict(list)
    for r in rooms:
        grouped[land_of_room(r)].append(r)
    for land in lands:
        rs = grouped.get(land['id'], [])
        as_terrain = sorted(r['name'] for r in rs if r['name'].casefold() in terrain_names[land['id']])
        counted = [r for r in rs if r['name'].casefold() not in terrain_names[land['id']]]
        ready = sum(1 for r in counted if r.get('state') in READY_ROOM_STATES)
        not_ready = _reasons([(r.get('state') or 'not_started',
                               {'id': r['id'], 'name': r['name'], 'access': r.get('access'),
                                'leads': LEADS.get(r.get('access') or '', r.get('access') or ''),
                                'reasons': list(r.get('reasons') or [])})
                              for r in counted if r.get('state') not in READY_ROOM_STATES], ROOM_REASONS)
        special = sorted(r['name'] for r in counted if r.get('state') in SPECIAL_ROOM_STATES)
        land['rooms'] = dict(figure(ready, len(counted)), not_ready=not_ready, as_terrain=as_terrain, special=special)
        t, m = land['terrain'], land['rooms']
        land['total'] = figure(t['ready'] + m['ready'], t['total'] + m['total'])
    every = {k: figure(sum(by_id[i][k]['ready'] for i in by_id), sum(by_id[i][k]['total'] for i in by_id))
             for k in ('terrain', 'rooms', 'total')}
    return {'format': FORMAT, 'definition': READY_TEXT, 'lands': lands, 'all': every,
            'build': ((doc or {}).get('headline') or {}).get('in_game_label')}


def summary(ready_doc):
    """The counts of a readiness section without the item lists (the page's snapshot keeps this)."""
    out = {'format': ready_doc['format'], 'definition': ready_doc['definition'], 'build': ready_doc.get('build'),
           'all': ready_doc['all'], 'lands': []}
    for land in ready_doc['lands']:
        row = {k: land[k] for k in ('id', 'name', 'game', 'master', 'island', 'total')}
        for part in ('terrain', 'rooms'):
            p = land[part]
            row[part] = dict({k: p[k] for k in ('ready', 'total', 'percent')},
                             not_ready=[{k: x[k] for k in ('reason', 'label', 'count')} for x in p['not_ready']])
        row['rooms']['not_ready_names'] = [i['name'] for x in land['rooms']['not_ready'] for i in x['items']]
        row['rooms']['as_terrain'] = list(land['rooms'].get('as_terrain') or [])
        row['rooms']['special'] = list(land['rooms'].get('special') or [])
        out['lands'].append(row)
    return out


def line(ready_doc):
    """One plain line of every land and all lands together (the README line and the status print)."""
    fig = lambda f: '%s of %s (%.1f %%)' % ('{:,}'.format(f['ready']), '{:,}'.format(f['total']), f['percent'])
    parts = ['%s: open terrain %s, rooms %s, total %s' % (x['name'], fig(x['terrain']), fig(x['rooms']), fig(x['total']))
             for x in ready_doc['lands']]
    a = ready_doc['all']
    return 'Ready (in the game on CHIM): %s; all lands: open terrain %s, rooms %s, total %s.' % (
        '; '.join(parts), fig(a['terrain']), fig(a['rooms']), fig(a['total']))


# --- the completion panel per master ---

def _room_land_names(doc):
    """{interior name casefold: land id} from the tracker's rooms (their master's land)."""
    return {r['name'].casefold(): land_of_room(r) for r in (((doc or {}).get('interior_rooms') or {}).get('rooms') or [])}


SET_LAND = {'vvardenfell': 'vvardenfell', 'tribunal': 'mournhold', 'bloodmoon': 'solstheim'}


def interior_land(rec, room_land):
    return room_land.get((rec.get('name') or '').casefold()) or SET_LAND.get(rec.get('set'), 'vvardenfell')


def placed(doc):
    """{land id: {kind: n}}: the things placed in the original in the land's own cells, by kind (the census counts the
    ingest keeps on every interior record and every exterior cell: the three masters merged as the game merges them).
    None when the data has no census."""
    if not ((doc or {}).get('sources') or {}).get('census'):
        return None
    room_land = _room_land_names(doc)
    out = {x['id']: collections.OrderedDict((k, 0) for k, _ in KINDS) for x in LANDS}
    island_land = {x['island']: x['id'] for x in LANDS}
    for rec in (doc or {}).get('interiors') or []:
        c = rec.get('contents') or {}
        by_type = ((rec.get('stats') or {}).get('records') or {}).get('by_type') or {}
        land = out[interior_land(rec, room_land)]
        for k, tag in KINDS:
            land[k] += int(by_type.get(tag, c.get(KIND_CONTENTS[tag], 0)) or 0)
    for c in ((doc or {}).get('cells') or {}).values():
        land = island_land.get(c.get('island'))
        got = c.get('contents') or {}
        if not land or got.get('source') != 'census':
            continue
        for k, tag in KINDS:
            out[land][k] += int(got.get(KIND_CONTENTS[tag], 0) or 0)
    return out


def doors(doc, census):
    """{land id: {load_doors, with_way_back, one_way: [...]}} from the census door records: every load door standing in
    the land's cells (its exterior cells and its rooms), and whether the place it leads to has a load door back (a room
    back to the room, a room out to the open world for a door from outside). None without a census."""
    if not census:
        return None
    room_land = _room_land_names(doc)
    cells = (doc or {}).get('cells') or {}
    island_land = {x['island']: x['id'] for x in LANDS}
    ints = census.get('interiors') or {}
    out_of = {k: {(d.get('to') or '').casefold() for d in e.get('doors') or []} for k, e in ints.items()}
    from_outside = {(d.get('to') or '').casefold() for e in (census.get('cells') or {}).values() for d in e.get('doors') or []}
    out = {x['id']: {'load_doors': 0, 'with_way_back': 0, 'one_way': []} for x in LANDS}

    def count(land, frm, frm_label, d):
        to = (d.get('to') or '').casefold()
        row = out[land]
        row['load_doors'] += 1
        if to and frm:
            back = frm in out_of.get(to, ())           # a room to a room: a door of that room back
        elif to:
            back = '' in out_of.get(to, ())            # the open world into a room: a door of that room out
        else:
            back = frm in from_outside                 # a room out to the open world: a door from outside into it
        if back:
            row['with_way_back'] += 1
        else:
            row['one_way'].append({'from': frm_label, 'to': d.get('to') or 'the open world'})
    for key, e in (census.get('cells') or {}).items():
        land = island_land.get((cells.get(key) or {}).get('island'))
        if land:
            for d in e.get('doors') or []:
                count(land, '', 'cell ' + key, d)
    for k, e in ints.items():
        land = interior_land({'name': e.get('name'), 'set': e.get('set')}, room_land)
        for d in e.get('doors') or []:
            count(land, k, e.get('name') or k, d)
    for row in out.values():
        row['one_way'].sort(key=lambda x: (x['from'], x['to']))
    return out


def scripts(script_doc):
    """{master: {source, measured, all, used, states: [{state, label, count, items}], start: [...]}} from the MWScript
    tracker, every row's state worked out again from the interpreter's function table (tools/mwscript_features.py)."""
    if not script_doc or not script_doc.get('scripts'):
        return None
    import mwscript_features as mf
    from mwscript import gamedata
    mf.use(script_doc)
    out = {}
    for land in LANDS:
        rows = [r for r in script_doc['scripts'] if r.get('master') == land['master']]
        states = collections.OrderedDict((s, []) for s in mf.STATES)
        start = []
        for r in rows:
            st, why = mf.state_of(r)
            item = {'id': r['id'], 'why': why}
            if st == 'missing-function':
                item['missing'] = mf.missing_now(r.get('notyet') or [])
            states[st].append(item)
            if r.get('start') or r['id'].casefold() == gamedata.MAIN_SCRIPT:
                start.append({'id': r['id'], 'state': st, 'label': mf.LABELS[st], 'why': why})
        out[land['id']] = {
            'source': 'docs/mwscript-features.json', 'measured': (script_doc.get('measured') or {}).get('date'),
            'version': script_doc.get('version'), 'all': len(rows), 'used': len(rows) - len(states['inert']),
            'states': [{'state': s, 'label': mf.LABELS[s], 'count': len(v), 'items': sorted(v, key=lambda i: i['id'].casefold())}
                       for s, v in states.items()],
            'start': sorted(start, key=lambda i: i['id'].casefold())}
    # TOOLKIT-PROGRESS-MWSCRIPT-MASTERS-69: the counts each land's block of the headline draws (used in the original,
    # run, AmiWind adaptation, not yet, and not used in the original, which never counts toward completion) and the
    # functions' effect in play, from the same tracker (tools/mwscript_features.py script_summary)
    summary = mf.script_summary(script_doc)
    by_master = {x['master']: x for x in summary['masters']}
    out['summary'] = {'format': SCRIPTS_FORMAT, 'source': summary['source'], 'version': summary['version'],
                      'measured': summary['measured'], 'definition': SCRIPTS_TEXT,
                      'lands': {land['id']: by_master[land['master']] for land in LANDS}, 'all': summary['all'],
                      'dialogue_results': summary['dialogue_results'], 'functions': summary['functions']}
    return out


def load_scripts(path):
    """The MWScript tracker at PATH (the repository's docs/mwscript-features.json, which the ingest's command line names;
    the build's tracker stage passes none, so the docs stay out of its stage key), or None when it is not there."""
    p = Path(path) if path else None
    return json.loads(p.read_text(encoding='utf-8')) if p and p.is_file() else None


def attach(doc, census=None, script_rows=None):
    """Write `readiness` and `completion` into a tracker doc (the ingest's last step before it is written).
    SCRIPT_ROWS: scripts(load_scripts(PATH)), worked out by the caller (the ingest's command line): the code a build
    stage reaches never reads the MWScript tracker, so the docs stay out of every stage key."""
    doc['readiness'] = readiness(doc)
    doc['completion'] = completion(doc, census, script_rows)
    return doc


def completion(doc, census=None, script_rows=None):
    """The `completion` section of a tracker doc: the readiness and one panel per master, Tribunal first.
    SCRIPT_ROWS: scripts() of the MWScript tracker, or None (that part says not measured)."""
    ready = (doc or {}).get('readiness') or readiness(doc)
    by_land = {x['id']: x for x in ready['lands']}
    things = placed(doc)
    door_rows = doors(doc, census)
    masters = []
    for lid in MASTER_ORDER:
        land = next(x for x in LANDS if x['id'] == lid)
        r = by_land[lid]
        no_door = [i for x in r['rooms']['not_ready'] for i in x['items'] if (i.get('access') or 'door') != 'door']
        masters.append({
            'id': lid, 'master': land['master'], 'game': land['game'], 'land': land['name'],
            'scripts': (script_rows or {}).get(lid),
            'variables': {'globals': None, 'journal_topics': None, 'save_state_table': None, 'todo': NOT_MEASURED},
            'placed': {'original': (things or {}).get(lid), 'source': 'census' if things else None,
                       'in_game': None, 'keyed_in_save': None, 'aimable': None, 'todo': NOT_MEASURED,
                       'gap': 'DISTRICT-PLACED-THINGS-NO-ROW-67'},
            'doors': dict((door_rows or {}).get(lid) or {'load_doors': None, 'with_way_back': None, 'one_way': []},
                          source='census' if door_rows else None, verified_in_build=None,
                          gap='DOORS-DISTRICT-FRAMES-NOT-HOLDERS-67',
                          rooms_no_door=sorted(no_door, key=lambda i: i['name'])),
        })
    return {'format': COMPLETION_FORMAT, 'todo': NOT_MEASURED, 'masters': masters,
            'script_summary': (script_rows or {}).get('summary')}
