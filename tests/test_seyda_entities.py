"""Seyda Neen's scene entity list (BUILD-SEYDA-ENTITY-BUS-48).

The scene stages read Seyda Neen's entities from SCENE/seyda-entities.json, which each writing stage publishes,
instead of the seyda.bsp carrier's entity lump; chim-town-seyda reads no .bsp. The legacy read path stays behind
--seyda-entities bsp (AMIWIND_SEYDA_ENTITIES=bsp), and both paths give the same bytes: checked here on a source-only
carrier scene (the bsp stage's own code, as tests/test_seyda_scene_carrier.py makes it) through the writers that run
without game data (intro rows, hand stamp, opening references) and the chim-town reader. No original assets,
compiler or emulator."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import chim_town
import hand_metadata
import prepare_intro as intro
import prepare_opening_refs as opening
import seyda_entities
import test_seyda_scene_carrier as scene_tests
from player_hull import lumps, pack_lumps
from test_seyda_source_carrier import BARREL

LEGACY = {seyda_entities.ENV: 'bsp'}
FIELDS = {'aw_eye_height': '40.5', '_aw_note': 'x'}   # the hand clips are the image's (FIRST-PERSON-HANDS-IN-C-54)
ROW = '{\n"classname" "aw_npc"\n"aw_ref" "990001"\n"origin" "1 2 3"\n}'


def carrier_scene(root):
    """A source-only carrier scene made by the bsp stage's code (prepare_mesh_bsp.prepare_carrier)."""
    maker = scene_tests.CarrierSceneTests('test_widened_cell_aligned_frame_is_the_shipped_seyda_area')
    out, _, index = maker.carrier(Path(root))
    return out, index


def tree(folder):
    """{relative path: bytes} of every file under FOLDER."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}


def bind_opening(scene, index):
    barrel = next(r for r in index['references'] if r['number'] == BARREL)
    moved = dict(barrel, position=[barrel['position'][0] + 400, *barrel['position'][1:]])
    with patch('mwad.paths.unshare_tree'), patch.object(opening, 'resolve_data_files', side_effect=Path), \
            patch.object(opening, 'opening_references', return_value=([], [moved], set())), \
            patch.object(opening, 'append_meshes', side_effect=AssertionError('append refused')):
        return opening.prepare(Path(scene).parent / 'data', scene)


class EntityListTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.scene, self.index = carrier_scene(self.root)
        self.raw = (self.scene / 'id1/maps/seyda.bsp').read_bytes()

    def tearDown(self):
        self._tmp.cleanup()

    def copy(self, name):
        target = self.root / name / 'scene'
        target.parent.mkdir()
        shutil.copytree(self.scene, target)
        return target

    def test_the_bsp_stage_publishes_the_list_of_its_map(self):
        record = seyda_entities.read(self.scene)
        parts = lumps(self.raw)
        self.assertEqual(record['format'], seyda_entities.FORMAT)
        self.assertEqual(record['bsp_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(seyda_entities.entity_lump(record), bytes(parts[0]))
        self.assertEqual(seyda_entities.models(record), list(struct.iter_unpack('<9f7i', parts[14])))
        self.assertEqual(record['lump_sizes'], [len(p) for p in parts])
        self.assertGreater(len(record['models']), 1)

    def test_writer_lump_is_the_maps_lump_in_both_modes(self):
        self.assertEqual(seyda_entities.writer_lump(self.scene, self.raw), bytes(lumps(self.raw)[0]))
        with patch.dict(os.environ, LEGACY):
            self.assertEqual(seyda_entities.mode(), 'bsp')
            self.assertEqual(bytes(seyda_entities.writer_lump(self.scene, self.raw)), bytes(lumps(self.raw)[0]))

    def test_a_list_of_another_map_or_no_list_is_refused(self):
        parts = lumps(self.raw)
        parts[0] = bytes(parts[0]).replace(b'"classname" "worldspawn"', b'"classname" "worldspawn"\n"x" "1"', 1)
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            seyda_entities.writer_lump(self.scene, pack_lumps(parts))
        (self.scene / seyda_entities.NAME).unlink()
        with self.assertRaisesRegex(ValueError, 'no Seyda Neen entity list'):
            seyda_entities.writer_lump(self.scene, self.raw)
        with patch.dict(os.environ, LEGACY):     # the legacy read path needs no list
            self.assertEqual(bytes(seyda_entities.writer_lump(self.scene, self.raw)), bytes(lumps(self.raw)[0]))
        with patch.dict(os.environ, {seyda_entities.ENV: 'lump'}), self.assertRaisesRegex(ValueError, 'takes'):
            seyda_entities.mode()

    def test_hand_stamp_from_the_list_is_the_legacy_stamp(self):
        lump = seyda_entities.writer_lump(self.scene, self.raw)
        self.assertEqual(hand_metadata.stamp_lump(self.raw, lump, FIELDS), hand_metadata.stamp(self.raw, FIELDS))
        stamped = hand_metadata.stamp(self.raw, FIELDS)
        self.assertNotEqual(stamped, self.raw)
        # unchanged: the map's own bytes
        self.assertIs(hand_metadata.stamp_lump(stamped, lumps(stamped)[0], FIELDS), stamped)

    def test_writers_give_the_legacy_bytes(self):
        """intro rows, then opening references, on two copies: the list path and the legacy path write the same
        files (maps, the list, the reports)."""
        results = {}
        for mode in ('list', 'bsp'):
            scene = self.copy(mode)
            with patch.dict(os.environ, {seyda_entities.ENV: mode}):
                intro.append_intro_rows(scene, {'seyda': [ROW]})
                bound = bind_opening(scene, self.index)
            self.assertEqual(bound['bound'], [BARREL])
            results[mode] = tree(scene)
        self.assertEqual(results['list'], results['bsp'])
        files = results['list']
        self.assertEqual(files['id1/maps/seyda.bsp'], files['seyda.bsp'])
        record = json.loads(files[seyda_entities.NAME])
        self.assertEqual(record['bsp_sha256'], hashlib.sha256(files['id1/maps/seyda.bsp']).hexdigest())
        self.assertIn('"aw_ref" "990001"', record['entities'])
        self.assertEqual(seyda_entities.entity_lump(record), bytes(lumps(files['seyda.bsp'])[0]))

    def test_chim_town_reads_the_list_with_the_legacy_result(self):
        intro.append_intro_rows(self.scene, {'seyda': [ROW]})
        raw = (self.scene / 'id1/maps/seyda.bsp').read_bytes()
        lump, models, sizes, sha = seyda_entities.source(self.scene)
        with patch.dict(os.environ, LEGACY):
            self.assertEqual(seyda_entities.source(self.scene), (lump, models, sizes, sha))
        self.assertEqual(sha, hashlib.sha256(raw).hexdigest())
        self.assertEqual(chim_town.seyda_maps_from(lump, models), chim_town.seyda_maps(raw))
        self.assertEqual(chim_town.source_carrier_check(self.scene, lump, sizes, sha),
                         chim_town.source_carrier_record(self.scene, raw))
        # chim-town-seyda reads no .bsp on the list path: the maps may be gone
        (self.scene / 'id1/maps/seyda.bsp').unlink()
        (self.scene / 'seyda.bsp').unlink()
        self.assertEqual(seyda_entities.source(self.scene)[3], sha)


class WiringTests(unittest.TestCase):
    """The writers that need game data (npcs, area) and the reader take the entities from the list."""

    def source(self, name):
        return (ROOT / 'tools' / name).read_text(encoding='utf-8')

    def test_every_writer_reads_and_publishes_the_list(self):
        for name in ('prepare_npcs.py', 'prepare_hands.py', 'prepare_intro.py', 'prepare_area.py',
                     'prepare_opening_refs.py'):
            text = self.source(name)
            self.assertIn('writer_lump(', text, name)
            self.assertIn('publish_entities(', text, name)
        for name in ('prepare_mesh_bsp.py', 'prepare_seyda_carrier.py'):
            self.assertIn('publish_entities(', self.source(name), name)

    def test_chim_town_seyda_reads_the_list_by_default(self):
        text = self.source('chim_town.py')
        self.assertIn('seyda_entities.source(scene)', text)
        self.assertIn("seyda_entities.mode() == 'bsp'", text)

    def test_build_exports_the_mode_and_the_keys_name_it(self):
        text = self.source('build.py')
        self.assertIn('seyda_entities.add_option(p)', text)
        self.assertIn('export_seyda_entities(', text)
        import build_cache
        index = build_cache.SourceIndex()
        for script in ('prepare_npcs.py', 'prepare_hands.py', 'prepare_intro.py', 'prepare_area.py',
                       'prepare_opening_refs.py', 'chim_town.py'):
            self.assertIn(seyda_entities.ENV, index.environment_names(ROOT / 'tools' / script), script)
        for script in ('prepare_mesh_bsp.py', 'chim_town.py', 'prepare_opening_refs.py'):
            python, _, _ = index.closure(ROOT / 'tools' / script)
            self.assertIn('tools/seyda_entities.py', python, script)

    def test_export_mode_removes_the_default(self):
        with patch.dict(os.environ, {seyda_entities.ENV: 'bsp'}):
            self.assertEqual(seyda_entities.export_mode('list'), 'list')
            self.assertNotIn(seyda_entities.ENV, os.environ)
            seyda_entities.export_mode('bsp')
            self.assertEqual(os.environ[seyda_entities.ENV], 'bsp')
            with self.assertRaises(ValueError):
                seyda_entities.export_mode('lump')


if __name__ == '__main__':
    unittest.main()
