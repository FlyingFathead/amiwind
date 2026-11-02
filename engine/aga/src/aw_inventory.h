/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_INVENTORY_H
#define AW_INVENTORY_H
/* Dropped items' world models a scene may add to the model table (ITEM-WORLD-MODELS-58): up to
 * AW_INVENTORY_MODELS distinct models, each only while a free slot stays below MAX_MODELS less
 * AW_INVENTORY_KEEP_MODELS (the arena opponent's slot). Every map is built with room for
 * AW_INVENTORY_MODELS_GUARANTEED of them (tools/map_engine_limits.py RUNTIME_MODELS); past that a drop
 * takes what the map leaves free and refuses with "World model table full; kept." when nothing is. */
#define AW_INVENTORY_MODELS 64
#define AW_INVENTORY_MODELS_GUARANTEED 16
#define AW_INVENTORY_KEEP_MODELS 1
/* Placed items (WORLD-OBJECT-PLACEMENT-59, progs/items/placed.awp): the distinct item models a level may load for
 * the items the original placed in its room or its exterior cells (the shared item model table; every row is a
 * reference to one of them, never a copy). Every map is built with this room (tools/map_engine_limits.py
 * RUNTIME_MODELS) and the item-models stage refuses a room or exterior neighbourhood that names more
 * (tools/prepare_item_models.py PLACED_MODELS). */
#define AW_PLACED_MODELS 96
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
/* A carried light (catalogue bytes 504..510: burn time, colour; subtype = radius). */
#define AW_INV_LIGHT 32U
/* The debug torch (test only), the maintainer's preview-stage request (17 October 2026): the
 * original torch (LIGH "torch") as one catalogue row that never burns out; given once when the
 * player leaves the census office while aw_debug_torch is 1 (the builder's game config, on until
 * the final game). Not an original item. */
#define AW_DEBUG_TORCH_ID "aw_debug_torch"
#define AW_DEBUG_TORCH_GRANTED "amiwind:debug_torch:granted"
/* The light burn time that never runs out: -1, as OpenMW 0.51 apps/openmw/mwmechanics/actors.cpp
 * ("-1 is infinite light source") treats a held light's remaining time. */
#define AW_LIGHT_INFINITE (-1)
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
    /* AW_INV_LIGHT rows: burn time in seconds (AW_LIGHT_INFINITE = never runs out), radius, colour. */
    int light_time,light_radius;
    /* the record's enchantment points (bytes 504..505 of a row that is not a light): what Enchanting can put on it */
    int enchant_capacity;
    unsigned char light_colour[3];
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
int AW_InventorySetCondition(const char *id,float condition);
/* Pure rules (debug torch): the remaining burn time of a carried light after seconds of use
 * (AW_LIGHT_INFINITE stays infinite; else it counts down to 0, as OpenMW's held light); and the
 * one-time grant: 1 = given now, 0 = switched off, given before, or no room (state unchanged). */
float AW_LightBurn(const aw_inventory_item_t *,float remaining,float seconds);
int AW_DebugTorchGrant(aw_state_t *,int enabled);
/* aw_debug_torch.c: the aw_debug_torch switch, the census-exit grant and the lit torch. */
void AW_DebugTorchInit(void);
int AW_MagicSelectedItem(aw_inventory_item_t *out);
void AW_MagicFrame(float seconds);
float AW_MagicRechargeRate(void);
/* Pure transactional rules. A failed operation leaves all state unchanged.
 * Placement must already have passed the world's trace/model admission. */
/* Equipment rules (pure; aw_inventory.c): an armour type's slot (-1 unknown); the slot a new item clears (a two-handed
 * weapon and a shield exclude each other; -1 none); an equipment slot's armour hit slot (aw_combat.h order; -1 none).
 * Weapon = 1 + the original type, two-handed: 2 long blade, 4 blunt, 5 staff, 6 spear, 8 axe (OpenMW weapontype.hpp). */
#define AW_INV_TWO_HANDED(weapon) ((weapon)==3 || (weapon)==5 || (weapon)==6 || (weapon)==7 || (weapon)==9)
int AW_InventoryArmourSlot(int type);
int AW_InventoryEquipConflict(const aw_inventory_item_t *item,const aw_inventory_item_t *right,const aw_inventory_item_t *left);
int AW_InventoryHitSlot(int slot);
/* The equipped right-hand weapon's original type (WPDT 0..8: short blade, long blade one- and two-handed, blunt one-
 * and two-handed (close and wide), spear, axe one- and two-handed), -1 when the hand is empty (hand to hand). For the
 * hand driver and the player body's group picker (v054-animcover). */
int AW_InventoryEquippedWeaponType(void);
/* The catalogue row of what a hand (AW_SLOT_RIGHT / AW_SLOT_LEFT) of the player holds, for AW_InventoryEquip's conflict
 * rule (set by AW_InventoryInit to AW_InventoryEquippedItem; NULL: no conflict rule, the pure fixtures). */
extern int (*aw_inventory_hand_item)(int slot,aw_inventory_item_t *out);
/* dbg give weapons (DBG-GIVE-WEAPONS-59): the weapon kit the builder chose from the game's records
 * (inventory/weapon-kit.txt, tools/prepare_weapon_kit.py), read on the command only, nothing resident. A row: the
 * item's catalogue id, how many, its kind (W melee, R bow or crossbow, T thrown, A arrows or bolts, S shield), a type
 * label, its name and ten stats as the builder wrote them ("-": not for this kind): chop, slash, thrust (bow,
 * crossbow, thrown and ammunition: chop = their damage), speed, reach, weight, value, health, enchantment points,
 * armour. Pure rules: parse the file (rows, -1 when malformed); the new item kinds the kit needs (-1 when a count
 * would overflow); give it all or nothing (1 given, 0 refused with the state unchanged); one row's console lines,
 * "label value" tokens wrapped so no line is longer than WIDTH (a single token longer than WIDTH stands alone), the
 * last token `equip "ID"` (equippable now) or `carry "ID"` (the lines, -1 when OUT is too small). AW_ConsoleWidth
 * (aw_console.c): the console's characters per line. */
int AW_ConsoleWidth(void);
#define AW_WEAPON_KIT_ROWS 20
#define AW_WEAPON_KIT_STATS 10
typedef struct {
    char id[64],type[24],name[48],stat[AW_WEAPON_KIT_STATS][12];
    int count;char kind;
} aw_kit_row_t;
int AW_WeaponKitParse(const char *text,int length,aw_kit_row_t *rows,int max);
int AW_WeaponKitNeeds(const aw_state_t *,const aw_kit_row_t *rows,int n);
int AW_WeaponKitGrant(aw_state_t *,const aw_kit_row_t *rows,int n);
int AW_WeaponKitLines(const aw_kit_row_t *row,int equippable,int width,char *out,int size);
int AW_InventoryEquipped(const aw_state_t *,const char *id);
int AW_InventoryEquipSlot(aw_state_t *,const aw_inventory_item_t *,int slot);
int AW_InventoryEquip(aw_state_t *,const aw_inventory_item_t *);
int AW_InventoryUnequip(aw_state_t *,const char *id);
int AW_InventoryDrop(aw_state_t *,const aw_inventory_item_t *,int32_t count,
                     const char *scene,const float position[3],float yaw);
int AW_InventoryPickup(aw_state_t *,int drop);
/* CELL-CHANGES-59 (aw_ledger_drops.c): the same rules on the world change list (aw_ledger.h). A drop: COUNT leaves
 * the inventory and a row (key bit 30 + the next serial, DROPPED) lies at AT / WHERE, POSITION (the place's units,
 * aw_ledger.h), YAW; the row's key, 0 when refused (nothing changed). A pickup: the row's items come back and the row
 * goes; 0 when refused. An older save's dropped[] (keyed by map name) moves onto the list as SCENE rows; returns how
 * many moved. */
struct aw_ledger_s;
uint32_t AW_LedgerDrop(aw_state_t *,struct aw_ledger_s *,const aw_inventory_item_t *,int32_t count,
                       int at,int32_t where,const float position[3],float yaw);
int AW_LedgerPickup(aw_state_t *,struct aw_ledger_s *,uint32_t key);
int AW_LedgerAdoptDrops(aw_state_t *,struct aw_ledger_s *);
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
/* The focus box (FOCUS-BOX-58): the aimed ground item within the activation distance, its name and the box's
 * "Weight: x" and "Value: y" lines; owned 1 when taking it would be theft. 0 when no item is aimed at. */
int AW_InventoryFocus(const char **name,char *weight_line,char *value_line,int line_size,int *owned);
float AW_ActivateDistance(void);
/* The same for things placed in the loaded room (id1/focus.awf): items with weight and value, actors and doors with
 * their name only (empty lines). */
int AW_PlacedFocus(const char **name,char *weight_line,char *value_line,int line_size,int *owned);
/* STEAL-PROMPT-58: "E: Take" or "E: Steal" (*steal 1) for the aimed takeable item; 0 for none. */
int AW_ItemPrompt(char *line,int size,int *steal);
/* The book reader's entry (NULL until it exists): opens the readable book placed as REFERENCE; 1 when it opened. */
extern int (*aw_book_reader)(unsigned reference);
/* BOOK-READER-58: the placed book's record id (FOCUS id, 33 bytes) and ownership; 1 when it is in the focus table. */
int AW_PlacedBook(unsigned reference,char *id,int *owned);
/* BOOK-READER-58: take the placed item REFERENCE as E on it would (owned: stolen); 1 when taken or refused. */
int AW_PlacedTake(unsigned reference);
/* WORLD-OBJECT-PLACEMENT-59: the placed item list (progs/items/placed.awp) is read with the focus rows; each row the
 * map does not draw itself is offered to aw_placed_admit (aw_placed.c: returns its drawn index + 1, 0 when it is not
 * drawn); aw_placed_begin forgets the drawn set and returns 0 when nothing is to be drawn. NULL: nothing is. */
extern int (*aw_placed_begin)(void);
extern int (*aw_placed_admit)(unsigned reference,const char *stem,const float local[3],const float angles[3],float scale);
/* Once per client frame (aw_placed.c): read the focus table again when the map or exterior cell changed; 1 outdoors. */
int AW_PlacedRefresh(void);
/* What the last read of the placed list saw: keys read (negative outdoors), rows, rows with no item row in the focus
 * table, rows the map draws itself, rows outside this map, rows offered. */
void AW_PlacedReadStats(int out[6]);
void AW_InventorySpawn(void);
void AW_InventoryOpen(void);
/* CELL-CHANGES-59 slice 3: placed containers (focus.awf 'C' rows and its AWC1 contents list, read on demand) and the
 * world change list's deltas. Contents: the data's list with the deltas, -1 for no container; Count: one id's (-1 no
 * container); Change: COUNT in (> 0) or out (< 0) on the list, what moved (OWNER_MARK: a take is stolen from the
 * owner); Command: aw_placed container ... */
#define AW_CONTAINER_ITEMS 64
typedef struct {char id[33];int count;} aw_container_item_t;
int AW_ContainerContents(unsigned reference,aw_container_item_t *out,int max,int *flags);
int AW_ContainerCount(unsigned reference,const char *id);
int AW_ContainerChange(unsigned reference,const char *id,int count,int owner_mark);
void AW_ContainerCommand(void);
#endif
