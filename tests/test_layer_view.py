# SPDX-License-Identifier: GPL-3.0-only
"""Per-unit views of what the selected expansion layers change (tools/layer_view.py, BUILD-UNIT-KEYS-LAYER-BLIND-66):
on small synthetic masters and archives (no game data). A unit the layers do not touch keeps its base-game key; a unit
that reads a changed record or a replaced archive file gets another; the base game alone changes nothing."""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

import layer_view  # noqa: E402
from test_layered_archives import write_bsa  # noqa: E402
from test_mwad_masters import ADDON, BASE  # noqa: E402

BOTH = ['Morrowind.esm', 'Tribunal.esm']


class LayerViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        (self.data / 'Morrowind.esm').write_bytes(BASE)
        (self.data / 'Tribunal.esm').write_bytes(ADDON)
        write_bsa(self.data / 'Morrowind.bsa', {'meshes\\a.nif': b'uses tx_wood.dds', 'meshes\\b.nif': b'plain',
                                                'textures\\tx_wood.dds': b'base wood', 'textures\\same.dds': b'x'})
        write_bsa(self.data / 'Tribunal.bsa', {'textures\\tx_wood.dds': b'tribunal wood', 'textures\\same.dds': b'x',
                                               'meshes\\t.nif': b'new'})
        for memo in (layer_view._DELTA, layer_view._OVERRIDES, layer_view._NIFS):
            memo.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_base_game_alone_has_no_view(self):
        self.assertEqual(layer_view.delta(self.data, ['Morrowind.esm']), {})
        self.assertEqual(layer_view.overrides(self.data, ['Morrowind.esm']), {})
        rows = layer_view.view(self.data, [layer_view.record_key('STAT', 'rock')], ['meshes/a.nif'], ['Morrowind.esm'])
        self.assertEqual(rows, [])
        self.assertEqual(layer_view.identity(self.data, [('STAT', 'rock')], ['a.nif'], ['Morrowind.esm'], base='L'), 'L')

    def test_delta_holds_the_changed_added_and_deleted_records(self):
        changed = layer_view.delta(self.data, BOTH)
        self.assertIn(('STAT', 'rock'), changed)           # replaced by the addon
        self.assertIn(('STAT', 'bush'), changed)           # new
        self.assertIsNone(changed[('STAT', 'tree')])       # deleted
        self.assertIn(('int', 'room'), changed)            # a base cell the addon adds a reference to
        self.assertIn(('int', 'new room'), changed)

    def test_overrides_are_the_files_replaced_with_other_bytes(self):
        self.assertEqual(sorted(layer_view.overrides(self.data, BOTH)), ['textures/tx_wood.dds'])

    def test_untouched_unit_keeps_its_base_key(self):
        # reads only an unchanged record and a model whose textures the layers do not replace
        self.assertEqual(layer_view.identity(self.data, [('STAT', 'unchanged')], ['meshes/b.nif'], BOTH, base='L'), 'L')

    def test_changed_record_or_replaced_texture_changes_the_key(self):
        by_record = layer_view.identity(self.data, [layer_view.record_key('STAT', 'Rock')], [], BOTH, base='L')
        by_texture = layer_view.identity(self.data, [], ['a.nif'], BOTH, base='L')   # its bytes name tx_wood
        self.assertNotEqual(by_record, 'L')
        self.assertNotEqual(by_texture, 'L')
        self.assertNotEqual(by_record, by_texture)
        rows = layer_view.view(self.data, [], ['textures/tx_wood.dds'], BOTH)
        self.assertEqual([r[1] for r in rows], ['textures/tx_wood.dds'])

    def test_asset_names_walks_nested_values(self):
        names = layer_view.asset_names({'parts': [{'mesh': 'b\\Robe.NIF'}, ('x', 'tx_a.dds')], 'n': 3, 'id': 'r'})
        self.assertEqual(names, {'b/robe.nif', 'tx_a.dds'})

    def test_layer_archive_reads_are_recorded_and_gaps_named(self):
        from mwad import archives
        from mwad.esm import read_bsa_asset
        layer_view.begin()
        # looked up after begin(), as a bake's own import does (names imported at module level are wrapped too)
        archive = archives.layered_bsa(self.data, BOTH)
        read_bsa_asset(archive, 'meshes/a.nif')                 # the base archive's own file: not a layer read
        read_bsa_asset(archive, 'textures/tx_wood.dds')
        self.assertEqual(layer_view.reads(), ['textures/tx_wood.dds'])
        self.assertEqual(layer_view.gaps(layer_view.reads(), [], self.data, BOTH), ['textures/tx_wood.dds'])
        rows = layer_view.view(self.data, [], ['tx_wood.dds'], BOTH)
        self.assertEqual(layer_view.gaps(layer_view.reads(), rows, self.data, BOTH), [])


class GameDataDigestTest(unittest.TestCase):
    """pass_cache.game_data_digest: the base game alone keeps the lock digest; selected layers are in it."""

    def test_selection_in_the_identity(self):
        import pass_cache
        from known_inputs import LOCK_ENV, LOCK_SCHEMA
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / 'lock.json'
            lock.write_text(json.dumps({'schema': LOCK_SCHEMA, 'files': {'/d/Morrowind.esm': {'sha256': 'a' * 64},
                                                                         '/d/Tribunal.esm': {'sha256': 'b' * 64}}}))
            with mock.patch.dict(os.environ, {LOCK_ENV: str(lock), 'AMIWIND_MASTERS': 'Morrowind.esm'}):
                base = pass_cache.game_data_digest()
                self.assertEqual(base, pass_cache.game_data_digest(layers=False))
            with mock.patch.dict(os.environ, {LOCK_ENV: str(lock), 'AMIWIND_MASTERS': 'Morrowind.esm,Tribunal.esm'}):
                self.assertNotEqual(pass_cache.game_data_digest(), base)
                self.assertEqual(pass_cache.game_data_digest(layers=False), base)


class ResidentReadsTest(unittest.TestCase):
    """The resident bake's reads of the game data outside its resolved appearance and greeting are the ones
    prepare_area.resident_reads names: every master_path call of build_resident's reach is in a known function."""

    # _guard_torch: guard_sources (its NPC record, the lights, the torch); _skeletal_resident and _bake_resident:
    # soun_records (the footstep sounds); prepare_gallery.catalogue: the gallery's cast list, in the static reach
    # through that module, never called by a resident bake
    KNOWN = {('tools/prepare_area.py', '_guard_torch'), ('tools/prepare_area.py', '_skeletal_resident'),
             ('tools/prepare_area.py', '_bake_resident'), ('tools/prepare_gallery.py', 'catalogue')}

    def master_reads(self, script, functions):
        from build_cache import SourceIndex
        import pass_cache
        index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        found = set()
        for function in functions:
            python, _, _, units = index.entry_units(ROOT / script, function)
            for path in sorted(python):
                if not path.startswith('tools/') or path not in units:
                    continue
                tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in units[path]:
                        for call in ast.walk(node):
                            if isinstance(call, ast.Call) and getattr(call.func, 'id', getattr(call.func, 'attr', '')) \
                                    in ('master_path', 'master_bytes'):
                                found.add((path, node.name))
        return found

    def test_room_actor_fits_read_no_game_data(self):
        # room_actor_bake keys its fits on the input lock alone: their reach reads neither content-keyed reader
        from build_cache import CONTENT_KEYED_READERS, SourceIndex
        import pass_cache
        index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        for script, function in (('tools/room_actor_bake.py', '_fit_head'), ('tools/room_actor_bake.py', '_fit_search'),
                                 ('tools/actor_grounding.py', 'finish')):
            python, data, uncertain, _ = index.entry_units(ROOT / script, function)
            self.assertFalse(uncertain, function)
            self.assertEqual(set(CONTENT_KEYED_READERS) & (set(python) | set(data)), set(), function)

    def test_master_reads_of_the_npc_library_bake(self):
        # npc_library.build keys the footstep sounds (soun_records) beside each appearance in the unit's inputs
        known = {('tools/npc_library.py', '_bake_standing'), ('tools/npc_library.py', '_skeletal_standing'),
                 ('tools/prepare_gallery.py', 'catalogue')}
        found = self.master_reads('tools/npc_library.py', ('bake_standing',))
        self.assertEqual(found - known, set(), 'a new master read in the NPC library bake: key what it reads in '
                                               'npc_library.build, then add it here')
        text = (ROOT / 'tools/npc_library.py').read_text(encoding='utf-8')
        self.assertEqual(text.count('_assets[key] = '), text.count(
            "_assets[key] = Assets(data, layered_bsa(data))"))

    def test_master_reads_of_the_resident_bake(self):
        from build_cache import SourceIndex
        import pass_cache
        index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        found = set()
        for function in ('build_resident', 'publish_resident'):
            python, _, _, units = index.entry_units(ROOT / 'tools/prepare_area.py', function)
            for path in sorted(python):
                if not path.startswith('tools/') or path not in units:
                    continue
                tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in units[path]:
                        for call in ast.walk(node):
                            if isinstance(call, ast.Call) and getattr(call.func, 'id', getattr(call.func, 'attr', '')) \
                                    in ('master_path', 'master_bytes'):
                                found.add((path, node.name))
        self.assertEqual(found - self.KNOWN, set(), 'a new master read in the resident bake: name what it reads in '
                                                    'prepare_area.resident_reads, then add it here')

    def test_the_resident_bake_reads_the_layered_archives(self):
        # the bake's assets are the selected masters' archives (mwad.archives.layered_bsa: the plain base archive for
        # the base game alone) and the loose files; a layer's replaced file it reads that resident_reads does not
        # name is caught by layer_view.gaps (not stored)
        text = (ROOT / 'tools/prepare_area.py').read_text(encoding='utf-8')
        self.assertIn("_resident_assets[key]=Assets(data,layered_bsa(data))", text)
        self.assertEqual(text.count('_resident_assets[key]='), text.count(
            "_resident_assets[key]=Assets(data,layered_bsa(data))"))


if __name__ == '__main__':
    unittest.main()
