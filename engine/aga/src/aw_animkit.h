/* SPDX-License-Identifier: GPL-2.0-or-later
 * The animation kit's debug console (dbg animkit, docs/ANIMKIT.md) and its
 * table of Morrowind's own animation groups.
 *
 * Pure parts (aw_animkit_rules.c, host-tested): the group table and the
 * command parser. Engine part (aw_animkit.c): the aw_animkit cvar, the
 * aw_animkit command and the per-frame forced group on one target.
 */
#ifndef AW_ANIMKIT_H
#define AW_ANIMKIT_H

/* Build-time switch: -DAW_ANIMKIT=0 compiles the kit out (movers play idle, dbg animkit only says so);
 * the default 1 keeps it, with the run-time cvar aw_animkit on top. */
#ifndef AW_ANIMKIT
#define AW_ANIMKIT 1
#endif

/* One Morrowind animation group (the skeleton's text keys) and the engine
 * group it plays as (aw_anim.h AW_ANIM_*), or -1: present in the data, not
 * wired yet. */
typedef struct {const char *name;int engine;} aw_animkit_group_t;
extern const aw_animkit_group_t aw_animkit_groups[];
extern const int aw_animkit_group_count;
/* The table row of NAME (case-insensitive), or -1. */
int AW_AnimKitFind(const char *name);
/* The engine group a name plays: an engine group name (idle, walk, run ...)
 * or a Morrowind group that is wired; -1 otherwise. */
int AW_AnimKitEngineGroup(const char *name);

enum {AW_ANIMKIT_HELP, AW_ANIMKIT_STATUS, AW_ANIMKIT_ON, AW_ANIMKIT_OFF, AW_ANIMKIT_LIST,
      AW_ANIMKIT_PLAY, AW_ANIMKIT_STOP, AW_ANIMKIT_SPEED,
      /* the animation stage (SKEL-ANIM-STAGE-52): the table's groups of the target, every group one after
       * another, a cast of skeletal actors lined up in front of the player */
      AW_ANIMKIT_GROUPS, AW_ANIMKIT_CYCLE, AW_ANIMKIT_STAGE};
/* group: an engine group (aw_anim.h), or -1 for a group played straight from a skeletal actor's shared table by
 * name (name); count: stage cast size, or 1 for "cycle all" (every staged or nearby skeletal actor). */
typedef struct {int kind;int group;float speed;int count;char name[32];} aw_animkit_cmd_t;
#define AW_ANIMKIT_STAGE_MAX 8
/* Parse "dbg animkit ..." arguments (argv[0] = the command). Returns 1 and
 * fills out, or 0 with out->kind = AW_ANIMKIT_HELP and a reason in out->name
 * (unknown subcommand, a group name too long, a speed outside 0.1..4, a stage
 * size outside 1..8). play takes any name: a wired one plays the engine group,
 * another is looked up in the target's animation table (skeletal actors). */
int AW_AnimKitParse(int argc,const char **argv,aw_animkit_cmd_t *out);

/* One group of a shared animation table played from its first to its last frame (inclusive) at rate frames a
 * second: *t (seconds into the group) advanced by dt; a loop wraps, a one-shot holds the last frame and sets *done
 * (may be NULL). Returns the table frame. Pure (host-tested). */
int AW_AnimKitSpanFrame(unsigned first,unsigned last,float rate,float *t,float dt,int loop,int *done);

/* aw_anim.c (pure): 0 = movers play their idle frames (the previous method);
 * the playback rate multiplier of dbg animkit speed. */
extern int aw_anim_kit_enabled;
extern float aw_anim_kit_speed;

/* The combat playground's animation mode (aw_arena.c, docs/COMBAT.md "Combat playground"): E plays every combat
 * group of its shared table in turn, over and over (a baked actor: its layout's groups); 1 table, 2 baked layout,
 * 0 nothing to play. Label: the lead's group and attack phase ("weapononehand: slash"), 0 when no cycle runs.
 * Skeletal: a model with a shared table. Stop: every forced actor given back. */
struct edict_s;
int AW_AnimKitCombatCycle(struct edict_s *e);
int AW_AnimKitLabel(char *out,int size);
int AW_AnimKitSkeletal(int modelindex);
void AW_AnimKitStop(void);
void AW_AnimKitInit(void);
void AW_AnimKitTick(void);
/* aw_magic.c: the actor plays its table's spellcast group for "self" / "touch" / "target" once, from the variant's
 * start key to its stop key; the seconds from start to the "<variant> release" key (when the spell leaves), or -1
 * (no table, no group or keys, or the kit off or compiled out). */
struct edict_s;
float AW_AnimKitCast(struct edict_s *e,const char *variant);
#endif
