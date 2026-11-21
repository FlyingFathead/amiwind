/* SPDX-License-Identifier: GPL-3.0-only */
/* The original game's console commands in AmiWind's console (MW-CONSOLE-COMMANDS-62, v0.0.63).
 *
 * A console line the engine does not know (no command, alias or cvar of that name) comes here. Its syntax is the
 * original's: an optional target "id->" (spaces around -> allowed), the command, its arguments separated by spaces
 * and/or commas, an id with spaces in quotes, all case-insensitive. The command is found in a small table:
 *  - an alias of an AmiWind command (tgm = dbg god, coc = dbg tp, ...): the line becomes ours, never a second copy;
 *  - a stat function (SetStrength, ModBlock, GetHealth, ...): run through the MWScript host, the same call a compiled
 *    script line makes (aw_mwhost.c host_actor);
 * the census of every original command and its state is config/mwscript-console.json (tests/test_mwscript_console.py). */
#ifndef AW_MWCONSOLE_H
#define AW_MWCONSOLE_H

/* v0.0.68 (MW-CONSOLE-COMMANDS-62): 13 arguments, the most a line of the original takes (OpenMW
 * components/compiler/extensions0.cpp 38 "aiwander" fff/llllllllll: range, duration, time, the unused chance, eight
 * idles, reset; 346 "modregion" S/llllllllllX: the region and ten chances). 6 before: ModRegion's chances past the
 * fifth and AIWander's idles past the third were dropped */
#define AW_MWCON_ARGS 13
#define AW_MWCON_TEXT 64

typedef struct {
    char target[AW_MWCON_TEXT];          /* "" none (the player) */
    char name[AW_MWCON_TEXT];            /* folded to lower case */
    char arg[AW_MWCON_ARGS][AW_MWCON_TEXT];
    int args;
} aw_mwcon_line_t;

/* the stat calls' verbs (as aw_mwvm.h AWV_*: 0 get, then set, mod, mod current) */
enum {AW_MWCON_GET, AW_MWCON_SET, AW_MWCON_MOD, AW_MWCON_MODCURRENT};

/* the commands run through the MWScript host on any target (aw_mwhost.c console_command); v0.0.68: ChangeWeather and
 * ModRegion, the region by its id in the compiled file's region table (RGNS), then the call a compiled line makes;
 * BecomeWerewolf and SetWerewolfAcrobatics, the werewolf's game settings from the compiled file (WERE); StartScript,
 * StopScript and ScriptRunning, the global script by its name (the compiled file's SCRH name hashes); the sounds
 * (PlaySound, PlaySoundVP, PlaySound3D, PlaySound3DVP, GetSoundPlaying), StreamMusic and SayDone, the sound or music
 * row by its name */
enum {AW_MWCON_ADDITEM,AW_MWCON_REMOVEITEM,AW_MWCON_GETITEMCOUNT,AW_MWCON_EQUIP,AW_MWCON_ADDSPELL,
      AW_MWCON_REMOVESPELL,AW_MWCON_ENABLE,AW_MWCON_DISABLE,AW_MWCON_GETDISABLED,AW_MWCON_POSITION,
      AW_MWCON_POSITIONCELL,AW_MWCON_SETPOS,AW_MWCON_GETPOS,AW_MWCON_SETANGLE,AW_MWCON_GETANGLE,AW_MWCON_AIWANDER,
      AW_MWCON_AITRAVEL,AW_MWCON_AIFOLLOW,AW_MWCON_AIESCORT,AW_MWCON_CHANGEWEATHER,AW_MWCON_MODREGION,
      AW_MWCON_BECOMEWEREWOLF,AW_MWCON_SETWEREWOLFACROBATICS,AW_MWCON_STARTSCRIPT,AW_MWCON_STOPSCRIPT,
      AW_MWCON_SCRIPTRUNNING,AW_MWCON_PLAYSOUND,AW_MWCON_PLAYSOUNDVP,AW_MWCON_PLAYSOUND3D,AW_MWCON_PLAYSOUND3DVP,
      AW_MWCON_GETSOUNDPLAYING,AW_MWCON_STREAMMUSIC,AW_MWCON_SAYDONE,AW_MWCON_PLACEATPC,AW_MWCON_PLACEATME,
      AW_MWCON_PLACEITEM,AW_MWCON_REMOVESPELLEFFECTS,AW_MWCON_EXPLODESPELL,AW_MWCON_GETSPELLEFFECTS,AW_MWCON_GETEFFECT,
      AW_MWCON_HASITEMEQUIPPED,AW_MWCON_DROP,AW_MWCON_ADDTOPIC,AW_MWCON_CAST,AW_MWCON_PLACEITEMCELL,
      AW_MWCON_AIFOLLOWCELL,AW_MWCON_AIESCORTCELL,AW_MWCON_GETPCCELL,AW_MWCON_COMMANDS};

/* --- v0.0.68 (MW-CONSOLE-COMMANDS-62, the cell table): the compiled file's CELN and CELG sections (tools/mwscript/
 * awms.py cell_rows, grid_rows), read through the host, and what a typed PositionCell, PlaceItemCell, AIFollowCell or
 * AIEscortCell works out from a row, by the compiler's own rules (tools/mwscript/codegen.py Program.player_move,
 * actor_move, place, ai_cell), so a typed line does what the same compiled line does. Nothing kept in memory. --- */
#define AW_MWCON_CELL_ROOM 1           /* a CELN row's kind: an interior cell (awms.py CELL_ROOM) */
#define AW_MWCON_CELL_EXTERIOR 2       /* an exterior cell's name (OpenMW's findCell finds an exterior by it) */
#define AW_MWCON_CELL_PRESENTED 3      /* a district the build presents as exterior cells: its move */
#define AW_MWCON_CELL_NO_MAP 1         /* a row's flag: the room has no map in the repo's room lists */
#define AW_MWCON_MOVE_OUTDOORS 1       /* = aw_mwcode.h AWM_MOVE_OUTDOORS */
#define AW_MWCON_MOVE_ROOM 2           /* = aw_mwcode.h AWM_MOVE_ROOM */
#define AW_MWCON_CELL_BYTES 24
typedef struct {
    int kind,flags,number;   /* AW_MWCON_CELL_*; the room's stable number (the room map's _aw_cell_int), 0 none */
    int map,name;            /* string indexes: the room map's name (-1 none), the cell's name as its record writes it */
    float offset[3];         /* a room's recentring (subtracted first), a presented district's move (x and y added) */
} aw_mwcon_cell_t;
typedef struct {
    int (*read)(void *user,unsigned long offset,unsigned char *out,unsigned long bytes);   /* 1 read */
    int (*string)(void *user,int index,char *out,int capacity);                           /* its length, 0 none */
    void *user;
    unsigned long celn,celn_rows,celg,celg_rows;   /* the sections' offsets for READ and their rows (0: none) */
} aw_mwcon_cells_t;
/* the row of the cell named TYPED (any case): 1 found, 0 no cell of the game has that name, -1 no table */
int AW_MwConsoleCellFind(const aw_mwcon_cells_t *t,const char *typed,aw_mwcon_cell_t *out);
/* the name of the room NUMBER (CELN) or of the exterior cell X, Y (CELG; OpenMW's getCellName) into OUT: 1 found */
int AW_MwConsoleCellRoomName(const aw_mwcon_cells_t *t,int number,char *out,int capacity);
int AW_MwConsoleCellGridName(const aw_mwcon_cells_t *t,int x,int y,char *out,int capacity);
/* OpenMW 0.51 cellextensions.cpp OpGetPCCell: 1 when the cell name CURRENT starts with TYPED, any case */
int AW_MwConsoleCellMatches(const char *typed,const char *current);
/* the line's verb: the player's PositionCell, anything else's, PlaceItemCell of an actor or object and of an item,
 * AIFollowCell, AIEscortCell */
enum {AW_MWCON_CELL_PLAYER,AW_MWCON_CELL_ACTOR,AW_MWCON_CELL_PLACE_ACTOR,AW_MWCON_CELL_PLACE_ITEM,
      AW_MWCON_CELL_FOLLOW,AW_MWCON_CELL_ESCORT};
/* what VERB does with FOUND (AW_MwConsoleCellFind's answer, 1 or 0) and ROW; IN: x, y, z (the original's units) and
 * the rotation as typed (degrees; PositionCell of anything but the player: minutes of arc). OUT the point (a room: its
 * map's own units, a placed item and outdoors: the original's), *YAW (Quake's, degrees), *KIND (AW_MWCON_MOVE_*),
 * *NUMBER (the room's number, 0 outdoors). 1 a move, 0 nothing (a cell the game has not: OpenMW does nothing then),
 * -1 the player into a room this image has no map for (the compiled line stays "not yet" then too) */
int AW_MwConsoleCellMove(int verb,int found,const aw_mwcon_cell_t *row,const float in[4],float out[3],float *yaw,
                         int *kind,int *number);

typedef struct {
    void (*exec)(const char *text);                       /* an AmiWind console line */
    /* COMMAND (AW_MWCON_*) on TARGET ("" the console target, else the player; "player"; an id) with LINE's arguments;
     * ANSWER a line to show ("" none); 1 done, 0 no such target */
    int (*command)(const char *target,int command,const aw_mwcon_line_t *line,char *answer,int capacity);
    /* a stat of TARGET (as for command): AWA_* STAT, VERB AW_MWCON_*; 1 done, VALUE out for a get */
    int (*stat)(const char *target,int verb,int stat,float *value);
    void (*print)(const char *text);
    /* any other name: the compiler's function table on disk (id1/mwconsole-functions.txt); -1 no such function,
     * 0 no such target, 1 done (ANSWER as for command) */
    int (*table)(const char *target,const aw_mwcon_line_t *line,char *answer,int capacity);
} aw_mwcon_host_t;

/* 1 parsed (a name found), 0 not a line of the original's form */
int AW_MwConsoleParse(const char *text,aw_mwcon_line_t *out);
/* 1 the line was the original's command and was run (or answered), 0 not one (the caller says Unknown command) */
int AW_MwConsoleRun(const char *text,const aw_mwcon_host_t *host);
/* the engine's console: the host above with the engine's own calls */
int AW_MwConsoleLine(const char *text);
/* the console target's id for the prompt ("" none: lines run on the player); aw_mwhost.c */
const char *AW_MwConsoleTarget(void);
/* dbg help mw / dbg mw help: the original commands' list, paged from id1/mwconsole-help.txt (aw_console.c) */
void AW_MwConsoleHelp(void);
/* the name of COMMAND (AW_MWCON_*) as the original spells it, its least argument count */
const char *AW_MwConsoleCommandName(int command,int *least);
/* the table, for the census test and the help: the N-th alias name ("" past the end), its AmiWind line */
const char *AW_MwConsoleAlias(int n,const char **amiwind);

#endif
