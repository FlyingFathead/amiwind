# SPDX-License-Identifier: GPL-3.0-only
"""Every finished unit into the unit cache the moment it comes back (UNIT-STORED-AT-MAP-END-62).

A stage that bakes many independent units (the player view's bodies, say) keeps each unit in the checksummed unit
cache (tools/pass_cache.py UnitCache) so that a build that stops later starts again from the units still missing.
The player view stored its units only when its whole pool map had ended (one worker pool for the step since
BUILD-PLAYER-VIEW-UNDERUSED-48): a stage that stopped mid-map, or a container that was stopped, kept nothing of that
run, and every resume of the v0.0.62 release build baked every player body again (incident INC-20261108-V062BUILD).

run_each() hands each unit to the caller's KEEP the moment its worker returns it (build_parallel.completed_map), in
the parent, so KEEP stores it at once; a unit that fails is collected and named, never ends the map; the times of
every unit that came back go into the item cost history (build_costs) also when the map stops early.

LEGACY_SOURCES keeps a unit cache backwards compatible when its key changes form: a cache keyed on what its workers
run (pass_cache.source_digest of (module, function) entries) looks a missing unit up, once, under the whole-file key
its units were stored with before, but only while the code that makes the unit is exactly what it was then (the
bake-reach digest in the table), so a stored unit is never taken for code that changed. A hit is stored under the
current key (pass_cache.PassCache.load does that for every previous key).
"""
import re
import time

# (unit cache name, bake-reach sources digest) -> whole-file sources digests its units were stored under.
LEGACY_SOURCES = {
    # tools/prepare_player_view.py at 70115402 (the v0.0.62 release build): the player view keyed every unit on the
    # whole files prepare_player_view.py and player_inventory_pose.py; its bake code (bake_unit, bake_body and what
    # they run) has the bake-reach digest below.
    ('player-view', '1eeb4b9a9b78f2df602772279ca9a9d280b94bc7f116ca6c518dbbea6a2a78ae'):
        ('9d09ca9cba358b6505d72a56ef908b7913d7002a2703693fe106326711a70d75',),
    # tools/prepare_area.py and tools/chim_room_batches.py at fe90f8ed (the v0.0.62 release build, whose residents and
    # rooms the v0.0.62 release runs reused): the resident and room unit caches keyed every unit on the whole file, so
    # the v0.0.63 edits elsewhere in prepare_area.py re-keyed all of them (UNIT-KEY-WHOLE-FILE-63). Bake reaches:
    # resident-bake = build_resident + publish_resident, interior-room = build_room (prepare_area.py),
    # interior-room-chim = build_shell (chim_room_batches.py).
    ('resident-bake', '4318d4be491911a8a2867bb8873f23a052a1616df08f4151d7344705a13ec576'):
        ('9e0e915fef811882a5c341a96549762b7fb07ea768a876fa0f0c9411ce8d1786',),
    ('interior-room', '4a4ff8d268a2b8030c1bd8b294aa61c888f734bf66edbbb91e040b370a2c45a2'):
        ('9e0e915fef811882a5c341a96549762b7fb07ea768a876fa0f0c9411ce8d1786',),
    ('interior-room-chim', '02b87fd3252e52456b3e2688fcc2ce3172853ef735ae43d159ef43f1a9983d49'):
        ('115d5e69098e1c5ffd0cf15e11c4431f326b8767ea01d5f650b0885fa1604b0a',),
    # The voice and dialogue tables (tools/greeting_lut.py, tools/dialogue_lut.py image_step) keyed their one unit on
    # whole files, which counted the script compiler's game data and function table, so every v0.0.63 dev build
    # baked them again (BUILD-TABLE-UNITS-REBAKE-63). Their bake reaches (voice: build_master + sound_resolver;
    # dialogue: build_master) were the same at 1d5eda8 (v0.0.62), d2c6408 (v0.0.63-dev2), 6e68096 (dev3) and
    # e7c5fa5a (dev4) as now, apart from the hearing rule and the declaration reader moved unchanged into
    # mwscript/hearing.py and mwscript/lexer.py; the whole-file digests of those four trees follow, in that order.
    ('npc-voice-table', '60f51a53b786fbf51e951a08225b0b4076b0316eb1874a8c048ac0010c20fb20'):
        ('1a15a9d2fe67c7a26d1a4964d0aef607b353a5c54853f2d5dbee49d6cc23cacb',
         'ca0e34d0e6789ffbc9022a46df1c32d937f80b9d41a16e36363855d8cb24cfae',
         'c45e26df3692c2f1c2b91b070023481e754121a788bce552c6d4177655bea662'),
    ('dialogue-table', 'e189af83bf90d3879a820f1837ca40cef7a911c2f79830ec5b0402f63f095b27'):
        ('70a96892b66c2aad94773dbf2c16cc0b04a0e63016fd6de7845c3df4b3821007',
         '004a9ca21f8a211f5e514ed00c236ab97f722d3c35d49d32a8a9addc3fdf07cc',
         '2caa0d24bbe95f1c55921cabef06dd6a8f834c1e3a189790994138acc7a4cfc4',
         '5a291620b94d3f6ffeb02d87d2e689f3600a64ee7c1afd2d38900d221ac061cc'),
    # The world region caches (tools/prepare_world_flora.py, tools/prepare_world_scenery.py) keyed every region on the
    # whole file up to bf2743fa (v0.0.64-dev3); 3c6f31aa keyed them on convert_region without adding their old keys
    # here, so the v0.0.64-dev4 preflight counted all 1931 flora and 2064 scenery regions as baking again
    # (BUILD-REGION-KEY-NO-LEGACY-64). Between bf2743fa and the new key the only edits in their reach were the cache
    # opening lines themselves (prepare / unit_cache), never region code; the old keys are the bf2743fa whole-file
    # digests (key form 2).
    ('world-flora-region', '98a996e7dabfcf7a0fd7bb13c95a86ce3be84e255b4ecd47c835df560da4c1ac'):
        ('c136479e96095474c88c3d543f865973c03e44360bef129d0fe9318916381726',),
    ('world-scenery-region', '625ada31d5038e7277ae2c59babaabbb212bbe850924c5a2b8f0cd3111e4cb5b'):
        ('7aab23025ab2f7644101d1eeecec459efbf5f1a60c39a2049fdb6d8d4b46f302',),
    # resident-bake: its reach names the Toolkit's seam check page as a data file (the seam check's
    # text names it), so the Toolkit edit 62c4ae6b re-keyed all 2147 residents although no resident reads the page
    # (BUILD-RESIDENT-KEY-TOOLKIT-PAGE-64). Apart from that page the reach is the same as at bf2743fa (v0.0.64-dev3),
    # whose residents are stored under the key below.
    ('resident-bake', '965a70be8255f95d2ebb3b44676934cce9faa6163c6592ac17a697a07d4f6c8b'):
        ('4318d4be491911a8a2867bb8873f23a052a1616df08f4151d7344705a13ec576',),
}

# AMIWIND_* settings that say where a stage does its work, never what a unit is made of: left out of a unit key
# (as pass_cache.environment leaves out the run's scratch folder). AMIWIND_RESIDENT_WORK (prepare_area
# resident_work_folder) picks the folder the residents are baked in.
WORK_PLACE_SETTINGS = ('AMIWIND_RESIDENT_WORK',)
# (The list of unit caches still keyed on whole files lives in tests/test_unit_store.py, not here: file names written
# in this module would count as files its users' code reads, and so as part of their keys.)


# Settings a unit's code can only hold, never read (BUILD-UNIT-KEYS-REACH-64). The AMIWIND_* names in a unit key were
# every name its reach holds as text, and a module's top-level constants (MODEL_HULL_VARIABLE, the model hull
# setting's name) are import-time code of every function of that module: every NPC, creature and player-body bake that
# imports mesh_geometry_env keyed the model hull setting, which only the collision code reads, so the v0.0.64-dev5 change of
# its default (chain -> auto) would have baked them all again. A name now counts only when the reached code names it:
# the setting text itself outside such a constant, or the constant's name. Units stored under the older form are
# looked up under it (the full set, with an unread setting at each value in SETTING_VALUES or unset).
# (The names are put together when this module runs: a setting name written in this module, even as two joined
# literals, would count as a setting every user of the unit caches reads, and a bare prefix as every setting.)
SETTING_PREFIX = ''.join(('AMIWIND', chr(95)))
SETTING_VALUES = {SETTING_PREFIX + 'MODEL' + chr(95) + 'HULL': ('auto', 'chain', 'routed', 'balanced', 'compiled')}
SETTING_TEXT = re.compile(re.escape(SETTING_PREFIX) + r'[A-Z0-9_]+')



# Decorators that only wrap a function (they run nothing of its body on import and register it nowhere): such a
# function is import-time code in a unit reach (build_cache '<top>'), but its body runs only when something calls it.
WRAPPING_DECORATORS = frozenset({'contextmanager', 'contextlib.contextmanager', 'staticmethod', 'property',
                                 'lru_cache', 'functools.lru_cache', 'cache', 'functools.cache'})


def _code_only(source, tree):
    """SOURCE with its comments and docstrings blanked (same positions; a docstring becomes 0): text that names a
    setting or a constant there reads nothing."""
    import ast
    import io
    import tokenize
    lines = source.splitlines(keepends=True)

    def blank(start, end, keep=''):
        (row, col), (end_row, end_col) = start, end
        for number in range(row, end_row + 1):
            line = lines[number - 1]
            first = col if number == row else 0
            last = end_col if number == end_row else len(line.rstrip('\r\n'))
            filler = (keep + ' ' * (last - first))[:last - first] if number == row else ' ' * (last - first)
            lines[number - 1] = line[:first] + filler + line[last:]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                blank((first.lineno, first.col_offset), (first.end_lineno, first.end_col_offset), '0')
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                blank(token.start, token.end)
    except (tokenize.TokenError, SyntaxError):
        pass
    return lines


def unread_settings(names, entries, root=None):
    """The settings of NAMES the code of ENTRIES [(path, function or None for the whole script)] never reads: not
    among the names its reach holds at all, or held only as a top-level `CONSTANT = <setting name>` whose CONSTANT no
    reached code names (a reached function or table, a wrapped function once named, every other top-level statement;
    comments and docstrings left out), with the setting written nowhere else in that code. A module the reach reads
    whole (all its units) counts every line. Empty when the reach is uncertain (every name counts)."""
    import ast
    from pathlib import Path
    from build_cache import ENV_ANY, SourceIndex, STAGE_TOP_FORMAT
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    index = SourceIndex(root, top_format=STAGE_TOP_FORMAT)
    try:
        keyed = [(Path(path).resolve().relative_to(root.resolve()).as_posix(), function) for path, function in entries]
    except ValueError:
        return set()
    python, _, uncertain, held_names, units = index.keyed_coverage(keyed)
    if uncertain or ENV_ANY in held_names:
        return set()
    pieces, holders, lazy = [], {}, []
    for path in sorted(python):
        try:
            source = (root / path).read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            return set()
        lines = _code_only(source, tree)
        reached = set(units.get(path) or ())
        whole = not reached or set(index._module_symbols(path)['units']) <= reached
        for statement in tree.body:
            first = min([statement.lineno] + [d.lineno for d in getattr(statement, 'decorator_list', ())])
            text = ''.join(lines[first - 1:statement.end_lineno])
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name) and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str) and SETTING_TEXT.fullmatch(statement.value.value)):
                holders.setdefault(statement.value.value, []).append(statement.targets[0].id)
                continue
            if whole:
                pieces.append(text)
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [ast.unparse(d.func if isinstance(d, ast.Call) else d) for d in statement.decorator_list]
                if not decorators:
                    if statement.name in reached:
                        pieces.append(text)
                elif all(name in WRAPPING_DECORATORS for name in decorators):
                    lazy.append((statement.name, text))
                else:
                    pieces.append(text)          # a decorator that runs code on import: counts
            elif (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                  and isinstance(statement.targets[0], ast.Name)
                  and isinstance(statement.value, (ast.Dict, ast.List, ast.Tuple, ast.Set))):
                if statement.targets[0].id in reached or not _literal(statement.value):
                    pieces.append(text)          # a literal table counts when reached (build_cache lazy_tables)
            else:
                pieces.append(text)              # imports, classes, statements: import-time code
    everything = '\n'.join(pieces)
    # a function whose decorator only wraps it runs when called: its body counts once reached code names it
    waiting = list(lazy)
    while waiting:
        named = [row for row in waiting if re.search(r'\b%s\b' % re.escape(row[0]), everything)]
        if not named:
            break
        everything += '\n' + '\n'.join(text for _, text in named)
        waiting = [row for row in waiting if row not in named]
    unread = {setting for setting in names if setting not in held_names}
    for setting in set(names) & set(held_names):
        constants = holders.get(setting)
        if not constants or setting in everything:
            continue
        if any(re.search(r'\b%s\b' % re.escape(constant), everything) for constant in constants):
            continue
        unread.add(setting)
    return unread


def _literal(node):
    import ast
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True



def keyed_environment(environment, entries, root=None):
    """(the settings of ENVIRONMENT a unit key counts, [older environments to look stored units up under]) for the code
    of ENTRIES (unread_settings). No unread setting: (ENVIRONMENT, [])."""
    unread = unread_settings(set(environment), entries, root) if entries else set()
    if not unread:
        return environment, []
    keyed = {name: value for name, value in environment.items() if name not in unread}
    # the full set as the older form keyed it; then each unread setting at another value, or not yet named (a setting
    # new in the code: absent from the older keys); then every unread setting that is unset left out at once
    # (each also with every unread unset setting left out: one setting changed while others are new)
    unset = {key: value for key, value in environment.items() if not (key in unread and value is None)}
    older = []
    for base in (dict(environment), unset):
        variants = [base]
        for name in sorted(unread):
            variants += [dict(base, **{name: value}) for value in SETTING_VALUES.get(name, ()) + (None,)]
            variants.append({key: value for key, value in base.items() if key != name})
        older += [variant for variant in variants if variant not in older]
    return keyed, older


def legacy_sources(name, sources):
    """The older whole-file keys under which units of cache NAME with the bake-reach digest SOURCES were stored."""
    return tuple(LEGACY_SOURCES.get((name, sources), ()))


def bake_keyed_cache(name, options, sources, previous, files, covered=(), neutral=(), entries=None):
    """The unit cache NAME keyed on SOURCES (the digest of what its workers run), or None when the cache is off.
    OPTIONS as UnitCache.open makes them: the caller's options with the AMIWIND_* settings that FILES read, less the
    NEUTRAL ones (WORK_PLACE_SETTINGS) and, given ENTRIES (the (path, function) SOURCES digests), less the settings
    that code never reads (keyed_environment; stored units are looked up under the full set too); PREVIOUS: older key
    forms (pass_cache.previous_digests) with the LEGACY_SOURCES keys added."""
    import pass_cache
    root = pass_cache.folder()
    if root is None:
        return None
    environment = pass_cache.environment(*files)
    for setting in neutral:
        environment.pop(setting, None)
    keyed, older = keyed_environment(environment, entries) if entries else (environment, [])
    return pass_cache.UnitCache(name, dict(options, environment=keyed), sources, root,
                                previous=tuple(previous) + legacy_sources(name, sources), covered=covered,
                                previous_options=[dict(options, environment=value) for value in older])


class Failed:
    """A unit's error, returned by timed() instead of raised (picklable: the message only)."""

    def __init__(self, message):
        self.message = message


def timed(work):
    """Pool worker: WORK (index, function, task) -> (index, seconds, function(task) or Failed)."""
    index, function, task = work
    began = time.monotonic()
    try:
        result = function(task)
    except Exception as error:   # collected: run_each names every failed unit after keeping the rest
        result = Failed('%s: %s' % (type(error).__name__, error))
    return index, round(time.monotonic() - began, 3), result


def timed_raising(call, work):
    """Pool worker: WORK (index, task) -> (index, seconds, call(task)); an error is raised as call raised it (the CHIM
    units: chim.units.run_units stores every unit that came back before it, then the map ends with that error)."""
    index, task = work
    began = time.monotonic()
    value = call(task)
    return index, round(time.monotonic() - began, 3), value


def completed_units(call, items, jobs):
    """(index, seconds, call(task)) for ITEMS [(index, task)] as each comes back from the worker pool
    (build_parallel.completed_map); the first error ends the map, after every unit handed back before it."""
    from functools import partial
    from build_parallel import completed_map
    return completed_map(partial(timed_raising, call), items, jobs)


def progress_line(label, done, total, name, seconds, failed=False):
    """'LABEL [done/total] NAME 41m12s' ('... FAILED 41m12s'): one short line per unit as it comes back, so the log
    always says how far a stage is (the maintainer asked for an X of Y next to every step, concise)."""
    minutes, rest = divmod(int(round(seconds)), 60)
    took = '%dm%02ds' % (minutes, rest) if minutes else '%ds' % rest
    return '%s [%d/%d] %s %s%s' % (label, done, total, name, 'FAILED ' if failed else '', took)


def stored(cache, inputs, row, contents):
    """Store a unit (UnitCache.store_files) and read its entry back: True when the record and every file are there
    with their SHA-256 (UNIT-CACHE-STORE-ERRORS-SILENT-63: a store never raises, so a folder the build cannot write,
    made by another user, lost every unit without a word). The read-back looks at the files only: it is no lookup, so
    it counts no hit and records no reuse."""
    import hashlib
    import json
    from pass_cache import input_digest
    cache.store_files(inputs, row, contents)
    meta, _ = cache._paths(input_digest(inputs))
    try:
        record = json.loads(meta.read_text(encoding='utf-8'))
        files = record['row']['files']
        if record.get('input_sha256') != input_digest(inputs) or set(files) != set(contents):
            return False
        return all(hashlib.sha256(cache._blob(digest).read_bytes()).hexdigest() == digest ==
                   hashlib.sha256(contents[name]).hexdigest() for name, digest in files.items())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def unwritable_folders(root, user=None):
    """The folders of the unit and pass cache ROOT (each cache's folder and its two-letter and files folders) this
    process cannot write: a build run as the build user stops on them in its first minute instead of losing every
    unit it makes (UNIT-CACHE-STORE-ERRORS-SILENT-63: a seed run as root left a cache folder the builds could not
    write). Missing folders are fine (made when first needed)."""
    import os
    from pathlib import Path
    root = Path(root)
    if not root.is_dir():
        return []
    out = [] if os.access(root, os.W_OK | os.X_OK) else [str(root)]
    for cache in sorted(p for p in root.iterdir() if p.is_dir()):
        folders = [cache] + [p for p in cache.iterdir() if p.is_dir()]
        folders += [p for p in (cache / 'files').iterdir() if p.is_dir()] if (cache / 'files').is_dir() else []
        out += [str(p) for p in folders if not os.access(p, os.W_OK | os.X_OK)]
    return out


def run_each(costs, function, items, names, jobs, keep, fallback=None, label=None, already=0, log=print):
    """Run FUNCTION(task) for ITEMS [(index, task)] on the worker pool, longest first by the cost history COSTS (or
    FALLBACK(name) seconds), and call KEEP(index, result) for each unit the moment it is back. NAMES: one stable name
    per item. LABEL: print '[done/total]' for every unit as it comes back, ALREADY units counted done before (taken
    from the unit cache). Returns ['name: error'] of the units that failed (empty when all passed).
    A KEEP that returns False (its store was not found again, stored()) gets a loud line at once; when the map has
    ended, the count ('K stores FAILED') is printed and the stage fails (UNIT-CACHE-STORE-ERRORS-SILENT-63)."""
    from build_costs import estimator, record
    from build_parallel import completed_map
    names = [str(n) for n in names]
    if len(names) != len(items):
        raise ValueError('run_each needs one name per item')
    total = already + len(items)
    if label:
        log('%s [%d/%d] cached, %d to make' % (label, already, total, len(items)), flush=True)
    by_index = {index: name for (index, _), name in zip(items, names)}
    estimate = estimator(costs, names, fallback)
    cost = None if estimate is None else (lambda work: estimate(by_index[work[0]]))
    seconds, failed, lost = {}, [], []
    try:
        for index, took, result in completed_map(timed, [(index, function, task) for index, task in items], jobs,
                                                 cost=cost):
            seconds[index] = took
            if label:
                log(progress_line(label, already + len(seconds), total, by_index[index], took,
                                  isinstance(result, Failed)), flush=True)
            if isinstance(result, Failed):
                failed.append('%s: %s' % (by_index[index], result.message))
                continue
            if keep(index, result) is False:
                lost.append(by_index[index])
                log('!! %s: STORE FAILED: %s is not in the unit cache after it was stored (is the cache folder '
                    'writable by this user?)' % (label or costs, by_index[index]), flush=True)
    finally:
        record(costs, [by_index[index] for index in seconds], [seconds[index] for index in seconds])
    if lost:
        log('!! %s: %d stores FAILED (%s)' % (label or costs, len(lost), ', '.join(lost[:8])), flush=True)
        raise RuntimeError('%s: %d stores FAILED: the unit cache did not keep %s; every unit made here would be made '
                           'again by the next build (UNIT-CACHE-STORE-ERRORS-SILENT-63)'
                           % (label or costs, len(lost), ', '.join(lost[:8])))
    return failed
