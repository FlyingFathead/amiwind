/* SPDX-License-Identifier: GPL-2.0-or-later
 * Include the actual intro adapter to select its two internal prompt states. */
#include "aw_intro.c"
#include <assert.h>

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
keydest_t key_dest=key_game;viddef_t vid;refdef_t r_refdef;aw_story_t aw_story;
double host_frametime=.02,realtime;int scr_fullupdate,scr_copyeverything;
static byte palette[768],glyphs[16384],frame[64000];
byte *host_basepal=palette,*draw_chars=glyphs;
static cvar_t *freeze,*black;
int AW_CharacterActive(void){return 0;}int AW_ReaderActive(void){return 0;}
int AW_GalleryModal(void){return 0;}int AW_MovieActive(void){return 0;}
int AW_ReaderKey(int key){return 0;}int AW_CharacterKey(int key){return 0;}
void AW_CharacterDraw(void){}void AW_ReaderDraw(void){}
int AW_NavStart(edict_t *e,float *p){return 1;}
void IN_AWClearButtons(void){}
int COM_FOpenFile(char *s,FILE **f){*f=NULL;return -1;}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_modal_freeze"))freeze=c;else if(!strcmp(c->name,"aw_modal_black"))black=c;}
void Cvar_SetValue(char *s,float v){}
void Cmd_AddCommand(char *s,void(*fn)(void)){}
char *Cmd_Argv(int n){return "";}int Cmd_Argc(void){return 0;}

int main(void){
    int i,f,b;
    for(i=0;i<256;i++)palette[i*3]=palette[i*3+1]=palette[i*3+2]=i;
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame;
    r_refdef.vrect.height=152;AW_UIInit();
    sv.active=true;svs.maxclients=1;cls.state=ca_connected;cls.signon=SIGNONS;
    active=1;prompt=1;assert(AW_IntroPromptActive());
    for(f=0;f<=1;f++)for(b=0;b<=1;b++){
        freeze->value=f;black->value=b;
        assert(!AW_ModalWorldFrozen() && !AW_ModalWorldHidden());
        memset(frame,0x5a,sizeof(frame));AW_IntroDraw();
        for(i=0;i<320*152;i++)assert(frame[i]==0x5a);
    }
    /* Original name entry keeps its world background and ordinary input. */
    AW_IntroKey('A');assert(!strcmp(aw_story.name,"A"));AW_IntroKey(K_ENTER);
    assert(!AW_IntroPromptActive() && !AW_ModalWorldFrozen() && jiub_state==20);
    prompt=2;assert(AW_IntroPromptActive());
    assert(!AW_ModalWorldFrozen());memset(frame,0x5a,sizeof(frame));AW_IntroDraw();
    for(i=0;i<320*152;i++)assert(frame[i]==0x5a);
    return 0;
}
