/* SPDX-License-Identifier: GPL-2.0-or-later
 * Active spell effects on every actor record: aw_effects.h. */
#include <string.h>
#include "aw_effects.h"

#define FL_STAT 1        /* acts on a stat (AW_EffectKind >= 0) */
#define FL_PER_SECOND 2
#define FL_CONSTANT 4    /* a worn item's or an ability's: lasts until taken off (AW_EffectsRemoveSource) */
#define SAVED_CONSTANT 1e7f   /* the seconds left a constant effect is saved with (its source says it is one) */
typedef struct {uint32_t owner;unsigned char used,effect,arg,flags;uint16_t source;float magnitude,left;} effect_t;
static effect_t fx[AW_EFFECTS_MAX];
static unsigned long refused;
static unsigned long generation=1;   /* moves with every reset and load: the worn items' effects are set again */

void AW_EffectsReset(void){memset(fx,0,sizeof(fx));generation++;}
int AW_EffectsCount(void){int i,n=0;for(i=0;i<AW_EFFECTS_MAX;i++)n+=fx[i].used;return n;}
int AW_EffectsCountOn(uint32_t owner){int i,n=0;for(i=0;i<AW_EFFECTS_MAX;i++)n+=fx[i].used && fx[i].owner==owner;return n;}
unsigned long AW_EffectsRefused(void){return refused;}

/* the stat blocks of the effect numbers: drain 17-21, damage 22-26, restore 74-78, fortify 79-83, each attribute,
 * health, magicka, fatigue, skill (the original's order); the damage of the elements, poison and the sun hurt health;
 * Absorb Health/Magicka/Fatigue hurt the target's (the caster's gain waits for caster-linked effects), Absorb
 * Attribute/Skill drain it (OpenMW spelleffects.cpp applyActorMagicEffect) */
int AW_EffectKind(int effect,int *group){
    static const int base[4]={17,22,74,79};int kind;
    for(kind=0;kind<4;kind++)if(effect>=base[kind] && effect<=base[kind]+4){*group=effect-base[kind];return kind;}
    switch(effect){
    case 14:case 15:case 16:case 27:case 135:*group=1;return AW_FX_DAMAGE;
    case 86:case 87:case 88:*group=effect-85;return AW_FX_DAMAGE;
    case 85:*group=0;return AW_FX_DRAIN;
    case 89:*group=4;return AW_FX_DRAIN;
    }
    *group=-1;return -1;
}
/* the effects that act while they last instead of once (OpenMW components/esm3/loadmgef.cpp: those without the
 * applied-once flag): the elements, Damage, Poison, the disintegrations, the cures, Restore, Absorb Health/Magicka/
 * Fatigue, Remove Curse, Sun Damage */
int AW_EffectPerSecond(int effect){
    return (effect>=14 && effect<=16) || (effect>=22 && effect<=27) || effect==37 || effect==38 ||
           (effect>=69 && effect<=78) || (effect>=86 && effect<=88) || effect==100 || effect==135;
}
/* the harmful effects (OpenMW components/esm3/loadmgef.cpp, the hardcoded harmful flag): Burden, the elements, Drain,
 * Damage, Poison, the Weaknesses, the disintegrations, Paralyze, Silence, Blind, Sound, Soultrap, Absorb, Turn Undead */
int AW_EffectHarmful(int effect){
    return effect==7 || (effect>=14 && effect<=38) || (effect>=45 && effect<=48) || effect==58 ||
           (effect>=85 && effect<=89) || effect==101;
}
int AW_EffectStat(int group,int arg){
    switch(group){
    case 0:return arg>=0 && arg<8?AWA_ATTRIBUTE+arg:-1;
    case 1:case 2:case 3:return AWA_HEALTH+group-1;
    case 4:return arg>=0 && arg<27?AWA_SKILL+arg:-1;
    }
    return -1;
}

static int dynamic(int stat){return stat>=AWA_HEALTH && stat<=AWA_FATIGUE?stat-AWA_HEALTH:-1;}
static short *mod_of(aw_actor_t *a,int stat){
    if(stat>=AWA_ATTRIBUTE && stat<AWA_ATTRIBUTE+8)return &a->attr_mod[stat-AWA_ATTRIBUTE];
    if(stat>=AWA_SKILL && stat<AWA_SKILL+27){
        /* creatures have no skills (OpenMW: a creature's skill effects change nothing); v061-stats' blocks may have
         * no skill part at all */
        if(a->kind==1)return NULL;
#ifdef AW_ACTOR_SKILL_PARTS
        if(!a->skill_mod)return NULL;
#endif
        return &a->skill_mod[stat-AWA_SKILL];
    }
    return NULL;
}
static short clamp_short(float v){return (short)(v>32767?32767:v<-32768?-32768:(v<0?v-0.5f:v+0.5f));}
/* one step of an effect's action: SIGN +1 applies MAGNITUDE, -1 undoes it (Fortify and Drain at their end) */
static void act(aw_actor_t *a,int kind,int stat,float m,int sign){
    int d=dynamic(stat);short *mod=mod_of(a,stat);
    if(d>=0){
        float *base=&a->dyn_base[d],*cur=&a->dyn_cur[d];
        switch(kind){
        case AW_FX_FORTIFY:*base+=sign*m;*cur+=sign*m;if(*cur<0 && sign<0 && d!=0)*cur=0;break;   /* spelleffects.cpp FortifyHealth.. */
        case AW_FX_DRAIN:*cur-=sign*m;break;                                          /* DrainHealth..: current, back at the end */
        case AW_FX_DAMAGE:*cur-=m;if(d!=0 && *cur<0)*cur=0;break;                     /* DamageHealth..: health may reach 0 */
        case AW_FX_RESTORE:if(*cur<*base){*cur+=m;if(*cur>*base)*cur=*base;}break;   /* RestoreHealth..: up to the base */
        }
        if(d==0 && *cur<0)*cur=0;
        return;
    }
    if(!mod)return;
    switch(kind){
    case AW_FX_FORTIFY:*mod=clamp_short(*mod+sign*m);break;      /* FortifyAttribute / FortifySkill: the modifier */
    case AW_FX_DRAIN:*mod=clamp_short(*mod-sign*m);break;        /* DrainAttribute / DrainSkill: back at the end */
    case AW_FX_DAMAGE:*mod=clamp_short(*mod-m);break;            /* DamageAttribute: lasting until restored */
    case AW_FX_RESTORE:if(*mod<0){*mod=clamp_short(*mod+m);if(*mod>0)*mod=0;}break;   /* RestoreAttribute: the damage back */
    }
}
static void act_entry(aw_actor_t *a,const effect_t *e,float m,int sign){
    int group,kind=AW_EffectKind(e->effect,&group),stat=kind>=0?AW_EffectStat(group,e->arg):-1;
    if(stat>=0)act(a,kind,stat,m,sign);
}

int AW_EffectsHasOn(uint32_t owner,int number){
    int i;
    for(i=0;i<AW_EFFECTS_MAX;i++)   /* the active spells' (OpenMW OpGetEffect), not a script's base modifier */
        if(fx[i].used && fx[i].owner==owner && fx[i].effect==number && fx[i].source!=AW_EFFECT_SOURCE_SCRIPT)return 1;
    return 0;
}
int AW_EffectsHas(int number){return AW_EffectsHasOn(AW_ACTOR_PLAYER_REF,number);}
float AW_EffectsMagnitude(uint32_t owner,int effect,int arg){
    int i;float m=0;
    for(i=0;i<AW_EFFECTS_MAX;i++)
        if(fx[i].used && fx[i].owner==owner && fx[i].effect==effect && (arg==AW_EFFECT_NO_ARG || fx[i].arg==arg))m+=fx[i].magnitude;
    return m;
}
int AW_EffectsOwners(uint32_t *out,int max){
    int i,j,n=0;
    for(i=0;i<AW_EFFECTS_MAX;i++){
        if(!fx[i].used || fx[i].owner==AW_ACTOR_PLAYER_REF)continue;
        for(j=0;j<n && out[j]!=fx[i].owner;j++);
        if(j==n && n<max)out[n++]=fx[i].owner;
    }
    return n;
}
int AW_EffectsForget(uint32_t owner){
    int i,n=0;
    for(i=0;i<AW_EFFECTS_MAX;i++)if(fx[i].used && fx[i].owner==owner){fx[i].used=0;n++;}
    return n;
}
int AW_EffectsRemoveSource(aw_actor_t *a,int source){
    int i,n=0;
    if(!a)return 0;
    for(i=0;i<AW_EFFECTS_MAX;i++){
        effect_t *e=&fx[i];
        if(!e->used || e->owner!=a->reference || e->source!=(uint16_t)source)continue;
        if(!(e->flags&FL_PER_SECOND) && (e->flags&FL_STAT))act_entry(a,e,e->magnitude,-1);   /* undone, as at its end */
        e->used=0;n++;
    }
    return n;
}
unsigned long AW_EffectsGeneration(void){return generation;}
int AW_EffectsAt(int i,aw_effect_info_t *out){
    int k;
    for(k=0;k<AW_EFFECTS_MAX;k++){
        if(!fx[k].used)continue;
        if(i--)continue;
        out->owner=fx[k].owner;out->effect=fx[k].effect;out->arg=fx[k].arg==AW_EFFECT_NO_ARG?-1:fx[k].arg;
        out->source=fx[k].source==AW_EFFECT_NO_SOURCE?-1:fx[k].source;out->magnitude=fx[k].magnitude;out->left=fx[k].left;
        return 1;
    }
    return 0;
}

static int free_slot(uint32_t owner){
    int i,player=AW_EffectsCountOn(AW_ACTOR_PLAYER_REF),others=AW_EffectsCount()-player;
    if(owner==AW_ACTOR_PLAYER_REF?player>=AW_EFFECTS_PLAYER:others>=AW_EFFECTS_MAX-AW_EFFECTS_PLAYER)return -1;
    for(i=0;i<AW_EFFECTS_MAX && fx[i].used;i++);
    return i<AW_EFFECTS_MAX?i:-1;
}
int AW_EffectsLand(aw_actor_t *a,int effect,int arg,float m,float seconds,int source){
    int i,group,kind,per_second;effect_t *e;
    if(!a || effect<0 || effect>=AW_EFFECT_COUNT || !(m>=0) || m>1e6f)return 0;
    kind=AW_EffectKind(effect,&group);per_second=AW_EffectPerSecond(effect);
    if(kind>=0 && AW_EffectStat(group,arg)<0)return 0;   /* an attribute or skill effect without its attribute or skill */
    if(seconds==AW_EFFECT_CONSTANT){                /* a worn item's: until its source is taken off */
        if(source<AW_EFFECT_SOURCE_CONSTANT || source>=AW_EFFECT_NO_SOURCE)return 0;
        if((i=free_slot(a->reference))<0){refused++;return 0;}
        e=&fx[i];memset(e,0,sizeof(*e));
        e->used=1;e->owner=a->reference;e->effect=(unsigned char)effect;
        e->arg=(unsigned char)(arg>=0 && arg<255?arg:AW_EFFECT_NO_ARG);
        e->flags=(unsigned char)((kind>=0?FL_STAT:0)|(per_second?FL_PER_SECOND:0)|FL_CONSTANT);
        e->source=(uint16_t)source;e->magnitude=m;e->left=SAVED_CONSTANT;
        if(!per_second)act_entry(a,e,m,1);
        return 1;
    }
    if(!(seconds>0)){                               /* once: a per-second effect acts its whole magnitude */
        if(per_second && kind>=0 && m>0)act(a,kind,AW_EffectStat(group,arg),m,1);
        return 1;
    }
    if((i=free_slot(a->reference))<0){refused++;return 0;}
    e=&fx[i];memset(e,0,sizeof(*e));
    e->used=1;e->owner=a->reference;e->effect=(unsigned char)effect;
    e->arg=(unsigned char)(arg>=0 && arg<255?arg:AW_EFFECT_NO_ARG);
    e->flags=(unsigned char)((kind>=0?FL_STAT:0)|(per_second?FL_PER_SECOND:0));
    e->source=(uint16_t)(source>=0 && source<0xFFFF?source:AW_EFFECT_NO_SOURCE);
    e->magnitude=m;e->left=seconds>1e7f?1e7f:seconds;
    if(!per_second)act_entry(a,e,m,1);
    return 1;
}
int AW_EffectsBaseModify(uint32_t owner,int effect,float delta){
    int i,group;effect_t *e=NULL;
    if(effect<0 || effect>=AW_EFFECT_COUNT || AW_EffectKind(effect,&group)>=0 || !(delta>-1e6f && delta<1e6f))return 0;
    for(i=0;i<AW_EFFECTS_MAX && !e;i++)
        if(fx[i].used && fx[i].owner==owner && fx[i].effect==effect && fx[i].source==AW_EFFECT_SOURCE_SCRIPT)e=&fx[i];
    if(!e){
        if(delta==0)return 1;
        if((i=free_slot(owner))<0){refused++;return 0;}
        e=&fx[i];memset(e,0,sizeof(*e));
        e->used=1;e->owner=owner;e->effect=(unsigned char)effect;e->arg=AW_EFFECT_NO_ARG;
        e->flags=(unsigned char)((AW_EffectPerSecond(effect)?FL_PER_SECOND:0)|FL_CONSTANT);
        e->source=AW_EFFECT_SOURCE_SCRIPT;e->left=SAVED_CONSTANT;
    }
    e->magnitude+=delta;
    if(e->magnitude>-0.5f && e->magnitude<0.5f)e->used=0;   /* back to none: the entry goes */
    return 1;
}
int AW_EffectsAdd(aw_actor_t *a,int kind,int stat,float m,float seconds){
    static const int base[4]={17,22,74,79};int group,arg;
    if(kind<AW_FX_DRAIN || kind>AW_FX_FORTIFY || !(m>0))return 0;
    if(stat>=AWA_ATTRIBUTE && stat<AWA_SKILL){group=0;arg=stat-AWA_ATTRIBUTE;}
    else if(stat>=AWA_SKILL && stat<AWA_HEALTH){group=4;arg=stat-AWA_SKILL;}
    else if(stat>=AWA_HEALTH && stat<=AWA_FATIGUE){group=stat-AWA_HEALTH+1;arg=AW_EFFECT_NO_ARG;}
    else return 0;
    return AW_EffectsLand(a,base[kind]+group,arg,m,seconds,AW_EFFECT_NO_SOURCE);
}
int AW_EffectsTick(aw_actor_t *a,float dt){
    int i,changed=0;
    if(!a || dt<=0)return 0;
    for(i=0;i<AW_EFFECTS_MAX;i++){
        effect_t *e=&fx[i];float step;
        if(!e->used || e->owner!=a->reference)continue;
        if(e->flags&FL_CONSTANT){   /* never ends on the clock; a per-second one acts each second it is worn */
            if((e->flags&FL_PER_SECOND) && (e->flags&FL_STAT)){act_entry(a,e,e->magnitude*dt,1);changed=1;}
            continue;
        }
        step=dt<e->left?dt:e->left;
        if(e->flags&FL_PER_SECOND){if(e->flags&FL_STAT){act_entry(a,e,e->magnitude*step,1);changed=1;}}
        e->left-=dt;
        if(e->left<=0){
            if(!(e->flags&FL_PER_SECOND) && (e->flags&FL_STAT))act_entry(a,e,e->magnitude,-1);
            e->used=0;changed=1;
        }
    }
    return changed;
}

static unsigned char *put32(unsigned char *p,float f){
    unsigned long u;unsigned int v;memcpy(&v,&f,4);u=v;
    p[0]=(unsigned char)(u>>24);p[1]=(unsigned char)(u>>16);p[2]=(unsigned char)(u>>8);p[3]=(unsigned char)u;return p+4;}
static uint32_t get_u32(const unsigned char *p){
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static float get32(const unsigned char *p){
    unsigned int v=(unsigned int)get_u32(p);float f;
    memcpy(&f,&v,4);return f;}
int AW_EffectsExport(unsigned char *out,int capacity){
    int i,n=AW_EffectsCount();unsigned char *p=out;
    if(6+16*n>capacity)return -1;
    memcpy(p,"AWEF",4);p[4]=2;p[5]=(unsigned char)n;p+=6;
    for(i=0;i<AW_EFFECTS_MAX;i++)if(fx[i].used){
        uint32_t o=fx[i].owner;
        *p++=(unsigned char)(o>>24);*p++=(unsigned char)(o>>16);*p++=(unsigned char)(o>>8);*p++=(unsigned char)o;
        *p++=fx[i].effect;*p++=fx[i].arg;*p++=(unsigned char)(fx[i].source>>8);*p++=(unsigned char)fx[i].source;
        p=put32(p,fx[i].magnitude);p=put32(p,fx[i].left);
    }
    return 6+16*n;
}
static int import_one(int i,uint32_t owner,int effect,int arg,int source,float m,float left){
    int group,kind;
    if(effect>=AW_EFFECT_COUNT || !((m>=0 || (source==AW_EFFECT_SOURCE_SCRIPT && m>-1e6f)) && m<1e6f) ||
       !(left>0 && left<=1e7f))return 0;
    kind=AW_EffectKind(effect,&group);
    if(source==AW_EFFECT_SOURCE_SCRIPT && kind>=0)return 0;
    if(kind>=0 && AW_EffectStat(group,arg)<0)return 0;
    fx[i].used=1;fx[i].owner=owner;fx[i].effect=(unsigned char)effect;fx[i].arg=(unsigned char)arg;
    fx[i].source=(uint16_t)source;fx[i].magnitude=m;fx[i].left=left;
    fx[i].flags=(unsigned char)((kind>=0?FL_STAT:0)|(AW_EffectPerSecond(effect)?FL_PER_SECOND:0)|
                                (source>=AW_EFFECT_SOURCE_CONSTANT && source<AW_EFFECT_NO_SOURCE && left==SAVED_CONSTANT?FL_CONSTANT:0));
    return 1;
}
int AW_EffectsBlockBytes(const unsigned char *data,unsigned long available){
    unsigned long n;
    if(available<6 || memcmp(data,"AWEF",4) || (data[4]!=1 && data[4]!=2))return -1;
    n=6+(data[4]==1?10UL:16UL)*data[5];
    return n>available?-1:(int)n;
}
int AW_EffectsImport(const unsigned char *data,int bytes){
    static const int base[4]={17,22,74,79};int i,n,size;
    AW_EffectsReset();
    if(bytes<6 || memcmp(data,"AWEF",4) || (data[4]!=1 && data[4]!=2))return 0;
    n=data[5];size=data[4]==1?10:16;
    if(n>AW_EFFECTS_MAX || bytes!=6+size*n)return 0;
    for(i=0;i<n;i++){
        const unsigned char *p=data+6+size*i;int ok;
        if(data[4]==1){   /* v0.0.57: u8 kind u8 stat f32 magnitude f32 left, the player's */
            int kind=p[0],stat=p[1],group,arg;
            if(kind>AW_FX_FORTIFY || stat>=AWA_LEVEL){AW_EffectsReset();return 0;}
            if(stat<AWA_SKILL){group=0;arg=stat;}else if(stat<AWA_HEALTH){group=4;arg=stat-AWA_SKILL;}
            else{group=stat-AWA_HEALTH+1;arg=AW_EFFECT_NO_ARG;}
            ok=import_one(i,AW_ACTOR_PLAYER_REF,base[kind]+group,arg,AW_EFFECT_NO_SOURCE,get32(p+2),get32(p+6));
            if(ok && !(fx[i].magnitude>0))ok=0;
        }else ok=import_one(i,get_u32(p),p[4],p[5],(p[6]<<8)|p[7],get32(p+8),get32(p+12));
        if(!ok){AW_EffectsReset();return 0;}
    }
    return 1;
}
