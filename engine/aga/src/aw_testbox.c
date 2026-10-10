/* SPDX-License-Identifier: GPL-2.0-or-later
 * Test harness channels into a running game (docs/chim/build_guide/DIRECT_START.md
 * "Driving a test image"). One image serves every test; nothing here changes a
 * normal game.
 *
 * 1. The command mailbox: a static block in memory that starts with the
 *    signature "AWCMDBOX" and its own address. A harness that can read and write
 *    guest memory (the emulator's debugger) finds it by searching for the
 *    signature, writes a command line, then increments command_seq. Once per
 *    frame the engine compares command_seq with the last one it took (one compare);
 *    a new one is queued with Cbuf_AddText, the console output of the next frame is
 *    copied into result, and result_seq is set to the command's number. Active in
 *    test builds (id1/miniwind.txt) or with aw_cmdbox 1; aw_cmdbox 0 turns it off.
 * 2. The AWTEST: drive: an optional extra drive (the emulator mounts a host
 *    folder with that volume name). At start-up the engine runs AWTEST:test.cfg
 *    when it exists (before the logo); with aw_test_poll N it reads and deletes
 *    AWTEST:cmd.cfg every N frames (a running session driven by files);
 *    aw_test_write and aw_test_shot write results and screenshots back. No
 *    drive: nothing happens (the check asks the DOS volume list, no requester).
 * 3. Start-up options for a test image (any build, default off): aw_boot_console 1
 *    opens the console over the main menu at once, aw_test_start 1 starts the
 *    quick start at once, both without the startup logo.
 */
#include "quakedef.h"
#include "aw_miniwind.h"
#include "aw_testbox.h"
#include "amiwind_version.h"
void WritePCXfile(char *filename,byte *data,int width,int height,int rowbytes,byte *palette);
void D_EnableBackBufferAccess(void);
void D_DisableBackBufferAccess(void);
#ifdef AMIGA
#include <proto/dos.h>
#include <dos/dosextens.h>
#define TEST_DRIVE "AWTEST:"
#endif

static cvar_t cmdbox={"aw_cmdbox","-1"};      /* -1 auto: test builds only; 0 off; 1 on */
static cvar_t test_poll={"aw_test_poll","0"}; /* frames between AWTEST:cmd.cfg reads; 0 off */
static cvar_t boot_console={"aw_boot_console","0"};
static cvar_t test_start={"aw_test_start","0"};

aw_cmdbox_t aw_cmdbox={{'A','W','C','M','D','B','O','X'},AW_CMDBOX_VERSION,sizeof(aw_cmdbox_t)};
static unsigned long taken;
static int capturing,result_used,poll_count;
static int box_enabled(void){
    return cmdbox.value<0?AW_MiniwindActive():cmdbox.value!=0;
}
void AW_TestBoxPrint(const char *text){
    int n;
    if(!capturing || !text)return;
    n=(int)strlen(text);
    if(result_used+n>AW_CMDBOX_RESULT-1)n=AW_CMDBOX_RESULT-1-result_used;
    if(n<=0)return;
    memcpy(aw_cmdbox.result+result_used,text,n);result_used+=n;aw_cmdbox.result[result_used]=0;
}
void AW_TestBoxFrame(void){
    unsigned long seq;int i;
    if(capturing){
        capturing=0;aw_cmdbox.frame=(unsigned long)host_framecount;aw_cmdbox.result_seq=taken;
    }
    seq=aw_cmdbox.command_seq;
    if(seq==taken)return;            /* the per-frame cost: this compare */
    if(!box_enabled()){taken=seq;aw_cmdbox.status=AW_CMDBOX_DISABLED;aw_cmdbox.result_seq=seq;return;}
    taken=seq;result_used=0;aw_cmdbox.result[0]=0;
    for(i=0;i<AW_CMDBOX_COMMAND && aw_cmdbox.command[i];i++)
        if((unsigned char)aw_cmdbox.command[i]<32 && aw_cmdbox.command[i]!='\n')break;
    if(i==AW_CMDBOX_COMMAND || aw_cmdbox.command[i]){
        aw_cmdbox.status=AW_CMDBOX_REFUSED;aw_cmdbox.frame=(unsigned long)host_framecount;aw_cmdbox.result_seq=seq;return;
    }
    aw_cmdbox.status=AW_CMDBOX_OK;
    Cbuf_AddText(aw_cmdbox.command);Cbuf_AddText("\n");
    capturing=1;
}

/* ---- the AWTEST: drive */
int AW_TestDrive(char *out,int capacity){
#ifdef AMIGA
    struct DosList *list;int found;
    list=LockDosList(LDF_VOLUMES|LDF_READ);
    found=FindDosEntry(list,(STRPTR)"AWTEST",LDF_VOLUMES)!=NULL;
    UnLockDosList(LDF_VOLUMES|LDF_READ);
    if(!found || capacity<(int)sizeof(TEST_DRIVE))return 0;
    strcpy(out,TEST_DRIVE);return 1;
#else
    /* Host builds (native tests): a folder named by AW_TEST_DRIVE, with its trailing '/'. */
    const char *path=getenv("AW_TEST_DRIVE");
    if(!path || !*path || (int)strlen(path)>=capacity)return 0;
    strcpy(out,path);return 1;
#endif
}
/* A whole small text file from the drive into out (0-terminated); its length, or -1. */
static int drive_read(const char *name,char *out,int capacity){
    char path[64];FILE *f;int n;
    if(!AW_TestDrive(path,sizeof(path)) || strlen(path)+strlen(name)>=sizeof(path))return -1;
    strcat(path,name);
    if(!(f=fopen(path,"rb")))return -1;
    n=(int)fread(out,1,capacity-1,f);
    if(n<0 || !feof(f)){fclose(f);return -1;} /* too big: refused whole */
    fclose(f);out[n]=0;
    return (int)strlen(out)==n?n:-1;
}
static int drive_path(const char *name,char *out,int capacity){
    if(!AW_TestDrive(out,capacity) || strlen(out)+strlen(name)>=(size_t)capacity)return 0;
    strcat(out,name);return 1;
}
int AW_TestBootExec(void){
    static char text[AW_TEST_FILE+32];int n;
    if((n=drive_read("test.cfg",text,AW_TEST_FILE))<0)return 0;
    Con_Printf("Test drive: running AWTEST:test.cfg (%ld bytes).\n",(long)n);
    strcat(text,"\naw_startup_continue\n");
    Cbuf_InsertText(text);
    return 1;
}
int AW_TestBootSkipLogo(void){
    if(AW_SceneStarting() || sv.active || cls.state==ca_connected)return 1; /* test.cfg started a game */
    if(boot_console.value){Cbuf_AddText("aw_main_menu\naw_console_fullscreen\n");Con_Printf("Boot console (aw_boot_console 1).\n");return 1;}
    if(test_start.value){Cbuf_AddText("aw_quick_start\n");Con_Printf("Test start (aw_test_start 1).\n");return 1;}
    return 0;
}
void AW_TestPollFrame(void){
    static char text[AW_TEST_FILE];char path[64];
    if(test_poll.value<1 || ++poll_count<(int)test_poll.value)return;
    poll_count=0;
    if(drive_read("cmd.cfg",text,sizeof(text))<=0)return;
    if(drive_path("cmd.cfg",path,sizeof(path)))remove(path);
    Cbuf_AddText(text);Cbuf_AddText("\n");
}
/* aw_test_write TEXT...: one line (frame number, text) appended to AWTEST:results.txt. */
static void write_command(void){
    char path[64];FILE *f;
    if(!drive_path("results.txt",path,sizeof(path))){Con_Printf("No AWTEST: drive.\n");return;}
    if(!(f=fopen(path,"ab"))){Con_Printf("AWTEST:results.txt not writable.\n");return;}
    fprintf(f,"%ld %s\n",(long)host_framecount,Cmd_Args());fclose(f);
}
/* aw_test_shot NAME: the last frame as AWTEST:NAME.pcx (the screenshot command's writer). */
static void shot_command(void){
    char saved[MAX_OSPATH],name[40];const char *s=Cmd_Argv(1);int i;
    if(Cmd_Argc()!=2 || !*s || strlen(s)>30){Con_Printf("Usage: aw_test_shot NAME\n");return;}
    for(i=0;s[i];i++)if(!((s[i]>='a'&&s[i]<='z')||(s[i]>='A'&&s[i]<='Z')||(s[i]>='0'&&s[i]<='9')||s[i]=='-'||s[i]=='_')){
        Con_Printf("Shot names: letters, digits, - and _.\n");return;
    }
    if(!AW_TestDrive(saved,sizeof(saved))){Con_Printf("No AWTEST: drive.\n");return;}
    sprintf(name,"%s.pcx",s);
    strcpy(saved,com_gamedir);
    AW_TestDrive(com_gamedir,sizeof(com_gamedir));
#ifndef AMIGA
    if(com_gamedir[0] && com_gamedir[strlen(com_gamedir)-1]=='/')com_gamedir[strlen(com_gamedir)-1]=0;
#endif
    D_EnableBackBufferAccess();
    WritePCXfile(name,vid.buffer,vid.width,vid.height,vid.rowbytes,host_basepal);
    D_DisableBackBufferAccess();
    strcpy(com_gamedir,saved);
    Con_Printf("Test shot: AWTEST:%s\n",name);
}
static void status_command(void){
    char path[64];
    Con_Printf("Mailbox %s at %p, command %lu, result %lu; AWTEST: %s; poll %ld frames\n",
        box_enabled()?"on":"off",(void *)&aw_cmdbox,aw_cmdbox.command_seq,aw_cmdbox.result_seq,
        AW_TestDrive(path,sizeof(path))?"present":"absent",(long)test_poll.value);
}
void AW_TestBoxInit(void){
    aw_cmdbox.self=&aw_cmdbox;
    strncpy(aw_cmdbox.build,AMIWIND_VERSION,sizeof(aw_cmdbox.build)-1);
    Cvar_RegisterVariable(&cmdbox);Cvar_RegisterVariable(&test_poll);
    Cvar_RegisterVariable(&boot_console);Cvar_RegisterVariable(&test_start);
    Cmd_AddCommand("aw_test_write",write_command);
    Cmd_AddCommand("aw_test_shot",shot_command);
    Cmd_AddCommand("aw_test_status",status_command);
}
