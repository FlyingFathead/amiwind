/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
byte *host_basepal;
#include "aw_sky.h"
#include "aw_state.h"
#include <assert.h>
#include <ctype.h>
/* Light-space night symbols owned by r_light.c / d_sprite.c / d_surf.c. */
int r_daylight=256;unsigned char *r_warm_colormap;const unsigned char *d_nightshade;
void Cvar_Set(char *name,char *value){(void)name;(void)value;}
viddef_t vid;void D_FlushCaches(void){}
extern int r_backgroundsky;
extern byte *r_skysource;
extern float skytime;
void R_SetSkyFrame(void);
double realtime;
int AW_DayGalleryClock(int actual_ms){return actual_ms;}
aw_state_t aw_state;
static int present,size,opens,clock_ms=123400;
char com_token[1024];
char *COM_Parse(char *s){int n=0;if(!s)return NULL;while(*s && isspace((unsigned char)*s))s++;if(!*s)return NULL;if(*s=='{'||*s=='}'){com_token[0]=*s++;com_token[1]=0;return s;}if(*s=='"'){s++;while(*s && *s!='"' && n<1023)com_token[n++]=*s++;if(*s=='"')s++;}else while(*s && !isspace((unsigned char)*s) && n<1023)com_token[n++]=*s++;com_token[n]=0;return s;}
void Con_Printf(char *fmt,...){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Cvar_SetValue(char *name,float value){assert(0);}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
int Cmd_Argc(void){return 1;}char *Cmd_Argv(int n){return "";}
int COM_FOpenFile(char *path,FILE **file){int i;if(!strcmp(path,AW_NIGHT_SKY_PATH)){*file=NULL;return -1;}assert(!strcmp(path,AW_SHARED_SKY_PATH));opens++;*file=NULL;if(!present)return -1;*file=tmpfile();assert(*file);for(i=0;i<size;i++)fputc((i%256)<128?0:200,*file);rewind(*file);return size;}
int AW_ClockEnsure(void){return 1;}
int32_t AW_StateGet(const aw_state_t *s,int kind,const char *id){return strstr(id,":ms")?clock_ms:0;}
int GreatestCommonDivisor(int a,int b){int t;while(b){t=a%b;a=b;b=t;}return a;}
int main(void){
 model_t m;texture_t *legacy;byte *source;int old_opens;float phase;
 R_InitDayNight();
 memset(&m,0,sizeof m);m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\" \"_aw_sky_asset\" \"gfx/aw_shared_sky.lmp\"}";
 R_SetSkyBackground(&m);assert(!r_backgroundsky); /* No fabricated fallback art. */
 present=1;size=12;R_SetSkyBackground(&m);assert(!r_backgroundsky);
 size=AW_SHARED_SKY_BYTES;R_SetSkyBackground(&m);assert(r_backgroundsky && r_skysource);source=r_skysource;old_opens=opens;
 R_SetSkyFrame();phase=skytime;assert(phase>0);
 m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"interior\"}";R_SetSkyBackground(&m);assert(!r_backgroundsky && r_skysource==source);
 legacy=calloc(1,sizeof(*legacy)+AW_SHARED_SKY_BYTES);assert(legacy);legacy->width=256;legacy->height=128;legacy->offsets[0]=sizeof(*legacy);memset((byte *)legacy+legacy->offsets[0],77,AW_SHARED_SKY_BYTES);R_InitSky(legacy);free(legacy);assert(source[128]==200); /* Map texture cannot overwrite shared resource. */
 m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\"}";present=0;R_SetSkyBackground(&m);assert(r_backgroundsky && opens==old_opens && r_skysource==source);R_SetSkyFrame();assert(skytime==phase);clock_ms+=1000;R_SetSkyFrame();assert(fabs(skytime-phase-1.0f/300)<.000001f);
 m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"unknown\"}";R_SetSkyBackground(&m);assert(!r_backgroundsky);
 m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\" \"_aw_sky_asset\" \"../other\"}";R_SetSkyBackground(&m);assert(!r_backgroundsky);
 m.entities="{\"classname\" \"worldspawn\"}";R_SetSkyBackground(&m);assert(!r_backgroundsky);R_SetSkyBackground(NULL);assert(!r_backgroundsky);
 {
  char huge[1200];memset(huge,'a',sizeof huge);memcpy(huge,"{\"classname\" \"worldspawn\" \"",27);huge[sizeof huge-1]=0;m.entities=huge;R_SetSkyBackground(&m);assert(!r_backgroundsky);
  m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior";R_SetSkyBackground(&m);assert(!r_backgroundsky);
 }
 return 0;
}
