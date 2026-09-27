/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <proto/exec.h>
#include <exec/memory.h>
static FILE *logfile, *stalls;
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
static double stages[5], marks[5];
void AW_Mark(int stage) {marks[stage]=Sys_FloatTime();}
void AW_EndMark(int stage) {stages[stage]+=Sys_FloatTime()-marks[stage];}
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
        if(!stalls){stalls=fopen("frame-stalls.csv","w");if(stalls)fprintf(stalls,"time_ms,frame,frame_us\n");}
        if(stalls)fprintf(stalls,"%ld,%d,%ld\n",(long)(now*1000),frames,(long)(dt*1000000));
    }
    if(!logfile) {logfile=fopen("walk-profile.csv","w");if(logfile)fprintf(logfile,"frame,elapsed_ms,frame_us,x100,y100,z100,yaw100,hunk_bytes\n");}
    p=&cl_entities[cl.viewentity].origin;
    if(logfile && frames%10==0)fprintf(logfile,"%d,%ld,%ld,%ld,%ld,%ld,%ld,%d\n",frames,(long)((now-start)*1000),(long)(dt*1000000),(long)((*p)[0]*100),(long)((*p)[1]*100),(long)((*p)[2]*100),(long)(cl.viewangles[YAW]*100),Hunk_LowMark()+Hunk_HighMark());
}
void AW_ProfileClose(void) {
    FILE *f;if(logfile){fclose(logfile);logfile=NULL;}if(stalls){fclose(stalls);stalls=NULL;}
    f=fopen("frame-profile.txt","w");
    if(f)fprintf(f,"surface_overflow_frames=%lu\nedge_overflow_frames=%lu\nmax_surfaces_seen=%d\nmax_edges_seen=%d\n",surface_overflow_frames,edge_overflow_frames,r_maxsurfsseen,r_maxedgesseen);
    if(f)fprintf(f,"audio_warmup_updates=%lu\naudio_warmup_missed_frames=%lu\n",audio_warmup,warmup_frames);
    if(f){fprintf(f,"frames=%d\nelapsed_ms=%ld\nworst_frame_us=%ld\nheap_used_bytes=%d\n",frames,(long)(sum*1000),(long)(worst*1000000),Hunk_LowMark()+Hunk_HighMark());fprintf(f,"audio_late_updates=%lu\nmissed_audio_frames=%lu\nfree_chip_bytes=%lu\nfree_fast_bytes=%lu\n",audio_late,missed_frames,AvailMem(MEMF_CHIP),AvailMem(MEMF_FAST));fprintf(f,"world_ms=%ld\nentities_ms=%ld\nc2p_ms=%ld\naudio_ms=%ld\n",(long)(stages[0]*1000),(long)(stages[1]*1000),(long)(stages[2]*1000),(long)(stages[3]*1000));fprintf(f,"hands_ms=%ld\n",(long)(stages[4]*1000));fclose(f);}
}
