/* SPDX-License-Identifier: GPL-2.0-or-later
 * The scripts' MessageBox (v0.0.51): the text with its numbers formatted in, its buttons, the button the player
 * chose. The rules (aw_msgbox_rules.c) have no engine dependencies and are host-tested (tests/aga_msgbox_test.c);
 * aw_msgbox.c shows the box in the game.
 */
#ifndef AW_MSGBOX_H
#define AW_MSGBOX_H

#define AW_MSGBOX_TEXT 512
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

/* The game (aw_msgbox.c): show a box (no buttons: a timed notice), its keys and drawing (1 = the key was used). */
void AW_MsgBoxShow(const char *text,const char *const *buttons,int count);
int AW_MsgBoxActive(void);
int AW_MsgBoxGameKey(int key);
void AW_MsgBoxDraw(void);
int AW_MsgBoxPressed(void);
void AW_MsgBoxClear(void);
#endif
