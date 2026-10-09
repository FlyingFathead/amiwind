/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM chunks: the frame's chunk directory, the ring around the player,
 * placement catalogues, collision and the link into Quake's renderer.
 *
 * Quake mechanisms reused:
 * - Static entities and efrags (cl_parse.c CL_ParseStatic, r_efrag.c): every
 *   placement is an entity_t linked to the world leaves its drawn box touches
 *   (R_SplitEntityOnNode), stored for drawing only when one of those leaves
 *   is visible (R_StoreEfrags from R_RecursiveWorldNode, after the PVS and
 *   frustum). No edict, no signon message, no 16-leaf edict limit, and no
 *   modelindex: placements never reach MAX_EDICTS or MAX_MODELS.
 * - Brush entity collision (world.c SV_ClipMoveToEntity): the same hull
 *   choice, offset, yaw rotation, SV_RecursiveHullCheck and DIST_EPSILON
 *   pull-back, with each placement's yaw sine and cosine computed once.
 * - The placement catalogue of aw_scenery.c: the same drawn box and the same
 *   merge into the world trace (AW_MergeCollisionTrace).
 *
 * Chunk terrain is world geometry (chim_graft.c grafts it into the map's
 * world model whenever the active set changes).
 *
 * A placement is stored once as its owner record and copied, as a record
 * only, into every other chunk its drawn box touches (reach copies). The
 * engine draws and collides each placement exactly once: the owner record
 * when the owner chunk is active, else one active reach copy (Reconcile).
 */
#include "quakedef.h"
#include "r_local.h"
#include "chim_local.h"

extern efrag_t	**lastlink;
extern vec3_t	r_emins, r_emaxs;
extern entity_t	*r_addent;
extern mnode_t	*r_pefragtopnode;
void R_SplitEntityOnNode (mnode_t *node);
void R_RemoveEfrags (entity_t *ent);
qboolean SV_RecursiveHullCheck (hull_t *hull, int num, float p1f, float p2f, vec3_t p1, vec3_t p2, trace_t *trace);
void AW_MergeCollisionTrace (trace_t *best, trace_t *candidate, edict_t *touch);

#define CHIM_DIST_EPSILON	(0.03125f)	/* world.c DIST_EPSILON */

chim_frame_state_t	chim_frame;
static short		*grid;				/* chunk (cx, cy) -> entry */
static chim_user_t	index_user;
static model_t		*link_world;		/* cl.worldmodel the efrags belong to */
static unsigned long	ticks;
static int			world_dirty;
static unsigned long	world_retry;
static unsigned long	frozen_frame, frozen_now, frozen_last;
/* The ring around the player: where it was last tick and which way it
 * moves (prefetch ahead), how far the nearest chunk without ground in the
 * frame world is (the safety margin), and loads past the budget for chunks
 * within the collision margin. */
static struct
{
	vec3_t			last, ahead;
	int				moved, has_ahead;
	float			margin, margin_min;	/* units; -1: every chunk of the frame grafted */
	unsigned long	urgent_loads;
} ring;
static struct
{
	int		efrags, placements_linked, one_leaf, max_leaves, hidden;
	unsigned long	activations, deactivations, reconciles;
	unsigned long	zone_maps;
} counts;
/* A full zone (CHIM-CHUNK-LOAD-FAIL-33): chunks released for a nearer one
 * (past the active radius, inside it), partial activations, and failed
 * loads by reason. Kept across maps, like the zone's own counters. */
static struct
{
	unsigned long	band, ring, partial, zone, data;
} pressure;

void ChimChunks_Pressure (unsigned long *released_band, unsigned long *released_ring, unsigned long *partial,
	unsigned long *zone_failures, unsigned long *data_failures)
{
	*released_band = pressure.band;
	*released_ring = pressure.ring;
	*partial = pressure.partial;
	*zone_failures = pressure.zone;
	*data_failures = pressure.data;
}

/* ---------------------------------------------------------------- directory */

/* The frame file (chunk directory, sector table) of frame (cx, cy); each
 * chunk record lives in one of the frame's sector files. */
int ChimChunks_Begin (int cx, int cy)
{
	byte head[CHIM_HEADER_BYTES + CHIM_FRAME_BYTES];
	chim_header_t h;
	chim_pack_t *pack;
	int i, n, cells, bits, size, row = -1, sectors;
	byte *raw = chim_world.buffer;
	int per = chim_world.buffer_bytes / CHIM_CHUNK_ENTRY_BYTES;

	memset (&chim_frame, 0, sizeof(chim_frame));
	memset (&counts, 0, sizeof(counts));
	link_world = NULL;
	for (i=0 ; i<chim_world.files && row < 0 ; i++)
		if (!strcmp (chim_world.file[i].kind, "FRAM") && chim_world.file[i].cx == cx && chim_world.file[i].cy == cy)
			row = i;
	if (row < 0 || !(pack = Chim_File (row)) || !Chim_PackRead (pack, 0, head, sizeof(head)) ||
		!ChimFormat_Header (head, pack->bytes, "FRAM", &h) ||
		!ChimFormat_Frame (head + CHIM_HEADER_BYTES, &chim_frame.frame))
		return 0;
	chim_frame.settings = chim_world.settings;
	/* Placement ids run on across the frames of a world, in pack order (the
	 * index's file table): this frame's ids start after the earlier frames'. */
	for (i=0 ; i<row ; i++)
	{
		byte other[CHIM_HEADER_BYTES + CHIM_FRAME_BYTES];
		chim_header_t oh;
		chim_frame_t of;
		chim_pack_t *op;
		if (strcmp (chim_world.file[i].kind, "FRAM"))
			continue;
		if (!(op = Chim_File (i)) || !Chim_PackRead (op, 0, other, sizeof(other)) ||
			!ChimFormat_Header (other, op->bytes, "FRAM", &oh) || !ChimFormat_Frame (other + CHIM_HEADER_BYTES, &of))
			return 0;
		chim_frame.first_pid += of.owned_total;
	}
	if (!(pack = Chim_File (row)))
		return 0;
	n = (int)h.count;
	cells = chim_frame.frame.nx * chim_frame.frame.ny;
	sectors = cells / (chim_frame.frame.sector_chunks * chim_frame.frame.sector_chunks);
	if (n < 1 || n > CHIM_MAX_CHUNKS || n != cells || chim_frame.frame.grain != chim_world.settings.grain ||
		chim_frame.frame.cx != cx || chim_frame.frame.cy != cy ||
		chim_frame.frame.sector_chunks != chim_world.settings.sector_chunks ||
		h.directory != CHIM_HEADER_BYTES + CHIM_FRAME_BYTES || h.directory + (unsigned)n*CHIM_CHUNK_ENTRY_BYTES != h.data ||
		h.data + (unsigned)sectors*CHIM_SECTOR_ENTRY_BYTES != h.bytes ||
		chim_frame.frame.owned_total > 0x7fffffffu - 7)
		return 0;
	bits = (int)((chim_frame.frame.owned_total + 7) / 8);
	size = n*sizeof(chim_entry_t) + cells*sizeof(short) + 2*bits;
	if (!ChimZone_Alloc (&index_user, size, CHIM_KIND_INDEX, 1))
		return 0;
	ChimZone_Lock (index_user.data);
	chim_frame.entries = index_user.data;
	grid = (short *)(chim_frame.entries + n);
	chim_frame.drawn = (unsigned char *)(grid + cells);
	chim_frame.visible = chim_frame.drawn + bits;
	chim_frame.view_entry = -2;
	for (i=0 ; i<cells ; i++)
		grid[i] = -1;
	for (i=0 ; i<n ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		unsigned bytes;
		if (!(i % per) && (!(pack = Chim_File (row)) || !Chim_PackRead (pack, h.directory + i*CHIM_CHUNK_ENTRY_BYTES,
			raw, (long)((n - i < per ? n - i : per) * CHIM_CHUNK_ENTRY_BYTES))))
			return 0;
		ChimFormat_ChunkEntry (raw + (i % per)*CHIM_CHUNK_ENTRY_BYTES, &e->disk);
		e->file = e->disk.sector < sectors ? Chim_FileRow ("SECT", cx, cy, e->disk.sector) : -1;
		if (e->file < 0 || e->disk.cx >= chim_frame.frame.nx || e->disk.cy >= chim_frame.frame.ny)
			return 0;
		bytes = chim_world.file[e->file].bytes;
		if (grid[e->disk.cy*chim_frame.frame.nx + e->disk.cx] >= 0 || e->disk.offset < CHIM_HEADER_BYTES ||
			(e->disk.offset & 3) || e->disk.offset > bytes ||
			e->disk.render < CHIM_CHUNK_HEAD_BYTES || e->disk.render > bytes - e->disk.offset ||
			e->disk.collision > bytes - e->disk.offset - e->disk.render ||
			e->disk.owned + e->disk.reach > CHIM_MAX_RECORDS)
			return 0;
		grid[e->disk.cy*chim_frame.frame.nx + e->disk.cx] = (short)i;
		e->low[0] = chim_frame.frame.low[0] + e->disk.cx*chim_frame.frame.grain;
		e->low[1] = chim_frame.frame.low[1] + e->disk.cy*chim_frame.frame.grain;
		e->high[0] = e->low[0] + chim_frame.frame.grain;
		e->high[1] = e->low[1] + chim_frame.frame.grain;
		e->distance = e->priority = 1e30f;
		e->graft = -1;
	}
	chim_frame.count = n;
	ticks = 0;
	memset (&ring, 0, sizeof(ring));
	ring.margin = ring.margin_min = -1;
	return 1;
}

/* ---------------------------------------------------------------- linking */

static int LinksValid (void)
{
	return link_world && cls.signon == SIGNONS && cl.worldmodel == link_world;
}

static int CountLeaves (const entity_t *ent)
{
	const efrag_t *ef;
	int n = 0;
	for (ef=ent->efrag ; ef ; ef=ef->entnext)
		n++;
	return n;
}

/* R_AddEfrags with an explicit drawn box: R_AddEfrags uses the model's
 * unrotated bounds, which miss leaves of a yawed placement. */
static int AddEfrags (entity_t *ent, const vec3_t mins, const vec3_t maxs)
{
	r_addent = ent;
	ent->efrag = NULL;
	lastlink = &ent->efrag;
	r_pefragtopnode = NULL;
	VectorCopy (mins, r_emins);
	VectorCopy (maxs, r_emaxs);
	R_SplitEntityOnNode (cl.worldmodel->nodes);
	ent->topnode = r_pefragtopnode;
	return CountLeaves (ent);
}

/* A chunk whose placements may be linked: active and, with the incremental
 * frame world, grafted (its leaves exist). */
static int Linkable (int index)
{
	chim_entry_t *e = &chim_frame.entries[index];
	return e->state == CHIM_STATE_ACTIVE && (e->grafted || !ChimGraft_Incremental ());
}

static void DropEfrags (entity_t *ent)
{
	if (ent->efrag && LinksValid ())
		ChimGraft_RemoveEfrags (ent);
	ent->efrag = NULL;
}

/* A placement's bit in the frame's rows: its id less the frame's first. */
static unsigned Local (unsigned pid)
{
	return pid - chim_frame.first_pid;
}

/* The opening story hides some placements (aw_opening.c's rule for
 * "aw_story_hidden"): not drawn, not solid. */
int (*chim_story_hidden)(void);

static int Hidden (const chim_place_t *p)
{
	return (p->flags & CHIM_RECORD_STORY_HIDDEN) && chim_story_hidden && chim_story_hidden ();
}

static void SetDrawn (unsigned pid, int on)
{
	pid = Local (pid);
	if (on)
		chim_frame.drawn[pid>>3] |= (unsigned char)(1u << (pid & 7));
	else
		chim_frame.drawn[pid>>3] &= (unsigned char)~(1u << (pid & 7));
}

static int Drawn (unsigned pid)
{
	pid = Local (pid);
	return (chim_frame.drawn[pid>>3] >> (pid & 7)) & 1;
}

static void Unlink (chim_place_t *p)
{
	if (!p->linked)
		return;
	if (p->leaves)
	{
		counts.efrags -= p->leaves;
		if (p->leaves == 1)
			counts.one_leaf--;
	}
	DropEfrags (&p->ent);
	p->leaves = 0;
	p->linked = 0;
	counts.placements_linked--;
	SetDrawn (p->pid, 0);
}

/* The owner chunk of a reach copy draws the placement: it is active and,
 * when partially active, holds the placement's model. */
static int OwnerDraws (const chim_place_t *p)
{
	chim_entry_t *o = &chim_frame.entries[p->owner];
	chim_chunk_t *c;
	int j;
	if (o->state != CHIM_STATE_ACTIVE)
		return 0;
	if (!o->partial)
		return 1;
	c = o->chunk.data;
	for (j=0 ; j<c->owned ; j++)
		if (c->places[j].pid == p->pid)
			return c->places[j].ent.model != NULL;
	return 0;
}

/* Each placement drawn and collided once: by its owner chunk when that is
 * active (and holds its model), else by the first active chunk holding a
 * reach copy of it. */
static void Reconcile (void)
{
	int i, j;
	chim_chunk_t *c;

	counts.reconciles++;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		c = chim_frame.entries[i].chunk.data;
		for (j=c->owned ; j<c->records ; j++)
			if (c->places[j].linked && OwnerDraws (&c->places[j]))
				Unlink (&c->places[j]);
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		c = chim_frame.entries[i].chunk.data;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (p->linked || Drawn (p->pid) || Hidden (p) || !p->ent.model)
				continue;
			if (j >= c->owned && OwnerDraws (p))
				continue;
			p->linked = 1;
			counts.placements_linked++;
			SetDrawn (p->pid, 1);
		}
	}
}

/* The view chunk's placement row (format 0.3), decompressed: Quake's zero
 * runs as in Mod_DecompressVis. Returns 0 when the row is missing or bad
 * (then every linked placement is drawn). */
static int ViewRow (int entry)
{
	chim_chunk_t *c;
	int nbytes = (int)((chim_frame.frame.owned_total + 7) >> 3), out = 0, in = 0, k;
	if (entry < 0 || chim_frame.entries[entry].state != CHIM_STATE_ACTIVE)
		return 0;
	c = chim_frame.entries[entry].chunk.data;
	if (!c->pvl_bytes)
		return 0;
	while (out < nbytes)
	{
		if (in >= c->pvl_bytes)
			return 0;
		if (c->pvl[in])
		{
			chim_frame.visible[out++] = c->pvl[in++];
			continue;
		}
		if (in + 1 >= c->pvl_bytes || out + c->pvl[in+1] > nbytes)
			return 0;
		for (k=c->pvl[in+1] ; k ; k--)
			chim_frame.visible[out++] = 0;
		in += 2;
	}
	return in == c->pvl_bytes;
}

static int ViewSees (const chim_place_t *p)
{
	unsigned bit = Local (p->pid);	/* bit k of the row = the frame's first id + k */
	if (chim_frame.view_entry < 0)
		return 1;
	return bit < chim_frame.frame.owned_total && ((chim_frame.visible[bit >> 3] >> (bit & 7)) & 1);
}

static int ViewEntry (void)
{
	const float *o;
	int x, y;
	if (cl.viewentity <= 0 || cl.viewentity >= MAX_EDICTS)
		return -1;
	o = cl_entities[cl.viewentity].origin;
	if (o[0] < chim_frame.frame.low[0] || o[1] < chim_frame.frame.low[1])
		return -1;
	x = (int)((o[0] - chim_frame.frame.low[0]) / chim_frame.frame.grain);
	y = (int)((o[1] - chim_frame.frame.low[1]) / chim_frame.frame.grain);
	return ChimChunks_CellEntry (x, y);
}

/* Client side, once per frame: efrags for what Reconcile linked and the
 * view chunk's placement list allows. Placements outside the list keep
 * their collision; they are only not drawn (format 0.3 placement lists). */
void ChimChunks_Link (void)
{
	int i, j, view;
	chim_entry_t *e;
	chim_chunk_t *c;

	if (cls.signon != SIGNONS || !cl.worldmodel)
		return;
	if (cl.worldmodel != link_world)
	{
		/* A new client map reset the efrag pool: forget the old links. */
		for (i=0 ; i<chim_frame.count ; i++)
		{
			e = &chim_frame.entries[i];
			if (e->state != CHIM_STATE_ACTIVE)
				continue;
			c = e->chunk.data;
			for (j=0 ; j<c->records ; j++)
			{
				c->places[j].ent.efrag = NULL;
				c->places[j].leaves = 0;
			}
		}
		counts.efrags = counts.one_leaf = 0;
		link_world = cl.worldmodel;
	}
	view = ViewEntry ();
	if (view != chim_frame.view_entry && view >= 0 && chim_frame.entries[view].state == CHIM_STATE_ACTIVE)
		chim_frame.view_entry = ViewRow (view) ? view : -1;
	else if (view < 0 || chim_frame.entries[view].state != CHIM_STATE_ACTIVE)
		chim_frame.view_entry = -1;
	counts.hidden = 0;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		e = &chim_frame.entries[i];
		if (e->state != CHIM_STATE_ACTIVE)
			continue;
		c = e->chunk.data;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked)
				continue;
			/* Incremental frame world: a chunk waiting for its ground is
			 * drawn once grafted (it is at the ring's edge), so its
			 * placements are not linked into the grid's empty leaves
			 * only to be linked again a frame later. */
			if (!e->grafted && ChimGraft_Incremental ())
				continue;
			if (!ViewSees (p))
			{
				counts.hidden++;
				if (p->leaves)
				{
					counts.efrags -= p->leaves;
					if (p->leaves == 1)
						counts.one_leaf--;
					DropEfrags (&p->ent);
					p->leaves = 0;
				}
				continue;
			}
			if (p->leaves)
				continue;
			p->leaves = AddEfrags (&p->ent, p->mins, p->maxs);
			counts.efrags += p->leaves;
			if (p->leaves == 1)
				counts.one_leaf++;
			if (p->leaves > counts.max_leaves)
				counts.max_leaves = p->leaves;
		}
	}
	/* Streamed statics (chim_statics.c): placed while their chunk is active. */
	ChimStatics_Link (AddEfrags, Linkable);
}

/* ---------------------------------------------------------------- catalogue */

static void ChunkEvicted (void *data, unsigned id)
{
	(void)data;
	if (id >= (unsigned)chim_frame.count)
		return;
	if (chim_frame.entries[id].state == CHIM_STATE_ACTIVE)
		Sys_Error ("CHIM: active chunk %lu evicted", (unsigned long)id);
	if (chim_frame.entries[id].state == CHIM_STATE_LOADED)
		chim_frame.loaded--;
	chim_frame.entries[id].state = CHIM_STATE_ABSENT;
	chim_frame.entries[id].ready = 0;
}

/* Read the chunk head and its placement records; one catalogue block holds
 * the chunk, a run-time placement per record and its distinct models. */
static int LoadCatalogue (int index, long *budget)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_head_t head;
	chim_record_t r;
	chim_chunk_t *c;
	chim_pack_t *pack = Chim_File (e->file);
	byte *raw = chim_world.buffer;
	int i, j, n, per = chim_world.buffer_bytes / CHIM_RECORD_BYTES;

	if (!pack || !Chim_PackRead (pack, e->disk.offset, raw, CHIM_CHUNK_HEAD_BYTES) ||
		!ChimFormat_ChunkHead (raw, &head) || head.owned != e->disk.owned || head.reach != e->disk.reach)
		return -1;
	n = head.owned + head.reach;
	if (head.image_at < (unsigned)(CHIM_CHUNK_HEAD_BYTES + n*CHIM_RECORD_BYTES + head.pvs_bytes + head.pvl_bytes) ||
		head.image_at + head.image_render != e->disk.render)
		return -1;
	c = ChimZone_Alloc (&e->chunk, sizeof(*c) + n*(sizeof(chim_place_t) + sizeof(chim_chunk_model_t)) +
		head.pvs_bytes + head.pvl_bytes, CHIM_KIND_CHUNK, (unsigned)index);
	if (!c)
		return -1;
	c->entry = index;
	c->records = n;
	c->owned = head.owned;
	c->places = (chim_place_t *)(c+1);
	c->model_list = (chim_chunk_model_t *)(c->places + n);
	*budget -= CHIM_CHUNK_HEAD_BYTES;
	for (i=0 ; i<n ; i++)
	{
		chim_place_t *p = &c->places[i];
		if (!(i % per))
		{
			int take = n - i < per ? n - i : per;
			if (!(pack = Chim_File (e->file)) ||
				!Chim_PackRead (pack, e->disk.offset + CHIM_CHUNK_HEAD_BYTES + i*CHIM_RECORD_BYTES,
				raw, (long)take*CHIM_RECORD_BYTES))
				goto bad;
			*budget -= (long)take*CHIM_RECORD_BYTES;
		}
		if (!ChimFormat_Record (raw + (i % per)*CHIM_RECORD_BYTES, &r) || r.pid < chim_frame.first_pid ||
			r.pid - chim_frame.first_pid >= chim_frame.frame.owned_total ||
			r.owner >= chim_frame.count || (i < head.owned) != (r.owner == index))
			goto bad;
		p->pid = r.pid;
		p->flags = r.flags;
		p->model = r.model;
		p->owner = r.owner;
		VectorCopy (r.origin, p->ent.origin);
		p->ent.angles[YAW] = r.yaw;
		p->ent.colormap = vid.colormap;
		Q_SinCosDeg (r.yaw, &p->s, &p->c);
		/* The record's drawn box (the AW_SceneryCapture box, rounded
		 * outward) serves efrags and the collision broadphase. */
		for (j=0 ; j<3 ; j++)
		{
			p->mins[j] = r.mins[j];
			p->maxs[j] = r.maxs[j];
		}
		if (r.flags & CHIM_RECORD_OVER_16_LEAVES)
			c->over_16_leaves++;
		for (j=0 ; j<c->models && c->model_list[j].id != r.model ; j++)
			;
		if (j == c->models)
			c->model_list[c->models++].id = r.model;
	}
	/* The PVS row follows the records; it moves up behind the model list. */
	c->pvs = (byte *)(c->model_list + c->models);
	c->pvs_bytes = head.pvs_bytes;
	c->pvl = c->pvs + head.pvs_bytes;
	c->pvl_bytes = head.pvl_bytes;
	c->terrain_leaves = head.terrain_leaves;
	if (head.pvs_bytes + head.pvl_bytes)
	{
		if (!(pack = Chim_File (e->file)) ||
			!Chim_PackRead (pack, e->disk.offset + CHIM_CHUNK_HEAD_BYTES + n*CHIM_RECORD_BYTES,
			c->pvs, head.pvs_bytes + head.pvl_bytes))
			goto bad;
		*budget -= head.pvs_bytes + head.pvl_bytes;
	}
	ChimZone_Trim (c, sizeof(*c) + n*sizeof(chim_place_t) + c->models*sizeof(chim_chunk_model_t) +
		head.pvs_bytes + head.pvl_bytes);
	e->state = CHIM_STATE_LOADED;
	chim_frame.loaded++;
	chim_world.chunk_loads++;
	return 1;
bad:
	ChimZone_Free (&e->chunk);
	return -1;
}

/* Lock what the chunk uses and instantiate its placements. Returns 0 when a
 * model or the terrain is not resident (the caller loads it first). With
 * partial set, only the terrain must be resident: a placement whose model
 * is missing stays out (not drawn, not solid) until Complete finds it. */
static int Activate (int index, int partial)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	chim_model_t *terrain = ChimModels_Terrain (index);
	int i, j, k, missing = 0;

	e->ready = 0;
	if (!terrain)
		return 0;
	for (i=0 ; i<c->models ; i++)
		if (!(c->model_list[i].model = ChimModels_Find (c->model_list[i].id)))
		{
			if (!partial)
				return 0;
			missing++;
		}
	e->ready = !missing;
	e->partial = missing != 0;
	ChimZone_Lock (c);
	ChimZone_Lock (terrain);
	VectorCopy (terrain->model.mins, c->mins);
	VectorCopy (terrain->model.maxs, c->maxs);
	if (terrain->leafs - 1 != c->terrain_leaves)
		Con_DPrintf ("CHIM: chunk %ld terrain leaves differ from its head\n", (long)index);
	for (i=0 ; i<c->models ; i++)
		if (c->model_list[i].model)
			ChimZone_Lock (c->model_list[i].model);
	for (i=0 ; i<c->records ; i++)
	{
		chim_place_t *p = &c->places[i];
		for (j=0 ; c->model_list[j].id != p->model ; j++)
			;
		p->ent.model = c->model_list[j].model ? &c->model_list[j].model->model : NULL;
		p->ent.efrag = NULL;
		p->linked = p->leaves = 0;
		for (k=0 ; k<3 ; k++)
		{
			if (p->mins[k] < c->mins[k]) c->mins[k] = p->mins[k];
			if (p->maxs[k] > c->maxs[k]) c->maxs[k] = p->maxs[k];
		}
	}
	/* Its streamed statics whose models are resident; the rest follow
	 * (Complete) like a partial chunk's models. */
	if (ChimStatics_Activate (index))
	{
		missing++;
		e->ready = 0;
		e->partial = 1;
	}
	if (missing)
		pressure.partial++;
	e->state = CHIM_STATE_ACTIVE;
	chim_frame.active++;
	counts.activations++;
	world_dirty = 1;
	return 1;
}

static void Deactivate (int index)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	int i;

	for (i=0 ; i<c->records ; i++)
	{
		Unlink (&c->places[i]);
		c->places[i].ent.model = NULL;
	}
	ChimStatics_Deactivate (index);
	for (i=0 ; i<c->models ; i++)
	{
		if (c->model_list[i].model)
			ChimZone_Unlock (c->model_list[i].model);
		c->model_list[i].model = NULL;
	}
	ChimZone_Unlock (e->terrain.data);
	ChimZone_Unlock (c);
	e->partial = 0;
	e->ready = 0;
	e->state = CHIM_STATE_LOADED;
	chim_frame.active--;
	counts.deactivations++;
	world_dirty = 1;
}

/* A partially active chunk: lock the models that have arrived since and
 * give their placements their model; Reconcile links them. Returns 1 when
 * any placement got its model. */
static int Complete (int index)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	int i, j, added = 0, missing = 0;

	for (i=0 ; i<c->models ; i++)
	{
		if (c->model_list[i].model)
			continue;
		if (!(c->model_list[i].model = ChimModels_Find (c->model_list[i].id)))
		{
			missing++;
			continue;
		}
		ChimZone_Lock (c->model_list[i].model);
		for (j=0 ; j<c->records ; j++)
			if (c->places[j].model == c->model_list[i].id)
			{
				c->places[j].ent.model = &c->model_list[i].model->model;
				added = 1;
			}
	}
	{
		/* Streamed statics whose models arrived are placed (and linked by
		 * ChimChunks_Link); the count is what still waits. */
		int before = ChimStatics_Missing (index) != 0;
		int waiting = ChimStatics_Activate (index);
		if (before && !waiting)
			added = 1;
		missing += waiting;
	}
	e->partial = missing != 0;
	e->ready = !missing;
	return added;
}

/* ---------------------------------------------------------------- the ring */

static float Distance (const chim_entry_t *e, const float *p)
{
	float dx = p[0] < e->low[0] ? e->low[0] - p[0] : p[0] > e->high[0] ? p[0] - e->high[0] : 0;
	float dy = p[1] < e->low[1] ? e->low[1] - p[1] : p[1] > e->high[1] ? p[1] - e->high[1] : 0;
	/* Compared against radii squared: no square root. */
	return dx*dx + dy*dy;
}

/* What the chunk still needs: 1 catalogue, 2 terrain, 3 a model, 4 activation,
 * 5 completion (a partially active chunk whose missing models arrived), 0 nothing. */
unsigned long chim_need_calls;	/* scheduler work, for the tests */

static int Need (int index, float active2, unsigned *model)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c;
	int i;
	chim_need_calls++;
	if (e->state == CHIM_STATE_ACTIVE)
	{
		if (!e->partial)
			return 0;
		c = e->chunk.data;
		for (i=0 ; i<c->models ; i++)
			if (!c->model_list[i].model && !ChimModels_Find (c->model_list[i].id))
			{
				*model = c->model_list[i].id;
				return 3;
			}
		if ((*model = ChimStatics_Missing (index)) != 0)
			return 3;
		return 5;
	}
	if (e->state == CHIM_STATE_ABSENT || !e->chunk.data)
		return 1;
	if (!ChimModels_Terrain (index))
		return 2;
	c = e->chunk.data;
	/* A prefetched chunk outside the active ring that was complete stays
	 * so as far as scheduling goes; Activate checks again. */
	if (e->ready && e->distance > active2)
		return 0;
	for (i=0 ; i<c->models ; i++)
		if (!ChimModels_Find (c->model_list[i].id))
		{
			e->ready = 0;
			*model = c->model_list[i].id;
			return 3;
		}
	if ((*model = ChimStatics_Missing (index)) != 0)
	{
		e->ready = 0;
		return 3;
	}
	e->ready = 1;
	return e->distance <= active2 ? 4 : 0;
}

/* The frame world follows the active set. An update that finds no room
 * waits 25 ticks: each try may evict prefetched data to make room. Phase 0
 * (after chunks left): give their terrain back; 1 (end of a tick): join
 * within the per-frame budget, more next tick; 2 (prime): everything. */
static void Graft (int phase)
{
	int r;
	if (!world_dirty || ticks < world_retry)
		return;
	r = ChimGraft_Update (phase);
	if (r == 1)
		world_dirty = 0;
	else if (!r)
		world_retry = ticks + 25;
}

/* Prefetch (work for a chunk beyond the active ring) goes only into free
 * room: twice the bytes it reads next, plus 64 KiB, must fit the largest
 * free block, so it never evicts. With eviction, two prefetched chunks whose
 * models do not fit together evicted each other's models in turn, reading
 * all the time while standing still (CHIM-ZONE-RING-THRASH-33). Chunks in
 * the active ring still evict, least recently used first. */
static unsigned long	prefetch_held;
static int PrefetchRoom (int index, int need, unsigned model, float active2)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_zone_stats_t s;
	long bytes;
	if (!chim_prefetch_room.value || e->distance <= active2)
		return 1;
	if (need == 1)
		bytes = 16384;
	else if (need == 2)
		bytes = (long)e->disk.render + e->disk.collision;
	else if (need == 3 && ChimStatics_IsStatic (model))
		bytes = ChimStatics_Bytes (model);
	else if (need == 3)
		bytes = model < chim_world.models ? (long)chim_world.model[model].bytes : 0;
	else
		return 1;
	ChimZone_Stats (&s);
	if (s.largest_free >= 2*bytes + 65536)
		return 1;
	prefetch_held++;
	return 0;
}

unsigned long ChimChunks_PrefetchHeld (void)
{
	return prefetch_held;
}

static void MapLine (const char *line)
{
	Con_Printf ("CHIM zone %s\n", line);
}

/* A chunk that could not be loaded waits (50 ticks; one tick for a chunk
 * without its ground within the collision margin, with chim_release), or
 * less: every release of an active chunk lets the waiting ones try again
 * (Released). The line
 * says which part failed and why: the zone had no room (with the request
 * and what the zone holds), or the data did not decode. */
static void Failed (int index, int need, unsigned model, int zone, int asked, int wait)
{
	static const char *part[] = {"", "catalogue", "terrain", "model", "", ""};
	chim_zone_stats_t s;
	chim_entry_t *e = &chim_frame.entries[index];
	e->failed_until = ticks + wait;
	chim_world.failed_loads++;
	if (zone)
		pressure.zone++;
	else
		pressure.data++;
	/* One line per chunk and 50 ticks: a chunk that tries again every tick
	 * does not fill the console. */
	if (e->failed_said && ticks + 1 < e->failed_said + 50)
		return;
	e->failed_said = ticks + 1;
	if (!zone)
	{
		if (need == 3 && ChimStatics_IsStatic (model))
			Con_Printf ("CHIM: chunk %ld: streamed static model %s unavailable; its statics stay out\n", (long)index, ChimStatics_Name (model));
		else if (need == 3)
			Con_Printf ("CHIM: chunk %ld not loaded: bad data in model %lu; retrying\n", (long)index, (unsigned long)model);
		else
			Con_Printf ("CHIM: chunk %ld not loaded: bad data in its %s; retrying\n", (long)index, part[need]);
		return;
	}
	ChimZone_Stats (&s);
	/* The zone's layout with the first such failure of a map (all of them
	 * with chim_debug): where the locked blocks split the room. */
	if (!counts.zone_maps++ || chim_debug.value)
		ChimZone_Map (MapLine);
	if (need == 3 && ChimStatics_IsStatic (model))
		Con_Printf ("CHIM: chunk %ld: streamed static model %s waits: zone full (%ld bytes; largest free %ld, free %ld, locked %ld of %ld); retrying\n",
			(long)index, ChimStatics_Name (model), (long)asked, (long)s.largest_free, (long)s.free_bytes, (long)s.locked_bytes,
			(long)(s.used_bytes + s.free_bytes));
	else if (need == 3)
		Con_Printf ("CHIM: chunk %ld not loaded: zone full (model %lu, %ld bytes; largest free %ld, free %ld, locked %ld of %ld); retrying\n",
			(long)index, (unsigned long)model, (long)asked, (long)s.largest_free, (long)s.free_bytes, (long)s.locked_bytes,
			(long)(s.used_bytes + s.free_bytes));
	else
		Con_Printf ("CHIM: chunk %ld not loaded: zone full (its %s, %ld bytes; largest free %ld, free %ld, locked %ld of %ld); retrying\n",
			(long)index, part[need], (long)asked, (long)s.largest_free, (long)s.free_bytes, (long)s.locked_bytes,
			(long)(s.used_bytes + s.free_bytes));
}

/* An active chunk went: chunks waiting after a failed load try again now. */
static void Released (void)
{
	int i;
	for (i=0 ; i<chim_frame.count ; i++)
		chim_frame.entries[i].failed_until = 0;
}

/* The zone has no room for chunk index (within the active radius): release
 * the active chunk farthest from the player that is farther than it and
 * outside the collision margin, so the nearer chunk wins (chim_release).
 * Chunks past the active radius (kept only by the load radius's
 * hysteresis) go first, being the farthest. Returns 1 when one went. */
static int Release (int index, float active2, float urgent2)
{
	int i, far = -1;
	float d = chim_frame.entries[index].distance;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		if (e->state != CHIM_STATE_ACTIVE || e->distance <= d || e->distance <= urgent2)
			continue;
		if (far < 0 || e->distance > chim_frame.entries[far].distance)
			far = i;
	}
	if (far < 0)
		return 0;
	if (chim_frame.entries[far].distance > active2)
		pressure.band++;
	else
	{
		pressure.ring++;
		if (chim_debug.value)
			Con_Printf ("CHIM: zone full: chunk %ld released for nearer chunk %ld\n", (long)far, (long)index);
	}
	Deactivate (far);
	/* Not active again for 50 ticks (unless the player comes within the
	 * collision margin of it): else the next nearer chunk short of room
	 * releases it again at once, and loads chase each other. */
	chim_frame.entries[far].released_until = ticks + 50;
	Reconcile ();
	/* Its terrain leaves the frame world now, which drops the world's lock. */
	ChimGraft_Update (0);
	Released ();
	return 1;
}

static short	candidate[CHIM_MAX_CHUNKS];

/* Lock (on) or unlock what chunk index has in the zone: its catalogue,
 * its terrain and its resident models (index < 0: nothing). Between the
 * two calls nothing may be loaded or evicted but by the zone itself. */
#define CHIM_MAX_PIN	256		/* past this many models a chunk pins only the first */
static void			*pinned[CHIM_MAX_PIN];
static int			npinned;
static void Pin (int index, int on)
{
	chim_entry_t *e;
	chim_chunk_t *c;
	int i;
	if (index < 0)
		return;
	if (!on)
	{
		for (i=0 ; i<npinned ; i++)
			ChimZone_Unlock (pinned[i]);
		npinned = 0;
		return;
	}
	e = &chim_frame.entries[index];
	c = e->chunk.data;
	npinned = 0;
	if (c)
		pinned[npinned++] = c;
	if (e->terrain.data && ChimModels_Terrain (index))
		pinned[npinned++] = e->terrain.data;
	for (i=0 ; c && i<c->models && npinned<CHIM_MAX_PIN ; i++)
	{
		chim_model_t *m = ChimModels_Find (c->model_list[i].id);
		if (m)
			pinned[npinned++] = m;
	}
	for (i=0 ; i<npinned ; i++)
		ChimZone_Lock (pinned[i]);
}

/* A chunk within the collision margin still needs work. */
static int UrgentPending (int candidates, float urgent2)
{
	int j;
	unsigned model;
	for (j=0 ; j<candidates ; j++)
	{
		chim_entry_t *e = &chim_frame.entries[candidate[j]];
		if ((e->state != CHIM_STATE_ACTIVE || e->partial) && e->distance <= urgent2 && Need (candidate[j], 1e30f, &model))
			return 1;
	}
	return 0;
}

/* The safety margin: how far the nearest chunk of the frame without its
 * ground in the frame world is (0: the player stands on one). */
static void Margin (void)
{
	float nearest = 1e30f;
	int i;
	for (i=0 ; i<chim_frame.count ; i++)
		if (!chim_frame.entries[i].grafted && chim_frame.entries[i].distance < nearest)
			nearest = chim_frame.entries[i].distance;
	ring.margin = nearest >= 1e30f ? -1 : (float)sqrt (nearest);
	if (ring.margin >= 0 && (ring.margin_min < 0 || ring.margin < ring.margin_min))
		ring.margin_min = ring.margin;
}

/* The smallest safety margin since the last call (units; -1: every chunk
 * grafted), the loads made past the budget, and whether there is a point
 * ahead (the player moves). */
void ChimChunks_Streaming (int *margin, unsigned long *urgent_loads, int *ahead)
{
	*margin = ring.margin_min < 0 ? -1 : (int)ring.margin_min;
	*urgent_loads = ring.urgent_loads;
	*ahead = ring.has_ahead;
	ring.margin_min = ring.margin;
}

/* The ring's radii: chunks within the active radius are active (drawn,
 * solid); within the load radius they are loaded (the prefetch margin, also
 * the hysteresis before a chunk is released). The active radius follows
 * the view distance (chim_draw_distance 0) plus the world's hysteresis. */
float ChimChunks_ActiveRadius (void)
{
	return (chim_draw_distance.value > 0 ? chim_draw_distance.value : Chim_ViewDistance ()) +
		chim_frame.settings.hysteresis;
}

float ChimChunks_LoadRadius (void)
{
	return ChimChunks_ActiveRadius () + (chim_prefetch.value >= 0 ? chim_prefetch.value : chim_frame.settings.prefetch_margin);
}

/* Which way the player moves: the step since the last tick (a step of a
 * chunk or more is a teleport, not a direction). The point ahead is the
 * look-ahead distance (chim_lookahead; -1: the prefetch margin) that way;
 * standing still, there is none. */
static void Ahead (const vec3_t origin)
{
	vec3_t step;
	float length, look = chim_lookahead.value >= 0 ? chim_lookahead.value : chim_frame.settings.prefetch_margin;
	VectorSubtract (origin, ring.last, step);
	step[2] = 0;
	length = (float)sqrt (step[0]*step[0] + step[1]*step[1]);
	ring.has_ahead = 0;
	if (ring.moved && length > 0.5f && length < chim_frame.frame.grain && look > 0)
	{
		ring.ahead[0] = origin[0] + step[0] / length * look;
		ring.ahead[1] = origin[1] + step[1] / length * look;
		ring.ahead[2] = origin[2];
		ring.has_ahead = 1;
	}
	VectorCopy (origin, ring.last);
	ring.moved = 1;
}

void ChimChunks_Tick (const vec3_t origin, long budget, int prime)
{
	float load2, active2, urgent2, r, ahead;
	int i, j, k, best, need, changed = 0, guard, candidates = 0, result, pin;
	unsigned model = 0;
	unsigned long zone_before;

	if (!chim_frame.count)
		return;
	r = ChimChunks_ActiveRadius ();
	active2 = r*r;
	r = ChimChunks_LoadRadius ();
	load2 = r*r;
	urgent2 = chim_frame.settings.collision_margin * chim_frame.settings.collision_margin;
	Ahead (origin);
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		e->distance = e->priority = Distance (e, origin);
		if (ring.has_ahead && (ahead = Distance (e, ring.ahead)) < e->priority)
			e->priority = ahead;
		if (e->state == CHIM_STATE_ACTIVE && e->distance > load2)
		{
			Deactivate (i);
			changed = 1;
		}
	}
	if (changed)
	{
		Reconcile ();
		Released ();
	}
	/* Before anything is loaded: a deactivated chunk's terrain must not be
	 * evicted while the world still points into it (the world holds its
	 * own locks, released by the update). */
	Graft (prime ? 2 : 0);
	changed = 0;
	/* The chunks within the load radius of the player or of the point ahead
	 * that are not active, by priority (the nearer of the two distances;
	 * insertion sort: a ring holds a few dozen). */
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		if (e->priority > load2 || (e->state == CHIM_STATE_ACTIVE && !e->partial))
			continue;
		for (k=candidates ; k>0 && chim_frame.entries[candidate[k-1]].priority > e->priority ; k--)
			candidate[k] = candidate[k-1];
		candidate[k] = (short)i;
		candidates++;
	}
	if (prime && chim_debug.value)
		Con_Printf ("CHIM: %ld candidates\n", (long)candidates);
	for (guard=0 ; guard<4*CHIM_MAX_CHUNKS ; guard++)
	{
		/* Past the budget only for a chunk within the collision margin:
		 * the ground under the player never waits for a later frame. */
		int urgent = !prime && budget <= 0;
		if (prime && chim_debug.value && !(guard % 64))
			Con_Printf ("CHIM: step %ld: %ld active, %ld loaded, %lu models\n",
				(long)guard, (long)chim_frame.active, (long)chim_frame.loaded, chim_world.model_loads);
		if (ChimModels_Busy ())
		{
			/* A stream in progress continues before anything else. */
			if (urgent && !UrgentPending (candidates, urgent2))
				break;
			if (urgent)
				ring.urgent_loads++;
			if (ChimModels_Step ((unsigned)-1, &budget) < 0)
				break;
			continue;
		}
		best = -1;
		need = 0;
		for (j=0 ; j<candidates && best < 0 ; j++)
		{
			i = candidate[j];
			if ((chim_frame.entries[i].state == CHIM_STATE_ACTIVE && !chim_frame.entries[i].partial) ||
				ticks < chim_frame.entries[i].failed_until ||
				(chim_frame.entries[i].state != CHIM_STATE_ACTIVE && ticks < chim_frame.entries[i].released_until &&
				chim_frame.entries[i].distance > urgent2))
				continue;
			if (urgent && chim_frame.entries[i].distance > urgent2)
				continue;
			if ((need = Need (i, active2, &model)) != 0 && PrefetchRoom (i, need, model, active2))
				best = i;
		}
		if (best < 0)
			break;
		if (urgent)
			ring.urgent_loads++;
		if (chim_debug.value >= 2)
			Con_Printf ("CHIM: chunk %ld need %ld model %lu\n", (long)best, (long)need, (unsigned long)model);
		zone_before = ChimZone_Failures (NULL);
		result = 0;
		switch (need)
		{
		case 1:
			result = LoadCatalogue (best, &budget);
			break;
		case 2:
			/* With chim_release, a chunk the player can see keeps what it
			 * has while it loads the rest (Pin): making room for its
			 * terrain or one model must not evict its catalogue, terrain or
			 * another of its models. The first method could, and a chunk
			 * whose models did not fit together evicted them in turn,
			 * loading for ever. */
			pin = chim_release.value && chim_frame.entries[best].distance <= active2 ? best : -1;
			Pin (pin, 1);
			result = ChimModels_TerrainStep (best, &budget);
			Pin (pin, 0);
			break;
		case 3:
			pin = chim_release.value && chim_frame.entries[best].distance <= active2 ? best : -1;
			Pin (pin, 1);
			result = ChimStatics_IsStatic (model) ? ChimStatics_Step (model, &budget) : ChimModels_Step (model, &budget);
			Pin (pin, 0);
			break;
		case 4:
			if (Activate (best, 0))
				changed = 1;
			break;
		case 5:
			if (Complete (best))
				changed = 1;
			break;
		}
		if (result < 0)
		{
			chim_entry_t *e = &chim_frame.entries[best];
			int asked, zone = ChimZone_Failures (&asked) != zone_before;
			/* No room for a chunk the player can see: farther chunks give
			 * theirs (chim_release), and the same chunk tries again. */
			if (zone && chim_release.value && e->distance <= active2 && Release (best, active2, urgent2))
				continue;
			Failed (best, need, model, zone, asked,
				chim_release.value && e->distance <= urgent2 && e->state != CHIM_STATE_ACTIVE ? 1 : 50);
			/* Its ground and its other placements do not wait for a model
			 * that has no room (chim_partial): never a hole to fall into. */
			if (need == 3 && chim_partial.value && e->state == CHIM_STATE_LOADED && e->distance <= active2 &&
				Activate (best, 1))
				changed = 1;
		}
		if (changed && !prime)
		{
			Reconcile ();
			changed = 0;
		}
	}
	if (changed)
		Reconcile ();
	Graft (prime ? 2 : 1);
	Margin ();
	ticks++;
}

/* The whole ring at once (a spawn or the first frame of a map). */
void ChimChunks_Prime (const vec3_t origin, long budget)
{
	ChimChunks_Tick (origin, budget, 1);
}

/* ---------------------------------------------------------------- collision */

/* SV_ClipMoveToEntity for a placed brush model, origin and yaw given. */
static void ClipModel (model_t *m, const vec3_t origin, float s, float c, vec3_t start, vec3_t mins,
	vec3_t maxs, vec3_t end, trace_t *best)
{
	trace_t trace;
	vec3_t offset, start_l, end_l, delta, temp;
	hull_t *hull;
	float speed;
	int rotated = s != 0 || c != 1;

	memset (&trace, 0, sizeof(trace));
	trace.fraction = 1;
	trace.allsolid = true;
	VectorCopy (end, trace.endpos);
	if (maxs[0] - mins[0] < 3)
		hull = &m->hulls[0];
	else if (maxs[0] - mins[0] <= 32)
		hull = &m->hulls[1];
	else
		hull = &m->hulls[2];
	if (!hull->clipnodes)
		return;
	VectorSubtract (hull->clip_mins, mins, offset);
	VectorAdd (offset, origin, offset);
	VectorSubtract (start, offset, start_l);
	VectorSubtract (end, offset, end_l);
	if (rotated)
	{
		VectorCopy (start_l, temp);
		start_l[0] = c*temp[0] + s*temp[1];
		start_l[1] = -s*temp[0] + c*temp[1];
		VectorCopy (end_l, temp);
		end_l[0] = c*temp[0] + s*temp[1];
		end_l[1] = -s*temp[0] + c*temp[1];
	}
	SV_RecursiveHullCheck (hull, hull->firstclipnode, 0, 1, start_l, end_l, &trace);
	if (!trace.allsolid && trace.fraction < 1)
	{
		VectorSubtract (end_l, start_l, delta);
		speed = DotProduct (delta, trace.plane.normal);
		if (speed < 0)
			speed = -speed;
		if (speed > 0)
		{
			trace.fraction -= CHIM_DIST_EPSILON/speed;
			if (trace.fraction < 0)
				trace.fraction = 0;
			VectorMA (start_l, trace.fraction, delta, trace.endpos);
		}
	}
	if (rotated && trace.fraction != 1)
	{
		VectorCopy (trace.endpos, temp);
		trace.endpos[0] = c*temp[0] - s*temp[1];
		trace.endpos[1] = s*temp[0] + c*temp[1];
		VectorCopy (trace.plane.normal, temp);
		trace.plane.normal[0] = c*temp[0] - s*temp[1];
		trace.plane.normal[1] = s*temp[0] + c*temp[1];
	}
	if (trace.fraction != 1)
		VectorAdd (trace.endpos, offset, trace.endpos);
	if (trace.allsolid)
	{
		trace.fraction = 0;
		VectorCopy (start, trace.endpos);
	}
	AW_MergeCollisionTrace (best, &trace, sv.edicts);
}

void ChimChunks_Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best)
{
	vec3_t low, high;
	int i, j, k;

	for (k=0 ; k<3 ; k++)
	{
		low[k] = (start[k] < end[k] ? start[k] : end[k]) + mins[k] - 1;
		high[k] = (start[k] > end[k] ? start[k] : end[k]) + maxs[k] + 1;
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		chim_chunk_t *c;
		if (e->state != CHIM_STATE_ACTIVE)
			continue;
		c = e->chunk.data;
		for (k=0 ; k<3 ; k++)
			if (low[k] > c->maxs[k] || high[k] < c->mins[k])
				break;
		if (k != 3)
			continue;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked)
				continue;
			for (k=0 ; k<3 ; k++)
				if (low[k] > p->maxs[k] || high[k] < p->mins[k])
					break;
			if (k != 3)
				continue;
			ClipModel (p->ent.model, p->ent.origin, p->s, p->c, start, mins, maxs, end, best);
			if (best->allsolid)
				return;
		}
	}
}

/* ---------------------------------------------------------------- end */

void ChimChunks_End (void)
{
	int i;
	if (!chim_frame.entries)
		return;
	/* Host_ClearMemory has already reset the efrag pool. */
	link_world = NULL;
	ChimStatics_PoolReset ();
	for (i=0 ; i<chim_frame.count ; i++)
		if (chim_frame.entries[i].state == CHIM_STATE_ACTIVE)
			Deactivate (i);
	ChimModels_Abort ();
	ChimZone_EvictKind (CHIM_KIND_CHUNK, NULL);
	ChimZone_EvictKind (CHIM_KIND_TERRAIN, NULL);
	world_dirty = 0;
	world_retry = 0;
	ChimZone_Unlock (index_user.data);
	ChimZone_Free (&index_user);
	memset (&chim_frame, 0, sizeof(chim_frame));
	grid = NULL;
}

void ChimChunks_Init (void)
{
	ChimZone_SetEvict (CHIM_KIND_CHUNK, ChunkEvicted);
}

/* What the renderer did with the placements in its last frame: stored for
 * drawing from a visible leaf (R_StoreEfrags sets visframe), and of those
 * how many stayed in one leaf (the cheap R_DrawSubmodelPolygons path, no
 * clipping down the world BSP). Counted on request only. */
void ChimChunks_LastFrame (int *sent, int *one_leaf_path, int *placements)
{
	int i, j;
	*sent = *one_leaf_path = *placements = 0;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked)
				continue;
			(*placements)++;
			if (p->ent.visframe != r_framecount)
				continue;
			(*sent)++;
			if (p->ent.topnode && p->ent.topnode->contents < 0)
				(*one_leaf_path)++;
		}
	}
}

void ChimChunks_Report (void)
{
	int sent, one_path, placements, i, flagged = 0;
	Con_Printf ("frame %ld %ld: %ld chunks, %ld loaded, %ld active (grain %ld)\n",
		(long)chim_frame.frame.cx, (long)chim_frame.frame.cy, (long)chim_frame.count, (long)chim_frame.loaded,
		(long)chim_frame.active, (long)chim_frame.frame.grain);
	Con_Printf ("placements linked %ld, efrags %ld (one leaf %ld, max leaves %ld)\n",
		(long)counts.placements_linked, (long)counts.efrags, (long)counts.one_leaf, (long)counts.max_leaves);
	Con_Printf ("actors frozen outside the ring: %lu; placements hidden by the view's list: %ld\n",
		frozen_last, (long)counts.hidden);
	Con_Printf ("activations %lu, deactivations %lu, reconciles %lu\n",
		counts.activations, counts.deactivations, counts.reconciles);
	ChimChunks_LastFrame (&sent, &one_path, &placements);
	for (i=0 ; i<chim_frame.count ; i++)
		if (chim_frame.entries[i].state == CHIM_STATE_ACTIVE)
			flagged += ((chim_chunk_t *)chim_frame.entries[i].chunk.data)->over_16_leaves;
	Con_Printf ("active records over 16 leaves (builder flag): %ld\n", (long)flagged);
	Con_Printf ("last frame: %ld of %ld placements sent from visible leaves, %ld of them unclipped (one leaf)\n",
		(long)sent, (long)placements, (long)one_path);
}

/* For the host tests: the link counters as numbers. */
int ChimChunks_Hidden (void)
{
	return counts.hidden;
}

void ChimChunks_Counts (int *linked, int *efrags, int *one_leaf, int *max_leaves)
{
	*linked = counts.placements_linked;
	*efrags = counts.efrags;
	*one_leaf = counts.one_leaf;
	*max_leaves = counts.max_leaves;
}

/* ---------------------------------------------------------------- frame world support */

/* An entity the frame world took out of its leaves (R_RemoveEfrags): when
 * it is a placement, ChimChunks_Link links it again. */
int ChimChunks_Forget (entity_t *ent)
{
	int i;
	if (ChimStatics_Forget (ent))
		return 1;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		chim_place_t *p = (chim_place_t *)ent;
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE || p < c->places || p >= c->places + c->records)
			continue;
		if (p->leaves)
		{
			counts.efrags -= p->leaves;
			if (p->leaves == 1)
				counts.one_leaf--;
			p->leaves = 0;
		}
		return 1;
	}
	return 0;
}

int ChimChunks_CellEntry (int x, int y)
{
	if (!grid || x < 0 || y < 0 || x >= chim_frame.frame.nx || y >= chim_frame.frame.ny)
		return -1;
	return grid[y*chim_frame.frame.nx + x];
}

/* Before the world's leaves are replaced: every placement's efrags go back
 * to the pool unlinked; ChimChunks_Link links them into the new leaves. */
void ChimChunks_ReleaseEfrags (void)
{
	int i, j;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		for (j=0 ; j<c->records ; j++)
			if (c->places[j].leaves)
			{
				ChimGraft_ReleaseEfrags (&c->places[j].ent);
				c->places[j].leaves = 0;
			}
	}
	counts.efrags = counts.one_leaf = counts.max_leaves = 0;
	ChimStatics_ReleaseEfrags ();
}

/* Actors stand on chunk terrain: outside the active ring they are frozen.
 * Only moving kinds; doors, platforms, triggers and timers run as before. */
int ChimChunks_Frozen (edict_t *ent)
{
	int movetype = (int)ent->v.movetype, x, y, e;
	float g = (float)chim_frame.frame.grain;
	if (!chim_frame.count || (movetype != MOVETYPE_STEP && movetype != MOVETYPE_TOSS &&
		movetype != MOVETYPE_BOUNCE && movetype != MOVETYPE_FLY && movetype != MOVETYPE_FLYMISSILE))
		return 0;
	if ((unsigned long)host_framecount != frozen_frame)
	{
		frozen_last = frozen_now;
		frozen_now = 0;
		frozen_frame = (unsigned long)host_framecount;
	}
	x = ent->v.origin[0] < chim_frame.frame.low[0] ? -1 : (int)((ent->v.origin[0] - chim_frame.frame.low[0]) / g);
	y = ent->v.origin[1] < chim_frame.frame.low[1] ? -1 : (int)((ent->v.origin[1] - chim_frame.frame.low[1]) / g);
	e = ChimChunks_CellEntry (x, y);
	if (e >= 0 && chim_frame.entries[e].grafted)
		return 0;
	frozen_now++;
	return 1;
}

int ChimChunks_FrozenLast (void)
{
	return (int)(frozen_now > frozen_last ? frozen_now : frozen_last);
}
