/* SPDX-License-Identifier: GPL-2.0-or-later
 * A place that cannot be reached or loaded, as one record (SCENE-LOAD-FAIL-FALLBACK-67, DBG-TP-NOT-FOUND-BOX-67): its
 * kind and short code, the OK box's text in the maintainer's form, the load menu's notice and the console's debug
 * block. No engine dependencies: host-tested by tests/aga_loaderr_test.c. aw_scene.c fills the record (every scene
 * load passes there: dbg tp, doors, travel, scripts, region crossings), aw_loadfail.c shows the box with one OK
 * button. The kinds and codes are listed for players in docs/LOAD_ERRORS.md.
 */
#ifndef AW_LOADERR_H
#define AW_LOADERR_H

/* The kinds. Codes LF1..LF9 in this order; the box and the console line share them. */
enum {
    AW_LOADERR_NONE,
    AW_LOADERR_NOT_FOUND,      /* LF1: no such map (what was typed) */
    AW_LOADERR_NOT_ON_DISK,    /* LF2: a map of the game this build leaves out */
    AW_LOADERR_NO_POINT,       /* LF3: a coordinate teleport whose point no map on this disk holds */
    AW_LOADERR_BROKEN,         /* LF4: the map file is damaged (bad header, short read, bad lump) */
    AW_LOADERR_MEMORY,         /* LF5: not enough memory to load it */
    AW_LOADERR_NO_SPAWN,       /* LF6: the map loaded but did not spawn */
    AW_LOADERR_TIMEOUT,        /* LF7: the load did not finish within the time limit */
    AW_LOADERR_MISSING_FILE,   /* LF8: a file the map needs (a model, a sound) is missing */
    AW_LOADERR_ERROR,          /* LF9: any other error during the load */
    AW_LOADERR_KINDS
};
/* What is wrong with a broken map file (AW_LOADERR_BROKEN). */
enum {AW_BROKEN_NONE,AW_BROKEN_HEADER,AW_BROKEN_SHORT,AW_BROKEN_LUMP,AW_BROKEN_DATA};
/* How the load ended for the player. */
enum {
    AW_WAY_NONE,      /* nothing was left: a refusal before the load, the player never moved */
    AW_WAY_BACK,      /* the way back worked: the player is where he started */
    AW_WAY_FAILED,    /* the way back failed as well: no place to stay, the load menu */
    AW_WAY_NOWHERE    /* there was no place to go back to (a save load, a start): the load menu */
};
#define AW_LOADERR_MAP 48   /* a map name (15 at most) or, for a door to a room the build did not convert, its label */
typedef struct {
    int kind;
    char command[96];               /* how the load started: as typed ("dbg tp bmcaius") or the way ("door 113893") */
    char map[AW_LOADERR_MAP];       /* the map asked for (what was typed when it is no map) */
    char place[64];                 /* its place's name, "" when not known */
    char file[64];                  /* its file, "" when not known */
    long file_bytes;                /* -1 not known */
    int broken,lump;                /* AW_BROKEN_*; the lump (Quake's numbers 0-14), -1 none */
    long offset;                    /* the file offset that was bad, -1 not known */
    long need,have;                 /* not enough memory: bytes needed and free */
    char arena[16];                 /* which memory: "hunk", "cache", "zone", "map" (the check before leaving) */
    long fast_free,chip_free;       /* the machine's free Fast and Chip RAM in bytes, -1 not known */
    float x,y;                      /* the point no map holds (original coordinates) */
    char detail[128];               /* the engine's own message */
    char from_map[AW_LOADERR_MAP];float from[3];int from_ok;   /* the place left */
    int way;                        /* AW_WAY_* */
    char back_map[AW_LOADERR_MAP];  /* the map of the way back */
    char here_map[AW_LOADERR_MAP],here_place[64];float here[3];int here_ok;   /* where the player is now */
    /* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: the error stopped the game in play, no load running (the map is the one he
     * was in): the way back loads that place again; AW_WAY_NOWHERE: the same error again soon after, the load menu */
    int in_play;
} aw_loaderr_t;

const char *AW_LoadErrCode(int kind);       /* "LF1".."LF9"; "" for none or out of range */
const char *AW_LoadErrKind(int kind);       /* "map not found", "broken map file" ... */
const char *AW_LoadErrLumpName(int lump);   /* "faces" ...; "?" out of range */
/* Copy IN into OUT (SIZE bytes) with every character a box or a console line could read as a code ('%', '^',
 * control and non-ASCII bytes) made '?'. */
void AW_LoadErrClean(char *out,int size,const char *in);
/* The reason line alone ("Broken map file (bad lump 7)."), "" for a kind without one. Returns its length. */
int AW_LoadErrReason(const aw_loaderr_t *e,char *out,int size);
/* The OK box's text, lines split by '\n': "Map <name> was not found." / "Map <name> was found but could not be
 * loaded." with the reason on the next line / "No map holds the point <X> <Y>." / "... and the way back to <map>
 * failed as well."; the code on the last error line ("Code LF4."); the last line "You are in <place>." (or, with no
 * place to stay, that a saved game is the way on). Returns its length. */
int AW_LoadErrBox(const aw_loaderr_t *e,char *out,int size);
/* One short line for the load menu's notice (at most SIZE-1, e.g. 79): the code and the map. */
int AW_LoadErrNotice(const aw_loaderr_t *e,char *out,int size);
/* The console's debug block: a head line with the code, the kind and the box's text, then the command, the map and
 * its file, the error, the memory, the place left and where the player is now. Lines end in '\n'. */
int AW_LoadErrConsole(const aw_loaderr_t *e,char *out,int size);
/* A map file's 124-byte header (Quake BSP version 29, little-endian) against the file's size, before anything is
 * left: 0 when it reads, else AW_BROKEN_HEADER (too short, another version, a negative lump) or AW_BROKEN_SHORT (a
 * lump past the end of the file: a truncated file), with *LUMP the first bad lump (-1 for the header itself). */
int AW_LoadErrMapHeader(const unsigned char *header,long header_bytes,long file_bytes,int *lump);

/* The engine's side (aw_scene.c, which links the rules above): what a map load in flight met (the first one counts),
 * and the hooks aw_loadfail.c sets: the check before anything is left (1 = refused, E filled with its kind and
 * details) and the machine's free Fast (0) or Chip (1) RAM in bytes. */
void AW_SceneLoadNote(const aw_loaderr_t *e);
extern int (*aw_load_precheck)(const char *map,aw_loaderr_t *e);
extern long (*aw_load_memory_free)(int chip);
#endif
