#!/usr/bin/env python3
"""Stage fingerprints, output manifests and explicit reuse of unchanged stages.

Every build records, for each stage, an input fingerprint and (after the stage
passed) a manifest of the files it created, changed or deleted in the run
folder. `tools/build.py --reuse-from OLD_RUN` then copies (or hard-links) the
outputs of stages whose fingerprint did not change, instead of running them.
Reuse is explicit and never silent: the build state, the stage log and the build
summary say "reused (fingerprint ...)" for every such stage.

A fingerprint covers everything a stage can depend on:
  * its command line, with the run folder and the --jobs value normalized
    (stage outputs do not depend on the worker count; the parallel tests and
    the from-scratch release gate check that contract);
  * the SHA-256 of every repository Python file it imports, transitively
    (static import scan, including imports inside functions), and of every
    non-Python repository file in a folder its code names (config/, engine/ ...);
  * the game input hashes from the build's input lock, when it reads game data;
  * the binaries it runs (map compilers, ffmpeg) and every other file or folder
    outside the run named on its command line;
  * AMIWIND_* environment variables, the Python version and package versions;
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
import time

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = 'amiwind-stage-outputs-v1'
PLAN_NAME = 'reuse-plan.json'
# Stages whose inputs are not fully fingerprinted always run.
NON_REUSABLE = {
    'engine': 'compiles with the Amiga SDK, whose files are not fingerprinted (about 15 s)',
    'image': 'final image: always assembled and verified from the stage outputs',
    'dry-run-image': 'final image: always assembled',
}
# Command options whose folder is a content-addressed cache the stage verifies itself.
CONTENT_ADDRESSED = {('npc-gallery', '--cache')}
IGNORED_ENV = {'AMIWIND_BUILD_JOBS', 'AMIWIND_INPUTS_LOCK', 'AMIWIND_PROFILE_SECTIONS',
               'AMIWIND_BUILD_PROFILE', 'AMIWIND_PROFILE_INTERVAL'}
EXTERNAL_DIRECTORY_LIMIT = 512 * 1024 ** 2
SKIP_DIRECTORIES = {'.git', '__pycache__', 'out', 'tests', 'node_modules'}
SKIP_PREFIXES = ('docs/images/',)
SKIP_SUFFIXES = ('.md', '.pyc')
PYTHON_ROOTS = ('tools', 'src', '')
PATH_CALLS = {'Path', 'PurePath', 'PurePosixPath', 'joinpath', 'join', 'open', 'child_ci', 'exists', 'isfile', 'isdir'}
# The profiler and this module are imported by every stage (through build_parallel) but never
# change a stage's outputs (tests/test_build_profile.py checks that); editing them keeps
# fingerprints, so a profiler fix does not force a full rebuild.
OUTPUT_NEUTRAL = {'tools/build_profile.py', 'tools/build_cache.py'}
RUN_PRIVATE = {'logs', 'profile', 'build-state.json', 'build-state.tmp', 'build-profile.json',
               'build-profile.json.tmp', 'build-summary.json', 'build-summary.tmp'}
TEMPORARY_SUFFIX = '.amiwind-reuse-tmp'


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

class SourceIndex:
    """SHA-256 of every repository file a stage may read (docs prose and tests excluded)."""

    def __init__(self, root=ROOT):
        self.root = Path(root)
        self._files = None
        self._closures = {}
        self._parsed = {}
        self._modules = {}

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
                        files[path] = sha256_file(full)
            self._files = files
        return self._files

    def _parse(self, relative):
        if relative not in self._parsed:
            text = (self.root / relative).read_text(encoding='utf-8', errors='replace')
            try:
                tree = ast.parse(text)
            except SyntaxError:
                self._parsed[relative] = ([], [], True)
                return self._parsed[relative]
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
            self._parsed[relative] = (imports, constants, False)
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
        script = Path(script).resolve()
        key = str(script)
        if key in self._closures:
            return self._closures[key]
        try:
            start = script.relative_to(self.root.resolve()).as_posix()
        except ValueError:
            self._closures[key] = (set(), set(), True)
            return self._closures[key]
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
        self._closures[key] = (python, data, uncertain)
        return self._closures[key]

    def digest(self, script):
        python, data, uncertain = self.closure(script)
        files = self.files
        if uncertain:
            selected = dict(files)
        else:
            selected = {path: files[path] for path in python | data if path in files}
        return digest_json(selected), len(selected), uncertain


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


def normalize_command(command, run):
    result = []
    skip_value = False
    for index, part in enumerate(map(str, command)):
        if skip_value:
            result.append('{JOBS}')
            skip_value = False
            continue
        if part == '--jobs':
            skip_value = True
            result.append(part)
            continue
        relative = under_run(part, run)
        result.append('{RUN}/' + relative if relative not in (None, '.') else ('{RUN}' if relative == '.' else part))
    return result


def stage_script(command):
    for part in map(str, command[1:3]):
        if part.endswith('.py'):
            return Path(part)
    return None


def external_inputs(name, command, run, metadata, skip_hashing=False, index=None):
    """{option=path: digest} of the paths outside the run named on the command line."""
    data_files = str(metadata.get('data_files') or '') or None
    tools = {str(Path(path)) for path in (metadata.get('tools') or {}).values()}
    tool_dirs = {str(Path(path).parent) for path in tools}
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
        if data_files and (str(path) == data_files or str(path).startswith(data_files.rstrip('/\\') + os.sep)):
            continue
        key = f'{option or "arg"}={part}'
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
        if path.is_file():
            result[key] = sha256_file(path)
            continue
        total, rows = 0, {}
        for file in sorted(p for p in path.rglob('*') if p.is_file()):
            total += file.stat().st_size
            if total > EXTERNAL_DIRECTORY_LIMIT:
                problems.append(f'{key}: folder larger than {EXTERNAL_DIRECTORY_LIMIT // 1024 ** 2} MiB is not fingerprinted')
                break
            rows[file.relative_to(path).as_posix()] = sha256_file(file)
        result[key] = digest_json(rows)
    return result, problems


def stage_components(name, command, run, metadata, index, dependencies, fingerprints):
    command = [str(part) for part in command]
    components = {'stage': name, 'command': normalize_command(command, run)}
    problems = []
    script = stage_script(command)
    if script is not None and script.is_file():
        digest, count, uncertain = index.digest(script)
        components['sources'] = {'digest': digest, 'files': count, 'scope': 'all files (dynamic import)' if uncertain else 'import closure'}
    else:
        components['sources'] = {'digest': digest_json(index.files), 'files': len(index.files), 'scope': 'all files (not a repository tool)'}
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
    components['environment'] = {key: value for key, value in sorted(os.environ.items())
                                 if key.startswith('AMIWIND_') and key not in IGNORED_ENV}
    if os.environ.get('PYTHONHASHSEED'):
        components['environment']['PYTHONHASHSEED'] = os.environ['PYTHONHASHSEED']
    components['python'] = {'version': sys.version, 'machine': platform.machine(),
                            'packages': {row['name']: row.get('detected') for row in metadata.get('version_comparison', [])
                                         if row.get('kind') == 'package'}}
    components['dependencies'] = {dep: fingerprints[dep] for dep in sorted(dependencies)}
    return components, problems


def fingerprint_steps(steps, run, metadata, index=None, dependencies=None):
    """({stage: fingerprint}, {stage: components}, {stage: [problems]}) for every stage."""
    index = index or SourceIndex()
    if dependencies is None:
        try:
            from build_parallel import stage_dependencies
            dependencies = stage_dependencies(steps)
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


def explain(old_components, new_components):
    """Which components of a stage fingerprint changed (for reports and refusals)."""
    changed = []
    for key in sorted(set(old_components) | set(new_components)):
        if old_components.get(key) != new_components.get(key):
            if key == 'dependencies':
                deps = [d for d in set(old_components.get(key, {})) | set(new_components.get(key, {}))
                        if old_components.get(key, {}).get(d) != new_components.get(key, {}).get(d)]
                changed.append('dependency ' + ', '.join(sorted(deps)))
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
        self.start = time.monotonic()
        plan = PLANS.pop(str(self.run), None)
        if plan is not None:
            (self.run / 'profile' / PLAN_NAME).write_text(json.dumps(plan) + '\n')
        details = DETAILS.pop(str(self.run), None)
        if details is not None:
            (self.run / 'profile' / 'fingerprints.json').write_text(json.dumps(details, indent=1, sort_keys=True) + '\n')

    def before(self, name, command):
        roots = self.roots.get(name) or output_roots(command, self.run)
        files, directories = snapshot(self.run, roots)
        inputs = input_files(self.original.get(name, command), self.run)
        self.state[name] = {'roots': roots, 'files': files, 'directories': directories,
                            'inputs': hash_files(self.run, inputs),
                            'top': set(os.listdir(self.run)) if self.run.is_dir() else set(),
                            'window': [round(time.monotonic() - self.start, 3), None]}

    def after(self, name, entry):
        state = self.state.pop(name, None)
        if state is None:
            return None
        state['window'][1] = round(time.monotonic() - self.start, 3)
        files, directories = snapshot(self.run, state['roots'])
        before = state['files']
        changed = sorted(path for path, info in files.items() if before.get(path) is None or before[path][:4] != info[:4]
                         or before[path][4] != info[4])
        regular = [path for path in changed if files[path][4] is None]
        hashes = hash_files(self.run, regular)
        reasons = []
        undeclared = sorted(set(os.listdir(self.run)) - state['top'] - RUN_PRIVATE - self.all_roots)
        if undeclared:
            reasons.append('created run-folder entries outside every declared stage path: ' + ', '.join(undeclared[:5]))
        manifest = {'schema': MANIFEST_SCHEMA, 'stage': name, 'status': 'complete',
                    'fingerprint': (self.cache.get('fingerprints') or {}).get(name),
                    'roots': state['roots'], 'window': state['window'], 'inputs': state['inputs'],
                    'files': {path: {'size': files[path][0], 'sha256': hashes[path],
                                     'mode': stat_module.S_IMODE(files[path][3])} for path in regular},
                    'links': {path: files[path][4] for path in changed if files[path][4] is not None},
                    'directories': sorted(directories - state['directories']),
                    'deleted': sorted(set(before) - set(files)),
                    'deleted_directories': sorted(state['directories'] - directories),
                    'reusable': not reasons, 'reasons': reasons}
        manifest['counts'] = {'files': len(regular), 'bytes': sum(files[path][0] for path in regular)}
        self.manifests[name] = manifest
        self._write(name, manifest)
        return manifest

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


# --------------------------------------------------------------------------
# Reuse planning (in the builder, before the stages start)

PLANS = {}    # run -> per-stage file plan, written into the run by Recorder
DETAILS = {}  # run -> fingerprint components, written into the run by Recorder


def load_manifest(run, name):
    path = Path(run) / 'profile' / 'manifests' / f'{name}.json'
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return manifest if manifest.get('schema') == MANIFEST_SCHEMA else None


def plan_reuse(steps, fingerprints, dependencies, components, problems, old_run):
    """({stage: plan}, {stage: reason not reused}) against a completed earlier run."""
    old_run = Path(old_run)
    state_path = old_run / 'build-state.json'
    if not state_path.is_file():
        raise ValueError(f'--reuse-from {old_run}: no build-state.json')
    state = json.loads(state_path.read_text())
    old_cache = state.get('stage_cache') or {}
    old_fingerprints = old_cache.get('fingerprints') or {}
    old_status = {step['name']: step.get('status') for step in state.get('steps', [])}
    try:
        old_details = json.loads((old_run / 'profile' / 'fingerprints.json').read_text())
    except (OSError, ValueError):
        old_details = {}
    names = [name for name, _ in steps]
    reasons, manifests = {}, {}
    for name in names:
        if name in NON_REUSABLE:
            reasons[name] = NON_REUSABLE[name]
        elif problems.get(name):
            reasons[name] = '; '.join(problems[name])
        elif old_status.get(name) != 'passed':
            reasons[name] = f'not passed in {old_run.name} ({old_status.get(name) or "absent"})'
        elif old_fingerprints.get(name) != fingerprints[name]:
            changed = explain(old_details.get(name, {}), components[name]) if name in old_details else ['fingerprint']
            reasons[name] = 'changed: ' + ', '.join(changed)
        else:
            manifest = load_manifest(old_run, name)
            if manifest is None:
                reasons[name] = 'no output manifest in the old run'
            elif manifest.get('status') != 'complete' or manifest.get('fingerprint') != fingerprints[name]:
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
    skips, verified = {}, {}
    while True:
        changed = True
        while changed:
            changed = False
            for name in sorted(candidates):
                missing = [dep for dep in dependencies.get(name, []) if dep not in candidates]
                if missing:
                    candidates.discard(name)
                    reasons[name] = 'depends on rebuilt stage ' + ', '.join(sorted(missing))
                    changed = True
                    continue
                # A path a later stage replaced is delivered by that stage, if it is reused too;
                # otherwise this stage's version no longer exists in the old run.
                skip = {}
                for path in (*manifests[name]['files'], *manifests[name]['links']):
                    later = writers[path][writers[path].index(name) + 1:]
                    if not later:
                        continue
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
    hazards = {}
    for name in candidates:
        for path, writer in skips[name].items():
            hazards.setdefault(writer, []).append(path)
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
                       # Files earlier reused stages left out because this stage replaces them:
                       # if this stage cannot be reused after all, it cannot be rebuilt either.
                       'rebuild_hazard': sorted(hazards.get(name, []))[:20],
                       'rebuild_hazard_count': len(hazards.get(name, []))}
    return plans, reasons


def prepare(steps, run, metadata, reuse_from=None, mode='copy', index=None):
    """Fingerprint every stage; with REUSE_FROM, swap reusable stages for verified copies.

    Records metadata['stage_cache'] (part of build-state.json) and returns the steps.
    """
    began = time.monotonic()
    index = index or SourceIndex()
    fingerprints, components, problems, dependencies = fingerprint_steps(steps, run, metadata, index)
    cache = {'schema': 'amiwind-stage-cache-v1', 'fingerprints': fingerprints, 'reuse_from': None, 'reused': {},
             'not_reused': {}, 'reuse_mode': None}
    DETAILS[str(run)] = components
    result = list(steps)
    if reuse_from is not None:
        reuse_from = Path(reuse_from).resolve()
        if reuse_from == Path(run).resolve():
            raise ValueError('--reuse-from must name an earlier run, not this one')
        plans, reasons = plan_reuse(steps, fingerprints, dependencies, components, problems, reuse_from)
        cache.update(reuse_from=str(reuse_from), not_reused=reasons, reuse_mode=mode)
        PLANS[str(run)] = {name: dict(plan, mode=mode) for name, plan in plans.items()}
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
                print(f'  reused  {name} (fingerprint {fingerprints[name][:12]})', flush=True)
            else:
                print(f'  rebuild {name}: {reasons.get(name, "")}', flush=True)
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


def _copy_verified(source, target, expected, mode, link):
    temporary = target.with_name(target.name + TEMPORARY_SUFFIX)
    if temporary.exists():
        temporary.unlink()
    try:
        if link:
            os.link(source, temporary)
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


def apply_stage(run, stage, command):
    run = Path(run)
    try:
        plans = json.loads((run / 'profile' / PLAN_NAME).read_text())
        plan = plans[stage]
    except (OSError, ValueError, KeyError):
        return _rebuild(run, stage, 'no reuse plan in this run', command)

    def refuse(reason):
        if plan.get('rebuild_hazard_count'):
            print(f"Reuse of {stage} failed: {reason}. It cannot be rebuilt in this run either: earlier reused "
                  f"stages left out {plan['rebuild_hazard_count']} files it replaces (first: "
                  f"{', '.join(plan['rebuild_hazard'][:3])}). Start a new build without --reuse-from.", flush=True)
            return 1
        return _rebuild(run, stage, reason, command)

    fallback = run / 'profile' / 'reuse-fallback'
    rebuilt = [name for name in plan['ancestors'] if (fallback / f'{name}.txt').is_file()]
    if rebuilt:
        return refuse('an earlier stage it depends on was rebuilt: ' + ', '.join(rebuilt))
    for relative, expected in sorted(plan.get('inputs', {}).items()):
        path = run / relative
        if not path.is_file() or sha256_file(path) != expected:
            return refuse(f'its input {relative} differs from the old run')
    old = Path(plan['from'])
    link = plan.get('mode') == 'hardlink'
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
        for relative, info in sorted(plan['files'].items()):
            target = run / relative
            make(target.parent)
            staged.append((_copy_verified(old / relative, target, info['sha256'], info['mode'], link), target))
    except (OSError, ValueError) as exc:
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
    print(f"Reused stage {stage} from {old} (fingerprint {plan['fingerprint']}): {len(plan['files'])} files, "
          f"{size:,} bytes, every SHA-256 verified ({'hard links, read-only' if link else 'copies'}); "
          f"{plan.get('skipped_later_replaced', 0)} files are replaced by later reused stages.", flush=True)
    return 0


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
    args = parser.parse_args(argv)
    if args.action == 'apply':
        return apply_stage(args.run, args.stage, command)
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
