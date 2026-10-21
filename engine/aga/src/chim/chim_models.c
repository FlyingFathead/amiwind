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
#include "chim_terc.h"
#include "chim_thgt.h"

void R_InitSky (texture_t *mt);

/* One load at a time: the model or terrain being decoded, possibly over
 * several frames when its brush image does not fit the loading buffer. */
static struct
{
	int				active, kind;
	unsigned		id;
	chim_model_t	*block;
	chim_pack_t		*pack;		/* a stream's file, pinned until the load ends */
	aw_brush_stream_t	stream;
} job;

/* The last load that failed in a stream step (bad data): the next ask for
 * it is answered -1 at once, so its chunk waits as for any failed load
 * instead of reading the same bad image again every frame. */
static int		bad_kind;
static unsigned	bad_id;

static void Unpin (void)
{
	if (job.pack && job.pack->pins > 0)
		job.pack->pins--;
	job.pack = NULL;
}

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
	/* Every mip level inside the pixels read (H15): a wrong offset would
	 * make the rasterizer read past the zone block. */
	for (j=0 ; j<MIPLEVELS ; j++)
		if (mt->offsets[j] < (int)sizeof(miptex_t) ||
			mt->offsets[j] - (int)sizeof(miptex_t) > pixels - (mt->width>>j)*(mt->height>>j))
			return NULL;
	if (chim_debug.value >= 2)
		Con_Printf ("CHIM: texture %lu %ldx%ld\n", (unsigned long)id, (long)mt->width, (long)mt->height);
	mt->name[sizeof(mt->name)-1] = 0;
	if (ChimFormat_TurbulentTile (mt->name, mt->width, mt->height) &&
		mt->offsets[1] == mt->offsets[0] + mt->width*mt->height && mt->offsets[0] == (int)sizeof(miptex_t) &&
		mt->offsets[2] == mt->offsets[1] + mt->width*mt->height/4 && mt->offsets[3] == mt->offsets[2] + mt->width*mt->height/16)
	{
		/* A small turbulent texture is tiled to the 64 x 64 that Turbulent8 reads (chim_format.h). */
		static byte small[CHIM_TURB_PIXELS];
		if (pixels > (int)sizeof(small) || !(pack = Chim_File (e->file)) ||
			!Chim_PackRead (pack, e->offset + sizeof(miptex_t), small, pixels))
			return NULL;
		tx = ChimZone_Alloc (NULL, sizeof(texture_t) + CHIM_TURB_PIXELS, CHIM_KIND_TEXTURE, id);
		if (!tx)
			return NULL;
		ChimFormat_TileTurbulent (small, mt->width, mt->height, (byte *)(tx+1));
		memcpy (tx->name, mt->name, sizeof(tx->name));
		tx->width = tx->height = CHIM_TURB_SIZE;
		tx->offsets[0] = sizeof(texture_t);
		for (j=1 ; j<MIPLEVELS ; j++)
			tx->offsets[j] = tx->offsets[j-1] + (CHIM_TURB_SIZE>>(j-1))*(CHIM_TURB_SIZE>>(j-1));
		chim_world.texture_loads++;
		return tx;
	}
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

/* The chunk whose terrain is being streamed in, -1: none (a window's frame
 * that leaves stops it first, chim_chunks.c SlotFinish). */
int ChimModels_JobTerrain (void)
{
	return job.active && job.kind == CHIM_KIND_TERRAIN ? (int)job.id : -1;
}

void ChimModels_Abort (void)
{
	if (!job.active)
		return;
	job.active = 0;
	Unpin ();
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
	/* 0.8: the piece table into native order once; a table the placed
	 * collision cannot use leaves the model on its stored hull */
	if (cm->piece_bytes && cm->model.visdata)
		cm->pieces = ChimPlaced_TableLoad (cm->model.visdata, cm->piece_bytes);
	if (job.kind == CHIM_KIND_MODEL)
	{
		chim_world.model_loads++;
		if (cm->id < chim_world.models)
			chim_world.model_slot[cm->id] = cm;
	}
	job.active = 0;
	job.block = NULL;
	Unpin ();
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
	long disk = bytes;		/* read from the disk (a compact terrain record expands after) */

	if (chim_debug.value >= 2)
		Con_Printf ("CHIM: begin %s %lu: %ld bytes at %ld in %s\n", kind == CHIM_KIND_MODEL ? "model" : "terrain",
			(unsigned long)id, bytes, offset, pack->path);
	if (image && kind == CHIM_KIND_TERRAIN && chim_world.minor >= CHIM_TERC_MINOR)
	{
		/* 0.10: a terrain record may be compact (chim_terc.c): read it to the buffer's end and expand it to the
		 * start, the same BSP29 bytes as the record it was packed from; a plain image moves to the start */
		long tail = chim_world.buffer_bytes - bytes, expanded;
		if (!Chim_PackRead (pack, offset, chim_world.buffer + tail, bytes))
			return -1;
		if (ChimTerc_Is (chim_world.buffer + tail, bytes))
		{
			if (!ChimTerc_Expand (chim_world.buffer + tail, bytes, chim_world.buffer, tail, &expanded))
				return -1;
			chim_world.terc_records++;
			bytes = expanded;
		}
		else if (chim_world.minor >= CHIM_THGT_MINOR && ChimThgt_Is (chim_world.buffer + tail, bytes))
		{
			/* 0.11: a generated record: the render part generated from its heights (chim_thgt.c) */
			if (!ChimThgt_Generate (chim_world.buffer + tail, bytes, chim_world.buffer, tail, &expanded,
				&chim_world.thgt))
				return -1;
			bytes = expanded;
		}
		else
			memmove (chim_world.buffer, chim_world.buffer + tail, (size_t)bytes);
	}
	else if (image ? !Chim_PackRead (pack, offset, chim_world.buffer, bytes) :
		!Chim_PackRead (pack, offset, head, sizeof(head)))
		return -1;
	if (!AW_BrushHeader (&header, image ? chim_world.buffer : head, bytes) ||
		(bound = AW_BrushBound (&header, 1, kind == CHIM_KIND_MODEL)) < 0 || bound > 0x7fffffff - (int)sizeof(*cm))
		return -1;
	cm = ChimZone_Alloc (user, sizeof(*cm) + bound, kind, id);
	if (!cm)
		return -1;
	ChimZone_Lock (cm);
	cm->id = id;
	cm->kind = kind;
	cm->leafs = header.lumps[LUMP_LEAFS].filelen / (int)sizeof(dleaf_t);
	/* 0.8: a placed model's lump 4 is its piece table (read as visdata) */
	cm->piece_bytes = kind == CHIM_KIND_MODEL && chim_world.minor >= CHIM_PLACED_MINOR ?
		header.lumps[LUMP_VISIBILITY].filelen : 0;
	cm->pieces = 0;
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
		*budget -= disk;
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
	/* The stream keeps this stdio handle over several frames: texture loads
	 * and other chunks open other files meanwhile (CHIM-PACK-LRU-STREAM-35). */
	job.pack = pack;
	pack->pins++;
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
	if (done < 0)
	{
		/* Bad data in the image (model.c said why): this load ends, the
		 * game goes on (CHIM-BRUSH-BAD-DATA-35). */
		bad_kind = job.kind;
		bad_id = job.id;
		chim_world.failed_loads++;
		ChimModels_Abort ();
		return -1;
	}
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
			return Continue (budget) > 0 && 0;
		/* The asker hears of a failure itself: nothing left to remember. */
		if ((r = Continue (budget)) < 0)
			bad_kind = 0;
		return r;
	}
	if (ChimModels_Find (id))
		return 1;
	if (id >= chim_world.models)
		return -1;
	if (bad_kind == CHIM_KIND_MODEL && bad_id == id)
	{
		bad_kind = 0;
		return -1;
	}
	e = &chim_world.model[id];
	if (!(pack = Chim_File (e->file)))
		return -1;
	r = Begin (CHIM_KIND_MODEL, id, NULL, pack, e->offset, e->bytes, budget);
	if (r < 0)
		chim_world.failed_loads++;
	return r;
}

/* Where a chunk's terrain image is: the end of its chunk record (CHK0), or
 * the TERR record its reference block names (0.7 CHK1), placed at the
 * block's shift (kept in the entry for the graft). Returns 1, or -1 on bad
 * data; pack and at may be NULL (bytes only). */
int ChimModels_TerrainPlace (int entry, chim_pack_t **pack_out, long *at_out, long *bytes_out)
{
	chim_entry_t *e = &chim_frame.entries[entry];
	chim_chunk_head_t head;
	chim_terrain_ref_t ref;
	chim_pack_t *pack;
	byte raw[CHIM_TERRAIN_REF_BYTES];
	long at, bytes;
	int k;

	if (!(pack = Chim_File (e->file)) || !Chim_PackRead (pack, e->disk.offset, raw, CHIM_CHUNK_HEAD_BYTES) ||
		!ChimFormat_ChunkHead (raw, &head))
		return -1;
	if (!head.ref)
	{
		at = (long)e->disk.offset + head.image_at;
		bytes = (long)e->disk.render + e->disk.collision - head.image_at;
		for (k=0 ; k<3 ; k++)
			e->shift[k] = 0;
	}
	else
	{
		if (chim_world.minor < 7 || head.image_render != CHIM_TERRAIN_REF_BYTES || e->disk.collision ||
			!Chim_PackRead (pack, (long)e->disk.offset + head.image_at, raw, CHIM_TERRAIN_REF_BYTES) ||
			!ChimFormat_TerrainRef (raw, &ref) || ref.file >= (unsigned)chim_world.files ||
			strcmp (chim_world.file[ref.file].kind, "SECT") || ref.offset < CHIM_HEADER_BYTES ||
			ref.offset > chim_world.file[ref.file].bytes || ref.bytes > chim_world.file[ref.file].bytes - ref.offset)
			return -1;
		if (pack_out && !(pack = Chim_File ((int)ref.file)))
			return -1;
		at = (long)ref.offset;
		bytes = (long)ref.bytes;
		for (k=0 ; k<3 ; k++)
			e->shift[k] = ref.shift[k];
	}
	/* A window's frame (type 1 crossings): placed at its offset from the
	 * frame the map started on, as the graft places a referenced terrain. */
	if (chim_frame.window)
		for (k=0 ; k<2 ; k++)
			e->shift[k] += chim_frame.slot[e->slot].offset[k];
	if (bytes < (long)sizeof(dheader_t))
		return -1;
	if (pack_out)
		*pack_out = pack;
	if (at_out)
		*at_out = at;
	if (bytes_out)
		*bytes_out = bytes;
	return 1;
}

/* A chunk's terrain: its brush image (ChimModels_TerrainPlace). */
int ChimModels_TerrainStep (int entry, long *budget)
{
	chim_entry_t *e = &chim_frame.entries[entry];
	chim_pack_t *pack;
	long at, bytes;
	int r;

	if (job.active)
	{
		if (job.kind != CHIM_KIND_TERRAIN || job.id != (unsigned)entry)
			return Continue (budget) > 0 && 0;
		if ((r = Continue (budget)) < 0)
			bad_kind = 0;
		return r;
	}
	if (e->terrain.data)
		return 1;
	if (bad_kind == CHIM_KIND_TERRAIN && bad_id == (unsigned)entry)
	{
		bad_kind = 0;
		return -1;
	}
	if (ChimModels_TerrainPlace (entry, &pack, &at, &bytes) < 0)
		return -1;
	r = Begin (CHIM_KIND_TERRAIN, (unsigned)entry, &e->terrain, pack, at, bytes, budget);
	if (r < 0)
		chim_world.failed_loads++;
	return r;
}
