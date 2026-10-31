/* SPDX-License-Identifier: GPL-2.0-or-later
 * The console-font list box's rules (aw_listbox.h): search, filter, selection and scrolling. No engine
 * dependencies; host-tested by tests/aga_listbox_test.c.
 */
#include <string.h>
#include "aw_listbox.h"

static int fold(int c) {
    if(c>='A' && c<='Z')return c-'A'+'a';
    if((c>='a' && c<='z') || (c>='0' && c<='9'))return c;
    if(c>=0xC0 && c<=0xFF)return c;          /* Latin-1 letters kept as they are */
    return 0;                                /* spaces and punctuation do not count */
}
int AW_ListBoxMatches(const char *label,const char *search) {
    char want[AW_LISTBOX_SEARCH+1];int n=0,i,j,c;
    if(!search)return 1;
    for(i=0;search[i] && n<AW_LISTBOX_SEARCH;i++)if((c=fold((unsigned char)search[i]))!=0)want[n++]=(char)c;
    if(!n)return 1;
    if(!label)return 0;
    for(i=0;label[i];i++){
        const char *p=label+i;int k=0;
        if(!fold((unsigned char)*p))continue;
        for(j=0;p[j] && k<n;j++){
            c=fold((unsigned char)p[j]);
            if(!c)continue;
            if(c!=(unsigned char)want[k])break;
            k++;
        }
        if(k==n)return 1;
    }
    return 0;
}
static void keep_visible(aw_listbox_t *b) {
    int range;
    if(b->visible<1)b->visible=1;
    if(b->selection>=b->shown_count)b->selection=b->shown_count-1;
    if(b->selection<0)b->selection=0;
    if(b->selection<b->top)b->top=b->selection;
    if(b->selection>=b->top+b->visible)b->top=b->selection-b->visible+1;
    range=b->shown_count-b->visible;if(range<0)range=0;
    if(b->top>range)b->top=range;
    if(b->top<0)b->top=0;
}
void AW_ListBoxFilter(aw_listbox_t *b) {
    int i,keep=AW_ListBoxSelected(b);
    b->shown_count=0;
    for(i=0;i<b->count;i++)
        if(AW_ListBoxMatches(b->label?b->label(b->ctx,i):"",b->search))b->shown[b->shown_count++]=i;
    /* the same row stays selected while it is still shown, else the first match */
    b->selection=0;
    for(i=0;i<b->shown_count;i++)if(b->shown[i]==keep){b->selection=i;break;}
    if(b->search[0] && (keep<0 || b->selection==0))b->top=0;
    keep_visible(b);
}
void AW_ListBoxReset(aw_listbox_t *b,int count,aw_listbox_label_t label,void *ctx,int *shown,int visible) {
    memset(b,0,sizeof(*b));
    b->count=count<0?0:count;b->label=label;b->ctx=ctx;b->shown=shown;b->visible=visible<1?1:visible;
    b->selection=-1;
    if(shown)AW_ListBoxFilter(b);
}
int AW_ListBoxSelected(const aw_listbox_t *b) {
    if(!b->shown || b->selection<0 || b->selection>=b->shown_count)return -1;
    return b->shown[b->selection];
}
int AW_ListBoxType(aw_listbox_t *b,int c) {
    int n=(int)strlen(b->search);
    if(c<32 || c>126)return 0;
    if(n>=AW_LISTBOX_SEARCH || (c==' ' && (!n || b->search[n-1]==' ')))return 1;
    b->search[n]=(char)c;b->search[n+1]=0;
    AW_ListBoxFilter(b);
    return 1;
}
int AW_ListBoxKey(aw_listbox_t *b,int key) {
    int n;
    switch(key){
    case AW_LBKEY_UP:b->selection--;break;
    case AW_LBKEY_DOWN:b->selection++;break;
    case AW_LBKEY_PAGEUP:b->selection-=b->visible;break;
    case AW_LBKEY_PAGEDOWN:b->selection+=b->visible;break;
    case AW_LBKEY_HOME:b->selection=0;break;
    case AW_LBKEY_END:b->selection=b->shown_count-1;break;
    case AW_LBKEY_BACKSPACE:
        n=(int)strlen(b->search);
        if(n){b->search[n-1]=0;AW_ListBoxFilter(b);}
        return AW_LB_NONE;
    case AW_LBKEY_CHOOSE:return AW_ListBoxSelected(b)>=0?AW_LB_CHOSEN:AW_LB_NONE;
    case AW_LBKEY_CLOSE:return AW_LB_CLOSED;
    default:return AW_LB_NONE;
    }
    keep_visible(b);
    return AW_LB_NONE;
}
int AW_ListBoxClick(aw_listbox_t *b,int line) {
    if(line<0 || line>=b->visible || b->top+line>=b->shown_count)return AW_LB_NONE;
    b->selection=b->top+line;keep_visible(b);
    return AW_LB_CHOSEN;
}
void AW_ListBoxScroll(aw_listbox_t *b,int top) {
    int range=b->shown_count-b->visible;
    if(range<0)range=0;
    if(top>range)top=range;
    if(top<0)top=0;
    b->top=top;
    if(b->selection<top)b->selection=top;
    if(b->selection>=top+b->visible)b->selection=top+b->visible-1;
    if(b->selection>=b->shown_count)b->selection=b->shown_count-1;
    if(b->selection<0)b->selection=0;
}
void AW_ListBoxSetVisible(aw_listbox_t *b,int visible) {b->visible=visible<1?1:visible;keep_visible(b);}

/* --- the settlements table (AWTP1, aw_listbox.h) --- */
static unsigned long be32(const unsigned char *p) {
    return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|(unsigned long)p[3];
}
static long signed32(const unsigned char *p) {
    unsigned long v=be32(p);
    return v&0x80000000ul?-(long)((~v&0xFFFFFFFFul)+1ul):(long)v;
}
long AW_TpPlacesRows(const unsigned char *data,long size) {
    unsigned long rows;
    if(!data || size<AW_TP_HEADER || memcmp(data,"AWTP",4))return -1;
    if(data[4]!=0 || data[5]!=1 || data[6]!=0 || data[7]!=AW_TP_ROW)return -1;
    rows=be32(data+8);
    if(rows>65535ul || (long)(AW_TP_HEADER+rows*AW_TP_ROW)!=size)return -1;
    return (long)rows;
}
void AW_TpPlacesRow(const unsigned char *data,long i,aw_tp_place_t *p) {
    const unsigned char *r=data+AW_TP_HEADER+i*AW_TP_ROW;
    memcpy(p->name,r,AW_TP_NAME);p->name[AW_TP_NAME-1]=0;
    p->x=signed32(r+32);p->y=signed32(r+36);p->z=signed32(r+40);
    p->flags=r[44];p->cells=r[45];
}
static int put_number(char *out,int at,int size,long v) {
    char digits[12];int n=0;unsigned long u=v<0?(unsigned long)(-(v+1))+1ul:(unsigned long)v;
    do{digits[n++]=(char)('0'+u%10);u/=10;}while(u && n<11);
    if(v<0){if(at+1>=size)return -1;out[at++]='-';}
    if(at+n>=size)return -1;
    while(n)out[at++]=digits[--n];
    return at;
}
int AW_TpPlacesCommand(const aw_tp_place_t *p,char *out,int size) {
    static const char head[]="aw_teleport ";int at=(int)sizeof(head)-1;
    if(!p || !out || size<=at+8)return -1;
    memcpy(out,head,(size_t)at);
    if((at=put_number(out,at,size,p->x))<0 || at+1>=size)return -1;
    out[at++]=' ';
    if((at=put_number(out,at,size,p->y))<0)return -1;
    if(p->flags&AW_TP_HAS_Z){
        if(at+1>=size)return -1;
        out[at++]=' ';
        if((at=put_number(out,at,size,p->z))<0)return -1;
    }
    if(at+2>size)return -1;
    out[at++]='\n';out[at]=0;
    return at;
}
