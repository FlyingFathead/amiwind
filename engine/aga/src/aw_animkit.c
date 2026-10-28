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
#include "aw_animpick.h"
#include "aw_combat.h"
#include "aw_weather.h"
#include "aw_hand_models.h"
#include "aw_format.h"

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
    /* a spell cast (AW_AnimKitCast): the spellcast group from its variant's start to stop frame, once, then back to
     * the group it had (prev_group, -1 none) or, when it was taken only for the cast, given back whole */
    int casting,cast_group,cast_to,prev_group,cast_only;float prev_t;
} forced_t;
static forced_t forced[AW_ANIMKIT_STAGE_MAX];
static int forced_count;
/* combat: the combat playground's cycle (AW_AnimKitCombatCycle): only the combat groups, over and over; on a baked
 * actor (no table) its layout's engine groups, each for its clip or at least KIT_SECONDS. */
static struct {int on,index,played,combat;double started;} cycle;
#define KIT_SECONDS 1.5f
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
    forced_count=0;cycle.on=0;cycle.combat=0;
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
/* The groups a fight plays (the original's group names; docs/COMBAT.md "Combat playground"): stance, movement,
 * the attack groups of every weapon class, the shield block, hits, knockdowns and deaths. A table view's own
 * groups ("f:", "d:") are left out: the lead plays the table's. */
static int combat_group(const char *name) {
    static const char *const exact[]={"idle","walkforward","runforward","handtohand","weapononehand","weapontwohand",
        "weapontwowide","bowandarrow","crossbow","throwweapon","shield","knockdown","knockout",0};
    static const char *const prefix[]={"hit","death",0};
    int i;
    if(strchr(name,':'))return 0;
    for(i=0;exact[i];i++)if(!Q_strcasecmp((char *)name,(char *)exact[i]))return 1;
    for(i=0;prefix[i];i++)if(!Q_strncasecmp((char *)name,(char *)prefix[i],strlen(prefix[i])))return 1;
    return 0;
}
static void kit_next(void) {
    forced_t *lead=&forced[0];const aw_anim_t *a=AW_AnimOf(lead->e);int tries;
    for(tries=0;tries<AW_ANIM_GROUPS;tries++){
        if(++cycle.index>=AW_ANIM_GROUPS){cycle.index=0;}
        if(a->g[cycle.index].present)break;
    }
    lead->kit=cycle.index;memset(&lead->play,0,sizeof(lead->play));lead->play.group=255;lead->t=0;
    cycle.played++;
    Con_Printf("%d %s (%d frames) at %.1f s\n",cycle.index+1,aw_anim_group_names[cycle.index],a->g[cycle.index].count,
               (float)(realtime-cycle.started));
}
static void cycle_next(void) {
    aw_skel_group_t g;int i;forced_t *lead=&forced[0];
    if(!lead->table){if(cycle.combat){kit_next();return;}cycle.on=0;return;}
    if(cycle.combat){
        /* the next combat group; past the last one the cycle starts again */
        for(i=0;i<lead->table->groups;i++){
            if(++cycle.index>=lead->table->groups)cycle.index=0;
            AW_SkelGroupAt(lead->table,cycle.index,&g);
            if(combat_group(g.name))break;
        }
        lead->group=cycle.index;lead->kit=-1;lead->t=0;cycle.played++;
        Con_Printf("%d/%d %s (%u frames) at %.1f s\n",cycle.index+1,lead->table->groups,g.name,g.last-g.first+1,
                   (float)(realtime-cycle.started));
        return;
    }
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

static void pick_command(void);
static void command(void) {
    const char *argv[4];int i,argc=Cmd_Argc();aw_animkit_cmd_t c;edict_t *e;forced_t *f;
    if(argc>4)argc=4;
    for(i=0;i<argc;i++)argv[i]=Cmd_Argv(i);
    if(argc>=2 && !strcmp(argv[1],"pick")){pick_command();return;}   /* every group by state (below) */
    if(!AW_AnimKitParse(argc,argv,&c)){
        Con_Printf("dbg animkit: %s\n",c.name);
        Con_Printf("dbg animkit [on/off / list / groups / play <group> / cycle [all] / stage [1..8] / stop / speed <0.1..4> / pick ...]\n");
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

/* ---- Every humanoid animation group hooked up (aw_animpick.h, ANIM-GROUPS-NOT-HOOKED-54) ----
 * The drivers (combat, the companion, the residents' idle think, the walk) set each actor's frame inside the kit's
 * engine groups. Just before the server sends the frames (SV_SendClientMessages), a skeletal actor's frame is moved
 * into the group OpenMW would play in its state (AW_AnimPick): one-shots and gaits keep the driver's progress
 * through its group (its timing, the attack's hit, the feet's speed), standing groups play on their own clock; equip,
 * unequip and a cast play over the source as their own one-shot. After the send the driver's frame comes back, so
 * no driver sees a changed frame. dbg animkit pick off: the previous method (the engine groups only). Cost: per drawn
 * skeletal actor a few compares a frame; a table lookup by name only when its state changes. */
static int pick_on=1;         /* dbg animkit pick on/off (not saved) */
#define PICKERS 48
#define TURN_DEGREES 30.f              /* yaw per second that counts as turning on the spot (AmiWind threshold) */
#define TURN_HOLD .5                   /* seconds a turn keeps playing after the yaw stops changing */
#define IDLE_CHANCE_MULT 75            /* fIdleChanceMultiplier 0.75 (the original's GMST) x 100 */
typedef struct {
    edict_t *e;double seen,last_time,idle_until,turn_until;
    vec3_t last_origin,vel;float last_yaw,yaw_rate;
    int fighting,weapon,knocked,turn;
    unsigned char sneak,has_chances,idle,roll,chances[8];
    int over_from,over_to;float over_t;     /* equip, unequip, cast: a one-shot over the source (-1 none) */
    aw_pick_state_t last;int picked,gi,from,to,lfrom,lto,loop,inner;float t;
    char group[AW_PICK_NAME];const char *rule;
    float saved;int applied;
} picker_t;
static picker_t pickers[PICKERS];
static model_t *pick_world;
static unsigned long pick_driven,pick_changes;

static picker_t *picker_of(edict_t *e,int create) {
    int i,old=-1;
    for(i=0;i<PICKERS;i++)if(pickers[i].e==e)return &pickers[i];
    if(!create)return NULL;
    for(i=0;i<PICKERS;i++){
        if(!pickers[i].e || pickers[i].e->free){old=i;break;}
        if(old<0 || pickers[i].seen<pickers[old].seen)old=i;
    }
    memset(&pickers[old],0,sizeof(pickers[old]));
    pickers[old].e=e;pickers[old].over_from=-1;pickers[old].gi=-1;
    VectorCopy(e->v.origin,pickers[old].last_origin);pickers[old].last_yaw=e->v.angles[1];
    return &pickers[old];
}
static int table_has(void *context,const char *name) {return AW_SkelGroup((const aw_skel_table_t *)context,name)>=0;}
/* A group's text key, else the same key of the group's later places (spellcast_2: the beast file's second spellcast,
 * tools/skeletal_actor.py), else -1. "start" / "stop" are the group's own ends. */
static int key_frame(const aw_skel_table_t *t,int g,const char *key) {
    aw_skel_group_t gg;char name[AW_SKEL_NAME+4];int k,i,n;
    AW_SkelGroupAt(t,g,&gg);
    if(!strcmp(key,"start"))return (int)gg.first;
    if(!strcmp(key,"stop"))return (int)gg.last;
    if((k=AW_SkelKeyFrame(t,g,key))>=0)return k;
    for(i=2;i<=4;i++){
        n=snprintf(name,sizeof(name),"%s_%d",gg.name,i);
        if(n<0 || n>=(int)sizeof(name) || (n=AW_SkelGroup(t,name))<0)break;
        if((k=AW_SkelKeyFrame(t,n,key))>=0)return k;
    }
    return -1;
}
/* the engine group the driver shows (a group the layout names whose frames hold FRAME), -1 none */
static int engine_group_of(const aw_anim_t *a,int frame) {
    static const unsigned char order[]={AW_ANIM_DEATH,AW_ANIM_KNOCK,AW_ANIM_HIT,AW_ANIM_ATTACK,AW_ANIM_BLOCK,AW_ANIM_DODGEL,
        AW_ANIM_DODGER,AW_ANIM_RUN,AW_ANIM_WALK,AW_ANIM_SWIM,AW_ANIM_SWIMIDLE,AW_ANIM_IDLE};
    int i;
    for(i=0;i<(int)sizeof(order);i++){
        const aw_anim_group_t *g=&a->g[order[i]];
        if(g->present && frame>=g->base && frame<g->base+g->count)return order[i];
    }
    return -1;
}
static int forced_now(edict_t *e) {int i;for(i=0;i<forced_count;i++)if(forced[i].e==e)return 1;return 0;}
/* the drawn weapon: the actor record's (OpenMW getActiveWeapon), a carried weapon of unknown type plays the long
 * blade's groups (getWeaponAnimation's fallback), nothing in the hand hand-to-hand */
static int weapon_of(edict_t *e) {
    int w=AW_MwscriptWeaponType(e);
    if(w>=0 && w<=AW_PW_LAST)return w;
    return AW_ItemsKinds(e)&1?1:AW_PW_HANDTOHAND;
}
static void over(picker_t *p,const aw_skel_table_t *t,aw_pick_state_t s) {
    aw_pick_t o;int g;
    if(!AW_AnimPick(&s,table_has,(void *)t,&o) || (g=AW_SkelGroup(t,o.group))<0)return;
    p->over_from=key_frame(t,g,o.start);p->over_to=key_frame(t,g,o.stop);p->over_t=0;
    if(p->over_from<0 || p->over_to<p->over_from)p->over_from=-1;
    else{memcpy(p->group,o.group,sizeof(p->group));p->rule=o.rule;}   /* both AW_PICK_NAME, NUL-terminated */
}
static void drive(picker_t *p,edict_t *e,const aw_skel_table_t *t,const aw_anim_t *a,int g,int storm) {
    aw_pick_state_t s;aw_pick_t o;const aw_fighter_t *f=AW_CombatFighter(e);
    int frame=(int)e->v.frame,fighting=f && !f->dead,out=frame;float dt=(float)(realtime-p->last_time),progress;
    const aw_anim_group_t *src=&a->g[g];
    if(p->last_time<=0 || dt<0 || dt>3)dt=0;
    if(dt>0){
        vec3_t d;float yaw=e->v.angles[1]-p->last_yaw;
        VectorSubtract(e->v.origin,p->last_origin,d);VectorScale(d,1.f/dt,p->vel);
        while(yaw>180)yaw-=360;
        while(yaw<-180)yaw+=360;
        p->yaw_rate=yaw/dt;
    }
    VectorCopy(e->v.origin,p->last_origin);p->last_yaw=e->v.angles[1];p->last_time=realtime;p->seen=realtime;
    memset(&s,0,sizeof(s));s.weapon=AW_PW_NONE;
    /* drawing and putting away (updateWeaponState: equip start .. equip stop, unequip ...) */
    if(fighting && !p->fighting){p->weapon=weapon_of(e);s.weapon=(signed char)p->weapon;s.event=AW_PE_EQUIP;over(p,t,s);}
    else if(!fighting && p->fighting && !(f && f->dead)){s.weapon=(signed char)p->weapon;s.event=AW_PE_UNEQUIP;over(p,t,s);}
    p->fighting=fighting;
    memset(&s,0,sizeof(s));s.weapon=(signed char)(fighting?p->weapon:AW_PW_NONE);
    s.swim=g==AW_ANIM_SWIM || g==AW_ANIM_SWIMIDLE;s.sneak=p->sneak;s.storm=(unsigned char)storm;
    switch(g){
    case AW_ANIM_IDLE:case AW_ANIM_SWIMIDLE:
        /* turning on the spot (Quake's yaw grows to the left), held a moment past the last turning frame (OpenMW holds
         * it 0.05 s; an actor here snaps its yaw in one think, so the hold is longer: TURN_HOLD) */
        if(p->yaw_rate>TURN_DEGREES || p->yaw_rate<-TURN_DEGREES){p->turn=p->yaw_rate>0?AW_PM_TURNLEFT:AW_PM_TURNRIGHT;p->turn_until=realtime+TURN_HOLD;}
        if(p->turn && realtime<p->turn_until)s.move=(unsigned char)p->turn;
        else if(!fighting && p->has_chances){
            if(realtime>=p->idle_until){
                unsigned char rolls[8];int i;
                for(i=0;i<8;i++)rolls[i]=(unsigned char)(rand()%101);
                p->idle=(unsigned char)AW_PickWanderIdle(p->chances,IDLE_CHANCE_MULT,rand()%101,rolls);
                p->idle_until=realtime+5+rand()%5;      /* the wander package's next choice (AmiWind pacing) */
            }
            s.idle=p->idle;
        }
        break;
    case AW_ANIM_WALK:case AW_ANIM_RUN:case AW_ANIM_SWIM:{
        /* the motion against the facing (a converted character faces its local +Y: yaw + 90) */
        float yaw=(e->v.angles[1]+90)*(float)M_PI/180,fx=Q_CosRad(yaw),fy=Q_SinRad(yaw);
        float fwd=p->vel[0]*fx+p->vel[1]*fy,side=p->vel[0]*fy-p->vel[1]*fx;
        s.run=g==AW_ANIM_RUN;
        if(side*side>fwd*fwd)s.move=side>0?AW_PM_RIGHT:AW_PM_LEFT;
        else s.move=fwd>=0?AW_PM_FORWARD:AW_PM_BACK;
        break;}
    case AW_ANIM_HIT:s.event=AW_PE_HIT;break;
    case AW_ANIM_KNOCK:s.event=f && f->knocked==2?AW_PE_KNOCKOUT:AW_PE_KNOCKDOWN;p->knocked=s.event==AW_PE_KNOCKOUT?2:1;break;
    case AW_ANIM_DEATH:s.event=AW_PE_DEATH;s.knocked=(unsigned char)p->knocked;break;
    case AW_ANIM_ATTACK:{int k=AW_CombatAttackType(e);s.event=AW_PE_ATTACK;s.attack=(unsigned char)(k>=0 && k<3?k:0);s.follow=AW_PF_LARGE;break;}
    case AW_ANIM_BLOCK:s.event=AW_PE_BLOCK;break;
    default:return;      /* the dodge: the AmiWind sidestep plays as it is */
    }
    if(g!=AW_ANIM_KNOCK && g!=AW_ANIM_DEATH)p->knocked=0;
    if(s.event!=p->last.event || !p->picked)p->roll=(unsigned char)(rand()&255);
    s.roll=p->roll;
    /* a hit, a fall or a death ends a draw or a cast at once */
    if(s.event==AW_PE_HIT || s.event==AW_PE_KNOCKDOWN || s.event==AW_PE_KNOCKOUT || s.event==AW_PE_DEATH)p->over_from=-1;
    if(p->over_from>=0){
        int done=0;
        out=AW_AnimKitSpanFrame((unsigned)p->over_from,(unsigned)p->over_to,t->rate,&p->over_t,dt*aw_anim_kit_speed,0,&done);
        if(done)p->over_from=-1;
        p->saved=e->v.frame;e->v.frame=(float)out;p->applied=1;pick_driven++;
        return;
    }
    if(!p->picked || memcmp(&s,&p->last,sizeof(s))){
        int gi=-1;
        p->last=s;p->picked=1;
        if(AW_AnimPick(&s,table_has,(void *)t,&o) && (gi=AW_SkelGroup(t,o.group))>=0){
            int from=key_frame(t,gi,o.start),to=key_frame(t,gi,o.stop);
            if(from<0 || to<from){aw_skel_group_t gg;AW_SkelGroupAt(t,gi,&gg);from=(int)gg.first;to=(int)gg.last;}
            if(gi!=p->gi || from!=p->from)p->t=0;
            p->from=from;p->to=to;p->loop=o.loop;
            p->lfrom=o.loop_start[0]?key_frame(t,gi,o.loop_start):-1;p->lto=o.loop_stop[0]?key_frame(t,gi,o.loop_stop):-1;
            if(p->lto<p->lfrom)p->lfrom=p->lto=-1;
            p->inner=0;memcpy(p->group,o.group,sizeof(p->group));p->rule=o.rule;pick_changes++;
        }
        p->gi=gi;
    }
    if(p->gi<0)return;                 /* nothing fits: the driver's frame stays (OpenMW keeps what plays) */
    progress=src->count>1?(float)(frame-src->base)/(float)(src->count-1):0;
    if(progress<0)progress=0;
    if(progress>1)progress=1;
    if(g==AW_ANIM_IDLE || g==AW_ANIM_SWIMIDLE ||
       (s.event==AW_PE_KNOCKOUT && p->lfrom>=0 && progress>=.5f)){
        /* standing (and a knockout held down): the group's own clock; an inner loop (idlestorm, knockout) once in */
        if(p->lfrom>=0 && p->inner)
            out=AW_AnimKitSpanFrame((unsigned)p->lfrom,(unsigned)p->lto,t->rate,&p->t,dt*aw_anim_kit_speed,1,NULL);
        else{
            out=AW_AnimKitSpanFrame((unsigned)p->from,(unsigned)(p->lfrom>=0?p->lto:p->to),t->rate,&p->t,dt*aw_anim_kit_speed,
                                    p->lfrom<0 && p->loop,NULL);
            if(p->lfrom>=0 && out>=p->lto){p->inner=1;p->t=0;}
        }
    }else out=p->from+(int)(progress*(float)(p->to-p->from)+.5f);   /* the driver's progress through its group */
    p->saved=e->v.frame;e->v.frame=(float)out;p->applied=1;pick_driven++;
}
void AW_AnimPickPreSend(void) {
    /* the storm pose is the arm layer of aw_items.c (ACTOR-STORM-POSE-51: idlestorm on the arm facing the storm, as
     * OpenMW plays it over the upper body), so the whole-body pick leaves it out here */
    int i,storm=0;
    if(pick_world!=sv.worldmodel){memset(pickers,0,sizeof(pickers));pick_world=sv.worldmodel;}
    if(!AW_ANIMKIT || !sv.active || !pick_on || !aw_anim_kit_enabled)return;
    for(i=1+svs.maxclients;i<sv.num_edicts;i++){
        edict_t *e=EDICT_NUM(i);const aw_skel_table_t *t;const aw_anim_t *a;picker_t *p;int g,mi;model_t *m;
        if(e->free || (mi=(int)e->v.modelindex)<=0 || mi>=MAX_MODELS)continue;
        if(strcmp(pr_strings+e->v.classname,"aw_npc") && !AW_CombatFighter(e))continue;   /* residents and fighters */
        /* only a model already in the cache: Mod_Extradata would load an evicted one from disk, every frame, for every
         * actor (a stall on a loaded scene); the renderer brings it back when it draws it */
        if(!(m=sv.models[mi]) || m->type!=mod_alias || !Cache_Check(&m->cache))continue;
        if(!(t=table_of(e)) || forced_now(e))continue;
        a=AW_AnimOf(e);
        if(!a->from_layout || (g=engine_group_of(a,(int)e->v.frame))<0)continue;   /* a scripted or own group plays */
        if(!(p=picker_of(e,1)))continue;
        drive(p,e,t,a,g,storm);
    }
}
void AW_AnimPickPostSend(void) {
    int i;
    for(i=0;i<PICKERS;i++){
        picker_t *p=&pickers[i];
        if(!p->applied)continue;
        p->applied=0;
        if(p->e && !p->e->free)p->e->v.frame=p->saved;
    }
}
void AW_AnimPickCast(edict_t *e,int range) {
    picker_t *p;const aw_skel_table_t *t=table_of(e);aw_pick_state_t s;
    if(!t || !(p=picker_of(e,1)))return;
    memset(&s,0,sizeof(s));s.weapon=AW_PW_SPELL;s.event=AW_PE_CAST;s.range=(unsigned char)(range>=0 && range<3?range:0);
    over(p,t,s);
}
void AW_AnimPickSneak(edict_t *e,int on) {picker_t *p=picker_of(e,1);if(p)p->sneak=(unsigned char)(on!=0);}
void AW_AnimPickIdleChances(edict_t *e,const unsigned char chances[8]) {
    picker_t *p=picker_of(e,1);int i,any=0;
    if(!p)return;
    for(i=0;i<8;i++){p->chances[i]=chances[i];if(chances[i])any=1;}
    p->has_chances=(unsigned char)any;p->idle_until=0;
}
int AW_AnimPickGroup(edict_t *e,char *out,int size) {
    picker_t *p=picker_of(e,0);
    if(!p || !p->group[0] || size<1)return 0;
    strncpy(out,p->group,(size_t)size-1);out[size-1]=0;
    return 1;
}
/* dbg animkit pick ... (the animation kit's command: no command record or setting of its own, the resident registry
 * budget unchanged). ARG(n): the word after "pick". */
#define ARG(n) Cmd_Argv((n)+1)
static void pick_command(void) {
    int argc=Cmd_Argc()-1;const char *w=argc>1?ARG(1):"";edict_t *e=target();picker_t *p;
    if(!strcmp(w,"on") || !strcmp(w,"off")){
        pick_on=!strcmp(w,"on");
        Con_Printf("Animation groups by state %s.\n",pick_on?"on: every group by OpenMW's rules":"off: the kit's engine groups only");
        return;
    }
    if(argc==1){
        Con_Printf("Animation groups by state %s: %lu frames placed, %lu group changes.\n",pick_on?"on":"off",pick_driven,pick_changes);
        if(e && (p=picker_of(e,0))!=NULL)
            Con_Printf("%s: %s (%s), stance %d, sneak %d, wander idle %d%s.\n",name_of(e),p->group[0]?p->group:"-",p->rule?p->rule:"-",
                       p->fighting?p->weapon:AW_PW_NONE,p->sneak,p->idle,p->has_chances?"":" (no chances given)");
        return;
    }
    if(!e || !table_of(e)){Con_Printf("dbg animkit pick: no skeletal NPC under the crosshair.\n");return;}
    if(!strcmp(w,"cast") && argc==3){
        const char *r=ARG(2);int range=!strcmp(r,"touch")?AW_PR_TOUCH:!strcmp(r,"target")?AW_PR_TARGET:AW_PR_SELF;
        AW_AnimPickCast(e,range);Con_Printf("%s casts (%s).\n",name_of(e),r);return;
    }
    if(!strcmp(w,"sneak") && argc==3){AW_AnimPickSneak(e,!strcmp(ARG(2),"on"));Con_Printf("%s sneaks: %s.\n",name_of(e),ARG(2));return;}
    if(!strcmp(w,"idle") && argc==10){
        unsigned char c[8];int i;
        for(i=0;i<8;i++){int v=Q_atoi(ARG(2+i));c[i]=(unsigned char)(v<0?0:v>100?100:v);}
        AW_AnimPickIdleChances(e,c);Con_Printf("%s: wander idle chances set.\n",name_of(e));return;
    }
    Con_Printf("dbg animkit pick [on/off / cast self/touch/target / sneak on/off / idle C2 .. C9]\n");
}
#undef ARG
void AW_AnimPickInit(void) {pick_on=1;}

/* ---- the combat playground (aw_arena.c animation mode; aw_animkit.h) ---- */
int AW_AnimKitSkeletal(int modelindex) {
    edict_t probe;memset(&probe,0,sizeof(probe));probe.v.modelindex=(float)modelindex;
    return table_of(&probe)!=NULL;
}
int AW_AnimKitCombatCycle(edict_t *e) {
    forced_t *f;const aw_anim_t *a;int g,any=0;
    release_all();
    if(!e || e->free || !(f=take(e)))return 0;
    f->table=table_of(e);
    if(!f->table){
        a=AW_AnimOf(e);
        for(g=0;g<AW_ANIM_GROUPS;g++)if(a->g[g].present)any=1;
        if(!any){release_all();return 0;}
    }
    cycle.on=1;cycle.combat=1;cycle.index=-1;cycle.played=0;cycle.started=realtime;
    cycle_next();
    Con_Printf("Combat animation cycle on %s: %s, every combat group in turn (dbg animkit stop).\n",name_of(e),
               f->table?table_name(f->table):"baked layout");
    return f->table?1:2;
}
void AW_AnimKitStop(void) {release_all();cycle.combat=0;}
/* "weapononehand: slash" for the lead of the combat cycle: its group and, inside an attack group, the phase the
 * frame is in (the latest of the phase start keys at or before it, AW_SkelKeyFrame). */
int AW_AnimKitLabel(char *out,int size) {
    static const char *const phases[]={"equip","chop","slash","thrust","shoot","block","unequip",0};
    forced_t *lead=&forced[0];aw_skel_group_t g;char key[32];int i,best=-1,best_at=-1,at,frame;
    if(!cycle.on || !cycle.combat || !forced_count || size<8 || !lead->e || lead->e->free)return 0;
    if(!lead->table){
        if(lead->kit<0)return 0;
        Q_snprintf(out,size,"%s (baked)",aw_anim_group_names[lead->kit]);return 1;
    }
    if(lead->group<0)return 0;
    group_at(lead,&g);frame=(int)lead->e->v.frame;
    for(i=0;phases[i];i++){
        Q_snprintf(key,sizeof(key),"%s start",phases[i]);
        at=AW_SkelKeyFrame(lead->table,lead->group,key);
        if(at>=0 && at<=frame && at>=best_at){best=i;best_at=at;}
    }
    if(best>=0)Q_snprintf(out,size,"%s: %s",g.name,phases[best]);
    else Q_snprintf(out,size,"%s",g.name);
    return 1;
}

#if !AW_ANIMKIT
static void compiled_out(void) {Con_Printf("dbg animkit: this engine was built without the animation kit (AW_ANIMKIT=0).\n");}
void AW_AnimKitInit(void) {Cmd_AddCommand("aw_animkit_cmd",compiled_out);aw_anim_kit_enabled=0;AW_SkelReleaseInit();AW_AnimPickInit();}
void AW_AnimKitTick(void) {AW_HandsTick();}
float AW_AnimKitCast(edict_t *e,const char *variant) {(void)e;(void)variant;return -1;}
#else
/* aw_magic.c: E plays its table's spellcast group for VARIANT ("self", "touch", "target"), from the variant's start
 * key to its stop key, once (rule from OpenMW mwmechanics/character.cpp: the spell is cast on the group's "<variant>
 * release" key; nothing copied). Returns the seconds from the start key to the release key, or -1 when E has no
 * table, no spellcast group or no such keys (the caller then times the cast itself). */
float AW_AnimKitCast(edict_t *e,const char *variant) {
    const aw_skel_table_t *t=table_of(e);int g,start,rel,stop,i;forced_t *f=NULL;char key[40];
    if(!aw_anim_kit_enabled || !t || !(t->rate>0) || !variant || strlen(variant)>16)return -1;
    if((g=AW_SkelGroup(t,"spellcast"))<0)return -1;
    sprintf(key,"%s start",variant);start=AW_SkelKeyFrame(t,g,key);
    sprintf(key,"%s release",variant);rel=AW_SkelKeyFrame(t,g,key);
    sprintf(key,"%s stop",variant);stop=AW_SkelKeyFrame(t,g,key);
    if(start<0 || rel<start || stop<rel)return -1;
    for(i=0;i<forced_count;i++)if(forced[i].e==e)f=&forced[i];
    if(!f){
        if(!(f=take(e)))return -1;
        f->table=t;f->cast_only=1;f->prev_group=-1;
    }else if(!f->casting){f->prev_group=f->group;f->prev_t=f->t;}
    f->casting=1;f->cast_group=g;f->cast_to=stop;
    e->v.frame=(float)start;
    return (rel-start)/t->rate;
}
#endif
#if AW_ANIMKIT
/* After the server frame: a forced group wins over every other driver of its actor's frame. */
void AW_AnimKitTick(void) {
    float dt;int i,done;
    AW_HandsTick();       /* the first-person hands (aw_hand_models.c; was world.qc aw_hands_update) */
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
            if(cycle.on && cycle.combat && i==0){
                const aw_anim_group_t *k=&AW_AnimOf(e)->g[f->kit];float clip=k->count*k->step;
                f->t+=dt*aw_anim_kit_speed;
                if(f->t>=(clip>KIT_SECONDS?clip:KIT_SECONDS))cycle_next();
            }
        }else if(f->casting){
            /* the cast: start to stop of the variant, once (aw_magic.c plays the effect and its sounds) */
            float to=(float)f->cast_to;
            e->v.frame+=dt*aw_anim_kit_speed*f->table->rate;
            if(e->v.frame>=to){
                f->casting=0;
                if(f->cast_only){release(f);memmove(f,f+1,(size_t)(forced_count-1-i)*sizeof(*f));forced_count--;i--;continue;}
                f->group=f->prev_group;f->t=f->prev_t;
            }
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
    AW_AnimPickInit();
    Cvar_RegisterVariable(&animkit);
    Cmd_AddCommand("aw_animkit_cmd",command);   /* not "aw_animkit": its cvar would shadow it (CONSOLE-COMMAND-SHADOWED-BY-CVAR-36) */
    sync();
    AW_SkelReleaseInit();   /* a room short of Fast RAM gets the tables and posed frames back first (aw_skel_release.c) */
}
#endif
