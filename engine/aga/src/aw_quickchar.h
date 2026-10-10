/* SPDX-License-Identifier: GPL-2.0-or-later
 * The quick character screen: the game's own character menus (aw_character.c)
 * in one sequence, for any caller that wants a character made or changed
 * quickly: a new game with --skip-census, the debug command dbg quickchar,
 * test and combat set-ups. One entry point, one implementation. */
#ifndef AW_QUICKCHAR_H
#define AW_QUICKCHAR_H
/* Pages, shown in this order; a caller picks any non-empty set. */
#define AW_QC_NAME       1   /* the name entry (the ship prompt's editing) */
#define AW_QC_APPEARANCE 2   /* race, sex, face and hair, with the head model */
#define AW_QC_CLASS      4
#define AW_QC_BIRTHSIGN  8
#define AW_QC_REVIEW     16  /* attributes and skills (review pages; R/C/B go back) */
#define AW_QC_ALL        31
/* Flag: the census officer's greeting when the screen opens and the dock
 * guard's line with a page sound when the character is confirmed (cvar
 * aw_quickchar_voice, default 1; absent files are skipped). */
#define AW_QC_VOICE      64
/* Called once when the screen closes: 1 accepted (aw_character and the player
 * updated), 0 cancelled (nothing changed). */
typedef void (*aw_quickchar_done_t)(int accepted);
/* Opens the screen over the current scene (a world must be loaded). Returns 0
 * and changes nothing when it cannot open (no world, catalogue missing, story
 * scene running, screen already open). */
int AW_QuickCharOpen(int pages,aw_quickchar_done_t on_done);
int AW_QuickCharActive(void);
/* Closes an open screen without accepting the current page (done(0)). */
void AW_QuickCharCancel(void);
/* Page words ("name race class birthsign review all", any order) to a page set; 0 if a word is unknown. */
int AW_QuickCharPages(int argc,char **argv,int first);
int AW_QuickCharKey(int key);
void AW_QuickCharDraw(void);
/* Once per frame (host.c), also while the world is frozen behind the screen. */
void AW_QuickCharTick(void);
void AW_QuickCharInit(void);
/* aw_skip_census (default 0; the builder's --skip-census writes 1 into the
 * game's default settings): New Game makes the character on the quick screen
 * instead of the ship and the census office walk. */
int AW_SkipCensus(void);
/* 1 once a test set the character with aw_quickchar_set (until aw_quickchar_set clear):
 * a quick start keeps that character and opens no screen. */
int AW_QuickCharScripted(void);
/* The ship's name entry, shared (aw_intro.c): editing (1 when Enter accepts a
 * non-empty name) and the line with its caret. */
int AW_NameEdit(char *name,int capacity,int key);
void AW_NameDraw(int x,int y,const char *name);
#endif
