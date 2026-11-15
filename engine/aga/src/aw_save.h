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
/* SAVE-ACTOR-ROWS-256-66: the saved actor rows (aw_save.c AW_SaveCapture, AW_SaveSpawn) are an open list, sorted by
 * scene and reference, holding for every NPC and creature of every place what no other part of the save holds:
 * - an actor of the game data (its reference in the change list, aw_actors.c, and its record in the actor records,
 *   aw_actorstate.c, which hold its place, facing, health, death, fight and follow): its greeting counters, only when
 *   one is set (AW_ROW_GREET);
 * - a role the builder made (the intro's, no game reference): its place, health and counters, as always.
 * An actor whose rows hold nothing has none; a row of an actor not loaded now stays as it was. A save writes the rows
 * packed (AWS4 feature 8192: a 3-byte reference, a byte of what follows, only that: 4 to 5 bytes a greeted NPC);
 * the 48-byte rows of saves before v0.0.66 (in the save's fixed fields, at most AW_SAVE_ACTORS, 256) still load, and
 * aw_save_rows_form 1 writes them for tests. Rows grow in blocks of AW_SAVE_ACTOR_ROW_BLOCK; AW_SAVE_ACTOR_ROWS_MAX
 * (four times every NPC reference of the base game and both expansions, about 3,300) bounds a count: a capture past it,
 * or one memory refuses, refuses the save with a line, never a row left out unsaid. */
#define AW_SAVE_ACTORS 256
#define AW_SAVE_ACTOR_ROWS_MAX 16384
#define AW_SAVE_ACTOR_ROW_BLOCK 64
#define AW_SAVE_ACTOR_ROW_BYTES 48     /* one row in memory (aw_saved_actor_t) */
#define AW_ROW_PLACE 1U                /* POSITION and ANGLES hold where it was left */
#define AW_ROW_HEALTH 2U               /* HEALTH holds its health */
#define AW_ROW_GREET 4U                /* HELLO_COUNT, MANUAL_COUNT and HELLO_DONE hold its greetings */
#define AW_ROW_ALL 7U
extern int aw_save_rows_form;          /* 0: packed (feature 8192, the default); 1: the 48-byte rows before v0.0.66 */
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
/* AWS4 feature bit 16: the actor record's block (aw_actorstate.c AW_ActorStateExport, AWAS1, and the blocks after it,
 * aw_mwhost.c actors_export); an older reader refuses a save that has it.
 * MAP-EXPLORED-SAVE-BLOCK-66: its size is the setting aw_save_block_kb (AW_SaveBlockBytes: 64 KB by default, 32 to
 * 256), in a buffer taken only while a save is written and one of the loaded block's own size while a load waits for
 * its spawn (was two fixed 32 KB buffers for the whole game). A block of up to AW_SAVE_ACTOR_MAX_BYTES loads, so every
 * save of the 32 KB block before it does. */
#define AW_SAVE_ACTOR_BYTES 32768      /* the block's size before v0.0.66; the save buffer always holds this much */
#define AW_SAVE_BLOCK_KB_MIN 32
#define AW_SAVE_BLOCK_KB_MAX 256
#define AW_SAVE_BLOCK_KB_DEFAULT 64
#define AW_SAVE_ACTOR_MAX_BYTES (AW_SAVE_BLOCK_KB_MAX*1024)
/* the block's bytes for the setting KB: clamped to 32..256 KB (NaN: the default), whole KB */
int AW_SaveBlockBytes(float kb);
typedef struct {
    int count;
    aw_change_t entry[AW_SAVE_CHANGES];
    /* the actor block: a caller's buffer of ACTOR_CAPACITY bytes, ACTOR_BYTES used (0: none); NULL: not wanted.
     * TAKE 1 (a load, MAP-EXPLORED-SAVE-BLOCK-66): the decoder takes a buffer of each kept section's own size, once
     * the whole save is good (ACTORS, EXPLORED_DATA; AW_TryMalloc), and AW_SaveChangesFree gives them back */
    unsigned char *actors;
    int actor_bytes,actor_capacity;
    int take;
    /* AWS4 feature bit 32 (CELL-CHANGES-59): the world change list of objects (aw_ledger.h), written when it has a
     * row, read back into it (NULL: checked, not kept); an older reader refuses a save that has it */
    struct aw_ledger_s *ledger;
    /* AWS4 feature bit 128 (JOURNAL-ORIGINAL-VIEW-59): the dated journal history (aw_jhist.h), written when it has an
     * entry, read back into it (NULL: checked, not kept); an older reader refuses a save that has it */
    struct aw_jhist_s *journal;
    /* AWS4 feature bit 2048 (MAP-MULTI-MARKERS-66): the player's map markers (aw_mapmarks.h, AWMK), written when
     * MARKERS is 1 and there is one; read back as the pending load when MARKERS is 1 (0: checked, not kept) */
    int markers;
    /* AWS4 feature bit 4096 (MAP-EXPLORED-SAVE-BLOCK-66): the explored map (aw_mapfog.h AWFG) in a section of its own,
     * as long as it needs (it was in the actor block, where a well explored map could refuse the whole save):
     * written when EXPLORED is 1 and the map has a cell or a room; read back, with TAKE, into EXPLORED_DATA
     * (EXPLORED_BYTES long; NULL: none in the save, the actor block's of a v0.0.66-dev save stands) */
    int explored;
    unsigned char *explored_data;
    int explored_bytes;
} aw_changes_t;
/* the sections a TAKE decode kept, given back (a caller's own ACTORS buffer is never freed) */
void AW_SaveChangesFree(aw_changes_t *changes);
/* the bytes the last decode could not take for lack of memory (0: none; the load then says so) */
int AW_SaveDecodeShort(void);
/* aw_mwhost.c binds these to the explored map (aw_mapfog.c; NULL: no section written, one read is left out):
 * ENCODE as AW_MapFogExport (OUT NULL: the bytes it needs, 0 nothing to keep), IMPORT a loaded save's section at its
 * spawn, after the actor block */
extern int (*aw_save_explored_encode)(unsigned char *out,int capacity);
extern void (*aw_save_explored_import)(const unsigned char *p,int bytes);
/* aw_save.c AW_SaveInit sets these to aw_jhist.c's (NULL in the codec's tests that do not link it): without them the
 * history is not written and a save that has one does not decode. */
extern int (*aw_save_journal_encode)(const struct aw_jhist_s *h,unsigned char *out,int capacity);
extern int (*aw_save_journal_decode)(const unsigned char *data,int size,struct aw_jhist_s *into);
/* aw_worldui.c AW_WorldUIInit sets these to aw_mapmarks.c's (NULL without the map: none written, a save with the
 * block does not decode); LOADED runs when a loaded save becomes the game's, RESET at New Game */
extern int (*aw_save_markers_encode)(unsigned char *out,int capacity);
extern int (*aw_save_markers_decode)(const unsigned char *p,int n,int commit);
extern void (*aw_save_markers_loaded)(void);
extern void (*aw_save_markers_reset)(void);

#define AW_EQUIPMENT_DRAWN 1U
#define AW_EQUIPMENT_TORCH 2U
#define AW_EQUIPMENT_MASK (AW_EQUIPMENT_DRAWN|AW_EQUIPMENT_TORCH)
typedef struct {
    uint32_t reference;
    unsigned short scene;          /* the place's save ID (aw_maps.h AW_MapLogicalId: up to AW_LAYER_ROOM_END) */
    unsigned short fields;         /* AW_ROW_*: what the row holds */
    float position[3],angles[3],health;
    int hello_count,manual_count,hello_done;
} aw_saved_actor_t;
typedef char aw_saved_actor_bytes_check[sizeof(aw_saved_actor_t)==AW_SAVE_ACTOR_ROW_BYTES?1:-1];
/* OWNERSHIP of the actor rows (SAVE-ACTOR-ROWS-256-66), as of the item table (aw_state.h): the rows belong to the
 * aw_save_t they were made for (the game's, a decoded save, a snapshot); a copy by value shares them;
 * AW_SaveActorsCopy gives a copy its own, AW_SaveRelease (or AW_SaveActorsFree) gives them back. */
typedef struct {
    uint32_t sequence,profile;
    uint32_t equipment; /* AWS4 intent flags; older saves default to hidden. */
    unsigned char content[32];
    char scene[16],label[32];
    float position[3],angles[3];
    aw_story_t story;
    aw_state_t state;
    aw_character_t character;
    int actor_count,actor_capacity;
    aw_saved_actor_t *actors;
} aw_save_t;
/* the row of REFERENCE in SCENE: its index, or -1 - the index it would take */
int AW_SaveActorFind(const aw_save_t *s,uint32_t reference,int scene);
/* room for WANT rows; 0 when memory says no or WANT is past AW_SAVE_ACTOR_ROWS_MAX (the rows as they were) */
int AW_SaveActorsReserve(aw_save_t *s,int want);
/* TO's rows become a copy of COUNT ROWS of its own (TO's earlier rows are not given back: the caller's); 0 memory */
int AW_SaveActorsCopy(aw_save_t *to,const aw_saved_actor_t *rows,int count);
void AW_SaveActorsFree(aw_save_t *s);
/* the bytes S's rows take in a save (feature 8192 with its length word; 0 when no row holds anything) */
int AW_SaveActorRowsBytes(const aw_save_t *s);
int AW_SaveEncode(unsigned char *out,int capacity,const aw_save_t *state);
int AW_SaveDecode(const unsigned char *data,int size,aw_save_t *out);
/* INVENTORY-ORIGINAL-LIMITS-61: a decoded save owns its item table (aw_state.h OWNERSHIP): the rows given back. A save
 * whose state became the game's (AW_SaveSpawn) or that was never decoded holds none. */
void AW_SaveRelease(aw_save_t *save);
void AW_SaveInit(void);
void AW_SaveReset(void);
int AW_SaveAllowed(void);
void AW_SaveTick(void);
/* the loaded place's actors into the saved actor rows (a save, a snapshot, leaving the place); 0 when memory or the
 * rows' bound refused it (said on the console; a save is then refused) */
int AW_SaveCapture(void);
/* one actor's row as it is now, before the actor window lets it go (aw_actors.c Release) */
struct edict_s;
void AW_SaveCaptureActor(struct edict_s *e);
/* the place is unloaded (aw_scene.c load_scene, before the next map): its actors' rows (AW_SaveCapture) and, through
 * aw_save_actor_leave (aw_actors.c AW_ActorsCapture; NULL: none), every NPC's and creature's change-list row as it
 * stands, so nothing changed since its last capture is lost with the map (the save contract, rule 6) */
int AW_SaveLeave(void);
extern void (*aw_save_actor_leave)(struct edict_s *e);
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
/* SAVE-EXPORT-FAILURE-ACCEPTED-65: 1 kept, 0 something could not be kept (the save is refused, the previous kept) */
extern int (*aw_save_script_export)(struct aw_ledger_s *ledger);
extern void (*aw_save_script_import)(const struct aw_ledger_s *ledger);
/* SAVE-EXPORT-FAILURE-ACCEPTED-65 (the save contract's rule 4, all or nothing): an export that cannot keep its part
 * names it here (a short phrase, "the quest stages") before it reports failure; the save is then refused with "Save
 * refused: PART could not be kept; previous saves retained." (aw_save.c encode_world: the last name given since that
 * save began, else the export's own). A row the world change list refused while the save was taken (its REFUSED count
 * rose) refuses the save too, whatever the export reported. */
void AW_SaveRefusePart(const char *part);
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
extern int (*aw_save_ident_refresh)(struct aw_ledger_s *ledger);   /* 0: memory refused it (the save is refused) */
extern long (*aw_save_migrate)(struct aw_ledger_s *ledger,void *dropped);
extern int (*aw_save_drop_actor_records)(void);
extern void (*aw_save_notice)(const char *line);   /* the on-screen line of a migrated load */
/* SAVE-INSIDE-SCRIPT-STEP-66 (the save contract, rule 6: the settled capture boundary): 1 while the game is inside a
 * script step (the frame's script tick, a dialogue answer's result script), where a gameplay transaction may be half
 * done; aw_mwhost.c binds it, NULL: never busy. A save asked for then is not taken: AW_SaveWrite queues the slot and
 * returns 2, and AW_SaveTick writes it at the first frame that is not busy and has no load pending (the one line then
 * says Saved as usual). The recorder's starting save and the debug snapshot refuse while busy. */
extern int (*aw_save_busy)(void);
int AW_SaveQueued(void);   /* the slot a queued save waits for, -1 none */
/* a new game's state begins (AW_SaveReset): the scripts start the original's run-once new-game scripts
 * (aw_mwhost.c AW_MwscriptNewGame, NPC-STORY-DISABLED-AT-START-42) */
extern void (*aw_save_new_game)(void);
#endif
