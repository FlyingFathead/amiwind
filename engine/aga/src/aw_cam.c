/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg cam: named camera marks (docs/CAMERA_MARKS.md). One console command,
 * aw_cam, reached through the on-disk dbg catalogue:
 *
 *   dbg cam mark NAME     save the current shot as a private mark
 *   dbg cam recall NAME   restore a public or private mark
 *   dbg cam list          the marks of both files
 *
 * Public marks: camera-marks.txt in the game data (config/camera-marks.txt in
 * the repository: the benchmark cameras, bug-evidence spots). Private marks:
 * saves/camera-marks.txt in the game folder, written by dbg cam mark; a public
 * name cannot be taken by a private mark. Both files are read on the command
 * only, line by line (nothing resident but this code). The line format is in
 * aw_cam_rules.c. A recall travels as dbg tp does (the same map load, arrival
 * placement and checks; nothing else is touched on arrival) or, for a mark on a
 * map, places the camera exactly there in noclip; the camera modes' detached
 * player (no enemy notices, no triggers) is later work (docs/PLAN-v0.0.42.md 1.2c).
 * The names mark and recall live under "cam" so they never read as the game's
 * Mark and Recall spells. */
#include "quakedef.h"
#include <errno.h>
#ifdef AMIGA
#include <proto/dos.h>
#else
#include <sys/stat.h>
#endif
#include "aw_cam.h"
#include "aw_clock.h"
#include "aw_world.h"
#include "aw_view.h"
#include "aw_inspect.h"

extern cvar_t aw_drawdistance;
extern void AW_SetDrawDistance(int value);

#define PUBLIC_FILE "camera-marks.txt"

static int read_line(FILE *f,int *left,char *line) {
    int n=0,c;
    if(*left<=0)return 0;
    while(*left>0){
        c=fgetc(f);
        if(c==EOF){if(!n)return 0;break;}
        --*left;
        if(c=='\n')break;
        if(c=='\r')continue;
        if(n>=AW_CAM_LINE-1)return -1;
        line[n++]=(char)c;
    }
    line[n]=0;return 1;
}
static int private_path(char *out,int size,const char *leaf) {
    int n=snprintf(out,size,"%s/saves%s%s",com_gamedir,leaf?"/":"",leaf?leaf:"");
    return n>0 && n<size;
}
/* A marks file: PUBLIC from the game data (the member size of a PAK entry),
 * else the private file. NULL when absent; *bad when its header is wrong. */
static FILE *open_marks(int public_file,int *left,int *bad) {
    FILE *f=NULL;char line[AW_CAM_LINE],path[256];
    *bad=0;
    if(public_file){*left=COM_FOpenFile(PUBLIC_FILE,&f);if(!f)return NULL;}
    else{
        if(!private_path(path,sizeof(path),PUBLIC_FILE) || !(f=fopen(path,"rb")))return NULL;
        *left=AW_CAM_FILE_BYTES;
    }
    if(*left>AW_CAM_FILE_BYTES || read_line(f,left,line)!=1 || strcmp(line,AW_CAM_MAGIC)){
        fclose(f);*bad=1;return NULL;
    }
    return f;
}
static const char *file_label(int public_file){return public_file?"public marks (" PUBLIC_FILE ")":"private marks (saves/" PUBLIC_FILE ")";}
/* NAME in one file: 1 found, 0 not there, -1 the file is invalid. */
static int find_in(int public_file,const char *name,aw_cam_mark_t *m) {
    FILE *f;int left,bad,status,parsed,found=0;char line[AW_CAM_LINE];
    f=open_marks(public_file,&left,&bad);
    if(!f)return bad?-1:0;
    while((status=read_line(f,&left,line))>0){
        parsed=AW_CamParse(line,m);
        if(parsed<0){status=-1;break;}
        if(parsed && AW_CamSameName(m->name,name)){found=1;break;}
    }
    if(!found && status==0 && !feof(f) && left<=0 && !public_file)status=-1;  /* a private file over the limit */
    fclose(f);
    if(status<0 && !found){Con_Printf("Camera marks: %s has an invalid line or is too large.\n",file_label(public_file));return -1;}
    return found;
}
static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected || !svs.clients){
        Con_Printf("Camera marks: start the local scene first.\n");return NULL;
    }
    return svs.clients[0].edict;
}
static void describe(const aw_cam_mark_t *m,const char *where) {
    char line[AW_CAM_LINE];
    if(!AW_CamFormat(m,line,sizeof(line)))return;
    Con_Printf(" %s%s\n",line,where);
}
static void list_command(void) {
    FILE *f;int file,left,bad,status,shown=0;char line[AW_CAM_LINE];aw_cam_mark_t m;
    for(file=1;file>=0;file--){
        f=open_marks(file,&left,&bad);
        if(!f){if(bad)Con_Printf("Camera marks: %s has an invalid header or is too large.\n",file_label(file));continue;}
        Con_Printf("%s: name|place|position|yaw pitch|time|headlamp|fog|note\n",file_label(file));
        while((status=read_line(f,&left,line))>0){
            status=AW_CamParse(line,&m);
            if(status<0){Con_Printf("Camera marks: invalid line in %s.\n",file_label(file));break;}
            if(status){describe(&m,"");shown++;}
        }
        fclose(f);
    }
    if(!shown)Con_Printf("No camera marks. dbg cam mark NAME saves the current shot.\n");
}
/* 0 = not recalled, 1 = in place, 2 = travelling */
static int recall_command(const char *name) {
    aw_cam_mark_t m;int found,result;char command[32];
    if(!AW_CamValidName(name)){Con_Printf("Usage: dbg cam recall NAME (dbg cam list shows the marks)\n");return 0;}
    found=find_in(1,name,&m);
    if(found==0)found=find_in(0,name,&m);
    if(found<=0){if(!found)Con_Printf("No camera mark \"%s\"; dbg cam list shows the marks.\n",name);return 0;}
    if(!player())return 0;
    /* As the benchmark method does: the clock held, then the time, the headlamp
     * and the fog distance, then the travel. */
    if(m.time>=0){
        Cvar_SetValue("aw_daynightcycle",0);
        snprintf(command,sizeof(command),"aw_set_time %04d",m.time);
        Cmd_ExecuteString(command,src_command);
    }
    if(m.headlamp>=0)Cvar_SetValue("aw_headlamp",m.headlamp);
    if(m.fog>=0)AW_SetDrawDistance(m.fog);
    result=AW_SceneShot(m.global,m.map,m.point,m.has_z,m.yaw,m.pitch);
    if(!result){Con_Printf("Camera mark %s: travel unavailable here (no map on this disk holds it, or play is restricted); position unchanged.\n",m.name);return 0;}
    Con_Printf("Camera mark %s%s\n",m.name,result==1?": in place.":": travelling.");
    if(m.note[0])Con_Printf(" %s\n",m.note);
    return result;
}
static int make_folder(const char *directory) {
#ifdef AMIGA
    BPTR lock=CreateDir((char *)directory);
    if(lock){UnLock(lock);return 0;}
    return IoErr()==ERROR_OBJECT_EXISTS?0:-1;
#else
    return mkdir(directory,0777)==0 || errno==EEXIST?0:-1;
#endif
}
/* The saves folder of the game, created when missing (also for timedemo results, aw_rcount.c). */
int AW_CamSavesFolder(char *out,int size) {
    return private_path(out,size,NULL) && make_folder(out)>=0;
}
/* The shot now, as a mark on this map at the exact point. */
static int current_shot(edict_t *p,const char *name,aw_cam_mark_t *m) {
    int year,month,day,hour,minute;float yaw,pitch,global[3];
    memset(m,0,sizeof(*m));
    Q_strcpy_bounded(m->name,name,sizeof(m->name));
    if(strlen(sv.name)>=sizeof(m->map))return 0;
    strcpy(m->map,sv.name);
    VectorCopy(p->v.origin,m->point);m->has_z=1;
    yaw=cl.viewangles[1]-360.0f*(float)floor(cl.viewangles[1]/360.0f);
    yaw=(float)floor(yaw*100.0f+.5f)/100.0f;if(yaw>=360)yaw=0;
    pitch=cl.viewangles[0];if(pitch>80)pitch=80;if(pitch<-80)pitch=-80;
    m->yaw=yaw;m->pitch=pitch;
    if(AW_ClockEnsure()){AW_ClockDate(&year,&month,&day,&hour,&minute);m->time=hour*100+minute;}else m->time=-1;
    m->headlamp=Cvar_VariableValue("aw_headlamp")!=0;
    m->fog=(int)aw_drawdistance.value;if(m->fog<100)m->fog=100;if(m->fog>4096)m->fog=4096;
    if(AW_WorldToSource(sv.name,p->v.origin,global))
        snprintf(m->note,sizeof(m->note),"marked in game; global %ld %ld %ld",(long)global[0],(long)global[1],(long)global[2]);
    else snprintf(m->note,sizeof(m->note),"marked in game");
    return 1;
}
static void mark_command(const char *name) {
    edict_t *p;aw_cam_mark_t m,old;FILE *f,*out;int left,bad,status,used=0,n,replaced=0;
    char line[AW_CAM_LINE],path[256],*kept;
    if(!AW_CamValidName(name)){Con_Printf("Usage: dbg cam mark NAME (1..31 of A-Z a-z 0-9 _ - .)\n");return;}
    status=find_in(1,name,&old);
    if(status<0)return;
    if(status){Con_Printf("\"%s\" is a public camera mark; choose another name.\n",name);return;}
    if(!(p=player()))return;
    if(!current_shot(p,name,&m) || !AW_CamFormat(&m,line,sizeof(line))){Con_Printf("Camera mark: this shot cannot be written.\n");return;}
    kept=malloc(AW_CAM_FILE_BYTES);if(!kept){Con_Printf("Camera mark: no memory.\n");return;}
    kept[0]=0;
    f=open_marks(0,&left,&bad);
    if(!f && bad){free(kept);Con_Printf("Camera mark: the private marks file is invalid; not overwritten.\n");return;}
    if(f){
        char row[AW_CAM_LINE];
        while((status=read_line(f,&left,row))>0){
            if(AW_CamParse(row,&old)==1 && AW_CamSameName(old.name,name)){replaced=1;continue;}
            n=(int)strlen(row);
            if(used+n+2>=AW_CAM_FILE_BYTES-AW_CAM_LINE-8){status=-1;break;}
            memcpy(kept+used,row,n);used+=n;kept[used++]='\n';kept[used]=0;
        }
        fclose(f);
        if(status<0){free(kept);Con_Printf("Camera mark: the private marks file is invalid or full; not overwritten.\n");return;}
    }
    /* The whole file was read above and is written again in one go (the C
     * library's rename is not linked on the Amiga). */
    if(!private_path(path,sizeof(path),NULL) || make_folder(path)<0 || !private_path(path,sizeof(path),PUBLIC_FILE)){
        free(kept);Con_Printf("Camera mark: cannot create the saves folder.\n");return;
    }
    out=fopen(path,"wb");
    if(!out){free(kept);Con_Printf("Camera mark: cannot write saves/" PUBLIC_FILE ".\n");return;}
    status=fprintf(out,"%s\n%s%s\n",AW_CAM_MAGIC,kept,line)>0;
    status=fclose(out)==0 && status;
    free(kept);
    if(!status){Con_Printf("Camera mark: cannot write saves/" PUBLIC_FILE ".\n");return;}
    Con_Printf("Camera mark %s %s: %s\n",name,replaced?"replaced":"saved",line);
}
/* ---- dbg cam orbit (the camera itself: aw_view.c) ---- */
#define ORBIT_RATE 36           /* degrees a second: one orbit in 10 s */
#define ORBIT_USAGE "Usage: dbg cam orbit [photo] [speed DEG] [ref N | mark NAME] / dbg cam orbit speed DEG / dbg cam orbit off\n"
static int number_arg(const char *text,double low,double high,float *out) {
    char *end;double value;const char *p;
    if(!*text || strlen(text)>16)return 0;
    for(p=text;*p;p++)if(!((*p>='0' && *p<='9') || *p=='-' || *p=='+' || *p=='.'))return 0;
    value=Q_strtod(text,&end);
    if(end==text || *end || !(value>=low && value<=high))return 0;
    *out=(float)value;return 1;
}
/* The live edict with original reference REF (the converter's aw_ref field). */
static int ref_target(long ref,int *number,vec3_t focal) {
    int i;edict_t *e;eval_t *v;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");
        if(!v || (long)v->_float!=ref)continue;
        *number=i;
        if(i<cl.num_entities && AW_InspectFrameCentre(&cl_entities[i],focal))return 1;
        VectorAdd(e->v.absmin,e->v.absmax,focal);VectorScale(focal,.5f,focal);return 1;
    }
    return 0;
}
static void orbit_command(int argc) {
    char mark[AW_CAM_NAME];int i,photo=0,have_ref=0,have_mark=0,off=0,speed=0,number=0,result;float rate=ORBIT_RATE,ref=0;vec3_t focal;
    mark[0]=0;
    for(i=2;i<argc;i++){
        char *w=Cmd_Argv(i);
        if(!Q_strcasecmp(w,"photo"))photo=1;
        else if(!Q_strcasecmp(w,"off") || !Q_strcasecmp(w,"stop"))off=1;
        else if(!Q_strcasecmp(w,"speed") && i+1<argc && number_arg(Cmd_Argv(i+1),-360,360,&rate)){i++;speed=1;}
        else if(!Q_strcasecmp(w,"ref") && i+1<argc && number_arg(Cmd_Argv(i+1),1,16777216,&ref)){i++;have_ref=1;}
        else if(!Q_strcasecmp(w,"mark") && i+1<argc && AW_CamValidName(Cmd_Argv(i+1))){Q_strcpy_bounded(mark,Cmd_Argv(i+1),sizeof(mark));i++;have_mark=1;}
        else{Con_Printf(ORBIT_USAGE);return;}
    }
    if(off){if(AW_ViewOrbitActive())AW_ViewOrbitEnd(1);else{AW_ViewOrbitEnd(0);Con_Printf("Orbit: not running.\n");}return;}
    if((have_ref && have_mark) || (off && argc>3)){Con_Printf(ORBIT_USAGE);return;}
    if(speed && argc==4 && AW_ViewOrbitActive()){AW_ViewOrbitSpeed(rate);return;}
    if(!player())return;
    if(have_mark){
        /* the mark's shot first (its travel, clock, headlamp, fog); then its subject */
        if(AW_ViewOrbitActive())AW_ViewOrbitEnd(0);
        result=recall_command(mark);
        if(!result)return;
        AW_ViewOrbitPending(photo,rate);
        Con_Printf("Orbit: starts on what the shot shows once it has arrived.\n");return;
    }
    if(have_ref){
        if(!ref_target((long)ref,&number,focal)){Con_Printf("Orbit: no entity with reference %ld on this map.\n",(long)ref);return;}
    }else{
        result=AW_InspectTarget(&number,focal);
        if(result<0){Con_Printf("Orbit: the camera is inside collision; move the view.\n");return;}
        if(!result){Con_Printf("Orbit: nothing under the crosshair within reach.\n");return;}
    }
    if(AW_ViewOrbitStart(number,focal,photo,rate))
        Con_Printf("Orbit around %s%s.\n",number?"entity ":"the point under the crosshair",number?va("%ld",(long)number):"");
}
static void cam_command(void) {
    char sub[16],name[AW_CAM_NAME];int n=Cmd_Argc();
    if(n<2){Con_Printf("Usage: dbg cam mark NAME / dbg cam recall NAME / dbg cam list / dbg cam orbit ...\n");return;}
    Q_strcpy_bounded(sub,Cmd_Argv(1),sizeof(sub));
    name[0]=0;if(n>2){if(strlen(Cmd_Argv(2))>=sizeof(name))name[0]='?',name[1]=0;else strcpy(name,Cmd_Argv(2));}
    if(!Q_strcasecmp(sub,"orbit")){orbit_command(n);return;}
    if(!Q_strcasecmp(sub,"list") && n==2)list_command();
    else if(!Q_strcasecmp(sub,"recall") && n==3)(void)recall_command(name);
    else if(!Q_strcasecmp(sub,"mark") && n==3)mark_command(name);
    else Con_Printf("Usage: dbg cam mark NAME / dbg cam recall NAME / dbg cam list / dbg cam orbit ...\n");
}
void AW_CamInit(void) {Cmd_AddCommand("aw_cam",cam_command);}
