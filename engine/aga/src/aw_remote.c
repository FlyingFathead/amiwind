/* SPDX-License-Identifier: GPL-2.0-or-later
 * Remote console for headless test sessions (aw_remote 1; off by default and
 * not saved). The Quake way: a command file run through the command buffer,
 * like exec. Twice a second the engine looks for <aw_remote_dir>cmd.txt (a
 * host folder the test emulator mounts as an Amiga volume, default AWCTL:),
 * appends its text to the command buffer, deletes it, and rewrites
 * <aw_remote_dir>state.txt: map, position, view, game time, daylight, lamps,
 * frame time and how many command files ran, ending with "end" (written in
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
static void write_state(void)
{
    char path[MAX_OSPATH];FILE *f;float global[3];int year,month,day,hour,minute,have_global;
    remote_path(path,sizeof path,"state.txt");
    f=fopen(path,"w");if(!f)return;
    have_global=sv.active && AW_WorldToSource(sv.name,r_refdef.vieworg,global);
    fprintf(f,"commands %ld\nrealtime %.2f\nframe_ms %.1f\n",command_files,realtime,host_frametime*1000.0);
    fprintf(f,"map %s\nserver %s\n",cl.worldmodel?cl.worldmodel->name:"none",sv.active?sv.name:"none");
    fprintf(f,"local %.0f %.0f %.0f\nangles %.1f %.1f\n",r_refdef.vieworg[0],r_refdef.vieworg[1],r_refdef.vieworg[2],
        cl.viewangles[PITCH],cl.viewangles[YAW]);
    if(have_global)fprintf(f,"global %.0f %.0f %.0f\n",global[0],global[1],global[2]);
    if(AW_ClockEnsure()){AW_ClockDate(&year,&month,&day,&hour,&minute);fprintf(f,"time %02d:%02d\nday %d %d %d\n",hour,minute,day,month,year);}
    fprintf(f,"daylight %d\nlamps_lit %d\nexterior %d\nguard_night %d\n",r_daylight,AW_LampLitCount(),R_SkyExterior(),AW_GuardTorchNight());
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
