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
// AmiWind: the version as text for the console lines, no float formatting (ENGINE-FPU-UNIMPL-31)
#define	AW_STRINGIFY(x)		#x
#define	AMIQUAKE_VERSION_LINE_OF(v)	"AmiQuake: VERSION " AW_STRINGIFY (v)
// AmiWind: the console line under the version lines (owner, 11 October 2026)
#define	AW_CONSOLE_HELP_LINE	"Type: \"dbg help\" for help."
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
/* Step rules (docs/STEP_MOVEMENT.md, STEP-MOVEMENT-OPENMW-RULES-48): aw_step_rules 1 makes the walking player step
 * and stand by Morrowind's rules as OpenMW states them; 0 (default) keeps the Quake rules above. OpenMW's walkable
 * slope: normal z over cos 46 degrees (sMaxSlope 46, strictly greater). aw_step_rules lives in aw_walk.c. */
#define AW_OPENMW_WALKABLE_Z 0.69465837f
#define AW_WALKABLE(nz) (aw_step_rules.value ? (nz) > AW_OPENMW_WALKABLE_Z : (nz) >= AW_WALKABLE_Z)

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

#define MAX_MSGLEN 16380 /* Dense static foliage sign-on; loopback needs four extra bytes. */
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
extern	cvar_t		aw_step_rules;	/* aw_walk.c: AW_WALKABLE, the step rules (docs/STEP_MOVEMENT.md) */

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
void Host_Error (char *error, ...) __attribute__((format(printf, 1, 2)));
void Host_EndGame (char *message, ...) __attribute__((format(printf, 1, 2)));
void Host_Frame (float time);
void Host_Quit_f (void);
void Host_ClientCommands (char *fmt, ...) __attribute__((format(printf, 1, 2)));
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
void AW_FpuCountInit(void);
void AW_FpuStatusInit(void);
void AW_FpuStatusFormat(char *out, int size, unsigned attn, const char *library, int version, int revision);
void AW_FpuStatusInit(void);
void AW_FpuStatusFormat(char *out, int size, unsigned attn, const char *library, int version, int revision);
void AW_FpuCountFrame(void);
void AW_ProfileClose(void);
void AW_Mark(int stage);
void AW_EndMark(int stage);
void AW_C2PRows(int rows, int height);
void AW_AudioLate(int missed);
void AW_MusicPaint(portable_samplepair_t *dst,int count);
unsigned long AW_MusicSilentSpans(void);	/* the music blocks that ran dry so far (AUDIO-LOAD-29: per load) */
void AW_MusicLoadPump(void);	/* the music stream's reads go on during a load (aw_music.c; never waits) */
void AW_FogInit(void);
void AW_FogDraw(void);

void AW_PlatformInit(void);
void AW_PlatformClose(void);
void AW_CullBegin(void);
int AW_NodeVisible(short *bounds);

void AW_DebugInit(void);
void AW_InputDebugInit(void);
void AW_InputGuardInit(void);
void AW_InputGuardShutdown(void);
extern qboolean noclip_anglehack;
int AW_ModelVisible(vec3_t origin,float radius);
/* aw_fog.c far tests of a brush model pass (aw_cull 2 and up). */
enum {AW_FAR_DRAW,AW_FAR_SKIP,AW_FAR_SIZE,AW_FAR_FACES};
int AW_BrushPassFar(vec3_t origin,float radius,const float *minmaxs);
void AW_FarPassBegin(int result);
void AW_FarDetailSavedBefore(int config_without_setting);
int AW_ConfigWithout(const char *name);
int AW_FogFullDepthValue(int distance);
float AW_SizeCutShare(int preset,float radius);
/* aw_cull (aw_fog.c): the far test 0..7 in its low bits, then the fog rule and
 * whole-structure cuts as switches (CHIM-BRIDGE-POP-PIECES-44). */
#define AW_CULL_TEST 7
#define AW_CULL_FOG_RULE 8
#define AW_CULL_GROUPS 16
#define AW_CULL_MAX 31
float AW_SizeCutDepthShare(float radius);
void AW_FarGroup(const float *box);
int AW_PassVisible(vec3_t origin,float radius);
extern float aw_far_depth[4],aw_far_down[4],aw_far_view[4],aw_far_detail_pixels;
extern int aw_far_faces;
extern int (*aw_flame_depth_limit)(void);

qboolean AW_FindSafeSpawn(edict_t *,vec3_t,vec3_t);
qboolean AW_PlacePlayer(edict_t *,vec3_t);

void AW_MenuMouse(int dx,int dy);
int AW_DebugCoordsEnabled(void);
int AW_SeaLevelEnabled(void);
void AW_NoclipVelocity(vec3_t view, usercmd_t *cmd, float maximum, vec3_t out);
void AW_NoclipDebugVelocity(vec3_t view,usercmd_t *cmd,float maximum,
                           int fast,int shifted,float shift_scale,vec3_t out);
int AW_DebugOverlaysEnabled(void);
/* Photo mode (aw_photo.c): dbg photomode / dbg killhud, dbg crosshair. */
void AW_PhotoInit(void);
int AW_PhotoModeActive(void);
int AW_PhotoModeAvailable(void);
int AW_PhotoModeSet(int on);
int AW_PhotoModeSetQuiet(int on);
void AW_PhotoConfigRestore(void);
void AW_PhotoDraw(void);
int AW_PhotoNoticeShowing(void);
void AW_PhotoConsoleReminder(void);
int AW_PhotoKey(int key);
int AW_CrosshairShown(void);
void AW_CrosshairSet(int on);
/* UI-HUD-TOGGLE-KEY-51: Ctrl+Alt+H / dbg photomode hud; aw_hud_hidden lives in view.c (not saved). */
void AW_HudToggle(void);
extern int aw_hud_hidden;
/* Crosshair colour (shape 0) and shape (shape 1): aw_crosshair_colour / aw_crosshair_shape. */
int AW_CrosshairStyleCount(int shape);
int AW_CrosshairStyle(int shape);
const char *AW_CrosshairStyleName(int shape,int value);
const unsigned char *AW_CrosshairColourRGB(int value);
void AW_CrosshairStyleSet(int shape,int value);
void AW_CrosshairDraw(int x,int y);   /* view.c: the crosshair cell at x,y (centre x+3,y+3), also the Options preview */
/* Mouse sensitivity in tenths (Quake's sensitivity cvar; default 3.0 = 30), dbg sensitivity. */
#define AW_SENSITIVITY_MENU_MIN 5
#define AW_SENSITIVITY_MENU_MAX 100
#define AW_SENSITIVITY_CONSOLE_MIN 1
#define AW_SENSITIVITY_CONSOLE_MAX 200
int AW_SensitivityTenths(void);
void AW_SensitivitySetTenths(int tenths);
void IN_AWClearButtons(void);

void AW_ConsoleInit(void);
void AW_ConsoleSetSmall(int value);
int AW_ConsoleCharWidth(void);
int AW_ConsoleCharHeight(void);
void AW_ConsoleCharacter(int x,int y,int c);
void AW_SmallString(int x,int y,const char *text);
void AW_SmallStringColor(int,int,int,const char *,int);
int AW_LightGalleryDraw(void);
extern int con_fullscreen;
int Con_ScrollPage(void);
int Con_ScrollMax(void);
void AW_ConsoleBackground(int lines);
int AW_DebugTranslate(int argc,char **argv,char *out,int capacity);

int AW_Interior(void);
int AW_SceneUse(void);
/* Activation (v0.0.51): a script's Activate on a load door of this map; the scripts' take-over of a door's use. */
int AW_SceneActivate(unsigned reference);
extern int (*aw_scene_intercept)(unsigned reference);
int AW_TravelKey(int key);
int AW_TravelDraw(void);
void AW_SceneDraw(void);
void AW_SceneSpawn(edict_t *p);
void AW_SceneSignon(void);
int AW_InteriorPlace(edict_t *p,vec3_t preferred);
int AW_RecoverPlace(edict_t *p,vec3_t preferred);
int AW_Unstuck(edict_t *p);
void AW_SceneInit(void);
void AW_DoorAudioInit(void);
float AW_DoorSound(unsigned reference,int closing);
/* Compiled game scripts (aw_mwhost.c, aw_mwvm.c; docs/MWSCRIPT_BYTECODE.md), experimental: aw_mwscript 0 by default. */
void AW_MwscriptInit(void);
void AW_MwscriptTick(float dt);
/* The actor record behind the scripts (aw_mwhost.c, aw_actorstate.h; docs/ACTOR_STATE.md): opens the actor table of
 * id1/mwscript.awm (1 ready). The hooks the other tables fill: StopCombat (aw_combat.h AW_CombatActorEnd) and
 * AIWander (aw_ambient.h AW_AmbientWander); NULL: the call is logged once and does nothing. The Speed attribute of
 * an actor's record for the ambient walk (aw_ambient_speed_attribute), -1 when it has none. */
int AW_MwscriptActors(void);
struct edict_s;
extern int (*aw_mwscript_combat_end)(struct edict_s *e);
extern int (*aw_mwscript_wander)(struct edict_s *e,int distance,int duration,int hour,const unsigned char idle[8],int repeat);
extern int (*aw_mwscript_ai_package)(struct edict_s *e,int *done);   /* the ambient tables' AI package (aw_mwhost.c) */
int AW_MwscriptSpeedAttribute(struct edict_s *e);
/* Object state the scripts set (aw_mwhost.c): 1 when Disable hid the placement REFERENCE; its lock level, or
 * ORIGINAL when no script set one (0 unlocked .. 100). */
int AW_ObjectDisabled(unsigned int reference);
int AW_ObjectLockLevel(unsigned int reference,int original);
int AW_MusicScriptTrack(int track);
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
void AW_MusicTitleAfter(double seconds);
void AW_MusicHold(void);
/* aw_music.c: the custom OST player (CUSTOM-OST-SLOT-53): hold the playlist (silence), play the custom track (its id
 * or -1: none built in, music off), stop (the playlist back), what custom track is playing (-1 none). */
void AW_MusicCustomHold(void);
int AW_MusicCustomPlay(void);
void AW_MusicCustomStop(void);
int AW_MusicCustomPlaying(void);

#ifndef AMIWIND_SPRITE_HANDS
#define AMIWIND_SPRITE_HANDS 0
#endif
void AW_HandSpritesInit(void);
void AW_HandSpritesDraw(void);
void AW_GuardTorchInit(void);
void AW_GuardTorchLoadAssets(const byte *torch);
void AW_GuardTorchUpdate(void);
void AW_GuardTorchDraw(void);
void AW_StaticFlamesDraw(void);
/* One placed static flame (aw_flame entity); shape: size, rise, spread (0 = legacy). */
typedef struct {vec3_t origin;float scale,shape[3];} aw_static_flame_t;
int AW_StaticFlamesPick(const aw_static_flame_t *flames,int count,int nearest,int *chosen);
void AW_EmberSpawn(const vec3_t org,float spread,float rise);
entity_t *AW_GuardTorchEntity(entity_t *entity);
void AW_TorchInit(void);
float AW_TorchLightRadius(void);
int AW_TorchFlameCoreColor(void);
byte AW_TorchFlameColor(byte original,int texel,float age,int core);
void AW_TorchUpdate(void);
void AW_TorchDraw(void);
void AW_TorchLoadAssets(void);
void AW_TorchViewModel(void);
int AW_TorchFrame(void);
double AW_TorchAnimationTime(void);
void AW_TorchRestoreAnimation(double time);
void AW_TorchResetAnimation(void);
int AW_TorchEquipped(void);
int AW_TorchAssetsValidate(const byte *p,int size);
int AW_HandSpritesValidate(byte *data,unsigned long bytes);

/* Original-style private-asset UI, independent of the console. */
void AW_UIInit(void);
int AW_ModalWorldFrozen(void);
extern int (*aw_death_prompt_active)(void); /* aw_view: finished death animation, choice still open */
int AW_ModalWorldHidden(void);
extern int (*aw_menu_fullscreen)(void);   /* aw_menu.c: the full-screen Options panel is open */
int AW_ModalBlackBackground(void);
int AW_UIMode(void);
void AW_SceneCancelTransition(void);
void AW_ModalFrame(void);
int AW_UIValidateFont(const byte *,int);
int AW_UIBackground(void);
int AW_MenuFrontEnd(void);
byte *AW_UIMenuPalette(void);
int AW_UIColor(int,int,int);
/* aw_ui.c: the original map arrow (16x16 in gfx/ui.awu, rows 64 bytes apart, 255 clear), NULL when absent. */
const byte *AW_UIMapArrow(void);
void AW_UIFill(int,int,int,int,int);
void AW_UIScrollbar(int,int,int,int,int,int);
int AW_UIScrollHit(int,int,int,int,int,int,int,int);
void AW_UIBox(int,int,int,int);
void AW_UIHudPlaceholders(int y,int channels);   /* the interim weapon/magic marks */
extern int (*aw_hud_item_boxes)(int y,int channels);   /* aw_icons.c: the original boxes */
void AW_IconsInit(void);
void AW_UIFrame(int,int,int,int);
void AW_UIOuterFrame(void);
int AW_UIFrameEnabled(void);
void AW_UIFrameToggle(void);
void AW_UIText(int,int,const char *,int);
void AW_UITextBox(int,int,int,int,const char *,int);
void AW_UITextCentred(int,int,int,int,const char *,int);   /* centred by painted bounds */
extern int (*aw_title_bar)(int x,int y,int w,const char *title);   /* aw_icons.c: the original title bar */
extern const char *(*aw_hand_to_hand_name)(void);   /* aw_icons.c: GMST sSkillHandtohand */
extern int (*aw_inventory_row_icon)(int slot,const char *id,int equipped,int x,int y);   /* aw_icons.c */
int AW_UILogo(int,int);
void AW_UILoading(void);
void AW_UIRoomRefused(const char *first,const char *second);
int AW_SceneRoomFastMb(const char *target);
int AW_SceneFrameFastMb(const char *target);
int AW_SceneRoomRefused(void);
int AW_SceneRoomRefuse(const char *target);
int AW_SceneFrameRefuse(edict_t *p,const char *target);   /* aw_scene.c: a marked CHIM frame refused on less RAM */
int AW_SceneEntryRefuse(const char *target,const float *point,int to_menu);   /* CHIM-32MB-SAVE-ENTRY-48 */
int AW_SceneSaveEntryRefuse(const char *scene,const float *position);
int AW_SceneMapRefuse(const char *name);
extern long aw_fast_ram_found_mb;
int AW_LoadingScreen(void);
typedef enum { AW_LOADING_NORMAL, AW_LOADING_BLANK, AW_LOADING_FROZEN } aw_loading_style_t;
void AW_SetNextLoadingStyle(aw_loading_style_t);
void AW_SetNextLoadingDelay(void);
int AW_LoadingDelayed(void);
int AW_LoadingDelayExpired(void);
void AW_BeginLoadingStyle(void);
void AW_EndLoadingStyle(void);
int AW_LoadingFrozen(void);
int AW_RegionLoadingFrozen(void);
void AW_RegionLoadingToggle(void);
extern qboolean aw_loading_music;
extern void (*aw_load_audio_tick)(void);
extern const char *aw_load_phase;	/* the map load step now running (snd_dma.c; AUDIO-LOAD-29) */
void S_LoadingMark(void);		/* a frame step reached: one line in the load's gap trace */
void S_LoadingUpdate(void);
int AW_UIWidth(const char *);
int AW_UIHeight(void);
const char *AW_UILine(const char *,int,char *,int);
void AW_UISubtitle(const char *,const char *,double);
int AW_UISubtitleIs(const char *text);
void AW_UIPickupNotice(const char *text,double duration);
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
edict_t *AW_NPCTargetReach(edict_t *player,vec3_t angles,float reach);
int AW_NPCFloor(edict_t *actor);
int AW_NPCFloorRetry(void);
int AW_AliasBudgetAllows(int vertices,int triangles);
int AW_AliasExceptionAllows(const char *name,int vertices,int triangles,const byte *raw,int bytes);
unsigned int AW_AliasCrcAdd(unsigned int crc,const byte *raw,size_t n);
int AW_AliasExceptionMatches(const char *name,int vertices,int triangles,int bytes,unsigned long crc);
/* The alias stream reader's ordinary vertex bound (the original 2,000); an extended model up to MAXALIASVERTS
 * (r_local.h: 3,072) needs its byte-matching model-budgets.txt line, as in the generic loader. */
#define AW_ALIAS_NORMAL_VERTS	2000
int AW_GalleryActive(void);
int AW_GalleryOmitted(void);
/* Quick test builds (tools/build.py --exclude): id1/excluded-content.txt, aw_excluded.c. */
int AW_ContentExcluded(const char *group);
const char *AW_ContentExcludedNotice(const char *group);
int AW_ContentExcludedSay(const char *group,int always);
void AW_ContentExcludedStartup(void);
void AW_ExcludedReset(void);
int AW_TorchTestActive(void);
int AW_DebugTestInputActive(void);
int AW_GalleryModal(void);
void AW_GalleryMouse(int dx,int dy);
void AW_GalleryInit(void);
void AW_GalleryEntities(void);
void AW_GallerySpawn(edict_t *player);
int AW_GalleryKey(int key,int down,int shift,int control);
void AW_GalleryDraw(void);
void AW_SweepInit(void);   /* dbg sweep (aw_sweep.c, ENTITY-SWEEP-AB) */
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
void AW_SpeechShiftTiming(int elapsed,int start_time);
int AW_NavDecode(const byte *,int);
int AW_NavLoad(const char *);
int AW_NavStart(edict_t *,vec3_t);
int AW_NavStep(double,int);
qboolean AW_ActorStep(edict_t *,vec3_t,double);
/* Character animation kit (aw_anim.c, aw_anim.h). */
void AW_AnimInit(void);
void AW_AnimKitInit(void);
void AW_AnimKitTick(void);
/* The Halloween scene (aw_halloween.c, aw_halloween.h). */
void AW_HalloweenInit(void);
void AW_HalloweenTick(void);
void AW_HalloweenDraw(void);
int AW_HalloweenCamera(float origin[3],float angles[3]);/* Debug companion (aw_companion.c). */
void AW_CompanionInit(void);
void AW_CompanionPhysics(void);
void AW_CompanionSceneSpawn(edict_t *player);
int AW_CompanionEdict(edict_t *e);
int AW_CompanionHome(edict_t *e,vec3_t origin,vec3_t angles);
int AW_CompanionSkipSave(edict_t *e);
void AW_CompanionSaveSwap(int begin);
int AW_CompanionCrosshair(int x,int y);
int AW_CompanionButtons(int bits);
extern int (*aw_combat_buttons)(int bits);
int AW_CompanionPickMode(void);
int AW_CompanionPickAim(void);
/* Hooks set by AW_CompanionInit, defined beside their callers (NULL in
 * fixtures that compile those files alone): view.c, cl_input.c,
 * aw_scene.c, aw_save.c. */
extern int (*aw_companion_crosshair)(int x,int y);
extern int (*aw_companion_buttons)(int bits);
extern void (*aw_companion_scene)(edict_t *player);
extern int (*aw_companion_home)(edict_t *e,vec3_t origin,vec3_t angles);
/* Melee combat for every NPC (aw_combat.c, aw_combat.h) and the Vivec Arena
 * debug minigame (aw_arena.c). Hooks defined beside their callers: aw_ui.c,
 * aw_scene.c. */
void AW_CombatInit(void);
void AW_CombatPhysics(void);
int AW_CombatHurtPlayer(float damage,const char *cause);
/* Lava damage and the in-lava view tint (aw_lava.c, aw_lava.h, docs/LAVA.md). */
void AW_LavaInit(void);
void AW_LavaPhysics(void);
int AW_LavaContentsShift(int eye_contents,int rgb[3],int *percent);
void AW_LavaEmbersDraw(void);
int AW_LavaPoolCount(void);
void AW_MusicCombat(int on);
void AW_MusicDeath(void);
extern int (*aw_combat_enemy_bar)(float *fraction,float *alpha);
extern int (*aw_combat_guard_marker)(void);
extern void (*aw_combat_scene)(void);
int AW_ArenaActive(void);
void AW_ArenaEntities(void);
void AW_ArenaSpawn(edict_t *player);
int AW_ArenaKey(int key,int down);
void AW_ArenaDraw(void);
void AW_UIEnemyBar(float fraction,float alpha);
int AW_CompanionDistance(void);
int AW_CompanionMimic(void);
int AW_CompanionToggleWord(char *word);
int AW_MovieStart(void);
void AW_MovieInit(void);
void AW_MovieStartup(void);
int AW_MovieActive(void);
int AW_MovieDebugActive(void);
int AW_MovieDebugPending(void);
void AW_MovieUpdate(void);
void AW_MovieDraw(void);
void AW_MoviePaint(portable_samplepair_t *,int,int);
byte *AW_MoviePalette(void);
int AW_MovieKey(int key,int down);
void AW_IntroBegin(void);
void AW_IntroInit(void);
void AW_IntroInputReport(void);
void AW_UIBookBegin(void);
int AW_UIFontSize(void);
int AW_UISetFontSize(int size);
void AW_UIBookEnd(void);
void AW_UISmallBegin(void);
void AW_UISmallEnd(void);
int AW_ReaderOpen(const char *stem,int action);
/* The player's text defines of an original line (%PCName, %PCRace, %PCClass), as in books. */
void AW_ExpandDialogue(char *out,int capacity,const char *source);
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
int AW_DayGalleryClock(int actual_ms);
int AW_DayNightFrozen(void);
int AW_DayGalleryView(float *origin,float *angles);
void V_RenderCameraView(void);
int AW_WaitKey(int key);
int AW_WaitDraw(void);

void AW_UICenteredLines(int x,int y,int w,int h,const char *text);
const char *AW_UIPage(const char *text,int width,int rows,char *out,int capacity);

const char *AW_SceneWorldModel(const char *name);

/* On-demand map and earned journal. */
int AW_ViewEquipmentReady(void);
int AW_ViewInventoryEquipment(model_t *models[2],float origins[2][3],float angles[2][3]);
extern int (*aw_hand_block_item)(char id[64],char model[64]);
int AW_ViewInventoryBody(model_t **model,int *frame);
int AW_ViewInventoryHeld(model_t **model,int *frame);   /* the carried torch with the torch pose */
int AW_InventoryPreviewDraw(model_t *model,int frame,int x,int y,int width,int height,float angle);
void AW_InventoryPreviewClear(void);
int AW_ViewInventoryLive(void);   /* aw_view.c: the old live inventory preview selected */
void AW_ViewInventoryClear(void);
int AW_InventoryActive(void);
void AW_WorldUIInit(void);
int AW_WorldUIActive(void);
void AW_WorldUICancelDrag(void);
int AW_WorldUIKey(int key,int down);
void AW_WorldUIMouse(int dx,int dy);
int AW_WorldUIDraw(void);

/* Placement-specific render pool; no new network or collision entities. */
void AW_RenderRangesNewMap(void);
qboolean AW_RenderRangeView(entity_t *entity,int pass,model_t *view);

/* THE "player dead" predicate (PLAYER-DEATH-LIMBO-35, docs/THIRD_PERSON.md "While dead"): the single-player
 * player's health is gone. Every focus name, hint, prompt, crosshair, voice line, greeting and activation path
 * asks it, and the input lock (aw_view.c AW_DeathLocked) is built on it: dead, nothing more is shown or done.
 * The original: OpenMW Player::activate refuses a dead player, Actors greet only a living one; the third-person
 * death camera shows no crosshair (camera.lua updateCrosshair). */
static inline int AW_PlayerDead(void)
{
    return sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict &&
        svs.clients[0].edict->v.health<=0;
}
