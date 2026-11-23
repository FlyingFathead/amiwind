/* SPDX-License-Identifier: GPL-2.0-or-later
 * WEREWOLF-BODY-63 (v0.0.68): the werewolf's look from the body recipe (engine/aga/src/aw_player_parts.c). The recipe's
 * pseudo-race "werewolf" on a skeleton letter of its own (w), its table, its groups and its one body part: assembled
 * with no head, hair or worn item, whatever the player wears; the robe slot's werewolf robe is what asks for it; a race
 * on that skeleton wears no item's part (the items have h and k columns only). Fails on the old reader: it took the
 * skeletons h and k only, so the werewolf's race line was never read. Run by tests/test_werewolf_change.py. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_player_parts.h"

static const char *with_wolf =
    "AWPP1\n"
    "T h progs/humanoid.awsk 59 60\n"
    "T w progs/werewolf.awsk 33 34\n"
    "A h 0 progs/parts/hm.anm\n"
    "A h 1 progs/parts/hf.anm\n"
    "A w 0 view/parts_wm.txt\n"
    "A w 1 view/parts_wm.txt\n"
    "R dark|elf 0 h 1.0000 1.0000\n"
    "S dark|elf 0 3 aaaaaaaaaaa3\n"
    "S dark|elf 0 4 aaaaaaaaaaa4\n"
    "H dark|elf 0 b_n_dark|elf_m_head_01 bbbbbbbbbbb1\n"
    "K dark|elf 0 b_n_dark|elf_m_hair_01 ccccccccccc1\n"
    "R werewolf 0 w 1.0000 1.0000\n"
    "R werewolf 1 w 1.0000 1.0000\n"
    "S werewolf 0 3 0f0f0f0f0f03\n"
    "S werewolf 1 3 0f0f0f0f0f03\n"
    "I common_shirt_01 2 3=111111111111/222222222222,333333333333/444444444444\n"
    "I werewolfrobe 24 3=-/-,-/-\n";

/* an older image: the same recipe without the werewolf's rows */
static const char *without_wolf =
    "AWPP1\n"
    "T h progs/humanoid.awsk 59 60\n"
    "A h 0 progs/parts/hm.anm\n"
    "R dark|elf 0 h 1.0000 1.0000\n"
    "S dark|elf 0 3 aaaaaaaaaaa3\n"
    "S dark|elf 0 4 aaaaaaaaaaa4\n"
    "I werewolfrobe 24 3=-/-,-/-\n";

int main (void)
{
    aw_parts_body_t b;
    const char *worn[2] = {"common_shirt_01", "werewolfrobe"};
    /* the robe slot's werewolf robe asks for the werewolf, in any case; nothing else does */
    assert (AW_PartsWerewolfWorn ("werewolfrobe") && AW_PartsWerewolfWorn ("WerewolfRobe"));
    assert (!AW_PartsWerewolfWorn ("werewolfrobe2") && !AW_PartsWerewolfWorn ("werewolf") &&
            !AW_PartsWerewolfWorn ("") && !AW_PartsWerewolfWorn (NULL));
    assert (!strcmp (AW_PARTS_WEREWOLF_RACE, "werewolf"));
    /* (a) the werewolf: its own table, groups and skeleton; its one body part; no head, hair or item part, even with
     * items asked (a race on the w skeleton has no item column) */
    assert (AW_PartsAssemble (with_wolf, (long)strlen (with_wolf), AW_PARTS_WEREWOLF_RACE, 0, NULL, NULL, NULL, 0, &b));
    assert (b.count == 1 && b.slot[0] == 3 && !strcmp (b.model[0], "progs/parts/0f/0f0f0f0f03.mdl"));
    assert (!strcmp (b.table, "progs/werewolf.awsk") && !strcmp (b.anm, "view/parts_wm.txt"));
    assert (b.weapon_bone == 33 && b.shield_bone == 34 && !b.beast && b.weight == 1.0f && b.height == 1.0f);
    printf ("werewolf: %d part, %s, table %s, groups %s\n", b.count, b.model[0], b.table, b.anm);
    assert (AW_PartsAssemble (with_wolf, (long)strlen (with_wolf), AW_PARTS_WEREWOLF_RACE, 0, NULL, NULL, worn, 2, &b));
    assert (b.count == 1 && !strcmp (b.model[0], "progs/parts/0f/0f0f0f0f03.mdl"));
    assert (AW_PartsAssemble (with_wolf, (long)strlen (with_wolf), AW_PARTS_WEREWOLF_RACE, 1, NULL, NULL, NULL, 0, &b));
    assert (b.count == 1 && !strcmp (b.table, "progs/werewolf.awsk"));
    /* the player's own look is as before: his skin under the shirt, his head and hair, the humanoid table */
    assert (AW_PartsAssemble (with_wolf, (long)strlen (with_wolf), "dark elf", 0, NULL, NULL, worn, 1, &b));
    assert (b.count == 4 && !strcmp (b.table, "progs/humanoid.awsk") && !strcmp (b.anm, "progs/parts/hm.anm"));
    /* the robe's own row names no player model (the original's werewolf robe has none for a race's skeleton): worn on
     * the player's own race it changes nothing (what is under it stays), the werewolf look is the engine's step */
    assert (AW_PartsAssemble (with_wolf, (long)strlen (with_wolf), "dark elf", 0, NULL, NULL, worn, 2, &b));
    assert (b.count == 4);
    /* (e) an image without the werewolf's rows: no werewolf body to assemble (the engine keeps the player's own) */
    assert (!AW_PartsAssemble (without_wolf, (long)strlen (without_wolf), AW_PARTS_WEREWOLF_RACE, 0, NULL, NULL, NULL, 0, &b));
    assert (AW_PartsAssemble (without_wolf, (long)strlen (without_wolf), "dark elf", 0, NULL, NULL, worn + 1, 1, &b));
    assert (b.count == 2);
    printf ("without the werewolf rows: none; own body %d parts\n", b.count);
    return 0;
}
