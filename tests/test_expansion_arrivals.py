# SPDX-License-Identifier: GPL-3.0-only
"""dbg tp's arrivals in the expansions (DBG-TP-EXPANSION-ARRIVALS-66, tools/expansion_arrivals.py): the rows with and
without each expansion, the aliases, the refusal texts, the image's teleport-names.txt as the engine reads it, the
smoke hops following the image, and the wiring (the image step, the stage key, the engine's "-" rows and the typed
place name). No game data: the room table and the frames are given."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))
import expansion_arrivals as E  # noqa: E402
import world_doors  # noqa: E402

BASE = ['Morrowind.esm']
TRIBUNAL = ['Morrowind.esm', 'Tribunal.esm']
BOTH = ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm']
RECEPTION = 'mournhold, royal palace: reception area'
ROOMS = {RECEPTION: 'rid3587e40b7'}          # config/room-batches.json: the Reception Area's batch map


def frostmoth_only(point):
    """A frame holds Fort Frostmoth's cell (-22,16) and nothing else of Solstheim."""
    return (int(point[0] // 8192), int(point[1] // 8192)) == (-22, 16)


def by_name(rows):
    return {row['name']: row for row in rows}


class Rows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.places = E.load()

    def test_the_base_game_alone_names_every_place_and_moves_nowhere(self):
        rows = by_name(E.rows(self.places, BASE, ROOMS, frostmoth_only))
        self.assertEqual({r['state'] for r in rows.values()}, {'needs the expansion'})
        self.assertEqual({r['map'] for r in rows.values()}, {world_doors.NOT_HERE})
        self.assertEqual(rows['mournhold']['label'], 'Mournhold is not in this build: it needs Tribunal (Tribunal.esm).')
        self.assertEqual(rows['solstheim']['label'],
                         'Fort Frostmoth is not in this build: it needs Bloodmoon (Bloodmoon.esm).')

    def test_tribunal_holds_the_reception_area_at_the_scripts_own_arrival(self):
        rows = by_name(E.rows(self.places, TRIBUNAL, ROOMS, frostmoth_only))
        m = rows['mournhold']
        self.assertEqual((m['state'], m['map'], m['label']),
                         ('present', 'rid3587e40b7', 'Mournhold, Royal Palace: Reception Area'))
        # the arrival MHTransportScript's PositionCell compiles to (its PMOV row in the v0.0.66 release run's
        # mwscript.awm: 0.7 239.8 -9.6, yaw 270): the same rule, mwscript.rooms.arrival
        self.assertEqual([round(v, 1) for v in m['at']] + [round(m['yaw'], 1)], [0.7, 239.8, -9.6, 270.0])
        from mwscript.rooms import arrival
        self.assertEqual(tuple(m['at']) + (m['yaw'],), arrival((2.730, 959.274, -105.817), 180.0))
        # Bloodmoon's places need their expansion; the districts are not held (not rooms of the image)
        self.assertEqual(rows['solstheim']['state'], 'needs the expansion')
        for name in ('godsreach', 'greatbazaar', 'brindisi', 'palacecourtyard', 'templecourtyard'):
            self.assertEqual((rows[name]['state'], rows[name]['map']), ('not held', world_doors.NOT_HERE), name)
            self.assertTrue(rows[name]['label'].endswith('is not in this build yet: this image does not hold it.'))

    def test_a_presented_district_is_an_outdoor_place_at_its_moved_point(self):
        # MOURNHOLD-EXTERIOR-CELLS-66: a district the build presents as exterior cells and converts (its arrival read
        # as the presented world has it: tools/presented_exterior.py present_arrivals) is a working outdoor place at its
        # moved point, held by the region frames of its block; the districts the build does not present stay as they
        # were, and without a presentation every row is today's
        import presented_exterior as P
        from tp_places_lut import LIFT
        places = {'mournhold, godsreach': {'cell': 'Mournhold, Godsreach', 'block': [-12, -30], 'size': [2, 2],
                                           'offset': [-90000.0, -240000.0]}}
        block = {(-12, -30), (-11, -30), (-12, -29), (-11, -29)}

        def held(point):
            return (int(point[0] // 8192), int(point[1] // 8192)) in block
        rows = by_name(E.rows(P.present_arrivals(places, self.places), TRIBUNAL, ROOMS, held))
        g = rows['godsreach']
        self.assertEqual((g['state'], g['map'], g['label']), ('present', world_doors.GLOBAL_PLACE, 'Mournhold, Godsreach'))
        self.assertEqual(g['at'], [-2504.0 - 90000.0, -232.0 - 240000.0, 160.0 + LIFT])
        self.assertEqual((rows['greatbazaar']['state'], rows['greatbazaar']['map']), ('not held', world_doors.NOT_HERE))
        self.assertEqual(rows['mournhold']['map'], 'rid3587e40b7')            # a room place: unchanged
        self.assertEqual(E.rows(P.present_arrivals({}, self.places), TRIBUNAL, ROOMS, held),
                         E.rows(self.places, TRIBUNAL, ROOMS, held))

    def test_without_the_room_tribunal_says_not_held(self):
        rows = by_name(E.rows(self.places, TRIBUNAL, {}, None))
        self.assertEqual((rows['mournhold']['state'], rows['mournhold']['map']), ('not held', world_doors.NOT_HERE))
        self.assertEqual(rows['mournhold']['label'], 'Mournhold is not in this build yet: this image does not hold it.')

    def test_bloodmoon_holds_what_a_frame_holds(self):
        rows = by_name(E.rows(self.places, BOTH, ROOMS, frostmoth_only))
        s = rows['solstheim']
        self.assertEqual((s['state'], s['map'], s['label']), ('present', world_doors.GLOBAL_PLACE,
                                                              'Fort Frostmoth, Solstheim (the dock)'))
        # the original's own point, the height LIFT above it (the floor at or below)
        from tp_places_lut import LIFT
        self.assertEqual(s['at'], [-174024.391, 136823.953, 457.668 + LIFT])
        self.assertEqual((rows['ravenrock']['state'], rows['skaal']['state']), ('not held', 'not held'))
        # no frames at all: nothing outdoors is present
        rows = by_name(E.rows(self.places, BOTH, ROOMS, None))
        self.assertEqual(rows['solstheim']['state'], 'not held')
        # Bloodmoon alone: Mournhold needs Tribunal
        rows = by_name(E.rows(self.places, ['Morrowind.esm', 'Bloodmoon.esm'], ROOMS, frostmoth_only))
        self.assertEqual((rows['mournhold']['state'], rows['solstheim']['state']), ('needs the expansion', 'present'))

    def test_the_aliases_are_the_same_place(self):
        rows = by_name(E.rows(self.places, BOTH, ROOMS, frostmoth_only))
        for name, alias in (('mournhold', 'tribunal'), ('solstheim', 'frostmoth'), ('greatbazaar', 'bazaar'),
                            ('brindisi', 'plazabrindisidorom')):
            self.assertEqual(dict(rows[name], name=alias), rows[alias])
        self.assertTrue(set(rows) >= {'mournhold', 'tribunal', 'solstheim', 'ravenrock', 'skaal'})

    def test_every_label_fits_the_engine(self):
        for masters in (BASE, TRIBUNAL, BOTH):
            for row in E.rows(self.places, masters, ROOMS, frostmoth_only):
                self.assertLessEqual(len(row['label'].encode('cp1252')), 95, row)
                self.assertLessEqual(len(E.line(row).encode('cp1252')), E.LINE_BYTES, row)

    def test_the_config_is_checked(self):
        good = {'names': ['x'], 'master': 'Tribunal.esm', 'place': 'X', 'label': 'X', 'at': [0, 0, 0], 'outdoors': True}
        E.check([good])
        for bad in (dict(good, names=['Has Space']), dict(good, names=['x' * 24]), dict(good, at=[0, 0]),
                    dict(good, cell='A cell'), {k: v for k, v in good.items() if k != 'outdoors'},
                    dict(good, master='')):
            with self.assertRaises(ValueError, msg=bad):
                E.check([bad])
        with self.assertRaises(ValueError):
            E.check([good, dict(good, place='Y')])           # a name twice
        # the shipped names are not names of config/teleport-names.txt
        base = world_doors.teleport_names((ROOT / 'config' / 'teleport-names.txt').read_bytes())
        self.assertFalse({n for p in self.places for n in p['names']} & set(base))


class NamesFile(unittest.TestCase):
    def test_the_image_file_keeps_the_config_and_adds_a_row_per_name(self):
        base = (ROOT / 'config' / 'teleport-names.txt').read_bytes()
        places = E.load()
        for masters in (BASE, TRIBUNAL, BOTH):
            out = E.text(base, E.rows(places, masters, ROOMS, frostmoth_only))
            self.assertTrue(out.startswith(base))
            names = world_doors.teleport_names(out)
            self.assertEqual(set(names), set(world_doors.teleport_names(base)) | {n for p in places for n in p['names']})
            # the image check: a "-" row says why itself, a present room row leads into a room the image holds, a
            # being row (lordvivec, DBG-TP-LORDVIVEC-69) to one being row of the image's teleport list
            self.assertEqual(world_doors.teleport_name_problems(names, dict(ROOMS, **{
                'x': 'ric5e9a38a4d', 'y': 'rifa4ef181ed', 'vivec, arena pit': 'vai000'}), {'vivec_god': 1}), [])
        out = world_doors.teleport_names(E.text(base, E.rows(places, TRIBUNAL, ROOMS, None)))
        self.assertEqual(out['mournhold'][0], 'rid3587e40b7')
        self.assertEqual(out['godsreach'][0], world_doors.NOT_HERE)

    def test_a_name_the_config_has_is_refused(self):
        base = b'AWTN1\nmournhold|global|0 0 0|0|Somewhere\n'
        with self.assertRaises(ValueError):
            E.text(base, E.rows(E.load(), BASE, {}, None))


class Hops(unittest.TestCase):
    """The smoke hops follow the image: a hop for every hop place it holds, nothing without the expansion."""

    def hops(self, masters, rooms, holds):
        base = (ROOT / 'config' / 'teleport-names.txt').read_bytes()
        return E.hops(E.text(base, E.rows(E.load(), masters, rooms, holds)), E.load())

    def test_no_expansion_no_hop(self):
        self.assertEqual(self.hops(BASE, ROOMS, frostmoth_only), [])
        self.assertEqual(self.hops(TRIBUNAL, {}, None), [])

    def test_a_hop_per_held_place(self):
        self.assertEqual(self.hops(TRIBUNAL, ROOMS, None),
                         ['cmd dbg tp mournhold', 'wait 45', 'state map', 'shot hop-mournhold', 'state frame_ms'])
        shots = [l for l in self.hops(BOTH, ROOMS, frostmoth_only) if l.startswith('shot ')]
        self.assertEqual(shots, ['shot hop-mournhold', 'shot hop-solstheim'])      # Skaal Village not held here
        everything = [l for l in self.hops(BOTH, ROOMS, lambda p: True) if l.startswith('shot ')]
        self.assertEqual(everything, ['shot hop-mournhold', 'shot hop-solstheim', 'shot hop-skaal'])

    def test_the_command_writes_the_base_script_and_the_hops(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            id1.mkdir()
            base = (ROOT / 'config' / 'teleport-names.txt').read_bytes()
            (id1 / 'teleport-names.txt').write_bytes(E.text(base, E.rows(E.load(), TRIBUNAL, ROOMS, None)))
            script = Path(tmp) / 'smoke-hops.txt'
            script.write_text('wait 8\ncmd dbg tp balmora\n', encoding='utf-8')
            out = Path(tmp) / 'hops.txt'
            self.assertEqual(E.main(['hops', '--id1', str(id1), '--base', str(script), '--out', str(out)]), 0)
            self.assertEqual(out.read_text(encoding='utf-8').splitlines(),
                             ['wait 8', 'cmd dbg tp balmora', 'cmd dbg tp mournhold', 'wait 45', 'state map',
                              'shot hop-mournhold', 'state frame_ms'])


class Wiring(unittest.TestCase):
    def test_the_image_step_writes_the_rows_where_it_knows_its_rooms(self):
        build = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        doors = build[build.index('def write_world_doors('):build.index('def write_door_check(')]
        self.assertLess(doors.index('rooms.update('), doors.index('expansion_arrivals.rows('))
        self.assertIn("(id1/'teleport-names.txt').write_bytes(", doors)
        self.assertIn("'arrivals': expansion_arrivals.summary(arrivals)", doors)
        self.assertIn('world_doors.holder(point, towns, regions) is not None', doors)

    def test_the_image_stage_key_reads_the_config(self):
        import build_cache
        python, data, uncertain = build_cache.SourceIndex().closure(ROOT / 'tools' / 'build_aga.py')
        self.assertIn('tools/expansion_arrivals.py', python)
        self.assertIn('config/expansion-arrivals.json', data)

    def test_the_engine_prints_a_not_held_row_and_moves_nothing(self):
        scene = (ROOT / 'engine' / 'aga' / 'src' / 'aw_scene.c').read_text(encoding='utf-8')
        named = scene[scene.index('static int named_place('):scene.index('static int roulette_room(')]
        self.assertIn('strcmp(map,"global") && strcmp(map,"-") && !map_valid(map)', named)
        command = scene[scene.index('static void scene_command(void) {'):]
        # the label said, then the one dbg tp refusal path (the box, as a place this build leaves out), nothing loaded
        refusal = command.index('if(!strcmp(r.target,"-")){\n            Con_Printf("%s\\n",r.label);\n'
                                '            tp_refused(AW_LOADERR_NOT_ON_DISK,s,"",NULL,r.label);return;\n        }')
        self.assertLess(refusal, command.index('load_scene(&r,1);return;'))

    def test_a_typed_place_name_goes_through_the_list(self):
        scene = (ROOT / 'engine' / 'aga' / 'src' / 'aw_scene.c').read_text(encoding='utf-8')
        command = scene[scene.index('static void scene_command(void) {'):]
        self.assertLess(command.index('AW_TpPlacesFind(Cmd_Argv(1)))return;'),
                        command.index('Con_Printf("Unknown destination: %s.\\n",Cmd_Argv(1));'))
        teleport = scene[scene.index('static void teleport_command(void) {'):]
        self.assertIn('if(Cmd_Argc()>=3 && !teleport_coordinate(Cmd_Argv(1),&source[0]) && place_words())return;',
                      teleport)
        places = (ROOT / 'engine' / 'aga' / 'src' / 'aw_tpplaces.c').read_text(encoding='utf-8')
        find = places[places.index('int AW_TpPlacesFind(const char *text){'):]
        # chosen as in the box; nothing held (the names list is read row by row)
        self.assertIn('if(row>=0){chosen(NULL,(int)row);return 1;}', find)
        self.assertNotIn('AW_TpNamesOpen', find[:find.index('/* ----')])

    def test_the_help_line_names_the_arrivals(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        line = next(l for l in catalogue.splitlines() if l.startswith('WORLD / TRAVEL|tp|aw_teleport|'))
        for name in ('mournhold', 'solstheim', 'ravenrock', 'skaal', 'a map, room or place'):
            self.assertIn(name, line)
        self.assertLessEqual(len(line.encode('utf-8')), 382)
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertTrue(re.search(r'\| `dbg tp` \|.*mournhold / solstheim / ravenrock / skaal', page))


if __name__ == '__main__':
    unittest.main()
