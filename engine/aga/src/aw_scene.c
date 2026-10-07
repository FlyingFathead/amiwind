/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded local scene links, converted from owned door records. One BSP at a
 * time. This is not inventory, quest persistence or original opening logic.
 */
#include "quakedef.h"
#include "aw_hand_state.h"
#include <errno.h>
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_story.h"
#include "aw_region.h"
#include "aw_section.h"
#include "aw_world.h"
#include "aw_character.h"
#include "aw_harvest_runtime.h"
#include "amiwind_version.h"
typedef struct {char source[16],target[16],label[96];vec3_t point,arrival,mins,maxs;float yaw;int bounds;unsigned reference;} aw_scene_link_t;
static aw_scene_link_t links[128];static int count,loaded,pending;
static aw_scene_link_t next;
static char links_map[16];
static double door_ready;
static aw_scene_link_t opening_door;
static unsigned door_close;
static float health;
static aw_hand_snapshot_t hand_snapshot;
static double hand_torch_time;
static int hand_clock_ready;
static double started;
static int region_crossing,map_jump;
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
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<AW_WALKABLE_Z)return 0;
    VectorCopy(tr.endpos,e->v.origin);e->v.origin[2]+=0.25f;
    e->v.flags=(int)e->v.flags|FL_ONGROUND;
    if(tr.ent)e->v.groundentity=EDICT_TO_PROG(tr.ent);
    SV_LinkEdict(e,false);return 1;
}
/* Shared with the QC greeting builtin. A visible head can be above the fixed
 * walking hull. Intersect the resident alias bounds in model space, retaining
 * the exact crosshair and world/brush occlusion rather than a facing cone. */
edict_t *AW_NPCTarget(edict_t *p,vec3_t angles) {
    edict_t *e,*best=NULL;model_t *m;int i,j,index;float limit,lo,hi,a,b,o,d,t;
    vec3_t eye,end,forward,right,up,delta,local,ray;trace_t tr;
    if(!p || p->v.movetype!=MOVETYPE_WALK)return NULL;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(angles,forward,right,up);
    VectorMA(eye,72,forward,end);
    tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);e=tr.ent;
    /* Keep direct physical hits, including legacy assets without bounds. */
    limit=72;
    if(!tr.startsolid && !tr.allsolid && tr.fraction<1){
        limit=tr.fraction*72;
        if(e && !e->free && e->v.modelindex && e->v.netname &&
           !strcmp(pr_strings+e->v.classname,"aw_npc"))best=e;
    }else{
        tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);
        if(tr.startsolid || tr.allsolid)return NULL;
        limit=tr.fraction*72;
    }
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);index=(int)e->v.modelindex;
        if(e==p || e->free || !e->v.netname || index<=0 || index>=MAX_MODELS ||
           strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        m=sv.models[index];if(!m || m->type!=mod_alias)continue;
        VectorSubtract(eye,e->v.origin,delta);
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
static edict_t *npc_target(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict || cls.state!=ca_connected)return NULL;
    return AW_NPCTarget(svs.clients[0].edict,cl.viewangles);
}
const char *AW_SceneTargetName(void) {
    edict_t *driver;
    if(!target_names.value || key_dest!=key_game || pending || AW_CharacterActive() ||
       AW_ReaderActive() || AW_IntroPromptActive() ||
       (aw_story.stage!=AW_STAGE_DEMO && aw_story.stage<AW_STAGE_PAPERS))return NULL;
    driver=travel_target();if(driver)return pr_strings+driver->v.netname;
    {const char *npc=npc_hint();return npc?npc:AW_HarvestHint();}
}
const char *AW_SceneWorldModel(const char *name) {
    FILE *f=NULL;const char *region;
    region=AW_RegionWorldModel(name,intro_docks_variant.value==2 && aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE);
    if(region)return region;
    if(!strcmp(name,"seyda") && intro_docks_variant.value==2 &&
       aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE){
        if(COM_FOpenFile("maps/intro_docks.bsp",&f)>=0 && f){fclose(f);return "maps/intro_docks.bsp";}
        if(f)fclose(f);
        Con_Printf("Intro docks variant missing; retaining full exterior.\n");
    }
    return NULL;
}
int AW_Interior(void) {return sv.active && (!strcmp(sv.name,"torchtest") || (AW_MapId(sv.name)>=0 && strcmp(sv.name,"seyda") && strcmp(sv.name,"balmora") && AW_TerrainId(sv.name)<0));}
static int map_valid(const char *name) {return AW_MapId(name)>=0;}
static void read_links_for(const char *map) {
    FILE *f=NULL;char line[384],extra,path[64];aw_scene_link_t r;int n,i,version;
    if(!map_valid(map))return;
    if(loaded && !strcmp(links_map,map))return;
    strcpy(links_map,map);loaded=1;count=0;
    sprintf(path,"doors-%s.txt",map);
    COM_FOpenFile(path,&f);
    if(!f){sprintf(path,"scene-doors-%s.txt",map);COM_FOpenFile(path,&f);}
    if(!f && AW_MapId(map)<AW_MAP_COUNT && strcmp(map,"balmora"))COM_FOpenFile("scene-doors.txt",&f);
    if(f) {
        if(!fgets(line,sizeof(line),f)){fclose(f);return;}
        version=!strcmp(line,"AWD3\n")?3:!strcmp(line,"AWD2\n")?2:!strcmp(line,"AWD1\n")?1:0;
        if(!version){fclose(f);return;}
        while(count<128 && fgets(line,sizeof(line),f)) {
            memset(&r,0,sizeof(r));
            if(version==3)n=sscanf(line,"%15s %15s %u %f %f %f %f %f %f %f %f %f %f %95[^\r\n]",r.source,r.target,&r.reference,
                &r.mins[0],&r.mins[1],&r.mins[2],&r.maxs[0],&r.maxs[1],&r.maxs[2],
                &r.arrival[0],&r.arrival[1],&r.arrival[2],&r.yaw,r.label);
            else n=sscanf(line,version==2?"%15s %15s %f %f %f %f %f %f %f %f %f %f %95[^\r\n]":"%15s %15s %f %f %f %f %f %f %f %f %f %f %c",r.source,r.target,
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
    if(!strcmp(map,"balmora") || AW_MapId(map)>=AW_MAP_COUNT)return;
    if(COM_FOpenFile("scene-links.txt",&f)<0 || !f)return;
    while(count<128 && fgets(line,sizeof(line),f)) {
        memset(&r,0,sizeof(r));
        n=sscanf(line,"%15s %15s %f %f %f %f %f %f %f %c",r.source,r.target,
            &r.point[0],&r.point[1],&r.point[2],&r.arrival[0],&r.arrival[1],&r.arrival[2],&r.yaw,&extra);
        if(n!=9 || !map_valid(r.source) || !map_valid(r.target))continue;
        for(i=0;i<3;i++)if(!(fabs(r.point[i])<32768 && fabs(r.arrival[i])<32768))break;
        if(i!=3 || !(r.yaw>=0 && r.yaw<360))continue;
        links[count++]=r;
    }
    fclose(f);
}
static void read_links(void){read_links_for(sv.name);}
static void load_scene(aw_scene_link_t *link,int immediate) {
    edict_t *p=svs.clients[0].edict;char command[32];
    if(pending || !map_valid(link->target))return;
    if(!AW_RegionSelect(link->target,link->arrival,intro_docks_variant.value==2 &&
       aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE))return;
    if(region_crossing){
        AW_SetNextLoadingStyle(AW_RegionLoadingFrozen()?AW_LOADING_FROZEN:AW_LOADING_BLANK);
        AW_SetNextLoadingDelay();
    }
    shroompicker_view=0;
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
int AW_MapTeleport(const float *source_position) {
    aw_scene_link_t r;edict_t *p;
    if(pending || !sv.active || svs.maxclients!=1 || !svs.clients ||
       !(p=svs.clients[0].edict) || cls.state!=ca_connected || p->v.health<=0 ||
       AW_StoryRestricted())return 0;
    memset(&r,0,sizeof(r));
    if(!AW_WorldMapTarget(source_position,r.target,r.arrival))return 0;
    r.yaw=p->v.v_angle[1];region_crossing=0;door_ready=0;door_close=0;
    crossing_movetype=p->v.movetype;
    load_scene(&r,1);
    if(!pending)return 0;
    map_jump=1;return 1;
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
static int aimed_door(void) {
    int i,best=-1;edict_t *p;vec3_t eye,delta,hit,forward,right,up;float distance,closest=57;trace_t tr;
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected)return -1;
    p=svs.clients[0].edict;if(p->v.movetype!=MOVETYPE_WALK)return -1;
    read_links();VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    for(i=0;i<count;i++) {
        if(aw_story.ship_disabled && !strcmp(links[i].target,"prison"))continue;
        if(strcmp(sv.name,links[i].source) || !door_hit(&links[i],eye,forward,hit))continue;
        VectorSubtract(hit,eye,delta);distance=Length(delta);if(distance>=closest)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,hit,MOVE_NOMONSTERS,p);
        if(tr.startsolid || (1-tr.fraction)*distance>(links[i].bounds?1.0f:12.0f))continue;
        closest=distance;best=i;
    }
    return best;
}
/* Travel stays unavailable until the destination has a validated arrival
 * and map registration. A stray BSP file alone must never enable a paid ride. */
static int travel_open,travel_choice;
static int travel_return,travel_count=5;
static const char *travel_names[]={"Balmora","Gnisis","Suran","Vivec","Cancel"};
static const char *travel_message;
static edict_t *travel_target(void) {
    edict_t *e;
    if(key_dest!=key_game || AW_StoryRestricted())return NULL;
    e=npc_target();if(!e)return NULL;
    if(!strcmp(sv.name,"balmora") && !strcmp(pr_strings+e->v.netname,"Selvil Sareloth"))return e;
    if(!strcmp(sv.name,"seyda") && !strcmp(pr_strings+e->v.netname,"Darvame Hleran"))return e;
    return NULL;
}
static int travel_use(void) {
    edict_t *e=travel_target();
    if(!e)return 0;
    travel_return=!strcmp(sv.name,"balmora");
    travel_count=travel_return?2:5;
    travel_open=1;travel_choice=0;travel_message=NULL;
    key_dest=key_menu;IN_AWClearButtons();return 1;
}
int AW_TravelKey(int key) {
    if(!travel_open)return 0;
    if(!sv.active || key_dest!=key_menu){travel_open=0;return 0;}
    if(key==K_ESCAPE || (key==K_ENTER && travel_choice==travel_count-1)){
        travel_open=0;key_dest=key_game;IN_AWClearButtons();return 1;
    }
    if(key==K_UPARROW || key=='w'){travel_choice=(travel_choice+travel_count-1)%travel_count;travel_message=NULL;}
    if(key==K_DOWNARROW || key=='s'){travel_choice=(travel_choice+1)%travel_count;travel_message=NULL;}
    if(key==K_ENTER){
        aw_scene_link_t r;memset(&r,0,sizeof(r));
        if(travel_choice==0 && AW_BalmoraArrival(travel_return,r.arrival,&r.yaw)){
            strcpy(r.target,travel_return?"seyda":"balmora");
            travel_open=0;key_dest=key_game;load_scene(&r,0);
        }else travel_message="Destination not found.";
    }
    return 1;
}
int AW_TravelDraw(void) {
    int i;char line[96];
    if(!travel_open || key_dest!=key_menu)return 0;
    AW_UIBox(18,18,284,170);AW_UISmallBegin();
    AW_UITextBox(26,23,268,20,travel_return?"Silt Strider: Selvil Sareloth":"Silt Strider: Darvame Hleran",-1);
    sprintf(line,"Your gold: %ld",(long)AW_StateGet(&aw_state,AW_ITEM,"gold_001"));
    AW_UITextBox(26,44,268,16,line,-1);
    for(i=0;i<travel_count;i++){
        sprintf(line,"%s%s",i==travel_choice?"> ":"  ",travel_return?(i?"Cancel":"Seyda Neen"):travel_names[i]);
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
int AW_SceneUse(void) {
    int i;float duration;FILE *f=NULL;char path[40];if(pending || door_ready)return 1;if(travel_use())return 1;if(!npc_hint() && AW_HarvestUse())return 1;i=aimed_door();if(i<0)return 0;
    if(!AW_StoryDoor(links[i].reference)){AW_UISubtitle("",links[i].reference==119513?"Finish registration and leave through the courtyard.":links[i].reference==113889?"Check the barrel beside the door first.":"Ask the captain about your duties first.",4);return 1;}
    if(AW_StoryRestricted() && !strcmp(links[i].target,"census") && aw_story.stage<AW_STAGE_OFFICE){AW_UISubtitle("","Speak to the dock guard first.",4);return 1;}
    sprintf(path,"maps/%s.bsp",links[i].target);
    if(!map_valid(links[i].target) || COM_FOpenFile(path,&f)<0 || !f){
        if(f)fclose(f);
        AW_UISubtitle("","Interior not found.",3);return 1;
    }
    fclose(f);
    if(AW_StoryRestricted() && links[i].reference==119659)AW_StoryTransition(AW_STAGE_RELEASED);
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
    if(key_dest!=key_game || pending || AW_IntroUse() || !sv.active ||
       svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected ||
       svs.clients[0].edict->v.movetype!=MOVETYPE_WALK)return;
    driver=travel_target();
    if(driver){name=pr_strings+driver->v.netname;action="E: Talk";npc=1;}
    else if(!npc_hint() && (name=AW_HarvestHint())!=NULL){action="E: Pick";npc=1;}
    else if(!AW_OpeningHint(&name,&action)){
        i=aimed_door();
        if(i>=0){
            name=links[i].label[0]?links[i].label:!strcmp(links[i].target,"seyda")?"Seyda Neen":"Imperial Prison Ship";
            action=!AW_StoryDoor(links[i].reference)?"Locked - finish duties":
                AW_StoryRestricted() && !strcmp(links[i].target,"census") && aw_story.stage<AW_STAGE_OFFICE?"Speak to dock guard":
                !map_valid(links[i].target)?"Interior unavailable":"Enter: E";
        }else{ name=npc_hint();if(name){
            eval_t *voice;edict_t *target=npc_target();npc=1;
            voice=target?GetEdictFieldValue(target,"aw_voice"):NULL;
            if(voice && voice->string && pr_strings[voice->string])action="E: Talk";
        } }
    }
    if(!name)return;
    y=r_refdef.vrect.y+r_refdef.vrect.height;
    if(vid.height-y<20+AW_ConsoleCharHeight())return;
    if(!npc && (!AW_UISpeakerAtRight() || label_style.value!=2))AW_UIObjectName(name,(int)label_style.value);
    if(!action)return;
    sprintf(line,"(%s)",action);cw=AW_ConsoleCharWidth();w=strlen(line)*cw;
    for(i=0;line[i];i++)AW_ConsoleCharacter(vid.width-w-6+i*cw,y+19,(unsigned char)line[i]);
    scr_copyeverything=1;
}
static void door_status(void) {
    int i;vec3_t eye,forward,right,up,hit,delta;trace_t tr;edict_t *p;
    if(!sv.active)return;
    read_links();p=svs.clients[0].edict;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    Con_Printf("Doors %ld / aimed %ld / eye %ld %ld %ld / pitch %ld\n",(long)count,
        (long)aimed_door(),(long)eye[0],(long)eye[1],(long)eye[2],(long)cl.viewangles[0]);
    for(i=0;i<count;i++)if(!strcmp(sv.name,links[i].source)) {
        if(!door_hit(&links[i],eye,forward,hit)){Con_Printf("Door %ld outside aim/reach\n",(long)i);continue;}
        VectorSubtract(hit,eye,delta);tr=SV_Move(eye,vec3_origin,vec3_origin,hit,MOVE_NOMONSTERS,p);
        Con_Printf("Door %ld hit %ld %ld %ld distance100 %ld clear1000 %ld solid %ld\n",
            (long)i,(long)hit[0],(long)hit[1],(long)hit[2],(long)(Length(delta)*100),
            (long)(tr.fraction*1000),(long)tr.startsolid);
    }
}
/* Narrow interior landings need a local floor test, not the exterior's wide
 * four-direction square. Source door destinations may start above their floor;
 * allow a bounded downward search when the standing head intersects a hatch. */
int AW_InteriorPlace(edict_t *p,vec3_t preferred) {
    vec3_t top,bottom,point;trace_t tr;int i,drop;
    static int offsets[9][2]={{0,0},{16,0},{-16,0},{0,16},{0,-16},{16,16},{-16,16},{16,-16},{-16,-16}};
    for(drop=0;drop<=64;drop+=8)for(i=0;i<9;i++) {
        VectorCopy(preferred,top);top[0]+=offsets[i][0];top[1]+=offsets[i][1];top[2]+=8-drop;
        VectorCopy(top,bottom);bottom[2]-=32;
        tr=SV_Move(top,p->v.mins,p->v.maxs,bottom,MOVE_NORMAL,p);
        if(tr.startsolid || tr.allsolid || tr.fraction==1 || tr.plane.normal[2]<AW_WALKABLE_Z)continue;
        VectorCopy(tr.endpos,point);point[2]+=.25f;
        tr=SV_Move(point,p->v.mins,p->v.maxs,point,MOVE_NORMAL,p);
        if(tr.startsolid || tr.allsolid)continue;
        VectorCopy(point,p->v.origin);VectorCopy(point,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
        p->v.flags=(int)p->v.flags&~FL_ONGROUND;SV_LinkEdict(p,false);
        Con_Printf("Interior spawn: %ld %ld %ld\n",(long)point[0],(long)point[1],(long)point[2]);return 1;
    }
    Con_Printf("Interior spawn blocked; use dbg noclip to inspect.\n");return 0;
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
void AW_SceneSpawn(edict_t *p) {
    int placed=0;float eye;
    if(region_crossing && (!pending || strcmp(sv.name,next.target)))S_CancelSceneVoice();
    crossing_view_ready=0;hand_clock_ready=0;door_ready=0;
    if(!region_crossing)AW_UISubtitle("","",0);
    if(pending && !strcmp(sv.name,next.target)) {
        if(map_jump){
            placed=AW_MapPlace(p,next.arrival);
            if(!placed){
                AW_InteriorPlace(p,p->v.origin);
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
        }else placed=AW_InteriorPlace(p,next.arrival);
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
        if(AW_Interior() || !strcmp(sv.name,"balmora") || AW_TerrainId(sv.name)>=0)AW_InteriorPlace(p,p->v.origin);
        else AW_PlacePlayer(p,p->v.origin);
    }
    AW_IntroSpawn();AW_OpeningSpawn();AW_SaveSpawn();AW_HarvestSpawn();AW_GallerySpawn(p);region_crossing=map_jump=0;
    if(AW_CharacterLoad() && (eye=AW_CharacterEyeHeight())>0)p->v.view_ofs[2]=eye+p->v.mins[2];
    AW_HeapAuditReport(sv.worldmodel?sv.worldmodel->name:sv.name);
}
void AW_SceneTick(void) {
    aw_scene_link_t r;edict_t *p;
    if(!pending && sv.active && cls.state==ca_connected && cls.signon==SIGNONS &&
       key_dest==key_game && svs.maxclients==1 && svs.clients && (p=svs.clients[0].edict))
        AW_StreamTick(AW_CellChangeMethod()==2?AW_RegionAhead(p->v.origin,p->v.velocity,
            intro_docks_variant.value==2 && aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE,AW_StreamLookahead()):NULL);
    if(door_ready){
        if(!sv.active || strcmp(sv.name,opening_door.source)){door_ready=0;return;}
        if(realtime>=door_ready){door_ready=0;door_close=opening_door.reference;load_scene(&opening_door,0);}
        return;
    }
    if(door_close && !pending && cls.state==ca_connected && cls.signon==SIGNONS){
        AW_DoorSound(door_close,1);door_close=0;
    }
    if(pending || !sv.active || cls.state!=ca_connected || cls.signon!=SIGNONS || key_dest!=key_game ||
       svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict) ||
       p->v.health<=0 || (p->v.movetype!=MOVETYPE_WALK && p->v.movetype!=MOVETYPE_NOCLIP))return;
    memset(&r,0,sizeof(r));
    if(AW_SectionDestination(sv.name,p->v.origin,r.target)){
        VectorCopy(p->v.origin,r.arrival);
    }else if(AW_StoryRestricted() || !AW_WorldDestination(sv.name,p->v.origin,r.target,r.arrival)){
        if(!AW_RegionCrossing(p->v.origin,intro_docks_variant.value==2 && aw_story.stage>=AW_STAGE_SHIP && aw_story.stage<=AW_STAGE_OFFICE))return;
        strcpy(r.target,sv.name);VectorCopy(p->v.origin,r.arrival);
    }
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
static void scene_command(void) {
    aw_scene_link_t r;const char *s=Cmd_Argv(1);char path[40];FILE *f=NULL;int i,size;
    if(!Q_strcasecmp((char *)s,"seydaneen") || !Q_strcasecmp((char *)s,"seyda") ||
       !Q_strcasecmp((char *)s,"town"))s="town";
    else if(!Q_strcasecmp((char *)s,"ship") || !Q_strcasecmp((char *)s,"prisonship"))s="ship";
    else for(i=0;i<AW_MAP_COUNT;i++)if(!Q_strcasecmp((char *)s,(char *)AW_MapName(i))){s=AW_MapName(i);break;}
    if(!sv.active || Cmd_Argc()!=2 || (strcmp(s,"ship") && strcmp(s,"town") && !map_valid(s))) {
        Con_Printf("During play: dbg tp balmora/seydaneen/prisonship/<map name>; dbg tp opens the menu.\n");return;
    }
    door_ready=0;door_close=0;
    sprintf(path,"maps/%s.bsp",!strcmp(s,"ship")?"prison":!strcmp(s,"town")?"seyda":s);
    size=COM_FOpenFile(path,&f);if(f)fclose(f);
    if(!f || size<124){Con_Printf("Destination not found: %s.\n",s);return;}
    if(map_valid(s)){
        if(!strcmp(s,"balmora")){
            memset(&r,0,sizeof(r));strcpy(r.target,"balmora");
            if(AW_BalmoraArrival(0,r.arrival,&r.yaw)){
                if(!aw_character.valid || !aw_story.name[0]){
                    if(!AW_CharacterHors()){Con_Printf("Hors preset: character catalogue unavailable.\n");return;}
                    AW_SaveReset();svs.clients[0].edict->v.health=aw_character.current[0];
                    svs.clients[0].edict->v.movetype=MOVETYPE_WALK;noclip_anglehack=false;
                    Con_Printf("Created Hors: Nord, Barbarian, The Steed; after Census.\n");
                }
                load_scene(&r,1);
            }
            else Con_Printf("Balmora conversion not found.\n");
            return;
        }
        /* Select the destination area's entrance catalogue. Appended Balmora
         * interior IDs must not fall back to Seyda's unrelated door bank. */
        read_links_for(AW_MapId(s)>AW_MapId("balmora")?"balmora":"seyda");
        /* The catalogue's first Census entry is a separate upper doorway.
         * Debug arrival uses the inspected registration entrance from the pier. */
        if(!strcmp(s,"census"))for(i=0;i<count;i++)
            if(links[i].reference==113893 && !strcmp(links[i].target,s)){
                load_scene(&links[i],1);return;
            }
        for(i=0;i<count;i++)if(!strcmp(links[i].target,s)){load_scene(&links[i],1);return;}
        Con_Printf("No converted entrance to %s.\n",s);return;
    }
    memset(&r,0,sizeof(r));strcpy(r.target,!strcmp(s,"ship")?"prison":"seyda");
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
    memset(&r,0,sizeof(r));strcpy(r.target,"seyda");r.arrival[2]=64;r.yaw=90;
    Con_Printf("Created Hors: Nord, Barbarian, The Steed; after Census.\n");load_scene(&r,1);
}
static int teleport_coordinate(const char *text,float *result) {
    char *end;double value;const char *p;
    if(!text || !*text || strlen(text)>32)return 0;
    for(p=text;*p;p++)if(!((*p>='0' && *p<='9') || *p=='+' || *p=='-' ||
                         *p=='.' || *p=='e' || *p=='E'))return 0;
    errno=0;value=strtod(text,&end);
    if(end==text || *end || errno==ERANGE || !isfinite(value) || fabs(value)>2000000)return 0;
    *result=(float)value;return isfinite(*result);
}
typedef struct {int slot,verified;unsigned reference;char map[16],label[96];float x,y,yaw,pitch;} shroompicker_spot_t;
static int shroompicker_line(char *line,shroompicker_spot_t *spot) {
    int end=0,i;size_t length=strlen(line);
    if(!length || line[length-1]!='\n')return 0;
    line[--length]=0;
    if(length && line[length-1]=='\r')line[--length]=0;
    if(sscanf(line,"%d %d %u %15s %f %f %f %f %95[^\r\n]%n",&spot->slot,&spot->verified,
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
static void teleport_command(void) {
    vec3_t source;
    if(Cmd_Argc()==3) {
        if(!teleport_coordinate(Cmd_Argv(1),&source[0]) ||
           !teleport_coordinate(Cmd_Argv(2),&source[1])) {
            Con_Printf("Usage: dbg tp X Y (original Morrowind global coordinates)\n");return;
        }
        source[2]=0;
        if(!AW_MapTeleport(source))
            Con_Printf("Coordinate teleport unavailable; player state unchanged.\n");
        return;
    }
    if(Cmd_Argc()>3) {
        Con_Printf("Usage: dbg tp X Y, dbg tp <name>, or dbg tp map\n");return;
    }

    if(Cmd_Argc()==1 && sv.active){Cbuf_InsertText("aw_scene_menu\n");return;}
    scene_command();
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
        if(COM_FOpenFile("maps/prison.bsp",&f)>=0 && f) {
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
}
