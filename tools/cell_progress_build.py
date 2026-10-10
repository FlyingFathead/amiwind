# SPDX-License-Identifier: GPL-3.0-only
"""Track your own build: write the CHIM Progress Tracker data of a build's own CHIM world.

The builder runs it as its own stage, cell-progress, after the CHIM stage (its own fingerprint: tracker code never keys
the CHIM world; BUILD-CHIM-KEY-UNDERDECLARED-35), so a CHIM build leaves BUILD/toolkit/cell-progress.json next to the
build, ready for the Toolkit's World Map (`toolkit_serve.py --build BUILD`). It reads only the build's own files (the
CHIM world folder and, if given, your own Morrowind Data Files for the cell universe). It never raises: a tracker
problem is a warning, never a failed build (--never-fail: exit 0 then too). Turn it off with --no-cell-progress.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOOLKIT_FOLDER = 'toolkit'


def write(chim_world, out, data_files=None, label=None, now=None, results=None):
    """Ingest the CHIM world into OUT. `results` = a folder of aw-cell-result-1 files (CHIMport) to store first.
    Returns the path of OUT/cell-progress.json, or None (with a printed warning) when it could not be written."""
    try:
        import cell_progress as cp
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        if results and Path(results).is_dir():
            for f in sorted(Path(results).glob('*.json')):
                doc = cp.read_json(f)
                if doc and doc.get('format') == cp.RESULT_FORMAT:
                    cp.record_result(out, doc, now)
        census = cp.read_json(out / 'mesh-census.json')        # made once per build, reused by every live refresh
        if census is None and data_files and Path(data_files).is_dir():
            census = cp.build_census(Path(data_files), progress=lambda *a: None)
            cp.write_json(out / 'mesh-census.json', census)
        runs = ['build=%s' % chim_world] if chim_world and (Path(chim_world) / 'chim-receipt.json').is_file() else []
        cp.ingest(out, census=census, chim_runs=runs, labels={'build': label or 'this build'}, now=now)
        return out / cp.OUT_FILES['progress']
    except Exception as exc:     # noqa: BLE001 - never fail a build over the tracker
        print('WARNING: the cell progress data was not written (%s: %s); the build is unaffected' % (type(exc).__name__, exc),
              flush=True)
        return None


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True, help='the build toolkit folder (BUILD/toolkit)')
    ap.add_argument('--chim-world', type=Path, help='the CHIM world folder of the build (omit before it exists)')
    ap.add_argument('--data-files', type=Path, help='your Morrowind Data Files (the cell universe)')
    ap.add_argument('--results', type=Path, help='a folder of aw-cell-result-1 files')
    ap.add_argument('--never-fail', action='store_true',
                    help='exit 0 even when the data could not be written (the builder stage: a warning, never a failed build)')
    a = ap.parse_args(argv)
    return 0 if write(a.chim_world, a.out, a.data_files, results=a.results) or a.never_fail else 1


if __name__ == '__main__':
    sys.exit(main())
