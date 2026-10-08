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

Usage:
  toolkit_serve.py --data DIR [--maps DIR] [--metrics FILE] [--port 8031] [--open]
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


class Handler(SimpleHTTPRequestHandler):
    data_dir = None
    maps_dir = None
    metrics = None   # the Map metrics layer as JSON bytes, or None

    def log_message(self, fmt, *args):  # quiet: one line per request is noise here
        pass

    def send_bytes(self, body, ctype):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

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
        if len(parts) == 2 and parts[0] == 'amiwind-toolkit' and parts[1].endswith('.html'):
            return self.send_file(ROOT / 'amiwind-toolkit' / parts[1])
        if len(parts) == 3 and parts[:2] == ['resources', 'media'] and parts[2].endswith('.png'):
            return self.send_file(ROOT / 'resources' / 'media' / parts[2])
        if parts == ['data', METRICS_FILE]:
            return self.send_bytes(self.metrics, 'application/json') if self.metrics else self.send_error(404)
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


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--maps', type=Path)
    p.add_argument('--metrics', type=Path, help='Map metrics layer, or a world estimate metrics.json/.csv')
    p.add_argument('--port', type=int, default=8031)
    p.add_argument('--open', action='store_true', help='open the toolkit in your browser')
    a = p.parse_args(argv)
    Handler.data_dir = a.data.resolve()
    Handler.maps_dir = a.maps.resolve() if a.maps else None
    Handler.metrics = load_metrics(a.metrics) if a.metrics else None
    server = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    url = 'http://127.0.0.1:%d/' % a.port
    present = [n for n in DATA_FILES if (Handler.data_dir / n).is_file()]
    maps = len(list(Handler.maps_dir.glob('*.bsp'))) if Handler.maps_dir else 0
    print('AmiWind Toolkit at %s (this machine only; Ctrl+C stops)\n  data: %s\n  maps: %d' % (url, ', '.join(present) or 'none', maps), flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
