/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_state.h"
#include "aw_story.h"
#include "aw_character.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;viddef_t vid;
aw_story_t aw_story;aw_character_t aw_character;
aw_race_t aw_races[16];aw_class_t aw_classes[32];
keydest_t key_dest=key_game;int scr_copyeverything;
static void (*map_command)(void),(*journal_command)(void);
static int missing,corrupt,opens;static char drawn[16384];
static byte pixels[320*200];
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_worldmap"))map_command=fn;else if(!strcmp(name,"aw_journal"))journal_command=fn;}
void IN_AWClearButtons(void){}
int AW_StoryRestricted(void){return 0;}
int AW_ReaderActive(void){return 0;}
int AW_CharacterActive(void){return 0;}
int AW_GalleryActive(void){return 0;}
void Con_Printf(char *s,...){}
int AW_UIColor(int r,int g,int b){return (r+g+b)%256;}
int AW_ConsoleCharWidth(void){return 4;}
void AW_ConsoleCharacter(int x,int y,int c){int n=strlen(drawn);assert(n<16383);drawn[n]=c;drawn[n+1]=0;}
void AW_UIFill(int x,int y,int w,int h,int c){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){}
int AW_UIScrollHit(int mx,int my,int x,int y,int h,int total,int visible,int top){return -1;}
void AW_UIBookBegin(void){}
void AW_UIBookEnd(void){}
void AW_UIText(int x,int y,const char *s,int c){strcat(drawn,s);}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){strcat(drawn,s);}
const char *AW_UILine(const char *p,int width,char *out,int capacity){int n=0;while(*p && n<width/6 && n<capacity-1)out[n++]=*p++;out[n]=0;return p;}
static void word(FILE *f,unsigned n){int i;for(i=0;i<4;i++)fputc((n>>(8*i))&255,f);}
static void fixed(FILE *f,const char *s,int n){int i;for(i=0;i<n;i++)fputc(i<(int)strlen(s)?s[i]:0,f);}
static const char body[]="Welcome %PCName. An earned event.\0Another earned event.";
int COM_FOpenFile(char *name,FILE **out){
    FILE *f;int size,i;long base=137;unsigned bits;float value;
    opens++;if(missing){*out=NULL;return -1;}f=tmpfile();assert(f);*out=f;
    for(i=0;i<base;i++)fputc(0,f); /* Exercise packed-member-relative seeks. */
    if(!strcmp(name,"world/map.awm")){
        fputs(corrupt?"BAD!":"AWM1",f);fputc(32,f);fputc(0,f);fputc(32,f);fputc(0,f);
        word(f,(unsigned)-8192);word(f,(unsigned)-8192);word(f,8192);word(f,8192);word(f,1);word(f,5);
        fixed(f,"balmora",16);fixed(f,"Balmora",32);word(f,0);word(f,0);value=.25;memcpy(&bits,&value,4);word(f,bits);
        for(i=0;i<1024;i++)fputc(i&255,f);
    }else if(!strcmp(name,"world/quests.awq")){fputs("AWQ1",f);word(f,1);fixed(f,"quest",64);fixed(f,"Known quest",96);
    }else if(!strcmp(name,"world/journal.awj")){
        fputs("AWJ1",f);word(f,2);
        fixed(f,"quest",64);word(f,1);word(f,0);word(f,strlen(body)+1);
        fixed(f,"quest",64);word(f,10);word(f,strlen(body)+1);word(f,sizeof(body)-strlen(body)-1);
    }else if(!strcmp(name,"world/entries.dat"))fwrite(body,1,sizeof(body),f);
    else assert(0);
    size=ftell(f)-base;fseek(f,base,SEEK_SET);return size;
}
static void draw(void){drawn[0]=0;assert(AW_WorldUIDraw());}
int main(void){
    edict_t player;client_t client;int before;
    memset(&player,0,sizeof(player));memset(&client,0,sizeof(client));
    sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&player;cls.state=ca_connected;
    strcpy(sv.name,"balmora");strcpy(aw_story.name,"Hors");
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;
    AW_WorldUIInit();assert(map_command && journal_command);
    missing=1;map_command();assert(!AW_WorldUIActive() && key_dest==key_game);missing=0;
    corrupt=1;map_command();assert(!AW_WorldUIActive() && key_dest==key_game);corrupt=0;
    map_command();assert(AW_WorldUIActive() && key_dest==key_menu);
    before=opens;draw();assert(strstr(drawn,"Cell 0,0"));
    AW_WorldUIKey('=',1);AW_WorldUIKey('p',1);AW_WorldUIKey('g',1);draw();
    assert(opens==before);AW_WorldUIKey('m',1);assert(!AW_WorldUIActive() && key_dest==key_game);
    journal_command();draw();assert(strstr(drawn,"No dated journal"));AW_WorldUIKey('j',1);
    assert(AW_JournalAdd(&aw_state,"quest",1));assert(AW_JournalAdd(&aw_state,"quest",10));
    journal_command();draw();assert(strstr(drawn,"Another earned event."));
    AW_WorldUIKey(K_LEFTARROW,1);draw();assert(strstr(drawn,"Welcome Hors."));
    before=opens;draw();assert(opens==before); /* Drawing never fetches text. */
    AW_WorldUIKey(K_TAB,1);draw();assert(strstr(drawn,"Quests in your journal"));
    AW_WorldUIKey(K_ENTER,1);draw();assert(strstr(drawn,"Another earned event."));
    AW_WorldUIKey(K_BACKSPACE,1);draw();assert(strstr(drawn,"2/2"));
    assert(!AW_WorldUIKey(K_F10,1));assert(!AW_WorldUIActive() && key_dest==key_game);
    assert(aw_state.journal_count==2 && AW_StateGet(&aw_state,AW_JOURNAL,"quest")==10);
    map_command();key_dest=key_game;assert(!AW_WorldUIDraw() && !AW_WorldUIActive());
    journal_command();assert(AW_WorldUIActive());AW_WorldUIKey('j',1);
    strcpy(sv.name,"census");map_command();draw();assert(strstr(drawn,"no exterior position"));
    strcpy(sv.name,"seyda");assert(!AW_WorldUIDraw() && !AW_WorldUIActive());
    return 0;
}
