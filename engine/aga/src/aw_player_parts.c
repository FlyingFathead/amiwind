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

int AW_PartsNpcFind (const char *text, long size, const char *id, aw_parts_npc_t *out)
{
    const char *p, *end, *line_end, *at;
    word_t k, w, sex, head, hair;
    if (!text || size < 6 || !id || !out || memcmp (text, "AWNP1", 5) || (text[5] != '\n' && text[5] != '\r'))
        return 0;
    end = text + size;
    for (p = text ; p < end ; p = line_end + 1)
    {
        line_end = memchr (p, '\n', (size_t)(end - p));
        if (!line_end)
            line_end = end;
        at = p;
        {
            const char *e = line_end > p && line_end[-1] == '\r' ? line_end - 1 : line_end;
            if (!next_word (&at, e, &k) || k.n != 1 || k.p[0] != 'N' || !next_word (&at, e, &w) || !same_id (w, id))
                continue;
            memset (out, 0, sizeof(*out));
            if (!next_word (&at, e, &w) || w.n >= AW_PARTS_ID || !next_word (&at, e, &sex) || sex.n != 1 ||
                (sex.p[0] != '0' && sex.p[0] != '1') || !next_word (&at, e, &head) || head.n >= AW_PARTS_ID ||
                !next_word (&at, e, &hair) || hair.n >= AW_PARTS_ID)
                return 0;
            copy_word (w, out->race, AW_PARTS_ID);
            out->female = sex.p[0] == '1';
            if (!(head.n == 1 && head.p[0] == '-'))
                copy_word (head, out->head, AW_PARTS_ID);
            if (!(hair.n == 1 && hair.p[0] == '-'))
                copy_word (hair, out->hair, AW_PARTS_ID);
            while (next_word (&at, e, &w))
            {
                if (w.n >= AW_PARTS_ID || out->count >= AW_PARTS_ITEMS)
                    return 0;
                copy_word (w, out->items[out->count++], AW_PARTS_ID);
            }
            return 1;
        }
    }
    return 0;
}

/* The residents' recipe tables per place (BUILD-NPC-RECIPES-PER-CELL-59; tools/npc_recipes.py cell_key) */
static char *put_int (char *o, char *end, int v)
{
    char digits[12];
    int n = 0;
    unsigned u = v < 0 ? 0u - (unsigned)v : (unsigned)v;
    if (v < 0 && o < end)
        *o++ = '-';
    do
        digits[n++] = (char)('0' + u % 10);
    while ((u /= 10) && n < 11);
    while (n && o < end)
        *o++ = digits[--n];
    return o;
}

void AW_NpcTableCellKey (int cx, int cy, char *out, int size)
{
    char *o = out, *end = out + size - 1;
    if (size <= 0)
        return;
    if (o < end)
        *o++ = 'c';
    o = put_int (o, end, cx);
    if (o < end)
        *o++ = '_';
    o = put_int (o, end, cy);
    *o = 0;
}

static int table_at (const aw_npc_tables_t *t, const char *key)
{
    int i;
    for (i=0 ; i<t->count ; i++)
        if (!strcmp (t->t[i].key, key))
            return i;
    return -1;
}

int AW_NpcTablesHas (const aw_npc_tables_t *t, const char *key)
{
    return t && key && table_at (t, key) >= 0;
}

static unsigned u16 (const unsigned char *p) {return (unsigned)p[0] << 8 | p[1];}
static unsigned long u32 (const unsigned char *p) {return (unsigned long)u16 (p) << 16 | u16 (p + 2);}

unsigned long AW_NpcIdHash (const char *id)
{
    unsigned long h = 0x811C9DC5UL;
    for ( ; id && *id ; id++)
        h = ((h ^ (unsigned long)(unsigned char)lower ((unsigned char)*id)) * 0x01000193UL) & 0xFFFFFFFFUL;
    return h;
}

long AW_NpcPackIndexBytes (const unsigned char *head)
{
    return head && !memcmp (head, "AWNP", 4) ? 8 + 12L * (long)u16 (head + 4) : -1;
}

static int s16 (const unsigned char *p) {int v = (int)u16 (p); return v >= 0x8000 ? v - 0x10000 : v;}

int AW_NpcPackFind (const unsigned char *index, long size, int cx, int cy, unsigned long *at, unsigned long *bytes)
{
    long lo, hi;
    if (!index || size < 8 || AW_NpcPackIndexBytes (index) != size)
        return 0;
    for (lo = 0, hi = (long)u16 (index + 4) - 1 ; lo <= hi ; )
    {
        long mid = (lo + hi) / 2;
        const unsigned char *e = index + 8 + 12 * mid;
        int x = s16 (e), y = s16 (e + 2);
        if (x == cx && y == cy)
        {
            *at = u32 (e + 4);
            *bytes = u32 (e + 8);
            return 1;
        }
        if (x < cx || (x == cx && y < cy))
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return 0;
}

int AW_NpcDirCount (const unsigned char *data, long size)
{
    long places, count, names, i;
    if (!data || size < 12 || memcmp (data, "AWND", 4))
        return 0;
    places = (long)u16 (data + 4);
    count = (long)u32 (data + 8);
    names = 12 + 6 * count + 2 * places;
    if (count > 0xFFFF || names > size || (places && data[size - 1]))
        return 0;
    for (i=0 ; i<places ; i++)
        if (names + (long)u16 (data + 12 + 6 * count + 2 * i) >= size)
            return 0;
    return (int)count;
}

int AW_NpcDirFind (const unsigned char *data, long size, const char *id, char *key, int keysize)
{
    long lo, hi, count = AW_NpcDirCount (data, size), places;
    unsigned long h;
    if (!count || !id || !key || keysize < 1)
        return 0;
    places = (long)u16 (data + 4);
    h = AW_NpcIdHash (id);
    for (lo = 0, hi = count - 1 ; lo <= hi ; )
    {
        long mid = (lo + hi) / 2;
        const unsigned char *e = data + 12 + 6 * mid;
        if (u32 (e) == h)
        {
            unsigned place = u16 (e + 4);
            const unsigned char *offsets = data + 12 + 6 * count;
            if ((long)place >= places)
                return 0;
            strncpy (key, (const char *)offsets + 2 * places + u16 (offsets + 2 * place), (size_t)keysize - 1);
            key[keysize - 1] = 0;
            return 1;
        }
        if (u32 (e) < h)
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return 0;
}

static int read_int (const char **p, int *out)
{
    int sign = 1, n = 0, digits = 0;
    if (**p == '-')
    {
        sign = -1;
        (*p)++;
    }
    while (**p >= '0' && **p <= '9' && digits < 9)
    {
        n = n * 10 + (*(*p)++ - '0');
        digits++;
    }
    *out = sign * n;
    return digits > 0;
}

int AW_NpcCellOfKey (const char *key, int *cx, int *cy)
{
    const char *p = key;
    if (!p || *p++ != 'c' || !read_int (&p, cx) || *p++ != '_' || !read_int (&p, cy) || *p)
        return 0;
    return 1;
}

/* AWNB version 2 (npc_recipes.table_bytes): 12-byte header, the records, a u16 offset per name, the names */
int AW_NpcTableCount (const unsigned char *data, long size)
{
    long count, names, blob, i;
    if (!data || size < 12 || memcmp (data, "AWNB", 4) || data[4] != 2 || data[5] != AW_NPC_RECORD)
        return -1;
    count = (long)u16 (data + 6);
    names = (long)u16 (data + 8);
    blob = 12 + count * AW_NPC_RECORD + 2 * names;
    if (blob > size || (names && data[size - 1]))
        return -1;
    for (i=0 ; i<names ; i++)
        if (blob + (long)u16 (data + 12 + count * AW_NPC_RECORD + 2 * i) >= size)
            return -1;
    return (int)count;
}

/* name INDEX of a checked table into OUT; 0 when out of range */
static int table_name (const unsigned char *data, unsigned index, char *out)
{
    long count = (long)u16 (data + 6), names = (long)u16 (data + 8), at = 12 + count * AW_NPC_RECORD;
    if ((long)index >= names)
        return 0;
    strncpy (out, (const char *)data + at + 2 * names + u16 (data + at + 2 * index), AW_PARTS_ID - 1);
    out[AW_PARTS_ID - 1] = 0;
    return 1;
}

int AW_NpcTableFind (const unsigned char *data, long size, const char *id, aw_parts_npc_t *out)
{
    long lo, hi, count = AW_NpcTableCount (data, size);
    unsigned long h;
    if (count <= 0 || !id || !out)
        return 0;
    h = AW_NpcIdHash (id);
    for (lo = 0, hi = count - 1 ; lo <= hi ; )
    {
        long mid = (lo + hi) / 2;
        const unsigned char *r = data + 12 + mid * AW_NPC_RECORD;
        unsigned long rh = u32 (r);
        if (rh == h)
        {
            int i, n = r[5];
            unsigned head = u16 (r + 6), hair = u16 (r + 8);
            memset (out, 0, sizeof(*out));
            if (n > AW_PARTS_ITEMS || !table_name (data, r[4] >> 1, out->race) ||
                (head != 0xFFFF && !table_name (data, head, out->head)) ||
                (hair != 0xFFFF && !table_name (data, hair, out->hair)))
                return 0;
            out->female = r[4] & 1;
            for (i=0 ; i<n ; i++)
                if (!table_name (data, u16 (r + 10 + 2 * i), out->items[out->count++]))
                    return 0;
            return 1;
        }
        if (rh < h)
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return 0;
}

int AW_NpcTablesAdd (aw_npc_tables_t *t, const char *key, unsigned char *data, long bytes)
{
    size_t n;
    if (!t || !key || !data || (n = strlen (key)) >= AW_PARTS_ID || table_at (t, key) >= 0 ||
        AW_NpcTableCount (data, bytes) < 0)
        return 0;
    if (t->count >= AW_NPC_TABLES)
        return -1;
    memcpy (t->t[t->count].key, key, n + 1);
    t->t[t->count].data = data;
    t->t[t->count].bytes = bytes;
    t->count++;
    t->bytes += bytes;
    return 1;
}

static unsigned char *drop_at (aw_npc_tables_t *t, int i, long *bytes)
{
    unsigned char *text = t->t[i].data;
    if (bytes)
        *bytes = t->t[i].bytes;
    t->bytes -= t->t[i].bytes;
    t->t[i] = t->t[--t->count];
    memset (&t->t[t->count], 0, sizeof(t->t[t->count]));
    return text;
}

unsigned char *AW_NpcTablesDrop (aw_npc_tables_t *t, const char *key, long *bytes)
{
    int i = t && key ? table_at (t, key) : -1;
    return i < 0 ? NULL : drop_at (t, i, bytes);
}

unsigned char *AW_NpcTablesPop (aw_npc_tables_t *t, long *bytes)
{
    return t && t->count ? drop_at (t, t->count - 1, bytes) : NULL;
}

int AW_NpcTablesFind (const aw_npc_tables_t *t, const char *id, aw_parts_npc_t *out)
{
    int i;
    for (i=0 ; t && i<t->count ; i++)
        if (AW_NpcTableFind (t->t[i].data, t->t[i].bytes, id, out))
            return 1;
    return 0;
}

/* NPC-RECIPES-PER-AREA-59: the shared per-area pack (little-endian) */
static unsigned long le32 (const unsigned char *p)
{
    return (unsigned long)p[0] | (unsigned long)p[1] << 8 | (unsigned long)p[2] << 16 | (unsigned long)p[3] << 24;
}

unsigned long AW_NpcAreaCellKey (int cx, int cy)
{
    return 0x80000000UL | ((unsigned long)((cx + 2048) & 0xFFF) << 12) | (unsigned long)((cy + 2048) & 0xFFF);
}

void AW_NpcAreaKeyName (unsigned long key, char *out, int size)
{
    static const char hex[] = "0123456789abcdef";
    int i;
    if (size < 10)
    {
        if (size > 0)
            out[0] = 0;
        return;
    }
    out[0] = 'a';
    for (i=0 ; i<8 ; i++)
        out[1 + i] = hex[(key >> (28 - 4 * i)) & 15];
    out[9] = 0;
}

int AW_NpcAreaKeyOf (const char *name, unsigned long *key)
{
    unsigned long k = 0;
    int i;
    if (!name || name[0] != 'a')
        return 0;
    for (i=1 ; i<=8 ; i++)
    {
        int c = (unsigned char)name[i], d = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
        if (d < 0)
            return 0;
        k = k << 4 | (unsigned long)d;
    }
    if (name[9])
        return 0;
    *key = k & 0xFFFFFFFFUL;
    return 1;
}

int AW_NpcAreaHead (const unsigned char *head, unsigned long length, unsigned long *areas, unsigned long *dir_at,
                    unsigned long *dir_n)
{
    unsigned long a, at, n;
    if (!head || length < AW_NPC_AREA_HEAD || memcmp (head, "AWR1", 4))
        return 0;
    a = le32 (head + 4);
    at = le32 (head + 8);
    n = le32 (head + 12);
    if (a > 65535 || n > 1048576 || at != AW_NPC_AREA_HEAD + 12 * a || at + 8 * n > length)
        return 0;
    *areas = a;
    *dir_at = at;
    *dir_n = n;
    return 1;
}

int AW_NpcAreaFind (const unsigned char *index, unsigned long areas, unsigned long key, unsigned long *at,
                    unsigned long *bytes, unsigned long *n)
{
    long lo = 0, hi = (long)areas - 1;
    while (index && lo <= hi)
    {
        long mid = (lo + hi) / 2;
        unsigned long k = le32 (index + 12 * mid);
        if (k == key)
        {
            *at = le32 (index + 12 * mid + 4);
            *bytes = le32 (index + 12 * mid + 8);
            if (n)
                *n = (unsigned long)mid;
            return 1;
        }
        if (k < key)
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return 0;
}

long AW_NpcAreaDirFind (const unsigned char *dir, unsigned long n, const char *id)
{
    long lo = 0, hi = (long)n - 1;
    unsigned long h;
    if (!dir || !id)
        return -1;
    h = AW_NpcIdHash (id);
    while (lo <= hi)
    {
        long mid = (lo + hi) / 2;
        unsigned long k = le32 (dir + 8 * mid);
        if (k == h)
            return (long)(dir[8 * mid + 4] | dir[8 * mid + 5] << 8);
        if (k < h)
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return -1;
}

/* tools/player_inventory_pose.py GROUPS: unarmed, then the original's melee weapon types 0..8 */
static const char *const inventory_groups[10] = {
    "inventoryhandtohand", "inventoryshortbladeonehand", "inventoryweapononehand", "inventoryweapontwohand",
    "inventorybluntonehand", "inventoryblunttwohand", "inventoryweapontwowide", "inventoryweapontwowide",
    "inventorybluntonehand", "inventoryblunttwohand"};

int AW_PartsInventoryGroups (int type, const char *out[2], int *show_left)
{
    int two;
    const char *fallback;
    if (type < 0 || type > 8)
        type = -1;
    two = type == 2 || type == 4 || type == 5 || type == 6 || type == 8;
    if (show_left)
        *show_left = !two;
    out[0] = inventory_groups[type + 1];
    out[1] = NULL;
    if (type < 0)
        return 1;
    fallback = two ? "inventoryweapontwohand" : "inventoryweapononehand";
    if (strcmp (fallback, out[0]))
        out[1] = fallback;
    return out[1] ? 2 : 1;
}
