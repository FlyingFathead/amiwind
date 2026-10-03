/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <assert.h>
#include <setjmp.h>
#include <stdlib.h>
static int fail_calloc, scratch_bytes;
static void *test_calloc(size_t count,size_t size){
    scratch_bytes=(int)(count*size);
    return fail_calloc?NULL:calloc(count,size);
}
#define calloc test_calloc
#include "../engine/aga/src/model.c"
#undef calloc

static byte heap[16*1024*1024];
static int used,allocation_calls,expect_error;
static jmp_buf failure;
static short same_short(short n){return n;}
static int same_long(int n){return n;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
void *Hunk_AllocName(int bytes,char *name){
    void *result;int amount=(bytes+15)&~15;
    assert(amount>=0 && used+amount<(int)sizeof(heap));
    result=heap+used;memset(result,0,amount);used+=amount;allocation_calls++;
    return result;
}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(failure,1);}

static model_t model;
static dmodel_t models[3];
static dnode_t disk[4];
static mplane_t planes[4];
static mleaf_t leaves[3];
static lump_t lump;
static void setup(int count){
    int i;
    memset(&model,0,sizeof(model));memset(models,0,sizeof(models));
    memset(disk,0,sizeof(disk));memset(planes,0,sizeof(planes));memset(leaves,0,sizeof(leaves));
    model.numplanes=4;model.planes=planes;model.numleafs=3;model.leafs=leaves;
    model.numsurfaces=4;model.numsubmodels=3;model.submodels=models;
    leaves[0].contents=CONTENTS_SOLID;leaves[1].contents=CONTENTS_EMPTY;leaves[2].contents=CONTENTS_WATER;
    for(i=0;i<count;i++){
        disk[i].planenum=i;disk[i].children[0]=-2;disk[i].children[1]=-1;
        disk[i].mins[0]=-10;disk[i].maxs[0]=10;
    }
    disk[0].numfaces=1;models[0].headnode[0]=0;models[1].headnode[0]=1;models[2].headnode[0]=-2;
    used=0;allocation_calls=0;expect_error=0;fail_calloc=0;
    loadmodel=&model;mod_base=(byte *)disk;lump.fileofs=0;lump.filelen=count*sizeof(dnode_t);
}

static void real_bsp(const char *path){
    FILE *file;byte *raw;long length;dheader_t *header;dleaf_t *diskleafs;
    dclipnode_t *legacy;int n,i,old_used,new_used,total,render,old_models;
    file=fopen(path,"rb");assert(file);assert(!fseek(file,0,SEEK_END));length=ftell(file);
    assert(length>=124 && !fseek(file,0,SEEK_SET));raw=malloc(length);assert(raw);
    assert(fread(raw,1,length,file)==(size_t)length);fclose(file);header=(dheader_t *)raw;
    assert(header->version==29);memset(&model,0,sizeof(model));
    model.numplanes=header->lumps[LUMP_PLANES].filelen/sizeof(dplane_t);
    model.planes=calloc(model.numplanes,sizeof(mplane_t));assert(model.planes);
    model.numleafs=header->lumps[LUMP_LEAFS].filelen/sizeof(dleaf_t);
    model.leafs=calloc(model.numleafs,sizeof(mleaf_t));assert(model.leafs);
    diskleafs=(dleaf_t *)(raw+header->lumps[LUMP_LEAFS].fileofs);
    for(i=0;i<model.numleafs;i++)model.leafs[i].contents=diskleafs[i].contents;
    model.numsurfaces=header->lumps[LUMP_FACES].filelen/sizeof(dface_t);
    model.numsubmodels=header->lumps[LUMP_MODELS].filelen/sizeof(dmodel_t);
    model.submodels=(dmodel_t *)(raw+header->lumps[LUMP_MODELS].fileofs);
    loadmodel=&model;mod_base=raw;used=allocation_calls=0;
    old_models=model.numsubmodels;model.numsubmodels=1;
    Mod_LoadNodes(&header->lumps[LUMP_NODES]);Mod_MakeHull0();
    total=model.numnodes;old_used=used;
    legacy=malloc(total*sizeof(*legacy));assert(legacy);
    memcpy(legacy,model.hulls[0].clipnodes,total*sizeof(*legacy));
    model.numsubmodels=old_models;used=allocation_calls=0;
    Mod_LoadNodes(&header->lumps[LUMP_NODES]);Mod_MakeHull0();
    render=model.numnodes;new_used=used;
    assert(!memcmp(legacy,model.hulls[0].clipnodes,total*sizeof(*legacy)));
    assert(model.hulls[0].lastclipnode==total-1);
    for(i=0;i<render;i++)for(n=0;n<2;n++){
        mnode_t *child=model.nodes[i].children[n];
        if(child->contents>=0)assert(child>=model.nodes && child<model.nodes+render);
    }
    printf("%s: total=%d render=%d exact_hull0=yes host_saved=%d scratch=%d\n",path,total,render,old_used-new_used,scratch_bytes);
    free(legacy);free(model.planes);free(model.leafs);free(raw);
}

int main(int argc,char **argv){
    dclipnode_t legacy[4];int count=3,legacy_used,before,i;
    if(argc>1){for(i=1;i<argc;i++)real_bsp(argv[i]);return 0;}
    setup(count);disk[1].children[0]=2;disk[2].children[0]=-3;
    model.numsubmodels=1; /* Force the unchanged generic loader as a control. */
    Mod_LoadNodes(&lump);Mod_MakeHull0();
    assert(!aw_direct_hull0 && model.numnodes==3);
    memcpy(legacy,model.hulls[0].clipnodes,count*sizeof(*legacy));legacy_used=used;
    setup(count);disk[1].children[0]=2;disk[2].children[0]=-3;
    Mod_LoadNodes(&lump);before=allocation_calls;Mod_MakeHull0();
    assert(aw_direct_hull0 && model.numnodes==1 && allocation_calls==before);
    assert(!memcmp(legacy,model.hulls[0].clipnodes,count*sizeof(*legacy)));
    assert(used<legacy_used && scratch_bytes==1);
    assert(model.hulls[0].lastclipnode==2 && models[1].headnode[0]==1 && models[2].headnode[0]==-2);
    assert(model.nodes[0].parent==NULL && leaves[1].parent==model.nodes && leaves[0].parent==model.nodes);
    assert(model.nodes[0].firstsurface==0 && model.nodes[0].numsurfaces==1);
    for(i=0;i<count;i++)assert(model.hulls[0].clipnodes[i].planenum==disk[i].planenum);
    /* Optional scratch allocation failure and shared roots use the legacy path. */
    setup(2);fail_calloc=1;Mod_LoadNodes(&lump);assert(!aw_direct_hull0 && model.numnodes==2);
    setup(2);models[1].headnode[0]=0;Mod_LoadNodes(&lump);assert(!aw_direct_hull0 && model.numnodes==2);
    /* A world tree spanning a disconnected inline node is not a valid prefix. */
    setup(3);disk[0].children[0]=2;Mod_LoadNodes(&lump);assert(!aw_direct_hull0 && model.numnodes==3);
    setup(2);disk[1].numfaces=1;Mod_LoadNodes(&lump);assert(!aw_direct_hull0);
    setup(3);Mod_LoadNodes(&lump);assert(!aw_direct_hull0); /* orphan tail */
    /* Invalid disk ranges must fail before allocating or making pointers. */
    setup(2);disk[1].children[0]=-4;expect_error=1;
    if(!setjmp(failure)){Mod_LoadNodes(&lump);assert(0);}assert(allocation_calls==0);
    setup(2);disk[1].planenum=4;expect_error=1;
    if(!setjmp(failure)){Mod_LoadNodes(&lump);assert(0);}assert(allocation_calls==0);
    setup(2);models[1].headnode[0]=99;expect_error=1;
    if(!setjmp(failure)){Mod_LoadNodes(&lump);assert(0);}assert(allocation_calls==0);
    return 0;
}
