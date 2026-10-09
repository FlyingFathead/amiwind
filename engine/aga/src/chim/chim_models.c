/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM shared models and textures.
 *
 * Quake mechanisms reused: Mod_Load* section decoders (model.c), reached
 * through AW_BrushImage / AW_BrushStream* with an arena instead of the Hunk;
 * Mod_LoadTextures' miptex-to-texture_t conversion for the shared texture
 * pool; R_InitSky for sky textures; the surface cache's own owner backlinks
 * (d_surf.c) to detach an evicted model. Library models never take a
 * mod_known slot and never go on the wire (no modelindex), so neither
 * MAX_MOD_KNOWN nor MAX_MODELS limits them: residency is limited by memory.
 */
#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include "chim_local.h"

void R_InitSky (texture_t *mt);

/* One load at a time: the model or terrain being decoded, possibly over
 * several frames when its brush image does not fit the loading buffer. */
static struct
{
	int				active, kind;
	unsigned		id;
	chim_model_t	*block;
	aw_brush_stream_t	stream;
} job;

/* ---------------------------------------------------------------- textures */

/* Same conversion as Mod_LoadTextures: texture_t, then the four mip levels. */
static texture_t *LoadTexture (unsigned id)
{
	chim_asset_t *e;
	chim_pack_t *pack;
	byte raw[sizeof(miptex_t)];
	miptex_t *mt = (miptex_t *)raw;
	texture_t *tx;
	int j, pixels;

	if (id >= chim_world.textures)
		return NULL;
	e = &chim_world.texture[id];
	if (e->bytes < sizeof(miptex_t) || !(pack = Chim_File (e->file)) ||
		!Chim_PackRead (pack, e->offset, raw, sizeof(raw)))
		return NULL;
	mt->width = LittleLong (mt->width);
	mt->height = LittleLong (mt->height);
	for (j=0 ; j<MIPLEVELS ; j++)
		mt->offsets[j] = LittleLong (mt->offsets[j]);
	if ((mt->width & 15) || (mt->height & 15) || mt->width <= 0 || mt->height <= 0 ||
		mt->width > 1024 || mt->height > 1024 || mt->width != e->width || mt->height != e->height)
		return NULL;
	pixels = mt->width*mt->height/64*85;
	if ((unsigned)pixels > e->bytes - sizeof(miptex_t))
		return NULL;
	if (chim_debug.value >= 2)
		Con_Printf ("CHIM: texture %lu %ldx%ld\n", (unsigned long)id, (long)mt->width, (long)mt->height);
	tx = ChimZone_Alloc (NULL, sizeof(texture_t) + pixels, CHIM_KIND_TEXTURE, id);
	if (!tx)
		return NULL;
	memcpy (tx->name, mt->name, sizeof(tx->name));
	tx->name[sizeof(tx->name)-1] = 0;
	tx->width = mt->width;
	tx->height = mt->height;
	for (j=0 ; j<MIPLEVELS ; j++)
		tx->offsets[j] = mt->offsets[j] + sizeof(texture_t) - sizeof(miptex_t);
	if (!(pack = Chim_File (e->file)) || !Chim_PackRead (pack, e->offset + sizeof(miptex_t), tx+1, pixels))
	{
		ChimZone_FreeData (tx);
		return NULL;
	}
	if (!Q_strncmp (tx->name, "sky", 3))
		R_InitSky (tx);
	chim_world.texture_loads++;
	return tx;
}

/* Brush arena resolver: every texture a resident model uses stays locked
 * (one lock per use) until the model is evicted. */
static texture_t *ResolveTexture (void *context, int id)
{
	texture_t *tx;
	if (id < 0)
		return NULL;
	tx = (unsigned)id < chim_world.textures ? chim_world.texture_slot[id] : NULL;
	if (!tx && (unsigned)id < chim_world.textures && (tx = LoadTexture ((unsigned)id)) != NULL)
		chim_world.texture_slot[id] = tx;
	if (!tx)
	{
		chim_world.failed_loads++;
		Con_Printf ("CHIM: texture %ld unavailable, drawn untextured\n", (long)id);
		return r_notexture_mip;
	}
	ChimZone_Touch (tx);
	ChimZone_Lock (tx);
	return tx;
}

int ChimModels_ResidentTextures (void)
{
	chim_zone_stats_t s;
	ChimZone_Stats (&s);
	return s.kind_blocks[CHIM_KIND_TEXTURE];
}

/* ---------------------------------------------------------------- eviction */

/* The surface cache keeps a backlink to each surface that owns a block;
 * unhook them so a later reuse of the block never writes into freed memory
 * (D_FlushCaches does the same for the whole cache at a map change). */
static void DetachSurfaces (model_t *m)
{
	int i;
	msurface_t *s;
	surfcache_t *c;

	if (!m->surfaces)
		return;
	for (i=0, s=m->surfaces ; i<m->numsurfaces ; i++, s++)
		while ((c = s->cachehead) != NULL)
		{
			s->cachehead = c->surface_next;
			if (c->surface_next)
				c->surface_next->owner = &s->cachehead;
			c->owner = NULL;
			c->surface_next = NULL;
		}
}

static void ReleaseModel (chim_model_t *cm)
{
	int i;
	DetachSurfaces (&cm->model);
	if (cm->model.textures && cm->arena.texture)
		for (i=0 ; i<cm->model.numtextures ; i++)
			if (cm->model.textures[i] && cm->model.textures[i] != r_notexture_mip)
				ChimZone_Unlock (cm->model.textures[i]);
	cm->model.textures = NULL;
	cm->model.numtextures = 0;
}

static void ModelEvicted (void *data, unsigned id)
{
	if (job.active && job.block == data)
		Sys_Error ("CHIM: model %lu evicted while loading", (unsigned long)id);
	if (((chim_model_t *)data)->kind == CHIM_KIND_MODEL && chim_world.model_slot && id < chim_world.models &&
		chim_world.model_slot[id] == data)
		chim_world.model_slot[id] = NULL;
	ReleaseModel ((chim_model_t *)data);
}

static void TextureEvicted (void *data, unsigned id)
{
	if (chim_world.texture_slot && id < chim_world.textures && chim_world.texture_slot[id] == data)
		chim_world.texture_slot[id] = NULL;
}

static void SlotModel (void *data, unsigned id)
{
	if (id < chim_world.models && !(job.active && job.block == data))
		chim_world.model_slot[id] = data;
}

static void SlotTexture (void *data, unsigned id)
{
	if (id < chim_world.textures)
		chim_world.texture_slot[id] = data;
}

/* After the index is read: the models and textures already in the zone. */
void ChimModels_IndexSlots (void)
{
	ChimZone_ForEach (CHIM_KIND_MODEL, SlotModel);
	ChimZone_ForEach (CHIM_KIND_TEXTURE, SlotTexture);
}

void ChimModels_Init (void)
{
	ChimZone_SetEvict (CHIM_KIND_MODEL, ModelEvicted);
	ChimZone_SetEvict (CHIM_KIND_TERRAIN, ModelEvicted);
	ChimZone_SetEvict (CHIM_KIND_TEXTURE, TextureEvicted);
}

/* ---------------------------------------------------------------- loading */

chim_model_t *ChimModels_Find (unsigned id)
{
	/* Set when a model's decode finishes, cleared when it is evicted. */
	return id < chim_world.models && chim_world.model_slot ? chim_world.model_slot[id] : NULL;
}

int ChimModels_Busy (void)
{
	return job.active;
}

/* A terrain block exists from the start of its load; it is usable after. */
chim_model_t *ChimModels_Terrain (int entry)
{
	chim_model_t *cm = chim_frame.entries[entry].terrain.data;
	return cm && !(job.active && job.block == cm) ? cm : NULL;
}

void ChimModels_Abort (void)
{
	if (!job.active)
		return;
	job.active = 0;
	ChimZone_Unlock (job.block);
	ReleaseModel (job.block);
	ChimZone_FreeData (job.block);
	job.block = NULL;
}

static void Finish (void)
{
	chim_model_t *cm = job.block;
	ChimZone_Trim (cm, sizeof(*cm) + cm->arena.used);
	cm->arena.size = cm->arena.used;
	cm->arena.slice = NULL;
	cm->arena.slice_bytes = 0;
	ChimZone_Unlock (cm);
	if (job.kind == CHIM_KIND_MODEL)
	{
		chim_world.model_loads++;
		if (cm->id < chim_world.models)
			chim_world.model_slot[cm->id] = cm;
	}
	job.active = 0;
	job.block = NULL;
}

/* Start a load of a brush image at [offset, offset+bytes) of a pack: decode
 * it at once when it fits the loading buffer, else begin a stream. Returns
 * 1 when the model is resident, 0 while a stream continues, -1 on failure. */
static int Begin (int kind, unsigned id, chim_user_t *user, chim_pack_t *pack, long offset, long bytes, long *budget)
{
	dheader_t header;
	byte head[sizeof(dheader_t)];
	chim_model_t *cm;
	int bound, image = bytes <= chim_world.buffer_bytes;

	if (chim_debug.value >= 2)
		Con_Printf ("CHIM: begin %s %lu: %ld bytes at %ld in %s\n", kind == CHIM_KIND_MODEL ? "model" : "terrain",
			(unsigned long)id, bytes, offset, pack->path);
	if (image ? !Chim_PackRead (pack, offset, chim_world.buffer, bytes) :
		!Chim_PackRead (pack, offset, head, sizeof(head)))
		return -1;
	if (!AW_BrushHeader (&header, image ? chim_world.buffer : head, bytes) ||
		(bound = AW_BrushBound (&header, 1)) < 0 || bound > 0x7fffffff - (int)sizeof(*cm))
		return -1;
	cm = ChimZone_Alloc (user, sizeof(*cm) + bound, kind, id);
	if (!cm)
		return -1;
	ChimZone_Lock (cm);
	cm->id = id;
	cm->kind = kind;
	cm->leafs = header.lumps[LUMP_LEAFS].filelen / (int)sizeof(dleaf_t);
	sprintf (cm->model.name, kind == CHIM_KIND_MODEL ? "chim:m%lu" : "chim:t%lu", (unsigned long)id);
	cm->arena.base = (byte *)(cm+1);
	cm->arena.size = bound;
	cm->arena.slice = chim_world.buffer;
	cm->arena.slice_bytes = chim_world.buffer_bytes;
	cm->arena.texture = ResolveTexture;
	/* Placed models: hull 0 only; chunk terrain keeps its world node tree. */
	cm->arena.point_hull_only = kind == CHIM_KIND_MODEL;
	cm->arena.context = NULL;
	job.active = 1; job.kind = kind; job.id = id; job.block = cm;
	if (chim_debug.value >= 2)
		Con_Printf ("CHIM: bound %ld bytes, %s\n", (long)bound, image ? "image" : "stream");
	if (image)
	{
		*budget -= bytes;
		if (!AW_BrushImage (&cm->model, chim_world.buffer, bytes, &cm->arena))
		{
			ChimModels_Abort ();
			return -1;
		}
		Finish ();
		return 1;
	}
	*budget -= sizeof(head);
	if (!AW_BrushStreamBegin (&job.stream, &cm->model, pack->file, pack->base + offset, bytes, &cm->arena))
	{
		ChimModels_Abort ();
		return -1;
	}
	chim_world.streamed_models++;
	return 0;
}

extern long aw_load_disk_bytes;

/* One section of the stream in progress; the bytes it read (its lump and
 * any textures it loaded) count against the frame's budget. */
static int Continue (long *budget)
{
	int done;
	long disk = aw_load_disk_bytes;
	unsigned long before = chim_world.bytes_read;
	done = AW_BrushStreamStep (&job.stream);
	*budget -= 1 + (aw_load_disk_bytes - disk) + (long)(chim_world.bytes_read - before);
	if (done)
	{
		Finish ();
		return 1;
	}
	return 0;
}

int ChimModels_Step (unsigned id, long *budget)
{
	chim_asset_t *e;
	chim_pack_t *pack;
	int r;

	if (job.active)
	{
		if (job.kind != CHIM_KIND_MODEL || job.id != id)
			return Continue (budget) && 0;
		return Continue (budget);
	}
	if (ChimModels_Find (id))
		return 1;
	if (id >= chim_world.models)
		return -1;
	e = &chim_world.model[id];
	if (!(pack = Chim_File (e->file)))
		return -1;
	r = Begin (CHIM_KIND_MODEL, id, NULL, pack, e->offset, e->bytes, budget);
	if (r < 0)
		chim_world.failed_loads++;
	return r;
}

/* A chunk's terrain: the brush image at the end of its chunk record. */
int ChimModels_TerrainStep (int entry, long *budget)
{
	chim_entry_t *e = &chim_frame.entries[entry];
	chim_chunk_head_t head;
	chim_pack_t *pack;
	byte raw[CHIM_CHUNK_HEAD_BYTES];
	long at, bytes;
	int r;

	if (job.active)
	{
		if (job.kind != CHIM_KIND_TERRAIN || job.id != (unsigned)entry)
			return Continue (budget) && 0;
		return Continue (budget);
	}
	if (e->terrain.data)
		return 1;
	if (!(pack = Chim_File (e->file)) || !Chim_PackRead (pack, e->disk.offset, raw, sizeof(raw)) ||
		!ChimFormat_ChunkHead (raw, &head))
		return -1;
	at = (long)e->disk.offset + head.image_at;
	bytes = (long)e->disk.render + e->disk.collision - head.image_at;
	if (bytes < (long)sizeof(dheader_t))
		return -1;
	r = Begin (CHIM_KIND_TERRAIN, (unsigned)entry, &e->terrain, pack, at, bytes, budget);
	if (r < 0)
		chim_world.failed_loads++;
	return r;
}
