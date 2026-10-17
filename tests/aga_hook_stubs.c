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
#define WEAK __attribute__((weak))
WEAK int AW_QuickCharActive(void){return 0;}
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
/* The animation kit console (aw_animkit.c): nothing to drive in fixtures without it. */
WEAK void AW_AnimKitTick(void) {}
WEAK void AW_AnimKitInit(void) {}

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
