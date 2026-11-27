# SPDX-License-Identifier: GPL-3.0-only
"""The "Current state" block of docs/chim/PROGRESS_TRACKER.md, generated from the tracker's own data.

PROGRESS-TRACKER-STALE-64: the page's current state stopped at v0.0.48 while its last-updated line named the newest
version. The block is now rendered, never typed:

  python3 tools/cell_progress_state.py snapshot --from DIR/cell-progress.json   write docs/chim/progress-state.json
                                                                                 (the counts of the tracker data, no
                                                                                 cell records; run after an ingest)
  python3 tools/cell_progress_state.py render                                    write the block into the page
  python3 tools/cell_progress_state.py check                                     fail when the block differs from a
                                                                                 fresh render, or its data is from
                                                                                 another release than VERSION

Every number comes from the tracker data (the same island rows, groups and builds the Toolkit's per-land headline draws,
tools/cell_progress.py island_headlines / group_figures) and from docs/mwscript-features.json (scripting). The block says
which build the numbers were counted from. The pregate and tests/test_progress_state.py run `check`.
"""
import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

STATE = ROOT / 'docs' / 'chim' / 'progress-state.json'
PAGE = ROOT / 'docs' / 'chim' / 'PROGRESS_TRACKER.md'
MWSCRIPT = ROOT / 'docs' / 'mwscript-features.json'
FORMAT = 'aw-progress-state-1'
BEGIN = ('<!-- BEGIN GENERATED CURRENT STATE: from docs/chim/progress-state.json and docs/mwscript-features.json; '
         'run python3 tools/cell_progress_state.py render -->')
END = '<!-- END GENERATED CURRENT STATE -->'
LANDS = (('Vvardenfell', 'Vvardenfell (main game)', 1), ('Solstheim', 'Solstheim (Bloodmoon)', 2),
         ('Mournhold', 'Mournhold (Tribunal)', 3))
FIRST_BUILD_ROW = (0, 0, 49)        # builds before this are in the history tables of the page
ISLAND_KEYS = ('island', 'name', 'cells', 'done', 'percent', 'complete', 'terrain_complete', 'complete_unlit',
               'terrain_complete_unlit', 'approved', 'playtested', 'audits_passed', 'passed', 'empty_sea', 'not_started',
               'converted', 'eligible', 'map_cells', 'ocean')
BUILD_KEYS = ('label', 'built_at', 'commit', 'cells', 'land', 'sea')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
          'December']


def n(v):
    return '{:,}'.format(int(v or 0))


def pct(a, b):
    return '%.1f %%' % (100.0 * a / b) if b else '0.0 %'


def version_tuple(text):
    found = re.findall(r'\d+', str(text).split('-')[0])[:3]
    return tuple(int(x) for x in found) if len(found) == 3 else None


def release_of(text):
    t = version_tuple(text)
    return 'v%d.%d.%d' % t if t else None


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(':--' if i == 0 else '--:' for i in range(len(head))) + ' |']
    return out + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]


# --- the snapshot: the counts of the tracker data, small enough to keep in the repository ---

def snapshot(doc):
    import cell_progress as cp
    head = doc['headline']
    fig = cp.group_figures(doc)
    ir = doc.get('interior_rooms') or {}
    rooms = ir.get('rooms') or []
    islands = []
    for row in head.get('islands', []):
        keep = {k: row[k] for k in ISLAND_KEYS if k in row}
        keep['lighting'] = (row.get('lighting') or {}).get('status')
        islands.append(keep)
    builds = []
    for b in head.get('on_chim_builds', []):
        item = {k: b.get(k) for k in BUILD_KEYS}
        item['islands'] = [{'name': i['name'], 'land': i['land'], 'sea': i['sea']} for i in b.get('islands', [])]
        builds.append(item)
    interiors = {k: ir.get(k) for k in ('groups', 'islands', 'labels', 'later', 'totals') if k in ir}
    interiors['headline'] = ir.get('headline') or {}
    interiors['classic_rooms'] = [{'id': r['id'], 'island': r.get('island'), 'label': r.get('label')}
                                  for r in rooms if r.get('state') == 'room_map']
    # the unified readiness count (tools/master_completion.py): the data's own, or counted now by the same rules
    import master_completion as MC
    ready = doc.get('readiness') if (doc.get('readiness') or {}).get('format') == MC.FORMAT else MC.readiness(doc)
    return {'format': FORMAT, 'generated': doc.get('generated'), 'version_stamp': doc.get('version_stamp'),
            'eligible_release': head.get('eligible_release'), 'in_game_label': head.get('in_game_label'),
            'groups': fig['groups'], 'states': fig['states'], 'islands': islands, 'builds': builds,
            'interiors': interiors if ir else None, 'readiness': MC.summary(ready)}


def dumps(state):
    return json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


# --- the block ---

def long_date(iso):
    y, m, d = (int(x) for x in str(iso)[:10].split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def exterior_rows(state):
    rel = state.get('eligible_release') or 'the next release'
    newest = (state.get('builds') or [{}])[0]
    on_chim = {i['name']: i for i in newest.get('islands', [])}
    by_id = {i.get('island'): i for i in state.get('islands', [])}
    rows = []
    for key, label, iid in LANDS:
        isl, oc = by_id.get(iid), on_chim.get(key)
        if not isl:
            rows.append([label, 'no exterior cells in the tracker data', '', '', '', '', '', ''])
            continue
        waiting = (isl.get('complete_unlit') or 0) + (isl.get('terrain_complete_unlit') or 0)
        rows.append([label,
                     ('%s land + %s sea cells' % (n(oc['land']), n(oc['sea']))) if oc else 'not in the build',
                     '%s of %s (%s)' % (n(isl['done']), n(isl['cells']), pct(isl['done'], isl['cells'])),
                     n(isl.get('complete')), n(isl.get('terrain_complete')), n(waiting), n(isl.get('audits_passed')),
                     n(isl.get('not_started'))])
    return rel, rows


READY_LABELS = {'vvardenfell': 'Vvardenfell (main game)', 'solstheim': 'Solstheim (Bloodmoon)',
                'mournhold': 'Mournhold (Tribunal)'}


def fig(f):
    return '%s of %s (%.1f %%)' % (n(f['ready']), n(f['total']), f['percent'])


def ready_block(state):
    """The unified count per land (TOOLKIT-EXPANSION-COMPLETION-67): open terrain ready, rooms ready, total ready, the
    same three columns as the Toolkit's headline, from the same readiness section (tools/master_completion.py)."""
    r = state.get('readiness')
    if not r:
        return ['No readiness count in this snapshot: python3 tools/cell_progress_state.py snapshot --from <tracker data>.',
                '']
    rows = [[READY_LABELS.get(x['id'], x['name']), fig(x['terrain']), fig(x['rooms']), fig(x['total'])] for x in r['lands']]
    rows.append(['**All lands**', fig(r['all']['terrain']), fig(r['all']['rooms']), '**%s**' % fig(r['all']['total'])])
    out = [r['definition'], ''] + table(['Land', 'Open terrain ready', 'Rooms ready', 'Total ready'], rows) + ['']
    for x in r['lands']:
        bits = ['open terrain: %s %s' % (y['label'], n(y['count'])) for y in x['terrain']['not_ready']]
        bits += ['rooms: %s %s' % (y['label'], n(y['count'])) for y in x['rooms']['not_ready']]
        names = x['rooms'].get('not_ready_names') or []
        line = '- %s: not ready: %s.' % (x['name'], '; '.join(bits) if bits else 'none')
        if names:
            line += ' The rooms: %s.' % '; '.join(names)
        if x['rooms'].get('special'):
            # ready rooms named from the data, never a reason (TRACKER-ROOM-MAPS-NOT-READY-67)
            line += ' Special interiors, ready, in the game as room maps of our own: %s.' % '; '.join(x['rooms']['special'])
        if x['rooms'].get('as_terrain'):
            line += ' Counted once, as open terrain: %s.' % '; '.join(x['rooms']['as_terrain'])
        out.append(line)
    return out + ['']


def readme_line(state):
    """The README's progress line, from the same snapshot (the coordinator passes it on to the README's owner)."""
    import master_completion as MC
    return MC.line(state['readiness'])


def interior_block(state):
    ir = state.get('interiors')
    if not ir or not ir.get('headline'):
        return ['No interior data in the tracker data of this snapshot.', '']
    labels, head, tot = ir.get('labels') or {}, ir['headline'], ir.get('totals') or {}
    names = dict(ir.get('islands') or {})
    order = [k for k, _, _ in LANDS] + ['none']
    keys = [k for k in order if k in head] + sorted(k for k in head if k not in order)
    cols = ('on_chim_rooms', 'room_map', 'converted', 'not_started')
    rows = []
    for k in keys:
        h = head[k]
        aside = (h.get('groups') or {}).get('set_aside', 0)
        rows.append([names.get(k, k), n(h.get('total'))] + [n(h.get(c)) for c in cols] + [n(aside)])
    rows.append(['All', n(tot.get('total'))] + [n(tot.get(c)) for c in cols] +
                [n((tot.get('groups') or {}).get('set_aside'))])
    out = table(['Land', 'Rooms'] + [labels.get(c, c) for c in cols] + ['Set aside, with a reason'], rows)
    districts = sum(len(x['rooms'].get('as_terrain') or []) for x in (state.get('readiness') or {}).get('lands', []))
    if districts:
        # TRACKER-DISTRICTS-COUNTED-TWICE-67: this table keeps the door graph's view; say how it meets the Ready table
        out += ['', 'This table counts every room of the door graph by the island its entrance is on, the districts '
                'among them. The Ready table above counts each room for its master\'s land, and the %s districts a land '
                'presents as open terrain once, as open terrain; the rooms no door leads to are rooms still to build, '
                'not ready.' % n(districts)]
    reasons = Counter()
    for h in head.values():
        reasons.update(h.get('hard_reasons') or {})
    kinds = ', '.join('%s %s' % (labels.get(c, c).replace('Set aside: ', '').lower(), n(tot.get(c)))
                      for c in ('hard_case', 'teleport_only', 'no_entrance', 'test_cell') if tot.get(c))
    out += ['']
    if kinds:
        out.append('Set aside: %s.%s' % (kinds, (' Reasons (a room can have two): %s.' % ', '.join(
            '%s %s' % (k.replace('_', ' '), n(v)) for k, v in sorted(reasons.items()))) if reasons else ''))
    classic = ir.get('classic_rooms') or []
    if classic:
        out.append('Rooms that are in the game as room maps of our own, not as CHIM rooms: %s. The builder converts '
                   'them from the original cells into regular Quake maps with the opening sequence\'s own markers, and '
                   'counts them as in the game; they stay room maps until CHIM rooms keep object state.' % '; '.join(
                       r['id'] for r in classic))
    out.append('')
    for later in ir.get('later') or []:
        h = head.get(later.get('island')) or {}
        if h.get('on_chim_rooms'):
            # the batch is no longer later: its rooms are in the game (TRACKERS-MOURNHOLD-NOT-COUNTED-67)
            out.append('- %s (%s): %s of its %s rooms are in the game on CHIM rooms; %s not started yet.' % (
                later['island'], later['master'], n(h['on_chim_rooms']), n(h.get('total')), n(h.get('not_started'))))
        else:
            out.append('- %s (%s): %s.' % (later['batch'], later['master'], later['waits_for']))
    return out + ['']


def scripting_block(script_doc):
    import mwscript_features as mf
    rows = script_doc['scripts']
    st = Counter(r['state'] for r in rows)
    used = len(rows) - st['inert']
    meas = script_doc.get('measured') or {}
    out = ['Counted from the MWScript tracker ([MWScript features](../MWSCRIPT_FEATURES.md)), measured %s for AmiWind v%s '
           'with the builder\'s own compiler: %s of the %s scripts the original game uses run as scripts or are AmiWind '
           'adaptations (%s run, %s adaptations: AmiWind\'s own code does every step of the script); %s script records '
           'are bound to placed objects.' % (
               long_date(meas.get('date') or script_doc['updated']), script_doc['version'], n(st['runs'] + st['carried']),
               n(used), n(st['runs']), n(st['carried']), n(meas.get('bindings'))), '']
    out += table(['State', 'Scripts'], [(mf.LABELS[s], n(st[s])) for s in mf.STATES if s != 'inert' and st[s]])
    # MWSCRIPT-EFFECT-PARITY-69: the same per game file, and the functions' effect in play beside it, so "runs" is
    # not read as "plays as the original"
    summary = mf.script_summary(script_doc)
    out += ['', 'Per game file (not yet = every other state: own code with steps open, a function missing, not '
            'attached, not in the image, not converted):', '']
    out += table(['Game file', 'Used in the original', 'Run', 'AmiWind adaptation', 'Not yet',
                  'Not used in the original (never runs there either)'],
                 [(x['game'], n(x['used']), n(x['run']), n(x['adaptation']), n(x['not_yet']), n(x['unused']))
                  for x in summary['masters'] + [dict(summary['all'], game='**All**')]])
    f = summary['functions']
    out += ['', 'A script that runs is not yet a script that plays as the original. Of the %s functions the scripts '
            'call, %s have the original\'s effect in play in full, %s in part and %s none; %s have something seen in '
            'play so far (the rest is read from the source or kept by a test).' % (
                n(f['called']), n(f['full']), n(f['part']), n(f['none']), n(f['seen_in_play']))]
    return out + ['', '%s more scripts are not used in the original game (they never run there either: test and '
                  'example scripts, replaced versions, cut content); they are not counted toward completion and are '
                  'listed apart on that page.' % n(st['inert']), '']


def build_rows(state):
    rows = []
    for b in state.get('builds', []):
        t = version_tuple(b['label'].lstrip('v'))
        if not t or t < FIRST_BUILD_ROW:
            continue
        isl = {i['name']: i for i in b.get('islands', [])}
        v, s, m = isl.get('Vvardenfell', {}), isl.get('Solstheim', {}), isl.get('Mournhold', {})
        rows.append([b['label'], str(b['built_at'])[:10], '%s + %s' % (n(v.get('land')), n(v.get('sea'))),
                     '%s + %s' % (n(s.get('land')), n(s.get('sea'))), '%s + %s' % (n(m.get('land')), n(m.get('sea'))),
                     n(b['cells'])])
    return rows


def building_note(label, version):
    """The sentence after the newest ingested build's date, or '' when none is needed. The newest ingested build of
    the release in development (a dev or release-candidate build of it, or the release itself) is the build of the
    version in development, so nothing says "no ingested build" (TRACKERS-MOURNHOLD-NOT-COUNTED-67, docs review H7:
    the page called v0.0.67 in development with no ingested build while its dev3 build was ingested). Only a newest
    build of an earlier release says the version in development has none."""
    built = label.lstrip('v').split(' ')[0]
    if built == version or (release_of(built) and release_of(built) == release_of(version)):
        return ''
    return ('; the version in development, %s, has no ingested build yet, so these are the figures of the newest '
            'ingested one' % version)


def render_block(state, script_doc, version):
    newest = (state.get('builds') or [{}])[0]
    label = state.get('in_game_label') or newest.get('label') or 'none'
    late = building_note(label, version)
    rel, ext = exterior_rows(state)
    g = state.get('groups') or {}
    out = ['_Counted from the tracker data generated %s: newest ingested build **%s**, built %s%s. Every number below is '
           'read from that data and from the MWScript tracker when this block is rendered; none is typed by hand._' % (
               str(state.get('generated'))[:10], label, str(newest.get('built_at', ''))[:10], late), '',
           '### Ready, per land', ''] + ready_block(state) + [
           '### Exterior cells, per land', '',
           'The tracker draws the open world as one square per cell. "On CHIM" counts what a frame of the newest '
           'build\'s CHIM world owns; the audit columns count cells by their measured status ("done" is complete, '
           'awaiting lighting, passed or empty sea; every figure and definition: [what we count](CELL_TRACKER.md#what-we-count)). '
           'Eligible for %s: %s of %s cells.' % (rel, n(next((i['eligible'] for i in state['islands'] if i.get('island') == 1), 0)),
                                                n(next((i['cells'] for i in state['islands'] if i.get('island') == 1), 0))), '']
    out += table(['Land', 'On CHIM in the newest build', 'Done (audited)', 'Fully approved cells', 'Fully approved terrain',
                  'Awaiting lighting', 'Passed, something deferred', 'Not started'], ext)
    out += ['', 'Every cell of the tracker in three groups: **in the game %s**, not in the game yet %s, settled (beyond the '
            'world\'s edge, nothing to build) %s; accounted for %s of %s.' % (
                n(g.get('in_game')), n(g.get('not_in_game')), n(g.get('settled')), n(g.get('accounted_for')),
                n(g.get('cells'))), '']
    sol = {i['name']: i for i in newest.get('islands', [])}.get('Solstheim')
    if sol is not None and not sol.get('land'):
        out += ['None of Solstheim\'s land cells is on CHIM in this build.', '']
    out += ['### Interiors, per land', ''] + interior_block(state)
    out += ['### Scripting', ''] + scripting_block(script_doc)
    rows = build_rows(state)
    out += ['### Builds, newest first', '',
            'Cells on CHIM (land + sea) in each ingested build since v%s, from the tracker data; older builds are in the '
            'history of this page and on the [cell tracker](CELL_TRACKER.md).' % '.'.join(str(x) for x in FIRST_BUILD_ROW), '']
    out += table(['Build', 'Built', 'Vvardenfell', 'Solstheim', 'Mournhold', 'All cells on CHIM'], rows)
    earlier = [b for b in state.get('builds', []) if (version_tuple(b['label'].lstrip('v')) or (9, 9, 9)) < FIRST_BUILD_ROW]
    listed = [b for b in state.get('builds', []) if (version_tuple(b['label'].lstrip('v')) or (0, 0, 0)) >= FIRST_BUILD_ROW]
    if earlier and listed:
        out += ['', 'The tracker data holds no ingested build between %s and %s; the figures of v0.0.48 are in the history '
                'table below.' % (earlier[0]['label'].split(' (')[0].split(' ')[0], listed[-1]['label'].split(' (')[0].split(' ')[0])]
    return '\n'.join(x.rstrip() for x in out) + '\n'


def split_page(text):
    a, b = text.find(BEGIN), text.find(END)
    if a < 0 or b < a:
        return None
    return text[:a], text[a + len(BEGIN):b], text[b:]


def rendered_page(page_text, state, script_doc, version):
    parts = split_page(page_text)
    if not parts:
        raise ValueError('the page has no %s ... %s markers' % ('BEGIN GENERATED CURRENT STATE', 'END GENERATED CURRENT STATE'))
    head, _, tail = parts
    return head + BEGIN + '\n\n' + render_block(state, script_doc, version) + '\n' + tail


def problems(page_text, state, script_doc, version):
    out = []
    if (state or {}).get('format') != FORMAT:
        return ['docs/chim/progress-state.json is missing or not %s: python3 tools/cell_progress_state.py snapshot' % FORMAT]
    stamp = (state.get('version_stamp') or {}).get('release')
    if stamp != release_of(version) or state.get('eligible_release') != release_of(version):
        out.append('the tracker snapshot is stamped %s, the release in development (VERSION %s) is %s: re-ingest or '
                   'restamp the tracker, then python3 tools/cell_progress_state.py snapshot --from <tracker data> and render'
                   % (stamp, version, release_of(version)))
    try:
        want = rendered_page(page_text, state, script_doc, version)
    except ValueError as exc:
        return out + [str(exc)]
    if want != page_text:
        out.append('docs/chim/PROGRESS_TRACKER.md current-state block differs from a fresh render: '
                   'python3 tools/cell_progress_state.py render')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sp = sub.add_parser('snapshot')
    sp.add_argument('--from', dest='src', required=True, help='the tracker data, cell-progress.json')
    sp.add_argument('--out', default=str(STATE))
    rp = sub.add_parser('render')
    rp.add_argument('--page', default=str(PAGE))
    cp_ = sub.add_parser('check')
    cp_.add_argument('--page', default=str(PAGE))
    sub.add_parser('readme-line', help='print the README progress line from the snapshot')
    a = ap.parse_args(argv)
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    if a.cmd == 'readme-line':
        print(readme_line(json.loads(STATE.read_text(encoding='utf-8'))))
        return 0
    if a.cmd == 'snapshot':
        doc = json.loads(Path(a.src).read_text(encoding='utf-8'))
        Path(a.out).write_text(dumps(snapshot(doc)), encoding='utf-8', newline='\n')
        print('wrote %s' % a.out)
        return 0
    state = json.loads(STATE.read_text(encoding='utf-8'))
    script_doc = json.loads(MWSCRIPT.read_text(encoding='utf-8'))
    page = Path(a.page)
    text = page.read_text(encoding='utf-8')
    if a.cmd == 'render':
        new = rendered_page(text, state, script_doc, version)
        today = datetime.date.today()
        new = re.sub(r'^_Last updated with AmiWind v[^ ]+ \([^)]*\)\._$',
                     '_Last updated with AmiWind v%s (%d %s %d)._' % (version, today.day, MONTHS[today.month - 1], today.year),
                     new, count=1, flags=re.M) if new != text else new
        page.write_text(new, encoding='utf-8', newline='\n')
        print('rendered %s (%s)' % (page, 'changed' if new != text else 'unchanged'))
        return 0
    found = problems(text, state, script_doc, version)
    for p in found:
        print('PROGRESS STATE: ' + p)
    print('progress state check: %s' % ('FAIL' if found else 'ok'))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
