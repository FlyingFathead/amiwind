/* SPDX-License-Identifier: GPL-2.0-or-later
 * Test harness channels (aw_testbox.c): the command mailbox found by its
 * signature, the AWTEST: drive (here a host folder named by AW_TEST_DRIVE) with
 * test.cfg at start-up and the cmd.cfg poll, and the test start-up options.
 * argv[1]: an empty folder for the drive. */
#include "quakedef.h"
#include "aw_testbox.h"
#include <assert.h>
server_t sv;client_static_t cls;viddef_t vid;int host_framecount;char com_gamedir[MAX_OSPATH];byte *host_basepal;
static char queued[4096],inserted[16384];static int miniwind_active,scene_starting,shots;
static cvar_t *cvars[8];static int cvar_count;
static const char *argv_now[8];static int argc_now;
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);cvars[cvar_count++]=v;}
static void set(const char *name,float value){int i;for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,name))cvars[i]->value=value;}
typedef void (*command_t)(void);
static struct {const char *name;command_t fn;} commands[8];static int command_count;
void Cmd_AddCommand(char *name,xcommand_t fn){commands[command_count].name=name;commands[command_count++].fn=fn;}
static void run(int argc,const char **argv){
    int i;argc_now=argc;for(i=0;i<argc;i++)argv_now[i]=argv[i];
    for(i=0;i<command_count;i++)if(!strcmp(commands[i].name,argv[0])){commands[i].fn();return;}
    assert(!"command registered");
}
int Cmd_Argc(void){return argc_now;}
char *Cmd_Argv(int i){return (char *)(i<argc_now?argv_now[i]:"");}
char *Cmd_Args(void){return (char *)(argc_now>1?argv_now[1]:"");}
void Con_Printf(char *fmt,...){(void)fmt;}
void Cbuf_AddText(char *text){strcat(queued,text);}
void Cbuf_InsertText(char *text){strcat(inserted,text);}
int AW_MiniwindActive(void){return miniwind_active;}
int AW_SceneStarting(void){return scene_starting;}
void WritePCXfile(char *filename,byte *data,int width,int height,int rowbytes,byte *palette){
    char path[256];FILE *f;(void)data;(void)width;(void)height;(void)rowbytes;(void)palette;
    sprintf(path,"%s/%s",com_gamedir,filename);f=fopen(path,"wb");assert(f);fputs("PCX",f);fclose(f);shots++;
}
void D_EnableBackBufferAccess(void){}
void D_DisableBackBufferAccess(void){}
static void frame(void){AW_TestBoxFrame();AW_TestPollFrame();host_framecount++;}
static void put(const char *dir,const char *name,const char *text){
    char path[256];FILE *f;sprintf(path,"%s%s",dir,name);f=fopen(path,"wb");assert(f);fputs(text,f);fclose(f);
}
int main(int argc,char **argv){
    char drive[200],path[256];const unsigned char *mem;size_t i,hits=0;FILE *f;
    assert(argc==2);
    strcpy(com_gamedir,"id1");
    AW_TestBoxInit();
    /* The mailbox: one signature in the block itself, its own address, version, size. */
    mem=(const unsigned char *)&aw_cmdbox;
    assert(!memcmp(mem,"AWCMDBOX",8) && aw_cmdbox.self==&aw_cmdbox);
    assert(aw_cmdbox.version==AW_CMDBOX_VERSION && aw_cmdbox.size==sizeof(aw_cmdbox_t));
    for(i=0;i+8<=sizeof(aw_cmdbox);i++)if(!memcmp(mem+i,"AWCMDBOX",8))hits++;
    assert(hits==1);
    /* A normal build (no miniwind.txt, aw_cmdbox -1 auto): a command is answered "disabled", never run. */
    strcpy(aw_cmdbox.command,"dbg headlamp on");aw_cmdbox.command_seq=1;frame();
    assert(!queued[0] && aw_cmdbox.result_seq==1 && aw_cmdbox.status==AW_CMDBOX_DISABLED);
    /* A test build: queued once, the next frame's console output is the result. */
    miniwind_active=1;
    strcpy(aw_cmdbox.command,"aw_quickchar_show");aw_cmdbox.command_seq=2;frame();
    assert(!strcmp(queued,"aw_quickchar_show\n") && aw_cmdbox.result_seq==1);
    AW_TestBoxPrint("Character: Hors\n");frame();
    assert(aw_cmdbox.result_seq==2 && aw_cmdbox.status==AW_CMDBOX_OK && !strcmp(aw_cmdbox.result,"Character: Hors\n"));
    AW_TestBoxPrint("later output is not captured\n");
    assert(!strcmp(aw_cmdbox.result,"Character: Hors\n"));
    frame();assert(!strcmp(queued,"aw_quickchar_show\n")); /* same number: nothing new */
    /* Unterminated or control characters: refused, nothing queued. */
    memset(aw_cmdbox.command,'x',AW_CMDBOX_COMMAND);aw_cmdbox.command_seq=3;queued[0]=0;frame();
    assert(!queued[0] && aw_cmdbox.result_seq==3 && aw_cmdbox.status==AW_CMDBOX_REFUSED);
    strcpy(aw_cmdbox.command,"echo\001");aw_cmdbox.command_seq=4;frame();
    assert(!queued[0] && aw_cmdbox.status==AW_CMDBOX_REFUSED);
    /* aw_cmdbox 0 turns it off in a test build too. */
    set("aw_cmdbox",0);strcpy(aw_cmdbox.command,"echo");aw_cmdbox.command_seq=5;frame();
    assert(!queued[0] && aw_cmdbox.status==AW_CMDBOX_DISABLED);
    set("aw_cmdbox",-1);
    /* No drive: no test.cfg, the normal logo runs; the options stay off. */
    unsetenv("AW_TEST_DRIVE");
    assert(!AW_TestDrive(drive,sizeof(drive)) && !AW_TestBootExec() && !AW_TestBootSkipLogo() && !inserted[0]);
    /* The drive with test.cfg: its text, then aw_startup_continue. */
    sprintf(drive,"%s/",argv[1]);setenv("AW_TEST_DRIVE",drive,1);
    assert(!AW_TestBootExec());                   /* drive present, no test.cfg: normal start */
    put(drive,"test.cfg","aw_quickchar_set race nord\naw_quick_start map prison 0 -35 -4 90");
    assert(AW_TestBootExec());
    assert(!strcmp(inserted,"aw_quickchar_set race nord\naw_quick_start map prison 0 -35 -4 90\naw_startup_continue\n"));
    scene_starting=1;assert(AW_TestBootSkipLogo());scene_starting=0;   /* test.cfg started a game */
    queued[0]=0;set("aw_boot_console",1);assert(AW_TestBootSkipLogo() && !strcmp(queued,"aw_main_menu\naw_console_fullscreen\n"));
    queued[0]=0;set("aw_boot_console",0);set("aw_test_start",1);assert(AW_TestBootSkipLogo() && !strcmp(queued,"aw_quick_start\n"));
    set("aw_test_start",0);
    /* The live poll: off by default; every N frames cmd.cfg is run once and deleted. */
    queued[0]=0;put(drive,"cmd.cfg","dbg tp balmora");
    frame();frame();assert(!queued[0]);
    set("aw_test_poll",2);frame();assert(!queued[0]);frame();
    assert(!strcmp(queued,"dbg tp balmora\n"));
    sprintf(path,"%scmd.cfg",drive);assert(!(f=fopen(path,"rb")));
    queued[0]=0;frame();frame();assert(!queued[0]);
    /* Results and screenshots back to the drive; the game directory is restored. */
    { const char *w[]={"aw_test_write","walk ok"};run(2,w); }
    sprintf(path,"%sresults.txt",drive);f=fopen(path,"rb");assert(f);
    { char line[64];assert(fgets(line,sizeof(line),f) && strstr(line," walk ok\n"));fclose(f); }
    { const char *s[]={"aw_test_shot","arrival-1"};run(2,s); }
    assert(shots==1 && !strcmp(com_gamedir,"id1"));
    sprintf(path,"%sarrival-1.pcx",drive);f=fopen(path,"rb");assert(f);fclose(f);
    { const char *s[]={"aw_test_shot","../x"};run(2,s); }
    assert(shots==1);
    puts("test mailbox, AWTEST drive, test.cfg, live poll and start-up options");
    return 0;
}
