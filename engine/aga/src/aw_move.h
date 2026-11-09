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
    /* fall damage (v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61; OpenMW 0.51 mwmechanics/character.cpp getFallDamage) */
    float fFallDamageDistanceMin,fFallDistanceBase,fFallDistanceMult,fFallAcroBase,fFallAcroMult;
    /* the werewolf's run (v0.0.63, WEREWOLF-RUN-SPEED-63; OpenMW 0.51 mwclass/npc.cpp getMaxSpeed) */
    float fWerewolfRunMult;
} aw_move_settings_t;
#define AW_MOVE_SETTING_COUNT 36

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
    int sneaking;       /* now: the sneak key held on foot (AW_MoveSneaking, SNEAK-58) */
    int swimming;       /* now: the water movement path */
    int knocked;        /* now: knocked down / knocked out (combat input lock) */
    int paralyzed;      /* later: Paralyze effect */
    int dead;           /* now: health <= 0 */
    int godmode;        /* now: dbg godmode (no fatigue cost, Burden ignored) */
    int werewolf;       /* now: a script's BecomeWerewolf holds (aw_move_werewolf, v0.0.63) */
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

/* Falls (v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61), for the player and every actor. Rules from OpenMW 0.51, written
 * independently:
 * - mwphysics/physicssystem.cpp: Slowfall's factor is 1 - magnitude x 0.005, clamped to 0..1;
 * - mwphysics/movementsolver.cpp: each physics step (OpenMW's 1/60 s) the vertical speed loses gravity x step and,
 *   while falling, is multiplied by that factor;
 * - mwphysics/mtphysics.cpp: the fall height grows by every drop while in the air, and starts again at 0 on the
 *   ground, under water, while flying or while any Slowfall is on (so a Slowfall landing never hurts);
 * - mwmechanics/character.cpp getFallDamage and the landing: below fFallDamageDistanceMin nothing; above it the
 *   height less the minimum less 1.5 x Acrobatics and the Jump magnitude (never below 0), times fFallDistanceMult plus
 *   fFallDistanceBase, times fFallAcroBase + fFallAcroMult x (100 - Acrobatics); the health lost is that times
 *   (1 - 0.25 x the fatigue term), and the actor is knocked down when the damage is more than Acrobatics x the
 *   fatigue term. No damage landing in water, none in god mode. */
#define AW_MOVE_GRAVITY 627.1152f        /* 8.96 m/s^2 x 69.99125 units a metre (components/misc/constants.hpp) */
#define AW_MOVE_PHYSICS_STEP (1.0f/60.0f)
float AW_MoveSlowFallFactor(float magnitude);
/* one physics step of STEP seconds: the new vertical speed (original units/s, up positive) */
float AW_MoveFallStep(float vz,float step,float gravity,float slowfall);
float AW_MoveFallDamage(const aw_move_settings_t *s,float height,float acrobatics,float jump);
float AW_MoveFallHealthLoss(float damage,float fatigue_term);
int AW_MoveFallKnockdown(float damage,float acrobatics,float fatigue_term);
/* aw_move.c: the same with the image's settings (the player's and the actors' falls); *KNOCKDOWN may be NULL */
float AW_MoveFallLoss(float height,float acrobatics,float jump,float fatigue,float fatigue_max,int *knockdown);
/* aw_fall.c: the actors held on an object a script removes, and their falls (the HELD rows of the compiled scripts) */
void AW_FallInit(void);
void AW_FallTick(float dt);
extern int (*aw_fall_far_event)(int edict);   /* a live far event's actor: drawn past the draw distance (r_main.c) */
void AW_FallStatus(void);

/* Original units -> AmiWind units (tools/prepare_quake.py SCALE, the converter's world scale). */
#define AW_MOVE_UNIT_SCALE 0.25f

/* A script's angles and moves of an object (MWSCRIPT-SMALL-FUNCTIONS-62; OpenMW 0.51 transformationextensions.cpp
 * OpGetAngle, OpSetAngle, OpMove, worldimp.cpp rotateObject; written independently). The converter places an object
 * turned by the original's z rotation R (radians) at Quake yaw -R in degrees (tools/import_town.py, prepare_area.py),
 * so the original's z angle is minus the yaw; x is Quake's pitch and y its roll, as Rotate turns them. OpenMW keeps an
 * actor's z (and y) angle within -180..180 once it turns (rotateObject normalizeAngle) and its x within -90..90; an
 * object keeps the angle it was given. AXIS 'x', 'y' or 'z' ('u', 'v', 'w' the same axes); anything else reads 0 and
 * sets nothing (-1). Pure. */
float AW_MoveScriptAngle(const float quake[3],int axis,int actor);
/* the Quake angle index (0 pitch, 1 yaw, 2 roll) SetAngle writes, and the Quake degrees in *OUT; -1 an unknown axis */
int AW_MoveScriptAngleSet(int axis,float degrees,int actor,float *out);
/* Move AXIS by AMOUNT (AmiWind units): along the object's own axes (OpenMW: its attitude x the axis), the original's
 * x being Quake's forward, y its left and z its up, from AngleVectors' FORWARD, RIGHT and UP; 0 for an unknown axis */
int AW_MoveScriptLocal(const float forward[3],const float right[3],const float up[3],int axis,float amount,float out[3]);

/* aw_move.c: the engine side. AW_MoveInit registers aw_superspeed and the
 * superspeed command and sets sv_user.c's hooks: the ground/air move and the
 * water move get the original's speed (AmiWind units/s) unless superspeed is
 * on; after each move, the fatigue cost of running/swimming and of a jump. */
void AW_MoveInit(void);
int AW_MoveSuperspeed(void);
/* DBG-SUPERSPEED-62: while superspeed is on, the movement rules read Speed, Athletics and Acrobatics as this (the
 * game's maximum for a skill and an unfortified attribute) and the player's fatigue is filled every move
 * (aw_combat.c AW_CombatPlayerFatigueFill): endless stamina. The character sheet is never written. */
#define AW_MOVE_SUPERSPEED_STAT 100.0f
/* SNEAK-58: 1 while the player sneaks (the sneak key held, on foot, not swimming, not in noclip). */
int AW_MoveSneaking(void);
/* MWSCRIPT-GAP-FUNCTIONS-62: 1 while a script's ForceSneak holds the player in the sneak stance (aw_mwhost.c). */
extern int aw_move_force_sneak;
/* MWSCRIPT-GAPS-63: 1 while a script's ForceRun makes the player run (aw_mwhost.c). */
extern int aw_move_force_run;
/* WEREWOLF-RUN-SPEED-63: 1 while the player is in werewolf form (aw_mwhost.c sets it with the form). */
extern int aw_move_werewolf;
/* The player's inputs as the rules see them this frame (live character sheet). */
void AW_MovePlayerInputs(aw_move_inputs_t *in);
/* ENCUMBRANCE-INCOMPLETE-61 (INVENTORY-ORIGINAL-LIMITS-61): the magnitudes of the Burden and Feather effects on the
 * player now (0 = none), set by the spell effects whenever they change (v061-magic, SPELL-EFFECTS-57); kept until set
 * again, not saved (the effects themselves are). AW_PlayerEncumbrance: OpenMW Actor::getEncumbrance (carried + Burden,
 * Burden not in godmode, - Feather, never below 0), with the capacity (Strength x fEncumbranceStrMult) in *CAPACITY. */
#define AW_ENCUMBRANCE_EFFECTS 1
void AW_EncumbranceSetEffects(float burden,float feather);
float AW_PlayerEncumbrance(float *capacity);
/* DBG-NOBURDEN-62: dbg noburden / unburdened / noweight, a debug mode (not saved, off at New Game): while on, the
 * encumbrance is 0 in every rule (AW_MoveNoBurden: the load, Burden and Feather taken as 0, so no slower walk, run,
 * swim or jump, no load in the fatigue costs or the rest, never over-encumbered), and the inventory's burden bar shows
 * the real load over AW_MOVE_NOBURDEN_SHOWN. That number: the bar's text field holds 28 characters of the 4-pixel font
 * (114 pixels) for "load/capacity", and OpenMW 0.51 shows the capacity as a whole number (inventorywindow.cpp
 * updateEncumbranceBar); six nines leave the load as many digits as the capacity. The original's real capacity is
 * Strength x fEncumbranceStrMult (5), 500 at Strength 100. */
#define AW_MOVE_NOBURDEN_SHOWN 999999.0f
void AW_MoveNoBurden(aw_move_inputs_t *in);
int AW_MoveNoBurdenOn(void);
void AW_MoveNoBurdenSet(int on);
#endif
