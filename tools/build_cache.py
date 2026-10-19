#!/usr/bin/env python3
"""Stage fingerprints, output manifests and explicit reuse of unchanged stages.

Every build records, for each stage, an input fingerprint and (after the stage
passed) a manifest of the files it created, changed or deleted in the run
folder. `tools/build.py --reuse-from OLD_RUN` then copies (or hard-links) the
outputs of stages whose fingerprint did not change, instead of running them.
Reuse is explicit and never silent: the build state, the stage log and the build
summary say "reused (fingerprint ...)" for every such stage.

A fingerprint covers everything a stage can depend on:
  * its command line, with the run folder, the --jobs value and every absolute
    location normalized ({RUN}, {REPO}, {PYTHON}, {DATA}, {TOOL}, {WORKSPACE},
    {EXTERNAL}): what counts is content, so a moved workspace or checkout keeps
    its fingerprints (stage outputs do not depend on the worker count; the
    parallel tests and the from-scratch release gate check that contract);
  * the SHA-256 of the repository code the stage can run and the data files
    that code names. Scope "units" (default): from the stage script's own
    code, the functions and classes it can reach (names, module attributes,
    imports inside reached functions, scripts named by path), transitively,
    each reached module hashed as its import-time code plus the source of
    each reached function (an edit to a function the stage never reaches,
    such as the builder's own scheduler in a module every stage imports,
    keeps the fingerprint); scope "symbols": the same reach, whole files
    hashed; scope "modules" (the first method): every module imported
    anywhere in an imported module (both still selectable);
  * the game input hashes from the build's input lock, when it reads game data;
  * the binaries it runs (map compilers, ffmpeg) and every other file or folder
    outside the run named on its command line (by content);
  * the AMIWIND_* environment variables its reached code names (all of them
    when the code builds such names dynamically), the Python version and
    package versions;
  * the fingerprints of the stages it depends on.

Any doubt means rebuild: a stage is reused only when its fingerprint matches,
the old stage passed, its manifest is complete and unambiguous, every stage it
depends on is reused too, its run-folder input files have the recorded content
and every old output still has its recorded SHA-256. Failing any check, the
stage runs normally. Release candidates and finals refuse reuse unless the
from-scratch gate runs separately (--allow-release-reuse). See docs/BUILD_PROFILE.md.
"""
import argparse
import ast
import errno
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import posixpath
import re
import shutil
import stat as stat_module
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = 'amiwind-stage-outputs-v1'
# v2: per-stage sources and environment, path-independent commands (BUILD-ENV-FINGERPRINT-GLOBAL-33,
# BUILD-CACHE-CLOSURE-WIDE-33, BUILD-CACHE-ABSOLUTE-PATHS-33). v1 runs are not reuse sources.
CACHE_SCHEMA = 'amiwind-stage-cache-v2'
# 'units' (default): the code a stage can reach, hashed per reached function (BUILD-CACHE-OVERBROAD-33);
# 'symbols': the same code, whole files hashed; 'modules': every import of every imported module.
SCOPES = ('units', 'symbols', 'modules')
DEFAULT_SCOPE = 'units'
# Forms of a module's import-time code in scope 'units' (unit_texts): 1 counts every function's default values,
# 2 only defaults that run code on import. Stage fingerprints use 2; a reuse source fingerprinted with 1 is
# compared in its own form (comparable), so the change costs no rebuild (BUILD-KEY-FUNCTION-DEFAULTS-TOP-36).
TOP_FORMATS = (1, 2)
STAGE_TOP_FORMAT = 2
TOP_TEXT = {1: '<top>', 2: '<top>#2'}
UNIT_PREFIX = {1: 'units:', 2: 'units2:'}
ENV_PREFIX = 'AMIWIND_'
ENV_NAME = re.compile(r'AMIWIND_[A-Z0-9_]*[A-Z0-9]')
ENV_ANY = '*'
PLAN_NAME = 'reuse-plan.json'
# Stages whose inputs are not fully fingerprinted always run.
FORCED_REASON = 'forced to run again (--rebuild-stage)'
NON_REUSABLE = {
    'engine': 'compiles with the Amiga SDK, whose files are not fingerprinted (about 15 s)',
    'image': 'final image: always assembled and verified from the stage outputs',
    'dry-run-image': 'final image: always assembled',
}
# Command options whose folder is a content-addressed cache the stage verifies itself.
# The CHIM unit cache keys every unit by its own fingerprint (tools/chim/units.py); hashing the
# folder made the chim stage's fingerprint change with every build that added units
# (BUILD-CACHE-CHIM-UNITS-33). The media and intro stages use the per-file asset pool the same way.
CONTENT_ADDRESSED = {('npc-gallery', '--cache'), ('world-terrain', '--cache'), ('chim', '--unit-cache'),
                     ('media', '--cache'), ('intro', '--cache')}
# The shared storage pool (WORKSPACE/cache/asset-pool-v1, --storage-pool-dir, tools/storage_pool.py) is
# content-addressed whatever stage or option names it: every object is stored by its own SHA-256 and every
# reader (tools/file_cache.py FileCache) looks objects up by a reuse key made of the inputs the object depends
# on (source file hashes, settings, conversion code) and verifies the bytes against the stored SHA-256. What a
# stage reads from it is therefore fixed by inputs its own fingerprint already covers (game data, code). Hashing
# the folder made a stage's fingerprint change with every object any build added, and once the pool grew past
# EXTERNAL_DIRECTORY_LIMIT it made the stage never reusable (BUILD-POOL-ARG-UNFINGERPRINTED-35: balmora's
# --npc-model-pool). Any argument naming the pool or a folder inside it counts as its token, never by content.
POOL_TOKEN = '{WORKSPACE}/cache/asset-pool-v1'
POOL_CONTENT = 'not hashed (content-addressed storage pool)'
# Worker counts (outputs do not depend on them), bookkeeping, and interpreter locations
# (the Python version and packages are fingerprinted themselves).
IGNORED_ENV = {'AMIWIND_BUILD_JOBS', 'AMIWIND_INPUTS_LOCK', 'AMIWIND_PROFILE_SECTIONS', 'AMIWIND_COST_HISTORY', 'AMIWIND_PASS_CACHE',
               'AMIWIND_BUILD_PROFILE', 'AMIWIND_PROFILE_INTERVAL', 'AMIWIND_BUILD_JOBS_FILE',
               'AMIWIND_BUILD_BUDGET', 'AMIWIND_ACTIVE_ENV', 'AMIWIND_PYTHON', 'AMIWIND_STAGE_TRACE',
               'AMIWIND_REBUILD_UNITS', 'AMIWIND_CACHE_FALLBACK', 'AMIWIND_SOURCE_COMMIT', 'AMIWIND_STORAGE_POOL',
               'AMIWIND_BUILD_RECIPE',
               # the stair walk's reuse and its check sample: the same rows either way (stair_walk.walk_cache_mode)
               'AMIWIND_STAIR_WALK_CACHE', 'AMIWIND_STAIR_WALK_SAMPLE', 'AMIWIND_STAIR_WALK_REUSE',
               # what the stages print and when the builder's heartbeat speaks: logs only (build_profile.phase)
               'AMIWIND_LOG_LEVEL', 'AMIWIND_HEARTBEAT_SECONDS', 'AMIWIND_BUILD_EPOCH',
               # who wrote a stair-walk record (tools/stair_records.py): provenance, not an input
               'AMIWIND_RUN_NAME', 'AMIWIND_RUN_COMMIT', 'AMIWIND_RUN_VERSION', 'AMIWIND_AW_REQUEST',
               # who wrote any cache entry (tools/cache_provenance.py): provenance, not an input (CACHE-NO-PROVENANCE-36)
               'AMIWIND_RUN_JOB', 'AMIWIND_RUN_TOOLS_SHA256', 'AMIWIND_RUN_CHIM_VERSION', 'AMIWIND_RUN_WORLD_FORMAT',
               'AMIWIND_RUN_KIND'}
SEPARATORS = '/' + os.sep
EXTERNAL_DIRECTORY_LIMIT = 512 * 1024 ** 2
SKIP_DIRECTORIES = {'.git', '__pycache__', 'out', 'tests', 'node_modules'}
SKIP_PREFIXES = ('docs/images/',)
SKIP_SUFFIXES = ('.md', '.pyc')
PYTHON_ROOTS = ('tools', 'src', '')
PATH_CALLS = {'Path', 'PurePath', 'PurePosixPath', 'joinpath', 'join', 'open', 'child_ci', 'exists', 'isfile', 'isdir'}
# Instrumentation modules: observability only (the profiler, its progress display, this
# module). Every stage imports them (through build_parallel) but they never change a stage's
# outputs (tests/test_build_profile.py checks that); they are left out of every fingerprint and
# not followed further, so a profiler or progress fix does not force a full rebuild. Explicit
# list, tested (tests/test_build_cache.py): add a module here only if it cannot change outputs.
# tools/unit_tree.py: the output-record hashes the stage cache computes (never a stage's outputs).
# tools/progress_line.py: the one form of the stages' progress lines (print only, never an output file).
# tools/cache_provenance.py: who/when/which version wrote a cache entry (CACHE-NO-PROVENANCE-36); it reads only
# the environment, never a repository file, and its statements in the cache writers are left out of every key
# (strip_provenance below).
# tools/resource_plan.py: the resource plan and the memory governor (how many units a pool keeps in flight, never what
# a unit computes or the order of any output; tests/test_resource_plan.py checks a governed map against the serial one).
# tools/pool_status.py, tools/stage_watch.py: the scheduler's live supervisor (queued and running units, cores used,
# worker shares lent to queued work, underuse warnings; BUILD-STAGE-ALLOWANCE-STUCK-43), never what a unit computes.
# tools/build_digest.py: the build summary's digest and build-summary.md (reads the run's records only).
INSTRUMENTATION_MODULES = frozenset({'tools/build_profile.py', 'tools/build_progress.py', 'tools/build_cache.py',
                                     'tools/unit_tree.py', 'tools/progress_line.py', 'tools/cache_provenance.py',
                                     'tools/resource_plan.py', 'tools/pool_status.py', 'tools/stage_watch.py',
                                     'tools/build_digest.py'})
OUTPUT_NEUTRAL = INSTRUMENTATION_MODULES
# Single functions that can never change a stage's outputs although they read files: the closure does not follow them
# (explicit list with the reason, tested in tests/test_build_cache.py; add one only if no output can depend on it).
# - tools/chim/regions.py converter_note: words of a CHIM regions preflight refusal (a refused build writes nothing);
#   it hashes the whole converter (chimport.code_identity: every file of tools/, src/ and config/), so every stage
#   that can reach the preflight keyed tools/release-files.json and the other files there, and a release file list
#   edit rebuilt the chim stage (BUILD-REUSE-KEYS-TOO-BROAD-35, v0.0.44-dev1 build try 2).
OUTPUT_NEUTRAL_UNITS = frozenset({('tools/chim/regions.py', 'converter_note')})
# Pool scheduling functions: how many units run at once, in which order and how long a pool waits before it starts
# more. They hand each unit to the same function with the same item and return its result, so no output depends on
# their code. Unlike OUTPUT_NEUTRAL_UNITS they are still followed (what they call, such as worker_environment(),
# keys every stage that reaches it); only their own text is left out of the digests. Origin: v0.0.45, the
# BUILD-CHIM-SERIAL-SECTIONS-44 pool changes turned 34 of 37 reusable stages into rebuilds. A function joins this
# list only if it schedules and never builds, reads or writes a unit's data (tests/test_build_cache.py).
SCHEDULING_UNITS = frozenset({
    ('tools/build_parallel.py', '_running'),
    ('tools/build_parallel.py', '_grow_seconds'),
    ('tools/build_parallel.py', '_submit'),
    ('tools/build_parallel.py', 'completed_map'),
    ('tools/build_parallel.py', 'governed_map'),
    ('tools/build_parallel.py', '_sized_map'),
})


def scheduling_top_text(relative, top):
    """A module's import-time text without the default-value lines of its SCHEDULING_UNITS functions. Top format 1
    lists every plain function's defaults (`\\0defaults NAME: ...`), so adding a scheduling function, or a default to
    one, still changed the import-time code of tools/build_parallel.py and with it every stage, NPC gallery face and
    stair walk that reaches it (BUILD-REUSE-SCHEDULER-TOP-45: the v0.0.45 release build reconverted all 3,551 gallery
    faces and walked all 1,351 stair frames again for _grow_seconds and governed_map's item_mib=None)."""
    names = {unit for path, unit in SCHEDULING_UNITS if path == relative}
    if not names:
        return top
    prefixes = tuple('\0defaults %s: ' % name for name in names)
    return ''.join(line for line in top.splitlines(keepends=True) if not line.startswith(prefixes))


INSTRUMENTATION_STEMS = frozenset(path.rsplit('/', 1)[-1][:-3] for path in INSTRUMENTATION_MODULES)
# The reuse step of a reused stage (`build_cache.py apply`) also loads the storage pool (tools/storage_pool.py) to
# link verified files; it never changes their bytes, so where it was loaded from is no reason to refuse the stage's
# record (it stays in fingerprints that reach it).
APPLY_STEMS = INSTRUMENTATION_STEMS | {'storage_pool'}
# scratch: the builder's scratch folder (build_scratch.stage_environment: AMIWIND_SCRATCH = RUN/scratch) holds
# only transient per-use folders; counted as an undeclared output, it made every stage running when it first
# appeared non-reusable, and every later stage with them (BUILD-REUSE-SCRATCH-UNDECLARED-33).
RUN_PRIVATE = {'logs', 'profile', 'scratch', 'build-state.json', 'build-state.tmp', 'build-profile.json',
               'build-profile.json.tmp', 'build-summary.json', 'build-summary.tmp',
               # the scheduler's live summary and supervisor (tools/build_digest.py, tools/stage_watch.py), written
               # while stages run; never a stage's output
               'build-summary.md', 'build-summary.md.tmp', 'underused.jsonl'}
TEMPORARY_SUFFIX = '.amiwind-reuse-tmp'


# Provenance statements (tools/cache_provenance.py) in the cache writers: `import cache_provenance` and bare calls
# `cache_provenance.NAME(...)`, each on lines of its own. They record who, when and from which version a cache
# entry was written, check an entry's output SHA-256 on read (a mismatch is a miss: the unit is built again) and
# append reuse lines; they never change an output. Every key computation reads module source with them removed
# (strip_provenance), so adding provenance to a writer keeps every stage, unit and pass key (maintainer order
# 2026-10-11: "KEEP USING all existing results and hashes WITHOUT REDOING ANYTHING"; tests/test_cache_provenance.py).
PROVENANCE_MODULE = 'cache_provenance'


def _provenance_statement(node):
    if isinstance(node, ast.Import):
        return all(alias.name == PROVENANCE_MODULE and alias.asname is None for alias in node.names)
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return False
    func = node.value.func
    while isinstance(func, ast.Attribute):
        func = func.value
    return isinstance(func, ast.Name) and func.id == PROVENANCE_MODULE and isinstance(node.value.func, ast.Attribute)


def strip_provenance(text):
    """TEXT without its provenance statements (whole lines), or TEXT itself when it has none (or any doubt)."""
    if PROVENANCE_MODULE not in text:
        return text
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    lines = text.splitlines(keepends=True)
    drop = set()
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody', 'handlers'):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            statements = [item for item in block if isinstance(item, ast.stmt)]
            found = [item for item in statements if _provenance_statement(item)]
            if not found or len(found) == len(statements):
                continue  # never empty a block: the statement stays (and counts)
            for item in found:
                first, last = lines[item.lineno - 1], lines[item.end_lineno - 1]
                if first[:item.col_offset].strip() or last[item.end_col_offset:].strip().split('#')[0].strip():
                    continue  # shares a line with other code: it stays
                drop.update(range(item.lineno, item.end_lineno + 1))
    if not drop:
        return text
    stripped = ''.join(line for number, line in enumerate(lines, 1) if number not in drop)
    try:
        ast.parse(stripped)
    except SyntaxError:
        return text
    return stripped


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def require_reuse_allowed(version, allow_release=False):
    """--reuse-from is for -devN builds; rc and final images are built from scratch."""
    if re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version) or allow_release:
        return
    raise ValueError(f'Version {version} is a release candidate or final: --reuse-from is refused. Release images '
                     'are built from scratch (the from-scratch gate). Use --allow-release-reuse only while that gate '
                     'runs separately on the same commit.')


# --------------------------------------------------------------------------
# Repository sources

class FileHashes(MutableMapping):
    """{relative path: SHA-256}: the file list is known at once, each hash on first use.

    A converter that fingerprints its own code (the world terrain map cache) then opens
    only the files it covers, which the stage read trace expects.
    """

    def __init__(self, paths):
        self._paths = paths
        self._hashes = {}

    def __getitem__(self, key):
        if key not in self._hashes:
            self._hashes[key] = sha256_file(self._paths[key])
        return self._hashes[key]

    def __setitem__(self, key, value):
        self._paths.setdefault(key, None)
        self._hashes[key] = value

    def __delitem__(self, key):
        del self._paths[key]
        self._hashes.pop(key, None)

    def __contains__(self, key):
        return key in self._paths

    def __iter__(self):
        return iter(self._paths)

    def __len__(self):
        return len(self._paths)


# Source text -> _parse_text / module_symbols result, shared by every SourceIndex of this process. Both are pure
# functions of the text (and the scope's REFINED flag): an index of an edited file reads a new text and gets a new
# entry, so a shared result is always the one a fresh parse would give. Callers only read the results.
_PARSE_MEMO = {}
_SYMBOL_MEMO = {}


def _parse_text(raw):
    """(imports, string constants, broken) of one module's source text: a pure function of RAW, so every
    index shares one result per text (_PARSE_MEMO); the AST walk is most of a closure's cost."""
    text = strip_provenance(raw)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ([], [], True)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    # Constants used as path parts: ROOT / 'engine', Path('config'), os.path.join(..., 'docs').
    path_parts = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            path_parts.update(id(side) for side in (node.left, node.right))
        elif isinstance(node, ast.Call):
            function = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            if function in PATH_CALLS:
                path_parts.update(id(argument) for argument in node.args)
    imports, constants = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, 0, None) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.module or '', node.level, [alias.name for alias in node.names]))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            constants.append((node.value, '/' in node.value or id(node) in path_parts))
        elif isinstance(node, (ast.BinOp, ast.JoinedStr)):
            joined = folded_string(node)
            if joined is not None:
                constants.append((joined, '/' in joined or id(node) in path_parts))
    return (imports, constants, False)


class SourceIndex:
    """SHA-256 of every repository file a stage may read (docs prose and tests excluded).

    SCOPE 'units' (default) and 'symbols' follow what a stage's code can reach ('units'
    hashes a reached module as its import-time code plus each reached function,
    'symbols' the whole file); 'modules' (the first method) follows every import of
    every imported module. All are kept.
    """

    def __init__(self, root=ROOT, scope=DEFAULT_SCOPE, top_format=1):
        if scope not in SCOPES:
            raise ValueError(f'fingerprint scope must be one of {", ".join(SCOPES)}')
        if top_format not in TOP_FORMATS:
            raise ValueError(f'top_format must be one of {TOP_FORMATS}')
        self.root = Path(root)
        self.scope = scope
        # Stage fingerprints use STAGE_TOP_FORMAT; the per-unit caches (gallery models, image passes, world
        # regions) keep format 1 until their own key format changes (BUILD-KEY-FUNCTION-DEFAULTS-TOP-36).
        self.top_format = top_format
        self._files = None
        self._closures = {}
        self._parsed = {}
        self._modules = {}
        self._symbols = {}
        self._exact = {}
        self._data_maps = None
        self._reached = {}
        self._json_values = {}

    @property
    def files(self):
        if self._files is None:
            files = {}
            for folder, directories, names in os.walk(self.root):
                relative = Path(folder).relative_to(self.root).as_posix()
                relative = '' if relative == '.' else relative + '/'
                directories[:] = sorted(d for d in directories
                                        if not d.startswith('.') and d not in SKIP_DIRECTORIES
                                        and not (relative + d + '/').startswith(SKIP_PREFIXES))
                for name in sorted(names):
                    path = relative + name
                    if name.startswith('.') or name.endswith(SKIP_SUFFIXES) or path.startswith(SKIP_PREFIXES):
                        continue
                    full = Path(folder) / name
                    if full.is_file():
                        files[path] = full
            self._files = FileHashes(files)
        return self._files

    def _parse(self, relative):
        if relative not in self._parsed:
            raw = (self.root / relative).read_text(encoding='utf-8', errors='replace')
            known = _PARSE_MEMO.get(raw)
            if known is None:
                known = _PARSE_MEMO[raw] = _parse_text(raw)
            self._parsed[relative] = known
        return self._parsed[relative]

    def _module_files(self, name, base=''):
        """Repository files that can provide module NAME (relative paths; BASE for relative imports)."""
        parts = [part for part in name.split('.') if part]
        key = (name, base)
        if key not in self._modules:
            # Every root that could provide the module counts (tools/mwad.py and src/mwad/ both do).
            # Existence comes from the index: no file system call per import.
            roots = [base] if base is not None else list(PYTHON_ROOTS)
            found = []
            for root in roots:
                prefix = root + '/' if root else ''
                for depth in range(1, len(parts) + 1):
                    stem = prefix + '/'.join(parts[:depth])
                    found += [c for c in (stem + '.py', stem + '/__init__.py') if c in self.files]
            self._modules[key] = found
        return self._modules[key]

    def closure(self, script):
        """(python files, data files, uncertain) for a stage script, transitively."""
        return self._analysis(script)[:3]

    def environment_names(self, script):
        """AMIWIND_* names the stage's code can read; {ENV_ANY} when it builds names dynamically."""
        return self._analysis(script)[3]

    def _analysis(self, script):
        script = Path(script).resolve()
        key = str(script)
        if key not in self._closures:
            try:
                start = script.relative_to(self.root.resolve()).as_posix()
            except ValueError:
                self._closures[key] = (set(), set(), True, {ENV_ANY})
                return self._closures[key]
            if self.scope == 'modules':
                python, data, uncertain, constants = self._closure_modules(start)
            else:
                python, data, uncertain, constants = self._closure_symbols(start, key)
            self._closures[key] = (python, data, uncertain, environment_names(constants, uncertain))
        return self._closures[key]

    def _closure_modules(self, start):
        """The earlier method: every import of every imported module (scope 'modules')."""
        python, constants, uncertain = set(), [], False
        pending = [start]
        while pending:
            relative = pending.pop()
            if relative in python or relative in OUTPUT_NEUTRAL or relative not in self.files:
                continue
            python.add(relative)
            imports, strings, broken = self._parse(relative)
            uncertain = uncertain or broken
            constants.extend(strings)
            folder = relative.rsplit('/', 1)[0] if '/' in relative else ''
            for module, level, names in imports:
                if level:
                    base = folder
                    for _ in range(level - 1):
                        base = base.rsplit('/', 1)[0] if '/' in base else ''
                    targets = [(module, base)] + [(f'{module}.{n}' if module else n, base) for n in names or ()]
                else:
                    targets = [(module, None)] + [(f'{module}.{n}', None) for n in names or ()]
                for target, base in targets:
                    pending.extend(self._module_files(target, base))
            for text, _ in strings:
                # Scripts named by path (spec_from_file_location, subprocess of a repo tool).
                if text.endswith('.py') and '\n' not in text and len(text) < 200:
                    for base in ('', 'tools/', folder + '/' if folder else ''):
                        candidate = posixpath.normpath(base + text)
                        if candidate in self.files:
                            pending.append(candidate)
        data = set()
        segments = set()
        basenames = []
        for text, path_like in constants:
            if len(text) > 400 or '\n' in text:
                continue
            basenames.append(text)
            if path_like:
                for match in re.finditer(r'(?:^|/)([A-Za-z0-9_.-]+)(?=/|$)', text):
                    segments.add(match.group(1))
        for relative in self.files:
            if relative.endswith('.py'):
                continue
            top, _, rest = relative.partition('/')
            if not rest or top in ('tools', 'src'):
                name = relative.rsplit('/', 1)[-1]
                if any(name in text for text in basenames):
                    data.add(relative)
            elif top in segments:
                data.add(relative)
        return python, data, uncertain, constants

    # ----------------------------------------------------------------------
    # Scope 'symbols': what the stage's code can reach

    def _exact_module(self, name, base=None):
        """Repository files that are module NAME itself (not its parent packages)."""
        key = (name, base)
        if key not in self._exact:
            parts = [part for part in name.split('.') if part]
            found = []
            if parts:
                for root in ([base] if base is not None else list(PYTHON_ROOTS)):
                    stem = (root + '/' if root else '') + '/'.join(parts)
                    found += [c for c in (stem + '.py', stem + '/__init__.py') if c in self.files]
            self._exact[key] = found
        return self._exact[key]

    def _module_symbols(self, relative):
        if relative not in self._symbols:
            raw = (self.root / relative).read_text(encoding='utf-8', errors='replace')
            key = (raw, self.scope == 'units')
            known = _SYMBOL_MEMO.get(key)
            if known is None:
                text = strip_provenance(raw)
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    tree = None
                known = _SYMBOL_MEMO[key] = module_symbols(tree, text, refined=key[1])
            self._symbols[relative] = known
        return self._symbols[relative]

    def refresh(self, paths):
        """Forget what this index knew about PATHS (edited files) and every closure."""
        for path in paths:
            self._parsed.pop(path, None)
            self._symbols.pop(path, None)
            if self._files is not None and path in self._files:
                self._files._hashes.pop(path, None)
        self._closures.clear()
        self._reached.clear()
        self._json_values.clear()

    def reached_units(self, script):
        """{python file: reached units} of a stage script (scopes 'units' and 'symbols'), or None."""
        script = Path(script).resolve()
        self._analysis(script)
        return self._reached.get(str(script))

    def _unit_texts(self, relative, top_format):
        """{unit: text} as unit_digest and unit_hashes hash them: the import-time text without the default-value
        lines of the module's scheduling functions (scheduling_top_text)."""
        texts = dict(self._module_symbols(relative).get('texts') or {})
        top = TOP_TEXT[top_format]
        if top in texts:
            texts[top] = scheduling_top_text(relative, texts[top])
        return texts

    def unit_digest(self, relative, units, top_format=None):
        """SHA-256 over a module's import-time code and the source of each reached function.
        TOP_FORMAT (default: the index's): which form of the import-time code (TOP_FORMATS)."""
        top_format = top_format or self.top_format
        texts = self._unit_texts(relative, top_format)
        text = {'<top>': TOP_TEXT[top_format]}
        rows = {unit: hashlib.sha256(texts[text.get(unit, unit)].encode('utf-8', 'surrogateescape')).hexdigest()
                for unit in sorted(set(units) | {'<top>'}) if text.get(unit, unit) in texts
                and (relative, unit) not in SCHEDULING_UNITS}
        return UNIT_PREFIX[top_format] + digest_json(rows)

    def _closure_symbols(self, start, key=None, entry=None):
        """(python files, data files, uncertain, constants) reachable from START run as a script.

        A module's top level runs when it is imported (its `if __name__ == '__main__'`
        block only when it is the script). A function or class counts once something
        reached names it: a call, a reference (callbacks, tables), `module.name`, or a
        re-export. Decorated definitions, `from m import *`, getattr()/vars() on a
        module and globals() count the whole module; import_module()/__import__()
        with a computed name, eval() or exec() make the closure uncertain (all files).
        """
        reached, pending, constants = set(), [], []
        state = {'uncertain': False}
        whole_done = set()

        def reach(relative, unit):
            if relative in OUTPUT_NEUTRAL or relative not in self.files or (relative, unit) in reached \
                    or (relative, unit) in OUTPUT_NEUTRAL_UNITS:
                return
            reached.add((relative, unit))
            pending.append((relative, unit))

        def reach_module(relative, main=False):
            reach(relative, '<top>')
            if main:
                reach(relative, '<main>')

        def reach_whole(relative):
            if relative in whole_done or relative in OUTPUT_NEUTRAL or relative not in self.files:
                return
            whole_done.add(relative)
            for unit in self._module_symbols(relative)['units']:
                if unit != '<main>':
                    reach(relative, unit)

        def folder_of(relative):
            return relative.rsplit('/', 1)[0] if '/' in relative else ''

        def relative_base(relative, level):
            base = folder_of(relative)
            for _ in range(level - 1):
                base = folder_of(base)
            return base

        def import_targets(relative, module, level, names):
            base = relative_base(relative, level) if level else None
            targets = [(module, base)] + [((f'{module}.{n}' if module else n), base) for n in names or () if n != '*']
            for target, target_base in targets:
                for found in self._module_files(target, target_base):
                    reach_module(found)

        def descend(relative, module, level, chain, whole, seen):
            """Module MODULE (imported in RELATIVE) used as MODULE.chain."""
            base = relative_base(relative, level) if level else None
            files = self._exact_module(module, base)
            for found in files:
                reach_module(found)
            if not chain:
                if whole:
                    for found in files:
                        reach_whole(found)
                return
            head, rest = chain[0], chain[1:]
            if self._exact_module(f'{module}.{head}' if module else head, base):
                descend(relative, f'{module}.{head}' if module else head, level, rest, whole, seen)
                return
            for found in files:
                reach_symbol(found, head, rest, whole, seen)

        def resolve(relative, binding, chain, whole, seen):
            if binding[0] == 'module':
                descend(relative, binding[1], binding[2], chain, whole, seen)
            else:
                _, module, level, attribute = binding
                base = relative_base(relative, level) if level else None
                name = f'{module}.{attribute}' if module else attribute
                if self._exact_module(name, base):
                    descend(relative, name, level, chain, whole, seen)
                else:
                    descend(relative, module, level, (attribute, *chain), whole, seen)

        def reach_symbol(relative, name, chain, whole, seen):
            if (relative, name) in seen or relative not in self.files:
                return
            seen = seen | {(relative, name)}
            symbols = self._module_symbols(relative)
            if name in symbols['units'] and not name.startswith('<'):
                reach(relative, name)
                return
            binding = symbols['bindings'].get(name)
            if binding is not None:  # re-exported name
                resolve(relative, binding, chain, whole, seen)

        def lookup(symbols, unit, name):
            facts = symbols['units'][unit]
            if name in facts['bindings']:
                return facts['bindings'][name]
            if name in symbols['bindings']:
                return symbols['bindings'][name]
            return symbols['fallback'].get(name)

        if entry is None:
            reach_module(start, main=True)
        else:
            # one function of the module (entry_digest): its import-time code and that function
            reach_module(start)
            reach(start, entry)
        while pending:
            relative, unit = pending.pop()
            symbols = self._module_symbols(relative)
            if symbols['broken']:
                state['uncertain'] = True
                continue
            facts = symbols['units'].get(unit)
            if facts is None:
                continue
            reach_module(relative)
            constants.extend(facts['constants'])
            state['uncertain'] = state['uncertain'] or facts['uncertain']
            for module, level, names in facts['imports']:
                import_targets(relative, module, level, names)
            for module, level in facts['star']:
                base = relative_base(relative, level) if level else None
                for found in self._exact_module(module, base):
                    reach_whole(found)
            for module in facts['dynamic_imports']:
                for found in self._module_files(module, None):
                    reach_module(found)
            if facts['globals']:
                reach_whole(relative)
            for name in facts['names'] | facts['whole']:
                if name in symbols['units'] and not name.startswith('<'):
                    reach(relative, name)
                    continue
                binding = lookup(symbols, unit, name)
                if binding is not None:
                    resolve(relative, binding, (), name in facts['whole'] or binding[0] == 'module'
                            or self._binding_is_module(relative, binding), frozenset())
            for name, chain in facts['attributes']:
                if name in symbols['units'] and not name.startswith('<'):
                    reach(relative, name)
                    continue
                binding = lookup(symbols, unit, name)
                if binding is not None:
                    resolve(relative, binding, chain, False, frozenset())
            folder = folder_of(relative)
            for text, _ in facts['constants']:
                # Scripts named by path (spec_from_file_location, a repository tool run as a subprocess).
                if text.endswith('.py') and '\n' not in text and len(text) < 200:
                    for base in ('', 'tools/', folder + '/' if folder else ''):
                        candidate = posixpath.normpath(base + text)
                        # A module naming itself ('generator': 'tools/cell_progress.py' in its own output) is a
                        # label, not a run of its command line: following it reached its main() and every file
                        # main() can name (BUILD-CELL-PROGRESS-KEY-BUGS-35: all of docs/, the bug register too).
                        # A unit that starts a Python process (sys.executable) may run itself: followed then.
                        if candidate in self.files and (candidate != relative
                                                        or ('sys', ('executable',)) in facts['attributes']):
                            reach_module(candidate, main=True)
        python = {relative for relative, _ in reached}
        units = {}
        for relative, unit in reached:
            units.setdefault(relative, set()).add(unit)
        if key is not None:
            self._reached[key] = units
        paths = [path for relative, unit in reached
                 for path in self._module_symbols(relative)['units'].get(unit, {}).get('paths', ())]
        return python, self._match_data(constants, paths), state['uncertain'], constants

    def _binding_is_module(self, relative, binding):
        """True when a 'from' binding names a submodule (a bare use of it counts the whole module)."""
        if binding[0] != 'from':
            return True
        _, module, level, attribute = binding
        base = None
        if level:
            base = relative.rsplit('/', 1)[0] if '/' in relative else ''
            for _ in range(level - 1):
                base = base.rsplit('/', 1)[0] if '/' in base else ''
        return bool(self._exact_module(f'{module}.{attribute}' if module else attribute, base))

    def _maps(self):
        if self._data_maps is None:
            suffixes, folders, names = {}, {}, {}
            for relative in self.files:
                if relative.endswith('.py'):
                    continue
                parts = relative.split('/')
                for index in range(len(parts)):
                    suffixes.setdefault('/'.join(parts[index:]), set()).add(relative)
                names.setdefault(parts[-1], set()).add(relative)
                for end in range(1, len(parts)):
                    for index in range(end):
                        folders.setdefault('/'.join(parts[index:end]), set()).add(relative)
            self._data_maps = suffixes, folders, names
        return self._data_maps

    def _match_data(self, constants, paths):
        """Non-Python repository files that reached code names.

        A literal path (a string with '/', or the constant parts of ROOT / 'config' /
        'towns.json', Path(...), os.path.join(...)) names one file, or a whole folder
        when it ends at a folder, continues with a computed part or contains a
        wildcard; a bare file name names every file with that name.
        """
        suffixes, folders, names = self._maps()
        data = set()
        literals = list(paths)
        for text, _ in constants:
            if len(text) > 400 or '\n' in text:
                continue
            for token in re.findall(r'[A-Za-z0-9_.+-]+', text):
                data |= names.get(token, set())
            if '/' in text or '\\' in text:
                literals.append((text, False))
        keyed = []

        def folder_files(parts, literal):
            if len(parts) > 1:
                return set(folders.get(literal, set()))
            # One name ('src', 'config'): a folder at the top or next to the code
            # (Path(__file__).parent / 'name'), not every nested folder of that name.
            return {path for prefix in ('', 'tools/', 'src/') for path in folders.get(literal, set())
                    if path.startswith(prefix + literal + '/')}

        for text, open_ended in literals:
            if len(text) > 400 or '\n' in text:
                continue
            parts = [part for part in text.replace('\\', '/').split('/') if part not in ('', '.', '..')]
            for index, part in enumerate(parts):
                if any(mark in part for mark in '*?['):
                    parts, open_ended = parts[:index], True
                    break
            if not parts:
                continue
            literal = '/'.join(parts)
            if isinstance(open_ended, tuple):
                keyed.append((parts, literal, open_ended[1]))
                continue
            if not open_ended:
                data |= suffixes.get(literal, set())
            data |= folder_files(parts, literal)
        # FOLDER / row['KEY'] (scope 'units'): the files that rows of a JSON registry in that
        # folder, itself named by the code, give under KEY (config/towns.json rows name
        # config/balmora.json ...). No registry, or no such value: the whole folder.
        for parts, literal, key in keyed:
            candidates = folder_files(parts, literal)
            folders_seen = {path.rsplit('/', 1)[0] for path in candidates}
            registries = sorted(path for path in data if path.endswith('.json') and path.rsplit('/', 1)[0] in folders_seen
                                and path.rsplit('/', 1)[0].endswith(literal))
            named = set()
            for registry in registries:
                base = registry.rsplit('/', 1)[0] + '/'
                for value in self._json_values_for(registry, key):
                    named |= {path for path in candidates if path == posixpath.normpath(base + value)}
            data |= named if named else candidates
        return data

    def _json_values_for(self, relative, key):
        """Every string value stored under KEY anywhere in a JSON file of the repository."""
        if (relative, key) not in self._json_values:
            found = set()
            try:
                document = json.loads((self.root / relative).read_text(encoding='utf-8'))
            except (OSError, ValueError):
                document = None
            pending = [document]
            while pending:
                value = pending.pop()
                if isinstance(value, dict):
                    for name, item in value.items():
                        if name == key and isinstance(item, str):
                            found.add(item)
                        pending.append(item)
                elif isinstance(value, list):
                    pending.extend(value)
            self._json_values[(relative, key)] = found
        return self._json_values[(relative, key)]

    def unit_hashes(self, relative, units, top_format=None):
        """{unit: SHA-256 of its text} for UNITS of a module (the parts unit_digest hashes), None for a unit the
        module no longer has; None when the module is gone or cannot be read (B7 narrowed reuse)."""
        top_format = top_format or self.top_format
        if relative not in self.files:
            return None
        symbols = self._module_symbols(relative)
        if symbols.get('broken'):
            return None
        texts = self._unit_texts(relative, top_format)
        text = {'<top>': TOP_TEXT[top_format]}
        return {unit: (hashlib.sha256(texts[text.get(unit, unit)].encode('utf-8', 'surrogateescape')).hexdigest()
                       if text.get(unit, unit) in texts else None) for unit in sorted(units)
                if (relative, unit) not in SCHEDULING_UNITS}

    def selection(self, script, top_format=None):
        """({path: digest} a stage's fingerprint covers, uncertain).

        Scope 'units': a reached module counts as its import-time code plus the source of
        each reached function (unit_digest), so an edit to a function the stage never
        reaches keeps the fingerprint; data files and the other scopes: whole files.
        """
        python, data, uncertain = self.closure(script)
        files = self.files
        if uncertain:
            return dict(files), True
        units = self.reached_units(script) if self.scope == 'units' else None
        selected = {}
        for path in python | data:
            if path not in files:
                continue
            if units is not None and path in units and path.endswith('.py'):
                selected[path] = self.unit_digest(path, units[path], top_format)
            else:
                selected[path] = files[path]
        return selected, False

    def digest(self, script, exclude=()):
        """(digest, files, uncertain) of SCRIPT's selection; EXCLUDE: repository paths left out (a cache's own
        key code in that cache's keys, pass_cache.PASS_KEY_NEUTRAL)."""
        selected, uncertain = self.selection(script)
        selected = {path: value for path, value in selected.items() if path not in exclude}
        return digest_json(selected), len(selected), uncertain

    def entry_digest(self, script, function, exclude=()):
        """(digest, files, uncertain) of the code one function of SCRIPT can reach: the module's import-time code,
        the function, and everything they reach (scope 'units' or 'symbols'), not the script's main flow. A per-unit
        cache keyed by its worker function is not rekeyed by an edit elsewhere in the same tool. EXCLUDE: as in
        digest()."""
        if self.scope == 'modules':
            return self.digest(script, exclude)
        script = Path(script).resolve()
        key = '%s::%s' % (script, function)
        if key not in self._closures:
            start = script.relative_to(self.root.resolve()).as_posix()
            if function not in self._module_symbols(start)['units']:
                raise ValueError('No function %s in %s' % (function, start))
            python, data, uncertain, constants = self._closure_symbols(start, key, entry=function)
            self._closures[key] = (python, data, uncertain, environment_names(constants, uncertain))
        python, data, uncertain, _ = self._closures[key]
        files = self.files
        if uncertain:
            selected = {path: value for path, value in files.items() if path not in exclude}
            return digest_json(selected), len(selected), True
        units = self._reached.get(key) if self.scope == 'units' else None
        selected = {}
        for path in python | data:
            if path not in files or path in exclude:
                continue
            if units is not None and path in units and path.endswith('.py'):
                selected[path] = self.unit_digest(path, units[path])
            else:
                selected[path] = files[path]
        return digest_json(selected), len(selected), False


# --------------------------------------------------------------------------
# Static facts of one module (scope 'symbols')

INTROSPECTION_CALLS = {'getattr', 'hasattr', 'setattr', 'delattr', 'vars', 'dir', 'reload'}
DYNAMIC_IMPORT_CALLS = {'import_module', '__import__'}


def environment_names(constants, uncertain=False):
    """AMIWIND_* names in CONSTANTS; {ENV_ANY} when a name is built at run time (a bare prefix)."""
    if uncertain:
        return {ENV_ANY}
    found = set()
    for text, _ in constants:
        if ENV_PREFIX not in text:
            continue
        for match in re.finditer(r'AMIWIND_[A-Za-z0-9_]*', text):
            name = match.group(0)
            if ENV_NAME.fullmatch(name):
                found.add(name)
            else:  # 'AMIWIND_' or 'AMIWIND_X_' + computed rest
                return {ENV_ANY}
    return found


def _docstring_ids(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def _flatten_path(node):
    """Operands of a ROOT / 'a' / name chain, left to right."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _flatten_path(node.left) + _flatten_path(node.right)
    return [node]


# Path expressions with loop names (loop_choices) are read once per combination of the names'
# values; more combinations than this read the expression as before (computed parts).
MAX_PATH_CHOICES = 64


def loop_choices(walked):
    """{name: (text, ...)} for names that a unit binds only as the target of ONE for loop (or
    comprehension) over a written-out sequence, at a position where every element is a string:
    `for name, file, reader in [('Balmora', 'balmora.json', regions), ('Seyda Neen', 'seyda_area.json', seyda)]`
    makes file one of the two names. A path built from it (ROOT / 'config' / file) names those
    files, not the whole folder (BUILD-SURVEY-KEY-CONFIG-35: the world survey's key counted
    every file under config/). A name bound any other way in the unit (assignment, another
    loop, with/except/import/def/match, a parameter, global/nonlocal) has no choices, so a key
    never under-declares."""
    stores, other = {}, set()
    for node in walked:
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            stores[node.id] = stores.get(node.id, 0) + 1
        elif isinstance(node, ast.ExceptHandler) and node.name:
            other.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            other.update((alias.asname or alias.name).split('.')[0] for alias in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            other.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            other.update(node.names)
        elif isinstance(node, ast.arg):
            other.add(node.arg)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            other.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            other.add(node.rest)
    found = {}
    for node in walked:
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            continue
        # The sequence is written out ([...] or (...)); only the target's string positions must be
        # literal (`for name, file, reader in [('Balmora', 'balmora.json', regions), ...]`).
        if not isinstance(node.iter, (ast.List, ast.Tuple)) or not node.iter.elts:
            continue
        target = node.target
        if isinstance(target, ast.Name):
            positions = [(None, target.id)]
        elif isinstance(target, (ast.Tuple, ast.List)) and all(isinstance(e, ast.Name) for e in target.elts):
            positions = list(enumerate(e.id for e in target.elts))
        else:
            continue
        for index, name in positions:
            options = []
            for element in node.iter.elts:
                if index is not None:
                    if not isinstance(element, (ast.Tuple, ast.List)) or len(element.elts) != len(target.elts)                             or any(isinstance(e, ast.Starred) for e in element.elts):
                        options = None
                        break
                    element = element.elts[index]
                if not (isinstance(element, ast.Constant) and isinstance(element.value, str)):
                    options = None
                    break
                options.append(element.value)
            if options is not None:
                found[name] = tuple(dict.fromkeys(options))
    return {name: options for name, options in found.items() if stores.get(name) == 1 and name not in other}


def _literal_runs(operands, constants=None, refined=True, choices=None):
    if refined and choices:
        # A loop name with known string values (loop_choices): one reading per combination.
        chosen = [index for index, operand in enumerate(operands)
                  if isinstance(operand, ast.Name) and operand.id in choices and operand.id not in (constants or {})]
        combinations = 1
        for index in chosen:
            combinations *= len(choices[operands[index].id])
        if chosen and combinations <= MAX_PATH_CHOICES:
            from itertools import product
            runs = []
            for values in product(*(choices[operands[index].id] for index in chosen)):
                expanded = list(operands)
                for index, value in zip(chosen, values):
                    expanded[index] = ast.Constant(value)
                runs.extend(_literal_runs(expanded, constants, refined))
            return runs
    """[(path, open_ended)] for each run of string constants in a path expression.

    Constants inside a computed operand ('a' if x else 'b', f'{name}.json') count as
    literals of their own (a file or a folder with that name). A module constant
    (REGISTRY = 'towns.json') counts as its value. A run followed by a lookup with a
    constant key (ROOT / 'config' / row['config']) is open-ended with ('key', 'config'):
    the files that registry rows in that folder name under that key (_match_data); the
    key itself is not a path.
    """
    runs, current = [], []
    constants = (constants or {}) if refined else {}
    for operand in operands:
        if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
            current.append(operand.value)
            continue
        if isinstance(operand, ast.Name) and operand.id in constants:
            current.append(constants[operand.id])
            continue
        keyed = (refined and isinstance(operand, ast.Subscript) and isinstance(operand.slice, ast.Constant)
                 and isinstance(operand.slice.value, str))
        runs.extend((node.value, False) for node in ast.walk(operand)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and not (keyed and node is operand.slice))
        if current:
            runs.append(('/'.join(current), ('key', operand.slice.value) if keyed else True))
            current = []
    if current:
        runs.append(('/'.join(current), False))
    return runs


def module_constants(tree):
    """{NAME: 'text'}: upper-case names bound once in a module, at its top level, to a string."""
    if tree is None:
        return {}
    bound = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        bound[name.id] = bound.get(name.id, 0) + 1
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.NamedExpr, ast.Global,
                               ast.Nonlocal, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import,
                               ast.ImportFrom, ast.ExceptHandler)):
            names = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names = [node.name]
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                names = list(node.names)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [(alias.asname or alias.name).split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ExceptHandler) and node.name:
                names = [node.name]
            elif isinstance(node, ast.NamedExpr):
                names = [node.target.id]
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                names = [n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)]
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                names = [n.id for item in node.items if item.optional_vars is not None
                         for n in ast.walk(item.optional_vars) if isinstance(n, ast.Name)]
            for name in names:
                bound[name] = bound.get(name, 0) + 2  # never a constant
    found = {}
    for statement in tree.body:
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)
                and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str)):
            name = statement.targets[0].id
            if name.isupper() and bound.get(name) == 1:
                found[name] = statement.value.value
    return found


def _is_sys_path(node):
    """sys.path, or a slice/item of it."""
    if isinstance(node, ast.Subscript):
        node = node.value
    return (isinstance(node, ast.Attribute) and node.attr == 'path' and isinstance(node.value, ast.Name)
            and node.value.id == 'sys')


def import_path_nodes(walked):
    """ids of every node inside an import search path entry: sys.path.insert/append/extend(...) arguments
    and values assigned to sys.path (or a slice of it), site.addsitedir(...). Such a folder is where Python
    looks for modules (the imports themselves are followed), not a data file the code reads: counting
    Path(__file__).parents[1] / 'tools' as a read named every non-Python file under tools/, so a new bug
    page (tools/release-files.json) rebuilt interior, census, harvest and chim (BUILD-KEY-OVERBROAD-33)."""
    found = set()
    for node in walked:
        values = []
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ('insert', 'append', 'extend') and _is_sys_path(node.func.value):
                values = node.args
            elif node.func.attr == 'addsitedir' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'site':
                values = node.args
        elif isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(_is_sys_path(target) for target in targets):
                values = [node.value]
        for value in values:
            found.update(id(inner) for inner in ast.walk(value))
    # for p in (ROOT / 'tools', ROOT / 'src'): sys.path.insert(0, str(p)): the loop's folders are search paths
    # when its variable is only ever used as one.
    for node in walked:
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        name = node.target.id
        uses = [inner for statement in node.body for inner in ast.walk(statement)
                if isinstance(inner, ast.Name) and inner.id == name]
        if uses and all(id(use) in found or _search_path_use(node.body, use) for use in uses):
            found.update(id(inner) for inner in ast.walk(node.iter))
    return found


def _search_path_use(body, use):
    """USE (a Name) is an argument of sys.path.remove/insert/append or of a str() inside one, or the
    subject of an `in sys.path` test."""
    for statement in body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and _is_sys_path(node.func.value)                     and node.func.attr in ('insert', 'append', 'remove', 'index', 'count')                     and any(use is inner for argument in node.args for inner in ast.walk(argument)):
                return True
            if isinstance(node, ast.Compare) and any(_is_sys_path(c) for c in node.comparators)                     and any(use is inner for inner in ast.walk(node.left)):
                return True
    return False


def _unit_facts(nodes, docstrings, constants=None, refined=True):
    facts = {'names': set(), 'attributes': set(), 'imports': [], 'bindings': {}, 'star': [], 'constants': [],
             'paths': [], 'whole': set(), 'globals': False, 'dynamic_imports': [], 'uncertain': False}
    under_attribute, path_parts, inner = set(), set(), set()
    walked = [node for root in nodes for node in ast.walk(root)]
    search_paths = import_path_nodes(walked) if refined else set()
    choices = loop_choices(walked) if refined else {}
    for node in walked:
        if refined and isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and id(node) in inner:
            continue  # part of a longer ROOT / 'a' / 'b' chain, read whole below (ast.walk is breadth-first)
        if id(node) in search_paths:
            continue  # an import search path entry (import_path_nodes), not a data read
        if isinstance(node, ast.Attribute):
            chain, value = [node.attr], node.value
            while isinstance(value, ast.Attribute):
                chain.append(value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                facts['attributes'].add((value.id, tuple(reversed(chain))))
            if isinstance(node.value, ast.Name):
                under_attribute.add(id(node.value))
                if node.attr == '__dict__':  # module.__dict__[name]: the whole module
                    facts['whole'].add(node.value.id)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            # Only the whole chain counts: ROOT / 'config' / 'towns.json' names one file, while its
            # inner ROOT / 'config' read alone would name the whole folder (BUILD-CACHE-OVERBROAD-33).
            nested = [node.left, node.right]
            while nested:
                part = nested.pop()
                if isinstance(part, ast.BinOp) and isinstance(part.op, ast.Div):
                    inner.add(id(part))
                    nested += [part.left, part.right]
            operands = _flatten_path(node)
            path_parts.update(id(operand) for operand in operands)
            facts['paths'].extend(_literal_runs(operands, constants, refined, choices))
        elif isinstance(node, ast.Call):
            function = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            if function in PATH_CALLS:
                path_parts.update(id(argument) for argument in node.args)
                facts['paths'].extend(_literal_runs(node.args, constants, refined, choices))
            if function in INTROSPECTION_CALLS:
                if node.args and isinstance(node.args[0], ast.Name):
                    facts['whole'].add(node.args[0].id)
                elif function == 'vars' and not node.args:
                    facts['globals'] = True
            elif function in ('globals', 'locals'):
                facts['globals'] = True
            elif function in DYNAMIC_IMPORT_CALLS:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    facts['dynamic_imports'].append(node.args[0].value)
                else:
                    facts['uncertain'] = True
            elif (isinstance(node.func, ast.Name) and function in ('eval', 'exec')) or function in ('run_path', 'run_module'):
                facts['uncertain'] = True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                facts['imports'].append((alias.name, 0, None))
                if alias.asname:
                    facts['bindings'][alias.asname] = ('module', alias.name, 0)
                else:
                    first = alias.name.split('.')[0]
                    facts['bindings'][first] = ('module', first, 0)
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            facts['imports'].append((node.module or '', node.level, names))
            for alias in node.names:
                if alias.name == '*':
                    facts['star'].append((node.module or '', node.level))
                else:
                    facts['bindings'][alias.asname or alias.name] = ('from', node.module or '', node.level, alias.name)
    for node in walked:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and id(node) not in under_attribute:
            facts['names'].add(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            facts['constants'].append((node.value, '/' in node.value or id(node) in path_parts))
        elif isinstance(node, (ast.BinOp, ast.JoinedStr)):
            joined = folded_string(node)
            if joined is not None:
                facts['constants'].append((joined, '/' in joined or id(node) in path_parts))
    return facts


def folded_string(node):
    """The text of a string built only from literals ('cell_progress' + '_build.py', f'{"a"}b.py'), else None.

    A name written in parts is still a name: a script started as a subprocess, or a data file, named that
    way is followed like a plain literal (BUILD-CHIM-KEY-UNDERDECLARED-35: the CHIM stage started
    tools/cell_progress_build.py by a name in two parts, so its fingerprint left out the 8 files it ran)."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = folded_string(node.left), folded_string(node.right)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                if value.format_spec is not None or value.conversion != -1:
                    return None
                value = value.value
            text = folded_string(value)
            if text is None:
                return None
            parts.append(text)
        return ''.join(parts)
    return None


def _is_main_guard(test):
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    sides = [test.left, test.comparators[0]]
    return (any(isinstance(side, ast.Name) and side.id == '__name__' for side in sides)
            and any(isinstance(side, ast.Constant) and side.value == '__main__' for side in sides))


def lazy_tables(tree):
    """{id(statement): name} of top-level literal tables: `NAME = {...}`, [...], (...) or a set whose value is a
    literal (ast.literal_eval) and whose NAME no other top-level statement binds. A table only matters to the code
    that reads it, so it is its own unit like a plain function: a stage whose reached code never names it does
    not hash it (BUILD-SCHEDULER-TABLE-KEY-35: the scheduler's DEPENDENCIES table in tools/build_parallel.py
    was import-time code of every stage). A module read whole (globals(), module.__dict__, `from m import *`)
    still reaches every table."""
    bound = {}
    for statement in tree.body:
        names = set()
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(statement.name)
        for node in ast.walk(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                names.add(node.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names.update((alias.asname or alias.name).split('.')[0] for alias in node.names)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                names.update(node.names)
        for name in names:
            bound[name] = bound.get(name, 0) + 1
    tables = {}
    for statement in tree.body:
        if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and isinstance(statement.value, (ast.Dict, ast.List, ast.Tuple, ast.Set))):
            continue
        name = statement.targets[0].id
        if name.startswith('__') or bound.get(name) != 1:
            continue
        try:
            ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            continue
        tables[id(statement)] = name
    return tables


def module_symbols(tree, text=None, refined=False):
    """{'units': {name: facts}, 'bindings', 'fallback', 'broken', 'texts'} for one parsed module.

    Units: '<top>' (what runs on import: statements, decorators, default values,
    class bodies), '<main>' (the `if __name__ == '__main__'` block) and one per
    undecorated top-level function. Classes and decorated definitions run with
    '<top>' (a decorator or metaclass may register them).

    TEXTS (with the module TEXT): the source each unit hashes as in scope 'units':
    a function's own lines; '<top>' the rest of the module (the main block, classes,
    decorated definitions, comments between definitions included) plus the default
    values of every function, which run on import. REFINED (scope 'units'): module
    string constants and keyed lookups count in path expressions (_literal_runs).
    """
    if tree is None:
        return {'units': {}, 'bindings': {}, 'fallback': {}, 'broken': True, 'texts': {}}
    docstrings = _docstring_ids(tree)
    constants = module_constants(tree) if refined else {}
    top, main, lazy = [], [], {}
    tables = lazy_tables(tree)
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and not statement.decorator_list:
            lazy.setdefault(statement.name, []).append(statement)
            top.extend([*statement.args.defaults, *(d for d in statement.args.kw_defaults if d is not None)])
            # A name defined twice (a def and an assignment) runs with the top level too.
        elif id(statement) in tables:
            lazy.setdefault(tables[id(statement)], []).append(statement)
        elif isinstance(statement, ast.If) and _is_main_guard(statement.test):
            main.extend(statement.body)
            top.extend(statement.orelse)
        else:
            top.append(statement)
    units = {'<top>': _unit_facts(top, docstrings, constants, refined),
             '<main>': _unit_facts(main, docstrings, constants, refined)}
    assigned = {target.id for statement in top for node in ast.walk(statement)
                if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign))
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
                if isinstance(target, ast.Name)}
    for name, statements in lazy.items():
        units[name] = _unit_facts(statements, docstrings, constants, refined)
        if name in assigned:  # rebound at import time: keep it with the top level
            units['<top>']['names'].add(name)
    fallback = {}
    for name, facts in units.items():
        if name != '<top>':
            for key, value in facts['bindings'].items():
                fallback.setdefault(key, value)  # `global X; import x as X` inside a function
    return {'units': units, 'bindings': dict(units['<top>']['bindings']), 'fallback': fallback, 'broken': False,
            'texts': unit_texts(tree, text, lazy) if text is not None else {}}


def unit_texts(tree, text, lazy):
    """{unit: source} for scope 'units' (see module_symbols)."""
    lines = text.splitlines(keepends=True)
    texts = {}
    for name, statements in lazy.items():
        texts[name] = '\n'.join(''.join(lines[statement.lineno - 1:statement.end_lineno]).rstrip()
                                for statement in statements)
    # '<top>': the source of each top-level statement that is not a plain function (decorators included),
    # in order; blank lines and comments between statements do not count (a whitespace-only edit, such as
    # a removed blank line at the end of a module, keeps every fingerprint). A function's default values
    # run on import: they stay with '<top>', in order.
    # Two forms (TOP_FORMATS): format 1 lists every plain function's default values, so adding a function
    # changed the module's import-time code and every key that reached it; format 2 lists only defaults that
    # run code on import (anything but literals). A literal default is part of its function's own text, which
    # only that function's callers reach (BUILD-KEY-FUNCTION-DEFAULTS-TOP-36).
    top, top2 = [], []
    tables = lazy_tables(tree)
    for statement in tree.body:
        if id(statement) in tables:
            continue  # a literal table: its own unit (lazy_tables)
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and statement.name in lazy \
                and not statement.decorator_list:
            defaults = [*statement.args.defaults, *(d for d in statement.args.kw_defaults if d is not None)]
            line = f'\0defaults {statement.name}: ' + ' | '.join(ast.dump(d) for d in defaults) + '\n'
            top.append(line)
            if not all(_literal(d) for d in defaults):
                top2.append(line)
            continue
        first = min([statement.lineno] + [d.lineno for d in getattr(statement, 'decorator_list', ())])
        source = ''.join(lines[first - 1:statement.end_lineno]).rstrip() + '\n'
        top.append(source)
        top2.append(source)
    texts['<top>'] = ''.join(top)
    texts[TOP_TEXT[2]] = ''.join(top2)
    return texts


def _literal(node):
    """True for a default value that runs no code on import (a literal; also negative numbers, containers)."""
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True


# --------------------------------------------------------------------------
# Fingerprints

def run_strings(run):
    run = Path(run)
    found = {str(run)}
    try:
        found.add(str(run.resolve()))
    except OSError:
        pass
    return sorted(found, key=len, reverse=True)


def under_run(value, run):
    for prefix in run_strings(run):
        if value == prefix or value.startswith(prefix + os.sep) or value.startswith(prefix + '/'):
            return value[len(prefix):].lstrip('/\\').replace('\\', '/') or '.'
    return None


def locations(run, metadata=None, index=None):
    """[(absolute prefix, token, prefix match)] normalized in fingerprints, longest first.

    Fingerprints hold content, not places: the run, the checkout, the game data, the
    tools, the interpreter and the workspace become tokens, so a moved workspace or
    checkout keeps every fingerprint (BUILD-CACHE-ABSOLUTE-PATHS-33).
    """
    metadata = metadata or {}
    rows = [(value, '{RUN}', True) for value in run_strings(run)]
    root = Path(index.root if index is not None else ROOT)
    rows += [(value, '{REPO}', True) for value in {str(root), str(root.resolve())}]
    if metadata.get('data_files'):
        data = Path(str(metadata['data_files']))
        rows += [(value, '{DATA}', True) for value in {str(data), str(data.resolve())}]
    for tool, path in sorted((metadata.get('tools') or {}).items()):
        rows += [(str(Path(path)), '{TOOL:' + tool + '}', False),
                 (str(Path(path).parent), '{TOOLDIR:' + tool + '}', False)]
    run = Path(run)
    if run.parent.name == 'build':
        workspace = run.parent.parent
        rows += [(value, '{WORKSPACE}', True) for value in {str(workspace), str(workspace.resolve())}]
        # A storage pool named elsewhere (--storage-pool-dir, AMIWIND_STORAGE_POOL) is the same content-addressed
        # store as the default WORKSPACE/cache/asset-pool-v1: the same token, so naming it keeps every key.
        pool = metadata.get('storage_pool_dir')
        if pool:
            rows += [(value, POOL_TOKEN, True) for value in {str(pool), str(Path(pool).resolve())}
                     if Path(value) != workspace / 'cache' / 'asset-pool-v1']
    for value in {sys.executable, str(Path(sys.executable).resolve())}:
        rows.append((value, '{PYTHON}', False))
    return sorted(rows, key=lambda row: len(row[0]), reverse=True)


def storage_pool_roots(run, metadata=None):
    """The shared storage pool folders a build's commands can name (resolved): the configured one
    (metadata storage_pool_dir: --storage-pool-dir, AMIWIND_STORAGE_POOL, the build config) and the default
    WORKSPACE/cache/asset-pool-v1 of a run inside a workspace (tools/storage_pool.resolve_dir)."""
    roots = []
    pool = (metadata or {}).get('storage_pool_dir')
    if pool:
        roots.append(Path(str(pool)))
    run = Path(run)
    if run.parent.name == 'build':
        roots.append(run.parent.parent / 'cache' / 'asset-pool-v1')
    result = []
    for root in roots:
        for value in (root, _resolved(root)):
            if value not in result:
                result.append(value)
    return result


def _resolved(path):
    try:
        return path.resolve()
    except OSError:
        return path


def in_storage_pool(path, run, metadata=None):
    """True when PATH is the shared storage pool or a folder/file inside it (BUILD-POOL-ARG-UNFINGERPRINTED-35)."""
    path = Path(path)
    candidates = {path, _resolved(path)}
    for root in storage_pool_roots(run, metadata):
        for candidate in candidates:
            if candidate == root or root in candidate.parents:
                return True
    return False


def normalize_path(part, rows):
    """PART with its absolute location replaced by a token, or None when it names no known place."""
    for prefix, token, nested in rows:
        if part == prefix:
            return token
        if nested and (part.startswith(prefix + os.sep) or part.startswith(prefix + '/')):
            return token + '/' + part[len(prefix):].lstrip(SEPARATORS).replace(os.sep, '/')
    return None


def normalize_command(command, run, metadata=None, index=None):
    rows = locations(run, metadata, index)
    result = []
    skip_value = False
    for part in map(str, command):
        if skip_value:
            result.append('{JOBS}')
            skip_value = False
            continue
        if part == '--jobs':
            skip_value = True
            result.append(part)
            continue
        normalized = normalize_path(part, rows)
        if normalized is None and os.path.isabs(part) and os.path.exists(part):
            normalized = '{EXTERNAL}'  # counted by content in external_inputs
        result.append(part if normalized is None else normalized)
    return result


def stage_script(command):
    for part in map(str, command[1:3]):
        if part.endswith('.py'):
            return Path(part)
    return None


def external_inputs(name, command, run, metadata, skip_hashing=False, index=None):
    """{option=location: digest} of the paths outside the run named on the command line."""
    data_files = str(metadata.get('data_files') or '') or None
    tools = {str(Path(path)) for path in (metadata.get('tools') or {}).values()}
    tool_dirs = {str(Path(path).parent) for path in tools}
    rows = locations(run, metadata, index)
    result, problems = {}, []
    previous = None
    for position, part in enumerate(map(str, command)):
        option, previous = previous, part
        if position < 2 or part.startswith('-') or under_run(part, run) is not None:
            continue  # Interpreter and stage script (source digest), options, run paths.
        path = Path(part)
        if not path.is_absolute() or not path.exists():
            continue
        if str(path) in tools or str(path) in tool_dirs or path.resolve() == Path(sys.executable).resolve():
            continue
        if data_files and (str(path) == data_files or str(path).startswith(data_files.rstrip(SEPARATORS) + os.sep)):
            continue
        key = f'{option or "arg"}={normalize_path(part, rows) or "{EXTERNAL}"}'
        while key in result:
            key += '+'
        try:
            inside = path.resolve().relative_to((index.root if index is not None else ROOT).resolve()).as_posix()
        except ValueError:
            inside = None
        if inside is not None and index is not None:
            # A repository file or folder named directly (a font, a config file).
            prefix = '' if inside == '.' else inside + '/'
            result[key] = digest_json({p: h for p, h in index.files.items() if p == inside or p.startswith(prefix)})
            continue
        if (name, option) in CONTENT_ADDRESSED or skip_hashing:
            result[key] = 'not hashed (content-addressed cache)' if not skip_hashing else 'not hashed'
            continue
        if in_storage_pool(path, run, metadata):
            # Checked after the stage table so the media and intro keys stay as they were.
            result[key] = POOL_CONTENT
            continue
        if path.is_file():
            result[key] = sha256_file(path)
            continue
        total, hashes = 0, {}
        for file in sorted(p for p in path.rglob('*') if p.is_file()):
            total += file.stat().st_size
            if total > EXTERNAL_DIRECTORY_LIMIT:
                problems.append(f'{key}: folder larger than {EXTERNAL_DIRECTORY_LIMIT // 1024 ** 2} MiB is not fingerprinted')
                break
            hashes[file.relative_to(path).as_posix()] = sha256_file(file)
        result[key] = digest_json(hashes)
    return result, problems


def stage_environment(script, index):
    """The AMIWIND_* variables a stage's code can read, with their values (None = unset).

    Only names the reached code mentions count (BUILD-ENV-FINGERPRINT-GLOBAL-33): the
    stair rule reaches the converters that read it, not media or music. Code that
    builds names at run time, and commands that are not repository scripts, get every
    AMIWIND_* variable. Worker-count and bookkeeping variables never count.
    """
    names = index.environment_names(script) if script is not None and script.is_file() else {ENV_ANY}
    if ENV_ANY in names:
        environment = {key: value for key, value in sorted(os.environ.items())
                       if key.startswith(ENV_PREFIX) and key not in IGNORED_ENV}
    else:
        environment = {key: os.environ.get(key) for key in sorted(names) if key not in IGNORED_ENV}
    if os.environ.get('PYTHONHASHSEED'):
        environment['PYTHONHASHSEED'] = os.environ['PYTHONHASHSEED']
    return environment


def stage_components(name, command, run, metadata, index, dependencies, fingerprints):
    command = [str(part) for part in command]
    components = {'stage': name, 'schema': CACHE_SCHEMA, 'command': normalize_command(command, run, metadata, index)}
    problems = []
    script = stage_script(command)
    if script is not None and script.is_file():
        selected, uncertain = index.selection(script)
        scope = 'all files (dynamic code)' if uncertain else {'units': 'reachable functions', 'symbols': 'reachable code',
                                                              'modules': 'import closure'}[index.scope]
        components['sources'] = {'digest': digest_json(selected), 'files': len(selected), 'scope': scope}
        if not uncertain:
            # Per file, so `explain` names the files that changed (BUILD-CACHE-OVERBROAD-33).
            components['sources']['by_file'] = selected
            if index.top_format != 1:
                # The same files in the import-time form of format 1, for reuse sources fingerprinted with it
                # (comparable); kept out of the fingerprint itself.
                PREVIOUS_SOURCES[(str(run), name)] = index.selection(script, 1)[0]
    else:
        components['sources'] = {'digest': digest_json(dict(index.files)), 'files': len(index.files), 'scope': 'all files (not a repository tool)'}
    tools = metadata.get('tools') or {}
    tool_hashes = metadata.get('tool_sha256') or {}
    joined = '\0'.join(command)
    components['tools'] = {tool: tool_hashes.get(tool) for tool, path in sorted(tools.items())
                           if str(path) in joined or str(Path(path).parent) in command}
    if '--data-files' in command:
        components['game_inputs'] = digest_json(metadata.get('input_sha256') or {})
    external, external_problems = external_inputs(name, command, run, metadata, skip_hashing=name in NON_REUSABLE,
                                                  index=index)
    problems += external_problems
    components['external_inputs'] = external
    components['environment'] = stage_environment(script, index)
    components['python'] = {'version': sys.version, 'machine': platform.machine(),
                            'packages': {row['name']: row.get('detected') for row in metadata.get('version_comparison', [])
                                         if row.get('kind') == 'package'}}
    components['dependencies'] = {dep: fingerprints[dep] for dep in sorted(dependencies)}
    # Quick test builds: the exclusion groups that change this stage (tools/build_exclusions.py).
    # Only when there are any, so the fingerprints of complete builds stay as they were.
    from build_exclusions import stage_groups
    excluded = stage_groups(name, (metadata.get('excluded_content') or {}).get('groups') or [])
    if excluded:
        components['excluded_content'] = excluded
    return components, problems


def fingerprint_steps(steps, run, metadata, index=None, dependencies=None):
    """({stage: fingerprint}, {stage: components}, {stage: [problems]}) for every stage."""
    index = index or SourceIndex(top_format=STAGE_TOP_FORMAT)
    if dependencies is None:
        try:
            from build_parallel import plan_skipped, stage_dependencies
            dependencies = stage_dependencies(steps, plan_skipped(metadata))
        except (ImportError, ValueError):
            names = [name for name, _ in steps]
            dependencies = {name: tuple(names[i - 1:i]) for i, name in enumerate(names)}
    commands = dict(steps)
    fingerprints, components, problems = {}, {}, {}

    def visit(name, trail=()):
        if name in fingerprints:
            return
        if name in trail:
            raise ValueError('Build dependency cycle at ' + name)
        for dep in dependencies.get(name, ()):
            visit(dep, (*trail, name))
        parts, issues = stage_components(name, commands[name], run, metadata, index, dependencies.get(name, ()), fingerprints)
        components[name], problems[name] = parts, issues
        fingerprints[name] = digest_json(parts)

    for name, _ in steps:
        visit(name)
    return fingerprints, components, problems, {name: list(deps) for name, deps in dependencies.items()}


# {(run, stage): {file: digest}}: a stage's sources in import-time form 1 (TOP_FORMATS), set by stage_components.
PREVIOUS_SOURCES = {}


def source_format(components):
    """The import-time form (TOP_FORMATS) of a stage fingerprint's per-file sources, or None (no unit digests)."""
    values = [str(value) for value in (((components or {}).get('sources') or {}).get('by_file') or {}).values()]
    for top_format in sorted(UNIT_PREFIX, reverse=True):
        if any(value.startswith(UNIT_PREFIX[top_format]) for value in values):
            return top_format
    return None


def comparable(old_components, new_components, run, name):
    """NEW_COMPONENTS as OLD_COMPONENTS' import-time form (TOP_FORMATS) sees them: a reuse source fingerprinted
    with format 1 is compared with this checkout's format-1 digests, so a change of form alone rebuilds nothing
    while a real edit still shows (BUILD-KEY-FUNCTION-DEFAULTS-TOP-36). Unchanged when the forms agree."""
    if source_format(old_components) != 1 or source_format(new_components) in (None, 1):
        return new_components
    previous = PREVIOUS_SOURCES.get((str(run), name))
    if previous is None:
        return new_components
    sources = dict(new_components['sources'], by_file=previous, digest=digest_json(previous))
    return dict(new_components, sources=sources)


def comparable_all(components, old_details, run):
    """{stage: comparable components} for every stage (see comparable)."""
    return {name: comparable(old_details.get(name), parts, run, name) for name, parts in components.items()}


def explain(old_components, new_components):
    """Which components of a stage fingerprint changed (for reports and refusals)."""
    changed = []
    for key in sorted(set(old_components) | set(new_components)):
        if old_components.get(key) != new_components.get(key):
            if key == 'dependencies':
                deps = [d for d in set(old_components.get(key, {})) | set(new_components.get(key, {}))
                        if old_components.get(key, {}).get(d) != new_components.get(key, {}).get(d)]
                changed.append('dependency ' + ', '.join(sorted(deps)))
            elif key == 'sources' and 'by_file' in (old_components.get(key) or {}) \
                    and 'by_file' in (new_components.get(key) or {}):
                old, new = old_components[key]['by_file'], new_components[key]['by_file']
                files = sorted(path for path in set(old) | set(new) if old.get(path) != new.get(path))
                more = f', +{len(files) - 3} more' if len(files) > 3 else ''
                changed.append(f"sources ({', '.join(files[:3])}{more})" if files else key)
            else:
                changed.append(key)
    return changed


# --------------------------------------------------------------------------
# Output manifests (recorded by the profiling session for every stage)

def output_roots(command, run):
    """Run-folder paths named on the command line: what the stage may read or write there."""
    roots = set()
    for part in map(str, command):
        relative = under_run(part, run)
        if relative and relative != '.' and relative.split('/')[0] not in RUN_PRIVATE:
            roots.add(relative)
    ordered = sorted(roots)
    return [root for root in ordered if not any(root.startswith(other + '/') for other in ordered if other != root)]


def snapshot(run, roots):
    """{relative path: (size, mtime_ns, inode, mode, link)} and directories under ROOTS."""
    run = Path(run)
    files, directories = {}, set()

    def visit(path, relative):
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            return
        if stat_module.S_ISLNK(info.st_mode):
            files[relative] = (info.st_size, info.st_mtime_ns, info.st_ino, info.st_mode, os.readlink(path))
        elif stat_module.S_ISDIR(info.st_mode):
            directories.add(relative)
            with os.scandir(path) as entries:
                for entry in entries:
                    visit(entry.path, relative + '/' + entry.name)
        elif stat_module.S_ISREG(info.st_mode):
            files[relative] = (info.st_size, info.st_mtime_ns, info.st_ino, info.st_mode, None)

    for root in roots:
        visit(run / root, root)
    return files, directories


def hash_files(run, paths, workers=None):
    workers = workers or min(8, os.cpu_count() or 1)
    run = Path(run)
    if not paths:
        return {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(paths, pool.map(lambda relative: sha256_file(run / relative), paths)))


def input_files(command, run):
    """Existing regular files under the run named on the command line (checked before reuse)."""
    found = []
    for part in map(str, command):
        relative = under_run(part, run)
        if relative and relative != '.' and (Path(run) / relative).is_file():
            found.append(relative)
    return sorted(set(found))


# --------------------------------------------------------------------------
# Read trace: every stage run checks that its fingerprint covered what it read

from build_profile import READS_FOLDER, TRACE_ENV, TRACE_HOOK_FOLDER, reads_path, trace_environment  # noqa: E402
# Written into the run (profile/trace-hook/sitecustomize.py) and put first on the stage's
# PYTHONPATH by the stage wrapper. It only observes: every Python process of the stage
# (workers and repository tools it starts included) appends the repository files it opens
# for reading, and Python code it loads from outside the checkout, to one list.
TRACE_HOOK = '''# Stage read trace (tools/build_cache.py). Observes file opens; never changes them.
import os
import sys


def _install():
    target = os.environ.get('AMIWIND_STAGE_TRACE', '')
    if not target or target == 'off':
        return
    root = ROOT.rstrip('/') + '/'
    outside = [path.rstrip('/') + '/' for path in os.environ.get('PYTHONPATH', '').split(os.pathsep)
               if path and os.path.isabs(path) and not (path.rstrip('/') + '/').startswith(root)
               and not path.rstrip('/').endswith('/' + HOOK_FOLDER)]
    try:
        handle = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    except OSError:
        return
    seen = set()
    written = set()
    copying = set()
    run = globals().get('RUN')
    run = run.rstrip('/') + '/' if run else None
    diagnostic_names = globals().get('DIAGNOSTIC') or ()
    # Storage pool reads ('%' lines, BUILD-POOL-ARG-UNFINGERPRINTED-35): the pool is not fingerprinted by
    # content, so every read of it must be a keyed lookup (keys/NAMESPACE/..) or a verified object (objects/..).
    pools = [path.rstrip('/') + '/' for path in globals().get('POOLS') or ()]
    fallback = os.environ.get('AMIWIND_CACHE_FALLBACK', '')
    if fallback and os.path.isabs(fallback):
        pools.append(fallback.rstrip('/') + '/asset-pool-v1/')

    # Trace form 2 (B7, v0.0.42): directory listings of the checkout ('#L' / '#R' recursive lines) and the
    # processes a stage starts ('$' lines) are listed too, so a stage's record can name exactly what it ran
    # and read (Recorder.used_record): a listing can see a new file, a process the trace does not follow can
    # read anything.
    os.write(handle, b'#v2\\n')
    hook_folder = os.path.dirname(os.path.abspath(__file__))

    def listed(path, recursive=False):
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        if path is None:
            path = '.'
        if not isinstance(path, str):
            return
        path = os.path.abspath(path)
        if (path.rstrip('/') + '/').startswith(root):
            line = ('#R' if recursive else '#L') + path[len(root):].rstrip('/') + '\\n'
            if line not in seen:
                seen.add(line)
                os.write(handle, line.encode('utf-8', 'surrogateescape'))

    def globbed(args):
        pattern = os.fsdecode(args[0]) if isinstance(args[0], bytes) else args[0]
        if not isinstance(pattern, str):
            return
        base = args[2] if len(args) > 2 and isinstance(args[2], (str, bytes)) else None
        if base is not None and not os.path.isabs(pattern):
            pattern = os.path.join(os.fsdecode(base), pattern)
        parts = pattern.split('/')
        fixed = []
        for part in parts:
            if any(ch in part for ch in '*?['):
                break
            fixed.append(part)
        listed('/'.join(fixed) or '/', recursive=('**' in pattern and bool(args[1])) or len(fixed) < len(parts) - 1)

    def spawned(event, args):
        if event == 'os.system':
            command = os.fsdecode(args[0]) if isinstance(args[0], bytes) else str(args[0])
            exe, argv, cwd, env = command.split()[0] if command.split() else '', [command], None, None
        elif event == 'subprocess.Popen':
            executable, argv, cwd, env = args
            argv = [argv] if isinstance(argv, (str, bytes)) else list(argv or ())
            exe = executable or (argv[0] if argv else '')
        else:  # os.posix_spawn, os.exec: (path, argv, env)
            exe, argv, env = args[0], list(args[1] or ()), args[2] if len(args) > 2 else None
            cwd = None
        exe = os.path.basename(os.fsdecode(exe) if isinstance(exe, bytes) else str(exe))
        texts = [os.fsdecode(a) if isinstance(a, bytes) else str(a) for a in argv] + ([os.fsdecode(cwd) if isinstance(cwd, bytes) else str(cwd)] if cwd else [])
        flags = []
        if exe.startswith('python') or exe == os.path.basename(sys.executable):
            flags.append('py')
            if isinstance(env, dict) and (hook_folder not in [os.path.abspath(p) for p in str(
                    env.get('PYTHONPATH', '')).split(os.pathsep) if p] or env.get('AMIWIND_STAGE_TRACE') != target):
                flags.append('untraced')
        if any(t.startswith(root) or (' ' + root) in t for t in texts):
            flags.append('repo')
        os.write(handle, ('$' + exe + '\\t' + ','.join(flags) + '\\n').encode('utf-8', 'surrogateescape'))

    def is_diagnostic(path):
        return path.endswith('.log') or os.path.basename(path) in diagnostic_names

    def wrote(path):
        # Writes into the run folder ('>' lines): which of two stages running at the same time wrote a
        # file both saw change (Recorder.close; BUILD-REUSE-ATTRIBUTION-33).
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        if not isinstance(path, str) or run is None:
            return
        if not path.startswith('/'):
            path = os.path.abspath(path)
        if path.startswith(run) and path not in written:
            written.add(path)
            os.write(handle, ('>' + path[len(run):] + '\\n').encode('utf-8', 'surrogateescape'))

    def hook(event, args):
        if not args:
            return
        if event == 'shutil.copyfile':
            # A diagnostic copied byte for byte into another diagnostic (the scene chain's copytree of the
            # previous scene: bsp-scene/light.log -> npc-scene/light.log) is not read: its bytes only reach a
            # diagnostic, which no stage reads and no reuse compares (BUILD-SCENE-DIAGNOSTIC-COPY-35). The
            # copy's own open of the source is not listed; any other read of it still is.
            try:
                source, target = (os.fsdecode(os.fspath(part)) for part in args[:2])  # copytree passes DirEntry objects
                source, target = os.path.abspath(source), os.path.abspath(target)
                if run is not None and source.startswith(run) and is_diagnostic(source) and is_diagnostic(target):
                    copying.add(source)
            except Exception:  # noqa: BLE001 - tracing must never change the stage
                pass
            return
        if event in ('os.listdir', 'os.scandir'):
            try:
                # the import system lists every folder on its search path (FileFinder): not a read of the stage
                frame, depth = sys._getframe(1), 0
                while frame is not None and depth < 4:
                    if frame.f_code.co_filename.startswith('<frozen importlib'):
                        return
                    frame, depth = frame.f_back, depth + 1
                listed(args[0])
            except Exception:  # noqa: BLE001 - tracing must never change the stage
                pass
            return
        if event in ('glob.glob', 'glob.glob/2'):
            try:
                globbed(args)
            except Exception:  # noqa: BLE001
                pass
            return
        if event in ('subprocess.Popen', 'os.posix_spawn', 'os.exec', 'os.system'):
            try:
                spawned(event, args)
            except Exception:  # noqa: BLE001
                pass
            return
        if event != 'open':
            try:
                if event in ('os.rename', 'os.replace', 'os.link', 'os.symlink') and len(args) > 1:
                    wrote(args[1])
                elif event in ('os.remove', 'os.rmdir'):
                    wrote(args[0])
            except Exception:  # noqa: BLE001 - tracing must never change the stage
                pass
            return
        try:
            path, mode = args[0], args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            if isinstance(path, bytes):
                path = os.fsdecode(path)
            if not isinstance(path, str):
                return
            if isinstance(mode, str):
                if 'w' in mode or 'a' in mode or 'x' in mode or '+' in mode:
                    wrote(path)
                    return
            elif isinstance(flags, int) and flags & 3 in (os.O_WRONLY, os.O_RDWR):
                wrote(path)
                if flags & 3 == os.O_WRONLY:
                    return
            if not path.startswith('/'):
                path = os.path.abspath(path)
            if path in copying:
                copying.discard(path)  # the copy's own read (shutil.copyfile event above)
                return
            if path in seen:
                return
            seen.add(path)
            if run is not None and path.startswith(run) and is_diagnostic(path):
                # A run-folder diagnostic read by a stage ('<' lines): not allowed (Recorder.after).
                os.write(handle, ('<' + path[len(run):] + '\\n').encode('utf-8', 'surrogateescape'))
                return
            pool = next((prefix for prefix in pools if path.startswith(prefix)), None)
            if pool is not None:
                os.write(handle, ('%' + path[len(pool):] + '\\n').encode('utf-8', 'surrogateescape'))
                return
            if path.startswith(root):
                line = path[len(root):]
            elif path.endswith(('.py', '.pyc')) and any(path.startswith(prefix) for prefix in outside):
                line = '!' + path
            else:
                return
            os.write(handle, (line + '\\n').encode('utf-8', 'surrogateescape'))
        except Exception:  # noqa: BLE001 - tracing must never change the stage
            pass

    sys.addaudithook(hook)
    # Call trace (scope 'units'): the first run of each repository function is listed as
    # '@file<TAB>name' (its top-level function or class); each code object reports once,
    # then its event is switched off (sys.monitoring, Python 3.12+).
    monitoring = getattr(sys, 'monitoring', None)
    if monitoring is None:
        return
    for tool in (4, 3):
        try:
            monitoring.use_tool_id(tool, 'amiwind-stage-trace')
            break
        except ValueError:
            continue
    else:
        return

    def started(code, offset):
        try:
            path = code.co_filename
            if not path.startswith('/'):
                path = os.path.abspath(path)
            if path.startswith(root) and path.endswith('.py'):
                name = code.co_qualname.split('.', 1)[0]
                os.write(handle, ('@' + path[len(root):] + '\\t' + name + '\\n').encode('utf-8', 'surrogateescape'))
        except Exception:  # noqa: BLE001 - tracing must never change the stage
            pass
        return monitoring.DISABLE

    try:
        monitoring.register_callback(tool, monitoring.events.PY_START, started)
        monitoring.set_events(tool, monitoring.events.PY_START)
    except Exception:  # noqa: BLE001
        pass


_install()
# Keep the interpreter's own sitecustomize (if any) working.
_here = os.path.dirname(os.path.abspath(__file__))
_path = list(sys.path)
try:
    sys.path[:] = [entry for entry in sys.path if os.path.abspath(entry or '.') != _here]
    del sys.modules[__name__]
    import sitecustomize  # noqa: F401
except Exception:  # noqa: BLE001
    pass
finally:
    sys.path[:] = _path
'''


def write_trace_hook(run, root, pools=()):
    """Install the read-trace hook into RUN (profile/trace-hook); False when switched off. POOLS: the storage
    pool folders whose reads are listed as '%' lines (pool_read_problems)."""
    if os.environ.get(TRACE_ENV, '') == 'off' or os.name != 'posix':
        return False
    folder = Path(run) / 'profile' / TRACE_HOOK_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    (Path(run) / 'profile' / READS_FOLDER).mkdir(exist_ok=True)
    text = TRACE_HOOK.replace('import os\n', f'import os\n\nROOT = {str(Path(root).resolve())!r}\n'
                              f'RUN = {str(Path(run).resolve())!r}\n'
                              f'DIAGNOSTIC = {sorted(DIAGNOSTIC_NAMES)!r}\n'
                              f'HOOK_FOLDER = {TRACE_HOOK_FOLDER!r}\n'
                              f'POOLS = {sorted({str(Path(pool)) for pool in pools})!r}\n', 1)
    temporary = folder / 'sitecustomize.tmp'
    temporary.write_text(text)
    temporary.replace(folder / 'sitecustomize.py')
    return True


def stage_closures(steps, index):
    """{stage: sorted repository files its fingerprint covers, or None (all files)}."""
    result = {}
    root = index.root.resolve()
    for name, command in steps:
        command = [str(part) for part in command]
        script = stage_script(command)
        if script is None or not script.is_file():
            result[name] = None
            continue
        python, data, uncertain = index.closure(script)
        if uncertain:
            result[name] = None
            continue
        covered = set(python) | set(data)
        for part in command:
            path = Path(part)
            if path.is_absolute() and path.exists():
                try:
                    inside = path.resolve().relative_to(root).as_posix()
                except ValueError:
                    continue
                prefix = '' if inside == '.' else inside + '/'
                covered |= {p for p in index.files if p == inside or p.startswith(prefix)}
        result[name] = sorted(covered)
    return result


def stage_units(steps, index):
    """({stage: {python file: reached units}}, {python file: its function units}) for scope 'units'.

    Checked against the stage's call trace: a function that ran but whose source the
    fingerprint left out makes the stage's outputs not reusable (check_calls).
    """
    if index.scope != 'units':
        return {}, {}
    stages, modules = {}, {}
    for name, command in steps:
        script = stage_script([str(part) for part in command])
        if script is None or not script.is_file():
            continue
        python, _, uncertain = index.closure(script)
        if uncertain:
            continue
        reached = index.reached_units(script) or {}
        stages[name] = {path: sorted(units) for path, units in sorted(reached.items())}
        for path in reached:
            modules.setdefault(path, sorted(unit for unit in index._module_symbols(path)['units'] if not unit.startswith('<')))
    return stages, modules


def apply_module(path):
    """True for a repository module of the reuse step (APPLY_STEMS: build_cache.py apply and what it loads)."""
    folder, _, name = path.rpartition('/')
    return folder == 'tools' and name.endswith('.py') and name[:-3] in APPLY_STEMS


def check_calls(lines, reached, modules, run_inside=None):
    """Functions a stage ran ('@file<TAB>name' trace lines) whose source its fingerprint left out."""
    misses = set()
    for line in lines:
        if not line.startswith('@'):
            continue
        path, _, name = line[1:].rstrip('\n').partition('\t')
        if (run_inside and (path == run_inside or path.startswith(run_inside + '/'))) or path in OUTPUT_NEUTRAL:
            continue
        if path not in modules or name not in modules[path]:
            continue  # import-time code, a class or a decorated function: counted with the module ('<top>')
        if name not in reached.get(path, ()):
            misses.add(f'{path}:{name}')
    return sorted(misses)


# Trace lines that are not repository reads: '@' code entered, '>' run-folder writes, '<' run-folder diagnostics
# read, '%' storage pool reads, '#' form and directory listings, '$' processes started (B7).
TRACE_MARKS = ('@', '>', '<', '%', '#', '$')


def check_reads(lines, covered, files, root, run_inside=None):
    """(misses, uncovered, outside) of one stage's read list.

    misses: fingerprinted repository files the stage read but its fingerprint left out;
    uncovered: repository files no fingerprint covers (prose, tests) that it read;
    outside: Python code it loaded from outside the checkout.
    """
    misses, uncovered, outside = set(), set(), set()
    covered = None if covered is None else set(covered)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('!'):
            # The builder's own instrumentation (the stage wrapper, `build_cache.py apply` of a
            # reused stage) may load from another checkout on PYTHONPATH; it never changes outputs.
            folder, _, name = line[1:].rpartition('/')
            stem = name.split('.')[0]
            if stem not in APPLY_STEMS:  # report the source of a cached .pyc
                outside.add((folder[:-len('/__pycache__')] if folder.endswith('/__pycache__') else folder)
                            + '/' + stem + '.py')
            continue
        parts = line.split('/')
        if '__pycache__' in parts:
            at = parts.index('__pycache__')
            if at + 1 < len(parts) and parts[-1].endswith('.pyc'):
                line = '/'.join(parts[:at] + [parts[-1].split('.')[0] + '.py'])
                parts = line.split('/')
        if (run_inside and (line == run_inside or line.startswith(run_inside + '/'))) or parts[0] in SKIP_DIRECTORIES - {'tests'} \
                or parts[0].startswith('.') or line in OUTPUT_NEUTRAL:
            continue
        if line in files:
            if covered is not None and line not in covered:
                misses.add(line)
        elif not any(part.startswith('.') for part in parts) and (Path(root) / line).is_file():
            uncovered.add(line)
    return sorted(misses), sorted(uncovered), sorted(outside)


def pool_read_problems(lines):
    """(problems, summary) of a stage's storage pool reads ('%' trace lines, paths inside the pool).

    The pool is not fingerprinted by content (in_storage_pool): a stage may read it only through a keyed lookup
    (tools/file_cache.py: keys/NAMESPACE/KK/KEY.json, the key a hash of inputs the stage's own fingerprint
    covers) and the verified objects such a key names (objects/KK/SHA256). Any other pool file read is an input
    no fingerprint covers (BUILD-POOL-ARG-UNFINGERPRINTED-35). summary: {'objects': n, 'keys': {namespace: n}}.
    """
    problems, keys, objects = [], {}, 0
    for line in lines:
        if not line.startswith('%'):
            continue
        parts = line[1:].rstrip('\n').split('/')
        if len(parts) == 3 and parts[0] == 'objects' and len(parts[1]) == 2 and parts[2].startswith(parts[1]):
            objects += 1
        elif len(parts) >= 4 and parts[0] == 'keys' and parts[-1].endswith('.json') \
                and len(parts[-2]) == 2 and parts[-1].startswith(parts[-2]):
            namespace = '/'.join(parts[1:-2])
            keys[namespace] = keys.get(namespace, 0) + 1
        else:
            problems.append('/'.join(parts))
    summary = {'objects': objects, 'keys': dict(sorted(keys.items()))} if objects or keys else {}
    return sorted(set(problems)), summary


# --------------------------------------------------------------------------
# What a stage really used (B7, v0.0.42; BUILD-REUSE-KEYS-TOO-BROAD-35)
#
# A stage's key covers everything its code CAN reach (functions, data files named in its code, whole folders
# named with a computed part). A stage that ran records, from its trace (form 2), what it DID use: every
# repository function and module top it ran (by the SHA-256 of its text), every repository file it read (by
# SHA-256) and every repository folder it listed (by the SHA-256 of its names). The stage's outputs are a
# function of its inputs (the other parts of the key) and of exactly this code and these files: with the same
# inputs it runs the same code and reads the same files again. So when a later key differs only in its sources,
# and every unit, file and listing of the record is unchanged, the stage is reused (narrowed reuse); the reuse
# plan says so and names the changed files the stage never used. A record is complete only when the trace saw
# every process of the stage: a Python process started without the trace, or another program given a checkout
# path, leaves it incomplete, and the key is compared whole as before. AMIWIND_REUSE_NARROWING=off: the whole
# key, always (the method before v0.0.42).

USED_SCHEMA = 1
NARROWING_ENV = 'AMIWIND_REUSE_NARROWING'


def narrowing_enabled():
    return os.environ.get(NARROWING_ENV, 'on') != 'off'


def listing_digest(root, relative, recursive=False):
    """SHA-256 of the names in a checkout folder (recursive: every file below it), None when it is gone."""
    folder = Path(root) / relative
    if not folder.is_dir():
        return None
    if recursive:
        names = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*')
                       if '__pycache__' not in p.parts and not p.name.endswith('.pyc'))
    else:
        names = sorted(n for n in os.listdir(folder) if n != '__pycache__' and not n.endswith('.pyc'))
    return hashlib.sha256('\n'.join(names).encode('utf-8', 'surrogateescape')).hexdigest()


def used_record(lines, index, run_inside=None, reused=False):
    """The record of what a stage used (see above), from its trace lines and its checkout's index."""
    root = Path(index.root)
    record = {'schema': USED_SCHEMA, 'top_format': index.top_format, 'complete': True, 'why': []}
    if '#v2' not in lines:
        record.update(complete=False, why=['trace form 1 (no listings or processes)'])
        return record

    def inside(path):
        return bool(run_inside) and (path == run_inside or path.startswith(run_inside + '/'))
    called, opened, listed = {}, set(), {}
    for line in lines:
        if line.startswith('@'):
            path, _, name = line[1:].partition('\t')
            if inside(path) or path in OUTPUT_NEUTRAL or (reused and apply_module(path)):
                continue
            called.setdefault(path, set()).add(name)
        elif line.startswith(('#L', '#R')):
            listed[line[2:]] = listed.get(line[2:], False) or line[1] == 'R'
        elif line.startswith('$'):
            exe, _, flags = line[1:].partition('\t')
            flags = set(flags.split(',')) if flags else set()
            if 'untraced' in flags:
                record['why'].append('started a Python process without the trace (%s)' % exe)
            elif 'repo' in flags and 'py' not in flags:
                record['why'].append('started %s with a checkout path' % exe)
        elif line.startswith('!'):
            name = line[1:].rpartition('/')[2]
            if name.split('.')[0] not in APPLY_STEMS:
                record['why'].append('ran Python code from outside the checkout (%s)' % line[1:])
        elif not line.startswith(TRACE_MARKS) and line.strip():
            if '__pycache__' in line.split('/'):
                continue      # a module's compiled form: the module itself is listed by its '@' lines
            opened.add(line.strip())
    if record['why']:
        record['complete'] = False
        return record
    units = {}
    for path, names in sorted(called.items()):
        if path not in index.files or not path.endswith('.py'):
            continue
        symbols = index._module_symbols(path)
        texts = symbols.get('texts') or {}
        functions = set(symbols.get('units') or ())
        wanted = {'<top>'}
        for name in names:
            if name == '<module>':
                if '<main>' in texts:
                    wanted.add('<main>')
            elif name in functions and not name.startswith('<'):
                wanted.add(name)
            # a class, a decorated function, a comprehension or lambda at module level: part of '<top>'
        hashes = index.unit_hashes(path, wanted)
        if hashes is None or any(v is None for v in hashes.values()):
            record.update(complete=False, why=['cannot hash the units of %s' % path])
            return record
        units[path] = hashes
    data = {}
    for path in sorted(opened):
        parts = path.split('/')
        if inside(path) or path in OUTPUT_NEUTRAL or parts[0] in SKIP_DIRECTORIES \
                or any(part.startswith('.') for part in parts):
            continue
        if path.endswith('.py') and path in called:
            continue          # imported: its code is in units
        if path in index.files:
            data[path] = index.files[path]
    listings = {}
    for path, recursive in sorted(listed.items()):
        if not inside(path):
            listings[('R:' if recursive else 'L:') + path] = listing_digest(root, path, recursive)
    record.update(units=units, data=data, listed=listings)
    return record


def narrowed_unchanged(old_run, name, index):
    """(True, None) when the stage's record in OLD_RUN (where it last really ran) names only code, files and
    listings that are unchanged in INDEX's checkout; else (False, why)."""
    if not narrowing_enabled():
        return False, 'narrowing off'
    record = (ran_manifest(old_run, name) or {}).get('used')
    if not record or record.get('schema') != USED_SCHEMA:
        return False, 'no record of what it used'
    if not record.get('complete'):
        return False, 'record incomplete: ' + '; '.join(record.get('why') or ['unknown'])
    top_format = record.get('top_format')
    for path, hashes in (record.get('units') or {}).items():
        # scheduling units key no stage, also in records written before SCHEDULING_UNITS existed
        hashes = {u: h for u, h in hashes.items() if (path, u) not in SCHEDULING_UNITS}
        now = index.unit_hashes(path, hashes, top_format)
        if now != hashes:
            changed = sorted(u for u in hashes if (now or {}).get(u) != hashes[u])
            return False, 'it ran changed code: %s %s' % (path, ', '.join(changed[:3]))
    for path, digest in (record.get('data') or {}).items():
        if path not in index.files or index.files[path] != digest:
            return False, 'it read a changed file: ' + path
    for key, digest in (record.get('listed') or {}).items():
        kind, _, path = key.partition(':')
        if listing_digest(index.root, path, kind == 'R') != digest:
            return False, 'a folder it listed changed: ' + path
    return True, None


def only_sources_changed(old_components, new_components):
    """True when, of a stage's own key parts, only its sources differ (its dependencies may differ too)."""
    changed = [part for part in explain(old_components or {}, new_components or {})
               if not part.startswith('dependency ')]
    return bool(changed) and all(part == 'sources' or part.startswith('sources (') for part in changed)


class Recorder:
    """Snapshots before and diffs after each stage; writes profile/manifests/STAGE.json."""

    def __init__(self, run, steps, metadata):
        self.run = Path(run)
        self.folder = self.run / 'profile' / 'manifests'
        self.folder.mkdir(parents=True, exist_ok=True)
        self.cache = metadata.get('stage_cache') or {}
        self.original = {name: (self.cache.get('reused', {}).get(name) or {}).get('original_command') or command
                         for name, command in steps}
        self.roots = {name: output_roots(command, self.run) for name, command in self.original.items()}
        self.all_roots = {root.split('/')[0] for roots in self.roots.values() for root in roots}
        self.state = {}
        self.manifests = {}
        self.writes = {}  # stage -> run-relative paths its Python processes wrote (read trace '>' lines), or None
        self.start = time.monotonic()
        plan = PLANS.pop(str(self.run), None)
        if plan is not None:
            (self.run / 'profile' / PLAN_NAME).write_text(json.dumps(plan) + '\n')
        details = DETAILS.pop(str(self.run), None)
        if details is not None:
            (self.run / 'profile' / 'fingerprints.json').write_text(json.dumps(details, indent=1, sort_keys=True) + '\n')
        self.closures = CLOSURES.pop(str(self.run), None) or {}
        self.index = None     # the checkout's SourceIndex for the used records (prepare's, when it made one)
        # The prerendered store (tools/prerendered.py): passed stages are captured as they finish
        # and become store entries only when the whole build passed.
        self.store = None
        if (self.cache.get('prerendered') or {}).get('dir'):
            try:
                import prerendered
                self.store = prerendered.Writer(self.run, metadata, self.cache['prerendered'])
            except Exception as exc:  # noqa: BLE001 - the store is optional; the build goes on without it
                print(f'[warning] Prerendered store disabled: {exc}', flush=True)
        self.traced = False
        if self.closures:
            (self.run / 'profile' / 'closures.json').write_text(json.dumps(self.closures, sort_keys=True) + '\n')
            try:
                self.traced = write_trace_hook(self.run, self.closures['root'],
                                               [str(path) for path in storage_pool_roots(self.run, metadata)])
            except OSError as exc:
                print(f'[warning] Stage read trace disabled: {exc}', flush=True)

    def before(self, name, command):
        roots = self.roots.get(name) or output_roots(command, self.run)
        files, directories = snapshot(self.run, roots)
        inputs = input_files(self.original.get(name, command), self.run)
        self.state[name] = {'roots': roots, 'files': files, 'directories': directories,
                            'inputs': hash_files(self.run, inputs),
                            'top': set(os.listdir(self.run)) if self.run.is_dir() else set(),
                            'window': [round(time.monotonic() - self.start, 3), None]}

    def check_trace(self, name, reads):
        """Reasons the stage's reads were not covered by its fingerprint (and the read summary)."""
        if not self.traced or reads is None or name in NON_REUSABLE or name not in self.closures.get('stages', {}):
            return [], None
        try:
            lines = Path(reads).read_text(encoding='utf-8', errors='surrogateescape').splitlines()
        except OSError:
            return [], {'traced': False}
        root = Path(self.closures['root'])
        try:
            run_inside = self.run.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            run_inside = None
        pool_problems, pool_summary = pool_read_problems(lines)
        misses, uncovered, outside = check_reads([line for line in lines if not line.startswith(TRACE_MARKS)],
                                                 self.closures['stages'][name], set(self.closures['files']),
                                                 root, run_inside)
        if (self.cache.get('reused') or {}).get(name):
            # A reused stage ran only the reuse step (`build_cache.py apply`), which loads the storage pool
            # from the checkout to link verified files; that is no input of the stage's outputs
            # (BUILD-POOL-APPLY-READ-MISS-35: every reused stage of a pool-mode build was marked not reusable).
            misses = [path for path in misses if not apply_module(path)]
            lines = [line for line in lines if not (line.startswith('@') and apply_module(line[1:].partition('\t')[0]))]
        calls = None
        if name in self.closures.get('units', {}):
            calls = check_calls(lines, self.closures['units'][name], self.closures.get('module_units', {}), run_inside)
        summary = {'traced': True, 'lines': len(lines), 'misses': misses[:50], 'uncovered': uncovered[:50],
                   'outside': outside[:50]}
        if pool_summary:
            summary['pool_reads'] = pool_summary
        if calls is not None:
            summary['calls'] = sum(line.startswith('@') for line in lines)
            summary['call_misses'] = calls[:50]
        reasons = []
        if misses:
            reasons.append(f'read {len(misses)} repository files its fingerprint left out (first: {misses[0]})')
        if calls:
            reasons.append(f'ran {len(calls)} repository functions its fingerprint left out (first: {calls[0]})')
        if uncovered:
            reasons.append(f'read {len(uncovered)} repository files no fingerprint covers (first: {uncovered[0]})')
        if outside:
            reasons.append(f'ran {len(outside)} Python files from outside the checkout (first: {outside[0]})')
        if pool_problems:
            reasons.append(f'read {len(pool_problems)} storage pool files outside its keyed lookups, which no '
                           f'fingerprint covers (first: {pool_problems[0]})')
        if reasons:
            print(f'[warning] {name}: its outputs will not be reused: ' + '; '.join(reasons) +
                  '. The fingerprint missed an input: register a bug (docs/BUILD_PROFILE.md, read trace).', flush=True)
        return reasons, summary

    def used(self, name, reads):
        """What the stage used (used_record), for a stage that really ran with the trace; else None."""
        if not self.traced or reads is None or name in NON_REUSABLE or name not in self.closures.get('stages', {}):
            return None
        reused = bool((self.cache.get('reused') or {}).get(name))
        if reused and not (self.run / 'profile' / 'reuse-fallback' / f'{name}.txt').is_file():
            return None       # it only copied its old outputs: its record is the one where it ran (manifests-ran)
        try:
            lines = Path(reads).read_text(encoding='utf-8', errors='surrogateescape').splitlines()
        except OSError:
            return None
        root = Path(self.closures['root'])
        try:
            run_inside = self.run.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            run_inside = None
        try:
            if self.index is None:
                self.index = INDEXES.pop(str(self.run), None) or SourceIndex(
                    root, scope=self.closures.get('scope') or DEFAULT_SCOPE, top_format=STAGE_TOP_FORMAT)
            return used_record(lines, self.index, run_inside, reused=reused)
        except Exception as exc:  # noqa: BLE001 - only an optimisation: without it the key is compared whole
            return {'schema': USED_SCHEMA, 'complete': False, 'why': ['record failed: %s' % exc]}

    def diagnostic_reads(self, reads):
        """Run-folder diagnostics (logs, timing reports) the stage's Python processes read ('<' lines)."""
        if not self.traced or reads is None:
            return []
        try:
            lines = Path(reads).read_text(encoding='utf-8', errors='surrogateescape').splitlines()
        except OSError:
            return []
        return sorted({line[1:] for line in lines if line.startswith('<')})

    def traced_writes(self, reads):
        """Run-relative paths the stage's Python processes opened for writing, renamed to, linked or removed
        ('>' lines of its read trace), or None when the stage was not traced."""
        if not self.traced or reads is None:
            return None
        try:
            lines = Path(reads).read_text(encoding='utf-8', errors='surrogateescape').splitlines()
        except OSError:
            return None
        return {line[1:] for line in lines if line.startswith('>')}

    def after(self, name, entry, reads=None):
        state = self.state.pop(name, None)
        if state is None:
            return None
        self.writes[name] = self.traced_writes(reads)
        state['window'][1] = round(time.monotonic() - self.start, 3)
        files, directories = snapshot(self.run, state['roots'])
        before = state['files']
        changed = sorted(path for path, info in files.items() if before.get(path) is None or before[path][:4] != info[:4]
                         or before[path][4] != info[4])
        regular = [path for path in changed if files[path][4] is None]
        hashes = hash_files(self.run, regular)
        reasons, trace = self.check_trace(name, reads)
        used = self.used(name, reads)
        # A reused stage copies into the run folder through NAME + TEMPORARY_SUFFIX while other stages run; that
        # temporary of a declared root is not this stage's output (BUILD-REUSE-TMP-UNDECLARED-33).
        undeclared = sorted(entry for entry in set(os.listdir(self.run)) - state['top'] - RUN_PRIVATE - self.all_roots
                            if not (entry.endswith(TEMPORARY_SUFFIX)
                                    and entry[:-len(TEMPORARY_SUFFIX)] in self.all_roots))
        if undeclared:
            reasons.append('created run-folder entries outside every declared stage path: ' + ', '.join(undeclared[:5]))
        # Diagnostics are not compared between runs (same_outputs), so a stage that reads another stage's could take
        # in a difference the reuse planner does not see (BUILD-OUTPUTS-NOT-REPRODUCIBLE-33). Its own, written in
        # this run, it may read back.
        foreign = [path for path in self.diagnostic_reads(reads)
                   if not (path in (self.writes.get(name) or ()) or (path in changed and path in files))]
        if foreign:
            # Such a read is a declared input from here on: its SHA-256 joins the record's inputs, and the
            # reuse step reuses the stage only when the file has those exact bytes again (apply_stage: "its
            # input ... differs"). Unreadable: not reusable, as before (BUILD-DIAGNOSTIC-INPUT-REFUSED-36).
            try:
                state['inputs'] = {**state['inputs'], **hash_files(self.run, foreign)}
            except OSError:
                reasons.append('read build diagnostics written by other stages, which are not stage inputs: '
                               + ', '.join(foreign[:3]))
        manifest = {'schema': MANIFEST_SCHEMA, 'stage': name, 'status': 'complete',
                    'fingerprint': (self.cache.get('fingerprints') or {}).get(name),
                    'roots': state['roots'], 'window': state['window'], 'inputs': state['inputs'],
                    'files': {path: {'size': files[path][0], 'sha256': hashes[path],
                                     'mode': stat_module.S_IMODE(files[path][3])} for path in regular},
                    'links': {path: files[path][4] for path in changed if files[path][4] is not None},
                    'directories': sorted(directories - state['directories']),
                    'deleted': sorted(set(before) - set(files)),
                    'deleted_directories': sorted(state['directories'] - directories),
                    'reusable': not reasons, 'reasons': reasons, 'reads': trace}
        if used is not None:
            manifest['used'] = used
        manifest['counts'] = {'files': len(regular), 'bytes': sum(files[path][0] for path in regular)}
        # Units -> segments -> stage hash (tools/unit_tree.py): compared in one step, drilled into on a mismatch.
        from unit_tree import of_manifest
        manifest['tree'] = of_manifest(manifest)
        # Who, when and from which version (tools/cache_provenance.py, CACHE-NO-PROVENANCE-36): never compared.
        import cache_provenance
        cache_provenance.attach_stage(manifest, self.run)
        self.manifests[name] = manifest
        self._write(name, manifest)
        self._keep_ran(name)
        if self.store is not None:
            try:
                self.store.capture(name, manifest)
            except Exception as exc:  # noqa: BLE001
                print(f'[warning] {name}: not captured for the prerendered store: {exc}', flush=True)
        return manifest

    def _keep_ran(self, name):
        """A reused stage: keep its original output record in this run (RAN_FOLDER), so early cutoff and the
        reuse audit can compare with it after the run it came from is retired (BUILD-REUSE-RECORD-RETIRED-36)."""
        reused = (self.cache.get('reused') or {}).get(name)
        if not reused or (self.run / 'profile' / 'reuse-fallback' / f'{name}.txt').is_file():
            return
        source = str(reused.get('from') or '')
        original = ran_manifest(source, name) if source and not source.startswith('prerendered ') else None
        if not original:
            return
        folder = self.run / 'profile' / RAN_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        temporary = folder / f'{name}.tmp'
        temporary.write_text(json.dumps(original, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
        temporary.replace(folder / f'{name}.json')

    def _write(self, name, manifest):
        temporary = self.folder / f'{name}.tmp'
        temporary.write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
        temporary.replace(self.folder / f'{name}.json')

    def close(self, receipt):
        """Stages that ran at the same time and touched the same path are never reused."""
        names = sorted(self.manifests)
        touched = {name: set(self.manifests[name]['files']) | set(self.manifests[name]['links'])
                   | set(self.manifests[name]['deleted']) for name in names}
        for i, first in enumerate(names):
            for second in names[i + 1:]:
                a, b = self.manifests[first]['window'], self.manifests[second]['window']
                if not (a[0] < b[1] and b[0] < a[1]):
                    continue
                shared = sorted(touched[first] & touched[second])
                writer = attribute(shared, self.writes.get(first), self.writes.get(second))
                if shared and writer is not None:
                    # Both saw the files change, but only one stage wrote them (its trace): they are its
                    # outputs, not the other's (BUILD-REUSE-ATTRIBUTION-33).
                    observer = second if writer == 0 else first
                    manifest = self.manifests[observer]
                    for field in ('files', 'links'):
                        manifest[field] = {path: value for path, value in manifest[field].items() if path not in shared}
                    manifest['deleted'] = [path for path in manifest['deleted'] if path not in shared]
                    manifest['counts'] = {'files': len(manifest['files']),
                                          'bytes': sum(row['size'] for row in manifest['files'].values())}
                    from unit_tree import of_manifest
                    manifest['tree'] = of_manifest(manifest)
                    manifest.setdefault('attributed', []).append(
                        {'stage': first if writer == 0 else second, 'paths': len(shared), 'first': shared[0]})
                    touched[observer] -= set(shared)
                    self._write(observer, manifest)
                    continue
                if shared:
                    for name, other in ((first, second), (second, first)):
                        manifest = self.manifests[name]
                        manifest['reusable'] = False
                        manifest['reasons'].append(f'changed {shared[0]} (and {len(shared) - 1} more) while {other} ran; '
                                                   'outputs cannot be attributed')
                        self._write(name, manifest)
        index = {name: {'fingerprint': m['fingerprint'], 'reusable': m['reusable'], 'reasons': m['reasons'],
                        'window': m['window'], 'files': m['counts']['files'], 'bytes': m['counts']['bytes']}
                 for name, m in self.manifests.items()}
        (self.folder / 'index.json').write_text(json.dumps(index, indent=1, sort_keys=True) + '\n')
        if self.store is not None:
            try:
                self.store.finish(receipt, self.manifests)
            except Exception as exc:  # noqa: BLE001
                print(f'[warning] Prerendered store not updated: {exc}', flush=True)


# --------------------------------------------------------------------------
# Reuse planning (in the builder, before the stages start)

PLANS = {}    # run -> per-stage file plan, written into the run by Recorder
CLOSURES = {}  # run -> {stage: repository files its fingerprint covers}, checked against the stage's trace
INDEXES = {}   # run -> the SourceIndex its fingerprints were made with (Recorder.used)
DETAILS = {}  # run -> fingerprint components, written into the run by Recorder


def attribute(shared, first_writes, second_writes):
    """Which of two stages that ran at the same time and both saw SHARED change wrote them: 0 (the first), 1
    (the second), or None when unknown. Known only when both were traced, one wrote every shared path and the
    other none of them (a native tool's writes are not traced: then nobody is credited)."""
    if not shared or first_writes is None or second_writes is None:
        return None
    shared = set(shared)
    if shared <= first_writes and not shared & second_writes:
        return 0
    if shared <= second_writes and not shared & first_writes:
        return 1
    return None


def load_manifest(run, name):
    return read_manifest(Path(run) / 'profile' / 'manifests' / f'{name}.json')


# A reused stage's record of what it wrote when it last really ran, copied into the run that reused it, so the
# run stays a complete reuse source after the run it came from is retired (BUILD-REUSE-RECORD-RETIRED-36).
RAN_FOLDER = 'manifests-ran'


def read_manifest(path):
    path = Path(path)
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return requalify(manifest) if manifest.get('schema') == MANIFEST_SCHEMA else None


SCRATCH_ONLY_REASON = 'created run-folder entries outside every declared stage path: scratch'


def requalify(manifest):
    """A manifest recorded before BUILD-REUSE-SCRATCH-UNDECLARED-33 whose ONLY reason not to be reused was the
    builder's scratch folder (now run-private) is reusable: its files, hashes and fingerprint are recorded as for
    any other stage, and the scratch folder never held outputs. The fingerprint and same-output checks apply as
    usual. Any other reason, alone or with this one, still refuses reuse."""
    if not manifest.get('reusable') and manifest.get('reasons') == [SCRATCH_ONLY_REASON]:
        manifest = dict(manifest, reusable=True, reasons=[],
                        requalified='recorded non-reusable only for the scratch folder (BUILD-REUSE-SCRATCH-UNDECLARED-33)')
    return manifest


def plan_reuse(steps, fingerprints, dependencies, components, problems, old_run, forced=(), index=None,
               narrowed=None):
    """({stage: plan}, {stage: reason not reused}) against a completed earlier run. INDEX (this checkout's
    SourceIndex): a stage whose key differs only in its sources is reused when what it used is unchanged
    (narrowed_unchanged); NARROWED (a dict) gets {stage: the changed key files it never used}."""
    old_run = Path(old_run)
    state_path = old_run / 'build-state.json'
    if not state_path.is_file():
        raise ValueError(f'--reuse-from {old_run}: no build-state.json')
    state = json.loads(state_path.read_text())
    old_cache = state.get('stage_cache') or {}
    old_fingerprints = old_cache.get('fingerprints') or {}
    old_status = {step['name']: step.get('status') for step in state.get('steps', [])}
    old_schema = old_cache.get('schema') or 'none'
    try:
        old_details = json.loads((old_run / 'profile' / 'fingerprints.json').read_text())
    except (OSError, ValueError):
        old_details = {}
    names = [name for name, _ in steps]
    reasons, manifests, left_out = {}, {}, {}
    # Conditional reuse (BUILD-CACHE-NO-CUTOFF-33): a stage whose own fingerprint parts are unchanged
    # but which depends on a stage that is rebuilt is reused only if, when it starts, every rebuilt
    # stage before it wrote exactly the files it wrote in the old run (apply_stage checks).
    conditional = set()
    for name in names:
        own_same = name in old_details and not [part for part in explain(old_details[name], components[name])
                                                 if not part.startswith('dependency ')]
        if (not own_same and index is not None and name in old_details and name not in NON_REUSABLE
                and name not in forced and old_status.get(name) == 'passed'
                and only_sources_changed(old_details[name], components[name])):
            same, _ = narrowed_unchanged(old_run, name, index)
            if same:
                own_same = True
                if narrowed is not None:
                    old_files = ((old_details[name].get('sources') or {}).get('by_file') or {})
                    new_files = ((components[name].get('sources') or {}).get('by_file') or {})
                    narrowed[name] = sorted(p for p in set(old_files) | set(new_files)
                                            if old_files.get(p) != new_files.get(p))
        if name in NON_REUSABLE:
            reasons[name] = NON_REUSABLE[name]
        elif name in forced:
            # --rebuild-stage: runs again; the stages after it are reused only if it writes the same outputs.
            reasons[name] = FORCED_REASON
        elif problems.get(name):
            reasons[name] = '; '.join(problems[name])
        elif old_schema != CACHE_SCHEMA:
            reasons[name] = (f'{old_run.name} has {old_schema} fingerprints, this builder makes {CACHE_SCHEMA} '
                             '(per-stage sources and environment, no absolute paths): build once without reuse')
        elif old_status.get(name) != 'passed':
            reasons[name] = f'not passed in {old_run.name} ({old_status.get(name) or "absent"})'
        elif old_fingerprints.get(name) != fingerprints[name] and not own_same:
            changed = explain(old_details.get(name, {}), components[name]) if name in old_details else ['fingerprint']
            reasons[name] = 'changed: ' + ', '.join(changed)
        else:
            manifest = load_manifest(old_run, name)
            if manifest is not None:
                # A stage the old run itself reused recorded only what it copied: files a later reused stage
                # replaced there are left out. They are checked below like replaced files of a stage that ran
                # (BUILD-REUSE-REDUCED-RECORD-36).
                # The full record belongs to the same outputs when every file the short record lists is in it
                # with the same SHA-256 (the stage key may differ between the runs: a key-form change with
                # unchanged outputs, BUILD-KEY-FUNCTION-DEFAULTS-TOP-36).
                ran = ran_manifest(old_run, name)
                ran_files, own_files = (ran or {}).get('files') or {}, manifest.get('files') or {}
                if ran is not None and all(path in ran_files and ran_files[path].get('sha256') == info.get('sha256')
                                           for path, info in own_files.items()):
                    left_out[name] = sorted(set(ran_files) - set(own_files))
            if manifest is None:
                reasons[name] = 'no output manifest in the old run'
            elif manifest.get('status') != 'complete' or manifest.get('fingerprint') != old_fingerprints.get(name):
                reasons[name] = 'old output manifest incomplete or for another fingerprint'
            elif not manifest.get('reusable'):
                reasons[name] = 'old outputs not reusable: ' + '; '.join(manifest.get('reasons') or ['unknown'])
            else:
                manifests[name] = manifest
    candidates = set(manifests)
    # Every manifest of the old run, in completion order, decides who wrote each path last.
    old_manifests = {}
    for name in old_fingerprints:
        manifest = manifests.get(name) or load_manifest(old_run, name)
        if manifest:
            old_manifests[name] = manifest
    order = sorted(old_manifests, key=lambda n: (old_manifests[n]['window'][1] or 0, n))
    writers = {}
    for name in order:
        manifest = old_manifests[name]
        for path in (*manifest['files'], *manifest['links'], *manifest['deleted']):
            writers.setdefault(path, []).append(name)
    # Who touched each left-out file where it really ran (the old run's own record of a reused stage lists only
    # what it copied or changed, so it may not show the stage that replaced the file).
    touched = {}
    if any(left_out.values()):
        for other in old_fingerprints:
            record = ran_manifest(old_run, other)
            for path in (*(record or {}).get('files', {}), *(record or {}).get('links', {}),
                         *(record or {}).get('deleted', [])):
                touched.setdefault(path, set()).add(other)
    skips, verified = {}, {}
    while True:
        changed = True
        while changed:
            changed = False
            for name in sorted(candidates):
                # Conditional: a stage before it is rebuilt, or may be (conditional itself). A fingerprint that
                # differs only through its dependencies' keys, with every one of them reused unconditionally,
                # has the old inputs: the key form changed, not the outputs (BUILD-KEY-FUNCTION-DEFAULTS-TOP-36).
                missing = [dep for dep in dependencies.get(name, []) if dep not in candidates or dep in conditional]
                if missing and name not in conditional:
                    # Reused only if the rebuilt stages' outputs come out unchanged (checked when it starts).
                    conditional.add(name)
                    changed = True
                # Files the old run's own reuse of this stage left out (a later stage replaced them there): the
                # stage is whole only if every stage that replaced them is reused unconditionally in this build;
                # otherwise it runs again, never with those files missing (BUILD-REUSE-REDUCED-RECORD-36).
                gone = next((path for path in left_out.get(name, ())
                             if not touched.get(path, set()) - {name}
                             or any(w not in candidates or w in conditional
                                    for w in touched.get(path, set()) - {name})), None)
                if gone is not None:
                    candidates.discard(name)
                    replaced = sorted(touched.get(gone, set()) - {name})
                    reasons[name] = (f'{old_run.name} reused it without {gone} (replaced there by '
                                     f'{", ".join(replaced) or "a stage no longer recorded"}), which this build '
                                     'runs again')
                    changed = True
                    continue
                # A path a later stage replaced is delivered by that stage, if it is reused too;
                # otherwise this stage's version no longer exists in the old run.
                skip = {}
                for path in (*manifests[name]['files'], *manifests[name]['links']):
                    later = writers[path][writers[path].index(name) + 1:]
                    if not later:
                        continue
                    if later[0] in candidates and later[0] in conditional:
                        # A conditional stage may still be rebuilt, and would then need this stage's
                        # version of the path, which the old run no longer has: rebuild it now.
                        candidates.discard(later[0])
                        conditional.discard(later[0])
                        reasons[later[0]] = (f'reuse would depend on rebuilt stages, and {name} (reused) leaves out '
                                             f'its version of {path}')
                        changed = True
                        break
                    if later[0] in candidates:
                        skip[path] = later[0]
                    else:
                        candidates.discard(name)
                        reasons[name] = (f'its output {path} was replaced later in {old_run.name} by {later[0]}, '
                                         'which is rebuilt')
                        changed = True
                        break
                else:
                    skips[name] = skip
        # Verify every file to copy now (SHA-256), so a damaged old run never starts a mixed build.
        pending = sorted({path for name in candidates for path in manifests[name]['files']
                          if path not in skips[name] and path not in verified})
        def check(path):
            try:
                return sha256_file(old_run / path)
            except OSError:
                return None
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as pool:
            verified.update(zip(pending, pool.map(check, pending)))
        damaged = False
        for name in sorted(candidates):
            for path, info in manifests[name]['files'].items():
                if path not in skips[name] and verified.get(path) != info['sha256']:
                    candidates.discard(name)
                    reasons[name] = f'old output {path} changed or missing since {old_run.name} was built'
                    damaged = True
                    break
        if not damaged:
            break
    hazards, hazard_stages = {}, {}
    for name in candidates:
        for path, writer in skips[name].items():
            hazards.setdefault(writer, []).append(path)
            stages = hazard_stages.setdefault(writer, {})
            stages[name] = stages.get(name, 0) + 1
    ancestors = {}

    def lineage(name):
        if name not in ancestors:
            found = set()
            for dep in dependencies.get(name, []):
                found |= {dep} | lineage(dep)
            ancestors[name] = found
        return ancestors[name]

    plans = {}
    for name in names:
        if name not in candidates:
            continue
        manifest = manifests[name]
        files = {path: info for path, info in manifest['files'].items() if path not in skips[name]}
        plans[name] = {'from': str(old_run), 'fingerprint': fingerprints[name], 'files': files,
                       'links': {path: target for path, target in manifest['links'].items() if path not in skips[name]},
                       'directories': manifest['directories'], 'deleted': manifest['deleted'],
                       'deleted_directories': manifest['deleted_directories'], 'inputs': manifest.get('inputs', {}),
                       'ancestors': sorted(lineage(name)), 'skipped_later_replaced': len(skips[name]),
                       # Stages before it that this build runs: each must write exactly its old files
                       # (checked when this stage starts), or this stage runs too.
                       'conditional': name in conditional,
                       'rebuilt_ancestors': sorted(a for a in lineage(name) if a not in candidates),
                       # Files earlier reused stages left out because this stage replaces them:
                       # if this stage cannot be reused after all, it cannot be rebuilt either.
                       'rebuild_hazard': sorted(hazards.get(name, []))[:20],
                       'rebuild_hazard_count': len(hazards.get(name, [])),
                       # {reused stage: files it left out}: a stage that ran again in this build after all wrote
                       # its own versions, so its share is no hazard any more (BUILD-RESUME-HAZARD-STATIC-35).
                       'rebuild_hazard_stages': dict(sorted(hazard_stages.get(name, {}).items()))}
    return plans, reasons


def recorded_sources(state):
    """The reuse source's recorded source tree (build-state.json source_sha256), without the folders and
    suffixes no fingerprint covers (tests, prose), so the preflight's source diff lists only candidate inputs."""
    return {path: digest for path, digest in (state.get('source_sha256') or {}).items()
            if not set(path.split('/')[:-1]) & SKIP_DIRECTORIES and not path.endswith(SKIP_SUFFIXES)
            and not path.startswith(SKIP_PREFIXES)}


def run_preflight(steps, reasons, components, old_run, index, reused=()):
    """The reuse preflight (tools/reuse_report.py preflight) of a plan against OLD_RUN."""
    import reuse_report
    old_run = Path(old_run)
    try:
        state = json.loads((old_run / 'build-state.json').read_text())
    except (OSError, ValueError):
        state = {}
    try:
        old_details = json.loads((old_run / 'profile' / 'fingerprints.json').read_text())
    except (OSError, ValueError):
        old_details = {}
    return reuse_report.preflight([name for name, _ in steps], reasons, components, old_details,
                                  recorded_sources(state), index.files, reused)


def predict_preflight(old_run, scope=DEFAULT_SCOPE, root=ROOT):
    """`build.py --reuse-plan OLD_RUN`: the preflight of OLD_RUN's own stages against this checkout (no build)."""
    old_run = Path(old_run)
    steps, state = old_run_steps(old_run, root)
    index = SourceIndex(root, scope=scope, top_format=STAGE_TOP_FORMAT)
    reasons, components = predict(old_run, scope, root, index=index, details=True)
    reasons = {name: reason for name, reason in reasons.items() if reason is not None}
    reused = [name for name, _ in steps if name not in reasons]
    return run_preflight(steps, reasons, components, old_run, index, reused)


def advisory_stages(steps, dependencies):
    """Stages whose command says --never-fail and that no other stage depends on: their outputs reach nothing
    else, and they never fail the build (the cell-progress tracker data)."""
    needed = {dep for deps in (dependencies or {}).values() for dep in deps}
    return {name for name, command in steps if '--never-fail' in map(str, command) and name not in needed}


def prepare(steps, run, metadata, reuse_from=None, mode='copy', index=None, scope=DEFAULT_SCOPE, prerendered=None,
            pool=None, forced=(), accept_rebuild=False):
    """Fingerprint every stage; with REUSE_FROM, swap reusable stages for verified copies.

    Records metadata['stage_cache'] (part of build-state.json) and returns the steps.
    SCOPE: 'units' (default), 'symbols' or 'modules' (SCOPES; the wider, earlier source closures).
    PRERENDERED: {'dir', 'read', 'write', 'stages'} (tools/prerendered.py): a stage REUSE_FROM does
    not reuse takes the store entry with its fingerprint (same plan, same verified apply);
    captured stages become entries when the whole build passed.
    MODE: 'copy' (default), 'hardlink' (links to the old run's files) or 'pool' (links to the shared
    storage pool's objects, tools/storage_pool.py: the old file is pooled by a hard link, never copied;
    POOL names the pool folder). Linked files are read-only in every run that shares them.
    """
    if mode == 'pool' and not pool:
        raise ValueError('--reuse-mode pool needs the storage pool folder')
    began = time.monotonic()
    index = index or SourceIndex(scope=scope, top_format=STAGE_TOP_FORMAT)
    fingerprints, components, problems, dependencies = fingerprint_steps(steps, run, metadata, index)
    cache = {'schema': CACHE_SCHEMA, 'scope': index.scope, 'fingerprints': fingerprints, 'reuse_from': None,
             'reused': {}, 'not_reused': {}, 'reuse_mode': None}
    units, modules = stage_units(steps, index)
    INDEXES[str(run)] = index
    CLOSURES[str(run)] = {'root': str(index.root), 'scope': index.scope, 'stages': stage_closures(steps, index),
                          'files': sorted(index.files), 'units': units, 'module_units': modules}
    DETAILS[str(run)] = components
    result = list(steps)
    if reuse_from is not None:
        reuse_from = Path(reuse_from).resolve()
        if reuse_from == Path(run).resolve():
            raise ValueError('--reuse-from must name an earlier run, not this one')
        # Compared in the reuse source's own fingerprint form (comparable); recorded in this run's form.
        try:
            old_details = json.loads((reuse_from / 'profile' / 'fingerprints.json').read_text())
        except (OSError, ValueError):
            old_details = {}
        compared = comparable_all(components, old_details, run)
        narrowed = {}
        plans, reasons = plan_reuse(steps, fingerprints, dependencies, compared, problems, reuse_from,
                                    forced=set(forced), index=index, narrowed=narrowed)
        if narrowed:
            cache['narrowed'] = {name: files[:20] for name, files in narrowed.items() if name in plans}
        if forced:
            cache['forced'] = sorted(forced)
        cache.update(reuse_from=str(reuse_from), not_reused=reasons, reuse_mode=mode)
        PLANS[str(run)] = {name: dict(plan, mode=mode, **({'pool': str(pool)} if mode == 'pool' else {}))
                           for name, plan in plans.items()}
        result = []
        for name, command in steps:
            if name in plans:
                plan = plans[name]
                cache['reused'][name] = {'from': str(reuse_from), 'fingerprint': plan['fingerprint'],
                                         'files': len(plan['files']), 'bytes': sum(i['size'] for i in plan['files'].values()),
                                         'original_command': [str(part) for part in command]}
                result.append((name, [sys.executable, str(Path(__file__).resolve()), 'apply', '--run', str(run),
                                      '--stage', name, '--', *map(str, command)]))
            else:
                result.append((name, command))
        print(f'Reuse from {reuse_from}: {len(plans)} of {len(steps)} stages reused ({mode}); '
              f'every other stage runs.', flush=True)
        for name, _ in steps:
            if name in plans:
                after = plans[name]['rebuilt_ancestors']
                print(f'   reused  {name} (fingerprint {fingerprints[name][:12]})'
                      + (f" if {', '.join(after)} write the same files again" if after else ''), flush=True)
                if name in narrowed:
                    files = narrowed[name]
                    more = f' (+{len(files) - 4} more)' if len(files) > 4 else ''
                    print(f"           its key changed only in code and files it never ran or read: "
                          f"{', '.join(files[:4])}{more}", flush=True)
        # Reuse preflight (BUILD-REUSE-KEYS-TOO-BROAD-35): every rebuild with its reason and the changed files
        # that touch it, before any stage runs; a rebuild the source diff and the inputs do not explain stops here.
        import reuse_report
        check = run_preflight(steps, reasons, compared, reuse_from, index, reused=plans)
        reuse_report.print_preflight(check, sys.stdout, accepted=accept_rebuild)
        sys.stdout.flush()
        cache['preflight'] = {key: check[key] for key in ('stages', 'reused', 'rebuilt', 'unexpected', 'policy')}
        cache['preflight']['source_diff'] = {key: len(value) if isinstance(value, list) else value
                                             for key, value in check['source_diff'].items()}
        cache['preflight']['unexpected_stages'] = [row['stage'] for row in check['rows'] if row['class'] == 'UNEXPECTED']
        # An advisory stage (--never-fail, no stage depends on it: the tracker data) costs at most a rerun of
        # itself: an over-broad key there is reported, never a stop (BUILD-CELL-PROGRESS-KEY-BUGS-35).
        advisory = advisory_stages(steps, dependencies)
        relaxed = [name for name in check['too_broad'] if name in advisory]
        if relaxed:
            print(f"Reuse preflight: {', '.join(relaxed)} rebuilt for an over-broad key; advisory stage(s) "
                  '(never fail the build, nothing depends on them): runs again, the build goes on.', flush=True)
            check['too_broad'] = [name for name in check['too_broad'] if name not in advisory]
            cache['preflight']['advisory_rebuilt'] = relaxed
        cache['preflight']['too_broad'] = check['too_broad']
        if check['too_broad'] and not accept_rebuild:
            metadata['stage_cache'] = cache
            raise ValueError(f"Reuse preflight: {len(check['too_broad'])} stage(s) would be rebuilt although neither "
                             f"the source diff nor their inputs explain it ({', '.join(check['too_broad'][:6])}); "
                             'fix the key or pass --accept-rebuild')
    if prerendered:
        import prerendered as store
        hits, cache['prerendered'] = store.plan_hits(steps, fingerprints, problems, dependencies, prerendered,
                                                     taken=set(cache['reused']))
        PLANS.setdefault(str(run), {}).update({name: dict(plan, mode=mode) for name, plan in hits.items()})
        originals = dict(steps)
        for position, (name, command) in enumerate(result):
            if name in hits:
                plan = hits[name]
                cache['reused'][name] = {'from': 'prerendered ' + plan['prerendered'], 'fingerprint': plan['fingerprint'],
                                         'files': len(plan['files']), 'bytes': sum(i['size'] for i in plan['files'].values()),
                                         'original_command': [str(part) for part in originals[name]]}
                result[position] = (name, [sys.executable, str(Path(__file__).resolve()), 'apply', '--run', str(run),
                                           '--stage', name, '--', *map(str, originals[name])])
        cache['reuse_mode'] = cache['reuse_mode'] or (mode if hits else None)
    cache['fingerprint_seconds'] = round(time.monotonic() - began, 3)
    metadata['stage_cache'] = cache
    return result


# --------------------------------------------------------------------------
# Apply (runs as the stage command of a reused stage)

def _rebuild(run, stage, reason, command):
    marker = Path(run) / 'profile' / 'reuse-fallback'
    marker.mkdir(parents=True, exist_ok=True)
    (marker / f'{stage}.txt').write_text(reason + '\n')
    print(f'Reuse of {stage} refused: {reason}. Running the stage instead.', flush=True)
    if not command:
        print('No stage command to run.', flush=True)
        return 1
    import subprocess
    return subprocess.run(command).returncode


APPLY_THREADS_ENV = 'AMIWIND_APPLY_THREADS'


class _StagingError(ValueError):
    """A file of a reused stage could not be staged; `staged` lists the temporaries already made."""


def apply_threads(files):
    """Threads that stage (link or copy, and verify by SHA-256) a reused stage's files (B8, v0.0.42): a reused
    stage applied its files one at a time on one core (the world terrain, scenery and flora stages 10 s each
    in every reuse build, one after another on the critical path). AMIWIND_APPLY_THREADS=1: the method
    before v0.0.42."""
    try:
        wanted = int(os.environ.get(APPLY_THREADS_ENV, '0'))
    except ValueError:
        wanted = 0
    if wanted < 1:
        wanted = min(8, os.cpu_count() or 1)
    return max(1, min(wanted, files // 64 + 1))


def _stage_files(items, run, old, pool, link):
    """[(temporary, target)] for ITEMS [(relative, info)] in their order. Files with the same SHA-256 are staged
    one after another by the same thread (the storage pool object they share is made once); different contents
    side by side. On any failure every temporary made is listed on the raised error (`staged`)."""
    groups = {}
    for relative, info in items:
        groups.setdefault(info['sha256'], []).append((relative, info))
    made, lock = {}, threading.Lock()

    def stage(group):
        for relative, info in group:
            target = run / relative
            source = old / relative
            if pool and link:
                source = _pooled(pool, source, info['sha256'])
            temporary = _copy_verified(source, target, info['sha256'], info['mode'], link)
            with lock:
                made[relative] = (temporary, target)
    threads = apply_threads(len(items))
    failure = None
    if threads == 1:
        try:
            for group in groups.values():
                stage(group)
        except (OSError, ValueError) as exc:
            failure = exc
    else:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for future in [executor.submit(stage, group) for group in groups.values()]:
                try:
                    future.result()
                except (OSError, ValueError) as exc:
                    failure = failure or exc
    staged = [made[relative] for relative, _ in items if relative in made]
    if failure is not None:
        error = _StagingError(str(failure))
        error.staged = staged
        raise error from failure
    return staged


def _copy_verified(source, target, expected, mode, link):
    temporary = target.with_name(target.name + TEMPORARY_SUFFIX)
    if temporary.exists():
        temporary.unlink()
    try:
        if link:
            try:
                os.link(source, temporary)
            except OSError as exc:
                if exc.errno != errno.EXDEV:
                    raise
                link = False  # another file system (a prerendered store on its own volume): copy
        if link:
            actual = sha256_file(temporary)
        else:
            digest = hashlib.sha256()
            with open(source, 'rb') as reader, open(temporary, 'wb') as writer:
                for block in iter(lambda: reader.read(1024 * 1024), b''):
                    digest.update(block)
                    writer.write(block)
            actual = digest.hexdigest()
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    if actual != expected:
        temporary.unlink()
        raise ValueError(f'{source} has SHA-256 {actual}, recorded {expected}')
    if link:
        os.chmod(temporary, mode & ~0o222)
    else:
        os.chmod(temporary, mode)
    return temporary


def _pooled(pool, source, digest):
    """The storage pool's object for DIGEST, pooling SOURCE by a hard link first if needed; SOURCE on any doubt."""
    try:
        import storage_pool
        return storage_pool.ensure(pool, source, digest)
    except (ImportError, OSError) as exc:
        print(f'[warning] storage pool not used for {source.name} ({exc}); linking the file of the old run.', flush=True)
        return source


OUTPUT_FIELDS = ('files', 'links', 'deleted', 'directories', 'deleted_directories')
# Diagnostic outputs (BUILD-OUTPUTS-NOT-REPRODUCIBLE-33): tool logs and reports that carry wall time, cache hit
# counts or host details, and that no stage reads. A rerun stage whose outputs differ only in these "wrote the
# same outputs" for the stages after it; they are still recorded and copied on reuse. No stage may read one: the
# stage trace lists every run-folder diagnostic a stage opens, and such a stage is not reused (Recorder.after).
DIAGNOSTIC_SUFFIXES = ('.log',)
DIAGNOSTIC_NAMES = frozenset({'chim-stats.json', 'chim-timing.json', 'gallery-cache.json', 'world-terrain-cache.json'})


def diagnostic(path):
    """True for a run-folder output that no stage reads (DIAGNOSTIC_SUFFIXES, DIAGNOSTIC_NAMES)."""
    name = path.rsplit('/', 1)[-1]
    return name.endswith(DIAGNOSTIC_SUFFIXES) or name in DIAGNOSTIC_NAMES


def _without_diagnostics(manifest, field):
    value = manifest.get(field)
    if isinstance(value, dict):
        return {path: row for path, row in value.items() if not diagnostic(path)}
    if isinstance(value, list):
        return [path for path in value if not diagnostic(path)]
    return value


def ran_manifest(run, stage, depth=0):
    """STAGE's output manifest from the run where it last actually ran (a reused stage's manifest
    lists only what was copied). In order: the copy the reusing run kept (RAN_FOLDER), the source run's
    record, and, when that run is gone, the record rebuilt from the reuse plan (planned_manifest)."""
    run = Path(run)
    try:
        reused = (json.loads((run / 'build-state.json').read_text()).get('stage_cache') or {}).get('reused') or {}
    except (OSError, ValueError):
        reused = {}
    if stage in reused and not (run / 'profile' / 'reuse-fallback' / f'{stage}.txt').is_file() and depth < 16:
        kept = read_manifest(run / 'profile' / RAN_FOLDER / f'{stage}.json')
        if kept:
            return kept
        source = str(reused[stage].get('from') or '')
        found = ran_manifest(source, stage, depth + 1) if source and not source.startswith('prerendered ') else None
        return found or planned_manifest(run, stage)
    return load_manifest(run, stage)


def planned_manifest(run, stage):
    """STAGE's original output record rebuilt from RUN's reuse plan, or None. Exact only when the plan left
    nothing out (no file of it replaced by a later reused stage): then the plan holds every file (SHA-256 and
    mode), link, folder and deletion the stage wrote when it ran (BUILD-REUSE-RECORD-RETIRED-36)."""
    try:
        plan = json.loads((Path(run) / 'profile' / PLAN_NAME).read_text()).get(stage)
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(plan, dict) or plan.get('skipped_later_replaced', 1) != 0 or 'files' not in plan:
        return None
    manifest = {'schema': MANIFEST_SCHEMA, 'stage': stage, 'status': 'complete', 'reusable': True, 'reasons': [],
                'fingerprint': plan.get('fingerprint'), 'from_plan': True,
                **{field: plan.get(field) or ({} if field in ('files', 'links') else [])
                   for field in OUTPUT_FIELDS}}
    from unit_tree import of_manifest
    manifest['tree'] = of_manifest(manifest)
    return manifest


# Reasons a record is refused as a REUSE SOURCE that say nothing about the outputs it recorded: the stage read
# something its key left out (repository code or files, outside code, another stage's diagnostics). Its recorded
# files are still exactly what it wrote, so they can be compared (BUILD-RESUME-OUTPUTS-DIFFER-35). Attribution
# problems (concurrent writers, undeclared run-folder entries) make the record itself unreliable.
TRACE_ONLY_REASONS = ('read ', 'ran ')


def outputs_recorded(manifest):
    """True when MANIFEST is a complete record of what its stage wrote (whether or not it may be reused)."""
    if not manifest or manifest.get('status') != 'complete':
        return False
    return bool(manifest.get('reusable')) or all(str(reason).startswith(TRACE_ONLY_REASONS)
                                                 for reason in manifest.get('reasons') or ())


def output_modes(manifest):
    """{path: mode without the write bits} of a manifest's non-diagnostic files."""
    return {path: (row.get('mode') & ~0o222 if isinstance(row.get('mode'), int) else row.get('mode'))
            for path, row in _without_diagnostics(manifest, 'files').items()}


def same_outputs(run, old_run, stage):
    """True when STAGE wrote, in RUN, exactly the files (SHA-256 and mode), links and deletions it wrote
    when it last ran for OLD_RUN."""
    new, old = load_manifest(run, stage), ran_manifest(old_run, stage)
    if not outputs_recorded(new) or not outputs_recorded(old):
        return False
    from unit_tree import of_manifest
    # The stage hash first (units -> segments -> stage, diagnostics left out): one comparison when nothing changed.
    if (new.get('tree') or of_manifest(new))['stage_hash'] != (old.get('tree') or of_manifest(old))['stage_hash']:
        return False
    # Modes without the write bits: a stage reused by hard link is read-only in the reusing run (link_file), so its
    # recorded mode is 0o444 where the same file written fresh is 0o644 (BUILD-REUSE-CUTOFF-MODE-36: dev3's bsp
    # rerun wrote byte-identical files and 11 stages after it were refused). Read and execute bits still count.
    if output_modes(new) != output_modes(old):
        return False
    return all(_without_diagnostics(new, field) == _without_diagnostics(old, field)
               for field in ('deleted', 'directories', 'deleted_directories'))


def output_differences(run, old_run, stage):
    """[(segment, unit, change)] between STAGE's outputs in RUN and in OLD_RUN (tools/unit_tree.py), or None
    when either record is missing."""
    from unit_tree import differences, of_manifest
    new, old = load_manifest(run, stage), ran_manifest(old_run, stage)
    if not new or not old:
        return None
    return differences(new.get('tree') or of_manifest(new), old.get('tree') or of_manifest(old))


def live_hazard(plan, run):
    """{reused stage: files it left out that this stage replaces} still missing when this stage must run after
    all. A stage that ran in this build (its reuse refused: profile/reuse-fallback/STAGE.txt, or planned as rebuilt)
    wrote its own versions of them. A plan without the per-stage split counts whole (older plans)."""
    count = plan.get('rebuild_hazard_count') or 0
    if not count:
        return {}
    stages = plan.get('rebuild_hazard_stages')
    if stages is None:
        return {'earlier reused stages': count}
    fallback = Path(run) / 'profile' / 'reuse-fallback'
    ran = set(plan.get('rebuilt_ancestors', ()))
    return {name: n for name, n in stages.items() if name not in ran and not (fallback / f'{name}.txt').is_file()}


def apply_stage(run, stage, command):
    run = Path(run)
    try:
        plans = json.loads((run / 'profile' / PLAN_NAME).read_text())
        plan = plans[stage]
    except (OSError, ValueError, KeyError):
        return _rebuild(run, stage, 'no reuse plan in this run', command)

    def refuse(reason):
        live = live_hazard(plan, run)
        if live:
            print(f"Reuse of {stage} failed: {reason}. It cannot be rebuilt in this run either: earlier reused "
                  f"stages ({', '.join(live)}) left out {sum(live.values())} files it replaces (first: "
                  f"{', '.join(plan['rebuild_hazard'][:3])}). Start a new build without --reuse-from.", flush=True)
            return 1
        return _rebuild(run, stage, reason, command)

    fallback = run / 'profile' / 'reuse-fallback'
    rebuilt = sorted(set(plan.get('rebuilt_ancestors', ()))
                     | {name for name in plan['ancestors'] if (fallback / f'{name}.txt').is_file()})
    # An earlier stage that ran in this build must have written exactly what it wrote in the old run
    # (BUILD-CACHE-NO-CUTOFF-33); then this stage's inputs are the old ones.
    differs = [name for name in rebuilt if not same_outputs(run, Path(plan['from']), name)]
    if differs:
        return refuse('an earlier stage it depends on ran again and its outputs differ from the old run: '
                      + ', '.join(differs))
    if rebuilt:
        print(f"{stage}: earlier stages ran again with outputs identical to the old run ({', '.join(rebuilt)}).",
              flush=True)
    for relative, expected in sorted(plan.get('inputs', {}).items()):
        path = run / relative
        if not path.is_file() or sha256_file(path) != expected:
            return refuse(f'its input {relative} differs from the old run')
    old = Path(plan['from'])
    link = plan.get('mode') in ('hardlink', 'pool')
    pool = plan.get('pool') if plan.get('mode') == 'pool' else None
    if link and hasattr(os, 'geteuid') and os.geteuid() == 0:
        print('Hard links refused as root (read-only protection does not apply); copying instead.', flush=True)
        link = False
    staged, created = [], []

    def make(folder):
        missing = []
        while not folder.exists():
            missing.append(folder)
            folder = folder.parent
        for path in reversed(missing):
            path.mkdir()
            created.append(path)

    try:
        for relative in sorted(plan['directories']):
            make(run / relative)
        for relative in sorted(plan['files']):
            make((run / relative).parent)
        staged = _stage_files(sorted(plan['files'].items()), run, old, pool, link)
    except (OSError, ValueError) as exc:
        staged = getattr(exc, 'staged', staged)
        # Leave the run exactly as before, so the stage can run on a clean state.
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        for folder in reversed(created):
            try:
                folder.rmdir()
            except OSError:
                pass
        return refuse(f'old output not usable ({exc})')
    for relative in plan['deleted']:
        path = run / relative
        if path.is_symlink() or path.is_file():
            path.unlink()
    for relative in sorted(plan['deleted_directories'], key=len, reverse=True):
        shutil.rmtree(run / relative, ignore_errors=True)
    for temporary, target in staged:
        os.replace(temporary, target)
    for relative, target in sorted(plan['links'].items()):
        path = run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or path.exists():
            path.unlink()
        os.symlink(target, path)
    size = sum(info['size'] for info in plan['files'].values())
    origin = f"prerendered {plan['prerendered']}" if plan.get('prerendered') else str(old)
    print(f"Reused stage {stage} from {origin} (fingerprint {plan['fingerprint']}): {len(plan['files'])} files, "
          f"{size:,} bytes on {apply_threads(len(plan['files']))} thread(s), every SHA-256 verified "
          f"({'links to the storage pool, read-only' if pool and link else 'hard links, read-only' if link else 'copies'}); "
          f"{plan.get('skipped_later_replaced', 0)} files are replaced by later reused stages.", flush=True)
    return 0


def old_run_steps(old_run, root=ROOT):
    """OLD_RUN's stage commands, pointed at the checkout ROOT and this interpreter."""
    state = json.loads((Path(old_run) / 'build-state.json').read_text())
    reused = (state.get('stage_cache') or {}).get('reused') or {}
    steps = []
    for step in state.get('steps', []):
        command = [str(part) for part in (reused.get(step['name']) or {}).get('original_command') or step['command']]
        script = stage_script(command)
        if script is not None:
            parts = script.as_posix().split('/')
            if 'tools' in parts:
                old_root = '/'.join(parts[:len(parts) - 1 - parts[::-1].index('tools')])
                command = [str(Path(root)) + part[len(old_root):] if old_root and (part == old_root or
                           part.startswith(old_root + '/')) else part for part in command]
        if command and Path(command[0]).name.startswith('python'):
            command[0] = sys.executable
        steps.append((step['name'], command))
    return steps, state


def predict(old_run, scope=DEFAULT_SCOPE, root=ROOT, dependencies=None, index=None, details=False):
    """{stage: None (fingerprint unchanged) or reason}: OLD_RUN's stages fingerprinted against ROOT now.

    A dry run: no outputs are checked, so the real plan can only reuse fewer stages
    (manifests, files replaced by later stages, damaged copies). Same game data and
    tools as OLD_RUN are assumed (its recorded hashes are used).
    """
    old_run = Path(old_run)
    steps, state = old_run_steps(old_run, root)
    old_cache = state.get('stage_cache') or {}
    try:
        old_details = json.loads((old_run / 'profile' / 'fingerprints.json').read_text())
    except (OSError, ValueError):
        old_details = {}
    index = index or SourceIndex(root, scope=scope, top_format=STAGE_TOP_FORMAT)
    fingerprints, components, problems, _ = fingerprint_steps(steps, old_run, state, index, dependencies)
    components = comparable_all(components, old_details, old_run)
    result = {}
    for name, _ in steps:
        if name in NON_REUSABLE:
            result[name] = NON_REUSABLE[name]
        elif problems.get(name):
            result[name] = '; '.join(problems[name])
        elif old_cache.get('schema') != CACHE_SCHEMA:
            result[name] = f"{old_run.name} has {old_cache.get('schema') or 'no'} fingerprints"
        elif (old_cache.get('fingerprints') or {}).get(name) != fingerprints[name]:
            changed = explain(old_details.get(name, {}), components[name]) if name in old_details else ['fingerprint']
            # Only stages before it changed: the build reuses it if they write the same outputs again
            # (early cutoff, BUILD-CACHE-NO-CUTOFF-33), as plan_reuse does; counted as reused (an upper bound).
            if all(part.startswith('dependency ') for part in changed):
                result[name] = None
            elif (name in old_details and only_sources_changed(old_details[name], components[name])
                  and narrowed_unchanged(old_run, name, index)[0]):
                result[name] = None   # narrowed reuse: what it used is unchanged (B7)
            else:
                result[name] = 'changed: ' + ', '.join(changed)
        else:
            result[name] = None
    return (result, components) if details else result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if '--' in argv:
        at = argv.index('--')
        argv, command = argv[:at], argv[at + 1:]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    apply = sub.add_parser('apply', help='(builder internal) apply a reused stage; the stage command follows --')
    apply.add_argument('--run', type=Path, required=True)
    apply.add_argument('--stage', required=True)
    explain_parser = sub.add_parser('explain', help='Why each stage of RUN would or would not be reused from OLD_RUN')
    explain_parser.add_argument('run', type=Path)
    explain_parser.add_argument('old_run', type=Path)
    predict_parser = sub.add_parser('predict', help='Dry run: which stages of OLD_RUN keep their fingerprint with this '
                                                    'checkout and environment (no build, no game data read)')
    predict_parser.add_argument('old_run', type=Path)
    predict_parser.add_argument('--fingerprint-scope', choices=SCOPES, default=DEFAULT_SCOPE)
    predict_parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'apply':
        return apply_stage(args.run, args.stage, command)
    if args.action == 'predict':
        result = predict(args.old_run, args.fingerprint_scope)
        if args.json:
            print(json.dumps(result, indent=1))
        else:
            for name, reason in result.items():
                print(f'  {"reuse  " if reason is None else "rebuild"} {name}' + ('' if reason is None else ': ' + reason))
            kept = sum(reason is None for reason in result.values())
            print(f'{kept} of {len(result)} stages keep their fingerprint (an upper bound: the build also checks outputs).')
        return 0
    new = json.loads((args.run / 'profile' / 'fingerprints.json').read_text())
    old = json.loads((args.old_run / 'profile' / 'fingerprints.json').read_text())
    for name, components in new.items():
        if name not in old:
            print(f'{name}: not in {args.old_run}')
        else:
            changed = explain(old[name], components)
            print(f"{name}: {'unchanged' if not changed else 'changed: ' + ', '.join(changed)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
