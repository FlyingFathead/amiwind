/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPC model levels of detail (aw_npc_lod.c; docs/NPC_MODEL_CACHE.md "NPC model
 * levels of detail"). A render-only swap: each actor is drawn with the finest
 * level its distance band allows that fits the level byte budget; the map's own
 * model (level 1) otherwise. Collision, QuakeC and the entity's frame are
 * untouched; every level has the same frame list. */
#ifndef AW_NPC_LOD_H
#define AW_NPC_LOD_H

#define AW_NPC_LOD_MANIFEST "progs/npc-lod.txt"
#define AW_NPC_LOD_LEVELS 4     /* 0 near, 1 the map's own model, 2 mid, 3 far */
#define AW_NPC_LOD_MAP_LEVEL 1
#define AW_NPC_LOD_ROWS 128     /* appearances kept for one map (its precached models) */
#define AW_NPC_LOD_TRACK 256    /* actors whose level is remembered (hysteresis), power of two */
#define AW_NPC_LOD_CANDIDATES 128
#define AW_NPC_LOD_PATH 64
/* A level model's cache block beyond its file bytes: header, frame descriptors and
 * block padding (Mod_TryStreamAlias), rounded up generously. */
#define AW_NPC_LOD_OVERHEAD 2048

void AW_NpcLodInit(void);
/* Free the level models and forget the map's table (Host_ClearMemory, before Mod_ClearAll). */
void AW_NpcLodReset(void);
/* Once a frame, before the entity list is drawn (r_origin set). */
void AW_NpcLodFrame(void);
/* The model to draw for an entity this frame: one of its levels or its own model. */
model_t *AW_NpcLodModel(entity_t *e);
/* Level models resident now (all levels but the map's own) and their bytes. */
int AW_NpcLodResident(int *bytes);

/* dbg npclod (command aw_npclod): the parsed form; host-tested. */
enum { AW_NPCLOD_NONE, AW_NPCLOD_STATS, AW_NPCLOD_FORCE, AW_NPCLOD_TARGET, AW_NPCLOD_SHOW, AW_NPCLOD_BANDS };
typedef struct {
    int kind;
    int level;          /* FORCE/TARGET: the level, -1 auto; SHOW: 1 on, 0 off, -1 toggle */
    int bands[AW_NPC_LOD_LEVELS - 1];
} aw_npclod_cmd_t;
int AW_NpcLodParseCommand(int argc, const char **argv, aw_npclod_cmd_t *out);
/* The labels of dbg npclod show, drawn with the HUD (Sbar_Draw). */
void AW_NpcLodDrawLabels(void);
/* Alias triangles drawn: this frame so far and the last whole frame (r_alias.c counts). */
extern int aw_alias_tris_frame, aw_alias_tris_last;

/* Decode one level table row ("<map model> <use 0|1> <bytes L0> <L1> <L2> <L3>"); 1 on success. */
int AW_NpcLodParseRow(const char *line, char *far, int *use, int bytes[AW_NPC_LOD_LEVELS]);
/* Level LEVEL's file of map model FAR (progs/lK/<name>; level 1: FAR itself); 0 if it does not fit. */
int AW_NpcLodLevelPath(const char *far, int level, char *out, int size);
/* The band level for distance D (Quake units) given band edges and the previous level:
 * a band edge moves 5 % away from the side the actor is on (10 % hysteresis). */
int AW_NpcLodBand(float d, const float edges[AW_NPC_LOD_LEVELS - 1], int previous);

#endif
