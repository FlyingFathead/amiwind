# SPDX-License-Identifier: GPL-3.0-only
"""The one map path helper (tools/map_files.py) and the engine's one resolver (aw_mappath.c): CHIM frame maps
are maps/<name>.chim (or .bsp with --chim-frame-ext bsp), found by their "_chim_frame" key, never by name;
no code outside the helpers builds a frame-map path by hand."""
import ast
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import map_files as MF  # noqa: E402
from chim_fixture import frame_header_bytes  # noqa: E402


class Helper(unittest.TestCase):
    def test_frame_ext_default_switch_and_refusal(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(MF.FRAME_EXT_VARIABLE, None)
            self.assertEqual(MF.frame_ext(), '.chim')                   # default: the .chim extension
            os.environ[MF.FRAME_EXT_VARIABLE] = 'bsp'
            self.assertEqual(MF.frame_ext(), '.bsp')                    # the earlier form stays selectable
            self.assertEqual(MF.frame_ext('chim'), '.chim')             # an explicit value wins
            os.environ[MF.FRAME_EXT_VARIABLE] = 'pak'
            with self.assertRaises(ValueError):
                MF.frame_ext()
            self.assertEqual(MF.export_frame_ext('chim'), 'chim')
            self.assertEqual(os.environ[MF.FRAME_EXT_VARIABLE], 'chim')

    def test_resolution_matches_the_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            (maps / 'vf1637.chim').write_bytes(frame_header_bytes((-7, 2)))
            (maps / 'vf1638.bsp').write_bytes(b'legacy')
            self.assertEqual(MF.map_file(maps, 'vf1637').name, 'vf1637.chim')   # the frame map first
            self.assertEqual(MF.map_file(maps, 'vf1638').name, 'vf1638.bsp')
            self.assertEqual(MF.map_file(maps, 'gone').name, 'gone.bsp')        # missing: the usual .bsp name
            self.assertEqual(MF.map_rel(tmp, 'vf1637'), 'maps/vf1637.chim')
            self.assertEqual([p.name for p in MF.map_files(maps)], ['vf1637.chim', 'vf1638.bsp'])
            self.assertEqual([p.name for p in MF.frame_maps(maps)], ['vf1637.chim'])
            self.assertEqual(MF.map_stem('maps/vf1637.chim'), 'vf1637')
            self.assertEqual(MF.map_stem('vf1638.bsp'), 'vf1638')
            self.assertTrue(MF.is_map_name('x.CHIM') and MF.is_map_name('x.bsp') and not MF.is_map_name('x.far'))

    def test_frames_are_told_by_their_key_not_their_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp)
            (maps / 'balmora-chim.bsp').write_bytes(frame_header_bytes(key=False))   # a name, no key
            (maps / 'vf0001.bsp').write_bytes(frame_header_bytes((3, -4)))         # a key, a legacy name
            (maps / 'broken.chim').write_bytes(b'\x1d\0\0\0' + bytes(8))
            self.assertFalse(MF.is_chim_frame(maps / 'balmora-chim.bsp'))
            self.assertTrue(MF.is_chim_frame(maps / 'vf0001.bsp'))
            self.assertFalse(MF.is_chim_frame(maps / 'broken.chim'))
            self.assertFalse(MF.is_chim_frame(maps / 'absent.chim'))
            self.assertEqual(MF.frame_cell(maps / 'vf0001.bsp'), (3, -4))
            self.assertEqual([p.name for p in MF.frame_maps(maps)], ['vf0001.bsp'])
            self.assertTrue(MF.is_chim_frame((maps / 'vf0001.bsp').read_bytes()))

    def test_region_frames_by_the_ownership_table(self):
        from chim import regions
        with tempfile.TemporaryDirectory() as tmp:
            world, maps = Path(tmp) / 'world', Path(tmp) / 'maps'
            world.mkdir()
            maps.mkdir()
            table = regions.ownership({(-7, 2): 'seabed'})
            import json
            (world / regions.TABLE_FILE).write_text(json.dumps(table), encoding='utf-8')
            (maps / 'vf0100.chim').write_bytes(frame_header_bytes((-7, 2)))
            (maps / 'balmora-chim.chim').write_bytes(frame_header_bytes((0, -2)))   # a town frame: not owned
            self.assertEqual(MF.owned_frames(world), {(-7, 2): regions.frame_id((-7, 2))})
            self.assertEqual(MF.region_frame_maps(maps, world), {'vf0100.chim': regions.frame_id((-7, 2))})
            self.assertEqual(MF.region_frame_maps(maps, None), {})


class Migration(unittest.TestCase):
    """tools/chim/frame_ext_migrate.py: frame maps named .bsp get their .chim name by a hard link (nothing
    copied or rebuilt), found by their key; stage manifests follow; release and protected folders stay."""

    def workspace(self, tmp):
        import json
        from unit_tree import of_manifest
        build = Path(tmp) / 'build'
        run = build / '2026_10_10_v0.0.36-dev1_full_0dbc838'
        maps = run / 'image/boot/id1/maps'
        maps.mkdir(parents=True)
        (maps / 'balmora-chim.bsp').write_bytes(frame_header_bytes((0, -2)))
        (maps / 'vf0100.bsp').write_bytes(frame_header_bytes((-7, 2), pad=3))   # a region frame, legacy name
        (maps / 'bm001.bsp').write_bytes(frame_header_bytes(key=False))          # a legacy map: stays
        (maps / 'balmora-chim.far').write_bytes(b'far')
        files = {('image/boot/id1/maps/' + p.name): {'size': p.stat().st_size, 'sha256': MF_sha(p), 'mode': 420}
                 for p in sorted(maps.iterdir())}
        manifest = {'schema': 'amiwind-stage-outputs-v1', 'stage': 'image', 'files': files, 'links': {}}
        manifest['tree'] = of_manifest(manifest)
        (run / 'profile/manifests').mkdir(parents=True)
        (run / 'profile/manifests/image.json').write_text(json.dumps(manifest), encoding='utf-8')
        release = build / '2026_10_10_v0.0.35_full_3cbe85a/image/boot/id1/maps'
        release.mkdir(parents=True)
        (release / 'seyda-chim.bsp').write_bytes(frame_header_bytes((1, 1)))
        older = build / 'final4c-d956883/image/boot/id1/maps'       # a release run named before the naming rule
        older.mkdir(parents=True)
        (older / 'seyda-chim.bsp').write_bytes(frame_header_bytes((1, 1)))
        archived = Path(tmp) / 'build/archive/old/maps'
        archived.mkdir(parents=True)
        (archived / 'seyda-chim.bsp').write_bytes(frame_header_bytes((1, 1)))
        return build, run, maps

    def test_dry_run_lists_and_changes_nothing(self):
        from chim import frame_ext_migrate as M
        with tempfile.TemporaryDirectory() as tmp:
            build, run, maps = self.workspace(tmp)
            before = sorted(p.name for p in maps.iterdir())
            renames, skipped = M.find([build])
            self.assertEqual(sorted(Path(r['from']).name for r in renames), ['balmora-chim.bsp', 'vf0100.bsp'])
            self.assertTrue(all(r['state'] == 'rename' and r['run'] == str(run) for r in renames))
            self.assertEqual(sorted(s['reason'].split(' ')[0] for s in skipped), ['protected', 'release', 'release'])
            self.assertEqual(M.main([str(build)]), 0)
            self.assertEqual(sorted(p.name for p in maps.iterdir()), before)

    def test_apply_links_renames_and_updates_the_manifest(self):
        import json
        from chim import frame_ext_migrate as M
        from unit_tree import of_manifest
        with tempfile.TemporaryDirectory() as tmp:
            build, run, maps = self.workspace(tmp)
            inode = (maps / 'balmora-chim.bsp').stat().st_ino
            digest = MF_sha(maps / 'balmora-chim.bsp')
            self.assertEqual(M.main([str(build), '--apply', '--json', str(Path(tmp) / 'r.json')]), 0)
            self.assertEqual(sorted(p.name for p in maps.iterdir()),
                             ['balmora-chim.chim', 'balmora-chim.far', 'bm001.bsp', 'vf0100.chim'])
            self.assertEqual((maps / 'balmora-chim.chim').stat().st_ino, inode)          # the same file
            self.assertEqual(MF_sha(maps / 'balmora-chim.chim'), digest)
            manifest = json.loads((run / 'profile/manifests/image.json').read_text(encoding='utf-8'))
            self.assertIn('image/boot/id1/maps/balmora-chim.chim', manifest['files'])
            self.assertNotIn('image/boot/id1/maps/balmora-chim.bsp', manifest['files'])
            self.assertEqual(manifest['files']['image/boot/id1/maps/balmora-chim.chim']['sha256'], digest)
            self.assertEqual(manifest['tree'], of_manifest(manifest))
            self.assertTrue((build / '2026_10_10_v0.0.35_full_3cbe85a/image/boot/id1/maps/seyda-chim.bsp').is_file())
            self.assertTrue((build / 'archive/old/maps/seyda-chim.bsp').is_file())
            report = json.loads((Path(tmp) / 'r.json').read_text(encoding='utf-8'))
            self.assertEqual((report['frame_maps'], report['to_rename'], report['conflicts']), (2, 2, 0))
            renames, _ = M.find([build])                                                # done: nothing left
            self.assertEqual(renames, [])

    def test_a_conflicting_chim_file_is_left_alone(self):
        from chim import frame_ext_migrate as M
        with tempfile.TemporaryDirectory() as tmp:
            build, run, maps = self.workspace(tmp)
            (maps / 'balmora-chim.chim').write_bytes(b'other')
            renames, _ = M.find([build])
            row = next(r for r in renames if r['from'].endswith('balmora-chim.bsp'))
            self.assertTrue(row['state'].startswith('conflict'))
            M.apply(renames)
            self.assertTrue((maps / 'balmora-chim.bsp').is_file())
            self.assertEqual((maps / 'balmora-chim.chim').read_bytes(), b'other')


def MF_sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_strings(path):
    """String constants of a Python file that are not docstrings (f-string parts included)."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docs.add(id(first.value))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


# '-chim.bsp' / '-chim.chim', the bare extension '.chim' and a maps/... .chim path (not stats keys such as 'bytes.chim')
HAND_MADE = re.compile(r'-chim\.(bsp|chim)|^\.chim$|maps/.*\.chim')


class NoHandMadeFramePaths(unittest.TestCase):
    def test_python_builds_frame_map_paths_only_in_the_helper(self):
        # A frame map's file name comes from tools/map_files.py (frame_map_path, map_file, map_files), never
        # from a literal: '-chim.bsp', '.chim' (the extension) outside the helper are refused.
        allowed = {ROOT / 'tools/map_files.py'}
        found = []
        for base in (ROOT / 'tools', ROOT / 'src'):
            for path in sorted(base.rglob('*.py')):
                if path in allowed:
                    continue
                for line, text in code_strings(path):
                    if HAND_MADE.search(text):
                        found.append('%s:%d %r' % (path.relative_to(ROOT).as_posix(), line, text))
        self.assertEqual(found, [], 'frame-map paths built by hand (use tools/map_files.py)')

    def test_engine_builds_map_paths_only_in_the_resolver(self):
        # Every "maps/<name>.bsp" / ".chim" the engine opens comes from AW_MapPath (aw_mappath.c).
        allowed = {'aw_mappath.c', 'aw_mappath.h'}
        literal = re.compile(r'"(?:[^"\\]|\\.)*"')
        found = []
        src = ROOT / 'engine/aga/src'
        for path in sorted(list(src.glob('*.[ch]')) + list(src.glob('chim/*.[ch]'))):
            if path.name in allowed:
                continue
            text = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='latin-1'), flags=re.S)
            text = re.sub(r'//[^\n]*', '', text)
            for match in literal.finditer(text):
                value = match.group(0)
                if re.search(r'\.bsp"$|\.chim"$|^"maps/%s\.(bsp|chim)', value) or value in ('".bsp"', '".chim"'):
                    found.append('%s %s' % (path.name, value))
        self.assertEqual(found, [], 'map paths built outside AW_MapPath')

    @unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
    def test_engine_resolver_and_refusals_native(self):
        import shutil
        if not shutil.which('cc'):
            self.skipTest('requires a C compiler')
        from test_chim_engine_native import SRC, compile_and_run
        compile_and_run(self, 'aga_mappath_test.c', [SRC / 'aw_mappath.c', SRC / 'aw_format.c'])

    def test_every_map_path_user_includes_the_resolver(self):
        src = ROOT / 'engine/aga/src'
        for name in ('aw_region.c', 'aw_section.c', 'aw_scene.c', 'aw_gallery.c', 'aw_arena.c', 'aw_wait.c',
                     'sv_main.c', 'chim/chim_world.c'):
            self.assertIn('#include "aw_mappath.h"', (src / name).read_text(encoding='latin-1'), name)
        self.assertIn('aw_mappath.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        world = (src / 'chim/chim_world.c').read_text(encoding='latin-1')
        self.assertIn('aw_chim_world = 1;', world)          # the resolver picks .chim only with a CHIM world
        spawn = (src / 'sv_main.c').read_text(encoding='latin-1')
        self.assertIn('AW_MapRefused (sv.modelname, sv.worldmodel->entities', spawn)
        self.assertIn('AW_MapChimOrphan (server', spawn)


if __name__ == '__main__':
    unittest.main()
