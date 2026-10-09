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

static void polygon(horizon_vertex_t *v,int n,byte colour,horizon_stats_t *st) {
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
    st->polygons++;
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
        depth=d_pzbuffer+y*d_zwidth;pixels=vid.buffer+y*vid.rowbytes;st->rows++;
        for(ix=x0;ix<x1;ix++,zi+=step){
            /* Every point is beyond the far plane, so this is at most256.
             * A conventional inverse-depth test keeps ALL nearer world/water,
             * and also resolves overlaps between distant LAND polygons. */
            if(!(zi>=0 && zi<=32767))continue;
            zvalue=(int)zi;
            if(depth[ix]==AW_SKY_BACKGROUND_DEPTH || zvalue>depth[ix]){
                depth[ix]=(short)zvalue;pixels[ix]=colour;st->pixels++;
            }
        }
    }
}

/* The viewport, buffers and projection the rasterizer writes through. */
static int view_valid(int distance) {
    return distance>=128 && distance<=4096 &&
       vid.buffer && d_pzbuffer && r_refdef.vrect.x>=0 && r_refdef.vrect.y>=0 &&
       r_refdef.vrect.width>0 && r_refdef.vrect.height>0 &&
       r_refdef.vrect.width<=vid.width-r_refdef.vrect.x &&
       r_refdef.vrect.height<=vid.height-r_refdef.vrect.y &&
       vid.rowbytes>=vid.width && d_zwidth>=vid.width &&
       xscale>0 && xscale<=16384 && yscale>0 && yscale<=16384 &&
       isfinite(xcenter) && isfinite(ycenter);
}

void AW_HorizonDraw(byte colour,int distance) {
    model_t *world=cl.worldmodel;msurface_t *surface;int i,n;float side;
    horizon_vertex_t original[AW_HORIZON_MAX_VERTS],clipped[AW_HORIZON_MAX_VERTS+1];
    memset(&stats,0,sizeof stats);
    if(!world || world->type!=mod_brush || !world->surfaces || !world->vertexes ||
       !world->edges || !world->surfedges || !view_valid(distance) ||
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
        if(n>=3)polygon(clipped,n,colour,&stats);
    }
}

void AW_HorizonReport(void) {
    Con_Printf("LAND horizon: faces %ld/%ld polygons %ld rows %ld pixels %ld rejected %ld limit %ld\n",
        (long)stats.land,(long)stats.examined,(long)stats.polygons,(long)stats.rows,
        (long)stats.pixels,(long)stats.rejected,(long)stats.limited);
}

/* ------------------------------------------------------------ far terrain grid
 * CHIM's resident far terrain (chim/chim_far.c, docs/chim/WORLD_FORMAT.md "Far
 * terrain"): a regular heightfield over the frame and a margin beyond it, drawn
 * with the same clip, scan and inverse-depth test as the LAND faces above, in
 * the same full fog colour, beyond the same fog plane. Only the data differs:
 * the frame world holds the active chunk ring only, so the land beyond it comes
 * from the grid. Blocks of quads are culled whole (all nearer than the fog
 * plane, beyond the reach, or outside one side of the view); a triangle that
 * faces away from the eye is skipped (a heightfield seen from above is closed:
 * a ray meets a facing triangle first). */
typedef struct {long blocks,near,far,side,drawn,triangles,back;} grid_stats_t;
static grid_stats_t grid;
static horizon_stats_t grid_raster;
#define AW_GRID_SIDE (AW_HORIZON_GRID_MAX_BLOCK+1)

static void view_point(float x,float y,float z,horizon_vertex_t *v) {
    float p[3];p[0]=x-r_origin[0];p[1]=y-r_origin[1];p[2]=z-r_origin[2];
    v->x=DotProduct(p,vright);v->y=DotProduct(p,vup);v->z=DotProduct(p,vpn);
}

/* Keep the part of a convex polygon on one side of the view plane z = d. */
static int clip_depth(const horizon_vertex_t *in,int n,horizon_vertex_t *out,float d,int keep_far) {
    int i,j,m=0,inside,next;float f;
    for(i=0;i<n;i++){
        j=(i+1)%n;
        inside=keep_far?in[i].z>=d:in[i].z<=d;next=keep_far?in[j].z>=d:in[j].z<=d;
        if(inside){if(m>=AW_HORIZON_MAX_VERTS)return 0;out[m++]=in[i];}
        if(inside!=next){
            if(m>=AW_HORIZON_MAX_VERTS)return 0;
            f=(d-in[i].z)/(in[j].z-in[i].z);
            out[m].x=in[i].x+(in[j].x-in[i].x)*f;
            out[m].y=in[i].y+(in[j].y-in[i].y)*f;
            out[m++].z=d;
        }
    }
    return m;
}

/* 1 when a box (8 view-space corners) cannot reach the viewport: every corner
 * outside the same side plane through the eye and a viewport edge. */
static int box_outside(const horizon_vertex_t *c) {
    float xl=(r_refdef.vrect.x-xcenter)/xscale,xr=(r_refdef.vrect.x+r_refdef.vrect.width-xcenter)/xscale;
    float yt=(ycenter-r_refdef.vrect.y)/yscale,yb=(ycenter-r_refdef.vrect.y-r_refdef.vrect.height)/yscale;
    int k,l=0,r=0,t=0,b=0;
    for(k=0;k<8;k++){
        if(c[k].x<xl*c[k].z)l++;
        if(c[k].x>xr*c[k].z)r++;
        if(c[k].y>yt*c[k].z)t++;
        if(c[k].y<yb*c[k].z)b++;
    }
    return l==8 || r==8 || t==8 || b==8;
}

static void grid_triangle(const aw_horizon_grid_t *g,const horizon_vertex_t *v,int ia,int ib,int ic,
                          const float *wa,const float *wb,const float *wc,byte colour,float distance) {
    horizon_vertex_t tri[3],a[AW_HORIZON_MAX_VERTS+1],b[AW_HORIZON_MAX_VERTS+1];
    float e1[3],e2[3],n[3],eye[3];int k,m;
    if(v[ia].z<distance && v[ib].z<distance && v[ic].z<distance)return;
    if(g->reach>0 && v[ia].z>g->reach && v[ib].z>g->reach && v[ic].z>g->reach)return;
    grid.triangles++;
    for(k=0;k<3;k++){e1[k]=wb[k]-wa[k];e2[k]=wc[k]-wa[k];eye[k]=wa[k]-r_origin[k];}
    CrossProduct(e1,e2,n);
    if(DotProduct(n,eye)>=0){grid.back++;return;}
    tri[0]=v[ia];tri[1]=v[ib];tri[2]=v[ic];
    m=clip_depth(tri,3,a,distance,1);
    if(m>=3 && g->reach>0)m=clip_depth(a,m,b,g->reach,0);
    else for(k=0;k<m;k++)b[k]=a[k];
    if(m>=3)polygon(b,m,colour,&grid_raster);
}

void AW_HorizonGrid(const aw_horizon_grid_t *g,byte colour,int distance,int cull) {
    static horizon_vertex_t v[AW_GRID_SIDE*AW_GRID_SIDE];
    horizon_vertex_t corner[8];
    int bx,by,bi,bj,i0,j0,i1,j1,i,j,k,w,zmin,zmax,z,a;float wa[3],wb[3],wc[3],wd[3],depth;
    memset(&grid,0,sizeof grid);memset(&grid_raster,0,sizeof grid_raster);
    if(!g || !g->heights || g->nx<2 || g->ny<2 || g->nx>1025 || g->ny>1025 ||
       g->block<1 || g->block>AW_HORIZON_GRID_MAX_BLOCK || !(g->step>0 && g->step<=65536) ||
       !isfinite(g->x0) || !isfinite(g->y0) || fabs(g->x0)>1000000 || fabs(g->y0)>1000000 ||
       !(g->reach>=0 && g->reach<=1000000) || !view_valid(distance))return;
    bx=(g->nx-2)/g->block+1;by=(g->ny-2)/g->block+1;
    for(bj=0;bj<by;bj++)for(bi=0;bi<bx;bi++){
        grid.blocks++;
        i0=bi*g->block;j0=bj*g->block;
        i1=i0+g->block;if(i1>g->nx-1)i1=g->nx-1;
        j1=j0+g->block;if(j1>g->ny-1)j1=g->ny-1;
        if(g->bounds){zmin=g->bounds[2*(bj*bx+bi)];zmax=g->bounds[2*(bj*bx+bi)+1];}
        else{
            zmin=32767;zmax=-32768;
            for(j=j0;j<=j1;j++)for(i=i0;i<=i1;i++){z=g->heights[j*g->nx+i];if(z<zmin)zmin=z;if(z>zmax)zmax=z;}
        }
        if(cull){
            for(k=0;k<8;k++)view_point(g->x0+((k&1)?i1:i0)*g->step,g->y0+((k&2)?j1:j0)*g->step,
                                        (float)((k&4)?zmax:zmin),&corner[k]);
            depth=corner[0].z;for(k=1;k<8;k++)if(corner[k].z>depth)depth=corner[k].z;
            if(depth<distance){grid.near++;continue;}
            if(g->reach>0){
                depth=corner[0].z;for(k=1;k<8;k++)if(corner[k].z<depth)depth=corner[k].z;
                if(depth>g->reach){grid.far++;continue;}
            }
            if(box_outside(corner)){grid.side++;continue;}
        }
        grid.drawn++;
        w=i1-i0+1;
        for(j=j0;j<=j1;j++)for(i=i0;i<=i1;i++)
            view_point(g->x0+i*g->step,g->y0+j*g->step,(float)g->heights[j*g->nx+i],&v[(j-j0)*w+(i-i0)]);
        for(j=j0;j<j1;j++)for(i=i0;i<i1;i++){
            /* Corners 0-1-2 and 0-2-3, counter-clockwise from above, as the converter's tiles. */
            a=(j-j0)*w+(i-i0);
            wa[0]=g->x0+i*g->step;wa[1]=g->y0+j*g->step;wa[2]=g->heights[j*g->nx+i];
            wb[0]=wa[0]+g->step;wb[1]=wa[1];wb[2]=g->heights[j*g->nx+i+1];
            wc[0]=wb[0];wc[1]=wa[1]+g->step;wc[2]=g->heights[(j+1)*g->nx+i+1];
            wd[0]=wa[0];wd[1]=wc[1];wd[2]=g->heights[(j+1)*g->nx+i];
            grid_triangle(g,v,a,a+1,a+w+1,wa,wb,wc,colour,(float)distance);
            grid_triangle(g,v,a,a+w+1,a+w,wa,wc,wd,colour,(float)distance);
        }
    }
}

void AW_HorizonGridCounts(long *out) {
    out[0]=grid.blocks;out[1]=grid.near;out[2]=grid.far;out[3]=grid.side;out[4]=grid.drawn;
    out[5]=grid.triangles;out[6]=grid.back;out[7]=grid_raster.polygons;out[8]=grid_raster.pixels;
}
