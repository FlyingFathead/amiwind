/* SPDX-License-Identifier: GPL-2.0-or-later
 * Local development console commands. No gameplay state/save format implied.
 */
#include "quakedef.h"
#include "aw_actors.h"
#include "aw_links.h"
#include "aw_bounds.h"
#include "aw_save.h"
#include "aw_region.h"
#include "aw_world.h"
#include "aw_log.h"
#include "aw_spike.h"
#include "aw_hinged_door.h"
#include "aw_talk.h"
#ifdef AMIGA
#include <proto/dos.h>
#endif
#include "chim/chim.h"
#include "aw_miniwind.h"
#include "aw_quickchar.h"
#include "aw_testbox.h"
#include "aw_view.h"
#include "aw_inspect.h"
#include "aw_inventory.h"
#include "aw_statswin.h"
#include "aw_glut.h"
#include "aw_dial.h"
#include "aw_ambient.h"
#include "aw_move.h"
#include "aw_magic.h"
void AW_CamInit(void);
extern trace_t SV_ClipMoveToEntity(edict_t *,vec3_t,vec3_t,vec3_t,vec3_t);
static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected) {
        Con_Printf("AmiWind: start the local scene first.\n");return NULL;
    }
    return svs.clients[0].edict;
}
static void position(void) {
    edict_t *p=player();vec3_t global;if(!p)return;
    Con_Printf("position %ld %ld %ld / movement %ld\n",(long)p->v.origin[0],
        (long)p->v.origin[1],(long)p->v.origin[2],(long)p->v.movetype);
    if(AW_WorldToSource(sv.name,p->v.origin,global))
        Con_Printf("global %ld %ld %ld / scene %s / cell %ld,%ld\n",(long)global[0],
            (long)global[1],(long)global[2],sv.name,(long)floor(global[0]/8192),(long)floor(global[1]/8192));
    else Con_Printf("scene %s / no exterior coordinate transform\n",sv.name);
}
/* SESSION-AW-VIEW-IN-SOLID-54: a capture camera inside a booth wall drew blank frames that were first read as a room
 * fault. aw_view warns (it still places the camera: a capture may want it) when the eye point is in solid, or, in an
 * interior, open to nothing within 8192 units in one of the six axis directions (outside the room). */
static void view_check(edict_t *p) {
    static float dir[6][3]={{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
    static const char *toward[6]={"+x","-x","+y","-y","up","down"};
    vec3_t eye,end;trace_t tr;int i;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);
    VectorCopy(eye,end);end[2]-=0.125f;
    tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);
    if(tr.startsolid || tr.allsolid) {
        Con_Printf("aw_view WARNING: the camera at %ld %ld %ld is inside solid (a wall or outside the map): its frames show no room\n",
            (long)eye[0],(long)eye[1],(long)eye[2]);return;
    }
    if(!AW_Interior())return;
    for(i=0;i<6;i++) {
        VectorMA(eye,8192,dir[i],end);
        tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);
        if(tr.fraction>=1) {
            Con_Printf("aw_view WARNING: the camera at %ld %ld %ld is outside the room: nothing toward %s within 8192 units\n",
                (long)eye[0],(long)eye[1],(long)eye[2],toward[i]);return;
        }
    }
}
/* Reproducible local camera placement for visual regression captures. */
static void view(void) {
    edict_t *p=player();int i;float v[5];if(!p)return;
    if(p->v.movetype!=MOVETYPE_NOCLIP || Cmd_Argc()!=6) {
        Con_Printf("Enable noclip, then aw_view x y z yaw pitch\n");return;
    }
    for(i=0;i<5;i++){v[i]=Q_atof(Cmd_Argv(i+1));if(v[i]<-32768 || v[i]>32768)return;}
    if(v[4]<-80 || v[4]>80)return;
    for(i=0;i<3;i++)p->v.origin[i]=v[i];
    VectorCopy(vec3_origin,p->v.velocity);p->v.angles[0]=v[4];p->v.angles[1]=v[3];p->v.angles[2]=0;
    p->v.fixangle=1;SV_LinkEdict(p,false);view_check(p);
}
static void tcl(void) { if(player())Cbuf_AddText("noclip\n"); }
static void unstuck(void) { AW_Unstuck(player()); }
/* Camera-only diagnostic: preserve ordinary walking and collision. */
static void aim(void) {
    edict_t *p=player();float yaw,pitch;if(!p)return;
    if(Cmd_Argc()!=3){Con_Printf("Usage: aw_aim yaw pitch\n");return;}
    yaw=Q_atof(Cmd_Argv(1));pitch=Q_atof(Cmd_Argv(2));
    if(!(yaw>=0 && yaw<360 && pitch>=-70 && pitch<=80))return;
    V_StopPitchDrift();cl.viewangles[0]=pitch;cl.viewangles[1]=yaw;
    p->v.angles[0]=pitch;p->v.angles[1]=yaw;p->v.angles[2]=0;p->v.fixangle=1;
}
static void help(void) {Cbuf_InsertText("debug help\n");}
static void recover(void) {
    edict_t *p=player(),*start=NULL;int i;
    if(!p)return;
    for(i=1;i<sv.num_edicts;i++) {
        start=EDICT_NUM(i);
        if(!strcmp(pr_strings+start->v.classname,"info_player_start"))break;
    }
    if(i==sv.num_edicts){Con_Printf("No spawn point in this scene.\n");return;}
    if(!AW_RecoverPlace(p,start->v.origin))return;
    p->v.movetype=MOVETYPE_WALK;noclip_anglehack=false;
    VectorCopy(start->v.angles,p->v.angles);p->v.fixangle=1;
    SV_LinkEdict(p,false);Con_Printf("Returned to scene spawn.\n");
}
/* Numbered recall entry point; 0 is the validated current Seyda Neen spawn.
 * Future points need scene identity and safe standing placement, not raw warps. */
static void reset_location(void) {
    if(Cmd_Argc()!=2 || strcmp(Cmd_Argv(1),"0")) {
        Con_Printf("Usage: amiwind_debug_reset_location 0 (Seyda Neen town)\n");return;
    }
    if(AW_Interior()){Cbuf_InsertText("aw_scene town\n");return;}
    recover();
}
/* Native floor scan uses the same swept hull as movement, with no teleport. */
static void probe(void) {
    FILE *f;edict_t *p=player();int x,y,n=0,missing=0;trace_t a,b;vec3_t top,bottom;
    if(!p)return;
    f=fopen("collision-probe.csv","w");if(!f){Con_Printf("Cannot write collision-probe.csv\n");return;}
    fprintf(f,"x,y,world_z100,scene_z100,world_startsolid,scene_startsolid,scene_allsolid,scene_fraction10000\n");
    for(y=-640;y<=640;y+=64)for(x=-640;x<=640;x+=64) {
        top[0]=bottom[0]=x;top[1]=bottom[1]=y;top[2]=400;bottom[2]=-505;
        a=SV_ClipMoveToEntity(sv.edicts,top,p->v.mins,p->v.maxs,bottom);
        b=SV_Move(top,p->v.mins,p->v.maxs,bottom,MOVE_NORMAL,p);
        if(a.fraction==1)missing++;
        fprintf(f,"%d,%d,%ld,%ld,%d,%d,%d,%ld\n",x,y,(long)(a.endpos[2]*100),
            (long)(b.endpos[2]*100),a.startsolid,b.startsolid,b.allsolid,(long)(b.fraction*10000));n++;
    }
    fclose(f);Con_Printf("Floor probe: %ld traces, %ld missing world hits.\n",(long)n,(long)missing);
}
static long field(edict_t *p,char *name) {
    eval_t *v=GetEdictFieldValue(p,name);return v?(long)v->_float:0;
}
static void eyeheight(void) {
    edict_t *p=player();float v;if(!p)return;
    if(Cmd_Argc()==2){v=Q_atof(Cmd_Argv(1));if(v>=4 && v<=24)p->v.view_ofs[2]=v;
        else {Con_Printf("Eye offset must be 4..24, above hull origin.\n");return;}}
    else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg eyeheight [offset]\n");return;}
    Con_Printf("Eye offset %.3f / above feet %.3f; collision unchanged.\n",(double)p->v.view_ofs[2],(double)(p->v.view_ofs[2]-p->v.mins[2]));
}
/* Compare live standing and point sweeps. In a flat calibration room the
 * difference between their limits measures the effective physical box. */
static void dimensions(void) {
    edict_t *p=player();hull_t *h;vec3_t end;trace_t body,point;int axis,sign;
    if(!p || !sv.worldmodel)return;
    h=&sv.worldmodel->hulls[1];
    Con_Printf("Player dimensions %.3f %.3f %.3f; BSP hull %.3f %.3f %.3f\n",
        (double)(p->v.maxs[0]-p->v.mins[0]),(double)(p->v.maxs[1]-p->v.mins[1]),(double)(p->v.maxs[2]-p->v.mins[2]),
        (double)(h->clip_maxs[0]-h->clip_mins[0]),(double)(h->clip_maxs[1]-h->clip_mins[1]),(double)(h->clip_maxs[2]-h->clip_mins[2]));
    for(axis=0;axis<3;axis++)for(sign=-1;sign<=1;sign+=2){
        VectorCopy(p->v.origin,end);end[axis]+=sign*128;
        body=SV_Move(p->v.origin,p->v.mins,p->v.maxs,end,MOVE_NOMONSTERS,p);
        point=SV_Move(p->v.origin,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);
        Con_Printf("Dimension axis %ld sign %ld body %.5f point %.5f solid %ld/%ld\n",
            (long)axis,(long)sign,(double)body.endpos[axis],(double)point.endpos[axis],
            (long)body.startsolid,(long)point.startsolid);
    }
}
static void hands(void) {
    edict_t *p=player();if(!p)return;
    Con_Printf("hands state %ld goal %ld frame %ld torch %ld / time %ld\n",field(p,"aw_hand_state"),field(p,"aw_hand_goal"),(long)p->v.weaponframe,field(p,"aw_torch"),(long)(sv.time*1000));
    Con_Printf("attack button %ld latched %ld; health %ld water %ld movetype %ld; sent move %ld %ld %ld\n",
        (long)p->v.button0,field(p,"aw_attack_latched"),(long)p->v.health,
        (long)p->v.waterlevel,(long)p->v.movetype,
        (long)cl.cmd.forwardmove,(long)cl.cmd.sidemove,(long)cl.cmd.upmove);
    AW_IntroInputReport();
}
static void npcs(void) {
    int i;edict_t *p;if(!player())return;
    /* dbg npcs talk [ID]: Talk with the nearest NPC (or that record), the dialogue window (aw_dialwin.c) */
    if(Cmd_Argc()>1 && !Q_strcasecmp(Cmd_Argv(1),"talk")){AW_DialWindowTalk(Cmd_Argc()>2?Cmd_Argv(2):NULL);return;}
    for(i=1;i<sv.num_edicts;i++) {
        p=EDICT_NUM(i);
        if(!p->free && !strcmp(pr_strings+p->v.classname,"aw_npc"))
            Con_Printf("NPC %s: %ld %ld %ld yaw %ld auto %ld E %ld armed %ld\n",pr_strings+p->v.netname,
                (long)p->v.origin[0],(long)p->v.origin[1],(long)p->v.origin[2],(long)p->v.angles[1],
                field(p,"aw_hello_count"),field(p,"aw_manual_count"),(long)!field(p,"aw_hello_done"));
    }
}
/* Read-only release audit of live feet against current collision. Run after
 * settling, region re-entry and quickload. Exceptions are explicit metadata. */
static void npc_floors(void) {
    FILE *f;int i,index,bad=0,total=0,exempt;edict_t *e;eval_t *id;model_t *m;
    vec3_t start,end;trace_t tr;float feet,gap;const char *status;
    if(!player())return;
    f=fopen("npc-ground.tsv","a");if(!f){Con_Printf("Cannot write npc-ground.tsv\n");return;}
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        total++;index=(int)e->v.modelindex;m=index>0 && index<MAX_MODELS?sv.models[index]:NULL;
        feet=e->v.origin[2]+(m?m->mins[2]:0);
        VectorCopy(e->v.origin,start);VectorCopy(start,end);start[2]+=8;end[2]-=64;
        tr=SV_Move(start,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,e);
        gap=feet-tr.endpos[2];exempt=field(e,"aw_ground_mode")!=0;
        status=exempt?"exempt":!AW_RegionGroundCoverage(e->v.origin)?"deferred-owner-core":tr.startsolid || tr.allsolid?"blocked":tr.fraction>=1?"unsupported":
            tr.plane.normal[2]<AW_WALKABLE_Z?"steep":gap<-.5f?"embedded":gap>1.0f?"floating":"grounded";
        if(!exempt && strcmp(status,"grounded") && strcmp(status,"deferred-owner-core"))bad++;
        id=GetEdictFieldValue(e,"aw_source_id");
        fprintf(f,"%s\t%ld\t%s\t%s\t%s\t%.5f\t%.5f\t%.5f\t%.5f\t%.5f\n",sv.name,
            field(e,"aw_ref"),id && id->string?pr_strings+id->string:"?",pr_strings+e->v.netname,status,
            (double)e->v.origin[0],(double)e->v.origin[1],(double)feet,(double)tr.endpos[2],(double)gap);
    }
    fclose(f);Con_Printf("NPC ground audit: %ld residents, %ld need review; npc-ground.tsv\n",(long)total,(long)bad);
}
/* On demand only: trace the actual standing hull, including scene broadphase. */
static void blockers(void) {
    static const float directions[8][2]={{1,0},{.7071,.7071},{0,1},{-.7071,.7071},
        {-1,0},{-.7071,-.7071},{0,-1},{.7071,-.7071}};
    edict_t *p=player();trace_t tr;vec3_t end;int i;if(!p)return;
    position();
    for(i=0;i<8;i++) {
        VectorCopy(p->v.origin,end);end[0]+=directions[i][0]*24;end[1]+=directions[i][1]*24;
        tr=SV_Move(p->v.origin,p->v.mins,p->v.maxs,end,MOVE_NORMAL,p);
        Con_Printf("dir %ld frac %ld solid %ld/%ld hit %s normal %ld %ld %ld\n",
            (long)i,(long)(tr.fraction*1000),(long)tr.startsolid,(long)tr.allsolid,
            tr.ent?pr_strings+tr.ent->v.model:"none",(long)(tr.plane.normal[0]*100),
            (long)(tr.plane.normal[1]*100),(long)(tr.plane.normal[2]*100));
    }
}
/* Diagnostic logs (aw_log.c, BOOT-VOLUME-NOT-VALIDATED-33): held in memory and
 * written at exit or with dbg savelogs; aw_logs_live 1 writes them as they
 * happen (benchmarks, diagnostics). Saved in config.cfg only once the player
 * has chosen it with dbg logs live; a --live-logs build sets it in
 * default-game.cfg. */
cvar_t aw_logs_live={"aw_logs_live","0",false};
static void log_folder(char *out,int size)
{
#ifdef AMIGA
    BPTR lock=Lock("",ACCESS_READ);
    if(lock){if(!NameFromLock(lock,out,size))out[0]=0;UnLock(lock);if(out[0])return;}
#endif
    snprintf(out,size,"the game folder");
}
static void logs_live_command(void)
{
    char *text=Cmd_Argv(1);
    if(Cmd_Argc()==1){
        Con_Printf("Diagnostic logs %s. Usage: dbg logs live on/off.\n",AW_LogLive()?"live (written as they happen)":
                   "in memory (written at Exit game or with dbg savelogs)");return;}
    if(Cmd_Argc()!=2 || (Q_strcasecmp(text,"on") && Q_strcasecmp(text,"off") && Q_strcasecmp(text,"true") &&
       Q_strcasecmp(text,"false") && strcmp(text,"1") && strcmp(text,"0"))){
        Con_Printf("Usage: dbg logs live on/off, true/false or 1/0.\n");return;}
    Cvar_SetValue(aw_logs_live.name,!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1"));
    aw_logs_live.archive=true;
    Con_Printf("Diagnostic logs %s (saved).\n",aw_logs_live.value?"live: written as they happen":"in memory: written at Exit game or with dbg savelogs");
}
static void savelogs_command(void)
{
    char folder[256];int i,files;unsigned long dropped=0;
    for(i=0;i<AW_LOG_COUNT;i++)dropped+=AW_LogDroppedLines(i);
    files=AW_LogFlushAll();
    log_folder(folder,sizeof folder);
    if(AW_LogLive())Con_Printf("Diagnostic logs are live and already in %s.\n",folder);
    else Con_Printf("Saved %d diagnostic log files to %s (%lu older lines dropped from the memory logs).\n",files,folder,dropped);
}
/* dbg god / dbg godmode: Quake's god cheat (Host_God_f, FL_GODMODE, the HUD GOD
 * indicator) with the usual on/off, true/false or 1/0 words. Not saved. The
 * state lives only in the player's edict; this asks Quake's own "god" to flip it. */
static void godmode_command(void)
{
    char *text=Cmd_Argv(1);int on,now;
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && Q_strcasecmp(text,"on") && Q_strcasecmp(text,"off") &&
       Q_strcasecmp(text,"true") && Q_strcasecmp(text,"false") && strcmp(text,"1") && strcmp(text,"0"))){
        Con_Printf("Usage: dbg godmode [on/off, true/false or 1/0]; no argument toggles (not saved).\n");return;}
    if(!sv.active || !sv_player){Con_Printf("Godmode needs a running game.\n");return;}
    now=((int)sv_player->v.flags & FL_GODMODE)!=0;
    on=Cmd_Argc()==1?!now:(!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1"));
    if(on!=now)Cbuf_AddText("god\n");   /* Host_God_f prints "godmode ON/OFF" */
    else Con_Printf("godmode %s\n",on?"ON":"OFF");
}
/* A recentre of the session's origin by d (CHIM's window, "chim crossing recentre 1", a test setting; design note
 * weak point 5), the server's and the client's half (aw_scene.c, before CHIM moves its own): every edict (its
 * links follow in CHIM's frame world rebuild), the client's entities (both interpolation ends and baselines),
 * static entities, dynamic lights, particles and sound channels. Engine modules keeping positions of their own
 * (paths, companions, combat) are not moved yet: the forced recentre is there to find exactly those. */
extern particle_t *active_particles;
static void AW_SessionShift(const float *d) {
    int i,k;edict_t *e;particle_t *pt;
    for(i=1,e=NEXT_EDICT(sv.edicts);i<sv.num_edicts;i++,e=NEXT_EDICT(e)){
        if(e->free)continue;
        for(k=0;k<2;k++){e->v.origin[k]-=d[k];e->v.oldorigin[k]-=d[k];e->baseline.origin[k]-=d[k];}
    }
    for(i=0;i<MAX_EDICTS;i++)for(k=0;k<2;k++){
        cl_entities[i].origin[k]-=d[k];cl_entities[i].msg_origins[0][k]-=d[k];cl_entities[i].msg_origins[1][k]-=d[k];
        cl_entities[i].baseline.origin[k]-=d[k];
    }
    for(i=0;i<cl.num_statics;i++)for(k=0;k<2;k++)cl_static_entities[i].origin[k]-=d[k];
    for(i=0;i<MAX_DLIGHTS;i++)for(k=0;k<2;k++)cl_dlights[i].origin[k]-=d[k];
    for(pt=active_particles;pt;pt=pt->next)for(k=0;k<2;k++)pt->org[k]-=d[k];
    for(i=0;i<total_channels;i++)for(k=0;k<2;k++)channels[i].origin[k]-=d[k];
    for(k=0;k<2;k++)listener_origin[k]-=d[k];
}
void AW_DebugInit(void) {
    AW_InspectInit();
    Cvar_RegisterVariable(&aw_logs_live);Cmd_AddCommand("aw_logs_live_set",logs_live_command);Cmd_AddCommand("aw_savelogs",savelogs_command);Cmd_AddCommand("aw_godmode",godmode_command);
    AW_GalleryInit();AW_SweepInit();AW_WorldUIInit();AW_StatsWindowInit();AW_DebugTorchInit();
    AW_StreamInit();AW_PhotoInit();AW_SpikeInit();Chim_Init();
    /* CHIM's window (type 1 crossings) names a cell's region map through the world directory. */
    {extern int (*chim_cell_map)(int,int,char *,int);chim_cell_map=AW_CellMap;}
    {extern void (*aw_session_shift)(const float *);aw_session_shift=AW_SessionShift;}
    AW_MiniwindInit();AW_QuickCharInit();AW_TestBoxInit();
    AW_CamInit();AW_InputDebugInit();AW_BoundsInit();AW_DoorAudioInit();AW_HingedDoorInit();aw_hinged_story=AW_OpeningHingedStory;AW_TalkInit();AW_MwscriptInit();AW_CompanionInit();AW_CombatInit();AW_AmbientInit();AW_MoveInit();AW_ActorsInit();AW_ViewInit();AW_LavaInit();AW_MagicInit();AW_AnimInit();AW_GlutInit();AW_DialWindowInit();AW_AnimKitInit();AW_HalloweenInit();AW_DemoWindInit();AW_WaitInit();AW_ConsoleInit();AW_SceneInit();AW_UIInit();AW_IconsInit();AW_IntroInit();AW_SaveInit();
    aw_save_entry_refuse=AW_SceneSaveEntryRefuse;   /* a save in a 32 MB place on less Fast RAM (CHIM-32MB-SAVE-ENTRY-48) */
    /* a bad sprite (r_sprite.c) names the CHIM streamed static it belongs to (SPRITE-BAD-TYPE-THREADED-56) */
    {extern const char *(*aw_sprite_describe)(const entity_t *,char *,int);
     extern const char *ChimStatics_Describe(const entity_t *,char *,int);aw_sprite_describe=ChimStatics_Describe;}
    Cmd_AddCommand("amiwind_debug_reset_location",reset_location);
    Cmd_AddCommand("aw_hands",hands);Cmd_AddCommand("aw_eyeheight",eyeheight);
    Cmd_AddCommand("aw_dimensions",dimensions);
    Cmd_AddCommand("aw_npc_floors",npc_floors);
    Cmd_AddCommand("aw_blockers",blockers);
    Cmd_AddCommand("aw_npcs",npcs);Cmd_AddCommand("tcl",tcl);Cmd_AddCommand("aw_help",help);Cmd_AddCommand("help",help);
    Cmd_AddCommand("aw_view",view);Cmd_AddCommand("aw_recover",recover);Cmd_AddCommand("aw_unstuck",unstuck);Cmd_AddCommand("aw_pos",position);Cmd_AddCommand("aw_probe",probe);
    Cmd_AddCommand("aw_aim",aim);Cmd_AddCommand("aw_startup",AW_MovieStartup);
}
