/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_SAVE_H
#define AW_SAVE_H
#include <stdint.h>
#include "aw_story.h"
#include "aw_character.h"
struct aw_ledger_s;
/* 256 KiB (was 64 KiB): room for the world-state change list (feature 8); a save without changes is the same
 * bytes as before, and any save of the old size limit still loads. */
#define AW_SAVE_BYTES 262144
/* CELL-CHANGES-59: a save with the world change list (feature 32) is AW_SAVE_BYTES plus the list's own bytes, so a
 * long game never meets a full save; a file is read only up to this many bytes (the list's own ceiling,
 * aw_ledger.h AW_LEDGER_ROWS rows, needs far less). */
#define AW_SAVE_MAX_BYTES 4194304
#define AW_SAVE_ACTORS 256
/* The world-state change list (CHIM type 1 actors: aw_actors.c), AWS4 feature bit 8; an older reader refuses a save
 * that has it. Key rule (template S0d): bits 0-23 the game's reference, bit 31 a builder-made object (the intro
 * roles: AW_CHANGE_BUILDER | role; old AWS4 actor rows say 0x800000 + role), bits 24-30 always 0 (the pieces of a
 * cut object share their source's state). */
#define AW_SAVE_CHANGES 2048
#define AW_CHANGE_BUILDER 0x80000000U
#define AW_CHANGE_DEAD 1U        /* killed: not spawned again (no respawn yet) */
#define AW_CHANGE_MOVED 2U       /* POSITION, YAW and HEALTH hold where and how it was left */
#define AW_CHANGE_FIGHT 4U       /* in a fight with the player when it was captured */
#define AW_CHANGE_FOLLOW 8U      /* following the player (the companion) when it was captured */
#define AW_CHANGE_PICK 16U       /* PICK holds a levelled list's roll */
#define AW_CHANGE_SCENE 32U      /* WHERE is a logical scene id (an old AWS4 actor row), else a cell */
/* Object state (v0.0.51, the scripts' Disable and Lock; aw_mwhost.c): an entry may carry only these. */
#define AW_CHANGE_DISABLED 64U   /* Disable: hidden and not solid until Enable */
#define AW_CHANGE_LOCK 128U      /* a script set its lock: the level (0 unlocked .. 100) in AW_CHANGE_LOCK_LEVEL */
#define AW_CHANGE_LOCK_SHIFT 8
#define AW_CHANGE_LOCK_LEVEL 0x7F00U
/* v0.0.57 (SAVEGAME-COMPLETE-57): WHERE is a room's stable number (worldspawn _aw_cell_int) and POSITION is
 * room-local; never with AW_CHANGE_SCENE */
#define AW_CHANGE_ROOM 0x8000U
#define AW_CHANGE_FLAGS (63U|AW_CHANGE_DISABLED|AW_CHANGE_LOCK|AW_CHANGE_LOCK_LEVEL|AW_CHANGE_ROOM)
#define AW_CHANGE_ENTRY_BYTES 36
typedef struct {
    uint32_t key;
    uint32_t flags,pick;         /* pick: 1 nothing, 2 + the actor table base it gave */
    int32_t where;               /* cell x << 16 | (cell y & 0xffff), or a scene id (AW_CHANGE_SCENE) */
    float position[3],yaw,health;/* island position (Quake units), or scene-local for AW_CHANGE_SCENE */
    float hours;                 /* game time when captured (hours since the game's start) */
} aw_change_t;
/* AWS4 feature bit 16: the actor record's block (aw_actorstate.c AW_ActorStateExport, AWAS1), at most this many
 * bytes; an older reader refuses a save that has it. */
#define AW_SAVE_ACTOR_BYTES 32768
typedef struct {
    int count;
    aw_change_t entry[AW_SAVE_CHANGES];
    /* the actor block: a caller's buffer of ACTOR_CAPACITY bytes, ACTOR_BYTES used (0: none); NULL: not wanted */
    unsigned char *actors;
    int actor_bytes,actor_capacity;
    /* AWS4 feature bit 32 (CELL-CHANGES-59): the world change list of objects (aw_ledger.h), written when it has a
     * row, read back into it (NULL: checked, not kept); an older reader refuses a save that has it */
    struct aw_ledger_s *ledger;
    /* AWS4 feature bit 128 (JOURNAL-ORIGINAL-VIEW-59): the dated journal history (aw_jhist.h), written when it has an
     * entry, read back into it (NULL: checked, not kept); an older reader refuses a save that has it */
    struct aw_jhist_s *journal;
} aw_changes_t;
/* aw_save.c AW_SaveInit sets these to aw_jhist.c's (NULL in the codec's tests that do not link it): without them the
 * history is not written and a save that has one does not decode. */
extern int (*aw_save_journal_encode)(const struct aw_jhist_s *h,unsigned char *out,int capacity);
extern int (*aw_save_journal_decode)(const unsigned char *data,int size,struct aw_jhist_s *into);

#define AW_EQUIPMENT_DRAWN 1U
#define AW_EQUIPMENT_TORCH 2U
#define AW_EQUIPMENT_MASK (AW_EQUIPMENT_DRAWN|AW_EQUIPMENT_TORCH)
typedef struct {
    uint32_t reference;
    int scene;
    float position[3],angles[3],health;
    int hello_count,manual_count,hello_done;
} aw_saved_actor_t;
typedef struct {
    uint32_t sequence,profile;
    uint32_t equipment; /* AWS4 intent flags; older saves default to hidden. */
    unsigned char content[32];
    char scene[16],label[32];
    float position[3],angles[3];
    aw_story_t story;
    aw_state_t state;
    aw_character_t character;
    int actor_count;
    aw_saved_actor_t actors[AW_SAVE_ACTORS];
} aw_save_t;
int AW_SaveEncode(unsigned char *out,int capacity,const aw_save_t *state);
int AW_SaveDecode(const unsigned char *data,int size,aw_save_t *out);
/* INVENTORY-ORIGINAL-LIMITS-61: a decoded save owns its item table (aw_state.h OWNERSHIP): the rows given back. A save
 * whose state became the game's (AW_SaveSpawn) or that was never decoded holds none. */
void AW_SaveRelease(aw_save_t *save);
void AW_SaveInit(void);
void AW_SaveReset(void);
int AW_SaveAllowed(void);
void AW_SaveTick(void);
void AW_SaveCapture(void);
int AW_SaveSnapshot(aw_save_t *snapshot);
void AW_SaveSnapshotRestore(const aw_save_t *snapshot);
void AW_SaveSpawn(void);
void AW_SaveSchedule(void);
/* GAME-RECORDER-61 (aw_recorder.c): the game encoded now without a file (the caller frees it; the character's profile
 * and sequence, 0 when none, in the two out values); a save loaded from such bytes; 1 while a load waits for its spawn */
unsigned char *AW_SaveEncodeNow(int *size,uint32_t *profile,uint32_t *sequence);
int AW_SaveLoadBytes(const unsigned char *raw,int size,uint32_t profile,uint32_t sequence);
int AW_SaveLoadPending(void);
int AW_SaveWrite(int slot);
int AW_SaveRead(uint32_t profile,int slot);
int AW_SaveProfiles(uint32_t *ids,char names[][32],int capacity);
int AW_SaveDescription(uint32_t profile,int slot,char *out,int capacity);
/* Why a slot has no loadable save (AW25-06: the load menu said "(empty)" for all of them alike). */
enum {AW_SLOT_EMPTY,AW_SLOT_UNREADABLE,AW_SLOT_OTHER_DATA,AW_SLOT_OK};
int AW_SaveSlotState(uint32_t profile,int slot);
int AW_SaveLatest(uint32_t profile,char *label,int capacity);
uint32_t AW_SaveProfile(void);
int AW_AutosaveCount(void);
void AW_SetAutosaveCount(int count);
int AW_SaveMenuOpen(int loading);
int AW_SaveMenuActive(void);
int AW_SaveMenuKey(int key);
void AW_SaveMenuDraw(void);
/* Encode with a change list (NULL or empty: exactly AW_SaveEncode's bytes) / decode one (CHANGES NULL: checked,
 * not kept). Entries are written sorted by key; a key appears once. */
int AW_SaveEncodeChanges(unsigned char *out,int capacity,const aw_save_t *state,const aw_changes_t *changes);
int AW_SaveDecodeChanges(const unsigned char *data,int size,aw_save_t *out,aw_changes_t *changes);
/* An old save's actor rows as change entries ("moved + health", WHERE = the row's scene): appended to CHANGES
 * for rows whose key is not in it yet. Returns the number added. */
int AW_SaveFoldActors(const aw_save_t *state,aw_changes_t *changes);
/* The change list's own key of an AWS4 actor row's reference (0x800000 + role -> AW_CHANGE_BUILDER | role). */
uint32_t AW_SaveChangeKey(uint32_t reference);
/* aw_actors.c sets these (NULL in builds and tests without it): export the session's changes for a save, import
 * a loaded save's changes before the window spawns its actors. */
extern int (*aw_save_changes_export)(aw_changes_t *changes);
extern void (*aw_save_changes_import)(const aw_changes_t *changes);
/* aw_mwhost.c sets these: the object state (AW_CHANGE_DISABLED, AW_CHANGE_LOCK) merged by key into the list the
 * actors exported (after it), and read from a loaded save's list (after the actors' import). With the world change
 * list on (aw_placed ledger, the default) the export adds nothing (the objects are in feature 32) and the import
 * reads an older save's object entries into the list. */
extern int (*aw_save_objects_export)(aw_changes_t *changes);
extern void (*aw_save_objects_import)(const aw_changes_t *changes);
/* aw_mwhost.c sets these: the actor record's block (feature 16): export the bytes (0 none, -1 too small), import a
 * loaded save's block (BYTES 0: none, the records start from their rows). */
extern int (*aw_save_actors_export)(unsigned char *out,int capacity);
extern void (*aw_save_actors_import)(const unsigned char *data,int bytes);
/* aw_mwhost.c sets these (CELL-CHANGES-59 slice 4; NULL without the compiled scripts): before a save, the scripts'
 * globals that differ from the data, the quest stages and the known topics are written into the list's tables; after
 * a load, read back from them (an older save without them: the data's start, the 32-slot journal folded in). */
extern void (*aw_save_script_export)(struct aw_ledger_s *ledger);
extern void (*aw_save_script_import)(const struct aw_ledger_s *ledger);
/* aw_save.c AW_SaveInit sets these to aw_ledger.c's (CELL-CHANGES-59; NULL in the codec's tests that do not link
 * it): the rows of a list, its saved form (aw_ledger.h AW_LedgerEncode / AW_LedgerDecode). Without them a list is
 * not written and a save that has one does not decode. */
extern int (*aw_save_ledger_rows)(const struct aw_ledger_s *ledger);
extern int (*aw_save_ledger_encode)(const struct aw_ledger_s *ledger,unsigned char *out,int capacity);
extern int (*aw_save_ledger_decode)(const unsigned char *data,int size,struct aw_ledger_s *into);
/* aw_scene.c AW_SceneSaveEntryRefuse (bound in aw_debug.c; NULL: no check): 1 when the saved scene and position lie
 * in a place marked for more Fast RAM than this start has; the refusal screen is up (CHIM-32MB-SAVE-ENTRY-48). */
extern int (*aw_save_entry_refuse)(const char *scene,const float *position);
/* CELL-CHANGES-59 slice 7: 1 while a save of other game data or another build is being loaded (migrated: what names
 * another build's table rows is left out) */
extern int aw_save_migrating;
/* the slice 7 hooks (aw_mwhost.c binds them to aw_inventory.c's reference identity table and aw_actorstate.c): a save
 * of other game data can be migrated here; a save's record hashes and content files; a loaded list migrated (-1 no
 * table; else the changes dropped, by part in DROPPED, an aw_ledger_dropped_t); the actor records and dead counts of
 * another build's actor table dropped (how many) */
extern int (*aw_save_other_ok)(void);
extern void (*aw_save_ident_refresh)(struct aw_ledger_s *ledger);
extern long (*aw_save_migrate)(struct aw_ledger_s *ledger,void *dropped);
extern int (*aw_save_drop_actor_records)(void);
extern void (*aw_save_notice)(const char *line);   /* the on-screen line of a migrated load */
/* a new game's state begins (AW_SaveReset): the scripts start the original's run-once new-game scripts
 * (aw_mwhost.c AW_MwscriptNewGame, NPC-STORY-DISABLED-AT-START-42) */
extern void (*aw_save_new_game)(void);
#endif
