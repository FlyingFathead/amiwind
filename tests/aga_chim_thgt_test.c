/* SPDX-License-Identifier: GPL-2.0-or-later
 * Generated terrain records (EXPERIMENTAL, world format 0.11): the engine's generator (chim/chim_thgt.c) against
 * the builder's records (tests/test_chim_thgt.py writes N.thg, the generated record, and N.img, the BSP29 image it
 * stands for). One line per record: "N same" when the generated image is that image byte for byte. Then the work
 * counted over all records, and a cut record, a wrong magic and too little room must be refused.
 *
 * argv: DIR COUNT OUT.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "chim/chim_format.h"
#include "chim/chim_thgt.h"

static unsigned char rec[1<<17],image[1<<17],out[1<<17];

static long Load(const char *dir,int n,const char *ext,unsigned char *to){
    char path[512];FILE *f;long got;
    snprintf(path,sizeof(path),"%s/%d.%s",dir,n,ext);
    f=fopen(path,"rb");if(!f)return -1;
    got=(long)fread(to,1,1<<17,f);fclose(f);return got;
}

int main(int argc,char **argv){
    FILE *o;int n,count,bad=0;long rb=0,ib=0,got;chim_thgt_stats_t st;
    if(argc!=4)return 2;
    count=atoi(argv[2]);
    o=fopen(argv[3],"w");if(!o)return 2;
    memset(&st,0,sizeof(st));
    for(n=0;n<count;n++){
        rb=Load(argv[1],n,"thg",rec);ib=Load(argv[1],n,"img",image);
        if(rb<0||ib<0)return 2;
        if(ChimThgt_Generate(rec,rb,out,sizeof(out),&got,&st) && got==ib && !memcmp(out,image,(size_t)ib))
            fprintf(o,"%d same%c",n,10);
        else
            fprintf(o,"%d differs%c",n,10);
    }
    fprintf(o,"work records %lu tiles %lu surfaces %lu splits %lu texture_splits %lu vertexes %lu faces %lu nodes %lu leaves %lu%c",
        st.records,st.tiles,st.surfaces,st.splits,st.texture_splits,st.vertexes,st.faces,st.nodes,st.leaves,10);
    if(ChimThgt_Generate(rec,rb-4,out,sizeof(out),&got,NULL)&&got!=ib)bad++;
    if(ChimThgt_Generate(rec,rb,out,ib-1,&got,NULL))bad++;
    rec[0]^=1;
    if(ChimThgt_Generate(rec,rb,out,sizeof(out),&got,NULL))bad++;
    fprintf(o,"%s%c",bad?"refusals FAILED":"refusals ok",10);
    fclose(o);
    return 0;
}
