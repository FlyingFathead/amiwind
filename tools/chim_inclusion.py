#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM inclusion ledger (amiwind-toolkit/chim-inclusion.json and .js): what each build's CHIM world holds.

The world map's "Included in build" list reads this ledger: per build, the cells its CHIM world holds (each with its
frame: a region frame, or a town frame for the cells inside a town frame's ownership core), the town frames, and the
evidence that the build was checked. Every entry is written from the build's own records, never by hand, in three
states:

  built      the builder writes it at the end of every build with a CHIM world (tools/build.py, inclusion_step) into
             the run's own toolkit/chim-inclusion.json/.js: the repository ledger with this run's entry on top, so the
             run's World map (and `toolkit_serve.py --build RUN` / `--builds`) shows the build it belongs to. No
             archive or readback yet.
  packaged   `chim_inclusion.py package --run RUN --archive ZIP --readback FILE --evidence TEXT`: the run's entry in
             its toolkit copy gains the playtest ZIP's and the readback's SHA-256 (both required).
  released   `chim_inclusion.py release --run RUN`: the run's packaged entry goes into the repository ledger as the
             release. Only this step changes the repository ledger; tools/release.py refuses to cut the public source
             of a release (rc or final) whose version the repository ledger lacks (`chim_inclusion.py check-release`).

The records an entry reads:
  chim-world/chim-source.json   frames: the cell and area of each
  the cell list the build was given (aw-chim-cells-1 JSON, or the builder's encoded --chim-regions-cells text);
  cells it lists that ended up inside a town frame are recorded as partial town overlaps, not as included cells

An entry for the same version and run is replaced; builds are kept newest first.

The flag form writes one packaged or released entry straight into a ledger (as before; --archive, --readback and
--evidence required; the repository ledger holds no built entries, those stay in their run):

    python3 tools/chim_inclusion.py --version v0.0.41-dev4 --state packaged --source-commit C \\
        --chim-source RUN/chim-world/chim-source.json --cells cells.json --archive PKG.zip \\
        --readback RUN/readback.json --evidence TEXT [--shipped] [--ledger amiwind-toolkit]
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'aw-chim-inclusion-1'
LEDGER = ROOT / 'amiwind-toolkit'
LEDGER_FILE = 'chim-inclusion.json'
SCRIPT_FILE = 'chim-inclusion.js'
SCRIPT_PREFIX = 'window.ChimInclusionMetadata = '
TOOLKIT_FOLDER = 'toolkit'                          # the run's toolkit folder (tools/cell_progress_build.py)
STATES = ('built', 'packaged', 'released')
EVIDENCE_STATES = ('packaged', 'released')          # these need the archive, the readback and the evidence text
COVERAGE_TOTAL = 1292
COVERAGE_BASIS = 'Vvardenfell terrain cells'
REGION_FRAME = re.compile(r'rc[mp]\d+_[mp]\d+')   # a CHIM region frame's area name, e.g. rcm18_p10, rcp5_m2
SHA256 = re.compile(r'[0-9a-f]{64}')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def text_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def key(cell):
    return '%d,%d' % tuple(cell)


def cell_order(k):
    return tuple(int(v) for v in k.split(','))


CELL_UNITS = 8192                                   # one exterior cell in world units


def town_cells(frame):
    """The whole cells a town frame owns: those inside its frame_ownership core rectangle [x0, y0, x1, y1]."""
    core = (frame.get('frame_ownership') or {}).get('core')
    if not core:
        return []
    x0, y0, x1, y1 = (int(round(v / CELL_UNITS)) for v in core)
    return [key((x, y)) for x in range(x0, x1) for y in range(y0, y1)]


def requested_cells(cells_file=None, cells_text=None):
    """The cells the build was given: an aw-chim-cells-1 JSON file (or a list of [x, y]) and/or the builder's encoded
    --chim-regions-cells text ("x,y:k ..."). Neither = none (a build of towns only)."""
    out = set()
    if isinstance(cells_file, (list, tuple)):
        out |= {key(c) for c in cells_file}
    elif cells_file:
        out |= {key(c) for c in json.loads(Path(cells_file).read_text(encoding='utf-8')).get('cells', [])}
    for token in (cells_text or '').split():
        out.add(key(int(v) for v in token.partition(':')[0].split(',')))
    return out


def scope_text(e):
    regional = sum(1 for c in e['cells'].values() if REGION_FRAME.fullmatch(str(c.get('frame', ''))))
    text = '%d regional whole cells and %d cells inside town frames (%s).' % (
        regional, len(e['cells']) - regional, ', '.join(e['town_frames']) or 'none')
    if e['state'] == 'built':
        return text + ' Built, not packaged yet: no archive or readback. Building does not certify lighting, actors, ' \
                      'gameplay or traversal.'
    return text + ' Packaging does not certify lighting, actors, gameplay or traversal.'


def with_evidence(e, state, archive_sha256=None, readback_sha256=None, evidence=None, shipped=False):
    """E in STATE with its evidence: the one place the states are checked. built takes no archive or readback (they do
    not exist yet); packaged and released need all three (the archive's and the readback's SHA-256, the evidence text)."""
    if state not in STATES:
        raise ValueError('inclusion state must be one of %s, not %r' % (', '.join(STATES), state))
    if state in EVIDENCE_STATES:
        missing = [name for name, value in (('archive', archive_sha256), ('readback', readback_sha256),
                                            ('evidence', evidence)) if not value]
        if missing:
            raise ValueError('a %s inclusion entry needs its %s' % (state, ', '.join(missing)))
        bad = [name for name, value in (('archive', archive_sha256), ('readback', readback_sha256))
               if not SHA256.fullmatch(value)]
        if bad:
            raise ValueError('a %s inclusion entry needs SHA-256 digests (64 hex digits) for %s' % (state, ', '.join(bad)))
    elif archive_sha256 or readback_sha256:
        raise ValueError('a built inclusion entry has no archive or readback yet (package it first)')
    out = dict(e, state=state, archive_sha256=archive_sha256, evidence_sha256=readback_sha256,
               evidence=evidence or ('built by run %s; not packaged yet' % (e.get('run') or e.get('version'))),
               shipped=bool(shipped))
    out['scope'] = scope_text(out)
    return out


def entry(version, state, source_commit, chim_source, cells_file, archive_sha256=None, readback_sha256=None,
          evidence=None, shipped=False, now=None, run=None, cells_text=None):
    """One ledger build entry from the build's records (see with_evidence for what each state needs)."""
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
    requested = requested_cells(cells_file, cells_text)
    partial = sorted(requested - set(region), key=cell_order)
    every = sorted(set(region) | set(owned), key=cell_order)
    e = {
        'version': version, 'state': state,
        'cells': {k: {'state': 'included', 'frame': region.get(k) or owned[k]} for k in every},
        'generated': now or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit': source_commit, 'image_source_commit': source_commit,
        'town_frames': towns, 'partial_town_overlap_cells': partial,
        'coverage_total': COVERAGE_TOTAL, 'coverage_basis': COVERAGE_BASIS,
        'native_checked': False, 'owner_accepted': False,
    }
    if run:
        e['run'] = run
    return with_evidence(e, state, archive_sha256, readback_sha256, evidence, shipped)


# -- the ledger files ------------------------------------------------------------------------------------------------

# The stored form is compact (the ledger grows by a build per release; tools/release.py LARGE_TEXT caps it at 1 MiB):
# an entry whose cells are all included keeps them as 'region_cells' (the cells whose frame is the region frame named
# after the cell, rcm19_p14 for -19,14), space-separated, and 'frame_cells' {frame: cells} for the rest (the town
# frames); one entry per line, no indentation. In memory every entry has 'cells' {cell: {state, frame}} as before, and
# the reader (load here, world-map.html inclusionExpand) still takes the earlier per-cell form.

def region_name(k):
    """The region frame named after cell K: -19,14 -> rcm19_p14, 22,0 -> rcp22_p0."""
    x, y = cell_order(k)
    return 'rc%s%d_%s%d' % ('m' if x < 0 else 'p', abs(x), 'm' if y < 0 else 'p', abs(y))


def compact_entry(e):
    """The stored form of an entry (see above); an entry with a cell that is not included keeps the per-cell form."""
    cells = e.get('cells')
    if cells is None or any(v.get('state') != 'included' for v in cells.values()):
        return e
    region, frames = [], {}
    for k in sorted(cells, key=cell_order):
        if cells[k].get('frame') == region_name(k):
            region.append(k)
        else:
            frames.setdefault(cells[k].get('frame'), []).append(k)
    out = {name: value for name, value in e.items() if name != 'cells'}
    out['region_cells'] = ' '.join(region)
    out['frame_cells'] = {f: ' '.join(ks) for f, ks in sorted(frames.items())}
    return out


def entry_cells(e):
    """{cell: {state, frame}} of an entry in either form."""
    if 'cells' in e:
        return e['cells']
    cells = {k: {'state': 'included', 'frame': region_name(k)} for k in (e.get('region_cells') or '').split()}
    for frame, ks in (e.get('frame_cells') or {}).items():
        for k in ks.split():
            cells[k] = {'state': 'included', 'frame': frame}
    return {k: cells[k] for k in sorted(cells, key=cell_order)}


def expand_entry(e):
    if 'cells' in e:
        return e
    out = {name: value for name, value in e.items() if name not in ('region_cells', 'frame_cells')}
    out['cells'] = entry_cells(e)
    return out


def ledger_text(doc):
    """The stored JSON: the document's own fields, then one compact entry per line."""
    head = {name: value for name, value in doc.items() if name != 'builds'}
    lines = [json.dumps(compact_entry(b), separators=(',', ':')) for b in doc.get('builds', [])]
    return (json.dumps(head, separators=(',', ':'))[:-1] + (',' if head else '') + '"builds":[\n'
            + ',\n'.join(lines) + '\n]}\n')


def load(ledger_dir):
    path = Path(ledger_dir) / LEDGER_FILE
    doc = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'format': FORMAT, 'builds': []}
    if doc.get('format') != FORMAT:
        raise ValueError('%s is not %s' % (path, FORMAT))
    return dict(doc, builds=[expand_entry(b) for b in doc.get('builds', [])])


def same_build(a, b):
    return a.get('version') == b.get('version') and a.get('run') == b.get('run')


def merged(doc, new, top=False, replace_version=False):
    """DOC with NEW in place of the same build (same version and run; every entry of that version with
    REPLACE_VERSION). Newest first, or NEW first with TOP."""
    builds = [b for b in doc.get('builds', [])
              if not (same_build(b, new) or (replace_version and b.get('version') == new.get('version')))]
    if top:
        builds = [new] + builds
    else:
        builds = sorted(builds + [new], key=lambda b: b.get('generated', ''), reverse=True)
    return dict(doc, format=FORMAT, builds=builds)


def _atomic(path, text):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text, encoding='utf-8', newline='\n')
    os.replace(tmp, path)


def save(ledger_dir, doc):
    """The JSON and the page's JS copy (the same content), each written atomically."""
    ledger_dir = Path(ledger_dir)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    _atomic(ledger_dir / LEDGER_FILE, ledger_text(doc))
    _atomic(ledger_dir / SCRIPT_FILE, script_text(doc))
    return doc


def write(ledger_dir, new, replace_version=False):
    """The repository ledger's writer: replace or add the entry, newest first; write the JSON and the page's JS copy.
    It holds packaged and released builds only: a built entry lives in its run's toolkit copy (build_step), never
    here, so the repository ledger grows by the packaged builds alone (its 1 MiB limit, tools/release.py)."""
    if new.get('state') not in EVIDENCE_STATES:
        raise ValueError('the repository inclusion ledger holds packaged and released builds only; a %s entry stays in '
                         "its run's toolkit copy" % new.get('state'))
    doc = merged(load(ledger_dir), new, replace_version=replace_version)
    doc['builds'] = [b for b in doc['builds'] if b.get('state') != 'built']
    return save(ledger_dir, doc)


# -- the builder's step, packaging and the release -------------------------------------------------------------------

def run_entry(doc, run_name):
    return next((b for b in doc.get('builds', []) if b.get('run') == run_name), None)


def build_step(run, version, source_commit, cells_text=None, ledger=LEDGER, now=None, log=print):
    """The builder's step at the end of a build with a CHIM world: RUN/toolkit/chim-inclusion.json/.js = the repository
    ledger with this run's entry (state built) on top. Reused when its inputs are unchanged: the entry is keyed by
    SHA-256 of this code, the version, run, commit, chim-source.json and the cell list ('inputs_sha256'); a changed
    repository ledger only re-merges the kept entry (a packaged entry stays packaged). Returns the entry, or None when
    the run has no CHIM world. Reads two JSON files and writes two: well under a second."""
    run = Path(run)
    source = run / 'chim-world' / 'chim-source.json'
    if not source.is_file():
        log('CHIM inclusion: skipped (no chim-world/chim-source.json in this run)')
        return None
    toolkit = run / TOOLKIT_FOLDER
    label = version if str(version).startswith('v') else 'v' + str(version)
    # the interiors the build includes (BUILD-SUMMARY-INTERIOR-COUNTS-48): kept with the entry, part of its inputs
    from interior_counts import counts as interior_counts, summary_lines as interior_lines
    interiors = interior_counts(run)
    inputs = text_sha256(json.dumps({
        'format': FORMAT, 'code': sha256(Path(__file__)), 'version': label, 'run': run.name,
        'source_commit': source_commit, 'chim_source': sha256(source), 'cells': text_sha256(cells_text or ''),
        'interiors': interiors}, sort_keys=True))
    repo = load(ledger)
    repo_sha = text_sha256(json.dumps(repo, sort_keys=True))
    kept = None
    if (toolkit / LEDGER_FILE).is_file():
        try:
            mine = load(toolkit)
            kept = run_entry(mine, run.name)
        except (OSError, ValueError):
            mine = None
        if kept is not None and kept.get('inputs_sha256') == inputs:
            if mine.get('repository_ledger_sha256') == repo_sha and (toolkit / SCRIPT_FILE).is_file():
                log('CHIM inclusion: reused (inputs unchanged): %s %s, %s, %d cells' % (
                    label, run.name, kept['state'], len(kept['cells'])))
                for line in interior_lines(interiors):
                    log('CHIM inclusion: ' + line)
                return kept
        else:
            kept = None
    new = kept or dict(entry(label, 'built', source_commit, source, None, now=now, run=run.name, cells_text=cells_text),
                       inputs_sha256=inputs)
    if interiors is not None:
        from interior_counts import ledger_record
        new['interiors'] = ledger_record(interiors)
    doc = merged(repo, new, top=True)
    doc['repository_ledger_sha256'] = repo_sha
    save(toolkit, doc)
    log('CHIM inclusion: %s %s, %s, %d cells (%d town overlaps) on top of the repository ledger -> %s' % (
        label, run.name, new['state'], len(new['cells']), len(new['partial_town_overlap_cells']), toolkit / LEDGER_FILE))
    for line in interior_lines(interiors):
        log('CHIM inclusion: ' + line)
    return new


def package(run, archive, readback, evidence, shipped=False):
    """Packaging: the run's entry in RUN/toolkit becomes packaged with the archive's and the readback's SHA-256."""
    run = Path(run)
    toolkit = run / TOOLKIT_FOLDER
    doc = load(toolkit)
    e = run_entry(doc, run.name)
    if e is None:
        raise ValueError('%s has no inclusion entry for run %s (the builder writes it at the end of a CHIM build)'
                         % (toolkit / LEDGER_FILE, run.name))
    new = with_evidence(e, 'packaged', sha256(archive), sha256(readback), evidence, shipped)
    save(toolkit, merged(doc, new, top=True))
    return new


def release(run, ledger=LEDGER, version=None, evidence=None):
    """The release step: the run's packaged entry goes into the repository LEDGER as released (replacing every entry of
    that version). VERSION renames it (a release run's entry already carries the release version)."""
    run = Path(run)
    e = run_entry(load(run / TOOLKIT_FOLDER), run.name)
    if e is None or e.get('state') not in EVIDENCE_STATES:
        raise ValueError('run %s has no packaged inclusion entry: package it first (chim_inclusion.py package)' % run.name)
    if version:
        e = dict(e, version=version if version.startswith('v') else 'v' + version)
    new = with_evidence(e, 'released', e.get('archive_sha256'), e.get('evidence_sha256'), evidence or e.get('evidence'),
                        True)
    write(ledger, new, replace_version=True)
    return new


def release_problems(version, ledger=LEDGER):
    """Why a release of VERSION cannot be cut: [] when the repository ledger holds VERSION as released, with its
    archive and readback digests."""
    label = version if version.startswith('v') else 'v' + version
    try:
        doc = load(ledger)
    except (OSError, ValueError) as exc:
        return ['the CHIM inclusion ledger cannot be read: %s' % exc]
    found = [b for b in doc.get('builds', []) if b.get('version') == label]
    if not found:
        return ['the CHIM inclusion ledger (amiwind-toolkit/%s) lacks %s: package the release run, then run '
                '`tools/chim_inclusion.py release --run RUN` and commit the ledger' % (LEDGER_FILE, label)]
    if not any(b.get('state') == 'released' and b.get('archive_sha256') and b.get('evidence_sha256') for b in found):
        return ['the CHIM inclusion ledger has %s only as %s, not released with its archive and readback: run '
                '`tools/chim_inclusion.py release --run RUN`' % (label, ', '.join(sorted({b.get('state', '?') for b in found})))]
    return []


SERVED_RUNS = 10                                    # toolkit_serve.py --builds: the newest runs' entries on top


def served_ledger(build_toolkit=None, builds=None, ledger=LEDGER, limit=SERVED_RUNS):
    """The ledger the served Toolkit answers (tools/toolkit_serve.py): a build's own copy (--build: its toolkit folder,
    this build on top) or the repository ledger, plus, with BUILDS (--builds: the folder of run folders), the entries
    of the LIMIT newest runs that wrote one, newest on top."""
    base = Path(build_toolkit) if build_toolkit and (Path(build_toolkit) / LEDGER_FILE).is_file() else Path(ledger)
    doc = load(base)
    if builds and Path(builds).is_dir():
        runs = []
        for run in Path(builds).iterdir():
            f = run / TOOLKIT_FOLDER / LEDGER_FILE
            if f.is_file():
                runs.append((f.stat().st_mtime, run))
        for _, run in sorted(runs)[-limit:]:          # oldest first, so the newest ends on top
            try:
                e = run_entry(load(run / TOOLKIT_FOLDER), run.name)
            except (OSError, ValueError):
                continue
            if e is not None:
                doc = merged(doc, e, top=True)
    return doc


def script_text(doc):
    return SCRIPT_PREFIX + ledger_text(doc).rstrip('\n') + ';\n'


# -- command line ----------------------------------------------------------------------------------------------------

def summary(e, doc):
    return '%s%s: %s, %d cells, %d town overlaps; ledger has %s' % (
        e['version'], ' (%s)' % e['run'] if e.get('run') else '', e['state'], len(e['cells']),
        len(e['partial_town_overlap_cells']), ', '.join(b['version'] for b in doc['builds']))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('package', 'release', 'check-release'):
        command = argv.pop(0)
        ap = argparse.ArgumentParser(prog='chim_inclusion.py ' + command)
        if command == 'check-release':
            ap.add_argument('--version', help='default: v + the VERSION file')
            ap.add_argument('--ledger', type=Path, default=LEDGER)
            a = ap.parse_args(argv)
            version = a.version or 'v' + (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
            problems = release_problems(version, a.ledger)
            for line in problems:
                print('CHIM inclusion: ' + line)
            if not problems:
                print('CHIM inclusion: %s is in the ledger as released' % version)
            return 1 if problems else 0
        ap.add_argument('--run', required=True, type=Path, help='the build run folder (its toolkit/ holds the entry)')
        if command == 'package':
            ap.add_argument('--archive', required=True, type=Path, help='the packaged playtest ZIP')
            ap.add_argument('--readback', required=True, type=Path, help='the HDF readback record')
            ap.add_argument('--evidence', required=True)
            ap.add_argument('--shipped', action='store_true')
            a = ap.parse_args(argv)
            e = package(a.run, a.archive, a.readback, a.evidence, a.shipped)
            print(summary(e, load(a.run / TOOLKIT_FOLDER)))
            return 0
        ap.add_argument('--ledger', type=Path, default=LEDGER)
        ap.add_argument('--version', help='the release version, when it differs from the run entry\'s')
        ap.add_argument('--evidence', help='the evidence text, when it differs from the packaged entry\'s')
        a = ap.parse_args(argv)
        e = release(a.run, a.ledger, a.version, a.evidence)
        print(summary(e, load(a.ledger)))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--version', required=True)
    ap.add_argument('--state', choices=EVIDENCE_STATES, default='packaged',
                    help='the repository ledger holds packaged and released builds (built entries: the builder, in the run)')
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--chim-source', required=True, type=Path)
    ap.add_argument('--cells', type=Path)
    ap.add_argument('--run', help='the build run name (kept with the entry)')
    ap.add_argument('--archive', type=Path, help='required for packaged and released')
    ap.add_argument('--readback', type=Path, help='required for packaged and released')
    ap.add_argument('--evidence', help='required for packaged and released')
    ap.add_argument('--shipped', action='store_true')
    ap.add_argument('--ledger', type=Path, default=LEDGER)
    a = ap.parse_args(argv)
    try:
        new = entry(a.version, a.state, a.source_commit, a.chim_source, a.cells,
                    sha256(a.archive) if a.archive else None, sha256(a.readback) if a.readback else None,
                    a.evidence, a.shipped, run=a.run)
        doc = write(a.ledger, new, replace_version=a.state == 'released')
    except ValueError as exc:
        ap.error(str(exc))
    print(summary(new, doc))
    return 0


if __name__ == '__main__':
    sys.exit(main())
