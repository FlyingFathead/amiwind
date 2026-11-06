/* SPDX-License-Identifier: GPL-2.0-or-later
 * The gameplay recorder, slice 1 (GAME-RECORDER-61; docs/GAME_RECORDER.md).
 *
 * dbg recorder arms it; Ctrl+R (or dbg recorder start) takes a save of the game as it is (the character, the
 * inventory, the world change list: aw_save.c AW_SaveEncodeNow), loads that save at once, and records from the first
 * frame in play after the load, so a recording and its replay both start from the same fresh load. Each frame keeps
 * its length, the move and view the client sent, the key events (every key: movement, E, menus, console typing) and
 * the remote command lines (headless test sessions), keyed to the frame number, never to the clock; the random
 * generator is seeded at frame 0 and its seed kept. Checkpoints every 5 s of game time hold the player's position,
 * health, place and a hash of the world change list. Everything stays in RAM and is written once, when the recording
 * stops, to recordings/NNN.awr in the game folder (no disk write during play). dbg recorder play FILE loads the
 * recording's save and replays the frames: the recorded keys go through Key_Event as typed, the recorded move, view and
 * frame length replace the live ones, the live keys are taken (Ctrl+R stops), and every checkpoint is compared.
 *
 * The version line at the top of the screen reads "AmiWind <version> (RECORDING)" or "(PLAYBACK)" (the maintainer's
 * decision, 6 November 2026); at the stop it names the file.
 *
 * File (little-endian): "AWR1", the build (32 bytes), u32 seed, profile, sequence, frames, checkpoints, save bytes,
 * stream bytes, then the save, the frame stream and the checkpoints. A frame: u8 flags, u16 length (1/10000 s);
 * with F_MOVE i16 forward, side, up and i16 pitch, yaw, roll (65536 to the turn); with F_KEYS u8 count and per event
 * u8 key, u8 down; with F_LINE u16 length and the text. A checkpoint (48 bytes): u32 frame, f32 x, y, z, health, u32
 * change-list hash, the place's name (24 bytes).
 *
 * Budget (docs/GAME_RECORDER.md "Budget"): off, one test per hook and frame and 1.2 KB of static data; recording, 3 to
 * 15 bytes a frame plus 2 per key event in a RAM buffer that grows from 32 KB up to 2 MB, a 48-byte checkpoint every 5 s
 * and the starting save held from the start to the stop.
 */
#include "quakedef.h"
#include "amiwind_version.h"
#include "aw_save.h"
#include "aw_ledger.h"
#include "aw_world.h"
#include "aw_tryalloc.h"
#include <ctype.h>
#ifdef AMIGA
#include <proto/dos.h>
#else
#include <sys/stat.h>
#endif

enum {IDLE,REC_START,RECORDING,PLAY_START,PLAYING};
#define FRAME_UNIT 10000.0        /* a frame's length in 1/10000 s */
#define CHECK_EVERY 5.0           /* seconds of game time between checkpoints */
#define STREAM_START 32768
#define STREAM_MAX 2097152        /* about three hours at 10 frames a second */
#define CHECKS_MAX 3600           /* five hours of checkpoints */
#define CHECK_BYTES 48
#define CELL_BYTES 24
#define EVENTS_MAX 32             /* key events kept in one frame */
#define LINE_MAX 1024             /* command line text kept in one frame */
#define HEAD_BYTES 64
#define F_MOVE 1
#define F_KEYS 2
#define F_LINE 4
/* held only while recording or playing back (dbg recorder), freed at the stop */
AW_RESIDENT_GROWS("recorder frames (GAME-RECORDER-61)",STREAM_MAX,1);
AW_RESIDENT_GROWS("recorder checkpoints (GAME-RECORDER-61)",CHECKS_MAX,CHECK_BYTES);

typedef struct {uint32_t frame;float origin[3],health;uint32_t changes;char cell[CELL_BYTES];} check_t;
static int mode,armed,taken_r,real_ctrl,injecting;
static unsigned char *stream,*file;           /* the frames: written while recording; a playback's file */
static unsigned long used,capacity,cursor,stream_bytes;
static check_t *checks;
static int check_count,check_capacity,check_next,matched,diverged;
static unsigned char *save;                   /* the starting save while recording (the file's while playing) */
static int save_bytes;
static uint32_t seed,save_profile,save_sequence;
static unsigned long frames,frame_count,dropped_keys,dropped_lines;
static double game_time,next_check,message_until,diverged_time;
static struct {int open,flags,keys,line;unsigned dt;short move[3],angle[3];unsigned char key[EVENTS_MAX][2];} cur;
static char line[LINE_MAX+2],message[96],name[48],diverged_cell[CELL_BYTES];

static void say(const char *text,double seconds)
{
    strncpy(message,text,sizeof(message)-1);message[sizeof(message)-1]=0;message_until=realtime+seconds;
}
static int room(unsigned long n)
{
    unsigned char *grown;unsigned long want=capacity?capacity:STREAM_START;
    if(used+n<=capacity)return 1;
    while(want<used+n)want*=2;
    if(want>STREAM_MAX || !(grown=(unsigned char *)AW_TryRealloc(stream,want)))return 0;
    stream=grown;capacity=want;return 1;
}
static void put8(unsigned v){stream[used++]=(unsigned char)v;}
static void put16(unsigned v){put8(v&255);put8((v>>8)&255);}
static void le32(unsigned char *p,uint32_t v){p[0]=v&255;p[1]=(v>>8)&255;p[2]=(v>>16)&255;p[3]=(v>>24)&255;}
static uint32_t get32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t float_bits(float f){uint32_t v;memcpy(&v,&f,4);return v;}
static float bits_float(uint32_t v){float f;memcpy(&f,&v,4);return f;}
static uint32_t fnv(uint32_t h,uint32_t v)
{
    int i;for(i=0;i<4;i++){h^=(v>>(8*i))&255;h*=16777619U;}
    return h;
}
/* the world change list (aw_ledger.h) in one number: its rows and the size of every table */
static uint32_t changes_hash(void)
{
    uint32_t h=2166136261U;int i;const aw_ledger_row_t *r;const aw_ledger_actor_t *a;
    for(i=0;i<aw_ledger.count;i++){
        r=&aw_ledger.row[i];
        h=fnv(h,r->key);h=fnv(h,(uint32_t)r->fields|(uint32_t)r->lock<<8|(uint32_t)r->at<<16);h=fnv(h,(uint32_t)r->where);
    }
    for(i=0;i<aw_ledger.actor_count;i++){
        a=&aw_ledger.actor[i];
        h=fnv(h,a->key);h=fnv(h,(uint32_t)a->dead|(uint32_t)a->moved<<8|(uint32_t)a->fight<<16|(uint32_t)a->follow<<24);
    }
    h=fnv(h,(uint32_t)aw_ledger.stolen_count);h=fnv(h,(uint32_t)aw_ledger.content_count);h=fnv(h,(uint32_t)aw_ledger.rank_count);
    for(i=0;i<AW_LEDGER_TABLES;i++)h=fnv(h,(uint32_t)aw_ledger.value_count[i]);
    h=fnv(h,(uint32_t)aw_ledger.fact_count);h=fnv(h,(uint32_t)aw_ledger.local_count);h=fnv(h,(uint32_t)aw_ledger.script_count);
    return h;
}
static void capture(check_t *c)
{
    edict_t *p=svs.clients[0].edict;
    memset(c,0,sizeof(*c));c->frame=(uint32_t)frames;
    VectorCopy(p->v.origin,c->origin);c->health=p->v.health;c->changes=changes_hash();
    strncpy(c->cell,AW_SceneName(),CELL_BYTES-1);
}
static int add_check(void)
{
    check_t *grown;int want;
    if(check_count==check_capacity){
        want=check_capacity?check_capacity*2:64;
        if(want>CHECKS_MAX || !(grown=(check_t *)AW_TryRealloc(checks,(unsigned long)want*sizeof(check_t))))return 0;
        checks=grown;check_capacity=want;
    }
    capture(&checks[check_count++]);return 1;
}
/* in play after a load: the same moment for a recording and its replay */
static int ready(void)
{
    return sv.active && cls.state==ca_connected && cls.signon==SIGNONS && svs.clients && svs.clients[0].edict &&
        !AW_SaveLoadPending() && key_dest==key_game && !AW_LoadingScreen();
}
static void release(void)
{
    if(!file)free(stream);      /* a playback's frames lie inside its file buffer */
    free(file);free(checks);free(save);
    stream=file=save=NULL;checks=NULL;used=capacity=cursor=stream_bytes=0;check_count=check_capacity=0;save_bytes=0;
    cur.open=0;mode=IDLE;
}
static void minutes(double t,long *m,long *s){long n=(long)t;*m=n/60;*s=n%60;}
static short move_code(float v){return v>32767?32767:v<-32768?-32768:(short)v;}
static short angle_code(float a)
{
    double v;a=anglemod(a);if(a>=180)a-=360;
    v=a*65536.0/360.0;v+=v<0?-0.5:0.5;
    return v>32767?32767:v<-32768?-32768:(short)v;
}
static float angle_value(short v,int yaw)
{
    float a=(float)(v*360.0/65536.0);
    return yaw && a<0?a+360:a;
}
static int commit(void)
{
    unsigned long n=3+((cur.flags&F_MOVE)?12:0)+((cur.flags&F_KEYS)?1+2*cur.keys:0)+((cur.flags&F_LINE)?2+cur.line:0);
    int i;
    if(!room(n))return 0;
    put8(cur.flags);put16(cur.dt);
    if(cur.flags&F_MOVE){for(i=0;i<3;i++)put16((unsigned short)cur.move[i]);for(i=0;i<3;i++)put16((unsigned short)cur.angle[i]);}
    if(cur.flags&F_KEYS){put8(cur.keys);for(i=0;i<cur.keys;i++){put8(cur.key[i][0]);put8(cur.key[i][1]);}}
    if(cur.flags&F_LINE){put16(cur.line);memcpy(stream+used,line,cur.line);used+=cur.line;}
    frames++;cur.open=0;return 1;
}
static int make_folder(const char *folder)
{
#ifdef AMIGA
    BPTR lock=CreateDir((char *)folder);
    if(lock)UnLock(lock);
    return 1;
#else
    mkdir(folder,0777);return 1;
#endif
}
static void encode_check(unsigned char *p,const check_t *c)
{
    int i;le32(p,c->frame);
    for(i=0;i<3;i++)le32(p+4+4*i,float_bits(c->origin[i]));
    le32(p+16,float_bits(c->health));le32(p+20,c->changes);memcpy(p+24,c->cell,CELL_BYTES);
}
static void decode_check(const unsigned char *p,check_t *c)
{
    int i;c->frame=get32(p);
    for(i=0;i<3;i++)c->origin[i]=bits_float(get32(p+4+4*i));
    c->health=bits_float(get32(p+16));c->changes=get32(p+20);memcpy(c->cell,p+24,CELL_BYTES);c->cell[CELL_BYTES-1]=0;
}
/* the recording into recordings/NNN.awr (the first free number): one write at the stop */
static int write_file(char *shown,int capacity_shown)
{
    char folder[MAX_OSPATH+16],path[MAX_OSPATH+32];unsigned char head[HEAD_BYTES],*packed;FILE *f;int n,i,ok;
    snprintf(folder,sizeof(folder),"%s/recordings",com_gamedir);make_folder(folder);
    for(n=1;n<1000;n++){
        snprintf(path,sizeof(path),"%s/%03d.awr",folder,n);
        if(!(f=fopen(path,"rb")))break;
        fclose(f);
    }
    if(n==1000)return 0;
    memset(head,0,sizeof(head));memcpy(head,"AWR1",4);strncpy((char *)head+4,AMIWIND_VERSION,31);
    le32(head+36,seed);le32(head+40,save_profile);le32(head+44,save_sequence);le32(head+48,(uint32_t)frames);
    le32(head+52,(uint32_t)check_count);le32(head+56,(uint32_t)save_bytes);le32(head+60,(uint32_t)used);
    packed=(unsigned char *)AW_TryMalloc((unsigned long)check_count*CHECK_BYTES+1);
    if(!packed)return 0;
    for(i=0;i<check_count;i++)encode_check(packed+i*CHECK_BYTES,&checks[i]);
    if(!(f=fopen(path,"wb"))){free(packed);return 0;}
    ok=fwrite(head,1,HEAD_BYTES,f)==HEAD_BYTES && fwrite(save,1,save_bytes,f)==(size_t)save_bytes &&
       (!used || fwrite(stream,1,used,f)==used) &&
       (!check_count || fwrite(packed,1,(size_t)check_count*CHECK_BYTES,f)==(size_t)check_count*CHECK_BYTES);
    if(fclose(f))ok=0;
    free(packed);
    snprintf(shown,capacity_shown,"recordings/%03d.awr",n);
    return ok;
}
static void record_stop(const char *why)
{
    char shown[40],text[96];long m,s;
    if(mode==REC_START){release();Con_Printf("Recorder: stopped before the recording started; nothing saved.\n");say("Recording cancelled",5);return;}
    /* the open frame is left out: the state is the one after the last kept frame, as its checkpoint says */
    cur.open=0;
    if(!add_check())Con_Printf("Recorder: no room for the last checkpoint.\n");
    minutes(game_time,&m,&s);
    if(write_file(shown,sizeof(shown))){
        Con_Printf("Recorder: saved %s (%lu frames, %ld:%02ld of game time, %d checkpoints, %lu bytes of frames, %d bytes of save; %s).\n",
                   shown,frames,m,s,check_count,used,save_bytes,why);
        snprintf(text,sizeof(text),"Saved %s",shown);say(text,8);
    }else{
        Con_Printf("Recorder: the recording could not be written (recordings folder full or not writable).\n");say("Recording NOT saved",8);
    }
    if(dropped_keys || dropped_lines)
        Con_Printf("Recorder: %lu key events and %lu command lines did not fit their frame; a replay may differ.\n",dropped_keys,dropped_lines);
    release();
}
static void record_start(void)
{
    int n,r;
    if(mode!=IDLE)return;
    if(!(save=AW_SaveEncodeNow(&n,&save_profile,&save_sequence)))return;
    save_bytes=n;used=0;check_count=0;dropped_keys=dropped_lines=0;
    r=AW_SaveLoadBytes(save,n,save_profile,save_sequence);
    if(r!=1){free(save);save=NULL;save_bytes=0;Con_Printf("Recorder: the starting save does not load here; nothing recorded.\n");return;}
    seed=(uint32_t)(Sys_FloatTime()*1000.0)^(uint32_t)host_framecount;if(!seed)seed=1;
    mode=REC_START;
    Con_Printf("Recorder: starting save taken (%d bytes); the game loads it and records from the first frame in play.\n",n);
}
static void play_end(void)
{
    char text[96];long m,s;
    if(mode==PLAY_START){Con_Printf("Recorder: playback stopped before it started.\n");}
    else if(diverged<0){
        Con_Printf("RECORDER RESULT match %d/%d checkpoints, %lu frames, file %s\n",matched,check_count,frames,name);
        snprintf(text,sizeof(text),"Playback: %d of %d checkpoints match",matched,check_count);say(text,30);
    }else{
        minutes(diverged_time,&m,&s);
        Con_Printf("RECORDER RESULT diverged at checkpoint %d (%ld:%02ld, in %s); %d/%d checkpoints match, file %s\n",
                   diverged+1,m,s,diverged_cell,matched,check_count,name);
        snprintf(text,sizeof(text),"Playback diverged at checkpoint %d, %ld:%02ld, in %s",diverged+1,m,s,diverged_cell);say(text,30);
    }
    release();IN_AWClearButtons();Key_ClearStates();
}
static void compare(int i)
{
    check_t now;const check_t *r=&checks[i];float d[3],distance;int ok;long m,s,tenths;
    capture(&now);
    VectorSubtract(now.origin,r->origin,d);distance=(float)sqrt(DotProduct(d,d));
    ok=distance<=0.5f && fabs(now.health-r->health)<0.01 && !strcmp(now.cell,r->cell) && now.changes==r->changes;
    minutes(game_time,&m,&s);tenths=(long)(distance*10+0.5f);
    Con_Printf("Recorder checkpoint %d/%d at %ld:%02ld (frame %lu) in %s: %s; off by %ld.%ld units%s%s%s\n",i+1,check_count,m,s,frames,
               now.cell,ok?"match":"DIFFERS",tenths/10,tenths%10,fabs(now.health-r->health)<0.01?"":", health differs",
               strcmp(now.cell,r->cell)?", place differs":"",now.changes!=r->changes?", world changes differ":"");
    if(ok)matched++;
    else if(diverged<0){diverged=i;diverged_time=game_time;strcpy(diverged_cell,now.cell);}
}
/* the next recorded frame into CUR; 0 when the stream ends inside it */
static int read_frame(void)
{
    const unsigned char *p=stream+cursor;unsigned long left=stream_bytes-cursor,need=3;int i;
    if(left<3)return 0;
    cur.flags=p[0];cur.dt=p[1]|p[2]<<8;p+=3;
    if(cur.flags&F_MOVE){
        if(left<need+12)return 0;
        for(i=0;i<3;i++)cur.move[i]=(short)(p[2*i]|p[2*i+1]<<8);
        for(i=0;i<3;i++)cur.angle[i]=(short)(p[6+2*i]|p[6+2*i+1]<<8);
        p+=12;need+=12;
    }
    cur.keys=0;cur.line=0;
    if(cur.flags&F_KEYS){
        if(left<need+1 || p[0]>EVENTS_MAX || left<need+1+2*p[0])return 0;
        cur.keys=p[0];for(i=0;i<cur.keys;i++){cur.key[i][0]=p[1+2*i];cur.key[i][1]=p[2+2*i];}
        p+=1+2*cur.keys;need+=1+2*cur.keys;
    }
    if(cur.flags&F_LINE){
        if(left<need+2)return 0;
        cur.line=p[0]|p[1]<<8;
        if(cur.line>LINE_MAX || left<need+2+cur.line)return 0;
        memcpy(line,p+2,cur.line);line[cur.line]=0;need+=2+cur.line;
    }
    cursor+=need;return 1;
}
static void play_start(const char *what)
{
    char path[MAX_OSPATH+64];FILE *f;unsigned long size=0,cap=65536,i;unsigned char *grown;size_t got;int r,k;
    uint32_t checks_in,save_in,stream_in;
    if(mode!=IDLE){Con_Printf("Recorder: busy; stop first (Ctrl+R).\n");return;}
    for(k=0;what[k] && isdigit((unsigned char)what[k]);k++);
    if(!what[k] && k)snprintf(name,sizeof(name),"%03d.awr",atoi(what));
    else snprintf(name,sizeof(name),"%s%s",what,strstr(what,".awr")?"":".awr");
    snprintf(path,sizeof(path),"%s/recordings/%s",com_gamedir,name);
    if(!(f=fopen(path,"rb"))){Con_Printf("Recorder: no recording recordings/%s.\n",name);return;}
    /* one read in growing steps, no seek (aw_save.c read_whole: CHIM-SEYDA-BALMORA-LOAD-HANG-43) */
    if(!(file=(unsigned char *)AW_TryMalloc(cap))){fclose(f);Con_Printf("Recorder: not enough memory for the file.\n");return;}
    while((got=fread(file+size,1,cap-size,f))>0){
        size+=got;if(size<cap)break;
        if(cap*2>STREAM_MAX*3 || !(grown=(unsigned char *)AW_TryRealloc(file,cap*2))){fclose(f);release();Con_Printf("Recorder: the file is too large.\n");return;}
        file=grown;cap*=2;
    }
    fclose(f);
    if(size<HEAD_BYTES || memcmp(file,"AWR1",4)){release();Con_Printf("Recorder: recordings/%s is not a recording.\n",name);return;}
    seed=get32(file+36);save_profile=get32(file+40);save_sequence=get32(file+44);frame_count=get32(file+48);
    checks_in=get32(file+52);save_in=get32(file+56);stream_in=get32(file+60);
    if(checks_in>CHECKS_MAX || save_in>AW_SAVE_MAX_BYTES || stream_in>STREAM_MAX ||
       (unsigned long)HEAD_BYTES+save_in+stream_in+checks_in*CHECK_BYTES!=size){
        release();Con_Printf("Recorder: recordings/%s is damaged (its sizes do not add up).\n",name);return;
    }
    if(checks_in && !(checks=(check_t *)AW_TryMalloc(checks_in*sizeof(check_t)))){release();Con_Printf("Recorder: not enough memory.\n");return;}
    for(i=0;i<checks_in;i++)decode_check(file+HEAD_BYTES+save_in+stream_in+i*CHECK_BYTES,&checks[i]);
    check_count=check_capacity=(int)checks_in;
    stream=NULL;stream_bytes=stream_in;cursor=0;
    if(strncmp((char *)file+4,AMIWIND_VERSION,31))
        Con_Printf("Recorder: recorded with AmiWind v%.31s, replayed with v" AMIWIND_VERSION ".\n",(char *)file+4);
    r=AW_SaveLoadBytes(file+HEAD_BYTES,(int)save_in,save_profile,save_sequence);
    if(r!=1){release();Con_Printf("Recorder: the recording's save does not load here.\n");return;}
    /* the frames are read where they lie in the file buffer */
    stream=file+HEAD_BYTES+save_in;
    mode=PLAY_START;matched=0;diverged=-1;check_next=0;
    Con_Printf("Recorder: playing back recordings/%s (%lu frames, %d checkpoints): the game loads its save first.\n",name,frame_count,check_count);
}
static void status(void)
{
    static const char *names[]={"off","starting","recording","playback starting","playing back"};
    Con_Printf("Recorder: %s, %s; frame %lu, %d checkpoints, %lu bytes of frames.\n",armed?"armed (Ctrl+R records)":"not armed",
               names[mode],frames,check_count,mode==RECORDING?used:stream_bytes);
}
static void command(void)
{
    char *a=Cmd_Argc()>1?Cmd_Argv(1):"";
    if(mode==PLAY_START || mode==PLAYING){
        if(!Q_strcasecmp(a,"status"))status();
        else Con_Printf("Recorder: playing back; Ctrl+R stops it.\n");
        return;
    }
    if(!*a || !Q_strcasecmp(a,"on") || !strcmp(a,"1")){
        armed=1;Con_Printf("Recorder armed: Ctrl+R starts and stops a recording (dbg recorder off disarms).\n");return;
    }
    if(!Q_strcasecmp(a,"off") || !strcmp(a,"0")){
        if(mode!=IDLE)record_stop("disarmed");
        armed=0;Con_Printf("Recorder off.\n");return;
    }
    if(!Q_strcasecmp(a,"start")){armed=1;if(mode==IDLE)record_start();return;}
    if(!Q_strcasecmp(a,"stop")){if(mode!=IDLE)record_stop("dbg recorder stop");else Con_Printf("Recorder: not recording.\n");return;}
    if(!Q_strcasecmp(a,"status")){status();return;}
    if(!Q_strcasecmp(a,"play") && Cmd_Argc()==3){play_start(Cmd_Argv(2));return;}
    Con_Printf("Usage: dbg recorder [on/off / start / stop / play FILE / status] (FILE: 001 = recordings/001.awr)\n");
}
void AW_RecorderInit(void){Cmd_AddCommand("aw_recorder",command);}
int AW_RecorderActive(void){return mode!=IDLE;}
const char *AW_RecorderSuffix(void)
{
    return mode==REC_START || mode==RECORDING?" (RECORDING)":mode==PLAY_START || mode==PLAYING?" (PLAYBACK)":"";
}
void AW_RecorderFrame(void)
{
    unsigned dt;
    if(mode==IDLE)return;
    if(mode==REC_START || mode==PLAY_START){
        if(!ready())return;
        /* frame 0: the same buttons, keys and random rolls for the recording and its replay */
        IN_AWClearButtons();Key_ClearStates();srand(seed);
        frames=0;game_time=0;next_check=0;cur.open=0;
        mode=mode==REC_START?RECORDING:PLAYING;
        Con_Printf("Recorder: %s from frame 0 in %s.\n",mode==RECORDING?"recording":"playing back",AW_SceneName());
    }
    if(mode==RECORDING){
        if(cur.open && !commit()){record_stop("the recording's memory is full");return;}
        if(game_time>=next_check){
            if(!add_check()){record_stop("no room for more checkpoints");return;}
            next_check+=CHECK_EVERY;
        }
        /* the length kept in the recording's unit, and used as kept, so the replay runs the same frame */
        dt=(unsigned)(host_frametime*FRAME_UNIT+0.5);if(dt<1)dt=1;if(dt>65535)dt=65535;
        host_frametime=dt/FRAME_UNIT;game_time+=host_frametime;
        memset(&cur,0,sizeof(cur));cur.open=1;cur.dt=dt;
        return;
    }
    while(check_next<check_count && checks[check_next].frame<frames)check_next++;
    if(check_next<check_count && checks[check_next].frame==frames)compare(check_next++);
    if(frames>=frame_count){play_end();return;}
    if(!read_frame()){Con_Printf("Recorder: frame %lu of the recording is damaged.\n",frames);play_end();return;}
    host_frametime=cur.dt/FRAME_UNIT;game_time+=host_frametime;frames++;
}
void AW_RecorderInput(void)
{
    int i;
    if(mode!=PLAYING)return;
    injecting=1;
    for(i=0;i<cur.keys;i++)Key_Event(cur.key[i][0],cur.key[i][1]?true:false);
    injecting=0;
    if(cur.line)Cbuf_AddText(line);
}
int AW_RecorderKey(int key,int down)
{
    if(injecting)return 0;
    if(key==K_CTRL)real_ctrl=down;
    if(!armed && mode==IDLE)return 0;
    if(down && (key=='r' || key=='R') && real_ctrl && (key_dest==key_game || mode==PLAYING)){
        taken_r=1;
        if(mode==IDLE)record_start();
        else if(mode==REC_START || mode==RECORDING)record_stop("Ctrl+R");
        else{Con_Printf("Recorder: playback stopped with Ctrl+R.\n");play_end();}
        return 1;
    }
    if(!down && taken_r && (key=='r' || key=='R')){taken_r=0;return 1;}
    if(mode==PLAY_START || mode==PLAYING)return 1;
    if(mode==RECORDING && cur.open){
        if(cur.keys<EVENTS_MAX){cur.key[cur.keys][0]=(unsigned char)key;cur.key[cur.keys][1]=(unsigned char)(down?1:0);cur.keys++;cur.flags|=F_KEYS;}
        else dropped_keys++;
    }
    return 0;
}
void AW_RecorderLine(const char *text)
{
    const char *p=text,*e;int n;char one[LINE_MAX+1];
    if(mode!=RECORDING || !cur.open)return;
    while(*p){
        e=strchr(p,'\n');n=e?(int)(e-p)+1:(int)strlen(p);
        if(n>LINE_MAX){dropped_lines++;p+=n;continue;}
        memcpy(one,p,n);one[n]=0;p+=n;
        if(strstr(one,"recorder"))continue;     /* the recorder's own commands are not replayed */
        if(cur.line+n+1>LINE_MAX){dropped_lines++;continue;}
        memcpy(line+cur.line,one,n);cur.line+=n;
        if(line[cur.line-1]!='\n')line[cur.line++]='\n';
        cur.flags|=F_LINE;
    }
}
void AW_RecorderMove(usercmd_t *cmd)
{
    int i;
    if(mode==RECORDING && cur.open){
        cur.move[0]=move_code(cmd->forwardmove);cur.move[1]=move_code(cmd->sidemove);cur.move[2]=move_code(cmd->upmove);
        for(i=0;i<3;i++)cur.angle[i]=angle_code(cl.viewangles[i]);
        cur.flags|=F_MOVE;
    }else if(mode!=PLAYING || !(cur.flags&F_MOVE))return;
    /* the kept values, so the recording and its replay send the same */
    cmd->forwardmove=cur.move[0];cmd->sidemove=cur.move[1];cmd->upmove=cur.move[2];
    for(i=0;i<3;i++)cl.viewangles[i]=angle_value(cur.angle[i],i==YAW);
}
/* the version line while armed or running (10 pixels), and the saved file or the result for a few seconds (10 more) */
int AW_RecorderLineShown(void)
{
    if(key_dest==key_console)return 0;
    return (mode!=IDLE || armed?10:0)+(realtime<message_until && message[0]?10:0);
}
void AW_RecorderDraw(void)
{
    char text[96];int y=0,w;
    if(!vid.buffer || !AW_RecorderLineShown())return;
    if(mode!=IDLE)snprintf(text,sizeof(text),"AmiWind v" AMIWIND_VERSION "%s",AW_RecorderSuffix());
    else if(armed)snprintf(text,sizeof(text),"AmiWind v" AMIWIND_VERSION " - Ctrl+R: record");
    else text[0]=0;
    if(text[0]){
        w=(int)strlen(text)*8+8;if(w>(int)vid.width)w=vid.width;
        Draw_Fill(0,0,w,10,255);Draw_String(4,1,text);y=10;
    }
    if(realtime<message_until && message[0]){
        w=(int)strlen(message)*8+8;if(w>(int)vid.width)w=vid.width;
        Draw_Fill(0,y,w,10,255);Draw_String(4,y+1,message);
    }
    scr_copyeverything=1;
}
