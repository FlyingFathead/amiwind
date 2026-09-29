/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
viddef_t vid;refdef_t r_refdef;keydest_t key_dest=key_game;double realtime,host_frametime=1;
client_static_t cls;server_t sv;server_static_t svs;int scr_copyeverything;
static byte pal[768],glyphs[16384],frame[64004];byte *host_basepal=pal,*draw_chars=glyphs;
static cvar_t *vars[16];static int count,prompt;
int AW_IntroPromptActive(void){return prompt;}
int AW_LoadingScreen(void){return 0;}int AW_MenuFrontEnd(void){return 0;}
double AW_SpeechRemaining(void){return 0;}
void Con_Printf(char *fmt,...){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);vars[count++]=c;}
void Cvar_SetValue(char *name,float v){int i;for(i=0;i<count;i++)if(!strcmp(name,vars[i]->name))vars[i]->value=v;}
void Cmd_AddCommand(char *s,void(*f)(void)){}
char *Cmd_Argv(int i){return "";}int Cmd_Argc(void){return 0;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int COM_FOpenFile(char *name,FILE **f){
    byte raw[2568];int i,size;
    size=strstr(name,"magic14")?14:strstr(name,"magic12")?12:0;
    if(!size){*f=NULL;return -1;}
    memset(raw,0,sizeof(raw));memcpy(raw,"AWF1",4);raw[4]=size;raw[5]=size+2;raw[7]=2;
    for(i=0;i<256;i++){raw[8+i*8+2]=4;raw[8+i*8+3]=8;raw[8+i*8+6]=6;}
    /* Descender with a negative left bearing exercises visible bounds. */
    raw[8+'g'*8+3]=10;raw[8+'g'*8+4]=254;raw[8+'g'*8+5]=3;
    memset(raw+2056,255,512);*f=tmpfile();assert(*f);fwrite(raw,1,sizeof(raw),*f);rewind(*f);return sizeof(raw);
}
static void clean(void){memset(frame,137,sizeof(frame));}
static int changed(int x,int y){return vid.buffer[y*320+x]!=137;}
static int framed(int x,int y){return vid.buffer[y*320+x]==AW_UIColor(151,131,87);}
int main(void){
    int i,x,y;
    for(i=0;i<256;i++)pal[i*3]=pal[i*3+1]=pal[i*3+2]=i;
    memset(glyphs,255,sizeof(glyphs));vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame+2;
    r_refdef.vrect.height=152;AW_UIInit();assert(AW_UIDialogueMethod()==2);
    Cvar_SetValue("aw_dialogue_box_layout",1);
    AW_UISubtitle("Speaker","AAAA\nBBBB\nCCCC",10);clean();AW_UIDraw();
    assert(changed(0,152) && !changed(0,151)); /* Unchanged panel footprint. */
    assert(changed(10,140) && !changed(9,140) && !changed(80,140)); /* No name plaque. */
    for(y=0;y<152;y++)for(x=80;x<320;x++)assert(!changed(x,y));
    assert(vid.buffer[160*320+10]!=0 && vid.buffer[176*320+10]!=0);
    Cvar_SetValue("aw_dialogue_box_display_method",1);clean();AW_UIDraw();
    for(i=0;i<152*320;i++)assert(vid.buffer[i]==137); /* Exact classic header stays inside. */
    assert(vid.buffer[158*320+10]!=0 && vid.buffer[174*320+10]!=0);
    Cvar_SetValue("aw_dialogue_box_display_method",2);assert(AW_UISetFontSize(12));clean();AW_UIDraw();
    assert(vid.buffer[159*320+10]!=0 && vid.buffer[173*320+10]!=0 && vid.buffer[187*320+10]!=0);
    prompt=1;clean();AW_UIDraw();for(i=0;i<64000;i++)assert(vid.buffer[i]==137);prompt=0;
    AW_UISubtitle("", "AAAA",10);clean();AW_UIDraw();for(i=0;i<152*320;i++)assert(vid.buffer[i]==137);
    clean();AW_UITargetName("Speaker");assert(changed(268,10) && !changed(267,10));
    for(i=0;i<152*320;i++)if(i/320>20)assert(vid.buffer[i]==137);
    AW_UISubtitle("Speaker","AAAA",10);
    Cvar_SetValue("aw_dialogue_box_display_method",3);clean();AW_UIDraw();
    for(i=0;i<152*320;i++)assert(vid.buffer[i]==137);
    Cvar_SetValue("aw_dialogue_box_display_method",4);clean();AW_UIDraw();
    assert(AW_UISpeakerAtRight() && changed(268,10) && !changed(10,140));
    prompt=1;assert(!AW_UISpeakerAtRight());prompt=0;
    clean();AW_UIObjectName("Speaker",1);assert(changed(272,158) && !changed(10,158));
    clean();AW_UIObjectName("Speaker",3);assert(changed(8,158) && !changed(272,158));
    AW_UIVoiceSubtitle("Speaker","AAAA",10);clean();AW_UIDraw();
    assert(!AW_UIVoiceNames() && !AW_UISpeakerAtRight());
    assert(AW_UIVoiceStyle()==2 && AW_UIVoiceAimOnly());
    Cvar_SetValue("aw_show_speaker_name_during_voiceovers",1);
    assert(!AW_UIVoiceNames()); /* Aim-only overrides even a forced legacy On. */
    for(i=1;i<=4;i++) {
        Cvar_SetValue("aw_dialogue_box_display_method",i);clean();AW_UIDraw();
        for(y=0;y<152*320;y++)assert(vid.buffer[y]==137);
    }
    for(i=0;i<152*320;i++)assert(vid.buffer[i]==137);
    AW_UIVoiceNamesToggle();clean();AW_UIDraw();assert(AW_UISpeakerAtRight() && changed(268,10));
    AW_UIVoiceNamesToggle();AW_UISubtitle("Speaker","Unvoiced",10);assert(AW_UISpeakerAtRight());
    Cvar_SetValue("aw_dialogue_box_display_method",999);assert(AW_UIDialogueMethod()==2);
    /* New content layout: exact eight-pixel padding around visible glyphs,
     * centered lines, short single-line panel and page-specific measurement. */
    Cvar_SetValue("aw_dialogue_box_layout",3);
    Cvar_SetValue("aw_dialogue_box_display_method",3);
    assert(AW_UISetFontSize(14));
    AW_UISubtitle("","AAAA",10);clean();AW_UIDraw();
    assert(framed(141,176) && framed(178,199));
    assert(vid.buffer[176*320+140]==0 && vid.buffer[176*320+179]==0);
    assert(!framed(140,176) && !framed(179,176) && !framed(141,175));
    assert(vid.buffer[184*320+149]==AW_UIColor(223,199,144));
    AW_UISubtitle("","AAAA\nBB",10);clean();AW_UIDraw();
    assert(framed(141,160) && !framed(141,159));
    assert(vid.buffer[168*320+149]==AW_UIColor(223,199,144));
    assert(vid.buffer[184*320+155]==AW_UIColor(223,199,144));
    assert(vid.buffer[183*320+155]==0); /* unchanged sixteen-pixel baseline */
    AW_UISubtitle("","AAAA\nBB\nC",10);realtime=6;clean();AW_UIDraw();
    assert(framed(150,176) && !framed(149,176)); /* narrow final page */
    assert(vid.buffer[184*320+158]==AW_UIColor(223,199,144));
    AW_UISubtitle("","AA\ng",10);clean();AW_UIDraw();
    assert(framed(147,155) && !framed(147,154));
    assert(vid.buffer[163*320+155]==AW_UIColor(223,199,144));
    assert(vid.buffer[182*320+158]==AW_UIColor(223,199,144));
    assert(vid.buffer[191*320+158]==AW_UIColor(223,199,144));
    assert(vid.buffer[192*320+158]==0);
    AW_UISubtitle("","C",10);
    Cvar_SetValue("aw_dialogue_box_layout",2);clean();AW_UIDraw();
    assert(framed(0,170) && !framed(0,169)); /* full-width option retained */
    assert(frame[0]==137 && frame[1]==137 && frame[64002]==137 && frame[64003]==137);
    return 0;
}
