/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
server_t sv;
char *pr_strings="\0aw_npc\0Resident";
static edict_t entities[4];static model_t model;
static float wall=1000,floor_z;static int blocked,steep,chim_on;static eval_t mode,valid,baked;
edict_t *EDICT_NUM(int n){assert(n>=0 && n<4);return &entities[n];}
eval_t *GetEdictFieldValue(edict_t *e,char *name){if(!strcmp(name,"aw_ground_mode"))return &mode;if(!strcmp(name,"aw_ground_valid"))return &valid;if(!strcmp(name,"aw_ground_baked"))return &baked;return NULL;}
void SV_LinkEdict(edict_t *e,qboolean touch){}
int AW_RegionGroundCoverage(const float *point){return 1;}
int Chim_Active(void){return chim_on;}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int type,edict_t *skip){
    trace_t t;memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
    if(blocked){t.startsolid=t.allsolid=true;t.fraction=0;return t;}
    if(a[2]>b[2] && a[2]>floor_z && b[2]<=floor_z){
        t.fraction=(a[2]-floor_z)/(a[2]-b[2]);t.endpos[2]=floor_z;
        t.plane.normal[2]=steep?.5f:1;return t;
    }
    if(a[0]<wall && b[0]>=wall)t.fraction=(wall-a[0])/(b[0]-a[0]);
    return t;
}
int main(void){
    edict_t *p=&entities[1],*e=&entities[2];vec3_t angles={0,0,0};
    sv.num_edicts=3;sv.models[1]=&model;sv.edicts=entities;
    p->v.movetype=MOVETYPE_WALK;p->v.view_ofs[2]=36;
    e->v.classname=1;e->v.netname=8;e->v.modelindex=1;e->v.origin[0]=20;
    model.type=mod_alias;model.mins[0]=model.mins[1]=-4;model.maxs[0]=model.maxs[1]=4;model.maxs[2]=40;
    /* Crosshair at visible head above the 33.25-unit physical box. */
    assert(AW_NPCTarget(p,angles)==e);
    p->v.origin[0]=18;assert(AW_NPCTarget(p,angles)==e); /* camera inside bounds */
    p->v.origin[0]=0;wall=10;assert(!AW_NPCTarget(p,angles));wall=1000;
    e->v.origin[1]=12;assert(!AW_NPCTarget(p,angles));e->v.origin[1]=0;
    e->v.origin[0]=90;assert(!AW_NPCTarget(p,angles));e->v.origin[0]=20;
    blocked=1;assert(!AW_NPCTarget(p,angles));blocked=0;
    /* distance precheck: a far NPC is skipped before its direction vectors */
    {int before=aw_fpucount[AW_FPU_NPCTEST];e->v.origin[0]=500;assert(!AW_NPCTarget(p,angles));
     assert(aw_fpucount[AW_FPU_NPCTEST]==before);e->v.origin[0]=20;assert(AW_NPCTarget(p,angles)==e);
     assert(aw_fpucount[AW_FPU_NPCTEST]==before+1);}
    floor_z=126;e->v.origin[2]=144;
    assert(AW_NPCFloor(e));assert(fabs(e->v.origin[2]-126.25f)<.001);
    assert(AW_NPCFloor(e));assert(fabs(e->v.origin[2]-126.25f)<.001); /* no drift */
    e->v.origin[2]=170;assert(!AW_NPCFloor(e) && e->v.origin[2]==170);
    e->v.origin[2]=144;mode._float=1;assert(!AW_NPCFloor(e) && e->v.origin[2]==144);mode._float=0;
    steep=1;assert(!AW_NPCFloor(e) && e->v.origin[2]==144);steep=0;
    blocked=1;assert(!AW_NPCFloor(e) && e->v.origin[2]==144);
    /* Preserve mesh-aware baked origin; moved and legacy actors still trace. */
    blocked=0;e->v.origin[2]=125.5f;VectorCopy(e->v.origin,baked.vector);valid._float=1;
    assert(AW_NPCFloor(e) && e->v.origin[2]==125.5f);
    e->v.origin[0]+=1;assert(AW_NPCFloor(e) && e->v.origin[2]==126.25f);
    VectorCopy(e->v.origin,baked.vector);e->v.origin[2]=144;valid._float=0;
    assert(AW_NPCFloor(e) && e->v.origin[2]==126.25f);
    /* COMBAT-CHASE-CHIM-STUCK-46: CHIM streams collision; a miss is retried once a second until the ground is there */
    sv.active=1;sv.time=10;e->v.flags=0;floor_z=-1000;e->v.origin[2]=144;
    assert(!AW_NPCFloor(e) && AW_NPCFloorRetry()==0);                    /* legacy: nothing kept */
    chim_on=1;assert(!AW_NPCFloor(e) && e->v.origin[2]==144);
    assert(AW_NPCFloorRetry()==0 && e->v.origin[2]==144);                /* still no ground */
    floor_z=126;sv.time=10.5;assert(AW_NPCFloorRetry()==0 && e->v.origin[2]==144);   /* not a second yet */
    sv.time=11;assert(AW_NPCFloorRetry()==1 && e->v.origin[2]==126.25f && ((int)e->v.flags&FL_ONGROUND));
    sv.time=12;assert(AW_NPCFloorRetry()==0);                            /* landed: dropped */
    /* an actor that moved, or went, is dropped; steep or out of reach stays where it is */
    floor_z=-1000;e->v.origin[2]=144;assert(!AW_NPCFloor(e));e->v.origin[0]+=5;floor_z=126;
    sv.time=13;assert(AW_NPCFloorRetry()==0 && e->v.origin[2]==144);
    sv.time=14;assert(AW_NPCFloorRetry()==0 && e->v.origin[2]==144);
    floor_z=-1000;assert(!AW_NPCFloor(e));e->free=true;floor_z=126;sv.time=15;assert(AW_NPCFloorRetry()==0 && e->v.origin[2]==144);
    e->free=false;chim_on=0;
    return 0;
}
