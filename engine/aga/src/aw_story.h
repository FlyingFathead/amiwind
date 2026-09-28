/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_STORY_H
#define AW_STORY_H
#include "aw_state.h"

/* Persistent values only. Map-owned edicts and navigation pointers never live
 * here. Explicit stages make control and door gates independent of map loads. */
enum aw_stage {
    AW_STAGE_DEMO, AW_STAGE_SHIP, AW_STAGE_DOCK, AW_STAGE_RACE,
    AW_STAGE_OFFICE, AW_STAGE_CLASS, AW_STAGE_BIRTH, AW_STAGE_REVIEW,
    AW_STAGE_PAPERS, AW_STAGE_COURTYARD, AW_STAGE_CAPTAIN, AW_STAGE_RELEASED
};
typedef struct {
    int stage, dock, census, hall, captain;
    int ship_disabled, captain_hint, hall_open;
    float dock_timer, census_timer, hall_timer;
    char name[32];
} aw_story_t;
extern aw_story_t aw_story;
void AW_StoryReset(int new_game);
int AW_StoryTransition(int next);
int AW_StoryRestricted(void);
int AW_StoryFighting(void);
int AW_StoryDoor(unsigned reference);
void AW_ExpandPlayerName(char *out, unsigned capacity, const char *text);
#endif
