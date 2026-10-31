/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Shared animation tables (engine/aga/src/aw_skel.c): reads a table the builder wrote (tools/skeletal_actor.py
 * write_table), poses it at the given frame positions and transforms the given bone-space points, printing one
 * line per point for tests/test_skel_native.py to compare with the builder's own pose. Also the refusals.
 * Usage: aga_skel_test TABLE POINTS (lines: frame bone x y z) */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_skel.h"

static unsigned char *read_file (const char *path, long *size)
{
	FILE *f = fopen (path, "rb");
	unsigned char *data;
	assert (f);
	fseek (f, 0, SEEK_END);
	*size = ftell (f);
	fseek (f, 0, SEEK_SET);
	data = malloc (*size + 1);
	assert (data && fread (data, 1, *size, f) == (size_t)*size);
	fclose (f);
	return data;
}

/* aga_skel_test verts TABLE VERTS N FRAME RESTSCALE OX OY OZ SX SY SZ: the posed byte vertices, one line each. */
static int verts_mode (char **argv)
{
	long size, vsize;
	unsigned char *data = read_file (argv[2], &size), *verts = read_file (argv[3], &vsize), *normals, *out;
	int n = atoi (argv[4]), v;
	float frame = (float)atof (argv[5]), rest_scale = (float)atof (argv[6]), origin[3], scale[3];
	aw_skel_table_t t;
	static float world[AW_SKEL_MAX_BONES][3][4];
	for (v=0 ; v<3 ; v++)
	{
		origin[v] = (float)atof (argv[7+v]);
		scale[v] = (float)atof (argv[10+v]);
	}
	assert (AW_SkelParse (data, size, &t) && vsize == (long)n * AW_SKEL_VERT_BYTES);
	normals = calloc (n, 1);
	out = malloc (4 * n);
	for (v=0 ; v<n ; v++)
		normals[v] = (unsigned char)(v % 162);
	AW_SkelPose (&t, frame, world);
	AW_SkelPoseVerts (verts, normals, 1, n, rest_scale, world, origin, scale, out);
	for (v=0 ; v<n ; v++)
	{
		assert (out[4*v+3] == normals[v]);
		printf ("%d %d %d\n", out[4*v], out[4*v+1], out[4*v+2]);
	}
	return 0;
}

/* aga_skel_test block BLOCK NV: the parsed block's fields, and the refusals of a damaged copy. */
static int block_mode (char **argv)
{
	long size;
	unsigned char *b = read_file (argv[2], &size), *bad;
	int nv = atoi (argv[3]);
	aw_skel_block_t k;
	assert (AW_SkelBlockParse (b, size, nv, &k));
	printf ("block %s %.6g %d %d %.6g %.6g %.6g %.6g %.6g %.6g\n", k.table, k.rest_scale, k.verts, k.frames,
		k.pose_origin[0], k.pose_origin[1], k.pose_origin[2], k.pose_step[0], k.pose_step[1], k.pose_step[2]);
	assert (!AW_SkelBlockParse (b, size, nv + 1, &k));		/* another vertex count */
	assert (!AW_SkelBlockParse (b, size - 1, nv, &k));		/* short */
	bad = malloc (size);
	memcpy (bad, b, size); bad[AW_SKEL_BLOCK_HEAD] = AW_SKEL_MAX_BONES;	/* a bone past any table */
	assert (!AW_SkelBlockParse (bad, size, nv, &k));
	memcpy (bad, b, size); bad[64] = bad[65] = bad[66] = bad[67] = 0;		/* a zero pose step */
	assert (!AW_SkelBlockParse (bad, size, nv, &k));
	assert (AW_SkelBlockParse (b, size, nv, &k) && AW_SkelBlockFits (&k, 3) && !AW_SkelBlockFits (&k, 2));
	return 0;
}

/* aga_skel_test tag M00 M01 ... M23 SX SY SZ: AW_SkelBoneTag of a column-form 3 x 4 bone matrix. */
static int tag_mode (char **argv)
{
	float bone[3][4], scale[3], tag[6];
	int i;
	for (i=0 ; i<12 ; i++)
		bone[i/4][i%4] = (float)atof (argv[2+i]);
	for (i=0 ; i<3 ; i++)
		scale[i] = (float)atof (argv[14+i]);
	AW_SkelBoneTag ((const float (*)[4])bone, scale, tag);
	printf ("%.6f %.6f %.6f %.6f %.6f %.6f\n", tag[0], tag[1], tag[2], tag[3], tag[4], tag[5]);
	return 0;
}

/* aga_skel_test layer TABLE FRAME LAYER ROOT SHIELD WEAPON: AW_SkelLeftArmRoot (SHIELD, WEAPON), then every bone's
 * world origin posed by AW_SkelPoseLayer (ROOT -1: AW_SkelPose), one line each (SKEL-ITEM-TAGS-52). */
static int layer_mode (char **argv)
{
	long size;
	unsigned char *data = read_file (argv[2], &size);
	aw_skel_table_t t;
	static float world[AW_SKEL_MAX_BONES][3][4];
	int b, root = atoi (argv[5]);
	assert (AW_SkelParse (data, size, &t));
	printf ("root %d\n", AW_SkelLeftArmRoot (&t, atoi (argv[6]), atoi (argv[7])));
	if (root < 0)
		AW_SkelPose (&t, (float)atof (argv[3]), world);
	else
		AW_SkelPoseLayer (&t, (float)atof (argv[3]), (float)atof (argv[4]), root, world);
	for (b=0 ; b<t.bones ; b++)
		printf ("%.6f %.6f %.6f\n", world[b][0][3], world[b][1][3], world[b][2][3]);
	return 0;
}

/* aga_skel_test layers TABLE FRAME LAYER0 ROOT0 LAYER1 ROOT1 SHIELD WEAPON: AW_SkelRightArmRoot (SHIELD, WEAPON), then
 * every bone's world origin posed by AW_SkelPoseLayers with both layers (a guard's torch arm and his storm arm,
 * ACTOR-STORM-POSE-51), one line each. */
static int layers_mode (char **argv)
{
	long size;
	unsigned char *data = read_file (argv[2], &size);
	aw_skel_table_t t;
	static float world[AW_SKEL_MAX_BONES][3][4];
	float frames[2];
	int b, roots[2];
	assert (AW_SkelParse (data, size, &t));
	frames[0] = (float)atof (argv[4]); roots[0] = atoi (argv[5]);
	frames[1] = (float)atof (argv[6]); roots[1] = atoi (argv[7]);
	printf ("root %d\n", AW_SkelRightArmRoot (&t, atoi (argv[8]), atoi (argv[9])));
	AW_SkelPoseLayers (&t, (float)atof (argv[3]), 2, frames, roots, world);
	for (b=0 ; b<t.bones ; b++)
		printf ("%.6f %.6f %.6f\n", world[b][0][3], world[b][1][3], world[b][2][3]);
	return 0;
}

/* aga_skel_test append BASE OWN: an appended table (version 3, CREATURE-APPENDED-TABLE-54) linked to its base: the own
 * groups first, then the base's (frames after the own ones); a pose past the own frames is the base's pose, one
 * within them the own table's; the base's name in the file; refusals (other parents, a base that is itself
 * appended, a version 2 table). Prints "append GROUPS FRAMES OWN_GROUPS OWN_FRAMES BASE_NAME". */
static int append_mode (char **argv)
{
	long bs, os;
	unsigned char *bd = read_file (argv[2], &bs), *od = read_file (argv[3], &os);
	aw_skel_table_t base, own, alone, bad;
	aw_skel_group_t g, h;
	static float w1[AW_SKEL_MAX_BONES][3][4], w2[AW_SKEL_MAX_BONES][3][4];
	int i, b, k;
	assert (AW_SkelParse (bd, bs, &base) && !base.base_name[0]);
	assert (AW_SkelParse (od, os, &own) && own.base_name[0] && !own.more);
	alone = own;
	assert (!AW_SkelAppend (&base, &own));				/* a version 2 table appends nothing */
	bad = own;
	bad.parent[bad.bones - 1] = (short)(bad.parent[bad.bones - 1] == 0 ? -1 : 0);
	assert (!AW_SkelAppend (&bad, &base));				/* other parents */
	assert (AW_SkelAppend (&own, &base));
	bad = alone;
	assert (!AW_SkelAppend (&bad, &own));				/* a base that is itself appended */
	assert (own.groups == alone.groups + base.groups && own.frames == alone.frames + base.frames);
	printf ("append %d %d %d %d %s\n", own.groups, own.frames, own.own_groups, own.own_frames, own.base_name);
	for (i=0 ; i<base.groups ; i++)
	{
		AW_SkelGroupAt (&base, i, &g);
		k = AW_SkelGroup (&own, g.name);
		AW_SkelGroupAt (&own, k, &h);
		if (k >= own.own_groups)
		{
			/* a base group the creature does not have: the base's frames, after the own ones */
			assert (h.first == g.first + (unsigned)own.own_frames && h.last == g.last + (unsigned)own.own_frames);
			assert (AW_SkelKeyFrame (&own, k, "stop") == (AW_SkelKeyFrame (&base, i, "stop") < 0 ? -1 :
				AW_SkelKeyFrame (&base, i, "stop") + own.own_frames));
			AW_SkelPose (&own, (float)h.first + 0.5f, w1);
			AW_SkelPose (&base, (float)g.first + 0.5f, w2);
		}
		else
		{
			/* the creature's own group of that name wins */
			assert (k < alone.groups);
			AW_SkelPose (&own, (float)h.first, w1);
			AW_SkelPose (&alone, (float)h.first, w2);
		}
		for (b=0 ; b<own.bones ; b++)
			for (k=0 ; k<12 ; k++)
				assert (w1[b][k/4][k%4] == w2[b][k/4][k%4]);
	}
	return 0;
}

/* a paged table's frames (WALK-CYCLES-57): the rows after the index of the whole file, frame clamped as the loader */
static const unsigned char *paged_rows;
static const unsigned char *test_row (const aw_skel_table_t *t, int frame)
{
	assert (frame >= 0 && frame < t->own_frames);
	return paged_rows + (long)frame * t->row;
}

int main (int argc, char **argv)
{
	if (argc == 4 && !strcmp (argv[1], "append"))
		return append_mode (argv);
	if (argc == 8 && !strcmp (argv[1], "layer"))
		return layer_mode (argv);
	if (argc == 10 && !strcmp (argv[1], "layers"))
		return layers_mode (argv);
	if (argc == 17 && !strcmp (argv[1], "tag"))
		return tag_mode (argv);
	if (argc == 13 && !strcmp (argv[1], "verts"))
		return verts_mode (argv);
	if (argc == 4 && !strcmp (argv[1], "block"))
		return block_mode (argv);
	long size;
	unsigned char *data, *bad;
	aw_skel_table_t t, paged;
	aw_skel_group_t g;
	static float world[AW_SKEL_MAX_BONES][3][4];
	float frame, in[3], out[3];
	int bone;
	FILE *points;
	assert (argc == 3);
	data = read_file (argv[1], &size);
	assert (AW_SkelParse (data, size, &t));
	/* refusals: short, wrong magic, a parent after its child */
	assert (!AW_SkelParse (data, size - 1, &t));
	bad = malloc (size);
	memcpy (bad, data, size); bad[0] = 'X';
	assert (!AW_SkelParse (bad, size, &t));
	memcpy (bad, data, size); bad[AW_SKEL_HEADER] = 0; bad[AW_SKEL_HEADER+1] = 1;	/* bone 0's parent 1 */
	assert (!AW_SkelParse (bad, size, &t));
	assert (AW_SkelParse (data, size, &t));
	printf ("table bones %d frames %d groups %d\n", t.bones, t.frames, t.groups);
	assert (AW_SkelGroup (&t, "WALKFORWARD") >= 0 && AW_SkelGroup (&t, "nosuchgroup") == -1);
	{
		/* a view (SKEL-TABLE-SHARED-FEMALE-52) gives prefix + name first, else the table's group: with the prefix
		 * "wal" the view's "kforward" is the table's walkforward, its idle the table's idle */
		aw_skel_table_t v = t;
		assert (!t.prefix[0]);
		strcpy (v.prefix, "wal");
		assert (AW_SkelGroup (&t, "kforward") == -1);
		assert (AW_SkelGroup (&v, "KFORWARD") == AW_SkelGroup (&t, "walkforward"));
		assert (AW_SkelGroup (&v, "idle") == AW_SkelGroup (&t, "idle"));
		/* several prefixes in order (DANCER-OWN-ANIM-IGNORED-53: "d:f:"): the first that names a group wins,
		 * then the next, then the table's own */
		strcpy (v.prefix, "x:wal");
		assert (AW_SkelGroup (&v, "kforward") == AW_SkelGroup (&t, "walkforward"));
		assert (AW_SkelGroup (&v, "idle") == AW_SkelGroup (&t, "idle"));
		strcpy (v.prefix, "wal:x:");
		assert (AW_SkelGroup (&v, "kforward") == -1);
	}
	AW_SkelGroupAt (&t, AW_SkelGroup (&t, "walkforward"), &g);
	printf ("group %s %u %u\n", g.name, g.first, g.last);
	/* text keys: a phase of a group by name, any case; another group's key or an unknown one is -1 */
	printf ("key walkforward stop %d idle stop %d none %d keys %d\n",
		AW_SkelKeyFrame (&t, AW_SkelGroup (&t, "walkforward"), "STOP"),
		AW_SkelKeyFrame (&t, AW_SkelGroup (&t, "idle"), "stop"),
		AW_SkelKeyFrame (&t, AW_SkelGroup (&t, "walkforward"), "chop hit"), t.keys_count);
	{
		/* WALK-CYCLES-57: the index alone, its frames given by row_of, poses exactly as the table held whole */
		long index = AW_SkelIndexBytes (data, size);
		assert (index > 0 && index < size);
		assert (AW_SkelParseIndex (data, index, size, &paged) && !paged.keys && paged.frames == t.frames);
		assert (!AW_SkelParseIndex (data, index, size - 1, &paged));
		assert (!AW_SkelParseIndex (data, index - 1, size, &paged));
		assert (AW_SkelParseIndex (data, index, size, &paged));
		paged_rows = data + index;
		paged.row_of = test_row;
	}
	points = fopen (argv[2], "r");
	assert (points);
	while (fscanf (points, "%f %d %f %f %f", &frame, &bone, &in[0], &in[1], &in[2]) == 5)
	{
		static float paged_world[AW_SKEL_MAX_BONES][3][4];
		assert (bone >= 0 && bone < t.bones);
		AW_SkelPose (&paged, frame, paged_world);
		AW_SkelPose (&t, frame, world);
		assert (!memcmp (paged_world, world, sizeof(world[0]) * t.bones));
		AW_SkelTransform (world[bone], in, out);
		printf ("%.6f %.6f %.6f\n", out[0], out[1], out[2]);
	}
	fclose (points);
	puts ("skel ok");
	return 0;
}
