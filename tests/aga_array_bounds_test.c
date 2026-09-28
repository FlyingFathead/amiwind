/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
extern model_t *loadmodel;
extern byte *mod_base;
texture_t *r_notexture_mip;
client_state_t cl;
extern vec3_t avelocities[162];
float r_avertexnormals[162][3];
void Mod_LoadTexinfo(lump_t *);
void R_EntityParticles(entity_t *);
static float same_float(float v){return v;}
static int same_long(int v){return v;}
float (*LittleFloat)(float)=same_float;
int (*LittleLong)(int)=same_long;
void *Hunk_AllocName(int n,char *s){return calloc(1,n);}
void Sys_Error(char *fmt,...){abort();}
int main(int argc,char **argv){
    int row,col;
    if(argc>1 && !strcmp(argv[1],"particles")){
        entity_t entity;float expected[162][3];
        memset(&entity,0,sizeof(entity));
        srand(7);
        for(row=0;row<162;row++)for(col=0;col<3;col++)
            expected[row][col]=(rand()&255)*.01;
        srand(7);R_EntityParticles(&entity);
        assert(!memcmp(expected,avelocities,sizeof(expected)));
    }else{
        model_t model;texinfo_t input;lump_t lump;
        memset(&model,0,sizeof(model));memset(&input,0,sizeof(input));
        for(row=0;row<2;row++)for(col=0;col<4;col++)input.vecs[row][col]=row*10+col+.25f;
        loadmodel=&model;mod_base=(byte *)&input;
        lump.fileofs=0;lump.filelen=sizeof(input);
        Mod_LoadTexinfo(&lump);
        for(row=0;row<2;row++)for(col=0;col<4;col++)
            assert(model.texinfo[0].vecs[row][col]==input.vecs[row][col]);
        free(model.texinfo);
    }
    return 0;
}
