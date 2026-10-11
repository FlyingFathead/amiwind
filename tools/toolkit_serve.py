#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Serve the AmiWind Toolkit locally with your own data preloaded.

Browsers do not let a page opened from disk read other local files, so the
toolkit normally asks you to pick each file. This tiny server, bound to this
machine only (127.0.0.1) and read-only, serves the toolkit pages plus the files
you point it at, so the World Map loads everything at once and the Local view
opens any map without picking a folder. Python standard library only.

  --data DIR   world-progress.json and the local layers (island.png/.json,
               island-world.png/.json, island-cells.json); missing ones are skipped
  --maps DIR   built maps (*.bsp), served on demand
  --metrics F  the Map metrics layer: a world-metrics.json written by
               tools/world_metrics.py, or the world estimate's metrics.json /
               metrics.csv itself (converted when the server starts); without
               it the World Map has no Map metrics layer
  --progress P the CHIM Progress Tracker: the folder tools/cell_progress.py writes
               (or its cell-progress.json). It is read again on every request, so
               running cell_progress.py after a build updates the page on reload
               without restarting the server; without it the tracker is empty
               until you use "Import progress" in the page

  --build DIR  a build folder of your own (tools/build.py run folder): its toolkit/cell-progress.json becomes
               --progress and, when the folder holds them, its world-progress.json / island files become --data,
               so `toolkit_serve.py --build BUILD` shows your own build's cell progress with nothing else to pass
  --reference F  the project's reference progress file (default: docs/chim/cell-progress-reference.json of this
               repository, if present); the World Map's Compare layer shows your cells next to it

The Monitor (amiwind-toolkit/monitor.html), read-only: follow a build as it runs.
  --builds DIR       the folder holding your build runs (tools/build.py run folders: build-progress.json, logs/)
  --monitor-docker VOLUME[:PATH]  instead of --builds: builds kept in a Docker named volume, read through a throwaway
               read-only container (tools/build_docker.py and tools/run_docker.py write their runs to the volume
               amiwind-docker-builds under build/, which is the default PATH); --monitor-image picks the image that
               runs the reader (default amiwind-builder:local, the image tools/build_docker.py builds)
  --builds-command C instead of --builds: a command (your own, given here) that runs tools/monitor_read.py --serve
               where the builds are, for example in a read-only container that can see a build volume; the server
               sends it one JSON request per line (only the requests monitor_read.py knows) and never builds a
               command from what a page asks
  --results DIR      master builder results (aw-result-1 JSON files) shown as recent builds and gates
  --console-logs DIR master builder console logs (<run>.console.log), followed like a stage log
  --bind ADDRESS     the address to listen on (default 127.0.0.1: this machine only). Another address, such as this
               machine's LAN address, lets a phone on your network open the Toolkit; anyone on that network can then
               read what the server serves (the Toolkit, your data, your build logs), so only do it on a network you trust

Mesh Compare (amiwind-toolkit/mesh-compare.html), read-only: two .OBJ files side by side.
  --mesh-cache DIR   a folder of mesh exports (tools/mesh_export.py --out DIR): the page lists them and opens two
  --mesh-data-files DIR  your own Morrowind Data Files: the page can then export a mesh by name into --mesh-cache
               (tools/mesh_export.py, the builder's own code path; needs numpy in this Python), or, with
               --mesh-docker IMAGE, in a throwaway container of that image (no network, Data Files read-only)

Usage:
  toolkit_serve.py [--builds DIR | --monitor-docker VOLUME[:PATH] | --builds-command C] [--results DIR] [--console-logs DIR]
  toolkit_serve.py [--build DIR] --data DIR [--maps DIR] [--metrics FILE] [--progress DIR|FILE] [--port 8031] [--open]
Then open http://127.0.0.1:8031/ (printed).
"""
import argparse, json, mimetypes, queue, re, shlex, subprocess, sys, threading, time, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
DATA_FILES = ('world-progress.json', 'island.png', 'island.json', 'island-world.png', 'island-world.json',
              'island-cells.json')
METRICS_FILE = 'world-metrics.json'   # served from --metrics, never from the data folder
# The CHIM Progress Tracker files, served from --progress under these names (the progress folder's own file names).
PROGRESS_FILES = {'cell-progress.json': 'application/json', 'cell-progress-next.json': 'application/json',
                  'cell-progress-curve.json': 'application/json', 'cell-progress-curve.png': 'image/png'}
PROGRESS_SOURCES = {'live-status.json': 'live-status.json', 'cell-progress.json': 'cell-progress.json', 'cell-progress-next.json': 'next.json',
                    'cell-progress-curve.json': 'mesh-curve.json', 'cell-progress-curve.png': 'mesh-curve.png'}


REFERENCE_FILE = 'cell-progress-reference.json'
REFERENCE_DEFAULT = ROOT / 'docs' / 'chim' / REFERENCE_FILE


def build_folders(build):
    """(progress folder, data folder) of a build folder: toolkit/ (or the folder itself) with cell-progress.json, and the
    folder that holds the world-progress layers; either may be None."""
    build = Path(build).resolve()
    progress = next((c for c in (build / 'toolkit', build, *sorted(build.glob('*/toolkit')), *sorted(build.glob('*/*/toolkit')))
                     if (c / 'cell-progress.json').is_file()), None)
    data = next((c for c in (build, build / 'toolkit', *sorted(build.glob('*/toolkit'))) if (c / 'world-progress.json').is_file()), None)
    return progress, data


class LocalBuilds:
    """The Monitor's build source for a local folder: tools/monitor_read.py in this process."""

    def __init__(self, root):
        import monitor_read
        self.reader = monitor_read.Reader(root)

    def ask(self, request):
        return self.reader.answer(request)


class CommandBuilds:
    """The Monitor's build source through a command that runs `monitor_read.py --serve` (one JSON request per line in,
    one answer per line out). The command is the operator's own (--builds-command); requests are JSON documents built
    by this server from checked values and are never part of a command line."""

    def __init__(self, argv, timeout=20.0):
        self.argv = list(argv)
        self.timeout = timeout
        self.lock = threading.Lock()
        self.proc = None
        self.lines = None

    def _start(self):
        self.proc = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding='utf-8', bufsize=1)
        self.lines = queue.Queue()
        proc, lines = self.proc, self.lines

        def pump():
            for line in proc.stdout:
                lines.put(line)
            lines.put(None)
        threading.Thread(target=pump, daemon=True).start()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def ask(self, request):
        with self.lock:
            for attempt in (1, 2):
                if self.proc is None or self.proc.poll() is not None:
                    self._start()
                try:
                    self.proc.stdin.write(json.dumps(request, separators=(',', ':')) + '\n')
                    self.proc.stdin.flush()
                    line = self.lines.get(timeout=self.timeout)
                except (OSError, queue.Empty):
                    line = None
                if line:
                    try:
                        return json.loads(line)
                    except ValueError:
                        pass
                self.stop()
                self.proc = None
            return {'ok': False, 'error': 'the build source did not answer'}


class Cached:
    """Answers kept briefly, so several pages polling every second or two cost one read."""

    def __init__(self, source, ttl=1.0):
        self.source, self.ttl, self.memo, self.lock = source, ttl, {}, threading.Lock()

    def ask(self, request):
        key = json.dumps(request, sort_keys=True)
        now = time.monotonic()
        with self.lock:
            hit = self.memo.get(key)
            if hit and now - hit[0] < self.ttl:
                return hit[1]
        answer = self.source.ask(request)
        with self.lock:
            if len(self.memo) > 500:
                self.memo.clear()
            self.memo[key] = (now, answer)
        return answer


DOCKER_VOLUME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
DOCKER_PATH = re.compile(r'^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$')
DOCKER_IMAGE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/:@-]{0,254}$')
DOCKER_DEFAULT_PATH = 'build'          # tools/build_docker.py and run_docker.py: /work/build/<run> in the volume
DOCKER_DEFAULT_IMAGE = 'amiwind-builder:local'


def docker_monitor_command(spec, image=DOCKER_DEFAULT_IMAGE, docker='docker', reader=None, name=None):
    """The fixed command of --monitor-docker VOLUME[:PATH]: a throwaway container that can only read (volume mounted
    read-only, read-only root, no network, no capabilities, unprivileged user, half a core) and runs
    tools/monitor_read.py --serve on VOLUME/PATH. Built once, when the server starts, from the operator's own options;
    a page never adds anything to it."""
    volume, _, path = spec.partition(':')
    path = (path or DOCKER_DEFAULT_PATH).strip('/')
    if not DOCKER_VOLUME.match(volume):
        raise ValueError('--monitor-docker: VOLUME must be a simple Docker volume name')
    if not DOCKER_PATH.match(path) or any(part in ('.', '..') for part in path.split('/')):
        raise ValueError('--monitor-docker: PATH must be a plain relative path inside the volume')
    if not DOCKER_IMAGE.match(image):
        raise ValueError('--monitor-image: not a Docker image name')
    reader = Path(reader or Path(__file__).resolve().parent / 'monitor_read.py').resolve()
    if ',' in str(reader) or not reader.is_file():
        raise ValueError('--monitor-docker: the reader %s is missing or its path has a comma' % reader)
    if name is not None and not DOCKER_VOLUME.match(name):
        raise ValueError('not a container name')
    return [docker, 'run', '-i', '--rm', '--pull', 'never', '--network', 'none', '--read-only',
            *(['--name', name] if name else []),
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '65534:65534',
            '--cpus', '0.5', '--memory', '256m',
            '--mount', 'type=volume,source=%s,target=/vol,readonly' % volume,
            '--mount', 'type=bind,source=%s,target=/amiwind-monitor/monitor_read.py,readonly' % reader,
            image, 'python3', '-I', '/amiwind-monitor/monitor_read.py', '--root', 'builds=/vol/' + path, '--serve']


RESULT_FIELDS = ('run_name', 'kind', 'status', 'gate', 'commit', 'version', 'started', 'finished', 'seconds',
                 'reason', 'requester', 'failed_steps', 'dry_run')
RESULT_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*\.json$')


def recent_results(folder, limit=30):
    """The newest master builder results (aw-result-1), a few fields each."""
    out = []
    try:
        files = [f for f in Path(folder).iterdir() if RESULT_NAME.match(f.name) and f.is_file() and not f.is_symlink()]
    except OSError:
        return out
    for f in sorted(files, key=lambda f: -f.stat().st_mtime)[:limit]:
        try:
            if f.stat().st_size > 2 * 1024 * 1024:
                continue
            d = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and d.get('schema') == 'aw-result-1':
            row = {k: d.get(k) for k in RESULT_FIELDS}
            numbers = d.get('numbers') if isinstance(d.get('numbers'), dict) else {}
            row['numbers'] = {k: v for k, v in numbers.items() if isinstance(v, (int, float, str)) and len(str(v)) < 80}
            out.append(row)
    return out


def check_bind(address):
    """The listen address: this machine only (127.0.0.1, the default) or one address of this machine chosen on purpose
    (for example its LAN address, to reach the Toolkit from a phone). Every-interface addresses are refused: listening
    beyond this machine is always one named address."""
    import ipaddress
    if address == 'localhost':
        return '127.0.0.1'
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        raise ValueError('--bind takes an IP address of this machine (default 127.0.0.1)')
    if ip.is_unspecified or ip.is_multicast:
        raise ValueError('--bind refuses an every-interface address: name the one address to listen on')
    return str(ip)


MESH_FILE = re.compile(r'^[a-z0-9_][a-z0-9_.+-]{0,200}\.(obj|mtl)$')
MESH_RECORD = '.export.json'


def mesh_exports(folder):
    """The mesh exports in a --mesh-cache folder: one row per .OBJ (from each export record), newest first."""
    rows = []
    try:
        records = [f for f in Path(folder).iterdir() if f.name.endswith(MESH_RECORD) and f.is_file() and not f.is_symlink()]
    except OSError:
        return rows
    for f in sorted(records, key=lambda f: (-f.stat().st_mtime, f.name)):
        try:
            d = json.loads(f.read_text(encoding='utf-8')) if f.stat().st_size < 1024 * 1024 else {}
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or d.get('format') != 'amiwind-mesh-export-1':
            continue
        space = (d.get('profile') or {}).get('space') if isinstance(d.get('profile'), dict) else None
        for r in d.get('files') or []:
            if isinstance(r, dict) and MESH_FILE.match(str(r.get('file', ''))) and '..' not in r['file']:
                rows.append(dict({k: r.get(k) for k in ('source', 'method', 'file', 'faces', 'vertices', 'sha256')},
                                 space=space if isinstance(space, str) else None))
    return rows


class MeshExporter:
    """Exports a mesh into the --mesh-cache folder on request, one at a time, through tools/mesh_export.py: in this
    Python, or in a throwaway container (--mesh-docker IMAGE: no network, read-only root and Data Files, no
    capabilities). The command is fixed when the server starts; a page only names a mesh and methods, both checked."""

    def __init__(self, data_files, cache, image=None, docker='docker', name=None):
        self.data, self.cache, self.image, self.docker, self.name = Path(data_files), Path(cache), image, docker, name
        self.lock = threading.Lock()
        if image is not None and not DOCKER_IMAGE.match(image):
            raise ValueError('--mesh-docker: not a Docker image name')
        if name is not None and not DOCKER_VOLUME.match(name):
            raise ValueError('not a container name')
        if image is not None and any(',' in str(Path(x).resolve()) for x in (ROOT, self.data, self.cache)):
            raise ValueError('--mesh-docker: the repository, Data Files and cache paths must not contain a comma')

    def methods(self):
        import mesh_export
        return list(mesh_export.available_methods())     # what this checkout (also the container's /src) has

    def command(self, mesh, methods):
        return [self.docker, 'run', '--rm', '--pull', 'never', '--network', 'none', '--read-only',
                *(['--name', self.name] if self.name else []),
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '1000:1000',
                '--cpus', '2', '--memory', '4g', '-e', 'PYTHONDONTWRITEBYTECODE=1',
                '--mount', 'type=bind,source=%s,target=/src,readonly' % ROOT,
                '--mount', 'type=bind,source=%s,target=/data,readonly' % self.data.resolve(),
                '--mount', 'type=bind,source=%s,target=/out' % self.cache.resolve(),
                '-w', '/src', self.image, 'python3', '-I', '/src/tools/mesh_export.py', mesh,
                '--data-files', '/data', '--methods', ','.join(methods), '--out', '/out']

    def export(self, mesh, methods):
        import mesh_export
        mesh = mesh_export.check_mesh(mesh)
        known = mesh_export.available_methods()
        if not methods or any(m not in known for m in methods) or len(set(methods)) != len(methods):
            raise ValueError('methods: some of ' + ', '.join(known))
        with self.lock:
            record = self.cache / (mesh_export.file_stem(mesh, 'x')[:-2] + MESH_RECORD)
            try:
                old = json.loads(record.read_text(encoding='utf-8'))
                if {r['method'] for r in old.get('files', [])} >= set(methods):
                    return old                                 # exported already: the cache answers
            except (OSError, ValueError, KeyError, TypeError):
                pass
            self.cache.mkdir(parents=True, exist_ok=True)
            if self.image:
                out = subprocess.run(self.command(mesh, methods), capture_output=True, text=True, timeout=600)
                if out.returncode:
                    last = (out.stderr or out.stdout).strip().splitlines()[-1:]
                    if any('FileNotFoundError' in line for line in last):
                        raise FileNotFoundError(mesh)
                    raise RuntimeError(last[0] if last else 'export failed')
                return json.loads(record.read_text(encoding='utf-8'))
            return mesh_export.export_mesh(self.data, mesh, methods, self.cache)


def int_param(query, name, default, lo, hi):
    """An integer query parameter (digits and an optional minus only), clamped to [lo, hi]."""
    from urllib.parse import parse_qs
    values = parse_qs(query).get(name)
    if not values:
        return default
    v = values[0]
    if not re.fullmatch(r'-?[0-9]{1,15}', v):
        raise ValueError('bad ' + name)
    return max(lo, min(hi, int(v)))


class Handler(SimpleHTTPRequestHandler):
    reference = None   # the project's reference progress file, or None
    data_dir = None
    maps_dir = None
    metrics = None   # the Map metrics layer as JSON bytes, or None
    progress_dir = None   # the CHIM Progress Tracker folder (files are read on every request), or None
    builds = None   # the Monitor's build source (LocalBuilds or CommandBuilds, cached), or None
    results_dir = None   # master builder results for the Monitor, or None
    console_dir = None   # master builder console logs for the Monitor, or None
    mesh_cache = None   # Mesh Compare: the folder of mesh exports, or None
    mesh_exporter = None   # Mesh Compare: a MeshExporter when --mesh-data-files is given, or None

    def log_message(self, fmt, *args):  # quiet: one line per request is noise here
        pass

    def send_bytes(self, body, ctype):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_nothing(self):
        self.send_response(204)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()

    def send_file(self, path):
        if not path.is_file():
            return self.send_error(404)
        self.send_bytes(path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream')

    def send_json(self, doc, status=200):
        body = json.dumps(doc, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def monitor(self, parts, query):
        """The Monitor's read-only endpoints (GET only): /monitor/config.json, runs.json, results.json,
        run/<run>/{progress,state,timeline,files}.json, run/<run>/log/<name>?offset=&max=, run/<run>/trace/<name>?offset=&max=
        (a stage's read/write trace), run/<run>/sections/<NN-stage>.json (a stage's sections), console/<run>?offset=&max=."""
        import monitor_read
        try:
            offset = int_param(query, 'offset', -1, -(1 << 62), 1 << 62)
            most = int_param(query, 'max', monitor_read.MAX_READ, 1, monitor_read.MAX_READ)
        except ValueError:
            return self.send_json({'ok': False, 'error': 'bad query'}, 400)
        if parts == ['config.json']:
            return self.send_json({'ok': True, 'builds': self.builds is not None, 'results': self.results_dir is not None,
                                   'console': self.console_dir is not None})
        if parts == ['results.json']:
            return self.send_json({'ok': True, 'results': recent_results(self.results_dir) if self.results_dir else []})
        if len(parts) == 2 and parts[0] == 'console':
            if not self.console_dir:
                return self.send_json({'ok': False, 'error': 'no console logs (start the server with --console-logs)'}, 404)
            try:
                monitor_read.check_name(parts[1], what='run')
                return self.send_json(dict(monitor_read.tail_file(self.console_dir, parts[1] + '.console.log', offset, most),
                                           ok=True))
            except (monitor_read.Refused, OSError) as e:
                return self.send_json({'ok': False, 'error': str(e) if isinstance(e, monitor_read.Refused) else 'unreadable'}, 404)
        if self.builds is None:
            return self.send_json({'ok': False, 'error': 'no build source (start the server with --builds or --builds-command)'}, 404)
        request = None
        if parts == ['runs.json']:
            request = {'op': 'runs'}
        elif len(parts) == 3 and parts[0] == 'run' and parts[2] in ('progress.json', 'state.json', 'timeline.json', 'files.json'):
            request = {'op': parts[2][:-5], 'run': parts[1]}
        elif len(parts) == 4 and parts[0] == 'run' and parts[2] == 'sections' and parts[3].endswith('.json'):
            request = {'op': 'sections', 'run': parts[1], 'stage': parts[3][:-5]}
        elif len(parts) == 4 and parts[0] == 'run' and parts[2] in ('log', 'trace'):
            request = {'op': parts[2], 'run': parts[1], 'name': parts[3], 'offset': offset, 'max': most}
        if request is None:
            return self.send_json({'ok': False, 'error': 'unknown'}, 404)
        # names are checked here as well as by the reader, so nothing unchecked reaches a build source
        try:
            if 'stage' in request:
                monitor_read.check_name(request['stage'], monitor_read.STAGE_NAME, 'stage')
            for k in ('run', 'name'):
                if k in request:
                    monitor_read.check_name(request[k], monitor_read.NAME if k == 'run' else
                                            monitor_read.TRACE_NAME if request['op'] == 'trace' else monitor_read.LOG_NAME, k)
        except monitor_read.Refused as e:
            return self.send_json({'ok': False, 'error': str(e)}, 400)
        answer = self.builds.ask(request)
        return self.send_json(answer, 200 if answer.get('ok') else 404)

    def mesh(self, parts, query):
        """Mesh Compare's endpoints (GET only): /mesh/config.json, /mesh/list.json, /mesh/file/<name>.obj|.mtl (a file of
        the cache, by its plain name), /mesh/export.json?mesh=meshes/...nif&methods=original,current (export it first
        when --mesh-data-files is given; the cache answers when it was exported already)."""
        from urllib.parse import parse_qs
        if parts == ['config.json']:
            ex = self.mesh_exporter
            try:
                methods = ex.methods() if ex else []
            except ImportError:
                methods = []
            return self.send_json({'ok': True, 'cache': bool(self.mesh_cache), 'export': bool(ex) and bool(methods),
                                   'methods': methods})
        if not self.mesh_cache:
            return self.send_json({'ok': False, 'error': 'no mesh cache (start the server with --mesh-cache DIR)'}, 404)
        if parts == ['list.json']:
            return self.send_json({'ok': True, 'files': mesh_exports(self.mesh_cache)})
        if len(parts) == 2 and parts[0] == 'file' and MESH_FILE.match(parts[1]) and '..' not in parts[1]:
            f = self.mesh_cache / parts[1]
            if f.is_symlink() or not f.is_file():
                return self.send_error(404)
            return self.send_bytes(f.read_bytes(), 'text/plain; charset=utf-8')
        if parts == ['export.json']:
            if not self.mesh_exporter:
                return self.send_json({'ok': False, 'error': 'export is off (start the server with --mesh-data-files DIR)'}, 404)
            q = parse_qs(query)
            mesh = (q.get('mesh') or [''])[0]
            methods = [m for m in (q.get('methods') or ['original,current'])[0].split(',') if m]
            try:
                record = self.mesh_exporter.export(mesh, methods)
            except ValueError as e:
                return self.send_json({'ok': False, 'error': str(e)}, 400)
            except FileNotFoundError:
                return self.send_json({'ok': False, 'error': 'no such mesh in your Data Files'}, 404)
            except Exception as e:                              # a broken mesh: say so, keep serving
                return self.send_json({'ok': False, 'error': 'export failed: %s' % (e,)}, 500)
            return self.send_json({'ok': True, 'record': record})
        return self.send_error(404)

    def do_GET(self):
        split = urlsplit(self.path)
        path = unquote(split.path)
        if path in ('/', '/index.html'):
            self.send_response(302); self.send_header('Location', '/amiwind-toolkit/index.html?served=1'); self.end_headers(); return
        parts = [p for p in path.split('/') if p]
        if any(p in ('..', '.') or '\\' in p for p in parts):
            return self.send_error(400)
        if parts and parts[0] == 'monitor':
            return self.monitor(parts[1:], split.query)
        if parts and parts[0] == 'mesh':
            return self.mesh(parts[1:], split.query)
        if len(parts) == 2 and parts[0] == 'amiwind-toolkit' and parts[1].endswith(('.html', '.js')):
            return self.send_file(ROOT / 'amiwind-toolkit' / parts[1])
        if parts == ['docs', 'chim', 'CHIM_PROGRESS_MAP.md']:      # the legend's "what do these colours mean?" guide, shown as text
            p = ROOT / 'docs' / 'chim' / 'CHIM_PROGRESS_MAP.md'
            return self.send_bytes(p.read_bytes(), 'text/plain; charset=utf-8') if p.is_file() else self.send_error(404)
        if len(parts) == 3 and parts[:2] == ['resources', 'media'] and parts[2].endswith('.png'):
            return self.send_file(ROOT / 'resources' / 'media' / parts[2])
        if parts == ['data', METRICS_FILE]:
            return self.send_bytes(self.metrics, 'application/json') if self.metrics else self.send_error(404)
        if len(parts) == 2 and parts[0] == 'data' and parts[1] in PROGRESS_FILES:
            f = self.progress_dir / PROGRESS_SOURCES[parts[1]] if self.progress_dir else None
            return self.send_bytes(f.read_bytes(), PROGRESS_FILES[parts[1]]) if f and f.is_file() else self.send_error(404)
        # Optional files answer 204 (nothing) when absent, so the browser console shows no 404 for them.
        if parts == ['data', REFERENCE_FILE]:
            return self.send_file(self.reference) if self.reference else self.send_nothing()
        if parts == ['data', 'live-status.json']:
            f = self.progress_dir / PROGRESS_SOURCES['live-status.json'] if self.progress_dir else None
            return self.send_bytes(f.read_bytes(), 'application/json') if f and f.is_file() else self.send_nothing()
        if len(parts) == 2 and parts[0] == 'data' and parts[1] in DATA_FILES and self.data_dir:
            return self.send_file(self.data_dir / parts[1])
        if parts == ['maps', 'index.json']:
            # x.bsp and the CHIM frame maps x.chim (tools/map_files.py): one name each
            from map_files import map_files
            names = sorted({p.stem.lower() for p in map_files(self.maps_dir)}) if self.maps_dir else []
            return self.send_bytes(json.dumps(names).encode(), 'application/json')
        from map_files import is_map_name
        if len(parts) == 2 and parts[0] == 'maps' and is_map_name(parts[1]) and self.maps_dir:
            # a map by name, resolved as the engine does (a frame map's .chim when there is one)
            from map_files import map_file, map_stem
            return self.send_file(map_file(self.maps_dir, map_stem(parts[1])))
        self.send_error(404)


def load_metrics(path):
    """The Map metrics layer as bytes: a layer file as is, a metrics table converted."""
    import world_metrics
    return world_metrics.dumps(world_metrics.load_any(path)).encode('utf-8')


def progress_folder(path):
    """The tracker folder for --progress: a folder, or the cell-progress.json inside it."""
    path = path.resolve()
    return path.parent if path.is_file() else path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data', type=Path)
    p.add_argument('--build', type=Path, help='your own build folder: loads its toolkit/cell-progress.json (and layers)')
    p.add_argument('--reference', type=Path, help='the project reference progress file (default: the repository copy)')
    p.add_argument('--maps', type=Path)
    p.add_argument('--metrics', type=Path, help='Map metrics layer, or a world estimate metrics.json/.csv')
    p.add_argument('--progress', type=Path, help='CHIM Progress Tracker folder (tools/cell_progress.py --out) or its cell-progress.json')
    p.add_argument('--builds', type=Path, help='Monitor: the folder holding your build runs')
    p.add_argument('--monitor-docker', metavar='VOLUME[:PATH]',
                   help='Monitor: builds in a Docker volume (default PATH build), read by a read-only container')
    p.add_argument('--monitor-image', default=DOCKER_DEFAULT_IMAGE, help='Monitor: the image that runs the reader')
    p.add_argument('--docker', default='docker', help='Monitor: the docker executable')
    p.add_argument('--builds-command', help='Monitor: a command that runs tools/monitor_read.py --serve where the builds are')
    p.add_argument('--bind', default='127.0.0.1', help='listen address (default 127.0.0.1, this machine only)')
    p.add_argument('--results', type=Path, help='Monitor: master builder results (aw-result-1 JSON)')
    p.add_argument('--console-logs', type=Path, help='Monitor: master builder console logs (<run>.console.log)')
    p.add_argument('--mesh-cache', type=Path, help='Mesh Compare: a folder of mesh exports (tools/mesh_export.py --out)')
    p.add_argument('--mesh-data-files', type=Path, help='Mesh Compare: your own Data Files, to export meshes into --mesh-cache')
    p.add_argument('--mesh-docker', metavar='IMAGE', help='Mesh Compare: export in a throwaway container of this image')
    p.add_argument('--port', type=int, default=8031)
    p.add_argument('--open', action='store_true', help='open the toolkit in your browser')
    a = p.parse_args(argv)
    build_progress = build_data = None
    if a.build:
        build_progress, build_data = build_folders(a.build)
        if not build_progress:
            p.error('no toolkit/cell-progress.json found under %s (build with the CHIM builder, or run cell_progress.py ingest)' % a.build)
    data = a.data or build_data
    monitor = a.builds or a.builds_command or a.monitor_docker or a.results or a.console_logs
    if not data and not a.build and not monitor and not a.mesh_cache:
        p.error('give --data DIR or --build DIR (or the Monitor options --builds / --builds-command, or --mesh-cache DIR)')
    if (a.mesh_data_files or a.mesh_docker) and not a.mesh_cache:
        p.error('--mesh-data-files and --mesh-docker need --mesh-cache DIR (where the exports go)')
    if a.mesh_docker and not a.mesh_data_files:
        p.error('--mesh-docker needs --mesh-data-files DIR')
    Handler.mesh_cache = a.mesh_cache.resolve() if a.mesh_cache else None
    if a.mesh_data_files:
        if not a.mesh_data_files.is_dir():
            p.error('--mesh-data-files: no such folder')
        try:
            Handler.mesh_exporter = MeshExporter(a.mesh_data_files, a.mesh_cache, a.mesh_docker, a.docker,
                                                 name='aw-toolkit-mesh-export-%d' % a.port if a.mesh_docker else None)
        except ValueError as e:
            p.error(str(e))
    if sum(bool(x) for x in (a.builds, a.builds_command, a.monitor_docker)) > 1:
        p.error('give one of --builds, --monitor-docker or --builds-command')
    if a.monitor_docker:
        try:
            Handler.builds = Cached(CommandBuilds(docker_monitor_command(a.monitor_docker, a.monitor_image, a.docker,
                                                                         name='amiwind-toolkit-monitor-%d' % a.port)))
        except ValueError as e:
            p.error(str(e))
    elif a.builds:
        Handler.builds = Cached(LocalBuilds(a.builds.resolve()))
    elif a.builds_command:
        Handler.builds = Cached(CommandBuilds(shlex.split(a.builds_command, posix=True)))
    Handler.results_dir = a.results.resolve() if a.results else None
    Handler.console_dir = a.console_logs.resolve() if a.console_logs else None
    Handler.reference = (a.reference or REFERENCE_DEFAULT).resolve() if (a.reference or REFERENCE_DEFAULT.is_file()) else None
    Handler.data_dir = data.resolve() if data else None
    Handler.maps_dir = a.maps.resolve() if a.maps else None
    Handler.metrics = load_metrics(a.metrics) if a.metrics else None
    Handler.progress_dir = progress_folder(a.progress or build_progress) if (a.progress or build_progress) else None
    try:
        bind = check_bind(a.bind)
    except ValueError as e:
        p.error(str(e))
    server = ThreadingHTTPServer((bind, a.port), Handler)
    url = 'http://%s:%d/' % ('[%s]' % bind if ':' in bind else bind, a.port)
    if bind not in ('127.0.0.1', '::1'):
        print('WARNING: listening on %s, not only on this machine: anyone who can reach it on your network can read the '
              'Toolkit, your data and your build logs. Use this only on a network you trust.' % a.bind, flush=True)
    present = [n for n in DATA_FILES if Handler.data_dir and (Handler.data_dir / n).is_file()]
    from map_files import map_files
    maps = len(map_files(Handler.maps_dir)) if Handler.maps_dir else 0
    print('AmiWind Toolkit at %s (this machine only; Ctrl+C stops)\n  data: %s\n  maps: %d\n  CHIM progress: %s' %
          (url, ', '.join(present) or 'none', maps, Handler.progress_dir or 'none (use Import progress in the page)'), flush=True)
    if monitor:
        print('  Monitor (read-only): %samiwind-toolkit/monitor.html  builds: %s' %
              (url, 'a command' if a.builds_command else ('Docker volume ' + a.monitor_docker) if a.monitor_docker
               else (a.builds or 'none')), flush=True)
    if Handler.mesh_cache:
        print('  Mesh Compare: %samiwind-toolkit/mesh-compare.html  exports: %s%s' %
              (url, Handler.mesh_cache, ' (export on request%s)' % (' in a container' if a.mesh_docker else '')
               if Handler.mesh_exporter else ''), flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if isinstance(Handler.builds, Cached) and isinstance(Handler.builds.source, CommandBuilds):
            Handler.builds.source.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
