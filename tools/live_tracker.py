# SPDX-License-Identifier: GPL-3.0-only
"""Live build tracker: follow a build on the Toolkit's World Map while it runs (guided builds; docs/AMIWIND_TOOLKIT.md).

Two ways, both local only and read-only on the build data:
  file    (default) no server. The builder keeps BUILD/toolkit/live/world-map.html (a static copy of the World Map) and
          BUILD/toolkit/live/cell-progress-data.js next to it. Open the page from disk; it loads the data with a script tag
          (a classic <script src> works from file:// in current browsers, unlike fetch) and re-injects that script every
          10 s, so nothing reloads and your zoom and selection stay.
  server  a small Python server (tools/toolkit_serve.py --build BUILD) bound to 127.0.0.1 only, on a free port, started
          at low priority; the page re-reads the files every 10 s. It is stopped when the build ends (or on Enter with
          --keep-tracker) and never outlives the builder.

The refresh runs in a low-priority background thread of the builder and in low-priority child processes (the cell ingest),
writes every file atomically, and any failure is one printed warning: the tracker never blocks, slows or fails a build.
"""
import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
INTERVAL = 10
STATUS_FILE = 'live-status.json'
DATA_FILE = 'cell-progress-data.js'
LIVE_FOLDER = 'live'
PAGE_FILES = ('world-map.html', 'header.js', 'chim-legend.js', 'zebra.js', 'chim-head.js')
DATA_MARKER = '<!--AW-LIVE-DATA-->'
MODES = ('file', 'server')

EXPLANATION = (
    "Live build tracker (optional)\n"
    "  Follow this build on the AmiWind Toolkit's map, cell by cell, while it runs.\n"
    "  [F]ile (default): no server. The builder keeps a small page and data file in the build folder; you open that page\n"
    "      from disk and it refreshes itself every %d seconds.\n"
    "  [S]erver: starts a small local web server on 127.0.0.1 only (this machine, read-only, stops with the build) and\n"
    "      prints an address like http://127.0.0.1:PORT/ to open in your browser.\n"
    "  Nothing leaves your computer either way. Turn this off any time with --no-live-tracker." % INTERVAL)


def choose(requested, disabled, guided, ask=input, say=print):
    """The tracker mode for this build: 'file', 'server' or None.
    requested: --live-tracker value (None, 'file' or 'server'); disabled: --no-live-tracker; guided: stdin is a terminal and
    --yes was not given. Non-guided builds only start it when asked for with the flag."""
    if disabled:
        return None
    if requested:
        return requested
    if not guided:
        return None
    say(EXPLANATION)
    try:
        answer = ask('Choose [F]ile / [S]erver / [N]o (default F): ').strip().casefold()
    except EOFError:
        return None
    if answer in ('', 'f', 'file'):
        return 'file'
    if answer in ('s', 'server'):
        return 'server'
    return None


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    os.replace(temporary, path)


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def low_priority():
    """Popen keyword arguments that start a child at low priority on this host."""
    if os.name == 'nt':
        return {'creationflags': getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0x4000)}
    return {'preexec_fn': lambda: os.nice(10)}


def stage_status(run, total):
    """The build's stage line from build-state.json: {stage, stages_done, stages_total, elapsed_s, eta_s}."""
    try:
        state = json.loads((Path(run) / 'build-state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'stage': None, 'stages_done': 0, 'stages_total': total, 'state': 'starting'}
    steps = state.get('steps', [])
    done = [s for s in steps if s.get('status') == 'passed']
    running = [s['name'] for s in steps if s.get('status') == 'running']
    spent = sum(s.get('elapsed_seconds') or 0 for s in done)
    eta = round(spent / len(done) * (total - len(done))) if done and total else None
    return {'stage': running[-1] if running else None, 'stages_done': len(done), 'stages_total': total,
            'elapsed_s': round(spent), 'eta_s': eta, 'eta_note': 'rough: mean time of the finished stages',
            'state': state.get('status', 'running')}


def page_html():
    """The World Map page for the file mode: the Toolkit's page plus the data script tag."""
    text = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')
    if DATA_MARKER not in text:
        raise ValueError('world-map.html has no %s marker' % DATA_MARKER)
    return text.replace(DATA_MARKER, '<script src="%s"></script>' % DATA_FILE)


class LiveTracker:
    """Keeps BUILD/toolkit current while the build runs and (server mode) serves it on 127.0.0.1."""

    def __init__(self, run, mode, total_stages=0, data_files=None, interval=INTERVAL, say=print):
        if mode not in MODES:
            raise ValueError('live tracker mode must be one of %s' % ', '.join(MODES))
        self.run, self.mode, self.total, self.data_files = Path(run), mode, total_stages, data_files
        self.interval, self.say = interval, say
        self.toolkit = self.run / 'toolkit'
        self.stop_event = threading.Event()
        self.thread = None
        self.server = None
        self.url = None
        self.page = None
        self._seen = None
        self._warned = False
        self._announced = False
        self.last_state = 'starting'

    # -- lifecycle ------------------------------------------------------------------------------------------------
    def start(self):
        atexit.register(self.stop)
        self.thread = threading.Thread(target=self._loop, name='live-tracker', daemon=True)
        self.thread.start()
        return self

    def stop(self, final=True):
        """Stop the refresh thread and the server. Safe to call twice; the server never outlives the builder."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=30)
        if final:
            self._tick(final=True)
        server, self.server = self.server, None
        if server is not None:
            try:
                server.terminate()
                server.wait(timeout=10)
            except Exception:       # noqa: BLE001
                try:
                    server.kill()
                except Exception:   # noqa: BLE001
                    pass

    def final_line(self):
        if self.mode == 'server' and self.url:
            return 'Track the build on the map: %s (the server stopped with the build)' % self.url
        if self.page:
            return 'Track the build on the map: open %s' % self.page.as_uri()
        return None

    # -- the refresh ----------------------------------------------------------------------------------------------
    def _loop(self):
        while not self.stop_event.is_set():
            self._tick()
            self.stop_event.wait(self.interval)

    def _warn(self, exc):
        if not self._warned:
            self._warned = True
            self.say('WARNING: the live tracker has a problem (%s: %s); the build is unaffected' % (type(exc).__name__, exc))

    def _tick(self, final=False):
        try:
            if not self.run.is_dir():
                return          # the build creates its run folder when its first stage starts
            status = stage_status(self.run, self.total)
            if final:
                status['state'] = status['state'] if status['state'] != 'running' else 'finished'
            self.last_state = status['state']
            self._ingest()
            self._publish(status)
            if not self._announced and (self.toolkit / 'cell-progress.json').is_file():
                self._announced = True
                self._announce()
        except Exception as exc:    # noqa: BLE001 - never fail a build over the tracker
            self._warn(exc)

    def _ingest(self):
        """Run the cell ingest in a low-priority child when the CHIM world changed (or once, for the empty start)."""
        world = self.run / 'chim-world'
        receipt = world / 'chim-receipt.json'
        stamp = receipt.stat().st_mtime if receipt.is_file() else None
        if self._seen is not None and stamp == self._seen:
            return
        command = [sys.executable, str(TOOLS / 'cell_progress_build.py'), '--out', str(self.toolkit)]
        if stamp is not None:
            command += ['--chim-world', str(world)]
        if self.data_files:
            command += ['--data-files', str(self.data_files)]
        done = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=900, **low_priority())
        if done.returncode == 0:
            self._seen = stamp
        else:
            raise RuntimeError('cell ingest failed: %s' % done.stderr.decode('utf-8', 'replace').strip()[-200:])

    def _publish(self, status):
        progress = self.toolkit / 'cell-progress.json'
        if not progress.is_file():
            return
        doc = json.loads(progress.read_text(encoding='utf-8'))
        head = (doc.get('headline') or {}).get('islands') or []
        status = dict(status, updated=time.strftime('%Y-%m-%d %H:%M:%S %z'), updated_epoch=round(time.time(), 1), mode=self.mode)
        if head:
            status['cells_done'], status['cells_total'] = head[0]['done'], head[0]['cells']
        atomic_write(self.toolkit / STATUS_FILE, json.dumps(status, sort_keys=True))
        if self.mode == 'file':
            live = self.toolkit / LIVE_FOLDER
            for name in PAGE_FILES:
                if name == 'world-map.html':
                    atomic_write(live / name, page_html())
                elif (ROOT / 'amiwind-toolkit' / name).is_file():
                    shutil.copyfile(ROOT / 'amiwind-toolkit' / name, live / name)
            logo = ROOT / 'resources' / 'media' / 'AmiWind_logo_name_only.png'
            if logo.is_file() and not (live / logo.name).is_file():
                shutil.copyfile(logo, live / logo.name)          # the page opened from disk finds its logo beside it
            atomic_write(live / DATA_FILE, 'window.AW_LOGO_SRC=%s;\nwindow.AW_PROGRESS=%s;\nwindow.AW_LIVE=%s;\n' % (
                json.dumps(logo.name), json.dumps(doc, separators=(',', ':')), json.dumps(status)))
            self.page = live / 'world-map.html'

    def _announce(self):
        if self.mode == 'server':
            port = free_port()
            self.server = subprocess.Popen([sys.executable, str(TOOLS / 'toolkit_serve.py'), '--build', str(self.run),
                                            '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           **low_priority())
            self.url = 'http://127.0.0.1:%d/' % port
            self.say('\n==> Track the build on the map: %s\n    A small local server on 127.0.0.1 only (this machine, read-only). '
                     'It stops when the build ends, or press Ctrl+C to cancel the build and stop it.\n' % self.url)
        else:
            self.say('\n==> Track the build on the map: open %s\n    No server: a static page that refreshes itself every %d '
                     'seconds (the Live box in the page).\n' % (self.toolkit.joinpath(LIVE_FOLDER, 'world-map.html').as_uri(),
                                                              self.interval))
            self.page = self.toolkit / LIVE_FOLDER / 'world-map.html'


def wait_for_enter(tracker, ask=input, say=print):
    """--keep-tracker: leave the server up after the build until Enter, so it is never orphaned."""
    if tracker and tracker.mode == 'server' and tracker.url:
        say('The tracker is still running at %s. Press Enter to stop it.' % tracker.url)
        try:
            ask('')
        except EOFError:
            pass
