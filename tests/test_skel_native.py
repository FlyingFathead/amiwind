# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared animation tables, the engine side (engine/aga/src/aw_skel.c): the C code reads the table the builder
writes (tools/skeletal_actor.py write_table) and poses bone-space points as the builder poses them, on a synthetic
three-bone chain, between frames too (normalised lerp of the quaternions). No game data."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))) / 'src'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import skeletal_actor as S  # noqa: E402
from test_skeletal_actor import Chain  # noqa: E402


def column(m):
    """The builder's 4 x 4 row-vector matrix as the engine's 3 x 4 column form."""
    out = np.zeros((3, 4))
    out[:, :3] = m[:3, :3].T
    out[:, 3] = m[3, :3]
    return out


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class SkelNativeTests(unittest.TestCase):
    def test_the_engine_poses_the_builders_table(self):
        chain = Chain()
        bones = S.bone_order(Chain.parents, ['fore'])
        parents = [-1 if Chain.parents[b] is None else bones.index(Chain.parents[b]) for b in bones]
        times = S.table_frames(0.0, 2.0, rate=10.0)
        rot, pos = S.sample_table(chain, bones, times)
        q, p, scale = S.quantise_table(rot, pos)
        self.assertEqual(len(times), 21)
        keys = [('start', 0, 0), ('stop', 0, 10), ('soundgen: left', S.NO_GROUP, 14), ('start', 1, 11),
                ('stop', 1, 20)]
        table = S.write_table(parents, {'idle': (0, 10), 'walkforward': (11, 20)}, q, p, scale, keys=keys)
        self.assertEqual(S.read_table(table)['keys'], keys)
        rot_q, pos_q = S.dequantise_table(q, p, scale)
        rng = np.random.default_rng(7)
        rows, expect = [], []
        for frame in (0.0, 4.0, 4.5, 12.25, 30.0, 45.0):
            f0 = min(int(frame), len(times) - 1)
            f1 = min(f0 + 1, len(times) - 1)
            u = min(frame, len(times) - 1) - f0
            locals_ = []
            for b in range(len(bones)):
                qq = S.nlerp(rot_q[f0, b], rot_q[f1, b], u)
                locals_.append(S.local_matrix(qq, pos_q[f0, b] * (1 - u) + pos_q[f1, b] * u))
            world = S.pose_matrices(parents, locals_)
            for b in range(len(bones)):
                point = rng.uniform(-5, 5, 3)
                rows.append('%.9g %d %.9g %.9g %.9g' % (frame, b, *point))
                expect.append((np.append(point, 1.0) @ world[b])[:3])
                np.testing.assert_allclose(column(world[b])[:, :3] @ point + column(world[b])[:, 3], expect[-1])
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            (scratch / 'table.bin').write_bytes(table)
            (scratch / 'points.txt').write_text('\n'.join(rows) + '\n')
            exe = scratch / 'skel-check'
            compiled = subprocess.run(['cc', '-std=gnu89', '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                       '-I' + str(SOURCE), str(ROOT / 'tests/aga_skel_test.c'),
                                       str(SOURCE / 'aw_skel.c'), '-lm', '-o', str(exe)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(exe), str(scratch / 'table.bin'), str(scratch / 'points.txt')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], 'table bones 3 frames 21 groups 2')
        self.assertEqual(lines[1], 'group walkforward 11 20')
        self.assertEqual(lines[2], 'key walkforward stop 20 idle stop 10 none -1 keys 5')
        lines = lines[:2] + lines[3:]
        self.assertEqual(lines[-1], 'skel ok')
        got = np.array([[float(v) for v in line.split()] for line in lines[2:-1]])
        np.testing.assert_allclose(got, np.array(expect), atol=1e-3)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class SkelVertsNativeTests(unittest.TestCase):
    def test_the_engine_poses_a_skinned_shape_into_alias_bytes(self):
        """A shape with one-bone and joint vertices: the engine's byte frame (AW_SkelPoseVerts) equals the builder's
        skinning of the same table frame, quantised the same way, within one byte step."""
        chain = Chain()
        bones = S.bone_order(Chain.parents, ['fore'])
        parents = [-1 if Chain.parents[b] is None else bones.index(Chain.parents[b]) for b in bones]
        times = S.table_frames(0.0, 2.0, rate=10.0)
        rot, pos = S.sample_table(chain, bones, times)
        q, p, scale = S.quantise_table(rot, pos)
        table = S.write_table(parents, {'idle': (0, 20)}, q, p, scale)
        rot_q, pos_q = S.dequantise_table(q, p, scale)
        # bind pose = frame 0 of the table
        bind = S.pose_matrices(parents, [S.local_matrix(rot_q[0, b], pos_q[0, b]) for b in range(len(bones))])
        inverse = {i: np.linalg.inv(bind[i]) for i in range(len(bones))}
        vertices = np.array([[1.0, 2.0, 25.0], [1.5, 2.0, 28.0], [1.0, 2.5, 15.0], [1.0, 2.0, 20.0], [0.5, 1.0, 3.0]])
        weights = {0: ([4], [1.0]), 1: ([2, 3], [1.0, 0.4]), 2: ([0, 1, 3], [1.0, 1.0, 0.6])}
        bone, second, weight, rest, rest2 = S.bind_skinned(vertices, weights, inverse)
        blob, rest_scale = S.write_verts(bone, second, weight, rest, rest2)
        self.assertEqual(len(blob), len(vertices) * S.VERT_BYTES)
        origin, step = np.array([-40.0, -40.0, -10.0]), np.array([0.35, 0.35, 0.3])
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            (scratch / 'table.bin').write_bytes(table)
            (scratch / 'verts.bin').write_bytes(blob)
            exe = scratch / 'skel-check'
            compiled = subprocess.run(['cc', '-std=gnu89', '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                       '-I' + str(SOURCE), str(ROOT / 'tests/aga_skel_test.c'),
                                       str(SOURCE / 'aw_skel.c'), '-lm', '-o', str(exe)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            for frame in (0, 9, 20):
                result = subprocess.run([str(exe), 'verts', str(scratch / 'table.bin'), str(scratch / 'verts.bin'),
                                         str(len(vertices)), str(frame), '%.9g' % rest_scale,
                                         *('%.9g' % v for v in origin), *('%.9g' % v for v in step)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                got = np.array([[int(v) for v in line.split()] for line in result.stdout.splitlines()])
                world = S.pose_matrices(parents, [S.local_matrix(rot_q[frame, b], pos_q[frame, b])
                                                  for b in range(len(bones))])
                posed = S.skin(rest, bone, second, weight, world, rest2)
                want = np.clip(np.round((posed - origin) / step), 0, 255)
                self.assertLessEqual(int(np.max(np.abs(got - want))), 1, (frame, got, want))
            # at the bind frame the shape comes back where it was bound
            np.testing.assert_allclose(S.skin(rest, bone, second, weight, bind, rest2), vertices, atol=1e-9)
            # the block the builder appends to the model, as the engine parses it (bones 0-2: fits 3 bones, not 2)
            block = S.write_block('progs/humanoid.awsk', blob, rest_scale, len(vertices), 31,
                                  (-1.5, 2.25, -8.0), (0.5, 0.25, 0.125))
            self.assertEqual(len(block), S.BLOCK_HEAD + len(blob))
            (scratch / 'block.bin').write_bytes(block)
            result = subprocess.run([str(exe), 'block', str(scratch / 'block.bin'), str(len(vertices))],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.split()[:5], ['block', 'progs/humanoid.awsk', '%.6g' % np.float32(rest_scale),
                                                         str(len(vertices)), '31'])
            self.assertEqual(result.stdout.split()[5:], ['-1.5', '2.25', '-8', '0.5', '0.25', '0.125'])


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class SkelBoneTagNativeTests(unittest.TestCase):
    def test_the_engine_tags_an_item_as_the_tag_writer_does(self):
        """A carried item's tag row from a posed bone (SKEL-ITEM-TAGS-52): AW_SkelBoneTag equals tools/npc_items.py
        bone_tags (position x the actor scale, quake_angles of the bone's rotation) for turned bones."""
        sys.path.insert(0, str(ROOT / 'src'))
        import npc_items
        from test_skeletal_actor import axis_quat
        scale = np.array([1.1, 1.1, 0.95]) * .25
        with tempfile.TemporaryDirectory() as scratch:
            exe = Path(scratch) / 'skel-check'
            compiled = subprocess.run(['cc', '-std=gnu89', '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                       '-I' + str(SOURCE), str(ROOT / 'tests/aga_skel_test.c'),
                                       str(SOURCE / 'aw_skel.c'), '-lm', '-o', str(exe)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            for axis, deg, pos in (((0, 0, 1), 30, (3, 4, 50)), ((1, 2, 0.5), 75, (-8, 2, 61)),
                                   ((0, 1, 0), -40, (0, 0, 0)), ((1, -1, 1), 170, (12, -3, 40))):
                m = S.local_matrix(axis_quat(axis, deg), pos)        # row-vector form, as the tag writer's pose
                col = np.zeros((3, 4))
                col[:, :3] = m[:3, :3].T
                col[:, 3] = m[3, :3]
                result = subprocess.run([str(exe), 'tag', *('%.9g' % v for v in col.ravel()),
                                         *('%.9g' % v for v in scale)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                got = np.array([float(v) for v in result.stdout.split()])
                want = np.array([*(m[3, :3] * scale), *npc_items.quake_angles(m[:3, :3])])
                np.testing.assert_allclose(got, want, atol=2e-3)


class SkelSourceTests(unittest.TestCase):
    def test_the_table_layout_matches_the_builder(self):
        header = (SOURCE / 'aw_skel.h').read_text()
        self.assertIn('#define AW_SKEL_NAME\t\t%d' % S.TABLE_NAME, header)
        self.assertIn('#define AW_SKEL_VERSION\t\t%d' % S.TABLE_VERSION, header)
        self.assertIn('#define AW_SKEL_BLOCK_VERSION\t%d' % S.BLOCK_VERSION, header)
        self.assertIn('#define AW_SKEL_KEY_TEXT\t%d' % S.KEY_TEXT, header)
        for name, value in (('STILL', S.STILL), ('TURNS', S.TURNS), ('MOVES', S.MOVES)):
            self.assertIn('#define AW_SKEL_%s\t\t%d' % (name, value), header)
        self.assertIn('#define AW_SKEL_MAGIC\t\t"%s"' % S.TABLE_MAGIC.decode(), header)

    def test_the_posing_is_cut_to_what_changes(self):
        # SKEL-RUNTIME-COST-52: a whole frame takes its one key without blend, square root or division; the bones
        # that never move are made once per table (keyed by the keys themselves, not the address); the vertex loop
        # has its transforms written out on direct i16 reads (the native tests above check the result)
        skel = (SOURCE / 'aw_skel.c').read_text()
        self.assertIn('if (u == 0)\n\t{', skel)
        self.assertIn('if (!still_same (t))', skel)
        self.assertIn('!memcmp (still_keys, t->base, (size_t)t->bones * AW_SKEL_BASE_BYTES)', skel)
        self.assertIn('memcpy (local, still_local[i], sizeof(local));', skel)
        self.assertNotIn('AW_SkelTransform (folded', skel)
        self.assertIn('#define SKEL_I16(p)\t(*(const short *)(const void *)(p))', skel)
        # 32 posed frames where memory allows (an idle loop of 8 table frames for a few actors in view), else 8
        alias = (SOURCE / 'r_alias.c').read_text()
        self.assertIn('#define AW_POSE_CACHE_LARGE\t32', alias)
        self.assertIn('aw_posed_t *more = (aw_posed_t *)AW_TryMalloc (AW_POSE_CACHE_LARGE * sizeof(aw_posed_t));', alias)
        self.assertIn('for (i=0 ; i<aw_pose_slots ; i++)', alias)
        # culled by the box of the pose it stands in once posed, not by the every-pose rest box (an extra model drawn)
        # (its key: the frame, or the torch pose's, SKEL-ITEM-TAGS-52; the storm pose's, ACTOR-STORM-POSE-51)
        self.assertIn('if (pahdr->aw_skel && AW_PoseBox (pmodel, pahdr, AW_SkelEntityKey (pmodel, pahdr, '
                      'currententity->frame,', alias)
        self.assertIn('memcpy (box, aw_posed[i].box, 6);', alias)

    def test_a_room_short_of_memory_gets_the_tables_and_posed_frames_back_first(self):
        # SKEL-ROOM-AFTER-TOWN-52: at 32 MB Akulakhan's Chamber failed after Balmora (2 MiB free for its models, 4 MiB
        # when loaded first): before Chim_RoomGrow measures the free Fast RAM the engine flushes its skeletal models
        # and gives back the tables and the large pose cache, all made again on demand
        world = (SOURCE / 'chim' / 'chim_world.c').read_text()
        grow = world[world.index('int Chim_RoomGrow (const char *name)'):]
        self.assertLess(grow.index('unsigned long given = AW_FastReleaseAll ("a room\'s models");'),
                        grow.index('ChimZone_RoomStep (chim_fast_avail (1))'))
        release = (SOURCE / 'aw_skel_release.c').read_text()
        self.assertLess(release.index('Cache_Free (&m->cache);'), release.index('AW_SkelTablesRelease ()'))
        self.assertIn('AW_FastReleaseRegister ("animation tables and posed frames", AW_SkelReleaseAll);', release)
        load = (SOURCE / 'aw_skel_load.c').read_text()
        self.assertIn('memset (tables, 0, sizeof(tables));', load)
        alias = (SOURCE / 'r_alias.c').read_text()
        self.assertIn('memset (aw_posed_kept, 0, sizeof(aw_posed_kept));', alias)
        self.assertIn('AW_SkelReleaseInit();', (SOURCE / 'aw_animkit.c').read_text())

    def test_a_table_is_refused_when_memory_cannot_hold_it(self):
        # SKEL-16MB-TRAP-52: the toolchain's malloc (libc malloc.o MemMap::alloc) stores through the NULL AllocMem
        # gives it and stops on TRAP #7 (Software Failure #80000027) instead of returning NULL; at 16 MB of Fast RAM
        # the female table's malloc did. The loader asks only when the largest free block holds the table.
        load = (SOURCE / 'aw_skel_load.c').read_text()
        self.assertIn('long largest = (long)AvailMem (MEMF_LARGEST);', load)
        self.assertIn('if (largest < size + 4 + AW_SKEL_ALLOC_SPARE)', load)
        self.assertIn('tables[i].data = table_alloc (size);', load)
        self.assertNotIn('= malloc (size);\n\tif (!tables[i].data', load)

    def test_a_table_holds_its_index_and_reads_only_the_frames_posed(self):
        # WALK-CYCLES-57: the common table is 602 KB, of which 39 KB is its index; a town's people play idles, turns,
        # walk and run (about 118 KB of frames). Paged by default, read in chunks when first posed and kept with the
        # table; the previous method (the whole file in one block) stays selectable (dbg animkit tables whole).
        load = (SOURCE / 'aw_skel_load.c').read_text()
        self.assertIn('int aw_skel_paged = 1;', load)
        self.assertIn('if (aw_skel_paged)', load)
        self.assertIn('tables[i].table.row_of = paged_row;', load)
        self.assertIn('pages_free ((aw_skel_pages_t *)tables[i].table.pages);', load)
        skel = (SOURCE / 'aw_skel.c').read_text()
        self.assertIn('*a = t->row_of (t, f0);', skel)
        kit = (SOURCE / 'aw_animkit.c').read_text()
        self.assertIn('aw_skel_paged=strcmp(argv[2],"whole")!=0;', kit)

    def test_a_layout_of_a_model_not_loaded_yet_is_checked_when_it_loads(self):
        # ANIMKIT-COVERAGE-35 / WALK-CYCLES-57: six actor models of the v0.0.57-dev2 sweep were known by name only at
        # spawn (numframes 0), so every group failed the frame check and the actor kept its idle; the layout is now
        # parsed against the table's frame limit and checked against the frames when the model loads (AW_AnimOf)
        anim = (SOURCE / 'aw_anim.c').read_text()
        self.assertIn('prep_layout(m,m->name,m->numframes>0?m->numframes:AW_ANIM_UNLOADED_FRAMES);', anim)
        self.assertIn('if(table[g].model==m && m->numframes>0 && table[g].needed>m->numframes)', anim)
        # the generic alias loader keeps a skeletal model's block and links its table as the stream does (Seyda's
        # dreamers were read by it, stood in their rest frame and had their layouts refused against 1 frame)
        model = (SOURCE / 'model.c').read_text()
        self.assertIn('if(frames==1 && left==(size_t)AW_SKEL_BLOCK_HEAD+(size_t)verts*AW_SKEL_VERT_BYTES', model)
        self.assertIn('if (aw_alias_skel_link (pheader, b, rest, pmodel->numverts, &frames))', model)
        self.assertIn('h->aw_skel_table = table;', (SOURCE / 'aw_skel_load.c').read_text())
        self.assertIn('aw_alias_skel_link = AW_SkelLinkAlias;', (SOURCE / 'aw_skel_release.c').read_text())

    def test_the_save_buffers_ask_only_for_memory_there_is(self):
        # SDK-MALLOC-TRAPS-52: with the table refused, the 16 MB stage stopped again in AW_SaveWrite's 256 KB buffer
        # (the arrival autosave): the save buffers go through AW_TryMalloc, which asks exec's largest block first
        header = (SOURCE / 'aw_tryalloc.h').read_text()
        body = (SOURCE / 'aw_tryalloc.c').read_text()      # the rule: tests/test_engine_allocations.py
        self.assertIn('return fits (size) ? malloc (size) : NULL;', body)
        self.assertIn('#define AW_TryMalloc(size)\tmalloc (size)', header)
        save = (SOURCE / 'aw_save.c').read_text()
        self.assertIn('#include "aw_tryalloc.h"', save)
        self.assertNotIn('malloc(AW_SAVE_BYTES)', save.replace('AW_TryMalloc(AW_SAVE_BYTES)', ''))
        self.assertEqual(save.count('AW_TryMalloc(AW_SAVE_BYTES)'), 3)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class SkelTorchLayerNativeTests(unittest.TestCase):
    """SKEL-ITEM-TAGS-52: a guard holding his torch has his left arm (Bip01 L Clavicle down) on the table's torch
    group, as the baked guards (prepare_guard_torches.TorchLayer) and the original; the rest of him on his own frame."""
    # root, neck, left clavicle, upper arm, forearm, hand, shield bone, the right arm likewise, head
    PARENTS = [-1, 0, 1, 2, 3, 4, 5, 1, 7, 8, 9, 10, 1]

    def run_layer(self, table, *args):
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            (scratch / 'table.bin').write_bytes(table)
            exe = scratch / 'skel-layer'
            compiled = subprocess.run(['cc', '-std=gnu89', '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                       '-I' + str(SOURCE), str(ROOT / 'tests/aga_skel_test.c'),
                                       str(SOURCE / 'aw_skel.c'), '-lm', '-o', str(exe)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(exe), 'layers' if len(args) == 7 else 'layer', str(scratch / 'table.bin'),
                                     *map(str, args)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        return int(lines[0].split()[1]), np.array([[float(v) for v in l.split()] for l in lines[1:]])

    def test_the_left_arm_takes_the_layer_frame(self):
        rng = np.random.default_rng(52)
        frames, bones = 12, len(self.PARENTS)
        rot = rng.normal(size=(frames, bones, 4))
        rot /= np.linalg.norm(rot, axis=2, keepdims=True)
        rot[rot[:, :, 0] < 0] *= -1
        pos = rng.uniform(-20, 20, size=(frames, bones, 3))
        q, p, scale = S.quantise_table(rot, pos)
        table = S.write_table(self.PARENTS, {'idle': (0, 5), 'torch': (6, 11)}, q, p, scale)
        rq, pq = S.dequantise_table(q, p, scale)

        def world(frame, layer=None, root=None):
            under = set()
            for b, parent in enumerate(self.PARENTS):
                if b == root or parent in under:
                    under.add(b)
            locals_ = [S.local_matrix(rq[layer if b in under else frame, b], pq[layer if b in under else frame, b])
                       for b in range(bones)]
            return np.array([m[3, :3] for m in S.pose_matrices(self.PARENTS, locals_)])

        root, got = self.run_layer(table, 2, 8, 2, 6, 11)
        self.assertEqual(root, 2)                       # the shield bone's fourth ancestor, beside the other clavicle
        np.testing.assert_allclose(got, world(2, 8, 2), atol=2e-3)
        self.assertGreater(np.abs(got[6] - world(2)[6]).max(), 0.5)       # the shield bone moved with the arm
        np.testing.assert_allclose(got[[0, 1, 7, 8, 9, 10, 11, 12]], world(2)[[0, 1, 7, 8, 9, 10, 11, 12]], atol=2e-3)
        root, got = self.run_layer(table, 2, 8, -1, 6, 11)
        np.testing.assert_allclose(got, world(2), atol=2e-3)              # no layer: AW_SkelPose as before
        # not shaped like two arms of one spine: no root, so no layer
        self.assertEqual(self.run_layer(table, 0, 0, -1, 5, 11)[0], -1)
        self.assertEqual(self.run_layer(table, 0, 0, -1, 6, 6)[0], -1)
        self.assertEqual(self.run_layer(table, 0, 0, -1, 6, 12)[0], -1)
        # ACTOR-STORM-POSE-51: two layers at once, the torch on the left arm and the storm on the right; the right arm's
        # root is the weapon bone's fourth ancestor (7), the rest of the body keeps the base frame
        root, got = self.run_layer(table, 2, 8, 2, 4, 7, 6, 11)
        self.assertEqual(root, 7)

        def layered(frame, roots):
            """world origins with each root's subtree on its frame (the nearest root above a bone wins)"""
            under = {}
            for b, parent in enumerate(self.PARENTS):
                if b in roots:
                    under[b] = roots[b]
                elif parent in under:
                    under[b] = under[parent]
            locals_ = [S.local_matrix(rq[under.get(b, frame), b], pq[under.get(b, frame), b]) for b in range(bones)]
            return np.array([m[3, :3] for m in S.pose_matrices(self.PARENTS, locals_)])

        np.testing.assert_allclose(got, layered(2, {2: 8, 7: 4}), atol=2e-3)
        np.testing.assert_allclose(got[[0, 1, 12]], world(2)[[0, 1, 12]], atol=2e-3)
        self.assertGreater(np.abs(got[11] - world(2, 8, 2)[11]).max(), 0.5)     # the weapon hand moved with the arm
        # the single-layer wrapper poses as before
        np.testing.assert_allclose(self.run_layer(table, 2, 8, 2, 6, 11)[1], world(2, 8, 2), atol=2e-3)
        # nested roots: the nearer root wins below it (a layer on the spine, the left arm back on the base frame)
        root, got = self.run_layer(table, 2, 4, 1, 2, 2, 6, 11)
        np.testing.assert_allclose(got, layered(2, {1: 4, 2: 2}), atol=2e-3)

    def test_the_renderer_the_cull_box_and_the_items_pose_alike(self):
        alias = (SOURCE / 'r_alias.c').read_text()
        self.assertIn('AW_SkelPoseLayers (table, (float)frame, AW_SKEL_LAYERS, layers, roots, world);', alias)
        self.assertIn('p->frame == key)', alias)
        self.assertIn('AW_PoseBox (pmodel, pahdr, AW_SkelEntityKey (pmodel, pahdr, currententity->frame,', alias)
        # ACTOR-STORM-POSE-51: the storm layer is part of the pose key and of the cull box's pose
        self.assertIn('key += AW_STORM_KEY;', alias)
        self.assertIn('currententity->angles[YAW], NULL, NULL), box))', alias)
        self.assertIn('R_AliasStormLayer=AW_ItemsStormLayer;', (SOURCE / 'aw_items.c').read_text())
        self.assertIn('AW_SkelGroup(tab,"idlestorm")', (SOURCE / 'aw_items.c').read_text())
        items = (SOURCE / 'aw_items.c').read_text()
        self.assertIn('AW_SkelPoseLayer(tab,(float)f,layer,layered?root:-1,world);', items)
        self.assertIn('R_AliasTorchLayer=AW_ItemsTorchLayer;', items)
        self.assertIn('AW_SkelGroup(tab,"torch")', items)
        # the flame point at the item's own scale (0.25), not the bone's units
        self.assertIn('out[k]=table[t].emitter[k]*AW_ITEMS_ITEM_SCALE;', items)
        self.assertIn('#define AW_ITEMS_ITEM_SCALE 0.25f', items)


if __name__ == '__main__':
    unittest.main()
