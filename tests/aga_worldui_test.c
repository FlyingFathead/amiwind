/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_state.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_save.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;viddef_t vid;
aw_story_t aw_story;aw_character_t aw_character;
aw_race_t aw_races[16];aw_class_t aw_classes[32];
aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
keydest_t key_dest=key_game;int scr_copyeverything;
static void (*map_command)(void),(*journal_command)(void),(*teleport_command)(void);
static int missing,corrupt,opens,jumps,jump_available=1,red_pixels,story_restricted;static float destination[3];static char drawn[16384];
static byte pixels[320*200];
static const char title[]="A long quest heading which must wrap completely within one journal page without losing text";
static int heading_rows,marker_x=-1,marker_y=-1,char_width=4,region_calls;
static char footer[80];static int footer_left,footer_right;
static const char *region_override;
static int cyan_pixels,cyan_left,cyan_right,cyan_top,cyan_bottom,button_x,button_y;
/* Model the registered values used by the real panel; do not bypass mode logic. */
static cvar_t *map_vars[2];static int map_var_count,debug_overlays=1;
void Cvar_RegisterVariable(cvar_t *v){assert(map_var_count<2);v->value=atof(v->string);map_vars[map_var_count++]=v;}
void Cvar_SetValue(char *name,float value){int i;for(i=0;i<map_var_count;i++)if(!strcmp(name,map_vars[i]->name)){map_vars[i]->value=value;return;}assert(0);}
int AW_DebugOverlaysEnabled(void){return debug_overlays;}
int Cmd_Argc(void){return 1;}
const char *AW_RegionNameAt(const float *p){region_calls++;return region_override?region_override:p[0]<0?"West test region":"East test region";}
int AW_MapTeleport(const float *p){int i;for(i=0;i<3;i++)destination[i]=p[i];if(!jump_available)return 0;jumps++;return 1;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_teleport_map"))teleport_command=fn;else if(!strcmp(name,"aw_worldmap"))map_command=fn;else if(!strcmp(name,"aw_journal"))journal_command=fn;}
void IN_AWClearButtons(void){}
int AW_StoryRestricted(void){return story_restricted;}
int AW_ReaderActive(void){return 0;}
int AW_CharacterActive(void){return 0;}
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
void AW_UIFill(int x,int y,int w,int h,int c){
    if(c==AW_UIColor(48,240,240) && w==1 && h==1){
        cyan_pixels++;if(x<cyan_left)cyan_left=x;if(x>cyan_right)cyan_right=x;
        if(y<cyan_top)cyan_top=y;if(y>cyan_bottom)cyan_bottom=y;
        assert(x>=4 && x<316 && y>=19 && y<173);
    }
    if(w==72 && h==15){button_x=x;button_y=y;}
if(c==AW_UIColor(255,32,32))red_pixels++;assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);if(w==9 && h==1){marker_x=x+4;marker_y=y;}}
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){}
int AW_UIScrollHit(int mx,int my,int x,int y,int h,int total,int visible,int top){return -1;}
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
static void draw(void){cyan_pixels=red_pixels=0;cyan_left=cyan_top=1000;cyan_right=cyan_bottom=-1;button_x=button_y=-1;drawn[0]=footer[0]=0;heading_rows=0;marker_x=marker_y=-1;assert(AW_WorldUIDraw());}
/* Exercise physical right/middle virtual keys through the real panel.
 * Map-marker movement proves pan state; host pointer transport is separate. */
static void drag_test_require(int good,const char *reason)
{
    if(!good){fprintf(stderr,"FAIL %s\n",reason);exit(1);}
}
static void drag_test_point(int x,int y)
{
    AW_WorldUIMouse(-1000,-1000);AW_WorldUIMouse(x,y);
}
static void drag_test_start(int teleport)
{
    if(AW_WorldUIActive())AW_WorldUIKey(K_ESCAPE,1);
    key_dest=key_game;Cvar_SetValue("aw_map_mode",0);
    jumps=0;jump_available=1;
    if(teleport)teleport_command();else map_command();
    drag_test_require(AW_WorldUIActive(),"panel failed to open");
    AW_WorldUIKey(K_HOME,1);drag_test_point(160,100);draw();
    drag_test_require(marker_x>20 && marker_y>20,"synthetic player marker missing");
}
static void drag_test_assert_shift(int x,int y,int dx,int dy,const char *reason)
{
    draw();drag_test_require(abs(marker_x-x-dx)<=1 && abs(marker_y-y-dy)<=1,reason);
}
static void drag_test_secondary(int button)
{
    int x,y;
    drag_test_start(1);x=marker_x;y=marker_y;
    AW_WorldUIKey(button,1);AW_WorldUIMouse(12,-6);
    drag_test_assert_shift(x,y,12,-6,button==K_MOUSE3?"RIGHT_DRAG_NOT_STARTED":"MIDDLE_DRAG_NOT_STARTED");
    x=marker_x;y=marker_y;AW_WorldUIKey(button,0);AW_WorldUIMouse(-5,3);
    drag_test_assert_shift(x,y,0,0,"secondary release left drag active");
    AW_WorldUIKey(K_ENTER,1);drag_test_require(jumps==0 && AW_WorldUIActive(),"secondary drag selected or confirmed teleport");
}
static void drag_test_normal(void)
{
    int x,y;
    drag_test_start(0);x=marker_x;y=marker_y;
    AW_WorldUIKey(K_MOUSE3,1);AW_WorldUIMouse(7,-3);AW_WorldUIKey(K_MOUSE3,0);
    drag_test_assert_shift(x,y,0,0,"ordinary right button acquired drag");
    AW_WorldUIKey(K_MOUSE2,1);AW_WorldUIMouse(-7,3);AW_WorldUIKey(K_MOUSE2,0);
    drag_test_assert_shift(x,y,0,0,"ordinary middle button acquired drag");
    AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIMouse(12,-6);
    drag_test_assert_shift(x,y,12,-6,"ordinary left drag regressed");
    x=marker_x;y=marker_y;AW_WorldUIKey(K_MOUSE3,0);AW_WorldUIMouse(5,2);
    drag_test_assert_shift(x,y,5,2,"unrelated right release interrupted ordinary left drag");
    x=marker_x;y=marker_y;AW_WorldUIKey(K_MOUSE1,0);AW_WorldUIMouse(-5,-2);
    drag_test_assert_shift(x,y,0,0,"ordinary left release failed");
    AW_WorldUIKey('m',1);drag_test_require(!AW_WorldUIActive(),"ordinary M close regressed");
}
static void drag_test_selection(void)
{
    int x,y,i;
    drag_test_start(1);x=marker_x;y=marker_y;
    /* Two complete left clicks select; neither is an implicit confirmation. */
    for(i=0;i<2;i++){AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);}
    drag_test_require(jumps==0 && AW_WorldUIActive(),"double click teleported without confirmation");
    AW_WorldUIMouse(6,-3);drag_test_assert_shift(x,y,0,0,"teleport left click started panning");
    red_pixels=0;draw();drag_test_require(red_pixels==22,"left selection crosshair missing");
    AW_WorldUIKey(K_ENTER,1);drag_test_require(jumps==1 && !AW_WorldUIActive(),"explicit confirmation regressed");
}
static void drag_test_boundaries(void)
{
    int x,y;
    drag_test_start(1);x=marker_x;y=marker_y;drag_test_point(30,8);
    AW_WorldUIKey(K_MOUSE3,1);AW_WorldUIMouse(0,45);AW_WorldUIKey(K_MOUSE3,0);
    drag_test_assert_shift(x,y,0,0,"right press above map acquired drag");
    drag_test_point(280,190);AW_WorldUIKey(K_MOUSE3,1);AW_WorldUIMouse(-10,-25);AW_WorldUIKey(K_MOUSE3,0);
    drag_test_assert_shift(x,y,0,0,"right press in footer acquired drag");
    drag_test_require(AW_WorldUIActive() && jumps==0,"right footer press confirmed or closed");
}
static void drag_test_cancel(void)
{
    int x,y;
    drag_test_start(1);AW_WorldUIKey(K_MOUSE3,1);AW_WorldUIMouse(10,4);
    AW_WorldUIKey(K_ESCAPE,1);drag_test_require(!AW_WorldUIActive() && jumps==0,"Escape failed to cancel drag");
    /* Open normally without issuing the old mouse release. Closing must reset drag. */
    map_command();AW_WorldUIKey(K_HOME,1);draw();x=marker_x;y=marker_y;
    AW_WorldUIMouse(8,-3);drag_test_assert_shift(x,y,0,0,"drag leaked across close/reopen");
    drag_test_require(!AW_WorldUIKey(K_F10,1) && !AW_WorldUIActive(),"F10 route regressed");
}

static void map_click(int button){AW_WorldUIKey(button,1);AW_WorldUIKey(button,0);}
static int32_t marked(const char *suffix){char id[64];sprintf(id,"amiwind:map:marker:%s",suffix);return AW_StateGet(&aw_state,AW_GLOBAL,id);}
static void marker_save_roundtrip(void)
{
    static aw_save_t saved,decoded;static unsigned char bytes[AW_SAVE_BYTES];int length;
    memset(&saved,0,sizeof(saved));saved.sequence=1;saved.profile=1;
    strcpy(saved.scene,"balmora");strcpy(saved.story.name,"Synthetic");
    saved.story.stage=AW_STAGE_RELEASED;saved.story.ship_disabled=1;saved.story.captain=-1;
    saved.character.level=1;saved.character.hair=1;
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"chargenstate",-1));saved.state=aw_state;
    length=AW_SaveEncode(bytes,sizeof(bytes),&saved);assert(length>0 && !memcmp(bytes,"AWS4",4));
    assert(AW_SaveDecode(bytes,length,&decoded));AW_StateReset();aw_state=decoded.state;
    assert(!memcmp(&aw_state,&saved.state,sizeof(aw_state)));
}
static void custom_marker_test(void)
{
    int x,y,i,old_count;int32_t source_x,source_y;static aw_state_t before;
    AW_StateReset();debug_overlays=1;drag_test_start(0);
    /* One source-world marker: a click never invokes the teleport path. */
    drag_test_point(120,80);map_click(K_MOUSE1);draw();
    assert(marked("ready")==1 && marked("x")==-4369 && marked("y")==1748);
    assert(cyan_pixels==17 && red_pixels==0 && jumps==0 && key_dest==key_menu);
    assert(abs((cyan_left+cyan_right)/2-120)<=1 && abs((cyan_top+cyan_bottom)/2-80)<=1);
    source_x=marked("x");source_y=marked("y");old_count=aw_state.count[AW_GLOBAL];
    AW_WorldUIKey(K_MWHEELUP,1);draw();x=(cyan_left+cyan_right)/2;y=(cyan_top+cyan_bottom)/2;
    assert(abs(x-80)<=1 && abs(y-64)<=1);
    AW_WorldUIKey(K_RIGHTARROW,1);draw();assert(abs((cyan_left+cyan_right)/2-x+24)<=1);
    AW_WorldUIKey(K_LEFTARROW,1);AW_WorldUIKey(K_MWHEELDOWN,1);draw();
    assert(abs((cyan_left+cyan_right)/2-120)<=1 && abs((cyan_top+cyan_bottom)/2-80)<=1);
    assert(marked("x")==source_x && marked("y")==source_y && aw_state.count[AW_GLOBAL]==old_count);
    /* Inverse pick uses the same source transform after zoom AND pan. */
    AW_WorldUIKey(K_MWHEELUP,1);AW_WorldUIKey(K_RIGHTARROW,1);
    drag_test_point(100,80);map_click(K_MOUSE1);assert(marked("x")==-1966 && marked("y")==874);
    AW_WorldUIKey(K_HOME,1);drag_test_point(120,80);map_click(K_MOUSE1);draw();
    /* The complete drag delta is applied at threshold, without placing a marker. */
    drag_test_point(120,80);x=marker_x;y=marker_y;AW_WorldUIKey(K_MOUSE1,1);
    AW_WorldUIMouse(2,1);drag_test_assert_shift(x,y,0,0,"click jitter panned map");
    AW_WorldUIMouse(10,-7);drag_test_assert_shift(x,y,12,-6,"threshold lost initial pan delta");
    AW_WorldUIKey(K_MOUSE1,0);assert(marked("x")==source_x && marked("y")==source_y);
    AW_WorldUIKey(K_HOME,1);drag_test_point(4,96);before=aw_state;map_click(K_MOUSE1);draw();
    assert(!memcmp(&before,&aw_state,sizeof(before)) && strstr(drawn,"Outside map bounds"));
    drag_test_point(3,96);map_click(K_MOUSE1);assert(!memcmp(&before,&aw_state,sizeof(before)));
    /* Letterbox edge is invalid; first and last source pixels remain bounded. */
    drag_test_point(86,22);map_click(K_MOUSE1);draw();
    assert(marked("x")>=-8192 && marked("x")<-8000 && marked("y")<=8192 && cyan_pixels>0 && cyan_left>=4);
    drag_test_point(234,170);map_click(K_MOUSE1);draw();
    assert(marked("x")<8192 && marked("x")>-8192 && marked("y")>-8192 && cyan_bottom<173);
    drag_test_point(120,80);map_click(K_MOUSE1);source_x=marked("x");source_y=marked("y");
    /* Save/reload and close/reopen keep source position, independent of map pan. */
    marker_save_roundtrip();AW_WorldUIKey('m',1);map_command();draw();
    assert(marked("x")==source_x && marked("y")==source_y && cyan_pixels==17);
    AW_WorldUIKey('c',1);draw();assert(!marked("ready") && cyan_pixels==0 && strstr(drawn,"Marker cleared"));
    marker_save_roundtrip();assert(!marked("ready"));
    drag_test_point(120,80);map_click(K_MOUSE1);drag_test_point(260,178);map_click(K_MOUSE1);
    assert(!marked("ready") && AW_WorldUIActive() && jumps==0);
    /* Focus loss cancels a pending click; explicit teleport and journal cannot place/clear a marker. */
    drag_test_point(120,80);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUICancelDrag();AW_WorldUIKey(K_MOUSE1,0);assert(!marked("ready"));
    map_click(K_MOUSE1);before=aw_state;AW_WorldUIKey(K_ESCAPE,1);teleport_command();
    map_click(K_MOUSE1);AW_WorldUIKey('c',1);assert(!memcmp(&before,&aw_state,sizeof(before)));
    AW_WorldUIKey(K_ESCAPE,1);journal_command();map_click(K_MOUSE1);AW_WorldUIKey('c',1);
    assert(!memcmp(&before,&aw_state,sizeof(before)));AW_WorldUIKey(K_ESCAPE,1);
    /* Insufficient slots refuse atomically; no dynamic allocation or table growth. */
    AW_StateReset();for(i=0;i<AW_STATE_VALUES-2;i++){char id[16];sprintf(id,"fixture%d",i);assert(AW_StateSet(&aw_state,AW_GLOBAL,id,i));}
    map_command();AW_WorldUIKey(K_HOME,1);drag_test_point(120,80);before=aw_state;map_click(K_MOUSE1);draw();
    assert(!memcmp(&before,&aw_state,sizeof(before)) && strstr(drawn,"globals full"));
    AW_WorldUIKey('c',1);assert(!memcmp(&before,&aw_state,sizeof(before)));
    AW_WorldUIKey(K_ESCAPE,1);AW_StateReset();
}
static void normal_debug_teleport_test(void)
{
    int x,y;float expected_x,expected_y;static aw_state_t before;
    debug_overlays=1;drag_test_start(0);AW_WorldUIKey(K_ESCAPE,1);
    Cvar_SetValue("aw_map_mode",1);map_command();AW_WorldUIKey(K_HOME,1);draw();
    assert(strstr(drawn,"DEBUG MAP") && map_vars[0]->value==0);
    /* Right click selects and draws the same destination cross as the explicit command. */
    drag_test_point(120,80);map_click(K_MOUSE3);draw();
    assert(red_pixels==22 && jumps==0 && button_x==244 && button_y==156 && key_dest==key_menu);
    x=marker_x;y=marker_y;map_click(K_MOUSE3);drag_test_assert_shift(x,y,0,0,"right click moved map");
    assert(jumps==0);expected_x=-4369.0667f;expected_y=1747.6267f;
    /* A normal marker may coexist; red selection remains independent. */
    drag_test_point(190,90);map_click(K_MOUSE1);draw();assert(cyan_pixels==17 && red_pixels==22 && jumps==0);
    before=aw_state;AW_WorldUIKey(K_MWHEELUP,1);AW_WorldUIKey(K_RIGHTARROW,1);draw();
    drag_test_point(button_x+4,button_y+5);map_click(K_MOUSE3);assert(jumps==0);
    jump_available=0;map_click(K_MOUSE1);draw();
    assert(jumps==0 && AW_WorldUIActive() && strstr(drawn,"Destination unavailable"));
    assert(fabs(destination[0]-expected_x)<.02 && fabs(destination[1]-expected_y)<.02);
    assert(!memcmp(&before,&aw_state,sizeof(before)));jump_available=1;map_click(K_MOUSE1);
    assert(jumps==1 && !AW_WorldUIActive() && key_dest==key_game);
    map_command();AW_WorldUIKey(K_HOME,1);draw();assert(red_pixels==0 && button_x==-1);
    drag_test_point(4,96);map_click(K_MOUSE3);draw();assert(red_pixels==0 && button_x==-1);
    AW_WorldUIKey(K_ENTER,1);assert(jumps==1);
    /* Tab changes invalidate pending debug selection; HUD-off M opens regular view. */
    drag_test_point(120,80);map_click(K_MOUSE3);drag_test_point(280,8);map_click(K_MOUSE1);draw();
    assert(strstr(drawn,"IN-GAME MAP PROTOTYPE") && red_pixels==0 && button_x==-1);
    AW_WorldUIKey(K_ENTER,1);assert(jumps==1);AW_WorldUIKey(K_ESCAPE,1);
    debug_overlays=0;Cvar_SetValue("aw_map_mode",0);map_command();AW_WorldUIKey(K_HOME,1);draw();
    assert(strstr(drawn,"IN-GAME MAP PROTOTYPE") && map_vars[0]->value==1);
    drag_test_point(120,80);map_click(K_MOUSE3);AW_WorldUIKey(K_ENTER,1);draw();assert(red_pixels==0 && jumps==1);
    drag_test_point(20,8);map_click(K_MOUSE1);drag_test_point(120,80);map_click(K_MOUSE3);draw();
    assert(strstr(drawn,"DEBUG MAP") && red_pixels==0 && button_x==-1);
    AW_WorldUIKey(K_ESCAPE,1);key_dest=key_console;teleport_command();AW_WorldUIKey(K_HOME,1);
    drag_test_point(120,80);map_click(K_MOUSE1);draw();assert(red_pixels==22 && button_y==184);
    AW_WorldUIKey(K_ESCAPE,1);debug_overlays=1;AW_StateReset();
}

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
    assert(!strcmp(footer,"REGION: East test region") && footer_right==315);
    AW_WorldUIKey(K_LEFTARROW,1);draw();assert(!strcmp(footer,"REGION: East test region"));
    player.v.origin[0]=-16;draw();assert(!strcmp(footer,"REGION: West test region"));player.v.origin[0]=0;
    char_width=8;region_override="A deliberately long region name from a synthetic game record";draw();
    assert(footer_left>=96 && footer_right==315 && strstr(footer,"..."));char_width=4;region_override=NULL;
    AW_WorldUIKey('=',1);AW_WorldUIKey('p',1);AW_WorldUIKey('g',1);draw();
    assert(opens==before);AW_WorldUIKey('m',1);assert(!AW_WorldUIActive() && key_dest==key_game);
    /* Keep zoom/pan on reopen, update the live position without disk reads,
     * and preserve global position across a terrain XYZ rebase. */
    map_command();draw();
    {int x=marker_x,y=marker_y;
     assert(x>=0 && y>=0);before=opens;player.v.origin[0]=128;player.v.origin[1]=64;draw();
     assert(marker_x>x && marker_y<y && opens==before);
     x=marker_x;y=marker_y;AW_WorldUIKey('m',1);map_command();draw();
     assert(marker_x==x && marker_y==y);AW_WorldUIKey('m',1);
     strcpy(sv.name,"vf0000");player.v.origin[0]-=1024;player.v.origin[2]-=512;
     map_command();draw();assert(marker_x==x && marker_y==y && strstr(drawn,"XYZ 512 256 0"));
     AW_WorldUIKey('m',1);strcpy(sv.name,"balmora");player.v.origin[0]=player.v.origin[1]=player.v.origin[2]=0;
    }
    journal_command();draw();assert(strstr(drawn,"No dated journal"));AW_WorldUIKey('j',1);
    assert(AW_JournalAdd(&aw_state,"quest",1));assert(AW_JournalAdd(&aw_state,"quest",10));
    journal_command();draw();assert(strstr(drawn,"Another earned event."));
    assert(strstr(drawn,title) && heading_rows>1);
    before=opens;AW_WorldUIMouse(40,-70);AW_WorldUIKey(K_MOUSE1,1);assert(opens==before); /* Right-page heading is not a quest link. */
    AW_WorldUIMouse(-150,0);AW_WorldUIKey(K_MOUSE1,1);assert(opens>before); /* Left heading follows the quest. */
    AW_WorldUIKey(K_LEFTARROW,1);draw();assert(strstr(drawn,"Welcome Hors."));
    before=opens;draw();assert(opens==before); /* Drawing never fetches text. */
    AW_WorldUIKey(K_TAB,1);draw();assert(strstr(drawn,"Quests") && strstr(drawn,title));
    AW_WorldUIKey(K_ENTER,1);draw();assert(strstr(drawn,"Another earned event."));
    AW_WorldUIKey(K_BACKSPACE,1);draw();assert(strstr(drawn,"2/2"));
    assert(!AW_WorldUIKey(K_F10,1));assert(!AW_WorldUIActive() && key_dest==key_game);
    assert(aw_state.journal_count==2 && AW_StateGet(&aw_state,AW_JOURNAL,"quest")==10);
    map_command();key_dest=key_game;assert(!AW_WorldUIDraw() && !AW_WorldUIActive());
    journal_command();assert(AW_WorldUIActive());AW_WorldUIKey('j',1);
    strcpy(sv.name,"census");map_command();before=region_calls;draw();assert(strstr(drawn,"no exterior position"));
    assert(!strcmp(footer,"REGION: unavailable") && region_calls==before);
    strcpy(sv.name,"seyda");assert(!AW_WorldUIDraw() && !AW_WorldUIActive());
    /* Debug mode: exact title/instruction, red selected crosshair, explicit
     * confirmation button, source coordinates stable across zoom and panning. */
    assert(teleport_command);key_dest=key_console;teleport_command();
    assert(AW_WorldUIActive() && key_dest==key_menu);AW_WorldUIKey(K_HOME,1);draw();
    assert(strstr(drawn,"DEBUG TELEPORT") && strstr(drawn,"CLICK ON TARGET TO TELEPORT"));
    assert(!strstr(drawn,"Esc closeTELEPORT") && jumps==0);
    AW_WorldUIKey(K_ENTER,1);assert(jumps==0);
    /* Initial pointer is 160,100. A click selects without moving the player. */
    AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);red_pixels=0;draw();
    assert(red_pixels==22 && strstr(drawn,"TELEPORT") && strstr(drawn,"test region") && jumps==0);
    AW_WorldUIKey('=',1);AW_WorldUIKey(K_RIGHTARROW,1);draw();
    AW_WorldUIMouse(120,90); /* confirmation button: 280,190 */
    jump_available=0;AW_WorldUIKey(K_MOUSE1,1);draw();
    assert(jumps==0 && AW_WorldUIActive() && strstr(drawn,"Destination unavailable"));
    assert(fabs(destination[0])<.01 && fabs(destination[1]+436.9067)<.02);
    jump_available=1;AW_WorldUIKey(K_MOUSE1,1);
    assert(jumps==1 && !AW_WorldUIActive() && key_dest==key_game);
    /* Reopening must discard the old destination. Escape cancels. */
    teleport_command();AW_WorldUIKey(K_ENTER,1);assert(jumps==1);
    AW_WorldUIKey(K_ESCAPE,1);assert(!AW_WorldUIActive());
    map_command();draw();assert(!strstr(drawn,"DEBUG TELEPORT"));AW_WorldUIKey('m',1);
    /* The default hidden HUD must not disable map tabs or explicit commands.
     * Keep the independent debug-map availability setting authoritative. */
    strcpy(sv.name,"balmora");debug_overlays=0;Cvar_SetValue("aw_map_mode",1);map_command();AW_WorldUIKey(K_HOME,1);draw();
    assert(strstr(drawn,"IN-GAME MAP PROTOTYPE") && strstr(drawn,"Balmora"));
    AW_WorldUIKey('m',1);debug_overlays=0;
    map_command();
    AW_WorldUIMouse(-1000,-1000);AW_WorldUIMouse(20,8);
    AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);draw();
    assert(map_vars[0]->value==0 && strstr(drawn,"DEBUG MAP"));
    assert(strstr(drawn,"Balmora") && marker_x>=0);
    AW_WorldUIMouse(260,0);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);draw();
    assert(map_vars[0]->value==1 && strstr(drawn,"IN-GAME MAP PROTOTYPE"));
    AW_WorldUIKey('m',1);key_dest=key_console;teleport_command();
    assert(AW_WorldUIActive() && key_dest==key_menu);draw();
    assert(strstr(drawn,"DEBUG TELEPORT"));AW_WorldUIKey(K_ESCAPE,1);
    /* Availability is distinct from HUD visibility and reports refusal. */
    Cvar_SetValue("aw_map_mode",0);Cvar_SetValue("aw_map_debug_available",0);
    map_command();draw();assert(map_vars[0]->value==1);
    AW_WorldUIMouse(-1000,-1000);AW_WorldUIMouse(20,8);
    AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);
    assert(map_vars[0]->value==1);AW_WorldUIKey('m',1);
    key_dest=key_console;teleport_command();
    assert(!AW_WorldUIActive() && key_dest==key_console);
    assert(strstr(console_message,"aw_map_debug_available"));
    Cvar_SetValue("aw_map_debug_available",1);story_restricted=1;
    teleport_command();assert(!AW_WorldUIActive() && key_dest==key_console);
    assert(strstr(console_message,"active single-player gameplay"));
    story_restricted=0;teleport_command();assert(AW_WorldUIActive());
    AW_WorldUIKey(K_ESCAPE,1);debug_overlays=1;
    strcpy(sv.name,"balmora");memset(player.v.origin,0,sizeof player.v.origin);
    drag_test_secondary(K_MOUSE3);drag_test_secondary(K_MOUSE2);
    drag_test_normal();drag_test_selection();drag_test_boundaries();drag_test_cancel();
    if(AW_WorldUIActive())AW_WorldUIKey(K_ESCAPE,1);
    custom_marker_test();normal_debug_teleport_test();
    return 0;
}
