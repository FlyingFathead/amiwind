/* SPDX-License-Identifier: GPL-2.0-or-later; include after quakedef.h */
#ifndef AW_HARVEST_RUNTIME_H
#define AW_HARVEST_RUNTIME_H
void AW_HarvestInit(void);
void AW_HarvestBegin(void);
void AW_HarvestClear(void);
void AW_HarvestLink(void);
int AW_HarvestProtect(edict_t *);
void AW_HarvestSpawn(void);
const char *AW_HarvestHint(void);
int AW_HarvestUse(void);
#endif
