/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/

#include "amiwind_version.h"
char *ID = "$VER: AmiWind " AMIWIND_VERSION "\r\n";

#include "quakedef.h"



// Amiga includes.
#include <proto/exec.h>
#include <exec/memory.h>
#include <proto/dos.h>
#include <proto/intuition.h>
#include <intuition/intuition.h>
#include <intuition/intuitionbase.h>
#include <devices/input.h>
#include <devices/inputevent.h>
#include <exec/interrupts.h>



// External video window from vid_amiga.c
extern struct Window *video_window;

/* Intuition handles Left-Amiga+M before IDCMP_RAWKEY. Reserve M/N while our
 * window is active, including console input and an accidentally held qualifier.
 * Other applications and all other system shortcuts retain their events. */
static struct MsgPort *guard_port;
static struct IOStdReq *guard_io;
static struct Interrupt guard_handler;
static int guard_open,guard_added;
struct InputEvent *AW_InputGuardEvents(struct InputEvent *events){
    struct InputEvent *e;
    if(video_window && IntuitionBase->FirstScreen==video_window->WScreen &&
       (video_window->Flags&WFLG_WINDOWACTIVE))
        for(e=events;e;e=e->ie_NextEvent)
            if(e->ie_Class==IECLASS_RAWKEY && ((e->ie_Code&0x7f)==0x37 || (e->ie_Code&0x7f)==0x36))
                e->ie_Qualifier&=~(IEQUALIFIER_LCOMMAND|IEQUALIFIER_RCOMMAND);
    return events;
}
/* input.device supplies the event list in A0; the C compiler uses the stack. */
extern void AW_InputGuardEntry(void);
__asm__(".text\n.globl _AW_InputGuardEntry\n_AW_InputGuardEntry:\n"
        "move.l %a0,-(%sp)\njsr _AW_InputGuardEvents\naddq.l #4,%sp\nrts\n");
void AW_InputGuardShutdown(void){
    if(guard_added){guard_io->io_Command=IND_REMHANDLER;guard_io->io_Data=&guard_handler;
        DoIO((struct IORequest *)guard_io);guard_added=0;}
    if(guard_open){CloseDevice((struct IORequest *)guard_io);guard_open=0;}
    if(guard_io){DeleteIORequest((struct IORequest *)guard_io);guard_io=NULL;}
    if(guard_port){DeleteMsgPort(guard_port);guard_port=NULL;}
}
void AW_InputGuardInit(void){
    if(guard_added)return;
    guard_port=CreateMsgPort();if(!guard_port)goto failed;
    guard_io=(struct IOStdReq *)CreateIORequest(guard_port,sizeof(*guard_io));if(!guard_io)goto failed;
    if(OpenDevice("input.device",0,(struct IORequest *)guard_io,0))goto failed;
    guard_open=1;memset(&guard_handler,0,sizeof(guard_handler));
    guard_handler.is_Node.ln_Type=NT_INTERRUPT;guard_handler.is_Node.ln_Pri=60;
    guard_handler.is_Node.ln_Name="AmiWind screen keys";
    guard_handler.is_Code=(VOID (*)())AW_InputGuardEntry;
    guard_io->io_Command=IND_ADDHANDLER;guard_io->io_Data=&guard_handler;
    if(DoIO((struct IORequest *)guard_io))goto failed;
    guard_added=1;Con_Printf("M/N protected before Intuition; debug Alt+M shows desktop.\n");return;
failed:
    AW_InputGuardShutdown();Con_Printf("Screen key protection unavailable. Release the Amiga modifier if M/N changes screens.\n");
}

// Dedicated server flag (not used on Amiga but needed for host.c)
qboolean isDedicated = FALSE;

// Mouse stuff.
int mouseX = 0;
int mouseY = 0;
qboolean mouse_has_moved = false;
static cvar_t aw_input_trace={"aw_input_trace","0"};
static void desktop(void){
    if(!AW_DebugOverlaysEnabled() || !video_window)return;
    IN_AWClearButtons();Key_ClearStates();
    ScreenToBack(video_window->WScreen);
}
void AW_InputDebugInit(void){
    Cvar_RegisterVariable(&aw_input_trace);Cmd_AddCommand("aw_desktop",desktop);
}

#define RAWKEY_NM_WHEEL_UP      0x7A
#define RAWKEY_NM_WHEEL_DOWN    0x7B


static quakeparms_t quakeparms;
/* Use checked Exec allocation for the large hunk; preserve the raw pointer. */
static void *aw_heap_allocation;
static ULONG aw_heap_allocation_size;



#ifndef NDEBUG
static int debugFileHandle = 0;

void Sys_Printf (char *message, ...)
{
	va_list		argptr;
	char		text[1024];

    va_start (argptr, message);
    vsprintf (text, message, argptr);
    va_end (argptr);

    if (!debugFileHandle) {
        debugFileHandle = Sys_FileOpenWrite("DEBUG.TXT");
    }

    if (debugFileHandle) {
	Sys_FileWrite(debugFileHandle, text, strlen(text));
    }
}
#endif


void IN_MLookDown (void);

// Timer function prototype (implemented in amiga_stubs.c)
void timer(unsigned int *clock);

// Timer functions from original awinquake
double Sys_FloatTime (void)
{
#ifndef __PPC__
  static unsigned int basetime=0;
  unsigned int clock[2];

  timer (clock);
  if (!basetime)
    basetime = clock[0];
  return (clock[0]-basetime) + clock[1] / 1000000.0;
#else
  unsigned int clock[2];

  ppctimer (clock);
#ifdef __VBCC__  /* work around bug in VBCC */
  return (((double)clock[0]) * (2147483648.0 + 2147483648.0) +
          (double)clock[1]) * clocks2secs;
#else
  return (((double)clock[0]) * 4294967296.0 + (double)clock[1]) *
         clocks2secs;
#endif
#endif
}

char *Sys_ConsoleInput (void)
{
	return NULL;
}

void Sys_Sleep (void)
{
}

void Sys_HighFPPrecision (void)
{
}

void Sys_LowFPPrecision (void)
{
}

static void Sys_Init(void) {

    // Allocate memory.
#ifndef AMIWIND_HEAP_MB
/* Expanded starting area plus renderer and actor cache, within the existing
 * 16 MiB Fast RAM playtest profile. Chip RAM remains reserved for hardware. */
#define AMIWIND_HEAP_MB 11
#endif
    quakeparms.memsize = AMIWIND_HEAP_MB*1024*1024;

    /* The SDK malloc failure path can trap before returning NULL. Keep this
     * large, fixed allocation in Fast RAM and report a normal startup error.
     * Leave up to 15 bytes of headroom for Quake's 16-byte hunk alignment. */
    quakeparms.memsize = (quakeparms.memsize+15)&~15;
    aw_heap_allocation_size = (ULONG)quakeparms.memsize + 15;
    aw_heap_allocation = AllocMem(aw_heap_allocation_size, MEMF_FAST|MEMF_PUBLIC);
    if (!aw_heap_allocation) {
        PutStr("AmiWind: cannot allocate the 11 MiB game heap in Fast RAM.\n"
               "Use 16 MiB Fast RAM or more, then reboot.\n");
        AW_PlatformClose();
        exit(EXIT_FAILURE);
    }
    quakeparms.membase = (void *)(((ULONG)aw_heap_allocation + 15) & ~15UL);

    // Mouse look by default.
    IN_MLookDown();
}

void Sys_Quit(void) {

	Host_Shutdown();

	if (quakeparms.membase) {
        FreeMem(aw_heap_allocation, aw_heap_allocation_size);
        aw_heap_allocation = NULL;
        quakeparms.membase = NULL;
    }

#ifndef NDEBUG
    if (debugFileHandle) {
	Sys_FileClose(debugFileHandle);
    }
#endif



    PutStr("To restart AmiWind, type: amiwind\n");
	AW_PlatformClose();
	exit(EXIT_SUCCESS);
}


void Sys_Error (char *error, ...)
{
	va_list		argptr;
	char		text[1024];
    BPTR errorFileHandle, errorLock;
    LONG errorLength, verified, chunk, received;
    char verifyBytes[64];
    qboolean errorSaved = false;
    char errorPath[512];


    va_start (argptr, error);
    vsprintf (text, error, argptr);
    va_end (argptr);

    /* Capture allocator state before shutdown releases caches and heap. */
    AW_HeapAuditPhase(NULL,"fatal-exit");
    /* DOS calls avoid the allocating stdio path during heap exhaustion.
     * Resolve the file itself so the displayed path matches this launch's cwd. */
    strcpy(errorPath,"ERROR.TXT (in the launch directory)");
    errorLength = (LONG)strlen(text);
    errorFileHandle = Open("ERROR.TXT",MODE_NEWFILE);
    if (errorFileHandle) {
        errorSaved = Write(errorFileHandle,text,errorLength) == errorLength;
        if (!Close(errorFileHandle)) errorSaved = false;
        if (errorSaved) {
            /* Read back in small fixed chunks; never allocate another report.
             * Require identical contents and EOF, not merely a successful open. */
            errorFileHandle = Open("ERROR.TXT",MODE_OLDFILE);
            if (!errorFileHandle) errorSaved = false;
            else {
                verified = 0;
                while (errorSaved && verified < errorLength) {
                    chunk = errorLength - verified;
                    if (chunk > (LONG)sizeof(verifyBytes)) chunk = sizeof(verifyBytes);
                    received = Read(errorFileHandle,verifyBytes,chunk);
                    if (received != chunk || memcmp(verifyBytes,text+verified,chunk))
                        errorSaved = false;
                    else verified += chunk;
                }
                if (errorSaved && Read(errorFileHandle,verifyBytes,1) != 0)
                    errorSaved = false;
                if (!Close(errorFileHandle)) errorSaved = false;
            }
        }
        if (errorSaved) {
            errorLock = Lock("ERROR.TXT",ACCESS_READ);
            if (errorLock) {
                if (!NameFromLock(errorLock,errorPath,sizeof(errorPath)))
                    strcpy(errorPath,"ERROR.TXT (in the launch directory)");
                UnLock(errorLock);
            }
        }
    }

	Host_Shutdown();

	if (quakeparms.membase) {
        FreeMem(aw_heap_allocation, aw_heap_allocation_size);
        aw_heap_allocation = NULL;
        quakeparms.membase = NULL;
    }



	AW_PlatformClose();
    /* Print after closing the game screen so AmigaDOS retains the reason.
     * Only the fatal path runs this; ERROR.TXT remains the durable copy. */
    PutStr("\n------------------------------------------------------\n"
           "AmiWind v" AMIWIND_VERSION " crashed!\n"
           "Crash details: ");
    PutStr(text[0] ? text : "No reason was provided.");
    PutStr("\n\n");
    if (errorSaved) {
        PutStr("Crash log is at ");
        PutStr(errorPath);
        PutStr("\n");
    } else {
        PutStr("Crash log could not be verified at ERROR.TXT (in the launch directory).\n"
               "Please copy the crash details shown above.\n");
    }
    PutStr("------------------------------------------------------\n"
           "To restart AmiWind, try typing: amiwind\n");
	exit(EXIT_FAILURE);
}






void Sys_SendKeyEvents(void) {

  ULONG class;
  UWORD code,qualifier;
  WORD mousex, mousey;
  struct IntuiMessage *msg;


  if (video_window != NULL) {
    while ((msg = (struct IntuiMessage *)GetMsg (video_window->UserPort)) != NULL) {
        class = msg->Class;
        code = msg->Code;
        qualifier = msg->Qualifier;
        mousex = msg->MouseX;
        mousey = msg->MouseY;
        ReplyMsg ((struct Message *)msg);

        switch (class) {
        case IDCMP_ACTIVEWINDOW:
        case IDCMP_INACTIVEWINDOW:
            AW_WorldUICancelDrag();IN_AWClearButtons();Key_ClearStates();break;
        case IDCMP_RAWKEY:
            Key_AmigaQualifiers(qualifier);
            /* The complete qualifier mask preserves the other Shift/Alt key. */
            if((code&0x7f)>=0x60 && (code&0x7f)<=0x67)break;
            if(aw_input_trace.value)Con_Printf("Input raw %ld qualifier %ld\n",(long)code,(long)qualifier);
            switch (code) {
                case RAWKEY_NM_WHEEL_UP:
	Key_Event(K_MWHEELUP, true);
	Key_Event(K_MWHEELUP, false);
	break;

                case RAWKEY_NM_WHEEL_DOWN:
	Key_Event(K_MWHEELDOWN, true);
	Key_Event(K_MWHEELDOWN, false);
	break;

                default:
                    if(Key_AmigaRaw(code))Key_Event(Key_AmigaRaw(code),(code & IECODE_UP_PREFIX)==0);
                    break;
            }
            break;

        case IDCMP_MOUSEBUTTONS:
          Key_AmigaQualifiers(qualifier);
          switch (code) {
            case IECODE_LBUTTON:
              Key_Event (K_MOUSE1, true);
              break;
            case IECODE_LBUTTON + IECODE_UP_PREFIX:
              Key_Event (K_MOUSE1, false);
              break;
            case IECODE_MBUTTON:
              Key_Event (K_MOUSE2, true);
              break;
            case IECODE_MBUTTON + IECODE_UP_PREFIX:
              Key_Event (K_MOUSE2, false);
              break;
            case IECODE_RBUTTON:
              Key_Event (K_MOUSE3, true);
              break;
            case IECODE_RBUTTON + IECODE_UP_PREFIX:
              Key_Event (K_MOUSE3, false);
              break;
            default:
              break;
          }
          break;

        case IDCMP_MOUSEMOVE:
          if(aw_input_trace.value)Con_Printf("Input mouse %ld %ld qualifier %ld\n",(long)mousex,(long)mousey,(long)qualifier);
          IN_AWMouseEvent(mousex, mousey);
          break;

        default:
          break;
        }
    }
  }
}


//=============================================================================



static void RunGameLoop(void)
{
    float newtime;
    float oldtime;

    // Never exits
    oldtime = Sys_FloatTime();
    while (true) {
        newtime = Sys_FloatTime();

        Host_Frame(newtime - oldtime);

        oldtime = newtime;
	}
}


/* The boot image uses the AmigaDOS shell. Do not link icon tooltype support:
 * some ROMs load icon.library from disk even before main() is entered. */
int main(int argc, char *argv[]) {
    static char *default_argv[] = {"AmiWind", NULL};
    AW_PlatformInit();
    PutStr("Loading AmiWind v");
    /* Referencing the tag keeps Amiga Version-command metadata in the executable. */
    PutStr(ID + sizeof("$VER: AmiWind ") - 1);
    Sys_Init();
    if (argc == 0) { argc = 1; argv = default_argv; }
    COM_InitArgv(argc, argv);
    quakeparms.basedir = "PROGDIR:";
    quakeparms.cachedir = NULL;
    quakeparms.argc = com_argc;
    quakeparms.argv = com_argv;
    Host_Init(&quakeparms);
    RunGameLoop();
    return EXIT_SUCCESS;
}
