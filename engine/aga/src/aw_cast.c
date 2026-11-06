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
 * once when it is selected (one read of its AEFF rows and their AMGE rows); a bolt is one SV_Move a frame. */
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

static int cast_on=1;              /* dbg cast casting on|off */
#define SCALE .25f                 /* original units -> map units (tools/prepare_quake.py SCALE) */
#define UNITS_PER_FOOT 21.333333f  /* original units a foot (an area's radius; OpenMW Constants::UnitsPerFoot) */
#define CAST_SECONDS .8f           /* one cast at a time: the spellcast group's length (until the hands' cast lands) */
#define BOLT_SPEED_DEFAULT 1000.0f /* fTargetSpellMaxSpeed of the masters, original units a second, when no table */
#define BOLT_SECONDS 6.0f          /* a bolt that hits nothing goes after this */
#define BOLTS 4
#define POWERS 8
static int ready,held,light_set,sel_kind=-1,sel_index=-1;
static float last_burden,last_feather;
/* the selected spell, read once */
static struct {
    int valid,type,cost,n,school;char name[32];
    aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];
} spell;
static float lock_until;
/* a bolt in flight: TARGET the actor aimed at when it left (edict number, 0 none; the fight's own aim test, as NPCs
 * are not solid to a plain trace), its distance, and how far the bolt has flown */
typedef struct {
    int used,source,target,n;vec3_t at,vel;float until,target_dist,flown;
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
    return spell.valid;
}
void AW_CastSelect(int kind,int index){
    sel_kind=index<0?-1:kind;sel_index=index;
    if(index>=0 && !load_spell()){Con_Printf("Magic: spell %d has no effects in this build.\n",index);sel_index=-1;}
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
    return AW_CastChance(base,spell.type,sel_kind==0?power_ready(sel_index):1,0,
                         AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_SILENCE,AW_EFFECT_NO_ARG),
                         AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_SOUND,AW_EFFECT_NO_ARG),
                         AW_CastFatigueTerm(1.25f,0.5f,f,fmax),AW_ActorStat(p,AWA_MAGICKA),spell.cost,0);
}
static void say(const char *text){AW_MsgBoxShow(text,NULL,0);}
static int first_mgef(int range){int i;for(i=0;i<spell.n;i++)if(spell.e[i].range==range)return spell.e[i].effect;return -1;}
static void eye(vec3_t at,vec3_t fwd){
    vec3_t right,up;
    VectorCopy(sv_player->v.origin,at);at[2]+=sv_player->v.view_ofs[2];
    AngleVectors(sv_player->v.v_angle,fwd,right,up);
}
static void touch(void){
    float reach=aw_combat_settings.fCombatDistance*SCALE+16;
    edict_t *t=AW_NPCTargetReach(sv_player,sv_player->v.v_angle,reach);
    if(!t){Con_DPrintf("Touch: no actor within %.0f units in front\n",reach);return;}
    if(AW_MwscriptLand(t,spell.e,spell.m,spell.n,AW_RANGE_TOUCH,sel_kind==0?sel_index:-1)>0)landed++;
}
static void launch(void){
    int i;vec3_t fwd;
    for(i=0;i<BOLTS && bolts[i].used;i++);
    if(i==BOLTS)i=0;   /* the oldest place: at most BOLTS in flight */
    memset(&bolts[i],0,sizeof(bolts[i]));
    eye(bolts[i].at,fwd);
    VectorScale(fwd,BOLT_SPEED_DEFAULT*SCALE,bolts[i].vel);
    bolts[i].used=1;bolts[i].until=(float)sv.time+BOLT_SECONDS;bolts[i].source=sel_kind==0?sel_index:-1;
    bolts[i].n=spell.n;
    {int k;for(k=0;k<spell.n;k++){bolts[i].e[k]=spell.e[k];bolts[i].flags[k]=spell.m[k].flags;}}
    {   /* the actor in the line of the cast, within the bolt's whole flight */
        edict_t *t=AW_NPCTargetReach(sv_player,sv_player->v.v_angle,BOLT_SPEED_DEFAULT*SCALE*BOLT_SECONDS);
        if(t && t!=sv_player && GetEdictFieldValue(t,"aw_ref")){
            vec3_t d;VectorSubtract(t->v.origin,bolts[i].at,d);
            bolts[i].target=NUM_FOR_EDICT(t);bolts[i].target_dist=(float)Length(d);
            Con_DPrintf("Bolt: aimed at %s, %.0f units\n",t->v.netname?pr_strings+t->v.netname:"an actor",bolts[i].target_dist);
        }
    }
}
/* the bolt's own Target effects land on T (their records' flags are all the landing reads) */
static void bolt_land(const bolt_t *b,edict_t *t,int source){
    aw_mgef_t m[AW_MADE_EFFECTS];int k;
    memset(m,0,sizeof(m));
    for(k=0;k<b->n;k++)m[k].flags=b->flags[k];
    if(AW_MwscriptLand(t,b->e,m,b->n,AW_RANGE_TARGET,source)>0)landed++;
}
/* every actor within the bolt's largest target area of AT (one pass over the edicts, at the explosion only) */
static void area_land(const bolt_t *b,const vec3_t at,edict_t *struck){
    int i,area=0;float radius;edict_t *e;
    for(i=0;i<b->n;i++)if(b->e[i].range==AW_RANGE_TARGET && b->e[i].area>area)area=b->e[i].area;
    if(!area)return;
    radius=(float)area*UNITS_PER_FOOT*SCALE;
    for(i=1,e=NEXT_EDICT(sv.edicts);i<sv.num_edicts;i++,e=NEXT_EDICT(e)){
        vec3_t d;
        if(e->free || e==struck || e==sv_player || !GetEdictFieldValue(e,"aw_ref"))continue;
        VectorSubtract(e->v.origin,at,d);
        if(Length(d)>radius)continue;
        bolt_land(b,e,-1);
    }
}
static void bolts_frame(float dt){
    int i;
    for(i=0;i<BOLTS;i++){
        bolt_t *b=&bolts[i];vec3_t end;trace_t tr;
        if(!b->used)continue;
        /* gone at its time, or when a map load started the clock again (a bolt never flies into another map) */
        if(sv.time>=b->until || b->until>(float)sv.time+BOLT_SECONDS){b->used=0;continue;}
        VectorMA(b->at,dt,b->vel,end);
        tr=SV_Move(b->at,vec3_origin,vec3_origin,end,MOVE_MISSILE,sv_player);
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
        area_land(b,tr.endpos,tr.ent);
        b->used=0;
    }
}
static void cast_now(void){
    float chance;int roll,ranges,god;aw_actor_t *p;
    if(!cast_on || !sv.active || !sv_player || sv_player->v.health<=0)return;
    /* a map load starts the server clock again: a lock from the last map never holds past one cast's length (seen
     * in game 6 November 2026: after a teleport across maps no cast went off for minutes) */
    if(lock_until>(float)sv.time+CAST_SECONDS)lock_until=0;
    if(sv.time<lock_until)return;
    if(sel_index<0 || !spell.valid){say("You have no spell selected.");return;}
    if(!(p=AW_MwscriptPlayerRecord())){Con_Printf("Casting: no player record in this build.\n");return;}
    lock_until=(float)sv.time+CAST_SECONDS;
    /* god mode (Quake's, dbg god on): no magicka paid and the cast always succeeds (OpenMW startSpellCast and
     * getSpellSuccessChance: godmode) */
    god=((int)sv_player->v.flags&FL_GODMODE)!=0;
    /* OpenMW World::startSpellCast: the magicka first; a used power refuses as well */
    if(!god && spell.cost>0 && p->dyn_cur[1]<(float)spell.cost){
        refused++;say("You do not have enough Magicka to cast the spell.");return;   /* sMagicInsufficientSP */
    }
    if(spell.type==AW_SPELL_TYPE_POWER && sel_kind==0 && !power_ready(sel_index)){
        refused++;say("You can only use this power once a day.");return;          /* sPowerAlreadyUsed */
    }
    chance=god?100.0f:AW_CastChanceNow();
    if(spell.type==AW_SPELL_TYPE_SPELL && !god){p->dyn_cur[1]-=(float)spell.cost;AW_MwscriptPlayerStore(p);}
    roll=rand()%100;
    if(roll>=(int)chance && chance<100){   /* CastSpell::cast: roll0to99 >= chance fails */
        /* sMagicSkillFail; the school's failure sound comes with the look (aw_magic_fx), not yet without it */
        fails++;say("You failed casting the spell.");
        Con_DPrintf("Cast %s failed: roll %d, chance %.0f %%, magicka %.0f left\n",spell.name,roll,chance,p->dyn_cur[1]);
        AW_MagicCastLook(spell.e[0].effect,spell.e[0].range,1,0);
        return;
    }
    casts++;
    Con_DPrintf("Cast %s: roll %d under %.0f %%, magicka %.0f left, ranges %s%s%s\n",spell.name,roll,chance,p->dyn_cur[1],
                AW_CastRanges(spell.e,spell.n)&1?"self ":"",AW_CastRanges(spell.e,spell.n)&2?"touch ":"",
                AW_CastRanges(spell.e,spell.n)&4?"target":"");
    if(spell.type==AW_SPELL_TYPE_POWER && sel_kind==0)power_used(sel_index);
    if(spell.type==AW_SPELL_TYPE_SPELL)AW_LevelupUse(AW_CastSchoolSkill(spell.school),0,1);   /* Spellcast_Success */
    ranges=AW_CastRanges(spell.e,spell.n);
    if(ranges&(1<<AW_RANGE_SELF)){
        if(AW_MwscriptLand(NULL,spell.e,spell.m,spell.n,AW_RANGE_SELF,sel_kind==0?sel_index:-1)>0)landed++;
        AW_MagicCastLook(first_mgef(AW_RANGE_SELF),AW_RANGE_SELF,0,0);
    }
    if(ranges&(1<<AW_RANGE_TOUCH)){touch();AW_MagicCastLook(first_mgef(AW_RANGE_TOUCH),AW_RANGE_TOUCH,0,0);}
    if(ranges&(1<<AW_RANGE_TARGET)){launch();AW_MagicCastLook(first_mgef(AW_RANGE_TARGET),AW_RANGE_TARGET,0,0);}
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
    if(out->selected>=0)out->cursor=out->selected;
    return out->count;
}
static void window_select(int kind,int index){AW_CastSelect(kind,index);}
static int window_status(char *out,int size){
    if(!spell.valid)return 0;
    Q_snprintf(out,size,"%s: cost %d, chance %.0f %%",spell.name,spell.cost,AW_CastChanceNow());
    return 1;
}
void AW_CastFrame(void){
    edict_t *p=sv_player;
    aw_magic_castables=window_castables;aw_magic_select=window_select;aw_magic_status=window_status;
    if(!sv.active || !p || p->free)return;
    bolts_frame((float)host_frametime);
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
    if(!ready || !cast_on)return;
    if(p->v.health<=0){ready=0;return;}
    /* with magic ready the attack button is the cast: taken before the fight and the hands see it */
    if(p->v.button0){
        if(!held)cast_now();   /* once per press; a held button never repeats */
        held=1;p->v.button0=0;
    }else held=0;
}
static void ready_command(void){
    eval_t *goal;
    if(!cast_on)return;
    if(!sv.active || !sv_player){Con_Printf("Ready magic: no game.\n");return;}
    ready=!ready;
    /* the hands come up as for a fight, and go down with the magic */
    if((goal=GetEdictFieldValue(sv_player,"aw_hand_goal"))!=NULL)goal->_float=ready?1:0;
    if(ready && sel_index<0)say("You have no spell selected.");
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
    if(ARG(0)[0]=='m')AW_CastSelect(1,Q_atoi(ARG(0)+1));
    else AW_CastSelect(0,Q_atoi(ARG(0)));
    if(spell.valid)Con_Printf("Selected %s: cost %d, chance %.0f %%.\n",spell.name,spell.cost,AW_CastChanceNow());
}
#undef ARG
#undef ARGS
/* aw_magicfx's words for casting (no command or setting of its own: the resident registry budget): "ready" (R),
 * "spell ...", "now", "casting on|off". 1 when the word was one of these. */
int AW_CastCommand(void){
    const char *w=Cmd_Argc()>=2?Cmd_Argv(1):"";
    if(!Q_strcasecmp((char *)w,"ready")){ready_command();return 1;}
    if(!Q_strcasecmp((char *)w,"spell")){spell_command(2);return 1;}
    if(!Q_strcasecmp((char *)w,"now")){cast_now();return 1;}
    if(!Q_strcasecmp((char *)w,"casting")){
        if(Cmd_Argc()>=3)cast_on=Q_strcasecmp(Cmd_Argv(2),"off") && strcmp(Cmd_Argv(2),"0");
        if(!cast_on){ready=0;held=0;}
        Con_Printf("Casting %s.\n",cast_on?"on":"off");
        return 1;
    }
    return 0;
}
