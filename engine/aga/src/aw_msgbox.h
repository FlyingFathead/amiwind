/* SPDX-License-Identifier: GPL-2.0-or-later
 * The scripts' MessageBox (v0.0.51): the text with its numbers formatted in, its buttons, the button the player
 * chose. The rules (aw_msgbox_rules.c) have no engine dependencies and are host-tested (tests/aga_msgbox_test.c);
 * aw_msgbox.c shows the box in the game.
 */
#ifndef AW_MSGBOX_H
#define AW_MSGBOX_H

/* CRIME-RELEASE-LINE-CUT-62: room for a long jail release (its first line and a line for every skill it changed) */
#define AW_MSGBOX_TEXT 1024
#define AW_MSGBOX_LINES 32                         /* at most this many text lines are drawn */
#define AW_MSGBOX_BUTTONS 12
#define AW_MSGBOX_LABEL 48

typedef struct {
    int open;                                      /* a box with buttons is shown */
    int count,selection;                           /* its buttons, the one the keys are on */
    int pressed;                                   /* the button chosen, -1 none; GetButtonPressed takes it */
    char text[AW_MSGBOX_TEXT];
    char button[AW_MSGBOX_BUTTONS][AW_MSGBOX_LABEL];
} aw_msgbox_t;

/* The keys of a shown box (AW_MsgBoxKey). */
enum {AW_MSGKEY_PREVIOUS=1,AW_MSGKEY_NEXT,AW_MSGKEY_CHOOSE,AW_MSGKEY_DIGIT=10};   /* DIGIT+n: button n (1-9) */

/* MWScript's message text (OpenMW interpreter formatMessage): %% a percent sign; %d %D the whole part of the next
 * number; %f %F %g %G %e %E the next number, with an optional ".N" precision (and a width); %s %S (string arguments
 * the compiler does not pass) are kept as written. A missing number reads 0. Returns the length written. */
int AW_MsgBoxFormat(char *out,int capacity,const char *format,const float *numbers,int number);
/* How long a box without buttons stays (OpenMW: the text's length times fMessageTimePerChar 0.1 s), 3 to 10 s. */
double AW_MsgBoxSeconds(const char *text);
void AW_MsgBoxReset(aw_msgbox_t *m);
/* A box with COUNT buttons (COUNT >= 1): it replaces a shown one (OpenMW createInteractiveMessageBox), and the
 * last choice is forgotten. Buttons past AW_MSGBOX_BUTTONS are left out. */
void AW_MsgBoxOpen(aw_msgbox_t *m,const char *text,const char *const *buttons,int count);
/* A key of a shown box: returns the button chosen (and closes the box), else -1. */
int AW_MsgBoxKey(aw_msgbox_t *m,int key);
/* GetButtonPressed: the button chosen, once; -1 until the next choice. */
int AW_MsgBoxTake(aw_msgbox_t *m);
/* CRIME-RELEASE-LINE-CUT-62: how many of a text's LINES (wrapped) a box with button ROWS shows on a screen SCREEN pixels
 * high, with LINE pixels a line: every line while the box fits (8 above and below the text, 24 a button row, 8 from
 * the screen's edges), else as many as fit (at least 1, at most AW_MSGBOX_LINES). OpenMW's box grows with its text. */
int AW_MsgBoxLinesShown(int lines,int rows,int screen,int line);

/* Where a box and its buttons are (MSGBOX-NO-CURSOR-62; the pointer's hit test and the drawing share them). FRAME
 * and RECT: x, y, w, h. A script's box: TEXT_PX of text on a VW x VH screen; the death box: AW_DEATHBOX_W x _H.
 * ButtonAt: the button under PX, PY, else -1. */
#define AW_MSGBOX_PER_ROW 3
#define AW_DEATHBOX_W 280
#define AW_DEATHBOX_H 96
void AW_MsgBoxLayout(int count,int vw,int vh,int text_px,int frame[4]);
void AW_MsgBoxButtonRect(int count,int i,const int frame[4],int rect[4]);
int AW_MsgBoxButtonAt(int count,const int frame[4],int px,int py);
/* UI-TEXT-BOX-CLEARANCE-64: the same with each button as wide as its label (LABEL_W[i] pixels) plus AW_MSGBOX_BUTTON_PAD
 * on each side, at least AW_MSGBOX_BUTTON_MIN, at most its share; a row's buttons centred in the box. */
#define AW_MSGBOX_BUTTON_PAD 12
#define AW_MSGBOX_BUTTON_MIN 48
void AW_MsgBoxButtonRectSized(int count,int i,const int frame[4],const int *label_w,int rect[4]);
int AW_MsgBoxButtonAtSized(int count,const int frame[4],const int *label_w,int px,int py);
void AW_DeathBoxButtonRect(int count,int i,int vw,int vh,int rect[4]);
int AW_DeathBoxButtonAt(int count,int vw,int vh,int px,int py);

/* The game (aw_msgbox.c): show a box (no buttons: a timed notice), its keys and drawing (1 = the key was used). */
void AW_MsgBoxShow(const char *text,const char *const *buttons,int count);
int AW_MsgBoxActive(void);
int AW_MsgBoxGameKey(int key);
void AW_MsgBoxDraw(void);
int AW_MsgBoxPressed(void);
void AW_MsgBoxClear(void);
#endif
