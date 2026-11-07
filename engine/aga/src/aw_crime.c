/* SPDX-License-Identifier: GPL-2.0-or-later
 * Crime, the engine side (aw_crime.h; STEAL-WITNESSED-NO-CRIME-61): a theft as OpenMW 0.51 mechanicsmanagerimp.cpp
 * itemTaken / commitCrime / reportCrime decide it, on the NPCs of the loaded world.
 *
 * Budget (per theft, never per frame): one walk over the edicts (the NPCs within the alarm radius, 500 Quake units),
 * one world trace per NPC in the radius, the host's actor records (in memory: the area's stat blocks), one voice line
 * per witness. The settings (11 floats) and the crime-reported line are read from combat/settings.txt once, at engine
 * start. Measured on FS-UAE at 32 MB Fast (Arrille's Tradehouse, 15 edicts, 7 NPCs in the radius, 7 traces): a theft
 * no one sees 14 ms, `aw_placed crime watch` 14-20 ms, a seen theft with two Thief lines and four witnesses starting
 * their fight 197-254 ms (their voices and combat sheets are read then, as any fight's start reads them). */
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

int (*aw_crime_witness)(edict_t *e,aw_crime_witness_t *out);
int (*aw_crime_attack)(edict_t *e,int fight);
void (*aw_crime_thief)(aw_crime_thief_t *out);

static aw_crime_settings_t settings;
static int loaded;                  /* 0 not tried, 1 every setting, -1 the image has none (logged once) */
static char crime_text[128];        /* sCrimeMessage */
#define SCALE AW_MOVE_UNIT_SCALE    /* Quake units per original unit */
#define WITNESSES 16                /* the NPCs of one crime kept for `aw_placed crime` */
static struct {
    char owner[33];int faction,value,bounty,reported,seen,neighbors,attackers,guards,before,after,dry;
    int edicts,traces;double ms;   /* the event's cost: edicts walked (both passes), world traces, wall time */
    struct {char name[32];short distance,target,roll,at[3];unsigned char los,noticed,alarm,fight,added,attacked,guard;} w[WITNESSES];
    short thief_at[3];
    int count;
} last;
static unsigned long thefts,crimes,rolls_state=0x2545f491UL;

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
    if(n!=AW_CRIME_SETTING_COUNT){
        Con_Printf("Crime: the image has %d of %d crime settings (rebuild the image): no crimes.\n",n,AW_CRIME_SETTING_COUNT);
        return 0;
    }
    loaded=1;return 1;
}
static edict_t *player(void){return sv.active && svs.maxclients>=1 && svs.clients?svs.clients[0].edict:NULL;}
static const char *source_id(edict_t *e){eval_t *v=GetEdictFieldValue(e,"aw_source_id");return v && v->string?pr_strings+v->string:"";}
static int is_npc(edict_t *e){return !e->free && !strcmp(pr_strings+e->v.classname,"aw_npc");}
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

int AW_CrimeTakenValue(const char *id,int count,int value){
    if(id && !Q_strncasecmp((char *)id,"gold_",5))return count;     /* gold: its pieces (itemTaken isGold) */
    return count*(value>0?value:0);
}

/* DRY (aw_placed crime watch): only who would see a theft from OWNER here now; no roll is kept, nothing said or changed */
static int crime_run(const char *owner,int faction,int value,int dry){
    edict_t *p=player(),*e;int i,reporter=0,seen=0;float radius;aw_crime_thief_t thief;vec3_t d;
    if(!dry)thefts++;
    Q_strcpy_bounded(last.owner,owner?owner:"",sizeof(last.owner));last.faction=faction;last.value=value;
    if(!p || !owner || !owner[0] || !load() || !aw_crime_witness)return 0;
    memset(&thief,0,sizeof(thief));thief.fatigue_term=1;
    if(aw_crime_thief)aw_crime_thief(&thief);
    radius=settings.fAlarmRadius*SCALE;
    last.thief_at[0]=(short)p->v.origin[0];last.thief_at[1]=(short)p->v.origin[1];last.thief_at[2]=(short)p->v.origin[2];
    /* commitCrime: every NPC in the alarm radius, and the victim (the owner) wherever it stands; can it report, does
     * it see the thief; each witness says Thief */
    last.edicts+=sv.num_edicts-1;
    for(i=1;i<sv.num_edicts;i++){
        aw_crime_witness_t w;float dist,aim;int victim,k,target,roll=-1,los=0,noticed=0;
        e=EDICT_NUM(i);
        if(!is_npc(e))continue;
        victim=!faction && !Q_strcasecmp((char *)source_id(e),(char *)owner);
        VectorSubtract(p->v.origin,e->v.origin,d);dist=(float)Length(d);
        if(dist>radius && !victim)continue;
        memset(&w,0,sizeof(w));
        if(!aw_crime_witness(e,&w) || !w.can_report)continue;
        last.neighbors++;
        if(AW_CRIME_REPORTS(w.alarm))reporter=1;
        w.observer.behind=behind(e,d);
        aim=AW_CrimeAwarenessTarget(&settings,&thief,&w.observer,dist/SCALE);target=(int)aim;
        last.traces++;
        if((los=sees(p,e))!=0){roll=roll100();noticed=(float)roll>=aim;}
        if(noticed){
            seen++;
            if(!dry && AW_GlutSay(e,AW_GLUT_THIEF,0) && AW_GlutText()[0])
                AW_UISubtitle(pr_strings+e->v.netname,AW_GlutText(),3);
        }
        if(last.count<WITNESSES){
            k=last.count++;
            Q_strcpy_bounded(last.w[k].name,pr_strings+e->v.netname,sizeof(last.w[k].name));
            last.w[k].distance=(short)(dist/SCALE);last.w[k].target=(short)target;last.w[k].roll=(short)roll;
            last.w[k].los=(unsigned char)los;last.w[k].noticed=(unsigned char)noticed;
            last.w[k].alarm=(unsigned char)(w.alarm>255?255:w.alarm);last.w[k].fight=(unsigned char)(w.fight>255?255:w.fight);
            last.w[k].guard=(unsigned char)w.guard;
            last.w[k].at[0]=(short)e->v.origin[0];last.w[k].at[1]=(short)e->v.origin[1];last.w[k].at[2]=(short)e->v.origin[2];
        }
    }
    last.seen=seen;last.dry=dry;
    if(!seen || dry)return seen;
    crimes++;
    /* reportCrime: reported when an NPC in the radius would report it (Alarm 100); the bounty, the message; then
     * every NPC in the radius reacts */
    last.reported=reporter;last.before=AW_StandingCrime();
    if(reporter){
        last.bounty=AW_CrimeTheftBounty(&settings,value);
        AW_StandingModCrime(last.bounty);
        if(crime_text[0])AW_MsgBoxShow(crime_text,NULL,0);   /* the window manager: a rise of the bounty */
    }
    last.after=AW_StandingCrime();
    last.edicts+=sv.num_edicts-1;
    for(i=1;i<sv.num_edicts;i++){
        aw_crime_witness_t w;float dist,term;int victim;
        e=EDICT_NUM(i);
        if(!is_npc(e))continue;
        victim=!faction && !Q_strcasecmp((char *)source_id(e),(char *)owner);
        VectorSubtract(p->v.origin,e->v.origin,d);dist=(float)Length(d);
        if(dist>radius && !victim)continue;
        memset(&w,0,sizeof(w));
        if(!aw_crime_witness(e,&w) || !w.can_report)continue;
        if(w.guard && AW_CRIME_REPORTS(w.alarm)){last.guards++;continue;}   /* alarmed: the pursuit is CRIME-59's */
        term=AW_CrimeTheftFight(&settings,value,w.fight,w.alarm,dist/SCALE,aw_combat_ai.fFightDispMult,
                                aw_combat_ai.iFightDistanceBase,aw_combat_ai.fFightDistanceMultiplier);
        if(w.fight+term>=100 && aw_crime_attack && aw_crime_attack(e,w.fight+(int)term)){
            int k;last.attackers++;
            for(k=0;k<last.count;k++)if(!strcmp(last.w[k].name,pr_strings+e->v.netname) && !last.w[k].attacked){
                last.w[k].attacked=1;last.w[k].added=(unsigned char)term;break;}
        }
    }
    return seen;
}
/* the theft event, timed (the budget sheet: it runs only when something owned is taken, never per frame) */
static int crime(const char *owner,int faction,int value,int dry){
    double t0=Sys_FloatTime();int seen;
    memset(&last,0,sizeof(last));
    seen=crime_run(owner,faction,value,dry);
    last.ms=(Sys_FloatTime()-t0)*1000.0;
    return seen;
}
int AW_CrimeTheft(const char *owner,int faction,int value){return crime(owner,faction,value,0);}

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

/* aw_placed crime: the settings and the last theft (its witnesses: distance, line of sight, the awareness roll, Alarm, Fight) */
static void status(void){
    int i;
    Con_Printf("Crime: settings %s, thefts %lu, crimes seen %lu, bounty now %d\n",loaded>0?"loaded":loaded<0?"missing":
               "not read yet",thefts,crimes,AW_StandingCrime());
    if(loaded>0)Con_Printf("  fAlarmRadius %g, fCrimeStealing %g, fFightStealing %g, iCrimeThreshold %g, message \"%s\"\n",
                           settings.fAlarmRadius,settings.fCrimeStealing,settings.fFightStealing,settings.iCrimeThreshold,
                           crime_text);
    if(!last.owner[0])return;
    Con_Printf("  cost of that event: %d edicts walked, %d NPCs tested, %d world traces, %.1f ms\n",last.edicts,
               last.neighbors,last.traces,last.ms);
    if(last.dry)Con_Printf("Watch (no theft): from %s here %d NPCs in the alarm radius, %d would see it\n",last.owner,
                           last.neighbors,last.seen);
    else Con_Printf("Last theft: worth %d from %s%s; %d NPCs in the alarm radius, %d saw it, %s (bounty %+d: %d -> %d), "
               "%d attack, %d guards alarmed\n",
               last.value,last.owner,last.faction?" (a faction)":"",last.neighbors,last.seen,
               last.seen?last.reported?"reported":"not reported (no one with Alarm 100)":"no crime",
               last.bounty,last.before,last.after,last.attackers,last.guards);
    Con_Printf("  the player at %d %d %d\n",last.thief_at[0],last.thief_at[1],last.thief_at[2]);
    for(i=0;i<last.count;i++)
        Con_Printf("  %s at %d %d %d: %d units, sight %s, awareness %d against %d -> %s; Alarm %d, Fight %d%s%s\n",last.w[i].name,
                   last.w[i].at[0],last.w[i].at[1],last.w[i].at[2],last.w[i].distance,last.w[i].los?"yes":"no",last.w[i].roll,last.w[i].target,
                   last.w[i].noticed?"noticed":"unaware",last.w[i].alarm,last.w[i].fight,last.w[i].guard?", a guard":"",
                   last.w[i].attacked?", attacks":"");
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
/* aw_placed crime [watch OWNER | take REFERENCE]: the status and the last theft; watch: who would see a theft from
 * OWNER here now (nothing happens); take: the placed item REFERENCE of this room or cell taken as E takes it (for
 * in-game checks that need no aim) */
static void command(void){
    const char *w=Cmd_Argc()>2?Cmd_Argv(2):"";
    if(!strcmp(w,"watch") && Cmd_Argc()>3){crime(Cmd_Argv(3),0,0,1);status();return;}
    if(!strcmp(w,"take") && Cmd_Argc()>3){
        unsigned reference=(unsigned)strtoul(Cmd_Argv(3),NULL,10);
        if(!AW_PlacedTake(reference)){Con_Printf("aw_placed crime take: no placed item %u to take in this room or cell.\n",reference);return;}
        Con_Printf("aw_placed crime take: took the placed item %u.\n",reference);
        status();return;
    }
    status();
}
void AW_CrimeInit(void){
    aw_inventory_theft=inventory_theft;aw_harvest_theft=harvest_theft;
    aw_placed_crime=command;
    /* the settings at engine start, not at the first theft: in s11 that read alone made the first theft's frame 734 ms
     * on FS-UAE at 32 MB Fast (combat/settings.txt read line by line); later thefts took 14-250 ms */
    load();
}
