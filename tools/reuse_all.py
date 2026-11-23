#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Reuse every finished stage the workspace already holds (--reuse-all-available, BUILD-UNIT-PREFLIGHT-63).

`tools/build.py --reuse-from RUN` reuses stages of exactly one earlier run. A stopped run with 26 passed stages
could not be combined with the stages of the release run before it, so a build rebuilt work the workspace already
held. With --reuse-all-available the builder looks every stage's fingerprint up in every earlier run of the
workspace that passed that stage, and takes it from the newest one that can deliver it:

  * the stage index (WORKSPACE/cache/stage-index-v1.json): one row per passed stage of every run (run, stage,
    fingerprint), built from the runs' build-state.json and refreshed for the runs that changed since (a stat
    per run), written again when a build ends; the lookup takes seconds;
  * each candidate run is planned exactly as --reuse-from plans it (build_cache.plan_reuse: fingerprint, manifest,
    every output's SHA-256, the files later stages replace there), newest first;
  * the plans are combined stage by stage (combine): a stage taken from one run whose earlier stages come from
    another is taken only when those stages' recorded outputs are the same in both runs, and a stage whose file a
    later stage replaces in its own run is taken only when that later stage is taken too and delivers the file.

Before any stage runs the builder prints one line per stage (minute_one_lines): "reused from RUN", or "rebuild: WHY"
with, for a stage that bakes into a unit cache, "N of T units from the cache". With --reuse-all-available the
build stops in its first minute (strict_problems) when a stage would bake again more than 5 % of the units a unit
cache already holds for it, or when a stage to rebuild runs a per-item bake with no cache at all; each needs a named
--allow-rebuild STAGE:REASON to go on.

The default of a plain build (BUILD-OFFER-EARLIER-RUNS-67): a build given none of --reuse-from, --reuse-all-available,
--no-reuse, --clean, --release-from-scratch, --no-profile, --dry-run or --recover-image-from, in a workspace whose stage
index holds earlier builds, takes --reuse-all-available by itself (default_choice). For that build the first-minute
stops are notices: it says what it makes again and why and goes on (an explicit --reuse-all-available keeps the stop).
It asks once in a terminal whether to reuse (ask_reuse; no terminal: yes) and prints the cached-build notice
(notice_lines): how many stages and units come from earlier builds and from which, and the from-scratch build in a new
build folder recommended if something in the game looks wrong. Reuse stays content-keyed and every file SHA-256 checked.
"""
import ast
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
INDEX_NAME = 'stage-index-v1.json'
INDEX_SCHEMA = 'amiwind-stage-index-1'
CENSUS_FOLDER = 'unit-census-v2'   # v2: each entry also names the build that stored it (REUSE-STOP-OLD-GROUPS-67)
# At most this many earlier runs are planned in one build (each plan checks every output's SHA-256).
MAX_SOURCES = 8
# Runs planned although no stage fingerprint equals: a stage whose key changed only in code it never ran or read
# is reused from them too (build_cache.narrowed_unchanged).
NEWEST_EXTRA = 2
# The strict stop: a stage would bake again more than this share of the units its unit caches hold.
REBAKE_LIMIT = 0.05

# Per-item bake paths with no cache (each item baked again in every build that runs the stage). The gate test
# tests/test_reuse_all.py fails on any path the scan finds that is not listed here. These three are known and
# expected to close (the NPC standing models, the creature library and the arena fighters onto the gallery and
# parts caches, NPC-LIBRARY-UNITS-63); a closed one is taken off the list.
KNOWN_UNCACHED_BAKES = {
    ('tools/npc_library.py', 'bake_standing'): 'NPC-LIBRARY-UNITS-63',
    ('tools/creature_library.py', 'bake'): 'NPC-LIBRARY-UNITS-63',
    ('tools/creature_library.py', 'bake_kf'): 'NPC-LIBRARY-UNITS-63',
    ('tools/creature_library.py', 'bake_skeletal'): 'NPC-LIBRARY-UNITS-63',
    ('tools/prepare_combat.py', 'bake_fighter'): 'NPC-LIBRARY-UNITS-63',
    # the Solstheim tree copies (test stage chim-sol-trees only, 56 views in about a minute; reused as a whole stage)
    ('tools/chim_tree_copies.py', 'bake_view'): 'TREES-DEPTH-56',
    # found by the first scan (2026-11-09), to be judged under BUILD-UNIT-PREFLIGHT-63: the room actors' ground
    # heights, and a study tool no build stage runs (tools/actor_grounding.py bake_ground has its per-placement unit
    # cache since BUILD-TABLE-UNITS-REBAKE-63)
    ('tools/room_actor_bake.py', 'bake_room_ground'): 'BUILD-UNIT-PREFLIGHT-63',
    ('tools/modular_npc_study.py', 'bake_resident'): 'BUILD-UNIT-PREFLIGHT-63',
}
POOL_CALLS = frozenset({'map', 'imap', 'imap_unordered', 'starmap', 'submit', 'run_each', 'completed_map',
                        'map_async', 'starmap_async', 'apply_async', 'ordered_map', 'Pool', 'ProcessPoolExecutor'})
# load_unit: a module handed its unit cache by the caller (tools/player_view_schedule.py bake_try: each body's
# fitting try and the body itself are looked up and stored there) uses the cache without naming its class.
CACHE_WORDS = ('UnitCache', 'bake_keyed_cache', 'gallery_cache', 'PassCache', 'actor_units', 'load_unit')


# --------------------------------------------------------------------------
# The stage index

def index_path(workspace):
    return Path(workspace) / 'cache' / INDEX_NAME


def _started(state, path):
    value = state.get('build_started_at')
    return value if isinstance(value, str) and value else time.strftime('%Y-%m-%dT%H:%M:%S+00:00',
                                                                         time.gmtime(path.stat().st_mtime))


def run_entry(run):
    """{'started', 'schema', 'stages': {stage: fingerprint}} of the stages RUN passed (None: no readable state)."""
    path = Path(run) / 'build-state.json'
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    cache = state.get('stage_cache') or {}
    fingerprints = cache.get('fingerprints') or {}
    stages = {step['name']: fingerprints[step['name']] for step in state.get('steps') or ()
              if step.get('status') == 'passed' and step.get('name') in fingerprints}
    # the version the run built (the default build's notice names it beside the run; BUILD-OFFER-EARLIER-RUNS-67)
    version = state.get('runtime_version') or (state.get('run_name') or {}).get('version')
    return {'started': _started(state, path), 'schema': cache.get('schema'), 'status': state.get('status'),
            'stages': stages, **({'version': version} if isinstance(version, str) and version else {})}


def update_index(workspace, write=True):
    """The workspace's stage index, refreshed for every run whose build-state.json changed (by size and time)."""
    path = index_path(workspace)
    try:
        index = json.loads(path.read_text(encoding='utf-8'))
        if index.get('schema') != INDEX_SCHEMA:
            raise ValueError
    except (OSError, ValueError):
        index = {'schema': INDEX_SCHEMA, 'runs': {}}
    runs, changed = index['runs'], False
    seen = set()
    build = Path(workspace) / 'build'
    for state in sorted(build.glob('*/build-state.json')) if build.is_dir() else ():
        name = state.parent.name
        seen.add(name)
        try:
            info = state.stat()
        except OSError:
            continue
        stamp = [info.st_size, info.st_mtime_ns]
        if (runs.get(name) or {}).get('stat') == stamp:
            continue
        entry = run_entry(state.parent)
        if entry is None:
            continue
        runs[name] = dict(entry, stat=stamp)
        changed = True
    for name in sorted(set(runs) - seen):
        del runs[name]
        changed = True
    if changed and write:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(f'{path.name}.{os.getpid()}.tmp')
            partial.write_text(json.dumps(index, indent=0, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
            os.replace(partial, path)
        except OSError:
            pass
    return index


def record_run(run, workspace=None):
    """Bring the index up to date after RUN ended (passed or not: its passed stages count). Never fails a build."""
    try:
        update_index(Path(workspace) if workspace else Path(run).resolve().parent.parent)
    except Exception as exc:  # noqa: BLE001 - the index is an accelerator, never a reason to fail
        print(f'Stage index not updated: {exc}', flush=True)


def rows(index):
    """[(run, stage, fingerprint, started)] of every passed stage in INDEX."""
    return [(run, stage, fingerprint, entry.get('started') or '')
            for run, entry in sorted(index['runs'].items()) for stage, fingerprint in sorted(entry['stages'].items())]


def matches(index, fingerprints, exclude=()):
    """{stage: [run, ...]} newest first: the runs that passed STAGE with exactly its fingerprint now."""
    found = {}
    for run, stage, fingerprint, started in rows(index):
        if run in exclude or fingerprints.get(stage) != fingerprint:
            continue
        found.setdefault(stage, []).append((started, run))
    return {stage: [run for _, run in sorted(runs, reverse=True)] for stage, runs in found.items()}


def candidate_runs(index, fingerprints, exclude=(), preferred=None, limit=MAX_SOURCES, extra=NEWEST_EXTRA):
    """Run names to plan, in priority order: PREFERRED (an explicit --reuse-from) first, then the runs holding at least
    one stage with its fingerprint now (newest first), then the EXTRA newest runs that passed any of the same stages
    (narrowed reuse). At most LIMIT."""
    runs = index['runs']
    order = sorted((name for name in runs if name not in exclude), key=lambda n: runs[n].get('started') or '',
                   reverse=True)
    found = matches(index, fingerprints, exclude)
    holding = {run for names in found.values() for run in names}
    chosen = [preferred] if preferred and preferred in runs and preferred not in exclude else []
    chosen += [run for run in order if run in holding and run not in chosen]
    added = 0
    for run in order:
        if added >= extra:
            break
        if run not in chosen and set(runs[run]['stages']) & set(fingerprints):
            chosen.append(run)
            added += 1
    return chosen[:limit]


# --------------------------------------------------------------------------
# Combining the plans of several runs

def ancestors_of(dependencies):
    found = {}

    def visit(name, trail=()):
        if name not in found:
            result = set()
            for dep in dependencies.get(name, ()):
                if dep not in trail:
                    result |= {dep} | visit(dep, trail + (name,))
            found[name] = result
        return found[name]

    for name in list(dependencies):
        visit(name)
    return found


def combine(order, dependencies, options, outputs_equal):
    """({stage: (run, plan)}, {stage: [why a newer source was passed over]}).

    OPTIONS: {stage: [(run, plan), ...]} in priority order; a plan as build_cache.plan_reuse makes it, with
    'skipped' = {path: the later stage of that run that replaces it}. OUTPUTS_EQUAL(stage, run_a, run_b): True when
    STAGE's recorded outputs are the same in both runs. A stage keeps its first option unless
      * an earlier stage it depends on is taken from another run whose outputs of it differ, or
      * a file it leaves to a later stage (replaced there in its own run) is not delivered by that later stage
        as this build takes it.
    Options are only ever passed over, never taken back, so the loop ends."""
    ancestors = ancestors_of(dependencies)
    position = {name: 0 for name in options}
    passed_over = {}

    def chosen(name):
        choices = options.get(name) or []
        at = position.get(name, 0)
        return choices[at] if at < len(choices) else None

    def problem(name, run, plan):
        for ancestor in sorted(ancestors.get(name, ())):
            taken = chosen(ancestor)
            if taken is not None and taken[0] != run and not outputs_equal(ancestor, taken[0], run):
                return f'{ancestor} comes from {Path(taken[0]).name} with other outputs'
        for path, writer in sorted((plan.get('skipped') or {}).items()):
            taken = chosen(writer)
            if taken is None:
                return f'{path} is replaced there by {writer}, which this build runs'
            if taken[0] != run and path not in taken[1]['files'] and path not in taken[1]['links']:
                return f'{path} is replaced there by {writer}, which comes from {Path(taken[0]).name} without it'
        return None

    changed = True
    while changed:
        changed = False
        for name in order:
            while chosen(name) is not None:
                run, plan = chosen(name)
                why = problem(name, run, plan)
                if why is None:
                    break
                passed_over.setdefault(name, []).append(f'{Path(run).name}: {why}')
                position[name] += 1
                changed = True
    result = {name: chosen(name) for name in order if chosen(name) is not None}
    return result, passed_over


def finish_plans(taken, dependencies):
    """The plans to apply: each one's rebuilt ancestors, condition and rebuild hazards as this build takes the stages
    (a plan is made against one run; here its ancestors may come from another run or run again)."""
    ancestors = ancestors_of(dependencies)
    plans = {}
    for name, (run, plan) in taken.items():
        plan = {key: value for key, value in plan.items() if key != 'skipped'}
        rebuilt = sorted(a for a in ancestors.get(name, ()) if a not in taken)
        hazards = {stage: count for stage, count in (plan.get('rebuild_hazard_stages') or {}).items()
                   if stage in taken and taken[stage][0] == run}
        plan.update(rebuilt_ancestors=rebuilt, conditional=bool(rebuilt), rebuild_hazard_stages=hazards,
                    rebuild_hazard_count=sum(hazards.values()),
                    rebuild_hazard=plan.get('rebuild_hazard', []) if hazards else [])
        plans[name] = plan
    return plans


def stage_hash(run, stage):
    """The recorded output hash of STAGE where it last ran for RUN (None: no complete record)."""
    import build_cache
    from unit_tree import of_manifest
    record = build_cache.ran_manifest(Path(run), stage)
    if not build_cache.outputs_recorded(record):
        return None
    return (record.get('tree') or of_manifest(record))['stage_hash']


def outputs_equal_from_records():
    memo = {}

    def equal(stage, first, second):
        values = []
        for run in (first, second):
            if (run, stage) not in memo:
                memo[(run, stage)] = stage_hash(run, stage)
            values.append(memo[(run, stage)])
        return values[0] is not None and values[0] == values[1]

    return equal


# --------------------------------------------------------------------------
# Unit caches: how many units a stage would take from the cache

def _imports(tree):
    """{local name: dotted module} of a module's imports."""
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                names[alias.asname or alias.name] = f'{node.module}.{alias.name}'
    return names


def _module_file(root, dotted):
    base = Path(root) / 'tools'
    for candidate in (base / (dotted.replace('.', '/') + '.py'), base / dotted.replace('.', '/') / '__init__.py'):
        if candidate.is_file():
            return candidate
    return None


def _constants(tree):
    return {target.id: node.value.value for node in tree.body if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
            for target in node.targets if isinstance(target, ast.Name)}


def _script(node, path, imports, root):
    """A script argument of a cache opener: __file__, X.__file__ or (one of those, 'function'); None if unknown."""
    if isinstance(node, ast.Tuple) and len(node.elts) == 2 and isinstance(node.elts[1], ast.Constant):
        inner = _script(node.elts[0], path, imports, root)
        return None if inner is None else (inner, node.elts[1].value)
    if isinstance(node, ast.Name) and node.id == '__file__':
        return str(path)
    if (isinstance(node, ast.Attribute) and node.attr == '__file__' and isinstance(node.value, ast.Name)
            and node.value.id in imports):
        found = _module_file(root, imports[node.value.id])
        return None if found is None else str(found)
    return None


def _module_constant(root, node):
    """The string a `module.NAME` node names: NAME's literal value at the top of tools/<module>.py, or None."""
    if not isinstance(node.value, ast.Name):
        return None
    try:
        tree = ast.parse((Path(root) / 'tools' / (node.value.id + '.py')).read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None
    return _constants(tree).get(node.attr)


def unit_cache_openers(root=ROOT):
    """[{'module', 'function', 'name', 'scripts'}] of every unit cache the tools open with a literal key: the cache
    name and the code its key hashes (UnitCache.open(name, options, *scripts), unit_store.bake_keyed_cache(name,
    options, source_digest(*scripts), ...)). 'scripts' is None when an argument cannot be read statically."""
    found = []
    for path in sorted((Path(root) / 'tools').rglob('*.py')):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if 'UnitCache.open(' not in text and 'bake_keyed_cache(' not in text and 'open_cache(' not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        imports, constants = _imports(tree), _constants(tree)
        relative = path.relative_to(root).as_posix()
        for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            for call in ast.walk(function):
                if not isinstance(call, ast.Call) or not call.args:
                    continue
                callee = call.func
                kind = ('open' if isinstance(callee, ast.Attribute) and callee.attr == 'open'
                        and isinstance(callee.value, ast.Name) and callee.value.id == 'UnitCache'
                        else 'keyed' if (isinstance(callee, ast.Name) and callee.id == 'bake_keyed_cache')
                        or (isinstance(callee, ast.Attribute) and callee.attr == 'bake_keyed_cache')
                        # actor_units.open_cache(NAME, entries, source_digest(...), ...): the actor bakes' caches
                        # (room-actor, npc-appearance, ...); left out, the preflight never counted the room-actor
                        # cache, and v0.0.64-dev4 fitted its 2,342 placements again with no stop
                        # (BUILD-ROOM-ACTOR-KEY-SWITCH-64)
                        else 'keyed' if (getattr(callee, 'id', None) == 'open_cache'
                                         or getattr(callee, 'attr', None) == 'open_cache') else None)
                if kind is None:
                    continue
                first = call.args[0]
                name = (first.value if isinstance(first, ast.Constant) and isinstance(first.value, str)
                        else constants.get(first.id) if isinstance(first, ast.Name)
                        else _module_constant(root, first) if isinstance(first, ast.Attribute) else None)
                if kind == 'open':
                    arguments = call.args[2:]
                else:
                    digest = call.args[2] if len(call.args) > 2 else None
                    arguments = (digest.args if isinstance(digest, ast.Call) and getattr(digest.func, 'id', getattr(
                        digest.func, 'attr', None)) == 'source_digest' else None)
                scripts = None
                if arguments is not None and not any(isinstance(a, ast.Starred) for a in arguments):
                    scripts = [_script(a, path, imports, root) for a in arguments]
                    if None in scripts:
                        scripts = None
                found.append({'module': relative, 'function': function.name, 'name': name,
                              'scripts': None if scripts is None else [list(s) if isinstance(s, tuple) else s
                                                                        for s in scripts]})
    return found


def _sources_of(meta):
    provenance = meta.get('provenance') or {}
    for value in (provenance.get('fields') or {}, provenance):
        if isinstance(value, dict) and value.get('sources_sha256'):
            return value['sources_sha256']
    for row in (provenance.get('input_manifest') or {}).get('inputs') or ():
        if row.get('name') == 'pass sources':
            return row.get('sha256')
    return None


class Groups(dict):
    """{sources digest: set of unit names} of a unit cache (census). BATCH: the most units one build stored under one
    key, when every entry names the build that stored it (its request, job or commit), else None."""
    batch = None


def _builder_of(meta):
    provenance = meta.get('provenance') or {}
    return provenance.get('request') or provenance.get('job') or provenance.get('commit') or None


def census(cache_root, name, workspace=None):
    """Groups ({sources digest: set of unit names}) stored in unit cache NAME, with the most units one build stored
    under one key (Groups.batch). Each entry is read once: the census is kept beside the cache,
    WORKSPACE/cache/unit-census-v2/NAME.json, and only new entries are read."""
    folder = Path(cache_root) / name
    keep = (Path(workspace) / 'cache' / CENSUS_FOLDER / f'{name}.json') if workspace else None
    known = {}
    if keep is not None:
        try:
            known = json.loads(keep.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            known = {}
    entries = {}
    for meta in folder.glob('??/*.json') if folder.is_dir() else ():
        if meta.name in known:
            entries[meta.name] = known[meta.name]
            continue
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        unit = ((data.get('provenance') or {}).get('input_manifest') or {}).get('unit') or data.get('input_sha256')
        entries[meta.name] = [_sources_of(data), unit, _builder_of(data)]
    if keep is not None and entries != known:
        try:
            keep.parent.mkdir(parents=True, exist_ok=True)
            partial = keep.with_name(f'{keep.name}.{os.getpid()}.tmp')
            partial.write_text(json.dumps(entries, sort_keys=True), encoding='utf-8', newline='\n')
            os.replace(partial, keep)
        except OSError:
            pass
    groups, batches, every_named = Groups(), {}, True
    for entry in entries.values():
        sources, unit = entry[0], entry[1]
        builder = entry[2] if len(entry) > 2 else None
        groups.setdefault(sources, set()).add(unit)
        if builder:
            batches.setdefault((sources, builder), set()).add(unit)
        else:
            every_named = False
    groups.batch = max(len(units) for units in batches.values()) if batches and every_named else None
    return groups


def held_units(groups):
    """The units one build of a cache looks up, as its stored entries show: its largest group (one key's full set of
    units), bounded by the most units one build stored under one key (Groups.batch) when every entry names its build.
    REUSE-STOP-OLD-GROUPS-67: a table a build looks up once (npc-voice-table) keeps one unit per input set its key saw,
    each stored by another build; its largest group of 7 was 7 builds' tables, not 7 units this build would bake
    again. A cache a build bakes item by item has a build that stored the whole set (player-fp-parts: 579 by one)."""
    held = max((len(units) for units in groups.values()), default=0)
    batch = getattr(groups, 'batch', None)
    return min(held, batch) if batch else held


def unit_counts(groups, digests):
    """(N, T): units stored under one of DIGESTS (this build's key and the older forms it still looks up), and the
    units one build looks up (held_units)."""
    held = held_units(groups)
    usable = max((len(groups.get(digest, ())) for digest in digests), default=0)
    return min(usable, held), held


def units_found(groups, digests):
    """The stored units one opener finds: the largest group under one of DIGESTS (its key and the older forms it still
    looks up), as unit_counts counts them."""
    best = set()
    for digest in digests:
        group = set(groups.get(digest, ()))
        if len(group) > len(best):
            best = group
    return best


def stage_unit_caches(openers, closure, units=None):
    """The openers a stage reaches: its module in the stage's closure, and its function in the reached units when
    the stage's unit reach is known."""
    found = []
    for opener in openers:
        if closure is not None and opener['module'] not in closure:
            continue
        reached = (units or {}).get(opener['module'])
        if reached is not None and opener['function'] not in reached:
            continue
        found.append(opener)
    return found


def current_digests(opener, root=ROOT):
    """(this checkout's key digest, the older forms looked up) of an opener's cache, or None when unreadable."""
    if not opener.get('scripts') or not opener.get('name'):
        return None
    import pass_cache
    import unit_store
    scripts = [tuple(s) if isinstance(s, list) else s for s in opener['scripts']]
    try:
        digest = pass_cache.source_digest(*scripts)
        older = tuple(pass_cache.previous_digests(*scripts))
    except Exception:  # noqa: BLE001 - an unreadable key is reported as unknown, never fails the plan
        return None
    return digest, (digest,) + older + tuple(unit_store.legacy_sources(opener['name'], digest))


# --------------------------------------------------------------------------
# Per-item bakes without a cache

def uncached_bakes(root=ROOT):
    """{(module, function)}: the top-level functions named bake or bake_* of a module that runs a worker pool (map,
    imap, submit, run_each, ordered_map, ...) and opens no cache (no unit, pass, gallery or actor unit cache named
    in it): a per-item bake whose every item is made again in each build that runs it."""
    found = set()
    for path in sorted((Path(root) / 'tools').rglob('*.py')):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if 'def bake' not in text or any(word in text for word in CACHE_WORDS):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        pooled = False
        for call in ast.walk(tree):
            if isinstance(call, ast.Call):
                callee = call.func
                called = (callee.attr if isinstance(callee, ast.Attribute)
                          else callee.id if isinstance(callee, ast.Name) else '')
                pooled = pooled or called in POOL_CALLS
        if not pooled:
            continue
        relative = path.relative_to(root).as_posix()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and (node.name == 'bake' or node.name.startswith('bake_')):
                found.add((relative, node.name))
    return found


# --------------------------------------------------------------------------
# The minute-one report and the strict stop

def parse_allowed(values):
    """{stage: reason} of --allow-rebuild STAGE:REASON values (each needs both)."""
    allowed = {}
    for value in values or ():
        stage, _, reason = str(value).partition(':')
        if not stage.strip() or not reason.strip():
            raise ValueError(f'--allow-rebuild {value!r}: give STAGE:REASON (a stage name and why it may rebuild)')
        allowed[stage.strip()] = reason.strip()
    return allowed


# Stages whose unit cache holds one unit per region the stage converts, and the stage whose receipt lists the regions:
# a region that is a CHIM region cell or a routing-only row gets no map from them (tools/prepare_world_scenery.py
# prepare, tools/prepare_world_flora.py: `entries = regions not no_legacy_map`). The cache keeps every region of
# every earlier key form (2,064 world-scenery regions, 1,931 world-flora regions from builds before the cells moved
# to CHIM), so a stage that converts none of them would still be counted as baking all of them
# (BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64).
REGION_STAGES = {'world-scenery': 'world-terrain', 'world-flora': 'world-terrain'}


def regions_to_make(terrain_run, stage='world-terrain'):
    """How many regions of the terrain stage's receipt in TERRAIN_RUN a region stage converts (those that are neither
    a CHIM region cell nor routing only); None when the receipt cannot be read."""
    try:
        receipt = json.loads((Path(terrain_run) / stage / 'world-regions.json').read_text(encoding='utf-8'))
        regions = receipt['regions']
        return sum(1 for row in regions if not (row.get('chim_region') or row.get('routing_only')))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def region_limits(steps, plans, rebuilt, checklist=None):
    """{stage: most units it can look up} for the REBUILT region stages whose terrain stage is taken from an earlier
    run by the plan (its receipt is read there); a stage whose terrain stage runs again, or whose receipt is unreadable,
    has no limit (all its stored units count, as before).

    CHECKLIST: the summary of this build's exterior checklist ({'bsp': N, 'chim-region': N, 'chim-town': N},
    exterior_plan.make, made before any stage). When the terrain stage runs again its receipt does not exist yet, but
    the checklist already says what it will hold: a region stage converts exactly the regions of 'bsp' cells (every
    other row is a CHIM region cell or routing only). With no 'bsp' cell it converts none, so none of its stored units
    is looked up (BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64, third cause: the eleven rows of Mournhold's districts make
    the terrain stage run again, and the plan counted all 2,064 and 1,931 stored Vvardenfell regions as baked again,
    though the build converts none of them)."""
    limits = {}
    for name, _ in steps:
        terrain = REGION_STAGES.get(name)
        if name not in rebuilt or terrain is None:
            continue
        if terrain not in plans:
            if isinstance(checklist, dict) and checklist.get('bsp') == 0:
                limits[name] = 0
            continue
        count = regions_to_make(plans[terrain].get('from'), terrain)
        if count is not None:
            limits[name] = count
    return limits


# The unit-cache report's keys on every core (BUILD-CHECK-ONE-CORE-66): each cache's key digest (current_digests:
# the code its key hashes, in this form and the older forms still looked up) is a pure function of the checkout,
# worked out for one cache after another on one core (a fresh source index per key form each time). They are worked
# out on forked worker processes, one cache key per task; the answers are the serial ones (tests/test_reuse_all.py).
DIGEST_TIMEOUT_S = 900    # no answer for this long: the pool is stopped and this process works them out alone


def digest_workers():
    """Processes for the unit-cache report's keys: the build's pre-flight workers (build_cache.PREFLIGHT_WORKERS: --jobs
    capped by the cores the build may use; AMIWIND_PREFLIGHT_JOBS=1 = this process alone), else this process alone."""
    cache = sys.modules.get('build_cache')
    workers = getattr(cache, 'PREFLIGHT_WORKERS', None) if cache is not None else None
    return int(workers) if workers else 1


def _digest_task(item):
    opener, root = item
    return current_digests(opener, root)


def unit_digests(wanted, root=ROOT, workers=None):
    """{(cache, scripts json): current_digests(opener)} for WANTED {(cache, scripts json): opener}, on WORKERS forked
    processes (default digest_workers()); one key alone, one worker, or a pool that fails: in this process, one after
    another (the earlier method)."""
    items = list(wanted.items())
    workers = digest_workers() if workers is None else workers
    if workers > 1 and len(items) > 1:
        import gc
        import multiprocessing
        gc.collect()
        gc.freeze()   # the inherited objects stay out of the workers' collections (no copy of every page)
        try:
            with multiprocessing.get_context('fork').Pool(min(workers, len(items))) as pool:
                pending = pool.map_async(_digest_task, [(opener, root) for _, opener in items], chunksize=1)
                found = pending.get(timeout=DIGEST_TIMEOUT_S)
            return {key: value for (key, _), value in zip(items, found)}
        except Exception as exc:  # noqa: BLE001 - a pool that stops: the same keys in this process
            print(f'Unit-cache keys: the worker pool stopped ({type(exc).__name__}: {exc}); working them out here',
                  flush=True)
        finally:
            gc.unfreeze()
    return {key: current_digests(opener, root) for key, opener in items}


def unit_report(steps, closures, units, cache_root, workspace, rebuilt, root=ROOT, openers=None, limits=None,
                workers=None):
    """{stage: [(cache name, N, T) or (cache name, None, None)]} of the rebuilt stages that bake into unit caches.
    LIMITS {stage: units}: the most units a stage can look up (region_limits); the stored group and the units found
    are counted up to it only. WORKERS: processes for the caches' key digests (unit_digests)."""
    if cache_root is None:
        return {}
    openers = unit_cache_openers(root) if openers is None else openers
    report, groups = {}, {}
    wanted = {}   # every cache key the rebuilt stages reach, each once
    for name, _ in steps:
        if name in rebuilt:
            for opener in stage_unit_caches(openers, (closures or {}).get(name), (units or {}).get(name)):
                if opener['name']:
                    wanted.setdefault((opener['name'], json.dumps(opener['scripts'])), opener)
    began = time.monotonic()
    digests = unit_digests(wanted, root, workers)
    if wanted:
        used = workers if workers is not None else digest_workers()
        print(f'Unit-cache keys: {len(wanted)} cache key(s) worked out in {time.monotonic() - began:.1f} s '
              f'({min(used, len(wanted)) if used > 1 and len(wanted) > 1 else 1} worker process(es))', flush=True)
    for name, _ in steps:
        if name not in rebuilt:
            continue
        # A cache several openers of the stage bake into (the creature models: the default route and the whole-model
        # route) holds their units side by side, each set under its own code's digest: the units found are the union
        # of what each opener finds, against the cache's held count once (counted per opener, the whole-model route's
        # 1 of 97 read as "96 of 97 would bake again": BUILD-UNIT-KEYS-REACH-64).
        found, order = {}, []
        for opener in stage_unit_caches(openers, (closures or {}).get(name), (units or {}).get(name)):
            cache = opener['name']
            if not cache:
                continue
            key = (cache, json.dumps(opener['scripts']))
            if cache not in groups:
                groups[cache] = census(cache_root, cache, workspace)
            if cache not in found:
                found[cache], order = set(), order + [cache]
            if found[cache] is None or digests[key] is None:
                found[cache] = None
            else:
                found[cache] |= units_found(groups[cache], digests[key][1])
        for cache in order:
            held = held_units(groups[cache])
            row = (cache, None if found[cache] is None else min(len(found[cache]), held), held)
            limit = (limits or {}).get(name)
            if limit is not None:
                row = (row[0], None if row[1] is None else min(row[1], limit), min(row[2], limit))
            if row not in report.setdefault(name, []):
                report[name].append(row)
    return report


# A whole stage with no unit cache that would redo stored work (its key changed, an earlier run holds it) stops the
# build when its stored run took this long or more (CHIM-KEYS-TOO-BROAD-62: v0.0.64-dev4 converted the whole CHIM
# world again for a key change, with no stop, because the stop looked only at unit caches).
WHOLE_STAGE_LIMIT_SECONDS = 600.0


def stored_seconds(run, stage, depth=12):
    """Wall seconds stage STAGE took where it last ran in full: RUN's build-profile.json, followed back through each
    'reused.from' (at most DEPTH runs); None when no profile says."""
    for _ in range(depth):
        try:
            profile = json.loads((Path(run) / 'build-profile.json').read_text())
        except (OSError, ValueError, TypeError):
            return None
        row = next((s for s in profile.get('stages') or () if s.get('name') == stage), None)
        if row is None:
            return None
        source = (row.get('reused') or {}).get('from')
        if not source:
            return float(row['wall']) if row.get('wall') is not None else None
        run = source
    return None


def strict_problems(steps, rebuilt, unit_rows, closures, uncached, allowed, limit=REBAKE_LIMIT, units=None,
                    costs=None, reasons=None, stage_limit=WHOLE_STAGE_LIMIT_SECONDS):
    """[(stage, why)] that stop a --reuse-all-available build before any stage runs (less those ALLOWED). UNITS:
    {stage: {module: reached functions}}; an uncached bake counts for a stage that reaches it (or, without the
    stage's unit reach, has its module in the closure). COSTS {stage: stored wall seconds} and REASONS {stage: why it
    rebuilds}: a stage without a unit cache whose key changed ('changed: ...') and whose stored run took STAGE_LIMIT
    seconds or more stops too, with its estimated minutes. A stage whose unit caches give back all but LIMIT of their
    units does not: its stored minutes were its unit bakes, which the caches deliver now (the v0.0.66-dev2 check
    stopped chim-room-batches as "about 419 min" with every resident and room from the cache; PLAN-CHECK-UNIT-STOPS-66)."""
    problems = []
    for name, _ in steps:
        if name not in rebuilt or name in allowed:
            continue
        seconds = (costs or {}).get(name)
        why = str((reasons or {}).get(name) or '')
        held_rows = [(usable, held) for _, usable, held in unit_rows.get(name, ()) if held]
        delivered = bool(held_rows) and all(usable is not None and (held - usable) <= limit * held
                                            for usable, held in held_rows)
        if seconds is not None and seconds >= stage_limit and why.startswith('changed: ') and not delivered:
            cached = '; '.join(f'{cache}: {usable} of {held} units from the cache' for cache, usable, held
                               in unit_rows.get(name, ()) if held) or 'no unit cache'
            problems.append((name, f'would run the whole stage again, about {seconds / 60.0:.0f} min where it last ran '
                                   f'in full ({cached}), because its key {why[:200]}'))
        for cache, usable, held in unit_rows.get(name, ()):
            if not held:
                continue
            if usable is None:
                problems.append((name, f'its unit cache {cache} holds {held} units and this build\'s key for them '
                                       'cannot be read: up to all of them may bake again'))
            elif (held - usable) > limit * held:
                problems.append((name, f'would bake again {held - usable} of the {held} units its unit cache {cache} '
                                       f'holds ({100.0 * (held - usable) / held:.0f} %, over {limit * 100:.0f} %)'))
        closure = (closures or {}).get(name)
        for module, function in sorted(uncached):
            reached = ((units or {}).get(name) or {}).get(module)
            if reached is not None:
                hit = function in reached
            else:
                hit = closure is not None and module in closure
            if hit:
                problems.append((name, f'runs {module} {function}, a per-item bake with no cache: every item '
                                       'bakes again'))
    return problems


def minute_one_lines(steps, plans, reasons, unit_rows):
    """One line per stage, before any stage runs."""
    lines = []
    for name, _ in steps:
        if name in plans:
            source = plans[name].get('prerendered')
            origin = f"prerendered {source}" if source else Path(plans[name]['from']).name
            condition = plans[name].get('rebuilt_ancestors') or []
            lines.append(f'   {name}: reused from {origin}'
                         + (f" (if {', '.join(condition)} write the same files again)" if condition else ''))
            continue
        line = f"   {name}: rebuild: {str(reasons.get(name) or 'no earlier run holds it')[:240]}"
        counts = [f'{cache}: {usable} of {held} units from the cache' if usable is not None
                  else f'{cache}: ? of {held} units (key unreadable)' for cache, usable, held in unit_rows.get(name, ())]
        lines.append(line + (' | ' + '; '.join(counts) if counts else ''))
    return lines


def notice_problem_lines(problems):
    """The default build's first-minute notices: the strict stop's findings, each said as what the build makes again
    and why, never a STOP line (the build server reads STOP lines as a stopped check)."""
    lines = [f'NOTICE {stage}: {why}; this build makes that again and goes on' for stage, why in problems]
    if problems:
        stages = sorted({stage for stage, _ in problems})
        lines.append(f'Reuse notice (the default build): {len(stages)} stage(s) make stored work again '
                     f"({', '.join(stages[:6])}{', ...' if len(stages) > 6 else ''}); the build goes on. Given "
                     'explicitly, --reuse-all-available stops here instead (see --allow-rebuild).')
    return lines


# --------------------------------------------------------------------------
# The default of a plain build (BUILD-OFFER-EARLIER-RUNS-67): reuse every earlier build of the workspace, ask once,
# say so at the start and the end

# An explicit reuse choice: the default does not apply and nothing about it is recorded.
EXPLICIT = (('reuse_from', '--reuse-from'), ('reuse_all_available', '--reuse-all-available'))
# Options that keep the default off for this build, in the order their name is given as the reason.
DEFAULT_OFF = (('reuse_declined', '--no-reuse'), ('clean', '--clean'), ('no_profile', '--no-profile'),
               ('dry_run', '--dry-run'), ('recover_image_from', '--recover-image-from'))
# Modes that build nothing: the default does not apply (a --check does: it plans the stages as the build would).
NO_BUILD_MODES = ('plan', 'host_plan', 'versions', 'check_inputs', 'install_dependencies', 'install_sdk',
                  'estimate_world', 'layout_selftest', 'resource_plan')
VERSION_IN_NAME = re.compile(r'_v([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z]+[0-9]+)?)_')
# The from-scratch build the notice recommends. --clean refuses a filled workspace cache and never empties it
# (tools/clean_build.py), so the command names a new build folder; the Windows form is the docs/WINDOWS_BUILD.md launcher.
CLEAN_COMMAND = './build.sh --clean --workspace ../amiwind-clean'
CLEAN_COMMAND_WINDOWS = r'.\build.cmd --clean --workspace ..\amiwind-clean'
FULL_BUILD_LOOKUPS = 50   # build profiles read at most for the last build that ran every stage (newest passed first)


def earlier_builds(index):
    """Names of the runs in the stage index that passed at least one stage: the earlier builds a build can take from."""
    return sorted(name for name, entry in (index.get('runs') or {}).items() if entry.get('stages'))


def default_choice(args, index=None):
    """The reuse default of this build: None where it does not apply (an explicit --reuse-from or --reuse-all-available,
    or a mode that builds nothing), else {'on', 'selected_by', 'earlier_builds'}. On only for a plain build whose
    workspace's stage index (INDEX; default: read from ARGS.workspace, never written) holds an earlier build that passed
    a stage. --no-reuse together with an explicit reuse option is a contradiction (ValueError)."""
    explicit = [flag for dest, flag in EXPLICIT if getattr(args, dest, None)]
    if explicit:
        if getattr(args, 'reuse_declined', False):
            raise ValueError('--no-reuse contradicts ' + ' and '.join(explicit) + '; give one of them')
        return None
    if any(getattr(args, mode, None) for mode in NO_BUILD_MODES):
        return None
    for dest, flag in DEFAULT_OFF:
        if getattr(args, dest, None):
            return {'on': False, 'selected_by': flag, 'earlier_builds': None}
    if getattr(args, 'allow_release_reuse', None) is False:
        return {'on': False, 'selected_by': '--release-from-scratch', 'earlier_builds': None}
    if index is None:
        try:
            index = update_index(args.workspace, write=False)
        except Exception as exc:  # noqa: BLE001 - an unreadable index is no earlier build, never a failed build
            return {'on': False, 'selected_by': f'the stage index could not be read ({type(exc).__name__}: {exc})',
                    'earlier_builds': 0}
    found = len(earlier_builds(index))
    if not found:
        return {'on': False, 'selected_by': 'no earlier build in this workspace', 'earlier_builds': 0}
    return {'on': True, 'earlier_builds': found,
            'selected_by': f"the default: {found} earlier build{'' if found == 1 else 's'} in this workspace"}


def default_line(record):
    """The build's start line about the default."""
    if record['on']:
        return (f"Reuse of earlier builds: on ({record['selected_by']}): every stage they hold unchanged is taken, each "
                'file checked by its SHA-256; --no-reuse turns it off for one build')
    return f"Reuse of earlier builds: off ({record['selected_by']})"


def run_label(name, entry=None):
    """'v0.0.66, built 2026-11-17' of an earlier run: its version (the stage index, else its run name) and start date."""
    entry = entry or {}
    version = entry.get('version')
    if not version:
        match = VERSION_IN_NAME.search(str(name))
        version = match.group(1) if match else None
    started = str(entry.get('started') or '')[:10]
    return '%s, built %s' % ('v' + version if version else 'version not recorded', started or 'on a date not recorded')


def duration_text(seconds):
    minutes = int(round(float(seconds) / 60.0))
    hours, minutes = divmod(minutes, 60)
    return f'{hours} h {minutes:02d} min' if hours else f'{minutes} min'


def last_full_build(workspace, index=None, limit=FULL_BUILD_LOOKUPS):
    """{'run', 'label', 'seconds'} of the newest passed build of WORKSPACE that ran every stage itself (its
    build-profile.json lists no reused stage), or None. Dry runs and MiniWind test builds do not count. Reads at most
    LIMIT profiles, newest passed runs first."""
    index = index if index is not None else update_index(workspace, write=False)
    runs = index.get('runs') or {}
    order = sorted((name for name, entry in runs.items() if entry.get('status') == 'passed' and entry.get('stages')
                    and '_dry-run' not in name and '_miniwind' not in name),
                   key=lambda name: runs[name].get('started') or '', reverse=True)
    for name in order[:limit]:
        try:
            profile = json.loads((Path(workspace) / 'build' / name / 'build-profile.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(profile, dict):
            continue
        stages, seconds = profile.get('stages'), profile.get('wall_seconds')
        if (not stages or not isinstance(seconds, (int, float)) or isinstance(seconds, bool)
                or any(isinstance(row, dict) and row.get('reused') for row in stages)):
            continue
        return {'run': name, 'label': run_label(name, runs[name]), 'seconds': round(float(seconds), 1)}
    return None


def question_text(found, reusable, total):
    return (f"Found {found} earlier build{'' if found == 1 else 's'} in this build folder: {reusable} of {total} stages "
            'can be reused unchanged. Reuse them? [Y/n] ')


def ask_reuse(question, interactive, read=input, write=print):
    """(yes, how): QUESTION asked once in a terminal (INTERACTIVE); Enter, or any answer but one starting with n, is
    yes. With no terminal the answer is yes, printed after the question so the log shows what was decided."""
    if not interactive:
        write(question + 'yes (no terminal to ask)')
        return True, 'no terminal: yes'
    try:
        reply = read(question)
    except EOFError:
        write('yes (no answer)')
        return True, 'terminal, no answer: yes'
    reply = str(reply or '').strip().lower()
    if reply.startswith('n'):
        return False, 'terminal: no'
    return True, 'terminal: yes' + ('' if reply in ('y', 'yes') else ' (the default)')


def notice_lines(record):
    """The cached-build notice of a default build that took stages from earlier builds: at its start, in its end
    summary and in its build report."""
    lines = [f"Earlier builds reused: {record.get('stages_reused') or 0} of {record.get('stages') or 0} stages come "
             'from earlier builds of this workspace, each file checked by its SHA-256:']
    for source in record.get('sources') or ():
        lines.append(f"   {source['stages']:3d} stage{' ' if source['stages'] == 1 else 's'} from {source['label']} "
                     f"({source['run']})")
    found, held = (list(record.get('units') or ()) + [0, 0])[:2]
    if held:
        lines.append(f'   the stages that run again take {found:,} of the {held:,} units they look up from the '
                     'workspace cache')
    lines.append('If something in the game looks wrong or unstable, build once from scratch in a new build folder, '
                 'with the options you build with:')
    lines.append(f'   {CLEAN_COMMAND}    (Windows: {CLEAN_COMMAND_WINDOWS})')
    full = record.get('last_full_build')
    if full:
        lines.append(f"   The last build of this workspace that ran every stage took {duration_text(full['seconds'])} "
                     f"({full['label']}, {full['run']}).")
    else:
        lines.append('   How long a build that runs every stage takes here: not known (this workspace records none).')
    return lines


def settle_default(record, stage_cache, total, workspace, interactive, read=input, write=print, check=False,
                   index=None):
    """The default build after its stage plan: RECORD (default_choice's) filled from STAGE_CACHE (metadata['stage_cache']
    after build_cache.prepare) and TOTAL (the build's stage count), the question asked once (ask_reuse; a --check, CHECK,
    only says what a build would ask), and the cached-build notice printed when the answer is yes. Returns RECORD; with
    the answer no, record['on'] is False and the caller plans the build again without the earlier builds."""
    index = index if index is not None else update_index(workspace, write=False)
    runs = index.get('runs') or {}
    reused = [row for row in (stage_cache.get('reused') or {}).values()
              if isinstance(row, dict) and not str(row.get('from') or '').startswith('prerendered ')]
    counts = {}
    for row in reused:
        source = Path(str(row.get('from'))).name
        counts[source] = counts.get(source, 0) + 1
    minute = stage_cache.get('minute_one') or {}
    rows = {tuple(row) for found in (minute.get('units') or {}).values() for row in found if len(row) == 3}
    record.update(stages_reused=len(reused), stages=total,
                  units=[sum(row[1] or 0 for row in rows), sum(row[2] or 0 for row in rows)],
                  sources=[{'run': name, 'stages': count, 'label': run_label(name, runs.get(name))}
                           for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
                  notices=len(minute.get('notices') or ()), last_full_build=last_full_build(workspace, index))
    found = record.get('earlier_builds') or len(earlier_builds(index))
    if not reused:
        record.update(asked=False, answer=None, answered_by='nothing to reuse')
        write(f'Reuse of earlier builds: none of the {total} stages is held unchanged by the {found} earlier build(s) of '
              'this workspace; every stage runs, its units still come from the workspace cache')
        return record
    question = question_text(found, len(reused), total)
    if check:
        record.update(asked=False, answer=None, answered_by='--check: a build would ask')
        write('A build would ask: ' + question.rstrip())
    else:
        yes, how = ask_reuse(question, interactive, read=read, write=write)
        record.update(asked=bool(interactive), answer='yes' if yes else 'no', answered_by=how)
        if not yes:
            record.update(on=False, selected_by='answered no at the start of the build')
            write('Reuse of earlier builds: off for this build (answered no): every stage runs, its units still come '
                  'from the workspace cache')
            return record
    record['notice'] = notice_lines(record)
    for line in record['notice']:
        write(line)
    return record


# --------------------------------------------------------------------------
# The dry run (read-only): which earlier runs would deliver each stage

def predict_all(steps_run, workspace, root=ROOT, scope=None, exclude=()):
    """{stage: run name or None}: STEPS_RUN's stages fingerprinted against ROOT now (build_cache.predict's way),
    each looked up in every run of the stage index. An upper bound like predict: no outputs are checked."""
    import build_cache
    scope = scope or build_cache.DEFAULT_SCOPE
    steps_run = Path(steps_run)
    steps, state = build_cache.old_run_steps(steps_run, root)
    index = build_cache.SourceIndex(root, scope=scope, top_format=build_cache.STAGE_TOP_FORMAT)
    fingerprints, _, problems, _ = build_cache.fingerprint_steps(steps, steps_run, state, index)
    stage_index = update_index(workspace, write=False)
    found = matches(stage_index, fingerprints, exclude=set(exclude))
    return {name: (None if problems.get(name) or name in build_cache.NON_REUSABLE else (found.get(name) or [None])[0])
            for name, _ in steps}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    index_p = sub.add_parser('index', help='refresh and print the stage index of WORKSPACE')
    index_p.add_argument('workspace', type=Path)
    predict_p = sub.add_parser('predict', help='dry run: the newest run holding each stage of RUN with its key now')
    predict_p.add_argument('run', type=Path, help='a run whose stage list to plan (e.g. the newest one)')
    predict_p.add_argument('--workspace', type=Path, required=True)
    predict_p.add_argument('--exclude', action='append', default=[], help='a run name never to take stages from')
    predict_p.add_argument('--json', action='store_true')
    scan_p = sub.add_parser('uncached', help='list per-item bakes with no cache')
    scan_p.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.action == 'index':
        index = update_index(args.workspace)
        for run, entry in sorted(index['runs'].items(), key=lambda item: item[1].get('started') or ''):
            print(f"{entry.get('started')}  {len(entry['stages']):3d} passed stages  {run}")
        return 0
    if args.action == 'uncached':
        for module, function in sorted(uncached_bakes(args.root)):
            known = KNOWN_UNCACHED_BAKES.get((module, function))
            print(f'{module} {function}' + (f' (known, {known})' if known else ' (NEW)'))
        return 0
    result = predict_all(args.run, args.workspace, exclude=args.exclude)
    if args.json:
        print(json.dumps(result, indent=1))
        return 0
    by_run = {}
    for name, run in result.items():
        print(f"   {name}: {'reused from ' + run if run else 'rebuild'}")
        by_run[run or '(rebuild)'] = by_run.get(run or '(rebuild)', 0) + 1
    for run, count in sorted(by_run.items(), key=lambda item: -item[1]):
        print(f'{count:3d} stages: {run}')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
