/* SPDX-License-Identifier: GPL-2.0-or-later
 * Remote console for headless test sessions (aw_remote 1; off by default and
 * not saved). The Quake way: a command file run through the command buffer,
 * like exec. Twice a second the engine looks for <aw_remote_dir>cmd.txt (a
 * host folder the test emulator mounts as an Amiga volume, default AWCTL:),
 * appends its text to the command buffer, deletes it, and rewrites
 * <aw_remote_dir>state.txt: map, position, view, game time, daylight, lamps,
 * frame time, how many command files ran and, while dbg rcount is on, the
 * last renderer counter line (aw_rcount.c; and the dbg rprof line while that
 * is on), ending with "end" (written in
 * place: the Amiga C library has no rename; a reader retries a file without
 * the end line). With aw_remote on, console
 * output also goes to <aw_remote_dir>console.log (Quake's -condebug log).
 * Nothing here runs while aw_remote is 0.
 */
#include <unistd.h>
#include <fcntl.h>
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
/* CHIM-SEYDA-BALMORA-LOAD-HANG-43: the candidate trigger of the test sessions' stops is the console log's append on the
 * remote folder (a directory drive the emulator serves from a host thread; the repeat2 stop of 15 November 2026 fell
 * inside it). aw_remote_log 0 keeps the console log off that folder entirely (the lines stay on the in-game console;
 * the command and state files are untouched), so sessions with and without it can be compared. Default 1: as before. */
static cvar_t aw_remote_log={"aw_remote_log","1"};
static double next_poll,next_busy;
static long command_files;
/* LOAD-STALL-SESSIONS-59: "ticks" advances on every host frame and on every long-work heartbeat
 * (AW_RemoteBusy), so a reader tells a paused game clock (a window open, a long step inside one
 * frame) from a dead engine. The screen line names an open window by the engine's own names
 * (the dialogue window opens as a world-UI panel, so it is asked first; another panel such as the
 * stats is "window"; the container window over the game is "container"); with none, game / menu / message by
 * key_dest. */
static unsigned long ticks;
int AW_DialWindowActive(void);int AW_LevelupBoxActive(void);int AW_MsgBoxActive(void);
int AW_ListBoxActive(void);int AW_QuickCharActive(void);int AW_CharacterActive(void);int AW_SaveMenuActive(void);
static const char *screen_name(void)
{
    const char *w;
    if(key_dest==key_console)return "console";
    if(AW_DialWindowActive())return "dialogue";
    if(AW_WorldUIActive())return AW_WorldUIName();
    if(AW_LevelupBoxActive())return "levelup";
    w=AW_WaitWindowName();if(w && *w)return w;
    if(AW_SaveMenuActive())return "save";
    if(AW_CharacterActive() || AW_QuickCharActive())return "character";
    if(AW_ReaderActive())return "book";
    if(AW_MsgBoxActive())return "messagebox";
    if(AW_ListBoxActive())return "listbox";
    /* CONTAINER-WINDOW-SURVIVES-PLACE-CHANGE-67: the container window over the game (it keeps key_dest on the game,
     * so a check read "game" while it was open) */
    if(key_dest==key_game && aw_cstrip_open_now && aw_cstrip_open_now())return "container";
    return key_dest==key_game?"game":key_dest==key_menu?"menu":"message";
}
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
/* SESSION-STALL-AFTER-LONG-FRAME-62: the console copy was one open, seek, write and close on the
 * remote folder per Con_Printf, and Quake prints piecewise (one "edict" listing is about 300
 * prints, each field name padded one space at a time): a 3-7 s frame of remote-folder file calls,
 * and 3 of 10 test sessions stopped right after one. The prints now collect here (8 KiB, a
 * fraction of a frame's text) and go out in ONE append: at the poll (twice a second), on the
 * long-work heartbeat, when the buffer is full, and at exit (Sys_Error flushes right after its
 * fatal-exit heap note). A print larger than the buffer is appended on its own. */
#define REMOTE_LOG_MAX 8192
static char log_buf[REMOTE_LOG_MAX];
static int log_len,log_exit_hook;
/* CHIM-SEYDA-BALMORA-LOAD-HANG-43 (the repeat2 stop of 15 November 2026): the append is the one remote-folder call the
 * disk wrappers in aw_spike.h do not see (a file descriptor, not a FILE), and that stop fell inside it: the last frame
 * printed had spent 2.5 s in the remote stage with 23 ms of wrapped disk time, and the load trace ring held no unfinished
 * call. Its four calls are traced by name here (op 5 = write; the numbers are aw_spike.h's AW_LT_OP_ enum), so the ring
 * names the one that never ends. */
extern int aw_loadtrace_on;
unsigned long AW_LoadTraceBegin(int op,const void *file,const char *name,long bytes);
void AW_LoadTraceEnd(unsigned long seq,long result,const void *file);
#define LOG_TRACE(op,bytes) (aw_loadtrace_on?AW_LoadTraceBegin((op),0,path,(bytes)):0)
static void log_append(const char *data,int len)
{
    const char *path=AW_RemoteConsoleLog();unsigned long lt;int fd;long r;
    lt=LOG_TRACE(1,0);fd=open(path,O_WRONLY|O_CREAT|O_APPEND,0666);if(lt)AW_LoadTraceEnd(lt,fd<0?-1:0,0);
    if(fd<0)return;
    /* the Amiga C library does not honour O_APPEND (REMOTE-CONSOLE-APPEND-31) */
    lt=LOG_TRACE(3,0);r=lseek(fd,0,SEEK_END);if(lt)AW_LoadTraceEnd(lt,r,0);
    lt=LOG_TRACE(5,len);r=write(fd,data,len);if(lt)AW_LoadTraceEnd(lt,r,0);   /* a short write loses log text only; nothing to retry here */
    lt=LOG_TRACE(4,0);r=close(fd);if(lt)AW_LoadTraceEnd(lt,r,0);
}
void AW_RemoteLogFlush(void)
{
    int n=log_len;
    log_len=0;
    if(n<=0 || aw_remote_log.value<=0)return;   /* aw_remote_log 0: what was collected is dropped, no file call */
    log_append(log_buf,n);
}
void AW_RemoteLog(const char *msg)
{
    int n=msg?(int)strlen(msg):0;
    if(n<=0 || aw_remote_log.value<=0)return;
    if(!log_exit_hook){log_exit_hook=1;atexit(AW_RemoteLogFlush);}
    if(log_len+n>REMOTE_LOG_MAX)AW_RemoteLogFlush();
    if(n>REMOTE_LOG_MAX){log_append(msg,n);return;}
    memcpy(log_buf+log_len,msg,n);log_len+=n;
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
    AW_RecorderLine(text);   /* a recording keeps it with its frame (GAME-RECORDER-61) */
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
    fprintf(f,"commands %ld\nrealtime %s\nframe_ms %s\nticks %lu\n",command_files,fixed(a,realtime,2),fixed(b,host_frametime*1000.0,1),ticks);
    fprintf(f,"map %s\nserver %s\n",cl.worldmodel?cl.worldmodel->name:"none",sv.active?sv.name:"none");
    /* The scene the player stands in: after a streamed (type 1) crossing the frame entered, else the running map. */
    fprintf(f,"scene %s\n",AW_SceneName());
    fprintf(f,"local %s %s %s\n",fixed(a,r_refdef.vieworg[0],0),fixed(b,r_refdef.vieworg[1],0),fixed(c,r_refdef.vieworg[2],0));
    fprintf(f,"angles %s %s\n",fixed(a,cl.viewangles[PITCH],1),fixed(b,cl.viewangles[YAW],1));
    if(have_global)fprintf(f,"global %s %s %s\n",fixed(a,global[0],0),fixed(b,global[1],0),fixed(c,global[2],0));
    if(AW_ClockEnsure()){AW_ClockDate(&year,&month,&day,&hour,&minute);fprintf(f,"time %02d:%02d\nday %d %d %d\n",hour,minute,day,month,year);}
    fprintf(f,"daynight %s\n",AW_DayNightFrozen()?"off":"on");
    fprintf(f,"daylight %d\nlamps_lit %d\nexterior %d\nguard_night %d\n",r_daylight,AW_LampLitCount(),R_SkyExterior(),AW_GuardTorchNight());
    {extern int aw_efrags_bad;fprintf(f,"efrags_bad %d\n",aw_efrags_bad);}
    /* AW-RECOVER (aw_scene.c): the errors in play the recovery chain took, those a test aid forced, and the frame
     * messages dropped (sv_main.c, cl_parse.c); the engine smoke fails a run with an unforced error or a drop */
    {extern int aw_scene_errors,aw_scene_errors_forced,aw_net_dropped,cl_parse_dropped;
     fprintf(f,"errors %d\nerrors_forced %d\nnet_dropped %d\n",aw_scene_errors,aw_scene_errors_forced,
             aw_net_dropped+cl_parse_dropped);}
    /* What the screen shows (SMOKE-PASSES-WITHOUT-MAP-36): a loaded server under the title menu
     * is not a played map. screen game = in play; world_leafs = the client's world model. */
    fprintf(f,"screen %s\nsignon %d\nworld_leafs %d\n",screen_name(),
        cls.signon,cl.worldmodel?cl.worldmodel->numleafs:0);   /* the efrag safety net (CHIM-FRAME-EDGE-EFRAG-CRASH-36) */
    if(*AW_RCountLine())fprintf(f,"rcount %s\n",AW_RCountLine());
    if(*AW_RProfLine())fprintf(f,"rprof %s\n",AW_RProfLine());
    fputs("end\n",f);
    fclose(f);
}
void AW_RemotePoll(void)
{
    ticks++;
    if(aw_remote.value<=0){AW_RemoteLogFlush();return;}   /* switched off: what was collected still goes out */
    if(realtime<next_poll)return;
    next_poll=realtime+REMOTE_PERIOD;
    AW_RemoteLogFlush();
    run_commands();
    write_state();
}
/* A heartbeat from long work inside one frame (S_ExtraUpdate's callers: catalogue reads, loads)
 * and from the modal loops that run their own key loop: the state file only, no command file,
 * at most twice a second of NOW (Sys_FloatTime: realtime stands still inside the frame). */
void AW_RemoteBusy(double now)
{
    ticks++;
    if(aw_remote.value<=0 || now<next_busy)return;
    next_busy=now+REMOTE_PERIOD;
    AW_RemoteLogFlush();
    write_state();
}
void AW_RemoteInit(void)
{
    Cvar_RegisterVariable(&aw_remote);Cvar_RegisterVariable(&aw_remote_dir);Cvar_RegisterVariable(&aw_remote_log);
}
