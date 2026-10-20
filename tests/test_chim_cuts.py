# SPDX-License-Identifier: GPL-3.0-only
"""CHIM distance cuts and the fog (CHIM-BRIDGE-POP-PIECES-44): the fog rule's builder check, whole-structure cut
groups found from the frame's data (tools/chim/cuts.py), their sidecar beside the frame map, and the engine's loader
(native, tests/aga_chim_cuts_test.c)."""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import cuts  # noqa: E402

SRC = ROOT / 'engine/aga/src'
SETTINGS = {'draw_distance': 540.0, 'hysteresis': 96.0}


def piece(pid, model, x0, x1, y0=-20, y1=20, z0=0, z1=40):
    return {'pid': pid, 'model': model, 'box': ((x0, y0, z0), (x1, y1, z1)),
            'origin': ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)}


# A walkway along x: two long bridge pieces and a short gap piece between them (51 units apart, as Vivec's),
# a canton tiled by the large-model cut, a lone bridge piece far away, a touching piece of another family.
NAMES = ['x/ex_vivec_b_01@s1', 'x/ex_vivec_b_wb_gap_01@s1', 'x/ex_vivec_c_04@s1@tile0,0', 'x/ex_vivec_c_04@s1@tile0,1',
         'x/ex_hlaalu_wall_01@s1', 'x/ex_vivec_b_01@s1#2']
WALKWAY = [piece(10, 0, 0, 400), piece(11, 1, 451, 480), piece(12, 0, 531, 931),
           piece(20, 2, 2000, 2300, 100, 400), piece(21, 3, 2000, 2300, 400, 700),
           piece(30, 5, 6000, 6400),
           piece(40, 4, 931, 1100)]


class FogRuleTests(unittest.TestCase):
    """No cut nearer than the fog's full-opacity depth."""

    def test_fog_levels_mirror_the_engine(self):
        # aw_fog.c AW_FogDepths: level L from D*(10+L)/25, 15 (one colour) at D
        self.assertEqual(cuts.fog_level(540, 540), 15)
        self.assertEqual(cuts.fog_level(.44 * 540 + .01, 540), 1)
        self.assertEqual(cuts.fog_level(.40 * 540, 540), 0)
        self.assertEqual(cuts.fog_level(.85 * 540, 540), 11)
        self.assertEqual(cuts.fog_full_depth(540), 540)
        fog = (SRC / 'aw_fog.c').read_text()
        self.assertIn('last=819200/(distance*(10+level));', fog)
        self.assertIn('last=819200/(distance*25);', fog)

    def test_size_cut_shares_mirror_the_engine_table(self):
        fog = (SRC / 'aw_fog.c').read_text()
        found = re.search(r'size_cut_share\[2\]\[4\]=\{\{([^}]*)\},\{([^}]*)\}\};', fog)
        self.assertTrue(found)
        for preset, row in ((1, found.group(1)), (2, found.group(2))):
            self.assertEqual(tuple(float(v.strip().rstrip('f')) for v in row.split(',')), cuts.SIZE_CUT_SHARE[preset])
        self.assertIn('radius<32?0:radius<128?1:radius<512?2:3', fog)
        self.assertEqual(cuts.SIZE_CLASSES, (32, 128, 512))

    def test_presets_cut_before_the_fog_end_without_the_rule_and_not_with_it(self):
        old = cuts.fog_cut_failures(SETTINGS, modes=(3, 4, 5, 6), fog_rule=False)
        self.assertTrue(any('aw_cull 4 size cut, radius 0 and over at 216' in f for f in old), old)
        self.assertTrue(any('far detail step at 270' in f for f in old), old)
        self.assertEqual(cuts.fog_cut_failures(SETTINGS, modes=(0, 1, 2, 3, 4, 5, 6), fog_rule=True), [])
        for preset in (1, 2):
            for r in (0, 31, 32, 127, 128, 511, 512, 4000):
                self.assertGreaterEqual(cuts.size_share(preset, r, fog_rule=True), 1.0)

    def test_world_check_refuses_a_ring_nearer_than_the_fog_end(self):
        self.assertEqual(cuts.fog_cut_failures(SETTINGS), [])
        fails = cuts.fog_cut_failures({'draw_distance': 540.0, 'hysteresis': -40.0})
        self.assertEqual(len(fails), 1)
        self.assertIn('chunk ring', fails[0])
        self.assertTrue(cuts.fog_cut_failures({'draw_distance': 0, 'hysteresis': 96}))

    def test_world_check_refuses_a_member_outside_its_structure_box(self):
        box = ((0, -20, 0), (931, 20, 40))
        ok = {10: (0, ((0, -20, 0), (400, 20, 40)))}
        self.assertEqual(cuts.fog_cut_failures(SETTINGS, [box], ok), [])
        out = {10: (0, ((0, -20, 0), (1000, 20, 40)))}
        self.assertIn('outside its structure', cuts.fog_cut_failures(SETTINGS, [box], out)[0])
        self.assertIn('does not exist', cuts.fog_cut_failures(SETTINGS, [box], {10: (3, box)})[0])

    def test_engine_rule_and_groups_default_off_until_the_maintainers_ab(self):
        fog = (SRC / 'aw_fog.c').read_text()
        # both switches are bits of aw_cull (no registry entry of their own), off in the default 4 (Strong)
        self.assertIn('static cvar_t aw_cull={"aw_cull","4",true};', fog)
        self.assertNotIn('aw_fog_rule', fog)
        self.assertNotIn('aw_cut_groups', fog)
        head = (SRC / 'quakedef.h').read_text()
        for line in ('#define AW_CULL_TEST 7', '#define AW_CULL_FOG_RULE 8', '#define AW_CULL_GROUPS 16',
                     '#define AW_CULL_MAX 31'):
            self.assertIn(line, head)
        self.assertIn('fog_rule=!AW_Interior() && ((int)aw_cull.value&AW_CULL_FOG_RULE);', fog)
        self.assertIn('((int)aw_cull.value&AW_CULL_GROUPS)', fog)
        table = (ROOT / 'config/debug-commands.txt').read_text()
        self.assertIn('VIDEO|fog rule|aw_cull|', table)
        self.assertIn('VIDEO|cut groups|aw_cull|', table)
        menu = (SRC / 'aw_menu.c').read_text()
        self.assertIn('far_values[i]|((int)Cvar_VariableValue("aw_cull")&~AW_CULL_TEST)', menu)   # menu keeps the bits


class StructureTests(unittest.TestCase):
    def test_stems_and_families(self):
        self.assertEqual(cuts.stem('x/ex_vivec_b_wb_gap_01@s1'), ('x/ex', 'vivec', 'b', 'wb', 'gap'))
        self.assertEqual(cuts.stem('x/ex_dae_wall_512_05@s1@t6.1,0.1,3.7'), ('x/ex', 'dae', 'wall'))
        self.assertEqual(cuts.stem('x/ex_vivec_c_04@s1@tile0,2'), ('x/ex', 'vivec', 'c'))
        self.assertEqual(cuts.stem('x/ex_vivec_b_01@s1#2'), ('x/ex', 'vivec', 'b'))
        self.assertTrue(cuts.same_family(cuts.stem('x/ex_vivec_b_01'), cuts.stem('x/ex_vivec_b_wb_gap_01')))
        self.assertTrue(cuts.same_family(cuts.stem('x/ex_gg_fence_01'), cuts.stem('x/ex_gg_fence_s_h_01')))
        self.assertFalse(cuts.same_family(cuts.stem('x/ex_vivec_b_01'), cuts.stem('x/ex_vivec_bt_01')))
        self.assertFalse(cuts.same_family(cuts.stem('x/ex_gg_02'), cuts.stem('x/ex_gg_fence_01')))   # 2-token stem
        self.assertFalse(cuts.same_family(cuts.stem('f/terrain_rock_ai_01'), cuts.stem('f/terrain_rocks_ai_01')))

    def test_walkway_canton_tiles_and_loners(self):
        found = cuts.structures(WALKWAY, NAMES)
        members = [s['members'] for s in found]
        self.assertIn([10, 11, 12], members)        # bridge, gap piece, bridge: one walkway
        self.assertIn([20, 21], members)            # the canton's tiles
        self.assertFalse(any(30 in m or 40 in m for m in members))   # far away; another family
        walk = found[members.index([10, 11, 12])]
        self.assertEqual(walk['box'], ((0, -20, 0), (931, 20, 40)))
        self.assertEqual(walk['span'], 931)
        # order and content do not depend on the input order
        self.assertEqual(cuts.structures(list(reversed(WALKWAY)), NAMES), found)

    def test_short_clusters_are_no_structure(self):
        rows = [piece(1, 0, 0, 100), piece(2, 0, 120, 200)]
        self.assertEqual(cuts.structures(rows, NAMES), [])
        self.assertEqual(len(cuts.structures(rows, NAMES, min_span=100)), 1)


class SidecarTests(unittest.TestCase):
    def test_round_trip_and_refusals(self):
        found = cuts.structures(WALKWAY, NAMES)
        data = cuts.encode((4, -12), found)
        head, boxes, members = cuts.decode(data)
        self.assertEqual(head, {'cell': (4, -12), 'structures': 2, 'members': 5})
        self.assertEqual(members, {10: 0, 11: 0, 12: 0, 20: 1, 21: 1})
        self.assertEqual(boxes[0], ((0, -20, 0), (931, 20, 40)))
        bad = bytearray(data)
        bad[-3] ^= 1
        with self.assertRaises(ValueError):
            cuts.decode(bytes(bad))
        with self.assertRaises(ValueError):
            cuts.decode(data[:-1])
        with self.assertRaises(ValueError):
            cuts.encode((0, 0), [{'box': ((0, 0, 0), (1, 1, 1)), 'members': [1]},
                                 {'box': ((0, 0, 0), (1, 1, 1)), 'members': [1]}])
        self.assertEqual(cuts.sidecar_name('maps/vf1234.bsp'), 'maps/vf1234.cut')
        self.assertEqual(cuts.file_name((-3, -2)), '-3_-2.cut')

    def test_image_step_installs_it_beside_the_frame_map(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            world, id1 = Path(tmp) / 'world', Path(tmp) / 'id1'
            (world / 'cuts').mkdir(parents=True)
            (id1 / 'maps').mkdir(parents=True)
            data = cuts.encode((4, -12), cuts.structures(WALKWAY, NAMES))
            (world / 'cuts' / '4_-12.cut').write_bytes(data)
            (world / 'cuts' / '1_1.cut').write_bytes(cuts.encode((1, 1), []))
            row = build_aga.chim_cut_sidecar(world, id1, {'frame': [4, -12], 'map': 'maps/vivec_city.bsp'})
            self.assertEqual(row['file'], 'maps/vivec_city.cut')
            self.assertEqual((id1 / 'maps/vivec_city.cut').read_bytes(), data)
            self.assertIsNone(build_aga.chim_cut_sidecar(world, id1, {'frame': [1, 1], 'map': 'maps/a.bsp'}))
            self.assertIsNone(build_aga.chim_cut_sidecar(world, id1, {'frame': [9, 9], 'map': 'maps/b.bsp'}))
            with self.assertRaises(ValueError):       # a file naming another frame
                (world / 'cuts' / '2_2.cut').write_bytes(data)
                build_aga.chim_cut_sidecar(world, id1, {'frame': [2, 2], 'map': 'maps/c.bsp'})

    def test_builder_writes_and_checks_after_the_far_terrain(self):
        text = (ROOT / 'tools/chim/build.py').read_text()
        self.assertLess(text.index('write_layers(out,'), text.index('rows = write_groups(out, jobs=jobs)'))
        self.assertIn("'fog_check': 'passed", text)
        image = (ROOT / 'tools/build_aga.py').read_text()
        self.assertIn("record['cut_groups'] = chim_cut_sidecar(chim_world, id1, record)", image)


class PaperCostTests(unittest.TestCase):
    """The on-paper count (drawn_counts) decides as the engine's tests do: a small middle piece of a walkway is
    cut by the Strong preset while the long pieces stay; with the structure all three stay or go together."""

    def setUp(self):
        frame = {'grain': 256, 'low': (-2048.0, -2048.0)}
        rows = [dict(r, origin=r['origin']) for r in WALKWAY[:3]]
        self.paper = cuts.PaperFrame(rows, cuts.structures(rows, NAMES), frame)

    def test_middle_piece(self):
        # the gap piece's near side 534 away: past 40 % of 540 (its size class); the far bridge piece past the far
        # plane; the structure's box begins 100 away
        viewer = (-100.0, 0.0)
        a = cuts.drawn_counts(self.paper, viewer, 540, 96, mode=4)
        c = cuts.drawn_counts(self.paper, viewer, 540, 96, mode=4, groups=True)
        self.assertEqual(c[0], 3)
        self.assertLess(a[0], 3)
        b = cuts.drawn_counts(self.paper, viewer, 540, 96, mode=4, fog_rule=True)
        self.assertGreaterEqual(b[0], a[0])
        far = cuts.drawn_counts(self.paper, (-2000.0, 0.0), 540, 96, mode=4, groups=True)
        self.assertEqual(far[0], 0)     # past the cut: all of it goes


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class LoaderNativeTests(unittest.TestCase):
    SOURCES = [SRC / 'chim/chim_cuts.c', SRC / 'chim/chim_format.c']

    def test_loader_reads_the_writers_file_and_refuses_damaged_ones(self):
        from test_chim_engine_native import compile_and_run
        found = cuts.structures(WALKWAY, NAMES)
        ok = cuts.encode((4, -12), found)
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            (maps / 'cuts-ok.cut').write_bytes(ok)
            bad = bytearray(ok)
            bad[30] ^= 4
            (maps / 'cuts-crc.cut').write_bytes(bytes(bad))
            (maps / 'cuts-frame.cut').write_bytes(cuts.encode((4, -11), found))
            (maps / 'cuts-short.cut').write_bytes(ok[:-1])
            # members out of order (a valid CRC over a body the writer would never make)
            import struct
            import zlib
            body = (cuts.BOX.pack(0, 0, 0, 1, 1, 1) + cuts.MEMBER.pack(9, 0, 0) + cuts.MEMBER.pack(5, 0, 0))
            (maps / 'cuts-order.cut').write_bytes(cuts.HEADER.pack(cuts.MAGIC, 1, 24, 4, -12, 1, 2,
                                                                  zlib.crc32(body) & 0xFFFFFFFF) + body)
            del struct
            args = ['load', 4, -12]
            for k, s in enumerate(found):
                for pid in s['members']:
                    args += [pid, k, s['box'][0][0]]
            args += ['-', 30, 40, 1, 999]
            out = compile_and_run(self, 'aga_chim_cuts_test.c', self.SOURCES, [args], cwd=tmp)
            self.assertIn('5 refused files give no box', out[0])

    def test_placements_take_their_box_and_the_map_forgets_it(self):
        chunks = (SRC / 'chim/chim_chunks.c').read_text()
        self.assertIn('p->ent.aw_cut_box = ChimCuts_Box (r.pid);', chunks)
        world = (SRC / 'chim/chim_world.c').read_text()
        end = world[world.index('static void MapEnd (void)'):]
        self.assertLess(end.index('ChimCuts_End ();'), end.index('if (!active && map_bank < 0)'))
        self.assertLess(world.index('ChimFar_Begin (MapModel ()'), world.index('ChimCuts_Begin (MapModel ()'))
        self.assertIn('chim/chim_cuts.c', (ROOT / 'engine/aga/Makefile').read_text())
        main = (SRC / 'r_main.c').read_text()
        self.assertIn('AW_FarGroup(currententity->aw_cut_box);', main)
        self.assertIn('if(!AW_PassVisible(currententity->origin,clmodel->radius))break;', main)


if __name__ == '__main__':
    unittest.main()
