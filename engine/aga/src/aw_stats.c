/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every being's stats (aw_stats.h, ACTOR-STATS-ALL-61): the AWS1 section of an area's record decoded into a stat
 * block, an auto-calculated NPC's stats derived, and the original's read rules (OpenMW 0.51, written independently). */
#include <string.h>
#include <math.h>
#include "aw_stats.h"

#define U16(p) ((unsigned)(((p)[0]<<8)|(p)[1]))
static uint32_t u32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
#define RACE_FIXED 35                /* u32 hash, 8 + 8 attributes, 7 x (skill, bonus), u8 spells */
#define CLASS_ROW 17

uint32_t AW_StatIdHash(const char *id){
    uint32_t h=2166136261u;
    if(id)for(;*id;id++){unsigned c=(unsigned char)*id;if(c>='A' && c<='Z')c+=32;h=(h^c)*16777619u;}
    return h?h:1u;
}

/* the head of a section: AWS1 whole (its own tables), AWS2 slim (the shared record's tables); 0 not a section */
static long head_of(const unsigned char *s,long bytes){
    long h;
    if(!s || bytes<AWS_SLIM_HEAD)return 0;
    if(!memcmp(s,"AWS1",4))h=AWS_SECTION_HEAD;else if(!memcmp(s,"AWS2",4))h=AWS_SLIM_HEAD;else return 0;
    return h<=bytes && h+6L*(long)U16(s+4)<=bytes?h:0;
}
static int tables_ok(const unsigned char *t,long bytes){return head_of(t,bytes)==AWS_SECTION_HEAD;}
long AW_StatSectionFind(const unsigned char *s,long bytes,uint32_t hash){
    int lo=0,hi,mid;long head=head_of(s,bytes);
    if(!head)return 0;
    hi=(int)U16(s+4)-1;
    while(lo<=hi){
        const unsigned char *e;uint32_t h;
        mid=(lo+hi)/2;e=s+head+6*mid;h=u32(e);
        if(h==hash){long o=(long)U16(e+4);return o>=head && o<bytes?o:0;}
        if(h<hash)lo=mid+1;else hi=mid-1;
    }
    return 0;
}
/* the race and class rows of a whole (AWS1) section T: walked from the first race row (races are few) */
static const unsigned char *rows_start(const unsigned char *t){return t+AWS_SECTION_HEAD+6L*U16(t+4);}
static const unsigned char *race_at(const unsigned char *t,long bytes,int n){
    const unsigned char *p=rows_start(t),*end=t+bytes;int i;
    if(n<0 || n>=t[6])return NULL;
    for(i=0;i<n;i++){if(p+RACE_FIXED>end)return NULL;p+=RACE_FIXED+2*p[RACE_FIXED-1];}
    return p+RACE_FIXED<=end && p+RACE_FIXED+2*p[RACE_FIXED-1]<=end?p:NULL;
}
static const unsigned char *class_at(const unsigned char *t,long bytes,int n){
    const unsigned char *p=rows_start(t);
    if(n<0 || n>=t[7])return NULL;
    if(t[6]){p=race_at(t,bytes,t[6]-1);if(!p)return NULL;p+=RACE_FIXED+2*p[RACE_FIXED-1];}
    p+=CLASS_ROW*n;
    return p+CLASS_ROW<=t+bytes?p:NULL;
}

/* Python's round(): halves to even (the builder's round_even) */
static double round_even(double v){
    double f=floor(v),d=v-f;
    if(d>0.5)return f+1;
    if(d<0.5)return f;
    return fmod(f,2.0)==0?f:f+1;
}
/* An auto-calculated NPC's attributes, skills, health, magicka, fatigue from its race and class rows and level (the
 * rule of tools/prepare_combat.py autocalc and tools/mwscript/actors.py, OpenMW 0.51 mwclass/npc.cpp
 * autoCalculateAttributes and autoCalculateSkills, creaturestats.cpp): the same operations in the same order. */
static void derive(aw_stat_block_t *b,const unsigned char *s,const unsigned char *race,const unsigned char *clas,
                   float magicka_mult){
    double attr[8],skill[27];int i,a,k,level=b->level,female=b->flags&1,spec=clas[6],fav0=clas[4],fav1=clas[5];
    const unsigned char *gov=s+12;      /* the skill table: governing attribute, specialization */
    int bonus[27];
    memset(bonus,0,sizeof(bonus));
    /* a skill named twice: the later pair wins (the builder's dict of the pairs) */
    for(i=0;i<7;i++){int sk=(signed char)race[20+2*i];if(sk>=0 && sk<27)bonus[sk]=race[21+2*i];}
    for(a=0;a<8;a++)attr[a]=race[4+(female?8:0)+a];
    if(fav0<8)attr[fav0]+=10;
    if(fav1<8)attr[fav1]+=10;
    for(a=0;a<8;a++){
        double total=0;
        for(k=0;k<27;k++){
            double add=.2;
            if(gov[2*k]!=a)continue;
            for(i=0;i<5;i++){if(clas[7+2*i]==k)add=.5;if(clas[8+2*i]==k)add=1.;}
            total+=add;
        }
        attr[a]=round_even(attr[a]+(level-1)*total);
        if(attr[a]>100.)attr[a]=100.;
    }
    for(k=0;k<27;k++)skill[k]=0.;
    for(i=0;i<5;i++){if(clas[7+2*i]<27)skill[clas[7+2*i]]+=10;}
    for(i=0;i<5;i++){if(clas[8+2*i]<27)skill[clas[8+2*i]]+=25;}
    for(k=0;k<27;k++){
        double major=.1,v;int same=gov[2*k+1]==spec;
        for(i=0;i<5;i++)if(clas[7+2*i]==k || clas[8+2*i]==k)major=1.;
        v=round_even(skill[k]+5+bonus[k]+(same?5:0)+(level-1)*(major+(same?.5:0.)));
        skill[k]=v>100.?100.:v;
    }
    for(a=0;a<8;a++)b->attributes[a]=(unsigned char)attr[a];
    for(k=0;k<27;k++)b->skills[k]=(unsigned char)skill[k];
    {int mult=3+(spec==0?2:spec==2?1:0)+((fav0==5 || fav1==5)?1:0);
     double health=floor((attr[0]+attr[5])/2)+mult*(level-1);
     b->dynamic[0]=(unsigned short)health;}
    b->dynamic[1]=(unsigned short)(int)(attr[1]*(double)magicka_mult);
    b->dynamic[2]=(unsigned short)(attr[0]+attr[2]+attr[3]+attr[5]);
}

int AW_StatDecode(const unsigned char *s,long bytes,uint32_t hash,const unsigned char *shared,long shared_bytes,
                  aw_stat_block_t *b){
    long o=AW_StatSectionFind(s,bytes,hash);
    if(!AW_StatDecodeAt(s,bytes,o,shared,shared_bytes,b))return 0;
    b->id=hash;
    return 1;
}
int AW_StatDecodeAt(const unsigned char *s,long bytes,long o,const unsigned char *shared,long shared_bytes,
                    aw_stat_block_t *b){
    const unsigned char *p,*end,*t;long head=head_of(s,bytes),tb;int i,ri=0xFF,ci=0xFF;float mult;
    memset(b,0,sizeof(*b));
    b->rank=-1;
    if(!head || o<head || o>=bytes)return 0;
    /* the tables (skill table, race and class rows): a whole section's own, else the shared record's */
    if(head==AWS_SECTION_HEAD){t=s;tb=bytes;}else{t=shared;tb=shared_bytes;}
    if(!tables_ok(t,tb))return 0;
    p=s+o;end=s+bytes;
    if(p+3>end)return 0;
    b->kind=p[0];b->mask=(unsigned short)U16(p+1);p+=3;
    for(i=0;i<27;i++)b->skill_spec[i]=t[13+2*i];
    {uint32_t m=u32(t+8);memcpy(&mult,&m,4);}
    switch(b->kind){
    case AWS_KIND_STORED:
        if(p+45>end)return 0;
        b->level=(short)U16(p);memcpy(b->attributes,p+2,8);memcpy(b->skills,p+10,27);
        for(i=0;i<3;i++)b->dynamic[i]=(unsigned short)U16(p+37+2*i);
        b->disposition=p[43];b->reputation=p[44];p+=45;break;
    case AWS_KIND_AUTO:
        if(p+4>end)return 0;
        b->level=(short)U16(p);b->disposition=p[2];b->reputation=p[3];p+=4;break;
    case AWS_KIND_CREATURE:
        if(p+34>end)return 0;
        b->type=p[0];b->level=(short)U16(p+1);memcpy(b->attributes,p+3,8);
        for(i=0;i<3;i++)b->dynamic[i]=(unsigned short)U16(p+11+2*i);
        b->soul=(unsigned short)U16(p+17);memcpy(b->cms,p+19,3);
        for(i=0;i<6;i++)b->attacks[i]=(unsigned short)U16(p+22+2*i);
        p+=34;
        for(i=0;i<27;i++)b->skills[i]=b->cms[b->skill_spec[i]<3?b->skill_spec[i]:0];   /* getSkill by specialization */
        break;
    default:return 0;
    }
    if(p+2>end)return 0;
    b->flags=p[0];b->blood=p[1];p+=2;
    if(b->kind!=AWS_KIND_CREATURE){b->hello=30;b->fight=30;b->flee=30;}   /* OpenMW loadnpc.cpp before AIDT */
    if(b->mask&AWS_P_AI){if(p+5>end)return 0;b->hello=(unsigned short)U16(p);b->fight=p[2];b->flee=p[3];b->alarm=p[4];p+=5;}
    if(b->mask&AWS_P_SERVICES){if(p+4>end)return 0;b->services=u32(p);p+=4;}
    if(b->mask&AWS_P_FACTION){if(p+5>end)return 0;b->faction=u32(p);b->rank=(short)(signed char)p[4];p+=5;}
    if(b->mask&AWS_P_RACE){if(p+2>end)return 0;ri=p[0];ci=p[1];p+=2;}
    if(b->mask&AWS_P_SPELLS){
        int n;if(p+1>end || p+1+2*p[0]>end)return 0;
        n=p[0];for(i=0;i<n;i++)if(b->nspells<AWS_SPELLS)b->spells[b->nspells++]=(uint16_t)U16(p+1+2*i);
        p+=1+2*n;
    }
    if(b->mask&AWS_P_GOLD){if(p+4>end)return 0;b->gold=u32(p);p+=4;}
    if(ri!=0xFF){
        const unsigned char *r=race_at(t,tb,ri);
        if(r){
            int n=r[RACE_FIXED-1];b->race=u32(r);
            for(i=0;i<n;i++)if(b->nspells<AWS_SPELLS){b->spells[b->nspells++]=(uint16_t)U16(r+RACE_FIXED+2*i);b->race_spells++;}
        }
        if(ci!=0xFF){const unsigned char *c=class_at(t,tb,ci);if(c)b->clas=u32(c);
            if(b->kind==AWS_KIND_AUTO && r && c)derive(b,t,r,c,mult);}
    }
    b->valid=1;
    return 1;
}

int AW_StatRaceSpells(const unsigned char *t,long tb,uint32_t race,int *out,int max){
    int i,k,n=0;
    if(!tables_ok(t,tb))return 0;
    for(i=0;i<t[6];i++){
        const unsigned char *r=race_at(t,tb,i);
        if(!r)return 0;
        if(u32(r)!=race)continue;
        for(k=0;k<r[RACE_FIXED-1] && n<max;k++)if(U16(r+RACE_FIXED+2*k)!=AWS_NO_SPELL)out[n++]=(int)U16(r+RACE_FIXED+2*k);
        return n;
    }
    return 0;
}
int AW_StatBirthSpells(const unsigned char *t,long tb,uint32_t birth,int *out,int max){
    const unsigned char *p,*end;int i,k,n=0,count;
    if(!tables_ok(t,tb) || tb<8 || memcmp(t+tb-8,"BSG1",4))return 0;
    count=(int)U16(t+tb-4);p=t+U16(t+tb-2);end=t+tb-8;
    if(p<t+AWS_SECTION_HEAD || p>end)return 0;
    for(i=0;i<count;i++){
        if(p+5>end || p+5+2*p[4]>end)return 0;
        if(u32(p)==birth){
            for(k=0;k<p[4] && n<max;k++)if(U16(p+5+2*k)!=AWS_NO_SPELL)out[n++]=(int)U16(p+5+2*k);
            return n;
        }
        p+=5+2*p[4];
    }
    return 0;
}

long AW_StatRowOffset(const unsigned char *row){
    return row && row[0]=='A' && row[92]=='S' && row[93]==0?(long)U16(row+94):0;
}
long AW_StatRowActb(const unsigned char *row){
    return row && row[0]=='A' && row[88]=='R' && row[89]==0?(long)U16(row+90):-1;
}

int AW_StatHas(const aw_stat_block_t *b,int stat){
    int npc,crea;
    if(!b || !b->valid)return 0;
    npc=b->kind!=AWS_KIND_CREATURE;crea=!npc;
    if(stat>=AWS_ATTRIBUTE && stat<AWS_ATTRIBUTE+8)return 1;
    if(stat>=AWS_SKILL && stat<AWS_SKILL+27)return npc;
    if(stat>=AWS_ATTACK && stat<AWS_ATTACK+6)return crea;
    switch(stat){
    case AWS_HEALTH:case AWS_MAGICKA:case AWS_FATIGUE:case AWS_LEVEL:case AWS_HELLO:case AWS_FIGHT:case AWS_FLEE:
    case AWS_ALARM:case AWS_GOLD:case AWS_SERVICES:case AWS_BLOOD:case AWS_FLAGS:return 1;
    case AWS_DISPOSITION:case AWS_REPUTATION:case AWS_RANK:return npc;
    case AWS_SOUL:case AWS_COMBAT:case AWS_MAGIC:case AWS_STEALTH:case AWS_TYPE:return crea;
    }
    return 0;
}

int AW_StatRead(const aw_stat_block_t *b,int stat){
    int crea;
    if(!b || !b->valid)return stat==AWS_RANK?-1:0;
    crea=b->kind==AWS_KIND_CREATURE;
    if(stat>=AWS_ATTRIBUTE && stat<AWS_ATTRIBUTE+8)return b->attributes[stat];
    if(stat>=AWS_SKILL && stat<AWS_SKILL+27)return b->skills[stat-AWS_SKILL];   /* creatures: filled by spec at decode */
    if(stat>=AWS_ATTACK && stat<AWS_ATTACK+6)return crea?b->attacks[stat-AWS_ATTACK]:0;
    switch(stat){
    case AWS_HEALTH:case AWS_MAGICKA:case AWS_FATIGUE:return b->dynamic[stat-AWS_HEALTH];
    case AWS_LEVEL:return b->level;
    case AWS_HELLO:return b->hello;
    case AWS_FIGHT:return b->fight;
    case AWS_FLEE:return b->flee;
    case AWS_ALARM:return b->alarm;
    case AWS_DISPOSITION:return crea?0:b->disposition;
    case AWS_REPUTATION:return crea?0:b->reputation;
    case AWS_RANK:return crea || !b->faction?-1:b->rank;
    case AWS_GOLD:return (int)b->gold;
    case AWS_SERVICES:return (int)b->services;
    case AWS_SOUL:return crea?b->soul:0;
    case AWS_COMBAT:case AWS_MAGIC:case AWS_STEALTH:return crea?b->cms[stat-AWS_COMBAT]:0;
    case AWS_TYPE:return crea?b->type:0;
    case AWS_BLOOD:return b->blood;
    case AWS_FLAGS:return b->flags;
    }
    return 0;
}

int AW_StatSpells(const aw_stat_block_t *b,int *out,int max){
    int i,n=0;
    if(!b || !b->valid)return 0;
    for(i=0;i<b->nspells && n<max;i++)if(b->spells[i]!=AWS_NO_SPELL)out[n++]=b->spells[i];
    return n;
}

static const char *const attr_names[8]={"strength","intelligence","willpower","agility","speed","endurance",
                                         "personality","luck"};
static const char *const skill_names[27]={"block","armorer","mediumarmor","heavyarmor","bluntweapon","longblade","axe",
    "spear","athletics","enchant","destruction","alteration","illusion","conjuration","mysticism","restoration",
    "alchemy","unarmored","security","sneak","acrobatics","lightarmor","shortblade","marksman","mercantile","speechcraft",
    "handtohand"};
const char *AW_StatName(int stat){
    static const char *const attack_names[6]={"chopmin","chopmax","slashmin","slashmax","thrustmin","thrustmax"};
    if(stat>=AWS_ATTRIBUTE && stat<AWS_ATTRIBUTE+8)return attr_names[stat];
    if(stat>=AWS_SKILL && stat<AWS_SKILL+27)return skill_names[stat-AWS_SKILL];
    if(stat>=AWS_ATTACK && stat<AWS_ATTACK+6)return attack_names[stat-AWS_ATTACK];
    switch(stat){
    case AWS_HEALTH:return "health";case AWS_MAGICKA:return "magicka";case AWS_FATIGUE:return "fatigue";
    case AWS_LEVEL:return "level";case AWS_HELLO:return "hello";case AWS_FIGHT:return "fight";case AWS_FLEE:return "flee";
    case AWS_ALARM:return "alarm";case AWS_DISPOSITION:return "disposition";case AWS_REPUTATION:return "reputation";
    case AWS_RANK:return "rank";case AWS_GOLD:return "gold";case AWS_SERVICES:return "services";case AWS_SOUL:return "soul";
    case AWS_COMBAT:return "combat";case AWS_MAGIC:return "magic";case AWS_STEALTH:return "stealth";
    case AWS_TYPE:return "type";case AWS_BLOOD:return "blood";case AWS_FLAGS:return "flags";
    }
    return "";
}
