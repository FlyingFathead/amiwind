/* SPDX-License-Identifier: GPL-2.0-or-later
 * UI-TEXT-BOX-CLEARANCE-64: every text box the engine draws, rendered with a font of the shipped size (14 on a 16-pixel
 * line, ink 13 rows a line) and MEASURED in pixel rows: between the frame's inner edge (AW_UI_FRAME_EDGE) and the ink of
 * the first and of the last line at least AW_UI_TEXT_CLEAR clear rows, the box's own side clearance (the 8-pixel text
 * inset less the 4-pixel edge), and at least one clear row between lines. Boxes: the opening's hint under the view (the
 * maintainer's picture of 11 November 2026: the last line touched the bottom edge), the shared text panel for 1..6
 * lines, the message box's text area for 1..8 lines (aw_msgbox.c), the death box's text area (aw_view.c).
 * Includes the actual intro adapter for its hint. */
#include "aw_intro.c"
#include <assert.h>
#include "aw_msgbox.h"

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
keydest_t key_dest=key_game;viddef_t vid;refdef_t r_refdef;aw_story_t aw_story;
double host_frametime=.02,realtime;int scr_fullupdate,scr_copyeverything;
static byte palette[768],glyphs[16384],frame[64000];
byte *host_basepal=palette,*draw_chars=glyphs;
static byte font_file[2056+21];
int AW_CharacterActive(void){return 0;}int AW_ReaderActive(void){return 0;}
int AW_GalleryModal(void){return 0;}int AW_MovieActive(void){return 0;}
int AW_ReaderKey(int key){return 0;}int AW_CharacterKey(int key){return 0;}
void AW_CharacterDraw(void){}void AW_ReaderDraw(void){}
int AW_NavStart(edict_t *e,float *p){return 1;}
void IN_AWClearButtons(void){}
/* the font of the shipped size, the only file served */
int COM_FOpenFile(char *s,FILE **f){
    *f=NULL;
    if(strcmp(s,"gfx/magicclear14.awf") && strcmp(s,"gfx/magic14.awf"))return -1;
    /* AW_REAL_FONT: the game font a build ships (a private build output), for the pictures sent for review; the
     * checks hold with it too */
    if(getenv("AW_REAL_FONT")){long n;*f=fopen(getenv("AW_REAL_FONT"),"rb");if(!*f)return -1;
        fseek(*f,0,SEEK_END);n=ftell(*f);rewind(*f);return (int)n;}
    *f=fmemopen(font_file,sizeof(font_file),"rb");
    return *f?(int)sizeof(font_file):-1;
}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Cvar_SetValue(char *s,float v){}
void Cmd_AddCommand(char *s,void(*fn)(void)){}
char *Cmd_Argv(int n){return "";}int Cmd_Argc(void){return 0;}
int AW_PhotoModeActive(void){return 0;}

static void make_font(void){
    int c;byte *m;
    memcpy(font_file,"AWF1",4);font_file[4]=14;font_file[5]=16;font_file[6]=21;font_file[7]=0;
    for(c=0;c<256;c++){
        m=font_file+8+c*8;
        if(c>32 && c<127){m[2]=6;m[3]=13;m[4]=0;m[5]=1;m[6]=7;}   /* ink rows 1..13 of the 16-pixel line */
        else m[6]=4;
    }
    memset(font_file+2056,0xFF,21);                                   /* every pixel at full coverage */
}
/* the measured rows of a box whose frame spans TOP..BOTTOM-1 between columns X0..X1-1 (inside the side inset):
 * the clear rows above the first ink and below the last, the text lines (ink runs) and the least clear rows between
 * them */
typedef struct {int above,below,lines,between;} gaps_t;
static gaps_t measure(int top,int bottom,int x0,int x1){
    gaps_t g;int y,x,ink,first=-1,last=-1,prev=0,run_end=-1;
    g.lines=0;g.between=1000;
    for(y=top+1;y<bottom-1;y++){
        for(ink=0,x=x0;x<x1;x++)if(frame[y*320+x]!=0){ink=1;break;}
        if(ink){
            if(first<0)first=y;
            if(!prev){g.lines++;if(run_end>=0 && y-run_end-1<g.between)g.between=y-run_end-1;}
            last=y;
        }else if(prev)run_end=y-1;
        prev=ink;
    }
    assert(first>=0);
    g.above=first-(top+AW_UI_FRAME_EDGE);g.below=(bottom-AW_UI_FRAME_EDGE)-(last+1);
    return g;
}
static void check(const char *what,gaps_t g,int lines){
    printf("%-34s lines %d: %d clear rows above, %d below, %d between\n",what,g.lines,g.above,g.below,
           g.lines>1?g.between:-1);
    assert(g.lines==lines);
    assert(g.above>=AW_UI_TEXT_CLEAR && g.below>=AW_UI_TEXT_CLEAR);
    assert(g.lines<2 || g.between>=1);
}
/* the screen as a greyscale picture (the fixture's palette is grey: index = level) when AW_CLEARANCE_PICS names a folder */
static void picture(const char *name){
    const char *dir=getenv("AW_CLEARANCE_PICS");char path[512];FILE *f;
    if(!dir)return;
    snprintf(path,sizeof(path),"%s/%s.pgm",dir,name);
    f=fopen(path,"wb");assert(f);
    fprintf(f,"P5\n320 200\n255\n");assert(fwrite(frame,1,320*200,f)==320*200);fclose(f);
}
#include "aw_tutorial.h"
/* the shipped bindings of the commands the tutorial boxes name */
static const char *tutorial_key(const char *command){
    if(!strcmp(command,"aw_inventory"))return "I";
    if(!strcmp(command,"aw_worldmap"))return "M";
    if(!strcmp(command,"impulse 202"))return "F";
    if(!strcmp(command,"winkey:inv_use"))return "E) or (Enter";
    return NULL;
}
static const char *text_of(int n){
    static char out[256];int i;out[0]=0;
    for(i=0;i<n;i++)strcat(out,i?"\nThe next line of the box.":"The first line of the box.");
    return out;
}

int main(void){
    int i,n,top;char label[48];
    for(i=0;i<256;i++)palette[i*3]=palette[i*3+1]=palette[i*3+2]=i;
    make_font();
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame;
    r_refdef.vrect.height=152;AW_UIInit();
    assert(AW_UIHeight()==16);                                       /* the shipped size is the one measured */
    sv.active=true;svs.maxclients=1;cls.state=ca_connected;cls.signon=SIGNONS;
    /* the opening's hint (the maintainer's picture): three lines in the 48-row strip under the view */
    active=1;prompt=2;
    memset(frame,0x5a,sizeof(frame));AW_IntroDraw();
    picture("opening_hint_after");
    for(top=0;top<200 && frame[top*320+160]==0x5a;top++);
    assert(top<152);                                                 /* it needed more than the strip: it rose */
    for(i=0;i<320*top;i++)assert(frame[i]==0x5a);                     /* nothing drawn above the panel */
    check("opening hint",measure(top,200,8,312),3);
    /* the layout before the fix (v0.0.64: the box fixed to the 48-row strip) fails the same measurement: the check
     * would have caught the maintainer's picture */
    {gaps_t old;
     memset(frame,0x5a,sizeof(frame));AW_UIBox(0,152,320,48);
     AW_UICenteredLines(0,152,320,48,"W and S move forward and back. A and D move side to side, "
                                     "and the mouse looks around.\nEnter: Ok");
     picture("opening_hint_before");
     old=measure(152,200,8,312);
     printf("before the fix: %d clear rows above, %d below\n",old.above,old.below);
     assert(old.above<AW_UI_TEXT_CLEAR || old.below<AW_UI_TEXT_CLEAR);}
    /* the shared panel under the view, 1..6 lines, never shorter than the strip */
    for(n=1;n<=6;n++){
        memset(frame,0x5a,sizeof(frame));
        top=AW_UITextPanel(0,200,320,48,text_of(n),6);
        assert(top<=152);
        sprintf(label,"text panel, %d line%s",n,n==1?"":"s");check(label,measure(top,200,8,312),n);
    }
    /* the message box's text area (aw_msgbox.c AW_MsgBoxDraw: n lines of the line height plus 8, from the frame's top
     * plus 4; the buttons stand below it) */
    for(n=1;n<=8;n++){
        int h=n*AW_UIHeight()+8,x=10,y=20;
        memset(frame,0x5a,sizeof(frame));AW_UIFill(0,0,320,200,0);
        AW_UICenteredLinesUpTo(x+6,y+4,300-12,h,text_of(n),n);
        sprintf(label,"message box text, %d line%s",n,n==1?"":"s");
        check(label,measure(y,y+4+h+AW_UI_FRAME_EDGE,x+6,x+300-6),n);
    }
    /* the death box's text area (aw_view.c AW_ViewDraw: AW_UICenteredLines in the box less 38 rows for its buttons) */
    for(n=1;n<=3;n++){
        int x=(320-AW_DEATHBOX_W)/2,y=(200-AW_DEATHBOX_H)/2;
        memset(frame,0x5a,sizeof(frame));AW_UIFill(0,0,320,200,0);
        AW_UICenteredLines(x+6,y+4,AW_DEATHBOX_W-12,AW_DEATHBOX_H-38,text_of(n));
        sprintf(label,"death box text, %d line%s",n,n==1?"":"s");
        check(label,measure(y,y+4+AW_DEATHBOX_H-38+AW_UI_FRAME_EDGE,x+6,x+AW_DEATHBOX_W-6),n);
    }
    /* the message box's buttons sized to their labels (UI-TEXT-BOX-CLEARANCE-64): one Ok button is no longer stretched
     * across the box; it is centred, its label plus the padding wide (at least the minimum) */
    {int f[4],r[4],w1[1],w3[3],i;
     AW_MsgBoxLayout(1,320,200,32,f);w1[0]=AW_UIWidth("Ok");
     AW_MsgBoxButtonRect(1,0,f,r);assert(r[2]==f[2]-16);                     /* before: the whole row */
     AW_MsgBoxButtonRectSized(1,0,f,w1,r);
     assert(r[2]==AW_MSGBOX_BUTTON_MIN && r[0]==f[0]+(f[2]-r[2])/2);
     assert(AW_MsgBoxButtonAtSized(1,f,w1,r[0]+1,r[1]+1)==0 && AW_MsgBoxButtonAtSized(1,f,w1,f[0]+9,r[1]+1)==-1);
     AW_MsgBoxLayout(3,320,200,32,f);
     w3[0]=AW_UIWidth("Yes");w3[1]=AW_UIWidth("No");w3[2]=AW_UIWidth("A longer answer to it");
     for(i=0;i<3;i++){int share[4];AW_MsgBoxButtonRect(3,i,f,share);AW_MsgBoxButtonRectSized(3,i,f,w3,r);
         /* as wide as its label, never wider than its share of the row (a longer label stays in its share, as before) */
         assert(r[2]>=AW_MSGBOX_BUTTON_MIN && r[2]<=share[2] && (r[2]>=w3[i] || r[2]==share[2]));
         assert(r[0]>=f[0]+8 && r[0]+r[2]<=f[0]+f[2]-8);}
     /* drawn: the label inside its button with room on both sides */
     memset(frame,0x5a,sizeof(frame));AW_MsgBoxLayout(1,320,200,32,f);AW_MsgBoxButtonRectSized(1,0,f,w1,r);
     AW_UIBox(r[0],r[1],r[2],r[3]);AW_UITextBox(r[0],r[1],r[2],r[3],"Ok",-1);
     picture("ok_button_after");}
    /* OPENING-TUTORIAL-KEYS-65: the tutorial boxes in the maintainer's layout, drawn as aw_msgbox.c draws them (frame,
     * sentences, a gap of a line, the actions with their keys right, a gap, the OK button sized to its label) and
     * measured: the clear rows inside the frame above the text, the gaps, the key column inside the box */
    {static const unsigned long boxes[2]={0xc2ddd5caUL,0x85f66d2bUL};static const char *names[2]={"tutorial_dagger_box","tutorial_map_box"};
     int b;
     for(b=0;b<2;b++){
        char text[512],line[160];const char *rest;int f[4],r[4],w1[1],n=0,lh=AW_UIHeight(),gap=0,y,first=-1,last=-1,
            rowsink=0,x,w=300-12;
        assert(AW_TutorialFill(AW_TutorialFind(boxes[b]),"",tutorial_key,text,sizeof(text))>0);
        /* the pipeline as aw_msgbox.c runs it: the wrapped lines counted (empty rows too), the frame from them, the
         * lines centred in it, a tab line in the key column */
        for(rest=text;rest && *rest && n<AW_MSGBOX_LINES;n++)rest=AW_UILine(rest,w-12-16,line,sizeof(line));
        AW_MsgBoxLayout(1,320,200,n*lh,f);assert(f[3]<=200-8);
        memset(frame,0x5a,sizeof(frame));AW_UIBox(f[0],f[1],f[2],f[3]);
        AW_UICenteredLinesUpTo(f[0]+6,f[1]+4,f[2]-12,n*lh+8,text,n);
        w1[0]=AW_UIWidth("Ok");AW_MsgBoxButtonRectSized(1,0,f,w1,r);AW_UIBox(r[0],r[1],r[2],r[3]);AW_UITextBox(r[0],r[1],r[2],r[3],"Ok",-1);
        picture(names[b]);
        /* the text's ink between the frame and the button: at least the clearance from the frame's inner edge, a gap of
         * at least the clearance before the button */
        for(y=f[1]+1;y<r[1];y++){int ink=0;for(x=f[0]+2;x<f[0]+f[2]-2;x++)if(frame[y*320+x]!=0){ink=1;break;}
            if(ink){if(first<0)first=y;last=y;rowsink++;}}
        assert(first-(f[1]+AW_UI_FRAME_EDGE)>=AW_UI_TEXT_CLEAR && r[1]-(last+1)>=AW_UI_TEXT_CLEAR);
        /* the empty rows of the layout: a clear gap of at least a line's height less the ink between the blocks */
        {int yy,run=0,best=0;for(yy=first;yy<=last;yy++){int ink=0;for(x=f[0]+2;x<f[0]+f[2]-2;x++)if(frame[yy*320+x]!=0){ink=1;break;}
            if(ink)run=0;else if(++run>best)best=run;}
         gap=best;assert(gap>=lh);}
        printf("%s: %d clear rows above, %d before the button, widest gap %d, box %d rows, %d lines\n",names[b],
               first-(f[1]+AW_UI_FRAME_EDGE),r[1]-(last+1),gap,f[3],n);
        (void)rowsink;
        /* the key column stays inside the box with its side clearance */
        for(y=f[1]+1;y<r[1];y++)for(x=f[0]+f[2]-1-AW_UI_FRAME_EDGE-AW_UI_TEXT_CLEAR+1;x<f[0]+f[2]-1;x++)
            assert(frame[y*320+x]==0 || x>=f[0]+f[2]-1-AW_UI_FRAME_EDGE);
     }}
    /* RACE-MENU-OK-HIGHLIGHT-65: the character windows' OK with the keyboard focus shows the rows' dark gold bar inside
     * its line (aw_character.c: 248,166 60x22); without the focus the inside stays black */
    {int x,y,inside_focused=0,inside_plain=0,bar=AW_UIColor(54,47,32);
     memset(frame,0x5a,sizeof(frame));AW_UIButtonFocus(248,166,60,22,"OK",1,AW_UIColor(223,199,144));
     picture("ok_focused");
     for(y=168;y<186;y++)for(x=250;x<256;x++)inside_focused+=frame[y*320+x]==bar;
     memset(frame,0x5a,sizeof(frame));AW_UIButtonFocus(248,166,60,22,"OK",0,AW_UIColor(223,199,144));
     for(y=168;y<186;y++)for(x=250;x<256;x++)inside_plain+=frame[y*320+x]==bar;
     assert(bar!=0 && inside_focused==18*6 && inside_plain==0);}
    return 0;
}
