/* SPDX-License-Identifier: GPL-2.0-or-later
 * Magic effects as Quake sprites and particles (docs/MAGIC_EFFECTS.md): the glow on the casting hands, the cast,
 * the bolt in flight, the hit and the area burst of a spell, from the game's own effect meshes and textures.
 * The builder (tools/prepare_magic.py) reads each chosen magic effect's cast, bolt, hit, area and hand meshes from
 * the user's game data and writes gfx/magic.awm (this table, text), one Quake sprite per effect texture
 * (progs/awmx_NN.spr, four fade frames) and the school sounds. The engine (aw_magic.c) shows them with Quake's own
 * machinery: the particle pool (r_part.c), sprites as temporary entities (cl_tent.c CL_NewTempEntity, r_sprite.c)
 * and, with aw_magic_fx 2, dynamic lights (cl_dlights).
 * Only what is SEEN: no magicka, skills, chances or effects on actors (the game logic work).
 * The rules here are pure functions (aw_magic_rules.c, host-tested); aw_magic.c is the engine glue. */
#ifndef AW_MAGIC_H
#define AW_MAGIC_H

#define AW_MAGIC_FILE "gfx/magic.awm"
#define AW_MAGIC_MAGIC "AWMG1"
#define AW_MAGIC_EFFECTS 16
#define AW_MAGIC_EMITTERS 3
#define AW_MAGIC_RAMP 8
#define AW_MAGIC_NAME 16
#define AW_MAGIC_PATH 40
#define AW_MAGIC_SPRITE_PIXELS 32 /* every effect sprite is 32x32 (aw_sprite_scale = world size / 32) */
#define AW_MAGIC_FADE_FRAMES 4

/* The phases of a spell's look, in the order they play (OpenMW: VFX_Hands, CVFX, BVFX, HVFX, AVFX), and the failed
 * cast: a sound only ("Spell Failure <School>"; a failed cast shows no effect). Sounds per phase: the effect's own
 * CSND / BSND / HSND / ASND, else its school's "<school> cast|bolt|hit|area"; the bolt's sound loops in flight and
 * follows the bolt (rules from OpenMW mwworld/store.cpp, mwmechanics/spellcasting.cpp, mwworld/projectilemanager.cpp). */
enum {AW_MAGIC_HAND,AW_MAGIC_CAST,AW_MAGIC_BOLT,AW_MAGIC_HIT,AW_MAGIC_AREA,AW_MAGIC_FAIL,AW_MAGIC_BUBBLE,AW_MAGIC_PHASES};
/* AW_MAGIC_BUBBLE: the translucent sphere in the effect's colour (its sprite only) that wraps the caster while casting
 * and the target while the spell lands on it (OpenMW mwrender/animation.cpp addEffect: the cast and hit models
 * attached to the actor), with small sprites swirling on its radius. */
/* Schools as the magic effect record numbers them. */
enum {AW_MAGIC_ALTERATION,AW_MAGIC_CONJURATION,AW_MAGIC_DESTRUCTION,AW_MAGIC_ILLUSION,AW_MAGIC_MYSTICISM,
      AW_MAGIC_RESTORATION,AW_MAGIC_SCHOOLS};

/* One particle emitter of an effect mesh, in map units and seconds. axis: the emission direction in the effect's
 * own space (x right, y forward, z up); spread: tan of the cone's half angle (>= 50 = all directions); jitter: the
 * start box half size; gravity: 1 when the mesh pulls its particles down. ramp: the emitter texture's colours,
 * brightest first (RGB from the build); index: the same in the running palette (aw_magic.c). */
typedef struct {
    int count;
    float size,life,life_rand,speed,speed_rand,axis[3],spread,gravity,start,stop,jitter[3];
    unsigned char ramp[AW_MAGIC_RAMP][3];
    unsigned char index[AW_MAGIC_RAMP];
} aw_magic_emitter_t;

typedef struct {
    float length,sprite_size,radius;   /* seconds; the sprite's world size; the area mesh's radius at scale 1 */
    char sprite[AW_MAGIC_PATH],sound[AW_MAGIC_PATH];   /* "" when the phase has none */
    int emitters,present;
    aw_magic_emitter_t em[AW_MAGIC_EMITTERS];
} aw_magic_phase_t;

/* The shell shapes of the magic effect set (each effect's bubble is built in both, tools/prepare_magic.py: the
 * shape's sprites beside progs/awmx_NN.spr): 0 the egg, the effect's own hit model outline (the shield's upright
 * "cosmic egg", taller than wide, from the feet to above the head; the default); 1 the dotted sphere, a round see-
 * through bubble of the effect's colour strongest at its rim (kept from v0.0.54's first shell at the maintainer's
 * word, for spells and effects that want it). */
enum {AW_MAGIC_SHAPE_EGG,AW_MAGIC_SHAPE_SPHERE,AW_MAGIC_SHAPES};
/* The magic effect record's flag for a hit visual that stays on the target for the spell's whole duration (rule from
 * OpenMW components/esm3/loadmgef.hpp ContinuousVfx, mwmechanics/spellcasting.cpp and character.cpp
 * updateContinuousVfx: the hit model loops while the effect is active). */
#define AW_MAGIC_CONTINUOUS_VFX 0x20
typedef struct {
    char name[AW_MAGIC_NAME];
    int mgef,school,flags;
    unsigned char rgb[3];
    aw_magic_phase_t phase[AW_MAGIC_PHASES];
} aw_magic_effect_t;

typedef struct {
    int effects;
    float bolt_speed;   /* map units a second (fTargetSpellMaxSpeed x 0.25; each effect's speed is 1 in the data) */
    aw_magic_effect_t fx[AW_MAGIC_EFFECTS];
} aw_magic_table_t;

/* ---- rules (aw_magic_rules.c) ---- */
/* A decimal number ("-12.5"); 1 when TEXT is one, its value in *OUT. No library float parsing (68040). */
int AW_MagicNumber(const char *text,float *out);
/* The header line "AWMG1 <bolt speed>": 1 and the table emptied, or 0. */
int AW_MagicHeader(aw_magic_table_t *t,const char *line);
/* One table line (fx / ph / em, # comments and blank lines skipped): 1 taken, 0 refused (the reason in WHY). */
int AW_MagicLine(aw_magic_table_t *t,const char *line,char *why,int why_size);
/* After the last line: 1 when every effect has its cast phase and every emitter is sane. */
int AW_MagicCheck(const aw_magic_table_t *t,char *why,int why_size);
int AW_MagicFind(const aw_magic_table_t *t,const char *name);
int AW_MagicPhase(const char *word);
int AW_MagicSchool(const char *word);
const char *AW_MagicPhaseName(int phase);
const char *AW_MagicSchoolName(int school);
/* Particles an emitter starts between phase times FROM (exclusive) and TO (inclusive): its count spread evenly over
 * [start, stop] (all at start when they are equal), times SCALE (the caps), never negative. */
int AW_MagicEmitBetween(const aw_magic_emitter_t *e,float from,float to,float scale);
/* A continuous emitter (the bolt's trail): particles a second. */
float AW_MagicTrailRate(const aw_magic_emitter_t *e);
/* An emission direction in the effect's space: the axis bent by the cone from R (a random point in the unit
 * ball), normalised; all directions when the cone is wide. 0 when R and the axis give no direction. */
int AW_MagicDirection(const aw_magic_emitter_t *e,const float r[3],float out[3]);
/* The fade frame (0 full .. 3 faintest) at AGE seconds of a LENGTH-second phase. */
int AW_MagicFadeFrame(float age,float length);
/* The area mesh's scale for an area of FEET (OpenMW: area x 2, at least 1). */
float AW_MagicAreaScale(float feet);
/* The hit or area sprite's world size at AGE: grows from SIZE to SIZE x GROW over the phase. */
float AW_MagicGrow(float size,float grow,float age,float length);

/* ---- engine glue (aw_magic.c) ---- */
/* The shared effect path (stable API for other effects: rain, smoke ...; independent of aw_magic_fx):
 * AW_FxParticles starts COUNT Quake particles (r_part.c's pool) at AT within a box of half size SPREAD, each moving
 * VEL plus up to VEL_RAND on every axis (map units a second), living LIFE seconds (+- a quarter), in the palette colour
 * nearest R G B, falling when GRAVITY is 1; returns how many started (the pool may be full).
 * AW_FxSprite draws the Quake sprite MODEL (Mod_ForName of a .spr) at AT for this frame only (a temporary entity,
 * cl_tent.c), WORLD_SIZE map units wide (aw_sprite_scale against its width), frame FRAME; 1 when drawn, 0 when the
 * frame's temporary entities are used up. Call it every frame the sprite should show (after CL_UpdateTEnts). */
struct model_s;
int AW_FxParticles(const float at[3],int count,float spread,const float vel[3],float vel_rand,float life,
                   int r,int g,int b,int gravity);
int AW_FxSprite(struct model_s *model,const float at[3],float world_size,int frame);
void AW_MagicInit(void);
void AW_MagicUpdate(void);   /* cl_main.c, after CL_UpdateTEnts: effects, sprites and lights of this frame */

#endif
