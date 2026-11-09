/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_CSTRIP_H
#define AW_CSTRIP_H
/* CONTAINER-WINDOW-59: the container strip, a box along the bottom of the screen up to the view that lists an opened
 * container's items (picture, name, count) and, on its second row, the player's own items to put in. Everything is
 * allocated when it opens and freed when it closes: nothing is resident while it is closed. Takes and puts go through
 * the container deltas of the world change list (aw_inventory.h AW_ContainerTake / AW_ContainerPut), so they are kept
 * across maps and saves; a take from an owned container is stolen (the change list's stolen mark).
 * The pure rules (aw_cstrip_rules.c, native-tested): selection, scrolling, the mouse's cell and the sides. */
#define AW_CSTRIP_ROWS 64          /* the container side's entries (AW_CONTAINER_ITEMS) */
#define AW_CSTRIP_NAME 40
enum {AW_CSTRIP_CONTAINER,AW_CSTRIP_INVENTORY};
typedef struct {char id[33];char name[AW_CSTRIP_NAME];int count;} aw_cstrip_entry_t;
/* INVENTORY-ORIGINAL-LIMITS-61: each side's entries are an array of CAP (heap, sized when the strip fills: the
 * container side AW_CSTRIP_ROWS, the inventory side every kind carried, no fixed limit) */
typedef struct {
    aw_cstrip_entry_t *row[2];int cap[2];
    int count[2],selected[2],first[2];
    int side,columns;              /* the side shown (CONTAINER / INVENTORY); cells in view */
} aw_cstrip_list_t;
/* Keep each side's selection inside its entries and in view (after a fill, a take or a put). */
void AW_CStripClamp(aw_cstrip_list_t *list);
/* Move the selection by DELTA on the side shown, scrolling the view to keep it there. */
void AW_CStripMove(aw_cstrip_list_t *list,int delta);
/* Show SIDE (0 / 1, else the other one). */
void AW_CStripSide(aw_cstrip_list_t *list,int side);
/* The selected entry of the side shown, NULL when that side is empty. */
const aw_cstrip_entry_t *AW_CStripSelected(const aw_cstrip_list_t *list);
/* LOOT-WINDOW-LAYOUT-60: the strip's layout on a WIDTH x HEIGHT screen whose view ends at VIEW_BOTTOM, its text lines
 * (the name, the properties, the key help) in the console font of CHAR_W x CHAR_H: rows from the bottom up, each with
 * AW_CSTRIP_GAP pixels around it inside the AW_CSTRIP_FRAME frame; the strip rises above the view when they need it. */
#define AW_CSTRIP_FRAME 4          /* the box's frame (aw_ui.c AW_UIBox) */
#define AW_CSTRIP_GAP 4            /* room above and below each row */
#define AW_CSTRIP_TITLE 14         /* the title row: the side names and the Take All / Close buttons */
#define AW_CSTRIP_CELL 36          /* a cell: the 32 x 32 picture, its frame and a gap */
#define AW_CSTRIP_COLUMNS 16       /* cells in view at most (a 640-wide screen) */
#define AW_CSTRIP_BUTTON_W 56
typedef struct {
    int top,bottom,left,columns;   /* the strip from TOP to BOTTOM; cells from LEFT, COLUMNS of them */
    int title_y,cells_y,name_y,props_y,keys_y;
    int char_w,char_h,line_h,text_columns;
} aw_cstrip_layout_t;
void AW_CStripLayout(int width,int height,int view_bottom,int char_w,int char_h,aw_cstrip_layout_t *layout);
/* The entry under (X,Y) for cells of W x H from (LEFT,TOP), COLUMNS of them: its index on the side shown, -1 none. */
int AW_CStripCell(const aw_cstrip_list_t *list,int x,int y,int left,int top,int w,int h);
/* The confirmation line of a take (CONTAINER-TAKE-CONFIRM-62): "Took Iron Sparksword", "Took Gold x 8", with " (stolen)"
 * of an owned container; FROM non-NULL: a Take All, "Took 5 items from Tarhiel". Shown only in the AmiWind name-label
 * style; the original and OpenMW 0.51 show no text for a take from a container (the item's own sound is all). */
int AW_CStripTakeLine(char *out,int size,const char *name,int count,int stolen,const char *from,int total);
/* aw_cstrip.c: the strip in the game (keys before the bindings, drawn over the view, the mouse while open), reached
 * through the hooks AW_CStripInit sets (quakedef.h). */
int AW_CStripActive(void);
/* The open strip's two lists (NULL while closed): the native tests read the names and counts */
const aw_cstrip_list_t *AW_CStripList(void);
int AW_CStripKey(int key);
void AW_CStripDraw(void);
int AW_CStripMouse(int dx,int dy);
/* CONTAINER-STRIP-REDRAW-COST-59: frames left that copy the whole screen out (a change sets a few; 0 = only the view) */
int AW_CStripDirty(void);
#endif
