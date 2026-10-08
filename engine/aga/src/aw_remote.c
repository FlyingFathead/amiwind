/* SPDX-License-Identifier: GPL-2.0-or-later
 * Remote console for headless test sessions (aw_remote 1; off by default and
 * not saved). The Quake way: a command file run through the command buffer,
 * like exec. Twice a second the engine looks for <aw_remote_dir>cmd.txt (a
 * host folder the test emulator mounts as an Amiga volume, default AWCTL:),
 * appends its text to the command buffer, deletes it, and rewrites
 * <aw_remote_dir>state.txt: map, position, view, game time, daylight, lamps,
 * frame time, how many command files ran and, while dbg rcount is on, the
 * last renderer counter line (aw_rcount.c), ending with "end" (written in
 * place: the Amiga C library has no rename; a reader retries a file without
 * the end line). With aw_remote on, console
 * output also goes to <aw_remote_dir>console.log (Quake's -condebug log).
 * Nothing here runs while aw_remote is 0.
 */
#include "quakedef.h"
#include "aw_world.h"
#include "aw_clock.h"
#include "aw_sky.h"
#include "aw_remote.h"
#include "aw_rcount.h"
int AW_GuardTorchNight(void);
#define REMOTE_CMD_MAX 4096
#define REMOTE_PERIOD .5
static cvar_t aw_remote={"aw_remote","0"};
static cvar_t aw_remote_dir={"aw_remote_dir","AWCTL:"};
static double next_poll;
static long command_files;
int AW_RemoteLogging(void){return aw_remote.value>0;}
static void remote_path(char *out,int size,const char *name)
{
    snprintf(out,size,"%s%s",aw_remote_dir.string,name);
}
const char *AW_RemoteConsoleLog(void)
{
    static char path[MAX_OSPATH];
    remote_path(path,sizeof path,"console.log");
    return path;
}
/* Run a waiting command file: its text goes to the command buffer as typed. */
static void run_commands(void)
{
    char path[MAX_OSPATH];static char text[REMOTE_CMD_MAX+2];FILE *f;size_t n;
    remote_path(path,sizeof path,"cmd.txt");
    f=fopen(path,"rb");if(!f)return;
    n=fread(text,1,REMOTE_CMD_MAX,f);fclose(f);
    remove(path);
    text[n]=0;
    if(n && text[n-1]!='\n'){text[n++]='\n';text[n]=0;}
    command_files++;
    Cbuf_AddText(text);
}
/* Fixed-point text for state.txt, same format as %.<decimals>f. printf's
 * float formatting runs the C library's dtoa, which executes 68040-
 * unimplemented FPU instructions twice a second (ENGINE-FPU-UNIMPL-31). */
static const char *fixed(char *out,double v,int decimals)
{
    long scale=decimals==2?100:decimals==1?10:1,n;
    n=(long)(v*scale+(v<0?-0.5:0.5));
    /* no "*" field widths: the Amiga C library prints them literally */
    if(!decimals)sprintf(out,"%ld",n);
    else sprintf(out,decimals==2?"%s%ld.%02ld":"%s%ld.%01ld",n<0?"-":"",labs(n)/scale,labs(n)%scale);
    return out;
}
static void write_state(void)
{
    char path[MAX_OSPATH],a[24],b[24],c[24];FILE *f;float global[3];int year,month,day,hour,minute,have_global;
    remote_path(path,sizeof path,"state.txt");
    f=fopen(path,"w");if(!f)return;
    have_global=sv.active && AW_WorldToSource(sv.name,r_refdef.vieworg,global);
    fprintf(f,"commands %ld\nrealtime %s\nframe_ms %s\n",command_files,fixed(a,realtime,2),fixed(b,host_frametime*1000.0,1));
    fprintf(f,"map %s\nserver %s\n",cl.worldmodel?cl.worldmodel->name:"none",sv.active?sv.name:"none");
    fprintf(f,"local %s %s %s\n",fixed(a,r_refdef.vieworg[0],0),fixed(b,r_refdef.vieworg[1],0),fixed(c,r_refdef.vieworg[2],0));
    fprintf(f,"angles %s %s\n",fixed(a,cl.viewangles[PITCH],1),fixed(b,cl.viewangles[YAW],1));
    if(have_global)fprintf(f,"global %s %s %s\n",fixed(a,global[0],0),fixed(b,global[1],0),fixed(c,global[2],0));
    if(AW_ClockEnsure()){AW_ClockDate(&year,&month,&day,&hour,&minute);fprintf(f,"time %02d:%02d\nday %d %d %d\n",hour,minute,day,month,year);}
    fprintf(f,"daynight %s\n",AW_DayNightFrozen()?"off":"on");
    fprintf(f,"daylight %d\nlamps_lit %d\nexterior %d\nguard_night %d\n",r_daylight,AW_LampLitCount(),R_SkyExterior(),AW_GuardTorchNight());
    if(*AW_RCountLine())fprintf(f,"rcount %s\n",AW_RCountLine());
    fputs("end\n",f);
    fclose(f);
}
void AW_RemotePoll(void)
{
    if(aw_remote.value<=0 || realtime<next_poll)return;
    next_poll=realtime+REMOTE_PERIOD;
    run_commands();
    write_state();
}
void AW_RemoteInit(void)
{
    Cvar_RegisterVariable(&aw_remote);Cvar_RegisterVariable(&aw_remote_dir);
}
