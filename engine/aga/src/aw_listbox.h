/* SPDX-License-Identifier: GPL-2.0-or-later
 * The console-font list box (v0.0.57, TP-PICKER-57): a box on top of the game with a title, a search field that
 * filters the rows as you type, Up/Down/PgUp/PgDn/Home/End, Enter and the mouse. One component for every debug
 * picker: dbg tp (the settlements, aw_tpplaces.c) first, dbg weapon and dbg gear next (WEAPONS-57).
 *
 * The rules (aw_listbox_rules.c) have no engine dependencies and are host-tested (tests/aga_listbox_test.c);
 * aw_listbox.c shows the box on the world windows' modal (aw_worldui.c AW_WorldUIOpenPanel: the pause, Escape,
 * F10 and the close on a scene change come with it). The rows stay with the caller: the box asks for a row's
 * label when it draws or filters, and keeps only the list of shown row numbers while it is open.
 */
#ifndef AW_LISTBOX_H
#define AW_LISTBOX_H

#define AW_LISTBOX_SEARCH 24

/* abstract keys (aw_listbox.c maps the engine's) */
enum {AW_LBKEY_UP=1,AW_LBKEY_DOWN,AW_LBKEY_PAGEUP,AW_LBKEY_PAGEDOWN,AW_LBKEY_HOME,AW_LBKEY_END,
      AW_LBKEY_BACKSPACE,AW_LBKEY_CHOOSE,AW_LBKEY_CLOSE};
/* what a key did */
enum {AW_LB_NONE=0,AW_LB_CHOSEN=1,AW_LB_CLOSED=2};

typedef const char *(*aw_listbox_label_t)(void *ctx,int row);

typedef struct {
    int count;                      /* the caller's rows */
    aw_listbox_label_t label;
    void *ctx;
    int *shown,shown_count;         /* the rows the search keeps, in the caller's order (caller's buffer, count ints) */
    int selection,top,visible;      /* selection and top index into shown; visible rows on screen */
    char search[AW_LISTBOX_SEARCH+1];
} aw_listbox_t;

void AW_ListBoxReset(aw_listbox_t *b,int count,aw_listbox_label_t label,void *ctx,int *shown,int visible);
/* 1 when LABEL holds SEARCH, letters and digits only, case ignored ("aldruhn" finds "Ald-ruhn"); "" holds all. */
int AW_ListBoxMatches(const char *label,const char *search);
void AW_ListBoxFilter(aw_listbox_t *b);
/* A printable character (32..126) into the search field; 1 when used. */
int AW_ListBoxType(aw_listbox_t *b,int c);
/* An AW_LBKEY_* key; AW_LB_CHOSEN only with a row selected. */
int AW_ListBoxKey(aw_listbox_t *b,int key);
/* A click on visible line LINE (0 = the top row on screen): selects it; AW_LB_CHOSEN when it is a row. */
int AW_ListBoxClick(aw_listbox_t *b,int line);
void AW_ListBoxScroll(aw_listbox_t *b,int top);
void AW_ListBoxSetVisible(aw_listbox_t *b,int visible);
/* The caller's row under the selection; -1 when nothing is shown. */
int AW_ListBoxSelected(const aw_listbox_t *b);

/* The game (aw_listbox.c): open the one box (0 when another is open, the world windows are not allowed now, or
 * there is no memory); CHOSEN runs with the caller's row before the box closes, CLOSED on every close. */
typedef struct {
    const char *title;
    int count;
    aw_listbox_label_t label;
    void *ctx;
    void (*chosen)(void *ctx,int row);
    void (*closed)(void *ctx);
} aw_listbox_spec_t;
int AW_ListBoxOpen(const aw_listbox_spec_t *spec);
int AW_ListBoxActive(void);

/* The settlements table (tools/tp_places_lut.py, AWTP1, id1/tp-places.lut), big-endian: header 16 bytes "AWTP",
 * u16 version 1, u16 row bytes 48, u32 rows, u32 0; rows x 48: name[32] (Latin-1, NUL-padded), i32 x, y, z
 * (original global units: the arrival point), u8 flags (AW_TP_*), u8 named cells, u16 0. Sorted by name. */
#define AW_TP_HEADER 16
#define AW_TP_ROW 48
#define AW_TP_NAME 32
#define AW_TP_HAS_Z 1        /* z is the arrival height (else: the floor at or below the point) */
#define AW_TP_DOOR 2         /* the arrival of a door into the place (on the street) */
#define AW_TP_COC 4          /* the game's own CocMarkerHeading */
typedef struct {char name[AW_TP_NAME];long x,y,z;int flags,cells;} aw_tp_place_t;
/* rows of a table of SIZE bytes (header checked, size exact); -1 when it is no AWTP1 table */
long AW_TpPlacesRows(const unsigned char *data,long size);
/* row I of a checked table into P (the name always ends in a NUL) */
void AW_TpPlacesRow(const unsigned char *data,long i,aw_tp_place_t *p);
/* the console line that takes you there ("aw_teleport X Y [Z]\n"), the existing coordinate path; length or -1 */
int AW_TpPlacesCommand(const aw_tp_place_t *p,char *out,int size);

/* dbg tp with no argument (aw_tpplaces.c): the settlements box from id1/tp-places.lut, read when it opens and
 * freed when it closes; 0 when the table is not on this disk (the caller then opens the scene picker, as before). */
int AW_TpPlacesOpen(void);

#endif
