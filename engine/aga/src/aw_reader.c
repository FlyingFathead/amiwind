/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_inventory.h"
#include "aw_tryalloc.h"
#include "aw_textdef.h"
#include "aw_levelup.h"
static char text[8192],title[96];
static unsigned short pages[512];
static int page_count,page,active,action,result;
/* BOOK-READER-58: a book read where it lies. Its text (id1/books.awb, tools/prepare_books.py AWB1) is read on
 * demand by record id into BOOK, allocated on open and freed on close: nothing is resident beyond the open book. */
#define BOOK_TEXT 40000       /* bytes per book: tools/prepare_books.py MAX_TEXT */
#define BOOK_ID 32
#define BOOK_LABEL 16
#define BOOK_PAGES 512
#define READER_LINES 8
#define BOOK_ACTION 4         /* action: a placed book, E takes it */
#define BOOK_BUTTON_Y 170     /* the buttons' row (320x200): "E: Take"/"E: Steal" and "Esc: Close" */
#define BOOK_BUTTON_H 22
#define BOOK_BUTTON_W 116
#define BOOK_TAKE_X 36
#define BOOK_CLOSE_X 168
static char *book,book_take[24],book_close[24];
static unsigned book_reference;
static int book_owned;
static const char *body_text(void){return book?book:text;}
static void book_free(void);
static int paginate(const char *body);
static void close_reader(int take);
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
/* The text defines (%PCName, %PCRace, %Cell, %GameHour ...) through the one getter table (aw_textdef.c,
 * BOOK-TEXT-MACROS-58), outside dialogue: the speaker's defines are filled before (aw_glut.c, aw_dialwin.c). */
static void expand(char *out,int capacity,const char *source)
{
    aw_textdef_values_t v;
    if(capacity<=0)return;
    AW_TextDefinesPlayer(&v);
    AW_TextDefines(out,capacity,source,&v);
}
void AW_ExpandDialogue(char *out,int capacity,const char *source)
{
    if(capacity>0)expand(out,capacity,source);
}
#define BOOK_DEFINE_ROOM 1024   /* bytes a book may grow by its defines (a name is at most 31 for 7 of %PCName) */
/* A placed book's text with its defines filled, in a fresh allocation that replaces BOOK (BOOK-TEXT-MACROS-58: the
 * placed-book path showed %PCName raw). 0 when there is no memory: the book is not opened. */
static int book_defines(void)
{
    size_t size;char *filled;
    if(!book)return 0;
    if(!strchr(book,'%') && !strchr(book,'^') && !strchr(book,AW_TEXTDEF_CODE) && !strchr(book,AW_TEXTDEF_GLOBAL))return 1;
    size=strlen(book)+BOOK_DEFINE_ROOM;
    if(!(filled=(char *)AW_TryMalloc(size)))return 0;
    expand(filled,(int)size,book);
    free(book);book=filled;
    return 1;
}
int AW_ReaderOpen(const char *stem,int on_take)
{
    char path[64],raw[8192],*body;
    int n,i;
    if(strlen(stem)>32)return 0;
    for(i=0;stem[i];i++)if(!((stem[i]>='a' && stem[i]<='z') || (stem[i]>='0' && stem[i]<='9') || stem[i]=='_'))return 0;
    sprintf(path,"reading/%s.txt",stem);n=read_asset(path,(byte *)raw,sizeof(raw));
    if(n<2 || raw[n-1] || memchr(raw,0,n-1))return 0;
    body=strchr(raw,'\n');if(!body || body-raw>95)return 0;
    *body++=0;book_free();strcpy(title,raw);expand(text,sizeof(text),body);
    if(!paginate(text))return 0;
    page=0;active=1;action=on_take;result=0;IN_AWClearButtons();return 1;
}
static void book_free(void){if(book){free(book);book=NULL;}}
static unsigned long u32le(const byte *p){return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);}
static void book_word(char *out,int size,const byte *raw,const char *fallback){
    int i;
    for(i=0;i<BOOK_LABEL && raw[i];i++)if(raw[i]<32 || raw[i]>126)break;
    if(i==BOOK_LABEL || !i || raw[i]){strcpy(out,fallback);return;}
    memcpy(out,raw,i);out[i]=0;(void)size;
}
/* Lay BODY out into pages of READER_LINES lines at the reader's width; a form feed starts a new page. */
static int paginate(const char *body)
{
    const char *p=body,*before;char line[128];int lines;
    page_count=0;AW_UIBookBegin();
    while(*p && page_count<BOOK_PAGES){
        pages[page_count++]=(unsigned short)(p-body);
        for(lines=0;lines<READER_LINES && *p;lines++){
            if(*p=='\f'){p++;break;}
            before=p;p=AW_UILine(p,274,line,sizeof(line));
            if(p==before){AW_UIBookEnd();return 0;}
        }
    }
    AW_UIBookEnd();
    if(*p)return 0;
    if(!page_count){pages[0]=0;page_count=1;}
    return 1;
}
/* Find ID in books.awb and read its text into a fresh allocation; 1 when the book is open. */
static int book_load(const char *id)
{
    FILE *f=NULL;byte head[8+2*BOOK_LABEL],entry[BOOK_ID+8];long base;int length=COM_FOpenFile("books.awb",&f),lo,hi,mid,c;
    unsigned long count,offset,size;char *nl;
    if(!f)return 0;
    base=ftell(f);
    if(length<(int)sizeof(head) || fread(head,1,sizeof(head),f)!=sizeof(head) || memcmp(head,"AWB1",4)){fclose(f);return 0;}
    count=u32le(head+4);
    if(count>65535 || sizeof(head)+count*sizeof(entry)>(unsigned long)length){fclose(f);return 0;}
    book_word(book_take,sizeof(book_take),head+8,"Take");book_word(book_close,sizeof(book_close),head+8+BOOK_LABEL,"Close");
    for(lo=0,hi=(int)count-1,offset=size=0;lo<=hi;){
        mid=(lo+hi)/2;
        if(fseek(f,base+(long)sizeof(head)+mid*(long)sizeof(entry),SEEK_SET) || fread(entry,1,sizeof(entry),f)!=sizeof(entry)){fclose(f);return 0;}
        c=strncmp(id,(const char *)entry,BOOK_ID);
        if(!c){offset=u32le(entry+BOOK_ID);size=u32le(entry+BOOK_ID+4);break;}
        if(c>0)lo=mid+1;else hi=mid-1;
    }
    if(!size || size>BOOK_TEXT || offset+size>(unsigned long)length || !(book=(char *)AW_TryMalloc(size+1))){fclose(f);return 0;}
    if(fseek(f,base+(long)offset,SEEK_SET) || fread(book,1,size,f)!=size){fclose(f);book_free();return 0;}
    fclose(f);book[size]=0;
    if(memchr(book,0,size) || !(nl=strchr(book,'\n')) || nl-book>95){book_free();return 0;}
    *nl=0;strcpy(title,book);memmove(book,nl+1,strlen(nl+1)+1);
    return 1;
}
/* The aw_book_reader hook (aw_inventory.c): E on a readable placed book. Reading is free; Take or Steal (owned, red)
 * and Close are the reader's buttons. 1 when the reader opened. */
static int book_open(unsigned reference)
{
    char id[BOOK_ID+1];int owned=0;
    if(active || !AW_PlacedBook(reference,id,&owned))return 0;
    book_free();
    if(!book_load(id))return 0;
    if(!book_defines() || !paginate(book)){book_free();return 0;}
    book_reference=reference;book_owned=owned;
    page=0;active=1;action=BOOK_ACTION;result=0;IN_AWClearButtons();
    AW_LevelupBookRead(id);     /* SKILL-BOOKS-MISSING-62: a skill book's first read raises its skill */
    return 1;
}
/* EQUIP-ACTION-REGRESSION-62 (the item classes): a carried book or scroll read from the inventory window (OpenMW
 * mwclass/book.cpp use: ActionRead); the generic reader with Close only. 1 when the reader opened. */
static int carried_open(const char *id)
{
    if(active || !id || strlen(id)>BOOK_ID)return 0;
    book_free();
    if(!book_load(id))return 0;
    if(!book_defines() || !paginate(book)){book_free();return 0;}
    book_reference=0;book_owned=0;
    page=0;active=1;action=0;result=0;IN_AWClearButtons();return 1;
}
static void close_reader(int take)
{
    unsigned reference=book_reference;int was_book=book!=NULL;
    active=0;book_free();book_reference=0;IN_AWClearButtons();
    if(was_book && take)AW_PlacedTake(reference);
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
    if(action==BOOK_ACTION){
        /* a placed book: arrows and page keys turn pages, E (or Enter) takes it, Esc closes; the mouse clicks the
         * buttons (BOOK_BUTTON_Y) or the page arrows at either side */
        if(key==K_MOUSE1){
            if(mouse_y<BOOK_BUTTON_Y)key=mouse_x<160?K_LEFTARROW:K_RIGHTARROW;
            else if(mouse_x>=BOOK_TAKE_X && mouse_x<BOOK_TAKE_X+BOOK_BUTTON_W)key='e';
            else if(mouse_x>=BOOK_CLOSE_X && mouse_x<BOOK_CLOSE_X+BOOK_BUTTON_W)key=K_ESCAPE;
            else return 1;
        }
        if((key==K_LEFTARROW || key==K_UPARROW || key==K_PGUP || key=='a' || key=='A') && page>0)page--;
        else if((key==K_RIGHTARROW || key==K_DOWNARROW || key==K_PGDN || key==K_SPACE || key=='d' || key=='D') &&
                page+1<page_count)page++;
        else if(key=='e' || key=='E' || key==K_ENTER)close_reader(1);
        else if(key==K_ESCAPE)close_reader(0);
        return 1;
    }
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
        active=0;book_free();IN_AWClearButtons();
    }
    return 1;
}
void AW_ReaderDraw(void)
{
    int i,ink;const char *p;char line[128];
    /* switch "E: Read" on: the inventory's hook to this reader (aw_inventory.c AW_ItemPrompt, placed_use) */
    if(!aw_book_reader)aw_book_reader=book_open;
    if(!aw_worldui_read)aw_worldui_read=carried_open;
    if(!active || key_dest!=key_game)return;
    AW_UIBox(2,2,316,196);
    /* Texture noise and curled edges obscure small text at 320x200. Keep the
     * converted artwork available, but use a full, clear reading surface. */
    AW_UIFill(10,10,300,180,AW_UIColor(255,255,255));
    ink=AW_UIColor(0,0,0);AW_UIBookBegin();
    AW_UITextBox(18,13,284,20,title,ink);p=body_text()+pages[page];
    for(i=0;i<READER_LINES && *p && *p!='\f';i++){p=AW_UILine(p,274,line,sizeof(line));AW_UIText(22,39+i*14,line,ink);}
    AW_UIBookEnd();
    if(action==BOOK_ACTION){
        /* BOOK-READER-58: the page count, then the two buttons; Take is white, Steal red (it belongs to someone) */
        sprintf(line,"< %ld/%ld >",(long)page+1,(long)page_count);
        AW_UIBookBegin();AW_UITextBox(10,152,300,16,line,ink);AW_UIBookEnd();
        AW_UIBox(BOOK_TAKE_X,BOOK_BUTTON_Y,BOOK_BUTTON_W,BOOK_BUTTON_H);
        Q_snprintf(line,sizeof(line),"E: %s",book_owned?"Steal":book_take);
        AW_UITextBox(BOOK_TAKE_X,BOOK_BUTTON_Y,BOOK_BUTTON_W,BOOK_BUTTON_H,line,
                     book_owned?AW_UIColor(220,40,40):AW_UIColor(255,255,255));
        AW_UIBox(BOOK_CLOSE_X,BOOK_BUTTON_Y,BOOK_BUTTON_W,BOOK_BUTTON_H);
        Q_snprintf(line,sizeof(line),"Esc: %s",book_close);
        AW_UITextBox(BOOK_CLOSE_X,BOOK_BUTTON_Y,BOOK_BUTTON_W,BOOK_BUTTON_H,line,AW_UIColor(255,255,255));
        if(!AW_UICursor(mouse_x,mouse_y)){AW_UIFill(mouse_x,mouse_y,2,6,ink);AW_UIFill(mouse_x,mouse_y,6,2,ink);}
        return;
    }
    sprintf(line,"< %ld/%ld >  Enter: %s  Esc: close",(long)page+1,(long)page_count,
            action==1?"Take":action==2?"Duties":action==3?"Accept":"Close");
    AW_UIBookBegin();AW_UITextBox(10,168,300,22,line,ink);AW_UIBookEnd();
    if(!AW_UICursor(mouse_x,mouse_y)){AW_UIFill(mouse_x,mouse_y,2,6,ink);AW_UIFill(mouse_x,mouse_y,6,2,ink);}
}
