/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_LINKS_H
#define AW_LINKS_H
/* Prototypes of AmiWind engine functions that are called from another file
 * (or kept public for the host tests) and had no shared declaration: the
 * defining file and the callers include this header, so the compiler checks
 * every call and definition against one prototype (-Wmissing-prototypes,
 * ENGINE-STRICT-WARNINGS-36). Needs quakedef.h first. */

/* aw_arena.c */
void AW_ArenaCommand(int argc,char **argv);
void AW_ArenaInit(void);
void AW_ArenaEnd(void);
/* aw_cam.c */
int AW_CamSavesFolder(char *out,int size);
void AW_CamInit(void);
/* aw_companion.c */
int AW_ActorOutOfView(edict_t *e,edict_t *p);
int AW_StuckMethod(int kind);
/* aw_fog.c */
int AW_DrawDistance(void);
void AW_SetDrawDistance(int value);
void AW_FogDepths(byte *table,int distance);
int AW_FogExactActive(void);
float AW_FogExactDepth(void);
/* aw_gallery.c */
int AW_GalleryArenaEnter(const char *map);
void AW_GalleryArenaReload(void);
void AW_GalleryArenaLeave(void);
int AW_GalleryArenaBack(vec3_t origin,vec3_t angles);
void AW_GalleryHandsDrawn(edict_t *p);
int AW_GalleryFind(const char *search,int index,char *id,char *name,char *model,int *total);
/* aw_hud.c */
void Sbar_DeathmatchOverlay(void);
/* aw_menu.c */
void M_Menu_Main_f(void);
void M_Menu_Quit_f(void);
/* aw_opening.c */
int AW_OpeningStoryHidden(void);
/* aw_profile.c */
int AW_FpsTenths(void);
/* aw_scene.c */
int AW_SceneMapMarker(float *source);
/* aw_scenery.c */
int AW_SceneryCount(void);
/* aw_walk.c */
int AW_TerrainFloor(edict_t *e,int player);
void AW_WalkPlayer(edict_t *p);

#endif
