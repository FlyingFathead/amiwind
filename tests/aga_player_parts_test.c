/* SPDX-License-Identifier: GPL-2.0-or-later
 * The assembled player body's recipe (engine/aga/src/aw_player_parts.c, PLAYER-GEAR-VISUAL-59): the race's skin per
 * slot, the chosen or the first head and hair, worn items over them by rank (equal ranks: the first id), a covered
 * slot showing nothing, the beast column, the female column, malformed recipes refused. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_player_parts.h"

static const char *recipe =
    "AWPP1\n"
    "T h progs/humanoid.awsk 59 60\n"
    "T k progs/humanoid_kna.awsk 61 62\n"
    "A h 0 progs/parts/hm.anm\n"
    "A h 1 progs/parts/hf.anm\n"
    "A k 0 progs/parts/km.anm\n"
    "A k 1 progs/parts/km.anm\n"
    "R dark|elf 0 h 1.0000 1.0000\n"
    "S dark|elf 0 3 aaaaaaaaaaa3\n"
    "S dark|elf 0 4 aaaaaaaaaaa4\n"
    "S dark|elf 0 15 aaaaaaaaa015\n"
    "S dark|elf 0 16 aaaaaaaaa016\n"
    "H dark|elf 0 b_n_dark|elf_m_head_01 bbbbbbbbbbb1\n"
    "H dark|elf 0 b_n_dark|elf_m_head_02 bbbbbbbbbbb2\n"
    "K dark|elf 0 b_n_dark|elf_m_hair_01 ccccccccccc1\n"
    "R nord 1 h 1.0600 0.9500\n"
    "S nord 1 3 ddddddddddd3\n"
    "H nord 1 b_n_nord_f_head_01 eeeeeeeeeee1\n"
    "R argonian 0 k 1.1000 1.0000\n"
    "S argonian 0 3 fffffffffff3\n"
    "S argonian 0 26 fffffffff026\n"
    "I common_shirt_01 2 3=111111111111/222222222222,333333333333/444444444444 13=111111111113/-,111111111113/-\n"
    "I iron_cuirass 3 3=555555555555/666666666666,555555555555/666666666666\n"
    "I iron_helmet 3 0=777777777777/888888888888,777777777777/888888888888 1=-,-\n"
    "I extravagant_robe_01 24 3=999999999999/-,999999999999/- 4=-,- 13=-,-\n"
    "I b_shirt 2 3=abababababab/-,abababababab/-\n"
    "I a_shirt 2 3=cdcdcdcdcdcd/-,cdcdcdcdcdcd/-\n";

static int has (const aw_parts_body_t *b, int slot, const char *hex)
{
    int i;
    char path[40];
    if (hex)
        snprintf (path, sizeof(path), "progs/parts/%.2s/%s.mdl", hex, hex + 2);
    for (i=0 ; i<b->count ; i++)
        if (b->slot[i] == slot)
            return hex ? !strcmp (b->model[i], path) : 0;
    return !hex;
}

int main (void)
{
    aw_parts_body_t b;
    const char *none[1] = {NULL};
    const char *shirt[1] = {"common_shirt_01"};
    const char *armour[3] = {"Iron_Cuirass", "Common_Shirt_01", "iron_helmet"};
    const char *robe[2] = {"iron_cuirass", "extravagant_robe_01"};
    const char *ties[2] = {"b_shirt", "a_shirt"};
    long n = (long)strlen (recipe);

    /* the skin and the first head and hair */
    assert (AW_PartsAssemble (recipe, n, "dark elf", 0, NULL, NULL, none, 0, &b));
    assert (!strcmp (b.table, "progs/humanoid.awsk") && b.weapon_bone == 59 && b.shield_bone == 60);
    assert (!strcmp (b.anm, "progs/parts/hm.anm") && b.weight == 1 && b.height == 1 && !b.beast);
    assert (b.count == 6 && has (&b, 0, "bbbbbbbbbbb1") && has (&b, 1, "ccccccccccc1") && has (&b, 3, "aaaaaaaaaaa3"));
    assert (has (&b, 15, "aaaaaaaaa015") && has (&b, 16, "aaaaaaaaa016"));
    /* the chosen head */
    assert (AW_PartsAssemble (recipe, n, "dark elf", 0, "B_N_Dark Elf_M_Head_02", NULL, none, 0, &b));
    assert (has (&b, 0, "bbbbbbbbbbb2"));
    /* a space and '_' are not the same: "dark_elf" is no race here */
    assert (!AW_PartsAssemble (recipe, n, "dark_elf", 0, NULL, NULL, none, 0, &b));
    /* a shirt over the chest skin, its sleeve on a bare slot */
    assert (AW_PartsAssemble (recipe, n, "Dark Elf", 0, NULL, NULL, shirt, 1, &b));
    assert (has (&b, 3, "111111111111") && has (&b, 13, "111111111113") && has (&b, 4, "aaaaaaaaaaa4"));
    /* armour (3) over clothing (2), the helmet hides the hair */
    assert (AW_PartsAssemble (recipe, n, "dark elf", 0, NULL, NULL, armour, 3, &b));
    assert (has (&b, 3, "555555555555") && has (&b, 0, "777777777777") && has (&b, 1, NULL) && has (&b, 13, "111111111113"));
    /* a robe (24) over the cuirass, covering groin and the upper arm with nothing */
    assert (AW_PartsAssemble (recipe, n, "dark elf", 0, NULL, NULL, robe, 2, &b));
    assert (has (&b, 3, "999999999999") && has (&b, 4, NULL) && has (&b, 13, NULL));
    /* equal ranks: the first id wins (mwad.npc.outfit sorts the worn list), whatever the order worn */
    assert (AW_PartsAssemble (recipe, n, "dark elf", 0, NULL, NULL, ties, 2, &b));
    assert (has (&b, 3, "cdcdcdcdcdcd"));
    /* the female column and the race's own scale */
    assert (AW_PartsAssemble (recipe, n, "nord", 1, NULL, NULL, shirt, 1, &b));
    assert (has (&b, 3, "333333333333") && !strcmp (b.anm, "progs/parts/hf.anm"));
    assert (b.weight > 1.059f && b.weight < 1.061f && b.height > .949f && b.height < .951f);
    /* the beast column; a part the beast table lacks shows the skin under it */
    assert (AW_PartsAssemble (recipe, n, "argonian", 0, NULL, NULL, shirt, 1, &b));
    assert (b.beast && !strcmp (b.table, "progs/humanoid_kna.awsk") && b.weapon_bone == 61);
    assert (has (&b, 3, "222222222222") && has (&b, 26, "fffffffff026") && has (&b, 13, NULL));
    assert (AW_PartsAssemble (recipe, n, "argonian", 0, NULL, NULL, robe, 2, &b) && has (&b, 3, "666666666666"));
    /* no such race or sex; malformed recipes */
    assert (!AW_PartsAssemble (recipe, n, "breton", 0, NULL, NULL, none, 0, &b));
    assert (!AW_PartsAssemble (recipe, n, "nord", 0, NULL, NULL, none, 0, &b));
    {
        static const char *bad[3] = {"AWPP2\nR nord 1 h 1 1\n",
                                     "AWPP1\nT h t 1 2\nA h 0 a\nR x 0 h 9.0 1.0\nS x 0 3 aaaaaaaaaaaa\n",
                                     "AWPP1\nT h t 1 2\nA h 0 a\nR x 0 h 1.0 1.0\nS x 0 3 AAAA\n"};
        int i;
        for (i=0 ; i<3 ; i++)
            assert (!AW_PartsAssemble (bad[i], (long)strlen (bad[i]), i ? "x" : "nord", i ? 0 : 1, NULL, NULL, none, 0, &b));
    }
    {
        const char *bad = "AWPP1\nT h t 1 2\nA h 0 a\nR x 0 h 1.0 1.0\nS x 0 3 aaaaaaaaaaaa\nI it 3 3555555555555/-\n";
        const char *it[1] = {"it"};
        assert (!AW_PartsAssemble (bad, (long)strlen (bad), "x", 0, NULL, NULL, it, 1, &b));
    }
    /* the first-person recipe (tools/prepare_player_fp_parts.py): one table for every race, no groups ('-'), the arm
     * skin; a gauntlet takes its hand, a part without a model ('-/-') leaves the skin, a robe's sleeves cover the arms */
    {
        const char *fp =
            "AWPP1\n"
            "T h progs/humanoid_1st.awsk 41 21\n"
            "A h 0 -\n"
            "A h 1 -\n"
            "R khajiit 0 h 1.0000 1.0000\n"
            "S khajiit 0 6 aaaaaaaaaaa6\n"
            "S khajiit 0 7 aaaaaaaaaaa7\n"
            "S khajiit 0 11 aaaaaaaaa011\n"
            "S khajiit 0 13 aaaaaaaaa013\n"
            "I iron_gauntlet_left 3 7=cccccccccccc/-,cccccccccccc/-\n"
            "I common_glove_right_01 2 6=-/-,-/-\n"
            "I common_robe_01 24 3=dddddddddddd/-,dddddddddddd/- 11=-,- 12=-,- 13=-,- 14=-,-\n";
        const char *worn[2] = {"iron_gauntlet_left", "common_glove_right_01"};
        const char *robe1[1] = {"common_robe_01"};
        long m = (long)strlen (fp);
        assert (AW_PartsAssemble (fp, m, "khajiit", 0, NULL, NULL, none, 0, &b));
        assert (!strcmp (b.table, "progs/humanoid_1st.awsk") && b.weapon_bone == 41 && b.shield_bone == 21 && !b.beast);
        assert (b.count == 4 && has (&b, 6, "aaaaaaaaaaa6") && has (&b, 7, "aaaaaaaaaaa7"));
        assert (AW_PartsAssemble (fp, m, "khajiit", 0, NULL, NULL, worn, 2, &b));
        assert (b.count == 4 && has (&b, 7, "cccccccccccc") && has (&b, 6, "aaaaaaaaaaa6"));
        assert (AW_PartsAssemble (fp, m, "khajiit", 0, NULL, NULL, robe1, 1, &b));
        assert (has (&b, 3, "dddddddddddd") && has (&b, 11, NULL) && has (&b, 13, NULL) && has (&b, 6, "aaaaaaaaaaa6"));
        assert (!AW_PartsAssemble (fp, m, "khajiit", 1, NULL, NULL, none, 0, &b));
    }
    /* CRLF line ends read the same */
    {
        const char *crlf = "AWPP1\r\nT h t 1 2\r\nA h 0 a\r\nR x 0 h 1.0 1.0\r\nS x 0 3 aaaaaaaaaaaa\r\n";
        assert (AW_PartsAssemble (crlf, (long)strlen (crlf), "x", 0, NULL, NULL, none, 0, &b) && has (&b, 3, "aaaaaaaaaaaa"));
    }
    puts ("aga_player_parts_test ok");
    return 0;
}
