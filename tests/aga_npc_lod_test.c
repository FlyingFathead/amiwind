/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPC model levels of detail (aw_npc_lod.c): the level table, distance bands with
 * hysteresis, the byte budget (nearest actors first, others step down), the near
 * cap, one load a frame, sharing, and the fallback to the map's own model on every
 * refusal (memory, model slots, frame mismatch, eviction), never an error. */
#include "quakedef.h"
#include "r_local.h"
#include "aw_npc_lod.h"
#include <assert.h>
#include <stdarg.h>

client_state_t cl;
client_static_t cls;
entity_t cl_entities[MAX_EDICTS];
entity_t *cl_visedicts[MAX_VISEDICTS];
int cl_numvisedicts;
vec3_t r_origin, vpn = {1, 0, 0}, vright = {0, -1, 0}, vup = {0, 0, 1};
double realtime;
float xcenter = 160, ycenter = 100, xscale = 160, yscale = 160;
viddef_t vid;
int aw_alias_tris_frame, aw_alias_tris_last;
static char *args[8];
static int arg_count, small_strings;
int Cmd_Argc(void) { return arg_count; }
char *Cmd_Argv(int i) { return i < arg_count ? args[i] : ""; }
void Cvar_Set(char *name, char *value) { (void)name; (void)value; }
void Cvar_SetValue(char *name, float value) { (void)name; (void)value; }
void AW_SmallString(int x, int y, const char *text) { (void)x; (void)y; (void)text; small_strings++; }

static cvar_t *cvars[8];
static int cvar_count;
static model_t world, far_a, far_b, far_c, level_models[3][4];
/* Cache data of every stub model: one aligned alias header (100 triangles) for the labels. */
static struct { aliashdr_t h; mdl_t m; } fake_alias;
static int loads, releases, slots_free = 1, largest = 1 << 20, frames_level = 8, opens;
static const char *manifest =
    "AWNL2 4 0123\n"
    "progs/a_aaaa.mdl 1 5000 4000 3000 2000\n"
    "progs/a_bbbb.mdl 1 5000 4000 3000 0\n"
    "progs/a_cccc.mdl 0 5000 4000 3000 2000\n"
    "progs/a_dddd.mdl 1 5000 4000 3000 2000\n";

void Con_Printf(char *fmt, ...) { (void)fmt; }
static xcommand_t npclod_command;
void Cmd_AddCommand(char *name, xcommand_t f) { if (!strcmp(name, "aw_npclod")) npclod_command = f; }
void Cvar_RegisterVariable(cvar_t *v) { v->value = (float)atof(v->string); cvars[cvar_count++] = v; }
static cvar_t *find(const char *name)
{
    int i;
    for (i = 0; i < cvar_count; i++)
        if (!strcmp(cvars[i]->name, name))
            return cvars[i];
    assert(0);
    return NULL;
}
static void set(const char *name, float value) { find(name)->value = value; }
static void set_string(const char *name, char *value) { find(name)->string = value; }
qboolean Mod_CanFindName(const char *name) { (void)name; return slots_free; }
int Cache_LargestFree(void) { return largest; }
void *Cache_Check(cache_user_t *c) { return c->data; }
static int sizes[4] = {5000, 4000, 3000, 2000};
/* (row 0..2, level) of a level file name; asserts on anything else. */
static void decode(const char *name, int *row, int *level)
{
    assert(!strncmp(name, "progs/l", 7) && name[8] == '/' && !strncmp(name + 9, "a_", 2));
    *level = name[7] - '0';
    *row = name[11] - 'a';
    assert(*level != 1 && *level >= 0 && *level < 4 && *row >= 0 && *row < 3);
}
int COM_FOpenFile(char *name, FILE **file)
{
    byte header[84];
    int row, level;
    *file = tmpfile();
    assert(*file);
    if (!strcmp(name, AW_NPC_LOD_MANIFEST)) {
        fwrite("PAK", 1, 3, *file);         /* a member inside a PAK: start at its offset */
        fwrite(manifest, 1, strlen(manifest), *file);
        fwrite("NEXT MEMBER", 1, 11, *file);
        fseek(*file, 3, SEEK_SET);
        return (int)strlen(manifest);
    }
    decode(name, &row, &level);
    opens++;
    memset(header, 0, sizeof header);
    memcpy(header, "IDPO", 4);
    header[4] = 6;
    header[60] = 0xe0; header[61] = 0x03;       /* 992 vertices */
    header[68] = (byte)frames_level;
    fwrite(header, 1, sizeof header, *file);
    fseek(*file, 0, SEEK_SET);
    return sizes[level];
}
model_t *Mod_ForName(char *name, qboolean crash)
{
    int row, level;
    model_t *m;
    decode(name, &row, &level);
    assert(!crash && slots_free);
    loads++;
    m = &level_models[row][level];
    strcpy(m->name, name);
    m->type = mod_alias;
    m->numframes = frames_level;
    m->cache.data = &fake_alias;
    return m;
}
void Mod_ReleaseAlias(model_t *mod)
{
    assert(mod->cache.data);
    mod->cache.data = NULL;
    releases++;
}

static void cmd(void) { npclod_command(); }
static void model(model_t *m, const char *name)
{
    strcpy(m->name, name);
    m->type = mod_alias;
    m->numframes = 8;
    m->cache.data = &fake_alias;
}
static void place(int i, float x)
{
    cl_entities[i].origin[0] = x;
    cl_entities[i].origin[1] = 0;
    cl_entities[i].origin[2] = 0;
}
static void frame(void)
{
    realtime += 0.05;
    AW_NpcLodFrame();
}
static model_t *drawn(int i) { return AW_NpcLodModel(&cl_entities[i]); }
static model_t *L(int row, int level) { return &level_models[row][level]; }

int main(void)
{
    int i, before, use, bytes[4], resident;
    char far[AW_NPC_LOD_PATH], path[AW_NPC_LOD_PATH];
    float edges[3] = {64, 256, 512};
    /* Rows and paths: strict format. */
    assert(AW_NpcLodParseRow("progs/a.mdl 1 5000 4000 0 2000", far, &use, bytes) && use && bytes[2] == 0);
    assert(!AW_NpcLodParseRow("progs/a.mdl 2 5000 4000 0 2000", far, &use, bytes));
    assert(!AW_NpcLodParseRow("progs/a.mdl 1 5000 4000 0", far, &use, bytes));
    assert(!AW_NpcLodParseRow("progs/a.mdl 1 5000 4000 0 2000 7", far, &use, bytes));
    assert(!AW_NpcLodParseRow("progs/a.mdl 1 5000 0 0 2000", far, &use, bytes));     /* map model needed */
    assert(!AW_NpcLodParseRow("progs/x/a.mdl 1 5000 4000 0 2000", far, &use, bytes));
    assert(!AW_NpcLodParseRow("progs/a.mdl 1 50 4000 0 2000", far, &use, bytes));
    assert(AW_NpcLodLevelPath("progs/a_aaaa.mdl", 0, path, sizeof path) && !strcmp(path, "progs/l0/a_aaaa.mdl"));
    assert(AW_NpcLodLevelPath("progs/a_aaaa.mdl", 1, path, sizeof path) && !strcmp(path, "progs/a_aaaa.mdl"));
    assert(AW_NpcLodLevelPath("progs/a_aaaa.mdl", 3, path, sizeof path) && !strcmp(path, "progs/l3/a_aaaa.mdl"));
    assert(!AW_NpcLodLevelPath("progs/a_aaaa.mdl", 3, path, 19));
    /* Bands: 5 % either side of an edge (10 % hysteresis). */
    assert(AW_NpcLodBand(60, edges, 1) == 0 && AW_NpcLodBand(66, edges, 1) == 1 && AW_NpcLodBand(66, edges, 0) == 0);
    assert(AW_NpcLodBand(68, edges, 0) == 1 && AW_NpcLodBand(62, edges, 1) == 1 && AW_NpcLodBand(60, edges, 1) == 0);
    assert(AW_NpcLodBand(300, edges, 1) == 2 && AW_NpcLodBand(260, edges, 2) == 2 && AW_NpcLodBand(260, edges, 1) == 1);
    assert(AW_NpcLodBand(9000, edges, 0) == 3);

    /* dbg npclod: strict parsing. */
    {
        aw_npclod_cmd_t c;
        const char *a1[] = {"aw_npclod"}, *a2[] = {"aw_npclod", "auto"}, *a3[] = {"aw_npclod", "2"};
        const char *a4[] = {"aw_npclod", "4"}, *a5[] = {"aw_npclod", "target", "0"}, *a6[] = {"aw_npclod", "target", "x"};
        const char *a7[] = {"aw_npclod", "show", "on"}, *a8[] = {"aw_npclod", "show", "maybe"};
        const char *a9[] = {"aw_npclod", "bands", "48", "200", "400"}, *a10[] = {"aw_npclod", "bands", "300", "200", "400"};
        const char *a11[] = {"aw_npclod", "bands", "48", "200"}, *a12[] = {"aw_npclod", "stats"}, *a13[] = {"aw_npclod", "nonsense"};
        const char *a14[] = {"aw_npclod", "show"}, *a15[] = {"aw_npclod", "target", "auto"};
        assert(AW_NpcLodParseCommand(1, a1, &c) && c.kind == AW_NPCLOD_STATS);
        assert(AW_NpcLodParseCommand(2, a2, &c) && c.kind == AW_NPCLOD_FORCE && c.level == -1);
        assert(AW_NpcLodParseCommand(2, a3, &c) && c.kind == AW_NPCLOD_FORCE && c.level == 2);
        assert(!AW_NpcLodParseCommand(2, a4, &c));
        assert(AW_NpcLodParseCommand(3, a5, &c) && c.kind == AW_NPCLOD_TARGET && c.level == 0);
        assert(!AW_NpcLodParseCommand(3, a6, &c));
        assert(AW_NpcLodParseCommand(3, a15, &c) && c.kind == AW_NPCLOD_TARGET && c.level == -1);
        assert(AW_NpcLodParseCommand(3, a7, &c) && c.kind == AW_NPCLOD_SHOW && c.level == 1);
        assert(!AW_NpcLodParseCommand(3, a8, &c));
        assert(AW_NpcLodParseCommand(2, a14, &c) && c.kind == AW_NPCLOD_SHOW && c.level == -1);
        assert(AW_NpcLodParseCommand(5, a9, &c) && c.kind == AW_NPCLOD_BANDS && c.bands[0] == 48 && c.bands[2] == 400);
        assert(!AW_NpcLodParseCommand(5, a10, &c) && !AW_NpcLodParseCommand(4, a11, &c));
        assert(AW_NpcLodParseCommand(2, a12, &c) && c.kind == AW_NPCLOD_STATS);
        assert(!AW_NpcLodParseCommand(2, a13, &c));
    }
    fake_alias.h.model = (int)((byte *)&fake_alias.m - (byte *)&fake_alias.h);
    fake_alias.m.numtris = 100;
    vid.width = 320;
    vid.height = 200;

    AW_NpcLodInit();
    assert(cvar_count == 6);
    /* Defaults the docs give (docs/NPC_MODEL_CACHE.md). */
    assert(find("aw_npc_lod")->value == 1 && find("aw_npc_lod_max")->value == 4);
    assert(find("aw_npc_lod_budget")->value == 1048576 && find("aw_npc_lod_reserve_kib")->value == 512);
    assert(!strcmp(find("aw_npc_lod_bands")->string, "64 256 512") && !strcmp(find("aw_npc_lod_levels")->string, "0123"));
    set("aw_npc_lod_reserve_kib", 0);

    cls.state = ca_connected;
    cl.worldmodel = &world;
    model(&far_a, "progs/a_aaaa.mdl");
    model(&far_b, "progs/a_bbbb.mdl");
    model(&far_c, "progs/a_cccc.mdl");
    cl.model_precache[1] = &world;
    cl.model_precache[2] = &far_a;
    cl.model_precache[3] = &far_b;
    cl.model_precache[4] = &far_c;          /* a_dddd is not on this map: ignored */
    cl.viewentity = 3;
    cl_entities[0].model = &far_a; place(0, 30);
    cl_entities[1].model = &far_b; place(1, 300);
    cl_entities[2].model = &far_c; place(2, 40);   /* level 0 not flagged */
    cl_entities[3].model = &far_a; place(3, 5);    /* the player: never swapped */
    for (i = 0; i < 4; i++) cl_visedicts[i] = &cl_entities[i];
    cl_numvisedicts = 4;

    /* One load a frame, nearest first; an unflagged actor keeps the map model up close. */
    frame();
    assert(loads == 1 && drawn(0) == L(0, 0) && drawn(1) == &far_b && drawn(2) == &far_c && drawn(3) == &far_a);
    frame();
    assert(loads == 2 && drawn(1) == L(1, 2) && AW_NpcLodResident(&resident) == 2 && resident == 5000 + 3000 + 2 * 2048);
    /* Far band: level 3 where the appearance has it, else the resident coarse level. */
    place(1, 700);
    frame();
    assert(drawn(1) == L(1, 2));            /* B has no level 3: keeps level 2 */
    cl_entities[2].model = &far_a; place(2, 700);
    frame();
    frame();
    assert(drawn(2) == L(0, 3));
    /* Same appearance, same band: shared, no load. */
    before = loads;
    place(1, 100);
    cl_entities[1].model = &far_a;
    frame();
    frame();
    assert(loads == before);
    /* Budget: the nearest keeps its level, the others step down. */
    cl_entities[1].model = &far_b; place(1, 300);
    cl_entities[2].model = &far_c; place(2, 600);
    frame();
    set("aw_npc_lod_budget", 5000 + 2048);
    realtime += 3;
    frame();
    frame();
    assert(drawn(0) == L(0, 0) && drawn(1) == &far_b && drawn(2) == &far_c);
    assert(AW_NpcLodResident(&resident) == 1 && resident == 5000 + 2048);
    set("aw_npc_lod_budget", 1048576);
    /* Hysteresis: 66 keeps level 0; 70 is level 1 and level 0 is freed after 2 s. */
    place(0, 66);
    frame();
    assert(drawn(0) == L(0, 0));
    place(0, 70);
    frame();
    assert(drawn(0) == &far_a && L(0, 0)->cache.data);
    realtime += 2.5;
    frame();
    assert(!L(0, 0)->cache.data);
    place(0, 30);

    /* Memory short: refused, map model, retried only after the back-off; no error. */
    largest = 3000;
    for (i = 0; i < 4; i++) frame();
    assert(drawn(0) == &far_a);
    before = opens;
    frame();
    assert(opens == before);
    largest = 1 << 20;
    realtime += 2.5;
    frame();
    assert(drawn(0) == L(0, 0));
    /* Evicted by the Cache: the map model, nothing freed twice; the reserve counts. */
    set("aw_npc_lod_reserve_kib", 512);
    largest = 400 * 1024;
    L(0, 0)->cache.data = NULL;
    before = releases;
    frame();
    assert(drawn(0) == &far_a && releases == before);
    realtime += 2.5;
    frame();
    assert(drawn(0) == &far_a);
    largest = 1 << 20;
    set("aw_npc_lod_reserve_kib", 0);
    /* Model slots full, or a level whose frame list differs: refused. */
    slots_free = 0;
    realtime += 2.5;
    before = loads;
    frame();
    assert(drawn(0) == &far_a && loads == before);
    slots_free = 1;
    frames_level = 9;
    realtime += 2.5;
    frame();
    assert(drawn(0) == &far_a && loads == before);
    frames_level = 8;
    realtime += 2.5;
    frame();
    assert(drawn(0) == L(0, 0));

    /* aw_npc_lod 2: level 0 for every appearance; the near cap holds. */
    place(2, 40);
    set("aw_npc_lod", 2);
    set("aw_npc_lod_max", 1);
    for (i = 0; i < 3; i++) frame();
    assert(drawn(0) == L(0, 0) && drawn(2) == &far_c);
    set("aw_npc_lod_max", 4);
    for (i = 0; i < 3; i++) frame();
    assert(drawn(2) == L(2, 0));
    /* aw_npc_lod_levels: "1" is the map models only (today), "13" skips 0 and 2. */
    set_string("aw_npc_lod_levels", "1");
    for (i = 0; i < 3; i++) frame();
    assert(drawn(0) == &far_a && drawn(1) == &far_b && drawn(2) == &far_c);
    realtime += 3;
    frame();
    assert(AW_NpcLodResident(NULL) == 0);
    set_string("aw_npc_lod_levels", "13");
    place(1, 700);
    cl_entities[1].model = &far_a;
    for (i = 0; i < 3; i++) frame();
    assert(drawn(0) == &far_a && drawn(1) == L(0, 3));
    set_string("aw_npc_lod_levels", "0123");
    /* dbg npclod 2 forces level 2 on everyone (budget and near cap aside); target forces one NPC;
     * show makes a label per visible NPC. */
    arg_count = 2; args[0] = "aw_npclod"; args[1] = "2";
    cmd();
    for (i = 0; i < 4; i++) frame();
    assert(drawn(0) == L(0, 2) && drawn(1) == L(0, 2));
    r_origin[0] = -100;                       /* look along +x from behind every actor */
    arg_count = 3; args[1] = "target"; args[2] = "0";
    cmd();
    for (i = 0; i < 3; i++) frame();
    assert(drawn(1) == L(0, 0) && drawn(0) == L(0, 2));   /* closest to the view line: actor 1 (x 700) */
    arg_count = 3; args[1] = "show"; args[2] = "on";
    cmd();
    frame();
    small_strings = 0;
    AW_NpcLodDrawLabels();
    assert(small_strings > 0);
    arg_count = 2; args[1] = "auto";
    cmd();
    arg_count = 3; args[1] = "target"; args[2] = "auto";
    cmd();
    arg_count = 3; args[1] = "show"; args[2] = "off";
    cmd();
    frame();
    small_strings = 0;
    AW_NpcLodDrawLabels();
    assert(small_strings == 0);
    r_origin[0] = 0;
    /* Off: the map models, every level model freed. */
    set("aw_npc_lod", 0);
    frame();
    assert(AW_NpcLodResident(NULL) == 0 && drawn(1) == &far_a);
    /* A new map: the table is read again for its own precache list. */
    set("aw_npc_lod", 1);
    AW_NpcLodReset();
    assert(drawn(0) == &far_a);
    frame();
    assert(drawn(0) == L(0, 0));
    AW_NpcLodReset();
    assert(AW_NpcLodResident(NULL) == 0 && !L(0, 0)->cache.data);
    puts("NPC LOD level table, bands with hysteresis, byte budget, near cap, one load a frame and fallback passed.");
    return 0;
}
