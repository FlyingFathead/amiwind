/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded local scene links, converted from owned door records. One BSP at a
 * time. This is not inventory, quest persistence or original opening logic.
 */
#include "quakedef.h"
#include "amiwind_version.h"
typedef struct {char source[16],target[16],label[96];vec3_t point,arrival,mins,maxs;float yaw;int bounds;} aw_scene_link_t;
static aw_scene_link_t links[64];static int count,loaded,pending;
static aw_scene_link_t next;
static float health,hand_goal;
static double started;
static cvar_t early_game_demo_start_1={"early_game_demo_start_1","1"};
int AW_Interior(void) {return sv.active && !strcmp(sv.name,"prison");}
static int map_valid(char *name) {return !strcmp(name,"prison") || !strcmp(name,"seyda");}
static void read_links(void) {
    FILE *f;char line[384],extra;aw_scene_link_t r;int n,i,version;
    if(loaded)return;loaded=1;
    if(COM_FOpenFile("scene-doors.txt",&f)>=0 && f) {
        if(!fgets(line,sizeof(line),f)){fclose(f);return;}
        version=!strcmp(line,"AWD2\n")?2:!strcmp(line,"AWD1\n")?1:0;
        if(!version){fclose(f);return;}
        while(count<64 && fgets(line,sizeof(line),f)) {
            memset(&r,0,sizeof(r));
            n=sscanf(line,version==2?"%15s %15s %f %f %f %f %f %f %f %f %f %f %95[^\r\n]":"%15s %15s %f %f %f %f %f %f %f %f %f %f %c",r.source,r.target,
                &r.mins[0],&r.mins[1],&r.mins[2],&r.maxs[0],&r.maxs[1],&r.maxs[2],
                &r.arrival[0],&r.arrival[1],&r.arrival[2],&r.yaw,version==2?r.label:&extra);
            if(n!=(version==2?13:12) || !map_valid(r.source) ||
                (!map_valid(r.target) && !(version==2 && !strcmp(r.target,"-"))))continue;
            if(version==2){for(i=0;r.label[i];i++)if((unsigned char)r.label[i]<32)break;if(r.label[i])continue;}
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
    edict_t *p=svs.clients[0].edict;eval_t *v;
    if(pending)return;next=*link;pending=1;started=Sys_FloatTime();
    health=p->v.health;v=GetEdictFieldValue(p,"aw_hand_goal");hand_goal=v?v->_float:0;
    IN_AWClearButtons();AW_MusicSceneEvent("scene-leave");
    Con_Printf("Loading AmiWind v" AMIWIND_VERSION ": %s...\n",next.target);
    Cbuf_AddText(!strcmp(next.target,"prison")?"map prison\n":"map seyda\n");
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
    sprintf(path,"maps/%s.bsp",links[i].target);
    if(!map_valid(links[i].target) || COM_FOpenFile(path,&f)<0 || !f){
        if(f)fclose(f);AW_UISubtitle("","Interior not found.",3);return 1;
    }
    fclose(f);
    load_scene(&links[i]);return 1;
}
void AW_SceneDraw(void) {
    int i,y;const char *name;extern int scr_copyeverything;
    if(key_dest!=key_game || pending || AW_IntroUse())return;
    i=aimed_door();if(i<0)return;
    y=r_refdef.vrect.y+r_refdef.vrect.height;
    if(vid.height-y<44)return;
    name=links[i].label[0]?links[i].label:!strcmp(links[i].target,"seyda")?"Seyda Neen":"Imperial Prison Ship";
    AW_UIBox(84,y,vid.width-84,44);
    AW_UITextBox(88,y+4,vid.width-92,18,name,-1);
    AW_UITextBox(88,y+22,vid.width-92,18,"E: Enter",-1);
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
    AW_IntroSpawn();
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
    Cmd_AddCommand("aw_door_status",door_status);
    Cvar_RegisterVariable(&early_game_demo_start_1);
    Cmd_AddCommand("aw_scene",scene_command);
    Cmd_AddCommand("aw_demo_start",demo_start);
}
