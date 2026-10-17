/* SPDX-License-Identifier: GPL-2.0-or-later */
/* NOCLIP-BOB-DEFAULT-42: no walking bob and no movement roll in noclip unless aw_noclipwobble 1, decided by
 * the local player's movetype (Quake's noclip_anglehack is cleared by every map load: a CHIM frame or region
 * crossing in noclip kept flying with the bob back on). Leaving noclip gives the player's own bob and roll
 * back exactly; nothing is forced or saved. */
#include "quakedef.h"
#include <assert.h>
client_state_t cl;
entity_t cl_entities[MAX_EDICTS];
viddef_t vid;
double host_frametime;
server_t sv;
server_static_t svs;
qboolean noclip_anglehack;
byte *host_basepal;
refdef_t r_refdef;
cvar_t chase_active={"chase_active","0"};
extern cvar_t cl_bob,cl_bobcycle,cl_bobup,cl_rollangle,cl_rollspeed,aw_noclipwobble;
float V_CalcBob(void);
void V_CalcViewRoll(void);
static float roll(void){r_refdef.viewangles[ROLL]=0;V_CalcViewRoll();return r_refdef.viewangles[ROLL];}
int main(void){
 client_t local;edict_t player;float walk_bob,walk_roll;
 memset(&local,0,sizeof(local));memset(&player,0,sizeof(player));
 cl_bob.value=0.02f;cl_bobcycle.value=0.6f;cl_bobup.value=0.5f;cl_rollangle.value=2;cl_rollspeed.value=200;
 sv.active=true;svs.maxclients=1;svs.clients=&local;local.edict=&player;
 cl.viewentity=1;cl.time=0.1;cl.stats[STAT_HEALTH]=100;cl.velocity[0]=200;cl.velocity[1]=150;
 player.v.movetype=MOVETYPE_WALK;
 walk_bob=V_CalcBob();walk_roll=roll();
 assert(walk_bob!=0 && walk_roll!=0);
 /* Noclip through the console (Host_Noclip_f sets both) and after a map load (the flag cleared). */
 player.v.movetype=MOVETYPE_NOCLIP;noclip_anglehack=true;
 assert(V_CalcBob()==0 && roll()==0);
 noclip_anglehack=false;
 assert(V_CalcBob()==0 && roll()==0);
 /* aw_noclipwobble 1 brings both back, unchanged. */
 aw_noclipwobble.value=1;assert(V_CalcBob()==walk_bob && roll()==walk_roll);aw_noclipwobble.value=0;
 /* Leaving noclip: the same walking bob and roll as before, from the player's own settings. */
 player.v.movetype=MOVETYPE_WALK;
 assert(V_CalcBob()==walk_bob && roll()==walk_roll);
 assert(cl_bob.value==0.02f && cl_rollangle.value==2);
 /* Without a local server (demo playback) only Quake's flag decides. */
 sv.active=false;player.v.movetype=MOVETYPE_NOCLIP;assert(V_CalcBob()==walk_bob);
 noclip_anglehack=true;assert(V_CalcBob()==0);
 puts("noclip bob and roll off, walking bob restored");
 return 0;
}
