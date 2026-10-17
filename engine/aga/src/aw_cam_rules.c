/* SPDX-License-Identifier: GPL-2.0-or-later
 * The camera marks file line (aw_cam.h, docs/CAMERA_MARKS.md):
 *
 *   NAME|PLACE|POSITION|VIEW|TIME|HEADLAMP|FOG|NOTE
 *
 * PLACE "global": POSITION is "X Y" or "X Y Z" in original Morrowind
 * coordinates and the shot travels as dbg tp X Y [Z] does; PLACE a map name:
 * POSITION is "X Y Z" in that map's local units, the camera placed exactly
 * there (noclip). VIEW "YAW PITCH"; TIME HHMM or "-"; HEADLAMP on/off/-; FOG
 * 100..4096 or "-"; NOTE free printable text without "|". Lines starting with
 * "#" and empty lines are comments. No engine dependencies: host-tested
 * (tests/aga_cam_test.c), the same rules as tools/camera_marks.py.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_format.h"
#include "aw_cam.h"

static int lower(int c){return c>='A' && c<='Z'?c-'A'+'a':c;}
int AW_CamValidName(const char *name) {
    int n=0;
    if(!name || !*name)return 0;
    for(;*name;name++,n++){
        char c=*name;
        if(n>=AW_CAM_NAME-1 || !((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9') ||
                                 c=='_' || c=='-' || c=='.'))return 0;
    }
    return 1;
}
int AW_CamSameName(const char *a,const char *b) {
    while(*a && *b && lower((unsigned char)*a)==lower((unsigned char)*b)){a++;b++;}
    return !*a && !*b;
}
static int valid_map(const char *map) {
    int n=0;
    if(!*map)return 0;
    for(;*map;map++,n++)if(n>=AW_CAM_MAP-1 || !((*map>='a' && *map<='z') || (*map>='0' && *map<='9') || *map=='_'))return 0;
    return 1;
}
/* One number of a space-separated list: digits, sign and point only. */
static int number(const char **text,double low,double high,float *out) {
    char token[24],*end;int n=0;double value;const char *p=*text;
    while(*p && *p!=' '){
        if(n>=(int)sizeof(token)-1 || !((*p>='0' && *p<='9') || *p=='-' || *p=='+' || *p=='.'))return 0;
        token[n++]=*p++;
    }
    token[n]=0;if(!n)return 0;
    value=Q_strtod(token,&end);
    if(end==token || *end || !(value>=low && value<=high))return 0;
    *out=(float)value;
    if(*p==' '){p++;if(!*p || *p==' ')return 0;}
    *text=p;return 1;
}
static int numbers(const char *text,float *out,int most,double bound) {
    int n=0;
    while(*text){if(n>=most || !number(&text,-bound,bound,&out[n]))return -1;n++;}
    return n;
}
static int split(char *line,char **field) {
    int i;char *p;
    field[0]=line;
    for(i=1;i<8;i++){p=strchr(field[i-1],'|');if(!p)return 0;*p=0;field[i]=p+1;}
    return !strchr(field[7],'|');
}
int AW_CamParse(const char *text,aw_cam_mark_t *m) {
    char line[AW_CAM_LINE],*field[8];const char *p;int n,i;float view[2],value;
    memset(m,0,sizeof(*m));
    n=(int)strlen(text);
    if(!n || text[0]=='#')return 0;
    if(n>=AW_CAM_LINE)return -1;
    for(p=text;*p;p++)if((unsigned char)*p<32 || (unsigned char)*p>126)return -1;
    strcpy(line,text);
    if(!split(line,field) || !AW_CamValidName(field[0]))return -1;
    strcpy(m->name,field[0]);
    if(!strcmp(field[1],"global")){
        m->global=1;
        n=numbers(field[2],m->point,3,AW_CAM_GLOBAL_BOUND);
        if(n<2)return -1;
        m->has_z=n==3;
    }else{
        if(!valid_map(field[1]))return -1;
        strcpy(m->map,field[1]);
        if(numbers(field[2],m->point,3,AW_CAM_LOCAL_BOUND)!=3)return -1;
        m->has_z=1;
    }
    if(numbers(field[3],view,2,360)!=2 || !(view[0]>=0 && view[0]<360) || !(view[1]>=-80 && view[1]<=80))return -1;
    m->yaw=view[0];m->pitch=view[1];
    if(!strcmp(field[4],"-"))m->time=-1;
    else{
        if(strlen(field[4])!=4)return -1;
        for(i=0;i<4;i++)if(field[4][i]<'0' || field[4][i]>'9')return -1;
        m->time=atoi(field[4]);
        if(m->time/100>23 || m->time%100>59)return -1;
    }
    if(!strcmp(field[5],"on"))m->headlamp=1;
    else if(!strcmp(field[5],"off"))m->headlamp=0;
    else if(!strcmp(field[5],"-"))m->headlamp=-1;
    else return -1;
    if(!strcmp(field[6],"-"))m->fog=-1;
    else{
        n=(int)strlen(field[6]);if(n<3 || n>4)return -1;
        for(i=0;i<n;i++)if(field[6][i]<'0' || field[6][i]>'9')return -1;
        if(numbers(field[6],&value,1,4096)!=1 || value<100)return -1;
        m->fog=(int)value;
    }
    if(strlen(field[7])>=AW_CAM_NOTE)return -1;
    strcpy(m->note,field[7]);
    return 1;
}
/* Two decimals, trailing zeros dropped ("-20088", "-64.7", "0"). */
static int put_number(char *out,int size,float value) {
    char text[32];int n;
    if(!(fabs(value)<AW_CAM_GLOBAL_BOUND+1))return 0;
    n=snprintf(text,sizeof(text),"%.2f",(double)value);
    if(n<1 || n>=(int)sizeof(text))return 0;
    while(n>1 && text[n-1]=='0')text[--n]=0;
    if(text[n-1]=='.')text[--n]=0;
    if(!strcmp(text,"-0"))strcpy(text,"0");
    if(n>=size)return 0;
    strcpy(out,text);return n;
}
int AW_CamFormat(const aw_cam_mark_t *m,char *out,int size) {
    char numbers_text[3][32],view[2][32],line[AW_CAM_LINE+8],time[16],fog[16];int i,count=m->global && !m->has_z?2:3,n;
    aw_cam_mark_t check;
    for(i=0;i<count;i++)if(!put_number(numbers_text[i],sizeof(numbers_text[i]),m->point[i]))return 0;
    if(!put_number(view[0],sizeof(view[0]),m->yaw) || !put_number(view[1],sizeof(view[1]),m->pitch))return 0;
    if(m->time<0)strcpy(time,"-");else snprintf(time,sizeof(time),"%04d",m->time);
    if(m->fog<0)strcpy(fog,"-");else snprintf(fog,sizeof(fog),"%d",m->fog);
    n=snprintf(line,sizeof(line),"%s|%s|%s %s%s%s|%s %s|%s|%s|%s|%s",m->name,m->global?"global":m->map,
               numbers_text[0],numbers_text[1],count==3?" ":"",count==3?numbers_text[2]:"",view[0],view[1],time,
               m->headlamp<0?"-":m->headlamp?"on":"off",fog,m->note);
    if(n<1 || n>=AW_CAM_LINE || n>=size || AW_CamParse(line,&check)!=1)return 0;
    strcpy(out,line);return n;
}
