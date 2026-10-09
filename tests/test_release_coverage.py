# SPDX-License-Identifier: GPL-3.0-only
"""Every file class the last release ships has a feature and a default builder step.

BUILD-HANDS-NOT-BUILT-32 and BUILD-HARVEST-NOT-BUILT-32: per-race hands and the
mushroom harvest data shipped in every release since v0.0.29, but no builder
step made them; release images were patched from earlier images, so nothing
noticed. config/release-features.json maps every shipped file class to a
feature and to the default builder steps that make it;
config/release-payload-classes.json records the path classes of the last
release (no game data). These tests fail when a shipped class has no feature,
when a feature names a step the default build does not run, and when a known
builder gap is fixed without leaving the gap list (the list may only shrink).
"""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import build  # noqa: E402
import payload_coverage as coverage  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')

# Features the default build cannot make yet, with their open bug. This set may
# only shrink: a new entry needs a registered bug and an edit here. Empty since
# the harvest step (BUILD-HARVEST-NOT-BUILT-32).
ALLOWED_GAPS = {}


def default_steps(*extra):
    args = build.parser().parse_args(list(extra))
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    return build.commands(args, TOOLS, RUN)


def example(path_class):
    """One concrete path for a recorded class."""
    return path_class.replace('<h>', '0123456789abcdef').replace('#', '007')


class ReleaseFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = coverage.load_features()
        cls.baseline = coverage.load_classes()
        cls.features = cls.config['features']

    def test_every_release_class_has_exactly_one_feature(self):
        for path_class in self.baseline['classes']:
            with self.subTest(path_class=path_class):
                self.assertEqual(len(coverage.feature_of(example(path_class), self.features)), 1,
                                 'add the shipped file class to one feature in config/release-features.json')

    def test_every_feature_ships_in_the_release(self):
        examples = [example(c) for c in self.baseline['classes']]
        for feature in self.features:
            with self.subTest(feature=feature['id']):
                self.assertTrue(any(coverage.feature_of(path, [feature]) for path in examples),
                                'remove the stale feature or record the new release classes')

    def test_new_features_are_made_by_their_builder(self):
        new = self.config['new_features']
        self.assertEqual({f['id'] for f in new}, {'chim-world', 'chim-frame-maps'})
        legacy = dict(default_steps('--builder', 'legacy'))
        chim = dict(default_steps('--builder', 'chim'))
        for feature in new:
            with self.subTest(feature=feature['id']):
                self.assertEqual(feature['builder'], 'chim')
                self.assertEqual(set(feature['steps']) - set(chim), set())
                self.assertIn('chim', set(feature['steps']) - set(legacy))      # opt-in: not a legacy step
                for flag in feature.get('image_options', []):
                    self.assertEqual(chim['image'].count(flag), 1)
                    self.assertEqual(legacy['image'].count(flag), 0)

    def test_new_features_are_not_in_the_release_and_own_their_paths(self):
        examples = [example(c) for c in self.baseline['classes']]
        new = self.config['new_features']
        for path in examples:
            self.assertEqual(coverage.feature_of(path, new), [], path)
        chim_paths = ['id1/chim/world.cwi', 'id1/chim/frames/x-03/y-02/frame.ccf',
                      'id1/chim/frames/x-03/y-02/s07.ccs', 'id1/maps/balmora-chim.bsp']
        for path in chim_paths:
            with self.subTest(path=path):
                self.assertEqual(len(coverage.feature_of(path, self.features + new)), 1)

    def test_chim_payload_needs_the_chim_features(self):
        base = [example(c) for c in self.baseline['classes']]
        chim = ['id1/chim/world.cwi', 'id1/chim/frames/x-03/y-02/frame.ccf',
                'id1/chim/frames/x-03/y-02/s00.ccs', 'id1/maps/balmora-chim.bsp']
        legacy = coverage.compare(base, self.config, self.baseline)
        self.assertFalse(coverage.failed(legacy), legacy)
        self.assertEqual(legacy['builder'], 'legacy')
        missing = coverage.compare(base, self.config, self.baseline, 'chim')
        self.assertEqual(missing['missing_features'], ['chim-world', 'chim-frame-maps'])
        self.assertTrue(coverage.failed(missing))
        complete = coverage.compare(base + chim, self.config, self.baseline, 'chim')
        self.assertFalse(coverage.failed(complete), complete)
        self.assertEqual(complete['features']['chim-world'], 3)
        with self.assertRaises(ValueError):
            coverage.compare(base, self.config, self.baseline, 'v2')

    def test_every_feature_names_default_builder_steps(self):
        names = {name for name, _ in default_steps()}
        gaps = self.config.get('builder_gaps', {})
        for feature in self.features:
            with self.subTest(feature=feature['id']):
                self.assertTrue(feature['steps'], 'a feature without a builder step is not built')
                missing = set(feature['steps']) - names
                if feature['id'] in gaps:
                    # Still a gap: the step really is missing. Once it exists, the gap must go.
                    self.assertTrue(missing, f"{feature['id']} is built now: remove it from builder_gaps")
                else:
                    self.assertEqual(missing, set(), 'the default build lacks a step this release feature needs')

    def test_builder_gaps_only_shrink(self):
        gaps = self.config.get('builder_gaps', {})
        for feature, bug in gaps.items():
            with self.subTest(feature=feature):
                self.assertEqual(ALLOWED_GAPS.get(feature), bug, 'new builder gaps are not allowed')
        register = (ROOT / 'docs/BUGS.md').read_text(encoding='utf-8')
        for bug in gaps.values():
            self.assertIsNotNone(re.search(r'\|\s*\[?' + re.escape(bug) + r'\]?', register), bug)

    def test_default_image_gets_every_feature_input(self):
        image = dict(default_steps())['image']
        for feature in self.features:
            for flag in feature.get('image_options', []):
                with self.subTest(feature=feature['id'], flag=flag):
                    self.assertEqual(image.count(flag), 1)

    def test_per_race_hands_are_a_default_step(self):
        steps = dict(default_steps())
        command = steps['hand-catalog']
        self.assertEqual(Path(command[1]).name, 'prepare_hand_catalog.py')
        # Byte-identical to v0.0.31: authored topology, runtime palette with the UI bank.
        self.assertEqual(command[command.index('--topology') + 1], 'source')
        self.assertIn('--runtime-palette', command)
        self.assertEqual(Path(command[command.index('--palette') + 1]), RUN / 'intro-scene/id1/gfx/palette.lmp')
        self.assertEqual(Path(steps['image'][steps['image'].index('--hand-catalog') + 1]), RUN / 'hand-catalog')
        names = [name for name, _ in default_steps()]
        self.assertLess(names.index('hand-catalog'), names.index('image'))
        from build_parallel import stage_dependencies
        deps = stage_dependencies(default_steps())
        self.assertEqual(deps['hand-catalog'], ('census',))  # palette rewrite (BUILD-PALETTE-RACE-32)
        self.assertIn('hand-catalog', deps['image'])

    def test_builder_gap_list_is_empty(self):
        self.assertEqual(self.config.get('builder_gaps'), {})

    def test_harvest_is_a_default_step(self):
        # BUILD-HARVEST-NOT-BUILT-32: the harvest data is built, not carried forward.
        steps = dict(default_steps())
        command = steps['harvest']
        self.assertEqual(Path(command[1]).name, 'harvest_build.py')
        self.assertEqual(command[2], 'prepare')
        self.assertEqual(Path(command[command.index('--palette') + 1]), RUN / 'intro-scene/id1/gfx/palette.lmp')
        self.assertEqual(Path(command[command.index('--out') + 1]), RUN / 'harvest')
        self.assertIn('--jobs', command)
        self.assertEqual(Path(steps['image'][steps['image'].index('--harvest') + 1]), RUN / 'harvest')
        names = [name for name, _ in default_steps()]
        self.assertLess(names.index('harvest'), names.index('image'))
        from build_parallel import stage_dependencies
        deps = stage_dependencies(default_steps())
        self.assertEqual(deps['harvest'], ('census',))
        self.assertIn('harvest', deps['image'])

    def test_harvest_modes(self):
        def status(*extra):
            return build.harvest_status(build.parser().parse_args(list(extra)))
        self.assertEqual(status(), (True, 'enabled'))
        self.assertEqual(status('--no-harvest'), (False, 'disabled by --no-harvest'))
        self.assertFalse(status('--dry-run')[0])
        self.assertFalse(status('--stage', 'terrain')[0])
        self.assertFalse(status('--recover-image-from', '/old')[0])
        debug = dict(default_steps('--no-harvest'))
        self.assertNotIn('harvest', debug)
        self.assertNotIn('--harvest', debug['image'])
        self.assertEqual(set(dict(default_steps())) - set(debug), {'harvest'})

    def test_hand_catalog_modes(self):
        def status(*extra):
            return build.hand_catalog_status(build.parser().parse_args(list(extra)))
        self.assertEqual(status(), (True, 'enabled'))
        self.assertFalse(status('--hands', 'sprites')[0])
        self.assertFalse(status('--dry-run')[0])
        self.assertFalse(status('--stage', 'terrain')[0])
        self.assertFalse(status('--recover-image-from', '/old')[0])
        sprites = dict(default_steps('--hands', 'sprites'))
        self.assertNotIn('hand-catalog', sprites)
        self.assertNotIn('--hand-catalog', sprites['image'])

    def test_shipped_towns_are_a_release_feature(self):
        # BUILD-EXTRA-TOWN-OPTIN-32: the Vivec Arena preview ships in v0.0.32; its files are
        # explained by the extra-towns feature, filled in from the town table. v0.0.33 withdraws it
        # (towns.json "withdrawn", CHIM-ARENA-MEMORY-33): still explained, no longer built or required.
        feature = next(f for f in self.features if f['id'] == 'extra-towns')
        self.assertNotIn('town-vivec_arena', feature['steps'])
        self.assertNotIn('town-vivec_arena', dict(default_steps()))
        self.assertIn('town-vivec_arena', dict(default_steps('--extra-town', 'vivec_arena')))
        self.assertTrue(feature['withdrawn_only'])
        arena = ['id1/maps/va%03d.bsp' % i for i in range(16)] + [
            'id1/maps/vivec_arena.bsp', 'id1/scene-doors-vivec_arena.txt', 'id1/vivec_arena-regions.txt']
        for path in arena:
            with self.subTest(path=path):
                self.assertEqual(coverage.feature_of(path, self.features), ['extra-towns'])
        for path_class in ('id1/maps/va#.bsp', 'id1/maps/vivec_arena.bsp', 'id1/scene-doors-vivec_arena.txt',
                           'id1/vivec_arena-regions.txt'):
            self.assertIn(path_class, self.baseline['classes'])
        self.assertEqual(self.baseline['release'], 'v0.0.32')

    def test_town_feature_follows_the_town_table(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'
            shutil.copytree(ROOT / 'config', config)
            towns = json.loads((config / 'towns.json').read_text(encoding='utf-8'))
            row = next(r for r in towns['towns'] if r['id'] == 'vivec_foreign')
            row['shipped_since'] = 'v0.0.33'
            (config / 'towns.json').write_text(json.dumps(towns), encoding='utf-8')
            feature = next(f for f in coverage.load_features(root=tmp)['features'] if f['id'] == 'extra-towns')
        self.assertEqual(feature['steps'], ['town-vivec_foreign', 'image'])
        self.assertNotIn('withdrawn_only', feature)
        self.assertIn('id1/maps/vivec_arena.bsp', feature['withdrawn_patterns'])
        self.assertIn('id1/maps/vq[0-9][0-9][0-9].bsp', feature['patterns'])
        self.assertIn('id1/scene-doors-vivec_foreign.txt', feature['patterns'])
        self.assertIn('id1/maps/vqi[0-9][0-9][0-9].bsp', feature['patterns'])  # its rooms, once converted
        config = {'format': 'AmiWind release features 1', 'features': [{'id': 'x', 'towns': 'all', 'steps': [], 'patterns': []}]}
        with self.assertRaises(ValueError):
            coverage.expand_town_features(config)

    def test_release_files_lists_the_coverage_files(self):
        listed = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        text = json.dumps(listed)
        for name in ('config/release-features.json', 'config/release-payload-classes.json',
                     'tools/payload_coverage.py', 'tests/test_release_coverage.py'):
            self.assertIn(name, text)


class PayloadCheck(unittest.TestCase):
    """tools/payload_coverage.py on synthetic payloads (the from-scratch gate)."""

    @classmethod
    def setUpClass(cls):
        cls.config = coverage.load_features()
        cls.baseline = coverage.load_classes()
        cls.paths = [example(c) for c in cls.baseline['classes']]

    def test_complete_payload_passes(self):
        report = coverage.compare(self.paths, self.config, self.baseline)
        self.assertEqual((report['missing_features'], report['known_gaps'], report['missing_classes'],
                          report['new_classes'], report['unexplained_files'], report['ambiguous_files']),
                         ([], {}, [], [], [], []))
        self.assertFalse(coverage.failed(report))

    def test_missing_feature_and_new_class_are_reported(self):
        paths = [p for p in self.paths if not p.startswith(('id1/progs/hands/', 'id1/gfx/hand-'))]
        paths.append('id1/new-feature/thing.bin')
        report = coverage.compare(paths, self.config, self.baseline)
        self.assertEqual(report['missing_features'], ['hands-per-race'])
        self.assertIn('id1/gfx/hand-models.awh', report['missing_classes'])
        self.assertEqual(report['new_classes'], ['id1/new-feature/thing.bin'])
        self.assertEqual(report['unexplained_files'], ['id1/new-feature/thing.bin'])
        self.assertTrue(coverage.failed(report))

    def test_payload_without_harvest_is_a_missing_feature(self):
        # BUILD-HARVEST-NOT-BUILT-32: no longer a known gap, so nothing excuses it.
        paths = [p for p in self.paths if 'harvest' not in p]
        report = coverage.compare(paths, self.config, self.baseline)
        self.assertEqual(report['missing_features'], ['harvest'])
        self.assertEqual(report['known_gaps'], {})
        self.assertTrue(coverage.failed(report))
        self.assertTrue(coverage.failed(report, allow_known_gaps=True))

    def test_payload_without_a_withdrawn_town_passes(self):
        # v0.0.33 withdraws the Vivec Arena (towns.json "withdrawn"): a default payload without it
        # matches the release; its v0.0.32 classes are listed as withdrawn, not missing.
        arena = ('id1/maps/va', 'id1/maps/vivec_arena', 'id1/scene-doors-vivec_arena', 'id1/vivec_arena-')
        classes = ['id1/maps/va#.bsp', 'id1/maps/vivec_arena.bsp', 'id1/scene-doors-vivec_arena.txt',
                   'id1/vivec_arena-regions.txt']
        paths = [p for p in self.paths if not p.startswith(arena)]
        report = coverage.compare(paths, self.config, self.baseline)
        self.assertEqual((report['missing_features'], report['missing_classes']), ([], []))
        self.assertEqual(report['withdrawn_classes'], classes)
        self.assertFalse(coverage.failed(report))
        self.assertIn('withdrawn towns', coverage.text(report))

    def test_payload_without_the_shipped_town_is_a_missing_feature(self):
        # A build that leaves a shipped town out (an opt-in build before BUILD-EXTRA-TOWN-OPTIN-32,
        # or --only-core-towns) does not match the release: the Arena shipped again for the check.
        import town_config
        real = town_config.load_registry

        def shipped(root=None):
            registry = real(root)
            for row in registry['towns']:
                row.pop('withdrawn', None)
            return registry
        with patch.object(town_config, 'load_registry', shipped):
            config = coverage.load_features()
        arena = ('id1/maps/va', 'id1/maps/vivec_arena', 'id1/scene-doors-vivec_arena', 'id1/vivec_arena-')
        paths = [p for p in self.paths if not p.startswith(arena)]
        report = coverage.compare(paths, config, self.baseline)
        self.assertEqual(report['missing_features'], ['extra-towns'])
        self.assertEqual(report['missing_classes'], ['id1/maps/va#.bsp', 'id1/maps/vivec_arena.bsp',
                                                     'id1/scene-doors-vivec_arena.txt', 'id1/vivec_arena-regions.txt'])
        self.assertTrue(coverage.failed(report))
        # With the Arena files (the 19 the dev1 payload had unexplained) nothing is unexplained.
        full = paths + ['id1/maps/va%03d.bsp' % i for i in range(16)] + [
            'id1/maps/vivec_arena.bsp', 'id1/scene-doors-vivec_arena.txt', 'id1/vivec_arena-regions.txt']
        report = coverage.compare(full, self.config, self.baseline)
        self.assertEqual((report['unexplained_files'], report['missing_classes'], report['features']['extra-towns']),
                         ([], [], 19))
        self.assertFalse(coverage.failed(report))

    def test_known_gap_fails_unless_allowed(self):
        config = dict(self.config, builder_gaps={'harvest': 'EXAMPLE-GAP-00'})
        paths = [p for p in self.paths if 'harvest' not in p]
        report = coverage.compare(paths, config, self.baseline)
        self.assertEqual(report['missing_features'], [])
        self.assertEqual(report['known_gaps'], {'harvest': 'EXAMPLE-GAP-00'})
        self.assertTrue(coverage.failed(report))
        self.assertFalse(coverage.failed(report, allow_known_gaps=True))

    def test_payload_sources_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / 'payload.json'
            manifest.write_text(json.dumps({'files': [{'path': p, 'part': 'DH0'} for p in self.paths]}), encoding='utf-8')
            boot = root / 'boot'
            for path in self.paths[:5]:
                (boot / path).parent.mkdir(parents=True, exist_ok=True)
                (boot / path).write_bytes(b'')
            self.assertEqual(coverage.load_payload(manifest), sorted(self.paths))
            self.assertEqual(coverage.load_payload(boot), sorted(self.paths[:5]))
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(coverage.main(['check', str(manifest)]), 0)
            self.assertNotIn('MISSING', out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(coverage.main(['check', str(boot)]), 1)
            self.assertIn('hands-per-race', out.getvalue().split('Missing features')[1])
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(coverage.main(['check', str(boot), '--json']), 1)
            self.assertIn('hands-per-race', json.loads(out.getvalue())['missing_features'])

    def test_classes_are_asset_free_and_recorded_by_the_tool(self):
        self.assertEqual(coverage.path_class('id1/maps/vf0555.bsp'), 'id1/maps/vf#.bsp')
        self.assertEqual(coverage.path_class('id1/gallery/me403364b065b5a6c.mdl'), 'id1/gallery/m<h>.mdl')
        self.assertEqual(coverage.path_class('id1/progs/hands/nord_m_t.mdl'), 'id1/progs/hands/nord_m_t.mdl')
        self.assertTrue(coverage.matches('id1/maps/bm[a-z]*.bsp', 'id1/maps/bmtemple.bsp'))
        self.assertFalse(coverage.matches('id1/maps/bm[a-z]*.bsp', 'id1/maps/bm019.bsp'))
        self.assertFalse(coverage.matches('id1/*', 'id1/maps/x.bsp'))
        for path_class in self.baseline['classes']:
            self.assertEqual(coverage.path_class(example(path_class)), path_class)
        self.assertEqual(self.baseline['files'], sum(self.baseline['classes'].values()))


if __name__ == '__main__':
    unittest.main()
