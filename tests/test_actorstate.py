# SPDX-License-Identifier: GPL-3.0-only
"""The actor record (docs/ACTOR_STATE.md): the builder's actor table on a small synthetic game data set (fixed and
autocalculated NPCs, a creature, items, a levelled list, spells; no game data in the repo), and the engine's
aw_actorstate.c natively on that file: lookup, the stats' OpenMW rules, inventory, spells, death, saved games."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript import awms  # noqa: E402
from mwscript.actors import read_actor, INV_EQUIPPED, INV_LEVELLED, ACTOR_FEMALE, ACTOR_AUTOCALC, ACTOR_WALKS  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, flags) + payload


def npco(count, name):
    return sub('NPCO', struct.pack('<i', count) + name.encode('ascii').ljust(32, b'\0'))


def npcs(name):
    return sub('NPCS', name.encode('ascii').ljust(32, b'\0'))


def aidt(hello, fight, flee, alarm):
    return sub('AIDT', struct.pack('<HBBB3sI', hello, fight, flee, alarm, b'\0' * 3, 0))


RESULT_CHOICE = 'Choice "Yes" 1 "No" 2'

def master_bytes():
    out = [record('GMST', sub('NAME', 'fNPCbaseMagickaMult'), sub('FLTV', struct.pack('<f', 2.0)))]
    for i in range(27):   # skill i: governed by attribute i % 8, specialization i % 3
        out.append(record('SKIL', sub('INDX', struct.pack('<i', i)), sub('SKDT', struct.pack('<ii4f', i % 8, i % 3, 1, 1, 1, 1))))
    radt = struct.pack('<14i', 5, 10, 6, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)          # +10 Long Blade, +5 Axe
    radt += b''.join(struct.pack('<2i', 40 + i, 30 + i) for i in range(8)) + struct.pack('<4fi', 1, 1, 1, 1, 0)
    out.append(record('RACE', sub('NAME', 'Test Race'), sub('RADT', radt), npcs('race power')))
    cldt = struct.pack('<3i', 0, 5, 0) + b''.join(struct.pack('<2i', m, M) for m, M in ((8, 5), (9, 6), (10, 7), (11, 4), (12, 0)))
    out.append(record('CLAS', sub('NAME', 'Test Class'), sub('CLDT', cldt + struct.pack('<2i', 0, 0))))
    out.append(record('SPEL', sub('NAME', 'test spell'), sub('FNAM', 'Spell of Testing'), sub('SPDT', struct.pack('<3i', 0, 5, 0))))
    # an autocalculated spell (SPDT flags 1): its cost from its effect and the magic effect's base cost (MGEF 14)
    # the effects' names: one sEffect<Name> setting per effect index, in order after sEffects (effect 14 Fire Damage)
    out.append(record('GMST', sub('NAME', 'sEffects'), sub('STRV', 'Effects')))
    for i in range(14):
        out.append(record('GMST', sub('NAME', 'sEffectTest%d' % i), sub('STRV', 'Test Effect %d' % i)))
    out.append(record('GMST', sub('NAME', 'sEffectFireDamage'), sub('STRV', 'Fire Damage')))
    out.append(record('MGEF', sub('INDX', struct.pack('<i', 14)), sub('MEDT', struct.pack('<ifi', 2, 5.0, 0) + bytes(24))))
    out.append(record('SPEL', sub('NAME', 'auto spell'), sub('FNAM', 'Auto Spell'), sub('SPDT', struct.pack('<3i', 0, 99, 1)),
                      sub('ENAM', struct.pack('<hbbiiiii', 14, -1, -1, 2, 0, 5, 10, 20))))
    out.append(record('SPEL', sub('NAME', 'race power'), sub('SPDT', struct.pack('<3i', 5, 0, 0))))
    out.append(record('SPEL', sub('NAME', 'other spell'), sub('SPDT', struct.pack('<3i', 1, 0, 0))))
    # RESIST-NORMAL-WEAPONS-61 (v0.0.62): always-active spells carry Resist (98) and Weakness (36) to Normal Weapons:
    # an ability 100 (the game's "immune to normal weapons"), a disease 20-40 (the middle, 30, counts), and a castable
    # spell and a power with 98 that must not count until cast
    out.append(record('SPEL', sub('NAME', 'rat immunity'), sub('SPDT', struct.pack('<3i', 1, 0, 0)),
                      sub('ENAM', struct.pack('<hbbiiiii', 98, -1, -1, 0, 0, 0, 100, 100))))
    out.append(record('SPEL', sub('NAME', 'rat pox'), sub('SPDT', struct.pack('<3i', 3, 0, 0)),
                      sub('ENAM', struct.pack('<hbbiiiii', 36, -1, -1, 0, 0, 0, 20, 40)),
                      sub('ENAM', struct.pack('<hbbiiiii', 98, -1, -1, 0, 0, 0, 5, 5))))
    out.append(record('SPEL', sub('NAME', 'rat shield spell'), sub('SPDT', struct.pack('<3i', 0, 5, 0)),
                      sub('ENAM', struct.pack('<hbbiiiii', 98, -1, -1, 0, 0, 10, 50, 50))))
    out.append(record('SPEL', sub('NAME', 'rat power'), sub('SPDT', struct.pack('<3i', 5, 0, 0)),
                      sub('ENAM', struct.pack('<hbbiiiii', 98, -1, -1, 0, 0, 10, 50, 50))))
    # UNDERWATER-BREATH-62 (v0.0.63-dev3): Water Breathing (0) has the NoMagnitude flag (0x8) and an ability with it
    # stores magnitude 0 (the Argonian's): it counts 1
    out.append(record('MGEF', sub('INDX', struct.pack('<i', 0)), sub('MEDT', struct.pack('<ifi', 1, 5.0, 0x8) + bytes(24))))
    out.append(record('SPEL', sub('NAME', 'rat gills'), sub('SPDT', struct.pack('<3i', 1, 0, 0)),
                      sub('ENAM', struct.pack('<hbbiiiii', 0, -1, -1, 0, 0, 0, 0, 0))))
    # v0.0.61 (PLAYER-CASTING-59): three starting spells (SPDT flags 2; one always succeeds, flag 4; one too dear for
    # any magicka) and two enchantments: a Cast When Strikes one on the sword, an autocalculated Cast When Used one
    out.append(record('SPEL', sub('NAME', 'start fire'), sub('SPDT', struct.pack('<3i', 0, 5, 2)),
                      sub('ENAM', struct.pack('<hbbiiiii', 14, -1, -1, 2, 0, 1, 2, 4))))
    out.append(record('SPEL', sub('NAME', 'start always'), sub('SPDT', struct.pack('<3i', 0, 50, 6)),
                      sub('ENAM', struct.pack('<hbbiiiii', 14, -1, -1, 1, 0, 1, 2, 4))))
    out.append(record('SPEL', sub('NAME', 'start pricey'), sub('SPDT', struct.pack('<3i', 0, 500, 2)),
                      sub('ENAM', struct.pack('<hbbiiiii', 14, -1, -1, 1, 0, 1, 2, 4))))
    out.append(record('ENCH', sub('NAME', 'strike_en'), sub('ENDT', struct.pack('<4i', 1, 4, 100, 0)),
                      sub('ENAM', struct.pack('<hbbiiiii', 14, -1, -1, 1, 0, 1, 3, 6))))
    out.append(record('ENCH', sub('NAME', 'auto_en'), sub('ENDT', struct.pack('<4i', 2, 0, 0, 1)),
                      sub('ENAM', struct.pack('<hbbiiiii', 14, -1, -1, 0, 0, 2, 2, 4))))
    wpdt = struct.pack('<fihhffh6Bi', 20.0, 100, 1, 500, 1.25, 1.5, 0, 2, 10, 3, 12, 4, 14, 0)
    out.append(record('WEAP', sub('NAME', 'test_sword'), sub('WPDT', wpdt), sub('ENAM', 'strike_en')))
    out.append(record('ARMO', sub('NAME', 'test_cuirass'), sub('AODT', struct.pack('<ifiiii', 1, 30.0, 50, 400, 0, 20))))
    out.append(record('MISC', sub('NAME', 'test_ring')))
    out.append(record('MISC', sub('NAME', 'Gold_001')))
    out.append(record('LEVI', sub('NAME', 'test_list'), sub('DATA', struct.pack('<i', 0)), sub('NNAM', b'\0'),
                      sub('INDX', struct.pack('<i', 1)), sub('INAM', 'test_ring'), sub('INTV', struct.pack('<H', 1))))
    npdt = struct.pack('<h8B27BB3HBBbBi', 5, *range(50, 58), *range(10, 37), 0, 50, 20, 100, 40, 1, 2, 0, 30)
    out.append(record('NPC_', sub('NAME', 'Fixed_NPC'), sub('RNAM', 'Test Race'), sub('CNAM', 'Test Class'),
                      sub('NPDT', npdt), sub('FLAG', struct.pack('<I', 1)), aidt(30, 90, 10, 5),
                      npco(2, 'test_sword'), npco(1, 'test_cuirass'), npco(5, 'gold_005'), npco(1, 'test_list'),
                      npcs('test spell'), npcs('auto spell')))
    out.append(record('NPC_', sub('NAME', 'auto_npc'), sub('RNAM', 'Test Race'), sub('CNAM', 'Test Class'),
                      sub('NPDT', struct.pack('<hBBb3si', 3, 60, 0, -1, b'\0' * 3, 7)), sub('FLAG', struct.pack('<I', 0x18))))
    out.append(record('NPC_', sub('NAME', 'player'), sub('RNAM', 'Test Race'), sub('CNAM', 'Test Class'),
                      sub('NPDT', npdt), sub('FLAG', struct.pack('<I', 0))))
    # a dialogue topic with result scripts (DIALOGUE-COMPLETE-58): each compiled as a _dlg_ script, found by DRSC
    out.append(record('DIAL', sub('NAME', 'test topic'), sub('DATA', b'\0')))
    out.append(record('INFO', sub('INAM', '1'), sub('ONAM', 'Fixed_NPC'), sub('NAME', 'Well?'),
                      sub('BNAM', RESULT_CHOICE)))
    out.append(record('INFO', sub('INAM', '2'), sub('NAME', 'Bye.'), sub('BNAM', 'Goodbye')))
    crea = struct.pack('<24i', 0, 4, *([20] * 8), 30, 0, 60, 10, 40, 5, 15, 1, 3, 2, 4, 0, 0, 0)
    out.append(record('CREA', sub('NAME', 'test_rat'), sub('NPDT', crea), sub('FLAG', struct.pack('<I', 0x48)),
                      aidt(0, 100, 0, 0), npcs('other spell'), npcs('rat immunity'), npcs('rat pox'),
                      npcs('rat shield spell'), npcs('rat power'), npcs('rat gills')))
    return b''.join(out)


def build():
    tmp = Path(tempfile.mkdtemp(prefix='aw-actors-'))
    try:
        (tmp / 'Morrowind.esm').write_bytes(master_bytes())
        data = GameData().load(tmp)
        prog, compiled = compile_program(data, handwritten=())
        raw, sizes = awms.write(prog, compiled, bindings(prog, compiled))
        return prog, raw, sizes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class ActorTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, cls.raw, cls.sizes = build()
        cls.f = awms.read(cls.raw)
        cls.names = awms.strings(cls.f)
        cls.t = cls.prog.actors

    def row(self, ident):
        return read_actor(self.f['ACTB'], self.t.actor(ident))

    def test_rows_sorted_and_counted(self):
        ids = [self.names[read_actor(self.f['ACTB'], i)['id']].casefold() for i in range(self.f['ACTB_rows'])]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(ids, ['auto_npc', 'fixed_npc', 'player', 'test_rat'])
        self.assertEqual(self.t.report['autocalc'], 1)
        self.assertEqual(self.sizes['ACTB'], 96 * 4)
        self.assertLess(self.sizes['resident'], self.f['BIND_rows'] * 24 + self.sizes['resident'] + 1)

    def test_fixed_npc_keeps_its_record(self):
        r = self.row('fixed_npc')
        self.assertEqual((r['level'], r['attributes'], r['skills'][:3]), (5, list(range(50, 58)), [10, 11, 12]))
        self.assertEqual((r['health'], r['magicka'], r['fatigue']), (50, 20, 100))
        self.assertEqual((r['hello'], r['fight'], r['flee'], r['alarm']), (30, 90, 10, 5))
        self.assertEqual((r['disposition'], r['reputation'], r['rank'], r['gold']), (40, 1, 2, 30))
        self.assertEqual(r['flags'] & ACTOR_FEMALE, ACTOR_FEMALE)
        self.assertEqual(self.names[r['race']], 'Test Race')

    def test_inventory_shared_items_levelled_and_gold(self):
        r = self.row('fixed_npc')
        inv = self.t.inventory[r['inv_first']:r['inv_first'] + r['inv_count']]
        named = {self.names[self.t.items[i]['id']]: (c, fl) for i, c, fl in inv}
        self.assertEqual(named['test_sword'], (2, INV_EQUIPPED))
        self.assertEqual(named['test_cuirass'], (1, INV_EQUIPPED))
        self.assertEqual(named['test_ring'], (1, INV_LEVELLED))      # the levelled list's pick
        self.assertEqual(named['Gold_001'][0], 5)                     # gold_005 is the gold item
        self.assertEqual(self.t.items[0]['id'], self.prog.string('Gold_001'))
        self.assertEqual(inv[r['weapon']][0], self.t.item_index['test_sword'])
        sword = self.t.items[self.t.item_index['test_sword']]
        self.assertEqual((sword['type'], sword['health'], sword['damage']), (1, 500, bytes([2, 10, 3, 12, 4, 14])))
        spells = [self.names[self.t.spells[s]['id']] for s in self.t.spell_list[r['spell_first']:r['spell_first'] + r['spell_count']]]
        self.assertEqual(spells, ['test spell', 'auto spell', 'race power'])   # the race's powers join (OpenMW)
        # ASPC: the names and the game's price cost (fixed SPDT 5; autocalculated 0.5 x 30 x 0.5 x 5 x 0.5 x 1.5 = 28.1)
        info = {self.names[s['id']]: (self.names[s['name']] if s['name'] != 0xFFFF else None, s['cost'])
                for s in self.t.spells}
        self.assertEqual(info['test spell'], ('Spell of Testing', 5))
        self.assertEqual(info['auto spell'], ('Auto Spell', 28))
        self.assertEqual(len(self.f['ASPC']), 4 * len(self.t.spells))

    def test_autocalculated_npc_by_the_original_rule(self):
        import prepare_combat
        r = self.row('auto_npc')
        self.assertEqual(r['flags'] & ACTOR_AUTOCALC, ACTOR_AUTOCALC)
        attributes, skills, health = prepare_combat.autocalc(self.t.records, self.t.records['NPC_']['auto_npc'], 3)
        self.assertEqual((r['attributes'], r['skills'], r['health']), (attributes, skills, int(health)))
        self.assertEqual(r['fatigue'], attributes[0] + attributes[2] + attributes[3] + attributes[5])
        self.assertEqual(r['magicka'], int(attributes[1] * 2.0))
        self.assertEqual((r['disposition'], r['gold']), (60, 7))

    def test_creature_skills_by_specialization(self):
        r = self.row('test_rat')
        self.assertEqual(r['kind'], 1)
        self.assertEqual(r['skills'], [(40, 5, 15)[i % 3] for i in range(27)])   # combat, magic, stealth
        self.assertEqual(r['attack'], [1, 3, 2, 4, 0, 0])
        self.assertEqual((r['health'], r['fatigue'], r['fight']), (30, 60, 100))
        self.assertTrue(r['flags'] & ACTOR_WALKS)

    def test_every_magic_effect_has_the_games_name(self):
        # the n-th sEffect setting names effect n (no hand list); an effect of the data without one stops the build
        from mwscript import actors as AC
        names = AC.effect_names(self.prog.actors.records)
        self.assertEqual((names[0], names[13], names[14], names[15]), ('Test Effect 0', 'Test Effect 13', 'Fire Damage', ''))
        mgef = dict(self.prog.actors.records['MGEF'])
        mgef[15] = []
        records = dict(self.prog.actors.records, MGEF=mgef)
        self.assertEqual([i for i in range(AC.MAGIC_EFFECTS) if i in records['MGEF'] and not AC.effect_names(records)[i]], [15])

    def test_dialogue_results_compiled_and_keyed(self):
        # each result text a _dlg_ script (Choice and Goodbye carried by the host), DRSC sorted by (hash, length)
        from mwscript.codegen import fnv1a, SCRIPT_DIALOGUE
        rows = [struct.unpack_from('>IHHHH', self.f['DRSC'], 12 * i) for i in range(self.f['DRSC_rows'])]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows, sorted(rows))
        for text in (RESULT_CHOICE, 'Goodbye'):
            raw = text.encode('cp1252')
            match = [r for r in rows if r[0] == fnv1a(raw) and r[1] == len(raw)]
            self.assertEqual(len(match), 1, text)
            self.assertEqual(match[0][2], 0xFFFF)       # the speakers have no script: no locals
            self.assertEqual(match[0][4], 0)            # compiled
        flags = [s['flags'] for s in awms.scripts(self.f)]
        self.assertEqual(sum(1 for x in flags if x & SCRIPT_DIALOGUE), 2)

    def test_enchantments_and_starting_spells(self):
        # PLAYER-CASTING-59: AENC sorted by folded id; the record's cost and charge as authored, the autocalculated
        # one by the game enchantment rule: 0.5 x (2 + 4) x 0.1 x 5 x 2 s = 3.0 x fEffectCostMult 0.5 = 1.5, its charge
        # round(1.5) = 2 x iMagicItemChargeUse 5 = 10; AITM's sword names its row; ASPT carries the SPDT flags; APCS
        # the settings (the masters' defaults here) and the starting spells in record order
        rows = [struct.unpack_from('>HBBffHBB', self.f['AENC'], 16 * i) for i in range(self.f['AENC_rows'])]
        self.assertEqual([self.names[r[0]] for r in rows], ['auto_en', 'strike_en'])
        self.assertEqual([r[1:5] + (r[6],) for r in rows], [(2, 1, 1.5, 10.0, 1), (1, 0, 4.0, 100.0, 1)])
        aeff = struct.unpack_from('>hbbBBHHHH', self.f['AEFF'], 14 * rows[1][5])
        self.assertEqual(aeff, (14, -1, -1, 1, 0, 0, 1, 3, 6))
        sword = self.t.item_index['test_sword']
        self.assertEqual(struct.unpack_from('>H', self.f['AITM'], 32 * sword + 28)[0], 1)
        self.assertEqual(struct.unpack_from('>H', self.f['AITM'], 32 * self.t.item_index['test_ring'] + 28)[0], 0xFFFF)
        self.assertEqual(len(self.f['AITM']), 32 * self.f['AITM_rows'])
        flags = {self.names[self.t.spells[i]['id']]: self.f['ASPT'][4 * i + 3] for i in range(len(self.t.spells))}
        self.assertEqual((flags['start fire'], flags['start always'], flags['auto spell'], flags['test spell']), (2, 6, 1, 0))
        head = struct.unpack_from('>ffHHf', self.f['APCS'])
        self.assertEqual(head, (1.0, 50.0, 100, 70, 0.5))
        start = [struct.unpack_from('>H', self.f['APCS'], 16 + 2 * i)[0] for i in range(self.f['APCS_rows'])]
        self.assertEqual([self.names[self.t.spells[i]['id']] for i in start], ['start fire', 'start always', 'start pricey'])

    def test_file_reads_back(self):
        f = awms.read(self.raw)
        for tag in ('OACT', 'ACTB', 'AINV', 'AITM', 'ASPT', 'ASPL', 'ASPC', 'AENC', 'APCS'):
            self.assertIn(tag, f)
        self.assertLess(f['resident'], [16 + 16 * i for i in range(1)][0] + len(self.raw))


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_actorstate.h"
static unsigned char *file;static long size;
static int rd(void *c,uint32_t off,void *out,uint32_t n){(void)c;if(off+n>(uint32_t)size)return 1;memcpy(out,file+off,n);return 0;}
#define P(...) printf(__VA_ARGS__)
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");aw_actorstate_io_t io={rd,NULL};aw_actor_t *a,*r;int row,i;unsigned char save[8192];int n;
    int sword=atoi(argv[2]),ring=atoi(argv[3]),spell=atoi(argv[4]),other=atoi(argv[5]),auto_spell=atoi(argv[6]);
    fseek(f,0,SEEK_END);size=ftell(f);fseek(f,0,SEEK_SET);file=malloc(size);if(fread(file,1,size,f)!=(size_t)size)return 2;fclose(f);
    n=AW_ActorStateOpen(file,(uint32_t)size,&io);P("open %d count %d\n",n,AW_ActorCount());
    P("find %d %d %d %d\n",AW_ActorFind("FIXED_npc"),AW_ActorFind("test_rat"),AW_ActorFind("nobody"),AW_ActorFind("auto_npc"));
    row=AW_ActorFind("fixed_npc");a=AW_ActorGet(1234,row,1);
    P("get %.0f %.0f %.0f %.0f lvl %.0f fight %.0f\n",AW_ActorStat(a,AWA_ATTRIBUTE),AW_ActorStat(a,AWA_SKILL+2),
      AW_ActorStat(a,AWA_HEALTH),AW_ActorStat(a,AWA_FATIGUE),AW_ActorStat(a,AWA_LEVEL),AW_ActorStat(a,AWA_FIGHT));
    P("same %d\n",AW_ActorGet(1234,row,0)==a);
    /* modStat: base 50 +60 -> capped at 100 (not fortified); then -120 -> 0 */
    AW_ActorModStat(a,AWA_ATTRIBUTE,60);P("mod %.0f\n",AW_ActorStat(a,AWA_ATTRIBUTE));
    AW_ActorModStat(a,AWA_ATTRIBUTE,-120);P("mod %.0f\n",AW_ActorStat(a,AWA_ATTRIBUTE));
    AW_ActorSetStat(a,AWA_ATTRIBUTE+1,150);P("set %.0f\n",AW_ActorStat(a,AWA_ATTRIBUTE+1));
    /* dynamics */
    AW_ActorModCurrent(a,AWA_HEALTH,-20);P("health %.0f ratio %.2f\n",AW_ActorStat(a,AWA_HEALTH),AW_ActorRatio(a,AWA_HEALTH));
    AW_ActorModCurrent(a,AWA_HEALTH,100);P("health %.0f\n",AW_ActorStat(a,AWA_HEALTH));
    AW_ActorModStat(a,AWA_HEALTH,10);P("health %.0f\n",AW_ActorStat(a,AWA_HEALTH));
    AW_ActorSetStat(a,AWA_MAGICKA,5);P("magicka %.0f\n",AW_ActorStat(a,AWA_MAGICKA));
    AW_ActorModCurrent(a,AWA_FATIGUE,-150);P("fatigue %.0f\n",AW_ActorStat(a,AWA_FATIGUE));
    AW_ActorModCurrent(a,AWA_MAGICKA,-50);P("magicka %.0f\n",AW_ActorStat(a,AWA_MAGICKA));
    AW_ActorSetStat(a,AWA_FIGHT,100);AW_ActorModStat(a,AWA_HELLO,-5);P("ai %.0f %.0f\n",AW_ActorStat(a,AWA_FIGHT),AW_ActorStat(a,AWA_HELLO));
    /* inventory */
    P("items %d %d %d\n",AW_ActorItemCount(a,sword),AW_ActorItemCount(a,ring),AW_ActorItemCount(a,0));
    AW_ActorAddItem(a,ring,3);P("ring %d\n",AW_ActorItemCount(a,ring));
    n=AW_ActorRemoveItem(a,sword,5);P("removed %d sword %d equipped %d\n",n,AW_ActorItemCount(a,sword),AW_ActorEquipped(a,0));
    AW_ActorAddItem(a,ring,-65535);P("ring %d\n",AW_ActorItemCount(a,ring));
    AW_ActorAddItem(a,ring,0);P("ring %d\n",AW_ActorItemCount(a,ring));
    /* spells */
    P("spells %d %d\n",AW_ActorHasSpell(a,spell),AW_ActorHasSpell(a,other));
    AW_ActorRemoveSpell(a,spell);AW_ActorAddSpell(a,other);P("spells %d %d n %d\n",AW_ActorHasSpell(a,spell),AW_ActorHasSpell(a,other),a->nspells);
    AW_ActorAddSpell(a,spell);P("spells %d n %d\n",AW_ActorHasSpell(a,spell),a->nspells);
    /* death */
    r=AW_ActorGet(77,AW_ActorFind("test_rat"),1);
    P("skill %.0f\n",AW_ActorStat(r,AWA_SKILL+1));
    AW_ActorSetStat(r,AWA_SKILL+1,99);P("skill %.0f\n",AW_ActorStat(r,AWA_SKILL+1));
    AW_ActorModCurrent(r,AWA_HEALTH,-100);
    {int first=AW_ActorOnDeath(r),second=AW_ActorOnDeath(r);
     P("dead %.0f ondeath %d %d count %d\n",AW_ActorStat(r,AWA_DEAD),first,second,AW_ActorDeadCount(AW_ActorFind("test_rat")));}
    /* save and load */
    n=AW_ActorStateExport(save,sizeof(save));P("export %d\n",n);
    P("import %d\n",AW_ActorStateImport(save,n));
    a=AW_ActorGet(1234,row,0);
    P("after %.0f %.0f ring %d spells %d %d count %d\n",AW_ActorStat(a,AWA_ATTRIBUTE+1),AW_ActorStat(a,AWA_HEALTH),
      AW_ActorItemCount(a,ring),AW_ActorHasSpell(a,spell),AW_ActorHasSpell(a,other),AW_ActorDeadCount(AW_ActorFind("test_rat")));
    P("small %d\n",AW_ActorStateExport(save+4096,20));
    save[4]=9;P("bad %d\n",AW_ActorStateImport(save,n));
    {char name[48];int type,cost,held[8],k,m;aw_actor_t *x=AW_ActorGet(4321,row,1);
     k=AW_ActorSpellInfo(spell,&type,name,sizeof(name),&cost);P("aspc %d %d %s %d\n",k,type,name,cost);
     m=AW_ActorSpells(x,held,8);P("held %d",m);for(k=0;k<m;k++)P(" %d",held[k]);P("\n");
     {int it[8],ct[8],eq[8];char id[40];m=AW_ActorItems(x,it,ct,eq,8);P("stock %d",m);
      for(k=0;k<m;k++){AW_ActorItemId(it[k],id,sizeof(id));P(" %s:%d",id,ct[k]);}P("\n");}}
    /* the pool: unchanged records give way, changed ones stay; when every record is changed the pool takes a new
     * block (ACTOR-STATE-POOL-LIMITS-54: it used to refuse the 129th) */
    AW_ActorStateImport(NULL,0);
    for(i=0;i<AW_ACTOR_POOL+10;i++)if(!AW_ActorGet(5000+i,row,1))break;
    P("pool %d evicted %lu\n",i,AW_ActorStateStats()->evicted);
    for(i=0;i<AW_ACTOR_POOL;i++){aw_actor_t *x=AW_ActorGet(9000+i,row,1);if(!x)break;AW_ActorSetStat(x,AWA_LEVEL,9);}
    P("changed %d full %d\n",i,AW_ActorGet(99999,row,1)==NULL);
    P("player %d resident %lu\n",AW_ActorPlayer()!=NULL && AW_ActorPlayer()->base==(uint16_t)AW_ActorFind("player"),AW_ActorStateResident());
    /* sold to a merchant that does not stock it: kept, carried through a save, bought back (BARTER-SOLD-ITEM-LOST-58) */
    {unsigned char blob[256];int k,m,count;uint32_t ref;char id[40];
     k=AW_SoldAdd(1234,"misc_vase",1);k+=AW_SoldAdd(1234,"MISC_Vase",1);k+=AW_SoldAdd(77,"misc_vase",1);
     m=AW_SoldExport(blob,sizeof(blob));AW_SoldReset();P("sold %d export %d after-reset %d",k,m,AW_SoldCount());
     k=AW_SoldImport(blob,m);P(" import %d count %d",k,AW_SoldCount());
     for(k=0;k<AW_SoldCount();k++){AW_SoldAt(k,&ref,id,sizeof(id),&count);P(" %u:%s:%d",(unsigned)ref,id,count);}
     {int b1=AW_SoldAdd(1234,"misc_vase",-1),b2=AW_SoldAdd(1234,"misc_vase",-1),b3=AW_SoldAdd(1234,"misc_vase",-1);
      P(" back %d %d %d left %d",b1,b2,b3,AW_SoldCount());}
     blob[5]=9;k=AW_SoldImport(blob,m);P(" bad %d %d\n",k,AW_SoldCount());AW_SoldReset();}
    /* the magic effects and a spell's effects (Spellmaking, Enchanting) */
    {aw_mgef_t me;aw_spell_effect_t se[4];int k=AW_ActorMagicEffect(14,&me),m=AW_ActorSpellEffects(auto_spell,se,4);
     P("mgef %d %u %.1f %d %s none %d effects %d",k,(unsigned)me.flags,me.base_cost,me.school,me.name,AW_ActorMagicEffect(3,&me),m);
     if(m>0)P(" %d %d %d %u %u %u %u",se[0].effect,se[0].skill,se[0].range,se[0].area,se[0].duration,se[0].magnitude_min,se[0].magnitude_max);
     P("\n");}
    /* the bound: past AW_SoldMax kinds the oldest is forgotten, never refused */
    {char id[40];int k,ok=1,count;uint32_t ref;
     for(k=0;k<=AW_SoldMax();k++){sprintf(id,"thing_%d",k);ok&=AW_SoldAdd(5,id,1);}
     AW_SoldAt(0,&ref,id,sizeof(id),&count);
     P("cap %d ok %d count %d first %s\n",AW_SoldMax(),ok,AW_SoldCount(),id);AW_SoldReset();}
    /* made spells and enchanted items: added, carried through a save, bounded at 64 each */
    {aw_made_spell_t s;aw_made_item_t m;unsigned char blob[32768];int k,len,full=0;
     memset(&s,0,sizeof(s));strcpy(s.name,"My Fire");s.effects=2;s.effect[0].effect=14;s.effect[0].range=2;
     s.effect[0].magnitude_min=5;s.effect[0].magnitude_max=10;s.effect[1].effect=1;s.effect[1].duration=30;
     memset(&m,0,sizeof(m));strcpy(m.base,"steel_longsword");strcpy(m.name,"Biter");m.charge=40;m.charge_max=40;
     m.cast_type=2;m.effects=1;m.effect[0].effect=14;m.effect[0].magnitude_max=7;
     k=AW_MadeSpellAdd(&s);k+=AW_MadeItemAdd(&m);len=AW_MadeExport(blob,sizeof(blob));AW_MadeReset();
     P("made %d export %d",k,len);k=AW_MadeImport(blob,len);
     P(" import %d spells %d items %d %s %d %u %s %s %.0f",k,AW_MadeSpellCount(),AW_MadeItemCount(),AW_MadeSpellAt(0)->name,
       AW_MadeSpellAt(0)->effects,(unsigned)AW_MadeSpellAt(0)->effect[1].duration,AW_MadeItemAt(0)->base,AW_MadeItemAt(0)->name,
       AW_MadeItemAt(0)->charge);
     for(k=0;k<70;k++)if(AW_MadeSpellAdd(&s)<0)full++;
     blob[4]=200;k=AW_MadeImport(blob,len);P(" full %d bad %d %d\n",full,k,AW_MadeSpellCount());AW_MadeReset();}
    /* filled soul gems: the soul from the creature record, through a save */
    {unsigned char blob[512];int k,len,creature;char gem[40];
     k=AW_GemAdd("misc_soulgem_petty",AW_ActorFind("test_rat"));len=AW_GemsExport(blob,sizeof(blob));AW_GemsReset();
     P("gem %d export %d",k,len);k=AW_GemsImport(blob,len);AW_GemAt(0,gem,sizeof(gem),&creature);
     P(" import %d %s soul %d",k,gem,AW_GemSoul(0));k=AW_GemRemove(0);P(" removed %d left %d\n",k,AW_GemCount());AW_GemsReset();}
    /* places revealed by ShowMap: once each (any case), through a save */
    {unsigned char blob[512];int k,len;
     k=AW_RevealedAdd("Tel Fyr");k+=AW_RevealedAdd("TEL FYR");k+=AW_RevealedAdd("Gnaar Mok");
     len=AW_RevealedExport(blob,sizeof(blob));AW_RevealedReset();
     P("revealed %d count",k);k=AW_RevealedImport(blob,len);P(" %d export %d import %d %s %s\n",AW_RevealedCount(),len,k,
       AW_RevealedAt(0),AW_RevealedAt(1));AW_RevealedReset();}
    /* slice 6 (CELL-CHANGES-59, ACTOR-STATE-POOL-LIMITS-54): every record changed up to AW_ACTOR_POOL_MAX (the game:
     * 3,437 actor bases, 2,673 NPCs placed), half killed, half hurt, a third hostile, each with an item change; the
     * next one refused; the records as "AWAR" and the dead counts alone as AWAS1, read back after an emptied pool;
     * refusals add nothing */
    {static unsigned char big[2200000];int k,m,changed,live,rat=AW_ActorFind("test_rat");aw_actor_t *x;
     AW_ActorStateImport(NULL,0);
     for(i=0;i<AW_ACTOR_POOL_MAX;i++){x=AW_ActorGet(20000+(uint32_t)i,i%2?row:rat,1);if(!x)break;
         if(i%2)AW_ActorModCurrent(x,AWA_HEALTH,-7);else AW_ActorKill(x);
         if(!AW_ActorAddItem(x,ring,1))break;
         if(i%3==0)AW_ActorSetStat(x,AWA_FIGHT,100);}
     k=AW_ActorGet(99999,row,1)==NULL;live=AW_ActorStateLive(&changed);
     m=AW_ActorStateExportRecords(big,sizeof(big));n=AW_ActorStateExportCounts(save,sizeof(save));
     P("big %d full %d live %d changed %d records %d need %d counts %d",i,k,live,changed,m,AW_ActorStateExportRecords(NULL,0),n);
     k=AW_ActorStateImport(save,n);live=AW_ActorStateLive(&changed);P(" emptied %d live %d deadcount %d",k,live,AW_ActorDeadCount(rat));
     k=AW_ActorStateImportRecords(big,m);live=AW_ActorStateLive(&changed);
     x=AW_ActorGet(20001,row,0);
     P(" import %d live %d changed %d health %.0f",k,live,changed,x?AW_ActorStat(x,AWA_HEALTH):-1.0f);
     x=AW_ActorGet(20000,rat,0);
     P(" dead %.0f fight %.0f ring %d",x?AW_ActorStat(x,AWA_DEAD):-1.0f,x?AW_ActorStat(x,AWA_FIGHT):-1.0f,x?AW_ActorItemCount(x,ring):-1);
     x=AW_ActorGet(20000+AW_ACTOR_POOL_MAX-1,row,0);P(" last %d",x!=NULL);
     /* refusals: cut, a longer block, a wrong version, no records, a block that is not AWAR; nothing added */
     AW_ActorStateImport(save,n);
     k=AW_ActorStateImportRecords(big,m-1)+AW_ActorStateImportRecords(big,m+1);
     big[4]=2;k+=AW_ActorStateImportRecords(big,m);big[4]=1;
     memcpy(save+4096,"AWAR\1\0\0\0\0\0\0\0",12);k+=AW_ActorStateImportRecords(save+4096,12);
     k+=AW_ActorStateImportRecords(save,n);
     live=AW_ActorStateLive(&changed);P(" refused %d live %d",k,live);
     /* one bad record among good ones (an item past the table) refuses the whole block */
     big[12+186+182]=0xFF;big[12+186+183]=0xFF;k=AW_ActorStateImportRecords(big,m);live=AW_ActorStateLive(&changed);
     P(" badrecord %d live %d empty %d\n",k,live,AW_ActorStateImportRecords(NULL,0));}
    /* v0.0.61 (PLAYER-CASTING-59): an enchantment found by id (any case, again from the kept answers), its row, the
     * sword's link, the NPC's held weapon's enchantment, the spells' flags and the starting spells */
    {aw_enchant_t en;aw_item_t it;aw_start_settings_t set;int k,item,rows[8],m,
         e1=AW_ActorEnchantFind("STRIKE_EN"),e2=AW_ActorEnchantFind("strike_en"),e3=AW_ActorEnchantFind("no_such");
     k=AW_ActorEnchant(e1,&en);AW_ActorItem(sword,&it);
     P("ench %d %d %d %d type %d flags %d cost %.1f charge %.1f n %d %d %d %u %u item %d",AW_ActorEnchantCount(),e1,e2,
       e3==AW_ACTOR_NONE,en.type,en.flags,en.cost,en.charge,en.n,k,en.effect[0].range,en.effect[0].magnitude_min,
       en.effect[0].magnitude_max,it.enchant);
     k=AW_ActorWeaponEnchant(AW_ActorFind("fixed_npc"),&item);
     P(" npc %d %d",k,item==sword);
     P(" none %d",AW_ActorWeaponEnchant(AW_ActorFind("test_rat"),&item)==AW_ACTOR_NONE);
     P(" flags %d %d",AW_ActorSpellFlags(spell),AW_ActorSpellFlags(auto_spell));
     m=AW_ActorStartSpells(&set,rows,8);
     P(" start %d %.1f %.1f %d %d %.1f",m,set.magicka_mult,set.chance,set.max,set.skill_min,set.cost_mult);
     for(k=0;k<m;k++)P(" %d:%d",rows[k],AW_ActorSpellFlags(rows[k]));
     P("\n");}
    /* RESIST-NORMAL-WEAPONS-61 (v0.0.62): the always-active spells' magnitudes: the rat's ability 100 + its disease's
     * 5 = 105 resist, the disease's weakness 30 (the middle of 20-40), its castable spell and power not counted; the
     * immunity removed by a script leaves 5; the NPC with no such spell 0 */
    {aw_actor_t *x;int rat=AW_ActorFind("test_rat"),immunity=atoi(argv[7]);
     AW_ActorStateImport(NULL,0);x=AW_ActorGet(31337,rat,1);
     P("passive %.0f %.0f %.0f",AW_ActorPassiveMagnitude(x,98),AW_ActorPassiveMagnitude(x,36),AW_ActorPassiveMagnitude(x,14));
     AW_ActorRemoveSpell(x,immunity);
     P(" removed %.0f npc %.0f none %.0f",AW_ActorPassiveMagnitude(x,98),
       AW_ActorPassiveMagnitude(AW_ActorGet(31338,row,1),98),AW_ActorPassiveMagnitude(NULL,98));
     /* UNDERWATER-BREATH-62: the NoMagnitude ability (stored magnitude 0) counts 1 */
     P(" water breathing %.0f\n",AW_ActorPassiveMagnitude(x,0));}
    /* UNDERWATER-BREATH-62 (v0.0.63-dev5 release check): an ability added to the player's record (the race's) is gone
     * after a load, since the player's record is not in the actor block; the pool's epoch moves so the host adds it
     * again */
    {aw_actor_t *p;unsigned long e0;int imm=atoi(argv[7]);
     AW_ActorStateImport(NULL,0);p=AW_ActorPlayer();AW_ActorAddSpell(p,imm);e0=AW_ActorStateEpoch();
     P("player ability %d",AW_ActorHasSpell(p,imm));
     n=AW_ActorStateExport(save,sizeof(save));AW_ActorStateImport(save,n>0?n:0);p=AW_ActorPlayer();
     P(" after load %d epoch moved %d\n",AW_ActorHasSpell(p,imm),AW_ActorStateEpoch()!=e0);}
    AW_ActorStateClose();free(file);return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, raw, _ = build()
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-actorstate-'))
        (cls.tmp / 'a.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(cls.tmp / 'h.c'), str(src / 'aw_actorstate.c'), '-o', str(cls.tmp / 'h')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        t = cls.prog.actors
        args = [str(t.item_index['test_sword']), str(t.item_index['test_ring']), str(t.spell_index['test spell']),
                str(t.spell_index['other spell']), str(t.spell_index['auto spell']), str(t.spell_index['rat immunity'])]
        r = subprocess.run([str(cls.tmp / 'h'), str(cls.tmp / 'a.awm'), *args], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.out = r.stdout.splitlines()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_lookup_and_base(self):
        self.assertEqual(self.out[0], 'open 1 count 4')
        self.assertEqual(self.out[1], 'find 1 3 65535 0')
        self.assertEqual(self.out[2], 'get 50 12 50 100 lvl 5 fight 90')
        self.assertEqual(self.out[3], 'same 1')

    def test_stats_follow_openmw(self):
        self.assertEqual(self.out[4:7], ['mod 100', 'mod 0', 'set 150'])
        self.assertEqual(self.out[7:13], ['health 30 ratio 0.60', 'health 50', 'health 60', 'magicka 5',
                                          'fatigue -50', 'magicka 0'])
        self.assertEqual(self.out[13], 'ai 100 25')

    def test_inventory(self):
        self.assertEqual(self.out[14], 'items 2 1 35')                  # gold: the record's 30 and the 5 carried
        self.assertEqual(self.out[15], 'ring 4')
        self.assertEqual(self.out[16], 'removed 2 sword 0 equipped 0')
        self.assertEqual(self.out[17:19], ['ring 5', 'ring 5'])         # -65535 is 1 (unsigned 16 bits); 0 nothing

    def test_spells(self):
        self.assertEqual(self.out[19:22], ['spells 1 0', 'spells 0 1 n 2', 'spells 1 n 1'])

    def test_creature_and_death(self):
        self.assertEqual(self.out[22:24], ['skill 5', 'skill 5'])        # magic skill; creatures' skills not set
        self.assertEqual(self.out[24], 'dead 1 ondeath 1 0 count 1')

    def test_saved_games(self):
        self.assertTrue(int(self.out[25].split()[1]) > 0)
        self.assertEqual(self.out[26], 'import 1')
        self.assertEqual(self.out[27], 'after 150 60 ring 5 spells 1 1 count 1')
        self.assertEqual(self.out[28:30], ['small -1', 'bad 0'])

    def test_spell_info_and_held_spells(self):
        # ASPC read back natively: the name and cost; a fresh record of the NPC holds its base list (its two spells
        # and the race power)
        t = self.prog.actors
        self.assertEqual(self.out[30], 'aspc 1 0 Spell of Testing 5')
        want = [t.spell_index[k] for k in ('test spell', 'auto spell', 'race power')]
        self.assertEqual(self.out[31], 'held 3 ' + ' '.join(map(str, want)))

    def test_stock(self):
        # a merchant's stock for Barter: its things with counts, gold aside (a fresh record: the base list)
        self.assertEqual(self.out[32], 'stock 3 test_sword:2 test_cuirass:1 test_ring:1')

    def test_sold_things_survive_a_save_and_are_bought_back(self):
        # BARTER-SOLD-ITEM-LOST-58: sell twice (any case) to merchant 1234 and once to 77, save, reopen, buy back
        self.assertEqual(self.out[36], 'sold 3 export 38 after-reset 0 import 38 count 2 1234:misc_vase:2 77:misc_vase:1 '
                                       'back 1 1 0 left 1 bad -1 0')

    def test_magic_and_spell_effects(self):
        # AMGE 14 (school 2, base 5.0), an effect index the master lacks, and the autocalculated spell's one effect
        self.assertEqual(self.out[37], 'mgef 1 0 5.0 2 Fire Damage none 0 effects 1 14 -1 2 0 5 10 20')

    def test_sold_things_are_bounded(self):
        # 1025 kinds: all taken, the list stays at 1024, the oldest (thing_0) forgotten
        self.assertEqual(self.out[38], 'cap 1024 ok 1 count 1024 first thing_1')

    def test_made_things_survive_a_save_and_are_bounded(self):
        # 5 + 33 + 2 x 14 + 5 + 82 + 14 = 167 bytes; 64 spells at most (63 more fit, 7 of 70 refused); a bad count refused
        self.assertEqual(self.out[39], 'made 0 export 167 import 167 spells 1 items 1 My Fire 2 30 steel_longsword Biter 40 '
                                       'full 7 bad -1 0')

    def test_soul_gems(self):
        # the rat's soul (its record's soul, 10) read through the creature row; 5 + 1 + 18 + 2 = 26 bytes
        self.assertEqual(self.out[40], 'gem 0 export 26 import 26 misc_soulgem_petty soul 10 removed 1 left 0')

    def test_revealed_places(self):
        # ShowMap's places: kept once (any case), 5 + 8 + 10 = 23 bytes saved
        self.assertEqual(self.out[41], 'revealed 3 count 2 export 23 import 23 Tel Fyr Gnaar Mok')

    def test_pool(self):
        self.assertEqual(self.out[33], 'pool %d evicted 10' % (128 + 10))
        # ACTOR-STATE-POOL-LIMITS-54: 128 changed records and one more: a second block, not a refusal
        self.assertEqual(self.out[34], 'changed 128 full 0')
        self.assertTrue(self.out[35].startswith('player 1 resident '))
        self.assertLess(int(self.out[35].split()[3]), 2 * 128 * 300 + 4000)

    def test_enchantments_and_starting_spells_natively(self):
        # PLAYER-CASTING-59: two enchantments; strike_en is row 1 by any case (the second ask from the kept answers),
        # an unknown id none; type 1, cost 4, charge 100, its touch Fire Damage 3-6; the sword names it, so does the
        # NPC holding it, the rat holds no weapon; flags of a plain and an autocalculated spell; three starting spells
        t = self.prog.actors
        start = ' '.join('%d:%d' % (t.spell_index[k], f) for k, f in (('start fire', 2), ('start always', 6), ('start pricey', 2)))
        self.assertEqual(self.out[43], 'ench 2 1 1 1 type 1 flags 0 cost 4.0 charge 100.0 n 1 1 1 3 6 item 1 npc 1 1 none 1 '
                                       'flags 0 1 start 3 1.0 50.0 100 70 0.5 ' + start)

    def test_always_active_spells_magnitudes(self):
        # RESIST-NORMAL-WEAPONS-61 (v0.0.62, OpenMW 0.51 activespells.cpp): abilities, blights, diseases and curses of
        # the actor's list act always (the ability's 100 + the disease's 5; the disease's weakness 30, the middle of
        # 20-40); a castable spell and a power only when cast; a removed ability no longer counts; no record, nothing
        self.assertEqual(self.out[44], 'passive 105 30 0 removed 5 npc 0 none 0 water breathing 1')

    def test_a_load_empties_the_player_record_and_moves_the_epoch(self):
        # UNDERWATER-BREATH-62 (v0.0.63-dev5): the race's ability added to the player is gone after a load; the
        # epoch tells the host to add the character's spells again
        self.assertEqual(self.out[45], 'player ability 1 after load 0 epoch moved 1')

    def test_pool_at_the_games_counts(self):
        # CELL-CHANGES-59 slice 6: 8,192 changed records (the game: 3,437 actor bases, 2,673 NPCs placed), each with an
        # item change: 12 + 8,192 x (182 + 4) bytes of AWAR; the dead counts alone 10 + 4; an emptied pool takes them
        # back whole; every refusal adds nothing; one bad record refuses the block
        self.assertEqual(self.out[42], 'big 8192 full 1 live 8192 changed 8192 records 1523724 need 1523724 counts 14 '
                                       'emptied 1 live 0 deadcount 4096 import 1 live 8192 changed 8192 health 43 '
                                       'dead 1 fight 100 ring 1 last 1 refused 0 live 0 badrecord 0 live 0 empty 1')


if __name__ == '__main__':
    unittest.main()
