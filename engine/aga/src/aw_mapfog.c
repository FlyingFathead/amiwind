/* SPDX-License-Identifier: GPL-2.0-or-later
 * The explored map (aw_mapfog.h). */
#include "aw_mapfog.h"
#include "aw_tryalloc.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef struct {short x,y;unsigned char bits[AW_MAPFOG_GRID*AW_MAPFOG_GRID/8];} fog_row_t;
typedef char fog_row_bytes_check[sizeof(fog_row_t)==AW_MAPFOG_ROW_BYTES?1:-1];
static fog_row_t *rows;static int count,capacity,last=-1;

#define ROOM_BYTES (AW_MAPFOG_ROOM_GRID*AW_MAPFOG_ROOM_GRID/8)
typedef struct {char name[16];unsigned char bits[ROOM_BYTES];} fog_room_t;
typedef char fog_room_bytes_check[sizeof(fog_room_t)==AW_MAPFOG_ROOM_BYTES?1:-1];
static fog_room_t *rooms;static int room_count,room_capacity,room_last=-1;
/* MAP-EXPLORED-ROOMS-CAP-66: the rooms by name, open addressing (a slot holds the room's number + 1, 0 is empty),
 * twice the rooms' capacity rounded up to a power of two, made again when the capacity grows: a room is found with a
 * few name compares, never a search of every room (the local map asks 256 times a frame, a load once a room) */
static unsigned short *room_index;static int room_slots;
static int left_cells,left_rooms;
AW_RESIDENT_GROWS("explored map: land cells (MAP-EXPLORED-SAVE-BLOCK-66)",AW_MAPFOG_MAX,AW_MAPFOG_ROW_BYTES);
AW_RESIDENT_GROWS("explored map: rooms (MAP-EXPLORED-ROOMS-CAP-66)",AW_MAPFOG_ROOMS,AW_MAPFOG_ROOM_BYTES);
AW_RESIDENT_GROWS("explored map: the rooms' name index (MAP-EXPLORED-ROOMS-CAP-66)",AW_MAPFOG_ROOMS,AW_MAPFOG_ROOM_INDEX_BYTES);

void AW_MapFogReset(void){
    free(rows);rows=NULL;count=capacity=0;last=-1;
    free(rooms);rooms=NULL;room_count=room_capacity=0;room_last=-1;
    free(room_index);room_index=NULL;room_slots=0;
}
int AW_MapFogRooms(void){return room_count;}
unsigned long AW_MapFogBytes(void){
    return (unsigned long)capacity*sizeof(fog_row_t)+(unsigned long)room_capacity*sizeof(fog_room_t)+
           (unsigned long)room_slots*sizeof(unsigned short);
}
static unsigned name_hash(const char *s){unsigned h=2166136261u;while(*s)h=(h^(unsigned char)*s++)*16777619u;return h;}
static void index_put(int r){
    unsigned mask=(unsigned)room_slots-1,i=name_hash(rooms[r].name)&mask;
    while(room_index[i])i=(i+1)&mask;
    room_index[i]=(unsigned short)(r+1);
}
static int room_find(const char *name){
    unsigned mask=(unsigned)room_slots-1,i;int r;
    if(room_last>=0 && room_last<room_count && !strcmp(rooms[room_last].name,name))return room_last;
    if(!room_slots)return -1;
    for(i=name_hash(name)&mask;(r=room_index[i])!=0;i=(i+1)&mask)if(!strcmp(rooms[r-1].name,name))return room_last=r-1;
    return -1;
}
static int room_add(const char *name){
    size_t n=strlen(name);
    if(n<1 || n>15 || room_count>=AW_MAPFOG_ROOMS)return -1;
    if(room_count==room_capacity){
        int want=room_capacity+AW_MAPFOG_ROOM_BLOCK,slots=64,i;fog_room_t *grown;unsigned short *index;
        while(slots<2*want)slots*=2;
        if(!(index=(unsigned short *)AW_TryCalloc((unsigned long)slots,sizeof(unsigned short))))return -1;
        if(!(grown=(fog_room_t *)AW_TryRealloc(rooms,(unsigned long)sizeof(fog_room_t)*(unsigned long)want))){free(index);return -1;}
        rooms=grown;room_capacity=want;free(room_index);room_index=index;room_slots=slots;
        for(i=0;i<room_count;i++)index_put(i);
    }
    memset(&rooms[room_count],0,sizeof(fog_room_t));memcpy(rooms[room_count].name,name,n);
    index_put(room_count);
    return room_last=room_count++;
}
/* the grid square of X, Y in the room's box; 0 when the box is unusable or the point outside it */
static int room_square(float x,float y,const float *mins,const float *maxs,int *gx,int *gy){
    float w,h;
    if(!mins || !maxs || !isfinite(x) || !isfinite(y))return 0;
    w=maxs[0]-mins[0];h=maxs[1]-mins[1];
    if(!(w>=1 && h>=1 && w<1e6f && h<1e6f))return 0;
    *gx=(int)floorf((x-mins[0])*AW_MAPFOG_ROOM_GRID/w);*gy=(int)floorf((y-mins[1])*AW_MAPFOG_ROOM_GRID/h);
    return *gx>=0 && *gy>=0 && *gx<AW_MAPFOG_ROOM_GRID && *gy<AW_MAPFOG_ROOM_GRID;
}
int AW_MapFogRoomReveal(const char *room,float x,float y,const float *mins,const float *maxs){
    int gx,gy,r,bit,changed=0;float w,h,dx,dy,rr=AW_MAPFOG_ROOM_RADIUS;
    if(!room || !room_square(x,y,mins,maxs,&gx,&gy))return 0;
    if((r=room_find(room))<0 && (r=room_add(room))<0)return 0;
    w=(maxs[0]-mins[0])/AW_MAPFOG_ROOM_GRID;h=(maxs[1]-mins[1])/AW_MAPFOG_ROOM_GRID;
    for(gy=0;gy<AW_MAPFOG_ROOM_GRID;gy++)for(gx=0;gx<AW_MAPFOG_ROOM_GRID;gx++){
        dx=mins[0]+(gx+.5f)*w-x;dy=mins[1]+(gy+.5f)*h-y;
        if(dx*dx+dy*dy>rr*rr && !(fabsf(dx)<=w*.5f && fabsf(dy)<=h*.5f))continue;   /* the square the player stands in always */
        bit=gy*AW_MAPFOG_ROOM_GRID+gx;
        if(!(rooms[r].bits[bit>>3]&(1<<(bit&7)))){rooms[r].bits[bit>>3]|=(unsigned char)(1<<(bit&7));changed=1;}
    }
    return changed;
}
int AW_MapFogRoomSeen(const char *room,float x,float y,const float *mins,const float *maxs){
    int gx,gy,r,bit;
    if(!room || (r=room_find(room))<0 || !room_square(x,y,mins,maxs,&gx,&gy))return 0;
    bit=gy*AW_MAPFOG_ROOM_GRID+gx;return (rooms[r].bits[bit>>3]>>(bit&7))&1;
}
const unsigned char *AW_MapFogRoomBits(const char *room){
    int r=room?room_find(room):-1;
    return r<0?NULL:rooms[r].bits;
}
static int room_full(const fog_room_t *r){int i;for(i=0;i<ROOM_BYTES;i++)if(r->bits[i]!=255)return 0;return 1;}
static int room_size(const fog_room_t *r){return 2+(int)strlen(r->name)+(room_full(r)?0:ROOM_BYTES);}
int AW_MapFogCells(void){return count;}
int AW_MapFogRow(int i,int *x,int *y,const unsigned char **bits){
    if(i<0 || i>=count)return 0;
    *x=rows[i].x;*y=rows[i].y;*bits=rows[i].bits;return 1;
}
static int find(int x,int y){
    int i;
    if(last>=0 && last<count && rows[last].x==x && rows[last].y==y)return last;
    for(i=0;i<count;i++)if(rows[i].x==x && rows[i].y==y)return last=i;
    return -1;
}
static int add(int x,int y){
    fog_row_t *grown;
    if(x<-32768 || x>32767 || y<-32768 || y>32767 || count>=AW_MAPFOG_MAX)return -1;
    if(count==capacity){
        grown=(fog_row_t *)AW_TryRealloc(rows,(unsigned long)sizeof(fog_row_t)*(unsigned long)(capacity+AW_MAPFOG_BLOCK));
        if(!grown)return -1;
        rows=grown;capacity+=AW_MAPFOG_BLOCK;
    }
    memset(&rows[count],0,sizeof(fog_row_t));rows[count].x=(short)x;rows[count].y=(short)y;
    return last=count++;
}
int AW_MapFogReveal(float x,float y){
    const float square=AW_MAPFOG_CELL/AW_MAPFOG_GRID,r=AW_MAPFOG_RADIUS;
    int gx0,gx1,gy0,gy1,gx,gy,cx,cy,row,bit,changed=0;float dx,dy;
    if(!isfinite(x) || !isfinite(y) || fabsf(x)>2.0e8f || fabsf(y)>2.0e8f)return 0;
    gx0=(int)floorf((x-r)/square);gx1=(int)floorf((x+r)/square);
    gy0=(int)floorf((y-r)/square);gy1=(int)floorf((y+r)/square);
    for(gy=gy0;gy<=gy1;gy++)for(gx=gx0;gx<=gx1;gx++){
        /* the square's nearest point to the player within the radius (OpenMW clears a texel by its distance) */
        dx=(gx+.5f)*square-x;dy=(gy+.5f)*square-y;
        if(dx*dx+dy*dy>r*r)continue;
        cx=(int)floorf(gx/(float)AW_MAPFOG_GRID);cy=(int)floorf(gy/(float)AW_MAPFOG_GRID);
        if((row=find(cx,cy))<0 && (row=add(cx,cy))<0)continue;
        bit=(gy-cy*AW_MAPFOG_GRID)*AW_MAPFOG_GRID+(gx-cx*AW_MAPFOG_GRID);
        if(!(rows[row].bits[bit>>3]&(1<<(bit&7)))){rows[row].bits[bit>>3]|=(unsigned char)(1<<(bit&7));changed=1;}
    }
    return changed;
}
int AW_MapFogSeen(float x,float y){
    const float square=AW_MAPFOG_CELL/AW_MAPFOG_GRID;int gx,gy,cx,cy,row,bit;
    if(!count || !isfinite(x) || !isfinite(y) || fabsf(x)>2.0e8f || fabsf(y)>2.0e8f)return 0;
    gx=(int)floorf(x/square);gy=(int)floorf(y/square);
    cx=(int)floorf(gx/(float)AW_MAPFOG_GRID);cy=(int)floorf(gy/(float)AW_MAPFOG_GRID);
    if((row=find(cx,cy))<0)return 0;
    bit=(gy-cy*AW_MAPFOG_GRID)*AW_MAPFOG_GRID+(gx-cx*AW_MAPFOG_GRID);
    return (rows[row].bits[bit>>3]>>(bit&7))&1;
}
#define FOG_BYTES ((int)sizeof(rows[0].bits))
static int full(const fog_row_t *r){int i;for(i=0;i<FOG_BYTES;i++)if(r->bits[i]!=255)return 0;return 1;}
void AW_MapFogLeftOut(int *cells,int *rooms_out){if(cells)*cells=left_cells;if(rooms_out)*rooms_out=left_rooms;}
int AW_MapFogExport(unsigned char *out,int room){
    int i,pass,at=6,rows_n=0,rooms_n=0,size,f;
    if(!out){   /* the bytes the whole map needs */
        int need=6;
        if(!count && !room_count)return 0;
        for(i=0;i<count;i++)need+=full(&rows[i])?5:5+FOG_BYTES;
        if(room_count){need+=6;for(i=0;i<room_count;i++)need+=room_size(&rooms[i]);}
        return need;
    }
    left_cells=count;left_rooms=room_count;
    /* MAP-EXPLORED-SAVE-BLOCK-66 (the save contract: the land is never cut): every land row or none; the save gives the
     * section the bytes the whole map needs, so nothing is ever left out there */
    for(size=6,i=0;i<count;i++)size+=full(&rows[i])?5:5+FOG_BYTES;
    if(size>room)return 0;
    /* the fully explored cells first (5 bytes each), then the others (13) */
    for(pass=0;pass<2;pass++)for(i=0;i<count;i++){
        if((f=full(&rows[i]))!=(pass==0))continue;
        size=f?5:5+FOG_BYTES;
        out[at]=(unsigned char)(rows[i].x&255);out[at+1]=(unsigned char)((rows[i].x>>8)&255);
        out[at+2]=(unsigned char)(rows[i].y&255);out[at+3]=(unsigned char)((rows[i].y>>8)&255);
        if(f)out[at+4]=1;else{out[at+4]=0;memcpy(out+at+5,rows[i].bits,FOG_BYTES);}
        at+=size;rows_n++;
    }
    memcpy(out,"AWFG",4);out[4]=(unsigned char)(rows_n&255);out[5]=(unsigned char)(rows_n>>8);
    left_cells=count-rows_n;
    if(room_count && at+6<=room){   /* the rooms that fit, the fully explored first */
        int start=at;
        at+=6;
        for(pass=0;pass<2;pass++)for(i=0;i<room_count;i++){
            int len=(int)strlen(rooms[i].name);
            if((f=room_full(&rooms[i]))!=(pass==0))continue;
            if(at+(size=room_size(&rooms[i]))>room)continue;
            out[at]=(unsigned char)len;memcpy(out+at+1,rooms[i].name,(size_t)len);
            if(f)out[at+1+len]=1;
            else{out[at+1+len]=0;memcpy(out+at+2+len,rooms[i].bits,ROOM_BYTES);}
            at+=size;rooms_n++;
        }
        if(rooms_n){memcpy(out+start,"AWFI",4);out[start+4]=(unsigned char)(rooms_n&255);out[start+5]=(unsigned char)(rooms_n>>8);}
        else at=start;   /* not one room fitted: no part for them */
    }
    left_rooms=room_count-rooms_n;
    return at;
}
/* 1 when no cell has two rows (a load's check): the cells sorted in a list taken for the check only */
static int key_order(const void *a,const void *b){
    unsigned long x=*(const unsigned long *)a,y=*(const unsigned long *)b;
    return x<y?-1:x>y;
}
static int rows_unique(void){
    unsigned long *k;int i,j,ok=1;
    if(count<2)return 1;
    if(!(k=(unsigned long *)AW_TryMalloc((unsigned long)sizeof(unsigned long)*(unsigned long)count))){
        for(i=1;i<count;i++)for(j=0;j<i;j++)if(rows[i].x==rows[j].x && rows[i].y==rows[j].y)return 0;   /* no memory: slowly */
        return 1;
    }
    for(i=0;i<count;i++)k[i]=((unsigned long)(unsigned short)rows[i].x<<16)|(unsigned long)(unsigned short)rows[i].y;
    qsort(k,(size_t)count,sizeof(*k),key_order);
    for(i=1;i<count;i++)if(k[i]==k[i-1])ok=0;
    free(k);return ok;
}
int AW_MapFogImport(const unsigned char *p,int bytes){
    int i,n,at=6,x,y,row;
    AW_MapFogReset();
    if(!p || bytes<6 || memcmp(p,"AWFG",4))return -1;
    n=p[4]|(p[5]<<8);
    if(n>AW_MAPFOG_MAX)return -1;
    for(i=0;i<n;i++){
        if(at+5>bytes || p[at+4]>1 || (!p[at+4] && at+5+FOG_BYTES>bytes)){AW_MapFogReset();return -1;}
        x=(short)(p[at]|(p[at+1]<<8));y=(short)(p[at+2]|(p[at+3]<<8));
        if((row=add(x,y))<0){AW_MapFogReset();return -1;}
        if(p[at+4]){memset(rows[row].bits,255,FOG_BYTES);at+=5;}
        else{memcpy(rows[row].bits,p+at+5,FOG_BYTES);at+=5+FOG_BYTES;}
    }
    if(!rows_unique()){AW_MapFogReset();return -1;}
    if(at+6<=bytes && !memcmp(p+at,"AWFI",4)){   /* stage 3: the rooms (absent in older saves) */
        char name[16];int len,r;
        n=p[at+4]|(p[at+5]<<8);at+=6;
        if(n>AW_MAPFOG_ROOMS){AW_MapFogReset();return -1;}
        for(i=0;i<n;i++){
            if(at+1>bytes || (len=p[at])<1 || len>15 || at+2+len>bytes || p[at+1+len]>1 ||
               (!p[at+1+len] && at+2+len+ROOM_BYTES>bytes)){AW_MapFogReset();return -1;}
            memcpy(name,p+at+1,(size_t)len);name[len]=0;
            if(memchr(name,0,(size_t)len) || room_find(name)>=0 || (r=room_add(name))<0){AW_MapFogReset();return -1;}
            if(p[at+1+len]){memset(rooms[r].bits,255,ROOM_BYTES);at+=2+len;}
            else{memcpy(rooms[r].bits,p+at+2+len,ROOM_BYTES);at+=2+len+ROOM_BYTES;}
        }
    }
    return at;
}
