/* SPDX-License-Identifier: GPL-2.0-or-later
 * Held and falling actors (v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61; docs/MWSCRIPT_BYTECODE.md "Held actors and falls").
 *
 * The original's falling mage north of Seyda Neen stands on an invisible platform; his journal's script disables the
 * platform and the game's physics drops him (OpenMW 0.51: World::disable takes the platform's collision away, the
 * actor falls under gravity, mwphysics/movementsolver.cpp, and the landing's fall damage kills him,
 * mwmechanics/character.cpp). The same holds for any actor the builder finds standing on an object some script
 * disables (tools/mwscript/events.py, the HELD section of id1/mwscript.awm, one row an actor). Here:
 * - HELD: while the object is in the world the actor stays at its placed position (the builder's row; no ground snap,
 *   aw_scene.c AW_NPCFloor asks aw_fall_held);
 * - FALLING: once the object is disabled (or taken), the actor falls with OpenMW's gravity in physics steps of 1/60 s,
 *   Slowfall on the actor slowing it (aw_move_rules.c AW_MoveFallStep), the drop counted as the fall height (none
 *   while a Slowfall is on), until its hull meets the ground or water. It starts only once something is under it
 *   (the streamed ground may not be collidable yet: COMBAT-CHASE-CHIM-STUCK-46);
 * - LANDED: the fall damage of AW_MoveFallLoss (its Acrobatics, the Jump magnitude and its fatigue from its actor
 *   record) comes off its health, the game's Health Damage sound plays on it; at 0 it dies as by a blow (OnDeath
 *   reads 1, the body is laid down and can be searched).
 * Cost: nothing while the file has no HELD rows; else one look over the edicts every half second for held actors (a
 * float compare each) and per tracked actor a few traces a frame while it falls (at most FALLS at once).
 */
#include "quakedef.h"
#include "aw_move.h"
#include "aw_mwvm.h"
#include "aw_effects.h"
#include "aw_actorstate.h"
#include "aw_combat.h"
#include "aw_world.h"
#include "aw_actors.h"

extern int (*aw_fall_held)(edict_t *e);          /* aw_scene.c */
int AW_ObjectDisabled(unsigned int reference);    /* aw_mwhost.c */
aw_actor_t *AW_MwscriptActorOf(edict_t *e,int *row);

#define FALLS 8
#define SKILL_ACROBATICS 20
#define FALL_MAX 40000.0f        /* original units: no ground met by then (a hole in the streamed world): it lands */
enum {HELD,WAITING,FALLING,LANDED};
static const char *state_names[]={"held","waiting for ground","falling","landed"};
typedef struct {int edict,state;uint32_t ref,support;float vz,height;} fall_t;
static fall_t falls[FALLS];static int nfalls;
static void *map_of;static double next_scan;
static struct {unsigned long scans,tracked,full,fell,landed,water,hurt,killed,no_record,slowed;float height,loss;} st;

static int is_actor(edict_t *e){
    const char *c;
    if(e->free || !e->v.classname)return 0;
    c=pr_strings+e->v.classname;
    return !strcmp(c,"aw_npc") || !strcmp(c,"aw_creature");
}
static uint32_t ref_of(edict_t *e){
    eval_t *v=GetEdictFieldValue(e,"aw_ref");
    return v && v->_float>=1 && v->_float<=16777215.0f?(uint32_t)v->_float:0;
}
/* aw_fall_held: an actor of a HELD row whose object is still there */
static int held(edict_t *e){
    uint32_t ref,support;int row;
    if(!AW_MwvmHeldCount() || !is_actor(e) || !(ref=ref_of(e)) || (row=AW_MwvmHeldFind(ref))<0)return 0;
    return AW_MwvmHeld(row,NULL,&support,NULL) && !AW_ObjectDisabled(support);
}
static void scan(void){
    int i,k,row;uint32_t ref,support;float at[3];vec3_t local;edict_t *e;
    st.scans++;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(!is_actor(e) || !(ref=ref_of(e)) || (row=AW_MwvmHeldFind(ref))<0)continue;
        for(k=0;k<nfalls && !(falls[k].edict==i && falls[k].ref==ref);k++);
        if(k<nfalls)continue;
        if(nfalls==FALLS){st.full++;continue;}
        if(!AW_MwvmHeld(row,NULL,&support,at))continue;
        memset(&falls[nfalls],0,sizeof(fall_t));
        falls[nfalls].edict=i;falls[nfalls].ref=ref;falls[nfalls].support=support;
        if(AW_CombatSlotState(e,NULL)==2)falls[nfalls].state=LANDED;          /* a body: as it lies */
        else if(!AW_ObjectDisabled(support)){
            /* where the game data puts it: a ground bake of its frame or of the actor table would have moved it */
            falls[nfalls].state=HELD;
            if(AW_SourceToWorld(sv.name,at,local)){VectorCopy(local,e->v.origin);}
            e->v.flags=(float)((int)e->v.flags&~FL_ONGROUND);
            SV_LinkEdict(e,false);
        }else falls[nfalls].state=WAITING;           /* already gone (a load): it falls from where it stands */
        nfalls++;st.tracked++;
    }
}
static void play(edict_t *e,int key,float gain){
    const char *path=AW_CombatSoundPath(key);sfx_t *s;
    if(!path || !*path || !(s=S_PrecacheSound((char *)path)))return;
    S_StartSound(NUM_FOR_EDICT(e),4,s,e->v.origin,gain,1);       /* the body channel, on the actor */
}
static void landed(edict_t *e,fall_t *f,int water){
    aw_actor_t *a;float acrobatics=0,fatigue=1,fatigue_max=1,loss,health;int knockdown=0;
    f->state=LANDED;st.landed++;st.height=f->height;
    e->v.flags=(float)((int)e->v.flags|FL_ONGROUND);
    SV_LinkEdict(e,false);
    if(water){st.water++;return;}                     /* OpenMW: no fall damage landing in water */
    if(!(f->height>0) || AW_CombatSlotState(e,NULL)==2)return;
    if(!(a=AW_MwscriptActorOf(e,NULL))){st.no_record++;return;}
    if(a->flags&AWL_DEAD)return;
    acrobatics=(float)(a->skill_base[SKILL_ACROBATICS]+a->skill_mod[SKILL_ACROBATICS]);
    fatigue=a->dyn_cur[2];fatigue_max=a->dyn_base[2];
    loss=AW_MoveFallLoss(f->height,acrobatics,AW_EffectsMagnitude(f->ref,AW_EFFECT_JUMP,AW_EFFECT_NO_ARG),
                         fatigue,fatigue_max,&knockdown);
    st.loss=loss;
    if(!(loss>0))return;
    st.hurt++;
    if(AW_CombatSlotState(e,&health)==1)a->dyn_cur[0]=health;    /* a fight's health is the live one */
    a->dyn_cur[0]-=loss;health=a->dyn_cur[0];
    play(e,AW_SND_HEALTH,1);
    if(health<=0){
        a->dyn_cur[0]=0;
        /* dies as by a blow: laid down, on the change list, its body searchable (aw_combat.c) */
        if(!AW_CombatSpellHit(e,0,0))AW_CombatTestEngage(e,1);
        play(e,AW_SND_FALL,1);
        AW_ActorKill(a);st.killed++;
    }else AW_CombatSpellHit(e,health,0);
    (void)knockdown;     /* a knockdown outside a fight: not yet (the combat layer's states start in a fight) */
    AW_MwvmStateChanged();
    Con_DPrintf("Fall: %s fell %.0f units, lost %.1f health (%.1f left)\n",e->v.netname?pr_strings+e->v.netname:"an actor",
                f->height,loss,health>0?health:0);
}
static void step(edict_t *e,fall_t *f,float dt){
    float slow,t=dt,move,drop;vec3_t end;trace_t tr;int contents;
    slow=AW_MoveSlowFallFactor(AW_EffectsMagnitude(f->ref,AW_EFFECT_SLOWFALL,AW_EFFECT_NO_ARG));
    if(slow<1)st.slowed++;
    while(t>0 && f->state==FALLING){
        float s=t<AW_MOVE_PHYSICS_STEP?t:AW_MOVE_PHYSICS_STEP;
        t-=s;
        f->vz=AW_MoveFallStep(f->vz,s,AW_MOVE_GRAVITY,slow);
        move=f->vz*s*AW_MOVE_UNIT_SCALE;
        VectorCopy(e->v.origin,end);end[2]+=move;
        tr=SV_Move(e->v.origin,e->v.mins,e->v.maxs,end,MOVE_NOMONSTERS,e);
        drop=e->v.origin[2]-tr.endpos[2];
        if(!tr.allsolid)VectorCopy(tr.endpos,e->v.origin);
        /* mtphysics.cpp: the height grows with every drop and starts again while a Slowfall is on */
        if(slow<1)f->height=0;else if(drop>0)f->height+=drop/AW_MOVE_UNIT_SCALE;
        contents=SV_PointContents(e->v.origin);
        if(contents==CONTENTS_WATER || contents==CONTENTS_SLIME){landed(e,f,1);break;}
        if(tr.fraction<1 || tr.allsolid || f->height>FALL_MAX){landed(e,f,0);break;}
    }
    SV_LinkEdict(e,false);
}
/* something under the actor (the streamed ground collidable) within FALL_MAX */
static int ground_below(edict_t *e){
    vec3_t end;trace_t tr;
    VectorCopy(e->v.origin,end);end[2]-=FALL_MAX*AW_MOVE_UNIT_SCALE;
    tr=SV_Move(e->v.origin,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,e);
    return tr.fraction<1;
}
/* a HELD row within NEAR_HELD original units of the player (outdoors), or a room (no outdoor position: its few edicts
 * are looked at): only then the edicts are looked over */
#define NEAR_HELD 24576.0f
static int held_near(void){
    float at[3],row[3],dx,dy;int k,n=AW_MwvmHeldCount();
    if(!sv_player || !AW_WorldToSource(sv.name,sv_player->v.origin,at))return 1;
    for(k=0;k<n;k++){
        if(!AW_MwvmHeld(k,NULL,NULL,row))continue;
        dx=row[0]-at[0];dy=row[1]-at[1];
        if(dx*dx+dy*dy<NEAR_HELD*NEAR_HELD)return 1;
    }
    return 0;
}
void AW_FallTick(float dt){
    int i;
    if(!sv.active || !AW_MwvmHeldCount()){nfalls=0;return;}
    if(map_of!=(void *)sv.worldmodel){map_of=(void *)sv.worldmodel;nfalls=0;next_scan=0;}
    if(sv.time>=next_scan){next_scan=sv.time+0.5;if(held_near())scan();}
    if(!(dt>0))return;                 /* the world stands (a menu, a message box) */
    if(dt>0.25f)dt=0.25f;
    for(i=0;i<nfalls;){
        fall_t *f=&falls[i];edict_t *e=f->edict<sv.num_edicts?EDICT_NUM(f->edict):NULL;
        if(!e || e->free || ref_of(e)!=f->ref){falls[i]=falls[--nfalls];continue;}   /* released, freed */
        if(f->state==HELD && AW_ObjectDisabled(f->support)){f->state=WAITING;st.fell++;}
        if(f->state==WAITING && ground_below(e)){f->state=FALLING;f->vz=0;f->height=0;
            e->v.flags=(float)((int)e->v.flags&~FL_ONGROUND);}
        if(f->state==FALLING)step(e,f,dt);
        i++;
    }
}
void AW_FallStatus(void){
    int i;
    Con_Printf("held actors: %d rows in the file, %d tracked here; %lu fell, %lu landed (%lu in water), %lu hurt, %lu "
               "killed, %lu without an actor record, %lu slowed steps; last fall %.0f units, %.1f health\n",
               AW_MwvmHeldCount(),nfalls,st.fell,st.landed,st.water,st.hurt,st.killed,st.no_record,st.slowed,st.height,st.loss);
    for(i=0;i<nfalls;i++)
        Con_Printf("  ref %lu on %lu: %s\n",(unsigned long)falls[i].ref,(unsigned long)falls[i].support,
                   state_names[falls[i].state]);
}
void AW_FallInit(void){aw_fall_held=held;}
