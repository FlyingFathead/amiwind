/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_log.h"
#include <proto/exec.h>
#include <exec/memory.h>
/* walk-profile.csv, frame-stalls.csv and frame-profile.txt are diagnostic logs held in
 * memory unless aw_logs_live (aw_log.c, BOOT-VOLUME-NOT-VALIDATED-33). */
static int logfile, stalls;
static double previous, start, sum, worst;
static int frames;
static double fps_start;
static int fps_frames,fps_tenths;
int AW_FpsTenths(void) {return fps_tenths;}
static unsigned long audio_late, missed_frames, audio_warmup, warmup_frames;
extern int r_outofsurfaces, r_outofedges, r_maxsurfsseen, r_maxedgesseen;
static unsigned long surface_overflow_frames, edge_overflow_frames;
void AW_AudioLate(int missed) {
    audio_late++;missed_frames+=missed;
    if(!frames){audio_warmup++;warmup_frames+=missed;}
}
static double stages[6], marks[6], last_stage[6];
extern int AW_DrawDistance(void);
extern cvar_t aw_surface_order;
void AW_Mark(int stage) {marks[stage]=Sys_FloatTime();}
void AW_EndMark(int stage) {last_stage[stage]=Sys_FloatTime()-marks[stage];stages[stage]+=last_stage[stage];}
void AW_ProfileFrame(void) {
    double now,dt;vec3_t *p;
    if(cls.state!=ca_connected || !cl.worldmodel)return;
    now=Sys_FloatTime();
    if(!fps_start)fps_start=now;
    fps_frames++;
    if(now-fps_start>=1.0){
        fps_tenths=(int)(fps_frames*10.0/(now-fps_start));
        if(fps_tenths>9999)fps_tenths=9999;
        fps_frames=0;fps_start=now;
    }
    if(r_outofsurfaces)surface_overflow_frames++;
    if(r_outofedges)edge_overflow_frames++;
    if(!previous){previous=start=now;return;}
    dt=now-previous;previous=now;frames++;sum+=dt;if(dt>worst)worst=dt;
    if(dt>.1) {
        if(!stalls){AW_LogHeader(AW_LOG_STALLS,"time_ms,frame,frame_us\n");stalls=1;}
        if(stalls)AW_LogPrintf(AW_LOG_STALLS,"%ld,%d,%ld\n",(long)(now*1000),frames,(long)(dt*1000000));
    }
    if(!logfile) {logfile=1;AW_LogHeader(AW_LOG_WALK,"frame,elapsed_ms,frame_us,x100,y100,z100,yaw100,hunk_bytes,distance,world_us,map,server_us,surface_order\n");}
    p=&cl_entities[cl.viewentity].origin;
    if(logfile && frames%10==0)AW_LogPrintf(AW_LOG_WALK,"%d,%ld,%ld,%ld,%ld,%ld,%ld,%d,%d,%ld,%s,%ld,%d\n",frames,(long)((now-start)*1000),(long)(dt*1000000),(long)((*p)[0]*100),(long)((*p)[1]*100),(long)((*p)[2]*100),(long)(cl.viewangles[YAW]*100),Hunk_LowMark()+Hunk_HighMark(),AW_DrawDistance(),(long)(last_stage[0]*1000000),cl.worldmodel->name,(long)(last_stage[5]*1000000),(int)aw_surface_order.value);
}
void AW_ProfileClose(void) {
    if(logfile){AW_LogStreamClose(AW_LOG_WALK);logfile=0;}if(stalls){AW_LogStreamClose(AW_LOG_STALLS);stalls=0;}
    AW_LogBegin(AW_LOG_FRAME);
    AW_LogPrintf(AW_LOG_FRAME,"efrag_peak=%d\nefrag_capacity=%d\nefrag_limit=%d\n",aw_efrags_peak,aw_efrags_capacity,AW_EFRAG_LIMIT);
    AW_LogPrintf(AW_LOG_FRAME,"surface_overflow_frames=%lu\nedge_overflow_frames=%lu\nmax_surfaces_seen=%d\nmax_edges_seen=%d\n",surface_overflow_frames,edge_overflow_frames,r_maxsurfsseen,r_maxedgesseen);
    AW_LogPrintf(AW_LOG_FRAME,"audio_warmup_updates=%lu\naudio_warmup_missed_frames=%lu\n",audio_warmup,warmup_frames);
    {AW_LogPrintf(AW_LOG_FRAME,"frames=%d\nelapsed_ms=%ld\nworst_frame_us=%ld\nheap_used_bytes=%d\n",frames,(long)(sum*1000),(long)(worst*1000000),Hunk_LowMark()+Hunk_HighMark());AW_LogPrintf(AW_LOG_FRAME,"audio_late_updates=%lu\nmissed_audio_frames=%lu\nfree_chip_bytes=%lu\nfree_fast_bytes=%lu\n",audio_late,missed_frames,AvailMem(MEMF_CHIP),AvailMem(MEMF_FAST));AW_LogPrintf(AW_LOG_FRAME,"world_ms=%ld\nentities_ms=%ld\nc2p_ms=%ld\naudio_ms=%ld\n",(long)(stages[0]*1000),(long)(stages[1]*1000),(long)(stages[2]*1000),(long)(stages[3]*1000));AW_LogPrintf(AW_LOG_FRAME,"hands_ms=%ld\nserver_ms=%ld\n",(long)(stages[4]*1000),(long)(stages[5]*1000));}
    AW_LogEnd(AW_LOG_FRAME);
}
/* dbg fpucount (aw_fpucount 1): once a second, the per-frame average and peak
 * of the maths counters in mathlib.h (ENGINE-FPU-UNIMPL-31): brush model
 * rotations and how many were rebuilt from sine/cosine, direction vectors,
 * table sine/cosine lookups and NPC targeting. The C library's trigonometry
 * is no longer linked at all (tools/check_fpu_unimplemented.py proves it per
 * build). Integer output only: printing a float would itself use the
 * library's float formatting, which executes unimplemented instructions. */
static cvar_t aw_fpucount_cvar={"aw_fpucount","0"};
static const char *const fpucount_names[AW_FPU_COUNTERS]={
    "rot","rottrig","av","table","npct","npcscan","npctest"};
static long fpucount_sum[AW_FPU_COUNTERS],fpucount_peak[AW_FPU_COUNTERS];
static double fpucount_start;static long fpucount_frames;
void AW_FpuCountInit(void) {Cvar_RegisterVariable(&aw_fpucount_cvar);}
void AW_FpuCountFrame(void) {
    int i;double now;char line[512];size_t used;long avg;
    for(i=0;i<AW_FPU_COUNTERS;i++){
        fpucount_sum[i]+=aw_fpucount[i];
        if(aw_fpucount[i]>fpucount_peak[i])fpucount_peak[i]=aw_fpucount[i];
        aw_fpucount[i]=0;
    }
    if(aw_fpucount_cvar.value<=0 || cls.state!=ca_connected){fpucount_frames=0;fpucount_start=0;
        memset(fpucount_sum,0,sizeof fpucount_sum);memset(fpucount_peak,0,sizeof fpucount_peak);return;}
    now=Sys_FloatTime();
    if(!fpucount_start){fpucount_start=now;fpucount_frames=0;
        memset(fpucount_sum,0,sizeof fpucount_sum);memset(fpucount_peak,0,sizeof fpucount_peak);return;}
    fpucount_frames++;
    if(now-fpucount_start<1.0)return;
    used=snprintf(line,sizeof line,"fpucount %ld frames fps10 %ld |",fpucount_frames,
        (long)(fpucount_frames*10.0/(now-fpucount_start)));
    for(i=0;i<AW_FPU_COUNTERS && used<sizeof line;i++){
        avg=fpucount_sum[i]*10/fpucount_frames;
        used+=snprintf(line+used,sizeof line-used," %s %ld.%ld/%ld",fpucount_names[i],avg/10,avg%10,fpucount_peak[i]);
    }
    Con_Printf("%s\n",line);
    fpucount_start=now;fpucount_frames=0;
    memset(fpucount_sum,0,sizeof fpucount_sum);memset(fpucount_peak,0,sizeof fpucount_peak);
}
