/* SPDX-License-Identifier: GPL-2.0-or-later
 * Space-separated diagnostics and an opaque palette-based console backdrop.
 * Background: no disk reads, alpha blending or extra framebuffer.
 * Explicit font changes read one atlas from disk.
 */
#include "quakedef.h"
#include "aw_tryalloc.h"
#include "aw_mwconsole.h"
static cvar_t colour={"_aw_console_colour","255",true};
extern int scr_copyeverything;
extern byte *draw_chars;
/* Command/help metadata belongs on disk, not in a permanently resident table.
 * Read on submitted dbg commands/help only; opening/typing does no catalogue I/O.
 * Handler code and Quake's small registered-command list remain resident.
 * Honor COM_FOpenFile's member size: FILE may point inside a larger PAK. */
#define DEBUG_LINE 384
#define DEBUG_BYTES 65536
extern int con_linewidth;
typedef struct {char *group,*words,*command,*arguments;} route_t;
static int catalogue_line(FILE *f,int *left,char *line) {
    int n=0,c;
    if(!*left)return 0;
    while(*left>0){
        c=fgetc(f);--*left;
        if(c==EOF)return -1;
        if(c=='\n'){line[n]=0;return 1;}
        if(c=='\r')continue;
        if(c<32 || c>126 || n>=DEBUG_LINE-1)return -1;
        line[n++]=(char)c;
    }
    line[n]=0;return 1;
}
static FILE *catalogue_open(int *left,char *line) {
    FILE *f=NULL;*left=COM_FOpenFile("debug-commands.txt",&f);
    if(!f || *left<6 || *left>DEBUG_BYTES ||
       catalogue_line(f,left,line)!=1 || strcmp(line,"AWDC1")){
        if(f)fclose(f);
        return NULL;
    }
    return f;
}
static int catalogue_route(char *line,route_t *r) {
    char *p,*fields[4];int i,n;
    fields[0]=line;
    for(i=1;i<4;i++){
        p=strchr(fields[i-1],'|');if(!p)return 0;
        *p=0;fields[i]=p+1;
    }
    if(strchr(fields[3],'|') || !*fields[0] || strlen(fields[0])>31 ||
       !*fields[1] || strlen(fields[1])>63 || !*fields[2] || strlen(fields[2])>63)return 0;
    /* Catalogue command text cannot inject separators, quotes or new commands. */
    for(i=1;i<=2;i++){
        n=(int)strlen(fields[i]);
        for(p=fields[i];*p;p++)if(!((*p>='a'&&*p<='z') ||
            (*p>='0'&&*p<='9') || *p=='_' || (i==1 && *p==' ')))return 0;
        if(fields[i][0]==' ' || fields[i][n-1]==' ' || strstr(fields[i],"  "))return 0;
    }
    r->group=fields[0];r->words=fields[1];r->command=fields[2];r->arguments=fields[3];
    return 1;
}
static int route_match(char *words,int argc,char **argv,int start) {
    int j=start,n;
    while(*words && j<argc){
        n=0;while(words[n] && words[n]!=' ')n++;
        if((int)strlen(argv[j])!=n || Q_strncasecmp(words,argv[j],n))return 0;
        words+=n;if(*words==' ')words++;j++;
    }
    return *words?0:j;
}
/* DBG-SUPERSPEED-62: every on/off debug command turns the other way when typed bare. A pure on/off entry is one whose
 * help starts with the switch words only (on/off, true/false, 1/0, 0/1, "or", commas), not followed by another choice
 * ("/ list"). Bare, a route onto a setting gets the other value of that setting; a route onto a command whose state
 * is a setting (the table) gets "on" or "off" by that setting; commands that turn themselves (god, photomode,
 * crosshair, noburden, superspeed, the debug overlays) get nothing added. tests/aga_console_test.c checks every pure
 * on/off entry of the catalogue. */
static const char *const toggle_state[][2]={
    {"footsteps","aw_player_footsteps"},{"music","aw_music"},{"worldbounds","aw_world_bounds"},
    {"headlamp","aw_headlamp"},{"hlamp","aw_headlamp"},{"ui targetnames","aw_target_names"},{"logs live","aw_logs_live"},
    {"camera parts","aw_player_body_parts"},{"camera hands","aw_hand_parts"},{"camera fpview","aw_fp_view"},
    {"ui topiccolours","aw_dialogue_topic_colours"}};
int AW_DebugPureToggle(const char *a);
int AW_DebugPureToggle(const char *a) {
    int words=0,n;
    if(!a)return 0;
    if(*a=='[')a++;
    for(;;){
        while(*a==' ' || *a==',')a++;
        for(n=0;a[n] && a[n]!=' ' && a[n]!=',' && a[n]!=';' && a[n]!=']';n++);
        if(!n)break;
        if((n==6 && !strncmp(a,"on/off",6)) || (n==10 && !strncmp(a,"true/false",10)) ||
           (n==3 && (!strncmp(a,"1/0",3) || !strncmp(a,"0/1",3))) || (n==2 && !strncmp(a,"or",2))){words++;a+=n;continue;}
        if(*a=='/')return 0;                    /* another choice follows: not a plain switch */
        break;
    }
    return words>0;
}
const char *AW_DebugToggleState(const char *words,const char *command);
const char *AW_DebugToggleState(const char *words,const char *command) {
    int i;
    if(Cvar_FindVar((char *)command))return command;
    for(i=0;i<(int)(sizeof(toggle_state)/sizeof(toggle_state[0]));i++)if(!strcmp(words,toggle_state[i][0]))return toggle_state[i][1];
    return NULL;
}
static int route_format(route_t *r,int argc,char **argv,int j,char *out,int capacity) {
    int used,n,k,setting,quoted,spaced;char *token;const char *flip;
    if(!strcmp(r->command,"aw_teleport") && argc-j>3)return 0;   /* dbg tp X Y [Z] */
    if(!strcmp(r->command,"aw_shroomtracker") && argc!=j)return 0;
    if(!strcmp(r->command,"aw_shroompicker")){
        if(argc-j>1)return 0;
        if(argc>j && strcmp(argv[j],"list")){
            n=0;
            for(token=argv[j];*token;token++){
                if(*token<'0'||*token>'9' || n>10)return 0;
                n=n*10+*token-'0';
            }
            if(n<1 || n>10)return 0;
        }
    }
    /* dbg fog rule / dbg cut groups: switches in aw_cull's upper bits
     * (quakedef.h AW_CULL_*), so they need no registry entry of their own;
     * the far test in the low bits is kept. No argument prints aw_cull. */
    if(!strcmp(r->command,"aw_cull") && (!strcmp(r->words,"fog rule") || !strcmp(r->words,"cut groups"))){
        int bit=r->words[0]=='f'?AW_CULL_FOG_RULE:AW_CULL_GROUPS,value=(int)Cvar_VariableValue("aw_cull"),on;
        if(argc-j>1 || capacity<16)return 0;
        /* bare: the switch turns the other way (DBG-SUPERSPEED-62; it printed aw_cull before) */
        if(argc==j)on=!(value&bit);
        else{
            token=argv[j];
            on=!Q_strcasecmp(token,"on") || !Q_strcasecmp(token,"true") || !strcmp(token,"1")?1:
                !Q_strcasecmp(token,"off") || !Q_strcasecmp(token,"false") || !strcmp(token,"0")?0:-1;
        }
        if(on<0)return 0;
        value=on?value|bit:value&~bit;
        sprintf(out,"aw_cull %d\n",value&AW_CULL_MAX);return 1;
    }
    /* DBG-SUPERSPEED-62: a bare pure on/off command turns the other way (AW_DebugPureToggle above): the word is added
     * at the end, after any words the route adds */
    flip=NULL;
    if(argc==j && AW_DebugPureToggle(r->arguments)){
        const char *state=AW_DebugToggleState(r->words,r->command);
        if(state){
            int on=Cvar_VariableValue((char *)state)==0;
            flip=!strcmp(state,r->command)?(on?"1":"0"):(on?"on":"off");
        }
    }
    used=(int)strlen(r->command);if(used+2>capacity)return 0;
    strcpy(out,r->command);
    /* dbg camera fpview|hands|parts and dbg cast casting|now|ready|spell|start|strike (DBG-SUPERSPEED-62): the
     * command's own word goes with what follows; up to v0.0.62-dev2 the route dropped it ("aw_camera off") */
    if((!strcmp(r->command,"aw_camera") && !strncmp(r->words,"camera ",7)) ||
       (!strcmp(r->command,"aw_magicfx") && !strncmp(r->words,"cast ",5))){
        const char *sub=strchr(r->words,' ');
        n=(int)strlen(sub);if(used+n+2>capacity)return 0;
        strcpy(out+used,sub);used+=n;
    }
    /* The appearance-only alias reuses quickchar; no second resident command. */
    if(!strcmp(r->words,"characterchange") && argc==j){
        if(used+13>capacity)return 0;
        strcpy(out+used," appearance\n");return 1;
    }
    if(!strcmp(r->command,"aw_inventory") && !strcmp(r->words,"inventory grant")){
        if(used+7>capacity)return 0;
        strcpy(out+used," grant");used+=6;
    }
    /* dbg torch, dbg dbgtorch, dbg debugtorch, dbg give dbgtorch, dbg give debugtorch (TORCH-HIDES-HELM-62; the two short
     * names since v0.0.65, when the census exit stopped giving it): one more debug torch, through the inventory
     * command, no resident command of its own */
    if(!strcmp(r->command,"aw_inventory") && (!strcmp(r->words,"torch") || !strcmp(r->words,"dbgtorch") ||
                                              !strcmp(r->words,"debugtorch") || !strcmp(r->words,"give dbgtorch") ||
                                              !strcmp(r->words,"give debugtorch"))){
        if(argc!=j || used+17>capacity)return 0;
        strcpy(out+used," give debugtorch");used+=16;
    }
    /* dbg give weapons [stats] (DBG-GIVE-WEAPONS-59): the inventory command's weapon kit, no resident command of its own */
    if(!strcmp(r->command,"aw_inventory") && !strcmp(r->words,"give weapons")){
        if(argc-j>1 || (argc>j && Q_strcasecmp(argv[j],"stats")) || used+14>capacity)return 0;
        strcpy(out+used," give weapons");used+=13;
    }
    /* dbg give [ID [N] / money|coin|rich [N]] and dbg additem, the same (DBG-GIVE-MONEY-62): the inventory command's give
     * words (alone: the item picker), no resident command of their own */
    if(!strcmp(r->command,"aw_inventory") && (!strcmp(r->words,"give") || !strcmp(r->words,"additem") ||
       !strcmp(r->words,"give money") || !strcmp(r->words,"give coin") || !strcmp(r->words,"give rich"))){
        int money=r->words[0]=='g' && r->words[4]==' ';
        if(argc-j>(money?1:2) || used+12>capacity)return 0;
        strcpy(out+used,money?" give money":" give");used+=money?11:5;
    }
    /* dbg noburden / unburdened / noweight [on/off] (DBG-NOBURDEN-62): the inventory command's no-burden mode, no
     * resident command or setting of its own */
    if(!strcmp(r->command,"aw_inventory") && (!strcmp(r->words,"noburden") || !strcmp(r->words,"unburdened") ||
       !strcmp(r->words,"noweight"))){
        if(argc-j>1 || used+10>capacity)return 0;
        strcpy(out+used," noburden");used+=9;
    }
    /* dbg setlvl|setlevel [N], dbg restorestats|restore stats|stats restore, dbg maxstats|maxstat
     * (DBG-STATS-COMMANDS-62): the levelling command's words, no resident command of their own */
    if(!strcmp(r->command,"aw_levelup") && strcmp(r->words,"levelup") && strcmp(r->words,"skill progress")){
        const char *w=r->words[0]=='s' && r->words[1]=='e'?" setlevel":r->words[0]=='m'?" max":" restore";
        if(argc-j>(w[1]=='s'?1:0) || used+10>capacity)return 0;
        strcpy(out+used,w);used+=(int)strlen(w);
    }
    /* dbg weapon / dbg gear (WEAPONS-57): the inventory command's list box, no resident command of its own */
    if(!strcmp(r->command,"aw_inventory") && (!strcmp(r->words,"weapon") || !strcmp(r->words,"gear"))){
        if(argc>j || used+12>capacity)return 0;
        strcpy(out+used,!strcmp(r->words,"weapon")?" box weapon\n":" box gear\n");return 1;
    }
    /* dbg creatures [on/off]: "chim actors creatures", no resident command or cvar of its own (aw_actors.c) */
    if(!strcmp(r->command,"chim") && !strcmp(r->words,"creatures")){
        if(argc-j>1 || used+20>capacity)return 0;
        strcpy(out+used," actors creatures");used+=17;
    }
    /* dbg kill [REF] (DBG-KILL-60): "chim actors killpick" (the red crosshair pick) or "chim actors kill REF"; no
     * resident command of its own */
    if(!strcmp(r->command,"chim") && !strcmp(r->words,"kill")){
        if(argc-j>1 || used+26>capacity)return 0;
        if(argc==j){strcpy(out+used," actors killpick\n");return 1;}
        /* dbg kill crime (CRIME-59): the same pick, the kill counted as the player's (the murder when it is one) */
        if(!Q_strcasecmp(argv[j],"crime")){strcpy(out+used," actors killpick crime\n");return 1;}
        strcpy(out+used," actors kill");used+=12;
    }
    /* dbg mwscript alone: what the compiled scripts do and what was loaded (DBG-MWSCRIPT-SILENT-56); dbg mwscript
     * status keeps the counts only */
    if(!strcmp(r->command,"aw_mwscript_status") && !strcmp(r->words,"mwscript") && argc==j){
        if(used+8>capacity)return 0;
        strcpy(out+used," about\n");return 1;
    }
    /* dbg mwscript stats [ID|on|off] (ACTOR-STATS-ALL-61): a being's stats, no resident command of its own */
    if(!strcmp(r->command,"aw_mwscript_status") && !strcmp(r->words,"mwscript stats")){
        if(used+7>capacity)return 0;
        strcpy(out+used," stats");used+=6;
    }
    /* dbg mwscript result TOPIC NPC [N] (MWSCRIPT-PLAYER-CONTROL-62): a result script without the dialogue window,
     * no resident command of its own; topics and ids may hold spaces (quoted) and apostrophes */
    if(!strcmp(r->command,"aw_mwscript_status") && !strcmp(r->words,"mwscript result")){
        if(argc-j>3 || used+8>capacity)return 0;   /* alone or short: the handler prints its usage */
        strcpy(out+used," result");used+=7;
    }
    /* dbg door roulette [SEED]: the teleport command's roulette, no resident command of its own */
    if(!strcmp(r->command,"aw_teleport") && !strcmp(r->words,"door roulette")){
        if(used+10>capacity)return 0;
        strcpy(out+used," roulette");used+=9;
    }
    /* dbg date (LORE-DATE-FORMAT-62): the clock command's date report, no resident command of its own */
    if(!strcmp(r->command,"aw_set_time") && !strcmp(r->words,"date")){
        if(used+6>capacity)return 0;
        strcpy(out+used," date");used+=5;
    }
    /* dbg doorlocks [on/off]: the hinged door command's lock switch, no resident command of its own */
    if(!strcmp(r->command,"aw_hinged_door") && !strcmp(r->words,"doorlocks")){
        if(used+7>capacity)return 0;
        strcpy(out+used," locks");used+=6;
    }
    if(!strcmp(r->command,"aw_quickchar_set") &&
       (!strcmp(r->words,"set race") || !strcmp(r->words,"set playerrace"))){
        if(used+13>capacity)return 0;
        strcpy(out+used," playerrace");used+=11;
    }
    setting=Cvar_FindVar(r->command)!=NULL;
    /* A quoted word with a space or an apostrophe (a record ID such as "agronian guy", a topic, a race) reaches every
     * command route quoted again, as one argument; a setting takes one plain value. Up to v0.0.62-dev1 only the
     * inventory, race and result routes took them, and dbg npcs talk "agronian guy" was refused as an unknown
     * debug command (TEST-HARNESS-MINIWIND-62). The characters stay checked: no separator, quote or new command. */
    spaced=!setting;
    for(;j<argc;j++){
        token=argv[j];
        /* A route straight onto a setting gets 1/0 for the toggle words the
         * help promises; Quake would read "on" as 0 (DBG-TOGGLE-WORDS-31). */
        if(setting && argc-j==1){
            if(!Q_strcasecmp(token,"on") || !Q_strcasecmp(token,"true") || !Q_strcasecmp(token,"yes"))token="1";
            else if(!Q_strcasecmp(token,"off") || !Q_strcasecmp(token,"false") || !Q_strcasecmp(token,"no"))token="0";
        }
        n=(int)strlen(token);
        quoted=spaced && (strchr(token,' ')!=NULL || strchr(token,'\'')!=NULL);   /* Quake's parser splits at ' */
        if(!n || used+n+(quoted?5:3)>capacity)return 0;
        for(k=0;k<n;k++)if(!((token[k]>='a'&&token[k]<='z') ||
            (token[k]>='A'&&token[k]<='Z') || (token[k]>='0'&&token[k]<='9') ||
            token[k]=='-' || token[k]=='+' || token[k]=='.' || token[k]=='_' ||
            (spaced && (token[k]==' ' || token[k]=='\''))))return 0;
        out[used++]=' ';if(quoted)out[used++]='"';
        memcpy(out+used,token,n);used+=n;if(quoted)out[used++]='"';
    }
    if(flip){n=(int)strlen(flip);if(used+n+3>capacity)return 0;out[used++]=' ';memcpy(out+used,flip,n);used+=n;}
    out[used++]='\n';out[used]=0;return 1;
}
/* Return -1 for missing/invalid catalogue, 0 for bad command, 1 translated,
 * 2 help. Do not queue anything until the complete bounded scan validates. */
int AW_DebugTranslate(int argc,char **argv,char *out,int capacity) {
    int start=1,left,status,j,best=0,valid=0;FILE *f;route_t r;
    char line[DEBUG_LINE],candidate[160];
    if(capacity>0)out[0]=0;
    if(argc<1)return 0;
    if(!Q_strcasecmp(argv[0],"amiwind")){
        if(argc<2 || Q_strcasecmp(argv[1],"debug"))return 0;
        start=2;
    }else if(Q_strcasecmp(argv[0],"debug") && Q_strcasecmp(argv[0],"dbg") && Q_strcasecmp(argv[0],"aw"))return 0;
    /* "aw" is the same prefix (aw bench halloween, aw halloweenbench: the benchmark testers type) */
    if(argc==start || (argc==start+1 && !Q_strcasecmp(argv[start],"help")))return 2;
    f=catalogue_open(&left,line);if(!f)return -1;
    while((status=catalogue_line(f,&left,line))>0){
        if(!*line || *line=='#')continue;
        if(!catalogue_route(line,&r)){status=-1;break;}
        j=route_match(r.words,argc,argv,start);
        if(!j || j<best)continue;
        if(j==best){status=-1;break;}
        best=j;valid=route_format(&r,argc,argv,j,candidate,sizeof(candidate));
    }
    fclose(f);
    if(status<0)return -1;
    if(!valid || (int)strlen(candidate)+1>capacity)return 0;
    strcpy(out,candidate);return 1;
}
/* A --no-npc-gallery image lists the gallery's commands as absent. The marker
 * is checked once per listing (dbg help, dbg help <word>), never on dispatch.
 * dbg combattest enters the Vivec Arena now, which needs no gallery (its
 * floor test, dbg combattest gallery, explains itself when used). */
static const char *availability(int omitted,const route_t *r) {
    return omitted && !strcmp(r->command,"aw_charplane")?" (not in this build)":"";
}
/* the console's characters per line for tables printed elsewhere (dbg give weapons, aw_inventory.c; declared in
 * aw_inventory.h) */
int AW_ConsoleWidth(void);
int AW_ConsoleWidth(void) {
    int width=con_linewidth;
    return width<1?38:width>128?128:width;
}
/* The console pager (DBG-HELP-PAGER-62): a long listing (dbg, dbg help, dbg help WORD) is collected while it is
 * made, then shown one console screen at a time with AW_PAGER_LINE between the pages; Enter shows the next page,
 * q (or Esc) stops. The text is held only while the pager waits (malloc, given back when it ends). */
#define AW_PAGER_LINE "---------- [ more: ENTER | stop: q ] ----------"
#define AW_PAGER_BYTES (DEBUG_BYTES+16384)
static char *pager_text;static int pager_used,pager_pos,pager_collect,pager_waiting;
static void pager_end(void) {
    if(pager_text)free(pager_text);
    pager_text=NULL;pager_used=pager_pos=pager_collect=pager_waiting=0;
}
static void say(const char *fmt,...) {
    char text[DEBUG_LINE+160];va_list args;int n;
    va_start(args,fmt);vsnprintf(text,sizeof(text),fmt,args);va_end(args);
    n=(int)strlen(text);
    if(pager_collect && pager_text && pager_used+n<AW_PAGER_BYTES){memcpy(pager_text+pager_used,text,n+1);pager_used+=n;return;}
    Con_Printf("%s",text);
}
static void pager_begin(void) {
    pager_end();
    pager_text=AW_TryMalloc(AW_PAGER_BYTES);   /* NULL: the listing is printed whole, as before the pager */
    if(pager_text){pager_text[0]=0;pager_collect=1;}
}
/* the console rows one page may use: half the screen of console text, less the input line and the pager line */
int AW_ConsolePageRows(void);
int AW_ConsolePageRows(void) {
    int rows=(int)vid.conheight/8/2-5;
    return rows<8?20:rows;
}
static void pager_page(void) {
    int rows=AW_ConsolePageRows(),width=AW_ConsoleWidth(),used=0,n,need;char *line,*end,keep;
    while(pager_text && pager_pos<pager_used){
        line=pager_text+pager_pos;end=strchr(line,'\n');
        n=end?(int)(end-line):(int)strlen(line);
        need=n<1?1:(n+width-1)/width;
        if(used && used+need>rows)break;
        keep=line[n];line[n]=0;Con_Printf("%s\n",line);line[n]=keep;
        used+=need;pager_pos+=n+(end?1:0);
    }
    if(pager_text && pager_pos<pager_used){pager_waiting=1;Con_Printf("\n%s\n\n",AW_PAGER_LINE);}
    else pager_end();
}
static void pager_show(void) {
    if(!pager_collect){return;}
    pager_collect=0;pager_pos=0;pager_page();
}
/* MW-CONSOLE-COMMANDS-62: dbg help mw / dbg mw help, the original game's console commands, paged straight from
 * id1/mwconsole-help.txt (tools/mwscript_console.py): each page opens the file, reads from where the last page ended
 * and closes it; only the offset and one line's buffer are kept between the pages, never the list. */
static long mwhelp_at=-1;
static void mwhelp_page(void) {
    FILE *f=NULL;int length,rows=AW_ConsolePageRows(),width=AW_ConsoleWidth(),used=0,need,n;long base,at;
    static char line[256];
    length=COM_FOpenFile("mwconsole-help.txt",&f);
    if(!f || length<6){if(f)fclose(f);mwhelp_at=-1;Con_Printf("No mwconsole-help.txt in this image.\n");return;}
    base=ftell(f);at=mwhelp_at;
    if(at==0){   /* the header line AWMH1 */
        if(!fgets(line,sizeof(line),f) || strncmp(line,"AWMH1",5)){fclose(f);mwhelp_at=-1;Con_Printf("mwconsole-help.txt: bad file.\n");return;}
        at=(long)strlen(line);
    }else if(fseek(f,base+at,SEEK_SET)){fclose(f);mwhelp_at=-1;return;}
    while(at<length && fgets(line,sizeof(line),f)){
        n=(int)strlen(line);
        need=n<=1?1:(n-1+width-1)/width;
        if(used && used+need>rows)break;
        Con_Printf("%s",line);used+=need;at+=n;
    }
    fclose(f);
    if(at<length){mwhelp_at=at;pager_waiting=1;Con_Printf("\n%s\n\n",AW_PAGER_LINE);}
    else mwhelp_at=-1;
}
void AW_MwConsoleHelp(void) {
    pager_end();mwhelp_at=0;mwhelp_page();
}
static void mw_help(void) {AW_MwConsoleHelp();}
/* keys.c Key_Console, before the input line: 1 = the pager took the key */
int AW_ConsolePagerKey(int key);
int AW_ConsolePagerKey(int key) {
    if(!pager_waiting)return 0;
    if(key==K_ENTER){pager_waiting=0;if(mwhelp_at>0)mwhelp_page();else pager_page();return 1;}
    if(key=='q' || key=='Q'){pager_end();mwhelp_at=-1;Con_Printf("(listing stopped)\n");return 1;}
    pager_end();mwhelp_at=-1;   /* any other key (Esc included) ends the listing and does what it always did */
    return 0;
}
static void catalogue_error(void) {
    Con_Printf("Debug catalogue missing/invalid: debug-commands.txt\n");
    Con_Printf("Restore the matching build's file; legacy command names still work.\n");
}
static void help(void) {
    FILE *f;route_t r;int left,status,width=con_linewidth,omitted;
    char line[DEBUG_LINE],group[32],separator[129];
    f=catalogue_open(&left,line);if(!f){catalogue_error();return;}
    omitted=AW_GalleryOmitted();
    if(width<1)width=38;
    if(width>128)width=128;
    memset(separator,'-',width);separator[width]=0;group[0]=0;
    pager_begin();
    say("AmiWind debug commands (Enter: next page, q: stop)\n");
    say("Prefix: debug / dbg / amiwind debug\n");
    while((status=catalogue_line(f,&left,line))>0){
        if(!*line || *line=='#')continue;
        if(!catalogue_route(line,&r)){status=-1;break;}
        if(strcmp(group,r.group)){
            strcpy(group,r.group);say("\n%s\n%s\n",group,separator);
        }
        say(" %s %s%s\n",r.words,r.arguments,availability(omitted,&r));
    }
    fclose(f);if(status<0){pager_end();catalogue_error();return;}
    say(" help: this list; old names still work\n");
    say("Toggle values: on/off true/false 1/0; none: the other way\n");
    say("Noclip: look+WASD, E/Q vertical, Shift\n");
    pager_show();
}
/* dbg help <word>: only the catalogue lines whose command starts with that word,
 * streamed from the disk file like the full list. */
static void help_for(char *word) {
    FILE *f;route_t r;int left,status,n=strlen(word),shown=0,omitted;char line[DEBUG_LINE];
    if(!Q_strcasecmp(word,"mw")){AW_MwConsoleHelp();return;}   /* dbg help mw: the original's console commands */
    f=catalogue_open(&left,line);if(!f){catalogue_error();return;}
    omitted=AW_GalleryOmitted();
    pager_begin();
    while((status=catalogue_line(f,&left,line))>0){
        if(!*line || *line=='#')continue;
        if(!catalogue_route(line,&r)){status=-1;break;}
        if(Q_strncasecmp(r.words,word,n) || (r.words[n] && r.words[n]!=' '))continue;
        say(" dbg %s %s%s\n",r.words,r.arguments,availability(omitted,&r));shown++;
    }
    fclose(f);if(status<0){pager_end();catalogue_error();return;}
    pager_show();
    if(!shown)Con_Printf("No debug command starts with \"%s\"; use debug help\n",word);
}
static void dispatch(void) {
    char *argv[12],out[160];int i,n=Cmd_Argc(),r;
    if(n>12){Con_Printf("Too many arguments; use debug help\n");return;}
    for(i=0;i<n;i++)argv[i]=Cmd_Argv(i);
    if(n==3 && Q_strcasecmp(argv[0],"amiwind") && !Q_strcasecmp(argv[1],"help")){help_for(argv[2]);return;}
    r=AW_DebugTranslate(n,argv,out,sizeof(out));
    if(r<0)catalogue_error();else if(r==2)help();else if(r==1)Cbuf_InsertText(out);
    else Con_Printf("Unknown debug command; use debug help\n");
}
static int integer(char *s,int maximum,int *out) {
    int n=0;if(!*s)return 0;
    while(*s){if(*s<'0'||*s>'9')return 0;n=n*10+*s++-'0';if(n>maximum)return 0;}
    *out=n;return 1;
}
static void set_colour(void) {
    int rgb[3],i,best=255;long distance,best_distance=0x7fffffff;char *s=Cmd_Argv(1);
    if(Cmd_Argc()==1) {
        i=(int)colour.value;if(i<0||i>255)i=255;
        Con_Printf("console bg palette %ld / RGB %ld %ld %ld\n",(long)i,
            (long)host_basepal[i*3],(long)host_basepal[i*3+1],(long)host_basepal[i*3+2]);return;
    }
    if(Cmd_Argc()==2 && !Q_strcasecmp(s,"black"))rgb[0]=rgb[1]=rgb[2]=0;
    else if(Cmd_Argc()==2 && !Q_strcasecmp(s,"blue")){rgb[0]=16;rgb[1]=24;rgb[2]=48;}
    else if(Cmd_Argc()==2 && (!Q_strcasecmp(s,"gray")||!Q_strcasecmp(s,"grey")))rgb[0]=rgb[1]=rgb[2]=48;
    else if(Cmd_Argc()==4 && integer(Cmd_Argv(1),255,&rgb[0]) &&
        integer(Cmd_Argv(2),255,&rgb[1]) && integer(Cmd_Argv(3),255,&rgb[2])){}
    else {Con_Printf("Color: black/blue/gray, or R G B (0..255)\n");return;}
    for(i=0;i<256;i++) {
        long r=host_basepal[i*3]-rgb[0],g=host_basepal[i*3+1]-rgb[1],b=host_basepal[i*3+2]-rgb[2];
        distance=r*r+g*g+b*b;if(distance<best_distance){best=i;best_distance=distance;}
    }
    Cvar_SetValue(colour.name,best);
    Con_Printf("Console color uses nearest palette entry.\n");
}
static void set_size(void) {
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()!=2 || (Q_strcasecmp(s,"small") && Q_strcasecmp(s,"normal"))) {
        Con_Printf("Usage: debug console font small/normal\n");return;
    }
    AW_ConsoleSetSmall(!Q_strcasecmp(s,"small"));
    Con_CheckResize();scr_copyeverything=1;
    Con_Printf("Console font: %s\n",s);
}
static void set_font(void) {
    byte data[16384];char *path,*name=Cmd_Argv(1);FILE *f=NULL;int size;
    if(Cmd_Argc()!=2 || (Q_strcasecmp(name,"readable") && Q_strcasecmp(name,"retro"))) {
        Con_Printf("Usage: debug font readable/retro (all UI text)\n");return;
    }
    path=!Q_strcasecmp(name,"retro")?"gfx/font-retro.lmp":"gfx/font-readable.lmp";
    size=COM_FOpenFile(path,&f);
    if(size!=sizeof(data) || !f){if(f)fclose(f);Con_Printf("Font missing or wrong size.\n");return;}
    if(fread(data,1,sizeof(data),f)!=sizeof(data)){fclose(f);Con_Printf("Font read failed.\n");return;}
    fclose(f);memcpy(draw_chars,data,sizeof(data));
    scr_copyeverything=1;Con_Printf("Font: %s\n",name);
}
void AW_ConsoleBackground(int lines) {
    int y,ink=(int)colour.value;
    if(lines<0)return;
    if(lines>(int)vid.conheight)lines=(int)vid.conheight;
    if(ink<0||ink>255)ink=255;
    for(y=0;y<lines;y++)
        memset(vid.conbuffer+y*vid.conrowbytes,ink,vid.conwidth);
    scr_copyeverything=1;
}
static void heap_audit(void){AW_HeapAuditReport(sv.worldmodel?sv.worldmodel->name:sv.name);}
void AW_ConsoleInit(void) {
    Cvar_RegisterVariable(&colour);
    Cmd_AddCommand("aw_heap_audit",heap_audit);
    Cmd_AddCommand("debug",dispatch);Cmd_AddCommand("dbg",dispatch);Cmd_AddCommand("aw",dispatch);
    Cmd_AddCommand("amiwind",dispatch);
    Cmd_AddCommand("aw_mw_help",mw_help);   /* dbg mw help (MW-CONSOLE-COMMANDS-62) */
    aw_console_pager_key=AW_ConsolePagerKey;   /* keys.c Key_Console (DBG-HELP-PAGER-62) */
    Cmd_AddCommand("aw_console_color",set_colour);
    Cmd_AddCommand("aw_console_font",set_font);
    Cmd_AddCommand("aw_console_size",set_size);
}
