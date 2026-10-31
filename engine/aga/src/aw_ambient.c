/* SPDX-License-Identifier: GPL-2.0-or-later
 * Ambient behaviour: the residents' Wander packages (aw_ambient.h, docs/NPC_PATHFINDING.md; NPC-WANDER-NOT-EXECUTED-35).
 *
 * Rules (OpenMW 0.51 apps/openmw/mwmechanics/aiwander.cpp, our own code): choose an action: an idle by the
 * original's roll (Idle2..Idle9 of the actor's animation table, played once), or with no idle and a distance, walk
 * to a random allowed destination other than the current one along the grid route; with no allowed destination
 * walk now and then (4 % per reaction) to a random spot 0.2..1 x the distance from the start, straight, stopping
 * at an obstacle; arrive within 64 original units; ten failed steps in a row end a walk; a greeting pauses it; an
 * idle actor further than 1.6 x the activation distance (192) from every allowed destination walks back. The
 * reaction (destinations, the manual roll) runs every 0.25 s; the think (steps, frames) every think interval (0.1 s; chim actors ambient think S).
 * Actors further than OpenMW's processing range (7168 original units) from the player do nothing. Combat owns an
 * actor while it fights (AW_CombatSlotState): this module yields and resumes at the choice after.
 * Levelled creatures (v0.0.57): the creature a levelled reference gave runs its own record's Wander package on the
 * reference's compiled routes (find_actor). Creatures this module moves also check aggro on sight (aggro below).
 * Memory: only the first key of every 32 rows and the idle profiles stay resident; a lookup reads one block of rows.
 * Flyers (v0.0.57) fly straight to their destinations off the ground (fly below).
 * Not done (said in docs/NPC_PATHFINDING.md): door proximity, occupied destinations, swimmers (stand), the
 * package is not saved (an actor starts again from its spawn), packages other than Wander.
 */
#include <string.h>
#include "aw_ambient.h"

static unsigned long rd32(const unsigned char *p) {return (unsigned long)p[0]<<24|(unsigned long)p[1]<<16|(unsigned long)p[2]<<8|p[3];}
static unsigned rd16(const unsigned char *p) {return (unsigned)p[0]<<8|p[1];}
static int sx16(unsigned v) {return v&0x8000u?(int)v-0x10000:(int)v;}

long AW_AmbientRowsSize(const unsigned char *h,long file_size) {
    unsigned long rows;
    if(memcmp(h,"AWAM",4) || rd16(h+4)!=1 || rd16(h+6)!=AW_AMBIENT_ROW)return -1;
    rows=rd32(h+8);
    if(rows>(unsigned long)(file_size/AW_AMBIENT_ROW))return -1;
    return AW_AMBIENT_HEADER+(long)rows*AW_AMBIENT_ROW;
}
long AW_AmbientProfilesSize(const aw_ambient_table_t *t) {return t->profiles*AW_AMBIENT_PROFILE;}

int AW_AmbientHeader(aw_ambient_table_t *t,const unsigned char *d,long file_size) {
    unsigned long points,hops,prof;long size;
    memset(t,0,sizeof(*t));
    if((size=AW_AmbientRowsSize(d,file_size))<0)return 0;
    t->rows=(long)rd32(d+8);points=rd32(d+12);hops=rd32(d+16);prof=rd32(d+20);
    t->multiplier=rd16(d+24);
    if(points>(unsigned long)(file_size/AW_AMBIENT_POINT) || hops>(unsigned long)file_size ||
       prof>(unsigned long)(file_size/AW_AMBIENT_PROFILE))return 0;
    t->points=(long)points;t->hop_bytes=(long)hops;t->profiles=(long)prof;
    t->points_at=size;t->hops_at=t->points_at+t->points*AW_AMBIENT_POINT;t->profiles_at=t->hops_at+t->hop_bytes;
    return t->profiles_at+t->profiles*AW_AMBIENT_PROFILE==file_size;
}
int AW_AmbientRowValid(const aw_ambient_table_t *t,const aw_ambient_row_t *r,const aw_ambient_row_t *prev) {
    if(!r->points || !r->destinations || r->destinations>r->points || r->destinations>AW_AMBIENT_MAX_DEST)return 0;
    if(r->first_point+r->points>(unsigned long)t->points)return 0;
    if(r->first_hop+(unsigned long)r->points*r->destinations>(unsigned long)t->hop_bytes)return 0;
    if((long)r->profile>=t->profiles)return 0;
    if(prev && (prev->ref>r->ref || (prev->ref==r->ref && prev->hash>=r->hash)))return 0;
    return 1;
}
int AW_AmbientOpen(aw_ambient_table_t *t,const unsigned char *d,long size,const unsigned char *profiles,long file_size) {
    long i;aw_ambient_row_t r,q;
    if(size<AW_AMBIENT_HEADER || AW_AmbientRowsSize(d,file_size)!=size || !AW_AmbientHeader(t,d,file_size))return 0;
    t->rows_data=d+AW_AMBIENT_HEADER;t->profile_data=profiles;
    for(i=0;i<t->rows;i++){
        AW_AmbientRow(t,i,&r);
        if(!AW_AmbientRowValid(t,&r,i?&q:NULL))return 0;
        q=r;
    }
    return 1;
}
void AW_AmbientLevelled(aw_ambient_row_t *routes,const aw_ambient_row_t *package) {
    /* the routes row keeps its reference, points and hops; the creature's package gives the rest */
    routes->distance=package->distance<routes->distance?package->distance:routes->distance;
    routes->duration=package->duration;routes->hour=package->hour;
    routes->flags=(unsigned char)(package->flags|AW_AMBIENT_LEVELLED);routes->profile=package->profile;
}
unsigned long AW_AmbientHash(const char *id) {
    unsigned long h=0x811C9DC5ul;int c;
    for(;*id;id++){c=(unsigned char)*id;if(c>='A' && c<='Z')c+=32;h=((h^(unsigned long)c)*0x01000193ul)&0xFFFFFFFFul;}
    return h;
}
void AW_AmbientRow(const aw_ambient_table_t *t,long i,aw_ambient_row_t *r) {
    const unsigned char *p=t->rows_data+i*AW_AMBIENT_ROW;
    r->ref=rd32(p);r->hash=rd32(p+4);r->distance=(unsigned short)rd16(p+8);r->duration=(unsigned short)rd16(p+10);
    r->hour=p[12];r->flags=p[13];r->points=p[14];r->destinations=p[15];
    r->first_point=rd32(p+16);r->first_hop=rd32(p+20);r->profile=(unsigned short)rd16(p+24);
}
long AW_AmbientFind(const aw_ambient_table_t *t,unsigned long ref,unsigned long hash) {
    long lo=0,hi=t->rows-1;
    while(lo<=hi){
        long mid=(lo+hi)/2;const unsigned char *p=t->rows_data+mid*AW_AMBIENT_ROW;
        unsigned long r=rd32(p),h=rd32(p+4);
        if(r==ref && h==hash)return mid;
        if(r<ref || (r==ref && h<hash))lo=mid+1;else hi=mid-1;
    }
    return -1;
}
void AW_AmbientBlobAt(const aw_ambient_table_t *t,const aw_ambient_row_t *r,long *points_at,long *points_bytes,
                      long *hops_at,long *hops_bytes) {
    *points_at=t->points_at+(long)r->first_point*AW_AMBIENT_POINT;*points_bytes=(long)r->points*AW_AMBIENT_POINT;
    *hops_at=t->hops_at+(long)r->first_hop;*hops_bytes=(long)r->points*r->destinations;
}
void AW_AmbientProfile(const aw_ambient_table_t *t,int index,unsigned short cdf[8]) {
    int i;
    for(i=0;i<8;i++)cdf[i]=(unsigned short)(index>=0 && index<t->profiles?rd16(t->profile_data+AW_AMBIENT_PROFILE*index+2*i):0);
}

void AW_AmbientIdleProfile(const unsigned char chances[8],unsigned multiplier,unsigned short cdf[8]) {
    unsigned long weight[8],run=0;int c[8],i,j,x2;
    for(i=0;i<8;i++)c[i]=chances[i]>100?100:chances[i];
    if(multiplier>65535)multiplier=65535;
    for(i=0;i<8;i++){
        unsigned long total=0;
        for(x2=1;x2<200 && x2<2*c[i];x2+=2){
            unsigned long p=65536ul;
            for(j=0;j<8;j++)if(j!=i){
                int below=x2<2*c[j]?x2:2*c[j];
                p=p*(unsigned long)(200-2*c[j]+below)/200ul;
            }
            total+=p;
        }
        weight[i]=total/100ul;
    }
    for(i=0;i<8;i++){
        run+=weight[i]*multiplier/65535ul;
        cdf[i]=(unsigned short)(run>65535ul?65535ul:run);
    }
}
int AW_AmbientPickIdle(const unsigned short cdf[8],unsigned roll) {
    int i;
    for(i=0;i<8;i++)if(roll<cdf[i])return i+2;
    return 0;
}
int AW_AmbientWithin(int x,int y,int z,unsigned distance) {
    unsigned long d;
    if(x<-16383 || x>16383 || y<-16383 || y>16383 || z<-16383 || z>16383)return 0;
    d=(unsigned long)((long)x*x)+(unsigned long)((long)y*y)+(unsigned long)((long)z*z);
    return d<=(unsigned long)distance*distance/16ul;
}

void AW_AmbientPoint(const aw_ambient_pkg_t *p,int i,int xyz[3],int *kind) {
    const unsigned char *b=p->blob+AW_AMBIENT_POINT*i;
    xyz[0]=sx16(rd16(b));xyz[1]=sx16(rd16(b+2));xyz[2]=sx16(rd16(b+4));
    if(kind)*kind=b[6];
}
static int allowed(const aw_ambient_pkg_t *p,int i) {return (p->allowed[i>>3]>>(i&7))&1;}
void AW_AmbientAllow(aw_ambient_pkg_t *p,unsigned distance) {
    int i,grid=0,kind,xyz[3];long best=-1,d;
    memset(p->allowed,0,sizeof(p->allowed));p->count=0;p->cur=0;p->distance=(unsigned short)distance;
    if(distance)for(i=0;i<p->destinations;i++){
        AW_AmbientPoint(p,i,xyz,&kind);
        if(kind==AW_AMBIENT_GRID && AW_AmbientWithin(xyz[0],xyz[1],xyz[2],distance)){p->allowed[i>>3]|=(unsigned char)(1<<(i&7));grid++;}
    }
    if(grid==1)for(i=0;i<p->destinations;i++){
        AW_AmbientPoint(p,i,xyz,&kind);
        if(kind==AW_AMBIENT_HOME || (kind==AW_AMBIENT_PARTWAY && distance==p->record_distance))
            p->allowed[i>>3]|=(unsigned char)(1<<(i&7));
    }
    for(i=0;i<p->destinations;i++)if(allowed(p,i)){
        p->count++;AW_AmbientPoint(p,i,xyz,NULL);
        d=(long)xyz[0]*xyz[0]+(long)xyz[1]*xyz[1]+(long)xyz[2]*xyz[2];
        if(best<0 || d<best){best=d;p->cur=(unsigned char)i;}
    }
    p->manual=(unsigned char)(distance>0 && p->count<2);
}
int AW_AmbientPickDestination(const aw_ambient_pkg_t *p,unsigned roll) {
    int i,k;
    if(p->count<2)return -1;
    k=(int)(roll%(unsigned)(p->count-1));
    for(i=0;i<p->destinations;i++)if(allowed(p,i) && i!=p->cur && k--==0)return i;
    return -1;
}
int AW_AmbientHop(const aw_ambient_pkg_t *p,int from,int goal) {
    int h;
    if(from<0 || from>=p->points || goal<0 || goal>=p->destinations)return -1;
    h=p->blob[AW_AMBIENT_POINT*p->points+from*p->destinations+goal];
    return h==AW_AMBIENT_NONE || h>=p->points?-1:h;
}
int AW_AmbientNearest(const aw_ambient_pkg_t *p,int x,int y,int z) {
    int i,best=-1,xyz[3];long d,bd=0;
    for(i=0;i<p->points;i++){
        AW_AmbientPoint(p,i,xyz,NULL);
        d=(long)(xyz[0]-x)*(xyz[0]-x)+(long)(xyz[1]-y)*(xyz[1]-y)+(long)(xyz[2]-z)*(xyz[2]-z);
        if(best<0 || d<bd){best=i;bd=d;}
    }
    return best;
}
/* AITravel's planning (v0.0.57; rules in the engine part's AITravel note): the range check and the route ends */
int AW_AmbientTravelInRange(int dx,int dy,int dz) {return AW_AmbientWithin(dx,dy,dz,7168u);}
int AW_AmbientTravelPlan(const aw_ambient_pkg_t *p,int fx,int fy,int fz,int tx,int ty,int tz,int *goal) {
    int i,best=-1,xyz[3];long bd=0;
    *goal=-1;
    if(!p || !p->blob || !p->destinations)return -1;
    for(i=0;i<p->destinations;i++){
        long dx,dy,dz,d;AW_AmbientPoint(p,i,xyz,NULL);
        dx=xyz[0]-tx;dy=xyz[1]-ty;dz=xyz[2]-tz;d=dx*dx+dy*dy+dz*dz;
        if(best<0 || d<bd){best=i;bd=d;}
    }
    *goal=best;
    return AW_AmbientNearest(p,fx,fy,fz);
}

#ifndef AW_AMBIENT_HOST_TEST
/* ------------------------------------------------------------------ the engine part */
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_skel.h"
#include "aw_npcpath.h"
#include "aw_actors.h"
#include "aw_move.h"
#include "aw_clock.h"
#include "aw_tryalloc.h"
#include "aw_mwvm.h"
#include "aw_combat.h"

#define SLOTS 128
#define ACTOR_RANGE 1792.0f       /* OpenMW's actors processing range 7168 x 0.25 */
#define REGISTER_RANGE 2048.0f
#define ARRIVE 16.0f            /* aiwander.cpp destinationTolerance 64 x 0.25 */
#define IDLE_CHECK 1.5f         /* idlePositionCheckInterval */
#define NEAR_ALLOWED 76.8f      /* iMaxActivateDist 192 x 1.6 x 0.25 */
#define STUCK_STEPS 10          /* countBeforeReset */
#define REACTION 0.25f          /* aitimer.hpp AI_REACTION_TIME */
enum {S_CHOOSE,S_IDLE,S_WALK,S_OFF};

typedef struct {
    edict_t *e;float ref;vec3_t home;
    aw_ambient_pkg_t pkg;unsigned char *mem;
    unsigned short cdf[8];
    unsigned char flags,state,goal,repeat,idle,manual_walk,stuck,fighting,greeting,mover,bad,can_walk;
    short at;                   /* the waypoint walked to (local point), -1 none */
    short num;                  /* the edict number (never computed from a stale pointer) */
    short fight;                /* the record's Fight (0 not read yet, -1 never hostile at any distance or no sheet) */
    float engage_at;            /* the next aggro check (OpenMW actor.hpp mEngageCombat: 1 s, deviating by 0.25 s) */
    float t,next_think,last_think,react_at,check_at,remain;int minutes;
    aw_anim_play_t play;
    int skel_first,skel_count;float skel_rate;
    float manual_goal[2];
    unsigned char travel;       /* AITravel (v0.0.57): 1 walking to travel_to, 2 arrived (the package is done);
                                   AIFollow: 3 following follow_num, 4 following and active (seen once in range) */
    float travel_to[3];
    short follow_num;           /* AIFollow: the followed edict's number */
    float follow_hours,follow_check;int follow_minutes;unsigned char follow_moving,follow_final;
} slot_t;
static void travel_end(slot_t *s);
static void follow_think(slot_t *s,float dt);
/* Saved AI packages (v0.0.57, SAVEGAME-COMPLETE-57): a loaded game's travel and follow packages, waiting until their
 * actor is in the map (applied at the once-a-second scan). */
#define SAVED_PACKAGES 64
typedef struct {float ref,follow_ref,hours,to[3];unsigned char travel,final;} saved_pkg_t;
static saved_pkg_t pend[SAVED_PACKAGES];static int npend;
static void apply_saved_packages(edict_t *p);

int (*aw_ambient_speed_attribute)(edict_t *e);
extern unsigned long aw_sv_move_calls;
int AW_CompanionEdict(edict_t *e);

/* "chim actors ambient on|off|think S|list|reset" (no command or cvar of its own: the resident registry budget).
 * Default ON since v0.0.57 (the compiled Wander packages run with the compiled scripts); "chim actors ambient off"
 * keeps every actor standing. Not saved. */
static int ambient_on=1;
static float think_interval=0.1f;
static aw_ambient_table_t table;
static unsigned char *resident,*profiles;
static FILE *file;long file_base;
static int loaded;              /* 0 not tried, 1 usable, -1 unavailable */
static long resident_size;      /* rows + idle profiles kept (the console answer) */
static slot_t slots[SLOTS];
static short slot_of[MAX_EDICTS];   /* slot + 1 per edict */
static float none_ref[MAX_EDICTS];
static int last_dry;               /* the contents at the last swim spot refused (status line) */  /* the reference an edict had when it was not found in the table */
static model_t *slots_world;
static unsigned long rng=1;
static float scan_at;
static struct {unsigned long thinks,steps,traces,walks,idles,bad_idles,registered,unknown,no_walk,blob_bytes,manual,stuck,
               levelled,aggro_checks,aggro_engaged,aggro_full,flights,dry,travels,travels_done,follows,follows_done;double seconds,worst;} st;
static const char path[]="npc-ambient.lut";
static aw_move_settings_t move_defaults;

static unsigned roll16(void) {rng=rng*1103515245ul+12345ul;return (unsigned)((rng>>8)&0xFFFFu);}
static float field(edict_t *e,char *name,float fallback) {eval_t *v=GetEdictFieldValue(e,name);return v?v->_float:fallback;}
static void set_field(edict_t *e,char *name,float value) {eval_t *v=GetEdictFieldValue(e,name);if(v)v->_float=value;}
static edict_t *player(void) {return sv.active && svs.clients && svs.clients[0].active?svs.clients[0].edict:NULL;}

static void unload(void) {
    if(file){fclose(file);file=NULL;}
    if(resident)free(resident);
    if(profiles)free(profiles);
    resident=profiles=NULL;memset(&table,0,sizeof(table));loaded=0;
}
/* Rows START.. (at most AW_AMBIENT_BLOCK) into BLOCK; the count read, 0 on a read error. */
static long read_block(long start,unsigned char *block) {
    long n=table.rows-start;
    if(n>AW_AMBIENT_BLOCK)n=AW_AMBIENT_BLOCK;
    if(n<=0 || fseek(file,file_base+AW_AMBIENT_HEADER+start*AW_AMBIENT_ROW,SEEK_SET) ||
       (long)fread(block,1,(size_t)(n*AW_AMBIENT_ROW),file)!=n*AW_AMBIENT_ROW)return 0;
    return n;
}
static int load(void) {
    long size,i,blocks;unsigned char head[AW_AMBIENT_HEADER],block[AW_AMBIENT_BLOCK*AW_AMBIENT_ROW];
    aw_ambient_row_t r,q;aw_ambient_table_t view;
    if(loaded)return loaded>0;
    loaded=-1;
    size=COM_FOpenFile((char *)path,&file);
    if(size<AW_AMBIENT_HEADER || !file){if(file)fclose(file);file=NULL;Con_DPrintf("Ambient table: %s not in this build\n",path);return 0;}
    file_base=ftell(file);
    if(fread(head,1,AW_AMBIENT_HEADER,file)!=AW_AMBIENT_HEADER || !AW_AmbientHeader(&table,head,size)){
        Con_Printf("Ambient table: %s is not AWAM1\n",path);fclose(file);file=NULL;memset(&table,0,sizeof(table));return 0;
    }
    /* outside the Quake heap, once per session: the first key of every block of rows (v0.0.57: the rows themselves
     * stay on disk, ACTORS-ALIVE-56) and the idle profiles; a lookup reads one block, the routes are read per actor */
    blocks=(table.rows+AW_AMBIENT_BLOCK-1)/AW_AMBIENT_BLOCK;
    resident=(unsigned char *)AW_TryMalloc((unsigned long)(blocks*8+1));
    profiles=(unsigned char *)AW_TryMalloc((unsigned long)(table.profiles*AW_AMBIENT_PROFILE+1));
    if(!resident || !profiles){Con_Printf("Ambient table: no memory for its index\n");unload();loaded=-1;return 0;}
    if(fseek(file,file_base+size-table.profiles*AW_AMBIENT_PROFILE,SEEK_SET) ||
       (long)fread(profiles,1,(size_t)(table.profiles*AW_AMBIENT_PROFILE),file)!=table.profiles*AW_AMBIENT_PROFILE){
        Con_Printf("Ambient table: %s is damaged\n",path);unload();loaded=-1;return 0;
    }
    table.profile_data=profiles;
    /* every row checked once (as AW_AmbientOpen does), block by block */
    memset(&view,0,sizeof(view));view.rows_data=block;
    for(i=0;i<blocks;i++){
        long n=read_block(i*AW_AMBIENT_BLOCK,block),k;
        if(!n){Con_Printf("Ambient table: %s is damaged\n",path);unload();loaded=-1;return 0;}
        for(k=0;k<n;k++){
            AW_AmbientRow(&view,k,&r);
            if(!AW_AmbientRowValid(&table,&r,i||k?&q:NULL)){Con_Printf("Ambient table: %s is damaged\n",path);unload();loaded=-1;return 0;}
            if(!k)memcpy(resident+8*i,block,8);
            q=r;
        }
    }
    resident_size=blocks*8+table.profiles*AW_AMBIENT_PROFILE;
    Con_DPrintf("Ambient table: %ld actors, %ld bytes resident\n",table.rows,resident_size);
    loaded=1;
    return 1;
}
/* The row of (REF, HASH) into *r: the block whose first key is the last at or before it, read and searched. */
static int find(unsigned long ref,unsigned long hash,aw_ambient_row_t *r) {
    long lo=0,hi=(table.rows+AW_AMBIENT_BLOCK-1)/AW_AMBIENT_BLOCK-1,b=-1,n,i;
    unsigned char block[AW_AMBIENT_BLOCK*AW_AMBIENT_ROW];aw_ambient_table_t view;
    while(lo<=hi){
        long mid=(lo+hi)/2;unsigned long kr=rd32(resident+8*mid),kh=rd32(resident+8*mid+4);
        if(kr<ref || (kr==ref && kh<=hash)){b=mid;lo=mid+1;}else hi=mid-1;
    }
    if(b<0 || !(n=read_block(b*AW_AMBIENT_BLOCK,block)))return 0;
    memset(&view,0,sizeof(view));view.rows_data=block;view.rows=n;
    if((i=AW_AmbientFind(&view,ref,hash))<0)return 0;
    AW_AmbientRow(&view,i,r);
    return 1;
}
/* The package of actor E: its placement's row, or for a levelled creature its reference's routes with the picked
 * creature's package (OpenMW 0.51: the picked creature runs its own record's packages, mwclass/creature.cpp). */
static int find_actor(edict_t *e,aw_ambient_row_t *r);

/* ---- slots ---- */
static void release(slot_t *s,int give_back) {
    edict_t *e=s->e;
    /* only an edict of the running world is touched: after a map change the old pointers are stale (the crash on a
     * teleport, NUM_FOR_EDICT: bad pointer, ACTOR-AMBIENT-STALE-EDICT-57); the slot keeps its edict number */
    if(give_back && e && slots_world==sv.worldmodel && !e->free){
        if(s->mover)AW_AnimMover(e,0);
        set_field(e,"aw_moving",0);
    }
    if(s->mem)free(s->mem);
    if(e && s->num>0 && s->num<MAX_EDICTS && slot_of[s->num]==(short)(s-slots+1))slot_of[s->num]=0;
    memset(s,0,sizeof(*s));
}
static void reset_all(void) {
    int i;
    for(i=0;i<SLOTS;i++)if(slots[i].e)release(&slots[i],0);
    memset(slot_of,0,sizeof(slot_of));memset(none_ref,0,sizeof(none_ref));slots_world=sv.worldmodel;rng=1;scan_at=0;
}
static slot_t *free_slot(void) {int i;for(i=0;i<SLOTS;i++)if(!slots[i].e)return &slots[i];return NULL;}
static int is_actor(edict_t *e) {
    const char *c;
    if(e->free || !e->v.classname)return 0;
    c=pr_strings+e->v.classname;
    return !strcmp(c,"aw_npc") || !strcmp(c,"aw_creature");
}
static const char *source_id(edict_t *e) {eval_t *v=GetEdictFieldValue(e,"aw_source_id");return v && v->string?pr_strings+v->string:"";}
static int can_walk(edict_t *e) {
    const aw_anim_t *a=AW_AnimOf(e);
    return a && ((a->from_layout && a->g[AW_ANIM_WALK].present) || a->mover[0]);
}
static void minutes_now(int *m) {int y,mo,d,h,mi;AW_ClockDate(&y,&mo,&d,&h,&mi);*m=d*1440+h*60+mi;}
/* A package for E from its row (or none: a script's package for an actor outside the table). */
static int find_actor(edict_t *e,aw_ambient_row_t *r) {
    unsigned long ref=(unsigned long)field(e,"aw_ref",0),hash=AW_AmbientHash(source_id(e));aw_ambient_row_t pkg;
    if(find(ref,hash,r))return 1;
    if(!find(ref,AW_AMBIENT_LEVELLED_HASH,r) || !find(AW_AMBIENT_LEVELLED_REF,hash,&pkg))return 0;
    AW_AmbientLevelled(r,&pkg);st.levelled++;
    return 1;
}
static slot_t *start(edict_t *e,const aw_ambient_row_t *row) {
    slot_t *s=free_slot();aw_ambient_row_t r;long pa,pb,ha,hb;int n=NUM_FOR_EDICT(e);
    if(!s || n<0 || n>=MAX_EDICTS)return NULL;
    memset(s,0,sizeof(*s));
    if(row){
        r=*row;AW_AmbientBlobAt(&table,&r,&pa,&pb,&ha,&hb);
        if(!(s->mem=(unsigned char *)AW_TryMalloc((unsigned long)(pb+hb))))return NULL;
        if(fseek(file,file_base+pa,SEEK_SET) || (long)fread(s->mem,1,(size_t)pb,file)!=pb ||
           fseek(file,file_base+ha,SEEK_SET) || (long)fread(s->mem+pb,1,(size_t)hb,file)!=hb){free(s->mem);s->mem=NULL;return NULL;}
        st.blob_bytes+=(unsigned long)(pb+hb);
        s->pkg.blob=s->mem;s->pkg.points=r.points;s->pkg.destinations=r.destinations;s->pkg.record_distance=r.distance;
        AW_AmbientProfile(&table,r.profile,s->cdf);
        s->flags=r.flags;s->repeat=(unsigned char)((r.flags&AW_AMBIENT_REPEAT)!=0);s->remain=r.duration;
        /* flyers wander on the routes or near the start (v0.0.57, fly() below); swimmers ignore the path grid
         * (OpenMW aiwander.cpp: "pathgrids don't usually include water, so swimmers ignore them") and swim to random
         * spots near the start that are in water */
        AW_AmbientAllow(&s->pkg,r.distance);
        if(r.flags&AW_AMBIENT_SWIMMER){memset(s->pkg.allowed,0,sizeof(s->pkg.allowed));s->pkg.count=0;s->pkg.manual=(unsigned char)(r.distance>0);}
    }
    s->e=e;s->ref=field(e,"aw_ref",0);VectorCopy(e->v.origin,s->home);
    s->state=S_CHOOSE;s->at=-1;s->can_walk=(unsigned char)can_walk(e);
    if(!s->can_walk && s->pkg.distance){st.no_walk++;}
    s->next_think=s->last_think=s->react_at=(float)sv.time;s->check_at=(float)sv.time+IDLE_CHECK;
    minutes_now(&s->minutes);
    s->num=(short)n;slot_of[n]=(short)(s-slots+1);st.registered++;
    return s;
}
static slot_t *slot_for(edict_t *e) {
    int n;slot_t *s;
    if(slots_world!=sv.worldmodel)reset_all();          /* a new map: every slot is stale */
    n=NUM_FOR_EDICT(e);
    if(n<0 || n>=MAX_EDICTS || !slot_of[n])return NULL;
    s=&slots[slot_of[n]-1];
    if(s->e!=e || s->ref!=field(e,"aw_ref",0)){release(s,0);slot_of[n]=0;return NULL;}
    return s;
}
/* Once a second: actors near the player that have a row get a package (lazy: an actor never near never costs). */
static void scan(edict_t *p) {
    int i;edict_t *e;vec3_t d;
    for(i=1;i<sv.num_edicts;i++){
        aw_ambient_row_t r;float ref;
        e=EDICT_NUM(i);
        if(!is_actor(e) || slot_for(e))continue;
        VectorSubtract(e->v.origin,p->v.origin,d);
        if(fabs(d[0])>REGISTER_RANGE || fabs(d[1])>REGISTER_RANGE || fabs(d[2])>REGISTER_RANGE)continue;
        ref=field(e,"aw_ref",0);
        if(ref<=0 || field(e,"aw_intro_role",0)){slot_of[i]=0;continue;}
        if(none_ref[i]==ref)continue;               /* looked up before: not in the table (no disk read again) */
        if(!find_actor(e,&r)){none_ref[i]=ref;st.unknown++;continue;}
        if(!start(e,&r))break;
    }
}

/* ---- animation ---- */
static const aw_skel_table_t *table_of(edict_t *e) {
    int i=(int)e->v.modelindex;model_t *m;const aliashdr_t *h;
    if(i<=0 || i>=MAX_MODELS || !(m=sv.models[i]) || m->type!=mod_alias)return NULL;
    h=(const aliashdr_t *)Mod_Extradata(m);
    return h && h->aw_skel?(const aw_skel_table_t *)h->aw_skel_table:NULL;
}
/* Plays IdleN once (playAnimationGroup "idleN", loop count 1); 0 when the actor has no such group (a bad idle). */
static int play_idle(slot_t *s,int idle) {
    const aw_skel_table_t *t=table_of(s->e);char name[8];int g;aw_skel_group_t grp;
    if(!t)return 0;
    name[0]='i';name[1]='d';name[2]='l';name[3]='e';name[4]=(char)('0'+idle);name[5]=0;
    if((g=AW_SkelGroup(t,name))<0)return 0;
    AW_SkelGroupAt(t,g,&grp);
    s->skel_first=(int)grp.first;s->skel_count=(int)(grp.last-grp.first+1);s->skel_rate=t->rate>0?t->rate:10;
    s->idle=(unsigned char)idle;s->t=0;
    set_field(s->e,"aw_moving",1);s->e->v.frame=(float)s->skel_first;
    return 1;
}
static void stop_walk(slot_t *s) {
    if(s->mover){AW_AnimMover(s->e,0);s->mover=0;}
    set_field(s->e,"aw_moving",0);s->at=-1;s->manual_walk=0;s->stuck=0;
}
static float walk_speed(slot_t *s) {
    aw_move_inputs_t in;int attr=aw_ambient_speed_attribute?aw_ambient_speed_attribute(s->e):-1;
    memset(&in,0,sizeof(in));in.speed=(float)(attr>=0?attr:50);in.scale=1;
    return AW_MoveWalkSpeed(&move_defaults,&in)*AW_MOVE_UNIT_SCALE;
}
static void walk_frames(slot_t *s,float speed,float dt) {
    const aw_anim_t *a=AW_AnimOf(s->e);float rate;int group,medium;unsigned long crossed=0;
    if(!a || !a->from_layout)return;
    medium=AW_AnimMedium(s->e);
    group=AW_AnimMoveGroup(a,speed,medium==AW_ANIM_SWIMMING,&rate);
    s->e->v.frame=(float)AW_AnimAdvance(a,&s->play,group,dt,rate,&crossed);
    AW_AnimSounds(s->e,a,group,crossed,medium);
}
static void begin_walk(slot_t *s) {
    const aw_anim_t *a=AW_AnimOf(s->e);
    if(a && a->mover[0] && !s->mover){AW_AnimMover(s->e,1);s->mover=1;}
    set_field(s->e,"aw_moving",1);memset(&s->play,0,sizeof(s->play));s->stuck=0;s->state=S_WALK;st.walks++;
}

/* ---- aggro on sight in the world (ACTORS-ALIVE-56, ACTOR-WANDER-AGGRO-52) ----
 * OpenMW 0.51 Actors::engageCombat (apps/openmw/mwmechanics/actors.cpp), every actor on its engage timer (actor.hpp
 * mEngageCombat, 1 s deviating by 0.25 s): an actor that is not fighting starts a fight with the player when
 * MechanicsManager::isAggressive holds (mechanicsmanagerimp.cpp: Fight + combat.cpp getFightDistanceBias
 * (iFightDistanceBase - fFightDistanceMultiplier x distance) + getFightDispositionBias >= 100) and it sees the player
 * (World::getLOS). The rule and the start of the fight are aw_combat.c's (AW_CombatAggro, the combat playground's
 * aggro mode); this module runs it for the creatures it moves. Our own code. Creatures only for now: an NPC's
 * disposition toward the player is not modelled yet (AW_CombatFightRating takes 50), said in docs/COMBAT.md. */
#define FIGHT_SLOTS 4           /* aw_combat.c SLOTS: hostiles at a time; a check with no slot free waits */
static int aggro_on=1;          /* "chim actors ambient aggro on|off" (default on, not saved) */
static void aggro(slot_t *s) {
    aw_fighter_t sheet;int got;
    if(!aggro_on || !(s->flags&AW_AMBIENT_CREATURE) || s->fight<0 || sv.time<s->engage_at)return;
    s->engage_at=(float)sv.time+0.75f+0.5f*(float)(roll16()&1023)/1023.0f;
    if(!AW_CombatAiLoaded())return;
    if(!s->fight){
        /* read once per package: a Fight that cannot reach 100 even at distance 0 never checks again */
        if(!AW_CombatActorLoad(source_id(s->e),&sheet) ||
           sheet.fight+aw_combat_ai.iFightDistanceBase<100){s->fight=-1;return;}
        s->fight=(short)(sheet.fight>0?sheet.fight:1);
    }
    st.aggro_checks++;
    {
        /* the rating from the kept Fight first (no file read while it stays under 100); distance in original units */
        edict_t *p=player();vec3_t d;
        if(!p)return;
        VectorSubtract(s->e->v.origin,p->v.origin,d);
        if(AW_CombatFightRating(&aw_combat_ai,s->fight,50,(float)Length(d)/AW_MOVE_UNIT_SCALE)<100)return;
    }
    if(AW_CombatHostiles()>=FIGHT_SLOTS){st.aggro_full++;return;}
    if(!AW_CombatActorLoad(source_id(s->e),&sheet)){s->fight=-1;return;}
    got=AW_CombatAggro(s->e,&sheet,NULL,50,NULL,NULL);
    if(got>0){st.aggro_engaged++;if(s->state==S_WALK)stop_walk(s);}
    else if(got<0 && !AW_CombatAiLoaded())s->fight=-1;
}

/* ---- the think ---- */
static void choose(slot_t *s) {
    int idle=AW_AmbientPickIdle(s->cdf,roll16());
    if(idle && !((s->bad>>(idle-2))&1)){
        if(play_idle(s,idle)){s->state=S_IDLE;st.idles++;return;}
        s->bad|=(unsigned char)(1<<(idle-2));st.bad_idles++;return;   /* aiwander.cpp mBadIdles */
    }
    if(!idle && s->pkg.distance && s->can_walk && !s->pkg.manual){
        int goal=AW_AmbientPickDestination(&s->pkg,roll16()),hop;
        if(goal<0)return;
        hop=AW_AmbientHop(&s->pkg,s->pkg.cur,goal);
        if(hop<0)return;
        s->goal=(unsigned char)goal;s->at=(short)hop;s->pkg.cur=(unsigned char)goal;   /* mCurrentPosition = destination */
        begin_walk(s);
    }
}
/* aiwander.cpp reactionTimeActions: the manual wander roll (no allowed destination) */
static void react(slot_t *s) {
    if(s->pkg.manual && s->can_walk && s->state!=S_WALK && roll16()%100>=96){
        unsigned r=roll16();float radius=(0.2f+0.8f*(float)(r&1023)/1023.0f)*s->pkg.distance*AW_MOVE_UNIT_SCALE;
        int heading=(int)(roll16()%AW_PATH_FAN);
        s->manual_goal[0]=s->home[0]+aw_path_fan[heading][0]*radius/AW_PATH_FAN_RADIUS;
        s->manual_goal[1]=s->home[1]+aw_path_fan[heading][1]*radius/AW_PATH_FAN_RADIUS;
        if(s->flags&AW_AMBIENT_SWIMMER){
            /* aiwander.cpp wanderNearStart: a water creature's spot must be in water (destinationIsAtWater) */
            vec3_t at;at[0]=s->manual_goal[0];at[1]=s->manual_goal[1];at[2]=s->home[2];
            if(!AW_AmbientInWater(at)){last_dry=SV_PointContents(at);st.dry++;return;}   /* water, as aw_anim.c reads it (<= CONTENTS_WATER) */
        }
        s->manual_walk=1;s->state=S_WALK;begin_walk(s);st.manual++;
    }
}
static int near_allowed(slot_t *s) {
    int i,xyz[3];float dx,dy;
    if(!s->pkg.count)return 1;
    for(i=0;i<s->pkg.destinations;i++)if((s->pkg.allowed[i>>3]>>(i&7))&1){
        AW_AmbientPoint(&s->pkg,i,xyz,NULL);
        dx=s->home[0]+xyz[0]-s->e->v.origin[0];dy=s->home[1]+xyz[1]-s->e->v.origin[1];
        if(dx*dx+dy*dy<NEAR_ALLOWED*NEAR_ALLOWED)return 1;
    }
    return 0;
}
/* Back onto the routes (displaced by a fight): straight to the nearest local point, then its route. */
static void rejoin(slot_t *s) {
    int near=AW_AmbientNearest(&s->pkg,(int)(s->e->v.origin[0]-s->home[0]),(int)(s->e->v.origin[1]-s->home[1]),
                               (int)(s->e->v.origin[2]-s->home[2])),goal=AW_AmbientPickDestination(&s->pkg,roll16());
    if(near<0 || goal<0 || !s->can_walk)return;
    s->goal=(unsigned char)goal;s->at=(short)near;s->pkg.cur=(unsigned char)goal;begin_walk(s);
}
/* "chim actors ambient steplog on": one console line per failed step, for the collision owner: where the actor
 * stood, where it stepped, and what the standing hull's sweep met (the brush model or entity, the plane normal) or,
 * when the sweep was free, that the floor or step height refused it (aw_walk.c support / step_height_ok). */
static int steplog;
static void log_failed_step(slot_t *s,const vec3_t move) {
    trace_t tr;vec3_t end;edict_t *e=s->e;const char *what="no floor or step too high (sweep free)";
    VectorAdd(e->v.origin,move,end);
    tr=SV_Move(e->v.origin,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);
    if(tr.startsolid)what="starts in solid";
    else if(tr.fraction<1)what=tr.ent && tr.ent!=sv.edicts?"an entity":"the world";
    static const char *const test[]={"none","move (no horizontal progress)","support (no floor within 8.75)",
                                     "step_height_ok (rise too steep)","lava"};
    Con_Printf("Ambient step failed: %s at %.1f %.1f %.1f dir %.2f %.2f, %s%s%s, frac %.3f solid %d/%d normal %.2f %.2f %.2f\n",
               source_id(e),e->v.origin[0],e->v.origin[1],e->v.origin[2],move[0],move[1],what,
               tr.ent && tr.ent!=sv.edicts && tr.ent->v.model?" ":"",
               tr.ent && tr.ent!=sv.edicts && tr.ent->v.model?pr_strings+tr.ent->v.model:"",
               tr.fraction,(int)tr.startsolid,(int)tr.allsolid,tr.plane.normal[0],tr.plane.normal[1],tr.plane.normal[2]);
    Con_Printf("  refused by %s; walk move reached %.1f %.1f %.1f; support there frac %.3f normal %.2f %.2f %.2f solid %d\n",
               test[aw_actor_step_fail>=0 && aw_actor_step_fail<=4?aw_actor_step_fail:0],aw_actor_step_reached[0],
               aw_actor_step_reached[1],aw_actor_step_reached[2],aw_actor_step_floor[0],aw_actor_step_floor[1],
               aw_actor_step_floor[2],aw_actor_step_floor[3],(int)aw_actor_step_floor[4]);
}
/* Water for a swimmer: the map's liquid contents, or outdoors anything below the sea level (z 0: the exterior water
 * height, OpenMW's cell water level). A CHIM world's sea is a drawn surface with a thin water volume (seen in game,
 * 31 October 2026: slaughterfish at z -150 read CONTENTS_EMPTY), so the contents alone strand every fish. */
int AW_AmbientInWater(const vec3_t p) {
    vec3_t q;VectorCopy(p,q);
    return SV_PointContents(q)<=CONTENTS_WATER || (!AW_Interior() && p[2]<0);
}/* Flying creatures (v0.0.57, ACTORS-ALIVE-56, ACTOR-MOVING-RUNTIME-GROUND-48): OpenMW 0.51 aiwander.cpp moves a pure
 * flying creature along a straight path (buildStraightPath), its random spot near the start at the start's height
 * (getRandomPointAround), with no ground under it, and gives up a blocked walk after one failed step
 * (getCountBeforeReset). Here: the standing hull swept straight toward the target in 3D (SV_Move), no floor test, no
 * gravity, never put on the ground (its aw_ground_mode is 1 from the record's flags, tools/creature_library.py).
 * 1 when it moved. */
static int fly(slot_t *s,const float target[3],float step) {
    edict_t *e=s->e;vec3_t d,end;trace_t tr;float len;
    VectorSubtract(target,e->v.origin,d);len=(float)Length(d);
    if(len<=0)return 1;
    if(step>len)step=len;
    VectorMA(e->v.origin,step/len,d,end);
    tr=SV_Move(e->v.origin,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);
    if(tr.startsolid || tr.allsolid || tr.fraction<=0)return 0;
    if((s->flags&AW_AMBIENT_SWIMMER) && !AW_AmbientInWater(tr.endpos))return 0;   /* a swimmer stays in water */
    VectorCopy(tr.endpos,e->v.origin);SV_LinkEdict(e,false);
    return tr.fraction>=1;
}
static void walk(slot_t *s,float dt) {
    float target[2],dx,dy,len,speed=walk_speed(s),step;vec3_t move,from;int xyz[3],heading;unsigned long before;
    int flyer=(s->flags&(AW_AMBIENT_FLYER|AW_AMBIENT_SWIMMER))!=0;float tz=s->home[2];   /* swimmers move the same way, in water */
    if(s->manual_walk){target[0]=s->manual_goal[0];target[1]=s->manual_goal[1];}
    else{AW_AmbientPoint(&s->pkg,s->at,xyz,NULL);target[0]=s->home[0]+xyz[0];target[1]=s->home[1]+xyz[1];tz=s->home[2]+xyz[2];}
    if(flyer){
        float t3[3],dz=tz-s->e->v.origin[2];
        dx=target[0]-s->e->v.origin[0];dy=target[1]-s->e->v.origin[1];
        if(dx*dx+dy*dy+dz*dz<=ARRIVE*ARRIVE){
            int next;
            if(s->manual_walk || s->at==s->goal || (next=AW_AmbientHop(&s->pkg,s->at,s->goal))<0){
                if(s->travel==1){travel_end(s);return;}
                stop_walk(s);s->state=S_CHOOSE;return;}
            s->at=(short)next;return;
        }
        heading=AW_PathHeading((int)dx,(int)dy);
        s->e->v.angles[1]=heading*360.0f/AW_PATH_FAN-90;s->e->v.angles[0]=s->e->v.angles[2]=0;
        t3[0]=target[0];t3[1]=target[1];t3[2]=tz;
        if(fly(s,t3,speed*dt)){s->stuck=0;st.steps++;st.flights++;walk_frames(s,speed,dt);}
        else{st.stuck++;if(s->travel==1){travel_end(s);return;}stop_walk(s);s->state=S_CHOOSE;}   /* getCountBeforeReset: 1 for a flyer */
        return;
    }
    dx=target[0]-s->e->v.origin[0];dy=target[1]-s->e->v.origin[1];len=(float)AW_PathLength((int)dx,(int)dy);
    if(len<=ARRIVE){
        int next;
        if(s->manual_walk || s->at==s->goal || (next=AW_AmbientHop(&s->pkg,s->at,s->goal))<0){
            if(s->travel==1){travel_end(s);return;}
            stop_walk(s);s->state=S_CHOOSE;return;}
        s->at=(short)next;return;
    }
    step=speed*dt;if(step>len)step=len;
    move[0]=dx*step/len;move[1]=dy*step/len;move[2]=0;
    heading=AW_PathHeading((int)dx,(int)dy);
    s->e->v.angles[1]=heading*360.0f/AW_PATH_FAN-90;s->e->v.angles[0]=s->e->v.angles[2]=0;
    before=aw_sv_move_calls;VectorCopy(s->e->v.origin,from);
    if(AW_ActorStep(s->e,move,host_frametime>0?host_frametime:dt)){   /* the velocity is moved over one frame */
        /* WALK-CYCLES-57: the walk plays by the distance the step covered (a step cut by a wall or the waypoint plays
         * that much of the cycle), so the feet do not slide; the phase is AW_AnimAdvance's speed over the own speed */
        float gone=(float)sqrt((s->e->v.origin[0]-from[0])*(s->e->v.origin[0]-from[0])+(s->e->v.origin[1]-from[1])*(s->e->v.origin[1]-from[1]));
        s->stuck=0;st.steps++;walk_frames(s,dt>0 && gone>0 && gone<speed*dt*2?gone/dt:speed,dt);
    }
    else{
        if(steplog)log_failed_step(s,move);
        if(++s->stuck>=STUCK_STEPS){st.stuck++;if(s->travel==1){travel_end(s);}else{stop_walk(s);s->state=S_CHOOSE;}}   /* countBeforeReset */
        else walk_frames(s,0,dt);
    }
    st.traces+=aw_sv_move_calls-before;
}
static void think(slot_t *s,float dt) {
    edict_t *e=s->e;int fighting=AW_CombatSlotState(e,NULL)!=0;
    if(fighting){s->fighting=1;s->mover=0;return;}           /* combat owns it (it restores the model when done) */
    if(s->fighting){s->fighting=0;s->state=S_CHOOSE;s->at=-1;s->manual_walk=0;set_field(e,"aw_moving",0);
                    if(s->travel==1){   /* a travel goes on after the fight, straight to its target */
                        s->manual_goal[0]=s->travel_to[0];s->manual_goal[1]=s->travel_to[1];s->manual_walk=1;begin_walk(s);
                        return;}
                    if(s->travel==2){s->state=S_OFF;return;}
                    if(!near_allowed(s)){rejoin(s);}
                    return;}
    aggro(s);                                   /* a finished package does not end the engage check (OpenMW) */
    if(AW_CombatSlotState(e,NULL)){s->fighting=1;s->mover=0;return;}
    if(s->travel==3 || s->travel==4){follow_think(s,dt);return;}
    if(s->state==S_OFF)return;
    /* a greeting pauses the package (aiwander.cpp: the greeting interrupts wandering) */
    if(field(e,"aw_face_until",0)>sv.time){
        if(!s->greeting){s->greeting=1;if(s->state==S_WALK)set_field(e,"aw_moving",0);if(s->state==S_IDLE){s->state=S_CHOOSE;set_field(e,"aw_moving",0);}}
        return;
    }
    if(s->greeting){s->greeting=0;if(s->state==S_WALK)set_field(e,"aw_moving",1);}
    s->t+=dt;
    if(sv.time>=s->react_at){
        int m;
        s->react_at=(float)sv.time+REACTION;
        minutes_now(&m);
        if(s->remain>0 && m!=s->minutes){
            int delta=m-s->minutes;if(delta<0)delta+=1440;
            s->remain-=delta/60.0f;s->minutes=m;
            if(s->remain<=0){
                aw_ambient_row_t r;
                if(s->repeat){if(find_actor(e,&r))s->remain=r.duration;}   /* repeat: again */
                else{stop_walk(s);s->state=S_OFF;AW_MwvmStateChanged();return;}   /* done: it stands; scripts wake */
            }
        }
        react(s);
    }
    switch(s->state){
    case S_CHOOSE:choose(s);break;
    case S_IDLE:
        e->v.frame=(float)(s->skel_first+(int)(s->t*s->skel_rate));
        if((int)(s->t*s->skel_rate)>=s->skel_count){e->v.frame=(float)s->skel_first;set_field(e,"aw_moving",0);s->state=S_CHOOSE;}
        else if(sv.time>=s->check_at){
            s->check_at=(float)sv.time+IDLE_CHECK;
            if(s->pkg.distance && !s->pkg.manual && !near_allowed(s)){set_field(e,"aw_moving",0);rejoin(s);}
        }
        break;
    case S_WALK:walk(s,dt);break;
    }
}
void AW_AmbientPhysics(void) {
    edict_t *p;int i;float interval;double t0;
    if(!ambient_on || !(p=player()))return;
    if(slots_world!=sv.worldmodel)reset_all();
    if(!load())return;
    if(sv.time>=scan_at){scan_at=(float)sv.time+1.0f;scan(p);if(npend)apply_saved_packages(p);}
    interval=think_interval;
    t0=Sys_FloatTime();
    for(i=0;i<SLOTS;i++){
        slot_t *s=&slots[i];vec3_t d;float dt;
        if(!s->e)continue;
        if(s->e->free || s->ref!=field(s->e,"aw_ref",0)){release(s,0);continue;}
        if(sv.time<s->next_think)continue;
        dt=(float)(sv.time-s->last_think);s->last_think=(float)sv.time;s->next_think=(float)sv.time+interval;
        VectorSubtract(s->e->v.origin,p->v.origin,d);
        if(DotProduct(d,d)>ACTOR_RANGE*ACTOR_RANGE)continue;   /* OpenMW: no actor is processed beyond this range */
        /* combat first (it stops the actor's think while it fights); then anyone else holding the think (the
         * companion, the animation stage) owns the actor */
        if(!AW_CombatSlotState(s->e,NULL) && !s->fighting &&
           (AW_CompanionEdict(s->e) || s->e->v.nextthink<=0 || field(s->e,"aw_story_hidden",0)))continue;
        if(dt>.5f)dt=.5f;
        st.thinks++;think(s,dt);
    }
    t0=Sys_FloatTime()-t0;st.seconds+=t0;if(t0>st.worst)st.worst=t0;
}

/* ---- AITravel (v0.0.57, MWSCRIPT-MORE-57; rules from OpenMW 0.51 apps/openmw/mwmechanics/aitravel.cpp, written
 * independently) ----
 * A travel goes only to a point within 7168 original units (isWithinMaxRange); farther, the package does not run.
 * The actor walks its compiled routes from the point nearest it to the destination nearest the target, then straight
 * to the target; it never crosses a door (the routes are one cell's or one room's). Arrival: within the walk's arrival
 * distance (aitravel.cpp endTolerance 64 original units); a walk stuck for countBeforeReset steps also ends it. Done
 * is reported to GetAIPackageDone; the actor then stands. The pure planning is AW_AmbientTravelPlan (above). */
static void travel_end(slot_t *s) {
    float dx=s->travel_to[0]-s->e->v.origin[0],dy=s->travel_to[1]-s->e->v.origin[1];
    if(!s->manual_walk && dx*dx+dy*dy>ARRIVE*ARRIVE && s->stuck<STUCK_STEPS){
        /* the routes brought it to the destination nearest the target: the last leg is straight */
        s->manual_goal[0]=s->travel_to[0];s->manual_goal[1]=s->travel_to[1];s->manual_walk=1;s->stuck=0;
        return;
    }
    stop_walk(s);s->travel=2;s->state=S_OFF;s->manual_walk=0;st.travels_done++;
    AW_MwvmStateChanged();                      /* GetAIPackageDone changes */
}
/* ---- AIFollow (v0.0.57; rules from OpenMW 0.51 apps/openmw/mwmechanics/aifollow.cpp, written independently) ----
 * The follow distance is 64 original units plus the target's half width plus twice the actor's (16 engine units +
 * the hulls); the package becomes active only once the target is within that distance + 384 original units and in
 * sight (checked every 0.5 s); then the actor walks straight toward the target when it is farther than the distance
 * (30 original units of hysteresis between moving and stopping) and stands facing it when near. A duration (game
 * hours) ends it, and so does reaching the final point when one is given. Followers do not cross doors here and are
 * never warped (OpenMW warps only at teleport doors within 800 units, out of view: not yet). */
static void follow_done(slot_t *s) {
    stop_walk(s);s->travel=2;s->state=S_OFF;st.follows_done++;AW_MwvmStateChanged();
}
static void follow_think(slot_t *s,float dt) {
    edict_t *t=s->follow_num>0 && s->follow_num<sv.num_edicts?EDICT_NUM(s->follow_num):NULL,*e=s->e;
    vec3_t d;float fd,th,dist2;
    if(!t || t->free){follow_done(s);return;}
    VectorSubtract(t->v.origin,e->v.origin,d);dist2=DotProduct(d,d);
    fd=16.0f+t->v.maxs[0]+2*e->v.maxs[0];
    if(s->travel==3){
        if(sv.time<s->follow_check)return;
        s->follow_check=(float)sv.time+0.5f;
        if(dist2<(fd+96)*(fd+96)){
            vec3_t eye;trace_t tr;
            VectorCopy(e->v.origin,eye);eye[2]+=e->v.view_ofs[2];
            tr=SV_Move(eye,vec3_origin,vec3_origin,t->v.origin,MOVE_NOMONSTERS,e);
            if(tr.fraction>=1)s->travel=4;
        }
        if(s->travel==3)return;
    }
    if(s->follow_hours>0){
        int m;minutes_now(&m);
        if(m!=s->follow_minutes){int delta=m-s->follow_minutes;if(delta<0)delta+=1440;s->follow_hours-=delta/60.0f;s->follow_minutes=m;}
        if(s->follow_hours<=0){follow_done(s);return;}
    }
    if(s->follow_final){
        float fx=s->travel_to[0]-e->v.origin[0],fy=s->travel_to[1]-e->v.origin[1],fz=s->travel_to[2]-e->v.origin[2];
        if(fx*fx+fy*fy+fz*fz<fd*fd){follow_done(s);return;}
    }
    th=s->follow_moving?fd-7.5f:fd+7.5f;
    if(dist2<=th*th){
        if(s->state==S_WALK)stop_walk(s);
        s->state=S_CHOOSE;s->follow_moving=0;
        e->v.angles[1]=(float)(atan2(d[1],d[0])*180.0/M_PI)-90;   /* a converted character faces its local +Y */
        return;
    }
    s->manual_goal[0]=t->v.origin[0];s->manual_goal[1]=t->v.origin[1];s->manual_walk=1;
    if(s->state!=S_WALK)begin_walk(s);
    s->follow_moving=1;
    walk(s,dt);
}
int AW_AmbientFollow(edict_t *e,edict_t *target,float hours,const float *final) {
    slot_t *s;aw_ambient_row_t r;
    if(!e || e->free || !is_actor(e) || !target || target->free || target==e)return 0;
    if(!(s=slot_for(e)) && !(s=start(e,load() && find_actor(e,&r)?&r:NULL)))return 0;
    if(!s->can_walk)return 0;
    if(s->state==S_WALK)stop_walk(s);
    s->travel=3;s->follow_num=(short)NUM_FOR_EDICT(target);s->follow_hours=hours>0?hours:0;minutes_now(&s->follow_minutes);
    s->follow_check=0;s->follow_moving=0;s->remain=0;s->repeat=0;s->state=S_CHOOSE;
    s->follow_final=(unsigned char)(final && (final[0]!=0 || final[1]!=0 || final[2]!=0));
    if(s->follow_final)VectorCopy(final,s->travel_to);
    st.follows++;AW_MwvmStateChanged();
    return 1;
}
int AW_AmbientTravel(edict_t *e,const float to[3]) {
    slot_t *s;aw_ambient_row_t r;int goal=-1,from;
    if(!e || e->free || !is_actor(e) || !to)return 0;
    if(!AW_AmbientTravelInRange((int)(to[0]-e->v.origin[0]),(int)(to[1]-e->v.origin[1]),(int)(to[2]-e->v.origin[2])))
        return 0;                               /* aitravel.cpp: beyond the maximum range the package does not run */
    if(!(s=slot_for(e)) && !(s=start(e,load() && find_actor(e,&r)?&r:NULL)))return 0;
    if(!s->can_walk)return 0;
    if(s->state==S_WALK)stop_walk(s);
    VectorCopy(to,s->travel_to);s->travel=1;s->remain=0;s->repeat=0;s->stuck=0;
    from=AW_AmbientTravelPlan(&s->pkg,(int)(e->v.origin[0]-s->home[0]),(int)(e->v.origin[1]-s->home[1]),
                              (int)(e->v.origin[2]-s->home[2]),(int)(to[0]-s->home[0]),(int)(to[1]-s->home[1]),
                              (int)(to[2]-s->home[2]),&goal);
    if(from>=0 && goal>=0 && !s->pkg.manual){s->goal=(unsigned char)goal;s->at=(short)from;s->manual_walk=0;}
    else{s->manual_goal[0]=to[0];s->manual_goal[1]=to[1];s->manual_walk=1;}   /* no routes: straight there */
    s->state=S_WALK;begin_walk(s);st.travels++;
    AW_MwvmStateChanged();                      /* a package started */
    return 1;
}

/* ---- saved packages (v0.0.57, SAVEGAME-COMPLETE-57; OpenMW keeps the package sequence in the actor's state:
 * components/esm3/aisequence.cpp, here only travel and follow) ----
 * "AWPK" u8 1 u8 count, then per package: f32 the actor's reference, u8 state (1 travelling, 2 done, 3/4 following),
 * u8 a final point given, f32 x y z (the travel's target or the follow's final point, map coordinates), f32 the
 * followed actor's reference (-1 the player), f32 hours of following left. 26 bytes a package. */
#define SAVED_PKG_BYTES 26
static unsigned char *putf32(unsigned char *p,float f){unsigned int v;memcpy(&v,&f,4);p[0]=(unsigned char)(v>>24);p[1]=(unsigned char)(v>>16);p[2]=(unsigned char)(v>>8);p[3]=(unsigned char)v;return p+4;}
static float getf32(const unsigned char *p){unsigned int v=((unsigned int)p[0]<<24)|((unsigned int)p[1]<<16)|((unsigned int)p[2]<<8)|p[3];float f;memcpy(&f,&v,4);return f;}
int AW_AmbientPackagesExport(unsigned char *out,int capacity) {
    int i,n=0;unsigned char *p=out+6;
    if(capacity<6)return -1;
    for(i=0;i<SLOTS+npend;i++){
        saved_pkg_t k;
        if(i<SLOTS){
            slot_t *s=&slots[i];edict_t *t;
            if(!s->e || !s->travel)continue;
            memset(&k,0,sizeof(k));k.ref=s->ref;k.travel=s->travel;k.hours=s->follow_hours;
            if(s->travel>=3){
                t=s->follow_num>0 && s->follow_num<sv.num_edicts?EDICT_NUM(s->follow_num):NULL;
                k.follow_ref=!t || t->free?0:t==player()?-1:field(t,"aw_ref",0);
                k.final=s->follow_final;
            }else k.final=1;
            VectorCopy(s->travel_to,k.to);
        }else k=pend[i-SLOTS];          /* not applied yet: kept for the next save */
        if(!k.ref || (k.travel>=3 && !k.follow_ref))continue;
        if(p+SAVED_PKG_BYTES>out+capacity || n==255)return -1;
        p=putf32(p,k.ref);*p++=k.travel;*p++=k.final;p=putf32(p,k.to[0]);p=putf32(p,k.to[1]);p=putf32(p,k.to[2]);
        p=putf32(p,k.follow_ref);p=putf32(p,k.hours);n++;
    }
    memcpy(out,"AWPK",4);out[4]=1;out[5]=(unsigned char)n;
    return 6+SAVED_PKG_BYTES*n;
}
int AW_AmbientPackagesImport(const unsigned char *data,int bytes) {
    int i,n;
    npend=0;
    if(bytes<6 || memcmp(data,"AWPK",4) || data[4]!=1)return 0;
    n=data[5];
    if(bytes!=6+SAVED_PKG_BYTES*n || n>SAVED_PACKAGES)return 0;
    for(i=0;i<n;i++){
        const unsigned char *p=data+6+SAVED_PKG_BYTES*i;saved_pkg_t *k=&pend[npend];
        k->ref=getf32(p);k->travel=p[4];k->final=p[5];k->to[0]=getf32(p+6);k->to[1]=getf32(p+10);k->to[2]=getf32(p+14);
        k->follow_ref=getf32(p+18);k->hours=getf32(p+22);
        if(!(k->ref>0) || k->travel<1 || k->travel>4)continue;
        npend++;
    }
    return 1;
}
static edict_t *edict_by_ref(float ref) {
    int i;
    for(i=1;i<sv.num_edicts;i++){edict_t *e=EDICT_NUM(i);if(!e->free && field(e,"aw_ref",0)==ref)return e;}
    return NULL;
}
static void apply_saved_packages(edict_t *p) {
    int i;
    for(i=0;i<npend;){
        saved_pkg_t *k=&pend[i];edict_t *e=edict_by_ref(k->ref),*t;int ok=0;
        if(!e){i++;continue;}                  /* its actor is not in this map (yet): it waits */
        if(k->travel==1)ok=AW_AmbientTravel(e,k->to);
        else if(k->travel==2){slot_t *s=slot_for(e);aw_ambient_row_t r;
            if(!s)s=start(e,load() && find_actor(e,&r)?&r:NULL);
            if(s){stop_walk(s);s->travel=2;s->state=S_OFF;ok=1;}}
        else{t=k->follow_ref<0?p:edict_by_ref(k->follow_ref);
            ok=t && AW_AmbientFollow(e,t,k->hours,k->final?k->to:NULL);}
        (void)ok;
        pend[i]=pend[--npend];                 /* applied (or not possible here): done */
    }
}

/* ---- MWScript AIWander (the interpreter's call) ---- */
int AW_AmbientWander(edict_t *e,int distance,int duration,int hour,const unsigned char idle[8],int repeat) {
    slot_t *s;aw_ambient_row_t r;
    if(!e || e->free || !is_actor(e))return 0;
    if(distance<0)distance=0;
    if(distance>65535)distance=65535;
    if(!(s=slot_for(e))){
        if(!(s=start(e,load() && find_actor(e,&r)?&r:NULL)))return 0;
    }
    if(s->state==S_WALK)stop_walk(s);
    (void)hour;                                 /* stored by OpenMW, read nowhere */
    AW_AmbientIdleProfile(idle,loaded>0?table.multiplier:49151u,s->cdf);
    s->repeat=(unsigned char)(repeat!=0);s->remain=(float)(duration>0?duration:0);s->bad=0;
    if(s->pkg.blob)AW_AmbientAllow(&s->pkg,(unsigned)distance);
    else{s->pkg.distance=(unsigned short)distance;s->pkg.manual=(unsigned char)(distance>0);}
    /* OpenMW starts a stacked package where the actor stands (mInitialActorPosition); the compiled routes are
     * relative to the spawn position, so the start stays there (an AmiWind simplification, docs/NPC_PATHFINDING.md) */
    s->state=S_CHOOSE;s->at=-1;s->travel=0;
    AW_MwvmStateChanged();                      /* a package started: GetCurrentAIPackage / GetAIPackageDone change */
    return 1;
}
/* The scripts' GetCurrentAIPackage / GetAIPackageDone (v054-mwscript's hook): the actor's current package in OpenMW's
 * numbers (aisequence.cpp / aiextensions.cpp; combat and pursue never show): 0 Wander for an actor this module runs or
 * whose placement has a compiled Wander package, -1 otherwise (Travel, Escort, Follow and Activate are not run yet,
 * so they read as none); *done 1 once a non-repeating Wander's duration has run out (OpenMW AiSequence mDone). */
int AW_AmbientAiPackage(edict_t *e,int *done) {
    slot_t *s;
    if(done)*done=0;
    if(!e || e->free || !is_actor(e))return -1;
    if((s=slot_for(e))!=NULL){
        if(s->travel>=3){return 3;}                          /* AIFollow: OpenMW's package 3, done when it ends */
        if(s->travel){if(done)*done=s->travel==2;return 1;}   /* AITravel: OpenMW's package 1 */
        if(done){*done=s->state==S_OFF;}
        return 0;
    }
    {
        aw_ambient_row_t r;int n=NUM_FOR_EDICT(e);float ref=field(e,"aw_ref",0);
        if(n>=0 && n<MAX_EDICTS && ref>0 && none_ref[n]==ref)return -1;   /* known absent: no disk read */
        if(load() && find_actor(e,&r))return 0;
        if(n>=0 && n<MAX_EDICTS && ref>0)none_ref[n]=ref;
    }
    return -1;
}

/* The row flags of the package E runs (AW_AMBIENT_FLYER, ...), 0 when it runs none: the combat layer's chase asks
 * whether a fighter flies (COMBAT-FLYER-FLEES-57). No disk read: only an actor with a slot answers. */
int AW_AmbientFlags(edict_t *e) {
    slot_t *s;
    if(!e || e->free || !is_actor(e) || !(s=slot_for(e)))return 0;
    return s->flags;
}

/* ---- console ---- */
static void status(void) {
    int i,active=0,walking=0,idling=0;
    for(i=0;i<SLOTS;i++)if(slots[i].e){active++;walking+=slots[i].state==S_WALK;idling+=slots[i].state==S_IDLE;}
    Con_Printf("Ambient (chim actors ambient %s, think %.2f s): table %s, %ld rows; %d actors registered (%d walking, %d in an idle)\n",
               ambient_on?"on":"off",think_interval,loaded>0?"loaded":loaded<0?"unavailable":"not read",loaded>0?table.rows:0L,active,walking,idling);
    Con_Printf("  since reset: %lu thinks, %lu steps, %lu traces, %lu walks (%lu manual, %lu stuck), %lu idles, %lu bad idles\n",
               st.thinks,st.steps,st.traces,st.walks,st.manual,st.stuck,st.idles,st.bad_idles);
    Con_Printf("  %lu registered, %lu actors not in the table, %lu cannot walk (no walk animation), %lu route bytes read\n",
               st.registered,st.unknown,st.no_walk,st.blob_bytes);
    Con_Printf("  %lu flying or swimming steps (straight, off the ground; %lu swim spots out of water skipped, last contents %d)\n",st.flights,st.dry,last_dry);
    Con_Printf("  %lu levelled creatures on their reference's routes; aggro %s: %lu checks, %lu fights started, %lu waited (4 fighting)\n",
               st.levelled,aggro_on?"on":"off",st.aggro_checks,st.aggro_engaged,st.aggro_full);
    Con_Printf("  cost: %.3f ms per think, worst frame %.3f ms\n",st.thinks?st.seconds*1000.0/st.thinks:0.0,st.worst*1000.0);
}
/* "chim actors ambient [on|off|think S|list|reset]" (aw_actors.c forwards it; arguments from the fourth word) */
void AW_AmbientCommand(void) {
    const char *a=Cmd_Argc()>3?Cmd_Argv(3):"status";
    if(!strcmp(a,"on") || !strcmp(a,"off")){
        ambient_on=a[1]=='n';
        if(!ambient_on){int i;for(i=0;i<SLOTS;i++)if(slots[i].e)release(&slots[i],1);}
        /* the answer says what it does and what was loaded (DBG-MWSCRIPT-SILENT-56) */
        Con_Printf("Ambient: %s (default on, not saved): %s\n",ambient_on?"ON":"OFF",ambient_on?
                   "placed actors run their compiled Wander packages (id1/npc-ambient.lut): walks inside the "
                   "package's distance along the cell's path grid, idles by the package's chances; MWScript "
                   "AIWander sets a package here":"every actor stands; chim actors ambient on walks them again");
        if(ambient_on && load())
            Con_Printf("Ambient table: id1/%s AWAM1, %ld actors, %ld bytes resident (routes read per actor)\n",path,
                       table.rows,resident_size);
        else if(ambient_on)Con_Printf("Ambient table: id1/%s not loaded (%s)\n",path,
                                      loaded<0?"not in this image, or damaged":"not read");
    }
    else if(!strcmp(a,"think") && Cmd_Argc()>4){
        float v=(float)Q_atof(Cmd_Argv(4));
        think_interval=v<.05f?.05f:v>.5f?.5f:v;
        Con_Printf("Ambient: think every %.2f s\n",think_interval);
    }
    else if(!strcmp(a,"steplog") && Cmd_Argc()>4){
        steplog=aw_actor_step_diag=!strcmp(Cmd_Argv(4),"on");Con_Printf("Ambient: failed-step log %s\n",steplog?"on":"off");
    }
    else if(!strcmp(a,"aggro") && Cmd_Argc()>4){
        aggro_on=!strcmp(Cmd_Argv(4),"on");
        Con_Printf("Ambient: aggro on sight %s (default on, not saved): creatures with a Fight that reaches 100 at "
                   "their distance attack the player they see (OpenMW's fight-distance rule)\n",aggro_on?"ON":"OFF");
    }
    else if(!strcmp(a,"reset")){memset(&st,0,sizeof(st));Con_Printf("Ambient: counters reset\n");}
    else if(!strcmp(a,"list")){
        int i;
        for(i=0;i<SLOTS;i++)if(slots[i].e){
            slot_t *s=&slots[i];
            Con_Printf("%3d %-24s ref %ld state %d dist %u dests %u/%u cur %u goal %u at %d%s%s%s at %.0f %.0f %.0f flags %u ground %.0f scale %.3f model %s%s\n",
                       i,source_id(s->e),(long)s->ref,s->state,s->pkg.distance,s->pkg.count,s->pkg.destinations,s->pkg.cur,
                       s->goal,s->at,s->pkg.manual?" manual":"",s->can_walk?"":" no-walk",
                       s->travel==1?" TRAVEL":s->travel==2?" TRAVEL-DONE":s->travel>=3?" FOLLOW":"",
                       s->e->v.origin[0],s->e->v.origin[1],
                       s->e->v.origin[2],s->flags,field(s->e,"aw_ground_mode",-1),field(s->e,"aw_scale",1),
                       s->e->v.model?pr_strings+s->e->v.model:"-",AW_CombatSlotState(s->e,NULL)?" fighting":"");
        }
    }
    else status();
}
extern void (*aw_ambient_cmd)(void);   /* aw_actors.c: "chim actors ambient" */
void AW_AmbientInit(void) {
    aw_ambient_cmd=AW_AmbientCommand;
    /* the actor record's two hooks (aw_mwhost.c): the scripts' AIWander sets this package; the walk speed is the
     * record's Speed attribute (-1 without one: the stand-in 50) */
    aw_mwscript_wander=AW_AmbientWander;
    aw_mwscript_travel=AW_AmbientTravel;
    aw_mwscript_follow=AW_AmbientFollow;
    aw_mwscript_packages_export=AW_AmbientPackagesExport;
    aw_mwscript_packages_import=AW_AmbientPackagesImport;
    aw_ambient_speed_attribute=AW_MwscriptSpeedAttribute;
    AW_MoveSettingsDefault(&move_defaults);
}
#endif
