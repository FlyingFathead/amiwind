/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_PLACED_H
#define AW_PLACED_H
/* WORLD-OBJECT-PLACEMENT-59 (aw_placed.c): the placed items the map does not draw itself, as references to the shared
 * item models. Init once (the cvar aw_placed and the hooks of aw_inventory.c and aw_mwhost.c); Link once per client
 * frame after the scenery and harvest; Count and Models: the rows drawn and the models loaded on this level. */
void AW_PlacedInit(void);
void AW_PlacedLink(void);
int AW_PlacedCount(void);
int AW_PlacedModels(void);
/* aw_mwhost.c: set by AW_PlacedInit; 1 when REFERENCE is drawn by the placed items (AW_ObjectTake may hide it). */
extern int (*aw_object_drawn)(unsigned reference);
/* aw_scenery.c: set by AW_PlacedInit to AW_PlacedLink; AW_SceneryLink calls it every client frame. */
extern void (*aw_placed_link)(void);
/* `aw_placed crime ...` (STEAL-WITNESSED-NO-CRIME-61): set by aw_crime.c AW_CrimeInit; NULL: no crime layer */
extern void (*aw_placed_crime)(void);
#endif
