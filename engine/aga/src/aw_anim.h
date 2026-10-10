/* SPDX-License-Identifier: GPL-2.0-or-later
 * Character animation kit, engine side (docs/ANIMATION.md).
 *
 * An actor model's frame groups come from the layout written beside it
 * (<model>.anm, tools/npc_anim.py):
 *   NAME:BASE:COUNT:STEP[:X]   X = own speed in units/s (walk, run, swim) or
 *                              the hit fraction (attack)
 *   @NAME:OFFSET:EVENT         footstep event (left, right) on a group frame
 *   ~EVENT:DRY:WADE:SWIM       its sound files (relative to sound/)
 *   >PATH                      the mover model (all groups), loaded only while the actor moves
 *   !TOPIC:HEX16[:KOPV]..      a voice line (attack, hit, flee, idle): sound/pool/aHEX16.wav, said when its
 *                              conditions hold (K h/p/r = speaker health %, player health %, Random100)
 * Quake mechanism: vertex frames played by changing the edict's frame, sounds
 * through SV_StartSound with names precached at spawn. A model without a
 * layout keeps the previous behaviour (idle 0..7; town actors walk 13..20).
 */
#ifndef AW_ANIM_H
#define AW_ANIM_H

enum {AW_ANIM_IDLE, AW_ANIM_WALK, AW_ANIM_RUN, AW_ANIM_SWIM, AW_ANIM_SWIMIDLE,
      AW_ANIM_HIT, AW_ANIM_KNOCK, AW_ANIM_DEATH, AW_ANIM_ATTACK,
      /* combat (aw_combat.c): the original shield block; the dodge sidesteps are an
       * AmiWind extension (no original dodge group exists) */
      AW_ANIM_BLOCK, AW_ANIM_DODGEL, AW_ANIM_DODGER, AW_ANIM_GROUPS};
enum {AW_ANIM_LEFT, AW_ANIM_RIGHT, AW_ANIM_EVENT_KINDS};
enum {AW_ANIM_DRY, AW_ANIM_WADE, AW_ANIM_SWIMMING, AW_ANIM_MEDIA};
#define AW_ANIM_EVENTS 24
#define AW_ANIM_SOUND_NAME 40
#define AW_ANIM_MOVER_NAME 64     /* MAX_QPATH */
/* Voice barks (the original's voice topics; docs/ANIMATION.md "Voices") */
enum {AW_VOICE_ATTACK_LINE, AW_VOICE_HIT_LINE, AW_VOICE_FLEE_LINE, AW_VOICE_IDLE_LINE, AW_VOICE_TOPICS};
#define AW_VOICE_LINES 12         /* per topic and model (tools: mwad.npc.voice_lines limit) */
typedef struct {
    unsigned char hash[8];        /* sound/pool/a<16 hex>.wav */
    char kind[2], op[2];          /* conditions: kind h|p|r (0 = none), op = ! > g < l */
    short value[2];
} aw_voice_line_t;

typedef struct {
    short base;
    unsigned char count, present;
    float step;     /* seconds per frame at rate 1 */
    float x;        /* own speed (units/s) or hit fraction; 0 = none */
} aw_anim_group_t;

typedef struct {
    aw_anim_group_t g[AW_ANIM_GROUPS];
    unsigned char ev_group[AW_ANIM_EVENTS], ev_offset[AW_ANIM_EVENTS], ev_kind[AW_ANIM_EVENTS];
    unsigned char events, from_layout;
    char sound[AW_ANIM_EVENT_KINDS][AW_ANIM_MEDIA][AW_ANIM_SOUND_NAME];
    char mover[AW_ANIM_MOVER_NAME];   /* >PATH: the full-kit model this actor wears while it moves */
    aw_voice_line_t voice[AW_VOICE_TOPICS][AW_VOICE_LINES];   /* !TOPIC:HEX16[:KOPV[:KOPV]] */
    unsigned char voices[AW_VOICE_TOPICS];
} aw_anim_t;

/* The play state of one actor (per edict, owned by the caller). */
typedef struct {
    float phase;            /* frames into the group, fractional */
    unsigned char group, index;
} aw_anim_play_t;

extern const char *const aw_anim_group_names[AW_ANIM_GROUPS];

/* Pure parts (host-tested): */
void AW_AnimDefault(aw_anim_t *a,int numframes);
int AW_AnimParse(aw_anim_t *a,const char *layout,int numframes);
/* Movement group for a horizontal speed: walk or run by the nearer own speed,
 * swim in water; *rate = speed / own speed (clamped 0.25..4); idle below 1 u/s. */
int AW_AnimMoveGroup(const aw_anim_t *a,float speed,int swimming,float *rate);
/* Advance by dt seconds at rate; returns the frame. *crossed gets a bit per
 * group frame index entered (loop groups wrap; one-shot groups hold the last). */
int AW_AnimAdvance(const aw_anim_t *a,aw_anim_play_t *p,int group,float dt,float rate,unsigned long *crossed);
int AW_AnimDone(const aw_anim_t *a,const aw_anim_play_t *p);
/* The voice line to say for a topic, or -1: the first line whose conditions hold (OpenMW Filter::search),
 * or with pick_random a random one of them (an AmiWind option). random100: a roll 0..100. */
int AW_VoicePick(const aw_anim_t *a,int topic,int speaker_health,int player_health,int random100,int pick_random,int roll);
/* Events of group whose frame offset bit is set in crossed: calls emit(kind). */
void AW_AnimEvents(const aw_anim_t *a,int group,unsigned long crossed,void (*emit)(void *,int),void *context);

/* Engine part (aw_anim.c without AW_ANIM_HOST_TEST): */
struct edict_s;
/* Spawn time (aw_animprep, #81): load <model>.anm once per model, precache its sounds. */
void AW_AnimPrep(struct edict_s *e);
/* The layout of an edict's model (default layout when it has none). */
const aw_anim_t *AW_AnimOf(struct edict_s *e);
/* Play footstep events crossed: medium = dry, wading or swimming. */
void AW_AnimSounds(struct edict_s *e,const aw_anim_t *a,int group,unsigned long crossed,int medium);
int AW_AnimMedium(struct edict_s *e);
void AW_AnimInit(void);
/* The mover model (aw_anim_t.mover): on = load it and wear it (companion follows,
 * combat engages); off = back to the standing model, the mover's cache freed when
 * no other edict wears it. Returns 1 when the edict changed model. */
int AW_AnimMover(struct edict_s *e,int on);
int AW_AnimMoving(struct edict_s *e);
/* Saves write the standing model: begin swaps it in for every moving edict, end back. */
void AW_AnimSaveSwap(int begin);
/* A mover model the client must not load at sign-on (cl_parse.c). */
int AW_AnimLazy(const char *name);
/* model.c: the entry only, nothing loaded (declared here: model.h is pinned by tools/edge_cache_heap.py) */
struct model_s *Mod_FindName (char *name);
/* Say a voice topic (AW_VOICE_*_LINE) with the original odds (per 10,000; 10000 = always); 1 when said. Not
 * while the actor speaks already (OpenMW DialogueManager::say). The idle topic also needs the player in
 * sight within 3000 original units (750). */
int AW_VoiceSay(struct edict_s *e,int topic,int odds);
#endif
