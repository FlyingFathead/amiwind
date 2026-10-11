/* SPDX-License-Identifier: GPL-2.0-or-later
 * The one "player dead" predicate (quakedef.h AW_PlayerDead, PLAYER-DEATH-LIMBO-35): true only for the
 * single-player player whose health is gone; every name, hint, crosshair, voice, greeting and activation
 * path asks it (tests/test_third_person.py pins the callers). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "quakedef.h"

server_t sv;
server_static_t svs;
static client_t client;
static edict_t player;

int main(void) {
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(&client,0,sizeof(client));memset(&player,0,sizeof(player));
    assert(!AW_PlayerDead());                               /* no game */
    sv.active=true;svs.maxclients=1;
    assert(!AW_PlayerDead());                               /* no client yet */
    svs.clients=&client;
    assert(!AW_PlayerDead());                               /* no player entity yet */
    client.edict=&player;player.v.health=100;
    assert(!AW_PlayerDead());                               /* alive */
    player.v.health=.5f;assert(!AW_PlayerDead());
    player.v.health=0;assert(AW_PlayerDead());              /* dead */
    player.v.health=-12;assert(AW_PlayerDead());
    svs.maxclients=2;assert(!AW_PlayerDead());              /* single player only */
    svs.maxclients=1;sv.active=false;assert(!AW_PlayerDead());   /* no server: nothing to ask */
    puts("player dead predicate ok");
    return 0;
}
