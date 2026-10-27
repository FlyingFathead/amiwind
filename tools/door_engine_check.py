# SPDX-License-Identifier: GPL-3.0-only
"""Every exterior entrance through the engine's own door code (DOOR-ENTRANCE-AUDIT-51, DOOR-BANK-STREAMED-FRAME-51,
CHIM-REGION-DOORS-NO-PROMPT-42): door, then entrance, then interior, and the way back, checked natively in seconds.

The door audit (tools/door_audit.py) reads the image the way the engine should; this check runs the engine itself: the
scene code (aw_scene.c with aw_world.c, aw_region.c and the rest tests/aga_scene_test.c links) is compiled for the host
with tools/door_engine_check.c and run over the built image's door banks, open-world directory and maps, read only. For
every exterior entrance of the original that leads into an interior (the audit's rows):
  - a region frame's door: the game runs a NEIGHBOURING region frame, the player walks over the border into the
    door's frame (the streamed type 1 crossing, the state DOOR-BANK-STREAMED-FRAME-51 broke: 830 of 1,102 entrances
    dead after walking in), then stands where the game puts a player who walks out of that room (the room exit's
    arrival, brought within reach of the door) facing the door's use box; a town's door: the town runs;
  - the prompt (AW_SceneDraw) must say "(Enter: E)", the use key (AW_SceneUse) and a script's Activate
    (AW_SceneActivate) must each queue the door's room;
  - the way back: in the room, at the arrival this door gives, facing the room's exit to this door: its use must
    queue the exterior the exit leads to.
The wall trace between the eye and the door is open here (the maps' collision is not loaded), and whether the door
model is drawn is the audit's "placed" check (the CHIM frame places the door) and the in-game sample's stills.

    python3 tools/door_engine_check.py --build BUILD --audit door-audit.json --out DIR [--engine-src DIR]
        [--scene-source FILE] [--baseline FILE] [--jobs N]
    python3 tools/door_engine_check.py --build BUILD --data-files DIR --out DIR ...   (runs the audit first)
Writes OUT/door-engine-check.json and OUT/door-engine-check.md (private: built from your game data). With --baseline
(config/door-check-baseline.json) a whole-world image fails when fewer entrances are usable than the last build's
count: the count only goes up.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

FORMAT = 'aw-door-engine-check-1'
BASELINE_FORMAT = 'aw-door-check-baseline-1'
EYE = 30.0          # the eye above the door's threshold (the box's floor; 32 measured in game at a Grazelands door)
REACH = 40.0        # stand this near the use box (the engine reaches 56)
PAST = 160.0        # the start spot: this far into the neighbouring frame, past the door frame's core
INSIDE = 128.0      # the crossing spot: this far inside the door frame's core (past the 64-unit margin)
PROMPT = '(Enter: E)'
OPENING_MAPS = frozenset({'prison', 'census', 'intro_docks', 'sncourt'})   # door_audit.OPENING_MAPS
# the scene code and what the scene fixture links with it (tests/test_aga_native_source.py compile_run)
ENGINE_FILES = ('aw_scene.c', 'aw_region.c', 'aw_story.c', 'aw_state.c', 'mathlib.c', 'cl_main.c', 'view.c',
                'aw_section.c', 'aw_world.c', 'aw_mappath.c', 'aw_miniwind.c', 'aw_harvest.c', 'aw_harvest_runtime.c',
                'aw_excluded.c', 'aw_format.c', 'aw_harvest_proxy.c')


def _inside(core, point, margin=0.0):
    return core[0] - margin <= point[0] <= core[2] + margin and core[1] - margin <= point[1] <= core[3] + margin


def aim(stand, box):
    """(eye, yaw, pitch) of a player standing at STAND's place (horizontally; brought within REACH of BOX's centre)
    on the door's threshold (the box's floor), looking at the box's centre."""
    centre = [(box[0][k] + box[1][k]) / 2 for k in range(3)]
    d = math.hypot(stand[0] - centre[0], stand[1] - centre[1])
    if d > REACH:
        t = REACH / d
        stand = [centre[0] + (stand[0] - centre[0]) * t, centre[1] + (stand[1] - centre[1]) * t]
    elif d < 1.0:
        stand = [centre[0] - REACH, centre[1]]
    eye = [stand[0], stand[1], min(box[0][2] + EYE, box[1][2] - 4)]
    yaw = math.degrees(math.atan2(centre[1] - eye[1], centre[0] - eye[0])) % 360
    pitch = -math.degrees(math.atan2(centre[2] - eye[2], math.hypot(centre[0] - eye[0], centre[1] - eye[1])))
    return eye, yaw, max(-70.0, min(80.0, pitch))


def neighbour_walks(directory, holder, stand):
    """[(running map, start, crossing)]: walks into region frame HOLDER from the frames across its core edges, the
    edge nearest to STAND (holder coordinates) first, both points in the running map's coordinates.
    directory: [(name, origin, core)] (chim.frame_map.world_directory)."""
    import door_audit
    frames = {n: (o, c) for n, o, c in directory}
    origin, core = frames[holder]
    edges = sorted([(stand[0] - core[0], (-1, 0)), (core[2] - stand[0], (1, 0)), (stand[1] - core[1], (0, -1)),
                    (core[3] - stand[1], (0, 1))])
    out = []
    for dist, (ex, ey) in edges:
        dist = max(dist, 0.0)
        start = [stand[0] + ex * (dist + PAST), stand[1] + ey * (dist + PAST)]
        hit = door_audit.directory_frame(directory, [start[0] + origin[0], start[1] + origin[1]])
        if not hit or hit[0] == holder:
            continue
        inward = min(INSIDE, (core[2] - core[0]) / 2 if ex else (core[3] - core[1]) / 2)
        edge_point = [stand[0] + ex * dist, stand[1] + ey * dist]
        cross = [edge_point[0] - ex * inward, edge_point[1] - ey * inward]
        shift = [origin[k] - hit[1][k] for k in range(3)]
        z = stand[2] + 8
        out.append((hit[0], [start[0] + shift[0], start[1] + shift[1], z + shift[2]],
                    [cross[0] + shift[0], cross[1] + shift[1], z + shift[2]]))
    return out


def job_lines(rows, bank, directory):
    """[(row, job line or None, why not)] for the audit ROWS; BANK(map) -> parse_bank result or None."""
    out = []
    for row in rows:
        if 'bank' not in row or not row.get('holder'):
            out.append((row, None, 'no bank row for the door (the audit: %s)' % '; '.join(row.get('problems') or [])))
            continue
        holder, box, target = row['holder'], row['bank']['box'], row['bank']['target']
        room_bank = bank(target) if target and target != '-' else None
        exits = [l for l in (room_bank or {}).get('links', []) if l['reference'] == row.get('exit_reference')]
        stand = list(exits[0]['arrival']) if exits and exits[0]['target'] == holder else \
            [box[0][0] - REACH, (box[0][1] + box[1][1]) / 2, box[0][2]]
        eye, yaw, pitch = aim(stand, box)
        line = 'D %d %s %s %.2f %.2f' % (row['reference'], holder, ' '.join('%.2f' % v for v in eye), yaw, pitch)
        if row.get('holder_kind') == 'region':
            walks = neighbour_walks(directory, holder, eye)
            if not walks:
                out.append((row, None, 'no neighbouring region frame to walk in from'))
                continue
            for running, start, cross in walks:
                line += ' W %s %s %s' % (running, ' '.join('%.2f' % v for v in start),
                                         ' '.join('%.2f' % v for v in cross))
        if exits:
            # the way back: in the room at this door's arrival, facing the room's exit to it
            reye, ryaw, rpitch = aim(list(row['bank']['arrival']), [exits[0]['mins'], exits[0]['maxs']])
            line += ' B %s %s %.2f %.2f' % (target, ' '.join('%.2f' % v for v in reye), ryaw, rpitch)
        out.append((row, line, None))
    return out


def compile_harness(engine_src, tmp, scene_source=None):
    """The host build of tools/door_engine_check.c with ENGINE_SRC's scene code (SCENE_SOURCE: another aw_scene.c,
    e.g. an earlier release's, for a before/after count). Returns the executable."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('aw_door_check_project_version', ROOT / 'tools/project_version.py')
    version = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version)
    tmp = Path(tmp)
    version.generate_native(ROOT / 'VERSION', tmp)
    src = Path(engine_src)
    files = [Path(scene_source) if scene_source and n == 'aw_scene.c' else src / n for n in ENGINE_FILES]
    exe = tmp / 'door_engine_check'
    cmd = [os.environ.get('CC', 'cc'), '-std=gnu89', '-O1', '-w', *os.environ.get('AW_DOOR_CHECK_CFLAGS', '').split(),
           '-ffunction-sections', '-fdata-sections',
           '-include', str(ROOT / 'tests/aga_test_files.h'), '-Wl,--gc-sections', '-I' + str(tmp), '-I' + str(src),
           '-I' + str(ROOT / 'tests'), str(ROOT / 'tools/door_engine_check.c'), *map(str, files),
           str(ROOT / 'tests/aga_hook_stubs.c'), '-lm', '-o', str(exe)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('door engine check: the harness does not build:\n' + result.stderr[-4000:])
    return exe


def run_harness(exe, id1, lines, jobs, tmp, world_id1=()):
    """{reference: result fields} from the harness over LINES, split over JOBS processes."""
    jobs = max(1, min(jobs, len(lines) or 1))
    parts = [lines[k::jobs] for k in range(jobs)]
    procs = []
    for k, part in enumerate(parts):
        path = Path(tmp) / ('jobs-%d.txt' % k)
        path.write_text('\n'.join(part) + '\n', encoding='utf-8', newline='\n')
        procs.append(subprocess.Popen([str(exe), str(path), str(id1), *map(str, world_id1)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      cwd=str(tmp), text=True, encoding='cp1252', errors='replace'))
    out = {}
    for proc in procs:
        stdout, stderr = proc.communicate()
        if proc.returncode:
            raise RuntimeError('door engine check: the harness stopped (exit %d): %s' % (proc.returncode, stderr[-2000:]))
        for text in stdout.splitlines():
            f = text[2:].split('\t') if text.startswith('R ') else []
            if len(f) == 9 and f[0].isdigit():
                out[int(f[0])] = dict(zip(('scene_after_crossing', 'scene_at_door', 'prompt', 'name', 'use', 'activate',
                                           'back', 'note'), f[1:]))
    return out


def judge(row, result, back_expected):
    """The checklist row of one entrance: each check yes/no and the reasons."""
    holder, target = row['holder'], row['bank']['target']
    checks = {'crossing': 'yes' if result['scene_after_crossing'] == holder else 'no',
              'in_frame_at_door': 'yes' if result['scene_at_door'] == holder else 'no',
              'prompt': 'yes' if result['prompt'] == PROMPT else 'no',
              'enters': 'yes' if result['use'] == target else 'no',
              'activate': 'yes' if result['activate'] == target else 'no',
              'way_back': 'yes' if back_expected and result['back'] == back_expected else 'no'}
    if target in OPENING_MAPS:
        # the opening's own rooms (the census office, the prison ship): the story's scenes lead out of them
        # (aw_opening.c, aw_intro.c), as tools/door_audit.py leaves them
        checks['way_back'] = 'not checked'
    reasons = []
    if checks['crossing'] == 'no':
        reasons.append('after the crossing the scene is %s, not %s' % (result['scene_after_crossing'], holder))
    if checks['in_frame_at_door'] == 'no':
        reasons.append('at the door the player stands in %s, not %s' % (result['scene_at_door'], holder))
    if checks['prompt'] == 'no':
        reasons.append('the prompt is %r' % result['prompt'])
    if checks['enters'] == 'no':
        reasons.append('the use key gives %s, not %s' % (result['use'], target))
    if checks['activate'] == 'no':
        reasons.append('Activate gives %s, not %s' % (result['activate'], target))
    if checks['way_back'] == 'no':
        reasons.append('the way back gives %s, not %s' % (result['back'], back_expected or 'an exit'))
    if result['note'] != '-':
        reasons.append(result['note'])
    return checks, reasons


HULL_FEET = 16.625      # tools/player_hull.py MINS[2]: the standing origin above the ground
VIEW = 14.45            # the eye above the standing origin (measured in game at the Tel Vos guard tower door, dev2)
STAND_DROP = 80.0       # the standing spot is searched up to this far above the door's threshold (under roofs and
                        # eaves first; over a doorway structure a player stands on, the use reach decides)
BELOW_THRESHOLD = 24.0  # a standing spot this far below the threshold is off a platform: not at the door
WALKABLE = 0.7          # sv_phys.c: a floor whose normal points up less than this is a slope the player slides off


def door_hit(mins, maxs, eye, forward, reach=56.0):
    """aw_scene.c door_hit: the entry point of the view ray into the use box within REACH, or None."""
    near, far = 0.0, reach
    for k in range(3):
        if abs(forward[k]) < 1e-5:
            if eye[k] < mins[k] or eye[k] > maxs[k]:
                return None
            continue
        a, b = (mins[k] - eye[k]) / forward[k], (maxs[k] - eye[k]) / forward[k]
        a, b = min(a, b), max(a, b)
        near, far = max(near, a), min(far, b)
        if near > far:
            return None
    if far < 0 or near > reach:
        return None
    return [eye[k] + forward[k] * near for k in range(3)]


def _reach_unit(task):
    """Worker: the doors of one CHIM region frame against the frame's own collision (chim.collision.FrameScene: its
    chunk terrain and the hulls of everything it places, as the engine collides them): where a player stands at the
    door (dropped from just above the threshold), the eye there, and the engine's wall trace from the eye to the
    use box (aw_scene.c aimed_door: the use is refused when a surface lies more than DOOR_USE_SLACK before the box)."""
    world_dir, index, doors, slack = task
    from chim import reach, placed, placement_light, terc, thgt  # noqa: F401 (world formats 0.8 .. 0.13)
    from chim.collision import FrameScene, stand_height
    from chim.validate import load_frame
    row, models = load_frame(world_dir, index)
    world = {'frames': {index: row}, 'models': models}
    standing, point = FrameScene(world, index, hull=1), FrameScene(world, index, hull=0)
    def stand_at(x, y, mins):
        """The standing origin z of the lowest spot a standing player fits in at (x, y), searched from just above the
        threshold up (a start in the ground or under an eave is solid: stand_height gives its start height back)."""
        for lift in range(1, int(STAND_DROP) + 1, 4):
            top = mins[2] + HULL_FEET + lift
            hit = standing.trace((x, y, top), (x, y, -4096.0))
            if not hit:
                return None
            z = top + (-4096.0 - top) * hit['fraction']
            if z < top - 1e-3:
                # a fall well below the threshold (off a platform, a roof, a tower top): no spot at the door here;
                # a floor steeper than the walk's (Quake's 0.7 normal) slides the player off (the shrine steps)
                if z - HULL_FEET < mins[2] - BELOW_THRESHOLD or (hit.get('normal') or (0, 0, 1))[2] < WALKABLE:
                    return None
                return z
            if lift == 1 and not standing.trace((x, y, top), (x, y, top + 0.5)):
                return z        # resting on the ground already, not inside it
        return None

    def try_use(eye, mins, maxs, aim):
        """None when the use works from EYE looking at AIM, else why not (aw_scene.c door_hit and the wall trace)."""
        d = [aim[k] - eye[k] for k in range(3)]
        n = math.sqrt(sum(v * v for v in d)) or 1.0
        hit = door_hit(mins, maxs, eye, [v / n for v in d])
        if hit is None:
            return 'the use box is out of reach (%.0f units)' % n
        dist = math.dist(eye, hit)
        trace = point.trace(tuple(eye), tuple(hit)) if dist > 0 else None
        if trace and (1 - trace['fraction']) * dist > slack:
            return 'the use ray meets %s %.0f units before the door' % (
                'the ground' if str(trace['reference']).startswith('chunk') else 'reference %s' % trace['reference'],
                (1 - trace['fraction']) * dist)
        return None
    out = {}
    for ref, box, spot in doors:
        mins, maxs = box
        centre = [(mins[k] + maxs[k]) / 2 for k in range(3)]
        h = maxs[2] - mins[2]
        trapdoor = h < min(maxs[0] - mins[0], maxs[1] - mins[1])
        if trapdoor:
            # a trapdoor (lying flat, thinnest upright): the player stands at its top, beside it, and looks down at it
            mins = [mins[0], mins[1], maxs[2]]
        # where a player stands: on the line from the door out to the spot the game puts a player walking out of
        # the room, at the use reach and nearer; looking at the door's middle, its upper and its lower part
        u = [spot[0] - centre[0], spot[1] - centre[1]]
        n = math.hypot(*u) or 1.0
        u = [u[0] / n, u[1] / n]
        # and straight out from the door's face (the box's thin side, toward that spot)
        thin = 0 if maxs[0] - mins[0] < maxs[1] - mins[1] else 1
        face = [0.0, 0.0]
        face[thin] = 1.0 if u[thin] >= 0 else -1.0
        result, first_why = None, None
        # straight out from the face, and 12 units to either side of that line (a step, a post or a slope at the
        # middle leaves room beside it), then toward the way-out arrival
        side = [-face[1], face[0]]
        spots = [(face[0] * d + side[0] * s, face[1] * d + side[1] * s) for d in (REACH, 28.0, 16.0)
                 for s in (0.0, 12.0, -12.0)] + [(u[0] * d, u[1] * d) for d in (REACH, 28.0, 16.0)]
        if trapdoor:
            # on the trapdoor itself (a tower top may hold nothing else), then beside it on every side
            half = max(maxs[0] - mins[0], maxs[1] - mins[1]) / 2
            sides = ([1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0])
            spots = [(0.0, 0.0)] + [(s[0] * half / 2, s[1] * half / 2) for s in sides] + \
                [(s[0] * (half + d), s[1] * (half + d)) for d in (10.0, 20.0) for s in sides] + spots
        for dx, dy in spots:
            x, y = centre[0] + dx, centre[1] + dy
            origin = stand_at(x, y, mins)
            if origin is None:
                first_why = first_why or ('no standing spot at the door within %d units above its threshold'
                                          % STAND_DROP)
                continue
            eye = [x, y, origin + VIEW]
            ground = round(origin - HULL_FEET - mins[2], 1)
            for z in (centre[2], mins[2] + .75 * h, mins[2] + .25 * h):
                why = try_use(eye, mins, maxs, [centre[0], centre[1], z])
                if why is None:
                    result = {'reach': 'yes', 'eye': [round(v, 1) for v in eye], 'ground_over_threshold': ground}
                    break
                first_why = first_why or why
            if result:
                break
        result = result or {'reach': 'no', 'why': first_why}
        out[ref] = result
    return out


def use_slack(engine_src):
    """aw_scene.c DOOR_USE_SLACK: how near before the use box a surface may lie (1.0 before it was named)."""
    m = re.search(r'#define DOOR_USE_SLACK ([0-9.]+)f', (Path(engine_src) / 'aw_scene.c').read_text(
        encoding='utf-8', errors='replace'))
    return float(m.group(1)) if m else 1.0


def reach_check(entries, world_dir, id1, jobs=None, slack=1.0):
    """{reference: reach result} for the region-frame doors of ENTRIES (their job lines give the standing spot and
    the use box comes from the audit row), one task per CHIM region frame, on every core. Town doors are not traced
    here (their frame maps are the towns' own)."""
    from build_jobs import resolve_jobs
    from build_parallel import in_order_map
    from chim import format as F
    from chim import reach, placed, placement_light, terc, thgt  # noqa: F401
    from chim.frame_map import region_frame_rows
    from chim.validate import _world_file
    world_dir = Path(world_dir)
    rows = region_frame_rows(id1, world_dir)
    _, files, _, _ = F.read_index(_world_file(world_dir / 'chim', 'world.cwi'))
    by_cell = {}
    for i, f in enumerate(f for f in files if f['kind'] == b'FRAM'):
        by_cell.setdefault(tuple(f['cell']), i)
    tasks = {}
    for e in entries:
        if e.get('holder_kind') != 'region' or not e.get('job') or not e.get('box') or e['holder'] not in rows:
            continue
        index = by_cell.get(tuple(rows[e['holder']]['cells'][0]))
        if index is None:
            continue
        d = e['job'].split()
        tasks.setdefault(index, []).append((e['reference'], e['box'], (float(d[3]), float(d[4]))))
    items = [(str(world_dir), index, doors, slack) for index, doors in sorted(tasks.items())]
    out = {}
    for part in in_order_map(_reach_unit, items, min(resolve_jobs(jobs), max(1, len(items)))):
        out.update(part)
    return out


def check(rows, id1, engine_src, directory, names, jobs=None, scene_source=None, world_id1=(), world_dir=None):
    """The report: one entry per audit row, the counts, the regions."""
    import door_audit
    from build_jobs import resolve_jobs
    banks = {}

    def bank(name):
        if name not in banks:
            path = Path(id1) / ('doors-%s.txt' % name)
            banks[name] = door_audit.parse_bank(path.read_text(encoding='cp1252'), names) if path.is_file() else None
        return banks[name]
    planned = job_lines(rows, bank, directory)
    from build_scratch import scratch_dir
    with scratch_dir(prefix='door-engine-check-', keep_on_failure=False) as tmp:
        exe = compile_harness(engine_src, tmp, scene_source)
        results = run_harness(exe, id1, [l for _, l, _ in planned if l], resolve_jobs(jobs), tmp, world_id1)
    entries = []
    for row, line, why in planned:
        entry = {k: row.get(k) for k in ('reference', 'id', 'cell', 'region', 'destination_cell', 'holder',
                                         'holder_kind', 'locked', 'lock_level', 'key')}
        entry['target'] = (row.get('bank') or {}).get('target')
        entry['placed'] = row['checks'].get('placed')
        # a frame or town of this image holds the door (a partial-area image holds only its own)
        entry['held'] = 'yes' if row['checks'].get('holder') == 'yes' else 'no'
        entry['job'] = line
        entry['box'] = (row.get('bank') or {}).get('box')
        result = results.get(row['reference']) if line else None
        if result is None:
            entry.update(usable='no', both_ways='no', checks={}, reasons=[why or 'the harness gave no result'])
        else:
            exits = [l for l in (bank(entry['target']) or {}).get('links', [])
                     if l['reference'] == row.get('exit_reference')] if entry['target'] else []
            checks, reasons = judge(row, result, exits[0]['target'] if exits else None)
            if entry['placed'] == 'no':
                reasons.append('its CHIM frame does not place the door model (the audit)')
            usable = all(checks[k] == 'yes' for k in ('crossing', 'in_frame_at_door', 'prompt', 'enters', 'activate'))
            entry.update(result=result, checks=checks, reasons=reasons, usable='yes' if usable else 'no',
                         both_ways='yes' if usable and checks['way_back'] in ('yes', 'not checked') else 'no')
        entries.append(entry)
    # the wall between the player and the door, with the CHIM world's own collision (region frames)
    reached = reach_check(entries, world_dir, id1, jobs, use_slack(engine_src)) if world_dir else {}
    for e in entries:
        r = reached.get(e['reference'])
        if 'checks' not in e or not e['checks']:
            continue
        e['checks']['reach'] = 'not checked' if r is None else r['reach']
        if r is not None:
            e['reach'] = r
            if r['reach'] == 'no':
                e['reasons'].append(r['why'])
        e['reachable'] = 'yes' if e['usable'] == 'yes' and e['checks']['reach'] in ('yes', 'not checked') else 'no'
    counts = {'doors': len(entries), 'held': sum(e['held'] == 'yes' for e in entries),
              'reachable': sum(e.get('reachable') == 'yes' for e in entries),
              'reach_traced': sum(e.get('checks', {}).get('reach') in ('yes', 'no') for e in entries),
              'usable_after_crossing': sum(e['usable'] == 'yes' for e in entries),
              'both_ways': sum(e['both_ways'] == 'yes' for e in entries),
              'locked': sum(e['locked'] == 'yes' for e in entries),
              'placed': sum(e['placed'] == 'yes' for e in entries),
              'region_doors': sum(e['holder_kind'] == 'region' for e in entries)}
    for key in ('crossing', 'in_frame_at_door', 'prompt', 'enters', 'activate', 'way_back', 'reach'):
        counts['check ' + key] = sum(e['checks'].get(key) == 'yes' for e in entries)
    regions = {}
    for e in entries:
        r = regions.setdefault(e['region'] or '(no region)', {'doors': 0, 'usable': 0, 'both_ways': 0, 'locked': 0})
        r['doors'] += 1
        r['usable'] += e['usable'] == 'yes'
        r['both_ways'] += e['both_ways'] == 'yes'
        r['locked'] += e['locked'] == 'yes'
    return {'format': FORMAT, 'counts': counts, 'regions': dict(sorted(regions.items())), 'entries': entries,
            'scene_source': str(scene_source) if scene_source else None}


def baseline_problem(report, baseline):
    """None, or why REPORT falls below BASELINE (aw-door-check-baseline-1: doors, usable_after_crossing, both_ways):
    an image with as many entrances as the baseline may not use fewer of them (DOOR-ENTRANCE-AUDIT-51). An image with
    fewer entrances held by its frames and towns (a partial-area build) is not compared."""
    if not baseline or baseline.get('format') != BASELINE_FORMAT:
        return None
    c = report['counts']
    if c.get('held', c['doors']) < baseline['doors']:
        return None
    # reachable: counted only where the wall was traced (an image with its CHIM world)
    keys = ('usable_after_crossing', 'both_ways') + (('reachable',) if c.get('reach_traced') else ())
    worse = ['%s %d < %d' % (k, c[k], baseline[k]) for k in keys if k in baseline and c[k] < baseline[k]]
    return ('the door engine check fell below the baseline (%s; config/door-check-baseline.json)' % ', '.join(worse)
            if worse else None)


def write_outputs(report, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'door-engine-check.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                                newline='\n')
    c = report['counts']
    lines = ['# Door engine check', '',
             'Exterior entrances: %d (%d in region frames). Usable after walking into their frame (prompt, use key '
             'and Activate lead into the room): %d. Also the way back out: %d. Locked in the original: %d. The CHIM '
             'frame places the door model: %d.' % (c['doors'], c['region_doors'], c['usable_after_crossing'],
                                                  c['both_ways'], c['locked'], c['placed']), '',
             'With the wall between the player and the door traced in the CHIM world\'s own collision (the %d '
             'region-frame doors; town doors not traced): %d usable. A player stands in front of the door (straight '
             'out from its face, and on the way to where the game puts a player walking out of the room; at the use '
             'reach and nearer) and looks at its middle, upper and lower part; the engine refuses the use when a '
             'surface lies more than the doorway slack (aw_scene.c DOOR_USE_SLACK) before the door\'s use box.'
             % (c['reach_traced'], c['reachable']), '',
             '| Check | yes |', '| --- | --- |']
    lines += ['| %s | %d |' % (k, c['check ' + k]) for k in ('crossing', 'in_frame_at_door', 'prompt', 'enters',
                                                              'activate', 'way_back', 'reach')]
    lines += ['', '## The wall in the way (region frames)', '']
    lines += ['- %d %s (cell %s) -> %s: %s' % (e['reference'], e['id'], ','.join(map(str, e['cell'] or [])),
                                               e['destination_cell'], e['reach']['why'])
              for e in report['entries'] if e.get('checks', {}).get('reach') == 'no'] or ['None.']
    lines += ['', '## Per region', '', '| Region | doors | usable | both ways | locked |', '| --- | --- | --- | --- | --- |']
    lines += ['| %s | %d | %d | %d | %d |' % (n, r['doors'], r['usable'], r['both_ways'], r['locked'])
              for n, r in report['regions'].items()]
    lines += ['', '## Not usable both ways', '']
    bad = [e for e in report['entries'] if e['both_ways'] != 'yes']
    lines += ['- %d %s (cell %s) -> %s: %s' % (e['reference'], e['id'], ','.join(map(str, e['cell'] or [])),
                                               e['destination_cell'], '; '.join(e['reasons'])) for e in bad] or ['None.']
    (out / 'door-engine-check.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def run(build=None, id1=None, engine_src=None, audit_rows=None, data_files=None, out=None, baseline=None, jobs=None,
        scene_source=None, world_doors=None, chim_world=None, world_id1=()):
    """The check over one image; returns (report, problem or None)."""
    import door_audit
    from chim.frame_map import world_directory
    id1 = Path(id1 or Path(build) / 'image/boot/id1')
    engine_src = Path(engine_src or Path(build) / 'engine/runtime/src')
    chim_world = chim_world or (Path(build) / 'chim-world' if build else None)
    if audit_rows is None:
        from mwad.interior import original_doors
        from mwad.paths import child_ci
        doors = original_doors(child_ci(data_files, 'Morrowind.esm').read_bytes())
        world_rows = json.loads(Path(world_doors or Path(build) / 'image/world-doors.json')
                                .read_text(encoding='utf-8'))['rows']
        image = door_audit.Image(id1, engine_src, chim_world, jobs)
        audit_rows = door_audit.audit(doors, world_rows, image, door_audit.regions_by_cell(data_files, jobs))['rows']
    names = door_audit.engine_map_names((engine_src / 'aw_maps.h').read_text(encoding='utf-8', errors='replace'),
                                        (engine_src / 'aw_town_table.h').read_text(encoding='utf-8', errors='replace'))
    world = chim_world if chim_world and (Path(chim_world) / 'chim' / 'world.cwi').is_file() else None
    report = check(audit_rows, id1, engine_src, world_directory(id1), names, jobs, scene_source, world_id1, world)
    problem = baseline_problem(report, json.loads(Path(baseline).read_text(encoding='utf-8')) if baseline else None)
    report['baseline_problem'] = problem
    if out:
        write_outputs(report, out)
    return report, problem


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--build', type=Path)
    ap.add_argument('--id1', type=Path)
    ap.add_argument('--engine-src', type=Path)
    ap.add_argument('--world-id1', type=Path, action='append', default=[],
                    help="a world volume's id1 (the files packed out of the boot disk's id1, e.g. the region frame maps)")
    ap.add_argument('--chim-world', type=Path, help='the CHIM world (default BUILD/chim-world): the wall check')
    ap.add_argument('--audit', type=Path, help='door-audit.json of tools/door_audit.py (else --data-files runs it)')
    ap.add_argument('--data-files', type=Path)
    ap.add_argument('--scene-source', type=Path, help='another aw_scene.c (an earlier release) for a before count')
    ap.add_argument('--baseline', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--jobs', type=int)
    a = ap.parse_args(argv)
    if not a.build and not (a.id1 and a.engine_src):
        ap.error('--build, or --id1 and --engine-src')
    if not a.audit and not a.data_files:
        ap.error('--audit or --data-files')
    rows = json.loads(a.audit.read_text(encoding='utf-8'))['rows'] if a.audit else None
    report, problem = run(a.build, a.id1, a.engine_src, rows, a.data_files, a.out, a.baseline, a.jobs, a.scene_source,
                          chim_world=a.chim_world, world_id1=a.world_id1)
    c = report['counts']
    print('door engine check: %d exterior entrances; usable after walking in %d, both ways %d; with the wall traced '
          '(%d region doors) %d; locked %d; placed %d'
          % (c['doors'], c['usable_after_crossing'], c['both_ways'], c['reach_traced'], c['reachable'], c['locked'],
             c['placed']))
    if problem:
        print('door engine check: ' + problem)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
