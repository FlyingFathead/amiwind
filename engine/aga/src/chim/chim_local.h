/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM internals shared by chim_models.c, chim_chunks.c and chim_world.c.
 */
#ifndef CHIM_LOCAL_H
#define CHIM_LOCAL_H

#include "chim.h"
#include "chim_format.h"
#include "chim_placed_clip.h"
#include "chim_thgt.h"
#include "chim_zone.h"
#include "aw_inspect.h"

#ifndef CHIM_OPEN_FILES
#define CHIM_OPEN_FILES		4		/* sector files kept open at once (the host tests may set fewer) */
#endif
#define CHIM_MAX_CHUNKS		4096
/* Rows of the world file table (chim_asset_t.file is 16 bits); a 270-region coast world has 7,236 (CHIM-DEV3-MAPLOAD-CRASH-36). */
#define CHIM_MAX_FILES		65535
#define CHIM_MAX_RECORDS	8192		/* placement records in one chunk */
#define CHIM_MIN_BUFFER		(AW_BRUSH_SLICE_BYTES)
#define CHIM_MIN_ZONE		(128*1024)	/* below this a CHIM map does not start */
/* Efrag links (client.h AW_EFRAG_LIMIT) CHIM placements leave for everything
 * else; near the limit placements wait unlinked, farthest chunks first
 * (CHIM-EFRAG-UNCAPPED-35). The builder's CHIM heap gate reads this define
 * (tools/engine_limits.py). */
#define CHIM_EFRAG_RESERVE	4096

/* An open CHIM file: the stdio handle, where the file starts (a member may
 * start inside a larger file) and its size. pins: loads holding the handle
 * across frames (a streamed model or terrain); Chim_File never closes a
 * pinned file to open another (CHIM-PACK-LRU-STREAM-35). */
typedef struct
{
	FILE		*file;
	long		base, bytes;
	int			pins;
	int			row;		/* its file-table row (Chim_File), -1: opened by path */
	char		path[CHIM_STORE_CHARS+1+CHIM_PATH_CHARS+1];	/* "<store>/<relative>" */
} chim_pack_t;

/* A shared model or terrain block: the model, then its decoded arena. */
typedef struct chim_model_s
{
	model_t			model;
	aw_brush_arena_t	arena;
	unsigned		id;
	int				kind;
	int				leafs;		/* decoded leaves, leaf 0 included */
	/* 0.8: the piece table in lump 4 (model.visdata, chim_placed_clip.c):
	 * its bytes, and 1 once it is in native order and usable */
	long			piece_bytes;
	int				pieces;
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
	float		*rot;			/* 0.8: model -> world of each record (9 floats; ChimPlaced_AnglesMatrix),
								 * NULL in 0.4-0.7 worlds */
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
	float		shift[3];			/* 0.7: where its (chunk-local) terrain is placed; 0 for CHK0 */
	long		terrain_bytes;		/* its terrain image's bytes once the head was read, else 0 */
	int			state, ready;
	int			partial;			/* active without some models (CHIM-CHUNK-LOAD-FAIL-33) */
	int			grafted;			/* its terrain is in the frame world */
	int			graft;				/* its row in the frame world's graft table, -1: none */
	unsigned long	failed_until;	/* tick before which a failed load waits */
	unsigned long	released_until;	/* released for a nearer chunk: not active again before this tick */
	unsigned long	failed_said;	/* tick + 1 of its last failure line (one line per 50 ticks) */
	float		distance;		/* squared, to the chunk square */
	float		priority;		/* squared; the nearer of the player and the point ahead */
	/* Type 1 crossings (the window, chim_window.c): its frame's slot (0
	 * without a window), the entry whose terrain stands at the same place
	 * when that is another frame's (-1: this one's own ground), and whether
	 * its activation locked its terrain (always, without a window). */
	short		slot, shadow;
	int			terrain_locked;
} chim_entry_t;

/* Type 1 crossings (docs/chim/CELL_CROSSINGS.md, "Type 1: one continuous
 * world"): the region frames around the player are one window of up to
 * CHIM_WINDOW_SLOTS frames in one frame world, at a fixed origin (the frame
 * the map started on). A slot holds one frame: its chunk entries are
 * chim_frame.entries[base, base + count), placed at offset (frame-local to
 * the session's coordinates); its own chunk grid, placement ids and
 * placement bits. */
#define CHIM_WINDOW_SLOTS	4
#define CHIM_CELL_UNITS		2048		/* a Morrowind exterior cell in map units (8,192 original) */
typedef struct
{
	int				used, leaving;		/* leaving: its chunks wait to leave the frame world */
	int				cx, cy, row;		/* its frame (= its cell) and FRAM file row */
	float			offset[2];			/* frame-local -> session coordinates */
	float			core[4];			/* the cell it owns, session coordinates: x0 y0 x1 y1 */
	int				base, count;
	unsigned		first_pid;
	chim_frame_t	frame;				/* its own frame header (frame-local) */
	short			*grid;				/* its chunk (x, y) -> local entry */
	unsigned char	*drawn, *visible;	/* bits over its placement ids */
	chim_user_t		user;				/* the zone block of the three above */
} chim_slot_t;

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
	/* Type 1 (chim_window.c): 1 when this map runs a window of frames; then
	 * frame.low/nx/ny is the window's chunk grid in the session's coordinates
	 * (frame.centre, cx, cy stay the map's own frame: the session origin). */
	int				window, slot_entries, view_slot, block_set;
	int				block[2];		/* the window's 2 x 2 block of cells: its south-west cell */
	chim_slot_t		slot[CHIM_WINDOW_SLOTS];
	unsigned long	joins, leaves, crossings, recentres;
} chim_frame_state_t;

/* A row of the index's file table as the engine keeps it (CHIM-ZONE-RELEASE-
 * FLICKER-42): the 33-character path is not stored when it is the builder's
 * own name for the row (frames/x+04/y-12[/gG]/sNN.ccs, .../frame.ccf), which
 * Chim_FilePath writes again from the row; about 30 bytes less per row, some
 * 600 KiB of the zone for the whole island's 19,371 files. A path of any
 * other form is kept (one of CHIM_PATH_KEPT, or every path when built with
 * CHIM_INDEX_KEEP_PATHS 1, the first method). */
typedef struct
{
	char			kind[5];
	signed char		group;		/* gG directory, -1: none */
	unsigned char	digits;		/* digits of the sector in its name */
	unsigned char	kept;		/* 1 + the kept path's slot, 0: written from the row */
	short			cx, cy;
	unsigned short	sector;
	unsigned		bytes, crc, entries;
} chim_file_row_t;
#define CHIM_PATH_KEPT	64
#ifndef CHIM_INDEX_KEEP_PATHS
#define CHIM_INDEX_KEEP_PATHS 0
#endif

typedef struct
{
	int				valid;
	chim_settings_t	settings;
	chim_toc_t		toc;
	int				files;
	chim_file_row_t	*file;
	char			*paths;			/* CHIM_INDEX_KEEP_PATHS 1: every row's path, CHIM_PATH_CHARS+1 each */
	unsigned		models, textures;
	chim_asset_t	*model, *texture;	/* the index's directories, by id */
	struct chim_model_s	**model_slot;	/* resident shared model by id, or NULL */
	texture_t		**texture_slot;		/* resident shared texture by id, or NULL */
	byte			*buffer;		/* the loading buffer */
	int				buffer_bytes;
	unsigned long	bytes_read, reads, model_loads, texture_loads, chunk_loads;
	unsigned long	terc_records;		/* 0.10: compact terrain records expanded */
	chim_thgt_stats_t	thgt;			/* 0.11: generated terrain records and the work done */
	unsigned long	streamed_models, failed_loads, opens;
	unsigned long	prefetch_hits, prefetch_bytes;	/* the prefetch (chim_prefetch.c): reads served, bytes read ahead */
	int				minor;			/* the world's format minor */
} chim_world_t;

extern chim_world_t	chim_world;
extern chim_frame_state_t	chim_frame;

/* chim_world.c */
extern cvar_t	chim_pool_kib, chim_draw_distance, chim_prefetch, chim_prefetch_room;
extern cvar_t	chim_graft_mode, chim_graft_kib, chim_lookahead, chim_graft_trim;
extern cvar_t	chim_release, chim_partial, chim_zone_ends;
extern unsigned long	chim_release_refused;	/* chim_chunks.c: release plans that found no room (nothing released) */
float Chim_ViewDistance (void);
int Chim_LookaheadScale (void);
int Chim_EdgeReached (const vec3_t origin);
int Chim_HunkRest (int *stated, int *used, int *measured);
extern cvar_t	chim_debug;			/* 1: a console line per CHIM stage (map, prime, rebuild) */
int Chim_PackOpen (chim_pack_t *pack, const char *relative);
/* The store folder every pack path is under (default "chim", the exterior
 * world; docs/chim/INTERIOR_STORE.md). Chim_StoreSelect: 0 for an invalid name
 * or while a CHIM map runs; a different store drops the resident index, every
 * kept model and texture and the read-ahead blocks (ids are per store). */
const char *Chim_Store (void);
int Chim_StoreSelect (const char *name);
void Chim_PackClose (chim_pack_t *pack);
int Chim_PackRead (chim_pack_t *pack, long offset, void *out, long bytes);
int Chim_PackReadRaw (chim_pack_t *pack, long offset, void *out, long bytes);
chim_pack_t *Chim_File (int row);
long ChimStatics_AliasBytes (void);
int Chim_FarOnly (void);
void Chim_FilesClose (void);
int Chim_FileRow (const char *kind, int cx, int cy, int sector);
const char *Chim_FilePath (int row);

/* chim_prefetch.c: read-ahead into spare Fast RAM (CHIM-CROSSING-SYNC-LOAD-43) */
void ChimPrefetch_Init (void);
void ChimPrefetch_Command (int argc, char **argv);
void ChimPrefetch_SetOn (int on);
int ChimPrefetch_Active (void);
int ChimPrefetch_Read (int row, long offset, void *out, long bytes);
void ChimPrefetch_Step (const vec3_t origin, int spare);
void ChimPrefetch_MapBegin (void);
void ChimPrefetch_StoreChanged (void);
void ChimPrefetch_Report (void);
int ChimPrefetch_Owned (int row, unsigned *count);
void ChimPrefetch_SetOwned (int row, unsigned count);
int ChimPrefetch_Wanted (int i, int *cx, int *cy, int *state);
long ChimPrefetch_Held (int *count);
unsigned long ChimPrefetch_Passes (void);

/* chim_models.c */
void ChimModels_Init (void);
chim_model_t *ChimModels_Find (unsigned id);
int ChimModels_Step (unsigned id, long *budget);
int ChimModels_TerrainStep (int entry, long *budget);
int ChimModels_TerrainPlace (int entry, chim_pack_t **pack, long *at, long *bytes);
int ChimModels_Busy (void);
chim_model_t *ChimModels_Terrain (int entry);
void ChimModels_Abort (void);
int ChimModels_JobTerrain (void);
int ChimModels_ResidentTextures (void);
void ChimModels_IndexSlots (void);

/* chim_chunks.c */
int ChimChunks_Begin (int cx, int cy);
/* The frame map's fire lights (aw_flame rows with aw_flame_light) and a placement's level from them. */
void ChimChunks_FireLights (const char *entities);
int ChimChunks_FireLevel (const vec3_t mins, const vec3_t maxs);
int ChimChunks_FireCount (void);
void ChimChunks_End (void);
void ChimChunks_Tick (const vec3_t origin, long budget, int prime);
void ChimChunks_Link (void);
void ChimChunks_Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best);
/* One placement's collision (rot9: its 0.8 matrix, NULL for the yaw path); the room loader's too. */
void ChimChunks_ClipPlace (chim_place_t *p, float *rot9, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end,
	trace_t *best);

/* chim_room.c: a room map's placements from its room record (docs/chim/INTERIOR_STORE.md) */
int ChimRoom_Begin (const char *name);
void ChimRoom_End (void);
int ChimRoom_Active (void);
void ChimRoom_Link (void);
void ChimRoom_Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best);
void ChimRoom_Report (void);
int ChimChunks_Pick (const vec3_t start, const vec3_t end, aw_chim_pick_t *out);
/* 0.9 reach references: served from a resident owner catalogue, read from
 * disk, and the owner record runs read (chim_chunks.c ReachRecord). */
typedef struct
{
	unsigned long	resident, read, span_reads;
} chim_reach_stats_t;
extern chim_reach_stats_t chim_reach_stats;
extern int chim_reach_resident;
void ChimChunks_Report (void);
void ChimChunks_Init (void);
void ChimChunks_Counts (int *linked, int *efrags, int *one_leaf, int *max_leaves);
void ChimChunks_EfragCounts (int *waiting, unsigned long *capped, unsigned long *novis_frames);
extern int chim_efrag_limit;
int ChimChunks_Hidden (void);
unsigned long ChimChunks_PrefetchHeld (void);
void ChimChunks_LastFrame (int *sent, int *one_leaf_path, int *placements);
int ChimChunks_CellEntry (int x, int y);
int ChimChunks_RowSees (const byte *row, int from, int to);
int ChimChunks_RowEntries (int entry);
int ChimChunks_Grounded (int entry);
int ChimChunks_WindowOn (int on);
int ChimChunks_WindowCross (const vec3_t origin, int *cx, int *cy);
int ChimChunks_WindowRecentre (int cx, int cy, float *d);
int ChimChunks_WindowOffset (int cx, int cy, float *d);
int ChimChunks_RecentreOn (int on);
int ChimGraft_Recentre (void);
void ChimStatics_Recentre (const float *d);
void ChimFar_Recentre (const float *d);
void ChimCuts_Recentre (const float *d);
void ChimChunks_WindowReport (void);
extern int (*chim_cell_map)(int cx, int cy, char *name, int size);	/* aw_world.c: a cell's region map name */
void ChimChunks_ReleaseEfrags (void);
int ChimChunks_Frozen (edict_t *ent);
int ChimChunks_FrozenLast (void);
void ChimChunks_Prime (const vec3_t origin, long budget);
int ChimChunks_Forget (entity_t *ent);
const char *ChimChunks_Describe (const entity_t *ent, char *out, int size);
extern int (*chim_story_hidden)(void);	/* 1: placements flagged story hidden stay out */
/* Hinged doors (aw_hinged_door.c AW_HingedDoorPlacement): 1 when a placement's
 * reference is an ordinary DOOR record without a destination; *yaw gets its
 * current pose. Such a placement carries CHIM_PLACE_HINGED (a run-time flag
 * above the record's 16 bits) and a drawn box that holds every pose. */
#define CHIM_PLACE_HINGED	0x10000
extern int (*chim_hinged_door)(unsigned pid, unsigned ref, const float *origin, float radius, float *yaw);
extern void (*chim_hinged_recentre)(const float *d);
int ChimChunks_DoorYaw (unsigned pid, float yaw);
int ChimChunks_DoorClip (unsigned pid, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *trace);
/* The distance from a placement's origin to its drawn box's farthest corner in
 * X and Y: a hinged door's box for every pose is the square of this about it. */
float ChimChunks_HingeRadius (const chim_place_t *p);
/* CHIM rooms (chim_room.c): the same door hooks on a room's placements. While
 * a room runs, ChimChunks_DoorYaw and ChimChunks_DoorClip come here. */
int ChimRoom_DoorYaw (unsigned pid, float yaw);
int ChimRoom_DoorClip (unsigned pid, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *trace);
void ChimChunks_Streaming (int *margin, unsigned long *urgent_loads, int *ahead);
float ChimChunks_ActiveRadius (void);
float ChimChunks_LoadRadius (void);
void ChimChunks_Pressure (unsigned long *released_band, unsigned long *released_ring, unsigned long *partial,
	unsigned long *zone_failures, unsigned long *data_failures);

/* chim_statics.c */
void ChimStatics_Begin (int stated, int chunks);
void ChimStatics_End (void);
int ChimStatics_SlotJoin (int slot, int base, int chunks, const char *map, const float *offset);
void ChimStatics_SlotEnd (int slot);
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
const char *ChimStatics_Describe (const entity_t *ent, char *out, int size);
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
/* chim_cuts.c: the frame map's whole-structure cut groups (maps/<map>.cut). */
int ChimCuts_Header (const unsigned char *p, long file_bytes, int cx, int cy, long *n, long *m, unsigned *crc);
int ChimCuts_Body (const unsigned char *body, long n, long m, unsigned crc,
	float *box_out, unsigned *pid_out, unsigned short *which_out);
const float *ChimCuts_Find (const float *box_table, const unsigned *pid_table, const unsigned short *which_table,
	long m, unsigned pid);
const float *ChimCuts_Box (unsigned pid);
void ChimCuts_Begin (const char *map_name, long hunk_spare);
void ChimCuts_End (void);
void ChimCuts_Report (void);

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
