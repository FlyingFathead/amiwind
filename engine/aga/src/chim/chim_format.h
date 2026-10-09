/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM world formats 0.4 to 0.6 as the engine reads them
 * (docs/chim/WORLD_FORMAT.md). 0.5 adds the story-hidden placement flag and
 * irregular ground with the same layout; 0.6 puts the sector files of a large
 * frame into one folder per sector row, which the index's file table names,
 * so the records are unchanged:
 * decoders for the big-endian CHIM structures (index, frame file, sector
 * files, chunk records and placement records). Brush images inside the
 * sector files stay little-endian BSP29 and go through model.c's section
 * loaders. The builder side (tools/chim/format.py) defines the layout; this
 * file must follow it byte for byte.
 */
#ifndef CHIM_FORMAT_H
#define CHIM_FORMAT_H

#define CHIM_FORMAT_MAJOR	0
#define CHIM_FORMAT_MINOR	6
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
#define CHIM_RECORD_BYTES		48
#define CHIM_RECORD_OVER_16_LEAVES	1	/* record flag: reaches more than MAX_ENT_LEAFS */
#define CHIM_RECORD_STORY_HIDDEN	2	/* record flag (0.5): hidden by the opening story */
#define CHIM_INDEX_NAME			"chim/world.cwi"
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
} chim_chunk_head_t;

typedef struct
{
	unsigned	pid, ref, model;
	float		origin[3], yaw;
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
int ChimFormat_Record (const unsigned char *p, chim_record_t *out);

#endif
