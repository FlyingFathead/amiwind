/* aw_skel.c: shared animation tables (aw_skel.h, docs/MODULAR_NPCS.md "Runtime method C"). */
#include <math.h>
#include <string.h>
#include "aw_skel.h"

static unsigned U16 (const unsigned char *p) {return (unsigned)p[0] << 8 | p[1];}
static unsigned long U32 (const unsigned char *p)
{
	return (unsigned long)p[0] << 24 | (unsigned long)p[1] << 16 | (unsigned long)p[2] << 8 | p[3];
}
static int S16 (const unsigned char *p) {int v = (int)U16 (p); return v >= 32768 ? v - 65536 : v;}
/* A vertex's big-endian i16 (16-byte vertices, so always at an even address): one load on the 68k, the byte form
 * elsewhere. */
#if defined(__m68k__)
#define SKEL_I16(p)	(*(const short *)(const void *)(p))
#else
#define SKEL_I16(p)	((short)(((p)[0] << 8) | (p)[1]))
#endif
static float F32 (const unsigned char *p)
{
	union {unsigned long u; float f;} v;
	v.u = U32 (p);
	return v.f;
}

/* The parse's checks, each its own function, never inlined: one function holding all of them crashed the m68k
 * compiler at -O1 and -O2 (internal compiler error in patch_jump_insn, gates 3942 and 3943; BUILD-M68K-ICE-SKEL-
 * PARSE-52). */
#if defined(__GNUC__)
#define AW_SKEL_APART	__attribute__((noinline))
#else
#define AW_SKEL_APART
#endif
static AW_SKEL_APART int bones_ok (const unsigned char *data, int bones_bytes, aw_skel_table_t *out)
{
	int i;
	for (i=0 ; i<out->bones ; i++)
	{
		out->parent[i] = (short)S16 (data + AW_SKEL_HEADER + 2*i);
		if (out->parent[i] < -1 || out->parent[i] >= i)
			return 0;			/* every parent before its child */
		out->kind[i] = data[AW_SKEL_HEADER + bones_bytes + i];
		if (out->kind[i] > AW_SKEL_MOVES)
			return 0;
		out->offset[i] = out->kind[i] == AW_SKEL_STILL ? -1 : (short)out->row;
		out->row += out->kind[i] == AW_SKEL_MOVES ? 12 : out->kind[i] == AW_SKEL_TURNS ? 6 : 0;
	}
	return 1;
}

static AW_SKEL_APART int groups_ok (const aw_skel_table_t *t)
{
	int i;
	for (i=0 ; i<t->groups ; i++)
	{
		const unsigned char *g = t->group_data + i*AW_SKEL_GROUP_BYTES;
		unsigned long first = U32 (g + AW_SKEL_NAME), last = U32 (g + AW_SKEL_NAME + 4);
		if (first > last || last >= (unsigned long)t->frames || g[AW_SKEL_NAME-1])
			return 0;
	}
	return 1;
}

static AW_SKEL_APART int keys_ok (const aw_skel_table_t *t)
{
	int i;
	for (i=0 ; i<t->keys_count ; i++)
	{
		const unsigned char *k = t->key_data + i*AW_SKEL_KEY_BYTES;
		unsigned group = U16 (k + AW_SKEL_KEY_TEXT);
		if (k[AW_SKEL_KEY_TEXT-1] || U32 (k + AW_SKEL_KEY_TEXT + 4) >= (unsigned long)t->frames ||
			(group != AW_SKEL_NO_GROUP && group >= (unsigned)t->groups))
			return 0;
	}
	return 1;
}

int AW_SkelParse (const unsigned char *data, long size, aw_skel_table_t *out)
{
	long need;
	int bones_bytes, kinds_bytes;
	if (!data || size < AW_SKEL_HEADER || memcmp (data, AW_SKEL_MAGIC, 4) || U16 (data+4) != AW_SKEL_VERSION)
		return 0;
	memset (out, 0, sizeof(*out));
	out->bones = (int)U16 (data+6);
	out->frames = (int)U32 (data+8);
	out->rate = F32 (data+12);
	out->scale = F32 (data+16);
	out->groups = (int)U16 (data+20);
	out->keys_count = (int)U16 (data+22);
	if (out->bones < 1 || out->bones > AW_SKEL_MAX_BONES || out->frames < 1 || out->frames > 1000000 ||
		!(out->rate > 0) || !(out->scale > 0) || out->rate > 1000 || out->scale > 1e6)
		return 0;
	bones_bytes = (out->bones * 2 + 3) & ~3;
	kinds_bytes = (out->bones + 3) & ~3;
	need = AW_SKEL_HEADER + bones_bytes + kinds_bytes + (long)out->groups * AW_SKEL_GROUP_BYTES +
		(long)out->keys_count * AW_SKEL_KEY_BYTES;
	if (size < need || !bones_ok (data, bones_bytes, out))
		return 0;
	need += (long)out->bones * AW_SKEL_BASE_BYTES + (long)out->frames * out->row;
	if (need != size)
		return 0;
	out->group_data = data + AW_SKEL_HEADER + bones_bytes + kinds_bytes;
	out->key_data = out->group_data + (long)out->groups * AW_SKEL_GROUP_BYTES;
	if (!groups_ok (out) || !keys_ok (out))
		return 0;
	out->base = out->key_data + (long)out->keys_count * AW_SKEL_KEY_BYTES;
	out->keys = out->base + (long)out->bones * AW_SKEL_BASE_BYTES;
	return 1;
}

int AW_SkelBlockParse (const unsigned char *b, long size, int nv, aw_skel_block_t *out)
{
	int i;
	if (!AW_SkelBlockHead (b, size, nv, out))
		return 0;
	for (i=0 ; i<nv ; i++)
	{
		const unsigned char *v = out->data + i*AW_SKEL_VERT_BYTES;
		if (v[0] >= AW_SKEL_MAX_BONES || (v[1] != AW_SKEL_NONE && v[1] >= AW_SKEL_MAX_BONES))
			return 0;
	}
	return 1;
}

int AW_SkelBlockHead (const unsigned char *b, long size, int nv, aw_skel_block_t *out)
{
	if (!b || nv < 1 || size != AW_SKEL_BLOCK_HEAD + (long)nv * AW_SKEL_VERT_BYTES || memcmp (b, AW_SKEL_BLOCK_MAGIC, 4) ||
		U16 (b+4) != AW_SKEL_BLOCK_VERSION || (long)U32 (b+44) != nv)
		return 0;
	memset (out, 0, sizeof(*out));
	memcpy (out->table, b + 8, AW_SKEL_TABLE_NAME);
	if (out->table[AW_SKEL_TABLE_NAME-1] || !out->table[0])
		return 0;
	out->rest_scale = F32 (b + 40);
	out->verts = nv;
	out->frames = (int)U32 (b + 48);
	if (!(out->rest_scale > 0) || out->rest_scale > 1e3f || out->frames < 1)
		return 0;
	{
		int k;
		for (k=0 ; k<3 ; k++)
		{
			out->pose_origin[k] = F32 (b + 52 + 4*k);
			out->pose_step[k] = F32 (b + 64 + 4*k);
			if (!(out->pose_step[k] > 0) || out->pose_step[k] > 1e6f || !(out->pose_origin[k] > -1e7f && out->pose_origin[k] < 1e7f))
				return 0;
		}
	}
	out->data = b + AW_SKEL_BLOCK_HEAD;
	return 1;
}

int AW_SkelBlockFits (const aw_skel_block_t *block, int bones)
{
	int i;
	for (i=0 ; i<block->verts ; i++)
	{
		const unsigned char *v = block->data + i*AW_SKEL_VERT_BYTES;
		if (v[0] >= bones || (v[1] != AW_SKEL_NONE && v[1] >= bones))
			return 0;
	}
	return 1;
}

static int same_name (const char *a, const char *b)
{
	for ( ; *a && *b ; a++, b++)
	{
		int x = *a >= 'A' && *a <= 'Z' ? *a + 32 : *a, y = *b >= 'A' && *b <= 'Z' ? *b + 32 : *b;
		if (x != y)
			return 0;
	}
	return !*a && !*b;
}

int AW_SkelGroup (const aw_skel_table_t *t, const char *name)
{
	int i;
	if (t->prefix[0])
	{
		char own[AW_SKEL_NAME];
		int n = (int)strlen (t->prefix);
		if (n + (int)strlen (name) < AW_SKEL_NAME)
		{
			memcpy (own, t->prefix, n);
			strcpy (own + n, name);
			for (i=0 ; i<t->groups ; i++)
				if (same_name ((const char *)(t->group_data + i*AW_SKEL_GROUP_BYTES), own))
					return i;
		}
	}
	for (i=0 ; i<t->groups ; i++)
		if (same_name ((const char *)(t->group_data + i*AW_SKEL_GROUP_BYTES), name))
			return i;
	return -1;
}

void AW_SkelGroupAt (const aw_skel_table_t *t, int index, aw_skel_group_t *out)
{
	const unsigned char *g = t->group_data + index*AW_SKEL_GROUP_BYTES;
	memcpy (out->name, g, AW_SKEL_NAME);
	out->first = (unsigned)U32 (g + AW_SKEL_NAME);
	out->last = (unsigned)U32 (g + AW_SKEL_NAME + 4);
}

int AW_SkelKeyFrame (const aw_skel_table_t *t, int group, const char *text)
{
	int i;
	for (i=0 ; i<t->keys_count ; i++)
	{
		const unsigned char *k = t->key_data + i*AW_SKEL_KEY_BYTES;
		if ((int)U16 (k + AW_SKEL_KEY_TEXT) == group && same_name ((const char *)k, text))
			return (int)U32 (k + AW_SKEL_KEY_TEXT + 4);
	}
	return -1;
}

void AW_SkelConcat (const float a[3][4], const float b[3][4], float c[3][4])
{
	int i, j;
	for (i=0 ; i<3 ; i++)
	{
		for (j=0 ; j<3 ; j++)
			c[i][j] = a[i][0]*b[0][j] + a[i][1]*b[1][j] + a[i][2]*b[2][j];
		c[i][3] = a[i][0]*b[0][3] + a[i][1]*b[1][3] + a[i][2]*b[2][3] + a[i][3];
	}
}

/* atan2 in degrees without the library's: the 68881 library compiles atan2 and asin to FATAN and FASIN, which the
 * 68040 lacks (they trap into the FPU emulation; the engine build refuses code that reaches them, gate 3946). A
 * polynomial for atan on 0..1 (largest error about 1e-5 radians, 0.0006 degrees) and the octant folds. */
static float atan2_deg (float y, float x)
{
	float ax = x < 0 ? -x : x, ay = y < 0 ? -y : y, t, t2, r;
	if (ax == 0 && ay == 0)
		return 0;
	t = ay <= ax ? ay / ax : ax / ay;
	t2 = t * t;
	r = t * (0.9998660f + t2 * (-0.3302995f + t2 * (0.1801410f + t2 * (-0.0851330f + t2 * 0.0208351f))));
	if (ay > ax)
		r = 1.57079633f - r;
	if (x < 0)
		r = 3.14159265f - r;
	return (y < 0 ? -r : r) * 57.29577951f;
}

void AW_SkelBoneTag (const float bone[3][4], const float actor_scale[3], float tag6[6])
{
	/* column form: column 0 is where the bone's x (Quake forward) goes, column 1 its y (left), column 2 its z (up);
	 * tools/npc_items.quake_angles on the same axes */
	float fz = bone[2][0], up_z = bone[2][2], left_z = bone[2][1], c;
	int k;
	for (k=0 ; k<3 ; k++)
		tag6[k] = bone[k][3] * actor_scale[k];
	if (fz > 1)
		fz = 1;
	if (fz < -1)
		fz = -1;
	c = 1 - fz * fz;
	tag6[3] = atan2_deg (-fz, c > 0 ? (float)sqrt (c) : 0);		/* asin(-fz); FSQRT is the 68040's own */
	tag6[4] = atan2_deg (bone[1][0], bone[0][0]);
	tag6[5] = atan2_deg (left_z, up_z);		/* atan2(-right.z, up.z), right = -left */
}

void AW_SkelTransform (const float m[3][4], const float in[3], float out[3])
{
	int i;
	for (i=0 ; i<3 ; i++)
		out[i] = m[i][0]*in[0] + m[i][1]*in[1] + m[i][2]*in[2] + m[i][3];
}

/* A stored quaternion (i16 x y z, w >= 0) as w x y z on the 32767 scale. */
static void quat_of (const unsigned char *k, float q[4])
{
	float s;
	q[1] = (float)S16 (k); q[2] = (float)S16 (k + 2); q[3] = (float)S16 (k + 4);
	s = 32767.0f*32767.0f - q[1]*q[1] - q[2]*q[2] - q[3]*q[3];
	q[0] = s > 0 ? (float)sqrt (s) : 0;
}

/* One bone's local transform, column form: its rotation keys ra, rb blended by u (0..1), its position keys pa, pb.
 * The stored w >= 0 can put neighbouring frames on opposite sides: b is turned to a's side before the normalised
 * lerp, so it never takes the long way. */
static void local_at (const aw_skel_table_t *t, const unsigned char *ra, const unsigned char *rb,
	const unsigned char *pa, const unsigned char *pb, float u, float m[3][4])
{
	float q[4], qa[4], qb[4], p[3], len, w, x, y, z;
	int k;
	quat_of (ra, qa);
	if (u == 0)
	{
		/* a whole frame (every pose the renderer asks for, SKEL-RUNTIME-COST-52): one key, already unit length on
		 * the 32767 scale (w was rebuilt from it), so no blend, no square root and no division */
		const float s = 1.0f / 32767.0f;
		w = qa[0] * s; x = qa[1] * s; y = qa[2] * s; z = qa[3] * s;
		for (k=0 ; k<3 ; k++)
			p[k] = (float)S16 (pa + 2*k) * t->scale;
		goto matrix;
	}
	quat_of (rb, qb);
	if (qa[0]*qb[0] + qa[1]*qb[1] + qa[2]*qb[2] + qa[3]*qb[3] < 0)
		for (k=0 ; k<4 ; k++)
			qb[k] = -qb[k];
	for (k=0 ; k<4 ; k++)
		q[k] = qa[k] * (1-u) + qb[k] * u;
	for (k=0 ; k<3 ; k++)
		p[k] = ((float)S16 (pa + 2*k) * (1-u) + (float)S16 (pb + 2*k) * u) * t->scale;
	len = sqrt (q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
	if (len <= 0)
		len = 1, q[0] = 1;
	len = 1 / len;
	w = q[0]*len; x = q[1]*len; y = q[2]*len; z = q[3]*len;
matrix:
	/* the column form of tools/skeletal_actor.quat_to_matrix (its row-vector matrix transposed) */
	m[0][0] = 1 - 2*(y*y + z*z); m[0][1] = 2*(x*y - w*z);     m[0][2] = 2*(x*z + w*y);
	m[1][0] = 2*(x*y + w*z);     m[1][1] = 1 - 2*(x*x + z*z); m[1][2] = 2*(y*z - w*x);
	m[2][0] = 2*(x*z - w*y);     m[2][1] = 2*(y*z + w*x);     m[2][2] = 1 - 2*(x*x + y*y);
	m[0][3] = p[0]; m[1][3] = p[1]; m[2][3] = p[2];
}

/* v rounded to the nearest integer and clamped to 0..255, without a float-to-integer conversion: the 68040 has no
 * FINTRZ (the conversion traps into the FPU emulation, hundreds of cycles), so v is added to 1.5 x 2^23, whose single
 * float keeps the rounded integer in its low mantissa bits (SKEL-RUNTIME-COST-52). */
static int byte_of (float v)
{
	union {float f; unsigned int u;} m;		/* 32 bits on the Amiga and on the host test */
	if (!(v > 0))
		return 0;
	if (v >= 255)
		return 255;
	m.f = v + 12582912.0f;
	return (int)(m.u & 0x3FFFFF);
}

void AW_SkelPoseVerts (const unsigned char *verts, const unsigned char *normals, int normal_stride, int n,
	float rest_scale, const float world[][3][4], const float origin[3], const float scale[3], unsigned char *out)
{
	/* each bone's matrix folded once with the rest scale (the vertices' i16 units) and the alias quantisation
	 * ((x - origin) / scale): per vertex one 3 x 4 transform per bone used, no division, no conversion
	 * (SKEL-RUNTIME-COST-52) */
	static float folded[AW_SKEL_MAX_BONES][3][4];
	static unsigned char ready[AW_SKEL_MAX_BONES];
	int v, k, j;
	float in[3], a[3], b[3], inv[3];
	for (k=0 ; k<3 ; k++)
		inv[k] = 1.0f / scale[k];
	memset (ready, 0, sizeof(ready));
	for (v=0 ; v<n ; v++, verts += AW_SKEL_VERT_BYTES, out += 4)
	{
		int bone[2], c;
		bone[0] = verts[0];
		bone[1] = verts[1] != AW_SKEL_NONE && verts[2] ? verts[1] : -1;
		for (c=0 ; c<2 ; c++)
		{
			int i = bone[c];
			if (i < 0 || ready[i])
				continue;
			for (k=0 ; k<3 ; k++)
			{
				for (j=0 ; j<3 ; j++)
					folded[i][k][j] = world[i][k][j] * rest_scale * inv[k];
				folded[i][k][3] = (world[i][k][3] - origin[k]) * inv[k];
			}
			ready[i] = 1;
		}
		/* the transform written out (no call per vertex) on the big-endian i16 read straight where the target
		 * allows it (SKEL-RUNTIME-COST-52) */
		in[0] = (float)SKEL_I16 (verts + 4); in[1] = (float)SKEL_I16 (verts + 6); in[2] = (float)SKEL_I16 (verts + 8);
		{
			const float (*m)[4] = folded[bone[0]];
			a[0] = m[0][0]*in[0] + m[0][1]*in[1] + m[0][2]*in[2] + m[0][3];
			a[1] = m[1][0]*in[0] + m[1][1]*in[1] + m[1][2]*in[2] + m[1][3];
			a[2] = m[2][0]*in[0] + m[2][1]*in[1] + m[2][2]*in[2] + m[2][3];
		}
		if (bone[1] >= 0)
		{
			const float (*m)[4] = folded[bone[1]];
			float w = (float)verts[2] * (1.0f / 255.0f);
			in[0] = (float)SKEL_I16 (verts + 10); in[1] = (float)SKEL_I16 (verts + 12); in[2] = (float)SKEL_I16 (verts + 14);
			b[0] = m[0][0]*in[0] + m[0][1]*in[1] + m[0][2]*in[2] + m[0][3];
			b[1] = m[1][0]*in[0] + m[1][1]*in[1] + m[1][2]*in[2] + m[1][3];
			b[2] = m[2][0]*in[0] + m[2][1]*in[1] + m[2][2]*in[2] + m[2][3];
			for (k=0 ; k<3 ; k++)
				a[k] += (b[k] - a[k]) * w;
		}
		for (k=0 ; k<3 ; k++)
			out[k] = (unsigned char)byte_of (a[k]);
		out[3] = normals[v * normal_stride];
	}
}

/* the STILL bones' local transforms of the table last posed, keyed by its bones' base keys and kinds themselves (a
 * table view shares its file's; a table loaded again at the same address with other keys is not mistaken) */
static unsigned char still_keys[AW_SKEL_MAX_BONES * (AW_SKEL_BASE_BYTES + 1)];
static int still_bones = -1;
static float still_scale;
static float still_local[AW_SKEL_MAX_BONES][3][4];
static int still_same (const aw_skel_table_t *t)
{
	return still_bones == t->bones && still_scale == t->scale &&
		!memcmp (still_keys, t->base, (size_t)t->bones * AW_SKEL_BASE_BYTES) &&
		!memcmp (still_keys + AW_SKEL_MAX_BONES * AW_SKEL_BASE_BYTES, t->kind, (size_t)t->bones);
}

/* A frame position's two key rows and the blend between them, clamped to the table. */
static void rows_at (const aw_skel_table_t *t, float frame, const unsigned char **a, const unsigned char **b, float *u)
{
	int f0, f1;
	if (!(frame > 0))
		frame = 0;
	if (frame > (float)(t->frames - 1))
		frame = (float)(t->frames - 1);
	f0 = (int)frame;
	f1 = f0 + 1 < t->frames ? f0 + 1 : f0;
	*u = frame - (float)f0;
	*a = t->keys + (long)f0 * t->row;
	*b = t->keys + (long)f1 * t->row;
}

int AW_SkelLeftArmRoot (const aw_skel_table_t *t, int shield, int weapon)
{
	int i, l = shield, r = weapon;
	if (shield < 0 || shield >= t->bones || weapon < 0 || weapon >= t->bones || shield == weapon)
		return -1;
	for (i=0 ; i<4 ; i++)
	{
		if (l < 0 || r < 0)
			return -1;
		l = t->parent[l];
		r = t->parent[r];
	}
	/* two clavicles of one spine: distinct bones with one parent */
	return l >= 0 && r >= 0 && l != r && t->parent[l] >= 0 && t->parent[l] == t->parent[r] ? l : -1;
}

void AW_SkelPose (const aw_skel_table_t *t, float frame, float world[][3][4])
{
	AW_SkelPoseLayer (t, frame, 0, -1, world);
}

void AW_SkelPoseLayer (const aw_skel_table_t *t, float frame, float layer_frame, int root, float world[][3][4])
{
	int i;
	float u, lu = 0, local[3][4];
	const unsigned char *a, *b, *la = NULL, *lb = NULL;
	unsigned char layered[AW_SKEL_MAX_BONES];
	rows_at (t, frame, &a, &b, &u);
	if (root >= 0 && root < t->bones)
		rows_at (t, layer_frame, &la, &lb, &lu);
	else
		root = -1;
	if (!still_same (t))
	{
		/* a bone that never moves has one local transform for every frame: made once per table, not per pose
		 * (27 of the 61 humanoid bones; SKEL-RUNTIME-COST-52) */
		for (i=0 ; i<t->bones ; i++)
			if (t->kind[i] == AW_SKEL_STILL)
			{
				const unsigned char *base = t->base + i*AW_SKEL_BASE_BYTES;
				local_at (t, base, base, base + 6, base + 6, 0, still_local[i]);
			}
		memcpy (still_keys, t->base, (size_t)t->bones * AW_SKEL_BASE_BYTES);
		memcpy (still_keys + AW_SKEL_MAX_BONES * AW_SKEL_BASE_BYTES, t->kind, (size_t)t->bones);
		still_bones = t->bones;
		still_scale = t->scale;
	}
	for (i=0 ; i<t->bones ; i++)
	{
		const unsigned char *base = t->base + i*AW_SKEL_BASE_BYTES, *ra = a, *rb = b;
		float ru = u;
		/* the layer's bones (ROOT and every bone under it; parents come first) take the layer frame's keys */
		layered[i] = root >= 0 && (i == root || (t->parent[i] >= 0 && layered[t->parent[i]]));
		if (layered[i])
			ra = la, rb = lb, ru = lu;
		if (t->kind[i] == AW_SKEL_STILL)
			memcpy (local, still_local[i], sizeof(local));
		else if (t->kind[i] == AW_SKEL_TURNS)
			local_at (t, ra + t->offset[i], rb + t->offset[i], base + 6, base + 6, ru, local);
		else
			local_at (t, ra + t->offset[i], rb + t->offset[i], ra + t->offset[i] + 6, rb + t->offset[i] + 6, ru, local);
		/* the builder's world = local @ world(parent) in row form: parent * local in column form */
		if (t->parent[i] < 0)
			memcpy (world[i], local, sizeof(local));
		else
			AW_SkelConcat (world[t->parent[i]], local, world[i]);
	}
}
