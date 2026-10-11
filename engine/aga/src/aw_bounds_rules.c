/* SPDX-License-Identifier: GPL-2.0-or-later
 * World bounds, the rules (docs/WORLD_BOUNDS.md): which cells the open world
 * holds (a bit table from the open-world directory) and the current at a
 * point near its edge. No engine state: the glue is aw_bounds.c. The same
 * rule as tools/world_bounds.py, which the tests compare against. */
#include "quakedef.h"
#include "aw_bounds.h"

static unsigned char grid[AW_BOUNDS_GRID*AW_BOUNDS_GRID/8];
static int gx,gy,gw,gh,ready;   /* the table's first cell and size: the world's box and one free cell round it */
static const int around[8][2]={{1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1}};

static int cell_floor(float v){return (int)floor(v/AW_BOUNDS_CELL);}
static int held(int x,int y)
{
    int i;
    x-=gx;y-=gy;
    if(x<0 || y<0 || x>=gw || y>=gh)return 0;
    i=y*gw+x;return (grid[i>>3]>>(i&7))&1;
}
void AW_BoundsReset(void){ready=0;gw=gh=0;memset(grid,0,sizeof(grid));}
int AW_BoundsReady(void){return ready;}
/* Cells from the map-unit centres of the open-world maps' cores (one per map;
 * a cell split into several maps is set several times). 0: no table. */
int AW_BoundsBuild(const float *centres,int count)
{
    int i,x,y,x0=0,y0=0,x1=0,y1=0;
    AW_BoundsReset();
    if(!centres || count<1)return 0;
    for(i=0;i<count;i++){
        if(!isfinite(centres[i*2]) || !isfinite(centres[i*2+1]) ||
           fabs(centres[i*2])>1000000 || fabs(centres[i*2+1])>1000000)return 0;
        x=cell_floor(centres[i*2]);y=cell_floor(centres[i*2+1]);
        if(!i || x<x0)x0=x;
        if(!i || y<y0)y0=y;
        if(!i || x>x1)x1=x;
        if(!i || y>y1)y1=y;
    }
    if(x1-x0+3>AW_BOUNDS_GRID || y1-y0+3>AW_BOUNDS_GRID)return 0;
    gx=x0-1;gy=y0-1;gw=x1-x0+3;gh=y1-y0+3;
    for(i=0;i<count;i++){
        int k=(cell_floor(centres[i*2+1])-gy)*gw+cell_floor(centres[i*2])-gx;
        grid[k>>3]|=(unsigned char)(1<<(k&7));
    }
    ready=1;return 1;
}
/* box: x0 y0 x1 y1 of the world's cells. Returns the number of cells held. */
int AW_BoundsCells(int *box)
{
    int x,y,n=0;
    if(!ready)return 0;
    for(y=0;y<gh;y++)for(x=0;x<gw;x++)n+=held(gx+x,gy+y);
    if(box){box[0]=gx+1;box[1]=gy+1;box[2]=gx+gw-2;box[3]=gy+gh-2;}
    return n;
}
/* Nearest point of a cell's square to p; returns its distance. */
static float nearest(const float *p,int cx,int cy,float *q)
{
    float lo[2],dx,dy;int k;
    lo[0]=cx*AW_BOUNDS_CELL;lo[1]=cy*AW_BOUNDS_CELL;
    for(k=0;k<2;k++){q[k]=p[k]<lo[k]?lo[k]:p[k]>lo[k]+AW_BOUNDS_CELL?lo[k]+AW_BOUNDS_CELL:p[k];}
    dx=p[0]-q[0];dy=p[1]-q[1];
    return (float)sqrt(dx*dx+dy*dy);
}
/* The signed distance past the world's edge (negative inside its last cell)
 * and the outward unit normal at a map-unit point. 0: nothing to do here
 * (deeper inside than AW_BOUNDS_PRE, or no table). */
int AW_BoundsField(const float *point,float *depth,float *normal)
{
    int cx,cy,i,inside,best=-1;float d,bestd=0,q[2],v[2]={0,0};
    if(!ready || !isfinite(point[0]) || !isfinite(point[1]))return 0;
    cx=cell_floor(point[0]);cy=cell_floor(point[1]);
    inside=held(cx,cy);
    for(i=0;i<8;i++){
        if(held(cx+around[i][0],cy+around[i][1])==inside)continue;
        d=nearest(point,cx+around[i][0],cy+around[i][1],q);
        if(best<0 || d<bestd){
            best=i;bestd=d;
            v[0]=inside?q[0]-point[0]:point[0]-q[0];v[1]=inside?q[1]-point[1]:point[1]-q[1];
        }
    }
    if(best<0){
        int box[4];float c[2],l;
        if(inside)return 0;
        /* Far out (a teleport, debug flight): straight back to the world's middle. */
        AW_BoundsCells(box);
        c[0]=(box[0]+box[2]+1)*AW_BOUNDS_CELL*.5f;c[1]=(box[1]+box[3]+1)*AW_BOUNDS_CELL*.5f;
        normal[0]=point[0]-c[0];normal[1]=point[1]-c[1];
        l=(float)sqrt(normal[0]*normal[0]+normal[1]*normal[1]);
        if(l<=0){normal[0]=1;normal[1]=0;}else{normal[0]/=l;normal[1]/=l;}
        *depth=AW_BOUNDS_HARD+1;return 1;
    }
    if(inside && bestd>=AW_BOUNDS_PRE)return 0;
    if(bestd>1e-3f){normal[0]=v[0]/bestd;normal[1]=v[1]/bestd;}
    else{
        float l=(float)sqrt((float)(around[best][0]*around[best][0]+around[best][1]*around[best][1]));
        normal[0]=(inside?around[best][0]:-around[best][0])/l;normal[1]=(inside?around[best][1]:-around[best][1])/l;
        bestd=0;
    }
    *depth=inside?-bestd:bestd;
    return 1;
}
/* One player step: fade the outward part of velocity (kept), and the drift
 * for this move only (Quake's basevelocity): back in, plus the current along
 * the edge in the water (anticlockwise round the island, scaled by depth as
 * Quake's currents are, sv_phys.c SV_CheckWater). Returns 1 when active. */
int AW_BoundsPush(const float *point,float *velocity,int waterlevel,float *drift)
{
    float depth,n[2],r,out,in,along;
    drift[0]=drift[1]=drift[2]=0;
    if(!AW_BoundsField(point,&depth,n))return 0;
    r=(depth+AW_BOUNDS_PRE)/(AW_BOUNDS_FULL+AW_BOUNDS_PRE);
    if(r<=0)return 0;
    if(r>1)r=1;
    out=velocity[0]*n[0]+velocity[1]*n[1];
    if(out>0){velocity[0]-=n[0]*out*r;velocity[1]-=n[1]*out*r;}
    in=AW_BOUNDS_INWARD*r*(depth>AW_BOUNDS_HARD?4:1);
    if(waterlevel<0)waterlevel=0;
    if(waterlevel>3)waterlevel=3;
    along=AW_BOUNDS_CURRENT*r*waterlevel/3.0f;
    drift[0]=-n[0]*in-n[1]*along;
    drift[1]=-n[1]*in+n[0]*along;
    return 1;
}
