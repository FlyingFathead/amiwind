/* SPDX-License-Identifier: GPL-2.0-or-later
 * Weak stand-ins for engine modules that many native fixtures do not link:
 * the quick character screen (aw_quickchar.c), the test harness channels
 * (aw_testbox.c) and the partial-area notice (aw_miniwind.c). A fixture that
 * links the real module gets the real functions (strong symbols win); every
 * other fixture sees "not active / not present", which is what a normal game
 * without those features does. tests/test_aga_native_source.py adds this file
 * to every native compile. */
#include "quakedef.h"
#include "aw_miniwind.h"
#include "aw_quickchar.h"
#include "aw_testbox.h"
#include "aw_weather.h"
#define WEAK __attribute__((weak))
WEAK int AW_QuickCharActive(void){return 0;}
/* The game clock (aw_clock.c): the travel services move it by a ride's hours (aw_scene.c travel_ride). */
WEAK int AW_ClockAdvance(int milliseconds){(void)milliseconds;return 0;}
/* The owned-item crosshair cue (view.c defines it; aw_harvest_runtime.c sets it). */
WEAK int (*aw_crosshair_owned)(void);
/* The inventory picture: still by default (aw_view.c); fixtures time it with a frozen clock. */
WEAK int AW_ViewInventoryLive(void){return 0;}
WEAK double Sys_FloatTime(void){return 0;}
WEAK int AW_QuickCharKey(int key){(void)key;return 0;}
WEAK void AW_QuickCharDraw(void){}
WEAK void AW_QuickCharTick(void){}
WEAK int AW_QuickCharOpen(int pages,aw_quickchar_done_t on_done){(void)pages;(void)on_done;return 0;}
WEAK int AW_QuickCharScripted(void){return 0;}
WEAK int AW_SkipCensus(void){return 0;}
WEAK void AW_QuickCharInit(void){}
WEAK int AW_TestBootExec(void){return 0;}
WEAK int AW_TestBootSkipLogo(void){return 0;}
WEAK void AW_TestBoxFrame(void){}
WEAK void AW_TestPollFrame(void){}
WEAK void AW_TestBoxPrint(const char *text){(void)text;}
WEAK void AW_TestBoxInit(void){}
WEAK int AW_MiniwindActive(void){return 0;}
WEAK const aw_miniwind_t *AW_Miniwind(void){static aw_miniwind_t none;return &none;}
WEAK int AW_MenuHeaderLines(const char *text,int width,char lines[2][AW_MINIWIND_HEADER]){
    (void)text;(void)width;lines[0][0]=lines[1][0]=0;return 0;
}
/* Demo playback's CHIM hook (aw_scenery.c): fixtures linking cl_parse.c without aw_scenery.c. */
WEAK void (*aw_demo_map_begin)(void);
/* The map load step (snd_dma.c, AUDIO-LOAD-29): fixtures linking sv_main.c or cl_parse.c without snd_dma.c. */
WEAK const char *aw_load_phase = "";
WEAK void S_LoadingMark(void) {}
/* The music's dry count (aw_music.c): fixtures linking snd_dma.c without aw_music.c (its load meter reads it). */
WEAK unsigned long AW_MusicSilentSpans(void) {return 0;}
WEAK void AW_MusicLoadPump(void) {}
/* Region weather (aw_weather.c): fixtures linking r_sky.c without it see no weather table, so the
 * clear sky every earlier sky contract was written against (SKY-REDMOUNTAIN-BLUE-44). */
WEAK void AW_WeatherInit(void) {}
WEAK int AW_WeatherFrame(int days,int milliseconds,aw_weather_blend_t *out){(void)days;(void)milliseconds;(void)out;return 0;}
/* The interior fog ramp (r_sky.c, INTERIOR-FOG-UNUSED-51): fixtures linking aw_fog.c without r_sky.c draw no interior fog. */
WEAK const unsigned char *R_InteriorFogColours(int r,int g,int b){(void)r;(void)g;(void)b;return 0;}
/* The combat layer's death hook (aw_combat.c, COMBAT-PACK-SLOTS-57): fixtures linking aw_actors.c without it. */
WEAK void (*aw_combat_actor_died)(struct edict_s *e);
/* The sky haze level (aw_fog.c, FOG-SKY-UNFOGGED-57): fixtures linking r_sky.c without aw_fog.c see no haze. */
WEAK int AW_SkyHazeNow(void) {return 0;}
/* The weather's land light (WEATHER-AMBIENT-SUN-UNUSED-51): never reached without a weather (key 0). */
WEAK int AW_WeatherLightOn(void) {return 1;}
WEAK int AW_WeatherMountainLevel(void) {return 0;}
/* The falling weather and the mesh smoke (aw_atmos.c, WEATHER-RAIN, MESH-PARTICLE-EMITTERS): nothing without it. */
WEAK void AW_AtmosInit(void) {}
WEAK void AW_AtmosUpdate(void) {}
WEAK int AW_WeatherFalling(int *strength) {if(strength)*strength=0;return 0;}
/* Flame light flicker (aw_torch.c): steady without it. */
WEAK float AW_LightFlicker(unsigned seed) {(void)seed;return 1;}
/* The storm at the player (ACTOR-STORM-POSE-51): none without the weather module. */
WEAK int AW_WeatherStorm(float dir[2]) {(void)dir;return 0;}
WEAK int AW_WeatherFacesStorm(float yaw,const float dir[2]) {(void)yaw;(void)dir;return 0;}
WEAK void AW_WeatherLightTone(const aw_weather_blend_t *blend,int a,int b,int mix,int *tone)
{(void)blend;(void)a;(void)b;(void)mix;tone[0]=tone[1]=tone[2]=256;}
/* The animation kit console (aw_animkit.c): nothing to drive in fixtures without it. */
WEAK void AW_AnimKitTick(void) {}
WEAK void AW_AnimKitInit(void) {}
/* DemoWind (aw_demowind.c): never on in fixtures. */
WEAK void AW_DemoWindInit(void) {}
WEAK void AW_DemoWindDraw(void) {}
WEAK int AW_DemoWindActive(void) {return 0;}
WEAK int AW_DemoWindKey(int key,int down) {(void)key;(void)down;return 0;}
/* The Halloween scene (aw_halloween.c): nothing runs in fixtures without it. */
WEAK void AW_HalloweenInit(void) {}
WEAK void AW_HalloweenTick(void) {}
WEAK void AW_HalloweenDraw(void) {}
WEAK int AW_HalloweenCamera(float origin[3],float angles[3]) {(void)origin;(void)angles;return 0;}

/* Inventory dependencies are inactive only in fixtures which omit that module.
 * Dedicated inventory fixtures link its real rules/UI/decoder instead. */
#include "aw_inventory.h"
WEAK int AW_InventoryActive(void){return 0;}
WEAK void AW_InventoryInit(void){}
WEAK int AW_InventoryBootstrap(void){return 0;}
WEAK int AW_InventoryEquippedItem(int slot,aw_inventory_item_t *out){(void)slot;(void)out;return 0;}
WEAK int AW_InventoryRead(const char *id,aw_inventory_item_t *out){(void)id;(void)out;return 0;}
WEAK int AW_InventoryCanEquip(const aw_inventory_item_t *item){(void)item;return 0;}
WEAK int AW_InventoryEquipped(const aw_state_t *state,const char *id){(void)state;(void)id;return 0;}
WEAK int AW_InventoryEquip(aw_state_t *state,const aw_inventory_item_t *item){(void)state;(void)item;return 0;}
WEAK int AW_InventoryUnequip(aw_state_t *state,const char *id){(void)state;(void)id;return 0;}
WEAK int AW_InventoryDropHere(const aw_inventory_item_t *item,int32_t count){(void)item;(void)count;return 0;}
WEAK int AW_InventoryUse(void){return 0;}
WEAK const char *AW_InventoryHint(void){return NULL;}
WEAK void AW_InventorySpawn(void){}
WEAK void AW_InventoryPreviewClear(void){}
WEAK void AW_ViewInventoryClear(void){}
WEAK int AW_ViewInventoryBody(model_t **model,int *frame){(void)model;(void)frame;return 0;}
WEAK int AW_ViewInventoryHeld(model_t **model,int *frame){(void)model;(void)frame;return 0;}
WEAK int AW_ViewInventoryEquipment(model_t *models[2],float origins[2][3],float angles[2][3]){(void)models;(void)origins;(void)angles;return 0;}
WEAK int AW_InventoryPreviewDraw(model_t *model,int frame,int x,int y,int w,int h,float angle){(void)model;(void)frame;(void)x;(void)y;(void)w;(void)h;(void)angle;return 0;}
WEAK void AW_CombatEquipmentStore(void){}
WEAK void AW_CombatEquipmentChanged(void){}

WEAK void AW_UIBox(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
WEAK void AW_UISmallBegin(void){}
WEAK void AW_UISmallEnd(void){}
WEAK int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}

/* Lighting/renderer fixtures which omit real hand runtime have no active block.
 * Dedicated block fixtures supply strong real functions. */
WEAK int AW_HandBlockApply(void){return 0;}
WEAK int AW_HandBlockItemApply(void){return 0;}
WEAK const char *AW_InventoryDropReason(void){return "Cannot place item here; kept.";}

WEAK void AW_InventoryGrantCommand(void){}

/* dbg tp's settlements box (aw_tpplaces.c, TP-PICKER-57): no table in fixtures, so the scene picker opens as before. */
WEAK int AW_TpPlacesOpen(void){return 0;}
