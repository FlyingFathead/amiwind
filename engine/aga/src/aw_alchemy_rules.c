/* SPDX-License-Identifier: GPL-2.0-or-later
 * Alchemy's rules, pure (aw_alchemy.h). No engine headers; native tests: tests/test_alchemy.py. */
#include <math.h>
#include <string.h>
#include "aw_alchemy.h"

int AW_AlchemyIngredientVisible(float skill,float wort,int index){
    return index>=0 && index<4 && skill>=wort*(float)(index+1);
}
int AW_AlchemyPotionVisible(float skill,float wort,int index){
    return (index<=1 && skill>=wort) || (index<=3 && skill>=wort*2) || (index<=5 && skill>=wort*3) ||
           (index<=7 && skill>=wort*4);
}
int AW_AlchemyArgKind(int effect){
    switch(effect){
    case 85:case 22:case 17:case 79:case 74:return 1;   /* Absorb, Damage, Drain, Fortify, Restore Attribute */
    case 89:case 26:case 21:case 83:case 78:return 2;   /* the same of a Skill */
    }
    return 0;
}
static int same(const aw_alchemy_effect_t *a,const aw_alchemy_effect_t *b){return a->effect==b->effect && a->arg==b->arg;}
static int holds(const aw_alchemy_slot_t *s,const aw_alchemy_effect_t *e){
    int i;
    for(i=0;i<4;i++)if(s->e[i].effect!=AW_ALCHEMY_NO_EFFECT && same(&s->e[i],e))return 1;
    return 0;
}
int AW_AlchemyCount(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS]){
    int i,n=0;
    for(i=0;i<AW_ALCHEMY_SLOTS;i++)n+=s[i].used!=0;
    return n;
}
int AW_AlchemyListEffects(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS],aw_alchemy_effect_t out[AW_ALCHEMY_OUT]){
    int a,b,i,k,n=0;
    for(a=0;a<AW_ALCHEMY_SLOTS-1;a++){
        if(!s[a].used)continue;
        for(b=a+1;b<AW_ALCHEMY_SLOTS;b++){
            if(!s[b].used)continue;
            for(i=0;i<4;i++){
                const aw_alchemy_effect_t *e=&s[a].e[i];
                if(e->effect==AW_ALCHEMY_NO_EFFECT)continue;
                for(k=0;k<n && !same(&out[k],e);k++);
                if(k<n || !holds(&s[b],e) || n>=AW_ALCHEMY_OUT)continue;
                out[n].effect=e->effect;out[n].arg=e->arg;out[n].duration=out[n].magnitude=0;n++;
            }
        }
    }
    return n;
}
float AW_AlchemyFactor(float skill,float intelligence,float luck){return skill+.1f*intelligence+.1f*luck;}
int AW_AlchemyTools(uint32_t flags,int harmful,const float quality[AW_APPARATUS_TYPES],float *value){
    int magnitude=!(flags&AW_ALCHEMY_MGEF_NO_MAGNITUDE),duration=!(flags&AW_ALCHEMY_MGEF_NO_DURATION);
    int tool=harmful?AW_APPARATUS_ALEMBIC:AW_APPARATUS_RETORT,setup;
    float t,c,q=1;
    int has_tool=quality[tool]>0,has_calc=quality[AW_APPARATUS_CALCINATOR]>0;
    if(has_tool && has_calc)setup=1;
    else if(has_tool)setup=2;
    else if(has_calc)setup=3;
    else return 1;
    t=setup==1 || setup==2?quality[tool]:0;
    c=setup==1 || setup==3?quality[AW_APPARATUS_CALCINATOR]:0;
    switch(setup){
    case 1:q=harmful?2*t+3*c:(magnitude && duration?2*t+c:2/3.0f*(t+c)+.5f);break;
    case 2:q=harmful?1+t:(magnitude && duration?t:t+.5f);break;
    case 3:q=magnitude && duration?c:c+.5f;break;
    }
    if(setup==3 || !harmful)*value+=q;
    else{
        if(q==0)return 0;
        *value/=q;
    }
    return 1;
}
/* roundf: half away from zero (the values are never negative here) */
static float round_half(float v){return v<0?-floorf(-v+.5f):floorf(v+.5f);}
int AW_AlchemyBrew(const aw_alchemy_settings_t *set,const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS],
                   const float quality[AW_APPARATUS_TYPES],float factor,aw_alchemy_mgef_t mgef,void *ctx,
                   aw_alchemy_effect_t out[AW_ALCHEMY_OUT],int *value){
    aw_alchemy_effect_t keys[AW_ALCHEMY_OUT];int n,i,k=0;float x;
    if(value)*value=0;
    if(!set || set->loaded!=AW_ALCHEMY_SETTINGS_ALL || AW_AlchemyCount(s)<2 || !(quality[AW_APPARATUS_MORTAR]>0) || !mgef)return -1;
    if(!(set->t1_mag>0) || !(set->t1_dur>0))return -1;
    n=AW_AlchemyListEffects(s,keys);
    x=factor*quality[AW_APPARATUS_MORTAR]*set->strength_mult;
    if(value)*value=(int)(x*(float)set->alchemy_mod);
    for(i=0;i<n;i++){
        uint32_t flags;float cost,magnitude,duration;int harmful;
        if(!mgef(ctx,keys[i].effect,&flags,&cost) || !(cost>0))continue;
        harmful=(flags&AW_ALCHEMY_MGEF_HARMFUL)!=0;
        magnitude=flags&AW_ALCHEMY_MGEF_NO_MAGNITUDE?1.0f:(x/set->t1_mag)/cost;
        duration=flags&AW_ALCHEMY_MGEF_NO_DURATION?1.0f:(x/set->t1_dur)/cost;
        if(!(flags&AW_ALCHEMY_MGEF_NO_MAGNITUDE) && !AW_AlchemyTools(flags,harmful,quality,&magnitude))continue;
        if(!(flags&AW_ALCHEMY_MGEF_NO_DURATION) && !AW_AlchemyTools(flags,harmful,quality,&duration))continue;
        duration=round_half(duration);magnitude=round_half(magnitude);
        if(!(magnitude>0 && duration>0))continue;
        out[k]=keys[i];
        out[k].duration=(unsigned short)(duration>65535?65535:duration);
        out[k].magnitude=(unsigned short)(magnitude>65535?65535:magnitude);
        k++;
    }
    return k;
}
int AW_AlchemyReady(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS],const float quality[AW_APPARATUS_TYPES]){
    aw_alchemy_effect_t keys[AW_ALCHEMY_OUT];
    if(!(quality[AW_APPARATUS_MORTAR]>0))return AW_ALCHEMY_NO_MORTAR;
    if(AW_AlchemyCount(s)<2)return AW_ALCHEMY_TOO_FEW;
    if(!AW_AlchemyListEffects(s,keys))return AW_ALCHEMY_NO_EFFECTS;
    return AW_ALCHEMY_OK;
}
int AW_AlchemySucceeds(float factor,int roll,int effects){return effects>0 && !(factor<(float)roll);}
float AW_AlchemyWeight(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS]){
    int i,n=0;float w=0;
    for(i=0;i<AW_ALCHEMY_SLOTS;i++)if(s[i].used){w+=s[i].weight;n++;}
    return n?w/(float)n:0;
}
int AW_AlchemyEat(float skill,float intelligence,float luck,float fatigue_term,int roll,uint32_t flags,float base_cost,
                  unsigned short *magnitude,unsigned short *duration){
    float x=(skill+.2f*intelligence+.1f*luck)*fatigue_term,y,m=0;
    if((float)roll>x || !(x>0))return 0;
    y=(float)roll/(x<100?x:100.0f);
    y*=.25f*x;
    *duration=(unsigned short)(flags&AW_ALCHEMY_MGEF_NO_DURATION?1:(y>65535?65535:(int)y));
    if(!(flags&AW_ALCHEMY_MGEF_NO_MAGNITUDE)){
        if(!(base_cost>0))return 0;
        m=flags&AW_ALCHEMY_MGEF_NO_DURATION?floorf(y/(.1f*base_cost)):floorf((.05f*y)/(.1f*base_cost));
        if(m<1)m=1;
    }else m=1;
    *magnitude=(unsigned short)(m>65535?65535:m);
    return 1;
}
void AW_AlchemyBestTools(const int *type,const float *quality,int n,float quality_out[AW_APPARATUS_TYPES],int best[AW_APPARATUS_TYPES]){
    int i;
    for(i=0;i<AW_APPARATUS_TYPES;i++){quality_out[i]=0;best[i]=-1;}
    for(i=0;i<n;i++){
        int t=type[i];
        if(t<0 || t>=AW_APPARATUS_TYPES || !(quality[i]>0))continue;
        if(best[t]<0 || quality[i]>quality_out[t]){best[t]=i;quality_out[t]=quality[i];}
    }
}
int AW_AlchemySetting(aw_alchemy_settings_t *set,const char *name,float value){
    static const char *const names[5]={"fWortChanceValue","fPotionStrengthMult","iAlchemyMod","fPotionT1MagMult","fPotionT1DurMult"};
    int i;
    for(i=0;i<5;i++){
        const char *a=names[i],*b=name;
        while(*a && *b && (*a|32)==(*b|32)){a++;b++;}
        if(*a || *b)continue;
        switch(i){
        case 0:set->wort=value;break;
        case 1:set->strength_mult=value;break;
        case 2:set->alchemy_mod=(int)value;break;
        case 3:set->t1_mag=value;break;
        case 4:set->t1_dur=value;break;
        }
        set->loaded|=1<<i;
        return 1;
    }
    return 0;
}
