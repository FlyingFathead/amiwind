/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>

/* Keep address/bounds checks; process enumeration for leak checking is not
 * available on all test hosts. This fixture frees its only allocation. */
const char *__asan_default_options(void){return "detect_leaks=0";}

client_state_t cl;
cvar_t aw_torch_strength={"aw_torch_strength","0.7",true,false,.7f};cvar_t aw_guard_torch_radius={"aw_guard_torch_radius","1",true,false,1};
dlight_t cl_dlights[MAX_DLIGHTS];
entity_t cl_entities[MAX_EDICTS];
entity_t *cl_visedicts[MAX_VISEDICTS];
int cl_numvisedicts;
vec3_t modelorg, base_modelorg, r_entorigin, r_worldmodelorg, r_emins, r_emaxs;
clipplane_t view_clipplanes[4];
entity_t *currententity;
viddef_t vid;
qboolean insubmodel;
mnode_t *r_pefragtopnode;
extern unsigned blocklights[18*18];
extern void R_AddDynamicLights(void);
extern int r_dlightframecount;
static mnode_t leaf;
int AW_ModelVisible(vec3_t point, float radius){return 1;}
void R_RotateBmodel(void){}
void R_EntityRotate(vec3_t point){float x=point[0];point[0]=point[1];point[1]=-x;}
void R_TransformFrustum(void){}
void R_ZDrawSubmodelPolys(model_t *model){}
void R_SplitEntityOnNode2(mnode_t *node){r_pefragtopnode=&leaf;}
void R_DrawSolidClippedSubmodelPolygo(model_t *model){}
void R_DrawSubmodelPolygons(model_t *model,int flags){}

int main(void)
{
    model_t world,brush;
    entity_t ent;
    mplane_t plane;
    mtexinfo_t tex;
    msurface_t surfaces[3],worldsurface;
    mnode_t *node;
    int i;
    memset(&world,0,sizeof(world));memset(&brush,0,sizeof(brush));
    memset(&ent,0,sizeof(ent));memset(&plane,0,sizeof(plane));
    memset(&tex,0,sizeof(tex));memset(surfaces,0,sizeof(surfaces));
    memset(&worldsurface,0,sizeof(worldsurface));
    /* Match converted non-colliding scenery: visible faces but a leaf root.
     * An allocation boundary catches treating -5 as a node array index. */
    node=calloc(1,sizeof(*node));assert(node);
    leaf.contents=-1;world.nodes=&leaf;world.surfaces=&worldsurface;
    world.numsurfaces=1;cl.worldmodel=&world;
    brush.type=mod_brush;brush.nodes=node;brush.numnodes=1;
    brush.hulls[0].firstclipnode=-5;
    brush.surfaces=surfaces;brush.numsurfaces=3;
    brush.firstmodelsurface=1;brush.nummodelsurfaces=1;
    brush.radius=64;
    for(i=0;i<3;i++){brush.mins[i]=-16;brush.maxs[i]=16;}
    plane.normal[2]=1;tex.vecs[0][0]=tex.vecs[1][1]=1;
    surfaces[1].plane=&plane;surfaces[1].texinfo=&tex;
    surfaces[1].extents[0]=surfaces[1].extents[1]=16;
    ent.model=&brush;ent.origin[0]=1000;ent.angles[1]=90;
    cl_visedicts[0]=&ent;cl_numvisedicts=1;
    for(i=0;i<4;i++)view_clipplanes[i].dist=-10000;
    r_drawentities.value=1;r_framecount=10;cl.time=1;
    /* No dynamic light: rc7 survives. Turning one on reaches the bad root. */
    R_DrawBEntitiesOnList();
    cl_dlights[0].die=2;cl_dlights[0].radius=144;cl_dlights[0].minlight=16;
    cl_dlights[0].origin[0]=1000;cl_dlights[0].origin[2]=24;
    R_DrawBEntitiesOnList();
    assert(surfaces[1].dlightframe==10 && surfaces[1].dlightbits==1);
    assert(!surfaces[0].dlightbits && !surfaces[2].dlightbits && !worldsurface.dlightbits);
    r_drawsurf.surf=&surfaces[1];memset(blocklights,0,sizeof(unsigned)*18*18);
    R_AddDynamicLights();assert(blocklights[0]>0 && blocklights[3]>0);
    /* A collision-only positive root has zero faces: it must still light. */
    brush.hulls[0].firstclipnode=0;node->plane=&plane;
    node->children[0]=node->children[1]=&leaf;
    surfaces[1].dlightframe=0;surfaces[1].dlightbits=0;
    R_DrawBEntitiesOnList();assert(surfaces[1].dlightbits==1);
    /* A separate model starting at face zero uses its own array too. */
    brush.firstmodelsurface=0;brush.nummodelsurfaces=3;
    surfaces[0]=surfaces[1];surfaces[2]=surfaces[1];
    surfaces[2].flags=SURF_DRAWTILED;
    for(i=0;i<3;i++)surfaces[i].dlightbits=surfaces[i].dlightframe=0;
    R_DrawBEntitiesOnList();
    assert(surfaces[0].dlightbits==1 && surfaces[1].dlightbits==1);
    assert(!surfaces[2].dlightbits && !worldsurface.dlightbits);
    /* The final light bit is valid; expired and zero-radius slots do not mark. */
    cl_dlights[MAX_DLIGHTS-1]=cl_dlights[0];cl_dlights[0].die=0;
    r_framecount++;
    R_DrawBEntitiesOnList();
    assert((unsigned)surfaces[1].dlightbits==(1u<<(MAX_DLIGHTS-1)));
    memset(blocklights,0,sizeof(unsigned)*18*18);R_AddDynamicLights();
    assert(blocklights[0]>0);
    /* Another instance far away must not inherit current-frame light marks. */
    r_framecount++;ent.origin[0]=3000;
    R_DrawBEntitiesOnList();assert(surfaces[1].dlightframe!=r_framecount);
    ent.origin[0]=1000;cl_dlights[MAX_DLIGHTS-1].radius=0;
    R_DrawBEntitiesOnList();assert(surfaces[1].dlightframe!=r_framecount);
    /* Bad face ranges must never address outside the owning array. */
    cl_dlights[0].die=2;brush.firstmodelsurface=2;brush.nummodelsurfaces=2;
    R_DrawBEntitiesOnList();assert(surfaces[1].dlightframe!=r_framecount);
    free(node);
    return 0;
}
