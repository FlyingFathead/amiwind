# SPDX-License-Identifier: GPL-3.0-only
"""The talk pack (tools/talk_pack.py, NPC-TALK-MOUTH-STILL-69, NPC-TALK-POSES-ONLY-OPENING-69): its format, the record
hash the engine computes (engine/aga/src/aw_talkpack.c AW_TalkHash), the head bone of the shared tables, and the
wiring (a stage that reads only the game data, its place in the plan, the image copying its file). The engine side
is tests/aga_talkpack_test.c (test_aga_native_source.py)."""
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'src', ROOT / 'tools'):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import numpy as np  # noqa: E402
import talk_pack as TP  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ (env_guard) when run as a file
import env_guard  # noqa: E402


def rows(n, shift=0.0):
    out = []
    for i in range(n):
        off = np.array([[0.1 * (lv + 1), -0.05 * (lv + 1), 0.02 * i] for lv in range(3)])
        out.append((1.5 + i + shift, -2.25, 30.0 - i, off))
    return out


class FormatTests(unittest.TestCase):
    def test_pack_reads_back(self):
        raw = TP.pack({'fargoth': 1, 'Socucius Ergalla': 0, 'hrisskar flat-foot': 1}, [rows(3), rows(5, .5)], 4)
        records, heads, bone = TP.read(raw)
        self.assertEqual(bone, 4)
        self.assertEqual(records[TP.fnv1a('fargoth')], 1)
        self.assertEqual(records[TP.fnv1a('SOCUCIUS ERGALLA')], 0)
        self.assertEqual([len(p) for p, _ in heads], [3, 5])
        pos, off = heads[1]
        self.assertTrue(np.allclose(pos[2], (4.0, -2.25, 28.0), atol=1 / TP.POSITION_UNITS))
        self.assertTrue(np.allclose(off[4], rows(5)[4][3], atol=1 / TP.OFFSET_UNITS))
        self.assertEqual(len(raw), TP.HEADER + 8 * 3 + 8 * 2 + TP.VERTEX_BYTES * 8)

    def test_hash_is_the_engines(self):
        # FNV-1a 32 of the id with ASCII letters lowered, as aw_talkpack.c AW_TalkHash (the C test checks the same values)
        self.assertEqual(TP.fnv1a(''), 0x811C9DC5)
        self.assertEqual(TP.fnv1a('a'), 0xE40C292C)
        self.assertEqual(TP.fnv1a('Fargoth'), TP.fnv1a('fargoth'))

    def test_a_shared_hash_of_two_heads_is_refused(self):
        with unittest.mock.patch.object(TP, 'fnv1a', lambda ident: 7):
            with self.assertRaisesRegex(ValueError, 'share the talk hash'):
                TP.pack({'a': 0, 'b': 1}, [rows(1), rows(1)], 4)

    def test_offsets_saturate_and_positions_are_checked(self):
        _, heads, _ = TP.read(TP.pack({'x': 0}, [[(0.0, 0.0, 0.0, np.full((3, 3), 9.0))]], 4))
        self.assertTrue(np.all(heads[0][1] > 3.9))
        with self.assertRaisesRegex(ValueError, 'outside the talk pack range'):
            TP.pack({'x': 0}, [[(200.0, 0.0, 0.0, np.zeros((3, 3)))]], 4)

    def test_head_bone_is_the_tables(self):
        import skeletal_actor
        self.assertEqual(TP.head_bone_index(), list(skeletal_actor.STICK_BONES).index('bip01 head'))
        self.assertEqual(TP.head_bone_index(), 4)

    def test_the_part_in_the_heads_place(self):
        # a helmet in the head's place (mwad.npc.outfit): that part is the one asked, and having no Talk morph it gives
        # the NPC no entry (the original draws no head under it)
        app = {'parts': [{'filter': 'Hair', 'mesh': 'h.nif'}, {'filter': 'Head', 'mesh': 'a/helm.nif'}]}
        self.assertEqual(TP.head_part(app)['mesh'], 'a/helm.nif')
        self.assertIsNone(TP.head_part({'parts': [{'filter': 'Hair', 'mesh': 'h.nif'}]}))


@env_guard.isolated  # the builder's plan may export AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class WiringTests(unittest.TestCase):
    def test_stage_reads_the_game_data_only_and_the_image_copies_it(self):
        build = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('("talk", tool("talk_pack.py", "--data-files", args.data_files, "--out", run / "talk", '
                      '"--jobs", jobs)),', build)
        self.assertIn('"--talk", run / "talk",', build)
        aga = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn('stage_talk_pack(args, boot/\'id1\')', aga)

    def test_plan_places_it_before_the_image(self):
        # the default plan (as tests/test_build_defaults.py makes it): the talk stage waits for nothing and the image
        # for it
        import build
        import build_parallel
        args = build.parser().parse_args([])
        args.data_files = Path('/owned/Data Files')
        args.sdk = Path('/sdk')
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        with unittest.mock.patch('build_jobs.auto_jobs', return_value=4):
            steps = build.commands(args, tools, Path('/private/run'))
        names = [name for name, _ in steps]
        self.assertIn('talk', names)
        self.assertLess(names.index('talk'), names.index('image'))
        deps = build_parallel.stage_dependencies(steps)
        self.assertEqual(deps['talk'], ())
        self.assertIn('talk', deps['image'])

    def test_engine_reads_the_same_format(self):
        c = (ROOT / 'engine/aga/src/aw_talkpack.c').read_text(encoding='utf-8')
        self.assertIn('"AWTP"', c)
        self.assertIn('#define AW_TALK_HEADER\t%d' % TP.HEADER, c)
        self.assertIn('#define AW_TALK_VERT\t%d' % TP.VERTEX_BYTES, c)
        self.assertIn('#define AW_TALK_REGION\t%d' % TP.MAX_ROWS, c)
        self.assertIn('/256.0f', c.replace(' ', ''))
        self.assertIn('sum*32.0f', c.replace(' ', ''))
        self.assertEqual(TP.POSITION_UNITS, 256.0)
        self.assertEqual(TP.OFFSET_UNITS, 32.0)


if __name__ == '__main__':
    unittest.main()
