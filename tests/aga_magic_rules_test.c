/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_magic_rules.c alone: the magic effect table (gfx/magic.awm) and the rules aw_magic.c follows.
 * argv[1] (optional): a table written by tools/prepare_magic.py table_text, read line by line as the engine does. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_magic.h"

static int near(float a,float b) {return fabsf(a-b)<.001f;}
static const char *const ramp=" 255 200 100 250 180 90 240 160 80 230 140 70 220 120 60 210 100 50 200 80 40 190 60 30";

static int line(aw_magic_table_t *t,const char *text) {
    char why[64];why[0]=0;
    return AW_MagicLine(t,text,why,sizeof(why));
}
static void read_file(const char *path) {
    static aw_magic_table_t t;FILE *f=fopen(path,"r");char text[600],why[64];int first=1;
    assert(f);
    while(fgets(text,sizeof(text),f)){
        text[strcspn(text,"\r\n")]=0;
        if(first){assert(AW_MagicHeader(&t,text));first=0;continue;}
        if(!AW_MagicLine(&t,text,why,sizeof(why))){fprintf(stderr,"refused: %s (%s)\n",text,why);assert(0);}
    }
    fclose(f);
    assert(AW_MagicCheck(&t,why,sizeof(why)));
    assert(AW_MagicFind(&t,"fire")==0 && t.fx[0].phase[AW_MAGIC_BOLT].present && t.fx[0].phase[AW_MAGIC_CAST].emitters==2);
}

int main(int argc,char **argv) {
    static aw_magic_table_t t;aw_magic_emitter_t e;char text[600],why[64];float x,d[3];
    float up[3]={0,0,1},side[3]={1,0,0},zero[3]={0,0,0};
    /* numbers without the C library's float parsing */
    assert(AW_MagicNumber("12.5",&x) && near(x,12.5f) && AW_MagicNumber("-0.25",&x) && near(x,-.25f));
    assert(AW_MagicNumber("3",&x) && near(x,3) && !AW_MagicNumber("",&x) && !AW_MagicNumber("1e5",&x));
    assert(!AW_MagicNumber("-",&x) && !AW_MagicNumber("1.2.3",&x) && !AW_MagicNumber("12345678901",&x));
    /* header */
    assert(!AW_MagicHeader(&t,"AWMG2 250") && !AW_MagicHeader(&t,"AWMG1") && !AW_MagicHeader(&t,"AWMG1 0"));
    assert(AW_MagicHeader(&t,"AWMG1 250") && near(t.bolt_speed,250) && t.effects==0);
    /* effects, phases, emitters */
    assert(line(&t,"# comment") && line(&t,""));
    assert(line(&t,"fx fire 14 destruction 253 136 66"));
    assert(!line(&t,"fx fire 14 destruction 253 136 66"));                /* repeated */
    assert(!line(&t,"fx Ice 16 destruction 1 2 3"));                      /* a-z only */
    assert(!line(&t,"fx frost 16 sorcery 1 2 3"));                        /* no such school */
    assert(!line(&t,"fx frost 16 destruction 1 2 300"));                  /* colour */
    assert(line(&t,"fx frost 16 destruction 146 162 239"));
    assert(t.effects==2 && t.fx[0].school==AW_MAGIC_DESTRUCTION && t.fx[0].rgb[1]==136 && t.fx[1].mgef==16);
    /* FLAGS, the 8th field: the record's ContinuousVfx keeps the hit shell for the duration */
    assert(!line(&t,"fx shield 3 alteration 128 0 128 x"));
    assert(line(&t,"fx shield 3 alteration 128 0 128 32") && t.effects==3 &&
           (t.fx[2].flags&AW_MAGIC_CONTINUOUS_VFX) && !t.fx[0].flags);
    assert(line(&t,"ph shield cast 1 - 6 0 -") && line(&t,"ph shield bubble 1.5 progs/awmx_02.spr 39.6 0 -"));
    assert(t.fx[2].phase[AW_MAGIC_BUBBLE].present && near(t.fx[2].phase[AW_MAGIC_BUBBLE].sprite_size,39.6f));
    assert(line(&t,"ph fire cast 1.033 progs/awmx_00.spr 9.4 0 aw/magic/destruction_cast.wav"));
    assert(!line(&t,"ph fire cast 1 - 4 0 -"));                           /* repeated phase */
    assert(!line(&t,"ph fire glow 1 - 4 0 -"));                           /* no such phase */
    assert(!line(&t,"ph fire bolt 1 ../x.spr 4 0 -"));                    /* unsafe path */
    assert(!line(&t,"ph fire bolt 0 - 4 0 -"));                           /* no length */
    assert(line(&t,"ph fire bolt 1 progs/awmx_01.spr 6 0 -") && line(&t,"ph fire area 1 - 16 10.5 -"));
    assert(t.fx[0].phase[AW_MAGIC_CAST].present && near(t.fx[0].phase[AW_MAGIC_CAST].length,1.033f) &&
           !strcmp(t.fx[0].phase[AW_MAGIC_CAST].sprite,"progs/awmx_00.spr") && !t.fx[0].phase[AW_MAGIC_AREA].sprite[0] &&
           near(t.fx[0].phase[AW_MAGIC_AREA].radius,10.5f) && !t.fx[0].phase[AW_MAGIC_BOLT].sound[0]);
    /* the failed cast: a sound-only phase */
    assert(line(&t,"ph fire fail 1 - 0 0 aw/magic/spell_failure_destruc.wav"));
    assert(t.fx[0].phase[AW_MAGIC_FAIL].present && !t.fx[0].phase[AW_MAGIC_FAIL].sprite[0] &&
           !strcmp(t.fx[0].phase[AW_MAGIC_FAIL].sound,"aw/magic/spell_failure_destruc.wav") &&
           !strcmp(AW_MagicPhaseName(AW_MAGIC_FAIL),"fail"));
    sprintf(text,"em fire cast 20 9.4 0.536 0 3.75 1 0 0 1 0.5 0 0 0.5 1 1 2%s",ramp);
    assert(line(&t,text));
    sprintf(text,"em fire cast 20 9.4 0.536 0 3.75 1 0 0 1 0.5 0 0 0.5 1 1 2%s 7",ramp);
    assert(!line(&t,text));                                                /* field count */
    sprintf(text,"em fire hit 20 9.4 0.536 0 3.75 1 0 0 1 0.5 0 0 0.5 1 1 2%s",ramp);
    assert(!line(&t,text));                                                /* phase not declared */
    sprintf(text,"em fire cast 20 9.4 0.536 0 3.75 1 0 0 1 0.5 0 0.6 0.5 1 1 2%s",ramp);
    assert(!line(&t,text));                                                /* stop before start */
    {
        aw_magic_emitter_t *m=&t.fx[0].phase[AW_MAGIC_CAST].em[0];
        assert(t.fx[0].phase[AW_MAGIC_CAST].emitters==1 && m->count==20 && near(m->speed,3.75f) && near(m->stop,.5f) &&
               near(m->axis[2],1) && near(m->jitter[2],2) && m->ramp[0][0]==255 && m->ramp[7][2]==30);
    }
    assert(!AW_MagicCheck(&t,why,sizeof(why)));                           /* frost has no cast */
    assert(line(&t,"ph frost cast 1 - 6 0 -") && AW_MagicCheck(&t,why,sizeof(why)));
    assert(AW_MagicFind(&t,"FROST")==1 && AW_MagicFind(&t,"shock")<0);
    assert(AW_MagicPhase("area")==AW_MAGIC_AREA && AW_MagicSchool("restoration")==AW_MAGIC_RESTORATION);
    /* emission over the phase: 20 particles over 0..0.5 s */
    memset(&e,0,sizeof(e));e.count=20;e.start=0;e.stop=.5f;e.life=.5f;
    assert(AW_MagicEmitBetween(&e,-1,0,1)==0 && AW_MagicEmitBetween(&e,-1,.25f,1)==10);
    assert(AW_MagicEmitBetween(&e,.25f,.5f,1)==10 && AW_MagicEmitBetween(&e,.5f,2,1)==0);
    {   /* frame by frame the total is the count */
        int n=0;float s;for(s=0;s<1;s+=.02f)n+=AW_MagicEmitBetween(&e,s>0?s:-1,s+.02f,1);
        assert(n==20);
    }
    e.stop=0;assert(AW_MagicEmitBetween(&e,-1,0,1)==20 && AW_MagicEmitBetween(&e,0,1,1)==0);  /* all at start */
    assert(AW_MagicEmitBetween(&e,-1,0,.5f)==10 && AW_MagicEmitBetween(&e,1,0,1)==0);
    e.stop=.5f;assert(near(AW_MagicTrailRate(&e),40));
    /* directions: the axis within its cone; every direction when wide */
    e.axis[0]=0;e.axis[1]=0;e.axis[2]=1;e.spread=0;
    assert(AW_MagicDirection(&e,side,d) && near(d[2],1));
    e.spread=1;assert(AW_MagicDirection(&e,side,d) && near(d[0],.7071f) && near(d[2],.7071f));
    e.spread=50;assert(AW_MagicDirection(&e,side,d) && near(d[0],1) && !AW_MagicDirection(&e,zero,d));
    e.spread=0;assert(AW_MagicDirection(&e,up,d) && near(d[2],1));
    /* fades, area, growth */
    assert(AW_MagicFadeFrame(0,1)==0 && AW_MagicFadeFrame(.3f,1)==1 && AW_MagicFadeFrame(.99f,1)==3 &&
           AW_MagicFadeFrame(5,1)==3 && AW_MagicFadeFrame(1,0)==0);
    assert(near(AW_MagicAreaScale(0),1) && near(AW_MagicAreaScale(10),20));
    assert(near(AW_MagicGrow(10,1.6f,0,1),10) && near(AW_MagicGrow(10,1.6f,1,1),16) && near(AW_MagicGrow(10,1.6f,9,1),16));
    if(argc>1)read_file(argv[1]);
    printf("magic rules ok\n");
    return 0;
}
