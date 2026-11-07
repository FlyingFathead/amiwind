/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Halloween scene's pure parts (aw_halloween_rules.c): the parser, the cast file, the choreography lines, a
 * step's beats and frames, the mirror and the two stage layouts. */
#include <assert.h>
#include <math.h>
#include <string.h>
#include "aw_halloween.h"

static int parse(const char *a,const char *b,const char *c,aw_hw_cmd_t *out) {
    const char *argv[3]={a,b,c};
    return AW_HalloweenParse(c?3:b?2:1,argv,out);
}
static int has(const aw_hw_step_t *s,int n,const char *g) {
    int i;for(i=0;i<n;i++)if(!strcmp(s[i].group,g))return 1;
    return 0;
}

int main(void) {
    aw_hw_cmd_t c;aw_hw_cast_t cast;aw_hw_slot_t slot[AW_HALLOWEEN_MAX];const aw_hw_step_t *s;char m[32];
    int i,n,left,right,beats;
    /* dbg halloween (and halloweentest, its alias): the Dagoth Ur version by default, skeletons, stop, status */
    assert(parse("aw_halloween",NULL,NULL,&c) && c.kind==AW_HW_START && c.version==AW_HW_WITH_LEAD);
    assert(parse("aw_halloween","Skeletons",NULL,&c) && c.kind==AW_HW_START && c.version==AW_HW_SKELETONS);
    assert(parse("aw_halloween","dagoth",NULL,&c) && c.version==AW_HW_WITH_LEAD);
    assert(parse("aw_halloween","stop",NULL,&c) && c.kind==AW_HW_STOP);
    assert(parse("aw_halloween","off",NULL,&c) && c.kind==AW_HW_STOP);
    assert(parse("aw_halloween","status",NULL,&c) && c.kind==AW_HW_STATUS);
    assert(!parse("aw_halloween","zombies",NULL,&c) && c.kind==AW_HW_HELP);
    assert(!parse("aw_halloween","stop","now",&c));
    /* the benchmark, the FPS counter and the camera lock */
    assert(parse("aw_halloween","bench",NULL,&c) && c.kind==AW_HW_START && c.bench && c.version==AW_HW_WITH_LEAD);
    assert(parse("aw_halloween","bench","skeletons",&c) && c.bench && c.version==AW_HW_SKELETONS);
    assert(!parse("aw_halloween","bench","fast",&c));
    assert(parse("aw_halloween","fps","on",&c) && c.kind==AW_HW_FPS && c.value==1);
    assert(parse("aw_halloween","fps","off",&c) && c.kind==AW_HW_FPS && c.value==0);
    assert(!parse("aw_halloween","fps",NULL,&c) && !parse("aw_halloween","fps","maybe",&c));
    assert(parse("aw_halloween","camera","wide",&c) && c.kind==AW_HW_CAMERA && c.value==1);
    assert(parse("aw_halloween","camera","director",&c) && c.kind==AW_HW_CAMERA && c.value==0);
    assert(!parse("aw_halloween","skeletons","now",&c));
    /* the cast file (tools/halloween_cast.py cast_text) */
    assert(AW_HalloweenReadCast("AWHW1 1320 0\nlead progs/hw_dagothur.mdl Dagoth_Ur\ndancer progs/a_e5192b0aca1d.mdl Marelle\n"
                                "skeleton progs/hw_skeleton.mdl Skeleton\n",&cast));
    assert(cast.bpm10==AW_HALLOWEEN_BPM10 && !cast.soundtrack && cast.rows==3);
    assert(cast.row[0].role==AW_HW_LEAD && !strcmp(cast.row[0].model,"progs/hw_dagothur.mdl") && !strcmp(cast.row[0].name,"Dagoth_Ur"));
    assert(cast.row[2].role==AW_HW_SKELETON);
    assert(AW_HalloweenReadCast("AWHW1 1200 1\r\nskeleton progs/hw_skeleton.mdl Skeleton\r\n",&cast) && cast.soundtrack && cast.rows==1);
    assert(!AW_HalloweenReadCast("AWHW2 1324 0\n",&cast));
    assert(!AW_HalloweenReadCast("AWHW1 99 0\n",&cast));
    assert(!AW_HalloweenReadCast("AWHW1 1324 0\nghost progs/x.mdl X\n",&cast));
    assert(!AW_HalloweenReadCast("AWHW1 1324 0\nskeleton maps/x.bsp X\n",&cast));
    assert(!AW_HalloweenReadCast("AWHW1 1324 0\nskeleton progs/x.mdl X extra\n",&cast));
    /* the soundtrack's pre-roll: optional on the first line; the older form reads as none */
    assert(AW_HalloweenReadCast("AWHW1 1320 1 1068\nskeleton progs/hw_skeleton.mdl Skeleton\n",&cast));
    assert(cast.soundtrack && cast.preroll_ms==1068 && cast.rows==1);
    assert(AW_HalloweenReadCast("AWHW1 1320 1\nskeleton progs/hw_skeleton.mdl Skeleton\n",&cast) && cast.preroll_ms==0);
    assert(!AW_HalloweenReadCast("AWHW1 1320 1 9000\n",&cast));
    assert(!AW_HalloweenReadCast("AWHW1 1320 1 1068 7\n",&cast));
    assert(AW_HalloweenPreroll(1068,.16f,5)>1.227f && AW_HalloweenPreroll(1068,.16f,5)<1.229f);
    assert(AW_HalloweenPreroll(0,0,5)==0 && AW_HalloweenPreroll(1000,-1,5)==1.f && AW_HalloweenPreroll(3500,2,5)==5.f);
    /* the lines: the moves the maintainer named, idles only as short beats, the lead mostly casting */
    n=AW_HalloweenLine(AW_HW_SKELETON,&s);
    for(i=0;i<n;i++)if(!strcmp(s[i].group,"idle"))assert(s[i].beats<=2);
    assert(has(s,n,"hit2") && has(s,n,"hit5") && has(s,n,"knockdown") && has(s,n,"knockout") && has(s,n,"death1"));
    assert(has(s,n,"swimwalkleft") && has(s,n,"swimwalkright") && has(s,n,"spellcast") && has(s,n,"sneakforward"));
    assert(has(s,n,"walkleft"));
    /* every death is followed by its getting up (the same group backwards) */
    for(i=0;i<n;i++)if(!strncmp(s[i].group,"death",5) && s[i].play==AW_HW_FIT)
        assert(i+1<n && !strcmp(s[i+1].group,s[i].group) && s[i+1].play==AW_HW_BACK);
    /* the dancers dance their own dance (their own animation file's idle9) and nothing else */
    n=AW_HalloweenLine(AW_HW_DANCER,&s);
    for(i=0;i<n;i++)assert(!strcmp(s[i].group,"idle9") && s[i].play==AW_HW_DANCE);
    assert(AW_HalloweenFrame(100,103,8,1,9,AW_HW_DANCE)==100.f);      /* 8 frames in at its own pace: wrapped */
    n=AW_HalloweenLine(AW_HW_LEAD,&s);
    for(i=0,beats=0;i<n;i++){assert(s[i].beats);beats+=s[i].beats;}
    assert(beats==32 && has(s,n,"spellcast") && has(s,n,"idlespell"));
    /* a step's beats: its own count, or its group's length at up to 1.25 x its pace in whole pairs */
    {aw_hw_step_t fall={"knockdown",0,AW_HW_FIT},hit={"hit2",1,AW_HW_FIT};float beat=60.f/132.f;
     assert(AW_HalloweenBeats(&hit,3.f,beat)==1);
     beats=AW_HalloweenBeats(&fall,4.f,beat);
     assert(beats%2==0 && beats*beat*1.25f>=4.f && (beats-2)*beat*1.25f<4.f);
     assert(AW_HalloweenBeats(&fall,.1f,beat)==2 && AW_HalloweenBeats(&fall,60.f,beat)==16);}
    /* frames: squeezed whole, backwards (getting up) and looping cycles */
    assert(AW_HalloweenFrame(100,110,8,0,2,AW_HW_FIT)==100.f);
    assert(AW_HalloweenFrame(100,110,8,1,2,AW_HW_FIT)==105.f);
    assert(AW_HalloweenFrame(100,110,8,5,2,AW_HW_FIT)==110.f);
    assert(AW_HalloweenFrame(100,110,8,0,2,AW_HW_BACK)==110.f && AW_HalloweenFrame(100,110,8,2,2,AW_HW_BACK)==100.f);
    assert(AW_HalloweenFrame(100,103,8,0,9,AW_HW_LOOP)==100.f && AW_HalloweenFrame(100,103,8,.5f,9,AW_HW_LOOP)==101.f);
    assert(AW_HalloweenFrame(100,103,8,.45f,9,AW_HW_LOOP)==100.f);     /* 4.5 frames in: the cycle wrapped */
    /* the mirror of a side-step */
    AW_HalloweenMirror("swimwalkleft",m);assert(!strcmp(m,"swimwalkright"));
    AW_HalloweenMirror("sneakright",m);assert(!strcmp(m,"sneakleft"));
    AW_HalloweenMirror("spellcast",m);assert(!strcmp(m,"spellcast"));
    /* the Dagoth Ur version: him in the centre, the same number of dancers and skeletons on each side */
    n=AW_HalloweenLayout(AW_HW_WITH_LEAD,1,3,1,slot);
    assert(n<=AW_HALLOWEEN_MAX && slot[0].role==AW_HW_LEAD && slot[0].right==0);
    {float widest_dancer=0;
     for(left=right=0,i=0;i<n;i++)if(slot[i].role==AW_HW_DANCER){
        if(slot[i].right<0)left++;else right++;
        assert(slot[i].model<3);
        if((slot[i].right<0?-slot[i].right:slot[i].right)>widest_dancer)widest_dancer=slot[i].right<0?-slot[i].right:slot[i].right;}
     assert(left==right && left>0);
     /* the dancers right beside him, the skeletons further out, the same number on each side */
     for(left=right=0,i=0;i<n;i++)if(slot[i].role==AW_HW_SKELETON){
        if(slot[i].right<0)left++;else right++;
        assert((slot[i].right<0?-slot[i].right:slot[i].right)>widest_dancer);}
     assert(left==right && left>0);}
    /* the measured platform: 88..144 ahead, at least 80 to a side; every spot with margin from its edges */
    for(i=0;i<n;i++)assert(slot[i].ahead>=88+16 && slot[i].ahead<=144-16 && slot[i].right>=-64 && slot[i].right<=64);
    /* without a lead, or asked for: the skeletons alone */
    n=AW_HalloweenLayout(AW_HW_WITH_LEAD,0,3,1,slot);
    for(i=0;i<n;i++)assert(slot[i].role==AW_HW_SKELETON);
    assert(n==8 && AW_HalloweenLayout(AW_HW_SKELETONS,1,3,1,slot)==8 && slot[0].role==AW_HW_SKELETON);
    assert(!AW_HalloweenLayout(AW_HW_WITH_LEAD,1,3,0,slot));
    /* the camera director: shots change only on bar boundaries (4 bars of 4 beats), eased within, locked = wide */
    {float beat=60.f/132.f,span=16*beat,u,prev_u=-1,eye[3],look[3],a[3];int shot,prev=-1,seen[AW_HW_SHOTS]={0};
     const float fwd[3]={1,0,0},centre[3]={80,0,22},close[3]={80,30,20};const float fit=120,close_fit=50;
     float t,d[3],dist;int k;
     for(t=0;t<span*AW_HW_SHOTS;t+=.05f){
        shot=AW_HalloweenShot(t,beat,0,&u);
        assert(u>=0 && u<=1);
        if(shot!=prev){
            /* a cut lands on a bar: within a frame of a multiple of the shot span */
            float into=t-span*(float)(int)(t/span+.5f);
            assert(prev<0 || (into>-.06f && into<.06f));
            prev=shot;prev_u=-1;seen[shot]=1;
        }else{assert(u>=prev_u-1e-4f);prev_u=u;}
        AW_HalloweenShotPose(shot,u,fwd,centre,fit,close,close_fit,eye,look);
        AW_HalloweenAim(eye,look,a);
        assert(a[0]>-89 && a[0]<89);
        /* every shot at least at its subject's fitting distance (head to feet in frame), in front of the cast */
        for(k=0;k<3;k++)d[k]=eye[k]-look[k];
        dist=(float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
        assert(dist>=(shot==AW_HW_SHOT_CLOSE?close_fit:fit)-.01f);
        assert(eye[0]<look[0]);
     }
     for(shot=0;shot<AW_HW_SHOTS;shot++)assert(seen[shot]);
     assert(AW_HalloweenShot(span*2.5f,beat,1,&u)==AW_HW_SHOT_WIDE);
     /* the wide shot looks down at the cast's middle from the fit; the dolly ends there; the crane ends higher than it
      * starts; the close-up looks at its dancer */
     AW_HalloweenShotPose(AW_HW_SHOT_WIDE,.5f,fwd,centre,fit,close,close_fit,eye,look);
     AW_HalloweenAim(eye,look,a);assert(a[0]>AW_HALLOWEEN_FRAME_PITCH-.5f && a[0]<AW_HALLOWEEN_FRAME_PITCH+.5f);
     {float wide[3];for(k=0;k<3;k++)wide[k]=eye[k];
      AW_HalloweenShotPose(AW_HW_SHOT_DOLLY,1,fwd,centre,fit,close,close_fit,eye,look);
      for(k=0;k<3;k++)assert(eye[k]-wide[k]<.01f && wide[k]-eye[k]<.01f);}
     AW_HalloweenShotPose(AW_HW_SHOT_CRANE,0,fwd,centre,fit,close,close_fit,eye,look);t=eye[2];
     AW_HalloweenShotPose(AW_HW_SHOT_CRANE,1,fwd,centre,fit,close,close_fit,eye,look);assert(eye[2]>t+60);
     AW_HalloweenShotPose(AW_HW_SHOT_CLOSE,0,fwd,centre,fit,close,close_fit,eye,look);assert(look[1]==30);
     /* looking straight ahead and down a little */
     {const float e[3]={0,0,22},l[3]={100,0,4};AW_HalloweenAim(e,l,a);assert(a[1]>-1e-3f && a[1]<1e-3f && a[0]>9 && a[0]<11);}}
    /* the whole cast in frame: every corner of the cast's box inside the field of view, looking down at its middle */
    {const float c[3]={80,0,22},f[3]={1,0,0};float eye[3],a[3],d[3],flat,yaw,pitch;int corner;
     AW_HalloweenFrameCast(c,62,28,f,90,73.74f,eye);
     assert(eye[0]<80 && eye[2]>22);
     AW_HalloweenAim(eye,c,a);
     assert(a[0]>AW_HALLOWEEN_FRAME_PITCH-.5f && a[0]<AW_HALLOWEEN_FRAME_PITCH+.5f);
     for(corner=0;corner<4;corner++){
        d[0]=c[0]-eye[0];d[1]=(corner&1?62.f:-62.f)-eye[1];d[2]=(corner&2?50.f:-6.f)-eye[2];
        flat=(float)sqrt(d[0]*d[0]+d[1]*d[1]);
        yaw=(float)(atan2(d[1],d[0])*180/3.14159265);pitch=(float)(atan2(-d[2],flat)*180/3.14159265);
        assert(yaw>-45 && yaw<45);
        assert(pitch-a[0]>-36.87f && pitch-a[0]<36.87f);
     }}
    /* the frame's edge rays: looking along +x, the left and right edges at +-45 degrees (left = +y in Quake), the top
     * edge up by half the vertical field; every ray DIST long; none points below the view's level line */
    {const float e[3]={0,0,0},l[3]={100,0,0};float ends[AW_HW_EDGE_RAYS][3],n;int k2;
     AW_HalloweenEdgeRays(e,l,90,73.74f,64,ends);
     for(k2=0;k2<AW_HW_EDGE_RAYS;k2++){
        n=(float)sqrt(ends[k2][0]*ends[k2][0]+ends[k2][1]*ends[k2][1]+ends[k2][2]*ends[k2][2]);
        assert(n>63.9f && n<64.1f);assert(ends[k2][0]>0);assert(ends[k2][2]>-1e-3f);
     }
     assert(ends[0][1]>44 && ends[0][1]<46 && ends[0][2]<1e-3f);   /* left middle: (45.25, 45.25, 0) */
     assert(ends[1][1]<-44 && ends[1][1]>-46);                     /* right middle */
     assert(ends[3][1]>-1e-3f && ends[3][1]<1e-3f && ends[3][2]>34 && ends[3][2]<40);  /* top middle: up 36.87 deg */
     assert(ends[2][1]>0 && ends[4][1]<0 && ends[2][2]>0 && ends[4][2]>0);}
    /* the benchmark's figures */
    {float times[200];aw_hw_bench_t b;
     for(i=0;i<200;i++)times[i]=.05f;
     times[10]=.5f;times[20]=.25f;
     AW_HalloweenBenchFigures(times,200,&b);
     assert(b.frames==200 && b.minimum>1.99f && b.minimum<2.01f);
     assert(b.low1>2.66f && b.low1<2.67f);                 /* two slowest: (0.5 + 0.25) / 2 */
     assert(b.seconds>10.64f && b.seconds<10.66f && b.average>18.7f && b.average<18.85f);   /* 198 x 0.05 + 0.75 */
     AW_HalloweenBenchFigures(times,0,&b);assert(!b.frames && !b.average);}
    /* BENCH-RESULT-FILE-62: the figures measured apart, from a fixed list of frame and disk times: 600 frames of
     * 0.2 s (5 fps) drawn, five slow drawn frames (0.4, 0.5, 0.6, 0.8, 1.0 s), and three frames that waited on the disk
     * (2.5 s with 2.3 s of it disk, 0.7 s with 0.5 s disk, 0.25 s with 0.01 s disk) */
    {static float times[600],disk[600];aw_hw_bench_split_t s;aw_hw_bench_t b;char name[AW_HW_BENCH_NAME];
     for(i=0;i<600;i++){times[i]=.2f;disk[i]=0;}
     times[100]=.4f;times[200]=.5f;times[300]=.6f;times[400]=.8f;times[500]=1.0f;
     times[11]=2.5f;disk[11]=2.3f;times[50]=.7f;disk[50]=.5f;times[599]=.25f;disk[599]=.01f;
     AW_HalloweenBenchSplit(times,disk,600,&s);
     /* every frame: the old figures, unchanged */
     AW_HalloweenBenchFigures(times,600,&b);
     assert(s.all.frames==600 && s.all.average==b.average && s.all.minimum==b.minimum && s.all.low1==b.low1);
     /* 592 x 0.2 + 3.3 (slow drawn) + 3.45 (disk frames) = 125.15 s */
     assert(s.all.seconds>125.14f && s.all.seconds<125.16f);
     assert(s.all.average>4.793f && s.all.average<4.796f);            /* 600 / 125.15 */
     assert(s.all.minimum>.399f && s.all.minimum<.401f);               /* the 2.5 s disk frame */
     assert(s.all.low1>.9835f && s.all.low1<.9837f);                   /* 6 slowest: 2.5+1.0+0.8+0.7+0.6+0.5 = 6.1 s */
     /* the drawing: the 597 frames with no disk wait */
     assert(s.drawing.frames==597);
     assert(s.drawing.seconds>121.69f && s.drawing.seconds<121.71f);   /* 592 x 0.2 + 3.3 */
     assert(s.drawing.average>4.9054f && s.drawing.average<4.9058f);   /* 597 / 121.7 */
     assert(s.drawing.minimum>.999f && s.drawing.minimum<1.001f);      /* the 1.0 s frame */
     assert(s.drawing.low1>1.5150f && s.drawing.low1<1.5153f);        /* 5 slowest drawn: 1.0+0.8+0.6+0.5+0.4 = 3.3 s */
     /* the disk side: three frames, 2.81 s of waits, the worst frame 12 */
     assert(s.disk_frames==3 && s.worst_disk_frame==12);
     assert(s.disk_seconds>2.809f && s.disk_seconds<2.811f && s.worst_disk>2.299f && s.worst_disk<2.301f);
     /* the five slowest frames, 1-based, slowest first */
     assert(s.slowest[0]==12 && s.slowest[1]==501 && s.slowest[2]==401 && s.slowest[3]==51 && s.slowest[4]==301);
     /* no disk times known (NULL): every frame counts as drawing, no disk side */
     AW_HalloweenBenchSplit(times,NULL,600,&s);
     assert(s.drawing.frames==600 && s.drawing.average==s.all.average && !s.disk_frames && !s.worst_disk_frame);
     /* fewer frames than the slowest list: the rest 0; every frame waited: no drawing figures */
     AW_HalloweenBenchSplit(times+11,disk+11,1,&s);
     assert(s.slowest[0]==1 && !s.slowest[1] && s.all.frames==1 && !s.drawing.frames && !s.drawing.average);
     assert(s.disk_frames==1 && s.worst_disk_frame==1);
     AW_HalloweenBenchSplit(times,disk,0,&s);assert(!s.all.frames && !s.disk_frames && !s.slowest[0]);
     /* the result file's name: fits an Amiga file name, the build cut, its odd characters replaced */
     AW_HalloweenBenchName("0.0.62-dev1",1,name);assert(!strcmp(name,"halloween-0.0.62-dev1-001.txt"));
     assert(strlen(name)<=30);
     AW_HalloweenBenchName("0.0.62-dev1 extra long",42,name);assert(!strcmp(name,"halloween-0.0.62-dev1_-042.txt"));
     assert(strlen(name)<=30);
     AW_HalloweenBenchName("a/b:c",1000,name);assert(!strcmp(name,"halloween-a_b_c-999.txt"));}
    return 0;
}
