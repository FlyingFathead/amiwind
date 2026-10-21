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
 *
 * Type 1 crossings (a window of frames, chim_chunks.c): one list per window
 * slot. The map's own frame (slot 0 at the start) takes its statics from the
 * map's entity text (ED_LoadFromFile, ChimStatics_Capture); a frame that joins
 * the window later has its frame map's entity text read for them
 * (ChimStatics_SlotJoin), placed at the frame's offset. Without a window there
 * is only list 0, as before.
 */
#include "quakedef.h"
#include "r_local.h"
#include "chim_local.h"
#include "aw_mappath.h"

int Mod_LoadSpriteInto (model_t *mod, void *(*alloc)(void *context, int size), void *context);

#define CHIM_MAX_STATICS		2048	/* streamed statics in one frame map */
#define CHIM_STATIC_MODEL_BIT	0x80000000u	/* in a chunk's model need: a static's model */
#define CHIM_STATIC_SLOT_SHIFT	24			/* ... its window slot, then its row in that slot's table */
#define CHIM_STATIC_ROW_MASK	0x00ffffffu

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
	int				base;			/* the slot's first chunk entry (0 without a window) */
	chim_user_t		table;			/* the zone block holding all of the above */
	unsigned long	sprite_loads, alias_loads, refused, linked_peak;
	int				linked, efrags;
	model_t			*link_world;
} chim_statics_t;

static chim_statics_t	lists[CHIM_WINDOW_SLOTS];
#define st	lists[0]		/* the map's own frame (type 0: the only list) */

/* The list and its chunk for a chunk entry (the slot's list in a window). */
static chim_statics_t *ListOf (int index, int *local)
{
	chim_statics_t *L;
	int s = 0;
	if (chim_frame.window && index >= 0 && index < chim_frame.count)
		s = chim_frame.entries[index].slot;
	L = &lists[s];
	*local = index - L->base;
	return L;
}

int ChimStatics_Count (void)
{
	int s, n = 0;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		n += lists[s].count;
	return n;
}

/* The i-th streamed static's entity (dbg and the host tests), over the lists in slot order. */
entity_t *ChimStatics_Entity (int i)
{
	int s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		if (i >= 0 && i < lists[s].count)
			return &lists[s].list[i].ent;
		i -= lists[s].count;
	}
	return NULL;
}

/* ---------------------------------------------------------------- the list */

static void ListBegin (chim_statics_t *L, int stated, int chunks, int base)
{
	int bytes;
	memset (L, 0, sizeof(*L));
	L->base = base;
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
	if (!ChimZone_Alloc (&L->table, bytes, CHIM_KIND_STATIC, 0xffffffffu))
	{
		Con_Printf ("CHIM: no room for %ld streamed statics (%ld bytes); they spawn as usual\n", (long)stated, (long)bytes);
		return;
	}
	ChimZone_Lock (L->table.data);
	memset (L->table.data, 0, bytes);
	L->list = (chim_static_t *)L->table.data;
	L->models = (chim_smodel_t *)(L->list + stated);
	L->order = (short *)(L->models + stated);
	L->first = (int *)(((size_t)(L->order + stated) + 7) & ~(size_t)7);
	L->capacity = stated;
	L->chunks = chunks;
}

/* The frame map states how many statics it streams ("_chim_streamed_statics");
 * room for them and their models is taken from the zone, locked for the map. */
void ChimStatics_Begin (int stated, int chunks)
{
	int s;
	for (s=1 ; s<CHIM_WINDOW_SLOTS ; s++)
		memset (&lists[s], 0, sizeof(lists[s]));
	ListBegin (&st, stated, chunks, 0);
}

static void ListEnd (chim_statics_t *L)
{
	int i;
	for (i=0 ; i<L->nmodels ; i++)
	{
		if (L->models[i].user.data)
		{
			while (ChimZone_Locks (L->models[i].user.data) > 0)
				ChimZone_Unlock (L->models[i].user.data);
			ChimZone_Free (&L->models[i].user);
		}
	}
	if (L->table.data)
	{
		ChimZone_Unlock (L->table.data);
		ChimZone_Free (&L->table);
	}
	memset (L, 0, sizeof(*L));
}

void ChimStatics_End (void)
{
	int s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		ListEnd (&lists[s]);
}

static int ModelRow (chim_statics_t *L, const char *name)
{
	int i, n;
	for (i=0 ; i<L->nmodels ; i++)
		if (!strcmp (L->models[i].name, name))
			return i;
	if (L->nmodels >= L->capacity)
		return -1;
	n = (int)strlen (name);
	memset (&L->models[i], 0, sizeof(L->models[i]));
	strcpy (L->models[i].name, name);
	L->models[i].sprite = n > 4 && !Q_strcasecmp ((char *)name + n - 4, ".spr");
	L->nmodels++;
	return i;
}

static int Vector3 (const char *text, vec3_t out)
{
	return Q_sscanf (text, "%f %f %f", &out[0], &out[1], &out[2]) == 3 &&
		isfinite (out[0]) && isfinite (out[1]) && isfinite (out[2]);
}

/* One entity of entity text (*data just past its opening brace): a tagged
 * aw_static or aw_flora is taken into list L and *data moves past its
 * closing brace; anything else is left as it was (0). */
static int CaptureInto (chim_statics_t *L, char **data)
{
	char *p = *data, key[64], classname[32], model[MAX_QPATH];
	vec3_t origin, angles, box[2];
	float scale = 1;
	int frame = 0, skin = 0, chunk = -1, has_box = 0, has_origin = 0, tagged = 0, row;
	chim_static_t *s;

	if (!L->capacity)
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
		!has_box || chunk < 0 || chunk >= L->chunks || L->count >= L->capacity || frame < 0 || frame > 255 ||
		skin < 0 || skin > 255)
	{
		L->refused++;
		if (L->refused == 1)
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
	if ((row = ModelRow (L, model)) < 0)
		return 0;
	if (!strcmp (classname, "aw_flora") && !L->models[row].sprite)
		Host_Error ("Invalid aw_flora static sprite scale");
	s = &L->list[L->count++];
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
	L->sorted = 0;
	*data = p;
	return 1;
}

/* ED_LoadFromFile, for every entity after worldspawn (*data just past its
 * opening brace): the map's own frame's list. */
int ChimStatics_Capture (char **data)
{
	return CaptureInto (&st, data);
}

/* Statics by chunk (counting sort, once after the map's entities). */
static void Sort (chim_statics_t *L)
{
	int i, c;
	if (L->sorted)
		return;
	memset (L->first, 0, (L->chunks + 2) * sizeof(int));
	for (i=0 ; i<L->count ; i++)
		L->first[L->list[i].chunk + 1]++;
	for (c=0 ; c<L->chunks ; c++)
		L->first[c+1] += L->first[c];
	for (i=0 ; i<L->count ; i++)
		L->order[L->first[L->list[i].chunk]++] = (short)i;
	for (c=L->chunks ; c>0 ; c--)
		L->first[c] = L->first[c-1];
	L->first[0] = 0;
	L->sorted = 1;
}

#define FOR_CHUNK(L, index, k, s) \
	for (Sort (L), k = (L)->first[index]; k < (L)->first[(index)+1] && ((s) = &(L)->list[(L)->order[k]]) != NULL; k++)

/* ---------------------------------------------------------------- a window's frame */

/* Frame map name's entity text read for its tagged statics into slot s's
 * list (type 1: a frame joins the window), placed at offset. Returns how
 * many it took. */
int ChimStatics_SlotJoin (int slot, int base, int chunks, const char *map, const float *offset)
{
	chim_statics_t *L = &lists[slot];
	char path[MAX_QPATH+16], *text, *p, *q;
	FILE *f = NULL;
	int bytes, i, stated = 0, n = 0;
	unsigned char head[12];
	long at, length;
	chim_user_t buffer = {NULL};

	ListEnd (L);
	L->base = base;
	if (slot < 0 || slot >= CHIM_WINDOW_SLOTS || !map || !*map)
		return 0;
	AW_MapPath (map, path, sizeof(path));
	bytes = COM_FOpenFile (path, &f);
	if (!f)
		return 0;
	at = ftell (f);
	/* BSP29 header: version, then the entity lump's offset and length. */
	if (fread (head, 1, sizeof(head), f) != sizeof(head))
	{
		fclose (f);
		return 0;
	}
	length = (long)(head[8] | (head[9] << 8) | (head[10] << 16) | ((unsigned long)head[11] << 24));
	i = head[4] | (head[5] << 8) | (head[6] << 16) | (head[7] << 24);
	if (i < 0 || length <= 0 || length > 4*1024*1024 || (long)i + length > bytes ||
		!ChimZone_Alloc (&buffer, (int)length + 1, CHIM_KIND_BUFFER, 0))
	{
		fclose (f);
		return 0;
	}
	ChimZone_Lock (buffer.data);
	text = buffer.data;
	if (fseek (f, at + i, SEEK_SET) || fread (text, 1, (size_t)length, f) != (size_t)length)
		length = 0;
	fclose (f);
	text[length] = 0;
	/* The worldspawn states the count (as the map's own start reads it). */
	if ((p = strstr (text, "\"_chim_streamed_statics\"")) != NULL && (q = strchr (text, '}')) != NULL && p < q)
	{
		for (p += 24 ; *p == ' ' || *p == '\t' ; p++)
			;
		if (*p == '"')
			stated = atoi (p + 1);
	}
	ListBegin (L, stated, chunks, base);
	p = text;
	if (L->capacity && (p = COM_Parse (p)) != NULL && com_token[0] == '{')
	{
		/* Past the worldspawn, then each entity: taken, or skipped whole. */
		while ((p = COM_Parse (p)) != NULL && com_token[0] != '}')
			if (!(p = COM_Parse (p)))
				break;
		while (p && (p = COM_Parse (p)) != NULL && com_token[0] == '{')
		{
			q = p;
			if (CaptureInto (L, &q))
			{
				chim_static_t *s = &L->list[L->count-1];
				int k;
				for (k=0 ; k<2 ; k++)
				{
					s->ent.origin[k] += offset[k];
					s->mins[k] += offset[k];
					s->maxs[k] += offset[k];
				}
				p = q;
				n++;
				continue;
			}
			while ((p = COM_Parse (p)) != NULL && com_token[0] != '}')
				if (!(p = COM_Parse (p)))
					break;
		}
	}
	ChimZone_Unlock (buffer.data);
	ChimZone_Free (&buffer);
	return n;
}

/* A slot's frame left the window: its list and models go. */
void ChimStatics_SlotEnd (int slot)
{
	chim_statics_t *L;
	int i;
	if (slot < 0 || slot >= CHIM_WINDOW_SLOTS)
		return;
	L = &lists[slot];
	for (i=0 ; i<L->count ; i++)
		if (L->list[i].placed || L->list[i].leaves || L->list[i].ent.efrag)
		{
			/* its chunks were deactivated first: nothing may be placed */
			if (L->list[i].ent.efrag && L->link_world && cl.worldmodel == L->link_world && cls.signon == SIGNONS)
				ChimGraft_RemoveEfrags (&L->list[i].ent);
			L->list[i].ent.efrag = NULL;
		}
	ListEnd (L);
}

/* Type 1 crossings, a recentre: the session's origin moved by d (local units). */
void ChimStatics_Recentre (const float *d)
{
	int s, i, k;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		for (i=0 ; i<lists[s].count ; i++)
			for (k=0 ; k<2 ; k++)
			{
				lists[s].list[i].ent.origin[k] -= d[k];
				lists[s].list[i].mins[k] -= d[k];
				lists[s].list[i].maxs[k] -= d[k];
			}
}

/* ---------------------------------------------------------------- models */

static model_t *Resident (chim_statics_t *L, int m)
{
	chim_smodel_t *sm = &L->models[m];
	return sm->sprite ? (sm->user.data ? (model_t *)sm->user.data : NULL) : sm->alias;
}

static unsigned ModelId (const chim_statics_t *L, int row)
{
	return CHIM_STATIC_MODEL_BIT | ((unsigned)(L - lists) << CHIM_STATIC_SLOT_SHIFT) | (unsigned)row;
}

/* The list and row a static model id names, NULL when there is none. */
static chim_statics_t *ModelList (unsigned model, int *row)
{
	unsigned s = (model & ~CHIM_STATIC_MODEL_BIT) >> CHIM_STATIC_SLOT_SHIFT;
	*row = (int)(model & CHIM_STATIC_ROW_MASK);
	if (s >= CHIM_WINDOW_SLOTS || *row >= lists[s].nmodels)
		return NULL;
	return &lists[s];
}

/* The first model a chunk's statics still need: CHIM_STATIC_MODEL_BIT | slot |
 * row, or 0 when all are resident (or cannot be loaded). */
unsigned ChimStatics_Missing (int index)
{
	int k, local;
	chim_static_t *s;
	chim_statics_t *L = ListOf (index, &local);
	if (!L->count || local < 0 || local >= L->chunks)
		return 0;
	FOR_CHUNK (L, local, k, s)
		if (!L->models[s->model].bad && !Resident (L, s->model))
			return ModelId (L, s->model);
	return 0;
}

int ChimStatics_IsStatic (unsigned model)
{
	return (model & CHIM_STATIC_MODEL_BIT) != 0;
}

const char *ChimStatics_Name (unsigned model)
{
	int row;
	chim_statics_t *L = ModelList (model, &row);
	return L ? L->models[row].name : "?";
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
	int row;
	chim_statics_t *L = ModelList (model, &row);
	chim_smodel_t *sm;
	if (!L)
		return 0;
	sm = &L->models[row];
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
	int bound, bytes, row;
	chim_statics_t *L = ModelList (model, &row);

	if (!L)
		return -1;
	sm = &L->models[row];
	if (Resident (L, row))
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
		/* An alias model's data goes to Quake's cache, in the Hunk's gap
		 * (Cache_Alloc ends the game when one request is larger than the
		 * gap). The map counts its alias statics in its Hunk rest
		 * (Chim_HunkRest); one that would still not fit is refused (H15). */
		long gap = (long)host_parms.memsize - Hunk_LowMark () - Hunk_HighMark ();
		if (gap < 2L*bytes + 16384)
		{
			sm->bad = 1;
			Con_Printf ("CHIM: streamed static model %s (%ld bytes) refused: the Hunk gap is %ld bytes\n",
				sm->name, (long)bytes, gap);
			return -1;
		}
		if (!(sm->alias = Mod_ForName (sm->name, false)) || sm->alias->type != mod_alias)
		{
			sm->alias = NULL;
			sm->bad = 1;
			Con_Printf ("CHIM: streamed static model %s is not an alias model\n", sm->name);
			return -1;
		}
		L->alias_loads++;
		return 1;
	}
	bound = (int)ChimStatics_Bytes (model) + (int)sizeof(model_t);
	if (!(m = ChimZone_Alloc (&sm->user, bound, CHIM_KIND_STATIC, (unsigned)row)))
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
	L->sprite_loads++;
	return 1;
}

/* The alias statics' file bytes (their cache need, about): counted in the
 * map's Hunk rest when the player is placed (chim_world.c CheckRest). */
long ChimStatics_AliasBytes (void)
{
	long n = 0;
	int i, s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		for (i=0 ; i<lists[s].nmodels ; i++)
			if (!lists[s].models[i].sprite && !lists[s].models[i].bad)
				n += FileBytes (&lists[s].models[i]);
	return n;
}

/* ---------------------------------------------------------------- chunks */

static void Use (chim_statics_t *L, int m, int on)
{
	chim_smodel_t *sm = &L->models[m];
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

static void Unplace (chim_statics_t *L, chim_static_t *s)
{
	if (s->leaves)
	{
		L->efrags -= s->leaves;
		L->linked--;
	}
	/* Whatever the leaf count says: no link may outlive the model (CHIM-FRAME-EDGE-EFRAG-CRASH-36). */
	if (s->ent.efrag && L->link_world && cl.worldmodel == L->link_world && cls.signon == SIGNONS)
		ChimGraft_RemoveEfrags (&s->ent);
	s->ent.efrag = NULL;
	s->leaves = 0;
	if (s->placed)
	{
		Use (L, s->model, 0);
		s->placed = 0;
		s->ent.model = NULL;
	}
}

/* CL_ParseStatic's entity, once its model is resident. */
static int Place (chim_statics_t *L, chim_static_t *s)
{
	model_t *m = Resident (L, s->model);
	if (!m)
		return 0;
	/* Bad flora data leaves the static out, never a Host_Error here: chunk
	 * activation holds zone locks a longjmp would leave behind, and the next
	 * map's zone drop then stopped the program (CHIM-STATIC-PLACE-HOST-ERROR-35). */
	if (s->flora && (m->type != mod_sprite || !isfinite (s->scale * m->radius)))
	{
		if (!L->models[s->model].bad)
			Con_Printf ("CHIM: invalid aw_flora static sprite scale (%s): left out\n", m->name);
		L->models[s->model].bad = 1;
		return 0;
	}
	s->ent.model = m;
	s->ent.frame = s->frame;
	s->ent.colormap = vid.colormap;
	s->ent.skinnum = s->skin;
	s->ent.effects = 0;
	s->ent.aw_sprite_scale = s->scale;
	s->ent.efrag = NULL;
	s->leaves = 0;
	s->placed = 1;
	Use (L, s->model, 1);
	return 1;
}

/* A chunk became active: its statics with resident models are placed.
 * Returns how many still wait for their model (a partial chunk). */
int ChimStatics_Activate (int index)
{
	int k, missing = 0, local;
	chim_static_t *s;
	chim_statics_t *L = ListOf (index, &local);
	if (!L->count || local < 0 || local >= L->chunks)
		return 0;
	FOR_CHUNK (L, local, k, s)
		if (!s->placed && !Place (L, s) && !L->models[s->model].bad)
			missing++;
	return missing;
}

void ChimStatics_Deactivate (int index)
{
	int k, local;
	chim_static_t *s;
	chim_statics_t *L = ListOf (index, &local);
	if (!L->count || local < 0 || local >= L->chunks)
		return;
	FOR_CHUNK (L, local, k, s)
		Unplace (L, s);
}

/* ChimChunks_Link: every placed static of an active, grafted chunk is in the
 * leaves its drawn box touches (the frame world's own leaves). */
static int ListLink (chim_statics_t *L, int (*add)(entity_t *ent, const vec3_t mins, const vec3_t maxs),
	int (*linkable)(int index))
{
	int i;
	chim_static_t *s;
	if (!L->count || !cl.worldmodel)
		return 0;
	if (cl.worldmodel != L->link_world)
	{
		/* A new client map reset the efrag pool. */
		for (i=0 ; i<L->count ; i++)
			L->list[i].ent.efrag = NULL, L->list[i].leaves = 0;
		L->linked = L->efrags = 0;
		L->link_world = cl.worldmodel;
	}
	for (i=0 ; i<L->count ; i++)
	{
		s = &L->list[i];
		if (!s->placed || s->leaves || !linkable (s->chunk + L->base))
			continue;
		s->leaves = (short)add (&s->ent, s->mins, s->maxs);
		if (s->leaves)
		{
			L->linked++;
			L->efrags += s->leaves;
		}
	}
	if ((unsigned long)L->linked > L->linked_peak)
		L->linked_peak = L->linked;
	return L->linked;
}

int ChimStatics_Link (int (*add)(entity_t *ent, const vec3_t mins, const vec3_t maxs), int (*linkable)(int index))
{
	int s, n = 0;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		n += ListLink (&lists[s], add, linkable);
	return n;
}

/* The client's efrag pool was reset (a map change): links are forgotten,
 * never unlinked from leaves that no longer exist. */
void ChimStatics_PoolReset (void)
{
	int i, s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		chim_statics_t *L = &lists[s];
		for (i=0 ; i<L->count ; i++)
			L->list[i].ent.efrag = NULL, L->list[i].leaves = 0;
		L->linked = L->efrags = 0;
		L->link_world = NULL;
	}
}

/* The list holding an entity, or NULL. */
static chim_statics_t *EntityList (const entity_t *ent)
{
	int s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		const chim_static_t *x = (const chim_static_t *)ent;
		if (lists[s].count && x >= lists[s].list && x < lists[s].list + lists[s].count)
			return &lists[s];
	}
	return NULL;
}

/* The frame world took an entity out of its leaves: when it is a static,
 * ChimStatics_Link links it again. */
const char *ChimStatics_Describe (const entity_t *ent, char *out, int size)
{
	const chim_static_t *s = (const chim_static_t *)ent;
	chim_statics_t *L = EntityList (ent);
	(void)size;
	if (!L)
		return NULL;
	sprintf (out, "CHIM static %ld (chunk %d, placed %d, leaves %d)", (long)(s - L->list), s->chunk, s->placed, s->leaves);
	return out;
}

int ChimStatics_Forget (entity_t *ent)
{
	chim_static_t *s = (chim_static_t *)ent;
	chim_statics_t *L = EntityList (ent);
	if (!L)
		return 0;
	if (s->leaves)
	{
		L->efrags -= s->leaves;
		L->linked--;
		s->leaves = 0;
	}
	return 1;
}

/* Before the world's leaves are replaced (ChimChunks_ReleaseEfrags). */
void ChimStatics_ReleaseEfrags (void)
{
	int i, s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		chim_statics_t *L = &lists[s];
		for (i=0 ; i<L->count ; i++)
			if (L->list[i].leaves)
			{
				ChimGraft_ReleaseEfrags (&L->list[i].ent);
				L->list[i].leaves = 0;
			}
		L->linked = L->efrags = 0;
	}
}

void ChimStatics_Report (void)
{
	int i, s, resident = 0, bytes = 0, bad = 0, count = 0, capacity = 0, linked = 0, efrags = 0, nmodels = 0;
	unsigned long peak = 0, sprites = 0, alias = 0, refused = 0;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		chim_statics_t *L = &lists[s];
		for (i=0 ; i<L->nmodels ; i++)
		{
			if (L->models[i].bad)
				bad++;
			if (L->models[i].user.data)
			{
				resident++;
				bytes += ChimZone_Size (L->models[i].user.data);
			}
			else if (L->models[i].alias)
				resident++;
		}
		count += L->count;
		capacity += L->capacity;
		linked += L->linked;
		efrags += L->efrags;
		nmodels += L->nmodels;
		peak += L->linked_peak;
		sprites += L->sprite_loads;
		alias += L->alias_loads;
		refused += L->refused;
	}
	if (!capacity)
		return;
	Con_Printf ("streamed statics: %ld of %ld stated, %ld linked (most %lu), %ld efrags; models %ld (%ld resident, %ld KiB of sprites in the zone, %ld bad); loads %lu sprites, %lu alias; refused %lu\n",
		(long)count, (long)capacity, (long)linked, peak, (long)efrags,
		(long)nmodels, (long)resident, (long)(bytes/1024), (long)bad, sprites, alias, refused);
}

void ChimStatics_Counts (int *count, int *linked, int *efrags, int *models, int *sprite_bytes)
{
	int i, s;
	*count = *linked = *efrags = *models = *sprite_bytes = 0;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		chim_statics_t *L = &lists[s];
		*count += L->count;
		*linked += L->linked;
		*efrags += L->efrags;
		*models += L->nmodels;
		for (i=0 ; i<L->nmodels ; i++)
			if (L->models[i].user.data)
				*sprite_bytes += ChimZone_Size (L->models[i].user.data);
	}
}
