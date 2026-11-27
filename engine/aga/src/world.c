/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// world.c -- world query functions

#include "quakedef.h"

/*

entities never clip against themselves, or their owner

line of sight checks trace->crosscontent, but bullets don't

*/


typedef struct
{
	vec3_t		boxmins, boxmaxs;// enclose the test object along entire move
	float		*mins, *maxs;	// size of the moving object
	vec3_t		mins2, maxs2;	// size when clipping against mosnters
	float		*start, *end;
	trace_t		trace;
	int			type;
	edict_t		*passedict;
} moveclip_t;


int SV_HullPointContents (hull_t *hull, int num, vec3_t p);

/*
===============================================================================

HULL BOXES

===============================================================================
*/


static	hull_t		box_hull;
static	dclipnode_t	box_clipnodes[6];
static	mplane_t	box_planes[6];

/*
===================
SV_InitBoxHull

Set up the planes and clipnodes so that the six floats of a bounding box
can just be stored out and get a proper hull_t structure.
===================
*/
void SV_InitBoxHull (void)
{
	int		i;
	int		side;

	box_hull.clipnodes = box_clipnodes;
	box_hull.planes = box_planes;
	box_hull.firstclipnode = 0;
	box_hull.lastclipnode = 5;

	for (i=0 ; i<6 ; i++)
	{
		box_clipnodes[i].planenum = i;

		side = i&1;

		box_clipnodes[i].children[side] = CONTENTS_EMPTY;
		if (i != 5)
			box_clipnodes[i].children[side^1] = i + 1;
		else
			box_clipnodes[i].children[side^1] = CONTENTS_SOLID;

		box_planes[i].type = i>>1;
		box_planes[i].normal[i>>1] = 1;
	}

}


/*
===================
SV_HullForBox

To keep everything totally uniform, bounding boxes are turned into small
BSP trees instead of being compared directly.
===================
*/
hull_t	*SV_HullForBox (vec3_t mins, vec3_t maxs)
{
	box_planes[0].dist = maxs[0];
	box_planes[1].dist = mins[0];
	box_planes[2].dist = maxs[1];
	box_planes[3].dist = mins[1];
	box_planes[4].dist = maxs[2];
	box_planes[5].dist = mins[2];

	return &box_hull;
}



/*
================
SV_HullForEntity

Returns a hull that can be used for testing or clipping an object of mins/maxs
size.
Offset is filled in to contain the adjustment that must be added to the
testing object's origin to get a point to use with the returned hull.
================
*/
/* SOL-SEA-INVISIBLE-BLOCKER-68: the top a body collides up to: a creature's drawn top when aw_actor_clip.c set one
 * (its box, the hull it walks the world with, is unchanged), else its box top. NULL: the box top. Declared in
 * aw_actor_clip.h, not world.h: quakedef.h's headers are in the CHIM world's stage key (chim_zone.c's includes). */
float (*aw_actor_clip_top)(const edict_t *e);

static float ClipTop (const edict_t *e)
{
	return aw_actor_clip_top ? aw_actor_clip_top (e) : e->v.maxs[2];
}

hull_t *SV_HullForEntity (edict_t *ent, vec3_t mins, vec3_t maxs, vec3_t offset)
{
	model_t		*model;
	vec3_t		size;
	vec3_t		hullmins, hullmaxs;
	hull_t		*hull;

// decide which clipping hull to use, based on the size
	if (ent->v.solid == SOLID_BSP)
	{	// explicit hulls in the BSP model
		if (ent->v.movetype != MOVETYPE_PUSH)
			Sys_Error ("SOLID_BSP without MOVETYPE_PUSH");

		model = sv.models[ (int)ent->v.modelindex ];

		if (!model || model->type != mod_brush)
			Sys_Error ("MOVETYPE_PUSH with a non bsp model");

		VectorSubtract (maxs, mins, size);
		if (size[0] < 3)
			hull = &model->hulls[0];
		else if (size[0] <= 32)
			hull = &model->hulls[1];
		else
			hull = &model->hulls[2];

// calculate an offset value to center the origin
		VectorSubtract (hull->clip_mins, mins, offset);
		VectorAdd (offset, ent->v.origin, offset);
	}
	else
	{	// create a temp hull from bounding box sizes

		VectorSubtract (ent->v.mins, maxs, hullmins);
		VectorSubtract (ent->v.maxs, mins, hullmaxs);
		hullmaxs[2] = ClipTop (ent) - mins[2];
		hull = SV_HullForBox (hullmins, hullmaxs);

		VectorCopy (ent->v.origin, offset);
	}


	return hull;
}

/*
===============================================================================

ENTITY AREA CHECKING

===============================================================================
*/

typedef struct areanode_s
{
	int		axis;		// -1 = leaf node
	float	dist;
	struct areanode_s	*children[2];
	link_t	trigger_edicts;
	link_t	solid_edicts;
} areanode_t;

#define	AREA_DEPTH	4
#define	AREA_NODES	32

static	areanode_t	sv_areanodes[AREA_NODES];
static	int			sv_numareanodes;

/*
===============
SV_CreateAreaNode

===============
*/
areanode_t *SV_CreateAreaNode (int depth, vec3_t mins, vec3_t maxs)
{
	areanode_t	*anode;
	vec3_t		size;
	vec3_t		mins1, maxs1, mins2, maxs2;

	anode = &sv_areanodes[sv_numareanodes];
	sv_numareanodes++;

	ClearLink (&anode->trigger_edicts);
	ClearLink (&anode->solid_edicts);

	if (depth == AREA_DEPTH)
	{
		anode->axis = -1;
		anode->children[0] = anode->children[1] = NULL;
		return anode;
	}

	VectorSubtract (maxs, mins, size);
	if (size[0] > size[1])
		anode->axis = 0;
	else
		anode->axis = 1;

	anode->dist = 0.5 * (maxs[anode->axis] + mins[anode->axis]);
	VectorCopy (mins, mins1);
	VectorCopy (mins, mins2);
	VectorCopy (maxs, maxs1);
	VectorCopy (maxs, maxs2);

	maxs1[anode->axis] = mins2[anode->axis] = anode->dist;

	anode->children[0] = SV_CreateAreaNode (depth+1, mins2, maxs2);
	anode->children[1] = SV_CreateAreaNode (depth+1, mins1, maxs1);

	return anode;
}

/*
===============
SV_ClearWorld

===============
*/
void SV_ClearWorld (void)
{
	SV_InitBoxHull ();

	memset (sv_areanodes, 0, sizeof(sv_areanodes));
	sv_numareanodes = 0;
	SV_CreateAreaNode (0, sv.worldmodel->mins, sv.worldmodel->maxs);
}


/*
===============
SV_UnlinkEdict

===============
*/
void SV_UnlinkEdict (edict_t *ent)
{
	if (!ent->area.prev)
		return;		// not linked in anywhere
	RemoveLink (&ent->area);
	ent->area.prev = ent->area.next = NULL;
}


/*
====================
SV_TouchLinks
====================
*/
void SV_TouchLinks ( edict_t *ent, areanode_t *node )
{
	link_t		*l, *next;
	edict_t		*touch;
	int			old_self, old_other;

// touch linked edicts
	for (l = node->trigger_edicts.next ; l != &node->trigger_edicts ; l = next)
	{
		next = l->next;
		touch = EDICT_FROM_AREA(l);
		if (touch == ent)
			continue;
		if (!touch->v.touch || touch->v.solid != SOLID_TRIGGER)
			continue;
		if (ent->v.absmin[0] > touch->v.absmax[0]
		|| ent->v.absmin[1] > touch->v.absmax[1]
		|| ent->v.absmin[2] > touch->v.absmax[2]
		|| ent->v.absmax[0] < touch->v.absmin[0]
		|| ent->v.absmax[1] < touch->v.absmin[1]
		|| ent->v.absmax[2] < touch->v.absmin[2] )
			continue;
		old_self = pr_global_struct->self;
		old_other = pr_global_struct->other;

		pr_global_struct->self = EDICT_TO_PROG(touch);
		pr_global_struct->other = EDICT_TO_PROG(ent);
		pr_global_struct->time = sv.time;
		PR_ExecuteProgram (touch->v.touch);

		pr_global_struct->self = old_self;
		pr_global_struct->other = old_other;
	}

// recurse down both sides
	if (node->axis == -1)
		return;

	if ( ent->v.absmax[node->axis] > node->dist )
		SV_TouchLinks ( ent, node->children[0] );
	if ( ent->v.absmin[node->axis] < node->dist )
		SV_TouchLinks ( ent, node->children[1] );
}


/*
===============
SV_FindTouchedLeafs

===============
*/
void SV_FindTouchedLeafs (edict_t *ent, mnode_t *node)
{
	mplane_t	*splitplane;
	mleaf_t		*leaf;
	int			sides;
	int			leafnum;

	if (node->contents == CONTENTS_SOLID)
		return;

// add an efrag if the node is a leaf

	if ( node->contents < 0)
	{
		if (ent->num_leafs == MAX_ENT_LEAFS)
			return;

		leaf = (mleaf_t *)node;
		leafnum = leaf - sv.worldmodel->leafs - 1;

		ent->leafnums[ent->num_leafs] = leafnum;
		ent->num_leafs++;
		return;
	}

// NODE_MIXED

	splitplane = node->plane;
	sides = BOX_ON_PLANE_SIDE(ent->v.absmin, ent->v.absmax, splitplane);

// recurse down the contacted sides
	if (sides & 1)
		SV_FindTouchedLeafs (ent, node->children[0]);

	if (sides & 2)
		SV_FindTouchedLeafs (ent, node->children[1]);
}

/*
===============
SV_LinkEdict

===============
*/
void SV_LinkEdict (edict_t *ent, qboolean touch_triggers)
{
	areanode_t	*node;

	if (ent->area.prev)
		SV_UnlinkEdict (ent);	// unlink from old position

	if (ent == sv.edicts)
		return;		// don't add the world

	if (ent->free)
		return;

// set the abs box

/* AmiWind: static architectural brushes have non-zero yaw. */
#if 1
	if (ent->v.solid == SOLID_BSP &&
	(ent->v.angles[0] || ent->v.angles[1] || ent->v.angles[2]) )
	{	// expand for rotation
        float radius, corner[3];
        int i;
        for(i=0;i<3;i++)corner[i]=fabs(ent->v.mins[i])>fabs(ent->v.maxs[i]) ? fabs(ent->v.mins[i]):fabs(ent->v.maxs[i]);
        radius=sqrt(DotProduct(corner,corner));
		for (i=0 ; i<3 ; i++)
		{
			ent->v.absmin[i] = ent->v.origin[i] - radius;
			ent->v.absmax[i] = ent->v.origin[i] + radius;
		}
	}
	else
#endif
	{
		VectorAdd (ent->v.origin, ent->v.mins, ent->v.absmin);
		VectorAdd (ent->v.origin, ent->v.maxs, ent->v.absmax);
	}

//
// to make items easier to pick up and allow them to be grabbed off
// of shelves, the abs sizes are expanded
//
	if ((int)ent->v.flags & FL_ITEM)
	{
		ent->v.absmin[0] -= 15;
		ent->v.absmin[1] -= 15;
		ent->v.absmax[0] += 15;
		ent->v.absmax[1] += 15;
	}
	else
	{	// because movement is clipped an epsilon away from an actual edge,
		// we must fully check even when bounding boxes don't quite touch
		ent->v.absmin[0] -= 1;
		ent->v.absmin[1] -= 1;
		ent->v.absmin[2] -= 1;
		ent->v.absmax[0] += 1;
		ent->v.absmax[1] += 1;
		ent->v.absmax[2] += 1;
	}

// link to PVS leafs
	ent->num_leafs = 0;
	if (ent->v.modelindex)
		SV_FindTouchedLeafs (ent, sv.worldmodel->nodes);

	if (ent->v.solid == SOLID_NOT)
		return;

// find the first node that the ent's box crosses
	node = sv_areanodes;
	while (1)
	{
		if (node->axis == -1)
			break;
		if (ent->v.absmin[node->axis] > node->dist)
			node = node->children[0];
		else if (ent->v.absmax[node->axis] < node->dist)
			node = node->children[1];
		else
			break;		// crosses the node
	}

// link it in

	if (ent->v.solid == SOLID_TRIGGER)
		InsertLinkBefore (&ent->area, &node->trigger_edicts);
	else
		InsertLinkBefore (&ent->area, &node->solid_edicts);

// if touch_triggers, touch all entities at this node and decend for more
	if (touch_triggers)
		SV_TouchLinks ( ent, sv_areanodes );
}



/*
===============================================================================

POINT TESTING IN HULLS

===============================================================================
*/

#if	!id386

/*
==================
SV_HullPointContents

==================
*/
/* Extended BSP29 clip indices use the unsigned half of the 16-bit field.
 * -1..-15 remain contents values; storage and Amiga memory cost stay unchanged. */
static int AW_ClipChild(short child)
{
    return child < -15 ? (unsigned short)child : child;
}

int SV_HullPointContents (hull_t *hull, int num, vec3_t p)
{
	float		d;
	dclipnode_t	*node;
	mplane_t	*plane;

	while (num >= 0)
	{
		if (num < hull->firstclipnode || num > hull->lastclipnode)
			Sys_Error ("SV_HullPointContents: bad node number");

		node = hull->clipnodes + num;
		plane = hull->planes + node->planenum;

		if (plane->type < 3)
			d = p[plane->type] - plane->dist;
		else
			d = DotProduct (plane->normal, p) - plane->dist;
		if (d < 0)
			num = AW_ClipChild(node->children[1]);
		else
			num = AW_ClipChild(node->children[0]);
	}

	return num;
}

#endif	// !id386


/*
==================
SV_PointContents

==================
*/
int SV_PointContents (vec3_t p)
{
	int		cont;

	cont = SV_HullPointContents (&sv.worldmodel->hulls[0], 0, p);
	if (cont <= CONTENTS_CURRENT_0 && cont >= CONTENTS_CURRENT_DOWN)
		cont = CONTENTS_WATER;
	return cont;
}

int SV_TruePointContents (vec3_t p)
{
	return SV_HullPointContents (&sv.worldmodel->hulls[0], 0, p);
}

//===========================================================================

/*
============
SV_TestEntityPosition

This could be a lot more efficient...
============
*/
edict_t	*SV_TestEntityPosition (edict_t *ent)
{
	trace_t	trace;

	trace = SV_Move (ent->v.origin, ent->v.mins, ent->v.maxs, ent->v.origin, 0, ent);

	if (trace.startsolid)
		return sv.edicts;

	return NULL;
}

/*
===============================================================================

BODIES THAT OVERLAP (DOOR-ARRIVAL-INSIDE-ACTOR-66)

===============================================================================
*/

/* aw_body_overlap 1 (the default, also written into id1/default-game.cfg): two bodies whose boxes already overlap
 * collide as the original's actors do; 0: Quake's box clip for every pair, the method before v0.0.66. Not saved. */
cvar_t aw_body_overlap = {"aw_body_overlap", "1", false, false, 1};

/* Two bodies (SOLID_SLIDEBOX: the player, residents, creatures) whose boxes already overlap when a box sweep starts:
 * an actor left standing on a door's arrival point, one placed where the player stands. The rule is the original's as
 * OpenMW 0.51 states it (apps/openmw/mwphysics/actorconvexcallback.cpp: overlapping actors collide as cylinders with
 * the distance between them as diameter; its motion vector is from minus to, trace.cpp): only a move that heads
 * horizontally toward the other's centre is stopped, at once, on the upright plane facing away from that centre;
 * every other move (away, along, up or down, or with both centres in one place) passes the other body, so the two can
 * always walk apart. Quake clips the sum of the two boxes instead: a sweep that starts inside it is allsolid until
 * one frame's move leaves it whole, SV_FlyMove then zeroes the velocity, and neither body could step out (at the
 * Seyda Neen census door the two boxes overlapped by 6.2 units across and 12.6 along). A position test
 * (START == END) is unchanged, so the placement searches still keep bodies apart.
 * Returns 0: not such a pair, Quake's clip applies; 1: the move passes TOUCH; 2: stopped, TRACE holds the stop. */
int AW_BodyOverlap (const edict_t *mover, const edict_t *touch, const float *start, const float *mins,
	const float *maxs, const float *end, trace_t *trace)
{
	float	n[2], len;
	int		i;

	if (!aw_body_overlap.value || !mover || mover->v.solid != SOLID_SLIDEBOX || touch->v.solid != SOLID_SLIDEBOX)
		return 0;
	if (maxs[0] <= mins[0] || maxs[1] <= mins[1])
		return 0;		/* a point trace (a sight line, a use ray): not a body's move */
	if (start[0] == end[0] && start[1] == end[1] && start[2] == end[2])
		return 0;		/* a position test */
	for (i=0 ; i<3 ; i++)
		if (start[i] + mins[i] >= touch->v.origin[i] + (i == 2 ? ClipTop (touch) : touch->v.maxs[i]) ||
			start[i] + maxs[i] <= touch->v.origin[i] + touch->v.mins[i])
			return 0;	/* apart (or only touching) at the start: Quake's clip */
	n[0] = start[0] - touch->v.origin[0];
	n[1] = start[1] - touch->v.origin[1];
	len = sqrt (n[0]*n[0] + n[1]*n[1]);
	if (len <= 0)
		return 1;
	n[0] /= len;
	n[1] /= len;
	/* toward means more than 1/1024 unit nearer the centre (OpenMW's test has no margin): a slide along the circle
	 * (SV_FlyMove's clipped velocity, which float rounding can leave a hair inward) passes */
	if (n[0]*(end[0] - start[0]) + n[1]*(end[1] - start[1]) > -1.0f/1024)
		return 1;
	memset (trace, 0, sizeof(*trace));
	trace->fraction = 0;
	VectorCopy (start, trace->endpos);
	trace->plane.normal[0] = n[0];
	trace->plane.normal[1] = n[1];
	trace->plane.dist = trace->plane.normal[0]*start[0] + trace->plane.normal[1]*start[1];
	trace->ent = (edict_t *)touch;
	return 2;
}

/* The first other body (SOLID_SLIDEBOX) whose box overlaps ENT's at its origin, or NULL: one pass over the edicts,
 * box tests only. The arrival's check asks it for a few seconds after a door or a teleport (aw_scene.c). */
edict_t *AW_BodyOverlapping (edict_t *ent)
{
	int		i, k;
	edict_t	*e;

	for (i=1 ; i<sv.num_edicts ; i++)
	{
		e = EDICT_NUM(i);
		if (e == ent || e->free || e->v.solid != SOLID_SLIDEBOX)
			continue;
		for (k=0 ; k<3 ; k++)
			if (ent->v.origin[k] + ent->v.mins[k] >= e->v.origin[k] + (k == 2 ? ClipTop (e) : e->v.maxs[k]) ||
				ent->v.origin[k] + (k == 2 ? ClipTop (ent) : ent->v.maxs[k]) <= e->v.origin[k] + e->v.mins[k])
				break;
		if (k == 3)
			return e;
	}
	return NULL;
}

/* SV_TestEntityPosition for Quake's stuck search (sv_phys.c SV_CheckStuck): a body counts as stuck only in the world
 * and its objects, never because other bodies overlap it (OpenMW 0.51 movementsolver.cpp unstuck leaves actor-on-actor
 * contacts out); the walk moves such bodies apart (AW_BodyOverlap). With Quake's test an actor on the player's spot
 * failed the search every frame, for the player and for the actor's own steps: "player is stuck." each time, after
 * up to 164 position tests. aw_body_overlap 0: Quake's test. */
edict_t *SV_TestWorldPosition (edict_t *ent)
{
	trace_t	trace;

	if (!aw_body_overlap.value || ent->v.solid != SOLID_SLIDEBOX)
		return SV_TestEntityPosition (ent);
	trace = SV_Move (ent->v.origin, ent->v.mins, ent->v.maxs, ent->v.origin, MOVE_NOBODIES, ent);
	if (trace.startsolid)
		return sv.edicts;
	return NULL;
}


/*
===============================================================================

LINE TESTING IN HULLS

===============================================================================
*/

// 1/32 epsilon to keep floating point happy
#define	DIST_EPSILON	(0.03125)

/*
==================
SV_RecursiveHullCheck

==================
*/
qboolean SV_RecursiveHullCheck (hull_t *hull, int num, float p1f, float p2f, vec3_t p1, vec3_t p2, trace_t *trace)
{
	dclipnode_t	*node;
	mplane_t	*plane;
	float		t1, t2;
	float		frac;
	int			i;
	vec3_t		mid;
	int			side;
	float		midf;

/* Same-side descent is iterative: long convex-union chains must not
 * consume the Amiga task stack. Splitting segments still recurse. */
aw_hull_next:
// check for empty
	if (num < 0)
	{
		if (num != CONTENTS_SOLID)
		{
			trace->allsolid = false;
			if (num == CONTENTS_EMPTY)
				trace->inopen = true;
			else
				trace->inwater = true;
		}
		else
			trace->startsolid = true;
		return true;		// empty
	}

	if (num < hull->firstclipnode || num > hull->lastclipnode)
		Sys_Error ("SV_RecursiveHullCheck: bad node number");

//
// find the point distances
//
	node = hull->clipnodes + num;
	plane = hull->planes + node->planenum;

	if (plane->type < 3)
	{
		t1 = p1[plane->type] - plane->dist;
		t2 = p2[plane->type] - plane->dist;
	}
	else
	{
		t1 = DotProduct (plane->normal, p1) - plane->dist;
		t2 = DotProduct (plane->normal, p2) - plane->dist;
	}

#if 1
	if (t1 >= 0 && t2 >= 0)
		{num=AW_ClipChild(node->children[0]);goto aw_hull_next;}
	if (t1 < 0 && t2 < 0)
		{num=AW_ClipChild(node->children[1]);goto aw_hull_next;}
#else
	if ( (t1 >= DIST_EPSILON && t2 >= DIST_EPSILON) || (t2 > t1 && t1 >= 0) )
		{num=AW_ClipChild(node->children[0]);goto aw_hull_next;}
	if ( (t1 <= -DIST_EPSILON && t2 <= -DIST_EPSILON) || (t2 < t1 && t1 <= 0) )
		{num=AW_ClipChild(node->children[1]);goto aw_hull_next;}
#endif

/* Traverse exact BSP partitions. Biasing every internal split can report an
 * interior union plane as a surface (or consume the complete surface margin).
 * Apply the contact margin once, on the complete sweep, after the hit. */
    frac = t1/(t1-t2);
	if (frac < 0)
		frac = 0;
	if (frac > 1)
		frac = 1;

	midf = p1f + (p2f - p1f)*frac;
	for (i=0 ; i<3 ; i++)
		mid[i] = p1[i] + frac*(p2[i] - p1[i]);

	side = (t1 < 0);

// move up to the node
	if (!SV_RecursiveHullCheck (hull, AW_ClipChild(node->children[side]), p1f, midf, p1, mid, trace) )
		return false;

#ifdef PARANOID
	if (SV_HullPointContents (sv_hullmodel, mid, AW_ClipChild(node->children[side]))
	== CONTENTS_SOLID)
	{
		Con_Printf ("mid PointInHullSolid\n");
		return false;
	}
#endif

    /* Starting inside an overlapping union must still search its far segment
     * for an exit. The split itself can remain solid in the adjacent subtree. */
	if (trace->allsolid || SV_HullPointContents (hull, AW_ClipChild(node->children[side^1]), mid)
	!= CONTENTS_SOLID)
// go past the node
		return SV_RecursiveHullCheck (hull, AW_ClipChild(node->children[side^1]), midf, p2f, mid, p2, trace);

//==================
// the other side of the node is solid, this is the impact point
//==================
	if (!side)
	{
		VectorCopy (plane->normal, trace->plane.normal);
		trace->plane.dist = plane->dist;
	}
	else
	{
		VectorSubtract (vec3_origin, plane->normal, trace->plane.normal);
		trace->plane.dist = -plane->dist;
	}

	trace->fraction = midf;
	VectorCopy (mid, trace->endpos);

	return false;
}


/*
==================
SV_ClipMoveToEntity

Handles selection or creation of a clipping hull, and offseting (and
eventually rotation) of the end points
==================
*/
trace_t SV_ClipMoveToEntity (edict_t *ent, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end)
{
	trace_t		trace;
	vec3_t		offset;
	vec3_t		start_l, end_l;
	hull_t		*hull;

// fill in a default trace
	memset (&trace, 0, sizeof(trace_t));
	trace.fraction = 1;
	trace.allsolid = true;
	VectorCopy (end, trace.endpos);

// get the clipping hull
	hull = SV_HullForEntity (ent, mins, maxs, offset);

	VectorSubtract (start, offset, start_l);
	VectorSubtract (end, offset, end_l);

/* AmiWind: static architectural brushes have non-zero yaw. */
#if 1
	// rotate start and end into the models frame of reference
	if (ent->v.solid == SOLID_BSP &&
	(ent->v.angles[0] || ent->v.angles[1] || ent->v.angles[2]) )
	{
		vec3_t	a;
		vec3_t	forward, right, up;
		vec3_t	temp;

		AngleVectors (ent->v.angles, forward, right, up);

		VectorCopy (start_l, temp);
		start_l[0] = DotProduct (temp, forward);
		start_l[1] = -DotProduct (temp, right);
		start_l[2] = DotProduct (temp, up);

		VectorCopy (end_l, temp);
		end_l[0] = DotProduct (temp, forward);
		end_l[1] = -DotProduct (temp, right);
		end_l[2] = DotProduct (temp, up);
	}
#endif

// trace a line through the apropriate clipping hull
	SV_RecursiveHullCheck (hull, hull->firstclipnode, 0, 1, start_l, end_l, &trace);
    if(!trace.allsolid && trace.fraction<1) {
        vec3_t delta;
        float speed,margin;
        VectorSubtract(end_l,start_l,delta);
        speed=fabs(DotProduct(delta,trace.plane.normal));
        if(speed>0) {
            margin=DIST_EPSILON/speed;
            trace.fraction-=margin;
            if(trace.fraction<0)trace.fraction=0;
            VectorMA(start_l,trace.fraction,delta,trace.endpos);
        }
    }


/* AmiWind: static architectural brushes have non-zero yaw. */
#if 1
	// rotate endpos back to world frame of reference
	if (ent->v.solid == SOLID_BSP &&
	(ent->v.angles[0] || ent->v.angles[1] || ent->v.angles[2]) )
	{
		vec3_t	a;
		vec3_t	forward, right, up;
		vec3_t	temp;

		if (trace.fraction != 1)
		{
			VectorSubtract (vec3_origin, ent->v.angles, a);
			AngleVectors (a, forward, right, up);

			VectorCopy (trace.endpos, temp);
			trace.endpos[0] = DotProduct (temp, forward);
			trace.endpos[1] = -DotProduct (temp, right);
			trace.endpos[2] = DotProduct (temp, up);

			VectorCopy (trace.plane.normal, temp);
			trace.plane.normal[0] = DotProduct (temp, forward);
			trace.plane.normal[1] = -DotProduct (temp, right);
			trace.plane.normal[2] = DotProduct (temp, up);
		}
	}
#endif

// fix trace up by the offset
	if (trace.fraction != 1)
		VectorAdd (trace.endpos, offset, trace.endpos);

/* A blocked sweep has no usable destination. Some movement paths (step-down
 * via SV_PushEntity) copy endpos even when allsolid, so returning the requested
 * end lets an already-overlapping player sink through the ground. */
    if(trace.allsolid) {trace.fraction=0;VectorCopy(start,trace.endpos);}

// did we clip the move?
	if (trace.fraction < 1 || trace.startsolid  )
		trace.ent = ent;

	return trace;
}

//===========================================================================

/*
====================
SV_ClipToLinks

Mins and maxs enclose the entire area swept by the move
====================
*/
/* An exit from an overlapping solid must not discard a nearer floor hit.
 * Keep startsolid as a flag while retaining the earliest blocking fraction. */
void AW_MergeCollisionTrace(trace_t *best,trace_t *candidate,edict_t *touch) {
    int started=best->startsolid || candidate->startsolid;
    if(candidate->allsolid || candidate->fraction < best->fraction) {
        *best=*candidate;best->ent=touch;
    }
    best->startsolid=started;
}

void SV_ClipToLinks ( areanode_t *node, moveclip_t *clip )
{
	link_t		*l, *next;
	edict_t		*touch;
	trace_t		trace;

// touch linked edicts
	for (l = node->solid_edicts.next ; l != &node->solid_edicts ; l = next)
	{
		next = l->next;
		touch = EDICT_FROM_AREA(l);
		if (touch->v.solid == SOLID_NOT)
			continue;
		if (touch == clip->passedict)
			continue;
		if (touch->v.solid == SOLID_TRIGGER)
			Sys_Error ("Trigger in clipping list");

		if (clip->type == MOVE_NOMONSTERS && touch->v.solid != SOLID_BSP)
			continue;
		if (clip->type == MOVE_NOBODIES && touch->v.solid == SOLID_SLIDEBOX)
			continue;

		if (clip->boxmins[0] > touch->v.absmax[0]
		|| clip->boxmins[1] > touch->v.absmax[1]
		|| clip->boxmins[2] > touch->v.absmax[2]
		|| clip->boxmaxs[0] < touch->v.absmin[0]
		|| clip->boxmaxs[1] < touch->v.absmin[1]
		|| clip->boxmaxs[2] < touch->v.absmin[2] )
			continue;

		if (clip->passedict && clip->passedict->v.size[0] && !touch->v.size[0])
			continue;	// points never interact

	// might intersect, so do an exact clip
		if (clip->trace.allsolid)
			return;
		if (clip->passedict)
		{
            if (PROG_TO_EDICT(touch->v.owner) == clip->passedict)
				continue;	// don't clip against own missiles
			if (PROG_TO_EDICT(clip->passedict->v.owner) == touch)
				continue;	// don't clip against owner
		}

		/* DOOR-ARRIVAL-INSIDE-ACTOR-66: a body the mover already overlaps (AW_BodyOverlap) */
		switch (AW_BodyOverlap (clip->passedict, touch, clip->start, clip->mins, clip->maxs, clip->end, &trace))
		{
		case 1:
			continue;
		case 2:
			AW_MergeCollisionTrace (&clip->trace, &trace, touch);
			continue;
		}

		if ((int)touch->v.flags & FL_MONSTER)
			trace = SV_ClipMoveToEntity (touch, clip->start, clip->mins2, clip->maxs2, clip->end);
		else
			trace = SV_ClipMoveToEntity (touch, clip->start, clip->mins, clip->maxs, clip->end);
        AW_MergeCollisionTrace(&clip->trace,&trace,touch);
	}

// recurse down both sides
	if (node->axis == -1)
		return;

	if ( clip->boxmaxs[node->axis] > node->dist )
		SV_ClipToLinks ( node->children[0], clip );
	if ( clip->boxmins[node->axis] < node->dist )
		SV_ClipToLinks ( node->children[1], clip );
}


/*
==================
SV_MoveBounds
==================
*/
void SV_MoveBounds (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, vec3_t boxmins, vec3_t boxmaxs)
{
#if 0
// debug to test against everything
boxmins[0] = boxmins[1] = boxmins[2] = -9999;
boxmaxs[0] = boxmaxs[1] = boxmaxs[2] = 9999;
#else
	int		i;

	for (i=0 ; i<3 ; i++)
	{
		if (end[i] > start[i])
		{
			boxmins[i] = start[i] + mins[i] - 1;
			boxmaxs[i] = end[i] + maxs[i] + 1;
		}
		else
		{
			boxmins[i] = end[i] + mins[i] - 1;
			boxmaxs[i] = start[i] + maxs[i] + 1;
		}
	}
#endif
}

/*
==================
SV_Move
==================
*/
/* Every collision sweep, counted (dbg companiontest reports its share). */
unsigned long aw_sv_move_calls;

trace_t SV_Move (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, int type, edict_t *passedict)
{
	moveclip_t	clip;
	int			i;

	aw_sv_move_calls++;
	memset ( &clip, 0, sizeof ( moveclip_t ) );

// clip to world
	clip.trace = SV_ClipMoveToEntity ( sv.edicts, start, mins, maxs, end );

	clip.start = start;
	clip.end = end;
	clip.mins = mins;
	clip.maxs = maxs;
	clip.type = type;
	clip.passedict = passedict;

	if (type == MOVE_MISSILE)
	{
		for (i=0 ; i<3 ; i++)
		{
			clip.mins2[i] = -15;
			clip.maxs2[i] = 15;
		}
	}
	else
	{
		VectorCopy (mins, clip.mins2);
		VectorCopy (maxs, clip.maxs2);
	}

// create the bounding box of the entire move
	SV_MoveBounds ( start, clip.mins2, clip.maxs2, end, clip.boxmins, clip.boxmaxs );

// clip to entities
	SV_ClipToLinks ( sv_areanodes, &clip );
    AW_SceneryClip(start,mins,maxs,end,&clip.trace);
	AW_BarrierClip(start,mins,maxs,end,passedict,&clip.trace);

	return clip.trace;
}
