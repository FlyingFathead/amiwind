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
int AW_HandModelsDecode(const unsigned char *data,int size);
void AW_HandModelsLoad(void);
void AW_HandModelsReset(void);
/* Returns one only after selecting a complete, validated appearance. */
int AW_HandModelsApply(void);
#endif
