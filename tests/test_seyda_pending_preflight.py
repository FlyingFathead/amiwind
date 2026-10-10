# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-SEYDA-CONVERTED-NOT-STAGED-35: the image step's early payload preflight runs before the image step
converts (or installs) the Seyda Neen region maps. A default build (CHIM with Seyda Neen, no recorded maps)
must pass its chim-inputs check with the conversion's plan, and still fail it when the conversion cannot run."""
import argparse
import contextlib
import inspect
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import build  # noqa: E402
import build_aga  # noqa: E402
import payload_preflight  # noqa: E402
import prepare_seyda_regions  # noqa: E402
from chim.frame_map import SPECIALS, region_table  # noqa: E402
from test_build_builder import plan  # noqa: E402

NL = bytes([10])
MISSING = 'seyda-regions.txt, maps/intro_docks.bsp, maps/sncourt.bsp'


def chim_world(base, areas=('seyda',)):
    """A CHIM world folder with passing receipts (build_aga.chim_world_receipt reads only these)."""
    world = Path(base) / 'chim-world'
    (world / 'chim').mkdir(parents=True)
    (world / 'chim/world.cwi').write_bytes(b'\0')
    (world / 'chim-receipt.json').write_text(json.dumps({'builder': 'chim', 'areas': list(areas)}), encoding='utf-8')
    (world / 'chim-validate.json').write_text(json.dumps({'ok': True, 'source_checked': True}), encoding='utf-8')
    (world / 'chim-stats.json').write_text('{}', encoding='utf-8')
    return world


def staged(base, *, seyda_map=True):
    """The failed run's state at the image step's early preflight: the scene's complete seyda.bsp copied
    into boot/id1/maps, no region table, no region or special maps; the scene keeps seyda.bsp/.map."""
    base = Path(base)
    scene = base / 'intro-scene'
    (scene / 'id1/maps').mkdir(parents=True)
    (scene / 'seyda.bsp').write_bytes(b'\0town')
    if seyda_map:
        (scene / 'seyda.map').write_text('{}\n', encoding='ascii')
    out = base / 'image'
    (out / 'boot/id1/maps').mkdir(parents=True)
    (out / 'boot/AmiWind').write_bytes(b'\0engine')
    (out / 'boot/id1/maps/seyda.bsp').write_bytes(b'\0town')
    return scene, out


def default_image_args(chim):
    """The default plan's image step options that decide the Seyda Neen source (build.py commands)."""
    command = [str(p) for p in dict(plan(['--jobs', '4']))['image']]
    return command, argparse.Namespace(miniwind='--miniwind' in command, chim_world=chim,
                                       seyda_recorded=None if '--seyda-recorded' not in command
                                       else command[command.index('--seyda-recorded') + 1])


def preflight(out, chim, pending):
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return payload_preflight.run(out, chim_world=chim, pending=pending), None
        except ValueError as exc:
            return None, exc


class SeydaPendingPreflightTests(unittest.TestCase):
    def test_default_plan_passes_chim_inputs_with_the_conversion_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            chim = chim_world(temp)
            scene, out = staged(temp)
            command, args = default_image_args(chim)
            self.assertIn('--chim-world', command)                 # the default build is a CHIM build
            self.assertIsNone(args.seyda_recorded)                 # ... converting Seyda Neen itself
            pending = build_aga.seyda_pending(args, scene)
            self.assertIsNotNone(pending)
            report, error = preflight(out, chim, pending)
            self.assertIsNone(error)
            self.assertNotIn('chim-inputs', [e['check'] for e in report['errors']])
            self.assertEqual(report['pending_from_image_step'], len(pending))

    def test_the_failed_run_state_without_the_plan_still_fails(self):
        # The check itself is unchanged: files neither staged nor planned are refused (the 901f8e9 run's error).
        with tempfile.TemporaryDirectory() as temp:
            chim = chim_world(temp)
            _, out = staged(temp)
            _, error = preflight(out, chim, None)
            self.assertIn('chim-inputs: CHIM frame map inputs are not staged: ' + MISSING, str(error))

    def test_no_plan_when_the_conversion_cannot_run(self):
        with tempfile.TemporaryDirectory() as temp:
            chim = chim_world(temp)
            scene, out = staged(temp, seyda_map=False)            # the conversion needs the scene's seyda.map
            _, args = default_image_args(chim)
            self.assertIsNone(build_aga.seyda_pending(args, scene))
            _, error = preflight(out, chim, build_aga.seyda_pending(args, scene))
            self.assertIn(MISSING, str(error))
            args.miniwind = True                                  # a MiniWind image converts no Seyda Neen
            self.assertIsNone(build_aga.seyda_pending(args, staged(Path(temp) / 'b')[0]))

    def test_a_plan_missing_a_region_map_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            chim = chim_world(temp)
            _, out = staged(temp)
            scene, _ = staged(Path(temp) / 'b')
            pending = build_aga.seyda_pending(default_image_args(chim)[1], scene)
            del pending['maps/sn005.bsp'], pending['maps/sncourt.bsp']
            _, error = preflight(out, chim, pending)
            self.assertIn('maps/sn005.bsp', str(error))
            self.assertIn('maps/sncourt.bsp', str(error))

    def test_plan_is_what_convert_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            scene, _ = staged(temp)
            pending = build_aga.seyda_pending(default_image_args(Path(temp))[1], scene)
            # The table convert() writes lists the layout's regions in order (the same text, parsed).
            entries = prepare_seyda_regions.regions()
            table = Path(temp) / 'seyda-regions.txt'
            table.write_text(prepare_seyda_regions.directory_text(entries), encoding='ascii', newline=chr(10))
            names = [name for name, _ in region_table(table)[1]]
        self.assertEqual(list(pending['seyda-regions.txt']), names)
        self.assertEqual(set(SPECIALS), set(build_aga.SEYDA_SPECIAL_MAPS))
        self.assertEqual(sorted(k for k in pending if k.startswith('maps/')),
                         sorted('maps/%s.bsp' % n for n in names + list(SPECIALS) + ['seyda']))
        source = inspect.getsource(prepare_seyda_regions.convert)
        for name in build_aga.SEYDA_SPECIAL_MAPS:                  # convert() writes the same special maps
            self.assertIn("('%s'," % name, source)
        self.assertIn("outputs['seyda']", source)

    def test_image_step_wiring(self):
        # The early preflight (and --check-payload) plan the Seyda Neen files; the late one checks them written.
        image = inspect.getsource(build_aga.image)
        self.assertIn('pending=None if mini else seyda_pending(args, scene)', image)
        self.assertIn('pending=seyda_pending(args, args.scene)', image)
        self.assertLess(image.index('seyda_pending(args, scene)'), image.index('convert_builder_scene('))
        finalize = inspect.getsource(build_aga.finalize_image)
        self.assertIn('payload_preflight(args, out, excluded, jobs)', finalize)
        self.assertNotIn('pending=', finalize)

    def test_recorded_plan_comes_from_the_pinned_set(self):
        import hashlib
        import recorded_stage
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            chim = chim_world(base)
            scene, out = staged(base)
            files = {'maps/%s.bsp' % n: n.encode() for n in ('sn000', 'sn001', 'intro_docks', 'sncourt', 'seyda')}
            files['seyda-regions.txt'] = (b'AWBR1 2 96 540 0 0 64 90 0 0 64 90' + NL + b'sn000 0 0 1 1 0 0 1 1' + NL +
                                          b'sn001 1 0 2 1 1 0 2 1' + NL)
            files['seyda-regions.json'] = json.dumps({'fallback_alias': 'sn000', 'regions': []}).encode()
            for name, raw in files.items():
                (base / 'recorded/id1' / name).parent.mkdir(parents=True, exist_ok=True)
                (base / 'recorded/id1' / name).write_bytes(raw)
            pin = base / 'pin.json'
            pin.write_text(json.dumps({'format': 'AmiWind recorded stage pin 1', 'exception': 'BUILD-SEYDA-REGEN-30',
                                       'files': [dict(file=n, bytes=len(r), sha256=hashlib.sha256(r).hexdigest())
                                                 for n, r in sorted(files.items())]}), encoding='utf-8')
            original = recorded_stage.load_pin
            args = argparse.Namespace(miniwind=False, seyda_recorded=base / 'recorded')
            with patch.object(recorded_stage, 'load_pin', lambda _pin=None: original(pin)):
                pending = build_aga.seyda_pending(args, scene)
            self.assertEqual(pending['seyda-regions.txt'], ('sn000', 'sn001'))
            report, error = preflight(out, chim, pending)
            self.assertIsNone(error)
            (base / 'recorded/id1/maps/sn001.bsp').write_bytes(b'changed')   # the pin check comes first
            with patch.object(recorded_stage, 'load_pin', lambda _pin=None: original(pin)),                     self.assertRaisesRegex(ValueError, 'differ'):
                build_aga.seyda_pending(args, scene)
            del pending['maps/sn001.bsp']
            _, error = preflight(out, chim, pending)
            self.assertIn('maps/sn001.bsp', str(error))


class SeydaReportPathTests(unittest.TestCase):
    """BUILD-SEYDA-REPORT-HOST-PATHS-35: the converted seyda-regions.json ships in the payload; it holds no build path."""

    def test_report_paths_are_relative_to_the_image_folder(self):
        import amiga_fs
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'image'
            work = out / 'bounded-seyda'
            report = {'complete_source_preserved': str(work / 'source-town.bsp'), 'overlap': 896, 'name': 'sn000',
                      'regions': [{'bounded': {'inputs': {'source_map': {'path': str(out / 'seyda.map'), 'sha256': 'ab'},
                                                          'palette': {'path': str(out / 'boot/id1/gfx/palette.lmp')}},
                                               'candidate_path': str(work / 'sn000/candidate.bsp')}}]}
            neutral = prepare_seyda_regions.neutral_paths(report, work.parent)
            self.assertEqual(neutral['complete_source_preserved'], 'bounded-seyda/source-town.bsp')
            bounded = neutral['regions'][0]['bounded']
            self.assertEqual(bounded['candidate_path'], 'bounded-seyda/sn000/candidate.bsp')
            self.assertEqual(bounded['inputs']['source_map'], {'path': 'seyda.map', 'sha256': 'ab'})
            self.assertEqual(bounded['inputs']['palette']['path'], 'boot/id1/gfx/palette.lmp')
            self.assertEqual((neutral['overlap'], neutral['name']), (896, 'sn000'))
            def strings(value):
                if isinstance(value, dict):
                    return [s for v in value.values() for s in strings(v)]
                if isinstance(value, list):
                    return [s for v in value for s in strings(v)]
                return [value] if isinstance(value, str) else []
            self.assertEqual([s for s in strings(neutral) if Path(s).is_absolute()], [])   # no absolute path left
            self.assertEqual(report['complete_source_preserved'], str(work / 'source-town.bsp'))  # caller's copy kept
            # The payload check the image step runs: the absolute form is refused, the written form passes.
            boot = out / 'boot'
            (boot / 'id1').mkdir(parents=True)
            table = boot / 'id1/seyda-regions.json'
            table.write_text(json.dumps(report), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'BUILD-PATH-IN-PAYLOAD-32'):
                amiga_fs.check_payload_host_paths(boot, [out.resolve()])
            table.write_text(json.dumps(neutral), encoding='utf-8')
            amiga_fs.check_payload_host_paths(boot, [out.resolve()])

    def test_convert_writes_the_neutral_report(self):
        source = inspect.getsource(prepare_seyda_regions.convert)
        self.assertIn("json.dumps(neutral_paths(report,work.parent)", source)
        self.assertIn("(work/'seyda-regions-full.json')", source)          # full paths stay in the build folder

if __name__ == '__main__':
    unittest.main()
