/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_INVENTORY_H
#define AW_INVENTORY_H
#define AW_INVENTORY_MODELS 16
#include "aw_state.h"
enum {AW_INV_ALL,AW_INV_WEAPON,AW_INV_ARMOUR,AW_INV_CLOTHING,AW_INV_POTION,
      AW_INV_INGREDIENT,AW_INV_BOOK,AW_INV_MISC};
enum {AW_SLOT_HELMET,AW_SLOT_CUIRASS,AW_SLOT_GREAVES,AW_SLOT_LPAULDRON,
      AW_SLOT_RPAULDRON,AW_SLOT_LGAUNTLET,AW_SLOT_RGAUNTLET,AW_SLOT_BOOTS,
      AW_SLOT_SHIRT,AW_SLOT_PANTS,AW_SLOT_SKIRT,AW_SLOT_ROBE,AW_SLOT_LRING,
      AW_SLOT_RRING,AW_SLOT_AMULET,AW_SLOT_BELT,AW_SLOT_RIGHT,AW_SLOT_LEFT,
      AW_SLOT_AMMUNITION};
#define AW_INV_EQUIP 1U
#define AW_INV_DROP 2U
#define AW_INV_EQUIP_SUPPORTED 4U
#define AW_INV_SCRIPTED 8U
#define AW_INV_CONSTANT_EFFECT 16U
typedef struct {
    char id[64],name[96],model[64],icon[64],enchantment[64],script[64];
    uint32_t slots,flags;
    int category,subtype,value;
    float weight;
    int weapon,weapon_skill,damage[6],shield_class,armor_skill_base;
    float reach,speed,health,armor;
    /* Catalogue bytes 496..: 0 none, else the ENDT type + 1 (AW_ENCH_*), and the
     * maximum charge (OpenMW getEnchantmentCharge, computed by the builder). */
    int enchant_kind;
    float charge_max;
} aw_inventory_item_t;
enum {AW_ENCH_NONE,AW_ENCH_ONCE,AW_ENCH_STRIKES,AW_ENCH_USED,AW_ENCH_CONSTANT};
/* Selected magic item and enchantment charge (aw_magic_state_t). Pure rules:
 * select only an owned Cast Once / Cast When Used item (OpenMW SpellModel);
 * charge is full unless recorded; recharge only When Used / When Strikes
 * items, by fMagicItemRechargePerSecond per second (OpenMW recharge.cpp). */
int AW_MagicSelectable(const aw_inventory_item_t *);
int AW_MagicSelect(aw_state_t *,const aw_inventory_item_t *);
void AW_MagicClear(aw_state_t *);
float AW_MagicCharge(const aw_state_t *,const aw_inventory_item_t *);
int AW_MagicSetCharge(aw_state_t *,const aw_inventory_item_t *,float);
int AW_MagicRecharge(aw_state_t *,const aw_inventory_item_t *,float seconds,float rate);
float AW_InventoryCondition(const char *id);
int AW_MagicSelectedItem(aw_inventory_item_t *out);
void AW_MagicFrame(float seconds);
float AW_MagicRechargeRate(void);
/* Pure transactional rules. A failed operation leaves all state unchanged.
 * Placement must already have passed the world's trace/model admission. */
int AW_InventoryEquipped(const aw_state_t *,const char *id);
int AW_InventoryEquipSlot(aw_state_t *,const aw_inventory_item_t *,int slot);
int AW_InventoryEquip(aw_state_t *,const aw_inventory_item_t *);
int AW_InventoryUnequip(aw_state_t *,const char *id);
int AW_InventoryDrop(aw_state_t *,const aw_inventory_item_t *,int32_t count,
                     const char *scene,const float position[3],float yaw);
int AW_InventoryPickup(aw_state_t *,int drop);
/* Declarations remain visible to pure-rule/UI fixtures; the implementation
 * switch changes linked code, never the callable ABI. */
/* Ordered ASCII case-insensitive comparison; unlike Quake equality helpers. */
int AW_InventoryCompare(const char *,const char *);
int AW_InventoryRead(const char *,aw_inventory_item_t *);
int AW_InventoryEquippedItem(int slot,aw_inventory_item_t *out);
int AW_InventoryCanEquip(const aw_inventory_item_t *item);
void AW_InventoryInit(void);
void AW_InventoryGrantCommand(void);
const char *AW_InventoryDropReason(void);
int AW_InventoryBootstrap(void);
int AW_InventoryDropHere(const aw_inventory_item_t *,int32_t count);
int AW_InventoryUse(void);
const char *AW_InventoryHint(void);
void AW_InventorySpawn(void);
void AW_InventoryOpen(void);
#endif
