# SPDX-License-Identifier: GPL-3.0-only
"""The MWScript tracker and the CHIM progress tracker count Mournhold once the image carries it
(TRACKERS-MOURNHOLD-NOT-COUNTED-67).

Before: the script measure bound only the base game's placements, so every script placed only in Tribunal's world was
"only in an add-on world, not in the image yet" although the image carries Mournhold's districts and rooms; and the
progress tracker digested only the base CHIM world, so Mournhold's exterior showed "0 on CHIM" beside "11 of 11 done".
Now: the measure reads what the image carries from the build (its scripts receipt and its room store's receipt), and the
ingest counts the module worlds beside a build's base world as the same build's."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):          # src before tools: the src/mwad package, not tools/mwad.py
    if str(p) in sys.path:
        sys.path.remove(str(p))
for p in (ROOT / 'tools', ROOT / 'src'):
    sys.path.insert(0, str(p))

import cell_progress as cp  # noqa: E402
import cell_progress_build as cpb  # noqa: E402
import cell_progress_chim as CH  # noqa: E402
import mwscript_features as F  # noqa: E402
from mwscript.gamedata import ADDON_KEY_STRIDE  # noqa: E402


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding='utf-8')


def chim_world(folder, cell):
    """A one-frame CHIM run folder that converts exactly the cell CELL (x, y)."""
    frame = {'cell': list(cell), 'centre': [cell[0] * 8192, cell[1] * 8192], 'grain': 256, 'low': [0, 0], 'nx': 2,
             'ny': 2}
    write(Path(folder) / 'chim-receipt.json', {'frames': [{'frame': frame}], 'areas': [], 'chim_version': '0.2.2'})
    return str(folder)


class TheScriptMeasureReadsTheImage(unittest.TestCase):
    def build(self, root):
        write(root / 'mwscript' / 'mwscript-receipt.json',
              {'inputs': {'bound_addons': ['Tribunal.esm', 'Bloodmoon.esm'],
                          'presented': {'Mournhold, Godsreach': {'block': [-12, -30]},
                                        'mournhold, great bazaar': {'block': [-8, -30]}}}})
        write(root / 'chim-interiors' / 'chim-rooms-receipt.json',
              {'rooms': [{'cell': 'Mournhold Temple: Basement', 'room': 'a'},
                         {'cell': 'Mournhold Temple: Basement', 'room': 'b'}, {'cell': 'Vivec, Arena Pit'}],
               'room_types': [{'cell': 'Vivec, Arena Pit', 'room': 'vai000t0'}]})
        return root

    def test_the_image_world_comes_from_the_build_not_from_this_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = F.image_world(self.build(Path(tmp)))
        self.assertEqual(image['addons'], ['Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual(image['districts'], ['mournhold, godsreach', 'mournhold, great bazaar'])
        self.assertEqual(image['rooms'], ['mournhold temple: basement', 'vivec, arena pit'])
        self.assertEqual(set(image['interiors']), set(image['districts']) | set(image['rooms']))

    def test_a_build_without_the_module_or_rooms_carries_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = F.image_world(Path(tmp))
        self.assertEqual((image['addons'], image['districts'], image['rooms'], image['interiors']), ([], [], [], []))

    def test_an_addon_binding_counts_only_in_a_cell_the_image_carries(self):
        image = {'interiors': ['mournhold, godsreach', 'mournhold temple: basement']}
        names = {10: 'mournhold, godsreach', 11: 'mournhold, palace of the king', 12: 'mournhold temple: basement'}
        binds = [{'reference': 5, 'cell': 3},                                   # Morrowind.esm: always as before
                 {'reference': ADDON_KEY_STRIDE + 9, 'cell': 10},               # Tribunal, a district in the image
                 {'reference': ADDON_KEY_STRIDE + 10, 'cell': 11},              # Tribunal, a room the image lacks
                 {'reference': ADDON_KEY_STRIDE + 11, 'cell': 12},              # Tribunal, a room in the image
                 {'reference': 2 * ADDON_KEY_STRIDE + 4, 'cell': (1, 2)},       # Bloodmoon exterior: not in the image
                 {'reference': 2 * ADDON_KEY_STRIDE + 5, 'cell': 99}]           # a cell with no known name
        kept = [b['reference'] % ADDON_KEY_STRIDE for b in F.bound_in_image(binds, image, names)]
        self.assertEqual(kept, [5, 9, 11])
        # no build given: the add-ons' bindings all drop, as the measure did before this item
        self.assertEqual([b['reference'] for b in F.bound_in_image(binds, None, names)], [5])

    def test_the_stores_frames_carry_the_addon_exteriors(self):
        # EXPANSION-SCRIPTS-NOT-ATTACHED-66 (v0.0.68): Solstheim's frames are in the image since v0.0.68-dev3, but the
        # measure counted no add-on exterior, so the Skaal village's and Raven Rock's door scripts (bound, attached on
        # their frames) read "only in an add-on world". The stores' frames now count; a district's frames stay the
        # district's (bound by its interior cell)
        with tempfile.TemporaryDirectory() as tmp:
            root = self.build(Path(tmp))
            write(root / 'image' / 'chim-layer-stores.json',
                  [{'store': 'chimmh', 'maps': [{'cell': [-12, -30]}, {'cell': [-8, -30]}]},
                   {'store': 'chimsol', 'maps': [{'cell': [-20, 25]}, {'cell': [-25, 19]}]}])
            image = F.image_world(root)
        self.assertEqual(image['exteriors'], [(-25, 19), (-20, 25)])
        names = {10: 'mournhold, godsreach'}
        binds = [{'reference': 2 * ADDON_KEY_STRIDE + 4, 'cell': (-20, 25)},     # rigmor's door: a Solstheim frame
                 {'reference': 2 * ADDON_KEY_STRIDE + 5, 'cell': (-26, 25)},     # a cell no frame carries
                 {'reference': ADDON_KEY_STRIDE + 9, 'cell': 10}]                # a district, by its interior cell
        kept = [b['reference'] % ADDON_KEY_STRIDE for b in F.bound_in_image(binds, image, names)]
        self.assertEqual(kept, [4, 9])
        # without the stores' record (an older build) no add-on exterior counts, as before
        self.assertEqual([b['reference'] % ADDON_KEY_STRIDE for b in
                          F.bound_in_image(binds, dict(image, exteriors=[]), names)], [9])

    def test_a_script_placed_only_in_mournhold_is_not_called_absent_once_the_image_binds_it(self):
        row = {'error': False, 'handwritten': False, 'inert': False, 'notyet': [], 'bound': 0, 'start': False,
               'started_by': [], 'refs': {'records': {'NPC_': ['asciene rane']}, 'placed': {'Tribunal.esm': {'NPC_': 1}},
                                          'levelled': 0, 'dialogue_starts': 0, 'dialogue_speaker': 0,
                                          'placed_by_scripts': 0}}
        # the old measure: no add-on binding, so every Tribunal script was "only in an add-on world"
        self.assertEqual(F.state_of(row)[0], 'not-in-image')
        row['bound'] = 1                                       # the image binds it in a district or a room
        self.assertEqual(F.state_of(row), ('runs', ''))
        row['notyet'] = ['placeitem']                          # and it is judged by the base game's rules from then on
        self.assertEqual(F.state_of(row)[0], 'missing-function')

    def test_the_committed_measure_names_its_image_and_counts_tribunal_in_it(self):
        doc = F.load()
        image = doc['measured'].get('image')
        self.assertTrue(image, 'docs/mwscript-features.json was measured without --image-build')
        self.assertIn('Tribunal.esm', image['addons'])
        self.assertGreater(image['districts'], 0)
        self.assertGreater(image['rooms'], 0)
        self.assertGreater(image['bound_in_image']['Tribunal.esm'], 0)
        self.assertLessEqual(sum(image['bound_in_image'].values()), image['addon_in_file'])
        # EXPANSION-SCRIPTS-NOT-ATTACHED-66: the image's Solstheim frames count, so Bloodmoon's exterior scripts run
        self.assertGreater(image.get('exteriors', 0), 0)
        self.assertGreater(image['bound_in_image']['Bloodmoon.esm'], 610, 'the rooms alone gave 610')
        states = {r['id'].casefold(): r['state'] for r in doc['scripts']}
        self.assertEqual((states['rigmordoorscript'], states['colony_door_uryn']), ('runs', 'runs'))
        tribunal = [r for r in doc['scripts'] if r['master'] == 'Tribunal.esm']
        runs = [r for r in tribunal if r['state'] == 'runs' and r['bound']]
        self.assertGreater(len(runs), 45, 'Tribunal scripts bound in the image run: 45 were all the old measure found')
        # a script is "only in an add-on world" only when none of its binding is in the image
        for r in tribunal:
            if r['state'] == 'not-in-image':
                self.assertEqual(r['bound'], 0, r['id'])


class TheProgressIngestCountsTheModulesWorld(unittest.TestCase):
    def test_the_modules_cells_join_the_build_s_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = chim_world(Path(tmp) / 'chim-world', (0, 0))
            module = chim_world(Path(tmp) / 'tribunal-mournhold', (5, 5))
            alone = CH.digest('b', base)
            both = CH.digest_many('b', [base, module], 'label', 'abc', 'now')
            self.assertEqual(CH.digest_many('b', [base])['cells'], alone['cells'])    # no module: the digest as before
        self.assertEqual([k for k, e in alone['cells'].items() if e['converted']], ['0,0'])
        self.assertEqual([k for k, e in both['cells'].items() if e['converted']], ['0,0', '5,5'])
        self.assertEqual([f['cell'] for f in both['frames']], [[0, 0], [5, 5]])

    def test_a_cell_two_worlds_both_convert_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = chim_world(Path(tmp) / 'chim-world', (0, 0))
            other = chim_world(Path(tmp) / 'tribunal-mournhold', (0, 0))
            with self.assertRaises(ValueError):
                CH.digest_many('b', [base, other])

    def test_the_modules_world_beside_a_build_run_is_found_by_its_stage_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            base = chim_world(run / 'chim-world', (0, 0))
            self.assertEqual(CH.module_worlds(base), [])
            module = chim_world(run / 'tribunal-mournhold', (5, 5))
            self.assertEqual(CH.module_worlds(base), [str(run / 'tribunal-mournhold')])
            self.assertEqual(CH.module_worlds(module), [])                    # only a build's chim-world has modules
            self.assertEqual(CH.module_worlds(chim_world(Path(tmp) / 'seyda-009', (1, 1))), [])

    def test_ingest_run_spec_counts_the_module_as_the_same_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            chim_world(run / 'chim-world', (0, 0))
            chim_world(run / 'tribunal-mournhold', (5, 5))
            out = Path(tmp) / 'out'
            digests = cp.load_runs(out, ['b=%s' % (run / 'chim-world')], {}, {})          # as the delivery's ingest gives it
            explicit = cp.load_runs(Path(tmp) / 'out2', ['b=%s|%s' % (run / 'chim-world', run / 'tribunal-mournhold')], {}, {})
        for found in (digests, explicit):
            self.assertEqual(len(found), 1)
            self.assertEqual(sorted(k for k, e in found[0]['cells'].items() if e['converted']), ['0,0', '5,5'])

    def test_the_build_stage_hands_its_module_worlds_to_the_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            chim_world(run / 'chim-world', (0, 0))
            chim_world(run / 'tribunal-mournhold', (5, 5))
            self.assertEqual(cpb.run_spec(run / 'chim-world', [run / 'tribunal-mournhold']),
                             ['build=%s|%s' % (run / 'chim-world', run / 'tribunal-mournhold')])
            self.assertEqual(cpb.run_spec(run / 'chim-world', [run / 'tribunal-nowhere']), ['build=%s' % (run / 'chim-world')])
            self.assertEqual(cpb.run_spec(run / 'chim-world'), ['build=%s' % (run / 'chim-world')])
            self.assertEqual(cpb.run_spec(run / 'missing', [run / 'tribunal-mournhold']), [])

    def test_the_committed_snapshot_has_mournhold_on_chim(self):
        state = json.loads((ROOT / 'docs' / 'chim' / 'progress-state.json').read_text(encoding='utf-8'))
        newest = state['builds'][0]
        mh = next(i for i in newest['islands'] if i['name'] == 'Mournhold')
        done = next(i for i in state['islands'] if i['name'] == 'Mournhold')
        self.assertGreater(mh['land'], 0, 'Mournhold shows 0 on CHIM in the newest build')
        self.assertLessEqual(mh['land'], done['cells'])


if __name__ == '__main__':
    unittest.main()
