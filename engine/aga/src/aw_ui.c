/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded proportional UI. Converted artwork is private external data.
 * Console font/atlas are independent and remain unchanged.
 */
#include "quakedef.h"
extern byte *draw_chars;
extern int scr_copyeverything;
static byte font_storage[26624],book_font[26624],skin[4104];
static byte *font=font_storage;
static int book_font_bytes,book_font_loaded;
/* Optional paper-only candidate; allocate its actual size once, not a full
 * second static font bank. No allocation on TTF/original builds. */
static byte *paper_font;
static int paper_font_bytes,paper_font_loaded;
static byte background[64776],loading_background[64776];
static int loading_state,loading_next;
static cvar_t loading_style={"aw_loading_style","normal",false};
static int next_loading_style=-1,loading_active,loading_blank;
static byte loading_black_palette[768];
static byte logo[8008];
static int logo_state;
static int background_state;
static int font_bytes,font_height=8,line_height=10,skin_ready,initialized;
static cvar_t ui_font={"aw_ui_font","14",true};
static cvar_t ui_hud={"aw_ui_hud","1",true};
static cvar_t ui_frame={"aw_ui_frame","0",true};
static cvar_t dialogue_method={"aw_dialogue_box_display_method","3",true};
static cvar_t dialogue_layout={"aw_dialogue_box_layout","3",true};
static cvar_t voice_names={"aw_show_speaker_name_during_voiceovers","0",true};
static cvar_t voice_style={"aw_voice_dialogue_display_style","2",true};
static int subtitle_voice;
static unsigned subtitle_revision;
static int ink[3],black,muted;
static char subtitle[2048],speaker[80];
static double subtitle_until,subtitle_started;
static float panel_position;
static int u16(const byte *p){return p[0]+(p[1]<<8);}
int AW_UIValidateFont(const byte *p,int n) {
    int i,offset,w,h;
    if(n<2056 || memcmp(p,"AWF1",4) || (p[4]!=12 && p[4]!=14 && p[4]!=16) ||
       p[5]!=p[4]+2 || n!=2056+u16(p+6) || n>26624)return 0;
    for(i=0;i<256;i++) {
        const byte *m=p+8+i*8;offset=u16(m);w=m[2];h=m[3];
        if(w>32 || h>32 || m[6]>32 || m[7] || offset+(w*h+3)/4>n-2056 ||
           (signed char)m[4]<-32 || (signed char)m[4]>32 ||
           (signed char)m[5]<-32 || (signed char)m[5]>32)return 0;
    }
    return 1;
}
int AW_UIColor(int r,int g,int b) {
    int i,best=0,distance=2147483647,dr,dg,db,d;
    for(i=0;i<256;i++){dr=host_basepal[i*3]-r;dg=host_basepal[i*3+1]-g;db=host_basepal[i*3+2]-b;
        d=dr*dr+dg*dg+db*db;if(d<distance){distance=d;best=i;}}
    return best;
}
void AW_UIFill(int x,int y,int w,int h,int color) {
    int bottom=y+h,right=x+w;
    if(x<0)x=0;
    if(y<0)y=0;
    if(right>vid.width)right=vid.width;
    if(bottom>vid.height)bottom=vid.height;
    if(right<=x || bottom<=y)return;
    for(;y<bottom;y++)memset(vid.buffer+y*vid.rowbytes+x,color,right-x);
}
static int read_asset(char *path,byte *out,int capacity) {
    FILE *f=NULL;int n=COM_FOpenFile(path,&f);
    if(!f)return 0;
    if(n<=0 || n>capacity || fread(out,1,n,f)!=n){fclose(f);return 0;}
    fclose(f);return n;
}
static int select_font(int size) {
    byte candidate[26624];char path[32];int n;
    if(!size){font_bytes=0;font_height=8;line_height=10;return 1;}
    if(size!=12 && size!=14 && size!=16)return 0;
    sprintf(path,"gfx/magic%ld.awf",(long)size);n=read_asset(path,candidate,sizeof(candidate));
    if(!AW_UIValidateFont(candidate,n))return 0;
    memcpy(font,candidate,n);font_bytes=n;font_height=font[4];line_height=font[5];return 1;
}
int AW_UIBackground(void) {
    int x,y;byte *row;
    if(!background_state){
        background_state=read_asset("gfx/menu.awb",background,sizeof(background))==sizeof(background) &&
            !memcmp(background,"AWB2",4) && u16(background+4)==320 && u16(background+6)==200?1:-1;
    }
    if(background_state<0)return 0;
    for(y=0;y<vid.height;y++){
        row=background+776+(y*200/vid.height)*320;
        for(x=0;x<vid.width;x++)vid.buffer[y*vid.rowbytes+x]=row[x*320/vid.width];
    }
    return 1;
}
void AW_SetNextLoadingStyle(aw_loading_style_t style) {
    next_loading_style=style==AW_LOADING_BLANK?AW_LOADING_BLANK:AW_LOADING_NORMAL;
}
void AW_BeginLoadingStyle(void) {
    /* Reconnect also begins a plaque: do not consume the one-shot override twice. */
    if(loading_active)return;
    loading_blank=next_loading_style>=0?next_loading_style==AW_LOADING_BLANK:
        !Q_strcasecmp(loading_style.string,"blank");
    next_loading_style=-1;loading_active=1;loading_state=0;
}
void AW_EndLoadingStyle(void) {
    loading_active=loading_blank=loading_state=0;
}
void AW_UILoading(void) {
    int row,n;char path[40];
    if(loading_blank){AW_UIFill(0,0,vid.width,vid.height,0);return;}
    if(!loading_state){
        sprintf(path,"gfx/loading%02ld.awb",(long)loading_next);
        n=read_asset(path,loading_background,sizeof(loading_background));
        if(!n && loading_next){loading_next=0;n=read_asset("gfx/loading00.awb",loading_background,sizeof(loading_background));}
        loading_state=n==sizeof(loading_background) && !memcmp(loading_background,"AWB2",4) &&
            u16(loading_background+4)==320 && u16(loading_background+6)==200?1:-1;
        loading_next=(loading_next+1)%32;
    }
    if(loading_state==1 && vid.width==320 && vid.height==200){
        for(row=0;row<200;row++)memcpy(vid.buffer+row*vid.rowbytes,loading_background+776+row*320,320);
    }else if(!AW_UIBackground())AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
    AW_UIBox(70,160,180,30);AW_UITextBox(74,164,172,22,"Loading...",-1);
}
byte *AW_UIMenuPalette(void){
    if(AW_LoadingScreen()){
        if(loading_blank)return loading_black_palette;
        if(loading_state==1)return loading_background+8;
        if(background_state==1)return background+8;
    }
    else loading_state=0;
    return background_state==1 && AW_MenuFrontEnd()?background+8:NULL;
}
static void initialize(void) {
    if(initialized)return;
    initialized=1;
    black=AW_UIColor(0,0,0);muted=AW_UIColor(115,108,89);
    ink[0]=AW_UIColor(76,67,46);ink[1]=AW_UIColor(151,131,87);ink[2]=AW_UIColor(223,199,144);
    skin_ready=read_asset("gfx/ui.awu",skin,sizeof(skin))==sizeof(skin) &&
        !memcmp(skin,"AWU1",4) && u16(skin+4)==64 && u16(skin+6)==64;
    if(!select_font((int)ui_font.value))Con_Printf("Original UI font unavailable; readable fallback active.\n");
}
static void font_command(void) {
    int size;char *s=Cmd_Argv(1);
    initialize();
    if(Cmd_Argc()!=2){Con_Printf("UI font: %ld; dbg ui font 16/14/12/fallback\n",(long)(font_bytes?font_height:0));return;}
    if(!strcmp(s,"16"))size=16;else if(!strcmp(s,"14"))size=14;
    else if(!strcmp(s,"12"))size=12;else if(!Q_strcasecmp(s,"fallback"))size=0;
    else {Con_Printf("Usage: dbg ui font 16/14/12/fallback\n");return;}
    if(!select_font(size)){Con_Printf("UI font missing or invalid; previous font preserved.\n");return;}
    Cvar_SetValue(ui_font.name,size);scr_copyeverything=1;
}
int AW_UIFontSize(void){initialize();return font_bytes?font_height:0;}
int AW_UISetFontSize(int size){
    initialize();
    if(!select_font(size))return 0;
    Cvar_SetValue(ui_font.name,size);scr_copyeverything=1;return 1;
}
int AW_UIHeight(void){initialize();return line_height;}
int AW_UIDialogueMethod(void){int n=(int)dialogue_method.value;return n>=1 && n<=4?n:3;}
int AW_UIVoiceStyle(void){return voice_style.value==1?1:2;}
int AW_UIVoiceNames(void){return AW_UIVoiceStyle()==1 && voice_names.value!=0;}
int AW_UIVoiceAimOnly(void){return AW_UIVoiceStyle()==2 && subtitle_voice && subtitle[0] && subtitle_until>realtime;}
void AW_UIVoiceNamesToggle(void){
    if(AW_UIVoiceStyle()==2){Cvar_SetValue(voice_style.name,1);Cvar_SetValue(voice_names.name,1);}
    else if(voice_names.value)Cvar_SetValue(voice_names.name,0);
    else Cvar_SetValue(voice_style.name,2);
}
void AW_UIDialogueCycle(int step){Cvar_SetValue(dialogue_method.name,(AW_UIDialogueMethod()-1+step+4)%4+1);}
int AW_UISpeakerAtRight(void){return AW_UIDialogueMethod()==4 && subtitle_until>realtime && subtitle[0] && speaker[0] && (!subtitle_voice || AW_UIVoiceNames()) && !AW_IntroPromptActive();}
static void dialogue_command(void) {
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2 && strlen(s)==1 && s[0]>='1' && s[0]<='4')
        Cvar_SetValue(dialogue_method.name,s[0]-'0');
    else Con_Printf("dbg ui dialogue 1 classic / 2 above / 3 target only / 4 speaker upper right\n");
}
static void layout_command(void) {
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2 && (!strcmp(s,"1") || !strcmp(s,"2") || !strcmp(s,"3")))
        Cvar_SetValue(dialogue_layout.name,s[0]-'0');
    else Con_Printf("dbg ui layout 1 legacy / 2 full width centered / 3 padded content (default)\n");
}
static int advance(int c){return font_bytes?font[8+c*8+6]:8;}
int AW_UIWidth(const char *text) {
    int width=0,best=0;initialize();
    while(*text){if(*text=='\n'){if(width>best)best=width;width=0;text++;}else width+=advance((unsigned char)*text++);}
    return width>best?width:best;
}
void AW_UIText(int x,int y,const char *text,int color) {
    int start=x,c,xx,yy,w,h,ox,oy,k,shade;const byte *m,*pixels;byte *dst;
    initialize();
    while(*text) {
        c=(unsigned char)*text++;
        if(c=='\n'){x=start;y+=line_height;continue;}
        if(font_bytes){m=font+8+c*8;w=m[2];h=m[3];ox=x+(signed char)m[4];oy=y+(signed char)m[5];pixels=font+2056+u16(m);}
        else {w=h=8;ox=x;oy=y;pixels=draw_chars+(c>>4)*1024+(c&15)*8;}
        for(yy=0;yy<h;yy++)if(oy+yy>=0 && oy+yy<vid.height) {
            dst=vid.buffer+(oy+yy)*vid.rowbytes;
            for(xx=0;xx<w;xx++)if(ox+xx>=0 && ox+xx<vid.width) {
                k=yy*w+xx;shade=font_bytes?((pixels[k>>2]>>(6-2*(k&3)))&3):(pixels[yy*128+xx]?3:0);
                if(shade)dst[ox+xx]=color<0?ink[shade-1]:(shade==3?color:(shade==2?ink[1]:ink[0]));
            }
        }
        x+=advance(c);
    }
}
/* Centre the visible glyph bounds, not the font's top bearing. Drawing and
 * mouse hit rectangles can now share exactly the same row geometry. */
void AW_UITextBox(int x,int y,int w,int h,const char *text,int color) {
    const unsigned char *p=(const unsigned char *)text;int top=32,bottom=-32,t,b;
    initialize();
    while(*p){
        if(font_bytes){t=(signed char)font[8+*p*8+5];b=t+font[8+*p*8+3];}
        else {t=0;b=8;}
        if(t<top)top=t;
        if(b>bottom)bottom=b;
        p++;
    }
    if(bottom<top)return;
    AW_UIText(x+(w-AW_UIWidth(text))/2,y+(h-bottom+top)/2-top,text,color);
}
int AW_UILogo(int x,int y) {
    int row;
    if(!logo_state)logo_state=read_asset("gfx/amiwind.awi",logo,sizeof(logo))==sizeof(logo) &&
        !memcmp(logo,"AWI1",4) && u16(logo+4)==200 && u16(logo+6)==40?1:-1;
    if(logo_state<0 || x<0 || y<0 || x+200>vid.width || y+40>vid.height)return 0;
    for(row=0;row<40;row++)memcpy(vid.buffer+(y+row)*vid.rowbytes+x,logo+8+row*200,200);
    return 1;
}
/* Reading uses its own pre-rasterized font without altering the menu setting. */
static int saved_font_bytes,saved_font_height,saved_line_height;
static int saved_book_ink[3];
static void small_font_begin(void) {
    initialize();
    if(!book_font_loaded){
        book_font_loaded=1;
        book_font_bytes=read_asset("gfx/book12.awf",book_font,sizeof(book_font));
        if(!AW_UIValidateFont(book_font,book_font_bytes)){
            book_font_bytes=read_asset("gfx/magic12.awf",book_font,sizeof(book_font));
            if(!AW_UIValidateFont(book_font,book_font_bytes))book_font_bytes=0;
        }
    }
    saved_font_bytes=font_bytes;saved_font_height=font_height;saved_line_height=line_height;
    memcpy(saved_book_ink,ink,sizeof(saved_book_ink));
    if(book_font_bytes){font=book_font;font_bytes=book_font_bytes;font_height=12;line_height=14;}
}
static void load_paper_font(void) {
    FILE *f=NULL;byte *candidate;int n,ok;
    if(paper_font_loaded)return;
    paper_font_loaded=1;
    n=COM_FOpenFile("gfx/paper12.awf",&f);
    if(!f)return; /* Normal TTF/original builds intentionally omit this asset. */
    if(n<2056 || n>(int)sizeof(book_font)){
        fclose(f);Con_Printf("Paper font invalid; original reading font retained.\n");return;
    }
    candidate=(byte *)malloc(n);
    if(!candidate){
        fclose(f);Con_Printf("Paper font allocation failed; original reading font retained.\n");return;
    }
    ok=fread(candidate,1,n,f)==(size_t)n;
    fclose(f);
    if(!ok || !AW_UIValidateFont(candidate,n) || candidate[4]!=12){
        free(candidate);Con_Printf("Paper font invalid; original reading font retained.\n");return;
    }
    paper_font=candidate;paper_font_bytes=n;
}
void AW_UIBookBegin(void) {
    small_font_begin();
    /* Antialiased book glyphs need gray edges on white, not menu gold. */
    ink[0]=AW_UIColor(170,170,170);ink[1]=AW_UIColor(85,85,85);ink[2]=AW_UIColor(0,0,0);
    load_paper_font();
    if(paper_font_bytes){font=paper_font;font_bytes=paper_font_bytes;font_height=12;line_height=14;}
}
void AW_UIBookEnd(void) {
    font=font_storage;font_bytes=saved_font_bytes;font_height=saved_font_height;line_height=saved_line_height;
    memcpy(ink,saved_book_ink,sizeof(saved_book_ink));
}
void AW_UISmallBegin(void) {
    /* Small character/menu text must not inherit paper-only coverage. */
    small_font_begin();
}
void AW_UISmallEnd(void) {AW_UIBookEnd();}
/* Returns the unconsumed text. Always consumes at least a byte for a narrow
 * box, and never splits a buffer or writes outside it. Long words are split. */
const char *AW_UILine(const char *text,int width,char *out,int capacity) {
    const char *p=text,*space=NULL;int used=0,pixels=0,word_used=0,a;
    if(capacity<2)return text;
    while(*p && *p!='\n' && used<capacity-1) {
        a=advance((unsigned char)*p);
        if(pixels+a>width && used)break;
        if(*p==' '){space=p;word_used=used;}
        out[used++]=*p++;pixels+=a;
    }
    if(*p && *p!='\n' && space && word_used>0){used=word_used;p=space+1;}
    out[used]=0;
    if(*p=='\n')p++;else while(*p==' ')p++;
    return p;
}
static void tile(int x,int y,int w,int h,int sx,int sy,int tw,int th) {
    int xx,yy;byte *dst;
    for(yy=0;yy<h;yy++)if(y+yy>=0 && y+yy<vid.height) {
        dst=vid.buffer+(y+yy)*vid.rowbytes;
        for(xx=0;xx<w;xx++)if(x+xx>=0 && x+xx<vid.width)
            dst[x+xx]=skin[8+(sy+yy%th)*64+sx+xx%tw];
    }
}
void AW_UIFrame(int x,int y,int w,int h) {
    initialize();if(w<8 || h<8)return;
    if(!skin_ready){AW_UIFill(x,y,w,1,ink[1]);AW_UIFill(x,y+h-1,w,1,ink[1]);AW_UIFill(x,y,1,h,ink[1]);AW_UIFill(x+w-1,y,1,h,ink[1]);return;}
    tile(x,y,4,4,0,0,4,4);tile(x+w-4,y,4,4,20,0,4,4);
    tile(x,y+h-4,4,4,0,20,4,4);tile(x+w-4,y+h-4,4,4,20,20,4,4);
    tile(x+4,y,w-8,4,4,0,16,4);tile(x+4,y+h-4,w-8,4,4,20,16,4);
    tile(x,y+4,4,h-8,0,4,4,16);tile(x+w-4,y+4,4,h-8,20,4,4,16);
}
void AW_UIBox(int x,int y,int w,int h) {
    initialize();if(w<8 || h<8)return;
    AW_UIFill(x,y,w,h,black);AW_UIFrame(x,y,w,h);
}
void AW_UIOuterFrame(void) {
    if(ui_frame.value && key_dest==key_game && cls.state==ca_connected)
        AW_UIFrame(0,0,vid.width,vid.height);
}
int AW_UIFrameEnabled(void){return ui_frame.value!=0;}
void AW_UIFrameToggle(void){Cvar_SetValue(ui_frame.name,!ui_frame.value);scr_copyeverything=1;}
void AW_UISubtitle(const char *name,const char *text,double duration) {
    subtitle_voice=0;subtitle_revision++;
    strncpy(speaker,name,sizeof(speaker)-1);speaker[sizeof(speaker)-1]=0;
    strncpy(subtitle,text,sizeof(subtitle)-1);subtitle[sizeof(subtitle)-1]=0;
    if(duration<0)duration=0;
    if(duration>120)duration=120;
    subtitle_started=realtime;subtitle_until=realtime+duration;
}
void AW_UIVoiceSubtitle(const char *name,const char *text,double duration) {
    AW_UISubtitle(name,text,duration);subtitle_voice=1;
}
void AW_UICenterMessage(const char *text) {
    char name[80];const char *p=strchr(text,'\n');int n;double duration=AW_SpeechRemaining();int voiced=duration>0;
    if(duration<=0)duration=8;
    if(p && (n=(int)(p-text))<80){memcpy(name,text,n);name[n]=0;AW_UISubtitle(name,p+1,duration);}
    else AW_UISubtitle("",text,duration);
    subtitle_voice=voiced;
}
void AW_UIBar(int x,int y,int w,int h,int color,float fraction) {
    int fill,row;
    initialize();if(!(fraction>0))fraction=0;if(fraction>1)fraction=1;fill=(int)((w-4)*fraction);
    AW_UIFill(x,y,w,h,ink[1]);AW_UIFill(x+1,y+1,w-2,h-2,black);
    if(fill>0){if(skin_ready){for(row=0;row<h-4;row++)tile(x+2,y+2+row,fill,1,color*16,32+(row*12/(h-4))+3,16,1);}
        else AW_UIFill(x+2,y+2,fill,h-4,AW_UIColor(color==0?170:35,color==2?160:35,color==1?170:35));}
}
void AW_UIHud(void) {
    float health=100;int y=vid.height-26;
    initialize();if(cls.state!=ca_connected)return;
    if(r_refdef.vrect.y+r_refdef.vrect.height<vid.height)
        AW_UIFill(0,r_refdef.vrect.y+r_refdef.vrect.height,vid.width,vid.height,black);
    if(!ui_hud.value)return;
    if(sv.active && svs.clients && svs.clients[0].edict)health=svs.clients[0].edict->v.health;
    AW_UIBar(8,y,75,7,0,health/100);AW_UIBar(8,y+8,75,7,1,1);AW_UIBar(8,y+16,75,7,2,1);
    scr_copyeverything=1;
}
/* Names are bounded text over the world, with no panel/background fill. */
static void name_label(const char *name,int x,int y,int right) {
    char label[80];int n,w;
    strncpy(label,name,sizeof(label)-1);label[sizeof(label)-1]=0;
    for(n=strlen(label);n && AW_UIWidth(label)>vid.width-24;n--)label[n-1]=0;
    w=AW_UIWidth(label);
    AW_UITextBox(right?x-w:x,y,w,line_height,label,-1);
}
void AW_UITargetName(const char *name) {
    if(!name || !*name)return;
    initialize();name_label(name,vid.width-10,6,1);scr_copyeverything=1;
}
void AW_UIObjectName(const char *name,int style) {
    int y=r_refdef.vrect.y+r_refdef.vrect.height;
    if(!name || !*name)return;
    if(style==2){AW_UITargetName(name);return;}
    if(vid.height-y<24)return;
    AW_UISmallBegin();
    name_label(name,style==3?8:vid.width-6,y+3,style!=3);
    AW_UISmallEnd();scr_copyeverything=1;
}
/* Cache painted extents for each font selection, including sparse bitmap masks.
 * A bounding rectangle may contain transparent rows after host quantization. */
static byte *bounds_font;
static int bounds_bytes=-1,bounds_height;
static signed char glyph_bounds[256][4];
static void prepare_bounds(void) {
    int c,x,y,k,w,h,left,top,right,bottom;const byte *m,*pixels;
    if(bounds_font==font && bounds_bytes==font_bytes && bounds_height==font_height)return;
    bounds_font=font;bounds_bytes=font_bytes;bounds_height=font_height;
    for(c=0;c<256;c++){
        left=top=32;right=bottom=0;
        if(font_bytes){
            m=font+8+c*8;w=m[2];h=m[3];pixels=font+2056+u16(m);
            for(y=0;y<h;y++)for(x=0;x<w;x++){
                k=y*w+x;if(!((pixels[k>>2]>>(6-2*(k&3)))&3))continue;
                if(x<left)left=x;
                if(y<top)top=y;
                if(x+1>right)right=x+1;
                if(y+1>bottom)bottom=y+1;
            }
            if(right){left+=(signed char)m[4];right+=(signed char)m[4];
                top+=(signed char)m[5];bottom+=(signed char)m[5];}
        }else if(c!=' '){left=top=0;right=bottom=8;}
        if(!right && !bottom)left=top=0;
        glyph_bounds[c][0]=left;glyph_bounds[c][1]=top;
        glyph_bounds[c][2]=right;glyph_bounds[c][3]=bottom;
    }
}
/* Visible bounds share a baseline; blank glyphs must not skew centering. */
static void text_bounds(const char *text,int *left,int *top,int *right,int *bottom) {
    const unsigned char *p=(const unsigned char *)text;int x=0,l,t,w,h;
    *left=*top=32767;*right=*bottom=-32767;
    prepare_bounds();
    while(*p){
        l=x+glyph_bounds[*p][0];t=glyph_bounds[*p][1];
        w=glyph_bounds[*p][2]-glyph_bounds[*p][0];h=glyph_bounds[*p][3]-t;
        if(w && h){
            if(l<*left)*left=l;
            if(t<*top)*top=t;
            if(l+w>*right)*right=l+w;
            if(t+h>*bottom)*bottom=t+h;
        }
        x+=advance(*p++);
    }
    if(*right<*left){*left=*right=*top=*bottom=0;}
}
/* Shared fixed-panel centering for instructional text and ordinary dialogue. */
void AW_UICenteredLines(int x,int y,int w,int h,const char *text) {
    const char *p=text;char lines[3][256];int n=0,i,l,t,r,b,top=32767,bottom=-32767,row;
    initialize();
    while(*p && n<3){
        p=AW_UILine(p,w-16,lines[n],sizeof(lines[n]));
        text_bounds(lines[n],&l,&t,&r,&b);
        if(t+n*line_height<top)top=t+n*line_height;
        if(b+n*line_height>bottom)bottom=b+n*line_height;
        n++;
    }
    if(!n)return;
    row=y+(h-(bottom-top))/2-top;
    for(i=0;i<n;i++){
        text_bounds(lines[i],&l,&t,&r,&b);
        AW_UIText(x+(w-(r-l))/2-l,row+i*line_height,lines[i],-1);
    }
}
/* Sentence-aware paging without a regex engine or per-frame allocation.
 * End punctuation can be followed by quotes; decimal points and common
 * abbreviations do not end a sentence. Oversized sentences word-wrap. */
static const char *sentence_end(const char *start) {
    const char *p=start,*q,*word;char token[12];int n;
    for(;*p;p++){
        if(*p!='.' && *p!='?' && *p!='!')continue;
        if(*p=='.' && p>start && p[-1]>='0' && p[-1]<='9' && p[1]>='0' && p[1]<='9')continue;
        q=p+1;while(*q=='.' || *q=='?' || *q=='!' || *q=='"' || *q=='\'' || *q==')')q++;
        if(*q && *q!=' ' && *q!='\n' && *q!='\t')continue;
        if(*p=='.'){
            word=p;while(word>start && ((word[-1]>='A' && word[-1]<='Z') || (word[-1]>='a' && word[-1]<='z')))word--;
            n=p-word;
            if(n==1 && *word>='A' && *word<='Z')continue;
            if(n>0 && n<11){memcpy(token,word,n);token[n]=0;
                if(!Q_strcasecmp(token,"Mr") || !Q_strcasecmp(token,"Mrs") || !Q_strcasecmp(token,"Ms") ||
                   !Q_strcasecmp(token,"Dr") || !Q_strcasecmp(token,"St"))continue;}
        }
        while(*q==' ' || *q=='\n' || *q=='\t')q++;
        return q;
    }
    return p;
}
static int wrapped_count(const char *text,int width,int limit) {
    char line[256];int n=0;
    while(*text && n<=limit){text=AW_UILine(text,width,line,sizeof(line));n++;}
    return n;
}
const char *AW_UIPage(const char *text,int width,int rows,char *out,int capacity) {
    const char *p=text,*end,*accepted=text,*next;char candidate[2048],line[256];int len,n=0,used=0,k;
    initialize();if(capacity<2 || rows<1)return text;
    /* Pack complete sentences while the whole page still fits. */
    while(*p){
        end=sentence_end(p);len=end-text;if(len>=(int)sizeof(candidate))break;
        memcpy(candidate,text,len);while(len && (candidate[len-1]==' ' || candidate[len-1]=='\n' || candidate[len-1]=='\t'))len--;
        candidate[len]=0;if(wrapped_count(candidate,width,rows)>rows)break;
        accepted=end;p=end;
    }
    p=text;
    while(*p && n<rows && (accepted==text || p<accepted)){
        if(accepted>text){len=accepted-p;if(len>=(int)sizeof(candidate))len=sizeof(candidate)-1;
            memcpy(candidate,p,len);candidate[len]=0;next=AW_UILine(candidate,width,line,sizeof(line));next=p+(next-candidate);
        }else next=AW_UILine(p,width,line,sizeof(line));
        k=strlen(line);while(k && (line[k-1]==' ' || line[k-1]=='\t'))line[--k]=0;
        if(used+k+2>capacity)break;
        if(n)out[used++]='\n';
        memcpy(out+used,line,k);used+=k;p=next;n++;
    }
    out[used]=0;return p;
}
void AW_UIDraw(void) {
    const char *p;char line[256],visible[3][256];
    int h,y,row,maxlines,page,pages,legacy,show_name,centered,n=0,i;
    char page_text[768];const char *next;int weight=0;
    static unsigned cached_revision=~0u;
    static int cached_width,cached_rows,cached_size,cached_pages,total;
    static unsigned short page_offsets[512],page_weights[512];
    int l,t,r,b,top=32767,bottom=-32767,boxwidth=vid.width,boxx=0,wide=0;
    float target,step;double elapsed,duration;
    initialize();
    if(key_dest==key_console)return;
    /* Input prompts own the strip; an expired speaker must not linger above it. */
    if(AW_IntroPromptActive()){panel_position=0;return;}
    h=vid.height-(r_refdef.vrect.y+r_refdef.vrect.height);
    if(h<24)return;
    legacy=AW_UIDialogueMethod()==1;centered=!legacy && dialogue_layout.value!=1;
    show_name=speaker[0] && (!subtitle_voice || AW_UIVoiceNames());
    maxlines=legacy?(h-12-(show_name?line_height:0))/line_height:
        (h-8+line_height-font_height)/line_height;
    if(maxlines<1)maxlines=1;
    if(!legacy && maxlines>3)maxlines=3;

    target=subtitle_until>realtime && subtitle[0]?1:0;step=host_frametime*6;
    if(panel_position<target){panel_position+=step;if(panel_position>target)panel_position=target;}
    if(panel_position>target){panel_position-=step;if(panel_position<target)panel_position=target;}
    if(panel_position<=0)return;
    /* Weights include a small per-page reading pause; long pages get longer.
     * The sum remains exactly the supplied speech duration. */
    if(cached_revision!=subtitle_revision || cached_width!=vid.width ||
       cached_rows!=maxlines || cached_size!=font_height){
        cached_revision=subtitle_revision;cached_width=vid.width;
        cached_rows=maxlines;cached_size=font_height;
        p=subtitle;cached_pages=0;total=0;
        while(*p && cached_pages<512){
            next=AW_UIPage(p,vid.width-24,maxlines,page_text,sizeof(page_text));
            if(next==p)break;
            page_offsets[cached_pages]=p-subtitle;total+=(int)(next-p)+16;
            page_weights[cached_pages++]=total;p=next;
        }
    }
    pages=cached_pages;
    elapsed=realtime-subtitle_started;duration=subtitle_until-subtitle_started;
    if(elapsed<0)elapsed=0;
    weight=duration>0?(int)(elapsed*total/duration):0;
    page=0;while(page<pages-1 && weight>=page_weights[page])page++;
    page_text[0]=0;
    if(pages)AW_UIPage(subtitle+page_offsets[page],vid.width-24,maxlines,page_text,sizeof(page_text));
    p=page_text;
    if(centered){
        while(*p && n<maxlines){
            p=AW_UILine(p,vid.width-24,visible[n],sizeof(visible[n]));
            text_bounds(visible[n],&l,&t,&r,&b);
            if(r-l>wide)wide=r-l;
            if(t+n*line_height<top)top=t+n*line_height;
            if(b+n*line_height>bottom)bottom=b+n*line_height;
            n++;
        }
        /* Layout 3 adds equal padding to actual glyph bounds. Layout 2
         * retains full width and a shorter single-line strip. */
        if(dialogue_layout.value!=2 && n){
            boxwidth=wide+16;
            if(boxwidth>vid.width)boxwidth=vid.width;
            boxx=(vid.width-boxwidth)/2;h=bottom-top+16;
        }else if(n==1 && h>font_height+16)h=font_height+16;
    }
    /* The old full-width panel covered bars and action hints. Clear their
     * strip before a compact box too, so partial labels cannot leak beside it. */
    if(centered)AW_UIFill(0,r_refdef.vrect.y+r_refdef.vrect.height,vid.width,vid.height,black);
    y=vid.height-(int)(h*panel_position);AW_UIBox(boxx,y,boxwidth,h);
    row=y+(legacy?6:4);
    if(show_name){
        if(legacy){AW_UIText(10,row,speaker,-1);row+=line_height;}
        else if(target && AW_UIDialogueMethod()==2)name_label(speaker,centered?boxx+8:10,y-line_height-2,0);
        else if(target && AW_UIDialogueMethod()==4)name_label(speaker,vid.width-10,6,1);
    }
    if(centered){
        if(n)row=y+(h-bottom+top)/2-top;
        for(i=0;i<n;i++){
            text_bounds(visible[i],&l,&t,&r,&b);
            AW_UIText((vid.width-r+l)/2-l,row+i*line_height,visible[i],-1);
        }
    }else while(*p && maxlines--){
        p=AW_UILine(p,vid.width-24,line,sizeof(line));
        if(legacy)AW_UIText(10,row,line,-1);
        else AW_UITextBox(10,row,AW_UIWidth(line),font_height,line,-1);
        row+=line_height;
    }
    scr_copyeverything=1;
}

static void preview(void){AW_UISubtitle("AmiWind","Proportional text, original borders and three ink shades. The console keeps its own font.",12);}
void AW_UIInit(void) {
    Cvar_RegisterVariable(&ui_font);Cvar_RegisterVariable(&ui_hud);Cvar_RegisterVariable(&ui_frame);
    Cvar_RegisterVariable(&loading_style);
    Cvar_RegisterVariable(&dialogue_method);Cvar_RegisterVariable(&dialogue_layout);
    Cvar_RegisterVariable(&voice_names);
    Cvar_RegisterVariable(&voice_style);
    Cmd_AddCommand("aw_dialogue_method",dialogue_command);Cmd_AddCommand("aw_dialogue_layout",layout_command);
    Cmd_AddCommand("aw_ui_select",font_command);Cmd_AddCommand("aw_ui_preview",preview);
}
