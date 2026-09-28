/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded proportional UI. Converted artwork is private external data.
 * Console font/atlas are independent and remain unchanged.
 */
#include "quakedef.h"
extern byte *draw_chars;
extern int scr_copyeverything;
static byte font[26624],skin[4104];
static int font_bytes,font_height=8,line_height=10,skin_ready,initialized;
static cvar_t ui_font={"aw_ui_font","16",true};
static cvar_t ui_hud={"aw_ui_hud","1",true};
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
    if(x<0)x=0;if(y<0)y=0;if(right>vid.width)right=vid.width;if(bottom>vid.height)bottom=vid.height;
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
static void initialize(void) {
    if(initialized)return;initialized=1;
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
int AW_UIHeight(void){initialize();return line_height;}
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
void AW_UIBox(int x,int y,int w,int h) {
    initialize();if(w<8 || h<8)return;
    AW_UIFill(x,y,w,h,black);
    if(!skin_ready){AW_UIFill(x,y,w,1,ink[1]);AW_UIFill(x,y+h-1,w,1,ink[1]);AW_UIFill(x,y,1,h,ink[1]);AW_UIFill(x+w-1,y,1,h,ink[1]);return;}
    tile(x,y,4,4,0,0,4,4);tile(x+w-4,y,4,4,20,0,4,4);
    tile(x,y+h-4,4,4,0,20,4,4);tile(x+w-4,y+h-4,4,4,20,20,4,4);
    tile(x+4,y,w-8,4,4,0,16,4);tile(x+4,y+h-4,w-8,4,4,20,16,4);
    tile(x,y+4,4,h-8,0,4,4,16);tile(x+w-4,y+4,4,h-8,20,4,4,16);
}
void AW_UISubtitle(const char *name,const char *text,double duration) {
    strncpy(speaker,name,sizeof(speaker)-1);speaker[sizeof(speaker)-1]=0;
    strncpy(subtitle,text,sizeof(subtitle)-1);subtitle[sizeof(subtitle)-1]=0;
    if(duration<0)duration=0;if(duration>120)duration=120;
    subtitle_started=realtime;subtitle_until=realtime+duration;
}
void AW_UICenterMessage(const char *text) {
    char name[80];const char *p=strchr(text,'\n');int n;
    if(p && (n=(int)(p-text))<80){memcpy(name,text,n);name[n]=0;AW_UISubtitle(name,p+1,8);}
    else AW_UISubtitle("",text,8);
}
void AW_UIBar(int x,int y,int w,int h,int color,float fraction) {
    int fill;
    initialize();if(!(fraction>0))fraction=0;if(fraction>1)fraction=1;fill=(int)((w-4)*fraction);
    AW_UIFill(x,y,w,h,ink[1]);AW_UIFill(x+1,y+1,w-2,h-2,black);
    if(fill>0){if(skin_ready)tile(x+2,y+2,fill,h-4,color*16,32,16,16);
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
void AW_UIDraw(void) {
    const char *p;char line[256];int lines=0,h,y,row,maxlines,page,pages,skip;
    float target,step;double elapsed,duration;
    initialize();
    if(key_dest==key_console)return;
    h=vid.height-(r_refdef.vrect.y+r_refdef.vrect.height);
    if(h<24)return;
    maxlines=(h-12-(speaker[0]?line_height:0))/line_height;
    if(maxlines<1)maxlines=1;
    p=subtitle;while(*p){p=AW_UILine(p,vid.width-24,line,sizeof(line));lines++;}
    target=subtitle_until>realtime && subtitle[0]?1:0;step=host_frametime*6;
    if(panel_position<target){panel_position+=step;if(panel_position>target)panel_position=target;}
    if(panel_position>target){panel_position-=step;if(panel_position<target)panel_position=target;}
    if(panel_position<=0)return;
    /* Start below the screen. Final panel occupies only the reserved UI strip. */
    y=vid.height-(int)(h*panel_position);AW_UIBox(0,y,vid.width,h);
    row=y+6;if(speaker[0]){AW_UIText(10,row,speaker,-1);row+=line_height;}
    pages=(lines+maxlines-1)/maxlines;if(pages<1)pages=1;
    elapsed=realtime-subtitle_started;duration=subtitle_until-subtitle_started;
    page=duration>0?(int)(elapsed*pages/duration):0;if(page>=pages)page=pages-1;if(page<0)page=0;
    p=subtitle;skip=page*maxlines;
    while(*p && skip--)p=AW_UILine(p,vid.width-24,line,sizeof(line));
    while(*p && maxlines--){p=AW_UILine(p,vid.width-24,line,sizeof(line));AW_UIText(10,row,line,-1);row+=line_height;}
    scr_copyeverything=1;
}

static void preview(void){AW_UISubtitle("AmiWind","Proportional text, original borders and three ink shades. The console keeps its own font.",12);}
void AW_UIInit(void) {
    Cvar_RegisterVariable(&ui_font);Cvar_RegisterVariable(&ui_hud);
    Cmd_AddCommand("aw_ui_select",font_command);Cmd_AddCommand("aw_ui_preview",preview);
}
