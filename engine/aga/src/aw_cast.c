/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_cast.c: player casting, the engine glue (aw_cast.h; docs/MAGIC_EFFECTS.md "Casting").
 *
 * "dbg cast ready" (aw_magicfx ready, bound to R) readies or lowers the player's magic (the hands come up as for a
 * fight); with magic ready the attack button casts the selected spell instead of striking. "dbg cast spell" selects
 * it. The words live under aw_magicfx: no command or setting of their own (tests/resident_registry_budget.json). A cast, by OpenMW 0.51's rules (aw_cast.h): not enough magicka refuses it; else the magicka is paid, the
 * chance rolled (a failure plays the school's failure sound and says so); a success lands the Self effects on the
 * player, the Touch effects on the actor within reach (fCombatDistance, as a blow), and sends the Target effects as
 * a bolt (fTargetSpellMaxSpeed) that lands them on the actor it strikes and, with an area, on every actor within it.
 * The school's skill gets its use (LEVEL-UP-58). A power works once a day. "dbg cast casting off" turns it all off.
 * Burden and Feather on the player go to the encumbrance (AW_EncumbranceSetEffects, aw_move.h) when that exists.
 * The look (hand glow, cast, bolt, hit) is aw_magic.c's when aw_magic_fx is on.
 *
 * Cost: nothing resident but this file's state (about 0.3 KB); a spell's effects are read from the actor table
 * once when it is selected (one read of its AEFF rows and their AMGE rows); a bolt is one SV_Move a frame.
 *
 * Magic items (v0.0.61; OpenMW 0.51 spellcasting.cpp CastSpell::cast(item), combat.cpp applyOnStrikeEnchantment,
 * activespells.cpp the equipment's constant effects; docs/MAGIC_EFFECTS.md "Magic items"): the enchantment of an item
 * is read from the actor table's AENC row by the catalogue's enchantment id (or a made item's own effects), the last
 * one kept. Cast When Strikes: a weapon blow that hits or is blocked casts it on the victim (the player's weapon and
 * an NPC's), the charge paid by the Enchant skill; Cast When Used and Cast Once: with an item selected (aw_magic
 * select ID) and magic ready, the cast button uses it (no success roll; a scroll is used up), Self on the user, Touch
 * on the actor in reach, Target as a bolt; Constant Effect: a worn item's effects are active while it is worn (the
 * slot is checked each frame by comparing its id, the item read once when it changes). The charge of the player's
 * items is saved (AW_ITEM_CHARGE); an NPC weapon's spent charge is kept for the session only (16 weapons). */
#include <stdlib.h>
#include <string.h>
#include "quakedef.h"
#include "aw_cast.h"
#include "aw_effects.h"
#include "aw_character.h"
#include "aw_combat.h"
#include "aw_msgbox.h"
#include "aw_levelup.h"
#include "aw_ledger.h"
#include "aw_move.h"
#include "aw_statswin.h"
#include "aw_inventory.h"
#include "aw_hand_models.h"
#include "aw_reset.h"
#include "aw_story.h"
#include "aw_spelllist.h"
#include "aw_iteminfo.h"
#include "aw_tryalloc.h"
#include "aw_roll.h"

static void give_spell_command(int first);   /* DBG-GIVE-SPELL-67, below */
static int cast_on=1;              /* dbg cast casting on|off */
#define SCALE .25f                 /* original units -> map units (tools/prepare_quake.py SCALE) */
#define UNITS_PER_FOOT 21.333333f  /* original units a foot (an area's radius; OpenMW Constants::UnitsPerFoot) */
#define CAST_SECONDS .8f           /* one cast at a time: the spellcast group's length (until the hands' cast lands) */
#define BOLT_SPEED_DEFAULT 1000.0f /* fTargetSpellMaxSpeed of the masters, original units a second, when no table */
#define BOLT_SECONDS 6.0f          /* a bolt that hits nothing goes after this */
#define BOLTS 4
#define POWERS 8
/* the magic ready flag is the hands' (aw_hands.c aw_magic_readied: F and R are exclusive stances there) */
#define ready aw_magic_readied
static int held,light_set,sel_kind=-1,sel_index=-1;
static float last_burden,last_feather;
/* the selected spell, read once */
static struct {
    int valid,type,cost,n,school,always;char name[32];
    aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];
} spell;
static char item_seen[64];         /* the magic item selection last seen (a new one deselects the spell) */
static float lock_until;
/* a bolt in flight: TARGET the actor aimed at when it left (edict number, 0 none; the fight's own aim test, as NPCs
 * are not solid to a plain trace), its distance, and how far the bolt has flown */
typedef struct {
    int used,source,target,n;vec3_t at,vel;float until,target_dist,flown;
    int caster;   /* NPC-NO-SPELLCASTING-65: the edict number of an actor that cast it (0: the player's bolt) */
    aw_spell_effect_t e[AW_MADE_EFFECTS];uint32_t flags[AW_MADE_EFFECTS];   /* its own spell: a later selection does not change it */
} bolt_t;
static bolt_t bolts[BOLTS];
static struct {int spell;float hours;} powers[POWERS];   /* the powers used and the game hour of their use */
static unsigned long casts,fails,refused,landed;

int AW_CastReady(void){return ready;}
int AW_CastSelected(int *kind){if(kind)*kind=sel_kind;return sel_index;}

static int load_spell(void){
    int i;
    memset(&spell,0,sizeof(spell));
    if(sel_index<0)return 0;
    if(sel_kind==0){
        if(!AW_ActorSpellInfo(sel_index,&spell.type,spell.name,sizeof(spell.name),&spell.cost))return 0;
        spell.n=AW_ActorSpellEffects(sel_index,spell.e,AW_MADE_EFFECTS);
        spell.always=(AW_ActorSpellFlags(sel_index)&AW_SPELL_ALWAYS)!=0;   /* SPDT "always succeeds" */
    }else{
        const aw_made_spell_t *s=AW_MadeSpellAt(sel_index);
        if(!s)return 0;
        Q_strncpy(spell.name,(char *)s->name,sizeof(spell.name)-1);spell.name[sizeof(spell.name)-1]=0;
        spell.type=AW_SPELL_TYPE_SPELL;
        spell.n=s->effects>AW_MADE_EFFECTS?AW_MADE_EFFECTS:s->effects;
        for(i=0;i<spell.n;i++)spell.e[i]=s->effect[i];
        spell.cost=AW_DialwinMadeSpellCost(spell.e,spell.n);
        if(spell.cost<0)spell.cost=0;
    }
    for(i=0;i<spell.n;i++)if(!AW_ActorMagicEffect(spell.e[i].effect,&spell.m[i]))memset(&spell.m[i],0,sizeof(spell.m[i]));
    spell.valid=spell.n>0;
    /* the hands' cast by the first effect's range (OpenMW CharacterController: the spell's first effect) */
    if(spell.valid && (int)spell.e[0].range<=AW_RANGE_TARGET)aw_magic_cast_range=(int)spell.e[0].range;
    return spell.valid;
}
void AW_CastSelect(int kind,int index){
    sel_kind=index<0?-1:kind;sel_index=index;
    if(index>=0 && !load_spell()){Con_Printf("Magic: spell %d has no effects in this build.\n",index);sel_index=-1;}
    /* a spell or a magic item is selected, never both (OpenMW InventoryStore: selecting a spell clears the item) */
    if(sel_index>=0){AW_MagicClear(&aw_state);item_seen[0]=0;}
}
static int power_ready(int row){
    int i;float now=AW_LedgerGameHours();
    for(i=0;i<POWERS;i++)if(powers[i].spell==row+1 && now-powers[i].hours<24)return 0;
    return 1;
}
static void power_used(int row){
    int i,k=0;float now=AW_LedgerGameHours();
    for(i=0;i<POWERS;i++){if(powers[i].spell==row+1){k=i;break;}if(powers[i].hours<powers[k].hours)k=i;}
    powers[k].spell=row+1;powers[k].hours=now;
}
/* the chance now, 0..100 (the Magic window shows it too) */
float AW_CastChanceNow(void){
    float skills[27],fmax,f,mult=AW_DialwinEffectCostMult(),base;int i,school;aw_actor_t *p=AW_MwscriptPlayerRecord();
    if(!spell.valid || !p)return 0;
    for(i=0;i<27;i++)skills[i]=AW_ActorStat(p,AWA_SKILL+i);   /* modified: base + fortify - drain, damage */
    if(!(mult>0))mult=0.5f;   /* a build without the dialogue table: the masters' value */
    base=AW_CastBaseChance(spell.e,spell.m,spell.n,skills,AW_ActorStat(p,AWA_ATTRIBUTE+2),AW_ActorStat(p,AWA_ATTRIBUTE+7),
                           spell.cost,mult,&school);
    spell.school=school;
    f=AW_CombatPlayerFatigue(&fmax);
    return AW_CastChance(base,spell.type,sel_kind==0?power_ready(sel_index):1,spell.always,
                         AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_SILENCE,AW_EFFECT_NO_ARG),
                         AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_SOUND,AW_EFFECT_NO_ARG),
                         AW_CastFatigueTerm(1.25f,0.5f,f,fmax),AW_ActorStat(p,AWA_MAGICKA),spell.cost,0);
}
static void say(const char *text){AW_MsgBoxShow(text,NULL,0);}
static int first_of(const aw_spell_effect_t *e,int n,int range){int i;for(i=0;i<n;i++)if(e[i].range==range)return e[i].effect;return -1;}
static int first_mgef(int range){return first_of(spell.e,spell.n,range);}
static void eye(vec3_t at,vec3_t fwd){
    vec3_t right,up;
    VectorCopy(sv_player->v.origin,at);at[2]+=sv_player->v.view_ofs[2];
    AngleVectors(sv_player->v.v_angle,fwd,right,up);
}
static void touch_effects(const aw_spell_effect_t *e,const aw_mgef_t *m,int n,int source){
    float reach=aw_combat_settings.fCombatDistance*SCALE+16;
    edict_t *t=AW_NPCTargetReach(sv_player,sv_player->v.v_angle,reach);
    if(!t){Con_DPrintf("Touch: no actor within %.0f units in front\n",reach);return;}
    if(AW_MwscriptLand(t,e,m,n,AW_RANGE_TOUCH,source)>0)landed++;
}
static void touch(void){touch_effects(spell.e,spell.m,spell.n,sel_kind==0?sel_index:-1);}
static void launch_effects(const aw_spell_effect_t *e,const aw_mgef_t *m,int n,int source){
    int i;vec3_t fwd;
    for(i=0;i<BOLTS && bolts[i].used;i++);
    if(i==BOLTS)i=0;   /* the oldest place: at most BOLTS in flight */
    memset(&bolts[i],0,sizeof(bolts[i]));
    eye(bolts[i].at,fwd);
    VectorScale(fwd,BOLT_SPEED_DEFAULT*SCALE,bolts[i].vel);
    bolts[i].used=1;bolts[i].until=(float)sv.time+BOLT_SECONDS;bolts[i].source=source;
    bolts[i].n=n>AW_MADE_EFFECTS?AW_MADE_EFFECTS:n;
    {int k;for(k=0;k<bolts[i].n;k++){bolts[i].e[k]=e[k];bolts[i].flags[k]=m[k].flags;}}
    {   /* the actor in the line of the cast, within the bolt's whole flight */
        edict_t *t=AW_NPCTargetReach(sv_player,sv_player->v.v_angle,BOLT_SPEED_DEFAULT*SCALE*BOLT_SECONDS);
        if(t && t!=sv_player && GetEdictFieldValue(t,"aw_ref")){
            vec3_t d;VectorSubtract(t->v.origin,bolts[i].at,d);
            bolts[i].target=NUM_FOR_EDICT(t);bolts[i].target_dist=(float)Length(d);
            Con_DPrintf("Bolt: aimed at %s, %.0f units\n",t->v.netname?pr_strings+t->v.netname:"an actor",bolts[i].target_dist);
        }
    }
}
static void launch(void){launch_effects(spell.e,spell.m,spell.n,sel_kind==0?sel_index:-1);}
/* the bolt's own Target effects land on T (their records' flags are all the landing reads) */
static void bolt_land(const bolt_t *b,edict_t *t,int source){
    aw_mgef_t m[AW_MADE_EFFECTS];int k;
    memset(m,0,sizeof(m));
    for(k=0;k<b->n;k++)m[k].flags=b->flags[k];
    if(AW_MwscriptLand(t==sv_player?NULL:t,b->e,m,b->n,AW_RANGE_TARGET,source)>0)landed++;   /* NULL: the player */
}
/* every actor within the bolt's largest target area of AT (one pass over the edicts, at the explosion only) */
static void area_land(const bolt_t *b,const vec3_t at,edict_t *struck){
    int i,area=0;float radius;edict_t *e;
    for(i=0;i<b->n;i++)if(b->e[i].range==AW_RANGE_TARGET && b->e[i].area>area)area=b->e[i].area;
    if(!area)return;
    radius=(float)area*UNITS_PER_FOOT*SCALE;
    /* an actor's bolt reaches the player too; never its own caster */
    if(b->caster>0 && sv_player && !sv_player->free && struck!=sv_player){
        vec3_t d;VectorSubtract(sv_player->v.origin,at,d);
        if(Length(d)<=radius)bolt_land(b,sv_player,-1);
    }
    for(i=1,e=NEXT_EDICT(sv.edicts);i<sv.num_edicts;i++,e=NEXT_EDICT(e)){
        vec3_t d;
        if(e->free || e==struck || e==sv_player || i==b->caster || !GetEdictFieldValue(e,"aw_ref"))continue;
        VectorSubtract(e->v.origin,at,d);
        if(Length(d)>radius)continue;
        bolt_land(b,e,-1);
    }
}
/* ExplodeSpell (aw_cast.h): for each actor, the Self and Touch effects whose area reaches it (OpenMW explodeSpell:
 * each effect with an area hits the actors within its own radius); a pass over the edicts, once per call */
static int explode_on(edict_t *t,const vec3_t at,const aw_spell_effect_t *e,const aw_mgef_t *m,int n,int row){
    aw_spell_effect_t pick[AW_MADE_EFFECTS];aw_mgef_t pm[AW_MADE_EFFECTS];int i,k,range,hit=0;vec3_t d;float dist;
    VectorSubtract(t->v.origin,at,d);dist=(float)Length(d);
    for(range=AW_RANGE_SELF;range<=AW_RANGE_TOUCH;range++){
        for(i=k=0;i<n;i++)
            if(e[i].range==range && e[i].area>0 && dist<=(float)e[i].area*UNITS_PER_FOOT*SCALE){pick[k]=e[i];pm[k]=m[i];k++;}
        if(k && AW_MwscriptLand(t==sv_player?NULL:t,pick,pm,k,range,row)>0)hit=1;
    }
    return hit;
}
int AW_CastExplode(const float at[3],int row){
    aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];int i,n,hits=0;edict_t *t;float radius=0;
    n=row>=0?AW_ActorSpellEffects(row,e,AW_MADE_EFFECTS):0;
    if(n<=0)return -1;
    for(i=0;i<n;i++){
        if(!AW_ActorMagicEffect(e[i].effect,&m[i]))memset(&m[i],0,sizeof(m[i]));
        if(e[i].range!=AW_RANGE_TARGET && (float)e[i].area*UNITS_PER_FOOT*SCALE>radius)radius=(float)e[i].area*UNITS_PER_FOOT*SCALE;
    }
    if(sv_player && !sv_player->free)hits+=explode_on(sv_player,at,e,m,n,row);
    for(i=1,t=NEXT_EDICT(sv.edicts);i<sv.num_edicts;i++,t=NEXT_EDICT(t)){
        vec3_t d;
        if(t->free || t==sv_player || !GetEdictFieldValue(t,"aw_ref"))continue;
        VectorSubtract(t->v.origin,at,d);
        if(Length(d)>radius || !AW_MwscriptActorOf(t,NULL))continue;   /* only near actors: no record made for the rest */
        hits+=explode_on(t,at,e,m,n,row);
    }
    landed+=(unsigned long)hits;
    return hits;
}
/* Cast SPELL TARGET of a script (aw_cast.h; OpenMW 0.53 CastSpell::cast): the Self effects on the caster when it is
 * an actor, the Touch and Target effects on the target, landed at once (no bolt flies). */
int AW_CastOn(edict_t *caster,edict_t *target,int row){
    aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];int i,n,hits=0,range;
    n=row>=0?AW_ActorSpellEffects(row,e,AW_MADE_EFFECTS):0;
    if(n<=0)return -1;
    for(i=0;i<n;i++)if(!AW_ActorMagicEffect(e[i].effect,&m[i]))memset(&m[i],0,sizeof(m[i]));
    for(range=AW_RANGE_SELF;range<=AW_RANGE_TARGET;range++){
        aw_spell_effect_t pick[AW_MADE_EFFECTS];aw_mgef_t pm[AW_MADE_EFFECTS];int k=0;edict_t *on;
        for(i=0;i<n;i++)if(e[i].range==range){pick[k]=e[i];pm[k]=m[i];k++;}
        if(!k)continue;
        if(range==AW_RANGE_SELF){
            if(!caster || caster->free)continue;
            if(caster!=sv_player && !AW_MwscriptActorOf(caster,NULL))continue;   /* an object: nothing to change */
            on=caster==sv_player?NULL:caster;
        }else on=target;
        if(AW_MwscriptLand(on,pick,pm,k,range,row)>0)hits++;
    }
    landed+=(unsigned long)hits;
    return hits;
}
/* NPC-NO-SPELLCASTING-65 (aw_cast.h): an actor's cast at the release, delivered as the player's: Self on itself, Touch
 * on the target within REACH, Target as a bolt from its eye to the target's chest (the bolts above) */
static unsigned long actor_casts;
int AW_CastActorRelease(edict_t *caster,edict_t *target,int row,float reach){
    aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];int i,n,hits=0,ranges;edict_t *t;
    n=row>=0?AW_ActorSpellEffects(row,e,AW_MADE_EFFECTS):0;
    if(n<=0 || !caster || caster->free || !sv_player)return -1;
    t=target?target:sv_player;
    for(i=0;i<n;i++)if(!AW_ActorMagicEffect(e[i].effect,&m[i]))memset(&m[i],0,sizeof(m[i]));
    ranges=AW_CastRanges(e,n);actor_casts++;
    if(ranges&(1<<AW_RANGE_SELF)){
        if(AW_MwscriptLand(caster,e,m,n,AW_RANGE_SELF,row)>0)landed++;
        hits++;
    }
    if((ranges&(1<<AW_RANGE_TOUCH)) && !t->free){
        vec3_t d;float gap;
        VectorSubtract(t->v.origin,caster->v.origin,d);d[2]=0;
        gap=(float)Length(d)-caster->v.maxs[0]-t->v.maxs[0];
        if(gap<=reach && AW_MwscriptLand(t==sv_player?NULL:t,e,m,n,AW_RANGE_TOUCH,row)>0)landed++;
        hits++;
    }
    if(ranges&(1<<AW_RANGE_TARGET)){
        bolt_t *b;vec3_t to,d;float len;
        for(i=0;i<BOLTS && bolts[i].used;i++);
        if(i==BOLTS)i=0;
        b=&bolts[i];memset(b,0,sizeof(*b));
        VectorCopy(caster->v.origin,b->at);b->at[2]+=caster->v.mins[2]+(caster->v.maxs[2]-caster->v.mins[2])*.75f;
        VectorCopy(t->v.origin,to);to[2]+=(t->v.mins[2]+t->v.maxs[2])*.5f;
        VectorSubtract(to,b->at,d);len=(float)VectorNormalize(d);
        VectorScale(d,BOLT_SPEED_DEFAULT*SCALE,b->vel);
        b->used=1;b->until=(float)sv.time+BOLT_SECONDS;b->source=row;b->caster=NUM_FOR_EDICT(caster);
        b->target=NUM_FOR_EDICT(t);b->target_dist=len;
        b->n=n;
        for(i=0;i<n;i++){b->e[i]=e[i];b->flags[i]=m[i].flags;}
        hits++;
    }
    return hits;
}
unsigned long AW_CastActorCasts(void){return actor_casts;}
static void bolts_frame(float dt){
    int i;
    for(i=0;i<BOLTS;i++){
        bolt_t *b=&bolts[i];vec3_t end;trace_t tr;
        if(!b->used)continue;
        /* gone at its time, or when a map load started the clock again (a bolt never flies into another map) */
        if(sv.time>=b->until || b->until>(float)sv.time+BOLT_SECONDS){b->used=0;continue;}
        VectorMA(b->at,dt,b->vel,end);
        {   /* the trace passes through its own caster (the player, or the actor that cast it) */
            edict_t *from=b->caster>0 && b->caster<sv.num_edicts?EDICT_NUM(b->caster):sv_player;
            tr=SV_Move(b->at,vec3_origin,vec3_origin,end,MOVE_MISSILE,from);
        }
        if(b->target>0 && b->target<sv.num_edicts){
            /* the aimed actor is reached before the world stops the bolt: it lands there */
            edict_t *t=EDICT_NUM(b->target);float step=(float)Length(b->vel)*dt*(tr.fraction<1?tr.fraction:1);
            if(!t->free && b->flown+step>=b->target_dist){
                Con_DPrintf("Bolt: struck %s after %.1f s\n",t->v.netname?pr_strings+t->v.netname:"an actor",
                            BOLT_SECONDS-(b->until-(float)sv.time));
                bolt_land(b,t,b->source);
                area_land(b,t->v.origin,t);
                b->used=0;continue;
            }
            b->flown+=step;
        }
        if(tr.fraction>=1 && !tr.allsolid){VectorCopy(end,b->at);continue;}
        Con_DPrintf("Bolt: struck %s after %.1f s\n",tr.ent && tr.ent!=sv.edicts?
                    (tr.ent->v.netname?pr_strings+tr.ent->v.netname:"an object"):"the world",BOLT_SECONDS-(b->until-(float)sv.time));
        if(tr.ent && tr.ent!=sv.edicts && tr.ent!=sv_player && GetEdictFieldValue(tr.ent,"aw_ref"))bolt_land(b,tr.ent,b->source);
        else if(b->caster>0 && tr.ent==sv_player){bolt_land(b,sv_player,b->source);area_land(b,tr.endpos,sv_player);b->used=0;continue;}
        area_land(b,tr.endpos,tr.ent);
        b->used=0;
    }
}
/* ---- magic items (v0.0.61) ---- */
typedef struct {int n,type;float cost,charge;aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];} item_magic_t;
static struct {char id[64];int ok;item_magic_t v;} magic_kept[2];   /* the last two enchantments read, by id */
static int magic_kept_next;
static unsigned long item_uses,item_refused,item_strikes,npc_strikes,worn_landed,worn_refused;
#define ENCHANT_SKILL 9            /* the Enchant skill */
#define ENCHANT_USE_ITEM 1         /* its uses: Enchant_UseMagicItem, Enchant_CastOnStrike (SKIL SKDT) */
#define ENCHANT_USE_STRIKE 3
#define MADE_PREFIX_LEN ((int)sizeof(AW_MADE_ITEM_PREFIX)-1)
/* IT's enchantment: the game's (its AENC row by the catalogue's enchantment id) or a made item's own (aw_made_N) */
static int item_magic(const aw_inventory_item_t *it,item_magic_t *out){
    int i,k;
    if(!it || !it->enchantment[0] || it->enchant_kind==AW_ENCH_NONE)return 0;
    for(k=0;k<2;k++)if(magic_kept[k].id[0] && !strcmp(magic_kept[k].id,it->enchantment)){*out=magic_kept[k].v;return magic_kept[k].ok;}
    memset(out,0,sizeof(*out));
    if(!strncmp(it->enchantment,AW_MADE_ITEM_PREFIX,MADE_PREFIX_LEN)){
        const aw_made_item_t *mi=AW_MadeItemAt(atoi(it->enchantment+MADE_PREFIX_LEN));
        if(!mi)return 0;   /* not kept: the made item may come with a load */
        out->type=mi->cast_type;out->n=mi->effects>AW_MADE_EFFECTS?AW_MADE_EFFECTS:mi->effects;
        for(i=0;i<out->n;i++)out->e[i]=mi->effect[i];
        out->cost=AW_DialwinMadeItemCost(out->e,out->n,out->type==3);if(out->cost<0)out->cost=0;
        out->charge=mi->charge_max;
    }else{
        aw_enchant_t en;int row=AW_ActorEnchantFind(it->enchantment);
        if(row==AW_ACTOR_NONE || !AW_ActorEnchant(row,&en)){
            if(AW_ActorEnchantCount())Con_DPrintf("Magic item %s: no enchantment %s in this build.\n",it->id,it->enchantment);
            return 0;
        }
        out->type=en.type;out->n=en.n;out->cost=en.cost;out->charge=en.charge;
        for(i=0;i<en.n;i++)out->e[i]=en.effect[i];
    }
    for(i=0;i<out->n;i++)if(!AW_ActorMagicEffect(out->e[i].effect,&out->m[i]))memset(&out->m[i],0,sizeof(out->m[i]));
    k=magic_kept_next;magic_kept_next=(magic_kept_next+1)%2;
    Q_strncpy(magic_kept[k].id,(char *)it->enchantment,sizeof(magic_kept[k].id)-1);magic_kept[k].id[sizeof(magic_kept[k].id)-1]=0;
    magic_kept[k].v=*out;magic_kept[k].ok=out->n>0;
    return out->n>0;
}
/* INVENTORY-ITEM-INFO-67 (aw_iteminfo.h aw_worldui_enchant_lines): IT's enchantment as the original's tooltip lists
 * it, one line per effect ("Jump 10 pts for 30 secs on Self"; a Constant Effect's without duration and range), the
 * effect's name and the attribute or skill it names as the spell lists build them (aw_spelllist.c); '\n' between.
 * One read of the enchantment's rows, when the information box opens. 1 when it wrote any. */
static int item_magic_lines(const aw_inventory_item_t *it,char *out,int size){
    item_magic_t mg;aw_sl_effect_t x;char line[AW_SL_TEXT*2];int i,at=0,group,n;
    if(!out || size<1)return 0;
    out[0]=0;
    if(!item_magic(it,&mg))return 0;
    for(i=0;i<mg.n;i++){
        memset(&x,0,sizeof(x));
        x.effect=mg.e[i].effect;x.range=mg.e[i].range;x.area=mg.e[i].area;x.duration=mg.e[i].duration;
        x.min=mg.e[i].magnitude_min;x.max=mg.e[i].magnitude_max;x.flags=mg.m[i].flags;
        Q_strncpy(x.name,mg.m[i].name,sizeof(x.name)-1);
        AW_EffectKind(mg.e[i].effect,&group);
        if(group==0 && mg.e[i].attribute>=0)Q_strncpy(x.arg,(char *)AW_StatsAttributeName(mg.e[i].attribute),sizeof(x.arg)-1);
        else if(group==4 && mg.e[i].skill>=0)Q_strncpy(x.arg,(char *)AW_StatsSkillName(mg.e[i].skill),sizeof(x.arg)-1);
        n=AW_SpellEffectText(&x,mg.type==AW_ENCH_CONSTANT-1,line,sizeof(line));
        if(at && at<size-1)out[at++]='\n';
        if(at+n>size-1)n=size-1-at;
        if(n>0){memcpy(out+at,line,(size_t)n);at+=n;}
        out[at]=0;
    }
    return at>0;
}
/* OpenMW CastSpell::cast(item) for the player's IT (ENCHANTMENT MG): the charge of a When Used or When Strikes item
 * by the Enchant skill (refused with the failure sound when too little; god mode free), the skill's use, a Cast Once
 * item used up; then Self on the player, Touch on TARGET, and Target on TARGET (a strike) or as a bolt (a use, BOLT).
 * 1 when it was cast. */
static int item_cast(const aw_inventory_item_t *it,const item_magic_t *mg,edict_t *target,int bolt){
    aw_actor_t *p=AW_MwscriptPlayerRecord();int god=((int)sv_player->v.flags&FL_GODMODE)!=0,ranges;
    if(!p)return 0;
    if(!god && (mg->type==AW_ENCH_STRIKES-1 || mg->type==AW_ENCH_USED-1)){
        int cost=AW_CastItemCost(mg->cost,AW_ActorStat(p,AWA_SKILL+ENCHANT_SKILL));
        float now=AW_MagicCharge(&aw_state,it),left=AW_CastItemCharge(now,cost);
        if(left<0){
            item_refused++;say("Item does not have enough charge.");   /* sMagicInsufficientCharge */
            AW_MagicCastLook(mg->e[0].effect,mg->e[0].range,1,0);
            Con_DPrintf("Magic item %s: charge %.1f, a use takes %d\n",it->name,now,cost);
            return 0;
        }
        AW_MagicSetCharge(&aw_state,it,left);
        Con_DPrintf("Magic item %s: charge %.1f -> %.1f of %.0f (cost %d)\n",it->name,now,left,it->charge_max,cost);
    }
    if(mg->type==AW_ENCH_USED-1)AW_LevelupUse(ENCHANT_SKILL,ENCHANT_USE_ITEM,1);
    else if(mg->type==AW_ENCH_STRIKES-1)AW_LevelupUse(ENCHANT_SKILL,ENCHANT_USE_STRIKE,1);
    else if(mg->type==AW_ENCH_ONCE-1 && !god)AW_ItemAdd(&aw_state,it->id,-1);   /* a scroll is gone */
    ranges=AW_CastRanges(mg->e,mg->n);
    if(ranges&(1<<AW_RANGE_SELF)){
        if(AW_MwscriptLand(NULL,mg->e,mg->m,mg->n,AW_RANGE_SELF,AW_EFFECT_SOURCE_ITEM)>0)landed++;
        if(bolt)AW_MagicCastLook(first_of(mg->e,mg->n,AW_RANGE_SELF),AW_RANGE_SELF,0,0);
    }
    if(ranges&(1<<AW_RANGE_TOUCH)){
        if(target){if(AW_MwscriptLand(target,mg->e,mg->m,mg->n,AW_RANGE_TOUCH,AW_EFFECT_SOURCE_ITEM)>0)landed++;}
        else if(bolt)touch_effects(mg->e,mg->m,mg->n,AW_EFFECT_SOURCE_ITEM);
        if(bolt)AW_MagicCastLook(first_of(mg->e,mg->n,AW_RANGE_TOUCH),AW_RANGE_TOUCH,0,0);
    }
    if(ranges&(1<<AW_RANGE_TARGET)){
        if(bolt){launch_effects(mg->e,mg->m,mg->n,AW_EFFECT_SOURCE_ITEM);AW_MagicCastLook(first_of(mg->e,mg->n,AW_RANGE_TARGET),AW_RANGE_TARGET,0,0);}
        else if(target && AW_MwscriptLand(target,mg->e,mg->m,mg->n,AW_RANGE_TARGET,AW_EFFECT_SOURCE_ITEM)>0)landed++;
    }
    return 1;
}
/* Cast When Used / Cast Once: the selected item, with magic ready (the cast button) or dbg cast now; and (SCROLL-CAST-64,
 * v0.0.67) a Cast Once item used in the inventory window. 1 when it was cast. */
static int use_item(const aw_inventory_item_t *it){
    item_magic_t mg;
    if(it->enchant_kind!=AW_ENCH_USED && it->enchant_kind!=AW_ENCH_ONCE)return 0;
    if(!item_magic(it,&mg)){say("This item has no effect in this build.");return 0;}
    lock_until=(float)sv.time+CAST_SECONDS;
    if(!item_cast(it,&mg,NULL,1))return 0;
    item_uses++;
    Con_Printf("Used %s (%s): %d effects, %d left.\n",it->name,it->enchant_kind==AW_ENCH_ONCE?"cast once":"when used",mg.n,
               (int)AW_StateGet(&aw_state,AW_ITEM,it->id));
    return 1;
}
/* WEAPON-STRIKE-ENCHANT-NOT-CAST-61 (aw_combat.h aw_combat_strike_enchant): a blow of ATTACKER reached VICTIM */
#define NPC_CHARGES 16
static struct {uint32_t ref;int item;float charge;} npc_charge[NPC_CHARGES];static int npc_charge_next;
static void strike_enchant(edict_t *attacker,edict_t *victim){
    if(!cast_on || !sv.active || !sv_player || !attacker || !victim)return;
    if(attacker==sv_player){
        aw_inventory_item_t it;item_magic_t mg;
        if(!AW_InventoryEquippedItem(AW_SLOT_RIGHT,&it) || it.enchant_kind!=AW_ENCH_STRIKES || !item_magic(&it,&mg) ||
           mg.type!=AW_ENCH_STRIKES-1)return;
        if(item_cast(&it,&mg,victim,0))item_strikes++;
        return;
    }
    {   /* an NPC's or a creature's weapon (its actor table row's held weapon): its charge kept for the session */
        aw_actor_t *a;int row,item=-1,ench,k,god=((int)sv_player->v.flags&FL_GODMODE)!=0,cost;aw_enchant_t en;item_magic_t mg;
        if(!(a=AW_MwscriptActorOf(attacker,&row)) || row==AW_ACTOR_NONE)return;
        if((ench=AW_ActorWeaponEnchant(row,&item))==AW_ACTOR_NONE || !AW_ActorEnchant(ench,&en) || en.type!=AW_ENCH_STRIKES-1)return;
        memset(&mg,0,sizeof(mg));mg.n=en.n;
        for(k=0;k<en.n;k++){mg.e[k]=en.effect[k];if(!AW_ActorMagicEffect(en.effect[k].effect,&mg.m[k]))memset(&mg.m[k],0,sizeof(mg.m[k]));}
        cost=AW_CastItemCost(en.cost,AW_ActorStat(a,AWA_SKILL+ENCHANT_SKILL));
        for(k=0;k<NPC_CHARGES && !(npc_charge[k].ref==a->reference && npc_charge[k].item==item);k++);
        if(k==NPC_CHARGES){k=npc_charge_next;npc_charge_next=(npc_charge_next+1)%NPC_CHARGES;
                           npc_charge[k].ref=a->reference;npc_charge[k].item=item;npc_charge[k].charge=en.charge;}
        if(AW_CastItemCharge(npc_charge[k].charge,cost)<0){Con_DPrintf("Strike: the weapon's charge is spent\n");return;}
        npc_charge[k].charge-=(float)cost;
        npc_strikes++;
        /* OpenMW CastSpell::cast(item): Self on the attacker, Touch and Target on the victim (god mode: the player
         * takes no harm from it, as from the blow) */
        AW_MwscriptLand(attacker,mg.e,mg.m,mg.n,AW_RANGE_SELF,AW_EFFECT_SOURCE_ITEM);
        if(victim==sv_player && god)return;
        AW_MwscriptLand(victim,mg.e,mg.m,mg.n,AW_RANGE_TOUCH,AW_EFFECT_SOURCE_ITEM);
        AW_MwscriptLand(victim,mg.e,mg.m,mg.n,AW_RANGE_TARGET,AW_EFFECT_SOURCE_ITEM);
    }
}
/* Constant Effect: each equipment slot's worn item; a changed slot's effects go (undone) and the new item's land, each
 * magnitude rolled once (OpenMW ActiveSpells::update, Flag_Equipment). After a load or a reset every slot again. */
static char worn_id[AW_INVENTORY_SLOTS][64];static unsigned long worn_generation;
static void worn_frame(void){
    int s,k;aw_actor_t *p=NULL;int all=AW_EffectsGeneration()!=worn_generation;
    for(s=0;s<AW_INVENTORY_SLOTS;s++){
        const char *id=aw_state.inventory.equipped[s];aw_inventory_item_t it;item_magic_t mg;
        if(id[0] && AW_StateGet(&aw_state,AW_ITEM,id)<1)id="";
        if(!all && !strcmp(worn_id[s],id))continue;
        if(!p && !(p=AW_MwscriptPlayerRecord()))return;
        AW_EffectsRemoveSource(p,AW_EFFECT_SOURCE_CONSTANT+s);
        Q_strncpy(worn_id[s],(char *)id,sizeof(worn_id[s])-1);worn_id[s][sizeof(worn_id[s])-1]=0;
        if(!id[0] || !AW_InventoryRead(id,&it) || it.enchant_kind!=AW_ENCH_CONSTANT || !item_magic(&it,&mg) ||
           mg.type!=AW_ENCH_CONSTANT-1)continue;
        for(k=0;k<mg.n;k++){
            float mag=mg.m[k].flags&AW_MGEF_NO_MAGNITUDE?1:AW_CastMagnitude(mg.e[k].magnitude_min,mg.e[k].magnitude_max,
                                                                              (float)AW_Roll(32768)/32768.0f);
            int arg=mg.e[k].attribute>=0?mg.e[k].attribute:mg.e[k].skill>=0?mg.e[k].skill:AW_EFFECT_NO_ARG;
            if(AW_EffectsLand(p,mg.e[k].effect,arg,mag,AW_EFFECT_CONSTANT,AW_EFFECT_SOURCE_CONSTANT+s))worn_landed++;
            else worn_refused++;
        }
        Con_DPrintf("Worn %s: %d constant effects\n",it.name,mg.n);
    }
    worn_generation=AW_EffectsGeneration();
    if(p)AW_MwscriptPlayerStore(p);
}
/* PLAYER-CASTING-59 (v0.0.66): a cast goes in two steps, as the original's spellcast group: at the press the refusals
 * (no spell, the magicka, a used power; OpenMW World::startSpellCast), then the hands' cast starts (aw_hands.c), and
 * at its release key (AW_HandCastReleaseNow: the attack clip's release frame) the magicka is paid, the roll made and
 * the spell leaves (CastSpell::cast at the "release" text key). pending: a cast between its start and its release. */
static int pending;static float release_at;
static int looks[3];   /* CAST-EGG-SYNC-62: the pending cast's held looks per range (AW_MagicCastLookStart), 0 none */
/* the refusals of a cast before it starts; 1 = it may start. P: the player's record. */
static int cast_allowed(aw_actor_t *p,int god){
    /* OpenMW World::startSpellCast: the magicka first; a used power refuses as well */
    if(!god && spell.cost>0 && p->dyn_cur[1]<(float)spell.cost){
        refused++;say("You do not have enough Magicka to cast the spell.");return 0;   /* sMagicInsufficientSP */
    }
    if(spell.type==AW_SPELL_TYPE_POWER && sel_kind==0 && !power_ready(sel_index)){
        refused++;say("You can only use this power once a day.");return 0;          /* sPowerAlreadyUsed */
    }
    return 1;
}
static void cast_release(void);
static void cast_now(void){
    aw_actor_t *p;float delay;
    if(!cast_on || !sv.active || !sv_player || sv_player->v.health<=0)return;
    /* a map load starts the server clock again: a lock from the last map never holds past one cast's length (seen
     * in game 6 November 2026: after a teleport across maps no cast went off for minutes) */
    if(lock_until>(float)sv.time+CAST_SECONDS)lock_until=0;
    if(sv.time<lock_until || pending)return;
    if(sel_index<0 || !spell.valid){
        aw_inventory_item_t it;
        if(AW_MagicSelectedItem(&it)){use_item(&it);return;}   /* Cast When Used / Cast Once (v0.0.61) */
        say("You have no spell selected.");return;
    }
    if(!(p=AW_MwscriptPlayerRecord())){Con_Printf("Casting: no player record in this build.\n");return;}
    lock_until=(float)sv.time+CAST_SECONDS;
    if(!cast_allowed(p,((int)sv_player->v.flags&FL_GODMODE)!=0))return;
    /* the hands' cast; the spell leaves at its release (at once when the image has no hand table or the hands are
     * not up: the cast never waits on the look) */
    delay=AW_HandsCastStart()?AW_HandCastReleaseNow(0):0;
    if(delay>0 && delay<CAST_SECONDS){
        /* CAST-EGG-SYNC-62: the look (hand glow, cast sound, the shell) starts now, with the cast animation; it waits
         * for the release below */
        int r,ranges=AW_CastRanges(spell.e,spell.n);
        for(r=0;r<3;r++)looks[r]=ranges&(1<<r)?AW_MagicCastLookStart(0,first_mgef(r),r,0):0;
        pending=1;release_at=(float)sv.time+delay;return;
    }
    cast_release();
}
/* the held looks of the pending cast end (AW_MagicCastLookRelease): OK 1 the spell left, each range's look goes on;
 * 0 the roll failed, one failure sound; -1 the cast was dropped, the looks end quietly */
static void looks_release(int ok){
    int r,first=1;
    for(r=0;r<3;r++)if(looks[r]){AW_MagicCastLookRelease(looks[r],ok==0 && !first?-1:ok);first=0;looks[r]=0;}
}
static void cast_release(void){
    float chance;int roll,ranges,god,look_held=looks[0] || looks[1] || looks[2];aw_actor_t *p;
    pending=0;
    if(!cast_on || !sv.active || !sv_player || sv_player->v.health<=0 || sel_index<0 || !spell.valid ||
       !(p=AW_MwscriptPlayerRecord())){looks_release(-1);return;}
    /* god mode (Quake's, dbg god on): no magicka paid and the cast always succeeds (OpenMW startSpellCast and
     * getSpellSuccessChance: godmode) */
    god=((int)sv_player->v.flags&FL_GODMODE)!=0;
    if(!cast_allowed(p,god)){looks_release(-1);return;}   /* the magicka spent since the start (another cast, a drain) */
    chance=god?100.0f:AW_CastChanceNow();
    if(spell.type==AW_SPELL_TYPE_SPELL && !god){p->dyn_cur[1]-=(float)spell.cost;AW_MwscriptPlayerStore(p);}
    roll=AW_Roll(100);
    if(roll>=(int)chance && chance<100){   /* CastSpell::cast: roll0to99 >= chance fails */
        /* sMagicSkillFail; the school's failure sound comes with the look (aw_magic_fx), not yet without it */
        fails++;say("You failed casting the spell.");
        Con_DPrintf("Cast %s failed: roll %d, chance %.0f %%, magicka %.0f left\n",spell.name,roll,chance,p->dyn_cur[1]);
        if(look_held)looks_release(0);else AW_MagicCastLook(spell.e[0].effect,spell.e[0].range,1,0);
        return;
    }
    casts++;
    Con_DPrintf("Cast %s: roll %d under %.0f %%, magicka %.0f left, ranges %s%s%s\n",spell.name,roll,chance,p->dyn_cur[1],
                AW_CastRanges(spell.e,spell.n)&1?"self ":"",AW_CastRanges(spell.e,spell.n)&2?"touch ":"",
                AW_CastRanges(spell.e,spell.n)&4?"target":"");
    if(spell.type==AW_SPELL_TYPE_POWER && sel_kind==0)power_used(sel_index);
    if(spell.type==AW_SPELL_TYPE_SPELL)AW_LevelupUse(AW_CastSchoolSkill(spell.school),0,1);   /* Spellcast_Success */
    ranges=AW_CastRanges(spell.e,spell.n);
    /* the looks: a held cast's (started with the animation) leave now; a cast without the hands' animation plays
     * its whole look from here, as before */
    if(look_held)looks_release(1);
    if(ranges&(1<<AW_RANGE_SELF)){
        if(AW_MwscriptLand(NULL,spell.e,spell.m,spell.n,AW_RANGE_SELF,sel_kind==0?sel_index:-1)>0)landed++;
        if(!look_held)AW_MagicCastLook(first_mgef(AW_RANGE_SELF),AW_RANGE_SELF,0,0);
    }
    if(ranges&(1<<AW_RANGE_TOUCH)){touch();if(!look_held)AW_MagicCastLook(first_mgef(AW_RANGE_TOUCH),AW_RANGE_TOUCH,0,0);}
    if(ranges&(1<<AW_RANGE_TARGET)){launch();if(!look_held)AW_MagicCastLook(first_mgef(AW_RANGE_TARGET),AW_RANGE_TARGET,0,0);}
}
/* SCROLL-CAST-64 (aw_inventory.h aw_worldui_cast): the inventory window's Use on a Cast Once item, cast at once as the
 * cast button casts a selected magic item (the maintainer's decision of 18 November 2026: a scroll is used, not read),
 * with the cast button's refusals: casting off, no game, dead, a script's DisablePlayerMagic or DisablePlayerControls
 * (OpenMW playercontrols.lua: no spell stance then), a cast still under way. The magic window's Magic Items stay. */
static int inventory_cast(const aw_inventory_item_t *it){
    if(!it || it->enchant_kind!=AW_ENCH_ONCE || !cast_on || !sv.active || !sv_player || sv_player->v.health<=0)return 0;
    if(!AW_ControlAllowed(AW_CONTROL_PLAYER|AW_CONTROL_MAGIC)){say("You cannot use magic now.");return 0;}
    if(lock_until>(float)sv.time+CAST_SECONDS)lock_until=0;
    if(sv.time<lock_until || pending)return 0;
    return use_item(it);
}

/* one carried item of AW_InventoryCarried: a Magic Items row when it can be cast (AW_MagicSelectable) */
static void window_item(void *ctx,int state_row,const aw_inventory_item_t *it,int file_row){
    aw_magic_list_t *out=(aw_magic_list_t *)ctx;(void)file_row;
    if(!it || out->count>=32 || !AW_MagicSelectable(it) || AW_ITEM_ROW(&aw_state,state_row)->value<=0)return;
    Q_strncpy(out->name[out->count],(char *)(it->name[0]?it->name:it->id),47);out->name[out->count][47]=0;
    out->power[out->count]=2;out->kind[out->count]=2;out->index[out->count]=state_row;
    if(sel_index<0 && aw_state.magic.selected[0] && !strcmp(aw_state.magic.selected,it->id))out->selected=out->count;
    out->count++;
}
/* the Magic window (aw_statswin.c): the spells and powers the player knows, the made spells, the selection */
static int window_castables(aw_magic_list_t *out){
    aw_actor_t *p=AW_ActorPlayer();int known[64],n=p?AW_ActorSpells(p,known,64):0,i,type,cost;char name[32];
    out->count=0;out->selected=-1;
    for(i=0;i<n && out->count<32;i++){
        if(!AW_ActorSpellInfo(known[i],&type,name,sizeof(name),&cost) || (type!=AW_SPELL_TYPE_SPELL && type!=AW_SPELL_TYPE_POWER))continue;
        Q_strncpy(out->name[out->count],name,47);out->name[out->count][47]=0;
        out->power[out->count]=(unsigned char)(type==AW_SPELL_TYPE_POWER);
        out->kind[out->count]=0;out->index[out->count]=known[i];
        if(sel_kind==0 && sel_index==known[i])out->selected=out->count;
        out->count++;
    }
    for(i=0;i<AW_MadeSpellCount() && out->count<32;i++){
        Q_strncpy(out->name[out->count],(char *)AW_MadeSpellAt(i)->name,47);out->name[out->count][47]=0;
        out->power[out->count]=0;out->kind[out->count]=1;out->index[out->count]=i;
        if(sel_kind==1 && sel_index==i)out->selected=out->count;
        out->count++;
    }
    /* SCROLL-CAST-64: the Magic Items (OpenMW 0.51 spellmodel.cpp: every carried item whose enchantment is Cast Once
     * or Cast When Used), from one pass over the item file as the inventory window opens it */
    if(out->count<32)AW_InventoryCarried(window_item,out);
    if(out->selected>=0)out->cursor=out->selected;
    return out->count;
}
static void window_select(int kind,int index){
    if(kind==2){   /* a magic item: its row in the player's item table */
        aw_inventory_item_t it;
        if(index<0 || index>=AW_ItemCount(&aw_state) || !AW_InventoryRead(AW_ITEM_ID(&aw_state,index),&it) ||
           !AW_MagicSelect(&aw_state,&it)){say("Cannot select that item.");return;}
        sel_kind=-1;sel_index=-1;memset(&spell,0,sizeof(spell));   /* an item or a spell, never both */
        Q_strncpy(item_seen,aw_state.magic.selected,sizeof(item_seen)-1);item_seen[sizeof(item_seen)-1]=0;
        return;
    }
    AW_CastSelect(kind,index);
}
static int window_status(char *out,int size){
    aw_inventory_item_t it;
    if(!spell.valid && AW_MagicSelectedItem(&it)){
        if(it.enchant_kind==AW_ENCH_ONCE)Q_snprintf(out,size,"%s: cast once, %d carried",it.name,(int)AW_StateGet(&aw_state,AW_ITEM,it.id));
        else Q_snprintf(out,size,"%s: charge %.0f of %.0f",it.name,AW_MagicCharge(&aw_state,&it),it.charge_max);
        return 1;
    }
    if(!spell.valid)return 0;
    Q_snprintf(out,size,"%s: cost %d, chance %.0f %%",spell.name,spell.cost,AW_CastChanceNow());
    return 1;
}
static void ready_reset(int new_game){(void)new_game;ready=0;held=0;pending=0;release_at=0;memset(looks,0,sizeof(looks));aw_magic_cast_range=AW_RANGE_TARGET;}
/* HANDS-STATE-LOST-THROUGH-DOORS-67: P is the player entity a spawned client plays (not a map's entity still waiting
 * for the client during a load) */
static int player_spawned(const edict_t *p){
    return svs.clients && svs.maxclients>=1 && svs.clients[0].active && svs.clients[0].spawned && svs.clients[0].edict==p;
}
void AW_CastFrame(void){
    edict_t *p=sv_player;
    aw_magic_castables=window_castables;aw_magic_select=window_select;aw_magic_status=window_status;
    aw_combat_strike_enchant=strike_enchant;
    aw_worldui_cast=inventory_cast;   /* SCROLL-CAST-64: Use on a scroll in the inventory window */
    aw_worldui_enchant_lines=item_magic_lines;   /* INVENTORY-ITEM-INFO-67: an enchantment's lines in its box */
    aw_inventory_give_spell=give_spell_command;  /* DBG-GIVE-SPELL-67: dbg give spell, through the inventory command */
    if(!sv.active || !p || p->free)return;
    bolts_frame((float)host_frametime);
    /* a magic item newly selected (aw_magic select ID) deselects the spell */
    if(strcmp(item_seen,aw_state.magic.selected)){
        Q_strncpy(item_seen,aw_state.magic.selected,sizeof(item_seen)-1);item_seen[sizeof(item_seen)-1]=0;
        if(item_seen[0] && sel_index>=0){sel_kind=-1;sel_index=-1;memset(&spell,0,sizeof(spell));}
    }
    AW_ResetRegister("cast ready",ready_reset,NULL);   /* idempotent: New Game lowers the magic */
    if(cast_on)worn_frame();
    /* Light on the player: Quake's own entity light (EF_DIMLIGHT, the client's dynamic light) while the effect lasts
     * (OpenMW: a light attached to the actor while its Light magnitude is above 0); only the bit set here is cleared */
    if(AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_LIGHT,AW_EFFECT_NO_ARG)>0){
        if(!((int)p->v.effects&EF_DIMLIGHT)){p->v.effects=(float)((int)p->v.effects|EF_DIMLIGHT);light_set=1;}
    }else if(light_set){p->v.effects=(float)((int)p->v.effects&~EF_DIMLIGHT);light_set=0;}
    {   /* Burden and Feather: their magnitudes to the encumbrance when they change (v0.0.61-inventory's call) */
        float burden=AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_BURDEN,AW_EFFECT_NO_ARG);
        float feather=AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_FEATHER,AW_EFFECT_NO_ARG);
        if(burden!=last_burden || feather!=last_feather){
            last_burden=burden;last_feather=feather;
#ifdef AW_ENCUMBRANCE_EFFECTS
            AW_EncumbranceSetEffects(burden,feather);
#endif
        }
    }
    /* a cast between its start and its release (a map load restarts the clock: one never waits past a cast's length) */
    if(pending && (release_at>(float)sv.time+CAST_SECONDS || p->v.health<=0)){pending=0;looks_release(-1);}
    if(pending && sv.time>=release_at)cast_release();
    if(!ready || !cast_on)return;
    /* HANDS-STATE-LOST-THROUGH-DOORS-67: only the spawned player's death lowers the magic. While a door, a teleport or
     * a cell change loads, the server runs frames on the new map's player entity before the client has spawned in it
     * (Quake's SV_RunClients sets sv_player first), its health still 0: since 6a3b897f9 (v0.0.61-dev2) that lowered
     * the readied magic, and since the magic and the weapon share the hands (1a0e3a3aa, v0.0.65) the hands, carried up
     * through the door, then showed the weapon stance (the fists) instead of the spell stance. */
    if(p->v.health<=0){if(player_spawned(p))ready=0;return;}
    /* with magic ready the attack button is the cast: taken before the fight and the hands see it */
    if(p->v.button0){
        if(!held)cast_now();   /* once per press; a held button never repeats */
        held=1;p->v.button0=0;
    }else held=0;
}
static void ready_command(void){
    eval_t *goal;int g;
    if(!cast_on)return;
    if(!sv.active || !sv_player){Con_Printf("Ready magic: no game.\n");return;}
    /* OPENING-FIGHTING-ON-BEFORE-PAPERS-66: a script's DisablePlayerMagic (CharGen's, from the ship until the papers)
     * or DisablePlayerControls: the magic is not readied; lowering it stays allowed (OpenMW 0.51 playercontrols.lua
     * ToggleSpell: the spell stance only with the Magic switch on, the stance left at any time) */
    if(!ready && !AW_ControlAllowed(AW_CONTROL_PLAYER|AW_CONTROL_MAGIC)){
        Con_DPrintf("Ready magic: switched off by a script.\n");return;}
    /* READY-MAGIC-SHOWS-WEAPON-65: the spell stance: the empty hands come up (the weapon is put away), and go down
     * with the magic; from the weapon stance the hands stay up and only the weapon goes */
    goal=GetEdictFieldValue(sv_player,"aw_hand_goal");g=goal && goal->_float!=0;
    AW_HandReadyPress(AW_READY_MAGIC_KEY,&g,&ready);
    if(goal)goal->_float=(float)g;
    if(ready && sel_index<0 && !aw_state.magic.selected[0])say("You have no spell selected.");
    Con_DPrintf("Magic %s.\n",ready?"ready":"lowered");
}
/* the words after "spell": Cmd_Argv(A) is the first */
#define ARG(k) Cmd_Argv(A+(k))
#define ARGS (Cmd_Argc()-A)
static void spell_command(int A){
    aw_actor_t *p=AW_ActorPlayer();int known[64],n=p?AW_ActorSpells(p,known,64):0,i,type,cost;char name[32];
    if(ARGS<1 || !Q_strcasecmp(ARG(0),"list")){
        for(i=0;i<n;i++)if(AW_ActorSpellInfo(known[i],&type,name,sizeof(name),&cost) && (type==0 || type==5))
            Con_Printf(" %d %s (%s, %d)%s\n",known[i],name,type?"power":"spell",cost,sel_kind==0 && sel_index==known[i]?" *":"");
        for(i=0;i<AW_MadeSpellCount();i++)Con_Printf(" m%d %s (made)%s\n",i,AW_MadeSpellAt(i)->name,sel_kind==1 && sel_index==i?" *":"");
        if(spell.valid)Con_Printf("Selected: %s, cost %d, chance %.0f %%; %lu cast, %lu failed, %lu refused, %lu landed\n",
                                  spell.name,spell.cost,AW_CastChanceNow(),casts,fails,refused,landed);
        {aw_inventory_item_t it;
         if(AW_MagicSelectedItem(&it))Con_Printf("Selected item: %s, charge %.1f of %.0f\n",it.name,AW_MagicCharge(&aw_state,&it),it.charge_max);
         if(AW_InventoryEquippedItem(AW_SLOT_RIGHT,&it) && it.enchant_kind!=AW_ENCH_NONE)
             Con_Printf("Weapon: %s, charge %.1f of %.0f\n",it.name,AW_MagicCharge(&aw_state,&it),it.charge_max);}
        Con_Printf("Magic items: %lu used, %lu refused, %lu of your strikes cast, %lu NPC strikes cast; worn: %lu effects on, %lu refused\n",
                   item_uses,item_refused,item_strikes,npc_strikes,worn_landed,worn_refused);
        AW_MwscriptResistReport();   /* RACE-RESIST-NOT-ON-SPELL-DAMAGE-64 */
        {   /* the player's active effects now: effect number, its attribute or skill, magnitude, seconds left (worn:
             * the slot of the item it comes with) */
            aw_effect_info_t e;int k;aw_actor_t *r=AW_MwscriptPlayerRecord();
            for(k=0;AW_EffectsAt(k,&e);k++){
                if(e.owner!=AW_ACTOR_PLAYER_REF)continue;
                if(e.source>=AW_EFFECT_SOURCE_CONSTANT)Con_Printf(" effect %d arg %d magnitude %.0f worn (slot %d)\n",e.effect,e.arg,e.magnitude,
                                                                  e.source-AW_EFFECT_SOURCE_CONSTANT);
                else Con_Printf(" effect %d arg %d magnitude %.0f %.0f s left%s\n",e.effect,e.arg,e.magnitude,e.left,
                                e.source>=AW_EFFECT_SOURCE_ITEM?" (an item's)":"");
            }
            if(r)Con_Printf("Attributes %.0f %.0f %.0f %.0f %.0f %.0f %.0f %.0f; health %.0f/%.0f magicka %.0f/%.0f\n",
                            AW_ActorStat(r,AWA_ATTRIBUTE),AW_ActorStat(r,AWA_ATTRIBUTE+1),AW_ActorStat(r,AWA_ATTRIBUTE+2),
                            AW_ActorStat(r,AWA_ATTRIBUTE+3),AW_ActorStat(r,AWA_ATTRIBUTE+4),AW_ActorStat(r,AWA_ATTRIBUTE+5),
                            AW_ActorStat(r,AWA_ATTRIBUTE+6),AW_ActorStat(r,AWA_ATTRIBUTE+7),r->dyn_cur[0],r->dyn_base[0],
                            r->dyn_cur[1],r->dyn_base[1]);
        }
        return;
    }
    if(!Q_strcasecmp(ARG(0),"none")){AW_CastSelect(0,-1);return;}
    /* for tests: give the player spell N (an ASPT row) as the scripts' AddSpell does, and select it. No search by name:
     * the table is on disk a row at a time, and a search over it made 6 to 9 s frames on FS-UAE (5 November 2026) */
    if(!Q_strcasecmp(ARG(0),"grant") && ARGS>=2){
        int row=ARG(1)[0]>='0' && ARG(1)[0]<='9'?Q_atoi(ARG(1)):-1;
        if(!p || row<0 || !AW_ActorSpellInfo(row,&type,name,sizeof(name),&cost)){Con_Printf("dbg cast spell grant: no spell %s\n",ARG(1));return;}
        Con_Printf("%s %s (%d).\n",AW_ActorAddSpell(p,row)?"Granted":"Could not grant",name,row);
        AW_CastSelect(0,row);
        if(spell.valid)Con_Printf("Selected %s: cost %d, chance %.0f %%.\n",spell.name,spell.cost,AW_CastChanceNow());
        return;
    }
    /* for tests: "spell make EFFECT RANGE AREA DURATION MAGNITUDE" adds a one-effect made spell as the Spellmaking
     * window does (RANGE 0 self, 1 touch, 2 target) and selects it (SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62: the
     * falling mage's Slowfall save) */
    if(!Q_strcasecmp(ARG(0),"make") && ARGS>=6){
        aw_made_spell_t m;int k;
        memset(&m,0,sizeof(m));Q_strncpy(m.name,"Test spell",sizeof(m.name));m.effects=1;
        m.effect[0].effect=(int16_t)Q_atoi(ARG(1));m.effect[0].skill=m.effect[0].attribute=-1;
        m.effect[0].range=(unsigned char)Q_atoi(ARG(2));m.effect[0].area=(unsigned short)Q_atoi(ARG(3));
        m.effect[0].duration=(unsigned short)Q_atoi(ARG(4));
        m.effect[0].magnitude_min=m.effect[0].magnitude_max=(unsigned short)Q_atoi(ARG(5));
        if((k=AW_MadeSpellAdd(&m))<0){Con_Printf("dbg cast spell make: refused\n");return;}
        AW_CastSelect(1,k);
        if(spell.valid)Con_Printf("Selected %s (m%d): cost %d, chance %.0f %%.\n",spell.name,k,spell.cost,AW_CastChanceNow());
        return;
    }
    if(ARG(0)[0]=='m')AW_CastSelect(1,Q_atoi(ARG(0)+1));
    else AW_CastSelect(0,Q_atoi(ARG(0)));
    if(spell.valid)Con_Printf("Selected %s: cost %d, chance %.0f %%.\n",spell.name,spell.cost,AW_CastChanceNow());
}
#undef ARG
#undef ARGS
/* ---- DBG-GIVE-SPELL-67: dbg give spell [ID / all / list [N]] (the maintainer, 18 November 2026: the spells of the
 * game's files, one or all of them in their base form) ----
 * The list is the actor table's spells (ASPT: every spell an actor, a script, the starting rule or a trap names) of the
 * kinds a player can know and cast: spells and powers (abilities, blights, diseases and curses are not given). It is
 * read once when the box opens or a word needs it (about seven small reads a row), held while the box is open and
 * freed when it closes; nothing resident. The player's list keeps at most AW_ACTOR_SPELLS changes. */
#include "aw_listbox.h"
#define GIVE_SPELL_LABEL 56
typedef struct {int row;unsigned char power;char label[GIVE_SPELL_LABEL];} give_spell_t;
static give_spell_t *gs;static int gs_n,gs_ms;
static void gs_free(void){free(gs);gs=NULL;gs_n=0;}
static int gs_order(const void *a,const void *b){
    return Q_strcasecmp((char *)((const give_spell_t *)a)->label,(char *)((const give_spell_t *)b)->label);
}
/* every spell and power of the table, by name: "Fireball (fireball)", "Mark [power] (mark)"; how many */
static int gs_load(void){
    int rows=AW_ActorSpellCount(),i,type,cost;char name[32],id[40];double t0=Sys_FloatTime();
    gs_free();
    if(rows<=0 || !(gs=(give_spell_t *)AW_TryCalloc((unsigned long)rows,sizeof(*gs))))return 0;
    for(i=0;i<rows;i++){
        if(!AW_ActorSpellInfo(i,&type,name,sizeof(name),&cost) || (type!=AW_SPELL_TYPE_SPELL && type!=AW_SPELL_TYPE_POWER))
            continue;
        AW_ActorSpellId(i,id,sizeof(id));
        gs[gs_n].row=i;gs[gs_n].power=(unsigned char)(type==AW_SPELL_TYPE_POWER);
        Q_snprintf(gs[gs_n].label,GIVE_SPELL_LABEL,"%s%s (%s)",name[0]?name:id,type==AW_SPELL_TYPE_POWER?" [power]":"",id);
        gs_n++;
    }
    if(gs_n>1)qsort(gs,(size_t)gs_n,sizeof(*gs),gs_order);
    gs_ms=(int)((Sys_FloatTime()-t0)*1000);
    return gs_n;
}
/* give row ROW to the player: 1 given, 2 already known, 0 refused (no room in the player's list) */
static int give_spell_row(int row){
    aw_actor_t *p=AW_ActorPlayer();
    if(!p)return 0;
    if(AW_ActorHasSpell(p,row))return 2;
    return AW_ActorAddSpell(p,row)?1:0;
}
static const char *gs_label(void *ctx,int row){(void)ctx;return row>=0 && row<gs_n?gs[row].label:"";}
static int gs_category(void *ctx,int row){(void)ctx;return row>=0 && row<gs_n && gs[row].power?2:1;}
static void gs_chosen(void *ctx,int row){
    int r;char line[96];(void)ctx;
    if(row<0 || row>=gs_n)return;
    r=give_spell_row(gs[row].row);
    Q_snprintf(line,sizeof(line),r==1?"You learn %s.":r==2?"You already know %s.":"No room for %s in your spells.",gs[row].label);
    say(line);Con_Printf("%s\n",line);
}
static void gs_closed(void *ctx){(void)ctx;gs_free();}
static void give_spell_command(int first){
    int argc=Cmd_Argc()-first,i,given=0,known=0,no_room=0;const char *w=argc>0?Cmd_Argv(first):"";
    if(!AW_ActorSpellCount()){Con_Printf("dbg give spell: no spell table in this build.\n");return;}
    if(!AW_ActorPlayer()){Con_Printf("dbg give spell: no game.\n");return;}
    if(argc==0){   /* the list box: Spells and Powers, type to search, Enter gives one */
        static const char *const cats[3]={"All","Spells","Powers"};
        aw_listbox_spec_t spec;
        if(!gs_load()){Con_Printf("dbg give spell: no spell to list.\n");return;}
        memset(&spec,0,sizeof(spec));
        spec.title="Give a spell (Enter: learn it)";spec.count=gs_n;spec.label=gs_label;spec.chosen=gs_chosen;
        spec.closed=gs_closed;spec.category_names=cats;spec.categories=3;spec.category=gs_category;
        Con_Printf("dbg give spell: %d spells and powers, read in %d ms.\n",gs_n,gs_ms);
        if(!AW_ListBoxOpen(&spec)){Con_Printf("dbg give spell: the list cannot open now (dbg give spell list [N]).\n");gs_free();}
        return;
    }
    if(!Q_strcasecmp((char *)w,"list")){   /* the same list on the console, a page of 20 */
        int page=argc>1?Q_atoi(Cmd_Argv(first+1)):1,pages;
        if(!gs_load()){Con_Printf("dbg give spell: no spell to list.\n");return;}
        pages=(gs_n+19)/20;if(page<1)page=1;if(page>pages)page=pages;
        for(i=(page-1)*20;i<gs_n && i<page*20;i++)Con_Printf(" %s\n",gs[i].label);
        Con_Printf("Page %d of %d (%d spells and powers; dbg give spell list N, dbg give spell ID, dbg give spell all).\n",
                   page,pages,gs_n);
        gs_free();return;
    }
    if(!Q_strcasecmp((char *)w,"all")){   /* every listed one, in its base form */
        if(!gs_load()){Con_Printf("dbg give spell: no spell to list.\n");return;}
        for(i=0;i<gs_n;i++){int r=give_spell_row(gs[i].row);if(r==1)given++;else if(r==2)known++;else no_room++;}
        Con_Printf("dbg give spell all: %d learnt, %d known before, %d refused (the player's list keeps %d changes) of %d.\n",
                   given,known,no_room,AW_ACTOR_SPELLS,gs_n);
        {char line[96];Q_snprintf(line,sizeof(line),"You learn %d spells and powers.",given);say(line);}
        gs_free();return;
    }
    {   /* one by its record id, case ignored */
        char id[40];int rows=AW_ActorSpellCount(),type,cost,r;char name[32];
        for(i=0;i<rows;i++)if(AW_ActorSpellId(i,id,sizeof(id)) && !Q_strcasecmp(id,(char *)w))break;
        if(i==rows || !AW_ActorSpellInfo(i,&type,name,sizeof(name),&cost)){
            Con_Printf("dbg give spell: no spell %s in this build (dbg give spell list).\n",w);return;}
        if(type!=AW_SPELL_TYPE_SPELL && type!=AW_SPELL_TYPE_POWER){
            Con_Printf("dbg give spell: %s is not a spell or a power (type %d).\n",w,type);return;}
        r=give_spell_row(i);
        Con_Printf("%s %s (%s).\n",r==1?"Learnt":r==2?"Already known:":"No room for",name[0]?name:id,id);
        if(r==1){char line[96];Q_snprintf(line,sizeof(line),"You learn %s.",name[0]?name:id);say(line);}
    }
}
/* aw_magicfx's words for casting (no command or setting of its own: the resident registry budget): "ready" (R),
 * "spell ...", "now", "casting on|off". 1 when the word was one of these. */
int AW_CastCommand(void){
    const char *w=Cmd_Argc()>=2?Cmd_Argv(1):"";
    if(!Q_strcasecmp((char *)w,"ready")){ready_command();return 1;}
    if(!Q_strcasecmp((char *)w,"spell")){spell_command(2);return 1;}
    if(!Q_strcasecmp((char *)w,"now")){cast_now();return 1;}
    if(!Q_strcasecmp((char *)w,"start")){AW_MwscriptStartSpellsReport();return 1;}   /* the starting spells chosen */
    if(!Q_strcasecmp((char *)w,"strike")){   /* for tests: the held weapon's blow lands on the actor in reach */
        edict_t *t;
        if(!sv.active || !sv_player){Con_Printf("Strike: no game.\n");return 1;}
        t=AW_NPCTargetReach(sv_player,sv_player->v.v_angle,aw_combat_settings.fCombatDistance*SCALE+16);
        if(!t){Con_Printf("Strike: no actor in reach.\n");return 1;}
        strike_enchant(sv_player,t);
        Con_Printf("Strike on %s: %lu of your strikes cast.\n",t->v.netname?pr_strings+t->v.netname:"an actor",item_strikes);
        return 1;
    }
    if(!Q_strcasecmp((char *)w,"casting")){
        if(Cmd_Argc()>=3)cast_on=Q_strcasecmp(Cmd_Argv(2),"off") && strcmp(Cmd_Argv(2),"0");
        else cast_on=!cast_on;   /* DBG-SUPERSPEED-62: bare turns it the other way */
        if(!cast_on){ready=0;held=0;}
        Con_Printf("Casting %s.\n",cast_on?"on":"off");
        return 1;
    }
    return 0;
}
