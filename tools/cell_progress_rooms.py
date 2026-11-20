# SPDX-License-Identifier: GPL-3.0-only
"""CHIM Progress Tracker, interiors: one state per interior cell and headline counts per island.

Additive to the exterior tracker (tools/cell_progress.py): the exterior buckets and the World map legend are not
touched. Inputs, all private and optional:
  --door-graph  door-graph.json       tools/door_graph.py graph (aw-door-graph-1): every room, its island, hard cases
  --batch-plan  batch-plan.json       tools/door_graph.py plan (aw-batch-plan-1): the batch of each room (the
                                      Vvardenfell batches, the final parity batch, the expansions' later batches)
  --chim-rooms  (repeatable)          rooms made as CHIM rooms: a chim-rooms-receipt.json (tools/chim/interior.py,
                                      aw-chim-rooms-1) or a build's chim-interiors.json (the rooms the image installed)
  the repo config folder               the rooms in the game today (scene lists, cell_progress.our_maps)

Parity: every room of the door graph gets a row, keyed by its cell name (the cell's ID in the game data); no room is
dropped, and none is set aside (ROOMS-SET-ASIDE-NOT-BUILT-67, the maintainer's rule of 19 November 2026: every space of
every master is built). A room is green (in the game) when it is built, with its way in (way_in, the row's 'entry'): a
load door leads in ('door'); no door does and a script, a dialogue result or a travel service moves the player there
by the cell's name, which resolves to the built room through the room list ('script'; a GetPCCell test is no way
in); or nothing in the game data leads there and its dbg tp picker row reaches it
('picker': the image lists every room it holds there, tools/tp_places_lut.py image_rooms). A room's state, first
match wins:
  on_chim_rooms  in the game on a CHIM room (a build's chim-interiors.json installed it, or a CHIM room record was made
                 for a room in the game), reached by its way in
  room_map       in the game as today's room map
  district       a cell that behaves like an exterior (Mournhold's districts), in the game as open terrain: the
                 district module built it and the presented data names it
  converted      a CHIM room record was made for it, not in the game yet
  test_cell      not built yet; no door reaches it, a developers' test cell (tools/door_graph.py TEST_CELLS)
  teleport_only  not built yet; no door reaches it, a script or a dialogue line sends the player there
  no_entrance    not built yet; no door reaches it and no script names it
  hard_case      only in a graph with a reason this reader does not know (every reason of a graph made before v0.0.67
                 is a note now)
  not_started    everything else
The states fall into the groups of the World map legend: in the game, not in the game yet, and set aside, which only
an unknown reason reaches.
"""
import collections

import door_graph as DG

STATES = ('on_chim_rooms', 'room_map', 'district', 'converted', 'not_started', 'test_cell', 'teleport_only',
          'no_entrance', 'hard_case')
STATE_LABELS = {'on_chim_rooms': 'In the game on CHIM rooms', 'room_map': 'In the game as a room map',
                'district': 'In the game as open terrain (a district)',
                'converted': 'Converted, not in the game yet',
                'not_started': 'Not started',
                'test_cell': 'Not built yet: a test cell, no door leads there',
                'teleport_only': 'Not built yet: no door, a script or a dialogue line sends the player there',
                'no_entrance': 'Not built yet: no door, and no script or dialogue line names it',
                'hard_case': 'Set aside: a reason this tracker does not know'}
GROUPS = collections.OrderedDict((
    ('in_game', ('In the game', ('on_chim_rooms', 'room_map', 'district'))),
    ('not_in_game', ('Not in the game yet', ('converted', 'not_started', 'test_cell', 'teleport_only',
                                             'no_entrance'))),
    ('set_aside', ('Set aside, with a reason', ('hard_case',)))))
GROUP_OF = {s: g for g, (_, states) in GROUPS.items() for s in states}
ISLAND_ORDER = ('Vvardenfell', 'Solstheim', 'Mournhold', 'none')
ISLAND_LABELS = {'none': 'No entrance area'}


def chim_room_cells(receipts, maps=None):
    """(made, installed): interior names (casefold) of the rooms made as CHIM room records (aw-chim-rooms-1 receipts)
    and of the rooms a build's image installed (chim-interiors.json, rows named by our map name)."""
    by_map = {m.casefold(): cell for cell, m in (maps or {}).items()}
    # the batch rooms (config/room-batches.json, tools/room_batches.py) under their batch map names
    try:
        from room_batches import load, rows
        for row in rows(load()):
            by_map.setdefault(row['map'].casefold(), row['room'].casefold())
    except (OSError, ValueError, ImportError):
        pass
    # a rooms receipt (aw-chim-rooms-1) names each room by its cell AND its map name: the image's chim-interiors.json
    # names rooms by map name only, so map them back through the receipts first (TRACKER-INTERIORS-IN-GAME-COUNT-64)
    for doc in receipts or ():
        for row in (doc or {}).get('rooms', []):
            if row.get('cell') and row.get('room'):
                by_map.setdefault(row['room'].casefold(), row['cell'].casefold())
    made, installed = set(), set()
    for doc in receipts or ():
        doc = doc or {}
        install = doc.get('format') != 'aw-chim-rooms-1' and 'not_in_image' in doc
        for row in doc.get('rooms', []):
            name = row.get('cell')
            if not name and row.get('room'):
                name = by_map.get(row['room'].casefold(), row['room'])
            if name:
                (installed if install else made).add(name.casefold())
    return made, installed


def way_in(room):
    """How the player gets into a room of the door graph: 'door' (a door chain from the open world leads in: access
    door, or teleport for a room behind a door of a room a script sends the player to), 'script' (no door leads in; a
    script, a dialogue result or a travel service moves the player there: PositionCell, a travel destination; access
    teleport_only; a cell name in a test such as GetPCCell moves no one, DOOR-GRAPH-CELL-TEST-AS-TELEPORT-67), or None
    (access unreachable: nothing in the game data leads there). A row without an access (an old graph) counts as a
    door."""
    access = room.get('access') or 'door'
    if access in ('door', 'teleport'):
        return 'door'
    if access == 'teleport_only':
        return 'script'
    return None


ENTRY_TEXT = {'door': 'a door', 'script': 'a script or a dialogue line moves the player there (PositionCell)',
              'picker': 'no door or script in the game data; reached by its picker link (dbg tp)'}


def room_state(name_cf, hard, in_game, made, installed=(), parity=None, district=False):
    """A built room is green: its way in is a door, a script or dialogue line whose target resolves to the built room
    map through the room list, or, for a room nothing in the game data leads to, its dbg tp picker row (the image lists
    every room it holds there, tools/tp_places_lut.py image_rooms)."""
    if name_cf in installed or (name_cf in in_game and name_cf in made):
        return 'on_chim_rooms'
    if name_cf in in_game:
        return 'room_map'
    if district:
        return 'district'
    if name_cf in made:
        return 'converted'
    if parity:
        return parity
    if hard:
        return 'hard_case'
    return 'not_started'


def is_district(room):
    """A cell flagged "behaves like an exterior" (Mournhold's districts): the graph row's flag, or its reason."""
    return bool(room.get('behaves_exterior')) or 'behaves_exterior' in DG.access_reasons(room)


def batches_of(plan):
    """{name casefold: batch} from a batch plan: the Vvardenfell batches (numbers), the later batches (text)."""
    out = {}
    for b in (plan or {}).get('batches', []):
        for name in b['rooms']:
            out[name.casefold()] = b['batch']
    for b in (plan or {}).get('later', []):
        for name in b['rooms']:
            out.setdefault(name.casefold(), b['batch'])
    return out


def rooms(graph, in_game=None, receipts=(), plan=None, districts=()):
    """{name casefold: room tracker row} for every room of the door graph (none is left out). DISTRICTS: the cell names
    the presented data gives Mournhold's open terrain (tools/cell_progress.py presented_cells): a district among them is
    in the game, built as open terrain by the district module."""
    maps = {k.casefold(): v for k, v in (in_game or {}).items()} if isinstance(in_game, dict) else \
        {k.casefold(): None for k in (in_game or ())}
    made, installed = chim_room_cells(receipts, {k: v for k, v in maps.items() if v})
    batch_of = batches_of(plan)
    districts = {d.casefold() for d in districts or ()}
    out = {}
    for r in (graph or {}).get('rooms', []):
        k = r['name'].casefold()
        # a graph made before lists water, lava and Levitate-only (before v0.0.48) and no door, teleport only, behaves
        # like an exterior and over a limit (before v0.0.67) as hard cases: they are notes now (every room is built),
        # as in a graph made today; the reasons stay on the row to say what leads there
        listed = list(r.get('hard') or [])
        hard = [h for h in listed if h not in DG.NOTES]
        notes = list(dict.fromkeys(list(r.get('notes') or []) + [h for h in listed if h in DG.NOTES]))
        state = room_state(k, hard, maps, made, installed, DG.parity_state(dict(r, hard=hard, notes=notes)),
                           district=is_district(r) and k in districts)
        entry = way_in(r) or 'picker'
        out[k] = {'id': r['name'], 'name': r['name'], 'master': r['master'], 'island': r['island'], 'state': state,
                  'label': STATE_LABELS[state], 'group': GROUP_OF[state],
                  'reasons': hard + [x for x in DG.access_reasons(r) if x not in hard], 'notes': notes,
                  'way_in': entry, 'entry': ENTRY_TEXT[entry],
                  'batch': batch_of.get(k), 'access': r.get('access'), 'entrance': r.get('entrance_exterior'),
                  'settlement': r.get('settlement'), 'region': r.get('region'),
                  'on_chim_rooms': state == 'on_chim_rooms', 'our_map': maps.get(k)}
    return out


def headline(rows):
    """{island: {state: count, 'total': n, 'groups': {group: n}, 'hard_reasons': {...}}} in island order, every state
    present."""
    by = collections.OrderedDict()
    islands = sorted({r['island'] for r in rows.values()},
                     key=lambda i: (ISLAND_ORDER.index(i) if i in ISLAND_ORDER else len(ISLAND_ORDER), i))
    for island in islands:
        counts = collections.Counter(r['state'] for r in rows.values() if r['island'] == island)
        row = collections.OrderedDict((s, counts.get(s, 0)) for s in STATES)
        row['total'] = sum(counts.values())
        row['groups'] = collections.OrderedDict((g, sum(counts.get(s, 0) for s in states))
                                                for g, (_, states) in GROUPS.items())
        reasons = collections.Counter(x for r in rows.values() if r['island'] == island and r['group'] == 'set_aside'
                                      for x in r['reasons'])
        row['hard_reasons'] = dict(sorted(reasons.items()))
        by[island] = row
    return by


def totals(rows):
    """Every island together: per state and per group."""
    counts = collections.Counter(r['state'] for r in rows.values())
    out = collections.OrderedDict((s, counts.get(s, 0)) for s in STATES)
    out['total'] = len(rows)
    out['groups'] = collections.OrderedDict((g, sum(counts.get(s, 0) for s in states))
                                            for g, (_, states) in GROUPS.items())
    return out


def section(rows, plan=None):
    """The doc's `interior_rooms` key."""
    return {'states': list(STATES), 'labels': STATE_LABELS,
            'groups': [{'id': g, 'label': label, 'states': list(states)} for g, (label, states) in GROUPS.items()],
            'islands': {i: ISLAND_LABELS.get(i, i) for i in ISLAND_ORDER},
            'headline': headline(rows), 'totals': totals(rows),
            'batches': len((plan or {}).get('batches', [])) or None,
            'later': [{k: b[k] for k in ('batch', 'island', 'master', 'waits_for')} for b in (plan or {}).get('later', [])],
            'rooms': [rows[k] for k in sorted(rows)]}


def attach(interiors, rows):
    """Add each interior tracker record its room state (records keep every key they had)."""
    for rec in interiors:
        row = rows.get((rec.get('name') or '').casefold())
        if row is not None:
            rec['room'] = {k: row[k] for k in ('state', 'label', 'group', 'reasons', 'island', 'access', 'batch')}
    return interiors
