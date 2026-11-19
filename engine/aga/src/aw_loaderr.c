/* SPDX-License-Identifier: GPL-2.0-or-later
 * The load errors' rules (aw_loaderr.h): kinds, codes, the OK box's text, the load menu's notice, the console's debug
 * block and the map header check. Plain C, no engine state: tests/aga_loaderr_test.c runs it on the host.
 */
#include <stdio.h>
#include <string.h>
#include "aw_loaderr.h"

/* The codes are a writable character table on purpose: as string literals they sat in the code section after the last
 * function, and the build's 68060 check (tools/check_fpu_unimplemented.py) decodes such bytes as instructions: "LF4" reads
 * as a 64-bit divide (divul d6,d0,d3), which failed gate 11150's engine step inside AW_LoadErrMapHeader. */
static char codes[AW_LOADERR_KINDS][4]={"","LF1","LF2","LF3","LF4","LF5","LF6","LF7","LF8","LF9"};
static const char *kinds[AW_LOADERR_KINDS]={"no error","map not found","map not on this disk",
    "no map holds the point","broken map file","not enough memory","the map did not spawn",
    "the load did not finish","a file the map needs is missing","load error"};
static const char *lumps[15]={"entities","planes","textures","vertexes","visibility","nodes","texinfo",
    "faces","lighting","clipnodes","leafs","marksurfaces","edges","surfedges","models"};

const char *AW_LoadErrCode(int kind){return kind>0 && kind<AW_LOADERR_KINDS?codes[kind]:"";}
const char *AW_LoadErrKind(int kind){return kind>=0 && kind<AW_LOADERR_KINDS?kinds[kind]:"load error";}
const char *AW_LoadErrLumpName(int lump){return lump>=0 && lump<15?lumps[lump]:"?";}

void AW_LoadErrClean(char *out,int size,const char *in){
    int n=0;
    if(!out || size<1)return;
    for(;in && *in && n<size-1;in++){
        unsigned char c=(unsigned char)*in;
        out[n++]=(char)(c<32 || c>126 || c=='%' || c=='^'?'?':c);
    }
    out[n]=0;
}
/* Appends to a bounded text: the length so far, never past SIZE-1. */
typedef struct {char *out;int size,used;} text_t;
static void put(text_t *t,const char *s){
    while(s && *s && t->used<t->size-1)t->out[t->used++]=*s++;
    if(t->size>0)t->out[t->used<t->size?t->used:t->size-1]=0;
}
static void put_clean(text_t *t,const char *s){char c[160];AW_LoadErrClean(c,sizeof(c),s);put(t,c);}
static void putf_long(text_t *t,const char *format,long a,long b){char s[96];snprintf(s,sizeof(s),format,a,b);put(t,s);}
static long kb(long bytes){return bytes<0?-1:(bytes+1023)/1024;}
/* "bmcaius (Caius Cosades' House)", or the map alone when the place is not known or is the same name */
static void put_map(text_t *t,const aw_loaderr_t *e){
    put_clean(t,e->map[0]?e->map:"?");
    if(e->place[0] && strcmp(e->place,e->map)){put(t," (");put_clean(t,e->place);put(t,")");}
}
static int not_found(int kind){return kind==AW_LOADERR_NOT_FOUND || kind==AW_LOADERR_NOT_ON_DISK;}
int AW_LoadErrReason(const aw_loaderr_t *e,char *out,int size){
    text_t t;t.out=out;t.size=size;t.used=0;
    if(size>0)out[0]=0;
    if(!e)return 0;
    switch(e->kind){
    case AW_LOADERR_NOT_ON_DISK:put(&t,"It is not on this disk.");break;
    case AW_LOADERR_BROKEN:
        put(&t,"Broken map file (");
        if(e->broken==AW_BROKEN_HEADER)put(&t,"bad header");
        else if(e->broken==AW_BROKEN_SHORT)put(&t,"short read");
        else if(e->broken==AW_BROKEN_LUMP && e->lump>=0)putf_long(&t,"bad lump %ld",(long)e->lump,0);
        else put(&t,"bad data");
        put(&t,").");break;
    case AW_LOADERR_MEMORY:putf_long(&t,"Not enough memory (needs %ld KB, %ld KB free).",kb(e->need),kb(e->have));break;
    case AW_LOADERR_NO_SPAWN:put(&t,"The map did not spawn.");break;
    case AW_LOADERR_TIMEOUT:put(&t,"The load did not finish.");break;
    case AW_LOADERR_MISSING_FILE:
        put(&t,"A file it needs is missing");
        if(e->detail[0]){put(&t," (");put_clean(&t,e->detail);put(&t,")");}
        put(&t,".");break;
    case AW_LOADERR_ERROR:
        put(&t,e->in_play?"Error":"Load error");   /* in play no load was running */
        if(e->detail[0]){put(&t,": ");put_clean(&t,e->detail);}
        put(&t,".");break;
    default:break;
    }
    return t.used;
}
static void put_code(text_t *t,const aw_loaderr_t *e){put(t," Code ");put(t,AW_LoadErrCode(e->kind));put(t,".");}
static int no_place(const aw_loaderr_t *e){return e->way==AW_WAY_FAILED || e->way==AW_WAY_NOWHERE;}
/* AW-RECOVER: the way back (or the place again) failed, and the same error came again soon after a recovery; the
 * records before the chain say both with their way alone (AW_WAY_FAILED; in play AW_WAY_NOWHERE) */
static int back_failed(const aw_loaderr_t *e){return e->back_failed || e->way==AW_WAY_FAILED;}
static int again(const aw_loaderr_t *e){return e->again || (e->in_play && e->way==AW_WAY_NOWHERE);}
int AW_LoadErrBox(const aw_loaderr_t *e,char *out,int size){
    text_t t;char reason[192];
    t.out=out;t.size=size;t.used=0;
    if(size>0)out[0]=0;
    if(!e || e->kind<=AW_LOADERR_NONE || e->kind>=AW_LOADERR_KINDS)return 0;
    if(e->in_play){
        /* an error in play, no load running (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66): the place is loaded again */
        put(&t,"An error stopped the game in ");put_map(&t,e);
        if(again(e))put(&t," again soon after");
        else if(back_failed(e))put(&t,", and loading it again failed as well");
        else if(e->way==AW_WAY_BACK)put(&t,"; it was loaded again");
    }
    else if(e->kind==AW_LOADERR_NO_POINT)putf_long(&t,"No map holds the point %ld %ld",(long)e->x,(long)e->y);
    else{put(&t,"Map ");put_map(&t,e);put(&t,not_found(e->kind)?" was not found":" was found but could not be loaded");}
    if(!e->in_play && back_failed(e)){put(&t,", and the way back to ");put_clean(&t,e->back_map[0]?e->back_map:"?");put(&t," failed as well");}
    put(&t,".");
    if(AW_LoadErrReason(e,reason,sizeof(reason))){put(&t,"\n");put(&t,reason);}
    put_code(&t,e);
    put(&t,"\n");
    /* AW-RECOVER: the later steps that were tried and did not load either */
    if(e->save_failed || e->previous_failed){
        put(&t,e->save_failed && e->previous_failed?"The last autosave and the previous map did not load either.":
               e->save_failed?"The last autosave did not load either.":"The previous map did not load either.");
        put(&t,"\n");
    }
    if(no_place(e))put(&t,"Load a saved game to go on.");
    else if(e->way==AW_WAY_AUTOSAVE || e->way==AW_WAY_PREVIOUS){
        /* AW-RECOVER: which one was loaded, then where he is (before the arrival: which one is loading) */
        if(e->way==AW_WAY_AUTOSAVE){
            put(&t,"The last autosave");
            if(e->save_label[0]){put(&t," (");put_clean(&t,e->save_label);put(&t,")");}
        }else{
            put(&t,"The previous map");
            if(e->previous_map[0]){put(&t,", ");put_clean(&t,e->previous_map);put(&t,",");}
        }
        if(e->here_place[0] || e->here_map[0]){
            put(&t," was loaded. You are in ");put_clean(&t,e->here_place[0]?e->here_place:e->here_map);put(&t,".");
        }else put(&t," is loading.");
    }
    else if(!e->here_place[0] && !e->here_map[0] && e->way==AW_WAY_BACK && e->back_map[0]){
        /* the console's block is written when the load fails, before the way back has arrived */
        put(&t,e->in_play?"Loading ":"Going back to ");put_clean(&t,e->back_map);put(&t,e->in_play?" again.":".");
    }
    else{put(&t,"You are in ");put_clean(&t,e->here_place[0]?e->here_place:e->here_map[0]?e->here_map:"the same place");put(&t,".");}
    return t.used;
}
/* One line of the load menu (its notice box holds about 58 characters; the in-game check of 0d6c6e87 showed a
 * 63-character one cut at both ends): the code, the map (at most 20 characters) and whether the way back failed, 56
 * characters at most. The load menu itself is the way on, so the line asks for nothing. */
int AW_LoadErrNotice(const aw_loaderr_t *e,char *out,int size){
    text_t t;char map[21];
    t.out=out;t.size=size;t.used=0;
    if(size>0)out[0]=0;
    if(!e || e->kind<=AW_LOADERR_NONE || e->kind>=AW_LOADERR_KINDS)return 0;
    put(&t,AW_LoadErrCode(e->kind));put(&t,": ");
    AW_LoadErrClean(map,sizeof(map),e->map);
    if(e->in_play){put(&t,"an error stopped the game in ");put(&t,map);put(&t,".");return t.used;}
    if(e->kind==AW_LOADERR_NO_POINT)put(&t,"no map holds that point");
    else{put(&t,"map ");put(&t,map);put(&t,not_found(e->kind)?" was not found":" did not load");}
    put(&t,e->way==AW_WAY_FAILED?"; no way back.":".");
    return t.used;
}
static void put_point(text_t *t,const char *map,const float *at){
    put_clean(t,map[0]?map:"?");putf_long(t," at %ld %ld",(long)at[0],(long)at[1]);putf_long(t," %ld",(long)at[2],0);
}
int AW_LoadErrConsole(const aw_loaderr_t *e,char *out,int size){
    text_t t;char box[1024],*p;
    t.out=out;t.size=size;t.used=0;
    if(size>0)out[0]=0;
    if(!e || e->kind<=AW_LOADERR_NONE || e->kind>=AW_LOADERR_KINDS)return 0;
    AW_LoadErrBox(e,box,sizeof(box));
    for(p=box;*p;p++)if(*p=='\n')*p=' ';
    put(&t,"Load error ");put(&t,AW_LoadErrCode(e->kind));put(&t," (");put(&t,AW_LoadErrKind(e->kind));put(&t,"): ");
    put(&t,box);put(&t,"\n");
    put(&t,"  command: ");put_clean(&t,e->command[0]?e->command:"(not recorded)");put(&t,"\n");
    if(e->kind==AW_LOADERR_NO_POINT)putf_long(&t,"  point: %ld %ld (original coordinates)\n",(long)e->x,(long)e->y);
    else{
        put(&t,"  map: ");put_map(&t,e);
        if(e->file[0]){put(&t,", file ");put_clean(&t,e->file);}
        if(e->file_bytes>=0)putf_long(&t,", %ld bytes",e->file_bytes,0);
        put(&t,"\n");
    }
    if(e->kind==AW_LOADERR_BROKEN || e->detail[0]){
        put(&t,"  error: ");
        if(e->kind==AW_LOADERR_BROKEN){
            put(&t,e->broken==AW_BROKEN_HEADER?"bad header":e->broken==AW_BROKEN_SHORT?"short read":"bad data");
            if(e->lump>=0){putf_long(&t," in lump %ld",(long)e->lump,0);put(&t," (");put(&t,AW_LoadErrLumpName(e->lump));put(&t,")");}
            if(e->offset>=0)putf_long(&t," at offset %ld",e->offset,0);
            if(e->detail[0])put(&t,": ");
        }
        put_clean(&t,e->detail);put(&t,"\n");
    }
    put(&t,"  memory: ");
    if(e->kind==AW_LOADERR_MEMORY){
        putf_long(&t,"needs %ld KB, %ld KB free",kb(e->need),kb(e->have));
        if(e->arena[0]){put(&t," (");put_clean(&t,e->arena);put(&t,")");}
        put(&t,"; ");
    }
    if(e->fast_free>=0)putf_long(&t,"Fast %ld KB free, Chip %ld KB free\n",kb(e->fast_free),kb(e->chip_free));
    else put(&t,"Fast and Chip free not known\n");
    put(&t,e->in_play?"  stopped at: ":"  left: ");
    if(e->from_ok)put_point(&t,e->from_map,e->from);else put(&t,e->way==AW_WAY_NONE?"nothing (refused before the load)":"no place");
    put(&t,"\n  now: ");
    if(no_place(e))put(&t,e->way==AW_WAY_FAILED?"no place: the way back failed; the load menu":"no place; the load menu");
    else if(e->here_ok){
        put_point(&t,e->here_map,e->here);
        if(e->here_place[0]){put(&t," (");put_clean(&t,e->here_place);put(&t,")");}
        if(e->way==AW_WAY_BACK)put(&t,e->in_play?", the place loaded again":", back where the load started");
        else if(e->way==AW_WAY_AUTOSAVE){
            put(&t,", the last autosave");
            if(e->save_label[0]){put(&t," (");put_clean(&t,e->save_label);put(&t,")");}
        }
        else if(e->way==AW_WAY_PREVIOUS)put(&t,", the previous map");
    }else if(e->way==AW_WAY_BACK){put(&t,e->in_play?"loading again ":"going back to ");put_clean(&t,e->back_map);}
    else if(e->way==AW_WAY_AUTOSAVE){
        put(&t,"loading the last autosave");
        if(e->save_label[0]){put(&t," (");put_clean(&t,e->save_label);put(&t,")");}
    }
    else if(e->way==AW_WAY_PREVIOUS){put(&t,"loading the previous map ");put_clean(&t,e->previous_map);}
    else put(&t,"where he was");
    put(&t,"\n");
    return t.used;
}
static long le32(const unsigned char *p){
    unsigned long v=(unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);
    return v&0x80000000UL?-(long)(((~v)&0xffffffffUL)+1):(long)v;
}
int AW_LoadErrMapHeader(const unsigned char *h,long header_bytes,long file_bytes,int *lump){
    int i;long ofs,len;
    if(lump)*lump=-1;
    if(!h || header_bytes<124 || file_bytes<124 || le32(h)!=29)return AW_BROKEN_HEADER;
    for(i=0;i<15;i++){
        ofs=le32(h+4+i*8);len=le32(h+8+i*8);
        if(ofs<0 || len<0){if(lump)*lump=i;return AW_BROKEN_HEADER;}
        if(ofs>file_bytes || len>file_bytes-ofs){if(lump)*lump=i;return AW_BROKEN_SHORT;}
    }
    return 0;
}
