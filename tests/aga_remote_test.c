/* SPDX-License-Identifier: GPL-2.0-or-later
 * Remote console: off by default; when on, a command file reaches the command
 * buffer once and is deleted, and the state file is rewritten every period. */
#include "../src/quakedef.h"
#include "../src/aw_remote.h"
#include <assert.h>
client_static_t cls;client_state_t cl;server_t sv;refdef_t r_refdef;keydest_t key_dest;
double realtime,host_frametime=.02;int r_daylight=200;
static char buffer[8192];static cvar_t *vars[4];static int nvars;
void Cbuf_AddText(char *t){strcat(buffer,t);}
void Cvar_RegisterVariable(cvar_t *v){vars[nvars++]=v;v->value=(float)atof(v->string);}
void Cvar_Set(char *n,char *v){int i;for(i=0;i<nvars;i++)if(!strcmp(vars[i]->name,n)){vars[i]->string=v;vars[i]->value=(float)atof(v);}}
#ifndef AW_FRAME_MAP
int AW_WorldToSource(const char *n,const float *l,float *g){(void)n;g[0]=l[0]*4;g[1]=l[1]*4;g[2]=l[2]*4;return 1;}
#else
/* CHIM-FRAME-SOURCE-CONVERSION-59: the state file's GLOBAL line on a CHIM frame map, through the real shared
 * conversion (aw_world.c) on a disk without the region table; a stand-in for chim_world.c's frame hook: map seyda,
 * centre 1000 -2000. */
extern int (*aw_world_chim_source)(const char *,const float *,float *);
static int frame_source(const char *n,const float *l,float *w){
    if(strcmp(n,"seyda"))return 0;w[0]=l[0]*4+1000;w[1]=l[1]*4-2000;w[2]=l[2]*4;return 1;}
int COM_FOpenFile(char *name,FILE **out){(void)name;*out=NULL;return -1;}   /* no region table, no region names */
int AW_SceneMapSize(const char *n,char *p,int s){(void)n;if(p && s>0)p[0]=0;return -1;}
void Con_Printf(char *fmt,...){(void)fmt;}
#endif
const char *AW_SceneName(void){return "vf0573";}   /* aw_scene.c: the scene the player stands in (type 1 crossings) */
int AW_ClockEnsure(void){return 1;}
void AW_ClockDate(int *y,int *mo,int *d,int *h,int *mi){*y=427;*mo=8;*d=16;*h=1;*mi=19;}
int AW_LampLitCount(void){return 2;}
int R_SkyExterior(void){return 1;}
int AW_GuardTorchNight(void){return 1;}
int aw_efrags_bad=3;   /* r_efrag.c: the efrag safety net's count (CHIM-FRAME-EDGE-EFRAG-CRASH-36) */
static int held;int AW_DayNightFrozen(void){return held;}
/* the windows' own state (aw_worldui.c, aw_wait.c, aw_dialwin.c, ...): LOAD-STALL-SESSIONS-59 */
static const char *the_window="";static int dialogue;
int AW_WorldUIActive(void){return *the_window!=0;}
const char *AW_WorldUIName(void){return the_window;}
const char *AW_WaitWindowName(void){return "";}
int AW_DialWindowActive(void){return dialogue;}
int AW_LevelupBoxActive(void){return 0;}int AW_MsgBoxActive(void){return 0;}int AW_ListBoxActive(void){return 0;}
int AW_QuickCharActive(void){return 0;}int AW_CharacterActive(void){return 0;}int AW_SaveMenuActive(void){return 0;}
int AW_ReaderActive(void){return 0;}
static int exists(const char *p){FILE *f=fopen(p,"rb");if(f)fclose(f);return f!=NULL;}
int main(void){
    char dir[256],cmd[300],state[300],text[2048];FILE *f;size_t n;
    snprintf(dir,sizeof dir,"/tmp/aw-remote-%ld/",(long)getpid());
    snprintf(text,sizeof text,"mkdir -p %s",dir);assert(!system(text));
    snprintf(cmd,sizeof cmd,"%scmd.txt",dir);snprintf(state,sizeof state,"%sstate.txt",dir);
    AW_RemoteInit();assert(nvars==2 && !AW_RemoteLogging());
    Cvar_Set("aw_remote_dir",dir);
    f=fopen(cmd,"w");fputs("dbg time 0119",f);fclose(f);
    realtime=1;AW_RemotePoll();assert(!buffer[0] && exists(cmd) && !exists(state)); /* off by default */
    Cvar_Set("aw_remote","1");assert(AW_RemoteLogging());
    AW_RemotePoll();assert(!strcmp(buffer,"dbg time 0119\n") && !exists(cmd) && exists(state));
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;
    assert(strstr(text,"commands 1\n") && strstr(text,"time 01:19\n") && strstr(text,"lamps_lit 2\n") && strstr(text,"daylight 200\n") && strstr(text,"guard_night 1\n") && strstr(text,"efrags_bad 3\n") && strstr(text,"screen game\n") && strstr(text,"world_leafs 0\n") && strstr(text,"end\n"));
    assert(strstr(text,"daynight on\n") && !strstr(text,"daynight off\n"));
    assert(strstr(text,"scene vf0573\n"));   /* the scene the player stands in (type 1 crossings) */
    f=fopen(cmd,"w");fputs("aw_aim 113 -3\n",f);fclose(f);
    realtime=1.2;AW_RemotePoll();assert(exists(cmd)); /* within the period: not yet */
    realtime=1.6;AW_RemotePoll();assert(!exists(cmd) && strstr(buffer,"aw_aim 113 -3\n"));
    /* dbg daynight off is visible to the remote harness. */
    held=1;realtime=2.2;AW_RemotePoll();
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"daynight off\n"));
    assert(strstr(AW_RemoteConsoleLog(),"console.log"));
    /* LOAD-STALL-SESSIONS-59: a window names itself; long work inside one frame (realtime standing)
     * still rewrites the file with ticks advancing; the format keeps "end" last. */
    assert(strstr(text,"ticks 5\n"));   /* five host frames polled so far (the first with aw_remote off) */
    the_window="inventory";key_dest=key_menu;
    AW_RemoteBusy(100.0);
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;
    assert(strstr(text,"screen inventory\n") && strstr(text,"realtime 2.20\n") && strstr(text,"ticks 6\n"));
    assert(!strcmp(text+n-4,"end\n"));
    AW_RemoteBusy(100.2);   /* within the period: ticks only */
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"ticks 6\n"));
    the_window="";AW_RemoteBusy(100.6);   /* no window: key_dest names the screen as before */
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;
    assert(strstr(text,"screen menu\n") && strstr(text,"ticks 8\n"));
    key_dest=key_console;the_window="journal";AW_RemoteBusy(101.2);   /* the console is on top of a window */
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"screen console\n"));
    key_dest=key_menu;the_window="window";dialogue=1;AW_RemoteBusy(101.8);   /* the dialogue window is a panel */
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"screen dialogue\n"));
    dialogue=0;AW_RemoteBusy(102.4);   /* another panel (stats, the container strip): a generic window */
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"screen window\n"));
    the_window="";key_dest=key_game;
#ifdef AW_FRAME_MAP
    aw_world_chim_source=frame_source;sv.active=1;strcpy(sv.name,"seyda");
    r_refdef.vieworg[0]=10;r_refdef.vieworg[1]=20;r_refdef.vieworg[2]=30;
    realtime=3.0;AW_RemotePoll();
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"global 1040 -1920 120\n"));
    strcpy(sv.name,"vf0001");realtime=4.0;AW_RemotePoll();   /* not the loaded frame map: no GLOBAL line */
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(!strstr(text,"global "));
    sv.active=0;aw_world_chim_source=NULL;
    puts("remote console on a CHIM frame map: the GLOBAL line through the shared conversion");
#endif
    /* SESSION-STALL-AFTER-LONG-FRAME-62: the console copy collects in memory and reaches console.log in one
     * append at the poll, on the heartbeat, when the buffer is full and at exit: never one file call per print */
    {
        char logp[300];static char big[9000];int i;long size;double t0=realtime;
        snprintf(logp,sizeof logp,"%sconsole.log",dir);remove(logp);
        for(i=0;i<300;i++)AW_RemoteLog(i%2?" ":"x");   /* an edict listing's padding, one space a print */
        AW_RemoteLog("end of listing\n");AW_RemoteLog("");AW_RemoteLog(NULL);
        assert(!exists(logp));                           /* 302 prints, no file call yet */
        realtime=t0+.2;AW_RemotePoll();assert(!exists(logp));   /* within the period: still collected */
        realtime=t0+.6;AW_RemotePoll();
        f=fopen(logp,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;
        assert(n==315 && text[0]=='x' && text[1]==' ' && !strcmp(text+300,"end of listing\n"));
        AW_RemoteLog("busy line\n");AW_RemoteBusy(103.0);   /* the long-work heartbeat sends it too, appended */
        f=fopen(logp,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;
        assert(n==325 && !strcmp(text+300,"end of listing\nbusy line\n"));
        memset(big,'a',8000);big[8000]=0;AW_RemoteLog(big);
        f=fopen(logp,"rb");fseek(f,0,SEEK_END);size=ftell(f);fclose(f);assert(size==325);   /* fits: kept */
        memset(big,'b',500);big[500]=0;AW_RemoteLog(big);   /* does not fit: the 8000 go first */
        f=fopen(logp,"rb");fseek(f,0,SEEK_END);size=ftell(f);fclose(f);assert(size==8325);
        memset(big,'c',8999);big[8999]=0;AW_RemoteLog(big);  /* larger than the buffer: the 500, then itself */
        f=fopen(logp,"rb");fseek(f,0,SEEK_END);size=ftell(f);fseek(f,8325,SEEK_SET);
        assert(size==17824 && fgetc(f)=='b');fseek(f,8825,SEEK_SET);assert(fgetc(f)=='c');fclose(f);
        AW_RemoteLog("last\n");AW_RemoteLogFlush();AW_RemoteLogFlush();   /* exit's flush; a second one is nothing */
        f=fopen(logp,"rb");fseek(f,0,SEEK_END);size=ftell(f);fclose(f);assert(size==17829);
        remove(logp);
        puts("remote console log: collected, one append a poll, heartbeat, full buffer and exit");
    }
    remove(state);snprintf(text,sizeof text,"rmdir %s",dir);assert(!system(text));
    puts("remote console: off by default, command file once, state file, period");
    return 0;
}
