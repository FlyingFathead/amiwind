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
/* The startup screen's last line, drawn by the engine in the console font
 * under the logo stream's held last frame; Enter starts the game (aw_movie.c;
 * tools/miniwind.py PROMPT, PROMPT_Y). */
#define AW_MINIWIND_PROMPT "Press ENTER to start"
#define AW_MINIWIND_PROMPT_Y 184
typedef struct {
    int valid;
    char town[AW_MINIWIND_TOWN],title[AW_MINIWIND_TITLE],features[AW_MINIWIND_FEATURES];
} aw_miniwind_t;
/* Parse the notice file's bytes; 1 and every field set when valid, else 0. */
int AW_MiniwindParse(const char *text,int size,aw_miniwind_t *out);
/* Read miniwind.txt once at start-up; absent in every normal build. */
void AW_MiniwindInit(void);
int AW_MiniwindActive(void);
const aw_miniwind_t *AW_Miniwind(void);
/* The command after the startup logo: the quick start of a partial-area
 * build, the main menu otherwise. */
const char *AW_MiniwindAfterLogo(void);
#endif
