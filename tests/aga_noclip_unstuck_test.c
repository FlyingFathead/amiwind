/* SPDX-License-Identifier: GPL-2.0-or-later
 * JOURNEY-DOCK-NOCLIP-UNSTUCK-RACE-68: noclip switched off where the box touches the world, then the next frame's stuck
 * check, run with the engine's own functions: host_cmd.c Host_Noclip_f and sv_phys.c SV_CheckStuck, cut out by
 * tests/test_noclip_unstuck.py into noclip_slice.c. This file is the server around them.
 *
 * The case, by number (the opening journey's first step, Seyda Neen's pier on the v0.0.68-dev6 image): the player
 * walks at the town start (16 44), noclip goes on, the flight ends at the plank end (627 -390 75), noclip goes off
 * there (its own test, which counts other bodies, lets it), and the next frame's world test finds the box touching the
 * rising plank. The stuck check falls back to ent->v.oldorigin, which only that check keeps, and only while walking:
 * before the fix it still held the spot before the flight, so the player was thrown back by the town start. Now noclip
 * going off keeps the spot it goes off at, and the check lifts the box clear where it stands. */
#include "quakedef.h"
#include <assert.h>

server_t sv;edict_t *sv_player;client_t *host_client;globalvars_t *pr_global_struct;cmd_source_t cmd_source;
qboolean noclip_anglehack;vec3_t vec3_origin;
static client_t client;static globalvars_t globals;static edict_t player;
static int noclip_on,noclip_off,noclip_refused,links;
void Cmd_ForwardToServer(void){assert(0);}
void SV_ClientPrintf(char *fmt,...){
    if(!strcmp(fmt,"noclip ON\n"))noclip_on++;
    else if(!strcmp(fmt,"noclip OFF\n"))noclip_off++;
    else noclip_refused++;
}
void Con_DPrintf(char *fmt,...){(void)fmt;}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;links++;}
/* noclip's own test: the other bodies too; here nothing overlaps the player there */
edict_t *SV_TestEntityPosition(edict_t *e){(void)e;return NULL;}
/* the world's clipping hull: the plank end (x 600..700) is solid up to 78 units; the pier and the town are free above 0 */
edict_t *SV_TestWorldPosition(edict_t *e){
    const float *o=e->v.origin;
    if(o[0]>=600 && o[0]<=700 && o[2]<78)return e;
    return o[2]<0?e:NULL;
}
#include "noclip_slice.c"
static void set(float x,float y,float z){player.v.origin[0]=x;player.v.origin[1]=y;player.v.origin[2]=z;}
static float dist2d(float x,float y){
    float dx=player.v.origin[0]-x,dy=player.v.origin[1]-y;return (float)sqrt(dx*dx+dy*dy);
}
int main(void){
    int failed=0;
    sv_player=&player;host_client=&client;pr_global_struct=&globals;globals.deathmatch=0;cmd_source=src_client;
    /* walking at the town start: the frame's check keeps the spot */
    player.v.movetype=MOVETYPE_WALK;set(16,44,48);SV_CheckStuck(&player);
    /* noclip on, the flight to the plank end (no stuck check while flying, as SV_Physics_Client) */
    Host_Noclip_f();assert(player.v.movetype==MOVETYPE_NOCLIP && noclip_on==1);
    set(627,-390,75);
    /* noclip off there, then the next frame's check */
    Host_Noclip_f();assert(player.v.movetype==MOVETYPE_WALK && noclip_off==1 && !noclip_refused);
    SV_CheckStuck(&player);
    printf("noclip off at the plank end (627 -390 75): the check left the player at %.0f %.0f %.0f\n",
           player.v.origin[0],player.v.origin[1],player.v.origin[2]);
    if(dist2d(16,44)<50){puts("FAIL: thrown back to the spot before the flight, by the town start");failed=1;}
    else if(dist2d(627,-390)>2 || player.v.origin[2]<78 || player.v.origin[2]>75+18){
        puts("FAIL: not lifted clear where noclip went off");failed=1;
    }else puts("ok: lifted clear where noclip went off");
    /* noclip off over free floor: nothing moves */
    Host_Noclip_f();set(300,-200,60);Host_Noclip_f();SV_CheckStuck(&player);
    if(dist2d(300,-200)>0.01f || player.v.origin[2]!=60){puts("FAIL: a free spot was moved");failed=1;}
    else puts("ok: over free floor the player stays");
    if(failed){puts("FAIL");return 1;}
    puts("PASS: noclip going off keeps the spot a stuck check falls back to");
    return 0;
}
