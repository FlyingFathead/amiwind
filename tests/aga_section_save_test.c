/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic actual write/decode/spawn regression; no original game data. */
#include <assert.h>
#include <stdarg.h>
#include "aw_save.c"
server_t sv;server_static_t svs;client_state_t cl;
double realtime;char com_gamedir[MAX_OSPATH];int pr_edict_size;
char *pr_strings;vec3_t vec3_origin;
static char strings_a[128]="\0progs/v_nord.mdl\0progs/future_weapon.mdl\0aw_npc";
static char strings_b[128]="\0unrelated\0progs/v_nord.mdl";
static eval_t field_values[5];static int missing=-1,warnings;
static const char *field_names[]={"aw_hand_goal","aw_hand_state","aw_torch","aw_hand_started","aw_attack_latched"};
static edict_t npc;static eval_t npc_ref,npc_hello;
static edict_t player;static client_t client;
edict_t *EDICT_NUM(int n){assert(n==1 || n==2);return n==1?&player:&npc;}
aw_story_t aw_story;
eval_t *GetEdictFieldValue(edict_t *p,char *name){int i;if(p==&npc){if(!strcmp(name,"aw_ref"))return &npc_ref;if(!strcmp(name,"aw_hello_count"))return &npc_hello;return NULL;}assert(p==&player);for(i=0;i<5;i++)if(!strcmp(name,field_names[i]))return i==missing?NULL:&field_values[i];return NULL;}
char *ED_NewString(char *s){int i;for(i=0;i<120;i++)if(!strcmp(pr_strings+i,s))return pr_strings+i;assert(0);return NULL;}
void Con_Printf(char *fmt,...){if(strstr(fmt,"equipment"))warnings++;}
int AW_BarrierLoad(void){return 1;}void AW_OpeningSpawn(void){}
int AW_NPCFloor(edict_t *p){return 1;}int AW_RegionContains(const float *p){return 1;}
void SV_LinkEdict(edict_t *p,qboolean b){}int AW_ReaderActive(void){return 0;}
int COM_FOpenFile(char *name,FILE **f){*f=NULL;return -1;}
float anglemod(float a){return a;}
static unsigned char raw[AW_SAVE_BYTES],copy[AW_SAVE_BYTES];
static aw_save_t original,decoded,unchanged;
static int bytes(const char *p){FILE *f=fopen(p,"rb");int n;assert(f);n=fread(raw,1,sizeof(raw),f);assert(fgetc(f)==EOF);fclose(f);return n;}
static void hand(int goal,int state,int torch){memset(field_values,0,sizeof(field_values));field_values[0]._float=goal;field_values[1]._float=state;field_values[2]._float=torch;field_values[3]._float=sv.time-.2;field_values[4]._float=1;player.v.weaponframe=state?2:0;player.v.weaponmodel=state?1:0;}
static void restore(const aw_save_t *s){pending=*s;loading=1;AW_SaveSpawn();assert(!loading);}
#ifndef OLD_CONTROL
static void header(unsigned char *p,int size){uint32_t crc=0xffffffffU;int i,j;for(i=12;i<size;i++){crc^=p[i];for(j=0;j<8;j++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}crc^=0xffffffffU;for(i=0;i<4;i++){p[4+i]=(unsigned)size>>(i*8);p[8+i]=crc>>(i*8);}}
static void bad(const unsigned char *p,int n){memset(&unchanged,0xa5,sizeof(unchanged));decoded=unchanged;assert(!AW_SaveDecode(p,n,&decoded));assert(!memcmp(&decoded,&unchanged,sizeof(decoded)));}
static void intent(void){uint32_t flags;int i;static const int goal[]={0,1,1,1,0};static const int state[]={0,1,2,3,4};
 pr_strings=strings_a;sv.time=10;
 for(i=0;i<5;i++){hand(goal[i],state[i],0);flags=0xdeadbeef;assert(AW_SavedEquipmentCapture(&flags,&player,sv.time));assert(flags==(goal[i]?1U:0U));}
 hand(1,2,1);assert(AW_SavedEquipmentCapture(&flags,&player,sv.time)&&flags==3);
 hand(0,4,1);assert(AW_SavedEquipmentCapture(&flags,&player,sv.time)&&flags==0);
 hand(1,2,1);player.v.weaponmodel=18;flags=0xdeadbeef;assert(!AW_SavedEquipmentCapture(&flags,&player,sv.time)&&flags==0xdeadbeef);
 hand(1,2,1);field_values[0]._float=NAN;assert(!AW_SavedEquipmentCapture(&flags,&player,sv.time));
 hand(1,2,1);missing=2;assert(!AW_SavedEquipmentCapture(&flags,&player,sv.time));missing=-1;
 hand(1,2,1);pr_strings=strings_b;sv.time=32;assert(AW_SavedEquipmentRestore(3,&player,sv.time));
 assert(field_values[0]._float==1&&field_values[1]._float==2&&field_values[2]._float==1&&field_values[3]._float==32&&!field_values[4]._float);
 assert(!player.v.weaponframe&&player.v.weaponmodel!=1&&!strcmp(pr_strings+player.v.weaponmodel,"progs/v_nord.mdl"));
 sv.model_precache[1]=NULL;assert(!AW_SavedEquipmentRestore(3,&player,sv.time));assert(field_values[2]._float==1);sv.model_precache[1]="progs/v_nord.mdl";
 missing=4;assert(!AW_SavedEquipmentRestore(0,&player,sv.time));assert(field_values[2]._float==1);missing=-1;
 assert(!AW_SavedEquipmentRestore(2,&player,sv.time));assert(!AW_SavedEquipmentRestore(4,&player,sv.time));assert(!AW_SavedEquipmentRestore(3,&player,NAN));
 assert(AW_SavedEquipmentRestore(0,&player,sv.time));assert(!field_values[0]._float&&!field_values[1]._float&&!field_values[2]._float&&!player.v.weaponmodel);
}
#endif
int main(int argc,char **argv){int n;char filename[512];assert(argc==2);
 aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=2;
 strcpy(aw_races[0].id,"test_race");strcpy(aw_classes[0].id,"test_class");
 strcpy(aw_births[0].id,"test_sign");strcpy(aw_parts[0].id,"test_head");
 strcpy(aw_parts[1].id,"test_hair");aw_parts[1].kind=1;
 original.sequence=1;original.profile=2;strcpy(original.scene,"seyda");
 strcpy(original.story.name,"Synthetic");original.story.stage=AW_STAGE_RELEASED;
 original.story.ship_disabled=1;original.story.captain=-1;
 original.character.level=1;original.character.hair=1;original.character.valid=1;
 original.character.current[0]=original.character.maximum[0]=50;
 assert(AW_StateSet(&original.state,AW_GLOBAL,"chargenstate",-1));
 assert(AW_ItemAdd(&original.state,"ingredient_test",1));
 original.state.harvest.slots=4;memset(original.state.harvest.catalogue,0x36,32);
 original.state.harvest.facts[0]=0x40100001U;
 strcpy(com_gamedir,argv[1]);pr_strings=strings_a;sv.active=1;sv.num_edicts=1;sv.time=10;strcpy(sv.name,"seyda");sv.model_precache[1]="progs/v_nord.mdl";svs.maxclients=1;svs.clients=&client;client.edict=&player;
 world=original;aw_story=original.story;aw_state=original.state;aw_character=original.character;player.v.health=aw_character.current[0];player.v.movetype=MOVETYPE_WALK;memcpy(content_id,original.content,32);content_ready=1;hand(1,2,1);
 assert(AW_SaveWrite(0));assert(path(filename,sizeof(filename),world.profile,0,0));n=bytes(filename);assert(AW_SaveDecode(raw,n,&decoded));
 /* Loading does not inherit currently hidden equipment: use only saved intent. */
 hand(0,0,0);pr_strings=strings_b;sv.time=32;restore(&decoded);
 assert(field_values[0]._float==1&&field_values[1]._float==2&&field_values[2]._float==1);
 assert(!field_values[4]._float&&!player.v.weaponframe&&field_values[3]._float==32);
 assert(!strcmp(pr_strings+player.v.weaponmodel,"progs/v_nord.mdl"));assert(AW_StateGet(&aw_state,AW_ITEM,"ingredient_test")==1);
#ifndef OLD_CONTROL
 assert(decoded.equipment==3);
 original.equipment=0;restore(&original);assert(!field_values[0]._float&&!field_values[2]._float&&!player.v.weaponmodel);
 decoded.equipment=3;sv.model_precache[1]=NULL;warnings=0;restore(&decoded);assert(warnings==1&&!field_values[2]._float);sv.model_precache[1]="progs/v_nord.mdl";
 {uint32_t sequence=world.sequence;pr_strings=strings_a;hand(1,2,1);player.v.weaponmodel=18;assert(!AW_SaveWrite(0)&&world.sequence==sequence);}
 intent();
 original.equipment=3;n=AW_SaveEncode(raw,sizeof(raw),&original);
 assert(n>0 && !memcmp(raw,"AWS4",4));assert(AW_SaveDecode(raw,n,&decoded));
 assert(decoded.state.harvest.facts[0]==original.state.harvest.facts[0]);
 memcpy(copy,raw,n);copy[n-4]=2;header(copy,n);bad(copy,n);
 memcpy(copy,raw,n);copy[n-4]=4;header(copy,n);bad(copy,n);
 bad(raw,n-1);
#endif

 /* One original actor remains one saved fact across distinct physical maps. */
 pr_strings=strings_a;npc.v.classname=42;npc_ref._float=221999;npc_hello._float=7;
 npc.v.health=43;npc.v.origin[0]=-150;npc.v.origin[1]=1088;npc.v.origin[2]=-192;
 sv.num_edicts=3;strcpy(sv.name,"mi5b8154939f7aa");world=original;
 world.actor_count=0;AW_SaveCapture();assert(world.actor_count==1 && world.actors[0].scene==8252);
 strcpy(sv.name,"mi5b8154939f7ab");npc.v.health=1;npc_hello._float=0;
 loading=0;AW_SaveSpawn();assert(npc.v.health==43 && npc_hello._float==7);
 npc_hello._float=8;AW_SaveCapture();assert(world.actor_count==1 && world.actors[0].hello_count==8);
 aw_story=original.story;aw_character=original.character;aw_state=original.state;
 hand(1,2,1);assert(AW_SaveWrite(1));assert(path(filename,sizeof(filename),world.profile,1,0));
 n=bytes(filename);assert(AW_SaveDecode(raw,n,&decoded));
 assert(!strcmp(decoded.scene,"mi5b8154939f7ab") && decoded.actors[0].scene==8252);
 assert(decoded.equipment==3 && decoded.state.harvest.facts[0]==original.state.harvest.facts[0]);
 assert(AW_StateGet(&decoded.state,AW_ITEM,"ingredient_test")==1);
 assert(AW_StateGet(&decoded.state,AW_GLOBAL,"chargenstate")==-1);
 hand(0,0,0);npc_hello._float=0;restore(&decoded);
 assert(npc_hello._float==8 && field_values[2]._float==1);
 puts("Physical section save resume, one logical NPC fact, inventory/quest/harvest and equipment roundtrip passed.");
 puts("Actual save/write/load-apply, legacy, intent, malformed and capacity gates passed.");return 0;}
