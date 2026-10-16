#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Add a packaged build to the CHIM inclusion ledger (amiwind-toolkit/chim-inclusion.json and .js).

The world map's "Included in build" list reads this ledger: per packaged build, the cells its CHIM world holds
(each with its frame: a region frame, or a town frame for the cells inside a town frame's ownership core), the town
frames, and the evidence that the package was checked. This
tool writes one build's entry from the build's own records, so the ledger is never edited by hand:

  --chim-source   the run's chim-world/chim-source.json (frames: the cell and area of each)
  --cells         the cell list the build was given (aw-chim-cells-1); cells it lists that ended up inside a
                  town frame are recorded as partial town overlaps, not as included cells
  --archive       the packaged playtest ZIP (its SHA-256 is recorded), --readback the HDF readback JSON

An entry for the same version is replaced; builds are kept newest first.

    python3 tools/chim_inclusion.py --version v0.0.41-dev4 --state packaged --source-commit C \\
        --chim-source RUN/chim-world/chim-source.json --cells cells.json --archive PKG.zip \\
        --readback RUN/readback.json --evidence TEXT [--shipped] [--ledger amiwind-toolkit]
"""
import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'aw-chim-inclusion-1'
COVERAGE_TOTAL = 1292
COVERAGE_BASIS = 'Vvardenfell terrain cells'
REGION_FRAME = re.compile(r'rc[mp]\d+_[mp]\d+')   # a CHIM region frame's area name, e.g. rcm18_p10, rcp5_m2


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def key(cell):
    return '%d,%d' % tuple(cell)


CELL_UNITS = 8192                                   # one exterior cell in world units


def town_cells(frame):
    """The whole cells a town frame owns: those inside its frame_ownership core rectangle [x0, y0, x1, y1]."""
    core = (frame.get('frame_ownership') or {}).get('core')
    if not core:
        return []
    x0, y0, x1, y1 = (int(round(v / CELL_UNITS)) for v in core)
    return [key((x, y)) for x in range(x0, x1) for y in range(y0, y1)]


def entry(version, state, source_commit, chim_source, cells_file, archive_sha256, readback_sha256, evidence,
          shipped=False, now=None):
    """One ledger build entry from the build's records."""
    source = json.loads(Path(chim_source).read_text(encoding='utf-8'))
    frames = source.get('frames', [source])
    region = {key(f['cell']): f['town'] for f in frames if REGION_FRAME.fullmatch(str(f.get('town', '')))}
    town_frames = [f for f in frames if not REGION_FRAME.fullmatch(str(f.get('town', '')))]
    towns = sorted({f['town'] for f in town_frames})
    owned = {}                                      # town frame cells: included, attributed to the town frame
    for f in town_frames:
        for k in town_cells(f):
            if k not in region:
                owned.setdefault(k, f['town'])
    requested = {key(c) for c in json.loads(Path(cells_file).read_text(encoding='utf-8')).get('cells', [])}
    partial = sorted(requested - set(region), key=lambda k: tuple(int(v) for v in k.split(',')))
    ordered = sorted(region, key=lambda k: tuple(int(v) for v in k.split(',')))
    every = sorted(set(region) | set(owned), key=lambda k: tuple(int(v) for v in k.split(',')))
    return {
        'version': version, 'state': state,
        'cells': {k: {'state': 'included', 'frame': region.get(k) or owned[k]} for k in every},
        'generated': now or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit': source_commit, 'image_source_commit': source_commit,
        'evidence_sha256': readback_sha256, 'archive_sha256': archive_sha256,
        'evidence': evidence,
        'scope': '%d regional whole cells and %d cells inside town frames (%s). Packaging does not certify '
                 'lighting, actors, gameplay or traversal.' % (len(ordered), len(owned), ', '.join(towns) or 'none'),
        'town_frames': towns, 'partial_town_overlap_cells': partial,
        'coverage_total': COVERAGE_TOTAL, 'coverage_basis': COVERAGE_BASIS,
        'native_checked': False, 'shipped': bool(shipped), 'owner_accepted': False,
    }


def write(ledger_dir, new):
    """Replace or add the entry, newest first; write the JSON and the page's JS copy."""
    ledger_dir = Path(ledger_dir)
    path = ledger_dir / 'chim-inclusion.json'
    doc = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'format': FORMAT, 'builds': []}
    if doc.get('format') != FORMAT:
        raise ValueError('%s is not %s' % (path, FORMAT))
    builds = [b for b in doc['builds'] if b.get('version') != new['version']]
    doc['builds'] = sorted(builds + [new], key=lambda b: b.get('generated', ''), reverse=True)
    text = json.dumps(doc, indent=2) + '\n'
    path.write_text(text, encoding='utf-8', newline='\n')
    (ledger_dir / 'chim-inclusion.js').write_text('window.ChimInclusionMetadata = ' + text.rstrip('\n') + ';\n',
                                                  encoding='utf-8', newline='\n')
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--version', required=True)
    ap.add_argument('--state', choices=('packaged', 'released'), default='packaged')
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--chim-source', required=True, type=Path)
    ap.add_argument('--cells', required=True, type=Path)
    ap.add_argument('--archive', required=True, type=Path)
    ap.add_argument('--readback', required=True, type=Path)
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--shipped', action='store_true')
    ap.add_argument('--ledger', type=Path, default=ROOT / 'amiwind-toolkit')
    a = ap.parse_args(argv)
    new = entry(a.version, a.state, a.source_commit, a.chim_source, a.cells, sha256(a.archive), sha256(a.readback),
                a.evidence, a.shipped)
    doc = write(a.ledger, new)
    print('%s: %d regional cells, %d town overlaps; ledger has %s' % (
        a.version, len(new['cells']), len(new['partial_town_overlap_cells']),
        ', '.join(b['version'] for b in doc['builds'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
