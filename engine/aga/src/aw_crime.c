/* SPDX-License-Identifier: GPL-2.0-or-later
 * Crime, the engine side (aw_crime.h; CRIME-59, STEAL-WITNESSED-NO-CRIME-61): the crimes as OpenMW 0.51
 * mechanicsmanagerimp.cpp itemTaken / commitCrime / reportCrime / actorAttacked / actorKilled decide them, on the NPCs
 * of the loaded world; the guards' arrest (actors.cpp, aipursue.cpp), the fine and jail (worldimp.cpp goToJail,
 * jailscreen.cpp).
 *
 * Budget (the budget sheet; measured figures in docs/GAME_FORMULAS.md "Crime"):
 *   per crime, never per frame: one walk over the edicts (the NPCs within the alarm radius, 500 Quake units), one
 *   world trace per NPC in the radius that has to see it (none for a murder: it is heard), the host's actor records
 *   (in memory: the area's stat blocks), one voice line per Thief or Intruder witness. Measured at v0.0.61 for a theft
 *   (Arrille's Tradehouse, 7 NPCs, 7 traces): unseen 14 ms, seen with four fight starts 197-254 ms.
 *   per frame: nothing while no guard pursues, the bounty is under iCrimeThreshold and no jail waits; else at most
 *   one edict walk every 0.25 s for the pursuers (a distance and one trace each) and one every second for the guards
 *   on sight (a distance, and one trace and the awareness roll for a guard within the alarm radius).
 *   resident: the settings (29 floats), the crime-reported line, 32 NPC rows of 16 bytes, the last crime's report
 *   (about 1 KB), the jail's state; the prison markers (a 6-line file) and the jail's lines are read only at the jail.
 */
#include "quakedef.h"
#include "aw_crime.h"
#include "aw_combat.h"
#include "aw_glut.h"
#include "aw_move.h"
#include "aw_msgbox.h"
#include "aw_pcstanding.h"
#include "aw_inventory.h"
#include "aw_harvest_runtime.h"
#include "aw_placed.h"
#include "aw_ledger.h"
#include "aw_state.h"
#include "aw_world.h"
#include "aw_dial.h"
#include "aw_character.h"
#include "aw_levelup.h"
#include "aw_rest.h"
#include "aw_statswin.h"
#include "aw_mwvm.h"
#include "aw_actors.h"   /* AW_CombatTestEngage: aw_placed crime kill */
int AW_SceneStarting(void);   /* aw_scene.c: a map load is pending */

int (*aw_crime_witness)(edict_t *e,aw_crime_witness_t *out);
int (*aw_crime_attack)(edict_t *e,int fight);
void (*aw_crime_thief)(aw_crime_thief_t *out);
void (*aw_crime_disposition)(edict_t *e,int change,int permanent);
void (*aw_crime_calm)(edict_t *e);
int (*aw_crime_pursue)(edict_t *e,int on);
int (*aw_crime_greet)(edict_t *e);                 /* aw_mwhost.c: the guard talks (ForceGreeting's act) */
int (*aw_crime_guard)(edict_t *e);                 /* aw_mwhost.c: of class Guard */

static aw_crime_settings_t settings;
static int loaded;                  /* 0 not tried, 2 every setting, 1 the theft's only (an older image), -1 none */
static char crime_text[128];        /* sCrimeMessage */
#define SCALE AW_MOVE_UNIT_SCALE    /* Quake units per original unit */
#define WITNESSES 16                /* the NPCs of one crime kept for `aw_placed crime` */
static struct {
    char owner[33];int kind,faction,value,bounty,reported,seen,neighbors,attackers,guards,before,after,dry,crime_id;
    int edicts,traces;double ms;   /* the event's cost: edicts walked (both passes), world traces, wall time */
    struct {char name[32];int distance,target,roll,at[3],disposition;unsigned char los,noticed,alarm,fight,added,attacked,guard,pursues;} w[WITNESSES];
    short thief_at[3];
    int count;
} last;
static unsigned long crimes_tried,crimes,rolls_state=0x2545f491UL,arrests,calmed,jailed,fines;
static aw_crime_actor_t actors[AW_CRIME_ACTORS];
static int actors_ready;

static int roll100(void){
    unsigned long x=rolls_state;
    x^=(x<<13)&0xFFFFFFFFUL;x^=x>>17;x^=(x<<5)&0xFFFFFFFFUL;rolls_state=x&0xFFFFFFFFUL;
    return (int)(rolls_state%100);
}
static int load(void){
    FILE *f=NULL;char line[128],name[64];float value;int n=0;
    if(loaded)return loaded>0;
    loaded=-1;memset(&settings,0,sizeof(settings));
    if(COM_FOpenFile("combat/settings.txt",&f)<0 || !f){Con_Printf("Crime: no combat/settings.txt in this image.\n");return 0;}
    while(fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        if(Q_sscanf(line,"crime %63s %f",name,&value)==2){if(AW_CrimeSettingSet(&settings,name,value))n++;continue;}
        if(!strncmp(line,"text sCrimeMessage ",19)){Q_strcpy_bounded(crime_text,line+19,sizeof(crime_text));continue;}
    }
    fclose(f);
    /* the theft's settings first: an image built before v0.0.62 has those alone (then thefts alone are crimes) */
    if(n<AW_CRIME_THEFT_SETTINGS){
        Con_Printf("Crime: the image has %d of %d crime settings (rebuild the image): no crimes.\n",n,AW_CRIME_SETTING_COUNT);
        return 0;
    }
    if(n<AW_CRIME_SETTING_COUNT){
        Con_Printf("Crime: the image has the theft's settings only (%d of %d; rebuild the image): no other crimes.\n",n,
                   AW_CRIME_SETTING_COUNT);
        loaded=1;return 1;
    }
    loaded=2;return 1;
}
static int full(void){return load() && loaded==2;}
float AW_CrimeAlarmRadius(void){return full()?settings.fAlarmRadius*SCALE:0;}   /* aw_crime.h (COMBAT-ACTOR-VS-ACTOR-62) */
static edict_t *player(void){return sv.active && svs.maxclients>=1 && svs.clients?svs.clients[0].edict:NULL;}
static const char *source_id(edict_t *e){eval_t *v=GetEdictFieldValue(e,"aw_source_id");return v && v->string?pr_strings+v->string:"";}
static unsigned long ref_of(edict_t *e){eval_t *v=GetEdictFieldValue(e,"aw_ref");return v && v->_float>0?(unsigned long)v->_float:0;}
static int is_npc(edict_t *e){return !e->free && !strcmp(pr_strings+e->v.classname,"aw_npc");}
static aw_crime_actor_t *row_of(edict_t *e,int make){
    unsigned long r=e?ref_of(e):0;
    if(!actors_ready){int i;memset(actors,0,sizeof(actors));for(i=0;i<AW_CRIME_ACTORS;i++)actors[i].crime_id=-1;actors_ready=1;}
    return make?AW_CrimeActorMake(actors,AW_CRIME_ACTORS,r):AW_CrimeActorFind(actors,AW_CRIME_ACTORS,r);
}
/* CRIME-SAVE-PURSUERS-62 (aw_crime.h): the rows to and from a saved game */
int AW_CrimeActorsExport(unsigned char *out,int capacity){
    row_of(NULL,0);   /* the table made */
    return AW_CrimeActorsPack(actors,AW_CRIME_ACTORS,out,capacity);
}
int AW_CrimeActorsImport(const unsigned char *data,int bytes){
    int k=AW_CrimeActorsUnpack(actors,AW_CRIME_ACTORS,data,bytes);
    actors_ready=1;   /* emptied, then filled (or left empty when unreadable) */
    return k;
}
void AW_CrimeActorsReset(void){AW_CrimeActorsUnpack(actors,AW_CRIME_ACTORS,NULL,0);actors_ready=1;}
static edict_t *edict_of_ref(unsigned long ref){
    int i;
    if(!ref)return NULL;
    for(i=1;i<sv.num_edicts;i++){edict_t *e=EDICT_NUM(i);if(is_npc(e) && ref_of(e)==ref)return e;}
    return NULL;
}
/* World::getLOS: eye to eye through the world (actors do not block) */
static int sees(edict_t *p,edict_t *e){
    vec3_t from,to;trace_t tr;
    VectorCopy(e->v.origin,from);from[2]+=e->v.maxs[2]*.9f;
    VectorCopy(p->v.origin,to);to[2]+=p->v.view_ofs[2];
    tr=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,e);
    return tr.fraction>=1 && !tr.startsolid && !tr.allsolid;
}
/* the thief more than 90 degrees off E's facing (awarenessCheck: the angle between its facing and the thief) */
static int behind(edict_t *e,const vec3_t to_thief){
    vec3_t f,r,u,a;a[0]=0;a[1]=e->v.angles[1];a[2]=0;
    AngleVectors(a,f,r,u);      /* it writes all three vectors (never NULL: the s1-s3 sessions stopped here) */
    return DotProduct(f,to_thief)<0;
}
static int guard_of(edict_t *e,const aw_crime_witness_t *w){return w->guard || (aw_crime_guard && aw_crime_guard(e));}

int AW_CrimeTakenValue(const char *id,int count,int value){
    if(id && !Q_strncasecmp((char *)id,"gold_",5))return count;     /* gold: its pieces (itemTaken isGold) */
    return count*(value>0?value:0);
}

/* reportCrime: the bounty, the message, the reactions of every NPC in the radius (VICTIM: the victim's edict) */
static void report(int kind,edict_t *victim,const char *owner,int faction,int arg,float radius){
    edict_t *p=player(),*e;int i,reporter=0,id=AW_StandingCrimeNew();vec3_t d;
    last.crime_id=id;
    /* who reports: an NPC in the radius with Alarm 100 (for trespass each says Intruder) */
    for(i=1;i<sv.num_edicts;i++){
        aw_crime_witness_t w;float dist;
        e=EDICT_NUM(i);
        if(!is_npc(e))continue;
        VectorSubtract(p->v.origin,e->v.origin,d);dist=(float)Length(d);
        if(dist>radius && e!=victim)continue;
        memset(&w,0,sizeof(w));
        if(!aw_crime_witness(e,&w) || !w.can_report || !AW_CRIME_REPORTS(w.alarm))continue;
        reporter=1;
        if((kind==AW_CRIME_TRESPASS) && AW_GlutSay(e,AW_GLUT_INTRUDER,0) && AW_GlutText()[0])
            AW_UISubtitle(pr_strings+e->v.netname,AW_GlutText(),3);
    }
    last.edicts+=sv.num_edicts-1;
    last.reported=reporter;last.before=AW_StandingCrime();
    /* every NPC in the radius reacts */
    for(i=1;i<sv.num_edicts;i++){
        aw_crime_witness_t w;aw_crime_react_in_t in;aw_crime_react_t out;aw_crime_actor_t *row;float dist;int k;
        e=EDICT_NUM(i);
        if(!is_npc(e))continue;
        VectorSubtract(p->v.origin,e->v.origin,d);dist=(float)Length(d);
        if(dist>radius && e!=victim)continue;
        memset(&w,0,sizeof(w));
        if(!aw_crime_witness(e,&w) || !w.can_report)continue;
        row=row_of(e,0);
        memset(&in,0,sizeof(in));in.alarm=w.alarm;in.fight=w.fight;in.victim=e==victim;
        /* the class matters for an alarmed NPC and a victim of pickpocketing or assault only (a read of its class) */
        in.guard=w.guard || ((in.victim || AW_CRIME_REPORTS(w.alarm)) && guard_of(e,&w));
        in.disposition=w.disposition+(row?row->disposition:0);
        if(in.disposition<0)in.disposition=0;else if(in.disposition>100)in.disposition=100;
        in.distance=dist/SCALE;
        AW_CrimeReact(&settings,kind,arg,&in,aw_combat_ai.fFightDispMult,aw_combat_ai.iFightDistanceBase,
                      aw_combat_ai.fFightDistanceMultiplier,&out);
        if(out.crime_id || out.disposition || out.alarmed)row=row_of(e,1);
        if(row){
            if(out.crime_id)row->crime_id=id;
            if(out.alarmed)row->alarmed=1;
            if(out.disposition && !out.permanent)row->disposition=(short)(row->disposition+out.disposition);
            if(kind==AW_CRIME_MURDER && e==victim)row->murdered=1;
        }
        if(out.disposition && out.permanent && aw_crime_disposition)aw_crime_disposition(e,out.disposition,1);
        for(k=0;k<last.count && strcmp(last.w[k].name,pr_strings+e->v.netname);k++){}
        if(k<last.count)last.w[k].disposition=(short)out.disposition;
        if(out.pursue){
            last.guards++;
            /* AiPursue: the guard means to arrest even where it cannot walk (the census office's guards of the opening
             * scene have no walking package): it talks once the player is near (STEAL-WITNESSED-NO-CRIME-61) */
            if(row && !row->pursue){if(aw_crime_pursue)aw_crime_pursue(e,1);row->pursue=1;row->walk_edict=NUM_FOR_EDICT(e);}
            if(k<last.count)last.w[k].pursues=1;
            continue;
        }
        if(out.attack && aw_crime_attack && aw_crime_attack(e,out.fight)){
            last.attackers++;if(row)row->attacked=1;
            if(k<last.count && !last.w[k].attacked){last.w[k].attacked=1;last.w[k].added=(unsigned char)(out.fight-w.fight);}
        }
    }
    last.edicts+=sv.num_edicts-1;
    /* a murder marks its victim for OnMurder whether or not it is reported (notifyMurder) */
    if(kind==AW_CRIME_MURDER && victim){aw_crime_actor_t *row=row_of(victim,1);if(row)row->murdered=1;}
    if(reporter){
        aw_crime_witness_t w;const char *f=NULL;
        last.bounty=AW_CrimeBounty(&settings,kind,arg);
        AW_StandingModCrime(last.bounty);
        if(crime_text[0])AW_MsgBoxShow(crime_text,NULL,0);   /* the window manager: a rise of the bounty */
        /* a crime against a faction's member, or a faction's own thing: the player is expelled from it */
        memset(&w,0,sizeof(w));w.want_faction=1;
        if(victim && aw_crime_witness(victim,&w) && w.faction[0])f=w.faction;
        else if(!victim && faction && owner && owner[0])f=owner;
        if(f && AW_StandingRank(f)>=0 && !AW_StandingExpelled(f)){
            AW_StandingSetExpelled(f,1);Con_Printf("Crime: expelled from %s.\n",f);
        }
    }
    last.after=AW_StandingCrime();
}

/* commitCrime: the witnesses of a crime of KIND against VICTIM (an NPC's edict, NULL: OWNER, a record id or a
 * faction, wherever it stands) worth ARG; DRY (aw_placed crime watch): only who would see it, nothing changes */
static int commit(int kind,edict_t *victim,const char *owner,int faction,int arg,int victim_aware,int dry){
    edict_t *p=player(),*e,*owner_npc=NULL;int i,seen=0;float radius;aw_crime_thief_t thief;vec3_t d;
    if(!dry)crimes_tried++;
    last.kind=kind;
    Q_strcpy_bounded(last.owner,victim?source_id(victim):owner?owner:"",sizeof(last.owner));last.faction=faction;last.value=arg;
    if(!p || (!victim && (!owner || !owner[0])) || !load() || !aw_crime_witness)return 0;
    if(kind!=AW_CRIME_THEFT && !full())return 0;      /* an older image: thefts alone */
    memset(&thief,0,sizeof(thief));thief.fatigue_term=1;
    if(aw_crime_thief)aw_crime_thief(&thief);
    radius=settings.fAlarmRadius*SCALE;
    last.thief_at[0]=(short)p->v.origin[0];last.thief_at[1]=(short)p->v.origin[1];last.thief_at[2]=(short)p->v.origin[2];
    last.edicts+=sv.num_edicts-1;
    for(i=1;i<sv.num_edicts;i++){
        aw_crime_witness_t w;float dist,aim=0;int is_victim,k,target=0,roll=-1,los=0,noticed=0,heard;
        e=EDICT_NUM(i);
        if(!is_npc(e))continue;
        is_victim=victim?e==victim:!faction && !Q_strcasecmp((char *)source_id(e),(char *)owner);
        VectorSubtract(p->v.origin,e->v.origin,d);dist=(float)Length(d);
        if(dist>radius && !is_victim)continue;
        memset(&w,0,sizeof(w));
        if(!aw_crime_witness(e,&w) || !w.can_report)continue;
        last.neighbors++;
        if(is_victim && !victim)owner_npc=e;   /* a theft's owner: the report's victim, wherever it stands */
        /* the victim of an assault knows, a murder is heard: no trace for those */
        heard=AW_CrimeWitness(kind,is_victim,victim_aware,0);
        if(!heard){
            w.observer.behind=behind(e,d);
            aim=AW_CrimeAwarenessTarget(&settings,&thief,&w.observer,dist/SCALE);target=(int)aim;
            last.traces++;
            if((los=sees(p,e))!=0){roll=roll100();noticed=(float)roll>=aim;}
        }
        if(AW_CrimeWitness(kind,is_victim,victim_aware,noticed)){
            seen++;noticed=1;
            /* the NPC complains about a theft even when it does nothing about it */
            if(!dry && (kind==AW_CRIME_THEFT || kind==AW_CRIME_PICKPOCKET) && AW_GlutSay(e,AW_GLUT_THIEF,0) && AW_GlutText()[0])
                AW_UISubtitle(pr_strings+e->v.netname,AW_GlutText(),3);
        }
        if(last.count<WITNESSES){
            k=last.count++;
            Q_strcpy_bounded(last.w[k].name,pr_strings+e->v.netname,sizeof(last.w[k].name));
            last.w[k].distance=(short)(dist/SCALE);last.w[k].target=(short)target;last.w[k].roll=(short)roll;
            last.w[k].los=(unsigned char)(los || heard);last.w[k].noticed=(unsigned char)noticed;
            last.w[k].alarm=(unsigned char)(w.alarm>255?255:w.alarm);last.w[k].fight=(unsigned char)(w.fight>255?255:w.fight);
            last.w[k].guard=(unsigned char)w.guard;
            last.w[k].at[0]=(short)e->v.origin[0];last.w[k].at[1]=(short)e->v.origin[1];last.w[k].at[2]=(short)e->v.origin[2];
        }
    }
    last.seen=seen;last.dry=dry;
    if(dry)return seen;
    if(seen){crimes++;report(kind,victim?victim:owner_npc,owner,faction,arg,radius);return seen;}
    /* an assault nobody saw (the victim could not report: knocked down): a guard reports it itself, anyone else fights
     * back (the combat layer starts that fight with the blow) */
    if(kind==AW_CRIME_ASSAULT && victim){
        aw_crime_witness_t w;aw_crime_actor_t *row=row_of(victim,0);
        memset(&w,0,sizeof(w));
        if(aw_crime_witness(victim,&w) && guard_of(victim,&w) && !(row && row->pursue)){crimes++;report(kind,victim,NULL,0,arg,radius);}
    }
    return 0;
}
/* the event, timed (the budget sheet: it runs only when a crime happens, never per frame) */
static int crime(int kind,edict_t *victim,const char *owner,int faction,int arg,int victim_aware,int dry){
    double t0=Sys_FloatTime();int seen;
    memset(&last,0,sizeof(last));last.crime_id=-1;
    seen=commit(kind,victim,owner,faction,arg,victim_aware,dry);
    last.ms=(Sys_FloatTime()-t0)*1000.0;
    return seen;
}
int AW_CrimeTheft(const char *owner,int faction,int value){return crime(AW_CRIME_THEFT,NULL,owner,faction,value,0,0);}
int AW_CrimeTrespass(const char *owner,int faction,int bed){
    return crime(bed?AW_CRIME_BED:AW_CRIME_TRESPASS,NULL,owner,faction,0,0,0)>0;
}
int AW_CrimeCanCommit(edict_t *victim){
    aw_crime_witness_t w;aw_crime_actor_t *row;
    if(!victim || !is_npc(victim) || !aw_crime_witness)return 0;
    memset(&w,0,sizeof(w));
    if(!aw_crime_witness(victim,&w))return 0;           /* not an NPC (a creature: no crime) */
    row=row_of(victim,0);
    return AW_CrimeCanCommitAgainst(1,w.aggressive,w.engaged,row && row->pursue,0,0);
}
int AW_CrimeAssault(edict_t *victim){
    if(!AW_CrimeCanCommit(victim) || !full())return 0;
    return crime(AW_CRIME_ASSAULT,victim,NULL,0,0,1,0)>0 || last.reported;
}
int AW_CrimeKilled(edict_t *victim,int can_commit){
    aw_crime_actor_t *row;aw_crime_witness_t w;
    if(!victim || !aw_crime_witness || !full())return 0;
    memset(&w,0,sizeof(w));
    if(!aw_crime_witness(victim,&w))return 0;           /* a creature: no crime ("animal rights" are not one) */
    if(can_commit<0)can_commit=0;                       /* dead now: it can no longer be the target of a new crime */
    row=row_of(victim,0);
    if(!AW_CrimeIsMurder(1,1,can_commit,row?row->crime_id:-1))return 0;
    crime(AW_CRIME_MURDER,victim,NULL,0,0,0,0);
    {aw_crime_actor_t *r=row_of(victim,1);if(r)r->murdered=1;}   /* notifyMurder: OnMurder reads it */
    AW_MwvmStateChanged();                                       /* the scripts that ask OnMurder run again */
    return 1;
}
int AW_CrimeOnMurder(unsigned long ref){
    aw_crime_actor_t *row=actors_ready?AW_CrimeActorFind(actors,AW_CRIME_ACTORS,ref):NULL;
    if(!row || !row->murdered)return 0;
    row->murdered=0;return 1;
}
int AW_CrimeAlarmed(unsigned long ref){
    aw_crime_actor_t *row=actors_ready?AW_CrimeActorFind(actors,AW_CRIME_ACTORS,ref):NULL;
    return row && row->alarmed;
}
int AW_CrimeDispositionOf(unsigned long ref){
    aw_crime_actor_t *row=actors_ready?AW_CrimeActorFind(actors,AW_CRIME_ACTORS,ref):NULL;
    return row?row->disposition:0;
}

/* --- the fine and jail --- */
/* recordCrimeId and the calm of actors.cpp: every NPC whose crime is paid stops pursuing and fighting, is no longer
 * alarmed, its Fight back to its own and its crime's disposition change gone */
static void calm_all(void){
    int paid,i,n=0;
    AW_StandingCrimePaid();paid=AW_StandingCrimeLast();
    if(!actors_ready)return;
    for(i=0;i<AW_CRIME_ACTORS;i++){
        aw_crime_actor_t *r=&actors[i];edict_t *e;
        if(!r->ref || r->crime_id==-1 || r->crime_id>paid)continue;
        if(sv.active && (e=edict_of_ref(r->ref))!=NULL){
            if(r->pursue && aw_crime_pursue)aw_crime_pursue(e,0);
            if(aw_crime_calm)aw_crime_calm(e);
        }
        n++;
    }
    AW_CrimeActorsCalm(actors,AW_CRIME_ACTORS,paid);
    calmed+=n;
}
/* the prison markers of the image (prison-markers.txt, tools/build_aga.py write_prison_markers): "AWPM1", then per
 * marker its reference, x y z (original units), the facing, the evidence chest's reference (0 none) and the prison */
#define MARKERS 16
typedef struct {unsigned long ref,chest;float at[3],yaw;char prison[64];} marker_t;
static int markers_read(marker_t *m,int max){
    FILE *f=NULL;char line[200];int n=0;
    if(COM_FOpenFile("prison-markers.txt",&f)<0 || !f)return 0;
    if(fgets(line,sizeof(line),f) && !strncmp(line,"AWPM1",5))
        while(n<max && fgets(line,sizeof(line),f)){
            char *bar=strchr(line,'|');
            line[strcspn(line,"\r\n")]=0;
            if(Q_sscanf(line,"%lu %f %f %f %f %lu",&m[n].ref,&m[n].at[0],&m[n].at[1],&m[n].at[2],&m[n].yaw,&m[n].chest)!=6)continue;
            Q_strcpy_bounded(m[n].prison,bar?bar+1:"",sizeof(m[n].prison));
            n++;
        }
    fclose(f);return n;
}
/* the player's place in original units: outdoors now, else the last outdoor place the tick saw */
static float outside[3];static int outside_known;static double outside_at;
static void outside_update(void){
    edict_t *p=player();float at[3];
    if(!p || realtime-outside_at<2)return;
    outside_at=realtime;
    if(!AW_Interior() && AW_WorldToSource(sv.name,p->v.origin,at)){VectorCopy(at,outside);outside_known=1;}
}
/* getClosestMarker: the nearest prison marker to where the player is (outdoors), else to the last outdoor place */
static int closest_marker(const marker_t *m,int n){
    int i,best=-1;float bd=0;
    outside_at=0;outside_update();
    for(i=0;i<n;i++){
        float dx=m[i].at[0]-outside[0],dy=m[i].at[1]-outside[1],dist=dx*dx+dy*dy;
        if(best<0 || (outside_known && dist<bd)){best=i;bd=dist;}
    }
    return best;
}
static int confiscated;
/* confiscateStolenItems: the stolen goods the player carries (the world change list's stolen pairs) go into the
 * nearest prison's evidence chest (CHEST; 0 or a chest the image does not hold: they are taken all the same) */
static void confiscate(unsigned long chest){
    int i,n;
    confiscated=0;
    if(!aw_ledger_on)return;
    for(i=aw_ledger.stolen_count-1;i>=0;i--){
        aw_ledger_stolen_t s=aw_ledger.stolen[i];int32_t have=AW_StateGet(&aw_state,AW_ITEM,s.item);
        n=have<s.count?have:s.count;
        if(n<=0)continue;
        AW_StateSet(&aw_state,AW_ITEM,s.item,have-n);
        AW_LedgerStolenAdd(&aw_ledger,s.item,s.owner,s.faction,-n);
        if(chest)AW_ContainerChange((unsigned)chest,s.item,n,0);
        confiscated+=n;
    }
    if(confiscated)AW_CombatEquipmentChanged();
}
static struct {int state,days,marker_ok;double at;char text[AW_MSGBOX_TEXT];} jail;
void AW_CrimePayFine(int confiscate_goods){
    marker_t m[MARKERS];int n,k;
    AW_StandingSetCrime(0);
    if(confiscate_goods){n=markers_read(m,MARKERS);k=closest_marker(m,n);confiscate(k>=0?m[k].chest:0);}
    calm_all();fines++;
}
int AW_CrimeInJail(void){return jail.state!=0;}
void AW_CrimeGoToJail(void){
    marker_t m[MARKERS];int n,k,bounty=AW_StandingCrime();
    if(jail.state || !load())return;
    jail.days=AW_CrimeJailDays(&settings,bounty);
    AW_StandingSetCrime(0);
    n=markers_read(m,MARKERS);k=closest_marker(m,n);
    confiscate(k>=0?m[k].chest:0);
    calm_all();
    jail.state=1;jail.at=realtime;jailed++;
}
/* one of the game's lines from combat/settings.txt ("text NAME ..."), read at the jail only */
static int game_text(const char *name,char *out,int size){
    FILE *f=NULL;char line[160];size_t n=strlen(name);int found=0;
    out[0]=0;
    if(COM_FOpenFile("combat/settings.txt",&f)<0 || !f)return 0;
    while(!found && fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        if(!strncmp(line,"text ",5) && !strncmp(line+5,name,n) && line[5+n]==' '){Q_strcpy_bounded(out,line+6+n,size);found=1;}
    }
    fclose(f);return found;
}
/* FORM's %d and %s filled in order from NUMBER and WORD */
static void fill(char *out,int size,const char *form,const char *word,int number){
    int i=0,o=0;char num[16];const char *put;
    Q_snprintf(num,sizeof(num),"%d",number);
    while(form[i] && o<size-1){
        put=NULL;
        if(form[i]=='%' && form[i+1]=='d'){put=num;i+=2;}
        else if(form[i]=='%' && form[i+1]=='s'){put=word?word:"";i+=2;}
        if(!put){out[o++]=form[i++];continue;}
        while(*put && o<size-1)out[o++]=*put++;
    }
    out[o]=0;
}
/* the sentence served (jailscreen.cpp onJailFinished; playerskillhandlers.lua jailTimeServed): the days pass as a rest,
 * one random skill a day changes by the jail's rule, the release line with every changed skill */
static void serve(void){
    int before[27],i,day,o;char form[160],line[200];
    for(i=0;i<27;i++)before[i]=aw_character.valid?aw_character.skills[i]:0;
    AW_RestPass(jail.days*24,1);
    if(aw_character.valid){
        AW_LevelupLoad();
        for(day=0;day<jail.days;day++){
            int sk=roll100()%27,change=AW_CrimeJailSkill(sk,aw_character.skills[sk]);
            if(change>0 && aw_levelup_rules.loaded && aw_character.clas>=0 && aw_character.clas<AW_CharacterClassCount())
                AW_LevelupSkillRaise(&aw_levelup_rules,&aw_classes[aw_character.clas],&aw_character,sk,1);
            else aw_character.skills[sk]+=change;
        }
    }
    if(!game_text(jail.days==1?"sNotifyMessage42":"sNotifyMessage43",form,sizeof(form)))
        Q_strcpy_bounded(form,jail.days==1?"You have been released after %d day.":"You have been released after %d days.",sizeof(form));
    fill(jail.text,sizeof(jail.text),form,NULL,jail.days);o=(int)strlen(jail.text);
    for(i=0;i<27 && aw_character.valid;i++){
        int now=aw_character.skills[i];
        if(now==before[i])continue;
        if(now<before[i]){if(!game_text("sNotifyMessage44",form,sizeof(form)))Q_strcpy_bounded(form,"Your %s skill decreased to %d.",sizeof(form));}
        else if(!AW_LevelupGameText("sNotifyMessage39",form,sizeof(form)))Q_strcpy_bounded(form,"Your %s skill increased to %d.",sizeof(form));
        {   /* %s then %d: the skill's name and its value */
            char tmp[160];int a=0,b=0,first=1;
            while(form[a] && b<(int)sizeof(tmp)-1){
                if(form[a]=='%' && form[a+1]=='s' && first){const char *s=AW_StatsSkillName(i);while(*s && b<(int)sizeof(tmp)-1)tmp[b++]=*s++;a+=2;first=0;continue;}
                tmp[b++]=form[a++];
            }
            tmp[b]=0;fill(line,sizeof(line),tmp,NULL,now);
        }
        /* a line of its own, as OpenMW's jail screen joins them (CRIME-RELEASE-LINE-CUT-62) */
        if(o+2+(int)strlen(line)<(int)sizeof(jail.text)){jail.text[o++]='\n';Q_strcpy_bounded(jail.text+o,line,sizeof(jail.text)-o);o+=(int)strlen(line);}
    }
}
static void jail_step(void){
    marker_t m[MARKERS];int n,k;
    if(jail.state==1){
        /* the guard's line is read first: the jail waits until the conversation and any window have closed */
        if(AW_DialWindowActive() || key_dest!=key_game || AW_MsgBoxActive())return;
        serve();
        n=markers_read(m,MARKERS);k=closest_marker(m,n);
        jail.marker_ok=k>=0 && AW_MapTeleportAt(m[k].at,1);
        if(!jail.marker_ok && k>=0){
            /* the marker in the map loaded now (a MiniWind refuses the coordinate teleport, DEBUG-TP-MINIWIND-36): the
             * player is put there at once, its feet on the marker */
            edict_t *p=player();float local[3];
            if(p && AW_SourceToWorld(sv.name,m[k].at,local)){
                local[2]-=p->v.mins[2];VectorCopy(local,p->v.origin);VectorCopy(vec3_origin,p->v.velocity);
                p->v.angles[1]=p->v.v_angle[1]=90-m[k].yaw;p->v.fixangle=1;SV_LinkEdict(p,false);jail.marker_ok=2;
            }
        }
        if(!jail.marker_ok)Con_Printf("Crime: no prison marker of this image can be reached; released here.\n");
        else Con_Printf("Crime: jailed %d days at %s; released at the prison marker %lu.\n",jail.days,m[k].prison,m[k].ref);
        jail.state=2;jail.at=realtime;
        return;
    }
    if(jail.state==2){
        if(AW_SceneStarting() || realtime-jail.at<.5)return;   /* the way out's map is loading */
        {   /* OpenMW showInteractiveMessage: the release line stays until it is closed */
            static const char *const ok[1]={"OK"};
            AW_MsgBoxShow(jail.text,ok,1);
        }
        jail.state=0;
    }
}
/* updateDialogueGlobals */
void AW_CrimeDialogueGlobals(int (*set_global)(const char *name,int value),int gold){
    static const char *const names[5]={"pchascrimegold","pchasgolddiscount","crimegolddiscount","crimegoldturnin","pchasturnin"};
    int v[5],i;
    if(!set_global || !full())return;
    AW_CrimeGoldGlobals(&settings,AW_StandingCrime(),gold,v);
    for(i=0;i<5;i++)set_global(names[i],v[i]);
}

/* --- the guards (actors.cpp, aipursue.cpp) --- */
static double pursue_at,sight_at;
static unsigned long pursue_walks,sight_walks,pursue_far,pursue_height,pursue_unseen,pursue_busy,greet_refused,pursue_absent;
static int pursue_last,pursue_last_dz;   /* the last pursuer's distance and height to the player (map units) */
/* an alarmed guard runs to the player; near and in sight it talks (the arrest); a bounty paid ends the pursuit */
static void pursuers(void){
    int i,any=0;edict_t *p=player();
    for(i=0;i<AW_CRIME_ACTORS;i++)if(actors[i].ref && actors[i].pursue)any=1;
    if(!any || realtime-pursue_at<.25)return;
    pursue_at=realtime;pursue_walks++;
    for(i=0;i<AW_CRIME_ACTORS;i++){
        aw_crime_actor_t *r=&actors[i];edict_t *e;vec3_t d;float reach;
        if(!r->ref || !r->pursue)continue;
        /* not here, or dead (an NPC's edict health is not its health: the fight's sheet says it; s6: every check
         * stopped here) */
        if(!(e=edict_of_ref(r->ref))){pursue_absent++;continue;}
        {const aw_fighter_t *f=AW_CombatFighter(e);if(f && f->dead){r->pursue=0;continue;}}
        if(AW_StandingCrime()<=0){r->pursue=0;if(aw_crime_pursue)aw_crime_pursue(e,0);continue;}   /* nothing to arrest for */
        /* CRIME-SAVE-PURSUERS-62: a pursuit loaded from a save, or a guard whose edict came back (a cell left and
         * entered again), walks again: the walk is the ambient tables', which a load or a new edict does not keep */
        if(r->walk_edict!=NUM_FOR_EDICT(e)){r->walk_edict=NUM_FOR_EDICT(e);if(aw_crime_pursue)aw_crime_pursue(e,1);}
        VectorSubtract(p->v.origin,e->v.origin,d);
        reach=24.0f+p->v.maxs[0]+3*e->v.maxs[0];          /* the follow's stop distance and the path's tolerance */
        /* feet to feet: an NPC's origin is at its feet, the player's at the middle of its box (s5: the guard stood at
         * the player's side and was 24 units "lower") */
        d[2]=(p->v.origin[2]+p->v.mins[2])-(e->v.origin[2]+e->v.mins[2]);
        pursue_last=(int)Length(d);pursue_last_dz=(int)d[2];
        if(Length(d)>reach){pursue_far++;continue;}
        if(fabs(d[2])>25){pursue_height++;continue;}
        if(!sees(p,e)){pursue_unseen++;continue;}
        if(AW_DialWindowActive() || key_dest!=key_game){pursue_busy++;continue;}
        if(aw_crime_greet && aw_crime_greet(e)){
            r->pursue=0;if(aw_crime_pursue)aw_crime_pursue(e,0);arrests++;
        }else greet_refused++;
    }
}
/* a guard that notices a player with a bounty of iCrimeThreshold pursues to arrest; at x iCrimeThresholdMultiplier
 * it attacks */
static void guards_on_sight(void){
    int i,act=AW_CrimeGuardSight(&settings,AW_StandingCrime());edict_t *p=player();aw_crime_thief_t thief;
    if(!act || realtime-sight_at<1)return;
    sight_at=realtime;sight_walks++;
    memset(&thief,0,sizeof(thief));thief.fatigue_term=1;
    if(aw_crime_thief)aw_crime_thief(&thief);
    for(i=1;i<sv.num_edicts;i++){
        edict_t *e=EDICT_NUM(i);aw_crime_witness_t w;aw_crime_actor_t *row;vec3_t d;float dist,aim;
        if(!is_npc(e))continue;
        VectorSubtract(p->v.origin,e->v.origin,d);dist=(float)Length(d);
        if(dist>settings.fAlarmRadius*SCALE)continue;
        memset(&w,0,sizeof(w));
        if(!aw_crime_witness(e,&w) || !w.can_report || w.engaged || !guard_of(e,&w))continue;
        row=row_of(e,0);
        if(row && row->pursue)continue;
        w.observer.behind=behind(e,d);
        aim=AW_CrimeAwarenessTarget(&settings,&thief,&w.observer,dist/SCALE);
        if(!sees(p,e) || (float)roll100()<aim)continue;
        if(!(row=row_of(e,1)))continue;
        row->alarmed=1;row->crime_id=AW_StandingCrimeNew();
        if(act==2){if(aw_crime_attack)aw_crime_attack(e,100);}
        else{if(aw_crime_pursue)aw_crime_pursue(e,1);row->pursue=1;row->walk_edict=NUM_FOR_EDICT(e);}
    }
}
void AW_CrimeTick(float dt){
    (void)dt;
    if(!sv.active || !player())return;
    if(jail.state){jail_step();return;}
    if(loaded<=0 && !load())return;
    if(!actors_ready)row_of(NULL,0);
    outside_update();
    if(loaded!=2)return;
    pursuers();
    if(!AW_DialWindowActive())guards_on_sight();   /* not while the player talks (the arrest itself) */
}

/* MWSCRIPT-SMALL-FUNCTIONS-62: GetLOS and GetDetected (aw_crime.h). Budget: one world trace per ask, plus the awareness
 * target's arithmetic; the scripts that ask run every frame (a handful of guards and slave owners near the player) */
static void eye(edict_t *e,vec3_t out){
    VectorCopy(e->v.origin,out);
    out[2]+=e->v.view_ofs[2]!=0?e->v.view_ofs[2]:e->v.maxs[2]*.9f;
}
int AW_CrimeSight(edict_t *from,edict_t *to){
    vec3_t a,b;trace_t tr;edict_t *p=player();
    if(!from || !to || from==to || from->free || to->free)return 0;
    if((from!=p && !from->v.modelindex) || (to!=p && !to->v.modelindex))return 0;   /* disabled: hidden, no model */
    eye(from,a);eye(to,b);
    tr=SV_Move(a,vec3_origin,vec3_origin,b,MOVE_NOMONSTERS,from);
    return tr.fraction>=1 && !tr.startsolid && !tr.allsolid;
}
#define ROLLS 16
static aw_crime_roll_t rolls[ROLLS];static int rolls_ready;
int AW_CrimeDetects(edict_t *observer,const aw_crime_observer_t *o,edict_t *actor,const aw_crime_thief_t *t){
    aw_crime_observer_t seen;vec3_t d;float aim;int key,roll,i;
    if(!AW_CrimeSight(observer,actor))return 0;
    if(!load())return 1;            /* no settings in the image: seen is noticed (logged once by load) */
    if(!rolls_ready){for(i=0;i<ROLLS;i++){rolls[i].key=0;rolls[i].roll=-1;rolls[i].at=0;}rolls_ready=1;}
    seen=*o;
    VectorSubtract(actor->v.origin,observer->v.origin,d);
    seen.behind=behind(observer,d);
    aim=AW_CrimeAwarenessTarget(&settings,t,&seen,(float)Length(d)/SCALE);
    key=NUM_FOR_EDICT(observer);
    if((roll=AW_CrimeRollFind(rolls,ROLLS,key,sv.time))<0){roll=roll100();AW_CrimeRollKeep(rolls,ROLLS,key,roll,sv.time);}
    return (float)roll>=aim;
}

/* aw_placed crime: the settings and the last crime (its witnesses: distance, line of sight, the awareness roll, Alarm,
 * Fight, the reaction) */
static void status(void){
    int i;
    Con_Printf("Crime: settings %s, crimes %lu, seen %lu, bounty now %d; arrests %lu, fines %lu, jailed %lu, calmed %lu%s\n",
               loaded==2?"loaded":loaded==1?"theft only":loaded<0?"missing":"not read yet",crimes_tried,crimes,
               AW_StandingCrime(),arrests,fines,jailed,calmed,jail.state?" (in jail)":"");
    if(loaded>0)Con_Printf("  fAlarmRadius %g, fCrimeStealing %g, iCrimeAttack %g, iCrimeKilling %g, iCrimeTresspass %g, "
                           "iCrimeThreshold %g, iDaysinPrisonMod %g, message \"%s\"\n",
                           settings.fAlarmRadius,settings.fCrimeStealing,settings.iCrimeAttack,settings.iCrimeKilling,
                           settings.iCrimeTresspass,settings.iCrimeThreshold,settings.iDaysinPrisonMod,crime_text);
    if(actors_ready)for(i=0;i<AW_CRIME_ACTORS;i++)if(actors[i].ref && !(actors[i].crime_id==-1 && !actors[i].alarmed &&
                                                     !actors[i].murdered && !actors[i].pursue))
        Con_Printf("  NPC ref %lu: crime %d, disposition %+d%s%s%s\n",actors[i].ref,actors[i].crime_id,actors[i].disposition,
                   actors[i].alarmed?", alarmed":"",actors[i].pursue?", pursues":"",actors[i].murdered?", murdered":"");
    Con_Printf("  guards: %lu pursuit checks (absent %lu, far %lu, height %lu, unseen %lu, busy %lu, talk refused %lu;",
               pursue_walks,pursue_absent,pursue_far,pursue_height,pursue_unseen,pursue_busy,greet_refused);
    Con_Printf(" last %d away, %+d high), %lu sight checks\n",pursue_last,pursue_last_dz,sight_walks);
    if(!last.owner[0])return;
    Con_Printf("  cost of that event: %d edicts walked, %d NPCs tested, %d world traces, %.1f ms\n",last.edicts,
               last.neighbors,last.traces,last.ms);
    if(last.dry)Con_Printf("Watch (no theft): from %s here %d NPCs in the alarm radius, %d would see it\n",last.owner,
                           last.neighbors,last.seen);
    else Con_Printf("Last crime: %s, worth %d, against %s%s; %d NPCs in the alarm radius, %d saw it, %s (bounty %+d: %d -> %d), "
               "%d attack, %d guards alarmed, crime %d\n",AW_CrimeKindName(last.kind),
               last.value,last.owner,last.faction?" (a faction)":"",last.neighbors,last.seen,
               last.seen?last.reported?"reported":"not reported (no one with Alarm 100)":"no crime",
               last.bounty,last.before,last.after,last.attackers,last.guards,last.crime_id);
    Con_Printf("  the player at %d %d %d\n",last.thief_at[0],last.thief_at[1],last.thief_at[2]);
    /* two prints a witness: one print of many numbers came out garbled on the Amiga (s5, 7 November 2026) */
    for(i=0;i<last.count;i++){
        Con_Printf("  %s at %d %d %d: %d units, sight %s, awareness %d against %d -> %s;",last.w[i].name,(int)last.w[i].at[0],
                   (int)last.w[i].at[1],(int)last.w[i].at[2],(int)last.w[i].distance,last.w[i].los?"yes":"no",
                   (int)last.w[i].roll,(int)last.w[i].target,last.w[i].noticed?"noticed":"unaware");
        Con_Printf(" Alarm %d, Fight %d, disposition %+d%s%s%s\n",(int)last.w[i].alarm,(int)last.w[i].fight,
                   (int)last.w[i].disposition,last.w[i].guard?", a guard":"",last.w[i].attacked?", attacks":"",
                   last.w[i].pursues?", pursues":"");
    }
}
/* the take paths (aw_inventory.c: a placed item, a container's content; aw_harvest_runtime.c: an owned plant):
 * OpenMW 0.51 isOwned: a faction's item is the player's to take once a member (the rank the reference asks for is
 * not in the area data yet: CRIME-59) */
static void inventory_theft(const char *owner,int faction,const char *id,int count,int value){
    if(faction && AW_StandingRank(owner)>=0)return;
    AW_CrimeTheft(owner,faction,AW_CrimeTakenValue(id,count,value));
}
static void harvest_theft(const char *owner,const char *id,int count){
    aw_inventory_item_t it;
    AW_CrimeTheft(owner,0,AW_CrimeTakenValue(id,count,AW_InventoryRead(id,&it)?it.value:0));
}
/* an owned bed (sleepInBed): the trespass; seen: the sleep is refused */
static int bed_crime(unsigned long reference,const char *owner,int faction){
    (void)reference;
    if(!full())return 1;            /* an image without the trespass's settings: refused as before */
    return AW_CrimeTrespass(owner,faction,1);
}
/* aw_placed crime [watch OWNER | take REFERENCE | pay | thief | jail | trespass OWNER]: the status and the last crime;
 * watch: who would see a theft from OWNER here now (nothing happens); take: the placed item REFERENCE of this room or
 * cell taken as E takes it; pay, thief, jail: PayFine, PayFineThief, GotoJail as the guard's answers run them;
 * trespass: an owned lock of OWNER picked here (the event the lockpicks will raise) */
static void command(void){
    const char *w=Cmd_Argc()>2?Cmd_Argv(2):"";
    if(!strcmp(w,"watch") && Cmd_Argc()>3){crime(AW_CRIME_THEFT,NULL,Cmd_Argv(3),0,0,0,1);status();return;}
    if(!strcmp(w,"take") && Cmd_Argc()>3){
        unsigned reference=(unsigned)strtoul(Cmd_Argv(3),NULL,10);
        if(!AW_PlacedTake(reference)){Con_Printf("aw_placed crime take: no placed item %u to take in this room or cell.\n",reference);return;}
        Con_Printf("aw_placed crime take: took the placed item %u.\n",reference);
        status();return;
    }
    if(!strcmp(w,"pay") || !strcmp(w,"thief")){
        AW_CrimePayFine(!strcmp(w,"pay"));
        Con_Printf("aw_placed crime %s: bounty 0, %d stolen things taken.\n",w,!strcmp(w,"pay")?confiscated:0);
        status();return;
    }
    if(!strcmp(w,"jail")){AW_CrimeGoToJail();Con_Printf("aw_placed crime jail: %d days, %d stolen things taken.\n",jail.days,confiscated);return;}
    if(!strcmp(w,"trespass") && Cmd_Argc()>3){AW_CrimeTrespass(Cmd_Argv(3),0,0);status();return;}
    /* kill REF / hit REF: the loaded NPC of placed reference REF killed by the player (dbg kill crime's act: the
     * murder when it is one) or attacked by the player (the assault, then its fight as a blow starts it), for in-game
     * checks that need no aim */
    if((!strcmp(w,"kill") || !strcmp(w,"hit")) && Cmd_Argc()>3){
        edict_t *e=edict_of_ref(strtoul(Cmd_Argv(3),NULL,10));int can;
        if(!e){Con_Printf("aw_placed crime %s: no loaded NPC of reference %s.\n",w,Cmd_Argv(3));return;}
        can=AW_CrimeCanCommit(e);
        if(!strcmp(w,"hit")){
            Con_Printf("aw_placed crime hit: %s, %s\n",pr_strings+e->v.netname,AW_CrimeAssault(e)?"an assault":"no crime");
            if(!AW_CombatFighter(e) && aw_crime_attack)aw_crime_attack(e,100);   /* it fights back (actorAttacked) */
        }else if(AW_CombatTestEngage(e,1))
            Con_Printf("aw_placed crime kill: %s is dead: %s\n",pr_strings+e->v.netname,AW_CrimeKilled(e,can)?"a murder":"no crime");
        else Con_Printf("aw_placed crime kill: %s has no combat sheet\n",pr_strings+e->v.netname);
        status();return;
    }
    status();
}
static void combat_assault(edict_t *e){AW_CrimeAssault(e);}
static void combat_killed(edict_t *e){AW_CrimeKilled(e,-1);}
void AW_CrimeInit(void){
    aw_inventory_theft=inventory_theft;aw_harvest_theft=harvest_theft;aw_rest_bed_crime=bed_crime;
    aw_combat_assault=combat_assault;aw_combat_killed=combat_killed;
    aw_placed_crime=command;
    /* the settings at engine start, not at the first theft: in s11 that read alone made the first theft's frame 734 ms
     * on FS-UAE at 32 MB Fast (combat/settings.txt read line by line); later thefts took 14-250 ms */
    load();
}
