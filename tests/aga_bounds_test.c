/* SPDX-License-Identifier: GPL-2.0-or-later
 * World bounds rules (aw_bounds_rules.c) against the reference in
 * tools/world_bounds.py: tests/test_world_bounds.py passes the cell set and
 * the reference answers as arguments. Arguments: N, then N cells "x y", then
 * groups of 13 numbers: x y waterlevel vx vy | active depth nx ny vx' vy' dx dy. */
#include "quakedef.h"
#include "aw_bounds.h"
#include <assert.h>
#include <stdlib.h>

static void near(double a,double b,const char *what,int group)
{
    if(fabs(a-b)>0.05+fabs(b)*1e-4){printf("group %d: %s %f, reference %f\n",group,what,a,b);exit(1);}
}
int main(int argc,char **argv)
{
    int n,i,at=1,group=0,box[4];float centres[2*256];
    float big[4]={0,0,AW_BOUNDS_CELL*(AW_BOUNDS_GRID+5),0};
    /* A table too big for the grid is refused, never clipped. */
    assert(!AW_BoundsBuild(big,2) && !AW_BoundsReady());
    assert(!AW_BoundsBuild(NULL,0));
    n=atoi(argv[at++]);assert(n>0 && n<=256);
    for(i=0;i<n;i++){
        centres[i*2]=(atoi(argv[at])+.5f)*AW_BOUNDS_CELL;centres[i*2+1]=(atoi(argv[at+1])+.5f)*AW_BOUNDS_CELL;at+=2;
    }
    assert(AW_BoundsBuild(centres,n) && AW_BoundsReady());
    assert(AW_BoundsCells(box)==n);
    for(;at+13<=argc;at+=13,group++){
        float p[2],v[3],d[3],depth=0,normal[2]={0,0};int active,want=atoi(argv[at+5]);
        p[0]=(float)atof(argv[at]);p[1]=(float)atof(argv[at+1]);
        v[0]=(float)atof(argv[at+3]);v[1]=(float)atof(argv[at+4]);v[2]=0;
        active=AW_BoundsField(p,&depth,normal);
        if(active!=(want!=0)){printf("group %d: field %d, reference %d\n",group,active,want);return 1;}
        if(active){
            near(depth,atof(argv[at+6]),"depth",group);
            near(normal[0],atof(argv[at+7]),"nx",group);near(normal[1],atof(argv[at+8]),"ny",group);
        }
        AW_BoundsPush(p,v,atoi(argv[at+2]),d);
        near(v[0],atof(argv[at+9]),"vx",group);near(v[1],atof(argv[at+10]),"vy",group);
        near(d[0],atof(argv[at+11]),"drift x",group);near(d[1],atof(argv[at+12]),"drift y",group);
        assert(d[2]==0);
    }
    assert(at==argc && group>0);
    AW_BoundsReset();assert(!AW_BoundsReady() && !AW_BoundsCells(box));
    printf("%d points match the reference\n",group);
    return 0;
}
