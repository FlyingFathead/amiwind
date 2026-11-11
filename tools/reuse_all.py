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
"""
import ast
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
INDEX_NAME = 'stage-index-v1.json'
INDEX_SCHEMA = 'amiwind-stage-index-1'
CENSUS_FOLDER = 'unit-census-v1'
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
    return {'started': _started(state, path), 'schema': cache.get('schema'), 'status': state.get('status'),
            'stages': stages}


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


def census(cache_root, name, workspace=None):
    """{sources digest: set of unit names} stored in unit cache NAME (each entry read once: the census is kept beside
    the cache, WORKSPACE/cache/unit-census-v1/NAME.json, and only new entries are read)."""
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
        entries[meta.name] = [_sources_of(data), unit]
    if keep is not None and entries != known:
        try:
            keep.parent.mkdir(parents=True, exist_ok=True)
            partial = keep.with_name(f'{keep.name}.{os.getpid()}.tmp')
            partial.write_text(json.dumps(entries, sort_keys=True), encoding='utf-8', newline='\n')
            os.replace(partial, keep)
        except OSError:
            pass
    groups = {}
    for sources, unit in entries.values():
        groups.setdefault(sources, set()).add(unit)
    return groups


def unit_counts(groups, digests):
    """(N, T): units stored under one of DIGESTS (this build's key and the older forms it still looks up), and the
    units the cache holds (its largest group: one key's full set of units)."""
    held = max((len(units) for units in groups.values()), default=0)
    usable = max((len(groups.get(digest, ())) for digest in digests), default=0)
    return min(usable, held), held


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


def unit_report(steps, closures, units, cache_root, workspace, rebuilt, root=ROOT, openers=None):
    """{stage: [(cache name, N, T) or (cache name, None, None)]} of the rebuilt stages that bake into unit caches."""
    if cache_root is None:
        return {}
    openers = unit_cache_openers(root) if openers is None else openers
    report, groups, digests = {}, {}, {}
    for name, _ in steps:
        if name not in rebuilt:
            continue
        for opener in stage_unit_caches(openers, (closures or {}).get(name), (units or {}).get(name)):
            cache = opener['name']
            if not cache:
                continue
            key = (cache, json.dumps(opener['scripts']))
            if key not in digests:
                digests[key] = current_digests(opener, root)
            if cache not in groups:
                groups[cache] = census(cache_root, cache, workspace)
            if digests[key] is None:
                row = (cache, None, max((len(u) for u in groups[cache].values()), default=0))
            else:
                row = (cache, *unit_counts(groups[cache], digests[key][1]))
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
    seconds or more stops too, with its estimated minutes."""
    problems = []
    for name, _ in steps:
        if name not in rebuilt or name in allowed:
            continue
        seconds = (costs or {}).get(name)
        why = str((reasons or {}).get(name) or '')
        if seconds is not None and seconds >= stage_limit and why.startswith('changed: '):
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
