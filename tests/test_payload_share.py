# SPDX-License-Identifier: GPL-3.0-only
"""Payload sharing (tools/payload_share.py): file aliases (IMAGE-DUPLICATE-FILES-46) and shared actor skins
(IMAGE-ACTOR-SKIN-REPEATS-46). The builder's forms rebuild every original byte; the engine's readers (common.c
COM_FindFile, model.c / model_alias_stream.inc) read exactly what the builder writes; both stay off by default.
Synthetic data only."""
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
            [SRC / name for name in ('model.c', 'mathlib.c')],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-Wl,--wrap=malloc'])


class Wiring(unittest.TestCase):
    def test_builder_options_default_on(self):
        # on by default since v0.0.47 (decided for the project, 2026-10-21); off stays selectable
        import build
        args = build.parser().parse_args([])
        self.assertEqual((args.file_aliases, args.shared_skins), ('on', 'on'))
        args = build.parser().parse_args(['--file-aliases', 'off', '--shared-skins', 'off'])
        self.assertEqual((args.file_aliases, args.shared_skins), ('off', 'off'))
        image = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("share_payload(boot/'id1'", image)
        common = (SRC / 'common.c').read_text(encoding='utf-8')
        self.assertIn('#define COM_ALIAS_FILE "file-aliases.txt"', common)
        self.assertEqual(share.ALIAS_FILE, 'file-aliases.txt')


if __name__ == '__main__':
    unittest.main()
