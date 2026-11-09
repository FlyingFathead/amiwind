# SPDX-License-Identifier: GPL-3.0-only
"""Payload sharing (tools/payload_share.py): file aliases (IMAGE-DUPLICATE-FILES-46), shared actor skins
(IMAGE-ACTOR-SKIN-REPEATS-46) and shared actor shapes (IMAGE-BIGGER-THAN-ORIGINAL-62). The builder's forms rebuild
every original byte; the engine's readers (common.c COM_FindFile, model.c / model_alias_stream.inc) read exactly
what the builder writes; the payload pass does nothing unless asked (build.py asks for all three by default).
Synthetic data, plus real models listed in AMIWIND_SHAPE_MODELS for the native shape test."""
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import payload_share as share  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


def model(skin_value, frames=b'frames', width=8, height=4):
    """A small single-skin alias model: header (84 bytes), skin type 0, pixels, then 'frames' bytes."""
    header = bytearray(84)
    header[:8] = b'IDPO' + struct.pack('<i', 6)
    struct.pack_into('<3i', header, 48, 1, width, height)
    return bytes(header) + struct.pack('<i', 0) + bytes([skin_value]) * (width * height) + frames


class SharedSkins(unittest.TestCase):
    def test_stored_form_rebuilds_the_model(self):
        raw = model(7)
        at, pixels = share.skin_of(raw)
        digest = share.sha256(raw[at:at + pixels])
        stored = share.shared_model(raw, digest)
        self.assertTrue(share.is_shared(stored))
        self.assertEqual(len(raw) - len(stored), pixels + 4 - share.SKIN_REF)
        self.assertEqual(share.expand_shared_skin(stored, lambda name: raw[at:at + pixels]), raw)
        self.assertIsNone(share.skin_of(stored))            # never shared twice

    def test_only_repeated_skins_of_actor_models_are_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'progs').mkdir(parents=True)
            (id1 / 'gallery').mkdir()
            originals = {'progs/a_one.mdl': model(1, b'stand'), 'progs/a_one_m.mdl': model(1, b'moving frames'),
                         'progs/a_two.mdl': model(2), 'gallery/f1.mdl': model(1)}
            for rel, raw in originals.items():
                (id1 / rel).write_bytes(raw)
            groups = share.plan_skins(id1)
            self.assertEqual(list(groups.values()), [['progs/a_one.mdl', 'progs/a_one_m.mdl']])
            record = share.apply_skins(id1, groups)
            self.assertEqual((record['skins'], record['models'], record['files_added']), (1, 2, 1))
            skin = next(iter(groups))
            self.assertEqual((id1 / share.skin_name(skin)).read_bytes(), bytes([1]) * 32)
            for rel, raw in originals.items():
                stored = (id1 / rel).read_bytes()
                rebuilt = share.expand_shared_skin(stored, lambda name: (id1 / name).read_bytes()) \
                    if share.is_shared(stored) else stored
                self.assertEqual(rebuilt, raw, rel)
            self.assertEqual(record['bytes_saved'], sum(len(r) for r in originals.values()) - sum(
                p.stat().st_size for p in id1.rglob('*') if p.is_file()))
            self.assertFalse(share.is_shared((id1 / 'progs/a_two.mdl').read_bytes()))
            self.assertFalse(share.is_shared((id1 / 'gallery/f1.mdl').read_bytes()))

    def test_both_methods_are_off_unless_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            for name in ('a_x.mdl', 'a_y.mdl'):
                (id1 / 'progs' / name).write_bytes(model(3, bytes(5000)))
            before = sorted((p.name, p.read_bytes()) for p in id1.rglob('*') if p.is_file())
            record = share.share_payload(id1, log=lambda line: None)
            self.assertEqual(record, {'file_aliases': False, 'shared_skins': False, 'bytes_removed': 0})
            self.assertEqual(sorted((p.name, p.read_bytes()) for p in id1.rglob('*') if p.is_file()), before)


def shaped(blocks_value, frames=b'frames', verts=3, tris=2, width=8, height=4, skin_value=1):
    """A small single-skin alias model with VERTS ST entries and TRIS triangles of BLOCKS_VALUE bytes."""
    header = bytearray(model(skin_value, b'', width, height))
    struct.pack_into('<2i', header, 60, verts, tris)
    return bytes(header) + bytes([blocks_value]) * (verts * 12 + tris * 16) + frames


class SharedShapes(unittest.TestCase):
    def test_stored_form_rebuilds_the_model(self):
        raw = shaped(5)
        at, st, tri = share.shape_of(raw)
        self.assertEqual((at, st, tri), (84 + 4 + 32, 36, 32))
        digest = share.sha256(raw[at:at + st + tri])
        stored = share.shared_shape_model(raw, digest)
        self.assertTrue(share.is_shape_shared(stored))
        self.assertEqual(len(raw) - len(stored), st + tri - share.SHAPE_REF)
        self.assertEqual(share.expand_shared_shape(stored, lambda name: raw[at:at + st + tri]), raw)
        self.assertIsNone(share.shape_of(stored))            # never shared twice
        with self.assertRaises(ValueError):
            share.expand_shared_shape(stored, lambda name: raw[at:at + st + tri - 1])

    def test_shape_after_a_shared_skin(self):
        raw = shaped(6)
        at, pixels = share.skin_of(raw)
        skin_digest = share.sha256(raw[at:at + pixels])
        skinned = share.shared_model(raw, skin_digest)
        sat, st, tri = share.shape_of(skinned)
        self.assertEqual(sat, 84 + share.SKIN_REF)
        blocks = skinned[sat:sat + st + tri]
        stored = share.shared_shape_model(skinned, share.sha256(blocks))
        self.assertTrue(share.is_shared(stored) and share.is_shape_shared(stored))
        rebuilt = share.expand_shared_skin(share.expand_shared_shape(stored, lambda name: blocks),
                                           lambda name: raw[at:at + pixels])
        self.assertEqual(rebuilt, raw)

    def test_only_repeated_shapes_of_top_level_progs_models_are_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'progs/sub').mkdir(parents=True)
            (id1 / 'items').mkdir()
            originals = {'progs/a_one.mdl': shaped(1, b'stand', skin_value=1),
                         'progs/n_two.mdl': shaped(1, b'other frames', skin_value=2),
                         'progs/c_three.mdl': shaped(2), 'progs/sub/a_four.mdl': shaped(1),
                         'items/a_five.mdl': shaped(1), 'progs/npc_lod_x.mdl': shaped(1)}
            for rel, raw in originals.items():
                (id1 / rel).write_bytes(raw)
            (id1 / share.NPC_LOD_MANIFEST).write_text('progs/npc_lod_x.mdl 1 2 3\n', encoding='ascii')
            groups = share.plan_shapes(id1, jobs=2)
            self.assertEqual(list(groups.values()), [['progs/a_one.mdl', 'progs/n_two.mdl']])
            record = share.apply_shapes(id1, groups)
            self.assertEqual((record['shapes'], record['models'], record['files_added']), (1, 2, 1))
            digest = next(iter(groups))
            self.assertEqual((id1 / share.shape_name(digest)).read_bytes(), bytes([1]) * 68)
            for rel, raw in originals.items():
                stored = (id1 / rel).read_bytes()
                rebuilt = share.expand_shared_shape(stored, lambda name: (id1 / name).read_bytes()) \
                    if share.is_shape_shared(stored) else stored
                self.assertEqual(rebuilt, raw, rel)
            self.assertEqual(record['bytes_saved'], 68 - 2 * share.SHAPE_REF)
            self.assertEqual(share.identity(id1)['shapes'], 0)      # nothing left to share

    def test_identity_over_a_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            for name, value in (('a_x.mdl', 3), ('a_y.mdl', 3), ('n_z.mdl', 3), ('a_w.mdl', 4)):
                (id1 / 'progs' / name).write_bytes(shaped(value, bytes(100)))
            result = share.identity(id1, jobs=1)
            self.assertEqual((result['shapes'], result['models'], result['byte_identical']), (1, 3, 3))
            self.assertEqual(result['bytes_saved'], 2 * 68 - 3 * share.SHAPE_REF)
            self.assertEqual(share.main(['identity', str(id1)]), 0)

    def test_payload_pass_order_and_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            for name in ('a_x.mdl', 'a_y.mdl'):
                (id1 / 'progs' / name).write_bytes(shaped(3, bytes(5000)))
            originals = {p.name: p.read_bytes() for p in (id1 / 'progs').iterdir()}
            record = share.share_payload(id1, shared_skins=True, shared_shapes=True, file_aliases=True,
                                         log=lambda line: None)
            self.assertEqual(record['skins']['models'], 2)
            self.assertEqual(record['shapes']['models'], 2)
            # both stored forms are byte-identical then: one is an alias of the other
            self.assertEqual(record['aliases']['files_removed'], 1)
            table = share.read_alias_table((id1 / share.ALIAS_FILE).read_bytes())
            for name, raw in originals.items():
                path = id1 / 'progs' / name
                stored = (path if path.is_file() else id1 / table[('progs/' + name).casefold()]).read_bytes()
                read = lambda rel: (id1 / rel).read_bytes()
                self.assertEqual(share.expand_shared_skin(share.expand_shared_shape(stored, read), read), raw)


def tiled(pattern, frames=b'frames', width=32, height=32, verts=3, tris=2):
    """A single-skin alias model with a 32 x 32 skin (4 tiles) whose pixels are PATTERN(x, y), then ST + triangles."""
    raw = bytearray(shaped(9, frames, verts, tris, width, height))
    for y in range(height):
        for x in range(width):
            raw[88 + y * width + x] = pattern(x, y) & 255
    return bytes(raw)


class SkinTiles(unittest.TestCase):
    def test_stored_form_rebuilds_the_model(self):
        raw = tiled(lambda x, y: x * 7 + y)
        at, width, height = share.tile_skin_of(raw)
        cut = share.cut_tiles(raw[at:at + width * height], width, height)
        self.assertEqual((len(cut), len(cut[0])), (4, 256))
        numbers = [3, 0, 65536 + 1, 1]                           # a tile of chunk 1 too
        chunks = {0: b''.join([cut[1], cut[3], cut[0], cut[0]]), 1: bytes(256) + cut[2]}
        digest = '0123456789abcdef' * 4
        stored = share.tiled_model(raw, digest, numbers)
        self.assertTrue(share.is_tiled(stored))
        self.assertEqual(len(stored), len(raw) - width * height + 24 + 4 * 4)
        read = lambda name: chunks[int(name[-7:-5], 16)]
        self.assertEqual(share.tile_pool_name(digest, 1), 'progs/tiles/0123456789abcdef-01.awtp')
        self.assertEqual(share.expand_tiled_skin(stored, read), raw)
        self.assertIsNone(share.tile_skin_of(stored))            # never tiled twice
        # the shape pass sees past the table
        sat, st, tri = share.shape_of(stored)
        self.assertEqual((sat, st, tri), (84 + 4 + 24 + 16, 36, 32))
        with self.assertRaises(ValueError):
            share.expand_tiled_skin(stored, lambda name: chunks[0][:256])
        self.assertEqual(share.read_plan([0, 1, 2, 70, 65536]), (3, 5))   # a run ends at 64 tiles and at a chunk
        self.assertEqual(share.read_plan([0, 9, 10, 100]), (3, 4))        # a hole of 9 tiles is sought over

    def test_one_pool_for_the_actor_skins(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'progs').mkdir(parents=True)
            originals = {'progs/a_one.mdl': tiled(lambda x, y: x // 16), 'progs/n_two.mdl': tiled(lambda x, y: 2 * (y // 16)),
                         'progs/c_three.mdl': tiled(lambda x, y: x // 16), 'progs/a_odd.mdl': tiled(lambda x, y: x,
                                                                                                 width=24),
                         'progs/npc_lod_x.mdl': tiled(lambda x, y: 1)}
            for rel, raw in originals.items():
                (id1 / rel).write_bytes(raw)
            (id1 / share.NPC_LOD_MANIFEST).write_text('progs/npc_lod_x.mdl 1 2 3\n', encoding='ascii')
            pool = share.plan_tiles(id1, jobs=2)
            self.assertEqual(sorted(rel for rel, _ in pool['models']), ['progs/a_one.mdl', 'progs/n_two.mdl'])
            self.assertEqual(len(pool['tiles']), 3)                  # (0, 1) by x and (0, 2) by y share the 0 tile
            self.assertEqual(pool['tiles'][0], bytes(256))           # the shared tile first
            record = share.apply_tiles(id1, pool)
            self.assertEqual((record['models'], record['chunks'], record['tiles']), (2, 1, 3))
            for rel, raw in originals.items():
                stored = (id1 / rel).read_bytes()
                rebuilt = share.expand_tiled_skin(stored, lambda name: (id1 / name).read_bytes()) \
                    if share.is_tiled(stored) else stored
                self.assertEqual(rebuilt, raw, rel)
            self.assertEqual(record['bytes_saved'], sum(len(r) for r in originals.values()) - sum(
                p.stat().st_size for p in id1.rglob('*.mdl')) - 3 * 256)

    def test_payload_pass_with_shapes_and_tiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            for name, value in (('a_x.mdl', 1), ('a_y.mdl', 2)):
                (id1 / 'progs' / name).write_bytes(tiled(lambda x, y, v=value: v * (x // 16), bytes(5000)))
            originals = {p.name: p.read_bytes() for p in (id1 / 'progs').iterdir()}
            record = share.share_payload(id1, shared_skins=True, shared_shapes=True, skin_tiles=True,
                                         file_aliases=True, log=lambda line: None)
            self.assertEqual((record['shapes']['models'], record['tiles']['models']), (2, 2))
            read = lambda rel: (id1 / rel).read_bytes()
            for name, raw in originals.items():
                stored = read('progs/' + name)
                self.assertEqual(share.expand_tiled_skin(share.expand_shared_shape(stored, read), read), raw)
                self.assertEqual(share.expand_shared_shape(share.expand_tiled_skin(stored, read), read), raw)


class FileAliases(unittest.TestCase):
    def payload(self, root):
        id1 = Path(root)
        (id1 / 'sound/npc').mkdir(parents=True)
        (id1 / 'sound/pool').mkdir(parents=True)
        (id1 / 'progs').mkdir()
        same = b'RIFF' + bytes(6000)
        files = {'sound/npc/b_2.wav': same, 'sound/pool/a_1.wav': same, 'sound/npc/A_3.wav': same,
                 'progs/x.mdl': b'm' * 5000, 'progs/y.mdl': b'm' * 5000, 'progs/small.tag': b't',
                 'progs/small2.tag': b't', 'progs/unique.mdl': b'u' * 9000, 'music/track00.mws': b's' * 9000,
                 'music/track01.mws': b's' * 9000}
        for rel, data in files.items():
            (id1 / rel).parent.mkdir(parents=True, exist_ok=True)
            (id1 / rel).write_bytes(data)
        return id1, files

    def test_every_name_still_reads_its_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1, files = self.payload(tmp)
            groups = share.plan_aliases(id1, jobs=1)
            record = share.apply_aliases(id1, groups)
            table = share.read_alias_table((id1 / share.ALIAS_FILE).read_bytes())
            for rel, data in files.items():
                path = id1 / rel if (id1 / rel).is_file() else id1 / table[rel.casefold()]
                self.assertEqual(path.read_bytes(), data, rel)
            # small files and the soundtrack (opened by path, aw_music.c) keep their own copies
            for rel in ('progs/small.tag', 'progs/small2.tag', 'music/track00.mws', 'music/track01.mws'):
                self.assertTrue((id1 / rel).is_file(), rel)
            self.assertEqual(record['files_removed'], 3)
            self.assertEqual(record['bytes_saved'], 2 * 6004 + 5000 - record['table_bytes'])

    def test_table_order_is_the_engine_order(self):
        names = ['progs/a_b.mdl', 'progs/ab.mdl', 'progs/A_c.mdl', 'progs/aZ.mdl']
        groups = [('progs/target.mdl', names, 5000)]
        table = share.alias_table(groups).decode('ascii').split('\n')
        aliases = [line.split('\t')[0] for line in table[2:-1]]
        # COM_AliasCompare reads a-z as A-Z: '_' (0x5F) sorts after every letter
        self.assertEqual(aliases, ['progs/ab.mdl', 'progs/aZ.mdl', 'progs/a_b.mdl', 'progs/A_c.mdl'])
        self.assertEqual(table[0], 'AWALIAS1 1 4')
        with self.assertRaises(ValueError):
            share.alias_table([('t.mdl', ['x.mdl', 'X.mdl'], 1)])


@unittest.skipIf(os.name == 'nt', 'Project workflow: no generated Windows test executables; run this native oracle on Linux')
@unittest.skipUnless(COMPILER, 'install a host C compiler or set CC')
class EngineReaders(unittest.TestCase):
    def test_engine_alias_lookup_reads_the_builder_table(self):
        groups = [('progs/target.mdl', ['progs/a_b.mdl', 'progs/ab.mdl', 'progs/A_c.mdl'], 5000),
                  ('sound/pool/x.wav', ['sound/npc/y.wav'], 9000)]
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / 'file-aliases.txt'
            table.write_bytes(share.alias_table(groups))
            bad = Path(tmp) / 'bad.txt'
            raw = share.alias_table(groups).decode('ascii').split('\n')
            raw[3], raw[4] = raw[4], raw[3]                  # out of order: the engine ignores the table
            bad.write_text('\n'.join(raw), encoding='ascii', newline='\n')
            import test_aga_native_source as native
            native.NativeSourceTests().compile_run('aga_file_alias_test.c', [SRC / 'common.c'],
                                                   arguments=[str(table.resolve()), str(bad.resolve())])

    def test_shared_skin_models_decode_like_inline_skins(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_shared_skin_test.c',
            [SRC / name for name in ('model.c', 'aw_skel.c', 'aw_skel_load.c', 'mathlib.c')],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-Wl,--wrap=malloc'])

    def test_shared_shape_models_decode_like_inline_blocks(self):
        # AMIWIND_SHAPE_MODELS: a file listing real converted actor models (one path a line, read only) that are
        # decoded too, as the identity run over a release image does.
        import test_aga_native_source as native
        listed = os.environ.get('AMIWIND_SHAPE_MODELS')
        models = Path(listed).read_text(encoding='utf-8').split() if listed else []
        native.NativeSourceTests().compile_run('aga_shared_shape_test.c',
            [SRC / name for name in ('model.c', 'aw_skel.c', 'aw_skel_load.c', 'mathlib.c')],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-Wl,--wrap=malloc'],
            arguments=models)

    def test_tiled_skin_models_decode_like_inline_skins(self):
        # AMIWIND_TILE_PAYLOAD: "TILED_ID1 ORIGINAL_ID1 LIST" of a real payload tiled by apply_tiles (read only):
        # every listed model is rebuilt byte for byte and the reader timed against the whole file.
        import test_aga_native_source as native
        listed = os.environ.get('AMIWIND_TILE_PAYLOAD')
        native.NativeSourceTests().compile_run('aga_tiled_skin_test.c',
            [SRC / name for name in ('model.c', 'aw_skel.c', 'aw_skel_load.c', 'mathlib.c')],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-Wl,--wrap=malloc'],
            arguments=listed.split() if listed else [])


class Wiring(unittest.TestCase):
    def test_builder_options_default_on(self):
        # on by default since v0.0.47 (decided for the project, 2026-10-21); off stays selectable
        import build
        args = build.parser().parse_args([])
        self.assertEqual((args.file_aliases, args.shared_skins, args.shared_shapes), ('on', 'on', 'on'))
        args = build.parser().parse_args(['--file-aliases', 'off', '--shared-skins', 'off', '--shared-shapes', 'off'])
        self.assertEqual((args.file_aliases, args.shared_skins, args.shared_shapes), ('off', 'off', 'off'))
        image = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("share_payload(boot/'id1'", image)
        self.assertIn("shared_shapes=getattr(args, 'shared_shapes', False)", image)
        model = (SRC / 'model.c').read_text(encoding='utf-8')
        self.assertIn('progs/shapes/', model)
        self.assertEqual(share.SHAPE_DIR, 'progs/shapes')
        self.assertNotIn('off by default until', (ROOT / 'tools/payload_share.py').read_text(encoding='utf-8'))
        common = (SRC / 'common.c').read_text(encoding='utf-8')
        self.assertIn('#define COM_ALIAS_FILE "file-aliases.txt"', common)
        self.assertEqual(share.ALIAS_FILE, 'file-aliases.txt')


if __name__ == '__main__':
    unittest.main()
