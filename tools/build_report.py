#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""One plain-text build report with everything needed to find why a build failed (BUILD-FAILURE-REPORT-66).

When a build fails, the builder writes logs/BUILD-REPORT-<run>.txt in the build workspace, beside the build/ and
cache/ folders, and prints where it is; with --report it writes one when the build passes or is cancelled too, and
when a --check or --plan stops on an error (without --report those create no files). The one file holds:

1. What failed: the stage, its exit and time, the unit or map its error names, its last progress line and the units it
   refused, the stage's command, the error lines, the traceback and the last 200 lines of the stage's own log; or the
   builder's own error when it stopped outside its stages.
2. The build settings: every option with its value and where it came from (the command line, a recipe, set by the
   builder, or the default), every AMIWIND_ setting with where it came from (set before the build started, the
   builder's defaults, set by the builder from the options), and the settings the failed stage reads.
3. The versions: VERSION, CHIM_VERSION, the source commit and the checkout's local changes, Python, its packages and
   every tool against the recorded reference, and whether the build ran in a container.
4. The game data: the data folder, the edition, and each master and archive with its size and SHA-256 and the known
   copy it matches, so two copies of the game are told apart.
5. The machine: the operating system, the cores, the memory, the free space of the workspace and the temp folder.
6. The stage plan: every stage with its state, its time, its workers and the start of its key.
7. The reuse state: the reuse source and mode, the stages reused and from where, the stages not reused and why, the
   reuse preflight and the reuse stops.

Right under the result line, when its marks are there, the failure's kind: OUT OF MEMORY or OUT OF DISK, proven or
likely, with what was found (the memory controller's kill counter, the free space at the start and now) and what to do
(tools/build_failure.py kinds, the same judgement FAILURE.md shows first).

Above the parts, under the result, a short environment summary (BUILD-REPORT-MACHINE-ALL-OS-67): the operating system and
its release, the container line, Python against the recorded reference, the cores, the memory and the free space.
Memory is read on Linux (/proc/meminfo), macOS (sysctl hw.memsize, vm_stat) and Windows (GlobalMemoryStatusEx);
"Not available" only where nothing answers. The container line says what was checked and what each check found, never
"not in a container" from finding nothing: our own mark first (AW_RUNTIME and AW_RUNTIME_IMAGE, set by the builder
image, tools/run_docker.py and the master builder), then the signals container engines leave (/.dockerenv,
/run/.containerenv, the container variable, /proc/1/cgroup, an overlay root in /proc/self/mountinfo). The mark is no
AMIWIND_ name on purpose: every AMIWIND_ setting a stage can read is part of its key (tools/build_cache.py, the CHIM
import's cell key), so a mark there would key a build in the image apart from the same build outside it.

The report stays on this computer: nothing is sent anywhere. It holds no environment value other than the AMIWIND_
settings, the build options, the builder image's mark and the container variable, and no host or user name: a path in
the workspace is written relative to it, one in the source checkout as <source>/..., the home folder as ~. FAILURE.md
in the run folder (tools/build_failure.py) stays the short form the Toolkit Monitor shows; this report is the one file
to send when asking for help.

Writing it never raises into the build: a part that cannot be read says so in its place. The builder calls note_start
first thing and write at its end (tools/build.py); no stage imports this module.
"""
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_LINE = 'AmiWind build report, format 1'
FOLDER = 'logs'                   # in the build workspace
PREFIX, SUFFIX = 'BUILD-REPORT-', '.txt'
TAIL_LINES = 200                  # the last lines of the failed stage's own log
MAX_STATE_BYTES = 64 << 20        # build-state.json, profile/fingerprints.json: larger files are not read
MAX_VALUE = 600                   # characters of one value shown (a reason, an option value)
ENV_PREFIX = 'AMIWIND_'
GIT_SECONDS = 20                  # the checkout's local changes: git status, at most this long
# Modes that build nothing: a failure there writes no report unless --report asks for one (a check creates no files)
PREVIEW_MODES = ('check', 'plan', 'host_plan', 'versions', 'check_inputs', 'install_dependencies', 'install_sdk',
                 'estimate_world', 'layout_selftest', 'resource_plan')
# The NPC bake settings every release is built with: the builder's defaults (tools/build.py SHIPPED_BAKE_DEFAULTS)
SHIPPED_SETTINGS = ('AMIWIND_MESH_SEAM_STOP', 'AMIWIND_NPC_BODY_CHECK', 'AMIWIND_NPC_BAKE_FALLBACK')
# What the builder gives each stage beside its own environment (tools/build_parallel.py, tools/build_scratch.py)
PER_STAGE = ('AMIWIND_BUILD_JOBS: the stage\'s worker count; AMIWIND_SCRATCH: the run\'s scratch folder unless set; '
             'AMIWIND_BUILD_JOBS_FILE and AMIWIND_BUILD_BUDGET: a pooled stage\'s live share and the build\'s budget')
# Our own container mark: which of our routes started the build in our builder image, and the image's tag
# (tools/build_docker.py DOCKERFILE, tools/run_docker.py, tools/aw_service.py). Not AMIWIND_ names: see the docstring.
RUNTIME_ENV, RUNTIME_IMAGE_ENV = 'AW_RUNTIME', 'AW_RUNTIME_IMAGE'
RUNTIMES = {'docker-builder': 'our builder image%s',
            'master-builder': 'our builder image%s, started by the master builder'}
CGROUP_WORDS = ('docker', 'kubepods', 'containerd', 'libpod', 'lxc')
CONTAINER_CHECKS = ('our builder image mark (%s)' % RUNTIME_ENV, '/.dockerenv', '/run/.containerenv',
                    'the container variable', '/proc/1/cgroup (it names nothing under cgroup v2)',
                    'an overlay root in /proc/self/mountinfo')
OVERLAY_TYPES = ('overlay', 'fuse-overlayfs')
MEMORY_SECONDS = 5                # sysctl and vm_stat on macOS: at most this long each

_START = {'environment': None}


def note_start(environ=None):
    """The AMIWIND_ settings of the environment the builder started in, before it sets any (tools/build.py _main), and
    the memory controller's kill counter and the free space a failure's kind is judged against (tools/build_failure.py)."""
    environ = os.environ if environ is None else environ
    _START['environment'] = {key: value for key, value in environ.items() if key.startswith(ENV_PREFIX)}
    try:
        import build_failure
        build_failure.note_start()
    except Exception:  # noqa: BLE001 - the start notes never stop the build
        pass
    return dict(_START['environment'])


def note_workspace(workspace):
    """The workspace's free space at the build's start, once the options name it (tools/build.py)."""
    try:
        import build_failure
        build_failure.note_workspace(workspace)
    except Exception:  # noqa: BLE001
        pass


def wanted(args, status):
    """Write a report for this run? Always with --report; otherwise for a failed build, never for a mode that builds
    nothing (--check, --plan and the setup and inventory modes create no files)."""
    if getattr(args, 'report', False):
        return True
    if status != 'failed':
        return False
    return not any(getattr(args, mode, None) for mode in PREVIEW_MODES)


def report_path(workspace, run):
    return Path(workspace) / FOLDER / (PREFIX + run + SUFFIX)


def fallback_name(version, now=None):
    """The report's name for a build that stopped before it chose its run name."""
    return '%s_v%s_before-the-run-name' % ((now or datetime.now()).strftime('%Y_%m_%d_%H%M%S'), version or 'unknown')


def _stamp(now=None):
    now = now or datetime.now(timezone.utc)
    return now.astimezone().strftime('%Y-%m-%d %H:%M:%S %z') + ' / ' + now.strftime('%Y-%m-%d %H:%M:%S UTC')


class Paths:
    """Shortens the paths in a text: the workspace to a relative path, the source checkout to <source>, the home
    folder to ~ (longest first, so a workspace inside the checkout or the home folder is relative to itself)."""

    def __init__(self, workspace=None, root=ROOT, home=None):
        if home is None:
            try:
                home = Path.home()
            except (RuntimeError, KeyError, OSError):
                home = None
        pairs = {}
        # the checkout's parent first: the home folder wins where they are the same folder
        parent = Path(root).parent if root else None
        for base, short in ((parent, '<source>/..'), (home, '~'), (root, '<source>'), (workspace, '')):
            if not base:
                continue
            # absolute forms only: a relative one ("out") would match any word
            base = Path(base).expanduser()
            forms = {str(base)} if base.is_absolute() else set()
            try:
                forms.add(str(base.resolve()))
            except (OSError, RuntimeError):
                pass
            for form in forms:
                form = form.rstrip('/\\')
                if len(form) > 1 and form not in ('/', '\\') and not (len(form) <= 3 and form[1:2] == ':'):
                    pairs[form] = short
        self.pairs = sorted(pairs.items(), key=lambda item: -len(item[0]))

    def text(self, value):
        text = str(value)
        for prefix, short in self.pairs:
            if prefix in text:
                text = self._swap(text, prefix, short)
        return text

    @staticmethod
    def _swap(text, prefix, short):
        out, at = [], 0
        while True:
            found = text.find(prefix, at)
            if found < 0:
                out.append(text[at:])
                return ''.join(out)
            end = found + len(prefix)
            before, after = text[found - 1:found] if found else '', text[end:end + 1]
            if before and (before.isalnum() or before in '._-/\\~'):     # inside a longer path: kept
                out.append(text[at:end])
            elif after in ('/', '\\'):
                out.append(text[at:found] + (short + after if short else ''))
                end += 1
            elif not after or not (after.isalnum() or after in '._-'):
                out.append(text[at:found] + (short or '.'))
            else:                                                        # a longer name that starts the same
                out.append(text[at:end])
            at = end


def _seconds(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return '-'
    value = int(round(value))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    return ('%d h %02d min' % (hours, minutes)) if hours else ('%d min %02d s' % (minutes, seconds)) if minutes else \
        '%d s' % seconds


def _size(value):
    if not isinstance(value, int) or isinstance(value, bool):
        return 'size not known'
    for unit, scale in (('GiB', 1 << 30), ('MiB', 1 << 20), ('KiB', 1 << 10)):
        if value >= scale:
            return '%.1f %s' % (value / scale, unit)
    return '%d bytes' % value


def _short(text, limit=MAX_VALUE):
    text = str(text)
    return text if len(text) <= limit else text[:limit] + ' ... (%d characters)' % len(text)


def _load_json(path):
    try:
        path = Path(path)
        if not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
            return {}
        doc = json.loads(path.read_bytes().decode('utf-8'))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _jsonable(value):
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _shown(value):
    value = _jsonable(value)
    if value is None:
        return '(not set)'
    if isinstance(value, bool):
        return 'on' if value else 'off'
    if isinstance(value, str):
        return value if value else '""'
    return json.dumps(value, sort_keys=True)


class Context:
    """Everything the report reads, gathered once (each part reads what it needs, never raising)."""

    def __init__(self, args, status, error, metadata, steps, factory, root, version, result, code):
        self.args, self.status, self.error, self.code = args, status, error, code
        self.root = Path(root or ROOT)
        self.version = version
        self.factory = factory
        self.result = result
        self.workspace = Path(getattr(args, 'workspace', None) or (self.root / 'out'))
        self.name = getattr(args, 'name', None) or None
        self.run = self.workspace / 'build' / self.name if self.name else None
        self.metadata = metadata if isinstance(metadata, dict) else {}
        self.state = _load_json(self.run / 'build-state.json') if self.run else {}
        # the run folder's state is this build's only when it carries this build's start (a build refused because a
        # run of that name exists already must not report the earlier run's stages as its own)
        self.foreign = bool(self.state) and (metadata is None or self.state.get('build_started_at')
                                             != self.metadata.get('build_started_at'))
        if self.foreign:
            self.state = {}
        self.steps = [(str(name), [str(part) for part in command]) for name, command in steps or ()]
        self.paths = Paths(self.workspace, self.root)
        self.stage_cache = self.metadata.get('stage_cache') or self.state.get('stage_cache') or {}
        self._scans, self._kinds = {}, None

    def path(self, value):
        return self.paths.text(value)

    def scan(self, step):
        """(the stage log, what it says or None) of a failed stage, read once (tools/build_failure.py scan_log)."""
        import build_failure
        name = str(step.get('name') or '?')
        if name not in self._scans:
            log_name = Path(str(step.get('log') or '')).name
            log = self.run / 'logs' / log_name if self.run is not None and log_name else None
            self._scans[name] = (log, build_failure.scan_log(log, tail_lines=TAIL_LINES)
                                 if log is not None and log.is_file() else None)
        return self._scans[name]

    def kinds(self):
        """The failure's kinds (out of memory, out of disk) when their marks are there, judged in the failing build."""
        if self._kinds is None:
            self._kinds = []
            if self.status == 'failed':
                import build_failure
                rows = []
                for step in self.failed_stages():
                    row = dict(self.scan(step)[1] or {})
                    row.update(name=str(step.get('name')), returncode=step.get('returncode'))
                    rows.append(row)
                rec = {'failed_stages': rows}
                if self.error is not None and not rows:
                    rec['builder_error'] = {'type': type(self.error).__name__, 'message': str(self.error)[:4000]}
                self._kinds = build_failure.kinds(rec, self.error, live=True, workspace=self.workspace)
        return self._kinds

    def failed_stages(self):
        return [step for step in self.state.get('steps') or [] if isinstance(step, dict) and step.get('status') == 'failed']

    def plan_names(self):
        if self.steps:
            return [name for name, _ in self.steps]
        names = [str(step.get('name')) for step in self.state.get('steps') or [] if isinstance(step, dict)]
        return names + [str(name) for name in self.state.get('not_started') or [] if str(name) not in names]


def _part(title, build, ctx):
    lines = [title, '-' * len(title)]
    try:
        lines += build(ctx)
    except Exception as exc:  # noqa: BLE001 - one part that cannot be read never hides the others
        lines.append('(this part could not be written: %s: %s)' % (type(exc).__name__, ctx.path(_short(exc, 300))))
    return lines + ['']


def header(ctx):
    result = {'failed': 'FAILED', 'passed': 'passed', 'cancelled': 'cancelled'}.get(ctx.status, ctx.status)
    if ctx.status == 'passed' and ctx.code:
        result += ', exit code %s (a guard after the stages: see the build output)' % ctx.code
    lines = [SCHEMA_LINE, '=' * len(SCHEMA_LINE), '',
             'Run: %s' % (ctx.name or 'not named yet (the build stopped before it chose its run name)'),
             'Result: %s' % result]
    try:                                         # out of memory, out of disk: named right under the result
        import build_failure
        lines += [ctx.path(line) for line in build_failure.kind_lines(ctx.kinds())]
    except Exception as exc:  # noqa: BLE001 - the kind never hides the report
        lines.append('Kind: not judged (%s)' % type(exc).__name__)
    lines.append('Written: %s' % _stamp())
    started = ctx.metadata.get('build_started_at') or ctx.state.get('build_started_at')
    if started:
        lines.append('Build started: %s' % started)
    if ctx.run is not None:
        lines.append('Run folder: %s%s' % (ctx.path(ctx.run), ' (an earlier run of the same name: not this build\'s)'
                                           if ctx.foreign else '' if ctx.run.is_dir() else
                                           ' (not made: the build stopped before its first stage)'))
        if (ctx.run / 'FAILURE.md').is_file() and not ctx.foreign:
            lines.append('Short form: %s (the failure page the Toolkit Monitor shows)' % ctx.path(ctx.run / 'FAILURE.md'))
    if ctx.status == 'failed':
        # what to do now, as the build printed it last (BUILD-OOM-HELP-AND-TIP-68)
        try:
            lines += [''] + [ctx.path(line) for line in tip_lines(ctx)]
        except Exception as exc:  # noqa: BLE001 - the advice never hides the report
            lines.append('What to do now: not written (%s)' % type(exc).__name__)
    lines += [''] + environment(ctx)
    lines += ['',
              'This file stays on this computer: nothing is sent anywhere. Send it when you ask for help with this '
              'build. It holds no environment value other than the AMIWIND_ settings, the build options, the builder '
              'image\'s mark and the container variable. Paths in the build workspace are relative to it, paths in the '
              'source checkout start with <source>, the home folder is ~.', '']
    return lines


def environment(ctx, start=False):
    """The short environment summary under the result (BUILD-REPORT-MACHINE-ALL-OS-67), with the swap and the memory
    peaks (BUILD-OOM-HELP-AND-TIP-68); a line that cannot be read says so in its place. START: the block the build
    prints at its start (start_lines), without the peaks."""
    rows = (('Operating system', system_text), ('Container', container), ('Python', python_text),
            ('Cores', lambda: cores_text(ctx)), ('Memory', memory_text), ('Swap', swap_text)) + (
        () if start else (('Memory peak', lambda: memory_peak_text(ctx)),)) + (
        ('Free space', lambda: '%s in the workspace, %s in the temp folder' % (free_text(ctx.workspace),
                                                                              free_text(temp_folder()))),)
    lines = ['Machine at the start of the build (a failed build\'s report has it again):' if start else
             'Environment (parts 3 and 5 have the details):']
    for title, read in rows:
        try:
            value = read()
        except Exception as exc:  # noqa: BLE001 - one line that cannot be read never hides the others
            value = 'not read (%s)' % type(exc).__name__
        lines.append('  %s: %s' % (title, ctx.path(value)))
    return lines


def what_failed(ctx):
    import build_failure
    lines = []
    failed = ctx.failed_stages()
    if ctx.status == 'passed':
        lines.append('Nothing failed: the build passed.')
        if ctx.result is not None:
            result = Path(ctx.result)
            size = result.stat().st_size if result.is_file() else None
            lines.append('Output: %s (%s)' % (ctx.path(result), _size(size) if size is not None else 'a folder'))
        return lines
    if ctx.status == 'cancelled':
        lines.append('The build was cancelled (Ctrl+C or a stop signal); no stage failed by itself.')
    plan = ctx.plan_names()
    commands = dict(ctx.steps)
    reused = ctx.stage_cache.get('reused') or {}
    for step in failed:
        name = str(step.get('name') or '?')
        number = plan.index(name) + 1 if name in plan else None
        lines.append('Stage: %s (stage %s of %d, exit %s, after %s, %s worker%s)' % (
            name, number or '?', len(plan), step.get('returncode', 'not recorded'), _seconds(step.get('elapsed_seconds')),
            step.get('jobs', '?'), '' if step.get('jobs') == 1 else 's'))
        log, scan = ctx.scan(step)
        if scan is None:
            lines.append('Error: the stage log %s was not found' % (ctx.path(log) if log else '(none recorded)'))
        else:
            said = build_failure.headline(scan) or 'the stage ended with exit %s' % step.get('returncode')
            lines.append('Error: %s' % ctx.path(said[len('Error: '):] if said.startswith('Error: ') else said))
        lines.append('Unit or map: as the error line above names it; the stage\'s last progress line and the units it '
                     'refused follow')
        if log is not None and log.is_file():
            try:
                import build_progress
                counter = build_progress.log_counter(log)
            except Exception:  # noqa: BLE001
                counter = None
            if counter:
                lines.append('Last progress line: %s (%s of %s%s)' % (
                    ctx.path(counter.get('name')), counter.get('done'), counter.get('total'),
                    ' ' + str(counter['unit']) if counter.get('unit') else ''))
            else:
                lines.append('Last progress line: none counted in the log')
        command = (reused.get(name) or {}).get('original_command') or commands.get(name) or step.get('command')
        if command:
            lines.append('Stage command: ' + ctx.path(shlex.join([str(part) for part in command])))
        if name in reused:
            lines.append('The stage was a reused one: its files came from %s' % ctx.path(reused[name].get('from')))
        if scan is None:
            continue
        lines.append('Stage log: %s (%s)' % (ctx.path(log), _size(scan.get('size'))))
        if scan.get('left_out_count'):
            lines += ['', 'Units the stage refused or left out: %d' % scan['left_out_count']]
            lines += ['  ' + ctx.path(line) for line in scan['left_out'][:50]]
            if scan['left_out_count'] > 50:
                lines.append('  ... %d more in the stage log' % (scan['left_out_count'] - 50))
        lines += ['', 'Error lines:']
        lines += ['  ' + ctx.path(line) for line in scan.get('error_lines') or []] or ['  (none)']
        lines += ['', 'Traceback:']
        lines += ['  ' + ctx.path(line) for line in scan.get('traceback') or []] or [
            '  (none in the log: the stage reported its error itself, or it is not a Python tool)']
        lines += ['', 'The last %d lines of the stage log:' % len(scan.get('tail') or [])]
        lines += ['  ' + ctx.path(line) for line in scan.get('tail') or []] or ['  (the log is empty)']
        lines.append('')
    others = [str(s.get('name')) for s in ctx.state.get('steps') or []
              if isinstance(s, dict) and s.get('status') in ('cancelled', 'running')]
    if others and ctx.status != 'passed':
        lines.append('Stopped with it: ' + ', '.join(others))
    if ctx.error is not None and not failed and ctx.status == 'failed':
        error = ctx.error
        if isinstance(error, SystemExit):
            text = str(error.code if error.code is not None else '')
            lines += ['The builder stopped outside its stages: ' + ctx.path(text.strip() or 'exit %s' % error.code)]
        else:
            message = str(error).strip()
            lines += ['The builder stopped outside its stages: %s: %s' % (type(error).__name__,
                                                                          ctx.path(message.splitlines()[0] if message
                                                                                   else ''))]
            if len(message.splitlines()) > 1:
                lines += ['  ' + ctx.path(line) for line in message.splitlines()[1:200]]
        trace = traceback.format_exception(type(error), error, error.__traceback__)
        lines += ['', 'The builder\'s traceback:']
        lines += ['  ' + ctx.path(line) for part in trace for line in part.rstrip('\n').splitlines()][-TAIL_LINES:]
    elif not failed and ctx.status == 'failed':
        lines.append('No failed stage is recorded and the builder recorded no error.')
    return lines


def _option_rows(ctx):
    """[(flag, value, source, default)] of every option of the builder, its value now and where it came from."""
    import argparse
    import build_recipe
    args = ctx.args
    argv = [str(part) for part in getattr(args, '_argv', None) or []]
    parser = ctx.factory()
    try:
        given = build_recipe.given(ctx.factory, argv)
    except (Exception, SystemExit):  # noqa: BLE001 - options that do not parse (argparse exits): sources not known
        given = None
    recipe = set()
    record = getattr(args, 'build_recipe_record', None)
    if isinstance(record, dict) and record.get('file'):
        try:
            document, _ = build_recipe.read(record['file'])
            recipe = set(document.get('options') or ())
        except Exception:  # noqa: BLE001
            recipe = set()
    try:
        # each option's value when it is not given (with several options to one value, the one argparse keeps)
        defaults = vars(ctx.factory().parse_args([]))
    except (Exception, SystemExit):  # noqa: BLE001
        defaults = {}
    rows, seen = [], set()
    for action in parser._actions:
        if not action.option_strings or action.dest in ('help', argparse.SUPPRESS) or action.dest in seen:
            continue
        seen.add(action.dest)
        flags = [next((flag for flag in a.option_strings if flag.startswith('--')), a.option_strings[0])
                 for a in parser._actions if a.dest == action.dest and a.option_strings]
        if len(flags) > 3:                  # one value behind many switches (the MiniWind presets): the first ones
            flags = flags[:2] + ['(%d more)' % (len(flags) - 2)]
        default = defaults[action.dest] if action.dest in defaults else parser.get_default(action.dest)
        value = getattr(args, action.dest, default)
        if given is not None and action.dest in given:
            source = 'command line'
        elif action.dest in recipe:
            source = 'recipe'
        elif _jsonable(value) == _jsonable(default):
            source = 'default'
        elif given is None:
            source = 'given or set by the builder'
        else:
            source = 'set by the builder'
        rows.append(('/'.join(flags), value, source, default))
    return rows


def settings(ctx):
    args = ctx.args
    argv = [str(part) for part in getattr(args, '_argv', None) or []]
    lines = ['Command line: tools/build.py ' + ctx.path(shlex.join(argv)), '']
    record = getattr(args, 'build_recipe_record', None)
    if isinstance(record, dict):
        lines.append('Recipe: %s (%s, SHA-256 %s); the command line overrides %d of its options' % (
            record.get('name'), ctx.path(record.get('file')), record.get('sha256'), len(record.get('overrides') or [])))
    else:
        lines.append('Recipe: none')
    rows = _option_rows(ctx)
    changed = [row for row in rows if row[2] != 'default']
    lines += ['', 'Options given or set (%d; the rest are at their defaults, listed after them):' % len(changed)]
    for flag, value, source, default in changed:
        lines.append('  %s = %s   [%s; default %s]' % (flag, ctx.path(_short(_shown(value))), source,
                                                       ctx.path(_short(_shown(default), 120))))
    lines += ['', 'Options at their defaults (%d):' % (len(rows) - len(changed))]
    lines += ['  %s = %s' % (flag, ctx.path(_short(_shown(value)))) for flag, value, source, _ in rows
              if source == 'default']
    lines += ['', 'AMIWIND_ settings (the builder\'s environment when the report was written):']
    start = _START['environment']
    now = {key: value for key, value in os.environ.items() if key.startswith(ENV_PREFIX)}
    if start is None:
        lines.append('  (where each came from is not known: the builder did not note its start)')
        start = {}
    elif 'AMIWIND_ACTIVE_ENV' in start:
        lines.append('  (this build started again inside its own Python environment: the settings the first start '
                     'made show as set before the build)')
    for key in sorted(set(now) | set(start)):
        before, after = start.get(key), now.get(key)
        if after is None:
            where = 'set before the build started, removed by the builder (the option\'s default)'
        elif before is None and key in SHIPPED_SETTINGS:
            where = 'the builder\'s default (a shipped NPC bake setting)'
        elif before is None:
            where = 'set by the builder from the options'
        elif before == after:
            where = 'set before the build started'
        else:
            where = 'set before the build started as %s, changed by the builder' % ctx.path(_short(before, 200))
        lines.append('  %s=%s   [%s]' % (key, ctx.path(_short(after if after is not None else before)), where))
    lines.append('  Each stage also gets ' + PER_STAGE + '.')
    fingerprints = _load_json(ctx.run / 'profile' / 'fingerprints.json') if ctx.run is not None else {}
    for step in ctx.failed_stages():
        name = str(step.get('name'))
        environment = (fingerprints.get(name) or {}).get('environment') if isinstance(fingerprints.get(name), dict) \
            else None
        lines += ['', 'Settings the failed stage %s reads (its key, profile/fingerprints.json):' % name]
        if isinstance(environment, dict) and environment:
            lines += ['  %s=%s' % (key, ctx.path(_short(value)) if value is not None else '(not set)')
                      for key, value in sorted(environment.items())]
        else:
            lines.append('  (not recorded)')
    return lines


def _git_changes(root):
    """'none', 'N changed, M untracked' or why it was not checked (git status, read only, no lock taken)."""
    if not (Path(root) / '.git').exists():
        return 'not a git checkout'
    git = shutil.which('git')
    if not git:
        return 'not checked (no git program)'
    try:
        done = subprocess.run([git, '--no-optional-locks', '-C', str(root), 'status', '--porcelain'],
                              capture_output=True, text=True, errors='replace', timeout=GIT_SECONDS,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        return 'not checked (%s)' % type(exc).__name__
    if done.returncode != 0:
        return 'not checked (git status ended with exit %d)' % done.returncode
    rows = [row for row in done.stdout.splitlines() if row.strip()]
    if not rows:
        return 'none'
    untracked = sum(row.startswith('??') for row in rows)
    return '%d changed, %d untracked files' % (len(rows) - untracked, untracked)


def _read(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def _overlay_root(mountinfo):
    """Whether the root folder is an overlay mount (the last mount on / in /proc/self/mountinfo)."""
    kind = None
    for row in (mountinfo or '').splitlines():
        left, separator, right = row.partition(' - ')
        fields = left.split()
        if separator and len(fields) >= 5 and fields[4] == '/':
            kind = (right.split() or [''])[0]
    return kind in OVERLAY_TYPES


def container(environ=None, exists=None, read=None):
    """Whether the build ran in a container, as what was checked and what each check found: our own mark first (the
    route and the image tag), then the signals container engines leave. Finding none is no proof of none, so the line
    then lists the checks, never "not in a container". EXISTS(path) and READ(path) stand in for the files in tests."""
    environ = os.environ if environ is None else environ
    exists = exists or (lambda path: Path(path).exists())
    read = read or _read
    signals = []
    if exists('/.dockerenv'):
        signals.append('/.dockerenv (Docker)')
    if exists('/run/.containerenv'):
        signals.append('/run/.containerenv (Podman)')
    kind = str(environ.get('container') or '').strip()
    if kind:
        signals.append('container=%s (the container variable)' % _short(kind, 60))
    groups = read('/proc/1/cgroup') or ''
    words = [word for word in CGROUP_WORDS if word in groups]
    if words:
        signals.append('/proc/1/cgroup names %s' % ', '.join(words))
    if _overlay_root(read('/proc/self/mountinfo')):
        signals.append('an overlay root (/proc/self/mountinfo)')
    runtime = str(environ.get(RUNTIME_ENV) or '').strip()
    image = str(environ.get(RUNTIME_IMAGE_ENV) or '').strip()
    if runtime:
        named = ' ' + _short(image, 160) if image else ''
        what = RUNTIMES.get(runtime)
        text = 'yes (%s)' % (what % named if what else 'marked %s=%s%s' % (RUNTIME_ENV, _short(runtime, 60), named))
        if signals:
            text += '; signals: ' + ', '.join(signals)
    elif signals:
        text = 'yes (signals: %s)' % ', '.join(signals)
    else:
        return 'no container signal found (checked: %s); finding none does not prove there is none' % ', '.join(
            CONTAINER_CHECKS)
    copy = (read('/opt/amiwind/VERSION') or '').strip()
    if copy:
        text += '; the image\'s own builder copy (/opt/amiwind) is v' + _short(copy, 60)
    return text


def versions(ctx):
    import run_name
    lines = ['AmiWind: %s (VERSION)' % (ctx.version or 'not known')]
    try:
        lines.append('CHIM: %s (CHIM_VERSION)' % (ctx.root / 'CHIM_VERSION').read_text(encoding='utf-8').strip())
    except OSError:
        lines.append('CHIM: CHIM_VERSION not found')
    named = getattr(ctx.args, 'run_name_record', None) or ctx.metadata.get('run_name') or {}
    head = run_name.git_head(ctx.root)
    if not head and not named.get('commit'):
        try:            # a build stopped before its run name: the commit as the run name would take it
            commit, origin = run_name.source_commit(ctx.root, getattr(ctx.args, 'source_commit', None))
            named = {'commit': commit, 'commit_from': origin} if commit != 'nogit' else {}
        except ValueError:
            named = {}
    if head:
        lines.append('Source commit: %s (the checkout\'s git files)' % head)
    elif named.get('commit'):
        lines.append('Source commit: %s (%s)' % (named['commit'], named.get('commit_from') or 'recorded'))
    else:
        lines.append('Source commit: not known (not a git checkout and no --source-commit)')
    lines.append('Local changes in the checkout: ' + _git_changes(ctx.root))
    lines.append('Python: %s (%s) at %s' % (platform.python_version(), platform.python_implementation(),
                                            ctx.path(sys.executable)))
    rows = getattr(ctx.args, 'version_report', None) or ctx.metadata.get('version_comparison') or []
    if rows:
        lines.append('Packages and tools against the recorded reference (tools/build-reference.json):')
        for row in rows:
            lines.append('  [%s] %s: %s (reference %s)%s' % (
                row.get('status'), row.get('name'), ctx.path(row.get('detected') or 'not found'), row.get('reference'),
                ('  ' + ctx.path(row['path'])) if row.get('path') else ''))
            if row.get('sha256'):
                lines.append('      SHA-256 %s' % row['sha256'])
    else:
        lines.append('Packages against the recorded reference (the tools were not checked before the build stopped):')
        try:
            import importlib.metadata
            import build_versions
            reference = json.loads(build_versions.REFERENCE.read_text(encoding='utf-8'))
            for package, wanted_version in sorted((reference.get('packages') or {}).items()):
                try:
                    found = importlib.metadata.version(package)
                except importlib.metadata.PackageNotFoundError:
                    found = None
                lines.append('  %s: %s (reference %s)' % (package, found or 'not installed', wanted_version))
        except Exception as exc:  # noqa: BLE001
            lines.append('  (not read: %s)' % type(exc).__name__)
    tools = ctx.metadata.get('tools') or ctx.state.get('tools') or {}
    hashes = ctx.metadata.get('tool_sha256') or {}
    if tools:
        lines.append('Tools the build uses:')
        for name, path in sorted(tools.items()):
            lines.append('  %s: %s%s' % (name, ctx.path(path), ('  SHA-256 ' + hashes[name]) if hashes.get(name) else ''))
    lines.append('Container: ' + container())
    return lines


def _game_records(ctx):
    """(data folder, records, absent, edition) from the build's known-inputs check, else read here."""
    import known_inputs
    report = getattr(ctx.args, 'known_game_data', None)
    data = (getattr(ctx.args, 'input_report', None) or {}).get('data_files') or getattr(ctx.args, 'data_files', None)
    if isinstance(report, dict) and report.get('files') is not None:
        return data, report['files'], report.get('absent') or [], (report.get('edition') or {}), True
    if not data:
        return None, [], [], {}, False
    from mwad.paths import child_ci, resolve_data_files
    folder = resolve_data_files(Path(data))
    table = known_inputs.load_table()
    records, absent = [], []
    for name, kind, required in known_inputs.GAME_FILES:
        path = child_ci(folder, name, required=False)
        if path is None or not path.is_file():
            absent.append(name)
            continue
        import hashlib
        digest = hashlib.sha256()
        with open(path, 'rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                digest.update(block)
        records.append(known_inputs.classify(kind, name, path, digest.hexdigest(), table, required=required))
    return folder, records, absent, {}, False


def game_data(ctx):
    data, records, absent, edition, checked = _game_records(ctx)
    if data is None:
        return ['No data folder was given (--data-files): an asset-free build, or the build stopped before it.']
    lines = ['Data folder: %s' % ctx.path(data)]
    if edition.get('edition'):
        lines.append('Edition: %s%s' % (edition['edition'], ' (the reference copy)' if edition.get('reference') else ''))
        if edition.get('font_sources'):
            lines.append('Font sources: ' + ', '.join('%s %s' % pair for pair in sorted(edition['font_sources'].items())))
        overrides = edition.get('loose_overrides')
        if isinstance(overrides, dict):
            lines.append('Loose files shadowing Morrowind.bsa copies: %s' % overrides.get('total'))
    elif not checked:
        lines.append('Edition: the masters\' known copies are named below (the build stopped before its game data '
                     'check, so the fonts that tell the GOG and Steam editions apart were not checked)')
    for record in records:
        lines.append('  %s%s  %s bytes  SHA-256 %s  %s' % (
            record.get('name'), (' v' + record['version']) if record.get('version') else '',
            '{:,}'.format(record['bytes']) if isinstance(record.get('bytes'), int) else '?',
            record.get('sha256') or 'not hashed', record.get('message') or record.get('verdict')))
    if absent:
        lines.append('Not present: ' + ', '.join(absent))
    layers = getattr(ctx.args, 'expansion_layers', None) or ctx.metadata.get('expansion_layers') or {}
    if layers.get('masters'):
        lines.append('Masters in load order: ' + ', '.join(layers['masters']) +
                     ' (requested: %s)' % layers.get('requested', 'default'))
    lock = getattr(ctx.args, '_input_lock', None)
    if lock is not None:
        try:
            lines.append('Hash check: --check-hashes %s' % lock.summary().get('mode'))
        except Exception:  # noqa: BLE001
            pass
    return lines


def _cgroup(*names):
    for name in names:
        try:
            return Path(name).read_text(encoding='utf-8').strip()
        except OSError:
            continue
    return None


def system_text(system=None):
    """The operating system, its release and the processor type (no machine or user name)."""
    system = system or platform.system() or 'not known'
    text = '%s %s (%s)' % (system, platform.release(), platform.machine())
    if system == 'Linux':
        for row in (_read('/etc/os-release') or '').splitlines():
            if row.startswith('PRETTY_NAME='):
                text += ', ' + row.split('=', 1)[1].strip().strip('"')
        if 'microsoft' in platform.release().lower():
            text += ', under WSL'
    elif system == 'Darwin':
        release = platform.mac_ver()[0]
        if release:
            text += ', macOS ' + release
    elif system == 'Windows':
        text += ', version ' + platform.version()
        edition = platform.win32_edition() if hasattr(platform, 'win32_edition') else None
        if edition:
            text += ' (%s)' % edition
    return text


def python_text():
    """This Python against the version the builder records as its reference (tools/build-reference.json)."""
    found = platform.python_version()
    text = '%s (%s)' % (found, platform.python_implementation())
    try:
        import build_versions
        reference = json.loads(build_versions.REFERENCE.read_text(encoding='utf-8')).get('python')
        verdict = build_versions.compare(found, reference) if reference else None
    except Exception:  # noqa: BLE001 - the summary never stops on its reference
        reference = verdict = None
    return text + (', the recorded reference %s: %s' % (reference, verdict) if reference else
                   ', the recorded reference was not read')


def cores_text(ctx):
    count = os.cpu_count()
    usable = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else count
    text = '%s usable of %s' % (usable, count)
    quota = _cgroup('/sys/fs/cgroup/cpu.max')
    if quota and not quota.startswith('max'):
        try:
            limit, period = quota.split()[:2]
            text += ', container limit %.1f' % (int(limit) / int(period))
        except ValueError:
            pass
    asked = getattr(ctx.args, 'jobs_requested', getattr(ctx.args, 'jobs', None))
    return text + '; build workers %s (--jobs %s)' % (getattr(ctx.args, 'jobs', None) or '?', asked if asked else 'auto')


def memory(system=None, read=None, run=None, kernel32=None):
    """(total, available, how) in bytes of the machine's memory: Linux /proc/meminfo, macOS sysctl hw.memsize and
    vm_stat, Windows GlobalMemoryStatusEx; (None, None, why) where nothing answers. READ, RUN and KERNEL32 stand in for
    the file reader, subprocess.run and the Windows kernel in tests."""
    system = system or platform.system()
    if system == 'Linux':
        found = {}
        for row in ((read or _read)('/proc/meminfo') or '').splitlines():
            key, _, value = row.partition(':')
            if key in ('MemTotal', 'MemAvailable'):
                try:
                    found[key] = int(value.split()[0]) * 1024
                except (ValueError, IndexError):
                    pass
        if found.get('MemTotal'):
            return found['MemTotal'], found.get('MemAvailable'), '/proc/meminfo'
        return None, None, '/proc/meminfo did not answer'
    if system == 'Darwin':
        return _mac_memory(run or subprocess.run)
    if system == 'Windows':
        return _windows_memory(kernel32)
    return None, None, 'no memory reader for %s' % system


def _mac_memory(run):
    def ask(command):
        try:
            done = run(command, capture_output=True, text=True, errors='replace', timeout=MEMORY_SECONDS,
                       stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            return ''
        return done.stdout if done.returncode == 0 else ''
    total = ask(['sysctl', '-n', 'hw.memsize']).strip()
    if not total.isdigit():
        return None, None, 'sysctl hw.memsize did not answer'
    stat = ask(['vm_stat'])
    size = re.search(r'page size of (\d+) bytes', stat)
    pages = [re.search(r'^Pages %s:\s+(\d+)\.?\s*$' % name, stat, re.M) for name in ('free', 'inactive', 'speculative')]
    if size and pages[0]:
        available = sum(int(found.group(1)) for found in pages if found) * int(size.group(1))
        return int(total), available, 'sysctl hw.memsize; vm_stat free, inactive and speculative pages'
    return int(total), None, 'sysctl hw.memsize; vm_stat did not answer'


def _windows_status(kernel32=None):
    """(MEMORYSTATUSEX, None) from GlobalMemoryStatusEx, or (None, why)."""
    import ctypes

    class Status(ctypes.Structure):          # MEMORYSTATUSEX
        _fields_ = [('dwLength', ctypes.c_uint32), ('dwMemoryLoad', ctypes.c_uint32)] + [
            (name, ctypes.c_uint64) for name in ('ullTotalPhys', 'ullAvailPhys', 'ullTotalPageFile', 'ullAvailPageFile',
                                                 'ullTotalVirtual', 'ullAvailVirtual', 'ullAvailExtendedVirtual')]
    status = Status()
    status.dwLength = ctypes.sizeof(Status)
    try:
        kernel32 = kernel32 or ctypes.windll.kernel32
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None, 'GlobalMemoryStatusEx did not answer'
    except (AttributeError, OSError) as exc:
        return None, 'GlobalMemoryStatusEx not reached (%s)' % type(exc).__name__
    return status, None


def _windows_memory(kernel32=None):
    status, why = _windows_status(kernel32)
    if status is None:
        return None, None, why
    return int(status.ullTotalPhys), int(status.ullAvailPhys), 'GlobalMemoryStatusEx'


def memory_text(system=None, **readers):
    system = system or platform.system()
    total, available, how = memory(system, **readers)
    if not total:
        return 'Not available (%s)' % how
    text = '%s total, %s' % (_size(total), '%s available' % _size(available) if available is not None else
                             'available not read')
    if system == 'Linux':
        limit = _cgroup('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes')
        if limit and limit.isdigit() and int(limit) < total:
            text += ', container limit %s' % _size(int(limit))
    return text + ' (%s)' % how


SWAP_UNITS = {'K': 1 << 10, 'M': 1 << 20, 'G': 1 << 30, 'T': 1 << 40}


def swap(system=None, read=None, run=None, kernel32=None):
    """(total, free, how) in bytes of the machine's swap (BUILD-OOM-HELP-AND-TIP-68): Linux /proc/meminfo SwapTotal and
    SwapFree, macOS sysctl vm.swapusage, Windows the page files (GlobalMemoryStatusEx: the commit limit less the
    physical memory); (None, None, why) where nothing answers. READ, RUN and KERNEL32 stand in for the file reader,
    subprocess.run and the Windows kernel in tests."""
    system = system or platform.system()
    if system == 'Linux':
        found = {}
        for row in ((read or _read)('/proc/meminfo') or '').splitlines():
            key, _, value = row.partition(':')
            if key in ('SwapTotal', 'SwapFree'):
                try:
                    found[key] = int(value.split()[0]) * 1024
                except (ValueError, IndexError):
                    pass
        if 'SwapTotal' in found:
            return found['SwapTotal'], found.get('SwapFree'), '/proc/meminfo'
        return None, None, '/proc/meminfo did not answer'
    if system == 'Darwin':
        try:
            done = (run or subprocess.run)(['sysctl', '-n', 'vm.swapusage'], capture_output=True, text=True,
                                           errors='replace', timeout=MEMORY_SECONDS, stdin=subprocess.DEVNULL)
            text = done.stdout if done.returncode == 0 else ''
        except (OSError, subprocess.SubprocessError):
            text = ''
        values = {name: re.search(r'\b%s = ([0-9.]+)([KMGT])' % name, text) for name in ('total', 'free')}
        if values['total']:
            def size(found):
                return int(float(found.group(1)) * SWAP_UNITS[found.group(2)]) if found else None
            return size(values['total']), size(values['free']), 'sysctl vm.swapusage'
        return None, None, 'sysctl vm.swapusage did not answer'
    if system == 'Windows':
        status, why = _windows_status(kernel32)
        if status is None:
            return None, None, why
        total = max(0, int(status.ullTotalPageFile) - int(status.ullTotalPhys))
        free = max(0, int(status.ullAvailPageFile) - int(status.ullAvailPhys))
        return total, min(free, total), 'GlobalMemoryStatusEx: the commit limit less the physical memory'
    return None, None, 'no swap reader for %s' % system


def swap_text(system=None, cgroup=None, **readers):
    """The swap line: its total and what is free, or none; on Linux also a container's own swap limit (cgroup
    memory.swap.max, CGROUP(path) stands in for the file in tests)."""
    system = system or platform.system()
    total, free, how = swap(system, **readers)
    if total is None:
        text = 'Not available (%s)' % how
    elif total == 0:
        text = 'none (%s)' % how
    else:
        text = '%s total, %s (%s)' % (_size(total), '%s free' % _size(free) if free is not None else 'free not read', how)
    if system == 'Linux':
        limit = (cgroup or (lambda path: _cgroup(path)))('/sys/fs/cgroup/memory.swap.max')
        if limit == '0':
            text += '; the container allows no swap (cgroup memory.swap.max 0)'
        elif limit and limit.isdigit():
            text += '; container swap limit %s' % _size(int(limit))
    return text


def memory_peak_text(ctx):
    """The build's memory peak beside the memory it saw, and the failed stage's peak with its largest process
    (tools/build_failure.py build_memory_seen and stage_memory; BUILD-OOM-HELP-AND-TIP-68)."""
    import build_failure
    seen = build_failure.build_memory_seen(ctx.run) if ctx.run is not None else {}
    parts = []
    if seen.get('peak'):
        parts.append('%s of the %s the build saw (%s)%s' % (
            _size(seen['peak']), _size(seen['limit']), seen['source'],
            ', with %s running' % ', '.join(seen['peak_stages']) if seen.get('peak_stages') else ''))
    elif seen:
        parts.append('not recorded; the build saw %s (%s)' % (_size(seen['limit']), seen['source']))
    for step in ctx.failed_stages():
        name = str(step.get('name'))
        found = build_failure.stage_memory(ctx.run, name, ctx.workspace)
        if found:
            parts.append('the failed stage %s reached %s, its largest process %s (%s)' % (
                name, _size(found['peak']), _size(found['largest']), found['source']))
    return '; '.join(parts) if parts else 'not recorded (the build kept no memory figures)'


def free_text(folder):
    """The free space of the disk FOLDER is on (its nearest existing parent when it is not made yet)."""
    try:
        folder = Path(folder)
        while not folder.exists() and folder.parent != folder:
            folder = folder.parent
        usage = shutil.disk_usage(folder)
    except OSError:
        return 'not read'
    return '%s of %s' % (_size(usage.free), _size(usage.total))


def temp_folder():
    """The temp folder, only to say how much room it has (the report writes nothing there)."""
    return tempfile.gettempdir()


def machine(ctx):
    temp = temp_folder()
    return ['Operating system: ' + system_text(), 'Cores: ' + cores_text(ctx), 'Memory: ' + memory_text(),
            'Swap: ' + swap_text(), 'Memory peak: ' + memory_peak_text(ctx),
            'Free space in the workspace: ' + free_text(ctx.workspace),
            'Free space in the temp folder (%s): %s' % (ctx.path(temp), free_text(temp))]


def start_lines(args, root=None):
    """The machine block a build prints at its start (BUILD-OOM-HELP-AND-TIP-68): the environment summary's lines, so a
    build that is ended without a report (the whole build killed for memory) still has them in its log. Never raises."""
    try:
        from types import SimpleNamespace
        workspace = Path(getattr(args, 'workspace', None) or (Path(root or ROOT) / 'out'))
        paths = Paths(workspace, root or ROOT)
        return environment(SimpleNamespace(args=args, workspace=workspace, path=paths.text), start=True)
    except Exception as exc:  # noqa: BLE001 - the start lines never stop the build
        return ['Machine at the start of the build: not read (%s)' % type(exc).__name__]


def tip_lines(ctx):
    """The block a failed build ends with (tools/build_failure.py tip_lines), at the top of the report: from the run's
    failure record, else from the builder's own error."""
    import build_failure
    rec = None
    if ctx.run is not None and not ctx.foreign:
        rec = build_failure._read_record(ctx.run)
    argv = [str(part) for part in getattr(ctx.args, '_argv', None) or []]
    report = getattr(ctx, 'report_file', None)
    if rec is not None:
        return build_failure.tip_lines(rec, ctx.run, ctx.workspace, argv=argv, live=True, report=report)
    return build_failure.tip_lines(build_failure.bare_record(ctx.error, argv), None, ctx.workspace, argv=argv,
                                   live=True, report=report)


def stage_plan(ctx):
    names = ctx.plan_names()
    if not names:
        return ['No stage plan: the build stopped before it planned its stages.']
    recorded = {str(step.get('name')): step for step in ctx.state.get('steps') or [] if isinstance(step, dict)}
    reused = ctx.stage_cache.get('reused') or {}
    keys = ctx.stage_cache.get('fingerprints') or {}
    started = bool(recorded)
    width = max(len(name) for name in names)
    lines = ['%3s  %-*s  %-24s  %-12s  %7s  %s' % ('#', width, 'stage', 'state', 'time', 'workers', 'key')]
    counts = {}
    for number, name in enumerate(names, 1):
        step = recorded.get(name)
        if step is None:
            state = 'not started' if started else 'planned'
        else:
            state = {'running': 'stopped with the build'}.get(step.get('status'), str(step.get('status')))
        if name in reused:
            state += ', reused'
        counts[state] = counts.get(state, 0) + 1
        lines.append('%3d  %-*s  %-24s  %-12s  %7s  %s' % (
            number, width, name, state, _seconds((step or {}).get('elapsed_seconds')),
            (step or {}).get('jobs', '-'), str(keys.get(name) or '-')[:12]))
    lines.append('')
    lines.append('Stages: %d; ' % len(names) + ', '.join('%d %s' % (n, state) for state, n in sorted(counts.items())))
    if ctx.state.get('elapsed_seconds') is not None:
        lines.append('Build time: %s' % _seconds(ctx.state.get('elapsed_seconds')))
    return lines


def reuse(ctx):
    args, cache = ctx.args, ctx.stage_cache
    lines = []
    source = cache.get('reuse_from') or getattr(args, 'reuse_from', None)
    # the default of a plain build (BUILD-OFFER-EARLIER-RUNS-67, tools/reuse_all.py settle_default)
    default = ctx.metadata.get('reuse_default') or getattr(args, 'reuse_default_record', None)
    if isinstance(default, dict):
        lines.append('Reuse of earlier builds: %s (%s)%s' % (
            'on' if default.get('on') else 'off', default.get('selected_by'),
            '; asked: %s' % default['answered_by'] if default.get('answered_by') else ''))
    if getattr(args, 'reuse_all_available', False):
        lines.append('Reuse: every earlier run of the workspace (--reuse-all-available%s)'
                     % (', the default of this build' if isinstance(default, dict) and default.get('on') else ''))
    lines.append('Reuse source: %s' % (ctx.path(source) if source else 'none (every stage runs)'))
    mode = cache.get('reuse_mode') or getattr(args, 'reuse_mode', None)
    lines.append('Reuse mode: %s' % (mode or '-'))
    pool = (ctx.metadata.get('storage_pool') or {})
    if pool:
        lines.append('Storage pool: %s' % ctx.path(_short(json.dumps(_jsonable(pool), sort_keys=True))))
    if not cache:
        lines.append('No reuse plan was made (the build stopped before it keyed its stages).')
        return lines
    reused = cache.get('reused') or {}
    total = len(ctx.plan_names()) or len(cache.get('fingerprints') or {})
    lines.append('Stages reused: %d of %d' % (len(reused), total))
    for name, row in sorted(reused.items()):
        lines.append('  %s from %s (%s files, %s)' % (name, ctx.path(row.get('from')), row.get('files'),
                                                      _size(row.get('bytes'))))
    not_reused = cache.get('not_reused') or {}
    if not_reused:
        lines.append('Stages not reused, with the reason:')
        for name, why in sorted(not_reused.items()):
            text = why if isinstance(why, str) else json.dumps(_jsonable(why), sort_keys=True)
            lines.append('  %s: %s' % (name, ctx.path(_short(text))))
    check = cache.get('preflight') or {}
    if check:
        def count(value):
            return len(value) if isinstance(value, (list, dict)) else value
        lines.append('Reuse preflight: %s reused, %s rebuilt, unexpected: %s, too broad: %s' % (
            count(check.get('reused')), count(check.get('rebuilt')),
            ', '.join(check.get('unexpected_stages') or []) or 'none', ', '.join(check.get('too_broad') or []) or 'none'))
    stops = (cache.get('minute_one') or {}).get('stops') or []
    if stops:
        lines.append('Reuse stops (the stored units the build would make again):')
        lines += ['  %s: %s' % (row[0], ctx.path(_short(row[1]))) for row in stops if len(row) >= 2]
    notices = (cache.get('minute_one') or {}).get('notices') or []
    if notices:
        lines.append('Reuse notices (the default build made this stored work again and went on):')
        lines += ['  %s: %s' % (row[0], ctx.path(_short(row[1]))) for row in notices if len(row) >= 2]
    if isinstance(default, dict) and default.get('notice'):
        lines += [ctx.path(line) for line in default['notice']]
    allowed = (cache.get('minute_one') or {}).get('allowed') or {}
    if allowed:
        lines.append('Allowed to rebuild: ' + '; '.join('%s: %s' % pair for pair in sorted(allowed.items())))
    if cache.get('forced'):
        lines.append('Rebuilt on request (--rebuild-stage): ' + ', '.join(cache['forced']))
    return lines


PARTS = (('1. What failed', what_failed), ('2. Build settings', settings), ('3. Versions', versions),
         ('4. Game data', game_data), ('5. Machine', machine), ('6. Stage plan', stage_plan), ('7. Reuse', reuse))


def render(ctx):
    lines = header(ctx)
    for title, build in PARTS:
        if title.endswith('What failed') and ctx.status == 'passed':
            title = '1. Result'
        lines += _part(title, build, ctx)
    lines.append('End of the build report.')
    return '\n'.join(lines) + '\n'


def write(args, status, error=None, metadata=None, steps=None, factory=None, root=None, version=None, result=None,
          code=None, stream=None):
    """Write logs/BUILD-REPORT-<run>.txt in ARGS' workspace for a build that ended with STATUS (failed, passed,
    cancelled); ERROR: the builder's exception; METADATA and STEPS: the build's receipt and stage plan as far as it
    got; FACTORY: the builder's parser function. Prints where it is. Returns the path, or None (never raises)."""
    stream = stream or sys.stdout
    try:
        ctx = Context(args, status, error, metadata, steps, factory, root, version, result, code)
        name = ctx.name or fallback_name(version)
        path = report_path(ctx.workspace, name)
        ctx.report_file = path
        text = render(ctx)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(text, encoding='utf-8', newline='\n')
        temporary.replace(path)
        stream.write('Build report: %s\n  Everything about this build in one file (what failed, the settings, the '
                     'versions, the game data, the stage plan, the stage\'s log). It stays on this computer; send '
                     'this one file when you ask for help.\n' % path)
        stream.flush()
        return path
    except Exception as exc:  # noqa: BLE001 - the report never hides the build's own result
        print('[report] the build report was not written: %s: %s' % (type(exc).__name__, exc), flush=True)
        return None
