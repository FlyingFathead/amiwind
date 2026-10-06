/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_HARVEST_H
#define AW_HARVEST_H
#include <stdio.h>
#include "aw_state.h"
#define AW_HARVEST_NODES 64
#define AW_HARVEST_EDGES 256
#define AW_HARVEST_PLANTS 24
#define AW_HARVEST_MODELS 8
typedef struct {char path[64];unsigned char digest[32];float mins[3],maxs[3];} aw_harvest_model_t;
typedef struct {int kind,flags,chance,first,count;char id[64],label[64];} aw_harvest_node_t;
typedef struct {int node,level,count;} aw_harvest_edge_t;
typedef struct {
    char key[64],label[64],model[16];unsigned reference;
    float origin[3],angles[3];int flags,first,count;
    int slot; /* AWH3: one-based global placement index, independent of map. */
    float scale; /* AWH4 external alias only; legacy inline brushes unchanged. */
} aw_harvest_plant_t;
typedef struct {
    int nodes,edges,plants;
    int slots;unsigned char catalogue[32]; /* zero slots: legacy AWH1/AWH2 */
    int representation,models; /* 4: shared alias catalogue; 0: legacy brush. */
    aw_harvest_model_t model[AW_HARVEST_MODELS];
    aw_harvest_node_t node[AW_HARVEST_NODES];
    aw_harvest_edge_t edge[AW_HARVEST_EDGES];
    aw_harvest_plant_t plant[AW_HARVEST_PLANTS];
} aw_harvest_t;
/* Catalogue load fails closed. kind: 0 ingredient, 1 LEVI, 2 missing item. */
int AW_HarvestRead(FILE *,int,aw_harvest_t *);
int AW_HarvestValidate(const aw_harvest_t *);
/* Validated external model index, or -1 for an invalid/legacy binding. */
int AW_HarvestModelIndex(const aw_harvest_t *,int);
int AW_HarvestHidden(const aw_harvest_t *,int,const aw_state_t *);
/* Collected placement facts only; EMPTY, repeated encounters and item quantity
 * are not picked mushroom counts. AWH3 uses dedicated global placement state;
 * legacy catalogues retain their older saved-global representation. */
int AW_HarvestPickedCount(const aw_state_t *);
/* First encounter: persist roll/level, classify without granting items.
 * 1 available, 0 absent (empty or harvested), -1 unresolved data/state capacity. */
int AW_HarvestPrepare(const aw_harvest_t *,int,aw_state_t *,int,uint32_t);
/* 1 collected, 2 original empty result, 0 already harvested, -1 rejected.
 * Loot seed/level persists even if inventory capacity rejects the transfer.
 * No item or harvested fact is committed until the complete transfer succeeds. */
int AW_HarvestTake(const aw_harvest_t *,int,aw_state_t *,int,uint32_t);
#endif
