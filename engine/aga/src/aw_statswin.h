/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_STATSWIN_H
#define AW_STATSWIN_H
/* The Stats window (P, aw_stats) and the Magic window placeholder (O, aw_magicmenu):
 * full-screen windows on the inventory's modal (aw_worldui.c AW_WorldUIOpenPanel).
 * docs/INVENTORY.md "Stats and Magic windows", docs/KEYMAPS.md. */
#define AW_STATS_FACTIONS 8
#define AW_STATS_FACTION_LINES 6   /* name and rank; next rank; its two attributes; the skills; the reputation */
#define AW_STATS_ROWS (32+1+AW_STATS_FACTIONS*AW_STATS_FACTION_LINES+2)
/* FACTION-STATS-PAGE-64: one faction the player belongs to, as the stats page lists it (OpenMW statswindow.cpp:
 * the rank's name or Expelled, and the next rank's needs). need[]: the next rank's attribute 1, attribute 2, one
 * favoured skill, a second favoured skill, the faction reputation; attribute[]: the faction's two attributes (0..7). */
typedef struct {
    char name[32],rank[32],next[32];
    short need[5],reputation;
    unsigned char attribute[2],expelled,has_next;
} aw_stats_faction_t;
typedef struct {
    char name[48],race[48],clas[48],birth[48];
    int level,classed;                  /* classed: major/minor from the class */
    int level_progress,level_total;     /* LEVEL-UP-58: raises toward the next level, of iLevelupTotal (0 = no bar) */
    float current[3],maximum[3];        /* health, magicka, fatigue */
    short attributes[8],base[8];        /* current (base + modifiers - damage) and base */
    short skills[27];
    unsigned char major[5],minor[5];
    /* FACTION-STATS-PAGE-64: filled by aw_stats_standing when the window opens (standing 0: no rows) */
    int standing,reputation,bounty,factions;
    aw_stats_faction_t faction[AW_STATS_FACTIONS];
} aw_stats_sheet_t;
/* Set by the dialogue window (aw_dialwin.c, which has the factions' rank table): fills the standing fields of S
 * from the player's standing, reading the rank names and needs from disk; called once per opening, never per frame. */
extern int (*aw_stats_standing)(aw_stats_sheet_t *s);
/* The live character sheet; 0 when no character exists (the sheet is then empty). */
int AW_StatsSheet(aw_stats_sheet_t *out);
/* The skill list rows: header (-1 major, -2 minor, -3 misc) or a skill index. */
int AW_StatsRows(const aw_stats_sheet_t *s,int *rows);
void AW_StatsDrawSheet(const aw_stats_sheet_t *s,int top);
/* The Magic window: names under Powers / Spells / Magic Items. Without casting (the hooks below NULL) the
 * race's and birthsign's spells by name, Magic Items empty; with casting (PLAYER-CASTING-59, aw_cast.c fills the
 * hooks) the spells and powers the player knows and (SCROLL-CAST-64) the Cast Once and Cast When Used items carried
 * (power 2, kind 2, index: the item's row in the player's item table): Up/Down (or W/S) move the cursor, Enter or a
 * click selects the spell or item to cast, and the footer names the selection. KIND/INDEX: as aw_cast.c selects it. */
typedef struct {int count;char name[32][48];unsigned char power[32];
                int castable,cursor,selected,kind[32],index[32];} aw_magic_list_t;
extern int (*aw_magic_castables)(aw_magic_list_t *out);   /* fills OUT (castable, selected); the count */
extern void (*aw_magic_select)(int kind,int index);
extern int (*aw_magic_status)(char *out,int size);         /* the footer text; 0 none */
int AW_MagicList(aw_magic_list_t *out);
void AW_MagicDrawList(const aw_magic_list_t *list);
/* Opens a full-screen panel on the inventory's modal (aw_worldui.c); 0 when it cannot open. */
int AW_WorldUIOpenPanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void));
/* RC2-SELLUS-NO-TALK-65: the dialogue window's own opener: in play only, never shut by the opening's menu rule */
int AW_WorldUIOpenDialoguePanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void));
/* MAP-MENU-BLOCKED-COURTYARD-65: the same for a window the opening's scripts can switch on (MENU: aw_story.h AW_MENU_*):
 * it opens while the opening restricts the rest once a script enabled it */
int AW_WorldUIOpenMenuPanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void),int menu);
/* set after AW_WorldUIOpenPanel: called with the pointer while the left button is held (a scroll bar's drag);
 * cleared on every close */
extern void (*aw_worldui_panel_drag)(int mouse_x,int mouse_y);
void AW_WorldUIClose(void);   /* the open window closed, as Esc does (ALCHEMY-61: aw_inventory alchemy close) */
void AW_StatsOpen(void);
void AW_MagicMenuOpen(void);
void AW_StatsWindowInit(void);
const char *AW_StatsAttributeName(int i);
const char *AW_StatsSkillName(int i);
#endif
