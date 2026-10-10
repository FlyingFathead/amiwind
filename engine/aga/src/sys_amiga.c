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
#include "aw_log.h"
extern cvar_t aw_logs_live;



// Amiga includes.
#include <proto/exec.h>
#include <exec/memory.h>
#include <proto/dos.h>
#include <dos/dos.h>
#include <dos/var.h>
#include <proto/intuition.h>
#include <intuition/intuition.h>
#include <intuition/intuitionbase.h>
#include <devices/input.h>
#include <devices/inputevent.h>
#include <exec/interrupts.h>
#include <devices/timer.h>
#include <proto/timer.h>



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
/* DEBUG.TXT, the console copy, is a diagnostic log held in memory and written
 * at exit, on a fatal error or with dbg savelogs (aw_log.c); aw_logs_live 1
 * writes it as it happens. If it cannot be created (for example the volume is
 * still being validated and the player chose Cancel) the game runs without it
 * instead of stopping, and it is not retried on every print
 * (BOOT-VOLUME-NOT-VALIDATED-33). */
void Sys_Printf (char *message, ...)
{
	va_list		argptr;
	char		text[1024];

    va_start (argptr, message);
    vsnprintf (text, sizeof(text), message, argptr);
    va_end (argptr);

    AW_LogWrite(AW_LOG_DEBUG, text);
}
#endif


void IN_MLookDown (void);

// Timer function prototype (implemented in amiga_stubs.c)
void timer(unsigned int *clock);

// Timer functions from original awinquake
/* ENGINE-FLOATTIME-DIV64-35: seconds between two EClock readings with one
 * 64-bit subtraction and one multiply. timer() divides the 64-bit tick count
 * twice per call (library routines, not FPU instructions) to make seconds and
 * microseconds that Sys_FloatTime then joined again; the mixer and the frame
 * loop call it several times per frame. */
/* aw_eclock_seconds begin */
static double AW_EClockSeconds (unsigned long hi, unsigned long lo,
                                unsigned long base_hi, unsigned long base_lo,
                                double tick_seconds)
{
  unsigned long dlo = (lo - base_lo) & 0xffffffffUL;
  unsigned long dhi = (hi - base_hi - (lo < base_lo)) & 0xffffffffUL;
  return ((double)dhi * 4294967296.0 + (double)dlo) * tick_seconds;
}
/* aw_eclock_seconds end */

#ifndef __PPC__
extern struct Device *TimerBase;
extern ULONG eclocks_per_second;
#endif

double Sys_FloatTime (void)
{
#ifndef __PPC__
  static unsigned int basetime=0;
  static int eclock_based = 0;
  static ULONG base_hi, base_lo;
  static double tick_seconds, offset, last;
  unsigned int clock[2];

  if (TimerBase != NULL && eclocks_per_second > 0) {
    struct EClockVal e;
    ReadEClock (&e);
    if (!eclock_based) {
      /* Continue from the last value of the start-up path below. */
      eclock_based = 1;
      base_hi = e.ev_hi;
      base_lo = e.ev_lo;
      tick_seconds = 1.0 / eclocks_per_second;
      offset = last;
    }
    last = offset + AW_EClockSeconds (e.ev_hi, e.ev_lo, base_hi, base_lo, tick_seconds);
    return last;
  }
  if (eclock_based)
    return last;   /* timer closed at shutdown: hold the clock */
  timer (clock);
  if (!basetime)
    basetime = clock[0];
  last = (clock[0]-basetime) + clock[1] / 1000000.0;
  return last;
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

/* The game heap (Quake's Hunk). The builder's --heap-mb N sets it through the
 * generated amiwind_heap.h; the start argument -heapmb N overrides it for one
 * start. Both are used exactly as asked; above AMIWIND_HEAP_SAFE_MB, the
 * largest size measured to run the whole game on the 16 MiB Fast RAM
 * profile, the start says so and goes on. */
#include "amiwind_heap.h"
#ifndef AMIWIND_HEAP_MB
/* Expanded starting area plus renderer and actor cache, within the existing
 * 16 MiB Fast RAM playtest profile. Chip RAM remains reserved for hardware. */
#define AMIWIND_HEAP_MB 11
#endif
#define AMIWIND_HEAP_SAFE_MB 11

/* -heapmb N from the start arguments (before COM_InitArgv, which runs after the
 * heap is allocated); 0 when absent or not a number from 1 to 2047. */
static int Sys_HeapArgument(int argc, char **argv) {
    int i, value;
    const char *p;
    for (i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], "-heapmb"))
            continue;
        for (value = 0, p = argv[i+1]; *p >= '0' && *p <= '9' && value < 4096; p++)
            value = value*10 + (*p - '0');
        if (*p || value < 1 || value > 2047) {
            PutStr("AmiWind: -heapmb takes a whole number of MiB from 1 to 2047; using the built size.\n");
            return 0;
        }
        return value;
    }
    return 0;
}

static void Sys_Init(int heap_mb) {
    char line[160];

    // Allocate memory.
    if (heap_mb <= 0)
        heap_mb = AMIWIND_HEAP_MB;
    if (heap_mb > AMIWIND_HEAP_SAFE_MB) {
        sprintf(line, "AmiWind: WARNING: game heap %d MiB is above the %d MiB measured to run the whole game on 16 MiB Fast RAM; starting as asked.\n",
                heap_mb, AMIWIND_HEAP_SAFE_MB);
        PutStr(line);
    }
    quakeparms.memsize = heap_mb*1024*1024;

    /* The SDK malloc failure path can trap before returning NULL. Keep this
     * large, fixed allocation in Fast RAM and report a normal startup error.
     * Leave up to 15 bytes of headroom for Quake's 16-byte hunk alignment. */
    quakeparms.memsize = (quakeparms.memsize+15)&~15;
    aw_heap_allocation_size = (ULONG)quakeparms.memsize + 15;
    aw_heap_allocation = AllocMem(aw_heap_allocation_size, MEMF_FAST|MEMF_PUBLIC);
    if (!aw_heap_allocation) {
        sprintf(line, "AmiWind: cannot allocate the %d MiB game heap in Fast RAM.\n"
                "Use more Fast RAM (16 MiB or more for the 11 MiB heap), or a smaller -heapmb, then reboot.\n", heap_mb);
        PutStr(line);
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

    /* Exit game: the in-memory diagnostic logs go to disk once, here. */
    AW_LogFlushAll();
    AW_LogClose();



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
    vsnprintf (text, sizeof(text), error, argptr);
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
    /* The in-memory diagnostic logs (heap audit with its fatal-exit phase,
     * console copy) go to disk after the crash report. */
    AW_LogFlushAll();
    AW_LogClose();

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



/* Frame times in double, as id's own Sys loops (sys_linux.c): a float holds
 * Sys_FloatTime's seconds since start to 1 ms after about 4.5 hours and to
 * 4 ms after about 18, so long sessions quantised or stalled their frame
 * deltas (ENGINE-FRAME-TIME-FLOAT-35). The 68040/060 FPU subtracts doubles
 * natively; only the difference goes to Host_Frame as before. */
static void RunGameLoop(void)
{
    double newtime;
    double oldtime;

    // Never exits
    oldtime = Sys_FloatTime();
    while (true) {
        newtime = Sys_FloatTime();

        Host_Frame(newtime - oldtime);

        oldtime = newtime;
	}
}


/* BOOT-VOLUME-NOT-VALIDATED-33. When the last session ended while the boot
 * volume had changes in flight (emulator closed, reset or killed during a
 * save or log write), AmigaOS validates the volume at the next boot. Until
 * that finishes the volume is read-only: the engine's first write opens
 * "Volume ... is not validated" (Retry/Cancel; Cancel stopped the game).
 * On a fast emulated CPU the boot check's countdown hides the validation;
 * on a slow cycle-exact one it runs about a minute. So wait for it here,
 * before anything is written. The local shell variable
 * AmiWindValidateWait=0 (Set in S:startup-sequence) keeps the previous
 * immediate start. GVF_LOCAL_ONLY: never touch ENV:, which the boot disk
 * does not assign. The wait gives up after AW_VALIDATE_WAIT_LIMIT seconds. */
/* aw_validate_wait begin */
#ifndef AW_VALIDATE_WAIT_LIMIT
#define AW_VALIDATE_WAIT_LIMIT 900
#endif
static int AW_WaitBootVolumeValidated(void)
{
    struct InfoData *info;
    BPTR lock;
    char value[8];
    int seconds = 0, waited = 0;

    if (GetVar("AmiWindValidateWait", value, sizeof value, GVF_LOCAL_ONLY) > 0 && value[0] == '0')
        return -1;
    lock = Lock("PROGDIR:", ACCESS_READ);
    if (!lock) return 0;
    info = AllocVec(sizeof(*info), MEMF_PUBLIC | MEMF_CLEAR);
    if (info) {
        while (seconds < AW_VALIDATE_WAIT_LIMIT && Info(lock, info) &&
               info->id_DiskState == ID_VALIDATING) {
            if (!waited) {
                PutStr("The game volume is being validated: the last session\n"
                       "did not end cleanly. Waiting for AmigaOS to finish...\n");
                waited = 1;
            }
            Delay(50);
            seconds++;
        }
        FreeVec(info);
    }
    UnLock(lock);
    if (waited)
        PutStr(seconds < AW_VALIDATE_WAIT_LIMIT ? "Volume validated.\n"
               : "Validation still running; starting anyway.\n");
    return seconds;
}
/* aw_validate_wait end */

/* The boot image uses the AmigaDOS shell. Do not link icon tooltype support:
 * some ROMs load icon.library from disk even before main() is entered. */
/* ENGINE-STACK-UNCHECKED-35: the pak directory alone takes 128 KiB of
 * stack (COM_LoadPackFile), and nothing checked the stack the game was
 * started with: a small one overwrote memory instead of stopping. The boot
 * disk runs "Stack 300000"; tc_SPUpper - tc_SPLower is the stack this program
 * runs on (RunCommand and Workbench start-up both set it). */
#define AW_MIN_STACK 262144UL
static int AW_StackTooSmall(void)
{
    struct Task *task = FindTask(NULL);
    unsigned long size = (unsigned long)task->tc_SPUpper - (unsigned long)task->tc_SPLower;
    char message[200];
    if (size >= AW_MIN_STACK)
        return 0;
    snprintf(message, sizeof(message),
             "AmiWind needs a stack of at least %lu bytes; it was started with %lu.\nRun \"Stack 300000\" first (the AmiWind boot disk does).\n",
             AW_MIN_STACK, size);
    PutStr(message);
    return 1;
}

int main(int argc, char *argv[]) {
    static char *default_argv[] = {"AmiWind", NULL};
    if (AW_StackTooSmall())
        return RETURN_FAIL;
    AW_PlatformInit();
    PutStr("Loading AmiWind v");
    /* Referencing the tag keeps Amiga Version-command metadata in the executable. */
    PutStr(ID + sizeof("$VER: AmiWind ") - 1);
    /* Diagnostic logs stay in memory unless aw_logs_live is set (from the
     * configuration, dbg logs live on or a --live-logs build). */
    AW_LogUseSwitch(&aw_logs_live.value);
    /* Before the first write (saves, settings, live logs). */
    AW_WaitBootVolumeValidated();
    if (argc == 0) { argc = 1; argv = default_argv; }
    Sys_Init(Sys_HeapArgument(argc, argv));
    COM_InitArgv(argc, argv);
    quakeparms.basedir = "PROGDIR:";
    quakeparms.cachedir = NULL;
    quakeparms.argc = com_argc;
    quakeparms.argv = com_argv;
    Host_Init(&quakeparms);
    RunGameLoop();
    return EXIT_SUCCESS;
}
