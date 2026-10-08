/* SPDX-License-Identifier: GPL-2.0-or-later
 * Data-driven town table. Rows come from aw_town_table.h, generated from
 * config/towns.json and the town configs (tools/town_table.py), like the
 * other converted id1/world tables: no town name is compiled into the
 * region, world, fog, scenery or scene code. Header-only so every native
 * test that compiles one of those modules gets the same table.
 */
#ifndef AW_TOWN_H
#define AW_TOWN_H
#include <string.h>
/* Intro docks and Census courtyard sub-scenes (Seyda Neen). */
#define AW_TOWN_SEYDA_SCENES 1
/* Without its region directory the town runs as one full legacy map. */
#define AW_TOWN_LEGACY_PAYLOAD 2
/* Own door bank only; never the shared scene-doors.txt/scene-links.txt. */
#define AW_TOWN_OWN_DOORS 4
/* func_wall placements go to the shared scenery catalogue (aw_scenery.c). */
#define AW_TOWN_SCENERY 8
/* dbg tp <town> uses the region directory's arrival point. */
#define AW_TOWN_TELEPORT 16
/* Arrival and respawn use interior-style ground placement. */
#define AW_TOWN_GROUND_PLACE 32
#include "aw_town_table.h"
typedef struct {
    const char *name,*title,*prefix,*regions,*travel_npc,*travel_target;
    int region_cap,draw_distance,world_slot,flags,travel_return,handoff;
    float origin[3],core[4];
} aw_town_t;
static __inline__ const aw_town_t *AW_Town(int i)
{
    static const aw_town_t rows[AW_TOWN_COUNT]=AW_TOWN_ROWS;
    return i>=0 && i<AW_TOWN_COUNT?&rows[i]:NULL;
}
/* Index of the town whose runtime map (sv.name) is name, or -1. */
static __inline__ int AW_TownFind(const char *name)
{
    int i;if(!name)return -1;
    for(i=0;i<AW_TOWN_COUNT;i++)if(!strcmp(name,AW_Town(i)->name))return i;
    return -1;
}
/* Index of the town owning a region map name (prefix + 3 digits below its
 * region cap, e.g. bm000..bm063), or -1. */
static __inline__ int AW_TownRegionMap(const char *name)
{
    int i,k,n;const aw_town_t *t;
    if(!name || strlen(name)!=5)return -1;
    for(i=0;i<AW_TOWN_COUNT;i++){
        t=AW_Town(i);if(strncmp(name,t->prefix,2))continue;
        for(n=0,k=2;k<5;k++){if(name[k]<'0' || name[k]>'9')return -1;n=n*10+name[k]-'0';}
        return n<t->region_cap?i:-1;
    }
    return -1;
}
static __inline__ int AW_TownFlag(const char *name,int flag)
{
    int i=AW_TownFind(name);
    return i>=0 && (AW_Town(i)->flags&flag)!=0;
}
#endif
