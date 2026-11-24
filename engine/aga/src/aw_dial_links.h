/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The links in the dialogue window's text (DIALOGUE-LINKS-62): which topics a link may ask now (one bit per table
 * topic, the topics of the speaker's current topic list) and the on-screen runs of links the mouse can click. Pure
 * rules, no engine state, so the click path is tested natively (tests/aga_dial_links_test.c). */
#ifndef AW_DIAL_LINKS_H
#define AW_DIAL_LINKS_H

/* one visible run of a link on one line: its box (x, y of the text row, width) and what it asks */
typedef struct {short x,y,w;unsigned short topic;short para,span;} aw_dial_hit_t;

/* BITS (TOPICS/8+1 bytes): exactly the topics of LIST[0..N) that are table topics (0 <= t < TOPICS) */
void AW_DialLinksSet(unsigned char *bits,int topics,const int *list,int n);
/* a link to TOPIC is lit and asks it now */
int AW_DialLinkOn(const unsigned char *bits,int topics,int topic);
/* the hit under the mouse (X, Y) of HITS[0..N) on rows ROW_H high (a row's box starts one pixel above its text),
 * -1 none */
int AW_DialLinkHit(const aw_dial_hit_t *hits,int n,int x,int y,int row_h);

/* DIALOGUE-CHOICES-62: a result script's Choice rows, drawn in the text under the last answer (OpenMW 0.51
 * DialogueWindow: the choices are links at the end of the history; the original shows them the same way). A row's
 * on-screen runs are hits with para AW_DIAL_HIT_CHOICE and span = the row (0 = the first Choice option); the pick is
 * always by row, never by typed letters. */
#define AW_DIAL_HIT_CHOICE (-1)
/* the choice row under the mouse (X, Y) of HITS[0..N) on rows ROW_H high, -1 none (a link is never a choice) */
int AW_DialChoiceAt(const aw_dial_hit_t *hits,int n,int x,int y,int row_h);
/* the keyboard's row after FOCUS (-1 none yet) of COUNT rows: DIR 1 down, -1 up, wrapping; from none the first row
 * (down) or the last (up); -1 when there are no rows */
int AW_DialChoiceStep(int count,int focus,int dir);

/* DIALOGUE-SCROLLBARS-62: the thin scroll bar beside each pane (the text and the topic list), always drawn so the
 * layout never shifts: dim in the frame's brown when the pane cannot scroll, lit with a thumb when it can */
#define AW_DIAL_BAR_W 3
#define AW_DIAL_BAR_MIN_THUMB 6
#define AW_DIAL_BAR_DIM 0x3e3524u      /* 62,53,36: the window's frame brown, darkened */
#define AW_DIAL_BAR_TRACK 0x967e50u    /* 150,126,80: the frame's lit colour */
#define AW_DIAL_BAR_THUMB 0xdfc99fu    /* 223,201,159 */
/* TOTAL lines, VISIBLE on screen, FIRST the top one shown, on a track TRACK pixels long: 1 and the thumb's start
 * (*POS, from the track's top) and length (*LEN) when the pane overflows, 0 (no thumb, both 0) when it fits */
int AW_DialBar(int total,int visible,int first,int track,int *pos,int *len);
/* the first line shown for the thumb grabbed at its centre at Y pixels down the track (a drag or a click) */
int AW_DialBarFirst(int total,int visible,int track,int y);
/* the whole bar, H pixels: an arrow end of AW_DIAL_BAR_ARROW pixels at each end (one line up / down), the track
 * between them (H - 2 arrows; AW_DialBar and AW_DialBarFirst work on it, Y counted from the track's top). A plain
 * click at Y pixels down the bar (no wheel needed): the arrow ends step one line, the track above or below the thumb
 * pages (VISIBLE - 1 lines), the thumb itself is grabbed for a drag (*GRAB 1). The new first line, clamped. */
#define AW_DIAL_BAR_ARROW 4
int AW_DialBarClick(int total,int visible,int first,int h,int y,int *grab);

/* DIALOGUE-WINDOW-LAYOUT-57: the talk window's right column as the original's (OpenMW 0.51 mwgui/dialogue.cpp
 * DialogueWindow::updateTopicsPane and updateDisposition): the disposition bar on top (a person only), then the
 * special entries, each only when the speaker offers it, in this order, then a separator line, then the topics, and
 * Goodbye at the bottom. The entries' words are the game settings sPersuasion, sBarter, sSpells, sTravel,
 * sSpellmakingMenuTitle, sEnchanting, sServiceTrainingTitle, sRepair and sCompanionShare. */
enum {AW_DIAL_SPECIAL_PERSUASION,AW_DIAL_SPECIAL_BARTER,AW_DIAL_SPECIAL_SPELLS,AW_DIAL_SPECIAL_TRAVEL,
      AW_DIAL_SPECIAL_SPELLMAKING,AW_DIAL_SPECIAL_ENCHANTING,AW_DIAL_SPECIAL_TRAINING,AW_DIAL_SPECIAL_REPAIR,
      AW_DIAL_SPECIAL_COMPANION,AW_DIAL_SPECIALS};
#define AW_DIAL_OFFER(k) (1u<<(k))
/* the special entries of OFFERS (AW_DIAL_OFFER bits) in the original's order into OUT (room for AW_DIAL_SPECIALS),
 * how many; a speaker that is not a PERSON (a creature) never has Persuasion (OpenMW: an NPC record only) */
int AW_DialSpecialEntries(unsigned offers,int person,int *out);
/* the separator line goes under shown row I of SHOWN[0..N) (indices into LIST, whose special entries have negative
 * codes and whose topics are table topics, 0 or more): row I is a special entry and the next shown row a topic, so a
 * search that hides every special entry, or every topic, draws none (OpenMW: a separator only after an entry) */
/* DIALOGUE-WINDOW-LAYOUT-57: whether the divider row stands between the special entries and the topics: both exist and
 * the window is not left with Goodbye only */
int AW_DialDividerWanted(int entries,int topics,int goodbye_only);
int AW_DialSeparatorUnder(const int *list,const int *shown,int n,int i);

#endif
