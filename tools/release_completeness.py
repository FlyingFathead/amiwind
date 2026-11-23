#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The completeness check: every space of every master the game ships is in the build (RELEASE-GATE-COMPLETENESS-LOST-67).

The rule (decided for the project, 19 November 2026): every exterior cell, interior cell, district, test cell and space
of every master a release ships is built and in the game. A place without a door, reached only by a teleport or a
script, behaving like an exterior or over a limit is a question to answer while building it, never a reason to leave
it out. Until v0.0.67 nothing refused a release with a place missing: tools/chim_inclusion.py check-release asks only
whether the version is in the inclusion ledger, and the release guard's tracker check only whether the world map
ingested the image run. This tool is that refusal. It reads the masters with the repository's own reader (src/mwad:
esm.py records, masters.py the merge rules: a cell by grid or name, a reference by its owning file and number, a moved
reference in the cell it moved to) and lists, by master and by name:

  a. every exterior cell (land, seabed and open sea alike: every CELL record) not in the build; a cell inside a CHIM
     town's core counts as in when the town is;
  b. every interior cell (room, district, test cell, empty cell) not in the build;
  c. every load door whose source or destination is not in the build, that the build does not carry, or whose way back
     the build loses; a door the original itself has no way back through is a note, not a refusal;
  d. the progress tracker counts the Toolkit draws (its tracker data) and the public tracker page's snapshot
     (docs/chim/progress-state.json), per land, where they differ.

Two modes:
  plan   BEFORE a build, from the source tree's plan: the base world's cell list (config/chim-cells.json), the Bloodmoon
         module's cells (tools/bloodmoon_solstheim_module.py module_plan: the tracker reference's finished cells and
         config/solstheim-sea-cells.json), the room batch lists (config/room-batches*.json). Printed by tools/build.py
         before the first stage.
  run    AFTER a build, from its run folder: what the IMAGE holds. Exterior cells: the engine's outdoor table (the image's
         world/regions.awr rows and the rows files of the lands with a store of their own, aw_world.c load_directory:
         the first row whose core holds the cell's centre) with that row's CHIM frame map in the image (the boot
         folder's maps and the world partitions' files, image/world-partitions.json), or a CHIM town's core
         (exterior-checklist.json towns) with the town installed (image/chim-towns.json and its frame map). Interior
         cells: the image's interior numbering (image/cell-numbers.json maps) with the map in the image, and the
         districts a presentation built as frames (image/world-doors.json presented, the presented data's blocks, the
         land store's frame maps). Load doors: the image's door table (image/world-doors.json, a row by the merged
         reference number and object), not held back, its target map in the image.

Only a place approved in the ledger (config/release-completeness-approved.json, by place and master, with the date and
the reason; it starts empty) is not counted missing. "No entrance", "teleport only", "unreachable" and "over a limit" are
never reasons, and no entry covers more than one place.

A development snapshot reports (exit 0, every missing place listed); a release candidate or final is refused (exit 1)
while any place is missing that the ledger does not approve. The release preflight and the release guard run it for
the rc and the final; tools/build.py prints the plan's line before the first stage of every build; the delivery's
tracker step prints the run's.

Usage:
  release_completeness.py plan [--root DIR] [--data-files DIR] [--masters LIST] [--kind dev|rc|final | --version V]
                               [--toolkit FILE] [--public FILE] [--approved FILE] [--out DIR] [--json]
  release_completeness.py run --run RUN [the same options]
  release_completeness.py ledger [--approved FILE]          check the approval ledger alone
Writes release-completeness.json and release-completeness.md into --out. Exit 0 complete (or a development build), 1 an
rc or final with an unapproved missing place (or an input it needs that is not there), 2 a bad call. Standard library
and the repository's own modules only; a few seconds (the three masters' cell records and the run's small receipts).
"""
import argparse
import collections
import datetime
import json
import math
import os
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):      # src before tools (TEST-WORKER-SYSPATH-32)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mwad.esm import GAME_MASTERS, is_deleted, records, string, subrecords  # noqa: E402
from mwad.masters import ADDON_KEY_STRIDE, _cell_key, _split_cell  # noqa: E402  (the merge's own cell rules)

FORMAT = 'aw-completeness-1'
LEDGER_FORMAT = 'aw-completeness-approved-1'
LEDGER = ROOT / 'config' / 'release-completeness-approved.json'
PUBLIC = ROOT / 'docs' / 'chim' / 'progress-state.json'
REFERENCE = ROOT / 'docs' / 'chim' / 'cell-progress-reference.json'
BASE_CELLS = ROOT / 'config' / 'chim-cells.json'
ROOM_BATCHES = ('config/room-batches.json', 'config/room-batches-tribunal.json', 'config/room-batches-bloodmoon.json')
REPORT_JSON, REPORT_MD = 'release-completeness.json', 'release-completeness.md'
CELL_UNITS = 8192.0           # Morrowind units per exterior cell
MAP_CELL = 2048.0             # map units per exterior cell (the outdoor table's units; chim-regions.json cell_map_units)
KINDS = ('dev', 'rc', 'final')
PLACE_KINDS = ('exterior', 'interior', 'door')
# never a reason to leave a place of the game out (decided for the project, 19 November 2026; ROOMS-SET-ASIDE-NOT-BUILT-67)
REFUSED_REASONS = (r'no\s+entrance', r'teleport[\s-]*only', r'unreachable', r'over\s+(a|the)?\s*limit', r'no\s+door')
BLANKET = re.compile(r'[*?]|^\s*(all|every|any)\b', re.I)


# ------------------------------------------------------------------ the masters

def place_label(place, cells):
    """'x,y Name (Region)' of an exterior place, the cell's own name of an interior one."""
    info = cells.get(place) or {}
    if place[0] == 'ext':
        text = '%d,%d' % (place[1], place[2])
        if info.get('name'):
            text += ' ' + info['name']
        if info.get('region'):
            text += ' (%s)' % info['region']
        return text
    return info.get('name') or place[1]


def place_key(place):
    """The ledger's text of a place: 'x,y' (exterior) or the interior cell's name, case kept as the game writes it."""
    return '%d,%d' % (place[1], place[2]) if place[0] == 'ext' else place[1]


def _owner(index, number, masts, names):
    """The merged reference number (src/mwad/masters.py _Merge._ref_key): the owning file's place in GAME_MASTERS x
    ADDON_KEY_STRIDE + the low bits; the top byte names the owning file (0 the file itself, k its k-th master)."""
    top, low = number >> 24, number & 0xFFFFFF
    owner = names[index] if top == 0 else next((n for n in names if n.casefold() == masts[top - 1].casefold()), None)
    if owner is None or owner not in GAME_MASTERS:
        return None
    return GAME_MASTERS.index(owner) * ADDON_KEY_STRIDE + low


def read_masters(files):
    """The game's places and load doors as the game merges FILES, [(master name, bytes)] in load order.
    {'cells': {place: {master, name, region}}, 'doors': {ref: {ref, master, id, src, dst, dnam}}, 'sha256': {}}.
    A place: ('ext', x, y) or ('int', the casefolded name); its master is the first file that defines it."""
    import hashlib
    names = [n for n, _ in files]
    cells, refs = {}, {}
    sha = {}
    for index, (name, raw) in enumerate(files):
        sha[name] = hashlib.sha256(raw).hexdigest()
        masts = []
        for tag, flags, payload in records(raw):
            if tag == 'TES3':
                masts = [string(d, errors='replace') for t, d in subrecords(payload) if t == 'MAST']
                continue
            if tag != 'CELL':
                continue
            header, blocks = _split_cell(list(subrecords(payload)))
            key = _cell_key(header)
            place = ('ext', key[1], key[2]) if key[0] == 'ext' else ('int', key[1])
            if is_deleted(flags, header):
                cells.pop(place, None)
                continue
            fields = dict(header)
            info = cells.setdefault(place, {'master': name, 'name': '', 'region': ''})
            text = string(fields.get('NAME', b''), errors='replace')
            if text:
                info['name'] = text
            if 'RGNN' in fields:
                info['region'] = string(fields['RGNN'], errors='replace')
            for target, block in blocks:
                ref = _owner(index, struct.unpack('<I', block[0][1][:4])[0], masts, names)
                if ref is None:
                    continue
                home = ('ext', target[0], target[1]) if target is not None else place
                sub = dict(block[1:])
                if any(t == 'DELE' for t, _ in block):
                    refs.pop(ref, None)
                    continue
                if 'DODT' not in sub:
                    refs.pop(ref, None)          # a later file made it no load door (or it never was one)
                    continue
                x, y = struct.unpack('<2f', sub['DODT'][:8])
                dnam = string(sub['DNAM'], errors='replace') if 'DNAM' in sub else None
                dst = ('int', dnam.casefold()) if dnam else ('ext', int(math.floor(x / CELL_UNITS)),
                                                              int(math.floor(y / CELL_UNITS)))
                refs[ref] = {'ref': ref, 'master': GAME_MASTERS[ref // ADDON_KEY_STRIDE],
                             'id': string(sub.get('NAME', b''), errors='replace'), 'src': home, 'dst': dst,
                             'dnam': dnam}
    for d in refs.values():
        if d['dst'][0] == 'int' and d['dst'] not in cells:
            d['dst_unknown'] = True                # the original names a cell no master defines
    return {'cells': cells, 'doors': refs, 'sha256': sha, 'masters': names}


def load_masters(data_files, masters):
    """read_masters() of MASTERS (names) found in DATA_FILES (any case)."""
    folder = Path(data_files)
    have = {p.name.casefold(): p for p in folder.iterdir()} if folder.is_dir() else {}
    files = []
    for name in masters:
        p = have.get(name.casefold())
        if p is None:
            raise FileNotFoundError('%s: no %s' % (folder, name))
        files.append((name, p.read_bytes()))
    return read_masters(files)


def _near(a, b):
    """Two places a load door's way back may join: the same room, or exterior cells next to each other (an exit
    lands beside the door it came in through, sometimes over a cell border)."""
    if a[0] != b[0]:
        return False
    if a[0] == 'int':
        return a == b
    return abs(a[1] - b[1]) <= 1 and abs(a[2] - b[2]) <= 1


def returns(doors):
    """{ref: [refs of the load doors back]}: the doors standing where REF leads that lead back to where REF stands."""
    by_src = collections.defaultdict(list)
    for d in doors.values():
        by_src[d['src']].append(d)
    out = {}
    for ref, d in doors.items():
        t = d['dst']
        if t[0] == 'int':
            cand = by_src.get(t, [])
        else:
            cand = [e for dx in (-1, 0, 1) for dy in (-1, 0, 1) for e in by_src.get(('ext', t[1] + dx, t[2] + dy), [])]
        out[ref] = sorted(e['ref'] for e in cand if e['ref'] != ref and _near(e['dst'], d['src']))
    return out


# ------------------------------------------------------------------ what a build holds

def _cells_of(values):
    out = set()
    for v in values or ():
        if isinstance(v, str):
            a, b = v.split(',')
            out.add((int(a), int(b)))
        else:
            out.add((int(v[0]), int(v[1])))
    return out


def in_cores(x, y, cores):
    """True when exterior cell X,Y lies in a CHIM town's core: its centre inside one of CORES, [x0, y0, x1, y1] in map
    units (tools/exterior_plan.py town_cores, the exterior checklist's towns). The one rule of both modes: a cell
    inside a town's frame is in when the town is."""
    cx, cy = (x + .5) * MAP_CELL, (y + .5) * MAP_CELL
    return any(c[0] <= cx <= c[2] and c[1] <= cy <= c[3] for c in cores or ())


def core_cells(cores):
    """{(x, y)}: every exterior cell in_cores() counts inside CORES."""
    out = set()
    for c in cores or ():
        for x in range(int(math.floor(c[0] / MAP_CELL)) - 1, int(math.ceil(c[2] / MAP_CELL)) + 1):
            for y in range(int(math.floor(c[1] / MAP_CELL)) - 1, int(math.ceil(c[3] / MAP_CELL)) + 1):
                if in_cores(x, y, [c]):
                    out.add((x, y))
    return out


def plan_evidence(root, masters, base_cells=None, module_cells=None, town_cores=None):
    """What a build of the source tree ROOT will contain: {'ext': {(x, y)}, 'int': {name casefold}, 'door_rows': None
    (a door is in when both its places are), 'notes': [...]}. BASE_CELLS / MODULE_CELLS: the cells a build resolved
    (tools/build.py: --chim-regions-cells, the Bloodmoon module's cells), else the source tree's defaults. TOWN_CORES:
    the cores of the CHIM towns the build makes (its exterior checklist's towns): the cells inside them are the towns'
    (the resolved region cells leave them out: "dropped, inside a town frame"), COMPLETENESS-PLAN-TOWN-CELLS-MISSING-68."""
    root = Path(root)
    notes = []
    if base_cells is not None:
        ext = {tuple(c) for c in base_cells}
        notes.append('base world: the %d cells the build resolved' % len(ext))
    else:
        base = json.loads((root / 'config' / 'chim-cells.json').read_text(encoding='utf-8'))
        ext = _cells_of(base.get('cells'))
        notes.append('base world: %d cells of config/chim-cells.json' % len(ext))
    if town_cores:
        towns = core_cells(town_cores)
        notes.append('CHIM towns: %d cells inside the cores of %d towns (%d not among the region cells)'
                     % (len(towns), len(town_cores), len(towns - ext)))
        ext |= towns
    if 'Bloodmoon.esm' in masters and module_cells is not None:
        ext |= {tuple(c) for c in module_cells}
        notes.append('Bloodmoon module: the %d cells the build resolved' % len(module_cells))
    elif 'Bloodmoon.esm' in masters:
        import bloodmoon_solstheim_module as BM
        table, problems = BM.module_plan(root / 'docs' / 'chim' / 'cell-progress-reference.json', root)
        sol = {tuple(c) for f in table.get('frames') or () for c in (f.get('cells') or [f['cell']])}
        ext |= sol
        notes.append('Bloodmoon module: %d cells (tools/bloodmoon_solstheim_module.py module_plan)%s'
                     % (len(sol), ('; plan problems: ' + '; '.join(problems)) if problems else ''))
    rooms = set()
    for rel in ROOM_BATCHES:
        p = root / rel
        if not p.is_file():
            continue
        for b in json.loads(p.read_text(encoding='utf-8')).get('batches') or ():
            for r in b.get('rooms') or ():
                rooms.add((r.get('room') if isinstance(r, dict) else str(r)).casefold())
    notes.append('rooms: %d in the room batch lists' % len(rooms))
    return {'mode': 'plan', 'ext': ext, 'int': rooms, 'door_rows': None, 'notes': notes, 'masters_sha256': None,
            'version': (root / 'VERSION').read_text(encoding='utf-8').strip() if (root / 'VERSION').is_file() else None}


def _json(path):
    p = Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def image_files(run):
    """The image's id1 files (relative 'id1/...'): the boot folder's and every world partition's."""
    run = Path(run)
    boot = run / 'image' / 'boot'
    out = set()
    for folder, _, names in os.walk(boot / 'id1'):
        rel = Path(folder).relative_to(boot).as_posix()
        out |= {rel + '/' + n for n in names}
    for part in (_json(run / 'image' / 'world-partitions.json') or {}).get('partitions') or ():
        out |= {f['path'] for f in part.get('files') or ()}
    return out


def run_evidence(run):
    """What the image of the build run RUN holds (see the module text)."""
    from chim.frame_map import world_directory
    from door_audit import layer_directory
    run = Path(run)
    img, id1 = run / 'image', run / 'image' / 'boot' / 'id1'
    if not (id1 / 'world' / 'regions.awr').is_file():
        raise FileNotFoundError('%s: no image (image/boot/id1/world/regions.awr)' % run)
    from map_files import FRAME_EXT, map_stem, is_map_name
    files = image_files(run)
    maps = [f[len('id1/maps/'):] for f in files if f.startswith('id1/maps/')]
    frames = {map_stem(m) for m in maps if m.lower().endswith(FRAME_EXT)}
    any_maps = {map_stem(m) for m in maps if is_map_name(m)}

    def frame_map(name):
        """A CHIM frame map of that name in the image (tools/map_files.py names the files)."""
        return name in frames

    def any_map(name):
        """A map the engine can run by that name: its own (a frame map or a legacy map), or a town's frame map, which
        the engine runs for a door that names the town (map_files.town_map_present)."""
        return bool(name) and (name in any_maps or (name + '-chim') in frames)
    rows = list(world_directory(id1)) + list(layer_directory(id1))
    notes = ['outdoor table: %d rows, %d with their frame map in the image' % (len(rows), sum(1 for r in rows if frame_map(r[0])))]
    # CHIM towns: a town's core cells are in when the town is installed with its frame map
    towns = {t.get('town') for t in _json(img / 'chim-towns.json') or ()}
    cores = []
    for t in (_json(run / 'exterior-checklist.json') or {}).get('towns') or ():
        if t.get('owner') in towns and frame_map('%s-chim' % t['owner']):
            cores.append(t['core'])
    notes.append('CHIM towns in the image: %s' % (', '.join(sorted(x for x in towns if x)) or 'none'))

    def exterior(x, y):
        if in_cores(x, y, cores):
            return True
        cx, cy = (x + .5) * MAP_CELL, (y + .5) * MAP_CELL
        for name, origin, core in rows:
            if origin[0] + core[0] <= cx <= origin[0] + core[2] and origin[1] + core[1] <= cy <= origin[1] + core[3]:
                return frame_map(name)
        return False
    numbers = _json(img / 'cell-numbers.json') or {}
    rooms = {r['cell'].casefold() for r in numbers.get('maps') or () if any_map(r.get('map'))}
    notes.append('interior maps in the image: %d of the %d the image numbers' % (len(rooms), len(numbers.get('maps') or ())))
    doors = _json(img / 'world-doors.json') or {}
    built = set((doors.get('presented') or {}).get('built') or ())
    presented = _json(run / 'tribunal-mournhold-data' / 'presented-data.json') or {}
    stores = _json(img / 'chim-layer-stores.json') or []
    installed = {tuple(m['cell']) for s in stores for m in s.get('maps') or ()
                 if (('id1/' + m['map']) in files if m.get('map') else frame_map(Path(m.get('file', '')).stem))}
    districts = collections.defaultdict(set)
    for row in presented.get('presented_cells') or ():
        (bx, by), (w, h) = row['block'], row.get('size') or (1, 1)
        districts[row['cell']] |= {(int(bx) + i, int(by) + j) for i in range(int(w)) for j in range(int(h))}
    for name in built:
        if districts.get(name) and districts[name] <= installed:
            rooms.add(name.casefold())
    notes.append('districts built as frames: %d of %d presented' % (
        sum(1 for n in built if districts.get(n) and districts[n] <= installed), len(districts)))
    by_ref = collections.defaultdict(list)
    for r in doors.get('rows') or ():
        # a marker row: a door object with a destination the player never walks through (the arrest system's
        # PrisonMarker, the jail it sends to); the door table carries it as kind "marker"
        if r.get('kind') in ('door', 'marker'):
            by_ref[int(r['reference'])].append(r)
    build = _json(img / 'build.json') or {}
    return {'mode': 'run', 'exterior': exterior, 'int': rooms, 'door_rows': by_ref, 'any_map': any_map, 'notes': notes,
            'masters_sha256': numbers.get('masters_sha256'), 'version': build.get('version'), 'run': str(run)}


# ------------------------------------------------------------------ the approval ledger

def load_ledger(path):
    """(entries, problems) of the approval ledger: {(master, kind, place casefold): entry}. A missing file is an empty
    ledger; an entry without master, kind, place, date or reason, with a refused reason or naming more than one place is
    a problem (and approves nothing)."""
    p = Path(path)
    if not p.is_file():
        return {}, []
    try:
        doc = json.loads(p.read_text(encoding='utf-8'))
    except ValueError as exc:
        return {}, ['%s: not JSON (%s)' % (p, exc)]
    problems, out = [], {}
    if doc.get('format') != LEDGER_FORMAT:
        problems.append('%s: format is %r, not %s' % (p.name, doc.get('format'), LEDGER_FORMAT))
    for n, e in enumerate(doc.get('approved') or (), 1):
        what = 'ledger entry %d' % n
        missing = [k for k in ('master', 'kind', 'place', 'date', 'reason') if not str(e.get(k) or '').strip()]
        if missing:
            problems.append('%s: no %s' % (what, ', '.join(missing)))
            continue
        if e['master'] not in GAME_MASTERS:
            problems.append('%s: master %r is not a game master' % (what, e['master']))
            continue
        if e['kind'] not in PLACE_KINDS:
            problems.append('%s: kind %r is not one of %s' % (what, e['kind'], ', '.join(PLACE_KINDS)))
            continue
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(e['date'])):
            problems.append('%s: date %r is not YYYY-MM-DD' % (what, e['date']))
            continue
        bad = [r for r in REFUSED_REASONS if re.search(r, e['reason'], re.I)]
        if bad:
            problems.append('%s (%s): "%s" is never a reason to leave a place of the game out' % (what, e['place'], e['reason']))
            continue
        if BLANKET.search(str(e['place'])) or isinstance(e['place'], list):
            problems.append('%s: %r names more than one place (one entry approves one place)' % (what, e['place']))
            continue
        out[(e['master'], e['kind'], str(e['place']).casefold())] = e
    return out, problems


# ------------------------------------------------------------------ the check

def assess(game, evidence, ledger=None, tracker=None):
    """The result: per master the places and doors, every missing one by name, the notes, the tracker differences."""
    ledger = ledger or {}
    cells, doors = game['cells'], game['doors']
    back = returns(doors)

    def has(place):
        if place[0] == 'ext':
            if evidence.get('exterior'):
                return evidence['exterior'](place[1], place[2])
            return (place[1], place[2]) in evidence['ext']
        return place[1] in evidence['int']

    def approved(master, kind, key):
        return ledger.get((master, kind, key.casefold()))
    masters = collections.OrderedDict((m, {'exterior': {'total': 0, 'in': 0, 'missing': [], 'approved': []},
                                           'interior': {'total': 0, 'in': 0, 'missing': [], 'approved': []},
                                           'doors': {'total': 0, 'both_ways': 0, 'missing': [], 'no_way_back': [],
                                                     'one_way_in_original': [], 'to_no_cell': [], 'approved': []}})
                                      for m in game['masters'])
    for place in sorted(cells, key=lambda p: (p[0], p[1:])):
        info = cells[place]
        part = masters[info['master']]['exterior' if place[0] == 'ext' else 'interior']
        part['total'] += 1
        if has(place):
            part['in'] += 1
            continue
        row = {'place': place_key(place), 'name': place_label(place, cells)}
        ok = approved(info['master'], 'exterior' if place[0] == 'ext' else 'interior', place_key(place))
        (part['approved'] if ok else part['missing']).append(dict(row, approved=ok) if ok else row)
    rows = evidence.get('door_rows')
    any_map = evidence.get('any_map')

    def carried(d):
        """'' when the build carries door D, else why not."""
        if not has(d['src']):
            return 'it stands in %s, which is not in the build' % place_label(d['src'], cells)
        if not has(d['dst']):
            return 'it leads to %s, which is not in the build' % place_label(d['dst'], cells)
        if rows is None:
            return ''
        found = [r for r in rows.get(d['ref'], ()) if (r.get('id') or '').casefold() == d['id'].casefold()]
        if not found:
            return 'the image\'s door table has no row for it'
        live = [r for r in found if not r.get('held_back')]
        if not live:
            return 'held back: ' + str(found[0].get('held_back'))
        if any_map and not any(r.get('target') in (None, '') or any_map(r.get('target')) for r in live):
            return 'its target map %s is not in the image' % live[0].get('target')
        return ''
    why = {ref: carried(d) for ref, d in doors.items()}
    for ref in sorted(doors):
        d = doors[ref]
        part = masters[d['master']]['doors']
        part['total'] += 1
        label = '%s -> %s (%s, ref %d)' % (place_label(d['src'], cells), d['dnam'] or place_label(d['dst'], cells),
                                          d['id'], ref)
        ok = approved(d['master'], 'door', 'ref %d' % ref)
        if d.get('dst_unknown'):
            part['to_no_cell'].append(label)
        if why[ref]:
            (part['approved'] if ok else part['missing']).append({'door': label, 'ref': ref, 'why': why[ref]})
            continue
        if not back[ref]:
            part['one_way_in_original'].append(label)
            continue
        if any(not why[e] for e in back[ref]):
            part['both_ways'] += 1
            continue
        lost = '; '.join('ref %d: %s' % (e, why[e]) for e in back[ref][:3])
        (part['approved'] if ok else part['no_way_back']).append({'door': label, 'ref': ref, 'why': lost})
    out = {'format': FORMAT, 'mode': evidence['mode'], 'masters': masters, 'notes': list(evidence.get('notes') or ()),
           'tracker': tracker}
    out['missing'] = sum(len(p[k]) for m in masters.values() for p, k in
                         ((m['exterior'], 'missing'), (m['interior'], 'missing'), (m['doors'], 'missing'),
                          (m['doors'], 'no_way_back')))
    return out


# ------------------------------------------------------------------ d. the two trackers' counts

def tracker_counts(doc):
    """{land id: {terrain: [ready, total], rooms: [ready, total]}} of a tracker doc or a progress-state snapshot (its
    readiness section, tools/master_completion.py; counted now by its rules when a tracker doc has none)."""
    import master_completion as MC
    ready = (doc or {}).get('readiness')
    if not ready or ready.get('format') != MC.FORMAT:
        if (doc or {}).get('cells') is None:
            return None
        ready = MC.readiness(doc)
    return {x['id']: {k: [x[k]['ready'], x[k]['total']] for k in ('terrain', 'rooms')} for x in ready.get('lands') or ()}


def compare_trackers(toolkit_path, public_path):
    """{toolkit, public, differences: [...], problems: [...]} of the Toolkit's tracker data and the public snapshot."""
    out = {'toolkit_file': str(toolkit_path) if toolkit_path else None, 'public_file': str(public_path),
           'toolkit': None, 'public': None, 'differences': [], 'problems': []}
    for side, path in (('toolkit', toolkit_path), ('public', public_path)):
        if not path or not Path(path).is_file():
            out['problems'].append('the %s tracker data is not there (%s)' % (side, path or 'not given'))
            continue
        counts = tracker_counts(json.loads(Path(path).read_text(encoding='utf-8')))
        if counts is None:
            out['problems'].append('%s has no readiness count (%s)' % (side, path))
        out[side] = counts
    if out['toolkit'] and out['public']:
        for land in sorted(set(out['toolkit']) | set(out['public'])):
            a, b = (out['toolkit'].get(land) or {}), (out['public'].get(land) or {})
            for part in ('terrain', 'rooms'):
                if a.get(part) != b.get(part):
                    out['differences'].append('%s %s: the Toolkit %s, the public tracker %s' % (
                        land, part, '%d of %d' % tuple(a[part]) if a.get(part) else 'none',
                        '%d of %d' % tuple(b[part]) if b.get(part) else 'none'))
    return out


# ------------------------------------------------------------------ the verdict and the report

def kind_of(kind=None, version=None):
    if kind:
        return kind
    v = str(version or '')
    return 'dev' if re.search(r'-dev\d+$', v) else 'rc' if re.search(r'-rc\d+$', v) else 'final' if v else 'dev'


def verdict(result, kind, ledger_problems=(), sha_problems=()):
    """Set result['kind'], ['problems'], ['refused'] (rc and final only) and ['line'] (the one-line summary)."""
    problems = []
    for m, p in result['masters'].items():
        for part, what in (('exterior', 'exterior cell'), ('interior', 'interior cell')):
            for row in p[part]['missing']:
                problems.append('%s: %s %s not in the build' % (m, what, row['name']))
        for row in p['doors']['missing']:
            problems.append('%s: load door %s: %s' % (m, row['door'], row['why']))
        for row in p['doors']['no_way_back']:
            problems.append('%s: load door %s has no way back in the build (%s)' % (m, row['door'], row['why']))
    tr = result.get('tracker')
    if tr is not None:
        problems += ['trackers: ' + x for x in tr['differences'] + tr['problems']]
    problems += ['approval ledger: ' + x for x in ledger_problems]
    problems += ['masters: ' + x for x in sha_problems]
    result['kind'] = kind
    result['problems'] = problems
    result['refused'] = kind in ('rc', 'final') and bool(problems)
    names = [row['name'] for p in result['masters'].values() for part in ('exterior', 'interior')
             for row in p[part]['missing']]
    doors = sum(len(p['doors']['missing']) + len(p['doors']['no_way_back']) for p in result['masters'].values())
    head = 'completeness (%s, %s): ' % (result['mode'], kind)
    if not problems:
        result['line'] = head + 'complete: every cell, room and load door of %s is in the build' % ', '.join(result['masters'])
    else:
        result['line'] = head + '%d missing: %s%s%s%s' % (
            len(names) + doors, '; '.join(names[:12]) + (' and %d more' % (len(names) - 12) if len(names) > 12 else ''),
            ('; %d load door(s)' % doors) if doors else '',
            ('; trackers differ (%d)' % len(tr['differences'] + tr['problems'])) if tr and (tr['differences'] or tr['problems']) else '',
            ('; %d other problem(s)' % (len(ledger_problems) + len(sha_problems))) if (ledger_problems or sha_problems) else '')
        if result['refused']:
            result['line'] += ' -> REFUSED for a release'
    return result


def build_start(root, data_files, masters, base_cells=None, module_cells=None, version=None, town_cores=None):
    """The plan's result for tools/build.py's start (printed before the first stage, report only: the release
    preflight and the release guard are where an rc or final is refused). No tracker counts: those are the release's.
    TOWN_CORES: the cores of the CHIM towns the build makes (its exterior checklist's towns)."""
    masters = [m for m in GAME_MASTERS if m in masters]
    ledger, ledger_problems = load_ledger(Path(root) / 'config' / 'release-completeness-approved.json')
    result = assess(load_masters(data_files, masters),
                    plan_evidence(root, masters, base_cells, module_cells, town_cores), ledger)
    return verdict(result, kind_of(None, version), ledger_problems)


def markdown(result):
    out = ['# Completeness of the build (%s, %s)' % (result['mode'], result['kind']), '',
           result['line'], '']
    out += ['| Master | Exterior cells in | Interior cells in | Load doors both ways | Doors missing | No way back | '
            'One way in the original |', '| --- | --- | --- | --- | --- | --- | --- |']
    for m, p in result['masters'].items():
        e, i, d = p['exterior'], p['interior'], p['doors']
        out.append('| %s | %d of %d | %d of %d | %d of %d | %d | %d | %d |' % (
            m, e['in'], e['total'], i['in'], i['total'], d['both_ways'], d['total'], len(d['missing']),
            len(d['no_way_back']), len(d['one_way_in_original'])))
    for m, p in result['masters'].items():
        rows = ([('exterior cell', r['name']) for r in p['exterior']['missing']] +
                [('interior cell', r['name']) for r in p['interior']['missing']] +
                [('load door', '%s: %s' % (r['door'], r['why'])) for r in p['doors']['missing']] +
                [('no way back', '%s: %s' % (r['door'], r['why'])) for r in p['doors']['no_way_back']])
        if rows:
            out += ['', '## %s: missing' % m, ''] + ['- %s: %s' % r for r in rows]
        appr = p['exterior']['approved'] + p['interior']['approved'] + p['doors']['approved']
        if appr:
            out += ['', '## %s: approved in the ledger' % m, ''] + ['- %s' % (r.get('name') or r.get('door')) for r in appr]
    tr = result.get('tracker')
    if tr:
        out += ['', '## The two trackers', '']
        out += ['- ' + x for x in tr['differences'] + tr['problems']] or ['- the Toolkit and the public tracker agree']
    notes = [n for p in result['masters'].values() for n in p['doors']['one_way_in_original']]
    if notes:
        out += ['', '## Notes: load doors the original has no way back through (not refused)', '']
        out += ['- ' + n for n in notes]
    out += ['', '## What was read', ''] + ['- ' + n for n in result['notes']]
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('mode', choices=('plan', 'run', 'ledger'))
    ap.add_argument('--run', help='the build run folder (mode run)')
    ap.add_argument('--root', default=str(ROOT), help='the source tree whose plan is read (mode plan)')
    ap.add_argument('--data-files', default='/owned', help='the folder with the game masters')
    ap.add_argument('--masters', help='the shipped masters, comma list (default: the image\'s, else all three)')
    ap.add_argument('--kind', choices=KINDS)
    ap.add_argument('--version', help='the version the build is for (-devN: dev, -rcN: rc, else final)')
    ap.add_argument('--toolkit', help='the Toolkit\'s tracker data (cell-progress.json) for the counts check')
    ap.add_argument('--public', default=None, help='the public tracker snapshot (default: ROOT/docs/chim/progress-state.json)')
    ap.add_argument('--no-trackers', action='store_true', help='skip the trackers\' counts (a build\'s start line)')
    ap.add_argument('--approved', default=None, help='the approval ledger (default: ROOT/config/release-completeness-approved.json)')
    ap.add_argument('--out', help='write release-completeness.json and .md here')
    ap.add_argument('--json', action='store_true', help='print the result as JSON')
    a = ap.parse_args(argv)
    root = Path(a.root)
    ledger, ledger_problems = load_ledger(a.approved or root / 'config' / 'release-completeness-approved.json')
    if a.mode == 'ledger':
        print('approval ledger: %d place(s) approved, %d problem(s)' % (len(ledger), len(ledger_problems)))
        for p in ledger_problems:
            print('  ' + p)
        return 1 if ledger_problems else 0
    if a.mode == 'run' and not a.run:
        ap.error('run: --run RUN')
    started = datetime.datetime.now()
    sha_problems = []
    try:
        evidence = run_evidence(a.run) if a.mode == 'run' else plan_evidence(root, (a.masters or ','.join(GAME_MASTERS)).split(','))
    except (OSError, ValueError, KeyError) as exc:
        kind = kind_of(a.kind, a.version)
        print('completeness (%s, %s): NOT CHECKED: %s' % (a.mode, kind, exc))
        return 1 if kind in ('rc', 'final') else 0
    masters = [m.strip() for m in a.masters.split(',')] if a.masters else (
        list(evidence['masters_sha256']) if evidence.get('masters_sha256') else list(GAME_MASTERS))
    masters = [m for m in GAME_MASTERS if m in masters]
    try:
        game = load_masters(a.data_files, masters)
    except (OSError, ValueError) as exc:
        kind = kind_of(a.kind, a.version or evidence.get('version'))
        print('completeness (%s, %s): NOT CHECKED: the masters: %s' % (a.mode, kind, exc))
        return 1 if kind in ('rc', 'final') else 0
    for m, want in (evidence.get('masters_sha256') or {}).items():
        if m in game['sha256'] and game['sha256'][m] != want:
            sha_problems.append('%s read here (%s) is not the one the build used (%s)' % (m, game['sha256'][m][:12], want[:12]))
    tracker = None if a.no_trackers else compare_trackers(a.toolkit, a.public or root / 'docs' / 'chim' / 'progress-state.json')
    result = assess(game, evidence, ledger, tracker)
    kind = kind_of(a.kind, a.version or evidence.get('version'))
    verdict(result, kind, ledger_problems, sha_problems)
    result['run'] = evidence.get('run')
    result['version'] = a.version or evidence.get('version')
    result['seconds'] = round((datetime.datetime.now() - started).total_seconds(), 2)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / REPORT_JSON).write_text(json.dumps(result, indent=1, default=str) + '\n', encoding='utf-8', newline='\n')
        (out / REPORT_MD).write_text(markdown(result), encoding='utf-8', newline='\n')
    if a.json:
        print(json.dumps(result, indent=1, default=str))
    else:
        for m, p in result['masters'].items():
            e, i, d = p['exterior'], p['interior'], p['doors']
            print('  %s: exterior cells %d of %d, interior cells %d of %d, load doors %d both ways of %d, %d missing, '
                  '%d without their way back, %d one way in the original' % (
                      m, e['in'], e['total'], i['in'], i['total'], d['both_ways'], d['total'], len(d['missing']),
                      len(d['no_way_back']), len(d['one_way_in_original'])))
        for line in result['problems'][:200]:
            print('  MISSING ' + line if not line.startswith(('trackers', 'approval', 'masters')) else '  PROBLEM ' + line)
        print(result['line'] + ' (%.1f s)' % result['seconds'])
    return 1 if result['refused'] else 0


if __name__ == '__main__':
    sys.exit(main())
