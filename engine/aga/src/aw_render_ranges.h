/* GPL-2.0-or-later: bounded pool-relative render range parser. */
#ifndef AW_RENDER_RANGES_H
#define AW_RENDER_RANGES_H
#include <stdlib.h>
#include <limits.h>
#include <errno.h>
typedef struct { int start, count; } aw_render_range_t;
static int AW_ParseRenderRanges(const char *text,int surfaces,aw_render_range_t *out,int capacity)
{
    int n=0;long start,count;char *end;
    if(!text || !*text || surfaces<0)return -1;
    while(*text){
        if(*text<'0' || *text>'9' || n>=capacity)return -1;
        errno=0;start=strtol(text,&end,10);
        if(errno || start>INT_MAX || *end!=':')return -1;
        text=end+1;if(*text<'0' || *text>'9')return -1;
        errno=0;count=strtol(text,&end,10);
        if(errno || count<=0 || count>INT_MAX || start>surfaces || count>surfaces-start)return -1;
        out[n].start=(int)start;out[n++].count=(int)count;
        if(!*end)break;
        if(*end!=',' || !end[1])return -1;
        text=end+1;
    }
    return n;
}
#endif
