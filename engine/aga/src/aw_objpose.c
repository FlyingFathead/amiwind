/* SPDX-License-Identifier: GPL-2.0-or-later
 * A script's animation group on a placed object: the group's end pose (MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68; aw_objpose.h).
 * The rules have no engine dependencies outside the host block at the end, so tests/aga_objpose_test.c runs them on the
 * host with AW_OBJPOSE_HOST_TEST defined.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_format.h"      /* Q_sscanf, Q_snprintf: the engine's own (the C library's number reading is not linked) */
#include "aw_objpose.h"

static aw_pose_row_t rows[AW_POSE_ROWS];
static int row_count, table_state;          /* table_state 0: not read, 1: read (or none there) */
static unsigned long plays, swaps, misses, bad_rows;
static struct {int row;double at;} pending[AW_POSE_PENDING];
static int pending_count;
static char room_now[AW_POSE_ROOM+1];
static unsigned long room_serial;
static int room_known;
static aw_objpose_host_t host;
static int (*table_load)(void);             /* the engine's reader of the table (AW_ObjPoseInit), NULL in host tests */

void AW_ObjPoseSetHost(const aw_objpose_host_t *h){
    if(h)host=*h;else memset(&host,0,sizeof(host));
}

/* the reference as the room record holds it (the merged master's number: master index x 2^22 + its number) against one
 * a script names, in either form: that number or the stable id (master index x 2^20 + its number), as chim_room.c
 * RoomRefIs matches them */
static int same_ref(unsigned row,unsigned ref){
    return row==ref || (row>=(1u<<22) && ((((row>>22)<<20)|(row&0x3FFFFFu))==ref));
}

long AW_ObjPoseGroupCode(const char *group){
    unsigned long h=2166136261UL;
    for(;group && *group;group++){
        int c=(unsigned char)*group;
        if(c>='A' && c<='Z')c+='a'-'A';
        h=((h^(unsigned long)c)*16777619UL)&0xFFFFFFFFUL;
    }
    return (long)((h&0x3FFFFFFFUL)|1UL);
}

void AW_ObjPoseFact(unsigned reference,char *out,int size){
    if(out && size>0)Q_snprintf(out,(size_t)size,"amiwind:pose:%u",reference);
}

static int group_is(const char *a,const char *b){
    for(;*a && *b;a++,b++){
        int x=(unsigned char)*a,y=(unsigned char)*b;
        if(x>='A' && x<='Z')x+='a'-'A';
        if(y>='A' && y<='Z')y+='a'-'A';
        if(x!=y)return 0;
    }
    return !*a && !*b;
}

/* one row of the table's text ("R room reference group kind model seconds loop x0 y0 z0 x1 y1 z1"): 1 kept */
static int parse_row(const char *line){
    aw_pose_row_t r;char room[64],group[64],kind[8];unsigned long ref;int model,b[6],k;float seconds,loop;
    if(line[0]!='R' || line[1]!=' ')return 0;
    if(Q_sscanf(line+2,"%63s %lu %63s %7s %d %f %f %d %d %d %d %d %d",room,&ref,group,kind,&model,&seconds,&loop,
              &b[0],&b[1],&b[2],&b[3],&b[4],&b[5])!=13 || strlen(room)>AW_POSE_ROOM || strlen(group)>AW_POSE_GROUP ||
       (kind[0]!='M' && kind[0]!='B' && kind[0]!='H') || kind[1] || seconds<0 || loop<0 ||
       (kind[0]!='H' && model<0) || row_count>=AW_POSE_ROWS){
        bad_rows++;
        return 0;
    }
    memset(&r,0,sizeof(r));
    strcpy(r.room,room);
    for(k=0;group[k];k++)r.group[k]=(char)(group[k]>='A' && group[k]<='Z'?group[k]+'a'-'A':group[k]);
    r.kind=kind[0];r.ref=(unsigned)ref;r.model=kind[0]=='H'?-1:model;r.seconds=seconds;r.loop=loop;
    for(k=0;k<6;k++)r.box[k]=(short)b[k];
    rows[row_count++]=r;
    return 1;
}

static void table_clear(void){
    row_count=0;bad_rows=0;table_state=1;
}

int AW_ObjPoseParse(const char *text){
    const char *p=text,*e;char line[160];
    table_clear();
    if(!text || strncmp(text,AW_POSE_HEADER,strlen(AW_POSE_HEADER)) ||
       (text[strlen(AW_POSE_HEADER)]!='\n' && text[strlen(AW_POSE_HEADER)]!='\r'))return -1;
    while(*p){
        size_t n;
        e=strchr(p,'\n');
        n=e?(size_t)(e-p):strlen(p);
        if(n<sizeof(line)){
            memcpy(line,p,n);line[n]=0;
            if(n && line[n-1]=='\r')line[n-1]=0;
            if(line[0]=='R')parse_row(line);
        }else bad_rows++;
        if(!e)break;
        p=e+1;
    }
    return row_count;
}

static void table_ready(void){
    if(table_state)return;
    table_clear();
    if(table_load)table_load();
}

static int find(unsigned reference,const char *group){
    int i,any=-1;
    table_ready();
    for(i=0;i<row_count;i++){
        if(!same_ref(rows[i].ref,reference) || !group_is(rows[i].group,group))continue;
        if(room_known && !strcmp(rows[i].room,room_now))return i;
        if(any<0)any=i;
    }
    return any;
}

static void apply(int i){
    if(host.swap && host.swap(rows[i].ref,rows[i].kind=='H'?-1:rows[i].model,rows[i].box)>0)swaps++;
}

int AW_ObjPosePlay(unsigned reference,const char *group,int count,int mode){
    int i,k;char id[40];double now,at;
    if(!reference || !group){misses++;return 0;}
    if((i=find(reference,group))<0){misses++;return 0;}
    /* the end state is decided now: kept at once, so a save or a door taken before the group ends keeps it */
    AW_ObjPoseFact(rows[i].ref,id,sizeof(id));
    if(host.set)host.set(id,rows[i].kind=='B'?0:AW_ObjPoseGroupCode(rows[i].group));
    plays++;
    if(!room_known || strcmp(rows[i].room,room_now))return 1;     /* not in the loaded room: its load applies the fact */
    now=host.now?host.now():0;at=now;
    for(k=0;k<pending_count && !same_ref(rows[pending[k].row].ref,reference);k++)
        ;
    /* mode 0: after the group the object still plays (OpenMW playGroup: queued behind it); 1 and 2: at once */
    if(!mode && k<pending_count && pending[k].at>now)at=pending[k].at;
    at+=rows[i].seconds+(count>0?(double)count*rows[i].loop:0.0);
    if(k==pending_count){
        if(pending_count==AW_POSE_PENDING){apply(pending[0].row);k=0;}   /* full: the oldest ends now */
        else pending_count++;
    }
    pending[k].row=i;pending[k].at=at;
    return 1;
}

void AW_ObjPoseTick(void){
    char name[AW_POSE_ROOM+1];unsigned long serial=0;int i;double now;
    if(!host.loaded || !host.loaded(name,sizeof(name),&serial)){room_known=0;pending_count=0;return;}
    if(!room_known || serial!=room_serial || strcmp(name,room_now)){
        /* a room that has just loaded: its placements as the facts left them */
        room_known=1;room_serial=serial;
        strncpy(room_now,name,AW_POSE_ROOM);room_now[AW_POSE_ROOM]=0;
        pending_count=0;
        table_ready();
        for(i=0;i<row_count;i++){
            char id[40];long v;
            if(rows[i].kind=='B' || strcmp(rows[i].room,room_now))continue;
            AW_ObjPoseFact(rows[i].ref,id,sizeof(id));
            v=host.get?host.get(id):0;
            if(v && v==AW_ObjPoseGroupCode(rows[i].group))apply(i);
        }
    }
    if(!pending_count)return;
    now=host.now?host.now():0;
    for(i=0;i<pending_count;){
        if(pending[i].at>now){i++;continue;}
        apply(pending[i].row);
        pending[i]=pending[--pending_count];
    }
}

void AW_ObjPoseReset(void){
    pending_count=0;room_known=0;room_now[0]=0;room_serial=0;
}

void AW_ObjPoseCounts(unsigned long out[4]){
    table_ready();
    out[0]=(unsigned long)row_count;out[1]=plays;out[2]=swaps;out[3]=misses;
}

#ifndef AW_OBJPOSE_HOST_TEST
/* ---- the engine's side ---- */
#include "quakedef.h"
#include "aw_reset.h"
#include "aw_state.h"

/* chim/chim_room.c (declared here, not in chim.h, which a build stage reads for CHIM's version) */
int ChimRoom_Loaded(char *name,int size,unsigned long *serial);
int ChimRoom_PoseModel(unsigned reference,int model,const short *box);

static long fact_get(const char *id){return (long)AW_StateGet(&aw_state,AW_GLOBAL,id);}
static void fact_set(const char *id,long value){AW_StateSet(&aw_state,AW_GLOBAL,id,(int32_t)value);}
static double game_now(void){return sv.time;}
static int read_table(void){
    FILE *f=NULL;char line[160];int first=1;
    if(COM_FOpenFile(AW_POSE_TABLE,&f)<0 || !f)return -1;     /* an image without CHIM rooms: no poses */
    while(fgets(line,sizeof(line),f)){
        size_t n=strlen(line);
        while(n && (line[n-1]=='\n' || line[n-1]=='\r'))line[--n]=0;
        if(first){first=0;if(strcmp(line,AW_POSE_HEADER)){bad_rows++;break;}continue;}
        if(line[0]=='R')parse_row(line);
    }
    fclose(f);
    if(bad_rows)Con_Printf("Object poses: %lu rows of %s left out (malformed or past %d).\n",bad_rows,AW_POSE_TABLE,
                           AW_POSE_ROWS);
    return row_count;
}
static void objpose_reset(int new_game){(void)new_game;AW_ObjPoseReset();}
void AW_ObjPoseInit(void){
    aw_objpose_host_t h;
    memset(&h,0,sizeof(h));
    h.loaded=ChimRoom_Loaded;h.swap=ChimRoom_PoseModel;h.get=fact_get;h.set=fact_set;h.now=game_now;
    AW_ObjPoseSetHost(&h);
    table_load=read_table;
    aw_objpose_tick=AW_ObjPoseTick;
    AW_ResetRegister("object poses",objpose_reset,NULL);
}
#else
void (*aw_objpose_tick)(void);      /* aw_scene.c's in the engine */
void AW_ObjPoseInit(void){aw_objpose_tick=AW_ObjPoseTick;}
#endif
