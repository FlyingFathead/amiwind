/* SPDX-License-Identifier: GPL-2.0-or-later
 * UI-NO-SHARED-LAYOUT-67: the one layout for every menu, message box and HUD text. A screen gives its box and asks the
 * helper where its title, its content and its buttons go; it never places a button or a line by pixels of its own.
 * Every number is in aw_layout_metrics (aw_layout.c), not in the screens.
 *
 * The rules the helper keeps and the gate measures (tests/aga_ui_layout_test.c, from what is actually drawn):
 * - a text or button lies inside its box's frame, with the padding clear between them;
 * - the button row stands AW_LAYOUT bottom margin above the box's inner bottom edge, never against it;
 * - no two texts share screen space (the HUD included), unless a box drawn between them covers the first.
 * No engine dependencies: host tested. */
#ifndef AW_LAYOUT_H
#define AW_LAYOUT_H

/* The table of every number (pixels, at the 320x200 screen) */
typedef struct {
    int edge;           /* the skin frame's edge (AW_UI_FRAME_EDGE) */
    int pad;            /* clear pixels between the frame's inner edge and what is inside (AW_UI_TEXT_CLEAR) */
    int button_h;       /* a button's height */
    int button_gap;     /* the clear pixels between two buttons of a row */
    int button_pad;     /* the clear pixels left and right of a button's label */
    int button_min;     /* the narrowest button */
    int bottom_margin;  /* the clear rows between the button row and the frame's inner bottom edge */
    int content_gap;    /* the clear rows between the content and the button row, and under the title row */
    int button_edge;    /* the thick (skin) button frame's edge; the thin outline's is 1 */
} aw_layout_metrics_t;
extern const aw_layout_metrics_t aw_layout_metrics;

/* A box laid out: RECT (x, y, w, h) of the frame; INNER the area inside the frame and the padding */
typedef struct {
    int box[4],inner[4];
    int title[4];       /* the title row (h 0: none) */
    int content[4];     /* what is left between the title and the button row */
    int buttons;        /* the number of buttons in the row (0: none) */
    int button[8][4];
} aw_layout_t;
#define AW_LAYOUT_BUTTONS 8

/* Lay out a box at X Y W H: TITLE_H the title row's height (0 none), COUNT buttons whose labels are LABEL_W pixels wide
 * (NULL: the narrowest), BUTTON_H their height (0: the table's). The buttons are centred in one row, sized to their
 * labels, the bottom margin above the frame's inner edge; the content takes what is left. */
void AW_LayoutBox(aw_layout_t *l,int x,int y,int w,int h,int title_h,int count,const int *label_w,int button_h);
/* The height a box needs for CONTENT_H pixels of content under a TITLE_H title and over a row of buttons (none when
 * BUTTONS is 0) */
int AW_LayoutBoxHeight(int content_h,int title_h,int buttons,int button_h);
/* The button under the pointer PX PY, -1 none (the hit test uses the same rectangles as the drawing) */
int AW_LayoutButtonAt(const aw_layout_t *l,int px,int py);

/* THE CHECK: what a screen drew, recorded as it is drawn (aw_ui.c records while AW_LayoutRecording is set) */
enum {AW_LAYOUT_BOX=1,AW_LAYOUT_BUTTON,AW_LAYOUT_TEXT,AW_LAYOUT_THIN_BOX};
typedef struct {int kind,x,y,w,h;char label[40];} aw_layout_rect_t;
#define AW_LAYOUT_RECORDS 512
typedef struct {int count,dropped;aw_layout_rect_t rect[AW_LAYOUT_RECORDS];} aw_layout_record_t;
extern aw_layout_record_t *AW_LayoutRecording;   /* NULL: nothing is recorded (the game) */
void AW_LayoutRecord(int kind,int x,int y,int w,int h,const char *label);
/* The faults in RECORD: a text or button that touches or leaves the box it starts in (the last box drawn before it that
 * holds its top left corner), a button closer than the bottom margin to that box's inner bottom edge, two texts on top
 * of one another (no box drawn between them covering the first). Each fault is a line in WHY (SIZE bytes). Returns the
 * number of faults. */
int AW_LayoutCheck(const aw_layout_record_t *record,char *why,int size);

#endif
