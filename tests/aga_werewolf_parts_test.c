/* SPDX-License-Identifier: GPL-2.0-or-later
 * WEREWOLF-BODY-63 (v0.0.68): the werewolf's look swaps the player's assembled body and first-person arms, and lets the
 * previous set go at once both ways, by number (the rule of FP-ARMS-NO-MODEL-SLOT-67: every swap unloads). The real
 * aw_view.c code (its part sets: the body's, the arms', the pending one; part_pin, part_drop, parts_ready,
 * hand_parts_ready, AW_ViewPartsUnload, parts_race_check and the werewolf's look) is cut out of the file by
 * tests/test_werewolf_change.py into view_parts_slice.c and run here on a model table, a cache and two recipes of the
 * test's own: the model table's slots in use, the pinned bytes and the cache's bytes after 50 changes on and off are
 * those before the first change; the werewolf's body and arms are one part each on the werewolf's tables; an image
 * without the werewolf's rows keeps the player's own sets (nothing released, said once). Fails on the old engine: it
 * had no werewolf look (the robe changed nothing).
 * wolffix (v0.0.68, WEREWOLF-BODY-63, WEREWOLF-TABLES-STAY-LOADED-68): (f) the first-person arms asked only while the
 * hands are up, as the engine does (aw_hands.c: no view model while they are put away), by four routes, 30 changes each:
 * the change of form's rule (every item off, the robe worn; back: the robe off, nothing put back on: dbg werewolf, a
 * script's BecomeWerewolf and the console's all run that one rule, aw_mwhost.c were_player_change) with the hands up
 * before the change, with them raised only after it, with them never raised while the form holds, and the robe worn
 * by hand over what is worn: the arms are the werewolf's every time they are asked while the robe is worn and the
 * player's own after every change back; the werewolf's two tables are given back at every change back and loaded again
 * by the next change (the table store's AW_SkelTableRelease, a stand-in here; the store itself is
 * tests/aga_skel_release_test.c); (g) a frame that draws neither set (a torch carried: its baked body and arms) still
 * lets the werewolf's set go at the next frame (were_look_frame, from AW_ViewFrame); (h) a table a loaded model still
 * points into is kept, and given back at the next change back once that model is gone. (g) and the tables fail on the
 * engine before wolffix: the tables were kept for the session and nothing asked while neither set was drawn.
 * wolfnpc (v0.0.68, NPC-WEREWOLF-NO-MODEL-66): (i) the NPCs a script turned are drawn with the player's werewolf set,
 * by the real aw_view.c code (AW_ViewWereNpcSend, AW_ViewWereNpcTable, npc_were_model, npc_were_release and the one
 * count part_pin, part_drop and were_tables_release ask), sent as aw_animkit.c AW_AnimPickPreSend sends them: the set
 * comes in with the first turned NPC on the map and is drawn for exactly the entities named; three NPCs share one model
 * and one table; the player's change back while an NPC is a werewolf keeps the shared body and its table (and gives
 * back the arms' table); an NPC's going while the player is a werewolf keeps his; 50 changes with the player turning
 * too in three orders leave the model table's slots, the pinned bytes, the cache and the tables as before the first;
 * an image without the werewolf's rows keeps the NPCs' own bodies (said once). Fails on the engine before wolfnpc: it
 * had no such code (a turned NPC kept its own body).
 * wolffight (v0.0.68, WEREWOLF-RACE-SCALE-68): (j) the werewolf drawn at the size of the race of the one turned: the
 * player's at his own race's row (read once), each turned NPC at its record's race and sex's (the host's answer, asked
 * once while it is drawn, a crowd at most four a send), forgotten when no send names it; the werewolf's rows carry 1.
 * Fails on the engine before wolffight: every werewolf was drawn at the unit size. */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_player_parts.h"
#include "aw_state.h"
#include "aw_inventory.h"
#include "aw_character.h"
#include "aw_anim.h"
#include "aw_skel.h"

/* ---- the engine's pieces the slice uses, as small stand-ins ---- */
typedef unsigned char byte;
typedef enum {false, true} qboolean;
typedef struct {char *name, *string; qboolean archive, server; float value; void *next;} cvar_t;
typedef struct {int frame;} entity_t;
typedef struct {void *data; int pinned; long bytes;} cache_user_t;
enum {mod_brush, mod_sprite, mod_alias};
typedef struct {int aw_skel; const void *aw_skel_table;} aliashdr_t;
typedef struct {char name[64]; int type, needload; cache_user_t cache; aliashdr_t hdr;} model_t;
#define MODELS 64
static model_t known[MODELS];
int mod_numknown;
unsigned long aw_cache_pinned_bytes, aw_file_finds;
static unsigned long cache_bytes, loads, said_missing, said_npc;
#define MAX_EDICTS 600   /* quakedef.h */
static long part_bytes = 4096;
static const char *recipe_3p, *recipe_1p;
static char filebuf[4096];
int com_filesize;
static aw_skel_table_t table_h, table_h1, table_w, table_w1;
/* the tables' state in the store (WEREWOLF-TABLES-STAY-LOADED-68): held, loads, give-backs */
static struct {const aw_skel_table_t *t; int held, loads, given;} store[4] = {
    {&table_h, 0, 0, 0}, {&table_h1, 0, 0, 0}, {&table_w, 0, 0, 0}, {&table_w1, 0, 0, 0}};
static void store_hold (const aw_skel_table_t *t)
{
    int i;
    for (i=0 ; i<4 ; i++)
        if (store[i].t == t && !store[i].held)
        {
            store[i].held = 1;
            store[i].loads++;
        }
}
aw_character_t aw_character;
aw_race_t aw_races[16];
aw_part_t aw_parts[384];
int aw_race_count, aw_part_count;

int Hunk_LowMark (void) {return 0;}
void Hunk_FreeToLowMark (int mark) {(void)mark;}
double Sys_FloatTime (void) {return 0;}
void Con_Printf (const char *fmt, ...)
{
    char line[512];
    va_list a;
    va_start (a, fmt);
    vsnprintf (line, sizeof(line), fmt, a);
    va_end (a);
    if (strstr (line, "werewolf models are not in this image"))
        said_missing++;
    if (strstr (line, "the turned NPCs keep their own bodies"))
        said_npc++;
}
int Q_strcasecmp (char *a, char *b)
{
    for ( ; *a && *b ; a++, b++)
        if ((*a | 32) != (*b | 32))
            return -1;
    return *a || *b ? -1 : 0;
}
byte *COM_LoadHunkFile (char *path)
{
    const char *text = !strcmp (path, "view/parts.txt") ? recipe_3p : !strcmp (path, "view/parts_1st.txt") ? recipe_1p :
                       strstr (path, ".anm") || strstr (path, "parts_wm") ? "AWAN1\n" : NULL;
    if (!text)
        return NULL;
    com_filesize = (int)strlen (text);
    memcpy (filebuf, text, (size_t)com_filesize + 1);
    return (byte *)filebuf;
}
int AW_AnimParse (aw_anim_t *a, const char *layout, int frames) {(void)layout; (void)frames; memset (a, 0, sizeof(*a)); return 1;}
static const aw_skel_table_t *table_named (const char *name)
{
    if (!strcmp (name, "progs/humanoid.awsk")) return &table_h;
    if (!strcmp (name, "progs/humanoid_1st.awsk")) return &table_h1;
    if (!strcmp (name, "progs/werewolf.awsk")) return &table_w;
    if (!strcmp (name, "progs/werewolf_1st.awsk")) return &table_w1;
    return NULL;
}
const aw_skel_table_t *AW_SkelTableFor (const char *name)
{
    const aw_skel_table_t *t = table_named (name);
    store_hold (t);
    return t;
}
/* the store's give-back (aw_skel_load.c): kept while a model is on it, 0 when not held */
long AW_SkelTableRelease (const char *name, int (*in_use) (const aw_skel_table_t *t))
{
    const aw_skel_table_t *t = table_named (name);
    int i;
    for (i=0 ; i<4 ; i++)
        if (t && store[i].t == t)
        {
            if (!store[i].held)
                return 0;
            if (in_use (t))
                return -1;
            store[i].held = 0;
            store[i].given++;
            return 20000;
        }
    return 0;
}
/* a part's table by its name: a werewolf part (0f..) on the werewolf's tables, the others on the humanoid ones; the
 * first-person parts (their names end in 1) on the first-person tables */
static const aw_skel_table_t *part_table (const char *name)
{
    int wolf = strstr (name, "/0f/") != NULL, first = name[strlen (name) - 5] == '1';
    return wolf ? (first ? &table_w1 : &table_w) : (first ? &table_h1 : &table_h);
}
model_t *Mod_Known (int i) {return &known[i];}
static model_t *find (const char *name)
{
    int i;
    for (i=0 ; i<mod_numknown ; i++)
        if (!strcmp (known[i].name, name))
            return &known[i];
    return NULL;
}
int Mod_CanFindName (char *name)
{
    int i;
    if (find (name) || mod_numknown < MODELS)
        return 1;
    for (i=0 ; i<mod_numknown ; i++)
        if (known[i].needload == 2)
            return 1;
    return 0;
}
model_t *Mod_ForName (char *name, qboolean crash)
{
    model_t *m = find (name);
    int i;
    (void)crash;
    if (!m)
    {
        /* a released slot first (model.c Mod_CanFindName's rule), then a new one */
        for (i=0 ; i<mod_numknown && !m ; i++)
            if (known[i].needload == 2)
                m = &known[i];
        if (!m)
        {
            if (mod_numknown >= MODELS)
                return NULL;
            m = &known[mod_numknown++];
        }
        memset (m, 0, sizeof(*m));
        strcpy (m->name, name);
    }
    if (!m->cache.data)
    {
        m->cache.data = malloc ((size_t)part_bytes);
        m->cache.bytes = part_bytes;
        cache_bytes += (unsigned long)part_bytes;
        loads++;
        aw_file_finds += 3;
    }
    m->type = mod_alias;
    m->needload = 0;
    m->hdr.aw_skel = 1;
    m->hdr.aw_skel_table = part_table (name);
    store_hold (part_table (name));                     /* the loader links the model to its table by its name */
    memcpy (m->cache.data, &m->hdr, sizeof(m->hdr));   /* the header at the start of its cache block, as model.c */
    return m;
}
void *Mod_Extradata (model_t *m) {return m->cache.data;}
void Cache_Pin (cache_user_t *c, int on)
{
    if (on && !c->pinned)
        aw_cache_pinned_bytes += (unsigned long)c->bytes;
    if (!on && c->pinned)
        aw_cache_pinned_bytes -= (unsigned long)c->bytes;
    c->pinned = on != 0;
}
void Mod_ReleaseAlias (model_t *m)
{
    if (m->cache.data)
    {
        free (m->cache.data);
        cache_bytes -= (unsigned long)m->cache.bytes;
    }
    m->cache.data = NULL;
    m->cache.bytes = 0;
    m->needload = 2;
}
static cvar_t parts_cvar = {"aw_player_body_parts", "1", true};

/* ---- the real code ---- */
#include "view_parts_slice.c"

/* ---- the recipes ---- */
/* WEREWOLF-RACE-SCALE-68: the races' own sizes (the dark elf man's 0.95 x 1.02, the Nord man's 1.20 x 1.06, the dark
 * elf woman's 0.90 x 1.00); the werewolf's rows carry 1 */
static const char *body_with =
    "AWPP1\nT h progs/humanoid.awsk 59 60\nT w progs/werewolf.awsk 33 34\nA h 0 progs/parts/hm.anm\n"
    "A w 0 view/parts_wm.txt\nA w 1 view/parts_wm.txt\nR dark|elf 0 h 0.9500 1.0200\nS dark|elf 0 3 aaaaaaaaaaa3\n"
    "S dark|elf 0 4 aaaaaaaaaaa4\nS dark|elf 0 26 aaaaaaaaa026\nR nord 0 h 1.2000 1.0600\nR dark|elf 1 h 0.9000 1.0000\n"
    "R werewolf 0 w 1.0000 1.0000\nR werewolf 1 w 1.0000 1.0000\n"
    "S werewolf 0 3 0f0f0f0f0f03\nS werewolf 1 3 0f0f0f0f0f03\nI werewolfrobe 24 3=-/-,-/-\n";
static const char *arms_with =
    "AWPP1\nT h progs/humanoid_1st.awsk 1 2\nT w progs/werewolf_1st.awsk 1 2\nA h 0 -\nA w 0 -\nA w 1 -\n"
    "R dark|elf 0 h 1.0000 1.0000\nS dark|elf 0 5 aaaaaaaa0051\nS dark|elf 0 6 aaaaaaaa0061\n"
    "R werewolf 0 w 1.0000 1.0000\nR werewolf 1 w 1.0000 1.0000\nS werewolf 0 5 0f0f0f0f0f51\nS werewolf 1 5 0f0f0f0f0f51\n";
static const char *body_without =
    "AWPP1\nT h progs/humanoid.awsk 59 60\nA h 0 progs/parts/hm.anm\nR dark|elf 0 h 1.0000 1.0000\n"
    "S dark|elf 0 3 aaaaaaaaaaa3\nS dark|elf 0 4 aaaaaaaaaaa4\nS dark|elf 0 26 aaaaaaaaa026\nI werewolfrobe 24 3=-/-,-/-\n";
static const char *arms_without =
    "AWPP1\nT h progs/humanoid_1st.awsk 1 2\nA h 0 -\nR dark|elf 0 h 1.0000 1.0000\nS dark|elf 0 5 aaaaaaaa0051\n"
    "S dark|elf 0 6 aaaaaaaa0061\n";

/* one frame of play: AW_ViewFrame's look check first, then what the frame draws: the third-person body (BODY) and the
 * first-person arms (ARMS: only while the hands are up in first person), as aw_view.c and aw_hand_models.c ask them */
static void play (int body, int arms)
{
    were_look_frame ();
    if (body)
        assert (parts_ready ("dark elf", 0) > 0);
    if (arms)
        assert (hand_parts_ready ("dark elf", 0) > 0);
}
static void frame (void) {play (1, 1);}
static void wear (int on)
{
    if (on)
        strcpy (aw_state.inventory.equipped[AW_SLOT_ROBE], AW_PARTS_WEREWOLF_ROBE);
    else
        memset (aw_state.inventory.equipped[AW_SLOT_ROBE], 0, 64);
}
/* the change of form's rule on the slots (aw_were_rules.c AW_WereChange, tests/aga_werewolf_change_test.c): into it
 * every item off and the robe worn; back, the robe off and nothing put back on */
static void change (int on)
{
    if (on)
        memset (aw_state.inventory.equipped, 0, sizeof(aw_state.inventory.equipped));
    wear (on);
}
static int held (const aw_skel_table_t *t) {int i; for (i=0 ; i<4 ; i++) if (store[i].t == t) return store[i].held; return 0;}
/* the arms are the werewolf's (WERE 1) or the player's own (0) */
static void arms_are (int were)
{
    assert (hparts_were == were && hparts.count == (were ? 1 : 2) && hparts_table == (were ? &table_w1 : &table_h1));
    assert (!strcmp (hparts.table, were ? "progs/werewolf_1st.awsk" : "progs/humanoid_1st.awsk"));
    assert (!strcmp (hpart_models[0]->name, were ? "progs/parts/0f/0f0f0f0f51.mdl" : "progs/parts/aa/aaaaaa0051.mdl"));
}
/* NAME holds no slot or a released one (a released slot may already hold the next model) */
static int released (const char *name) {model_t *m = find (name); return !m || (m->needload == 2 && !m->cache.data);}
/* NPC-WEREWOLF-NO-MODEL-66: one server send as aw_animkit.c AW_AnimPickPreSend makes it: the N turned NPCs on the map
 * (ENTITIES) named, the werewolf's table asked at the first, each drawn on it; returns the table (NULL: not drawn) */
static const aw_skel_table_t *npc_send (int n, const int *entities)
{
    const aw_skel_table_t *t = NULL;
    int i, drawn = 1;
    AW_ViewWereNpcSend (0, 0);
    for (i=0 ; i<n ; i++)
    {
        AW_ViewWereNpcSend (1, entities[i]);
        if (drawn && !t && !(t = AW_ViewWereNpcTable ()))
            drawn = 0;
        if (drawn)
            AW_ViewWereNpcSend (2, entities[i]);
    }
    AW_ViewWereNpcSend (3, 0);
    return t;
}
static const int skaal[3] = {40, 41, 77};
#define WOLF_BODY "progs/parts/0f/0f0f0f0f03.mdl"
/* WEREWOLF-RACE-SCALE-68: the script host's answer (aw_mwhost.c actor_race): entity 40 a Nord man, 41 a dark elf woman,
 * 50 to 55 Nord men (a crowd), any other no record; every ask counted */
static int race_asks;
static int test_race (int entity, char *race, int capacity, int *female)
{
    race_asks++;
    if (entity == 40 || (entity >= 50 && entity <= 55))
    {
        snprintf (race, (size_t)capacity, "Nord");
        *female = 0;
        return 1;
    }
    if (entity == 41)
    {
        snprintf (race, (size_t)capacity, "Dark Elf");
        *female = 1;
        return 1;
    }
    return 0;
}
static int near (float a, float b) {return a - b < .001f && b - a < .001f;}

int main (void)
{
    int slots0, part_slots0, slots, part_slots, cycle;
    unsigned long pinned0, cache0, released0;
    table_h.frames = 1000; table_h.bones = 61;
    table_h1.frames = table_w1.frames = HAND_PART_FRAMES * HAND_PART_STANCES; table_h1.bones = table_w1.bones = 40;
    table_w.frames = 1590; table_w.bones = 38;
    parts_cvar.value = player_cache_cvar.value = hand_parts_cvar.value = 1;
    strcpy (aw_races[0].id, "dark elf");
    aw_race_count = 1;
    aw_character.valid = 1;
    aw_character.race = 0;
    aw_character.head = aw_character.hair = -1;
    recipe_3p = body_with;
    recipe_1p = arms_with;
    /* the player's own sets, as before the first change */
    frame ();
    assert (!parts_were && !hparts_were && parts.count == 3 && hparts.count == 2);
    assert (!strcmp (parts.table, "progs/humanoid.awsk") && !strcmp (hparts.table, "progs/humanoid_1st.awsk"));
    slots0 = model_slots_in_use (&part_slots0);
    pinned0 = aw_cache_pinned_bytes;
    cache0 = cache_bytes;
    released0 = parts_released;
    printf ("own: model table %d slots in use (%d player parts), %lu bytes pinned, %lu bytes in the cache\n", slots0,
            part_slots0, pinned0, cache0);
    assert (slots0 == 5 && part_slots0 == 5 && pinned0 == 5 * (unsigned long)part_bytes && cache0 == pinned0);
    /* the robe worn: the werewolf's body and arms, one part each on the werewolf's tables; the five parts of the
     * player's own sets released at once (their slots free, their bytes back) */
    wear (1);
    frame ();
    assert (parts_were && hparts_were && parts.count == 1 && hparts.count == 1);
    assert (!strcmp (parts.table, "progs/werewolf.awsk") && !strcmp (hparts.table, "progs/werewolf_1st.awsk"));
    assert (!strcmp (part_models[0]->name, "progs/parts/0f/0f0f0f0f03.mdl") && parts_table == &table_w);
    assert (released ("progs/parts/aa/aaaaaaaaa3.mdl") && released ("progs/parts/aa/aaaaaa0051.mdl"));
    slots = model_slots_in_use (&part_slots);
    printf ("werewolf: model table %d slots in use (%d player parts), %lu bytes pinned, %lu bytes in the cache, %lu "
            "released\n", slots, part_slots, aw_cache_pinned_bytes, cache_bytes, parts_released - released0);
    assert (slots == 2 && part_slots == 2 && aw_cache_pinned_bytes == 2 * (unsigned long)part_bytes &&
            cache_bytes == aw_cache_pinned_bytes && parts_released - released0 == 5);
    /* taken off: the player's own sets again, the werewolf's two parts released */
    wear (0);
    frame ();
    assert (!parts_were && !hparts_were && parts.count == 3 && hparts.count == 2 && released ("progs/parts/0f/0f0f0f0f03.mdl"));
    /* WEREWOLF-TABLES-STAY-LOADED-68: its two tables given back with its parts, the player's own kept */
    assert (!held (&table_w) && !held (&table_w1) && held (&table_h) && held (&table_h1));
    /* (c) 50 changes on and off: the slots, the pinned bytes and the cache as before the first change */
    for (cycle=0 ; cycle<50 ; cycle++)
    {
        wear (1);
        frame ();
        frame ();
        assert (parts_were && hparts_were && parts.count == 1 && hparts.count == 1);
        assert (held (&table_w) && held (&table_w1));
        wear (0);
        frame ();
        assert (!parts_were && !hparts_were && parts.count == 3 && hparts.count == 2);
        assert (!held (&table_w) && !held (&table_w1));
    }
    slots = model_slots_in_use (&part_slots);
    printf ("after 51 changes on and off: model table %d slots in use (%d player parts), %lu bytes pinned, %lu bytes in "
            "the cache, %d slots ever made, %lu part loads, %lu releases\n", slots, part_slots, aw_cache_pinned_bytes,
            cache_bytes, mod_numknown, loads, parts_released - released0);
    assert (slots == slots0 && part_slots == part_slots0 && aw_cache_pinned_bytes == pinned0 && cache_bytes == cache0);
    assert (mod_numknown <= 7 && parts_released - released0 == 51 * 7 && were_looks == 51);
    assert (store[2].given == 51 && store[2].loads == 51 && store[3].given == 51 && store[3].loads == 51);
    assert (store[0].given == 0 && store[1].given == 0 && were_tables_released == 102);

    /* (f) four routes, 30 changes each, the arms asked only while the hands are up in first person */
    {
        int route, hands_up = 0, w1_loads = store[3].loads, w1_given = store[3].given;
        for (route=0 ; route<4 ; route++)
            for (cycle=0 ; cycle<30 ; cycle++)
            {
                /* the frames before the change: own; the hands up for routes 0 and 3 (the own arms asked) */
                hands_up = route == 0 || route == 3;
                if (route == 3)   /* the robe worn by hand over a shirt: the shirt stays worn */
                    strcpy (aw_state.inventory.equipped[AW_SLOT_SHIRT], "common_shirt_01");
                play (1, hands_up);
                if (hands_up)
                    arms_are (0);
                /* the change: the change of form's rule (routes 0 to 2: dbg werewolf, a script, the console), or the robe
                 * put on by hand (route 3) */
                if (route == 3)
                    wear (1);
                else
                    change (1);
                play (1, hands_up);                     /* route 0 and 3: the arms asked in the change's own frame */
                assert (parts_were && parts.count == 1 && held (&table_w));
                if (hands_up)
                    arms_are (1);
                else
                    assert (!hparts.count && !hparts_table);   /* nothing assembled while the hands are put away */
                if (route == 1)
                {
                    play (1, 0);                        /* third person a while, then the claws readied (F) */
                    play (1, 1);
                    arms_are (1);
                }
                play (1, route != 2);
                if (route != 2)
                    arms_are (1);
                /* the change back: the robe off (route 3: the shirt still worn), the frames after it */
                if (route == 3)
                    wear (0);
                else
                    change (0);
                play (1, 0);
                assert (!parts_were && parts.count == 3 && !hparts.count);
                assert (!held (&table_w) && !held (&table_w1));
                play (1, 1);                             /* the fists readied: the player's own arms */
                arms_are (0);
                if (route == 3)
                    memset (aw_state.inventory.equipped[AW_SLOT_SHIRT], 0, 64);
            }
        play (1, 1);
        slots = model_slots_in_use (&part_slots);
        assert (slots == slots0 && part_slots == part_slots0 && aw_cache_pinned_bytes == pinned0 && cache_bytes == cache0);
        /* the arms' table: loaded and given back in the 90 changes whose claws were readied (route 2 never readied) */
        assert (store[3].loads - w1_loads == 90 && store[3].given - w1_given == 90);
        printf ("(f) 4 routes x 30 changes: the arms the werewolf's on every change, the own after every change back; "
                "model table %d slots in use (%d player parts), %lu bytes pinned\n", slots, part_slots,
                aw_cache_pinned_bytes);
        printf ("the werewolf's tables given back %d times, loaded again %d times (its arms' table %d and %d)\n",
                store[2].given, store[2].loads, store[3].given, store[3].loads);
        assert (store[2].given == 171 && store[2].loads == 171);
    }

    /* (g) a torch carried: neither the assembled body nor the arms from parts are drawn (its baked body and arms), but
     * the robe worn by hand draws the werewolf (no torch on it); the robe taken off: the next frame lets its set go */
    {
        unsigned long before = parts_released;
        wear (1);
        play (1, 1);
        assert (parts_were && hparts_were && held (&table_w) && held (&table_w1));
        wear (0);
        play (0, 0);                                 /* the frame after: the torch's baked body and arms only */
        assert (!parts.count && !hparts.count && !part_models[0] && !hpart_models[0]);
        assert (released ("progs/parts/0f/0f0f0f0f03.mdl") && released ("progs/parts/0f/0f0f0f0f51.mdl"));
        assert (!held (&table_w) && !held (&table_w1) && aw_cache_pinned_bytes == 0);
        assert (parts_released - before == 5 + 2);  /* the own five at the change, the werewolf's two at the next frame */
        printf ("(g) a frame that draws neither set: the werewolf's set let go at the next frame, %lu bytes pinned\n",
                aw_cache_pinned_bytes);
        play (1, 1);                                 /* the torch put away: the own sets again */
        assert (parts.count == 3 && hparts.count == 2 && aw_cache_pinned_bytes == pinned0);
    }

    /* (h) a model still on the werewolf's body table (a turned NPC's, NPC-WEREWOLF-NO-MODEL-66): that table kept at the
     * change back, said; given back at the next change back once the model is gone */
    {
        model_t *npc;
        unsigned long kept = were_tables_kept;
        change (1);
        play (1, 1);
        npc = Mod_ForName ("progs/npcs/0f/0f0f0f0fnp.mdl", false);
        assert (npc && part_table (npc->name) == &table_w);
        change (0);
        play (1, 1);
        assert (were_tables_kept == kept + 1 && held (&table_w) && !held (&table_w1) && !strcmp (were_tables[0], "progs/werewolf.awsk"));
        Mod_ReleaseAlias (npc);
        change (1);
        play (1, 1);
        change (0);
        play (1, 1);
        assert (!held (&table_w) && !held (&table_w1) && !were_tables[0][0] && !were_tables[1][0]);
        printf ("(h) a model still on the werewolf's table: kept once, given back at the next change back\n");
    }

    /* (i) NPC-WEREWOLF-NO-MODEL-66 (wolfnpc): the turned NPCs drawn with the player's werewolf set, one count of who
     * draws it, the last one out releases */
    {
        int slots_a, parts_a, k, kept = (int)were_tables_kept, w1_given;
        unsigned long pinned_a, cache_a, npc_loads;
        const aw_skel_table_t *t;
        model_t *wolf;
        change (0);
        play (1, 1);
        slots_a = model_slots_in_use (&parts_a);
        pinned_a = aw_cache_pinned_bytes;
        cache_a = cache_bytes;
        assert (!held (&table_w) && !held (&table_w1) && slots_a == slots0);
        /* a send with no turned NPC on the map: nothing loaded, nothing drawn */
        assert (!npc_send (0, NULL) && !npc_were.model && !npc_were_model (40) && model_slots_in_use (NULL) == slots_a);
        /* one turned NPC on the map: the werewolf body of the recipe's row on its table, drawn for that entity only */
        t = npc_send (1, skaal);
        wolf = npc_were.model;
        assert (t == &table_w && wolf && !strcmp (wolf->name, WOLF_BODY) && held (&table_w) && !held (&table_w1));
        assert (npc_were_model (40) == wolf && !npc_were_model (41) && !npc_were_model (0) && !npc_were_model (MAX_EDICTS));
        assert (wolf->cache.pinned && model_slots_in_use (NULL) == slots_a + 1 &&
                aw_cache_pinned_bytes == pinned_a + (unsigned long)part_bytes);
        /* three of them (the Skaal hunt): one model and one table for all, nothing more loaded */
        npc_loads = loads;
        assert (npc_send (3, skaal) == &table_w && npc_were.model == wolf && npc_were.count == 3 && loads == npc_loads);
        assert (npc_were_model (40) == wolf && npc_were_model (41) == wolf && npc_were_model (77) == wolf);
        /* UndoWerewolf on one: the others still drawn as the werewolf, that one its own */
        assert (npc_send (2, skaal + 1) == &table_w && !npc_were_model (40) && npc_were_model (41) == wolf);
        /* none on the map any more (the last UndoWerewolf, or the place left): the set let go at once */
        npc_send (0, NULL);
        assert (!npc_were.model && released (WOLF_BODY) && !held (&table_w) && !npc_were_model (41));
        assert (model_slots_in_use (NULL) == slots_a && aw_cache_pinned_bytes == pinned_a && cache_bytes == cache_a);
        printf ("(i) a turned NPC drawn with the werewolf body (%s on progs/werewolf.awsk), three sharing it, let go by "
                "the last one out\n", WOLF_BODY);

        /* the player turns while an NPC is a werewolf: his body is the very same model */
        npc_send (1, skaal);
        change (1);
        play (1, 1);
        assert (parts_were && hparts_were && part_models[0] == npc_were.model && held (&table_w) && held (&table_w1));
        /* his change back while the NPC is a werewolf: the shared body and its table stay (not "kept": the NPC's now),
         * his arms and their table go */
        w1_given = store[3].given;
        change (0);
        play (1, 1);
        npc_send (1, skaal);
        assert (!parts_were && npc_were.model == wolf && !released (WOLF_BODY) && wolf->cache.pinned);
        assert (held (&table_w) && !held (&table_w1) && store[3].given == w1_given + 1 && (int)were_tables_kept == kept);
        assert (released ("progs/parts/0f/0f0f0f0f51.mdl") && npc_were_model (40) == wolf);
        /* the NPC goes too: the last one out releases the body and gives its table back */
        npc_send (0, NULL);
        assert (released (WOLF_BODY) && !held (&table_w) && model_slots_in_use (NULL) == slots_a &&
                aw_cache_pinned_bytes == pinned_a && cache_bytes == cache_a);
        /* the other way round: the player a werewolf first, an NPC comes and goes, his set stays; his change back lets
         * it go */
        change (1);
        play (1, 1);
        assert (npc_send (1, skaal) == &table_w && npc_were.model == part_models[0]);
        npc_send (0, NULL);
        assert (parts_were && !released (WOLF_BODY) && part_models[0]->cache.pinned && held (&table_w));
        change (0);
        play (1, 1);
        assert (released (WOLF_BODY) && !held (&table_w) && !held (&table_w1) && model_slots_in_use (NULL) == slots_a &&
                aw_cache_pinned_bytes == pinned_a && cache_bytes == cache_a && (int)were_tables_kept == kept);
        printf ("(i) the player's change back while an NPC is a werewolf keeps the shared body and its table; the NPC's "
                "going while he is one keeps his\n");

        /* 50 changes with the player turning too, in three orders */
        for (k=0 ; k<50 ; k++)
        {
            switch (k % 3)
            {
            case 0:     /* the NPC first, then the player; the NPC goes, then the player changes back */
                npc_send (2, skaal);
                change (1); play (1, 1); npc_send (2, skaal);
                npc_send (0, NULL);
                change (0); play (1, 1); npc_send (0, NULL);
                break;
            case 1:     /* the player first; the NPCs come; the player back; the NPCs go */
                change (1); play (1, 1); npc_send (0, NULL);
                npc_send (3, skaal);
                change (0); play (1, 1); npc_send (3, skaal);
                assert (npc_were.model && npc_were.model->cache.pinned && held (&table_w) && !held (&table_w1));
                npc_send (0, NULL);
                break;
            default:    /* the NPCs alone, then the player alone */
                npc_send (3, skaal); npc_send (0, NULL);
                change (1); play (1, 1); change (0); play (1, 1);
            }
            assert (released (WOLF_BODY) && !held (&table_w) && !held (&table_w1));
            assert (model_slots_in_use (NULL) == slots_a && aw_cache_pinned_bytes == pinned_a && cache_bytes == cache_a);
        }
        assert ((int)were_tables_kept == kept && npc_were.kept == 0 && !npc_were.failed);
        printf ("(i) 50 changes with the player turning too: model table %d slots in use, %lu bytes pinned, %lu bytes in "
                "the cache, as before; the NPCs' set in %lu times and let go %lu times, no table kept\n",
                model_slots_in_use (NULL), aw_cache_pinned_bytes, cache_bytes, npc_were.loads, npc_were.releases);
        assert (npc_were.loads == npc_were.releases && npc_were.loads >= 50);
    }
    /* (j) WEREWOLF-RACE-SCALE-68 (wolffight): the werewolf drawn at the size of the race of the one turned, as the
     * original scales any character (OpenMW 0.51 mwclass/npc.cpp adjustScale): the werewolf's own rows carry 1, the
     * player's werewolf is drawn at his own race's (the dark elf man's 0.95 x 1.02), each turned NPC at its record's race
     * and sex's (a Nord man 1.20 x 1.06, a dark elf woman 0.90 x 1.00, no record: the unit size), each asked of the host
     * once while it is drawn (a crowd at most 4 a send), forgotten when no send names it. Fails on the engine before: the
     * werewolf was drawn at the unit size for every race (no such code). */
    {
        static const int crowd[6] = {50, 51, 52, 53, 54, 55};
        float w = 0, h = 0;
        int asks;
        change (1);
        play (1, 1);
        assert (parts_were && near (parts.weight, 1) && near (parts.height, 1));   /* the werewolf's row: 1 */
        assert (were_own_scale (&w, &h) && near (w, .95f) && near (h, 1.02f));
        asks = (int)were_own.reads;
        assert (were_own_scale (&w, &h) && (int)were_own.reads == asks);       /* read once, not every frame */
        aw_view_were_race = test_race;
        race_asks = 0;
        assert (npc_send (3, skaal) == &table_w);
        assert (npc_were_scale (40, &w, &h) && near (w, 1.2f) && near (h, 1.06f));
        assert (npc_were_scale (41, &w, &h) && near (w, .9f) && near (h, 1));
        assert (npc_were_scale (77, &w, &h) && near (w, 1) && near (h, 1) && npc_were_scale_unknown >= 1);
        npc_send (3, skaal);
        npc_send (3, skaal);
        assert (race_asks == 3);                                                /* once each while drawn */
        npc_send (2, skaal + 1);                                                /* 40 changed back */
        assert (!npc_were_scale (40, &w, &h) && npc_were_scale (41, &w, &h));
        /* a crowd turned at once: 4 sized at the first send, the other 2 at the next */
        race_asks = 0;
        npc_send (6, crowd);
        assert (race_asks == 4 && npc_were_scale (50, &w, &h) && near (w, 1.2f) && !npc_were_scale (55, &w, &h));
        npc_send (6, crowd);
        assert (race_asks == 6 && npc_were_scale (55, &w, &h) && near (h, 1.06f));
        change (0);
        play (1, 1);
        npc_send (0, NULL);
        assert (!npc_were.model && !npc_were_scale (50, &w, &h) && !npc_were_race_count);
        aw_view_were_race = NULL;
        printf ("(j) the werewolf at the race's size: the player's 0.95 x 1.02 (read once), a Nord man's 1.20 x 1.06, a "
                "dark elf woman's 0.90 x 1.00, no record 1 x 1; a crowd sized 4 a send\n");
    }
    /* a set refused by an image without the werewolf's rows keeps the player's own sets: nothing released, said once */
    AW_ViewPartsUnload ();
    were_rows = -1;
    recipe_3p = body_without;
    recipe_1p = arms_without;
    frame ();
    released0 = parts_released;
    wear (1);
    frame ();
    frame ();
    assert (!parts_were && !hparts_were && parts.count == 3 && hparts.count == 2 && parts_released == released0);
    assert (said_missing == 1 && !were_rows);
    slots = model_slots_in_use (&part_slots);
    assert (slots == slots0 && aw_cache_pinned_bytes == pinned0);
    /* NPC-WEREWOLF-NO-MODEL-66: the turned NPCs keep their own bodies too (said once, not asked again) */
    assert (!npc_send (3, skaal) && !npc_send (3, skaal) && said_npc == 1 && npc_were.failed && !npc_were_model (40));
    assert (model_slots_in_use (NULL) == slots0 && aw_cache_pinned_bytes == pinned0);
    printf ("(e) without the werewolf rows: the own sets stay (%d and %d parts), %lu released, said %lu time\n",
            parts.count, hparts.count, parts_released - released0, said_missing);
    return 0;
}
