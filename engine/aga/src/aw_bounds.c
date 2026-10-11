/* SPDX-License-Identifier: GPL-2.0-or-later
 * World bounds (an AmiWind extension; docs/WORLD_BOUNDS.md). Morrowind's sea
 * goes on; ours ends 896 units past the outermost open-world cells, where an
 * invisible wall used to stop the player. With aw_world_bounds 1 (written by
 * the builder, --world-bounds on, the default) the water near that edge
 * carries a current along it and back in, and outward motion fades before
 * the wall, so the player drifts along the coast and is never held there.
 *
 * Quake mechanism: the water currents (CONTENTS_CURRENT_*, 150 units/s by
 * depth, sv_phys.c SV_CheckWater) and their basevelocity, added for the move
 * and taken off after it. Quake bakes currents into leaf contents; our qbsp
 * does not write them, the push is compiled only for Quake 2 (#ifdef QUAKE2)
 * and every outer map would need its own copy, so the push is chosen by
 * position from the open-world directory's cells (aw_bounds_rules.c). */
#include "quakedef.h"
#include "aw_bounds.h"
#include "aw_world.h"

cvar_t aw_world_bounds={"aw_world_bounds","0"};   /* not saved: the builder's default-game.cfg sets it */
static int attempted;

static int table(void)
{
    float *centres;int n;
    if(attempted)return AW_BoundsReady();
    attempted=1;
    n=AW_WorldRegionCentres(NULL,0);
    if(n<1)return 0;
    centres=(float *)malloc(sizeof(float)*2*n);
    if(!centres)return 0;
    AW_WorldRegionCentres(centres,n);
    if(!AW_BoundsBuild(centres,n))Con_Printf("World bounds: the open-world directory does not fit the table; bounds off.\n");
    free(centres);
    return AW_BoundsReady();
}
/* The player's map-unit point in the open world (0: an interior or no world). */
static int world_point(edict_t *ent,float *point)
{
    float source[3];
    if(!AW_WorldToSource(sv.name,ent->v.origin,source))return 0;
    point[0]=source[0]*.25f;point[1]=source[1]*.25f;point[2]=source[2]*.25f;
    return 1;
}
/* SV_Physics_Client, walking and flying (never noclip): adds the drift to the
 * velocity for this move; the caller takes it off after the move. */
static int player(edict_t *ent,vec3_t drift)
{
    float point[3];
    drift[0]=drift[1]=drift[2]=0;
    if(!aw_world_bounds.value || ent->v.movetype==MOVETYPE_NOCLIP || !world_point(ent,point) || !table())return 0;
    if(!AW_BoundsPush(point,ent->v.velocity,(int)ent->v.waterlevel,drift))return 0;
    VectorAdd(ent->v.velocity,drift,ent->v.velocity);
    return 1;
}
/* dbg worldbounds [on/off, true/false or 1/0]: no argument shows the state,
 * the world's box and where the player is against its edge. Not saved. */
static void command(void)
{
    char *text=Cmd_Argv(1);int box[4],cells;float point[3],depth,normal[2];
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && Q_strcasecmp(text,"on") && Q_strcasecmp(text,"off") &&
       Q_strcasecmp(text,"true") && Q_strcasecmp(text,"false") && strcmp(text,"1") && strcmp(text,"0"))){
        Con_Printf("Usage: dbg worldbounds [on/off, true/false or 1/0]; no argument shows the state (not saved).\n");return;}
    if(Cmd_Argc()==2)
        Cvar_SetValue("aw_world_bounds",(!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1"))?1:0);
    cells=table()?AW_BoundsCells(box):0;
    if(!cells){Con_Printf("World bounds %s; no open-world directory in this game.\n",aw_world_bounds.value?"ON":"OFF");return;}
    Con_Printf("World bounds %s: %d cells, box %d,%d .. %d,%d (an AmiWind extension: the sea at the edge carries you along it).\n",
               aw_world_bounds.value?"ON":"OFF",cells,box[0],box[1],box[2],box[3]);
    if(sv.active && sv_player && world_point(sv_player,point)){
        if(AW_BoundsField(point,&depth,normal))
            Con_Printf("You are %ld units %s the edge (outward %ld %ld).\n",(long)fabs(depth),depth>0?"past":"inside",
                       (long)(normal[0]*100),(long)(normal[1]*100));
        else Con_Printf("You are well inside the world.\n");
    }
}
void AW_BoundsInit(void)
{
    Cvar_RegisterVariable(&aw_world_bounds);
    Cmd_AddCommand("aw_worldbounds",command);
    aw_bounds_player=player;
}
