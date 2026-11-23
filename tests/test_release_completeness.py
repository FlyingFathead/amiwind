# SPDX-License-Identifier: GPL-3.0-only
"""The completeness check (tools/release_completeness.py, RELEASE-GATE-COMPLETENESS-LOST-67): a release candidate or final
is refused while any exterior cell, interior cell or load door of a shipped master is missing from the build, or the two
trackers' counts differ, unless the approval ledger names that one place; a development build reports the same and is
never stopped. Small synthetic masters and run folders: no game data, a few milliseconds each."""
import hashlib
import io
import json
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):      # src ends up before tools (TEST-WORKER-SYSPATH-32)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import release_completeness as RC  # noqa: E402

STRIDE = 1 << 22


# ------------------------------------------------------------------ a tiny master, written the way the game's are

def sub(tag, data):
    return struct.pack('<4sI', tag.encode('ascii'), len(data)) + data


def rec(tag, payload, flags=0):
    return struct.pack('<4sIII', tag.encode('ascii'), len(payload), 0, flags) + payload


def z(text):
    return text.encode('cp1252') + b'\0'


def tes3(masters=()):
    body = sub('HEDR', b'\0' * 300)
    for m in masters:
        body += sub('MAST', z(m)) + sub('DATA', b'\0' * 8)
    return rec('TES3', body)


def door(number, obj, dest_xy, dnam=None):
    """A load door reference: FRMR, NAME, DATA (its place), DODT (where it leads), DNAM (an interior destination)."""
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(obj)) + sub('DATA', b'\0' * 24)
    out += sub('DODT', struct.pack('<6f', dest_xy[0], dest_xy[1], 0, 0, 0, 0))
    if dnam:
        out += sub('DNAM', z(dnam))
    return out


def static(number, obj):
    return sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(obj)) + sub('DATA', b'\0' * 24)


def ext_cell(x, y, refs=b'', name='', region=''):
    body = sub('NAME', z(name)) + sub('DATA', struct.pack('<Iii', 2, x, y))
    if region:
        body += sub('RGNN', z(region))
    return rec('CELL', body + refs)


def int_cell(name, refs=b''):
    return rec('CELL', sub('NAME', z(name)) + sub('DATA', struct.pack('<Iii', 1, 0, 0)) + refs)


def base_master():
    """Two exterior cells, three rooms: a door out of (0,0) into Room A and back, a door from Room A into Room B and
    back, a test room whose only door leads into itself (one way in the original)."""
    return (tes3()
            + ext_cell(0, 0, door(1, 'door_a', (0, 0), 'Room A'), name='Town', region='Coast Region')
            + ext_cell(1, 0, static(2, 'rock'), region='Coast Region')
            + int_cell('Room A', door(3, 'door_out', (100.0, 100.0)) + door(4, 'door_b', (0, 0), 'Room B'))
            + int_cell('Room B', door(5, 'door_back', (0, 0), 'Room A'))
            + int_cell('Test Room', door(6, 'door_self', (0, 0), 'Test Room')))


def expansion_master():
    """An expansion: a new exterior cell (5,5), a new room, a door between them both ways; it also moves nothing of
    the base game (its references are its own: top byte 0)."""
    return (tes3(['Morrowind.esm'])
            + ext_cell(5, 5, door(1, 'exp_door', (0, 0), 'Exp Room'), region='Snow Region')
            + int_cell('Exp Room', door(2, 'exp_out', (5 * 8192 + 10.0, 5 * 8192 + 10.0))))


# ------------------------------------------------------------------ a tiny run folder

def awr2(rows):
    """world/regions.awr (AWR2): 64-byte head with the row count at 4, then 52 bytes a row: name, origin, core, cover."""
    head = b'AWR2' + struct.pack('<I', len(rows))
    head = head.ljust(64, b'\0')
    body = b''
    for i, (origin, core) in enumerate(rows):
        body += ('vf%04d' % i).encode().ljust(8, b'\0') + struct.pack('<3f4f4f', *origin, *core, *core)
    return head + body


def cell_row(x, y):
    """The outdoor row of one exterior cell: origin at its centre, core the cell (2048 map units a side)."""
    return ((x + .5) * 2048, (y + .5) * 2048, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0)


class Fixture:
    def __init__(self, test, masters=(('Morrowind.esm', None),)):
        self.dir = Path(tempfile.mkdtemp(prefix='aw-completeness-'))
        test.addCleanup(self.cleanup)
        self.data = self.dir / 'data'
        self.data.mkdir()
        self.sha = {}
        for name, raw in masters:
            raw = raw if raw is not None else base_master()
            (self.data / name).write_bytes(raw)
            self.sha[name] = hashlib.sha256(raw).hexdigest()
        self.run = self.dir / 'run'
        self.id1 = self.run / 'image' / 'boot' / 'id1'
        (self.id1 / 'world').mkdir(parents=True)
        (self.id1 / 'maps').mkdir()
        self.rows, self.maps, self.room_maps, self.door_rows = [], [], [], []

    def cleanup(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def exterior(self, x, y, made=True):
        self.rows.append(cell_row(x, y))
        if made:
            self.maps.append('vf%04d.chim' % (len(self.rows) - 1))

    def room(self, cell, made=True):
        name = 'r' + hashlib.sha256(cell.encode()).hexdigest()[:8]
        self.room_maps.append({'map': name, 'cell': cell})
        if made:
            self.maps.append(name + '.chim')
        return name

    def door(self, ref, obj, target=None, held=None, kind='door'):
        row = {'reference': ref, 'id': obj, 'kind': kind}
        if target is not None:
            row['target'] = target
        if held:
            row['held_back'] = held
        self.door_rows.append(row)

    def write(self):
        (self.id1 / 'world' / 'regions.awr').write_bytes(awr2(self.rows))
        for m in self.maps:
            (self.id1 / 'maps' / m).write_bytes(b'')
        img = self.run / 'image'
        (img / 'cell-numbers.json').write_text(json.dumps({'masters_sha256': self.sha, 'maps': self.room_maps}))
        (img / 'world-doors.json').write_text(json.dumps({'rows': self.door_rows, 'presented': {'built': []}}))
        (img / 'chim-towns.json').write_text('[]')
        (img / 'build.json').write_text(json.dumps({'version': '0.0.99'}))
        (self.run / 'exterior-checklist.json').write_text(json.dumps({'towns': []}))
        return self

    def complete(self):
        """Everything of base_master() in the image, every door carried."""
        self.exterior(0, 0)
        self.exterior(1, 0)
        ra, rb = self.room('Room A'), self.room('Room B')
        self.room('Test Room')
        self.door(1, 'door_a', ra)
        self.door(3, 'door_out')
        self.door(4, 'door_b', rb)
        self.door(5, 'door_back', ra)
        self.door(6, 'door_self', 'r' + hashlib.sha256(b'Test Room').hexdigest()[:8])
        return self

    def check(self, kind='final', extra=()):
        out = self.dir / 'out'
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = RC.main(['run', '--run', str(self.run), '--data-files', str(self.data), '--kind', kind,
                          '--no-trackers', '--approved', str(self.dir / 'ledger.json'), '--out', str(out)] + list(extra))
        return rc, json.loads((out / RC.REPORT_JSON).read_text()), buf.getvalue()

    def ledger(self, entries):
        (self.dir / 'ledger.json').write_text(json.dumps({'format': RC.LEDGER_FORMAT, 'approved': entries}))


class TheReleaseRefusesAMissingPlace(unittest.TestCase):
    """The refusal that was lost: until v0.0.67 a release passed with rooms of a shipped master missing (the release
    check asked only the inclusion ledger). With a room missing from the image, the release check now refuses."""

    def test_a_release_with_a_room_missing_is_refused(self):
        f = Fixture(self)
        f.complete()
        f.room_maps = [r for r in f.room_maps if r['cell'] != 'Room B']
        f.write()
        rc, result, text = f.check('final')
        self.assertEqual(rc, 1, text)
        self.assertTrue(result['refused'])
        self.assertEqual([r['name'] for r in result['masters']['Morrowind.esm']['interior']['missing']], ['Room B'])
        self.assertIn('REFUSED for a release', result['line'])

    def test_a_complete_release_passes(self):
        f = Fixture(self).complete().write()
        rc, result, text = f.check('final')
        self.assertEqual(rc, 0, text)
        self.assertEqual(result['missing'], 0)
        m = result['masters']['Morrowind.esm']
        self.assertEqual((m['exterior']['in'], m['exterior']['total'], m['interior']['in'], m['interior']['total']),
                         (2, 2, 3, 3))
        self.assertIn('complete', result['line'])

    def test_a_dev_build_reports_and_is_never_stopped(self):
        f = Fixture(self)
        f.complete()
        f.room_maps = [r for r in f.room_maps if r['cell'] != 'Room B']
        f.write()
        rc, result, _ = f.check('dev')
        self.assertEqual(rc, 0)
        self.assertFalse(result['refused'])
        # the room, and the two doors that stand in it or lead to it
        self.assertIn('3 missing: Room B; 2 load door(s)', result['line'])

    def test_the_kind_follows_the_version(self):
        self.assertEqual(RC.kind_of(None, '0.0.68-dev8'), 'dev')
        self.assertEqual(RC.kind_of(None, '0.0.68-rc1'), 'rc')
        self.assertEqual(RC.kind_of(None, '0.0.68'), 'final')


class EachPartOfTheCheck(unittest.TestCase):
    def test_a_exterior_cell_without_its_frame_map(self):
        f = Fixture(self)
        f.complete()
        f.maps.remove('vf0001.chim')          # the row of 1,0 is there, its frame map is not
        f.write()
        rc, result, _ = f.check('rc')
        self.assertEqual(rc, 1)
        self.assertEqual([r['place'] for r in result['masters']['Morrowind.esm']['exterior']['missing']], ['1,0'])
        self.assertIn('(Coast Region)', result['masters']['Morrowind.esm']['exterior']['missing'][0]['name'])

    def test_a_cell_in_a_town_core_counts_when_the_town_is_installed(self):
        f = Fixture(self)
        f.complete()
        f.maps.remove('vf0001.chim')
        f.write()
        (f.run / 'exterior-checklist.json').write_text(json.dumps({'towns': [{'owner': 'town', 'core': [2048, 0, 4096, 2048]}]}))
        (f.run / 'image' / 'chim-towns.json').write_text(json.dumps([{'town': 'town'}]))
        (f.id1 / 'maps' / 'town-chim.chim').write_bytes(b'')
        rc, result, _ = f.check('final')
        self.assertEqual(rc, 0, result['problems'])

    def test_b_interior_cell_whose_map_is_not_in_the_image(self):
        f = Fixture(self)
        f.complete()
        f.maps.remove(f.room_maps[2]['map'] + '.chim')        # Test Room: numbered, its map not in the image
        f.write()
        rc, result, _ = f.check('final')
        self.assertEqual(rc, 1)
        self.assertEqual([r['name'] for r in result['masters']['Morrowind.esm']['interior']['missing']], ['Test Room'])

    def test_c_a_door_held_back_and_a_door_whose_way_back_is_lost(self):
        f = Fixture(self)
        f.complete()
        f.door_rows = [r for r in f.door_rows if r['reference'] != 5]
        f.door(5, 'door_back', f.room_maps[0]['map'], held='its place is not planned')
        f.write()
        rc, result, _ = f.check('final')
        self.assertEqual(rc, 1)
        doors = result['masters']['Morrowind.esm']['doors']
        self.assertEqual([r['ref'] for r in doors['missing']], [5])
        self.assertIn('held back', doors['missing'][0]['why'])
        self.assertEqual([r['ref'] for r in doors['no_way_back']], [4])      # Room A -> Room B: its way back is gone

    def test_c_a_door_the_image_does_not_carry(self):
        f = Fixture(self)
        f.complete()
        f.door_rows = [r for r in f.door_rows if r['reference'] != 1]
        f.write()
        rc, result, _ = f.check('final')
        doors = result['masters']['Morrowind.esm']['doors']
        self.assertEqual([r['ref'] for r in doors['missing']], [1])
        self.assertIn('no row', doors['missing'][0]['why'])
        self.assertEqual([r['ref'] for r in doors['no_way_back']], [3])      # Room A's way out lost its way in

    def test_c_a_one_way_door_of_the_original_is_a_note(self):
        f = Fixture(self).complete().write()
        rc, result, _ = f.check('final')
        self.assertEqual(rc, 0)
        notes = result['masters']['Morrowind.esm']['doors']['one_way_in_original']
        self.assertEqual(len(notes), 1)
        self.assertIn('Test Room -> Test Room', notes[0])

    def test_c_an_expansion_door_is_keyed_by_its_master(self):
        f = Fixture(self, masters=(('Morrowind.esm', None), ('Tribunal.esm', expansion_master())))
        f.complete()
        f.exterior(5, 5)
        er = f.room('Exp Room')
        f.door(STRIDE + 1, 'exp_door', er)
        f.write()
        rc, result, text = f.check('final')
        tri = result['masters']['Tribunal.esm']
        self.assertEqual(tri['exterior']['total'], 1)
        self.assertEqual([r['ref'] for r in tri['doors']['missing']], [STRIDE + 2], text)   # its way out has no row
        f.door(STRIDE + 2, 'exp_out')
        f.write()
        rc, result, text = f.check('final')
        self.assertEqual(rc, 0, text)
        self.assertEqual(result['masters']['Tribunal.esm']['doors']['both_ways'], 2)

    def test_d_the_trackers_counts_differ(self):
        d = Path(tempfile.mkdtemp(prefix='aw-completeness-tr-'))
        self.addCleanup(__import__('shutil').rmtree, d, True)
        import master_completion as MC

        def doc(terrain, rooms):
            return {'readiness': {'format': MC.FORMAT, 'lands': [
                {'id': 'solstheim', 'terrain': {'ready': terrain[0], 'total': terrain[1]},
                 'rooms': {'ready': rooms[0], 'total': rooms[1]}}]}}
        (d / 'toolkit.json').write_text(json.dumps(doc((135, 150), (101, 101))))
        (d / 'public.json').write_text(json.dumps(doc((0, 144), (101, 101))))
        out = RC.compare_trackers(d / 'toolkit.json', d / 'public.json')
        self.assertEqual(out['differences'], ['solstheim terrain: the Toolkit 135 of 150, the public tracker 0 of 144'])
        (d / 'public.json').write_text(json.dumps(doc((135, 150), (101, 101))))
        self.assertEqual(RC.compare_trackers(d / 'toolkit.json', d / 'public.json')['differences'], [])
        self.assertTrue(RC.compare_trackers(None, d / 'public.json')['problems'])

    def test_the_masters_read_must_be_the_ones_the_build_used(self):
        f = Fixture(self).complete()
        f.sha = {'Morrowind.esm': '0' * 64}
        f.write()
        rc, result, _ = f.check('final')
        self.assertEqual(rc, 1)
        self.assertTrue(any(p.startswith('masters:') for p in result['problems']))


class TheApprovalLedger(unittest.TestCase):
    def test_the_shipped_ledger_starts_empty_and_is_valid(self):
        doc = json.loads(RC.LEDGER.read_text(encoding='utf-8'))
        self.assertEqual(doc['format'], RC.LEDGER_FORMAT)
        self.assertEqual(doc['approved'], [])
        self.assertEqual(RC.load_ledger(RC.LEDGER), ({}, []))

    def test_an_approved_place_is_not_missing(self):
        f = Fixture(self)
        f.complete()
        f.room_maps = [r for r in f.room_maps if r['cell'] != 'Room B']
        f.write()
        f.ledger([{'master': 'Morrowind.esm', 'kind': 'interior', 'place': 'Room B', 'date': '2026-11-22',
                   'reason': 'the maintainer decided it ships in the next release'},
                  {'master': 'Morrowind.esm', 'kind': 'door', 'place': 'ref 4', 'date': '2026-11-22',
                   'reason': 'the maintainer decided it ships in the next release'},
                  {'master': 'Morrowind.esm', 'kind': 'door', 'place': 'ref 5', 'date': '2026-11-22',
                   'reason': 'the maintainer decided it ships in the next release'}])
        rc, result, text = f.check('final')
        self.assertEqual(rc, 0, text)
        self.assertEqual([r['name'] for r in result['masters']['Morrowind.esm']['interior']['approved']], ['Room B'])

    def test_refused_reasons_and_blanket_entries_approve_nothing(self):
        base = {'master': 'Morrowind.esm', 'kind': 'interior', 'place': 'Room B', 'date': '2026-11-22'}
        for reason in ('no entrance', 'Teleport only', 'unreachable', 'over a limit', 'over the limit'):
            d = Path(tempfile.mkdtemp(prefix='aw-completeness-l-'))
            self.addCleanup(__import__('shutil').rmtree, d, True)
            (d / 'l.json').write_text(json.dumps({'format': RC.LEDGER_FORMAT, 'approved': [dict(base, reason=reason)]}))
            entries, problems = RC.load_ledger(d / 'l.json')
            self.assertEqual(entries, {}, reason)
            self.assertTrue(problems, reason)
        for place in ('*', 'all rooms', ['Room A', 'Room B']):
            d = Path(tempfile.mkdtemp(prefix='aw-completeness-l-'))
            self.addCleanup(__import__('shutil').rmtree, d, True)
            (d / 'l.json').write_text(json.dumps({'format': RC.LEDGER_FORMAT,
                                                  'approved': [dict(base, place=place, reason='decided')]}))
            entries, problems = RC.load_ledger(d / 'l.json')
            self.assertEqual(entries, {}, place)
            self.assertTrue(problems, place)


class ThePlan(unittest.TestCase):
    def test_the_plan_names_what_a_build_will_not_contain(self):
        d = Path(tempfile.mkdtemp(prefix='aw-completeness-plan-'))
        self.addCleanup(__import__('shutil').rmtree, d, True)
        (d / 'config').mkdir()
        (d / 'data').mkdir()
        (d / 'data' / 'Morrowind.esm').write_bytes(base_master())
        (d / 'config' / 'chim-cells.json').write_text(json.dumps({'cells': [[0, 0]]}))
        (d / 'config' / 'room-batches.json').write_text(json.dumps({'batches': [
            {'rooms': [{'room': 'Room A'}, {'room': 'Room B', 'state': 'no_entrance'}]}]}))
        (d / 'VERSION').write_text('0.0.99-dev1\n')
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = RC.main(['plan', '--root', str(d), '--data-files', str(d / 'data'), '--masters', 'Morrowind.esm',
                          '--no-trackers', '--out', str(d / 'out')])
        result = json.loads((d / 'out' / RC.REPORT_JSON).read_text())
        self.assertEqual(rc, 0)                       # 0.0.99-dev1: a dev build, reported only
        m = result['masters']['Morrowind.esm']
        self.assertEqual([r['place'] for r in m['exterior']['missing']], ['1,0'])
        self.assertEqual([r['name'] for r in m['interior']['missing']], ['Test Room'])
        self.assertEqual(m['doors']['missing'][0]['ref'], 6)
        self.assertIn('completeness (plan, dev): 3 missing: 1,0 (Coast Region); Test Room; 1 load door(s)',
                      result['line'])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(RC.main(['plan', '--root', str(d), '--data-files', str(d / 'data'), '--masters',
                                      'Morrowind.esm', '--no-trackers', '--kind', 'rc']), 1)


def box(x0, y0, x1, y1):
    return {(x, y) for x in range(x0, x1) for y in range(y0, y1)}


# the 61 exterior cells the three CHIM towns own (their configs' cores; a build's CHIM regions line: "61 dropped (inside
# a town frame)"): Balmora 3 x 3, Seyda Neen 4 x 4, Vivec 6 x 6
TOWN_CELLS = box(-4, -3, -1, 0) | box(-3, -11, 1, -7) | box(1, -14, 7, -8)


class TheTownsOfThePlan(unittest.TestCase):
    """COMPLETENESS-PLAN-TOWN-CELLS-MISSING-68: the plan line of every dev9 build counted 617 places missing, the 61
    cells inside the CHIM towns' frames (the build's resolved region cells leave them out) and the 556 load doors that
    stand in them or lead to them. The plan counts a cell inside the core of a town the build makes as in, by the
    same rule as the run's exterior checklist."""

    def test_the_real_town_cores_hold_the_61_cells(self):
        import exterior_plan
        cores = exterior_plan.town_cores(['balmora', 'seyda', 'vivec_city'])
        self.assertEqual(len(TOWN_CELLS), 61)
        self.assertEqual(RC.core_cells([t['core'] for t in cores]), TOWN_CELLS)
        for x, y in TOWN_CELLS:
            self.assertTrue(RC.in_cores(x, y, [t['core'] for t in cores]))
        self.assertFalse(RC.in_cores(-1, -2, [t['core'] for t in cores]))      # beside Balmora's core

    def test_the_plan_with_the_resolved_region_cells_counts_the_towns_cells(self):
        import exterior_plan
        cores = [t['core'] for t in exterior_plan.town_cores(['balmora', 'seyda', 'vivec_city'])]
        everything = TOWN_CELLS | box(-6, -16, 9, 2)
        regions = everything - TOWN_CELLS                     # what --chim-regions-cells holds: the towns dropped
        before = RC.plan_evidence(ROOT, ['Morrowind.esm'], base_cells=regions)
        after = RC.plan_evidence(ROOT, ['Morrowind.esm'], base_cells=regions, town_cores=cores)
        self.assertEqual(TOWN_CELLS - before['ext'], TOWN_CELLS)
        self.assertEqual(everything - after['ext'], set())
        self.assertIn('CHIM towns: 61 cells inside the cores of 3 towns (61 not among the region cells)', after['notes'])

    def test_the_builds_start_line_counts_a_town_cell_and_its_door(self):
        import types
        import build
        import exterior_plan
        d = Path(tempfile.mkdtemp(prefix='aw-completeness-towns-'))
        self.addCleanup(__import__('shutil').rmtree, d, True)
        # Balmora's cell -3,-2 with a door into a room and back; the open cell 0,0
        way_out = door(3, 'door_out', (-3 * 8192 + 9.0, -2 * 8192 + 9.0))
        master = (tes3() + ext_cell(-3, -2, door(1, 'door_in', (0, 0), 'Room A'), name='Balmora')
                  + ext_cell(0, 0, static(2, 'rock')) + int_cell('Room A', way_out))
        (d / 'Morrowind.esm').write_bytes(master)
        towns = exterior_plan.town_cores(['balmora'])
        args = types.SimpleNamespace(stage='aga', miniwind=False, dry_run=False, data_files=str(d),
                                     expansion_layers={'masters': ['Morrowind.esm']}, chim_regions_cells='0,0:l',
                                     bloodmoon_solstheim_cells=None, exterior_checklist={'towns': towns})
        with redirect_stdout(io.StringIO()):
            record = build.completeness_plan_step(args)
        # Room A is in no room batch list of the repository: it and its two doors stay missing; Balmora's cell is in
        self.assertNotIn('-3,-2', record['line'])
        self.assertEqual(record['missing'], 3, record)
        args.exterior_checklist = {'towns': []}                # a build without CHIM towns: the cell is missing
        with redirect_stdout(io.StringIO()):
            self.assertIn('-3,-2 Balmora', build.completeness_plan_step(args)['line'])


class TheBuildsStartLine(unittest.TestCase):
    """tools/build.py prints the plan's line before the first stage of a full AGA build: a report, never a stop."""

    def test_the_line_is_printed_and_a_failure_to_count_never_stops_the_build(self):
        import types
        import build
        d = Path(tempfile.mkdtemp(prefix='aw-completeness-build-'))
        self.addCleanup(__import__('shutil').rmtree, d, True)
        (d / 'Morrowind.esm').write_bytes(base_master())
        args = types.SimpleNamespace(stage='aga', miniwind=False, dry_run=False, data_files=str(d),
                                     expansion_layers={'masters': ['Morrowind.esm']},
                                     chim_regions_cells='0,0:l 1,0:l', bloodmoon_solstheim_cells=None)
        out = io.StringIO()
        with redirect_stdout(out):
            record = build.completeness_plan_step(args)
        self.assertIn('Completeness of the plan', out.getvalue())
        # the build's resolved cells hold both exterior cells; the three rooms of the synthetic master are in no room
        # batch list of the repository, so they and the five doors that stand in them or lead to them are missing
        self.assertIn('completeness (plan', record['line'])
        self.assertIn('Room A', record['line'])
        self.assertEqual(record['missing'], 8, record)
        args.data_files = str(d / 'nowhere')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(build.completeness_plan_step(args)['line'], 'not counted')
        self.assertIsNone(build.completeness_plan_step(types.SimpleNamespace(stage='terrain', miniwind=False,
                                                                             dry_run=False)))


if __name__ == '__main__':
    unittest.main()
