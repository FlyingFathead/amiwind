/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_CSTRIP_H
#define AW_CSTRIP_H
/* CONTAINER-WINDOW-59: the container strip, a box along the bottom of the screen up to the view that lists an opened
 * container's items (picture, name, count) and, on its second row, the player's own items to put in. Everything is
 * allocated when it opens and freed when it closes: nothing is resident while it is closed. Takes and puts go through
 * the container deltas of the world change list (aw_inventory.h AW_ContainerTake / AW_ContainerPut), so they are kept
 * across maps and saves; a take from an owned container is stolen (the change list's stolen mark).
 * The pure rules (aw_cstrip_rules.c, native-tested): selection, scrolling, the mouse's cell and the sides. */
#define AW_CSTRIP_ROWS 64          /* a side's entries: the container list (AW_CONTAINER_ITEMS) and the inventory */
#define AW_CSTRIP_NAME 40
enum {AW_CSTRIP_CONTAINER,AW_CSTRIP_INVENTORY};
typedef struct {char id[33];char name[AW_CSTRIP_NAME];int count;} aw_cstrip_entry_t;
typedef struct {
    aw_cstrip_entry_t row[2][AW_CSTRIP_ROWS];
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
/* The entry under (X,Y) for cells of W x H from (LEFT,TOP), COLUMNS of them: its index on the side shown, -1 none. */
int AW_CStripCell(const aw_cstrip_list_t *list,int x,int y,int left,int top,int w,int h);
/* aw_cstrip.c: the strip in the game (keys before the bindings, drawn over the view, the mouse while open), reached
 * through the hooks AW_CStripInit sets (quakedef.h). */
int AW_CStripActive(void);
int AW_CStripKey(int key);
void AW_CStripDraw(void);
int AW_CStripMouse(int dx,int dy);
/* CONTAINER-STRIP-REDRAW-COST-59: frames left that copy the whole screen out (a change sets a few; 0 = only the view) */
int AW_CStripDirty(void);
#endif
