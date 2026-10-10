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

Usage:
  toolkit_serve.py [--build DIR] --data DIR [--maps DIR] [--metrics FILE] [--progress DIR|FILE] [--port 8031] [--open]
Then open http://127.0.0.1:8031/ (printed).
"""
import argparse, json, mimetypes, sys, webbrowser
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


class Handler(SimpleHTTPRequestHandler):
    reference = None   # the project's reference progress file, or None
    data_dir = None
    maps_dir = None
    metrics = None   # the Map metrics layer as JSON bytes, or None
    progress_dir = None   # the CHIM Progress Tracker folder (files are read on every request), or None

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

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path in ('/', '/index.html'):
            self.send_response(302); self.send_header('Location', '/amiwind-toolkit/index.html?served=1'); self.end_headers(); return
        parts = [p for p in path.split('/') if p]
        if any(p in ('..', '.') or '\\' in p for p in parts):
            return self.send_error(400)
        if len(parts) == 2 and parts[0] == 'amiwind-toolkit' and parts[1].endswith(('.html', '.js')):
            return self.send_file(ROOT / 'amiwind-toolkit' / parts[1])
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
            names = sorted(p.stem.lower() for p in self.maps_dir.glob('*.bsp')) if self.maps_dir else []
            return self.send_bytes(json.dumps(names).encode(), 'application/json')
        if len(parts) == 2 and parts[0] == 'maps' and parts[1].lower().endswith('.bsp') and self.maps_dir:
            return self.send_file(self.maps_dir / parts[1])
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
    p.add_argument('--port', type=int, default=8031)
    p.add_argument('--open', action='store_true', help='open the toolkit in your browser')
    a = p.parse_args(argv)
    build_progress = build_data = None
    if a.build:
        build_progress, build_data = build_folders(a.build)
        if not build_progress:
            p.error('no toolkit/cell-progress.json found under %s (build with the CHIM builder, or run cell_progress.py ingest)' % a.build)
    data = a.data or build_data
    if not data and not a.build:
        p.error('give --data DIR or --build DIR')
    Handler.reference = (a.reference or REFERENCE_DEFAULT).resolve() if (a.reference or REFERENCE_DEFAULT.is_file()) else None
    Handler.data_dir = data.resolve() if data else None
    Handler.maps_dir = a.maps.resolve() if a.maps else None
    Handler.metrics = load_metrics(a.metrics) if a.metrics else None
    Handler.progress_dir = progress_folder(a.progress or build_progress) if (a.progress or build_progress) else None
    server = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    url = 'http://127.0.0.1:%d/' % a.port
    present = [n for n in DATA_FILES if Handler.data_dir and (Handler.data_dir / n).is_file()]
    maps = len(list(Handler.maps_dir.glob('*.bsp'))) if Handler.maps_dir else 0
    print('AmiWind Toolkit at %s (this machine only; Ctrl+C stops)\n  data: %s\n  maps: %d\n  CHIM progress: %s' %
          (url, ', '.join(present) or 'none', maps, Handler.progress_dir or 'none (use Import progress in the page)'), flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
