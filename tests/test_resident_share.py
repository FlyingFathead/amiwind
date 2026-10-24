# SPDX-License-Identifier: GPL-3.0-only
"""Shared resident files of the batch rooms (tools/resident_share.py, ROOM-RESIDENT-MODELS-SIZE-48)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import resident_share  # noqa: E402
from player_hull import lumps, pack_lumps  # noqa: E402


def write(id1, rel, raw):
    path = Path(id1) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if isinstance(raw, bytes) else raw.encode('ascii'))


def kit(id1, stem, model=b'MODEL', mover=b'MOVER', layout='idle 0 8', tag='TAG 1', voice=b'VOICE'):
    """A kit resident's files and record, as prepare_area.populate leaves them."""
    write(id1, 'progs/%s.mdl' % stem, model)
    write(id1, 'progs/%s_m.mdl' % stem, mover)
    write(id1, 'progs/%s.anm' % stem, '%s >progs/%s_m.mdl\n' % (layout, stem))
    write(id1, 'progs/%s_m.anm' % stem, 'walk 0 16\n')
    write(id1, 'progs/%s.tag' % stem, tag)
    write(id1, 'progs/%s_m.tag' % stem, tag + ' mover')
    record = {'model': 'progs/%s.mdl' % stem, 'voice': '', 'anim': {'mover': {'model': 'progs/%s_m.mdl' % stem}}}
    if voice is not None:
        write(id1, 'sound/npc/%s.wav' % stem, voice)
        record['voice'] = 'npc/%s.wav' % stem
    return record


def room_map(path, entities):
    parts = [bytearray() for _ in range(15)]
    parts[0] = bytearray(('\n'.join(entities) + '\n\0').encode('cp1252'))
    parts[1] = bytearray(b'planes')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(pack_lumps(parts))


class ResidentShareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.id1 = Path(self.tmp.name) / 'id1'

    def tearDown(self):
        self.tmp.cleanup()

    def residents(self):
        return {'a npc': kit(self.id1, 'a_aaa'),
                'b npc': kit(self.id1, 'a_bbb'),                        # the same set as a npc: shared
                'c npc': kit(self.id1, 'a_ccc', layout='idle 0 9'),     # another layout: its own model set
                'd npc': kit(self.id1, 'a_ddd', voice=b'OTHER'),        # same set, another greeting
                'e npc': dict(kit(self.id1, 'a_eee'), lod_levels={'1': 'progs/a_eee.mdl'})}  # npc_lod: left alone

    def test_identical_sets_are_written_once(self):
        models = self.residents()
        record = resident_share.share(self.id1, models)
        self.assertEqual(models['b npc']['model'], 'progs/a_aaa.mdl')
        self.assertEqual(models['b npc']['anim']['mover']['model'], 'progs/a_aaa_m.mdl')
        self.assertEqual(models['b npc']['shared_model'], 'a npc')
        self.assertEqual(models['d npc']['model'], 'progs/a_aaa.mdl')
        self.assertEqual(models['c npc']['model'], 'progs/a_ccc.mdl')
        self.assertEqual(models['e npc']['model'], 'progs/a_eee.mdl')
        for stem in ('a_bbb', 'a_ddd'):
            self.assertEqual(sorted(p.name for p in (self.id1 / 'progs').glob(stem + '*')), [])
        for stem in ('a_aaa', 'a_ccc', 'a_eee'):
            self.assertEqual(len(list((self.id1 / 'progs').glob(stem + '*'))), 6)
        # the kept layout still names its own mover
        self.assertIn('>progs/a_aaa_m.mdl', (self.id1 / 'progs/a_aaa.anm').read_text())
        self.assertEqual(record['models'], {'residents': 5, 'sets': 2, 'shared': 2, 'files_removed': 12,
                                            'bytes_removed': record['models']['bytes_removed'], 'left_alone': 1})
        # greetings: a, b, c and e say VOICE (one kept), d says OTHER (kept)
        self.assertEqual(models['b npc']['voice'], 'npc/a_aaa.wav')
        self.assertEqual(models['d npc']['voice'], 'npc/a_ddd.wav')
        self.assertEqual(models['e npc']['voice'], 'npc/a_aaa.wav')
        self.assertEqual(record['voices']['kept'], 2)
        self.assertEqual(record['voices']['files_removed'], 3)
        self.assertEqual(sorted(p.name for p in (self.id1 / 'sound/npc').iterdir()), ['a_aaa.wav', 'a_ddd.wav'])

    def test_per_resident_keeps_every_copy(self):
        models = self.residents()
        before = json.dumps(models, sort_keys=True)
        files = sorted(p for p in self.id1.rglob('*') if p.is_file())
        record = resident_share.share(self.id1, models, 'per-resident')
        self.assertEqual(record['paths'], {})
        self.assertEqual(json.dumps(models, sort_keys=True), before)
        self.assertEqual(sorted(p for p in self.id1.rglob('*') if p.is_file()), files)
        with self.assertRaises(ValueError):
            resident_share.share(self.id1, models, 'sometimes')

    def test_a_different_file_anywhere_in_the_set_keeps_it_apart(self):
        models = {'a': kit(self.id1, 'a_aaa'), 'b': kit(self.id1, 'a_bbb', tag='TAG 2'),
                  'c': kit(self.id1, 'a_ccc', mover=b'MOVER2'), 'd': kit(self.id1, 'a_ddd', model=b'MODEL2')}
        record = resident_share.share(self.id1, models)
        self.assertEqual(record['models']['shared'], 0)
        self.assertEqual([models[k]['model'] for k in 'abcd'],
                         ['progs/a_aaa.mdl', 'progs/a_bbb.mdl', 'progs/a_ccc.mdl', 'progs/a_ddd.mdl'])

    def test_creatures_and_corpses_share_by_their_model_alone(self):
        write(self.id1, 'progs/a_c1.mdl', b'CREATURE')
        write(self.id1, 'progs/a_c2.mdl', b'CREATURE')
        models = {'rat 1': {'model': 'progs/a_c1.mdl', 'voice': ''}, 'rat 2': {'model': 'progs/a_c2.mdl', 'voice': ''}}
        resident_share.share(self.id1, models)
        self.assertEqual(models['rat 2']['model'], 'progs/a_c1.mdl')
        self.assertFalse((self.id1 / 'progs/a_c2.mdl').exists())

    def test_room_maps_and_report_point_at_the_kept_files(self):
        models = self.residents()
        maps = self.id1 / 'maps'
        room_map(maps / 'room1.bsp', ['{\n"classname" "worldspawn"\n}',
                                      '{\n"classname" "aw_npc"\n"model" "progs/a_bbb.mdl"\n"aw_voice" "npc/a_bbb.wav"\n}',
                                      '{\n"classname" "aw_npc"\n"model" "progs/a_ccc.mdl"\n"aw_voice" "npc/a_ccc.wav"\n}'])
        room_map(maps / 'room2.bsp', ['{\n"classname" "worldspawn"\n}',
                                      '{\n"classname" "aw_npc"\n"model" "progs/a_aaa.mdl"\n"aw_voice" "npc/a_aaa.wav"\n}'])
        untouched = (maps / 'room2.bsp').read_bytes()
        record = resident_share.share(self.id1, models)
        changed = resident_share.rewrite_maps(maps, ['room1', 'room2', 'gone'], record['paths'])
        self.assertEqual(changed, {'room1': 3})
        parts = lumps((maps / 'room1.bsp').read_bytes())
        text = bytes(parts[0]).decode('cp1252')
        self.assertIn('"model" "progs/a_aaa.mdl"\n"aw_voice" "npc/a_aaa.wav"', text)
        self.assertIn('"model" "progs/a_ccc.mdl"\n"aw_voice" "npc/a_aaa.wav"', text)
        self.assertNotIn('a_bbb', text)
        self.assertTrue(text.endswith('\0'))
        self.assertEqual(bytes(parts[1]), b'planes')
        self.assertEqual((maps / 'room2.bsp').read_bytes(), untouched)
        report = {'models': models, 'cast': []}
        resident_share.rewrite_report(self.id1 / 'r.json', report)
        self.assertEqual(json.loads((self.id1 / 'r.json').read_text())['models']['b npc']['model'], 'progs/a_aaa.mdl')

    def test_every_placed_path_exists_after_sharing(self):
        models = self.residents()
        resident_share.share(self.id1, models)
        for record in models.values():
            paths, _ = resident_share.model_files(record)
            self.assertTrue((self.id1 / paths[0]).is_file(), paths[0])
            self.assertTrue((self.id1 / paths[3]).is_file(), paths[3])
            self.assertTrue((self.id1 / 'sound' / record['voice']).is_file(), record['voice'])


class ResidentShareKeyTests(unittest.TestCase):
    """The stage key reaches the sharing code; the resident bake key (prepare_area.py's reach) does not, so the
    1,769 resident bakes are reused (BUILD-STAGE-KEY-WHOLE-CLASS-48)."""

    @classmethod
    def setUpClass(cls):
        import build_cache
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def covered(self, script):
        python, data, _ = self.index.closure(ROOT / 'tools' / script)
        return set(python) | set(data)

    def test_the_room_batches_stage_key_covers_resident_share(self):
        self.assertIn('tools/resident_share.py', self.covered('chim_room_batches.py'))

    def test_the_resident_bake_key_does_not(self):
        self.assertNotIn('tools/resident_share.py', self.covered('prepare_area.py'))


if __name__ == '__main__':
    unittest.main()
