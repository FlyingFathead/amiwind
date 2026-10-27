/* SPDX-License-Identifier: GPL-2.0-or-later
 * The engine's own door code over a built image (DOOR-ENTRANCE-AUDIT-51, DOOR-BANK-STREAMED-FRAME-51): the scene code
 * (aw_scene.c, aw_world.c, aw_region.c and the rest tests/aga_scene_test.c links) compiled for the host and run on the
 * image's real door banks, open-world directory and maps, read only. tools/door_engine_check.py writes one job line
 * per exterior entrance and reads one result line back:
 *
 *   job:    D <ref> <holder map> <ex> <ey> <ez> <yaw> <pitch> [W <running map> <sx> <sy> <sz> <cx> <cy> <cz>]...
 *           [B <room> <rx> <ry> <rz> <ryaw> <rpitch>]
 *   result: R <ref>\t<scene after the crossing>\t<scene at the door>\t<prompt>\t<name>\t<use>\t<activate>\t<back>\t<note>
 *
 * A region frame's door (W): the game runs the neighbouring frame <running map>; the player stands at S (inside it),
 * then at C (inside the holder's core): the tick streams the crossing (the type 1 window, CHIM's hook always streams
 * here: the case DOOR-BANK-STREAMED-FRAME-51 broke), the running map stays the neighbour and the holder is the logical
 * scene; the first W whose start spot stays in its frame is walked. A town's door (no W): the town runs and no
 * crossing happens. Then the eye E (the holder's own
 * coordinates) with the view yaw/pitch, a tick there (a spot in another frame crosses again, as walking there would),
 * the prompt (AW_SceneDraw), the use key (AW_SceneUse) and a script's Activate (AW_SceneActivate): each queues
 * "map <room>" when the door works. B: the way back, the room running and the eye at its exit (the room's own
 * coordinates): its use must queue the exterior. The wall trace is open (the maps' collision is not loaded here).
 */
#define AW_DOOR_ENGINE_CHECK 1
#include <stdio.h>
static int door_check_open(char *name,FILE **f);
#define main aw_scene_fixture_main
#include "aga_scene_test.c"
#undef main
#include "aw_mappath.h"
#include "aw_region.h"
/* The engine's search paths: the boot disk's id1, then each world volume's id1 (common.c, world/volumes.awv) */
static char data_dirs[8][1024];static int data_count;
static int door_check_open(char *name,FILE **f){
    char path[1400];long size;int i;
    *f=NULL;
    if(!name || strstr(name,"..") || strlen(name)>256)return -1;
    for(i=0;i<data_count && !*f;i++){snprintf(path,sizeof(path),"%s/%s",data_dirs[i],name);*f=fopen(path,"rb");}
    if(getenv("AW_DOOR_CHECK_TRACE"))fprintf(stderr,"open %s: %s\n",name,*f?"yes":"no");
    if(!*f)return -1;
    if(fseek(*f,0,SEEK_END)){fclose(*f);*f=NULL;return -1;}
    size=ftell(*f);rewind(*f);
    return (int)size;
}
/* chim_world.c TownMap: a CHIM town's exterior is its frame map maps/<town>-chim.chim when the image has it */
static const char *town_map(const char *town){
    static char path[MAX_QPATH+16];char name[32];FILE *f=NULL;
    if(!town || !*town || strlen(town)>24)return NULL;
    sprintf(name,"%s-chim",town);AW_MapPath(name,path,sizeof(path));
    if(door_check_open(path,&f)<0 || !f)return NULL;
    fclose(f);return path;
}
static void field(char *out,size_t size,const char *in){
    size_t i,n=0;
    for(i=0;in && in[i] && n+1<size;i++)out[n++]=in[i]=='\t' || in[i]=='\n' || in[i]=='\r'?' ':in[i];
    out[n]=0;if(!n && size>1){out[0]='-';out[1]=0;}
}
static void queued_map(char *out,size_t size){
    char *end;
    if(!strncmp(queued,"map ",4)){field(out,size,queued+4);if((end=strchr(out,' '))!=NULL)*end=0;}
    else field(out,size,"");
}
static edict_t player_edict;static client_t player_client;
static void place(const char *map,const float *origin,float yaw,float pitch){
    edict_t *p=&player_edict;int k;
    AW_SceneCancelTransition();CL_ClearState();
    strncpy(sv.name,map,sizeof(sv.name)-1);sv.name[sizeof(sv.name)-1]=0;
    p->v.movetype=MOVETYPE_WALK;p->v.health=100;
    for(k=0;k<3;k++)p->v.origin[k]=origin[k];
    /* the map's region (a town's sub-cell, load_scene's AW_RegionSelect), as a load at this spot selects it */
    AW_RegionSelect(map,p->v.origin,0);
    {   /* the world model the server runs (a CHIM town's frame map: no legacy region crossings, aw_region.c) */
        const char *model=AW_RegionWorldModel(map,0);char path[MAX_QPATH+16];
        if(!model)model=AW_MapPath(map,path,sizeof(path));
        strncpy(sv.modelname,model,sizeof(sv.modelname)-1);sv.modelname[sizeof(sv.modelname)-1]=0;
    }
    AW_SceneSpawn(p);finish_signon(p);
    cls.state=ca_connected;cls.signon=SIGNONS;key_dest=key_game;
    p->v.movetype=MOVETYPE_WALK;p->v.health=100;p->v.view_ofs[2]=22;
    cl.viewangles[0]=pitch;cl.viewangles[1]=yaw;cl.viewangles[2]=0;
}
static void set_eye(const float *eye,const float *shift,float yaw,float pitch){
    edict_t *p=&player_edict;int k;
    for(k=0;k<3;k++)p->v.origin[k]=eye[k]+shift[k]-p->v.view_ofs[k];
    VectorCopy(p->v.origin,p->v.oldorigin);
    cl.viewangles[0]=pitch;cl.viewangles[1]=yaw;cl.viewangles[2]=0;
}
/* The prompt, the use key and a script's Activate at the eye, each from a clean transition state. */
static void door_actions(unsigned ref,char *prompt,char *name,char *use,char *activate,size_t size){
    hint[0]=object_name[0]=0;AW_SceneDraw();field(prompt,size,hint);field(name,size,object_name);
    door_duration=0;queued[0]=0;notice[0]=0;AW_SceneUse();queued_map(use,size);
    if(!queued[0] && notice[0]){snprintf(use,size,"notice:%.60s",notice);}
    AW_SceneCancelTransition();
    queued[0]=0;AW_SceneActivate(ref);queued_map(activate,size);AW_SceneCancelTransition();
}
int main(int argc,char **argv){
    FILE *jobs;char line[1024],running[32],holder[32],room[32],after[32],at[32];
    char prompt[96],name[96],use[96],activate[96],back[96],bprompt[96],bname[96],bact[96],note[160];
    float s[3],c[3],e[3],r[3],arrival[3],shift[3],zero[3]={0,0,0},yaw,pitch,ryaw,rpitch;unsigned ref;int n,k,region;
    char target[32];
    if(argc<3 || argc>10){fprintf(stderr,"usage: door_engine_check JOBS ID1 [WORLD_ID1...]\n");return 2;}
    for(n=2;n<argc;n++)snprintf(data_dirs[data_count++],sizeof(data_dirs[0]),"%s",argv[n]);
    jobs=fopen(argv[1],"r");if(!jobs){fprintf(stderr,"no job file %s\n",argv[1]);return 2;}
    sv.active=true;svs.maxclients=1;svs.clients=&player_client;player_client.edict=&player_edict;
    sv.model_precache[1]="progs/v_nord.mdl";sv.num_edicts=1;
    cls.state=ca_connected;cls.signon=SIGNONS;key_dest=key_game;
    aw_story.stage=AW_STAGE_RELEASED;AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);
    AW_SceneInit();if(names_option)names_option->value=1;
    vid.width=320;vid.height=200;r_refdef.vrect.height=152;
    target_trace=travel_trace=occluded=all_solid=water_feet=narrow_room=0;
    {extern int (*aw_chim_cross)(const float *origin,int *cx,int *cy);aw_chim_cross=stream_cross_hook;}
    {extern int aw_chim_world;aw_chim_world=1;}   /* a CHIM image: maps/<name>.chim (aw_mappath.c) */
    aw_chim_town_map=town_map;
    while(fgets(line,sizeof(line),jobs)){
        char *b,*w;int walked=0;
        if(line[0]!='D')continue;
        n=sscanf(line,"D %u %31s %f %f %f %f %f",&ref,holder,&e[0],&e[1],&e[2],&yaw,&pitch);
        if(n!=7){printf("R ?\tbad job line\n");continue;}
        region=strstr(line," W ")!=NULL;note[0]=0;
        VectorCopy(zero,shift);
        /* W: a walk in from a neighbouring frame (the first of the candidates whose start spot stays in its frame) */
        for(w=strstr(line," W ");w && !walked;w=strstr(w+3," W ")){
            if(sscanf(w," W %31s %f %f %f %f %f %f",running,&s[0],&s[1],&s[2],&c[0],&c[1],&c[2])!=7)continue;
            /* in the neighbour, then over the border: the streamed crossing */
            place(running,s,yaw,0);
            queued[0]=0;AW_SceneTick();
            if(queued[0] || strcmp(AW_SceneName(),running)){
                snprintf(note,sizeof(note),"the start spot in %s left it",running);continue;}
            note[0]=0;walked=1;
            if(!AW_WorldDestination(running,c,target,arrival) || strcmp(target,holder))
                snprintf(note,sizeof(note),"the crossing point leads to %s, not %s",target,holder);
            else for(k=0;k<3;k++)shift[k]=c[k]-arrival[k];
            VectorCopy(c,player_edict.v.origin);
            queued[0]=0;AW_SceneTick();
            if(queued[0])snprintf(note,sizeof(note),"the crossing loaded a map (%.40s)",queued);
        }
        if(!region)place(holder,e,yaw,pitch);
        field(after,sizeof(after),AW_SceneName());
        /* at the door: a tick there, as walking there would run one */
        set_eye(e,shift,yaw,pitch);
        queued[0]=0;AW_SceneTick();
        if(queued[0] && !note[0])snprintf(note,sizeof(note),"the spot at the door crossed again (%.40s)",queued);
        field(at,sizeof(at),AW_SceneName());
        door_actions(ref,prompt,name,use,activate,sizeof(prompt));
        strcpy(back,"-");
        if((b=strstr(line," B "))!=NULL &&
           sscanf(b," B %31s %f %f %f %f %f",room,&r[0],&r[1],&r[2],&ryaw,&rpitch)==6){
            place(room,r,ryaw,rpitch);set_eye(r,zero,ryaw,rpitch);
            bprompt[0]=0;door_actions(0,bprompt,bname,back,bact,sizeof(back));
            if(strcmp(bprompt,"(Enter: E)"))snprintf(back+strlen(back),sizeof(back)-strlen(back),"|%s",bprompt);
        }
        printf("R %u\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",ref,after,at,prompt,name,use,activate,back,note[0]?note:"-");
        fflush(stdout);
    }
    fclose(jobs);
    return 0;
}
