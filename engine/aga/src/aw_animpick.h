/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every humanoid animation group hooked up (ANIM-GROUPS-NOT-HOOKED-54, docs/ANIMKIT.md "Every group hooked up").
 *
 * The game logic (combat, the companion, the residents' idle, the walk) drives an actor through the animation kit's
 * engine groups (aw_anim.h: idle, walk, run, swim, hit, knock, death, attack, block, jump). For a skeletal actor (one
 * shared table per skeleton, aw_skel.h) this layer then picks the Morrowind group OpenMW's character controller would
 * play in the same state, by its rules (apps/openmw/mwmechanics/character.cpp, weapontype.cpp, aiwander.cpp; rules
 * read there and written here independently):
 *   moving:   walk/run/sneak/swimwalk/swimrun x forward/back/left/right by the motion against the facing, the
 *             weapon stance's own set (walkforward1h, runleft2c, sneakbackhh ...) with OpenMW's fallbacks
 *             (1s/1b/bow/1t -> 1h, 2b -> 2c, a missing swim group -> its land group, a missing run -> walk);
 *   turning:  turnleft/turnright (+ stance, swimturn*, spellturn* in the spell stance) while it turns on the spot;
 *   standing: idle, idle + stance (idlehh, idle1h, idle2c, idle2w, idlespell, idlecrossbow), idlesneak, idleswim,
 *             the wander idles idle2..idle9 by the package's chances, idlestorm in a storm;
 *   hit:      hit1..hitN at random (swimhit -> hit), knockdown, knockout (looped while out), the swim ones, shield;
 *   death:    death1..deathN at random, deathknockdown, deathknockout, swimdeath, swimdeathknockdown/-knockout;
 *   attack:   the weapon's own group (handtohand, weapononehand, weapontwohand, weapontwowide, bowandarrow,
 *             crossbow, throwweapon) between its "<chop|slash|thrust|shoot> start" and follow keys;
 *   cast:     spellcast between "<self|touch|target> start" and "... stop";
 *   equip:    the weapon's group "equip start" .. "equip stop" when it draws, "unequip ..." when it puts it away;
 *   jump:     jump + stance; pickprobe (a lockpick or probe used), inventory* (the inventory picture).
 * Pure functions (no engine state; aw_animpick_rules.inc, part of aw_animkit_rules.c), host-tested
 * (tests/aga_animpick_test.c). The engine side (the state of each skeletal actor, the frame) is in aw_animkit.c. */
#ifndef AW_ANIMPICK_H
#define AW_ANIMPICK_H

#define AW_PICK_NAME 24
#define AW_PICK_KEY 32

/* The weapon stance: OpenMW's weapon type numbers (ESM::Weapon::Type, the WPDT type of the user's own data):
 * 0 short blade, 1 long blade, 2 long blade two-handed, 3 blunt, 4 blunt two-close, 5 blunt two-wide, 6 spear,
 * 7 axe, 8 axe two-handed, 9 bow, 10 crossbow, 11 thrown; and these. */
enum {AW_PW_PICKPROBE=-4,AW_PW_HANDTOHAND=-3,AW_PW_SPELL=-2,AW_PW_NONE=-1,AW_PW_LAST=11};
/* What happens now: nothing (moving or standing), or a one-shot state. */
enum {AW_PE_NONE,AW_PE_HIT,AW_PE_KNOCKDOWN,AW_PE_KNOCKOUT,AW_PE_BLOCK,AW_PE_DEATH,AW_PE_ATTACK,AW_PE_CAST,
      AW_PE_EQUIP,AW_PE_UNEQUIP,AW_PE_JUMP,AW_PE_USE,AW_PE_INVENTORY,AW_PE_COUNT};
enum {AW_PM_NONE,AW_PM_FORWARD,AW_PM_BACK,AW_PM_LEFT,AW_PM_RIGHT,AW_PM_TURNLEFT,AW_PM_TURNRIGHT,AW_PM_COUNT};
enum {AW_PA_CHOP,AW_PA_SLASH,AW_PA_THRUST};
enum {AW_PR_SELF,AW_PR_TOUCH,AW_PR_TARGET};
enum {AW_PF_SMALL,AW_PF_MEDIUM,AW_PF_LARGE};

typedef struct {
    signed char weapon;        /* AW_PW_* or 0..AW_PW_LAST: the drawn weapon; AW_PW_NONE: nothing drawn */
    unsigned char event;       /* AW_PE_* */
    unsigned char move;        /* AW_PM_* (no event, or the stance's legs under a one-shot) */
    unsigned char run,sneak,swim,storm;
    unsigned char attack;      /* AW_PA_* (melee) */
    unsigned char follow;      /* AW_PF_*: the swing's follow-through by its strength */
    unsigned char range;       /* AW_PR_*: the spell's first effect's range */
    unsigned char idle;        /* 0, or 2..9: a wander idle (aiwander.cpp sIdleSelectToGroupName) */
    unsigned char knocked;     /* death after: 1 a knockdown, 2 a knockout */
    unsigned char roll;        /* 0..255: the random hit / death variant */
} aw_pick_state_t;

typedef struct {
    char group[AW_PICK_NAME];  /* the group to play (looked up in the actor's table, a view's own groups first) */
    char start[AW_PICK_KEY],stop[AW_PICK_KEY];   /* its text keys, "start" / "stop" for a whole group */
    unsigned char loop;        /* loops while the state holds (else held on its last frame) */
    char loop_start[AW_PICK_KEY],loop_stop[AW_PICK_KEY];  /* a held one-shot's inner loop (knockout), "" none */
    const char *rule;          /* the OpenMW rule it follows (the coverage report's "hooked by") */
} aw_pick_t;

/* HAS: 1 when the actor's table has the group NAME (OpenMW Animation::hasAnimation). */
typedef int (*aw_pick_has_t)(void *context,const char *name);
/* The group to play in state S, with OpenMW's fallbacks; 0 when the table has none of them (the caller keeps what
 * plays: OpenMW keeps the previous animation or the idle). */
int AW_AnimPick(const aw_pick_state_t *s,aw_pick_has_t has,void *context,aw_pick_t *out);
/* OpenMW CharacterController::getWeaponShortGroup / getWeaponAnimation (long group), "" for none. */
const char *AW_PickShortGroup(int weapon);
const char *AW_PickLongGroup(int weapon);
/* The wander idle by the package's eight chances (Idle2..Idle9) (aiwander.cpp getRandomIdle): ROLL_GATE 0..100
 * against fIdleChanceMultiplier x 100 (MULTIPLIER100), then one roll 0..100 per idle; the highest roll at or under
 * its own chance picks it. 0 = none (the plain idle). */
int AW_PickWanderIdle(const unsigned char chances[8],int multiplier100,int roll_gate,const unsigned char rolls[8]);

/* The coverage catalogue: every group of the humanoid animation files (base_anim, base_animkna, base_anim_female
 * and an NPC's own file), how the game logic reaches it. tools/anim_coverage.py reads this table from the source. */
typedef struct {const char *group;const char *hook;} aw_pick_catalogue_t;
extern const aw_pick_catalogue_t aw_pick_catalogue[];
extern const int aw_pick_catalogue_count;

/* Engine part (aw_animkit.c; dbg animkit pick). */
struct edict_s;
void AW_AnimPickInit(void);
/* sv_main.c SV_SendClientMessages: the picked frames in before the send, the drivers' frames back after it. */
void AW_AnimPickPreSend(void);
void AW_AnimPickPostSend(void);
/* An actor starts a cast (RANGE AW_PR_*: the spell's first effect): spellcast between its range's keys, over the rest
 * (the spell effects work's entry point). */
void AW_AnimPickCast(struct edict_s *e,int range);
/* Sneaking on or off (MWScript ForceSneak / ClearForceSneak): the sneak gaits and idlesneak. */
void AW_AnimPickSneak(struct edict_s *e,int on);
/* The actor's wander package idle chances Idle2..Idle9 (AI_W, AIWander): the wander idles while it stands. */
void AW_AnimPickIdleChances(struct edict_s *e,const unsigned char chances[8]);
/* The group the actor shows now (1), for dbg and tests. */
int AW_AnimPickGroup(struct edict_s *e,char *out,int size);
/* aw_mwhost.c: the type of the weapon an actor's record holds (OpenMW's weapon type 0..11), -1 none or no record. */
int AW_MwscriptWeaponType(struct edict_s *e);
#endif
