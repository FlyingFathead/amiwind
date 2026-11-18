# SPDX-License-Identifier: GPL-3.0-only
"""Seyda Neen's CHIM frame and its town agree on the containers that open (BUILD-SEYDA-TOWN-CONTAINERS-67,
SEYDA-CONTAINERS-NOT-DRAWN-67). The v0.0.67-dev2 build stopped in chim-town-seyda, after the world stage: "19 CHIM
statics are not in the town", the 19 containers the frame had begun to place as its own (exported and placed as the
tutorial barrel is) and declared in its parity record, which the town's statics comparison did not count. Here: the
comparison counts them and still refuses a stray static either way, the declared containers are bound to the frame's
rule, and the builder's early check runs the same comparison on the frame predicted from the world stage's inputs,
right after the bsp stage. Synthetic town and records, no game data."""
import inspect
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import chim_town  # noqa: E402
import env_guard  # noqa: E402,F401
from player_hull import pack_lumps  # noqa: E402

BARREL = 172851        # aw_activated.h AW_REF_COURTYARD_BARREL, held by the town carrier itself
STATIC = 4242
# the 19 containers that open which the v0.0.67-dev2 frame placed (its CHIM world's parity open_containers)
CONTAINERS = [3864, 297457, 297459, 297461, 297463, 297464, 297465, 297466, 299125, 309361, 317802, 317803, 317804,
              317805, 317806, 333272, 333273, 333274, 333275]
DEV2_REFUSAL = '19 CHIM statics are not in the town (first: 3864, 297457, 297459, 297461, 297463)'


def town_map():
    """A converted town as the bsp stage's carrier leaves it: worldspawn, start, the tutorial barrel (activated) and one
    static, both brush models; no container (the scene's scenery selection keeps none)."""
    text = ('{\n"classname" "worldspawn"\n"aw_hull" "h"\n"message" "Seyda Neen"\n}\n'
            '{\n"classname" "info_player_start"\n"origin" "16.0 44.0 74.0"\n"angle" "90"\n}\n'
            '{\n"classname" "func_wall"\n"model" "*1"\n"origin" "120 -45 46"\n"aw_ref" "%d"\n}\n'
            '{\n"classname" "func_wall"\n"model" "*2"\n"origin" "-500 -500 0"\n"aw_ref" "%d"\n}\n' % (BARREL, STATIC))
    data = [bytearray() for _ in range(15)]
    data[0] = bytearray(text.encode('ascii') + b'\0')
    world = struct.pack('<9f7i', -2000, -2000, -100, 2000, 2000, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    barrel = struct.pack('<9f7i', -8, -8, -9, 8, 8, 9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    static = struct.pack('<9f7i', -16, -16, 0, 16, 16, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    data[14] = bytearray(world + barrel + static)
    return bytes(pack_lumps(data))


def town():
    from prepare_seyda_regions import regions
    maps, _, _ = chim_town.seyda_maps(town_map())
    return maps, [e['name'] for e in regions()]


def row(number, ident, x, y, kind='CONT', model='o/crate.nif'):
    """An original audit row (work/generated/seyda-neen/placements.json, the frame's source catalogue)."""
    return dict(number=number, id=ident, type=kind, model=model, cell=[math.floor(x / 8192), math.floor(y / 8192)],
                position=[x, y, 200.], rotation_radians=[0., 0., 0.], scale=1.)


def audit_rows():
    """The 19 containers in the frame's owned cells (cells (-1, -9) and (-2, -9)), a plant (organic: the harvest's),
    a container outside the owned cells, the tutorial barrel and a static."""
    rows = [row(n, 'chargen_crate_01', -7862. - k, -73174.) for k, n in enumerate(CONTAINERS)]
    rows += [row(500001, 'kollop_03_pearl', -7000., -73000.),
             row(500002, 'crate_far', 9000., -73174.),
             row(BARREL, 'chargen barrel fatigue', -10781., -71863.),
             row(STATIC, 'ex_common_house', -12000., -73000., kind='STAT', model='x/house.nif')]
    return rows


OPEN_IDS = frozenset({'chargen_crate_01', 'crate_far', 'chargen barrel fatigue'})


class StaticsComparison(unittest.TestCase):
    def test_the_19_placed_containers_are_the_towns_when_declared(self):
        maps, names = town()
        placed = {BARREL, STATIC, *CONTAINERS}
        refused, statics, specials = chim_town.seyda_statics_refusals(maps, names, placed,
                                                                      {'open_containers': CONTAINERS})
        self.assertEqual(refused, [])
        self.assertEqual((statics['chim_only'], statics['town_only'], statics['statics']), ([], [], 21))
        self.assertEqual(sorted(specials), ['intro_docks', 'sncourt'])
        self.assertIn('open_containers', chim_town.FRAME_ADDITIONS)

    def test_undeclared_they_stop_the_town_stage_as_in_dev2(self):
        maps, names = town()
        refused, statics, _ = chim_town.seyda_statics_refusals(maps, names, {BARREL, STATIC, *CONTAINERS}, {})
        self.assertEqual(refused, [DEV2_REFUSAL])
        self.assertEqual(statics['chim_only'], CONTAINERS)

    def test_a_stray_static_is_still_refused_either_way(self):
        maps, names = town()
        parity = {'open_containers': CONTAINERS}
        # placed by the frame, neither in the town nor declared
        refused, _, _ = chim_town.seyda_statics_refusals(maps, names, {BARREL, STATIC, 999001, *CONTAINERS}, parity)
        self.assertEqual(refused, ['1 CHIM statics are not in the town (first: 999001)'])
        # a static of the town the frame does not place
        refused, _, _ = chim_town.seyda_statics_refusals(maps, names, {BARREL, *CONTAINERS}, parity)
        self.assertEqual(refused[0], '1 statics of the town are not in the CHIM world (%d)' % STATIC)
        # a declared container the frame does not place (the special maps' one-way rule names it too)
        refused, _, _ = chim_town.seyda_statics_refusals(maps, names, {BARREL, STATIC, *CONTAINERS[1:]}, parity)
        self.assertEqual(refused[0], '1 statics of the town are not in the CHIM world (%d)' % CONTAINERS[0])
        self.assertTrue(all('(%d)' % CONTAINERS[0] in r for r in refused), refused)

    def test_every_addition_the_frame_declares_is_counted(self):
        """A reference the frame's source stage declares as its own addition (chim.seyda.prepare_area's parity record)
        is counted by the comparison; the other parity entries are removals and records."""
        from chim import seyda
        source = inspect.getsource(seyda.prepare_area)
        literal = source[source.index('parity = {'):]
        literal = literal[:literal.index('}') + 1]
        keys = set(re.findall(r"parity\['(\w+)'\]", source)) | set(re.findall(r"'(\w+)':", literal))
        self.assertIn('open_containers', keys)
        self.assertEqual(sorted(keys - set(chim_town.FRAME_ADDITIONS) - {'harvest_removed', 'omitted', 'opening'}), [])

    def test_the_town_stage_binds_the_containers_before_it_compares(self):
        source = inspect.getsource(chim_town.prepare_seyda)
        bind = source.index('seyda_container_check(')
        self.assertIn("chim_world / 'work' / SEYDA / 'source-catalogue.json'", source)
        self.assertLess(bind, source.index('seyda_statics_refusals(maps, region_names, placed, parity)'))
        self.assertNotIn('seyda_static_check(', source)      # the town and the specials through the one comparison


class ContainerBinding(unittest.TestCase):
    def check(self, declared, placed, rows=None):
        with tempfile.TemporaryDirectory() as tmp:
            catalogue = Path(tmp) / 'source-catalogue.json'
            catalogue.write_text(json.dumps({'references': audit_rows() if rows is None else rows}), encoding='utf-8')
            with mock.patch('open_containers.data_open_container_ids', return_value=OPEN_IDS), \
                    mock.patch('mwad.paths.resolve_data_files', side_effect=lambda p: p):
                return chim_town.seyda_container_check('data', catalogue, declared, placed)

    def test_the_19_hold(self):
        placed = {str(n) for n in [BARREL, STATIC, *CONTAINERS]}
        self.assertEqual(self.check(list(reversed(CONTAINERS)), placed), CONTAINERS)

    def test_anything_else_declared_is_refused(self):
        placed = {BARREL, STATIC, 500001, 500002, 600000, *CONTAINERS}
        for declared, words in (([*CONTAINERS, 500001], 'not containers that open'),     # a plant
                                ([*CONTAINERS, 500002], 'not containers that open'),     # outside the owned cells
                                ([*CONTAINERS, STATIC], 'not containers that open'),     # a static
                                ([*CONTAINERS, 600000], 'not references of the frame'),  # not in the catalogue
                                ([*CONTAINERS, CONTAINERS[0]], 'repeat')):
            with self.subTest(declared=declared[-1]):
                with self.assertRaisesRegex(ValueError, words):
                    self.check(declared, placed)
        with self.assertRaisesRegex(ValueError, r'1 are not placements of the frame \(3864\)'):
            self.check(CONTAINERS, {BARREL, STATIC, *CONTAINERS[1:]})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'source catalogue'):
                chim_town.seyda_container_check('data', Path(tmp) / 'missing.json', CONTAINERS, CONTAINERS)


class EarlyCheck(unittest.TestCase):
    """tools/seyda_early_checks.py: the frame predicted from the world stage's inputs against the bsp stage's town."""

    def inputs(self, tmp, selected=(STATIC,)):
        import seyda_entities
        tmp = Path(tmp)
        scene = tmp / 'bsp-scene'
        scene.mkdir()
        seyda_entities.publish(scene, town_map())
        index = {'models': [{'source': 'meshes/x/ex_common_house.nif'}],
                 'references': [{'number': n, 'model_index': 0} for n in selected]}
        (tmp / 'scenery-index.json').write_text(json.dumps(index), encoding='utf-8')
        (tmp / 'placements.json').write_text(json.dumps(audit_rows()), encoding='utf-8')
        return tmp / 'placements.json', tmp / 'scenery-index.json', scene

    def patched(self):
        refs = lambda index: ([dict(r) for r in index['references']], {'omitted': []}, {})   # noqa: E731
        return [mock.patch('chim.seyda.placements', side_effect=refs),
                mock.patch('prepare_opening_refs.opening_references',
                           return_value=([], [{'id': 'chargen barrel fatigue', 'number': BARREL}], set())),
                mock.patch('open_containers.data_open_container_ids', return_value=OPEN_IDS),
                mock.patch('mwad.paths.resolve_data_files', side_effect=lambda p: p)]

    def run_check(self, selected=(STATIC,), extra=()):
        import seyda_early_checks
        lines = []
        with tempfile.TemporaryDirectory() as tmp:
            audit, index, scene = self.inputs(tmp, selected)
            patches = self.patched() + list(extra)
            for p in patches:
                p.start()
            try:
                return seyda_early_checks.check(audit, index, scene, 'data', lines.append), lines
            finally:
                for p in reversed(patches):
                    p.stop()

    def test_the_predicted_frame_holds_the_barrel_and_the_containers(self):
        import seyda_early_checks
        with tempfile.TemporaryDirectory() as tmp:
            audit, index, _ = self.inputs(tmp)
            patches = self.patched()
            for p in patches:
                p.start()
            try:
                placed, parity = seyda_early_checks.predicted_frame(json.loads(index.read_text()),
                                                                   json.loads(audit.read_text()), 'data')
            finally:
                for p in reversed(patches):
                    p.stop()
        self.assertEqual(placed, {BARREL, STATIC, *CONTAINERS})
        self.assertEqual(parity, {'source_dressing_added': [], 'open_containers': CONTAINERS})

    def test_frame_and_town_agree(self):
        problems, lines = self.run_check()
        self.assertEqual(problems, [])
        self.assertIn('21 predicted placements (19 containers that open', lines[0])

    def test_the_dev2_mismatch_is_caught_before_the_world(self):
        uncounted = tuple(k for k in chim_town.FRAME_ADDITIONS if k != 'open_containers')
        problems, _ = self.run_check(extra=[mock.patch('chim_town.FRAME_ADDITIONS', uncounted)])
        self.assertEqual(len(problems), 1)
        self.assertIn(DEV2_REFUSAL, problems[0])
        self.assertIn('would stop after the world stage', problems[0])

    def test_a_frame_static_the_town_lacks_is_caught(self):
        problems, _ = self.run_check(selected=(STATIC, 5555))
        self.assertEqual(len(problems), 1)
        self.assertIn('1 CHIM statics are not in the town (first: 5555)', problems[0])

    def test_missing_inputs_are_named(self):
        import seyda_early_checks
        with tempfile.TemporaryDirectory() as tmp:
            problems = seyda_early_checks.check(Path(tmp) / 'a.json', Path(tmp) / 'i.json', Path(tmp), 'data')
        self.assertEqual(len(problems), 1)
        self.assertIn('cannot be compared', problems[0])


class EarlyCheckWiring(unittest.TestCase):
    def context(self, phase, **kw):
        import build_preflight
        return build_preflight.EarlyContext(phase, log=self.lines.append, **kw)

    def setUp(self):
        self.lines = []

    def test_registered_stored_and_after_the_bsp_stage(self):
        import build_preflight
        rows = [(p, t) for n, p, t in build_preflight.EARLY_CHECKS if n == 'seyda-frame-town']
        self.assertEqual(rows, [('stored', 'seyda_early_checks:frame_town'),
                                ('after:bsp', 'seyda_early_checks:frame_town_after')])

    def test_stored_reads_the_inputs_of_the_runs_they_come_from(self):
        import seyda_early_checks as sec
        steps = ['terrain', 'scenery', 'bsp', 'chim', 'chim-town-seyda']
        with mock.patch.object(sec, 'check', return_value=['x']) as check:
            ctx = self.context('stored', steps=steps, reused={'bsp': '/w/old', 'scenery': '/w/older'})
            ctx.data_files = Path('/data')
            self.assertEqual(sec.frame_town(ctx), ['the inputs this build takes from old: x'])
        audit, index, scene, data = check.call_args[0][:4]
        self.assertEqual((audit, index, scene, data),
                         (Path('/w/old/work/generated/seyda-neen/placements.json'),
                          Path('/w/older/scenery/scenery-index.json'), Path('/w/old/bsp-scene'), Path('/data')))

    def test_stored_skips_what_it_need_not_check(self):
        import seyda_early_checks as sec
        with mock.patch.object(sec, 'check') as check:
            # Seyda Neen is not a CHIM-native town of the build
            self.assertEqual(sec.frame_town(self.context('stored', steps=['bsp', 'chim'], reused={'bsp': '/w/o'})),
                             [])
            # the town stage itself is taken from an earlier run
            self.assertEqual(sec.frame_town(self.context('stored', steps=['bsp', 'chim-town-seyda'],
                                                         reused={'bsp': '/w/o', 'chim-town-seyda': '/w/o'})), [])
            # the bsp stage is made by this build: checked the moment it has passed
            self.assertEqual(sec.frame_town(self.context('stored', steps=['bsp', 'chim-town-seyda'])), [])
        check.assert_not_called()
        self.assertIn('compared the moment it has passed', self.lines[-1])

    def test_after_the_bsp_stage_on_the_run_folder(self):
        import seyda_early_checks as sec
        with mock.patch.object(sec, 'check', return_value=[]) as check, \
                mock.patch.dict(os.environ, {'AMIWIND_CHIM_NATIVE_TOWNS': 'balmora,seyda',
                                             'AMIWIND_DATA_FILES': '/data'}):
            self.assertEqual(sec.frame_town_after(self.context('after:bsp', run='/w/run', steps=['bsp'])), [])
        self.assertEqual(check.call_args[0][:4], (Path('/w/run/work/generated/seyda-neen/placements.json'),
                                                  Path('/w/run/scenery/scenery-index.json'),
                                                  Path('/w/run/bsp-scene'), Path('/data')))
        with mock.patch.object(sec, 'check') as check, \
                mock.patch.dict(os.environ, {'AMIWIND_CHIM_NATIVE_TOWNS': 'balmora'}):
            self.assertEqual(sec.frame_town_after(self.context('after:bsp', run='/w/run', steps=['bsp'])), [])
        check.assert_not_called()


if __name__ == '__main__':
    unittest.main()
