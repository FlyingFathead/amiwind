/* SPDX-License-Identifier: GPL-2.0-or-later
 * Ordinary hinged doors (engine/aga/src/aw_hinged_door.c) on the engine's
 * own collision (world.c SV_Move, SV_ClipMoveToEntity with a turned brush
 * model, SV_LinkEdict): the table, the 90 degree turn in one second, the
 * prompt, the sounds, locks, reversing, a door that holds when it would turn
 * into the player, and a CHIM placement door through the CHIM hooks. */
#include "quakedef.h"
#include "aw_hinged_door.h"
#include "chim/chim.h"
#include <assert.h>
#include <stdarg.h>

server_t sv;server_static_t svs;client_state_t cl;int pr_edict_size;
globalvars_t *pr_global_struct;
void PR_ExecuteProgram(func_t f){(void)f;}
#define VectorSet(v,x,y,z) ((v)[0]=(x),(v)[1]=(y),(v)[2]=(z))
void ClearLink(link_t *l){l->prev=l->next=l;}
void RemoveLink(link_t *l){l->next->prev=l->prev;l->prev->next=l->next;}
void InsertLinkBefore(link_t *l,link_t *before){l->next=before;l->prev=before->prev;l->prev->next=l;l->next->prev=l;}
static edict_t edicts[8];static eval_t refs[8];static client_t client;
char *pr_strings="\0func_wall\0info_null";
#define FUNC_WALL 1
int (*aw_hinged_use)(void);
int (*aw_hinged_hint)(const char **name,const char **action);
void (*aw_hinged_spawn)(void);
void (*aw_hinged_tick)(double seconds);
int (*aw_hinged_locked_sound)(void);
/* a script's lock on one reference (aw_mwhost.c AW_ObjectLockLevel in the engine) */
static unsigned script_ref;static int script_level;
static int script_lock(unsigned reference,int original){return reference==script_ref?script_level:original;}
int (*aw_chim_door_yaw)(unsigned pid,float yaw);
int (*aw_chim_door_clip)(unsigned pid,vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *trace);

static const char *table;
static int opens,started,stopped,last_entity,last_channel;static float last_volume,last_attenuation;
static char last_path[64];static sfx_t sample;static xcommand_t door_command;static char *argv1;
edict_t *EDICT_NUM(int n){assert(n>=0 && n<sv.max_edicts);return &edicts[n];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-edicts);}
eval_t *GetEdictFieldValue(edict_t *e,char *name){return strcmp(name,"aw_ref")?NULL:&refs[e-edicts];}
int COM_FOpenFile(char *path,FILE **f){
    if(strcmp(path,"hinged-doors.txt") || !table){*f=NULL;return -1;}
    opens++;*f=tmpfile();fputs(table,*f);rewind(*f);return (int)strlen(table);
}
sfx_t *S_PrecacheSound(char *name){strcpy(last_path,name);strcpy(sample.name,name);return &sample;}
void S_StartSound(int entnum,int channel,sfx_t *s,vec3_t origin,float volume,float attenuation){
    (void)origin;assert(s==&sample);started++;last_entity=entnum;last_channel=channel;last_volume=volume;last_attenuation=attenuation;
}
void S_StopSound(int entnum,int channel){(void)entnum;assert(channel==6);stopped++;}
float Cvar_VariableValue(char *name){assert(!strcmp(name,"aw_door_sounds"));return 1;}
void Cmd_AddCommand(char *name,xcommand_t f){assert(!strcmp(name,"aw_hinged_door"));door_command=f;}
int Cmd_Argc(void){return argv1?2:1;}
char *Cmd_Argv(int i){return i==1 && argv1?argv1:"";}
void Con_Printf(char *fmt,...){va_list ap;va_start(ap,fmt);vprintf(fmt,ap);va_end(ap);}
void Con_DPrintf(char *fmt,...){(void)fmt;}
void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(2);}
void Host_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(3);}
void *Hunk_AllocName(int n,char *name){(void)name;return calloc(1,n);}
int SV_ModelIndex(char *name){(void)name;return 0;}
void AW_BarrierClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,edict_t *entity,trace_t *trace){
    (void)start;(void)mins;(void)maxs;(void)end;(void)entity;(void)trace;
}
static char last_subtitle[96];static int subtitles;
void AW_UISubtitle(const char *name,const char *text,double duration){
    (void)name;(void)duration;strncpy(last_subtitle,text,sizeof(last_subtitle)-1);subtitles++;
}

/* A box as a chain of six axial planes: outside each plane is empty. */
typedef struct {mplane_t planes[6];dclipnode_t nodes[6];} box_hull_t;
static void box_hull(hull_t *hull,box_hull_t *b,const vec3_t lo,const vec3_t hi,const vec3_t clip_mins){
    int i;
    memset(b,0,sizeof(*b));memset(hull,0,sizeof(*hull));
    for(i=0;i<6;i++){
        b->planes[i].normal[i/2]=(i&1)?-1:1;b->planes[i].type=3;
        b->planes[i].dist=(i&1)?-lo[i/2]:hi[i/2];
        b->nodes[i].planenum=i;b->nodes[i].children[0]=CONTENTS_EMPTY;
        b->nodes[i].children[1]=i==5?CONTENTS_SOLID:i+1;
    }
    hull->planes=b->planes;hull->clipnodes=b->nodes;hull->firstclipnode=0;hull->lastclipnode=5;
    if(clip_mins)VectorCopy(clip_mins,hull->clip_mins);
}
static vec3_t pmins={-7.32f,-7.12f,-16.625f},pmaxs={7.32f,7.12f,16.625f};
/* The door: local x 0..4 (thickness), y 0..32 (width, hinge at the origin), z 0..48. */
static vec3_t dlo={0,0,0},dhi={4,32,48};
static model_t world,door,wall;static box_hull_t door0,door1,wall0;static mleaf_t leafs[2];
static dclipnode_t empty_node;static mplane_t empty_plane;

static void setup(void){
    vec3_t lo,hi;int i;
    memset(edicts,0,sizeof(edicts));memset(refs,0,sizeof(refs));
    pr_edict_size=sizeof(edict_t);sv.edicts=edicts;sv.max_edicts=8;sv.num_edicts=5;sv.active=true;
    memset(&world,0,sizeof(world));world.type=mod_brush;
    VectorSet(world.mins,-4096,-4096,-4096);VectorSet(world.maxs,4096,4096,4096);
    leafs[1].contents=CONTENTS_EMPTY;world.leafs=leafs;world.nodes=(mnode_t *)&leafs[1];
    empty_plane.normal[2]=1;empty_plane.dist=-9000;empty_plane.type=2;
    empty_node.planenum=0;empty_node.children[0]=empty_node.children[1]=CONTENTS_EMPTY;
    for(i=0;i<3;i++){world.hulls[i].planes=&empty_plane;world.hulls[i].clipnodes=&empty_node;}
    sv.worldmodel=&world;sv.models[1]=&world;
    memset(&door,0,sizeof(door));door.type=mod_brush;door.nummodelsurfaces=6;
    VectorCopy(dlo,door.mins);VectorCopy(dhi,door.maxs);
    box_hull(&door.hulls[0],&door0,dlo,dhi,NULL);
    VectorAdd(dlo,pmins,lo);VectorAdd(dhi,pmaxs,hi);box_hull(&door.hulls[1],&door1,lo,hi,pmins);
    sv.models[2]=&door;
    SV_ClearWorld();
    edicts[0].v.modelindex=1;edicts[0].v.solid=SOLID_BSP;edicts[0].v.movetype=MOVETYPE_PUSH;
    /* 1: an unlocked hinged door at the origin, closed yaw 0 */
    edicts[1].v.classname=FUNC_WALL;edicts[1].v.modelindex=2;edicts[1].v.solid=SOLID_BSP;
    edicts[1].v.movetype=MOVETYPE_PUSH;VectorCopy(dlo,edicts[1].v.mins);VectorCopy(dhi,edicts[1].v.maxs);refs[1]._float=100;
    /* 3: a locked door far east; 4: the census hall door (lock level 100; the story holds its lock) */
    edicts[3]=edicts[1];VectorSet(edicts[3].v.origin,300,0,0);refs[3]._float=200;
    edicts[4]=edicts[1];VectorSet(edicts[4].v.origin,-300,0,0);refs[4]._float=172860;
    for(i=1;i<5;i++)if(i!=2)SV_LinkEdict(&edicts[i],false);
    /* 2: the player, standing east of the door's middle, looking west at it */
    edicts[2].v.solid=SOLID_SLIDEBOX;edicts[2].v.movetype=MOVETYPE_WALK;
    VectorCopy(pmins,edicts[2].v.mins);VectorCopy(pmaxs,edicts[2].v.maxs);edicts[2].v.view_ofs[2]=13.3f;
    VectorSet(edicts[2].v.origin,40,16,16.625f);SV_LinkEdict(&edicts[2],false);
    client.edict=&edicts[2];svs.clients=&client;svs.maxclients=1;
    VectorSet(cl.viewangles,0,180,0);
}
static void place_player(float x,float y,float yaw){
    VectorSet(edicts[2].v.origin,x,y,16.625f);SV_LinkEdict(&edicts[2],false);cl.viewangles[1]=yaw;
}
static int solid_at(edict_t *e,float x,float y,float z){
    vec3_t p;trace_t t;VectorSet(p,x,y,z);
    t=SV_ClipMoveToEntity(e,p,vec3_origin,vec3_origin,p);return t.startsolid || t.allsolid;
}
static void tick(double seconds,int steps){int i;for(i=0;i<steps;i++)AW_HingedDoorTick(seconds);}

static const char *good=
    "AWHD1\n"
    "W doors/d0123456789abcdef.wav 0.5 1.2\n"
    "W doors/dfedcba9876543210.wav 0.25 0.9\n"
    "W doors/d00000000000000aa.wav 1 0.4\n"
    "B 0 1 Door\n"
    "B -1 -1 Gate of the Tribunal\n"
    "D 100 0 0 0\n"
    "D 150 9 0 0\n"
    "D 200 1 50 1\n"
    "D 199 0 0 0\n"
    "D 172860 0 100 1\n"
    "L 2\n";

static void table_mode(void){
    table=good;
    assert(AW_HingedDoorRow(100)==0 && AW_HingedDoorRow(200)==1 && AW_HingedDoorRow(172860)==2);
    /* out of order and a base that does not exist: left out */
    assert(AW_HingedDoorRow(150)<0 && AW_HingedDoorRow(199)<0 && AW_HingedDoorRow(7)<0 && opens==1);
    printf("table ok\n");
}
static void bad_table_mode(void){
    /* a sample outside doors/ would renumber everything after it: the whole table goes */
    table="AWHD1\nW ../evil.wav 1 1\nW doors/d0123456789abcdef.wav 0.5 1.2\nB 0 0 Door\nD 100 0 0 0\n";
    assert(AW_HingedDoorRow(100)<0);
    printf("bad table ok\n");
}

static void door_mode(void){
    const char *name,*action;edict_t *d=&edicts[1];int i;
    table=good;setup();AW_HingedDoorInit();assert(door_command && aw_hinged_use==AW_HingedDoorUse);
    AW_HingedDoorMapBegin();AW_HingedDoorSpawn();AW_HingedDoorSpawn();	/* a second spawn adds nothing */
    assert(AW_HingedDoorProtect(&edicts[1]) && AW_HingedDoorProtect(&edicts[3]) && AW_HingedDoorProtect(&edicts[4]));
    /* closed: blocks the doorway (x 0..4, y 0..32), the swing quadrant east is open */
    assert(solid_at(d,2,16,24) && !solid_at(d,16,-2,24));
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(name,"Door") && !strcmp(action,"Open: E"));
    /* nothing moves, nothing is turned or tested */
    tick(.1,5);assert(d->v.angles[1]==0 && started==0);
    /* open: the Open Sound at the door, 90 degrees in one second, yaw falling */
    assert(AW_HingedDoorUse() && started==1 && last_entity==1 && last_channel==6 && last_volume==.5f &&
           last_attenuation==1 && !strcmp(last_path,"doors/d0123456789abcdef.wav"));
    tick(.05,10);assert(fabs(d->v.angles[1]+45)<.01f);
    tick(.1,4);assert(fabs(d->v.angles[1]+81)<.01f);	/* 0.9 s: not there yet */
    tick(.1,1);assert(d->v.angles[1]==-90);
    /* the collision turned with it: the doorway is free, the door lies along x, y -4..0 */
    assert(!solid_at(d,2,16,24) && solid_at(d,16,-2,24));
    /* the doorway is clear: the ray where the door stood finds nothing */
    assert(!AW_HingedDoorHint(&name,&action));
    /* close: the Close Sound, back to the placed yaw */
    place_player(45,-2,180);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Close: E"));
    assert(AW_HingedDoorUse() && started==2 && last_volume==.25f && !strcmp(last_path,"doors/dfedcba9876543210.wav"));
    tick(.1,10);assert(d->v.angles[1]==0 && solid_at(d,2,16,24));
    /* a use while it turns reverses it from where it is */
    place_player(40,16,180);
    assert(AW_HingedDoorUse());tick(.1,3);assert(fabs(d->v.angles[1]+27)<.01f);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Close: E"));
    assert(AW_HingedDoorUse());tick(.1,2);assert(fabs(d->v.angles[1]+9)<.01f);
    tick(.1,5);assert(d->v.angles[1]==0);
    /* the player in the swing: the door turns until it would touch them and holds, its sound stops */
    place_player(20,14,180);
    assert(AW_HingedDoorUse());i=stopped;tick(.05,40);
    assert(d->v.angles[1]<-5 && d->v.angles[1]>-80 && stopped>i);
    /* the player reads why, once for the whole hold (40 ticks held) */
    assert(subtitles==1 && !strcmp(last_subtitle,AW_HINGE_HELD_TEXT));
    {
        trace_t t=SV_ClipMoveToEntity(d,edicts[2].v.origin,pmins,pmaxs,edicts[2].v.origin);
        assert(!t.startsolid && !t.allsolid);	/* never turned into the player */
    }
    /* the player steps away: it goes on */
    place_player(60,60,180);tick(.1,10);assert(d->v.angles[1]==-90);
    /* closing on the player: the same rule */
    {
        float before;
        place_player(30,-20,135);	/* aim at the open door from the south-east */
        assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Close: E"));
        assert(AW_HingedDoorUse());place_player(20,14,135);tick(.05,40);
        before=d->v.angles[1];assert(before<-10 && before>-85 && subtitles==2);
        place_player(60,60,180);tick(.1,10);assert(d->v.angles[1]==0 && subtitles==2);
    }
    /* locked: the locked sound, nothing turns, the prompt says so */
    place_player(340,16,180);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(name,"Gate of the Tribunal") && !strcmp(action,"Locked"));
    i=started;assert(AW_HingedDoorUse() && started==i+1 && !strcmp(last_path,"doors/d00000000000000aa.wav"));
    tick(.1,10);assert(edicts[3].v.angles[1]==0);
    /* dbg door opens it anyway (testing); dbg door status/list print */
    argv1=NULL;door_command();tick(.1,10);assert(edicts[3].v.angles[1]==-90);
    argv1="list";door_command();argv1=NULL;
    /* the hall door is a hinged door too; with no story rule its table lock (level 100) keeps it shut */
    place_player(-260,16,180);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(name,"Door") && !strcmp(action,"Locked"));
    assert(AW_HingedDoorUse());tick(.1,10);assert(edicts[4].v.angles[1]==0);
    /* object state (v0.0.51): a script's Unlock opens a door the game data locks, its Lock shuts an open one;
     * the story's word still comes first (tested below); the game data's own levels for GetLocked */
    assert(AW_HingedDoorOriginalLock(200)==50 && AW_HingedDoorOriginalLock(100)==0 &&
           AW_HingedDoorOriginalLock(172860)==100 && AW_HingedDoorOriginalLock(999)==-1);
    script_ref=172860;script_level=0;aw_object_lock_level=script_lock;
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Open: E"));
    script_ref=172860;script_level=40;
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Locked"));
    aw_object_lock_level=NULL;
    /* out of reach: nothing */
    place_player(200,16,180);assert(!AW_HingedDoorHint(&name,&action));
    /* a new map forgets the doors */
    AW_HingedDoorMapBegin();place_player(40,16,180);assert(!AW_HingedDoorHint(&name,&action));
    printf("door ok\n");
}

/* A CHIM placement door: the CHIM hooks turn and clip it (stand-ins here,
 * the real ones are tested in tests/aga_chim_world_test.c "door"). */
static edict_t *chim_door;static int chim_turns;
static int chim_yaw(unsigned pid,float yaw){assert(pid==7);chim_door->v.angles[1]=yaw;chim_turns++;return 1;}
static int chim_clip(unsigned pid,vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *trace){
    assert(pid==7);*trace=SV_ClipMoveToEntity(chim_door,start,mins,maxs,end);return 1;
}
static void chim_mode(void){
    const char *name,*action;float yaw=30,d[2]={100,0};int n;
    table=good;setup();
    /* the world trace holds the placement (CHIM merges its placements into the world's trace) */
    chim_door=&edicts[5];memset(chim_door,0,sizeof(*chim_door));chim_door->v.modelindex=2;chim_door->v.solid=SOLID_BSP;chim_door->v.movetype=MOVETYPE_PUSH;
    VectorSet(chim_door->v.origin,0,0,0);chim_door->v.angles[1]=30;
    world.hulls[0]=door.hulls[0];world.hulls[1]=door.hulls[1];
    for(n=1;n<5;n++)if(n!=2){SV_UnlinkEdict(&edicts[n]);edicts[n].free=1;}
    AW_HingedDoorInit();
    aw_chim_door_yaw=chim_yaw;aw_chim_door_clip=chim_clip;
    AW_HingedDoorMapBegin();
    assert(!AW_HingedDoorPlacement(8,999,chim_door->v.origin,32.2f,&yaw));		/* not a door */
    assert(AW_HingedDoorPlacement(9,172860,chim_door->v.origin,32.2f,&yaw));	/* the hall door: hinged too */
    assert(AW_HingedDoorPlacement(7,100,chim_door->v.origin,32.2f,&yaw) && yaw==30);
    AW_HingedDoorSpawn();	/* the map's edicts do not drop the placement */
    /* the world's yaw-0 hull stands in for the placement drawn at yaw 0: aim at its middle */
    chim_door->v.angles[1]=0;yaw=0;AW_HingedDoorMapBegin();
    assert(AW_HingedDoorPlacement(7,100,chim_door->v.origin,32.2f,&yaw) && yaw==0);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Open: E"));
    assert(AW_HingedDoorUse() && last_entity==MAX_EDICTS);
    n=chim_turns;tick(.1,10);assert(chim_turns>n && chim_door->v.angles[1]==-90);
    /* a chunk that loads again gets the door's present pose */
    yaw=0;assert(AW_HingedDoorPlacement(7,100,chim_door->v.origin,32.2f,&yaw) && yaw==-90);
    /* a window recentre moves the door with the frame */
    AW_HingedDoorRecentre(d);argv1="list";door_command();argv1=NULL;
    /* DOOR-BANK-STREAMED-FRAME-51, hinged doors: after a streamed crossing the running map keeps its coordinates and
     * CHIM places the frame the player walked into at its window slot's offset (chim_chunks.c: dx, dy), in the same
     * coordinates as the player, so its doors are picked and turned with no shift of their own (unlike the load
     * doors' banks, which are in each frame's own coordinates). A door 2048 east and 1024 north of the start frame's
     * origin: picked and opened from there; the same eye at the start frame's origin finds nothing. */
    {
        static box_hull_t far0,far1;vec3_t lo,hi,o={2048,1024,0};
        VectorCopy(o,chim_door->v.origin);chim_door->v.angles[1]=0;
        VectorAdd(dlo,o,lo);VectorAdd(dhi,o,hi);box_hull(&world.hulls[0],&far0,lo,hi,NULL);
        VectorAdd(lo,pmins,lo);VectorAdd(hi,pmaxs,hi);box_hull(&world.hulls[1],&far1,lo,hi,pmins);
        yaw=0;AW_HingedDoorMapBegin();
        assert(AW_HingedDoorPlacement(7,100,chim_door->v.origin,32.2f,&yaw) && yaw==0);
        place_player(o[0]+40,o[1]+16,180);
        assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Open: E"));
        n=chim_turns;assert(AW_HingedDoorUse());tick(.1,10);assert(chim_turns>n && chim_door->v.angles[1]==-90);
        place_player(40,16,180);assert(!AW_HingedDoorHint(&name,&action));
        world.hulls[0]=door.hulls[0];world.hulls[1]=door.hulls[1];VectorCopy(vec3_origin,chim_door->v.origin);
    }
    /* A locked placement door (reference 200, lock level 50; a CHIM room's or a frame's: the same hooks) stays
     * shut: the prompt says Locked, the use plays the locked sound and nothing is turned. */
    chim_door->v.angles[1]=0;yaw=0;AW_HingedDoorMapBegin();
    assert(AW_HingedDoorPlacement(7,200,chim_door->v.origin,32.2f,&yaw) && yaw==0);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Locked"));
    n=chim_turns;assert(AW_HingedDoorUse() && !strcmp(last_path,"doors/d00000000000000aa.wav"));
    tick(.1,10);assert(chim_turns==n && chim_door->v.angles[1]==0);
    /* An activated object's collision-only marker (a func_wall whose model has no faces, kept by a CHIM map:
     * tools/chim/frame_map.py keep_activated) for a door the placement draws: it stops being solid, so it
     * neither stands shut in the doorway nor hides the placement from the aim. A marker of anything else stays. */
    {
        static model_t marker;edict_t *m=&edicts[6],*other=&edicts[7];
        memset(&marker,0,sizeof(marker));marker.type=mod_brush;marker.nummodelsurfaces=0;
        VectorCopy(dlo,marker.mins);VectorCopy(dhi,marker.maxs);marker.hulls[0]=door.hulls[0];marker.hulls[1]=door.hulls[1];
        sv.models[3]=&marker;sv.num_edicts=8;
        memset(m,0,sizeof(*m));m->v.classname=FUNC_WALL;m->v.modelindex=3;m->v.solid=SOLID_BSP;m->v.movetype=MOVETYPE_PUSH;
        VectorCopy(dlo,m->v.mins);VectorCopy(dhi,m->v.maxs);refs[6]._float=200;SV_LinkEdict(m,false);
        *other=*m;memset(&other->area,0,sizeof(other->area));refs[7]._float=172859;SV_LinkEdict(other,false);
        AW_HingedDoorSpawn();
        assert(m->v.solid==SOLID_NOT && other->v.solid==SOLID_BSP);
        sv.num_edicts=5;
    }
    printf("chim ok\n");
}

/* The census hall door (172860, "chargen door hall": lock level 100, no key,
 * no script). The story holds its lock (aw_opening.c AW_OpeningHingedStory:
 * the door guard unlocks it once the player has the papers, as the original's
 * CharGenDoorGuardTalker does); after that it turns like every hinged door.
 * The stand-in story below keeps the same answers. */
static int story_hall,story_open,story_events[5];
static int census_story(unsigned ref,int event){
    if(ref!=172860)return -1;
    assert(event>=0 && event<5);story_events[event]++;
    switch(event){
    case AW_HINGE_STORY_LOCK:return story_hall?0:1;
    case AW_HINGE_STORY_OPEN:story_open=1;return 1;
    case AW_HINGE_STORY_CLOSED:story_open=0;return 1;
    case AW_HINGE_STORY_SPAWN:return story_open;
    }
    return 1;
}
static void census_mode(void){
    const char *name,*action;edict_t *h=&edicts[4];int i;
    table=good;setup();AW_HingedDoorInit();aw_hinged_story=census_story;
    AW_HingedDoorMapBegin();AW_HingedDoorSpawn();
    assert(AW_HingedDoorProtect(h));
    /* before the papers: Locked; the use plays the locked sound and the story says why; nothing turns */
    place_player(-260,16,180);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(name,"Door") && !strcmp(action,"Locked"));
    i=started;
    assert(AW_HingedDoorUse() && started==i+1 && !strcmp(last_path,"doors/d00000000000000aa.wav") &&
           story_events[AW_HINGE_STORY_REFUSED]==1 && !story_open);
    tick(.1,10);assert(h->v.angles[1]==0 && solid_at(h,-298,16,24));
    /* the papers shown, the guard unlocks it: Open; its record's open sound; 90 degrees in one second */
    story_hall=1;
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Open: E"));
    assert(AW_HingedDoorUse() && !strcmp(last_path,"doors/d0123456789abcdef.wav") && story_open==1);
    tick(.1,5);assert(fabs(h->v.angles[1]+45)<.01f);
    tick(.1,5);assert(h->v.angles[1]==-90);
    /* its collision turned with it: the doorway is free, the door lies along x */
    assert(!solid_at(h,-298,16,24) && solid_at(h,-284,-2,24));
    /* the census map again (a loaded game, the map loaded again): it stands as it was left */
    AW_HingedDoorMapBegin();h->v.angles[1]=0;SV_LinkEdict(h,false);AW_HingedDoorSpawn();
    assert(h->v.angles[1]==-90 && !solid_at(h,-298,16,24));
    /* closing on the player in its swing: it holds, its sound stops, the words once; then it shuts */
    place_player(-270,-20,135);
    assert(AW_HingedDoorHint(&name,&action) && !strcmp(action,"Close: E"));
    i=subtitles;assert(AW_HingedDoorUse());place_player(-280,14,135);tick(.05,40);
    assert(h->v.angles[1]<-10 && h->v.angles[1]>-85 && subtitles==i+1 && !strcmp(last_subtitle,AW_HINGE_HELD_TEXT));
    assert(story_open==1);
    place_player(-240,60,180);tick(.1,10);assert(h->v.angles[1]==0 && story_open==0 && solid_at(h,-298,16,24));
    argv1="list";door_command();argv1=NULL;
    aw_hinged_story=NULL;
    /* the locked sound to the player alone (a room door this start cannot open, aw_scene.c) */
    assert(aw_hinged_locked_sound==AW_HingedDoorLockedSound);
    i=started;assert(AW_HingedDoorLockedSound() && started==i+1 && !strcmp(last_path,"doors/d00000000000000aa.wav") &&
                     last_attenuation==0);
    printf("census ok\n");
}

int main(int argc,char **argv){
    assert(argc==2);
    if(!strcmp(argv[1],"table"))table_mode();
    else if(!strcmp(argv[1],"badtable"))bad_table_mode();
    else if(!strcmp(argv[1],"door"))door_mode();
    else if(!strcmp(argv[1],"chim"))chim_mode();
    else if(!strcmp(argv[1],"census"))census_mode();
    else return 1;
    return 0;
}
