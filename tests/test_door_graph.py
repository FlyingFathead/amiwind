# SPDX-License-Identifier: GPL-3.0-only
"""Door graph (tools/door_graph.py) and the interior tracker rows (tools/cell_progress_rooms.py).

Synthetic masters only: made-up cells, objects, scripts and meshes. No game data."""
import io
import json
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import door_graph as G  # noqa: E402
import cell_progress_rooms as RM  # noqa: E402


def sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, subs, flags=0):
    body = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def tes3(count, masters=()):
    hedr = struct.pack('<fI', 1.3, 1) + b'fixture'.ljust(32, b'\0') + b'synthetic'.ljust(256, b'\0') + \
        struct.pack('<I', count)
    out = [sub('HEDR', hedr)]
    for m in masters:
        out += [sub('MAST', z(m)), sub('DATA', struct.pack('<Q', 0))]
    return record('TES3', out)


def obj(tag, name, model, script=''):
    subs = [sub('NAME', z(name)), sub('MODL', z(model))]
    if script:
        subs.append(sub('SCRI', z(script)))
    return record(tag, subs)


def ref(number, ident, pos, dest=None, dcell=None, deleted=False):
    out = [sub('FRMR', struct.pack('<I', number)), sub('NAME', z(ident)),
           sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))]
    if dest is not None:
        out.append(sub('DODT', struct.pack('<6f', *dest, 0, 0, 0)))
    if dcell:
        out.append(sub('DNAM', z(dcell)))
    if deleted:
        out.append(sub('DELE', struct.pack('<I', 0)))
    return out


def cell(name, flags, x=0, y=0, refs=(), water=None, region=''):
    subs = [sub('NAME', z(name)), sub('DATA', struct.pack('<Iii', flags, x, y))]
    if region:
        subs.append(sub('RGNN', z(region)))
    if water is not None:
        subs.append(sub('WHGT', struct.pack('<f', water)))
    if flags & 1:
        subs.append(sub('AMBI', bytes(16)))
    for r in refs:
        subs += r
    return record('CELL', subs)


def script(name, text):
    return record('SCPT', [sub('SCHD', name.encode('ascii').ljust(32, b'\0') + bytes(20)), sub('SCTX', text.encode())])


def base_master():
    """Town (exterior 0,0) -> Hall -> Cellar; Hall -> outside; Grotto (water), Smithy (lava), Vault (teleport only),
    Attic (no way in), a Telvanni tower whose top is reached only by a high door."""
    recs = [
        obj('DOOR', 'door_load', 'd\\door_load.nif'),
        obj('STAT', 'wall', 'i\\in_wall.nif'),
        obj('STAT', 't_wall', 'i\\in_t_wall.nif'),
        obj('ACTI', 'lava_pool', 'i\\in_lava_pool.nif', 'lavadamage'),
        script('lavadamage', 'begin lavadamage\nHurtStandingActor, 30\nend'),
        script('vaultscript', 'begin vaultscript\nPositionCell 0 0 0 0 "Vault"\nend'),
        cell('Town', 0, 0, 0, region='Green Region', refs=[
            ref(1, 'door_load', (100, 100, 0), (0, 0, 10), 'Hall'),
            ref(2, 'door_load', (200, 100, 0), (0, 0, 10), 'Grotto'),
            ref(3, 'door_load', (300, 100, 0), (0, 0, 10), 'Smithy'),
            ref(4, 'door_load', (400, 100, 0), (0, 0, 10), 'Tower Foot')]),
        cell('Hall', 1, refs=[ref(10, 'wall', (0, 0, 0)), ref(11, 'door_load', (0, 0, 0), (0, 0, 5), 'Cellar'),
                              ref(12, 'door_load', (5, 5, 0), (90, 90, 0))]),
        cell('Cellar', 1, refs=[ref(20, 'wall', (0, 0, 0)), ref(21, 'door_load', (0, 0, 0), (0, 0, 5), 'Hall')]),
        cell('Grotto', 3, water=-50.0, refs=[ref(30, 'wall', (0, 0, 0))]),
        cell('Smithy', 1, refs=[ref(40, 'wall', (0, 0, 0)), ref(41, 'lava_pool', (0, 0, 0))]),
        cell('Vault', 1, refs=[ref(50, 'wall', (0, 0, 0))]),
        cell('Attic', 1, refs=[ref(60, 'wall', (0, 0, 0))]),
        cell('Tower Foot', 1, refs=[ref(70, 't_wall', (0, 0, 0)), ref(71, 't_wall', (0, 0, 0)),
                                    ref(72, 'door_load', (0, 0, 2000), (0, 0, 5), 'Tower Top')]),
        cell('Tower Top', 1, refs=[ref(80, 't_wall', (0, 0, 0)),
                                   ref(81, 'door_load', (0, 0, 0), (0, 0, 2100), 'Tower Foot')]),
    ]
    return tes3(len(recs)) + b''.join(recs)


def expansion():
    """Tribunal-like: deletes the Hall's door to the Cellar (FRMR high byte 1 = its first master) and adds a room
    reached only by a script, which leads on to a second room."""
    recs = [
        script('portscript', 'begin portscript\nPositionCell 0 0 0 0 "City Gate"\nend'),
        cell('Hall', 1, refs=[ref((1 << 24) | 11, 'door_load', (0, 0, 0), deleted=True)]),
        cell('City Gate', 1 | 0x80, refs=[ref(1, 'wall', (0, 0, 0)),
                                          ref(2, 'door_load', (0, 0, 0), (0, 0, 5), 'Palace')]),
        cell('Palace', 1, refs=[ref(3, 'wall', (0, 0, 0))]),
    ]
    return tes3(len(recs), ['Morrowind.esm']) + b''.join(recs)


class DoorGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        (self.data / 'Morrowind.esm').write_bytes(base_master())

    def tearDown(self):
        self.tmp.cleanup()

    def graph(self, jobs=1):
        warnings = []
        doc = G.build_graph(self.data, jobs, warn=warnings.append)
        return doc, {r['name']: r for r in doc['rooms']}, warnings

    def test_missing_expansions_warn_and_continue(self):
        doc, rooms, warnings = self.graph()
        self.assertEqual(doc['missing_masters'], ['Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual(len(warnings), 2)
        self.assertTrue(all('missing' in w for w in warnings))
        self.assertEqual(doc['format'], G.FORMAT)

    def test_morrowind_is_required(self):
        (self.data / 'Morrowind.esm').unlink()
        with self.assertRaises(ValueError):
            G.build_graph(self.data, 1, warn=lambda m: None)

    def test_door_kinds_and_reach(self):
        doc, rooms, _ = self.graph()
        self.assertEqual(doc['summary']['doors'], {'exterior_to_interior': 4, 'interior_to_exterior': 1,
                                                   'interior_to_interior': 4})
        self.assertEqual(rooms['Hall']['access'], 'door')
        self.assertEqual(rooms['Cellar']['depth'], 2)
        self.assertEqual(rooms['Hall']['island'], 'Vvardenfell')
        self.assertEqual(rooms['Hall']['settlement'], 'Town')
        self.assertEqual(rooms['Hall']['region'], 'Green Region')
        self.assertEqual([e['to'] for e in rooms['Hall']['exits']], ['Cellar', '0,0'])
        self.assertEqual(rooms['Vault']['access'], 'teleport_only')
        self.assertFalse(rooms['Vault']['door_in'])
        self.assertEqual(rooms['Vault']['island'], 'none')
        self.assertEqual(rooms['Attic']['access'], 'unreachable')
        self.assertEqual(doc['summary']['reachable'], 7)
        self.assertEqual(doc['summary']['unreachable'], 1)

    def test_hard_cases(self):
        doc, rooms, _ = self.graph()
        # water, lava and Levitate-only are notes since v0.0.48: those rooms are converted like any room
        self.assertEqual((rooms['Grotto']['hard'], rooms['Grotto']['notes']), ([], ['water']))
        self.assertEqual(rooms['Grotto']['water']['height'], -50.0)
        self.assertEqual((rooms['Smithy']['hard'], rooms['Smithy']['notes']), ([], ['lava']))
        self.assertEqual(rooms['Vault']['hard'], ['teleport_only'])
        self.assertEqual(rooms['Attic']['hard'], ['unreachable'])
        self.assertTrue(rooms['Tower Foot']['telvanni'])
        self.assertEqual((rooms['Tower Top']['hard'], rooms['Tower Top']['notes']), ([], ['levitate_only']))
        self.assertEqual(doc['summary']['notes'], {'lava': 1, 'levitate_only': 1, 'water': 1})
        self.assertEqual(rooms['Tower Foot']['hard'], [])
        self.assertEqual(rooms['Hall']['hard'], [])
        self.assertEqual(doc['summary']['levitate_doors'], 1)

    def test_over_limit_from_the_engine_limits(self):
        limits = G.room_limits()
        self.assertEqual(limits['placements_record_max'], 65535)
        self.assertGreater(limits['zone_room_bytes'], 0)
        room = {'kept_placements': 10, 'actors': 1, 'lights': 1, 'load_doors': 1}
        self.assertEqual(G.over_limit(room, limits, None), [])
        room['kept_placements'] = limits['placements_linked_max'] + 1
        self.assertEqual(G.over_limit(room, limits, None), ['placements'])
        sizes = {'bytes': limits['room_bytes_min_fast'] + 1,
                 'largest_model_vertexes': limits['model_vertexes_max'] + 1}
        self.assertEqual(G.over_limit(dict(room, kept_placements=1), limits, sizes), ['zone_bytes', 'model_vertexes'])
        # The need (zone bytes) decides when measured; over the 16 MiB zone but within the 32 MiB room: no limit.
        sizes = {'bytes': 1, 'need_bytes': limits['zone_room_bytes'] + 1, 'largest_model_vertexes': 1}
        self.assertEqual(G.over_limit(dict(room, kept_placements=1), limits, sizes), [])
        sizes['need_bytes'] = limits['room_bytes_min_fast'] + 1
        self.assertEqual(G.over_limit(dict(room, kept_placements=1), limits, sizes), ['zone_bytes'])
        # one model larger than any single block (the zone, one cache bank) cannot load, whatever the sum
        sizes = {'bytes': 1, 'need_bytes': 1, 'largest_model_vertexes': 1,
                 'largest_model_zone_bytes': limits['block_bytes_min_fast'] + 1}
        self.assertEqual(G.over_limit(dict(room, kept_placements=1), limits, sizes), ['model_block'])

    def test_room_memory_by_fast_ram(self):
        """CHIM-ROOM-ESTIMATE-48: a room has the whole zone (no frame-world pool) less the loading buffer, and at the
        32 MiB minimum the automatic cache bank too; the engine's rules reproduce the measured start-ups."""
        import engine_limits as EL
        limits = G.room_limits()
        zone = EL.chim_memory()['zone_kib'] * 1024
        mib = 1024 * 1024
        self.assertEqual(limits['zone_room_bytes'], zone - 32 * 1024)
        self.assertEqual(limits['min_fast_ram_mib'], 32)
        self.assertEqual(limits['room_bytes_min_fast'], zone + 7 * mib - 32 * 1024)
        # Measured: 16 MiB keeps the 11 MiB heap and no bank (0 MiB free); 32 MiB: heap 13 and 13 MiB free (the v0.0.50
        # final, FS-UAE, 24 October 2026: 14 MiB on 23 October), so a 7 MiB budget: one 7 MiB bank since the first bank
        # needs 4 MiB (none with the 8 MiB of before, CHIM-AUTO-BANK-CLIFF-51); 64 and 128 MiB: heaps 20 and 24
        # (RAM-REQUIREMENT-32MB-48's tests).
        for fast, heap, bank in ((16, 11, 0), (32, 13, 7), (64, 20, 28), (128, 24, 80)):
            plan = EL.fast_ram_memory(fast)
            self.assertEqual((plan['heap_mb'], plan['bank_bytes'] // mib), (heap, bank), fast)
        self.assertEqual(EL.fast_ram_memory(32)['free_after_heap_mib'], EL.MEASURED_FAST['free_after_heap_mib'])

    def test_store_set_in_memory(self):
        """The zone bytes of a store model come from its census counts with the target's structure sizes."""
        sizes = {'hunk': 16, 'model': 400, 'mvertex': 12, 'medge': 4, 'int': 4, 'pointer': 4, 'dclipnode': 8,
                 'mplane': 20, 'mtexinfo': 44, 'msurface': 48, 'mleaf': 48, 'dmodel': 64, 'float': 4, 'entity': 192,
                 'texture': 60}
        c = {'faces': 10, 'vertexes': 20, 'edges': 30, 'surfedges': 40, 'texinfo': 5, 'planes': 6, 'cplanes': 4,
             'nodes': 3, 'clipnodes': 7, 'textures': ['t|64|1,1,1|0']}
        arena = sum((x + 15) & ~15 for x in (240, 124, 160, 4, 56, 200, 220, 480, 40, 192, 64, 24))
        self.assertEqual(G.model_zone_bytes(c, sizes), 16 + ((400 + arena + 15) & ~15))
        meshes = {'a': {'status': 'ok', 'bytes': 100, 'vertexes': 20, 'textures': {'t|64|1,1,1|0': 5000},
                        'zone': 3000, 'texture_zone': {'t|64|1,1,1|0': 5536}}}
        s = G.store_set(['a'], meshes, placements=2, sizes=sizes)
        self.assertEqual((s['bytes'], s['zone_bytes']), (5100, 8536))
        self.assertEqual(s['need_bytes'], 8536 + 2 * G.placement_zone_bytes(sizes))
        self.assertNotIn('zone_bytes', G.store_set(['a'], meshes))

    def test_lava_under_water(self):
        """A room with water and lava is held when a pool's bed reaches the water (chim.interior.room_liquids), with
        the numbers; one it cannot read is held with the reason."""
        import lava
        with patch.object(lava, 'pools_of', lambda *a, **k: [{'top': 400.0}]), \
                patch('mwad.interior.read_interiors', lambda m, n: [{'refs': []}]), \
                patch.object(lava, 'molten_objects_of', lambda p: {}):
            self.assertIsNone(G.lava_under_water(self.data, {'master': 'Morrowind.esm', 'name': 'X'}, -50.0))
            why = G.lava_under_water(self.data, {'master': 'Morrowind.esm', 'name': 'X'}, 380.0)
            self.assertIn('lava at or under the water level', why)
        self.assertIn('not checked', G.lava_under_water(self.data, {'master': 'Morrowind.esm', 'name': 'Nowhere'}, 0.0))

    def test_expansion_merges_in_load_order(self):
        (self.data / 'Tribunal.esm').write_bytes(expansion())
        doc, rooms, warnings = self.graph()
        self.assertEqual(len(warnings), 1)
        self.assertEqual(doc['summary']['per_master'], {'Morrowind.esm': 8, 'Tribunal.esm': 2})
        self.assertEqual(rooms['Hall']['modified_by'], ['Tribunal.esm'])
        # the expansion deleted the Hall's door to the Cellar: the Cellar has no way in any more
        self.assertEqual(rooms['Cellar']['access'], 'unreachable')
        self.assertEqual(rooms['City Gate']['island'], 'Mournhold')
        self.assertEqual(rooms['City Gate']['access'], 'teleport_only')
        self.assertEqual(rooms['City Gate']['hard'], ['teleport_only', 'behaves_exterior'])
        self.assertEqual(rooms['Palace']['access'], 'teleport')
        self.assertEqual(rooms['Palace']['island'], 'Mournhold')
        self.assertEqual(rooms['Palace']['hard'], [])

    def test_parallel_ranges_match_one_range(self):
        (self.data / 'Tribunal.esm').write_bytes(expansion())
        one, _, _ = self.graph(jobs=1)
        many, _, _ = self.graph(jobs=4)
        self.assertGreater(many['timings']['ranges'], one['timings']['ranges'])
        for doc in (one, many):
            doc.pop('timings')
        self.assertEqual(json.dumps(one, sort_keys=True), json.dumps(many, sort_keys=True))

    def test_record_ranges_cut_on_record_boundaries(self):
        path = self.data / 'Morrowind.esm'
        masters, ranges = G.record_ranges(path, 5)
        self.assertEqual(masters, [])
        self.assertEqual(ranges[0][0], 0)
        self.assertEqual(ranges[-1][1], path.stat().st_size)
        for (a, b), (c, d) in zip(ranges, ranges[1:]):
            self.assertEqual(b, c)
        merged = []
        for a, b in ranges:
            merged += G.parse_range((str(path), a, b))['cells']
        self.assertEqual(len(merged), 9)

    def test_plan_batches_and_sets_aside(self):
        doc, _, _ = self.graph()
        with tempfile.TemporaryDirectory() as cfg:
            (Path(cfg) / 'rooms.json').write_text(json.dumps({'scenes': [{'cell': 'Cellar', 'map': 'cellar'}]}))
            plan = G.plan(doc, cfg, batch_rooms=1)
        s = plan['summary']
        # Hall, Cellar, Tower Foot, and since v0.0.48 the water, lava and Levitate-only rooms (Grotto, Smithy, Tower
        # Top: notes, not reasons to set them aside)
        self.assertEqual(s['ready'], 6)
        # the rooms no door reaches are a final parity batch (never split), each with its state
        self.assertEqual(s['batch_sizes'], [1, 1, 1, 1, 1, 1, 2])
        self.assertEqual(plan['batches'][0]['kind'], 'town with rooms in the game')
        self.assertEqual(s['in_game_ready'], 1)
        self.assertEqual(s['aside_reasons'], {})
        self.assertEqual(s['aside'], 0)
        self.assertEqual(s['ready_notes'], {'lava': 1, 'levitate_only': 1, 'water': 1})
        last = plan['batches'][-1]
        self.assertEqual((last['batch'], last['kind'], last['rooms']), (7, 'parity', ['Vault', 'Attic']))
        self.assertEqual([(p['room'], p['state'], p['label'], p['reasons']) for p in last['parity']],
                         [('Vault', 'teleport_only', 'teleport only', ['teleport_only']),
                          ('Attic', 'no_entrance', 'no entrance, no script', ['unreachable'])])
        self.assertEqual((s['parity'], s['parity_states']), (2, {'no_entrance': 1, 'teleport_only': 1}))
        self.assertEqual((s['every_room'], s['graph_rooms'], plan['later']), (8, 8, []))
        self.assertNotIn('Vault', [a['room'] for a in plan['aside']])
        self.assertIsNone(s['store_bytes'])               # no mesh census given
        md = G.plan_markdown(plan)
        self.assertIn('| 1 |', md)
        self.assertIn('| 7 | Attic | no entrance, no script | unreachable |', md)

    def test_plan_parity_keeps_every_room(self):
        # The expansion: its rooms go in its later batch with the reason they wait; nothing is left out.
        (self.data / 'Tribunal.esm').write_bytes(expansion())
        doc, _, _ = self.graph()
        plan = G.plan(doc, None, batch_rooms=40)
        s = plan['summary']
        self.assertEqual(s['every_room'], s['graph_rooms'])
        self.assertEqual(s['later'], {'Mournhold': 2})
        later = plan['later'][0]
        self.assertEqual((later['batch'], later['master'], later['rooms']),
                         ('later: Mournhold', 'Tribunal.esm', ['City Gate', 'Palace']))
        self.assertIn('scripts step', later['waits_for'])
        self.assertEqual([(p['room'], p['state']) for p in later['parity']], [('City Gate', 'teleport_only')])
        # the Cellar lost its door to the expansion: no door reaches it, so it joins the Vvardenfell parity batch
        self.assertIn('Cellar', plan['batches'][-1]['rooms'])
        self.assertIn('## Later batches (expansions)', G.plan_markdown(plan))

    def test_parity_states(self):
        self.assertEqual(G.parity_state({'name': 'ToddTest', 'hard': ['unreachable']}), 'test_cell')
        self.assertEqual(G.parity_state({'name': 'Draugr Test', 'hard': ['unreachable', 'water']}), 'test_cell')
        self.assertEqual(G.parity_state({'name': 'Somewhere', 'hard': ['teleport_only']}), 'teleport_only')
        self.assertEqual(G.parity_state({'name': 'Somewhere', 'hard': ['unreachable']}), 'no_entrance')
        self.assertIsNone(G.parity_state({'name': 'Somewhere', 'hard': ['water']}))
        self.assertIsNone(G.parity_state({'name': 'ToddTest', 'hard': []}))

    def test_plan_packs_small_groups_and_splits_large_ones(self):
        def room(name, town, models, region='R'):
            return {'name': name, 'island': 'Vvardenfell', 'master': 'Morrowind.esm', 'hard': [], 'settlement': town,
                    'region': region, 'depth': 1, 'kept_placements': 2, 'models': models}
        graph = {'masters': [], 'meshes': {'m1': {'bytes': 100}, 'm2': {'bytes': 50}, 'm3': {'bytes': 7}},
                 'textures': {'t1': 10, 't2': 1}, 'mesh_textures': {'m1': ['t1'], 'm2': ['t1', 't2'], 'm3': []},
                 'rooms': [room('A1', 'Big', ['m1']), room('A2', 'Big', ['m1']), room('A3', 'Big', ['m2']),
                           room('A4', 'Big', ['m1']), room('B1', 'Ruin', ['m2'], 'Q'), room('C1', 'Tomb', ['m3']),
                           room('W1', None, ['m3'])]}
        plan = G.plan(graph, None, batch_rooms=3)
        # Big (4 rooms) is a town, split evenly; a lone named ruin or tomb goes with its region; small groups share.
        self.assertEqual([(b['kind'], b['groups'], b['part'], len(b['rooms'])) for b in plan['batches']],
                         [('town', ['Big'], 1, 2), ('town', ['Big'], 2, 2), ('region', ['Q', 'R'], 0, 3)])
        self.assertEqual([b['store_growth_bytes'] for b in plan['batches']], [110, 51, 7])
        self.assertEqual(plan['summary']['store_bytes'], 168)
        self.assertIn('Q; R', G.plan_markdown(plan))

    def test_command_line_writes_the_graph(self):
        out = self.data / 'out' / 'graph.json'
        with redirect_stdout(io.StringIO()) as text:
            self.assertEqual(G.main(['graph', '--data-files', str(self.data), '--out', str(out), '--jobs', '2']), 0)
        self.assertIn('2 workers', text.getvalue())
        self.assertEqual(json.loads(out.read_text())['format'], G.FORMAT)


class TrackerRoomsTests(unittest.TestCase):
    GRAPH = {'rooms': [
        {'name': 'A', 'hard': [], 'island': 'Vvardenfell', 'master': 'Morrowind.esm', 'access': 'door'},
        {'name': 'B', 'hard': ['over_limit'], 'island': 'Vvardenfell', 'master': 'Morrowind.esm', 'access': 'door'},
        {'name': 'C', 'hard': [], 'island': 'Vvardenfell', 'master': 'Morrowind.esm', 'access': 'door'},
        {'name': 'D', 'hard': [], 'island': 'Solstheim', 'master': 'Bloodmoon.esm', 'access': 'door'},
        {'name': 'E', 'hard': ['over_limit'], 'island': 'Vvardenfell', 'master': 'Morrowind.esm', 'access': 'door'},
        {'name': 'ToddTest', 'hard': ['unreachable'], 'island': 'none', 'master': 'Morrowind.esm',
         'access': 'unreachable'},
        {'name': 'V', 'hard': ['teleport_only'], 'island': 'none', 'master': 'Morrowind.esm', 'access': 'teleport_only'},
        {'name': 'W', 'hard': ['unreachable'], 'island': 'none', 'master': 'Tribunal.esm', 'access': 'unreachable'},
        {'name': 'G', 'hard': [], 'island': 'Vvardenfell', 'master': 'Morrowind.esm', 'access': 'door',
         'entrance_exterior': '3,-4', 'settlement': 'Town'}]}

    def test_states_first_match_wins(self):
        rows = RM.rooms(self.GRAPH, in_game={'a': 'mapa', 'e': 'mape'},
                        receipts=[{'format': 'aw-chim-rooms-1', 'rooms': [{'cell': 'A'}, {'cell': 'C'}]},
                                  {'store': 'chimi', 'rooms': [{'room': 'mape'}], 'not_in_image': []}],
                        plan={'batches': [{'batch': 3, 'rooms': ['D']}, {'batch': 4, 'rooms': ['ToddTest', 'V']}],
                              'later': [{'batch': 'later: Mournhold', 'rooms': ['W']}]})
        self.assertEqual({k: r['state'] for k, r in rows.items()},
                         {'a': 'on_chim_rooms', 'b': 'hard_case', 'c': 'converted', 'd': 'not_started',
                          'e': 'on_chim_rooms', 'toddtest': 'test_cell', 'v': 'teleport_only', 'w': 'no_entrance',
                          'g': 'not_started'})
        # a build's chim-interiors.json (rows named by our map name) puts a room on CHIM rooms
        self.assertTrue(rows['e']['on_chim_rooms'])
        self.assertFalse(rows['c']['on_chim_rooms'])
        self.assertEqual(rows['b']['reasons'], ['over_limit'])
        self.assertEqual(rows['e']['reasons'], ['over_limit'])     # the reasons are kept in every state
        # a graph from before v0.0.48: water, lava and Levitate-only are notes, not reasons to set a room aside
        old = RM.rooms({'rooms': [{'name': 'Q', 'hard': ['water', 'levitate_only'], 'island': 'Vvardenfell',
                                   'master': 'Morrowind.esm', 'access': 'door'}]})
        self.assertEqual((old['q']['state'], old['q']['reasons'], old['q']['notes']),
                         ('not_started', [], ['water', 'levitate_only']))
        self.assertEqual((rows['d']['batch'], rows['v']['batch'], rows['w']['batch']), (3, 4, 'later: Mournhold'))
        self.assertEqual((rows['g']['id'], rows['g']['entrance'], rows['g']['settlement']), ('G', '3,-4', 'Town'))
        self.assertEqual({k: r['group'] for k, r in rows.items() if k in ('a', 'c', 'w')},
                         {'a': 'in_game', 'c': 'not_in_game', 'w': 'set_aside'})
        head = RM.headline(rows)
        self.assertEqual(list(head), ['Vvardenfell', 'Solstheim', 'none'])
        self.assertEqual(head['Vvardenfell']['total'], 5)
        self.assertEqual(head['Vvardenfell']['hard_case'], 1)
        self.assertEqual(head['Vvardenfell']['hard_reasons'], {'over_limit': 1})
        self.assertEqual(dict(head['Vvardenfell']['groups']), {'in_game': 2, 'not_in_game': 2, 'set_aside': 1})
        self.assertEqual(head['Solstheim']['not_started'], 1)
        self.assertEqual((head['none']['test_cell'], head['none']['teleport_only'], head['none']['no_entrance']),
                         (1, 1, 1))
        self.assertEqual(RM.totals(rows)['total'], len(self.GRAPH['rooms']))

    def test_attach_is_additive(self):
        recs = [{'name': 'A', 'chim': {'status': 'not_started'}}, {'name': 'Z'}]
        RM.attach(recs, RM.rooms(self.GRAPH))
        self.assertEqual(recs[0]['chim'], {'status': 'not_started'})
        self.assertEqual(recs[0]['room']['state'], 'not_started')
        self.assertNotIn('room', recs[1])

    def test_tracker_ingest_adds_interior_rooms_only(self):
        import cell_progress as cp
        with tempfile.TemporaryDirectory() as out:
            plain = cp.ingest(Path(out), now='2026-10-22T00:00:00+03:00')
            doc = cp.ingest(Path(out), now='2026-10-22T00:00:00+03:00', door_graph=self.GRAPH)
        self.assertNotIn('interior_rooms', plain)
        ir = doc['interior_rooms']
        self.assertEqual(ir['headline']['Vvardenfell']['total'], 5)
        self.assertEqual(len(ir['rooms']), len(self.GRAPH['rooms']))
        self.assertEqual([g['id'] for g in ir['groups']], ['in_game', 'not_in_game', 'set_aside'])
        self.assertEqual(ir['totals']['total'], len(self.GRAPH['rooms']))
        # the tracker page: counts per island and state in the three groups; nothing for data without interiors
        import cell_progress_md as md
        self.assertEqual(md.interior_lines(plain), [])
        text = '\n'.join(md.interior_lines(doc))
        self.assertIn('## Interiors', text)
        self.assertIn('**9 rooms: in the game 0; not in the game yet 4; set aside, with a reason 5.**', text)
        self.assertIn('| Set aside, with a reason | Set aside: test cell | 0 | 0 | 1 | 1 |', text)
        self.assertNotIn('ToddTest', text)                 # aggregate counts only
        self.assertIn('| Group | State | Vvardenfell | Solstheim | No entrance area | All |', text)
        resorted = dict(doc, interior_rooms=dict(ir, headline=dict(sorted(ir['headline'].items()))))
        self.assertEqual(md.interior_lines(resorted), md.interior_lines(doc))
        self.assertEqual(doc['headline'], plain['headline'])
        self.assertEqual(doc['cells'], plain['cells'])


if __name__ == '__main__':
    unittest.main()
