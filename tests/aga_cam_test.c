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
int main(int argc,char **argv) {
    fields();refused();
    if(argc>1)public_file(argv[1]);
    puts("camera marks rules ok");
    return 0;
}
