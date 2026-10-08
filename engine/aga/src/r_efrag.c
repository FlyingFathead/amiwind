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
// r_efrag.c

#include "quakedef.h"
#include "r_local.h"

mnode_t	*r_pefragtopnode;


//===========================================================================

/*
===============================================================================

					ENTITY FRAGMENT FUNCTIONS

===============================================================================
*/

efrag_t		**lastlink;

vec3_t		r_emins, r_emaxs;

entity_t	*r_addent;

/* Keep the original BSS pool; dense maps add bounded low-Hunk pages only while
 * linking static entities. Client resets reuse pages until the map Hunk dies. */
typedef struct aw_efrag_page_s {
    struct aw_efrag_page_s *next;
    efrag_t links[AW_EFRAG_PAGE_LINKS];
} aw_efrag_page_t;
static aw_efrag_page_t *aw_efrag_pages;
int aw_efrags_capacity = MAX_EFRAGS;

/* Quake drops an entity silently when cl_visedicts is full (MAX_VISEDICTS).
 * Count every drop (in total and since the frame's list was reset) and say so
 * once per map, so a dense view cannot lose objects unnoticed. */
int aw_visedicts_dropped, aw_visedicts_dropped_frame;
static int aw_visedicts_warned;
void AW_VisedictDropped(void)
{
    aw_visedicts_dropped++;
    aw_visedicts_dropped_frame++;
    if (aw_visedicts_warned) return;
    aw_visedicts_warned = 1;
    Con_Printf("WARNING: visible entity limit (%d) reached; some objects are not drawn.\n", MAX_VISEDICTS);
}

static void R_ResetEfragBlock(efrag_t *links, int count, qboolean reuse)
{
    int i;
    for (i=0; i<count; i++)
        if (links[i].leaf) links[i].leaf->efrags = NULL;
    memset(links, 0, count*sizeof(*links));
    if (!reuse) return;
    for (i=0; i<count-1; i++) links[i].entnext = &links[i+1];
    links[count-1].entnext = cl.free_efrags;
    cl.free_efrags = links;
}

void R_ClearEfrags(qboolean release_pages)
{
    aw_efrag_page_t *page;
    cl.free_efrags = NULL;
    cl.num_statics = 0;
    lastlink = NULL;
    r_addent = NULL;
    r_pefragtopnode = NULL;
    aw_efrags_used = 0;
    aw_visedicts_warned = 0;
    aw_efrags_capacity = MAX_EFRAGS;
    R_ResetEfragBlock(cl_efrags, MAX_EFRAGS, true);
    for (page=aw_efrag_pages; page; page=page->next) {
        R_ResetEfragBlock(page->links, AW_EFRAG_PAGE_LINKS, !release_pages);
        if (!release_pages) aw_efrags_capacity += AW_EFRAG_PAGE_LINKS;
    }
    if (release_pages) aw_efrag_pages = NULL;
    memset(cl_static_entities, 0, sizeof(cl_static_entities));
}

static void R_GrowEfrags(void)
{
    aw_efrag_page_t *page;
    if (aw_efrags_capacity > AW_EFRAG_LIMIT-AW_EFRAG_PAGE_LINKS)
        Host_Error("Static entity leaf-link limit exceeded (%d efrags)", AW_EFRAG_LIMIT);
    page = Hunk_AllocName(sizeof(*page), "efrags");
    page->next = aw_efrag_pages;
    aw_efrag_pages = page;
    R_ResetEfragBlock(page->links, AW_EFRAG_PAGE_LINKS, true);
    aw_efrags_capacity += AW_EFRAG_PAGE_LINKS;
}


/*
================
R_RemoveEfrags

Call when removing an object from the world or moving it to another position
================
*/
void R_RemoveEfrags (entity_t *ent)
{
	efrag_t		*ef, *old, *walk, **prev;

	ef = ent->efrag;

	while (ef)
	{
		prev = &ef->leaf->efrags;
		while (1)
		{
			walk = *prev;
			if (!walk)
				break;
			if (walk == ef)
			{	// remove this fragment
				*prev = ef->leafnext;
				break;
			}
			else
				prev = &walk->leafnext;
		}

		old = ef;
		ef = ef->entnext;

	// put it on the free list
		old->entnext = cl.free_efrags;
		cl.free_efrags = old;
		aw_efrags_used--;
	}

	ent->efrag = NULL;
}

/*
===================
R_SplitEntityOnNode
===================
*/
void R_SplitEntityOnNode (mnode_t *node)
{
	efrag_t		*ef;
	mplane_t	*splitplane;
	mleaf_t		*leaf;
	int			sides;

	if (node->contents == CONTENTS_SOLID)
	{
		return;
	}

// add an efrag if the node is a leaf

	if ( node->contents < 0)
	{
		if (!r_pefragtopnode)
			r_pefragtopnode = node;

		leaf = (mleaf_t *)node;

// grab an efrag off the free list
		ef = cl.free_efrags;
		if (!ef)
		{
            R_GrowEfrags();
            ef = cl.free_efrags;
		}
		cl.free_efrags = cl.free_efrags->entnext;
		aw_efrags_used++;
		if(aw_efrags_used>aw_efrags_peak)aw_efrags_peak=aw_efrags_used;

		ef->entity = r_addent;

// add the entity link
		*lastlink = ef;
		lastlink = &ef->entnext;
		ef->entnext = NULL;

// set the leaf links
		ef->leaf = leaf;
		ef->leafnext = leaf->efrags;
		leaf->efrags = ef;

		return;
	}

// NODE_MIXED

	splitplane = node->plane;
	sides = BOX_ON_PLANE_SIDE(r_emins, r_emaxs, splitplane);

	if (sides == 3)
	{
	// split on this plane
	// if this is the first splitter of this bmodel, remember it
		if (!r_pefragtopnode)
			r_pefragtopnode = node;
	}

// recurse down the contacted sides
	if (sides & 1)
		R_SplitEntityOnNode (node->children[0]);

	if (sides & 2)
		R_SplitEntityOnNode (node->children[1]);
}


/*
===================
R_SplitEntityOnNode2
===================
*/
void R_SplitEntityOnNode2 (mnode_t *node)
{
	mplane_t	*splitplane;
	int			sides;

	if (node->visframe != r_visframecount)
		return;
	/* Use the same far plane as world traversal and clipped brush faces. */
	if (!AW_NodeVisible(node->minmaxs))
		return;

	if (node->contents < 0)
	{
		if (node->contents != CONTENTS_SOLID)
			r_pefragtopnode = node; // we've reached a non-solid leaf, so it's
									//  visible and not BSP clipped
		return;
	}

	splitplane = node->plane;
	sides = BOX_ON_PLANE_SIDE(r_emins, r_emaxs, splitplane);

	if (sides == 3)
	{
	// remember first splitter
		r_pefragtopnode = node;
		return;
	}

// not split yet; recurse down the contacted side
	if (sides & 1)
		R_SplitEntityOnNode2 (node->children[0]);
	else
		R_SplitEntityOnNode2 (node->children[1]);
}


/*
===========
R_AddEfrags
===========
*/
void R_AddEfrags (entity_t *ent)
{
	model_t		*entmodel;
	int			i;

	if (!ent->model)
		return;

	if (ent == cl_entities)
		return;		// never add the world

	r_addent = ent;

	ent->efrag = NULL;
	lastlink = &ent->efrag;
	r_pefragtopnode = NULL;

	entmodel = ent->model;

	for (i=0 ; i<3 ; i++)
	{
        float scale = R_SpriteEntityScale(ent);
        r_emins[i] = ent->origin[i] + entmodel->mins[i] * scale;
        r_emaxs[i] = ent->origin[i] + entmodel->maxs[i] * scale;
	}

	R_SplitEntityOnNode (cl.worldmodel->nodes);

	ent->topnode = r_pefragtopnode;
}


/*
================
R_StoreEfrags

// FIXME: a lot of this goes away with edge-based
================
*/
void R_StoreEfrags (efrag_t **ppefrag)
{
	entity_t	*pent;
	model_t		*clmodel;
	efrag_t		*pefrag;


	while ((pefrag = *ppefrag) != NULL)
	{
		pent = pefrag->entity;
		clmodel = pent->model;

		switch (clmodel->type)
		{
		case mod_alias:
		case mod_brush:
		case mod_sprite:
			pent = pefrag->entity;

			if (pent->visframe != r_framecount)
			{
				if (cl_numvisedicts < MAX_VISEDICTS)
					cl_visedicts[cl_numvisedicts++] = pent;
				else
					AW_VisedictDropped ();

			// mark that we've recorded (or counted) this entity for this frame
				pent->visframe = r_framecount;
			}

			ppefrag = &pefrag->leafnext;
			break;

		default:
			Sys_Error ("R_StoreEfrags: Bad entity type %d\n", clmodel->type);
		}
	}
}
