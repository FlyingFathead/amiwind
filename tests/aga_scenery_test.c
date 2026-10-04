/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
server_t sv;char *pr_strings="\0func_wall\0*1";
int cl_numvisedicts;entity_t *cl_visedicts[MAX_VISEDICTS];
void Sys_Error(char *fmt,...) {exit(2);}
void Host_Error(char *fmt,...) {exit(3);}
void Con_DPrintf(char *fmt,...) {}
void *Hunk_AllocName(int n,char *name){return calloc(1,n);}
int SV_ModelIndex(char *name){assert(!strcmp(name,"*1"));return 1;}
int main(void) {
    char text[24000]="";model_t model;edict_t e,world;int i;
    mplane_t planes[6];dclipnode_t nodes[6];trace_t hit;
    const char *allowed[]={"balmora","bm000","bm019","bm063"};
    const char *rejected[]={"bm064","bm099","bm100","bm01","bm000x","bm0a0","BM019","seyda","vf0698"};
    unsigned int map;
    vec3_t a={0,80,80},b={0,80,-40},mins={-16,-16,-24},maxs={16,16,32};
    memset(&model,0,sizeof(model));memset(&e,0,sizeof(e));memset(planes,0,sizeof(planes));
    for(i=0;i<6;i++){
        planes[i].normal[i/2]=(i&1)?-1:1;planes[i].type=3;
        nodes[i].planenum=i;nodes[i].children[0]=CONTENTS_EMPTY;
        nodes[i].children[1]=i==5?CONTENTS_SOLID:i+1;
    }
    planes[0].dist=136;planes[1].dist=-24;planes[2].dist=21;planes[3].dist=21;
    planes[4].dist=28;planes[5].dist=32;
    model.type=mod_brush;model.hulls[1].planes=planes;model.hulls[1].clipnodes=nodes;
    model.hulls[1].lastclipnode=5;VectorCopy(mins,model.hulls[1].clip_mins);
    model.mins[0]=40;model.maxs[0]=120;model.mins[1]=-5;model.maxs[1]=5;model.maxs[2]=4;
    sv.active=true;sv.edicts=&world;sv.models[1]=&model;
    for(i=0;i<700;i++)strcat(text,"\"classname\" \"func_wall\"\n");
    for(map=0;map<sizeof(allowed)/sizeof(allowed[0]);map++) {
    strcpy(sv.name,allowed[map]);cl_numvisedicts=0;
    a[0]=b[0]=0;a[1]=b[1]=80;
    AW_SceneryBegin(text);e.v.classname=1;e.v.model=11;e.v.angles[1]=90;
    for(i=0;i<700;i++){e.v.origin[0]=i*256;assert(AW_SceneryCapture(&e));}
    AW_SceneryLink();assert(cl_numvisedicts==700);
    memset(&hit,0,sizeof(hit));hit.fraction=1;VectorCopy(b,hit.endpos);
    AW_SceneryClip(a,mins,maxs,b,&hit);
    assert(hit.fraction<1 && fabs(hit.endpos[2]-28)<.1 && hit.ent==&world);
    a[0]=b[0]=80;a[1]=b[1]=0;hit.fraction=1;hit.allsolid=hit.startsolid=false;
    AW_SceneryClip(a,mins,maxs,b,&hit);assert(hit.fraction==1);
    /* Reloading must replace the old catalogue, never append stale objects. */
    AW_SceneryBegin("\"classname\" \"func_wall\"\n");
    e.v.origin[0]=0;assert(AW_SceneryCapture(&e));cl_numvisedicts=0;
    AW_SceneryLink();assert(cl_numvisedicts==1);
    AW_SceneryClear();cl_numvisedicts=0;AW_SceneryLink();assert(cl_numvisedicts==0);
    }
    for(map=0;map<sizeof(rejected)/sizeof(rejected[0]);map++) {
        /* Begin on a rejected map must also clear a previous valid catalogue. */
        strcpy(sv.name,"bm019");AW_SceneryBegin("\"classname\" \"func_wall\"\n");
        assert(AW_SceneryCapture(&e));
        strcpy(sv.name,rejected[map]);
        /* Capture and Link each reject the name even before Begin clears it. */
        assert(!AW_SceneryCapture(&e));cl_numvisedicts=0;
        AW_SceneryLink();assert(cl_numvisedicts==0);
        AW_SceneryBegin(text);
        assert(!AW_SceneryCapture(&e));cl_numvisedicts=0;
        AW_SceneryLink();assert(cl_numvisedicts==0);
        memset(&hit,0,sizeof(hit));hit.fraction=1;
        a[0]=b[0]=0;a[1]=b[1]=80;
        AW_SceneryClip(a,mins,maxs,b,&hit);assert(hit.fraction==1);
    }
    return 0;
}
