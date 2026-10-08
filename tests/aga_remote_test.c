/* SPDX-License-Identifier: GPL-2.0-or-later
 * Remote console: off by default; when on, a command file reaches the command
 * buffer once and is deleted, and the state file is rewritten every period. */
#include "../src/quakedef.h"
#include "../src/aw_remote.h"
#include <assert.h>
client_static_t cls;client_state_t cl;server_t sv;refdef_t r_refdef;
double realtime,host_frametime=.02;int r_daylight=200;
static char buffer[8192];static cvar_t *vars[4];static int nvars;
void Cbuf_AddText(char *t){strcat(buffer,t);}
void Cvar_RegisterVariable(cvar_t *v){vars[nvars++]=v;v->value=(float)atof(v->string);}
void Cvar_Set(char *n,char *v){int i;for(i=0;i<nvars;i++)if(!strcmp(vars[i]->name,n)){vars[i]->string=v;vars[i]->value=(float)atof(v);}}
int AW_WorldToSource(const char *n,const float *l,float *g){(void)n;g[0]=l[0]*4;g[1]=l[1]*4;g[2]=l[2]*4;return 1;}
int AW_ClockEnsure(void){return 1;}
void AW_ClockDate(int *y,int *mo,int *d,int *h,int *mi){*y=427;*mo=8;*d=16;*h=1;*mi=19;}
int AW_LampLitCount(void){return 2;}
int R_SkyExterior(void){return 1;}
int AW_GuardTorchNight(void){return 1;}
static int held;int AW_DayNightFrozen(void){return held;}
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
    assert(strstr(text,"commands 1\n") && strstr(text,"time 01:19\n") && strstr(text,"lamps_lit 2\n") && strstr(text,"daylight 200\n") && strstr(text,"guard_night 1\n") && strstr(text,"end\n"));
    assert(strstr(text,"daynight on\n") && !strstr(text,"daynight off\n"));
    f=fopen(cmd,"w");fputs("aw_aim 113 -3\n",f);fclose(f);
    realtime=1.2;AW_RemotePoll();assert(exists(cmd)); /* within the period: not yet */
    realtime=1.6;AW_RemotePoll();assert(!exists(cmd) && strstr(buffer,"aw_aim 113 -3\n"));
    /* dbg daynight off is visible to the remote harness. */
    held=1;realtime=2.2;AW_RemotePoll();
    f=fopen(state,"r");n=fread(text,1,sizeof text-1,f);fclose(f);text[n]=0;assert(strstr(text,"daynight off\n"));
    assert(strstr(AW_RemoteConsoleLog(),"console.log"));
    remove(state);snprintf(text,sizeof text,"rmdir %s",dir);assert(!system(text));
    puts("remote console: off by default, command file once, state file, period");
    return 0;
}
