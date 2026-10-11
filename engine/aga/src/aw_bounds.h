/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_BOUNDS_H
#define AW_BOUNDS_H
/* World bounds (an AmiWind extension, docs/WORLD_BOUNDS.md): a sea current
 * along the edge of the open world, the same rule as tools/world_bounds.py. */
#define AW_BOUNDS_CELL 2048.0f   /* map units per exterior cell */
#define AW_BOUNDS_PRE 128.0f     /* the field starts this far inside the last cell */
#define AW_BOUNDS_FULL 640.0f    /* outward motion fully faded from here */
#define AW_BOUNDS_HARD 768.0f    /* past this the inward push is four times stronger */
#define AW_BOUNDS_CURRENT 150.0f /* Quake's current, units/s at full depth */
#define AW_BOUNDS_INWARD 48.0f   /* back into the world, units/s at full ramp */
#define AW_BOUNDS_GRID 128       /* cells a side the table can hold */
int AW_BoundsBuild(const float *centres,int count);
void AW_BoundsReset(void);
int AW_BoundsReady(void);
int AW_BoundsCells(int *box);
int AW_BoundsField(const float *point,float *depth,float *normal);
int AW_BoundsPush(const float *point,float *velocity,int waterlevel,float *drift);
void AW_BoundsInit(void);
extern int (*aw_bounds_player)(edict_t *,vec3_t);
#endif
