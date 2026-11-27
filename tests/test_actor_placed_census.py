# SPDX-License-Identifier: GPL-3.0-only
"""The placed actor census (tools/actor_placed_census.py, ACTOR-CHECKS-MISS-PLACED-MODELS-69): every actor row of
every map, .chim maps too, judged on the model it stands in; and the record audit judging the placed model."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import actor_placed_census as APC  # noqa: E402

FULL = 'idle:0:21:0.1270 walk:1102:8:0.1333:48.14 run:1164:7:0.1333:52.93 hit:689:8:0.1250 death:735:14:0.1282 ' \
       'attack:2340:8:0.1253:0.714 @walk:1:right ~right:aw/fx/a.wav:aw/fx/b.wav:aw/fx/c.wav !attack:abcd:rg90\n'


def _map(entities):
    """A minimal map file whose lump 0 is the entity text (the layout a BSP29 and a .chim frame map share)."""
    text = entities.encode('cp1252') + b'\0'
    return struct.pack('<iii', 29, 124, len(text)) + b'\0' * (124 - 12) + text


def _row(**fields):
    return '{\n' + '\n'.join('"%s" "%s"' % kv for kv in fields.items()) + '\n}\n'


def _image(tmp):
    """An image with one opening person in a .chim frame, one in a .bsp room with the role the engine clears, one
    resident on the shared model, one body and one model without a layout."""
    id1 = Path(tmp) / 'image' / 'boot' / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    (id1 / 'progs').mkdir()
    world = _row(classname='worldspawn')
    (id1 / 'maps/seyda-chim.chim').write_bytes(_map(world + _row(
        classname='aw_npc', model='progs/np_dock.mdl', netname='Guard', aw_source_id='chargen dock guard',
        aw_ref='172852', aw_intro_role='5') + _row(
        classname='aw_npc', model='progs/a_70b3ebc9daa8.mdl', netname='Fargoth', aw_source_id='fargoth',
        aw_ref='128964') + _row(
        classname='aw_corpse', model='progs/a_dead.mdl', netname='Processus Vitellius',
        aw_source_id='processus vitellius', aw_ref='288981')))
    (id1 / 'maps/census.bsp').write_bytes(_map(world + _row(
        classname='aw_npc', model='progs/np_hall.mdl', netname='Ganciele Douar', aw_source_id='chargen door guard',
        aw_ref='172857', aw_intro_role='8') + _row(
        classname='aw_npc', model='progs/a_idleonly.mdl', netname='Vivec', aw_source_id='vivec_god', aw_ref='405515')))
    for name in ('np_dock', 'np_hall', 'n_aaaa', 'n_bbbb', 'a_70b3ebc9daa8', 'a_dead', 'a_idleonly', 'fargoth'):
        (id1 / ('progs/%s.mdl' % name)).write_bytes(b'mdl')
    (id1 / 'progs/np_dock.anm').write_text('idle:0:8:0.1500 walk:13:8:0.1250 >progs/n_aaaa.mdl\n', encoding='ascii')
    (id1 / 'progs/np_hall.anm').write_text('idle:0:8:0.1500 walk:13:8:0.1250 >progs/n_bbbb.mdl\n', encoding='ascii')
    for key in ('n_aaaa', 'n_bbbb', 'a_70b3ebc9daa8'):
        (id1 / ('progs/%s.anm' % key)).write_text(FULL, encoding='ascii')
    (id1 / 'progs/n_aaaa.tag').write_text('AWTS1 2932\nweapon items/wed2c14f9ae68.mdl\nshield -\nbones 18 9\n',
                                          encoding='ascii')
    (id1 / 'progs/n_bbbb.tag').write_text('AWTS1 2932\nweapon -\nshield -\nbones 18 9\n', encoding='ascii')
    return id1


class PlacedCensusTests(unittest.TestCase):
    def test_rows_of_every_map_kind_and_the_standing_models_own_facts(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-placed-') as tmp:
            id1 = _image(tmp)
            rows = APC.rows(id1)
            self.assertEqual(len(rows), 5)                      # the .chim frame's three rows are read too
            by = {r['record']: r for r in rows}
            dock = by['chargen dock guard']
            self.assertEqual(dock['map'], 'seyda-chim.chim')
            self.assertEqual(dock['own_groups'], ['idle', 'walk'])          # not the fight model's groups
            self.assertIn('attack', dock['fight_groups'])
            self.assertEqual(dock['fight_model'], 'progs/n_aaaa.mdl')
            self.assertIsNone(dock['tag'])
            self.assertEqual(dock['fight_tag']['weapon'], 'items/wed2c14f9ae68.mdl')
            self.assertEqual(dock['findings'], [APC.ROLE, APC.FIGHT_ONLY, APC.NO_TAG])
            # role 8 is cleared by the engine at the spawn; this fight model carries nothing, so no tag finding
            self.assertEqual(by['chargen door guard']['findings'], [APC.FIGHT_ONLY])
            # a resident on the shared model, and a body, have no finding
            self.assertEqual(by['fargoth']['findings'], [])
            self.assertTrue(by['fargoth']['voice_lines'] and by['fargoth']['footsteps'])
            self.assertEqual(by['processus vitellius']['findings'], [])
            self.assertEqual(by['vivec_god']['findings'], [APC.NO_LAYOUT])

    def test_the_allowed_counts_stop_the_image(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-placed-') as tmp:
            id1 = _image(tmp)
            doc = APC.document(APC.rows(id1))
            self.assertEqual(doc['findings'], {APC.ROLE: 1, APC.FIGHT_ONLY: 2, APC.NO_TAG: 1, APC.NO_LAYOUT: 1})
            self.assertEqual((doc['actors'], doc['bodies'], doc['maps_with_actors']), (4, 1, 2))
            allow = {APC.ROLE: {'rows': 1, 'register': 'X-1'}, APC.FIGHT_ONLY: {'rows': 2, 'register': 'X-2'},
                     APC.NO_TAG: {'rows': 1, 'register': 'X-2'}, APC.NO_LAYOUT: {'rows': 1, 'by_design': 'docs/A.md'}}
            self.assertEqual(APC.failures(doc, allow), [])
            allow[APC.FIGHT_ONLY]['rows'] = 1                   # one row more than allowed
            bad = APC.failures(doc, allow)
            self.assertEqual(len(bad), 1)
            self.assertIn('2 row(s), 1 allowed (X-2)', bad[0])
            del allow[APC.ROLE]                                 # a kind the file does not name
            self.assertEqual(len(APC.failures(doc, allow)), 2)
            allow[APC.ROLE] = {'rows': 1}                       # allowed, but tracked nowhere
            self.assertTrue(any('without a register entry' in line for line in APC.failures(doc, allow)))
            # the stage writes the table and stops
            path = Path(tmp) / 'allow.json'
            path.write_text(json.dumps({'allow': allow}), encoding='utf-8')
            with self.assertRaises(ValueError):
                APC.stage(id1, Path(tmp) / 'image', allow=path)
            self.assertTrue((Path(tmp) / 'image' / APC.REPORT).is_file())

    def test_the_shipped_allow_file_names_every_kind_with_its_tracking(self):
        allow = APC.read_allow()
        self.assertEqual(sorted(allow), sorted(APC.KINDS))
        for kind, row in allow.items():
            self.assertTrue(row.get('register') or row.get('by_design'), kind)
            self.assertGreaterEqual(int(row['rows']), 0)
            if 'parts' in row:                                  # a count of several causes says how it adds up
                self.assertEqual(sum(row['parts'].values()), row['rows'], kind)
            if row.get('register'):
                self.assertTrue((ROOT / 'docs' / 'bugs' / (row['register'] + '.md')).is_file(), row['register'])
            else:
                self.assertTrue((ROOT / row['by_design']).is_file(), row['by_design'])

    def test_the_coverage_table_alone_misses_the_chim_rows(self):
        """The fault this census answers: the coverage table reads the .bsp maps only."""
        import actor_library as AL
        with tempfile.TemporaryDirectory(prefix='amiwind-placed-') as tmp:
            id1 = _image(tmp)
            self.assertEqual({r['map'] for r in AL.coverage_rows(id1)}, {'census.bsp'})
            self.assertEqual({r['map'] for r in APC.rows(id1)}, {'census.bsp', 'seyda-chim.chim'})


class AuditPlacedModelTests(unittest.TestCase):
    """The record audit judges the model a record is placed with, not the first one a stage report names."""

    def _run(self, tmp, with_census):
        id1 = _image(tmp)
        run = Path(tmp)
        # an early stage's leftover report names a prototype model without a layout; it sorts before the area stage's
        (run / 'hands-scene').mkdir()
        (run / 'hands-scene/npc-report.json').write_text(json.dumps({'models': {
            'fargoth': {'appearance': {'id': 'fargoth'}, 'model': 'progs/fargoth.mdl'}}}), encoding='utf-8')
        (run / 'intro-scene').mkdir()
        (run / 'intro-scene/area-report.json').write_text(json.dumps({'models': {
            'fargoth': {'appearance': {'id': 'fargoth'}, 'model': 'progs/a_70b3ebc9daa8.mdl'}}}), encoding='utf-8')
        (run / 'actor-library').mkdir()
        (run / 'actor-library/npc-library.json').write_text(json.dumps({
            'npcs': {'chargen dock guard': {'key': 'aaaa', 'dead': False}},
            'models': {'aaaa': {'model': 'progs/n_aaaa.mdl'}}}), encoding='utf-8')
        if with_census:
            APC.stage(id1, run / 'image', allow=self._allow(tmp))
        import actor_record_audit as ARA
        return ARA.read_anim_build(run)

    def _allow(self, tmp):
        path = Path(tmp) / 'allow.json'
        path.write_text(json.dumps({'allow': {k: {'rows': 9, 'register': 'X'} for k in APC.KINDS}}), encoding='utf-8')
        return path

    def test_fargoth_is_judged_on_his_placed_model(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-audit-') as tmp:
            anim = self._run(tmp, with_census=True)
            self.assertEqual(anim['fargoth'][0], 'room resident')
            # the dock guard stands in his opening model: judged as that, not as a library actor
            self.assertEqual(anim['chargen dock guard'][0], 'opening standing model + full kit')

    def test_without_the_table_the_reports_count_as_before(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-audit-') as tmp:
            anim = self._run(tmp, with_census=False)
            self.assertEqual(anim['fargoth'][0], 'room resident (no layout: idle only)')
            self.assertEqual(anim['chargen dock guard'][0], 'NPC library')


if __name__ == '__main__':
    unittest.main()
