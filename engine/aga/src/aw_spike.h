/* SPDX-License-Identifier: GPL-2.0-or-later
 * Frame spikes ("chim spikes MS"): every frame that takes MS milliseconds or
 * more prints one console line naming what ran in it (map load, CHIM index,
 * prime, chunk tick, reads, sounds, models), so a pause in play is tied to
 * the work that caused it (CHIM-CROSSING-SYNC-LOAD-43). Console: "chim spikes
 * MS" (0: off, the default: one integer test per site), "chim spikes report"
 * sums them (no registered command or cvar of its own).
 */
#ifndef AW_SPIKE_H
#define AW_SPIKE_H

enum
{
	AW_SP_SPAWN,		/* SV_SpawnServer: the whole server side of a map load */
	AW_SP_MAPFILE,		/* the world model file read and decoded (Mod_ForName of the map) */
	AW_SP_CHIM_INDEX,	/* CHIM: chim/world.cwi read and decoded at map start */
	AW_SP_CHIM_BEGIN,	/* CHIM: the rest of the map start (frame pack, far terrain, frame world) */
	AW_SP_CLINFO,		/* client: server info, model and sound precache, R_NewMap */
	AW_SP_PRIME,		/* CHIM: the ring loaded around the arrival before play */
	AW_SP_TICK,			/* CHIM: the per-frame ring tick (streamed loads) */
	AW_SP_LINK,			/* CHIM: the per-frame client link */
	AW_SP_READ,			/* CHIM: time inside pack reads (nested in the above) */
	AW_SP_SOUND,		/* a sound loaded from disk (S_LoadSound past the cache) */
	AW_SP_PREFETCH,		/* CHIM prefetch slices in spare frame time */
	/* the host frame's stages (host.c), printed from 2 ms */
	AW_SP_CBUF,			/* console commands (a map change runs here) */
	AW_SP_SERVER,		/* Host_ServerFrame */
	AW_SP_CLIENT,		/* CL_ReadFromServer */
	AW_SP_SCREEN,		/* SCR_UpdateScreen: the frame drawn */
	AW_SP_SNDUPD,		/* S_Update */
	AW_SP_SCENE,		/* AW_SceneTick: crossings and doors */
	AW_SP_SAVE,			/* AW_SaveTick: autosaves */
	AW_SP_WINDOW,		/* CHIM type 1: frames joining or leaving the window (nested in the tick) */
	/* finer parts of the frame (TRADEHOUSE-LONG-FRAME-59), printed from 2 ms like the stages */
	AW_SP_MODAL,		/* AW_ModalFrame: open windows (strip, talk, inventory) */
	AW_SP_MWSCRIPT,		/* AW_MwscriptTick: compiled game scripts */
	AW_SP_TICKS,		/* the other end-of-frame ticks (quick character, test box, intro, wait, kits) */
	AW_SP_PSTART,		/* SV_Physics: the progs' StartFrame */
	AW_SP_ENTS,			/* SV_Physics: every entity's physics and think (the slowest one is named) */
	AW_SP_COMPANION,	/* AW_CompanionPhysics */
	AW_SP_COMBAT,		/* AW_CombatPhysics */
	AW_SP_AMBIENT,		/* AW_AmbientPhysics: the residents' Wander packages */
	AW_SP_ROOM,			/* AW_ActorsRoomTick */
	AW_SP_ITEMS,		/* AW_ItemsCarriedUpdate */
	AW_SP_MAGIC,		/* the magic frame (recharge, effects) */
	AW_SP_LAVA,			/* AW_LavaPhysics */
	AW_SP_RUNCLIENTS,	/* SV_RunClients: the player's move and commands */
	AW_SP_SENDMSG,		/* SV_SendClientMessages */
	AW_SP_AMBSCAN,		/* aw_ambient.c: the once-a-second scan for actors (table lookups, routes read) */
	AW_SP_AMBAGGRO,		/* aw_ambient.c: the aggro checks (nested in ambient) */
	AW_SP_AMBCHOOSE,	/* aw_ambient.c: idles and destinations picked */
	AW_SP_AMBWALK,		/* aw_ambient.c: the walking steps */
	AW_SP_INPUT,		/* Sys_SendKeyEvents + IN_Commands */
	AW_SP_REMOTE,		/* AW_RemotePoll: test sessions' command and state files */
	AW_SP_NET,			/* NET_Poll + CL_SendCmd */
	AW_SP_HOSTCON,		/* Host_GetConsoleCommands */
	AW_SP_AUDIOX,		/* CDAudio_Update + S_ExtraUpdate + AW_StreamPresented */
	AW_SP_TAIL,			/* the frame's last calls (CD audio, profile counters) */
	AW_SP_SLOTS
};

#ifdef AMIGA
extern int aw_spike_on;
void AW_SpikeAdd (int slot, double seconds, long bytes);
void AW_SpikeFrame (void);
void AW_SpikeInit (void);
void AW_SpikeSet (int ms);
int AW_SpikeThreshold (void);
void AW_SpikeReport (void);
void AW_SpikeEnt (int num, double seconds);	/* the slowest entity of the frame's physics loop */
double Sys_FloatTime (void);
/* ARRIVAL-LONG-FRAME-DEV6-59: file work per frame, counted always (one add per call): every file looked up by
 * name (COM_FindFile: a DOS Lock per search path, then the opens; FOUND 0 a miss) and every Sys_FileRead. A spike
 * line ends with them and the names opened most; any frame of AW_SPIKE_LONG_MS or more prints a "Long frame" line
 * even with spikes off, and "chim spikes report" names the longest frame since the last report with its files. */
void AW_SpikeFile (const char *name, int found);
void AW_SpikeFileRead (long bytes);
#define AW_SPIKE_LONG_MS	500
/* FRAME-WAIT-COUNTERS-59: the frame's waits, timed always (one Sys_FloatTime pair per call, no allocation): disk =
 * file lookups, opens, seeks and reads (nested calls count once: only the outermost is timed), c2p = the
 * chunky-to-planar copy to the screen, vbl = the screen buffer swap (the engine has no vertical blank wait in
 * play). Printed on the spike and "Long frame" lines and summed in "chim spikes report". */
enum {AW_WAIT_DISK, AW_WAIT_C2P, AW_WAIT_VBL, AW_WAITS};
extern double aw_wait_time[AW_WAITS];
extern int aw_disk_depth;
/* BENCH-RESULT-FILE-62: running totals since the start (one add per frame, one per file call): the disk wait of
 * every finished frame (the frame in progress is still in aw_wait_time[AW_WAIT_DISK]), the files looked up by name
 * and the file reads; a caller takes the difference between two moments (aw_halloween.c: per benchmark frame). */
extern double aw_disk_total;
extern unsigned long aw_file_finds, aw_file_reads;
#define AW_DISK_BEGIN(t0)	((t0) = aw_disk_depth++ ? 0 : Sys_FloatTime ())
#define AW_DISK_END(t0)		do { if (--aw_disk_depth <= 0) { aw_disk_depth = 0; aw_wait_time[AW_WAIT_DISK] += Sys_FloatTime () - (t0); } } while (0)
#define AW_WAIT_BEGIN(t0)	((t0) = Sys_FloatTime ())
#define AW_WAIT_END(k, t0)	(aw_wait_time[(k)] += Sys_FloatTime () - (t0))
#define AW_SPIKE_BEGIN(t0)		((t0) = aw_spike_on ? Sys_FloatTime () : 0)
#define AW_SPIKE_END(slot, t0, bytes)	do { if (aw_spike_on && (t0) > 0) AW_SpikeAdd ((slot), Sys_FloatTime () - (t0), (bytes)); } while (0)
/* one host stage, timed when spikes are on */
#define AW_SPIKE_STAGE(slot, call)	do { double aw_st0_; AW_SPIKE_BEGIN (aw_st0_); call; AW_SPIKE_END ((slot), aw_st0_, 0); } while (0)
#else	/* host tests: no spike storage linked */
#define aw_spike_on 0
#define AW_SPIKE_BEGIN(t0)		((t0) = 0)
#define AW_SPIKE_END(slot, t0, bytes)	do { (void)(t0); (void)(bytes); } while (0)
#define AW_SpikeAdd(s, t, b)	((void)0)
#define AW_SpikeFrame()			((void)0)
#define AW_SpikeInit()			((void)0)
static __inline__ void AW_SpikeSet (int ms) { (void)ms; }
#define AW_SpikeThreshold()		0
#define AW_SpikeReport()		((void)0)
#define AW_SpikeFile(n, f)		((void)0)
#define AW_SpikeFileRead(b)		((void)0)
#define AW_SpikeEnt(n, s)		((void)0)
#define AW_DISK_BEGIN(t0)		((t0) = 0)
#define AW_DISK_END(t0)			do { (void)(t0); } while (0)
#define AW_WAIT_BEGIN(t0)		((t0) = 0)
#define AW_WAIT_END(k, t0)		((void)(t0))
#define AW_SPIKE_STAGE(slot, call)	do { call; } while (0)
#endif

/* CHIM's counters for the spike line (chim/chim_world.c sets it): bytes read,
 * reads, models, textures and chunks loaded, zone evictions, prefetch hits. */
extern void (*aw_chim_spike_counts)(unsigned long *out, int count);
#define AW_SPIKE_CHIM_COUNTS	8

#endif

/* FRAME-WAIT-COUNTERS-59: the disk wait wrappers and the fopen, fread and fseek macros that call them, for
 * quakedef.h (it defines AW_DISKWAIT_WRAPPED, with <stdio.h> included, before it includes this header; only on the
 * Amiga and without AW_DISKWAIT_NO_WRAP). Here, outside the include guard,
 * so a file that included this header first still gets them; kept in the timing header so a change to them re-keys
 * no CHIM world stage (tools/engine_facts.py TIMING_HEADERS, BUILD-ENGINE-SOURCE-KEY-BROAD-36). */
#if defined(AW_DISKWAIT_WRAPPED) && !defined(AW_DISKWAIT_BODIES)
#define AW_DISKWAIT_BODIES
static inline FILE *AW_DiskFopen(const char *path,const char *mode)
{
    double t0; FILE *f;
    AW_DISK_BEGIN(t0); f=(fopen)(path,mode); AW_DISK_END(t0);
    return f;
}
static inline size_t AW_DiskFread(void *p,size_t size,size_t n,FILE *f)
{
    double t0; size_t got;
    AW_DISK_BEGIN(t0); got=(fread)(p,size,n,f); AW_DISK_END(t0);
    return got;
}
static inline int AW_DiskFseek(FILE *f,long offset,int whence)
{
    double t0; int r;
    AW_DISK_BEGIN(t0); r=(fseek)(f,offset,whence); AW_DISK_END(t0);
    return r;
}
#undef fopen
#undef fread
#undef fseek
#define fopen(p,m) AW_DiskFopen((p),(m))
#define fread(p,s,n,f) AW_DiskFread((p),(s),(n),(f))
#define fseek(f,o,w) AW_DiskFseek((f),(o),(w))
#endif
