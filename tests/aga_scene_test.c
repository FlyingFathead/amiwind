/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static char queued[64];static eval_t goal;static int clear_buttons,events;
int COM_FOpenFile(char *name,FILE **f){
 const char *s="prison seyda 0 40 30 0 0 77 90\nprison evil;quit 0 40 30 0 0 77 90\n";
 *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
}
void Con_Printf(char *fmt,...){}
void Cbuf_AddText(char *s){strcpy(queued,s);}
void IN_AWClearButtons(void){clear_buttons++;}
void AW_MusicSceneEvent(const char *s){events++;}
double Sys_FloatTime(void){return 1;}
int Hunk_LowMark(void){return 1000;}
int Hunk_HighMark(void){return 0;}
eval_t *GetEdictFieldValue(edict_t *p,char *name){return &goal;}
qboolean AW_PlacePlayer(edict_t *p,vec3_t v){return false;}
void SV_LinkEdict(edict_t *p,qboolean touch){}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int type,edict_t *p){
 trace_t t;memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
 if(type==MOVE_NOMONSTERS)return t;
 if(a[2]>80){t.startsolid=t.allsolid=true;t.fraction=0;return t;}
 if(b[2]<50 && a[2]>=50){t.fraction=(a[2]-50)/(a[2]-b[2]);t.endpos[2]=50;t.plane.normal[2]=1;}
 return t;
}
int main(void){
 edict_t p;client_t client;vec3_t arrival={0,0,77};memset(&p,0,sizeof(p));memset(&client,0,sizeof(client));
 sv.active=true;svs.maxclients=1;svs.clients=&client;client.edict=&p;strcpy(sv.name,"prison");
 cls.state=ca_connected;p.v.movetype=MOVETYPE_WALK;p.v.health=100;p.v.view_ofs[2]=30;goal._float=1;cl.viewangles[1]=90;
 assert(AW_Interior());assert(AW_SceneUse());assert(!strcmp(queued,"map seyda\n"));assert(clear_buttons==1);
 assert(AW_SceneUse());assert(clear_buttons==1); /* held use cannot queue twice */
 strcpy(sv.name,"seyda");p.v.health=0;goal._float=0;AW_SceneSpawn(&p);
 assert(p.v.health==100 && goal._float==1 && events==2);assert(p.v.origin[2]>50 && p.v.origin[2]<51);
 assert(p.v.angles[1]==90 && p.v.fixangle);assert(!AW_Interior());
 assert(AW_InteriorPlace(&p,arrival));assert(p.v.origin[2]>50 && p.v.origin[2]<51);
 p.v.movetype=MOVETYPE_NOCLIP;assert(!AW_SceneUse());
 return 0;
}
