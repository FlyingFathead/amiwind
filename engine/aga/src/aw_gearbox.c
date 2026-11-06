/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg weapon and dbg gear (v0.0.61, WEAPONS-57): every weapon and shield of the game, or every armour and clothing
 * piece, in the console-font list box (aw_listbox.c, the box dbg tp uses), sorted by type, searchable as you type
 * ("long blade 2h", "glass", "heavy"). Choosing a row gives one of it when it is not carried (a test grant, saved and
 * loaded like any other) and equips it by the inventory window's own rules; a row this engine cannot equip yet is only
 * given ("carry only": arrows and bolts, enchanted pieces).
 * The rows come from the item catalogue (inventory/items.awi), read when the box opens and freed when it closes: no
 * memory while it is shut, no file read in play.
 */
#include "quakedef.h"
#include "aw_listbox.h"
#include "aw_tryalloc.h"
#include "aw_inventory.h"
#include "aw_combat.h"

#define GEAR_LABEL 64
typedef struct {char id[64];char label[GEAR_LABEL];short order;} gear_row_t;
static gear_row_t *rows;
static int count,capacity,kind_open,full;

static void collect(void *ctx,const aw_inventory_item_t *it){
    (void)ctx;
    if(full || AW_GearBoxKind(it)!=kind_open)return;
    if(count>=capacity){
        int grow=capacity?capacity*2:512;gear_row_t *more=(gear_row_t *)AW_TryMalloc((unsigned long)grow*sizeof(*more));
        if(!more){full=1;return;}
        if(rows){memcpy(more,rows,(size_t)count*sizeof(*rows));free(rows);}
        rows=more;capacity=grow;
    }
    Q_strncpy(rows[count].id,(char *)it->id,63);rows[count].id[63]=0;
    if(AW_GearBoxLabel(it,rows[count].label,GEAR_LABEL)<0)return;
    rows[count].order=(short)AW_GearBoxOrder(it);
    count++;
}
static int by_type(const void *a,const void *b){
    const gear_row_t *x=(const gear_row_t *)a,*y=(const gear_row_t *)b;
    if(x->order!=y->order)return x->order<y->order?-1:1;
    return AW_InventoryCompare(x->label,y->label);
}
static const char *label(void *ctx,int row){(void)ctx;return rows && row>=0 && row<count?rows[row].label:"";}
static void chosen(void *ctx,int row){
    aw_inventory_item_t item;int have;(void)ctx;
    if(!rows || row<0 || row>=count || !AW_InventoryRead(rows[row].id,&item))return;
    have=AW_StateGet(&aw_state,AW_ITEM,item.id);
    if(have<1){
        if(!AW_ItemAdd(&aw_state,item.id,1)){
            Con_Printf("%s: not given: %s.\n",item.name,AW_ItemRefusalText(&aw_state,AW_ItemRefusal(&aw_state,item.id,1)));return;
        }
        Con_Printf("DIAGNOSTIC gear given: %s (%s).\n",item.name,item.id);
    }
    if((item.flags&(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))!=(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED)){
        Con_Printf("%s: carried; this engine does not equip it yet.\n",item.name);return;
    }
    if(AW_InventoryEquipped(&aw_state,item.id)){Con_Printf("%s: already equipped.\n",item.name);return;}
    if(!AW_InventoryCanEquip(&item)){Con_Printf("%s: cannot be equipped now (as in the inventory window).\n",item.name);return;}
    AW_CombatEquipmentStore();
    if(!AW_InventoryEquip(&aw_state,&item)){Con_Printf("%s: equip refused.\n",item.name);return;}
    AW_CombatEquipmentChanged();
    Con_Printf("DIAGNOSTIC gear equipped: %s (%s).\n",item.name,item.id);
}
static void closed(void *ctx){(void)ctx;free(rows);rows=NULL;count=capacity=0;}
int AW_GearBoxOpen(int kind){
    aw_listbox_spec_t s;int read;double t0=Sys_FloatTime();
    if(AW_ListBoxActive())return 1;
    if(kind!=AW_GEARBOX_WEAPON && kind!=AW_GEARBOX_GEAR)return 0;
    closed(NULL);kind_open=kind;full=0;
    read=AW_InventoryScan(collect,NULL);
    if(read<0 || !count){Con_Printf("Gear list: %s.\n",read<0?"no item catalogue on this disk":"nothing of that kind in it");closed(NULL);return 0;}
    if(full)Con_Printf("Gear list: not enough memory for every row; %d shown.\n",count);
    qsort(rows,(size_t)count,sizeof(*rows),by_type);
    memset(&s,0,sizeof(s));
    s.title=kind==AW_GEARBOX_WEAPON?"Weapons and shields: Enter gives and equips":"Armour and clothing: Enter gives and equips";
    s.count=count;s.label=label;s.chosen=chosen;s.closed=closed;
    if(!AW_ListBoxOpen(&s)){closed(NULL);return 0;}
    Con_Printf("Gear list: %d rows of %d catalogue rows, %lu bytes while open, %.0f ms.\n",count,read,
               (unsigned long)capacity*sizeof(*rows),(Sys_FloatTime()-t0)*1000);
    return 1;
}
