/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded local scene links, converted from owned door records. One BSP at a
 * time. This is not inventory, quest persistence or original opening logic.
 */
#include "quakedef.h"
#include "amiwind_version.h"
typedef struct {char source[16],target[16];vec3_t point,arrival;float yaw;} aw_scene_link_t;
static aw_scene_link_t links[4];static int count,loaded,pending;
static aw_scene_link_t next;
static float health,hand_goal;
static double started;
static cvar_t early_game_demo_start_1={"early_game_demo_start_1","1"};
int AW_Interior(void) {return sv.active && !strcmp(sv.name,"prison");}
static int map_valid(char *name) {return !strcmp(name,"prison") || !strcmp(name,"seyda");}
static void read_links(void) {
    FILE *f;char line[256],extra;aw_scene_link_t r;int n,i;
    if(loaded)return;loaded=1;
    if(COM_FOpenFile("scene-links.txt",&f)<0 || !f)return;
    while(count<4 && fgets(line,sizeof(line),f)) {
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
    edict_t *p=svs.clients[0].edict;eval_t *v;
    if(pending)return;next=*link;pending=1;started=Sys_FloatTime();
    health=p->v.health;v=GetEdictFieldValue(p,"aw_hand_goal");hand_goal=v?v->_float:0;
    IN_AWClearButtons();AW_MusicSceneEvent("scene-leave");
    Con_Printf("Loading AmiWind v" AMIWIND_VERSION ": %s...\n",next.target);
    Cbuf_AddText(!strcmp(next.target,"prison")?"map prison\n":"map seyda\n");
}
int AW_SceneUse(void) {
    int i;edict_t *p;vec3_t eye,delta,forward,right,up;float distance;trace_t tr;
    if(pending)return 1;
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected)return 0;
    p=svs.clients[0].edict;if(p->v.movetype!=MOVETYPE_WALK)return 0;
    read_links();VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    for(i=0;i<count;i++) {
        if(strcmp(sv.name,links[i].source))continue;
        VectorSubtract(links[i].point,eye,delta);distance=Length(delta);
        if(distance>56 || distance<1 || DotProduct(delta,forward)/distance<0.45f)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,links[i].point,MOVE_NOMONSTERS,p);
        if(tr.startsolid || (1-tr.fraction)*distance>12)continue;
        load_scene(&links[i]);return 1;
    }
    return 0;
}
/* Narrow interior landings need a local floor test, not the exterior's wide
 * four-direction square. Source door destinations may start above their floor;
 * allow a bounded downward search when the standing head intersects a hatch. */
int AW_InteriorPlace(edict_t *p,vec3_t preferred) {
    vec3_t top,bottom,point;trace_t tr;int i,drop;
    static int offsets[9][2]={{0,0},{16,0},{-16,0},{0,16},{0,-16},{16,16},{-16,16},{16,-16},{-16,-16}};
    for(drop=0;drop<=64;drop+=32)for(i=0;i<9;i++) {
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
}
static void scene_command(void) {
    aw_scene_link_t r;char *s=Cmd_Argv(1);
    if(!sv.active || Cmd_Argc()!=2 || (strcmp(s,"ship") && strcmp(s,"town"))) {
        Con_Printf("Usage: dbg scene ship/town\n");return;
    }
    memset(&r,0,sizeof(r));strcpy(r.target,!strcmp(s,"ship")?"prison":"seyda");
    if(!strcmp(s,"ship")){r.arrival[1]=-35;r.arrival[2]=-4;r.yaw=90;}
    else {r.arrival[0]=0;r.arrival[1]=0;r.arrival[2]=64;r.yaw=90;}
    load_scene(&r);
}
static void demo_start(void) {
    FILE *f;
    pending=0;
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
    Cvar_RegisterVariable(&early_game_demo_start_1);
    Cmd_AddCommand("aw_scene",scene_command);
    Cmd_AddCommand("aw_demo_start",demo_start);
}
