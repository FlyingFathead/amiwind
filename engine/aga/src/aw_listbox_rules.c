/* SPDX-License-Identifier: GPL-2.0-or-later
 * The console-font list box's rules (aw_listbox.h): search, filter, selection and scrolling. No engine
 * dependencies; host-tested by tests/aga_listbox_test.c.
 */
#include <math.h>
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
int AW_ListBoxNames(const char *label,const char *text) {
    int end,i=0,j=0,a,b,any=0;
    if(!label || !text)return 0;
    end=(int)strlen(label);
    /* the trailing " (...)" parts: "Mournhold, Royal Palace: Reception Area (Tribunal) (interior)" names the room */
    while(end>2 && label[end-1]==')'){
        int k=end-2;
        while(k>0 && label[k]!='(')k--;
        if(k<2 || label[k]!='(' || label[k-1]!=' ')break;
        end=k-1;
    }
    for(;;){
        while(i<end && !fold((unsigned char)label[i]))i++;
        while(text[j] && !fold((unsigned char)text[j]))j++;
        a=i<end?fold((unsigned char)label[i]):0;
        b=text[j]?fold((unsigned char)text[j]):0;
        if(a!=b)return 0;
        if(!a)return any;
        any=1;i++;j++;
    }
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
    for(i=0;i<b->count;i++){
        if(b->category && b->chosen>0 && b->category(b->ctx,i)!=b->chosen)continue;
        if(AW_ListBoxMatches(b->label?b->label(b->ctx,i):"",b->search))b->shown[b->shown_count++]=i;
    }
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
void AW_ListBoxCategories(aw_listbox_t *b,aw_listbox_category_t category,int count) {
    if(count>AW_LISTBOX_CATEGORIES)count=AW_LISTBOX_CATEGORIES;
    b->category=count>1?category:NULL;b->categories=b->category?count:0;b->chosen=0;
    if(b->shown)AW_ListBoxFilter(b);
}
void AW_ListBoxChoose(aw_listbox_t *b,int n) {
    if(!b->category || n<0 || n>=b->categories || n==b->chosen)return;
    b->chosen=n;b->top=0;
    if(b->shown)AW_ListBoxFilter(b);
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
    case AW_LBKEY_LEFT:
        if(b->categories)AW_ListBoxChoose(b,(b->chosen+b->categories-1)%b->categories);
        return AW_LB_NONE;
    case AW_LBKEY_RIGHT:
        if(b->categories)AW_ListBoxChoose(b,(b->chosen+1)%b->categories);
        return AW_LB_NONE;
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
    if(data[4]!=0 || data[6]!=0 || !((data[5]==1 && data[7]==AW_TP_ROW) || (data[5]==2 && data[7]==AW_TP_ROW2) ||
                                     (data[5]==3 && data[7]==AW_TP_ROW3)))return -1;
    rows=be32(data+8);
    if(rows>65535ul || (long)(AW_TP_HEADER+rows*data[7])!=size)return -1;
    return (long)rows;
}
void AW_TpPlacesRow(const unsigned char *data,long i,aw_tp_place_t *p) {
    int v2=data[5]>=2,v3=data[5]==3,name=v2?AW_TP_NAME:AW_TP_NAME1;
    const unsigned char *r=data+AW_TP_HEADER+i*(long)data[7];
    memset(p,0,sizeof(*p));
    memcpy(p->name,r,(size_t)name);p->name[name-1]=0;
    r+=name;
    p->x=signed32(r);p->y=signed32(r+4);p->z=signed32(r+8);
    p->flags=r[12];p->cells=r[13];
    if(v2){memcpy(p->map,r+16,AW_TP_MAP);p->map[AW_TP_MAP-1]=0;}
    else p->flags&=~AW_TP_ROOM;
    if(v3){memcpy(p->id,r+16+AW_TP_MAP,AW_TP_ID);p->id[AW_TP_ID-1]=0;}
    else p->flags&=~(AW_TP_BEING|AW_TP_NEAREST);
}
int AW_TpPlacesCategory(int flags) {
    if(flags&AW_TP_BEING)return AW_TP_CAT_BEING;
    if(flags&AW_TP_ROOM)return AW_TP_CAT_INTERIOR;
    return AW_TP_CAT_EXTERIOR;
}
/* --- the names list (aw_listbox.h AW_TpNames*) --- */
#ifndef AW_TP_ALLOC
#include <stdlib.h>
#include "aw_tryalloc.h"
#define AW_TP_ALLOC(n) AW_TryMalloc(n)
#define AW_TP_FREE(p) free(p)
#else
/* a test's own allocator (tests/aga_tpnames_test.c: the heap test) */
void *AW_TP_ALLOC(unsigned long size);
void AW_TP_FREE(void *block);
#endif
static int names_chunk(aw_tp_names_t *n,long at) {
    long want=n->bytes-at;
    if(want>AW_TPN_CHUNK)want=AW_TPN_CHUNK;
    if(want<2 || fseek(n->file,n->base+AW_TPN_HEADER+at,SEEK_SET))return 0;
    if((long)fread(n->chunk,1,(size_t)want,n->file)!=want)return 0;
    n->chunk_at=at;n->chunk_len=want;
    return 1;
}
/* row bytes at offset AT (category, length, label), whole or through the chunk */
static const unsigned char *names_row(aw_tp_names_t *n,long at) {
    const unsigned char *r;
    if(at<0 || at+2>n->bytes)return NULL;
    if(n->names)r=n->names+at;
    else {
        if(at<n->chunk_at || at+2>n->chunk_at+n->chunk_len ||
           at+2+n->chunk[at-n->chunk_at+1]>n->chunk_at+n->chunk_len)
            if(!names_chunk(n,at))return NULL;
        r=n->chunk+(at-n->chunk_at);
    }
    if(r[1]>=AW_TP_NAME || at+2+r[1]>n->bytes)return NULL;
    return r;
}
long AW_TpNamesOpen(aw_tp_names_t *n,FILE *f,long base,long size,int whole) {
    unsigned char head[AW_TPN_HEADER];unsigned long rows,bytes,need;long i,at;const unsigned char *r;
    memset(n,0,sizeof(*n));
    if(!f || fseek(f,base,SEEK_SET) || fread(head,1,AW_TPN_HEADER,f)!=AW_TPN_HEADER)return -1;
    if(memcmp(head,"AWTN",4) || head[4] || head[5]!=1 || head[6] || head[7])return -1;
    rows=be32(head+8);bytes=be32(head+12);
    if(rows<1 || rows>65535ul || bytes<2*rows || (long)(AW_TPN_HEADER+bytes)!=size)return -1;
    need=rows*sizeof(unsigned long)+(whole?bytes:0);
    if(!(n->block=(unsigned char *)AW_TP_ALLOC(need)))return -1;
    n->at=(unsigned long *)n->block;n->rows=(long)rows;n->bytes=(long)bytes;n->base=base;n->file=f;
    if(whole){
        n->names=n->block+rows*sizeof(unsigned long);
        if((long)fread((void *)n->names,1,bytes,f)!=(long)bytes){AW_TpNamesClose(n);return -1;}
    }
    n->chunk_at=-1;
    for(i=0,at=0;i<n->rows;i++){
        if(!(r=names_row(n,at))){AW_TpNamesClose(n);return -1;}
        n->at[i]=(unsigned long)at;at+=2+r[1];
    }
    if(at!=n->bytes){AW_TpNamesClose(n);return -1;}
    return n->rows;
}
int AW_TpNamesGet(aw_tp_names_t *n,long i,char *label,int size,int *category) {
    const unsigned char *r;int len;
    if(!n->block || i<0 || i>=n->rows || size<1 || !(r=names_row(n,(long)n->at[i])))return 0;
    len=r[1]<size-1?r[1]:size-1;
    memcpy(label,r+2,(size_t)len);label[len]=0;
    if(category)*category=r[0];
    return 1;
}
void AW_TpNamesClose(aw_tp_names_t *n) {
    if(n->block)AW_TP_FREE(n->block);
    memset(n,0,sizeof(*n));
}
long AW_TpNamesHeld(const aw_tp_names_t *n) {
    return n->block?(long)(n->rows*sizeof(unsigned long))+(n->names?n->bytes:0):0;
}
long AW_TpNamesFind(FILE *f,long base,long size,const char *text,long *matches,char *list,int list_size) {
    unsigned char head[AW_TPN_HEADER],r[2];char label[AW_TP_NAME];unsigned long rows,bytes;
    long i,at,only=-1,count=0;int used=0,n,any=0,full=0;const char *t;
    if(matches)*matches=0;
    if(list && list_size>0)list[0]=0;
    for(t=text;t && *t;t++)if(fold((unsigned char)*t))any=1;
    if(!any || !f || fseek(f,base,SEEK_SET) || fread(head,1,AW_TPN_HEADER,f)!=AW_TPN_HEADER)return -1;
    if(memcmp(head,"AWTN",4) || head[4] || head[5]!=1 || head[6] || head[7])return -1;
    rows=be32(head+8);bytes=be32(head+12);
    if(rows<1 || rows>65535ul || (long)(AW_TPN_HEADER+bytes)!=size)return -1;
    for(i=0,at=0;i<(long)rows;i++){
        if(at+2>(long)bytes || fread(r,1,2,f)!=2 || r[1]>=AW_TP_NAME || at+2+r[1]>(long)bytes ||
           fread(label,1,r[1],f)!=(size_t)r[1])return -1;
        label[r[1]]=0;at+=2+r[1];
        if(AW_ListBoxNames(label,text)){if(matches)*matches=1;return i;}
        if(!AW_ListBoxMatches(label,text))continue;
        if(!count++)only=i;
        n=(int)strlen(label);
        if(list && !full && used+n+3<list_size){
            if(used){list[used++]=';';list[used++]=' ';}
            memcpy(list+used,label,(size_t)n+1);used+=n;
        }
        else full=1;                          /* the first labels only, in the list's order */
    }
    if(matches)*matches=count;
    return count==1?only:count?-2:-1;
}
long AW_TpKindRows(const unsigned char *data,long size) {
    unsigned long rows;
    if(!data || size<AW_TPK_HEADER || memcmp(data,"AWTK",4) || data[4] || data[5]!=1 || data[6] || data[7]!=AW_TPK_ROW)
        return -1;
    rows=be32(data+8);
    if(rows<1 || rows>65535ul || (long)(AW_TPK_HEADER+rows*AW_TPK_ROW)!=size)return -1;
    return (long)rows;
}
void AW_TpKindRow(const unsigned char *data,long i,aw_tp_place_t *p) {
    const unsigned char *r=data+AW_TPK_HEADER+i*(long)AW_TPK_ROW;
    memset(p,0,sizeof(*p));
    memcpy(p->id,r,AW_TP_ID);p->id[AW_TP_ID-1]=0;
    memcpy(p->map,r+AW_TP_ID,AW_TP_MAP);p->map[AW_TP_MAP-1]=0;
    r+=AW_TP_ID+AW_TP_MAP;
    p->x=signed32(r);p->y=signed32(r+4);p->z=signed32(r+8);
    p->flags=AW_TP_BEING|AW_TP_HAS_Z|(p->map[0]?AW_TP_ROOM:0);
}
/* 16 directions (cos, sin of k * 22.5 degrees) */
static const float dirs[16][2]={{1,0},{.92388f,.38268f},{.70711f,.70711f},{.38268f,.92388f},{0,1},
    {-.38268f,.92388f},{-.70711f,.70711f},{-.92388f,.38268f},{-1,0},{-.92388f,-.38268f},{-.70711f,-.70711f},
    {-.38268f,-.92388f},{0,-1},{.38268f,-.92388f},{.70711f,-.70711f},{.92388f,-.38268f}};
void AW_TpSpotCandidate(const float *centre,const float *from,float radius,int i,float *out) {
    float dx=from[0]-centre[0],dy=from[1]-centre[1],best=-2,d;int k,first=0,ring,step,dir;
    for(k=0;k<16 && (dx || dy);k++){d=dirs[k][0]*dx+dirs[k][1]*dy;if(d>best){best=d;first=k;}}
    if(i<0)i=0;
    ring=(i/16)%3;step=i%16;
    /* the side towards FROM first, then alternating either way round */
    dir=(first+((step&1)?(step+1)/2:16-step/2))%16;
    out[0]=centre[0]+dirs[dir][0]*(radius+24*ring);
    out[1]=centre[1]+dirs[dir][1]*(radius+24*ring);
    out[2]=centre[2];
}
int AW_TpPickSpot(const float *centre,const float *from,float radius,
                  int (*free_at)(void *ctx,const float *point,float *out),void *ctx,float *out) {
    float cand[3];int i;
    for(i=0;i<AW_TP_SPOTS;i++){
        AW_TpSpotCandidate(centre,from,radius,i,cand);
        if(free_at(ctx,cand,out))return i+1;
    }
    return 0;
}
float AW_TpFacingYaw(const float *from,const float *to) {
    float y=(float)(atan2(to[1]-from[1],to[0]-from[0])*180.0/3.14159265358979);
    while(y<0)y+=360;
    while(y>=360)y-=360;
    return y;
}
/* TP-BEING-TRIBUNAL-FALLS-THROUGH-67: the being's feet lifted to a door arrival's height. The arrival search
 * (aw_scene.c standing_spot) looks for a floor from 8 units over the arrival down to 88 under it; handed the feet,
 * its first standing box stood in the floor and it took the next floor under the room (a teleport to 'Ten-Tongues'
 * Weerhat landed 64 units under the pawnbroker's floor). */
void AW_TpBeingArrival(const float *feet,float box_bottom,float *out) {
    out[0]=feet[0];out[1]=feet[1];out[2]=feet[2]-box_bottom+.25f;
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
    static const char head[]="aw_teleport ",room[]="dbg tp ";int at=(int)sizeof(head)-1;
    if(p && out && (p->flags&AW_TP_ROOM)){
        int n=0;at=(int)sizeof(room)-1;
        for(;p->map[n];n++){
            char c=p->map[n];
            if(!((c>='a' && c<='z') || (c>='0' && c<='9') || c=='_'))return -1;
        }
        if(!n || at+n+2>size)return -1;
        memcpy(out,room,(size_t)at);memcpy(out+at,p->map,(size_t)n);at+=n;
        out[at++]='\n';out[at]=0;
        return at;
    }
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
