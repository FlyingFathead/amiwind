# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-INTRO-SEAM-STOP-CHARGEN-CLASS-64: the builder's NPC bake defaults are the settings the shipped builds use, so a
build started without them bakes as the release builds do instead of stopping in the intro stage."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build  # noqa: E402


class ShippedBakeDefaults(unittest.TestCase):
    def test_an_empty_environment_gets_the_shipped_settings(self):
        env = build.apply_shipped_bake_defaults({})
        self.assertEqual(env, {'AMIWIND_MESH_SEAM_STOP': 'warn', 'AMIWIND_NPC_BODY_CHECK': 'warn',
                               'AMIWIND_NPC_BAKE_FALLBACK': 'dev1'})

    def test_a_set_value_is_kept(self):
        env = build.apply_shipped_bake_defaults({'AMIWIND_MESH_SEAM_STOP': 'ratchet', 'AMIWIND_NPC_BODY_CHECK': ' '})
        self.assertEqual(env['AMIWIND_MESH_SEAM_STOP'], 'ratchet')
        self.assertEqual(env['AMIWIND_NPC_BODY_CHECK'], 'warn')

    def test_the_build_and_the_reuse_plan_set_them_in_the_one_stage_environment(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        start = text.index('def export_option_environment(')
        self.assertIn('apply_shipped_bake_defaults()', text[start:start + 1200])
        self.assertEqual(text.count('apply_shipped_bake_defaults()'), 1)

    def test_the_bake_reads_them(self):
        import npc_geometry
        saved = {k: os.environ.get(k) for k, _ in build.SHIPPED_BAKE_DEFAULTS}
        try:
            for k, _ in build.SHIPPED_BAKE_DEFAULTS:
                os.environ.pop(k, None)
            build.apply_shipped_bake_defaults()
            self.assertEqual(npc_geometry.seam_stop_mode(), 'warn')
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_the_reported_intro_stop_now_warns_and_the_bake_goes_on(self):
        """The reported build log: 'seam stop (worse): npc chargen class: 14 uncovered new openings' with the repo's
        baseline line for it (14 uncovered, least width 0.771) and a thinner limb from another copy of the game data.
        Without the defaults that line stops the intro stage; with them it is printed and the bake goes on."""
        import io
        import contextlib
        import npc_geometry
        from model_face_overrides import load_seam_baseline
        baseline = load_seam_baseline(ROOT / 'config' / 'mesh-seam-baseline.json')
        self.assertIn('npc:chargen class', baseline)
        saved = {k: os.environ.get(k) for k, _ in build.SHIPPED_BAKE_DEFAULTS}
        try:
            for k, _ in build.SHIPPED_BAKE_DEFAULTS:
                os.environ.pop(k, None)
            with self.assertRaisesRegex(npc_geometry.BakeStop,
                                        r'seam stop \(worse\): npc chargen class: 14 uncovered new openings'):
                npc_geometry.seam_stop('chargen class', 14, 0.6, False, baseline=baseline)
            build.apply_shipped_bake_defaults()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                status = npc_geometry.seam_stop('chargen class', 14, 0.6, False, baseline=baseline)
            self.assertEqual(status, 'worse')
            self.assertIn('seam stop (warn, worse): npc chargen class: 14 uncovered new openings', out.getvalue())
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == '__main__':
    unittest.main()
