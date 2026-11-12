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
#include "aw_skel.h"
#include "aw_torch.h"
#define WEAK __attribute__((weak))
WEAK int AW_QuickCharActive(void){return 0;}
/* TAKEN-LIGHT-FLAME-61: the effect links' users (aw_guard_torch.c, aw_lamps.c, chim/chim_chunks.c) and their source
 * (aw_inventory.c): a fixture without them has no exterior placement to hide and no link to apply. */
WEAK void AW_StaticFlameLink(model_t *world,int ordinal,unsigned reference){(void)world;(void)ordinal;(void)reference;}
WEAK void AW_LampLink(unsigned row,unsigned reference){(void)row;(void)reference;}
WEAK int ChimChunks_GonePid(unsigned pid,int gone){(void)pid;(void)gone;return 0;}
WEAK int AW_AreaEffectPids(unsigned reference,unsigned *pids,int most){(void)reference;(void)pids;(void)most;return 0;}
WEAK void AW_AreaEffectsApply(void){}
/* The crime rules (aw_crime.c, CRIME-59): dbg kill crime (aw_companion.c) asks them; a fixture without them: no crime. */
struct edict_s;
WEAK int AW_CrimeCanCommit(struct edict_s *victim){(void)victim;return 0;}
WEAK int AW_CrimeKilled(struct edict_s *victim,int can_commit){(void)victim;(void)can_commit;return 0;}
/* The game clock (aw_clock.c): the travel services move it by a ride's hours (aw_scene.c travel_ride). */
WEAK int AW_ClockAdvance(int milliseconds){(void)milliseconds;return 0;}
/* The owned-item crosshair cue (view.c defines it; aw_harvest_runtime.c sets it). */
WEAK int (*aw_crosshair_owned)(void);
/* The inventory window's armour rating (aw_worldui.c defines it; aw_combat.c sets it, INVENTORY-NO-ARMOR-RATING-61). */
WEAK float (*aw_worldui_armor_rating)(void);
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
/* The scripts' moon colour (aw_story.c, MWSCRIPT-GAPS-63): fixtures linking r_sky.c without it see a white Secunda. */
WEAK int AW_MoonRed(void) {return 0;}
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
WEAK float AW_InventoryAimDistance(void){return -1;}   /* FOCUS-NPC-OVERRIDES-ITEM-62: no item aimed at */
WEAK int AW_InventoryFocus(const char **name,char *weight_line,char *value_line,int line_size,int *owned){(void)name;(void)weight_line;(void)value_line;(void)line_size;(void)owned;return 0;}
WEAK float AW_ActivateDistance(void){return 48;}
WEAK int AW_ConsoleWidth(void){return 38;}   /* aw_console.c: dbg give weapons lines its table up to it */
WEAK int AW_MoveSneaking(void){return 0;}   /* aw_move.c (SNEAK-58): the HUD's sneak indicator asks it */
WEAK float (*aw_view_sneak)(void);   /* view.c's hook (SNEAK-58), for fixtures with aw_move.c and no view.c */
WEAK int AW_ItemPrompt(char *line,int size,int *steal){(void)line;(void)size;if(steal)*steal=0;return 0;}
WEAK void AW_ConsoleCharacterRed(int x,int y,int c,int red){(void)x;(void)y;(void)c;(void)red;}
WEAK int AW_PlacedFocus(const char **name,char *weight_line,char *value_line,int line_size,int *owned){(void)name;(void)weight_line;(void)value_line;(void)line_size;(void)owned;return 0;}
WEAK void AW_MwscriptRoomShift(float shift[3]){shift[0]=shift[1]=shift[2]=0;}
WEAK int AW_SourceToWorld(const char *name,const float *world,float *local){(void)name;(void)world;(void)local;return 0;}
WEAK int AW_WorldToSource(const char *name,const float *local,float *world){(void)name;(void)local;(void)world;return 0;}
WEAK void AW_UIFocusBox(const char *name,const char *line2,const char *line3,int owned){(void)name;(void)line2;(void)line3;(void)owned;}
WEAK void AW_InventorySpawn(void){}
WEAK void AW_InventoryPreviewClear(void){}
WEAK void AW_ViewInventoryClear(void){}
WEAK int AW_ViewInventoryBody(model_t **model,int *frame){(void)model;(void)frame;return 0;}
WEAK int AW_ViewInventoryHeld(model_t **model,int *frame){(void)model;(void)frame;return 0;}
WEAK int AW_ViewInventoryEquipment(model_t *models[2],float origins[2][3],float angles[2][3]){(void)models;(void)origins;(void)angles;return 0;}
/* INVENTORY-PREVIEW-STALE-61: aw_worldui.c's hook, set by aw_view.c, for fixtures with aw_view.c and no world UI */
WEAK int (*aw_inventory_preview_pending)(void);
/* PLACED-PIT-AXE-NO-FOCUS-61: aw_placed aim's report (aw_inventory.c), for fixtures with aw_placed.c alone */
WEAK void AW_PlacedAimReport(void){}
/* INVENTORY-PREVIEW-BAKED-BODY-59: the assembled body's further parts (aw_view.c), and the posing of a skeletal part
 * (aw_skel.c) for fixtures that link aw_head.c without them: no assembled body, no skeletal part posed. */
/* JOURNAL-BOOK-32-QUESTS-59: the scripts' export to the world change list (aw_save_codec.c holds the pointer; set by
 * aw_mwhost.c) for fixtures that link the book without the save codec */
struct aw_ledger_s;
WEAK void (*aw_save_script_export)(struct aw_ledger_s *ledger);
WEAK int AW_ViewInventoryParts(model_t **models,int max,float scale[3]){(void)models;(void)max;(void)scale;return -1;}
WEAK void AW_SkelPose(const aw_skel_table_t *t,float frame,float world[][3][4]){(void)t;(void)frame;(void)world;}
WEAK int AW_SkelBlockHead(const unsigned char *b,long size,int nv,aw_skel_block_t *out){(void)b;(void)size;(void)nv;(void)out;return 0;}
WEAK void AW_SkelPoseVerts(const unsigned char *verts,const unsigned char *normals,int normal_stride,int n,
    float rest_scale,const float world[][3][4],const float origin[3],const float scale[3],unsigned char *out){
    (void)verts;(void)normals;(void)normal_stride;(void)n;(void)rest_scale;(void)world;(void)origin;(void)scale;(void)out;}
WEAK int AW_InventoryPreviewDraw(model_t *model,int frame,int x,int y,int w,int h,float angle){(void)model;(void)frame;(void)x;(void)y;(void)w;(void)h;(void)angle;return 0;}
WEAK void AW_CombatEquipmentStore(void){}
WEAK void AW_CombatEquipmentChanged(void){}

WEAK void AW_UIBox(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
/* Morrowind's mouse pointer (aw_ui.c, CURSOR-MW-58): fixtures without aw_ui.c draw their window's own cursor. */
WEAK int AW_UICursor(int x,int y){(void)x;(void)y;return 0;}
WEAK void AW_UIThinBox(int x,int y,int w,int h,int lit){(void)x;(void)y;(void)w;(void)h;(void)lit;}
WEAK void AW_UIButton(int x,int y,int w,int h,const char *text,int lit,int colour){(void)x;(void)y;(void)w;(void)h;(void)text;(void)lit;(void)colour;}
WEAK void AW_UIButtonFocus(int x,int y,int w,int h,const char *text,int focused,int colour){(void)x;(void)y;(void)w;(void)h;(void)text;(void)focused;(void)colour;}
WEAK void AW_UISmallBegin(void){}
WEAK void AW_UISmallEnd(void){}
/* aw_character.c's class page draws its skill rows with AW_UIText at one fixed line (CLASS-LIST-LAYOUT-62) */
WEAK void AW_UIText(int x,int y,const char *text,int color){(void)x;(void)y;(void)text;(void)color;}
WEAK int AW_UIWidth(const char *text){return 6*(int)strlen(text);}
WEAK int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}

/* Lighting/renderer fixtures which omit real hand runtime have no active block.
 * Dedicated block fixtures supply strong real functions. */
WEAK int AW_HandBlockApply(void){return 0;}
WEAK int AW_HandBlockItemApply(void){return 0;}
WEAK int AW_HandWeaponItemApply(void){return 0;}
/* HELD-LIGHT-OWN-MODEL-61: a held light of its own (aw_torch.c, aw_hand_models.c, aw_guard_torch.c, aw_view.c);
 * fixtures without them hold none. */
WEAK int AW_HandLightItemApply(void){return 0;}
WEAK void AW_HeldLightDraw(void){}
WEAK const aw_held_light_t *AW_HeldLight(void){return NULL;}
WEAK void AW_HeldFlameDraw(const vec3_t origin,const float shape[4],int view){(void)origin;(void)shape;(void)view;}
WEAK const aw_held_light_t *(*aw_held_light_now)(void);
WEAK int (*aw_view_held_flames)(vec3_t out[AW_HELD_FLAMES]);
WEAK int (*aw_view_held_light)(vec3_t out);
WEAK int (*aw_hand_held_light)(float origin[3],float angles[3]);
WEAK int (*aw_hand_parts_shield_tag)(float tag[6]);
WEAK int (*aw_held_light_item)(char id[64],char model[64],int *radius,int *flags,int *torch_radius);
WEAK const char *AW_InventoryDropReason(void){return "Cannot place item here; kept.";}

WEAK void AW_InventoryGrantCommand(void){}

/* The gameplay recorder (aw_recorder.c, GAME-RECORDER-61): off in fixtures without it, so every hook passes through. */
WEAK void AW_RecorderInit(void){}
WEAK int AW_RecorderActive(void){return 0;}
WEAK void AW_RecorderFrame(void){}
WEAK void AW_RecorderInput(void){}
WEAK int AW_RecorderKey(int key,int down){(void)key;(void)down;return 0;}
WEAK void AW_RecorderLine(const char *text){(void)text;}
WEAK void AW_RecorderMove(usercmd_t *cmd){(void)cmd;}
WEAK const char *AW_RecorderSuffix(void){return "";}
WEAK int AW_RecorderLineShown(void){return 0;}
/* the original's console commands (aw_mwhost.c, MW-CONSOLE-COMMANDS-62): no target, no line taken in fixtures */
WEAK const char *AW_MwConsoleTarget(void){return "";}
WEAK int AW_MwConsoleLine(const char *text){(void)text;return 0;}
WEAK void AW_RecorderDraw(void){}
/* dbg tp's settlements box (aw_tpplaces.c, TP-PICKER-57): no table in fixtures, so the scene picker opens as before. */
WEAK int AW_TpPlacesOpen(void){return 0;}
/* The scripts' control switches (aw_story.c, MWSCRIPT-PLAYER-CONTROL-62): every switch on in fixtures without it. */
WEAK int AW_ControlAllowed(int controls){(void)controls;return 1;}
WEAK int AW_ControlsDisabled(void){return 0;}
/* dbg weapon / dbg gear's box (aw_gearbox.c, WEAPONS-57): no box in fixtures. */
WEAK int AW_GearBoxOpen(int kind){(void)kind;return 0;}
/* dbg give's item picker and count box (aw_gearbox.c, DBG-GIVE-MONEY-62): no box in fixtures. */
WEAK int AW_GiveBoxOpen(void){return 0;}
WEAK int AW_GiveCountBoxOpen(void){return 0;}
/* dbg noburden's mode (aw_move.c, DBG-NOBURDEN-62): off in fixtures without the movement code. */
WEAK int AW_MoveNoBurdenOn(void){return 0;}
WEAK void AW_MoveNoBurdenSet(int on){(void)on;}
/* superspeed's endless stamina (aw_combat.c, DBG-SUPERSPEED-62): nothing to fill in fixtures without the fight sheet. */
WEAK void AW_CombatPlayerFatigueFill(void){}
