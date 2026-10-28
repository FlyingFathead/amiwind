/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg sweep (aw_sweep, ENTITY-SWEEP-AB; the maintainer, 27 October 2026: "some subroutine dbg command (look them up,
 * from the game F10 console) that checks the existence of all such entities across the map, a sort of sweep check"):
 * every entity class of the loaded area, what the image ships for it (B: the map's own entity text, its door bank,
 * its harvest catalogue) against what is live (C: the edicts, the bound plants), and every failure by name:
 *   actors      aw_npc rows of the map vs live actors (the CHIM window's joins counted apart); an actor without a
 *               model, a standing actor without animation (no layout and no skeleton table)
 *   corpses     aw_corpse rows vs live
 *   plants      the harvest catalogue's plants vs those bound to a live placement and pickable now; a catalogue plant
 *               with no live placement is "harvestable but not pickable"
 *   doors       the door bank's rows; a door without a link ("-") or to a map this image does not hold
 *   lights      flame rows (aw_flame; the flame list draws them, no edict): counted
 *   statics     referenced scenery and activators (func_wall with aw_ref) vs live; streamed statics counted
 * The last line is one machine line for the smoke tests: "SWEEP RESULT ok|FAIL failures=N ms=T map=NAME".
 * Read only: nothing is spawned, moved or saved. Containers have no runtime class yet (static scenery; said so).
 */
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_harvest_runtime.h"
#include "aw_region.h"
#include "aw_maps.h"
#include "aw_town.h"

#define SWEEP_NAMES 6      /* failures named per class (the count is always whole) */
enum {S_ACTOR,S_CORPSE,S_FLAME,S_STATIC,S_STREAMED,S_CLASSES};
static const char *const sweep_class[S_CLASSES]={"aw_npc","aw_corpse","aw_flame","func_wall","aw_static"};
static int failures;
static char only[16];

static int wanted(const char *name){return !only[0] || !Q_strcasecmp((char *)only,(char *)name);}
static void fail(const char *what,const char *name,int *shown){
    failures++;
    if(*shown<SWEEP_NAMES){Con_Printf("  FAIL %s: %s\n",what,name);(*shown)++;}
}
/* B: the classname counts of the loaded map's own entity text (in memory since the load; no disk read). func_wall
 * counts only rows with a reference (aw_ref): the unreferenced ones are collision. */
static void map_counts(int *count){
    const char *s=sv.worldmodel?sv.worldmodel->entities:NULL,*end,*c;int i,n;
    memset(count,0,sizeof(int)*S_CLASSES);
    while(s && (s=strchr(s,'{'))){
        end=strchr(s,'}');if(!end)break;
        c=strstr(s,"\"classname\" \"");
        if(c && c<end){
            c+=13;
            for(i=0;i<S_CLASSES;i++){
                n=(int)strlen(sweep_class[i]);
                if(!strncmp(c,sweep_class[i],n) && c[n]=='"'){
                    if(i!=S_STATIC){count[i]++;break;}
                    {const char *r=strstr(s,"\"aw_ref\" \"");if(r && r<end)count[i]++;}
                    break;
                }
            }
        }
        s=end+1;
    }
}
static int skeletal(model_t *m){
    aliashdr_t *h;
    if(!m || m->type!=mod_alias)return 0;
    h=(aliashdr_t *)Mod_Extradata(m);
    return h && h->aw_skel;
}
static const char *name_of(edict_t *e){
    eval_t *v=GetEdictFieldValue(e,"aw_source_id");
    if(v && v->string && pr_strings[v->string])return pr_strings+v->string;
    return e->v.netname?pr_strings+e->v.netname:"?";
}
static void actors(const int *map){
    int i,live[2]={0,0},no_model=0,no_anim=0,shown=0,k;edict_t *e;model_t *m;char note[128];
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || !e->v.classname)continue;
        if(!strcmp(pr_strings+e->v.classname,"aw_npc"))k=0;
        else if(!strcmp(pr_strings+e->v.classname,"aw_corpse"))k=1;
        else continue;
        live[k]++;
        m=(e->v.modelindex>0 && e->v.modelindex<MAX_MODELS)?sv.models[(int)e->v.modelindex]:NULL;
        if(!m){no_model++;sprintf(note,"%.60s (%s)",name_of(e),k?"corpse":"actor");fail("actor without a model",note,&shown);continue;}
        if(!k && !AW_AnimOf(e)->from_layout && !skeletal(m)){
            no_anim++;sprintf(note,"%.60s (%.40s)",name_of(e),m->name);fail("actor without animation",note,&shown);
        }
    }
    Con_Printf(" actors: map %ld, live %ld; corpses: map %ld, live %ld; %ld without a model, %ld without animation\n",
               (long)map[S_ACTOR],(long)live[0],(long)map[S_CORPSE],(long)live[1],(long)no_model,(long)no_anim);
    /* the map's own actors are spawned at its load; fewer live ones than it lists are missing (a CHIM window's joins
     * can only add) */
    if(live[0]+live[1]<map[S_ACTOR]+map[S_CORPSE]){
        sprintf(note,"%ld of the map's %ld actors and corpses",(long)(map[S_ACTOR]+map[S_CORPSE]-live[0]-live[1]),
                (long)(map[S_ACTOR]+map[S_CORPSE]));
        fail("not live",note,&shown);
    }
}
static void plants(void){
    int count,bound,pickable,proxy,shown=0;char note[96];
    AW_HarvestSweep(&count,&bound,&pickable,&proxy);
    Con_Printf(" plants: catalogue %ld, bound %ld, pickable now %ld%s\n",(long)count,(long)bound,(long)pickable,
               proxy?" (proxy catalogue)":"");
    if(bound<count){sprintf(note,"%ld catalogue plants with no live placement",(long)(count-bound));fail("harvestable but not pickable",note,&shown);}
}
static void doors(void){
    FILE *f=NULL;char path[64],line[384],source[16],target[16];int rows=0,linked=0,shown=0,version;
    sprintf(path,"doors-%.40s.txt",sv.name);
    if(COM_FOpenFile(path,&f)<0 || !f){sprintf(path,"scene-doors-%.32s.txt",sv.name);COM_FOpenFile(path,&f);}
    if(!f){Con_Printf(" doors: no door bank for this map\n");return;}
    version=fgets(line,sizeof(line),f) && (!strcmp(line,"AWD3\n") || !strcmp(line,"AWD2\n") || !strcmp(line,"AWD1\n"));
    while(version && fgets(line,sizeof(line),f)){
        if(Q_sscanf(line,"%15s %15s",source,target)!=2)continue;
        rows++;
        if(!strcmp(target,"-"))fail("door without a link",line[0]?source:"?",&shown);
        else if(AW_MapId(target)<0 || AW_SceneMapSize(target,NULL,0)<124){
            char note[48];sprintf(note,"%s -> %s",source,target);fail("door to a map this image does not hold",note,&shown);
        }
        else linked++;
    }
    fclose(f);
    Con_Printf(" doors: bank %ld, linked %ld\n",(long)rows,(long)linked);
}
static void counted(const int *map,int k,const char *label){
    int i,live=0,shown=0;edict_t *e;char note[64];
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || !e->v.classname || strcmp(pr_strings+e->v.classname,sweep_class[k]))continue;
        if(k==S_STATIC){eval_t *r=GetEdictFieldValue(e,"aw_ref");if(!r || !r->_float)continue;}
        live++;
    }
    Con_Printf(" %s: map %ld, live %ld\n",label,(long)map[k],(long)live);
    if(live<map[k]){sprintf(note,"%ld of the map's %ld",(long)(map[k]-live),(long)map[k]);fail(label,note,&shown);}
}
static void sweep(void){
    int map[S_CLASSES];double t0=Sys_FloatTime();
    only[0]=0;
    if(Cmd_Argc()>1)Q_strcpy_bounded(only,Cmd_Argv(1),sizeof(only));
    if(only[0] && strcmp(only,"actors") && strcmp(only,"plants") && strcmp(only,"doors") && strcmp(only,"lights") &&
       strcmp(only,"statics")){
        Con_Printf("Usage: dbg sweep [actors/plants/doors/lights/statics]\n");return;
    }
    if(!sv.active || !sv.worldmodel){Con_Printf("dbg sweep: no map loaded.\n");return;}
    failures=0;
    map_counts(map);
    Con_Printf("Sweep of %s (the loaded area; containers have no runtime class yet):\n",sv.name);
    if(wanted("actors"))actors(map);
    if(wanted("plants"))plants();
    if(wanted("doors"))doors();
    /* flames are read from the entity text by the flame list (world.qc aw_flame removes its edict) and streamed
     * statics go with their chunks, never edicts: counted, not compared */
    if(wanted("lights"))Con_Printf(" lights (flames): map %ld (drawn by the flame list)\n",(long)map[S_FLAME]);
    if(wanted("statics")){
        counted(map,S_STATIC,"statics and activators");
        Con_Printf(" streamed statics: map %ld (with their CHIM chunks)\n",(long)map[S_STREAMED]);
    }
    Con_Printf("SWEEP RESULT %s failures=%ld ms=%ld map=%s\n",failures?"FAIL":"ok",(long)failures,
               (long)((Sys_FloatTime()-t0)*1000),sv.name);
}
void AW_SweepInit(void){Cmd_AddCommand("aw_sweep",sweep);}
