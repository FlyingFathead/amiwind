#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bug register: docs/bugs/bugs.json is the source; docs/BUGS.md, the fact table and the
"Bugs in the same category" section of every report page, the families table in
docs/bugs/README.md and the CHIM Engine tracker (docs/bugs/CHIM_TRACKER.md) are generated
from it.

Usage:
  bug_register.py render        rewrite every generated part (register, pages, families table,
                                CHIM tracker); first marks every CHIM- ID and chim-streamer bug
                                that lacks its CHIM part (printed, saved to bugs.json)
  bug_register.py check         validate bugs.json; fail if any generated part is stale
  bug_register.py add ID --title T --found VERSION --reported-by WHO --where TEXT
                         --severity S --severity-reason TEXT --family KEY
                         [--found-date YYYY-MM-DD] [--reproduction R] [--related ID...]
                         [--status TEXT] [--tag T...] [--chim PART] [build options]
                                add an open bug (then write its report page and render)
  bug_register.py set ID [--state open|fixed|closed] [--fixed-in V] [--status TEXT]
                         [--owner-accepted V] [--tag T...] [any fact option of add]
                         [--duplicate-of ID] [--persists-in V...] [--chim PART] [build options]

Build options (the build a bug was found in, docs/bugs/README.md "Found in build"):
  --from-build build.json       fill them from a build receipt (and PLAYTEST-MANIFEST.json
                                beside it): playtest version, source, engine and world
                                commits, CHIM version and world format
  --build-name N --source-commit C --engine-commit C --world-commit C|none
  --chim-version V|none --chim-format F|none --unknown-reason TEXT --build-note TEXT
                                set or override single values ("unknown" needs a reason)
  bug_register.py backfill FILE [--overwrite] [--pages]
                                merge facts from a JSON list of records (same keys as
                                bugs.json) into the register: fills missing facts only
                                unless --overwrite; related links are made symmetric;
                                --pages also reads hand-written fact tables (they win)

Schema (docs/bugs/bugs.schema.json): a list of objects, one per bug, unique "id"; "state" is
open, fixed (a correction shipped in "fixed_in" with verification) or closed (not a bug,
duplicate or superseded; say why in "status"). Bugs found from v0.0.30 on (ID suffix 30 or
higher) must carry every fact field (FACTS). Families: docs/bugs/families.json. Rules and the
report template: docs/bugs/README.md.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'bugs' / 'bugs.json'
FAMILIES = ROOT / 'docs' / 'bugs' / 'families.json'
REGISTER = ROOT / 'docs' / 'BUGS.md'
README = ROOT / 'docs' / 'bugs' / 'README.md'
PAGES = ROOT / 'docs' / 'bugs'
BEGIN = '<!-- BEGIN GENERATED BUG REGISTER: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->'
END = '<!-- END GENERATED BUG REGISTER -->'
FACTS_BEGIN = '<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->'
FACTS_END = '<!-- END GENERATED FACTS -->'
CAT_BEGIN = '<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->'
CAT_END = '<!-- END GENERATED CATEGORY -->'
FAM_BEGIN = '<!-- BEGIN GENERATED FAMILIES: edit docs/bugs/families.json and bugs.json, then run tools/bug_register.py render -->'
FAM_END = '<!-- END GENERATED FAMILIES -->'
CHIM_TRACKER = ROOT / 'docs' / 'bugs' / 'CHIM_TRACKER.md'
JOURNAL = ROOT / 'docs' / 'BUG_JOURNAL.md'
CHIM_VERSION_FILE = ROOT / 'CHIM_VERSION'
# Generated pages inside docs/bugs that are not report pages.
GENERATED_PAGES = ('README.md', 'CHIM_TRACKER.md')
CAT_HEADING = '## Bugs in the same category'
ID_RE = re.compile(r'^(AW-\d{8}-\d{2}|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]{2,3}|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-0[0-9])$')
FIELDS = {'id': str, 'title': str, 'state': str, 'fixed_in': (str, type(None)),
          'owner_accepted': (str, type(None)), 'status': str, 'report': (str, type(None))}
# Facts every bug found from v0.0.30 on must carry (owner requirement, 9 October 2026).
FACTS = ('reported_by', 'found_date', 'found_in', 'where', 'reproduction', 'duplicate_of', 'persists_in',
         'severity', 'severity_reason', 'family', 'related')
OPTIONAL = ('tags', 'chim', 'build')
# CHIM Engine tracker (docs/bugs/CHIM_TRACKER.md): a bug is a CHIM bug when its "chim" field names
# its part. Required for every CHIM- ID and every bug of the chim-streamer family; any other bug
# opts in when its cause or repair is in the CHIM engine, world format, builder stage or streaming.
CHIM_PARTS = (('streaming', 'Engine streaming and memory'), ('format', 'World format'), ('builder', 'Builder'),
              ('stairs', 'Stairs and collision on CHIM worlds'), ('rendering', 'Rendering and visibility'),
              ('performance', 'Performance'))
CHIM_PART_KEYS = tuple(k for k, _ in CHIM_PARTS)
CHIM_FAMILY = 'chim-streamer'
# The build a bug was found in (owner requirement, 9 October 2026): "build" in bugs.json.
BUILD_KEYS = ('name', 'source_commit', 'engine_commit', 'world_commit', 'chim_version', 'chim_format',
              'unknown_reason', 'note')
BUILD_SOURCE = 'source'
COMMIT_RE = re.compile(r'^[0-9a-f]{7,40}$')
CHIM_VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')
CHIM_FORMAT_RE = re.compile(r'^\d+\.\d+$')
# A numbered build (playtest, release candidate or release); a found_in like this needs "build".
BUILD_RE = re.compile(r'^v\d+\.\d+\.\d+(-(dev|rc)\d+)?$')
IMAGES = ROOT / 'docs' / 'images'
# Frames on bug pages follow the documentation image convention: docs/images/amiwind-v<version>-<name>.png
# (or .gif clips), listed in tools/release.py, tools/release-files.json and the .gitignore exceptions.
IMAGE_NAME_RE = re.compile(r'^amiwind-v\d+\.\d+\.\d+(-[a-z]+\d*)?-[a-z0-9]+(-[a-z0-9]+)*\.(png|gif)$')
IMAGE_REF_RE = re.compile(r'\]\(((?:\.\./)*images/[^)\s]+|[^)\s]*\.(?:png|gif|jpe?g))(?:\s+"[^"]*")?\)')
IMAGE_LIMITS = {'.png': 1048576, '.gif': 4194304}
IMAGE_MAGIC = {'.png': (b'\x89PNG\r\n\x1a\n',), '.gif': (b'GIF87a', b'GIF89a')}
STATES = ('open', 'fixed', 'closed')
REPRODUCTION = ('always', 'sometimes', 'once', 'unknown')
SEVERITIES = ('critical', 'high', 'medium', 'low')
REPORTERS = ('owner', 'developer', 'review', 'audit', 'test', 'build', 'ci', 'unknown')
REPORTER_RE = re.compile(r'^(%s|gate:[a-z0-9][a-z0-9-]*)$' % '|'.join(REPORTERS))
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
FACTS_FROM_SERIES = 30
# Optional cross-cutting tags; each gets its own list below the register table.
TAGS = ('performance',)
VERSION_RE = re.compile(r'^v\d+\.\d+\.\d+(-[a-z]+\d*)?$')
# A development line such as v0.0.32-dev is a branch, not a shipped build (numbered -devN builds are).
DEV_LINE_RE = re.compile(r'^v\d+\.\d+\.\d+-dev$')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December')
ORDER = {'open': 0, 'fixed': 1, 'closed': 2}


def load(path=DATA):
    return json.loads(path.read_text(encoding='utf-8'))


def load_families(path=FAMILIES):
    return json.loads(path.read_text(encoding='utf-8'))


def save(bugs, path=DATA):
    path.write_text(json.dumps(bugs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def series(bug_id):
    """Version series an ID was found in (its two-digit suffix), or None for dated/legacy IDs."""
    if bug_id.startswith('AW-'):
        return None
    m = re.search(r'-(\d{2})$', bug_id)
    return int(m.group(1)) if m else None


def needs_facts(b):
    s = series(b['id'])
    return s is not None and s >= FACTS_FROM_SERIES


def has_facts(b):
    return any(k in b for k in FACTS)


def _line_ok(text, limit):
    return isinstance(text, str) and text.strip() and '|' not in text and '\n' not in text and len(text) <= limit


def validate_facts(b, ids, families, where):
    errors = []
    missing = [k for k in FACTS if k not in b]
    if missing:
        if needs_facts(b) or has_facts(b):
            errors.append('%s: missing facts %s (required for bugs found from v0.0.%d on; '
                          'see docs/bugs/README.md)' % (where, ', '.join(missing), FACTS_FROM_SERIES))
        if not has_facts(b):
            return errors
    g = b.get
    if 'reported_by' in b and not (isinstance(g('reported_by'), str) and REPORTER_RE.match(g('reported_by'))):
        errors.append('%s: reported_by must be one of %s or gate:<name>' % (where, '/'.join(REPORTERS)))
    if 'found_date' in b:
        d = g('found_date')
        ok = d == 'unknown'
        if isinstance(d, str) and DATE_RE.match(d):
            try:
                datetime.date.fromisoformat(d)
                ok = True
            except ValueError:
                ok = False
        if not ok:
            errors.append('%s: found_date must be YYYY-MM-DD or unknown' % where)
    if 'found_in' in b and not (g('found_in') == 'unknown' or isinstance(g('found_in'), str)
                                and VERSION_RE.match(g('found_in'))):
        errors.append('%s: found_in must be a version like v0.0.32-dev3, or unknown' % where)
    if 'where' in b and not _line_ok(g('where'), 100):
        errors.append('%s: where must be one line of at most 100 characters without |' % where)
    if 'reproduction' in b and g('reproduction') not in REPRODUCTION:
        errors.append('%s: reproduction must be one of %s' % (where, REPRODUCTION))
    if 'duplicate_of' in b:
        dup = g('duplicate_of')
        if dup is not None and (not isinstance(dup, str) or dup not in ids or dup == b['id']):
            errors.append('%s: duplicate_of must be null or another registered ID' % where)
        elif dup is not None and b['state'] != 'closed':
            errors.append('%s: a duplicate is closed (state closed, status "duplicate of %s")' % (where, dup))
    if 'persists_in' in b:
        p = g('persists_in')
        if b['state'] == 'fixed':
            if p != 'fixed in %s' % b['fixed_in']:
                errors.append('%s: persists_in of a fixed bug must be "fixed in %s"' % (where, b['fixed_in']))
        elif p != 'unknown' and not (isinstance(p, list) and p and len(set(p)) == len(p)
                                     and all(isinstance(v, str) and VERSION_RE.match(v) for v in p)):
            errors.append('%s: persists_in must be a non-empty list of versions (last = last seen), '
                          'or unknown' % where)
    if 'severity' in b and g('severity') not in SEVERITIES:
        errors.append('%s: severity must be one of %s' % (where, SEVERITIES))
    if 'severity_reason' in b and not _line_ok(g('severity_reason'), 160):
        errors.append('%s: severity_reason must be one line of at most 160 characters without |' % where)
    if 'family' in b and g('family') not in families:
        errors.append('%s: family %r is not in docs/bugs/families.json' % (where, g('family')))
    if 'related' in b:
        r = g('related')
        if not isinstance(r, list) or r != sorted(set(r)) or b['id'] in r or any(x not in ids for x in r):
            errors.append('%s: related must be a sorted list of other registered IDs' % where)
    return errors


def must_be_chim(b):
    """A CHIM- ID or a chim-streamer bug: it must carry its CHIM part."""
    return b['id'].startswith('CHIM-') or b.get('family') == CHIM_FAMILY


def is_chim(b):
    return 'chim' in b


def needs_build(b):
    """The found-in-build record is required for CHIM bugs and for bugs found in a numbered build."""
    return is_chim(b) or must_be_chim(b) or (needs_facts(b) and isinstance(b.get('found_in'), str)
                                             and bool(BUILD_RE.match(b['found_in'])))


def validate_build(b, where):
    errors = []
    if 'build' not in b:
        if needs_build(b):
            errors.append('%s: missing build (the build it was found in: playtest version, source/engine/world '
                          'commits, CHIM version and world format; fill with tools/bug_register.py set %s '
                          '--from-build build.json, or --build-name %s --source-commit HASH for a finding in '
                          'source; "unknown" only with --unknown-reason)' % (where, b['id'], BUILD_SOURCE))
        return errors
    m = b['build']
    if not isinstance(m, dict) or not {'name', 'source_commit', 'engine_commit', 'world_commit', 'chim_version',
                                       'chim_format'} <= set(m) or set(m) - set(BUILD_KEYS):
        return ['%s: build must hold name, source_commit, engine_commit, world_commit, chim_version, chim_format '
                'and optionally unknown_reason and note' % where]
    if not _line_ok(m['name'], 60):
        errors.append('%s: build.name must be one line of at most 60 characters (e.g. "CHIM Preview 1", '
                      '"v0.0.33-dev1", "MiniWind v0.0.33-dev1", or "%s")' % (where, BUILD_SOURCE))
    for k in ('source_commit', 'engine_commit'):
        if not (m[k] == 'unknown' or isinstance(m[k], str) and COMMIT_RE.match(m[k])):
            errors.append('%s: build.%s must be a commit hash (7 to 40 hex digits) or unknown' % (where, k))
    legacy = m['chim_version'] is None
    for k, rx, what in (('world_commit', COMMIT_RE, 'a commit hash'), ('chim_version', CHIM_VERSION_RE, 'like 0.1.0'),
                        ('chim_format', CHIM_FORMAT_RE, 'like 0.4')):
        v = m[k]
        if v is None:
            if not legacy:
                errors.append('%s: build.%s is null only for a legacy-engine build (chim_version null)' % (where, k))
        elif legacy:
            errors.append('%s: a legacy-engine build (chim_version null) has no %s' % (where, k))
        elif not (v == 'unknown' or isinstance(v, str) and rx.match(v)):
            errors.append('%s: build.%s must be %s or unknown' % (where, k, what))
    if is_chim(b) and legacy:
        errors.append('%s: a CHIM bug names the CHIM version and world format of its build (or unknown with '
                      'a reason)' % where)
    unknown = [k for k in BUILD_KEYS[:6] if m.get(k) == 'unknown']
    if unknown and not _line_ok(m.get('unknown_reason'), 200):
        errors.append('%s: build has unknown %s: say why in build.unknown_reason (one line, at most 200 '
                      'characters, no |)' % (where, ', '.join(unknown)))
    if not unknown and 'unknown_reason' in m:
        errors.append('%s: build.unknown_reason without an unknown value' % where)
    if 'note' in m and not _line_ok(m['note'], 200):
        errors.append('%s: build.note must be one line of at most 200 characters without |' % where)
    return errors


def validate_chim(b, where):
    if 'chim' not in b:
        if must_be_chim(b):
            return ['%s: a CHIM bug (CHIM- ID or family %s) carries "chim": its part, one of %s (render fills '
                    'it)' % (where, CHIM_FAMILY, ', '.join(CHIM_PART_KEYS))]
        return []
    if b['chim'] not in CHIM_PART_KEYS:
        return ['%s: chim must be one of %s' % (where, ', '.join(CHIM_PART_KEYS))]
    return []


CHIM_PART_WORDS = (('stairs', r'stair|collision|hull|ground|standing'),
                   ('builder', r'builder|validator|harvest|payload|catalogue|receipt|tools/|gate|stage'),
                   ('format', r'format|pack order|read runs|record'),
                   ('rendering', r'pvs|visib|faces|texture|leaf|leaves|light|draw|render|speck|sky'),
                   ('performance', r'slow|performance|seconds|time'),
                   ('streaming', r'.'))


def guess_chim_part(b):
    """The CHIM part of a newly marked bug, from its title and where (render prints it to check)."""
    if 'performance' in b.get('tags', []):
        return 'performance'
    text = ('%s %s' % (b.get('title', ''), b.get('where', ''))).lower()
    return next(k for k, rx in CHIM_PART_WORDS if re.search(rx, text))


def mark_chim(bugs):
    """Give every CHIM- ID and chim-streamer bug without a part one; returns the IDs marked."""
    marked = []
    for b in bugs:
        if isinstance(b, dict) and isinstance(b.get('id'), str) and must_be_chim(b) and 'chim' not in b:
            b['chim'] = guess_chim_part(b)
            marked.append(b['id'])
    return marked


def _prose(text):
    """Page text without fenced code blocks."""
    out, fence = [], False
    for line in text.split('\n'):
        if line.lstrip().startswith(('```', '~~~')):
            fence = not fence
            continue
        if not fence:
            out.append(line)
    return '\n'.join(out)


def page_images(text):
    """Images and clips a report page links to (link targets as written, in page order)."""
    return list(dict.fromkeys(IMAGE_REF_RE.findall(_prose(text))))


def bug_images(b, pages=None):
    """The frames of one bug: docs/images files its report page links to (file names)."""
    pages = PAGES if pages is None else pages
    if not b.get('report') or not (pages / ('%s.md' % b['id'])).is_file():
        return []
    refs = page_images((pages / ('%s.md' % b['id'])).read_text(encoding='utf-8'))
    return [r.rsplit('/', 1)[-1] for r in refs if r.startswith('../images/')]


def release_media(root=ROOT):
    """(public PNGs, public GIF clips, files in the release list, .gitignore exceptions)."""
    import importlib
    sys.path.insert(0, str(root / 'tools'))
    release = importlib.import_module('release')
    shipped = set(json.loads((root / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
    ignore = (root / '.gitignore').read_text(encoding='utf-8').splitlines() if (root / '.gitignore').is_file() else []
    exceptions = {line[1:].lstrip('/') for line in ignore if line.startswith('!')}
    return set(release.DOCUMENTATION_IMAGES), set(release.DOCUMENTATION_CLIPS), shipped, exceptions


def image_problems(bugs, pages=None, images=None, media=None):
    """Every frame a report page shows is a public documentation image: docs/images/amiwind-v<version>-
    <name>.png (or a .gif clip), present, a real PNG/GIF under the release size limit, listed in
    tools/release.py, tools/release-files.json and the .gitignore exceptions."""
    pages = PAGES if pages is None else pages
    images = IMAGES if images is None else images
    pngs, gifs, shipped, exceptions = release_media() if media is None else media
    errors = []
    for b in sorted((x for x in bugs if isinstance(x, dict) and x.get('report')), key=lambda x: x['id']):
        page = pages / ('%s.md' % b['id'])
        if not page.is_file():
            continue
        for ref in page_images(page.read_text(encoding='utf-8')):
            where = '%s.md: %s' % (b['id'], ref)
            name = ref.rsplit('/', 1)[-1]
            if ref != '../images/%s' % name:
                errors.append('%s: bug frames live in docs/images/ (link ../images/<file>), see docs/bugs/README.md '
                              '"Screenshots"' % where)
                continue
            if not IMAGE_NAME_RE.match(name):
                errors.append('%s: name frames amiwind-v<version>-<name>.png (lower case, hyphens)' % where)
                continue
            path, ext = images / name, name[name.rindex('.'):]
            rel = 'docs/images/%s' % name
            if not path.is_file():
                errors.append('%s: missing file' % where)
                continue
            data = path.read_bytes()
            if not data.startswith(IMAGE_MAGIC[ext]):
                errors.append('%s: not a %s file' % (where, ext[1:].upper()))
            if len(data) > IMAGE_LIMITS[ext]:
                errors.append('%s: %d bytes, over the %d byte release limit' % (where, len(data), IMAGE_LIMITS[ext]))
            if rel not in (pngs if ext == '.png' else gifs):
                errors.append('%s: not listed in tools/release.py %s' % (
                    where, 'DOCUMENTATION_IMAGES' if ext == '.png' else 'DOCUMENTATION_CLIPS'))
            if rel not in shipped:
                errors.append('%s: not listed in tools/release-files.json' % where)
            if rel not in exceptions:
                errors.append('%s: no .gitignore exception !/%s' % (where, rel))
    return errors


def validate(bugs, families=None):
    errors = []
    if not isinstance(bugs, list):
        return ['bugs.json must be a list']
    if families is None:
        families = {f['key'] for f in load_families()}
    elif not isinstance(families, set):
        families = {f['key'] for f in families}
    ids = {b.get('id') for b in bugs if isinstance(b, dict)}
    seen = set()
    by_id = {}
    for i, b in enumerate(bugs):
        where = b.get('id', '#%d' % i) if isinstance(b, dict) else '#%d' % i
        if not isinstance(b, dict):
            errors.append('%s: not an object' % where)
            continue
        if not set(FIELDS) <= set(b) or set(b) - set(FIELDS) - set(FACTS) - set(OPTIONAL):
            errors.append('%s: fields must be %s, the facts %s and optional %s' % (
                where, sorted(FIELDS), list(FACTS), list(OPTIONAL)))
            continue
        by_id[b['id']] = b
        tags = b.get('tags', [])
        if not isinstance(tags, list) or not tags and 'tags' in b or len(set(tags)) != len(tags) \
                or any(t not in TAGS for t in tags) or tags != sorted(tags):
            errors.append('%s: tags must be a sorted, non-empty list from %s' % (where, TAGS))
        for k, t in FIELDS.items():
            if not isinstance(b[k], t):
                errors.append('%s: %s has the wrong type' % (where, k))
        if not ID_RE.match(b['id']):
            errors.append('%s: ID must look like AREA-WHAT-NN' % where)
        if b['id'] in seen:
            errors.append('%s: duplicate ID' % where)
        seen.add(b['id'])
        if b['state'] not in STATES:
            errors.append('%s: state must be one of %s' % (where, STATES))
        if b['state'] == 'fixed' and not b['fixed_in']:
            errors.append('%s: a fixed bug needs fixed_in' % where)
        if b['state'] != 'fixed' and b['fixed_in']:
            errors.append('%s: only a fixed bug has fixed_in' % where)
        for k in ('fixed_in', 'owner_accepted'):
            if b[k] and not VERSION_RE.match(b[k]):
                errors.append('%s: %s must be a version like v0.0.30-rc1' % (where, k))
            elif b[k] and DEV_LINE_RE.match(b[k]):
                errors.append('%s: %s names a development line (%s), not a shipped build; keep the bug open '
                              'with "fixed in source" in status until a numbered build ships it' % (where, k, b[k]))
        if b['owner_accepted'] and b['state'] != 'fixed':
            errors.append('%s: owner_accepted needs a fixed bug' % where)
        if b['report'] and b['report'] != 'bugs/%s.md' % b['id']:
            errors.append('%s: report must be bugs/%s.md' % (where, b['id']))
        if b['report'] and not (REGISTER.parent / b['report']).is_file():
            errors.append('%s: report page missing' % where)
        if '|' in b['title'] + b['status'] or '\n' in b['title'] + b['status']:
            errors.append('%s: no | or line breaks in title/status' % where)
        if not b['status'].strip() or not b['title'].strip():
            errors.append('%s: title and status are required' % where)
        errors += validate_facts(b, ids, families, where)
        errors += validate_chim(b, where)
        errors += validate_build(b, where)
    for b in by_id.values():
        for r in b.get('related') or []:
            other = by_id.get(r)
            if other is None or not isinstance(other.get('related'), list):
                continue
            if b['id'] not in other['related']:
                errors.append('%s: related lists %s, but %s does not list %s (links are both ways)'
                              % (b['id'], r, r, b['id']))
            if b.get('family') and b.get('family') == other.get('family') and b['id'] < r:
                errors.append('%s: related %s is in the same family %s; the family already links them, '
                              'so list only bugs from other families' % (b['id'], r, b['family']))
    return errors


def link(b, prefix=''):
    return '[%s](%s%s)' % (b['id'], prefix, b['report']) if b['report'] else b['id']


def human_date(d):
    if not d or d == 'unknown':
        return 'unknown'
    y, m, day = (int(x) for x in d.split('-'))
    return '%d %s %d' % (day, MONTHS[m - 1], y)


def first_noticed(b):
    date, version = b.get('found_date', 'unknown'), b.get('found_in', 'unknown')
    if date == 'unknown' and version == 'unknown':
        return 'unknown'
    return '%s, in %s' % (human_date(date), 'an unknown version' if version == 'unknown' else version)


def persists_text(b):
    p = b.get('persists_in', 'unknown')
    if isinstance(p, list):
        return ', '.join(p) + ' (last seen)'
    return p


def facts_table(b, by_id, families):
    fam = families.get(b.get('family'))
    dup = b.get('duplicate_of')
    rows = [('Reported by', b.get('reported_by', 'unknown')),
            ('First noticed', first_noticed(b)),
            ('Where', b.get('where', 'unknown')),
            ('Reproduction', b.get('reproduction', 'unknown')),
            ('Duplicate of', page_link(by_id[dup]) if dup else 'no'),
            ('Persists in', persists_text(b)),
            ('Severity', '%s: %s' % (b['severity'], b['severity_reason']) if b.get('severity') else 'unknown'),
            ('Family', '%s (`%s`)' % (fam['title'], fam['key']) if fam else 'unknown')]
    if is_chim(b):
        rows.append(('CHIM', '%s ([CHIM Engine tracker](CHIM_TRACKER.md))' % dict(CHIM_PARTS)[b['chim']]))
    rows += build_rows(b)
    out = [FACTS_BEGIN, '', '| Fact | Value |', '| --- | --- |']
    out += ['| %s | %s |' % (k, v) for k, v in rows]
    return '\n'.join(out + ['', FACTS_END])


def short(commit):
    return commit[:7] if commit and commit != 'unknown' else commit


def build_rows(b):
    """Fact table rows for the build a bug was found in."""
    m = b.get('build')
    if not isinstance(m, dict):
        return []
    name = m['name']
    if name == BUILD_SOURCE:
        name = 'none: found in source (development branch, tests or gates), not in a playtest build'
    if m['chim_version'] is None:
        commit = 'source and engine %s' % short(m['source_commit']) if m['source_commit'] == m['engine_commit'] \
            else 'source %s, engine %s' % (short(m['source_commit']), short(m['engine_commit']))
        engine = 'none: legacy engine'
    else:
        commit = 'source %s, engine %s, CHIM world %s' % (short(m['source_commit']), short(m['engine_commit']),
                                                         short(m['world_commit']))
        engine = 'CHIM %s, engine %s, world format %s' % (m['chim_version'], short(m['engine_commit']),
                                                         m['chim_format'])
    rows = [('Playtest version', name), ('From commit', commit), ('CHIM engine version', engine)]
    if m.get('unknown_reason'):
        rows.append(('Unknown because', m['unknown_reason']))
    if m.get('note'):
        rows.append(('Build note', m['note']))
    return rows


def build_text(m):
    """One-line summary of the found-in build for tables; values not recorded are named once."""
    if not isinstance(m, dict):
        return '-'
    shown, missing = [], []
    items = (('CHIM', m['chim_version']), ('format', m['chim_format']), ('engine', short(m['engine_commit'])),
             ('source', short(m['source_commit'])), ('world', short(m['world_commit'])))
    if m['chim_version'] is None:
        shown.append('legacy engine')
        if m['source_commit'] == m['engine_commit']:
            items = (('commit', short(m['source_commit'])),)
        else:
            items = (('engine', short(m['engine_commit'])), ('source', short(m['source_commit'])))
    for label, v in items:
        if v == 'unknown':
            missing.append(label)
        else:
            shown.append('%s %s' % (label, v))
    if missing:
        shown.append('%s not recorded' % ', '.join(missing))
    return '%s: %s' % ('source' if m['name'] == BUILD_SOURCE else m['name'], ', '.join(shown))


def page_link(b):
    return '[%s](%s.md)' % (b['id'], b['id']) if b['report'] else '%s (no report page)' % b['id']


def category_section(b, bugs, by_id, families):
    fam = families[b['family']]
    same = [x for x in sorted(bugs, key=lambda x: x['id']) if x.get('family') == b['family'] and x['id'] != b['id']]
    out = [CAT_BEGIN, '', CAT_HEADING, '',
           'Family: %s (`%s`). %s See [families](README.md#families).' % (fam['title'], fam['key'], fam['rule']), '']
    if same:
        out += ['- %s: %s' % (page_link(x), x['title']) for x in same]
    else:
        out += ['No other bugs in this category yet.']
    related = [by_id[r] for r in b.get('related') or [] if r in by_id]
    if related:
        out += ['', 'Related bugs in other categories:', '']
        out += ['- %s: %s' % (page_link(x), x['title']) for x in related]
    return '\n'.join(out + ['', CAT_END])


def found_in_cell(b):
    """The register's "Found in" cell: the version, plus the named build when it says more."""
    v = b.get('found_in', '-')
    m = b.get('build')
    if isinstance(m, dict) and m['name'] not in (BUILD_SOURCE, 'unknown', v):
        return '%s (%s)' % (v, m['name'])
    return v


def journal_changes(bugs, text, limit=10):
    """The newest journal entries (the journal is newest first) that name a CHIM bug:
    [(heading, anchor, [ids])]."""
    import doc_toc
    ids = {b['id'] for b in bugs if is_chim(b)}
    lines = text.split('\n')
    heads = [(i, raw) for i, level, raw in doc_toc.headings(lines) if level == 2]
    slug = doc_toc.Slugger()
    anchors = {}
    for i, level, raw in doc_toc.headings(lines):
        anchors[i] = slug(raw)
    out = []
    for n, (i, raw) in enumerate(heads):
        if raw == doc_toc.TITLE:
            continue
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        named = re.findall(r'\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+-\d{2,3}\b', '\n'.join(lines[i:end]))
        found = list(dict.fromkeys(x for x in named if x in ids))
        if found:
            out.append((raw, anchors[i], found))
            if len(out) == limit:
                break
    return out


CHIM_VERSION_PLANNED = '0.1.0'


def chim_version(path=None):
    """CHIM's own version from the CHIM_VERSION file; the planned first version until the file exists."""
    path = CHIM_VERSION_FILE if path is None else path
    if path.is_file():
        return path.read_text(encoding='utf-8').strip()
    return '%s (planned for the first CHIM release; no CHIM_VERSION file in this tree yet)' % CHIM_VERSION_PLANNED


def chim_tracker(bugs, journal_text, version, pages=None):
    """docs/bugs/CHIM_TRACKER.md, generated whole."""
    import doc_toc
    chim = [b for b in bugs if is_chim(b)]
    counts = {s: sum(1 for b in chim if b['state'] == s) for s in STATES}
    out = ['# CHIM Engine tracker', '',
           '<!-- Generated whole by tools/bug_register.py render from docs/bugs/bugs.json and docs/BUG_JOURNAL.md; '
           'do not edit by hand. -->', '',
           'Every bug of the CHIM engine: its streaming and memory, world format, builder, stairs and collision '
           'on CHIM worlds, rendering and performance. Generated together with the [bug register](../BUGS.md) '
           'from [`bugs.json`](bugs.json); a test fails when this page is stale or a CHIM bug is missing. Which '
           'bugs appear here and how to add one: [CHIM bugs](README.md#chim-bugs). Design: '
           '[world streamer](../WORLD_STREAMER.md).', '',
           'CHIM version: %s. %d CHIM bugs: %d open, %d fixed, %d closed.' % (
               version, len(chim), counts['open'], counts['fixed'], counts['closed']), '',
           '| Part | Open | Fixed | Closed |', '| --- | --- | --- | --- |']
    for key, title in CHIM_PARTS:
        part = [b for b in chim if b['chim'] == key]
        out.append('| [%s](#%s) | %d | %d | %d |' % (title, doc_toc.slug(title),
                                                   *(sum(1 for b in part if b['state'] == s) for s in STATES)))
    out += ['', '## Latest changes', '',
            'Newest first: the last 10 [journal](../BUG_JOURNAL.md) entries that name a CHIM bug.', '']
    changes = journal_changes(bugs, journal_text)
    out += ['- [%s](../BUG_JOURNAL.md#%s): %s' % (raw.replace('[', '(').replace(']', ')'), anchor, ', '.join(ids))
            for raw, anchor, ids in changes] or ['No journal entry names a CHIM bug yet.']
    for key, title in CHIM_PARTS:
        part = sorted((b for b in chim if b['chim'] == key), key=lambda b: (ORDER[b['state']], b['id']))
        out += ['', '## %s' % title, '']
        if not part:
            out.append('No bugs in this part yet.')
            continue
        out += ['| ID | Issue | State | Severity | First seen | Fixed in | Found in build | Status |',
                '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for b in part:
            pics = bug_images(b, pages)
            cell = '[%s](%s.md)' % (b['id'], b['id']) if b['report'] else b['id']
            if pics:
                cell += ' ([%d %s](../images/%s))' % (len(pics), 'frame' if len(pics) == 1 else 'frames', pics[0])
            out.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (
                cell, b['title'], b['state'], b.get('severity', '-'), first_noticed(b), b['fixed_in'] or '-',
                build_text(b.get('build')), b['status']))
    return '\n'.join(out) + '\n'


FACT_ROW = re.compile(r'^\|\s*(Reported by|First noticed)\s*\|')


def _strip_block(lines, begin, end):
    if begin in lines and end in lines:
        a, z = lines.index(begin), lines.index(end)
        return lines[:a] + lines[z + 1:], a
    return lines, None


def _hand_fact_table(lines):
    """A hand-written fact table directly under the title (the v0.0.32 release format): its line span."""
    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not lines[i].startswith('|'):
        return None
    j = i
    while j < len(lines) and lines[j].startswith('|'):
        j += 1
    if not any(FACT_ROW.match(x) for x in lines[i:j]):
        return None
    return i, j


def parse_fact_table(text):
    """Rows of the fact table (generated or hand-written) as {name: value}."""
    lines = text.split('\n')
    if FACTS_BEGIN in lines and FACTS_END in lines:
        span = lines[lines.index(FACTS_BEGIN):lines.index(FACTS_END)]
    else:
        hand = _hand_fact_table(lines)
        span = lines[hand[0]:hand[1]] if hand else []
    rows = {}
    for line in span:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 2 and cells[0] and not set(cells[0]) <= set('-: '):
            rows[cells[0]] = '|'.join(cells[1:]).strip()
    return rows


def rendered_page(text, b, bugs, by_id, families):
    lines = text.rstrip('\n').split('\n')
    lines, _ = _strip_block(lines, FACTS_BEGIN, FACTS_END)
    lines, _ = _strip_block(lines, CAT_BEGIN, CAT_END)
    hand = _hand_fact_table(lines)
    if hand:
        lines = lines[:hand[0]] + lines[hand[1]:]
    while lines and not lines[-1].strip():
        lines.pop()
    body = lines[1:]
    while body and not body[0].strip():
        body.pop(0)
    out = [lines[0]]
    if has_facts(b):
        out += ['', facts_table(b, by_id, families)]
    out += [''] + body if body else []
    if b.get('family') in families:
        out += ['', category_section(b, bugs, by_id, families)]
    return '\n'.join(out) + '\n'


def table(bugs):
    out = ['| ID | Issue | Severity | Found in | State | Fixed in | Owner accepted | Status |',
           '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for b in sorted(bugs, key=lambda b: (ORDER[b['state']], b['id'])):
        out.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (
            link(b), b['title'], b.get('severity', '-'), found_in_cell(b), b['state'], b['fixed_in'] or '-',
            b['owner_accepted'] or '-', b['status']))
    for tag in TAGS:
        tagged = [b for b in sorted(bugs, key=lambda b: (ORDER[b['state']], b['id'])) if tag in b.get('tags', [])]
        if tagged:
            out += ['', '### Tagged %s' % tag, '']
            out += ['- %s: %s (%s)' % (link(b), b['title'], b['state']) for b in tagged]
    return '\n'.join(out) + '\n'


def family_groups(bugs, families):
    out = ['', '### Bugs by family', '',
           'Every bug from v0.0.%d on belongs to one family (bugs with a shared cause or area); the families and '
           'their shared rules are in [bug tracking](bugs/README.md#families).' % FACTS_FROM_SERIES]
    for f in families:
        members = sorted((b for b in bugs if b.get('family') == f['key']), key=lambda b: (ORDER[b['state']], b['id']))
        if not members:
            continue
        out += ['', '#### %s (`%s`)' % (f['title'], f['key']), '']
        out += ['- %s: %s (%s, %s)' % (link(b), b['title'], b['state'], b.get('severity', 'severity unknown'))
                for b in members]
    return '\n'.join(out) + '\n'


def rendered(text, bugs, families=None):
    families = load_families() if families is None else families
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise SystemExit('docs/BUGS.md needs exactly one generated-register block')
    a = text.index(BEGIN) + len(BEGIN)
    b = text.index(END)
    counts = {s: sum(1 for x in bugs if x['state'] == s) for s in STATES}
    summary = '\n\n%d bugs: %d open, %d fixed, %d closed.\n\n' % (len(bugs), counts['open'], counts['fixed'], counts['closed'])
    return text[:a] + summary + table(bugs) + family_groups(bugs, families) + '\n' + text[b:]


def families_table(bugs, families):
    out = ['| Family | Key | Bugs (open of total) | Shared cause or rule |', '| --- | --- | --- | --- |']
    for f in families:
        members = [b for b in bugs if b.get('family') == f['key']]
        anchor = re.sub(r'[^\w\- ]', '', ('%s (%s)' % (f['title'], f['key'])).lower()).replace(' ', '-')
        out.append('| [%s](../BUGS.md#%s) | `%s` | %d of %d | %s |' % (
            f['title'], anchor, f['key'], sum(1 for b in members if b['state'] == 'open'), len(members), f['rule']))
    return '\n'.join(out)


def rendered_readme(text, bugs, families):
    if text.count(FAM_BEGIN) != 1 or text.count(FAM_END) != 1:
        raise SystemExit('docs/bugs/README.md needs exactly one generated-families block')
    a = text.index(FAM_BEGIN) + len(FAM_BEGIN)
    b = text.index(FAM_END)
    return text[:a] + '\n\n' + families_table(bugs, families) + '\n\n' + text[b:]


def validate_families(families):
    errors = []
    keys = [f.get('key') for f in families]
    if len(set(keys)) != len(keys):
        errors.append('families.json: duplicate family key')
    for f in families:
        if set(f) != {'key', 'title', 'rule'} or not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', f.get('key', '')) \
                or not _line_ok(f.get('title'), 80) or not _line_ok(f.get('rule'), 400):
            errors.append('families.json: %s needs key (lowercase-hyphenated), title and rule (one line, no |)'
                          % f.get('key'))
    return errors


def outputs(bugs, families):
    """Every generated file as {path: new text}."""
    fam = {f['key']: f for f in families}
    by_id = {b['id']: b for b in bugs}
    out = {REGISTER: rendered(REGISTER.read_text(encoding='utf-8'), bugs, families),
           README: rendered_readme(README.read_text(encoding='utf-8'), bugs, families)}
    for b in bugs:
        if b['report']:
            path = REGISTER.parent / b['report']
            out[path] = rendered_page(path.read_text(encoding='utf-8'), b, bugs, by_id, fam)
    out[CHIM_TRACKER] = chim_tracker(bugs, JOURNAL.read_text(encoding='utf-8'), chim_version())
    return out


def symmetric(bugs):
    """Make related links two-way, sorted, and drop links inside one family."""
    by_id = {b['id']: b for b in bugs}
    for b in bugs:
        for r in list(b.get('related') or []):
            if r in by_id and 'related' in by_id[r] and b['id'] not in by_id[r]['related']:
                by_id[r]['related'].append(b['id'])
    for b in bugs:
        if isinstance(b.get('related'), list):
            b['related'] = sorted({r for r in b['related'] if r in by_id and r != b['id']
                                   and not (b.get('family') and by_id[r].get('family') == b.get('family'))})


REPORTER_WORDS = (('owner', 'owner'), ('harry', 'owner'), ('playtest', 'owner'), ('review', 'review'),
                  ('hosted ci', 'ci'), ('unit test', 'test'), ('test suite', 'test'), ('build', 'build'),
                  ('audit', 'audit'), ('census', 'audit'), ('a/b', 'audit'), ('measure', 'audit'))
DATE_TEXT_RE = re.compile(r'\b(\d{1,2}) (%s) (\d{4})\b' % '|'.join(MONTHS))
VERSION_TEXT_RE = re.compile(r'\bv\d+\.\d+\.\d+(?:-[a-z]+\d*)?\b')


def facts_from_table(rows, b, ids):
    """Facts read from a hand-written fact table (free text, the v0.0.32 release format).

    Only values that map cleanly onto the schema are returned; the rest stay with the register."""
    out = {}
    text = {k: v for k, v in rows.items() if v}
    rep = text.get('Reported by', '').lower()
    if 'gate' in rep or 'validator' in rep:
        name = re.sub(r'[^a-z0-9]+', '-', rep.split('gate')[0].split('validator')[0]).strip('-')
        old = b.get('reported_by', '')
        out['reported_by'] = old if old.startswith('gate:') else 'gate:%s' % (name or 'unnamed')
    else:
        for word, who in REPORTER_WORDS:
            if word in rep:
                out['reported_by'] = who
                break
    noticed = text.get('First noticed', '')
    m = DATE_TEXT_RE.search(noticed)
    if m:
        out['found_date'] = '%s-%02d-%02d' % (m.group(3), MONTHS.index(m.group(2)) + 1, int(m.group(1)))
    m = VERSION_TEXT_RE.search(noticed)
    if m:
        out['found_in'] = m.group(0)
    if text.get('Where'):
        where = text['Where'].replace('|', '/').strip()
        out['where'] = where if len(where) <= 100 else where[:97].rsplit(' ', 1)[0] + '...'
    word = text.get('Reproduction', '').split(' ')[0].strip('.,;:').lower()
    if word in REPRODUCTION:
        out['reproduction'] = word
    dup = text.get('Duplicate of', '')
    m = re.search(r'duplicate of ([A-Z][A-Z0-9-]+)', dup, re.I) or re.match(r'\[?([A-Z][A-Z0-9-]+-\d{2,3})\b', dup)
    if m and m.group(1) in ids and m.group(1) != b['id']:
        out['duplicate_of'] = m.group(1)
    elif dup.lower().startswith(('no', '-')):
        out['duplicate_of'] = None
    versions = VERSION_TEXT_RE.findall(text.get('Persists in', ''))
    if text.get('Persists in', '').lower().startswith('unknown') and b['state'] != 'fixed':
        out['persists_in'] = 'unknown'
    elif versions and b['state'] != 'fixed':
        first = out.get('found_in', b.get('found_in'))
        seq = ([first] if first and first != 'unknown' and first not in versions else []) + versions
        out['persists_in'] = list(dict.fromkeys(seq))
    sev = text.get('Severity', '')
    word = re.split(r'[\s:(]', sev, maxsplit=1)[0].lower()
    if word in SEVERITIES:
        out['severity'] = word
        m = re.search(r'\((.+)\)', sev) or re.search(r':\s*(.+)$', sev)
        if m:
            reason = m.group(1).strip().rstrip('.')
            reason = (reason[0].upper() + reason[1:] + '.').replace('|', '/')
            if len(reason) <= 160:
                out['severity_reason'] = reason
    linked = set(re.findall(r'\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+-\d{2,3}\b', ' '.join(text.values())))
    out['related'] = sorted(x for x in linked if x in ids and x != b['id'] and x != out.get('duplicate_of'))
    return out


def backfill(bugs, records, overwrite=False, pages=False):
    """Merge fact records into bugs; returns the number of values written.

    With pages, a hand-written fact table on a report page (no generated markers) is read as well
    and wins over the records: it is newer, human-written input. render then replaces it."""
    by_id = {b['id']: b for b in bugs}
    written = 0
    records = list(records)
    if pages:
        for b in bugs:
            page = REGISTER.parent / (b['report'] or '')
            if not b['report'] or not page.is_file():
                continue
            text = page.read_text(encoding='utf-8')
            if FACTS_BEGIN in text or not _hand_fact_table(text.split('\n')):
                continue
            base = next((r for r in records if r.get('id') == b['id']), {})
            rec = facts_from_table(parse_fact_table(text), dict(base, **b), set(by_id))
            # the records file fills what the hand table does not say; the hand table wins where it does
            records = [r for r in records if r.get('id') != b['id']] + [dict(base, **rec, id=b['id'])]
            for k in rec:
                if k != 'related':
                    b.pop(k, None)
    for rec in records:
        b = by_id.get(rec.get('id'))
        if b is None:
            continue
        for k in FACTS:
            if k not in rec:
                continue
            if k == 'related':
                merged = sorted(set(b.get('related') or []) | {r for r in rec[k] if r in by_id})
                if merged != b.get('related'):
                    b['related'] = merged
                    written += 1
            elif overwrite or k not in b:
                b[k] = rec[k]
                written += 1
    # Every bug that carries facts carries all of them; missing ones start as unknown/empty.
    for b in bugs:
        if has_facts(b):
            for k, v in (('duplicate_of', None), ('related', []), ('reproduction', 'unknown'),
                         ('found_date', 'unknown'), ('found_in', 'unknown'), ('reported_by', 'unknown')):
                b.setdefault(k, v)
            if b['state'] == 'fixed':
                b['persists_in'] = 'fixed in %s' % b['fixed_in']
    symmetric(bugs)
    return written


def _order(b):
    """Keys in schema order: the register fields, the facts, then the optional tags, chim and build."""
    out = {k: b[k] for k in list(FIELDS) + list(FACTS) + list(OPTIONAL) if k in b}
    if isinstance(out.get('build'), dict):
        out['build'] = {k: out['build'][k] for k in BUILD_KEYS if k in out['build']}
    return out


def _find(d, keys):
    """The first value under any of keys in a receipt, top level first, then nested objects."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if d.get(k) not in (None, ''):
            return d[k]
    for v in d.values():
        got = _find(v, keys)
        if got not in (None, ''):
            return got
    return None


def _build_name(receipt, manifest):
    pre = receipt.get('chim_preview') if isinstance(receipt.get('chim_preview'), dict) else {}
    for name in (receipt.get('build_name'), pre.get('name'), (manifest or {}).get('package')):
        if isinstance(name, str) and name.strip():
            name = re.sub(r'\s*\(.*\)\s*$', '', name.strip())
            name = re.sub(r'^AmiWind\s+', '', name)
            if name:
                return name
    version = receipt.get('version') or (manifest or {}).get('version')
    if not version:
        return 'unknown'
    version = version if str(version).startswith('v') else 'v%s' % version
    return 'MiniWind %s' % version if receipt.get('miniwind') else version


def build_from_receipt(receipt, manifest=None):
    """The found-in-build record from a build receipt (build.json) and its PLAYTEST-MANIFEST.json.

    Only versions and commits are taken; paths and hashes of private files never enter bugs.json."""
    source = _find(receipt, ('source_commit',))
    pre = receipt.get('chim_preview') if isinstance(receipt.get('chim_preview'), dict) else {}
    engine = _find(pre, ('commit',)) if isinstance(pre.get('engine'), dict) else None
    engine = engine or _find(receipt, ('engine_commit',)) or source
    version = (_find(pre, ('chim_version',)) or _find(receipt, ('chim_version',))
               or _find(manifest or {}, ('chim_version',)))
    fmt = _find(pre, ('chim_world_format', 'world_format')) or _find(receipt, ('chim_world_format', 'chim_format',
                                                                              'world_format'))
    chim = version is not None or fmt is not None or receipt.get('builder') == 'chim'
    world = _find(receipt, ('world_commit',))
    if world is None and chim and not pre:
        world = source  # the repository builder wrote the CHIM world in the same run
    m = {'name': _build_name(receipt, manifest), 'source_commit': source or 'unknown',
         'engine_commit': engine or 'unknown',
         'world_commit': (world or 'unknown') if chim else None,
         'chim_version': (version or 'unknown') if chim else None,
         'chim_format': (fmt or 'unknown') if chim else None}
    missing = [k for k, v in m.items() if v == 'unknown']
    if missing:
        m['unknown_reason'] = 'the build receipt does not record %s' % ', '.join(k.replace('_', ' ') for k in missing)
    return m


def read_receipt(path):
    path = Path(path)
    receipt = json.loads(path.read_text(encoding='utf-8'))
    man = path.parent / 'PLAYTEST-MANIFEST.json'
    manifest = json.loads(man.read_text(encoding='utf-8')) if man.is_file() and man != path else None
    return build_from_receipt(receipt, manifest)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('render'); sub.add_parser('check')
    bf = sub.add_parser('backfill'); bf.add_argument('file'); bf.add_argument('--overwrite', action='store_true')
    bf.add_argument('--pages', action='store_true', help='also read hand-written fact tables on report pages')

    def facts_args(x, required):
        x.add_argument('--reported-by', required=required)
        x.add_argument('--found-date')
        x.add_argument('--where', required=required)
        x.add_argument('--reproduction', choices=REPRODUCTION)
        x.add_argument('--severity', choices=SEVERITIES, required=required)
        x.add_argument('--severity-reason', required=required)
        x.add_argument('--family', required=required)
        x.add_argument('--related', nargs='+', default=[])
        x.add_argument('--chim', choices=CHIM_PART_KEYS, help='mark as a CHIM bug of this part')
        x.add_argument('--from-build', help='fill the found-in-build record from a build receipt (build.json)')
        x.add_argument('--build-name')
        for opt in ('--source-commit', '--engine-commit', '--world-commit', '--chim-version', '--chim-format'):
            x.add_argument(opt)
        x.add_argument('--unknown-reason')
        x.add_argument('--build-note')
    a = sub.add_parser('add'); a.add_argument('id'); a.add_argument('--title', required=True)
    a.add_argument('--found', required=True); a.add_argument('--status')
    a.add_argument('--tag', action='append', choices=TAGS, default=[])
    facts_args(a, True)
    s = sub.add_parser('set'); s.add_argument('id'); s.add_argument('--state', choices=STATES)
    s.add_argument('--fixed-in'); s.add_argument('--status'); s.add_argument('--owner-accepted')
    s.add_argument('--tag', action='append', choices=TAGS, default=[])
    s.add_argument('--found-in'); s.add_argument('--duplicate-of'); s.add_argument('--persists-in', nargs='+')
    facts_args(s, False)
    args = p.parse_args(argv)
    bugs = load()
    families = load_families()
    by_id = {b['id']: b for b in bugs}

    def apply_facts(b):
        for opt, key in (('reported_by', 'reported_by'), ('found_date', 'found_date'), ('where', 'where'),
                         ('reproduction', 'reproduction'), ('severity', 'severity'),
                         ('severity_reason', 'severity_reason'), ('family', 'family'),
                         ('found_in', 'found_in'), ('duplicate_of', 'duplicate_of')):
            v = getattr(args, opt, None)
            if v is not None:
                b[key] = v
        if getattr(args, 'persists_in', None):
            b['persists_in'] = args.persists_in
        if args.related:
            unknown = [r for r in args.related if r not in by_id]
            if unknown:
                raise SystemExit('unknown related IDs: ' + ' '.join(unknown))
            b['related'] = sorted(set(b.get('related') or []) | set(args.related))
            for r in args.related:
                if 'related' in by_id[r] or has_facts(by_id[r]):
                    by_id[r]['related'] = sorted(set(by_id[r].get('related') or []) | {b['id']})
        if args.chim:
            b['chim'] = args.chim
        apply_build(b)

    def apply_build(b):
        m = dict(b.get('build') or {})
        if args.from_build:
            m = read_receipt(args.from_build)
        for opt, key in (('build_name', 'name'), ('source_commit', 'source_commit'),
                         ('engine_commit', 'engine_commit'), ('world_commit', 'world_commit'),
                         ('chim_version', 'chim_version'), ('chim_format', 'chim_format'),
                         ('unknown_reason', 'unknown_reason'), ('build_note', 'note')):
            v = getattr(args, opt, None)
            if v is not None:
                m[key] = None if v == 'none' and key in ('world_commit', 'chim_version', 'chim_format') else v
        if not m:
            return
        if m.get('name') == BUILD_SOURCE and 'engine_commit' not in m and 'source_commit' in m:
            m['engine_commit'] = m['source_commit']
        for key in ('world_commit', 'chim_version', 'chim_format'):
            m.setdefault(key, None)
        if args.unknown_reason is None and m.get('unknown_reason') and \
                not any(m.get(k) == 'unknown' for k in BUILD_KEYS[:6]):
            del m['unknown_reason']
        b['build'] = m

    if args.cmd == 'add':
        if args.id in by_id:
            raise SystemExit('ID exists: ' + args.id)
        page = 'bugs/%s.md' % args.id
        b = {'id': args.id, 'title': args.title, 'state': 'open', 'fixed_in': None, 'owner_accepted': None,
             'status': args.status or 'Reported in %s; cause unknown.' % args.found,
             'report': page if (REGISTER.parent / page).is_file() else None,
             'reported_by': args.reported_by, 'found_date': args.found_date or datetime.date.today().isoformat(),
             'found_in': args.found, 'where': args.where, 'reproduction': args.reproduction or 'unknown',
             'duplicate_of': None, 'persists_in': [args.found], 'severity': args.severity,
             'severity_reason': args.severity_reason, 'family': args.family, 'related': []}
        bugs.append(b)
        by_id[b['id']] = b
        apply_facts(b)
        if args.tag:
            b['tags'] = sorted(set(args.tag))
    elif args.cmd == 'set':
        b = by_id.get(args.id)
        if b is None:
            raise SystemExit('unknown ID: ' + args.id)
        if args.state:
            b['state'] = args.state
            if args.state != 'fixed':
                b['fixed_in'] = None
        if args.fixed_in:
            b['fixed_in'] = args.fixed_in
        if args.status:
            b['status'] = args.status
        if args.owner_accepted:
            b['owner_accepted'] = args.owner_accepted
        if args.tag:
            b['tags'] = sorted(set(b.get('tags', [])) | set(args.tag))
        apply_facts(b)
        if b['state'] == 'fixed' and has_facts(b):
            b['persists_in'] = 'fixed in %s' % b['fixed_in']
        page = 'bugs/%s.md' % b['id']
        if (REGISTER.parent / page).is_file():
            b['report'] = page
    elif args.cmd == 'backfill':
        records = json.loads(Path(args.file).read_text(encoding='utf-8'))
        print('backfill: %d values written' % backfill(bugs, records, args.overwrite, args.pages))
    if args.cmd in ('add', 'render'):
        marked = mark_chim(bugs)
        for x in marked:
            print('marked %s as a CHIM bug, part %s (correct with: set %s --chim PART)'
                  % (x, by_id[x]['chim'], x))
        if marked and args.cmd == 'render':
            save([_order(b) for b in bugs])  # the marking is kept even when validation then fails
    bugs[:] = [_order(b) for b in bugs]
    errors = validate_families(families) + validate(bugs, families) + image_problems(bugs)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    new = outputs(bugs, families)
    if args.cmd == 'check':
        stale = [p.relative_to(ROOT).as_posix() for p, t in new.items()
                 if not p.is_file() or p.read_text(encoding='utf-8') != t]
        if stale:
            print('stale generated files (run tools/bug_register.py render): ' + ', '.join(stale), file=sys.stderr)
            return 1
        print('bug register ok: %d bugs, %d with report pages' % (len(bugs), sum(1 for b in bugs if b['report'])))
        return 0
    if args.cmd in ('add', 'set', 'backfill'):
        save(bugs)
    changed = 0
    for path, text in new.items():
        if not path.is_file() or path.read_text(encoding='utf-8') != text:
            path.write_text(text, encoding='utf-8', newline='\n')
            changed += 1
    print('rendered %d bugs (%d files changed)' % (len(bugs), changed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
