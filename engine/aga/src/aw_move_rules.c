/* SPDX-License-Identifier: GPL-2.0-or-later
 * The movement rules as pure functions (aw_move.h; tests/aga_move_rules_test.c).
 * Rules from OpenMW 0.51 (files named in aw_move.h); independent code.
 */
#include <math.h>
#include <string.h>
#include "aw_move.h"

static const char *names[AW_MOVE_SETTING_COUNT]={
    "fMinWalkSpeed","fMaxWalkSpeed","fEncumberedMoveEffect","fBaseRunMultiplier","fAthleticsRunBonus",
    "fSwimRunBase","fSwimRunAthleticsMult","fSneakSpeedMultiplier","fEncumbranceStrMult",
    "fMinFlySpeed","fMaxFlySpeed",
    "fJumpAcrobaticsBase","fJumpAcroMultiplier","fJumpEncumbranceBase","fJumpEncumbranceMultiplier",
    "fJumpRunMultiplier","fJumpMoveBase","fJumpMoveMult",
    "fFatigueRunBase","fFatigueRunMult","fFatigueSwimWalkBase","fFatigueSwimWalkMult",
    "fFatigueSwimRunBase","fFatigueSwimRunMult","fFatigueSneakBase","fFatigueSneakMult",
    "fFatigueJumpBase","fFatigueJumpMult","fFatigueBase","fFatigueMult"};
/* Morrowind.esm values of the same settings, in the same order. */
static const float originals[AW_MOVE_SETTING_COUNT]={
    100,200,.3f,1.75f,1, .5f,.1f,.75f,5, 5,300, 128,4,.5f,1, 1,.5f,.5f,
    5,2,2.5f,0, 7,0,1.5f,1.5f, 5,0,1.25f,.5f};

const char *AW_MoveSettingName(int index) {
    return index>=0 && index<AW_MOVE_SETTING_COUNT?names[index]:0;
}
int AW_MoveSettingIndex(const char *name) {
    int i;
    if(!name)return -1;
    for(i=0;i<AW_MOVE_SETTING_COUNT;i++){
        const char *a=names[i],*b=name;
        while(*a && (*a|32)==(*b|32)){a++;b++;}
        if(!*a && !*b)return i;
    }
    return -1;
}
int AW_MoveSettingSet(aw_move_settings_t *s,const char *name,float value) {
    int i=AW_MoveSettingIndex(name);
    if(i<0 || !(value==value))return 0;
    ((float *)s)[i]=value;return 1;
}
void AW_MoveSettingsDefault(aw_move_settings_t *s) {
    memcpy(s,originals,sizeof(originals));
}

/* Npc::getCapacity: modified Strength x fEncumbranceStrMult. */
float AW_MoveCapacity(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    return in->strength*s->fEncumbranceStrMult;
}
/* Actor::getEncumbrance (carried - Feather + Burden, Burden ignored in godmode,
 * not below 0) over the capacity; Class::getNormalizedEncumbrance (0 when
 * nothing is carried, over capacity when the capacity is 0). */
float AW_MoveEncumbrance(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float weight=in->carried-in->feather+(in->godmode?0:in->burden),capacity=AW_MoveCapacity(s,in);
    if(weight<0)weight=0;
    if(weight==0)return 0;
    if(capacity<=0)return 1.000001f;
    return weight/capacity;
}
float AW_MoveWalkSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float walk=s->fMinWalkSpeed+.01f*in->speed*(s->fMaxWalkSpeed-s->fMinWalkSpeed);
    walk*=1-s->fEncumberedMoveEffect*AW_MoveEncumbrance(s,in);
    if(walk<0)walk=0;
    if(in->sneaking)walk*=s->fSneakSpeedMultiplier;
    return walk;
}
float AW_MoveRunSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    return AW_MoveWalkSpeed(s,in)*(.01f*in->athletics*s->fAthleticsRunBonus+s->fBaseRunMultiplier);
}
float AW_MoveSwimSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float base=in->running?AW_MoveRunSpeed(s,in):AW_MoveWalkSpeed(s,in);
    return base*(1+.01f*in->swift_swim)*(s->fSwimRunBase+.01f*in->athletics*s->fSwimRunAthleticsMult);
}
float AW_MoveMaxSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float e;
    if(in->paralyzed || in->knocked || in->dead)return 0;
    e=AW_MoveEncumbrance(s,in);
    if(e>1)return 0;
    if(in->levitate>0 && in->levitation_enabled){
        float fly=.01f*(in->speed+in->levitate);
        fly=s->fMinFlySpeed+fly*(s->fMaxFlySpeed-s->fMinFlySpeed);
        fly*=1-s->fEncumberedMoveEffect*e;
        return fly<0?0:fly;
    }
    if(in->swimming)return AW_MoveSwimSpeed(s,in);
    if(in->running && !in->sneaking)return AW_MoveRunSpeed(s,in);
    return AW_MoveWalkSpeed(s,in);
}
int AW_MoveStrafing(float forward,float side) {
    return fabs(side)>fabs(forward)*2;
}
float AW_MoveCurrentSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in,float factor,int strafing) {
    float speed;
    if(factor<0)factor=0;
    if(factor>1)factor=1;
    speed=AW_MoveMaxSpeed(s,in)*factor;
    if(strafing)speed*=.75f;
    return speed*(in->scale>0?in->scale:1);
}
/* CreatureStats::getFatigueTerm. */
float AW_MoveFatigueTerm(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float normalised=in->fatigue_max>0?in->fatigue/in->fatigue_max:1;
    if(normalised<0)normalised=0;
    return s->fFatigueBase-s->fFatigueMult*(1-normalised);
}
/* x^g for x >= 0 with add, multiply and divide only (as mathlib.c Q_GammaPow, ENGINE-GAMMA-POW-35): the C library
 * pow executes FPU instructions the 68040 does not implement (tools/check_fpu_unimplemented.py fails the build).
 * A whole exponent (fJumpAcroMultiplier is 4 in the original settings) is exact; others use ln/exp series. */
static double move_pow(double x,double g) {
    const double ln2=0.69314718055994530942;
    double m,z,z2,term,sum,y,scale,r;
    int i,n;
    if(!(x>0))return 0;
    if(g==(double)(n=(int)g) && n>=0 && n<=64) {for(r=1;n>0;n--)r*=x;return r;}
    for(m=x,y=0;m<.5;m*=2)y-=ln2;
    for(;m>1;m*=.5)y+=ln2;
    z=(m-1)/(m+1);z2=z*z;term=z;sum=0;
    for(i=1;i<40;i+=2){sum+=term/i;term*=z2;}
    y=g*(y+2*sum);
    if(y<-60)return 0;
    if(y>60)y=60;
    for(scale=1;y<0;y+=ln2)scale*=.5;
    for(;y>=ln2;y-=ln2)scale*=2;
    for(r=1,term=1,i=1;i<20;i++){term*=y/i;r+=term;}
    return r*scale;
}
float AW_MoveJumpVelocity(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float e=AW_MoveEncumbrance(s,in),a=in->acrobatics,b=0,x;
    if(e>1 || in->paralyzed || in->knocked || in->dead)return 0;
    if(a>50){b=a-50;a=50;}
    x=s->fJumpAcrobaticsBase+(float)move_pow(a/15.0f,s->fJumpAcroMultiplier);
    x+=3*b*s->fJumpAcroMultiplier;
    x+=in->jump*64;
    x*=s->fJumpEncumbranceBase+s->fJumpEncumbranceMultiplier*(1-e);
    if(in->running)x*=s->fJumpRunMultiplier;
    x*=AW_MoveFatigueTerm(s,in);
    x+=8.96f*69.99125109f;     /* minus -GravityConst x UnitsPerMeter (components/misc/constants.hpp) */
    return x/3;
}
float AW_MoveFatigueRate(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float e;
    if(in->godmode)return 0;
    e=AW_MoveEncumbrance(s,in);
    if(e>1)return 0;
    if(in->sneaking)return s->fFatigueSneakBase+e*s->fFatigueSneakMult;
    if(in->swimming)return in->running?s->fFatigueSwimRunBase+e*s->fFatigueSwimRunMult:
        s->fFatigueSwimWalkBase+e*s->fFatigueSwimWalkMult;
    if(in->running)return s->fFatigueRunBase+e*s->fFatigueRunMult;
    return 0;
}
float AW_MoveJumpFatigue(const aw_move_settings_t *s,const aw_move_inputs_t *in) {
    float e=AW_MoveEncumbrance(s,in);
    if(in->godmode)return 0;
    if(e>1)e=1;
    return s->fFatigueJumpBase+e*s->fFatigueJumpMult;
}
float AW_MoveFatigueAfter(float fatigue,float loss) {
    float after=fatigue-loss;
    if(loss<=0)return fatigue;
    if(after<0 && fatigue>=0)after=0;
    return after;
}
