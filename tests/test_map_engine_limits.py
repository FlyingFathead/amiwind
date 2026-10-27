"""Every output map fits the engine's per-map tables; town budgets only tighten them (BUILD-BUDGET-ENGINE-LIMITS-35).

The town configs set "entity_budget": 1000 and "model_budget": 220 while the engine holds MAX_EDICTS 600
edicts and MAX_MODELS 256 model precaches. On a scenery town's region maps the func_walls go to the scenery
catalogue (aw_scenery.c, AW_SCENERY_MAX_PLACEMENTS), not to edicts; everywhere else they are edicts. These
tests keep tools/map_engine_limits.py in step with the engine and the QuakeC it reads."""
from pathlib import Path
import json
import re
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import map_engine_limits as mel  # noqa: E402

SRC = ROOT / 'engine/aga/src'


def bsp(entities, models=1, leafs=0):
    """A BSP29 with only an entity lump, MODELS empty model records and LEAFS empty leaves."""
    text = ''.join('{\n' + ''.join('"%s" "%s"\n' % kv for kv in e.items()) + '}\n' for e in entities)
    ent = (text + '\0').encode('latin-1')
    lumps = [(0, 0)] * 15
    head = 4 + 15 * 8
    lumps[0] = (head, len(ent))
    lumps[14] = (head + len(ent), models * 64)
    lumps[10] = (head + len(ent) + models * 64, leafs * 28)
    return (struct.pack('<i', 29) + b''.join(struct.pack('<ii', *l) for l in lumps) + ent + bytes(models * 64)
            + bytes(leafs * 28))


def world(*rows):
    return [{'classname': 'worldspawn'}, {'classname': 'info_player_start', 'origin': '0 0 0'}, *rows]


class EngineLimitsTests(unittest.TestCase):
    def test_limits_are_the_engine_defines(self):
        table = mel.limits()
        quakedef = (SRC / 'quakedef.h').read_text()
        for key, name in (('max_edicts', 'MAX_EDICTS'), ('max_models', 'MAX_MODELS'), ('max_sounds', 'MAX_SOUNDS')):
            self.assertEqual(table[key], int(re.search(r'#define\s+%s\s+(\d+)' % name, quakedef).group(1)))
        self.assertEqual(table['max_scenery'],
                         int(re.search(r'#define\s+AW_SCENERY_MAX_PLACEMENTS\s+(\d+)', (SRC / 'aw_town.h').read_text()).group(1)))
        self.assertEqual(table['entity_room'], table['max_edicts'] - table['fixed_edicts'])
        self.assertEqual(table['model_room'], table['max_models'] - table['fixed_models'])

    def test_scenery_catalogue_uses_the_define(self):
        text = (SRC / 'aw_scenery.c').read_text()
        self.assertIn('capacity>AW_SCENERY_MAX_PLACEMENTS', text)
        self.assertNotRegex(text, r'capacity\s*>\s*\d')

    def test_runtime_edicts_are_every_engine_allocation(self):
        """Every ED_Alloc call outside the map load (pr_edict.c), QuakeC spawn (pr_cmds.c) and the NPC
        gallery's own map is counted in runtime_edicts."""
        sites = []
        for path in sorted(SRC.rglob('*.c')):
            if path.name in ('pr_edict.c', 'pr_cmds.c', 'aw_gallery.c'):
                continue
            text = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='utf-8', errors='replace'), flags=re.S)
            sites += [path.name] * len(re.findall(r'\bED_Alloc\s*\(\s*\)', text))
        # PROTOTYPE (branch v0.0.46-type1-stateful): aw_actors.c spawns a joining window frame's actors and the test
        # command's summoned copy; they are not counted in runtime_edicts yet (the map gate models one frame; the
        # window's edicts are an open item, docs/chim/CELL_CROSSINGS.md "Weak points").
        # The Halloween scene (aw_halloween.c, HALLOWEEN-SCENE-53; a MiniWind test scene) takes no reserved slot: it
        # checks for a free edict before each actor and leaves the rest out when the map is full.
        self.assertEqual(sorted(sites), ['aw_actors.c', 'aw_actors.c', 'aw_arena.c', 'aw_companion.c', 'aw_halloween.c',
                                         'aw_inventory.c', 'aw_inventory.c', 'aw_items.c', 'aw_items.c'])
        self.assertIn('if(!edict_available()){', (SRC / 'aw_halloween.c').read_text())
        # one each for the companion and the arena foe; aw_items.c one per carried item of every hostile, and one
        # per carried light of a skeletal guard (its torch, at most AW_ITEMS_CARRIERS: SKEL-ITEM-TAGS-52)
        items = (SRC / 'aw_items.c').read_text()
        self.assertRegex(items, r'for\(k=0;k<AW_ITEMS_KINDS;k\+\+\)\{\s*int i=table\[t\]\.item\[k\];[^}]*ED_Alloc\(\)')
        self.assertRegex(items, r'e=carriers\[i\]\.light=ED_Alloc\(\)')
        self.assertIn('static struct {edict_t *actor;edict_t *light;int table;} carriers[CARRIERS];', items)
        self.assertIn('AW_ItemsShow(e,s->item);', (SRC / 'aw_combat.c').read_text())
        self.assertEqual(mel.runtime_edicts(), 2 + 4 * 2 + 32 + 32)
        inventory = (SRC/'aw_inventory.c').read_text()
        self.assertIn('j==AW_INVENTORY_DROPS', inventory)
        self.assertIn('sv.time-e->freetime>.5', inventory)
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text() + (ROOT / 'engine/aga/qc/defs.qc').read_text()
        self.assertNotRegex(qc, r'\bspawn\s*=\s*#14', 'QuakeC spawn() would allocate edicts at run time')

    def test_runtime_models_are_every_engine_precache(self):
        writers = set()
        for path in sorted(SRC.rglob('*.c')):
            if path.name in ('sv_main.c', 'pr_cmds.c', 'aw_gallery.c'):
                continue
            if re.search(r'sv\.model_precache\[\w+\]\s*=', path.read_text(encoding='utf-8', errors='replace')):
                writers.add(path.name)
        # aw_halloween.c (HALLOWEEN-SCENE-53) admits its cast's models only into free slots and leaves a model out
        # when the table is full (no reserved slot, as the arena's model reports "model table full")
        self.assertEqual(writers, {'aw_arena.c', 'aw_items.c', 'aw_anim.c', 'aw_inventory.c', 'aw_halloween.c'})
        self.assertIn('if(i>=MAX_MODELS || model_names_used>=AW_HALLOWEEN_MAX_ROWS)return 0;',
                      (SRC / 'aw_halloween.c').read_text())
        # aw_anim.c registers a layout's mover model only while the map loads (model_extras reads '>PATH')
        self.assertIn("sv.state!=ss_loading || lazies>=MOVERS", (SRC / 'aw_anim.c').read_text())
        # aw_items.c precaches only while the map loads, from the .tag files model_extras reads
        self.assertIn("sv.state!=ss_loading", (SRC / 'aw_items.c').read_text())
        self.assertEqual(mel.RUNTIME_MODELS, 1 + 16)
        inventory = (SRC/'aw_inventory.c').read_text()
        self.assertIn('model_names_used>=AW_INVENTORY_MODELS', inventory)
        self.assertIn('model_names[AW_INVENTORY_MODELS][64]', inventory)

    def test_spawn_rules_are_read_from_the_quakec(self):
        rules = mel.spawn_rules()
        f = rules['functions']
        for name in ('aw_static', 'aw_flora'):
            self.assertFalse(f[name]['keeps_edict'])
            self.assertTrue(f[name]['static'])
            self.assertTrue(f[name]['model_from_self'])
        for name in ('aw_flame', 'aw_lava'):
            self.assertFalse(f[name]['keeps_edict'])
        for name in ('func_wall', 'aw_npc', 'aw_corpse', 'aw_loop', 'info_player_start'):
            self.assertTrue(f[name]['keeps_edict'])
        self.assertEqual(f['aw_npc']['sounds_from_self'], ['aw_voice'])
        self.assertEqual(rules['worldspawn_models'], ['progs/player.mdl', 'progs/v_nord.mdl'])
        # A new spawn function is classified from its body.
        extra = mel.spawn_rules('void() worldspawn = { precache_model("a.mdl"); };\n'
                                'void() x_static = { precache_model(self.model); makestatic(self); };\n'
                                'void() x_keep = { if (1) { self.solid = 4; } };')
        self.assertEqual(extra['worldspawn_models'], ['a.mdl'])
        self.assertFalse(extra['functions']['x_static']['keeps_edict'])
        self.assertTrue(extra['functions']['x_keep']['keeps_edict'])

    def test_scenery_towns_are_the_engine_town_table(self):
        towns = mel.scenery_towns()
        self.assertEqual(towns['bm'], ('balmora', 64))
        self.assertTrue(mel.scenery_map('bm028') and mel.scenery_map('balmora') and mel.scenery_map('va000'))
        self.assertFalse(mel.scenery_map('bm064') or mel.scenery_map('vf0001') or mel.scenery_map('sn001'))
        self.assertFalse(mel.scenery_map('seyda'))


class MapCountTests(unittest.TestCase):
    def test_edicts_models_sounds_statics(self):
        rows = world({'classname': 'func_wall', 'model': '*1'}, {'classname': 'func_wall', 'model': '*2'},
                     {'classname': 'aw_npc', 'model': 'progs/a.mdl', 'aw_voice': 'v/a.wav'},
                     {'classname': 'aw_npc', 'model': 'progs/a.mdl', 'aw_voice': ''},
                     {'classname': 'aw_static', 'model': 'progs/s.mdl'}, {'classname': 'light'})
        refused, c = mel.check(bsp(rows, models=3), 'vf0001')
        self.assertEqual(refused, [])
        # world + client + 4 kept (2 walls, 2 NPCs) + player start + one reused freed slot + 2 runtime
        self.assertEqual(c['edicts_kept'], 5)
        self.assertEqual(c['edicts_peak'], 1 + 1 + 5 + 1 + mel.runtime_edicts())
        # slot 0, world, *1, *2, player.mdl, v_nord.mdl, a.mdl, s.mdl, runtime
        self.assertEqual(c['models'], 2 + 2 + 2 + 2 + mel.RUNTIME_MODELS)
        self.assertEqual(c['sounds'], 2)
        self.assertEqual(c['static_entities'], 1)
        self.assertEqual(c['no_spawn_function'], {'light': 1})
        self.assertEqual(c['scenery'], 0)

    def test_actor_items_and_animation_sounds_count(self):
        self.assertTrue(mel.spawn_rules()['functions']['aw_npc']['animprep'])
        with tempfile.TemporaryDirectory() as temp:
            id1 = Path(temp)
            (id1 / 'progs').mkdir()
            (id1 / 'progs/a.anm').write_text('IDLE:0:8:0.1 ~LEFT:aw/fx/l.wav:aw/fx/w.wav:aw/fx/s.wav ~RIGHT:aw/fx/l.wav '
                                             '>progs/a_m.mdl')
            (id1 / 'progs/a_m.anm').write_text('WALK:0:8:0.1 ~LEFT:aw/fx/m.wav')
            (id1 / 'progs/a.tag').write_text(chr(10).join(['AWTG1 8', 'weapon progs/items/sword.mdl', 'shield -', '']))
            rows = world({'classname': 'aw_npc', 'model': 'progs/a.mdl'})
            plain = mel.count(bsp(rows))
            withx = mel.count(bsp(rows), id1=id1)
            self.assertEqual(withx['models'] - plain['models'], 2)      # sword + mover
            self.assertEqual(withx['sounds'] - plain['sounds'], 4)      # three + the mover's

    def test_skeletal_actor_tags_count_their_items_and_light(self):
        # an AWTS1 tag (SKEL-ITEM-TAGS-52): weapon, shield and a guard's carried light are precached at spawn
        with tempfile.TemporaryDirectory() as temp:
            id1 = Path(temp)
            (id1 / 'progs').mkdir()
            (id1 / 'progs/g.anm').write_text('IDLE:0:21:0.127')
            (id1 / 'progs/g.tag').write_text(chr(10).join(['AWTS1 2730', 'weapon items/spear.mdl', 'shield -',
                                                          'bones 18 9', 'scale 0.25 0.25 0.25', 'light items/torch.mdl',
                                                          'emitter 0 0 12', '']))
            rows = world({'classname': 'aw_npc', 'model': 'progs/g.mdl'})
            self.assertEqual(mel.count(bsp(rows), id1=id1)['models'] - mel.count(bsp(rows))['models'], 2)

    def test_too_many_edicts_is_refused_on_a_plain_map(self):
        room = mel.limits()['entity_room']
        light = {'classname': 'light'}                 # freed at load: one reused slot
        ok = world(light, *[{'classname': 'func_wall', 'model': '*1'}] * (room - 1))      # + info_player_start
        self.assertEqual(mel.check(bsp(ok, 2), 'vf0001')[0], [])
        over = world(light, *[{'classname': 'func_wall', 'model': '*1'}] * room)
        refused, counts = mel.check(bsp(over, 2), 'vf0001')
        self.assertEqual(counts['edicts_peak'], mel.limits()['max_edicts'] + 1)
        self.assertTrue(refused and 'MAX_EDICTS' in refused[0])

    def test_scenery_maps_take_func_walls_into_the_catalogue(self):
        cap = mel.limits()['max_scenery']
        rows = world(*[{'classname': 'func_wall', 'model': '*1'}] * cap)
        refused, c = mel.check(bsp(rows, 2), 'bm005')
        self.assertEqual(refused, [])
        self.assertEqual((c['scenery'], c['edicts_kept']), (cap, 1))
        self.assertEqual(c['visedicts_at_scenery_link'], cap + c['edicts_peak'])
        refused, _ = mel.check(bsp(world(*[{'classname': 'func_wall', 'model': '*1'}] * (cap + 1)), 2), 'bm005')
        self.assertTrue(any('AW_SCENERY_MAX_PLACEMENTS' in r for r in refused))
        # Harvest-bound func_walls stay edicts.
        _, c = mel.check(bsp(rows, 2), 'bm005', plants=10)
        self.assertEqual((c['scenery'], c['edicts_kept']), (cap - 10, 11))

    def test_visible_entity_table_at_the_scenery_link(self):
        table = mel.limits()
        npcs = table['max_visedicts'] - table['max_scenery']     # pushes catalogue + edicts over MAX_VISEDICTS
        rows = world(*[{'classname': 'func_wall', 'model': '*1'}] * table['max_scenery'],
                     *[{'classname': 'aw_npc', 'model': 'progs/a.mdl'}] * npcs)
        refused, _ = mel.check(bsp(rows, 2), 'bm005')
        self.assertTrue(any('MAX_VISEDICTS' in r for r in refused))

    def test_too_many_models_and_statics_are_refused(self):
        table = mel.limits()
        refused, _ = mel.check(bsp(world(), models=table['model_room'] + 1), 'vf0001')
        self.assertEqual(refused, [])
        refused, c = mel.check(bsp(world(), models=table['model_room'] + 2), 'vf0001')
        self.assertTrue(refused and 'MAX_MODELS' in refused[0], c)
        self.assertEqual(mel.check(bsp(world(), leafs=table['max_leafs']), 'vf0001')[0], [])
        refused, _ = mel.check(bsp(world(), leafs=table['max_leafs'] + 1), 'vf0001')
        self.assertTrue(any('MAX_MAP_LEAFS' in r for r in refused))
        self.assertIn('count > MAX_MAP_LEAFS', (SRC / 'model.c').read_text())
        statics = [{'classname': 'aw_flora', 'model': 'f.spr'}] * (table['max_static_entities'] + 1)
        refused, _ = mel.check(bsp(world(*statics)), 'vf0001')
        self.assertTrue(any('MAX_STATIC_ENTITIES' in r for r in refused))

    def test_streamed_frame_statics_count_against_the_chim_list(self):
        # a CHIM frame map's tagged statics (chim/chim_statics.c): the streamed list, not cl_static_entities
        table = mel.limits()
        tagged = [{'classname': 'aw_flora', 'model': 'f.spr', '_chim_chunk': '0'}] * (table['max_static_entities'] + 1)
        frame = [{'classname': 'worldspawn', '_chim_frame': '0 0'}, {'classname': 'info_player_start', 'origin': '0 0 0'}]
        refused, c = mel.check(bsp(frame + tagged), 'seyda')
        self.assertEqual(refused, [], c)
        self.assertEqual((c['static_entities'], c['streamed_statics']), (0, table['max_static_entities'] + 1))
        # the same rows in an ordinary map (no _chim_frame) are Quake statics
        refused, _ = mel.check(bsp(world(*tagged)), 'vf0001')
        self.assertTrue(any('MAX_STATIC_ENTITIES' in r for r in refused))

    def test_check_maps_lists_every_refusal_and_skips_placeholders(self):
        with tempfile.TemporaryDirectory() as temp:
            maps = Path(temp) / 'id1/maps'
            maps.mkdir(parents=True)
            (maps / 'vf0001.bsp').write_bytes(bsp(world()))
            (maps / 'stub.bsp').write_bytes(b'\0bsp stub')
            report = mel.check_maps(maps, Path(temp) / 'r.json')
            self.assertEqual((report['maps'], list(report['unreadable'])), (1, ['stub']))
            self.assertTrue(json.loads((Path(temp) / 'r.json').read_text())['per_map']['vf0001'])
            room = mel.limits()['entity_room']
            (maps / 'vf0002.bsp').write_bytes(bsp(world({'classname': 'light'}, *[{'classname': 'func_wall'}] * room)))
            with self.assertRaisesRegex(ValueError, 'vf0002.*MAX_EDICTS'):
                mel.check_maps(maps)
            self.assertEqual(mel.check_maps(maps, skip={'vf0002.bsp'})['maps'], 1)
            # The harvest catalogue beside the maps folder keeps bound func_walls as edicts.
            (maps / 'bm001.bsp').write_bytes(bsp(world(*[{'classname': 'func_wall', 'model': '*1'}] * 5), 2))
            (Path(temp) / 'id1/harvest-bm001.txt').write_text('AWH1 0 0 3\n')
            self.assertEqual(mel.audit_maps(maps)['per_map']['bm001']['edicts_kept'], 4)


class BudgetTests(unittest.TestCase):
    def test_every_config_budget_fits_the_engine(self):
        budgets = mel.check_config_budgets()
        self.assertIn('balmora.json', budgets)
        for name in [p.name for p in (ROOT / 'config').glob('vivec_*.json')]:
            self.assertIn(name, budgets)

    def test_a_budget_may_only_tighten(self):
        table = mel.limits()
        scenery = {'town': {'map_prefix': 'bm'}}
        self.assertEqual(mel.budget_room(dict(scenery, entity_budget=500, model_budget=100)), (500, 100))
        with self.assertRaisesRegex(ValueError, 'entity_budget 1001'):
            mel.budget_room(dict(scenery, entity_budget=table['max_scenery'] + 1, model_budget=100))
        with self.assertRaisesRegex(ValueError, 'model_budget'):
            mel.budget_room(dict(scenery, entity_budget=10, model_budget=table['model_room'] + 1))
        plain = {'town': {'map_prefix': 'zz'}, 'entity_budget': table['entity_room'] + 1, 'model_budget': 10}
        with self.assertRaisesRegex(ValueError, 'MAX_EDICTS'):
            mel.budget_room(plain)
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'big.json').write_text(json.dumps(dict(scenery, entity_budget=5000, model_budget=1)))
            with self.assertRaisesRegex(ValueError, 'big.json'):
                mel.check_config_budgets(Path(temp))
            import build_preflight
            self.assertTrue(build_preflight.budget_problems(Path(temp)))
            self.assertEqual(build_preflight.budget_problems(), [])

    def test_other_hand_budgets_stay_inside_the_engine(self):
        import prepare_world_flora
        table = mel.limits()
        self.assertLessEqual(prepare_world_flora.RESERVES['entities'], table['entity_room'])
        self.assertLessEqual(prepare_world_flora.RESERVES['models_plus_sprites'], table['model_room'])

    def test_the_gates_run_in_the_builder(self):
        aga = (ROOT / 'tools/build_aga.py').read_text()
        at = aga.index('check_engine_map_limits(boot/')
        self.assertLess(at, aga.index('require_stairs(boot/'))
        self.assertLess(at, aga.index('world_heap=audit_world_map_heap_with_receipt('))
        self.assertGreater(at, aga.index('chim_frames = chim_frame_maps(args.chim_world'))
        self.assertIn("('engine-map-limits', lambda: check_engine_map_limits(id1, removed, jobs))",
                      (ROOT / 'tools/payload_preflight.py').read_text())
        self.assertIn('budget_problems()', (ROOT / 'tools/build_preflight.py').read_text())


if __name__ == '__main__':
    unittest.main()
