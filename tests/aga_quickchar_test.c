/* SPDX-License-Identifier: GPL-2.0-or-later
 * The quick character screen (aw_quickchar.c) over stand-ins for the census
 * office menus (aw_character.c): the page order, Enter-only pages before the
 * last and the "Really choose" box on the last, the name page, the callback, the
 * page words, cancel, refusals, and both callers (the debug command here; New
 * Game through AW_QuickCharOpen in aw_scene.c) reaching the same entry point. */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_quickchar.h"
#include <assert.h>
#include <stdarg.h>
server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;viddef_t vid;keydest_t key_dest;
cmd_source_t cmd_source=src_command;vec3_t vec3_origin;
aw_story_t aw_story;aw_character_t aw_character;aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];
static client_t client;static edict_t player;
static int menu,menu_done,restricted,opened[16][2],opens,sounds,callbacks[4],last_callback=-1,cleared,set_calls;
int aw_race_count=3;
static int fail_set;
static char printed[4096],set_value[64];
float AW_CharacterEyeHeight(void){return 51;}
int AW_CharacterLoad(void){return 1;}
void AW_CharacterReset(void){aw_character.valid=1;}
int AW_CharacterOpenQuick(int kind,int confirm){opened[opens][0]=kind;opened[opens++][1]=confirm;menu=kind;return 1;}
int AW_CharacterActive(void){return menu!=0;}
int AW_CharacterDone(void){int r=menu_done;menu_done=0;return r;}
void AW_CharacterClose(void){menu=0;}
int AW_CharacterSet(aw_character_t *c,const char *field,const char *value,const char *number){
    int i;(void)number;set_calls++;strcpy(set_value,value);
    if(fail_set || !strcmp(field,"bogus"))return 0;
    if(!strcmp(field,"race"))for(i=0;i<aw_race_count;i++)if(!strcmp(value,aw_races[i].id)){c->race=i;c->head=i*2;c->hair=i*2+1;c->level=1;c->attributes[0]=17;c->current[0]=99;break;}
    return 1;
}
/* The census menu accepting its page (Enter, or Choose in its box). */
static void accept_menu(void){menu_done=menu;menu=0;}
int AW_StoryRestricted(void){return restricted;}
int AW_NameEdit(char *name,int capacity,int key){
    int n=(int)strlen(name);
    if(key==K_BACKSPACE && n)name[n-1]=0;
    else if(key>=32 && key<127 && n<capacity-1){name[n]=(char)key;name[n+1]=0;}
    else if(key==K_ENTER && n)return 1;
    return 0;
}
void AW_NameDraw(int x,int y,const char *name){(void)x;(void)y;(void)name;}
int COM_FOpenFile(char *name,FILE **f){(void)name;*f=NULL;return -1;}  /* no voice files: skipped quietly */
sfx_t *S_PrecacheSound(char *name){(void)name;sounds++;return NULL;}
void S_StartSound(int e,int c,sfx_t *s,vec3_t o,float v,float a){(void)e;(void)c;(void)s;(void)o;(void)v;(void)a;}
sfxcache_t *S_LoadSound(sfx_t *s){(void)s;return NULL;}
void AW_ExpandPlayerName(char *out,unsigned capacity,const char *text){(void)capacity;strcpy(out,text);}
void AW_UIVoiceSubtitle(const char *n,const char *t,double d){(void)n;(void)t;(void)d;}
void IN_AWClearButtons(void){cleared++;}
int AW_ModalBlackBackground(void){return 1;}
void AW_UIFill(int x,int y,int w,int h,int c){(void)x;(void)y;(void)w;(void)h;(void)c;}
int AW_UIColor(int r,int g,int b){return r+g+b;}
void AW_UIBox(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
void AW_UITextBox(int x,int y,int w,int h,const char *t,int c){(void)x;(void)y;(void)w;(void)h;(void)t;(void)c;}
void Con_Printf(char *fmt,...){
    va_list args;size_t n=strlen(printed);va_start(args,fmt);
    vsnprintf(printed+n,sizeof(printed)-n,fmt,args);va_end(args);
}
void Con_ToggleConsole_f(void){}
void Cbuf_AddText(char *t){(void)t;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int Q_atoi(char *s){return atoi(s);}
int scr_copyeverything;
static cvar_t *cvars[4];static int cvar_count;
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);cvars[cvar_count++]=v;}
static struct {const char *name;xcommand_t fn;} commands[8];static int command_count;
static const char *args[8];static int arg_count;
void Cmd_AddCommand(char *name,xcommand_t fn){commands[command_count].name=name;commands[command_count++].fn=fn;}
int Cmd_Argc(void){return arg_count;}
char *Cmd_Argv(int i){return (char *)(i<arg_count?args[i]:"");}
static void run(int n,const char **v){
    int i;printed[0]=0;arg_count=n;for(i=0;i<n;i++)args[i]=v[i];
    for(i=0;i<command_count;i++)if(!strcmp(commands[i].name,v[0])){commands[i].fn();return;}
    assert(!"registered");
}
static void done(int accepted){callbacks[accepted]++;last_callback=accepted;}
static void tick_until_quiet(void){int i;for(i=0;i<3;i++)AW_QuickCharTick();}
int main(void){
    int i;
    AW_QuickCharInit();
    strcpy(aw_races[0].name,"Nord");strcpy(aw_classes[0].name,"Barbarian");strcpy(aw_births[0].name,"The Steed");
    aw_character.valid=1;aw_character.current[0]=55;
    /* No world: refused, nothing opened. */
    assert(!AW_QuickCharOpen(AW_QC_ALL,done) && !AW_QuickCharActive() && !opens);
    sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&player;cls.state=ca_connected;key_dest=key_game;
    /* All pages: name, then appearance, class, birthsign (Enter only), review (with the box). */
    strcpy(aw_story.name,"Hors");
    assert(AW_QuickCharOpen(AW_QC_ALL|AW_QC_VOICE,done) && AW_QuickCharActive() && !opens);
    assert(AW_QuickCharKey(K_BACKSPACE) && AW_QuickCharKey('a') && !strcmp(aw_story.name,"Hors"));
    assert(AW_QuickCharKey(K_ENTER) && !strcmp(aw_story.name,"Hora"));
    assert(opens==1 && opened[0][0]==1 && opened[0][1]==0);
    assert(!AW_QuickCharKey('x'));                       /* menu pages: the census menu has the keys */
    tick_until_quiet();assert(opens==1);                 /* still on the page */
    accept_menu();AW_QuickCharTick();assert(opens==2 && opened[1][0]==2 && opened[1][1]==0);
    accept_menu();AW_QuickCharTick();assert(opens==3 && opened[2][0]==3 && opened[2][1]==0);
    accept_menu();AW_QuickCharTick();assert(opens==4 && opened[3][0]==4 && opened[3][1]==1);
    assert(!callbacks[1]);
    accept_menu();AW_QuickCharTick();
    assert(!AW_QuickCharActive() && callbacks[1]==1 && last_callback==1 && player.v.health==55);
    assert(sounds==0);                                   /* no voice or page files in this payload: none played */
    /* Page words: any order, aliases; unknown words refused. */
    { char *w[]={"x","review","CLASS"};assert(AW_QuickCharPages(3,w,1)==(AW_QC_CLASS|AW_QC_REVIEW)); }
    { char *w[]={"x","all"};assert(AW_QuickCharPages(2,w,1)==AW_QC_ALL); }
    { char *w[]={"x","head","birth","skills"};assert(AW_QuickCharPages(4,w,1)==(AW_QC_APPEARANCE|AW_QC_BIRTHSIGN|AW_QC_REVIEW)); }
    { char *w[]={"x","stats"};assert(!AW_QuickCharPages(2,w,1)); }
    /* One page: its box asks (it is the last page). */
    opens=0;assert(AW_QuickCharOpen(AW_QC_CLASS,done) && opens==1 && opened[0][0]==2 && opened[0][1]==1);
    accept_menu();AW_QuickCharTick();assert(!AW_QuickCharActive() && callbacks[1]==2);
    /* Cancel: the callback says so; the open menu closes. */
    assert(AW_QuickCharOpen(AW_QC_CLASS|AW_QC_BIRTHSIGN,done));
    AW_QuickCharCancel();assert(!AW_QuickCharActive() && !menu && callbacks[0]==1);
    /* A menu taken away (a reset) without accepting: cancelled. */
    assert(AW_QuickCharOpen(AW_QC_CLASS,done));menu=0;AW_QuickCharTick();assert(callbacks[0]==2);
    /* The world going away: cancelled. */
    assert(AW_QuickCharOpen(AW_QC_CLASS,done));sv.active=0;AW_QuickCharTick();assert(callbacks[0]==3);sv.active=1;
    /* Refused: during the story's own registration, while open, bad page sets. */
    restricted=1;assert(!AW_QuickCharOpen(AW_QC_ALL,done));restricted=0;
    assert(!AW_QuickCharOpen(0,done) && !AW_QuickCharOpen(128,done));
    assert(AW_QuickCharOpen(AW_QC_NAME,done) && !AW_QuickCharOpen(AW_QC_NAME,done));
    AW_QuickCharKey(K_ENTER);assert(!AW_QuickCharActive() && callbacks[1]==3);
    /* The second caller: dbg quickchar (aw_quickchar) opens the same screen through AW_QuickCharOpen. */
    opens=0;{ const char *v[]={"aw_quickchar","class"};run(2,v); }
    assert(AW_QuickCharActive() && opens==1 && opened[0][0]==2);
    accept_menu();AW_QuickCharTick();assert(!AW_QuickCharActive());
    { const char *v[]={"aw_quickchar","nonsense"};opens=0;run(2,v);assert(!opens && !AW_QuickCharActive()); }
    /* Appearance inspection defaults to the exact pier page and confirmation.
     * Normal story registration still owns its own menu and cannot be bypassed. */
    opens=0;{ const char *v[]={"aw_quickchar","appearance"};run(2,v); }
    assert(AW_QuickCharActive() && opens==1 && opened[0][0]==1 && opened[0][1]==1);
    accept_menu();AW_QuickCharTick();assert(!AW_QuickCharActive());
    restricted=1;opens=0;{ const char *v[]={"aw_quickchar","appearance"};run(2,v); }
    assert(!opens && !AW_QuickCharActive());restricted=0;
    { const char *v[]={"aw_quickchar","class"};run(2,v); }
    assert(AW_QuickCharActive() && opened[0][0]==2);
    AW_QuickCharCancel();assert(!AW_QuickCharActive() && !menu);
    /* Scripted character: aw_quickchar_set marks it (a quick start keeps it); clear forgets. */
    assert(!AW_QuickCharScripted());
    { const char *v[]={"aw_quickchar_set","race","nord"};run(3,v); }
    assert(AW_QuickCharScripted() && set_calls==1);
    { const char *v[]={"aw_quickchar_set","clear"};run(2,v); }
    assert(!AW_QuickCharScripted());
    { const char *v[]={"aw_quickchar_set","bogus","x"};run(3,v);assert(!AW_QuickCharScripted()); }
    { const char *v[]={"aw_quickchar_set","name","Tester"};run(3,v);assert(AW_QuickCharScripted() && !strcmp(aw_story.name,"Tester")); }
    /* Race command resolves the loaded catalogue and forwards its canonical ID.
     * Listing/invalid input/registration/death must not change the character. */
    strcpy(aw_races[0].id,"nord");
    strcpy(aw_races[1].id,"argonian");strcpy(aw_races[1].name,"Argonian");
    strcpy(aw_races[2].id,"high elf");strcpy(aw_races[2].name,"High Elf");
    aw_character.race=0;aw_character.female=1;aw_character.clas=2;aw_character.birth=3;
    aw_character.level=7;aw_character.attributes[0]=88;aw_character.current[0]=55;
    player.v.health=55;player.v.mins[2]=-24;
    { const char *v[]={"aw_quickchar_set","clear"};run(2,v); }
    { const char *v[]={"aw_quickchar_set","playerrace"};i=set_calls;run(2,v);
      assert(set_calls==i && strstr(printed,"0: Nord [current]") && strstr(printed,"2: High Elf")); }
    { const char *v[]={"aw_quickchar_set","playerrace","LIST"};run(3,v);assert(set_calls==i && strstr(printed,"1: Argonian")); }
    { const char *v[]={"aw_quickchar_set","playerrace","1"};run(3,v);
      assert(set_calls==i+1 && aw_character.race==1 && !strcmp(set_value,"argonian"));
      assert(aw_character.female==1 && aw_character.clas==2 && aw_character.birth==3);
      assert(player.v.health==55 && player.v.view_ofs[2]==27 && !AW_QuickCharScripted());
      assert(aw_character.current[0]==55 && aw_character.level==7 && aw_character.attributes[0]==88);
      assert(aw_character.head==2 && aw_character.hair==3); }
    { const char *v[]={"aw_quickchar_set","playerrace","HiGh","ElF"};run(4,v);assert(aw_character.race==2 && !strcmp(set_value,"high elf")); }
    { const char *v[]={"aw_quickchar_set","playerrace","argonian"};run(3,v);assert(aw_character.race==1); }
    { const char *v[]={"aw_quickchar_set","playerrace","HIGH_ELF"};run(3,v);assert(aw_character.race==2); }
    { const char *v[]={"aw_quickchar_set","playerrace","Argonian"};run(3,v);assert(aw_character.race==1); }
    { const char *v[]={"aw_quickchar_set","playerrace","high-elf"};run(3,v);assert(aw_character.race==2); }
    { const char *v[]={"aw_quickchar_set","playerrace","High Elf"};i=set_calls;run(3,v);assert(set_calls==i && strstr(printed,"unchanged")); }
    { const char *bad[]={"-1","3","999999999999999999999999999999999999","1junk","1.0","imperial","","0 1"};
      int b;aw_character_t before=aw_character;
      for(b=0;b<8;b++){const char *v[]={"aw_quickchar_set","playerrace",bad[b]};run(3,v);assert(set_calls==i && !memcmp(&aw_character,&before,sizeof before));} }
    { const char *v[]={"aw_quickchar_set","playerrace","0"};
      restricted=1;run(3,v);restricted=0;assert(set_calls==i);
      menu=1;run(3,v);menu=0;assert(set_calls==i);
      sv.active=0;run(3,v);sv.active=1;assert(set_calls==i);
      cls.state=ca_disconnected;run(3,v);cls.state=ca_connected;assert(set_calls==i);
      svs.maxclients=2;run(3,v);svs.maxclients=1;assert(set_calls==i);
      player.v.health=0;run(3,v);player.v.health=55;assert(set_calls==i);
      cmd_source=src_client;run(3,v);cmd_source=src_command;assert(set_calls==i);
      fail_set=1;run(3,v);fail_set=0;assert(set_calls==i+1 && aw_character.race==2 && strstr(printed,"cannot be applied"));
      run(3,v);assert(aw_character.race==0 && strstr(printed,"Player race: 0: Nord")); }
    /* aw_skip_census: off by default (the normal game keeps the ship and the census). */
    assert(!AW_SkipCensus());
    for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,"aw_skip_census"))cvars[i]->value=1;
    assert(AW_SkipCensus());
    puts("quick character screen: page order, confirm on the last page, name, callback, cancel, both callers");
    return 0;
}
