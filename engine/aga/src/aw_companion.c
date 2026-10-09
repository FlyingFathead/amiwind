/* SPDX-License-Identifier: GPL-2.0-or-later
 * Debug companion: one NPC that follows the player (pathfinding prototype;
 * docs/DEBUG_OVERLAYS.md, "NPC companion test"). dbg companion test spawns a
 * copy of a resident actor beside the player; dbg companion pick makes the
 * NPC under the crosshair follow instead. Not saved: the spawned companion
 * is no aw_npc and the Quake save writes it as a free slot; a picked NPC is
 * saved at its home spot and returns there when released.
 *
 * Quake first: the follower is an edict with a think on Quake's cadence
 * (nextthink 0.1 s, run from SV_Physics after the entities). The think is C,
 * not QuakeC: our progs are data-built and minimal, and the C side owns the
 * actor step (AW_ActorStep: the player's own SV_WalkMove stairs and slides;
 * the stock monster step refuses ground the player walks). The decisions
 * are aw_npcpath.c (integer, budgeted). Between thinks it costs one pointer
 * test per frame. The follower is SOLID_NOT and the player is passed through
 * for the follower's own sweeps, so neither blocks the other.
 *
 * Load doors: AW_CompanionSceneSpawn is the hand-over point after a scene
 * change. Today the test companion respawns beside the player there; a
 * picked NPC stays home. Carrying a follower through a door needs only the
 * small record below (model, kind) and the arrival spot.
 */
#include "quakedef.h"
#include "aw_npcpath.h"

#define DISTANCE_MIN 48         /* dbg companion distance: follow distance clamp */
#define DISTANCE_MAX 512
#define FAR_TELEPORT 640        /* hopelessly far: teleport back (at least 3 x the distance) */
#define STUCK_THINKS 60         /* net movement under 48 units for this long: teleport */
#define PICK_REACH 384
#define STEP_UP 8.5f
#define HEAVY_STEP 24           /* traces: a normal step costs 3-16, an unstick search far more */

extern unsigned long aw_sv_move_calls;
static char companion_class[]="aw_companion",companion_name[]="Test companion";

/* All companion state: one follower at a time. */
static struct {
    edict_t *e;                 /* follower, NULL = none */
    unsigned char kind;         /* 0 none, 1 spawned test companion, 2 picked NPC */
    unsigned char wanted;       /* respawn the test companion after a scene load */
    unsigned char walking, walk_frames, idle_frames, near;
    unsigned char teleport;     /* teleport search: next candidate + 1 (0 = none) */
    unsigned char teleport_why; /* 1 far, 2 stuck */
    unsigned char heavy;        /* steps in a row that ran the unstick search */
    int anchor[2];              /* net-movement anchor */
    unsigned short stuck;       /* thinks since the anchor */
    float next_think, last_think;
    aw_path_t path;
    /* picked NPC: its own state, restored on release */
    vec3_t home, home_angles;
    float home_solid, home_nextthink, home_frame, home_flags;
    func_t home_think;
} c;

static struct {
    unsigned long thinks, teleports_far, teleports_stuck, respawns, move_traces, picks, slow_thinks, heavy_steps;
    double started, think_seconds, think_max;
} stats;

static struct {unsigned char on, click, red, drawn; int frame; edict_t *target;} pick;
static cvar_t think_interval={"aw_companion_think","0.1"};
/* How close the follower keeps (feet to feet, game units). 96: out of the
 * player's way in a doorway, still in view. Not saved. */
static cvar_t follow_distance={"aw_companion_distance","96"};
/* Match the player's speed (aw_npcpath.c AW_PathSpeed); 0: fixed walk/run. */
static cvar_t mimic_speed={"aw_companion_mimic","1"};
int AW_CompanionDistance(void) {
    int d=(int)follow_distance.value;
    return d<DISTANCE_MIN?DISTANCE_MIN:d>DISTANCE_MAX?DISTANCE_MAX:d;
}
int AW_CompanionMimic(void) {return mimic_speed.value!=0;}

static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
static int feet_z(edict_t *e) {return (int)floor(e->v.origin[2]+e->v.mins[2]);}
/* The follower's origin is at its feet (mins z 0, as aw_npc). */
static void feet(edict_t *e,int out[3]) {
    out[0]=(int)floor(e->v.origin[0]);out[1]=(int)floor(e->v.origin[1]);out[2]=feet_z(e);
}
static float field(edict_t *e,char *name,float fallback) {
    eval_t *v=GetEdictFieldValue(e,name);return v && v->_float>0?v->_float:fallback;
}
static void set_field(edict_t *e,char *name,float value) {
    eval_t *v=GetEdictFieldValue(e,name);if(v)v->_float=value;
}
int AW_CompanionEdict(edict_t *e) {return e && c.e==e;}
static int alive(void) {
    if(!c.e)return 0;
    if(c.e->free || (c.kind==1 && c.e->v.classname!=companion_class-pr_strings)){c.e=NULL;c.kind=0;return 0;}
    return 1;
}

/* ---- traces for aw_npcpath.c, with the player passed through ---- */
static float player_solid;
static void pass_player(int on) {
    edict_t *p=player();if(!p)return;
    if(on){player_solid=p->v.solid;p->v.solid=SOLID_NOT;}else p->v.solid=player_solid;
}
static int sweep(void *context,int dx,int dy) {
    edict_t *e=context;vec3_t start,end;trace_t tr;
    VectorCopy(e->v.origin,start);start[2]+=STEP_UP;
    VectorCopy(start,end);end[0]+=dx;end[1]+=dy;
    tr=SV_Move(start,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);
    return !tr.startsolid && !tr.allsolid && tr.fraction==1;
}
static int standing(edict_t *e,float x,float y,float z,int *floor_z) {
    vec3_t start,end;trace_t tr;
    start[0]=end[0]=x;start[1]=end[1]=y;start[2]=z+AW_PATH_STEP;end[2]=z-AW_PATH_STEP;
    tr=SV_Move(start,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<AW_WALKABLE_Z)return 0;
    if(floor_z)*floor_z=(int)floor(tr.endpos[2]);
    return 1;
}
static int cell(void *context,int x,int y,int z,int *floor_z) {return standing(context,x,y,z,floor_z);}

/* ---- placement next to the player ---- */
/* Candidate k: a ring of 8 spots 32 units out, starting behind the player.
 * Standing room and a clear line from the player's eye. Two traces. */
static int candidate(edict_t *e,edict_t *p,int k,vec3_t out) {
    /* behind the player: its yaw as a heading index, plus half a turn (no trig) */
    int yaw=(int)floor(anglemod(p->v.angles[1])*AW_PATH_FAN/360.0f+.5f);
    int h=(yaw+AW_PATH_FAN/2+((k&1)?(k+1)/2:-(k/2))*4)&(AW_PATH_FAN-1);
    vec3_t eye,spot;int z;trace_t tr;
    spot[0]=p->v.origin[0]+aw_path_fan[h][0]/2;spot[1]=p->v.origin[1]+aw_path_fan[h][1]/2;spot[2]=feet_z(p);
    if(!standing(e,spot[0],spot[1],spot[2],&z))return 0;
    spot[2]=z;VectorAdd(p->v.origin,p->v.view_ofs,eye);
    {vec3_t mid;VectorCopy(spot,mid);mid[2]+=16;tr=SV_Move(eye,vec3_origin,vec3_origin,mid,MOVE_NOMONSTERS,e);}
    if(tr.fraction<1)return 0;
    VectorCopy(spot,out);return 1;
}
static void put(edict_t *e,vec3_t spot) {
    VectorCopy(spot,e->v.origin);VectorCopy(spot,e->v.oldorigin);VectorCopy(vec3_origin,e->v.velocity);
    e->v.flags=(int)e->v.flags|FL_ONGROUND;SV_LinkEdict(e,false);
    AW_PathReset(&c.path,(int)floor(spot[0]),(int)floor(spot[1]));
    c.anchor[0]=(int)floor(spot[0]);c.anchor[1]=(int)floor(spot[1]);c.stuck=0;
}
static void put_at_player(edict_t *e,edict_t *p) {
    vec3_t spot;VectorCopy(p->v.origin,spot);spot[2]=feet_z(p);put(e,spot);
}

/* ---- the think ---- */
static void face(edict_t *e,int heading) {e->v.angles[1]=heading*360.0f/AW_PATH_FAN-90;e->v.angles[0]=e->v.angles[2]=0;}
static void animate(edict_t *e,int walking) {
    float t=(float)sv.time;
    if(walking && c.walk_frames)e->v.frame=13+((int)(t/field(e,"aw_walk_step",.125f)))%8;
    else if(c.idle_frames)e->v.frame=((int)(t/field(e,"aw_idle_step",.15f)))%8;
    else e->v.frame=0;
}
static void teleport_step(edict_t *e,edict_t *p) {
    vec3_t spot,from;int found=0;
    VectorCopy(e->v.origin,from);
    if(c.teleport<=8){found=candidate(e,p,c.teleport-1,spot);c.teleport++;}
    if(!found && c.teleport<=8)return;      /* next candidate next think (2 traces each) */
    if(found)put(e,spot);else put_at_player(e,p);
    if(c.teleport_why==1)stats.teleports_far++;else stats.teleports_stuck++;
    Con_Printf("Companion teleported (%s): %ld %ld %ld -> %ld %ld %ld\n",c.teleport_why==1?"too far":"stuck",
        (long)from[0],(long)from[1],(long)from[2],(long)e->v.origin[0],(long)e->v.origin[1],(long)e->v.origin[2]);
    c.teleport=0;c.near=0;c.heavy=0;
}
static void think(edict_t *e,edict_t *p,float dt) {
    int self[3],goal[3],dx,dy,dz,gap,step,heading,moved=0,speed,near=AW_CompanionDistance(),far;
    unsigned long before;aw_path_io_t io;
    far=3*near>FAR_TELEPORT?3*near:FAR_TELEPORT;
    feet(e,self);feet(p,goal);
    dx=goal[0]-self[0];dy=goal[1]-self[1];dz=goal[2]-self[2];
    gap=AW_PathLength(dx,dy);
    if(c.teleport){teleport_step(e,p);return;}
    if(gap>far || dz>448 || dz<-448 || c.stuck>=STUCK_THINKS){
        c.teleport=1;c.teleport_why=c.stuck>=STUCK_THINKS?2:1;teleport_step(e,p);return;
    }
    /* Early out: close enough (resume a quarter beyond), no traces at all. */
    if(gap<=(c.near?near+near/4:near) && dz<24 && dz>-24){
        if(!c.near){AW_PathIdle(&c.path,self[0],self[1]);c.near=1;}
        c.anchor[0]=self[0];c.anchor[1]=self[1];c.stuck=0;animate(e,0);return;
    }
    c.near=0;
    /* The player's horizontal speed, read once per think (no square root). */
    speed=AW_PathSpeed(AW_CompanionMimic(),AW_PathLength((int)p->v.velocity[0],(int)p->v.velocity[1]),gap,near);
    step=(int)(speed*dt);
    if(step>gap-near)step=gap-near;     /* stop at the distance: no overshoot */
    if(step<1)step=1;
    io.context=e;io.sweep=sweep;io.cell=cell;
    pass_player(1);
    if(AW_PathThink(&c.path,&io,self,goal,step,&heading)){
        vec3_t move;
        move[0]=aw_path_fan[heading][0]*step/(float)AW_PATH_FAN_RADIUS;
        move[1]=aw_path_fan[heading][1]*step/(float)AW_PATH_FAN_RADIUS;move[2]=0;
        if(c.heavy>=2)c.stuck=STUCK_THINKS;   /* in solid: place it beside the player next think */
        else {
            before=aw_sv_move_calls;
            moved=AW_ActorStep(e,move,host_frametime>0?host_frametime:dt);
            before=aw_sv_move_calls-before;stats.move_traces+=before;
            /* The player's walk runs Quake's unstick search (SV_CheckStuck, up to
             * 164 position tests) when the box starts in solid. Never pay that
             * every think: two such steps in a row and the follower is placed. */
            if(before>HEAVY_STEP){c.heavy++;stats.heavy_steps++;}else c.heavy=0;
            face(e,heading);
        }
    }
    pass_player(0);
    animate(e,moved);
    feet(e,self);
    if(abs(self[0]-c.anchor[0])+abs(self[1]-c.anchor[1])>=48){c.anchor[0]=self[0];c.anchor[1]=self[1];c.stuck=0;}
    else if(c.stuck<65535)c.stuck++;
}

/* SV_Physics, after the entities: the follower's think on Quake's cadence. */
void AW_CompanionPhysics(void) {
    edict_t *p;double t0;float dt,interval;
    if(!c.e)return;
    if(!alive() || !(p=player()))return;
    if(sv.time<c.next_think)return;
    interval=think_interval.value;if(interval<.05f)interval=.05f;if(interval>.2f)interval=.2f;
    dt=(float)(sv.time-c.last_think);if(dt>.3f)dt=.3f;if(dt<0)dt=interval;
    c.last_think=(float)sv.time;c.next_think=(float)sv.time+interval;
    {
        unsigned long moves=aw_sv_move_calls,search=aw_path_stats.traces;int mode=c.path.mode,tele=c.teleport;
        t0=Sys_FloatTime();
        think(c.e,p,dt);
        t0=Sys_FloatTime()-t0;stats.thinks++;stats.think_seconds+=t0;
        /* A slow think says what it did: the search is capped, the step is the player's walk. */
        if(t0>.02){
            stats.slow_thinks++;
            if(t0>stats.think_max)Con_Printf("Companion think %.1f ms: %s, %lu traces (%lu search)\n",t0*1000,
                tele?"teleport":c.near?"standing":mode==AW_PATH_PING?"ping":mode==AW_PATH_FLOOD?"flood":"walk",
                aw_sv_move_calls-moves,aw_path_stats.traces-search);
        }
        if(t0>stats.think_max)stats.think_max=t0;
    }
}

/* ---- spawn, pick, release ---- */
static void reset_stats(void) {
    memset(&stats,0,sizeof(stats));memset(&aw_path_stats,0,sizeof(aw_path_stats));stats.started=sv.time;
}
static void frames_of(edict_t *e) {
    int i=(int)e->v.modelindex,n=i>0 && i<MAX_MODELS && sv.models[i]?sv.models[i]->numframes:0;
    c.walk_frames=n>=21;c.idle_frames=n>=8;
}
static void follow(edict_t *e) {
    c.e=e;c.near=0;c.teleport=0;c.heavy=0;c.next_think=c.last_think=(float)sv.time;
    frames_of(e);AW_PathReset(&c.path,(int)floor(e->v.origin[0]),(int)floor(e->v.origin[1]));
    c.anchor[0]=(int)floor(e->v.origin[0]);c.anchor[1]=(int)floor(e->v.origin[1]);c.stuck=0;
}
/* A resident actor to copy: the nearest with walk frames, else the nearest. */
static edict_t *model_source(edict_t *p) {
    edict_t *e,*best=NULL;int i,walk,best_walk=0;float d,best_d=1e30f;vec3_t delta;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || !e->v.modelindex || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        walk=(int)e->v.modelindex<MAX_MODELS && sv.models[(int)e->v.modelindex] && sv.models[(int)e->v.modelindex]->numframes>=21;
        VectorSubtract(e->v.origin,p->v.origin,delta);d=DotProduct(delta,delta);
        if(walk>best_walk || (walk==best_walk && d<best_d)){best=e;best_d=d;best_walk=walk;}
    }
    return best;
}
/* A copy of a resident actor: its model, frames and its box (set by the
 * QuakeC setsize), so the scene needs nothing precached for it. */
static int spawn_test(edict_t *p) {
    edict_t *e,*src=model_source(p);vec3_t spot;int k;
    if(!src){Con_Printf("Test companion: no resident actor in this scene to copy.\n");c.wanted=0;return 0;}
    e=ED_Alloc();memcpy(&e->v,&src->v,progs->entityfields*4);
    e->v.classname=companion_class-pr_strings;e->v.netname=companion_name-pr_strings;
    e->v.solid=SOLID_NOT;e->v.movetype=MOVETYPE_NONE;e->v.think=e->v.touch=0;e->v.nextthink=0;
    set_field(e,"aw_ref",0);set_field(e,"aw_intro_role",0);set_field(e,"aw_hello_distance",0);set_field(e,"aw_moving",0);
    e->v.angles[1]=p->v.angles[1];c.kind=1;
    for(k=0;k<8 && !candidate(e,p,k,spot);k++);
    follow(e);
    if(k<8)put(e,spot);else put_at_player(e,p);
    Con_Printf("Test companion: a copy of %s, %s.\n",pr_strings+src->v.netname,
        c.walk_frames?"walk frames":"no walk frames (idle pose)");
    return 1;
}
static void release(int quiet) {
    edict_t *e=c.e;
    if(!alive()){c.kind=0;return;}
    if(c.kind==1){ED_Free(e);if(!quiet)Con_Printf("Test companion removed.\n");}
    else if(c.kind==2){
        VectorCopy(c.home,e->v.origin);VectorCopy(c.home,e->v.oldorigin);VectorCopy(c.home_angles,e->v.angles);
        e->v.solid=c.home_solid;e->v.think=c.home_think;e->v.nextthink=c.home_nextthink>0?(float)sv.time+.1f:0;
        e->v.frame=c.home_frame;e->v.flags=c.home_flags;set_field(e,"aw_moving",0);SV_LinkEdict(e,false);
        if(!quiet)Con_Printf("%s returns home.\n",pr_strings+e->v.netname);
    }
    c.e=NULL;c.kind=0;
}
static void pick_npc(edict_t *e) {
    if(c.e==e)return;
    release(1);c.wanted=0;
    VectorCopy(e->v.origin,c.home);VectorCopy(e->v.angles,c.home_angles);
    c.home_solid=e->v.solid;c.home_think=e->v.think;c.home_nextthink=e->v.nextthink;
    c.home_frame=e->v.frame;c.home_flags=e->v.flags;
    e->v.solid=SOLID_NOT;e->v.nextthink=0;SV_LinkEdict(e,false);   /* its QuakeC idle stops */
    c.kind=2;follow(e);reset_stats();stats.picks++;
    Con_Printf("Companion: %s follows you (dbg companion off sends it home).\n",pr_strings+e->v.netname);
}

/* Saves: a picked NPC is written at its home spot. */
int AW_CompanionHome(edict_t *e,vec3_t origin,vec3_t angles) {
    if(!e || c.kind!=2 || c.e!=e || !alive())return 0;
    VectorCopy(c.home,origin);VectorCopy(c.home_angles,angles);return 1;
}
/* Quake's own save (host_cmd.c): swap the picked NPC's home state in while
 * the edicts are written; the spawned companion is written as a free slot. */
void AW_CompanionSaveSwap(int begin) {
    static vec3_t origin,angles;static float solid,nextthink;static func_t think_function;edict_t *e=c.e;
    if(c.kind!=2 || !alive())return;
    if(begin){
        VectorCopy(e->v.origin,origin);VectorCopy(e->v.angles,angles);solid=e->v.solid;nextthink=e->v.nextthink;think_function=e->v.think;
        VectorCopy(c.home,e->v.origin);VectorCopy(c.home_angles,e->v.angles);e->v.solid=c.home_solid;
        e->v.think=c.home_think;e->v.nextthink=c.home_nextthink;
    }else{
        VectorCopy(origin,e->v.origin);VectorCopy(angles,e->v.angles);e->v.solid=solid;e->v.nextthink=nextthink;e->v.think=think_function;
    }
}
int AW_CompanionSkipSave(edict_t *e) {return e && c.kind==1 && c.e==e && alive();}

/* aw_scene.c, after a scene spawned: the old edicts are gone. */
void AW_CompanionSceneSpawn(edict_t *p) {
    int was=c.kind;
    c.e=NULL;c.kind=0;pick.on=0;pick.target=NULL;
    if(was==2)Con_Printf("The picked companion stayed in the previous scene.\n");
    if(c.wanted && p){spawn_test(p);stats.respawns++;Con_Printf("Test companion rejoined you in %s.\n",sv.name);}
}

/* ---- dbg pickcompanion: red crosshair on a pickable NPC, attack picks ---- */
static edict_t *pick_target(void) {
    edict_t *p=player();
    if(!pick.on || !p || key_dest!=key_game)return NULL;
    if(pick.frame!=host_framecount){
        pick.frame=host_framecount;pick.target=AW_NPCTargetReach(p,cl.viewangles,PICK_REACH);
        if(pick.target && pick.target==c.e)pick.target=NULL;
    }
    return pick.target;
}
/* view.c: 0 = not picking (normal crosshair rule), 1 = picking, no target
 * (white crosshair, even if the crosshair is off), 2 = red: click picks. */
static void pick_escape(void) {if(pick.on && key_dest==key_menu){pick.on=0;Con_Printf("Pick mode off.\n");}}
int AW_CompanionCrosshair(int x,int y) {
    static int red=-1;int i;long best=0x7fffffff,d,r,g,b;
    pick_escape();
    if(!pick.on)return 0;
    if(!pick_target())return 1;
    if(red<0)for(red=0,i=0;i<256 && host_basepal;i++){
        r=host_basepal[i*3]-255;g=host_basepal[i*3+1];b=host_basepal[i*3+2];
        d=r*r+g*g+b*b;if(d<best){best=d;red=i;}
    }
    Draw_Fill(x,y+3,8,2,red);Draw_Fill(x+3,y,2,8,red);   /* a red '+' */
    return 2;
}
/* cl_input.c: the attack button while picking picks instead of punching. */
int AW_CompanionButtons(int bits) {
    static int held;edict_t *t;
    pick_escape();
    if(!pick.on){held=bits&1;return bits;}
    if((bits&1) && !held){
        t=pick_target();
        if(t)pick_npc(t);else Con_Printf("Pick: no NPC under the crosshair.\n");
    }
    held=bits&1;return bits&~1;
}
int AW_CompanionPickMode(void) {return pick.on;}

/* ---- commands ---- */
static void report(void) {
    double span=sv.time-stats.started;unsigned long thinks=stats.thinks;
    if(span<.001)span=.001;
    if(!alive())Con_Printf("Companion off.\n");
    else {
        int self[3],goal[3];edict_t *p=player();
        static const char *modes[]={"follow","ping","detour","flood","walk route","lost"};
        feet(c.e,self);if(p)feet(p,goal);else VectorCopy(self,goal);
        Con_Printf("Companion %s: %s, %s, %ld units away\n",c.kind==1?"(test)":"(picked)",pr_strings+c.e->v.netname,
            c.teleport?"teleporting":c.near?"standing":modes[c.path.mode<6?c.path.mode:0],
            (long)AW_PathLength(goal[0]-self[0],goal[1]-self[1]));
    }
    Con_Printf("thinks %lu (%.1f/s) stuck %lu pings %lu (%lu traces) detours %lu\n",thinks,thinks/span,
        aw_path_stats.stuck,aw_path_stats.pings,aw_path_stats.ping_traces,aw_path_stats.detours);
    Con_Printf("floods %lu (%lu cells) routes %lu lost %lu; teleports: far %lu, stuck %lu; respawns %lu\n",
        aw_path_stats.floods,aw_path_stats.flood_cells,aw_path_stats.routes,aw_path_stats.lost,
        stats.teleports_far,stats.teleports_stuck,stats.respawns);
    Con_Printf("traces/s search %.2f move %.1f; ms/think avg %.3f max %.3f; over 20 ms %lu; unstick steps %lu\n",aw_path_stats.traces/span,
        stats.move_traces/span,thinks?stats.think_seconds*1000/thinks:0.0,stats.think_max*1000,stats.slow_thinks,stats.heavy_steps);
    Con_Printf("distance %ld, mimic %s; bytes: path %ld, companion %ld, scratch %ld; no allocation\n",(long)AW_CompanionDistance(),AW_CompanionMimic()?"on":"off",(long)sizeof(aw_path_t),
        (long)sizeof(c),(long)AW_PathScratchBytes());
}
/* on/off, true/false, 1/0: 1 or 0; -1 for anything else. */
int AW_CompanionToggleWord(char *a) {
    if(!Q_strcasecmp(a,"on") || !Q_strcasecmp(a,"true") || !strcmp(a,"1"))return 1;
    if(!Q_strcasecmp(a,"off") || !Q_strcasecmp(a,"false") || !strcmp(a,"0"))return 0;
    return -1;
}
static int start_test(void) {
    edict_t *p=player();
    if(!p || cls.state!=ca_connected){Con_Printf("AmiWind: start the local scene first.\n");return 0;}
    if(alive() && c.kind==1){Con_Printf("Test companion already on.\n");return 0;}
    release(0);reset_stats();c.wanted=1;return spawn_test(p);
}
static void stop(void) {
    c.wanted=0;pick.on=0;
    if(!alive())Con_Printf("Companion already off.\n");else release(0);
}
static void toggle_pick(void) {
    if(!player() || cls.state!=ca_connected){Con_Printf("AmiWind: start the local scene first.\n");return;}
    pick.on=!pick.on;pick.frame=-1;pick.target=NULL;
    Con_Printf(pick.on?"Pick mode: aim at an NPC (red crosshair) and attack to pick; dbg companion pick or Escape leaves.\n":
        "Pick mode off.\n");
}
static void distance(void) {
    float v;
    if(Cmd_Argc()==2){Con_Printf("Companion follow distance %ld (%ld..%ld game units).\n",(long)AW_CompanionDistance(),(long)DISTANCE_MIN,(long)DISTANCE_MAX);return;}
    v=Q_atof(Cmd_Argv(2));
    if(!(v>0)){Con_Printf("Usage: dbg companion distance [%ld..%ld]\n",(long)DISTANCE_MIN,(long)DISTANCE_MAX);return;}
    Cvar_SetValue(follow_distance.name,v<DISTANCE_MIN?DISTANCE_MIN:v>DISTANCE_MAX?DISTANCE_MAX:v);
    Con_Printf("Companion follow distance %ld.\n",(long)AW_CompanionDistance());
}
static void mimic(void) {
    int on;
    if(Cmd_Argc()==3){Con_Printf("Companion mimic speed %s.\n",AW_CompanionMimic()?"on":"off");return;}
    if((on=AW_CompanionToggleWord(Cmd_Argv(3)))<0){Con_Printf("Usage: dbg companion mimic speed [on/off, true/false or 1/0]\n");return;}
    Cvar_SetValue(mimic_speed.name,(float)on);
    Con_Printf("Companion mimic speed %s.\n",on?"on":"off");
}
/* dbg companion [pick/choose/test/off/distance N/mimic speed on|off]; no argument: status. */
static void companion(void) {
    char *a=Cmd_Argv(1);int n=Cmd_Argc();
    if(n==1)report();
    else if(n==2 && (!Q_strcasecmp(a,"pick") || !Q_strcasecmp(a,"choose")))toggle_pick();
    else if(n==2 && !Q_strcasecmp(a,"test"))start_test();
    else if(n==2 && !Q_strcasecmp(a,"off"))stop();
    else if(n<=3 && !Q_strcasecmp(a,"distance"))distance();
    else if(n>=3 && n<=4 && !Q_strcasecmp(a,"mimic") && !Q_strcasecmp(Cmd_Argv(2),"speed"))mimic();
    else Con_Printf("Usage: dbg companion [pick/choose/test/off/distance N/mimic speed on|off]\n");
}
/* Aliases: dbg companiontest on/off, dbg pickcompanion, dbg choosecompanion. */
static void companiontest(void) {
    int on=Cmd_Argc()==2?AW_CompanionToggleWord(Cmd_Argv(1)):-1;
    if(Cmd_Argc()==1)report();
    else if(on==1)start_test();
    else if(on==0)stop();
    else Con_Printf("Usage: dbg companiontest [on/off]\n");
}
static void pickcompanion(void) {toggle_pick();}
void AW_CompanionInit(void) {
    Cvar_RegisterVariable(&think_interval);Cvar_RegisterVariable(&follow_distance);Cvar_RegisterVariable(&mimic_speed);
    Cmd_AddCommand("aw_companion",companion);
    aw_companion_crosshair=AW_CompanionCrosshair;aw_companion_buttons=AW_CompanionButtons;
    aw_companion_scene=AW_CompanionSceneSpawn;aw_companion_home=AW_CompanionHome;
    Cmd_AddCommand("aw_companiontest",companiontest);
    Cmd_AddCommand("aw_pickcompanion",pickcompanion);
}
