/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
static char text[8192],title[96];
static unsigned short pages[128];
static int page_count,page,active,action,result;
static int mouse_x=160,mouse_y=90;
static byte sign[10760];
static int sign_index=-1;
static int read_asset(char *path,byte *out,int capacity)
{
    FILE *f=NULL;int n=COM_FOpenFile(path,&f),ok;
    if(!f)return 0;
    ok=n>0 && n<=capacity && fread(out,1,n,f)==(size_t)n;
    fclose(f);return ok?n:0;
}
static int valid_art(const byte *p,int n,int w,int h)
{
    return n==8+w*h && !memcmp(p,"AWI1",4) && p[4]+(p[5]<<8)==w && p[6]+(p[7]<<8)==h;
}
static void draw_art(const byte *p,int x,int y,int w,int h)
{
    int row;
    if(x<0 || y<0 || x+w>(int)vid.width || y+h>(int)vid.height)return;
    for(row=0;row<h;row++)memcpy(vid.buffer+(y+row)*vid.rowbytes+x,p+8+row*w,w);
}
void AW_BirthArt(int index,int x,int y)
{
    char path[40];int n;
    if(index<0 || index>=aw_birth_count)return;
    if(sign_index!=index){
        sprintf(path,"reading/birth%02ld.awi",(long)index);n=read_asset(path,sign,sizeof(sign));
        if(!valid_art(sign,n,96,112)){sign_index=-1;return;}
        sign_index=index;
    }
    draw_art(sign,x,y,96,112);
}
static void expand(char *out,int capacity,const char *source)
{
    int n=0,length;const char *value;
    while(*source && n+1<capacity){
        value=NULL;length=0;
        if(!strncmp(source,"%PCName",7)){value=aw_story.name;length=7;}
        else if(aw_character.valid && !strncmp(source,"%PCRace",7)){value=aw_races[aw_character.race].name;length=7;}
        else if(aw_character.valid && !strncmp(source,"%PCClass",8)){value=aw_classes[aw_character.clas].name;length=8;}
        if(value){while(*value && n+1<capacity)out[n++]=*value++;source+=length;}
        else out[n++]=*source++;
    }
    out[n]=0;
}
int AW_ReaderOpen(const char *stem,int on_take)
{
    char path[64],raw[8192],line[128],*body;const char *p,*before;
    int n,i,lines;
    if(strlen(stem)>32)return 0;
    for(i=0;stem[i];i++)if(!((stem[i]>='a' && stem[i]<='z') || (stem[i]>='0' && stem[i]<='9') || stem[i]=='_'))return 0;
    sprintf(path,"reading/%s.txt",stem);n=read_asset(path,(byte *)raw,sizeof(raw));
    if(n<2 || raw[n-1] || memchr(raw,0,n-1))return 0;
    body=strchr(raw,'\n');if(!body || body-raw>95)return 0;
    *body++=0;strcpy(title,raw);expand(text,sizeof(text),body);
    page_count=0;p=text;AW_UIBookBegin();
    while(*p && page_count<128){
        pages[page_count++]=(unsigned short)(p-text);
        for(lines=0;lines<8 && *p;lines++){
            before=p;p=AW_UILine(p,274,line,sizeof(line));
            if(p==before){AW_UIBookEnd();return 0;}
        }
    }
    AW_UIBookEnd();if(*p)return 0;
    if(!page_count){pages[0]=0;page_count=1;}
    page=0;active=1;action=on_take;result=0;IN_AWClearButtons();return 1;
}
int AW_ReaderActive(void){return active;}
int AW_ReaderResult(void){int r=result;result=0;return r;}
void AW_ReaderMouse(int dx,int dy)
{
    mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>199)mouse_y=199;
}
int AW_ReaderKey(int key)
{
    if(!active || key_dest!=key_game)return 0;
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_LEFTARROW;
    if(key=='s' || key=='S')key=K_RIGHTARROW;
    if(key==K_MOUSE1){
        if(mouse_y>=168)key=mouse_x<106?K_LEFTARROW:mouse_x>212?K_RIGHTARROW:K_ENTER;
        else return 1;
    }
    if(key==K_LEFTARROW && page>0)page--;
    if((key==K_RIGHTARROW || key==K_SPACE) && page+1<page_count)page++;
    if(key==K_ENTER || key=='t' || key==K_ESCAPE){
        if(key!=K_ESCAPE)result=action;
        active=0;IN_AWClearButtons();
    }
    return 1;
}
void AW_ReaderDraw(void)
{
    int i,ink;const char *p;char line[128];
    if(!active || key_dest!=key_game)return;
    AW_UIBox(2,2,316,196);
    /* Texture noise and curled edges obscure small text at 320x200. Keep the
     * converted artwork available, but use a full, clear reading surface. */
    AW_UIFill(10,10,300,180,AW_UIColor(255,255,255));
    ink=AW_UIColor(0,0,0);AW_UIBookBegin();
    AW_UITextBox(18,13,284,20,title,ink);p=text+pages[page];
    for(i=0;i<8 && *p;i++){p=AW_UILine(p,274,line,sizeof(line));AW_UIText(22,39+i*14,line,ink);}
    AW_UIBookEnd();
    sprintf(line,"< %ld/%ld >  Enter: %s  Esc: close",(long)page+1,(long)page_count,
            action==1?"Take":action==2?"Duties":action==3?"Accept":"Close");
    AW_UIBookBegin();AW_UITextBox(10,168,300,22,line,ink);AW_UIBookEnd();
    AW_UIFill(mouse_x,mouse_y,2,6,ink);AW_UIFill(mouse_x,mouse_y,6,2,ink);
}
