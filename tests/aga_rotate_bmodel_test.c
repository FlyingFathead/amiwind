/* SPDX-License-Identifier: GPL-2.0-or-later
 * R_RotateBmodel fast paths (ENGINE-FPU-UNIMPL-31): all-zero angles give the
 * identity without trigonometry, yaw-only and full rotations match id's
 * original three-matrix product, and the per-entity basis is rebuilt only
 * when the angles change. */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
#include <math.h>

int r_visframecount=1;
vec3_t vpn,vright,vup;
static int frustums;
extern float entity_rotation[3][3];
void Con_Printf(char *fmt,...) {}
void Sys_Error(char *fmt,...) {assert(0);}
int AW_NodeVisible(short *bounds) {return 1;}
void R_RenderBmodelFace(bedge_t *edges,msurface_t *surface) {}
void R_TransformFrustum(void) {frustums++;}

/* id's original R_RotateBmodel matrix, in double precision */
static void reference(const float a[3],double out[3][3])
{
    double y=a[YAW]*M_PI/180,p=a[PITCH]*M_PI/180,r=a[ROLL]*M_PI/180;
    double t1[3][3]={{cos(y),sin(y),0},{-sin(y),cos(y),0},{0,0,1}};
    double t2[3][3]={{cos(p),0,-sin(p)},{0,1,0},{sin(p),0,cos(p)}};
    double t3[3][3]={{1,0,0},{0,cos(r),sin(r)},{0,-sin(r),cos(r)}},m[3][3];
    int i,j,k;
    for(i=0;i<3;i++)for(j=0;j<3;j++){m[i][j]=0;for(k=0;k<3;k++)m[i][j]+=t2[i][k]*t1[k][j];}
    for(i=0;i<3;i++)for(j=0;j<3;j++){out[i][j]=0;for(k=0;k<3;k++)out[i][j]+=t3[i][k]*m[k][j];}
}
static void set_view(void)
{
    modelorg[0]=10;modelorg[1]=-20;modelorg[2]=30;
    vpn[0]=1;vpn[1]=0;vpn[2]=0;vright[0]=0;vright[1]=-1;vright[2]=0;vup[0]=0;vup[1]=0;vup[2]=1;
}
static void check(entity_t *e,float y,float p,float r,double tolerance)
{
    double ref[3][3];int i,j;
    e->angles[YAW]=y;e->angles[PITCH]=p;e->angles[ROLL]=r;
    currententity=e;set_view();R_RotateBmodel();
    reference(e->angles,ref);
    for(i=0;i<3;i++)for(j=0;j<3;j++)assert(fabs(entity_rotation[i][j]-ref[i][j])<=tolerance);
    /* modelorg is rotated by the same matrix */
    assert(fabs(modelorg[0]-(ref[0][0]*10-ref[0][1]*20+ref[0][2]*30))<1e-4);
}
int main(void)
{
    static entity_t a,b;int i,j,before;
    memset(aw_fpucount,0,sizeof aw_fpucount);
    /* zero angles: exact identity, view untouched, no trigonometry */
    currententity=&a;set_view();R_RotateBmodel();
    for(i=0;i<3;i++)for(j=0;j<3;j++)assert(entity_rotation[i][j]==(i==j));
    assert(modelorg[0]==10 && modelorg[1]==-20 && modelorg[2]==30 && vright[1]==-1);
    assert(aw_fpucount[AW_FPU_ROTATE]==1 && aw_fpucount[AW_FPU_ROTATE_TRIG]==0 && frustums==1);
    /* yaw only, then full rotations, against the original product */
    for(i=-720;i<=720;i+=15)check(&a,(float)i+0.25f,0,0,2e-6);
    check(&a,30,10,0,2e-6);check(&a,30,0,-20,2e-6);check(&a,123.5f,-45,77,2e-6);
    check(&a,0,90,0,2e-6);check(&a,0,0,180,2e-6);
    /* cache: same angles again -> no rebuild; another entity -> its own entry */
    check(&a,200,5,6,2e-6);before=aw_fpucount[AW_FPU_ROTATE_TRIG];
    check(&a,200,5,6,2e-6);check(&a,200,5,6,2e-6);
    assert(aw_fpucount[AW_FPU_ROTATE_TRIG]==before);
    check(&b,10,0,0,2e-6);assert(aw_fpucount[AW_FPU_ROTATE_TRIG]==before+1);
    check(&a,200,5,6,2e-6);assert(aw_fpucount[AW_FPU_ROTATE_TRIG]==before+1);
    check(&a,201,5,6,2e-6);assert(aw_fpucount[AW_FPU_ROTATE_TRIG]==before+2);
    return 0;
}
