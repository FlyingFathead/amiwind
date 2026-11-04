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
/* CORPSE-INVENTORY-NOT-OPENABLE-59: a resident model with two frames, standing (8 wide, 40 high) and lying (60 long,
 * 8 high); the whole-model bounds enclose both. Cache_Check gives it while resident (never loads). */
static struct {aliashdr_t h;maliasframedesc_t lying;mdl_t m;} alias;static int resident;
void *Cache_Check(cache_user_t *c){(void)c;return resident?&alias:NULL;}
static void frame_box(maliasframedesc_t *f,int x0,int y0,int z0,int x1,int y1,int z1){
    f->bboxmin.v[0]=(byte)(x0+128);f->bboxmin.v[1]=(byte)(y0+128);f->bboxmin.v[2]=(byte)z0;
    f->bboxmax.v[0]=(byte)(x1+128);f->bboxmax.v[1]=(byte)(y1+128);f->bboxmax.v[2]=(byte)z1;
}
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
    /* the drawn frame's box, not the whole model's (CORPSE-INVENTORY-NOT-OPENABLE-59) */
    {int k;
     alias.h.model=(int)((byte *)&alias.m-(byte *)&alias);alias.m.numframes=2;
     for(k=0;k<3;k++){alias.m.scale[k]=1;alias.m.scale_origin[k]=k<2?-128:0;}
     frame_box(&alias.h.frames[0],-4,-4,0,4,4,40);frame_box(&alias.lying,-30,-30,0,30,30,8);
     model.mins[0]=model.mins[1]=-30;model.maxs[0]=model.maxs[1]=30;model.maxs[2]=40;
     e->v.origin[1]=12;resident=0;assert(AW_NPCTarget(p,angles)==e);   /* evicted: the whole model's bounds */
     resident=1;e->v.frame=0;assert(!AW_NPCTarget(p,angles));            /* standing beside the line: missed */
     e->v.origin[1]=0;assert(AW_NPCTarget(p,angles)==e);                  /* standing on it: hit */
     e->v.frame=1;assert(!AW_NPCTarget(p,angles));                        /* lying below the eye: missed */
     {vec3_t down={30,0,0};assert(AW_NPCTarget(p,down)==e);}             /* looking down at the body: hit */
     e->v.frame=7;e->v.origin[1]=12;assert(!AW_NPCTarget(p,angles));      /* a frame out of range: frame 0 */
     e->v.frame=0;e->v.origin[1]=0;resident=0;
     model.mins[0]=model.mins[1]=-4;model.maxs[0]=model.maxs[1]=4;}
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
