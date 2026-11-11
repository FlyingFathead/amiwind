# SPDX-License-Identifier: GPL-3.0-only
"""Every version or release value the Toolkit shows, or stores in its tracker data, must follow the VERSION file.

TOOLKIT-ELIGIBLE-RELEASE-STALE-64: the tracker headline read "eligible for v0.0.57" for six versions, because the
ingest that wrote the data ran from an old checkout. The rule since: version-derived fields are computed from VERSION at
the moment the data is written (tools/cell_progress.py stamp_document), never typed, never read from a plan.

  python3 tools/tracker_version_check.py static        the code: no version typed into the Toolkit pages or the tracker
  python3 tools/tracker_version_check.py data FILE     the tracker data file (cell-progress.json): stamp, eligible release
                                                       and build against VERSION; the fix is
                                                       cell_progress.py restamp --out DIR (no re-ingest needed)

The pregate runs both before every gate; tests/test_tracker_version.py runs the same functions.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = 'amiwind-toolkit'
# Files whose version-like text is data or another program's own version, not a claim about the AmiWind line:
#   chim-inclusion.js    the generated inclusion ledger (build names, release names of cells)
#   map-inspector.html   the inspector's own program/format version (data-inspector-version, program.version)
# The "Last updated with AmiWind" line and the Toolkit's own version are kept by tools/toolkit_version.py.
SKIP_FILES = {'chim-inclusion.js', 'map-inspector.html'}
ALLOWED = (re.compile(r'Last updated with AmiWind v[0-9.]+'),
           re.compile(r'data-inspector-version="[0-9.]+"'),
           re.compile(r"program:\{name:'[^']*',version:'[0-9.]+'\}"),
           re.compile(r"const TOOLKIT = \{name: '[^']*', version: '[0-9.]+'\}"))
VERSION_LIKE = re.compile(r'(?<![0-9.])v?0\.0\.\d{2,3}(?:-(?:dev|rc)\d+)?(?![0-9.])')
COMMENT = re.compile(r'^\s*(//|\*|/\*|<!--)')
RELEASE_IN_NAME = re.compile(r'v(\d+)[._](\d+)[._](\d+)')


def version_tuple(text):
    found = re.findall(r'\d+', str(text).split('-')[0])[:3]
    return tuple(int(x) for x in found) if len(found) == 3 else None


def current_version(root=ROOT):
    return (Path(root) / 'VERSION').read_text(encoding='utf-8').strip()


def static_problems(root=ROOT):
    """Problems in the code: a version typed into a Toolkit page or script (comments excepted), or a tracker that does not
    compute its release label from VERSION."""
    root = Path(root)
    out = []
    for path in sorted((root / KIT).glob('*')):
        if path.suffix not in ('.html', '.js') or path.name in SKIP_FILES:
            continue
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if COMMENT.match(line):
                continue
            text = line
            for pattern in ALLOWED:
                text = pattern.sub('', text)
            for found in VERSION_LIKE.findall(text):
                out.append('%s/%s:%d types the version %s; show the data\'s own value (version.json / the tracker headline)'
                           % (KIT, path.name, number, found))
    source = (root / 'tools' / 'cell_progress.py').read_text(encoding='utf-8')
    if re.search(r"ELIGIBLE_RELEASE\s*=\s*['\"]v", source):
        out.append('tools/cell_progress.py types an eligible release: compute it from VERSION (working_release)')
    if 'eligible_release(None, working_release())' not in source or 'stamp_document(doc)' not in source:
        out.append('tools/cell_progress.py no longer computes eligible_release from VERSION / stamps its data (stamp_document)')
    return out


def data_problems(doc, version):
    """Problems in a tracker document against the VERSION text: the stamp, the eligible release, the newest build."""
    out = []
    want = version_tuple(version)
    release = 'v%d.%d.%d' % want if want else None
    stamp = doc.get('version_stamp')
    head = doc.get('headline') or {}
    fix = 'run tools/cell_progress.py restamp --out <tracker folder> (no re-ingest needed)'
    if not isinstance(stamp, dict):
        out.append('tracker data has no version_stamp: %s' % fix)
    elif stamp.get('release') != release:
        out.append('tracker data is stamped %s, the release in development (VERSION %s) is %s: %s'
                   % (stamp.get('release'), version, release, fix))
    if head.get('eligible_release') != release:
        out.append('tracker headline says "eligible for %s", the release in development is %s: %s'
                   % (head.get('eligible_release'), release, fix))
    for key in ('in_game_label', 'in_game_build'):
        named = RELEASE_IN_NAME.search(str(head.get(key) or ''))
        if named and want and tuple(int(x) for x in named.groups()) > want:
            out.append('tracker headline %s names a build newer than VERSION %s: %s' % (key, version, head.get(key)))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['static']:
        problems = static_problems()
    elif len(argv) == 2 and argv[0] == 'data':
        try:
            doc = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            print('tracker data could not be read: %s' % exc)
            return 1
        problems = data_problems(doc, current_version())
    else:
        print(__doc__)
        return 2
    for line in problems:
        print('VERSION CHECK: ' + line)
    if not problems:
        print('ok: %s follows VERSION %s' % (argv[0], current_version()))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
