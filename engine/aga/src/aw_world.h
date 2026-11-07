/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_WORLD_H
#define AW_WORLD_H
int AW_WorldDestination(const char *,const float *,char *,float *);
/* The shared conversion (CHIM-FRAME-SOURCE-CONVERSION-59): the region table first, then the loaded CHIM frame. */
int AW_WorldToSource(const char *,const float *,float *);
int AW_SourceToWorld(const char *,const float *,float *);
/* The region table alone, the shared conversion's first half; no other file calls these. */
int AW_RegionWorldToSource(const char *,const float *,float *);
int AW_RegionSourceToWorld(const char *,const float *,float *);
int AW_WorldMapTarget(const float *,char *,float *);
/* DEBUG-TP-MINIWIND-36: a disk without the open-world table (a MiniWind) and a point inside the loaded map */
int AW_WorldHasDirectory(void);
int AW_WorldLoadedTarget(const char *,const float *,char *,float *);
int AW_CellMap(int,int,char *,int);
const char *AW_SceneName(void);
const char *AW_SceneWalkModel(void);
int AW_MapTeleport(const float *);
int AW_MapTeleportAt(const float *,int);
int AW_SceneLoadRoom(const char *,const float *,float);
int AW_SceneShot(int,const char *,const float *,int,float,float);
qboolean AW_MapPlaceBelow(edict_t *,const float *);
qboolean AW_MapPlace(edict_t *,const float *);
int AW_WorldContains(const char *,const float *);
int AW_WorldRegionCentres(float *,int);
const char *AW_RegionNameAt(const float *source_coordinates);
int AW_RegionIndexAt(const float *source_coordinates);
#endif
