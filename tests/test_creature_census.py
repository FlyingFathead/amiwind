# SPDX-License-Identifier: GPL-3.0-only
"""The world-wide creature check (FAUNA-COVERAGE-62): every creature record of the masters is built by the image or
not built for a reason that config/creature-census.json names; anything else stops a full build. Synthetic records
only."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import creature_census as C


def sub(tag, value):
    return tag.encode() + struct.pack('<I', len(value)) + value


def record(tag, value):
    return tag.encode() + struct.pack('<III', len(value), 0, 0) + value


def creature(name, model, health=40):
    npdt = bytearray(96)
    struct.pack_into('<i', npdt, C.DEAD_OFFSET, health)
    return record('CREA', sub('NAME', name + b'\0') + sub('MODL', model + b'\0') + sub('FNAM', b'Beast\0') +
                  sub('NPDT', bytes(npdt)) + sub('FLAG', struct.pack('<I', 0x48)))


def ref(name, number):
    return sub('FRMR', struct.pack('<I', number)) + sub('NAME', name + b'\0') + \
        sub('DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 0))


def exterior(x, y, region, *refs):
    return record('CELL', sub('NAME', b'\0') + sub('DATA', struct.pack('<Iii', 0, x, y)) +
                  sub('RGNN', region + b'\0') + b''.join(refs))


def room(name, *refs):
    return record('CELL', sub('NAME', name + b'\0') + sub('DATA', struct.pack('<Iii', 1, 0, 0)) + b''.join(refs))


def levelled(name, *entries):
    return record('LEVC', sub('NAME', name + b'\0') + sub('DATA', struct.pack('<I', 0)) +
                  sub('NNAM', b'\0') + sub('INDX', struct.pack('<I', len(entries))) +
                  b''.join(sub('CNAM', e + b'\0') + sub('INTV', struct.pack('<H', 1)) for e in entries))


def setting(name, value):
    return record('GMST', sub('NAME', name + b'\0') + sub('STRV', value))


def script(name, text):
    return record('SCPT', sub('SCHD', name.ljust(32, b'\0') + bytes(20)) + sub('SCTX', text))


def master(extra=b''):
    return (creature(b'rat', b'r/rat.nif') + creature(b'kwama queen', b'r/kwamaqueen.nif') +
            creature(b'scamp_summon', b'r/scamp.nif') + creature(b'scrib_dead', b'r/scrib.nif', health=0) +
            creature(b'nix-hound', b'r/nixhound.nif') + creature(b'guar_scripted', b'r/guar.nif') +
            levelled(b'ex_wild_lev', b'nix-hound') + setting(b'sMagicScampID', b'scamp_summon') +
            script(b'guarscript', b'begin guarscript\r\nPlaceAtPC "guar_scripted", 1, 64, 1\r\nend') +
            exterior(1, 1, b'Bitter Coast Region', ref(b'rat', 10), ref(b'ex_wild_lev', 11)) +
            room(b'Shulk Egg Mine', ref(b'kwama queen', 20), ref(b'rat', 21), ref(b'ex_wild_lev', 22)) + extra)


def expansion():
    return creature(b'bm_wolf_grey', b'r/wolf.nif') + exterior(-20, 20, b'Felsaad Coast Region', ref(b'bm_wolf_grey', 5))


BUILT = {'rat', 'nix-hound', 'guar_scripted'}


def image(**changes):
    return dict(dict(built=set(BUILT), refs={21, 22}, meshes=None, left_out={}, kit_on_idle={}, sounds_missing=[],
                     partial=None), **changes)


class CreatureCensusTests(unittest.TestCase):
    def group(self, report, name):
        return next(g for g in report['groups'] if g['name'] == name)

    def test_the_shipped_config_names_the_masters_and_a_register_page_for_every_missing_group(self):
        config = C.load_config()
        self.assertEqual([m['name'] for m in config['masters']], ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'])
        for row in [g for g in config['groups'] if g['status'] == 'missing'] + config['masters'][1:] + \
                config['levelled_points']:
            self.assertTrue((ROOT / 'docs/bugs' / (row['register'] + '.md')).is_file(), row['register'])

    def test_every_record_is_built_or_not_built_for_its_reason(self):
        report = C.census([('Morrowind.esm', master()), ('Tribunal.esm', expansion())], image=image())
        self.assertEqual(C.check(report), [])
        t = report['totals']
        self.assertEqual((t['records'], t['built'], t['unclassified']), (7, 3, 0))
        self.assertEqual([r['id'] for r in self.group(report, 'Summoned creatures')['records']], ['scamp_summon'])
        self.assertEqual([r['id'] for r in self.group(report, 'Not used by the game data')['records']], ['scrib_dead'])
        self.assertEqual([r['id'] for r in self.group(report, 'Tribunal and Bloodmoon creatures')['records']],
                         ['bm_wolf_grey'])
        rooms = self.group(report, 'Creatures placed in rooms')
        self.assertEqual([r['id'] for r in rooms['records']], ['kwama queen'])
        # the room's rat is placed (reference 21), the queen is not
        self.assertEqual(rooms['placements'], 1)
        self.assertEqual(report['regions']['Bitter Coast Region'], dict(placements=1, built=1, levelled_points=1,
                                                                         levelled_built=1))
        self.assertEqual(t['scripts_placing'], 1)

    def test_a_room_placement_the_room_stage_holds_back_counts_under_the_rooms(self):
        report = C.census([('Morrowind.esm', master())], image=image(refs={22}))
        self.assertEqual(C.check(report), [])
        self.assertEqual(self.group(report, 'Creatures placed in rooms')['placements'], 2)

    def test_an_outdoor_creature_the_image_does_not_build_stops_the_build(self):
        report = C.census([('Morrowind.esm', master())], image=image(built=BUILT - {'rat'}))
        problems = C.check(report)
        self.assertEqual(len(problems), 1)
        self.assertIn('rat', problems[0])
        self.assertIn('register it', problems[0])
        # a creature only a script places has no group today: it stops the build too
        self.assertTrue(any('guar_scripted' in p for p in
                            C.check(C.census([('Morrowind.esm', master())], image=image(built={'rat', 'nix-hound'})))))

    def test_a_creature_without_a_model_or_with_a_refused_mesh_stops_the_build_whatever_else_holds(self):
        report = C.census([('Morrowind.esm', master())], image=image(meshes={'r/rat.nif', 'r/nixhound.nif'}))
        self.assertEqual(sorted(u['id'] for u in report['unclassified']), ['kwama queen', 'scamp_summon',
                                                                           'scrib_dead'])
        self.assertIn('no_model', report['unclassified'][0]['facts'])
        refused = C.census([('Morrowind.esm', master())], image=image(left_out={'r/kwamaqueen.nif': 'ValueError'}))
        self.assertEqual([u['id'] for u in refused['unclassified']], ['kwama queen'])
        self.assertTrue(C.check(refused))

    def test_a_levelled_point_not_placed_stops_the_build_unless_its_cell_is_named(self):
        report = C.census([('Morrowind.esm', master())], image=image(refs={21}))
        self.assertTrue(any('Shulk Egg Mine' in p for p in C.check(report)))
        config = C.load_config()
        config['levelled_points'][0]['cells'].append('Shulk Egg Mine')
        held = C.census([('Morrowind.esm', master())], config, image=image(refs={21}))
        self.assertEqual(C.check(held), [])
        self.assertEqual(held['levelled_not_built']['groups'][0]['points'], 1)

    def test_a_partial_build_is_reported_and_an_unnamed_master_stops_a_full_build(self):
        report = C.census([('Morrowind.esm', master())], image=image(built=set(), partial='a MiniWind'))
        self.assertEqual(C.check(report), [])
        self.assertGreater(report['totals']['unclassified'], 0)
        odd = C.census([('Morrowind.esm', master()), ('Other.esm', expansion())], image=image())
        self.assertTrue(any('Other.esm' in p for p in C.check(odd)))

    def test_built_creatures_without_sounds_stop_the_build(self):
        report = C.census([('Morrowind.esm', master())], image=image(sounds_missing=['rat']))
        self.assertEqual(C.check(report), ['built creature rat has no sounds in the voice table'])

    def test_map_refs_reads_the_actor_rows_reference_numbers(self):
        text = (b'{\n"classname" "worldspawn"\n}\n{\n"classname" "aw_npc"\n"aw_ref" "21"\n}\n'
                b'{\n"classname" "aw_levelled"\n"aw_ref" "22"\n}\n{\n"classname" "light"\n"aw_ref" "23"\n}\n')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'room.chim'
            path.write_bytes(struct.pack('<iii', 29, 12, len(text)) + text)
            self.assertEqual(C.map_refs(path), {21, 22})

    def test_the_public_tables_hold_counts_only(self):
        report = C.census([('Morrowind.esm', master()), ('Tribunal.esm', expansion())], image=image())
        text = '\n'.join(C.public_tables(report))
        self.assertIn('| Bitter Coast | 1 | 1 | none | 1 | 1 |', text)
        self.assertIn('| Felsaad Coast | 1 | 0 | Tribunal and Bloodmoon creatures 1 | 0 | 0 |', text)
        for ident in ('kwama queen', 'scamp_summon', 'Shulk Egg Mine'):
            self.assertNotIn(ident, text)

    def test_config_rules(self):
        config = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'c.json'
            for change in (lambda c: c['groups'][0].pop('register'),                       # missing without register
                           lambda c: c['groups'][3].pop('reason'),                         # skipped without reason
                           lambda c: c['groups'][1].update(when='weather'),                # unknown fact
                           lambda c: c['groups'].append(copy.deepcopy(c['groups'][1])),    # duplicate group
                           lambda c: c['levelled_points'][0].pop('cells'),                  # levelled group, no cells
                           lambda c: c['masters'].reverse()):                               # base master not first
                bad = copy.deepcopy(config)
                change(bad)
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    C.load_config(path)


if __name__ == '__main__':
    unittest.main()
