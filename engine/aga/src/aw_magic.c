/* SPDX-License-Identifier: GPL-2.0-or-later
 * Magic effects, the engine glue (aw_magic.h, docs/MAGIC_EFFECTS.md): a spell's look with Quake's machinery.
 *
 * aw_magic_fx 0 (the default): nothing is loaded, spawned or drawn; dbg cast says how to turn it on.
 * aw_magic_fx 1: the effect table (gfx/magic.awm) and its sprites are loaded on the first cast; each phase's
 *   emitters start Quake particles (r_part.c's pool, pt_static / pt_slowgrav, colours from the emitter texture);
 *   the cast glow, the bolt, the hit and the area burst are Quake sprites drawn as temporary entities
 *   (cl_tent.c CL_NewTempEntity, r_sprite.c, aw_sprite_scale); the phase sounds are the game's school sounds.
 * aw_magic_fx 2: the same plus dynamic lights (cl_dlights): the bolt's light (OpenMW gives the bolt a point
 *   light in the effect's colour) and a short flash where it lands. Quake's lights are white and a software
 *   dynamic light rebuilds the surfaces it touches, so it has its own setting.
 *
 * dbg cast NAME [target | touch | self | fail] [area FEET] [repeat]: the player casts NAME's look: the hand glow and
 * the cast at once, the bolt from the hands along the view (target), its hit on an actor it strikes and the area
 * burst where it lands; touch lands within reach, self plays the hit on the player, fail plays only the school's
 * failure sound. Sounds: cast, the bolt's loop following it in flight, hit, area, fail. repeat casts again as each
 * cast ends (for measurements) until dbg cast stop. dbg cast list; dbg cast (status and costs).
 * Placement rules follow OpenMW (apps/openmw/mwmechanics/spellcasting.cpp, character.cpp,
 * mwworld/projectilemanager.cpp); the hand glow sits at two points before the caster's chest, not yet on the hand
 * bones. No magicka, skills, chances or effects on actors: the game logic work. */
#include "quakedef.h"
#include "aw_magic.h"
#include "aw_animkit.h"
#include "aw_tryalloc.h"
#include <math.h>

extern particle_t *active_particles,*free_particles;
extern cvar_t chase_active;
entity_t *CL_NewTempEntity(void);
int AW_UIColor(int r,int g,int b);

#define CASTS 6                 /* casts alive at once */
#define RELEASE .25f            /* seconds from the cast to the bolt leaving the hands */
#define BOLT_LIFE 3.0f          /* a bolt that hits nothing ends after this */
#define TOUCH_REACH 48.0f       /* map units: a touch spell lands within this */
#define LIGHT_KEY 0x4d470       /* dynamic light keys: LIGHT_KEY + cast slot */
#define HIT_GROW 1.6f           /* hit and area sprites grow to this x their size */
#define RING 8                  /* the area burst's ring of sprites */
#define SOUND_ENT 32000         /* the magic sounds' own sound entity: no edict, never the view entity */
#define FAIL_LENGTH 1.0f        /* a failed cast is over after this (its sound plays on) */
#define VIEW_HIT 24.0f          /* a hit on the player's own view stands this far before the eye */
#define VIEW_SHARE .35f         /* ...with this share of its particles and half its sprite size */

static cvar_t aw_magic_fx={"aw_magic_fx","0",true};
enum {MODE_TARGET,MODE_TOUCH,MODE_SELF,MODE_FAIL};
typedef struct {
    int used,fx,mode,repeat,hit_actor,bolt_alive,landed;
    int hit_view;               /* 1: it lands on the player seen from his own eyes (a small burst before the view) */
    float hit_height;           /* the height of the actor it lands on (its orb), 0 unknown */
    int target;                 /* the edict the spell landed on (its shell follows it), 0 none */
    float duration;             /* seconds the hit shell stays on the target (dbg cast ... dur S) */
    int caster;                 /* edict number of the caster: 0 = the player, else an actor casting at the player */
    float release;              /* seconds from the cast to the spell leaving: the spellcast group's release key, or RELEASE */
    int body;                   /* 1: the cast plays around the caster's body (an actor, or the player seen from behind) */
    vec3_t feet;float height;   /* the caster's feet and height (map units) for the body cast */
    float start,area;           /* cl.time of the cast; the area in feet */
    float bolt_start,land;      /* cl.time the bolt left / the spell landed */
    vec3_t eye,right,forward,up,bolt,dir,where,hit;
    float trail_debt;
} cast_t;
static aw_magic_table_t *table;
static int table_state;         /* 0 not tried, 1 loaded, -1 refused */
static char table_why[64];
static model_t *sprites[AW_MAGIC_EFFECTS][AW_MAGIC_PHASES];
static sfx_t *sounds[AW_MAGIC_EFFECTS][AW_MAGIC_PHASES];
static cast_t casts[CASTS];
static double last_time;
static model_t *last_world;
static unsigned long frames,frame_particles,frame_sprites,total_particles,total_sprites,dropped_sprites,dropped_particles;
static double update_seconds;
static unsigned long update_frames;
static float frame_dt;          /* this frame's seconds (AW_MagicUpdate) */

static float frand(void) {return (rand()&32767)/16383.5f-1;}   /* -1 .. 1 */
static void ball(float r[3]) {
    int k;
    for(k=0;k<16;k++){
        r[0]=frand();r[1]=frand();r[2]=frand();
        if(r[0]*r[0]+r[1]*r[1]+r[2]*r[2]<=1)return;
    }
    r[0]=r[1]=0;r[2]=1;
}
static void bolt_sound_stop(int slot) {S_StopSound(SOUND_ENT,slot+1);}
static void clear_casts(void) {
    int i;
    for(i=0;i<CASTS;i++)if(casts[i].used && casts[i].bolt_alive)bolt_sound_stop(i);
    memset(casts,0,sizeof(casts));
}

/* ---- the table, loaded on the first cast ---- */
static void palette_ramps(void) {
    int i,p,e,k;
    for(i=0;i<table->effects;i++)for(p=0;p<AW_MAGIC_PHASES;p++)
        for(e=0;e<table->fx[i].phase[p].emitters;e++){
            aw_magic_emitter_t *m=&table->fx[i].phase[p].em[e];
            for(k=0;k<AW_MAGIC_RAMP;k++)m->index[k]=(unsigned char)AW_UIColor(m->ramp[k][0],m->ramp[k][1],m->ramp[k][2]);
        }
}
static int load_table(void) {
    FILE *f=NULL;int left,n,c,ok=1,first=1;char line[512],why[64];
    if(table_state)return table_state>0;
    table_state=-1;
    left=COM_FOpenFile(AW_MAGIC_FILE,&f);
    if(!f || left<6 || left>262144){if(f)fclose(f);strcpy(table_why,"gfx/magic.awm missing");return 0;}
    table=(aw_magic_table_t *)AW_TryMalloc(sizeof(*table));
    if(!table){fclose(f);strcpy(table_why,"no memory for the table");return 0;}
    why[0]=0;
    while(left>0 && ok){
        n=0;
        while(left>0){
            c=fgetc(f);left--;
            if(c==EOF){left=0;break;}
            if(c=='\n')break;
            if(c=='\r')continue;
            if(c<32 || c>126 || n>=(int)sizeof(line)-1){ok=0;strcpy(why,"bad character or long line");break;}
            line[n++]=(char)c;
        }
        line[n]=0;
        if(!ok)break;
        if(first){if(!AW_MagicHeader(table,line)){ok=0;strcpy(why,"not an AWMG1 table");}first=0;continue;}
        if(!AW_MagicLine(table,line,why,sizeof(why)))ok=0;
    }
    fclose(f);
    if(ok && !AW_MagicCheck(table,why,sizeof(why)))ok=0;
    if(!ok){free(table);table=NULL;sprintf(table_why,"gfx/magic.awm: %.48s",why);return 0;}
    palette_ramps();
    memset(sprites,0,sizeof(sprites));memset(sounds,0,sizeof(sounds));
    table_state=1;return 1;
}
static model_t *sprite_of(int fx,int phase) {
    const aw_magic_phase_t *ph=&table->fx[fx].phase[phase];
    if(!ph->sprite[0])return NULL;
    if(!sprites[fx][phase]){
        int i,p;
        /* the same sprite file is shared by effects and phases: one Mod_ForName per file */
        for(i=0;i<table->effects;i++)for(p=0;p<AW_MAGIC_PHASES;p++)
            if(sprites[i][p] && !strcmp(table->fx[i].phase[p].sprite,ph->sprite)){sprites[fx][phase]=sprites[i][p];return sprites[i][p];}
        sprites[fx][phase]=Mod_ForName((char *)ph->sprite,false);
        if(sprites[fx][phase] && sprites[fx][phase]->type!=mod_sprite)sprites[fx][phase]=NULL;
    }
    return sprites[fx][phase];
}
/* A phase's sound at AT. CHANNEL 0: plays out where it started; channel slot+1: the bolt's own channel, its sound
 * file loops (the image step writes a Quake loop point) until bolt_sound_stop, moved along by S_MoveSound. */
static void sound_on(int fx,int phase,vec3_t at,int channel) {
    const aw_magic_phase_t *ph=&table->fx[fx].phase[phase];
    if(!ph->present || !ph->sound[0])return;
    if(!sounds[fx][phase])sounds[fx][phase]=S_PrecacheSound((char *)ph->sound);
    if(sounds[fx][phase])S_StartSound(SOUND_ENT,channel,sounds[fx][phase],at,1,1);
}
static void sound_at(int fx,int phase,vec3_t at) {sound_on(fx,phase,at,0);}

/* ---- particles and sprites of one frame ---- */
static void particle(const aw_magic_emitter_t *e,const vec3_t centre,const cast_t *c) {
    particle_t *p;float r[3],d[3],speed,life;int k;
    if(!free_particles){dropped_particles++;return;}
    p=free_particles;free_particles=p->next;p->next=active_particles;active_particles=p;
    ball(r);
    for(k=0;k<3;k++)p->org[k]=centre[k]+r[0]*e->jitter[0]*c->right[k]+r[1]*e->jitter[1]*c->forward[k]+r[2]*e->jitter[2]*c->up[k];
    ball(r);
    if(!AW_MagicDirection(e,r,d)){d[0]=d[1]=0;d[2]=1;}
    speed=e->speed+frand()*e->speed_rand;
    for(k=0;k<3;k++)p->vel[k]=speed*(d[0]*c->right[k]+d[1]*c->forward[k]+d[2]*c->up[k]);
    life=e->life+frand()*e->life_rand;if(life<.05f)life=.05f;
    p->die=cl.time+life;p->ramp=0;
    p->color=e->index[(rand()&3)+((rand()&7)==0?4:0)];   /* mostly the bright half of the texture's colours */
    p->type=e->gravity>0?pt_slowgrav:pt_static;
    frame_particles++;
}
static void emit_phase(const cast_t *c,int phase,const vec3_t centre,float from,float to) {
    const aw_magic_phase_t *ph=&table->fx[c->fx].phase[phase];int e,n;
    float share=c->hit_view && (phase==AW_MAGIC_HIT || phase==AW_MAGIC_AREA)?VIEW_SHARE:1;
    for(e=0;e<ph->emitters;e++)
        for(n=AW_MagicEmitBetween(&ph->em[e],from,to,share);n>0;n--)particle(&ph->em[e],centre,c);
}
static void sprite(int fx,int phase,const vec3_t at,float size,int frame) {
    model_t *m=sprite_of(fx,phase);entity_t *e;
    if(!m || !(size>0))return;
    e=CL_NewTempEntity();
    if(!e){dropped_sprites++;return;}
    e->model=m;VectorCopy(at,e->origin);e->frame=frame;e->aw_sprite_scale=size/AW_MAGIC_SPRITE_PIXELS;
    frame_sprites++;
}
/* The orb that wraps a magic user (the caster while casting, the target while the spell lands on it), the
 * maintainer's types to compare (dbg cast orb N): 0 the first prototype (the cast glow sprite, as tall as the
 * actor); 1 the bubble (the effect's own shell texture on a translucent sphere in its colour, AW_MAGIC_BUBBLE);
 * 2 the bubble with small sprites swirling on its radius; 3 the swirling sprites only, more and brighter. Each at
 * full strength for the first half of its time, then fading. */
static int orb_type=2;
#define SWIRL 6                 /* swirling sprites of type 2 (type 3: twice as many) */
#define SWIRL_TURN 2.4f         /* radians a second */
#define SHELL_END .6f           /* a held shell fades over its last seconds */
#define VIEW_VEIL 12.0f         /* the player's own shell, seen from inside: a faint veil this far before the eye */
#define HOLD_DEFAULT 8.0f       /* dbg cast without dur: a ContinuousVfx effect's shell stays this long */
/* How long the hit shell stays on its target: the spell's duration when it has one, else the passing orb. */
static float hit_hold(const cast_t *c) {
    const aw_magic_effect_t *fx=&table->fx[c->fx];
    if(c->duration>0)return c->duration;
    return fx->phase[AW_MAGIC_BUBBLE].present && !c->hit_view?fx->phase[AW_MAGIC_BUBBLE].length:0;
}
static void orb_at(const cast_t *c,const vec3_t centre,float height,float t,float length,int held) {
    const aw_magic_effect_t *fx=&table->fx[c->fx];const aw_magic_phase_t *bub=&fx->phase[AW_MAGIC_BUBBLE];
    int f,i,n,k,bubble=bub->present;
    /* the baked hit model is as wide as SIZE for a standard character (32 map units tall): scaled to this one */
    float size=bubble && bub->sprite_size*height/32.0f>height*1.15f?bub->sprite_size*height/32.0f:height*1.15f;
    float radius=height*.5f;vec3_t at;   /* never smaller than the character it wraps */
    if(!(length>0) || t>length || !(height>0))return;
    /* a shell held for the spell's duration (OpenMW: the hit model loops while the effect lasts) pulses between its
     * two strongest frames and fades at the end; a passing orb fades over its second half */
    if(held)f=t>length-SHELL_END?2+(t>length-SHELL_END*.5f):((int)(t*4)&1);
    else f=t<length*.5f?0:AW_MagicFadeFrame(t-length*.5f,length*.5f);
    if(orb_type==0 || ((orb_type==1 || orb_type==2) && !bubble)){
        float s=fx->phase[AW_MAGIC_CAST].sprite_size>size?fx->phase[AW_MAGIC_CAST].sprite_size:size;
        sprite(c->fx,AW_MAGIC_CAST,centre,AW_MagicGrow(s*.8f,1.3f,t,length),f);
    }else if(orb_type==1 || orb_type==2)
        sprite(c->fx,AW_MAGIC_BUBBLE,centre,held?size:AW_MagicGrow(size*.9f,1.15f,t,length),f);
    if(orb_type<2)return;
    n=orb_type==3?SWIRL*2:SWIRL;
    for(i=0;i<n;i++){
        /* two rings turning opposite ways, rising and sinking a little: the small sprites of the cast's glow */
        /* the table sine (mathlib.c Q_SinCosRad): the C library's sin/cos reach 68040-unimplemented instructions */
        float a=(i&1?-1:1)*SWIRL_TURN*t+i*6.2832f/n,sa,ca,sb,cb;
        Q_SinCosRad(a,&sa,&ca);Q_SinCosRad(t*3+i,&sb,&cb);
        for(k=0;k<3;k++)at[k]=centre[k]+radius*(ca*c->right[k]+sa*c->forward[k]);
        at[2]+=sb*height*.3f;
        sprite(c->fx,AW_MAGIC_CAST,at,fx->phase[AW_MAGIC_CAST].sprite_size*(orb_type==3?.6f:.45f),orb_type==3?0:f);
    }
}
static void light(int slot,const vec3_t at,float radius,float life) {
    dlight_t *dl;
    if((int)aw_magic_fx.value<2)return;
    dl=CL_AllocDlight(LIGHT_KEY+slot);
    VectorCopy(at,dl->origin);dl->radius=radius;dl->die=cl.time+life;dl->decay=0;dl->minlight=8;
}
/* the two hand points before the caster's chest: 20 forward, 7 to each side, 6 down, inside a first-person view
 * (16 forward / 12 down fell just below its bottom edge: FS-UAE session fx1, 2026-10-27) */
#define HAND_FORWARD 20
#define HAND_SIDE 7
#define HAND_DOWN 6
static void hands(const cast_t *c,vec3_t left,vec3_t right_hand) {
    /* a body seen from outside: the hands before its chest, by its height (an actor is about 33 map units tall) */
    float fw=c->body?c->height*.25f:HAND_FORWARD,sd=c->body?c->height*.15f:HAND_SIDE,dn=c->body?c->height*.25f:HAND_DOWN;
    int k;
    for(k=0;k<3;k++){
        left[k]=c->eye[k]+fw*c->forward[k]-sd*c->right[k]-dn*c->up[k];
        right_hand[k]=c->eye[k]+fw*c->forward[k]+sd*c->right[k]-dn*c->up[k];
    }
}
/* The caster's eye and aim: the player along the view, or an actor (c->caster) at the player's chest, its eye at
 * three quarters of its height. 0 when that actor is gone. */
static int aim(cast_t *c) {
    if(!sv.active || !sv_player)return 0;
    if(c->caster>0){
        edict_t *a;vec3_t to;float flat;
        if(c->caster>=sv.num_edicts)return 0;
        a=EDICT_NUM(c->caster);
        if(a->free || a->v.solid!=SOLID_SLIDEBOX)return 0;
        c->body=1;VectorCopy(a->v.origin,c->feet);c->feet[2]+=a->v.mins[2];c->height=a->v.maxs[2]-a->v.mins[2];
        VectorCopy(a->v.origin,c->eye);c->eye[2]+=a->v.mins[2]+(a->v.maxs[2]-a->v.mins[2])*.75f;
        VectorCopy(sv_player->v.origin,to);to[2]+=(sv_player->v.mins[2]+sv_player->v.maxs[2])*.5f;
        VectorSubtract(to,c->eye,c->forward);
        if(VectorNormalize(c->forward)<1)return 0;
        /* right = forward x up(0,0,1), level; up = right x forward */
        flat=(float)sqrt(c->forward[0]*c->forward[0]+c->forward[1]*c->forward[1]);
        if(flat<1e-3f){c->right[0]=1;c->right[1]=c->right[2]=0;}
        else{c->right[0]=c->forward[1]/flat;c->right[1]=-c->forward[0]/flat;c->right[2]=0;}
        CrossProduct(c->right,c->forward,c->up);
        return 1;
    }
    VectorCopy(sv_player->v.origin,c->eye);c->eye[2]+=sv_player->v.view_ofs[2];
    AngleVectors(cl.viewangles,c->forward,c->right,c->up);
    /* seen from behind (the chase camera), the player's own body carries the cast */
    c->body=chase_active.value!=0;
    VectorCopy(sv_player->v.origin,c->feet);c->feet[2]+=sv_player->v.mins[2];
    c->height=sv_player->v.maxs[2]-sv_player->v.mins[2];
    return 1;
}
/* The caster plays its spellcast group (aw_animkit.c AW_AnimKitCast; the spell leaves on the group's release key,
 * rule from OpenMW mwmechanics/character.cpp; a failed cast plays it too); without a table the cast is timed. */
static void animate(cast_t *c) {
    static const char *const variant[]={"target","touch","self","self"};
    edict_t *e=c->caster>0?EDICT_NUM(c->caster):sv_player;
    float r=e?AW_AnimKitCast(e,variant[c->mode]):-1;
    c->release=r>=0 && r<3?r:RELEASE;
}
/* The actor that casts at the player for `dbg cast NAME npc`: the solid actor most in front of the view within 600
 * units (0 when none). */
static int npc_caster(void) {
    int i,best=0;float best_dot=.3f;vec3_t fwd,r,u,d;
    AngleVectors(cl.viewangles,fwd,r,u);
    for(i=1;i<sv.num_edicts;i++){
        edict_t *a=EDICT_NUM(i);float len,dot;
        if(a->free || a==sv_player || a->v.solid!=SOLID_SLIDEBOX)continue;
        VectorSubtract(a->v.origin,sv_player->v.origin,d);
        len=(float)sqrt(DotProduct(d,d));
        if(len<32 || len>600)continue;
        dot=DotProduct(d,fwd)/len;
        if(dot>best_dot){best_dot=dot;best=i;}
    }
    return best;
}
/* A spell that lands on the player seen from his own eyes: the burst stands VIEW_HIT units before the eye, towards
 * where it came from, smaller and with fewer particles (Quake draws a particle bigger the nearer it is: at the eye
 * the burst was a wall of squares, FS-UAE session fx4, 2026-10-27). */
static void view_hit(cast_t *c) {
    vec3_t eye,back;int k;
    if(!sv_player || chase_active.value)return;
    VectorCopy(sv_player->v.origin,eye);eye[2]+=sv_player->v.view_ofs[2];
    for(k=0;k<3;k++)back[k]=c->mode==MODE_TARGET?-c->dir[k]:c->forward[k];
    for(k=0;k<3;k++)c->hit[k]=c->where[k]=eye[k]+VIEW_HIT*back[k];
    c->hit_view=1;
}
/* where the bolt goes this frame: a move from the bolt to its next point, stopped by the world or an actor */
static void fly(cast_t *c,int slot,float dt) {
    vec3_t next;trace_t tr;int k;
    for(k=0;k<3;k++)next[k]=c->bolt[k]+c->dir[k]*table->bolt_speed*dt;
    if(sv.active && sv_player){
        edict_t *from=c->caster>0 && c->caster<sv.num_edicts?EDICT_NUM(c->caster):sv_player;
        tr=SV_Move(c->bolt,vec3_origin,vec3_origin,next,MOVE_NORMAL,from);
        if(tr.fraction<1 || tr.allsolid || tr.startsolid){
            VectorCopy(tr.endpos,c->where);
            c->hit_actor=tr.ent && tr.ent!=sv.edicts && tr.ent->v.solid==SOLID_SLIDEBOX;
            if(c->hit_actor)for(k=0;k<3;k++)c->hit[k]=tr.ent->v.origin[k]+(k==2?(tr.ent->v.mins[2]+tr.ent->v.maxs[2])*.5f:0);
            if(c->hit_actor){c->hit_height=tr.ent->v.maxs[2]-tr.ent->v.mins[2];c->target=NUM_FOR_EDICT(tr.ent);}
            if(c->hit_actor && tr.ent==sv_player)view_hit(c);
            c->bolt_alive=0;c->landed=1;c->land=cl.time;bolt_sound_stop(slot);return;
        }
    }
    VectorCopy(next,c->bolt);
    S_MoveSound(SOUND_ENT,slot+1,c->bolt);
    if(cl.time-c->bolt_start>BOLT_LIFE){
        VectorCopy(c->bolt,c->where);c->bolt_alive=0;c->landed=1;c->land=cl.time;c->hit_actor=0;bolt_sound_stop(slot);
    }
}
static void update_cast(cast_t *c,int slot,float t0,float t1) {
    const aw_magic_effect_t *fx=&table->fx[c->fx];const aw_magic_phase_t *ph;vec3_t lh,rh,mid,at;float age,size,end=0;int k,f;
    hands(c,lh,rh);
    for(k=0;k<3;k++)mid[k]=(lh[k]+rh[k])*.5f;
    /* a failed cast (OpenMW spellcasting.cpp: the roll fails before any effect plays): the school's failure sound
     * at the caster and nothing seen */
    if(c->mode==MODE_FAIL){
        if(t0<=0)sound_at(c->fx,AW_MAGIC_FAIL,c->eye);
        if(t1>FAIL_LENGTH){
            if(c->repeat){c->start=cl.time;}else c->used=0;
        }
        return;
    }
    /* the hand glow (VFX_Hands, textured with the effect's particle texture) and the cast at the caster */
    ph=&fx->phase[AW_MAGIC_HAND];
    if(ph->present){
        if(t1<=ph->length){emit_phase(c,AW_MAGIC_HAND,lh,t0,t1);emit_phase(c,AW_MAGIC_HAND,rh,t0,t1);}
        if(end<ph->length)end=ph->length;
    }
    ph=&fx->phase[AW_MAGIC_CAST];
    if(ph->present){
        if(t1<=ph->length){
            f=AW_MagicFadeFrame(t1,ph->length);
            /* the cast effect wraps the caster (OpenMW mwmechanics/spellcasting.cpp playSpellCastingEffects: the
             * CVFX model on the caster, its root at the feet): the emitters from the feet */
            emit_phase(c,AW_MAGIC_CAST,c->body?c->feet:mid,t0,t1);
            sprite(c->fx,AW_MAGIC_CAST,lh,ph->sprite_size*(c->body?.5f:1),f);
            sprite(c->fx,AW_MAGIC_CAST,rh,ph->sprite_size*(c->body?.5f:1),f);
        }
        if(c->body){
            /* the orb around the caster, from the start of the cast to just after the spell leaves */
            float orb=ph->length>c->release+.5f?ph->length:c->release+.5f;
            if(t1<=orb){
                for(k=0;k<3;k++)at[k]=c->feet[k];
                at[2]+=c->height*.5f;
                orb_at(c,at,c->height,t1,orb,0);
            }
            if(end<orb)end=orb;
        }
        if(end<ph->length)end=ph->length;
    }
    if(t0<=0)sound_at(c->fx,AW_MAGIC_CAST,c->eye);
    /* the bolt (target), the reach (touch) or the caster (self), on the spellcast group's release key */
    if(c->mode==MODE_TARGET){
        if(!c->bolt_alive && !c->landed && t1>=c->release){
            c->bolt_alive=1;c->bolt_start=cl.time;VectorCopy(mid,c->bolt);VectorCopy(c->forward,c->dir);
            sound_on(c->fx,AW_MAGIC_BOLT,c->bolt,slot+1);
        }
        if(c->bolt_alive){
            fly(c,slot,t1-t0);
            ph=&fx->phase[AW_MAGIC_BOLT];
            if(c->bolt_alive && ph->present){
                int e;float due;
                for(e=0;e<ph->emitters;e++){
                    c->trail_debt+=AW_MagicTrailRate(&ph->em[e])*(t1-t0);
                    for(due=c->trail_debt;due>=1;due-=1)particle(&ph->em[e],c->bolt,c);
                    c->trail_debt-=(float)(int)c->trail_debt;
                }
                sprite(c->fx,AW_MAGIC_BOLT,c->bolt,ph->sprite_size,0);
                light(slot,c->bolt,96,.1f);
            }
        }
    }else if(!c->landed && t1>=c->release){
        c->landed=1;c->land=cl.time;
        if(c->mode==MODE_SELF){
            VectorCopy(c->eye,c->where);c->where[2]-=12;c->hit_actor=1;VectorCopy(c->where,c->hit);
            c->hit_height=c->height;c->target=c->caster>0?c->caster:(sv_player?NUM_FOR_EDICT(sv_player):0);
            if(c->body){VectorCopy(c->feet,c->hit);c->hit[2]+=c->height*.5f;VectorCopy(c->hit,c->where);}
            else view_hit(c);
        }
        else{
            vec3_t to;trace_t tr;
            for(k=0;k<3;k++)to[k]=mid[k]+c->forward[k]*TOUCH_REACH;
            VectorCopy(to,c->where);c->hit_actor=0;
            if(sv.active && sv_player){
                tr=SV_Move(mid,vec3_origin,vec3_origin,to,MOVE_NORMAL,sv_player);VectorCopy(tr.endpos,c->where);
                c->hit_actor=tr.ent && tr.ent!=sv.edicts && tr.ent->v.solid==SOLID_SLIDEBOX;
                if(c->hit_actor)for(k=0;k<3;k++)c->hit[k]=tr.ent->v.origin[k]+(k==2?(tr.ent->v.mins[2]+tr.ent->v.maxs[2])*.5f:0);
                if(c->hit_actor){c->hit_height=tr.ent->v.maxs[2]-tr.ent->v.mins[2];c->target=NUM_FOR_EDICT(tr.ent);}
            }
        }
    }
    /* the landing: the hit on an actor; the area burst for a target spell (OpenMW spawns it even with area 0) or an
     * area > 0 */
    if(c->landed){
        float la1=(float)(cl.time-c->land),la0=la1-frame_dt;
        if(la0<0)la0=-1;   /* the landing frame takes everything that starts at 0 */
        if(la0<0){
            if(c->hit_actor)sound_at(c->fx,AW_MAGIC_HIT,c->hit);
            if(c->mode==MODE_TARGET || c->area>0)sound_at(c->fx,AW_MAGIC_AREA,c->where);
        }
        ph=&fx->phase[AW_MAGIC_HIT];
        if(c->hit_actor && ph->present && la1<=ph->length){
            emit_phase(c,AW_MAGIC_HIT,c->hit,la0,la1);
            size=AW_MagicGrow(ph->sprite_size*(c->hit_view?.5f:1),HIT_GROW,la1,ph->length);
            sprite(c->fx,AW_MAGIC_HIT,c->hit,size,AW_MagicFadeFrame(la1,ph->length));
        }
        /* the shell wraps the character the spell lands on (OpenMW mwrender/animation.cpp addEffect: the hit model on
         * the target, looping for the effect's duration when its record has ContinuousVfx, removed when the effect
         * ends: mwmechanics/character.cpp updateContinuousVfx) and follows it as it moves; the player's own view sees
         * it as a faint veil before the eye */
        if(c->hit_actor && c->hit_height>0){
            float len=hit_hold(c),*at3=c->hit;vec3_t now;
            edict_t *t=c->target>0 && c->target<sv.num_edicts?EDICT_NUM(c->target):NULL;
            if(t && !t->free){
                VectorCopy(t->v.origin,now);now[2]+=(t->v.mins[2]+t->v.maxs[2])*.5f;at3=now;
            }
            if(!c->hit_view)orb_at(c,at3,c->hit_height,la1,len,c->duration>0);
            else if(c->duration>0 && sv_player && fx->phase[AW_MAGIC_BUBBLE].present && la1<=len){
                vec3_t eye;
                VectorCopy(sv_player->v.origin,eye);eye[2]+=sv_player->v.view_ofs[2];
                for(k=0;k<3;k++)eye[k]+=VIEW_VEIL*vpn[k];
                sprite(c->fx,AW_MAGIC_BUBBLE,eye,VIEW_VEIL*2.6f,la1>len-SHELL_END?3:2+((int)(la1*4)&1));
            }
        }
        ph=&fx->phase[AW_MAGIC_AREA];
        if((c->mode==MODE_TARGET || c->area>0) && ph->present && la1<=ph->length){
            float scale=AW_MagicAreaScale(c->area),radius=ph->radius*scale,grow;
            static const float ring[RING][2]={{1,0},{.7071f,.7071f},{0,1},{-.7071f,.7071f},{-1,0},{-.7071f,-.7071f},{0,-1},{.7071f,-.7071f}};
            emit_phase(c,AW_MAGIC_AREA,c->where,la0,la1);
            f=AW_MagicFadeFrame(la1,ph->length);
            size=AW_MagicGrow(ph->sprite_size*(scale>1?1+scale*.25f:1)*(c->hit_view?.5f:1),HIT_GROW,la1,ph->length);
            sprite(c->fx,AW_MAGIC_AREA,c->where,size,f);
            if(scale>1 && !c->hit_view){   /* the ring spreads around the player: not drawn across his own view */
                grow=radius*(la1/ph->length);
                for(k=0;k<RING;k++){
                    for(f=0;f<3;f++)at[f]=c->where[f]+grow*(ring[k][0]*c->right[f]+ring[k][1]*c->forward[f]);
                    sprite(c->fx,AW_MAGIC_AREA,at,ph->sprite_size,AW_MagicFadeFrame(la1,ph->length));
                }
            }
            if(la1<.4f)light(slot,c->where,160*(1-la1/.4f)+32,.1f);
        }
        age=(float)(cl.time-c->land);
        if((!c->hit_actor || (age>fx->phase[AW_MAGIC_HIT].length && age>hit_hold(c))) &&
           (!(c->mode==MODE_TARGET || c->area>0) || age>fx->phase[AW_MAGIC_AREA].length) && t1>end){
            if(c->repeat){int fxi=c->fx,mode=c->mode,caster=c->caster;float area=c->area,duration=c->duration;
                memset(c,0,sizeof(*c));c->used=1;c->fx=fxi;c->mode=mode;c->area=area;c->repeat=1;c->start=cl.time;
                c->caster=caster;c->duration=duration;
                if(!aim(c))c->used=0;
                else animate(c);
            }else c->used=0;
        }
    }
}
void AW_MagicUpdate(void) {
    int i;float dt;double t;
    if(!aw_magic_fx.value){
        if(last_world)clear_casts();
        last_world=NULL;return;
    }
    if(cls.state!=ca_connected || !cl.worldmodel || table_state<=0)return;
    if(cl.worldmodel!=last_world || cl.time<last_time){clear_casts();last_world=cl.worldmodel;last_time=cl.time;return;}
    dt=(float)(cl.time-last_time);last_time=cl.time;
    if(!(dt>0))return;
    if(dt>.25f)dt=.25f;
    frame_dt=dt;t=Sys_FloatTime();frame_particles=frame_sprites=0;
    for(i=0;i<CASTS;i++)if(casts[i].used){
        float t1=(float)(cl.time-casts[i].start),t0=t1-dt;
        if(t0<0)t0=-1;   /* the first frame takes everything that starts at 0 */
        update_cast(&casts[i],i,t0,t1);
    }
    frames++;total_particles+=frame_particles;total_sprites+=frame_sprites;
    update_seconds+=Sys_FloatTime()-t;update_frames++;
}

/* ---- the shared effect path (aw_magic.h): particles and sprites for other effects ---- */
int AW_FxParticles(const float at[3],int count,float spread,const float vel[3],float vel_rand,float life,
                   int r,int g,int b,int gravity) {
    int i,k,colour,started=0;
    if(!at || count<=0 || !(life>0))return 0;
    if(count>256)count=256;
    colour=AW_UIColor(r<0?0:r>255?255:r,g<0?0:g>255?255:g,b<0?0:b>255?255:b);
    for(i=0;i<count;i++){
        particle_t *p;
        if(!free_particles)break;
        p=free_particles;free_particles=p->next;p->next=active_particles;active_particles=p;
        for(k=0;k<3;k++){p->org[k]=at[k]+frand()*spread;p->vel[k]=(vel?vel[k]:0)+frand()*vel_rand;}
        p->die=cl.time+life*(1+frand()*.25f);p->ramp=0;p->color=colour;
        p->type=gravity?pt_grav:pt_static;
        started++;
    }
    return started;
}
int AW_FxSprite(struct model_s *model,const float at[3],float world_size,int frame) {
    entity_t *e;
    if(!model || model->type!=mod_sprite || !at || !(world_size>0))return 0;
    if(!(e=CL_NewTempEntity()))return 0;
    e->model=model;VectorCopy(at,e->origin);e->frame=frame;
    /* the sprite's own width: Mod_LoadSpriteModel sets its bounds to +-maxwidth/2 */
    e->aw_sprite_scale=world_size/(model->maxs[0]-model->mins[0]>1?model->maxs[0]-model->mins[0]:AW_MAGIC_SPRITE_PIXELS);
    return 1;
}

/* ---- dbg cast ---- */
static void status(void) {
    int i,alive=0;
    for(i=0;i<CASTS;i++)alive+=casts[i].used;
    Con_Printf("Magic effects: aw_magic_fx %d (0 off, 1 sprites and particles, 2 also their light)\n",(int)aw_magic_fx.value);
    if(table_state>0)Con_Printf("Table: %d effects, bolt speed %.0f; casts alive %d\n",table->effects,table->bolt_speed,alive);
    else if(table_state<0)Con_Printf("Table refused: %s\n",table_why);
    else Con_Printf("Table not loaded yet (the first cast loads it)\n");
    Con_Printf("Last frame: %lu particles started, %lu sprites; %lu frames: %lu particles, %lu sprites, dropped %lu sprites, %lu particles\n",
               frame_particles,frame_sprites,frames,total_particles,total_sprites,dropped_sprites,dropped_particles);
    if(update_frames)Con_Printf("Update cost: %.3f ms a frame on average (spawning only; drawing is in the frame)\n",update_seconds*1000/update_frames);
}
static void command(void) {
    int i,fx,mode=MODE_TARGET,repeat=0,slot=-1,caster=0;float area=0,dur=-1;char *a;
    if(cmd_source!=src_command)return;
    if(Cmd_Argc()<2){status();return;}
    a=Cmd_Argv(1);
    if(!Q_strcasecmp(a,"stop")){clear_casts();Con_Printf("Magic effects: casts stopped.\n");return;}
    if(!Q_strcasecmp(a,"orb")){
        static const char *const types[4]={"the first prototype (the cast glow)","the bubble","the bubble and swirling sprites",
                                          "swirling sprites only"};
        if(Cmd_Argc()==3 && Cmd_Argv(2)[0]>='0' && Cmd_Argv(2)[0]<='3' && !Cmd_Argv(2)[1])orb_type=Cmd_Argv(2)[0]-'0';
        else if(Cmd_Argc()!=2){Con_Printf("Usage: dbg cast orb 0|1|2|3\n");return;}
        Con_Printf("Magic orb type %d: %s\n",orb_type,types[orb_type]);return;
    }
    if(!aw_magic_fx.value){Con_Printf("Magic effects are off: dbg magicfx 1 turns them on (2 adds their light).\n");return;}
    if(!sv.active || svs.maxclients!=1 || !sv_player){Con_Printf("dbg cast: single-player game only.\n");return;}
    if(!load_table()){Con_Printf("Magic effects unavailable: %s\n",table_why);return;}
    if(!Q_strcasecmp(a,"list")){
        for(i=0;i<table->effects;i++)Con_Printf(" %s (%s, effect %d)\n",table->fx[i].name,AW_MagicSchoolName(table->fx[i].school),table->fx[i].mgef);
        return;
    }
    if((fx=AW_MagicFind(table,a))<0){Con_Printf("dbg cast: no effect '%s' (dbg cast list)\n",a);return;}
    for(i=2;i<Cmd_Argc();i++){
        a=Cmd_Argv(i);
        if(!Q_strcasecmp(a,"target"))mode=MODE_TARGET;
        else if(!Q_strcasecmp(a,"touch"))mode=MODE_TOUCH;
        else if(!Q_strcasecmp(a,"self"))mode=MODE_SELF;
        else if(!Q_strcasecmp(a,"fail"))mode=MODE_FAIL;
        else if(!Q_strcasecmp(a,"npc")){
            if(!(caster=npc_caster())){Con_Printf("dbg cast: no actor in front within 600 units\n");return;}
        }
        else if(!Q_strcasecmp(a,"repeat"))repeat=1;
        else if(!Q_strcasecmp(a,"area") && i+1<Cmd_Argc() && AW_MagicNumber(Cmd_Argv(i+1),&area) && area>=0 && area<=100)i++;
        else if(!Q_strcasecmp(a,"dur") && i+1<Cmd_Argc() && AW_MagicNumber(Cmd_Argv(i+1),&dur) && dur>=0 && dur<=120)i++;
        else{Con_Printf("Usage: dbg cast NAME [target | touch | self | fail] [npc] [area FEET] [dur SECONDS] [repeat]; dbg cast list / stop / orb N\n");return;}
    }
    for(i=0;i<CASTS;i++)if(!casts[i].used){slot=i;break;}
    if(slot<0){Con_Printf("dbg cast: %d casts already alive\n",CASTS);return;}
    memset(&casts[slot],0,sizeof(cast_t));
    casts[slot].used=1;casts[slot].fx=fx;casts[slot].mode=mode;casts[slot].repeat=repeat;casts[slot].area=area;
    casts[slot].start=cl.time;casts[slot].caster=caster;
    /* the hit shell's time on the target: dur S, else HOLD_DEFAULT for an effect whose record keeps its hit visual
     * for the duration (ContinuousVfx: shields, levitate, light ...), else the passing orb */
    casts[slot].duration=dur>=0?dur:(table->fx[fx].flags&AW_MAGIC_CONTINUOUS_VFX)?HOLD_DEFAULT:0;
    if(!aim(&casts[slot])){casts[slot].used=0;Con_Printf("dbg cast: the caster is gone\n");return;}
    animate(&casts[slot]);
    if(last_world!=cl.worldmodel){last_world=cl.worldmodel;last_time=cl.time;}
    /* the label on screen (notify line): who casts what */
    if(caster){
        edict_t *e=EDICT_NUM(caster);const char *who=e->v.netname?pr_strings+e->v.netname:"";
        Con_Printf("%s casts %s (%s) at you%s\n",*who?who:"An actor",table->fx[fx].name,
                   AW_MagicSchoolName(table->fx[fx].school),repeat?", repeating":"");
    }else Con_Printf("You cast %s (%s)%s%s\n",table->fx[fx].name,AW_MagicSchoolName(table->fx[fx].school),
                     mode==MODE_FAIL?": the spell fails":"",repeat?", repeating":"");
}
void AW_MagicInit(void) {
    Cvar_RegisterVariable(&aw_magic_fx);
    Cmd_AddCommand("aw_magicfx",command);
}
