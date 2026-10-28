/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_HAND_MODELS_H
#define AW_HAND_MODELS_H
#define AW_BLOCK_FRAMES 8
#define AW_BLOCK_APPEARANCES 32
typedef struct {char race[64],model[64];int female;} aw_block_appearance_t;
typedef struct {
    int count,hold;
    float duration,hit,time[AW_BLOCK_FRAMES],tag[AW_BLOCK_FRAMES][6];
    aw_block_appearance_t appearance[AW_BLOCK_APPEARANCES];
} aw_block_view_t;
typedef struct {int mode;float phase;} aw_block_clock_t;
int AW_BlockViewDecode(aw_block_view_t *,const unsigned char *,int);
int AW_BlockPlayback(const aw_block_view_t *,aw_block_clock_t *,int,float,float);
/* base angles and returned angles use the alias renderer's negated pitch.
 * Local tag angles use ordinary AngleVectors pitch/yaw/roll. */
void AW_BlockCompose(const float base_origin[3],const float base_angles[3],
                     const float tag[6],float origin[3],float angles[3]);
/* Inventory installs this only for an actual owned, equipped shield alias. */
extern int (*aw_hand_block_item)(char id[64],char model[64]);
int AW_HandBlockApply(void);
int AW_HandBlockItemApply(void);
/* The first-person hand clips (FIRST-PERSON-HANDS-IN-C-54): the builder writes them to gfx/hand-anims.txt in the image
 * (tools/hand_metadata.py hand_table; read by aw_hands.c), never into a map's worldspawn or the QuakeC, so a change to the hands rebuilds
 * the image only. Text: "AWHA1", then "clip NAME FIRST COUNT DURATION" for idle, draw, lower and punch (frames of the
 * hand model, seconds). The hand state machine (draw, idle, punch, lower; the torch) runs in C (AW_HandsTick) on the
 * player's QuakeC fields aw_hand_state, aw_hand_goal, aw_hand_started, aw_torch, aw_attack_latched. */
enum {AW_HAND_IDLE,AW_HAND_DRAW,AW_HAND_LOWER,AW_HAND_PUNCH,AW_HAND_CLIPS};
#define AW_HAND_TABLE_PATH "gfx/hand-anims.txt"
typedef struct {int first[AW_HAND_CLIPS],count[AW_HAND_CLIPS];float duration[AW_HAND_CLIPS];} aw_hand_table_t;
/* 1 and OUT filled when TEXT is a complete table (every clip once, 1..64 frames, 0 < duration <= 60 s). Pure. */
int AW_HandTableParse(const char *text,aw_hand_table_t *out);
/* The frame of a clip ELAPSED seconds in (the QuakeC contract: first + floor(elapsed x count / duration)). Pure. */
int AW_HandClipFrame(const aw_hand_table_t *t,int clip,float elapsed);
int AW_HandTableReady(void);
/* The table is read again at the next use (tests; aw_hands.c). */
void AW_HandTableReset(void);
/* A clip's duration from the image's table, FALLBACK when the image has none. */
float AW_HandDuration(int clip,float fallback);
/* Once a frame after the server frame: the hands' state machine (impulse 202, the attack button, the clips). */
void AW_HandsTick(void);
int AW_HandModelsDecode(const unsigned char *data,int size);
void AW_HandModelsLoad(void);
void AW_HandModelsReset(void);
/* Returns one only after selecting a complete, validated appearance. */
int AW_HandModelsApply(void);
#endif
