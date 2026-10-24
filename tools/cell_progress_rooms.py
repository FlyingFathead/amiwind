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
dropped. A room's state, first match wins:
  on_chim_rooms  in the game on a CHIM room: a build's chim-interiors.json installed it, or a CHIM room record was
                 made for a room in the game
  room_map       in the game as today's room map
  converted      a CHIM room record was made for it, not in the game yet
  test_cell      no door reaches it, a developers' test cell (tools/door_graph.py TEST_CELLS)
  teleport_only  no door reaches it, a script sends the player there
  no_entrance    no door reaches it and no script names it
  hard_case      set aside by the door graph for another reason (lava at or under the water, size on the 32 MiB
                 minimum machine, behaves like an exterior); water, lava, Levitate-only and over the 16 MiB zone are
                 notes on a room (its row's 'notes'), not reasons to set it aside (v0.0.48)
  not_started    everything else
The states fall into the three groups of the World map legend: in the game, not in the game yet, set aside (each
with its reason).
"""
import collections

import door_graph as DG

STATES = ('on_chim_rooms', 'room_map', 'converted', 'not_started', 'hard_case', 'test_cell', 'teleport_only',
          'no_entrance')
STATE_LABELS = {'on_chim_rooms': 'In the game on CHIM rooms', 'room_map': 'In the game as a room map',
                'converted': 'Converted, not in the game yet', 'not_started': 'Not started',
                'hard_case': 'Set aside: hard case', 'test_cell': 'Set aside: test cell',
                'teleport_only': 'Set aside: teleport only', 'no_entrance': 'Set aside: no entrance, no script'}
GROUPS = collections.OrderedDict((
    ('in_game', ('In the game', ('on_chim_rooms', 'room_map'))),
    ('not_in_game', ('Not in the game yet', ('converted', 'not_started'))),
    ('set_aside', ('Set aside, with a reason', ('hard_case', 'test_cell', 'teleport_only', 'no_entrance')))))
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


def room_state(name_cf, hard, in_game, made, installed=(), parity=None):
    if name_cf in installed or (name_cf in in_game and name_cf in made):
        return 'on_chim_rooms'
    if name_cf in in_game:
        return 'room_map'
    if name_cf in made:
        return 'converted'
    if parity:
        return parity
    if hard:
        return 'hard_case'
    return 'not_started'


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


def rooms(graph, in_game=None, receipts=(), plan=None):
    """{name casefold: room tracker row} for every room of the door graph (none is left out)."""
    maps = {k.casefold(): v for k, v in (in_game or {}).items()} if isinstance(in_game, dict) else \
        {k.casefold(): None for k in (in_game or ())}
    made, installed = chim_room_cells(receipts, {k: v for k, v in maps.items() if v})
    batch_of = batches_of(plan)
    out = {}
    for r in (graph or {}).get('rooms', []):
        k = r['name'].casefold()
        # a graph made before v0.0.48 lists water, lava and Levitate-only as hard cases: they are notes now (the
        # rooms are converted like any room), as in a graph made today
        listed = list(r.get('hard') or [])
        hard = [h for h in listed if h not in DG.NOTES]
        notes = list(dict.fromkeys(list(r.get('notes') or []) + [h for h in listed if h in DG.NOTES]))
        state = room_state(k, hard, maps, made, installed, DG.parity_state(dict(r, hard=hard)))
        out[k] = {'id': r['name'], 'name': r['name'], 'master': r['master'], 'island': r['island'], 'state': state,
                  'label': STATE_LABELS[state], 'group': GROUP_OF[state], 'reasons': hard, 'notes': notes,
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
