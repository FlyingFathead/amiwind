/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_activate.h"   /* AW_MODEL_ONE_STORED_FRAME (FOCUS-NPC-OVERRIDES-ITEM-62) */
#include <assert.h>
server_t sv;
/* string offsets: 1 the class, 8 the name, 17 an outdoor creature's model (FOCUS-NPC-OVERRIDES-ITEM-62) */
char *pr_strings="\0aw_npc\0Resident\0progs/c_guar.mdl";
static edict_t entities[4];static model_t model;
static float wall=1000,floor_z;static int blocked,steep,chim_on;static eval_t mode,valid,baked;
edict_t *EDICT_NUM(int n){assert(n>=0 && n<4);return &entities[n];}
/* CREATURE-FLOATING-62: the actor record's answer (aw_ambient.c sets the hook: a creature that neither flies nor
 * swims), the drop setting */
static int record_walks;extern int (*aw_actor_walks)(edict_t *e);
static int walks(edict_t *e){(void)e;return record_walks;}
/* FOCUS-NPC-OVERRIDES-ITEM-62: the instance scale (aw_scale) when SCALE_ON, the fight's state (2 a body) */
static int scale_on,slot_state;static eval_t scale;
int AW_CombatSlotState(edict_t *x,float *health){(void)x;if(health)*health=0;return slot_state;}
/* aw_ambient.c's answer (its wander slot's creature flag; -1 no slot) */
static int slot_kind=-1;extern int (*aw_actor_creature)(edict_t *e);
static int creature_slot(edict_t *x){(void)x;return slot_kind;}
eval_t *GetEdictFieldValue(edict_t *e,char *name){if(!strcmp(name,"aw_ground_mode"))return &mode;if(!strcmp(name,"aw_ground_valid"))return &valid;if(!strcmp(name,"aw_ground_baked"))return &baked;if(!strcmp(name,"aw_scale"))return scale_on?&scale:NULL;return NULL;}
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
    /* FOCUS-NPC-OVERRIDES-ITEM-62: a skeletal person, the kind the game ships since v0.0.52, holds ONE stored frame
     * whose box encloses every pose (here 60 by 60 by 40, the two frames above together); his animation's frame
     * numbers run past it (frame 0's box). The use is tested against his body: world.qc aw_npc_floor's hull, half
     * widths 7.32 by 7.12 times his scale, never wider than the stored box, its height kept for the head; a body
     * against the stored box lowered to 8 units over its floor. Before, the stored box reached 30 units around him
     * (Aleri Aren 44 units from the door back in the Mournhold Guards' Quarters, Fargoth at the census office door).
     * THE GUARD'S LESSON: the two-frame fixture above passed from v0.0.60-dev3 on while every person the game shipped
     * had one frame; a test fixture is of the kind the game ships. */
    {static const vec3_t hull_lo={-7.32f,-7.12f,0},hull_hi={7.32f,7.12f,33.25f};vec3_t down={30,0,0};
     model.mins[0]=model.mins[1]=-30;model.maxs[0]=model.maxs[1]=30;model.maxs[2]=40;
     VectorCopy(hull_lo,e->v.mins);VectorCopy(hull_hi,e->v.maxs);resident=1;
     /* two frames, the person's hull: the drawn frame's box as before, the lying frame not narrowed */
     e->v.frame=1;e->v.origin[1]=24;assert(AW_NPCTarget(p,down)==e);
     e->v.frame=0;e->v.origin[1]=12;assert(!AW_NPCTarget(p,angles));
     /* ONE frame */
     alias.m.numframes=1;frame_box(&alias.h.frames[0],-30,-30,0,30,30,40);e->v.frame=22;
     e->v.origin[1]=12;assert(!AW_NPCTarget(p,angles));                   /* standing beside the line: missed */
     e->v.origin[1]=0;assert(AW_NPCTarget(p,angles)==e);                  /* on it, at the head above the hull: hit */
     e->v.origin[1]=6;assert(AW_NPCTarget(p,angles)==e);                  /* inside his half width: hit */
     e->v.origin[1]=12;scale_on=1;scale._float=2;
     assert(AW_NPCTarget(p,angles)==e);scale_on=0;                        /* twice his size, 14.24 wide: hit */
     e->v.model=17;assert(AW_NPCTarget(p,angles)==e);e->v.model=0;        /* an outdoor creature: the stored box */
     /* a creature by its wander slot (aw_ambient.c): a room creature (progs/a_*) keeps the stored box; the slot's
      * word wins over the model's name; no slot: the name decides */
     aw_actor_creature=creature_slot;slot_kind=1;assert(AW_NPCTarget(p,angles)==e);
     slot_kind=0;e->v.model=17;assert(!AW_NPCTarget(p,angles));
     slot_kind=-1;assert(AW_NPCTarget(p,angles)==e);e->v.model=0;assert(!AW_NPCTarget(p,angles));
     aw_actor_creature=NULL;
     /* evicted: the whole model's bounds, narrowed the same once a resident look has seen the one stored frame (the
      * bit it keeps in model_t flags); never seen resident, as before */
     model.flags=0;resident=0;assert(AW_NPCTarget(p,angles)==e);         /* not known yet: the whole bounds */
     resident=1;assert(!AW_NPCTarget(p,angles) && (model.flags&AW_MODEL_ONE_STORED_FRAME));   /* seen: learnt */
     resident=0;assert(!AW_NPCTarget(p,angles));                          /* evicted: still his body */
     e->v.origin[1]=0;assert(AW_NPCTarget(p,angles)==e);
     resident=1;
     slot_state=2;e->v.origin[1]=0;assert(!AW_NPCTarget(p,angles));      /* a body, level over it: missed */
     assert(AW_NPCTarget(p,down)==e);                                     /* looking down at it: hit */
     e->v.origin[1]=24;assert(AW_NPCTarget(p,down)==e);                   /* across the line: its stored width */
     slot_state=0;
     /* two frames again: a resident look forgets the one-frame bit */
     alias.m.numframes=2;frame_box(&alias.h.frames[0],-4,-4,0,4,4,40);e->v.frame=0;e->v.origin[1]=0;
     assert(AW_NPCTarget(p,angles)==e && !(model.flags&AW_MODEL_ONE_STORED_FRAME));
     VectorCopy(vec3_origin,e->v.mins);VectorCopy(vec3_origin,e->v.maxs);
     resident=0;model.flags=0;
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
    /* CREATURE-FLOATING-62: a walking creature without a baked ground point drops onto the ground under it (OpenMW
     * adjustPosition: up to a cell); an NPC, a flyer, a baked one or aw_actor_drop 0 keep the 32-unit bound */
    e->v.origin[0]=20;floor_z=26;valid._float=0;
    e->v.origin[2]=144;assert(!AW_NPCFloor(e) && e->v.origin[2]==144);                 /* no records: bound */
    aw_actor_walks=walks;record_walks=0;
    assert(!AW_NPCFloor(e) && e->v.origin[2]==144);       /* an NPC, a flyer, or the drop off: bound */
    record_walks=1;assert(AW_NPCFloor(e) && e->v.origin[2]==26.25f);                    /* 118 units down */
    e->v.origin[2]=2100;assert(!AW_NPCFloor(e) && e->v.origin[2]==2100);              /* beyond a cell: stays */
    aw_actor_walks=NULL;record_walks=0;
    return 0;
}
