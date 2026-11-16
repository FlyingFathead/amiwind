/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_actors.c (the type 1 window's actors, EXPERIMENTAL, "chim crossing 1") with small stubs: the spawn queue and
 * its per-tick budget, the warm step's order (model, voice, spawn, then the client's new sounds one per tick), the
 * client lists keeping mover models lazy, actor-table queue entries (record placement, reference id, instance
 * scale on the entity) and the levelled roll (the same pick for the same seed, kept for a later join).
 *
 * usage: check MODE TABLE FRAME SEED FRAME2
 *   MODE queue | warm | lazy | table | roll | save | home   (roll prints its picks; the Python side compares two
 *   runs; save: the change list through a save's export and a load's import; home: the home map's own actors)
 * The engine pieces it stands in for: the edicts and their QuakeC fields (GetEdictFieldValue), ED_ParseEdict (the
 * "key" "value" pairs this module reads), the spawn function (PR_ExecuteProgram: precaches the model, the voice, a
 * footstep sound of the animation layout and, for models named "*_mover.mdl", a mover model by name only, as
 * aw_anim.c does), the model and sound caches (each first load logged), the file system (the frame map and the actor
 * table are real files).
 */
#include "quakedef.h"
#include <assert.h>
#include "aw_actors.h"
#include "aw_character.h"
#include "aw_save.h"
#include "aw_state.h"
#include "aw_ledger.h"

server_t sv;
server_static_t svs;
client_state_t cl;
aw_character_t aw_character;
char com_token[1024];
static globalvars_t globals;
globalvars_t *pr_global_struct = &globals;
static dfunction_t functions[2];
dfunction_t *pr_functions = functions;
static dprograms_t programs;
dprograms_t *progs = &programs;
static char strings[1 << 16];
char *pr_strings = strings;
static int nstrings = 1;
void (*chim_actors_join)(int cx, int cy, const char *map, const float *offset);
void (*chim_actors_leave)(int cx, int cy);
void (*chim_actors_tick)(void);
void (*chim_actors_cmd)(void);
/* the save's hooks (aw_save_codec.c) and the game clock's state (aw_state.c): this module fills and reads them */
int (*aw_save_changes_export)(aw_changes_t *changes);
void (*aw_save_changes_import)(const aw_changes_t *changes);
aw_state_t aw_state;
/* the game clock (amiwind:clock:*): stopped (0) unless a check sets test_hours (ACTOR-RESPAWN-CORPSE-RULES-66) */
static long test_hours;
int32_t AW_StateGet (const aw_state_t *state, int kind, const char *id)
{
	if (!test_hours)
		return 0;
	if (!strcmp (id, "amiwind:clock:ready"))
		return 1;
	if (!strcmp (id, "amiwind:clock:days"))
		return (int32_t)(test_hours / 24);
	if (!strcmp (id, "amiwind:clock:ms"))
		return (int32_t)((test_hours % 24) * 3600000L);
	return 0;
}
uint32_t AW_SaveChangeKey (uint32_t reference)
{
	return reference >= 0x800000U && reference <= 0xffffffU ? AW_CHANGE_BUILDER | (reference - 0x800000U) : reference;
}
void Q_strncpy (char *dest, char *src, int count) {strncpy (dest, src, count); if (count > 0) dest[count-1] = 0;}

/* ---- events: every first-time load and every spawn, in order */
static char events[256][96];
static int nevents;
static void event (const char *what, const char *name)
{
	assert (nevents < 256);
	snprintf (events[nevents++], sizeof(events[0]), "%s %s", what, name);
}

/* ---- edicts with their QuakeC fields */
#define EDICTS 64
#define FIELDS 12
static edict_t ents[EDICTS];
static struct {char name[24]; eval_t v[3];} fields[EDICTS][FIELDS];
edict_t *EDICT_NUM (int n) {assert (n >= 0 && n < EDICTS); return &ents[n];}
int NUM_FOR_EDICT (edict_t *e) {return (int)(e - ents);}
eval_t *GetEdictFieldValue (edict_t *e, char *name)
{
	int n = (int)(e - ents), i;
	static const char *known[] = {"aw_ref", "aw_ground_baked", "aw_ground_valid", "aw_scale", "aw_source_id", "aw_voice"};
	for (i=0 ; i<(int)(sizeof(known)/sizeof(known[0])) ; i++)
		if (!strcmp (name, known[i]))
			break;
	if (i == (int)(sizeof(known)/sizeof(known[0])))
		return NULL;
	if (!fields[n][i].name[0])
		strcpy (fields[n][i].name, name);
	return fields[n][i].v;
}
static string_t NewString (const char *s)
{
	int at = nstrings;
	assert (nstrings + (int)strlen (s) + 1 < (int)sizeof(strings));
	strcpy (strings + at, s);
	nstrings += (int)strlen (s) + 1;
	return at;
}
edict_t *ED_Alloc (void)
{
	int i;
	for (i=2 ; i<EDICTS ; i++)		/* 0 world, 1 the player */
		if (i >= sv.num_edicts || ents[i].free)
		{
			memset (&ents[i], 0, sizeof(ents[i]));
			memset (fields[i], 0, sizeof(fields[i]));
			if (i >= sv.num_edicts)
				sv.num_edicts = i + 1;
			return &ents[i];
		}
	assert (0);
	return NULL;
}
void ED_Free (edict_t *e) {e->free = true;}
char *ED_ParseEdict (char *data, edict_t *ent)
{
	char key[64], value[256];
	eval_t *v;
	for (;;)
	{
		char *s = strchr (data, '"'), *e;
		if (!s || (strchr (data, '}') && strchr (data, '}') < s))
			break;
		e = strchr (s + 1, '"');
		memcpy (key, s + 1, e - s - 1);
		key[e - s - 1] = 0;
		s = strchr (e + 1, '"');
		e = strchr (s + 1, '"');
		memcpy (value, s + 1, e - s - 1);
		value[e - s - 1] = 0;
		data = e + 1;
		if (!strcmp (key, "classname"))
			ent->v.classname = NewString (value);
		else if (!strcmp (key, "model"))
			ent->v.model = NewString (value);
		else if (!strcmp (key, "netname"))
			ent->v.netname = NewString (value);
		else if (!strcmp (key, "origin"))
			sscanf (value, "%f %f %f", &ent->v.origin[0], &ent->v.origin[1], &ent->v.origin[2]);
		else if (!strcmp (key, "aw_ref") && (v = GetEdictFieldValue (ent, "aw_ref")) != NULL)
			v->_float = (float)atof (value);
		else if (!strcmp (key, "aw_voice") && (v = GetEdictFieldValue (ent, "aw_voice")) != NULL)
			v->string = NewString (value);
	}
	return strchr (data, '}') ? strchr (data, '}') + 1 : data;
}
dfunction_t *ED_FindFunction (char *name)
{
	return !strcmp (name, "aw_npc") ? &functions[0] : !strcmp (name, "aw_creature") ? &functions[1] : NULL;
}

/* ---- the model and sound caches */
#define MODELS 32
static model_t models[MODELS];
static int nmodels;
static int cached[MODELS];
model_t *Mod_FindName (char *name)
{
	int i;
	for (i=0 ; i<nmodels ; i++)
		if (!strcmp (models[i].name, name))
			return &models[i];
	assert (nmodels < MODELS);
	strcpy (models[nmodels].name, name);
	models[nmodels].needload = 1;		/* NL_NEEDS_LOADED */
	models[nmodels].type = mod_alias;
	return &models[nmodels++];
}
model_t *Mod_ForName (char *name, qboolean crash)
{
	model_t *m = Mod_FindName (name);
	if (m->needload || !m->cache.data)
	{
		event ("load model", name);
		m->needload = 0;
		m->cache.data = &cached[m - models];
	}
	return m;
}
void *Cache_Check (cache_user_t *c) {return c->data;}
#define SOUNDS 32
static sfx_t sounds[SOUNDS];
static int nsounds, sound_cached[SOUNDS];
sfx_t *S_FindName (char *name)
{
	int i;
	for (i=0 ; i<nsounds ; i++)
		if (!strcmp (sounds[i].name, name))
			return &sounds[i];
	assert (nsounds < SOUNDS);
	strcpy (sounds[nsounds].name, name);
	return &sounds[nsounds++];
}
sfx_t *S_PrecacheSound (char *name)
{
	sfx_t *s = S_FindName (name);
	if (!s->cache.data)
	{
		event ("load sound", name);
		s->cache.data = &sound_cached[s - sounds];
	}
	return s;
}
static void flush_caches (void)
{
	int i;
	for (i=0 ; i<nmodels ; i++)
		models[i].cache.data = NULL;
	for (i=0 ; i<nsounds ; i++)
		sounds[i].cache.data = NULL;
}

/* ---- the spawn function (QuakeC aw_npc/aw_creature, world.qc) as far as this module sees it */
static int precache_model (const char *name, int lazy)
{
	int i;
	for (i=1 ; i<MAX_MODELS && sv.model_precache[i] ; i++)
		if (!strcmp (sv.model_precache[i], name))
			return i;
	sv.model_precache[i] = pr_strings + NewString (name);
	sv.models[i] = lazy ? Mod_FindName (sv.model_precache[i]) : Mod_ForName (sv.model_precache[i], true);
	return i;
}
static void precache_sound (const char *name)
{
	int i;
	for (i=1 ; i<MAX_SOUNDS && sv.sound_precache[i] ; i++)
		if (!strcmp (sv.sound_precache[i], name))
			return;
	sv.sound_precache[i] = pr_strings + NewString (name);
}
void PR_ExecuteProgram (func_t fnum)
{
	edict_t *e = PROG_TO_EDICT(pr_global_struct->self);
	const char *model = pr_strings + e->v.model;
	eval_t *voice = GetEdictFieldValue (e, "aw_voice");
	char step[96], mover[96];
	assert (sv.state == ss_loading);	/* precache only in a spawn function */
	e->v.modelindex = (float)precache_model (model, 0);
	if (voice && voice->string)
	{
		precache_sound (pr_strings + voice->string);
		S_PrecacheSound (pr_strings + voice->string);	/* the server's precache loads it (snd_dma.c) */
	}
	snprintf (step, sizeof(step), "step/%s.wav", model + 6);	/* the layout's footstep */
	precache_sound (step);
	if (strstr (model, "_mover"))
	{
		snprintf (mover, sizeof(mover), "progs/worn_%s", model + 6);	/* registered by name, loaded while worn */
		precache_model (mover, 1);
	}
	event ("spawn", model);
}
int AW_AnimLazy (const char *name) {return strstr (name, "worn_") != NULL;}

/* ---- the rest of the engine */
static const char *table_path, *frame_path, *frame2_path;
int COM_FOpenFile (char *path, FILE **file)
{
	const char *p = !strcmp (path, "maps/chim-actors.cca") ? table_path : strstr (path, "frame2") ? frame2_path : frame_path;
	long n;
	*file = p ? fopen (p, "rb") : NULL;
	if (!*file)
		return -1;
	fseek (*file, 0, SEEK_END);
	n = ftell (*file);
	fseek (*file, 0, SEEK_SET);
	return (int)n;
}
char *COM_Parse (char *data)
{
	while (data && *data && (*data == ' ' || *data == '\n' || *data == '\t' || *data == '\r'))
		data++;
	if (!data || !*data)
		return NULL;
	com_token[0] = *data;
	com_token[1] = 0;
	return data + 1;
}
void AW_MapPath (const char *name, char *out, int size) {snprintf (out, size, "maps/%s.chim", name);}
static double now;
double Sys_FloatTime (void) {return now += 0.0001;}
void Con_Printf (char *fmt, ...)
{
	va_list ap;
	va_start (ap, fmt);
	vprintf (fmt, ap);
	va_end (ap);
}
static char *argv_[6];
static int argc_;
int Cmd_Argc (void) {return argc_;}
char *Cmd_Argv (int i) {return i < argc_ ? argv_[i] : "";}
static void command (const char *a, const char *b)
{
	argv_[0] = "chim"; argv_[1] = "actors"; argv_[2] = (char *)a; argv_[3] = (char *)b;
	argc_ = b ? 4 : 3;
	chim_actors_cmd ();
}
void SV_LinkEdict (edict_t *e, qboolean touch) {}
float Q_atof (char *str) {return (float)atof (str);}	/* common.c; the Amiga build avoids strtod, a host test may not */
void Sys_Error (char *error, ...) {va_list ap; va_start (ap, error); vprintf (error, ap); va_end (ap); abort ();}
void AW_AnimPrep (edict_t *e) {}
void AW_ItemsPrep (edict_t *e) {}
int AW_CompanionEdict (edict_t *e) {return 0;}
/* combat: the reference DEAD_REF counts as killed (slot state 2) */
static float dead_ref;
static int is_laid (float ref);
static int on_map (float ref);
int AW_CombatSlotState (edict_t *e, float *health)
{
	eval_t *v = GetEdictFieldValue (e, "aw_ref");
	return v && ((dead_ref && v->_float == dead_ref) || is_laid (v->_float)) ? 2 : 0;
}
/* ACTOR-DEAD-RESPAWN-INTERIOR-65: the bodies laid down (AW_CombatTestEngage with DEAD), as the combat slots hold them;
 * the scene's set-up empties them (AW_CombatSceneSpawn: combat_scene_reset) */
static float laid[8];
static int nlaid;
int AW_CombatTestEngage (edict_t *e, int dead)
{
	eval_t *v = GetEdictFieldValue (e, "aw_ref");
	if (!dead || !v || nlaid == 8)
		return 0;
	laid[nlaid++] = v->_float;
	return 1;
}
/* a saved death laid down again (OUTDOOR-DEAD-BODY-GONE-66): the same corpse, counted apart */
static int nlay_saved;
int AW_CombatLayCorpse (edict_t *e) {nlay_saved++; return AW_CombatTestEngage (e, 1);}
static void combat_scene_reset (void) {nlaid = 0;}
static int is_laid (float ref)
{
	int i;
	for (i=0 ; i<nlaid ; i++)
		if (laid[i] == ref)
			return 1;
	return 0;
}
int AW_CombatSetHealth (edict_t *e, float health) {return 0;}
void AW_CombatForget (edict_t *e) {}
void AW_CompanionKillMode (void) {}
void AW_CompanionKillCrime (void) {}	/* dbg kill crime (CRIME-59) */
int ChimChunks_OriginCell (int *cx, int *cy) {*cx = *cy = 0; return 1;}
/* the residents' recipe tables (aw_npc_parts.c, BUILD-NPC-RECIPES-PER-CELL-59): in with a join, out with a leave */
static int parts_cells_in, parts_cells_out, parts_rooms;
void AW_NpcPartsCell (int cx, int cy, int in) {if (in) parts_cells_in++; else parts_cells_out++;}
void AW_NpcPartsRoom (const char *map) {parts_rooms++;}
/* The window's cell of a position: here the cell the test says is leaving (every actor stands in it), held by the
 * window (a tick releases nobody). */
static int leaving_cx, leaving_cy;
/* grid mode (the home frame test): the cell of a position around home cell 0 0, held when listed in HELD_CELLS */
static int grid_mode, held_cells[4][2], nheld;
int ChimChunks_WindowCell (const vec3_t origin, int *cx, int *cy, int *held)
{
	if (grid_mode)
	{
		int k;
		*cx = (int)floor ((origin[0] + 1024) / 2048);
		*cy = (int)floor ((origin[1] + 1024) / 2048);
		for (*held=0, k=0 ; k<nheld ; k++)
			*held |= held_cells[k][0] == *cx && held_cells[k][1] == *cy;
		return 1;
	}
	*cx = leaving_cx;
	*cy = leaving_cy;
	*held = 1;
	return 1;
}

/* ---- checks */
static int count (const char *what)
{
	int i, n = 0;
	for (i=0 ; i<nevents ; i++)
		n += !strncmp (events[i], what, strlen (what));
	return n;
}
static int index_of (const char *ev)
{
	int i;
	for (i=0 ; i<nevents ; i++)
		if (!strcmp (events[i], ev))
			return i;
	return -1;
}
static int actors_alive (void)
{
	int i, n = 0;
	for (i=2 ; i<sv.num_edicts ; i++)
		n += !ents[i].free && ents[i].v.classname;
	return n;
}
static void reset_level (void)
{
	int i;
	memset (sv.model_precache, 0, sizeof(sv.model_precache));
	memset (sv.sound_precache, 0, sizeof(sv.sound_precache));
	memset (cl.model_precache, 0, sizeof(cl.model_precache));
	memset (cl.sound_precache, 0, sizeof(cl.sound_precache));
	for (i=2 ; i<sv.num_edicts ; i++)
		ents[i].free = true;
	nevents = 0;
}

static void queue_and_budget (void)
{
	static const float none[2] = {0, 0}, east[2] = {1024, 0};
	int ticks;
	/* budget 1 (the default): the frame's three actors one per tick, the nearest to the player first */
	chim_actors_join (0, 0, "frame", none);
	assert (actors_alive () == 0);			/* a join only queues */
	chim_actors_tick ();
	assert (actors_alive () == 1 && count ("spawn") == 1);
	assert (!strcmp (events[index_of ("spawn progs/a_near.mdl")], "spawn progs/a_near.mdl"));
	assert (index_of ("spawn progs/a_near.mdl") >= 0 && index_of ("spawn progs/a_far_mover.mdl") < 0);
	chim_actors_tick ();
	chim_actors_tick ();
	assert (actors_alive () == 3 && count ("spawn") == 3);
	assert (index_of ("spawn progs/a_far_mover.mdl") > index_of ("spawn progs/a_mid.mdl"));
	/* the same frame joining again: alive actors are not spawned twice */
	chim_actors_join (0, 0, "frame", none);
	for (ticks=0 ; ticks<4 ; ticks++)
		chim_actors_tick ();
	assert (actors_alive () == 3 && count ("spawn") == 3);
	/* budget 0 (all at once): the next frame's three actors in one tick, moved by the frame's offset */
	command ("budget", "0");
	chim_actors_join (1, 0, "frame2", east);
	chim_actors_tick ();
	assert (actors_alive () == 6 && count ("spawn") == 6);
	assert (ents[sv.num_edicts - 1].v.origin[0] >= 1024);
	command ("budget", "1");
	assert (parts_cells_in >= 3 && parts_rooms >= 0);	/* every join brings its cell's recipe table in */
	puts ("queue and budget passed");
}

/* Object state (v0.0.51): a script's Disable keeps an actor of the window from spawning; since v0.0.62 the Enable
 * spawns it on the next tick, its cell still in the window (SCRIPTED-EVENT-FALLING-MAGE-61), and a later join of the
 * same cell does not spawn it twice (aw_mwhost.c sets aw_actor_disabled and calls aw_actor_enabled in the engine). */
static unsigned disabled_ref;
static int disabled_stub (unsigned reference)
{
	return reference == disabled_ref;
}
static void disabled_actor (void)
{
	static const float none[2] = {0, 0};
	reset_level ();
	command ("budget", "0");
	disabled_ref = 502;
	aw_actor_disabled = disabled_stub;
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 2 && index_of ("spawn progs/a_mid.mdl") < 0);
	chim_actors_tick ();
	assert (actors_alive () == 2);			/* kept, not spawned, while disabled */
	aw_actor_enabled (999);				/* another reference's Enable: nothing */
	chim_actors_tick ();
	assert (actors_alive () == 2);
	disabled_ref = 0;			/* Enable: on the next tick, no join needed */
	assert (aw_actor_enabled != NULL);
	aw_actor_enabled (502);
	chim_actors_tick ();
	assert (actors_alive () == 3 && index_of ("spawn progs/a_mid.mdl") >= 0);
	chim_actors_join (0, 0, "frame", none);	/* the cell joining again: alive, not spawned twice */
	chim_actors_tick ();
	assert (actors_alive () == 3);
	/* disabled again and its cell left and joined: kept again; the Enable after the leave of its cell does nothing */
	reset_level ();
	disabled_ref = 502;
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 2);
	chim_actors_leave (0, 0);
	disabled_ref = 0;
	aw_actor_enabled (502);
	chim_actors_tick ();
	assert (index_of ("spawn progs/a_mid.mdl") < 0);
	aw_actor_disabled = NULL;
	command ("budget", "1");
	puts ("disabled actor passed");
}

static void warm_order (int on)
{
	static const float none[2] = {0, 0};
	int ticks, spawn;
	reset_level ();
	flush_caches ();
	command ("warm", on ? "1" : "0");
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	if (on)
	{
		/* tick 1: the nearest actor's model only; tick 2: its voice only; tick 3: the spawn, its sounds wait */
		assert (nevents == 1 && !strcmp (events[0], "load model progs/a_near.mdl"));
		chim_actors_tick ();
		assert (nevents == 2 && !strcmp (events[1], "load sound npc/near.wav"));
		chim_actors_tick ();
		assert (nevents == 3 && !strcmp (events[2], "spawn progs/a_near.mdl"));
		assert (!cl.sound_precache[2]);		/* the footstep reaches the client on a later tick */
		chim_actors_tick ();					/* the voice joins the client list (already loaded) */
		assert (nevents == 3 && cl.sound_precache[1] && !cl.sound_precache[2]);
		chim_actors_tick ();
		assert (nevents == 4 && !strcmp (events[3], "load sound step/a_near.mdl.wav") && cl.sound_precache[2]);
	}
	else
	{
		/* one tick: the model, the voice, the spawn and the client's sounds together */
		spawn = index_of ("spawn progs/a_near.mdl");
		assert (spawn > 0 && index_of ("load model progs/a_near.mdl") < spawn &&
			index_of ("load sound npc/near.wav") < spawn && index_of ("load sound step/a_near.mdl.wav") > spawn);
	}
	for (ticks=0 ; ticks<16 ; ticks++)
		chim_actors_tick ();
	assert (actors_alive () == 3 && count ("spawn") == 3 && count ("load model") == 3);
	/* every actor's model was loaded before its spawn, in both modes */
	assert (index_of ("load model progs/a_far_mover.mdl") >= 0 &&
		index_of ("load model progs/a_far_mover.mdl") < index_of ("spawn progs/a_far_mover.mdl"));
	printf ("warm %d order passed\n", on);
}

static void lazy_movers (void)
{
	static const float none[2] = {0, 0};
	int i, worn = 0, plain = 0;
	reset_level ();
	flush_caches ();
	command ("warm", "0");
	chim_actors_join (0, 0, "frame", none);
	for (i=0 ; i<8 ; i++)
		chim_actors_tick ();
	for (i=1 ; i<MAX_MODELS && sv.model_precache[i] ; i++)
	{
		assert (cl.model_precache[i]);
		if (strstr (sv.model_precache[i], "worn_"))
		{
			assert (cl.model_precache[i]->needload);	/* named, not loaded (as CL_ParseServerInfo) */
			worn++;
		}
		else
		{
			assert (!cl.model_precache[i]->needload);
			plain++;
		}
	}
	assert (worn == 1 && plain == 3 && count ("load model progs/worn_") == 0);
	puts ("lazy mover models passed");
}

/* The actor table's cell 0 0 joined at an offset of 2048 units: print every spawned actor's id, placement, yaw,
 * model and instance scale (aw_scale); the Python side checks them against the table's records. */
static void table_entries (void)
{
	static const float east[2] = {2048, 0};
	int i;
	eval_t *v, *s;
	reset_level ();
	command ("table", "1");
	chim_actors_join (0, 0, "frame", east);
	for (i=0 ; i<16 ; i++)
		chim_actors_tick ();
	for (i=2 ; i<sv.num_edicts ; i++)
		if (!ents[i].free && (v = GetEdictFieldValue (&ents[i], "aw_ref")) != NULL)
		{
			s = GetEdictFieldValue (&ents[i], "aw_scale");
			printf ("table ref %.0f at %.3f %.3f %.3f yaw %.3f model %s scale %.4f\n", v->_float, ents[i].v.origin[0],
				ents[i].v.origin[1], ents[i].v.origin[2], ents[i].v.angles[1], pr_strings + ents[i].v.model,
				s && s->_float ? s->_float : 1.0f);
		}
}

/* The levelled references of cells 0 0 and 1 0 rolled with seed SEED: print the picks (key and model or "none") */
static void roll (unsigned seed)
{
	static const float none[2] = {0, 0}, east[2] = {1024, 0};
	char s[16];
	int i, pass;
	eval_t *v;
	reset_level ();
	command ("table", "1");
	snprintf (s, sizeof(s), "%u", seed);
	command ("seed", s);
	for (pass=0 ; pass<2 ; pass++)
	{
		chim_actors_join (0, 0, "frame", none);
		chim_actors_join (1, 0, "frame", east);
		for (i=0 ; i<16 ; i++)
			chim_actors_tick ();
		for (i=2 ; i<sv.num_edicts ; i++)
			if (!ents[i].free && (v = GetEdictFieldValue (&ents[i], "aw_ref")) != NULL &&
				(v->_float == 11 || v->_float == 12 || v->_float == 21 || v->_float == 22))
				printf ("pick pass %d ref %.0f %s\n", pass, v->_float, pr_strings + ents[i].v.model);
		/* both cells leave (released to the change list: the player is far away, nothing keeps them), then join
		 * again: the picks kept in the change list */
		ents[1].v.origin[0] = 100000;
		chim_actors_leave (0, 0);	/* the stub puts every actor in cell 0 0 */
		ents[1].v.origin[0] = 0;
		for (i=2 ; i<sv.num_edicts ; i++)
			if (!ents[i].free && ents[i].v.classname)
				printf ("left alive %s at %.1f %.1f\n", pr_strings + ents[i].v.model, ents[i].v.origin[0], ents[i].v.origin[1]);
		assert (actors_alive () == 0);
	}
}

/* The change list through a save: the frame's actors leave (one killed, one moved), the session's changes are
 * exported (aw_save_changes_export), forgotten (chim actors clear) and imported again (as a load); the frame joining
 * again spawns the living ones where they were left and not the dead one. */
static void save_round_trip (void)
{
	static const float none[2] = {0, 0};
	static aw_changes_t saved;
	int i, n, pass, found = 0;
	eval_t *v;
	reset_level ();
	command ("budget", "0");
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 3);
	for (i=2 ; i<sv.num_edicts ; i++)
		if (!ents[i].free && (v = GetEdictFieldValue (&ents[i], "aw_ref")) != NULL && v->_float == 502)
			ents[i].v.origin[1] = 333;			/* a_mid walked */
	dead_ref = 501;							/* a_near was killed */
	ents[1].v.origin[0] = 100000;
	chim_actors_leave (0, 0);
	assert (parts_cells_out > 0);		/* the leaving cell's recipe table goes with it */
	ents[1].v.origin[0] = 0;
	dead_ref = 0;
	assert (actors_alive () == 0);
	assert (aw_save_changes_export && aw_save_changes_import);
	/* CELL-CHANGES-59 slice 6: the three let go are rows of the world change list (one killed where it fell, one
	 * moved), not entries of the save's own list (only actors alive at the save go there) */
	assert (aw_ledger.actor_count == 3);
	for (i=0 ; i<aw_ledger.actor_count ; i++)
	{
		assert (aw_ledger.actor[i].moved);
		assert (!aw_ledger.actor[i].dead == (aw_ledger.actor[i].key != 501));
	}
	n = aw_save_changes_export (&saved);
	assert (n == 0 && saved.count == 0);
	for (pass=0 ; pass<2 ; pass++)
	{
		/* pass 0: a save of this engine (the list in its sixth form); pass 1: a save made before slice 6, whose
		 * three actor entries are migrated onto the list at the load */
		static aw_ledger_t loaded;
		static unsigned char bytes[65536];
		int k;
		AW_LedgerClear (&loaded);
		if (!pass)
		{
			k = AW_LedgerEncode (&aw_ledger, bytes, sizeof(bytes));
			assert (k > 0 && !memcmp (bytes, "AWL6", 4) && AW_LedgerDecode (bytes, k, &loaded));
			saved.count = 0;
		}
		else
		{
			saved.count = 0;
			for (i=0 ; i<aw_ledger.actor_count ; i++)
			{
				aw_change_t *e = &saved.entry[saved.count++];
				memset (e, 0, sizeof(*e));
				e->key = aw_ledger.actor[i].key;
				e->flags = AW_CHANGE_MOVED | (aw_ledger.actor[i].dead ? AW_CHANGE_DEAD : 0);
				memcpy (e->position, aw_ledger.actor[i].origin, sizeof(e->position));
				e->health = aw_ledger.actor[i].health;
			}
		}
		saved.ledger = &loaded;
		command ("clear", NULL);
		assert (aw_ledger.actor_count == 0);
		aw_save_changes_import (&saved);
		AW_LedgerMove (&aw_ledger, &loaded);		/* as aw_save.c: the save's list is the session's */
		assert (aw_ledger.actor_count == 3);
		chim_actors_join (0, 0, "frame", none);
		chim_actors_tick ();
		/* OUTDOOR-DEAD-BODY-GONE-66: the killed one is back as its body, laid down where it fell (the clock stopped:
		 * its clear delay has not passed) */
		assert (actors_alive () == 3 && on_map (501) && is_laid (501));
		found = 0;
		for (i=2 ; i<sv.num_edicts ; i++)
			if (!ents[i].free && (v = GetEdictFieldValue (&ents[i], "aw_ref")) != NULL)
			{
				if (v->_float == 502)
				{
					assert (fabs (ents[i].v.origin[1] - 333) < 0.01f);
					found++;
				}
			}
		assert (found == 1);
		/* leave again so the next pass starts from the rows alone */
		ents[1].v.origin[0] = 100000;
		chim_actors_leave (0, 0);
		ents[1].v.origin[0] = 0;
		assert (actors_alive () == 0 && aw_ledger.actor_count == 3);
	}
	saved.ledger = NULL;
	command ("budget", "1");
	puts ("save round trip passed");
}

/* A town frame's own residents (spawned by its map, not by a join) in a cell beside the home cell: kept while the
 * home frame is in the window, kept while their own cell's frame is, released when neither is
 * (CHIM-ACTORS-TOWN-RETURN-EMPTY-47: they were released at once as "left the window"). */
static edict_t *map_actor (const char *text)
{
	edict_t *e = ED_Alloc ();
	ED_ParseEdict ((char *)text, e);
	return e;
}
static void home_frame (void)
{
	edict_t *near, *beside;
	int i;
	reset_level ();
	grid_mode = 1;
	nheld = 1;
	held_cells[0][0] = held_cells[0][1] = 0;				/* the window holds the home frame only */
	strcpy (sv.name, "town");
	near = map_actor ("\"classname\" \"aw_npc\" \"model\" \"progs/a_near.mdl\" \"origin\" \"100 0 0\" \"aw_ref\" \"601\" }");
	beside = map_actor ("\"classname\" \"aw_npc\" \"model\" \"progs/a_mid.mdl\" \"origin\" \"3000 0 0\" \"aw_ref\" \"602\" }");
	for (i=0 ; i<30 ; i++)
		chim_actors_tick ();
	assert (!near->free && !beside->free);		/* cell 1 0 is not held, the home frame that spawned it is */
	/* cell 1 0's frame joins; the home frame leaves with the player far away: the home cell's resident goes, the
	 * one standing in the held cell stays */
	nheld = 2;
	held_cells[1][0] = 1;
	held_cells[1][1] = 0;
	ents[1].v.origin[0] = 100000;
	chim_actors_leave (0, 0);
	held_cells[0][0] = 1;
	nheld = 1;
	assert (near->free && !beside->free);
	for (i=0 ; i<30 ; i++)
		chim_actors_tick ();
	assert (!beside->free);
	/* its own cell leaves too: released */
	chim_actors_leave (1, 0);
	nheld = 0;
	assert (beside->free);
	ents[1].v.origin[0] = 0;
	grid_mode = 0;
	sv.name[0] = 0;
	puts ("home frame actors passed");
}

/* A room's levelled creatures (CREATURE-ROOM-LEVELLED-54): an "aw_levelled" entity of the room map (aw_ref, sounds =
 * the list's index) handed over as ED_LoadFromFile does: rolled on every list of the table at levels 1 and 30, the
 * picked creature spawned at the entity's place with its reference; the room loaded again gives the same creature.
 * Prints "room LIST LEVEL REF MODEL|none X Y". */
void (*aw_levelled_entity)(edict_t *ent);
static void room_levelled (void)
{
	int list, level, pass, i;
	reset_level ();
	assert (aw_levelled_entity);
	for (level=1 ; level<=30 ; level+=29)
	{
		aw_character.valid = 1;
		aw_character.level = level;
		command ("clear", NULL);
		for (list=0 ; list<4 ; list++)
		{
			char first[64] = "";
			for (pass=0 ; pass<2 ; pass++)
			{
				edict_t *e = ED_Alloc ();
				eval_t *v = GetEdictFieldValue (e, "aw_ref");
				int before = sv.num_edicts, found = 0;
				char got[64] = "none";
				e->v.classname = NewString ("aw_levelled");
				e->v.origin[0] = 10.0f * list;
				e->v.origin[1] = 7.0f;
				e->v.sounds = list;
				v->_float = 900 + list;
				aw_levelled_entity (e);
				ED_Free (e);
				for (i=2 ; i<sv.num_edicts ; i++)
					if (!ents[i].free && ents[i].v.classname && strcmp (pr_strings + ents[i].v.classname, "aw_levelled") &&
						(v = GetEdictFieldValue (&ents[i], "aw_ref")) != NULL && v->_float == 900 + list)
					{
						snprintf (got, sizeof(got), "%s", pr_strings + ents[i].v.model);
						assert (fabs (ents[i].v.origin[0] - 10.0f * list) < 0.01f && fabs (ents[i].v.origin[1] - 7.0f) < 0.01f);
						ents[i].free = true;		/* the room is left: its creature goes */
						found++;
					}
				assert (found <= 1);
				(void)before;
				if (!pass)
					snprintf (first, sizeof(first), "%s", got);
				else
					assert (!strcmp (first, got));		/* loaded again: the kept pick */
			}
			printf ("room %d %d %d %s\n", list, level, 900 + list, first);
		}
	}
	puts ("room levelled passed");
}

/* ACTOR-DEAD-RESPAWN-INTERIOR-65: the dead stay dead across an area change and a save. A town map's own residents
 * (701 killed in a fight, 702 killed by a script on its actor record only), a room entered and left, the town map
 * spawned again: its first window tick runs inside the player's scene set-up (not spawned yet), which then empties the
 * combat slots; after that both bodies lie dead, 703 lives. The same after a save of the change list and a load. */
static client_t *test_client;
extern int (*aw_actor_dead_record)(unsigned reference);
void AW_ActorsRoomTick (void);
static int record_dead_stub (unsigned reference) {return reference == 702;}
static void town_residents (void)
{
	reset_level ();
	strcpy (sv.name, "town");
	map_actor ("\"classname\" \"aw_npc\" \"model\" \"progs/a_near.mdl\" \"origin\" \"100 0 0\" \"aw_ref\" \"701\" }");
	map_actor ("\"classname\" \"aw_npc\" \"model\" \"progs/a_mid.mdl\" \"origin\" \"200 0 0\" \"aw_ref\" \"702\" }");
	map_actor ("\"classname\" \"aw_npc\" \"model\" \"progs/a_far_mover.mdl\" \"origin\" \"300 0 0\" \"aw_ref\" \"703\" }");
}
static void scene_arrives (void)
{
	int i;
	test_client->spawned = false;		/* AW_SceneSpawn primes the ring: the first window tick of the map */
	chim_actors_tick ();
	combat_scene_reset ();				/* then AW_CombatSceneSpawn empties the slots */
	test_client->spawned = true;
	for (i=0 ; i<4 ; i++)
	{
		chim_actors_tick ();
		AW_ActorsRoomTick ();			/* every server frame (sv_phys.c), outdoors too */
	}
	assert (is_laid (701) && is_laid (702) && !is_laid (703));
}
static void dead_stay_dead (void)
{
	static model_t room;
	static aw_ledger_t loaded;
	static unsigned char bytes[65536];
	static aw_changes_t saved;
	int i, k, pass;
	nlaid = 0;
	command ("clear", NULL);
	town_residents ();
	for (i=0 ; i<3 ; i++)
		chim_actors_tick ();
	dead_ref = 701;							/* killed in a fight */
	chim_actors_tick ();
	dead_ref = 0;
	aw_actor_dead_record = record_dead_stub;	/* 702: SetHealth 0 of a script, no fight */
	for (pass=0 ; pass<2 ; pass++)
	{
		/* a room: its map holds its cell number; its tick clears the town's map memory */
		reset_level ();
		strcpy (sv.name, "room");
		room.entities = "{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"77\"\n}\n";
		sv.worldmodel = &room;
		for (i=0 ; i<4 ; i++)
			AW_ActorsRoomTick ();
		sv.worldmodel = NULL;
		/* back out: the town map spawns its residents again */
		combat_scene_reset ();
		town_residents ();
		scene_arrives ();
	}
	/* a save of the change list and a load of it (the map spawned again by the load) */
	k = AW_LedgerEncode (&aw_ledger, bytes, sizeof(bytes));
	AW_LedgerClear (&loaded);
	assert (k > 0 && AW_LedgerDecode (bytes, k, &loaded));
	saved.count = 0;
	saved.ledger = &loaded;
	command ("clear", NULL);
	assert (aw_ledger.actor_count == 0);
	aw_save_changes_import (&saved);
	AW_LedgerMove (&aw_ledger, &loaded);
	saved.ledger = NULL;
	combat_scene_reset ();
	town_residents ();
	scene_arrives ();
	for (i=0, k=0 ; i<aw_ledger.actor_count ; i++)
		k += aw_ledger.actor[i].dead;
	assert (k == 2);
	aw_actor_dead_record = NULL;
	sv.name[0] = 0;
	puts ("dead stay dead passed");
}

/* ACTOR-RESPAWN-CORPSE-RULES-66: the original's death rules over time (OpenMW 0.51 CellStore::respawn and clearCorpse,
 * Morrowind.esm's fCorpseRespawnDelay 72 and fCorpseClearDelay 72). Three town residents die at game hour 10: 701 an
 * ordinary NPC (no flag), 702 flagged Respawn, 703 Persistent. At hour 81 (71 h later) the town is entered again: all
 * three lie dead. At hour 83 (73 h): 701's body is cleared away and it stays dead for good (its row DEAD and CLEARED),
 * 702 is back alive as the game data has it, 703's body still lies there. The same after a save and a load, and still
 * after another 10,000 hours (701 never comes back). */
extern uint32_t (*aw_actors_ref_flags)(uint32_t key, aw_ledger_respawn_t *rule);
extern int (*aw_actors_forget)(uint32_t reference);
static int forgot_702;
static uint32_t ref_flags_stub (uint32_t key, aw_ledger_respawn_t *rule)
{
	aw_ledger_respawn_t r = AW_LEDGER_RESPAWN_DEFAULT;
	if (rule)
		*rule = r;
	return key == 702 ? AW_REFS_RESPAWN : key == 703 ? AW_REFS_PERSISTENT : 0;
}
static int forget_stub (uint32_t reference) {if (reference == 702) forgot_702 = 1; return 1;}
static int record_dead_three (unsigned reference) {return reference == 701 || reference == 703 || (reference == 702 && !forgot_702);}
static int on_map (float ref)
{
	int i;
	for (i=2 ; i<sv.num_edicts ; i++)
	{
		eval_t *v = GetEdictFieldValue (&ents[i], "aw_ref");
		if (!ents[i].free && v && v->_float == ref)
			return 1;
	}
	return 0;
}
static void town_again (void)
{
	static model_t room;
	int i;
	reset_level ();
	strcpy (sv.name, "room");
	room.entities = "{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"77\"\n}\n";
	sv.worldmodel = &room;
	for (i=0 ; i<4 ; i++)
		AW_ActorsRoomTick ();
	sv.worldmodel = NULL;
	combat_scene_reset ();
	town_residents ();
	test_client->spawned = false;
	chim_actors_tick ();
	combat_scene_reset ();
	test_client->spawned = true;
	for (i=0 ; i<4 ; i++)
	{
		chim_actors_tick ();
		AW_ActorsRoomTick ();
	}
}
static void corpse_rules (void)
{
	static aw_ledger_t loaded;
	static unsigned char bytes[65536];
	static aw_changes_t saved;
	{
	aw_ledger_actor_t *a;
	int k;
	nlaid = 0;
	command ("clear", NULL);
	aw_actors_ref_flags = ref_flags_stub;
	aw_actors_forget = forget_stub;
	aw_actor_dead_record = record_dead_three;
	test_hours = 10;
	town_residents ();
	for (k=0 ; k<3 ; k++)
		chim_actors_tick ();
	town_again ();
	assert ((a = AW_LedgerActor (&aw_ledger, 701, 0)) && a->dead && a->died == 10 && !a->cleared);
	test_hours = 81;					/* 71 h after: nothing yet */
	town_again ();
	assert (is_laid (701) && is_laid (702) && is_laid (703) && !forgot_702);
	test_hours = 83;					/* 73 h after */
	town_again ();
	assert ((a = AW_LedgerActor (&aw_ledger, 701, 0)) && a->dead && a->cleared && !on_map (701) && !is_laid (701));
	assert (forgot_702 && on_map (702) && !is_laid (702));		/* back alive */
	assert ((a = AW_LedgerActor (&aw_ledger, 703, 0)) && a->dead && !a->cleared && is_laid (703));
	/* a save and a load: the cleared body stays gone, the persistent one lies there */
	k = AW_LedgerEncode (&aw_ledger, bytes, sizeof(bytes));
	AW_LedgerClear (&loaded);
	assert (k > 0 && !memcmp (bytes, "AWL7", 4) && AW_LedgerDecode (bytes, k, &loaded));
	saved.count = 0;
	saved.ledger = &loaded;
	command ("clear", NULL);
	aw_save_changes_import (&saved);
	AW_LedgerMove (&aw_ledger, &loaded);
	saved.ledger = NULL;
	test_hours = 10083;					/* long after: the ordinary NPC never comes back */
	town_again ();
	assert ((a = AW_LedgerActor (&aw_ledger, 701, 0)) && a->dead && a->cleared && !on_map (701));
	assert (on_map (702) && is_laid (703));
	}
	aw_actors_ref_flags = NULL;
	aw_actors_forget = NULL;
	aw_actor_dead_record = NULL;
	test_hours = 0;
	sv.name[0] = 0;
	puts ("corpse rules passed");
}

/* OUTDOOR-DEAD-BODY-GONE-66: an outdoor cell's actor (a window join, not a map's own) killed at hour 10 lies there as
 * its body on every later join until its clear delay (fCorpseClearDelay 72, OpenMW 0.51 cellstore.cpp clearCorpse):
 * at hour 50 the body is laid down again (as a saved death: no second essential message); "chim actors corpses 0" (the
 * method before) does not spawn it; at hour 83 the body is cleared away and stays gone. */
static void join_frame_again (void)
{
	static const float none[2] = {0, 0};
	ents[1].v.origin[0] = 100000;
	chim_actors_leave (0, 0);
	ents[1].v.origin[0] = 0;
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
}
static void outdoor_corpse (void)
{
	static const float none[2] = {0, 0};
	aw_ledger_actor_t *a;
	int lays;
	reset_level ();
	nlaid = 0;
	command ("clear", NULL);
	command ("budget", "0");
	aw_actors_ref_flags = ref_flags_stub;		/* 501: no Respawn flag, not Persistent */
	test_hours = 10;
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 3 && on_map (501));
	dead_ref = 501;					/* killed in a fight */
	ents[1].v.origin[0] = 100000;
	chim_actors_leave (0, 0);
	ents[1].v.origin[0] = 0;
	dead_ref = 0;
	assert ((a = AW_LedgerActor (&aw_ledger, 501, 0)) && a->dead && a->died == 10 && !a->cleared);
	test_hours = 50;				/* 40 h later: the body lies there, lootable */
	lays = nlay_saved;
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 3 && on_map (501) && is_laid (501) && nlay_saved == lays + 1);
	command ("corpses", "0");			/* the older method: not spawned */
	join_frame_again ();
	assert (actors_alive () == 2 && !on_map (501));
	command ("corpses", "1");
	join_frame_again ();
	assert (on_map (501));
	test_hours = 83;				/* 73 h after: cleared away, dead for good */
	join_frame_again ();
	assert (actors_alive () == 2 && !on_map (501));
	assert ((a = AW_LedgerActor (&aw_ledger, 501, 0)) && a->dead && a->cleared);
	test_hours = 10083;
	join_frame_again ();
	assert (!on_map (501));
	aw_actors_ref_flags = NULL;
	test_hours = 0;
	command ("budget", "1");
	puts ("outdoor corpse passed");
}

/* JOURNEY-STEP7-FIGHTER-NEAREST-66: "chim actors summon" copies the nearest resident; "chim actors summon REF" copies the
 * living resident of that reference (the journey's step 7 names the Seyda Neen guard), and says so when nobody of that
 * reference lives here (a dead one counts as nobody). The copy stands at the player's feet with its own reference. */
static edict_t *copy_of (float ref)
{
	int i;
	for (i=2 ; i<sv.num_edicts ; i++)
	{
		eval_t *v = GetEdictFieldValue (&ents[i], "aw_ref");
		if (!ents[i].free && v && v->_float == ref)
			return &ents[i];
	}
	return NULL;
}
static void summon_by_reference (void)
{
	edict_t *c, *far_one, *mid;
	programs.entityfields = sizeof(entvars_t) / 4;		/* the copy takes the source's fields as the engine's progs say */
	reset_level ();
	nlaid = 0;
	dead_ref = 0;
	command ("clear", NULL);
	town_residents ();
	chim_actors_tick ();
	assert (on_map (701) && on_map (702) && on_map (703));
	far_one = copy_of (703);
	mid = copy_of (702);
	ents[1].v.origin[0] = 0;
	/* without a reference: the nearest resident (701, at 100 east) */
	command ("summon", NULL);
	assert ((c = copy_of (900500)) != NULL && c->v.model == copy_of (701)->v.model);
	/* with one: that resident, though it is the farthest (703, at 300 east) */
	command ("summon", "703");
	assert ((c = copy_of (900501)) != NULL && c->v.model == far_one->v.model && c->v.model != mid->v.model);
	assert (c->v.origin[0] == ents[1].v.origin[0] && c->v.origin[1] == ents[1].v.origin[1]);
	/* the reference of nobody here: no copy, the count of copies stays */
	command ("summon", "999");
	assert (!copy_of (900502));
	/* a dead resident is nobody */
	dead_ref = 702;
	command ("summon", "702");
	assert (!copy_of (900502));
	dead_ref = 0;
	command ("summon", "702");
	assert ((c = copy_of (900502)) != NULL && c->v.model == mid->v.model);
	puts ("summon by reference passed");
}

/* COMBAT-PLAYGROUND-CREATURE-HUMANOID-61: a creature record ID's world model from its table base (any case); a
 * creature with no model in this build, an unknown id and a buffer too small for the path give none */
static void base_model (void)
{
	char model[64];
	assert (AW_ActorsBaseModel ("CRAB", model, sizeof(model)) && !strcmp (model, "progs/c_crab.mdl"));
	assert (AW_ActorsBaseModel ("crab", model, sizeof(model)) && !strcmp (model, "progs/c_crab.mdl"));
	assert (!AW_ActorsBaseModel ("racer", model, sizeof(model)) && !model[0]);
	assert (!AW_ActorsBaseModel ("nobody", model, sizeof(model)) && !model[0]);
	assert (!AW_ActorsBaseModel ("crab", model, 8) && !model[0]);
	assert (!AW_ActorsBaseModel ("", model, sizeof(model)));
	printf ("base model %s\n", AW_ActorsBaseModel ("Crab", model, sizeof(model)) ? model : "none");
	puts ("base model passed");
}

int main (int argc, char **argv)
{
	static client_t client;
	setvbuf (stdout, NULL, _IONBF, 0);		/* every line reaches the test even when a check aborts */
	assert (argc >= 4);
	table_path = argv[2];
	frame_path = argv[3];
	frame2_path = argc > 5 ? argv[5] : argv[3];
	sv.active = true;
	sv.edicts = ents;
	sv.num_edicts = 2;
	sv.state = ss_active;
	svs.clients = &client;
	client.active = true;
	client.spawned = true;		/* in play (the change list waits for it, ACTOR-DEAD-RESPAWN-INTERIOR-65) */
	svs.maxclients = 1;
	test_client = &client;
	client.edict = &ents[1];
	ents[1].v.origin[0] = 0;
	ents[1].v.origin[1] = 0;
	AW_ActorsInit ();
	if (!strcmp (argv[1], "queue"))
		queue_and_budget ();
	else if (!strcmp (argv[1], "warm"))
	{
		warm_order (0);
		warm_order (1);
	}
	else if (!strcmp (argv[1], "lazy"))
		lazy_movers ();
	else if (!strcmp (argv[1], "table"))
		table_entries ();
	else if (!strcmp (argv[1], "home"))
		home_frame ();
	else if (!strcmp (argv[1], "save"))
		save_round_trip ();
	else if (!strcmp (argv[1], "disabled"))
		disabled_actor ();
	else if (!strcmp (argv[1], "roll"))
		roll ((unsigned)atoi (argv[4]));
	else if (!strcmp (argv[1], "room"))
		room_levelled ();
	else if (!strcmp (argv[1], "basemodel"))
		base_model ();
	else if (!strcmp (argv[1], "deadstay"))
		dead_stay_dead ();
	else if (!strcmp (argv[1], "corpse"))
		corpse_rules ();
	else if (!strcmp (argv[1], "outdoorcorpse"))
		outdoor_corpse ();
	else if (!strcmp (argv[1], "summonref"))
		summon_by_reference ();
	else
		return 2;
	return 0;
}
