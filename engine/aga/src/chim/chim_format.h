/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM world formats 0.4 to 0.6 as the engine reads them
 * (docs/chim/WORLD_FORMAT.md). 0.5 adds the story-hidden placement flag and
 * irregular ground with the same layout; 0.6 puts the sector files of a large
 * frame into one folder per sector row, which the index's file table names,
 * so the records are unchanged; 0.7 adds terrain references: a CHK1 chunk
 * record ends in a reference block naming a TERR record (chunk terrain stored
 * once, in chunk-local units) and the shift it is placed at; 0.8
 * (EXPERIMENTAL, written only with the builder's placement format 0.8) adds
 * the pitch and the roll to the placement record (56 bytes, the chunk head
 * names the record size) and the piece table in a placed model's lump 4
 * (chim_placed_clip.c); 0.9 (EXPERIMENTAL, written only with the builder's
 * reach index refs) keeps each placement record once per frame: a chunk that
 * a record's drawn box reaches but does not own holds a 4-byte reference
 * (CHK2: inline terrain, CHK3: terrain reference block) to the record in its
 * owner chunk of the same frame; 0.10 (EXPERIMENTAL, the builder's terrain pack
 * compact) may store a TERR record compact (chim_terc.c expands it to the same
 * BSP29 bytes), and every chunk head names its record size (0: 48 bytes); 0.11
 * (EXPERIMENTAL, terrain pack generate) may store a TERR record as heights and
 * facts from which chim_thgt.c generates the same bytes:
 * decoders for the big-endian CHIM structures (index, frame file, sector
 * files, chunk records and placement records). Brush images inside the
 * sector files stay little-endian BSP29 and go through model.c's section
 * loaders. The builder side (tools/chim/format.py) defines the layout; this
 * file must follow it byte for byte.
 */
#ifndef CHIM_FORMAT_H
#define CHIM_FORMAT_H

#define CHIM_FORMAT_MAJOR	0
#define CHIM_FORMAT_MINOR	12
#define CHIM_FORMAT_MINOR_OLDEST	4	/* the oldest minor of this major the engine reads */

#define CHIM_HEADER_BYTES		32
#define CHIM_SETTINGS_BYTES		40
#define CHIM_TOC_BYTES			32
#define CHIM_FILE_BYTES			60
#define CHIM_MODEL_DIR_BYTES	24
#define CHIM_TEXTURE_DIR_BYTES	24
#define CHIM_FRAME_BYTES		32
#define CHIM_CHUNK_ENTRY_BYTES	28
#define CHIM_SECTOR_ENTRY_BYTES	12
#define CHIM_RECORD_ENTRY_BYTES	16
#define CHIM_CHUNK_HEAD_BYTES	24
#define CHIM_TERRAIN_REF_BYTES	32	/* 0.7: the reference block of a CHK1 chunk */
#define CHIM_RECORD_BYTES		48
#define CHIM_RECORD_BYTES_PLACED	56	/* 0.8: the 48 bytes, then pitch and roll */
#define CHIM_PLACED_MINOR		8	/* the first minor with placed records and piece tables */
#define CHIM_REACH_MINOR		9	/* the first minor with reach references (CHK2, CHK3) */
#define CHIM_REACH_REF_BYTES	4	/* 0.9: u16 owner chunk (frame, pack order), u16 its owned record */
#define CHIM_THGT_MINOR		11	/* the first minor with generated terrain records (chim_thgt.c) */
#define CHIM_TERC_MINOR		10	/* the first minor with compact terrain records (chim_terc.c); its chunk heads name the record size */
#define CHIM_RECORD_OVER_16_LEAVES	1	/* record flag: reaches more than MAX_ENT_LEAFS */
#define CHIM_RECORD_STORY_HIDDEN	2	/* record flag (0.5): hidden by the opening story */
#define CHIM_LIGHT_MINOR		12	/* the first minor whose record flags carry a light level (docs/chim/INTERIOR_STORE.md) */
#define CHIM_RECORD_LIGHT_SHIFT	8	/* 0.12: flags bits 8-15, the placement's light level (0 none, 1-255) */
#define CHIM_INDEX_NAME			"chim/world.cwi"
#define CHIM_STORE_DEFAULT		"chim"	/* the store folder of the exterior world */
#define CHIM_STORE_CHARS		8		/* a store folder name: 1-8 of a-z 0-9 _ */
#define CHIM_ROOM_BLOCK_BYTES	32	/* a room record's block after its header (docs/chim/INTERIOR_STORE.md) */
#define CHIM_ROOM_NAME_CHARS	22	/* "rooms/<name>.crm" within CHIM_PATH_CHARS */
#define CHIM_PATH_CHARS			32

typedef struct
{
	char		kind[5];
	int			major, minor;
	unsigned	count, directory, data, bytes;
} chim_header_t;

typedef struct
{
	float		draw_distance, hysteresis, collision_margin, prefetch_margin;
	int			grain, terrain_light;
	unsigned	placements, models, textures, frames;
	int			sector_chunks;
} chim_settings_t;

/* Where the index keeps its tables. */
typedef struct
{
	unsigned	files_at, files, models_at, models, order_at, textures_at, textures, names_at;
} chim_toc_t;

typedef struct
{
	char		kind[5];			/* FRAM or SECT */
	int			sector, cx, cy;
	unsigned	bytes, crc, entries;
	char		path[CHIM_PATH_CHARS+1];
} chim_file_t;

/* A model or texture record: which file (a row of the file table) and where. */
typedef struct
{
	unsigned short	file, width, height, pad;
	unsigned	offset, bytes, render;
} chim_asset_t;

typedef struct
{
	int			cx, cy;
	float		centre[2], low[2];
	int			grain, nx, ny, sector_chunks;
	unsigned	owned_total;
} chim_frame_t;

typedef struct
{
	int			cx, cy, sector;
	unsigned	offset, render, collision;
	int			owned, reach, zmin, zmax;
} chim_chunk_entry_t;

typedef struct
{
	int			owned, reach;
	unsigned	image_at, image_render;
	int			pvs_bytes, terrain_leaves;
	int			pvl_bytes;			/* the placements a view from the chunk may see */
	int			ref;				/* 0.7 CHK1: the image is a terrain reference block */
	int			record_bytes;		/* 0.8: 56; 0 in 0.4-0.7 (48-byte records) */
	int			reach_refs;			/* 0.9 CHK2/CHK3: the reach entries are 4-byte references */
} chim_chunk_head_t;

/* 0.7: where a referenced chunk's terrain is stored and where it is placed. */
typedef struct
{
	unsigned	id, file, offset, bytes, render;
	float		shift[3];			/* local units, added when the chunk is grafted */
} chim_terrain_ref_t;

typedef struct
{
	unsigned	pid, ref, model;
	float		origin[3], yaw;
	float		pitch, roll;		/* 0.8 records; 0 for 0.4-0.7 */
	int			owner, cell_dx, cell_dy;
	short		mins[3], maxs[3];	/* drawn box, local units, rounded outward */
	int			leaves, flags;
} chim_record_t;

unsigned ChimFormat_U32 (const unsigned char *p);
int ChimFormat_U16 (const unsigned char *p);
int ChimFormat_S16 (const unsigned char *p);
float ChimFormat_F32 (const unsigned char *p);

int ChimFormat_Header (const unsigned char *p, long bytes, const char *kind, chim_header_t *out);
int ChimFormat_Settings (const unsigned char *p, chim_settings_t *out);
void ChimFormat_Toc (const unsigned char *p, chim_toc_t *out);
int ChimFormat_File (const unsigned char *p, chim_file_t *out);
void ChimFormat_ModelDir (const unsigned char *p, chim_asset_t *out);
void ChimFormat_TextureDir (const unsigned char *p, chim_asset_t *out);
int ChimFormat_Frame (const unsigned char *p, chim_frame_t *out);
void ChimFormat_ChunkEntry (const unsigned char *p, chim_chunk_entry_t *out);
int ChimFormat_ChunkHead (const unsigned char *p, chim_chunk_head_t *out);
int ChimFormat_TerrainRef (const unsigned char *p, chim_terrain_ref_t *out);
int ChimFormat_Record (const unsigned char *p, chim_record_t *out);
/* 0.8: a 56-byte record (ChimFormat_Record's 48 bytes, then pitch and roll). */
int ChimFormat_RecordPlaced (const unsigned char *p, chim_record_t *out);
/* The placement record size of a world of this minor (48 or 56). */
int ChimFormat_RecordBytes (int minor);
/* 0.12: a record's light level from its flags (0 before 0.12 or none). */
int ChimFormat_RecordLight (int minor, int flags);
/* A store folder name: 1 when valid (1-8 of a-z 0-9 _). */
int ChimFormat_StoreNameValid (const char *name);
/* "<store>/<relative>" into out (size bytes); 0 when the name is invalid or it does not fit. */
int ChimFormat_StorePath (char *out, int size, const char *store, const char *relative);

/* A room record (<store>/rooms/<room>.crm, docs/chim/INTERIOR_STORE.md): the
 * common header (kind ROOM, count = placements, directory = the model list at
 * 64, data = the placements after it), the room block (bounds, model count),
 * the store model ids (u32 each), then 56-byte placed records. */
typedef struct
{
	float		mins[3], maxs[3];
	unsigned	models;
} chim_room_t;
/* 1 when the whole file checks out: header, sizes and offsets, the block. */
int ChimFormat_Room (const unsigned char *p, long bytes, chim_header_t *h, chim_room_t *room);
/* A room name: 1-22 of a-z 0-9 _ - (the map name). */
int ChimFormat_RoomNameValid (const char *name);
/* 0.9: a reach reference: the owner chunk's index in its frame and the
 * record's position among that chunk's owned records. */
void ChimFormat_ReachRef (const unsigned char *p, int *owner, int *record);

/* A turbulent texture ('*' name: SURF_DRAWTURB) smaller than 64 x 64 (GHOSTFENCE-NO-ANIMATION-46): Quake's
 * Turbulent8 (d_scan.c) reads a 64 x 64 texture, so the loader tiles it to 64 x 64. A texture repeated 2 x 2
 * shows the same texels at every texture coordinate as the small one repeating, so the faces' mapping holds. */
#define CHIM_TURB_SIZE	64
#define CHIM_TURB_PIXELS	(CHIM_TURB_SIZE*CHIM_TURB_SIZE/64*85)
int ChimFormat_TurbulentTile (const char *name, int width, int height);
void ChimFormat_TileTurbulent (const unsigned char *src, int width, int height, unsigned char *dst);

#endif
