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
 * Not done (said in docs/NPC_PATHFINDING.md): door proximity, occupied destinations, swimmers and flyers (stand), the
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

int AW_AmbientOpen(aw_ambient_table_t *t,const unsigned char *d,long size,const unsigned char *profiles,long file_size) {
    long i;unsigned long points,hops,prof;
    memset(t,0,sizeof(*t));
    if(size<AW_AMBIENT_HEADER || AW_AmbientRowsSize(d,file_size)!=size)return 0;
    t->rows=(long)rd32(d+8);points=rd32(d+12);hops=rd32(d+16);prof=rd32(d+20);
    t->multiplier=rd16(d+24);
    if(points>(unsigned long)(file_size/AW_AMBIENT_POINT) || hops>(unsigned long)file_size ||
       prof>(unsigned long)(file_size/AW_AMBIENT_PROFILE))return 0;
    t->points=(long)points;t->hop_bytes=(long)hops;t->profiles=(long)prof;
    t->points_at=size;t->hops_at=t->points_at+t->points*AW_AMBIENT_POINT;t->profiles_at=t->hops_at+t->hop_bytes;
    if(t->profiles_at+t->profiles*AW_AMBIENT_PROFILE!=file_size)return 0;
    t->rows_data=d+AW_AMBIENT_HEADER;t->profile_data=profiles;
    for(i=0;i<t->rows;i++){
        aw_ambient_row_t r;AW_AmbientRow(t,i,&r);
        if(!r.points || !r.destinations || r.destinations>r.points || r.destinations>AW_AMBIENT_MAX_DEST)return 0;
        if(r.first_point+r.points>(unsigned long)t->points)return 0;
        if(r.first_hop+(unsigned long)r.points*r.destinations>(unsigned long)t->hop_bytes)return 0;
        if((long)r.profile>=t->profiles)return 0;
        if(i){
            aw_ambient_row_t q;AW_AmbientRow(t,i-1,&q);
            if(q.ref>r.ref || (q.ref==r.ref && q.hash>=r.hash))return 0;
        }
    }
    return 1;
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
    float t,next_think,last_think,react_at,check_at,remain;int minutes;
    aw_anim_play_t play;
    int skel_first,skel_count;float skel_rate;
    float manual_goal[2];
} slot_t;

int (*aw_ambient_speed_attribute)(edict_t *e);
extern unsigned long aw_sv_move_calls;
int AW_CompanionEdict(edict_t *e);

/* "chim actors ambient on|off|think S|list|reset" (no command or cvar of its own: the resident registry budget).
 * Default OFF until the A/B is recorded; not saved. */
static int ambient_on;
static float think_interval=0.1f;
static aw_ambient_table_t table;
static unsigned char *resident,*profiles;
static FILE *file;long file_base;
static int loaded;              /* 0 not tried, 1 usable, -1 unavailable */
static slot_t slots[SLOTS];
static short slot_of[MAX_EDICTS];   /* slot + 1 per edict */
static model_t *slots_world;
static unsigned long rng=1;
static float scan_at;
static struct {unsigned long thinks,steps,traces,walks,idles,bad_idles,registered,unknown,no_walk,blob_bytes,manual,stuck;double seconds,worst;} st;
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
static int load(void) {
    long size,rows_size;unsigned char head[AW_AMBIENT_HEADER];aw_ambient_table_t probe;
    if(loaded)return loaded>0;
    loaded=-1;
    size=COM_FOpenFile((char *)path,&file);
    if(size<AW_AMBIENT_HEADER || !file){if(file)fclose(file);file=NULL;Con_DPrintf("Ambient table: %s not in this build\n",path);return 0;}
    file_base=ftell(file);
    if(fread(head,1,AW_AMBIENT_HEADER,file)!=AW_AMBIENT_HEADER || (rows_size=AW_AmbientRowsSize(head,size))<0){
        Con_Printf("Ambient table: %s is not AWAM1\n",path);fclose(file);file=NULL;return 0;
    }
    /* outside the Quake heap, once per session: the rows and the idle profiles; the routes are read per actor */
    memset(&probe,0,sizeof(probe));probe.profiles=(long)rd32(head+20);
    resident=(unsigned char *)AW_TryMalloc((unsigned long)rows_size);
    profiles=(unsigned char *)AW_TryMalloc((unsigned long)(probe.profiles*AW_AMBIENT_PROFILE+1));
    if(!resident || !profiles){Con_Printf("Ambient table: no memory for %ld bytes\n",rows_size);unload();loaded=-1;return 0;}
    memcpy(resident,head,AW_AMBIENT_HEADER);
    if((long)fread(resident+AW_AMBIENT_HEADER,1,(size_t)(rows_size-AW_AMBIENT_HEADER),file)!=rows_size-AW_AMBIENT_HEADER ||
       fseek(file,file_base+size-probe.profiles*AW_AMBIENT_PROFILE,SEEK_SET) ||
       (long)fread(profiles,1,(size_t)(probe.profiles*AW_AMBIENT_PROFILE),file)!=probe.profiles*AW_AMBIENT_PROFILE ||
       !AW_AmbientOpen(&table,resident,rows_size,profiles,size)){
        Con_Printf("Ambient table: %s is damaged\n",path);unload();loaded=-1;return 0;
    }
    Con_DPrintf("Ambient table: %ld actors, %ld bytes resident\n",table.rows,rows_size+table.profiles*AW_AMBIENT_PROFILE);
    loaded=1;
    return 1;
}

/* ---- slots ---- */
static void release(slot_t *s,int give_back) {
    edict_t *e=s->e;
    if(give_back && e && !e->free){
        if(s->mover)AW_AnimMover(e,0);
        set_field(e,"aw_moving",0);
    }
    if(s->mem)free(s->mem);
    if(e){int n=NUM_FOR_EDICT(e);if(n>=0 && n<MAX_EDICTS)slot_of[n]=0;}
    memset(s,0,sizeof(*s));
}
static void reset_all(void) {
    int i;
    for(i=0;i<SLOTS;i++)if(slots[i].e)release(&slots[i],0);
    memset(slot_of,0,sizeof(slot_of));slots_world=sv.worldmodel;rng=1;scan_at=0;
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
static slot_t *start(edict_t *e,long row) {
    slot_t *s=free_slot();aw_ambient_row_t r;long pa,pb,ha,hb;int n=NUM_FOR_EDICT(e);
    if(!s || n<0 || n>=MAX_EDICTS)return NULL;
    memset(s,0,sizeof(*s));
    if(row>=0){
        AW_AmbientRow(&table,row,&r);AW_AmbientBlobAt(&table,&r,&pa,&pb,&ha,&hb);
        if(!(s->mem=(unsigned char *)AW_TryMalloc((unsigned long)(pb+hb))))return NULL;
        if(fseek(file,file_base+pa,SEEK_SET) || (long)fread(s->mem,1,(size_t)pb,file)!=pb ||
           fseek(file,file_base+ha,SEEK_SET) || (long)fread(s->mem+pb,1,(size_t)hb,file)!=hb){free(s->mem);s->mem=NULL;return NULL;}
        st.blob_bytes+=(unsigned long)(pb+hb);
        s->pkg.blob=s->mem;s->pkg.points=r.points;s->pkg.destinations=r.destinations;s->pkg.record_distance=r.distance;
        AW_AmbientProfile(&table,r.profile,s->cdf);
        s->flags=r.flags;s->repeat=(unsigned char)((r.flags&AW_AMBIENT_REPEAT)!=0);s->remain=r.duration;
        AW_AmbientAllow(&s->pkg,(r.flags&(AW_AMBIENT_FLYER|AW_AMBIENT_SWIMMER))?0:r.distance);
    }
    s->e=e;s->ref=field(e,"aw_ref",0);VectorCopy(e->v.origin,s->home);
    s->state=S_CHOOSE;s->at=-1;s->can_walk=(unsigned char)can_walk(e);
    if(!s->can_walk && s->pkg.distance){st.no_walk++;}
    s->next_think=s->last_think=s->react_at=(float)sv.time;s->check_at=(float)sv.time+IDLE_CHECK;
    minutes_now(&s->minutes);
    slot_of[n]=(short)(s-slots+1);st.registered++;
    return s;
}
static slot_t *slot_for(edict_t *e) {
    int n=NUM_FOR_EDICT(e);slot_t *s;
    if(n<0 || n>=MAX_EDICTS || !slot_of[n])return NULL;
    s=&slots[slot_of[n]-1];
    if(s->e!=e || s->ref!=field(e,"aw_ref",0)){release(s,0);slot_of[n]=0;return NULL;}
    return s;
}
/* Once a second: actors near the player that have a row get a package (lazy: an actor never near never costs). */
static void scan(edict_t *p) {
    int i;edict_t *e;vec3_t d;
    for(i=1;i<sv.num_edicts;i++){
        long row;float ref;
        e=EDICT_NUM(i);
        if(!is_actor(e) || slot_for(e))continue;
        VectorSubtract(e->v.origin,p->v.origin,d);
        if(fabs(d[0])>REGISTER_RANGE || fabs(d[1])>REGISTER_RANGE || fabs(d[2])>REGISTER_RANGE)continue;
        ref=field(e,"aw_ref",0);
        if(ref<=0 || field(e,"aw_intro_role",0)){slot_of[i]=0;continue;}
        row=AW_AmbientFind(&table,(unsigned long)ref,AW_AmbientHash(source_id(e)));
        if(row<0){st.unknown++;continue;}
        if(!start(e,row))break;
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
static void walk(slot_t *s,float dt) {
    float target[2],dx,dy,len,speed=walk_speed(s),step;vec3_t move;int xyz[3],heading;unsigned long before;
    if(s->manual_walk){target[0]=s->manual_goal[0];target[1]=s->manual_goal[1];}
    else{AW_AmbientPoint(&s->pkg,s->at,xyz,NULL);target[0]=s->home[0]+xyz[0];target[1]=s->home[1]+xyz[1];}
    dx=target[0]-s->e->v.origin[0];dy=target[1]-s->e->v.origin[1];len=(float)AW_PathLength((int)dx,(int)dy);
    if(len<=ARRIVE){
        int next;
        if(s->manual_walk || s->at==s->goal || (next=AW_AmbientHop(&s->pkg,s->at,s->goal))<0){stop_walk(s);s->state=S_CHOOSE;return;}
        s->at=(short)next;return;
    }
    step=speed*dt;if(step>len)step=len;
    move[0]=dx*step/len;move[1]=dy*step/len;move[2]=0;
    heading=AW_PathHeading((int)dx,(int)dy);
    s->e->v.angles[1]=heading*360.0f/AW_PATH_FAN-90;s->e->v.angles[0]=s->e->v.angles[2]=0;
    before=aw_sv_move_calls;
    if(AW_ActorStep(s->e,move,host_frametime>0?host_frametime:dt)){   /* the velocity is moved over one frame */s->stuck=0;st.steps++;walk_frames(s,speed,dt);}
    else{
        if(steplog)log_failed_step(s,move);
        if(++s->stuck>=STUCK_STEPS){st.stuck++;stop_walk(s);s->state=S_CHOOSE;}   /* countBeforeReset */
        else walk_frames(s,0,dt);
    }
    st.traces+=aw_sv_move_calls-before;
}
static void think(slot_t *s,float dt) {
    edict_t *e=s->e;int fighting=AW_CombatSlotState(e,NULL)!=0;
    if(fighting){s->fighting=1;s->mover=0;return;}           /* combat owns it (it restores the model when done) */
    if(s->fighting){s->fighting=0;s->state=S_CHOOSE;s->at=-1;s->manual_walk=0;set_field(e,"aw_moving",0);
                    if(!near_allowed(s)){rejoin(s);}
                    return;}
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
                aw_ambient_row_t r;long row=AW_AmbientFind(&table,(unsigned long)s->ref,AW_AmbientHash(source_id(e)));
                if(s->repeat){if(row>=0){AW_AmbientRow(&table,row,&r);s->remain=r.duration;}}   /* repeat: again */
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
    if(sv.time>=scan_at){scan_at=(float)sv.time+1.0f;scan(p);}
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

/* ---- MWScript AIWander (the interpreter's call) ---- */
int AW_AmbientWander(edict_t *e,int distance,int duration,int hour,const unsigned char idle[8],int repeat) {
    slot_t *s;long row=-1;
    if(!e || e->free || !is_actor(e))return 0;
    if(distance<0)distance=0;
    if(distance>65535)distance=65535;
    if(!(s=slot_for(e))){
        if(load())row=AW_AmbientFind(&table,(unsigned long)field(e,"aw_ref",0),AW_AmbientHash(source_id(e)));
        if(!(s=start(e,row)))return 0;
    }
    if(s->state==S_WALK)stop_walk(s);
    (void)hour;                                 /* stored by OpenMW, read nowhere */
    AW_AmbientIdleProfile(idle,loaded>0?table.multiplier:49151u,s->cdf);
    s->repeat=(unsigned char)(repeat!=0);s->remain=(float)(duration>0?duration:0);s->bad=0;
    if(s->pkg.blob)AW_AmbientAllow(&s->pkg,(unsigned)distance);
    else{s->pkg.distance=(unsigned short)distance;s->pkg.manual=(unsigned char)(distance>0);}
    /* OpenMW starts a stacked package where the actor stands (mInitialActorPosition); the compiled routes are
     * relative to the spawn position, so the start stays there (an AmiWind simplification, docs/NPC_PATHFINDING.md) */
    s->state=S_CHOOSE;s->at=-1;
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
    if((s=slot_for(e))!=NULL){if(done)*done=s->state==S_OFF;return 0;}
    if(load() && AW_AmbientFind(&table,(unsigned long)field(e,"aw_ref",0),AW_AmbientHash(source_id(e)))>=0)return 0;
    return -1;
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
    Con_Printf("  cost: %.3f ms per think, worst frame %.3f ms\n",st.thinks?st.seconds*1000.0/st.thinks:0.0,st.worst*1000.0);
}
/* "chim actors ambient [on|off|think S|list|reset]" (aw_actors.c forwards it; arguments from the fourth word) */
void AW_AmbientCommand(void) {
    const char *a=Cmd_Argc()>3?Cmd_Argv(3):"status";
    if(!strcmp(a,"on") || !strcmp(a,"off")){
        ambient_on=a[1]=='n';
        if(!ambient_on){int i;for(i=0;i<SLOTS;i++)if(slots[i].e)release(&slots[i],1);}
        Con_Printf("Ambient: %s\n",ambient_on?"on":"off");
    }
    else if(!strcmp(a,"think") && Cmd_Argc()>4){
        float v=(float)Q_atof(Cmd_Argv(4));
        think_interval=v<.05f?.05f:v>.5f?.5f:v;
        Con_Printf("Ambient: think every %.2f s\n",think_interval);
    }
    else if(!strcmp(a,"steplog") && Cmd_Argc()>4){
        steplog=aw_actor_step_diag=!strcmp(Cmd_Argv(4),"on");Con_Printf("Ambient: failed-step log %s\n",steplog?"on":"off");
    }
    else if(!strcmp(a,"reset")){memset(&st,0,sizeof(st));Con_Printf("Ambient: counters reset\n");}
    else if(!strcmp(a,"list")){
        int i;
        for(i=0;i<SLOTS;i++)if(slots[i].e){
            slot_t *s=&slots[i];
            Con_Printf("%3d %-24s ref %ld state %d dist %u dests %u/%u cur %u goal %u at %d%s%s\n",i,source_id(s->e),(long)s->ref,
                       s->state,s->pkg.distance,s->pkg.count,s->pkg.destinations,s->pkg.cur,s->goal,s->at,
                       s->pkg.manual?" manual":"",s->can_walk?"":" no-walk");
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
    aw_ambient_speed_attribute=AW_MwscriptSpeedAttribute;
    AW_MoveSettingsDefault(&move_defaults);
}
#endif
