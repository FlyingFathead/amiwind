/* SPDX-License-Identifier: GPL-2.0-or-later
 * Distant resident LAND, without texture/light/edge-cache work. The ordinary
 * renderer stops at the fog plane; sky is not a substitute for opaque ground
 * beyond it. Rasterize the actual retained LAND polygons in the fully fogged
 * colour. Do not invent a skyline from trees, roofs or a screen-space envelope.
 */
#include "quakedef.h"
#include "aw_horizon.h"
#include "aw_sky.h"

#define AW_HORIZON_MAX_FACES 8192
#define AW_HORIZON_MAX_VERTS 64
typedef struct {float x,y,z;} horizon_vertex_t;
typedef struct {int examined,land,polygons,rows,pixels,rejected,limited;} horizon_stats_t;
static horizon_stats_t stats;
extern short *d_pzbuffer;
extern unsigned int d_zwidth;
extern float xcenter,ycenter,xscale,yscale;

static int land_surface(const msurface_t *s) {
    const char *name;int i;
    if(!s->plane || !s->texinfo || !s->texinfo->texture ||
       (s->flags&(SURF_DRAWSKY|SURF_DRAWTURB|SURF_DRAWBACKGROUND)))return 0;
    /* g<decimal material id> is the converter's LAND material namespace.
     * Upward normals exclude original brush bottoms and vertical closures. */
    if(!isfinite(s->plane->normal[2]) ||
       s->plane->normal[2]*((s->flags&SURF_PLANEBACK)?-1:1)<=.001f)return 0;
    name=s->texinfo->texture->name;
    if(name[0]!='g' || name[1]<'0' || name[1]>'9')return 0;
    for(i=2;i<16;i++){
        if(!name[i])return 1;
        if(name[i]<'0' || name[i]>'9')return 0;
    }
    return 0;
}

static int transform(const model_t *world,const msurface_t *s,horizon_vertex_t *v) {
    int i,k,e,index;float p[3];const float *src;
    if(s->numedges<3 || s->numedges>AW_HORIZON_MAX_VERTS ||
       s->firstedge<0 || s->firstedge>world->numsurfedges-s->numedges)return 0;
    for(i=0;i<s->numedges;i++){
        e=world->surfedges[s->firstedge+i];
        if(e<=-world->numedges || e>=world->numedges)return 0;
        index=world->edges[e<0?-e:e].v[e<0?1:0];
        if(index>=world->numvertexes)return 0;
        src=world->vertexes[index].position;
        for(k=0;k<3;k++){
            if(!isfinite(src[k]) || fabs(src[k])>1000000)return 0;
            p[k]=src[k]-r_origin[k];
        }
        v[i].x=DotProduct(p,vright);v[i].y=DotProduct(p,vup);v[i].z=DotProduct(p,vpn);
        if(!isfinite(v[i].x) || !isfinite(v[i].y) || !isfinite(v[i].z))return 0;
    }
    return s->numedges;
}

static int clip_far(const horizon_vertex_t *in,int n,horizon_vertex_t *out,float distance) {
    int i,j,m=0,inside,next;float f;
    for(i=0;i<n;i++){
        j=(i+1)%n;inside=in[i].z>=distance;next=in[j].z>=distance;
        if(inside){if(m>=AW_HORIZON_MAX_VERTS+1)return 0;out[m++]=in[i];}
        if(inside!=next){
            if(m>=AW_HORIZON_MAX_VERTS+1)return 0;
            f=(distance-in[i].z)/(in[j].z-in[i].z);
            out[m].x=in[i].x+(in[j].x-in[i].x)*f;
            out[m].y=in[i].y+(in[j].y-in[i].y)*f;
            out[m++].z=distance;
        }
    }
    return m;
}

static void polygon(horizon_vertex_t *v,int n,byte colour) {
    float low=1e30f,high=-1e30f,left,right,leftzi,rightzi,f,x,zi,step,scan;
    int i,j,y,first,last,x0,x1,ix,zvalue;short *depth;byte *pixels;
    int xmin=r_refdef.vrect.x,xmax=xmin+r_refdef.vrect.width;
    int ymin=r_refdef.vrect.y,ymax=ymin+r_refdef.vrect.height;
    for(i=0;i<n;i++){
        v[i].z=1.0f/v[i].z;
        v[i].x=xcenter+v[i].x*xscale*v[i].z;
        v[i].y=ycenter-v[i].y*yscale*v[i].z;
        if(!isfinite(v[i].x) || !isfinite(v[i].y))return;
        if(v[i].y<low)low=v[i].y;
        if(v[i].y>high)high=v[i].y;
    }
    /* Clamp in floating point before converting: clipped, extreme projections
     * must never overflow integer coordinates or escape the active viewport. */
    if(low<ymin)low=ymin;
    if(high>ymax)high=ymax;
    if(low>=high)return;
    /* Match R_EmitEdge/D_DrawZSpans: integer pixel samples, with the half-pixel
     * viewport bias already included in the renderer's xcenter/ycenter. */
    first=(int)ceil(low);last=(int)ceil(high);
    stats.polygons++;
    for(y=first;y<last;y++){
        left=1e30f;right=-1e30f;leftzi=rightzi=0;scan=(float)y;
        for(i=0;i<n;i++){
            j=(i+1)%n;
            if(!((v[i].y<=scan && scan<v[j].y)||(v[j].y<=scan && scan<v[i].y)))continue;
            f=(scan-v[i].y)/(v[j].y-v[i].y);
            x=v[i].x+(v[j].x-v[i].x)*f;zi=v[i].z+(v[j].z-v[i].z)*f;
            if(x<left){left=x;leftzi=zi;}if(x>right){right=x;rightzi=zi;}
        }
        if(left>=right || right<=xmin || left>=xmax)continue;
        step=(rightzi-leftzi)/(right-left);
        x0=left<xmin?xmin:(int)ceil(left);
        x1=right>xmax?xmax:(int)ceil(right);
        zi=(leftzi+(x0-left)*step)*32768.0f;step*=32768.0f;
        depth=d_pzbuffer+y*d_zwidth;pixels=vid.buffer+y*vid.rowbytes;stats.rows++;
        for(ix=x0;ix<x1;ix++,zi+=step){
            /* Every point is beyond the far plane, so this is at most256.
             * A conventional inverse-depth test keeps ALL nearer world/water,
             * and also resolves overlaps between distant LAND polygons. */
            if(!(zi>=0 && zi<=32767))continue;
            zvalue=(int)zi;
            if(depth[ix]==AW_SKY_BACKGROUND_DEPTH || zvalue>depth[ix]){
                depth[ix]=(short)zvalue;pixels[ix]=colour;stats.pixels++;
            }
        }
    }
}

void AW_HorizonDraw(byte colour,int distance) {
    model_t *world=cl.worldmodel;msurface_t *surface;int i,n;float side;
    horizon_vertex_t original[AW_HORIZON_MAX_VERTS],clipped[AW_HORIZON_MAX_VERTS+1];
    memset(&stats,0,sizeof stats);
    if(!world || world->type!=mod_brush || !world->surfaces || !world->vertexes ||
       !world->edges || !world->surfedges || distance<128 || distance>4096 ||
       !vid.buffer || !d_pzbuffer || r_refdef.vrect.x<0 || r_refdef.vrect.y<0 ||
       r_refdef.vrect.width<=0 || r_refdef.vrect.height<=0 ||
       r_refdef.vrect.width>vid.width-r_refdef.vrect.x ||
       r_refdef.vrect.height>vid.height-r_refdef.vrect.y ||
       vid.rowbytes<vid.width || d_zwidth<vid.width ||
       !(xscale>0 && xscale<=16384 && yscale>0 && yscale<=16384) ||
       !isfinite(xcenter) || !isfinite(ycenter) ||
       world->numvertexes<=0 || world->numedges<=0 || world->numsurfedges<0 ||
       world->numsurfaces<0 || world->firstmodelsurface<0 ||
       world->firstmodelsurface>world->numsurfaces || world->nummodelsurfaces<0 ||
       world->nummodelsurfaces>world->numsurfaces-world->firstmodelsurface)return;
    if(world->nummodelsurfaces>AW_HORIZON_MAX_FACES){stats.limited=1;return;}
    surface=world->surfaces+world->firstmodelsurface;
    for(i=0;i<world->nummodelsurfaces;i++,surface++){
        stats.examined++;
        if(!land_surface(surface))continue;
        stats.land++;
        side=DotProduct(r_origin,surface->plane->normal)-surface->plane->dist;
        if((surface->flags&SURF_PLANEBACK)?side>=-.01f:side<=.01f)continue;
        n=transform(world,surface,original);
        if(!n){stats.rejected++;continue;}
        n=clip_far(original,n,clipped,(float)distance);
        if(n>=3)polygon(clipped,n,colour);
    }
}

void AW_HorizonReport(void) {
    Con_Printf("LAND horizon: faces %ld/%ld polygons %ld rows %ld pixels %ld rejected %ld limit %ld\n",
        (long)stats.land,(long)stats.examined,(long)stats.polygons,(long)stats.rows,
        (long)stats.pixels,(long)stats.rejected,(long)stats.limited);
}
