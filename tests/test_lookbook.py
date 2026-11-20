# SPDX-License-Identifier: GPL-3.0-only
"""tools/lookbook.py, the confirmed look book (CONFIRMED-LOOKBOOK-67; docs/LOOKBOOK.md): the book and its pages are
well formed and their reference pages rendered; the session of all pages is one journey with one step per page; the
judge passes a page whose game answers hold and fails one whose numbers miss, naming the page (the held light away
from the hand: FP-TORCH-OUT-OF-HAND-67), a page the session stopped in and the pages after it; pictures are compared
over their regions; and the code a page guards (its LOOKBOOK markers) may change only with a recorded pass of that
page: a changed block fails here, naming the page and what to run."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import lookbook as lb  # noqa: E402
import journey_smoke as js  # noqa: E402

GOOD_GRIP = ('held light: first person, aw_debug_torch (items/torch.mdl); left hand bone 21, 40 hand vertices, 120 '
             'light vertices; attach point 1.5 units from the hand, nearest vertex 0.2 units from the hand')
BAD_GRIP = GOOD_GRIP.replace('nearest vertex 0.2', 'nearest vertex 14.8')


def answers_for(journey, overrides=None):
    """A console log answering every probe of a composed journey as a good run would."""
    overrides = overrides or {}
    good = {}
    for name, pr in journey['probes'].items():
        cmd = pr['command']
        if cmd.startswith('aw_inventory worn') and name.startswith('worn_'):
            good[name] = ['  right hand: -', '  left hand: aw_debug_torch']
        elif cmd.startswith('aw_inventory worn'):
            item = {'torch': 'aw_debug_torch', 'lantern': 'light_de_lantern_02', 'candle': 'light_com_candle_01_64',
                    'robe': 'common_shirt_01 common_robe_01'}[name.split('_')[0]]
            good[name] = ['  worn slot 9: %s' % item if name.startswith('robe') else '  right hand: -',
                          '  left hand: %s' % item]
        elif cmd == 'aw_hands':
            good[name] = ['hands state 2 goal 2 frame 0 torch 1 / time 9000', 'attack button 0 latched 0']
        elif cmd == 'aw_camera held':
            good[name] = [GOOD_GRIP]
        elif cmd == 'aw_camera' and name.startswith('view_'):
            good[name] = ['View: %s person (primary first person), distance 60.0 (7.5..200.0), vanity off' % (
                'first' if '_first' in name else 'third'),
                'First-person view: the original\'s (aw_fp_view 1): its own field 74 degrees high, the arms turn 0.50 '
                'of the pitch; view pitch 40.0, arms pitch 20.0']
        elif cmd == 'aw_camera':
            good[name] = ['View: third person', 'Assembled body: 9 parts (scale 1.000 x 1.000), table t; slots 0 1 3',
                          'First-person arms: 3 parts, table x, frame 0, assembled 1 times, last 2.0 ms; slots 1 2']
        elif cmd == 'aw_pos':
            good[name] = ['position 120 340 64 / movement 3']
        elif cmd == 'aw_blockers':
            good[name] = ['position 120 340 64 / movement 3', 'dir 0 frac 1000 solid 0/0 hit none normal 0 0 0']
        else:
            good[name] = ['%s -> 1' % cmd]
    good.update(overrides)
    lines = []
    for step in journey['steps']:
        lines.append('%s STEP %d' % (js.MARK, step['step']))
        for name, pr in journey['probes'].items():
            if pr['step'] == step['step'] and pr['kind'] == 'console':
                lines.append('%s PROBE %s' % (js.MARK, name))
                lines += good[name]
    return '\n'.join(lines) + '\n'


def fake_run(d, scripts, overrides=None, result='PASS script, maps/seyda-chim.chim running, 300 s', stop_step=None):
    meta = json.loads((Path(scripts) / 'lookbook.json').read_text(encoding='utf-8'))
    run = Path(d)
    (run / 'logs').mkdir(parents=True, exist_ok=True)
    (run / 'shots').mkdir(parents=True, exist_ok=True)
    steps = []
    for s in meta['journey']['steps']:
        steps.append('10:00:00 cmd echo %s STEP %d' % (js.MARK, s['step']))
        if stop_step and s['step'] == stop_step:
            break
    steps.append('10:05:00 smoke RESULT %s' % result)
    (run / 'logs' / 'steps.log').write_text('\n'.join(steps) + '\n', encoding='utf-8')
    console = answers_for(meta['journey'], overrides)
    if stop_step:
        cut = console.index('%s STEP %d' % (js.MARK, stop_step + 1)) if '%s STEP %d' % (js.MARK, stop_step + 1) in console \
            else len(console)
        console = console[:cut]
    (run / 'logs' / 'console.log').write_text(console, encoding='utf-8')
    return run


class BookTests(unittest.TestCase):
    def test_the_book_is_well_formed(self):
        book = lb.load_book()
        self.assertEqual(lb.check_book(book), [])
        ids = [p['id'] for p in book['pages']]
        for first in ('HELD-LIGHT-IN-HAND', 'ROBE-WORN', 'TELEPORT-ARRIVALS', 'DOCK-GUARD-POST', 'INVENTORY-HINT-PER-KIND',
                      'CLIFF-RACER-WHOLE'):
            self.assertIn(first, ids)
        self.assertGreaterEqual(len(book['seeds']), 10)

    def test_every_page_has_its_rendered_reference_page(self):
        self.assertEqual(lb.render(lb.load_book(), check=True), [])

    def test_the_marked_code_is_as_its_pages_last_passed_it(self):
        problems, changed = lb.check_guards(lb.load_book())
        self.assertEqual(problems, [])
        self.assertEqual([lb.changed_message(c) for c in changed], [])

    def test_the_held_light_page_reads_the_engines_grip_line(self):
        # the page picks the number after "nearest vertex"; the engine's dbg camera held prints it there
        page = (ROOT / 'tests/lookbook/held_light_in_hand.txt').read_text(encoding='utf-8')
        self.assertIn('after nearest vertex', page)
        view = (ROOT / 'engine/aga/src/aw_view.c').read_text(encoding='utf-8')
        self.assertIn('nearest vertex %.1f units from the hand', view)
        self.assertIn('if(!Q_strcasecmp(a,"held")){held_report();return;}', view)
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('VIDEO|camera held|aw_camera|', catalogue)


class ComposeTests(unittest.TestCase):
    def test_all_active_session_pages_are_one_session(self):
        book = lb.load_book()
        with tempfile.TemporaryDirectory() as d:
            ids = lb.write_session(book, d)
            meta = json.loads((Path(d) / 'lookbook.json').read_text(encoding='utf-8'))
            self.assertEqual(len(meta['journey']['parts']), 1)
            self.assertEqual(list(meta['pages'].values()), ids)
            text = (Path(d) / 'lookbook-session.txt').read_text(encoding='utf-8')
            self.assertIn('cmd aw_debug_hors 0', text)                 # the prelude once, first
            self.assertLess(text.index('aw_debug_hors'), text.index('%s STEP 1' % js.MARK))
            self.assertIn('shot lookbook-held-light-in-hand-torch-first-down', text)
            self.assertNotIn('\nstill ', text)
            self.assertEqual([p['id'] for p in book['pages'] if p['kind'] == 'session' and p['status'] == 'active'], ids)
            self.assertNotIn('INVENTORY-HINT-PER-KIND', ids)               # a draft is not run

    def test_a_resumed_session_starts_at_the_page_after_a_stop(self):
        book = lb.load_book()
        with tempfile.TemporaryDirectory() as d:
            ids = lb.write_session(book, d, start='ROBE-WORN')
            self.assertEqual(ids[0], 'ROBE-WORN')
            self.assertNotIn('HELD-LIGHT-IN-HAND', ids)

    def test_near_and_known(self):
        page = {'id': 'X-PAGE', 'kind': 'session', 'steps': 'x.txt', 'known': 'FP-TORCH-OUT-OF-HAND-67'}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'tests/lookbook').mkdir(parents=True)
            (root / 'tests/lookbook/x.txt').write_text('probe gap aw_camera held\npick g gap after nearest vertex\n'
                                                       'expect g near 1 0.5\nstill a-b\n', encoding='utf-8')
            lines, stills = lb.page_lines(page, root)
        self.assertEqual(stills, ['a-b'])
        self.assertIn('expect known FP-TORCH-OUT-OF-HAND-67 g >= 0.5', lines)
        self.assertIn('expect known FP-TORCH-OUT-OF-HAND-67 g <= 1.5', lines)
        self.assertIn('shot lookbook-x-page-a-b', lines)

    def test_the_page_words_part_and_step_are_refused(self):
        page = {'id': 'X-PAGE', 'kind': 'session', 'steps': 'x.txt'}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'tests/lookbook').mkdir(parents=True)
            (root / 'tests/lookbook/x.txt').write_text('part B\nwait 2\n', encoding='utf-8')
            with self.assertRaises(lb.BookError):
                lb.page_lines(page, root)


class JudgeTests(unittest.TestCase):
    def run_book(self, overrides=None, known=False, mark=None, **kw):
        book = lb.load_book()
        if not known:   # the judge's own verdicts, without the book's known gaps (KnownGapTests below has them)
            for p in book['pages']:
                p.pop('known', None)
        if mark:        # (page id, register id): a known gap set by the test itself, whatever the book carries now
            next(p for p in book['pages'] if p['id'] == mark[0])['known'] = mark[1]
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = td.name
        scripts = Path(d) / 'scripts'
        lb.write_session(book, scripts)
        run = fake_run(Path(d) / 'run', scripts, overrides, **kw)
        ok, lines = lb.judge(book, [(str(scripts), str(run))], Path(d) / 'out')
        report = json.loads((Path(d) / 'out' / 'LOOKBOOK-REPORT.json').read_text(encoding='utf-8'))
        return ok, lines, report

    def test_a_good_run_passes_every_page(self):
        ok, lines, report = self.run_book()
        self.assertTrue(ok, '\n'.join(lines))
        self.assertTrue(lines[-1].startswith('LOOKBOOK RESULT PASS'), lines[-1])
        self.assertTrue(all(p['state'] == 'PASS' for p in report['pages']))
        # no reference picture yet: the stills are kept and named, not counted
        self.assertTrue(any('no reference picture yet' in s['line'] for p in report['pages'] for s in p['stills']))

    def test_a_light_away_from_the_hand_fails_its_page(self):
        ok, lines, report = self.run_book({'torch_grip_first': [BAD_GRIP]})
        self.assertFalse(ok)
        self.assertIn('LOOKBOOK RESULT FAIL 1 of', lines[-1])
        self.assertIn('HELD-LIGHT-IN-HAND', lines[-1])
        page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
        self.assertEqual(page['state'], 'FAIL')
        self.assertTrue(any('torch_gap_first <= torch_gap_third+0.5' in c and 'read 14.8' in c for c in page['checks']),
                        page['checks'])
        self.assertEqual(next(p for p in report['pages'] if p['page'] == 'ROBE-WORN')['state'], 'PASS')

    def test_an_old_engine_without_the_readout_fails_the_grip_checks(self):
        usage = ['Usage: dbg camera [first | third | toggle | ... | die]']
        over = {n: usage for n in ('torch_grip_first', 'torch_grip_third', 'lantern_grip_first', 'lantern_grip_third',
                                   'candle_grip_first')}
        ok, lines, report = self.run_book(over)
        self.assertFalse(ok)
        page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
        self.assertEqual(page['state'], 'FAIL')
        self.assertTrue(any('no number' in c for c in page['checks']))

    def test_a_light_not_lit_fails_its_page(self):
        ok, lines, report = self.run_book({'torch_hands': ['hands state 0 goal 0 frame 0 torch 0 / time 9000']})
        self.assertFalse(ok)
        page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
        self.assertTrue(any('torch_lit == 1' in c and c.startswith('FAIL') for c in page['checks']))

    def test_a_stop_fails_its_page_and_the_pages_after_it_did_not_run(self):
        ok, lines, report = self.run_book(stop_step=1, result='FAIL walkto 1 2: not reached in 30 s')
        self.assertFalse(ok)
        states = {p['page']: p['state'] for p in report['pages']}
        self.assertEqual(states['HELD-LIGHT-IN-HAND'], 'FAIL')
        self.assertEqual(states['ROBE-WORN'], 'NOT RUN')
        self.assertIn('stopped in this page', next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')['stop'])

    def test_a_fall_after_a_teleport_fails_its_page(self):
        ok, lines, report = self.run_book({'viv_pos1': ['position 120 340 20 / movement 3']})
        self.assertFalse(ok)
        self.assertEqual(next(p for p in report['pages'] if p['page'] == 'TELEPORT-ARRIVALS')['state'], 'FAIL')

    def test_a_still_in_the_wrong_camera_mode_fails_its_page_by_number(self):
        # the idle vanity camera turned a "first" still into a third-person view (2026-11-18): the mode is read before
        # every first- or third-person still, and a wrong one fails the page even when it carries a known gap
        vanity = ['View: vanity orbit (primary first person), distance 60.0 (7.5..200.0), vanity on']
        for known in (False, True):
            ok, lines, report = self.run_book({'view_held_light_in_hand_candle_first_down': vanity}, known=known)
            page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
            self.assertFalse(ok)
            self.assertEqual(page['state'], 'FAIL')
            self.assertTrue(any('View: first person' in c and c.startswith('FAIL') for c in page['checks']), page['checks'])
        with tempfile.TemporaryDirectory() as d:
            lb.write_session(lb.load_book(), d)
            text = (Path(d) / 'lookbook-session.txt').read_text(encoding='utf-8')
        shot = text.index('shot lookbook-held-light-in-hand-torch-first-down')
        self.assertLess(text.rindex('JOURNEY PROBE view_held_light_in_hand_torch_first_down', 0, shot), shot)
        self.assertLess(text.rindex('JOURNEY PROBE worn_held_light_in_hand_torch_first_down', 0, shot), shot)
        self.assertIn('cmd aw_camera vanity off', text)

    def test_a_first_person_still_of_the_hands_looks_down_by_number(self):
        # the maintainer's routine, step 3: the pitch read back; a view not looking down fails the page
        level = ['View: first person (primary first person), distance 60.0, vanity off',
                 'First-person view: the original\'s (aw_fp_view 1): view pitch 0.0, arms pitch 0.0']
        ok, lines, report = self.run_book({'view_held_light_in_hand_lantern_first_steep': level}, known=True)
        page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
        self.assertFalse(ok)
        self.assertEqual(page['state'], 'FAIL')
        self.assertTrue(any('pitch_held_light_in_hand_lantern_first_steep >= 30' in c and c.startswith('FAIL')
                            for c in page['checks']), page['checks'])

    def test_every_still_line_carries_its_variables(self):
        ok, lines, report = self.run_book()
        page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
        line = next(s['line'] for s in page['stills'] if 'torch-first-down' in s['line'])
        for want in ('engine', 'View: first person', 'pitch 40', 'left hand aw_debug_torch', 'local'):
            self.assertIn(want, line)

    def test_a_known_gap_reports_and_does_not_stop(self):
        # a page with a known gap (set here by the test: HELD-LIGHT-IN-HAND carried FP-TORCH-OUT-OF-HAND-67 until its
        # fix, and the book's mark was taken out when it closed): the miss is KNOWN, not counted
        mark = ('HELD-LIGHT-IN-HAND', 'FP-TORCH-OUT-OF-HAND-67')
        ok, lines, report = self.run_book({'torch_grip_first': [BAD_GRIP]}, known=True, mark=mark)
        self.assertTrue(ok, '\n'.join(lines))
        page = next(p for p in report['pages'] if p['page'] == 'HELD-LIGHT-IN-HAND')
        self.assertEqual(page['state'], 'KNOWN')
        self.assertIn('known gaps: HELD-LIGHT-IN-HAND', lines[-1])
        # when its checks pass, the page says the gap closed
        ok, lines, report = self.run_book(known=True, mark=mark)
        self.assertTrue(any('closed: take the known mark out' in ln for ln in lines), lines)
        # a stop in a known page still fails the run
        ok, lines, report = self.run_book(known=True, mark=mark, stop_step=1,
                                          result='FAIL walkto 1 2: not reached in 30 s')
        self.assertFalse(ok)

    def test_a_journey_page_reads_the_journey_result(self):
        book = lb.load_book()
        page = next(p for p in book['pages'] if p['id'] == 'DOCK-GUARD-POST')
        good = 'PASS step 1 (the opening): expect fight_ship == 1\nPASS step 2 (x): y\nJOURNEY RESULT PASS 2/2\n'
        lines, fails = lb.journey_page(page, good)
        self.assertEqual((len(lines), fails), (1, []))
        lines, fails = lb.journey_page(page, good.replace('PASS step 1', 'FAIL step 1'))
        self.assertEqual(len(fails), 1)


class PictureTests(unittest.TestCase):
    def test_png_round_trip_and_compare(self):
        rows = [bytes((x * 7 + y) % 256 for x in range(30 * 3)) for y in range(20)]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'a.png'
            lb.write_png(p, 30, 20, rows)
            w, h, back = lb.read_png(p)
            self.assertEqual((w, h), (30, 20))
            self.assertEqual(back, rows)
            self.assertEqual(lb.compare(rows, back), (0.0, 0.0))
            other = [bytes(255 - v for v in r) for r in rows]
            mean, share = lb.compare(rows, other)
            self.assertGreater(mean, 50)
            self.assertGreater(share, 0.5)
            self.assertEqual(lb.crop(rows, 2, 3, 4, 5), [r[6:18] for r in rows[3:8]])

    def test_a_still_against_its_reference(self):
        rows = [bytes(((x // 3) * 5 + y) % 256 for x in range(40 * 3)) for y in range(30)]
        entry = {'name': 'pic', 'regions': [[10, 5, 20, 10]], 'reference': True, 'max_mean': 4, 'max_changed': 0.02}
        with tempfile.TemporaryDirectory() as d:
            root, shots = Path(d), Path(d) / 'shots'
            lb.write_png(shots / (lb.shot_name('X-PAGE', 'pic') + '.png'), 40, 30, rows)
            for f in lb.reference_files('X-PAGE', 'pic', entry, root):
                lb.write_png(f, 20, 10, lb.crop(rows, 10, 5, 20, 10))
            self.assertEqual(lb.judge_still('X-PAGE', entry, shots, root)[0], 'PASS')
            moved = [r[6:] + r[:6] for r in rows]
            lb.write_png(shots / (lb.shot_name('X-PAGE', 'pic') + '.png'), 40, 30, moved)
            state, line = lb.judge_still('X-PAGE', entry, shots, root)
            self.assertEqual(state, 'FAIL', line)
            self.assertEqual(lb.judge_still('X-PAGE', dict(entry, name='gone'), shots, root)[0], 'MISSING')


MARKED = '''int other(void){return 0;}
/* LOOKBOOK HELD-LIGHT-IN-HAND: confirmed by the maintainer 2026-11-07 on v0.0.61; a change here must pass this page */
int grip(void){return 4;}
/* LOOKBOOK HELD-LIGHT-IN-HAND end */
'''


class MarkerTests(unittest.TestCase):
    def tree(self, text=MARKED):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = Path(td.name)
        (d / 'engine/aga/src').mkdir(parents=True)
        (d / 'engine/aga/src/aw_x.c').write_text(text, encoding='utf-8')
        (d / 'tests/lookbook').mkdir(parents=True)
        book = json.loads((ROOT / lb.BOOK).read_text(encoding='utf-8'))
        # the marks are read from the files of the pages' code lists: the test file is one of the held light's
        next(p for p in book['pages'] if p['id'] == 'HELD-LIGHT-IN-HAND')['code'].append(
            {'file': 'engine/aga/src/aw_x.c', 'functions': ['grip']})
        (d / lb.BOOK).write_text(json.dumps(book), encoding='utf-8')
        return d

    def test_a_marked_block_without_its_record_and_then_recorded(self):
        d = self.tree()
        book = lb.load_book(d)
        problems, changed = lb.check_guards(book, d)
        self.assertEqual(len(problems), 1)
        self.assertIn('has no guard record', problems[0])
        report = {'result': 'LOOKBOOK RESULT PASS 1/1 pages',
                  'pages': [{'page': 'HELD-LIGHT-IN-HAND', 'state': 'PASS', 'session': 'run1'}],
                  'blocks': [{'page': b['page'], 'file': b['file'], 'sha256': b['sha256']} for b in lb.scan_markers(d)]}
        (d / 'r').mkdir()
        (d / 'r' / 'LOOKBOOK-REPORT.json').write_text(json.dumps(report), encoding='utf-8')
        self.assertEqual(lb.record('HELD-LIGHT-IN-HAND', d / 'r' / 'LOOKBOOK-REPORT.json', d), 1)
        self.assertEqual(lb.check_guards(book, d), ([], []))

    def test_a_change_to_the_marked_block_fails_naming_the_page(self):
        d = self.tree()
        book = lb.load_book(d)
        block = lb.scan_markers(d)[0]
        (d / lb.GUARDS).write_text(json.dumps({'schema': 1, 'blocks': [
            {'page': block['page'], 'file': block['file'], 'index': 0, 'sha256': block['sha256']}]}), encoding='utf-8')
        self.assertEqual(lb.check_guards(book, d), ([], []))
        (d / 'engine/aga/src/aw_x.c').write_text(MARKED.replace('return 4;', 'return 9;'), encoding='utf-8')
        problems, changed = lb.check_guards(book, d)
        self.assertEqual(problems, [])
        self.assertEqual(len(changed), 1)
        msg = lb.changed_message(changed[0])
        self.assertIn('LOOKBOOK HELD-LIGHT-IN-HAND', msg)
        self.assertIn('--pages HELD-LIGHT-IN-HAND', msg)
        self.assertIn('docs/lookbook/HELD-LIGHT-IN-HAND.md', msg)
        # a pass made on the old code does not record the new one
        report = {'pages': [{'page': 'HELD-LIGHT-IN-HAND', 'state': 'PASS'}],
                  'blocks': [{'page': block['page'], 'file': block['file'], 'sha256': block['sha256']}]}
        (d / 'old.json').write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaises(lb.BookError):
            lb.record('HELD-LIGHT-IN-HAND', d / 'old.json', d)
        # neither does a failed run
        report['pages'][0]['state'] = 'FAIL'
        report['blocks'][0]['sha256'] = lb.scan_markers(d)[0]['sha256']
        (d / 'failed.json').write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaises(lb.BookError):
            lb.record('HELD-LIGHT-IN-HAND', d / 'failed.json', d)

    def test_malformed_markers(self):
        cases = {
            MARKED.replace('/* LOOKBOOK HELD-LIGHT-IN-HAND end */\n', ''): 'has no end line',
            MARKED.replace('HELD-LIGHT-IN-HAND:', 'NO-SUCH-PAGE:').replace('HELD-LIGHT-IN-HAND end', 'NO-SUCH-PAGE end'):
                'is no page of the book',
            MARKED.replace('2026-11-07 on v0.0.61', '2026-11-09 on v0.0.63'): 'none of the page\'s confirmations',
            MARKED.replace('confirmed by the maintainer', 'checked'): 'not of the form',
        }
        for text, want in cases.items():
            d = self.tree(text)
            problems, _ = lb.check_guards(lb.load_book(d), d)
            self.assertTrue(any(want in p for p in problems), (want, problems))

    def test_marks_are_read_from_the_pages_code_lists_only(self):
        d = self.tree()
        (d / 'engine/aga/src/aw_other.c').write_text(MARKED, encoding='utf-8')
        self.assertEqual([b['file'] for b in lb.scan_markers(d)], ['engine/aga/src/aw_x.c'])

    def test_a_record_whose_block_is_gone(self):
        d = self.tree('int nothing(void){return 0;}\n')
        (d / lb.GUARDS).write_text(json.dumps({'schema': 1, 'blocks': [
            {'page': 'HELD-LIGHT-IN-HAND', 'file': 'engine/aga/src/aw_x.c', 'index': 0, 'sha256': 'x'}]}), encoding='utf-8')
        problems, _ = lb.check_guards(lb.load_book(d), d)
        self.assertTrue(any('has no marked block' in p for p in problems), problems)


if __name__ == '__main__':
    unittest.main()
