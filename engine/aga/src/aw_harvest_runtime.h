/* SPDX-License-Identifier: GPL-2.0-or-later; include after quakedef.h */
#ifndef AW_HARVEST_RUNTIME_H
#define AW_HARVEST_RUNTIME_H
void AW_HarvestInit(void);
void AW_HarvestBegin(void);
void AW_HarvestClear(void);
void AW_HarvestLink(void);
int AW_HarvestProtect(edict_t *);
void AW_HarvestSpawn(void);
typedef int (*aw_harvest_region_at_t)(const float *point,int current,char *map,int size);
int AW_HarvestFollow(aw_harvest_region_at_t,const float *,int);
const char *AW_HarvestHint(void);
int AW_HarvestUse(void);
/* FOCUS-NPC-OVERRIDES-ITEM-62: how far along the view ray (map units from the eye) the plant the use key would pick
 * lies; -1 when none */
float AW_HarvestAimDistance(void);
/* STEAL-WITNESSED-NO-CRIME-61: COUNT of ingredient ID picked from a plant OWNER owns; set by aw_crime.c (NULL: none) */
extern void (*aw_harvest_theft)(const char *owner,const char *id,int count);
void AW_HarvestSweep(int *count,int *bound,int *pickable,int *proxy);
#endif
