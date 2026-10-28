/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded local scene links, converted from owned door records. One BSP at a
 * time. This is not inventory, quest persistence or original opening logic.
 */
#include "quakedef.h"
#include "aw_links.h"
#include "aw_inventory.h"
#include "aw_hand_state.h"
#include <errno.h>
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_story.h"
#include "aw_region.h"
#include "aw_town.h"
#include "aw_section.h"
#include "aw_mappath.h"
#include "aw_world.h"
#include "chim/chim.h"
#include "aw_character.h"
#include "aw_harvest_runtime.h"
#include "aw_miniwind.h"
#include "aw_quickchar.h"
#include "aw_testbox.h"
#include "aw_travel.h"
#include "aw_clock.h"
#include "aw_tryalloc.h"
/* Ordinary hinged doors (aw_hinged_door.c sets these; NULL: none). */
int (*aw_hinged_use)(void);
int (*aw_hinged_hint)(const char **name,const char **action);
void (*aw_hinged_spawn)(void);
void (*aw_hinged_tick)(double seconds);
int (*aw_hinged_locked_sound)(void);
/* aw_hinged_door.c AW_HingedDoorLoadLock (DEBUG-GOD-LOCKED-DOORS-51); NULL in fixtures without it: no locks. */
int (*aw_load_door_lock)(unsigned reference,int use);
/* aw_talk.c AW_CanTalk (TALK-PROMPT-RULES): the prompt, E (pr_cmds.c #79) and the caravaners; NULL without it. */
int (*aw_can_talk)(edict_t *e);
#include "amiwind_version.h"

/* CHIM rooms that need more Fast RAM than this start has (CHIM-ROOM-16MB-REFUSAL-48). The builder marks each
 * room map whose store set does not fit the 16 MB baseline's zone with "_chim_room_fast_mb" "32" in its
 * worldspawn (tools/chim/heap.py require_room_map_heap). At the door, before anything loads, a marked room is
 * refused when this start runs on less: Fast RAM found under the safe minimum (sys_amiga.c sets
 * aw_fast_ram_found_mb; 0 = the minimum or more) or Options > Video > Extra RAM off (aw_autoram 0: the built
 * heap and no cache bank, the 16 MB baseline). The player stays at the door; a screen on the loading art says
 * why, and ENTER returns to the game. */
long aw_fast_ram_found_mb;
#define ROOM_FAST_KEY "\"_chim_room_fast_mb\""
#define ROOM_REFUSED_FIRST "Sorry, but this interior cannot be run with 16MB of Fast RAM."
#define ROOM_REFUSED_SECOND "Press ENTER to return."
/* CHIM region frames the builder marked for 32 MB of Fast RAM (CHIM-FRAME-16MB-REFUSAL-48; tools/chim/heap.py
 * FRAME_FAST_KEY: a frame whose ring is over the 16 MB baseline's zone or within FRAME_NEAR_BYTES of it):
 * "_chim_frame_fast_mb" "32" in its frame map's worldspawn. At the crossing into such a frame, on less Fast RAM (as
 * for the rooms), the player stays at the last spot inside the frame he is in: the first time the same screen as a
 * refused room says why (ENTER returns), then the message box every 3 seconds while he walks into it. Nothing of the
 * frame is loaded. */
#define FRAME_FAST_KEY "\"_chim_frame_fast_mb\""
#define FRAME_REFUSED_FIRST "Sorry, but this area cannot be run with 16MB of Fast RAM."
static int room_refused;
static const char *refused_text=ROOM_REFUSED_FIRST;
/* 1 when this start decided on no CHIM cache at all (chim_world.c Memory op 4: 0 KiB); 0 with a cache or when it
 * is not known (no CHIM, or not decided yet). */
static int no_cache_bank(void){
    return aw_chim_memory && aw_chim_memory(4,NULL,NULL,0)==0;
}
/* The reason a refused place names: Extra RAM off, the Fast RAM found, or no cache bank taken. */
static void refused_reason(char *out,int size,long mb){
    if(!Cvar_VariableValue("aw_autoram"))
        snprintf(out,size,"Extra RAM is off (Options > Video), the 16 MB baseline");
    else if(aw_fast_ram_found_mb>0)snprintf(out,size,"this machine has %ld MB",aw_fast_ram_found_mb);
    else snprintf(out,size,"this start took no CHIM cache bank (not enough extra Fast RAM; %ld MB counts on one)",mb);
}
/* The Fast RAM a marked room may count on in this start, in MB: 0 when every room loads (enough Fast RAM or
 * not known), else 16. */
static int room_fast_have(void){
    if(!Cvar_VariableValue("aw_autoram"))return 16;
    if(aw_fast_ram_found_mb>0)return 16;
    /* a marked place counts on the CHIM cache bank of the 32 MB minimum: a start that took none (not enough free
     * Fast RAM beyond the margin) holds what the 16 MB baseline holds (CHIM-AUTO-BANK-CLIFF-51: the v0.0.50 32 MB
     * start took none and Akulakhan's Chamber ended the game at its load) */
    return no_cache_bank()?16:0;
}
/* The Fast RAM the map of TARGET needs, in MB, from its worldspawn's mark; 0 for every map without one (BSP room
 * maps, frame maps, the census office). Reads the map's header and the start of its entity lump only. */
static int map_fast_mb(const char *target,const char *key);
int AW_SceneRoomFastMb(const char *target){return map_fast_mb(target,ROOM_FAST_KEY);}
/* The same for a CHIM frame map's FRAME_FAST_KEY mark. */
int AW_SceneFrameFastMb(const char *target){return map_fast_mb(target,FRAME_FAST_KEY);}
static int map_fast_mb(const char *target,const char *key){
    char path[MAX_QPATH+24],text[1024],*p,*end;FILE *f=NULL;unsigned char h[12];long base,at,len;int n,mb=0;
    if(AW_SceneMapSize(target,path,sizeof(path))<124 || !AW_MapPathChim(path))return 0;
    if(COM_FOpenFile(path,&f)<0 || !f)return 0;
    base=ftell(f);
    if(fread(h,1,12,f)==12){
        at=(long)h[4]|((long)h[5]<<8)|((long)h[6]<<16)|((long)h[7]<<24);
        len=(long)h[8]|((long)h[9]<<8)|((long)h[10]<<16)|((long)h[11]<<24);
        if(at>=124 && len>0 && !fseek(f,base+at,SEEK_SET)){
            n=(int)fread(text,1,len<(long)sizeof(text)-1?(size_t)len:sizeof(text)-1,f);text[n<0?0:n]=0;
            if((end=strchr(text,'}'))!=NULL)*end=0;        /* the worldspawn only */
            if((p=strstr(text,key))!=NULL && Q_sscanf(p+strlen(key)," \"%d\"",&mb)!=1)mb=0;
        }
    }
    fclose(f);
    return mb>0 && mb<=2048?mb:0;   /* Fast RAM in MB, as the -heapmb bound */
}
/* 1 when the door to TARGET is refused here (the screen is up). */
int AW_SceneRoomRefuse(const char *target){
    int have=room_fast_have(),mb;
    char why[128];
    if(!have || (mb=AW_SceneRoomFastMb(target))<=have)return 0;
    refused_reason(why,sizeof(why),(long)mb);
    Con_Printf("CHIM room %s needs %ld MB of Fast RAM (its build mark); %s: refused at the door, nothing loaded.\n",
        target,(long)mb,why);
    if(aw_hinged_locked_sound)aw_hinged_locked_sound();
    AW_UIRoomRefused(NULL,NULL);
    refused_text=ROOM_REFUSED_FIRST;room_refused=1;key_dest=key_menu;IN_AWClearButtons();
    return 1;
}
int AW_SceneRoomRefused(void){return room_refused;}
/* Every other way into a marked place (CHIM-32MB-SAVE-ENTRY-48): loading a save, a new/quick start, the console's
 * dbg tp / aw_scene / raw "map" and "changelevel", the silt strider and a door out of a room all go through
 * AW_SceneEntryRefuse before anything is left or loaded. The mark is the room's or the frame's on TARGET's own map, or,
 * with POINT (a save's position in TARGET's coordinates), the frame that holds the point when it lies past TARGET's
 * own core (a save written after a streamed crossing). On less Fast RAM the same screen as at a door says why; ENTER
 * returns to the previous place when a game runs and TO_MENU is 0 (a console jump), else to the main menu (a load
 * or a start: there is no previous place, or it is a death screen). 1 when refused. */
static int refused_to_menu;
static int entry_mark(const char *target,const float *point,int *room){
    char other[16];float arrival[3];int mb;
    *room=1;if((mb=AW_SceneRoomFastMb(target))>0)return mb;
    *room=0;if((mb=AW_SceneFrameFastMb(target))>0)return mb;
    if(point && AW_WorldDestination(target,point,other,arrival) && (mb=AW_SceneFrameFastMb(other))>0)return mb;
    return 0;
}
int AW_SceneEntryRefuse(const char *target,const float *point,int to_menu){
    int have=room_fast_have(),mb,room;
    char why[128];
    if(!have || !target || !*target || (mb=entry_mark(target,point,&room))<=have)return 0;
    refused_reason(why,sizeof(why),(long)mb);
    Con_Printf("CHIM %s %s needs %ld MB of Fast RAM (its build mark); %s: refused, nothing loaded.\n",
        room?"room":"area",target,(long)mb,why);
    AW_UIRoomRefused(NULL,NULL);
    refused_text=room?ROOM_REFUSED_FIRST:FRAME_REFUSED_FIRST;room_refused=1;refused_to_menu=to_menu || !sv.active;
    key_dest=key_menu;IN_AWClearButtons();
    return 1;
}
/* A save's scene and position (aw_save.c AW_SaveRead, through aw_save_entry_refuse): ENTER goes to the main menu. */
int AW_SceneSaveEntryRefuse(const char *scene,const float *position){return AW_SceneEntryRefuse(scene,position,1);}
/* The crossing into a marked CHIM frame (FRAME_FAST_KEY) on less Fast RAM: the player P goes back to the last spot
 * inside the frame he stands in (frame_last, AW_SceneTick), the screen the first time per frame, else the message
 * box. 1 when refused. The mark is read once per target map (cached until the next scene). */
static vec3_t frame_last;static int frame_last_ok;static double frame_said=-10;
static char frame_refused[16],frame_mark_map[16];static int frame_mark_mb;
int AW_SceneFrameRefuse(edict_t *p,const char *target){
    int have=room_fast_have(),mb;
    if(!have || !target || !*target)return 0;
    if(strcmp(frame_mark_map,target)){
        strncpy(frame_mark_map,target,sizeof(frame_mark_map)-1);frame_mark_map[sizeof(frame_mark_map)-1]=0;
        frame_mark_mb=AW_SceneFrameFastMb(target);
    }
    if((mb=frame_mark_mb)<=have)return 0;
    if(frame_last_ok){
        VectorCopy(frame_last,p->v.origin);VectorCopy(frame_last,p->v.oldorigin);
        p->v.velocity[0]=p->v.velocity[1]=0;SV_LinkEdict(p,false);
    }
    if(strcmp(frame_refused,target)){
        strncpy(frame_refused,target,sizeof(frame_refused)-1);frame_refused[sizeof(frame_refused)-1]=0;
        if(!Cvar_VariableValue("aw_autoram"))
            Con_Printf("CHIM frame %s needs %ld MB of Fast RAM (its build mark); Extra RAM is off (Options > Video), the 16 MB baseline: the player stays out, nothing loaded.\n",
                target,(long)mb);
        else Con_Printf("CHIM frame %s needs %ld MB of Fast RAM (its build mark); this machine has %ld MB: the player stays out, nothing loaded.\n",
                target,(long)mb,aw_fast_ram_found_mb);
        AW_UIRoomRefused(NULL,NULL);
        refused_text=FRAME_REFUSED_FIRST;room_refused=1;key_dest=key_menu;IN_AWClearButtons();
        frame_said=realtime;
    }else if(realtime>=frame_said+3 || realtime<frame_said){frame_said=realtime;AW_UISubtitle("",FRAME_REFUSED_FIRST,3);}
    return 1;
}
/* CHIM: the harvest catalogue of the region the player is in while a town
 * runs its frame map; 0 on a legacy map. */
static int harvest_follow(edict_t *p,int arrival){return AW_HarvestFollow(AW_RegionAt,p->v.origin,arrival);}
typedef struct {char source[16],target[16],label[96];vec3_t point,arrival,mins,maxs;float yaw;int bounds;unsigned reference;} aw_scene_link_t;
/* One door bank: the doors of one map (all of Vivec in one CHIM frame holds 157 load doors; tools/town_interiors.py
 * BANK_ROWS follows this, IMPORT-DOORBANK-LIMIT-32). */
#define AW_SCENE_LINKS 256
static aw_scene_link_t links[AW_SCENE_LINKS];static int count,loaded,pending;
static aw_scene_link_t next;
/* A raw "map" / "changelevel" (host_cmd.c), before the running game is left (CHIM-32MB-SAVE-ENTRY-48). A scene
 * change this file started (load_scene, the quick start) was checked there, a region crossing by the tick: those
 * pass. 1 when refused. */
int AW_SceneMapRefuse(const char *name){
    if(!name || (pending && !strcmp(next.target,name)))return 0;
    return AW_SceneEntryRefuse(name,NULL,0);
}
static char links_map[16];
/* The frame whose door table the player uses, and the shift from the running map's coordinates into its own: after a
 * streamed crossing the logical frame (DOOR-BANK-STREAMED-FRAME-51: its doors were never read, 830 of 1,102 exterior
 * entrances dead after walking in), else the running map with no shift. */
static const char *door_scene(void);
static void door_shift(vec3_t shift);
/* A script's Activate after a streamed crossing: only the logical frame's own rows (1 for every row otherwise). */
static int door_in_frame(const aw_scene_link_t *r);
static double door_ready;
static aw_scene_link_t opening_door;
static unsigned door_close;
static float health;
static aw_hand_snapshot_t hand_snapshot;
static double hand_torch_time;
static int hand_clock_ready;
static double started;
static int region_crossing,map_jump;
static const edict_t *travel_rows_for;   /* the travel services' looked-up provider (travel_service, below) */
/* A partial-area build (aw_miniwind.c): what an exit to an area it does not
 * hold says, and the quick start's notice still to show on arrival. */
#define AREA_UNAVAILABLE "Area unavailable"
static int quick_notice;
/* A quick start with aw_skip_census: the quick character screen opens on arrival. */
static int quick_screen;
/* The sandbox's own setup (miniwind.txt "boot", docs/MINIWIND.md: e.g. "dbg companion test;dbg combat on"), once per
 * arrival of the quick start. */
static void miniwind_boot(void) {
    if(AW_Miniwind()->boot[0]){
        char line[AW_MINIWIND_BOOT+2];int i;
        for(i=0;AW_Miniwind()->boot[i] && i<AW_MINIWIND_BOOT;i++)line[i]=AW_Miniwind()->boot[i]==';'?'\n':AW_Miniwind()->boot[i];
        line[i++]='\n';line[i]=0;Cbuf_AddText(line);
    }
}
/* The partial-area notice and the sandbox's setup wait for the quick character screen to close (they were lost
 * behind it: the combat playground's duel never started, v0.0.54-dev1). */
static void quick_screen_done(int accepted) {
    (void)accepted;
    if(AW_MiniwindActive()){AW_UISubtitle(AW_Miniwind()->title,AW_Miniwind()->features,15);miniwind_boot();}
}
static vec3_t area_last;static int area_last_ok;static double area_said=-10;
static int area_hold(edict_t *p);
/* 1: requested, 2: checked spawn awaiting the final signon angle packet. */
static int shroompicker_view;
static float shroompicker_pitch,shroompicker_yaw;
static vec3_t crossing_angles,crossing_velocity;
static float crossing_movetype;
/* Local camera state outlives CL_ClearState during an implicit map handoff.
 * Restore after the legacy signon angle packets, which round to byte angles. */
static int crossing_view_ready;
static qboolean crossing_nodrift;
static float crossing_pitchvel,crossing_driftmove;
static double crossing_laststop;
static cvar_t early_game_demo_start_1={"early_game_demo_start_1","1"};
static cvar_t intro_docks_variant={"intro_docks_variant","2",true};
static cvar_t target_names={"aw_target_names","1",true};
static cvar_t label_style={"aw_interaction_label_style","1",true};
static cvar_t target_style={"aw_target_name_style","1",true};
int AW_SceneUIOption(int option,int change) {
    cvar_t *c=option==0?&target_names:option==1?&target_style:&label_style;int value;
    value=option==0?(c->value!=0):(int)c->value;
    if(option!=0 && (value<1 || value>3))value=1;
    if(change){value=option==0?!value:(value-1+change+3)%3+1;Cvar_SetValue(c->name,value);}
    return value;
}
static void set_label_style(cvar_t *setting) {
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2 && (!Q_strcasecmp(s,"below") || !strcmp(s,"1")))Cvar_SetValue(setting->name,1);
    else if(Cmd_Argc()==2 && (!Q_strcasecmp(s,"topright") || !strcmp(s,"2")))Cvar_SetValue(setting->name,2);
    else if(Cmd_Argc()==2 && (!Q_strcasecmp(s,"hudleft") || !strcmp(s,"3")))Cvar_SetValue(setting->name,3);
    else Con_Printf("%s: below/topright/hudleft (1/2/3)\n",setting->name);
}
static void label_style_command(void){set_label_style(&label_style);}
static void target_style_command(void){set_label_style(&target_style);}
static void target_names_command(void) {
    char *s=Cmd_Argv(1);int value=-1;
    if(!Q_strcasecmp(s,"on") || !strcmp(s,"1") || !Q_strcasecmp(s,"true"))value=1;
    if(!Q_strcasecmp(s,"off") || !strcmp(s,"0") || !Q_strcasecmp(s,"false"))value=0;
    if(Cmd_Argc()==2 && value>=0)Cvar_SetValue(target_names.name,value);
    else Con_Printf("dbg ui targetnames on/off (after character creation)\n");
}
static const char *npc_hint(void);
static edict_t *travel_target(void);
/* CHIM streams its collision with the player (the ring): an actor spawned
 * where the ground is not collidable yet finds nothing under it and stayed in
 * the air for good (COMBAT-CHASE-CHIM-STUCK-46). Such a miss is kept and the
 * same bounded snap tried again (AW_NPCFloorRetry, from AW_SceneTick) until the
 * ground arrives (once a second), or the actor moves or goes. At most 64
 * kept. Legacy maps (no CHIM world): unchanged. */
#define FLOOR_RETRY_MAX 64
static struct {edict_t *e;vec3_t origin;double since;} floor_retry[FLOOR_RETRY_MAX];
static int floor_retries,floor_retrying;static double floor_retry_next;
static void floor_retry_add(edict_t *e) {
    int i;
    if(floor_retrying || !Chim_Active())return;
    for(i=0;i<floor_retries;i++)if(floor_retry[i].e==e){VectorCopy(e->v.origin,floor_retry[i].origin);return;}
    if(floor_retries>=FLOOR_RETRY_MAX)return;
    floor_retry[floor_retries].e=e;VectorCopy(e->v.origin,floor_retry[floor_retries].origin);
    floor_retry[floor_retries].since=sv.time;floor_retries++;
}
/* Once a second of server time: returns how many actors it put on the ground. */
int AW_NPCFloorRetry(void) {
    int i,landed=0,drop;edict_t *e;
    if(!floor_retries)return 0;
    if(!sv.active || !Chim_Active() || sv.time<floor_retry_next-2 || sv.time<floor_retry[0].since){floor_retries=0;floor_retry_next=0;return 0;} /* gone, or a new server */
    if(sv.time<floor_retry_next)return 0;
    floor_retry_next=sv.time+1;floor_retrying=1;
    for(i=0;i<floor_retries;){
        e=floor_retry[i].e;
        drop=e->free || !VectorCompare(e->v.origin,floor_retry[i].origin);
        if(!drop && AW_NPCFloor(e)){landed++;drop=1;}
        if(drop)floor_retry[i]=floor_retry[--floor_retries];else i++;
    }
    floor_retrying=0;
    return landed;
}
/* Resolve the authored feet point against linked world/architectural brushes.
 * Balmora's ground conversion leaves source feet up to 18 units above paving.
 * Bound correction to 32 units so a missing floor cannot move actors a storey. */
int AW_NPCFloor(edict_t *e) {
    vec3_t start,end;trace_t tr;eval_t *mode,*valid,*baked;int k;
    mode=GetEdictFieldValue(e,"aw_ground_mode");if(mode && mode->_float)return 0;
    if(!AW_RegionGroundCoverage(e->v.origin))return 0;
    /* The host fitted the actual rendered soles. A second origin-only snap
     * would destroy that result. Preserve only the exact baked initial position;
     * moved/restored legacy actors still use the bounded runtime fallback. */
    valid=GetEdictFieldValue(e,"aw_ground_valid");baked=GetEdictFieldValue(e,"aw_ground_baked");
    if(valid && valid->_float==1 && baked){
        for(k=0;k<3;k++)if(!isfinite(baked->vector[k]) || !isfinite(e->v.origin[k]) ||
            fabs(e->v.origin[k]-baked->vector[k])>.001f)break;
        if(k==3){e->v.flags=(int)e->v.flags|FL_ONGROUND;SV_LinkEdict(e,false);return 1;}
    }
    VectorCopy(e->v.origin,start);VectorCopy(start,end);start[2]+=8;end[2]-=32;
    tr=SV_Move(start,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,e);
    if(!tr.startsolid && !tr.allsolid && tr.fraction>=1)floor_retry_add(e);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<AW_WALKABLE_Z)return 0;
    VectorCopy(tr.endpos,e->v.origin);e->v.origin[2]+=0.25f;
    e->v.flags=(int)e->v.flags|FL_ONGROUND;
    if(tr.ent)e->v.groundentity=EDICT_TO_PROG(tr.ent);
    SV_LinkEdict(e,false);return 1;
}
/* Shared with the QC greeting builtin. A visible head can be above the fixed
 * walking hull. Intersect the resident alias bounds in model space, retaining
 * the exact crosshair and world/brush occlusion rather than a facing cone. */
void (*aw_companion_scene)(edict_t *);   /* aw_companion.c: a scene spawned */
void (*aw_combat_scene)(void);           /* aw_combat.c: a scene spawned (before the arena spawns its fight) */
edict_t *AW_NPCTarget(edict_t *p,vec3_t angles) {return AW_NPCTargetReach(p,angles,72);}
/* The same test with a longer reach (dbg pickcompanion: 384 units). */
edict_t *AW_NPCTargetReach(edict_t *p,vec3_t angles,float reach) {
    edict_t *e,*best=NULL;model_t *m;int i,j,index;float limit,lo,hi,a,b,o,d,t;
    vec3_t eye,end,forward,right,up,delta,local,ray;trace_t tr;
    AW_FPUCOUNT(AW_FPU_NPCTARGET);
    if(!p || p->v.movetype!=MOVETYPE_WALK)return NULL;
    AW_FPUCOUNT(AW_FPU_NPCSCAN);
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(angles,forward,right,up);
    VectorMA(eye,reach,forward,end);
    tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);e=tr.ent;
    /* Keep direct physical hits, including legacy assets without bounds. */
    limit=reach;
    if(!tr.startsolid && !tr.allsolid && tr.fraction<1){
        limit=tr.fraction*reach;
        if(e && !e->free && e->v.modelindex && e->v.netname &&
           !strcmp(pr_strings+e->v.classname,"aw_npc"))best=e;
    }else{
        tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);
        if(tr.startsolid || tr.allsolid)return NULL;
        limit=tr.fraction*reach;
    }
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);index=(int)e->v.modelindex;
        if(e==p || e->free || !e->v.netname || index<=0 || index>=MAX_MODELS ||
           strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        m=sv.models[index];if(!m || m->type!=mod_alias)continue;
        VectorSubtract(eye,e->v.origin,delta);
        /* Distance precheck: the bounds lie within the sum of their largest
         * extents of the origin, so an NPC farther than limit plus that sum
         * cannot meet the ray (no direction vectors needed). */
        for(o=0,j=0;j<3;j++)o+=fabs(m->mins[j])>fabs(m->maxs[j])?fabs(m->mins[j]):fabs(m->maxs[j]);
        if(DotProduct(delta,delta)>(limit+o)*(limit+o))continue;
        AW_FPUCOUNT(AW_FPU_NPCTEST);
        AngleVectors(e->v.angles,local,right,up);
        ray[0]=DotProduct(forward,local);ray[1]=-DotProduct(forward,right);ray[2]=DotProduct(forward,up);
        end[0]=DotProduct(delta,local);end[1]=-DotProduct(delta,right);end[2]=DotProduct(delta,up);
        lo=0;hi=limit;
        for(j=0;j<3;j++){
            o=end[j];d=ray[j];
            if(fabs(d)<0.00001f){if(o<m->mins[j] || o>m->maxs[j])break;}
            else{
                a=(m->mins[j]-o)/d;b=(m->maxs[j]-o)/d;
                if(a>b){t=a;a=b;b=t;}if(a>lo)lo=a;if(b<hi)hi=b;
                if(lo>hi)break;
            }
        }
        if(j==3 && lo<limit){limit=lo;best=e;}
    }
    return best;
}
/* The scene draw asks for the target several times a frame (name, travel,
 * hints, speaker): compute it once per host frame, stamped the way Quake
 * stamps visframe, and again only if the view turned or the NPC went away. */
static edict_t *npc_target(void) {
    static int stamp=-1,cached_count;static edict_t *cached,*cached_player,*cached_edicts;static vec3_t cached_angles;
    edict_t *p;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict || cls.state!=ca_connected)return NULL;
    p=svs.clients[0].edict;
    /* same frame, player, view and edict table (a scene load replaces it) */
    if(stamp==host_framecount && cached_player==p && cached_edicts==sv.edicts && cached_count==sv.num_edicts &&
       VectorCompare(cached_angles,cl.viewangles) && (!cached || !cached->free))return cached;
    cached=AW_NPCTarget(p,cl.viewangles);
    stamp=host_framecount;cached_player=p;cached_edicts=sv.edicts;cached_count=sv.num_edicts;
    VectorCopy(cl.viewangles,cached_angles);
    return cached;
}
const char *AW_SceneTargetName(void) {
    edict_t *driver;
    if(!target_names.value || key_dest!=key_game || pending || AW_PlayerDead() || AW_CharacterActive() ||
       AW_ReaderActive() || AW_IntroPromptActive() ||
       (aw_story.stage!=AW_STAGE_DEMO && aw_story.stage<AW_STAGE_PAPERS))return NULL;
    driver=travel_target();if(driver)return pr_strings+driver->v.netname;
    {const char *npc=npc_hint(),*item;item=AW_InventoryHint();return npc?npc:item?item:AW_HarvestHint();}
}
const char *AW_SceneWorldModel(const char *name) {
    FILE *f=NULL;const char *region;
    region=AW_RegionWorldModel(name,intro_docks_variant.value==2 && aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE);
    if(region)return region;
    if(!strcmp(name,"seyda") && intro_docks_variant.value==2 &&
       aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE){
        static char docks[AW_MAP_PATH_SIZE];
        AW_MapPath("intro_docks",docks,sizeof(docks));
        if(COM_FOpenFile(docks,&f)>=0 && f){fclose(f);return docks;}
        if(f)fclose(f);
        Con_Printf("Intro docks variant missing; retaining full exterior.\n");
    }
    return NULL;
}
int AW_Interior(void) {return sv.active && (!strcmp(sv.name,"torchtest") || (AW_MapId(sv.name)>=0 && AW_TownFind(sv.name)<0 && AW_TerrainId(sv.name)<0));}
/* ENGINE-SCENE-NAME-BOUND-35: map names go into 16-byte fields; copy bounded. */
static void copy_name(char *out,size_t size,const char *in){Q_strcpy_bounded(out,in,size);}
static int map_valid(const char *name) {return AW_MapId(name)>=0;}
static void read_links_for(const char *map) {
    FILE *f=NULL;char line[384],extra,path[64];aw_scene_link_t r;int n,i,version;
    if(!map_valid(map))return;
    if(loaded && !strcmp(links_map,map))return;
    copy_name(links_map,sizeof(links_map),map);loaded=1;count=0;
    sprintf(path,"doors-%s.txt",map);
    COM_FOpenFile(path,&f);
    if(!f){sprintf(path,"scene-doors-%s.txt",map);COM_FOpenFile(path,&f);}
    if(!f && AW_MapId(map)<AW_MAP_COUNT && !AW_TownFlag(map,AW_TOWN_OWN_DOORS))COM_FOpenFile("scene-doors.txt",&f);
    if(f) {
        if(!fgets(line,sizeof(line),f)){fclose(f);return;}
        version=!strcmp(line,"AWD3\n")?3:!strcmp(line,"AWD2\n")?2:!strcmp(line,"AWD1\n")?1:0;
        if(!version){fclose(f);return;}
        while(count<AW_SCENE_LINKS && fgets(line,sizeof(line),f)) {
            memset(&r,0,sizeof(r));
            if(version==3)n=Q_sscanf(line,"%15s %15s %u %f %f %f %f %f %f %f %f %f %f %95[^\r\n]",r.source,r.target,&r.reference,
                &r.mins[0],&r.mins[1],&r.mins[2],&r.maxs[0],&r.maxs[1],&r.maxs[2],
                &r.arrival[0],&r.arrival[1],&r.arrival[2],&r.yaw,r.label);
            else n=Q_sscanf(line,version==2?"%15s %15s %f %f %f %f %f %f %f %f %f %f %95[^\r\n]":"%15s %15s %f %f %f %f %f %f %f %f %f %f %c",r.source,r.target,
                &r.mins[0],&r.mins[1],&r.mins[2],&r.maxs[0],&r.maxs[1],&r.maxs[2],
                &r.arrival[0],&r.arrival[1],&r.arrival[2],&r.yaw,version==2?r.label:&extra);
            if(n!=(version==3?14:version==2?13:12) || !map_valid(r.source) ||
                (!map_valid(r.target) && !(version>=2 && !strcmp(r.target,"-"))))continue;
            if(version>=2){for(i=0;r.label[i];i++)if((unsigned char)r.label[i]<32)break;if(r.label[i])continue;}
            for(i=0;i<3;i++)if(!(fabs(r.mins[i])<32768 && fabs(r.maxs[i])<32768 &&
                r.maxs[i]>=r.mins[i] && r.maxs[i]-r.mins[i]<=256 && fabs(r.arrival[i])<32768))break;
            if(i!=3 || !(r.yaw>=0 && r.yaw<360))continue;
            r.bounds=1;links[count++]=r;
        }
        fclose(f);return;
    }
    if(AW_TownFlag(map,AW_TOWN_OWN_DOORS) || AW_MapId(map)>=AW_MAP_COUNT)return;
    if(COM_FOpenFile("scene-links.txt",&f)<0 || !f)return;
    while(count<AW_SCENE_LINKS && fgets(line,sizeof(line),f)) {
        memset(&r,0,sizeof(r));
        n=Q_sscanf(line,"%15s %15s %f %f %f %f %f %f %f %c",r.source,r.target,
            &r.point[0],&r.point[1],&r.point[2],&r.arrival[0],&r.arrival[1],&r.arrival[2],&r.yaw,&extra);
        if(n!=9 || !map_valid(r.source) || !map_valid(r.target))continue;
        for(i=0;i<3;i++)if(!(fabs(r.point[i])<32768 && fabs(r.arrival[i])<32768))break;
        if(i!=3 || !(r.yaw>=0 && r.yaw<360))continue;
        links[count++]=r;
    }
    fclose(f);
}
static void load_scene(aw_scene_link_t *link,int immediate) {
    edict_t *p=svs.clients[0].edict;char command[32];
    if(pending || !map_valid(link->target))return;
    /* a marked room or frame on less Fast RAM (CHIM-32MB-SAVE-ENTRY-48): the strider, a door out of a room, dbg tp;
     * a region crossing was checked by the tick (AW_SceneFrameRefuse) */
    if(!region_crossing && AW_SceneEntryRefuse(link->target,link->arrival,0))return;
    if(!AW_RegionSelect(link->target,link->arrival,intro_docks_variant.value==2 &&
       aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE))return;
    if(region_crossing){
        AW_SetNextLoadingStyle(AW_RegionLoadingFrozen()?AW_LOADING_FROZEN:AW_LOADING_BLANK);
        AW_SetNextLoadingDelay();
    }
    shroompicker_view=0;travel_rows_for=NULL;   /* edicts are reused by the next map: look the provider up again */
    next=*link;pending=1;started=Sys_FloatTime();AW_StreamTransitionBegin();
    AW_SaveCapture();
    health=p->v.health;
    if(!AW_HandSnapshotCapture(&hand_snapshot,p,sv.time))
        Con_Printf("Hand transition state unavailable; destination rules will initialize hands.\n");
    hand_torch_time=AW_TorchAnimationTime();hand_clock_ready=0;
    /* Automatic residency changes retain live held controls. Key releases and
     * focus-loss clearing still run through the normal input path. Doors and
     * explicit teleports keep their deliberate input boundary. */
    if(!region_crossing)IN_AWClearButtons();
    AW_MusicSceneEvent("scene-leave");
    Con_Printf("Loading AmiWind v" AMIWIND_VERSION ": %s...\n",next.target);
    sprintf(command,"map %s\n",next.target);
    if(region_crossing)S_BeginSceneVoice();
    if(immediate)Cbuf_InsertText(command);else Cbuf_AddText(command);
}
/* A teleport to original-game coordinates: the town or region whose map holds
 * the point (a CHIM town's frame map on a CHIM disk, AW_WorldMapTarget), the
 * ring there loaded before the ground is searched (aw_chim_spawn). With a
 * height (dbg tp X Y Z) the player lands on the first surface at or below it,
 * else on the highest one; a blocked target falls back to the scene spawn. */
int AW_MapTeleportAt(const float *source_position,int use_height) {
    aw_scene_link_t r;edict_t *p;float local[3];
    if(pending || !sv.active || svs.maxclients!=1 || !svs.clients ||
       !(p=svs.clients[0].edict) || cls.state!=ca_connected || p->v.health<=0 ||
       AW_StoryRestricted())return 0;
    memset(&r,0,sizeof(r));
    if(!AW_WorldMapTarget(source_position,r.target,r.arrival))return 0;
    if(use_height){
        if(!AW_SourceToWorld(r.target,source_position,local) || !(fabs(local[2])<AW_COORD_BOUND))return 0;
        r.arrival[2]=local[2];
    }
    r.yaw=p->v.v_angle[1];region_crossing=0;door_ready=0;door_close=0;
    crossing_movetype=p->v.movetype;
    load_scene(&r,1);
    if(!pending)return 0;
    map_jump=use_height?2:1;return 1;
}
int AW_MapTeleport(const float *source_position) {return AW_MapTeleportAt(source_position,0);}
/* The view of a shot, as aw_aim sets it (dbg cam recall, aw_cam.c). */
static void shot_view(edict_t *p,float yaw,float pitch) {
    V_StopPitchDrift();cl.viewangles[0]=pitch;cl.viewangles[1]=yaw;cl.viewangles[2]=0;
    p->v.angles[0]=pitch;p->v.angles[1]=yaw;p->v.angles[2]=0;p->v.fixangle=1;
}
/* dbg cam recall (aw_cam.c): a named shot. GLOBAL: the teleport of dbg tp X Y
 * [Z] (the same route, placement and checks; HAS_Z as its Z); a second recall
 * that finds the player already on that map within 48 units of the point only
 * sets the view. Else MAP at the local POINT exactly, noclip: on the current
 * map at once (no reload, SV_LinkEdict without touching triggers), on another
 * map through the debug teleport's map load. The view is applied on arrival
 * after the signon angles (the mushroom picker's view). 0 = unavailable,
 * player state unchanged; 1 = placed now; 2 = loading. */
int AW_SceneShot(int global,const char *map,const float *point,int has_z,float yaw,float pitch) {
    aw_scene_link_t r;edict_t *p;float local[3];
    if(pending || !sv.active || svs.maxclients!=1 || !svs.clients ||
       !(p=svs.clients[0].edict) || cls.state!=ca_connected || p->v.health<=0 ||
       AW_StoryRestricted())return 0;
    memset(&r,0,sizeof(r));
    if(global){
        if(!AW_WorldMapTarget(point,r.target,r.arrival))return 0;
        if(!strcmp(r.target,sv.name) && fabs(p->v.origin[0]-r.arrival[0])<48 && fabs(p->v.origin[1]-r.arrival[1])<48 &&
           (!has_z || (AW_SourceToWorld(r.target,point,local) && p->v.origin[2]<=local[2]+48))){
            shot_view(p,yaw,pitch);return 1;
        }
        if(!AW_MapTeleportAt(point,has_z))return 0;
    }else{
        if(!map_valid(map) || !(fabs(point[0])<AW_COORD_BOUND && fabs(point[1])<AW_COORD_BOUND &&
                                fabs(point[2])<AW_COORD_BOUND))return 0;
        if(!strcmp(map,sv.name)){
            VectorCopy(point,p->v.origin);VectorCopy(vec3_origin,p->v.velocity);
            p->v.movetype=MOVETYPE_NOCLIP;noclip_anglehack=true;
            shot_view(p,yaw,pitch);SV_LinkEdict(p,false);return 1;
        }
        copy_name(r.target,sizeof(r.target),map);VectorCopy(point,r.arrival);
        r.yaw=yaw;region_crossing=0;door_ready=0;door_close=0;
        crossing_movetype=MOVETYPE_NOCLIP;
        load_scene(&r,1);
        if(!pending)return 0;
        map_jump=3;
    }
    next.yaw=yaw;shroompicker_pitch=pitch;shroompicker_yaw=yaw;shroompicker_view=1;
    return 2;
}
/* Ray/slab intersection with converted model bounds. The model origin may
 * be buried in the ceiling or far from the visible handle/hatch surface. */
static int door_hit(aw_scene_link_t *r,vec3_t eye,vec3_t forward,vec3_t hit) {
    int axis;float near=0,far=56,a,b,t;vec3_t delta;
    if(!r->bounds){
        VectorSubtract(r->point,eye,delta);t=Length(delta);
        if(t>56 || t<1 || DotProduct(delta,forward)/t<.45f)return 0;
        VectorCopy(r->point,hit);return 1;
    }
    for(axis=0;axis<3;axis++) {
        if(fabs(forward[axis])<.00001f){if(eye[axis]<r->mins[axis] || eye[axis]>r->maxs[axis])return 0;continue;}
        a=(r->mins[axis]-eye[axis])/forward[axis];b=(r->maxs[axis]-eye[axis])/forward[axis];
        if(a>b){t=a;a=b;b=t;}if(a>near)near=a;if(b<far)far=b;if(near>far)return 0;
    }
    if(far<0 || near>56)return 0;
    for(axis=0;axis<3;axis++)hit[axis]=eye[axis]+forward[axis]*near;
    return 1;
}
/* The doorway a door is set in (DOOR-USE-BLOCKED-53): the use ray may meet a surface this near before the door's use
 * box and still reach the door. The converted collision of an entrance (the Daedric shrines' oval doorways, the fort
 * and ship doors) closes the doorway 1 to 11 units in front of the door model; the original activates the door
 * there. 21 region-frame entrances were refused at 1 unit (tools/door_engine_check.py reads this value). */
#define DOOR_USE_SLACK 16.0f
static int aimed_door(void) {
    int i,best=-1;edict_t *p;vec3_t eye,local,shift,delta,hit,forward,right,up;float distance,closest=57;trace_t tr;
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected)return -1;
    p=svs.clients[0].edict;if(p->v.movetype!=MOVETYPE_WALK)return -1;
    read_links_for(door_scene());door_shift(shift);
    VectorAdd(p->v.origin,p->v.view_ofs,eye);VectorSubtract(eye,shift,local);AngleVectors(cl.viewangles,forward,right,up);
    for(i=0;i<count;i++) {
        if(aw_story.ship_disabled && !strcmp(links[i].target,"prison"))continue;
        if(strcmp(door_scene(),links[i].source) || !door_hit(&links[i],local,forward,hit))continue;
        VectorAdd(hit,shift,hit);       /* back into the running map for the wall trace */
        VectorSubtract(hit,eye,delta);distance=Length(delta);if(distance>=closest)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,hit,MOVE_NOMONSTERS,p);
        if(tr.startsolid || (1-tr.fraction)*distance>(links[i].bounds?DOOR_USE_SLACK:12.0f))continue;
        closest=distance;best=i;
    }
    return best;
}
/* Travel stays unavailable until the destination has a validated arrival
 * and map registration. A stray BSP file alone must never enable a paid ride. */
static int travel_open,travel_choice;
static int travel_return,travel_count=5,travel_town=-1;
static const char *travel_names[]={"Balmora","Gnisis","Suran","Vivec","Cancel"};
static const char *travel_message;
/* The town table names each town's strider (travel_npc) and where it goes:
 * Seyda's Darvame Hleran to Balmora's arrival, Balmora's Selvil Sareloth
 * back to Seyda through Balmora's return point. */
/* The travel services of the game data (TRAVEL-SERVICES-CHIM-51; aw_travel.h): id1/travel.txt, read once; the rows of
 * the provider in front of the player are looked up by its record id (aw_source_id) and kept until another actor is
 * aimed at. travel_services: 1 while the open menu is such a provider's (else the town table's ride above). */
static char *travel_text;static int travel_text_read;
static aw_travel_t travel_rows;static int travel_services;
static int travel_price[AW_TRAVEL_ROWS],travel_hours[AW_TRAVEL_ROWS];
static const char *travel_table(void) {
    FILE *f;int size;
    if(travel_text_read)return travel_text;
    travel_text_read=1;
    if((size=COM_FOpenFile("travel.txt",&f))<0 || !f)return NULL;
    if(size>0 && size<262144 && (travel_text=AW_TryMalloc(size+1))!=NULL){
        if((int)fread(travel_text,1,size,f)==size)travel_text[size]=0;else{free(travel_text);travel_text=NULL;}
    }
    fclose(f);
    if(travel_text && AW_TravelParse(travel_text,NULL,&travel_rows)<0){
        Con_Printf("travel.txt is not a travel table (AWT1); travel services off.\n");free(travel_text);travel_text=NULL;
    }
    return travel_text;
}
static int travel_service(const edict_t *e) {
    eval_t *v;const char *text;
    if(e==travel_rows_for)return travel_rows.count>0;
    travel_rows_for=e;travel_rows.count=0;
    v=GetEdictFieldValue((edict_t *)e,"aw_source_id");
    if(!v || !v->string || !pr_strings[v->string] || !(text=travel_table()))return 0;
    return AW_TravelParse(text,pr_strings+v->string,&travel_rows)>0;
}
static edict_t *travel_target(void) {
    edict_t *e;const aw_town_t *town=AW_Town(AW_TownFind(sv.name));
    if(key_dest!=key_game || AW_StoryRestricted())return NULL;
    e=npc_target();if(!e){travel_rows_for=NULL;return NULL;}
    /* a caravaner in a fight (or dead) offers no ride: the talk rule (aw_talk.c), for the town table's ride and the
     * travel services alike */
    if(aw_can_talk && !aw_can_talk(e))return NULL;
    if(town && town->travel_npc[0] && !strcmp(pr_strings+e->v.netname,town->travel_npc))return e;
    if(travel_service(e))return e;
    return NULL;
}
static int travel_use(void) {
    edict_t *e=travel_target();int i;float local[3],source[3],*player=NULL;
    if(!e)return 0;
    travel_town=AW_TownFind(sv.name);
    if(travel_town>=0 && AW_Town(travel_town)->travel_npc[0] &&
       !strcmp(pr_strings+e->v.netname,AW_Town(travel_town)->travel_npc)){
        travel_services=0;
        travel_return=AW_Town(travel_town)->travel_return;
        travel_count=travel_return?2:5;
    }else{
        /* the price from where the player stands (original coordinates), else the provider's own placement */
        VectorCopy(svs.clients[0].edict->v.origin,local);
        if(AW_WorldToSource(sv.name,local,source))player=source;
        for(i=0;i<travel_rows.count;i++)AW_TravelCost(&travel_rows,i,player,&travel_price[i],&travel_hours[i]);
        travel_services=1;travel_count=travel_rows.count+1;
    }
    travel_open=1;travel_choice=0;travel_message=NULL;
    key_dest=key_menu;IN_AWClearButtons();return 1;
}
/* A ride of the travel services: paid, the clock moved by the ride's hours (none from an interior), then the
 * destination loaded as a door's link would be. */
static void travel_ride(int i) {
    aw_scene_link_t r;const aw_travel_row_t *row=&travel_rows.rows[i];long gold=AW_StateGet(&aw_state,AW_ITEM,"gold_001");
    char path[40];
    if(gold<travel_price[i]){travel_message="You do not have enough gold.";return;}
    if(!map_valid(row->map) || AW_SceneMapSize(row->map,path,sizeof(path))<0){
        travel_message=AW_MiniwindActive()?AREA_UNAVAILABLE:"Destination not in this build.";return;
    }
    memset(&r,0,sizeof(r));copy_name(r.target,sizeof(r.target),row->map);
    VectorCopy(row->arrival,r.arrival);r.yaw=row->yaw;
    if(AW_SceneEntryRefuse(r.target,r.arrival,0)){travel_open=0;return;}
    if(!AW_ItemAdd(&aw_state,"gold_001",-travel_price[i])){travel_message="You do not have enough gold.";return;}
    if(travel_hours[i]>0)AW_ClockAdvance((travel_hours[i]>720?720:travel_hours[i])*3600000);
    travel_open=0;key_dest=key_game;region_crossing=0;door_ready=0;door_close=0;load_scene(&r,0);
}
int AW_TravelKey(int key) {
    /* The refused room's screen (AW_SceneRoomRefuse): ENTER returns the player to the game at the door; it holds the
     * other keys. */
    if(room_refused){
        if(key_dest!=key_menu){room_refused=refused_to_menu=0;return 0;}
        if(key==K_ENTER){
            room_refused=0;key_dest=key_game;IN_AWClearButtons();
            /* a refused load or start (CHIM-32MB-SAVE-ENTRY-48): the main menu, as the death screen's "No" */
            if(refused_to_menu){refused_to_menu=0;Cbuf_AddText("disconnect\naw_main_menu\n");}
        }
        return 1;
    }
    if(!travel_open)return 0;
    if(!sv.active || key_dest!=key_menu){travel_open=0;return 0;}
    if(key==K_ESCAPE || (key==K_ENTER && travel_choice==travel_count-1)){
        travel_open=0;key_dest=key_game;IN_AWClearButtons();return 1;
    }
    if(key==K_UPARROW || key=='w'){travel_choice=(travel_choice+travel_count-1)%travel_count;travel_message=NULL;}
    if(key==K_DOWNARROW || key=='s'){travel_choice=(travel_choice+1)%travel_count;travel_message=NULL;}
    if(key==K_ENTER && travel_services){travel_ride(travel_choice);return 1;}
    if(key==K_ENTER){
        aw_scene_link_t r;const aw_town_t *town=AW_Town(travel_town);memset(&r,0,sizeof(r));
        if(travel_choice==0 && town && AW_TownArrival(travel_return?town->name:town->travel_target,travel_return,r.arrival,&r.yaw)){
            copy_name(r.target,sizeof(r.target),town->travel_target);
            travel_open=0;key_dest=key_game;load_scene(&r,0);
        }else travel_message=AW_MiniwindActive()?AREA_UNAVAILABLE:"Destination not found.";
    }
    return 1;
}
int AW_TravelDraw(void) {
    int i;char line[96];const aw_town_t *town=AW_Town(travel_town),*home;
    if(room_refused && key_dest==key_menu){AW_UIRoomRefused(refused_text,ROOM_REFUSED_SECOND);return 1;}
    if(!travel_open || key_dest!=key_menu || (!town && !travel_services))return 0;
    home=travel_services?NULL:AW_Town(AW_TownFind(town->travel_target));
    AW_UIBox(18,18,284,170);AW_UISmallBegin();
    if(travel_services)sprintf(line,"Travel: %.60s",travel_rows_for?pr_strings+travel_rows_for->v.netname:"");
    else sprintf(line,"Silt Strider: %.60s",town->travel_npc);
    AW_UITextBox(26,23,268,20,line,-1);
    sprintf(line,"Your gold: %ld",(long)AW_StateGet(&aw_state,AW_ITEM,"gold_001"));
    AW_UITextBox(26,44,268,16,line,-1);
    for(i=0;i<travel_count;i++){
        if(travel_services){
            /* the original's line: the destination, then its price in gold (sgp) */
            if(i<travel_rows.count)sprintf(line,"%s%.44s - %ldgp",i==travel_choice?"> ":"  ",travel_rows.rows[i].label,
                (long)travel_price[i]);
            else sprintf(line,"%sCancel",i==travel_choice?"> ":"  ");
        }else sprintf(line,"%s%.60s",i==travel_choice?"> ":"  ",travel_return?(i?"Cancel":home?home->title:"?"):travel_names[i]);
        if(AW_UIMode()==2){
            int y=61+i*18;
            AW_UIBox(40,y,240,18);
            if(i==travel_choice)AW_UIFill(43,y+3,234,12,AW_UIColor(54,47,32));
            AW_UITextBox(44,y,232,18,line,-1);
        }else AW_UITextBox(40,63+i*17,240,17,line,-1);
    }
    AW_UITextBox(26,153,268,16,travel_message?travel_message:"Arrows: select  Enter: choose",-1);
    AW_UITextBox(26,170,268,14,"Esc: cancel",-1);
    AW_UISmallEnd();return 1;
}
/* aw_debug_torch.c: the player leaves the census office (the opening hands over control). */
void (*aw_scene_census_exit)(void);
/* Object state (v0.0.51, aw_mwhost.c sets it; NULL without the scripts): 1 when a script that reads OnActivate
 * takes the use of the object REFERENCE (the original's rule); the door then waits for the script's Activate. */
int (*aw_scene_intercept)(unsigned reference);
static int use_link(int i);
int AW_SceneUse(void) {
    int i;
    if(AW_PlayerDead())return 1;   /* dead: nothing is used (the key is spent) */
    i=0;if(pending || door_ready)return 1;if(travel_use())return 1;if(!npc_hint() && (AW_InventoryUse() || AW_HarvestUse()))return 1;i=aimed_door();
    if(i<0)return aw_hinged_use?aw_hinged_use():0;   /* an ordinary hinged door (aw_hinged_door.c), else nothing here */
    if(aw_scene_intercept && aw_scene_intercept(links[i].reference))return 1;
    return use_link(i);
}
/* A script's Activate on a load door of this map (aw_mwhost.c): the door's own use, as if the player used it. 0 when
 * REFERENCE is no door here. */
int AW_SceneActivate(unsigned reference) {
    int i;
    if(AW_PlayerDead() || pending || door_ready)return 0;
    /* the table of the frame the player stands in, not the one read last (DOOR-BANK-STREAMED-FRAME-51) */
    read_links_for(door_scene());
    for(i=0;i<count;i++)if(links[i].reference==reference && door_in_frame(&links[i]))return use_link(i);
    return 0;
}
static int use_link(int i) {
    float duration;char path[40];
    if(!AW_StoryDoor(links[i].reference)){AW_UISubtitle("",links[i].reference==119513?"Finish registration and leave through the courtyard.":links[i].reference==113889?"Check the barrel beside the door first.":"Ask the captain about your duties first.",4);return 1;}
    if(AW_StoryRestricted() && !strcmp(links[i].target,"census") && aw_story.stage<AW_STAGE_OFFICE){AW_UISubtitle("","Speak to the dock guard first.",4);return 1;}
    /* a locked load door (DEBUG-GOD-LOCKED-DOORS-51): the key or god mode goes through, else the LockedDoor sound */
    if(aw_load_door_lock && aw_load_door_lock(links[i].reference,1))return 1;
    if(!map_valid(links[i].target) || AW_SceneMapSize(links[i].target,path,sizeof(path))<0){
        /* A quick test build without interiors (aw_excluded.c): a friendly line, not a repair message. */
        if(AW_ContentExcludedSay("interiors",1)){AW_UISubtitle("","Area unavailable in this quick test build.",3);return 1;}
        AW_UISubtitle("",AW_MiniwindActive()?AREA_UNAVAILABLE:"Interior not found.",3);return 1;
    }
    if(AW_SceneRoomRefuse(links[i].target))return 1;   /* a CHIM room this start's Fast RAM cannot hold: nothing loads */
    if(AW_StoryRestricted() && links[i].reference==119659 && AW_StoryTransition(AW_STAGE_RELEASED) && aw_scene_census_exit)
        aw_scene_census_exit();
    duration=AW_DoorSound(links[i].reference,0);
    if(duration>0){
        opening_door=links[i];door_ready=realtime+(duration>1?1:duration);
    }else {door_close=links[i].reference;load_scene(&links[i],0);}
    return 1;
}
/* Identity remains visible during speech; cooldown only controls playback. */
static const char *npc_hint(void)
{
    edict_t *e;eval_t *v;
    e=npc_target();if(!e)return NULL;
    v=GetEdictFieldValue(e,"aw_intro_role");if(v && v->_float)return NULL;
    return pr_strings+e->v.netname;
}
/* npc_interaction_layout_template_001: Morrowind name, console action below. */
void AW_SceneDraw(void) {
    int i,y,w,cw,npc=0;char line[80];edict_t *driver;const char *name=NULL,*action=NULL;extern int scr_copyeverything;
    if(!AW_UISpeakerAtRight() || target_style.value!=2)AW_UIObjectName(AW_SceneTargetName(),(int)target_style.value);
    if(key_dest!=key_game || pending || AW_IntroUse() || AW_PlayerDead() || !sv.active ||
       svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected ||
       svs.clients[0].edict->v.movetype!=MOVETYPE_WALK)return;
    driver=travel_target();
    if(driver){name=pr_strings+driver->v.netname;action="E: Talk";npc=1;}
    else if(!npc_hint() && ((name=AW_InventoryHint())!=NULL || (name=AW_HarvestHint())!=NULL)){action="E: Pick";npc=1;}
    else if(!AW_OpeningHint(&name,&action)){
        i=aimed_door();
        if(i>=0){
            name=links[i].label[0]?links[i].label:!strcmp(links[i].target,"seyda")?"Seyda Neen":"Imperial Prison Ship";
            action=!AW_StoryDoor(links[i].reference)?"Locked - finish duties":
                AW_StoryRestricted() && !strcmp(links[i].target,"census") && aw_story.stage<AW_STAGE_OFFICE?"Speak to dock guard":
                aw_load_door_lock && aw_load_door_lock(links[i].reference,0)?"Locked":
                !map_valid(links[i].target)?(AW_ContentExcluded("interiors")?"Area unavailable":"Interior unavailable"):"Enter: E";
        }else if(aw_hinged_hint && aw_hinged_hint(&name,&action)){
        }else{ name=npc_hint();if(name){
            eval_t *voice;edict_t *target=npc_target();npc=1;
            voice=target?GetEdictFieldValue(target,"aw_voice"):NULL;
            /* TALK-PROMPT-RULES: the name stays; the talk option only when the actor can be talked to (aw_talk.c,
             * the same rule as E) */
            if(aw_can_talk?target && aw_can_talk(target):voice && voice->string && pr_strings[voice->string])
                action="E: Talk";
        } }
    }
    if(!name)return;
    y=r_refdef.vrect.y+r_refdef.vrect.height;
    if((int)vid.height-y<20+AW_ConsoleCharHeight())return;
    if(!npc && (!AW_UISpeakerAtRight() || label_style.value!=2))AW_UIObjectName(name,(int)label_style.value);
    if(!action)return;
    sprintf(line,"(%s)",action);cw=AW_ConsoleCharWidth();w=strlen(line)*cw;
    for(i=0;line[i];i++)AW_ConsoleCharacter(vid.width-w-6+i*cw,y+19,(unsigned char)line[i]);
    scr_copyeverything=1;
}
static void door_status(void) {
    int i;vec3_t eye,local,shift,forward,right,up,hit,delta;trace_t tr;edict_t *p;
    if(!sv.active)return;
    read_links_for(door_scene());door_shift(shift);p=svs.clients[0].edict;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);VectorSubtract(eye,shift,local);AngleVectors(cl.viewangles,forward,right,up);
    Con_Printf("Doors %ld of %s / aimed %ld / eye %ld %ld %ld / pitch %ld\n",(long)count,door_scene(),
        (long)aimed_door(),(long)eye[0],(long)eye[1],(long)eye[2],(long)cl.viewangles[0]);
    for(i=0;i<count;i++)if(!strcmp(door_scene(),links[i].source)) {
        if(!door_hit(&links[i],local,forward,hit)){Con_Printf("Door %ld outside aim/reach\n",(long)i);continue;}
        VectorAdd(hit,shift,hit);
        VectorSubtract(hit,eye,delta);tr=SV_Move(eye,vec3_origin,vec3_origin,hit,MOVE_NOMONSTERS,p);
        Con_Printf("Door %ld hit %ld %ld %ld distance100 %ld clear1000 %ld solid %ld\n",
            (long)i,(long)hit[0],(long)hit[1],(long)hit[2],(long)(Length(delta)*100),
            (long)(tr.fraction*1000),(long)tr.startsolid);
    }
}
/* Narrow interior landings need a local floor test, not the exterior's wide
 * four-direction square. Source door destinations may start above their floor;
 * allow a bounded downward search when the standing head intersects a hatch. */
/* The standing-spot search shared by arrivals and dbg unstuck; the same rule as
 * tools/arrival_spot.py, which checks every town arrival at build time. A spot
 * needs a walkable floor, a clear standing hull and dry feet (never water). */
static int standing_spot(edict_t *p,const vec3_t preferred,vec3_t point) {
    vec3_t top,bottom,feet;trace_t tr;int i,drop;
    static int offsets[9][2]={{0,0},{16,0},{-16,0},{0,16},{0,-16},{16,16},{-16,16},{16,-16},{-16,-16}};
    for(drop=0;drop<=64;drop+=8)for(i=0;i<9;i++) {
        VectorCopy(preferred,top);top[0]+=offsets[i][0];top[1]+=offsets[i][1];top[2]+=8-drop;
        VectorCopy(top,bottom);bottom[2]-=32;
        tr=SV_Move(top,p->v.mins,p->v.maxs,bottom,MOVE_NORMAL,p);
        if(tr.startsolid || tr.allsolid || tr.fraction==1 || tr.plane.normal[2]<AW_WALKABLE_Z)continue;
        VectorCopy(tr.endpos,point);point[2]+=.25f;
        tr=SV_Move(point,p->v.mins,p->v.maxs,point,MOVE_NORMAL,p);
        if(tr.startsolid || tr.allsolid)continue;
        VectorCopy(point,feet);feet[2]+=p->v.mins[2]+1;
        if(SV_PointContents(feet)!=CONTENTS_EMPTY)continue;
        return 1;
    }
    return 0;
}
static void install_spot(edict_t *p,const vec3_t point) {
    VectorCopy(point,p->v.origin);VectorCopy(point,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
    p->v.flags=(int)p->v.flags&~FL_ONGROUND;SV_LinkEdict(p,false);
}
int AW_InteriorPlace(edict_t *p,vec3_t preferred) {
    vec3_t point;
    if(standing_spot(p,preferred,point)) {
        install_spot(p,point);
        Con_Printf("Interior spawn: %ld %ld %ld\n",(long)point[0],(long)point[1],(long)point[2]);return 1;
    }
    Con_Printf("Interior spawn blocked; use dbg noclip to inspect.\n");return 0;
}
/* Debug recovery uses CHIM's checked arrival floor, after loading its ring.
 * A refused destination restores collision residency around the unchanged player. */
int AW_RecoverPlace(edict_t *p,vec3_t preferred) {
    if(Chim_Active()) {
        if(aw_chim_spawn)aw_chim_spawn(preferred);
        if(AW_InteriorPlace(p,preferred))return 1;
        if(aw_chim_spawn)aw_chim_spawn(p->v.origin);
        return 0;
    }
    if(AW_Interior())return AW_InteriorPlace(p,preferred);
    return AW_PlacePlayer(p,preferred);
}
/* dbg unstuck: the nearest clear standing spot below or beside the player
 * (then one storey up); never into a wall or water, otherwise nothing moves. */
int AW_Unstuck(edict_t *p) {
    vec3_t point,above;
    if(!p)return 0;
    VectorCopy(p->v.origin,above);above[2]+=32;
    if(!standing_spot(p,p->v.origin,point) && !standing_spot(p,above,point)) {
        Con_Printf("No clear standing spot near here; fly clear in noclip or use dbg recover.\n");return 0;
    }
    install_spot(p,point);p->v.movetype=MOVETYPE_WALK;noclip_anglehack=false;
    Con_Printf("Unstuck: %ld %ld %ld\n",(long)point[0],(long)point[1],(long)point[2]);return 1;
}
/* A scene arrival tries the requested point, then the scene's own spawn point
 * (the town default), then the highest clear floor at the requested XY (a map
 * teleport tries that first). If all fail the player stays at the spawn point,
 * which is also the stuck-recovery anchor: never the frame origin under the
 * sea (VIVEC-ARENA-TP-ARRIVAL-32). */
static int arrival_place(edict_t *p,const vec3_t arrival,int jump) {
    vec3_t spawn,point;
    VectorCopy(p->v.origin,spawn);
    if(jump && AW_MapPlace(p,arrival))return 1;
    if(standing_spot(p,arrival,point) ||
       ((spawn[0]!=arrival[0] || spawn[1]!=arrival[1] || spawn[2]!=arrival[2]) && standing_spot(p,spawn,point))) {
        install_spot(p,point);
        Con_Printf("Interior spawn: %ld %ld %ld\n",(long)point[0],(long)point[1],(long)point[2]);return 1;
    }
    if(!jump && AW_MapPlace(p,arrival))return 1;
    install_spot(p,spawn);
    Con_Printf("Arrival blocked: staying at the scene spawn; use dbg unstuck or dbg noclip.\n");return 0;
}
/* An explicit debug scene restart owns no old door/cell arrival or voice tail. */
void AW_SceneCancelTransition(void) {
    pending=region_crossing=map_jump=crossing_view_ready=shroompicker_view=0;
    door_ready=0;door_close=0;S_CancelSceneVoice();
    memset(&hand_snapshot,0,sizeof(hand_snapshot));hand_clock_ready=0;
    AW_TorchResetAnimation();
}
void AW_SceneSignon(void) {
    if(shroompicker_view==2){
        shroompicker_view=0;
        if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict &&
           cls.state==ca_connected && !cls.demoplayback && cls.signon==SIGNONS &&
           !strcmp(sv.name,next.target)){
            edict_t *p=svs.clients[0].edict;
            /* Apply after signon, not as a queued aw_aim that map loading can
             * consume too early. Keep the exact tested downward viewing angle. */
            cl.viewangles[0]=shroompicker_pitch;cl.viewangles[1]=shroompicker_yaw;cl.viewangles[2]=0;
            VectorCopy(cl.viewangles,p->v.angles);VectorCopy(cl.viewangles,p->v.v_angle);
            V_StopPitchDrift();
        }
    }
    if(hand_clock_ready){
        hand_clock_ready=0;
        if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict &&
           cls.state==ca_connected && !cls.demoplayback && cls.signon==SIGNONS &&
           !strcmp(sv.name,next.target))AW_TorchRestoreAnimation(hand_torch_time);
        else AW_TorchResetAnimation();
    }
    if(!crossing_view_ready)return;
    crossing_view_ready=0;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict ||
       cls.state!=ca_connected || cls.demoplayback || cls.signon!=SIGNONS ||
       strcmp(sv.name,next.target)){S_CancelSceneVoice();return;}
    VectorCopy(crossing_angles,cl.viewangles);
    cl.nodrift=crossing_nodrift;cl.pitchvel=crossing_pitchvel;
    cl.driftmove=crossing_driftmove;cl.laststop=cl.time+crossing_laststop;
    S_EndSceneVoice();
}
/* CHIM: the chunk ring around the arrival point is loaded before the
 * clearance search (chim/chim_world.c sets it only when its data exists). */
void (*aw_chim_spawn)(vec3_t);
/* Type 1 cell crossings (CHIM's window of region frames, "chim crossing 1";
 * docs/chim/CELL_CROSSINGS.md): a crossing between two region frames the
 * window holds streams instead of loading the next map. The running map keeps
 * its name and its coordinates (the session's); the frame the player stands
 * in is the logical scene: its region map name and the offset from its own
 * coordinates to the session's. Every other crossing (towns, doors, dbg tp,
 * a frame the window does not hold) changes the level as before. */
int (*aw_chim_cross)(const float *origin,int *cx,int *cy);
int (*aw_chim_recentre)(int cx,int cy,const float *d,int apply);
static char logical_map[16];
static vec3_t logical_offset;
static int logical_used;		/* a streamed crossing since the map started */
/* The scene the player stands in: the logical frame after a streamed
 * crossing, else the running map (aw_remote.c's state file). */
const char *AW_SceneName(void){return logical_map[0]?logical_map:sv.active?sv.name:"none";}
static const char *door_scene(void){return logical_map[0]?logical_map:sv.name;}
static void door_shift(vec3_t shift){
    if(logical_map[0]){VectorCopy(logical_offset,shift);}
    else {VectorCopy(vec3_origin,shift);}
}
static int door_in_frame(const aw_scene_link_t *r){return !logical_map[0] || !strcmp(logical_map,r->source);}
/* The walk log's map column (aw_profile.c) after a streamed crossing:
 * maps/<scene>; NULL: the client's world model as before. */
const char *AW_SceneWalkModel(void){
    static char path[MAX_QPATH+8];
    if(!logical_used || !sv.active)return NULL;
    sprintf(path,"maps/%s",AW_SceneName());return path;
}
/* A recentre ("chim crossing recentre 1", a test setting; design note weak
 * point 5): the server's and the client's positions move by d first
 * (aw_debug.c AW_SessionShift, set by the engine at start-up), then CHIM's own
 * (aw_chim_recentre). NULL: no recentre. */
void (*aw_session_shift)(const float *d);
static int world_destination(const float *origin,char *target,float *arrival){
    float local[3];int k;
    for(k=0;k<3;k++)local[k]=origin[k]-logical_offset[k];
    return AW_WorldDestination(logical_map[0]?logical_map:sv.name,local,target,arrival);
}
static int stream_cross(edict_t *p,aw_scene_link_t *r){
    int cx,cy,k,how,moved=0;double t0=Sys_FloatTime();float d[3];
    if(!aw_chim_cross || AW_TerrainId(r->target)<0 || !(how=aw_chim_cross(p->v.origin,&cx,&cy)))return 0;
    copy_name(logical_map,sizeof(logical_map),r->target);logical_used=1;
    for(k=0;k<3;k++)logical_offset[k]=p->v.origin[k]-r->arrival[k];
    VectorCopy(logical_offset,d);d[2]=0;
    if(how==2 && aw_session_shift && aw_chim_recentre && aw_chim_recentre(cx,cy,d,0)){
        /* The entered frame's coordinates become the session's (CHIM agreed on the offset): the
         * map's name follows (saves, doors and the crossing checks read its coordinates from here on). */
        aw_session_shift(d);
        if((moved=aw_chim_recentre(cx,cy,d,1))!=0){
            copy_name(sv.name,sizeof(sv.name),r->target);
            logical_map[0]=0;VectorCopy(vec3_origin,logical_offset);
        }
    }
    Con_Printf("Scene ready: %s, 0 ms, streamed crossing (type 1%s), CHIM frame %ld %ld, %ld us\n",r->target,
        moved?", recentred":"",(long)cx,(long)cy,(long)((Sys_FloatTime()-t0)*1e6));
    return 1;
}
void AW_SceneSpawn(edict_t *p) {
    int placed=0;float eye;
    area_last_ok=0;frame_last_ok=0;frame_refused[0]=frame_mark_map[0]=0;
    logical_map[0]=0;VectorCopy(vec3_origin,logical_offset);logical_used=0;
    /* Quake's stuck recovery returns to oldorigin, which a fresh client edict
     * leaves at the frame origin; anchor it at the scene spawn instead. */
    VectorCopy(p->v.origin,p->v.oldorigin);
    if(aw_chim_spawn)aw_chim_spawn(pending && !strcmp(sv.name,next.target)?next.arrival:p->v.origin);
    if(region_crossing && (!pending || strcmp(sv.name,next.target)))S_CancelSceneVoice();
    crossing_view_ready=0;hand_clock_ready=0;door_ready=0;
    if(!region_crossing)AW_UISubtitle("","",0);
    if(pending && !strcmp(sv.name,next.target)) {
        if(map_jump){
            extern const char *aw_map_place_failure;
            /* 3: a camera mark on its map (AW_SceneShot): the exact point, noclip. */
            if(map_jump==3){
                VectorCopy(next.arrival,p->v.origin);VectorCopy(next.arrival,p->v.oldorigin);
                VectorCopy(vec3_origin,p->v.velocity);SV_LinkEdict(p,false);placed=1;
            }else
            placed=(map_jump==2 && AW_MapPlaceBelow(p,next.arrival)) || arrival_place(p,next.arrival,1);
            /* Said when the player did not land at the asked XY (the fallbacks
             * use the scene spawn), with why the map placement failed. */
            if(placed && (fabs(p->v.origin[0]-next.arrival[0])>48 || fabs(p->v.origin[1]-next.arrival[1])>48))
                Con_Printf("Debug teleport: %s at %ld %ld (map %s); placed at %ld %ld %ld instead.\n",
                    (char *)(aw_map_place_failure[0]?aw_map_place_failure:"no standing spot"),(long)next.arrival[0],(long)next.arrival[1],
                    sv.name,(long)p->v.origin[0],(long)p->v.origin[1],(long)p->v.origin[2]);
            if(!placed){
                Con_Printf("Debug teleport target has no clear standing surface; using scene spawn.\n");
                AW_UISubtitle("DEBUG TELEPORT","Target blocked; using scene spawn.",5);
            }
            p->v.movetype=crossing_movetype==MOVETYPE_NOCLIP?MOVETYPE_NOCLIP:MOVETYPE_WALK;
            noclip_anglehack=p->v.movetype==MOVETYPE_NOCLIP;
            map_jump=0;
        }else if(region_crossing){
            VectorCopy(next.arrival,p->v.origin);VectorCopy(next.arrival,p->v.oldorigin);
            VectorCopy(crossing_angles,p->v.angles);VectorCopy(crossing_velocity,p->v.velocity);
            p->v.movetype=crossing_movetype;p->v.fixangle=1;SV_LinkEdict(p,false);placed=1;
        }else placed=arrival_place(p,next.arrival,0);
        p->v.angles[0]=0;p->v.angles[1]=next.yaw;p->v.angles[2]=0;p->v.fixangle=1;
        shroompicker_view=shroompicker_view && placed?2:0;
        if(shroompicker_view){
            p->v.angles[0]=shroompicker_pitch;p->v.angles[1]=shroompicker_yaw;
            VectorCopy(p->v.angles,p->v.v_angle);
        }
        if(region_crossing){
            VectorCopy(crossing_angles,p->v.angles);
            VectorCopy(crossing_angles,p->v.v_angle);
            crossing_view_ready=1;
        }
        p->v.health=health;
        /* Host_Spawn_f serializes weapon model/frame immediately after this
         * callback, before the first visible arrival or QC player tick. */
        if(AW_HandSnapshotRestore(&hand_snapshot,p,sv.time))hand_clock_ready=1;
        else {AW_TorchResetAnimation();Con_Printf("Hand transition state not restored.\n");}
        memset(&hand_snapshot,0,sizeof(hand_snapshot));
        Con_Printf("Scene ready: %s, %ld ms, %ld hunk bytes, arrival %s\n",sv.name,
            (long)((Sys_FloatTime()-started)*1000),(long)(Hunk_LowMark()+Hunk_HighMark()),placed?"checked":"blocked");
        AW_MusicSceneEvent("scene-enter");pending=0;AW_StreamTransitionReady();
    } else {
        pending=shroompicker_view=0;memset(&hand_snapshot,0,sizeof(hand_snapshot));AW_TorchResetAnimation();
        if(AW_Interior() || AW_TownFlag(sv.name,AW_TOWN_GROUND_PLACE) || AW_TerrainId(sv.name)>=0)AW_InteriorPlace(p,p->v.origin);
        else AW_PlacePlayer(p,p->v.origin);
    }
    AW_IntroSpawn();AW_OpeningSpawn();if(aw_hinged_spawn)aw_hinged_spawn();AW_SaveSpawn();AW_InventorySpawn();if(!harvest_follow(p,1))AW_HarvestSpawn();
    if(aw_combat_scene)aw_combat_scene();
    AW_GallerySpawn(p);if(aw_companion_scene)aw_companion_scene(p);region_crossing=map_jump=0;
    if(AW_CharacterLoad() && (eye=AW_CharacterEyeHeight())>0)p->v.view_ofs[2]=eye+p->v.mins[2];
    /* The partial-area build's notice, in the game's own message box, once the
     * quick start has arrived (the build's data file, aw_miniwind.c). */
    if(quick_screen){
        quick_screen=0;
        if(AW_QuickCharOpen(AW_QC_ALL|AW_QC_VOICE,quick_screen_done))quick_notice=0;
    }
    if(quick_notice && AW_MiniwindActive()){
        quick_notice=0;AW_UISubtitle(AW_Miniwind()->title,AW_Miniwind()->features,15);
        miniwind_boot();
    }
    AW_HeapAuditReport(sv.worldmodel?sv.worldmodel->name:sv.name);
}
void AW_SceneTick(void) {
    aw_scene_link_t r;edict_t *p;
    AW_NPCFloorRetry();
    if(!pending && aw_hinged_tick)aw_hinged_tick(host_frametime);   /* nothing unless a door turns */
    if(!pending && sv.active && cls.state==ca_connected && cls.signon==SIGNONS &&
       key_dest==key_game && svs.maxclients==1 && svs.clients && (p=svs.clients[0].edict))
        AW_StreamTick(AW_CellChangeMethod()==2?AW_RegionAhead(p->v.origin,p->v.velocity,
            intro_docks_variant.value==2 && aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE,AW_StreamLookahead()):NULL);
    if(door_ready){
        if(!sv.active || strcmp(door_scene(),opening_door.source)){door_ready=0;return;}
        if(realtime>=door_ready){door_ready=0;door_close=opening_door.reference;load_scene(&opening_door,0);}
        return;
    }
    if(door_close && !pending && cls.state==ca_connected && cls.signon==SIGNONS){
        AW_DoorSound(door_close,1);door_close=0;
    }
    if(pending || !sv.active || cls.state!=ca_connected || cls.signon!=SIGNONS || key_dest!=key_game ||
       svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict) ||
       p->v.health<=0 || (p->v.movetype!=MOVETYPE_WALK && p->v.movetype!=MOVETYPE_NOCLIP))return;
    harvest_follow(p,0);
    if(area_hold(p))return;
    memset(&r,0,sizeof(r));
    if(AW_SectionDestination(sv.name,p->v.origin,r.target)){
        VectorCopy(p->v.origin,r.arrival);
    }else if(AW_StoryRestricted() || !world_destination(p->v.origin,r.target,r.arrival)){
        VectorCopy(p->v.origin,frame_last);frame_last_ok=1;   /* inside the scene: where a refused crossing returns */
        if(!AW_RegionCrossing(p->v.origin,intro_docks_variant.value==2 && aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE))return;
        copy_name(r.target,sizeof(r.target),sv.name);VectorCopy(p->v.origin,r.arrival);
    }else if(AW_SceneFrameRefuse(p,r.target))return;   /* a CHIM frame this start's Fast RAM cannot hold */
    else if(stream_cross(p,&r))return;
    r.yaw=p->v.angles[1];
    /* The displayed local view can differ from the last rounded movement
     * packet. Preserve it and its drift policy across the client-state reset. */
    VectorCopy(cl.viewangles,crossing_angles);
    crossing_nodrift=cl.nodrift;crossing_pitchvel=cl.pitchvel;
    crossing_driftmove=cl.driftmove;crossing_laststop=cl.laststop-cl.time;
    VectorCopy(p->v.velocity,crossing_velocity);crossing_movetype=p->v.movetype;
    region_crossing=1;
    load_scene(&r,1);
    if(!pending)region_crossing=0;
}
/* A partial-area build holds the player inside the town's CHIM frame: past
 * the union of its region cores (the frame's edge, AW_RegionAt) lies an area
 * the build does not hold. The player stays at the last spot 32 units clear of
 * the edge and the message box says so. Normal builds, legacy region maps,
 * interiors and noclip are never held. Returns 1 while holding. */
static int area_inside(const float *o) {
    static const float step[4][2]={{32,0},{-32,0},{0,32},{0,-32}};float q[3];int i;
    for(i=0;i<4;i++){
        q[0]=o[0]+step[i][0];q[1]=o[1]+step[i][1];q[2]=o[2];
        if(AW_RegionAt(q,-1,NULL,0)==-1)return 0;
    }
    return 1;
}
static int area_hold(edict_t *p) {
    if(!AW_MiniwindActive() || p->v.movetype!=MOVETYPE_WALK || AW_RegionAt(p->v.origin,-1,NULL,0)==-2)return 0;
    if(area_inside(p->v.origin)){VectorCopy(p->v.origin,area_last);area_last_ok=1;return 0;}
    if(area_last_ok){
        VectorCopy(area_last,p->v.origin);VectorCopy(area_last,p->v.oldorigin);
        p->v.velocity[0]=p->v.velocity[1]=0;SV_LinkEdict(p,false);
    }
    if(realtime>=area_said+3 || realtime<area_said){area_said=realtime;AW_UISubtitle("",AREA_UNAVAILABLE,3);}
    return 1;
}
/* Help line built from the town table, so new teleport towns appear without
 * editing this text (DEBUG-TP-TOWN-NAMES-32). */
static void scene_help(void) {
    char names[256];
    /* Only what this disk has: a pure-CHIM disk offers its CHIM towns. */
    if(AW_TeleportDestinations(names,sizeof(names)))
        Con_Printf("During play: dbg tp %s/<map name>, dbg tp X Y [Z] (original coordinates); dbg tp opens the menu.\n",names);
    else Con_Printf("During play: dbg tp <map name> or dbg tp X Y [Z] (original coordinates); no town on this disk.\n");
}
/* dbg tp NAME for a place no town name reaches: teleport-names.txt in the game data (config/teleport-names.txt,
 * checked by the builder), one "name|map|x y z|yaw|label" per line; the arrival is where the game's own door into the
 * place puts the player. 1 with R filled when NAME is listed and its map is valid. */
static int named_place(const char *name,aw_scene_link_t *r) {
    FILE *f;char line[192],key[24],map[16],label[96];float x,y,z,yaw;int found=0;
    COM_FOpenFile("teleport-names.txt",&f);
    if(!f)return 0;
    if(!fgets(line,sizeof(line),f) || (strcmp(line,"AWTN1\n") && strcmp(line,"AWTN1\r\n"))){fclose(f);return 0;}
    while(!found && fgets(line,sizeof(line),f)) {
        if(line[0]=='#')continue;
        if(Q_sscanf(line,"%23[^|]|%15[^|]|%f %f %f|%f|%95[^\r\n]",key,map,&x,&y,&z,&yaw,label)!=7)continue;
        if(Q_strcasecmp(key,(char *)name) || !map_valid(map))continue;
        memset(r,0,sizeof(*r));copy_name(r->target,sizeof(r->target),map);copy_name(r->label,sizeof(r->label),label);
        r->arrival[0]=x;r->arrival[1]=y;r->arrival[2]=z;r->yaw=yaw;found=1;
    }
    fclose(f);return found;
}
static void scene_command(void) {
    aw_scene_link_t r;const char *s=Cmd_Argv(1);char path[40];int i,size;
    if(!Q_strcasecmp((char *)s,"seydaneen") || !Q_strcasecmp((char *)s,"seyda") ||
       !Q_strcasecmp((char *)s,"town"))s="town";
    else if(!Q_strcasecmp((char *)s,"ship") || !Q_strcasecmp((char *)s,"prisonship"))s="ship";
    /* Short names (DEBUG-TP-TOWN-NAMES-32): "vivec" is the whole city when this disk holds it
     * (vivec_city, one CHIM frame), else the Arena canton; "arena" is the Arena canton. */
    else if(!Q_strcasecmp((char *)s,"vivec") && AW_TownFind("vivec_city")>=0 &&
            AW_SceneMapSize("vivec_city",NULL,0)>=124)s="vivec_city";
    else if((!Q_strcasecmp((char *)s,"vivec") || !Q_strcasecmp((char *)s,"arena")) &&
            AW_TownFind("vivec_arena")>=0)s="vivec_arena";
    else{
        for(i=0;i<AW_MAP_COUNT;i++)if(!Q_strcasecmp((char *)s,(char *)AW_MapName(i))){s=AW_MapName(i);break;}
        if(i==AW_MAP_COUNT)for(i=0;i<AW_TOWN_COUNT;i++)if(!Q_strcasecmp((char *)s,(char *)AW_Town(i)->name)){s=AW_Town(i)->name;break;}
    }
    /* A test build without a game yet (main menu, boot console): a town loads as the quick start. */
    if(!sv.active && Cmd_Argc()==2 && AW_MiniwindActive() && AW_TownFind(s)>=0 && (AW_Town(AW_TownFind(s))->flags&AW_TOWN_TELEPORT)){
        Cbuf_AddText((char *)va("aw_quick_start town %s\n",s));return;
    }
    if(!sv.active && Cmd_Argc()==2){
        Con_Printf("dbg tp needs a game running: New Game first%s.\n",AW_MiniwindActive()?", or aw_quick_start":"");return;
    }
    /* a named place (teleport-names.txt: dbg tp heartchamber) */
    if(sv.active && Cmd_Argc()==2 && strcmp(s,"ship") && strcmp(s,"town") && !map_valid(s) && named_place(s,&r)){
        if(AW_SceneMapSize(r.target,path,sizeof(path))<124){Con_Printf("Destination not on this disk: %s.\n",r.label);return;}
        door_ready=0;door_close=0;Con_Printf("%s\n",r.label);load_scene(&r,1);return;
    }
    if(!sv.active || Cmd_Argc()!=2 || (strcmp(s,"ship") && strcmp(s,"town") && !map_valid(s))) {
        if(sv.active && Cmd_Argc()==2)Con_Printf("Unknown destination: %s.\n",Cmd_Argv(1));
        scene_help();return;
    }
    door_ready=0;door_close=0;
    size=AW_SceneMapSize(!strcmp(s,"ship")?"prison":!strcmp(s,"town")?"seyda":s,path,sizeof(path));
    if(size<124){Con_Printf("Destination not on this disk: %s.\n",s);scene_help();return;}
    if(map_valid(s)){
        if(AW_TownFlag(s,AW_TOWN_TELEPORT)){
            memset(&r,0,sizeof(r));copy_name(r.target,sizeof(r.target),s);
            if(AW_TownArrival(s,0,r.arrival,&r.yaw)){
                if(!aw_character.valid || !aw_story.name[0]){
                    if(!AW_CharacterHors()){Con_Printf("Hors preset: character catalogue unavailable.\n");return;}
                    AW_SaveReset();svs.clients[0].edict->v.health=aw_character.current[0];
                    svs.clients[0].edict->v.movetype=MOVETYPE_WALK;noclip_anglehack=false;
                    Con_Printf("Created Hors: Nord, Barbarian, The Steed; after Census.\n");
                }
                load_scene(&r,1);
            }
            else Con_Printf("%s conversion not found.\n",AW_Town(AW_TownFind(s))->title);
            return;
        }
        /* Select the destination area's entrance catalogue. Appended Balmora
         * interior IDs must not fall back to Seyda's unrelated door bank; a
         * town interior uses its own town's bank. */
        i=AW_MapId(s)-AW_TOWN_INTERIOR_BASE;
        if(i>=0 && AW_TownInteriorTown(i)>=0)read_links_for(AW_Town(AW_TownInteriorTown(i))->name);
        else read_links_for(AW_MapId(s)>AW_MapId("balmora")?"balmora":"seyda");
        /* The catalogue's first Census entry is a separate upper doorway.
         * Debug arrival uses the inspected registration entrance from the pier. */
        if(!strcmp(s,"census"))for(i=0;i<count;i++)
            if(links[i].reference==113893 && !strcmp(links[i].target,s)){
                load_scene(&links[i],1);return;
            }
        for(i=0;i<count;i++)if(!strcmp(links[i].target,s)){load_scene(&links[i],1);return;}
        Con_Printf("No converted entrance to %s.\n",s);return;
    }
    memset(&r,0,sizeof(r));copy_name(r.target,sizeof(r.target),!strcmp(s,"ship")?"prison":"seyda");
    if(!strcmp(s,"ship")){r.arrival[1]=-35;r.arrival[2]=-4;r.yaw=90;}
    else {r.arrival[0]=0;r.arrival[1]=0;r.arrival[2]=64;r.yaw=90;}
    load_scene(&r,1);
}
static void hors_command(void) {
    aw_scene_link_t r;
    if(!sv.active || !svs.clients || pending || Cmd_Argc()!=2 || strcmp(Cmd_Argv(1),"0")){
        Con_Printf("During play: dbg aw hors 0 (restart after Census in Seyda Neen)\n");return;
    }
    if(!AW_CharacterHors()){Con_Printf("Hors preset: character catalogue unavailable.\n");return;}
    door_ready=0;door_close=0;
    AW_SaveReset();svs.clients[0].edict->v.health=aw_character.current[0];
    svs.clients[0].edict->v.movetype=MOVETYPE_WALK;noclip_anglehack=false;
    memset(&r,0,sizeof(r));copy_name(r.target,sizeof(r.target),"seyda");r.arrival[2]=64;r.yaw=90;
    Con_Printf("Created Hors: Nord, Barbarian, The Steed; after Census.\n");load_scene(&r,1);
}
static int teleport_coordinate(const char *text,float *result) {
    char *end;double value;const char *p;
    if(!text || !*text || strlen(text)>32)return 0;
    for(p=text;*p;p++)if(!((*p>='0' && *p<='9') || *p=='+' || *p=='-' ||
                         *p=='.' || *p=='e' || *p=='E'))return 0;
    errno=0;value=Q_strtod(text,&end);
    if(end==text || *end || errno==ERANGE || !isfinite(value) || fabs(value)>2000000)return 0;
    *result=(float)value;return isfinite(*result);
}
typedef struct {int slot,verified;unsigned reference;char map[16],label[96];float x,y,yaw,pitch;} shroompicker_spot_t;
static int shroompicker_line(char *line,shroompicker_spot_t *spot) {
    int end=0,i;size_t length=strlen(line);
    if(!length || line[length-1]!='\n')return 0;
    line[--length]=0;
    if(length && line[length-1]=='\r')line[--length]=0;
    if(Q_sscanf(line,"%d %d %u %15s %f %f %f %f %95[^\r\n]%n",&spot->slot,&spot->verified,
       &spot->reference,spot->map,&spot->x,&spot->y,&spot->yaw,&spot->pitch,spot->label,&end)!=9 ||
       end!=(int)length || spot->slot<1 || spot->slot>10 || spot->verified<0 || spot->verified>1 ||
       (!spot->reference && spot->slot!=1) || !map_valid(spot->map) ||
       !isfinite(spot->x) || !isfinite(spot->y) || fabs(spot->x)>2000000 || fabs(spot->y)>2000000 ||
       !isfinite(spot->yaw) || spot->yaw<0 || spot->yaw>=360 ||
       !isfinite(spot->pitch) || spot->pitch<-70 || spot->pitch>80)return 0;
    for(i=0;spot->label[i];i++)if((unsigned char)spot->label[i]<32)return 0;
    return 1;
}
static int shroompicker_getline(FILE *f,int *left,char *line,int capacity) {
    int c,i=0;
    while(*left>0 && i<capacity-1){
        c=fgetc(f);if(c==EOF)return 0;--*left;line[i++]=(char)c;
        if(c=='\n'){line[i]=0;return 1;}
    }
    return 0; /* An unterminated/oversized line cannot escape the member. */
}
static int shroompicker_read(int wanted,int list,shroompicker_spot_t *selected) {
    FILE *f=NULL;char line[256];shroompicker_spot_t row;int size,left,seen=0,ok=1;long start;
    size=COM_FOpenFile("shroompicker.txt",&f);
    if(!f || size<8 || size>4096){if(f)fclose(f);return 0;}
    start=ftell(f);left=size;
    if(start<0 || !shroompicker_getline(f,&left,line,sizeof(line)) ||
       (strcmp(line,"AWSP1\n") && strcmp(line,"AWSP1\r\n")))ok=0;
    while(ok && left>0){
        if(!shroompicker_getline(f,&left,line,sizeof(line)) || !shroompicker_line(line,&row) ||
           (seen&(1<<(row.slot-1)))){ok=0;break;}
        seen|=1<<(row.slot-1);if(row.slot==wanted)*selected=row;
    }
    if(ferror(f) || seen!=1023)ok=0;
    if(ok && list){
        left=size;
        if(fseek(f,start,SEEK_SET) || !shroompicker_getline(f,&left,line,sizeof(line)))ok=0;
        while(ok && left>0){
            if(!shroompicker_getline(f,&left,line,sizeof(line)) || !shroompicker_line(line,&row)){ok=0;break;}
            Con_Printf("%ld: %s [%s]\n",(long)row.slot,row.label,
                row.verified?"playtested":"source checked; native unverified");
        }
    }
    fclose(f);return ok;
}
static void shroompicker_command(void) {
    vec3_t source,arrival;char target[16];shroompicker_spot_t spot;int slot=1,list=0;
    if(Cmd_Argc()==2){
        const char *arg=Cmd_Argv(1);
        if(!strcmp(arg,"list"))list=1;
        else if(!strcmp(arg,"10"))slot=10;
        else if(arg[0]>='1' && arg[0]<='9' && !arg[1])slot=arg[0]-'0';
        else slot=0;
    }
    if(Cmd_Argc()>2 || !slot){Con_Printf("Usage: dbg shroompicker [1-10|list]\n");return;}
    if(!shroompicker_read(slot,list,&spot)){Con_Printf("Mushroom destinations missing or invalid: shroompicker.txt.\n");return;}
    if(list)return;
    source[0]=spot.x;source[1]=spot.y;source[2]=0;
    if(!AW_WorldMapTarget(source,target,arrival) || strcmp(target,spot.map)){
        Con_Printf("Mushroom destination map is missing or its source route changed.\n");return;
    }
    /* Use the normal checked global-XY route. Never reset the character,
     * inventory, harvest seed or picked facts just to make a test plant appear. */
    if(!AW_MapTeleport(source)){
        Con_Printf("Mushroom test teleport unavailable; start unrestricted play first.\n");return;
    }
    next.yaw=spot.yaw;shroompicker_pitch=spot.pitch;shroompicker_yaw=spot.yaw;shroompicker_view=1;
    Con_Printf("Mushroom spot %ld: %s [%s]. Aim and E: Pick.\n",(long)slot,spot.label,
        spot.verified?"playtested":"source checked; native unverified");
    Con_Printf("Standing surface checked on arrival. Picked/empty plants remain absent; dbg shroomtracker counts picks.\n");
}
/* dbg tp mark / dbg tp marker: the user map marker (the map screen's right click, MAP-MARKER-29, saved in the
 * globals under aw_worldui.c's keys, original global X Y), by the same route as dbg tp X Y: the map that
 * holds the point (a CHIM frame on a CHIM disk) and the highest standing surface there. 0: no marker. */
int AW_SceneMapMarker(float *source) {
    if(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:map:marker:ready")!=1)return 0;
    source[0]=(float)AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:map:marker:x");
    source[1]=(float)AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:map:marker:y");
    source[2]=0;return 1;
}
static void roulette_command(int first);
static void teleport_command(void) {
    vec3_t source;
    if(Cmd_Argc()>=2 && !strcmp(Cmd_Argv(1),"roulette")){roulette_command(2);return;}   /* dbg door roulette [SEED] */
    if(Cmd_Argc()==2 && (!strcmp(Cmd_Argv(1),"mark") || !strcmp(Cmd_Argv(1),"marker"))) {
        if(!AW_SceneMapMarker(source)){Con_Printf("no map marker set\n");return;}
        if(!AW_MapTeleportAt(source,0))
            Con_Printf("Map marker teleport unavailable (no map on this disk holds %ld %ld); player state unchanged.\n",
                (long)source[0],(long)source[1]);
        else Con_Printf("Teleport to the map marker: %ld %ld.\n",(long)source[0],(long)source[1]);
        return;
    }
    if(Cmd_Argc()==2 && (!strcmp(Cmd_Argv(1),"tel_uvirith") || !strcmp(Cmd_Argv(1),"teluvirith"))) {
        /* Recorded exterior approach; reuse the checked coordinate route and
         * standing-surface placement rather than resetting the character. */
        source[0]=85676;source[1]=11440;source[2]=1852;
        if(!AW_MapTeleportAt(source,1))
            Con_Printf("Tel Uvirith teleport unavailable; start play on a disk containing this location.\n");
        return;
    }
    if(Cmd_Argc()==3 || Cmd_Argc()==4) {
        if(!teleport_coordinate(Cmd_Argv(1),&source[0]) ||
           !teleport_coordinate(Cmd_Argv(2),&source[1]) ||
           (Cmd_Argc()==4 && !teleport_coordinate(Cmd_Argv(3),&source[2]))) {
            Con_Printf("Usage: dbg tp X Y [Z] (original Morrowind global coordinates)\n");return;
        }
        if(Cmd_Argc()==3)source[2]=0;
        if(!AW_MapTeleportAt(source,Cmd_Argc()==4))
            Con_Printf("Coordinate teleport unavailable (no map on this disk holds that point); player state unchanged.\n");
        return;
    }
    if(Cmd_Argc()>4) {
        Con_Printf("Usage: dbg tp X Y [Z], dbg tp <name>, or dbg tp map\n");return;
    }

    if(Cmd_Argc()==1 && sv.active){Cbuf_InsertText("aw_scene_menu\n");return;}
    scene_command();
}
/* dbg door roulette [SEED] (the maintainer, v0.0.53: random tests of interior loading): one random room of this
 * disk, loaded straight away at the room's own start (its info_player_start), the way a door loads it; the console
 * says which (its name, map id and cell number) and the seed, which repeats the same choice. The rooms are every
 * interior the engine names (aw_maps.h: the fixed rooms, the room maps, the town interiors, the room batches) whose
 * map is on this disk and has a start; one draw at a time, a room missing from the disk is drawn again. */
static int roulette_total(void){return AW_MAP_COUNT+AW_INTERIOR_MAP_COUNT+AW_TOWN_INTERIOR_COUNT+AW_ROOM_BATCH_COUNT;}
static const char *roulette_name(int k){
    if(k<AW_MAP_COUNT)return AW_TownFind(AW_MapName(k))>=0?"":AW_MapName(k);   /* a town is no room */
    k-=AW_MAP_COUNT;if(k<AW_INTERIOR_MAP_COUNT)return AW_InteriorMapName(k);
    k-=AW_INTERIOR_MAP_COUNT;if(k<AW_TOWN_INTERIOR_COUNT)return AW_TownInteriorName(k);
    return AW_RoomBatchName(k-AW_TOWN_INTERIOR_COUNT);
}
/* A key's value in one entity's text (START..END), copied into OUT; 0 without it. */
static int entity_value(const char *start,const char *end,const char *key,char *out,int size){
    const char *p=start,*q;int n;
    while((p=strstr(p,key))!=NULL && p<end){
        p+=strlen(key);while(*p==' ' || *p=='\t')p++;
        if(*p!='"')continue;
        q=strchr(++p,'"');if(!q || q>end)return 0;
        n=(int)(q-p);if(n>=size)n=size-1;
        memcpy(out,p,n);out[n]=0;return 1;
    }
    return 0;
}
/* Room NAME's start (its map's info_player_start: origin and angle) into R, its title (the worldspawn's
 * _aw_cell_id, else message, else NAME) and cell number (_aw_cell_int, -1 without); 0 when the map is not on this
 * disk or has no start. Reads the map's header and the start of its entity lump only. */
static int roulette_room(const char *name,aw_scene_link_t *r,char *title,int size,long *cell){
    static char text[2048];char path[MAX_QPATH+24],value[96];FILE *f=NULL;unsigned char h[12];long base,at,len;int n=0;
    const char *world_end,*start,*start_end;
    if(!name || !*name || !map_valid(name) || AW_SceneMapSize(name,path,sizeof(path))<124)return 0;
    if(COM_FOpenFile(path,&f)<0 || !f)return 0;
    base=ftell(f);
    if(fread(h,1,12,f)==12){
        at=(long)h[4]|((long)h[5]<<8)|((long)h[6]<<16)|((long)h[7]<<24);
        len=(long)h[8]|((long)h[9]<<8)|((long)h[10]<<16)|((long)h[11]<<24);
        if(at>=124 && len>0 && !fseek(f,base+at,SEEK_SET))
            n=(int)fread(text,1,len<(long)sizeof(text)-1?(size_t)len:sizeof(text)-1,f);
    }
    fclose(f);text[n<0?0:n]=0;
    if(!(world_end=strchr(text,'}')) || !(start=strstr(world_end,"\"info_player_start\"")))return 0;
    if(!(start_end=strchr(start,'}')))return 0;
    memset(r,0,sizeof(*r));copy_name(r->target,sizeof(r->target),name);
    if(!entity_value(start,start_end,"\"origin\"",value,sizeof(value)) ||
       Q_sscanf(value,"%f %f %f",&r->arrival[0],&r->arrival[1],&r->arrival[2])!=3 ||
       !(fabs(r->arrival[0])<32768 && fabs(r->arrival[1])<32768 && fabs(r->arrival[2])<32768))return 0;
    if(!entity_value(start,start_end,"\"angle\"",value,sizeof(value)) || Q_sscanf(value,"%f",&r->yaw)!=1 ||
       !(r->yaw>-36000 && r->yaw<36000))r->yaw=0;
    while(r->yaw<0)r->yaw+=360;
    while(r->yaw>=360)r->yaw-=360;
    if(!entity_value(text,world_end,"\"_aw_cell_id\"",title,size) && !entity_value(text,world_end,"\"message\"",title,size))
        copy_name(title,size,name);
    if(!entity_value(text,world_end,"\"_aw_cell_int\"",value,sizeof(value)) || Q_sscanf(value,"%ld",cell)!=1)*cell=-1;
    copy_name(r->label,sizeof(r->label),title);
    return 1;
}
/* A script's PositionCell of the player into a room (aw_mwhost.c, v0.0.54): room map MAP loaded the way a door loads
 * it, the player put at ARRIVAL (the map's own units, as a door's arrival) facing YAW. 0 when no game runs, a load is
 * pending, the story holds the player, or the map is not on this disk; the player is unchanged then. */
int AW_SceneLoadRoom(const char *map,const float *arrival,float yaw) {
    aw_scene_link_t r;edict_t *p;char path[MAX_QPATH+24];
    if(pending || !sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict) ||
       cls.state!=ca_connected || p->v.health<=0 || AW_StoryRestricted())return 0;
    if(!map || !*map || !map_valid(map) || AW_SceneMapSize(map,path,sizeof(path))<124)return 0;
    if(!(fabs(arrival[0])<32768 && fabs(arrival[1])<32768 && fabs(arrival[2])<32768))return 0;
    memset(&r,0,sizeof(r));copy_name(r.target,sizeof(r.target),map);VectorCopy(arrival,r.arrival);
    r.yaw=yaw;region_crossing=0;door_ready=0;door_close=0;crossing_movetype=p->v.movetype;
    load_scene(&r,1);
    return pending!=0;
}
/* FIRST: the argument index of the seed (aw_teleport roulette [SEED], routed from dbg door roulette by aw_console.c,
 * so the roulette needs no resident command of its own). */
static void roulette_command(int first){
    unsigned long seed=0,state;int total=roulette_total(),tries;aw_scene_link_t r;char title[96];long cell;
    const char *arg=Cmd_Argv(first),*p;
    if(Cmd_Argc()>first+1){Con_Printf("Usage: dbg door roulette [SEED] (a number; the same seed loads the same room)\n");return;}
    if(Cmd_Argc()==first+1){
        for(p=arg;*p;p++)if(*p<'0' || *p>'9' || p-arg>=10)break;
        if(*p || !*arg){Con_Printf("Usage: dbg door roulette [SEED] (a number; the same seed loads the same room)\n");return;}
        for(p=arg;*p;p++)seed=(seed*10+(unsigned long)(*p-'0'))&0xffffffffUL;
    }else seed=((unsigned long)(Sys_FloatTime()*1000.0)^(unsigned long)(realtime*7919.0))&0xffffffffUL;
    if(!sv.active || pending || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict){
        Con_Printf("dbg door roulette needs a game running: New Game first.\n");return;}
    state=seed;
    for(tries=0;tries<total*4;tries++){
        state=(state*1103515245UL+12345UL)&0xffffffffUL;
        if(roulette_room(roulette_name((int)((state>>8)%(unsigned long)total)),&r,title,sizeof(title),&cell)){
            door_ready=0;door_close=0;
            Con_Printf("Door roulette (seed %lu): %s [%s, cell %ld]\n",seed,title,r.target,cell);
            load_scene(&r,1);return;
        }
    }
    Con_Printf("Door roulette (seed %lu): no room of this disk found.\n",seed);
}
/* aw_quick_start [town] [NAME] | map MAP X Y Z YAW: a fresh game straight in a town
 * (default: the partial-area build's town or start line, aw_miniwind.c), as the
 * Hors preset dbg tp creates, at the town's directory arrival, placed as a door
 * arrival is; or on a map at a local point and heading (the start line's format).
 * A partial-area build runs it after the startup logo and for New Game; a normal
 * build with aw_skip_census runs it for New Game (Seyda Neen after the census).
 * With aw_skip_census the quick character screen opens on arrival, unless a test
 * already set the character (aw_quickchar_set). */
/* The build's ready-made character (a direct start's character line), else the Hors
 * preset; a character a test set with aw_quickchar_set is kept over either. */
static int quick_character(void) {
    char race[32],clas[32],birth[32],name[32],kept_name[32];int female,ok,scripted=AW_QuickCharScripted();
    aw_character_t kept;
    kept=aw_character;strcpy(kept_name,aw_story.name);
    if(AW_MiniwindActive() && AW_MiniwindCharacter(AW_Miniwind(),race,clas,birth,&female,name,sizeof(name)))
        ok=AW_CharacterPreset(race,clas,birth,female,name);
    else ok=AW_CharacterHors();
    if(ok && scripted){aw_character=kept;if(kept_name[0])strcpy(aw_story.name,kept_name);}
    return ok;
}
int AW_SceneStarting(void){return pending;}
static void quick_go(aw_scene_link_t *r,const char *title) {
    char command[48];
    if(AW_SceneEntryRefuse(r->target,r->arrival,1))return;   /* a start in a marked place: the main menu after ENTER */
    AW_SaveReset();AW_SceneCancelTransition();
    health=aw_character.current[0];next=*r;pending=1;started=Sys_FloatTime();
    quick_notice=1;
    quick_screen=AW_SkipCensus() && !AW_QuickCharScripted();
    IN_AWClearButtons();key_dest=key_game;
    Con_Printf("Quick start: %s as %s%s.\n",title,aw_story.name,quick_screen?"; quick character screen on arrival":"");
    sprintf(command,"map %s\n",r->target);Cbuf_AddText(command);
}
static void quick_start(void) {
    aw_scene_link_t r;const char *s="";int town,n=Cmd_Argc();aw_quick_start_t start;
    memset(&r,0,sizeof(r));memset(&start,0,sizeof(start));
    if(n==7 && !strcmp(Cmd_Argv(1),"map")){
        /* The start line's own format and checks (aw_miniwind.c AW_MiniwindStart). */
        aw_miniwind_t line;memset(&line,0,sizeof(line));
        if(snprintf(line.start,sizeof(line.start),"map %s %s %s %s %s",Cmd_Argv(2),Cmd_Argv(3),Cmd_Argv(4),
                    Cmd_Argv(5),Cmd_Argv(6))>=(int)sizeof(line.start) || !AW_MiniwindStart(&line,&start)){
            Con_Printf("Usage: aw_quick_start map MAP X Y Z YAW (local units, yaw 0..359)\n");return;
        }
    }
    /* A direct-start build's start line (tools/direct_start.py): a town, or a map at a spot
     * the builder checked (a door arrival, or the arrival search on its collision). */
    else if(n==1 && AW_MiniwindActive())AW_MiniwindStart(AW_Miniwind(),&start);
    if(start.kind==2){
        if(!map_valid(start.map) || AW_SceneMapSize(start.map,NULL,0)<0 || !quick_character()){
            Con_Printf("Quick start: %s or the character catalogue not found.\n",start.map);
            if(!sv.active)Cbuf_AddText("aw_main_menu\n");
            return;
        }
        copy_name(r.target,sizeof(r.target),start.map);VectorCopy(start.point,r.arrival);r.yaw=start.yaw;
        quick_go(&r,start.map);
        return;
    }
    if(n==1 && !AW_MiniwindActive() && AW_SkipCensus()){
        /* A normal build with --skip-census: Seyda Neen after the census, where dbg aw hors 0 arrives. */
        if(!quick_character()){
            Con_Printf("Quick start: character catalogue not found.\n");
            if(!sv.active)Cbuf_AddText("aw_main_menu\n");
            return;
        }
        copy_name(r.target,sizeof(r.target),"seyda");r.arrival[2]=64;r.yaw=90;
        quick_go(&r,"Seyda Neen");
        return;
    }
    if(n==3 && !strcmp(Cmd_Argv(1),"town"))s=Cmd_Argv(2);
    else if(n==2)s=Cmd_Argv(1);
    else if(n==1)s=start.kind==1?start.map:AW_MiniwindActive()?AW_Miniwind()->town:"";
    town=AW_TownFind(s);
    if(n>3 || town<0 || !(AW_Town(town)->flags&AW_TOWN_TELEPORT)){
        Con_Printf("Usage: aw_quick_start [town] <town with an arrival point, e.g. balmora> | map MAP X Y Z YAW\n");return;
    }
    memset(&r,0,sizeof(r));copy_name(r.target,sizeof(r.target),AW_Town(town)->name);
    if(!AW_TownArrival(r.target,0,r.arrival,&r.yaw) || !quick_character()){
        Con_Printf("Quick start: %s or the character catalogue not found.\n",AW_Town(town)->title);
        if(!sv.active)Cbuf_AddText("aw_main_menu\n");
        return;
    }
    quick_go(&r,AW_Town(town)->title);
}
static void demo_start(void) {
    FILE *f;
    pending=0;AW_StoryReset(0);AW_SaveReset();
    if(early_game_demo_start_1.value) {
        Con_Printf("early_game_demo_start_1: Seyda Neen town center, track 04.\n");
        if(!AW_MusicStartTrack(4))
            Con_Printf("Track 04 unavailable in exploration playlist; using normal music selection.\n");
        /* The exterior's info_player_start is the town-center point. Its
         * normal spawn path still checks the standing hull and nearby exits. */
        Cbuf_AddText("map seyda\n");
    } else {
        char prison[AW_MAP_PATH_SIZE];
        if(COM_FOpenFile(AW_MapPath("prison",prison,sizeof(prison)),&f)>=0 && f) {
            fclose(f);Cbuf_AddText("map prison\n");
        } else Cbuf_AddText("map seyda\n");
    }
}
void AW_SceneInit(void) {
    AW_HarvestInit();
    Cmd_AddCommand("aw_debug_hors",hors_command);
    Cvar_RegisterVariable(&intro_docks_variant);
    Cvar_RegisterVariable(&target_style);Cmd_AddCommand("aw_target_place",target_style_command);
    Cvar_RegisterVariable(&label_style);Cmd_AddCommand("aw_label_style",label_style_command);
    Cvar_RegisterVariable(&target_names);Cmd_AddCommand("aw_target_names_set",target_names_command);
    Cmd_AddCommand("aw_door_status",door_status);
    Cvar_RegisterVariable(&early_game_demo_start_1);
    Cmd_AddCommand("aw_scene",scene_command);
    Cmd_AddCommand("aw_teleport",teleport_command);
    Cmd_AddCommand("aw_shroompicker",shroompicker_command);
    Cmd_AddCommand("aw_demo_start",demo_start);
    Cmd_AddCommand("aw_quick_start",quick_start);
    /* aw_debug.c binds aw_save.c's aw_save_entry_refuse to AW_SceneSaveEntryRefuse (CHIM-32MB-SAVE-ENTRY-48) */
}
