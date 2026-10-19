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
double Sys_FloatTime (void);
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
#define AW_SPIKE_STAGE(slot, call)	do { call; } while (0)
#endif

/* CHIM's counters for the spike line (chim/chim_world.c sets it): bytes read,
 * reads, models, textures and chunks loaded, zone evictions, prefetch hits. */
extern void (*aw_chim_spike_counts)(unsigned long *out, int count);
#define AW_SPIKE_CHIM_COUNTS	8

#endif
