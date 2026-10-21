/* SPDX-License-Identifier: GPL-2.0-or-later
 * The CHIM actor table (EXPERIMENTAL; tools/chim/actors.py writes it): the
 * engine's decoders (chim/chim_actor_table.c) read a table the builder wrote
 * (tests/test_chim_actor_table.py); one line per header, cell, record and base
 * (its text in hex), which the test compares with the builder's own reader.
 * A table cut short or with a bad header is refused.
 *
 * argv: TABLE OUT.
 */
#include "quakedef.h"
#include "chim/chim_format.h"
#include "chim/chim_actor_table.h"
#include <stdarg.h>

void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...){(void)fmt;}

static unsigned char data[1<<22];

int main(int argc,char **argv){
    FILE *f,*o;long n;unsigned i,k;chim_actor_head_t h;chim_actor_cell_t c;chim_actor_record_t r;chim_actor_base_t b;
    if(argc!=3)return 2;
    f=fopen(argv[1],"rb");if(!f)return 2;
    n=(long)fread(data,1,sizeof(data),f);fclose(f);
    o=fopen(argv[2],"w");if(!o)return 2;
    if(ChimActors_Header(data,n-4,&h) || ChimActors_Header(data,n+4,&h)){fprintf(o,"size not refused%c",10);return 1;}
    data[0]^=1;
    if(ChimActors_Header(data,n,&h)){fprintf(o,"magic not refused%c",10);return 1;}
    data[0]^=1;
    if(!ChimActors_Header(data,n,&h)){fprintf(o,"header refused%c",10);return 1;}
    fprintf(o,"head %u %u %u%c",h.cells,h.records,h.bases,10);
    for(i=0;i<h.cells;i++){
        ChimActors_Cell(data+h.cells_at+i*CHIM_ACTOR_CELL_BYTES,&c);
        fprintf(o,"cell %d %d %u %u%c",c.cx,c.cy,c.first,c.count,10);
    }
    for(i=0;i<h.records;i++){
        if(!ChimActors_Record(data+h.records_at+i*CHIM_ACTOR_RECORD_BYTES,&h,&r)){fprintf(o,"record %u refused%c",i,10);continue;}
        fprintf(o,"rec %u %d %d %.9g %.9g %.9g %.9g%c",r.key,r.base,r.flags,r.origin[0],r.origin[1],r.origin[2],r.yaw,10);
    }
    for(i=0;i<h.bases;i++){
        if(!ChimActors_Base(data+h.bases_at+i*CHIM_ACTOR_BASE_BYTES,&h,&b)){fprintf(o,"base %u refused%c",i,10);continue;}
        fprintf(o,"base %d %u %u ",b.kind,b.hash,b.bytes);
        for(k=0;k<b.bytes;k++)fprintf(o,"%02x",data[h.text_at+b.at+k]);
        fprintf(o,"%c",10);
    }
    fclose(o);
    return 0;
}
