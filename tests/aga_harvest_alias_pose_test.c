/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
entity_t *currententity;vec3_t modelorg,vright={1,0,0},vup={0,-1,0},vpn={0,0,1};
float aliasxscale=1,aliasyscale=1;clipplane_t view_clipplanes[4];
extern mdl_t *pmdl;extern float aliastransform[3][4];
extern void R_AliasSetUpTransform(int);
extern qboolean AW_AliasSphereVisible(vec3_t,float);
static void transform(vec3_t in,vec3_t out)
{
    int i;R_AliasSetUpTransform(0);for(i=0;i<3;i++)out[i]=DotProduct(in,aliastransform[i])+aliastransform[i][3];
}
int main(int argc,char **argv)
{
    entity_t e;model_t m;mdl_t mdl;FILE *f;vec3_t input,actual,expected;int i,n=0;
    assert(argc==2);memset(&e,0,sizeof e);memset(&m,0,sizeof m);memset(&mdl,0,sizeof mdl);
    currententity=&e;e.model=&m;m.type=mod_alias;pmdl=&mdl;
    for(i=0;i<3;i++)mdl.scale[i]=1;
    f=fopen(argv[1],"r");assert(f);
    while(fscanf(f,"%f %f %f %f %f %f %f %f %f %f %f %f %f",
          &e.origin[0],&e.origin[1],&e.origin[2],&e.angles[0],&e.angles[1],&e.angles[2],&e.aw_sprite_scale,
          &input[0],&input[1],&input[2],&expected[0],&expected[1],&expected[2])==13){
        e.effects=AW_EF_ALIAS_SCALE;for(i=0;i<3;i++)modelorg[i]=-e.origin[i];transform(input,actual);
        for(i=0;i<3;i++)assert(fabs(actual[i]-expected[i])<.001f);n++;
    }
    fclose(f);assert(n>800);
    memset(e.origin,0,sizeof e.origin);memset(e.angles,0,sizeof e.angles);memset(modelorg,0,sizeof modelorg);
    e.aw_sprite_scale=2;e.effects=AW_EF_ALIAS_SCALE;
    mdl.scale[0]=.1f;mdl.scale[1]=.2f;mdl.scale[2]=.3f;mdl.scale_origin[0]=-2;mdl.scale_origin[1]=5;mdl.scale_origin[2]=1;
    input[0]=input[1]=input[2]=10;transform(input,actual);assert(fabs(actual[0]+2)<.0001f && actual[1]==14 && actual[2]==8);
    e.effects=0;transform(input,actual);assert(fabs(actual[0]+1)<.0001f && actual[1]==7 && actual[2]==4); /* legacy alias ignores untagged field */
    m.type=mod_sprite;assert(R_SpriteEntityScale(&e)==2);m.type=mod_alias;e.effects=AW_EF_ALIAS_SCALE;
    memset(view_clipplanes,0,sizeof view_clipplanes);view_clipplanes[0].normal[0]=-1;view_clipplanes[0].dist=-10;
    e.origin[0]=13;m.radius=2;assert(AW_AliasSphereVisible(e.origin,m.radius*R_SpriteEntityScale(&e)));
    e.effects=0;assert(!AW_AliasSphereVisible(e.origin,m.radius*R_SpriteEntityScale(&e)));
    printf("%d synthetic placement vertices match actual alias transform; origin/scale, legacy and scaled sphere controls passed\n",n);return 0;
}
