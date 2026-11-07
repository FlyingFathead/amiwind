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
/* Original registration HUD channels, independent of manual HUD hiding and
 * weapon readiness. The map/menu admission is a separate feature. */
enum aw_story_hud { AW_HUD_STATS=1, AW_HUD_WEAPON=2, AW_HUD_MAGIC=4, AW_HUD_ALL=7 };
int AW_StoryHudChannels(void);
int AW_StoryPapersRead(void);
/* The inventory window during the registration: from the papers' activation on (CHARGEN-INVENTORY-LOCKED-60). */
int AW_StoryInventoryAllowed(void);
int AW_StoryViewAllowed(void);
int AW_StoryDoor(unsigned reference);
void AW_ExpandPlayerName(char *out, unsigned capacity, const char *text);
/* The player's control switches the scripts set (MWSCRIPT-PLAYER-CONTROL-62; rules from OpenMW 0.51
 * mwinput/controlswitch.cpp, mwscript/controlextensions.cpp and miscextensions.cpp OpEnableTeleporting, mwworld World
 * enableTeleporting / enableLevitation): Disable/EnablePlayerControls, -Fighting, -Jumping, -Looking, -Magic,
 * -ViewSwitch, -VanityMode, -Teleporting, -Levitation and the Get...Disabled readers. Every switch starts on in a new
 * game; the disabled ones are one bit mask in the saved named facts ("amiwind:controls", no new save field: an older
 * save reads 0, everything on). They are separate from the opening's own rule (the AW_Story* permissions above): a
 * control is usable only when both allow it. */
enum aw_control {
    AW_CONTROL_PLAYER=1, AW_CONTROL_FIGHTING=2, AW_CONTROL_JUMPING=4, AW_CONTROL_LOOKING=8, AW_CONTROL_MAGIC=16,
    AW_CONTROL_VIEWSWITCH=32, AW_CONTROL_VANITY=64, AW_CONTROL_TELEPORTING=128, AW_CONTROL_LEVITATION=256,
    AW_CONTROL_ALL=511
};
#define AW_CONTROL_FACT "amiwind:controls"
int AW_ControlsDisabled(void);              /* the mask of switches a script turned off */
int AW_ControlAllowed(int controls);        /* 1 when none of CONTROLS is off */
int AW_ControlSet(int controls,int enable); /* 1 when kept (0: the named facts are full; nothing changed) */
const char *AW_ControlName(int control);    /* "playercontrols" ... for one bit, "" else */
#endif
