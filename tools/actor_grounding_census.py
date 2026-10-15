#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Island-wide actor grounding census and the build preflight check (CHIM-ACTOR-GROUNDING-POLICY-36).

The grounding policy (config/actor_grounding.json, tools/actor_grounding.py) is an explicit list: every
placed NPC is either standing on the ground or a documented exception, and an unclassified NPC is an
error, so no behaviour is guessed. This tool fills that list for the whole island by MEASUREMENT from
the owner's own game data, instead of town by town:

  census     every NPC placed in an exterior cell of the base master. For each placement the feet
             (the reference position) are compared with the highest support under them: the LAND
             surface (the converter's own triangle split, prepare_world_regions) or a triangle of a
             static object it may stand on (STAT, ACTI, DOOR, CONT, LIGH placed in the same or a
             neighbouring cell; visible and collision triangles, placed like the scenery converter
             places them). The support is sampled at the centre and 8 points on a 16-unit foot circle
             and the highest wins. gap = feet - support:
               -STEP_UP <= gap <= DROP   ground (feet a little inside the support or a little above it:
                                         the build fits and the engine settles that much, TOLERANCE below)
               otherwise                 candidate exception, reported with the measured numbers
             Also a candidate, whatever the gap: feet below sea level (OpenMW World::isSwimming decides
             swimming from the water level) and an NPC whose record carries a Levitate ability (OpenMW
             World::isFlying: a Levitate magnitude makes an actor fly).
             An NPC id is ground only when EVERY exterior placement of it measures ground. An NPC
             whose record is placed dead (NPDT health 0) is authored_dead: the record says so.
             Nothing else is classified automatically: flying, levitating, swimming or scripted
             airborne states need a cited source (the NPC/script records, the OpenMW source, the
             private UESP corpus) and are decided by a person.
  --write    merge the census into config/actor_grounding.json (format 2): every existing entry and
             exception is kept; new ground NPCs and record-sourced authored_dead exceptions are added;
             unresolved candidates are listed in the report, never written.
  preflight  area_problems(): every NPC resident of every CHIM area of a build is classified. Reads
             only the master's exterior cells (seconds); tools/build.py runs it before any stage.

    python3 tools/actor_grounding_census.py --data-files DATA --report OUT.json [--write] [--jobs N]
    python3 tools/actor_grounding_census.py --data-files DATA --check-area balmora [--check-area ...]

The report holds placements and heights from the game data: keep it private (it is not a repo file).
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

CELL = 8192
LAND_STEP = 128
# TOLERANCE (Morrowind units), from what the build itself fits and what the engine does:
# - the support fitter (actor_grounding._Fitter._setup, also on CHIM frames) looks for the support from
#   8 Quake units above the authored feet down 40 Quake units, at the world scale 0.25: from 32 Morrowind
#   units inside a support (STEP_UP) to 128 above it (DROP). A gap outside that cannot be fitted.
# - the original game data places most actors a little above their support and the engine settles them:
#   OpenMW 0.51 World::adjustPosition lifts an actor that is not flying or swimming 20 units and traces it
#   down onto the first collision below; the exterior placements of the hand-classified ground NPCs of the
#   shipped towns (Seyda Neen, Balmora, Vivec) measure from -20 to +91 here.
STEP_UP = 32.0
DROP = 128.0
FOOT_RADIUS = 16.0
SUPPORT_TYPES = ('STAT', 'ACTI', 'DOOR', 'CONT', 'LIGH')
WATER_LEVEL = 0.0  # exterior sea level of the base master
CENSUS_FORMAT = 'AmiWind actor grounding census 1'


# ---------------------------------------------------------------- master reading (no numpy)

def _exterior_cells(raw):
    """{(x, y): cell} of the master's exterior cells, the NPC_ ids, and their records."""
    from mwad.audit import cell_data, records, subrecords
    cells, npcs = {}, {}
    for tag, flags, payload in records(raw):
        if tag == 'CELL':
            subs = list(subrecords(payload))
            data = next((v for k, v in subs if k == 'DATA'), b'')
            if len(data) == 12 and not struct.unpack_from('<I', data)[0] & 1:
                cell = cell_data(subs)
                cells[(cell['x'], cell['y'])] = cell
        elif tag == 'NPC_':
            subs = list(subrecords(payload))
            name = next((v for k, v in subs if k == 'NAME'), b'').rstrip(b'\0').decode('cp1252')
            if name:
                npcs[name.casefold()] = subs
    return cells, npcs


def levitate_abilities(raw):
    """Casefolded ids of SPEL abilities (SPDT type 1) with a Levitate effect (ENAM index 10)."""
    from mwad.audit import records, subrecords
    found = set()
    for tag, flags, payload in records(raw):
        if tag != 'SPEL' or flags & 0x20:
            continue
        subs = list(subrecords(payload))
        name = next((v for k, v in subs if k == 'NAME'), b'').rstrip(b'\0').decode('cp1252')
        kind = next((v for k, v in subs if k == 'SPDT'), b'')
        if (len(kind) >= 4 and struct.unpack_from('<i', kind)[0] == 1
                and any(k == 'ENAM' and len(v) >= 2 and struct.unpack_from('<h', v)[0] == 10 for k, v in subs)):
            found.add(name.casefold())
    return found


def npc_facts(subs, levitating=()):
    """What the NPC_ record itself says: placed dead (NPDT health 0), its script, spells, Levitate abilities."""
    fields = {}
    for k, v in subs:
        fields.setdefault(k, []).append(v)
    stats = fields.get('NPDT', [b''])[0]
    text = lambda v: v.rstrip(b'\0').decode('cp1252')  # noqa: E731
    return {'dead': len(stats) == 52 and struct.unpack_from('<h', stats, 38)[0] <= 0,
            'script': text(fields['SCRI'][0]) if 'SCRI' in fields else '',
            'spells': sorted(text(v) for v in fields.get('NPCS', [])),
            'levitate_abilities': sorted(text(v) for v in fields.get('NPCS', []) if text(v).casefold() in levitating)}


def npc_placements(cells, npcs):
    """[(cell key, ref)] of every live NPC_ placement in an exterior cell."""
    return [(key, ref) for key, cell in sorted(cells.items()) for ref in cell['refs']
            if not ref.get('deleted') and ref['id'].casefold() in npcs]


# ---------------------------------------------------------------- preflight (seconds)

def area_box(area, root=None):
    """The CHIM area's frame in Morrowind units (x0, y0, x1, y1), as chim.areas compares frames."""
    if area == 'seyda':
        from chim.seyda import owned_world_box
        return owned_world_box(root=root)
    from town_config import load_settings
    settings = load_settings(area, root)
    (lx, ly), (hx, hy) = settings['bounds']
    c = settings['centre']
    s = 1 / settings['scale']
    return c[0] + s * lx, c[1] + s * ly, c[0] + s * hx, c[1] + s * hy


def area_exclusions(area, root=None):
    if area == 'seyda':
        return set()
    from town_config import load_settings, resident_exclusions
    return set(resident_exclusions(load_settings(area, root)))


def area_residents(cells, npcs, box, skip=()):
    """Sorted NPC ids placed in exterior cells with their origin inside BOX (frame, Morrowind units)."""
    x0, y0, x1, y1 = box
    found = set()
    for cx in range(math.floor(x0 / CELL), math.floor(x1 / CELL) + 1):
        for cy in range(math.floor(y0 / CELL), math.floor(y1 / CELL) + 1):
            for ref in cells.get((cx, cy), {'refs': []})['refs']:
                key = ref['id'].casefold()
                x, y = ref['position'][:2]
                if not ref.get('deleted') and key in npcs and key not in skip and x0 <= x <= x1 and y0 <= y <= y1:
                    found.add(key)
    return sorted(found)


def unclassified(identifiers, policy=None):
    """The ids actor_grounding.initial_state() would refuse."""
    from actor_grounding import POLICY, initial_state
    policy = Path(policy or POLICY)
    missing = []
    for identifier in identifiers:
        try:
            initial_state(identifier) if policy == POLICY else _state(identifier, policy)
        except ValueError:
            missing.append(identifier)
    return missing


def _state(identifier, policy):
    """initial_state() against another policy file (tests)."""
    import actor_grounding
    saved = actor_grounding.POLICY
    actor_grounding.POLICY = Path(policy)
    try:
        return actor_grounding.initial_state(identifier)
    finally:
        actor_grounding.POLICY = saved


def area_problems(data_files, areas, root=None, policy=None):
    """[problem] for every CHIM area of a build with an NPC resident the grounding policy does not
    classify (the chim-town stage would stop on it, 40 minutes in). Empty when all are classified."""
    from mwad.paths import child_ci
    raw = Path(child_ci(Path(data_files), 'Morrowind.esm')).read_bytes()
    cells, npcs = _exterior_cells(raw)
    problems = []
    for area in areas:
        residents = area_residents(cells, npcs, area_box(area, root), area_exclusions(area, root))
        missing = unclassified(residents, policy)
        if missing:
            problems.append('CHIM area %s: %d of %d NPC residents have no grounding classification in '
                            'config/actor_grounding.json (%s); fix: python3 tools/actor_grounding_census.py '
                            '--data-files DATA --report REPORT.json --write, then classify the listed candidates '
                            'by their cited source (CHIM-ACTOR-GROUNDING-POLICY-36)'
                            % (area, len(missing), len(residents), ', '.join(missing)))
    return problems


# ---------------------------------------------------------------- measurement

def land_height(lands, x, y):
    """LAND surface at (x, y), Morrowind units; the converter's split of each 128-unit quad
    (prepare_world_regions.Terrain.shoreline_detail). None where the cell has no LAND."""
    cx, cy = math.floor(x / CELL), math.floor(y / CELL)
    heights = lands.get((cx, cy))
    if heights is None:
        return None
    fx, fy = (x - cx * CELL) / LAND_STEP, (y - cy * CELL) / LAND_STEP
    ix, iy = min(63, int(fx)), min(63, int(fy))
    u, v = fx - ix, fy - iy
    a, b = heights[iy][ix], heights[iy][ix + 1]
    c, d = heights[iy + 1][ix + 1], heights[iy + 1][ix]
    return a + (b - a) * u + (c - b) * v if v <= u else a + (c - d) * u + (d - a) * v


def foot_points(x, y):
    points = [(x, y)]
    for k in range(8):
        angle = k * math.pi / 4
        points.append((x + FOOT_RADIUS * math.cos(angle), y + FOOT_RADIUS * math.sin(angle)))
    return points


def surface_heights(tris, x, y):
    """Heights of the triangles (N x 3 x 3 world array) above/below the vertical line at (x, y)."""
    import numpy as np
    if not len(tris):
        return np.zeros(0)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    v0, v1 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2]
    p = np.array([x, y]) - a[:, :2]
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1)
    s = (p[:, 0] * v1[:, 1] - v1[:, 0] * p[:, 1]) / den
    t = (v0[:, 0] * p[:, 1] - p[:, 0] * v0[:, 1]) / den
    inside = ok & (s >= -1e-6) & (t >= -1e-6) & (s + t <= 1 + 1e-6)
    z = a[:, 2] + s * (b[:, 2] - a[:, 2]) + t * (c[:, 2] - a[:, 2])
    return z[inside]


def support(z, land, statics):
    """(height, kind) of the highest support at or below z + STEP_UP, or (None, None)."""
    best, kind = None, None
    if land is not None and land <= z + STEP_UP:
        best, kind = land, 'land'
    for height, name in statics:
        if height <= z + STEP_UP and (best is None or height > best):
            best, kind = height, name
    return best, kind


def classify_gap(gap):
    return gap is not None and -STEP_UP <= gap <= DROP


def _read_model(task):
    """Worker: (name, vertices, faces, error) of a model's visible + collision triangles, model space."""
    name, path, extent, loose = task
    try:
        import numpy as np
        from mwad.scene import unpack_geometry
        from prepare_scenery import model_geometry, nif_reader
        if loose:
            raw = Path(loose).read_bytes()
        else:
            with Path(path).open('rb') as source:
                source.seek(extent['offset'])
                raw = source.read(extent['bytes'])
        N = nif_reader()
        verts, faces = [], []
        for collision in (False, True):
            try:
                packet = model_geometry(raw, N, collision=collision)[0]
            except ValueError:
                continue
            v, f, _ = unpack_geometry(packet)
            base = sum(len(x) for x in verts)
            verts.append(np.array([p[:3] for p in v], dtype=float))
            faces.append(np.array([q[:3] for q in f], dtype=np.int64) + base)
        if not verts:
            return name, None, None, 'no triangles'
        return name, np.concatenate(verts), np.concatenate(faces), None
    except Exception as exc:  # a model the reader cannot parse is reported, never fatal
        return name, None, None, '%s: %s' % (type(exc).__name__, exc)


def measure(data_files, jobs=1, log=print):
    """The census rows of every exterior NPC placement (see the module docstring)."""
    import numpy as np
    from mwad.audit import BSA, decode_heights, normpath, records, subrecords
    from mwad.paths import child_ci
    from build_parallel import ordered_map
    from prepare_scenery import reference_rotation
    data_files = Path(data_files)
    raw = Path(child_ci(data_files, 'Morrowind.esm')).read_bytes()
    cells, npcs = _exterior_cells(raw)
    lands, objects = {}, {}
    for tag, flags, payload in records(raw):
        if tag == 'LAND':
            s = dict(subrecords(payload))
            if 'VHGT' in s and len(s.get('INTV', b'')) == 8 and not flags & 0x20:
                lands[struct.unpack('<ii', s['INTV'])] = decode_heights(s['VHGT'])
        elif tag in SUPPORT_TYPES:
            s = dict(subrecords(payload))
            if 'NAME' in s and s.get('MODL') and not flags & 0x20 and 'DELE' not in s:
                objects[s['NAME'].rstrip(b'\0').decode('cp1252').casefold()] = \
                    normpath('meshes/' + s['MODL'].rstrip(b'\0').decode('cp1252'))
    placements = npc_placements(cells, npcs)
    near = {}
    for key, _ in placements:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                k = (key[0] + dx, key[1] + dy)
                if k in cells:
                    near[k] = [r for r in cells[k]['refs'] if not r.get('deleted') and r['id'].casefold() in objects]
    names = sorted({objects[r['id'].casefold()] for refs in near.values() for r in refs})
    bsa = BSA(child_ci(data_files, 'Morrowind.bsa'))
    # Models from the base archive, as the scenery converter reads them (prepare_scenery.export_refs).
    tasks = [(name, str(bsa.path), bsa.entries[name], None) for name in names if name in bsa.entries]
    log('Census: %d exterior NPC placements, %d support models' % (len(placements), len(tasks)))
    models, errors = {}, {}
    for name, verts, faces, error in ordered_map(_read_model, tasks, max(1, min(jobs, len(tasks) or 1))):
        if error:
            errors[name] = error
        else:
            models[name] = (verts, faces, verts.min(axis=0), verts.max(axis=0))
    placed = {}

    def placed_tris(ref):
        number = ref['number']
        if number not in placed:
            model = models.get(objects[ref['id'].casefold()])
            if model is None:
                placed[number] = None
            else:
                verts, faces, low, high = model
                world = verts @ reference_rotation(ref).T * ref['scale'] + np.array(ref['position'])
                tris = world[faces]
                placed[number] = (tris, tris[:, :, 0].min(), tris[:, :, 1].min(),
                                  tris[:, :, 0].max(), tris[:, :, 1].max())
        return placed[number]

    rows = []
    for key, ref in placements:
        x, y, z = ref['position']
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in near.get((key[0] + dx, key[1] + dy), []):
                    entry = placed_tris(other)
                    if entry is None:
                        continue
                    tris, x0, y0, x1, y1 = entry
                    if x0 - FOOT_RADIUS <= x <= x1 + FOOT_RADIUS and y0 - FOOT_RADIUS <= y <= y1 + FOOT_RADIUS:
                        candidates.append((other, tris))
        best = (None, None, None)
        for fx, fy in foot_points(x, y):
            land = land_height(lands, fx, fy)
            statics = [(h, other['id']) for other, tris in candidates for h in surface_heights(tris, fx, fy).tolist()]
            height, kind = support(z, land, statics)
            if height is not None and (best[0] is None or height > best[0]):
                best = (height, kind, land)
        land_here = land_height(lands, x, y)
        gap = None if best[0] is None else z - best[0]
        rows.append({'id': ref['id'].casefold(), 'reference': ref['number'], 'cell': list(key),
                     'position': [round(v, 3) for v in ref['position']],
                     'land': None if land_here is None else round(land_here, 3),
                     'support': None if best[0] is None else round(best[0], 3), 'support_kind': best[1],
                     'gap': None if gap is None else round(gap, 3), 'ground': classify_gap(gap),
                     'below_water': z < WATER_LEVEL})
    levitating = levitate_abilities(raw)
    facts = {identifier: npc_facts(npcs[identifier], levitating) for identifier in {r['id'] for r in rows}}
    return rows, facts, errors


def classify(rows, facts, policy):
    """(ground ids, authored_dead {id: rule}, candidates {id: [rows]}, conflicts) against POLICY (dict)."""
    known_ground = set(policy['ground_npcs'])
    known_rules = {k.casefold() for k in policy['exceptions']}
    by_id = {}
    for row in rows:
        by_id.setdefault(row['id'], []).append(row)
    ground, dead, candidates, conflicts = set(), {}, {}, []
    for identifier, placed in sorted(by_id.items()):
        measured = (all(r['ground'] and not r['below_water'] for r in placed)
                    and not facts[identifier].get('levitate_abilities'))
        if identifier in known_rules:
            continue
        if identifier in known_ground:
            if not measured:
                conflicts.append({'id': identifier, 'rows': placed})
            continue
        if facts[identifier]['dead']:
            dead[identifier] = {'mode': 'authored_dead', 'source': 'NPC_ record NPDT: health 0 (base master)',
                                'reason': 'Authored initially dead NPC; preserve the converted death pose and placement.'}
        elif measured:
            ground.add(identifier)
        else:
            candidates[identifier] = {'rows': placed, 'record': facts[identifier]}
    return ground, dead, candidates, conflicts


def merged_policy(policy, ground, dead):
    out = dict(policy)
    out['ground_npcs'] = sorted(set(policy['ground_npcs']) | set(ground))
    exceptions = dict(policy['exceptions'])
    for identifier, rule in sorted(dead.items()):
        exceptions.setdefault(identifier, rule)
    out['exceptions'] = exceptions
    return out


def main(argv=None):
    from build_jobs import add_jobs, resolve_jobs
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data-files', type=Path, required=True)
    ap.add_argument('--report', type=Path, help='census report (private: game-derived placements)')
    ap.add_argument('--write', action='store_true', help='merge new ground NPCs and authored_dead into the policy')
    ap.add_argument('--policy', type=Path, default=None)
    ap.add_argument('--check-area', action='append', default=[], metavar='AREA',
                    help='only the preflight check for these CHIM areas')
    add_jobs(ap)
    args = ap.parse_args(argv)
    from actor_grounding import POLICY
    policy_path = args.policy or POLICY
    if args.check_area:
        problems = area_problems(args.data_files, args.check_area, policy=policy_path)
        for problem in problems:
            print('Grounding preflight: ' + problem)
        print('Grounding preflight: %d problems' % len(problems))
        return 1 if problems else 0
    rows, facts, errors = measure(args.data_files, resolve_jobs(args.jobs))
    policy = json.loads(Path(policy_path).read_text())
    ground, dead, candidates, conflicts = classify(rows, facts, policy)
    ids = {r['id'] for r in rows}
    summary = {'exterior_placements': len(rows), 'exterior_npcs': len(ids),
               'measured_ground_placements': sum(r['ground'] for r in rows),
               'already_ground': len(ids & set(policy['ground_npcs'])),
               'already_exception': len(ids & {k.casefold() for k in policy['exceptions']}),
               'new_ground': len(ground), 'new_authored_dead': len(dead), 'unresolved': len(candidates),
               'conflicts': len(conflicts), 'model_errors': len(errors)}
    print(json.dumps(summary, indent=2))
    for identifier, info in candidates.items():
        print('Unresolved:', identifier, json.dumps([{k: r[k] for k in ('cell', 'position', 'land', 'support',
                                                                        'support_kind', 'gap', 'below_water')}
                                                     for r in info['rows']]), info['record'])
    for conflict in conflicts:
        print('Conflict (listed ground, measured off ground):', conflict['id'],
              json.dumps([{k: r[k] for k in ('cell', 'position', 'support', 'gap')} for r in conflict['rows']]))
    if args.report:
        args.report.write_text(json.dumps({'format': CENSUS_FORMAT, 'tolerance': {'step_up': STEP_UP, 'drop': DROP,
                                                                                    'foot_radius': FOOT_RADIUS},
                                           'summary': summary, 'rows': rows, 'new_ground': sorted(ground),
                                           'new_authored_dead': dead, 'unresolved': candidates,
                                           'conflicts': conflicts, 'model_errors': errors}, indent=1) + '\n',
                               encoding='utf-8', newline='\n')
    if args.write:
        Path(policy_path).write_text(json.dumps(merged_policy(policy, ground, dead), indent=2) + '\n',
                                     encoding='utf-8', newline='\n')
        print('Policy written:', policy_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
