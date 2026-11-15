"""The builder's own stall alert: a "stall" block in build-progress.json and a [stall] line in the build log, on by
default (standard library only). Anyone watching build-progress.json (the Toolkit build monitor, a script) gets it.

States, the same rules as the master builder's stall fallback (tools/stall_guard.py):
  stalled      no progress (no output, no log growth) for STALL_S and the build under IDLE_CORES cores;
  under-cores  under half of the planned cores for UNDER_S (working, but too slowly);
  slow         a stage past SLOW_FACTOR times its recorded time (its history);
  ok           none of these.
Block: {"state", "since" (seconds into the build the state began), "reason"}.

The start-up before the first stage (the entry check, the reuse preflight, the resource plan) is watched too:
StartupWatch writes the same file with status "starting" until the stage tracker takes it over.
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

STALL_S = 20 * 60
UNDER_S = 5 * 60
SLOW_FACTOR = 3.0
IDLE_CORES = 0.05
SCHEMA = 'amiwind-build-progress-v1'


STATUS_FORMAT = 'amiwind-build-status-1'
STATUS_DIR = 'status'


class StatusWriter:
    """The file interface any catcher can read (docs/BUILD_STATUS.md): FOLDER/heartbeat.json, rewritten atomically
    (temp file + rename) on every beat, and FOLDER/stall.jsonl, one JSON line appended per stall incident."""

    def __init__(self, folder, resume='', make_parents=False):
        """MAKE_PARENTS: the start-up may make the run folder for its status folder; the stage tracker never makes
        a run folder that is not there (a missing run stays missing)."""
        self.folder = Path(folder)
        self.resume = resume
        self.make_parents = make_parents

    def _ready(self):
        if not self.make_parents and not self.folder.parent.is_dir():
            return False
        self.folder.mkdir(parents=self.make_parents, exist_ok=True)
        return True

    def heartbeat(self, data):
        try:
            if not self._ready():
                return
            record = dict(data, format=STATUS_FORMAT, written_epoch=round(time.time(), 3))
            tmp = self.folder / ('heartbeat.json.tmp.%d' % os.getpid())
            tmp.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8', newline='\n')
            tmp.replace(self.folder / 'heartbeat.json')
        except Exception:  # noqa: BLE001 - never fails a build
            pass

    def incident(self, stage, block):
        try:
            if not self._ready():
                return
            line = json.dumps({'format': STATUS_FORMAT, 'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                               'epoch': round(time.time(), 3), 'stage': stage, 'state': block['state'],
                               'since': block['since'], 'reason': block['reason'], 'resume': self.resume})
            with open(self.folder / 'stall.jsonl', 'a', encoding='utf-8', newline='\n') as f:
                f.write(line + '\n')     # one write per line: a reader never sees half a record it can parse
        except Exception:  # noqa: BLE001
            pass


class Assessor:
    """Keeps the clocks between snapshots; assess() returns the block and, on a change of state, prints one line
    (and hands a new incident to ON_INCIDENT(what, block))."""

    def __init__(self, stream=None, stall_s=STALL_S, under_s=UNDER_S, slow_factor=SLOW_FACTOR, on_incident=None):
        self.on_incident = on_incident
        self.stream = stream or sys.stdout
        self.stall_s, self.under_s, self.slow_factor = stall_s, under_s, slow_factor
        self.under_since = None
        self.state, self.since = 'ok', 0.0

    def assess(self, now, what, silent, cores_now, cores_planned, elapsed=None, expected=None):
        """NOW: seconds into the build; SILENT: seconds since the last progress; ELAPSED/EXPECTED: the running
        stage's time and its recorded time (None without history)."""
        if cores_now is not None and cores_planned and cores_now < cores_planned / 2.0:
            if self.under_since is None:
                self.under_since = now
        else:
            self.under_since = None
        if silent is not None and silent >= self.stall_s and (cores_now is None or cores_now < IDLE_CORES):
            state = 'stalled'
            reason = ('%s: no progress for %d s at %s cores' %
                      (what, silent, 'unknown' if cores_now is None else '%.2f' % cores_now))
        elif self.under_since is not None and now - self.under_since >= self.under_s:
            state = 'under-cores'
            reason = ('%s: %.1f of %g planned cores for %d s' % (what, cores_now, cores_planned, now - self.under_since))
        elif expected and elapsed is not None and elapsed > self.slow_factor * expected:
            state = 'slow'
            reason = '%s: %d s, %.1f x its recorded %d s' % (what, elapsed, elapsed / expected, expected)
        else:
            state, reason = 'ok', ''
        if state != self.state:
            self.state, self.since = state, now
            block = {'state': state, 'since': round(self.since, 1), 'reason': reason}
            if state != 'ok':
                print('[stall] %s: %s' % (state, reason), file=self.stream, flush=True)
                if self.on_incident:
                    self.on_incident(what, block)
            else:
                print('[stall] ok again: %s' % what, file=self.stream, flush=True)
            return block
        return {'state': state, 'since': round(self.since, 1), 'reason': reason}


def from_progress(assessor, progress):
    """The block for a stage tracker snapshot (build_progress.Tracker.snapshot)."""
    running = [row for row in progress.get('stages') or () if row.get('status') == 'running']
    silent = None
    if running:
        silent = min(float((row.get('heartbeat') or {}).get('silent_seconds') or 0.0) for row in running)
    worst = None
    for row in running:
        if row.get('expected_seconds') and row.get('elapsed_seconds') is not None:
            ratio = row['elapsed_seconds'] / row['expected_seconds']
            if worst is None or ratio > worst[0]:
                worst = (ratio, row)
    what = ', '.join(row['name'] for row in running) or 'between stages'
    elapsed = worst[1]['elapsed_seconds'] if worst else None
    expected = worst[1]['expected_seconds'] if worst else None
    if worst:
        what = worst[1]['name']
    return assessor.assess(float(progress.get('elapsed_seconds') or 0.0), what, silent, progress.get('cores_now'),
                           progress.get('budget'), elapsed, expected)


def heartbeat_of(progress):
    """The heartbeat.json record from a progress snapshot (start-up or stage tracker)."""
    running = [row['name'] for row in progress.get('stages') or () if row.get('status') == 'running']
    return {'run': progress.get('run'), 'status': progress.get('status'),
            'started_at': progress.get('started_at'), 'ended_at': progress.get('ended_at'),
            'phase': progress.get('phase') or (', '.join(running) if running else None),
            'elapsed_seconds': progress.get('elapsed_seconds'), 'cores_now': progress.get('cores_now'),
            'cores_planned': progress.get('budget'), 'seconds_since_progress': progress.get('seconds_since_progress'),
            'stall': progress.get('stall')}


class _Tee:
    """sys.stdout that notes the time and text of the last line (start-up progress)."""

    def __init__(self, inner, watch):
        self.inner, self.watch = inner, watch

    def write(self, text):
        if text.strip():
            self.watch.last_line = text.strip().splitlines()[-1][:200]
            self.watch.last_progress = time.monotonic()
        return self.inner.write(text)

    def __getattr__(self, name):
        return getattr(self.inner, name)


class StartupWatch:
    """Writes PATH (build-progress.json, status "starting") every INTERVAL s from the start of build.py until stop():
    the last start-up line as the phase, the process's cores now against the cores planned, the seconds since the last
    line and the stall block."""

    def __init__(self, path, cores_planned, interval=5.0, assessor=None, status=None):
        self.path = Path(path) if path is not None else None   # None: log lines only (a check run)
        self.status = status            # a StatusWriter: heartbeat.json + stall.jsonl from the start-up on
        self.planned = cores_planned
        self.interval = interval
        self.origin = time.monotonic()
        self.started_epoch = time.time()
        self.last_progress = self.origin
        self.last_line = 'start-up'
        self.assessor = assessor or Assessor(on_incident=status.incident if status else None)
        self.cpu = (time.monotonic(), self._cpu())
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name='build-startup-watch', daemon=True)
        self.saved = None

    @staticmethod
    def _cpu():
        t = os.times()
        return t.user + t.system + t.children_user + t.children_system

    def start(self):
        self.saved = sys.stdout
        sys.stdout = _Tee(sys.stdout, self)
        self.write()
        self.thread.start()
        return self

    def snapshot(self):
        now = time.monotonic()
        wall, cpu = self.cpu
        used = self._cpu()
        cores = (used - cpu) / (now - wall) if now - wall > 0.5 else None
        self.cpu = (now, used)
        elapsed = now - self.origin
        silent = now - self.last_progress
        stall = self.assessor.assess(elapsed, 'start-up (%s)' % self.last_line, silent, cores, self.planned)
        return {'schema': SCHEMA, 'status': 'starting', 'phase': self.last_line,
                'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(self.started_epoch)),
                'updated_epoch': round(time.time(), 3), 'elapsed_seconds': round(elapsed, 1),
                'cores_now': None if cores is None else round(cores, 2), 'budget': self.planned,
                'seconds_since_progress': round(silent, 1), 'stages': [], 'stall': stall}

    def write(self):
        try:
            data = self.snapshot()                   # the assessment and its [stall] lines, files or not
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_name(self.path.name + '.tmp')
                tmp.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
                tmp.replace(self.path)
            if self.status:
                self.status.heartbeat(heartbeat_of(data))
        except Exception:  # noqa: BLE001 - never fails a build
            pass

    def _loop(self):
        while not self.stop_event.wait(self.interval):
            self.write()

    def stop(self, final=None):
        """FINAL: the status the last heartbeat says (a check or plan run that ends here: "checked"); None when the
        stage tracker takes over the files."""
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        if final and self.status:
            data = self.snapshot()
            data['status'] = final
            self.status.heartbeat(heartbeat_of(data))
        if self.saved is not None and isinstance(sys.stdout, _Tee):
            sys.stdout = self.saved
        if self.thread.is_alive():
            self.thread.join(timeout=5)
