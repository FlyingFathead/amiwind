/* SPDX-License-Identifier: GPL-2.0-or-later
 * Authored collision-only boxes, including full pitch/roll/yaw. Bounded storage
 * outlives a scene; no scene or hunk pointers are retained. */
#include "quakedef.h"
#include "aw_story.h"
#define AW_BARRIERS 32
typedef struct {vec3_t centre,axis[3],half;} aw_barrier_t;
static aw_barrier_t boxes[AW_BARRIERS];
static int count;
/* OPENING-SHIP-BLOCKER-NOT-CONVERTED-63 (v0.0.63): the prison ship's own blocker (intro/barriers-ship.awb, the same
 * format, the ship map's units), CharGenDisable's one placement inside the ship */
static aw_barrier_t ship_boxes[AW_BARRIERS];
static int ship_count;
/* OPENING-BARRIERS-PER-BOX-68 / INVISIBLE-WALLS-NOT-BUILT-68 (v0.0.68): every box of the game a script can switch, and the
 * collision markers outside the opening (id1/world-barriers.txt, tools/world_barriers.py collision_boxes, written by
 * the image step). Each box is on while the world change list has no DISABLED (or TAKEN) row of its reference: what a
 * script's Disable writes for any placement, saved with the game and cleared by New Game; no state of its own. The
 * bits are read again once a server frame (AW_ObjectDisabled, a binary search a box). A box without a reference
 * (an image without the file) is always on, so the opening's boxes clip exactly as before while no script touches
 * one; they keep the story's gate (AW_StoryRestricted) besides. Resident: the references (4 bytes a box), the world
 * boxes of the file (up to AW_WORLD_BOXES rows of 64 bytes) and the loaded map's selection. */
#define AW_WORLD_BOXES 16          /* the three game files hold 7 (2026-11-21); a row past it is not read */
static uint32_t box_ref[AW_BARRIERS],ship_ref[AW_BARRIERS];static int box_refs,ship_refs;
static unsigned long box_on=~0UL,ship_on=~0UL,world_on;       /* a bit a box: 1 on */
typedef struct {uint32_t ref;vec3_t centre,axis[3],half;} world_row_t;   /* the original's units */
static world_row_t world_rows[AW_WORLD_BOXES];static int world_rows_n;
static aw_barrier_t world_boxes[AW_WORLD_BOXES];static uint32_t world_ref[AW_WORLD_BOXES];static int world_n;
static double world_touched[AW_WORLD_BOXES];                  /* sv.time the player last met the box */
static char world_map[64];static double world_selected=-1,bits_time=-1;
int AW_ObjectDisabled(unsigned int reference);   /* aw_mwhost.c */
int AW_SourceToWorld(const char *,const float *,float *);   /* aw_world.c */

static float read_float(const byte *p)
{
    float f;
    memcpy(&f,p,4);
    return LittleFloat(f);
}

int AW_BarrierDecode(const byte *raw,int size)
{
    int n,i,j,k,at=6;
    aw_barrier_t b;
    count=0;
    if(size<6 || memcmp(raw,"AWB1",4))return 0;
    n=raw[4]+(raw[5]<<8);
    if(n<1 || n>AW_BARRIERS || size!=6+n*60)return 0;
    for(i=0;i<n;i++){
        for(j=0;j<3;j++,at+=4){
            b.centre[j]=read_float(raw+at);
            if(!(fabs(b.centre[j])<32768))return 0;
        }
        for(j=0;j<3;j++)for(k=0;k<3;k++,at+=4){
            b.axis[j][k]=read_float(raw+at);
            if(!(fabs(b.axis[j][k])<=1.001))return 0;
        }
        for(j=0;j<3;j++,at+=4){
            b.half[j]=read_float(raw+at);
            if(!(b.half[j]>.01 && b.half[j]<1024))return 0;
            if(fabs(DotProduct(b.axis[j],b.axis[j])-1)>.001)return 0;
            for(k=0;k<j;k++)if(fabs(DotProduct(b.axis[j],b.axis[k]))>.001)return 0;
        }
        boxes[i]=b;
    }
    count=n;
    return 1;
}

static int load_file(const char *name,byte *raw,int capacity)
{
    FILE *f=NULL;int size=COM_FOpenFile((char *)name,&f);
    if(!f)return -1;
    if(size<6 || size>capacity || fread(raw,1,size,f)!=(size_t)size){fclose(f);return -1;}
    fclose(f);
    return size;
}
int AW_BarrierLoad(void)
{
    byte raw[6+AW_BARRIERS*60];
    int size,ok;
    count=ship_count=0;
    /* the ship's first: AW_BarrierDecode fills the dock's set, so the ship's is decoded there and moved */
    if((size=load_file("intro/barriers-ship.awb",raw,(int)sizeof(raw)))>0 && AW_BarrierDecode(raw,size)){
        memcpy(ship_boxes,boxes,sizeof(boxes));ship_count=count;count=0;
    }
    if((size=load_file("intro/barriers.awb",raw,(int)sizeof(raw)))<0)return 0;
    ok=AW_BarrierDecode(raw,size);
    return ok;
}

/* id1/world-barriers.txt (tools/world_barriers.py world_barriers_text): "AWWB1", "opening N REF..." (intro/barriers.awb's
 * rows), "ship N REF..." (barriers-ship.awb's), then "box KEY CX CY CZ" + the three axes + "HX HY HZ" in the original's
 * units. Read once, at the first server spawn; a line that does not parse, or counts that are not the AWB1 tables',
 * leaves those references out (the boxes then stay on, as before). */
/* a line "WORD N REF...": its references into REFS, their number (0: not this word, or a reference that is not one) */
static int read_refs(char *line,const char *word,uint32_t *refs){
    char *p=line;int n,i;long v;
    if(strncmp(p,word,strlen(word)))return 0;
    p+=strlen(word);n=(int)strtol(p,&p,10);
    if(n<1 || n>AW_BARRIERS)return 0;
    for(i=0;i<n;i++){v=strtol(p,&p,10);if(v<=0)return 0;refs[i]=(uint32_t)v;}
    return n;
}
static void world_read_file(void){
    FILE *f=NULL;static char line[300];int j;world_row_t r;float v[15];long key;
    world_rows_n=box_refs=ship_refs=0;
    if(COM_FOpenFile("world-barriers.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWWB1",5)){fclose(f);return;}
    while(fgets(line,sizeof(line),f)){
        if(!strncmp(line,"opening ",8)){box_refs=read_refs(line,"opening",box_ref);continue;}
        if(!strncmp(line,"ship ",5)){ship_refs=read_refs(line,"ship",ship_ref);continue;}
        if(strncmp(line,"box ",4) || world_rows_n>=AW_WORLD_BOXES)continue;
        if(Q_sscanf(line+4,"%ld %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f",&key,&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],
                    &v[6],&v[7],&v[8],&v[9],&v[10],&v[11],&v[12],&v[13],&v[14])!=16 || key<=0)continue;
        r.ref=(uint32_t)key;
        for(j=0;j<3;j++){r.centre[j]=v[j];r.half[j]=v[12+j];r.axis[0][j]=v[3+j];r.axis[1][j]=v[6+j];r.axis[2][j]=v[9+j];}
        for(j=0;j<3;j++)if(!(fabs(r.centre[j])<1e7) || !(r.half[j]>.01f && r.half[j]<16384))break;
        if(j==3)world_rows[world_rows_n++]=r;
    }
    fclose(f);
}
/* sv_main.c SV_SpawnServer: a new server; the file read again (a few hundred bytes, one open a map change) and the
 * selection made again on the new map */
void AW_BarrierServerReset(void);
void AW_BarrierServerReset(void){
    world_read_file();
    world_selected=-1;bits_time=-1;world_n=0;world_map[0]=0;
}
/* the world boxes of the loaded map: each row's centre through the map's own transform (AW_SourceToWorld: a region
 * map's or the loaded CHIM frame's; a presented district's boxes are at its moved place already), the half sizes and
 * the axes as the opening's (a quarter of the original's units). Made again once a second (a frame window that moved) */
static void world_select(void){
    int i,j;float local[3];aw_barrier_t b;
    world_n=0;Q_strcpy_bounded(world_map,sv.name,sizeof(world_map));world_selected=sv.time;
    for(i=0;i<world_rows_n;i++){
        if(!AW_SourceToWorld(sv.name,world_rows[i].centre,local))continue;
        VectorCopy(local,b.centre);
        for(j=0;j<3;j++){VectorCopy(world_rows[i].axis[j],b.axis[j]);b.half[j]=world_rows[i].half[j]*.25f;}
        world_ref[world_n]=world_rows[i].ref;world_touched[world_n]=-1;world_boxes[world_n++]=b;
    }
}
static unsigned long bits(const uint32_t *refs,int n){
    unsigned long on=0;int i;
    for(i=0;i<n;i++)if(!refs[i] || !AW_ObjectDisabled(refs[i]))on|=1UL<<i;
    return on;
}
static void refresh(void){
    if(sv.time==bits_time)return;
    bits_time=sv.time;
    if(strcmp(world_map,sv.name) || sv.time<world_selected || sv.time-world_selected>1)world_select();
    /* the opening's references only when the file names as many as the AWB1 tables hold, row for row; else on */
    box_on=box_refs==count?bits(box_ref,count):~0UL;
    ship_on=ship_refs==ship_count?bits(ship_ref,ship_count):~0UL;
    world_on=bits(world_ref,world_n);
}
/* GetCollidingPC of a box (aw_mwhost.c): 1 while the player met the box with REFERENCE in the last tenth of a second */
int AW_BarrierTouching(unsigned int reference);
int AW_BarrierTouching(unsigned int reference){
    int i;
    for(i=0;i<world_n;i++)
        if(world_ref[i]==reference && world_touched[i]>=0 && sv.time-world_touched[i]<=.1f)return 1;
    return 0;
}

/* Swept separating-axis test for an AABB and an OBB. The 15 axes include the
 * edge cross-products; the six face axes alone miss corner separations. */
static void sweep(aw_barrier_t *b,vec3_t start,vec3_t mins,vec3_t maxs,
                  vec3_t end,trace_t *trace)
{
    vec3_t axes[15],offset,half,velocity,normal;
    float r,p,v,a,z,enter=-1e30f,leave=1e30f,length,hit,closing=1;
    int i,j,k,inside=1,ends_inside=1;
    memset(axes,0,sizeof(axes));VectorCopy(vec3_origin,normal);
    for(i=0;i<3;i++){
        axes[i][i]=1;VectorCopy(b->axis[i],axes[3+i]);
        offset[i]=start[i]+(mins[i]+maxs[i])*.5f-b->centre[i];
        half[i]=(maxs[i]-mins[i])*.5f;velocity[i]=end[i]-start[i];
    }
    for(i=0;i<3;i++)for(j=0;j<3;j++)CrossProduct(axes[i],b->axis[j],axes[6+i*3+j]);
    for(i=0;i<15;i++){
        /* Engine Length uses an approximate reciprocal square root. Collision
         * plane normals must be unit length for sliding response. */
        length=(float)sqrt(DotProduct(axes[i],axes[i]));if(length<.0001f)continue;
        VectorScale(axes[i],1/length,axes[i]);
        r=0;
        for(j=0;j<3;j++)r+=half[j]*fabs(axes[i][j])+b->half[j]*fabs(DotProduct(axes[i],b->axis[j]));
        p=DotProduct(offset,axes[i]);v=DotProduct(velocity,axes[i]);
        if(p<=-r || p>=r)inside=0;
        if(p+v<=-r || p+v>=r)ends_inside=0;
        if(fabs(v)<.000001f){if(p<=-r || p>=r)return;continue;}
        a=(-r-p)/v;z=(r-p)/v;
        if(a>z){hit=a;a=z;z=hit;}
        if(a>enter){
            enter=a;closing=fabs(v);
            for(k=0;k<3;k++)normal[k]=v>0?-axes[i][k]:axes[i][k];
        }
        if(z<leave)leave=z;
        if(enter>leave)return;
    }
    if(inside){
        trace->startsolid=true;
        if(ends_inside){trace->allsolid=true;trace->fraction=0;VectorCopy(start,trace->endpos);trace->ent=sv.edicts;}
        return;
    }
    if(enter<0 || enter>1 || leave<0)return;
    hit=enter-.03125f/closing;if(hit<0)hit=0;
    if(hit>=trace->fraction)return;
    trace->fraction=hit;trace->ent=sv.edicts;
    VectorCopy(normal,trace->plane.normal);
    for(i=0;i<3;i++)trace->endpos[i]=start[i]+hit*velocity[i];
    trace->plane.dist=DotProduct(normal,trace->endpos);
}

/* The source boxes surround the ship/plank but stop before the long pier.
 * Complete the two side edges and shore end during the dock stage. Bounds
 * follow the placed dock tiles; only the player is constrained, never the guard.
 * The ship end stays open where it overlaps the authored plank enclosure. */
static void pier_clip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *trace)
{
    aw_barrier_t b;int side;
    const float ux=.8414506f,uy=-.5403344f;
    if(aw_story.ship_disabled || aw_story.stage>AW_STAGE_OFFICE)return;
    memset(&b,0,sizeof(b));
    b.axis[0][0]=ux;b.axis[0][1]=uy;
    b.axis[1][0]=-uy;b.axis[1][1]=ux;b.axis[2][2]=1;
    b.half[0]=200;b.half[1]=1;b.half[2]=1023;
    for(side=-1;side<=1;side+=2){
        b.centre[0]=306+ux*200-uy*side*31;
        b.centre[1]=-185+uy*200+ux*side*31;
        sweep(&b,start,mins,maxs,end,trace);
    }
    /* Close the shore end within interaction distance of the real office door. */
    b.half[0]=1;b.half[1]=32;b.centre[0]=306;b.centre[1]=-185;
    sweep(&b,start,mins,maxs,end,trace);
}

/* the world boxes of this map for the player, walking or levitating: each one on, swept as the opening's; a box
 * that stops the move or holds the player is marked met for GetCollidingPC */
static void world_clip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *trace){
    int i;float before;qboolean was;
    for(i=0;i<world_n;i++){
        if(!(world_on>>i&1))continue;
        before=trace->fraction;was=trace->startsolid;
        sweep(&world_boxes[i],start,mins,maxs,end,trace);
        if(trace->fraction<before || (trace->startsolid && !was))world_touched[i]=sv.time;
    }
}
void AW_BarrierClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,
                    edict_t *entity,trace_t *trace)
{
    int i;
    if(!svs.clients || entity!=svs.clients[0].edict || maxs[2]-mins[2]<1)return;
    refresh();
    if(world_n && (entity->v.movetype==MOVETYPE_WALK || entity->v.movetype==MOVETYPE_FLY))
        world_clip(start,mins,maxs,end,trace);
    if(!AW_StoryRestricted() || entity->v.movetype!=MOVETYPE_WALK)return;
    /* the ship's blocker on the ship (CharGenDisable keeps it while CharGenState is 0 or over, as the dock's) */
    if(!strcmp(sv.name,"prison")){
        for(i=0;i<ship_count;i++)if(ship_on>>i&1)sweep(&ship_boxes[i],start,mins,maxs,end,trace);
        return;
    }
    if(!count || strcmp(sv.name,"seyda"))return;
    for(i=0;i<count;i++)if(box_on>>i&1)sweep(&boxes[i],start,mins,maxs,end,trace);
    pier_clip(start,mins,maxs,end,trace);
}
/* DROP-REFUSED-CENSUS-ROOM-67 (v0.0.69): the inventory's drop (aw_inventory.c AW_InventoryDropHere) traces points,
 * which AW_BarrierClip above leaves alone (it clips the player's own box), so a drop ahead could lie past a box the
 * player cannot pass. 1 when the segment START..END meets a box that clips the walking player on this map now: the
 * world's boxes and, while the story holds, the opening's (the ship's blocker, the dock's boxes and the pier's sides),
 * the same selection as AW_BarrierClip. It marks no box as met: GetCollidingPC is the player's own touch. */
int AW_BarrierPointBlocked(const float *start,const float *end)
{
    vec3_t a,b,zero;trace_t trace;int i;
    if(!sv.active)return 0;
    refresh();
    VectorCopy(start,a);VectorCopy(end,b);VectorCopy(vec3_origin,zero);
    memset(&trace,0,sizeof(trace));trace.fraction=1;
    for(i=0;i<world_n;i++)if(world_on>>i&1)sweep(&world_boxes[i],a,zero,zero,b,&trace);
    if(AW_StoryRestricted()){
        if(!strcmp(sv.name,"prison")){
            for(i=0;i<ship_count;i++)if(ship_on>>i&1)sweep(&ship_boxes[i],a,zero,zero,b,&trace);
        }else if(count && !strcmp(sv.name,"seyda")){
            for(i=0;i<count;i++)if(box_on>>i&1)sweep(&boxes[i],a,zero,zero,b,&trace);
            pier_clip(a,zero,zero,b,&trace);
        }
    }
    return trace.fraction<1 || trace.startsolid;
}
