/* SPDX-License-Identifier: GPL-2.0-or-later
 * The game's text defines (BOOK-TEXT-MACROS-58): %PCName and the rest in books, scrolls, journal entries, message
 * boxes and dialogue, filled in from one getter table. The rules follow OpenMW 0.51 (components/interpreter/
 * defines.cpp: '%' or '^' starts a define, names compared without case as a prefix of the text, the action bindings
 * and %PCCrimeLevel first, then the fixed list, then the game's global variables, longest name first; outside
 * dialogue %Name, %Race and %Class are the player's and the speaker-only defines print nothing; an unknown define
 * prints as written), written independently.
 *
 * Two inputs: a define written out (%PCName) and the builder's code for it (AW_TEXTDEF_CODE + the getter's number,
 * AW_TEXTDEF_GLOBAL + the global's number in two bytes), so a converted text needs no name search at run time.
 *
 * Pure C, no engine headers (native tests: tests/test_text_defines.py). */
#ifndef AW_TEXTDEF_H
#define AW_TEXTDEF_H

#define AW_TEXTDEF_CODE 0x01     /* followed by 1 + the getter number (AW_TD_*) */
/* followed by 1 + global / 255 and 1 + global % 255 (no zero byte). Was 0x02 until v0.0.59: 0x02 and 0x03 are the
 * dialogue's link marks (aw_dial.h AW_DIAL_LINK_OPEN/CLOSE), which reached this table as a global code and printed a
 * number over a link's first two letters (DIALOGUE-LINK-MARK-AS-DEFINE-58). */
#define AW_TEXTDEF_GLOBAL 0x04
/* the bytes of the code at P (2 or 3), 0 when P holds none: passes that move text around keep a code whole (its
 * second and third bytes may equal any mark) */
#define AW_TEXTDEF_CODE_BYTES(p) ((unsigned char)(p)[0] == AW_TEXTDEF_CODE && (p)[1] ? 2 : \
                                  (unsigned char)(p)[0] == AW_TEXTDEF_GLOBAL && (p)[1] && (p)[2] ? 3 : 0)

enum {
    AW_TD_PCCRIMELEVEL, AW_TD_NEXTPCRANK, AW_TD_PCNEXTRANK, AW_TD_FACTION, AW_TD_PCCLASS, AW_TD_PCNAME,
    AW_TD_PCRACE, AW_TD_PCRANK, AW_TD_CLASS, AW_TD_CELL, AW_TD_RACE, AW_TD_RANK, AW_TD_NAME,
    AW_TD_ACTION_FIRST    /* the action bindings follow: AW_TD_ACTION_FIRST + AW_TextDefineAction index */
};
#define AW_TD_ACTIONS 19
/* %GameHour: in OpenMW a global like the others (matched after the fixed list); here a getter of the game clock
 * (TEXT-MACROS-DIALOGUE-CODES-59), so the builder codes it and no global name is searched */
#define AW_TD_GAMEHOUR (AW_TD_ACTION_FIRST + AW_TD_ACTIONS)
#define AW_TD_COUNT (AW_TD_GAMEHOUR + 1)

/* The values a text is filled from. Strings may be NULL (= empty). SPEAKER = 0 outside dialogue. */
typedef struct {
    int speaker;
    const char *pc_name, *pc_race, *pc_class, *pc_rank, *pc_next_rank, *cell;
    int pc_crime;
    const char *name, *race, *clas, *faction, *rank;      /* the speaker's */
    /* the game's globals: the longest global name (any case) that the RUN characters at TEXT start with: its number
     * and LENGTH, -1 none; and a global's value as text */
    int (*global_prefix)(const char *text, int run, int *length);
    void (*global_text)(int global, char *out, int capacity);
    const char *(*action_key)(int action);                 /* the key bound to an action, NULL: the action's word */
    int clock;            /* 1: GAME_HOUR is the clock's hour of the day; 0: %GameHour reads the global of that name */
    float game_hour;
} aw_textdef_values_t;

/* The define names in getter order (lower case; AW_TD_COUNT of them). */
const char *AW_TextDefineName(int id);
/* The getter table: define ID's text for V into OUT (NUL-terminated). */
void AW_TextDefineValue(int id, const aw_textdef_values_t *v, char *out, int capacity);
/* The builtin define at TEXT (after the '%'/'^'): its id and length, -1 none. */
int AW_TextDefineMatch(const char *text, int *length);
/* Fill SOURCE's defines (written and coded) into OUT; never longer than CAPACITY - 1. Returns the length. */
int AW_TextDefines(char *out, int capacity, const char *source, const aw_textdef_values_t *v);

/* Engine part (left out with AW_TEXTDEF_HOST_TEST; native fixtures give their own): the values from the player's
 * character and the game state. */
void AW_TextDefinesPlayer(aw_textdef_values_t *v);
/* The key bound to action A (an AW_TD_ACTION_FIRST offset; the player's bindings, keys.c), NULL when none is bound. */
const char *AW_TextDefineBoundKey(int action);
/* aw_mwhost.c: the longest global name at TEXT (global_prefix above) and a global's type (0 short, 1 long, 2 float,
 * -1 none), from the compiled scripts' file. */
int AW_MwscriptGlobalPrefix(const char *text, int run, int *length);
int AW_MwscriptGlobalType(int global);
#endif
