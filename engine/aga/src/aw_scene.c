/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded local scene links, converted from owned door records. One BSP at a
 * time. This is not inventory, quest persistence or original opening logic.
 */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_story.h"
#include "amiwind_version.h"
typedef struct {char source[16],target[16],label[96];vec3_t point,arrival,mins,maxs;float yaw;int bounds;unsigned reference;} aw_scene_link_t;
static aw_scene_link_t links[64];static int count,loaded,pending;
static aw_scene_link_t next;
static float health,hand_goal;
static double started;
static cvar_t early_game_demo_start_1={"early_game_demo_start_1","1"};
static cvar_t target_names={"aw_target_names","1",true};
static cvar_t label_style={"aw_interaction_label_style","1",true};
static cvar_t target_style={"aw_target_name_style","2",true};
int AW_SceneUIOption(int option,int change) {
    cvar_t *c=option==0?&target_names:option==1?&target_style:&label_style;int value;
    value=option==0?(c->value!=0):(int)c->value;
    if(option!=0 && (value<1 || value>3))value=option==1?2:1;
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
const char *AW_SceneTargetName(void) {
    edict_t *p,*e;vec3_t eye,end,forward,right,up;trace_t tr;int i;
    if((!target_names.value && !AW_UIVoiceAimOnly()) || key_dest!=key_game || pending || !sv.active ||
       svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict ||
       cls.state!=ca_connected || AW_CharacterActive() || AW_ReaderActive() ||
       (aw_story.stage!=AW_STAGE_DEMO && aw_story.stage<AW_STAGE_PAPERS))return NULL;
    p=svs.clients[0].edict;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    for(i=0;i<3;i++)end[i]=eye[i]+forward[i]*96;
    tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);e=tr.ent;
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || !e || e->free ||
       !e->v.modelindex || strcmp(pr_strings+e->v.classname,"aw_npc") || !e->v.netname)return NULL;
    return pr_strings+e->v.netname;
}
int AW_Interior(void) {return sv.active && AW_MapId(sv.name)>=0 && strcmp(sv.name,"seyda");}
static int map_valid(char *name) {return AW_MapId(name)>=0;}
static void read_links(void) {
    FILE *f;char line[384],extra;aw_scene_link_t r;int n,i,version;
    if(loaded)return;loaded=1;
    if(COM_FOpenFile("scene-doors.txt",&f)>=0 && f) {
        if(!fgets(line,sizeof(line),f)){fclose(f);return;}
        version=!strcmp(line,"AWD3\n")?3:!strcmp(line,"AWD2\n")?2:!strcmp(line,"AWD1\n")?1:0;
        if(!version){fclose(f);return;}
        while(count<64 && fgets(line,sizeof(line),f)) {
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
    if(COM_FOpenFile("scene-links.txt",&f)<0 || !f)return;
    while(count<64 && fgets(line,sizeof(line),f)) {
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
static void load_scene(aw_scene_link_t *link) {
    edict_t *p=svs.clients[0].edict;eval_t *v;char command[32];
    if(pending || !map_valid(link->target))return;next=*link;pending=1;started=Sys_FloatTime();
    AW_SaveCapture();
    health=p->v.health;v=GetEdictFieldValue(p,"aw_hand_goal");hand_goal=v?v->_float:0;
    IN_AWClearButtons();AW_MusicSceneEvent("scene-leave");
    Con_Printf("Loading AmiWind v" AMIWIND_VERSION ": %s...\n",next.target);
    sprintf(command,"map %s\n",next.target);Cbuf_AddText(command);
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
int AW_SceneUse(void) {
    int i;FILE *f=NULL;char path[40];if(pending)return 1;i=aimed_door();if(i<0)return 0;
    if(!AW_StoryDoor(links[i].reference)){AW_UISubtitle("",links[i].reference==113889?"Check the barrel beside the door first.":"Ask the captain about your duties first.",4);return 1;}
    if(AW_StoryRestricted() && !strcmp(links[i].target,"census") && aw_story.stage<AW_STAGE_OFFICE){AW_UISubtitle("","Speak to the dock guard first.",4);return 1;}
    sprintf(path,"maps/%s.bsp",links[i].target);
    if(!map_valid(links[i].target) || COM_FOpenFile(path,&f)<0 || !f){
        if(f)fclose(f);AW_UISubtitle("","Interior not found.",3);return 1;
    }
    fclose(f);
    if(AW_StoryRestricted() && links[i].reference==119659)AW_StoryTransition(AW_STAGE_RELEASED);
    load_scene(&links[i]);return 1;
}
/* Match the manual QC greeting selector, including its voice cooldown and
 * scripted-actor exclusion. This only labels greetings supported by that path. */
static const char *npc_hint(void)
{
    edict_t *p,*e,*best=NULL;eval_t *v;ddef_t *g;int i;
    vec3_t eye,point,delta,forward,right,up;float distance,closest=72;trace_t tr;
    g=ED_FindGlobal("aw_voice_deadline");
    if(g && sv.time<pr_globals[g->ofs])return NULL;
    p=svs.clients[0].edict;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || !e->v.modelindex || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        VectorCopy(e->v.origin,point);point[2]+=27;VectorSubtract(point,eye,delta);distance=Length(delta);
        if(distance<=.1f || distance>=closest || DotProduct(delta,forward)/distance<=.65f)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,point,MOVE_NOMONSTERS,p);
        if(tr.startsolid || tr.fraction<1)continue;
        closest=distance;best=e;
    }
    if(!best)return NULL;
    /* Identity is independent of the greeting cooldown. Only advertise Talk
     * when the manual greeting candidate is also the NPC under the crosshair. */
    VectorMA(eye,96,forward,point);tr=SV_Move(eye,vec3_origin,vec3_origin,point,MOVE_NORMAL,p);
    if(tr.ent!=best || tr.startsolid || tr.allsolid)return NULL;
    v=GetEdictFieldValue(best,"aw_intro_role");if(v && v->_float)return NULL;
    v=GetEdictFieldValue(best,"aw_voice");if(!v || !v->string)return NULL;
    return pr_strings+best->v.netname;
}
/* npc_interaction_layout_template_001: Morrowind name, console action below. */
void AW_SceneDraw(void) {
    int i,y,w,cw,npc=0;char line[80];const char *name=NULL,*action=NULL;extern int scr_copyeverything;
    if(!AW_UISpeakerAtRight() || target_style.value!=2)AW_UIObjectName(AW_SceneTargetName(),(int)target_style.value);
    if(key_dest!=key_game || pending || AW_IntroUse() || !sv.active ||
       svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected ||
       svs.clients[0].edict->v.movetype!=MOVETYPE_WALK)return;
    if(!AW_OpeningHint(&name,&action)){
        i=aimed_door();
        if(i>=0){
            name=links[i].label[0]?links[i].label:!strcmp(links[i].target,"seyda")?"Seyda Neen":"Imperial Prison Ship";
            action=!AW_StoryDoor(links[i].reference)?"Locked - finish duties":
                AW_StoryRestricted() && !strcmp(links[i].target,"census") && aw_story.stage<AW_STAGE_OFFICE?"Speak to dock guard":
                !map_valid(links[i].target)?"Interior unavailable":"Enter: E";
        }else{ name=npc_hint();if(name){action="Talk: E";npc=1;} }
    }
    if(!name)return;
    y=r_refdef.vrect.y+r_refdef.vrect.height;
    if(vid.height-y<20+AW_ConsoleCharHeight())return;
    if(!npc && (!AW_UISpeakerAtRight() || label_style.value!=2))AW_UIObjectName(name,(int)label_style.value);
    sprintf(line,"(%s)",action);cw=AW_ConsoleCharWidth();w=strlen(line)*cw;
    for(i=0;line[i];i++)AW_ConsoleCharacter(vid.width-w-6+i*cw,y+19,(unsigned char)line[i]);
    scr_copyeverything=1;
}
static void door_status(void) {
    int i;vec3_t eye,forward,right,up,hit,delta;trace_t tr;edict_t *p;
    if(!sv.active)return;read_links();p=svs.clients[0].edict;
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
        if(tr.startsolid || tr.allsolid || tr.fraction==1 || tr.plane.normal[2]<.7f)continue;
        VectorCopy(tr.endpos,point);point[2]+=.25f;
        tr=SV_Move(point,p->v.mins,p->v.maxs,point,MOVE_NORMAL,p);
        if(tr.startsolid || tr.allsolid)continue;
        VectorCopy(point,p->v.origin);VectorCopy(point,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
        p->v.flags=(int)p->v.flags&~FL_ONGROUND;SV_LinkEdict(p,false);
        Con_Printf("Interior spawn: %ld %ld %ld\n",(long)point[0],(long)point[1],(long)point[2]);return 1;
    }
    Con_Printf("Interior spawn blocked; use dbg noclip to inspect.\n");return 0;
}
void AW_SceneSpawn(edict_t *p) {
    eval_t *v;int placed=0;
    if(pending && !strcmp(sv.name,next.target)) {
        placed=AW_InteriorPlace(p,next.arrival);
        p->v.angles[0]=0;p->v.angles[1]=next.yaw;p->v.angles[2]=0;p->v.fixangle=1;
        p->v.health=health;v=GetEdictFieldValue(p,"aw_hand_goal");if(v)v->_float=hand_goal;
        Con_Printf("Scene ready: %s, %ld ms, %ld hunk bytes, arrival %s\n",sv.name,
            (long)((Sys_FloatTime()-started)*1000),(long)(Hunk_LowMark()+Hunk_HighMark()),placed?"checked":"blocked");
        AW_MusicSceneEvent("scene-enter");pending=0;
    } else {
        pending=0;if(AW_Interior())AW_InteriorPlace(p,p->v.origin);else AW_PlacePlayer(p,p->v.origin);
    }
    AW_IntroSpawn();AW_OpeningSpawn();AW_SaveSpawn();
}
static void scene_command(void) {
    aw_scene_link_t r;char *s=Cmd_Argv(1);int i;
    if(!sv.active || Cmd_Argc()!=2 || (strcmp(s,"ship") && strcmp(s,"town") && !map_valid(s))) {
        Con_Printf("Usage: dbg scene ship/town/<map name>, or dbg scene change\n");return;
    }
    if(map_valid(s)){
        read_links();
        for(i=0;i<count;i++)if(!strcmp(links[i].target,s)){load_scene(&links[i]);return;}
        Con_Printf("No converted entrance to %s.\n",s);return;
    }
    memset(&r,0,sizeof(r));strcpy(r.target,!strcmp(s,"ship")?"prison":"seyda");
    if(!strcmp(s,"ship")){r.arrival[1]=-35;r.arrival[2]=-4;r.yaw=90;}
    else {r.arrival[0]=0;r.arrival[1]=0;r.arrival[2]=64;r.yaw=90;}
    load_scene(&r);
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
    Cvar_RegisterVariable(&target_style);Cmd_AddCommand("aw_target_place",target_style_command);
    Cvar_RegisterVariable(&label_style);Cmd_AddCommand("aw_label_style",label_style_command);
    Cvar_RegisterVariable(&target_names);Cmd_AddCommand("aw_target_names_set",target_names_command);
    Cmd_AddCommand("aw_door_status",door_status);
    Cvar_RegisterVariable(&early_game_demo_start_1);
    Cmd_AddCommand("aw_scene",scene_command);
    Cmd_AddCommand("aw_demo_start",demo_start);
}
