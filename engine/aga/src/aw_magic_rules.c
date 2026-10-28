/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_magic_rules.c: the magic effect table (gfx/magic.awm, tools/prepare_magic.py) and the pure rules the engine
 * glue (aw_magic.c) follows: emission over time, directions, fade frames, the area scale. Host-tested
 * (tests/aga_magic_rules_test.c); no engine headers, no library float parsing. */
#include <math.h>
#include <string.h>
#include <stdio.h>
#include "aw_magic.h"

#define TOKENS 48
#define TOKEN 48
#define PH_FIELDS 8   /* ph NAME PHASE LENGTH SPRITE SIZE RADIUS SOUND */
#define FX_FIELDS 7   /* fx NAME MGEF SCHOOL R G B, then the record's FLAGS when the line has one more */

static const char *const phase_names[AW_MAGIC_PHASES]={"hand","cast","bolt","hit","area","fail","bubble"};
static const char *const school_names[AW_MAGIC_SCHOOLS]={"alteration","conjuration","destruction","illusion",
    "mysticism","restoration"};

static int same(const char *a,const char *b) {
    while(*a && *b){
        int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;
        if(x!=y)return 0;
        a++;b++;
    }
    return !*a && !*b;
}
static void reason(char *why,int size,const char *text) {
    if(why && size>0){strncpy(why,text,size-1);why[size-1]=0;}
}
int AW_MagicNumber(const char *text,float *out) {
    double value=0,scale=1;int sign=1,digits=0;
    if(!text || !*text)return 0;
    if(*text=='-' || *text=='+'){if(*text=='-')sign=-1;text++;}
    while(*text>='0' && *text<='9'){value=value*10+(*text-'0');text++;digits++;if(digits>9)return 0;}
    if(*text=='.'){
        text++;
        while(*text>='0' && *text<='9'){scale/=10;value+=(*text-'0')*scale;text++;digits++;if(scale<1e-7)return 0;}
    }
    if(*text || !digits)return 0;
    *out=(float)(sign*value);return 1;
}
static int split(const char *line,char tokens[TOKENS][TOKEN]) {
    int n=0,k;
    while(*line){
        while(*line==' ' || *line=='\t')line++;
        if(!*line || *line=='\r' || *line=='\n')break;
        if(n==TOKENS)return -1;
        for(k=0;*line && *line!=' ' && *line!='\t' && *line!='\r' && *line!='\n';line++){
            if(k==TOKEN-1)return -1;
            tokens[n][k++]=*line;
        }
        tokens[n][k]=0;n++;
    }
    return n;
}
int AW_MagicPhase(const char *word) {
    int i;for(i=0;i<AW_MAGIC_PHASES;i++)if(same(word,phase_names[i]))return i;
    return -1;
}
int AW_MagicSchool(const char *word) {
    int i;for(i=0;i<AW_MAGIC_SCHOOLS;i++)if(same(word,school_names[i]))return i;
    return -1;
}
const char *AW_MagicPhaseName(int phase) {return phase>=0 && phase<AW_MAGIC_PHASES?phase_names[phase]:"?";}
const char *AW_MagicSchoolName(int school) {return school>=0 && school<AW_MAGIC_SCHOOLS?school_names[school]:"?";}
int AW_MagicFind(const aw_magic_table_t *t,const char *name) {
    int i;if(!t || !name)return -1;
    for(i=0;i<t->effects;i++)if(same(t->fx[i].name,name))return i;
    return -1;
}
int AW_MagicHeader(aw_magic_table_t *t,const char *line) {
    char tok[TOKENS][TOKEN];float speed;
    if(!t || split(line,tok)!=2 || strcmp(tok[0],AW_MAGIC_MAGIC) || !AW_MagicNumber(tok[1],&speed) ||
       !(speed>0) || speed>100000)return 0;
    memset(t,0,sizeof(*t));t->bolt_speed=speed;return 1;
}
/* A path field: "-" for none, else a relative path of safe characters that fits. */
static int path(char *out,const char *token) {
    const char *p;
    if(!strcmp(token,"-")){out[0]=0;return 1;}
    if((int)strlen(token)>=AW_MAGIC_PATH || token[0]=='/' || strstr(token,".."))return 0;
    for(p=token;*p;p++)if(!((*p>='a' && *p<='z') || (*p>='0' && *p<='9') || *p=='_' || *p=='/' || *p=='.'))return 0;
    strcpy(out,token);return 1;
}
static int numbers(char tok[TOKENS][TOKEN],int from,int n,float *out) {
    int i;for(i=0;i<n;i++)if(!AW_MagicNumber(tok[from+i],&out[i]))return 0;
    return 1;
}
int AW_MagicLine(aw_magic_table_t *t,const char *line,char *why,int why_size) {
    char tok[TOKENS][TOKEN];int n,i,k,phase;float v[48];aw_magic_effect_t *fx;aw_magic_phase_t *ph;aw_magic_emitter_t *e;
    if(!t){reason(why,why_size,"no table");return 0;}
    n=split(line,tok);
    if(n<0){reason(why,why_size,"line too long");return 0;}
    if(n==0 || tok[0][0]=='#')return 1;
    if(!strcmp(tok[0],"fx")){
        if(n!=FX_FIELDS && n!=FX_FIELDS+1){reason(why,why_size,"fx: 7 or 8 fields");return 0;}
        if(t->effects>=AW_MAGIC_EFFECTS){reason(why,why_size,"too many effects");return 0;}
        if((int)strlen(tok[1])>=AW_MAGIC_NAME || AW_MagicFind(t,tok[1])>=0){reason(why,why_size,"fx: bad or repeated name");return 0;}
        for(i=0;tok[1][i];i++)if(!(tok[1][i]>='a' && tok[1][i]<='z')){reason(why,why_size,"fx: name a-z only");return 0;}
        if(!numbers(tok,2,1,v) || !numbers(tok,4,3,v+1) || v[0]<0 || v[0]>1000){reason(why,why_size,"fx: bad numbers");return 0;}
        if((k=AW_MagicSchool(tok[3]))<0){reason(why,why_size,"fx: unknown school");return 0;}
        for(i=1;i<4;i++)if(v[i]<0 || v[i]>255){reason(why,why_size,"fx: colour out of range");return 0;}
        fx=&t->fx[t->effects];memset(fx,0,sizeof(*fx));
        strcpy(fx->name,tok[1]);fx->mgef=(int)v[0];fx->school=k;
        for(i=0;i<3;i++)fx->rgb[i]=(unsigned char)v[i+1];
        /* FLAGS: the magic effect record's flags (AW_MAGIC_CONTINUOUS_VFX); a 7-field line has none */
        if(n==FX_FIELDS+1){
            if(!numbers(tok,7,1,v+4) || v[4]<0 || v[4]>65535){reason(why,why_size,"fx: bad flags");return 0;}
            fx->flags=(int)v[4];
        }
        t->effects++;return 1;
    }
    if(!strcmp(tok[0],"ph")){
        if(n!=PH_FIELDS){reason(why,why_size,"ph: 8 fields");return 0;}
        if((i=AW_MagicFind(t,tok[1]))<0 || (phase=AW_MagicPhase(tok[2]))<0){reason(why,why_size,"ph: unknown effect or phase");return 0;}
        ph=&t->fx[i].phase[phase];
        if(ph->present){reason(why,why_size,"ph: repeated phase");return 0;}
        if(!numbers(tok,3,1,v) || !numbers(tok,5,2,v+1) || !(v[0]>0) || v[0]>10 || v[1]<0 || v[1]>512 || v[2]<0 || v[2]>2048){
            reason(why,why_size,"ph: bad numbers");return 0;
        }
        if(!path(ph->sprite,tok[4]) || !path(ph->sound,tok[7])){reason(why,why_size,"ph: bad path");return 0;}
        ph->length=v[0];ph->sprite_size=v[1];ph->radius=v[2];ph->present=1;return 1;
    }
    if(!strcmp(tok[0],"em")){
        if(n!=19+3*AW_MAGIC_RAMP){reason(why,why_size,"em: wrong field count");return 0;}
        if((i=AW_MagicFind(t,tok[1]))<0 || (phase=AW_MagicPhase(tok[2]))<0 || !t->fx[i].phase[phase].present){
            reason(why,why_size,"em: unknown effect or phase");return 0;
        }
        ph=&t->fx[i].phase[phase];
        if(ph->emitters>=AW_MAGIC_EMITTERS){reason(why,why_size,"em: too many emitters");return 0;}
        if(!numbers(tok,3,16+3*AW_MAGIC_RAMP,v)){reason(why,why_size,"em: bad numbers");return 0;}
        if(v[0]<0 || v[0]>256 || v[1]<0 || v[1]>256 || !(v[2]>0) || v[2]>10 || v[3]<0 || v[3]>10 || v[4]<0 || v[4]>2000 ||
           v[5]<0 || v[5]>2000 || v[9]<0 || v[10]<0 || v[10]>1 || v[11]<0 || v[12]<v[11] || v[12]>10){
            reason(why,why_size,"em: numbers out of range");return 0;
        }
        for(k=0;k<3;k++)if(v[6+k]<-1.01f || v[6+k]>1.01f || v[13+k]<0 || v[13+k]>512){reason(why,why_size,"em: axis or jitter out of range");return 0;}
        for(k=0;k<3*AW_MAGIC_RAMP;k++)if(v[16+k]<0 || v[16+k]>255){reason(why,why_size,"em: colour out of range");return 0;}
        e=&ph->em[ph->emitters];memset(e,0,sizeof(*e));
        e->count=(int)v[0];e->size=v[1];e->life=v[2];e->life_rand=v[3];e->speed=v[4];e->speed_rand=v[5];
        for(k=0;k<3;k++){e->axis[k]=v[6+k];e->jitter[k]=v[13+k];}
        e->spread=v[9];e->gravity=v[10];e->start=v[11];e->stop=v[12];
        for(k=0;k<3*AW_MAGIC_RAMP;k++)e->ramp[k/3][k%3]=(unsigned char)v[16+k];
        ph->emitters++;return 1;
    }
    reason(why,why_size,"unknown line");return 0;
}
int AW_MagicCheck(const aw_magic_table_t *t,char *why,int why_size) {
    int i;
    if(!t || t->effects<1){reason(why,why_size,"no effects");return 0;}
    for(i=0;i<t->effects;i++)if(!t->fx[i].phase[AW_MAGIC_CAST].present){reason(why,why_size,"an effect without its cast");return 0;}
    return 1;
}
static float clamp01(float x) {return x<0?0:x>1?1:x;}
static int emitted(const aw_magic_emitter_t *e,float at,float scale) {
    float span=e->stop-e->start,share;
    if(at<e->start)return 0;
    share=span>0.001f?clamp01((at-e->start)/span):1;
    return (int)(e->count*scale*share+.0001f);
}
int AW_MagicEmitBetween(const aw_magic_emitter_t *e,float from,float to,float scale) {
    int n;
    if(!e || !(scale>0) || !(to>from))return 0;
    n=emitted(e,to,scale)-emitted(e,from,scale);
    return n>0?n:0;
}
float AW_MagicTrailRate(const aw_magic_emitter_t *e) {
    float span;
    if(!e || e->count<=0)return 0;
    span=e->stop-e->start;
    if(span<e->life)span=e->life;
    if(span<.1f)span=.1f;
    return e->count/span;
}
int AW_MagicDirection(const aw_magic_emitter_t *e,const float r[3],float out[3]) {
    float d[3],len;int k;
    if(!e || !r)return 0;
    for(k=0;k<3;k++)d[k]=e->spread>=50?r[k]:e->axis[k]+r[k]*e->spread;
    len=(float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
    if(!(len>1e-4f))return 0;
    for(k=0;k<3;k++)out[k]=d[k]/len;
    return 1;
}
int AW_MagicFadeFrame(float age,float length) {
    int f;
    if(!(length>0) || !(age>0))return 0;
    f=(int)(clamp01(age/length)*AW_MAGIC_FADE_FRAMES);
    return f>=AW_MAGIC_FADE_FRAMES?AW_MAGIC_FADE_FRAMES-1:f;
}
float AW_MagicAreaScale(float feet) {return feet*2>1?feet*2:1;}
float AW_MagicGrow(float size,float grow,float age,float length) {
    if(!(length>0))return size;
    return size*(1+(grow-1)*clamp01(age/length));
}
