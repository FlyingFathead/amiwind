/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Halloween scene's pure parts (aw_halloween.h, docs/HALLOWEEN.md): the parser, the cast file, the
 * choreography, a step's frame and the stage layout. No engine state: the host test runs them.
 *
 * The choreography is our own, made of the game's own animation groups (their Morrowind names, the shared tables'
 * groups): the dancers' and the skeletons' lines are fast moves on the beat (spellcasting, the hits, knockdowns and
 * knockouts, deaths and the getting up again, the swimming side-steps in quick succession, sneaks and walks), idles
 * only as a short beat between them; the lead (Dagoth Ur, on his own table) poses more than he dances: his
 * spellcasting on the strong beats with an idle or a pose between.
 */
#include <math.h>
#include <string.h>
#include "aw_halloween.h"
/* mathlib.c's FPU-safe forms: libm's sin, cos and atan2 reach instructions a 68040 does not implement */
float Q_SinRad(float radians);
float Q_CosRad(float radians);
double Q_atan2(double y,double x);
float Q_TanRad(float radians);
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int same(const char *a,const char *b) {
    for(;*a && *b;a++,b++){
        int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;
        if(x!=y)return 0;
    }
    return !*a && !*b;
}

int AW_HalloweenParse(int argc,const char **argv,aw_hw_cmd_t *out) {
    const char *w,*v;
    memset(out,0,sizeof(*out));
    out->kind=AW_HW_START;out->version=AW_HW_WITH_LEAD;
    if(argc<2)return 1;
    if(argc>3)goto help;
    w=argv[1];v=argc==3?argv[2]:NULL;
    if(same(w,"bench")){
        out->bench=1;
        if(!v || same(v,"dagoth"))return 1;
        if(same(v,"skeletons")){out->version=AW_HW_SKELETONS;return 1;}
        goto help;
    }
    if(same(w,"fps") && v){
        out->kind=AW_HW_FPS;
        if(same(v,"on") || same(v,"1")){out->value=1;return 1;}
        if(same(v,"off") || same(v,"0"))return 1;
        goto help;
    }
    if(same(w,"camera") && v){
        out->kind=AW_HW_CAMERA;
        if(same(v,"wide") || same(v,"lock")){out->value=1;return 1;}
        if(same(v,"director") || same(v,"shots"))return 1;
        goto help;
    }
    if(v)goto help;
    if(same(w,"dagoth") || same(w,"lead") || same(w,"on"))return 1;
    if(same(w,"skeletons")){out->version=AW_HW_SKELETONS;return 1;}
    if(same(w,"stop") || same(w,"off")){out->kind=AW_HW_STOP;return 1;}
    if(same(w,"status")){out->kind=AW_HW_STATUS;return 1;}
help:
    out->kind=AW_HW_HELP;
    return 0;
}

/* one word of at most size-1 bytes (no spaces), 0 when none; *p moves past it */
static int word(const char **p,char *out,int size) {
    int n=0;
    while(**p==' ')(*p)++;
    while(**p && **p!=' ' && **p!='\n' && **p!='\r'){if(n>=size-1)return 0;out[n++]=*(*p)++;}
    out[n]=0;
    return n>0;
}
static int number(const char *s,int *out) {
    int n=0;
    if(!*s)return 0;
    for(;*s;s++){if(*s<'0' || *s>'9' || n>100000)return 0;n=n*10+(*s-'0');}
    *out=n;return 1;
}
float AW_HalloweenPreroll(int preroll_ms,float lead,float box) {
    float s=(preroll_ms>0?preroll_ms/1000.f:0.f)+(lead>0?lead:0.f);
    if(s>box)s=box;
    return s<0?0:s;
}
int AW_HalloweenReadCast(const char *text,aw_hw_cast_t *out) {
    char w[AW_HALLOWEEN_PATH];const char *p=text;
    memset(out,0,sizeof(*out));
    if(!text || !word(&p,w,sizeof(w)) || strcmp(w,"AWHW1"))return 0;
    if(!word(&p,w,sizeof(w)) || !number(w,&out->bpm10) || out->bpm10<300 || out->bpm10>3000)return 0;
    if(!word(&p,w,sizeof(w)) || (strcmp(w,"0") && strcmp(w,"1")))return 0;
    out->soundtrack=w[0]=='1';
    /* optional on the first line: the soundtrack's leading silence in milliseconds (its pre-roll) */
    while(*p==' ')p++;
    if(*p>='0' && *p<='9'){
        if(!word(&p,w,sizeof(w)) || !number(w,&out->preroll_ms) || out->preroll_ms>AW_HALLOWEEN_MAX_PREROLL_MS)return 0;
        while(*p==' ')p++;
        if(*p && *p!='\n' && *p!='\r')return 0;
    }
    for(;;){
        aw_hw_row_t *r;
        while(*p=='\r' || *p=='\n' || *p==' ')p++;
        if(!*p)break;
        if(out->rows>=AW_HALLOWEEN_MAX_ROWS)return 0;
        r=&out->row[out->rows];
        if(!word(&p,w,sizeof(w)))return 0;
        if(!strcmp(w,"lead"))r->role=AW_HW_LEAD;
        else if(!strcmp(w,"dancer"))r->role=AW_HW_DANCER;
        else if(!strcmp(w,"skeleton"))r->role=AW_HW_SKELETON;
        else return 0;
        if(!word(&p,r->model,sizeof(r->model)) || strncmp(r->model,"progs/",6))return 0;
        if(!word(&p,r->name,sizeof(r->name)))return 0;
        while(*p==' ')p++;
        if(*p && *p!='\n' && *p!='\r')return 0;
        out->rows++;
    }
    return 1;
}

/* The lead: his spellcasting on the strong beats, an idle or a pose between (32 beats). */
static const aw_hw_step_t lead_line[]={
    {"idle",2,AW_HW_FIT},{"spellcast",4,AW_HW_FIT},{"idlespell",2,AW_HW_FIT},
    {"spellturnleft",2,AW_HW_FIT},{"spellturnright",2,AW_HW_FIT},{"spellcast",4,AW_HW_FIT},{"idle2",4,AW_HW_FIT},
    {"attack2",2,AW_HW_FIT},{"idlespell",2,AW_HW_FIT},{"spellcast",4,AW_HW_FIT},{"idle3",4,AW_HW_FIT},
};
/* The dancers: their own dance from the game (Desele's dancers' own animation file, anim_dancingGirl: its idle9,
 * the table's d:idle9 in their view; DANCER-OWN-ANIM-IGNORED-53), looping at its own pace. */
static const aw_hw_step_t dancer_line[]={
    {"idle9",16,AW_HW_DANCE},
};
/* The skeletons: the line dance of the skeletons-only version, and the sides of the other. */
static const aw_hw_step_t skeleton_line[]={
    {"hit2",1,AW_HW_FIT},{"hit3",1,AW_HW_FIT},{"hit4",1,AW_HW_FIT},{"hit5",1,AW_HW_FIT},
    {"swimwalkleft",1,AW_HW_LOOP},{"swimwalkright",1,AW_HW_LOOP},{"swimwalkleft",1,AW_HW_LOOP},{"swimwalkright",1,AW_HW_LOOP},
    {"spellcast",0,AW_HW_FIT},
    {"idle",2,AW_HW_FIT},
    {"knockdown",0,AW_HW_FIT},
    {"sneakforward",2,AW_HW_LOOP},{"sneakback",2,AW_HW_LOOP},
    {"death1",0,AW_HW_FIT},{"death1",0,AW_HW_BACK},
    {"swimwalkleft",1,AW_HW_LOOP},{"swimwalkright",1,AW_HW_LOOP},{"swimwalkleft",1,AW_HW_LOOP},{"swimwalkright",1,AW_HW_LOOP},
    {"knockout",0,AW_HW_FIT},
    {"idle",2,AW_HW_FIT},
    {"hit5",1,AW_HW_FIT},{"hit4",1,AW_HW_FIT},{"hit3",1,AW_HW_FIT},{"hit2",1,AW_HW_FIT},
    {"death3",0,AW_HW_FIT},{"death3",0,AW_HW_BACK},
    {"walkleft",2,AW_HW_LOOP},{"walkright",2,AW_HW_LOOP},
    {"spellcast",0,AW_HW_FIT},
    {"death5",0,AW_HW_FIT},{"death5",0,AW_HW_BACK},
    {"idle",2,AW_HW_FIT},
};
int AW_HalloweenLine(int role,const aw_hw_step_t **steps) {
    if(role==AW_HW_LEAD){*steps=lead_line;return (int)(sizeof(lead_line)/sizeof(lead_line[0]));}
    if(role==AW_HW_DANCER){*steps=dancer_line;return (int)(sizeof(dancer_line)/sizeof(dancer_line[0]));}
    *steps=skeleton_line;return (int)(sizeof(skeleton_line)/sizeof(skeleton_line[0]));
}

int AW_HalloweenBeats(const aw_hw_step_t *s,float seconds,float beat) {
    int n;
    if(s->beats)return s->beats;
    if(!(beat>0))return 2;
    /* its own length at up to 1.25 times its pace, rounded up to whole pairs of beats */
    n=(int)(seconds/(beat*1.25f)+.999f);
    if(n<2)n=2;
    if(n&1)n++;
    if(n>16)n=16;
    return n;
}

float AW_HalloweenFrame(unsigned first,unsigned last,float rate,float into,float span,int play) {
    int frames=last>=first?(int)(last-first)+1:1;float u,pos;
    if(into<0)into=0;
    if(play==AW_HW_LOOP || play==AW_HW_DANCE){
        int f;
        if(!(rate>0))rate=8;
        pos=into*rate*(play==AW_HW_DANCE?1.f:1.25f);
        f=(int)pos;
        return (float)(first+(unsigned)(f%frames));
    }
    u=span>0?into/span:1;
    if(u>1)u=1;
    pos=u*(float)(frames-1);
    return play==AW_HW_BACK?(float)last-pos:(float)first+pos;
}

void AW_HalloweenMirror(const char *group,char *out) {
    const char *l=strstr(group,"left"),*r=strstr(group,"right");
    size_t n=strlen(group);
    if(n>=32){out[0]=0;strncat(out,group,31);return;}
    if(l && n+1<32){memcpy(out,group,(size_t)(l-group));strcpy(out+(l-group),"right");strcat(out,l+4);return;}
    if(r){memcpy(out,group,(size_t)(r-group));strcpy(out+(r-group),"left");strcat(out,r+5);return;}
    strcpy(out,group);
}

static int put(aw_hw_slot_t *out,int n,int role,int model,float right,float ahead) {
    if(n>=AW_HALLOWEEN_MAX)return n;
    out[n].role=role;out[n].model=model;out[n].right=right;out[n].ahead=ahead;
    return n+1;
}
int AW_HalloweenLayout(int version,int leads,int dancers,int skeletons,aw_hw_slot_t *out) {
    int n=0,i;
    if(skeletons<1)return 0;
    /* The Balmora stage platform, measured from its own floor (the scene's stage grid, 27 October 2026, from the
     * MiniWind arrival facing yaw 90): one level from 88 to 144 units ahead and at least 80 to each side, a stairway
     * up toward the player in front of it (the take 5 cast stood on its top step, 80 ahead). One row through its
     * middle, 116 ahead: 28 units from its front and back edges, at most 60 to a side (20 from the measured width). */
    if(version==AW_HW_WITH_LEAD && leads>0){
        /* him in the centre, the dancers right beside him (two each side), the skeletons further out (two each side) */
        static const float dx[4]={-16,16,-30,30},sx[4]={-46,46,-60,60};
        n=put(out,n,AW_HW_LEAD,0,0,AW_HALLOWEEN_STAGE_AHEAD);
        for(i=0;dancers>0 && i<4;i++)n=put(out,n,AW_HW_DANCER,i%dancers,dx[i],AW_HALLOWEEN_STAGE_AHEAD);
        for(i=0;i<4;i++)n=put(out,n,AW_HW_SKELETON,i%skeletons,sx[i],AW_HALLOWEEN_STAGE_AHEAD);
        return n;
    }
    /* the skeletons alone: a line of eight, 16 apart */
    for(i=0;i<8;i++)n=put(out,n,AW_HW_SKELETON,i%skeletons,-56.f+16.f*(float)i,AW_HALLOWEEN_STAGE_AHEAD);
    return n;
}

/* ---- the camera director ---- */
int AW_HalloweenShot(float seconds,float beat,int locked,float *u) {
    float bar=4*beat,span=bar*AW_HALLOWEEN_SHOT_BARS,t;long n;
    if(locked || !(beat>0) || seconds<0){*u=0;return AW_HW_SHOT_WIDE;}
    n=(long)(seconds/span);
    t=(seconds-(float)n*span)/span;
    if(t<0)t=0;
    if(t>1)t=1;
    *u=t*t*(3-2*t);                         /* eased: slow in, slow out, never a jump inside a shot */
    return (int)(n%AW_HW_SHOTS);
}
/* The eye DIST from SUBJECT, turned YAW degrees from straight in front (the cast faces back along FORWARD) and raised
 * ELEV degrees. */
static void around(const float subject[3],const float forward[3],float yaw,float elev,float dist,float eye[3]) {
    float a=(float)(yaw*M_PI/180),e=(float)(elev*M_PI/180),bx=-forward[0],by=-forward[1],ca=Q_CosRad(a),sa=Q_SinRad(a),
          ce=Q_CosRad(e),se=Q_SinRad(e);
    eye[0]=subject[0]+(bx*ca-by*sa)*ce*dist;
    eye[1]=subject[1]+(bx*sa+by*ca)*ce*dist;
    eye[2]=subject[2]+se*dist;
}
void AW_HalloweenShotPose(int shot,float u,const float forward[3],const float centre[3],float fit,
                          const float close[3],float close_fit,float eye[3],float look[3]) {
    int i;
    /* every shot looks at its subject from at least its fitting distance: the whole subject, head to feet, in frame */
    for(i=0;i<3;i++)look[i]=centre[i];
    switch(shot){
    case AW_HW_SHOT_DOLLY:                  /* a slow push in, from wider than the wide shot to its framing */
        around(centre,forward,0,AW_HALLOWEEN_FRAME_PITCH,fit*(1.3f-.3f*u),eye);break;
    case AW_HW_SHOT_TRACK:                  /* sliding along the line, a quarter turn across the front */
        around(centre,forward,-25+50*u,AW_HALLOWEEN_FRAME_PITCH,fit*1.1f,eye);break;
    case AW_HW_SHOT_CRANE:                  /* rising from low to high over the group */
        around(centre,forward,0,8+42*u,fit*1.15f,eye);break;
    case AW_HW_SHOT_ORBIT:                  /* around the centre, a third of a turn across the front */
        around(centre,forward,-60+120*u,AW_HALLOWEEN_FRAME_PITCH,fit*1.1f,eye);break;
    case AW_HW_SHOT_CLOSE:                  /* one dancer, head to feet, the camera drifting across her */
        for(i=0;i<3;i++)look[i]=close[i];
        around(close,forward,20-40*u,12,close_fit,eye);break;
    default:                                /* the wide shot: the whole cast, looking down at its middle */
        around(centre,forward,0,AW_HALLOWEEN_FRAME_PITCH,fit,eye);break;
    }
}
void AW_HalloweenFrameCast(const float centre[3],float half_width,float half_height,const float forward[3],
                           float fov_x,float fov_y,float eye[3]) {
    float tx,ty,d,dw,dh,p=(float)(AW_HALLOWEEN_FRAME_PITCH*M_PI/180),c,s;int i;
    if(!(fov_x>1 && fov_x<179))fov_x=90;
    if(!(fov_y>1 && fov_y<179))fov_y=73.74f;
    tx=Q_TanRad((float)(fov_x*M_PI/360));ty=Q_TanRad((float)(fov_y*M_PI/360));
    dw=half_width*AW_HALLOWEEN_FRAME_MARGIN/tx;
    /* the height seen from above: the box's height foreshortened by the pitch, its depth added */
    c=Q_CosRad(p);s=Q_SinRad(p);
    dh=(half_height*c+8*s)*AW_HALLOWEEN_FRAME_MARGIN/ty;
    d=dw>dh?dw:dh;
    for(i=0;i<3;i++)eye[i]=centre[i]-forward[i]*d*c;
    eye[2]=centre[2]+d*s;
}
void AW_HalloweenEdgeRays(const float eye[3],const float look[3],float fov_x,float fov_y,float dist,
                          float out[AW_HW_EDGE_RAYS][3]) {
    static const float sx[AW_HW_EDGE_RAYS]={-1,1,-1,0,1},sy[AW_HW_EDGE_RAYS]={0,0,1,1,1};
    float f[3],r[3],u[3],n,tx,ty,d[3];int i,k;
    if(!(fov_x>1 && fov_x<179))fov_x=90;
    if(!(fov_y>1 && fov_y<179))fov_y=73.74f;
    tx=Q_TanRad((float)(fov_x*M_PI/360));ty=Q_TanRad((float)(fov_y*M_PI/360));
    for(i=0;i<3;i++)f[i]=look[i]-eye[i];
    n=(float)sqrt(f[0]*f[0]+f[1]*f[1]+f[2]*f[2]);
    if(n<.01f){f[0]=1;f[1]=f[2]=0;}else for(i=0;i<3;i++)f[i]/=n;
    /* right = forward x up (level), up = right x forward */
    r[0]=f[1];r[1]=-f[0];r[2]=0;
    n=(float)sqrt(r[0]*r[0]+r[1]*r[1]);
    if(n<.01f){r[0]=1;r[1]=0;}else{r[0]/=n;r[1]/=n;}
    u[0]=r[1]*f[2]-r[2]*f[1];u[1]=r[2]*f[0]-r[0]*f[2];u[2]=r[0]*f[1]-r[1]*f[0];
    for(k=0;k<AW_HW_EDGE_RAYS;k++){
        for(i=0;i<3;i++)d[i]=f[i]+sx[k]*tx*r[i]+sy[k]*ty*u[i];
        n=(float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
        for(i=0;i<3;i++)out[k][i]=eye[i]+d[i]/n*dist;
    }
}
void AW_HalloweenAim(const float eye[3],const float look[3],float angles[3]) {
    float d[3],flat;int i;
    for(i=0;i<3;i++)d[i]=look[i]-eye[i];
    flat=(float)sqrt(d[0]*d[0]+d[1]*d[1]);
    angles[1]=flat>.01f?(float)(Q_atan2(d[1],d[0])*180/M_PI):0;
    angles[0]=(float)(Q_atan2(-d[2],flat>.01f?flat:.01f)*180/M_PI);
    angles[2]=0;
}

/* ---- the benchmark's figures ---- */
void AW_HalloweenBenchFigures(const float *times,int n,aw_hw_bench_t *out) {
    double sum=0,worst=0,slow=0;int i,j,k,count;
    memset(out,0,sizeof(*out));
    if(n<=0)return;
    for(i=0;i<n;i++){sum+=times[i];if(times[i]>worst)worst=times[i];}
    out->frames=n;out->seconds=(float)sum;
    out->average=sum>0?(float)(n/sum):0;
    out->minimum=worst>0?(float)(1/worst):0;
    /* the slowest 1 % (at least one frame, at most 64): picked one by one, the caller's array left as it is */
    count=n/100;if(count<1)count=1;if(count>64)count=64;
    {int taken[64];
     for(k=0;k<count;k++){
        int at=-1;
        for(j=0;j<n;j++){
            int used=0,m;
            for(m=0;m<k;m++)if(taken[m]==j)used=1;
            if(!used && (at<0 || times[j]>times[at]))at=j;
        }
        taken[k]=at;slow+=times[at];
     }}
    out->low1=slow>0?(float)(count/slow):0;
}
