#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The confirmed look book (CONFIRMED-LOOKBOOK-67; docs/LOOKBOOK.md): every look and behaviour the maintainer has
confirmed in play is a page, checked on every development build before it is delivered.

The book is tests/lookbook/pages.json. A page names what was confirmed (when, on which version), the register entries
it guards, the public docs of the feature, and how it is checked:
  kind "session"   steps in the journey language of tools/journey_smoke.py (a file in tests/lookbook/), with one more
                   word: "still NAME", a screenshot of the page compared with its reference picture over the page's
                   regions. The numbers (probe / pick / expect) are the main check; the pictures are the second.
                   "expect NAME near VALUE TOL" is a number within TOL of VALUE.
  kind "journey"   steps of a journey that already runs on every build (tests/sessions/journey_opening.txt): the page
                   passes when every check of those steps passed in that journey's result on the same image
  kind "image"     a check on the image's own files (drafted here, run by the chain's image step)
  kind "gate"      a data check that runs in the gate itself (a test module of tests/, "gate_test"): no emulator; the
                   page passes when that module passes in the gate (the dialogue's answer choices against the
                   original's rules for every NPC, for example)
Every page runs in ONE emulator session where it can (all session pages after each other, each a step of one
journey, after tests/lookbook/prelude.txt); a page that stops the session is reported and the runner goes on with the
next page in a new session.

Code a page guards carries a marker (docs/LOOKBOOK.md "Marked code"):
  /* LOOKBOOK <PAGE>: confirmed by the maintainer <YYYY-MM-DD> on <version>; a change here must pass this page */
  ... the guarded lines ...
  /* LOOKBOOK <PAGE> end */
tests/lookbook/guards.json keeps each marked block's SHA-256 as the page last passed it. A change to a marked block
fails the gate (tests/test_lookbook.py) until the page has passed on an engine built with the change and the run is
recorded ("record" below), so the record names the page, the run and the image.

  lookbook.py check [--repo R]                  the book, its page files, the markers against guards.json
  lookbook.py compose OUTDIR [--pages A,B] [--from PAGE]
                                                OUTDIR/lookbook-session.txt (the session script) and
                                                OUTDIR/lookbook.json (the composed journey and its pages)
  lookbook.py judge OUT SCRIPTS:RUN [SCRIPTS:RUN ...] [--journey-result FILE]
                                                reads each session's logs and shots, compares the pictures, writes
                                                OUT/LOOKBOOK-REPORT.json and .md, prints one line per page and the last
                                                line "LOOKBOOK RESULT PASS n/n pages" or "LOOKBOOK RESULT FAIL ..."; exit 1
  lookbook.py stopped SCRIPTS RUN               the page the session stopped in, or nothing (for the runner's resume)
  lookbook.py markers                           every marked block with its page, file, lines and SHA-256
  lookbook.py record PAGE REPORT                after a PASS of PAGE in REPORT: the marked blocks of PAGE as they are
                                                now become the confirmed ones in guards.json (the run named)
  lookbook.py reference PAGE STILL RUN          the still of RUN cropped to the page's regions as its reference pictures
  lookbook.py render [--check]                  docs/lookbook/<PAGE>.md, the reference page of every page
Standard library only.
"""
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import journey_smoke as js  # noqa: E402

BOOK = 'tests/lookbook/pages.json'
GUARDS = 'tests/lookbook/guards.json'
REF_DIR = 'tests/lookbook/ref'
DOC_DIR = 'docs/lookbook'
PAGE_ID = re.compile(r'[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+')
REGISTER_ID = re.compile(r'[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+')
VERSION = re.compile(r'v\d+\.\d+\.\d+(?:-[a-z]+\d*)?')
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
KINDS = ('session', 'journey', 'image', 'gate')
PRELUDE = 'tests/lookbook/prelude.txt'
STATES = ('active', 'draft')
# the marked code: begin and end lines in any comment form (C, Python, QuakeC, assembly)
MARK_BEGIN = re.compile(r'LOOKBOOK (%s): confirmed by the maintainer (%s) on (%s); a change here must pass this page'
                        % (PAGE_ID.pattern, DATE.pattern, VERSION.pattern))
MARK_END = re.compile(r'LOOKBOOK (%s) end\b' % PAGE_ID.pattern)
MARK_ANY = re.compile(r'\bLOOKBOOK [A-Z]')
MARKED_DIRS = ('engine', 'tools', 'src')
MARKED_SUFFIXES = ('.c', '.h', '.py', '.qc', '.s', '.asm', '.i')
# the generated part of a reference page that the gate compares (the register history under it is a snapshot)
HISTORY_MARK = '<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->'


class BookError(Exception):
    pass


# ---------------------------------------------------------------------------------------------------------- the book
def load_book(root=ROOT):
    path = Path(root) / BOOK
    try:
        book = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise BookError('%s: %s' % (BOOK, e))
    if not isinstance(book, dict) or book.get('schema') != 1 or not isinstance(book.get('pages'), list):
        raise BookError('%s: schema 1 with a "pages" list' % BOOK)
    return book


def register_ids(root=ROOT):
    """Every id of the register (docs/bugs/bugs.json and its archives)."""
    ids = set()
    files = [Path(root) / 'docs/bugs/bugs.json'] + sorted((Path(root) / 'docs/bugs/archive').glob('*.json'))
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        rows = data if isinstance(data, list) else data.get('bugs') or []
        ids.update(b['id'] for b in rows if isinstance(b, dict) and b.get('id'))
    return ids


def register_entries(root=ROOT):
    out = {}
    files = [Path(root) / 'docs/bugs/bugs.json'] + sorted((Path(root) / 'docs/bugs/archive').glob('*.json'))
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        rows = data if isinstance(data, list) else data.get('bugs') or []
        for b in rows:
            if isinstance(b, dict) and b.get('id') and b['id'] not in out:
                out[b['id']] = b
    return out


def page_steps_text(page, root=ROOT):
    """The page's steps (its file in tests/lookbook/), or ''."""
    if page.get('kind') != 'session':
        return ''
    return (Path(root) / 'tests/lookbook' / page['steps']).read_text(encoding='utf-8')


STILL = re.compile(r'^\s*still\s+([a-z0-9][a-z0-9-]*)\s*$')
NEAR = re.compile(r'^(\s*expect\s+(?:known\s+%s\s+)?)([a-z][a-z0-9_]*)\s+near\s+(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*$'
                  % REGISTER_ID.pattern)


def shot_name(page_id, still):
    return 'lookbook-%s-%s' % (page_id.lower(), still)


def still_view(name):
    """The camera mode a still's name asks for ('first person' for a name with the word first, 'third person' for
    third), or None: checked BY NUMBER before the shot (the maintainer, 2026-11-18: stills named first were third-person
    views, the idle vanity camera had turned the view, and nothing checked it)."""
    words = name.split('-')
    return 'first person' if 'first' in words else 'third person' if 'third' in words else None


DOWN_WORDS = ('down', 'steep', 'photo')   # a first-person still of the hands: the view looks down at them
DOWN_PITCH = 30


def still_probes(page_id, still):
    """The probe names a still's variables are read into: view (aw_camera), worn (aw_inventory worn), local and angles
    (the state file), pitch (picked from the view probe's first-person line)."""
    key = '%s_%s' % (page_id.lower().replace('-', '_'), still.replace('-', '_'))
    return {k: '%s_%s' % (k, key) for k in ('view', 'pitch', 'worn', 'local', 'angles')}


def still_lines(page_id, still):
    """A still: its variables read first (the camera mode, what the hands hold, the place and the view's angles), the
    camera mode checked BY NUMBER for a first- or third-person still (a wrong mode fails the page: never the picture),
    the view's pitch read back and checked to look down for a first-person still of the hands (the maintainer's routine,
    2026-11-18: first person, the light in the hand, look down at the ground), then the shot."""
    p = still_probes(page_id, still)
    view = still_view(still)
    out = ['probe %s aw_camera' % p['view']]
    if view:
        out.append('expect has %s View: %s' % (p['view'], view))
    if view == 'first person':
        out.append('pick %s %s after view pitch' % (p['pitch'], p['view']))
        if any(w in still.split('-') for w in DOWN_WORDS):
            out.append('expect %s >= %d' % (p['pitch'], DOWN_PITCH))
    out += ['probe %s aw_inventory worn' % p['worn'], 'probe %s state local' % p['local'],
            'probe %s state angles' % p['angles'], 'shot %s' % shot_name(page_id, still)]
    return out


def still_caption(page_id, still, con, sta, session):
    """A still's variables as one line: version and engine (of the session), view, pitch, left and right hand, place."""
    p = still_probes(page_id, still)
    view = next((ln for ln in con.get(p['view'], []) if ln.startswith('View:')), 'View: not read')
    view = view.split(',')[0]
    pitch = js.pick_number(con.get(p['view'], []), 'after', 'view pitch')
    worn = ' '.join(con.get(p['worn'], []))
    left = re.search(r'left hand: (\S+)', worn)
    right = re.search(r'right hand: (\S+)', worn)
    return ('%s, engine %s; %s; pitch %s (angles %s); left hand %s, right hand %s; local %s' % (
        session.get('version', 'version ?'), session.get('engine', '?'), view,
        '%g' % pitch if pitch is not None else '?', sta.get(p['angles'], '?'), left.group(1) if left else '?',
        right.group(1) if right else '?', sta.get(p['local'], '?')))


def session_info(run):
    """The version (from the image's run name), the image and the engine of a session (its SESSION-REPORT.json)."""
    try:
        rep = json.loads((Path(run) / 'SESSION-REPORT.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        rep = {}
    image = str(rep.get('image', ''))
    v = re.search(r'_(v\d+\.\d+\.\d+(?:-[a-z]+\d*)?)_', image)
    engine = str(rep.get('engine_sha256', ''))[:12] or '?'
    if rep.get('engine_override'):
        engine += ' (%s)' % str(rep['engine_override']).replace('\\', '/').split('/')[-2:][0]
    else:
        engine += ' (the image\'s own)'
    return {'version': v.group(1) if v else (image or 'version ?'), 'image': image, 'engine': engine}


def page_lines(page, root=ROOT):
    """The page's steps as journey lines: stills become the page's shots, each one of a first- or third-person still
    after a check of the camera mode by number (aw_camera's "View:" line), "near" becomes two bounds, a page with a
    "known" register id has every check as a known gap of it. (lines, the stills named)."""
    lines, stills = [], []

    def own(ln):
        # the page's own checks become known gaps of its "known" register id; the camera checks never do
        return re.sub(r'^(\s*)expect\s+(?!known\b)', r'\1expect known %s ' % page['known'], ln) if page.get('known') else ln
    for raw in page_steps_text(page, root).splitlines():
        line = raw.rstrip()
        m = STILL.match(line)
        if m:
            stills.append(m.group(1))
            lines += still_lines(page['id'], m.group(1))
            continue
        m = NEAR.match(line)
        if m:
            head, name, value, tol = m.group(1), m.group(2), float(m.group(3)), float(m.group(4))
            lines += [own('%s%s >= %g' % (head, name, value - tol)), own('%s%s <= %g' % (head, name, value + tol))]
            continue
        if re.match(r'\s*(part|step)\b', line):
            raise BookError('page %s: "%s" is the look book\'s own word (one step per page, one session)'
                            % (page['id'], line.split()[0]))
        lines.append(own(line))
    return lines, stills


def check_book(book, root=ROOT):
    """Every problem of the book, as plain lines (none: the book is good)."""
    bad, seen = [], set()
    known_ids = register_ids(root)
    for n, page in enumerate(book['pages']):
        pid = page.get('id', '?') if isinstance(page, dict) else '?'
        where = 'page %d (%s)' % (n + 1, pid)
        if not isinstance(page, dict):
            bad.append('%s: not an object' % where)
            continue
        if not PAGE_ID.fullmatch(pid):
            bad.append('%s: id must be capitals and digits joined by -' % where)
        if pid in seen:
            bad.append('%s: id twice' % where)
        seen.add(pid)
        for key in ('title', 'what'):
            if not isinstance(page.get(key), str) or len(page.get(key, '').strip()) < 8:
                bad.append('%s: %s (a plain line) missing' % (where, key))
        if page.get('kind') not in KINDS:
            bad.append('%s: kind is one of %s' % (where, ', '.join(KINDS)))
        if page.get('status') not in STATES:
            bad.append('%s: status is one of %s' % (where, ', '.join(STATES)))
        conf = page.get('confirmed')
        if not isinstance(conf, list) or not conf:
            bad.append('%s: confirmed: when the maintainer confirmed it (date, version, how)' % where)
        else:
            for c in conf:
                if not (isinstance(c, dict) and DATE.fullmatch(str(c.get('date', ''))) and
                        VERSION.fullmatch(str(c.get('version', ''))) and len(str(c.get('how', ''))) >= 8):
                    bad.append('%s: a confirmation needs date YYYY-MM-DD, version vX.Y.Z[-devN] and how' % where)
        regs = page.get('register')
        if not isinstance(regs, list) or not regs:
            bad.append('%s: register: the entries it guards' % where)
        else:
            for r in regs:
                if r not in known_ids:
                    bad.append('%s: register entry %s is not in docs/bugs' % (where, r))
        if page.get('known') and page['known'] not in (regs or []):
            bad.append('%s: known %s must be one of its register entries' % (where, page['known']))
        for d in page.get('docs') or []:
            if not (Path(root) / d).exists():
                bad.append('%s: doc %s does not exist' % (where, d))
        # the affected code: the files and functions (modules) the confirmed behaviour lives in, each named function
        # found in its file (the list the marked blocks come from, and the overview shows)
        code = page.get('code')
        if not isinstance(code, list) or not code:
            bad.append('%s: code: the files and functions the confirmed behaviour lives in' % where)
        else:
            for c in code:
                f = Path(root) / str(c.get('file', '')) if isinstance(c, dict) else None
                if not f or not c.get('file') or not f.is_file():
                    bad.append('%s: code file %s does not exist' % (where, c.get('file') if isinstance(c, dict) else c))
                    continue
                text = f.read_text(encoding='utf-8', errors='replace')
                for fn in c.get('functions') or []:
                    if not re.search(r'\b%s\b' % re.escape(fn), text):
                        bad.append('%s: function %s is not in %s' % (where, fn, c['file']))
        if page.get('kind') == 'session':
            f = Path(root) / 'tests/lookbook' / str(page.get('steps', ''))
            if not page.get('steps') or not f.exists():
                bad.append('%s: steps: its file in tests/lookbook/' % where)
                continue
            try:
                lines, stills = page_lines(page, root)
                js.parse('\n'.join(['step 1 %s' % pid] + lines))
            except (BookError, js.JourneyError) as e:
                bad.append('%s: %s' % (where, e))
                continue
            declared = {s.get('name'): s for s in page.get('stills') or [] if isinstance(s, dict)}
            for s in stills:
                if s not in declared:
                    bad.append('%s: still %s has no entry in its "stills"' % (where, s))
            for name, s in declared.items():
                if name not in stills:
                    bad.append('%s: still %s is not taken in its steps' % (where, name))
                for r in s.get('regions') or []:
                    if not (isinstance(r, list) and len(r) == 4 and all(isinstance(v, int) for v in r) and
                            r[0] >= 0 and r[1] >= 0 and r[2] > 0 and r[3] > 0 and r[0] + r[2] <= 1024 and
                            r[1] + r[3] <= 768):
                        bad.append('%s: still %s region %r is not x,y,w,h inside 1024x768' % (where, name, r))
                for p in reference_files(pid, name, s, root):
                    if s.get('reference') and not p.exists():
                        bad.append('%s: still %s reference %s missing' % (where, name, p.relative_to(root)))
        elif page.get('kind') == 'journey':
            if not (Path(root) / str(page.get('journey', ''))).exists() or not page.get('journey_steps'):
                bad.append('%s: journey and journey_steps: the journey file and its step numbers' % where)
        elif page.get('kind') == 'image' and page.get('status') == 'active' and not page.get('image_check'):
            bad.append('%s: an active image page needs its image_check' % where)
        elif page.get('kind') == 'gate':
            mod = str(page.get('gate_test', ''))
            # the module's file named as a path, never a computed script name (tests/test_stage_key_coverage.py)
            if not re.fullmatch(r'tests\.test_[a-z0-9_]+', mod) or \
                    not (Path(root) / 'tests' / Path(mod.split('.', 1)[1]).with_suffix('.py')).exists():
                bad.append('%s: gate_test: the test module of tests/ that is the check (tests.test_...)' % where)
    for s in book.get('seeds') or []:
        if not isinstance(s, dict) or not s.get('what') or s.get('status') not in ('to write', 'written', 'not a page'):
            bad.append('seed %r: what and status (to write, written, not a page)' % (s.get('what') if isinstance(s, dict)
                                                                                      else s))
            continue
        if s['status'] == 'written' and s.get('page') not in seen:
            bad.append('seed "%s": written as page %s, which is not in the book' % (s['what'][:40], s.get('page')))
        for r in s.get('register') or []:
            if r not in known_ids:
                bad.append('seed "%s": register entry %s is not in docs/bugs' % (s['what'][:40], r))
    return bad


def reference_files(pid, still, entry, root=ROOT):
    """The reference picture files of a still: one per region (tests/lookbook/ref/<PAGE>/<still>-<k>.png)."""
    return [Path(root) / REF_DIR / pid / ('%s-%d.png' % (still, k + 1)) for k in range(len(entry.get('regions') or []))]


# ----------------------------------------------------------------------------------------------------- the session
def select(book, pages=None, start=None):
    """The pages to run: the active session pages (or the named ones), from START on."""
    chosen = [p for p in book['pages'] if p.get('kind') == 'session' and
              (p['id'] in pages if pages else p.get('status') == 'active')]
    if pages:
        missing = sorted(set(pages) - {p['id'] for p in chosen})
        if missing:
            raise BookError('no session page %s in the book' % ', '.join(missing))
    if start:
        ids = [p['id'] for p in chosen]
        if start not in ids:
            raise BookError('--from %s: not among the pages to run' % start)
        chosen = chosen[ids.index(start):]
    return chosen


def compose(book, chosen, root=ROOT):
    """(the journey text, the page map {step: page id}): each page one step of one part."""
    text, pages = ['# generated by tools/lookbook.py from %s; do not edit' % BOOK], {}
    text += [ln.rstrip() for ln in (Path(root) / PRELUDE).read_text(encoding='utf-8').splitlines()
             if ln.strip() and not ln.lstrip().startswith('#')]
    for n, page in enumerate(chosen, 1):
        lines, _ = page_lines(page, root)
        text.append('step %d %s' % (n, page['id']))
        text += lines
        pages[n] = page['id']
    text.append('step %d end of the book' % (len(chosen) + 1))
    text.append('wait 2')
    return '\n'.join(text) + '\n', pages


def write_session(book, outdir, pages=None, start=None, root=ROOT):
    chosen = select(book, pages, start)
    if not chosen:
        raise BookError('no page to run')
    text, page_map = compose(book, chosen, root)
    journey = js.parse(text)
    if len(journey['parts']) != 1:
        raise BookError('a look book session is one part')
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    head = ['# generated by tools/lookbook.py: pages %s; do not edit' % ' '.join(p['id'] for p in chosen)]
    (out / 'lookbook-session.txt').write_text('\n'.join(head + journey['parts'][0]['lines']) + '\n', encoding='utf-8',
                                              newline='\n')
    (out / 'lookbook-journey.txt').write_text(text, encoding='utf-8', newline='\n')
    (out / 'lookbook.json').write_text(json.dumps({
        'journey': journey, 'pages': {str(k): v for k, v in page_map.items()},
        'stills': {p['id']: p.get('stills') or [] for p in chosen}}, indent=1) + '\n', encoding='utf-8', newline='\n')
    return [p['id'] for p in chosen]


def stopped_page(scripts, run):
    """The page a session stopped in (its step), else None."""
    meta = json.loads((Path(scripts) / 'lookbook.json').read_text(encoding='utf-8'))
    r = js.read_run(run)
    if r is None:
        return None
    stop = js.session_stop(r[0])
    if not stop:
        return None
    return meta['pages'].get(str(stop[0])) if stop[0] else None


# ------------------------------------------------------------------------------------------------------ pictures
def read_png(path):
    """(width, height, rows of RGB bytes) of an 8-bit, non-interlaced PNG (grey, RGB or RGBA)."""
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('%s: not a PNG' % path)
    at, idat, w = 8, [], None
    while at < len(data):
        n, kind = struct.unpack('>I4s', data[at:at + 8])
        body = data[at + 8:at + 8 + n]
        if kind == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
            if depth != 8 or ctype not in (0, 2, 6) or interlace:
                raise ValueError('%s: only 8-bit grey, RGB or RGBA, not interlaced' % path)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
        at += 12 + n
    if w is None:
        raise ValueError('%s: no header' % path)
    bpp = {0: 1, 2: 3, 6: 4}[ctype]
    raw = zlib.decompress(b''.join(idat))
    stride = w * bpp
    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(h):
        f, line = raw[pos], bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b, c = prev[i], prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif f:
            raise ValueError('%s: filter %d' % (path, f))
        prev = line
        if bpp == 3:
            rows.append(bytes(line))
        elif bpp == 4:
            rows.append(bytes(b for i in range(0, stride, 4) for b in line[i:i + 3]))
        else:
            rows.append(bytes(v for g in line for v in (g, g, g)))
    return w, h, rows


def write_png(path, w, h, rows):
    """An RGB PNG of ROWS (h rows of w*3 bytes)."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def crop(rows, x, y, w, h):
    return [r[x * 3:(x + w) * 3] for r in rows[y:y + h]]


def compare(a_rows, b_rows, threshold=48):
    """(mean absolute difference per channel 0..255, share of pixels whose largest channel difference passes
    THRESHOLD) of two crops of one size."""
    total, changed, n = 0, 0, 0
    for ra, rb in zip(a_rows, b_rows):
        for i in range(0, min(len(ra), len(rb)), 3):
            d = (abs(ra[i] - rb[i]), abs(ra[i + 1] - rb[i + 1]), abs(ra[i + 2] - rb[i + 2]))
            total += d[0] + d[1] + d[2]
            changed += max(d) > threshold
            n += 1
    return (total / (3.0 * n) if n else 0.0), (changed / float(n) if n else 0.0)


def judge_still(page_id, entry, shots, root=ROOT):
    """One still of a page against its reference: (state, line). state PASS, FAIL, NEW (no reference yet: kept, not
    counted) or MISSING (the shot was not taken)."""
    name = entry['name']
    shot = Path(shots) / (shot_name(page_id, name) + '.png')
    refs = reference_files(page_id, name, entry, root)
    if not entry.get('reference') or not refs:
        return 'NEW', 'still %s: no reference picture yet (%s)' % (
            name, 'kept: %s' % shot.name if shot.exists() else 'and the screenshot was not taken')
    if not shot.exists():
        return 'MISSING', 'still %s: no screenshot %s' % (name, shot.name)
    try:
        w, h, rows = read_png(shot)
    except ValueError as e:
        return 'FAIL', 'still %s: %s' % (name, e)
    worst = []
    for (x, y, rw, rh), ref in zip(entry['regions'], refs):
        _, _, ref_rows = read_png(ref)
        mean, share = compare(crop(rows, x, y, rw, rh), ref_rows)
        worst.append((mean, share, (x, y, rw, rh)))
    max_mean, max_share = float(entry.get('max_mean', 12)), float(entry.get('max_changed', 0.05))
    bad = [(m, s, r) for m, s, r in worst if m > max_mean or s > max_share]
    text = '; '.join('region %s mean %.1f, %.1f %% changed' % (','.join(map(str, r)), m, 100 * s) for m, s, r in worst)
    if bad:
        return 'FAIL', 'still %s: %s (allowed mean %.1f, %.1f %% changed)' % (name, text, max_mean, 100 * max_share)
    return 'PASS', 'still %s: %s' % (name, text)


# --------------------------------------------------------------------------------------------------------- judging
STEP_LINE = re.compile(r'^(PASS|FAIL|KNOWN) step (\d+|None) \(')


def judge_session(meta, run):
    """{page id: {"checks": [lines], "fails": n, "known": n, "reached": bool}} from one session of the book."""
    journey = meta['journey']
    journey.setdefault('talks', [])
    r = js.read_run(run)
    passed, lines = js.judge(journey, [r])
    pages = {v: {'checks': [], 'fails': 0, 'known': 0, 'closed': 0, 'reached': True, 'stop': ''}
             for v in meta['pages'].values()}
    stop = js.session_stop(r[0]) if r else (0, 'the session left no logs')
    for line in lines:
        m = STEP_LINE.match(line)
        if not m:
            continue
        pid = meta['pages'].get(m.group(2))
        if pid is None:
            continue
        p = pages[pid]
        p['checks'].append(line)
        if m.group(1) == 'FAIL':
            p['fails'] += 1
            if 'not reached' in line:
                p['reached'] = False
        elif m.group(1) == 'KNOWN':
            p['known'] += 1
        elif 'passes now' in line:
            p['closed'] += 1
    if stop:
        step = stop[0]
        for k, pid in meta['pages'].items():
            if step and int(k) == step:
                pages[pid]['stop'] = 'the session stopped in this page: %s' % stop[1][:300]
            elif not step or int(k) > step:
                pages[pid]['reached'] = False
    return pages


def journey_page(page, result_text):
    """A journey page from that journey's result lines: every check of its steps must have passed."""
    lines = [ln for ln in result_text.splitlines() if re.match(r'(PASS|FAIL|KNOWN) step (%s) \(' %
                                                               '|'.join(str(s) for s in page['journey_steps']), ln)]
    fails = [ln for ln in lines if ln.startswith('FAIL')]
    return lines, fails


def judge(book, sessions, out, journey_result=None, root=ROOT):
    """sessions: [(scripts dir, run dir)] in order; a later session's result for a page wins (a resumed run)."""
    by_id = {p['id']: p for p in book['pages']}
    results, order = {}, []
    for scripts, run in sessions:
        meta = json.loads((Path(scripts) / 'lookbook.json').read_text(encoding='utf-8'))
        pages = judge_session(meta, run)
        r = js.read_run(run) or ('', '')
        con, sta, info = js.console_answers(r[1]), js.state_answers(r[0]), session_info(run)
        for k in sorted(meta['pages'], key=int):
            pid = meta['pages'][k]
            p = pages[pid]
            if pid not in order:
                order.append(pid)
            if pid in results and not p['reached'] and results[pid]['reached']:
                continue
            stills = []
            for entry in meta['stills'].get(pid) or []:
                state, line = judge_still(pid, entry, Path(run) / 'shots', root)
                # every still carries its variables (version, engine, view, pitch, what the hands hold, the place)
                stills.append({'state': state, 'line': '%s [%s]' % (line, still_caption(pid, entry['name'], con, sta, info)),
                               'shot': shot_name(pid, entry['name']) + '.png', 'session': str(run)})
            p['stills'] = stills
            p['session'] = str(run)
            results[pid] = p
    report = []
    for pid in order:
        p, page = results[pid], by_id.get(pid, {})
        still_fail = [s for s in p['stills'] if s['state'] in ('FAIL', 'MISSING') and p['reached']]
        # a stop or a page not reached counts even on a known page: the known gap is its checks, not the session
        if not p['reached']:
            state = 'NOT RUN'
        elif p['stop']:
            state = 'FAIL'
        elif page.get('known'):
            # its own checks are KNOWN lines; a FAIL line is a check outside the gap (the camera mode): it counts
            state = 'FAIL' if p['fails'] else 'KNOWN' if p['known'] else 'PASS'
        elif p['fails'] or still_fail:
            state = 'FAIL'
        else:
            state = 'PASS'
        report.append({'page': pid, 'state': state, 'title': page.get('title', ''), 'register': page.get('register', []),
                       'known': page.get('known', ''), 'checks': p['checks'], 'stills': p['stills'], 'stop': p['stop'],
                       'session': p['session']})
    if journey_result is not None:
        text = Path(journey_result).read_text(encoding='utf-8', errors='replace') if Path(journey_result).exists() else ''
        for page in book['pages']:
            if page.get('kind') != 'journey' or page.get('status') != 'active':
                continue
            lines, fails = journey_page(page, text)
            state = 'NOT RUN' if not lines else 'FAIL' if fails else 'PASS'
            report.append({'page': page['id'], 'state': state, 'title': page['title'], 'register': page['register'],
                           'known': page.get('known', ''), 'checks': lines, 'stills': [], 'stop': '',
                           'session': str(journey_result)})
    return write_report(book, report, out, root)


def write_report(book, report, out, root=ROOT):
    counted = [r for r in report if r['state'] != 'KNOWN']
    bad = [r['page'] for r in counted if r['state'] != 'PASS']
    known = [r['page'] for r in report if r['state'] == 'KNOWN']
    lines = []
    for r in report:
        lines.append('%s %s: %s%s' % (r['state'], r['page'], r['title'],
                                      ' (known gap %s)' % r['known'] if r['state'] == 'KNOWN' else
                                      ' (known gap %s closed: take the known mark out of the page)' % r['known']
                                      if r['known'] and r['state'] == 'PASS' else ''))
        for c in r['checks']:
            lines.append('    ' + c)
        for s in r['stills']:
            lines.append('    %s %s' % (s['state'], s['line']))
        if r['stop']:
            lines.append('    STOP ' + r['stop'])
    tail = ''
    if known:
        tail = '; known gaps: %s' % ', '.join(known)
    if bad:
        result = 'LOOKBOOK RESULT FAIL %d of %d pages: %s%s' % (len(bad), len(counted), ', '.join(bad), tail)
    else:
        result = 'LOOKBOOK RESULT PASS %d/%d pages%s' % (len(counted), len(counted), tail)
    lines.append(result)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'LOOKBOOK-REPORT.json').write_text(json.dumps({
        'result': result, 'pages': report,
        'blocks': [{'page': b['page'], 'file': b['file'], 'sha256': b['sha256']} for b in scan_markers(root)],
        'book_sha256': hashlib.sha256((Path(root) / BOOK).read_bytes()).hexdigest()}, indent=1) + '\n',
        encoding='utf-8', newline='\n')
    (out / 'LOOKBOOK-REPORT.md').write_text('# Look book result\n\n```\n%s\n```\n' % '\n'.join(lines), encoding='utf-8',
                                            newline='\n')
    # the stills' captions, one line each beside the pictures' names (the pictures themselves are never edited)
    caps = ['%s: %s' % (s.get('shot', '?'), s['line']) for r in report for s in r['stills']]
    (out / 'STILLS.txt').write_text('\n'.join(caps) + ('\n' if caps else ''), encoding='utf-8', newline='\n')
    return not bad, lines


# ---------------------------------------------------------------------------------------------------- marked code
def marked_files(root=ROOT):
    """The files the marks may be in: every file of the pages' "code" lists (the affected code, the maintainer's
    overview of 18 November 2026: the marker map is built from it), so a marked block always has its page's list."""
    try:
        book = load_book(root)
    except BookError:
        return []
    files = sorted({c['file'] for p in book['pages'] for c in p.get('code') or [] if isinstance(c, dict) and c.get('file')})
    return [Path(root) / f for f in files if (Path(root) / f).is_file() and Path(f).suffix in MARKED_SUFFIXES]


def block_hash(lines):
    return hashlib.sha256('\n'.join(ln.rstrip() for ln in lines).encode('utf-8')).hexdigest()


def scan_file(path, rel):
    """The marked blocks of one file: [{"page", "file", "date", "version", "first", "last", "sha256"}] and the
    problems (a begin without its end, an end without a begin, a marker that is not of the form)."""
    blocks, bad, open_ = [], [], None
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return [], ['%s: %s' % (rel, e)]
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        if not MARK_ANY.search(line):
            continue
        b, e = MARK_BEGIN.search(line), MARK_END.search(line)
        if b:
            if open_:
                bad.append('%s:%d: LOOKBOOK %s begins inside the block of %s (line %d)' % (rel, n, b.group(1),
                                                                                            open_['page'], open_['first']))
            open_ = {'page': b.group(1), 'file': rel, 'date': b.group(2), 'version': b.group(3), 'first': n}
        elif e:
            if not open_ or open_['page'] != e.group(1):
                bad.append('%s:%d: LOOKBOOK %s end without its begin' % (rel, n, e.group(1)))
                continue
            open_['last'] = n
            open_['sha256'] = block_hash(lines[open_['first']:n - 1])
            blocks.append(open_)
            open_ = None
        elif 'LOOKBOOK RESULT' not in line and 'LOOKBOOK <' not in line and 'LOOKBOOK [' not in line:
            bad.append('%s:%d: a LOOKBOOK marker not of the form "LOOKBOOK <PAGE>: confirmed by the maintainer <date> on '
                       '<version>; a change here must pass this page" / "LOOKBOOK <PAGE> end"' % (rel, n))
    if open_:
        bad.append('%s:%d: LOOKBOOK %s has no end line' % (rel, open_['first'], open_['page']))
    return blocks, bad


def scan_markers(root=ROOT, problems=None):
    out = []
    for f in marked_files(root):
        if f.resolve() == Path(__file__).resolve():
            continue
        rel = f.relative_to(root).as_posix()
        blocks, bad = scan_file(f, rel)
        out += blocks
        if problems is not None:
            problems += bad
    # the n-th block of a page in a file, for the guard records
    seen = {}
    for b in out:
        key = (b['page'], b['file'])
        b['index'] = seen.get(key, 0)
        seen[key] = b['index'] + 1
    return out


def load_guards(root=ROOT):
    path = Path(root) / GUARDS
    if not path.exists():
        return {'schema': 1, 'blocks': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not isinstance(data.get('blocks'), list):
        raise BookError('%s: schema 1 with a "blocks" list' % GUARDS)
    return data


def check_guards(book, root=ROOT):
    """(problems of the marks, the changed blocks): every marked block names a page of the book and one of its
    confirmations, has its guard record, and is as the page last passed it; every record has its block."""
    problems = []
    blocks = scan_markers(root, problems)
    pages = {p['id']: p for p in book['pages']}
    records = {(g['page'], g['file'], g.get('index', 0)): g for g in load_guards(root)['blocks']}
    changed = []
    for b in blocks:
        key = (b['page'], b['file'], b['index'])
        page = pages.get(b['page'])
        if not page:
            problems.append('%s:%d: LOOKBOOK %s is no page of the book (%s)' % (b['file'], b['first'], b['page'], BOOK))
            continue
        if not any(c.get('date') == b['date'] and c.get('version') == b['version'] for c in page.get('confirmed') or []):
            problems.append('%s:%d: LOOKBOOK %s says confirmed %s on %s, which is none of the page\'s confirmations'
                            % (b['file'], b['first'], b['page'], b['date'], b['version']))
        g = records.pop(key, None)
        if g is None:
            problems.append('%s:%d: LOOKBOOK %s has no guard record in %s (tools/lookbook.py record %s REPORT after '
                            'the page passed)' % (b['file'], b['first'], b['page'], GUARDS, b['page']))
        elif g.get('sha256') != b['sha256']:
            changed.append(dict(b, confirmed_sha256=g.get('sha256')))
    for (pid, f, i), g in sorted(records.items()):
        problems.append('%s: the guard record of LOOKBOOK %s (block %d) has no marked block: a marker was taken out '
                        '(only with the page\'s own TODO item, and the record with it)' % (f, pid, i))
    return problems, changed


def changed_message(c):
    return ('%s:%d-%d: the code LOOKBOOK %s guards has changed (confirmed by the maintainer %s on %s; SHA-256 %s, '
            'confirmed %s). Before it is merged the page must pass on an engine built with the change: run it '
            '(docs/LOOKBOOK.md "Running the book", --pages %s), then tools/lookbook.py record %s <its '
            'LOOKBOOK-REPORT.json> and commit tests/lookbook/guards.json. Its reference page: docs/lookbook/%s.md'
            % (c['file'], c['first'], c['last'], c['page'], c['date'], c['version'], c['sha256'][:12],
               str(c.get('confirmed_sha256'))[:12], c['page'], c['page'], c['page']))


def record(page_id, report_path, root=ROOT):
    """The marked blocks of PAGE_ID as they are now, recorded as confirmed: only after a PASS of that page in REPORT,
    whose run saw the same blocks."""
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    entry = next((p for p in report.get('pages', []) if p.get('page') == page_id), None)
    if not entry or entry.get('state') != 'PASS':
        raise BookError('page %s did not pass in %s (%s): nothing recorded' % (
            page_id, report_path, entry.get('state') if entry else 'not in the report'))
    now = [b for b in scan_markers(root) if b['page'] == page_id]
    seen = {(b['file'], b['sha256']) for b in report.get('blocks', []) if b.get('page') == page_id}
    stale = [b for b in now if (b['file'], b['sha256']) not in seen]
    if stale:
        raise BookError('the report was made on other code: %s (rerun the page on an engine of this tree)' % ', '.join(
            '%s:%d' % (b['file'], b['first']) for b in stale))
    guards = load_guards(root)
    keep = [g for g in guards['blocks'] if g['page'] != page_id]
    for b in now:
        keep.append({'page': page_id, 'file': b['file'], 'index': b['index'], 'sha256': b['sha256'],
                     'confirmed': {'date': b['date'], 'version': b['version']},
                     'passed': {'report': str(report_path).replace('\\', '/').split('/')[-2:],
                                'session': entry.get('session', ''), 'result': report.get('result', '')}})
    guards['blocks'] = sorted(keep, key=lambda g: (g['page'], g['file'], g['index']))
    (Path(root) / GUARDS).write_text(json.dumps(guards, indent=1) + '\n', encoding='utf-8', newline='\n')
    return len(now)


def reference(book, page_id, still, run, root=ROOT):
    page = next((p for p in book['pages'] if p['id'] == page_id), None)
    if not page:
        raise BookError('no page %s' % page_id)
    entry = next((s for s in page.get('stills') or [] if s.get('name') == still), None)
    if not entry or not entry.get('regions'):
        raise BookError('page %s has no still %s with regions' % (page_id, still))
    shot = Path(run) / 'shots' / (shot_name(page_id, still) + '.png')
    w, h, rows = read_png(shot)
    files = reference_files(page_id, still, entry, root)
    for (x, y, rw, rh), f in zip(entry['regions'], files):
        write_png(f, rw, rh, crop(rows, x, y, rw, rh))
    return files


# -------------------------------------------------------------------------------------------------- reference pages
def bug_link(rid, root=ROOT):
    """The register entry's page from docs/lookbook/ (its own report page, else the register)."""
    return '../bugs/%s.md' % rid if (Path(root) / 'docs/bugs' / ('%s.md' % rid)).exists() else '../BUGS.md'


def render_page(page, blocks, entries, version, root=ROOT):
    out = ['# Look book page %s' % page['id'], '',
           '_Generated from tests/lookbook/pages.json with AmiWind v%s._' % version, '',
           page['title'] + '.', '', '## What the maintainer confirmed', '', page['what'], '']
    for c in page['confirmed']:
        out.append('- %s, on %s: %s' % (c['date'], c['version'], c['how']))
    out += ['', '## How it is checked', '']
    if page['kind'] == 'session':
        out.append('A scripted session step of the look book (`tests/lookbook/%s`), run with every other page in one '
                   'emulator session on every development build before it is delivered. Its numbers are the check; '
                   'its pictures are compared with their references where it has them.' % page['steps'])
        if page.get('stills'):
            out.append('')
        for s in page.get('stills') or []:
            out.append('- picture `%s`: %s' % (s['name'], s.get('what', '')))
    elif page['kind'] == 'journey':
        out.append('The checks of steps %s of `%s`, which runs on every development build.'
                   % (', '.join(str(s) for s in page['journey_steps']), page['journey']))
    else:
        out.append(page.get('image_check') or 'A check on the image\'s own files (to be written).')
    if page.get('checks'):
        out.append('')
        for c in page['checks']:
            out.append('- %s' % c)
    out += ['', 'Status: %s%s.' % ('checked on every development build' if page['status'] == 'active' else
                                   'drafted, not run yet', '; a known gap of %s until it is fixed' % page['known']
                                   if page.get('known') else ''), '']
    out += ['## The code it lives in', '']
    for c in page.get('code') or []:
        out.append('- `%s`%s%s' % (c['file'], ': ' + ', '.join('`%s`' % f for f in c.get('functions') or [])
                                   if c.get('functions') else '', ' (%s)' % c['what'] if c.get('what') else ''))
    out += ['', '## The code it guards', '']
    mine = [b for b in blocks if b['page'] == page['id']]
    if mine:
        out.append('A change to these lines must pass this page first (`tools/lookbook.py`, tests/lookbook/guards.json):')
        out.append('')
        for b in mine:
            out.append('- `%s`, the block marked `LOOKBOOK %s` (confirmed %s on %s)' % (b['file'], page['id'], b['date'],
                                                                                      b['version']))
    else:
        out.append('No code is marked yet: the marker goes on the code once the page passes.')
    out += ['', '## Feature pages', '']
    for d in page.get('docs') or []:
        out.append('- [%s](../%s)' % (d.split('/')[-1], d[len('docs/'):] if d.startswith('docs/') else '../' + d))
    out += ['', '## Register entries', '', HISTORY_MARK, '']
    for rid in page['register']:
        b = entries.get(rid, {})
        out.append('### [%s](%s)' % (rid, bug_link(rid, root)))
        out.append('')
        out.append('%s. State: %s%s; found in %s.' % (b.get('title', '').rstrip('.'), b.get('state', '?'),
                                                      ', fixed in %s' % b['fixed_in'] if b.get('fixed_in') else '',
                                                      b.get('found_in', '?')))
        events = []
        for h in b.get('history') or []:
            events.append((str(h.get('at', '')), str(h.get('note', ''))))
        for r in b.get('regressions') or []:
            events.append((str(r.get('at', '')), 'regressed on %s (was %s in %s): %s' % (
                r.get('version', '?'), r.get('was', '?'), r.get('fixed_in', '?'), r.get('note', ''))))
        for r in b.get('reports') or []:
            events.append((str(r.get('at', '')), 'seen again on %s: %s' % (r.get('version', '?'), r.get('note', ''))))
        for c in b.get('closure') or []:
            for s in (c if isinstance(c, list) else [c]):
                if isinstance(s, dict):
                    events.append((str(s.get('when', '')), '%s: %s, %s (%s)' % (s.get('stage', ''), s.get('who', ''),
                                                                               s.get('where', ''), s.get('how', ''))))
        if events:
            out.append('')
            for when, note in sorted(events):
                out.append('- %s %s' % (when or '-', ' '.join(note.split())[:600]))
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def render_overview(book, blocks, guards, version, root=ROOT):
    """docs/lookbook/README.md: every page with its register entries, the modules it lives in, its marked blocks and
    its last recorded pass."""
    out = ['# The confirmed look book', '', '_Generated from tests/lookbook/pages.json with AmiWind v%s._' % version, '',
           'Every look and behaviour the maintainer has confirmed in play, checked on every development build before it '
           'is delivered ([LOOKBOOK.md](../LOOKBOOK.md)). One reference page per page below.', '',
           '| Page | Kind | Status | Register | Modules | Marked blocks | Last recorded pass |',
           '|---|---|---|---|---|---|---|']
    for p in book['pages']:
        mods = ', '.join('`%s`' % c['file'].split('/')[-1] for c in p.get('code') or [])
        marks = sum(1 for b in blocks if b['page'] == p['id'])
        passes = [g.get('passed', {}).get('result', '') for g in guards['blocks'] if g['page'] == p['id']]
        out.append('| [%s](%s.md) | %s | %s%s | %s | %s | %d | %s |' % (
            p['id'], p['id'], p['kind'], p['status'], ' (known gap)' if p.get('known') else '',
            ', '.join('[%s](%s)' % (r, bug_link(r, root)) for r in p['register']), mods, marks,
            passes[0][:60] if passes else '-'))
    out += ['', '## Pages to write', '', 'From the register\'s confirmations, the maintainer\'s confirmations and the '
            'regressions reported again:', '']
    for s in book.get('seeds') or []:
        if s['status'] == 'to write':
            out.append('- %s%s' % (s['what'], ' (%s)' % ', '.join('[%s](%s)' % (r, bug_link(r, root))
                                                                  for r in s['register']) if s.get('register') else ''))
    return '\n'.join(out) + '\n'


def render(book, root=ROOT, check=False):
    """Writes (or with CHECK compares, above the register history) docs/lookbook/<PAGE>.md and the overview
    docs/lookbook/README.md; the problems."""
    version = (Path(root) / 'VERSION').read_text(encoding='utf-8').strip()
    blocks, entries = scan_markers(root), register_entries(root)
    bad = []
    overview = render_overview(book, blocks, load_guards(root), version, root)
    opath = Path(root) / DOC_DIR / 'README.md'
    strip_v = lambda t: re.sub(r'_Generated from .*?with AmiWind v[^_]*_', '', t)
    if check:
        if not opath.exists() or strip_v(opath.read_text(encoding='utf-8')) != strip_v(overview):
            bad.append('%s is not the rendering of the book (tools/lookbook.py render)' % opath.relative_to(root))
    else:
        opath.parent.mkdir(parents=True, exist_ok=True)
        opath.write_text(overview, encoding='utf-8', newline='\n')
    for page in book['pages']:
        text = render_page(page, blocks, entries, version, root)
        path = Path(root) / DOC_DIR / ('%s.md' % page['id'])
        if check:
            have = path.read_text(encoding='utf-8') if path.exists() else ''
            strip = lambda t: re.sub(r'_Generated from .*?with AmiWind v[^_]*_', '', t.split(HISTORY_MARK)[0])
            if strip(have) != strip(text):
                bad.append('%s is not the rendering of its page (tools/lookbook.py render)' % path.relative_to(root))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8', newline='\n')
    if check:
        want = {'%s.md' % p['id'] for p in book['pages']} | {'README.md'}
        have = {f.name for f in (Path(root) / DOC_DIR).glob('*.md')} if (Path(root) / DOC_DIR).exists() else set()
        for extra in sorted(have - want):
            bad.append('%s/%s has no page in the book' % (DOC_DIR, extra))
    return bad


# ------------------------------------------------------------------------------------------------------------ main
def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    try:
        book = load_book()
        if cmd == 'check':
            bad = check_book(book)
            problems, changed = check_guards(book)
            bad += problems + [changed_message(c) for c in changed] + render(book, check=True)
            for line in bad:
                print('FAIL ' + line)
            print('lookbook %s: %d pages (%d active), %d seeds, %d marked blocks, %d problems' % (
                'ok' if not bad else 'FAIL', len(book['pages']),
                sum(1 for p in book['pages'] if p.get('status') == 'active'), len(book.get('seeds') or []),
                len(scan_markers()), len(bad)))
            return 1 if bad else 0
        if cmd == 'compose':
            pages = start = None
            rest = list(args[1:])
            while rest:
                k = rest.pop(0)
                if k == '--pages' and rest:
                    pages = [p for p in rest.pop(0).split(',') if p]
                elif k == '--from' and rest:
                    start = rest.pop(0)
                else:
                    raise BookError('compose OUTDIR [--pages A,B] [--from PAGE]')
            ids = write_session(book, args[0], pages, start)
            print('lookbook session: %d pages (%s) in %s' % (len(ids), ' '.join(ids), args[0]))
            return 0
        if cmd == 'judge':
            jr, sessions, rest = None, [], list(args[1:])
            while rest:
                k = rest.pop(0)
                if k == '--journey-result' and rest:
                    jr = rest.pop(0)
                else:
                    scripts, _, run = k.rpartition(':')
                    if not scripts or len(scripts) == 1:   # a Windows drive letter is no pair
                        raise BookError('judge OUT SCRIPTS:RUN ...')
                    sessions.append((scripts, run))
            ok, lines = judge(book, sessions, args[0], jr)
            for line in lines:
                print(line)
            return 0 if ok else 1
        if cmd == 'stopped':
            page = stopped_page(args[0], args[1])
            if page:
                print(page)
            return 0
        if cmd == 'markers':
            for b in scan_markers():
                print('%s %s:%d-%d confirmed %s on %s sha256 %s' % (b['page'], b['file'], b['first'], b['last'], b['date'],
                                                                     b['version'], b['sha256']))
            return 0
        if cmd == 'record':
            n = record(args[0], args[1])
            print('recorded %d marked blocks of %s as confirmed (%s)' % (n, args[0], GUARDS))
            return 0
        if cmd == 'reference':
            for f in reference(book, args[0], args[1], args[2]):
                print('reference %s' % Path(f).relative_to(ROOT))
            return 0
        if cmd == 'render':
            bad = render(book, check='--check' in args)
            for line in bad:
                print('FAIL ' + line)
            return 1 if bad else 0
    except (BookError, js.JourneyError, ValueError, OSError, IndexError) as e:
        print('LOOKBOOK RESULT FAIL %s: %s' % (cmd, e))
        return 2
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
