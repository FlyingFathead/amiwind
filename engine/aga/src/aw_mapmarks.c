/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's own map markers and the hot marker (aw_mapmarks.h). */
#include "aw_mapmarks.h"
#include "aw_tryalloc.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static aw_mapmark_t *marks;static int count,capacity,most=AW_MAPMARKS_DEFAULT;
static int hot;static float hot_x,hot_y;
/* the pending load (AW_MapMarksDecode with COMMIT), taken by AW_MapMarksLoaded */
static aw_mapmark_t *pending;static int pending_count,pending_hot,pending_ready;static float pending_hx,pending_hy;

void AW_MapMarksReset(void){
    free(marks);marks=NULL;count=capacity=0;hot=0;hot_x=hot_y=0;
    free(pending);pending=NULL;pending_count=pending_hot=pending_ready=0;
}
void AW_MapMarksSetMax(int n){most=n<1?1:n>AW_MAPMARKS_MAX?AW_MAPMARKS_MAX:n;}
int AW_MapMarksMax(void){return most;}
int AW_MapMarksCount(void){return count;}
const aw_mapmark_t *AW_MapMark(int i){return i>=0 && i<count?&marks[i]:NULL;}
static void set_name(aw_mapmark_t *m,const char *name,int number){
    int i,k=0;
    if(name)for(i=0;name[i] && k<AW_MAPMARK_NAME;i++)m->name[k++]=(name[i]>=32 && name[i]<127)?name[i]:' ';
    while(k>0 && m->name[k-1]==' ')k--;
    m->name[k]=0;
    if(!k)sprintf(m->name,"Marker %d",number);
}
int AW_MapMarkAdd(float x,float y,const char *name){
    if(count>=most)return -1;
    if(count==capacity){
        int grown=capacity?capacity*2:8;aw_mapmark_t *p;
        if(grown>AW_MAPMARKS_MAX)grown=AW_MAPMARKS_MAX;
        p=(aw_mapmark_t *)AW_TryRealloc(marks,(unsigned long)grown*sizeof(*p));
        if(!p)return -2;
        marks=p;capacity=grown;
    }
    marks[count].x=x;marks[count].y=y;set_name(&marks[count],name,count+1);
    return count++;
}
int AW_MapMarkRename(int i,const char *name){
    const char *p=name;
    if(i<0 || i>=count)return 0;
    while(p && *p==' ')p++;
    if(!p || !*p)return 1;
    set_name(&marks[i],p,i+1);return 1;
}
int AW_MapMarkDelete(int i){
    if(i<0 || i>=count)return 0;
    memmove(marks+i,marks+i+1,(size_t)(count-i-1)*sizeof(*marks));
    count--;
    if(!count){free(marks);marks=NULL;capacity=0;}
    return 1;
}
void AW_MapMarksClear(void){free(marks);marks=NULL;count=capacity=0;}
static int folded(int c){if(c>='A' && c<='Z')return c+32;return (c>='a' && c<='z') || (c>='0' && c<='9')?c:0;}
int AW_MapMarkMatches(const char *name,const char *text){
    char a[AW_MAPMARK_NAME+1],b[AW_MAPMARK_NAME+1];int i,k;
    for(i=k=0;name && name[i] && k<AW_MAPMARK_NAME;i++)if(folded((unsigned char)name[i]))a[k++]=(char)folded((unsigned char)name[i]);
    a[k]=0;
    for(i=k=0;text && text[i] && k<AW_MAPMARK_NAME;i++)if(folded((unsigned char)text[i]))b[k++]=(char)folded((unsigned char)text[i]);
    b[k]=0;
    return strstr(a,b)!=NULL;
}
int AW_MapMarkFind(const char *text,int from){
    int i;
    for(i=from<0?0:from;i<count;i++)if(AW_MapMarkMatches(marks[i].name,text))return i;
    return -1;
}
static int same(const char *a,const char *b){
    for(;*a && *b;a++,b++){int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;if(x!=y)return 0;}
    return !*a && !*b;
}
int AW_MapMarkLookup(const char *text){
    int i,n=0;const char *p=text;
    if(!text || !*text)return -1;
    for(;*p>='0' && *p<='9';p++)n=n*10+(*p-'0');
    if(!*p && p!=text)return n>=1 && n<=count?n-1:-1;
    for(i=0;i<count;i++)if(same(marks[i].name,text))return i;
    return AW_MapMarkFind(text,0);
}
int AW_MapHotGet(float *x,float *y){if(hot){if(x)*x=hot_x;if(y)*y=hot_y;}return hot;}
void AW_MapHotSet(float x,float y){hot=1;hot_x=x;hot_y=y;}
void AW_MapHotOff(void){hot=0;}

static void put32(unsigned char *p,long v){unsigned long u=(unsigned long)v;p[0]=(unsigned char)(u>>24);p[1]=(unsigned char)(u>>16);p[2]=(unsigned char)(u>>8);p[3]=(unsigned char)u;}
static long get32(const unsigned char *p){unsigned long u=((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];
    return u&0x80000000UL?-(long)((~u&0xffffffffUL)+1):(long)u;}
static long whole(float v){return (long)floor(v+.5f);}
int AW_MapMarksEncode(unsigned char *out,int room){
    int i,n=8+(hot?8:0),at;
    for(i=0;i<count;i++)n+=9+(int)strlen(marks[i].name);
    if(!count && !hot)return 0;
    if(!out)return n;
    if(n>room)return -1;
    memcpy(out,"AWMK",4);out[4]=1;out[5]=(unsigned char)(count>>8);out[6]=(unsigned char)count;out[7]=(unsigned char)hot;at=8;
    if(hot){put32(out+at,whole(hot_x));put32(out+at+4,whole(hot_y));at+=8;}
    for(i=0;i<count;i++){
        int k=(int)strlen(marks[i].name);
        put32(out+at,whole(marks[i].x));put32(out+at+4,whole(marks[i].y));out[at+8]=(unsigned char)k;
        memcpy(out+at+9,marks[i].name,(size_t)k);at+=9+k;
    }
    return at;
}
int AW_MapMarksDecode(const unsigned char *p,int n,int commit){
    int rows,i,at,k;aw_mapmark_t *list=NULL;
    if(!p){
        if(commit){free(pending);pending=NULL;pending_count=pending_hot=0;pending_ready=1;}
        return 1;
    }
    if(n<8 || memcmp(p,"AWMK",4) || p[4]!=1 || p[7]>1)return 0;
    rows=(p[5]<<8)|p[6];
    if(rows>AW_MAPMARKS_MAX)return 0;
    at=8+(p[7]?8:0);
    if(at>n)return 0;
    if(commit && rows && !(list=(aw_mapmark_t *)AW_TryMalloc((unsigned long)rows*sizeof(*list))))return 0;
    for(i=0;i<rows;i++){
        if(at+9>n){free(list);return 0;}
        k=p[at+8];
        if(k<1 || k>AW_MAPMARK_NAME || at+9+k>n){free(list);return 0;}
        if(list){
            list[i].x=(float)get32(p+at);list[i].y=(float)get32(p+at+4);
            memcpy(list[i].name,p+at+9,(size_t)k);list[i].name[k]=0;
        }
        at+=9+k;
    }
    if(at!=n){free(list);return 0;}
    if(commit){
        free(pending);pending=list;pending_count=rows;pending_hot=p[7];pending_ready=1;
        if(pending_hot){pending_hx=(float)get32(p+8);pending_hy=(float)get32(p+12);}
    }
    return 1;
}
void AW_MapMarksLoaded(void){
    if(!pending_ready)return;
    free(marks);marks=pending;count=capacity=pending_count;
    if(!count){free(marks);marks=NULL;capacity=0;}
    hot=pending_hot;hot_x=pending_hx;hot_y=pending_hy;
    pending=NULL;pending_count=pending_hot=pending_ready=0;
}
