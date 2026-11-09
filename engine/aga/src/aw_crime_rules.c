/* SPDX-License-Identifier: GPL-2.0-or-later
 * The crime rules as pure functions (aw_crime.h); host tested by tests/aga_crime_rules_test.c. */
#include <string.h>
#include "aw_crime.h"

static const char *const names[AW_CRIME_SETTING_COUNT]={
    "fAlarmRadius","fCrimeStealing","fDispStealing","fFightStealing",
    "fSneakSkillMult","fSneakBootMult","fSneakDistanceBase","fSneakDistanceMultiplier","fSneakNoViewMult",
    "fSneakViewMult","iCrimeThreshold",
    "iCrimeAttack","iCrimeKilling","iCrimeTresspass","iCrimePickPocket",
    "iDispAttackMod","fDispAttacking","iDispKilling","iDispTresspass","fDispPickPocketMod",
    "iFightAttack","iFightAttacking","iFightKilling","iFightTrespass","iFightPickpocket",
    "iDaysinPrisonMod","iCrimeThresholdMultiplier","fCrimeGoldDiscountMult","fCrimeGoldTurnInMult"};
const char *AW_CrimeSettingName(int index){return index>=0 && index<AW_CRIME_SETTING_COUNT?names[index]:NULL;}
int AW_CrimeSettingSet(aw_crime_settings_t *s,const char *name,float value){
    float *field=(float *)s;int i;
    if(!s || !name)return 0;
    for(i=0;i<AW_CRIME_SETTING_COUNT;i++)if(!strcmp(names[i],name)){field[i]=value;return 1;}
    return 0;
}
static const char *const kinds[AW_CRIME_KINDS]={"theft","pickpocketing","trespass","assault","murder","an owned bed"};
const char *AW_CrimeKindName(int kind){return kind>=0 && kind<AW_CRIME_KINDS?kinds[kind]:"?";}

/* OpenMW 0.51 mechanicsmanagerimp.cpp awarenessCheck: the thief's term x (sneaking: skill, agility, luck and the boots'
 * weight, scaled by the distance and its fatigue; Chameleon adds, Invisibility adds 100) less the observer's term y
 * (Sneak, agility, luck less Blind, by its fatigue, x fSneakViewMult in view or fSneakNoViewMult from behind). */
float AW_CrimeAwarenessTarget(const aw_crime_settings_t *s,const aw_crime_thief_t *t,const aw_crime_observer_t *o,
                              float distance){
    float sneak_term=0,dist_term,x,obs_term,y;
    if(t->sneaking)
        sneak_term=s->fSneakSkillMult*t->sneak+0.2f*t->agility+0.1f*t->luck+t->boot_weight*s->fSneakBootMult;
    dist_term=s->fSneakDistanceBase+s->fSneakDistanceMultiplier*distance;
    x=sneak_term*dist_term*t->fatigue_term+t->chameleon;
    if(t->invisibility>0)x+=100;
    obs_term=o->sneak+0.2f*o->agility+0.1f*o->luck-o->blind;
    y=obs_term*o->fatigue_term*(o->behind?s->fSneakNoViewMult:s->fSneakViewMult);
    return x-y;
}

/* reportCrime OT_Theft: bounty = arg x fCrimeStealing, at least 1 (a theft of a worthless item still counts) */
int AW_CrimeTheftBounty(const aw_crime_settings_t *s,int value){
    int bounty=(int)((float)value*s->fCrimeStealing);
    return bounty<1?1:bounty;
}
/* reportCrime: the bounty of each kind (the settings are whole numbers: getInteger) */
int AW_CrimeBounty(const aw_crime_settings_t *s,int kind,int arg){
    switch(kind){
    case AW_CRIME_THEFT:return AW_CrimeTheftBounty(s,arg);
    case AW_CRIME_PICKPOCKET:return (int)s->iCrimePickPocket;
    case AW_CRIME_TRESPASS:case AW_CRIME_BED:return (int)s->iCrimeTresspass;
    case AW_CRIME_ASSAULT:return (int)s->iCrimeAttack;
    case AW_CRIME_MURDER:return (int)s->iCrimeKilling;
    }
    return arg;
}

/* reportCrime, a witness that is not an alarmed guard: fight = fFightStealing (read as a whole number, getInteger) x
 * arg; + getFightDispositionBias(dispTerm), dispTerm = fDispStealing x arg; + getFightDistanceBias; x Alarm / 100;
 * kept within 0 .. 100 - Fight */
float AW_CrimeTheftFight(const aw_crime_settings_t *s,int value,int fight,int alarm,float distance,
                         float fight_disp_mult,float distance_base,float distance_mult){
    float disp=s->fDispStealing*(float)value;
    float term=(float)((int)s->fFightStealing*value);
    term+=(50.0f-disp)*fight_disp_mult;
    term+=distance_base-distance_mult*distance;
    term*=0.01f*(float)alarm;
    if((float)fight+term>100)term=(float)(100-fight);
    return term<0?0:term;
}

/* reportCrime's per-kind terms: the disposition change of a bystander and of the victim, the Fight of a bystander and of
 * the victim */
static void terms(const aw_crime_settings_t *s,int kind,int arg,float *disp,float *disp_victim,int *fight,int *fight_victim){
    *disp=*disp_victim=0;*fight=*fight_victim=0;
    switch(kind){
    case AW_CRIME_TRESPASS:case AW_CRIME_BED:
        *disp=*disp_victim=s->iDispTresspass;*fight=*fight_victim=(int)s->iFightTrespass;break;
    case AW_CRIME_PICKPOCKET:
        *disp=*disp_victim=s->fDispPickPocketMod;*fight=(int)s->iFightPickpocket;
        *fight_victim=(int)s->iFightPickpocket*4;break;   /* x 4 for the victim (OpenMW: "according to research wiki") */
    case AW_CRIME_ASSAULT:
        *disp=s->iDispAttackMod;*disp_victim=s->fDispAttacking;
        *fight=(int)s->iFightAttacking;*fight_victim=(int)s->iFightAttack;break;
    case AW_CRIME_MURDER:
        *disp=*disp_victim=s->iDispKilling;*fight=*fight_victim=(int)s->iFightKilling;break;
    case AW_CRIME_THEFT:
        *disp=*disp_victim=s->fDispStealing*(float)arg;*fight=*fight_victim=(int)s->fFightStealing*arg;break;
    }
}
static int clamp_change(int change,int disposition){
    if(change<-disposition)change=-disposition;
    if(change>100-disposition)change=100-disposition;
    return change;
}
/* reportCrime's loop over the NPCs in the alarm radius, one NPC */
void AW_CrimeReact(const aw_crime_settings_t *s,int kind,int arg,const aw_crime_react_in_t *in,
                   float fight_disp_mult,float distance_base,float distance_mult,aw_crime_react_t *out){
    float disp,disp_victim,disp_term,alarm_term=0.01f*(float)in->alarm,fight_term;int fight,fight_victim;
    int permanent=0,only_if_hostile=0,change=0;
    memset(out,0,sizeof(*out));
    terms(s,kind,arg,&disp,&disp_victim,&fight,&fight_victim);
    disp_term=in->victim?disp_victim:disp;
    /* murder and trespass do not change the disposition */
    if(kind==AW_CRIME_THEFT)change=(int)(disp_term*alarm_term);
    else if(kind==AW_CRIME_PICKPOCKET){
        if(in->alarm>=100 && in->guard)change=(int)disp_term;
        else if(in->victim && in->guard){permanent=1;change=(int)(disp_term*alarm_term);}
        else if(in->victim){permanent=1;change=(int)disp_term;}
    }else if(kind==AW_CRIME_ASSAULT){
        if(in->victim && !in->guard){permanent=1;change=(int)disp_term;}
        else if(in->alarm>=100)change=(int)disp_term;
        else if(in->victim && in->guard){permanent=1;change=(int)(disp_term*alarm_term);}
        else{only_if_hostile=1;change=(int)(disp_term*alarm_term);}
    }
    if(change && !only_if_hostile){
        out->crime_id=1;out->disposition=clamp_change(change,in->disposition);out->permanent=permanent;
    }
    if(in->guard && in->alarm>=100){
        out->alarmed=1;out->crime_id=1;out->pursue=1;   /* marked Alarmed for the dialogue; AiPursue */
        return;
    }
    /* Alarm 0 counts as 100 for the victim of pickpocketing; bystanders that would not arrest do not care about it */
    if(kind==AW_CRIME_PICKPOCKET && in->victim && alarm_term==0)alarm_term=1;
    else if(kind==AW_CRIME_PICKPOCKET && !in->victim)alarm_term=0;
    fight_term=(float)(in->victim?fight_victim:fight);
    fight_term+=(50.0f-disp_term)*fight_disp_mult;                    /* getFightDispositionBias(dispTerm) */
    fight_term+=distance_base-distance_mult*in->distance;             /* getFightDistanceBias */
    fight_term*=alarm_term;
    if((float)in->fight+fight_term>100)fight_term=(float)(100-in->fight);
    if(fight_term<0)fight_term=0;
    if((float)in->fight+fight_term>=100){
        if(change && only_if_hostile){out->disposition=clamp_change(change,in->disposition);out->permanent=0;}
        out->attack=1;out->fight=in->fight+(int)fight_term;out->crime_id=1;out->alarmed=1;
    }
}
int AW_CrimeWitness(int kind,int is_victim,int victim_aware,int seen){
    if(is_victim && (victim_aware || kind==AW_CRIME_ASSAULT))return 1;   /* an assault's victim is always aware */
    if(kind==AW_CRIME_MURDER && !is_victim)return 1;                    /* "hearing is enough" */
    return seen!=0;
}
int AW_CrimeCanCommitAgainst(int npc,int aggressive,int engaged,int pursuing,int werewolf,int vampire){
    return npc && !aggressive && !engaged && !pursuing && !werewolf && !vampire;
}
int AW_CrimeIsMurder(int npc,int by_player,int can_commit,int crime_id){
    return npc && by_player && (can_commit || crime_id!=-1);
}
int AW_CrimeJailDays(const aw_crime_settings_t *s,int bounty){
    int mod=(int)s->iDaysinPrisonMod,days=mod>0?bounty/mod:1;
    return days<1?1:days;
}
int AW_CrimeJailSkill(int skill,int base){
    if(skill==18 || skill==19)return base<100?1:0;   /* Security, Sneak */
    return base>0?-1:0;
}
void AW_CrimeGoldGlobals(const aw_crime_settings_t *s,int bounty,int gold,int out[5]){
    int discount=(int)((float)bounty*s->fCrimeGoldDiscountMult),turn_in=(int)((float)bounty*s->fCrimeGoldTurnInMult);
    if(bounty>0){if(discount<1)discount=1;if(turn_in<1)turn_in=1;}
    out[0]=bounty<=gold;out[1]=discount<=gold;out[2]=discount;out[3]=turn_in;out[4]=turn_in<=gold;
}
int AW_CrimeGuardSight(const aw_crime_settings_t *s,int bounty){
    int cutoff=(int)s->iCrimeThreshold,mult=(int)s->iCrimeThresholdMultiplier;
    if(cutoff<=0 || bounty<cutoff)return 0;
    return bounty>=cutoff*mult?2:1;
}

/* creaturestats.cpp getAwarenessRoll / updateAwareness: the roll stays until 5 seconds have passed */
static int roll_live(const aw_crime_roll_t *r,double now){
    return r->roll>=0 && now>=r->at && now-r->at<AW_CRIME_ROLL_SECONDS;
}
int AW_CrimeRollFind(const aw_crime_roll_t *table,int count,int key,double now){
    int i;
    for(i=0;i<count;i++)if(table[i].key==key && roll_live(&table[i],now))return table[i].roll;
    return -1;
}
void AW_CrimeRollKeep(aw_crime_roll_t *table,int count,int key,int roll,double now){
    int i,slot=0;
    for(i=0;i<count;i++){
        if(table[i].key==key || !roll_live(&table[i],now)){slot=i;break;}
        if(table[i].at<table[slot].at)slot=i;
    }
    table[slot].key=key;table[slot].roll=roll;table[slot].at=now;
}

/* the NPCs' crime rows */
aw_crime_actor_t *AW_CrimeActorFind(aw_crime_actor_t *table,int count,unsigned long ref){
    int i;
    if(!ref)return NULL;
    for(i=0;i<count;i++)if(table[i].ref==ref)return &table[i];
    return NULL;
}
static int row_quiet(const aw_crime_actor_t *r){return r->crime_id==-1 && !r->alarmed && !r->murdered && !r->pursue;}
aw_crime_actor_t *AW_CrimeActorMake(aw_crime_actor_t *table,int count,unsigned long ref){
    aw_crime_actor_t *r=AW_CrimeActorFind(table,count,ref);int i;
    if(r || !ref)return r;
    for(i=0;i<count && !r;i++)if(!table[i].ref)r=&table[i];                     /* a free row */
    for(i=0;i<count && !r;i++)if(row_quiet(&table[i]))r=&table[i];              /* else a calm one */
    if(!r)return NULL;
    memset(r,0,sizeof(*r));r->ref=ref;r->crime_id=-1;
    return r;
}
int AW_CrimeActorsPack(const aw_crime_actor_t *table,int count,unsigned char *out,int capacity){
    int i,n=0,at=6;
    for(i=0;i<count;i++)if(table[i].ref && !row_quiet(&table[i]))n++;
    if(n>255)n=255;
    if(!out || capacity<6+n*AW_CRIME_SAVE_ROW)return -1;
    memcpy(out,"AWCR",4);out[4]=1;out[5]=(unsigned char)n;
    for(i=0;i<count && at<6+n*AW_CRIME_SAVE_ROW;i++){
        const aw_crime_actor_t *r=&table[i];unsigned long id=(unsigned long)(long)r->crime_id;
        unsigned d=(unsigned)(unsigned short)r->disposition;
        if(!r->ref || row_quiet(r))continue;
        out[at]=(unsigned char)(r->ref>>24);out[at+1]=(unsigned char)(r->ref>>16);
        out[at+2]=(unsigned char)(r->ref>>8);out[at+3]=(unsigned char)r->ref;
        out[at+4]=(unsigned char)(id>>24);out[at+5]=(unsigned char)(id>>16);
        out[at+6]=(unsigned char)(id>>8);out[at+7]=(unsigned char)id;
        out[at+8]=(unsigned char)(d>>8);out[at+9]=(unsigned char)d;
        out[at+10]=(unsigned char)((r->alarmed?1:0)|(r->murdered?2:0)|(r->pursue?4:0)|(r->attacked?8:0));
        out[at+11]=0;
        at+=AW_CRIME_SAVE_ROW;
    }
    return at;
}
int AW_CrimeActorsUnpack(aw_crime_actor_t *table,int count,const unsigned char *in,int bytes){
    int i,n,at=6;
    memset(table,0,sizeof(*table)*(size_t)count);
    for(i=0;i<count;i++)table[i].crime_id=-1;
    if(!in || bytes<6 || memcmp(in,"AWCR",4) || in[4]!=1)return -1;
    n=in[5];
    if(bytes<6+n*AW_CRIME_SAVE_ROW)return -1;
    for(i=0;i<n;i++,at+=AW_CRIME_SAVE_ROW){
        const unsigned char *p=in+at;aw_crime_actor_t *r;
        unsigned long ref=((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];
        unsigned long id=((unsigned long)p[4]<<24)|((unsigned long)p[5]<<16)|((unsigned long)p[6]<<8)|p[7];
        unsigned d=((unsigned)p[8]<<8)|p[9];
        if(i>=count || !ref || !(r=AW_CrimeActorMake(table,count,ref)))continue;   /* more than the table: the rest left */
        r->crime_id=id>0x7FFFFFFFUL?-(int)((0xFFFFFFFFUL-id)+1):(int)id;
        r->disposition=(short)(d>0x7FFF?(int)d-0x10000:(int)d);
        r->alarmed=(unsigned char)(p[10]&1);r->murdered=(unsigned char)((p[10]>>1)&1);
        r->pursue=(unsigned char)((p[10]>>2)&1);r->attacked=(unsigned char)((p[10]>>3)&1);
    }
    return at;
}
int AW_CrimeActorsCalm(aw_crime_actor_t *table,int count,int paid){
    int i,n=0;
    for(i=0;i<count;i++){
        aw_crime_actor_t *r=&table[i];
        if(!r->ref || r->crime_id==-1 || r->crime_id>paid)continue;
        r->crime_id=-1;r->alarmed=0;r->disposition=0;r->pursue=0;r->attacked=0;n++;
    }
    return n;
}
