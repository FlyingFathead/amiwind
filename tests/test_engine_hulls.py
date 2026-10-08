# SPDX-License-Identifier: GPL-3.0-only
"""Collision hull limits apply to the hulls the engine traces, and only those.

BUILD-SEYDA-HULL2-32: the scaled standing-collision compile of the Seyda Neen
town stopped on qbsp's BSP29 clipnode limit in hull 2, a hull the engine
never traces. The intermediate is now BSP2 and only its hull 1 is grafted;
the engine's limits are checked on the grafted BSP29 result. The contract
tests below fail if the engine or QuakeC starts selecting hull 2.
"""
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from player_hull import (ENGINE_CLIPNODE_LIMIT, ENGINE_HULLS, INTERMEDIATE_FORMAT, MAXS, MINS,  # noqa: E402
                         check_engine_hulls, clip_child, graft_hull, intermediate_hull, lumps,
                         pack_lumps, rebuild_world_hull, scaled_map)

ENGINE = ROOT / 'engine/aga/src'
WORLDSPAWN = b'{\n"classname" "worldspawn"\n}\n\0'


def engine_hull(width):
    """SV_HullForEntity (world.c): the hull selected for a moving box's x size."""
    return 0 if width < 3 else 1 if width <= 32 else 2


def model(headnodes):
    return struct.pack('<9f7i', *[0.0] * 9, *headnodes, 0, 0, 0)


def target(clipnodes=0, headnodes=(-1, -1, -1, -1)):
    data = [bytearray() for _ in range(15)]
    data[0] = bytearray(WORLDSPAWN)
    data[1] = bytearray(struct.pack('<4fi', 0, 0, 1, 0, 2))
    data[9] = bytearray(struct.pack('<ihh', 0, -1, -2) * clipnodes)
    data[14] = bytearray(model(headnodes))
    return pack_lumps(data)


def chain(start, count, fmt):
    """count clipnodes, each with a solid side and the next node (or empty) behind it."""
    return b''.join(struct.pack(fmt, 0, -2, start + i + 1 if i + 1 < count else -1) for i in range(count))


def intermediate(hull1, hull2, bsp2=True):
    fmt = '<iii' if bsp2 else '<ihh'
    parts = [b''] * 15
    parts[0] = WORLDSPAWN
    parts[1] = struct.pack('<4fi', 0, 0, 1, 8, 2)
    parts[9] = chain(0, hull1, fmt) + chain(hull1, hull2, fmt)
    parts[14] = model((-1, 0, hull1, 0))
    if not bsp2:
        return pack_lumps([bytearray(p) for p in parts])
    head = bytearray(b'BSP2' + bytes(120))
    body = bytearray()
    for i, raw in enumerate(parts):
        body += bytes(-len(body) % 4)
        struct.pack_into('<ii', head, 4 + i * 8, 124 + len(body), len(raw))
        body += raw
    return bytes(head + body)


def hull1_nodes(raw):
    data = lumps(raw)
    clips = [(p, clip_child(a), clip_child(b)) for p, a, b in struct.iter_unpack('<ihh', data[9])]
    root = struct.unpack_from('<i', data[14], 40)[0]
    seen = []
    while root >= 0:
        seen.append(root)
        root = clips[root][2]
    return seen, data


class EngineHullContract(unittest.TestCase):
    def test_engine_selects_hulls_by_box_width(self):
        text = (ENGINE / 'world.c').read_text(encoding='utf-8')
        self.assertRegex(text, r'if \(size\[0\] < 3\)\s*hull = &model->hulls\[0\];\s*'
                               r'else if \(size\[0\] <= 32\)\s*hull = &model->hulls\[1\];\s*'
                               r'else\s*hull = &model->hulls\[2\];')
        self.assertEqual(ENGINE_HULLS, (0, 1))

    def test_quakec_boxes_select_only_engine_hulls(self):
        text = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        boxes = re.findall(r"setsize\(\s*\w+\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*\)", text)
        self.assertGreaterEqual(len(boxes), 3)
        for low, high in boxes:
            low, high = [list(map(float, v.split())) for v in (low, high)]
            with self.subTest(box=(low, high)):
                self.assertIn(engine_hull(high[0] - low[0]), ENGINE_HULLS)
                self.assertIn(engine_hull(high[1] - low[1]), ENGINE_HULLS)

    def test_engine_traces_only_points_and_entity_boxes(self):
        """Engine C passes vec3_origin, an entity's own box, or its caller's box."""
        # clip->mins/maxs copy SV_Move's box; clip->mins2/maxs2 are that box
        # or, for missiles against monsters, the fixed +-15 box checked below.
        box = r'(vec3_origin|\w+->v\.(mins|maxs)|mins|maxs|clip->(mins|maxs)2?)'
        world = (ENGINE / 'world.c').read_text(encoding='utf-8')
        missile = re.findall(r'clip\.(mins2|maxs2)\[i\] = (-?\d+);', world)
        self.assertEqual(sorted(missile), [('maxs2', '15'), ('mins2', '-15')])
        self.assertIn(engine_hull(30), ENGINE_HULLS)
        calls = 0
        for path in sorted(ENGINE.glob('*.c')):
            text = path.read_text(encoding='utf-8', errors='replace')
            for name, first in (('SV_Move', 1), ('SV_ClipMoveToEntity', 2)):
                for match in re.finditer(name + r'\s*\(([^;{]*)\)\s*;', text):
                    args = [a.strip() for a in match.group(1).split(',')]
                    if any(re.search(r'\b(vec3_t|edict_t)\b', a) for a in args):
                        continue  # a prototype, not a call
                    calls += 1
                    with self.subTest(file=path.name, call=match.group(0)[:80]):
                        self.assertRegex(args[first], '^' + box + '$')
                        self.assertRegex(args[first + 1], '^' + box + '$')
        self.assertGreater(calls, 40)

    def test_entity_boxes_are_set_only_by_setsize_and_setmodel(self):
        write = re.compile(r'v\.(mins|maxs)(\[[^\]]*\])?\s*=(?!=)|VectorCopy\s*\([^;]*,\s*[^;,]*v\.(mins|maxs)\s*\)')
        writers = sorted({path.name for path in ENGINE.glob('*.c')
                          if write.search(path.read_text(encoding='utf-8', errors='replace'))})
        # pr_cmds.c SetMinMaxSize (setsize/setmodel); sv_phys.c only shrinks pushed boxes.
        self.assertEqual(writers, ['pr_cmds.c', 'sv_phys.c'])

    def test_hull1_box_is_the_standing_humanoid(self):
        text = (ENGINE / 'model.c').read_text(encoding='utf-8')
        block = text[text.index('hull = &loadmodel->hulls[1];'):text.index('hull = &loadmodel->hulls[2];')]
        values = {f'{k}[{i}]': float(v) for k, i, v in
                  re.findall(r'hull->(clip_mins|clip_maxs)\[(\d)\] = ([-\d.]+)f?;', block)}
        self.assertEqual([values[f'clip_mins[{i}]'] for i in range(3)], list(MINS))
        self.assertEqual([values[f'clip_maxs[{i}]'] for i in range(3)], list(MAXS))

    def test_engine_clipnode_limit(self):
        text = (ENGINE / 'model.c').read_text(encoding='utf-8')
        self.assertIn('count>%d' % ENGINE_CLIPNODE_LIMIT, text.replace(' ', ''))
        self.assertIn('child < -15 ? (unsigned short)child : child', (ENGINE / 'world.c').read_text(encoding='utf-8'))


class GraftLimits(unittest.TestCase):
    def test_unused_hull2_over_the_bsp29_limit_does_not_stop_the_graft(self):
        collision = intermediate(3, 70000)
        self.assertEqual(intermediate_hull(collision)[2], 0)
        raw = graft_hull(target(), collision)
        nodes, _ = hull1_nodes(raw)
        self.assertEqual(len(nodes), 3)
        report = check_engine_hulls(raw)
        self.assertEqual(report['hulls']['1'], {'reachable': 3, 'engine_traced': True})
        self.assertFalse(report['hulls']['2']['engine_traced'])

    def test_bsp29_intermediate_matches_bsp2(self):
        self.assertEqual(graft_hull(target(4), intermediate(5, 2, bsp2=False)),
                         graft_hull(target(4), intermediate(5, 2)))

    def test_used_hull_over_the_engine_limit_fails(self):
        with self.assertRaisesRegex(ValueError, 'engine clipnode limit'):
            graft_hull(target(ENGINE_CLIPNODE_LIMIT - 10), intermediate(11, 1))
        graft_hull(target(ENGINE_CLIPNODE_LIMIT - 10), intermediate(10, 1))

    def test_hull1_indices_past_32767_use_the_engine_encoding(self):
        raw = graft_hull(target(32760), intermediate(20, 70000))
        nodes, data = hull1_nodes(raw)
        self.assertEqual(nodes, list(range(32760, 32780)))
        stored = struct.unpack_from('<HH', data[9], 32770 * 8 + 4)
        self.assertEqual(stored, (65534, 32771))
        self.assertEqual(check_engine_hulls(raw)['clipnodes'], 32780)

    def test_check_limits_used_hulls_and_ignores_unused(self):
        with self.assertRaisesRegex(ValueError, 'Hull 1 child'):
            check_engine_hulls(target(2, (-1, 7, -1, -1)))
        report = check_engine_hulls(target(2, (-1, 0, 9, 9)))
        self.assertEqual(report['hulls']['2']['reachable'], 0)
        data = lumps(target(1))
        data[9] = bytearray(struct.pack('<ihh', 0, -1, -2) * (ENGINE_CLIPNODE_LIMIT + 1))
        with self.assertRaisesRegex(ValueError, 'Clipnode count exceeds the engine limit'):
            check_engine_hulls(pack_lumps(data))


QBSP = os.environ.get('AMIWIND_TEST_QBSP')
ROOM = '''{
"classname" "worldspawn"
%s}
{
"classname" "info_player_start"
"origin" "0 0 24"
}
'''


@unittest.skipIf(os.name == 'nt', 'compiler checks run in Linux Docker')
@unittest.skipUnless(QBSP, 'requires external qbsp')
class RealCompiler(unittest.TestCase):
    def test_bsp2_intermediate_hull_equals_the_bsp29_one(self):
        import subprocess
        walls = [((-256, -256, -16), (256, 256, 0)), ((-256, -256, 256), (256, 256, 272)),
                 ((-272, -256, 0), (-256, 256, 256)), ((256, -256, 0), (272, 256, 256)),
                 ((-256, -272, 0), (256, -256, 256)), ((-256, 256, 0), (256, 272, 256)),
                 ((-40, -24, 0), (8, 40, 96)), ((96, 64, 0), (160, 72, 40))]
        from prepare_quake import box
        text = ROOM % ''.join(box(*w, 'stone') + '\n' for w in walls)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            outputs = {}
            for name, options in (('bsp29', []), ('bsp2', [INTERMEDIATE_FORMAT])):
                (tmp / name).mkdir()
                (tmp / name / 'standing.map').write_text(scaled_map(text), newline='\n')
                subprocess.run([QBSP, '-nopercent', *options, 'standing.map'], cwd=tmp / name, check=True,
                               stdout=subprocess.DEVNULL)
                outputs[name] = (tmp / name / 'standing.bsp').read_bytes()
            self.assertEqual(outputs['bsp2'][:4], b'BSP2')
            base = target(3)
            self.assertEqual(graft_hull(base, outputs['bsp29']), graft_hull(base, outputs['bsp2']))
            (tmp / 'room').mkdir()
            (tmp / 'room' / 'room.map').write_text(text, newline='\n')
            subprocess.run([QBSP, '-nopercent', 'room.map'], cwd=tmp / 'room', check=True, stdout=subprocess.DEVNULL)
            bsp = tmp / 'room' / 'room.bsp'
            before = bsp.read_bytes()
            rebuild_world_hull(bsp, tmp / 'room' / 'room.map', QBSP)
            self.assertEqual(bsp.read_bytes(), graft_hull(before, outputs['bsp2']))
            self.assertEqual((tmp / 'room' / 'standing-collision.bsp').read_bytes()[:4], b'BSP2')
            self.assertTrue(check_engine_hulls(bsp.read_bytes())['hulls']['1']['reachable'] > 0)


if __name__ == '__main__':
    unittest.main()
