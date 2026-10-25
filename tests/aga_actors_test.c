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
int32_t AW_StateGet (const aw_state_t *state, int kind, const char *id) {return 0;}
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
int AW_CombatSlotState (edict_t *e, float *health)
{
	eval_t *v = GetEdictFieldValue (e, "aw_ref");
	return dead_ref && v && v->_float == dead_ref ? 2 : 0;
}
int AW_CombatTestEngage (edict_t *e, int dead) {return 0;}
int AW_CombatSetHealth (edict_t *e, float health) {return 0;}
void AW_CombatForget (edict_t *e) {}
int ChimChunks_OriginCell (int *cx, int *cy) {*cx = *cy = 0; return 1;}
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
	puts ("queue and budget passed");
}

/* Object state (v0.0.51): a script's Disable keeps an actor of the window from spawning; after Enable it comes
 * with its cell's next join (aw_mwhost.c sets aw_actor_disabled in the engine). */
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
	disabled_ref = 0;			/* Enable */
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 3 && index_of ("spawn progs/a_mid.mdl") >= 0);
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
	int i, n, found = 0;
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
	ents[1].v.origin[0] = 0;
	dead_ref = 0;
	assert (actors_alive () == 0);
	assert (aw_save_changes_export && aw_save_changes_import);
	n = aw_save_changes_export (&saved);
	assert (n == 3 && saved.count == 3);
	for (i=0 ; i<saved.count ; i++)
	{
		assert (saved.entry[i].flags & AW_CHANGE_MOVED);
		assert (!(saved.entry[i].flags & AW_CHANGE_DEAD) == (saved.entry[i].key != 501));
	}
	command ("clear", NULL);
	aw_save_changes_import (&saved);
	chim_actors_join (0, 0, "frame", none);
	chim_actors_tick ();
	assert (actors_alive () == 2);
	for (i=2 ; i<sv.num_edicts ; i++)
		if (!ents[i].free && (v = GetEdictFieldValue (&ents[i], "aw_ref")) != NULL)
		{
			assert (v->_float != 501);
			if (v->_float == 502)
			{
				assert (fabs (ents[i].v.origin[1] - 333) < 0.01f);
				found++;
			}
		}
	assert (found == 1);
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
	else
		return 2;
	return 0;
}
