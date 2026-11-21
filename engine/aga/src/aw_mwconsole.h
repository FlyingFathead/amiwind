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
      AW_MWCON_HASITEMEQUIPPED,AW_MWCON_DROP,AW_MWCON_ADDTOPIC,AW_MWCON_CAST,AW_MWCON_COMMANDS};

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
