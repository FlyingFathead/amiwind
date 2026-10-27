#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The free space a build needs, checked first and measured on every passing build (BUILD-DISK-NEED-UNKNOWN-52).

A tester's public v0.0.50 build stopped halfway when its disk filled: the only check asked a fixed 20 GiB once. The
maintainer (26 October 2026): the check among the very first steps of a build, failing fast; the minimum configurable
in the build defaults; compared automatically with the last known good build, about 30 % over it; the game data
copied into Docker counted too.

The figure. Every passing build writes RUN/disk-footprint.json, in bytes on disk:

  run      the run folder at the end of the build (each file once: pooled files are links to the pool's objects);
  scratch  the most the build's file systems grew above their final growth while it ran (the stages' scratch
           folders and other files removed before the end), sampled every few seconds;
  cache    what the build added to the workspace's file system besides its run folder: cache and pool entries;
  pool     the same for the storage pool when it has a file system of its own (tools/storage_pool.py);
  game_data  the game data folder (a Docker build copies it into a volume first);

and, per stage, the most each role's file system (workspace, pool) grew while the stage ran. Growth is read from the
free space (no walk of a shared cache of millions of files); other work on the same file system meanwhile counts
too, so the figure errs on the safe side. The release ships the last known good figure as
config/disk-footprint.json (`disk_need.py ship RUN`); tests/test_disk_need.py fails when it is missing or older than
the release. A Docker build adds the builder image (builder_image, measured once).

The need. For each file system: the figure's bytes of everything placed on it, less the cache and pool when the
workspace already holds a passing build's (they are reused), plus the margin (disk_margin_percent, 30 by default);
the workspace's file system never below the minimum (min_free_gib, 35 by default: the v0.0.52 floor). The figure is
the larger of the shipped one and the newest passing build of this workspace, category by category. Both settings
live in config/build-defaults.json and are machine settings: they key no stage (tools/build_cache.py
MACHINE_SETTINGS; tests/test_disk_need.py). --min-free-gib and --disk-margin-percent, or AMIWIND_MIN_FREE_GIB and
AMIWIND_DISK_MARGIN_PERCENT, override them; AMIWIND_DISK_WATCH=off turns the checks and the figure off (the test
suite's temporary workspaces).

Where it runs: tools/build.py right after the options are read (every image build: ./build.sh, build.cmd and the
build inside Docker), tools/build_docker.py before the builder image is built, tools/run_docker.py before the game
data is copied into a volume, and before each stage (tools/build_profile.py start: the stage's own last figure plus
the margin).

    python3 tools/disk_need.py check --workspace DIR [--pool DIR] [--add CATEGORY=BYTES]
    python3 tools/disk_need.py ship RUN        (copies a passing run's figure to config/disk-footprint.json)
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_FILE = ROOT / 'config' / 'build-defaults.json'
FIGURE_FILE = ROOT / 'config' / 'disk-footprint.json'
RECORD = 'disk-footprint.json'
SCHEMA = 'amiwind-disk-footprint-1'
MIN_FREE_KEY = 'min_free_gib'
MARGIN_KEY = 'disk_margin_percent'
# Settings of config/build-defaults.json that only say how much room this machine must have: no stage key counts them
# (tools/build_cache.py keys that file without them).
MACHINE_SETTINGS = frozenset({MIN_FREE_KEY, MARGIN_KEY})
MIN_FREE_ENV = 'AMIWIND_MIN_FREE_GIB'
MARGIN_ENV = 'AMIWIND_DISK_MARGIN_PERCENT'
WATCH_ENV = 'AMIWIND_DISK_WATCH'
# tools/build.py options that build no image (previews, setup, inventories, the asset-free dry run): no check
SETUP_ONLY = ('dry_run', 'plan', 'check', 'host_plan', 'install_dependencies', 'install_sdk', 'versions',
              'check_inputs', 'layout_selftest', 'estimate_world')
PRERENDERED_ACTIONS = ('list', 'verify', 'prune')
FALLBACK_MIN_FREE_GIB = 35
FALLBACK_MARGIN_PERCENT = 30
CATEGORIES = ('run', 'scratch', 'cache', 'pool', 'game_data', 'builder_image')
REUSED = ('cache', 'pool')             # left in the workspace by a passing build and reused by the next
GIB = 2 ** 30
INTERVAL = 5.0


class DiskShort(OSError):
    """Too little free space before a stage (the build stops before starting it)."""


def settings(environ=None, defaults=DEFAULTS_FILE):
    """{'min_free_gib', 'margin_percent'}: the environment over config/build-defaults.json over the fallbacks."""
    environ = os.environ if environ is None else environ
    try:
        values = json.loads(Path(defaults).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        values = {}
    result = {'min_free_gib': values.get(MIN_FREE_KEY, FALLBACK_MIN_FREE_GIB),
              'margin_percent': values.get(MARGIN_KEY, FALLBACK_MARGIN_PERCENT)}
    for key, name in (('min_free_gib', MIN_FREE_ENV), ('margin_percent', MARGIN_ENV)):
        if environ.get(name):
            try:
                result[key] = float(environ[name])
            except ValueError:
                raise ValueError(f'{name}={environ[name]!r} is not a number') from None
    for key, value in result.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f'config/build-defaults.json: {key} must be a number of at least 0, not {value!r}')
    return result


def check_figure(figure, where):
    if not isinstance(figure, dict) or figure.get('schema') != SCHEMA:
        raise ValueError(f'{where}: not a {SCHEMA} figure')
    sizes = figure.get('bytes')
    if not isinstance(sizes, dict) or not all(isinstance(sizes.get(c, 0), int) and sizes.get(c, 0) >= 0
                                              for c in CATEGORIES):
        raise ValueError(f'{where}: "bytes" needs a whole number of at least 0 for each of ' + ', '.join(CATEGORIES))
    if not re.fullmatch(r'\d+\.\d+\.\d+(-(dev|rc)\d*)?', str(figure.get('version'))):
        raise ValueError(f'{where}: "version" must be the version of the build it was measured on')
    return figure


def load(path):
    path = Path(path)
    return check_figure(json.loads(path.read_text(encoding='utf-8')), str(path))


def shipped(path=FIGURE_FILE):
    try:
        return load(path)
    except (OSError, ValueError):
        return None


def local(workspace):
    """The figure of the newest passing build of WORKSPACE (WORKSPACE/build/*/disk-footprint.json), or None."""
    found = []
    try:
        runs = list(os.scandir(Path(workspace) / 'build'))
    except OSError:
        return None
    for entry in runs:
        path = Path(entry.path) / RECORD
        try:
            found.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for _, path in sorted(found, reverse=True):
        try:
            return load(path)
        except (OSError, ValueError):
            continue
    return None


def reference(workspace, figure_file=FIGURE_FILE):
    """(figure, local figure or None): the larger of the shipped figure and this workspace's newest passing build,
    category by category and stage by stage."""
    ship, mine = shipped(figure_file), local(workspace)
    merged = {'schema': SCHEMA, 'bytes': {c: 0 for c in CATEGORIES}, 'stages': {}, 'sources': []}
    for figure in (ship, mine):
        if figure is None:
            continue
        merged['sources'].append('%s (%s)' % (figure.get('build') or '?', figure['version']))
        for category in CATEGORIES:
            merged['bytes'][category] = max(merged['bytes'][category], int(figure['bytes'].get(category) or 0))
        for stage, roles in (figure.get('stages') or {}).items():
            row = merged['stages'].setdefault(stage, {})
            for role, value in roles.items():
                row[role] = max(row.get(role, 0), int(value or 0))
    return merged, mine


def warm(workspace, mine=None, look=8):
    """True when WORKSPACE holds the cache and pool of a passing build (its figure, or one of its LOOK newest run
    folders passed): the next build there reuses them, so they need no new room."""
    if mine is not None:
        return True
    try:
        runs = sorted(os.scandir(Path(workspace) / 'build'), key=lambda e: e.stat().st_mtime, reverse=True)
    except OSError:
        return False
    for entry in runs[:look]:
        try:
            with open(Path(entry.path) / 'build-state.json', encoding='utf-8') as state:
                if json.load(state).get('status') == 'passed':
                    return True
        except (OSError, ValueError, AttributeError):
            continue
    return False


def existing(path):
    path = Path(path).absolute()
    while not path.exists() and path.parent != path:
        path = path.parent
    return path


def device(path):
    try:
        return os.stat(existing(path)).st_dev
    except OSError:
        return None


def free_bytes(path):
    try:
        return shutil.disk_usage(existing(path)).free
    except OSError:
        return None


def roles(workspace, pool=None, scratch=None, extra=None):
    """{category: folder} where a build puts each category (EXTRA: {category: folder} of a Docker build)."""
    workspace = Path(workspace)
    places = {'run': workspace / 'build', 'scratch': Path(scratch) if scratch else workspace / 'build',
              'cache': workspace / 'cache', 'pool': Path(pool) if pool else workspace / 'cache' / 'asset-pool-v1'}
    places.update(extra or {})
    return places


def plan(workspace, pool=None, scratch=None, extra=None, figure=None, mine=None, config=None, adds=None):
    """[row] per file system: {'path', 'categories', 'figure', 'present', 'need', 'free'} (bytes).

    ADDS: {category: bytes} measured now (the game data a Docker build is about to copy), over the figure."""
    config = config or settings()
    if figure is None:
        figure, mine = reference(workspace)
    places = roles(workspace, pool, scratch, extra)
    sizes = dict(figure['bytes'])
    sizes.update(adds or {})
    margin = 1 + config['margin_percent'] / 100.0
    home = device(workspace)
    reused = warm(workspace, mine)
    rows = {}
    for category, folder in places.items():
        dev = device(folder)
        row = rows.setdefault(dev, {'path': str(existing(folder)), 'categories': [], 'figure': 0, 'present': 0})
        row['categories'].append(category)
        row['figure'] += int(sizes.get(category) or 0)
        if category in REUSED and reused and Path(folder).is_dir():
            row['present'] += int(sizes.get(category) or 0)
    result = []
    for dev, row in rows.items():
        need = int(max(0, row['figure'] - row['present']) * margin)
        if dev == home:
            need = max(need, int(config['min_free_gib'] * GIB))
        row.update(need=need, free=free_bytes(row['path']))
        result.append(row)
    return result


def gib(value):
    return '%.1f GiB' % (value / GIB)


def problems(rows, config=None):
    config = config or settings()
    found = []
    for row in rows:
        if row['free'] is not None and row['free'] < row['need']:
            found.append(f"{gib(row['free'])} free on the file system of {row['path']} ({', '.join(row['categories'])}), "
                         f"{gib(row['need'])} needed: the last known good build's {gib(row['figure'])}"
                         + (f" less {gib(row['present'])} of cache and pool already there" if row['present'] else '')
                         + f" plus {config['margin_percent']:g} %, never below {config['min_free_gib']:g} GiB; fix: "
                         f"free space there or build in another --workspace (config/build-defaults.json "
                         f"{MIN_FREE_KEY} and {MARGIN_KEY}; {MIN_FREE_ENV}, {MARGIN_ENV})")
    return found


def summary(rows):
    return 'Free space: ' + '; '.join(f"{gib(row['free']) if row['free'] is not None else '?'} free, {gib(row['need'])} "
                                      f"needed at {row['path']} ({', '.join(row['categories'])})" for row in rows)


def entry(args, parser, pool_for=None):
    """tools/build.py, right after the options are read: an image build stops here when a file system is short."""
    if getattr(args, 'stage', None) != 'aga' or any(getattr(args, name, None) for name in SETUP_ONLY):
        return
    if (getattr(args, 'prerendered', None) or [None])[0] in PRERENDERED_ACTIONS or os.environ.get(WATCH_ENV) == 'off':
        return
    for option, name in (('min_free_gib', MIN_FREE_ENV), ('disk_margin_percent', MARGIN_ENV)):
        if getattr(args, option, None) is not None:      # --min-free-gib, --disk-margin-percent: for the stages too
            os.environ[name] = '%g' % getattr(args, option)
    try:
        pool = pool_for(args) if pool_for else None
    except (OSError, ValueError):
        pool = None
    try:
        config = settings()
        rows = plan(args.workspace, pool, os.environ.get('AMIWIND_SCRATCH'), config=config)
    except ValueError as exc:
        parser.exit(2, f'Error: {exc}\n')
    print(summary(rows), flush=True)
    found = problems(rows, config)
    if found:
        parser.exit(1, 'Build stopped before any work (BUILD-DISK-NEED-UNKNOWN-52):\n  ' + '\n  '.join(found) + '\n')


# --------------------------------------------------------------------------
# Measuring a build

def tree_bytes(roots, seen=None, workers=None, since=None):
    """Bytes on disk of the files under ROOTS, each inode once (SEEN: {(dev, ino)} shared across calls); with SINCE
    (seconds since the epoch) only files written at or after it. One thread per top folder: the walk is I/O."""
    seen = set() if seen is None else seen
    tops = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        try:
            tops += [entry.path for entry in os.scandir(root)]
        except OSError:
            continue

    def walk(top):
        found = {}
        stack = [top]
        while stack:
            path = stack.pop()
            try:
                info = os.stat(path, follow_symlinks=False)
            except OSError:
                continue
            if os.path.isdir(path) and not os.path.islink(path):
                try:
                    stack += [entry.path for entry in os.scandir(path)]
                except OSError:
                    pass
                continue
            if since is not None and info.st_mtime < since:
                continue
            blocks = getattr(info, 'st_blocks', None)
            found[(info.st_dev, info.st_ino)] = blocks * 512 if blocks is not None else info.st_size
        return found

    total = 0
    with ThreadPoolExecutor(max_workers=workers or min(32, (os.cpu_count() or 1) * 2)) as pool:
        for found in pool.map(walk, tops):
            for key, value in found.items():
                if key not in seen:
                    seen.add(key)
                    total += value
    return total


class Watch:
    """A build's disk figure: samples each role's file system while stages run, checks each stage's last figure
    before it starts and writes RUN/disk-footprint.json when the build passes."""

    def __init__(self, run, metadata, interval=INTERVAL, config=None, figure=None):
        self.run = Path(run)
        self.started = time.time() - 1
        self.workspace = self.run.parent.parent
        self.metadata = metadata
        self.config = config or settings()
        self.figure = figure if figure is not None else reference(self.workspace)[0]
        pool = metadata.get('storage_pool_dir') or self.workspace / 'cache' / 'asset-pool-v1'
        self.places = {'workspace': self.workspace, 'pool': Path(pool)}
        self.devices = {}
        for role, path in self.places.items():
            dev = device(path)
            if dev not in self.devices.values():
                self.devices[role] = dev
        self.start_free = {role: free_bytes(self.places[role]) for role in self.devices}
        self.low = dict(self.start_free)
        self.stage_start, self.stage_low, self.stages = {}, {}, {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, args=(interval,), name='disk-need', daemon=True)
        self.thread.start()

    def _sample(self):
        now = {role: free_bytes(self.places[role]) for role in self.devices}
        with self.lock:
            for role, value in now.items():
                if value is None:
                    continue
                if self.low.get(role) is None or value < self.low[role]:
                    self.low[role] = value
                for low in self.stage_low.values():
                    if low.get(role) is None or value < low[role]:
                        low[role] = value
        return now

    def _loop(self, interval):
        while not self.stop.wait(interval):
            self._sample()

    def before(self, name):
        """Stop (DiskShort) when a role's file system has less free space than the stage's last figure plus the
        margin; then start watching the stage."""
        now = self._sample()
        last = self.figure.get('stages', {}).get(name) or {}
        margin = 1 + self.config['margin_percent'] / 100.0
        for role in self.devices:
            need = int(int(last.get(role) or 0) * margin)
            if need and now.get(role) is not None and now[role] < need:
                message = (f'Build stopped before the stage {name} (BUILD-DISK-NEED-UNKNOWN-52): {gib(now[role])} free on '
                           f'the {role} file system ({self.places[role]}), {gib(need)} needed (its last known good build '
                           f'used {gib(int(last[role]))}, plus {self.config["margin_percent"]:g} %); fix: free space '
                           f'there and resume with --reuse-from {self.run}')
                print(message, flush=True)
                raise DiskShort(message)
        with self.lock:
            self.stage_start[name] = dict(now)
            self.stage_low[name] = dict(now)

    def finished(self, name):
        self._sample()
        with self.lock:
            start, low = self.stage_start.pop(name, None), self.stage_low.pop(name, None)
        if start is None:
            return
        self.stages[name] = {role: max(0, (start[role] or 0) - (low.get(role) or 0))
                             for role in self.devices if start.get(role) is not None}

    def close(self, receipt):
        self.stop.set()
        now = self._sample()
        if receipt.get('status') != 'passed':
            return None
        try:
            return self.record(receipt, now)
        except Exception as exc:  # noqa: BLE001 - a missing figure is reported, never a failed build
            print(f'[warning] Disk figure not written: {exc}', flush=True)
            return None

    def record(self, receipt, now):
        # The run folder whole (each file once: its pooled files are links to the pool's objects; about 130,000 files,
        # seconds). The cache and the pool by what the build added to their file systems: the growth of the free space
        # less the run's new files, never by a walk (a shared pool and cache hold millions of earlier builds' files).
        # A build that reused stages added less than a fresh one: the need takes the larger of this and the shipped
        # figure. Other work on the same file system while the build ran counts too: the figure errs on the safe side.
        run_new = tree_bytes([self.run], since=self.started)
        sizes = {'run': tree_bytes([self.run])}
        growth = {role: max(0, (self.start_free[role] or 0) - (now.get(role) or 0)) for role in self.devices
                  if self.start_free.get(role) is not None and now.get(role) is not None}
        peak = {role: max(0, (self.start_free[role] or 0) - (self.low.get(role) or 0)) for role in growth}
        sizes['cache'] = max(0, growth.get('workspace', 0) - run_new)
        sizes['pool'] = growth.get('pool', 0)            # only when the pool has a file system of its own
        sizes['scratch'] = max([0] + [peak[role] - growth[role] for role in growth])
        data = self.metadata.get('data_files')
        sizes['game_data'] = tree_bytes([data]) if data and data != 'None' else 0
        sizes['builder_image'] = int((shipped() or {}).get('bytes', {}).get('builder_image') or 0)
        figure = {'schema': SCHEMA, 'version': receipt.get('runtime_version') or self.metadata.get('runtime_version')
                  or (ROOT / 'VERSION').read_text(encoding='utf-8').strip(),
                  'build': self.run.name, 'measured': datetime.date.today().isoformat(),
                  'bytes': {c: int(sizes.get(c) or 0) for c in CATEGORIES},
                  'file_systems': [{'role': role, 'peak_growth': peak[role], 'growth': growth[role]} for role in growth],
                  'stages': dict(sorted(self.stages.items()))}
        temporary = self.run / (RECORD + '.tmp')
        temporary.write_text(json.dumps(figure, indent=2) + '\n', encoding='utf-8', newline='\n')
        temporary.replace(self.run / RECORD)
        print('Disk figure: ' + ', '.join(f'{c} {gib(figure["bytes"][c])}' for c in CATEGORIES if figure['bytes'][c])
              + f' ({self.run / RECORD}; ship it with tools/disk_need.py ship)', flush=True)
        return figure


class WatchedSession:
    """A profiling session (tools/build_profile.py) with the disk watch: the stage check before each stage."""

    def __init__(self, session, watch):
        self._session, self._watch = session, watch

    def __getattr__(self, name):
        return getattr(self._session, name)

    def command(self, number, name, command, jobs):
        self._watch.before(name)
        return self._session.command(number, name, command, jobs)

    def finished(self, name, entry):
        self._watch.finished(name)
        return self._session.finished(name, entry)

    def close(self, receipt):
        result = self._session.close(receipt)
        self._watch.close(receipt)
        return result


def watched(session, run, metadata):
    """SESSION with the disk watch for a real image build (a build receipt of stage 'aga', not the asset-free dry
    run); AMIWIND_DISK_WATCH=off leaves it out."""
    if (metadata.get('schema') != 'amiwind-build-receipt-v1' or metadata.get('stage') != 'aga'
            or metadata.get('npc_gallery') == 'asset-free' or os.environ.get(WATCH_ENV) == 'off'):
        return session
    try:
        return WatchedSession(session, Watch(run, metadata))
    except (OSError, ValueError) as exc:
        print(f'[warning] Disk watch off: {exc}', flush=True)
        return session


# --------------------------------------------------------------------------
# Docker builds and the shipped figure

def docker_problems(root, figure=None, config=None, build=True):
    """([problem], need, free) before the builder image is built: on the file system of Docker's storage (ROOT, a host
    folder), the builder image and, when BUILD (a full build follows), the last known good build and its game data
    copy too, plus the margin and never below the minimum. free is None when that folder cannot be seen from this
    host (Docker Desktop keeps it in its own virtual machine): tools/run_docker.py checks the build's volume before
    the game data copy."""
    config = config or settings()
    figure = figure or shipped() or {'bytes': {}}
    sizes = figure['bytes']
    total = int(sizes.get('builder_image') or 0)
    if build:
        total += sum(int(sizes.get(c) or 0) for c in ('run', 'scratch', 'cache', 'pool', 'game_data'))
    need = int(total * (1 + config['margin_percent'] / 100.0))
    if build:
        need = max(need, int(config['min_free_gib'] * GIB))
    free = free_bytes(root) if root and Path(root).exists() else None
    if free is None or free >= need:
        return [], need, free
    return [f'{gib(free)} free where Docker keeps its images and volumes ({root}), {gib(need)} needed (the '
            + ('builder image, the game data copy and the last known good build' if build else 'builder image')
            + f', plus {config["margin_percent"]:g} %' + (f', never below {config["min_free_gib"]:g} GiB' if build else '')
            + '); fix: free space there (docker system df shows what Docker holds)'], need, free


def docker_root(docker):
    """The folder where Docker keeps images and volumes (docker info), or None."""
    import subprocess
    try:
        found = subprocess.run(list(docker) + ['info', '--format', '{{.DockerRootDir}}'], capture_output=True,
                               text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    root = found.stdout.strip()
    return root if found.returncode == 0 and root else None


def docker_volume_check(docker, volume, image, game_data=0):
    """The build's free space in the Docker volume VOLUME, checked by tools/disk_need.py inside IMAGE (no network),
    with GAME_DATA bytes about to be copied: (ok, text)."""
    import subprocess
    command = list(docker) + ['run', '--rm', '--network', 'none', '--mount', f'type=volume,source={volume},target=/work',
                              image, 'python', 'tools/disk_need.py', 'check', '--workspace', '/work']
    if game_data:
        command += ['--add', f'game_data={int(game_data)}']
    found = subprocess.run(command, capture_output=True, text=True)
    text = (found.stdout + found.stderr).strip()
    if found.returncode == 2 and 'disk_need.py' in text and 'No such file' in text:
        # an image built before this check: no claim either way (the build checks again first)
        return True, 'Free space: this builder image has no tools/disk_need.py; rebuild it with tools/build_docker.py'
    return found.returncode == 0, text


def release_version(version):
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-(dev|rc)\d*)?', version.strip())
    if not match:
        raise ValueError(f'{version!r} is not a version')
    return tuple(int(part) for part in match.groups()[:3]), match.group(4)


def ship(run, figure_file=FIGURE_FILE):
    """Copy RUN's figure (a passing build) to config/disk-footprint.json, keeping the measured builder image."""
    figure = load(Path(run) / RECORD)
    old = shipped(figure_file)
    if not figure['bytes'].get('builder_image') and old:
        figure['bytes']['builder_image'] = int(old['bytes'].get('builder_image') or 0)
    figure['note'] = ('The last known good build\'s disk figure (tools/disk_need.py, BUILD-DISK-NEED-UNKNOWN-52): '
                      'bytes on disk, each file once. Written by tools/disk_need.py ship RUN.')
    Path(figure_file).write_text(json.dumps(figure, indent=2) + '\n', encoding='utf-8', newline='\n')
    return figure


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    check = sub.add_parser('check', help='the free space checks of a build in WORKSPACE (exit 1 when short)')
    check.add_argument('--workspace', type=Path, required=True)
    check.add_argument('--pool', type=Path)
    check.add_argument('--add', action='append', default=[], metavar='CATEGORY=BYTES',
                       help='bytes measured now, over the figure (the game data a Docker build copies: game_data=N)')
    shipping = sub.add_parser('ship', help="copy a passing run's figure to config/disk-footprint.json")
    shipping.add_argument('run', type=Path)
    args = ap.parse_args(argv)
    if args.action == 'ship':
        figure = ship(args.run)
        print(f'config/disk-footprint.json: {figure["build"]} ({figure["version"]})')
        return 0
    adds = {}
    for item in args.add:
        category, _, value = item.partition('=')
        if category not in CATEGORIES or not value.isdigit():
            ap.error(f'--add {item}: CATEGORY=BYTES with one of ' + ', '.join(CATEGORIES))
        adds[category] = int(value)
    config = settings()
    rows = plan(args.workspace, args.pool, config=config, adds=adds,
                extra={'game_data': args.workspace} if 'game_data' in adds else None)
    print(summary(rows))
    found = problems(rows, config)
    for line in found:
        print('Disk need: ' + line)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
