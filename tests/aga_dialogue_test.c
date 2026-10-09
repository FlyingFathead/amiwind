/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
viddef_t vid;refdef_t r_refdef;keydest_t key_dest=key_game;double realtime,host_frametime=1;
client_static_t cls;server_t sv;server_static_t svs;int scr_copyeverything;
static byte pal[768],glyphs[16384],frame[64004];byte *host_basepal=pal,*draw_chars=glyphs;
static cvar_t *vars[16];static int count,prompt;static int photo;
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
    int i,x,y;char pagebuf[768];const char *rest;
    for(i=0;i<256;i++)pal[i*3]=pal[i*3+1]=pal[i*3+2]=i;
    memset(glyphs,255,sizeof(glyphs));vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame+2;
    r_refdef.vrect.height=152;AW_UIInit();assert(AW_UIDialogueMethod()==3);
    Cvar_SetValue("aw_dialogue_box_display_method",2);
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
    Cvar_SetValue("aw_dialogue_box_display_method",999);assert(AW_UIDialogueMethod()==3);
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
    rest=AW_UIPage("Stand up. You were dreaming. What's your name?",72,2,pagebuf,sizeof(pagebuf));
    assert(!strcmp(pagebuf,"Stand up."));
    assert(!strcmp(rest,"You were dreaming. What's your name?"));
    rest=AW_UIPage(rest,72,2,pagebuf,sizeof(pagebuf));
    assert(!strcmp(pagebuf,"You were\ndreaming."));
    assert(!strcmp(rest,"What's your name?"));
    rest=AW_UIPage("Dr. Hleran has 3.5 gold. Yes?",160,2,pagebuf,sizeof(pagebuf));
    assert(!*rest); /* titles and decimal points stay inside the sentence */
    rest=AW_UIPage("A very long sentence that cannot fit on one page continues safely.",72,2,pagebuf,sizeof(pagebuf));
    assert(rest[0] && strstr(pagebuf,"A very long"));
    clean();AW_UIBox(0,152,320,48);AW_UICenteredLines(0,152,320,48,"AAAA\nBB");
    assert(vid.buffer[164*320+149]==AW_UIColor(223,199,144));
    assert(vid.buffer[180*320+155]==AW_UIColor(223,199,144));
    /* Bounded pickup summaries may exceed the former 2048-byte buffer. */
    {char long_message[2600];long_message[0]=0;
     for(i=0;i<500;i++)strcat(long_message,"AAAA\n");strcat(long_message,"Z");
     Cvar_SetValue("aw_dialogue_box_layout",3);r_refdef.vrect.height=152;realtime=0;
     AW_UISubtitle("",long_message,100);realtime=99.99;clean();AW_UIDraw();
     assert(framed(150,176) && !framed(149,176));}
    /* Pickup-only animation toggle never changes ordinary dialogue policy. */
    realtime=200;host_frametime=1;clean();AW_UIDraw();
    host_frametime=0;Cvar_SetValue("aw_animate_item_pickups",0);
    AW_UIPickupNotice("C",3);clean();AW_UIDraw();assert(framed(150,176));
    realtime=204;clean();AW_UIDraw();assert(!changed(150,176));
    Cvar_SetValue("aw_animate_item_pickups",1);
    AW_UIPickupNotice("C",3);clean();AW_UIDraw();assert(!changed(150,176));
    host_frametime=1;clean();AW_UIDraw();assert(framed(150,176));
    realtime=208;clean();AW_UIDraw();host_frametime=0;
    Cvar_SetValue("aw_animate_item_pickups",0);
    AW_UISubtitle("","C",3);clean();AW_UIDraw();assert(!changed(150,176));
    /* Photo mode: the full-screen view leaves no strip, yet its notice uses this
     * same message box, risen over the bottom 72 rows; the view above stays clean. */
    {int top=200;
     r_refdef.vrect.height=200;host_frametime=1;realtime=300;
     AW_UISubtitle("","AAAA\nBBBB\nCCCC",4);assert(AW_UISubtitleIs("AAAA\nBBBB\nCCCC") && !AW_UISubtitleIs("AAAA"));
     clean();AW_UIDraw();for(i=0;i<64000;i++)assert(vid.buffer[i]==137); /* no strip, no photo mode: nothing */
     photo=1;clean();AW_UIDraw();
     for(i=0;i<64000;i++)if(vid.buffer[i]!=137 && i/320<top)top=i/320;
     assert(top>=128 && top<190 && changed(160,199));
     AW_UISubtitle("Speaker","AAAA",4);assert(!AW_UISubtitleIs("AAAA")); /* speech is not a photo notice */
     photo=0;r_refdef.vrect.height=152;}
    return 0;
}
int AW_PhotoModeActive(void){return photo;}
