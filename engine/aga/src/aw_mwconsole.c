/* SPDX-License-Identifier: GPL-3.0-only */
/* The original game's console commands (MW-CONSOLE-COMMANDS-62): see aw_mwconsole.h. */
#include <stdio.h>
#include <string.h>
#include "aw_mwconsole.h"

static char fold(char c){return c>='A' && c<='Z'?(char)(c+32):c;}
static int is_space(char c){return c==' ' || c=='\t' || c==',' || c=='\r' || c=='\n';}

/* one token at *P: quoted (the quotes dropped) or bare (up to a space, a comma or "->"); 0 none */
static int token(const char **p,char *out,int capacity){
    const char *s=*p;int n=0;
    while(*s && is_space(*s))s++;
    if(!*s){*p=s;return 0;}
    if(*s=='"'){
        s++;
        while(*s && *s!='"'){if(n<capacity-1)out[n++]=*s;s++;}
        if(*s=='"')s++;
    }else while(*s && !is_space(*s) && !(s[0]=='-' && s[1]=='>')){if(n<capacity-1)out[n++]=*s;s++;}
    out[n]=0;*p=s;
    return 1;
}
int AW_MwConsoleParse(const char *text,aw_mwcon_line_t *out){
    const char *p=text,*q;char first[AW_MWCON_TEXT];int i;
    memset(out,0,sizeof(*out));
    if(!text || !token(&p,first,sizeof(first)))return 0;
    q=p;while(*q==' ' || *q=='\t')q++;
    if(q[0]=='-' && q[1]=='>'){           /* "id->Command" or "id -> Command" */
        snprintf(out->target,sizeof(out->target),"%s",first);
        p=q+2;
        if(!token(&p,first,sizeof(first)))return 0;
    }
    for(i=0;first[i];i++)out->name[i]=fold(first[i]);
    out->name[i]=0;
    while(out->args<AW_MWCON_ARGS && token(&p,out->arg[out->args],AW_MWCON_TEXT))out->args++;
    return out->name[0]!=0;
}

/* --- the aliases: the original's name, its other form, AmiWind's line (%1 %2 the arguments, as typed) --- */
typedef struct {const char *name,*other,*amiwind;int player_only;} alias_t;
static const alias_t aliases[]={
    {"tgm","togglegodmode","dbg god",0},
    {"tcl","togglecollision","noclip",0},      /* "tcl" itself is AmiWind's own command (the same switch) */
    {"coc","centeroncell","dbg tp \"%1\"",0},
    {"fixme",NULL,"dbg unstuck",0},
    {"tm","togglemenus","dbg killhud",0},
    {"tvm","togglevanitymode","dbg vanitycam on",0},
    {"setlevel",NULL,"dbg setlvl %1",1},
    {"enablenamemenu",NULL,"dbg quickchar name",0},
    {"enableracemenu",NULL,"dbg characterchange race",0},
    {"enableclassmenu",NULL,"dbg quickchar class",0},
    {"enablebirthmenu",NULL,"dbg quickchar birthsign",0},
    {"enablestatreviewmenu",NULL,"dbg quickchar review",0},
    /* v0.0.63 (MW-CONSOLE-COMMANDS-62): the original's console-only toggles mapped to AmiWind's own switches */
    {"tdt","toggledebugtext","dbg hud",0},               /* the debug text: AmiWind's debug HUD (toggles) */
    {"tst","togglestats","dbg fps",0},                   /* the frame statistics: the FPS counter (toggles) */
    {"tcs","togglecombatstats","toggle aw_combat_readout",0},  /* the combat rolls on the console */
    {"tl","togglelights","toggle r_fullbright",0},       /* the lighting off and on (Quake's full-bright drawing) */
    {"repairedonme",NULL,"echo 0",0},                    /* OpenMW 0.51 OpRepairedOnMe: always 0 */
    /* v0.0.64 (CONSOLE-QUEST-READS-64): the journal as typed, through the same host route a script's Journal and
     * SetJournalIndex take (aw_mwhost.c status "call journal"); the reads print the index kept now */
    {"journal",NULL,"aw_mwscript_status call journal \"%1\" %2",0},
    {"setjournalindex",NULL,"aw_mwscript_status call setjournalindex \"%1\" %2",0},
    {"getjournalindex",NULL,"aw_mwscript_status call getjournalindex \"%1\"",0},
    {"getpcexpelled",NULL,"aw_mwscript_status call pcexpelled \"%1\"",0},   /* the read form of PCExpelled */
};
#define NALIAS ((int)(sizeof(aliases)/sizeof(aliases[0])))
const char *AW_MwConsoleAlias(int n,const char **amiwind){
    int k=n/2;
    if(n<0 || k>=NALIAS){if(amiwind)*amiwind=NULL;return "";}
    if(amiwind)*amiwind=aliases[k].amiwind;
    return n%2?(aliases[k].other?aliases[k].other:aliases[k].name):aliases[k].name;
}
static int is_player(const char *target){
    static const char me[]="player";int i;
    for(i=0;target[i] && me[i] && fold(target[i])==me[i];i++){}
    return !target[0] || (i==6 && !target[6]);
}
static void fill(char *out,int capacity,const char *form,const aw_mwcon_line_t *l){
    int o=0;
    for(;*form && o<capacity-1;form++){
        if(form[0]=='%' && form[1]>='1' && form[1]<='4'){
            const char *a=l->arg[form[1]-'1'];
            while(*a && o<capacity-1)out[o++]=*a++;
            form++;continue;
        }
        out[o++]=*form;
    }
    out[o]=0;
    /* an argument not given: its empty quotes and the spaces after the words go */
    for(;;){
        if(o>0 && out[o-1]==' ')out[--o]=0;
        else if(o>1 && out[o-1]=='"' && out[o-2]=='"'){o-=2;out[o]=0;}
        else break;
    }
}

/* --- the stat functions: Set/Mod/Get/ModCurrent + a stat's name (AWA_* numbers, aw_actorstate.h) --- */
static const char *const stat_names[]={
    "strength","intelligence","willpower","agility","speed","endurance","personality","luck",
    "block","armorer","mediumarmor","heavyarmor","bluntweapon","longblade","axe","spear","athletics","enchant",
    "destruction","alteration","illusion","conjuration","mysticism","restoration","alchemy","unarmored","security",
    "sneak","acrobatics","lightarmor","shortblade","marksman","mercantile","speechcraft","handtohand",
    "health","magicka","fatigue"};
#define NSTAT ((int)(sizeof(stat_names)/sizeof(stat_names[0])))
static int stat_of(const char *name,int *verb){
    static const struct {const char *prefix;int verb;} verbs[]={
        {"modcurrent",AW_MWCON_MODCURRENT},{"set",AW_MWCON_SET},{"mod",AW_MWCON_MOD},{"get",AW_MWCON_GET}};
    int v,s;
    for(v=0;v<4;v++){
        size_t n=strlen(verbs[v].prefix);
        if(strncmp(name,verbs[v].prefix,n))continue;
        for(s=0;s<NSTAT;s++)if(!strcmp(name+n,stat_names[s])){
            if(verbs[v].verb==AW_MWCON_MODCURRENT && s<35)return -1;   /* ModCurrent: the dynamic stats only */
            *verb=verbs[v].verb;return s;
        }
    }
    return -1;
}
static int number(const char *s,float *out){
    float v=0,scale=0;int sign=1,digits=0;
    if(*s=='-'){sign=-1;s++;}else if(*s=='+')s++;
    for(;*s;s++){
        if(*s>='0' && *s<='9'){digits++;if(scale>0){v+=(float)(*s-'0')*scale;scale*=0.1f;}else v=v*10+(float)(*s-'0');}
        else if(*s=='.' && scale==0)scale=0.1f;
        else return 0;
    }
    *out=(float)sign*v;
    return digits>0;
}

/* --- the commands run through the host on any target: the original's name, the AW_MWCON_* number, least arguments --- */
static const struct {const char *name;int command,least;} commands[]={
    {"additem",AW_MWCON_ADDITEM,1},{"removeitem",AW_MWCON_REMOVEITEM,1},{"getitemcount",AW_MWCON_GETITEMCOUNT,1},
    {"equip",AW_MWCON_EQUIP,1},{"addspell",AW_MWCON_ADDSPELL,1},{"removespell",AW_MWCON_REMOVESPELL,1},
    {"enable",AW_MWCON_ENABLE,0},{"disable",AW_MWCON_DISABLE,0},{"getdisabled",AW_MWCON_GETDISABLED,0},
    {"position",AW_MWCON_POSITION,3},{"positioncell",AW_MWCON_POSITIONCELL,4},{"setpos",AW_MWCON_SETPOS,2},
    {"getpos",AW_MWCON_GETPOS,1},{"setangle",AW_MWCON_SETANGLE,2},{"getangle",AW_MWCON_GETANGLE,1},
    {"aiwander",AW_MWCON_AIWANDER,3},{"aitravel",AW_MWCON_AITRAVEL,3},{"aifollow",AW_MWCON_AIFOLLOW,2},
    {"aiescort",AW_MWCON_AIESCORT,5},
    /* v0.0.68: ChangeWeather REGION WEATHER, ModRegion REGION [CHANCES...] (OpenMW compiler extensions0.cpp: "Sl",
     * "S/llllllllllX"): the region is a typed id, found by the host in the region catalogue */
    {"changeweather",AW_MWCON_CHANGEWEATHER,2},{"modregion",AW_MWCON_MODREGION,1},
    /* v0.0.68: BecomeWerewolf, SetWerewolfAcrobatics (OpenMW extensions0.cpp 499, 502: no arguments; the player or the
     * target by id->); UndoWerewolf needs nothing compiled and runs through the function table */
    {"becomewerewolf",AW_MWCON_BECOMEWEREWOLF,0},{"setwerewolfacrobatics",AW_MWCON_SETWEREWOLFACROBATICS,0},
    /* v0.0.68 (CONSOLE-STARTSCRIPT-STOPSCRIPT-67): StartScript NAME, StopScript NAME, ScriptRunning NAME (OpenMW
     * extensions0.cpp: a global script by its id) */
    {"startscript",AW_MWCON_STARTSCRIPT,1},{"stopscript",AW_MWCON_STOPSCRIPT,1},{"scriptrunning",AW_MWCON_SCRIPTRUNNING,1},
    /* v0.0.68: the sounds, StreamMusic, SayDone (OpenMW extensions0.cpp 355-367: "cXX" the sound, "cff" the sound,
     * volume and pitch, "S" the music file, SayDone none); StopSound stays AmiWind's own stopsound (a collision); the
     * loop forms stay planned (no script keeps a typed loop going) */
    {"playsound",AW_MWCON_PLAYSOUND,1},{"playsoundvp",AW_MWCON_PLAYSOUNDVP,3},{"playsound3d",AW_MWCON_PLAYSOUND3D,1},
    {"playsound3dvp",AW_MWCON_PLAYSOUND3DVP,3},{"getsoundplaying",AW_MWCON_GETSOUNDPLAYING,1},
    {"streammusic",AW_MWCON_STREAMMUSIC,1},{"saydone",AW_MWCON_SAYDONE,0},
    /* v0.0.68: PlaceAtPC and PlaceAtMe ID COUNT DISTANCE DIRECTION, PlaceItem ID X Y Z ZROT (OpenMW extensions0.cpp
     * 525-527: "clflX", "cffffX"); PlaceItemCell stays planned (its cell is the compiler's) */
    {"placeatpc",AW_MWCON_PLACEATPC,4},{"placeatme",AW_MWCON_PLACEATME,4},{"placeitem",AW_MWCON_PLACEITEM,5},
    /* v0.0.68: the spells, the effects, the items, the topics (OpenMW extensions0.cpp 113, 167, 237-238, 268, 271, 278,
     * 455: RemoveSpellEffects, ExplodeSpell, GetSpellEffects, HasItemEquipped "c", GetEffect and AddTopic "S", Drop "cl",
     * Cast "SS") */
    {"removespelleffects",AW_MWCON_REMOVESPELLEFFECTS,1},{"explodespell",AW_MWCON_EXPLODESPELL,1},
    {"getspelleffects",AW_MWCON_GETSPELLEFFECTS,1},{"geteffect",AW_MWCON_GETEFFECT,1},
    {"hasitemequipped",AW_MWCON_HASITEMEQUIPPED,1},{"drop",AW_MWCON_DROP,2},{"addtopic",AW_MWCON_ADDTOPIC,1},
    {"cast",AW_MWCON_CAST,2}};
#define NCOMMAND ((int)(sizeof(commands)/sizeof(commands[0])))
const char *AW_MwConsoleCommandName(int command,int *least){
    int k;
    for(k=0;k<NCOMMAND;k++)if(commands[k].command==command){if(least)*least=commands[k].least;return commands[k].name;}
    return NULL;
}
int AW_MwConsoleRun(const char *text,const aw_mwcon_host_t *host){
    /* static: the 68k stack is small (the line is 964 bytes with its 13 arguments since v0.0.68); a line runs whole
     * before the next one is read (an AmiWind line it becomes is queued, never run inside this call) */
    static aw_mwcon_line_t l;static char line[512];int k,verb,stat;float value;
    if(!host || !AW_MwConsoleParse(text,&l))return 0;
    for(k=0;k<NCOMMAND;k++){
        if(strcmp(l.name,commands[k].name))continue;
        if(l.args<commands[k].least){
            snprintf(line,sizeof(line),"%s: %d argument%s.\n",l.name,commands[k].least,commands[k].least>1?"s":"");
            host->print(line);return 1;
        }
        line[0]=0;
        if(!host->command(l.target,commands[k].command,&l,line,sizeof(line))){
            snprintf(line,sizeof(line),"%s: no such reference here: %s\n",l.name,l.target[0]?l.target:"(the target)");
            host->print(line);return 1;
        }
        if(line[0])host->print(line);
        return 1;
    }
    for(k=0;k<NALIAS;k++){
        if(strcmp(l.name,aliases[k].name) && (!aliases[k].other || strcmp(l.name,aliases[k].other)))continue;
        if(aliases[k].player_only && !is_player(l.target)){
            snprintf(line,sizeof(line),"%s: only the player can be the target here (player->%s).\n",l.name,l.name);
            host->print(line);return 1;
        }
        fill(line,sizeof(line),aliases[k].amiwind,&l);
        host->exec(line);
        return 1;
    }
    if(!strcmp(l.name,"coe") || !strcmp(l.name,"centeronexterior")){   /* an exterior cell's grid X, Y: its centre */
        float x,y;
        if(l.args<2 || !number(l.arg[0],&x) || !number(l.arg[1],&y)){host->print("coe: two numbers, the cell's X and Y.\n");return 1;}
        snprintf(line,sizeof(line),"dbg tp %ld %ld",(long)x*8192L+4096L,(long)y*8192L+4096L);
        host->exec(line);
        return 1;
    }
    if((stat=stat_of(l.name,&verb))>=0){
        value=0;
        if(verb!=AW_MWCON_GET && (l.args<1 || !number(l.arg[0],&value))){
            snprintf(line,sizeof(line),"%s: one number.\n",l.name);host->print(line);return 1;}
        if(!host->stat(l.target,verb,stat,&value)){
            snprintf(line,sizeof(line),"%s: no such actor here: %s\n",l.name,l.target[0]?l.target:"(the target)");
            host->print(line);return 1;
        }
        if(verb==AW_MWCON_GET){snprintf(line,sizeof(line),"%s -> %g\n",l.name,(double)value);host->print(line);}
        return 1;
    }
    if(host->table){
        line[0]=0;
        k=host->table(l.target,&l,line,sizeof(line));
        if(k<0)return 0;
        if(!k)snprintf(line,sizeof(line),"%s: no such reference here: %s\n",l.name,l.target[0]?l.target:"(the target)");
        if(line[0])host->print(line);
        return 1;
    }
    return 0;
}
