/* SPDX-License-Identifier: GPL-2.0-or-later
 * The load trace ring (engine/aga/src/aw_loadtrace.c, LOAD-HANG-WATCHDOG-62): off traces nothing, on keeps the
 * last 128 calls with their file names and stages, wraps, marks a call that never ended, and formats its lines. */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static char output[65536];static int used;static double clock_now;
double Sys_FloatTime(void){return clock_now;}
void Con_Printf(char *format,...){
    va_list ap;int n;va_start(ap,format);
    n=vsnprintf(output+used,sizeof(output)-used,format,ap);va_end(ap);
    assert(n>=0 && n<(int)sizeof(output)-used);used+=n;
}
extern int aw_loadtrace_on;
void AW_LoadTraceSet(int on);
unsigned long AW_LoadTraceBegin(int op,const void *file,const char *name,long bytes);
void AW_LoadTraceEnd(unsigned long seq,long result,const void *file);
void AW_LoadTraceStage(const char *phase,int cvar_on);
int AW_LoadTraceFormat(unsigned long seq,char *out,int size);
unsigned long AW_LoadTraceCount(void);
void AW_LoadTraceDump(const char *why,int lines);
void AW_LoadTraceSceneReady(const char *why);

int main(void){
    char line[160];unsigned long s,open_seq;int i,a=1,b=2;
    /* off: nothing is traced, no number handed out */
    assert(!aw_loadtrace_on && AW_LoadTraceBegin(1,0,"x",0)==0 && AW_LoadTraceCount()==0);
    /* on through the cvar at a stage change */
    clock_now=10.0;AW_LoadTraceStage("before-bsp",1);
    assert(aw_loadtrace_on && strstr(output,"Load trace on: ring at $"));
    clock_now=10.5;s=AW_LoadTraceBegin(1,0,"PROGDIR:id1/maps/a-very-long-folder-name/balmora-frame.chim",0);
    clock_now=10.5625;AW_LoadTraceEnd(s,0,&a);
    assert(s==1 && AW_LoadTraceFormat(1,line,sizeof(line)));
    /* the path's last 35 characters, the stage, the time since on and the duration */
    assert(!strcmp(line,"LT 1 before-bsp open long-folder-name/balmora-frame.chim 0 bytes -> 0, at 500 ms, 62 ms"));
    /* a read by the file handle is named by its open */
    AW_LoadTraceStage("after-bsp",1);
    s=AW_LoadTraceBegin(2,&a,0,4096);AW_LoadTraceEnd(s,4096,&a);
    AW_LoadTraceFormat(s,line,sizeof(line));
    assert(strstr(line,"after-bsp read long-folder-name/balmora-frame.chim 4096 bytes -> 4096"));
    s=AW_LoadTraceBegin(4,&a,0,0);AW_LoadTraceEnd(s,0,&a);
    s=AW_LoadTraceBegin(2,&a,0,16);AW_LoadTraceFormat(s,line,sizeof(line));
    assert(strstr(line," read ? 16 bytes, at "));     /* closed: no longer named */
    assert(strstr(line,"NOT FINISHED"));             /* begun, never ended */
    open_seq=s;
    /* wrap: 200 more calls, the ring keeps the last 128; the old numbers are gone, the stale end is ignored */
    for(i=0;i<200;i++){s=AW_LoadTraceBegin(3,&b,0,i);AW_LoadTraceEnd(s,0,&b);}
    assert(AW_LoadTraceCount()==204);
    assert(!AW_LoadTraceFormat(open_seq,line,sizeof(line)) && !AW_LoadTraceFormat(76,line,sizeof(line)));
    assert(AW_LoadTraceFormat(77,line,sizeof(line)) && strstr(line,"LT 77 after-bsp seek ? 72 bytes -> 0"));
    AW_LoadTraceEnd(open_seq,16,&a);
    assert(AW_LoadTraceFormat(204,line,sizeof(line)) && strstr(line,"seek ? 199 bytes -> 0"));
    /* the dump: a summary, the last lines, every unfinished call; once per load at Scene ready */
    s=AW_LoadTraceBegin(2,&b,0,512);used=0;output[0]=0;
    AW_LoadTraceSceneReady("scene ready");
    assert(strstr(output,"Load trace (scene ready): 205 calls since on, 128 kept, 1 not finished"));
    assert(strstr(output,"LT 205 after-bsp read ? 512 bytes, at ") && strstr(output,"LT 198 ") && !strstr(output,"LT 197 "));
    used=0;output[0]=0;AW_LoadTraceSceneReady("scene ready");assert(!used);
    AW_LoadTraceStage("outgoing",1);AW_LoadTraceSceneReady("scene ready");assert(used);
    /* off again through the cvar */
    AW_LoadTraceStage("after-unload",0);assert(!aw_loadtrace_on && AW_LoadTraceBegin(1,0,"y",0)==0);
    (void)b;puts("load trace ok");return 0;
}
