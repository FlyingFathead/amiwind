# SPDX-License-Identifier: GPL-3.0-only
"""NPCs drown (ACTOR-DROWNING-NOT-CARRIED-67, v0.0.68; engine/aga/src/aw_drown.h).

OpenMW 0.51 runs updateDrowning (apps/openmw/mwmechanics/actors.cpp 989-1047) for every NPC in the actors processing
range (line 1663: NPCs only, creatures never drown): submerged (World::isSubmerged: the point 1/fSwimHeightScale of its
height over its feet under water) and without Water Breathing, its breath falls from fHoldBreathTime; at 0 it loses
fSuffocationDamage health a second. Before, only the player drowned here, so the flood that drowns the Black Dart gang
in Old Mournhold: Temple Sewers West left them standing.

Checked here: the pure rules natively (the breath, the damage, Water Breathing, the head point, which residents are
taken, the fixed table, the saved fact), and the wiring: every server frame after the player's breath, only in a room
with the water flag, a resident taken by its fight state and never by its edict's own health field (seen in play
2026-11-20: no NPC was ever checked), the
health through the NPC's own record and the scripts' death path, the breath kept in the world change list, New Game's
reset, the status lines, the build lists."""
import os
from pathlib import Path
import re
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tests', ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, start):
    part = text[text.index(start):]
    return part[:part.index('\n}\n')]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class DrownRuleTests(unittest.TestCase):
    def test_breath_damage_table_and_fact(self):
        native.NativeSourceTests().compile_run('aga_drown_rules_test.c', [SRC / 'aw_drown_rules.c',
                                                                          SRC / 'aw_breath_rules.c'], cflags=UBSAN)


class DrownWiringTests(unittest.TestCase):
    def test_every_frame_after_the_players_breath(self):
        breath = code('aw_breath.c')
        physics = body(breath, 'void AW_BreathPhysics(void) {')
        self.assertIn('breath_player();', physics)
        self.assertIn('AW_DrownPhysics();', physics)
        self.assertIn('AW_DrownInit();', body(breath, 'void AW_BreathInit(void) {'))
        self.assertIn('AW_DrownStatus();', body(breath, 'static void breath_command(void) {'))
        # the same settings as the player's (combat/settings.txt "breath" lines or the original's)
        self.assertIn('void AW_BreathSettingsGet(aw_breath_settings_t *out) {', breath)

    def test_npcs_only_in_a_room_with_water(self):
        drown = code('aw_drown.c')
        physics = body(drown, 'void AW_DrownPhysics(void)\n{')
        self.assertIn('!AW_MwscriptRoomWater()', physics)
        self.assertIn('"aw_npc"', body(drown, 'static int npc(edict_t *e)\n{'))
        self.assertNotIn('aw_creature', drown)                 # creatures never drown (OpenMW actors.cpp 1663)
        head = body(drown, 'static int under_water(const edict_t *e)\n{')
        self.assertIn('p[2]+=e->v.mins[2]+AW_DrownHeadHeight(e->v.maxs[2]-e->v.mins[2]);', head)
        self.assertIn('SV_PointContents(p)', head)
        self.assertIn('AW_EFFECT_WATER_BREATHING', drown)
        # a new map: the rows' edicts are gone
        self.assertIn('if(table_map!=(void *)sv.worldmodel){table_map=(void *)sv.worldmodel;table.count=0;}', physics)
        self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc|Cache_Alloc)\s*\(', drown))
        host = code('aw_mwhost.c')
        self.assertIn('int AW_MwscriptRoomWater(void){return water_table && map_room && room_water;}', host)

    def test_a_resident_is_taken_by_its_fight_state_not_its_edict_health(self):
        # ACTOR-DROWNING-NOT-CARRIED-67 seen again in play (2026-11-20, the water journey on the build of 5986ff997):
        # the check took an NPC only with e->v.health over 0; resident NPCs never set that field (their health is the
        # actor record's and the fight sheet's), so in Temple Sewers West aw_breath read 0 NPC checks in 11870 frames
        # and the Black Dart gang stood under the flood alive
        drown = code('aw_drown.c')
        taken = body(drown, 'static int npc(edict_t *e)\n{')
        self.assertNotIn('v.health', taken)
        self.assertIn('AW_DrownTakes(AW_CombatSlotState(e,NULL),e->v.modelindex!=0)', taken)
        self.assertIn('#include "aw_actors.h"', drown)
        # the residents' spawn really leaves the field alone (qc/world.qc aw_npc and aw_npc_floor set no health)
        qc = (ROOT / 'engine' / 'aga' / 'qc' / 'world.qc').read_text(encoding='utf-8')
        spawn = qc[qc.index('void() aw_npc_floor = {'):qc.index('void() aw_corpse = {')]
        self.assertNotIn('self.health', spawn)

    def test_the_health_goes_through_the_record_and_the_death_path(self):
        host = code('aw_mwhost.c')
        hurt = body(host, 'int AW_MwscriptActorHurt(edict_t *e,float loss){')
        self.assertIn("if(!a || a->kind!=0 || a->reference==AW_ACTOR_PLAYER_REF)return -1;", hurt)
        self.assertIn('f=fighter_of(e);from_fighter(a,f);', hurt)
        self.assertIn('AW_ActorModCurrent(a,AWA_HEALTH,-loss);', hurt)
        self.assertIn('script_death(a,e,was_dead,before);', hurt)
        self.assertIn('to_fighter(a,f);', hurt)
        drown = code('aw_drown.c')
        self.assertIn('AW_MwscriptActorHurt(e,loss)', drown)

    def test_the_breath_is_saved_and_new_game_clears_it(self):
        drown = code('aw_drown.c')
        physics = body(drown, 'void AW_DrownPhysics(void)\n{')
        self.assertIn('AW_LedgerFact(&aw_ledger,id,&kept)', physics)
        self.assertIn('AW_LedgerFactSet(&aw_ledger,id,(int32_t)AW_DrownFactValue(table.row[row].left));', physics)
        self.assertIn('AW_LedgerFactSet(&aw_ledger,id,(int32_t)AW_DrownFactValue(s.hold));', physics)
        self.assertIn('AW_ResetRegister("breath of NPCs (drowning)",reset_drown,digest_drown);', drown)
        self.assertIn('memset(&table,0,sizeof(table));', body(drown, 'static void reset_drown(int new_game)\n{'))

    def test_the_build_lists(self):
        make = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_drown_rules.c aw_drown.c', make)
        files = (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')
        for path in ('engine/aga/src/aw_drown.c', 'engine/aga/src/aw_drown.h', 'engine/aga/src/aw_drown_rules.c',
                     'tests/aga_drown_rules_test.c', 'tests/test_actor_drowning.py'):
            self.assertIn('"%s"' % path, files)


if __name__ == '__main__':
    unittest.main()
