/* SPDX-License-Identifier: GPL-2.0-or-later
 * The assembled player body's recipe (aw_player_parts.h). Read line by line from the text, nothing kept: the recipe
 * stays on disk and is read only when the race, the head, the hair or the worn items change (LOOKUP TABLES ON DISK).
 * No sscanf or atof (they pull in the 68040's emulated number parsing); numbers are read digit by digit. */
#include <string.h>
#include "aw_player_parts.h"

typedef struct {const char *p; int n;} word_t;

/* the next space-separated word of the line [*at, end): 0 at the line's end */
static int next_word (const char **at, const char *end, word_t *w)
{
    const char *p = *at;
    while (p < end && *p == ' ')
        p++;
    if (p >= end)
        return 0;
    w->p = p;
    while (p < end && *p != ' ')
        p++;
    w->n = (int)(p - w->p);
    *at = p;
    return 1;
}

static int lower (int c) {return c >= 'A' && c <= 'Z' ? c + 32 : c == ' ' ? '|' : c;}

/* the word equals the id S: case-insensitive, a space written '|' in the recipe (ids hold both "ember hand" and
 * "ember_hand") */
static int same_id (word_t w, const char *s)
{
    int i;
    if (!s)
        return 0;
    for (i=0 ; i<w.n ; i++)
        if (!s[i] || lower ((unsigned char)w.p[i]) != lower ((unsigned char)s[i]))
            return 0;
    return !s[i];
}

static int number (word_t w, int *out)
{
    int i, v = 0;
    if (w.n < 1 || w.n > 6)
        return 0;
    for (i=0 ; i<w.n ; i++)
    {
        if (w.p[i] < '0' || w.p[i] > '9')
            return 0;
        v = v * 10 + (w.p[i] - '0');
    }
    *out = v;
    return 1;
}

/* "1.0600": digits, an optional point and up to 6 fraction digits */
static int decimal (word_t w, float *out)
{
    int i = 0, whole = 0, frac = 0, scale = 1, digits = 0;
    for ( ; i<w.n && w.p[i] != '.' ; i++)
    {
        if (w.p[i] < '0' || w.p[i] > '9' || ++digits > 4)
            return 0;
        whole = whole * 10 + (w.p[i] - '0');
    }
    if (i < w.n)
        for (i++ ; i<w.n ; i++)
        {
            if (w.p[i] < '0' || w.p[i] > '9' || scale >= 1000000)
                return 0;
            frac = frac * 10 + (w.p[i] - '0');
            scale *= 10;
        }
    if (!digits)
        return 0;
    *out = (float)whole + (float)frac / (float)scale;
    return 1;
}

/* a model word: 12 lower-case hex digits */
static int hex12 (word_t w)
{
    int i;
    if (w.n != 12)
        return 0;
    for (i=0 ; i<12 ; i++)
        if (!((w.p[i] >= '0' && w.p[i] <= '9') || (w.p[i] >= 'a' && w.p[i] <= 'f')))
            return 0;
    return 1;
}

static void copy_word (word_t w, char *out, int size)
{
    int n = w.n < size - 1 ? w.n : size - 1;
    memcpy (out, w.p, (size_t)n);
    out[n] = 0;
}

typedef struct {
    char model[13];       /* "" none */
    int rank;
} slot_t;

/* SIDE "<h hex>/<k hex>" or "-" (covered: nothing). Into OUT the column of the skeleton (beast: the k column):
 * 1 = a model, 0 = covered (nothing shows), 2 = no part for this skeleton (what is under it stays), -1 = malformed. */
static int side_model (word_t side, int beast, char out[13])
{
    word_t a, b;
    const char *slash;
    out[0] = 0;
    if (side.n == 1 && side.p[0] == '-')
        return 0;
    slash = memchr (side.p, '/', (size_t)side.n);
    if (!slash)
        return -1;
    a.p = side.p; a.n = (int)(slash - side.p);
    b.p = slash + 1; b.n = side.n - a.n - 1;
    a = beast ? b : a;
    if (a.n == 1 && a.p[0] == '-')
        return 2;
    if (!hex12 (a))
        return -1;
    copy_word (a, out, 13);
    return 1;
}

int AW_PartsAssemble (const char *text, long size, const char *race, int female, const char *head, const char *hair,
                      const char *const *items, int nitems, aw_parts_body_t *out)
{
    const char *p, *end, *line_end;
    word_t w, k, sex, a, b, c;
    slot_t slot[AW_PARTS_SLOTS];
    int have_race = 0, beast = 0, head_done = 0, hair_done = 0, i, n, pass;
    char skeleton = 0;
    /* the worn items in the original's order: rank, then id (mwad.npc.outfit sorts its worn list so) */
    struct {const char *line, *end; int rank; const char *id;} worn[AW_PARTS_ITEMS];
    int worn_count = 0;
    if (!text || size < 6 || !race || !out || memcmp (text, "AWPP1", 5) || (text[5] != '\n' && text[5] != '\r'))
        return 0;
    memset (out, 0, sizeof(*out));
    memset (slot, 0, sizeof(slot));
    out->weapon_bone = out->shield_bone = -1;
    if (nitems > AW_PARTS_ITEMS)
        nitems = AW_PARTS_ITEMS;
    end = text + size;
    /* two passes: the race (its skeleton letter) first, then the rest, which needs it */
    for (pass=0 ; pass<2 ; pass++)
        for (p = text ; p < end ; p = line_end + 1)
        {
            const char *at;
            line_end = memchr (p, '\n', (size_t)(end - p));
            if (!line_end)
                line_end = end;
            at = p;
            if (line_end > p && line_end[-1] == '\r')
                line_end--;
            if (!next_word (&at, line_end, &k) || k.n != 1)
            {
                if (line_end < end && *line_end == '\r')
                    line_end++;
                continue;
            }
            if (pass == 0)
            {
                /* R <race> <0|1> <s> <weight> <height> */
                if (k.p[0] == 'R' && next_word (&at, line_end, &w) && same_id (w, race) && next_word (&at, line_end, &sex) &&
                    sex.n == 1 && sex.p[0] == '0' + (female ? 1 : 0) && next_word (&at, line_end, &a) && a.n == 1 &&
                    (a.p[0] == 'h' || a.p[0] == 'k') && next_word (&at, line_end, &b) && decimal (b, &out->weight) &&
                    next_word (&at, line_end, &c) && decimal (c, &out->height))
                {
                    if (!(out->weight >= .5f && out->weight <= 2 && out->height >= .5f && out->height <= 2))
                        return 0;
                    skeleton = a.p[0];
                    beast = skeleton == 'k';
                    have_race = 1;
                }
            }
            else if (k.p[0] == 'T' || k.p[0] == 'A')
            {
                /* T <s> <table> <weapon bone> <shield bone>; A <s> <0|1> <anm> */
                if (!next_word (&at, line_end, &w) || w.n != 1 || w.p[0] != skeleton)
                    goto next;
                if (k.p[0] == 'T')
                {
                    if (!next_word (&at, line_end, &a) || a.n >= AW_PARTS_PATH || !next_word (&at, line_end, &b) ||
                        !next_word (&at, line_end, &c))
                        return 0;
                    copy_word (a, out->table, AW_PARTS_PATH);
                    if (!number (b, &out->weapon_bone))
                        out->weapon_bone = -1;
                    if (!number (c, &out->shield_bone))
                        out->shield_bone = -1;
                }
                else if (next_word (&at, line_end, &sex) && sex.n == 1 && sex.p[0] == '0' + (female ? 1 : 0))
                {
                    if (!next_word (&at, line_end, &a) || a.n >= (int)sizeof(out->anm))
                        return 0;
                    copy_word (a, out->anm, sizeof(out->anm));
                }
            }
            else if (k.p[0] == 'S' || k.p[0] == 'H' || k.p[0] == 'K')
            {
                int s;
                if (!next_word (&at, line_end, &w) || !same_id (w, race) || !next_word (&at, line_end, &sex) ||
                    sex.n != 1 || sex.p[0] != '0' + (female ? 1 : 0))
                    goto next;
                if (k.p[0] == 'S')
                {
                    if (!next_word (&at, line_end, &a) || !number (a, &s) || s >= AW_PARTS_SLOTS ||
                        !next_word (&at, line_end, &b) || !hex12 (b))
                        return 0;
                    copy_word (b, slot[s].model, 13);
                    slot[s].rank = 1;
                }
                else
                {
                    /* H/K <race> <sex> <body id> <model>: the chosen one, else the first */
                    const char *want = k.p[0] == 'H' ? head : hair;
                    int *done = k.p[0] == 'H' ? &head_done : &hair_done;
                    s = k.p[0] == 'H' ? 0 : 1;
                    if (!next_word (&at, line_end, &a) || !next_word (&at, line_end, &b) || !hex12 (b))
                        return 0;
                    if (*done == 2 || (*done == 1 && !(want && *want && same_id (a, want))))
                        goto next;
                    copy_word (b, slot[s].model, 13);
                    slot[s].rank = 1;
                    *done = want && *want && same_id (a, want) ? 2 : 1;
                }
            }
            else if (k.p[0] == 'I' && worn_count < AW_PARTS_ITEMS)
            {
                /* I <id> <rank> <slot>=<m>,<f> ...: kept for the ordered pass below */
                int rank;
                if (!next_word (&at, line_end, &w) || !next_word (&at, line_end, &a) || !number (a, &rank))
                    goto next;
                for (i=0 ; i<nitems ; i++)
                    if (items[i] && same_id (w, items[i]))
                        break;
                if (i == nitems)
                    goto next;
                worn[worn_count].line = at;
                worn[worn_count].end = line_end;
                worn[worn_count].rank = rank;
                worn[worn_count].id = items[i];
                worn_count++;
            }
        next:
            if (line_end < end && *line_end == '\r')
                line_end++;
            if (pass == 0 && have_race)
                break;
        }
    if (!have_race || !out->table[0] || !out->anm[0])
        return 0;
    /* the worn items, lowest rank first, equal ranks by id; a higher rank takes the slot */
    for (i=1 ; i<worn_count ; i++)
    {
        int j;
        for (j=i ; j>0 ; j--)
        {
            const char *x = worn[j-1].id, *y = worn[j].id;
            int before = worn[j-1].rank < worn[j].rank;
            if (worn[j-1].rank == worn[j].rank)
            {
                while (*x && lower ((unsigned char)*x) == lower ((unsigned char)*y))
                    x++, y++;
                before = lower ((unsigned char)*x) <= lower ((unsigned char)*y);
            }
            if (before)
                break;
            {
                char tmp[sizeof(worn[0])];
                memcpy (tmp, &worn[j], sizeof(worn[0]));
                memcpy (&worn[j], &worn[j-1], sizeof(worn[0]));
                memcpy (&worn[j-1], tmp, sizeof(worn[0]));
            }
        }
    }
    for (i=0 ; i<worn_count ; i++)
    {
        const char *at = worn[i].line;
        while (next_word (&at, worn[i].end, &w))
        {
            /* <slot>=<male side>,<female side> */
            const char *eq = memchr (w.p, '=', (size_t)w.n), *comma;
            word_t s_word, male, fem;
            char model[13];
            int s, r;
            if (!eq)
                return 0;
            s_word.p = w.p; s_word.n = (int)(eq - w.p);
            comma = memchr (eq + 1, ',', (size_t)(w.p + w.n - eq - 1));
            if (!comma || !number (s_word, &s) || s >= AW_PARTS_SLOTS)
                return 0;
            male.p = eq + 1; male.n = (int)(comma - eq - 1);
            fem.p = comma + 1; fem.n = (int)(w.p + w.n - comma - 1);
            if ((r = side_model (female ? fem : male, beast, model)) < 0)
                return 0;
            if (r != 2 && worn[i].rank > slot[s].rank)
            {
                strcpy (slot[s].model, model);
                slot[s].rank = worn[i].rank;
            }
        }
    }
    for (i=0, n=0 ; i<AW_PARTS_SLOTS && n<AW_PARTS_MAX ; i++)
    {
        char path[AW_PARTS_PATH];
        int j, dup = 0;
        if (!slot[i].model[0])
            continue;
        /* progs/parts/<hex 1-2>/<hex 3-12>.mdl (tools/prepare_player_parts.py part_path) */
        memcpy (path, "progs/parts/", 12);
        memcpy (path + 12, slot[i].model, 2);
        path[14] = '/';
        memcpy (path + 15, slot[i].model + 2, 10);
        memcpy (path + 25, ".mdl", 5);
        /* one model drawn once (the key holds the slot, so two slots never name one model; kept as a guard) */
        for (j=0 ; j<n ; j++)
            if (!strcmp (out->model[j], path))
                dup = 1;
        if (dup)
            continue;
        strcpy (out->model[n], path);
        out->slot[n++] = i;
    }
    out->count = n;
    out->beast = beast;
    return n > 0;
}
