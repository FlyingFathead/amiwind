# SPDX-License-Identifier: GPL-3.0-only
"""NPC-NO-SPELLCASTING-65: fighters cast the spells they know. The choice between the weapon and each spell (OpenMW 0.51
aicombataction.cpp prepareNextAction, spellpriority.cpp, weaponpriority.cpp) is host-built (aga_spell_ai_test.c); the
engine wiring (the choice each second, the cast from its range with the spellcast group, the look held to the release,
the delivery as the player's, the switch) is checked in the source."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


class NpcSpellcasting(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
    @unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
    def test_the_choice_between_weapon_and_spell(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-spellai-'))
        try:
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                    '-fno-sanitize-recover=all', '-I' + str(SRC), str(ROOT / 'tests/aga_spell_ai_test.c'),
                                    str(SRC / 'aw_cast_rules.c'), str(SRC / 'aw_effects.c'), '-lm', '-o', str(tmp / 't')],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(tmp / 't')], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('spell ai:', run.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_fight_casts(self):
        combat, cast = code('aw_combat.c'), code('aw_cast.c')
        # the switch, on by default, and its console word
        self.assertIn('static int rules[AW_RULE_COUNT]={1,1,1,1};', combat)
        self.assertIn('enum {AW_RULE_FLEE,AW_RULE_SOUNDS,AW_RULE_CONTACT,AW_RULE_SPELLS,AW_RULE_COUNT};', code('aw_combat.h'))
        self.assertIn('!Q_strcasecmp(a,"spells")', combat)
        self.assertIn('spells on/off', (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8'))
        # the choice each second against the weapon, by the masters' settings
        self.assertIn('r=AW_SpellAiRateSpell(&c,row,type,e,m,ne,chance);', combat)
        self.assertIn('best_rating=AW_SpellAiRateWeapon(', combat)
        self.assertIn('c.spell_mult=3;c.range_spell_mult=5;', combat)
        self.assertIn('if(AW_EffectHarmful(e[k].effect))m.flags|=AW_MGEF_HARMFUL;', combat)
        # the cheaper version: the spells are read once per fight (aga_combat_test.c counts the reads)
        self.assertIn('if(!s->spells_cached)cache_spells(s,a);', combat)
        choose = combat[combat.index('static void choose_spell('):combat.index('static int start_cast(')]
        for read in ('AW_ActorSpellEffects(', 'AW_ActorSpellFlags(', 'AW_ActorMagicEffect(', 'AW_ActorSpells('):
            self.assertNotIn(read, choose)
        # the cast: magicka at the start, the spellcast group, the look held to the release, the roll and the delivery
        # NPC-CAST-MAGICKA-NOT-PAID-66: the stat is magicka (stat 1 is Intelligence, which ModCurrent ignores)
        self.assertIn('AW_ActorModCurrent(a,AWA_MAGICKA,-(float)mcost);', combat)
        self.assertNotIn('AW_ActorModCurrent(a,1,', combat)
        self.assertIn('r=AW_AnimKitCast(s->e,variant[range]);', combat)
        self.assertIn('s->cast_look=AW_MagicCastLookStart(NUM_FOR_EDICT(s->e),e[0].effect,range,0);', combat)
        self.assertIn('AW_CastActorRelease(s->e,NULL,s->spell,', combat)
        self.assertIn('AW_MagicCastLookRelease(s->cast_look,ok);', combat)
        self.assertIn('if(s->cast_look)AW_MagicCastLookRelease(s->cast_look,-1);', combat)   # a released slot
        # the delivery: an actor's bolt flies from its eye at the player and lands on the player
        self.assertIn('b->caster=NUM_FOR_EDICT(caster);', cast)
        self.assertIn('AW_MwscriptLand(t==sv_player?NULL:t,b->e,m,b->n,AW_RANGE_TARGET,source)', cast)
        self.assertIn('else if(b->caster>0 && tr.ent==sv_player)', cast)


if __name__ == '__main__':
    unittest.main()
