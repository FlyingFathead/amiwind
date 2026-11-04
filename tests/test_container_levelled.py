"""CONTAINER-LEVELLED-CONTENTS-60 and CORPSE-LOOT-60: the builder side.

tools/prepare_focus.py keeps a container's levelled item list entries (LEVI) by their list id, gives every NPC and
creature record with an NPCO list its inventory (flag 8) and writes the lists after the identity table (AWL1);
tools/prepare_area_tables.py writes each area's lists in the CHIM actor table's list layout, so the engine rolls them
with ChimActors_LevelledPick; the roll's outcomes are checked here with the same rule's Python form
(tools/chim/actors.py levelled_distribution). Hand-made records only; no game data is read.
"""
import struct, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
import prepare_focus as focus
import prepare_area_tables as areas
from chim.actors import levelled_distribution, PICK_NONE
from test_focus_box import rec, sub, z, ref


def levi(ident, flags, chance, entries):
    return rec('LEVI', sub('NAME', z(ident)), sub('DATA', struct.pack('<I', flags)), sub('NNAM', bytes([chance])),
               sub('INDX', struct.pack('<I', len(entries))),
               *[sub('INAM', z(e)) + sub('INTV', struct.pack('<H', lv)) for e, lv in entries])


def npco(count, ident):
    return sub('NPCO', struct.pack('<i', count) + ident.encode().ljust(32, b'\0'))


MASTER = b''.join([
    rec('MISC', sub('NAME', z('gem')), sub('FNAM', z('Gem')), sub('MCDT', struct.pack('<fii', .1, 50, 0))),
    rec('MISC', sub('NAME', z('cup')), sub('FNAM', z('Cup')), sub('MCDT', struct.pack('<fii', .5, 2, 0))),
    levi('random_gem', 1, 0, [('gem', 1), ('cup', 5)]),
    levi('random_outer', 2, 25, [('random_gem', 1)]),
    rec('CONT', sub('NAME', z('sack')), sub('FNAM', z('Sack')), sub('FLAG', struct.pack('<I', 0)),
        npco(1, 'cup'), npco(2, 'random_gem'), npco(1, 'no_such_thing')),
    rec('NPC_', sub('NAME', z('trader')), sub('FNAM', z('A Trader')), npco(3, 'gem'), npco(1, 'random_outer')),
    rec('NPC_', sub('NAME', z('poor')), sub('FNAM', z('A Poor Man'))),
    rec('CELL', sub('NAME', z('Shop')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
        ref(30, 'sack', (0, 0, 0)), ref(31, 'trader', (10, 0, 0)), ref(32, 'poor', (20, 0, 0))),
])


class BuilderTests(unittest.TestCase):
    def test_item_lists_read_flags_chance_and_entries(self):
        lists = focus.item_lists(MASTER)
        self.assertEqual(lists['random_gem'], (1, 0, [('gem', 1), ('cup', 5)]))
        self.assertEqual(lists['random_outer'], (2, 25, [('random_gem', 1)]))

    def test_levelled_entries_kept_and_actors_get_inventories(self):
        lists = focus.item_lists(MASTER)
        objects = focus.objects_of(MASTER, lists)
        self.assertEqual(objects['sack'][5], [('cup', 1), ('random_gem', 2)])
        self.assertEqual(objects['sack'][6] & 2, 2)          # the unknown entry left out
        self.assertEqual(objects['trader'][5], [('gem', 3), ('random_outer', 1)])
        self.assertEqual(objects['trader'][6] & focus.ACTOR_INVENTORY, focus.ACTOR_INVENTORY)
        self.assertEqual(len(objects['poor']), 5)                # no NPCO: no inventory entry
        rows = {r[2]: r for r in focus.placements(MASTER, objects, {'shop': 4})[4]}
        self.assertEqual(rows[31][12][1] & 8, 8)
        self.assertIsNone(rows[32][12])
        # without the lists the old behaviour stands: the levelled entry is left out
        self.assertEqual(focus.objects_of(MASTER)['sack'][5], [('cup', 1)])

    def test_section_round_trip(self):
        lists = focus.item_lists(MASTER)
        raw = b'AWI1' + focus.levelled_section(lists)
        self.assertEqual(areas.read_levelled(raw, 4), lists)

    def test_area_record_lists_and_rolls(self):
        lists = focus.item_lists(MASTER)
        items = {}
        for ident in ('cup', 'gem'):
            row = bytearray(512); row[0:len(ident)] = ident.encode(); items[ident] = bytes(row)
        def row(kind, reference):
            return struct.pack('<BBBBIiiifi', ord(kind), 0, 1, 0, reference, 0, 0, 0, 0.0, 0) + bytes(36) + bytes(32)
        containers = {30: (0, [('cup', 1), ('random_gem', 2)]), 31: (8, [('gem', 3), ('random_outer', 1)])}
        record, stats = areas.area([row('C', 30), row('A', 31)], {}, containers, {}, {}, items, {}, lists)
        self.assertEqual((stats['levelled_lists'], stats['actor_inventories']), (2, 1))
        self.assertEqual(record[-4:], b'AWL1')
        at = struct.unpack('<I', record[-8:-4])[0]
        self.assertEqual(record[at:at + 4], b'AWL1')
        block = record[at + 4:-8]
        n = struct.unpack('>I', block[:4])[0]
        table = []
        for k in range(n):
            first, count, chance, flags = struct.unpack_from('>IHBB', block, 4 + 8 * k)
            entries = [struct.unpack_from('>HH', block, 4 + 8 * n + 4 * (first + j)) for j in range(count)]
            table.append((chance, flags, entries))
        # random_gem (Each, not all levels): level 1 -> gem only; level 5 -> cup only (the highest at or below)
        gem, cup = sorted(items).index('gem'), sorted(items).index('cup')
        self.assertEqual(table[0][1], 2)                          # bit 1: each
        self.assertEqual(levelled_distribution(table, 0, 1), {PICK_NONE: 0.0, gem: 1.0})
        self.assertEqual(levelled_distribution(table, 0, 7), {PICK_NONE: 0.0, cup: 1.0})
        # random_outer (all levels, chance none 25): a list inside a list
        self.assertEqual(table[1][1], 1)
        self.assertAlmostEqual(levelled_distribution(table, 1, 1)[gem], 0.75)
        # the container rows: the actor flag, the levelled entries flagged with their list index
        conts = 16 + 2 * 96
        c30 = struct.unpack_from('<IHHBBH', record, conts)
        c31 = struct.unpack_from('<IHHBBH', record, conts + 12)
        self.assertEqual((c30[0], c30[3] & areas.CONT_ACTOR, c31[0], c31[3] & areas.CONT_ACTOR), (30, 0, 31, areas.CONT_ACTOR))
        contents = [struct.unpack_from('<HHi', record, conts + 24 + 8 * i) for i in range(4)]
        self.assertEqual(contents, [(cup, 0, 1), (0, 1, 2), (gem, 0, 3), (1, 1, 1)])

    def test_area_without_lists_is_byte_for_byte_the_old_record(self):
        items = {'cup': bytes(512)}
        r = struct.pack('<BBBBIiiifi', ord('C'), 0, 1, 0, 30, 0, 0, 0, 0.0, 0) + bytes(68)
        old, _ = areas.area([r], {}, {30: (0, [('cup', 1)])}, {}, {}, items, {})
        new, _ = areas.area([r], {}, {30: (0, [('cup', 1)])}, {}, {}, items, {}, focus.item_lists(MASTER))
        self.assertEqual(old, new)


class EngineSourceTests(unittest.TestCase):
    SRC = ROOT / 'engine/aga/src'

    def test_body_search_is_wired_and_the_respawn_drops_the_body_changes(self):
        scene = (self.SRC / 'aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('if(aw_corpse_use && aw_corpse_use())return 1;', scene)
        self.assertIn('AW_CorpseInit();', (self.SRC / 'aw_placed.c').read_text(encoding='utf-8'))
        self.assertIn('AW_LedgerContentDrop (&aw_ledger, c->key);', (self.SRC / 'aw_actors.c').read_text(encoding='utf-8'))
        self.assertIn('aw_corpse.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))

    def test_body_check_never_stands_inside_a_living_actor(self):
        # CORPSE-INVENTORY-NOT-OPENABLE-59: the spot beside the body is cleared against actors too (MOVE_NORMAL), so
        # no living resident's bounds hold the crosshair; the dead body is SOLID_NOT and never blocks the spot
        corpse = (self.SRC / 'aw_corpse.c').read_text(encoding='utf-8')
        self.assertIn('tr=SV_Move(spot,p->v.mins,p->v.maxs,spot,MOVE_NORMAL,p);', corpse)
        self.assertNotIn('spot,MOVE_NOMONSTERS', corpse)
        self.assertIn('(another actor)', corpse)
        # the aim test uses the drawn frame's box (a lying body's, a standing resident's), never the whole model's,
        # which encloses every frame and reached a body's length around a standing resident
        scene = (self.SRC / 'aw_scene.c').read_text(encoding='utf-8')
        aim = scene[scene.index('edict_t *AW_NPCTargetReach('):scene.index('static edict_t *npc_target(void)')]
        self.assertIn('Cache_Check(&m->cache)', aim)
        self.assertIn('fd=&h->frames[f];', aim)
        self.assertIn('a=(fmins[j]-o)/d;b=(fmaxs[j]-o)/d;', aim)
        self.assertNotIn('a=(m->mins[j]-o)/d', aim)
        actors = (self.SRC / 'aw_actors.c').read_text(encoding='utf-8')
        self.assertIn('dead again: %s', actors)
        # a room lays its bodies down only once the player is in (the scene set-up empties the combat slots before)
        room = actors[actors.index('void AW_ActorsRoomTick (void)'):actors.index('static void Tick (void)')]
        self.assertIn('!svs.clients[0].spawned', room)
        self.assertLess(room.index('!svs.clients[0].spawned'), room.index('ApplyLoaded ();'))
        combat = (self.SRC / 'aw_combat.c').read_text(encoding='utf-8')
        self.assertIn('set_state(s,S_DEAD,G_DEATH);s->e->v.solid=SOLID_NOT;', combat)
        # a death goes onto the change list at once (a room captures its actors only every half minute), from a fight
        # and from chim actors kill alike
        self.assertEqual(combat.count('if(aw_combat_actor_died)aw_combat_actor_died(s->e);'), 2)
        self.assertIn('found=AW_NPCTarget(p,p->v.v_angle)==best;', corpse)


if __name__ == '__main__':
    unittest.main()
