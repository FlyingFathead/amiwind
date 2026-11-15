/* SPDX-License-Identifier: GPL-2.0-or-later
 * The explored map (MAP-ORIGINAL-POI-66 stage 2): every exterior cell the player has walked in keeps a
 * 8 x 8 grid of bits (OpenMW's local map fog uses 32 x 32 texels per cell and reveals within 0.17 of a cell width
 * around the player, localmap.cpp updatePlayer; the original's saves hold 16 x 16; 8 x 8 keeps a whole explored
 * island at about 17 KB, docs/WORLD_MAP_AND_JOURNAL.md "Explored land"). A bit is set once its square of the cell
 * (1024 x 1024 source units) has its centre within that radius of the player and is never cleared, except by New
 * Game. Only cells walked in have a row (AW_MAPFOG_ROW_BYTES: x, y, 8 bytes of bits), in blocks of 64 rows; saved
 * with the game (AWFG: a fully explored cell as 5 bytes, else 13) and read back with it.
 *
 * MAP-EXPLORED-SAVE-BLOCK-66: the save writes it in a section of its own (aw_save.h feature 4096), as long as it
 * needs; a save never refuses it. Saves of v0.0.66-dev1 and dev2 have it inside the actor block and still load.
 *
 * Pure C; allocations through aw_tryalloc.h (native test: tests/aga_mapfog_test.c). */
#ifndef AW_MAPFOG_H
#define AW_MAPFOG_H
#define AW_MAPFOG_GRID 8              /* squares per cell side */
#define AW_MAPFOG_CELL 8192.0f         /* source units per cell */
#define AW_MAPFOG_RADIUS (0.17f*8192.0f)
#define AW_MAPFOG_BLOCK 64             /* rows per allocation */
#define AW_MAPFOG_MAX 8192             /* rows at most: a damaged-file guard, five times the island's and Solstheim's
                                        * under 1,600 land cells (was 2,048: a 2,049th cell was silently not remembered;
                                        * the save contract, 2026-11-14); costs nothing until the rows are used */
#define AW_MAPFOG_ROW_BYTES 12         /* one land row in memory: x, y (2 bytes each), 8 bytes of bits */
void AW_MapFogReset(void);
/* reveal around the source point X, Y; 1 when a new bit was set */
int AW_MapFogReveal(float x,float y);
/* 1 when the square holding the source point X, Y is explored */
int AW_MapFogSeen(float x,float y);
int AW_MapFogCells(void);
/* row I: its cell X, Y and its bits (row-major from the cell's south-west square, bit = y*GRID+x); 0 past the end */
int AW_MapFogRow(int i,int *x,int *y,const unsigned char **bits);
/* "AWFG" u16 rows, each <hh> cell x, y, a u8 (1 all explored, 0 the 8 bytes of bits follow), then the rooms (below).
 * OUT NULL: the bytes the whole map needs (0 when nothing is explored: no section to write). Else it writes into
 * CAPACITY and returns the bytes written: every land row (the fully explored cells first, 5 bytes each, then the
 * others), never a part of the land (0 when the land does not fit: nothing written), then the rooms that fit, the fully
 * explored first; what was left out is counted (AW_MapFogLeftOut). The save sizes the section to the whole need. */
int AW_MapFogExport(unsigned char *out,int capacity);
/* the land cells and the rooms the last export with an OUT could not write (0 and 0 when it wrote everything) */
void AW_MapFogLeftOut(int *cells,int *rooms);
/* bytes read, -1 when broken (then nothing is kept) */
int AW_MapFogImport(const unsigned char *p,int bytes);
/* Stage 3: the explored part of each interior room (its map name, up to 15 letters): a 16 x 16 grid of bits over the
 * room's own box (the loaded map's mins/maxs, engine units, x and y), opened within AW_MAPFOG_ROOM_RADIUS engine units
 * of the player the way the land opens; rooms in blocks of AW_MAPFOG_ROOM_BLOCK, at most AW_MAPFOG_ROOMS. Saved
 * inside AWFG after the land rows as an optional "AWFI" part (u16 rooms, each u8 name length, the name, u8 1 all
 * explored / 0 + 32 bytes); a save without it reads as before.
 * MAP-EXPLORED-ROOMS-CAP-66: 2,048 rooms (was 256): every room of the base game and both expansions (about 1,750:
 * 1,328 batch rooms, 149 town rooms, the first towns' and the expansions' 103 each) with room to spare. A room costs
 * AW_MAPFOG_ROOM_BYTES (48: the name and 32 bytes of bits) plus 4 bytes of its name index (an index of twice the
 * rooms' capacity, 2 bytes a slot); found by the index or the last room asked for, never by a search of every name. */
#define AW_MAPFOG_ROOM_GRID 16
#define AW_MAPFOG_ROOM_RADIUS 384.0f
#define AW_MAPFOG_ROOMS 2048
#define AW_MAPFOG_ROOM_BLOCK 64
#define AW_MAPFOG_ROOM_BYTES 48
#define AW_MAPFOG_ROOM_INDEX_BYTES 4   /* the name index's share of one room: two 2-byte slots */
int AW_MapFogRoomReveal(const char *room,float x,float y,const float *mins,const float *maxs);
int AW_MapFogRoomSeen(const char *room,float x,float y,const float *mins,const float *maxs);
/* the room's 32 bytes of bits (bit = gy*AW_MAPFOG_ROOM_GRID+gx over its box), NULL when it has none: one lookup for a
 * whole picture (aw_worldui.c draws the local map from it) */
const unsigned char *AW_MapFogRoomBits(const char *room);
int AW_MapFogRooms(void);
/* the bytes the explored map holds now (rows, rooms and the rooms' index, as allocated) */
unsigned long AW_MapFogBytes(void);
#endif
