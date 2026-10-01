/* SPDX-License-Identifier: GPL-2.0-or-later
 * One resident terrain BSP with explicit local origins. Source coordinates
 * survive crossings; network/render coordinates stay bounded inside a region.
 */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_world.h"
#include <stdint.h>
typedef struct {float origin[3],core[4],cover[4];} terrain_region_t;
static terrain_region_t *regions;
static terrain_region_t towns[2];
static int count,attempted;
static const char *town_names[2]={"seyda","balmora"};
static uint32_t word(const byte *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float number(const byte *p){uint32_t n=word(p);float f;memcpy(&f,&n,4);return f;}
static int load_directory(void){
    FILE *f=NULL;byte header[8],row[52];int size,n,i,k;char expected[8];terrain_region_t *r;
    if(attempted)return count>0;
    attempted=1;size=COM_FOpenFile("world/regions.awr",&f);
    if(!f)return 0;
    if(size<64 || fread(header,1,8,f)!=8 || memcmp(header,"AWR2",4))goto bad;
    n=(int)word(header+4);if(n<1 || n>8192 || size!=64+n*52)goto bad;
    for(i=0;i<2;i++){
        if(fread(row,1,28,f)!=28)goto bad;
        for(k=0;k<3;k++)towns[i].origin[k]=number(row+k*4);
        for(k=0;k<4;k++)towns[i].core[k]=number(row+12+k*4);
        for(k=0;k<3;k++)if(!isfinite(towns[i].origin[k]) || fabs(towns[i].origin[k])>1000000)goto bad;
        for(k=0;k<2;k++)if(!(towns[i].core[k]>=-4000 && towns[i].core[k+2]<=4000 && towns[i].core[k]<towns[i].core[k+2]))goto bad;
    }
    regions=(terrain_region_t *)malloc(n*sizeof(*regions));if(!regions)goto bad;
    for(i=0;i<n;i++){
        if(fread(row,1,52,f)!=52)goto bad;
        sprintf(expected,"vf%04ld",(long)i);if(memcmp(row,expected,7) || row[7])goto bad;
        r=&regions[i];
        for(k=0;k<3;k++)r->origin[k]=number(row+8+k*4);
        for(k=0;k<4;k++){r->core[k]=number(row+20+k*4);r->cover[k]=number(row+36+k*4);}
        for(k=0;k<3;k++)if(!isfinite(r->origin[k]) || fabs(r->origin[k])>1000000)goto bad;
        for(k=0;k<2;k++)if(!(r->core[k]<r->core[k+2] && r->cover[k]<=r->core[k]-896 &&
            r->cover[k+2]>=r->core[k+2]+896 && r->cover[k]>-4000 && r->cover[k+2]<4000))goto bad;
    }
    fclose(f);count=n;Con_Printf("Vvardenfell: %ld terrain regions; %ld directory bytes.\n",(long)n,(long)(n*sizeof(*regions)));return 1;
bad:
    fclose(f);free(regions);regions=NULL;count=0;
    Con_Printf("Invalid or unavailable Vvardenfell region directory.\n");return 0;
}
static terrain_region_t *source(const char *name){
    int i=AW_TerrainId(name);
    if(i<0 && strcmp(name,"seyda") && strcmp(name,"balmora"))return NULL;
    if(!load_directory())return NULL;
    if(i>=0)return i<count?&regions[i]:NULL;
    for(i=0;i<2;i++)if(!strcmp(name,town_names[i]))return &towns[i];
    return NULL;
}
static int inside(const float *point,const float *box,float margin){
    int k;for(k=0;k<2;k++)if(!(point[k]>=box[k]-margin && point[k]<box[k+2]+margin))return 0;
    return 1;
}
int AW_WorldToSource(const char *name,const float *local,float *world){
    terrain_region_t *r=source(name);int k;if(!r)return 0;
    for(k=0;k<3;k++)if(!isfinite(local[k]))return 0;
    for(k=0;k<3;k++)world[k]=(local[k]+r->origin[k])*4;
    return 1;
}
int AW_WorldContains(const char *name,const float *local){
    terrain_region_t *r=source(name);
    return r && inside(local,r->cover,-24);
}
int AW_WorldDestination(const char *name,const float *local,char *target,float *arrival){
    terrain_region_t *from,*to=NULL;float global[3],point[3];int i,k,id;char path[32];FILE *f=NULL;
    if(strcmp(name,"seyda") && strcmp(name,"balmora") && AW_TerrainId(name)<0)return 0;
    from=source(name);if(!from)return 0;
    for(k=0;k<3;k++){if(!isfinite(local[k]))return 0;global[k]=local[k]+from->origin[k];}
    for(i=0;i<2;i++){
        for(k=0;k<3;k++)point[k]=global[k]-towns[i].origin[k];
        if(inside(point,towns[i].core,!strcmp(name,town_names[i])?32:0)){
            if(!strcmp(name,town_names[i]))return 0;
            to=&towns[i];strcpy(target,town_names[i]);break;
        }
    }
    id=AW_TerrainId(name);
    if(!to && id>=0 && inside(local,from->core,64))return 0;
    if(!to)for(i=0;i<count;i++){
        for(k=0;k<3;k++)point[k]=global[k]-regions[i].origin[k];
        if(inside(point,regions[i].core,0)){to=&regions[i];sprintf(target,"vf%04ld",(long)i);break;}
    }
    if(!to || !strcmp(name,target))return 0;
    for(k=0;k<3;k++){arrival[k]=global[k]-to->origin[k];if(!(fabs(arrival[k])<4000))return 0;}
    sprintf(path,"maps/%s.bsp",target);
    if(COM_FOpenFile(path,&f)<124 || !f){if(f)fclose(f);return 0;}
    fclose(f);return 1;
}
