/* SPDX-License-Identifier: GPL-2.0-or-later
 * The CHIM actor table's instance scales (version 3, EXPERIMENTAL; tools/chim/actors.py writes them): the
 * engine's checks and lookup (chim/chim_actor_table.c ChimActors_ListBytes, ChimActors_ScalesValid,
 * ChimActors_Scale) on a table the builder wrote (tests/test_creature_pose.py). Two broken copies of the scale
 * section must be refused (record indices out of order, a count past the section), then one line per record:
 * its scale (1 when not listed), which the test compares with the builder's reader.
 *
 * argv: TABLE OUT.
 */
#include "quakedef.h"
#include "chim/chim_format.h"
#include "chim/chim_actor_table.h"
#include <stdarg.h>

void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...){(void)fmt;}

static unsigned char data[1<<20],copy[1<<16];

int main(int argc,char **argv){
    FILE *f,*o;long n;unsigned i,nl,nlist,ns;chim_actor_head_t h;unsigned char *s,t[4];
    if(argc!=3)return 2;
    f=fopen(argv[1],"rb");if(!f)return 2;
    n=(long)fread(data,1,sizeof(data),f);fclose(f);
    o=fopen(argv[2],"w");if(!o)return 2;
    if(!ChimActors_Header(data,n,&h) || h.version!=CHIM_ACTOR_VERSION_SCALES){fprintf(o,"header refused%c",10);return 1;}
    nl=h.bytes-h.lists_at;nlist=(unsigned)ChimActors_ListBytes(data+h.lists_at,nl);
    if(!nlist || !ChimActors_ListsValid(data+h.lists_at,nlist,h.bases)){fprintf(o,"lists refused%c",10);return 1;}
    s=data+h.lists_at+nlist;ns=nl-nlist;
    memcpy(copy,s,ns);memcpy(t,copy+4,4);memcpy(copy+4,copy+12,4);memcpy(copy+12,t,4);
    fprintf(o,"%s order%c",ChimActors_ScalesValid(copy,ns,h.records)?"accepted":"refused",10);
    memcpy(copy,s,ns);copy[3]+=1;
    fprintf(o,"%s count%c",ChimActors_ScalesValid(copy,ns,h.records)?"accepted":"refused",10);
    fprintf(o,"%s%c",ChimActors_ScalesValid(s,ns,h.records)?"valid":"invalid",10);
    for(i=0;i<h.records;i++)fprintf(o,"scale %u %.6g%c",i,ChimActors_Scale(s,i),10);
    fclose(o);
    return 0;
}
