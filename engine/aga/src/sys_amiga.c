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
#include <intuition/intuition.h>



// External video window from vid_amiga.c
extern struct Window *video_window;

// Dedicated server flag (not used on Amiga but needed for host.c)
qboolean isDedicated = FALSE;

// Mouse stuff.
int mouseX = 0;
int mouseY = 0;
qboolean mouse_has_moved = false;
static cvar_t aw_input_trace={"aw_input_trace","0"};
void AW_InputDebugInit(void){Cvar_RegisterVariable(&aw_input_trace);}

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
	int errorFileHandle;


    va_start (argptr, error);
    vsprintf (text, error, argptr);
    va_end (argptr);

    errorFileHandle = Sys_FileOpenWrite("ERROR.TXT");
    if (errorFileHandle) {
	Sys_FileWrite(errorFileHandle, text, strlen(text));
	Sys_FileClose(errorFileHandle);
    }

	Host_Shutdown();

	if (quakeparms.membase) {
        FreeMem(aw_heap_allocation, aw_heap_allocation_size);
        aw_heap_allocation = NULL;
        quakeparms.membase = NULL;
    }



	AW_PlatformClose();
	exit(EXIT_FAILURE);
}



static int xlate[0x68] = {
    '`', '1', '2', '3', '4', '5', '6', '7',
    '8', '9', '0', '-', '=', '\\', 0, '0',
    'q', 'w', 'e', 'r', 't', 'y', 'u', 'i',
    'o', 'p', K_F11, K_F12, 0, '0', '2', '3',
    'a', 's', 'd', 'f', 'g', 'h', 'j', 'k',
    'l', ';', '\'', K_ENTER, 0, '4', '5', '6',
    K_SHIFT, 'z', 'x', 'c', 'v', 'b', 'n', 'm',
    ',', '.', '/', 0, '.', '7', '8', '9',
    K_SPACE, K_BACKSPACE, K_TAB, K_ENTER, K_ENTER, K_ESCAPE, K_F11,
    0, 0, 0, '-', 0, K_UPARROW, K_DOWNARROW, K_RIGHTARROW, K_LEFTARROW,
    K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8,
    K_F9, K_F10, '(', ')', '/', '*', '=', K_PAUSE,
    K_SHIFT, K_SHIFT, 0, K_CTRL, K_ALT, K_ALT, 0, K_CTRL
};


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
        case IDCMP_RAWKEY:
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
                    if ((code & ~IECODE_UP_PREFIX) >= 0x68) break;
                    if (code & IECODE_UP_PREFIX) {
		Key_Event(xlate[code & ~IECODE_UP_PREFIX], false);
	} else {
		Key_Event(xlate[code], true);
	}
                    break;
            }
            break;

        case IDCMP_MOUSEBUTTONS:
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
          mouseX = mousex;
          mouseY = mousey;
          mouse_has_moved = true;
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
