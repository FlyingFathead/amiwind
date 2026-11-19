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
#include <stdio.h>

#define AW_LISTBOX_SEARCH 24

/* abstract keys (aw_listbox.c maps the engine's) */
enum {AW_LBKEY_UP=1,AW_LBKEY_DOWN,AW_LBKEY_PAGEUP,AW_LBKEY_PAGEDOWN,AW_LBKEY_HOME,AW_LBKEY_END,
      AW_LBKEY_BACKSPACE,AW_LBKEY_CHOOSE,AW_LBKEY_CLOSE,AW_LBKEY_LEFT,AW_LBKEY_RIGHT};
/* what a key did */
enum {AW_LB_NONE=0,AW_LB_CHOSEN=1,AW_LB_CLOSED=2};

typedef const char *(*aw_listbox_label_t)(void *ctx,int row);

/* TP-MENU-CATEGORY-FILTER-66: a row's category (1..categories-1; category 0 is "All", every row) */
typedef int (*aw_listbox_category_t)(void *ctx,int row);
#define AW_LISTBOX_CATEGORIES 6

typedef struct {
    int count;                      /* the caller's rows */
    aw_listbox_label_t label;
    void *ctx;
    int *shown,shown_count;         /* the rows the search keeps, in the caller's order (caller's buffer, count ints) */
    int selection,top,visible;      /* selection and top index into shown; visible rows on screen */
    char search[AW_LISTBOX_SEARCH+1];
    aw_listbox_category_t category; /* NULL: no category row */
    int categories,chosen;          /* buttons (All included) and the chosen one (0 = All) */
} aw_listbox_t;

void AW_ListBoxReset(aw_listbox_t *b,int count,aw_listbox_label_t label,void *ctx,int *shown,int visible);
/* The category buttons (TP-MENU-CATEGORY-FILTER-66): COUNT buttons (All first), CATEGORY gives each row's; the
 * search filters within the chosen one. AW_ListBoxChoose picks button N (0 = All) and filters again. */
void AW_ListBoxCategories(aw_listbox_t *b,aw_listbox_category_t category,int count);
void AW_ListBoxChoose(aw_listbox_t *b,int n);
/* 1 when LABEL holds SEARCH, letters and digits only, case ignored ("aldruhn" finds "Ald-ruhn"); "" holds all. */
int AW_ListBoxMatches(const char *label,const char *search);
/* 1 when LABEL names TEXT (DBG-TP-EXPANSION-ARRIVALS-66): the label without its trailing " (...)" parts (" (interior)",
 * " (Tribunal)") has exactly TEXT's letters and digits, case ignored; TEXT without a letter or digit names nothing. */
int AW_ListBoxNames(const char *label,const char *text);
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
    /* optional category buttons (zero: none): their labels, All first, and each row's category */
    const char *const *category_names;
    int categories;
    aw_listbox_category_t category;
    /* optional, DBG-SPAWN-MENU-67 (NULL: none): DETAIL a line about the selected row, over the footer; a switch row
     * under it, CHECK its words and *CHECKED its state, turned by Space or a click on it (a filter typed in the search
     * holds letters and digits only, so Space is free) */
    aw_listbox_label_t detail;
    const char *check;
    int *checked;
} aw_listbox_spec_t;
int AW_ListBoxOpen(const aw_listbox_spec_t *spec);
int AW_ListBoxActive(void);

/* The settlements table (tools/tp_places_lut.py, id1/tp-places.lut), big-endian: header 16 bytes "AWTP",
 * u16 version, u16 row bytes, u32 rows, u32 0. Version 2 (TP-MENU-INTERIORS-63), rows x 96: name[64] (Latin-1,
 * NUL-padded), i32 x, y, z (original global units: the arrival point), u8 flags (AW_TP_*), u8 named cells, u16 0,
 * map[16] (a room row's map name). Version 1 (an older disk), rows x 48: name[32], the same 16 bytes, no map.
 * Sorted by name. */
#define AW_TP_HEADER 16
#define AW_TP_ROW 48         /* version 1 */
#define AW_TP_ROW2 96        /* version 2 */
#define AW_TP_NAME1 32
#define AW_TP_NAME 64
#define AW_TP_MAP 16
#define AW_TP_HAS_Z 1        /* z is the arrival height (else: the floor at or below the point) */
#define AW_TP_DOOR 2         /* the arrival of a door into the place (on the street) */
#define AW_TP_COC 4          /* the game's own CocMarkerHeading */
#define AW_TP_ROOM 8         /* a converted room: map is its room map, entered through dbg tp <map> */
/* Version 3 (DBG-TP-TO-NPC-66), rows x 128: the version 2 row, then id[32] (a being's record id). */
#define AW_TP_ROW3 128
#define AW_TP_ID 32
#define AW_TP_BEING 16       /* a person or creature: id is its record; map its room map ("" outdoors: x y z global) */
#define AW_TP_NEAREST 32     /* a common kind: map names its placements file tpk/<map>.tpk; the nearest one */
/* the list's categories (the buttons All / Exteriors / Interiors / Beings) */
enum {AW_TP_CAT_ALL=0,AW_TP_CAT_EXTERIOR,AW_TP_CAT_INTERIOR,AW_TP_CAT_BEING,AW_TP_CATS};
int AW_TpPlacesCategory(int flags);
typedef struct {char name[AW_TP_NAME];char map[AW_TP_MAP];char id[AW_TP_ID];long x,y,z;int flags,cells;} aw_tp_place_t;
/* A common kind's placements file (tools/tp_places_lut.py, id1/tpk/<name>.tpk), big-endian: "AWTK", u16 1, u16 64,
 * u32 rows, u32 0; rows x 64: id[32], map[16] (a room map, "" outdoors), i32 x, y, z, u32 0. */
#define AW_TPK_HEADER 16
#define AW_TPK_ROW 64
/* The names list (tools/tp_places_lut.py, id1/tp-names.lut): what the box holds while open, row for row the same as
 * tp-places.lut. Big-endian: "AWTN", u16 1, u16 0, u32 rows, u32 name bytes; then per row u8 category (AW_TP_CAT_*),
 * u8 length (at most 63), the label (Latin-1, no NUL). Held as ONE block allocated at open and freed at close: the
 * labels and a u32 offset per row, or (low memory, WHOLE 0) only the offsets, the labels read from FILE in 4 KB
 * chunks into the struct's own buffer. A row's details (position, map, id) are read from tp-places.lut on choose. */
#define AW_TPN_HEADER 16
#define AW_TPN_CHUNK 4096
typedef struct {
    unsigned char *block;          /* the one allocation */
    const unsigned char *names;    /* the labels, whole; NULL when paged */
    unsigned long *at;             /* offset of each row from the first row, rows entries */
    long rows,bytes,base;
    FILE *file;                    /* paged: the open names file (the caller's; never closed here) */
    unsigned char chunk[AW_TPN_CHUNK];
    long chunk_at,chunk_len;
} aw_tp_names_t;
/* Rows, or -1 (a bad file, no memory); BASE is the file position of the header in F (read from there). */
long AW_TpNamesOpen(aw_tp_names_t *n,FILE *f,long base,long size,int whole);
/* Row I's label into LABEL (NUL-ended) and its category; 0 when it cannot be read. */
int AW_TpNamesGet(aw_tp_names_t *n,long i,char *label,int size,int *category);
void AW_TpNamesClose(aw_tp_names_t *n);
/* The bytes the open list holds (the block). */
long AW_TpNamesHeld(const aw_tp_names_t *n);
/* A typed name (dbg tp TEXT, DBG-TP-EXPANSION-ARRIVALS-66): the row of the names list (F at BASE, SIZE bytes) the box
 * would take for TEXT: the first row that names it (AW_ListBoxNames), else the only row that holds it
 * (AW_ListBoxMatches). -1 when no row holds it (or the file is bad); -2 when several hold it and none names it: *MATCHES
 * gets how many, LIST the first labels with "; " between them, as many as fit. Read row by row, nothing allocated. */
long AW_TpNamesFind(FILE *f,long base,long size,const char *text,long *matches,char *list,int list_size);
long AW_TpKindRows(const unsigned char *data,long size);
void AW_TpKindRow(const unsigned char *data,long i,aw_tp_place_t *p);
/* rows of a table of SIZE bytes (header checked, size exact); -1 when it is no AWTP1/AWTP2/AWTP3 table */
long AW_TpPlacesRows(const unsigned char *data,long size);
/* row I of a checked table into P (the name and the map always end in a NUL) */
void AW_TpPlacesRow(const unsigned char *data,long i,aw_tp_place_t *p);
/* the console line that takes you there: "aw_teleport X Y [Z]\n" (the coordinate path), for a room row
 * "dbg tp <map>\n" (the room path, at its door's arrival); length or -1 */
int AW_TpPlacesCommand(const aw_tp_place_t *p,char *out,int size);

/* dbg tp with no argument (aw_tpplaces.c): the settlements box from id1/tp-places.lut, read when it opens and
 * freed when it closes; 0 when the table is not on this disk (the caller then opens the scene picker, as before). */
int AW_TpPlacesOpen(void);
/* dbg tp TEXT for a name no other form takes (aw_tpplaces.c, DBG-TP-EXPANSION-ARRIVALS-66): the row of the list TEXT
 * names, chosen as in the box (AW_TpNamesFind); several rows: their count and first names, nothing moved. 1 when the
 * list took TEXT, 0 when no row holds it or the list is not on this disk. */
int AW_TpPlacesFind(const char *text);

/* A free spot beside a being (aw_listbox_rules.c, host-tested): candidate I (0..AW_TP_SPOTS-1) around CENTRE at
 * rings of RADIUS, RADIUS+24, RADIUS+48, 16 directions, the direction from FROM first; OUT gets the point. */
#define AW_TP_SPOTS 48
void AW_TpSpotCandidate(const float *centre,const float *from,float radius,int i,float *out);
/* The first candidate FREE_AT accepts (it tests the player's hull there and gives the standing point in OUT):
 * its number + 1, or 0 when none is free. */
int AW_TpPickSpot(const float *centre,const float *from,float radius,
                  int (*free_at)(void *ctx,const float *point,float *out),void *ctx,float *out);
/* The yaw (degrees, 0..360) from FROM looking at TO */
float AW_TpFacingYaw(const float *from,const float *to);
/* TP-BEING-TRIBUNAL-FALLS-THROUGH-67: a being row's point is where the being stands (its feet: the original's placed
 * position, in the room's units); a room arrival is the player's origin, the standing box's bottom (BOX_BOTTOM, the
 * player's mins z) a quarter unit above that floor, as every door's arrival into a room (tools/town_interiors.py FEET
 * 16.875 = 16.625 + .25). OUT gets that arrival. */
void AW_TpBeingArrival(const float *feet,float box_bottom,float *out);
/* dbg tp's being arrival (aw_tpplaces.c): a chosen Beings row; on arrival in its scene the player is put on a free
 * spot beside the being, facing it (called from aw_scene.c AW_SceneSpawn and by aw_tp_being_arrive). */
void AW_TpBeingGo(const aw_tp_place_t *p);
void AW_TpBeingArrive(void);
void AW_TpPlacesInit(void);

#endif
