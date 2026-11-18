#!/usr/bin/env python3
"""Build preflight: the checks that take seconds run before any stage (BUILD-CACHE-OWNER-FAILS-STAGE-34).

tools/build.py runs it for every real image build, right after the previous-release check and before setup:

- the workspace cache (WORKSPACE/cache: unit caches, pass caches, the storage pool) holds no folder this
  user cannot write and no entry owned by another user (a container that ran as root left such entries
  and a release build failed four minutes in); its millions of entries are checked on a process pool
  (cache_problems, BUILD-PREFLIGHT-SERIAL-REPEATED-66);
- (free space: since v0.0.53 tools/disk_need.py, right after the options are read: the last known good build's
  figure plus the margin, never below min_free_gib, BUILD-DISK-NEED-UNKNOWN-52; free_space_problems below is the
  plain minimum, for this command alone);
- the game data folder exists and holds the master file;
- every town config's entity and model budget fits the engine's tables (tools/map_engine_limits.py
  budget_room: a config may only tighten the engine's limits, BUILD-BUDGET-ENGINE-LIMITS-35);
- every NPC resident of every CHIM area of the build has a grounding classification in
  config/actor_grounding.json (tools/actor_grounding_census.py area_problems; the chim-town stage stopped
  40 minutes in on unlisted residents, CHIM-ACTOR-GROUNDING-POLICY-36);
- every NPC and creature resident of every room the build's room batches convert (config/room-batches.json, the
  selected expansions' batches, the exterior-like cells set aside) has a grounding class in config/actor_grounding.json
  or config/actor_grounding_rooms.json (room_grounding_problems; the chim-room-batches stage stopped 14 minutes in on
  179 expansion residents, ROOM-BATCH-NPC-GROUNDING-48);
- every CHIM town of a full build other than Seyda Neen and Balmora has a CHIM region frame of the build around its
  frame, whose catalogues carry its harvestable plants (harvest_town_problems, BUILD-HARVEST-TOWN-PLAN-54).

Every problem is listed at once, each with the command that fixes it. Run it alone with
`python3 tools/build_preflight.py --workspace DIR [--data-files DIR]`.

THE EARLY CHECKS (EARLY_CHECKS, BUILD-IMAGE-CHECKS-EARLY-66): one list for every further check of seconds that a stage
or the image step would otherwise meet hours into a build. Each entry is (name, phase, 'module:function'); the function
takes an EarlyContext and returns a list of problems (text naming the unit, its input and the check; empty when all is
well). It never exits; an error of its own is reported as a problem of that check. tools/build.py runs every check of
a phase, prints one line per check and stops once, before any stage, with every problem of the phase in its error and
its failure page. Phase 'inputs' runs with the checks above (the game data, the selected masters, the options);
phase 'stored' runs after the reuse plan, before the first stage, with the stored outputs the build reuses
(EarlyContext.reused); phase 'after:STAGE' runs the moment STAGE has passed in this build, on its output, before the
stages after it (after_stage_problems, called by the stage scheduler: the stage stays passed, the build stops). A new
check is one line in EARLY_CHECKS and a module of its own.
A cache entry that still cannot be read or written later never fails a stage: the unit is built locally and
the build reports "cache write refused".
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

MIN_FREE_ENV = 'AMIWIND_MIN_FREE_GIB'
DEFAULT_MIN_FREE_GIB = 35
FILL_WARN_ENV = 'AMIWIND_FILL_WARN_PERCENT'
DEFAULT_FILL_WARN_PERCENT = 80
SHOWN = 5


def cache_problems_walk(cache, uid=None):
    """[message] for folders under CACHE this user cannot write and entries another user owns: the earlier method, one
    os.walk with a Path per entry on one core (cache_problems is the same check on the pool, the same message)."""
    cache = Path(cache)
    if not cache.is_dir():
        return []
    if uid is None:
        if not hasattr(os, 'geteuid'):
            return []  # no POSIX owners (Windows): only the write test below would apply
        uid = os.geteuid()
    if uid == 0:
        return []
    foreign, unwritable = [], []
    for folder, _, files in os.walk(cache):
        for path in [Path(folder), *(Path(folder) / name for name in files)]:
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if info.st_uid != uid:
                foreign.append(path)
        if not os.access(folder, os.W_OK | os.X_OK):
            unwritable.append(Path(folder))
    return _cache_message(cache, uid, len(foreign), [str(p) for p in foreign[:SHOWN]], len(unwritable),
                          [str(p) for p in unwritable[:SHOWN]])


def _cache_message(cache, uid, foreign, first_foreign, unwritable, first_unwritable):
    problems = []
    gid = os.getegid() if hasattr(os, 'getegid') else uid
    if foreign or unwritable:
        listed = ', '.join((first_unwritable + first_foreign)[:SHOWN])
        problems.append(f'{foreign} cache entries owned by another user and {unwritable} folders this user '
                        f'cannot write under {cache} (first: {listed}); fix, as root where the cache lives: '
                        f'chown -R {uid}:{gid} {cache}')
    return problems


# The cache holds millions of entries (14.2 million on 2026-11-14: the storage pool, the unit caches): their lstat on
# one core, a Path object each, took about a third of a build check, three times per build start (the check before the
# request, aw submit's check and the build itself; BUILD-PREFLIGHT-SERIAL-REPEATED-66). cache_problems walks the folders
# above SPLIT_DEPTH itself and hands each folder's own entries and each subtree at SPLIT_DEPTH to a process pool; the
# results are joined in os.walk's own order (the order those tasks come in), so the counts and the first entries named
# are exactly the serial walk's (tests/test_build_preflight.py compares the pool, the serial path and the earlier method).
SPLIT_DEPTH = 3
TASK_CHUNK = 8
RESULT_TIMEOUT_S = 900    # no result for this long (a worker that died): the walk is done again in this process
FALLBACK = True           # a pool that stops: the same walk in this process (the tests turn it off to see the pool)


def _walk_tasks(cache, depth=SPLIT_DEPTH):
    """The walk of CACHE (a str) in os.walk's order (top-down, symbolic links to folders not followed) as tasks:
    ('here', folder, files) for each folder above DEPTH, ('tree', folder) for each folder at DEPTH."""
    top = len(cache.rstrip(os.sep).split(os.sep))
    for folder, dirs, files in os.walk(cache):
        yield ('here', folder, files)
        if len(folder.rstrip(os.sep).split(os.sep)) - top + 1 >= depth:
            for name in dirs:
                path = os.path.join(folder, name)
                if not os.path.islink(path):        # os.walk does not follow them either
                    yield ('tree', path)
            dirs[:] = []


def _check_folder(folder, files, uid, found):
    """Add FOLDER's and its FILES' owners and FOLDER's write access to FOUND [foreign, first, unwritable, first]."""
    for path in [folder, *(os.path.join(folder, name) for name in files)]:
        try:
            info = os.lstat(path)
        except OSError:
            continue
        if info.st_uid != uid:
            found[0] += 1
            if len(found[1]) < SHOWN:
                found[1].append(path)
    if not os.access(folder, os.W_OK | os.X_OK):
        found[2] += 1
        if len(found[3]) < SHOWN:
            found[3].append(folder)


def _check_task(task, uid=None):
    """(foreign entries, the first SHOWN of them, unwritable folders, the first SHOWN of them) of one walk task."""
    if uid is None:
        task, uid = task
    found = [0, [], 0, []]
    if task[0] == 'here':
        _check_folder(task[1], task[2], uid, found)
    else:
        for folder, _, files in os.walk(task[1]):
            _check_folder(folder, files, uid, found)
    return found


def _check_chunk(chunk):
    return [_check_task(task) for task in chunk]


def _chunks(tasks, size=TASK_CHUNK):
    """TASKS in lists of SIZE, in order (the pool takes one list per call: Pool.imap with a chunksize hands back a
    plain generator, which has no timeout)."""
    chunk = []
    for task in tasks:
        chunk.append(task)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def cache_problems(cache, uid=None, workers=None):
    """[message] for folders under CACHE this user cannot write and entries another user owns. WORKERS: processes
    for the walk (None or 1: this process, the same tasks in the same order); the message is the same either way."""
    cache = Path(cache)
    if not cache.is_dir():
        return []
    if uid is None:
        if not hasattr(os, 'geteuid'):
            return []  # no POSIX owners (Windows): only the write test below would apply
        uid = os.geteuid()
    if uid == 0:
        return []
    tasks = ((task, uid) for task in _walk_tasks(str(cache)))
    total = [0, [], 0, []]

    def add(found):
        total[0] += found[0]
        total[1].extend(found[1][:SHOWN - len(total[1])])
        total[2] += found[2]
        total[3].extend(found[3][:SHOWN - len(total[3])])
    pool = None
    if workers is not None and workers > 1:
        import multiprocessing
        try:
            pool = multiprocessing.get_context('fork').Pool(workers)
        except (ValueError, OSError):   # no fork (Windows) or no processes: this process walks
            pool = None
    if pool is None:
        for task in tasks:
            add(_check_task(task))
    else:
        try:
            with pool:
                results = pool.imap(_check_chunk, _chunks(tasks, TASK_CHUNK))
                while True:
                    try:
                        chunk = results.next(timeout=RESULT_TIMEOUT_S)
                    except StopIteration:
                        break
                    for found in chunk:
                        add(found)
        except Exception:  # noqa: BLE001 - a pool that stops (a worker that died): the same walk in this process
            if not FALLBACK:
                raise
            return cache_problems(cache, uid)
    return _cache_message(cache, uid, total[0], total[1], total[2], total[3])


def free_space_problems(workspace, minimum_gib=None):
    if minimum_gib is None:
        try:
            minimum_gib = float(os.environ.get(MIN_FREE_ENV, DEFAULT_MIN_FREE_GIB))
        except ValueError:
            minimum_gib = DEFAULT_MIN_FREE_GIB
    existing = Path(workspace).absolute()
    while not existing.exists() and existing.parent != existing:
        existing = existing.parent
    try:
        free = shutil.disk_usage(existing).free / 2 ** 30
    except OSError:
        return []
    if free < minimum_gib:
        return [f'{free:.1f} GiB free where the workspace is ({existing}), {minimum_gib:g} GiB needed; fix: free space '
                f'there or build in another --workspace ({MIN_FREE_ENV} sets the minimum)']
    return []


def fill_warning(workspace, share=None):
    """A warning line when the disk the workspace is on is SHARE full or more, naming the garbage collector, or None.
    Never a refusal: free_space_problems refuses; this says early where the space went (BUILD-CACHE-NO-RETENTION-55:
    old runs and cache entries piled up for weeks and nothing said so)."""
    if share is None:
        try:
            share = float(os.environ.get(FILL_WARN_ENV, DEFAULT_FILL_WARN_PERCENT)) / 100
        except ValueError:
            share = DEFAULT_FILL_WARN_PERCENT / 100
    existing = Path(workspace).absolute()
    while not existing.exists() and existing.parent != existing:
        existing = existing.parent
    try:
        usage = shutil.disk_usage(existing)
    except OSError:
        return None
    if not usage.total or usage.used / usage.total < share:
        return None
    return (f'[disk] WARNING: the build disk is {usage.used / usage.total:.0%} full ({usage.free / 2 ** 30:.0f} GiB free '
            f'of {usage.total / 2 ** 30:.0f} GiB at {existing}); old runs and cache entries: python tools/build_gc.py '
            f'plan {Path(workspace)} (a dry run; add --delete to remove what it lists as expired; docs/BUILD_CACHE.md '
            f'"Free disk space"; {FILL_WARN_ENV} sets the percent)')


def data_problems(data_files):
    if data_files is None:
        return []
    data = Path(data_files)
    if not data.is_dir():
        return [f'game data folder {data} does not exist; fix: --data-files <your Morrowind Data Files folder>']
    if not any(p.name.lower() == 'morrowind.esm' for p in data.iterdir()):
        return [f'game data folder {data} has no Morrowind.esm; fix: point --data-files at the Data Files folder']
    return []


def budget_problems(config_dir=None):
    """[problem] when a town config asks for more entities or models than the engine holds."""
    import map_engine_limits
    try:
        if config_dir is None:
            map_engine_limits.check_config_budgets()
        else:
            map_engine_limits.check_config_budgets(config_dir)
    except ValueError as exc:
        return [f'{exc}; fix: lower the budget in the named config']
    return []


def grounding_problems(data_files, areas):
    """[problem] for each CHIM area with an NPC resident the grounding policy does not classify."""
    if data_files is None or not areas or data_problems(data_files):
        return []
    import actor_grounding_census
    return actor_grounding_census.area_problems(data_files, areas)


def room_grounding_problems(data_files, batches, masters=None, log=print):
    """[problem] when an NPC or creature resident of a room the build's room batches convert (BATCHES: the batch
    numbers of tools/build.py room_batch_selection; MASTERS: the selected masters in load order) has no grounding class
    (tools/actor_grounding_census.py room_problems, seconds). The chim-room-batches stage checks the same before its
    first unit, but only 14 minutes into the build: the v0.0.66-dev2 build stopped there on 179 residents of the
    expansion rooms (ROOM-BATCH-NPC-GROUNDING-48). Nothing for a build without room batches or game data, or with a
    selected master missing from the data folder (the build's expansion check names that file, with its fix)."""
    if data_files is None or not batches or data_problems(data_files):
        return []
    from mwad.masters import selected_masters
    from mwad.paths import child_ci
    masters = selected_masters(masters)
    for name in masters:
        try:
            if not child_ci(Path(data_files), name).is_file():
                return []
        except (OSError, ValueError):
            return []
    import actor_grounding_census
    try:
        return actor_grounding_census.room_problems(data_files, batches, masters, log=log)
    except (OSError, ValueError) as exc:   # a room the reader refuses: the stage would stop on it too
        return [f'room batches: the rooms could not be read for the grounding check ({exc}); the chim-room-batches '
                f'stage would stop on the same (ROOM-BATCH-NPC-GROUNDING-48)']


def harvest_town_problems(native, regions, miniwind=False, boxes=None):
    """[problem] for each CHIM town of a full build (NATIVE: made from the game data, tools/chim_town.py) other than
    Seyda Neen and Balmora whose frame no built CHIM region frame reaches (BUILD-HARVEST-TOWN-PLAN-54). Only the two
    fixed towns have a harvest catalogue mechanism of their own (harvest_build.plan_rows, the engine's
    AW_HarvestFollow); another town's plants are carried by the catalogues of the CHIM region frame maps around its
    frame (the v0.0.53 final: Vivec's 10, no region cell inside its frame). REGIONS: the build's CHIM region table
    (resolve_chim_regions: (table, statuses), or None when it builds no region cells). Without a region cell in the ring
    of cells around the town's frame, the image step's harvest coverage check would stop the build late. A MiniWind
    (MINIWIND) lists such plants as its limit instead (its plan says so). BOXES: {town: frame box} (default: the towns'
    own, chim.regions.town_boxes). A necessary condition, checked in seconds; the image step's coverage check stays."""
    from town_config import runtime_towns
    # since v0.0.57 every town with a region table has catalogues of its own (harvest_build.plan_rows,
    # CHIM-NATIVE-HARVEST-MISSING-36); the check stays for a town without one
    fixed = {town['id'] for town in runtime_towns() if town.get('regions')}
    others = [town for town in native or () if town not in fixed]
    if miniwind or not others:
        return []
    from chim import regions as chim_regions
    cells = set((regions[0] or {}).get('cells') or ()) if regions else set()
    boxes = boxes if boxes is not None else chim_regions.town_boxes(others)
    unit = chim_regions.CELL_UNITS
    problems = []
    for town in others:
        box = boxes[town]
        ring = [(x, y) for x in range(int(box[0] // unit) - 1, int(-(-box[2] // unit)) + 1)
                for y in range(int(box[1] // unit) - 1, int(-(-box[3] // unit)) + 1)
                if not chim_regions.box_covered(chim_regions.cell_box((x, y)), [box])]
        if not any(chim_regions.cell_key(cell) in cells for cell in ring):
            problems.append(f'CHIM town {town} has no harvest catalogue mechanism of its own (only Seyda Neen and '
                            f'Balmora do) and no CHIM region frame of this build reaches its frame, so its harvestable '
                            f'plants would be placed nowhere and the image step would stop; fix: build CHIM region cells '
                            f'around it (the default --chim-regions list), or leave the town out of the CHIM areas')
    return problems


# ---------------------------------------------------------------- the early checks (BUILD-IMAGE-CHECKS-EARLY-66)

PHASES = ('inputs', 'stored')
AFTER = 'after:'    # phase after:STAGE: right after STAGE has passed in this build, on its output (after_stage_problems)
# (name, phase, 'module:function'), in the order they run; a pre-flight of its own adds one line here
EARLY_CHECKS = [
    # the image step's actor frames check on the room batches' own output: stored when the stage is taken from an
    # earlier run, right after it when this build makes it (tools/image_early_checks.py)
    ('room-actor-frames', 'stored', 'image_early_checks:room_actor_frames'),
    ('room-actor-frames', AFTER + 'chim-room-batches', 'image_early_checks:room_actor_frames_after'),
    # every outdoor creature and outdoor levelled list of the base game has a model in the actor library (the engine
    # spawns none without one; OUTDOOR-CREATURES-REGRESSION-66, tools/actor_early_checks.py); the image step's actor
    # spec check counts the placed table at the end
    ('outdoor-creature-models', 'stored', 'actor_early_checks:exterior_creature_models'),
    ('outdoor-creature-models', AFTER + 'actor-library', 'actor_early_checks:exterior_creature_models_after'),
    # Seyda Neen's CHIM frame, predicted from the inputs the world stage reads, against its town's statics: the
    # chim-town-seyda stage's own comparison, before the world stage instead of an hour into the build
    # (BUILD-SEYDA-TOWN-CONTAINERS-67, tools/seyda_early_checks.py)
    ('seyda-frame-town', 'stored', 'seyda_early_checks:frame_town'),
    ('seyda-frame-town', AFTER + 'bsp', 'seyda_early_checks:frame_town_after'),
]


def known_phase(phase):
    return phase in PHASES or (str(phase).startswith(AFTER) and len(str(phase)) > len(AFTER))


class EarlyContext:
    """What an early check gets. PHASE: 'inputs' or 'stored'; ARGS: the build's options; MASTERS: the selected masters
    in load order; WORKSPACE: the build workspace; RUN: this build's run folder (not made yet); REUSED: {stage: the
    run folder its stored outputs come from} (phase 'stored'; empty in phase 'inputs'); STEPS: the stage names of the
    plan; KEYS: {stage: this build's stage key} (phase 'stored'); LOG: where a check prints its progress lines."""

    def __init__(self, phase, args=None, masters=(), workspace=None, run=None, reused=None, steps=(), log=print,
                 keys=None):
        if not known_phase(phase):
            raise ValueError('early check phase %r: one of %s or %sSTAGE' % (phase, ', '.join(PHASES), AFTER))
        self.phase, self.args, self.log = phase, args, log
        self.data_files = getattr(args, 'data_files', None)
        self.masters = list(masters or ())
        self.workspace = Path(workspace) if workspace is not None else (
            Path(args.workspace) if getattr(args, 'workspace', None) else None)
        self.run = Path(run) if run is not None else None
        self.reused = {str(stage): Path(folder) for stage, folder in (reused or {}).items()}
        self.steps = [str(name) for name in steps or ()]
        self.keys = {str(stage): str(key) for stage, key in (keys or {}).items()}


def early_problems(context, checks=None):
    """Every early check of CONTEXT.phase (EARLY_CHECKS, or CHECKS): [problem], each starting with its check's name.
    Prints one line per check (its problems or ok, and its time). Never raises and never exits for a check."""
    import importlib
    import time
    problems = []
    for name, phase, target in (EARLY_CHECKS if checks is None else checks):
        if not known_phase(phase):
            problems.append('%s: early check of an unknown phase %r (one of %s or %sSTAGE)'
                            % (name, phase, ', '.join(PHASES), AFTER))
            continue
        if phase != context.phase:
            continue
        began = time.monotonic()
        module, _, function = str(target).partition(':')
        try:
            found = getattr(importlib.import_module(module), function)(context)
            found = [str(problem) for problem in found or ()]
        except (Exception, SystemExit) as exc:   # noqa: BLE001 - a check never stops the build by itself
            found = ['the check itself failed (%s: %s); fix the check (%s), the build does not start without it'
                     % (type(exc).__name__, str(exc).strip()[:500] or '-', target)]
        context.log('Early check %s (%s): %s, %.1f s' % (
            name, phase, '%d problem%s' % (len(found), '' if len(found) == 1 else 's') if found else 'ok',
            time.monotonic() - began))
        problems += ['%s: %s' % (name, problem) for problem in found]
    return problems


def after_stage_problems(stage, run, log=print, checks=None):
    """The checks registered for right after STAGE (phase after:STAGE), on its output in the run folder RUN: called by
    the stage scheduler the moment STAGE has passed in this build. [problem]; nothing registered for it: []."""
    entries = EARLY_CHECKS if checks is None else checks
    if not any(phase == AFTER + stage for _, phase, _ in entries):
        return []
    return early_problems(EarlyContext(AFTER + stage, run=run, steps=[stage], log=log), entries)


def run(workspace, data_files=None, uid=None, minimum_gib=None, space=True, workers=None):
    """[problem] of every check; empty when the build may start. tools/build.py checks the free space itself
    (space=False): release candidates and finals stop on it, development builds print a warning. WORKERS: processes
    for the cache walk (cache_problems; tools/build.py gives its pre-flight workers)."""
    workspace = Path(workspace)
    return (cache_problems(workspace / 'cache', uid, workers=workers)
            + (free_space_problems(workspace, minimum_gib) if space else [])
            + data_problems(data_files) + budget_problems())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--data-files', type=Path)
    args = ap.parse_args(argv)
    problems = run(args.workspace, args.data_files)
    for problem in problems:
        print('Build preflight: ' + problem)
    print(f'Build preflight: {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
