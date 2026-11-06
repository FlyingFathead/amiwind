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
/* First-person weapons (PLAYER-GEAR-VISUAL-59, FIRST-PERSON-WEAPONS-56): the player's equipped melee weapon in the
 * hand. The builder (tools/prepare_hand_catalog.py) bakes, per appearance, one arms model per stance of
 * base_anim.1st.nif with the same 28-frame contract as the bare hands (idle 8, draw 6, lower 4, swing 10):
 * <hands model stem>_1h.mdl (one-handed), _2c.mdl (two-handed close), _2w.mdl (two-handed wide); and once,
 * gfx/hand-weapons.aww: "AWW1", 0, the stance count, 0, the frame count (28), then per stance and frame the Weapon
 * Bone tag in the view model's space (origin, angles: 6 big-endian 16.16 values, the AWB1 tag form). The weapon
 * itself is the item's own model (one per mesh, the item model table), drawn as one more alias entity on that tag,
 * only while armed: the bare-hand frame costs nothing more. */
/* v0.0.61 (FIRST-PERSON-WEAPONS-56): three more stances, bow, crossbow and thrown, in the table and the tags (an
 * older image's table has three: those weapons keep the bare hands there); they have no baked arms. */
#define AW_HAND_STANCES 6
#define AW_HAND_WEAPON_FRAMES 28
typedef struct {int stances;float tag[AW_HAND_STANCES][AW_HAND_WEAPON_FRAMES][6];} aw_hand_weapons_t;
/* The stance of an inventory item's weapon value (1 + the record's weapon type; 0 none): 0 one-handed, 1 two-handed
 * close, 2 two-handed wide, 3 bow, 4 crossbow, 5 thrown, -1 none (hand to hand, ammunition). Pure. */
int AW_HandStance(int weapon);
/* 1 and OUT filled when RAW is a complete gfx/hand-weapons.aww. Pure. */
int AW_HandWeaponsDecode(aw_hand_weapons_t *out,const unsigned char *raw,int size);
/* An item model path the hands may draw: progs/inv/ or progs/items/, lower case, ".mdl", no "..". Pure. */
int AW_HandItemPath(const char *path);
/* Inventory installs this: 1 with the weapon value and model of the right-hand weapon the player has equipped. */
extern int (*aw_hand_weapon_item)(int *weapon,char model[64]);
/* After the hands are drawn: 1 with cl.viewent set to the equipped weapon on its tag for this frame. */
int AW_HandWeaponItemApply(void);
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
/* FP-WEAPON-SWAY-61: 1 = Morrowind stiff (aw_fp_sway 2): the ready hands hold the idle's first frame (aw_hands.c;
 * view.c sets it from the setting) */
extern int aw_fp_stiff;
int AW_HandModelsDecode(const unsigned char *data,int size);
void AW_HandModelsLoad(void);
void AW_HandModelsReset(void);
/* Returns one only after selecting a complete, validated appearance. */
int AW_HandModelsApply(void);
#endif
