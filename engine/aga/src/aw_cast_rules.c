/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_cast_rules.c: the casting rules, pure (aw_cast.h). No engine headers. */
#include <math.h>
#include "aw_cast.h"
#include "aw_effects.h"

/* the schools' skills in the original's skill order: Alteration 11, Conjuration 13, Destruction 10, Illusion 12,
 * Mysticism 14, Restoration 15 */
int AW_CastSchoolSkill(int school){
    static const int school_skill[AW_CAST_SCHOOLS]={11,13,10,12,14,15};
    return school>=0 && school<AW_CAST_SCHOOLS?school_skill[school]:11;
}
float AW_CastBaseChance(const aw_spell_effect_t *e,const aw_mgef_t *m,int n,const float skills[27],float willpower,
                        float luck,int cost,float effect_cost_mult,int *school){
    float y=3.0e38f,lowest=0;int i;
    if(school)*school=0;
    for(i=0;i<n;i++){
        /* the original's own cost term here differs a little from the spell's cost (no minimum magnitude of 1) */
        float x=(float)e[i].duration,s;
        if(AW_EffectPerSecond(e[i].effect) && x<1)x=1;      /* at least 1 unless applied once */
        x*=0.1f*m[i].base_cost;
        x*=0.5f*(float)(e[i].magnitude_min+e[i].magnitude_max);
        x+=(float)e[i].area*0.05f*m[i].base_cost;
        if(e[i].range==AW_RANGE_TARGET)x*=1.5f;
        x*=effect_cost_mult;
        s=2.0f*skills[AW_CastSchoolSkill(m[i].school)];
        if(s-x<y){y=s-x;lowest=s;if(school)*school=m[i].school;}
    }
    return lowest-(float)cost+0.2f*willpower+0.1f*luck;
}
float AW_CastChance(float base,int type,int power_ready,int always,float silence,float sound,float fatigue_term,
                    float magicka,int cost,int check_magicka){
    float c;
    if(type==AW_SPELL_TYPE_POWER)return power_ready?100.0f:0.0f;
    if(silence>0)return 0;
    if(type!=AW_SPELL_TYPE_SPELL)return 100.0f;
    if(check_magicka && cost>0 && magicka<(float)cost)return 0;
    if(always)return 100.0f;
    c=(base-sound)*fatigue_term;
    return c<0?0:c>100?100:c;
}
float AW_CastFatigueTerm(float base,float mult,float current,float maximum){
    float normalised=floor(maximum)==0?1.0f:current/maximum;
    if(normalised<0)normalised=0;
    return base-mult*(1.0f-normalised);
}
float AW_CastMagnitude(int lo,int hi,float r){
    float m;
    if(hi<lo)hi=lo;
    if(!(r>=0))r=0;
    m=(float)lo+(float)floor(r*(float)(hi-lo+1));
    return m>(float)hi?(float)hi:m;
}
/* RACE-RESIST-NOT-ON-SPELL-DAMAGE-64 (rules from OpenMW 0.53 components/esm3/loadmgef.cpp getResistanceEffect /
 * getWeaknessEffect and mwmechanics/spellresistance.cpp, written independently). EFFECT's resisting effect, its
 * weakness effect and the elemental shield that also resists it (ESM indices; -1 none); 1 when it can be resisted. */
int AW_CastResistEffects(int effect,int *resist,int *weakness,int *shield){
    int r=-1,w=-1,s=-1;
    if((effect>=17 && effect<=26) || (effect>=85 && effect<=89) || (effect>=28 && effect<=36) ||
       effect==7 || effect==44 || (effect>=46 && effect<=56) || effect==101){r=93;w=31;}   /* Resist / Weakness to Magicka */
    else if(effect==37 || effect==38)r=42;               /* Disintegrate Weapon / Armor: Sanctuary */
    else if(effect==14){r=90;w=28;s=4;}                  /* Fire Damage: Resist Fire, Weakness to Fire, Fire Shield */
    else if(effect==16){r=91;w=29;s=6;}                  /* Frost Damage: Resist Frost, ..., Frost Shield */
    else if(effect==15){r=92;w=30;s=5;}                  /* Shock Damage: Resist Shock, ..., Lightning Shield */
    else if(effect==27){r=97;w=35;}                      /* Poison */
    else if(effect==45)r=99;                             /* Paralyze: Resist Paralysis */
    else if(effect==132){r=96;w=34;}                     /* Corprus */
    else if(effect==133){r=94;w=32;}                     /* Vampirism: Resist / Weakness to Common Disease */
    if(resist)*resist=r;
    if(weakness)*weakness=w;
    if(shield)*shield=s;
    return r>=0;
}
/* The resistance in percent (OpenMW getEffectResistance): ATTR the target's resist (+ shield) less its weakness
 * magnitudes; X = (Willpower + Luck/10) x the fatigue term, scaled by 50 / CAST_CHANCE (100: a caster that is no
 * actor, a trap); ROLL 0..100; a NoMagnitude effect's roll counts the resistance first and it is all or nothing.
 * min(X' + ATTR, 100): may be below 0 (a weakness: more than the full magnitude). */
float AW_CastResistance(float attr,float willpower,float luck,float fatigue_term,float cast_chance,float roll,int no_magnitude){
    float x=(willpower+0.1f*luck)*fatigue_term;
    if(cast_chance>0)x*=50.0f/cast_chance;
    if(no_magnitude)roll-=attr;
    if(x<=roll)x=0;
    else x=no_magnitude?100.0f:roll/(x<100.0f?x:100.0f);
    x+=attr;
    return x<100.0f?x:100.0f;
}
float AW_CastDuration(const aw_spell_effect_t *e,const aw_mgef_t *m){
    return m->flags&AW_MGEF_NO_DURATION?1.0f:(float)e->duration;
}
int AW_CastRanges(const aw_spell_effect_t *e,int n){
    int i,bits=0;
    for(i=0;i<n;i++)if(e[i].range<=AW_RANGE_TARGET)bits|=1<<e[i].range;
    return bits;
}

/* ---- magic items (OpenMW 0.51 spellutil.cpp getEffectiveEnchantmentCastCost, spellcasting.cpp CastSpell::cast) ---- */
int AW_CastItemCost(float cast_cost,float enchant_skill){
    float r=cast_cost-(cast_cost/100.0f)*(enchant_skill-10.0f);   /* a point of Enchant over 10 takes 1 % off */
    return r<1?1:(int)r;
}
float AW_CastItemCharge(float charge,int cost){return charge<(float)cost?-1.0f:charge-(float)cost;}

/* ---- the starting spells (OpenMW 0.51 autocalcspell.cpp autoCalcPlayerSpells, attrSkillCheck, calcWeakestSchool,
 * calcAutoCastChance; our own code) ---- */
#define MGEF_TARGET_SKILL 0x1
#define MGEF_TARGET_ATTRIBUTE 0x2
#define MGEF_APPLIED_ONCE 0x1000
static int start_skill_check(const aw_start_spell_t *s,const float skills[27],const float attributes[8],int minimum){
    int i;
    for(i=0;i<s->n;i++){
        if((s->m[i].flags&MGEF_TARGET_SKILL) && (s->e[i].skill<0 || s->e[i].skill>=27 || skills[s->e[i].skill]<(float)minimum))return 0;
        if((s->m[i].flags&MGEF_TARGET_ATTRIBUTE) &&
           (s->e[i].attribute<0 || s->e[i].attribute>=8 || attributes[s->e[i].attribute]<(float)minimum))return 0;
    }
    return 1;
}
/* the skill term of the weakest school: 2 x the school's skill of the effect whose term minus its cost is lowest (the
 * original's own cost formula here: magnitudes at least 1, 1 + duration, the area at least 1) */
static float start_skill_term(const aw_start_spell_t *s,const float skills[27],float cost_mult){
    float low=3.0e38f,term=0;int i;
    for(i=0;i<s->n;i++){
        int lo=1,hi=1,duration=0;float x,k;
        if(!(s->m[i].flags&AW_MGEF_NO_MAGNITUDE)){lo=s->e[i].magnitude_min;hi=s->e[i].magnitude_max;}
        if(!(s->m[i].flags&AW_MGEF_NO_DURATION))duration=s->e[i].duration;
        if(!(s->m[i].flags&MGEF_APPLIED_ONCE) && duration<1)duration=1;
        x=0.5f*(float)((lo>1?lo:1)+(hi>1?hi:1));
        x*=0.1f*s->m[i].base_cost;
        x*=(float)(1+duration);
        x+=0.05f*(float)(s->e[i].area>1?s->e[i].area:1)*s->m[i].base_cost;
        x*=cost_mult;
        if(s->e[i].range==AW_RANGE_TARGET)x*=1.5f;
        k=2.0f*skills[AW_CastSchoolSkill(s->m[i].school)];
        if(k-x<low){low=k-x;term=k;}
    }
    return term;
}
float AW_CastStartChance(const aw_start_spell_t *s,const float skills[27],const float attributes[8],float cost_mult){
    if(s->flags&4)return 100.0f;                    /* always succeeds */
    return start_skill_term(s,skills,cost_mult)-(float)s->cost+0.2f*attributes[2]+0.1f*attributes[7];
}
int AW_CastStartSpells(const aw_start_spell_t *s,int count,const aw_start_settings_t *set,const float skills[27],
                       const float attributes[8],const int *race,int nrace,int *out,int max){
    int n=0,i,j,reached=0,weakest=-1,min_cost=0x7FFFFFFF;
    float magicka=set->magicka_mult*attributes[1];  /* the base Intelligence */
    for(i=0;i<count;i++){
        int cost=s[i].cost;
        if(reached && cost<=min_cost)continue;
        for(j=0;j<nrace && race[j]!=s[i].row;j++);
        if(j<nrace)continue;                        /* the race gives it already */
        if(magicka<(float)cost)continue;
        if(AW_CastStartChance(&s[i],skills,attributes,set->cost_mult)<set->chance)continue;
        if(!start_skill_check(&s[i],skills,attributes,set->skill_min))continue;
        if(n>=max)break;
        out[n++]=i;
        if(reached){
            for(j=0;j<n && out[j]!=weakest;j++);
            if(j<n){for(;j<n-1;j++)out[j]=out[j+1];n--;}
            min_cost=0x7FFFFFFF;
            for(j=0;j<n;j++)if(s[out[j]].cost<min_cost){min_cost=s[out[j]].cost;weakest=out[j];}
        }else{
            if(cost<min_cost){weakest=i;min_cost=cost;}
            if(n==set->max)reached=1;
        }
    }
    for(i=0;i<n;i++)out[i]=s[out[i]].row;
    return n;
}

/* ---- NPC-NO-SPELLCASTING-65: the fighters' spell and weapon ratings (aw_cast.h) ---- */
/* the game's magic effect numbers this rating names (OpenMW's MGEF indexes, components/esm3/loadmgef.cpp) */
enum {E_BURDEN=7,E_FEATHER=8,E_LEVITATE=10,E_DRAIN_ATTR=17,E_DRAIN_SKILL=21,E_DAMAGE_ATTR=22,E_DAMAGE_SKILL=26,
      E_DISINT_WEAPON=37,E_DISINT_ARMOR=38,E_CHAMELEON=40,E_SILENCE=46,E_BLIND=47,E_SOUND=48,E_DISPEL=57,
      E_SPELL_ABSORB=67,E_REFLECT=68,E_CURE_POISON=72,E_CURE_PARALYZE=73,E_RESTORE_ATTR=74,E_RESTORE_HEALTH=75,
      E_RESTORE_MAGICKA=76,E_RESTORE_FATIGUE=77,E_RESTORE_SKILL=78,E_ABSORB_ATTR=85,E_ABSORB_MAGICKA=87,
      E_ABSORB_SKILL=89,E_BOUND_DAGGER=120,E_BOUND_LONGBOW=125,E_EXTRA_SPELL=126,E_BOUND_CUIRASS=127,
      E_BOUND_HELM=128,E_BOUND_BOOTS=129,E_BOUND_SHIELD=130,E_BOUND_GLOVES=131};
/* rateEffect's first list: effects a fighter never casts */
static int ai_useless(int e){
    static const unsigned char useless[]={58,62,63,49,50,51,52,53,54,55,56,44,64,65,66,59,60,61,9,0,1,2,11,41,12,13,
                                          101,32,33,34,69,70,71,94,95,96,39,43,133,136,126,100,118,119};
    unsigned i;
    for(i=0;i<sizeof(useless);i++)if(useless[i]==e)return 1;
    return 0;
}
float AW_SpellAiEffectCost(const aw_spell_effect_t *e,const aw_mgef_t *m,float cost_mult){
    int has_mag=!(m->flags&AW_MGEF_NO_MAGNITUDE),has_dur=!(m->flags&AW_MGEF_NO_DURATION);
    int lo=has_mag?e->magnitude_min:1,hi=has_mag?e->magnitude_max:1,dur=has_dur?e->duration:1;
    float x;
    if(lo<1)lo=1;
    if(hi<1)hi=1;
    /* OpenMW clamps the duration to 1 unless the effect is applied once (a hardcoded flag the data lacks): the effects
     * that act each second (AW_EffectPerSecond) or have no duration take at least 1 */
    if(dur<1 && (AW_EffectPerSecond(e->effect) || !has_dur))dur=1;
    x=0.5f*(float)(lo+hi);
    x*=0.1f*m->base_cost;
    x*=(float)dur;
    x+=0.05f*(float)e->area*m->base_cost;
    return x*cost_mult;
}
static float has_on(const aw_spell_ai_t *c,int who,int effect){return c->has?c->has(c->ctx,who,effect):0;}
float AW_SpellAiRateEffect(const aw_spell_ai_t *c,const aw_spell_effect_t *e,const aw_mgef_t *m){
    float rating=1;int id=e->effect;
    if(ai_useless(id))return 0;
    if(id==E_CHAMELEON)rating*=c->inviso_mult;
    else if(id==E_BLIND){   /* only on an enemy standing with its weapon ready */
        if(!c->enemy || c->enemy_down || c->enemy_ready!=1)return 0;
    }else if(id==E_SOUND || id==E_SILENCE){   /* only on an enemy with magic ready (Sound: and not silenced) */
        if(!c->enemy || c->enemy_down || c->enemy_ready!=2)return 0;
        if(id==E_SOUND && has_on(c,1,E_SILENCE)>0)return 0;
    }
    else if(id==E_RESTORE_ATTR || id==E_RESTORE_SKILL)return 0;
    else if((id>=90 && id<=93) || id==97 || id==98 || id==99 || id==E_SPELL_ABSORB || id==E_REFLECT)return 0;
    else if((id>=79 && id<=84) || id==117)return 0;   /* the fortify effects */
    else if(id==E_BURDEN){   /* only to overburden an enemy that is not overburdened yet */
        float burden;
        if(!c->enemy || !c->enemy_inventory)return 0;
        burden=c->enemy_encumbrance-c->enemy_capacity;
        if(burden>0)return 0;
        if(.5f*(float)(e->magnitude_min+e->magnitude_max)>-burden)rating*=3;else return 0;
    }else if(id==E_FEATHER){   /* only for a caster that is overburdened, enough to lift it */
        float burden;
        if(!c->inventory)return 0;
        burden=c->encumbrance-c->capacity;
        if(burden<=0)return 0;
        if(.5f*(float)(e->magnitude_min+e->magnitude_max)>=burden)rating*=3;else return 0;
    }
    else if(id==E_LEVITATE)return 0;
    else if(id==E_BOUND_BOOTS || id==E_BOUND_HELM){if(!c->npc || c->beast)return 0;}
    else if(id==E_BOUND_SHIELD){if(!c->npc)return 0;}   /* a creature's one-handed weapon test: not rated here */
    else if(id==E_BOUND_CUIRASS || id==E_BOUND_GLOVES){if(!c->npc)return 0;}
    else if(id==E_ABSORB_MAGICKA){   /* an enemy with no magicka left: by the caster's own need for magicka */
        if(c->enemy && c->enemy_magicka<=0)rating=.5f*c->magicka_need;
    }
    else if(id==E_RESTORE_HEALTH || id==E_RESTORE_FATIGUE || id==E_RESTORE_MAGICKA){
        if(e->range==AW_RANGE_SELF){
            float cur=id==E_RESTORE_HEALTH?c->health:id==E_RESTORE_MAGICKA?c->magicka:c->fatigue;
            float mod=id==E_RESTORE_HEALTH?c->health_max:id==E_RESTORE_MAGICKA?c->magicka_max:c->fatigue_max;
            float mag=.5f*(float)(e->magnitude_min+e->magnitude_max),heal=mag*(float)(e->duration>1?e->duration:1);
            float damage=mod-cur>0?mod-cur:0,over=0,base,power=1;int k;
            float pr=id==E_RESTORE_HEALTH?4.0f:id==E_RESTORE_MAGICKA?(c->magicka_need>0?2.0f:0.0f):2.0f;
            if(!(mod>0))return 0;
            base=damage/mod+.6f;
            if(damage<heal && cur>mod*.5f){over=heal-damage;heal=damage;}
            /* pow(base, 2 x priority): the exponent is 8 or 4, a whole number: multiplied out (no libm pow, whose
             * 68040 code reaches unimplemented instructions) */
            for(k=0;k<(int)(pr*2);k++)power*=base;
            rating=(pr-1)/2*power+pr*(heal-2*over)/mod-.5f;
        }
    }
    else if(id==E_DISPEL){
        /* on itself: the harmful spell effects it would lose over the helpful ones; on the enemy the other way round */
        int pos,neg,diff;
        if(!c->dispel)return 0;
        if(e->range==AW_RANGE_SELF){pos=c->dispel(c->ctx,0,-1,0);neg=c->dispel(c->ctx,0,-1,1);diff=neg-pos;}
        else{
            if(!c->enemy)return 0;
            pos=c->dispel(c->ctx,1,-1,0);neg=c->dispel(c->ctx,1,-1,1);diff=pos-neg;
            rating*=-1;   /* below 0 here: aimed at the enemy, turned again at the end */
        }
        if(diff<=0)return 0;
        rating*=(float)diff/5.0f;
    }
    /* the cures before Dispel: 1001 for each such effect on itself */
    else if(id==E_CURE_PARALYZE)return c->dispel?1001.0f*(float)c->dispel(c->ctx,0,AW_EFFECT_PARALYZE,1):0;
    else if(id==E_CURE_POISON)return c->dispel?1001.0f*(float)c->dispel(c->ctx,0,AW_EFFECT_POISON,1):0;
    else if(id==E_DISINT_ARMOR){if(!c->enemy || !c->enemy_armor)return 0;}
    else if(id==E_DISINT_WEAPON){if(!c->enemy || !c->enemy_weapon)return 0;}
    else if(id==E_ABSORB_ATTR || id==E_DAMAGE_ATTR || id==E_DRAIN_ATTR){
        static const float priority[8]={1.0f,.5f,.6f,.7f,.5f,.8f,.7f,.3f};
        if(c->enemy && e->attribute>=0 && e->attribute<8 && c->enemy_attributes[e->attribute]<=0)return 0;
        if(e->attribute>=0 && e->attribute<8)rating*=priority[e->attribute];
    }
    else if(id==E_ABSORB_SKILL || id==E_DAMAGE_SKILL || id==E_DRAIN_SKILL){
        if(!c->enemy || !c->enemy_npc)return 0;
        if(e->skill>=0 && e->skill<27 && c->enemy_skills[e->skill]<=0)return 0;
    }
    /* one summoned creature at a time, rated above the rest */
    if(AW_EffectSummon(id)){
        int k;for(k=102;k<=142;k++)if(AW_EffectSummon(k) && has_on(c,0,k)>0)return 0;
        rating=3;
    }
    if((id>=E_BOUND_DAGGER && id<=E_BOUND_LONGBOW) || (id>=E_EXTRA_SPELL && id<=E_BOUND_GLOVES)){
        rating=2;   /* bound items before other spells */
        if(id>=E_BOUND_DAGGER && id<=E_BOUND_LONGBOW){
            static const int skill[6]={22,5,4,6,7,23};   /* short blade, long blade, blunt, axe, spear, marksman */
            int k;
            /* one bound weapon at a time; a bound bow out lets another kind be cast only while there are arrows (as
             * OpenMW 0.51's code reads, its comment says the other way round) */
            for(k=E_BOUND_DAGGER;k<=E_BOUND_LONGBOW;k++)
                if(has_on(c,0,k)>0 && (k!=E_BOUND_LONGBOW || id==k || !c->ammo))return 0;
            if(id==E_BOUND_LONGBOW && !c->ammo)return 0;   /* never the bow without arrows to shoot */
            rating*=(50.0f+c->skills[skill[id-E_BOUND_DAGGER]])/100.0f;
        }else if(has_on(c,0,id)>0)return 0;
    }
    /* no casting on a target under water, or from under water */
    if(e->range==AW_RANGE_TARGET && (c->underwater || !c->enemy || c->enemy_underwater))return 0;
    if(m->flags&AW_MGEF_HARMFUL){
        float r=c->resist?c->resist(c->ctx,id):0;
        rating*=-1;
        if(!c->enemy)return 0;
        rating*=1-(r<100?r:100)/100.0f;
    }
    /* a no-magnitude effect already on its target (harmful: the enemy; else the caster) */
    if(m->flags&AW_MGEF_NO_MAGNITUDE){
        if(has_on(c,(m->flags&AW_MGEF_HARMFUL)?1:0,id)>0)return 0;
    }
    rating*=AW_SpellAiEffectCost(e,m,c->effect_cost_mult);
    /* every Touch or Target effect is aimed at the enemy (OpenMW: never a helpful one at a friend) */
    if(e->range!=AW_RANGE_SELF)rating*=-1;
    return rating;
}
float AW_SpellAiRateSpell(const aw_spell_ai_t *c,int row,int type,const aw_spell_effect_t *e,const aw_mgef_t *m,int n,
                          float chance){
    float rating=0;int i,ranges;
    if(!(chance>0) || type!=AW_SPELL_TYPE_SPELL || n<=0)return 0;
    ranges=AW_CastRanges(e,n);
    /* spells do not stack: not while the same spell is active on its target */
    if(c->active){
        if((ranges&(1<<AW_RANGE_SELF)) && c->active(c->ctx,0,row))return 0;
        if((ranges&((1<<AW_RANGE_TOUCH)|(1<<AW_RANGE_TARGET))) && c->enemy && c->active(c->ctx,1,row))return 0;
    }
    for(i=0;i<n;i++){
        float r=AW_SpellAiRateEffect(c,&e[i],&m[i]);
        rating+=r*(e[i].range==AW_RANGE_TARGET?c->range_spell_mult:c->spell_mult);
    }
    return rating*(chance/100.0f);
}
float AW_SpellAiRateWeapon(const unsigned char damage[3][2],float strength_factor,float condition,float hit_chance,
                           float speed,int skill,float melee_mult){
    float ch=.5f*(damage[0][0]+damage[0][1]),sl=.5f*(damage[1][0]+damage[1][1]),th=.5f*(damage[2][0]+damage[2][1]);
    float rating,hit=hit_chance/100.0f;
    if(skill<=0 || ch+sl+th<=0)return 0;
    rating=(sl*sl+th*th+ch*ch)/(sl+th+ch);
    rating*=strength_factor*(condition>0 && condition<1?condition:1);
    rating*=hit<.01f?.01f:hit>1?1:hit;
    return rating*speed*melee_mult;
}
float AW_SpellAiCombatRange(int ranges,float combat_distance,float h2h_reach){
    if(ranges&(1<<AW_RANGE_TOUCH))return combat_distance;
    return combat_distance*(h2h_reach>2?h2h_reach:2)*4;
}
