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
/* HELD-LIGHT-OWN-MODEL-61: the arms from parts' light stance (the first-person table's eighth group, 'light': the bare
 * hands with the left arm on the original's torch group; tools/prepare_player_fp_parts.py LIGHT_STANCE), and after the
 * arms are drawn, 1 with cl.viewent set to the held light's own model on their shield bone for this frame. */
#define AW_HAND_LIGHT_STANCE 7
int AW_HandLightItemApply(void);
/* FP-TORCH-HAND-REGRESSION-67: ONE placement of a held item in first person, for both hands, as the original carries
 * it (OpenMW 0.51 npcanimation.cpp, read not copied: a carried light or a shield on "Shield Bone", the weapon on "Weapon
 * Bone", of the first-person skeleton the arms are drawn on) and as our third person does (aw_view.c parts_draws): the
 * view model's place, then that hand's bone of the arms from parts at their frame (BONE_TAG, aw_view.c
 * hand_parts_bone_tag), then the item's own carried place on the bone (CARRIED: a light's carried-light offset, its
 * .hld; NULL none). Nothing else: no offset from the view. Before, a held light was also moved 4 units forward along
 * the view (AW_HAND_LIGHT_FORWARD, the baked torch arms' view offset, cd67bdcf, v0.0.61) while the arms it rides were
 * not: its grip sat 4.00 units from the shield bone, off the hand. Pure. */
#define AW_HAND_RIGHT 0
#define AW_HAND_LEFT 1
void AW_HandItemPlace(const float view_origin[3],const float view_angles[3],const float bone_tag[6],
                      const float carried[6],float origin[3],float angles[3]);
/* PLAYER-CASTING-59 (v0.0.66): the spell stance of the arms from parts, one per spell range (the first-person table's
 * groups 'sps', 'spt', 'sp' after the light: tools/prepare_player_fp_parts.py SPELL_STANCES): AW_HAND_SPELL_STANCE +
 * aw_magic_cast_range (0 self, 1 touch, 2 target). The baked arms carry one spell stance of their own, the target cast:
 * <hands model stem>_sp.mdl (tools/prepare_hand_catalog.py SPELL_STANCE). Each holds the original's open hands
 * (idlespell), raising and lowering (spellcast equip, unequip) and the cast in the attack's 10 frames, the spell's
 * release on the attack's frame AW_HAND_CAST_RELEASE_FRAME (tools/prepare_hands.py SPELL_RELEASE_FRAME). */
#define AW_HAND_SPELL_STANCE 8
#define AW_HAND_CAST_RELEASE_FRAME 6
#define AW_HAND_CAST_FRAMES 10
/* aw_cast.c sets it from the selected spell's first effect (AW_PR_SELF, AW_PR_TOUCH, AW_PR_TARGET); 2 when none */
extern int aw_magic_cast_range;
/* aw_cast.c, a cast that goes: the hands play the cast (the attack clip) from the ready stance. 1 = started. */
int AW_HandsCastStart(void);
/* aw_view.c: the arms from parts' bone of HAND (AW_HAND_RIGHT the weapon bone, AW_HAND_LEFT the shield bone) at the
 * frame drawn now, as a tag in the view model's space (AW_SkelBoneTag at the parts' 0.25 scale); 0 none */
extern int (*aw_hand_parts_bone_tag)(int hand,float tag[6]);
/* LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67, aw_view.c: the arms from parts applied this frame take their left arm from the
 * light stance (AW_HAND_LIGHT_STANCE) at the hands' FRAME (0..27), over the stance applied, in the drawing and in the
 * bone tags; 0 when the table has no light stance or no left arm root (the stance applied stays whole). The layer ends
 * with the next aw_hand_parts_apply. NULL in fixtures without it. */
extern int (*aw_hand_parts_left_light)(int frame);
/* The weapon stances (AW_HandStance) a carried light is held beside: one-handed (1h) and thrown (1t); the two-handed
 * stances, the bow and the crossbow put it away (OpenMW 0.51 updateCarriedLeftVisible: the TwoHanded weapon types,
 * read not copied). Pure. */
int AW_HandStanceOneHanded(int stance);
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
/* PLAYER-CASTING-59: the seconds from a cast's start to the spell's release: the attack clip's frame
 * AW_HAND_CAST_RELEASE_FRAME (the frame AW_HandClipFrame reaches first at that time). Pure. */
float AW_HandCastRelease(const aw_hand_table_t *t);
/* The image's table's AW_HandCastRelease, FALLBACK when the image has none. */
float AW_HandCastReleaseNow(float fallback);
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
/* READY-MAGIC-SHOWS-WEAPON-65 (aw_hands.c): the player's magic is readied (R; aw_cast.c reads and sets it). The
 * weapon key and the magic key are exclusive stances: AW_HandReadyPress changes the hands' goal and the magic flag
 * for one press; AW_HandShowsWeapon = the drawn weapon is shown (the weapon stance only). Pure. */
enum {AW_READY_WEAPON_KEY,AW_READY_MAGIC_KEY};
extern int aw_magic_readied;
void AW_HandReadyPress(int key,int *goal,int *magic);
int AW_HandShowsWeapon(int goal,int magic);
/* READY-MAGIC-SHOWS-WEAPON-65 (v0.0.66; decided for the project, 14 November 2026: readying magic shows the open hands
 * whatever is equipped): the first-person arms drawn (aw_hand_models.c AW_HandModelsApply), by priority. MAGIC ready:
 * the spell stance (the original's open palms, idlespell), whatever the weapon, the carried torch, a held light or the
 * shield; then the lit TORCH's arms, a held LIGHT's stance, and AW_HAND_VIEW_HANDS: the drawn weapon's stance or the bare
 * hands (the fists of hand to hand). As the original (OpenMW 0.51, read not copied: the spell is a two-handed draw
 * state, mwworld/store.cpp's weapon types, and a two-handed draw hides the carried-left item, the torch, a light or the
 * shield, npcanimation.cpp updateCarriedLeftVisible). Before, the lit torch and a held light came first, so with
 * either in the left hand R showed the right hand's fist (v0.0.66-dev1). Pure. */
enum {AW_HAND_VIEW_HANDS,AW_HAND_VIEW_SPELL,AW_HAND_VIEW_TORCH,AW_HAND_VIEW_LIGHT};
int AW_HandView(int magic,int torch,int light);
/* 1 while the left hand's torch, light or shield is carried visibly: 0 (put away, no light cast) while MAGIC is ready,
 * back when the weapon is readied or the magic lowered (aw_torch.c aw_torch_put_away, the guard, the third-person
 * body). Pure. */
int AW_HandCarriesLeft(int magic);
/* aw_view.c installs it: 1 while the equipped weapon must not be drawn in first person (the spell stance). */
extern int (*aw_hand_weapon_hidden)(void);
int AW_HandModelsDecode(const unsigned char *data,int size);
void AW_HandModelsLoad(void);
void AW_HandModelsReset(void);
/* Returns one only after selecting a complete, validated appearance. */
int AW_HandModelsApply(void);
#endif
