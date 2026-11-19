/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The light test and the item tester, one tool (LIGHTTEST-MAP-67, DBG-CYCLEITEMS-67; docs/ITEM_CYCLING.md).
 * dbg lighttest enters the dark light test corridor (maps/lighttest.bsp, tools/build_lighttest.py): the game's scripts
 * paused, nothing over the world but one line at the top left with the held items' names and ids; dbg lighttest 1 also
 * walks it: AW_LIGHTWALK_S seconds forward, the head straight for 10 s, down to the hands from 10 to 15 s, back up to
 * the end. dbg cycleitems puts every item the hands can hold (inventory/holdable.txt, tools/holdable_items.py) in the
 * player's hands there in turn, in the maintainer's order: the hands empty, the item in the hand or hands, the walk,
 * its action (the attack key) where it has one, then the next; the grip measured in every frame of it. */
#ifndef AW_CYCLEITEMS_H
#define AW_CYCLEITEMS_H
#define AW_HOLDABLE_PATH "inventory/holdable.txt"
typedef struct {char name[96],id[64],kind[32],hands[8],action[24];int equips;} aw_holdable_t;
/* One row of the index (a line of N bytes without its end, the fields separated by tabs): 1 with OUT filled when the
 * row is whole (six fields, each within its size; equips 0 or 1). Pure. */
int AW_HoldableParse(const char *line,int n,aw_holdable_t *out);
/* The steps per item, in his order. */
enum {AW_CYCLE_EMPTY,AW_CYCLE_HOLD,AW_CYCLE_WALK,AW_CYCLE_ACTION,AW_CYCLE_STEPS};
/* 1 when the item's ACTION is used with the attack key (a weapon's attack); a shield blocks by itself, a light is
 * carried, a lockpick or probe waits for lockpicking. Pure. */
int AW_CycleHasAction(const aw_holdable_t *h);
/* The tester's line at the top left: "<name> (<id>)  <x>/<total>  <step>". Pure. */
int AW_CycleHudLine(char *out,int size,const aw_holdable_t *h,int index,int total,int step);
/* The light test's line at the top left: what the hands hold, "<name> (<id>)", the left hand first, both joined by
 * "  +  ", "empty hands" when they hold nothing. Pure. */
int AW_LightHeldLine(char *out,int size,const char *left_name,const char *left_id,const char *right_name,
                     const char *right_id);
/* The walk: AW_LIGHTWALK_S seconds forward; the view's pitch (degrees, down positive) T seconds into it: 0 to 10 s,
 * down to AW_LIGHTWALK_DOWN over the next second and held to 15 s, back up over a second, 0 to the end. Pure. */
#define AW_LIGHTWALK_S 20.0f
#define AW_LIGHTWALK_DOWN 45.0f
float AW_LightWalkPitch(float t);
/* the corridor's west end, where the player stands facing along it (tools/build_lighttest.py START) */
#define AW_LIGHTTEST_START_X -1984
#ifndef AW_CYCLE_HOST_TEST
void AW_CycleItemsInit(void);
void AW_CycleItemsFrame(void);    /* after each server frame (aw_animkit.c) */
void AW_CycleItemsDraw(void);     /* screen.c: the line, only in the corridor or while the tester runs */
int AW_CycleItemsActive(void);
/* aw_gallery.c: the player has arrived in the light test corridor: a waiting walk or item tester starts */
void AW_LightTestReady(void);
/* aw_view.c installs it: the grip of what HAND (aw_hand_models.h AW_HAND_LEFT, AW_HAND_RIGHT) holds in the view now:
 * the units from the item's attach point on its bone to the nearest vertex of that hand as drawn; -1 not measured */
extern float (*aw_view_held_gap)(int hand);
#endif
#endif
