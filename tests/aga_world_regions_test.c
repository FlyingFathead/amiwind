/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_world.h"
#include <assert.h>
static int opens,missing_map,broken_names;
void Con_Printf(char *fmt,...){}
static void word(FILE *f,unsigned n){int i;for(i=0;i<4;i++)fputc((n>>(8*i))&255,f);}
static void number(FILE *f,float value){unsigned n;memcpy(&n,&value,4);word(f,n);}
int COM_FOpenFile(char *name,FILE **out){
    FILE *f=tmpfile();int i,k;float towns[2][7]={{0,0,0,-200,-200,200,200},{4096,0,0,-200,-200,200,200}};
    float rows[2][11]={{1024,0,512,-1024,-1024,1024,1024,-1920,-1920,1920,1920},
                       {3072,0,768,-1024,-1024,1024,1024,-1920,-1920,1920,1920}};
    opens++;assert(f);*out=f;
    if(!strcmp(name,"world/regions.awr")){
        fputs("AWR2",f);word(f,2);
        for(i=0;i<2;i++)for(k=0;k<7;k++)number(f,towns[i][k]);
        for(i=0;i<2;i++){
            char id[8]={0};sprintf(id,"vf%04d",i);fwrite(id,1,8,f);
            for(k=0;k<11;k++)number(f,rows[i][k]);
        }
        rewind(f);return 168;
    }
    if(!strcmp(name,"world/region-names.awn")){
        char labels[128]={0};
        /* A packed file has a nonzero member offset. Names deliberately differ
         * from any town name; negative cells must use floor, not truncation. */
        for(i=0;i<137;i++)fputc(0,f);
        fputs(broken_names?"BAD!":"ARN1",f);word(f,2);word(f,3);
        strcpy(labels,"Western test region");strcpy(labels+64,"Eastern test region");fwrite(labels,1,128,f);
        word(f,(unsigned)-1);word(f,0);word(f,0);
        word(f,0);word(f,0);word(f,1);
        word(f,1);word(f,0);word(f,1);
        fseek(f,137,SEEK_SET);return 176;
    }
    assert(!strncmp(name,"maps/",5));if(missing_map){fclose(f);*out=NULL;return -1;}rewind(f);return 124;
}
int main(void){
    float a[3]={240,0,40},b[3],c[3],source[3];char target[16];int before;
    assert(AW_MapId("vf0000")==AW_MAP_COUNT);
    /* Outdoor save IDs stay fixed when interior sections are appended. */
    assert(AW_MapId("vf8191")==8251 && AW_INTERIOR_MAP_BASE==8252);
    assert(!strcmp(AW_MapName(8251),"vf8191"));
    assert(AW_MapId("vf8192")==-1 && AW_MapId("vf12")==-1 && AW_MapId("vf001x")==-1);
    assert(!strcmp(AW_MapName(AW_MAP_COUNT+1),"vf0001"));
    assert(AW_WorldDestination("seyda",a,target,b));
    assert(!strcmp(target,"vf0000") && b[0]==-784 && b[2]==-472);
    assert(AW_WorldToSource(target,b,source));
    assert(source[0]==960 && source[2]==160);
    before=opens;assert(!AW_WorldDestination(target,b,target,c));assert(opens==before);
    b[0]=1100;assert(AW_WorldDestination("vf0000",b,target,c));
    assert(!strcmp(target,"vf0001") && c[0]==-948 && c[2]==-728);
    assert(AW_WorldToSource(target,c,source) && source[0]==8496 && source[2]==160);
    c[0]=-1100;assert(AW_WorldDestination("vf0001",c,target,b));
    assert(!strcmp(target,"vf0000") && b[0]==948 && b[2]==-472);
    b[0]=-850;assert(AW_WorldDestination("vf0000",b,target,c));
    assert(!strcmp(target,"seyda") && c[0]==174 && c[2]==40);
    a[0]=-240;assert(AW_WorldDestination("balmora",a,target,b));
    assert(!strcmp(target,"vf0001") && b[0]==784 && b[2]==-728);
    b[0]=850;assert(AW_WorldDestination("vf0001",b,target,c));
    assert(!strcmp(target,"balmora") && c[0]==-174 && c[2]==40);
    assert(!AW_WorldDestination("census",a,target,b));
    assert(AW_WorldContains("vf0000",a));a[0]=1900;assert(!AW_WorldContains("vf0000",a));
    a[0]=NAN;assert(!AW_WorldDestination("vf0000",a,target,b));
    source[0]=4000;source[1]=0;source[2]=NAN;
    assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"vf0000") && b[0]==-24 && b[2]==0);
    source[0]=0;assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"seyda"));
    source[0]=16384;assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"balmora"));
    source[0]=200000;assert(!AW_WorldMapTarget(source,target,b));
    source[0]=0;missing_map=1;assert(!AW_WorldMapTarget(source,target,b));missing_map=0;
    source[0]=NAN;assert(!AW_WorldMapTarget(source,target,b));
    source[0]=-0.01f;assert(!strcmp(AW_RegionNameAt(source),"Western test region"));
    before=opens;source[0]=-8192;assert(AW_RegionNameAt(source) && before==opens);
    source[0]=0;assert(!strcmp(AW_RegionNameAt(source),"Eastern test region"));
    before=opens;source[0]=8191;assert(AW_RegionNameAt(source) && opens==before);
    source[0]=8192;assert(AW_RegionNameAt(source) && opens==before+1);
    source[0]=16384;assert(!AW_RegionNameAt(source));
    broken_names=1;source[0]=-1;assert(!AW_RegionNameAt(source));
    source[0]=NAN;assert(!AW_RegionNameAt(source));
    return 0;
}
