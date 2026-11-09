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

/* ---- dbg give (DBG-GIVE-MONEY-62) ----
 * dbg give alone (also dbg additem): every item of the catalogue in the same list box as dbg tp and dbg gear, by its
 * in-game name with its record id beside it in the dimmer colour (aw_listbox.c draws what follows a tab dimmer), the
 * kinds as groups (Weapon, Armour, Clothing, Potion, Ingredient, Book, Light, Apparatus, Misc), type to filter by name
 * or id. Choosing a row opens a second box for the count (1 to 1000); choosing that gives the item, saved like any
 * grant. The rows come from the item catalogue, read when the box opens, freed when it closes: one label pool and one
 * row list (about 50 bytes a row while open), nothing while it is shut. */
#define GIVE_NAME 40
typedef struct {long label;short order;} give_row_t;
static give_row_t *give_rows;
static char *give_pool;
static long give_used,give_size;
static int give_count,give_capacity,give_full;
static char give_id[64],give_name[GIVE_NAME+1];   /* the item chosen, for the count box */
static const char *const give_kinds[]={"Weapon","Armour","Clothing","Potion","Ingredient","Book","Light","Apparatus","Misc"};
static int give_kind(const aw_inventory_item_t *it){
    if(it->flags&AW_INV_LIGHT)return 6;
    if((it->flags&AW_INV_ALCHEMY) && it->alchemy_kind==AW_ALCHEMY_APPARATUS)return 7;
    switch(it->category){
    case AW_INV_WEAPON:return 0;case AW_INV_ARMOUR:return 1;case AW_INV_CLOTHING:return 2;case AW_INV_POTION:return 3;
    case AW_INV_INGREDIENT:return 4;case AW_INV_BOOK:return 5;default:return 8;
    }
}
static void give_collect(void *ctx,const aw_inventory_item_t *it){
    char line[24+GIVE_NAME+64];int n,k;(void)ctx;
    if(give_full || !it->id[0])return;
    k=give_kind(it);
    n=snprintf(line,sizeof(line),"%-10s %.*s\t%s",give_kinds[k],GIVE_NAME,it->name[0]?it->name:it->id,it->id);
    if(n<1 || n>=(int)sizeof(line))return;
    if(give_count>=give_capacity){
        int grow=give_capacity?give_capacity*2:1024;give_row_t *more=(give_row_t *)AW_TryMalloc((unsigned long)grow*sizeof(*more));
        if(!more){give_full=1;return;}
        if(give_rows){memcpy(more,give_rows,(size_t)give_count*sizeof(*give_rows));free(give_rows);}
        give_rows=more;give_capacity=grow;
    }
    if(give_used+n+1>give_size){
        long grow=give_size?give_size*2:32768;char *more=(char *)AW_TryMalloc((unsigned long)grow);
        if(!more){give_full=1;return;}
        if(give_pool){memcpy(more,give_pool,(size_t)give_used);free(give_pool);}
        give_pool=more;give_size=grow;
    }
    memcpy(give_pool+give_used,line,(size_t)n+1);
    give_rows[give_count].label=give_used;give_rows[give_count].order=(short)k;give_used+=n+1;give_count++;
}
static int give_by_kind(const void *a,const void *b){
    const give_row_t *x=(const give_row_t *)a,*y=(const give_row_t *)b;
    if(x->order!=y->order)return x->order<y->order?-1:1;
    return AW_InventoryCompare(give_pool+x->label,give_pool+y->label);
}
static const char *give_label(void *ctx,int row){(void)ctx;return give_rows && row>=0 && row<give_count?give_pool+give_rows[row].label:"";}
static void give_closed(void *ctx){
    (void)ctx;free(give_rows);free(give_pool);give_rows=NULL;give_pool=NULL;give_count=give_capacity=0;give_used=give_size=0;
}
static void give_chosen(void *ctx,int row){
    const char *label,*tab,*name;int n;(void)ctx;
    if(!give_rows || row<0 || row>=give_count)return;
    label=give_pool+give_rows[row].label;tab=strchr(label,'\t');
    if(!tab || !tab[1] || strlen(tab+1)>=sizeof(give_id))return;
    strcpy(give_id,tab+1);
    name=label+11;n=(int)(tab-name);if(n<0)n=0;if(n>GIVE_NAME)n=GIVE_NAME;
    memcpy(give_name,name,(size_t)n);give_name[n]=0;
    /* the count box opens once this box has closed (one box at a time; the world window closes it after this) */
    Cbuf_AddText("aw_inventory givecount\n");
}
int AW_GiveBoxOpen(void){
    aw_listbox_spec_t s;int read;double t0=Sys_FloatTime();
    if(AW_ListBoxActive())return 1;
    if(!sv.active || svs.maxclients!=1){Con_Printf("Start or load a game first.\n");return 0;}
    give_closed(NULL);give_full=0;
    read=AW_InventoryScan(give_collect,NULL);
    if(read<0 || !give_count){Con_Printf("Give list: %s.\n",read<0?"no item catalogue on this disk":"no items in it");give_closed(NULL);return 0;}
    if(give_full)Con_Printf("Give list: not enough memory for every row; %d shown.\n",give_count);
    qsort(give_rows,(size_t)give_count,sizeof(*give_rows),give_by_kind);
    memset(&s,0,sizeof(s));
    s.title="Give an item: Enter picks, then the count";
    s.count=give_count;s.label=give_label;s.chosen=give_chosen;s.closed=give_closed;
    if(!AW_ListBoxOpen(&s)){give_closed(NULL);return 0;}
    Con_Printf("Give list: %d items of %d catalogue rows, %lu bytes while open, %.0f ms.\n",give_count,read,
               (unsigned long)give_capacity*sizeof(*give_rows)+(unsigned long)give_size,(Sys_FloatTime()-t0)*1000);
    return 1;
}
static const char *const give_counts[]={"1","2","3","5","10","20","25","50","100","250","500","1000"};
#define GIVE_COUNTS ((int)(sizeof(give_counts)/sizeof(give_counts[0])))
static char give_title[80];
static const char *count_label(void *ctx,int row){(void)ctx;return row>=0 && row<GIVE_COUNTS?give_counts[row]:"";}
static void count_chosen(void *ctx,int row){
    (void)ctx;
    if(row<0 || row>=GIVE_COUNTS || !give_id[0])return;
    AW_InventoryGive(give_id,atol(give_counts[row]));
}
static void count_closed(void *ctx){(void)ctx;give_id[0]=0;give_name[0]=0;}
int AW_GiveCountBoxOpen(void){
    aw_listbox_spec_t s;
    if(!give_id[0] || AW_ListBoxActive())return 0;
    Q_snprintf(give_title,sizeof(give_title),"How many %s?",give_name[0]?give_name:give_id);
    memset(&s,0,sizeof(s));
    s.title=give_title;s.count=GIVE_COUNTS;s.label=count_label;s.chosen=count_chosen;s.closed=count_closed;
    if(!AW_ListBoxOpen(&s)){count_closed(NULL);return 0;}
    return 1;
}
