# SPDX-License-Identifier: GPL-3.0-only
"""Per-cell lighting audit (tools/cell_lighting.py): classification, reach per mode, surfaces and status precedence.

Synthetic records only (made-up identifiers and numbers). No game data.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cell_lighting as lt  # noqa: E402
import light_sources as ls  # noqa: E402


def placed(**classes):
    """placed(pure_light=(0, 2), lamp=(1, 0)): class -> (with a mesh, without)."""
    rows = []
    for k, (m, n) in classes.items():
        rows += [(k, True, 0, 0)] * m + [(k, False, 0, 0)] * n
    return lt.light_census_cell(rows)


class LightingAuditTests(unittest.TestCase):
    def test_census_light_classifies_mesh_and_style(self):
        self.assertEqual(lt.census_light('syn_light_256', {'model': '', 'lflags': 0}), ('pure_light', False, 0, ls.STYLE_SOURCE))
        self.assertEqual(lt.census_light('syn_shroom_glow', {'model': '', 'lflags': ls.PULSE}),
                         ('glow_plant', False, ls.PULSE, ls.STYLE_SOURCE_PULSE))
        self.assertEqual(lt.census_light('syn_dark', {'model': '', 'lflags': ls.NEGATIVE})[0], 'negative')
        self.assertEqual(lt.census_light('syn_lantern', {'model': 'meshes/l/syn_lantern.nif', 'lflags': ls.FLICKER}),
                         ('lamp', True, ls.FLICKER, ls.STYLE_SOURCE_FLICKER))
        self.assertEqual(lt.census_light('syn_lantern', {'model': 'meshes/l/syn_lantern.nif', 'lflags': 0}, False)[3],
                         ls.STYLE_SOURCE)
        self.assertEqual(lt.census_light('syn_off', {'model': 'x.nif', 'lflags': ls.OFF_DEFAULT})[0], 'off')

    def test_cell_summary_counts_classes_styles_and_leaves_off_lights_out_of_the_styles(self):
        s = lt.light_census_cell([('pure_light', False, 0, 0), ('lamp', True, ls.FLICKER, 32), ('off', True, ls.FLICKER, 0)])
        self.assertEqual(s['placed'], 3)
        self.assertEqual(s['by_class'], {'lamp': {'mesh': 1, 'meshless': 0}, 'pure_light': {'mesh': 0, 'meshless': 1},
                                         'off': {'mesh': 1, 'meshless': 0}})
        self.assertEqual(s['styles'], {'0': 1, '32': 1})
        self.assertEqual(s['animated'], 1)
        self.assertEqual(lt.totals(s), (2, 1, 1, 1))

    def test_reach_per_mode(self):
        p = placed(pure_light=(0, 2), lamp=(1, 0), fire=(0, 1), off=(1, 0))
        self.assertEqual(lt.reach(p, 'none'), {'baked': 0, 'lamp_table': 0, 'none': 4})
        self.assertEqual(lt.reach(p, 'lamps'), {'baked': 0, 'lamp_table': 2, 'none': 2})
        self.assertEqual(lt.reach(p, 'baked'), {'baked': 4, 'lamp_table': 0, 'none': 0})
        self.assertEqual(lt.reach(p, 'baked', baked=3), {'baked': 3, 'lamp_table': 0, 'none': 1})
        with self.assertRaises(ValueError):
            lt.reach(p, 'sunshine')

    def test_status_precedence(self):
        lit = {'mode': 'baked', 'terrain_faces': 8, 'terrain_lit': 8, 'model_faces': 2, 'model_lit': 2}
        p = placed(pure_light=(0, 2))
        self.assertEqual(lt.audit(p, lit)['status'], 'lit')
        self.assertEqual(lt.audit(p, dict(lit, baked=1))['status'], 'partial')        # one light not baked
        self.assertEqual(lt.audit(p, dict(lit, terrain_lit=4))['status'], 'partial')  # surfaces not all lit
        a = lt.audit(p, None, stats={'faces': {'chim_terrain': 8, 'chim_placed': 2}})   # today's builds
        self.assertEqual((a['status'], a['mode'], a['assumed'], a['surfaces']['lit_share']), ('unlit', 'lamps', True, 0.0))
        self.assertIn('assumed', a['reason'])
        lamps = lt.audit(placed(lamp=(1, 0)), None, stats={'faces': {'chim_terrain': 8}})
        self.assertEqual(lamps['status'], 'partial')                                     # night lamps only
        self.assertEqual(lt.audit(placed(), {'mode': 'lamps', 'terrain_faces': 4, 'terrain_lit': 0})['status'], 'unlit')
        self.assertEqual(lt.audit(placed(), dict(lit, mode='lamps'))['status'], 'lit')  # no sources, surfaces lit
        self.assertEqual(lt.audit(p, lit, converted=False)['status'], 'not_measured')
        self.assertEqual(lt.audit(None, lit)['status'], 'not_measured')
        self.assertEqual(tuple(lt.STATUS_TEXT), lt.STATUSES)

    def test_headline_sums_status_classes_and_reach(self):
        lit = {'mode': 'baked', 'terrain_faces': 1, 'terrain_lit': 1}
        audits = [lt.audit(placed(pure_light=(0, 2)), lit), lt.audit(placed(glow_plant=(1, 1)), None),
                  lt.audit(placed(negative=(0, 1)), lit, converted=False)]
        h = lt.headline(audits)
        self.assertEqual(h['status'], {'lit': 1, 'partial': 0, 'unlit': 1, 'not_measured': 1})
        self.assertEqual(h['lights']['glow_plant'], {'mesh': 1, 'meshless': 1})
        self.assertEqual(h['lights']['negative'], {'mesh': 0, 'meshless': 1})
        self.assertEqual(h['reach'], {'baked': 2, 'lamp_table': 0, 'none': 2})
        self.assertEqual(h['cells_with_lights'], 3)

    def test_toolkit_has_the_lighting_layer_and_headline_line(self):
        page = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')
        for needle in ('CHIM_LIGHTING', "['lighting', 'Lighting (lit / partial / unlit)']", 'chimLightingBlock(c)'):
            self.assertIn(needle, page)
        for k in lt.STATUSES:
            self.assertIn(k + ': [', page)
        self.assertIn('lightLine(h.lighting)', (ROOT / 'amiwind-toolkit' / 'chim-head.js').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
