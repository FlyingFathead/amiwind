/* SPDX-License-Identifier: GPL-2.0-or-later
 * The loaded room's water plane, moved by SetWaterLevel and ModWaterLevel (MWSCRIPT-WATER-LEVEL-STATIC-67, v0.0.68).
 *
 * A CHIM room's world (tools/chim/interior.py liquid_world) holds its water as ONE level plane at its root node: the
 * open air in front, a CONTENTS_WATER leaf behind, the two "*water" faces (seen from above and from below) on it. Hull
 * 0 shares the node planes (model.c Mod_MakeHull0) and the client draws the same model (one model_t by name), so
 * moving the water is one plane's dist and the faces' vertices: swimming, the breath, the eyes under water and the
 * drawing follow by themselves (world.c SV_PointContents, sv_phys.c SV_CheckWater). The rule of the level is OpenMW
 * 0.51's (apps/openmw/mwscript/cellextensions.cpp OpSetWaterLevel / OpModWaterLevel, lines 201-245: the player's
 * room; mwworld/worldimp.cpp setWaterHeight, lines 1881-1885: its physics and its surface); the script host keeps the
 * level and its save (aw_mwhost.c), this file only the plane.
 *
 * A room whose root is not such a plane (a room with lava carved under its water, a room map with no water node, a
 * map that is no room) keeps its water where it was built, counted with the reason. A level outside the room's box
 * puts the plane at the box's edge: under every placement it draws nothing, over them the room is full. No
 * allocation; while the water is still nothing runs. aw_water_movable 0 leaves every plane where it was built (the
 * method before, for an A/B). */
#include "quakedef.h"
#include "aw_reset.h"
#include "aw_water.h"

#define WATER_VERTS 8

static struct {
    model_t		*model;		/* the world model the plane was found in (sv.worldmodel at the map's attach) */
    mvertex_t	*vertexes;	/* its memory then: a map loaded again in the same model slot has its own */
    mnode_t		*root;
    mplane_t	*plane;
    mleaf_t		*above,*below;
    int			verts[WATER_VERTS],nverts;
    float		lo,hi,z;	/* the room box's floor and top, the plane now (map units) */
    int			movable,widened;
    const char	*why;
} plane;
static unsigned long plane_maps,plane_found,plane_moves,plane_clamped,plane_refused;
static cvar_t aw_water_movable = {"aw_water_movable", "1"};

/* The CHIM room's hook (aw_water.h aw_water_relink): defined by the room loader, chim/chim_room.c, which links again
 * the placements whose box the plane passed, so each is drawn on its right side of the surface. */

static int water_face(const model_t *m,int s)
{
    const msurface_t *f;
    if(s<0 || s>=m->numsurfaces)return 0;
    f=m->surfaces+s;
    return (f->flags&SURF_DRAWTURB) && f->texinfo && f->texinfo->texture &&
           !Q_strcasecmp(f->texinfo->texture->name,"*water");
}
static void add_vertex(int v)
{
    int i;
    for(i=0;i<plane.nverts;i++)if(plane.verts[i]==v)return;
    if(plane.nverts<WATER_VERTS)plane.verts[plane.nverts++]=v;else plane.why="its water faces have too many corners";
}
static int faces_vertices(const model_t *m,const mnode_t *n)
{
    int s,k;
    for(s=n->firstsurface;s<n->firstsurface+n->numsurfaces;s++){
        const msurface_t *f=m->surfaces+s;
        for(k=0;k<f->numedges;k++){
            int e=m->surfedges[f->firstedge+k],a=e<0?-e:e;
            if(a>=m->numedges)return 0;
            add_vertex(m->edges[a].v[e<0?1:0]);
            add_vertex(m->edges[a].v[e<0?0:1]);
        }
    }
    for(k=0;k<plane.nverts;k++)if(plane.verts[k]<0 || plane.verts[k]>=m->numvertexes)return 0;
    return plane.nverts>=3 && plane.nverts<=WATER_VERTS;
}

int AW_WaterPlaneFind(void)
{
    model_t *m=sv.worldmodel;mnode_t *n;
    memset(&plane,0,sizeof(plane));
    plane_maps++;
    plane.why="no map";
    if(!m || m->type!=mod_brush || m->numnodes<1 || !m->nodes)return 0;
    n=m->nodes+m->hulls[0].firstclipnode;
    plane.why="its root is no level plane";
    if(m->hulls[0].firstclipnode<0 || m->hulls[0].firstclipnode>=m->numnodes || n->contents!=0 || !n->plane ||
       n->plane->normal[2]<0.999f)return 0;
    plane.why="no water face on its root";
    if(n->numsurfaces!=2 || !water_face(m,n->firstsurface) || !water_face(m,n->firstsurface+1))return 0;
    plane.why="lava or another liquid is carved beside the water";
    if(!n->children[0] || !n->children[1] || n->children[0]->contents!=CONTENTS_EMPTY ||
       n->children[1]->contents!=CONTENTS_WATER)return 0;
    plane.why="its water faces do not check out";
    if(!faces_vertices(m,n))return 0;
    plane.model=m;plane.vertexes=m->vertexes;plane.root=n;plane.plane=n->plane;
    plane.above=(mleaf_t *)n->children[0];plane.below=(mleaf_t *)n->children[1];
    plane.lo=m->mins[2];plane.hi=m->maxs[2];plane.z=n->plane->dist;
    plane.movable=1;plane.why=NULL;
    plane_found++;
    return 1;
}

int AW_WaterPlaneMovable(void)
{
    /* the plane belongs to the map loaded now: the same model, its memory, its root still on that plane (between a
     * server spawn and the new map's attach the old pointers name nothing) */
    return plane.movable && aw_water_movable.value && plane.model && plane.model==sv.worldmodel &&
           plane.model->vertexes==plane.vertexes && plane.model->nodes &&
           plane.model->nodes+plane.model->hulls[0].firstclipnode==plane.root && plane.root->plane==plane.plane;
}

float AW_WaterPlaneZ(void)
{
    return plane.z;
}

int AW_WaterPlaneSet(float z)
{
    float old;int i;
    if(!AW_WaterPlaneMovable()){plane_refused++;return 0;}
    if(z<plane.lo+1){z=plane.lo+1;plane_clamped++;}
    else if(z>plane.hi-1){z=plane.hi-1;plane_clamped++;}
    if(z==plane.z)return 1;
    if(!plane.widened){
        /* the two leaves' boxes (the view's culling) the whole room high: a placement linked to either is never
         * culled by the old water line */
        plane.above->minmaxs[2]=plane.below->minmaxs[2]=(short)floor(plane.lo);
        plane.above->minmaxs[5]=plane.below->minmaxs[5]=(short)ceil(plane.hi);
        plane.widened=1;
    }
    old=plane.z;plane.z=z;
    plane.plane->dist=z;
    for(i=0;i<plane.nverts;i++)plane.model->vertexes[plane.verts[i]].position[2]=z;
    plane_moves++;
    if(aw_water_relink)aw_water_relink(old,z);
    return 1;
}

void AW_WaterPlaneStatus(void)
{
    if(plane.movable)
        Con_Printf("water plane: at %.2f (map units; the room box %.1f to %.1f); %lu maps, %lu with a movable plane, "
                   "%lu moves, %lu at the box's edge, %lu refused%s\n",plane.z,plane.lo,plane.hi,plane_maps,plane_found,
                   plane_moves,plane_clamped,plane_refused,aw_water_movable.value?"":" (aw_water_movable 0: kept as built)");
    else
        Con_Printf("water plane: none movable here (%s); %lu maps, %lu with a movable plane, %lu moves, %lu refused\n",
                   plane.why?plane.why:"-",plane_maps,plane_found,plane_moves,plane_refused);
}

static void reset_water_plane(int new_game)
{
    (void)new_game;
    plane_maps=plane_found=plane_moves=plane_clamped=plane_refused=0;
}

void AW_WaterInit(void)
{
    Cvar_RegisterVariable(&aw_water_movable);
    AW_ResetRegister("water plane",reset_water_plane,NULL);
}
