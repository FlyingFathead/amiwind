/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original-cell sections, finite authored connectors and hysteresis.
 * Residency never owns quest, actor or harvested-placement identity. */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_section.h"
static aw_section_directory_t directory;
static int loaded,valid;
static char ahead[40];
static int find(const aw_section_directory_t *d,const char *name)
{
    int i;for(i=0;i<d->count;i++)if(!strcmp(name,d->section[i].name))return i;
    return -1;
}
static int contains(const aw_section_record_t *s,const float *point)
{
    int k;for(k=0;k<3;k++)if(!isfinite(point[k]) || point[k]<s->low[k] || point[k]>s->high[k])return 0;
    return 1;
}
int AW_SectionRead(FILE *f,aw_section_directory_t *out)
{
    aw_section_directory_t d;char line[256],extra,a[16],b[16];int i,j,k;
    memset(&d,0,sizeof(d));
    if(!f || !out || !fgets(line,sizeof(line),f) ||
       Q_sscanf(line,"AWIS1 %d %d %c",&d.count,&d.portals,&extra)!=2 ||
       d.count<2 || d.count>AW_SECTION_MAX || d.portals<1 || d.portals>AW_SECTION_PORTALS)return 0;
    for(i=0;i<d.count;i++){
        aw_section_record_t *r=&d.section[i];
        if(!fgets(line,sizeof(line),f) || Q_sscanf(line,"%15s %f %f %f %f %f %f %c",r->name,
           &r->low[0],&r->low[1],&r->low[2],&r->high[0],&r->high[1],&r->high[2],&extra)!=7 ||
           !AW_MapInteriorSection(r->name))return 0;
        for(j=0;j<i;j++)if(!strcmp(r->name,d.section[j].name))return 0;
        for(k=0;k<3;k++)if(!(r->low[k]<r->high[k] && fabs(r->low[k])<32768 && fabs(r->high[k])<32768))return 0;
    }
    for(i=0;i<d.portals;i++){
        aw_section_portal_t *p=&d.portal[i];
        if(!fgets(line,sizeof(line),f) || Q_sscanf(line,"%15s %15s %d %f %f %f %f %f %f %f %f %c",a,b,
           &p->axis,&p->split,&p->margin,&p->low[0],&p->low[1],&p->low[2],
           &p->high[0],&p->high[1],&p->high[2],&extra)!=11)return 0;
        p->a=find(&d,a);p->b=find(&d,b);
        if(p->a<0 || p->b<0 || p->a==p->b || AW_MapLogicalId(a)!=AW_MapLogicalId(b) ||
           p->axis<0 || p->axis>2 || !(p->margin>0 && p->margin<=32) || !isfinite(p->split))return 0;
        for(j=0;j<i;j++)if((d.portal[j].a==p->a && d.portal[j].b==p->b) ||
                           (d.portal[j].a==p->b && d.portal[j].b==p->a))return 0;
        for(k=0;k<3;k++)if(!(p->low[k]<p->high[k] &&
           p->low[k]>=d.section[p->a].low[k] && p->low[k]>=d.section[p->b].low[k] &&
           p->high[k]<=d.section[p->a].high[k] && p->high[k]<=d.section[p->b].high[k]))return 0;
        if(!(p->split-p->margin>p->low[p->axis] && p->split+p->margin<p->high[p->axis]))return 0;
    }
    if(fgets(line,sizeof(line),f) || ferror(f))return 0;
    *out=d;return 1;
}
int AW_SectionChoose(const aw_section_directory_t *d,const char *name,const float *point)
{
    int current,i,k,next=-1,target;const aw_section_portal_t *p;
    if(!d || !name || !point || (current=find(d,name))<0)return -1;
    if(!contains(&d->section[current],point))return -1;
    for(i=0;i<d->portals;i++){
        p=&d->portal[i];target=-1;
        if(current==p->a && point[p->axis]>p->split+p->margin)target=p->b;
        if(current==p->b && point[p->axis]<p->split-p->margin)target=p->a;
        if(target<0)continue;
        for(k=0;k<3;k++)if(point[k]<p->low[k] || point[k]>p->high[k])break;
        if(k!=3 || !contains(&d->section[target],point))continue;
        if(next>=0 && next!=target)return -1;
        next=target;
    }
    return next;
}
static int read_directory(void)
{
    FILE *f=NULL;
    if(loaded)return valid;
    loaded=1;
    if(COM_FOpenFile("interior-sections.txt",&f)<0 || !f)return 0;
    valid=AW_SectionRead(f,&directory);fclose(f);
    if(!valid)Con_Printf("Invalid interior section directory; section travel disabled.\n");
    return valid;
}
int AW_SectionSelect(const char *name,const float *point)
{
    int i;if(!AW_MapInteriorSection(name))return 1;
    if(!read_directory() || (i=find(&directory,name))<0)return 0;
    return contains(&directory.section[i],point);
}
int AW_SectionContains(const char *name,const float *point){return AW_SectionSelect(name,point);}
int AW_SectionDestination(const char *name,const float *point,char *target)
{
    int i;if(!AW_MapInteriorSection(name) || !read_directory())return 0;
    i=AW_SectionChoose(&directory,name,point);if(i<0)return 0;
    strcpy(target,directory.section[i].name);return 1;
}
const char *AW_SectionAhead(const char *name,const float *point,const float *velocity,float seconds)
{
    vec3_t next;char namebuf[16];int k;
    if(!(seconds>0 && seconds<=5))return NULL;
    for(k=0;k<3;k++){if(!isfinite(velocity[k]) || !isfinite(point[k]))return NULL;next[k]=point[k]+velocity[k]*seconds;}
    if(!AW_SectionDestination(name,next,namebuf))return NULL;
    sprintf(ahead,"maps/%s.bsp",namebuf);return ahead;
}
unsigned AW_SectionStaticBytes(void){return sizeof(directory)+sizeof(loaded)+sizeof(valid)+sizeof(ahead);}
