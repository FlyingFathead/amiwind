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


class SideBySideTests(unittest.TestCase):
    def test_creatures_and_npcs_are_baked_side_by_side(self):
        # BUILD-ACTOR-LIBRARY-UNDERUSED-54: the NPCs' units waited for the creatures' last few; the creatures now run
        # in a thread beside the NPC build, on a quarter of the jobs
        text = (ROOT / 'tools/actor_library.py').read_text(encoding='utf-8')
        self.assertLess(text.index('creature_future = side.submit(L.bake'), text.index('NL.build('))
        self.assertLess(text.index('NL.build('), text.index('creature_future.result()'))

    def test_the_npc_pool_follows_the_live_share_up_to_every_allowed_core(self):
        # BUILD-ACTOR-LIBRARY-UNDERUSED-54 (reopened 31 October 2026): launched with --jobs 12 beside other stages,
        # the NPC pool must not stay below the cores the stage is allowed once it runs alone
        import os
        import actor_library
        import build_parallel
        with tempfile.TemporaryDirectory() as tmp:
            allowance = Path(tmp) / 'allowance'
            allowance.write_text('12')
            env = {build_parallel.ALLOWANCE_ENV: str(allowance), build_parallel.BUDGET_ENV: '24',
                   'AMIWIND_BUILD_JOBS': '12'}
            with patch.dict(os.environ, env):
                creatures, npcs = actor_library.pool_sizes(12)
                self.assertEqual(creatures, 3)
                self.assertEqual(npcs, 24)                      # sized for the budget: grows when the stage is alone
                # the pool's in-flight limit follows the allowance: 24 once the other stages finish
                size, limit = build_parallel._throttle(npcs)
                self.assertEqual(size, 24)
                allowance.write_text('24')
                import time
                time.sleep(.6)
                self.assertEqual(limit(), 24)
    def test_the_two_pools_never_hold_more_than_the_allowance(self):
        # while the creatures bake, the NPC pool's limit is the allowance minus the creature workers; after, all of it
        import os
        import time
        import actor_library
        import build_parallel
        with tempfile.TemporaryDirectory() as tmp:
            allowance = Path(tmp) / 'allowance'
            allowance.write_text('12')
            env = {build_parallel.ALLOWANCE_ENV: str(allowance), build_parallel.BUDGET_ENV: '24',
                   'AMIWIND_BUILD_JOBS': '12'}
            with patch.dict(os.environ, env):
                creatures, npcs = actor_library.pool_sizes(12)
                with actor_library.NpcAllowance(creatures) as share:
                    self.assertNotEqual(os.environ[build_parallel.ALLOWANCE_ENV], str(allowance))
                    _, npc_limit = build_parallel._throttle(npcs)
                    _, creature_limit = build_parallel._throttle(creatures)
                    self.assertLessEqual(npc_limit() + creature_limit(), 12)
                    self.assertEqual(npc_limit(), 9)
                    allowance.write_text('24')                     # the other stages finished
                    time.sleep(1.2)
                    self.assertEqual(npc_limit(), 21)
                    self.assertLessEqual(npc_limit() + creature_limit(), 24)
                    share.creatures_done()
                    time.sleep(.6)
                    self.assertEqual(npc_limit(), 24)              # every allowed core once the creatures are done
                self.assertEqual(os.environ[build_parallel.ALLOWANCE_ENV], str(allowance))   # put back
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(build_parallel.ALLOWANCE_ENV, None)
            with actor_library.NpcAllowance(3):
                self.assertNotIn(build_parallel.ALLOWANCE_ENV, os.environ)    # outside the scheduler: nothing

    def test_outside_the_scheduler_the_split_is_as_before(self):
        import os
        import actor_library
        import build_parallel
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(build_parallel.ALLOWANCE_ENV, None)
            self.assertEqual(actor_library.pool_sizes(12), (3, 9))      # outside the scheduler: as before
            self.assertEqual(actor_library.pool_sizes(1), (1, 1))


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


def _bsp(entities):
    """A minimal BSP29 file whose entity lump is ENTITIES (fight_layout_failures reads lump 0 only)."""
    import struct
    text = entities.encode('cp1252') + b'\0'
    return struct.pack('<iii', 29, 124, len(text)) + b'\0' * (124 - 12) + text


class OpeningActorTests(unittest.TestCase):
    """CENSUS-NPC-NO-ATTACK-ANIM-65: the opening's actors (the census office, the ship, the dock) had only their
    21 talk and walk frames and fought with no attack animation."""

    def test_list_is_the_openings_placed_roles(self):
        import re
        import actor_library as AL
        text = (ROOT / 'tools/prepare_intro.py').read_text(encoding='utf-8')
        body = text[text.index('INTRO_ACTORS=('):text.index('INTRO_MAPS=')]
        roles = [(i, s) for i, s, r in re.findall(r"\('([^']+)','([^']+)',(\d+)\)", body) if r != '0']
        self.assertEqual(sorted(roles), sorted(AL.OPENING_ACTORS))
        self.assertEqual(len(AL.OPENING_ACTORS), 8)

    def test_plan_bakes_the_opening_records(self):
        import actor_library as AL
        master = b'NPC_....NAME\x10\0\0\0Chargen Captain\0....NAME\x0e\0\0\0chargen class\0'
        self.assertEqual(AL.opening_ids(master), {'chargen captain', 'chargen class'})
        self.assertEqual(AL.opening_ids(b'nothing'), set())

    def test_layouts_link_the_full_kit_and_every_fighter_has_attack_frames(self):
        import actor_library as AL
        with tempfile.TemporaryDirectory(prefix='amiwind-opening-') as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'progs').mkdir()
            (id1 / 'maps/census.bsp').write_bytes(_bsp(
                '{\n"classname" "worldspawn"\n}\n'
                '{\n"classname" "aw_npc"\n"model" "progs/np_captain.mdl"\n"netname" "Sellus Gravius"\n}\n'
                '{\n"classname" "aw_npc"\n"model" "progs/np_census.mdl"\n"netname" "Socucius Ergalla"\n}\n'))
            for stem in ('captain', 'census'):
                (id1 / ('progs/np_%s.mdl' % stem)).write_bytes(b'mdl')
            # before: no layout, so no attack group anywhere
            self.assertEqual([b[1] for b in AL.fight_layout_failures(id1)], ['Sellus Gravius', 'Socucius Ergalla'])
            manifest = {'npcs': {'chargen captain': {'key': 'aaaa'}, 'chargen class': {'key': 'bbbb'}}}
            links = AL.write_opening_layouts(manifest, id1)
            self.assertEqual(links, {'captain': 'progs/n_aaaa.mdl', 'census': 'progs/n_bbbb.mdl'})
            self.assertEqual((id1 / 'progs/np_captain.anm').read_text(encoding='ascii'),
                             'idle:0:8:0.1500 walk:13:8:0.1250 >progs/n_aaaa.mdl\n')
            # a link to a model that is missing or has no attack group still fails
            self.assertEqual(len(AL.fight_layout_failures(id1)), 2)
            for key in ('aaaa', 'bbbb'):
                (id1 / ('progs/n_%s.mdl' % key)).write_bytes(b'mdl')
                (id1 / ('progs/n_%s.anm' % key)).write_text('idle:0:21:0.1270 walk:1102:8:0.1333:48.14\n',
                                                          encoding='ascii')
            self.assertEqual(len(AL.fight_layout_failures(id1)), 2)
            for key in ('aaaa', 'bbbb'):
                (id1 / ('progs/n_%s.anm' % key)).write_text(
                    'idle:0:21:0.1270 walk:1102:8:0.1333:48.14 attack:2340:8:0.1253:0.714\n', encoding='ascii')
            self.assertEqual(AL.fight_layout_failures(id1), [])
            # the lookup table the check reads (actor-anim-coverage.json)
            rows = AL.write_coverage(id1, Path(tmp) / 'run')
            doc = json.loads((Path(tmp) / 'run/actor-anim-coverage.json').read_text(encoding='utf-8'))
            self.assertEqual((doc['actors'], doc['failing']), (2, 0))
            captain = next(r for r in rows if r['name'] == 'Sellus Gravius')
            self.assertEqual(captain['full_kit'], 'progs/n_aaaa.mdl')
            self.assertEqual(captain['groups'], {'idle': True, 'walk': True, 'run': False, 'attack': True,
                                                 'hit': False, 'death': False})
            self.assertTrue(captain['can_be_hostile'] and captain['ok'] and captain['exception'] is None)
            self.assertEqual(AL.COVERAGE_EXCEPTIONS, {})

    def test_record_binding_names_what_an_actor_lacks(self):
        # OPENING-ACTORS-FULL-RECORD-65: with the image's record tables present, an actor must reach its own combat
        # sheet, reference identity and room stat entry; the failure names the record and the missing part
        import actor_library as AL
        with tempfile.TemporaryDirectory(prefix='amiwind-opening-record-') as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'progs').mkdir()
            (id1 / 'combat').mkdir()
            (id1 / 'maps/census.bsp').write_bytes(_bsp(
                '{\n"classname" "worldspawn"\n"_aw_cell_int" "763"\n}\n'
                '{\n"classname" "aw_npc"\n"model" "progs/np_hall.mdl"\n"netname" "Ganciele Douar"\n'
                '"aw_source_id" "chargen door guard"\n"aw_ref" "172857"\n}\n'))
            (id1 / 'progs/np_hall.anm').write_text('idle:0:8:0.15 attack:8:8:0.1:0.7\n', encoding='ascii')
            (id1 / 'combat/actors.txt').write_text(
                'AWCA1 1\nchargen door guard\tGanciele Douar\t15\t1 2 3 4 5 6 7 8\t' + ' '.join(['6'] * 27) +
                '\t170 110 265\t10 0\tx\n', encoding='ascii')
            rows = AL.coverage_rows(id1)
            b = rows[0]['record_binding']
            self.assertEqual(b['room'], 763)
            self.assertEqual(b['sheet']['level'], 15)
            self.assertEqual(b['missing'], ['reference identity', 'stat entry in its room'])
            self.assertFalse(rows[0]['ok'])
            fail = AL.fight_layout_failures(id1)
            self.assertIn('chargen door guard: reference identity, stat entry in its room', fail[0][2])

    def test_install_refuses_a_fighter_without_attack_frames(self):
        import actor_library as AL
        import npc_library as NL
        with tempfile.TemporaryDirectory(prefix='amiwind-opening-install-') as tmp:
            lib, id1 = Path(tmp) / 'actor-library', Path(tmp) / 'image-id1'
            (lib / 'id1/progs').mkdir(parents=True)
            (lib / 'creature-library.json').write_text(json.dumps({'format': 'x', 'models': {}, 'creatures': {}}),
                                                       encoding='utf-8')
            (lib / 'npc-library.json').write_text(json.dumps(
                {'format': NL.FORMAT, 'profile': 'react', 'models': {}, 'npcs': {}, 'left_out': {}}), encoding='utf-8')
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'maps/census.bsp').write_bytes(_bsp(
                '{\n"classname" "aw_npc"\n"model" "progs/np_hall.mdl"\n"netname" "Ganciele Douar"\n}\n'))
            with self.assertRaisesRegex(ValueError, 'Ganciele Douar'):
                AL.install(lib, id1)

    def test_script_walk_keeps_the_opening_model(self):
        src = (ROOT / 'engine/aga/src/aw_ambient.c').read_text(encoding='utf-8')
        self.assertIn('a->mover[0] && field(s->e,"aw_intro_role",0)<=0 && !AW_AnimMoving(s->e)', src)
        combat = (ROOT / 'engine/aga/src/aw_combat.c').read_text(encoding='utf-8')
        self.assertIn('AW_AnimMover(e,1);', combat[combat.index('int AW_CombatEngage('):])


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
