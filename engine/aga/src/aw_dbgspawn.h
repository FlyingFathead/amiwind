/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg spawn (DBG-SPAWN-MENU-67): the people and creatures of the build in a list box like dbg tp's (find, their names,
 * the buttons All / NPCs / Creatures, a line of the selected one's properties, the switch "spawn in with base
 * attributes", on by default); the chosen one appears in front of the player (aw_mwhost.c AW_MwscriptSpawn). The rules
 * below have no engine dependencies (tests/aga_dbgspawn_test.c builds aw_dbgspawn.c with AW_DBGSPAWN_RULES_ONLY). */
#ifndef AW_DBGSPAWN_HEADER
#define AW_DBGSPAWN_HEADER

#define AW_SPAWN_LABEL 72        /* a row's label: the name, a tab, the record id (the list box shows the id dimmer) */
#define AW_SPAWN_DETAIL 96       /* the selected row's line */
enum {AW_SPAWN_CAT_ALL=0,AW_SPAWN_CAT_NPC,AW_SPAWN_CAT_CREATURE,AW_SPAWN_CATS};

/* What the line of properties says: the record's kind (0 NPC, 1 creature), level, health, magicka, Fight and Flee, a
 * creature's type (0 creature, 1 daedra, 2 undead, 3 humanoid: the record's), an NPC's race and class as written. */
typedef struct {int kind,level,health,magicka,fight,flee,type;char race[32],cls[32];} aw_spawn_facts_t;

/* "Name<tab>id" into OUT (SIZE bytes), the id alone when NAME is empty; the name gives way to keep the whole id. The
 * length, -1 when the id does not fit or is empty. */
int AW_SpawnLabel(const char *name,const char *id,char *out,int size);
/* The record id of a label (the part after the tab, or the whole label) into OUT; 1 when it fits. */
int AW_SpawnLabelId(const char *label,char *out,int size);
/* Labels in the list's order: by name, case ignored, then by id; <0, 0, >0. */
int AW_SpawnCompare(const char *a,const char *b);
/* The line of properties: "Level 5, health 60, magicka 20, Fight 30<tab>Dark Elf Commoner" (a creature: "<tab>creature",
 * "daedra", ...). The length. */
int AW_SpawnDetail(const aw_spawn_facts_t *f,char *out,int size);
/* The second word of dbg spawn ID [WORD]: none, "full" or "attributes" 1 (its base attributes), "model" or
 * "placeholder" 0 (its model only); -1 anything else. */
int AW_SpawnHow(const char *word);

#endif
