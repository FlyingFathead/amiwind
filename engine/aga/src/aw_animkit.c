/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg animkit (aw_animkit, docs/ANIMKIT.md): the animation kit's debug
 * console. on/off switches the walk/run/swim selection by speed (off: movers
 * play their idle frames, the previous method); list shows the groups of the
 * actor under the crosshair and Morrowind's whole group table; play forces one
 * group on that actor until stop; speed scales every kit playback rate.
 * The animation stage (SKEL-ANIM-STAGE-52): play also takes any group of a
 * skeletal actor's shared table by name (AW_SkelGroup), groups lists them,
 * cycle plays every group one after another, stage lines a cast of skeletal
 * actors up in front of the player (a man, a woman, a beast, a guard with his
 * torch, an armed actor) for cycle all.
 * Not saved (the cvar aw_animkit is archived; the forced groups are not).
 */
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_animkit.h"
#include "aw_skel.h"
#include "aw_items.h"

static cvar_t animkit={"aw_animkit","1",true};
void AW_SkelCastSound(edict_t *e,const aw_skel_table_t *t,int group,int from,int to);    /* aw_halloween.c */
/* A forced actor: an engine group of its layout (kit >= 0), or a group of its shared table (table, group). While
 * forced its think is held (the resident idle would step the frame) and a staged actor stands where the stage put
 * it, with its carried items shown; stop gives everything back. */
typedef struct {
    edict_t *e;int kit;aw_anim_play_t play;
    const aw_skel_table_t *table;int group;float t;
    int staged;vec3_t home,home_angles;float home_nextthink;
    edict_t *items[AW_ITEMS_KINDS];
} forced_t;
static forced_t forced[AW_ANIMKIT_STAGE_MAX];
static int forced_count;
static struct {int on,index,played;double started;} cycle;
static double last;
static model_t *forced_world;

static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
static edict_t *target(void) {
    edict_t *p=player();
    return p?AW_NPCTargetReach(p,cl.viewangles,1024):NULL;
}
static void sync(void) {aw_anim_kit_enabled=animkit.value!=0;}

/* The shared animation table of an actor's model, or NULL (a baked model). */
static const aw_skel_table_t *table_of(edict_t *e) {
    int i=e?(int)e->v.modelindex:0;model_t *m;const aliashdr_t *h;
    if(i<=0 || i>=MAX_MODELS || !(m=sv.models[i]) || m->type!=mod_alias)return NULL;
    h=(const aliashdr_t *)Mod_Extradata(m);
    return h && h->aw_skel?(const aw_skel_table_t *)h->aw_skel_table:NULL;
}
static const char *table_name(const aw_skel_table_t *t) {
    if(t && t->prefix[0] && t->prefix[0]!='f')return "own animation";  /* progs/humanoid.awsk|d(|f): DANCER-OWN-ANIM-IGNORED-53 */
    if(t && t->prefix[0]=='f')return "female";        /* the view progs/humanoid.awsk|f */
    if(t && t==AW_SkelTableFor("progs/humanoid_kna.awsk"))return "beast";
    if(t && t==AW_SkelTableFor("progs/humanoid.awsk"))return "common";
    return t?"other":"baked";
}
static const char *name_of(edict_t *e) {return e && e->v.netname?pr_strings+e->v.netname:"?";}

static void release(forced_t *f) {
    edict_t *e=f->e;
    if(e && !e->free){
        if(f->staged){VectorCopy(f->home,e->v.origin);VectorCopy(f->home_angles,e->v.angles);SV_LinkEdict(e,false);}
        e->v.nextthink=f->home_nextthink>0?(float)sv.time+.1f:0;
    }
    AW_ItemsHide(f->items);
    memset(f,0,sizeof(*f));
}
static void release_all(void) {
    int i;
    for(i=0;i<forced_count;i++)release(&forced[i]);
    forced_count=0;cycle.on=0;
}
static forced_t *take(edict_t *e) {
    int i;forced_t *f;
    for(i=0;i<forced_count;i++)if(forced[i].e==e)return &forced[i];
    if(forced_count>=AW_ANIMKIT_STAGE_MAX)return NULL;
    forced_world=sv.worldmodel;
    f=&forced[forced_count++];memset(f,0,sizeof(*f));
    f->e=e;f->kit=-1;f->group=-1;f->home_nextthink=e->v.nextthink;
    e->v.nextthink=0;          /* the resident idle think would step the frame (engine/aga/qc/world.qc aw_npc_idle) */
    return f;
}
/* Starts a table group by name on a forced actor (its idle when its table has no such group: OpenMW falls back). */
static int start_group(forced_t *f,const char *name) {
    int g=f->table?AW_SkelGroup(f->table,name):-1;
    if(g<0 && f->table)g=AW_SkelGroup(f->table,"idle");
    f->kit=-1;f->group=g;f->t=0;
    return g;
}
static void group_at(const forced_t *f,aw_skel_group_t *out) {
    memset(out,0,sizeof(*out));
    if(f->table && f->group>=0 && f->group<f->table->groups)AW_SkelGroupAt(f->table,f->group,out);
}

static void list(edict_t *e) {
    const aw_anim_t *a=e?AW_AnimOf(e):NULL;int i,wired=0,unwired=0;const aw_skel_table_t *t=table_of(e);
    if(a)Con_Printf("Animation kit groups of the target (%s; %s table%s):\n",a->from_layout?"layout":"no layout: idle only",
                    table_name(t),t?": every group plays by name, dbg animkit groups":"");
    else Con_Printf("Animation kit: no NPC under the crosshair; Morrowind's group table:\n");
    for(i=0;a && i<AW_ANIM_GROUPS;i++)
        if(a->g[i].present)Con_Printf("  %-9s %2d frames%s\n",aw_anim_group_names[i],a->g[i].count,
                                      a->mover[0] && !AW_AnimMoving(e)?" (standing model)":"");
    for(i=0;i<aw_animkit_group_count;i++){
        int g=aw_animkit_groups[i].engine;
        if(g<0){unwired++;continue;}
        wired++;
        Con_Printf("  %-22s -> %s%s\n",aw_animkit_groups[i].name,aw_anim_group_names[g],
                   a && !a->g[g].present?" (not in this model)":"");
    }
    Con_Printf("Present in data, not wired to the game logic yet (%d; a skeletal actor plays them by name):",unwired);
    for(i=0;i<aw_animkit_group_count;i++)if(aw_animkit_groups[i].engine<0)Con_Printf(" %s",aw_animkit_groups[i].name);
    Con_Printf("\n%d groups wired, %d not wired.\n",wired,unwired);
}
static void groups(edict_t *e) {
    const aw_skel_table_t *t=table_of(e);aw_skel_group_t g;int i;
    if(!t){Con_Printf("Animation kit: %s.\n",e?"the target is not a skeletal actor (no shared table)":"no NPC under the crosshair");return;}
    Con_Printf("%s: %s table, %d groups, %d frames at %.0f a second:\n",name_of(e),table_name(t),t->groups,t->frames,t->rate);
    for(i=0;i<t->groups;i++){AW_SkelGroupAt(t,i,&g);Con_Printf(" %d %s %u-%u",i+1,g.name,g.first,g.last);}
    Con_Printf("\n");
}

/* The stage's cast: the nearest skeletal actor of each kind first (a guard with a carried light, a beast, a woman,
 * an armed actor, a common-skeleton actor without a weapon), then the nearest others; lined up in a row in front of
 * the player, facing the same way as the player turned about (they face local +Y: yaw + 90). */
#define STAGE_KINDS 5
static int kind_of(edict_t *e,const aw_skel_table_t *t) {
    int items=AW_ItemsKinds(e);const char *n=table_name(t);
    if(items&AW_ITEMS_LIGHT)return 0;
    if(!strcmp(n,"beast"))return 1;
    if(!strcmp(n,"female"))return 2;
    if(items&1)return 3;
    return 4;
}
static void stage(int n) {
    static const char *const kinds[STAGE_KINDS]={"guard with a carried light","beast","woman","armed","common, unarmed"};
    edict_t *p=player(),*pick[AW_ANIMKIT_STAGE_MAX],*e;float best[AW_ANIMKIT_STAGE_MAX],d;int i,k,count=0,used;
    vec3_t forward,right,up,spot,low,delta;trace_t tr;
    if(!p){Con_Printf("Animation stage: no game running.\n");return;}
    release_all();
    for(k=0;k<STAGE_KINDS+AW_ANIMKIT_STAGE_MAX && count<n;k++){
        edict_t *found=NULL;float near=1e30f;
        for(i=1;i<sv.num_edicts;i++){
            const aw_skel_table_t *t;int j,dup=0;
            e=EDICT_NUM(i);
            if(e->free || !e->v.modelindex || strcmp(pr_strings+e->v.classname,"aw_npc") || !(t=table_of(e)))continue;
            for(j=0;j<count;j++)if(pick[j]==e)dup=1;
            if(dup || (k<STAGE_KINDS && kind_of(e,t)!=k))continue;
            VectorSubtract(e->v.origin,p->v.origin,delta);d=DotProduct(delta,delta);
            if(d<near){near=d;found=e;}
        }
        if(found){pick[count]=found;best[count]=near;count++;}
        else if(k<STAGE_KINDS)Con_Printf("Animation stage: no %s skeletal actor on this map.\n",kinds[k]);
    }
    (void)best;
    if(!count){Con_Printf("Animation stage: no skeletal actors on this map (built with --npc-anim-type 1?).\n");return;}
    {vec3_t view;VectorCopy(cl.viewangles,view);view[0]=view[2]=0;AngleVectors(view,forward,right,up);}
    for(i=0,used=0;i<count;i++){
        forced_t *f;e=pick[i];
        if(!(f=take(e)))break;
        f->table=table_of(e);f->staged=1;
        VectorCopy(e->v.origin,f->home);VectorCopy(e->v.angles,f->home_angles);
        /* on the ground near the player's feet (a ledge or stairs: not the street far below), else at his feet */
        /* map units: an actor is about 33 tall (world.qc aw_npc_floor's box; the map scale is a quarter) */
        VectorMA(p->v.origin,80,forward,spot);VectorMA(spot,((float)i-(float)(count-1)*.5f)*16,right,spot);
        spot[2]=p->v.origin[2]+p->v.mins[2];
        VectorCopy(spot,low);spot[2]+=16;low[2]-=32;
        tr=SV_Move(spot,vec3_origin,vec3_origin,low,MOVE_NOMONSTERS,e);
        if(!tr.startsolid && !tr.allsolid && tr.fraction<1){VectorCopy(tr.endpos,e->v.origin);}
        else{spot[2]-=48;VectorCopy(spot,e->v.origin);}
        /* facing the player: a converted character faces its local +Y, Quake's yaw 0 is +X (world.qc aw_npc_idle) */
        e->v.angles[0]=e->v.angles[2]=0;e->v.angles[1]=anglemod(cl.viewangles[1]+90);
        SV_LinkEdict(e,false);
        AW_ItemsShow(e,f->items);
        start_group(f,"idle");
        k=AW_ItemsKinds(e);
        Con_Printf("Stage %d: %s (%s table%s%s%s)\n",i+1,name_of(e),table_name(f->table),k&1?", weapon":"",k&2?", shield":"",
                   k&AW_ITEMS_LIGHT?", carried light":"");
        used++;
    }
    Con_Printf("Animation stage: %d skeletal actors (dbg animkit cycle all; dbg guardtorch on for the torch; dbg animkit stop).\n",used);
}

static void begin_cycle(int all) {
    edict_t *e;const aw_skel_table_t *t;int i;
    if(!all || !forced_count){
        if(!(e=target()) || !(t=table_of(e))){Con_Printf("Animation kit: %s.\n",all?"no stage and no skeletal NPC under the crosshair (dbg animkit stage)":"no skeletal NPC under the crosshair");return;}
        if(!all){int staged=0;for(i=0;i<forced_count;i++)if(forced[i].e==e)staged=1;if(!staged)release_all();}
        {forced_t *f=take(e);if(!f)return;f->table=t;}
    }
    for(i=0;i<forced_count;i++){if(!forced[i].table)forced[i].table=table_of(forced[i].e);start_group(&forced[i],"idle");}
    cycle.on=1;cycle.index=-1;cycle.played=0;cycle.started=realtime;
    Con_Printf("Animation cycle: %d groups of the %s table on %d actor%s, every group once (dbg animkit stop).\n",
               forced[0].table?forced[0].table->groups:0,table_name(forced[0].table),forced_count,forced_count==1?"":"s");
}
/* The lead (the first forced actor) plays each group of its table once; the others play the same group by name
 * (their own table's frames) and loop it until the lead goes on. */
static void cycle_next(void) {
    aw_skel_group_t g;int i;forced_t *lead=&forced[0];
    if(!lead->table){cycle.on=0;return;}
    if(++cycle.index>=lead->table->groups){
        Con_Printf("Animation cycle done: %d groups in %.0f s.\n",cycle.played,(float)(realtime-cycle.started));
        cycle.on=0;
        for(i=0;i<forced_count;i++)start_group(&forced[i],"idle");
        return;
    }
    AW_SkelGroupAt(lead->table,cycle.index,&g);
    for(i=0;i<forced_count;i++){
        if(i==0){lead->group=cycle.index;lead->kit=-1;lead->t=0;}
        else start_group(&forced[i],g.name);
    }
    cycle.played++;
    /* the time into the cycle: a recording of it is cut and labelled by these lines */
    Con_Printf("%d/%d %s (%u frames) at %.1f s\n",cycle.index+1,lead->table->groups,g.name,g.last-g.first+1,
               (float)(realtime-cycle.started));
}

static void command(void) {
    const char *argv[4];int i,argc=Cmd_Argc();aw_animkit_cmd_t c;edict_t *e;forced_t *f;
    if(argc>4)argc=4;
    for(i=0;i<argc;i++)argv[i]=Cmd_Argv(i);
    if(!AW_AnimKitParse(argc,argv,&c)){
        Con_Printf("dbg animkit: %s\n",c.name);
        Con_Printf("dbg animkit [on/off / list / groups / play <group> / cycle [all] / stage [1..8] / stop / speed <0.1..4>]\n");
        return;
    }
    switch(c.kind){
    case AW_ANIMKIT_ON:case AW_ANIMKIT_OFF:
        Cvar_SetValue(animkit.name,c.kind==AW_ANIMKIT_ON);sync();
        Con_Printf("Animation kit %s.\n",aw_anim_kit_enabled?"on: walk, run and swim by speed":"off: movers play idle");
        return;
    case AW_ANIMKIT_LIST:list(target());return;
    case AW_ANIMKIT_GROUPS:groups(target());return;
    case AW_ANIMKIT_STOP:release_all();Con_Printf("Animation kit: no forced group.\n");return;
    case AW_ANIMKIT_SPEED:aw_anim_kit_speed=c.speed;Con_Printf("Animation kit playback speed x%.2f.\n",c.speed);return;
    case AW_ANIMKIT_STAGE:stage(c.count);return;
    case AW_ANIMKIT_CYCLE:begin_cycle(c.count);return;
    case AW_ANIMKIT_PLAY:{
        const aw_skel_table_t *t;
        if(!(e=target())){Con_Printf("Animation kit: no NPC under the crosshair.\n");return;}
        t=table_of(e);
        cycle.on=0;
        if(t && AW_SkelGroup(t,c.name)>=0){
            /* a skeletal actor: straight from its table, every group by its own name */
            if(!(f=take(e))){Con_Printf("Animation kit: %d actors forced already (dbg animkit stop).\n",AW_ANIMKIT_STAGE_MAX);return;}
            f->table=t;start_group(f,c.name);
            {aw_skel_group_t g;group_at(f,&g);
             Con_Printf("Animation kit: playing %s (table frames %u-%u) on %s (dbg animkit stop).\n",g.name,g.first,g.last,name_of(e));}
            return;
        }
        if(c.group<0){Con_Printf("Animation kit: %s.\n",t?"no such group in the target's table":
                                 AW_AnimKitFind(c.name)<0?"unknown group":"not wired yet (a baked actor plays only the wired groups)");return;}
        if(!AW_AnimOf(e)->g[c.group].present){Con_Printf("Animation kit: the target has no %s group.\n",aw_anim_group_names[c.group]);return;}
        if(!(f=take(e))){Con_Printf("Animation kit: %d actors forced already (dbg animkit stop).\n",AW_ANIMKIT_STAGE_MAX);return;}
        f->kit=c.group;memset(&f->play,0,sizeof(f->play));f->play.group=255;
        Con_Printf("Animation kit: playing %s on the NPC under the crosshair (dbg animkit stop).\n",aw_anim_group_names[c.group]);
        return;}
    default:
        Con_Printf("Animation kit %s, playback speed x%.2f, %d forced actor%s%s.\n",aw_anim_kit_enabled?"on":"off",aw_anim_kit_speed,
                   forced_count,forced_count==1?"":"s",cycle.on?", cycling":"");
    }
}

#if !AW_ANIMKIT
static void compiled_out(void) {Con_Printf("dbg animkit: this engine was built without the animation kit (AW_ANIMKIT=0).\n");}
void AW_AnimKitInit(void) {Cmd_AddCommand("aw_animkit_cmd",compiled_out);aw_anim_kit_enabled=0;AW_SkelReleaseInit();}
void AW_AnimKitTick(void) {}
#else
/* After the server frame: a forced group wins over every other driver of its actor's frame. */
void AW_AnimKitTick(void) {
    float dt;int i,done;
    sync();
    dt=(float)(realtime-last);last=realtime;
    /* a load or a stall stands still; a slow machine's long frames still play (SKEL-RUNTIME-COST-52: on the
     * slow-CPU preset, about 1.6 s a frame, the old 0.5 s cut left every forced group on its first frame) */
    if(dt<0 || dt>3.0f)dt=0;
    if(!forced_count)return;
    if(!sv.active || forced_world!=sv.worldmodel){
        if(forced_world!=sv.worldmodel){memset(forced,0,sizeof(forced));forced_count=0;cycle.on=0;}  /* a new map: its edicts are gone */
        forced_world=sv.worldmodel;
        if(!sv.active)return;
    }
    for(i=0;i<forced_count;i++){
        forced_t *f=&forced[i];edict_t *e=f->e;
        if(!e || e->free){if(i==0)cycle.on=0;continue;}
        if(f->kit>=0){
            e->v.frame=(float)AW_AnimAdvance(AW_AnimOf(e),&f->play,f->kit,dt,aw_anim_kit_speed,NULL);
        }else if(f->table && f->group>=0){
            aw_skel_group_t g;int was=(int)e->v.frame;group_at(f,&g);
            /* the cycle's lead plays its group once; every other forced group loops */
            e->v.frame=(float)AW_AnimKitSpanFrame(g.first,g.last,f->table->rate,&f->t,dt*aw_anim_kit_speed,!(cycle.on && i==0),&done);
            /* a cast plays its whoosh on its own release keys (aw_halloween.c) */
            AW_SkelCastSound(e,f->table,f->group,was,(int)e->v.frame);
            if(cycle.on && i==0 && done)cycle_next();
        }else if(cycle.on && i==0)cycle_next();
        if(f->staged)AW_ItemsUpdate(e,f->items);
    }
    if(cycle.on && forced[0].group<0 && forced[0].table)cycle_next();
}

void AW_AnimKitInit(void) {
    Cvar_RegisterVariable(&animkit);
    Cmd_AddCommand("aw_animkit_cmd",command);   /* not "aw_animkit": its cvar would shadow it (CONSOLE-COMMAND-SHADOWED-BY-CVAR-36) */
    sync();
    AW_SkelReleaseInit();   /* a room short of Fast RAM gets the tables and posed frames back first (aw_skel_release.c) */
}
#endif
