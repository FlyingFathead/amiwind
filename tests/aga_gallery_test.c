/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include "aw_save.h"
server_t sv;server_static_t svs;client_state_t cl;viddef_t vid;
vec3_t vec3_origin;
int scr_copyeverything;
int mouseX,mouseY;
qboolean mouse_has_moved,noclip_anglehack;
kbutton_t in_strafe,in_mlook;
cvar_t sensitivity={"sensitivity","1",false,1},lookstrafe,m_side,m_pitch,m_yaw,m_forward;
void V_StopPitchDrift(void){}
void AW_MenuMouse(int x,int y){}
int AW_WorldUIActive(void){return 0;}
void AW_WorldUIMouse(int x,int y){}
int AW_WorldUIKey(int key,int down){return 0;}
int AW_ReaderActive(void){return 0;}
void AW_ReaderMouse(int x,int y){}
int AW_CharacterActive(void){return 0;}
void AW_CharacterMouse(int x,int y){}
static void (*command)(void);static int argc=1,bad,captures,region_selected;static char *args[4];
static char queued[64],drawn[8192];
static int opens,restores,missing_return,many;
static aw_character_t character;
void Cmd_AddCommand(char *s,void (*f)(void)){command=f;}
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?args[i]:"";}
void IN_AWClearButtons(void){}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
void Con_Printf(char *s,...){}
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
eval_t *GetEdictFieldValue(edict_t *e,char *name){return NULL;}
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
    edict_t player;client_t client;memset(&player,0,sizeof(player));memset(&client,0,sizeof(client));
    sv.active=true;strcpy(sv.name,"balmora");svs.maxclients=1;svs.clients=&client;client.edict=&player;
    player.v.origin[0]=800;player.v.origin[2]=57;player.v.movetype=MOVETYPE_WALK;cl.viewangles[1]=91;vid.width=320;vid.height=200;player.v.health=73;character.level=12;
    args[0]="aw_charplane";AW_GalleryInit();assert(command);command();assert(captures==1 && !strcmp(queued,"map charplane\n"));
    strcpy(sv.name,"charplane");AW_GallerySpawn(&player);draw();assert(strstr(drawn,"#7 Dagoth Ur"));
    AW_GalleryKey('N',1,1,0);draw();assert(strstr(drawn,"#12 Dagoth Ur"));
    AW_GalleryKey('N',1,1,0);draw();assert(strstr(drawn,"Clagius Clanler"));
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
     mouseX=25;mouseY=10;mouse_has_moved=true;IN_Move(&move);
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
    return 0;
}
