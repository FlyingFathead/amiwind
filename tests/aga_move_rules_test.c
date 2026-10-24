/* SPDX-License-Identifier: GPL-2.0-or-later
 * The movement rules (engine/aga/src/aw_move_rules.c) against values worked out
 * by hand from OpenMW 0.51 npc.cpp / actor.hpp / actor.cpp / character.cpp /
 * physicssystem.cpp with the original game settings (docs/PLAYER_MOVEMENT.md).
 */
#include <assert.h>
#include <math.h>
#include <string.h>
#include "aw_move.h"

static int near(float a,float b) {return fabs(a-b)<=.001f*(fabs(b)>1?fabs(b):1);}
/* AmiWind units/s for the straight full input: x race weight x 0.25. */
static float units(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    return AW_MoveCurrentSpeed(s,in,1,0)*AW_MOVE_UNIT_SCALE;
}

int main(void) {
    aw_move_settings_t s;aw_move_inputs_t in;
    AW_MoveSettingsDefault(&s);
    assert(AW_MoveSettingIndex("fminwalkspeed")==0 && AW_MoveSettingIndex("fFatigueMult")==AW_MOVE_SETTING_COUNT-1);
    assert(AW_MoveSettingIndex("fCombatDistance")<0 && !AW_MoveSettingSet(&s,"nonsense",1));
    assert(s.fMinWalkSpeed==100 && s.fMaxWalkSpeed==200 && s.fBaseRunMultiplier==1.75f && s.fAthleticsRunBonus==1);
    assert(AW_MOVE_UNIT_SCALE==.25f);

    /* A fresh character: Nord male Barbarian (the direct-start preset, AW_CharacterHors):
     * Speed 40 + 10 (favoured attribute) = 50, Strength 50 + 10 = 60,
     * Athletics 5 + 5 (combat specialization) + 25 (major) = 35, Acrobatics 5 + 10 (minor) = 15,
     * Nord male weight 1.25, nothing carried. */
    memset(&in,0,sizeof in);
    in.speed=50;in.strength=60;in.athletics=35;in.acrobatics=15;in.scale=1.25f;in.fatigue=in.fatigue_max=200;
    assert(near(AW_MoveWalkSpeed(&s,&in),150));            /* 100 + 0.5 x (200 - 100) */
    assert(near(AW_MoveRunSpeed(&s,&in),315));             /* 150 x (1.75 + 0.35) */
    assert(near(units(&s,&in),46.875f));                   /* 150 x 1.25 x 0.25 */
    in.running=1;
    assert(near(units(&s,&in),98.4375f));                  /* 315 x 1.25 x 0.25 */
    /* The old fixed speeds were 120 / 216: 2.56 and 2.19 times these. */
    assert(near(216/units(&s,&in),2.194286f));
    in.running=0;
    assert(near(120/units(&s,&in),2.56f));
    in.swimming=1;
    assert(near(AW_MoveSwimSpeed(&s,&in),80.25f));         /* 150 x (0.5 + 0.35 x 0.1) */
    in.running=1;
    assert(near(AW_MoveMaxSpeed(&s,&in),168.525f));        /* 315 x 0.535 */
    in.swift_swim=100;assert(near(AW_MoveMaxSpeed(&s,&in),337.05f));   /* Swift Swim 100 doubles it */
    in.swift_swim=0;in.swimming=0;

    /* Live stats: the same sheet with Athletics raised to 60, then Speed to 70. */
    in.athletics=60;assert(near(AW_MoveRunSpeed(&s,&in),352.5f));     /* 150 x 2.35 */
    in.speed=70;assert(near(AW_MoveWalkSpeed(&s,&in),170) && near(AW_MoveRunSpeed(&s,&in),399.5f));

    /* A high-athletics character: Speed 100, Athletics 100 (unit race weight). */
    in.speed=100;in.athletics=100;in.scale=1;in.running=0;
    assert(near(units(&s,&in),50));                         /* 200 x 0.25 */
    in.running=1;assert(near(units(&s,&in),137.5f));        /* 550 x 0.25 */
    in.scale=1.25f;assert(near(units(&s,&in),171.875f));    /* Nord male */

    /* Direction and input: a half-pushed stick halves it, strafing x 0.75 (first person:
     * |side| > 2 |forward|), backwards is not strafing. */
    in.speed=50;in.athletics=35;in.running=0;
    assert(near(AW_MoveCurrentSpeed(&s,&in,.5f,0)*AW_MOVE_UNIT_SCALE,23.4375f));
    assert(near(AW_MoveCurrentSpeed(&s,&in,1,1)*AW_MOVE_UNIT_SCALE,35.15625f));
    assert(AW_MoveStrafing(0,1) && AW_MoveStrafing(.4f,1) && !AW_MoveStrafing(.5f,1) && !AW_MoveStrafing(-1,0));
    assert(AW_MoveCurrentSpeed(&s,&in,2,0)==AW_MoveCurrentSpeed(&s,&in,1,0));

    /* Encumbrance: capacity 5 x Strength 60 = 300; half load slows walking by 15 %;
     * Feather lightens, Burden weighs (not in godmode); over capacity: no movement. */
    assert(near(AW_MoveCapacity(&s,&in),300));
    in.carried=150;assert(near(AW_MoveEncumbrance(&s,&in),.5f) && near(AW_MoveWalkSpeed(&s,&in),127.5f));
    in.feather=150;assert(AW_MoveEncumbrance(&s,&in)==0);
    in.feather=0;in.burden=151;assert(AW_MoveMaxSpeed(&s,&in)==0);
    in.godmode=1;assert(near(AW_MoveMaxSpeed(&s,&in),127.5f));
    in.godmode=0;in.burden=0;in.carried=0;
    in.strength=0;in.carried=1;assert(AW_MoveMaxSpeed(&s,&in)==0);  /* zero capacity carrying anything */
    in.carried=0;assert(AW_MoveMaxSpeed(&s,&in)>0);
    in.strength=60;

    /* Sneaking walks at x 0.75 and never runs. */
    in.sneaking=1;in.running=1;
    assert(near(AW_MoveMaxSpeed(&s,&in),112.5f));
    in.sneaking=0;in.running=0;

    /* States that stop movement. */
    in.knocked=1;assert(AW_MoveMaxSpeed(&s,&in)==0 && AW_MoveJumpVelocity(&s,&in)==0);in.knocked=0;
    in.paralyzed=1;assert(AW_MoveMaxSpeed(&s,&in)==0);in.paralyzed=0;
    in.dead=1;assert(AW_MoveMaxSpeed(&s,&in)==0);in.dead=0;

    /* Levitation (later: no effect yet): (5 + 0.01 x (50 + 10) x 295). */
    in.levitate=10;assert(near(AW_MoveMaxSpeed(&s,&in),150));
    in.levitation_enabled=1;assert(near(AW_MoveMaxSpeed(&s,&in),182));
    in.levitate=0;in.levitation_enabled=0;

    /* Jump (getJump): Acrobatics 15, no load, full fatigue (term 1.25):
     * (128 + 1) x 1.5 x 1.25 = 241.875; + 8.96 x 69.99125 = 869; / 3 = 289.66. */
    assert(near(AW_MoveFatigueTerm(&s,&in),1.25f));
    assert(fabs(AW_MoveJumpVelocity(&s,&in)-289.666f)<.01f);
    in.acrobatics=100;  /* 128 + (50/15)^4 + 3 x 50 x 4 = 851.457; x 1.5 x 1.25; + 627.12; / 3 */
    assert(fabs(AW_MoveJumpVelocity(&s,&in)-(851.4568f*1.875f+627.1216f)/3)<.05f);
    in.acrobatics=15;in.fatigue=0;assert(near(AW_MoveFatigueTerm(&s,&in),.75f));
    in.fatigue=200;

    /* Fatigue cost per second of full input: walking free, running 5 (+ 2 x load), swimming 2.5 / 7,
     * sneaking 1.5 (+ 1.5 x load); a jump 5; nothing in godmode or over capacity. */
    assert(AW_MoveFatigueRate(&s,&in)==0);
    in.running=1;assert(near(AW_MoveFatigueRate(&s,&in),5));
    in.carried=150;assert(near(AW_MoveFatigueRate(&s,&in),6));
    in.swimming=1;assert(near(AW_MoveFatigueRate(&s,&in),7));
    in.running=0;assert(near(AW_MoveFatigueRate(&s,&in),2.5f));
    in.swimming=0;in.sneaking=1;assert(near(AW_MoveFatigueRate(&s,&in),2.25f));
    in.sneaking=0;in.running=1;in.godmode=1;assert(AW_MoveFatigueRate(&s,&in)==0 && AW_MoveJumpFatigue(&s,&in)==0);
    in.godmode=0;in.carried=400;assert(AW_MoveFatigueRate(&s,&in)==0);
    in.carried=0;assert(near(AW_MoveJumpFatigue(&s,&in),5));
    /* A loss stops at 0; an already negative fatigue (knocked out) keeps falling. */
    assert(AW_MoveFatigueAfter(10,1)==9 && AW_MoveFatigueAfter(3,5)==0 && AW_MoveFatigueAfter(-2,1)==-3);
    assert(AW_MoveFatigueAfter(4,0)==4);
    return 0;
}
