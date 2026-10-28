/* SPDX-License-Identifier: GPL-2.0-or-later
 * PROTOTYPE (branch v0.0.46-type1-stateful, not for the dev line as is):
 * stateful actors for the type 1 window ("chim crossing 1", chim_chunks.c).
 *
 * An actor belongs to its position, not to a frame:
 * - a frame that joins the window spawns its actors (aw_npc, aw_creature) from
 *   its own frame map's entity text with the engine's own machinery
 *   (ED_ParseEdict, the QuakeC spawn function), at the frame's offset in the
 *   session; an actor the change list marks dead is not spawned, one still
 *   alive in the session (it followed or pursued the player) is not spawned
 *   twice, one that moved is put where it was left;
 * - a frame that leaves releases the actors standing in its cell, except a
 *   companion, an actor in a fight (alive) and an actor within the behaviour range of
 *   the player (OpenMW's 7168-unit processing range, 1,792 local units): those
 *   stay alive with their health, target and behaviour state; a released actor's
 *   state (position, alive or dead) goes to the change list keyed by its
 *   reference id (aw_ref);
 * - every window tick, a kept actor whose cell is no longer in the window and
 *   which no rule keeps any more is released the same way.
 *
 * Shortcut of the prototype (labelled): a model or sound precached by a join
 * after the sign-on is handed to the client directly (one process, loopback);
 * the design is a precache message to the client (svc_aw_precache).
 * Console (a "chim" subcommand, no command or cvar of its own): chim actors (status),
 * chim actors list, chim actors trace 0/1, chim actors resetstats, chim actors budget N, chim actors warm 0/1
 * (spawns per tick, 0 = all at once; default 1), chim actors fight (the nearest resident
 * attacks the player), chim actors kill (the nearest resident dies), chim actors summon
 * (TEST: a copy of the nearest resident at the player's feet), chim actors hash LABEL,
 * chim actors clear (forget the change list), chim actors seed N (the levelled lists' session seed).
 *
 * Levelled creature lists (actor table version 2, tools/chim/actors.py): a levelled reference of a joining cell is
 * rolled once with the player's level (ChimActors_LevelledPick: the game's rule, read from OpenMW 0.51) and the
 * pick kept in the change list under the reference, so a later join spawns the same creature (or nothing); the
 * spawned creature keeps the list reference's id, so its death and moves are kept the same way. The roll's
 * random numbers come from the reference's key and the session seed (EXPERIMENTAL: OpenMW uses the world's random
 * generator and saves the pick; here a pick that does not fit the change list is rolled again with the same
 * numbers, which gives the same creature at the same level). Not done: the respawn (OpenMW rolls a list again
 * when its creature has been dead min(fCorpseRespawnDelay, fCorpseClearDelay) game hours, 72 in Morrowind.esm,
 * at the next cell load).
 */
#include "quakedef.h"
#include "aw_actors.h"
#include "aw_anim.h"
#include "aw_items.h"
#include "chim/chim_format.h"
#include "chim/chim_actor_table.h"
#include "aw_character.h"
#include "aw_save.h"

/* "chim actors ambient ..." (aw_ambient.c sets it at init; NULL: not in this engine) */
void (*aw_ambient_cmd)(void);
#include "aw_state.h"

#define AI_RANGE		1792.0f		/* local units: OpenMW's actors processing range 7168 x 0.25 */
#define MAX_CHANGES		2048

typedef struct
{
	float	ref;
	vec3_t	origin, angles;		/* origin: ISLAND position (session + origin cell), so a recentre keeps it */
	unsigned char	dead, moved, fight, follow;
	unsigned short	pick;		/* a levelled reference's roll: 0 not rolled, 1 nothing, 2 + the base it gave */
	float	health, hours;		/* health when left (moved); game hours when captured */
} change_t;

static change_t	changes[MAX_CHANGES];
static int		nchanges;
static aw_changes_t	carried;		/* loaded change entries this module does not place (kept for the next save) */
static int			apply_pending;	/* a load's changes wait for the next window tick (ApplyLoaded) */
static void ApplyLoaded (void);
static int		aw_actors_trace;		/* aw_actors trace 1: one line per tick that spawns */
static struct
{
	unsigned long	joins, leaves, spawned, skipped_dead, skipped_alive, released, kept, rehomed, frees_by_tick, spawn_ticks;
	unsigned long	skipped_disabled;
	double			join_time, leave_time, spawn_time, spawn_worst;
} st;

/* Object state (aw_mwhost.c sets it; NULL without the scripts): 1 when a script disabled the placement REFERENCE. */
int (*aw_actor_disabled)(unsigned reference);
extern void (*chim_actors_join)(int cx, int cy, const char *map, const float *offset);
extern void (*chim_actors_leave)(int cx, int cy);
extern void (*chim_actors_tick)(void);
extern void (*chim_actors_cmd)(void);
extern void (*aw_levelled_entity)(edict_t *ent);	/* pr_edict.c: an "aw_levelled" entity of a loading map */
int AW_CompanionEdict (edict_t *e);
#include "aw_mappath.h"
#include "aw_tryalloc.h"
dfunction_t *ED_FindFunction (char *name);

static int IsActor (edict_t *e)
{
	const char *c;
	if (e->free || !e->v.classname)
		return 0;
	c = pr_strings + e->v.classname;
	return !strcmp (c, "aw_npc") || !strcmp (c, "aw_creature");
}

/* dbg creatures on|off ("chim actors creatures 0|1"; no command or cvar of its own: the resident registry budget):
 * the outdoor creatures of the actor library (models progs/c_*, tools/creature_library.py) and aw_creature actors.
 * Off: the ones alive are released as a leaving cell releases them (their state kept in the change list) and no new
 * one spawns; on: they come back with their cells' next joins. Default on, not saved. Room creatures (resident
 * models, progs/a_*) are not told apart from the room's NPCs yet. */
static int		creatures_on = 1;
static unsigned long	creatures_skipped;

static int IsCreature (edict_t *e)
{
	const char *m;
	if (e->free || !e->v.classname)
		return 0;
	if (!strcmp (pr_strings + e->v.classname, "aw_creature"))
		return 1;
	m = e->v.model ? pr_strings + e->v.model : "";
	return !strncmp (m, "progs/c_", 8);
}

static float RefOf (edict_t *e)
{
	eval_t *v = GetEdictFieldValue (e, "aw_ref");
	return v ? v->_float : 0;
}

static change_t *Change (float ref, int make)
{
	int i;
	if (!ref)
		return NULL;
	for (i=0 ; i<nchanges ; i++)
		if (changes[i].ref == ref)
			return &changes[i];
	if (!make || nchanges == MAX_CHANGES)
		return NULL;
	memset (&changes[nchanges], 0, sizeof(change_t));
	changes[nchanges].ref = ref;
	return &changes[nchanges++];
}

static edict_t *Player (void)
{
	return svs.clients && svs.clients[0].active ? svs.clients[0].edict : NULL;
}

/* Kept alive: a companion, a fighter that is alive, or within the behaviour range. */
static int Keep (edict_t *e)
{
	edict_t *p = Player ();
	vec3_t d;
	if (AW_CompanionEdict (e) || AW_CombatSlotState (e, NULL) == 1)
		return 1;
	if (!p)
		return 0;
	VectorSubtract (e->v.origin, p->v.origin, d);
	d[2] = 0;
	return DotProduct (d, d) < AI_RANGE * AI_RANGE;
}

/* The actors the session's own map spawned at its start (its entity text, ED_LoadFromFile; the home frame's join is
 * never run for that reason) belong to the home frame, wherever they stand: a town frame covers several cells, and
 * its residents in the cells beside its own were released at once as "left the window", although the frame that
 * holds their ground was in it (CHIM-ACTORS-TOWN-RETURN-EMPTY-47). Such an actor stays while the home frame is in the
 * window or its own cell's frame is, and goes when the last of them leaves. Marked at the first window tick of a
 * map (and after a load); an edict a join spawns is never one. */
static unsigned char	home_own[MAX_EDICTS];
static float			home_ref[MAX_EDICTS];

static void MarkHome (void)
{
	int i;
	memset (home_own, 0, sizeof(home_own));
	for (i=1 ; i<sv.num_edicts && i<MAX_EDICTS ; i++)
	{
		edict_t *e = EDICT_NUM(i);
		if (IsActor (e))
		{
			home_own[i] = 1;
			home_ref[i] = RefOf (e);
		}
	}
}

static int HomeOwned (edict_t *e)
{
	int i = NUM_FOR_EDICT (e);
	return i > 0 && i < MAX_EDICTS && home_own[i] && home_ref[i] == RefOf (e);
}

/* The home frame's cell and whether the window holds it (0 without a window). */
static int HomeCell (int *cx, int *cy, int *held)
{
	return ChimChunks_WindowCell (vec3_origin, cx, cy, held);
}

/* The session's origin cell: session position + (cell x 2048 + 1024) = island position (the world-state hash's
 * rule). 0 outside a CHIM session (then positions stay as they are). */
static void IslandOffset (float *d)
{
	int ox, oy;
	d[0] = d[1] = d[2] = 0;
	if (ChimChunks_OriginCell (&ox, &oy))
	{
		d[0] = ox * 2048.0f + 1024;
		d[1] = oy * 2048.0f + 1024;
	}
}

/* Game hours since the game's start (the game clock's globals; 0 before the clock runs). */
static float GameHours (void)
{
	if (AW_StateGet (&aw_state, AW_GLOBAL, "amiwind:clock:ready") != 1)
		return 0;
	return AW_StateGet (&aw_state, AW_GLOBAL, "amiwind:clock:days") * 24.0f +
		AW_StateGet (&aw_state, AW_GLOBAL, "amiwind:clock:ms") / 3600000.0f;
}

/* An actor's state into its change entry (when it leaves, and for a save): dead, where, health, fight, follow. */
static void Capture (edict_t *e, change_t *c)
{
	float h = e->v.health, d[3];
	int state = AW_CombatSlotState (e, &h);
	IslandOffset (d);
	/* death stays (no respawn yet): an actor a level change spawned again from its map is not alive again */
	c->dead = c->dead || state == 2;
	c->fight = state == 1;
	c->follow = AW_CompanionEdict (e) ? 1 : 0;
	c->moved = 1;
	c->health = h;
	VectorAdd (e->v.origin, d, c->origin);
	VectorCopy (e->v.angles, c->angles);
	c->hours = GameHours ();
}

static void Release (edict_t *e)
{
	change_t *c = Change (RefOf (e), 1);
	if (c)
		Capture (e, c);
	AW_CombatForget (e);
	ED_Free (e);
	st.released++;
}

/* The client learns models and sounds a join precached (prototype shortcut). */
static int			warm_on;		/* chim actors warm 0/1 (below) */
static struct {unsigned long models, voices, sounds; double model_time, voice_time, sound_time, worst;} wst;

static void ClientLists (int sounds)
{
	int i;
	/* as CL_ParseServerInfo: a mover model (registered by name at a spawn, AW_AnimLazy) is not loaded here; it
	 * loads while worn */
	for (i=1 ; i<MAX_MODELS && sv.model_precache[i] ; i++)
		if (!cl.model_precache[i])
			cl.model_precache[i] = AW_AnimLazy (sv.model_precache[i]) ? Mod_FindName (sv.model_precache[i]) :
				Mod_ForName (sv.model_precache[i], false);
	if (sounds)
		for (i=1 ; i<MAX_SOUNDS && sv.sound_precache[i] ; i++)
			if (!cl.sound_precache[i])
				cl.sound_precache[i] = S_PrecacheSound (sv.sound_precache[i]);
}

/* chim actors warm 1: the sounds a spawn added (its animation layout's footsteps and the like) reach the client one
 * per tick on the ticks after it, never in the spawn's own tick; until then such a sound does not play (the client
 * plays nothing for an index it has not loaded). 1 when this tick loaded one. */
static int ClientSoundStep (void)
{
	int i;
	double t0;
	for (i=1 ; i<MAX_SOUNDS && sv.sound_precache[i] ; i++)
		if (!cl.sound_precache[i])
		{
			t0 = Sys_FloatTime ();
			cl.sound_precache[i] = S_PrecacheSound (sv.sound_precache[i]);
			t0 = Sys_FloatTime () - t0;
			wst.sounds++;
			wst.sound_time += t0;
			if (t0 > wst.worst)
				wst.worst = t0;
			if (aw_actors_trace)
				Con_Printf ("actors: tick warmed client sound %s in %.1f ms\n", sv.sound_precache[i], t0*1000);
			return 1;
		}
	return 0;
}

static int AliveWithRef (float ref, edict_t *self)
{
	int i;
	edict_t *e;
	if (!ref)
		return 0;
	for (i=1 ; i<sv.num_edicts ; i++)
	{
		e = EDICT_NUM(i);
		if (e != self && IsActor (e) && RefOf (e) == ref)
			return 1;
	}
	return 0;
}

/* A joining frame's actors wait in a queue and are spawned a few per tick
 * (chim actors budget N, default 1; 0 = all at once, the first prototype's way),
 * the nearest to where the player will be in half a second first. */
#define MAX_PENDING		256
typedef struct
{
	char	*text;			/* the entity's text after its '{' */
	vec3_t	origin;			/* session position (frame offset added) */
	vec3_t	offset;
	short	cx, cy;
	short	warmed;			/* chim actors warm 1: loads already done ahead of the spawn (0 model, 1 voice, 2 both) */
	short	table;			/* 1: from the actor table, REC holds the placement */
	chim_actor_record_t	rec;
	float	scale;			/* the table's instance scale (1: none) */
} pending_t;

static pending_t	pending[MAX_PENDING];
static int			npending;
static int			budget_n = 1;		/* chim actors budget N: spawns per tick (0: all at once) */
/* chim actors warm 1 (default 0, experimental): a queued actor's first-time loads (its model file, then its voice)
 * each take a tick of their own before the tick that spawns it, so no single tick pays a model load, a voice load
 * and the spawn together. A load that was already done costs nothing and takes no tick. */
sfx_t *S_FindName (char *name);		/* snd_dma.c */

/* The value of key in an entity's text (the pending copy), or "" */
static void TextValue (const char *text, const char *key, char *out, int size)
{
	char pat[64];
	const char *s, *e;
	int n;
	out[0] = 0;
	snprintf (pat, sizeof(pat), "\"%s\" \"", key);
	if (!(s = strstr (text, pat)))
		return;
	s += strlen (pat);
	if (!(e = strchr (s, '"')) || (n = (int)(e - s)) <= 0 || n >= size)
		return;
	memcpy (out, s, n);
	out[n] = 0;
}

/* One warm step for q: 1 when it used this tick for a load (the spawn waits for a later tick). */
static char warm_note[MAX_QPATH+64];
static int WarmStep (pending_t *q)
{
	char name[MAX_QPATH];
	double t0;
	model_t *m;
	sfx_t *sfx;
	while (q->warmed < 2)
	{
		TextValue (q->text, q->warmed ? "aw_voice" : "model", name, sizeof(name));
		q->warmed++;
		if (!name[0])
			continue;
		t0 = Sys_FloatTime ();
		if (q->warmed == 1)
		{
			m = Mod_FindName (name);
			if (!m->needload && (m->type != mod_alias || Cache_Check (&m->cache)))
				continue;		/* already in memory */
			Mod_ForName (name, false);
			t0 = Sys_FloatTime () - t0;
			wst.models++;
			wst.model_time += t0;
		}
		else
		{
			sfx = S_FindName (name);
			if (!sfx || Cache_Check (&sfx->cache))
				continue;
			S_PrecacheSound (name);
			t0 = Sys_FloatTime () - t0;
			wst.voices++;
			wst.voice_time += t0;
		}
		if (t0 > wst.worst)
			wst.worst = t0;
		/* printed after the tick is timed (SpawnQueued): a console line inside the tick would be counted as its work */
		if (aw_actors_trace)
			snprintf (warm_note, sizeof(warm_note), "actors: tick warmed %s %s in %.1f ms\n",
				q->warmed == 1 ? "model" : "voice", name, t0*1000);
		return 1;
	}
	return 0;
}

static void PendingDrop (int i)
{
	free (pending[i].text);
	pending[i] = pending[--npending];
}

static int SpawnOne (pending_t *q)
{
	edict_t *ent;
	dfunction_t *func;
	server_state_t was = sv.state;
	change_t *c;
	float ref;
	char *data;

	ent = ED_Alloc ();
	if (NUM_FOR_EDICT (ent) < MAX_EDICTS)
		home_own[NUM_FOR_EDICT (ent)] = 0;		/* a window join's actor: its cell's, never the home frame's */
	data = ED_ParseEdict (q->text, ent);
	if (!data || !IsActor (ent))
	{
		ED_Free (ent);
		return 0;
	}
	if (!creatures_on && IsCreature (ent))
	{
		ED_Free (ent);			/* dbg creatures off: its levelled pick and state stay for when they are on */
		creatures_skipped++;
		return 0;
	}
	if (q->table)
	{
		/* the actor table (EXPERIMENTAL): the base's text, the record's placement in its cell's local units */
		eval_t *v;
		VectorCopy (q->rec.origin, ent->v.origin);
		ent->v.angles[0] = ent->v.angles[2] = 0;
		ent->v.angles[1] = q->rec.yaw;
		if ((v = GetEdictFieldValue (ent, "aw_ref")) != NULL)
			v->_float = (float)q->rec.key;
		if ((v = GetEdictFieldValue (ent, "aw_ground_baked")) != NULL)
			VectorCopy (q->rec.origin, v->vector);
		if ((v = GetEdictFieldValue (ent, "aw_ground_valid")) != NULL)
			v->_float = (q->rec.flags & CHIM_ACTOR_BAKED) ? 1 : 0;
		/* the instance scale (version 3): the entity's aw_scale, which the client draws (AWU_SCALE); not when the
		 * base names a model already baked at that scale (record flag CHIM_ACTOR_SCALED_MODEL, the older method) */
		if (q->scale != 1.0f && !(q->rec.flags & CHIM_ACTOR_SCALED_MODEL) &&
			(v = GetEdictFieldValue (ent, "aw_scale")) != NULL)
			v->_float = q->scale;
	}
	ref = RefOf (ent);
	c = Change (ref, 0);
	if (c && c->dead)
	{
		ED_Free (ent);
		st.skipped_dead++;
		return 0;
	}
	/* a script's Disable (aw_mwhost.c object state, v0.0.51): not spawned while disabled; after Enable it comes with
	 * its cell's next join */
	if (aw_actor_disabled && ref > 0 && aw_actor_disabled ((unsigned)ref))
	{
		ED_Free (ent);
		st.skipped_disabled++;
		return 0;
	}
	if (AliveWithRef (ref, ent))
	{
		ED_Free (ent);
		st.skipped_alive++;
		return 0;
	}
	ent->v.origin[0] += q->offset[0];
	ent->v.origin[1] += q->offset[1];
	{
		/* The builder's baked ground point (aw_ground_baked, AW_NPCFloor) moves with the frame's offset, so a
		 * joined frame's actor keeps its exact standing height as at a level start. */
		eval_t *baked = GetEdictFieldValue (ent, "aw_ground_baked");
		if (baked)
		{
			baked->vector[0] += q->offset[0];
			baked->vector[1] += q->offset[1];
		}
	}
	func = ED_FindFunction (pr_strings + ent->v.classname);
	if (!func)
	{
		ED_Free (ent);
		return 0;
	}
	pr_global_struct->self = EDICT_TO_PROG(ent);
	sv.state = ss_loading;		/* the spawn function precaches its model and voice */
	PR_ExecuteProgram (func - pr_functions);
	sv.state = was;
	if (c && c->moved && !ent->free)
	{
		float d[3];
		IslandOffset (d);
		VectorSubtract (c->origin, d, ent->v.origin);
		VectorCopy (c->angles, ent->v.angles);
		SV_LinkEdict (ent, false);
		/* a fight it was in goes on, with the health it had (the combat sheet's) */
		if (c->fight && AW_CombatTestEngage (ent, 0))
			AW_CombatSetHealth (ent, c->health);
	}
	st.spawned++;
	return 1;
}

/* The actor table (EXPERIMENTAL, "chim actors table 1"; tools/chim/actors.py): a joining frame's actors come
 * from the island-wide table, the records of the frame's cell, instead of its frame map's entity text. Off by
 * default: the frame maps' actors, as before. */
static int		table_on;
static struct
{
	int					tried, ok;
	chim_actor_head_t	head;
	unsigned char		*cells, *bases, *lists, *scales;
	unsigned long		joins, records, spawnable, no_model, not_actor, full;
	unsigned long		levelled, levelled_none, levelled_no_model, levelled_kept;
} table;
static unsigned		roll_seed;			/* chim actors seed N */

static FILE *TableOpen (long *at, int *bytes)
{
	FILE *f = NULL;
	*bytes = COM_FOpenFile (CHIM_ACTOR_FILE, &f);
	if (f)
		*at = ftell (f);
	return f;
}

static int TableLoad (void)
{
	unsigned char head[CHIM_ACTOR_HEADER_BYTES];
	long at;
	int bytes;
	unsigned long nc, nb;
	FILE *f;
	if (table.tried)
		return table.ok;
	table.tried = 1;
	if (!(f = TableOpen (&at, &bytes)))
	{
		Con_Printf ("actors: no actor table (%s)\n", CHIM_ACTOR_FILE);
		return 0;
	}
	nc = nb = 0;
	if (fread (head, 1, sizeof(head), f) == sizeof(head) && ChimActors_Header (head, bytes, &table.head))
	{
		nc = (unsigned long)table.head.cells * CHIM_ACTOR_CELL_BYTES;
		nb = (unsigned long)table.head.bases * CHIM_ACTOR_BASE_BYTES;
		table.cells = AW_TryMalloc (nc + 1);
		table.bases = AW_TryMalloc (nb + 1);
		table.ok = table.cells && table.bases &&
			!fseek (f, at + (long)table.head.cells_at, SEEK_SET) && fread (table.cells, 1, nc, f) == nc &&
			!fseek (f, at + (long)table.head.bases_at, SEEK_SET) && fread (table.bases, 1, nb, f) == nb;
	}
	if (table.ok && table.head.version != CHIM_ACTOR_VERSION)
	{
		/* the levelled creature lists: small (the exterior's 61 lists: about 3 KB), kept whole; version 3: the
		 * instance scales after them (5 references in the game data) */
		unsigned long nl = table.head.bytes - table.head.lists_at, nlist = nl;
		table.lists = AW_TryMalloc (nl + 1);
		if (table.lists && !fseek (f, at + (long)table.head.lists_at, SEEK_SET) && fread (table.lists, 1, nl, f) == nl &&
			table.head.version == CHIM_ACTOR_VERSION_SCALES)
		{
			nlist = ChimActors_ListBytes (table.lists, nl);
			if (nlist && ChimActors_ScalesValid (table.lists + nlist, nl - nlist, table.head.records))
				table.scales = table.lists + nlist;
			else
				nlist = 0;
		}
		if (!table.lists || !nlist || !ChimActors_ListsValid (table.lists, nlist, table.head.bases))
		{
			free (table.lists);
			table.lists = table.scales = NULL;
			Con_Printf ("actors: the actor table's levelled lists cannot be read; levelled references are left out\n");
		}
		else
			table.head.lists = ChimFormat_U32 (table.lists);
	}
	fclose (f);
	if (!table.ok)
	{
		free (table.cells);
		free (table.bases);
		table.cells = table.bases = NULL;
		Con_Printf ("actors: the actor table %s cannot be read\n", CHIM_ACTOR_FILE);
		return 0;
	}
	Con_Printf ("actors: actor table: %lu records in %lu cells, %lu bases, %lu levelled lists\n",
		(unsigned long)table.head.records, (unsigned long)table.head.cells, (unsigned long)table.head.bases,
		(unsigned long)table.head.lists);
	return 1;
}

/* The records of cell CX CY queued for spawning (the frame map is not read). */
static void TableJoin (int cx, int cy, const float *offset)
{
	chim_actor_cell_t cell;
	chim_actor_record_t r;
	chim_actor_base_t b;
	unsigned char raw[CHIM_ACTOR_RECORD_BYTES];
	unsigned i, k;
	int bytes, queued = 0;
	long at;
	FILE *f;
	if (!TableLoad ())
		return;
	for (i=0 ; i<table.head.cells ; i++)
	{
		ChimActors_Cell (table.cells + i*CHIM_ACTOR_CELL_BYTES, &cell);
		if (cell.cx == cx && cell.cy == cy)
			break;
	}
	table.joins++;
	if (i == table.head.cells || cell.first + cell.count > table.head.records || !(f = TableOpen (&at, &bytes)))
		return;
	for (k=0 ; k<cell.count ; k++)
	{
		pending_t *q;
		if (fseek (f, at + (long)table.head.records_at + (long)(cell.first + k)*CHIM_ACTOR_RECORD_BYTES, SEEK_SET) ||
			fread (raw, 1, sizeof(raw), f) != sizeof(raw) || !ChimActors_Record (raw, &table.head, &r) ||
			!ChimActors_Base (table.bases + r.base*CHIM_ACTOR_BASE_BYTES, &table.head, &b))
			break;
		table.records++;
		if (b.kind == CHIM_ACTOR_KIND_LEVELLED && table.lists)
		{
			/* a levelled reference: its kept pick, or one roll at the player's level (kept in the change list) */
			change_t *c = Change ((float)r.key, 0);
			unsigned pick;
			table.levelled++;
			if (c && c->pick)
			{
				pick = c->pick;
				table.levelled_kept++;
			}
			else
			{
				unsigned state = ChimActors_RollSeed (r.key, roll_seed);
				int level = aw_character.valid && aw_character.level > 0 ? aw_character.level : 1;
				int got = ChimActors_LevelledPick (table.lists, b.at, level, &state);
				pick = got < 0 ? 1 : (unsigned)got + 2;
				if ((c = Change ((float)r.key, 1)) != NULL)
					c->pick = (unsigned short)pick;
			}
			if (pick == 1 || !ChimActors_Base (table.bases + (pick-2)*CHIM_ACTOR_BASE_BYTES, &table.head, &b))
			{
				table.levelled_none++;
				continue;
			}
			if (!b.bytes)
			{
				table.levelled_no_model++;		/* the creature it gave has no model in this build */
				table.no_model++;
				continue;
			}
		}
		if (!b.bytes)
		{
			table.no_model++;			/* no actor model in this build */
			continue;
		}
		if (b.kind != CHIM_ACTOR_KIND_NPC && b.kind != CHIM_ACTOR_KIND_CREATURE)
		{
			table.not_actor++;			/* a dead resident (aw_corpse) or a levelled list */
			continue;
		}
		if (npending == MAX_PENDING)
		{
			table.full++;
			continue;
		}
		q = &pending[npending];
		if (!(q->text = AW_TryMalloc (b.bytes + 3)))
			break;
		if (fseek (f, at + (long)table.head.text_at + (long)b.at, SEEK_SET) ||
			fread (q->text, 1, b.bytes, f) != b.bytes)
		{
			free (q->text);
			break;
		}
		q->text[b.bytes] = '}';
		q->text[b.bytes+1] = 0;
		q->table = 1;
		q->warmed = 0;
		q->rec = r;
		q->scale = table.scales ? ChimActors_Scale (table.scales, cell.first + k) : 1.0f;
		VectorCopy (r.origin, q->origin);
		q->offset[0] = offset[0];
		q->offset[1] = offset[1];
		q->offset[2] = 0;
		q->origin[0] += offset[0];
		q->origin[1] += offset[1];
		q->cx = (short)cx;
		q->cy = (short)cy;
		npending++;
		queued++;
		table.spawnable++;
	}
	fclose (f);
	Con_Printf ("actors: cell %ld %ld joins from the actor table: %ld actors queued (%ld waiting)\n", (long)cx,
		(long)cy, (long)queued, (long)npending);
}

/* A room's levelled creature (CREATURE-ROOM-LEVELLED-54): the room map's "aw_levelled" entity (aw_ref = the reference
 * number, sounds = the list's index in the actor table's lists: chim.actors.table_list_order, the same order the
 * table is written in), handed over by ED_LoadFromFile (pr_edict.c aw_levelled_entity) while the map loads. Rolled as
 * an outdoor levelled reference is (ChimActors_LevelledPick at the player's level, the pick kept in the change list
 * under the reference, so the room gives the same creature again, or nothing), and the creature spawned there and
 * then (the map is loading: its spawn function may precache). The entity itself is freed by the caller. */
static void LevelledEntity (edict_t *ent)
{
	chim_actor_base_t b;
	pending_t q;
	eval_t *v = GetEdictFieldValue (ent, "aw_ref");
	float ref = v ? v->_float : 0;
	unsigned list = (unsigned)ent->v.sounds, pick;
	change_t *c;
	if (!TableLoad () || !table.lists || list >= table.head.lists)
		return;
	table.levelled++;
	c = Change (ref, 0);
	if (c && c->pick)
	{
		pick = c->pick;
		table.levelled_kept++;
	}
	else
	{
		unsigned state = ChimActors_RollSeed ((unsigned)ref, roll_seed);
		int level = aw_character.valid && aw_character.level > 0 ? aw_character.level : 1;
		int got = ChimActors_LevelledPick (table.lists, list, level, &state);
		pick = got < 0 ? 1 : (unsigned)got + 2;
		if ((c = Change (ref, 1)) != NULL)
			c->pick = (unsigned short)pick;
	}
	if (pick == 1 || !ChimActors_Base (table.bases + (pick-2)*CHIM_ACTOR_BASE_BYTES, &table.head, &b))
	{
		table.levelled_none++;
		return;
	}
	if (!b.bytes)
	{
		table.levelled_no_model++;
		return;
	}
	{
		long at;
		int bytes;
		FILE *f = TableOpen (&at, &bytes);
		memset (&q, 0, sizeof(q));
		if (!f)
			return;
		if (!(q.text = AW_TryMalloc (b.bytes + 3)) || fseek (f, at + (long)table.head.text_at + (long)b.at, SEEK_SET) ||
			fread (q.text, 1, b.bytes, f) != b.bytes)
		{
			free (q.text);
			fclose (f);
			return;
		}
		fclose (f);
	}
	q.text[b.bytes] = '}';
	q.text[b.bytes+1] = 0;
	q.table = 1;
	q.scale = 1.0f;
	q.rec.key = (unsigned)ref;
	VectorCopy (ent->v.origin, q.rec.origin);
	q.rec.yaw = ent->v.angles[1];
	q.rec.flags = 0;
	if (SpawnOne (&q))
		table.spawnable++;
	free (q.text);
}

static void Join (int cx, int cy, const char *map, const float *offset)
{
	char path[MAX_QPATH+16], *text, *data, *start;
	unsigned char head[12];
	FILE *f = NULL;
	int bytes, at, queued = 0, k;
	long length;
	double t0 = Sys_FloatTime (), took;

	if (!sv.active)
		return;
	if (table_on)
	{
		TableJoin (cx, cy, offset);
		return;
	}
	AW_MapPath (map, path, sizeof(path));
	bytes = COM_FOpenFile (path, &f);
	if (!f)
		return;
	at = ftell (f);
	if (fread (head, 1, sizeof(head), f) != sizeof(head))
	{
		fclose (f);
		return;
	}
	k = head[4] | (head[5] << 8) | (head[6] << 16) | (head[7] << 24);
	length = (long)(head[8] | (head[9] << 8) | (head[10] << 16) | ((unsigned long)head[11] << 24));
	if (k < 0 || length <= 0 || length > 4*1024*1024 || (long)k + length > bytes || !(text = AW_TryMalloc (length + 1)))
	{
		fclose (f);
		return;
	}
	if (fseek (f, at + k, SEEK_SET) || fread (text, 1, (size_t)length, f) != (size_t)length)
		length = 0;
	fclose (f);
	text[length] = 0;
	/* Each entity block: queued when it is an actor (the text is copied, the
	 * spawn happens later), skipped otherwise. */
	data = text;
	while ((data = COM_Parse (data)) != NULL && com_token[0] == '{' && npending < MAX_PENDING)
	{
		char *end = strchr (data, '}'), *o;
		pending_t *q;
		start = data;
		if (!end)
			break;
		*end = 0;
		if ((strstr (start, "\"aw_npc\"") || strstr (start, "\"aw_creature\"")) &&
			(q = &pending[npending], (q->text = AW_TryMalloc (strlen (start) + 3)) != NULL))
		{
			sprintf (q->text, "%s}", start);
			q->origin[0] = q->origin[1] = q->origin[2] = 0;
			if ((o = strstr (start, "\"origin\"")) != NULL)
			{
				/* Q_atof, never sscanf %f (strtod reaches 68040-unimplemented instructions) */
				char *v = o + 8;
				int axis;
				while (*v == ' ' || *v == '\t' || *v == '"')
					v++;
				for (axis=0 ; axis<3 && *v && *v != '"' ; axis++)
				{
					q->origin[axis] = Q_atof (v);
					while (*v && *v != ' ' && *v != '"')
						v++;
					while (*v == ' ')
						v++;
				}
			}
			q->offset[0] = offset[0];
			q->offset[1] = offset[1];
			q->offset[2] = 0;
			q->origin[0] += offset[0];
			q->origin[1] += offset[1];
			q->cx = (short)cx;
			q->cy = (short)cy;
			q->warmed = 0;
			q->table = 0;
			q->scale = 1.0f;
			npending++;
			queued++;
		}
		data = end + 1;
	}
	free (text);
	took = Sys_FloatTime () - t0;
	st.joins++;
	st.join_time += took;
	Con_Printf ("actors: frame %ld %ld joins: %ld actors queued (%ld waiting), %.1f ms\n", (long)cx, (long)cy,
		(long)queued, (long)npending, took*1000);
}

/* This tick's spawns: up to the budget, nearest to the player's position half
 * a second ahead first. */
static void SpawnQueued (void)
{
	edict_t *p = Player ();
	vec3_t ahead, d;
	int n, best, i, spawned = 0, limit = budget_n;
	float bd, dd;
	double t0, tl;
	if (!p)
		return;
	if (warm_on && limit > 0 && ClientSoundStep ())
		return;		/* this tick loaded a sound the client was still missing */
	if (!npending)
		return;
	t0 = Sys_FloatTime ();
	VectorMA (p->v.origin, 0.5f, p->v.velocity, ahead);
	for (n=0 ; npending && (limit <= 0 || n < limit) ; n++)
	{
		best = -1;
		bd = 1e30f;
		for (i=0 ; i<npending ; i++)
		{
			VectorSubtract (pending[i].origin, ahead, d);
			d[2] = 0;
			dd = DotProduct (d, d);
			if (dd < bd)
			{
				bd = dd;
				best = i;
			}
		}
		if (warm_on && limit > 0 && WarmStep (&pending[best]))
			break;		/* this tick loaded; the spawn comes on a later one */
		spawned += SpawnOne (&pending[best]);
		PendingDrop (best);
	}
	/* a tick that only loaded (warm) added nothing to the precache lists: no client list pass */
	tl = Sys_FloatTime ();
	if (spawned || !(warm_on && limit > 0))
		ClientLists (!(warm_on && budget_n > 0));
	tl = Sys_FloatTime () - tl;
	t0 = Sys_FloatTime () - t0;
	st.spawn_ticks++;
	st.spawn_time += t0;
	if (t0 > st.spawn_worst)
		st.spawn_worst = t0;
	if (aw_actors_trace)
	{
		if (warm_note[0])
			Con_Printf ("%s", warm_note);
		Con_Printf ("actors: tick spawned %ld in %.1f ms (client lists %.1f ms; %ld waiting, edicts %ld)\n",
			(long)spawned, t0*1000, tl*1000, (long)npending, (long)sv.num_edicts);
	}
	warm_note[0] = 0;
}

static void Leave (int cx, int cy)
{
	int i, ex, ey, held, released = 0, kept = 0, dropped = 0;
	unsigned long r0 = st.released;
	double t0 = Sys_FloatTime ();
	edict_t *e;
	if (!sv.active)
		return;
	for (i=npending-1 ; i>=0 ; i--)
		if (pending[i].cx == cx && pending[i].cy == cy)
		{
			PendingDrop (i);
			dropped++;
		}
	for (i=1 ; i<sv.num_edicts ; i++)
	{
		int own, hx, hy, hheld;
		e = EDICT_NUM(i);
		if (!IsActor (e) || !ChimChunks_WindowCell (e->v.origin, &ex, &ey, &held))
			continue;
		own = HomeOwned (e) && HomeCell (&hx, &hy, &hheld);
		if ((ex != cx || ey != cy) && !(own && hx == cx && hy == cy))
			continue;
		/* still on ground the window keeps (the leaving frame counts as held until it is gone): its own cell's frame,
		 * or the home frame for the home map's own actors */
		if ((held && (ex != cx || ey != cy)) || (own && hheld && (hx != cx || hy != cy)))
			continue;
		if (Keep (e))
		{
			kept++;
			continue;
		}
		Release (e);
	}
	released = (int)(st.released - r0);
	st.kept += kept;
	st.leaves++;
	st.leave_time += Sys_FloatTime () - t0;
	Con_Printf ("actors: frame %ld %ld leaves: %ld released to the change list (%ld entries), %ld kept alive, "
		"%ld never spawned dropped, %.1f ms\n", (long)cx, (long)cy, (long)released, (long)nchanges, (long)kept,
		(long)dropped, (Sys_FloatTime () - t0)*1000);
}

/* Every window tick: the queued spawns; every tenth, kept actors whose cell
 * left the window are released once no rule keeps them. */
static void Tick (void)
{
	static int n;
	int i, ex, ey, held;
	edict_t *e;
	if (!sv.active)
		return;
	{
		/* a new map (a level change into a town frame, or a load): the actors its own entities spawned take
		 * their change list state (a killed resident stays dead, as a joining frame's do: SpawnOne) */
		static char map[64];
		if (strncmp (map, sv.name, sizeof(map) - 1))
		{
			Q_strncpy (map, sv.name, sizeof(map) - 1);
			MarkHome ();
			if (nchanges)
				apply_pending = 1;
		}
	}
	if (apply_pending)
		ApplyLoaded ();
	SpawnQueued ();
	if (++n % 10)
		return;
	for (i=1 ; i<sv.num_edicts ; i++)
	{
		e = EDICT_NUM(i);
		if (!IsActor (e) || !ChimChunks_WindowCell (e->v.origin, &ex, &ey, &held) || held || Keep (e))
			continue;
		if (HomeOwned (e))
		{
			int hx, hy, hheld;
			if (HomeCell (&hx, &hy, &hheld) && hheld)
				continue;		/* the home map's own actor: the home frame holds its ground */
		}
		Con_Printf ("actors: %s left the window (cell %ld %ld): released to the change list\n",
			e->v.netname ? pr_strings + e->v.netname : "actor", (long)ex, (long)ey);
		Release (e);
		st.frees_by_tick++;
	}
}

static edict_t *tried[MAX_EDICTS];
static int ntried;

static edict_t *Nearest (void)
{
	edict_t *p = Player (), *e, *best = NULL;
	float bd = 1e30f, d;
	vec3_t v;
	int i, k;
	if (!p)
		return NULL;
	for (i=1 ; i<sv.num_edicts ; i++)
	{
		e = EDICT_NUM(i);
		if (!IsActor (e) || AW_CombatSlotState (e, NULL) == 2)
			continue;
		for (k=0 ; k<ntried && tried[k]!=e ; k++)
			;
		if (k < ntried)
			continue;
		VectorSubtract (e->v.origin, p->v.origin, v);
		d = DotProduct (v, v);
		if (d < bd)
		{
			bd = d;
			best = e;
		}
	}
	return best;
}

/* "chim actors hash LABEL": the world-state hash of the streamed-world acceptance
 * test (the same route run with both crossing methods must give the same hashes): the actors in the player's cell and every
 * actor in a fight or following (the companion), each as reference id, position in island
 * coordinates on a 32-unit grid, combat state and health; then the dead references. Independent
 * of the method: positions are converted from the session's origin cell to island coordinates.
 * One line per actor ("hash LABEL actor ...") so a difference names the actor and the field, then
 * "hash LABEL = FNV32". */
static unsigned Fnv (unsigned h, const char *s)
{
	for ( ; *s ; s++)
		h = (h ^ (unsigned char)*s) * 16777619u;
	return h;
}

static int CmpFloat (const void *a, const void *b)
{
	float x = *(const float *)a, y = *(const float *)b;
	return x < y ? -1 : x > y;
}

static void Hash (const char *label)
{
	static float refs[MAX_EDICTS], dead[MAX_CHANGES + MAX_EDICTS];
	static char lines[MAX_EDICTS][128];
	int i, j, n = 0, nd = 0, ox, oy, pcx, pcy, ecx, ecy, state, comp;
	unsigned h = 2166136261u;
	edict_t *e, *p = Player ();
	float health, gx, gy, gz;
	char buf[128];
	if (!p || !ChimChunks_OriginCell (&ox, &oy))
	{
		Con_Printf ("hash %s: no player or no CHIM region frame\n", label);
		return;
	}
	pcx = ox + (int)floor ((p->v.origin[0] + 1024) / 2048.0f);
	pcy = oy + (int)floor ((p->v.origin[1] + 1024) / 2048.0f);
	for (i=1 ; i<sv.num_edicts && n<MAX_EDICTS ; i++)
	{
		e = EDICT_NUM(i);
		comp = !e->free && AW_CompanionEdict (e);
		if (!comp && !IsActor (e))
			continue;
		state = AW_CombatSlotState (e, &health);
		if (state != 2 || !comp)
		{
			if (state == 2)
			{
				dead[nd++] = RefOf (e);
				continue;
			}
		}
		ecx = ox + (int)floor ((e->v.origin[0] + 1024) / 2048.0f);
		ecy = oy + (int)floor ((e->v.origin[1] + 1024) / 2048.0f);
		if (!comp && state != 1 && (ecx != pcx || ecy != pcy))
			continue;
		gx = e->v.origin[0] + ox * 2048 + 1024;
		gy = e->v.origin[1] + oy * 2048 + 1024;
		gz = e->v.origin[2];
		snprintf (lines[n], sizeof(lines[n]), "%s ref %.0f at %ld %ld %ld state %d health %ld",
			comp ? "companion" : "actor", comp ? 0 : RefOf (e), (long)floor (gx / 32 + .5f), (long)floor (gy / 32 + .5f),
			(long)floor (gz / 32 + .5f), state, state ? (long)(health + .5f) : -1L);
		refs[n] = comp ? -1 : RefOf (e);
		n++;
	}
	for (i=0 ; i<nchanges ; i++)
		if (changes[i].dead)
			dead[nd++] = changes[i].ref;
	/* the levelled picks (only with the actor table's lists): one line each, by reference (a load restores the
	 * change list sorted, so the hash must not depend on the order the entries were made in) */
	{
		static float picked[MAX_CHANGES];
		int np = 0;
		for (i=0 ; i<nchanges ; i++)
			if (changes[i].pick)
				picked[np++] = changes[i].ref;
		qsort (picked, np, sizeof(float), CmpFloat);
		for (i=0 ; i<np ; i++)
		{
			change_t *c = Change (picked[i], 0);
			snprintf (buf, sizeof(buf), "pick %.0f %ld", picked[i], (long)c->pick - 2);
			Con_Printf ("hash %s %s\n", label, buf);
			h = Fnv (h, buf);
		}
	}
	/* sort the lines by reference id (insertion sort: few) */
	for (i=1 ; i<n ; i++)
		for (j=i ; j>0 && refs[j-1] > refs[j] ; j--)
		{
			float t = refs[j]; refs[j] = refs[j-1]; refs[j-1] = t;
			memcpy (buf, lines[j], sizeof(buf)); memcpy (lines[j], lines[j-1], sizeof(buf)); memcpy (lines[j-1], buf, sizeof(buf));
		}
	qsort (dead, nd, sizeof(float), CmpFloat);
	for (i=0 ; i<n ; i++)
	{
		Con_Printf ("hash %s %s\n", label, lines[i]);
		h = Fnv (h, lines[i]);
	}
	for (i=0 ; i<nd ; i++)
		if (!i || dead[i] != dead[i-1])
		{
			snprintf (buf, sizeof(buf), "dead %.0f", dead[i]);
			Con_Printf ("hash %s %s\n", label, buf);
			h = Fnv (h, buf);
		}
	Con_Printf ("hash %s = %08lx (%ld actors, player cell %ld %ld)\n", label, (unsigned long)h, (long)n, (long)pcx, (long)pcy);
}

static void Command (void)
{
	char *a = Cmd_Argv (2);
	if (!strcmp (a, "ambient"))
	{
		if (aw_ambient_cmd)
			aw_ambient_cmd ();		/* the Wander packages (aw_ambient.c sets it) */
		else
			Con_Printf ("chim actors ambient: not in this engine\n");
		return;
	}
	if (Cmd_Argc () == 4 && !strcmp (a, "hash"))
	{
		Hash (Cmd_Argv (3));
		return;
	}
	int i, n = 0, cx, cy, held;
	edict_t *e;
	float h;
	/* The settings first: they hold without a running map. default-game.cfg runs before any map starts, so a
	 * settings line behind the running-map check below was dropped without a word: "chim actors table 1" never
	 * took, every joining frame read its frame map, and the 5,082 levelled creature references of the exterior were
	 * never rolled (CHIM-EXTERIOR-ACTORS-MISSING-46, found 2026-10-27 in the v0.0.53 final: "actors: frame 1 -7
	 * joins", never "joins from the actor table"). */
	if (Cmd_Argc () == 4 && !strcmp (a, "budget"))
	{
		budget_n = atoi (Cmd_Argv (3));
		Con_Printf ("chim actors: %d spawns per tick (0: all at once)\n", budget_n);
		return;
	}
	if (Cmd_Argc () == 4 && !strcmp (a, "warm"))
	{
		warm_on = atoi (Cmd_Argv (3)) != 0;
		Con_Printf ("chim actors: warm %d (first-time model and voice loads on ticks of their own)\n", warm_on);
		return;
	}
	if (Cmd_Argc () >= 3 && !strcmp (a, "table"))
	{
		if (Cmd_Argc () == 4)
			table_on = atoi (Cmd_Argv (3)) != 0;
		Con_Printf ("chim actors table %d (%s): joins %lu, records %lu, queued %lu, without a model %lu, "
			"not an actor %lu, queue full %lu; levelled %lu (kept picks %lu, nothing %lu, no model %lu; player level %ld, "
			"seed %lu)\n", table_on, table_on ? "actors join from the actor table" :
			"actors join from the frame maps", table.joins, table.records, table.spawnable, table.no_model,
			table.not_actor, table.full, table.levelled, table.levelled_kept, table.levelled_none,
			table.levelled_no_model, (long)(aw_character.valid && aw_character.level > 0 ? aw_character.level : 1),
			(unsigned long)roll_seed);
		return;
	}
	if (Cmd_Argc () == 4 && !strcmp (a, "seed"))
	{
		roll_seed = (unsigned)strtoul (Cmd_Argv (3), NULL, 10);
		Con_Printf ("chim actors: levelled lists seed %lu (picks already kept stay)\n", (unsigned long)roll_seed);
		return;
	}
	if (Cmd_Argc () == 4 && !strcmp (a, "trace"))
	{
		aw_actors_trace = atoi (Cmd_Argv (3));
		return;
	}
	if (Cmd_Argc () >= 3 && !strcmp (a, "creatures"))
	{
		int released = 0, alive = 0;
		if (Cmd_Argc () == 4)
		{
			char *w = Cmd_Argv (3);
			int on = !Q_strcasecmp (w, "on") || !Q_strcasecmp (w, "true") || !strcmp (w, "1") ? 1 :
				!Q_strcasecmp (w, "off") || !Q_strcasecmp (w, "false") || !strcmp (w, "0") ? 0 : -1;
			if (on < 0)
			{
				Con_Printf ("Usage: dbg creatures [on/off, true/false or 1/0]\n");
				return;
			}
			creatures_on = on;
		}
		for (i=1 ; sv.active && i<sv.num_edicts ; i++)
		{
			e = EDICT_NUM(i);
			if (!IsCreature (e))
				continue;
			if (!creatures_on && !AW_CompanionEdict (e))
			{
				Release (e);
				released++;
			}
			else
				alive++;
		}
		Con_Printf ("Creatures %s: %d alive, %d released now, %lu spawns skipped while off (outdoor creatures; not saved)\n",
			creatures_on ? "on" : "off", alive, released, creatures_skipped);
		return;
	}
	if (!sv.active)
		return;
	if (Cmd_Argc () == 3 && (!strcmp (a, "fight") || !strcmp (a, "kill")))
	{
		/* the nearest resident that has a combat sheet */
		ntried = 0;
		while ((e = Nearest ()) != NULL && !AW_CombatTestEngage (e, a[0] == 'k') && ntried < MAX_EDICTS)
			tried[ntried++] = e;
		if (!e)
		{
			Con_Printf ("chim actors %s: no resident with a combat sheet near\n", a);
			return;
		}
		Con_Printf ("chim actors %s: %s (ref %.0f, edict %ld)\n", a, e->v.netname ? pr_strings + e->v.netname : "?",
			RefOf (e), (long)NUM_FOR_EDICT(e));
		return;
	}
	if (Cmd_Argc () == 3 && !strcmp (a, "summon"))
	{
		/* TEST: a copy of the nearest resident standing exactly where the player stands (the player's feet: ground
		 * the player's own hull rests on, so the copy's support test and path search find it), with its own
		 * reference id; then "chim actors fight" makes it the pursuer. Same command, same place in both methods. */
		static int summoned;
		edict_t *src = Nearest (), *p = Player (), *copy;
		eval_t *v;
		if (!src || !p)
		{
			Con_Printf ("chim actors summon: no resident to copy\n");
			return;
		}
		copy = ED_Alloc ();
		memcpy (&copy->v, &src->v, progs->entityfields * 4);
		copy->v.origin[0] = p->v.origin[0];
		copy->v.origin[1] = p->v.origin[1];
		copy->v.origin[2] = p->v.origin[2] + p->v.mins[2];
		VectorCopy (p->v.angles, copy->v.angles);
		copy->v.flags = (float)((int)copy->v.flags | FL_ONGROUND);
		if ((v = GetEdictFieldValue (copy, "aw_ref")) != NULL)
			v->_float = (float)(900500 + summoned++);
		if ((v = GetEdictFieldValue (copy, "aw_ground_valid")) != NULL)
			v->_float = 0;
		AW_AnimPrep (copy);
		AW_ItemsPrep (copy);
		SV_LinkEdict (copy, false);
		Con_Printf ("chim actors summon: a copy of %s (ref %.0f) at %.0f %.0f %.0f\n", copy->v.netname ?
			pr_strings + copy->v.netname : "?", RefOf (copy), copy->v.origin[0], copy->v.origin[1], copy->v.origin[2]);
		return;
	}
	if (Cmd_Argc () == 3 && !strcmp (a, "resetstats"))
	{
		memset (&st, 0, sizeof(st));
		memset (&wst, 0, sizeof(wst));
		return;
	}
	if (Cmd_Argc () == 3 && !strcmp (a, "clear"))
	{
		nchanges = 0;
		carried.count = 0;
		Con_Printf ("chim actors: change list cleared\n");
		return;
	}
	for (i=1 ; i<sv.num_edicts ; i++)
	{
		e = EDICT_NUM(i);
		if (!IsActor (e))
			continue;
		n++;
		if (Cmd_Argc () == 3 && !strcmp (a, "list"))
		{
			int state = AW_CombatSlotState (e, &h);
			if (!ChimChunks_WindowCell (e->v.origin, &cx, &cy, &held))
				cx = cy = held = 0;
			Con_Printf ("  %ld %s ref %.0f cell %ld %ld%s at %.0f %.0f %.0f%s%s\n", (long)i,
				e->v.netname ? pr_strings + e->v.netname : "?", RefOf (e), (long)cx, (long)cy, held ? "" : " (outside)",
				e->v.origin[0], e->v.origin[1], e->v.origin[2], state == 1 ? " FIGHTING" : state == 2 ? " DEAD" : "",
				AW_CompanionEdict (e) ? " COMPANION" : "");
		}
	}
	Con_Printf ("chim actors: %ld actors alive, %ld edicts; joins %lu (%.1f ms reading); spawned %lu in %lu ticks "
		"(%.1f ms, worst tick %.1f ms, budget %ld per tick, %ld waiting; dead skipped %lu, alive skipped %lu, disabled "
		"skipped %lu); leaves %lu (released %lu, kept %lu, by tick %lu, %.1f ms); change list %ld\n",
		(long)n, (long)sv.num_edicts, st.joins, st.join_time*1000, st.spawned, st.spawn_ticks, st.spawn_time*1000,
		st.spawn_worst*1000, (long)budget_n, (long)npending, st.skipped_dead, st.skipped_alive, st.skipped_disabled, st.leaves,
		st.released, st.kept, st.frees_by_tick, st.leave_time*1000, (long)nchanges);
	Con_Printf ("chim actors: warm %d; warmed %lu models (%.1f ms), %lu voices (%.1f ms), %lu client sounds (%.1f ms), worst warm tick %.1f ms\n",
		warm_on, wst.models, wst.model_time*1000, wst.voices, wst.voice_time*1000, wst.sounds, wst.sound_time*1000, wst.worst*1000);
}

/* The change list in a save (aw_save.c, AWS4 feature 8; aw_save.h): every change entry plus the actors alive in
 * the session now (captured, not released), keyed by AW_SaveChangeKey of the reference; entries a load brought
 * that this module does not place (old actor rows of a scene, builder-made keys) are carried through unchanged.
 * Returns the number written, -1 when they do not fit. */

static aw_change_t *Entry (aw_changes_t *out, uint32_t key)
{
	int i;
	for (i=0 ; i<out->count ; i++)
		if (out->entry[i].key == key)
			return &out->entry[i];
	if (out->count == AW_SAVE_CHANGES)
		return NULL;
	memset (&out->entry[out->count], 0, sizeof(aw_change_t));
	out->entry[out->count].key = key;
	return &out->entry[out->count++];
}

static int ToEntry (const change_t *c, aw_changes_t *out)
{
	uint32_t ref = (uint32_t)c->ref, flags;
	aw_change_t *e;
	int cx, cy;
	if (!c->ref || c->ref < 0 || ref > 0xFFFFFFu)
		return 1;
	flags = (c->dead ? AW_CHANGE_DEAD : 0) | (c->moved ? AW_CHANGE_MOVED : 0) | (c->fight ? AW_CHANGE_FIGHT : 0) |
		(c->follow ? AW_CHANGE_FOLLOW : 0) | (c->pick ? AW_CHANGE_PICK : 0);
	if (!flags)
		return 1;			/* nothing to keep */
	if (!(e = Entry (out, AW_SaveChangeKey (ref))))
		return 0;
	e->flags = flags;
	e->pick = c->pick;
	VectorCopy (c->origin, e->position);
	e->yaw = anglemod (c->angles[1]);
	e->health = c->health;
	e->hours = c->hours;
	cx = (int)floor (c->origin[0] / 2048.0f);
	cy = (int)floor (c->origin[1] / 2048.0f);
	e->where = (int32_t)(((uint32_t)(cx & 0xFFFF) << 16) | (uint32_t)(cy & 0xFFFF));
	return 1;
}

static int SaveExport (aw_changes_t *out)
{
	int i;
	edict_t *e;
	change_t live;
	out->count = 0;
	for (i=0 ; i<carried.count ; i++)
		out->entry[out->count++] = carried.entry[i];
	for (i=0 ; i<nchanges ; i++)
		if (!ToEntry (&changes[i], out))
			return -1;
	if (sv.active)
		for (i=1 ; i<sv.num_edicts ; i++)
		{
			e = EDICT_NUM(i);
			if (!IsActor (e) || !RefOf (e))
				continue;
			memset (&live, 0, sizeof(live));
			live.ref = RefOf (e);
			{
				change_t *c = Change (live.ref, 0);
				if (c)
				{
					live.pick = c->pick;
					live.dead = c->dead;
				}
			}
			Capture (e, &live);
			if (!ToEntry (&live, out))
				return -1;
		}
	return out->count;
}

/* A loaded save's change list becomes the session's (before the window spawns its actors). */
static void SaveImport (const aw_changes_t *in)
{
	int i;
	nchanges = 0;
	carried.count = 0;
	for (i=0 ; i<in->count ; i++)
	{
		const aw_change_t *e = &in->entry[i];
		change_t *c;
		if (e->flags & AW_CHANGE_SCENE)
			continue;		/* an old save's actor row (AW_SaveFoldActors): the save's actor rows keep it */
		if ((e->key & AW_CHANGE_BUILDER) || nchanges == MAX_CHANGES)
		{
			carried.entry[carried.count++] = *e;	/* not this module's: kept for the next save */
			continue;
		}
		c = &changes[nchanges++];
		memset (c, 0, sizeof(*c));
		c->ref = (float)e->key;
		c->dead = (e->flags & AW_CHANGE_DEAD) ? 1 : 0;
		c->moved = (e->flags & AW_CHANGE_MOVED) ? 1 : 0;
		c->fight = (e->flags & AW_CHANGE_FIGHT) ? 1 : 0;
		c->follow = (e->flags & AW_CHANGE_FOLLOW) ? 1 : 0;
		c->pick = (unsigned short)((e->flags & AW_CHANGE_PICK) ? e->pick : 0);
		VectorCopy (e->position, c->origin);
		c->angles[0] = c->angles[2] = 0;
		c->angles[1] = e->yaw;
		c->health = e->health;
		c->hours = e->hours;
	}
	apply_pending = 1;
	Con_Printf ("actors: %d changes from the save (%d carried for other modules)\n", nchanges, carried.count);
}

/* After a load or a level change, at the first window tick (the scene's combat set-up has run by then): the actors
 * the new scene's own map spawned (a town frame's residents) take their saved state too: a killed one is dead again, a
 * fight goes on with its health, one that was moved stands where it was left. */
static void ApplyLoaded (void)
{
	float d[3];
	int i, applied = 0;
	apply_pending = 0;
	MarkHome ();		/* a load spawned the map's actors again (the same map name: no new map seen) */
	IslandOffset (d);
	for (i=1 ; i<sv.num_edicts ; i++)
	{
		edict_t *e = EDICT_NUM(i);
		change_t *c;
		if (!IsActor (e) || !(c = Change (RefOf (e), 0)))
			continue;
		if (c->moved)
		{
			VectorSubtract (c->origin, d, e->v.origin);
			VectorCopy (c->angles, e->v.angles);
			SV_LinkEdict (e, false);
		}
		if (c->dead)
			AW_CombatTestEngage (e, 1);
		else if (c->fight && AW_CombatTestEngage (e, 0))
			AW_CombatSetHealth (e, c->health);
		applied++;
	}
	Con_Printf ("actors: the save's changes applied to %d of the scene's actors\n", applied);
}

void AW_ActorsInit (void)
{
	aw_save_changes_export = SaveExport;
	aw_save_changes_import = SaveImport;
	chim_actors_join = Join;
	chim_actors_leave = Leave;
	chim_actors_tick = Tick;
	chim_actors_cmd = Command;		/* "chim actors ...": no command or cvar of its own (the resident registry budget) */
	aw_levelled_entity = LevelledEntity;	/* a room map's levelled creatures (pr_edict.c ED_LoadFromFile) */
}
