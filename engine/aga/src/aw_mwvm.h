/* SPDX-License-Identifier: GPL-2.0-or-later
 * The interpreter of the compiled game scripts (docs/MWSCRIPT_BYTECODE.md, tools/mwscript/).
 *
 * Pure C: no engine headers; one allocation, its tables, at the first load, none while running. Everything it
 * needs from the game goes through the host table
 * (aw_mwhost.c in the engine, stubs in the native tests). Fixed tables: instances (the placed objects and the
 * global scripts that run), their local values, a parking store that keeps an object's values while its map is
 * not loaded. */
#ifndef AW_MWVM_H
#define AW_MWVM_H
#include <stdint.h>

#define AW_MWVM_INSTANCES 256      /* placed objects attached to the loaded map, plus running global scripts */
#define AW_MWVM_CELLS 4096         /* local values of the attached objects and the global scripts */
#define AW_MWVM_PARKED 512         /* objects whose values are kept while their map is not loaded */
#define AW_MWVM_PARK_CELLS 4096
#define AW_MWVM_STACK 32
#define AW_MWVM_STRINGS 8192       /* NOTYET names logged once each */
#define AW_MWVM_SELF (-2)
#define AW_MWVM_PLAYER (-1)

typedef union {int32_t i;float f;} aw_mwcell_t;

/* How a sound is started (host sound()). */
enum {AW_MWSND_2D, AW_MWSND_3D, AW_MWSND_LOOP, AW_MWSND_STOP};

typedef struct {
    /* TARGET: AW_MWVM_SELF (the instance's own object), AW_MWVM_PLAYER, or an object table index. */
    void (*sound)(int instance,int target,int sound,int how,float volume,float pitch);
    int (*sound_playing)(int instance,int target,int sound);
    void (*say)(int instance,int target,int voice,int text);
    int (*say_done)(int instance,int target);
    void (*music)(int music);
    float (*distance)(int instance,int target);            /* game units (the engine's units times 4) */
    int (*menu_mode)(void);
    int32_t (*query)(int instance,int query,int operand);
    int32_t (*journal_get)(int topic);
    void (*journal_set)(int topic,int32_t index,int advance);
    void (*notyet)(int name_string,int script_name_string); /* called once per function name */
    void (*warn)(const char *what,int script_name_string);   /* once per script and kind */
} aw_mwvm_host_t;

typedef struct {
    uint16_t script,flags;          /* flags: AWI_* */
    uint32_t reference;             /* 0 for a global script */
    int entity;                     /* the object's edict number, -1 none */
    float origin[3];                /* engine units, for the activation range */
    int locals;                     /* first cell in the pool */
    uint32_t generation;            /* the state generation of its last run */
    float last_run;                 /* the interpreter clock of its last run (GetSecondsPassed) */
    float say_until;                /* (host use) */
} aw_mwvm_instance_t;

#define AWI_USED 1
#define AWI_GLOBAL 2       /* a global script (StartScript or a start script) */
#define AWI_RUNNING 4      /* a global script that runs (StopScript clears it, its values stay) */
#define AWI_QUIET 8        /* its last run changed nothing and called nothing */
#define AWI_CELLCHANGED 16 /* CellChanged is true on its next run */
#define AWI_INTERIOR 32    /* in a room: active while the room is loaded */
#define AWI_ACTIVE 64      /* within the activation range this frame */

typedef struct {
    unsigned long frames,runs,skipped_quiet,skipped_far,deferred,ops,max_ops_frame,aborted,notyet_calls;
} aw_mwvm_stats_t;

/* Load the resident part of an AWMS1 file (DATA, BYTES: at least its resident bytes; the whole file works too).
 * Returns 1, or 0 with nothing loaded (bad magic, version, sizes). The buffer must outlive the interpreter. */
int AW_MwvmLoad(const unsigned char *data,unsigned long bytes,const aw_mwvm_host_t *host);
void AW_MwvmReset(void);
int AW_MwvmLoaded(void);
/* Table access for the host. */
int AW_MwvmScriptCount(void);
int AW_MwvmScriptFlags(int script);
int AW_MwvmScriptName(int script);                       /* string index */
/* 1 mapped; NEAR/FAR: hearing distances in game units */
int AW_MwvmSound(int sound,unsigned char hash[8],int *centis,int *volume,int *near_units,int *far_units);
int AW_MwvmVoice(int voice,unsigned char hash[8],int *centis);                               /* 1 mapped */
int AW_MwvmMusic(int music);                             /* track number, -1 none */
uint32_t AW_MwvmObjectReference(int object);             /* 0: not placed once */
int AW_MwvmTopicName(int topic);                         /* string index */
int AW_MwvmTopicCount(void);
void AW_MwvmConfig(uint32_t *range_units,int *ops_frame,int *ops_run);
/* Section offsets in the file (BIND and STRS stay on disk): offset, rows; 0 if absent. */
int AW_MwvmSection(const char tag[4],uint32_t *offset,uint32_t *rows,uint32_t *bytes);

/* Map changes: every attached object is parked (its values kept), then the host attaches the new map's objects. */
void AW_MwvmBeginMap(void);
int AW_MwvmAttach(uint32_t reference,int script,int bind_flags,int entity,const float origin[3]);
void AW_MwvmSetOrigin(int instance,const float origin[3]);
aw_mwvm_instance_t *AW_MwvmInstance(int instance);
int AW_MwvmInstanceCount(void);
/* Start scripts and StartScript. */
void AW_MwvmStartScript(int script);
/* One frame: DT seconds of game time, PLAYER the player's position (engine units). */
void AW_MwvmTick(float dt,const float player[3]);
const aw_mwvm_stats_t *AW_MwvmStats(void);
/* Values for tests and the debug command. */
int32_t AW_MwvmGlobalInt(int global);
float AW_MwvmGlobalFloat(int global);
int AW_MwvmGlobalCount(void);
aw_mwcell_t AW_MwvmLocal(int instance,int slot);
#endif
