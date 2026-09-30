/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_SAVE_H
#define AW_SAVE_H
#include <stdint.h>
#include "aw_story.h"
#include "aw_character.h"
#define AW_SAVE_BYTES 32768
#define AW_SAVE_ACTORS 256
typedef struct {
    uint32_t reference;
    int scene;
    float position[3],angles[3],health;
    int hello_count,manual_count,hello_done;
} aw_saved_actor_t;
typedef struct {
    uint32_t sequence,profile;
    unsigned char content[32];
    char scene[16],label[32];
    float position[3],angles[3];
    aw_story_t story;
    aw_state_t state;
    aw_character_t character;
    int actor_count;
    aw_saved_actor_t actors[AW_SAVE_ACTORS];
} aw_save_t;
int AW_SaveEncode(unsigned char *out,int capacity,const aw_save_t *state);
int AW_SaveDecode(const unsigned char *data,int size,aw_save_t *out);
void AW_SaveInit(void);
void AW_SaveReset(void);
int AW_SaveAllowed(void);
void AW_SaveTick(void);
void AW_SaveCapture(void);
void AW_SaveSpawn(void);
void AW_SaveSchedule(void);
int AW_SaveWrite(int slot);
int AW_SaveRead(uint32_t profile,int slot);
int AW_SaveProfiles(uint32_t *ids,char names[][32],int capacity);
int AW_SaveDescription(uint32_t profile,int slot,char *out,int capacity);
uint32_t AW_SaveProfile(void);
int AW_AutosaveCount(void);
void AW_SetAutosaveCount(int count);
int AW_SaveMenuOpen(int loading);
int AW_SaveMenuActive(void);
int AW_SaveMenuKey(int key);
void AW_SaveMenuDraw(void);
#endif
