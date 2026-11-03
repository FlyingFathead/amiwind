/* SPDX-License-Identifier: GPL-2.0-or-later
 * The residents' recipe tables per place (BUILD-NPC-RECIPES-PER-CELL-59; engine/aga/src/aw_player_parts.c): the
 * builder's binary tables (tools/npc_recipes.py, written by tests/test_npc_recipes.py into DIR) give every resident of
 * a place the very recipe the one island-wide text table (DIR/global.txt, the earlier form) gave; a table has only
 * its own place's residents; a set of tables loaded and let go again and again holds nothing afterwards (the bytes are
 * the caller's: ASan's leak check sees any that is not freed).
 * DIR/places.txt: one line per place, "<key>\t<id>\t<id>...", the residents placed there. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_player_parts.h"

static unsigned char *slurp (const char *dir, const char *name, long *size)
{
    char path[512];
    FILE *f;
    unsigned char *data;
    snprintf (path, sizeof(path), "%s/%s", dir, name);
    f = fopen (path, "rb");
    assert (f);
    fseek (f, 0, SEEK_END);
    *size = ftell (f);
    fseek (f, 0, SEEK_SET);
    data = malloc ((size_t)*size + 1);
    assert (data && fread (data, 1, (size_t)*size, f) == (size_t)*size);
    data[*size] = 0;
    fclose (f);
    return data;
}

#define PLACES 64
#define IDS 64

int main (int argc, char **argv)
{
    long gsize, psize, bytes;
    char *global, *list, *line, *save = NULL;
    char keys[PLACES][AW_PARTS_ID], ids[PLACES][IDS][AW_PARTS_ID];
    int nids[PLACES], nplaces = 0, p, q, i, round, checked = 0;
    aw_npc_tables_t t;
    aw_parts_npc_t a, b;
    assert (argc == 2);
    global = (char *)slurp (argv[1], "global.txt", &gsize);
    list = (char *)slurp (argv[1], "places.txt", &psize);
    for (line = strtok_r (list, "\n", &save) ; line ; line = strtok_r (NULL, "\n", &save))
    {
        char *word, *s2 = NULL;
        assert (nplaces < PLACES);
        word = strtok_r (line, "\t", &s2);
        strcpy (keys[nplaces], word);
        nids[nplaces] = 0;
        while ((word = strtok_r (NULL, "\t", &s2)) != NULL)
            strcpy (ids[nplaces][nids[nplaces]++], word);
        nplaces++;
    }
    {   /* the resident directory: every resident's place is one that holds it; a narrow load needs only that table */
        long dsize;
        unsigned char *dir = slurp (argv[1], "dir.awnd", &dsize);
        char key[AW_PARTS_ID];
        int cx, cy, total = 0;
        for (p=0 ; p<nplaces ; p++)
            total += nids[p];
        assert (AW_NpcDirCount (dir, dsize) > 0 && AW_NpcDirCount (dir, dsize) <= total);
        for (p=0 ; p<nplaces ; p++)
            for (i=0 ; i<nids[p] ; i++)
            {
                int j, held = 0;
                assert (AW_NpcDirFind (dir, dsize, ids[p][i], key, sizeof(key)));
                for (q=0 ; q<nplaces ; q++)
                    if (!strcmp (keys[q], key))
                        for (j=0 ; j<nids[q] ; j++)
                            held |= !strcmp (ids[q][j], ids[p][i]);
                assert (held);
            }
        assert (!AW_NpcDirFind (dir, dsize, "nobody at all", key, sizeof(key)));
        assert (AW_NpcCellOfKey ("c-2_-9", &cx, &cy) && cx == -2 && cy == -9);
        assert (!AW_NpcCellOfKey ("census_and_excise_office", &cx, &cy) && !AW_NpcCellOfKey ("c1_", &cx, &cy));
        free (dir);
    }
    memset (&t, 0, sizeof(t));
    for (round=0 ; round<3 ; round++)               /* in and out again: no stale entry, nothing kept */
    {
        for (p=0 ; p<nplaces ; p++)
        {
            char name[AW_PARTS_ID + 8];
            unsigned char *data;
            int cx, cy;
            char tail;
            if (sscanf (keys[p], "c%d_%d%c", &cx, &cy, &tail) == 2)
            {   /* a cell: its table out of the cells pack by the pack's index */
                long whole;
                unsigned long at, size;
                unsigned char *pack = slurp (argv[1], "cells.awnp", &whole);
                long index = AW_NpcPackIndexBytes (pack);
                assert (index >= 8 && index <= whole);
                assert (AW_NpcPackFind (pack, index, cx, cy, &at, &size) && at + size <= (unsigned long)whole);
                assert (!AW_NpcPackFind (pack, index, cx + 1000, cy, &at, &size));
                data = malloc (size);
                memcpy (data, pack + at, size);
                bytes = (long)size;
                free (pack);
            }
            else
            {
                snprintf (name, sizeof(name), "%s.awnb", keys[p]);
                data = slurp (argv[1], name, &bytes);
            }
            assert (AW_NpcTableCount (data, bytes) == nids[p]);
            /* each table alone: its own residents with the island-wide recipe, nobody else's */
            for (q=0 ; q<nplaces ; q++)
                for (i=0 ; i<nids[q] ; i++)
                {
                    int own = AW_NpcTableFind (data, bytes, ids[q][i], &b), j, here = 0;
                    for (j=0 ; j<nids[p] ; j++)
                        here |= !strcmp (ids[p][j], ids[q][i]);
                    assert (own == here);
                    if (own)
                    {
                        assert (AW_PartsNpcFind (global, gsize, ids[q][i], &a));
                        assert (!memcmp (&a, &b, sizeof(a)));
                        checked++;
                    }
                }
            assert (AW_NpcTablesAdd (&t, keys[p], data, bytes) == 1);
            assert (AW_NpcTablesAdd (&t, keys[p], data, bytes) == 0);       /* one place held once */
        }
        assert (t.count == nplaces);
        /* the set: the recipe of every resident of the places held */
        for (p=0 ; p<nplaces ; p++)
            for (i=0 ; i<nids[p] ; i++)
                assert (AW_NpcTablesFind (&t, ids[p][i], &b) && AW_PartsNpcFind (global, gsize, ids[p][i], &a) &&
                        !memcmp (&a, &b, sizeof(a)));
        assert (!AW_NpcTablesFind (&t, "nobody at all", &b));
        /* the first place goes: its own residents are found no more unless another held place has them too */
        free (AW_NpcTablesDrop (&t, keys[0], &bytes));
        assert (!AW_NpcTablesHas (&t, keys[0]) && !AW_NpcTablesDrop (&t, keys[0], &bytes));
        for (i=0 ; i<nids[0] ; i++)
        {
            int elsewhere = 0;
            for (p=1 ; p<nplaces ; p++)
                for (q=0 ; q<nids[p] ; q++)
                    elsewhere |= !strcmp (ids[p][q], ids[0][i]);
            assert (AW_NpcTablesFind (&t, ids[0][i], &b) == elsewhere);
        }
        /* a new map: every table goes */
        {
            unsigned char *data;
            while ((data = AW_NpcTablesPop (&t, NULL)) != NULL)
                free (data);
        }
        assert (t.count == 0 && t.bytes == 0);
    }
    {   /* not a table; a full set refuses (the caller keeps the bytes) */
        static unsigned char empty[12] = {'A', 'W', 'N', 'B', 2, 10 + 2 * AW_PARTS_ITEMS, 0, 0, 0, 0, 0, 0};
        char key[AW_PARTS_ID];
        assert (AW_NpcTablesAdd (&t, "c1_1", (unsigned char *)"AWNP1\nN x y 0 - -\n", 18) == 0);
        empty[4] = 1;
        assert (AW_NpcTableCount (empty, 12) == -1);
        empty[4] = 2;
        for (i=0 ; i<AW_NPC_TABLES ; i++)
        {
            AW_NpcTableCellKey (i, 0, key, sizeof(key));
            assert (AW_NpcTablesAdd (&t, key, empty, 12) == 1);
        }
        assert (AW_NpcTablesAdd (&t, "c99_99", empty, 12) == -1 && t.count == AW_NPC_TABLES);
        while (AW_NpcTablesPop (&t, NULL))
            ;
        assert (t.count == 0 && t.bytes == 0);
    }
    free (global);
    free (list);
    printf ("aga_npc_tables_test ok: %d places, %d lookups equal the island-wide table\n", nplaces, checked);
    return 0;
}
