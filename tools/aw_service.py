# SPDX-License-Identifier: GPL-3.0-only
"""aw submit / aw request: the request service of the master builder (phase 2). Standard library only.

A worker hands the build server one request in the aw-request-1 form (config/schemas/aw-request-1.json) and gets
back one result in the aw-result-1 form, written into the state folder (results/). The server checks the request
before anything expensive runs, names the run, leases it, runs the work in the configured container and records it:

    gate             the existing gate path (aw gate)
    build            the central build: entry check of the requested commit (VERSION = working version, the commit
                     contains the published integration head), the builder of THAT commit only (exported source,
                     PYTHONPATH from it), --developer-mode, the reuse preflight (source diff against the reuse source
                     + build.py --reuse-plan, refused when it plans rebuilds the diff does not explain), the shared
                     storage pool, the run name, refusal of retired flags, a trial line and the perf ingest
    miniwind         a MiniWind build of one test spot (options.preset: a preset recipe config/recipes/miniwind/
                     PRESET.json of THE requested commit, or a row of config/miniwind-presets.json for builders from
                     before the recipes): the same checks, run name, pool, receipts and trial line as kind build, the
                     builder given --miniwind-preset PRESET (which builds from that recipe); the result records the
                     recipe's SHA-256; the purpose is miniwind-<scene> (default miniwind-PRESET)
    chimport-region, smoke
                     accepted in the request form, refused as not yet implemented

A build request may carry a build recipe (options.recipe, tools/build_recipe.py, docs/BUILD_RECIPES.md) instead of or
next to its flags: the recipe file is staged into the build volume and handed to the builder with --recipe (flags then
win over the recipe, each difference recorded by the builder); its retired options are refused like retired flags and
its input files are hashed like declared inputs. Every passed build whose builder knows recipes saves its recipe
(--save-recipe); the server fills in checked_with (the run, the host time, the SHA-256 of the result record) and
writes it next to the result as <run name>.recipe.json.

Every docker and volume parameter comes from the "build" section of the config file (docs/AW.md); this file holds
no paths of its own.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

import aw
import build_recipe

NOT_YET = ('chimport-region', 'smoke')
# A MiniWind request: the test spot table of the requested commit (tools/miniwind_presets.py) and the options the
# server sets for it (the preset and MiniWind itself; say them in options.preset / options.description).
PRESET_TABLE = 'config/miniwind-presets.json'  # builders from before the build recipes
PRESET_RECIPES = 'config/recipes/miniwind'  # one recipe per preset (tools/miniwind_presets.py)
MINIWIND_MANAGED = ('--miniwind', '--miniwind-preset', '--miniwind-description')
OVERRIDES = ('retired-flags', 'unexplained-rebuilds', 'version-mismatch', 'build-hold', 'stair-walk-full')

# Retired builder options: (flag, value or None for any value, why). A build that names one is refused unless the
# request carries override.allow "retired-flags" (an A/B test of a historical regression; the run name says so).
RETIRED_FLAGS = (
    ('--legacy-area', None, 'legacy town chains are retired: every CHIM area is prepared CHIM-native'),
    ('--chim-native-towns', 'off', 'CHIM towns are prepared CHIM-native; "off" brings back the retired legacy town '
                                   'chains'),
    # a Vivec district frame (the Arena-only frame and the other cantons): all of Vivec is one CHIM frame,
    # vivec_city (project decision 2026-10-11 09:55 +0300); tools/retired_flags.py VIVEC_DISTRICTS
    *((flag, district, 'Vivec is one CHIM frame (vivec_city); a district frame is a retired legacy area')
      for flag in ('--chim-area', '--miniwind-town', '--extra-town')
      for district in ('vivec_arena', 'vivec_foreign', 'vivec_hlaalu', 'vivec_redoran', 'vivec_telvanni',
                       'vivec_temple', 'vivec_delyn', 'vivec_olms')),
)
REGRESSION_LABEL = 'ab-regression'

# Hashed stair walks are mandatory (BUILD-CHIM-STAIR-WALK-UNCACHED-36): once the published builder head has the
# records layer, a build of a commit without it is refused (merge the published builder), and a full walk of every
# map and frame again is a regression or beta test only: override.allow "stair-walk-full" with a reason; the run
# name carries the label.
REQUIRED_BUILDER_FILES = ('tools/stair_records.py',)
STAIR_WALK_FULL_LABEL = 'regression-beta-test'


def has_file(repo, rev, path):
    """True/False when REV in REPO has PATH; None when git cannot tell."""
    listed = git_text(repo, 'ls-tree', '--name-only', rev, '--', path)
    if listed is None:
        return None
    return path in listed.splitlines()


def builder_file_refusals(repo, commit, published, ref=None):
    """Refusals of a commit that lacks a builder file the published builder head has."""
    if not published:
        return []
    out = []
    for path in REQUIRED_BUILDER_FILES:
        if has_file(repo, published['head'], path) and has_file(repo, commit, path) is False:
            merge = f'git -C {repo} merge {ref or published["head"]}'
            out.append(f'HASHED STAIR WALKS: {commit[:7]} lacks {path}, which the published builder head '
                       f'{published["head"]} has: every build walks stairs through the records layer; merge the '
                       f'published builder first ({merge}), gate the merge, then ask again')
    return out


def stair_walk_full(flags):
    """True when FLAGS ask the builder to walk every map and frame again (--stair-walk-cache full)."""
    return any(name == '--stair-walk-cache' and value == 'full' for name, value in flag_pairs(flags))

# Options the build server sets itself; a request that names them is refused (say it in the request instead).
MANAGED_FLAGS = {
    '--name': 'the server names the run',
    '--workspace': 'the workspace comes from the server config or options.workspace',
    '--reuse-from': 'use options.reuse_from',
    '--reuse-mode': 'the server always reuses through the storage pool',
    '--storage-pool': 'the server always builds with the storage pool on',
    '--developer-mode': 'the server always builds in developer mode',
    '--devmode': 'the server always builds in developer mode',
    '--data-files': 'the game data mount comes from the server config',
    '--tools-dir': 'the tool folder comes from the server config',
    '--jobs': 'use options.jobs',
    '--source-commit': 'the server records the requested commit',
    '--accept-rebuild': 'use override.allow "unexplained-rebuilds" with a reason',
    '--accept-version-mismatch': 'use override.allow "version-mismatch" with a reason',
    '--any-run-name': 'the server names the run',
}

DEFAULT_BUILD = {
    'docker': 'docker',
    'user': '1000:1000',
    'mount': '/vol',
    'inputs_mount': '/owned',
    'source_dir': '{mount}/src/{series}-{commit}',
    'tools_dir': '/opt/amiwind-tools',
    'container_prefix': 'aw',
    'python': 'python3',
    'default_flags': [],
    'recipes_dir': '{mount}/src/recipes',
    'save_recipe': True,
}
RECIPE_FILE = 'build-recipe.json'  # what the builder writes into the run folder (--save-recipe)
RECIPE_MODULE = 'tools/build_recipe.py'  # a commit whose builder has it takes --recipe / --save-recipe

# Read-only summary of a finished run, printed as one JSON line (run inside the build container image).
SUMMARY_SCRIPT = r'''
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
out = {"run_dir": str(run), "found": False}
try:
    state = json.loads((run / "build-state.json").read_text())
except (OSError, ValueError) as exc:
    out["error"] = str(exc)
else:
    steps = state.get("steps") or []
    cache = state.get("stage_cache") or {}
    failed = [s.get("name") for s in steps if isinstance(s, dict) and s.get("status") == "failed"]
    out.update(found=True, status=state.get("status"), stages=len(steps), reused=len(cache.get("reused") or {}),
               rebuilt=len(cache.get("not_reused") or {}), failed_stage=failed[0] if failed else None,
               not_started=len(state.get("not_started") or []), elapsed_seconds=state.get("elapsed_seconds"),
               reuse_from=cache.get("reuse_from"), storage_pool=state.get("storage_pool"))
    # every CHIM frame over its memory budget, worst first, with how much (maintainer 2026-10-16: "whenever something is
    # over budget, I'd know how much over budget")
    over = []
    for report in sorted(run.glob("chim*/chim-heap.json")):
        try:
            frames = json.loads(report.read_text()).get("frames") or []
        except (OSError, ValueError):
            continue
        for f in frames:
            if isinstance(f, dict) and f.get("ok") is False and "peak_bytes" in f and "budget_bytes" in f:
                over.append({"report": str(report.relative_to(run)), "frame": f.get("frame"), "needs": f["peak_bytes"],
                             "budget": f["budget_bytes"], "over": f["peak_bytes"] - f["budget_bytes"]})
    out["over_budget"] = sorted(over, key=lambda o: -o["over"])
    try:
        out["recipe"] = json.loads((run / "build-recipe.json").read_text())
    except (OSError, ValueError):
        out["recipe"] = None
print(json.dumps(out, sort_keys=True))
'''


class Refused(aw.AwError):
    """A request refused before any work ran."""


# --------------------------------------------------------------------------
# The published integration head (the builder head broadcast)

def published_integration(config):
    """The newest PUBLISHED entry of the configured integration-head file: {'head', 'note', 'contains'} or None."""
    path = config.get('integration_head_file')
    if not path:
        return None
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError:
        return None
    for index, line in enumerate(lines):
        match = re.match(r'PUBLISHED\b[^:]*:\s+([0-9a-f]{7,40})\b\s*(.*)$', line.strip())
        if not match:
            continue
        contains = []
        for follow in lines[index + 1:]:
            if not follow.strip() or follow.startswith('PUBLISHED') or follow.startswith('PREVIOUS'):
                break
            contains.append(follow.strip())
        return {'head': match.group(1), 'note': match.group(2).strip(), 'contains': contains, 'file': str(path)}
    return None


# --------------------------------------------------------------------------
# Request checks

def request_errors(request):
    """Every reason the request form is malformed (empty = well-formed): the schema, then the kind's options."""
    if not isinstance(request, dict):
        return ['a request is a JSON object']
    errors = aw.validate(request, aw.schema('aw-request-1'))
    if errors:
        return errors
    options_schema = aw.schema('aw-request-1')['$defs'][request['kind']]
    errors += aw.validate(request.get('options') or {}, options_schema, '$.options')
    if any(re.match(r'[A-Za-z]:/', str(error.split("'")[1]) if "'" in error else '') for error in errors):
        errors.append('a container path became a Windows path (Git Bash rewrites /vol/...: run aw with '
                      'MSYS_NO_PATHCONV=1)')
    override = request.get('override')
    if override is not None and not override.get('allow'):
        errors.append('$.override: allow names no refusal to lift')
    recipe = (request.get('options') or {}).get('recipe') if request.get('kind') == 'build' else None
    if recipe is not None:
        errors += recipe_errors(recipe)
    return errors


def recipe_errors(recipe):
    """A request's recipe: the text's SHA-256 is the one stated, and the text is a well-formed recipe."""
    import hashlib
    text = recipe.get('text') or ''
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != recipe.get('sha256'):
        return ['$.options.recipe: the text\'s SHA-256 is not the stated sha256']
    try:
        document = json.loads(text)
    except ValueError as exc:
        return [f'$.options.recipe: not JSON: {exc}']
    return ['$.options.recipe: ' + error for error in build_recipe.document_errors(document)]


def recipe_document(request):
    recipe = (request.get('options') or {}).get('recipe')
    return json.loads(recipe['text']) if recipe else None


def recipe_retired_hits(document):
    """Retired options a recipe sets (tools/retired_flags.py rows: dest and the retired value)."""
    import retired_flags
    hits = []
    options = (document or {}).get('options') or {}
    for row in retired_flags.RETIRED:
        for dest in row.get('dests', (row['dest'],)):
            value = options.get(dest)
            if retired_flags.matches(row, value)[0]:
                hits.append(f'{row["flag"]} (recipe option {dest}: {json.dumps(value)}): {row["why"]}')
    return hits


def flag_pairs(flags):
    """(flag, value or None) for every --option in FLAGS ('--x=v', '--x v' or '--x')."""
    pairs = []
    flags = list(flags or [])
    for index, token in enumerate(flags):
        if not token.startswith('--'):
            continue
        name, equal, inline = token.partition('=')
        if equal:
            pairs.append((name, inline))
        elif index + 1 < len(flags) and not flags[index + 1].startswith('--'):
            pairs.append((name, flags[index + 1]))
        else:
            pairs.append((name, None))
    return pairs


def retired_hits(flags):
    hits = []
    for name, value in flag_pairs(flags):
        for flag, retired_value, why in RETIRED_FLAGS:
            if name == flag and (retired_value is None or value == retired_value):
                hits.append(f'{name}{" " + value if value else ""}: {why}')
    return hits


def managed_hits(flags):
    return [f'{name}: {MANAGED_FLAGS[name]}' for name, _ in flag_pairs(flags) if name in MANAGED_FLAGS]


def with_defaults(flags, defaults):
    """FLAGS plus each default group (['--flag', 'value'...]) whose flag the request does not name itself."""
    named = {name for name, _ in flag_pairs(flags)}
    result = list(flags or [])
    for group in defaults or []:
        group = [group] if isinstance(group, str) else list(group)
        if group and group[0] not in named:
            result += group
    return result


def allowed(request, what):
    override = request.get('override') or {}
    return what in (override.get('allow') or [])


def series(version):
    """'v036' for v0.0.36[-suffix]: v + minor + patch (v + major + minor + patch from 1.0.0 on)."""
    match = re.match(r'v?([0-9]+)\.([0-9]+)\.([0-9]+)', version)
    if not match:
        return 'v' + aw.safe_part(version)
    major, minor, patch = match.groups()
    return f'v{major if major != "0" else ""}{minor}{patch}'


def reuse_commit_of(reuse_from):
    """The git hash at the end of a reuse source's run name (YYYY_MM_DD_vX.Y.Z_<purpose>_<git>), or None."""
    match = aw.RUN_NAME.fullmatch(Path(str(reuse_from).rstrip('/')).name)
    return match.group('git') if match and match.group('git') != 'nogit' else None


def build_settings(config):
    build = dict(DEFAULT_BUILD)
    build.update(config.get('build') or {})
    missing = [key for key in ('image', 'volume', 'inputs_volume', 'workspace') if not build.get(key)]
    if missing:
        raise aw.AwError('the config has no build.' + ', build.'.join(missing) + ' (docs/AW.md "Config")')
    return build


# --------------------------------------------------------------------------
# Commands (pure: built from the config and the checked request; printed as they run)

def docker_run(build, name, args, mounts=(), extra=(), workdir=None, env=None, stdin=False, image=None):
    command = [build['docker'], 'run'] + (['-i'] if stdin else []) + [
        '--pull', 'never', '--rm', '--network', 'none', '--user', build['user'], '--name', name, *extra]
    for mount in mounts:
        command += ['-v', mount]
    if workdir:
        command += ['-w', workdir]
    for key, value in (env or {}).items():
        command += ['-e', f'{key}={value}']
    return command + [image or build['image'], *args]


def build_commands(config, request, facts, run_name):
    """Every command of one build request: {'source': (git argv, docker argv), 'inputs', 'check', 'build',
    'summary', 'ingest'} plus the run folder. 'check' = the build command itself with --check: the builder's own
    developer-mode block (version, imports, run name, the reuse preflight in the build's own environment) and its
    seconds-long build preflight, no stage run, nothing written. 'inputs' is None without declared input files,
    'ingest' None without an ingest config."""
    build = build_settings(config)
    options = request.get('options') or {}
    mount = build['mount']
    commit = facts['commit']
    source = build['source_dir'].format(mount=mount, series=series(facts['version']), commit=commit)
    workspace = options.get('workspace') or build['workspace']
    run_dir = f'{workspace.rstrip("/")}/build/{run_name}'
    prefix = build['container_prefix']
    env = {'PYTHONPATH': f'{source}/src:{source}/tools', 'AMIWIND_AW_REQUEST': request['id']}
    volume_rw, volume_ro = f'{build["volume"]}:{mount}:rw', f'{build["volume"]}:{mount}:ro'
    script = (f'S={shlex.quote(source)}; if [ -f "$S/VERSION" ]; then echo "aw: source exists"; cat > /dev/null; '
              f'else rm -rf "$S.part" && mkdir -p "$S.part" && tar -xf - -C "$S.part" && mv "$S.part" "$S"; fi; '
              f'cat "$S/VERSION"')
    commands = {
        'source': (['git', '-C', str(request['repo']), 'archive', '--format=tar', facts['full']],
                   docker_run(build, f'{prefix}-src-{commit}-{os.getpid()}', ['sh', '-c', script], [volume_rw],
                              stdin=True)),
        'inputs': None, 'ingest': None, 'run_dir': run_dir, 'source_dir': source,
    }
    reuse = options.get('reuse_from')
    declared = [item['path'] for item in options.get('inputs') or []]
    if declared:
        commands['inputs'] = docker_run(build, f'{prefix}-inputs-{run_name}', ['sha256sum', '--', *declared],
                                        [volume_ro])
    flags = with_defaults(options.get('flags'), build.get('default_flags'))
    recipe = options.get('recipe')
    commands['recipe'] = None
    if recipe:
        folder = build['recipes_dir'].format(mount=mount)
        commands['recipe_path'] = f'{folder}/{run_name}.json'
        stage = (f'D={shlex.quote(folder)}; P="$D/{run_name}.json"; mkdir -p "$D" && cat > "$P.part" && '
                 f'mv "$P.part" "$P" && sha256sum "$P"')
        commands['recipe'] = docker_run(build, f'{prefix}-recipe-{run_name}', ['sh', '-c', stage], [volume_rw],
                                        stdin=True)
    args = [build['python'], 'tools/build.py', '--data-files', build['inputs_mount'], '--workspace', workspace,
            '--name', run_name, '--source-commit', commit, '--tools-dir', build['tools_dir'],
            '--jobs', str(options.get('jobs') or build.get('jobs') or 24)]
    if reuse:
        args += ['--reuse-from', reuse, '--reuse-mode', 'pool']
    args += ['--storage-pool', 'on', '--developer-mode']
    if allowed(request, 'unexplained-rebuilds') and reuse:
        args += ['--accept-rebuild']
    if facts.get('version_mismatch') and allowed(request, 'version-mismatch'):
        args += ['--accept-version-mismatch', request['override']['reason']]
    if recipe:
        args += ['--recipe', commands['recipe_path']]
    args += flags
    save = []
    if facts.get('recipes') and build.get('save_recipe', True):
        save = ['--save-recipe', f'{run_dir}/{RECIPE_FILE}']
    extra = ['--cpus', str(options.get('cpus') or build.get('cpus') or 24),
             '--memory', str(options.get('memory') or build.get('memory') or '44g')]
    mounts = [f'{build["inputs_volume"]}:{build["inputs_mount"]}:ro', volume_rw]
    # rw only because the build preflight checks that the caches are writable; --check returns before the input
    # lock, the run folder or any stage
    check = ['--check']
    if facts.get('resource_plan'):
        # the resource plan of THIS build against the container it will get (its --memory and --cpus), in the check
        check += ['--resource-plan', '--resource-memory-gb', '%g' % aw.memory_gib(extra[3]),
                  '--resource-threads', str(extra[1])]
    commands['check'] = docker_run(build, f'{prefix}-check-{run_name}', args + check, mounts,
                                   extra=['--cpus', str(build.get('check_cpus') or 4)], workdir=source, env=env)
    commands['build'] = docker_run(build, f'{prefix}-build-{run_name}', args + save, mounts, extra=extra,
                                   workdir=source, env=env)
    commands['summary'] = docker_run(build, f'{prefix}-summary-{run_name}',
                                     [build['python'], '-c', SUMMARY_SCRIPT, run_dir], [volume_ro])
    # after a PASSED build only: its stair-walk records become reusable (tools/stair_records.py; they were
    # candidates until now); the step's JSON line carries the reuse counts into the result
    commands['stair-records'] = docker_run(build, f'{prefix}-stair-records-{run_name}',
                                           [build['python'], 'tools/stair_records.py', 'promote', '--run', run_dir,
                                            '--request', request['id']], [volume_rw], workdir=source, env=env)
    # the perf guard's verdict (tools/perf_guard.py, written by build.py at the end of the build); exit 1 = failed
    commands['perf-guard'] = docker_run(build, f'{prefix}-perf-guard-{run_name}',
                                        [build['python'], 'tools/perf_guard.py', 'show', run_dir, '--json'],
                                        [volume_ro], workdir=source, env=env)
    ingest = build.get('ingest')
    if ingest:
        fill = {'run_dir': run_dir, 'run_name': run_name, 'purpose': request['purpose'], 'mount': mount}
        commands['ingest'] = docker_run(
            build, f'{prefix}-ingest-{run_name}', [str(part).format(**fill) for part in ingest['command']],
            [volume_ro, *ingest.get('mounts', [])], image=ingest.get('image'))
    commands['flags'] = flags
    commands['volume_ro'] = volume_ro
    return commands


def show(command):
    """One command line for logs and results (the long inline summary script shortened)."""
    parts = ['<summary script>' if part == SUMMARY_SCRIPT else part for part in command]
    return ' '.join(shlex.quote(str(part)) for part in parts)


# --------------------------------------------------------------------------
# Running (a small runner so tests replace docker and git)

class Runner:
    def __init__(self, echo=True):
        self.echo = echo

    def capture(self, command, timeout=None):
        """(exit, stdout, stderr)."""
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=timeout)
        return result.returncode, result.stdout, result.stderr

    def pipe(self, producer, consumer):
        """PRODUCER | CONSUMER; (exit of both, consumer stdout, stderr)."""
        first = subprocess.Popen(producer, stdout=subprocess.PIPE)
        second = subprocess.run(consumer, stdin=first.stdout, capture_output=True, text=True, encoding='utf-8',
                                errors='replace')
        first.stdout.close()
        code = first.wait()
        return (code or second.returncode), second.stdout, second.stderr

    def logged(self, command, log_path):
        return aw.run_logged(command, dict(os.environ), log_path, echo=self.echo)

    def feed(self, command, data):
        """COMMAND with DATA (bytes) on its stdin; (exit, stdout, stderr)."""
        result = subprocess.run(command, input=data, capture_output=True)
        return (result.returncode, result.stdout.decode('utf-8', 'replace'),
                result.stderr.decode('utf-8', 'replace'))


def git_text(repo, *args):
    return aw.git(repo, *args)


def commit_facts(config, request):
    """The requested commit in the request's repository: full and short hash, its VERSION, the working version and
    integration head findings. Raises Refused when the commit cannot be read."""
    repo = request['repo']
    full = git_text(repo, 'rev-parse', '--verify', '--quiet', request['commit'] + '^{commit}')
    if not full:
        raise Refused(f'commit {request["commit"]} is not in {repo}')
    text = git_text(repo, 'show', f'{full}:VERSION')
    if not text:
        raise Refused(f'commit {full[:7]} has no VERSION file')
    version = 'v' + text.strip().lstrip('v')
    # Builders from the build-recipes change on take --recipe / --save-recipe (git cat-file -e prints nothing).
    recipes = git_text(repo, 'cat-file', '-e', full + ':' + RECIPE_MODULE) is not None
    # Builders with the resource plan (tools/resource_plan.py) take --resource-plan on the check
    resources = git_text(repo, 'cat-file', '-e', full + ':' + RESOURCE_MODULE) is not None
    return {'full': full, 'commit': full[:7], 'version': version, 'recipes': recipes, 'resource_plan': resources}


RESOURCE_MODULE = 'tools/resource_plan.py'
RESOURCE_PLAN_EXIT = 5   # tools/build.py --resource-plan: a stage's single unit is larger than the build's memory


# --------------------------------------------------------------------------
# Results

def result_document(request, run_name, status, started, t0, **fields):
    document = {'schema': 'aw-result-1', 'request_id': request['id'], 'kind': request['kind'], 'status': status,
                'version': fields.pop('version', request['version']), 'commit': fields.pop('commit', request['commit']),
                'run_name': run_name, 'time': aw.stamp(), 'started': started, 'finished': aw.stamp(),
                'seconds': round(time.time() - t0, 1), 'numbers': {}, 'steps': {}, 'failed_steps': [],
                'failures': [], 'artifacts': [], 'logs': [], 'timings': {}, 'reuse': {'applicable': False},
                'leases': [], 'notes': [], 'requester': request['requester'], 'reason': request['reason'],
                'override': request.get('override')}
    document.update(fields)
    document['failed_steps'] = [name for name, step in document['steps'].items() if not step['ok']]
    return document


def write_result(config, document):
    folder = aw.state_dir(config) / 'results'
    folder.mkdir(exist_ok=True)
    path = folder / f'{document["run_name"]}.json'
    document['artifacts'] = document['artifacts'] + [str(path)]
    aw.write_json(path, aw.checked(document, 'aw-result-1'))
    aw.log_trial(config, 'result', path=str(path), sha256=aw.file_sha256(path), result={
        key: document.get(key) for key in (
        'request_id', 'kind', 'status', 'version', 'commit', 'run_name', 'numbers', 'failed_steps', 'failed_stage',
        'seconds', 'dry_run', 'requester', 'reason', 'stair_walk', 'perf_guard')})
    aw.perf_db_post(config, document, path)     # after the file is final: the database reads it as written
    return path


def save_request(config, request):
    folder = aw.state_dir(config) / 'requests'
    folder.mkdir(exist_ok=True)
    path = folder / f'{request["id"]}.json'
    aw.write_json(path, request)
    return path


def append_trial(config, line):
    path = (config.get('build') or {}).get('trials_log')
    if not path:
        return None
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(line, sort_keys=True) + '\n')
    return path


# --------------------------------------------------------------------------
# Kinds

def submit(config, request, dry_run=False, runner=None, quiet=False):
    """Checks REQUEST, runs it, writes its result; returns (exit code, result path or None)."""
    errors = request_errors(request)
    if errors:
        aw.log_trial(config, 'refused-request', errors=errors[:20],
                     request_id=request.get('id') if isinstance(request, dict) else None)
        raise Refused('malformed request: ' + '; '.join(errors[:8]))
    print(f'aw submit: request {save_request(config, request)}')
    aw.log_trial(config, 'request', request=request)
    if request['kind'] == 'gate':
        return submit_gate(config, request), None
    if request['kind'] in NOT_YET:
        return refuse(config, request, [f'kind {request["kind"]} is not implemented yet by the build server '
                                        '(the request form is fixed; use kind build or gate)'])
    if request['kind'] == 'miniwind':
        try:
            request = miniwind_build_request(config, request)
        except Refused as exc:
            return refuse(config, request, [str(exc)])
    return submit_build(config, request, dry_run or bool((request.get('options') or {}).get('dry_run')),
                        runner or Runner(echo=not quiet))


def git_blob(repo, commit, path):
    """The bytes of PATH at COMMIT (exactly, for a SHA-256), or None."""
    try:
        result = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', f'{commit}:{path}'], capture_output=True,
                                timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def preset_recipe(repo, commit, preset):
    """The preset's recipe at COMMIT as options.recipe-like facts (name, sha256, file), or None (no such recipe)."""
    import hashlib
    path = f'{PRESET_RECIPES}/{preset}.json'
    raw = git_blob(repo, commit, path)
    try:
        document = json.loads(raw.decode('utf-8')) if raw else None
    except (ValueError, UnicodeError):
        return None
    if not isinstance(document, dict) or document.get('name') != preset or build_recipe.document_errors(document):
        return None
    return {'name': preset, 'sha256': hashlib.sha256(raw).hexdigest(), 'file': path}


def preset_names(repo, commit):
    """Test spot names at COMMIT (the requested builder's own): its preset recipes, else the rows of the earlier
    table config/miniwind-presets.json; None when it has neither."""
    listing = git_text(repo, 'ls-tree', '--name-only', commit, PRESET_RECIPES + '/') or ''
    names = [Path(line).stem for line in listing.splitlines() if line.strip().endswith('.json')]
    if names:
        return names
    text = git_text(repo, 'show', f'{commit}:{PRESET_TABLE}')
    if not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    rows = data.get('presets') if isinstance(data, dict) else None
    return [row.get('name') for row in rows if isinstance(row, dict)] if isinstance(rows, list) else None


def miniwind_build_request(config, request):
    """A miniwind request as the build request the server runs (the kind stays 'miniwind' in the result): the preset
    checked against the requested commit's table, the MiniWind options the server owns refused in the flags, the
    purpose miniwind-<scene>. Raises Refused."""
    options = dict(request.get('options') or {})
    preset = options.pop('preset', None)
    description = options.pop('description', None)
    if not preset:
        raise Refused('a miniwind request names its test spot: options.preset (a row of ' + PRESET_TABLE + ')')
    names = preset_names(request['repo'], request['commit'])
    if names is None:
        raise Refused(f'commit {request["commit"]} has no readable {PRESET_TABLE}: its builder cannot take a preset')
    if preset not in names:
        raise Refused(f'unknown MiniWind preset {preset} at {request["commit"]}; presets: {", ".join(names)}')
    flags = list(options.get('flags') or [])
    owned = sorted({name for name, _ in flag_pairs(flags)
                    if name in MINIWIND_MANAGED or name in {'--miniwind-' + n for n in names}})
    if owned:
        raise Refused('flag ' + ', '.join(owned) + ': the server sets the MiniWind options (options.preset, '
                      'options.description)')
    purpose = request['purpose']
    if purpose == 'miniwind':
        purpose = 'miniwind-' + preset
    if not purpose.startswith('miniwind-'):
        raise Refused(f'a miniwind run is named miniwind-<scene>: purpose {purpose} (default miniwind-{preset})')
    options['flags'] = ['--miniwind-preset', preset] + (['--miniwind-description', description]
                                                          if description else []) + flags
    converted = dict(request, purpose=purpose, options=options)
    recipe = preset_recipe(request['repo'], request['commit'], preset)
    if recipe is not None:
        converted['_preset_recipe'] = recipe  # the result records the recipe the builder reads (its SHA-256)
    return converted


def free(config, lease, requester):
    """Releases a run-name lease (a preview name was never leased) and the build's core lease, whose cores go to
    the builds still running (docker update --cpus)."""
    if lease.get('status') != 'preview':
        aw.release(config, lease['id'], requester)
    cores = lease.pop('_cores', None)
    if cores:
        apply_core_changes(config, cores['runner'], aw.release_cores(config, cores['lease']['id'], requester))


def core_priority(request):
    """release-critical > dev > optional: the request's options.priority, else release for release/rc purposes."""
    options = request.get('options') or {}
    if options.get('priority'):
        return options['priority']
    return 'release' if re.match(r'(release|rc\d*)\b', str(request.get('purpose') or '')) else 'dev'


def apply_core_changes(config, runner, changes):
    """Resize running build containers to their new core share (docker update --cpus); returns note lines."""
    docker = build_settings(config).get('docker', 'docker')
    lines = []
    for container, old, new in changes:
        if not container:
            continue
        code, _, err = runner.capture([docker, 'update', '--cpus', str(new), container], timeout=60)
        lines.append(f'core lease rebalance: {container} {old} -> {new} cores'
                     + ('' if code == 0 else f' (docker update failed: {(err or "").strip()[:120]})'))
    for line in lines:
        print('aw submit: ' + line, flush=True)
    return lines


QUEUE_POLL_S = 30


def memory_lease(config, asked=None):
    """The GiB a build leases and a note, or None (AW-LEASE-MEMORY-DEADLOCK-36). A request that can never fit
    (more than the host's memory less its reserve) is refused at once instead of waiting in the queue. The default
    (build.memory) is sized down so that it fits beside one running gate; an explicit --memory that only fits while
    no gate runs is kept, with a note."""
    host_mem, reserve, gate_mem = aw.memory_settings(config)
    build = build_settings(config)
    memory = aw.memory_gib(asked or build.get('memory') or '44g')
    ceiling = host_mem - reserve
    if memory > ceiling + 1e-9:
        raise aw.AwError(f'can never fit: {memory:g} GiB wanted, the host leases at most {ceiling:g} GiB '
                         f'({host_mem:g} less {reserve:g} reserved); ask for less with --memory')
    beside_gate = ceiling - gate_mem
    if memory > beside_gate + 1e-9:
        if not asked:
            return beside_gate, (f'memory lease {beside_gate:g} GiB instead of the default {memory:g} GiB, so the '
                                 f'build fits beside a running gate ({gate_mem:g} GiB)')
        return memory, (f'{memory:g} GiB fits only while no gate runs (a gate holds {gate_mem:g} GiB of '
                         f'{ceiling:g}); it waits for a moment without gates')
    return memory, None


def machine_state(config, request, run_name, threads, memory_gib):
    """The machine at this start, one line (build.machine_state_command: e.g. a launch registry's `state`; the
    command prints the line and, last, a JSON object with "busy" and "line"). Returns the reason to wait when the
    host is busy (above its threshold for the last minute), else None. No command configured: nothing."""
    command = (build_settings(config).get('machine_state_command') or None)
    if not command:
        return None
    argv = [str(part) for part in command] + ['--owner', str(request.get('requester') or 'aw'), '--purpose',
                                              f'aw build {run_name}', '--threads', str(threads),
                                              '--mem-gb', '%g' % memory_gib, '--json']
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=180)
        state = json.loads((done.stdout.strip().splitlines() or ['{}'])[-1])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'aw submit: {run_name}: machine state unknown ({type(exc).__name__}: {exc})', flush=True)
        return None
    if state.get('line'):
        print(f'aw submit: {run_name}: {state["line"]}', flush=True)
    return state.get('wait_reason') if state.get('busy') else None


def take_cores(config, request, run_name, runner, notes, sleep=time.sleep):
    """The build's core and memory lease (docs/AW.md "Core leases"): (request with options cpus = jobs = the leased
    cores and memory = the leased GiB, lease info for the result, lease or None). A request that does not fit waits
    in the queue (release-critical first) up to build.queue_timeout_s, then raises aw.AwError."""
    host, minimum, gate_cores, enabled = aw.core_settings(config)
    options = dict(request.get('options') or {})
    if not enabled:
        return request, None, None
    build = build_settings(config)
    priority = core_priority(request)
    want = int(options.get('cpus') or options.get('jobs') or build.get('cpus') or host)
    memory, fit = memory_lease(config, options.get('memory'))
    if fit:
        notes.append(fit)
        print(f'aw submit: {run_name}: {fit}', flush=True)
    container = f'{build["container_prefix"]}-build-{run_name}'
    timeout = float(build.get('queue_timeout_s', 6 * 3600))
    poll = float(build.get('queue_poll_s', QUEUE_POLL_S))
    waited, said = 0.0, None
    while True:
        busy = machine_state(config, request, run_name, min(want, host), memory)
        if busy:
            if busy != said:
                print(f'aw submit: {run_name}: waiting ({priority}): {busy}', flush=True)
                said = busy
            if waited >= timeout:
                aw.dequeue(config, run_name, request['requester'])
                raise aw.AwError(f'{busy} (waited {waited:.0f} s, timeout {timeout:.0f} s)')
            # keep a ticket queued earlier alive while the machine is busy (AW-QUEUE-DEAD-TICKET-54)
            aw.touch_ticket(config, run_name, request['requester'])
            sleep(poll)
            waited += poll
            continue
        if waited and config.get('_path'):
            # a waiting request reads the config again, so a changed lease size or gate reserve reaches it
            # (AW-LEASE-MEMORY-DEADLOCK-36)
            config = aw.load_config(config['_path'])
            memory, _ = memory_lease(config, options.get('memory'))
        lease, changes = aw.lease_cores(config, run_name, request['requester'], priority, min(want, host), container,
                                        purpose=request.get('purpose', ''), reason=request.get('reason', ''),
                                        memory_gib=memory, ticket=run_name)
        if lease is not None:
            break
        if changes != said:
            print(f'aw submit: {run_name}: queued ({priority}): {changes}', flush=True)
            said = changes
        if waited >= timeout:
            aw.dequeue(config, run_name, request['requester'])
            raise aw.AwError(f'{changes} (queued {waited:.0f} s, timeout {timeout:.0f} s)')
        sleep(poll)
        waited += poll
    if said is not None:
        notes.append(f'queued {waited:.0f} s for cores and memory ({said})')
    rebalanced = apply_core_changes(config, runner, changes)
    notes.extend(rebalanced)
    # --jobs is the lease at the start; the CPU quota (--cpus) follows rebalances while the build runs, the worker
    # pools do not (AW-LEASE-NO-GROW-36: resizing them through the builder's jobs file is the open repair)
    options.update(cpus=lease['cores'], jobs=lease['cores'], memory=f'{memory:g}g')
    info = {'priority': priority, 'wanted': want, 'leased': lease['cores'], 'host_threads': host,
            'memory_gib': memory, 'queued_s': waited, 'lease': lease['id'], 'rebalanced': rebalanced}
    notes.append(f'core lease {lease["id"]}: {lease["cores"]} of {host} threads and {memory:g} GiB ({priority} '
                 f'priority; wanted {want} cores); --jobs, --cpus and --memory follow the lease')
    return dict(request, options=options), info, lease


def refuse(config, request, refusals, run_name=None, **fields):
    """A refusal result; the run name is leased and released so the name records the attempt."""
    started, t0 = aw.stamp(), time.time()
    if run_name is None:
        lease = aw.lease_run_name(config, request['repo'], request['purpose'], request['requester'],
                                  request['reason'], version=fields.get('version', request['version']),
                                  commit=fields.get('commit', request['commit']), record=False)
        run_name = lease['key']
        fields.setdefault('leases', [lease['id']])
    fields.setdefault('steps', {'checks': {'exit': None, 'ok': False, 'detail': refusals[0][:200]}})
    document = result_document(request, run_name, 'refused', started, t0, refusals=refusals,
                               notes=list(refusals), **fields)
    path = write_result(config, document)
    for text in refusals:
        print(f'aw submit: REFUSED: {text}', file=sys.stderr)
    print(f'aw submit: result {path}')
    return aw.EXIT['refused'], path


def submit_gate(config, request):
    options = request.get('options') or {}
    args = argparse.Namespace(
        repo=request['repo'], commit=request['commit'], reason=request['reason'], range=options.get('range'),
        number=options.get('number'), requester=request['requester'], allow_dirty=bool(options.get('allow_dirty')),
        accept_version_mismatch=(request['override']['reason'] if allowed(request, 'version-mismatch') else None),
        quiet=bool(options.get('quiet')))
    return aw.cmd_gate(args, config)


CHECK_LINE = re.compile(r'\(f\) reuse preflight: (?P<reused>[0-9]+) of (?P<stages>[0-9]+) stages reusable, '
                        r'(?P<rebuilt>[0-9]+) rebuilt, (?P<unexpected>[0-9]+) unexpected'
                        r'(?:, keys too broad: (?P<too_broad>.*))?$')


def parse_check(text):
    """What build.py ... --check printed: the developer-mode verdict, its reuse preflight line (f), its REFUSED
    lines, the first Error line and whether the checks completed."""
    found = {'developer_mode': None, 'preflight': None, 'refusals': [], 'error': None, 'completed': False,
             'line': None, 'resources': []}
    for raw in (text or '').splitlines():
        line = raw.strip()
        if line.startswith(('Resource plan:', 'ADVISORY:', 'WILL THROTTLE', 'WILL NOT FIT', 'Machine at start:')):
            found['resources'].append(line)
        match = re.match(r'Developer mode: (OK|REFUSED)', line)
        if match:
            found['developer_mode'] = match.group(1)
        if line.startswith('(f) reuse preflight:'):
            found['line'] = line
            match = CHECK_LINE.search(line)
            if match:
                pre = {key: int(match.group(key)) for key in ('reused', 'stages', 'rebuilt', 'unexpected')}
                pre['too_broad'] = [part.strip() for part in (match.group('too_broad') or '').split(',')
                                    if part.strip()]
                found['preflight'] = pre
            else:
                found['preflight'] = {'error': line.split(':', 1)[1].strip()}
        if line.startswith('REFUSED:'):
            found['refusals'].append(line[len('REFUSED:'):].strip())
        if line.startswith('Error:') and found['error'] is None:
            found['error'] = line[len('Error:'):].strip()
        if line.startswith('Checks completed.'):
            found['completed'] = True
    return found


def source_diff(request, facts, notes):
    """The files changed between the reuse source's commit and the requested commit (git, on the host)."""
    options = request.get('options') or {}
    old = options.get('reuse_from_commit') or reuse_commit_of(options.get('reuse_from'))
    info = {'applicable': True, 'from': options.get('reuse_from'), 'from_commit': old}
    if not old:
        notes.append('source diff: the reuse source names no commit (give options.reuse_from_commit)')
        return info
    names = git_text(request['repo'], 'diff', '--name-only', old, facts['full'])
    if names is None:
        notes.append(f'source diff: commit {old} of the reuse source is not in {request["repo"]}')
        return info
    files = [line for line in names.splitlines() if line.strip()]
    info.update(diff_files=len(files), diff_sample=files[:40])
    print(f'aw submit: source diff {old}..{facts["commit"]}: {len(files)} files'
          + (': ' + ', '.join(files[:8]) + (' ...' if len(files) > 8 else '') if files else ''), flush=True)
    return info


def preflight_check(request, commands, runner, notes, reuse_info):
    """The builder's own developer-mode check of this exact build (the build command + --check: same flags, same
    environment, so the same reuse preflight the build prints as "(f)"). Returns (step, refusals) and fills
    REUSE_INFO with the reuse preflight numbers."""
    code, out, err = runner.capture(commands['check'], timeout=1800)
    found = parse_check((out or '') + '\n' + (err or ''))
    refusals, problems = [], []
    # the resource plan (tools/resource_plan.py): its checklist into the result; WILL NOT FIT refuses here
    for line in found['resources']:
        if line.startswith(('ADVISORY:', 'WILL THROTTLE', 'WILL NOT FIT')) or line.startswith('Resource plan: ') and \
                line.split(':', 1)[1].strip().split(' ')[0] in ('OK', 'THROTTLED', 'REFUSED'):
            notes.append('resource plan: ' + line)
            print('aw submit: resource plan: ' + line, flush=True)
    if code == RESOURCE_PLAN_EXIT and found['completed']:
        problems.append('resource plan: WILL NOT FIT: a stage\'s single unit is larger than the memory this build '
                        'gets (' + '; '.join(line for line in found['resources'] if 'WILL NOT FIT' in line)[:400]
                        + '); ask for more memory')
        code = 0
    pre = found['preflight']
    if pre and 'error' not in pre:
        reuse_info.update(stages=pre['stages'], planned_reuse=pre['reused'], planned_rebuild=pre['rebuilt'],
                          unexpected=pre['unexpected'], too_broad=pre['too_broad'])
        print('aw submit: ' + found['line'][4:], flush=True)
        if pre['too_broad']:
            problems.append(f'the reuse preflight rebuilds {len(pre["too_broad"])} stage(s) the source diff does '
                            f'not explain ({", ".join(pre["too_broad"][:8])}): a stage key too broad (HOLD-LEVEL)')
        if pre['unexpected']:
            problems.append(f'the reuse preflight has {pre["unexpected"]} UNEXPECTED rebuild(s) (old records '
                            'refused or damaged): check the reuse source')
    elif (request.get('options') or {}).get('reuse_from'):
        detail = pre['error'] if pre else 'no "(f) reuse preflight" line'
        problems.append(f'the reuse preflight did not answer: {detail}')
    if problems and allowed(request, 'unexplained-rebuilds'):
        notes.append('override (unexplained-rebuilds): ' + request['override']['reason'] + ': '
                     + '; '.join(problems))
        problems = []
    refusals += problems
    if code != 0 or not found['completed']:
        refusals += [f'developer mode: {text}' for text in found['refusals']]
        if found['error'] and not any(text in found['error'] for text in found['refusals']):
            refusals.append(f'build check: {found["error"]}')
        if not found['refusals'] and not found['error']:
            refusals.append(f'build check exited {code} without "Checks completed"')
    detail = (found['line'] or '')[4:] or ('checks completed' if found['completed'] else f'exit {code}')
    return {'exit': code, 'ok': not refusals, 'detail': detail[:200]}, refusals


def verify_inputs(request, commands, runner):
    """SHA-256 of every declared input file in the build volume against the request. Returns (step, records,
    refusals)."""
    declared = (request.get('options') or {}).get('inputs') or []
    if not declared:
        return None, [], []
    code, out, _ = runner.capture(commands['inputs'], timeout=900)
    seen = {}
    for line in (out or '').splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and re.fullmatch(r'[0-9a-f]{64}', parts[0]):
            seen[parts[1].lstrip('*')] = parts[0]
    records, refusals = [], []
    for item in declared:
        actual = seen.get(item['path'])
        records.append({'path': item['path'], 'sha256': actual, 'expected': item['sha256'],
                        **({'role': item['role']} if item.get('role') else {})})
        if actual is None:
            refusals.append(f'input {item["path"]}: not readable in the build volume')
        elif actual != item['sha256']:
            refusals.append(f'input {item["path"]}: sha256 {actual[:12]}... is not the requested '
                            f'{item["sha256"][:12]}...')
    detail = f'{len(declared) - len(refusals)} of {len(declared)} input files match their sha256'
    return {'exit': code, 'ok': not refusals, 'detail': detail}, records, refusals


def existing_runs(config, request, runner, notes):
    """Run names already in the workspace's build folder (read-only listing), so a new name gets -tryN."""
    build = build_settings(config)
    workspace = (request.get('options') or {}).get('workspace') or build['workspace']
    command = docker_run(build, f'{build["container_prefix"]}-ls-{os.getpid()}',
                         ['ls', '-1', f'{workspace.rstrip("/")}/build'], [f'{build["volume"]}:{build["mount"]}:ro'])
    try:
        code, out, err = runner.capture(command, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        code, out, err = None, '', str(exc)
    if code != 0:
        notes.append(f'run names on disk not listed (exit {code}): {(err or "").strip()[:160]}')
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def release_guard_refusals(config, request, facts):
    """Release guard FIRST (fail fast): an rc or final build request is refused unless the config's release guard
    passes on the commit (schema, characters, syntax of rendered scripts, version against the repo, notes format, test
    list, privacy). Config: "release_guard": {"command": [...], "releases": DIR}; release configs DIR/vX.Y.Z.json."""
    guard = config.get('release_guard')
    purpose = str(request.get('purpose') or '')
    if not guard or not (purpose.startswith('rc') or purpose in ('release', 'final')):
        return []
    plain = facts['version'].lstrip('v')
    base = plain.split('-')[0]
    release_cfg = Path(guard['releases']) / ('v%s.json' % base)
    if not release_cfg.is_file():
        return ['release guard: no release config %s for %s' % (release_cfg, facts['version'])]
    cmd = list(guard['command']) + [str(release_cfg), facts['full'], '--repo', request['repo']]
    if '-' not in plain:
        cmd.append('--final')
    out = Path(guard.get('out') or Path(release_cfg).parent / 'guard') / facts['commit']   # RELEASE-GUARD.json per commit
    out.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd + ['--out', str(out)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode == 0:
        print('aw submit: release guard PASS on %s' % facts['commit'])
        return []
    failed = [line for line in r.stdout.splitlines() if line.startswith('FAIL')]
    return ['release guard FAILED (%d): %s' % (len(failed), ' | '.join(failed[:8]) or r.stderr.strip()[:400])]


def submit_build(config, request, dry_run, runner):
    started, t0 = aw.stamp(), time.time()
    notes, refusals = [], []
    options = request.get('options') or {}
    build_settings(config)  # a config without a build section is refused before anything else
    try:
        facts = commit_facts(config, request)
    except Refused as exc:
        return refuse(config, request, [str(exc)])
    if facts['version'] != request['version']:
        refusals.append(f'the request says {request["version"]} but commit {facts["commit"]} has VERSION '
                        f'{facts["version"]}')
    refusals += release_guard_refusals(config, request, facts)
    accept = request['override']['reason'] if allowed(request, 'version-mismatch') else None
    entry_refusals, warnings, entry = aw.entry_findings(config, request['repo'], accept, rev=facts['full'],
                                                        version=facts['version'])
    facts['version_mismatch'] = bool(entry.get('working_version') and entry['working_version'] != facts['version'])
    refusals += entry_refusals
    notes += warnings
    published = published_integration(config)
    checked_head = entry.get('integration_head') or ''
    same = bool(published and checked_head and (published['head'].startswith(checked_head)
                                                 or checked_head.startswith(published['head'])))
    if published and not same:
        contained = aw.is_ancestor(request['repo'], published['head'], facts['full'])
        if contained is False:
            refusals.append(aw.stale_builder_text(request['repo'], facts['commit'], published['head'],
                                                  'published integration head', config.get('integration_ref')))
    import aw_broadcast
    joined = aw_broadcast.join(config, request['repo'], request['requester'])
    if joined:
        notes.append(joined)
    refusals, deferred = aw_broadcast.relax_stale(config, request['requester'], refusals, build=True)
    notes += deferred
    # never deferred: a build without the records layer walks every stair again (BUILD-CHIM-STAIR-WALK-UNCACHED-36)
    refusals += builder_file_refusals(request['repo'], facts['full'], published, config.get('integration_ref'))
    holds = aw_broadcast.hold_refusals(config)
    if holds and allowed(request, 'build-hold'):
        notes += [f'override (build-hold): {request["override"]["reason"]}: {text}' for text in holds]
    else:
        refusals += holds
    flags = options.get('flags') or []
    managed = managed_hits(flags)
    refusals += [f'flag {text}' for text in managed]
    retired = retired_hits(flags)
    recipe = recipe_document(request)
    if recipe is not None:
        if not facts.get('recipes'):
            refusals.append(f'commit {facts["commit"]} has no build recipes (tools/build_recipe.py): merge the '
                            'integration head, or send --flags')
        retired += recipe_retired_hits(recipe)
        relative = [item['role'] for item in recipe['inputs'] if not item['path'].startswith('/')]
        if relative:
            refusals.append('recipe inputs with relative paths (' + ', '.join(relative) + '): a build server '
                            'recipe names its input files by their path in the build volume (/...)')
    reason = request['reason']
    if retired:
        if allowed(request, 'retired-flags'):
            notes.append('override (retired-flags, A/B test of a historical regression): '
                         + request['override']['reason'] + ': ' + '; '.join(retired))
            if REGRESSION_LABEL not in reason:
                reason = f'{REGRESSION_LABEL}-{reason}' if reason else REGRESSION_LABEL
        else:
            refusals += [f'retired flag {text} (only an A/B test of a historical regression may use it: '
                         'override.allow "retired-flags" with a reason)' for text in retired]
    if stair_walk_full(flags):
        if allowed(request, 'stair-walk-full'):
            notes.append('override (stair-walk-full, regression/beta test: every map and frame walked again): '
                         + request['override']['reason'])
            if STAIR_WALK_FULL_LABEL not in reason:
                reason = f'{STAIR_WALK_FULL_LABEL}-{reason}' if reason else STAIR_WALK_FULL_LABEL
        else:
            refusals.append('--stair-walk-cache full walks every map and frame again: a regression or beta test '
                            'only (override.allow "stair-walk-full" with a reason; the run name says so); everyday '
                            'builds reuse the checked stair walks')
    taken = set() if refusals else existing_runs(config, request, runner, notes)
    lease = aw.lease_run_name(config, request['repo'], request['purpose'], request['requester'], reason,
                              version=facts['version'], commit=facts['commit'], taken=taken,
                              record=not (dry_run or refusals))
    run_name = lease['key']
    if refusals:
        free(config, lease, request['requester'])
        return refuse(config, request, refusals, run_name=run_name, version=facts['version'], commit=facts['commit'],
                      leases=[lease['id']])
    cores_info = None
    if not dry_run:
        try:
            request, cores_info, cores_lease = take_cores(config, request, run_name, runner, notes)
        except aw.AwError as exc:
            free(config, lease, request['requester'])
            return refuse(config, request, [f'core lease: {exc}'], run_name=run_name, version=facts['version'],
                          commit=facts['commit'], leases=[lease['id']])
        if cores_lease:
            lease['_cores'] = {'lease': cores_lease, 'runner': runner}
        options = request.get('options') or {}
    commands = build_commands(config, request, facts, run_name)
    shown = [show(commands['source'][0]) + ' | ' + show(commands['source'][1])]
    shown += [show(commands[key]) for key in ('inputs', 'check', 'build', 'summary', 'perf-guard', 'stair-records',
                                              'ingest')
              if commands.get(key)]
    print(f'aw submit: {run_name}: build of {facts["commit"]} ({facts["version"]}) for {request["requester"]}',
          flush=True)
    steps = {'checks': {'exit': 0, 'ok': True, 'detail': 'version, integration head, flags'}}
    logs_dir = aw.state_dir(config) / 'logs'
    logs_dir.mkdir(exist_ok=True)
    reuse_info = source_diff(request, facts, notes) if options.get('reuse_from') else {'applicable': False}
    inputs = [dict(item) for item in options.get('inputs') or []]
    if dry_run:
        for line in shown:
            print('aw submit: would run: ' + line)
        notes.append('dry run: nothing ran (no source export, no input hashes, no developer-mode check, no build)')
        free(config, lease, request['requester'])
        document = result_document(request, run_name, 'passed', started, t0, version=facts['version'],
                                   commit=facts['commit'], steps=steps, notes=notes, dry_run=True, commands=shown,
                                   reuse=reuse_info, leases=[lease['id']], inputs=inputs)
        path = write_result(config, document)
        print(f'aw submit: result {path}')
        return aw.EXIT['passed'], path

    def stop(problems):
        free(config, lease, request['requester'])
        return refuse(config, request, problems, run_name=run_name, version=facts['version'], commit=facts['commit'],
                      leases=[lease['id']], steps=steps, reuse=reuse_info, commands=shown, inputs=inputs)

    # 1. the source of THAT commit, exported into the build volume (never a working tree)
    code, out, err = runner.pipe(*commands['source'])
    seen = (out.strip().splitlines() or [''])[-1].strip()
    ok = code == 0 and 'v' + seen.lstrip('v') == facts['version']
    steps['stage-source'] = {'exit': code, 'ok': ok, 'detail': f'{commands["source_dir"]}: VERSION {seen or "?"}'}
    if not ok:
        return stop([f'source export failed (exit {code}, VERSION {seen or "?"}): '
                     f'{(err.strip().splitlines() or [""])[-1][:200]}'])
    # 1b. the recipe file, byte for byte, into the build volume (its SHA-256 checked there)
    if commands.get('recipe'):
        data = options['recipe']['text'].encode('utf-8')
        code, out, err = runner.feed(commands['recipe'], data)
        line = (out.strip().splitlines() or [''])[-1].split()
        ok = code == 0 and bool(line) and line[0] == options['recipe']['sha256']
        steps['stage-recipe'] = {'exit': code, 'ok': ok, 'detail': f'{commands["recipe_path"]}: '
                                 + (line[0][:12] + '...' if line else '?')}
        if not ok:
            return stop([f'recipe staging failed (exit {code}): {(err.strip().splitlines() or [""])[-1][:200]}'])
    # 2. declared input files: exactly the bytes the request names
    step, inputs, problems = verify_inputs(request, commands, runner)
    if step:
        steps['inputs'] = step
    if problems:
        return stop(problems)
    # 3. the builder's own developer-mode check + reuse preflight (seconds) before the build (hours)
    steps['check'], problems = preflight_check(request, commands, runner, notes, reuse_info)
    if problems:
        return stop(problems)
    # 4. the build
    log_path = logs_dir / f'{run_name}.console.log'
    build_started = aw.stamp()
    build_t0 = time.time()
    code = runner.logged(commands['build'], log_path)
    timings = {'build_s': round(time.time() - build_t0, 1)}
    steps['build'] = {'exit': code, 'ok': code == 0, 'detail': f'build.py exit {code}'}
    # 5. what the run says about itself
    summary = {}
    s_code, s_out, _ = runner.capture(commands['summary'], timeout=300)
    try:
        summary = json.loads((s_out.strip().splitlines() or ['{}'])[-1])
    except ValueError:
        summary = {}
    steps['summary'] = {'exit': s_code, 'ok': bool(summary.get('found')),
                        'detail': f'build-state status {summary.get("status")}'}
    if code == PERF_GUARD_EXIT and summary.get('found') and summary.get('status') == 'passed':
        # every stage passed and its outputs are valid; the perf guard step below fails the result
        steps['build']['ok'] = True
        steps['build']['detail'] += ' (stages passed; the perf guard failed the build)'
    if code == SIZE_GUARD_EXIT and summary.get('found') and summary.get('status') == 'passed':
        # every stage passed and its outputs are valid; a payload folder grew past the margin without a named
        # reason (tools/size_ledger.py, size-ledger.json in the run): the size guard fails the result
        steps['build']['ok'] = True
        steps['build']['detail'] += ' (stages passed; the size guard failed the build)'
        steps['size-guard'] = {'exit': code, 'ok': False,
                               'detail': 'size guard FAILED: a payload folder grew past the margin without '
                                         '--size-growth-reason (size-ledger.json in the run)'}
    if code in (0, PERF_GUARD_EXIT, SIZE_GUARD_EXIT) and summary.get('found') and summary.get('status') != 'passed':
        steps['build']['ok'] = False
        steps['build']['detail'] += f', but build-state says {summary.get("status")}'
    guard = None
    if steps['build']['ok'] and commands.get('perf-guard'):
        guard, steps['perf-guard'] = perf_guard_result(runner, commands['perf-guard'], code)
    numbers = {'stages': summary.get('stages'), 'reused_stages': summary.get('reused'),
               'rebuilt_stages': summary.get('rebuilt'), 'not_started': summary.get('not_started')}
    result = 'passed' if steps['build']['ok'] else 'failed'   # the build's outputs (stair records follow them)
    stair = None
    if result == 'passed' and commands.get('stair-records'):
        # master-checked stair walks: only a passed build's records are ever reused (BUILD-CHIM-STAIR-WALK-UNCACHED-36)
        r_code, r_out, r_err = runner.capture(commands['stair-records'], timeout=900)
        try:
            stair = json.loads((r_out.strip().splitlines() or ['{}'])[-1])
        except ValueError:
            stair = None
        if not isinstance(stair, dict):
            stair = None
        steps['stair-records'] = {'exit': r_code, 'ok': r_code == 0,
                                  'detail': '%s marked, %s already, %s changed; %s reused, %s walked' % tuple(
                                      stair.get(k) for k in ('marked', 'already', 'changed', 'reused', 'walked'))
                                  if stair else ((r_err or r_out).strip().splitlines() or [''])[-1][:200]}
    # 6. trial line + perf ingest, whatever the outcome
    trial = {'time': aw.stamp(), 'run': commands['run_dir'], 'run_name': run_name,
             'version': facts['version'].lstrip('v'), 'commit': facts['commit'], 'started': build_started,
             'finished': aw.stamp(), 'result': result, 'failed_stage': summary.get('failed_stage'),
             'reuse_from': options.get('reuse_from'), 'requester': request['requester'], 'reason': request['reason'],
             'request_id': request['id'], 'inputs': inputs, 'via': 'aw submit'}
    trials = append_trial(config, trial)
    steps['trial-log'] = {'exit': 0, 'ok': True, 'detail': str(trials or 'no build.trials_log configured')}
    if commands['ingest']:
        i_code, i_out, i_err = runner.capture(commands['ingest'], timeout=600)
        steps['perf-ingest'] = {'exit': i_code, 'ok': i_code == 0,
                                'detail': ((i_out or i_err).strip().splitlines() or [''])[-1][:200]}
    reuse_info.update(reused=summary.get('reused'), rebuilt=summary.get('rebuilt'))
    requested = options.get('recipe') or request.get('_preset_recipe')
    recipe_info = {'requested': ({'name': requested.get('name'), 'sha256': requested['sha256'],
                                  'file': requested.get('file')} if requested else None),
                   'saved': summary.get('recipe') if result == 'passed' else None}
    return finish_build(config, request, run_name, lease, started, t0, facts, steps, notes, shown, reuse_info, [],
                        numbers=numbers, timings=timings,
                        failed_stage=summary.get('failed_stage') or (
                            'perf-guard' if steps.get('perf-guard', {}).get('ok') is False else
                            'size-guard' if steps.get('size-guard', {}).get('ok') is False else None),
                        logs=[str(log_path)], artifacts=[commands['run_dir']], inputs=inputs, recipe=recipe_info,
                        **({'stair_walk': stair} if stair else {}), **({'perf_guard': guard} if guard else {}),
                        **({'over_budget': summary['over_budget']} if summary.get('over_budget') else {}),
                        **({'cores': cores_info} if cores_info else {}))


PERF_GUARD_EXIT = 3   # tools/build.py: every stage passed, the perf guard failed the build result
SIZE_GUARD_EXIT = 4   # tools/build.py: every stage passed, the size guard failed the build result


def perf_guard_result(runner, command, build_code):
    """(summary, step) of the perf guard: the verdict build.py wrote (tools/perf_guard.py show --json). A failed
    or unreadable verdict fails the build result; a builder older than the guard has no tools/perf_guard.py and
    passes with that said."""
    code, out, err = runner.capture(command, timeout=300)
    try:
        summary = json.loads((out.strip().splitlines() or ['{}'])[-1])
    except ValueError:
        summary = None
    text = (err or out or '').strip()
    if not isinstance(summary, dict) or 'verdict' not in summary:
        if "perf_guard.py" in text and ('No such file' in text or "can't open file" in text):
            return None, {'exit': code, 'ok': True, 'detail': 'this builder has no perf guard (tools/perf_guard.py)'}
        return None, {'exit': code, 'ok': False, 'detail': 'perf guard verdict unreadable: '
                      + (text.splitlines() or [''])[-1][:200]}
    verdict = summary.get('verdict')
    ok = verdict == 'passed' and build_code != PERF_GUARD_EXIT
    detail = 'perf guard %s: %s failing, %s waived (%s), %s busy-host' % (
        verdict, summary.get('failed', '?'), summary.get('waived', '?'), ', '.join(summary.get('waivers') or []) or '-',
        summary.get('busy', '?'))
    if summary.get('failing'):
        detail += '; ' + ' | '.join(summary['failing'][:3])
    if verdict == 'missing':
        ok, detail = False, 'the build wrote no perf guard verdict (perf-guard.json missing)'
    return summary, {'exit': code, 'ok': ok, 'detail': detail[:600]}


def finish_build(config, request, run_name, lease, started, t0, facts, steps, notes, shown, reuse_info, problems,
                 **fields):
    free(config, lease, request['requester'])
    # bookkeeping after the build never fails it: a failed perf ingest or record marking shows in its step (the
    # records then stay candidates and the next build walks those stairs again)
    status = 'passed' if all(step['ok'] for name, step in steps.items()
                             if name not in ('perf-ingest', 'stair-records')) else 'failed'
    recipe = fields.pop('recipe', None) or {}
    # 'saved' is internal: never in the result document (a failed build's recipe has it too)
    saved = recipe.pop('saved', None)
    saved = saved if status == 'passed' else None
    recipe_path = aw.state_dir(config) / 'results' / f'{run_name}.recipe.json'
    if saved:
        recipe['path'] = str(recipe_path)
    elif status == 'passed' and facts.get('recipes'):
        notes = notes + ['the build saved no recipe (build-recipe.json missing in the run folder)']
    document = result_document(request, run_name, status, started, t0, version=facts['version'],
                               commit=facts['commit'], steps=steps, notes=notes + problems, commands=shown,
                               reuse=reuse_info, leases=[lease['id']], dry_run=False,
                               recipe=recipe if (recipe.get('requested') or recipe.get('path')) else None, **fields)
    path = write_result(config, document)
    if saved:
        verify_recipe(saved, facts, run_name, path, recipe_path)
    print(f'aw submit: {run_name}: {status.upper()}'
          + (f' (failed stage {fields.get("failed_stage")})' if fields.get('failed_stage') else '')
          + aw.over_budget_text(fields.get('over_budget')))
    print(f'aw submit: result {path}')
    return aw.EXIT[status], path


def verify_recipe(saved, facts, run_name, result_path, recipe_path):
    """The recipe a passed build saved, checked in: checked_with = this build (run, host time, the SHA-256 of its
    result record), written next to the result. Never fails the request: a problem is printed."""
    try:
        result_sha = build_recipe.file_sha256(result_path)
        written = saved.get('written_with') or {}
        document = build_recipe.mark_checked(saved, facts['version'].lstrip('v'), written.get('chim_version'),
                                             facts['commit'], run_name, result_sha)
        digest = build_recipe.write(recipe_path, document)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'aw submit: {run_name}: recipe not checked in: {exc}')
        return None
    print(f'aw submit: recipe {recipe_path} (verified, SHA-256 {digest})')
    return recipe_path


# --------------------------------------------------------------------------
# Command line

def parse_input(text):
    path, _, rest = text.partition('=')
    sha, _, role = rest.partition('=')
    item = {'path': path, 'sha256': sha.lower()}
    if role:
        item['role'] = role
    return item


def read_recipe(path):
    """options.recipe of a request: the recipe file's text (byte for byte), its SHA-256, name and host path."""
    import hashlib
    try:
        raw = Path(path).read_bytes()
        text = raw.decode('utf-8')
        document = json.loads(text)
    except (OSError, ValueError) as exc:
        raise Refused(f'cannot read the recipe {path}: {exc}')
    errors = build_recipe.document_errors(document)
    if errors:
        raise Refused(f'recipe {path}: ' + '; '.join(errors[:6]))
    return {'name': document['name'], 'sha256': hashlib.sha256(raw).hexdigest(), 'file': str(Path(path).resolve()),
            'text': text}


def make_request(args, repo_version=None):
    repo = str(Path(args.repo).resolve())
    commit = args.commit or aw.git_short(repo) or 'nogit'
    version = args.version or repo_version
    if not version:
        text = aw.git(repo, 'show', f'{commit}:VERSION')
        version = 'v' + text.strip().lstrip('v') if text else aw.repo_version(repo)
    options = {}
    if args.kind == 'build':
        if args.flags:
            options['flags'] = shlex.split(args.flags)
        for key in ('reuse_from', 'reuse_from_commit', 'workspace', 'cpus', 'memory', 'jobs', 'priority'):
            if getattr(args, key) is not None:
                options[key] = getattr(args, key)
        if args.input:
            options['inputs'] = [parse_input(text) for text in args.input]
        if args.recipe:
            options['recipe'] = read_recipe(args.recipe)
            declared = {item['path'] for item in options.get('inputs') or []}
            for item in json.loads(options['recipe']['text'])['inputs']:
                if item['path'].startswith('/') and item['path'] not in declared:
                    options.setdefault('inputs', []).append(
                        {'path': item['path'], 'sha256': item['sha256'], 'role': item['role']})
        if args.dry_run:
            options['dry_run'] = True
    elif args.kind == 'miniwind':
        if args.flags:
            options['flags'] = shlex.split(args.flags)
        for key in ('preset', 'description', 'reuse_from', 'reuse_from_commit', 'workspace', 'cpus', 'memory', 'jobs',
                    'priority'):
            if getattr(args, key, None) is not None:
                options[key] = getattr(args, key)
        if args.input:
            options['inputs'] = [parse_input(text) for text in args.input]
        if args.dry_run:
            options['dry_run'] = True
    elif args.kind == 'gate':
        for key in ('range', 'number'):
            if getattr(args, key) is not None:
                options[key] = getattr(args, key)
    elif args.flags:
        options['flags'] = shlex.split(args.flags)
    now = datetime.datetime.now().astimezone()
    request = {'schema': 'aw-request-1', 'id': f'req-{now:%Y%m%d-%H%M%S}-{os.getpid()}-{args.kind}',
               'kind': args.kind, 'repo': repo, 'commit': commit, 'purpose': args.purpose, 'version': version,
               'reason': args.reason, 'requester': aw.requester_of(args), 'time': aw.stamp(now), 'options': options}
    if args.override:
        request['override'] = {'reason': args.override, 'allow': args.allow or []}
    return request


def add_parsers(sub):
    submit_p = sub.add_parser('submit', help='hand the build server one request (aw-request-1 JSON file)')
    submit_p.add_argument('request', help='the request file')
    submit_p.add_argument('--dry-run', action='store_true', help='check the request and print every command only')
    submit_p.add_argument('--quiet', action='store_true')
    request_p = sub.add_parser('request', help='write one request from options and submit it')
    request_p.add_argument('--kind', required=True, choices=aw.KINDS)
    request_p.add_argument('--repo', required=True)
    request_p.add_argument('--commit')
    request_p.add_argument('--purpose', required=True)
    request_p.add_argument('--reason', default='')
    request_p.add_argument('--version', help='default: VERSION of the commit')
    request_p.add_argument('--requester')
    request_p.add_argument('--flags', help='build flags as one quoted string, e.g. "--no-npc-gallery --extra-town X"; '
                                          'with --recipe they win over the recipe (each difference recorded)')
    request_p.add_argument('--recipe', metavar='FILE',
                           help='a build recipe (docs/BUILD_RECIPES.md) instead of or next to --flags; its input files '
                                'are declared inputs')
    request_p.add_argument('--reuse-from', dest='reuse_from')
    request_p.add_argument('--reuse-from-commit', dest='reuse_from_commit')
    request_p.add_argument('--input', action='append', metavar='PATH=SHA256[=ROLE]',
                           help='an input file in the build volume the flags name, with its sha256 (repeatable)')
    request_p.add_argument('--workspace')
    request_p.add_argument('--cpus', type=int)
    request_p.add_argument('--memory')
    request_p.add_argument('--jobs', type=int)
    request_p.add_argument('--priority', choices=('release', 'dev', 'optional'),
                           help='core lease priority (docs/AW.md "Core leases"); default release for release/rcN '
                                'purposes, else dev')
    request_p.add_argument('--preset', help='kind miniwind: the test spot (config/miniwind-presets.json)')
    request_p.add_argument('--description', help='kind miniwind: the Scene: line of the startup screen '
                           '(default: the description of the preset)')
    request_p.add_argument('--range')
    request_p.add_argument('--number', type=int)
    request_p.add_argument('--override', metavar='REASON', help='lift the refusals named by --allow, with a reason')
    request_p.add_argument('--allow', action='append', choices=OVERRIDES)
    request_p.add_argument('--write-only', action='store_true', help='write the request file, do not submit')
    request_p.add_argument('--dry-run', action='store_true')
    request_p.add_argument('--quiet', action='store_true')


def main(args, config):
    try:
        if args.command == 'request':
            request = make_request(args)
            if args.write_only:
                errors = request_errors(request)
                if errors:
                    raise Refused('malformed request: ' + '; '.join(errors[:8]))
                print(f'aw request: {save_request(config, request)}')
                return 0
        else:
            try:
                request = json.loads(Path(args.request).read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                raise Refused(f'cannot read the request {args.request}: {exc}')
        code, _ = submit(config, request, dry_run=args.dry_run, quiet=args.quiet)
        return code
    except Refused as exc:
        print(f'aw {args.command}: REFUSED: {exc}', file=sys.stderr)
        return aw.EXIT['refused']
