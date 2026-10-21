/* SPDX-License-Identifier: GPL-2.0-or-later
 * Compact terrain records (EXPERIMENTAL, world format 0.10): the engine's
 * expander (chim/chim_terc.c) against the builder's records
 * (tests/test_chim_terc.py writes N.trc, the compact record, and N.img, the
 * BSP29 image it was packed from). One line per record: "N same" when the
 * expansion is that image byte for byte. Then a cut record, a wrong magic and
 * too little room must be refused.
 *
 * argv: DIR COUNT OUT.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "chim/chim_format.h"
#include "chim/chim_terc.h"

static unsigned char packed[1<<17],image[1<<17],out[1<<17];

static long Load(const char *dir,int n,const char *ext,unsigned char *to){
    char path[512];FILE *f;long got;
    snprintf(path,sizeof(path),"%s/%d.%s",dir,n,ext);
    f=fopen(path,"rb");if(!f)return -1;
    got=(long)fread(to,1,1<<17,f);fclose(f);return got;
}

int main(int argc,char **argv){
    FILE *o;int n,count,bad=0;long pb=0,ib=0,got;
    if(argc!=4)return 2;
    count=atoi(argv[2]);
    o=fopen(argv[3],"w");if(!o)return 2;
    for(n=0;n<count;n++){
        pb=Load(argv[1],n,"trc",packed);ib=Load(argv[1],n,"img",image);
        if(pb<0||ib<0)return 2;
        if(ChimTerc_Expand(packed,pb,out,sizeof(out),&got) && got==ib && !memcmp(out,image,(size_t)ib))
            fprintf(o,"%d same%c",n,10);
        else
            fprintf(o,"%d differs%c",n,10);
    }
    /* the last record: cut short, wrong magic, too little room */
    if(ChimTerc_Expand(packed,pb-4,out,sizeof(out),&got))bad++;
    if(ChimTerc_Expand(packed,pb,out,ib-1,&got))bad++;
    packed[0]^=1;
    if(ChimTerc_Expand(packed,pb,out,sizeof(out),&got))bad++;
    fprintf(o,"%s%c",bad?"refusals FAILED":"refusals ok",10);
    fclose(o);
    return 0;
}
