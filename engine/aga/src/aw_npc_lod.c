/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPC model levels of detail (docs/NPC_MODEL_CACHE.md "NPC model levels of detail").
 *
 * The builder bakes every resident at up to four levels from the same recipe and
 * frame times: 0 near (the head as authored), 1 the map's own model (precached as
 * always), 2 mid distance and 3 crowds far away. progs/npc-lod.txt lists them per
 * appearance, with the level-0 use flag (the builder's face LOD policy).
 *
 * Each frame the actors are ranked by distance from the view. Each gets the level
 * of its distance band (aw_npc_lod_bands, 10 % hysteresis), stepped down to the
 * next level that fits: the level models (all but the map's own) share a byte
 * budget (aw_npc_lod_budget), nearer actors first, and at most aw_npc_lod_max
 * near models. An actor whose level is not in memory yet is drawn with a coarser
 * level that is, or the map's own model.
 *
 * Quake mechanisms reused: models are model_t entries found by name (Mod_ForName,
 * as the race/sex hand models, aw_hand_models.c); their data lives in the Cache
 * (Mod_TryStreamAlias -> Cache_Alloc, LRU, reloaded by Mod_Extradata). The swap
 * happens where the renderer picks currententity->model (R_DrawEntitiesOnList),
 * so collision, QuakeC, the server's precache list and the entity's frame stay
 * as they were. Software Quake has no frame interpolation: the frame index is the
 * whole animation state, and every level has the same frame list.
 *
 * Memory: a level model is loaded only when the Cache has a free block for it with
 * aw_npc_lod_reserve_kib free beside it, so a load never evicts another cache user
 * (sounds, other actors); at most one load a frame, nearest actor first. A level
 * model nobody planned for 2 s, or whose room the budget needs, is freed. When the
 * Cache evicts one anyway, its actors go back to a resident level. The map's own
 * model is the fallback: every refusal draws it, never an error.
 *
 * cvars: aw_npc_lod 0 off (the map's own model only), 1 level 0 for flagged
 * appearances (default), 2 level 0 for every appearance; aw_npc_lod_bands (band
 * edges 0|1, 1|2, 2|3 in Quake units); aw_npc_lod_levels (levels allowed, for
 * A/B: "1" draws the map's model only); aw_npc_lod_budget (bytes);
 * aw_npc_lod_max (near models at once); aw_npc_lod_reserve_kib.
 * aw_npc_lod_status prints the table, the resident models and the refusals.
 */
#include "quakedef.h"
#include "r_local.h"
#include "aw_npc_lod.h"
#include "aw_rcount.h"

static cvar_t aw_npc_lod = {"aw_npc_lod", "1"};
static cvar_t aw_npc_lod_bands = {"aw_npc_lod_bands", "64 256 512"};
static cvar_t aw_npc_lod_levels = {"aw_npc_lod_levels", "0123"};
static cvar_t aw_npc_lod_budget = {"aw_npc_lod_budget", "1048576"};
static cvar_t aw_npc_lod_max = {"aw_npc_lod_max", "4"};
static cvar_t aw_npc_lod_reserve_kib = {"aw_npc_lod_reserve_kib", "512"};

typedef struct {
    model_t *far;
    int use;
    int bytes[AW_NPC_LOD_LEVELS];
    model_t *model[AW_NPC_LOD_LEVELS];      /* resident level models (never level 1) */
    double idle[AW_NPC_LOD_LEVELS];         /* realtime it was last planned for */
    double retry[AW_NPC_LOD_LEVELS];        /* realtime before which a refused load is not tried */
    unsigned char planned[AW_NPC_LOD_LEVELS];
} lod_row_t;
typedef struct {
    entity_t *ent;
    model_t *model;
    short row;
    signed char band;       /* distance band level (hysteresis state) */
    signed char draw;       /* level drawn this frame */
} lod_track_t;
typedef struct {
    lod_track_t *t;
    float d;
} lod_candidate_t;

static lod_row_t rows[AW_NPC_LOD_ROWS];
static int row_count, table_ready, table_levels, manifest_missing;
static model_t *table_world;
static lod_track_t track_a[AW_NPC_LOD_TRACK], track_b[AW_NPC_LOD_TRACK];
static lod_track_t *track_cur = track_a, *track_prev = track_b;
static int track_valid;
/* dbg npclod (aw_npclod): a level forced on every NPC (-1: the distance bands), a level forced on one
 * entity (the one under the crosshair when it was asked), and the labels. Not saved. */
static int force_all = -1, force_target = -1, show_labels;
static entity_t *target_ent;
extern float xcenter, ycenter, xscale, yscale;
#define AW_NPC_LOD_LABELS 32
typedef struct { int x, y; char text[40]; } lod_label_t;
static lod_label_t labels[AW_NPC_LOD_LABELS];
static int label_count;
/* Events since the map started (aw_npc_lod_status). */
static long n_loads, n_frees, n_budget, n_memory, n_names, n_invalid, n_evicted, n_untracked;

static int token(const char **p, char *out, int size)
{
    int n = 0;
    while (**p == ' ')
        (*p)++;
    while (**p && **p != ' ' && **p != '\n' && **p != '\r') {
        if (n + 1 >= size)
            return 0;
        out[n++] = *(*p)++;
    }
    out[n] = 0;
    return n > 0;
}
static int number(const char *s, int *out)
{
    long v = 0;
    if (!*s)
        return 0;
    for (; *s; s++) {
        if (*s < '0' || *s > '9' || v > 100000000L)
            return 0;
        v = v * 10 + (*s - '0');
    }
    *out = (int)v;
    return 1;
}
int AW_NpcLodParseRow(const char *line, char *far, int *use, int bytes[AW_NPC_LOD_LEVELS])
{
    char field[16];
    const char *p = line;
    int i;
    if (!token(&p, far, AW_NPC_LOD_PATH) || !token(&p, field, sizeof field))
        return 0;
    if (strcmp(field, "0") && strcmp(field, "1"))
        return 0;
    *use = field[0] == '1';
    for (i = 0; i < AW_NPC_LOD_LEVELS; i++)
        if (!token(&p, field, sizeof field) || !number(field, &bytes[i]) || (bytes[i] && bytes[i] < 84))
            return 0;
    while (*p == ' ')
        p++;
    if (*p && *p != '\r' && *p != '\n')     /* nothing after the six fields */
        return 0;
    if (strncmp(far, "progs/", 6) || strchr(far + 6, '/') || strstr(far, "..") || !bytes[AW_NPC_LOD_MAP_LEVEL])
        return 0;
    return 1;
}
int AW_NpcLodLevelPath(const char *far, int level, char *out, int size)
{
    if (level == AW_NPC_LOD_MAP_LEVEL) {
        if ((int)strlen(far) >= size)
            return 0;
        strcpy(out, far);
        return 1;
    }
    if (level < 0 || level >= AW_NPC_LOD_LEVELS || strncmp(far, "progs/", 6) ||
        (int)strlen(far) + 3 >= size)
        return 0;
    sprintf(out, "progs/l%d/%s", level, far + 6);
    return 1;
}
int AW_NpcLodBand(float d, const float edges[AW_NPC_LOD_LEVELS - 1], int previous)
{
    int k, band = 0;
    for (k = 0; k < AW_NPC_LOD_LEVELS - 1; k++)
        if (d > edges[k] * (previous > k ? 0.95f : 1.05f))
            band = k + 1;
    return band;
}

static int owned(lod_row_t *row, int k)
{
    char path[AW_NPC_LOD_PATH];
    model_t *m = row->model[k];
    return m && m->type == mod_alias && AW_NpcLodLevelPath(row->far->name, k, path, sizeof path) &&
           !strcmp(m->name, path);
}
static void release(lod_row_t *row, int k)
{
    if (!row->model[k])
        return;
    if (owned(row, k))
        Mod_ReleaseAlias(row->model[k]);
    row->model[k] = NULL;
    n_frees++;
}
static void release_all(void)
{
    int r, k;
    for (r = 0; r < row_count; r++)
        for (k = 0; k < AW_NPC_LOD_LEVELS; k++)
            release(&rows[r], k);
    track_valid = 0;
}

void AW_NpcLodReset(void)
{
    /* Host_ClearMemory, before Mod_ClearAll: free the level models while their
     * model_t entries are still ours, then forget the map's table. */
    release_all();
    target_ent = NULL;
    force_target = -1;
    label_count = 0;
    row_count = 0;
    table_ready = 0;
    table_world = NULL;
    n_loads = n_frees = n_budget = n_memory = n_names = n_invalid = n_evicted = n_untracked = 0;
}

/* The rows whose map model this map precached. */
static void build_table(void)
{
    FILE *f = NULL;
    int size, i, use, bytes[AW_NPC_LOD_LEVELS];
    char *text, *line, *next, far[AW_NPC_LOD_PATH], *p;
    row_count = 0;
    table_ready = 1;
    table_world = cl.worldmodel;
    table_levels = 0;
    manifest_missing = 0;
    track_valid = 0;
    size = COM_FOpenFile(AW_NPC_LOD_MANIFEST, &f);
    if (!f) {
        manifest_missing = 1;
        return;
    }
    if (size < 8 || size > 256 * 1024 || !(text = malloc(size + 1))) {
        fclose(f);
        return;
    }
    if ((int)fread(text, 1, size, f) != size) {
        fclose(f);
        free(text);
        return;
    }
    fclose(f);
    text[size] = 0;
    line = strchr(text, '\n');
    if (strncmp(text, "AWNL2 ", 6) || !line) {
        Con_Printf("Invalid NPC LOD table; the map's own models only.\n");
        free(text);
        return;
    }
    *line = 0;
    p = strrchr(text, ' ');
    for (p++; *p >= '0' && *p < '0' + AW_NPC_LOD_LEVELS; p++)
        table_levels |= 1 << (*p - '0');
    for (line++; *line; line = next) {
        next = strchr(line, '\n');
        if (next)
            *next++ = 0;
        else
            next = line + strlen(line);
        if (!AW_NpcLodParseRow(line, far, &use, bytes)) {
            Con_Printf("Invalid NPC LOD table row; the map's own models only.\n");
            row_count = 0;
            break;
        }
        for (i = 1; i < MAX_MODELS && cl.model_precache[i]; i++)
            if (cl.model_precache[i]->type == mod_alias && !strcmp(cl.model_precache[i]->name, far))
                break;
        if (i == MAX_MODELS || !cl.model_precache[i])
            continue;
        if (row_count == AW_NPC_LOD_ROWS) {
            Con_Printf("NPC LOD: more than %d appearances on this map; the rest keep their own model.\n",
                       AW_NPC_LOD_ROWS);
            break;
        }
        memset(&rows[row_count], 0, sizeof rows[row_count]);
        rows[row_count].far = cl.model_precache[i];
        rows[row_count].use = use;
        memcpy(rows[row_count].bytes, bytes, sizeof bytes);
        row_count++;
    }
    free(text);
}

static int find_row(model_t *m)
{
    int i;
    for (i = 0; i < row_count; i++)
        if (rows[i].far == m)
            return i;
    return -1;
}
static lod_track_t *track_find(lod_track_t *table, entity_t *e, int insert)
{
    unsigned int h = ((unsigned long)e >> 4) & (AW_NPC_LOD_TRACK - 1), n;
    for (n = 0; n < AW_NPC_LOD_TRACK; n++, h = (h + 1) & (AW_NPC_LOD_TRACK - 1)) {
        if (table[h].ent == e)
            return &table[h];
        if (!table[h].ent) {
            if (!insert)
                return NULL;
            table[h].ent = e;
            return &table[h];
        }
    }
    return NULL;
}

static unsigned int le32(const byte *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) | ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}
static int resident(lod_row_t *row, int k)
{
    return row->model[k] && row->model[k]->cache.data;
}
static int resident_bytes(int *count, int *near)
{
    int r, k, total = 0;
    if (count)
        *count = 0;
    if (near)
        *near = 0;
    for (r = 0; r < row_count; r++)
        for (k = 0; k < AW_NPC_LOD_LEVELS; k++)
            if (k != AW_NPC_LOD_MAP_LEVEL && rows[r].model[k]) {
                total += rows[r].bytes[k] + AW_NPC_LOD_OVERHEAD;
                if (count)
                    (*count)++;
                if (near && !k)
                    (*near)++;
            }
    return total;
}
int AW_NpcLodResident(int *bytes)
{
    int count;
    int total = resident_bytes(&count, NULL);
    if (bytes)
        *bytes = total;
    return count;
}

/* Load row r's level k; 0 with the refusal counted. */
static int admit(lod_row_t *row, int k)
{
    int ok, size, need, reserve;
    FILE *f = NULL;
    byte header[84];
    char path[AW_NPC_LOD_PATH];
    model_t *m;
    if (realtime < row->retry[k])
        return 0;
    row->retry[k] = realtime + 2.0;
    if (row->far->type != mod_alias || row->far->numframes < 1 ||
        !AW_NpcLodLevelPath(row->far->name, k, path, sizeof path)) {
        n_invalid++;
        return 0;
    }
    if (!Mod_CanFindName(path)) {
        n_names++;
        return 0;
    }
    /* The header must agree with the map model (frame count) and the table (bytes). */
    size = COM_FOpenFile(path, &f);
    if (!f) {
        n_invalid++;
        return 0;
    }
    ok = size == row->bytes[k] && fread(header, 1, sizeof header, f) == sizeof header &&
         !memcmp(header, "IDPO", 4) && le32(header + 4) == 6 &&
         (int)le32(header + 68) == row->far->numframes;
    /* Over 2,000 vertices (an original-head near model) loads through model-budgets.txt
     * like every extended model (Mod_LoadModel, AW_AliasExceptionAllows). */
    fclose(f);
    if (!ok) {
        n_invalid++;
        return 0;
    }
    reserve = (int)aw_npc_lod_reserve_kib.value;
    if (reserve < 0)
        reserve = 0;
    need = size + AW_NPC_LOD_OVERHEAD + reserve * 1024;
    if (Cache_LargestFree() < need) {
        n_memory++;
        return 0;
    }
    m = Mod_ForName(path, false);
    if (!m || m->type != mod_alias || strcmp(m->name, path) || m->numframes != row->far->numframes ||
        !m->cache.data) {
        n_invalid++;
        return 0;
    }
    row->model[k] = m;
    row->retry[k] = 0;
    n_loads++;
    return 1;
}

static void parse_bands(float edges[AW_NPC_LOD_LEVELS - 1])
{
    const char *p = aw_npc_lod_bands.string;
    char field[16];
    int i, v;
    float last = 0;
    for (i = 0; i < AW_NPC_LOD_LEVELS - 1; i++) {
        v = 0;
        if (!p || !token(&p, field, sizeof field) || !number(field, &v))
            v = (int)last;
        edges[i] = last = (float)v < last ? last : (float)v;
    }
}
static int allowed_levels(void)
{
    const char *p = aw_npc_lod_levels.string;
    int mask = 1 << AW_NPC_LOD_MAP_LEVEL;
    for (; p && *p; p++)
        if (*p >= '0' && *p < '0' + AW_NPC_LOD_LEVELS)
            mask |= 1 << (*p - '0');
    return mask & (table_levels | 1 << AW_NPC_LOD_MAP_LEVEL);
}

/* Levels to try for a band, finest first; the map's own model always ends the list. */
static int sequence(int band, int out[AW_NPC_LOD_LEVELS])
{
    int n = 0;
    if (band == 0)
        out[n++] = 0;
    else if (band == 2) {
        out[n++] = 2;
        out[n++] = 3;
    } else if (band == 3) {
        out[n++] = 3;
        out[n++] = 2;
    }
    out[n++] = AW_NPC_LOD_MAP_LEVEL;
    return n;
}

static int model_triangles(model_t *m)
{
    aliashdr_t *h;
    if (!m || m->type != mod_alias || !(h = (aliashdr_t *)Cache_Check(&m->cache)))
        return -1;
    return ((mdl_t *)((byte *)h + h->model))->numtris;
}
/* "L<level> <triangles>t <KiB>k" over the actor's head (dbg npclod show). */
static void make_label(lod_track_t *t, float d)
{
    vec3_t local;
    float z, x, y;
    lod_row_t *row = &rows[t->row];
    model_t *m = t->draw == AW_NPC_LOD_MAP_LEVEL ? row->far : row->model[t->draw];
    lod_label_t *l;
    VectorSubtract(t->ent->origin, r_origin, local);
    local[2] += 64;
    z = DotProduct(local, vpn);
    if (z < 8)
        return;
    x = xcenter + xscale * DotProduct(local, vright) / z;
    y = ycenter - yscale * DotProduct(local, vup) / z;
    if (x < 0 || y < 0 || x > vid.width - 8 || y > vid.height - 8)
        return;
    l = &labels[label_count++];
    l->x = (int)x;
    l->y = (int)y;
    snprintf(l->text, sizeof l->text, "L%d %dt %dk %dd", t->draw, model_triangles(m),
             (row->bytes[t->draw] + 512) / 1024, (int)d);
}
void AW_NpcLodDrawLabels(void)
{
    int i, x;
    for (i = 0; i < label_count; i++) {
        x = labels[i].x - (int)strlen(labels[i].text) * 2;
        AW_SmallString(x < 0 ? 0 : x, labels[i].y, labels[i].text);
    }
}

void AW_NpcLodFrame(void)
{
    int i, j, k, r, n, mode, mask, budget, planned_bytes, near_cap, near_planned, count = 0, loaded = 0, forced;
    int seq[AW_NPC_LOD_LEVELS];
    float edges[AW_NPC_LOD_LEVELS - 1], x, y, z;
    lod_candidate_t cand[AW_NPC_LOD_CANDIDATES], swap;
    lod_track_t *t, *old, *tmp;
    lod_row_t *row;
    mode = (int)aw_npc_lod.value;
    if (cls.state != ca_connected || !cl.worldmodel) {
        track_valid = 0;
        return;
    }
    if (!table_ready || table_world != cl.worldmodel) {
        release_all();
        build_table();
    }
    if (mode <= 0 || !row_count) {
        if (row_count)
            release_all();
        return;
    }
    parse_bands(edges);
    mask = allowed_levels();
    budget = (int)aw_npc_lod_budget.value;
    near_cap = (int)aw_npc_lod_max.value;
    /* Level models the Cache evicted: their actors fall back below. */
    for (r = 0; r < row_count; r++)
        for (k = 0; k < AW_NPC_LOD_LEVELS; k++) {
            rows[r].planned[k] = 0;
            if (rows[r].model[k] && (!owned(&rows[r], k) || !Cache_Check(&rows[r].model[k]->cache))) {
                rows[r].model[k] = NULL;    /* evicted (or its slot reused): nothing to free */
                n_evicted++;
            }
        }
    /* This frame's actors, with their previous band. */
    tmp = track_prev;
    track_prev = track_cur;
    track_cur = tmp;
    memset(track_cur, 0, sizeof track_a);
    for (i = 0; i < cl_numvisedicts; i++) {
        entity_t *e = cl_visedicts[i];
        if (!e || !e->model || e->model->type != mod_alias || e == &cl_entities[cl.viewentity])
            continue;
        old = track_valid ? track_find(track_prev, e, 0) : NULL;
        r = old && old->model == e->model ? old->row : find_row(e->model);
        if (r < 0)
            continue;
        t = track_find(track_cur, e, 1);
        if (!t || count == AW_NPC_LOD_CANDIDATES) {
            n_untracked++;
            continue;
        }
        t->model = e->model;
        t->row = (short)r;
        t->band = old && old->model == e->model ? old->band : AW_NPC_LOD_MAP_LEVEL;
        t->draw = AW_NPC_LOD_MAP_LEVEL;
        x = e->origin[0] - r_origin[0];
        y = e->origin[1] - r_origin[1];
        z = e->origin[2] - r_origin[2];
        cand[count].t = t;
        cand[count].d = (float)sqrt(x * x + y * y + z * z);
        count++;
    }
    track_valid = 1;
    aw_alias_tris_last = aw_alias_tris_frame;
    aw_alias_tris_frame = 0;
    for (i = 1; i < count; i++)     /* nearest first (insertion sort: a few dozen actors) */
        for (j = i; j > 0 && cand[j].d < cand[j - 1].d; j--) {
            swap = cand[j];
            cand[j] = cand[j - 1];
            cand[j - 1] = swap;
        }
    /* Plan: each actor's band level, stepped down to what fits the budget, nearest first. */
    planned_bytes = near_planned = 0;
    for (i = 0; i < count; i++) {
        t = cand[i].t;
        row = &rows[t->row];
        t->band = (signed char)AW_NpcLodBand(cand[i].d, edges, t->band);
        forced = t->ent == target_ent && force_target >= 0 ? force_target : force_all;
        n = sequence(forced >= 0 ? forced : t->band, seq);
        for (j = 0; j < n; j++) {
            k = seq[j];
            if (k == AW_NPC_LOD_MAP_LEVEL)
                break;
            if (!(mask & 1 << k) || !row->bytes[k] || (!k && mode == 1 && !row->use))
                continue;
            if (row->planned[k])
                break;
            /* A forced level (dbg npclod) skips the budget and the near cap, not the memory check. */
            if (forced < 0 && (planned_bytes + row->bytes[k] + AW_NPC_LOD_OVERHEAD > budget ||
                               (!k && near_planned >= near_cap))) {
                n_budget++;
                continue;
            }
            row->planned[k] = 1;
            row->idle[k] = realtime;
            planned_bytes += row->bytes[k] + AW_NPC_LOD_OVERHEAD;
            if (!k)
                near_planned++;
            break;
        }
        t->draw = (signed char)k;
    }
    /* Free level models nobody planned for 2 s, and any the budget needs back. */
    for (r = 0; r < row_count; r++)
        for (k = 0; k < AW_NPC_LOD_LEVELS; k++)
            if (rows[r].model[k] && !rows[r].planned[k] && realtime - rows[r].idle[k] > 2.0)
                release(&rows[r], k);
    /* One disk load a frame: the nearest actor whose planned level is not in memory. */
    for (i = 0; i < count && !loaded; i++) {
        t = cand[i].t;
        row = &rows[t->row];
        k = t->draw;
        if (k == AW_NPC_LOD_MAP_LEVEL || resident(row, k) || realtime < row->retry[k])
            continue;       /* in memory, or refused a moment ago: the next actor may load */
        loaded = 1;
        forced = t->ent == target_ent && force_target >= 0 ? force_target : force_all;
        while (forced < 0 && resident_bytes(NULL, NULL) + row->bytes[k] + AW_NPC_LOD_OVERHEAD > budget) {
            int fr = -1, fk = -1;     /* the unplanned model idle the longest */
            for (r = 0; r < row_count; r++)
                for (j = 0; j < AW_NPC_LOD_LEVELS; j++)
                    if (rows[r].model[j] && !rows[r].planned[j] && (fr < 0 || rows[r].idle[j] < rows[fr].idle[fk])) {
                        fr = r;
                        fk = j;
                    }
            if (fr < 0)
                break;
            release(&rows[fr], fk);
        }
        if (forced >= 0 || resident_bytes(NULL, NULL) + row->bytes[k] + AW_NPC_LOD_OVERHEAD <= budget)
            admit(row, k);
        else
            n_budget++;
    }
    /* Draw: the planned level when in memory, else a resident coarse level, else the map's own. */
    for (i = 0; i < count; i++) {
        t = cand[i].t;
        row = &rows[t->row];
        if (t->draw == AW_NPC_LOD_MAP_LEVEL || resident(row, t->draw))
            continue;
        k = t->draw;
        t->draw = AW_NPC_LOD_MAP_LEVEL;
        if (k >= 2) {
            j = k == 2 ? 3 : 2;
            if ((mask & 1 << j) && resident(row, j)) {
                t->draw = (signed char)j;
                row->idle[j] = realtime;
            }
        }
    }
    label_count = 0;
    if (show_labels)
        for (i = 0; i < count && label_count < AW_NPC_LOD_LABELS; i++)
            make_label(cand[i].t, cand[i].d);
}

model_t *AW_NpcLodModel(entity_t *e)
{
    lod_track_t *t;
    lod_row_t *row;
    if (!track_valid || aw_npc_lod.value <= 0)
        return e->model;
    t = track_find(track_cur, e, 0);
    if (!t || t->model != e->model || t->draw == AW_NPC_LOD_MAP_LEVEL)
        return e->model;
    row = &rows[t->row];
    if (!resident(row, t->draw))
        return e->model;
    return row->model[t->draw];
}

int AW_NpcLodParseCommand(int argc, const char **argv, aw_npclod_cmd_t *out)
{
    int i, v;
    memset(out, 0, sizeof *out);
    out->level = -1;
    if (argc < 2 || !strcmp(argv[1], "stats")) {
        out->kind = AW_NPCLOD_STATS;
        return argc <= 2;
    }
    if (!strcmp(argv[1], "auto")) {
        out->kind = AW_NPCLOD_FORCE;
        return argc == 2;
    }
    if (argc == 2 && number(argv[1], &v) && v < AW_NPC_LOD_LEVELS) {
        out->kind = AW_NPCLOD_FORCE;
        out->level = v;
        return 1;
    }
    if (!strcmp(argv[1], "target")) {
        out->kind = AW_NPCLOD_TARGET;
        if (argc == 3 && !strcmp(argv[2], "auto"))
            return 1;
        return argc == 3 && number(argv[2], &out->level) && out->level < AW_NPC_LOD_LEVELS;
    }
    if (!strcmp(argv[1], "show")) {
        out->kind = AW_NPCLOD_SHOW;
        if (argc == 2) {
            out->level = -1;        /* toggle */
            return 1;
        }
        if (argc != 3)
            return 0;
        if (!strcmp(argv[2], "on") || !strcmp(argv[2], "1") || !strcmp(argv[2], "true"))
            out->level = 1;
        else if (!strcmp(argv[2], "off") || !strcmp(argv[2], "0") || !strcmp(argv[2], "false"))
            out->level = 0;
        else
            return 0;
        return 1;
    }
    if (!strcmp(argv[1], "bands")) {
        out->kind = AW_NPCLOD_BANDS;
        if (argc != 2 + AW_NPC_LOD_LEVELS - 1)
            return 0;
        for (i = 0; i < AW_NPC_LOD_LEVELS - 1; i++) {
            if (!number(argv[2 + i], &out->bands[i]) || out->bands[i] > 65535 ||
                (i && out->bands[i] < out->bands[i - 1]))
                return 0;
        }
        return 1;
    }
    out->kind = AW_NPCLOD_NONE;
    return 0;
}

/* The NPC nearest the view direction (within about 6 degrees, 1,024 units): "under the crosshair". */
static entity_t *aimed_npc(void)
{
    int i;
    float best = 0.9945f, d, dot;
    vec3_t v;
    entity_t *found = NULL;
    for (i = 0; i < cl_numvisedicts; i++) {
        entity_t *e = cl_visedicts[i];
        if (!e || !e->model || e->model->type != mod_alias || e == &cl_entities[cl.viewentity] ||
            find_row(e->model) < 0)
            continue;
        VectorSubtract(e->origin, r_origin, v);
        v[2] += 40;
        d = (float)sqrt(DotProduct(v, v));
        if (d < 1 || d > 1024)
            continue;
        dot = DotProduct(v, vpn) / d;
        if (dot > best) {
            best = dot;
            found = e;
        }
    }
    return found;
}
static void stats(void)
{
    int i, have[AW_NPC_LOD_LEVELS] = {0, 0, 0, 0}, bytes, models = AW_NpcLodResident(&bytes);
    lod_track_t *t;
    for (i = 0; i < AW_NPC_LOD_TRACK; i++) {
        t = &track_cur[i];
        if (track_valid && t->ent && t->draw >= 0 && t->draw < AW_NPC_LOD_LEVELS)
            have[t->draw]++;
    }
    Con_Printf("NPC levels in use: L0 %d, L1 %d, L2 %d, L3 %d; %s%s; level models %d, %d bytes of %d; "
               "alias triangles last frame %d\n", have[0], have[1], have[2], have[3],
               force_all >= 0 ? "forced on all" : "distance bands", force_target >= 0 ? " + one target" : "",
               models, bytes, (int)aw_npc_lod_budget.value, aw_alias_tris_last);
}
static void command(void)
{
    const char *argv[8];
    char bands[48];
    int i, argc = Cmd_Argc() > 8 ? 8 : Cmd_Argc();
    aw_npclod_cmd_t c;
    for (i = 0; i < argc; i++)
        argv[i] = Cmd_Argv(i);
    if (!AW_NpcLodParseCommand(argc, argv, &c)) {
        Con_Printf("dbg npclod [auto/0/1/2/3 / target <0..3/auto> / show on/off / bands <d0> <d1> <d2> / stats]\n");
        return;
    }
    if (c.kind != AW_NPCLOD_STATS && aw_npc_lod.value <= 0)
        Cvar_SetValue("aw_npc_lod", 1);
    if (table_ready && !row_count)
        Con_Printf("NPC levels: this map has no level table (a build made without --npc-lod on)\n");
    switch (c.kind) {
    case AW_NPCLOD_FORCE:
        force_all = c.level;
        Con_Printf(c.level < 0 ? "NPC levels: distance bands\n" : "NPC levels: L%d on every NPC\n", c.level);
        break;
    case AW_NPCLOD_TARGET:
        target_ent = c.level < 0 ? NULL : aimed_npc();
        force_target = target_ent ? c.level : -1;
        Con_Printf(target_ent ? "NPC levels: L%d on the NPC under the crosshair\n" :
                   c.level < 0 ? "NPC levels: no target\n" : "NPC levels: no NPC under the crosshair\n", c.level);
        break;
    case AW_NPCLOD_SHOW:
        show_labels = c.level < 0 ? !show_labels : c.level;
        break;
    case AW_NPCLOD_BANDS:
        snprintf(bands, sizeof bands, "%d %d %d", c.bands[0], c.bands[1], c.bands[2]);
        Cvar_Set("aw_npc_lod_bands", bands);
        break;
    default:
        stats();
    }
}

static void status(void)
{
    int r, k, flagged = 0, bytes, count = AW_NpcLodResident(&bytes), have[AW_NPC_LOD_LEVELS] = {0, 0, 0, 0};
    for (r = 0; r < row_count; r++) {
        flagged += rows[r].use;
        for (k = 0; k < AW_NPC_LOD_LEVELS; k++)
            if (rows[r].model[k])
                have[k]++;
    }
    Con_Printf("NPC LOD %s: %d appearances on this map (%d may use level 0)%s, levels %s, bands %s\n",
               aw_npc_lod.value <= 0 ? "off" : aw_npc_lod.value >= 2 ? "level 0 for all" : "level 0 if flagged",
               row_count, flagged, manifest_missing ? ", no table" : "", aw_npc_lod_levels.string,
               aw_npc_lod_bands.string);
    Con_Printf("resident: %d models, %d bytes of %d (level 0: %d, 2: %d, 3: %d; near cap %d)\n", count, bytes,
               (int)aw_npc_lod_budget.value, have[0], have[2], have[3], (int)aw_npc_lod_max.value);
    Con_Printf("loads %ld, freed %ld; stepped down for the budget %ld; refused: memory %ld, model slots %ld, "
               "invalid %ld; evicted %ld; untracked %ld; cache largest free %d\n",
               n_loads, n_frees, n_budget, n_memory, n_names, n_invalid, n_evicted, n_untracked, Cache_LargestFree());
}

void AW_NpcLodInit(void)
{
    Cvar_RegisterVariable(&aw_npc_lod);
    Cvar_RegisterVariable(&aw_npc_lod_bands);
    Cvar_RegisterVariable(&aw_npc_lod_levels);
    Cvar_RegisterVariable(&aw_npc_lod_budget);
    Cvar_RegisterVariable(&aw_npc_lod_max);
    Cvar_RegisterVariable(&aw_npc_lod_reserve_kib);
    Cmd_AddCommand("aw_npc_lod_status", status);
    Cmd_AddCommand("aw_npclod", command);
}
