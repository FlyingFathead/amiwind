/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM internals shared by chim_models.c, chim_chunks.c and chim_world.c.
 */
#ifndef CHIM_LOCAL_H
#define CHIM_LOCAL_H

#include "chim.h"
#include "chim_format.h"
#include "chim_zone.h"

#define CHIM_OPEN_FILES		4		/* sector files kept open at once */
#define CHIM_MAX_CHUNKS		4096
#define CHIM_MAX_RECORDS	8192		/* placement records in one chunk */
#define CHIM_MIN_BUFFER		(AW_BRUSH_SLICE_BYTES)
#define CHIM_MIN_ZONE		(128*1024)	/* below this a CHIM map does not start */

/* An open CHIM file: the stdio handle, where the file starts (a member may
 * start inside a larger file) and its size. */
typedef struct
{
	FILE		*file;
	long		base, bytes;
	char		path[CHIM_PATH_CHARS+8];
} chim_pack_t;

/* A shared model or terrain block: the model, then its decoded arena. */
typedef struct chim_model_s
{
	model_t			model;
	aw_brush_arena_t	arena;
	unsigned		id;
	int				kind;
	int				leafs;		/* decoded leaves, leaf 0 included */
} chim_model_t;

/* Run-time placement: one per placement record of an active chunk. */
typedef struct
{
	entity_t	ent;			/* render entity; ent.model set while linked */
	vec3_t		mins, maxs;		/* drawn box in the frame */
	float		s, c;			/* yaw sine and cosine for model-space traces */
	unsigned	pid, model;
	int			owner;			/* chunk index (pack order) of the owner record */
	int			linked;			/* drawn and collided by this chunk */
	int			flags;			/* record flags (CHIM_RECORD_*) */
	int			leaves;			/* efrags while linked on the client */
} chim_place_t;

typedef struct
{
	unsigned	id;
	chim_model_t	*model;		/* valid while the chunk is active */
} chim_chunk_model_t;

typedef struct
{
	int			entry;
	int			records, owned, models;
	int			over_16_leaves;		/* records flagged by the builder */
	chim_place_t		*places;
	chim_chunk_model_t	*model_list;
	vec3_t		mins, maxs;		/* terrain and every placement box */
	byte		*pvs;			/* compressed row over the frame's chunks */
	int			pvs_bytes, terrain_leaves;
	byte		*pvl;			/* compressed row over the frame's placements: */
	int			pvl_bytes;		/* the ones a view from this chunk may see */
} chim_chunk_t;

#define CHIM_STATE_ABSENT	0
#define CHIM_STATE_LOADED	1	/* catalogue (and terrain) in the zone */
#define CHIM_STATE_ACTIVE	2	/* models locked, placements instantiated */

typedef struct
{
	chim_chunk_entry_t	disk;
	int			file;				/* file table row of its sector */
	float		low[2], high[2];	/* chunk square in the frame */
	chim_user_t	chunk;				/* chim_chunk_t catalogue */
	chim_user_t	terrain;			/* chim_model_t terrain */
	int			state, ready;
	int			partial;			/* active without some models (CHIM-CHUNK-LOAD-FAIL-33) */
	int			grafted;			/* its terrain is in the frame world */
	int			graft;				/* its row in the frame world's graft table, -1: none */
	unsigned long	failed_until;	/* tick before which a failed load waits */
	unsigned long	released_until;	/* released for a nearer chunk: not active again before this tick */
	unsigned long	failed_said;	/* tick + 1 of its last failure line (one line per 50 ticks) */
	float		distance;		/* squared, to the chunk square */
	float		priority;		/* squared; the nearer of the player and the point ahead */
} chim_entry_t;

typedef struct
{
	chim_settings_t	settings;
	chim_frame_t	frame;
	int				count;
	chim_entry_t	*entries;
	unsigned char	*drawn;			/* one bit per placement id of the frame */
	unsigned char	*visible;		/* the view chunk's placement row, decompressed */
	int				view_entry;		/* chunk of the visible row, -1: none (all visible) */
	unsigned		first_pid;		/* placement ids run on across frames: this frame's first */
	int				active, loaded;
} chim_frame_state_t;

typedef struct
{
	int				valid;
	chim_settings_t	settings;
	chim_toc_t		toc;
	int				files;
	chim_file_t		*file;
	unsigned		models, textures;
	chim_asset_t	*model, *texture;	/* the index's directories, by id */
	struct chim_model_s	**model_slot;	/* resident shared model by id, or NULL */
	texture_t		**texture_slot;		/* resident shared texture by id, or NULL */
	byte			*buffer;		/* the loading buffer */
	int				buffer_bytes;
	unsigned long	bytes_read, reads, model_loads, texture_loads, chunk_loads;
	unsigned long	streamed_models, failed_loads, opens;
	int				minor;			/* the world's format minor */
} chim_world_t;

extern chim_world_t	chim_world;
extern chim_frame_state_t	chim_frame;

/* chim_world.c */
extern cvar_t	chim_pool_kib, chim_draw_distance, chim_prefetch, chim_prefetch_room;
extern cvar_t	chim_graft_mode, chim_graft_kib, chim_lookahead, chim_graft_trim;
extern cvar_t	chim_release, chim_partial, chim_zone_ends;
float Chim_ViewDistance (void);
int Chim_EdgeReached (const vec3_t origin);
int Chim_HunkRest (int *stated, int *used, int *measured);
extern cvar_t	chim_debug;			/* 1: a console line per CHIM stage (map, prime, rebuild) */
int Chim_PackOpen (chim_pack_t *pack, const char *relative);
void Chim_PackClose (chim_pack_t *pack);
int Chim_PackRead (chim_pack_t *pack, long offset, void *out, long bytes);
chim_pack_t *Chim_File (int row);
void Chim_FilesClose (void);
int Chim_FileRow (const char *kind, int cx, int cy, int sector);

/* chim_models.c */
void ChimModels_Init (void);
chim_model_t *ChimModels_Find (unsigned id);
int ChimModels_Step (unsigned id, long *budget);
int ChimModels_TerrainStep (int entry, long *budget);
int ChimModels_Busy (void);
chim_model_t *ChimModels_Terrain (int entry);
void ChimModels_Abort (void);
int ChimModels_ResidentTextures (void);
void ChimModels_IndexSlots (void);

/* chim_chunks.c */
int ChimChunks_Begin (int cx, int cy);
void ChimChunks_End (void);
void ChimChunks_Tick (const vec3_t origin, long budget, int prime);
void ChimChunks_Link (void);
void ChimChunks_Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best);
void ChimChunks_Report (void);
void ChimChunks_Init (void);
void ChimChunks_Counts (int *linked, int *efrags, int *one_leaf, int *max_leaves);
int ChimChunks_Hidden (void);
unsigned long ChimChunks_PrefetchHeld (void);
void ChimChunks_LastFrame (int *sent, int *one_leaf_path, int *placements);
int ChimChunks_CellEntry (int x, int y);
void ChimChunks_ReleaseEfrags (void);
int ChimChunks_Frozen (edict_t *ent);
int ChimChunks_FrozenLast (void);
void ChimChunks_Prime (const vec3_t origin, long budget);
int ChimChunks_Forget (entity_t *ent);
extern int (*chim_story_hidden)(void);	/* 1: placements flagged story hidden stay out */
void ChimChunks_Streaming (int *margin, unsigned long *urgent_loads, int *ahead);
float ChimChunks_ActiveRadius (void);
float ChimChunks_LoadRadius (void);
void ChimChunks_Pressure (unsigned long *released_band, unsigned long *released_ring, unsigned long *partial,
	unsigned long *zone_failures, unsigned long *data_failures);

/* chim_statics.c */
void ChimStatics_Begin (int stated, int chunks);
void ChimStatics_End (void);
int ChimStatics_Capture (char **data);
int ChimStatics_Count (void);
entity_t *ChimStatics_Entity (int i);
unsigned ChimStatics_Missing (int index);
int ChimStatics_IsStatic (unsigned model);
const char *ChimStatics_Name (unsigned model);
long ChimStatics_Bytes (unsigned model);
int ChimStatics_Step (unsigned model, long *budget);
int ChimStatics_Activate (int index);
void ChimStatics_Deactivate (int index);
int ChimStatics_Link (int (*add)(entity_t *ent, const vec3_t mins, const vec3_t maxs), int (*linkable)(int index));
int ChimStatics_Forget (entity_t *ent);
void ChimStatics_ReleaseEfrags (void);
void ChimStatics_PoolReset (void);
void ChimStatics_Report (void);
void ChimStatics_Counts (int *count, int *linked, int *efrags, int *models, int *sprite_bytes);
/* chim_far.c: the frame's far terrain (maps/<frame map>.far, tools/chim/far.py) */
#define CHIM_FAR_VERSION		2	/* reads 1 (heights) and 2 (heights and object stamps) */
#define CHIM_FAR_HEADER_BYTES	40
typedef struct
{
	int			version, header, cx, cy, nx, ny, block, stamps;
	float		origin[2], step, scale;		/* world position of sample 0, Morrowind units; local per unit */
	unsigned	crc;						/* CRC-32 of the height bytes */
} chim_far_header_t;
extern cvar_t	chim_far, chim_far_reach, chim_far_objects, chim_terrain_floor;
int ChimFar_Parse (const unsigned char *p, long file_bytes, chim_far_header_t *h);
long ChimFar_BodyBytes (const chim_far_header_t *h);
int ChimFar_Stamps (short *heights, int nx, int ny, const unsigned char *list, int count);
void ChimFar_Bounds (const short *heights, int nx, int ny, int block, short *bounds);
void ChimFar_Begin (const char *map_name, long hunk_spare);
void ChimFar_End (void);
int ChimFar_Loaded (void);
struct aw_horizon_grid_s;
const struct aw_horizon_grid_s *ChimFar_Layer (void);
int ChimFar_RCount (char *out, int size);
void ChimFar_Report (void);
void ChimFar_Init (void);
void ChimFar_Hook (void);
int ChimFar_Floor (const vec3_t origin, float *lowest, float *surface);	/* the terrain floor (aw_walk.c) */

/* chim_graft.c */
int ChimGraft_Begin (model_t *world);
void ChimGraft_End (void);
int ChimGraft_Rebuild (void);
int ChimGraft_Update (int phase);
int ChimGraft_Incremental (void);
int ChimGraft_LeafOwner (int leaf, int *entry, int *local);
int ChimGraft_ReleaseEfrags (entity_t *ent);
void ChimGraft_RemoveEfrags (entity_t *ent);
void ChimGraft_Report (void);
void ChimGraft_Stats (int *rebuilds, int *grafts, int *leafs, int *surfs, int *bytes);
void ChimGraft_Slots (int *slot0, int *slot1, unsigned long *outgrown, unsigned long *failures);
void ChimGraft_Trims (unsigned long *trims, int *trimmed);
void ChimGraft_Interval (int *rebuilds, long *total_us, long *worst_us, int *pool_bytes);
void ChimGraft_Work (int *adds, int *removes, int *repacks, long *worst_bytes, unsigned long *urgent);
void ChimGraft_Totals (unsigned long *adds, unsigned long *removes, unsigned long *repacks, unsigned long *copied,
	unsigned long *relinked, unsigned long *urgent);

#endif
