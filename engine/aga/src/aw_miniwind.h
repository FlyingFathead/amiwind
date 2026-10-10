/* SPDX-License-Identifier: GPL-2.0-or-later
 * Partial-area playtest builds (the builder's "MiniWind" build type). */
#ifndef AW_MINIWIND_H
#define AW_MINIWIND_H
#define AW_MINIWIND_FILE "miniwind.txt"
/* Buffer sizes, one byte for the terminator (tools/miniwind.py TOWN_CHARS,
 * TITLE_CHARS, FEATURES_CHARS). */
#define AW_MINIWIND_TOWN 16
#define AW_MINIWIND_TITLE 80
#define AW_MINIWIND_FEATURES 512
/* Optional quick-start lines of a direct-start build (tools/direct_start.py):
 * "start town NAME" or "start map MAP X Y Z YAW", and
 * "character RACE|CLASS|BIRTHSIGN|m or f|NAME". */
#define AW_MINIWIND_START 96
#define AW_MINIWIND_CHARACTER 128
/* Optional "header TEXT": the main menu's top line in a test build, e.g.
 * "MINIWIND TEST UNIT: <description>" (tools/miniwind.py HEADER_CHARS). */
#define AW_MINIWIND_HEADER 96
/* "boot": dbg commands a sandbox runs once on arrival, separated by ";" (tools/miniwind.py BOOT_CHARS + 1). */
#define AW_MINIWIND_BOOT 160
/* The startup screen's last line, drawn by the engine in the console font
 * under the logo stream's held last frame; Enter starts the game (aw_movie.c;
 * tools/miniwind.py PROMPT, PROMPT_Y). */
#define AW_MINIWIND_PROMPT "Press ENTER to start"
#define AW_MINIWIND_PROMPT_Y 184
typedef struct {
    int valid;
    char town[AW_MINIWIND_TOWN],title[AW_MINIWIND_TITLE],features[AW_MINIWIND_FEATURES];
    char start[AW_MINIWIND_START],character[AW_MINIWIND_CHARACTER],header[AW_MINIWIND_HEADER];
    char boot[AW_MINIWIND_BOOT];
} aw_miniwind_t;
/* The start line, parsed: kind 1 town (map = the town), kind 2 map at point/yaw; 0 none or invalid. */
typedef struct {int kind;char map[32];float point[3],yaw;} aw_quick_start_t;
int AW_MiniwindStart(const aw_miniwind_t *m,aw_quick_start_t *out);
/* The character line, split: 1 and the five fields when valid. */
int AW_MiniwindCharacter(const aw_miniwind_t *m,char *race,char *clas,char *birth,int *female,char *name,int size);
/* Parse the notice file's bytes; 1 and every field set when valid, else 0. */
int AW_MiniwindParse(const char *text,int size,aw_miniwind_t *out);
/* Read miniwind.txt once at start-up; absent in every normal build. */
void AW_MiniwindInit(void);
int AW_MiniwindActive(void);
const aw_miniwind_t *AW_Miniwind(void);
/* The command after the startup logo: the quick start of a partial-area
 * build, the main menu otherwise. */
const char *AW_MiniwindAfterLogo(void);
/* The header line wrapped for the title screen (aw_menu.c): at most two lines of
 * width pixels in the game font, the second ending in "..." when cut. Line count. */
int AW_MenuHeaderLines(const char *text,int width,char lines[2][AW_MINIWIND_HEADER]);
#endif
