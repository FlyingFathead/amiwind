/* SPDX-License-Identifier: GPL-2.0-or-later
 * WEREWOLF-BODY-63, WEREWOLF-TRANSFORM-RULES-PARTIAL-68 (v0.0.68): the player's change of form on the game state
 * (engine/aga/src/aw_were_rules.c), as the original's setWerewolf (OpenMW 0.51 mwmechanics/mechanicsmanagerimp.cpp
 * 1880-1937, read not copied): every item taken off, the werewolf robe added and worn in the robe slot, the temporary
 * effects ended (a worn item's and a script's base modifier are not temporary), the player's attributes and skills kept
 * and the werewolf's set (Acrobatics stays), no change when the form is already so; back: the robe taken off and away,
 * his own stats given back, nothing put back on. The robe is never listed (class.cpp showsInInventory), but in the
 * player's own inventory while he is not a werewolf (the debug route). Fifty changes leave the state as after the
 * first; the save keeps the form and the robe; New Game clears both. Fails on the old engine: there was no robe, no
 * purge and no such rule file. Run by tests/test_werewolf_change.py. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_were_rules.h"
#include "aw_effects.h"

static aw_inventory_item_t shirt, sword, ring, robe;
static void item (aw_inventory_item_t *it, const char *id, int category, unsigned slots)
{
    memset (it, 0, sizeof(*it));
    strcpy (it->id, id);
    it->category = category;
    it->slots = slots;
    it->flags = AW_INV_EQUIP | AW_INV_EQUIP_SUPPORTED;
}
static int worn_slots (void)
{
    int i, n = 0;
    for (i=0 ; i<AW_INVENTORY_SLOTS ; i++)
        n += aw_state.inventory.equipped[i][0] != 0;
    return n;
}
/* the werewolf's settings as the compiler packs them: 35 stats a byte each, four to a number, high byte first */
static int pack (const int *v, int32_t *out)
{
    int i;
    memset (out, 0, 9 * sizeof(*out));
    for (i=0 ; i<35 ; i++)
        out[i/4] |= (int32_t)((uint32_t)(v[i] & 255) << (8 * (3 - i % 4)));
    for (i=35 ; i<36 ; i++)
        out[i/4] |= (int32_t)(255u << (8 * (3 - i % 4)));
    return 9;
}

int main (void)
{
    aw_were_t w;
    aw_actor_t p;
    aw_were_report_t r;
    int32_t numbers[9];
    int v[35], i, n, rows, cycle;
    unsigned char block[256];
    uint32_t refs[4];
    aw_were_t back;
    memset (&w, 0, sizeof(w));
    memset (&aw_state, 0, sizeof(aw_state));
    memset (&p, 0, sizeof(p));
    p.reference = AW_ACTOR_PLAYER_REF;
    for (i=0 ; i<8 ; i++)
        p.attr_base[i] = (short)(40 + i);
    for (i=0 ; i<27 ; i++)
        p.skill_base[i] = (short)(10 + i);
    p.dyn_base[0] = p.dyn_cur[0] = 100;
    item (&shirt, "common_shirt_01", AW_INV_CLOTHING, 1U << AW_SLOT_SHIRT);
    item (&sword, "iron saber", AW_INV_WEAPON, 1U << AW_SLOT_RIGHT);
    item (&ring, "ring_1", AW_INV_CLOTHING, (1U << AW_SLOT_LRING) | (1U << AW_SLOT_RRING));
    item (&robe, AW_WERE_ROBE, AW_INV_CLOTHING, 1U << AW_SLOT_ROBE);
    assert (AW_ItemAdd (&aw_state, shirt.id, 1) && AW_ItemAdd (&aw_state, sword.id, 1) && AW_ItemAdd (&aw_state, ring.id, 1));
    assert (AW_InventoryEquip (&aw_state, &shirt) && AW_InventoryEquip (&aw_state, &sword) && AW_InventoryEquip (&aw_state, &ring));
    assert (worn_slots () == 3);
    /* the effects on him: a cast Fortify Strength (a spell's), a Light from no source (a potion's or a script cast's),
     * the ring's Constant Effect Shield and a script's Resist Fire base modifier */
    assert (AW_EffectsLand (&p, 79, 0, 10, 30, 5) && p.attr_mod[0] == 10);
    assert (AW_EffectsLand (&p, AW_EFFECT_LIGHT, AW_EFFECT_NO_ARG, 20, 60, AW_EFFECT_NO_SOURCE));
    i = !strcmp (aw_state.inventory.equipped[AW_SLOT_LRING], ring.id) ? AW_SLOT_LRING : AW_SLOT_RRING;   /* the ring's slot */
    assert (!strcmp (aw_state.inventory.equipped[i], ring.id));
    assert (AW_EffectsLand (&p, AW_EFFECT_SHIELD, AW_EFFECT_NO_ARG, 5, AW_EFFECT_CONSTANT, AW_EFFECT_SOURCE_CONSTANT + i));
    assert (AW_EffectsBaseModify (p.reference, 90, 20));
    assert (AW_EffectsCountOn (p.reference) == 4);
    /* the werewolf's settings: Strength 150, Agility 150, Hand-to-hand 100, Acrobatics 80 (it stays: SetWerewolfAcrobatics
     * sets it), the rest none */
    for (i=0 ; i<35 ; i++)
        v[i] = 255;
    v[0] = 150;
    v[3] = 150;
    v[8 + 26] = 100;
    v[8 + 20] = 80;
    n = pack (v, numbers);

    /* (b) into the form */
    assert (AW_WereChange (&w, 1, &aw_state, &robe, &p, numbers, n, &r) == 1);
    assert (w.player && r.changed && r.taken_off == 3 && r.robe_added && r.robe_worn && !r.robe_removed && r.stats == 1);
    assert (worn_slots () == 1 && !strcmp (aw_state.inventory.equipped[AW_SLOT_ROBE], AW_WERE_ROBE));
    assert (AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 1);
    assert (AW_StateGet (&aw_state, AW_ITEM, shirt.id) == 1 && AW_StateGet (&aw_state, AW_ITEM, sword.id) == 1);
    /* the cast and the Light ended (the Fortify undone), the ring's Shield went with the ring, the script's stays */
    assert (r.purged == 2 && p.attr_mod[0] == 0 && AW_EffectsCountOn (p.reference) == 1);
    assert (AW_EffectsMagnitude (p.reference, 90, AW_EFFECT_NO_ARG) == 20 && AW_EffectsMagnitude (p.reference, AW_EFFECT_SHIELD, AW_EFFECT_NO_ARG) == 0);
    /* his own kept, the werewolf's set; Acrobatics and the stats without a setting stay */
    assert (w.kept && w.attr[0] == 40 && w.skill[26] == 36);
    assert (p.attr_base[0] == 150 && p.attr_base[3] == 150 && p.attr_base[1] == 41 && p.skill_base[26] == 100);
    assert (p.skill_base[20] == 30);
    printf ("on: %d taken off, robe added %d worn %d, %d effects ended, strength %d, hand-to-hand %d\n",
            r.taken_off, r.robe_added, r.robe_worn, r.purged, p.attr_base[0], p.skill_base[26]);
    /* the robe is never listed: not in a container's, a corpse's or a trade list, not in his own window while a
     * werewolf (it does not open then); his own window lists it while he is himself (the debug route) */
    assert (!AW_WereItemShown (AW_WERE_ROBE, 0, 1) && !AW_WereItemShown (AW_WERE_ROBE, 0, 0));
    assert (!AW_WereItemShown (AW_WERE_ROBE, 1, 1) && AW_WereItemShown (AW_WERE_ROBE, 1, 0));
    assert (AW_WereItemShown (shirt.id, 0, 1) && AW_WereItemShown ("WerewolfRobe2", 0, 1));
    assert (AW_WERE_ROBE_ID ("werewolfrobe") && !AW_WERE_ROBE_ID ("common_shirt_01"));
    /* no change when the form is already so: the robe stays one, worn */
    assert (AW_WereChange (&w, 1, &aw_state, &robe, &p, numbers, n, &r) == 0 && !r.changed);
    assert (AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 1 && worn_slots () == 1 && p.attr_base[0] == 150);

    /* (d) the save keeps the form (AWWF) and the robe worn (the inventory): one robe after the load, never two */
    refs[0] = 8403236;
    n = AW_WerePack (block, sizeof(block), &w, refs, 1);
    assert (n == 83);
    memset (&back, 0, sizeof(back));
    {
        int count = 0;
        uint32_t got[4];
        assert (AW_WereUnpack (block, n, &back, got, 4, &count) == 83 && count == 1 && got[0] == 8403236);
    }
    assert (back.player && back.kept && back.attr[0] == 40 && back.skill[26] == 36);
    {
        /* the robe is an ordinary row of the item table and the robe slot's id: what a save writes of the inventory (the
         * save codec's own tests carry every row and slot); a copy of the table, as the save takes, holds it once */
        aw_state_t snap = aw_state;
        assert (AW_ItemsClone (&snap.items, &aw_state.items));
        assert (AW_StateGet (&snap, AW_ITEM, AW_WERE_ROBE) == 1 && !strcmp (snap.inventory.equipped[AW_SLOT_ROBE], AW_WERE_ROBE));
        printf ("save: the form in AWWF (%d bytes), the robe %d in the inventory, worn in the robe slot\n", n,
                (int)AW_StateGet (&snap, AW_ITEM, AW_WERE_ROBE));
        AW_ItemsFree (&snap);
    }

    /* (c) back: the robe taken off and away, his own stats back, nothing put back on */
    assert (AW_WereChange (&w, 0, &aw_state, &robe, &p, NULL, 0, &r) == 1);
    assert (!w.player && !w.kept && r.robe_removed && r.stats == 2 && !r.robe_added);
    assert (worn_slots () == 0 && AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 0);
    assert (AW_StateGet (&aw_state, AW_ITEM, shirt.id) == 1 && AW_StateGet (&aw_state, AW_ITEM, ring.id) == 1);
    assert (p.attr_base[0] == 40 && p.attr_base[3] == 43 && p.skill_base[26] == 36 && p.skill_base[20] == 30);
    assert (AW_EffectsCountOn (p.reference) == 1);
    printf ("off: robe removed %d, strength %d, hand-to-hand %d, worn %d\n", r.robe_removed, p.attr_base[0],
            p.skill_base[26], worn_slots ());
    /* 50 changes on and off: the state is as after the first (rows, counts, stats, effects) */
    rows = AW_ItemCount (&aw_state);
    for (cycle=0 ; cycle<50 ; cycle++)
    {
        assert (AW_WereChange (&w, 1, &aw_state, &robe, &p, numbers, 9, &r) && r.robe_worn && w.player);
        assert (worn_slots () == 1 && p.attr_base[0] == 150);
        assert (AW_WereChange (&w, 0, &aw_state, &robe, &p, NULL, 0, &r) && r.robe_removed && !w.player);
    }
    assert (AW_ItemCount (&aw_state) == rows && worn_slots () == 0 && AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 0);
    for (i=0 ; i<8 ; i++)
        assert (p.attr_base[i] == 40 + i);
    for (i=0 ; i<27 ; i++)
        assert (p.skill_base[i] == 10 + i);
    assert (AW_EffectsCountOn (p.reference) == 1 && !w.kept);
    printf ("50 changes: item rows %d as after the first, robe 0, worn 0, stats own, effects 1\n", AW_ItemCount (&aw_state));

    /* a robe given by hand (dbg give werewolfrobe): the change adds one more and wears it; back: one taken away, the
     * given one stays, not worn (the original's add and remove of one) */
    assert (AW_ItemAdd (&aw_state, AW_WERE_ROBE, 1));
    assert (AW_WereChange (&w, 1, &aw_state, &robe, &p, numbers, 9, &r) && AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 2);
    assert (AW_WereChange (&w, 0, &aw_state, &robe, &p, NULL, 0, &r) && AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 1);
    assert (worn_slots () == 0);
    assert (AW_ItemAdd (&aw_state, AW_WERE_ROBE, -1));
    /* no robe in this game's data (an image without Bloodmoon): the form holds without it; no player record: the
     * inventory alone */
    assert (AW_InventoryEquip (&aw_state, &shirt));
    assert (AW_WereChange (&w, 1, &aw_state, NULL, &p, numbers, 9, &r) && w.player && !r.robe_added && worn_slots () == 0);
    assert (AW_WereChange (&w, 0, &aw_state, NULL, &p, NULL, 0, &r) && !w.player && !r.robe_removed && p.attr_base[0] == 40);
    assert (AW_WereChange (&w, 1, &aw_state, &robe, NULL, numbers, 9, &r) && r.robe_worn && !r.stats && !r.purged);
    assert (AW_WereChange (&w, 0, &aw_state, &robe, NULL, NULL, 0, &r) && r.robe_removed);

    /* New Game: the state reset (story and globals) and the werewolf state's (aw_mwhost.c forced_reset): neither the
     * form nor the robe survives */
    assert (AW_WereChange (&w, 1, &aw_state, &robe, &p, numbers, 9, &r) && w.player);
    AW_StateReset ();
    memset (&w, 0, sizeof(w));
    assert (!w.player && AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE) == 0 && worn_slots () == 0);
    printf ("new game: form %d, robe %d, worn %d\n", w.player, (int)AW_StateGet (&aw_state, AW_ITEM, AW_WERE_ROBE), worn_slots ());
    return 0;
}
