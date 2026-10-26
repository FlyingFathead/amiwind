# SPDX-License-Identifier: GPL-3.0-only
"""The actor library (EXPERIMENTAL, --chim-actor-table on only): its stage in the build plan, the image option, the
stage order, the NPC standing library's keys and base texts, the installation into an image with the actor table's
base texts, and the engine's live-entity scale (U_AW_EXT, AWU_SCALE) in the protocol (CHIM-EXTERIOR-ACTORS-MISSING-46).

Checked: with the option off (the default) the plan has no actor-library stage and the image no --actor-library
option (the default stage list is unchanged); with it on the stage runs after the census and the CHIM towns and
the image waits for it; an appearance key changes with what the bake reads and not with the record's name; a base
text holds the resident row's fields without per-placement ones; install copies the files and gives NPC and creature
texts; the table gives an NPC without a built row its library text and flags a reference whose base names a model
baked at its scale; the server writes the scale after the angles exactly when the bit is set and the client reads
it at the same place. Synthetic data only.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'


def steps(*extra):
    import build
    from test_build_defaults import TOOLS, RUN
    args = build.parser().parse_args(list(extra))
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    with patch('build_jobs.auto_jobs', return_value=4):
        return build.commands(args, TOOLS, RUN)


class StageTests(unittest.TestCase):
    def test_on_by_default_off_selectable(self):
        # on by default since v0.0.47 (decided for the project, 2026-10-21)
        self.assertEqual(steps(), steps('--chim-actor-table', 'on'))
        # the region actors (on by default since v0.0.48-dev2) name the same models: the stage stays for them
        self.assertIn('actor-library', [n for n, _ in steps('--chim-actor-table', 'off')])
        plan = steps('--chim-actor-table', 'off', '--chim-region-actors', 'off')
        self.assertNotIn('actor-library', [n for n, _ in plan])
        self.assertNotIn('--actor-library', [str(x) for x in dict(plan)['image']])

    def test_on_adds_the_stage(self):
        from build_parallel import stage_dependencies
        plan = steps('--chim-actor-table', 'on')
        names = [n for n, _ in plan]
        self.assertIn('actor-library', names)
        self.assertLess(names.index('actor-library'), names.index('image'))
        self.assertIn('--actor-library', [str(x) for x in dict(plan)['image']])
        deps = stage_dependencies(plan)
        self.assertIn('census', deps['actor-library'])
        self.assertTrue(all(d == 'census' or d.startswith('chim-town-') for d in deps['actor-library']))
        self.assertIn('actor-library', deps['image'])
        # the other stages' commands are those of the default plan
        default = dict(steps())
        for name, command in plan:
            if name not in ('actor-library', 'image'):
                self.assertEqual([str(x) for x in command], [str(x) for x in default[name]], name)


class NpcLibraryTests(unittest.TestCase):
    APP = {'id': 'a', 'parts': [{'slot': 0, 'mesh': 'b/head.nif'}], 'skeleton': 'meshes/base_anim.nif',
           'height': 1.0, 'weight': 1.0, 'female': False, 'initially_dead': False, 'foot': 'bare'}

    def test_appearance_key(self):
        import npc_library as NL
        key = NL.appearance_key(self.APP, 'react')
        self.assertEqual(key, NL.appearance_key(dict(self.APP, id='other', foot='heavy'), 'react'))
        self.assertNotEqual(key, NL.appearance_key(dict(self.APP, height=1.1), 'react'))
        self.assertNotEqual(key, NL.appearance_key(dict(self.APP, initially_dead=True), 'react'))
        self.assertNotEqual(key, NL.appearance_key(self.APP, 'idle'))
        self.assertEqual(NL.model_path(key), 'progs/n_%s.mdl' % key)

    def test_base_text(self):
        import npc_library as NL
        text = NL.entity_text('some villager', {'name': 'Some "Villager"', 'dead': False},
                              {'model': 'progs/n_x.mdl', 'step': 0.25})
        import re
        fields = dict(re.findall(r'"([^"]*)" "([^"]*)"', text))
        self.assertEqual(fields['classname'], 'aw_npc')
        self.assertEqual(fields['model'], 'progs/n_x.mdl')
        self.assertEqual(fields['netname'], 'Some Villager')
        for f in ('origin', 'angles', 'aw_ref', 'aw_ground_baked', 'aw_ground_valid'):
            self.assertNotIn('"%s"' % f, text)
        dead = NL.entity_text('x', {'name': 'X', 'dead': True}, {'model': 'm', 'step': 0})
        self.assertIn('"classname" "aw_corpse"', dead)


class InstallTests(unittest.TestCase):
    def test_install_and_table(self):
        import actor_library as AL
        import creature_library as L
        import npc_library as NL
        from chim import actors as A
        from test_chim_levelled import MASTER
        with tempfile.TemporaryDirectory(prefix='amiwind-actor-library-') as tmp:
            lib, id1 = Path(tmp) / 'actor-library', Path(tmp) / 'image-id1'
            (lib / 'id1/progs').mkdir(parents=True)
            (lib / 'id1/progs/c_x.mdl').write_bytes(b'mdl')
            (lib / 'id1/sound/fx').mkdir(parents=True)
            (lib / 'id1/sound/fx/step.wav').write_bytes(b'wav')
            planned = L.plan(MASTER)
            models = {m: {'model': L.variant_path(m), 'step': 0.25} for m in planned['meshes']}
            (lib / 'creature-library.json').write_text(json.dumps(L.manifest(planned, models)), encoding='utf-8')
            npc = {'format': NL.FORMAT, 'profile': 'react', 'models': {'k1': {'model': 'progs/n_k1.mdl', 'step': .3}},
                   'npcs': {'villager': {'key': 'k1', 'name': 'Villager', 'dead': False}}, 'left_out': {}}
            (lib / 'npc-library.json').write_text(json.dumps(npc), encoding='utf-8')
            texts, copied = AL.install(lib, id1)
            self.assertEqual(copied, 2)
            self.assertTrue((id1 / 'progs/c_x.mdl').is_file() and (id1 / 'sound/fx/step.wav').is_file())
            self.assertIn('"model" "progs/n_k1.mdl"', texts['villager'])
            self.assertIn('crab', texts)
            data, rep = A.build_table(A.exterior_actors(MASTER), {}, A.levelled_lists(MASTER), A.creature_ids(MASTER),
                                      texts, {14: 0.8})
            head, cells, records, bases, _ = A.read_table(data)
            villager = next(r for r in records if r['key'] == 13)
            self.assertIn('progs/n_k1.mdl', bases[villager['base']]['text'])
            crab = next(r for r in records if r['key'] == 14)
            self.assertEqual(crab['flags'] & A.FLAG_SCALED_MODEL, 0)      # no baked variant: the engine scales it
            variants = dict(texts, **{'crab@0.8000': '"classname" "aw_npc"\n"model" "progs/c_crab_s080.mdl"\n'})
            data, _ = A.build_table(A.exterior_actors(MASTER), {}, A.levelled_lists(MASTER), A.creature_ids(MASTER),
                                    variants, {14: 0.8})
            head, cells, records, bases, _ = A.read_table(data)
            crab = next(r for r in records if r['key'] == 14)
            self.assertEqual(crab['flags'] & A.FLAG_SCALED_MODEL, A.FLAG_SCALED_MODEL)


class LeftOutTests(unittest.TestCase):
    """ACTOR-LIBRARY-LEFT-OUT-48: the library dropped the authored-dead creatures (no model at all, no reason) and
    the NPC records a CHIM town also places ('hlaalu guard_outside', 'ordinator wander') although they also stand
    outside the towns. Corpses now get the last key of their own death group as a one-frame aw_corpse model; an
    NPC record gets a library model when a reference of it is not in the towns' cast."""

    def master(self):
        from test_chim_levelled import MASTER, cell, ref
        return MASTER + cell('', False, 2, 0, ref(41, 'dead_rat', (2 * 8192.0 + 50.0, 60.0, 0.0)))

    def test_plan_corpses_and_town_npcs(self):
        import actor_library as AL
        import creature_library as L
        master = self.master()
        self.assertEqual(L.plan(master)['corpses'], {'r/rust rat.nif': ['dead_rat']})
        meshes, _, _, npcs, _, corpses = AL.plan(master)
        self.assertEqual(corpses, {'r/rust rat.nif': ['dead_rat']})
        self.assertNotIn('dead_rat', [i for v in meshes.values() for i in v])
        self.assertIn('villager', npcs)
        self.assertNotIn('villager', AL.plan(master, {'villager'})[3])               # the rule before v0.0.48
        self.assertNotIn('villager', AL.plan(master, {'villager'}, {13})[3])         # its only reference: a town's
        self.assertIn('villager', AL.plan(master, {'villager'}, {99})[3])            # a reference outside the towns

    def test_town_cast(self):
        import actor_library as AL
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'chim-town-x').mkdir()
            (Path(tmp) / 'chim-town-x/residents.json').write_text(json.dumps(
                {'models': {'Hlaalu Guard_Outside': {}}, 'cast': [{'number': 428715, 'id': 'hlaalu guard_outside'}]}))
            self.assertEqual(AL.town_cast(tmp), ({'hlaalu guard_outside'}, {428715}))
            self.assertEqual(AL.town_residents(tmp), {'hlaalu guard_outside'})

    def test_corpse_base_text(self):
        import creature_library as L
        planned = L.plan(self.master())
        models = {m: {'model': L.variant_path(m), 'step': 0.25} for m in planned['meshes']}
        models[L.corpse_key('r/rust rat.nif')] = {'model': L.corpse_path('r/rust rat.nif'), 'step': 0.0,
                                                  'corpse': True}
        texts = L.base_texts(L.manifest(planned, models))
        import re
        dead = dict(re.findall(r'"([^"]*)" "([^"]*)"', texts['dead_rat']))
        self.assertEqual(dead['classname'], 'aw_corpse')
        self.assertEqual(dead['model'], L.corpse_path('r/rust rat.nif'))
        self.assertTrue(dead['model'].endswith('_d.mdl'))
        self.assertEqual(dead['aw_ground_mode'], '1')                               # lying at its authored spot
        live = dict(re.findall(r'"([^"]*)" "([^"]*)"', texts['rat']))
        self.assertEqual((live['classname'], live['model']), ('aw_npc', L.variant_path('r/rust rat.nif')))

    def test_corpse_gets_the_death_pose_model(self):
        """bake_kf(corpse=True) on a synthetic creature: one frame, posed at the last key of its death group
        (death1: stop at 2 s, the bone moved 8 units), not its idle; a creature without a death group is refused."""
        import numpy as np
        import creature_library as L
        import creature_pose as P
        from test_creature_pose import FILES, kf, model, reader
        from check_actor_ground import model_frames
        files = dict(FILES)
        files['meshes/r/xbeast.nif'] = model()
        files['meshes/r/xbeast.kf'] = kf(
            [(0.0, 'idle: start'), (1.0, 'idle: stop'), (1.0, 'death1: start'), (2.0, 'death1: stop')],
            [(b'Bone', (1, [(0.0, (0, 0, 0)), (2.0, (8, 0, 0))]))])

        class FakeAssets:
            def __init__(self, files):
                self.read = reader(files)

            def texture(self, name):
                raise KeyError(name)
        from prepare_scenery import nif_reader
        rig = P.CreatureRig(nif_reader(), reader(files), 'r/beast.nif', False)
        samples, groups = rig.plan(P.CORPSE)
        self.assertEqual([(s[0], s[1]) for s in samples], [(0, 2.0)])
        self.assertEqual(groups[0]['name'], 'death')
        palette = bytes(range(256)) * 3
        with tempfile.TemporaryDirectory() as tmp, patch.dict(L._assets, {str(Path(tmp).resolve()): FakeAssets(files)}):
            out = L.bake_kf(tmp, palette, {'id': 'dead beast', 'mesh': 'r/beast.nif'}, False, corpse=True)
            self.assertEqual([(r, p) for r, _, p in out['files']], [('corpse', L.corpse_path('r/beast.nif'))])
            self.assertEqual(out['record']['corpse_frames'], 1)
            frames = np.array(model_frames(out['files'][0][1]))
            self.assertEqual(len(frames), 1)
            # the bone's box (0..8 units) moved 8 by the death stop key: from 2 Quake units (x 0.25), not 0
            self.assertAlmostEqual(float(frames[0][:, 0].min()), 2.0, delta=0.1)
            live = L.bake_kf(tmp, palette, {'id': 'beast', 'mesh': 'r/beast.nif'}, False)
            self.assertNotEqual(out['files'][0][1], live['files'][0][1])
            idle_only = dict(files, **{'meshes/r/xbeast.kf': kf([(0.0, 'idle: start'), (1.0, 'idle: stop')],
                                                              [(b'Bone', (1, [(0.0, (0, 0, 0)), (1.0, (0, 0, 0))]))])})
            L._assets[str(Path(tmp).resolve())] = FakeAssets(idle_only)
            with self.assertRaisesRegex(ValueError, 'no death group'):
                L.bake_kf(tmp, palette, {'id': 'dead beast', 'mesh': 'r/beast.nif'}, False, corpse=True)


class ScaleProtocolTests(unittest.TestCase):
    def test_bit_and_order(self):
        """U_AW_EXT is bit 15 (the second bits byte): after the third angle a byte of AmiWind fields, then the scale
        float (AWU_SCALE) and the high byte of a frame over 255 (AWU_FRAME2, the shared animation tables); the client
        reads them in the same place and order and draws the scale as statics are scaled."""
        proto = (SRC / 'protocol.h').read_text(encoding='utf-8')
        self.assertIn('#define	U_AW_EXT	(1<<15)', proto)
        self.assertEqual(proto.count('(1<<15)'), 1)
        self.assertIn('#define	AWU_SCALE	(1<<0)', proto)
        self.assertIn('#define	AWU_FRAME2	(1<<1)', proto)
        sv = (SRC / 'sv_main.c').read_text(encoding='utf-8')
        write = sv[sv.index('void SV_WriteEntitiesToClient'):]
        self.assertLess(write.index('MSG_WriteAngle(msg, ent->v.angles[2]);'), write.index('MSG_WriteByte (msg, aw);'))
        self.assertLess(write.index('MSG_WriteByte (msg, aw);'), write.index('MSG_WriteFloat (msg, scale);'))
        self.assertLess(write.index('MSG_WriteFloat (msg, scale);'), write.index('MSG_WriteByte (msg, (frame >> 8) & 255);'))
        self.assertIn('aw = (scale != 1 ? AWU_SCALE : 0) | (frame > 255 ? AWU_FRAME2 : 0);', write)
        self.assertIn('if (ent->baseline.frame != ent->v.frame || frame > 255)', write)
        self.assertIn('MSG_WriteByte (msg, frame & 255);', write)
        cl = (SRC / 'cl_parse.c').read_text(encoding='utf-8')
        parse = cl[cl.index('void CL_ParseUpdate'):cl.index('void CL_ParseBaseline')]
        self.assertLess(parse.index('ent->msg_angles[0][2] = MSG_ReadAngle();'), parse.index('if (bits & U_AW_EXT)'))
        self.assertLess(parse.index('if (aw & AWU_SCALE)'), parse.index('if (aw & AWU_FRAME2)'))
        self.assertIn('ent->frame |= MSG_ReadByte () << 8;', parse)
        self.assertIn('ent->effects |= AW_EF_ALIAS_SCALE;', parse)
        self.assertIn('ent->aw_sprite_scale = 1;', parse)


if __name__ == '__main__':
    unittest.main()


class ScriptImportTests(unittest.TestCase):
    """BUILD-ACTOR-LIBRARY-MWAD-PATH-47: the build runs tools/actor_library.py as a script, so Python put tools/
    first and tools/mwad.py hid the src/mwad package (ModuleNotFoundError 'mwad.cli'; v0.0.47-dev2 stopped in the
    actor-library stage). Run it the way the build does and check the package import gets past that point."""

    def test_run_as_a_script_finds_the_mwad_package(self):
        import subprocess
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(root / 'tools' / 'actor_library.py'),
                                     '--data-files', str(Path(tmp) / 'no-such-data'), '--palette', str(Path(tmp) / 'p'),
                                     '--out', str(Path(tmp) / 'out')],
                                    capture_output=True, text=True, timeout=120,
                                    env={'PATH': '', 'PYTHONPATH': str(root / 'tools') + ':' + str(root / 'src')})
        self.assertNotIn('ModuleNotFoundError', result.stderr, result.stderr[-2000:])
        self.assertNotIn("'mwad' is not a package", result.stderr)
