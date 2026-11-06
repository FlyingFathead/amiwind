/* SPDX-License-Identifier: GPL-2.0-or-later
 * The debug torch (test only): while AmiWind is a preview, the player leaves the census office
 * with the original torch (LIGH "torch", catalogue row AW_DEBUG_TORCH_ID) that never burns out
 * (the maintainer, 17 October 2026). aw_debug_torch 1 comes from the builder's game config and
 * stays on until the final game. The grant is one saved transaction (AW_DebugTorchGrant), so a
 * reload or a second census exit never gives a second torch. Equipped in the left hand (the
 * inventory's Equip), it lights the carried torch (aw_torch.c), as a torch does in Morrowind.
 */
#include "quakedef.h"
#include "aw_inventory.h"
/* Not saved in config.cfg: the image's game config decides, a saved value never overrides it. */
static cvar_t aw_debug_torch={"aw_debug_torch","0"};
extern void (*aw_scene_census_exit)(void);
extern int (*aw_torch_item_lit)(void);
static void census_exit(void)
{
    aw_inventory_item_t item;
    if(!aw_debug_torch.value)return;
    if(!AW_InventoryRead(AW_DEBUG_TORCH_ID,&item) || !(item.flags&AW_INV_LIGHT)){
        Con_Printf("Debug torch (test only) unavailable in this image's item catalogue.\n");return;
    }
    if(AW_DebugTorchGrant(&aw_state,1)){
        Con_Printf("%s received (never burns out; equip it in the inventory, or V with hands raised).\n",item.name);
        AW_UISubtitle("","Debug torch (test only) received.",4);
    }
}
static int item_lit(void)
{
    aw_inventory_item_t item;
    return AW_InventoryEquippedItem(AW_SLOT_LEFT,&item) && (item.flags&AW_INV_LIGHT);
}
/* HELD-LIGHT-OWN-MODEL-61 (aw_torch.h aw_held_light_item): the light in the left hand and the torch record's radius,
 * the torch's catalogue row read once (the debug torch's row is the torch's record: the same radius). */
extern int (*aw_held_light_item)(char id[64],char model[64],int *radius,int *flags,int *torch_radius);
static int held_item(char id[64],char model[64],int *radius,int *flags,int *torch_radius)
{
    static int torch=-1;aw_inventory_item_t item;
    if(!AW_InventoryEquippedItem(AW_SLOT_LEFT,&item) || !(item.flags&AW_INV_LIGHT))return 0;
    if(torch<0){
        aw_inventory_item_t t;
        torch=AW_InventoryRead("torch",&t) && (t.flags&AW_INV_LIGHT)?t.light_radius:
              AW_InventoryRead(AW_DEBUG_TORCH_ID,&t) && (t.flags&AW_INV_LIGHT)?t.light_radius:0;
    }
    memcpy(id,item.id,64);id[63]=0;memcpy(model,item.model,64);model[63]=0;
    *radius=item.light_radius;*flags=item.light_flags;*torch_radius=torch;
    return 1;
}
void AW_DebugTorchInit(void)
{
    Cvar_RegisterVariable(&aw_debug_torch);
    aw_scene_census_exit=census_exit;aw_torch_item_lit=item_lit;aw_held_light_item=held_item;
}
