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
    assert(AW_MoveSettingIndex("fminwalkspeed")==0 && AW_MoveSettingIndex("fFatigueMult")==29 &&
           AW_MoveSettingIndex("fFallAcroMult")==AW_MOVE_SETTING_COUNT-1);
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

    /* ENCUMBRANCE-INCOMPLETE-61: every term at a load, by hand from OpenMW 0.51 (actor.cpp getEncumbrance, npc.cpp
     * getCapacity / getWalkSpeed / getRunSpeed / getMaxSpeed / getJump, actor.hpp getSwimSpeedImpl, character.cpp
     * fatigue, physicssystem.cpp handleJump) with the settings as Morrowind.esm has them (checked 5 November 2026:
     * the 30 values of AW_MoveSettingsDefault equal the master's GMSTs). Strength 60: capacity 300. */
    in.running=0;in.godmode=0;in.sneaking=0;in.swimming=0;in.levitate=0;in.levitation_enabled=0;
    in.speed=50;in.athletics=35;in.acrobatics=15;in.strength=60;in.fatigue=in.fatigue_max=200;
    /* exactly at the limit (normalized 1): still moving, at 1 - 0.3 of the speed */
    in.carried=300;assert(near(AW_MoveEncumbrance(&s,&in),1));
    assert(near(AW_MoveWalkSpeed(&s,&in),105));                  /* 150 x (1 - 0.3 x 1) */
    assert(near(AW_MoveRunSpeed(&s,&in),220.5f));                /* 105 x (0.35 x 1 + 1.75) */
    assert(near(AW_MoveMaxSpeed(&s,&in),105));
    in.swimming=1;assert(near(AW_MoveMaxSpeed(&s,&in),56.175f)); /* 105 x (0.5 + 0.35 x 0.1) */
    in.swimming=0;
    /* the jump's load term 0.5 + 1 x (1 - 1) = 0.5: (128 + 1) x 0.5 x 1.25 + 8.96 x 69.99125, / 3 */
    assert(fabs(AW_MoveJumpVelocity(&s,&in)-(129*.5f*1.25f+627.1216f)/3)<.01f);
    in.running=1;assert(near(AW_MoveFatigueRate(&s,&in),7));     /* fFatigueRunBase 5 + 1 x fFatigueRunMult 2 */
    in.sneaking=1;assert(near(AW_MoveFatigueRate(&s,&in),3));    /* 1.5 + 1 x 1.5 */
    in.sneaking=0;assert(near(AW_MoveJumpFatigue(&s,&in),5));    /* 5 + min(1, n) x fFatigueJumpMult 0 */
    in.running=0;
    /* Burden adds, Feather takes away (not below 0): 200 + 100 = 300 still moves; - 50 Feather = 250 */
    in.carried=200;in.burden=100;assert(near(AW_MoveEncumbrance(&s,&in),1) && AW_MoveMaxSpeed(&s,&in)>0);
    in.feather=50;assert(near(AW_MoveEncumbrance(&s,&in),250/300.0f));
    assert(near(AW_MoveWalkSpeed(&s,&in),150*(1-.3f*250/300.0f)));
    in.feather=500;assert(AW_MoveEncumbrance(&s,&in)==0);       /* floored at 0 */
    in.feather=0;in.burden=0;
    /* over the limit by a hundredth: no movement, no jump, no running cost; the jump cost stays 5 */
    in.carried=300.01f;assert(AW_MoveMaxSpeed(&s,&in)==0 && AW_MoveJumpVelocity(&s,&in)==0);
    in.running=1;assert(AW_MoveFatigueRate(&s,&in)==0 && near(AW_MoveJumpFatigue(&s,&in),5));
    in.running=0;
    /* DBG-NOBURDEN-62: the no-burden mode: 10 times the capacity carried, with Burden, is no load in any rule: the
     * unloaded walk 150 and run 150 x 2.1, the unloaded jump, the run costs fFatigueRunBase 5 only */
    {aw_move_inputs_t nb=in;
     nb.carried=3000;nb.burden=200;nb.feather=10;assert(AW_MoveMaxSpeed(&s,&nb)==0);
     AW_MoveNoBurden(&nb);
     assert(AW_MoveEncumbrance(&s,&nb)==0 && near(AW_MoveWalkSpeed(&s,&nb),150) && near(AW_MoveMaxSpeed(&s,&nb),150));
     nb.running=1;assert(near(AW_MoveRunSpeed(&s,&nb),315) && near(AW_MoveFatigueRate(&s,&nb),5));
     nb.running=0;assert(fabs(AW_MoveJumpVelocity(&s,&nb)-(129*1.5f*1.25f+627.1216f)/3)<.01f);
     assert(near(AW_MoveCapacity(&s,&nb),300) && AW_MOVE_NOBURDEN_SHOWN==999999.0f);
     AW_MoveNoBurden(NULL);}
    /* levitation with half the load: (5 + 0.01 x (50 + 10) x 295) x (1 - 0.3 x 0.5) */
    in.carried=150;in.levitate=10;in.levitation_enabled=1;assert(near(AW_MoveMaxSpeed(&s,&in),182*.85f));
    in.levitate=0;in.levitation_enabled=0;in.carried=0;

    /* Falls (SCRIPTED-EVENT-FALLING-MAGE-61), by hand from OpenMW 0.51 character.cpp getFallDamage with Morrowind.esm's
     * fFallDamageDistanceMin 400, fFallDistanceBase 0, fFallDistanceMult 0.07, fFallAcroBase 0.25, fFallAcroMult 0.01
     * (read from the master on 7 November 2026). */
    assert(s.fFallDamageDistanceMin==400 && s.fFallDistanceBase==0 && near(s.fFallDistanceMult,.07f) &&
           s.fFallAcroBase==.25f && near(s.fFallAcroMult,.01f));
    assert(AW_MoveFallDamage(&s,399.9f,0,0)==0);                     /* below the minimum: nothing */
    assert(AW_MoveFallDamage(&s,400,0,0)==0);                        /* at it: (0 + 0.07 x 0) x 1.25 */
    assert(near(AW_MoveFallDamage(&s,1400,0,0),87.5f));              /* 0.07 x 1000 x (0.25 + 0.01 x 100) */
    /* Acrobatics 15: (1400 - 400 - 22.5) x 0.07 x (0.25 + 0.85) = 75.2675 */
    assert(near(AW_MoveFallDamage(&s,1400,15,0),75.2675f));
    /* a Jump magnitude of 20 takes 20 more units off: (977.5 - 20) x 0.07 x 1.1 */
    assert(near(AW_MoveFallDamage(&s,1400,15,20),73.7275f));
    assert(AW_MoveFallDamage(&s,500,100,0)==0);                       /* Acrobatics 100 absorbs 150 units: 0 left */
    /* The falling mage: about 2,464 units from his platform to the ground, Acrobatics 15 (a level 6 enchanter, read
     * from his record by the actor table in game): (2464 - 400 - 22.5) x 0.07 x 1.1 = 157.195; at full fatigue
     * (term 1.25) the health lost is 157.195 x (1 - 0.3125) = 108.07, far over his 5 */
    assert(near(AW_MoveFallDamage(&s,2464,15,0),157.1955f));
    assert(near(AW_MoveFallHealthLoss(157.1955f,1.25f),108.0719f));
    assert(AW_MoveFallHealthLoss(0,1.25f)==0);
    /* knocked down when the damage passes Acrobatics x the fatigue term */
    assert(AW_MoveFallKnockdown(20,15,1.25f) && !AW_MoveFallKnockdown(18,15,1.25f) && !AW_MoveFallKnockdown(0,0,1));
    /* Slowfall (physicssystem.cpp): 1 - magnitude x 0.005, clamped */
    assert(AW_MoveSlowFallFactor(0)==1 && near(AW_MoveSlowFallFactor(10),.95f) && near(AW_MoveSlowFallFactor(100),.5f));
    assert(AW_MoveSlowFallFactor(300)==0 && AW_MoveSlowFallFactor(-5)==1);
    /* a step (movementsolver.cpp): gravity x step off the vertical speed, then the factor while falling */
    assert(near(AW_MoveFallStep(0,AW_MOVE_PHYSICS_STEP,AW_MOVE_GRAVITY,1),-AW_MOVE_GRAVITY/60));
    assert(near(AW_MoveFallStep(0,AW_MOVE_PHYSICS_STEP,AW_MOVE_GRAVITY,.5f),-AW_MOVE_GRAVITY/120));
    assert(near(AW_MoveFallStep(100,AW_MOVE_PHYSICS_STEP,AW_MOVE_GRAVITY,.5f),100-AW_MOVE_GRAVITY/60));   /* rising: kept */
    {   /* with Slowfall 10 the speed settles where v = 0.95 (v - g/60): -0.95 x 10.452 / 0.05 = -198.6 units/s */
        float v=0;int i;
        for(i=0;i<600;i++)v=AW_MoveFallStep(v,AW_MOVE_PHYSICS_STEP,AW_MOVE_GRAVITY,AW_MoveSlowFallFactor(10));
        assert(fabs(v+.95f*AW_MOVE_GRAVITY/60/.05f)<.5f);
    }

    /* A script's angles (MWSCRIPT-SMALL-FUNCTIONS-62; OpenMW 0.51 OpGetAngle / OpSetAngle / rotateObject): an object
     * placed with the original's z rotation 4.5 radians stands at Quake yaw -257.83, so GetAngle Z reads 257.83 back
     * as placed; an actor's reads within -180..180 (-102.17), its x within -90..90; y is the roll */
    {
        float q[3]={10,-257.8310f,-30},out;
        assert(near(AW_MoveScriptAngle(q,'z',0),257.831f) && near(AW_MoveScriptAngle(q,'Z',1),-102.169f));
        assert(near(AW_MoveScriptAngle(q,'x',0),10) && near(AW_MoveScriptAngle(q,'y',1),-30));
        q[0]=200;assert(near(AW_MoveScriptAngle(q,'x',0),200) && near(AW_MoveScriptAngle(q,'x',1),-90));
        q[0]=100;assert(near(AW_MoveScriptAngle(q,'x',1),90));
        q[1]=-720.5f;assert(near(AW_MoveScriptAngle(q,'w',1),.5f));    /* w is z; whole turns off */
        assert(AW_MoveScriptAngle(q,'q',0)==0);
        /* SetAngle: z 90 is Quake yaw -90 (the doors' "SetAngle Z 90"); 270 on an actor turns to -90, so yaw 90 */
        assert(AW_MoveScriptAngleSet('z',90,0,&out)==1 && near(out,-90));
        assert(AW_MoveScriptAngleSet('Z',270,1,&out)==1 && near(out,90));
        assert(AW_MoveScriptAngleSet('x',45,0,&out)==0 && near(out,45));
        assert(AW_MoveScriptAngleSet('x',135,1,&out)==0 && near(out,90));
        assert(AW_MoveScriptAngleSet('v',-20,0,&out)==2 && near(out,-20));
        assert(AW_MoveScriptAngleSet('a',1,0,&out)==-1);
        /* GetAngle reads back what SetAngle wrote */
        q[0]=q[1]=q[2]=0;AW_MoveScriptAngleSet('z',123.5f,0,&q[1]);assert(near(AW_MoveScriptAngle(q,'z',0),123.5f));
    }
    /* Move along the object's own axes: x forward, y left (minus right), z up */
    {
        float f[3]={0,1,0},r[3]={1,0,0},u[3]={0,0,1},d[3];
        assert(AW_MoveScriptLocal(f,r,u,'x',5,d) && d[0]==0 && d[1]==5 && d[2]==0);
        assert(AW_MoveScriptLocal(f,r,u,'Y',5,d) && d[0]==-5 && d[1]==0);
        assert(AW_MoveScriptLocal(f,r,u,'z',-2,d) && d[2]==-2 && d[0]==0);
        assert(!AW_MoveScriptLocal(f,r,u,'w',5,d) && d[0]==0 && d[1]==0 && d[2]==0);
    }
    return 0;
}
