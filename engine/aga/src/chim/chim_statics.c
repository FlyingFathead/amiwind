/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM streamed statics: a frame map's aw_static and aw_flora entities tagged
 * by the builder with "_chim_chunk" (the chunk that holds the origin) and
 * "_chim_box" (the drawn box) are not spawned at map load. They are kept as a
 * list and become static entities while their chunk is active, their models
 * decoded into the zone (sprites) or held in Quake's cache (alias models).
 *
 * Quake mechanisms reused: the entity text parser (COM_Parse, as
 * ED_ParseEdict); PF_makestatic's rules for the two classes (aw_flora: a
 * sprite with a finite positive aw_scale; aw_static: scale 1) and the client
 * static entity it makes (CL_ParseStatic: model, frame, skin, colormap,
 * origin, angles, efrags); the sprite loader (Mod_LoadSpriteInto, the Hunk
 * loader with the zone as its allocator); Mod_ForName for alias models,
 * whose data lives in the cache as every actor's does.
 *
 * Why: a frame map that spawns every static of its town loads all their
 * sprite models into the Hunk at once (Seyda Neen: 229 statics, about 0.95
 * MB), more than the whole-map Hunk rule leaves (CHIM-SEYDA-HUNK-GAP-33).
 * Each model is decoded once, shared by name and locked while an active
 * chunk places it; unlocked it stays in the zone as cache.
 */
#include "quakedef.h"
#include "r_local.h"
#include "chim_local.h"

int Mod_LoadSpriteInto (model_t *mod, void *(*alloc)(void *context, int size), void *context);

#define CHIM_MAX_STATICS		2048	/* streamed statics in one frame map */
#define CHIM_STATIC_MODEL_BIT	0x80000000u	/* in a chunk's model need: a static's model */

typedef struct
{
	entity_t	ent;			/* first: ChimStatics_Forget compares pointers */
	vec3_t		mins, maxs;		/* the drawn box, "_chim_box" (frame-local) */
	float		scale;			/* aw_flora: aw_scale; aw_static: 1 (PF_makestatic) */
	short		model;			/* row in the model table */
	short		chunk;			/* the frame's chunk index, "_chim_chunk" */
	short		leaves;			/* efrags while linked */
	unsigned char	frame, skin, flora, placed;	/* placed: its model is set (chunk active) */
} chim_static_t;

typedef struct
{
	char		name[MAX_QPATH];
	chim_user_t	user;			/* a sprite: its zone block (model_t, then the sprite) */
	model_t		*alias;			/* an alias model: Quake's (Mod_ForName, data in the cache) */
	int			sprite;			/* 1: .spr (zone), 0: alias */
	int			bytes;			/* file bytes, for the prefetch room check */
	int			refs;			/* placed statics using it */
	int			bad;			/* missing or not loadable: never asked again this map */
} chim_smodel_t;

typedef struct
{
	chim_static_t	*list;
	chim_smodel_t	*models;
	short			*order;			/* statics by chunk */
	int				*first;			/* per chunk: first row in order, then count in first[count+1] */
	int				capacity, count, nmodels, sorted, chunks;
	chim_user_t		table;			/* the zone block holding all of the above */
	unsigned long	sprite_loads, alias_loads, refused, linked_peak;
	int				linked, efrags;
	model_t			*link_world;
} chim_statics_t;

static chim_statics_t	st;

int ChimStatics_Count (void) { return st.count; }

/* The i-th streamed static's entity (dbg and the host tests). */
entity_t *ChimStatics_Entity (int i)
{
	return i >= 0 && i < st.count ? &st.list[i].ent : NULL;
}

/* ---------------------------------------------------------------- the list */

/* The frame map states how many statics it streams ("_chim_streamed_statics");
 * room for them and their models is taken from the zone, locked for the map. */
void ChimStatics_Begin (int stated, int chunks)
{
	int bytes;
	memset (&st, 0, sizeof(st));
	if (stated <= 0 || chunks <= 0)
		return;
	if (stated > CHIM_MAX_STATICS)
	{
		Con_Printf ("CHIM: %ld streamed statics stated, %ld at most; the rest spawn as usual\n",
			(long)stated, (long)CHIM_MAX_STATICS);
		stated = CHIM_MAX_STATICS;
	}
	bytes = stated * (int)(sizeof(chim_static_t) + sizeof(chim_smodel_t) + sizeof(short)) +
		(chunks + 2) * (int)sizeof(int) + 64;
	if (!ChimZone_Alloc (&st.table, bytes, CHIM_KIND_STATIC, 0xffffffffu))
	{
		Con_Printf ("CHIM: no room for %ld streamed statics (%ld bytes); they spawn as usual\n", (long)stated, (long)bytes);
		return;
	}
	ChimZone_Lock (st.table.data);
	memset (st.table.data, 0, bytes);
	st.list = (chim_static_t *)st.table.data;
	st.models = (chim_smodel_t *)(st.list + stated);
	st.order = (short *)(st.models + stated);
	st.first = (int *)(((size_t)(st.order + stated) + 7) & ~(size_t)7);
	st.capacity = stated;
	st.chunks = chunks;
}

void ChimStatics_End (void)
{
	int i;
	for (i=0 ; i<st.nmodels ; i++)
	{
		if (st.models[i].user.data)
		{
			while (ChimZone_Locks (st.models[i].user.data) > 0)
				ChimZone_Unlock (st.models[i].user.data);
			ChimZone_Free (&st.models[i].user);
		}
	}
	if (st.table.data)
	{
		ChimZone_Unlock (st.table.data);
		ChimZone_Free (&st.table);
	}
	memset (&st, 0, sizeof(st));
}

static int ModelRow (const char *name)
{
	int i, n;
	for (i=0 ; i<st.nmodels ; i++)
		if (!strcmp (st.models[i].name, name))
			return i;
	if (st.nmodels >= st.capacity)
		return -1;
	n = (int)strlen (name);
	memset (&st.models[i], 0, sizeof(st.models[i]));
	strcpy (st.models[i].name, name);
	st.models[i].sprite = n > 4 && !Q_strcasecmp ((char *)name + n - 4, ".spr");
	st.nmodels++;
	return i;
}

static int Vector3 (const char *text, vec3_t out)
{
	return Q_sscanf (text, "%f %f %f", &out[0], &out[1], &out[2]) == 3 &&
		isfinite (out[0]) && isfinite (out[1]) && isfinite (out[2]);
}

/* ED_LoadFromFile, for every entity after worldspawn (*data just past its
 * opening brace): a tagged aw_static or aw_flora is taken into the list and
 * *data moves past its closing brace; anything else is left as it was (0). */
int ChimStatics_Capture (char **data)
{
	char *p = *data, key[64], classname[32], model[MAX_QPATH];
	vec3_t origin, angles, box[2];
	float scale = 1;
	int frame = 0, skin = 0, chunk = -1, has_box = 0, has_origin = 0, tagged = 0, row;
	chim_static_t *s;

	if (!st.capacity)
		return 0;
	classname[0] = model[0] = 0;
	VectorCopy (vec3_origin, origin);
	VectorCopy (vec3_origin, angles);
	while (1)
	{
		p = COM_Parse (p);
		if (!p)
			return 0;		/* ED_LoadFromFile says what is wrong */
		if (com_token[0] == '}')
			break;
		Q_strncpy (key, com_token, sizeof(key) - 1);
		key[sizeof(key)-1] = 0;
		p = COM_Parse (p);
		if (!p || com_token[0] == '}')
			return 0;
		if (!strcmp (key, "classname"))
		{
			Q_strncpy (classname, com_token, sizeof(classname) - 1);
			classname[sizeof(classname)-1] = 0;
		}
		else if (!strcmp (key, "model"))
		{
			Q_strncpy (model, com_token, sizeof(model) - 1);
			model[sizeof(model)-1] = 0;
		}
		else if (!strcmp (key, "origin"))
			has_origin = Vector3 (com_token, origin);
		else if (!strcmp (key, "angles"))
			Vector3 (com_token, angles);
		else if (!strcmp (key, "angle"))
		{
			angles[1] = (float)Q_atof (com_token);
			if (!isfinite (angles[1]))
				angles[1] = 0;
		}
		else if (!strcmp (key, "frame"))
			frame = Q_atoi (com_token);
		else if (!strcmp (key, "skin"))
			skin = Q_atoi (com_token);
		else if (!strcmp (key, "aw_scale"))
			scale = (float)Q_atof (com_token);
		else if (!strcmp (key, "_chim_chunk"))
		{
			chunk = Q_atoi (com_token);
			tagged = 1;
		}
		else if (!strcmp (key, "_chim_box"))
			has_box = Q_sscanf (com_token, "%f %f %f %f %f %f", &box[0][0], &box[0][1], &box[0][2],
				&box[1][0], &box[1][1], &box[1][2]) == 6;
	}
	if (!tagged)
		return 0;
	/* Only the two classes whose spawn is a plain makestatic (world.qc);
	 * anything else tagged is the builder's error and spawns as usual. */
	if ((strcmp (classname, "aw_static") && strcmp (classname, "aw_flora")) || !model[0] || !has_origin ||
		!has_box || chunk < 0 || chunk >= st.chunks || st.count >= st.capacity || frame < 0 || frame > 255 ||
		skin < 0 || skin > 255)
	{
		st.refused++;
		if (st.refused == 1)
			Con_Printf ("CHIM: a tagged %s (%s) cannot stream: spawned as usual\n", classname[0] ? classname : "entity", model);
		return 0;
	}
	if (!strcmp (classname, "aw_flora"))
	{
		/* PF_makestatic and CL_ParseStatic: a sprite, finite positive scale. */
		if (!isfinite (scale) || scale <= 0)
			Host_Error ("aw_flora requires finite positive aw_scale");
	}
	else
		scale = 1;
	if ((row = ModelRow (model)) < 0)
		return 0;
	if (!strcmp (classname, "aw_flora") && !st.models[row].sprite)
		Host_Error ("Invalid aw_flora static sprite scale");
	s = &st.list[st.count++];
	memset (s, 0, sizeof(*s));
	VectorCopy (origin, s->ent.origin);
	VectorCopy (angles, s->ent.angles);
	VectorCopy (box[0], s->mins);
	VectorCopy (box[1], s->maxs);
	s->scale = scale;
	s->model = (short)row;
	s->chunk = (short)chunk;
	s->frame = (unsigned char)frame;
	s->skin = (unsigned char)skin;
	s->flora = !strcmp (classname, "aw_flora");
	st.sorted = 0;
	*data = p;
	return 1;
}

/* Statics by chunk (counting sort, once after the map's entities). */
static void Sort (void)
{
	int i, c;
	if (st.sorted)
		return;
	memset (st.first, 0, (st.chunks + 2) * sizeof(int));
	for (i=0 ; i<st.count ; i++)
		st.first[st.list[i].chunk + 1]++;
	for (c=0 ; c<st.chunks ; c++)
		st.first[c+1] += st.first[c];
	for (i=0 ; i<st.count ; i++)
		st.order[st.first[st.list[i].chunk]++] = (short)i;
	for (c=st.chunks ; c>0 ; c--)
		st.first[c] = st.first[c-1];
	st.first[0] = 0;
	st.sorted = 1;
}

#define FOR_CHUNK(index, k, s) \
	for (Sort (), k = st.first[index]; k < st.first[(index)+1] && ((s) = &st.list[st.order[k]]) != NULL; k++)

/* ---------------------------------------------------------------- models */

static model_t *Resident (int m)
{
	chim_smodel_t *sm = &st.models[m];
	return sm->sprite ? (sm->user.data ? (model_t *)sm->user.data : NULL) : sm->alias;
}

/* The first model a chunk's statics still need: CHIM_STATIC_MODEL_BIT | row,
 * or 0 when all are resident (or cannot be loaded). */
unsigned ChimStatics_Missing (int index)
{
	int k;
	chim_static_t *s;
	if (!st.count || index < 0 || index >= st.chunks)
		return 0;
	FOR_CHUNK (index, k, s)
		if (!st.models[s->model].bad && !Resident (s->model))
			return CHIM_STATIC_MODEL_BIT | (unsigned)s->model;
	return 0;
}

int ChimStatics_IsStatic (unsigned model)
{
	return (model & CHIM_STATIC_MODEL_BIT) != 0;
}

const char *ChimStatics_Name (unsigned model)
{
	model &= ~CHIM_STATIC_MODEL_BIT;
	return (int)model < st.nmodels ? st.models[model].name : "?";
}

static int FileBytes (chim_smodel_t *sm)
{
	FILE *f = NULL;
	int n;
	if (sm->bytes)
		return sm->bytes;
	n = COM_FOpenFile (sm->name, &f);
	if (f)
		fclose (f);
	sm->bytes = f && n > 0 ? n : 0;
	return sm->bytes;
}

/* What a model's load takes from the zone at most (prefetch room). */
long ChimStatics_Bytes (unsigned model)
{
	chim_smodel_t *sm;
	model &= ~CHIM_STATIC_MODEL_BIT;
	if ((int)model >= st.nmodels)
		return 0;
	sm = &st.models[model];
	return sm->sprite ? (long)FileBytes (sm) * (r_pixbytes + 2) + 1024 : 0;
}

/* The sprite loader's allocator: bump allocation in the block, 8-aligned. */
typedef struct
{
	byte	*base;
	int		size, used;
} chim_bump_t;

static void *Bump (void *context, int size)
{
	chim_bump_t *b = context;
	int at = (b->used + 7) & ~7;
	if (size < 0 || at > b->size - size)
		return NULL;
	b->used = at + size;
	memset (b->base + at, 0, size);
	return b->base + at;
}

/* Load one static model: a sprite decodes into a zone block (sized for its
 * file, trimmed afterwards), an alias model goes through Mod_ForName (its
 * data in Quake's cache). 1 resident, -1 failed (no room: the caller makes
 * room or waits; bad data: never asked again this map). */
int ChimStatics_Step (unsigned model, long *budget)
{
	chim_smodel_t *sm;
	chim_bump_t bump;
	model_t *m;
	int bound, bytes;

	model &= ~CHIM_STATIC_MODEL_BIT;
	if ((int)model >= st.nmodels)
		return -1;
	sm = &st.models[model];
	if (Resident (model))
		return 1;
	bytes = FileBytes (sm);
	if (!bytes)
	{
		sm->bad = 1;
		Con_Printf ("CHIM: streamed static model %s not found\n", sm->name);
		return -1;
	}
	*budget -= bytes;
	if (!sm->sprite)
	{
		if (!(sm->alias = Mod_ForName (sm->name, false)) || sm->alias->type != mod_alias)
		{
			sm->alias = NULL;
			sm->bad = 1;
			Con_Printf ("CHIM: streamed static model %s is not an alias model\n", sm->name);
			return -1;
		}
		st.alias_loads++;
		return 1;
	}
	bound = (int)ChimStatics_Bytes (model) + (int)sizeof(model_t);
	if (!(m = ChimZone_Alloc (&sm->user, bound, CHIM_KIND_STATIC, model)))
		return -1;
	ChimZone_Lock (m);
	memset (m, 0, sizeof(*m));
	Q_strncpy (m->name, sm->name, sizeof(m->name) - 1);
	bump.base = (byte *)(m + 1);
	bump.size = bound - (int)sizeof(model_t);
	bump.used = 0;
	if (!Mod_LoadSpriteInto (m, Bump, &bump))
	{
		ChimZone_Unlock (m);
		ChimZone_Free (&sm->user);
		sm->bad = 1;
		Con_Printf ("CHIM: streamed static model %s is not a sprite\n", sm->name);
		return -1;
	}
	ChimZone_Trim (m, (int)sizeof(model_t) + bump.used);
	ChimZone_Unlock (m);
	st.sprite_loads++;
	return 1;
}

/* ---------------------------------------------------------------- chunks */

static void Use (int m, int on)
{
	chim_smodel_t *sm = &st.models[m];
	if (!sm->sprite)
	{
		sm->refs += on ? 1 : -1;
		return;
	}
	if (on)
	{
		if (!sm->refs++)
			ChimZone_Lock (sm->user.data);
		ChimZone_Touch (sm->user.data);
	}
	else if (!--sm->refs && sm->user.data)
		ChimZone_Unlock (sm->user.data);
}

static void Unplace (chim_static_t *s)
{
	if (s->leaves)
	{
		st.efrags -= s->leaves;
		st.linked--;
		if (s->ent.efrag && st.link_world && cl.worldmodel == st.link_world && cls.signon == SIGNONS)
			ChimGraft_RemoveEfrags (&s->ent);
	}
	s->ent.efrag = NULL;
	s->leaves = 0;
	if (s->placed)
	{
		Use (s->model, 0);
		s->placed = 0;
		s->ent.model = NULL;
	}
}

/* CL_ParseStatic's entity, once its model is resident. */
static int Place (chim_static_t *s)
{
	model_t *m = Resident (s->model);
	if (!m)
		return 0;
	if (s->flora && (m->type != mod_sprite || !isfinite (s->scale * m->radius)))
		Host_Error ("Invalid aw_flora static sprite scale");
	s->ent.model = m;
	s->ent.frame = s->frame;
	s->ent.colormap = vid.colormap;
	s->ent.skinnum = s->skin;
	s->ent.effects = 0;
	s->ent.aw_sprite_scale = s->scale;
	s->ent.efrag = NULL;
	s->leaves = 0;
	s->placed = 1;
	Use (s->model, 1);
	return 1;
}

/* A chunk became active: its statics with resident models are placed.
 * Returns how many still wait for their model (a partial chunk). */
int ChimStatics_Activate (int index)
{
	int k, missing = 0;
	chim_static_t *s;
	if (!st.count || index < 0 || index >= st.chunks)
		return 0;
	FOR_CHUNK (index, k, s)
		if (!s->placed && !Place (s) && !st.models[s->model].bad)
			missing++;
	return missing;
}

void ChimStatics_Deactivate (int index)
{
	int k;
	chim_static_t *s;
	if (!st.count || index < 0 || index >= st.chunks)
		return;
	FOR_CHUNK (index, k, s)
		Unplace (s);
}

/* ChimChunks_Link: every placed static of an active, grafted chunk is in the
 * leaves its drawn box touches (the frame world's own leaves). */
int ChimStatics_Link (int (*add)(entity_t *ent, const vec3_t mins, const vec3_t maxs), int (*linkable)(int index))
{
	int i;
	chim_static_t *s;
	if (!st.count || !cl.worldmodel)
		return 0;
	if (cl.worldmodel != st.link_world)
	{
		/* A new client map reset the efrag pool. */
		for (i=0 ; i<st.count ; i++)
			st.list[i].ent.efrag = NULL, st.list[i].leaves = 0;
		st.linked = st.efrags = 0;
		st.link_world = cl.worldmodel;
	}
	for (i=0 ; i<st.count ; i++)
	{
		s = &st.list[i];
		if (!s->placed || s->leaves || !linkable (s->chunk))
			continue;
		s->leaves = (short)add (&s->ent, s->mins, s->maxs);
		if (s->leaves)
		{
			st.linked++;
			st.efrags += s->leaves;
		}
	}
	if ((unsigned long)st.linked > st.linked_peak)
		st.linked_peak = st.linked;
	return st.linked;
}

/* The client's efrag pool was reset (a map change): links are forgotten,
 * never unlinked from leaves that no longer exist. */
void ChimStatics_PoolReset (void)
{
	int i;
	for (i=0 ; i<st.count ; i++)
		st.list[i].ent.efrag = NULL, st.list[i].leaves = 0;
	st.linked = st.efrags = 0;
	st.link_world = NULL;
}

/* The frame world took an entity out of its leaves: when it is a static,
 * ChimStatics_Link links it again. */
int ChimStatics_Forget (entity_t *ent)
{
	chim_static_t *s = (chim_static_t *)ent;
	if (!st.count || s < st.list || s >= st.list + st.count)
		return 0;
	if (s->leaves)
	{
		st.efrags -= s->leaves;
		st.linked--;
		s->leaves = 0;
	}
	return 1;
}

/* Before the world's leaves are replaced (ChimChunks_ReleaseEfrags). */
void ChimStatics_ReleaseEfrags (void)
{
	int i;
	for (i=0 ; i<st.count ; i++)
		if (st.list[i].leaves)
		{
			ChimGraft_ReleaseEfrags (&st.list[i].ent);
			st.list[i].leaves = 0;
		}
	st.linked = st.efrags = 0;
}

void ChimStatics_Report (void)
{
	int i, resident = 0, bytes = 0, bad = 0;
	if (!st.capacity)
		return;
	for (i=0 ; i<st.nmodels ; i++)
	{
		if (st.models[i].bad)
			bad++;
		if (st.models[i].user.data)
		{
			resident++;
			bytes += ChimZone_Size (st.models[i].user.data);
		}
		else if (st.models[i].alias)
			resident++;
	}
	Con_Printf ("streamed statics: %ld of %ld stated, %ld linked (most %lu), %ld efrags; models %ld (%ld resident, %ld KiB of sprites in the zone, %ld bad); loads %lu sprites, %lu alias; refused %lu\n",
		(long)st.count, (long)st.capacity, (long)st.linked, st.linked_peak, (long)st.efrags,
		(long)st.nmodels, (long)resident, (long)(bytes/1024), (long)bad, st.sprite_loads, st.alias_loads, st.refused);
}

void ChimStatics_Counts (int *count, int *linked, int *efrags, int *models, int *sprite_bytes)
{
	int i;
	*count = st.count;
	*linked = st.linked;
	*efrags = st.efrags;
	*models = st.nmodels;
	*sprite_bytes = 0;
	for (i=0 ; i<st.nmodels ; i++)
		if (st.models[i].user.data)
			*sprite_bytes += ChimZone_Size (st.models[i].user.data);
}
