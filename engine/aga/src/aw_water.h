/* SPDX-License-Identifier: GPL-2.0-or-later
 * A room's water level, as the scripts read it (GETWATERLEVEL-COLUMN-NOT-ROOM-67, v0.0.68).
 *
 * The rule is OpenMW 0.51's (apps/openmw/mwscript/cellextensions.cpp OpGetWaterLevel, lines 181-199): outdoors the
 * reading is 0 (the original's oddity), in an interior cell with the water flag it is the cell's own level, in an
 * interior without the flag it is the lowest float. The level of a cell starts as its record's (CELL INTV or WHGT;
 * the flag alone: 0; components/esm3/loadcell.cpp lines 129-159, apps/openmw/mwworld/cellstore.cpp line 612).
 *
 * The builder writes the levels into the script file's WATR section (tools/mwscript/awms.py): 8 bytes a room with the
 * water flag, ascending by the room's stable number (the room map's worldspawn _aw_cell_int): u16 the number, u8 flags
 * (AW_WATER_FLAG), u8 0, f32 the level in the original's units, big-endian. The engine looks the loaded room up once
 * per map (aw_mwhost.c attach_map) and keeps the level; a script reads it with no search of the map.
 *
 * Pure functions (aw_water_rules.c; tests/aga_water_rules_test.c). */
#ifndef AW_WATER_H
#define AW_WATER_H

#define AW_WATER_ROW_BYTES 8
#define AW_WATER_FLAG 1u            /* the room's cell carries the water flag (CELL flags 0x02) */

/* where the player is, as the script host's player cell says (aw_mwhost.c host_player_cell) */
#define AW_WATER_NOWHERE 0
#define AW_WATER_OUTDOORS 1
#define AW_WATER_ROOM 2

/* The row of room NUMBER in the WATR rows ROWS (COUNT of them): 1 and its level in *LEVEL when the room is listed with
 * the water flag, else 0 (*LEVEL untouched). A binary search; the rows must be ascending (the builder writes them so). */
int AW_WaterRow(const unsigned char *rows, unsigned long count, unsigned long number, float *level);

/* What GetWaterLevel reads: WHERE one of AW_WATER_*; FOUND 1 when the room has the water flag, its LEVEL then. */
float AW_WaterReading(int where, int found, float level);

/* The lowest float: the reading in a room without water (OpenMW: -std::numeric_limits<float>::max()). */
float AW_WaterNone(void);

/* SetWaterLevel / ModWaterLevel (MWSCRIPT-WATER-LEVEL-STATIC-67, v0.0.68; OpenMW 0.51 cellextensions.cpp
 * OpSetWaterLevel / OpModWaterLevel, lines 201-245): the room's level after a call with VALUE, the level NOW (MOD 1:
 * ModWaterLevel adds, 0: SetWaterLevel sets). */
float AW_WaterLevelAfter(int mod, float now, float value);
/* Whether such a call changes anything: in a room (WHERE AW_WATER_ROOM) whose cell has the water flag (FOUND 1). An
 * exterior stops OpenMW's script with an error; a room without the flag saves no level there: both counted, nothing
 * changed. */
int AW_WaterCallChanges(int where, int found);
/* The saved fact of room NUMBER's level (the world change list's named facts): "amiwind:water:<number>" into OUT. */
void AW_WaterFactId(char out[32], unsigned long number);
/* A level kept in a fact's 32 bits and back, exactly (its float's bits). */
long AW_WaterFactValue(float level);
float AW_WaterFactLevel(long value);

/* The plane (aw_water.c): found in the loaded room's world at the map's attach (1 when movable: the root node a level
 * plane with the two "*water" faces, the open air in front, water behind), moved to Z (map units, clamped into the
 * room's box), its Z now; the status line; the cvar and the reset at init. */
int AW_WaterPlaneFind(void);
int AW_WaterPlaneMovable(void);
int AW_WaterPlaneSet(float z);
float AW_WaterPlaneZ(void);
void AW_WaterPlaneStatus(void);
void AW_WaterInit(void);
/* The CHIM room's placements whose box the plane passed, from OLD_Z to NEW_Z, linked again: defined by the room
 * loader (chim/chim_room.c, ChimRoom_WaterMoved), called by AW_WaterPlaneSet on every move; NULL: none. */
extern void (*aw_water_relink)(float old_z, float new_z);

#endif
