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
// quakedef.h -- primary header for client

//#define	GLTEST			// experimental stuff

#define	QUAKE_GAME			// as opposed to utilities

#define	VERSION				1.09
#define	GLQUAKE_VERSION		1.00
#define	D3DQUAKE_VERSION	0.01
#define	WINQUAKE_VERSION	0.996
#define	LINUX_VERSION		1.30
#define	X11_VERSION			1.10

//define	PARANOID			// speed sapping error checking

#ifdef QUAKE2
#define	GAMENAME	"id1"		// directory to look in by default
#else
#define	GAMENAME	"id1"
#endif

/* Inspected Hlaalu stair ramps reach normal Z=0.69766 (~45.76 degrees). */
#define AW_WALKABLE_Z 0.69f

#include <math.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>

#if defined(AMIGA) || (defined(_WIN32) && !defined(WINDED))

#if defined(_M_IX86)
#define __i386__	1
#endif

void	VID_LockBuffer (void);
void	VID_UnlockBuffer (void);

#else

#define	VID_LockBuffer()
#define	VID_UnlockBuffer()

#endif

#if defined __i386__ // && !defined __sun__
#define id386	1
#else
#define id386	0
#endif

#if id386
#define UNALIGNED_OK	1	// set to 0 if unaligned accesses are not supported
#else
#define UNALIGNED_OK	0
#endif

// !!! if this is changed, it must be changed in d_ifacea.h too !!!
#define CACHE_SIZE	32		// used to align key data structures

#define UNUSED(x)	(x = x)	// for pesky compiler / lint warnings

#define	MINIMUM_MEMORY			0x550000
#define	MINIMUM_MEMORY_LEVELPAK	(MINIMUM_MEMORY + 0x100000)

#define MAX_NUM_ARGVS	50

// up / down
#define	PITCH	0

// left / right
#define	YAW		1

// fall over
#define	ROLL	2


#define	MAX_QPATH		64			// max length of a quake game pathname
#define	MAX_OSPATH		128			// max length of a filesystem pathname

#define	ON_EPSILON		0.1			// point on plane side epsilon

#define	MAX_MSGLEN		8000		// max length of a reliable message
#define	MAX_DATAGRAM	1024		// max length of unreliable message

//
// per-level limits
//
#define	MAX_EDICTS		600			// FIXME: ouch! ouch! ouch!
#define	MAX_LIGHTSTYLES	64
#define	MAX_MODELS		256			// these are sent over the net as bytes
#define	MAX_SOUNDS		256			// so they cannot be blindly increased

#define	SAVEGAME_COMMENT_LENGTH	39

#define	MAX_STYLESTRING	64

//
// stats are integers communicated to the client by the server
//
#define	MAX_CL_STATS		32
#define	STAT_HEALTH			0
#define	STAT_FRAGS			1
#define	STAT_WEAPON			2
#define	STAT_AMMO			3
#define	STAT_ARMOR			4
#define	STAT_WEAPONFRAME	5
#define	STAT_SHELLS			6
#define	STAT_NAILS			7
#define	STAT_ROCKETS		8
#define	STAT_CELLS			9
#define	STAT_ACTIVEWEAPON	10
#define	STAT_TOTALSECRETS	11
#define	STAT_TOTALMONSTERS	12
#define	STAT_SECRETS		13		// bumped on client side by svc_foundsecret
#define	STAT_MONSTERS		14		// bumped by svc_killedmonster

// stock defines

#define	IT_SHOTGUN				1
#define	IT_SUPER_SHOTGUN		2
#define	IT_NAILGUN				4
#define	IT_SUPER_NAILGUN		8
#define	IT_GRENADE_LAUNCHER		16
#define	IT_ROCKET_LAUNCHER		32
#define	IT_LIGHTNING			64
#define IT_SUPER_LIGHTNING      128
#define IT_SHELLS               256
#define IT_NAILS                512
#define IT_ROCKETS              1024
#define IT_CELLS                2048
#define IT_AXE                  4096
#define IT_ARMOR1               8192
#define IT_ARMOR2               16384
#define IT_ARMOR3               32768
#define IT_SUPERHEALTH          65536
#define IT_KEY1                 131072
#define IT_KEY2                 262144
#define	IT_INVISIBILITY			524288
#define	IT_INVULNERABILITY		1048576
#define	IT_SUIT					2097152
#define	IT_QUAD					4194304
#define IT_SIGIL1               (1<<28)
#define IT_SIGIL2               (1<<29)
#define IT_SIGIL3               (1<<30)
#define IT_SIGIL4               (1<<31)

//===========================================
//rogue changed and added defines

#define RIT_SHELLS              128
#define RIT_NAILS               256
#define RIT_ROCKETS             512
#define RIT_CELLS               1024
#define RIT_AXE                 2048
#define RIT_LAVA_NAILGUN        4096
#define RIT_LAVA_SUPER_NAILGUN  8192
#define RIT_MULTI_GRENADE       16384
#define RIT_MULTI_ROCKET        32768
#define RIT_PLASMA_GUN          65536
#define RIT_ARMOR1              8388608
#define RIT_ARMOR2              16777216
#define RIT_ARMOR3              33554432
#define RIT_LAVA_NAILS          67108864
#define RIT_PLASMA_AMMO         134217728
#define RIT_MULTI_ROCKETS       268435456
#define RIT_SHIELD              536870912
#define RIT_ANTIGRAV            1073741824
#define RIT_SUPERHEALTH         2147483648

//MED 01/04/97 added hipnotic defines
//===========================================
//hipnotic added defines
#define HIT_PROXIMITY_GUN_BIT 16
#define HIT_MJOLNIR_BIT       7
#define HIT_LASER_CANNON_BIT  23
#define HIT_PROXIMITY_GUN   (1<<HIT_PROXIMITY_GUN_BIT)
#define HIT_MJOLNIR         (1<<HIT_MJOLNIR_BIT)
#define HIT_LASER_CANNON    (1<<HIT_LASER_CANNON_BIT)
#define HIT_WETSUIT         (1<<(23+2))
#define HIT_EMPATHY_SHIELDS (1<<(23+3))

//===========================================

#define	MAX_SCOREBOARD		16
#define	MAX_SCOREBOARDNAME	32

#define	SOUND_CHANNELS		8

// This makes anyone on id's net privileged
// Use for multiplayer testing only - VERY dangerous!!!
// #define IDGODS

#include "common.h"
#include "bspfile.h"
#include "vid.h"
#include "sys.h"
#include "zone.h"
#include "mathlib.h"

typedef struct
{
    vec3_t	origin;
    vec3_t	angles;
    int		modelindex;
    int		frame;
    int		colormap;
    int		skin;
    int		effects;
} entity_state_t;


#include "wad.h"
#include "draw.h"
#include "cvar.h"
#include "screen.h"
#include "net.h"
#include "protocol.h"
#include "cmd.h"
#include "sbar.h"
#include "sound.h"
#include "render.h"
#include "client.h"
#include "progs.h"
#include "server.h"

#ifdef GLQUAKE
#include "gl_model.h"
#else
#include "model.h"
#include "d_iface.h"
#endif

#include "input.h"
#include "world.h"
#include "keys.h"
#include "console.h"
#include "view.h"
#include "menu.h"
#include "crc.h"
#include "cdaudio.h"

#ifdef GLQUAKE
#include "glquake.h"
#endif

//=============================================================================

// the host system specifies the base of the directory tree, the
// command line parms passed to the program, and the amount of memory
// available for the program to use

typedef struct
{
    char	*basedir;
    char	*cachedir;		// for development over ISDN lines
    int		argc;
    char	**argv;
    void	*membase;
    int		memsize;
} quakeparms_t;


//=============================================================================



extern qboolean noclip_anglehack;


//
// host
//
extern	quakeparms_t host_parms;

extern	cvar_t		sys_ticrate;
extern	cvar_t		sys_nostdout;
extern	cvar_t		developer;

extern	qboolean	host_initialized;		// true if into command execution
extern	double		host_frametime;
extern	byte		*host_basepal;
extern	byte		*host_colormap;
extern	int			host_framecount;	// incremented every frame, never reset
extern	double		realtime;			// not bounded in any way, changed at
                                        // start of every frame, never reset

void Host_ClearMemory (void);
void Host_ServerFrame (void);
void Host_InitCommands (void);
void Host_Init (quakeparms_t *parms);
void Host_Shutdown(void);
void Host_Error (char *error, ...);
void Host_EndGame (char *message, ...);
void Host_Frame (float time);
void Host_Quit_f (void);
void Host_ClientCommands (char *fmt, ...);
void Host_ShutdownServer (qboolean crash);

extern qboolean		msg_suppress_1;		// suppresses resolution and cache size console output
                                        //  an fullscreen DIB focus gain/loss
extern int			current_skill;		// skill level for currently loaded level (in case
                                        //  the user changes the cvar while the level is
                                        //  running, this reflects the level actually in use)

extern qboolean		isDedicated;

extern int			minimum_memory;

//
// chase
//
extern	cvar_t	chase_active;

void Chase_Init (void);
void Chase_Reset (void);
void Chase_Update (void);

/* AmiWind standalone runtime modules, GPL-2.0-or-later. */
void AW_ProfileFrame(void);
void AW_ProfileClose(void);
void AW_Mark(int stage);
void AW_EndMark(int stage);
void AW_AudioLate(int missed);
void AW_MusicPaint(portable_samplepair_t *dst,int count);
void AW_FogInit(void);
void AW_FogDraw(void);

void AW_PlatformInit(void);
void AW_PlatformClose(void);
void AW_CullBegin(void);
int AW_NodeVisible(short *bounds);

void AW_DebugInit(void);
void AW_InputDebugInit(void);
extern qboolean noclip_anglehack;
int AW_ModelVisible(vec3_t origin,float radius);

qboolean AW_FindSafeSpawn(edict_t *,vec3_t,vec3_t);
qboolean AW_PlacePlayer(edict_t *,vec3_t);

void AW_MenuMouse(int dx,int dy);
int AW_DebugCoordsEnabled(void);
int AW_SeaLevelEnabled(void);
void AW_NoclipVelocity(vec3_t view, usercmd_t *cmd, float maximum, vec3_t out);
int AW_DebugOverlaysEnabled(void);
void IN_AWClearButtons(void);

void AW_ConsoleInit(void);
void AW_ConsoleSetSmall(int value);
int AW_ConsoleCharWidth(void);
int AW_ConsoleCharHeight(void);
void AW_ConsoleCharacter(int x,int y,int c);
void AW_SmallString(int x,int y,const char *text);
extern int con_fullscreen;
int Con_ScrollPage(void);
int Con_ScrollMax(void);
void AW_ConsoleBackground(int lines);
int AW_DebugTranslate(int argc,char **argv,char *out,int capacity);

int AW_Interior(void);
int AW_SceneUse(void);
int AW_TravelKey(int key);
int AW_TravelDraw(void);
void AW_SceneDraw(void);
void AW_SceneSpawn(edict_t *p);
int AW_InteriorPlace(edict_t *p,vec3_t preferred);
void AW_SceneInit(void);
void AW_DoorAudioInit(void);
float AW_DoorSound(unsigned reference,int closing);
void AW_SceneTick(void);
void AW_SceneryClear(void);
void AW_SceneryBegin(const char *entities);
int AW_SceneryCapture(edict_t *e);
void AW_SceneryLink(void);
void AW_SceneryClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *best);
trace_t SV_ClipMoveToEntity(edict_t *,vec3_t,vec3_t,vec3_t,vec3_t);
void AW_MusicSceneEvent(const char *why);
int AW_MusicStartTrack(int id);
void AW_MusicTitle(void);

#ifndef AMIWIND_SPRITE_HANDS
#define AMIWIND_SPRITE_HANDS 0
#endif
void AW_HandSpritesInit(void);
void AW_HandSpritesDraw(void);
int AW_HandSpritesValidate(byte *data,unsigned long bytes);

/* Original-style private-asset UI, independent of the console. */
void AW_UIInit(void);
int AW_UIValidateFont(const byte *,int);
int AW_UIBackground(void);
int AW_MenuFrontEnd(void);
byte *AW_UIMenuPalette(void);
int AW_UIColor(int,int,int);
void AW_UIFill(int,int,int,int,int);
void AW_UIScrollbar(int,int,int,int,int,int);
int AW_UIScrollHit(int,int,int,int,int,int,int,int);
void AW_UIBox(int,int,int,int);
void AW_UIFrame(int,int,int,int);
void AW_UIOuterFrame(void);
int AW_UIFrameEnabled(void);
void AW_UIFrameToggle(void);
void AW_UIText(int,int,const char *,int);
void AW_UITextBox(int,int,int,int,const char *,int);
int AW_UILogo(int,int);
void AW_UILoading(void);
int AW_LoadingScreen(void);
typedef enum { AW_LOADING_NORMAL, AW_LOADING_BLANK, AW_LOADING_FROZEN } aw_loading_style_t;
void AW_SetNextLoadingStyle(aw_loading_style_t);
void AW_BeginLoadingStyle(void);
void AW_EndLoadingStyle(void);
int AW_LoadingFrozen(void);
int AW_RegionLoadingFrozen(void);
void AW_RegionLoadingToggle(void);
extern qboolean aw_loading_music;
extern void (*aw_load_audio_tick)(void);
void S_LoadingUpdate(void);
int AW_UIWidth(const char *);
int AW_UIHeight(void);
const char *AW_UILine(const char *,int,char *,int);
void AW_UISubtitle(const char *,const char *,double);
void AW_UICenterMessage(const char *);
void AW_UIDraw(void);
int AW_UIDialogueMethod(void);
int AW_UISpeakerAtRight(void);
int AW_UIVoiceNames(void);
int AW_UIVoiceStyle(void);
int AW_UIVoiceAimOnly(void);
void AW_UIVoiceNamesToggle(void);
void AW_UIDialogueCycle(int step);
void AW_UIVoiceSubtitle(const char *name,const char *text,double duration);
int AW_SceneUIOption(int option,int change);
void AW_UITargetName(const char *name);
void AW_UIObjectName(const char *name,int style);
int AW_IntroPromptActive(void);
const char *AW_SceneTargetName(void);
edict_t *AW_NPCTarget(edict_t *player,vec3_t angles);
int AW_NPCFloor(edict_t *actor);
int AW_AliasBudgetAllows(int vertices,int triangles);
int AW_AliasExceptionAllows(const char *name,int vertices,int triangles,const byte *raw,int bytes);
int AW_GalleryActive(void);
int AW_GalleryModal(void);
void AW_GalleryMouse(int dx,int dy);
void AW_GalleryInit(void);
void AW_GalleryEntities(void);
void AW_GallerySpawn(edict_t *player);
int AW_GalleryKey(int key,int down,int shift,int control);
void AW_GalleryDraw(void);
void AW_StreamInit(void);
int AW_StreamOption(int,int);
float AW_StreamLookahead(void);
void AW_StreamTransitionBegin(void);
void AW_StreamTransitionReady(void);
void AW_StreamPresented(void);
int AW_CellChangeMethod(void);
void AW_StreamTick(const char *next);
void AW_StreamLoadBegin(const char *name);
void AW_StreamLoadEnd(const char *name,double world,double actors,double total);
void AW_UIHud(void);
void AW_UIBar(int,int,int,int,int,float);

int AW_SpeechValidate(const byte *p,int n);
void AW_SpeechStart(int entity,int channel,const char *sound,int start,int length,int speed,int skip);
void AW_SpeechStop(int entity,int channel);
double AW_SpeechRemaining(void);
int AW_SpeechPose(int entity,int current,int frames,const char *model);
void AW_SpeechRelink(void);
int AW_NavDecode(const byte *,int);
int AW_NavLoad(const char *);
int AW_NavStart(edict_t *,vec3_t);
int AW_NavStep(double,int);
qboolean AW_ActorStep(edict_t *,vec3_t,double);
int AW_MovieStart(void);
void AW_MovieInit(void);
void AW_MovieStartup(void);
int AW_MovieActive(void);
void AW_MovieUpdate(void);
void AW_MovieDraw(void);
void AW_MoviePaint(portable_samplepair_t *,int,int);
byte *AW_MoviePalette(void);
int AW_MovieKey(int key,int down);
void AW_IntroBegin(void);
void AW_IntroInit(void);
void AW_UIBookBegin(void);
int AW_UIFontSize(void);
int AW_UISetFontSize(int size);
void AW_UIBookEnd(void);
void AW_UISmallBegin(void);
void AW_UISmallEnd(void);
int AW_ReaderOpen(const char *stem,int action);
int AW_ReaderActive(void);
int AW_ReaderKey(int key);
void AW_ReaderDraw(void);
void AW_ReaderMouse(int dx,int dy);
int AW_ReaderResult(void);
void AW_BirthArt(int index,int x,int y);
int AW_IntroSpeak(int role,const char *stem);
edict_t *AW_IntroRole(int role);
int AW_OpeningTick(void);
int AW_OpeningLocked(void);
void AW_OpeningSpawn(void);
int AW_OpeningUse(void);
int AW_OpeningHint(const char **name,const char **action);
int AW_BarrierDecode(const byte *raw,int size);
int AW_BarrierLoad(void);
void AW_BarrierClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,edict_t *entity,trace_t *trace);
void AW_IntroSpawn(void);
void AW_IntroTick(void);
void AW_IntroMove(usercmd_t *);
int AW_IntroButtons(int);
int AW_IntroImpulse(int);
int AW_IntroUse(void);
int AW_IntroKey(int);
void AW_IntroDraw(void);

void AW_WaitInit(void);
void AW_WaitTick(void);
int AW_WaitKey(int key);
int AW_WaitDraw(void);

void AW_UICenteredLines(int x,int y,int w,int h,const char *text);
const char *AW_UIPage(const char *text,int width,int rows,char *out,int capacity);

const char *AW_SceneWorldModel(const char *name);
