/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's movement speed by the original's rules (docs/PLAYER_MOVEMENT.md).
 *
 * aw_move_rules.c holds the rules as pure functions (host tested,
 * tests/aga_move_rules_test.c); aw_move.c gathers the inputs from the live
 * character sheet every frame and applies them in sv_user.c.
 *
 * The rules follow the original game as the OpenMW engine implements them
 * (reference: OpenMW 0.51 apps/openmw/mwclass/npc.cpp getMaxSpeed, getWalkSpeed,
 * getRunSpeed, getJump; mwclass/actor.hpp getSwimSpeedImpl; mwclass/actor.cpp
 * getCurrentSpeed, getEncumbrance; mwworld/class.cpp getNormalizedEncumbrance;
 * mwmechanics/character.cpp race weight, strafing, movement fatigue;
 * mwphysics/physicssystem.cpp jump fatigue). Independent code; the numbers come
 * from the game settings in the user's own master file at build time
 * (combat/settings.txt "move" lines, tools/prepare_combat.py).
 *
 * Superspeed (dbg superspeed on, AmiWind extension for debugging) bypasses all
 * of this: movement is then the fixed cl_forwardspeed / cl_movespeedkey path
 * exactly as before.
 */
#ifndef AW_MOVE_H
#define AW_MOVE_H

/* Game settings the movement rules read; names are the master file's GMST names. */
typedef struct {
    float fMinWalkSpeed,fMaxWalkSpeed,fEncumberedMoveEffect,fBaseRunMultiplier,fAthleticsRunBonus;
    float fSwimRunBase,fSwimRunAthleticsMult,fSneakSpeedMultiplier,fEncumbranceStrMult;
    float fMinFlySpeed,fMaxFlySpeed;
    float fJumpAcrobaticsBase,fJumpAcroMultiplier,fJumpEncumbranceBase,fJumpEncumbranceMultiplier;
    float fJumpRunMultiplier,fJumpMoveBase,fJumpMoveMult;
    float fFatigueRunBase,fFatigueRunMult,fFatigueSwimWalkBase,fFatigueSwimWalkMult;
    float fFatigueSwimRunBase,fFatigueSwimRunMult,fFatigueSneakBase,fFatigueSneakMult;
    float fFatigueJumpBase,fFatigueJumpMult,fFatigueBase,fFatigueMult;
} aw_move_settings_t;
#define AW_MOVE_SETTING_COUNT 30

/* Everything the speed depends on, gathered in one place so later effects plug
 * in without rewriting the rules. Stats are the MODIFIED values (base +
 * modifiers - damage, plus Fortify/Drain/Damage once magic effects exist), read
 * live every frame, never baked. A zero field means "no effect". */
typedef struct {
    /* stats (now: the character sheet, aw_character) */
    float speed,athletics,acrobatics,strength;
    /* load (now: the carried items' weights; feather/burden later: magic effects) */
    float carried,feather,burden;
    /* actor scale: reference scale x race weight (now: the race's weight from the master file) */
    float scale;
    /* state */
    int running;        /* now: Shift (+speed) held */
    int sneaking;       /* later: no sneak input yet */
    int swimming;       /* now: the water movement path */
    int knocked;        /* now: knocked down / knocked out (combat input lock) */
    int paralyzed;      /* later: Paralyze effect */
    int dead;           /* now: health <= 0 */
    int godmode;        /* now: dbg godmode (no fatigue cost, Burden ignored) */
    /* effects (later: magic effects; magnitudes, 0 = none) */
    float levitate,swift_swim,jump,slowfall,water_walking;
    int levitation_enabled;
    /* fatigue (now: the character sheet's fatigue; the jump uses its term) */
    float fatigue,fatigue_max;
} aw_move_inputs_t;

int AW_MoveSettingIndex(const char *name);
int AW_MoveSettingSet(aw_move_settings_t *s,const char *name,float value);
const char *AW_MoveSettingName(int index);
/* The original's values (Morrowind.esm), used only when the image carries no
 * move lines (an older image). */
void AW_MoveSettingsDefault(aw_move_settings_t *s);

/* All speeds below are in ORIGINAL units per second, before the actor scale. */
float AW_MoveCapacity(const aw_move_settings_t *s,const aw_move_inputs_t *in);
float AW_MoveEncumbrance(const aw_move_settings_t *s,const aw_move_inputs_t *in);   /* normalized; >1 = over */
float AW_MoveWalkSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in);
float AW_MoveRunSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in);
float AW_MoveSwimSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in);
float AW_MoveMaxSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in);
/* getCurrentSpeed x actor scale: factor = input 0..1, strafing (sideways) x 0.75. */
float AW_MoveCurrentSpeed(const aw_move_settings_t *s,const aw_move_inputs_t *in,float factor,int strafing);
/* Strafing in first person (character.cpp): |side| > |forward| * 2. */
int AW_MoveStrafing(float forward,float side);
float AW_MoveFatigueTerm(const aw_move_settings_t *s,const aw_move_inputs_t *in);
/* Initial jump velocity, original units/s (getJump); 0 when the actor cannot jump. */
float AW_MoveJumpVelocity(const aw_move_settings_t *s,const aw_move_inputs_t *in);
/* Fatigue lost per second of full movement input (running, swimming, sneaking;
 * plain walking costs nothing); 0 in godmode or above capacity. */
float AW_MoveFatigueRate(const aw_move_settings_t *s,const aw_move_inputs_t *in);
/* Fatigue lost per jump. */
float AW_MoveJumpFatigue(const aw_move_settings_t *s,const aw_move_inputs_t *in);
/* OpenMW DynamicStat::setCurrent: a loss never takes fatigue below 0 unless it already is. */
float AW_MoveFatigueAfter(float fatigue,float loss);

/* Original units -> AmiWind units (tools/prepare_quake.py SCALE, the converter's world scale). */
#define AW_MOVE_UNIT_SCALE 0.25f

/* aw_move.c: the engine side. AW_MoveInit registers aw_superspeed and the
 * superspeed command and sets sv_user.c's hooks: the ground/air move and the
 * water move get the original's speed (AmiWind units/s) unless superspeed is
 * on; after each move, the fatigue cost of running/swimming and of a jump. */
void AW_MoveInit(void);
int AW_MoveSuperspeed(void);
/* The player's inputs as the rules see them this frame (live character sheet). */
void AW_MovePlayerInputs(aw_move_inputs_t *in);
#endif
