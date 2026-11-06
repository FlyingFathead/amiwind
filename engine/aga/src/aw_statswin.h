/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_STATSWIN_H
#define AW_STATSWIN_H
/* The Stats window (P, aw_stats) and the Magic window placeholder (O, aw_magicmenu):
 * full-screen windows on the inventory's modal (aw_worldui.c AW_WorldUIOpenPanel).
 * docs/INVENTORY.md "Stats and Magic windows", docs/KEYMAPS.md. */
#define AW_STATS_ROWS 32
typedef struct {
    char name[48],race[48],clas[48],birth[48];
    int level,classed;                  /* classed: major/minor from the class */
    int level_progress,level_total;     /* LEVEL-UP-58: raises toward the next level, of iLevelupTotal (0 = no bar) */
    float current[3],maximum[3];        /* health, magicka, fatigue */
    short attributes[8],base[8];        /* current (base + modifiers - damage) and base */
    short skills[27];
    unsigned char major[5],minor[5];
} aw_stats_sheet_t;
/* The live character sheet; 0 when no character exists (the sheet is then empty). */
int AW_StatsSheet(aw_stats_sheet_t *out);
/* The skill list rows: header (-1 major, -2 minor, -3 misc) or a skill index. */
int AW_StatsRows(const aw_stats_sheet_t *s,int *rows);
void AW_StatsDrawSheet(const aw_stats_sheet_t *s,int top);
/* The Magic window: names under Powers / Spells, Magic Items empty. Without casting (the hooks below NULL) the
 * race's and birthsign's spells by name; with casting (PLAYER-CASTING-59, aw_cast.c fills the hooks) the spells and
 * powers the player knows: Up/Down (or W/S) move the cursor, Enter or a click selects the spell to cast, and the
 * footer names the selection with its cost and chance. KIND/INDEX: the spell as aw_cast.c selects it. */
typedef struct {int count;char name[32][48];unsigned char power[32];
                int castable,cursor,selected,kind[32],index[32];} aw_magic_list_t;
extern int (*aw_magic_castables)(aw_magic_list_t *out);   /* fills OUT (castable, selected); the count */
extern void (*aw_magic_select)(int kind,int index);
extern int (*aw_magic_status)(char *out,int size);         /* the footer text; 0 none */
int AW_MagicList(aw_magic_list_t *out);
void AW_MagicDrawList(const aw_magic_list_t *list);
/* Opens a full-screen panel on the inventory's modal (aw_worldui.c); 0 when it cannot open. */
int AW_WorldUIOpenPanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void));
void AW_StatsOpen(void);
void AW_MagicMenuOpen(void);
void AW_StatsWindowInit(void);
const char *AW_StatsAttributeName(int i);
const char *AW_StatsSkillName(int i);
#endif
