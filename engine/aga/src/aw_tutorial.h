/* SPDX-License-Identifier: GPL-2.0-or-later
 * The tutorial texts' keys (OPENING-TUTORIAL-KEYS-65): a message box of the game that names a control or announces a
 * window is shown with the key the player has bound now. The rows (config/tutorial-texts.json, rendered into
 * aw_tutorial_table.inc) are found by the normalized hash of the box's text, so no game text is kept in the repo.
 * Pure C (tests/aga_tutorial_test.c); the engine sets aw_msgbox_tutorial (aw_msgbox.c) at its init. */
#ifndef AW_TUTORIAL_H
#define AW_TUTORIAL_H

/* ONCE (AW_TUTORIAL_ONCE): shown the first time in a game only (AW_TutorialReset clears it), the original text after
 * it. AW_TUTORIAL_HIDE: the box is not shown at all; its row of the box before it already says it (the original's
 * second "right click to use your new menu" box after the stats and the inventory boxes showed our same text twice,
 * TUTORIAL-BOX-SHOWN-TWICE-65); text "" */
#define AW_TUTORIAL_ONCE 1
#define AW_TUTORIAL_HIDE 2
typedef struct {unsigned long hash;int once;const char *text;} aw_tutorial_row_t;
void AW_TutorialReset(void);
/* FNV-1a over TEXT in lower case with every run of white space as one space, the ends trimmed (32 bits). */
unsigned long AW_TutorialHash(const char *text);
/* The row's AmiWind text for HASH, NULL none. */
const char *AW_TutorialFind(unsigned long hash);
int AW_TutorialRows(void);
const aw_tutorial_row_t *AW_TutorialRow(int i);
/* TEMPLATE filled into OUT: {text} = ORIGINAL, {key:COMMAND} = KEY(COMMAND), the bound key's name ("not bound" when
 * nothing is bound); never longer than CAPACITY - 1. Returns the length. */
int AW_TutorialFill(const char *tmpl,const char *original,const char *(*key)(const char *command),char *out,int capacity);
/* OPENING-TUTORIAL-KEYS-65: a window's own action keys, bindable (the inventory's use/equip and drop): LIST is the
 * binding, key names separated by spaces ("E ENTER"). 1 when NAME (Key_KeynumToString of the key pressed) is in it;
 * and the list as a player reads it into OUT ("E or Enter"), "" for an empty list. */
int AW_WinKeyMatch(const char *list,const char *name);
void AW_WinKeyWords(const char *list,char *out,int capacity);
/* TEXT's row filled into OUT: 1 when TEXT has a row, else 0 (OUT untouched); -1 when its row hides the box. */
int AW_TutorialApply(const char *text,const char *(*key)(const char *command),char *out,int capacity);
#endif
