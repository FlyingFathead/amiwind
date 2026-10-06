/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include "aw_save.h"
#include "aw_story.h"
server_t sv;server_static_t svs;client_state_t cl;viddef_t vid;
vec3_t vec3_origin;
int scr_copyeverything;
int mouseX,mouseY;
qboolean mouse_has_moved,noclip_anglehack;
kbutton_t in_strafe,in_mlook;
cvar_t sensitivity={"sensitivity","1",false,1},lookstrafe,m_side,m_pitch,m_yaw,m_forward;
cvar_t r_fullbright={"r_fullbright","0",false,false,0};
void Cvar_Set(char *name,char *value){assert(!strcmp(name,"r_fullbright"));r_fullbright.value=atof(value);}
void Cvar_SetValue(char *name,float value){assert(!strcmp(name,"r_fullbright"));r_fullbright.value=value;}
void V_StopPitchDrift(void){}
qboolean V_ExplicitPitchCentering(void){return false;}
void AW_MenuMouse(int x,int y){}
int AW_WorldUIActive(void){return 0;}
void AW_WorldUIMouse(int x,int y){}
int AW_WorldUIKey(int key,int down){return 0;}
int AW_ReaderActive(void){return 0;}
void AW_ReaderMouse(int x,int y){}
static int opening_locked,character_modal;
int AW_OpeningLocked(void){return opening_locked;}
int AW_CharacterActive(void){return character_modal;}
void AW_CharacterMouse(int x,int y){}
static void (*command)(void),(*combat_command)(void),(*torch_command)(void);static int argc=1,bad,captures,region_selected;static char *args[4];
static char queued[64],drawn[8192];
static int opens,restores,missing_return,many,missing_catalog,disabled;
static char printed[512];
static aw_character_t character;
void Cmd_AddCommand(char *s,void (*f)(void)){if(!strcmp(s,"aw_charplane"))command=f;else if(!strcmp(s,"aw_combattest"))combat_command=f;else if(!strcmp(s,"aw_torchtest"))torch_command=f;else assert(0);}
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?args[i]:"";}
void IN_AWClearButtons(void){}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
void Con_Printf(char *s,...){va_list ap;va_start(ap,s);vsnprintf(printed,sizeof(printed),s,ap);va_end(ap);}
int AW_SaveSnapshot(aw_save_t *out){captures++;out->character=character;return 1;}
void AW_SaveSnapshotRestore(const aw_save_t *out){restores++;character=out->character;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void AW_UIFill(int x,int y,int w,int h,int color){}
int AW_UIColor(int r,int g,int b){return 0;}
void AW_UIBox(int x,int y,int w,int h){}
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){}
int AW_UIScrollHit(int mx,int my,int x,int y,int height,int total,int visible,int top){
 if(mx<x || mx>=x+10 || my<y || my>=y+height || total<=visible)return -1;
 return my>=y+height-10?total-visible:0;
}
void S_LocalSound(char *s){}
void AW_UIVoiceSubtitle(const char *name,const char *text,double duration){}
static eval_t timings[4],hands[5];
static const char *timing_names[]={"aw_hand_idle","aw_hand_draw","aw_hand_lower","aw_hand_punch"};
static const char *hand_names[]={"aw_hand_goal","aw_hand_state","aw_torch","aw_hand_started","aw_attack_latched"};
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    int i;if(e==sv.edicts){for(i=0;i<4;i++)if(!strcmp(name,timing_names[i]))return timings+i;}
    else for(i=0;i<5;i++)if(!strcmp(name,hand_names[i]))return hands+i;
    return NULL;
}
static char stringstore[128];char *pr_strings=stringstore;
static edict_t actor;static model_t actor_model;static int allocations,model_loads,budget_ok=1;
edict_t *ED_Alloc(void){allocations++;memset(&actor,0,sizeof(actor));return &actor;}
char *ED_NewString(char *s){strcpy(stringstore+1,s);return stringstore+1;}
model_t *Mod_ForName(char *s,qboolean crash){assert(!crash && !strcmp(s,"gallery/m0000000000000003.mdl"));model_loads++;return &actor_model;}
int AW_AliasBudgetAllows(int vertices,int triangles){assert(vertices==3 && triangles==1);return budget_ok;}
int AW_RegionSelect(const char *name,const float *point,int intro){region_selected++;assert(!strcmp(name,"balmora"));assert(point[0]==800);return 1;}
void SV_LinkEdict(edict_t *e,qboolean touch){}
int AW_ConsoleCharWidth(void){return 8;}
int AW_ConsoleCharHeight(void){return 8;}
void AW_ConsoleCharacter(int x,int y,int c){int n=strlen(drawn);assert(n<8191);drawn[n]=(char)c;drawn[n+1]=0;}
int COM_FOpenFile(char *s,FILE **f){
    const char *catalog="AWG1 3\n7\tCREA\tm0000000000000001\tm0000000000000001\t100\t40\t150\tdagoth_ur_1\tDagoth Ur\n"
        "12\tCREA\tm0000000000000002\tm0000000000000002\t90\t40\t145\tdagoth_ur_2\tDagoth Ur\n"
        "3\tNPC_\tm0000000000000003\tm0000000000000004\t10\t8\t35\tclagius clanler\tClagius Clanler\n";
    opens++;
    if(!strcmp(s,"gallery/poses.txt")){*f=tmpfile();assert(*f);fputs("AWGP1\n",*f);rewind(*f);return 6;}
    if(!strcmp(s,"gallery/m0000000000000003.mdl")){
        byte header[72];memset(header,0,sizeof(header));memcpy(header,"IDPO",4);header[60]=3;header[64]=1;
        *f=tmpfile();assert(*f);assert(fwrite(header,1,sizeof(header),*f)==sizeof(header));rewind(*f);return sizeof(header);
    }
    if(!strcmp(s,"gallery/catalog.txt") && missing_catalog){*f=NULL;return -1;}
    if(!strcmp(s,"npc-gallery-disabled.txt")){
        if(!disabled){*f=NULL;return -1;}
        *f=tmpfile();assert(*f);return 1;
    }
    if(!strncmp(s,"maps/",5)){
        if(missing_return){*f=NULL;return -1;}
        *f=tmpfile();assert(*f);return 124;
    }
    *f=tmpfile();assert(*f);
    if(many){int i;fputs("AWG1 20\n",*f);for(i=1;i<=20;i++)fprintf(*f,"%d\tNPC_\tm0000000000000003\tm0000000000000004\t10\t8\t35\tresident%d\tResident %d\n",i,i,i);}
    else fputs(bad?"AWG1 1\n1\tCREA\t../../bad\t-\t1\t2\t3\tx\tBad\n":catalog,*f);
    rewind(*f);return 1;
}
static void draw(void){drawn[0]=0;AW_GalleryDraw();}
int main(void){
    edict_t player,world;client_t client;memset(&player,0,sizeof(player));memset(&client,0,sizeof(client));
    memset(&world,0,sizeof(world));sv.edicts=&world;sv.time=10;
    sv.active=true;strcpy(sv.name,"balmora");svs.maxclients=1;svs.clients=&client;client.edict=&player;
    player.v.origin[0]=800;player.v.origin[2]=57;player.v.movetype=MOVETYPE_WALK;cl.viewangles[1]=91;vid.width=320;vid.height=200;player.v.health=73;character.level=12;
    AW_StoryReset(1);
    args[0]="aw_charplane";AW_GalleryInit();assert(command);
    missing_catalog=1;command();assert(!captures && !queued[0] && strstr(printed,"catalogue missing"));
    disabled=1;command();assert(!captures && !queued[0] && strstr(printed,"--no-npc-gallery"));
    missing_catalog=disabled=0;command();assert(captures==1 && !strcmp(queued,"map charplane\n"));
    strcpy(sv.name,"charplane");AW_GallerySpawn(&player);draw();assert(strstr(drawn,"#7 Dagoth Ur"));
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202)); /* ordinary gallery stays restricted */
    AW_GalleryKey('N',1,1,0);draw();assert(strstr(drawn,"#12 Dagoth Ur"));
    AW_GalleryKey('N',1,1,0);draw();assert(strstr(drawn,"Clagius Clanler"));
    assert(AW_GalleryKey(K_MWHEELUP,1,0,0));draw();assert(strstr(drawn,"#12 Dagoth Ur"));
    assert(AW_GalleryKey(K_MWHEELUP,0,0,0));draw();assert(strstr(drawn,"#12 Dagoth Ur"));
    AW_GalleryKey(K_MWHEELDOWN,1,0,0);draw();assert(strstr(drawn,"Clagius Clanler"));
    AW_GalleryKey(K_MOUSE2,1,0,0);assert(AW_GalleryModal());
    AW_GalleryKey(K_MOUSE2,0,0,0);assert(AW_GalleryModal());
    AW_GalleryKey(K_MOUSE2,1,0,0);assert(!AW_GalleryModal());
    AW_GalleryKey('B',1,1,0);draw();assert(strstr(drawn,"Base body"));
    argc=2;args[1]="DAGOTHUR";command();draw();assert(strstr(drawn,"#7 Dagoth Ur") && strstr(drawn,"2 matches"));
    args[1]="dagoth_ur_2";command();draw();assert(strstr(drawn,"#12 Dagoth Ur"));
    args[1]="3";command();draw();assert(strstr(drawn,"Clagius Clanler"));
    AW_GalleryKey(K_ENTER,1,0,0);AW_GalleryKey('7',1,0,0);AW_GalleryKey(K_ENTER,1,0,0);draw();assert(strstr(drawn,"#7 Dagoth Ur"));
    bad=1;queued[0]=0;command();assert(!queued[0]);draw();assert(strstr(drawn,"Invalid gallery"));bad=0;
    /* Help only intercepts F1 inside the gallery. Ordinary drawing never opens
     * the disk catalogue. Modal text entry cannot leak walking commands. */
    {int before=opens;draw();draw();assert(opens==before);}
    AW_GalleryKey(K_F1,1,0,0);draw();assert(strstr(drawn,"Ctrl+X") && strstr(drawn,"dbg gallery exit"));
    AW_GalleryKey(K_F1,1,0,0);
    AW_GalleryKey(K_TAB,1,0,0);draw();assert(strstr(drawn,"Gallery browser") && strstr(drawn,"3 matches"));
    {int before=opens;AW_GalleryKey('C',1,0,0);AW_GalleryKey('L',1,0,0);AW_GalleryKey('A',1,0,0);assert(opens==before);}
    AW_GalleryKey(K_ENTER,1,0,0);draw();assert(strstr(drawn,"1 matches") && strstr(drawn,"Clagius Clanler"));
    AW_GalleryKey(K_ENTER,1,0,0);draw();assert(!strstr(drawn,"Gallery browser") && strstr(drawn,"#3 Clagius Clanler"));
    AW_GalleryKey('b',1,0,0);AW_GalleryKey('U',1,0,0);AW_GalleryKey('R',1,0,0);
    AW_GalleryKey(' ',1,0,0);AW_GalleryKey('D',1,0,0);AW_GalleryKey('A',1,0,0);
    AW_GalleryKey(K_ENTER,1,0,0);draw();assert(strstr(drawn,"2 matches"));
    AW_GalleryKey(K_DOWNARROW,1,0,0);AW_GalleryKey(K_ENTER,1,0,0);draw();assert(strstr(drawn,"#12 Dagoth Ur"));
    many=1;AW_GalleryKey(K_TAB,1,0,0);assert(AW_GalleryModal());
    {usercmd_t move;memset(&move,0,sizeof(move));cl.viewangles[0]=12;cl.viewangles[1]=91;
     IN_AWMouseEvent(25,10);IN_Move(&move);
     assert(cl.viewangles[0]==12 && cl.viewangles[1]==91 && !mouse_has_moved);
     assert(!move.forwardmove && !move.sidemove && !move.upmove);}
    assert(Key_AmigaRaw(0x68)==K_PGUP && Key_AmigaRaw(0xe9)==K_PGDN);
    AW_GalleryKey(Key_AmigaRaw(0x49),1,0,0);draw();assert(strstr(drawn,"Resident 7"));
    AW_GalleryKey(Key_AmigaRaw(0xc8),1,0,0);draw();assert(strstr(drawn,"Resident 1"));
    AW_GalleryKey(K_DOWNARROW,1,1,0);draw();assert(strstr(drawn,"Resident 7"));
    AW_GalleryKey(K_END,1,0,0);draw();assert(strstr(drawn,"Resident 19") && strstr(drawn,"Resident 20"));
    AW_GalleryKey(K_HOME,1,0,0);
    AW_GalleryKey(K_MWHEELDOWN,1,0,0);AW_GalleryKey(K_ENTER,1,0,0);draw();assert(strstr(drawn,"#2 Resident 2"));
    AW_GalleryKey(K_TAB,1,0,0);AW_GalleryMouse(-150,-52); // first row, second line
    AW_GalleryKey(K_MOUSE1,1,0,0);draw();assert(!AW_GalleryModal() && strstr(drawn,"#1 Resident 1"));
    AW_GalleryKey(K_TAB,1,0,0);AW_GalleryMouse(145,50); // scrollbar bottom
    AW_GalleryKey(K_MOUSE1,1,0,0);AW_GalleryKey(K_MOUSE1,0,0,0);draw();assert(strstr(drawn,"Resident 15"));
    AW_GalleryKey(K_ESCAPE,1,0,0);assert(!AW_GalleryModal());many=0;
    character.level=99;player.v.health=1;missing_return=1;queued[0]=0;
    AW_GalleryKey('x',1,0,1);assert(!queued[0] && !restores);
    missing_return=0;AW_GalleryKey('x',1,0,1);
    assert(region_selected==1 && !strcmp(queued,"map balmora\n"));
    strcpy(sv.name,"balmora");AW_GallerySpawn(&player);assert(player.v.origin[0]==800 && player.v.origin[2]==57 && cl.viewangles[1]==91 && player.v.health==73 && character.level==12);
    assert(!AW_GalleryKey(K_F1,1,0,0) && !AW_GalleryKey(K_TAB,1,0,0));
    /* Empty combat mode reuses the map but needs no NPC catalogue, footprint,
     * actor allocation or all-appearance model load. Invalid inputs retain the
     * live game. Hands run the usual action state machine and attack binding. */
    argc=1;assert(combat_command);queued[0]=0;missing_catalog=1;
    {int before=captures;combat_command();assert(captures==before && !queued[0]);}
    timings[0]._float=2;timings[1]._float=.4f;timings[2]._float=.3f;timings[3]._float=.8f;
    missing_return=1;
    {int before=captures;combat_command();assert(captures==before && !queued[0]);}
    missing_return=0;hands[0]._float=1;hands[2]._float=1;
    aw_story.stage=AW_STAGE_RACE;opening_locked=1;
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    combat_command();assert(!strcmp(queued,"map charplane\n"));
    /* SV_SpawnServer invokes this real hook after ED_LoadFromFile, before
     * sv.active=true. Missing authored test-map timing fields start at zero. */
    strcpy(sv.name,"charplane");sv.active=false;memset(timings,0,sizeof(timings));
    assert(!AW_GalleryActive() && !AW_TorchTestActive());
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    {int before=opens;AW_GalleryEntities();assert(opens==before);}
    assert(timings[0]._float==2 && timings[1]._float==.4f && timings[2]._float==.3f && timings[3]._float==.8f);
    sv.active=true;
    AW_GallerySpawn(&player);assert(player.v.origin[0]==0 && player.v.origin[2]==17);
    assert(hands[0]._float==1 && hands[1]._float==1 && hands[2]._float==0);
    assert(AW_IntroButtons(3)==3 && AW_IntroImpulse(202)==202);
    {usercmd_t move;memset(&move,0,sizeof(move));move.forwardmove=42;AW_IntroMove(&move);assert(move.forwardmove==42);}
    character_modal=1;assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));character_modal=0;
    assert(!AW_GalleryKey(K_MOUSE1,1,0,0) && !AW_GalleryKey('f',1,0,0));
    assert(!AW_GalleryKey(K_TAB,1,0,0) && !AW_GalleryModal());
    draw();assert(strstr(drawn,"Combat test") && !strstr(drawn,"Dagoth"));
    {int before=opens;draw();draw();assert(opens==before);}
    argc=2;args[1]="punch";combat_command();assert(hands[1]._float==3 && hands[3]._float==10 && hands[4]._float==0);
    args[1]="lower";combat_command();assert(hands[1]._float==4 && hands[0]._float==0);
    args[1]="idle";combat_command();assert(hands[1]._float==2 && hands[0]._float==1);
    args[1]="draw";combat_command();assert(hands[1]._float==1);
    player.v.origin[0]=999;args[1]="center";combat_command();assert(player.v.origin[0]==0);
    AW_GalleryKey(K_F1,1,0,0);draw();assert(AW_GalleryModal() && strstr(drawn,"dbg combattest"));
    assert(AW_GalleryKey(K_MOUSE1,1,0,0));AW_GalleryKey(K_ESCAPE,1,0,0);assert(!AW_GalleryModal());
    queued[0]=0;command();assert(!queued[0] && strstr(printed,"Exit combat"));
    args[1]="exit";combat_command();assert(!strcmp(queued,"map balmora\n"));
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202) && aw_story.stage==AW_STAGE_RACE);
    strcpy(sv.name,"balmora");AW_GallerySpawn(&player);
    assert(player.v.origin[0]==800 && player.v.health==73 && character.level==12);
    assert(hands[0]._float==1 && hands[2]._float==1);
    /* Separate dark room: no catalogue required, real common capture/return,
     * valid source timing, scoped fullbright reset and ordinary V binding. */
    assert(torch_command);argc=1;queued[0]=0;r_fullbright.value=1;
    timings[0]._float=NAN;
    {int before=captures;torch_command();assert(captures==before && !queued[0] && r_fullbright.value==1);}
    timings[0]._float=2;missing_return=1;
    {int before=captures;torch_command();assert(captures==before && !queued[0] && r_fullbright.value==1);}
    missing_return=0;torch_command();assert(!strcmp(queued,"map torchtest\n") && r_fullbright.value==0);
    /* A pending test session must not inject fields into another loading map. */
    sv.active=false;strcpy(sv.name,"balmora");memset(timings,0,sizeof(timings));
    {int before=opens;AW_GalleryEntities();assert(opens==before && !allocations && !model_loads);}
    assert(timings[0]._float==0 && timings[1]._float==0 && timings[2]._float==0 && timings[3]._float==0);
    strcpy(sv.name,"torchtest");assert(!AW_TorchTestActive() && !AW_GalleryActive());
    memset(timings,0,sizeof(timings));
    {int before=opens;AW_GalleryEntities();assert(opens==before && !allocations && !model_loads);}
    assert(timings[0]._float==2 && timings[1]._float==.4f && timings[2]._float==.3f && timings[3]._float==.8f);
    sv.active=true;assert(AW_TorchTestActive() && AW_GalleryActive());
    AW_GallerySpawn(&player);assert(player.v.origin[0]==64 && player.v.origin[2]==17 && hands[0]._float==1 && hands[2]._float==0);
    assert(!AW_GalleryKey('v',1,0,0) && !AW_GalleryKey(K_TAB,1,0,0));
    assert(AW_IntroButtons(3)==3 && AW_IntroImpulse(202)==202);
    draw();assert(strstr(drawn,"Torch test") && strstr(drawn,"Empty room"));
    {int before=opens;draw();draw();assert(opens==before);}
    AW_GalleryKey(K_F1,1,0,0);draw();assert(strstr(drawn,"dbg torchtest") && AW_GalleryModal());
    AW_GalleryKey(K_ESCAPE,1,0,0);assert(!AW_GalleryModal());
    player.v.origin[0]=99;argc=2;args[1]="center";torch_command();assert(player.v.origin[0]==64);
    queued[0]=0;argc=1;combat_command();assert(!queued[0]);
    /* Optional NPC: missing/rejected records keep the room. Only one fitting
     * model is loaded, and no footprint/all-catalogue model batch is requested. */
    argc=3;args[1]="npc";args[2]="clagius";torch_command();assert(!queued[0]);
    missing_catalog=0;args[2]="7";torch_command();assert(!queued[0] && strstr(printed,"needs an NPC"));
    argc=4;args[2]="Clagius";args[3]="Clanler";torch_command();assert(!strcmp(queued,"map torchtest\n"));
    actor_model.mins[0]=-20;actor_model.mins[1]=-10;actor_model.mins[2]=-5;
    actor_model.maxs[0]=20;actor_model.maxs[1]=10;actor_model.maxs[2]=35;
    sv.active=false;AW_GalleryEntities();assert(allocations==1 && model_loads==1 && actor.v.solid==SOLID_NOT);
    assert(!AW_TorchTestActive() && !AW_GalleryActive());sv.active=true;
    assert(actor.v.origin[0]==-40 && actor.v.origin[2]==5.25f);draw();assert(strstr(drawn,"Clagius Clanler"));
    actor_model.maxs[0]=200;AW_GalleryEntities();assert(allocations==1);draw();assert(strstr(drawn,"does not fit"));
    actor_model.maxs[0]=20;budget_ok=0;AW_GalleryEntities();assert(allocations==1);budget_ok=1;
    argc=2;args[1]="empty";torch_command();
    {int before=opens;AW_GalleryEntities();assert(opens==before && allocations==1);}
    args[1]="exit";missing_return=1;queued[0]=0;torch_command();assert(!queued[0] && AW_TorchTestActive() && r_fullbright.value==0);
    assert(AW_IntroButtons(3)==3 && AW_IntroImpulse(202)==202);
    missing_return=0;torch_command();assert(!strcmp(queued,"map balmora\n"));
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    strcpy(sv.name,"balmora");AW_GallerySpawn(&player);
    assert(!AW_TorchTestActive() && !AW_GalleryActive() && r_fullbright.value==1);
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202) && aw_story.stage==AW_STAGE_RACE);
    {usercmd_t move;memset(&move,0,sizeof(move));move.forwardmove=42;AW_IntroMove(&move);assert(!move.forwardmove);}
    strcpy(sv.name,"charplane");assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    strcpy(sv.name,"torchtest");assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    assert(player.v.origin[0]==800 && player.v.health==73 && character.level==12 && hands[0]._float==1 && hands[2]._float==1);
    return 0;
}
