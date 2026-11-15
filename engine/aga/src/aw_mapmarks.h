/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's own map markers (MAP-MULTI-MARKERS-66) and the hot marker (NAV-HOT-MARKER-COMPASS-66).
 *
 * Up to the allowance of named markers (the setting aw_map_markers_max, 1..AW_MAPMARKS_MAX, default
 * AW_MAPMARKS_DEFAULT), each a point in the original's world units and a name of up to AW_MAPMARK_NAME characters. The
 * list grows as markers are set (AW_TryRealloc), so an unused allowance costs nothing. One hot marker beside it: no
 * name, never in the list. Saved with the game in its own block (AWMK, aw_save_codec.c feature 2048): about 10 KB
 * with the default allowance full. New Game empties both. No engine dependencies besides the allocator (host-tested:
 * tests/aga_mapmarks_test.c).
 * SAVE-STATE-FIXED-CAPS-66 (the save contract, 2026-11-14): AW_MAPMARKS_MAX is a damaged-file guard and the most the
 * setting allows, no longer the default: a save with more markers than this build's allowance still loads them all.
 */
#ifndef AW_MAPMARKS_H
#define AW_MAPMARKS_H

#define AW_MAPMARKS_DEFAULT 256
#define AW_MAPMARKS_MAX 4096
#define AW_MAPMARK_NAME 32

typedef struct {float x,y;char name[AW_MAPMARK_NAME+1];} aw_mapmark_t;

void AW_MapMarksReset(void);              /* New Game: no marker, no hot marker, nothing pending */
void AW_MapMarksSetMax(int most);         /* the allowance (clamped 1..AW_MAPMARKS_MAX); markers past it stay, no new ones */
int AW_MapMarksMax(void);
int AW_MapMarksCount(void);
const aw_mapmark_t *AW_MapMark(int i);    /* NULL past the end */
/* a new marker at X, Y (NAME cut to AW_MAPMARK_NAME; NULL or "" = "Marker N"): its index; -1 the allowance is
 * used up, -2 no memory */
int AW_MapMarkAdd(float x,float y,const char *name);
int AW_MapMarkRename(int i,const char *name);   /* 1 done; an empty name keeps the old one */
int AW_MapMarkDelete(int i);                    /* 1 done; the later markers move up one */
void AW_MapMarksClear(void);                    /* every named marker (the hot one stays) */
/* the first marker at or after FROM whose name holds TEXT (letters and digits, case ignored); -1 none */
int AW_MapMarkFind(const char *text,int from);
/* a marker by its number (1-based) or its whole name (case ignored), else the first whose name holds it; -1 none */
int AW_MapMarkLookup(const char *text);
/* 1 when NAME holds TEXT, letters and digits only, case ignored ("" holds every name) */
int AW_MapMarkMatches(const char *name,const char *text);

/* the hot marker */
int AW_MapHotGet(float *x,float *y);      /* 1 when set */
void AW_MapHotSet(float x,float y);
void AW_MapHotOff(void);

/* the saved block: "AWMK" u8 version 1, u16 count, u8 hot (0/1), [i32 hot x, y], then per marker i32 x, y, u8 name
 * length, the name. Encode: bytes written (OUT NULL: bytes needed), 0 when there is nothing to save, -1 no room.
 * Decode: 1 when P holds a whole, good block of N bytes; COMMIT 1 keeps it as the pending load (P NULL: the save had
 * none, the pending load is empty). Loaded: the pending load becomes the game's. */
int AW_MapMarksEncode(unsigned char *out,int capacity);
int AW_MapMarksDecode(const unsigned char *p,int n,int commit);
void AW_MapMarksLoaded(void);
#endif
