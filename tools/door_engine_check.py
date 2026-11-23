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
count: the count only goes up. With --known (config/door-check-known.json) a whole-world image also fails when an
exterior entrance the wall check cannot reach is not listed there with its reason and class
(DOOR-USE-COLLISION-FILLED-53): every entrance is reachable or a known, registered case. With --data-files the
masters' script stages are read (tools/script_stages.py): a door no player reaches is traced again without the
placements a script hides while it is shown (DOOR-USE-COLLISION-EXPANSIONS-68).
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
                'aw_excluded.c', 'aw_format.c', 'aw_harvest_proxy.c', 'aw_travel_rules.c', 'aw_activate_rules.c',
                'aw_loaderr.c')


def _inside(core, point, margin=0.0):
    return core[0] - margin <= point[0] <= core[2] + margin and core[1] - margin <= point[1] <= core[3] + margin


def door_cores(core):
    """The cores (x0, y0, x1, y1 in the door frame's coordinates) a player may stand in to use a door: CORE is one core
    or a sequence of them (the door frame's own and those of the frames whose bank holds a border copy of the door,
    copy_cores); () for none."""
    if not core:
        return ()
    if isinstance(core[0], (int, float)):
        return (tuple(core),)
    return tuple(tuple(c) for c in core if c)


def copy_cores(reference, holder, frames, cores, bank):
    """DOOR-USE-ACROSS-FRAME-EDGE-68: the cores, in HOLDER's coordinates, of the neighbouring frames whose door bank
    holds the door REFERENCE too (a border copy, tools/world_doors.py border_copies: a door within reach of its frame's
    core edge is written into the bank of the frame across it). The engine reads the bank of the frame the player
    stands in (aw_scene.c read_links_for(door_scene())), so such a door is used from that frame's core as well: in play
    on the v0.0.68-dev8 image Mournhold's ladder down to Bamz-Amschend (mh0005, copied into mh0004) entered from its
    walk-out arrival in mh0004, 48.8 units from it. FRAMES {name: origin}, CORES {name: core}, BANK(name) the parsed
    bank or None."""
    if holder not in frames:
        return []
    out = []
    ho = frames[holder]
    for name, origin in frames.items():
        if name == holder or name not in cores or abs(origin[0] - ho[0]) > 3072 or abs(origin[1] - ho[1]) > 3072:
            continue
        links = (bank(name) or {}).get('links', [])
        if any(l.get('reference') == reference for l in links):
            dx, dy = origin[0] - ho[0], origin[1] - ho[1]
            c = cores[name]
            out.append((c[0] + dx, c[1] + dy, c[2] + dx, c[3] + dy))
    return out


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
    if holder not in frames:
        return []           # a frame of another world (job_lines names it): no walk in this directory
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


# A door whose region frame is in none of the directories this check walks: Vvardenfell's (world/regions.awr) and the
# rows files of the lands installed as stores of their own (Solstheim's slNNNN, Mournhold's mhNNNN:
# door_audit.full_directory, tools/chim/layer_stores.py). The image step runs the check after those stores are
# installed, so their frames are walked like any other; a door whose frame has no row (a rows file missing from the
# id1 the check was given) is listed with this reason and never walked (DOOR-CHECK-MODULE-FRAME-MAPS-67: the check
# once stopped an image's last step on the first such map, then listed all of them as not walked).
OWN_WORLD = ('its frame %s is not in the directories this check walks (a frame of a world of its own whose rows '
             'file is not in this image): not walked here')


def job_lines(rows, bank, directory):
    """[(row, job line or None, why not)] for the audit ROWS; BANK(map) -> parse_bank result or None."""
    out = []
    walked = {name for name, _origin, _core in directory}
    for row in rows:
        if 'bank' not in row or not row.get('holder'):
            out.append((row, None, 'no bank row for the door (the audit: %s)' % '; '.join(row.get('problems') or [])))
            continue
        holder, box, target = row['holder'], row['bank']['box'], row['bank']['target']
        if row.get('holder_kind') == 'region' and holder not in walked:
            out.append((row, None, OWN_WORLD % holder))
            continue
        room_bank = bank(target) if target and target != '-' else None
        exits = [l for l in (room_bank or {}).get('links', []) if l['reference'] == row.get('exit_reference')]
        stand = list(exits[0]['arrival']) if exits and exits[0]['target'] == holder else \
            [box[0][0] - REACH, (box[0][1] + box[1][1]) / 2, box[0][2]]
        eye, yaw, pitch = aim(stand, box)
        line = 'D %d %s %s %.2f %.2f' % (row['reference'], holder, ' '.join('%.2f' % v for v in eye), yaw, pitch)
        if row.get('holder_kind') == 'region':
            # a frame with no frame across any side of its core (a district that stands alone: Mournhold's Royal
            # Palace courtyard) has no walk in: the player arrives in it by a door or a teleport, so the frame itself
            # runs at the door, as a town's does (the line then has no W; DOOR-CHECK-MODULE-FRAME-MAPS-67)
            for running, start, cross in neighbour_walks(directory, holder, eye):
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
CONTENTS_WATER = -3     # bspfile.h: the chunk terrain's water leaf (chim_thgt.c), as SV_PointContents reads it
ARRIVAL_LIFT = 2 * HULL_FEET    # an arrival whose start is in a floor or a step: lifted up to a hull's height
# From a spot the player is put at (the walk-out arrival and the way from it), the use must land within the original's
# activation reach, iMaxActivateDist 192 units (48 map units; OpenMW mwworld/worldimp.cpp getMaxActivationDistance),
# short of the engine's 56: in play on the v0.0.68-dev8 image the walk-out spots that worked used their doors from 0 to
# 44 units, and Rimhull's trapdoor, 54 units from its walk-out arrival, showed no prompt there.
WALK_OUT_REACH = 48.0
# The kinds of entrance the check judges beyond a spot at the threshold (DOOR-USE-COLLISION-EXPANSIONS-68): each stays
# on only once play has shown its doors used. 'walk_out' (the room exit's arrival and the way from it: shown on the
# v0.0.68-dev8 image, six entrances of Solstheim entered from it); 'swim' (a door under water used by a swimming
# player, DOOR-CHECK-NO-SWIM-CASE-68: shown on the v0.0.68-dev8 image with the gated engine of 4974f47ac, Stahlman's
# Gorge, the Caves of Fjalding and the Unmarked Shipwreck's trapdoor entered by swimming down to them); 'stages' (the
# placements a script hides while the door is shown left out) and 'doorway' (the other doors of a doorway the scripts
# switch between switched off, DOOR-CHECK-DOORWAY-STAGES-68): kept as selectable methods until play shows them;
# AMIWIND_DOOR_CHECK_RULES=walk_out,swim,stages,doorway selects them for an A/B run (an empty value: the check before
# these rules).
RULES = ('walk_out', 'swim')
ALL_RULES = ('walk_out', 'swim', 'stages', 'doorway')


def active_rules(rules=None):
    """The rules the check judges by: RULES, or the environment's AMIWIND_DOOR_CHECK_RULES, or RULES given."""
    if rules is None:
        value = os.environ.get('AMIWIND_DOOR_CHECK_RULES')
        rules = RULES if value is None else tuple(r.strip() for r in value.split(',') if r.strip())
    bad = [r for r in rules if r not in ALL_RULES]
    if bad:
        raise ValueError('door check: unknown rules %s (known: %s)' % (', '.join(bad), ', '.join(ALL_RULES)))
    return tuple(rules)


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


def _leave_out(row, refs):
    """The frame row (path, frame, chunks) with the placements of source references REFS taken out of every chunk
    (a moment of the door's stage: placements a script hides while the door is shown, tools/script_stages.py)."""
    from chim.cut import source_ref
    path, frame, chunks = row
    return (path, frame, [dict(c, owned=[r for r in c['owned'] if source_ref(r['ref']) not in refs])
                          for c in chunks])


def _reach_unit(task):
    """Worker: the doors of one CHIM region frame against the frame's own collision (chim.collision.FrameScene: its
    chunk terrain and the hulls of everything it places, as the engine collides them): where a player stands at the
    door (dropped from just above the threshold), the eye there, and the engine's wall trace from the eye to the
    use box (aw_scene.c aimed_door: the use is refused when a surface lies more than DOOR_USE_SLACK before the box).
    A door is (reference, box, spot[, arrival[, (door stage, switched)[, core]]]); the task (world, frame, doors,
    slack[, rules]) names the rules judged by (active_rules; the four RULES kinds). 'walk_out': ARRIVAL, the spot the
    game puts a player walking out of the room, is where the player stands when no spot at the threshold serves (a
    door set into a slope, whose box reaches deep into the ground in front of it), it and the way from it inside the
    frame's CORE (x0, y0, x1, y1: the engine reads the door bank of the frame the player stands in) and the use within
    WALK_OUT_REACH; 'swim': a door under water is used by a player swimming at it; 'stages' (with the stages,
    tools/script_stages.py: the door's own, SWITCHED {source reference: stage}): a door no player reaches is tried
    again without the placements near it a script hides while the door is shown."""
    world_dir, index, doors, slack = task[:4]
    rules = task[4] if len(task) > 4 else ALL_RULES
    swim = 'swim' in rules
    from chim import reach, placed, placement_light, terc, thgt  # noqa: F401 (world formats 0.8 .. 0.13)
    from chim.collision import FrameScene, stand_height
    from chim.validate import load_frame
    row, models = load_frame(world_dir, index)
    scenes = {}

    def scenes_for(leave):
        """The standing and point scenes of the frame, without the placements LEAVE (a door's stage)."""
        key = frozenset(leave or ())
        if key not in scenes:
            for old in [k for k in scenes if k]:
                scenes.pop(old)         # the whole frame's scenes and the latest moment's: never more
            world = {'frames': {index: _leave_out(row, key) if key else row}, 'models': models}
            scenes[key] = (FrameScene(world, index, hull=1), FrameScene(world, index, hull=0))
        return scenes[key]
    standing = point = None

    def free(x, y, z):
        """A standing player fits with its origin at (x, y, z) (no solid at the start)."""
        hit = standing.trace((x, y, z), (x, y, z + 0.5))
        return not hit or hit['fraction'] > 0

    def floats(x, y, z):
        """A player with its origin at (x, y, z) swims there: the origin is in the terrain's water (sv_phys.c
        SV_CheckWater: waterlevel 2 and over; aw_walk.c AW_WalkPlayer adds no gravity while swimming, and an idle
        swimmer does not sink, sv_user.c SV_WaterMove), so the player stays where it swims to (OpenMW: an actor swims
        once the water stands over fSwimHeightScale of its height, mwworld/worldimp.cpp isSwimming). Only with the
        rule 'swim'."""
        return swim and point.contents((x, y, z)) == CONTENTS_WATER and free(x, y, z)

    def stand_at(x, y, mins):
        """The standing origin z of the lowest spot a standing player fits in at (x, y), searched from just above the
        threshold up (a start in the ground or under an eave is solid: stand_height gives its start height back); a
        start in the water is where a swimming player stays (DOOR-CHECK-NO-SWIM-CASE-68: an entrance under water, the
        player swims to it and uses it from the water)."""
        for lift in range(1, int(STAND_DROP) + 1, 4):
            top = mins[2] + HULL_FEET + lift
            if floats(x, y, top):
                return top
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

    def stand_under(x, y, z, lowest):
        """The standing origin z where a player put with its origin at (x, y, Z) comes to rest: the floor under it
        (the engine drops a player walking out of a room at the arrival onto it), a start in a floor or a step lifted
        up to ARRIVAL_LIFT; in the water it swims there. None when it falls under LOWEST or onto a slope it slides
        off, or nothing holds it."""
        for lift in range(0, int(ARRIVAL_LIFT) + 1, 4):
            top = z + lift
            if not free(x, y, top):
                continue
            if floats(x, y, top):
                return top
            hit = standing.trace((x, y, top), (x, y, -4096.0))
            if not hit:
                return None
            floor = top + (-4096.0 - top) * hit['fraction']
            if floor < lowest or (hit.get('normal') or (0, 0, 1))[2] < WALKABLE:
                return None
            return floor
        return None

    def try_use(eye, mins, maxs, aim, reach=56.0):
        """None when the use works from EYE looking at AIM, else why not (aw_scene.c door_hit and the wall trace)."""
        d = [aim[k] - eye[k] for k in range(3)]
        n = math.sqrt(sum(v * v for v in d)) or 1.0
        hit = door_hit(mins, maxs, eye, [v / n for v in d], reach)
        if hit is None:
            return 'the use box is out of reach (%.0f units)' % n
        dist = math.dist(eye, hit)
        try:
            trace = point.trace(tuple(eye), tuple(hit)) if dist > 0 else None
        except ValueError as err:
            # the offline tracer's visit guard (audit_walkability.Scene.trace) on a deep collision tree: not judged
            # usable from this eye, never a stop of the whole check
            return 'the use ray could not be traced (%s)' % err
        if trace and (1 - trace['fraction']) * dist > slack:
            return 'the use ray meets %s %.0f units before the door' % (
                'the ground' if str(trace['reference']).startswith('chunk') else 'reference %s' % trace['reference'],
                (1 - trace['fraction']) * dist)
        return None

    def swim_to(x, y, low, high, aim_z):
        """The origin z nearest AIM_Z between LOW and HIGH where a player swims at (x, y), or None."""
        steps = int((high - low) // 4) + 1
        for z in sorted((low + 4 * k for k in range(steps)), key=lambda z: abs(z - aim_z)):
            if floats(x, y, z):
                return z
        return None

    def attempt(door, leave):
        """(result or None, {'first': why, 'walk_out': why from the walk-out arrival}) of one door, with the
        placements of source references LEAVE left out of the frame."""
        nonlocal standing, point
        ref, (mins, maxs), spot = door[:3]
        arrival = door[3] if len(door) > 3 and 'walk_out' in rules else None
        cores = door_cores(door[5] if len(door) > 5 else None)
        standing, point = scenes_for(leave)
        centre = [(mins[k] + maxs[k]) / 2 for k in range(3)]
        h = maxs[2] - mins[2]
        trapdoor = h < min(maxs[0] - mins[0], maxs[1] - mins[1])
        # the use box is the engine's (aw_scene.c door_hit reads the bank's box as it is); a trapdoor (lying flat,
        # thinnest upright) is stood at from its top: the player stands on it or beside it and looks down at it
        floor = [mins[0], mins[1], maxs[2] if trapdoor else mins[2]]
        # where a player stands: on the line from the door out to the spot the game puts a player walking out of
        # the room, at the use reach and nearer; looking at the door's middle, its upper and its lower part
        u = [spot[0] - centre[0], spot[1] - centre[1]]
        n = math.hypot(*u) or 1.0
        u = [u[0] / n, u[1] / n]
        # and straight out from the door's face (the box's thin side, toward that spot)
        thin = 0 if maxs[0] - mins[0] < maxs[1] - mins[1] else 1
        face = [0.0, 0.0]
        face[thin] = 1.0 if u[thin] >= 0 else -1.0
        why = {'first': None, 'walk_out': None}
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

        def use_from(x, y, origin, how, walk_out=False):
            """The result when a player at origin (x, y, ORIGIN) uses the door, else None (the first why kept); from a
            walk-out spot, inside the frame's core and within WALK_OUT_REACH."""
            eye = [x, y, origin + VIEW]
            if walk_out and cores and not any(_inside(c, eye) for c in cores):
                why['walk_out'] = why['walk_out'] or ('the spot lies outside the frame\'s core and the cores of the '
                                                      'frames whose bank holds the door (the engine reads the door '
                                                      'bank of the frame the player stands in)')
                return None
            for z in (centre[2], floor[2] + .75 * h, floor[2] + .25 * h):
                got = try_use(eye, mins, maxs, [centre[0], centre[1], z], WALK_OUT_REACH if walk_out else 56.0)
                if got is None:
                    res = {'reach': 'yes', 'eye': [round(v, 1) for v in eye],
                           'ground_over_threshold': round(origin - HULL_FEET - floor[2], 1)}
                    if floats(x, y, origin):
                        res['swimming'] = 'yes'
                    if how:
                        res['stands'] = how
                    return res
                why['first'] = why['first'] or got
                if walk_out:
                    why['walk_out'] = why['walk_out'] or got
            return None
        for dx, dy in spots:
            x, y = centre[0] + dx, centre[1] + dy
            origin = stand_at(x, y, floor)
            if origin is None:
                why['first'] = why['first'] or ('no standing spot at the door within %d units above its threshold'
                                                % STAND_DROP)
                continue
            result = use_from(x, y, origin, None)
            if result:
                return result, why
        way = []
        if arrival:
            # the spot the game puts a player walking out of the room, and the way from it to the door at the use
            # reach and nearer, each on the floor under the arrival's height: a door set into a slope (an ice cave's
            # dark door, a tomb door in a hillside: their boxes reach deep into the rock and the ground in front of
            # them, so no spot near the threshold is open) is used from the floor its own way out leads onto
            # (DOOR-USE-COLLISION-EXPANSIONS-68)
            a = [arrival[0] - centre[0], arrival[1] - centre[1]]
            d = math.hypot(*a) or 1.0
            way = [(centre[0] + a[0] / d * k, centre[1] + a[1] / d * k) for k in (REACH, 28.0, 16.0) if k < d]
            ground = stand_under(arrival[0], arrival[1], arrival[2], -4096.0)
            if ground is None:
                why['walk_out'] = 'the walk-out arrival has no floor a player stands on'
            else:
                result = use_from(arrival[0], arrival[1], ground, 'at the walk-out arrival', True)
                if result:
                    return result, why
                for x, y in way:
                    origin = stand_under(x, y, ground, ground - BELOW_THRESHOLD)
                    if origin is not None:
                        result = use_from(x, y, origin, 'on the way from the walk-out arrival', True)
                        if result:
                            return result, why
        # an entrance under water (Stahlman's Gorge under the Mortrag Glacier, the Caves of Fjalding at the bottom of
        # Lake Fjalding: the player swims down to them): wherever around the door the player swims, at the height
        # nearest the box's middle (DOOR-CHECK-NO-SWIM-CASE-68; the rule 'swim')
        low, high = floor[2] - BELOW_THRESHOLD + HULL_FEET, maxs[2] + HULL_FEET + VIEW
        for x, y in ([(centre[0] + dx, centre[1] + dy) for dx, dy in spots] + way +
                     ([(arrival[0], arrival[1])] if arrival else [])) if swim else ():
            origin = swim_to(x, y, low, high, centre[2] - VIEW)
            if origin is not None:
                result = use_from(x, y, origin, 'swimming at the door')
                if result:
                    return result, why
        return None, why

    def near(box, arrival, frame_refs):
        """The source references of the frame's placements within reach of the door box (and its walk-out arrival)."""
        lo = [box[0][k] - REACH - HULL_FEET * 2 for k in range(3)]
        hi = [box[1][k] + REACH + HULL_FEET * 2 for k in range(3)]
        if arrival:
            lo = [min(lo[k], arrival[k] - HULL_FEET * 4) for k in range(3)]
            hi = [max(hi[k], arrival[k] + HULL_FEET * 4) for k in range(3)]
        return {r for r, (a, b) in frame_refs.items() if all(a[k] <= hi[k] and b[k] >= lo[k] for k in range(3))}
    frame_refs = None
    out = {}
    for door in doors:
        result, why = attempt(door, ())
        if not result and len(door) > 4 and door[4] and 'stages' in rules:
            # the placements a script hides while this door is shown (a colony's earlier stages and the trees cleared
            # for its buildings, a quest's ice block or rock in front of an entrance): not in this door's way
            # (tools/script_stages.py; the engine hides a switched-off placement, OUTDOOR-DISABLE-NOT-HIDDEN-68)
            import script_stages
            from chim.cut import source_ref
            door_stage, switched = door[4]
            if frame_refs is None:
                frame_refs = {}
                for c in row[2]:
                    for r in c['owned']:
                        k, (a, b) = source_ref(r['ref']), r['box']
                        old = frame_refs.get(k)
                        frame_refs[k] = (a, b) if old is None else (
                            [min(old[0][i], a[i]) for i in range(3)], [max(old[1][i], b[i]) for i in range(3)])
            near_switched = {r: switched[r] for r in near(door[1], door[3] if len(door) > 3 else None, frame_refs)
                             if r in switched}
            for how, leave in script_stages.moments(door_stage, near_switched):
                result, _ = attempt(door, tuple(leave))
                if result:
                    result['stage'] = '%s: %s left out' % (how, ', '.join(map(str, leave)))
                    break
        if not result:
            result = {'reach': 'no', 'why': why['first']}
            if len(door) > 3 and door[3] and 'walk_out' in rules:
                result['walk_out'] = why['walk_out'] or 'no floor on the way from the walk-out arrival'
        out[door[0]] = result
    return out


def use_slack(engine_src):
    """aw_scene.c DOOR_USE_SLACK: how near before the use box a surface may lie (1.0 before it was named)."""
    m = re.search(r'#define DOOR_USE_SLACK ([0-9.]+)f', (Path(engine_src) / 'aw_scene.c').read_text(
        encoding='utf-8', errors='replace'))
    return float(m.group(1)) if m else 1.0


def layer_frame_cells(layers):
    """[(world folder, {frame map: cell})] of the stores of frames among the image step's --chim-layer-world
    STORE=WORLD values LAYERS (Solstheim's slNNNN, Mournhold's mhNNNN: the names chim.layer_stores.frame_holders
    gives their frames); [] for none."""
    if not layers:
        return []
    from chim.layer_stores import frame_holders, parse, store_kinds
    kinds = store_kinds()
    return [(Path(world), {name: cell for cell, (name, _origin) in frame_holders(['%s=%s' % (store, world)]).items()})
            for store, world in parse(layers) if kinds[store] == 'frames']


def reach_check(entries, world_dir, id1, jobs=None, slack=1.0, layers=None, stages=None, rules=None):
    """{reference: reach result} for the region-frame doors of ENTRIES (their job lines give the standing spot and
    the use box comes from the audit row), one task per CHIM region frame, on every core. Town doors are not traced
    here (their frame maps are the towns' own). LAYERS: the image step's --chim-layer-world values: a door of a frame
    of such a store is traced in that store's own world (DOOR-CHECK-MODULE-FRAME-MAPS-67). An entry's walk_out (the
    room exit's arrival in the door's frame) is where its player stands when no spot at the threshold serves. STAGES
    (tools/script_stages.Stages): the doors no player reaches are traced again, frame by frame, without the
    placements near them a script hides while the door is shown (the rule 'stages'). RULES: active_rules."""
    import door_audit
    rules = active_rules(rules)
    try:
        cores = {name: core for name, _origin, core in door_audit.full_directory(id1)}
    except (OSError, ValueError):
        cores = {}
    from build_jobs import resolve_jobs
    from build_parallel import in_order_map
    from chim import format as F
    from chim import reach, placed, placement_light, terc, thgt  # noqa: F401
    from chim.frame_map import region_frame_rows
    from chim.validate import _world_file
    worlds = []
    if world_dir:
        world_dir = Path(world_dir)
        worlds.append((world_dir, {name: tuple(row['cells'][0])
                                   for name, row in region_frame_rows(id1, world_dir).items()}))
    worlds += layer_frame_cells(layers)
    tasks = {}
    for folder, cells in worlds:
        if not any(e.get('holder') in cells for e in entries):
            continue
        _, files, _, _ = F.read_index(_world_file(folder / 'chim', 'world.cwi'))
        by_cell = {}
        for i, f in enumerate(f for f in files if f['kind'] == b'FRAM'):
            by_cell.setdefault(tuple(f['cell']), i)
        for e in entries:
            if e.get('holder_kind') != 'region' or not e.get('job') or not e.get('box') or e['holder'] not in cells:
                continue
            index = by_cell.get(tuple(cells[e['holder']]))
            if index is None:
                continue
            d = e['job'].split()
            own = cores.get(e['holder'])
            tasks.setdefault((str(folder), index), []).append(
                (e['reference'], e['box'], (float(d[3]), float(d[4])), e.get('walk_out'), None,
                 ([own] if own else []) + list(e.get('copy_cores') or []) if e.get('copy_cores') else own))
    items = [(folder, index, doors, slack, rules) for (folder, index), doors in sorted(tasks.items())]
    out = {}
    for part in in_order_map(_reach_unit, items, min(resolve_jobs(jobs), max(1, len(items)))):
        out.update(part)
    if stages is not None and 'stages' in rules:
        ids = {e['reference']: e.get('id') for e in entries}
        again = [(folder, index, [door[:4] + ((stages.of_record(ids[door[0]]), stages.switched), door[5])
                                  for door in doors if out.get(door[0], {}).get('reach') == 'no'], slack, rules)
                 for folder, index, doors, slack, rules in items]
        again = [item for item in again if item[2]]
        for part in in_order_map(_reach_unit, again, min(resolve_jobs(jobs), max(1, len(again)))):
            out.update({ref: r for ref, r in part.items() if r['reach'] == 'yes'})
    return out


def _overlap(a, b):
    """Two door bank rows' use boxes meet (one doorway)."""
    return all(a['mins'][k] <= b['maxs'][k] and b['mins'][k] <= a['maxs'][k] for k in range(3))


def doorway_off(link, links, stages):
    """The references of the load doors of LINKS (one bank's rows) that stand in the doorway of LINK (their use boxes
    meet) and that a script hides while LINK's door is shown: where two or three doors stand in one doorway and the
    scripts switch between them (Raven Rock's colony houses, one door per stage; a Skaal hut that becomes another
    house), the engine takes only the door that is on (DOOR-LOAD-DISABLED-STILL-USED-68), and the check runs the door
    with the others switched off. With STAGES (tools/script_stages.Stages): a door its own script never switches is in
    no such doorway; of two read stages of one global, the other door is off when it is hidden at the first value this
    door is shown at; a stage not read alternates with the door's (DOOR-USE-COLLISION-EXPANSIONS-68)."""
    import script_stages
    if not stages or link.get('reference') not in stages.switched:
        return []
    own = stages.switched[link['reference']]
    at = None
    if own not in (None, script_stages.ALWAYS) and own[1]:
        at = (own[0], min(own[1]))
    out = []
    for other in links:
        ref = other.get('reference')
        if not ref or ref == link['reference'] or ref not in stages.switched or not _overlap(link, other):
            continue
        stage = stages.switched[ref]
        if stage not in (None, script_stages.ALWAYS) and at and stage[0] == at[0]:
            if at[1] in stage[2]:
                out.append(ref)
        elif stage is not script_stages.ALWAYS:
            out.append(ref)
    return sorted(out)


def switched_off(row, bank, stages):
    """The job line's ' X r1,r2' (or ''): the load doors switched off while the audit ROW's door is shown, of its own
    doorway in its frame's bank and of its room exit's doorway in the room's bank (doorway_off)."""
    off = []
    target = (row.get('bank') or {}).get('target')
    for name, ref in ((row.get('holder'), row.get('reference')), (target, row.get('exit_reference'))):
        links = (bank(name) or {}).get('links', []) if name and name != '-' else []
        own = [l for l in links if l.get('reference') == ref]
        if own:
            off += doorway_off(own[0], links, stages)
    return ' X ' + ','.join(map(str, sorted(set(off)))) if off else ''


def walk_out_spot(exit_link, holder, origins):
    """Where the game puts a player walking out of the room through EXIT_LINK (its bank row: target map and arrival),
    in the coordinates of the door's frame HOLDER, or None when either is not a frame of ORIGINS ({frame: origin}). An
    arrival just across the frame's core edge is in the neighbouring frame's coordinates (Mournhold's ladder down to
    Bamz-Amschend: its way out arrives in the district frame beside the ladder's)."""
    target = exit_link.get('target')
    if target not in origins or holder not in origins:
        return None
    return [round(exit_link['arrival'][k] + origins[target][k] - origins[holder][k], 2) for k in range(3)]


def check(rows, id1, engine_src, directory, names, jobs=None, scene_source=None, world_id1=(), world_dir=None,
          layers=None, stages=None, rules=None):
    """The report: one entry per audit row, the counts, the regions. LAYERS, STAGES, RULES: reach_check; with the
    rule 'doorway' and STAGES, each door of a doorway the scripts switch between runs with the others off."""
    rules = active_rules(rules)
    import door_audit
    from build_jobs import resolve_jobs
    banks = {}

    def bank(name):
        if name not in banks:
            path = Path(id1) / ('doors-%s.txt' % name)
            banks[name] = door_audit.parse_bank(path.read_text(encoding='cp1252'), names) if path.is_file() else None
        return banks[name]
    planned = job_lines(rows, bank, directory)
    if stages is not None and 'doorway' in rules:
        planned = [(row, line + switched_off(row, bank, stages) if line else line, why) for row, line, why in planned]
    frames = {name: origin for name, origin, _core in directory}
    frame_cores = {name: core for name, _origin, core in directory}
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
            spot = walk_out_spot(exits[0], entry['holder'], frames) if exits else None
            if spot:
                entry['walk_out'] = spot
                copies = copy_cores(entry['reference'], entry['holder'], frames, frame_cores, bank)
                if copies:
                    entry['copy_cores'] = copies
            if entry['placed'] == 'no':
                reasons.append('its CHIM frame does not place the door model (the audit)')
            usable = all(checks[k] == 'yes' for k in ('crossing', 'in_frame_at_door', 'prompt', 'enters', 'activate'))
            entry.update(result=result, checks=checks, reasons=reasons, usable='yes' if usable else 'no',
                         both_ways='yes' if usable and checks['way_back'] in ('yes', 'not checked') else 'no')
        entries.append(entry)
    # the wall between the player and the door, with the CHIM world's own collision (region frames)
    reached = reach_check(entries, world_dir, id1, jobs, use_slack(engine_src), layers, stages,
                          rules) if world_dir else {}
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


KNOWN_FORMAT = 'aw-door-check-known-1'


def load_known(path):
    """{reference: reason} of config/door-check-known.json (aw-door-check-known-1): the region-frame entrances the
    converted collision still blocks for a named, measured reason (DOOR-USE-COLLISION-FILLED-53), each with its
    register class; refused when the file is not that format or an entry has no reason."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format') != KNOWN_FORMAT or not isinstance(data.get('entrances'), dict):
        raise ValueError('%s: format %s with an entrances table expected' % (path, KNOWN_FORMAT))
    out = {}
    for ref, row in data['entrances'].items():
        if not str(ref).isdigit() or not isinstance(row, dict) or not row.get('reason') or not row.get('class'):
            raise ValueError('%s: entrance %s needs a reference number, a reason and a class' % (path, ref))
        out[int(ref)] = row
    return out


def known_split(report, known):
    """The unreachable region-frame entrances of REPORT (the wall traced: checks reach 'no') against KNOWN
    ({reference: row}, load_known): {'known': [refs listed], 'new': [refs not listed], 'known_passing': [listed refs
    the check now reaches]}; refs sorted."""
    known = known or {}
    blocked = {e['reference'] for e in report['entries'] if e.get('checks', {}).get('reach') == 'no'}
    reached = {e['reference'] for e in report['entries'] if e.get('checks', {}).get('reach') == 'yes'}
    return {'known': sorted(blocked & set(known)), 'new': sorted(blocked - set(known)),
            'known_passing': sorted(reached & set(known))}


def known_problem(report, baseline, known):
    """None, or why a whole-world image (as many entrances held as the baseline's, the wall traced) leaves an
    exterior entrance unreachable that config/door-check-known.json does not list with its reason: every entrance of
    the original is either reachable or a known, registered case (DOOR-USE-COLLISION-FILLED-53). A partial-area image
    is not compared; a listed entrance the check now reaches is reported (known_passing), never a failure."""
    c = report['counts']
    if known is None or not baseline or c.get('held', c['doors']) < baseline.get('doors', 0) or \
            not c.get('reach_traced'):
        return None
    new = report.get('known_split', known_split(report, known))['new']
    if not new:
        return None
    by_ref = {e['reference']: e for e in report['entries']}
    return ('%d exterior entrances cannot be reached and are not on config/door-check-known.json: %s' % (
        len(new), '; '.join('%d %s -> %s (%s)' % (r, by_ref[r]['id'], by_ref[r]['destination_cell'],
                                                  by_ref[r]['reach']['why']) for r in new[:12])))


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
             'reach and nearer) and looks at its middle, upper and lower part; when no such spot serves, by the rules '
             'on in this run (%s; walk_out: at that walk-out arrival and on the way from it; swim: swimming around a '
             'door under water; stages: without the placements a script hides while the door is shown; doorway: the '
             'other doors of a doorway the scripts switch between switched off); the engine refuses the use when a '
             'surface lies more than the doorway slack (aw_scene.c DOOR_USE_SLACK) before the door\'s use box.'
             % (c['reach_traced'], c['reachable'], ', '.join(report.get('rules') or ()) or 'none'), '',
             '| Check | yes |', '| --- | --- |']
    lines += ['| %s | %d |' % (k, c['check ' + k]) for k in ('crossing', 'in_frame_at_door', 'prompt', 'enters',
                                                              'activate', 'way_back', 'reach')]
    lines += ['', '## The wall in the way (region frames)', '']
    split = report.get('known_split') or {}
    known = set(split.get('known', ()))
    lines += ['- %d %s (cell %s) -> %s: %s%s' % (e['reference'], e['id'], ','.join(map(str, e['cell'] or [])),
                                                 e['destination_cell'], e['reach']['why'],
                                                 ' (known: config/door-check-known.json)' if e['reference'] in known
                                                 else '')
              for e in report['entries'] if e.get('checks', {}).get('reach') == 'no'] or ['None.']
    if split.get('known_passing'):
        lines += ['', 'Listed in config/door-check-known.json but reached now (take them off the list): %s.'
                  % ', '.join(map(str, split['known_passing']))]
    lines += ['', '## Per region', '', '| Region | doors | usable | both ways | locked |', '| --- | --- | --- | --- | --- |']
    lines += ['| %s | %d | %d | %d | %d |' % (n, r['doors'], r['usable'], r['both_ways'], r['locked'])
              for n, r in report['regions'].items()]
    lines += ['', '## Not usable both ways', '']
    bad = [e for e in report['entries'] if e['both_ways'] != 'yes']
    lines += ['- %d %s (cell %s) -> %s: %s' % (e['reference'], e['id'], ','.join(map(str, e['cell'] or [])),
                                               e['destination_cell'], '; '.join(e['reasons'])) for e in bad] or ['None.']
    (out / 'door-engine-check.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def run(build=None, id1=None, engine_src=None, audit_rows=None, data_files=None, out=None, baseline=None, jobs=None,
        scene_source=None, world_doors=None, chim_world=None, world_id1=(), known=None, layers=None, stages=None,
        rules=None):
    """The check over one image; returns (report, problem or None). known: config/door-check-known.json (load_known):
    a whole-world image then fails on an unreachable entrance it does not list. layers: the image step's
    --chim-layer-world STORE=WORLD values (the stores of frames the image installs beside the base world). stages:
    tools/script_stages.Stages of the masters (given data_files and no stages, read from them): a door no player
    reaches is traced again without the placements a script hides while it is shown (the rule 'stages'). rules:
    active_rules (default RULES: the kinds play has shown)."""
    import door_audit
    id1 = Path(id1 or Path(build) / 'image/boot/id1')
    engine_src = Path(engine_src or Path(build) / 'engine/runtime/src')
    chim_world = chim_world or (Path(build) / 'chim-world' if build else None)
    if audit_rows is None:
        from mwad.interior import original_doors
        from mwad.paths import child_ci
        from mwad.masters import master_path
        doors = original_doors(master_path(data_files).read_bytes())
        world_rows = json.loads(Path(world_doors or Path(build) / 'image/world-doors.json')
                                .read_text(encoding='utf-8'))['rows']
        image = door_audit.Image(id1, engine_src, chim_world, jobs, layer_worlds=door_audit.layer_frame_worlds(layers))
        audit_rows = door_audit.audit(doors, world_rows, image, door_audit.regions_by_cell(data_files, jobs))['rows']
    names = door_audit.engine_map_names((engine_src / 'aw_maps.h').read_text(encoding='utf-8', errors='replace'),
                                        (engine_src / 'aw_town_table.h').read_text(encoding='utf-8', errors='replace'))
    world = chim_world if chim_world and (Path(chim_world) / 'chim' / 'world.cwi').is_file() else None
    if stages is None and data_files:
        import script_stages
        stages = script_stages.read(data_files)
    rules = active_rules(rules)
    report = check(audit_rows, id1, engine_src, door_audit.full_directory(id1), names, jobs, scene_source, world_id1,
                   world, layers, stages, rules)
    report['rules'] = list(rules)
    base = json.loads(Path(baseline).read_text(encoding='utf-8')) if baseline else None
    problem = baseline_problem(report, base)
    report['baseline_problem'] = problem
    known_rows = load_known(known) if known else None
    report['known_split'] = known_split(report, known_rows)
    report['known_problem'] = known_problem(report, base, known_rows)
    problem = '; '.join(p for p in (problem, report['known_problem']) if p) or None
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
    ap.add_argument('--known', type=Path, help='config/door-check-known.json: the entrances still blocked for a '
                                               'named reason (a whole-world image fails on any other)')
    ap.add_argument('--layer-world', action='append', default=[], metavar='STORE=WORLD',
                    help="a store of frames the image installs beside the base world (the image step's "
                         '--chim-layer-world values): its doors are traced in its own world')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--jobs', type=int)
    a = ap.parse_args(argv)
    if not a.build and not (a.id1 and a.engine_src):
        ap.error('--build, or --id1 and --engine-src')
    if not a.audit and not a.data_files:
        ap.error('--audit or --data-files')
    rows = json.loads(a.audit.read_text(encoding='utf-8'))['rows'] if a.audit else None
    report, problem = run(a.build, a.id1, a.engine_src, rows, a.data_files, a.out, a.baseline, a.jobs, a.scene_source,
                          chim_world=a.chim_world, world_id1=a.world_id1, known=a.known, layers=a.layer_world)
    c = report['counts']
    print('door engine check: %d exterior entrances; usable after walking in %d, both ways %d; with the wall traced '
          '(%d region doors) %d; locked %d; placed %d'
          % (c['doors'], c['usable_after_crossing'], c['both_ways'], c['reach_traced'], c['reachable'], c['locked'],
             c['placed']))
    split = report.get('known_split') or {}
    if any(split.values()):
        print('door engine check: unreachable and known %d, not known %d; known but reached now %d'
              % (len(split['known']), len(split['new']), len(split['known_passing'])))
    if problem:
        print('door engine check: ' + problem)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
