"""A pure-CHIM disk (no legacy exterior maps of the CHIM towns, only maps/<town>-chim.bsp and the
region tables): arrivals, saves, the scene checks and a save/load round trip in CHIM Balmora work,
and the same paths still work on a legacy disk (tests/aga_chim_save_test.c)."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class PureChimDiskTests(unittest.TestCase):
    def test_scene_checks_and_save_load_without_legacy_town_maps(self):
        src = ROOT / 'engine/aga/src'
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / 'saves/p00000002').mkdir(parents=True)
            binary = work / 'chim-save'
            build = subprocess.run(
                ['cc', '-std=gnu99', '-O1', '-g', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                 '-Wall', '-Werror', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-pointer-sign',
                 '-Wno-format-truncation', '-Wno-stringop-truncation',
                 '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-I' + str(src),
                 str(ROOT / 'tests/aga_chim_save_test.c'),
                 *(str(src / n) for n in ('aw_character.c', 'aw_state.c', 'aw_save_codec.c', 'aw_region.c', 'aw_format.c',
                                          'aw_world.c')),
                 '-lm', '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(binary), str(work)], capture_output=True, text=True,
                                 env={'ASAN_OPTIONS': 'detect_leaks=0'})
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('disk chim ok', run.stdout)
            self.assertIn('disk legacy ok', run.stdout)
            # dbg tp on a pure-CHIM disk (DEBUG-TP-CHIM-33): only what the disk has is offered.
            self.assertIn('tp chim: seydaneen/balmora/vivec_arena/vivec', run.stdout)
            self.assertIn('tp legacy: seydaneen/prisonship/balmora/vivec_arena/vivec_foreign/', run.stdout)

    def test_dbg_tp_source_forms(self):
        # dbg tp X Y [Z]: the router passes three numbers, the command takes Z, and a Z teleport lands on
        # the first floor at or below it (AW_MapPlaceBelow) before the usual search.
        src = ROOT / 'engine/aga/src'
        console = (src / 'aw_console.c').read_text()
        self.assertIn('"aw_teleport") && argc-j>3)return 0;', console)
        scene = (src / 'aw_scene.c').read_text()
        self.assertIn('if(Cmd_Argc()==3 || Cmd_Argc()==4) {', scene)
        self.assertIn('AW_MapTeleportAt(source,Cmd_Argc()==4)', scene)
        self.assertIn('placed=(map_jump==2 && AW_MapPlaceBelow(p,next.arrival)) || arrival_place(p,next.arrival,1);', scene)
        self.assertIn('Unknown destination: %s.', scene)
        self.assertIn('AW_TeleportDestinations(names,sizeof(names))', scene)
        self.assertIn('map_place(p,point,point[2])', (src / 'aw_spawn.c').read_text())


if __name__ == '__main__':
    unittest.main()
