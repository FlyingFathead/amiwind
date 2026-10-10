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
      AW_ANIMKIT_PLAY, AW_ANIMKIT_STOP, AW_ANIMKIT_SPEED};
typedef struct {int kind;int group;float speed;char name[32];} aw_animkit_cmd_t;
/* Parse "dbg animkit ..." arguments (argv[0] = the command). Returns 1 and
 * fills out, or 0 with out->kind = AW_ANIMKIT_HELP and a reason in out->name
 * (unknown subcommand, a group that is not wired, a speed outside 0.1..4). */
int AW_AnimKitParse(int argc,const char **argv,aw_animkit_cmd_t *out);

/* aw_anim.c (pure): 0 = movers play their idle frames (the previous method);
 * the playback rate multiplier of dbg animkit speed. */
extern int aw_anim_kit_enabled;
extern float aw_anim_kit_speed;

void AW_AnimKitInit(void);
void AW_AnimKitTick(void);
#endif
