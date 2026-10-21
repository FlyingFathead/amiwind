/* SPDX-License-Identifier: GPL-2.0-or-later
 * Levelled creature lists of the CHIM actor table (version 2, EXPERIMENTAL; tools/chim/actors.py writes it): the
 * engine's list check and roll (chim/chim_actor_table.c ChimActors_ListsValid, ChimActors_LevelledPick) on a
 * table the builder wrote (tests/test_chim_levelled.py). First three broken copies of the list section must be
 * refused (a chance none over 100, a target past the bases, a section cut short), then one line per levelled
 * base, player level 1-30 and seed 0-39: the base index the roll gives (-1 nothing), which the test compares with
 * the builder's own roll.
 *
 * argv: TABLE OUT.
 */
#include "quakedef.h"
#include "chim/chim_format.h"
#include "chim/chim_actor_table.h"
#include <stdarg.h>

void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...){(void)fmt;}

static unsigned char data[1<<20],copy[1<<20];

int main(int argc,char **argv){
    FILE *f,*o;long n;unsigned i,level,seed,state,lists,nl,entries_at;chim_actor_head_t h;chim_actor_base_t b;
    unsigned char *s;
    if(argc!=3)return 2;
    f=fopen(argv[1],"rb");if(!f)return 2;
    n=(long)fread(data,1,sizeof(data),f);fclose(f);
    o=fopen(argv[2],"w");if(!o)return 2;
    if(!ChimActors_Header(data,n,&h) || h.version!=CHIM_ACTOR_VERSION_LISTS){fprintf(o,"header refused%c",10);return 1;}
    s=data+h.lists_at;nl=h.bytes-h.lists_at;lists=ChimFormat_U32(s);entries_at=4+lists*CHIM_ACTOR_LIST_BYTES;
    memcpy(copy,s,nl);copy[4+6]=101;
    fprintf(o,"%s chance%c",ChimActors_ListsValid(copy,nl,h.bases)?"accepted":"refused",10);
    memcpy(copy,s,nl);copy[entries_at+2]=(unsigned char)(h.bases>>8);copy[entries_at+3]=(unsigned char)h.bases;
    fprintf(o,"%s target%c",ChimActors_ListsValid(copy,nl,h.bases)?"accepted":"refused",10);
    fprintf(o,"%s size%c",ChimActors_ListsValid(s,nl-4,h.bases)?"accepted":"refused",10);
    fprintf(o,"%s%c",ChimActors_ListsValid(s,nl,h.bases)?"valid":"invalid",10);
    for(i=0;i<h.bases;i++){
        if(!ChimActors_Base(data+h.bases_at+i*CHIM_ACTOR_BASE_BYTES,&h,&b)){fprintf(o,"base %u refused%c",i,10);continue;}
        if(b.kind!=CHIM_ACTOR_KIND_LEVELLED)continue;
        for(level=1;level<=30;level++)
            for(seed=0;seed<40;seed++){
                state=ChimActors_RollSeed(1000+i,seed);
                fprintf(o,"pick %u %u %u %d%c",i,level,seed,ChimActors_LevelledPick(s,b.at,(int)level,&state),10);
            }
    }
    fclose(o);
    return 0;
}
