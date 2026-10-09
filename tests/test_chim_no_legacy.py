"""CHIM builds ship no legacy exterior map of a CHIM area: plan split, image safety net, Seyda input, legacy plan."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import build
from test_build_builder import plan

# The legacy plan at the CHIM no-legacy change (stage, tool script): --builder legacy must keep it.
LEGACY_PLAN = (
    ('setup', 'mwad.py'), ('terrain', 'mwad.py'), ('scenery', 'prepare_scenery.py'), ('scene', 'prepare_quake.py'),
    ('bsp', 'prepare_mesh_bsp.py'), ('npcs', 'prepare_npcs.py'), ('hands', 'prepare_hands.py'),
    ('interior', 'prepare_interior.py'), ('dialogue-lookup', 'prepare_dialogue_lookup.py'),
    ('intro', 'prepare_intro.py'), ('census', 'prepare_census.py'), ('npc-gallery', 'build_gallery.py'),
    ('area', 'prepare_area.py'), ('balmora', 'prepare_balmora.py'),
    ('balmora-interiors', 'prepare_balmora_interiors.py'),
    ('door-audio', 'prepare_door_audio.py'), ('character', 'prepare_character.py'),
    ('reading', 'prepare_reading.py'), ('opening-references', 'prepare_opening_refs.py'),
    ('world-survey', 'survey_vvardenfell.py'), ('world-ui', 'prepare_world_ui.py'),
    ('actor-contact', 'check_scene_actors.py'), ('world-terrain', 'prepare_world_regions.py'),
    ('seam-audit', 'seam_audit.py'), ('world-scenery-assets', 'world_scenery.py'), ('world-scenery', 'prepare_world_scenery.py'),
    ('media', 'prepare_media_assets.py'), ('music', 'prepare_music.py'), ('engine', 'build_aga.py'),
    ('world-flora-assets', 'prepare_tree_sprites.py'), ('world-flora', 'prepare_world_flora.py'),
    ('harvest', 'harvest_build.py'), ('hand-catalog', 'prepare_hand_catalog.py'), ('image', 'build_aga.py'))
LEGACY_IMAGE_OPTIONS = (
    '--balmora-cache', '--balmora-scenery', '--canonical-land-source', '--data-files', '--engine', '--entity-baseline',
    '--gallery', '--hand-catalog', '--hands', '--harvest', '--hidden-surface-cull', '--jobs', '--light',
    '--local-skybox', '--map-budget-policy', '--media', '--music', '--out', '--qbsp', '--qcc', '--rdbtool', '--scene',
    '--sdk', '--town-flora-scene-report', '--town-flora-source-index', '--town-scenery', '--vis', '--world-flora',
    '--world-scenery', '--xdftool')
BOTH = ['--jobs', '4', '--builder', 'chim', '--chim-area', 'balmora', '--chim-area', 'seyda']


def script(command):
    return Path(str(command[1]).replace(chr(92), '/')).name


class LegacyPlanTests(unittest.TestCase):
    def test_legacy_plan_is_unchanged(self):
        # The Vivec Arena (town-vivec_arena) is withdrawn from v0.0.33 default builds (config/towns.json).
        for argv in (['--jobs', '4', '--builder', 'legacy'],):
            with self.subTest(argv=argv):
                steps = plan(argv)
                self.assertEqual(tuple((name, script(command)) for name, command in steps), LEGACY_PLAN)
                image = dict(steps)['image']
                self.assertEqual(tuple(sorted({str(p) for p in image if str(p).startswith('--')})),
                                 LEGACY_IMAGE_OPTIONS)
        self.assertNotEqual(plan(['--jobs', '4']), plan(['--jobs', '4', '--builder', 'legacy']))  # chim is the default

    def test_legacy_build_needs_no_recorded_seyda(self):
        args = build.parser().parse_args(['--jobs', '4', '--builder', 'legacy'])
        build.chim_seyda_input(args)        # no error: the legacy builder converts Seyda Neen as before


class ChimPlanTests(unittest.TestCase):
    def test_chim_plan_split_is_recorded_and_pinned(self):
        from chim.plan import record
        steps = plan(BOTH)
        names = [name for name, _ in steps]
        # interiors and the shared converter stages stay; CHIM's own stage runs before the image
        for stage in ('interior', 'area', 'balmora-interiors', 'census', 'scenery', 'scene', 'world-survey',
                      'harvest', 'world-flora-assets', 'chim', 'image'):
            self.assertIn(stage, names)
        rows = record(names, ['balmora', 'seyda'])['legacy_exterior_stages']
        self.assertEqual([(r['stage'], r['area'], r['on_chim']) for r in rows], [
            ('balmora', 'balmora', True),
            ('world-terrain', 'open world', False), ('world-scenery-assets', 'open world', False),
            ('world-scenery', 'open world', False), ('world-flora', 'open world', False)])
        for row in rows:
            self.assertTrue(row['makes'] and row['read_by'], row)

    def test_chim_stage_reads_shared_converter_outputs(self):
        command = [str(p) for p in dict(plan(BOTH))['chim']]
        self.assertEqual(command[command.index('--legacy-run') + 1], str(Path('/private/run')))
        self.assertEqual([command[i + 1] for i, p in enumerate(command) if p == '--area'], ['balmora', 'seyda'])

    def test_build_state_records_the_split(self):
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("metadata['chim_plan'] = chim_plan_record(", source)


class SeydaInputTests(unittest.TestCase):
    def test_chim_seyda_requires_the_recorded_maps_before_setup(self):
        err = io.StringIO()
        with patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(err), \
                self.assertRaises(SystemExit) as stop:
            build.main(['--builder', 'chim', '--chim-area', 'seyda', '--check'])
        self.assertEqual(stop.exception.code, 1)
        self.assertIn('--seyda-recorded', err.getvalue())
        setup.assert_not_called()

    def test_default_build_needs_the_recorded_maps_with_a_clear_message(self):
        # v0.0.33: the shipped default is --builder chim with Balmora and Seyda Neen.
        args = build.parser().parse_args([])
        with self.assertRaises(ValueError) as stop:
            build.chim_seyda_input(args)
        for text in ('--seyda-recorded DIR', 'v0.0.31', 'shipped default', 'BUILD-SEYDA-REGEN-30',
                     '--builder legacy', '--chim-area balmora'):
            self.assertIn(text, str(stop.exception))
        for argv in (['--dry-run'], ['--stage', 'terrain'], ['--chim-area', 'balmora'], ['--builder', 'legacy']):
            with self.subTest(argv=argv):
                build.chim_seyda_input(build.parser().parse_args(argv))   # asset-free, terrain, no Seyda, legacy
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            build.chim_seyda_input(build.parser().parse_args(['--install-sdk']))   # setup only: a note
        self.assertIn('Note: ', out.getvalue())

    def test_given_or_not_needed(self):
        for argv, given in ((['--builder', 'chim', '--chim-area', 'balmora'], False),
                            (['--builder', 'chim', '--chim-area', 'seyda', '--dry-run'], False),
                            (['--builder', 'chim', '--chim-area', 'seyda'], True)):
            with self.subTest(argv=argv):
                args = build.parser().parse_args(argv)
                if given:
                    args.seyda_recorded = Path('/recorded')
                build.chim_seyda_input(args)

    def test_recorded_maps_reach_the_image_step(self):
        steps = plan(BOTH + ['--seyda-recorded', '/recorded'])
        image = [str(p) for p in dict(steps)['image']]
        self.assertEqual(image[image.index('--seyda-recorded') + 1], str(Path('/recorded')))


def region_table(path, names):
    path.write_text('AWBR1 0 0 0 0 0\n' + ''.join('%s -100 -100 100 100\n' % n for n in names),
                    encoding='ascii', newline='\n')


class SafetyNetTests(unittest.TestCase):
    def image_id1(self, tmp):
        from town_config import runtime_towns
        row = next(t for t in runtime_towns() if t['id'] == 'balmora')
        id1 = Path(tmp) / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        region_table(id1 / row['regions'], ['bm001', 'bm002'])
        for name in ('bm001', 'bm002', row['name'], 'balmora-chim', 'interior01'):
            (id1 / 'maps' / (name + '.bsp')).write_bytes(b'BSP')
        return id1

    def test_a_legacy_map_of_a_chim_area_fails_the_build(self):
        from chim.frame_map import require_no_legacy_areas
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.image_id1(tmp)
            with self.assertRaisesRegex(ValueError, r'3 legacy exterior map\(s\) of CHIM areas'):
                require_no_legacy_areas(id1, ['balmora'], 'final image payload')

    def test_after_removal_the_check_passes_and_keeps_frame_map_and_interiors(self):
        from chim.frame_map import remove_legacy_areas, require_no_legacy_areas
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.image_id1(tmp)
            removed = remove_legacy_areas(id1, ['balmora'], 'the town runs on CHIM')
            self.assertEqual(len(removed), 3)
            record = require_no_legacy_areas(id1, ['balmora'], 'final image payload')
            self.assertEqual(record['status'], 'passed')
            json.dumps(record)
            self.assertEqual(sorted(p.name for p in (id1 / 'maps').iterdir()), ['balmora-chim.bsp', 'interior01.bsp'])
            # a later pass putting one back is caught
            (id1 / 'maps/bm002.bsp').write_bytes(b'BSP')
            with self.assertRaisesRegex(ValueError, 'bm002'):
                require_no_legacy_areas(id1, ['balmora'], 'final image payload')

    def test_image_step_checks_before_packing_and_records_it(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        check = source.index("require_no_legacy_areas(boot/'id1', chim_frames['areas'], 'final image payload',")
        self.assertLess(source.index("remove_legacy_areas(boot/'id1'"), check)
        self.assertLess(check, source.index('world_images=pack_world_volumes('))
        self.assertIn("chim_world['legacy_check']=legacy_check", source)


class NotOnChimTests(unittest.TestCase):
    """Owner decision for pass 2: extra towns not on CHIM yet (the Vivec Arena) leave a CHIM image."""

    def image_id1(self, tmp):
        id1 = Path(tmp) / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        region_table(id1 / 'vivec_arena-regions.txt', ['va001', 'va002'])
        for name in ('va001', 'va002', 'va003', 'vivec_arena', 'bm001', 'balmora-chim'):
            (id1 / 'maps' / (name + '.bsp')).write_bytes(b'BSP')
        for name in ('scene-doors-vivec_arena.txt', 'harvest-va001.txt', 'harvest-bm001.txt'):
            (id1 / name).write_bytes(b'x')
        return id1

    def test_the_arena_leaves_whole_and_is_recorded(self):
        from chim.frame_map import NOT_ON_CHIM, remove_towns_not_on_chim, require_no_legacy_areas
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.image_id1(tmp)
            rows = remove_towns_not_on_chim(id1, ['vivec_arena'])
            self.assertEqual(sorted(r['file'] for r in rows), [
                'harvest-va001.txt', 'maps/va001.bsp', 'maps/va002.bsp', 'maps/va003.bsp', 'maps/vivec_arena.bsp',
                'scene-doors-vivec_arena.txt', 'vivec_arena-regions.txt'])
            self.assertEqual({(r['town'], r['reason']) for r in rows}, {('vivec_arena', NOT_ON_CHIM)})
            self.assertTrue(all(set(r) == {'file', 'bytes', 'sha256', 'town', 'reason'} for r in rows))
            self.assertEqual(sorted(p.name for p in id1.rglob('*') if p.is_file()),
                             ['balmora-chim.bsp', 'bm001.bsp', 'harvest-bm001.txt'])
            record = require_no_legacy_areas(id1, [], 'final image payload', not_on_chim=['vivec_arena'])
            self.assertEqual(record['not_on_chim'], ['vivec_arena'])
            (id1 / 'maps/va002.bsp').write_bytes(b'BSP')
            with self.assertRaisesRegex(ValueError, 'va002'):
                require_no_legacy_areas(id1, [], 'final image payload', not_on_chim=['vivec_arena'])

    def test_the_starting_towns_are_never_dropped(self):
        from chim.frame_map import remove_towns_not_on_chim
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Not an extra town'):
                remove_towns_not_on_chim(self.image_id1(tmp), ['seyda'])

    def test_image_step_drops_only_in_chim_builds_and_before_the_gates(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        block = source[source.index("chim_frames = chim_frame_maps(args.chim_world, boot/'id1')"):]
        drop = block.index('remove_towns_not_on_chim(boot/')
        rebind = block.index('rebind_chim_maps(boot/')
        self.assertLess(drop, rebind)
        self.assertLess(rebind, block.index('audit_world_map_heap_with_receipt('))
        self.assertLess(block.index('require_stairs('), block.index('audit_world_map_heap_with_receipt('))
        self.assertLess(rebind, block.index('require_stairs('))
        self.assertIn("chim_world['not_on_chim']=not_on_chim", source)


def optimizer_receipt(maps, names):
    from optimize_world_maps import sha
    rows = [{'map': n, 'input_sha256': sha((maps / n).read_bytes()), 'output_sha256': sha((maps / n).read_bytes()),
             'file_bytes_saved': 0, 'changed': False} for n in names]
    return {'status': 'verified', 'maps': rows, 'committed_maps': [], 'map_count': len(rows)}


class OptimizerRebindTests(unittest.TestCase):
    def test_frame_maps_in_removed_maps_out_then_verified(self):
        from optimize_world_maps import rebind_chim_maps, verify_optimized_maps
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            for name in ('bm001', 'bm002', 'interior01'):
                (maps / (name + '.bsp')).write_bytes(name.encode())
            report = optimizer_receipt(maps, ['bm001.bsp', 'bm002.bsp', 'interior01.bsp'])
            # the CHIM image: frame map written, legacy maps removed; the old receipt no longer binds
            (maps / 'balmora-chim.bsp').write_bytes(b'frame')
            for name in ('bm001', 'bm002'):
                (maps / (name + '.bsp')).unlink()
            with self.assertRaises(ValueError):
                verify_optimized_maps(maps, report)
            path = Path(tmp) / 'optimize-world-maps.json'
            report = rebind_chim_maps(maps, report, path, ['maps/bm001.bsp', 'maps/bm002.bsp', 'balmora-regions.txt'])
            verify_optimized_maps(maps, report)
            self.assertEqual([r['map'] for r in report['maps']], ['balmora-chim.bsp', 'interior01.bsp'])
            self.assertEqual(report['chim_rebind'], {'removed': ['bm001.bsp', 'bm002.bsp'],
                                                     'added_frame_maps': ['balmora-chim.bsp']})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['map_count'], 2)

    def test_anything_else_stops_the_image(self):
        from optimize_world_maps import rebind_chim_maps
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            (maps / 'bm001.bsp').write_bytes(b'a')
            report = optimizer_receipt(maps, ['bm001.bsp'])
            (maps / 'stray.bsp').write_bytes(b'b')
            with self.assertRaisesRegex(ValueError, 'not CHIM frame maps'):
                rebind_chim_maps(maps, dict(report), Path(tmp) / 'r.json', [])
            (maps / 'stray.bsp').unlink()
            (maps / 'bm001.bsp').unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                rebind_chim_maps(maps, dict(report), Path(tmp) / 'r.json', [])


if __name__ == '__main__':
    unittest.main()
