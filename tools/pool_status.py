# SPDX-License-Identifier: GPL-3.0-only
"""What a stage's worker pools are doing right now, for the scheduler's live supervisor (BUILD-STAGE-ALLOWANCE-STUCK-43).

Under the stage scheduler (tools/build_parallel.py execute_parallel) every running pool map of a stage writes a small
JSON file beside the stage's allowance file (RUN/jobs/NN-stage.pool): per map its label, the units still queued
(None when the map reads a generator and has not reached its end), the units running, the units done and the slowest
running unit by name with its seconds so far. The scheduler reads it to:

- lend the workers of a stage with nothing queued to the stages that have queued units (its share comes back at the
  next look once it queues units again), and
- name a stage that runs under half its share for over a minute while units are queued (RUN/underused.jsonl).

Observability only: it never changes what a unit computes, the order units are handed out or the order results come
back (a key-neutral module, tools/build_cache.py INSTRUMENTATION_MODULES). Outside the scheduler nothing is written.
"""
import json
import os
import threading
import time
from pathlib import Path

ALLOWANCE_ENV = 'AMIWIND_BUILD_JOBS_FILE'      # the same variable as build_parallel.ALLOWANCE_ENV
SUFFIX = '.pool'
WRITE_SECONDS = 1.0
NAME_CHARS = 80

_lock = threading.Lock()
_maps = {}
_state = {'written': 0.0, 'serial': 0}


def status_path(allowance_file):
    return Path(str(allowance_file) + SUFFIX)


def unit_name(item, index):
    """A short readable name of one unit: the item itself when it is a name, else the first name-like part of a
    tuple, list or dict ('name', 'map', 'frame', 'town', 'path'), else '#index'."""
    def plain(value):
        if isinstance(value, (str, os.PathLike)):
            text = os.fspath(value)
            return text if len(text) <= NAME_CHARS else '...' + text[-(NAME_CHARS - 3):]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return None
    found = plain(item)
    if found is not None:
        return found
    if isinstance(item, dict):
        for key in ('name', 'map', 'frame', 'town', 'path'):
            if key in item and plain(item[key]) is not None:
                return plain(item[key])
    if isinstance(item, (tuple, list)):
        for part in item:
            found = plain(part)
            if found is not None:
                return found
            if isinstance(part, dict):
                found = unit_name(part, index)
                if not found.startswith('#'):
                    return found
    return '#%d' % index


class MapWatch:
    """One pool map's live counts. Every call is cheap; the file is written at most every WRITE_SECONDS."""

    def __init__(self, label, total, path):
        self.label, self.total, self.path = label, total, path
        self.submitted = self.done = 0
        self.exhausted = total is not None
        self.running = {}            # index -> (name, started)
        with _lock:
            _state['serial'] += 1
            self.key = '%d-%d' % (os.getpid(), _state['serial'])
            _maps[self.key] = self
        self.flush(force=True)

    def submit(self, index, item):
        name = unit_name(item, index)
        with _lock:
            self.submitted += 1
            self.running[index] = (name, time.monotonic())
        self.flush()

    def finish(self, index):
        # also called from the executor's thread (a future's done callback)
        with _lock:
            self.done += 1
            self.running.pop(index, None)
        self.flush()

    def end_of_input(self):
        self.exhausted = True
        self.flush()

    def queued(self):
        if self.total is not None:
            return max(0, self.total - self.submitted)
        return 0 if self.exhausted else None

    def row(self, now):
        slowest = None
        if self.running:
            name, started = min(self.running.values(), key=lambda value: value[1])
            slowest = [name, round(now - started, 1)]
        return {'label': self.label, 'queued': self.queued(), 'running': len(self.running), 'done': self.done,
                'slowest': slowest}

    def flush(self, force=False):
        now = time.monotonic()
        if not force and now - _state['written'] < WRITE_SECONDS:
            return
        _write(self.path, now)

    def close(self):
        with _lock:
            _maps.pop(self.key, None)
        _write(self.path, time.monotonic())


def _write(path, now):
    with _lock:
        _state['written'] = now
        rows = {key: watch.row(now) for key, watch in _maps.items() if watch.path == path}
    record = {'pid': os.getpid(), 'updated': round(time.time(), 3), 'maps': rows}
    temporary = path.with_name('%s.%d.tmp' % (path.name, os.getpid()))
    try:
        temporary.write_text(json.dumps(record) + '\n', encoding='utf-8', newline='\n')
        os.replace(temporary, path)
    except OSError:
        pass       # status for the supervisor only; never fails a stage


def watch(label, items):
    """A MapWatch for one pool map of the running stage, or None outside the scheduler. ITEMS: the map's input
    (its length when it has one)."""
    allowance = os.environ.get(ALLOWANCE_ENV)
    if not allowance:
        return None
    try:
        total = len(items)
    except TypeError:
        total = None
    return MapWatch(label, total, status_path(allowance))


def read(allowance_file, stale_seconds=30.0, now=None):
    """{'queued': n or None (more to come, count unknown), 'running': n, 'slowest': [name, seconds] or None,
    'maps': n} of one stage, from its status file; None when there is none or it is older than STALE_SECONDS."""
    path = status_path(allowance_file)
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    now = time.time() if now is None else now
    if now - float(record.get('updated') or 0) > stale_seconds and record.get('maps'):
        return None
    queued, unknown, running, slowest = 0, False, 0, None
    for row in (record.get('maps') or {}).values():
        if row.get('queued') is None:
            unknown = True
        else:
            queued += int(row['queued'])
        running += int(row.get('running') or 0)
        if row.get('slowest') and (slowest is None or row['slowest'][1] > slowest[1]):
            slowest = list(row['slowest'])
    return {'queued': None if unknown and not queued else queued, 'more': unknown or queued > 0,
            'running': running, 'slowest': slowest, 'maps': len(record.get('maps') or {})}
