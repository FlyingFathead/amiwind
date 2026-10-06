/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_state.h"
#include "aw_story.h"
#include "aw_character.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;viddef_t vid;
aw_story_t aw_story;aw_character_t aw_character;
aw_race_t aw_races[16];aw_class_t aw_classes[32];
int scr_copyeverything;
static void (*map_command)(void),(*journal_command)(void),(*teleport_command)(void);
static int missing,corrupt,opens,jumps,jump_available=1,red_pixels,story_restricted;static float destination[3];static char drawn[16384];
static byte pixels[320*200];
static const char title[]="A long quest heading which must wrap completely within one journal page without losing text";
static int heading_rows,marker_x=-1,marker_y=-1,char_width=4,region_calls;
static char footer[80];static int footer_left,footer_right;
static const char *region_override;
/* Model the registered values used by the real panel; do not bypass mode logic. */
static cvar_t *map_vars[16];static int map_var_count,debug_overlays=1;
void Cvar_RegisterVariable(cvar_t *v){assert(map_var_count<16);v->value=atof(v->string);map_vars[map_var_count++]=v;}
void Cvar_SetValue(char *name,float value){int i;for(i=0;i<map_var_count;i++)if(!strcmp(name,map_vars[i]->name)){map_vars[i]->value=value;return;}assert(0);}
int AW_DebugOverlaysEnabled(void){return debug_overlays;}
int Cmd_Argc(void){return 1;}
const char *AW_RegionNameAt(const float *p){region_calls++;return region_override?region_override:p[0]<0?"West test region":"East test region";}
int AW_MapTeleport(const float *p){int i;for(i=0;i<3;i++)destination[i]=p[i];if(!jump_available)return 0;jumps++;return 1;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_teleport_map"))teleport_command=fn;else if(!strcmp(name,"aw_worldmap"))map_command=fn;else if(!strcmp(name,"aw_journal"))journal_command=fn;}
int AW_StoryRestricted(void){return story_restricted;}
static int ui_kind;
int AW_ReaderActive(void){return ui_kind==2;}
int AW_CharacterActive(void){return ui_kind==3;}
int AW_GalleryActive(void){return 0;}
int AW_WorldToSource(const char *name,const float *local,float *world){
 int i;if(strcmp(name,"vf0000"))return 0;
 for(i=0;i<3;i++)world[i]=local[i]*4;world[0]+=4096;world[2]+=2048;return 1;
}
static char console_message[256];
void Con_Printf(char *s,...){strncpy(console_message,s,sizeof(console_message)-1);}
int AW_UIColor(int r,int g,int b){return (r+g+b)%256;}
int AW_ConsoleCharWidth(void){return char_width;}
void AW_ConsoleCharacter(int x,int y,int c){int n=strlen(drawn);assert(n<16383);drawn[n]=c;drawn[n+1]=0;
    if(y==188 && x>=96){n=strlen(footer);assert(n<79);if(!n)footer_left=x;footer[n]=c;footer[n+1]=0;footer_right=x+char_width;}
}
void AW_UIFill(int x,int y,int w,int h,int c){if(c==AW_UIColor(255,32,32))red_pixels++;assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);if(w==9 && h==1){marker_x=x+4;marker_y=y;}}
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){}
static int scroll_hits;
int AW_UIScrollHit(int mx,int my,int x,int y,int h,int total,int visible,int top){scroll_hits++;return -1;}
void AW_UIBookBegin(void){}
void AW_UIBookEnd(void){}
int AW_UIWidth(const char *s){return (int)strlen(s)*6;}
void AW_UIText(int x,int y,const char *s,int c){strcat(drawn,s);}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){
    assert((x>=10 && x+w<=154) || (x>=166 && x+w<=302));
    assert(AW_UIWidth(s)<=w);assert(y>=5 && y+h<=188);
    if(x==14 && y>=26 && y<110 && h==14)heading_rows++;
    strcat(drawn,s);
}
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
    }else if(!strcmp(name,"world/quests.awq")){fputs("AWQ1",f);word(f,1);fixed(f,"quest",64);fixed(f,title,96);
    }else if(!strcmp(name,"world/journal.awj")){
        fputs("AWJ1",f);word(f,2);
        fixed(f,"quest",64);word(f,1);word(f,0);word(f,strlen(body)+1);
        fixed(f,"quest",64);word(f,10);word(f,strlen(body)+1);word(f,sizeof(body)-strlen(body)-1);
    }else if(!strcmp(name,"world/entries.dat"))fwrite(body,1,sizeof(body),f);
    else assert(0);
    size=ftell(f)-base;fseek(f,base,SEEK_SET);return size;
}
static void draw(void){drawn[0]=footer[0]=0;heading_rows=0;marker_x=marker_y=-1;assert(AW_WorldUIDraw());}
/* Platform stubs below do not implement movement or hit testing. */
int mouseX,mouseY;
qboolean mouse_has_moved,noclip_anglehack;
extern kbutton_t in_strafe,in_mlook;
extern cvar_t m_filter;
cvar_t sensitivity={"sensitivity","1"},lookstrafe={"lookstrafe","0"};
cvar_t m_side={"m_side","1"},m_pitch={"m_pitch","1"};
cvar_t m_yaw={"m_yaw","1"},m_forward={"m_forward","1"};
static int ui_calls,ui_dx,ui_dy;
void V_StopPitchDrift(void){}
qboolean V_ExplicitPitchCentering(void){return false;}
static void ui_motion(int x,int y){ui_calls++;ui_dx+=x;ui_dy+=y;}
void AW_MenuMouse(int x,int y){ui_motion(x,y);}
void AW_ReaderMouse(int x,int y){ui_motion(x,y);}
void AW_CharacterMouse(int x,int y){ui_motion(x,y);}
int AW_GalleryModal(void){return ui_kind==4;}
void AW_GalleryMouse(int x,int y){ui_motion(x,y);}
static void click(void){assert(AW_WorldUIKey(K_MOUSE1,1));assert(AW_WorldUIKey(K_MOUSE1,0));}
static void no_motion(void){usercmd_t move;memset(&move,0,sizeof(move));IN_Move(&move);assert(cl.viewangles[YAW]==0 && cl.viewangles[PITCH]==0);}

/* Implemented by an adapter generated from the unchanged native switch body. */
void AW_TestFocusEvent(void);
extern qboolean keydown[256];
extern int key_repeats[256];
static void require(int ok,const char *reason){if(!ok){fprintf(stderr,"FAIL %s\n",reason);exit(1);}}
static void point(int x,int y){IN_AWMouseEvent(-1000,-1000);IN_AWMouseEvent(x,y);}
static void start_map(int teleport){
    if(AW_WorldUIActive())AW_WorldUIKey(K_ESCAPE,1);
    key_dest=key_game;Cvar_SetValue("aw_map_mode",0);jumps=0;
    if(teleport)teleport_command();else map_command();
    require(AW_WorldUIActive(),"OPEN_FAILED");
    AW_WorldUIKey(K_HOME,1);point(160,100);draw();
    require(marker_x>20 && marker_y>20,"MARKER_MISSING");
}
static void shift(int x,int y,int dx,int dy,const char *why){
    draw();require(abs(marker_x-x-dx)<=1 && abs(marker_y-y-dy)<=1,why);
}
static void focus_pair(void){
    /* Both native focus cases share this exact extracted statement sequence.
     * No button-up is dispatched: it was lost while the guest was inactive. */
    keydown[K_MOUSE1]=keydown[K_MOUSE2]=keydown[K_MOUSE3]=true;
    key_repeats[K_MOUSE1]=key_repeats[K_MOUSE2]=key_repeats[K_MOUSE3]=1;
    AW_TestFocusEvent();AW_TestFocusEvent();
    require(!keydown[K_MOUSE1] && !keydown[K_MOUSE2] && !keydown[K_MOUSE3],"KEY_RESET_FAILED");
    require(!key_repeats[K_MOUSE1] && !key_repeats[K_MOUSE2] && !key_repeats[K_MOUSE3],"REPEAT_RESET_FAILED");
    require(in_mlook.state==1,"MLOOK_WAS_DISABLED");
}
static void drag_case(int button,int lose_focus){
    int x,y;start_map(button!=K_MOUSE1);x=marker_x;y=marker_y;
    AW_WorldUIKey(button,1);IN_AWMouseEvent(12,-6);
    shift(x,y,12,-6,"NORMAL_DRAG_FAILED");x=marker_x;y=marker_y;
    if(lose_focus)focus_pair();else AW_WorldUIKey(button,0);
    require(AW_WorldUIActive() && key_dest==key_menu,"FOCUS_CLOSED_PANEL");
    shift(x,y,0,0,"FOCUS_MOVED_VIEW");
    IN_AWMouseEvent(-5,3);
    shift(x,y,0,0,lose_focus?"FOCUS_LOSS_DRAG_STILL_ACTIVE":"NORMAL_RELEASE_FAILED");
    no_motion();require(jumps==0,"UNEXPECTED_TELEPORT");
    /* A fresh press must still work after cancellation. */
    AW_WorldUIKey(button,1);IN_AWMouseEvent(3,2);
    shift(x,y,3,2,"NEW_DRAG_FAILED");AW_WorldUIKey(button,0);
}
int main(int argc,char **argv){
    edict_t player;client_t client;int x,y,before;
    require(argc==2,"CASE_REQUIRED");memset(&player,0,sizeof(player));memset(&client,0,sizeof(client));
    sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&player;cls.state=ca_connected;
    key_dest=key_game;strcpy(sv.name,"balmora");strcpy(aw_story.name,"Hors");
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;
    AW_WorldUIInit();IN_Init();m_filter.value=0;in_mlook.state=1;
    Cvar_RegisterVariable(&sensitivity);Cvar_RegisterVariable(&lookstrafe);
    Cvar_RegisterVariable(&m_side);Cvar_RegisterVariable(&m_pitch);
    Cvar_RegisterVariable(&m_yaw);Cvar_RegisterVariable(&m_forward);
    if(!strcmp(argv[1],"focus_left"))drag_case(K_MOUSE1,1);
    else if(!strcmp(argv[1],"focus_right"))drag_case(K_MOUSE3,1);
    else if(!strcmp(argv[1],"focus_middle"))drag_case(K_MOUSE2,1);
    else if(!strcmp(argv[1],"normal_left"))drag_case(K_MOUSE1,0);
    else if(!strcmp(argv[1],"normal_right"))drag_case(K_MOUSE3,0);
    else if(!strcmp(argv[1],"normal_middle"))drag_case(K_MOUSE2,0);
    else if(!strcmp(argv[1],"focus_journal")){
        require(AW_JournalAdd(&aw_state,"quest",1),"JOURNAL_SETUP_FAILED");
        journal_command();AW_WorldUIKey(K_TAB,1);point(307,80);
        AW_WorldUIKey(K_MOUSE1,1);require(scroll_hits>0,"SCROLL_DRAG_NOT_STARTED");
        before=scroll_hits;focus_pair();IN_AWMouseEvent(0,5);
        require(scroll_hits==before,"FOCUS_LOSS_SCROLL_DRAG_STILL_ACTIVE");
        require(AW_WorldUIActive() && key_dest==key_menu,"FOCUS_CLOSED_JOURNAL");no_motion();
    }else if(!strcmp(argv[1],"close_reopen")){
        start_map(1);AW_WorldUIKey(K_MOUSE3,1);IN_AWMouseEvent(10,4);
        AW_WorldUIKey(K_ESCAPE,1);require(!AW_WorldUIActive() && jumps==0,"CANCEL_FAILED");
        map_command();draw();x=marker_x;y=marker_y;IN_AWMouseEvent(8,-3);
        shift(x,y,0,0,"DRAG_LEAKED_ACROSS_REOPEN");no_motion();
    }else if(!strcmp(argv[1],"selection_preserved")){
        start_map(1);click();red_pixels=0;draw();require(red_pixels==22,"SELECTION_MISSING");
        focus_pair();red_pixels=0;draw();require(red_pixels==22,"FOCUS_DROPPED_SELECTION");
        AW_WorldUIKey(K_ENTER,1);require(jumps==1 && !AW_WorldUIActive(),"CONFIRM_FAILED");no_motion();
    }else if(!strcmp(argv[1],"cursor_preserved")){
        start_map(0);Cvar_SetValue("aw_map_mode",1);point(30,8);focus_pair();click();draw();
        require(map_vars[0]->value==0 && strstr(drawn,"DEBUG MAP"),"FOCUS_RESET_CURSOR_OR_MODE");no_motion();
    }else if(!strcmp(argv[1],"game_motion_discarded")){
        IN_AWMouseEvent(12,-4);in_strafe.state=1;focus_pair();
        require(!in_strafe.state && !mouse_has_moved && !mouseX && !mouseY,"GAME_INPUT_NOT_RESET");no_motion();
        require(key_dest==key_game,"FOCUS_CHANGED_DEST");
    }else require(0,"UNKNOWN_CASE");
    printf("PASS %s\n",argv[1]);return 0;
}
