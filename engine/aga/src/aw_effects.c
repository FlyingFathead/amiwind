/* SPDX-License-Identifier: GPL-2.0-or-later
 * Spell effects on the player, the first slice: aw_effects.h. */
#include <string.h>
#include "aw_effects.h"

typedef struct {unsigned char used,kind,stat;float magnitude,left;} effect_t;
static effect_t fx[AW_EFFECTS_MAX];
static unsigned long refused;

void AW_EffectsReset(void){memset(fx,0,sizeof(fx));}
int AW_EffectsCount(void){int i,n=0;for(i=0;i<AW_EFFECTS_MAX;i++)n+=fx[i].used;return n;}
unsigned long AW_EffectsRefused(void){return refused;}

static int dynamic(int stat){return stat>=AWA_HEALTH && stat<=AWA_FATIGUE?stat-AWA_HEALTH:-1;}
static short *mod_of(aw_actor_t *a,int stat){
    if(stat>=AWA_ATTRIBUTE && stat<AWA_ATTRIBUTE+8)return &a->attr_mod[stat-AWA_ATTRIBUTE];
    if(stat>=AWA_SKILL && stat<AWA_SKILL+27)return &a->skill_mod[stat-AWA_SKILL];
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
/* GetEffect: an active effect of the game's effect NUMBER (OpenMW's MGEF index): drain 17-21, damage 22-26,
 * restore 74-78, fortify 79-83, each block attribute, health, magicka, fatigue, skill. Other effects: none can be
 * active here yet, so 0 is their true answer. */
int AW_EffectsHas(int number){
    static const int base[4]={17,22,74,79};int kind,group,i;
    for(kind=0;kind<4;kind++)if(number>=base[kind] && number<=base[kind]+4)break;
    if(kind==4)return 0;
    group=number-base[kind];
    for(i=0;i<AW_EFFECTS_MAX;i++){
        int s=fx[i].stat,g;
        if(!fx[i].used || fx[i].kind!=kind)continue;
        g=s<AWA_SKILL?0:s<AWA_HEALTH?4:s-AWA_HEALTH+1;
        if(g==group)return 1;
    }
    return 0;
}
static int per_second(int kind){return kind==AW_FX_DAMAGE || kind==AW_FX_RESTORE;}

int AW_EffectsAdd(aw_actor_t *a,int kind,int stat,float m,float seconds){
    int i;
    if(!a || kind<AW_FX_DRAIN || kind>AW_FX_FORTIFY || m<=0)return 0;
    if(seconds<=0){                                 /* instant: Damage and Restore act once; Fortify and Drain do nothing */
        if(per_second(kind))act(a,kind,stat,m,1);
        return 1;
    }
    for(i=0;i<AW_EFFECTS_MAX && fx[i].used;i++);
    if(i==AW_EFFECTS_MAX){refused++;return 0;}
    fx[i].used=1;fx[i].kind=(unsigned char)kind;fx[i].stat=(unsigned char)stat;fx[i].magnitude=m;fx[i].left=seconds;
    if(!per_second(kind))act(a,kind,stat,m,1);
    return 1;
}
int AW_EffectsTick(aw_actor_t *a,float dt){
    int i,changed=0;
    if(!a || dt<=0)return 0;
    for(i=0;i<AW_EFFECTS_MAX;i++){
        effect_t *e=&fx[i];float step;
        if(!e->used)continue;
        step=dt<e->left?dt:e->left;
        if(per_second(e->kind)){act(a,e->kind,e->stat,e->magnitude*step,1);changed=1;}
        e->left-=dt;
        if(e->left<=0){
            if(!per_second(e->kind))act(a,e->kind,e->stat,e->magnitude,-1);
            e->used=0;changed=1;
        }
    }
    return changed;
}

static unsigned char *put32(unsigned char *p,float f){
    unsigned long u;unsigned int v;memcpy(&v,&f,4);u=v;
    p[0]=(unsigned char)(u>>24);p[1]=(unsigned char)(u>>16);p[2]=(unsigned char)(u>>8);p[3]=(unsigned char)u;return p+4;}
static float get32(const unsigned char *p){
    unsigned int v=((unsigned int)p[0]<<24)|((unsigned int)p[1]<<16)|((unsigned int)p[2]<<8)|p[3];float f;
    memcpy(&f,&v,4);return f;}
int AW_EffectsExport(unsigned char *out,int capacity){
    int i,n=AW_EffectsCount();unsigned char *p=out;
    if(6+10*n>capacity)return -1;
    memcpy(p,"AWEF",4);p[4]=1;p[5]=(unsigned char)n;p+=6;
    for(i=0;i<AW_EFFECTS_MAX;i++)if(fx[i].used){*p++=fx[i].kind;*p++=fx[i].stat;p=put32(p,fx[i].magnitude);p=put32(p,fx[i].left);}
    return 6+10*n;
}
int AW_EffectsImport(const unsigned char *data,int bytes){
    int i,n;
    AW_EffectsReset();
    if(bytes<6 || memcmp(data,"AWEF",4) || data[4]!=1)return 0;
    n=data[5];
    if(n>AW_EFFECTS_MAX || bytes!=6+10*n)return 0;
    for(i=0;i<n;i++){
        const unsigned char *p=data+6+10*i;float m=get32(p+2),left=get32(p+6);
        if(p[0]>AW_FX_FORTIFY || p[1]>=AWA_LEVEL || !(m>0 && m<1e6f) || !(left>0 && left<1e7f)){AW_EffectsReset();return 0;}
        fx[i].used=1;fx[i].kind=p[0];fx[i].stat=p[1];fx[i].magnitude=m;fx[i].left=left;
    }
    return 1;
}
