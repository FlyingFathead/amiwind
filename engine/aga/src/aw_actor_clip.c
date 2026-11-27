/* SPDX-License-Identifier: GPL-2.0-or-later
 * SOL-SEA-INVISIBLE-BLOCKER-68, ACTOR-CLIP-ABOVE-DRAWN-BODY-69 (v0.0.69): a creature collides only as high as its
 * drawn body.
 *
 * Every actor stood in the same person-sized box (world.qc aw_npc_floor: -7.32 -7.12 0 .. 7.32 7.12 33.25, the
 * original's NPC box), creatures included. A creature lower than a person therefore had a column of collision over its
 * back where nothing is drawn: a horker (bm_horker_large, drawn 11.34 units tall in its idle pose) rolled by the
 * levelled list bm_ex_horker_h20 swims at its placed depth in Solstheim's sea, wholly under the water surface (the
 * one at cell -19,17: origin 22.2 units below the surface, drawn top 10.86 units below it), while its box reached
 * 11.05 units ABOVE the surface: a player walking on the water from Khuul stopped against open sea (dbg blockers: the
 * horker's model progs/c_9d8917efa100_k.mdl). The same column stood over every rat, mudcrab or scrib on land.
 *
 * The original gives a creature the box of its own model (OpenMW 0.53 apps/openmw/mwphysics/actor.cpp 40-63, the
 * model's "Bounding Box" node: components/nifbullet/bulletnifloader.cpp 85-108), never a person's. Here the rule is
 * the one that can be checked against what is drawn: once its spawn has set the person box (pr_cmds.c SetMinMaxSize
 * asks AW_ActorClipSet after every new box, so world.qc and the CHIM world's stage key stay as they are), a creature
 * collides up to the top of its drawn idle pose (the skeletal actor's rest frame, tools/skeletal_actor.py; every stored
 * frame of any
 * other model), times its drawn scale (aw_scale), never higher than the box it was given. Only collision changes
 * (world.c SV_HullForEntity, AW_BodyOverlap, AW_BodyOverlapping read the top through aw_actor_clip_top): the box
 * itself, the hull a creature walks the world with, its eye height, its combat reach and its spell shells are as
 * before. A step never lands on a body (sv_phys.c SV_WalkMove; OpenMW stepper.cpp canStepDown), so a low creature is
 * walked around, not climbed.
 *
 * Which actors: a creature by its ambient slot (aw_scene.c aw_actor_creature), else an outdoor creature of the
 * creature library by its model name (progs/c_*); people keep the person box. Cost: 4.8 KB for the per-edict tops,
 * 4 KB for the per-model tops (600 edicts, 512 models, a pointer and a float each); one pass over a model's rest vertices the first time a scene spawns that model, one
 * table read per collision test against a body. */
#include "quakedef.h"
#include "aw_actor_clip.h"

cvar_t aw_actor_clip = {"aw_actor_clip", "1"};
/* aw_scene.c (FOCUS-NPC-OVERRIDES-ITEM-62): 1 a creature, 0 a person, -1 no slot; NULL in tests */
extern int (*aw_actor_creature)(edict_t *e);

static model_t *top_model[MAX_MODELS];    /* the model each top_value was measured from (a new map: another model) */
static float top_value[MAX_MODELS];
static model_t *clip_model[MAX_EDICTS];   /* the model of the edict when its top was set (none: not lowered) */
static float clip_top[MAX_EDICTS];

float AW_ActorClipTopRule(float box_top, float drawn, float scale)
{
	float top;
	if (!(drawn > 0) || !(scale > 0) || !(box_top > 0))
		return box_top;
	top = drawn * scale;
	if (top < AW_ACTOR_CLIP_MIN)
		top = AW_ACTOR_CLIP_MIN;
	return top < box_top ? top : box_top;
}

float AW_ActorModelTop(model_t *m)
{
	aliashdr_t *h;
	mdl_t *md;
	trivertx_t *v;
	float top = 0, z;
	int f, i, any = 0;
	if (!m || m->type != mod_alias)
		return 0;
	h = (aliashdr_t *)Mod_Extradata (m);
	if (!h)
		return 0;
	md = (mdl_t *)((byte *)h + h->model);
	for (f = 0 ; f < md->numframes ; f++)
	{
		if (h->frames[f].type != ALIAS_SINGLE)
			continue;
		v = (trivertx_t *)((byte *)h + h->frames[f].frame);
		for (i = 0 ; i < md->numverts ; i++)
		{
			z = v[i].v[2] * md->scale[2] + md->scale_origin[2];
			if (!any || z > top)
				top = z;
			any = 1;
		}
		if (h->aw_skel)
			break;		/* a skeletal actor stores one frame: the rest pose it stands in */
	}
	return any && top > 0 ? top : 0;
}

static int is_creature(edict_t *e)
{
	int c = aw_actor_creature ? aw_actor_creature (e) : -1;
	if (c >= 0)
		return c;
	return e->v.model && !strncmp (pr_strings + e->v.model, "progs/c_", 8);
}

void AW_ActorClipSet(edict_t *e)
{
	int n, mi;
	model_t *m;
	eval_t *s;
	float scale = 1, top;
	if (!e || e->free)
		return;
	n = NUM_FOR_EDICT (e);
	if (n <= 0 || n >= MAX_EDICTS)
		return;
	clip_model[n] = NULL;
	mi = (int)e->v.modelindex;
	if (mi <= 0 || mi >= MAX_MODELS || !(m = sv.models[mi]) || !is_creature (e))
		return;
	if (top_model[mi] != m)
	{
		top_model[mi] = m;
		top_value[mi] = AW_ActorModelTop (m);
	}
	s = GetEdictFieldValue (e, "aw_scale");
	if (s && s->_float > 0)
		scale = s->_float;
	top = AW_ActorClipTopRule (e->v.maxs[2], top_value[mi], scale);
	if (top < e->v.maxs[2])
	{
		clip_model[n] = m;
		clip_top[n] = top;
	}
}

float AW_ActorClipTop(const edict_t *e)
{
	int n, mi;
	if (!aw_actor_clip.value)
		return e->v.maxs[2];
	n = NUM_FOR_EDICT ((edict_t *)e);
	mi = (int)e->v.modelindex;
	if (n > 0 && n < MAX_EDICTS && clip_model[n] && mi > 0 && mi < MAX_MODELS &&
		clip_model[n] == sv.models[mi] && clip_top[n] < e->v.maxs[2])
		return clip_top[n];
	return e->v.maxs[2];
}

/* dbg actorclip [on/off; no argument toggles] is the setting itself (config/debug-commands.txt routes onto it); what a
 * move hits is shown by dbg blockers. */
void AW_ActorClipInit(void)
{
	Cvar_RegisterVariable (&aw_actor_clip);
	aw_actor_clip_top = AW_ActorClipTop;
}
