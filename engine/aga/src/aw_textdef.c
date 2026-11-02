/* SPDX-License-Identifier: GPL-2.0-or-later
 * The game's text defines, one getter table (aw_textdef.h; BOOK-TEXT-MACROS-58). */
#include <stdio.h>
#include <string.h>
#include "aw_textdef.h"

/* Getter order = match order: %PCCrimeLevel and the action bindings are tried first, then the list as OpenMW keeps
 * it (a longer name before a shorter one it starts with: pcclass before class, nextpcrank before rank). */
static const char *const names[AW_TD_COUNT] = {
    "pccrimelevel", "nextpcrank", "pcnextrank", "faction", "pcclass", "pcname", "pcrace", "pcrank", "class", "cell",
    "race", "rank", "name",
    "actionslideright", "actionreadymagic", "actionprevweapon", "actionnextweapon", "actiontogglerun",
    "actionslideleft", "actionreadyitem", "actionprevspell", "actionnextspell", "actionrestmenu", "actionmenumode",
    "actionactivate", "actionjournal", "actionforward", "actioncrouch", "actionjump", "actionback", "actionuse",
    "actionrun", "gamehour"
};
/* The action's own word when no key is known (the original's settings names). */
static const char *const action_words[AW_TD_ACTIONS] = {
    "Right", "Ready Magic", "Previous Weapon", "Next Weapon", "Auto Run", "Left", "Ready Weapon", "Previous Spell",
    "Next Spell", "Rest", "Inventory", "Activate", "Journal", "Forward", "Sneak", "Jump", "Back", "Use", "Run"
};

const char *AW_TextDefineName(int id) { return id >= 0 && id < AW_TD_COUNT ? names[id] : NULL; }

static int lower(int c) { return c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c; }
static int prefix(const char *text, const char *name)
{
    int n = 0;
    while (name[n]) { if (lower((unsigned char)text[n]) != name[n]) return 0; n++; }
    return n;
}

int AW_TextDefineMatch(const char *text, int *length)
{
    int k, n;
    if ((n = prefix(text, names[AW_TD_PCCRIMELEVEL])) > 0) { *length = n; return AW_TD_PCCRIMELEVEL; }
    for (k = AW_TD_ACTION_FIRST; k < AW_TD_GAMEHOUR; k++) if ((n = prefix(text, names[k])) > 0) { *length = n; return k; }
    for (k = AW_TD_NEXTPCRANK; k < AW_TD_ACTION_FIRST; k++) if ((n = prefix(text, names[k])) > 0) { *length = n; return k; }
    /* the globals' place in OpenMW's order (no global name starts with "gamehour" in the masters) */
    if ((n = prefix(text, names[AW_TD_GAMEHOUR])) > 0) { *length = n; return AW_TD_GAMEHOUR; }
    *length = 0;
    return -1;
}

static void put(char *out, int capacity, const char *s)
{
    if (capacity <= 0) return;
    if (!s) s = "";
    strncpy(out, s, (size_t)capacity - 1);
    out[capacity - 1] = 0;
}

void AW_TextDefineValue(int id, const aw_textdef_values_t *v, char *out, int capacity)
{
    const char *s = NULL;
    if (capacity <= 0) return;
    out[0] = 0;
    if (!v) return;
    if (id >= AW_TD_ACTION_FIRST && id < AW_TD_GAMEHOUR) {
        s = v->action_key ? v->action_key(id - AW_TD_ACTION_FIRST) : NULL;
        put(out, capacity, s ? s : action_words[id - AW_TD_ACTION_FIRST]);
        return;
    }
    if (id == AW_TD_GAMEHOUR) {
        int length = 0, g;
        if (v->clock) { snprintf(out, (size_t)capacity, "%g", (double)v->game_hour); return; }
        /* no clock (a fixture): the global of that name, as OpenMW reads it */
        if (v->global_prefix && v->global_text && (g = v->global_prefix("GameHour", 8, &length)) >= 0 && length == 8)
            v->global_text(g, out, capacity);
        return;
    }
    switch (id) {
    case AW_TD_PCCRIMELEVEL: snprintf(out, (size_t)capacity, "%d", v->pc_crime); return;
    case AW_TD_PCNAME: s = v->pc_name; break;
    case AW_TD_PCRACE: s = v->pc_race; break;
    case AW_TD_PCCLASS: s = v->pc_class; break;
    case AW_TD_CELL: s = v->cell; break;
    /* outside dialogue: the player's (OpenMW's second getter column) */
    case AW_TD_NAME: s = v->speaker ? v->name : v->pc_name; break;
    case AW_TD_RACE: s = v->speaker ? v->race : v->pc_race; break;
    case AW_TD_CLASS: s = v->speaker ? v->clas : v->pc_class; break;
    /* dialogue only: nothing outside it */
    case AW_TD_FACTION: s = v->speaker ? v->faction : NULL; break;
    case AW_TD_RANK: s = v->speaker ? v->rank : NULL; break;
    case AW_TD_PCRANK: s = v->speaker ? v->pc_rank : NULL; break;
    case AW_TD_NEXTPCRANK: case AW_TD_PCNEXTRANK: s = v->speaker ? v->pc_next_rank : NULL; break;
    default: break;
    }
    put(out, capacity, s);
}

/* The longest global name that TEXT starts with: its number and length, -1 none. */
static int match_global(const aw_textdef_values_t *v, const char *text, int *length)
{
    int run = 0, g;
    while ((text[run] >= 'a' && text[run] <= 'z') || (text[run] >= 'A' && text[run] <= 'Z') ||
           (text[run] >= '0' && text[run] <= '9') || text[run] == '_') run++;
    *length = 0;
    if (!run || !v || !v->global_prefix) return -1;
    g = v->global_prefix(text, run, length);
    if (g < 0 || *length <= 0 || *length > run) { *length = 0; return -1; }
    return g;
}

int AW_TextDefines(char *out, int capacity, const char *p, const aw_textdef_values_t *v)
{
    int n = 0, id, length, g;
    char value[96];
    if (capacity <= 0) return 0;
    while (*p && n < capacity - 1) {
        value[0] = 0;
        id = -1;
        g = -1;
        if ((unsigned char)*p == AW_TEXTDEF_CODE && p[1]) {
            id = (unsigned char)p[1] - 1;
            p += 2;
            if (id < 0 || id >= AW_TD_COUNT) continue;
        } else if ((unsigned char)*p == AW_TEXTDEF_GLOBAL && p[1] && p[2]) {
            g = ((unsigned char)p[1] - 1) * 255 + ((unsigned char)p[2] - 1);
            p += 3;
        } else if ((*p == '%' || *p == '^') && (id = AW_TextDefineMatch(p + 1, &length)) >= 0) {
            p += 1 + length;
        } else if ((*p == '%' || *p == '^') && (g = match_global(v, p + 1, &length)) >= 0) {
            p += 1 + length;
        } else {
            out[n++] = *p++;      /* not a define: as written, the '%' included */
            continue;
        }
        if (id >= 0) AW_TextDefineValue(id, v, value, sizeof(value));
        else if (g >= 0 && v && v->global_text) v->global_text(g, value, sizeof(value));
        {
            const char *s = value;
            while (*s && n < capacity - 1) out[n++] = *s++;
        }
    }
    out[n] = 0;
    return n;
}

#ifndef AW_TEXTDEF_HOST_TEST
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_pcstanding.h"
#include "aw_mwvm.h"
#include "aw_clock.h"
#include "aw_state.h"

/* A written global define (%GameHour) is looked up on disk, nothing kept: the builder codes the defines it knows
 * (AW_TEXTDEF_GLOBAL), so this runs only for a text that was not converted. */
static void global_text(int g, char *out, int capacity)
{
    if (AW_MwscriptGlobalType(g) == 2) snprintf(out, (size_t)capacity, "%g", (double)AW_MwvmGlobalFloat(g));
    else snprintf(out, (size_t)capacity, "%ld", (long)AW_MwvmGlobalInt(g));
}
/* The command each action is bound to (config/keymaps.cfg; the original's action names, action_words above), NULL
 * where the game has no such command yet. */
static const char *const action_commands[AW_TD_ACTIONS] = {
    "+moveright", NULL, NULL, NULL, NULL, "+moveleft", "impulse 202", NULL, NULL, "aw_wait", "aw_inventory",
    "+aw_use", "aw_journal", "+forward", "+aw_sneak", "+jump", "+back", "+attack", "+speed"
};
/* The first key (lowest key number, so a letter before the arrows) bound to the action's command, a single letter in
 * upper case as the original's settings show it; a loop over the 256 bindings, run only for a text holding an action
 * define. */
const char *AW_TextDefineBoundKey(int action)
{
    static char key[16];
    int k;
    const char *name;
    if (action < 0 || action >= AW_TD_ACTIONS || !action_commands[action]) return NULL;
    for (k = 0; k < 256; k++) {
        if (!keybindings[k] || Q_strcasecmp(keybindings[k], (char *)action_commands[action])) continue;
        if (!(name = Key_KeynumToString(k)) || !*name) continue;
        strncpy(key, name, sizeof(key) - 1);
        key[sizeof(key) - 1] = 0;
        if (key[0] >= 'a' && key[0] <= 'z' && !key[1]) key[0] = (char)(key[0] - 'a' + 'A');
        return key;
    }
    return NULL;
}
static char cell_name[64];
void AW_TextDefinesPlayer(aw_textdef_values_t *v)
{
    const char *slash = strrchr(cl.levelname, '/');
    memset(v, 0, sizeof(*v));
    /* the name the player gave (aw_story.name, set at the name step of character creation) */
    v->pc_name = aw_story.name;
    if (aw_character.valid) {
        if (aw_character.race >= 0 && aw_character.race < aw_race_count) v->pc_race = aw_races[aw_character.race].name;
        if (aw_character.clas >= 0 && aw_character.clas < aw_class_count) v->pc_class = aw_classes[aw_character.clas].name;
    }
    v->pc_crime = AW_StandingCrime();
    /* the player's cell: the place name the HUD shows (as the dialogue's %Cell, aw_dialwin.c) */
    strncpy(cell_name, slash ? slash + 1 + (slash[1] == ' ') : cl.levelname, sizeof(cell_name) - 1);
    cell_name[sizeof(cell_name) - 1] = 0;
    v->cell = cell_name;
    v->global_prefix = AW_MwscriptGlobalPrefix;
    v->global_text = global_text;
    v->action_key = AW_TextDefineBoundKey;
    /* %GameHour: the clock's hour of the day (OpenMW's GameHour global follows the clock) */
    v->clock = AW_ClockEnsure();
    v->game_hour = v->clock ? (float)(AW_StateGet(&aw_state, AW_GLOBAL, "amiwind:clock:ms") / 3600000.0) : 0;
}
#endif
