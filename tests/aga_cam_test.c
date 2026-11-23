/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_cam_rules.c alone: the camera marks line (dbg cam mark / recall / list,
 * docs/CAMERA_MARKS.md). Every line of the public file given as the first
 * argument parses; marks round-trip through the writer; bad lines are refused
 * as tools/camera_marks.py refuses them. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_cam.h"

static int near(float a,float b){return fabsf(a-b)<.001f;}
static int parse(const char *line){aw_cam_mark_t m;return AW_CamParse(line,&m);}

static void public_file(const char *path) {
    FILE *f=fopen(path,"rb");char line[1024];int n,first=1,marks=0,status;aw_cam_mark_t m;
    assert(f);
    while(fgets(line,sizeof(line),f)){
        n=(int)strlen(line);assert(n && line[n-1]=='\n');line[n-1]=0;
        if(first){assert(!strcmp(line,AW_CAM_MAGIC));first=0;continue;}
        status=AW_CamParse(line,&m);
        if(status<0)fprintf(stderr,"refused: %s\n",line);
        assert(status>=0);
        if(status){
            char again[AW_CAM_LINE];aw_cam_mark_t back;
            assert(AW_CamFormat(&m,again,sizeof(again))>0);
            assert(!strcmp(again,line));       /* the public file is written in the writer's own form */
            assert(AW_CamParse(again,&back)==1 && !memcmp(&back,&m,sizeof(m)));
            marks++;
        }
    }
    fclose(f);
    assert(marks>=11);
}
static void fields(void) {
    aw_cam_mark_t m;char out[AW_CAM_LINE];
    assert(AW_CamParse("bm1|global|-20088 -14638|113 -3|1200|off|540|Balmora 1",&m)==1);
    assert(m.global && !m.has_z && near(m.point[0],-20088) && near(m.point[1],-14638));
    assert(near(m.yaw,113) && near(m.pitch,-3) && m.time==1200 && m.headlamp==0 && m.fog==540);
    assert(!strcmp(m.note,"Balmora 1"));
    assert(AW_CamParse("tz|global|1 2 300|0 0|-|-|-|",&m)==1 && m.has_z && near(m.point[2],300));
    assert(m.time==-1 && m.headlamp==-1 && m.fog==-1 && !m.note[0]);
    assert(AW_CamParse("vivec-palace|vpi015|0 -64.7 -83.9|90 0|1200|off|-|x",&m)==1);
    assert(!m.global && !strcmp(m.map,"vpi015") && m.has_z && near(m.point[1],-64.7f) && near(m.point[2],-83.9f));
    /* the writer: two decimals at most, no trailing zeros, "-0" as "0" */
    m.point[0]=-0.001f;m.point[1]=12.345f;m.point[2]=-83.9f;m.yaw=359.5f;m.pitch=0;m.headlamp=1;m.fog=4096;m.time=5;
    assert(AW_CamFormat(&m,out,sizeof(out))>0);
    assert(!strcmp(out,"vivec-palace|vpi015|0 12.35 -83.9|359.5 0|0005|on|4096|x"));
    assert(AW_CamFormat(&m,out,10)==0);                                 /* does not fit */
    m.yaw=360;assert(AW_CamFormat(&m,out,sizeof(out))==0);            /* yaw 0..<360 */
}
static void refused(void) {
    assert(parse("")==0 && parse("# a comment")==0);
    assert(parse("bm1|global|-20088|113 -3|1200|off|540|")<0);          /* global: X Y at least */
    assert(parse("bm1|global|1 2 3 4|0 0|1200|off|540|")<0);
    assert(parse("m|vpi015|1 2|0 0|1200|off|540|")<0);                  /* map: X Y Z */
    assert(parse("m|VPI015|1 2 3|0 0|1200|off|540|")<0);                /* map names are lower case */
    assert(parse("m|vpi015|1 2 40000|0 0|1200|off|540|")<0);            /* local range */
    assert(parse("m|global|3000000 0|0 0|1200|off|540|")<0);            /* global range, as dbg tp */
    assert(parse("m|global|1  2|0 0|1200|off|540|")<0);                 /* single spaces */
    assert(parse("m|global|1 2e3|0 0|1200|off|540|")<0);                /* digits, sign and point only */
    assert(parse("m|global|1 2|360 0|1200|off|540|")<0 && parse("m|global|1 2|0 81|1200|off|540|")<0);
    assert(parse("m|global|1 2|0 0|2400|off|540|")<0 && parse("m|global|1 2|0 0|1260|off|540|")<0);
    assert(parse("m|global|1 2|0 0|120|off|540|")<0);
    assert(parse("m|global|1 2|0 0|1200|maybe|540|")<0);
    assert(parse("m|global|1 2|0 0|1200|off|99|")<0 && parse("m|global|1 2|0 0|1200|off|4097|")<0);
    assert(parse("m|global|1 2|0 0|1200|off|540")<0);                   /* eight fields */
    assert(parse("m|global|1 2|0 0|1200|off|540|a|b")<0);
    assert(parse("bad name|global|1 2|0 0|1200|off|540|")<0);
    assert(parse("a2345678901234567890123456789012|global|1 2|0 0|1200|off|540|")<0);  /* 32 characters */
    assert(parse("m|global|1 2|0 0|1200|off|540|tab\there")<0);
    assert(AW_CamSameName("BM1","bm1") && !AW_CamSameName("bm1","bm10"));
    assert(AW_CamValidName("a.b-c_9") && !AW_CamValidName("a b") && !AW_CamValidName(""));
}
/* ---- the camera shots (dbg cam pan, dbg cam track; DBG-CAM-PAN-TRACK-68) ---- */
static int close_to(float a,float b,float tolerance){return fabsf(a-b)<=tolerance;}
static float not_a_number(void){volatile float zero=0;return zero/zero;}
static float travel_at(aw_cam_shot_t s,float clock){s.clock=clock;return AW_CamShotTravel(&s);}
/* the speed at CLOCK, by a centred difference of a millisecond either side */
static float speed_at(const aw_cam_shot_t *s,float clock){return (travel_at(*s,clock+.001f)-travel_at(*s,clock-.001f))/.002f;}
/* the default pan, 360 degrees at the field of view of 90 over 6 s, 3 s held at each end */
static void pan_360(void) {
    aw_cam_shot_t s;float t,last,step=0,most=0;int i;
    assert(close_to(AW_CamPanSpeed(90),15,1e-6f));                          /* 90 / 6 s */
    assert(AW_CamShotBegin(&s,360,AW_CamPanSpeed(90),AW_CAM_SHOT_HOLD));
    assert(close_to(s.ease,1.25f,1e-6f) && close_to(AW_CamShotMoveSeconds(&s),25.25f,1e-4f));
    assert(close_to(AW_CamShotSeconds(&s),31.25f,1e-4f));                   /* 3 + 24 + 1.25 + 3 */
    /* the opening hold: not a degree */
    for(t=0;t<=3;t+=.25f)assert(travel_at(s,t)==0);
    /* eased in: the speed rises from 0 to 15 over 1.25 s, smoothly (never down, never over the speed) */
    assert(speed_at(&s,3.002f)<.01f);
    for(t=3.01f,last=0;t<4.25f;t+=.01f){float v=speed_at(&s,t);assert(v>=last-1e-2f && v<=15+1e-2f);last=v;}
    assert(close_to(travel_at(s,4.25f),15*1.25f/2,1e-3f));                  /* the ramp covers half its time at speed */
    /* the constant middle: from the end of the ramp (clock 4.25) to the start of the other (3 + 24 = 27) */
    for(t=4.3f;t<26.95f;t+=.5f)assert(close_to(speed_at(&s,t),15,.02f));
    assert(speed_at(&s,27.6f)<15-.5f);                                      /* easing out */
    /* eased out: the mirror of the start, ending exactly at 360 */
    for(t=0;t<=1.25f;t+=.05f)assert(close_to(travel_at(s,28.25f-t),360-travel_at(s,3+t),2e-3f));
    assert(speed_at(&s,28.248f)<.02f);
    /* the closing hold: exactly where it began (360 = a whole turn) */
    for(t=28.25f;t<=31.25f;t+=.25f)assert(travel_at(s,t)==360);
    /* driven by frame time: frames of different lengths that add up to the same clock give the same angle, and
     * no frame moves more than the speed allows for its own length (no quantised steps) */
    {aw_cam_shot_t a=s,b=s;unsigned seed=12345;
     for(i=0;i<200;i++)AW_CamShotStep(&a,.05f);                             /* 10 s in 200 even frames */
     for(t=0;t<10-1e-4f;t+=step){seed=seed*1103515245u+12345u;step=.01f+(float)(seed>>16&1023)/1023.f*.23f;
         if(t+step>10)step=10-t;
         last=AW_CamShotTravel(&b);AW_CamShotStep(&b,step);
         if(AW_CamShotTravel(&b)-last>most)most=AW_CamShotTravel(&b)-last;
         assert(AW_CamShotTravel(&b)-last<=15*step+1e-3f && AW_CamShotTravel(&b)>=last);}
     assert(close_to(a.clock,10,1e-3f) && close_to(b.clock,10,1e-3f));
     assert(close_to(AW_CamShotTravel(&a),AW_CamShotTravel(&b),5e-2f));
     assert(most>0 && most<15*.24f+1e-3f);}
    /* a long frame (a load) counts a quarter second: no jump; a negative or not-a-number one counts nothing */
    {aw_cam_shot_t c=s;c.clock=10;AW_CamShotStep(&c,2);assert(close_to(c.clock,10.25f,1e-5f));
     AW_CamShotStep(&c,-1);AW_CamShotStep(&c,not_a_number());assert(close_to(c.clock,10.25f,1e-5f));}
    /* it ends by itself after the closing hold */
    {aw_cam_shot_t d=s;int frames=0;
     while(!AW_CamShotDone(&d) && frames<10000){AW_CamShotStep(&d,1.f/50);frames++;}
     assert(AW_CamShotDone(&d) && frames>=1562 && frames<=1563 && AW_CamShotTravel(&d)==360);   /* 31.25 s at 50 fps */
     d.clock=31.2f;assert(!AW_CamShotDone(&d));}
}
/* dbg cam pan 180 5: 5 s held, 180 degrees, 5 s held */
static void pan_180_hold_5(void) {
    aw_cam_shot_t s;float t;
    assert(AW_CamShotBegin(&s,180,15,5));
    assert(close_to(AW_CamShotMoveSeconds(&s),13.25f,1e-4f) && close_to(AW_CamShotSeconds(&s),23.25f,1e-4f));
    for(t=0;t<=5;t+=.5f)assert(travel_at(s,t)==0);                          /* the opening frame, 5 s */
    assert(travel_at(s,5.5f)>0 && travel_at(s,5.5f)<1);                    /* easing in: slow */
    assert(close_to(travel_at(s,5+13.25f/2),90,1e-3f));                     /* half way at half the move */
    for(t=6.5f;t<16.75f;t+=.5f)assert(close_to(speed_at(&s,t),15,.02f));    /* constant between the ramps */
    for(t=18.25f;t<=23.25f;t+=.5f)assert(travel_at(s,t)==180);              /* the closing frame, 5 s */
    s.clock=23.2f;assert(!AW_CamShotDone(&s));s.clock=23.25f;assert(AW_CamShotDone(&s));
}
/* the speed word: dbg cam pan 360 3 speed 30 takes half the constant time; the cap and the field of view */
static void pan_speed(void) {
    aw_cam_shot_t s;float t;
    assert(AW_CamShotBegin(&s,360,30,3) && close_to(AW_CamShotMoveSeconds(&s),13.25f,1e-4f));
    for(t=5;t<15;t+=.5f)assert(close_to(speed_at(&s,t),30,.04f));
    assert(close_to(AW_CamPanSpeed(60),10,1e-6f) && close_to(AW_CamPanSpeed(120),20,1e-6f));
    assert(close_to(AW_CamPanSpeed(5),15,1e-6f) && close_to(AW_CamPanSpeed(not_a_number()),15,1e-6f));   /* out of range: 90 */
    assert(AW_CamPanSpeed(170)<=AW_CAM_PAN_SPEED_MAX);
}
/* a short move eases over less time with no constant middle; the track's default; refused values */
static void short_track_and_refusals(void) {
    aw_cam_shot_t s;float t,last=0;
    assert(AW_CamShotBegin(&s,10,15,0) && close_to(s.ease,10.f/15,1e-6f));
    assert(close_to(AW_CamShotMoveSeconds(&s),20.f/15,1e-5f) && close_to(travel_at(s,10.f/15),5,1e-3f));
    for(t=0;t<=20.f/15;t+=.01f){float d=travel_at(s,t);assert(d>=last && d<=10);last=d;}
    assert(travel_at(s,20.f/15)==10);
    assert(AW_CamShotBegin(&s,256,AW_CAM_TRACK_SPEED,AW_CAM_SHOT_HOLD) && close_to(AW_CamShotMoveSeconds(&s),9.25f,1e-4f));
    assert(!AW_CamShotBegin(&s,0,15,3) && !AW_CamShotBegin(&s,-10,15,3) && !AW_CamShotBegin(&s,360,0,3));
    assert(!AW_CamShotBegin(&s,360,15,-1) && !AW_CamShotBegin(&s,360,15,AW_CAM_SHOT_HOLD_MAX+1));
    assert(!AW_CamShotBegin(&s,not_a_number(),15,3) && !AW_CamShotBegin(&s,360,15,not_a_number()));
}
/* the track's turn to a mark's view: the short way round */
static void turns(void) {
    assert(close_to(AW_CamTurn(10,350),-20,1e-4f) && close_to(AW_CamTurn(350,10),20,1e-4f));
    assert(close_to(AW_CamTurn(0,180),180,1e-4f) && close_to(AW_CamTurn(90,90),0,1e-4f));
    assert(close_to(AW_CamTurn(-720,45),45,1e-3f) && close_to(AW_CamTurn(400,30),-10,1e-3f));
    assert(AW_CamTurn(not_a_number(),10)==0);
}
int main(int argc,char **argv) {
    fields();refused();
    if(argc>1)public_file(argv[1]);
    puts("camera marks rules ok");
    pan_360();pan_180_hold_5();pan_speed();short_track_and_refusals();turns();
    puts("camera shots ok");
    return 0;
}
