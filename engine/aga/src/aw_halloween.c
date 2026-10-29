/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg halloween (aw_halloween.h, docs/HALLOWEEN.md): the Halloween scene. Built on the animation stage
 * (aw_animkit.c, SKEL-ANIM-STAGE-52): the cast stands in a line before the player as the stage's cast does, each
 * actor facing the camera, and plays groups of its own shared table by name; here a beat clock picks the groups: each
 * role (the lead, the dancers, the skeletons) walks its line of steps (aw_halloween_rules.c), every step a whole
 * number of beats, so a role's actors move together and every move starts on a beat.
 *
 * The cast is spawned at run time from the image's halloween.txt (tools/halloween_cast.py): each model is admitted to
 * the precache lists as the inventory admits a dropped item's model (aw_inventory.c inv_model: local single-player
 * only, the local client gets the same slot), each actor an edict of its own, solid nothing, no think; stop frees
 * them. The cast is grounded on ONE floor, the stage's: the floor under the lead's spot found by a trace down, every
 * other actor on the nearest free spot to its place whose floor is that same level (so none stands on another roof
 * level, in the air or in a wall), then settled as the engine settles its residents (AW_NPCFloor); a ground check
 * over the cast is printed.
 *
 * The show opens on a black screen with the greeting box alone for AW_HALLOWEEN_BOX_SECONDS, in silence (the music
 * is held); then the scene appears, its clock starts and the user's own soundtrack, when the image has one, starts
 * with the first beat (dbg ost play halloween). Photo mode, its own notices hidden (aw_photomode_ui 0), hides the HUD.
 * The track starts early, under the greeting, by its own leading silence (the cast file's pre-roll, measured by the
 * builder) plus AW_HALLOWEEN_AUDIO_LEAD (the player's own start delay, measured in the emulator), so its first beat
 * is heard on the first frame of the dance.
 *
 * A cast move sounds as it plays: a skeletal actor crossing the release key of its table's spellcast group
 * ("self/touch/target release", the table's own text keys) plays the game's spell cast sound (AW_SkelCastSound; the
 * animation stage uses it too), so the whoosh is on the hand motion, never on a separate timer.
 *
 * The camera director (AW_HalloweenCamera, called by view.c before the world is drawn) changes shot on bar
 * boundaries: wide, dolly-in, tracking, crane, orbit, close-up; each eye is pulled in front of any wall or roof
 * between it and what it looks at (a trace from the subject, as the orbit camera does: aw_view.c). dbg halloween
 * camera wide locks it to the wide shot. The frame's edges are kept clear too: while a wall or roof lies close beside
 * the eye on a side or the top of the frame, the eye moves in toward its subject (clear_edges).
 *
 * Overlays keep to the corners: the FPS counter, small, at the bottom left (off in the show, on in halloweentest
 * and the benchmark; dbg halloween fps on/off). aw bench halloween (also aw halloweenbench, dbg halloween bench): no
 * greeting, no music change, the scene clock stepping a fixed time a frame for a fixed number of frames (every run
 * draws the same frames), then one result line on the console.
 */
#include "quakedef.h"
#include "amiwind_version.h"
#include "aw_halloween.h"
#include "aw_skel.h"
#include "aw_links.h"
#include "aw_clock.h"
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/execbase.h>
#include <exec/memory.h>
#endif

typedef struct {edict_t *e;int role,mirror,group,frame;const aw_skel_table_t *table;} hw_actor_t;
static struct {
    int on,version,count,photo,fps,locked,bench,frames,close_actor,close_shot,intro,music_held,music_checked,
        music_started;
    double started,last;float beat,now,photo_ui,music_was,floor;model_t *world;
    vec3_t eye0,forward,right,angles0,centre;float fit,close_fit;
    aw_hw_cast_t cast;
    hw_actor_t actor[AW_HALLOWEEN_MAX];
    struct {int step,steps,lead;double start;float span;const aw_hw_step_t *line;} role[AW_HW_ROLES];
} hw;
static float bench_times[AW_HALLOWEEN_BENCH_FRAMES];
static char model_names[AW_HALLOWEEN_MAX_ROWS][AW_HALLOWEEN_PATH],actor_names[AW_HALLOWEEN_MAX_ROWS][32];
static int model_names_used;
static model_t *names_world;
static char hw_class[]="aw_halloween";
/* The player's own start delay: from the custom play command to the track's first sound at the speaker, measured in
 * the emulator (27 October 2026, the v0.0.53 platform takes: the onset came 1.22 to 1.23 s after the cut for a track
 * whose leading silence is 1.07 s, so 0.15 to 0.17 s). The scene starts the track that much earlier too. A constant,
 * not a setting: it is the player's property, not the user's choice, and a setting would cost a resident cvar slot
 * (tests/resident_registry_budget.json). */
#define AW_HALLOWEEN_AUDIO_LEAD 0.16f

static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
/* A cast model's precache slot, admitted during play (aw_inventory.c inv_model's way), or 0. */
static int admit(const char *path) {
    int i;model_t *m;
    if(names_world!=sv.worldmodel){names_world=sv.worldmodel;model_names_used=0;}
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],path))return i;
    if(i>=MAX_MODELS || model_names_used>=AW_HALLOWEEN_MAX_ROWS)return 0;
    m=Mod_ForName((char *)path,false);
    if(!m || m->type!=mod_alias || !Cache_Check(&m->cache))return 0;
    strcpy(model_names[model_names_used],path);
    sv.model_precache[i]=model_names[model_names_used++];sv.models[i]=m;
    if(cls.state==ca_connected)cl.model_precache[i]=m;
    return i;
}
/* A free edict for one more actor (aw_inventory.c's rule): the scene takes no slot the map gate reserves, so it
 * leaves an actor out rather than meet ED_Alloc's "no free edicts". */
static int edict_available(void) {
    int i;edict_t *e;
    for(i=svs.maxclients+1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free && (e->freetime<2 || sv.time-e->freetime>.5))return 1;
    }
    return sv.num_edicts<MAX_EDICTS-8;
}
static const aw_skel_table_t *table_of(int index) {
    model_t *m=index>0 && index<MAX_MODELS?sv.models[index]:NULL;const aliashdr_t *h;
    if(!m || m->type!=mod_alias)return NULL;
    h=(const aliashdr_t *)Mod_Extradata(m);
    return h && h->aw_skel?(const aw_skel_table_t *)h->aw_skel_table:NULL;
}

/* ---- the cast sound: the game's spell cast sounds on the spellcast group's release keys ---- */
static const char *const cast_sounds[]={"aw/cast/destruction.wav","aw/cast/alteration.wav","aw/cast/illusion.wav",
    "aw/cast/conjuration.wav","aw/cast/mysticism.wav","aw/cast/restoration.wav"};
#define CAST_SOUNDS ((int)(sizeof(cast_sounds)/sizeof(cast_sounds[0])))
#define CAST_BOLT "aw/cast/bolt.wav"
static int cast_next;
/* The spell cast sound on a skeletal actor's spellcast release keys between table frames FROM (exclusive) and TO
 * (inclusive); aw_animkit.c (the animation stage) declares and uses it too. */
void AW_SkelCastSound(edict_t *e,const aw_skel_table_t *t,int group,int from,int to);
/* A sound's precache slot during play (as admit does for models; the local client loads it at once), or 0. */
static int has_sound(const char *path) {
    char full[MAX_QPATH+8];FILE *f=NULL;
    if(strlen(path)+7>=sizeof(full))return 0;
    sprintf(full,"sound/%s",path);
    COM_FOpenFile(full,&f);if(!f)return 0;
    fclose(f);return 1;
}
static int admit_sound(const char *path) {
    int i;
    for(i=1;i<MAX_SOUNDS && sv.sound_precache[i];i++)if(!strcmp(sv.sound_precache[i],path))return i;
    if(i>=MAX_SOUNDS)return 0;
    sv.sound_precache[i]=(char *)path;
    if(cls.state==ca_connected)cl.sound_precache[i]=S_PrecacheSound((char *)path);
    return i;
}
void AW_SkelCastSound(edict_t *e,const aw_skel_table_t *t,int group,int from,int to) {
    static const char *const keys[3]={"self release","touch release","target release"};
    aw_skel_group_t g;int k,f;
    if(!e || !t || group<0 || group>=t->groups || to<=from)return;
    AW_SkelGroupAt(t,group,&g);
    if(Q_strncasecmp(g.name,"spellcast",9) && Q_strncasecmp(g.name+(g.name[1]==':'?2:0),"spellcast",9))return;
    for(k=0;k<3;k++){
        f=AW_SkelKeyFrame(t,group,keys[k]);
        if(f<0 || f<=from || f>to)continue;
        /* one school after another; a target cast (a bolt) with the bolt sound */
        {const char *s=k==2 && has_sound(CAST_BOLT)?CAST_BOLT:cast_sounds[cast_next++%CAST_SOUNDS];
         if(has_sound(s) && admit_sound(s))SV_StartSound(e,0,(char *)s,200,1.0f);}
    }
}

/* ---- the stage floor ---- */
/* The floor under (x, y) within DOWN below z+UP: 1 and its height in *z when it is walkable ground. */
static int floor_at(const vec3_t at,float up,float down,float *z,edict_t *pass) {
    vec3_t a,b;trace_t tr;
    VectorCopy(at,a);VectorCopy(at,b);a[2]+=up;b[2]-=down;
    tr=SV_Move(a,vec3_origin,vec3_origin,b,MOVE_NOMONSTERS,pass);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<AW_WALKABLE_Z)return 0;
    *z=tr.endpos[2];return 1;
}

/* An eye with a clear view of LOOK: when a wall or roof lies between them, the eye first rises a little (up to 32
 * units: take 3, pulled straight in, lost the outer dancers; take 4, raised up to 80, saw them tiny under a sky of
 * fog), and only then comes in front of the obstacle. */
static void clear_eye(vec3_t look,vec3_t eye,edict_t *p) {
    trace_t t;vec3_t d;int k;
    for(k=0;k<3;k++){
        t=SV_Move(look,vec3_origin,vec3_origin,eye,MOVE_NOMONSTERS,p);
        if(t.fraction>=1 && !t.startsolid && !t.allsolid)return;
        if(k<2)eye[2]+=16;
    }
    if(t.fraction<1){VectorSubtract(look,t.endpos,d);VectorNormalize(d);VectorMA(t.endpos,4,d,eye);}
}

/* The frame's edges clear of walls and roofs: clear_eye keeps the line to LOOK open, but a wall or roof beside the
 * eye still filled a side of the frame with a dark wedge (the v0.0.53 platform takes: the tracking, orbit and crane
 * shots by the ruin's walls). While an edge ray (AW_HalloweenEdgeRays, EDGE_NEAR units) hits something, the eye moves
 * EDGE_STEP units toward LOOK along the open line, never nearer than EDGE_MIN. */
#define EDGE_NEAR 64.f
#define EDGE_STEP 12.f
#define EDGE_MIN 48.f
static void clear_edges(vec3_t look,vec3_t eye,edict_t *p) {
    float ends[AW_HW_EDGE_RAYS][3];vec3_t d;trace_t t;int k,i,hit;float dist;
    for(k=0;k<16;k++){
        AW_HalloweenEdgeRays(eye,look,r_refdef.fov_x,r_refdef.fov_y,EDGE_NEAR,ends);
        for(hit=0,i=0;i<AW_HW_EDGE_RAYS && !hit;i++){
            t=SV_Move(eye,vec3_origin,vec3_origin,ends[i],MOVE_NOMONSTERS,p);
            hit=t.fraction<1 || t.startsolid || t.allsolid;
        }
        if(!hit)return;
        VectorSubtract(look,eye,d);dist=VectorNormalize(d);
        if(dist-EDGE_STEP<EDGE_MIN)return;
        VectorMA(eye,EDGE_STEP,d,eye);
    }
}

static void restore_settings(void) {
    if(hw.photo)AW_PhotoModeSetQuiet(0);
    Cvar_SetValue("aw_photomode_ui",hw.photo_ui);
    /* the custom OST player gives the playlist back */
    if(hw.music_held){AW_MusicCustomStop();hw.music_held=0;}
}
/* The scene's hour: sunset, held for the whole scene so the sky, the sun and the fog keep the game's own sunset
 * colours for this spot (aw_wait.c "sunset" is 19:00; no tint of our own). */
#define SUNSET_HOUR 19
static void hold_sunset(void) {AW_ClockSetTime(SUNSET_HOUR,0);}
static void stop(int quiet) {
    int i;
    for(i=0;i<hw.count;i++)if(hw.actor[i].e && !hw.actor[i].e->free && hw.world==sv.worldmodel)ED_Free(hw.actor[i].e);
    if(hw.on)restore_settings();
    if(hw.on && !quiet)Con_Printf("Halloween scene stopped.\n");
    hw.on=hw.count=hw.photo=hw.bench=hw.intro=0;
}

static float group_seconds(const aw_skel_table_t *t,int g) {
    aw_skel_group_t s;
    if(!t || g<0 || g>=t->groups || !(t->rate>0))return 1;
    AW_SkelGroupAt(t,g,&s);
    return (float)(s.last-s.first+1)/t->rate;
}
static int find_group(const aw_skel_table_t *t,const char *name,int mirror) {
    char mirrored[32];int g=-1;
    if(!t)return -1;
    if(mirror){AW_HalloweenMirror(name,mirrored);g=AW_SkelGroup(t,mirrored);}
    if(g<0)g=AW_SkelGroup(t,name);
    if(g<0)g=AW_SkelGroup(t,"idle");      /* a group the table lacks: the idle (OpenMW falls back so too) */
    return g;
}
/* A role's next step: every actor of it takes the step's group; the step's length comes from the role's first
 * actor (so the role keeps together) in whole beats. */
static void begin_step(int r) {
    const aw_hw_step_t *s=&hw.role[r].line[hw.role[r].step];int i;
    for(i=0;i<hw.count;i++)if(hw.actor[i].role==r){
        hw.actor[i].group=find_group(hw.actor[i].table,s->group,hw.actor[i].mirror);hw.actor[i].frame=-1;}
    i=hw.role[r].lead;
    hw.role[r].span=(float)AW_HalloweenBeats(s,group_seconds(hw.actor[i].table,hw.actor[i].group),hw.beat)*hw.beat;
}

static int read_cast(void) {
    static char text[1024];FILE *f=NULL;int n=COM_FOpenFile(AW_HALLOWEEN_CAST_FILE,&f);
    if(!f){Con_Printf("Halloween scene: this image has no cast (%s; built with --halloween).\n",AW_HALLOWEEN_CAST_FILE);return 0;}
    if(n<=0 || n>=(int)sizeof(text) || fread(text,1,n,f)!=(size_t)n){fclose(f);Con_Printf("Halloween scene: the cast file is unreadable.\n");return 0;}
    fclose(f);text[n]=0;
    if(!AW_HalloweenReadCast(text,&hw.cast)){Con_Printf("Halloween scene: the cast file is not valid.\n");return 0;}
    return 1;
}

/* The stage platform (take 5: the automatic search found a storey below it and stood the cast off the platform):
 * the platform is the floor the animation stage's line stood on in the stage videos, at the player's feet level on
 * the Balmora arrival roof, 80 ahead and up to 56 to each side (aw_animkit.c stage: a short trace from 16 above the
 * feet to 32 below). Each slot is that fixed spot (aw_halloween_rules.c AW_HalloweenLayout); its floor is found by
 * the same short trace only, never a lower storey. 1 and *out filled. */
static int stage_spot(edict_t *p,const aw_hw_slot_t *s,vec3_t forward,vec3_t right,vec3_t out) {
    vec3_t spot;float z,feet=p->v.origin[2]+p->v.mins[2];
    VectorMA(p->v.origin,s->ahead,forward,spot);VectorMA(spot,s->right,right,spot);
    spot[2]=hw.floor;(void)feet;
    if(!floor_at(spot,16,32,&z,p) || z-hw.floor>4 || hw.floor-z>4)return 0;
    spot[2]=z;VectorCopy(spot,out);
    return 1;
}
/* The guard over a placed actor: how far its spot is from the platform's edge (the nearest of eight directions where
 * the floor is no longer the platform's: none within 32 below, or a floor more than 4 units from its height), up to
 * 64. A probe that starts inside a solid object standing on the platform (a railing, a post: the platform grid's
 * solid cells) is no edge: it is passed over (take 6: one such line beside a dancer read as the edge). */
static float edge_distance(edict_t *p,const vec3_t at) {
    int k,r;float best=64;vec3_t probe,a2,b2;trace_t t;
    for(k=0;k<8;k++){
        float a=(float)k*(float)M_PI/4,c=Q_CosRad(a),s=Q_SinRad(a);
        for(r=4;r<=64;r+=4){
            VectorCopy(at,probe);probe[0]+=c*r;probe[1]+=s*r;
            VectorCopy(probe,a2);VectorCopy(probe,b2);a2[2]+=16;b2[2]-=32;
            t=SV_Move(a2,vec3_origin,vec3_origin,b2,MOVE_NOMONSTERS,p);
            if(t.startsolid || t.allsolid)continue;
            if(t.fraction>=1 || t.endpos[2]-hw.floor>4 || hw.floor-t.endpos[2]>4){if(r-4<best)best=(float)(r-4);break;}
        }
    }
    return best;
}

static void start(int version,int bench,int fps) {
    edict_t *p=player(),*e;aw_hw_slot_t slot[AW_HALLOWEEN_MAX];int index[AW_HALLOWEEN_MAX_ROWS],by_role[AW_HW_ROLES][AW_HALLOWEEN_MAX_ROWS];
    int count[AW_HW_ROLES]={0,0,0},i,n,left=0,grounded=0;vec3_t view,forward,right,up,spot;float z;
    if(!p || cls.state!=ca_connected){Con_Printf("Halloween scene: start the local scene first.\n");return;}
    stop(1);
    if(!read_cast())return;
    for(i=0;i<hw.cast.rows;i++){
        index[i]=admit(hw.cast.row[i].model);
        if(!index[i] || !table_of(index[i])){
            Con_Printf("Halloween scene: %s (%s) is %s; left out.\n",hw.cast.row[i].name,hw.cast.row[i].model,
                       index[i]?"not a skeletal model":"missing or full");
            continue;
        }
        strcpy(actor_names[i],hw.cast.row[i].name);
        by_role[hw.cast.row[i].role][count[hw.cast.row[i].role]++]=i;
    }
    if(version==AW_HW_WITH_LEAD && !count[AW_HW_LEAD]){
        Con_Printf("Halloween scene: no Dagoth Ur in this cast: the skeletons-only version.\n");version=AW_HW_SKELETONS;
    }
    n=AW_HalloweenLayout(version,count[AW_HW_LEAD],count[AW_HW_DANCER],count[AW_HW_SKELETON],slot);
    if(!n){Con_Printf("Halloween scene: no skeleton in the cast.\n");return;}
    VectorCopy(cl.viewangles,view);view[0]=view[2]=0;AngleVectors(view,forward,right,up);
    VectorCopy(p->v.origin,hw.eye0);hw.eye0[2]+=p->v.view_ofs[2];
    VectorCopy(forward,hw.forward);VectorCopy(right,hw.right);VectorCopy(cl.viewangles,hw.angles0);hw.angles0[2]=0;
    /* the stage floor: the platform at the player's feet level under the middle of the line (a short trace only:
     * never the storey below it) */
    VectorMA(p->v.origin,AW_HALLOWEEN_STAGE_AHEAD,forward,spot);spot[2]=p->v.origin[2]+p->v.mins[2];
    if(!floor_at(spot,48,256,&z,p)){Con_Printf("Halloween scene: no floor before you; face the stage.\n");return;}
    hw.floor=z;
    /* the platform's geometry, measured once: the floor height on a grid before the player (ahead 40..200, right
     * -80..80, 8 units apart; a long trace down from above the feet), relative to the stage floor, for the fixed
     * spots (HALLOWEEN-SCENE-53) */
    {int a,r,len;char row[256];
     Con_Printf("Halloween stage grid: feet %.1f, stage floor %.1f; rows ahead 40..200, columns right -80..80 (floor - stage, '.' none)\n",
                p->v.origin[2]+p->v.mins[2],hw.floor);
     for(a=40;a<=200;a+=8){
        len=sprintf(row,"%3d:",a);
        for(r=-80;r<=80;r+=8){
            vec3_t g;float gz;
            VectorMA(p->v.origin,(float)a,forward,g);VectorMA(g,(float)r,right,g);g[2]=p->v.origin[2]+p->v.mins[2];
            if(floor_at(g,48,256,&gz,p))len+=sprintf(row+len," %3d",(int)(gz-hw.floor));else len+=sprintf(row+len,"   .");
        }
        Con_Printf("%s\n",row);
     }}
    hw.world=sv.worldmodel;hw.version=version;hw.count=0;
    hw.beat=60.f/((float)hw.cast.bpm10/10.f);
    for(i=0;i<n;i++){
        int row=by_role[slot[i].role][slot[i].model],mi=index[row];hw_actor_t *a=&hw.actor[hw.count];
        if(!edict_available()){Con_Printf("Halloween scene: the map has no room for more actors (%d placed).\n",hw.count);break;}
        if(!stage_spot(p,&slot[i],forward,right,spot)){left++;continue;}
        e=ED_Alloc();
        e->v.classname=hw_class-pr_strings;e->v.netname=actor_names[row]-pr_strings;
        e->v.model=sv.model_precache[mi]-pr_strings;e->v.modelindex=(float)mi;
        e->v.solid=SOLID_NOT;e->v.movetype=MOVETYPE_NONE;e->v.think=0;e->v.nextthink=0;e->v.frame=0;
        VectorCopy(spot,e->v.origin);
        /* facing the player: a converted character faces its local +Y */
        e->v.angles[0]=e->v.angles[2]=0;e->v.angles[1]=anglemod(cl.viewangles[1]+90);
        SV_LinkEdict(e,false);
        /* settled as the engine settles its residents (bounded snap onto the floor under it) */
        AW_NPCFloor(e);
        a->e=e;a->role=slot[i].role;a->table=table_of(mi);a->group=-1;a->frame=-1;
        /* around the lead the left side mirrors the right; the skeletons' own line dance is in unison */
        a->mirror=version==AW_HW_WITH_LEAD && slot[i].right<0;
        hw.count++;
    }
    /* the ground check over the cast: every actor's feet on the stage platform, inside its edges; per actor its
     * position, the floor under it and its distance to the platform's edge */
    for(i=0;i<hw.count;i++){
        float zz=0,edge;edict_t *x=hw.actor[i].e;int on;
        on=floor_at(x->v.origin,8,16,&zz,x) && zz-hw.floor<=4 && hw.floor-zz<=4 && x->v.origin[2]-zz<=1;
        edge=edge_distance(p,x->v.origin);
        if(on && edge>=4)grounded++;
        Con_Printf("Halloween stage %d: %s at %.0f %.0f %.0f, floor %.1f (stage %.1f), edge %.0f%s\n",i+1,pr_strings+x->v.netname,
                   x->v.origin[0],x->v.origin[1],x->v.origin[2],zz,hw.floor,edge,on && edge>=4?"":" (OFF THE STAGE: CHECK FAILED)");
    }
    if(!hw.count){Con_Printf("Halloween scene: no room on the stage floor before you.\n");return;}
    /* the camera's start: the whole cast in frame, looking down at its middle (the first frame after the greeting
     * and the wide shot); every other shot moves from it */
    {vec3_t c,d;float half=0,h;int k;
     c[0]=c[1]=c[2]=0;
     for(k=0;k<hw.count;k++)VectorAdd(c,hw.actor[k].e->v.origin,c);
     VectorScale(c,1.f/hw.count,c);
     for(k=0;k<hw.count;k++){VectorSubtract(hw.actor[k].e->v.origin,c,d);h=DotProduct(d,right);if(h<0)h=-h;if(h>half)half=h;}
     c[2]=hw.floor+22;
     AW_HalloweenFrameCast(c,half+10,28,forward,r_refdef.fov_x,r_refdef.fov_y,hw.eye0);   /* +10: an actor's half width */
     VectorCopy(c,hw.centre);VectorSubtract(hw.eye0,c,d);hw.fit=Length(d);
     /* the close-up: one dancer alone, head to feet */
     {vec3_t one;AW_HalloweenFrameCast(c,12,22,forward,r_refdef.fov_x,r_refdef.fov_y,one);VectorSubtract(one,c,d);hw.close_fit=Length(d);}
     /* never inside or behind a wall or a roof */
     clear_eye(c,hw.eye0,p);
     AW_HalloweenAim(hw.eye0,c,hw.angles0);}
    for(i=0;i<AW_HW_ROLES;i++){
        int k;
        hw.role[i].steps=AW_HalloweenLine(i,&hw.role[i].line);hw.role[i].step=0;hw.role[i].start=0;hw.role[i].lead=-1;
        for(k=0;k<hw.count && hw.role[i].lead<0;k++)if(hw.actor[k].role==i)hw.role[i].lead=k;
        if(hw.role[i].lead>=0)begin_step(i);
    }
    hw.on=1;hw.bench=bench;hw.frames=0;hw.fps=fps || bench;hw.close_shot=-1;hw.now=0;
    /* the show opens on the greeting, alone on black and in silence; the bench has none */
    hw.intro=!bench;
    hw.started=realtime+(hw.intro?AW_HALLOWEEN_BOX_SECONDS:0);hw.last=realtime;
    hw.photo_ui=Cvar_VariableValue("aw_photomode_ui");Cvar_SetValue("aw_photomode_ui",0);
    /* photo mode for the clean screen, but the game's own fog of this spot kept (photo mode's aw_photomode_nofog
     * would switch it off) */
    {float fog=Cvar_VariableValue("aw_fog");
     hw.photo=0;if(!AW_PhotoModeActive()){AW_PhotoModeSetQuiet(1);hw.photo=1;}
     Cvar_SetValue("aw_fog",fog);}
    hold_sunset();
    /* the custom OST player holds the playlist for the whole scene: no OST track at any point; the custom track
     * (when the image has one) starts with the first beat */
    AW_MusicCustomHold();hw.music_held=1;hw.music_checked=0;
    hw.music_started=0;
    if(bench){AW_MusicCustomPlay();hw.music_started=1;}  /* the benchmark has no greeting: the custom track at once */
    /* one line per cast member: who, the table (its view), the group playing at the start */
    for(i=0;i<hw.count;i++){
        hw_actor_t *a=&hw.actor[i];aw_skel_group_t g;const char *own="";
        if(a->table && a->group>=0)AW_SkelGroupAt(a->table,a->group,&g);else strcpy(g.name,"?");
        if(a->role==AW_HW_DANCER)own=!Q_strncasecmp(g.name,"d:",2)?" (her own dance, anim_dancingGirl)":" (NOT her own dance: CHECK FAILED)";
        Con_Printf("Halloween cast %d: %s, %s, group %s%s\n",i+1,pr_strings+a->e->v.netname,
                   a->role==AW_HW_LEAD?"his own table":a->role==AW_HW_DANCER?"humanoid table, own-animation view":"humanoid table",
                   g.name,own);
    }
    Con_Printf("Halloween %s: %s, %d actors at %d.%d BPM%s; ground check: %d of %d feet on the stage floor%s%s.\n",
               bench?"bench":"scene",version==AW_HW_WITH_LEAD?"Dagoth Ur and his dancers":"the skeletons",hw.count,
               hw.cast.bpm10/10,hw.cast.bpm10%10,hw.cast.soundtrack && !bench?", your soundtrack":"",grounded,hw.count,
               left?", some left out (no free spot on that floor)":"",grounded==hw.count?"":" (CHECK FAILED)");
}

static void bench_result(void) {
    aw_hw_bench_t b;unsigned long fast=0;int cpu=0;
    AW_HalloweenBenchFigures(bench_times,hw.frames,&b);
#ifdef AMIGA
    fast=(unsigned long)AvailMem(MEMF_FAST|MEMF_TOTAL)/(1024UL*1024UL);
    {unsigned attn=SysBase->AttnFlags;cpu=attn&(1u<<7)?60:attn&(1u<<3)?40:attn&(1u<<2)?30:attn&(1u<<1)?20:0;}
#endif
    Con_Printf("HALLOWEEN BENCH %s: avg %.1f fps, min %.1f, 1%% low %.1f, %d frames, %.1f s, Fast RAM %lu MB, CPU 680%02d, %s\n",
               hw.version==AW_HW_WITH_LEAD?"dagoth":"skeletons",b.average,b.minimum,b.low1,b.frames,b.seconds,fast,cpu,
               AMIWIND_TITLE);
}

void AW_HalloweenTick(void) {
    double dt;int i,r;
    if(!hw.on)return;
    if(!sv.active || hw.world!=sv.worldmodel){hw.on=hw.count=0;restore_settings();return;}   /* a new map: its edicts are gone */
    dt=realtime-hw.last;hw.last=realtime;
    if(hw.bench){
        /* the frame just drawn (the first one is the scene's own start); then the fixed step */
        if(hw.frames>0)bench_times[hw.frames-1]=(float)dt;
        if(hw.frames>=AW_HALLOWEEN_BENCH_FRAMES){bench_result();stop(1);return;}
        hw.now=(float)hw.frames*AW_HALLOWEEN_BENCH_STEP;hw.frames++;
    }else{
        hw.now=(float)(realtime-hw.started);
        /* the custom track starts under the greeting by its pre-roll (its own leading silence and the player's start
         * delay), so the first beat is heard as the scene appears */
        if(hw.intro && !hw.music_started &&
           hw.now>=-AW_HalloweenPreroll(hw.cast.soundtrack?hw.cast.preroll_ms:0,AW_HALLOWEEN_AUDIO_LEAD,
                                        AW_HALLOWEEN_BOX_SECONDS)){
            AW_MusicCustomPlay();hw.music_started=1;
            Con_Printf("Halloween music: started %.2f s before the dance (pre-roll %d ms, lead %.2f s)\n",-hw.now,
                       hw.cast.preroll_ms,(double)AW_HALLOWEEN_AUDIO_LEAD);
        }
        if(hw.intro && hw.now>=0){
            /* the greeting is over: the scene appears; the custom track already runs (or starts now) */
            hw.intro=0;hw.started=realtime;hw.now=0;
            if(!hw.music_started){AW_MusicCustomPlay();hw.music_started=1;}
        }
        if(hw.now<0)hw.now=0;
        /* the scene's music check, once, a second into the dance: what is playing is the custom track (or silence
         * in an image without one), never a playlist track */
        if(!hw.intro && !hw.music_checked && hw.now>1){
            int id=AW_MusicCustomPlaying();hw.music_checked=1;
            if(id>=0)Con_Printf("Halloween music playing: track %02ld (custom)\n",(long)id);
            else Con_Printf("Halloween music: %s\n",hw.cast.soundtrack?"the custom track is NOT playing (CHECK FAILED)":
                            "no custom track in this image: silence (no OST track)");
        }
    }
    hold_sunset();
    for(r=0;r<AW_HW_ROLES;r++){
        if(hw.role[r].lead<0)continue;
        /* the next step starts where the last one ended: the beat grid never drifts */
        while(hw.now>=hw.role[r].start+hw.role[r].span && hw.role[r].span>0){
            hw.role[r].start+=hw.role[r].span;
            hw.role[r].step=(hw.role[r].step+1)%hw.role[r].steps;
            begin_step(r);
        }
    }
    for(i=0;i<hw.count;i++){
        hw_actor_t *a=&hw.actor[i];aw_skel_group_t g;int play,f;
        if(!a->e || a->e->free || !a->table || a->group<0)continue;
        AW_SkelGroupAt(a->table,a->group,&g);
        r=a->role;play=hw.role[r].line[hw.role[r].step].play;
        a->e->v.frame=AW_HalloweenFrame(g.first,g.last,a->table->rate,(float)(hw.now-hw.role[r].start),hw.role[r].span,play);
        f=(int)a->e->v.frame;
        /* the cast whoosh on the move's own release key (forward play only; not during the greeting) */
        if(!hw.intro && play==AW_HW_FIT && a->frame>=0)AW_SkelCastSound(a->e,a->table,a->group,a->frame,f);
        a->frame=f;
    }
}

/* ---- the camera director ---- */
static void chest(const edict_t *e,vec3_t out) {VectorCopy(e->v.origin,out);out[2]+=18;}
static int big_move(int i) {
    const char *g=hw.role[hw.actor[i].role].line[hw.role[hw.actor[i].role].step].group;
    return !strcmp(g,"spellcast") || !strncmp(g,"knock",5) || !strncmp(g,"death",5);
}
/* the close-up's dancer, chosen when the shot begins: one in a big move (a cast, a fall) first, a different one
 * each time */
static int pick_close(void) {
    int pass,i,k,best=-1;
    for(pass=0;pass<2 && best<0;pass++)
        for(k=1;k<=hw.count && best<0;k++){
            i=(hw.close_actor+k)%hw.count;
            if(hw.actor[i].role==AW_HW_LEAD)continue;
            if(pass==0 && !big_move(i))continue;
            best=i;
        }
    return best<0?0:best;
}
int AW_HalloweenCamera(float origin[3],float angles[3]) {
    vec3_t close,eye,look;float u;int shot;long number;edict_t *p=player();
    if(!hw.on || !hw.count || !p)return 0;
    shot=AW_HalloweenShot(hw.now,hw.beat,hw.locked,&u);
    number=(long)(hw.now/(4*hw.beat*AW_HALLOWEEN_SHOT_BARS));
    if(shot==AW_HW_SHOT_CLOSE && number!=hw.close_shot){hw.close_shot=number;hw.close_actor=pick_close();}
    chest(hw.actor[hw.close_actor<hw.count?hw.close_actor:0].e,close);
    close[2]-=2;                            /* her mid-body */
    /* every shot at its subject's fitting distance: the whole cast (or the one dancer) head to feet in frame */
    AW_HalloweenShotPose(shot,u,hw.forward,hw.centre,hw.fit,close,hw.close_fit,eye,look);
    clear_eye(look,eye,p);                  /* never inside or behind a wall or a roof */
    clear_edges(look,eye,p);                /* nor beside one that fills a side of the frame */
    VectorCopy(eye,origin);
    AW_HalloweenAim(eye,look,angles);
    return 1;
}

void AW_HalloweenDraw(void) {
    int lh,w,h,x,y,w1,w2,i;
    if(!hw.on || key_dest==key_console || !vid.buffer)return;
    if(hw.intro){
        /* the greeting: alone on black, the box only as large as its two lines, in the exact centre */
        i=AW_UIColor(0,0,0);
        for(y=0;y<(int)vid.height;y++)memset(vid.buffer+y*vid.rowbytes,i,vid.width);
        lh=AW_UIHeight();if(lh<8)lh=8;
        w1=AW_UIWidth(AW_HALLOWEEN_TEXT1);w2=AW_UIWidth(AW_HALLOWEEN_TEXT2);
        w=(w1>w2?w1:w2)+20;if(w>(int)vid.width-8)w=vid.width-8;
        h=2*lh+14;
        x=((int)vid.width-w)/2;y=((int)vid.height-h)/2;
        AW_UIBox(x,y,w,h);
        AW_UITextBox(x,y+6,w,lh,AW_HALLOWEEN_TEXT1,AW_UIColor(223,199,144));
        AW_UITextBox(x,y+8+lh,w,lh,AW_HALLOWEEN_TEXT2,AW_UIColor(223,199,144));
        scr_copyeverything=1;
        return;
    }
    /* small, in the bottom-left corner: the same counter as dbg fps (HUD-FPS-NEEDS-DBG-HUD-56) */
    if(hw.fps)AW_FpsCorner();
}

static void command_with(int fps) {
    const char *argv[3];int i,argc=Cmd_Argc();aw_hw_cmd_t c;
    for(i=0;i<argc && i<3;i++)argv[i]=Cmd_Argv(i);
    if(argc>3 || !AW_HalloweenParse(argc,argv,&c)){Con_Printf("Usage: dbg halloween [dagoth / skeletons / bench [skeletons] / fps on|off / camera wide|director / stop / status]\n");return;}
    switch(c.kind){
    case AW_HW_STOP:if(!hw.on)Con_Printf("Halloween scene not running.\n");stop(0);return;
    case AW_HW_FPS:hw.fps=c.value;Con_Printf("Halloween FPS counter %s.\n",c.value?"on (bottom left)":"off");return;
    case AW_HW_CAMERA:hw.locked=c.value;Con_Printf("Halloween camera: %s.\n",c.value?"the wide shot only":"the director's shots");return;
    case AW_HW_STATUS:
        if(!hw.on){Con_Printf("Halloween scene not running.\n");return;}
        {float u;int shot=AW_HalloweenShot(hw.now,hw.beat,hw.locked,&u);
         Con_Printf("Halloween scene: %d actors, %.1f s, beat %.3f s, shot %d, stage floor %.1f, steps: lead %d, dancers %d, skeletons %d%s.\n",
                    hw.count,hw.now,hw.beat,shot,hw.floor,hw.role[0].step,hw.role[1].step,hw.role[2].step,hw.bench?", bench":"");}
        return;
    default:start(c.version,c.bench,fps);
    }
}
static void command(void) {command_with(0);}
/* dbg halloweentest: the same with the FPS counter on */
static void command_test(void) {command_with(1);}
/* aw bench NAME (aw halloweenbench, dbg bench): the standard benchmarks by name; one today, halloween [skeletons] */
static void bench_command(void) {
    const char *name=Cmd_Argc()>1?Cmd_Argv(1):"halloween";
    if(Cmd_Argc()>3 || Q_strcasecmp((char *)name,"halloween") ||
       (Cmd_Argc()==3 && Q_strcasecmp(Cmd_Argv(2),"skeletons") && Q_strcasecmp(Cmd_Argv(2),"dagoth"))){
        Con_Printf("Usage: aw bench halloween [skeletons] (the standard benchmark: docs/REAL_HARDWARE.md)\n");return;
    }
    start(Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(2),"skeletons")?AW_HW_SKELETONS:AW_HW_WITH_LEAD,1,1);
}

void AW_HalloweenInit(void) {
    Cmd_AddCommand("aw_halloween",command);
    Cmd_AddCommand("aw_halloweentest",command_test);
    Cmd_AddCommand("aw_bench",bench_command);
}
