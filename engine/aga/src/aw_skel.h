/* aw_skel.h: shared animation tables (docs/MODULAR_NPCS.md, "Runtime method C").
 *
 * Every humanoid moves by one skeleton and one table of every motion it can make, stored once
 * (tools/skeletal_actor.py writes it). Per drawn actor the engine samples the table at the actor's group and time,
 * builds one 3 x 4 matrix per bone (parent first), and the alias renderer transforms each vertex by its bone's
 * matrix instead of the one model matrix. Pure functions, no engine state: the renderer, the loader and the host
 * test (tests/aga_skel_test.c) use the same code.
 *
 * The table, big-endian (the Amiga's order):
 *   "AWSK", u16 version 2, u16 bones, u32 frames, f32 rate (frames per second), f32 position scale (units per step),
 *   u16 groups, u16 text keys;
 *   bones x i16 parent (-1 none; every parent before its child), padded to 4 bytes;
 *   bones x u8 kind (AW_SKEL_STILL, AW_SKEL_TURNS, AW_SKEL_MOVES), padded to 4 bytes;
 *   groups x { char name[24] (NUL padded), u32 first frame, u32 last frame };
 *   text keys x { char text[32] (a phase of its group: "start", "self release", "chop min hit"; or a sound event
 *   whole: "soundgen: left"), u16 group (AW_SKEL_NO_GROUP none), u16 0, u32 frame }, sorted by frame: the frames
 *   the game logic plays between, and MWScript's PlayGroup and LoopGroup later (OpenMW mwrender/animation.cpp);
 *   bones x { i16 quaternion x y z (x 32767; w >= 0, rebuilt from them), i16 position x y z (x scale) }: each
 *   bone's first frame, all a STILL bone ever has, and the position of one that only TURNS;
 *   frames x { per bone that is not STILL: i16 quaternion x y z, then i16 position x y z if it MOVES }.
 * SKEL-TABLE-SIZE-52: of the base game's 61 humanoid nodes 27 never move and 23 only turn; at 10 frames a second
 * the table is under a quarter of version 1 (every bone, w x y z and a position, 15 a second).
 * Matrices here are column form (Quake's): out = M[0..2][0..2] * in + M[i][3]. */
#ifndef AW_SKEL_H
#define AW_SKEL_H

#define AW_SKEL_MAGIC		"AWSK"
#define AW_SKEL_VERSION		2
#define AW_SKEL_BLOCK_VERSION	1
#define AW_SKEL_MAX_BONES	64
#define AW_SKEL_NAME		24
#define AW_SKEL_HEADER		24
#define AW_SKEL_GROUP_BYTES	(AW_SKEL_NAME + 8)
#define AW_SKEL_KEY_TEXT	32		/* "slash large follow start" is 24 */
#define AW_SKEL_KEY_BYTES	(AW_SKEL_KEY_TEXT + 8)
#define AW_SKEL_NO_GROUP	0xFFFF
/* a view's group prefixes with their NUL: "f:" (SKEL-TABLE-SHARED-FEMALE-52), "d:f:" (an NPC's own animation file
 * and a woman's groups, in that order: DANCER-OWN-ANIM-IGNORED-53) */
#define AW_SKEL_PREFIX		8
#define AW_SKEL_BASE_BYTES	12
#define AW_SKEL_STILL		0
#define AW_SKEL_TURNS		1
#define AW_SKEL_MOVES		2

typedef struct {
	char		name[AW_SKEL_NAME];
	unsigned	first, last;
} aw_skel_group_t;

typedef struct {
	int			bones, frames, groups, keys_count;
	float		rate, scale;
	short		parent[AW_SKEL_MAX_BONES];
	unsigned char	kind[AW_SKEL_MAX_BONES];
	short		offset[AW_SKEL_MAX_BONES];	/* a bone's bytes within a frame's row (-1 STILL) */
	int			row;			/* bytes per frame */
	const unsigned char	*group_data;	/* groups x AW_SKEL_GROUP_BYTES, in the table's memory */
	const unsigned char	*key_data;		/* keys_count x AW_SKEL_KEY_BYTES */
	const unsigned char	*base;			/* bones x AW_SKEL_BASE_BYTES */
	const unsigned char	*keys;			/* frames x row */
	char		prefix[AW_SKEL_PREFIX];	/* a view's own groups ("f:", "d:f:" in order), looked up first by name; "" for a table */
} aw_skel_table_t;

/* 1 and *out filled when data[0..size) is a valid table (sizes, parents before children, groups inside the
 * frames); 0 otherwise. The table keeps pointers into data: data must live as long as the table. */
int AW_SkelParse (const unsigned char *data, long size, aw_skel_table_t *out);
/* The index of a group by name (case-insensitive), or -1; a view (prefix set) gives its own group of that name
 * (prefix + name) when the table has one. */
int AW_SkelGroup (const aw_skel_table_t *t, const char *name);
void AW_SkelGroupAt (const aw_skel_table_t *t, int index, aw_skel_group_t *out);
/* The frame of a group's text key by name (case-insensitive: "start", "self release", "chop hit"), or -1: the one
 * entry point the game logic (and MWScript later) uses to play a phase of a group. */
int AW_SkelKeyFrame (const aw_skel_table_t *t, int group, const char *text);
/* The bones' world matrices at a frame position (a fraction between two frames blends them: the quaternions by
 * normalised lerp, the positions by lerp). frame is clamped to the table. */
void AW_SkelPose (const aw_skel_table_t *t, float frame, float world[][3][4]);
/* AW_SkelPose with one layer: ROOT and every bone under it take LAYER_FRAME's keys (ROOT -1: none). A guard holding
 * his torch has his left arm on the table's "torch" group, as the baked guards (tools/prepare_guard_torches.py
 * TorchLayer, below Bip01 L Clavicle) and the original (SKEL-ITEM-TAGS-52). */
void AW_SkelPoseLayer (const aw_skel_table_t *t, float frame, float layer_frame, int root, float world[][3][4]);
/* The left arm's root (Bip01 L Clavicle) from the item bones: the shield bone's fourth ancestor (shield bone, hand,
 * forearm, upper arm, clavicle; tools/skeletal_actor.py STICK_BONES), checked against the weapon bone's (the other
 * clavicle, the same parent). -1 when the table is not shaped so. */
int AW_SkelLeftArmRoot (const aw_skel_table_t *t, int shield, int weapon);
/* One vertex of a skeletal model (16 bytes on disk, big-endian): the bone it hangs on, a second bone at joints
 * (255 none) and that bone's weight (0-255), and its position in each bone's rest space (x rest_scale). */
#define AW_SKEL_NONE		255
#define AW_SKEL_VERT_BYTES	16
/* Poses n vertices into an alias frame (Quake's byte vertices: (pos - origin) / scale, clamped 0..255):
 * verts = n x AW_SKEL_VERT_BYTES; normals: each vertex's light normal index, kept, normal_stride bytes apart (4
 * when read from the model's rest frame); out: n x 4 bytes (x y z normal), the layout of trivertx_t. world:
 * AW_SkelPose's matrices. */
void AW_SkelPoseVerts (const unsigned char *verts, const unsigned char *normals, int normal_stride, int n,
	float rest_scale, const float world[][3][4], const float origin[3], const float scale[3], unsigned char *out);
/* The skeletal block of a model (after the frames of an ordinary MDL, which keeps one rest frame for its box,
 * collision and normals), big-endian: "AWSB", u16 version 1, u16 0, char table[32] (the shared table's path,
 * NUL padded), f32 rest scale, u32 vertex count (the model's), u32 the table's frame count, f32 x 3 pose origin,
 * f32 x 3 pose step; then the vertices. The pose origin and step quantise a posed vertex (the skeleton's units)
 * into the model's bytes: they are the model's scale_origin and scale divided by the actor's own scale (the race's
 * weight and height, and the map scale), which a non-uniform scale makes necessary: it does not commute with the
 * bones' rotations, so it is applied here, after posing. */
#define AW_SKEL_BLOCK_MAGIC	"AWSB"
#define AW_SKEL_BLOCK_HEAD	76
#define AW_SKEL_TABLE_NAME	32
typedef struct {
	char		table[AW_SKEL_TABLE_NAME];
	float		rest_scale;
	int			verts, frames;
	float		pose_origin[3], pose_step[3];
	const unsigned char	*data;		/* verts x AW_SKEL_VERT_BYTES */
} aw_skel_block_t;
/* 1 and *out filled when b[0..size) is a valid block for a model of nv vertices (every bone index checked against
 * AW_SKEL_MAX_BONES; the table's own bone count is checked when it is posed). */
int AW_SkelBlockParse (const unsigned char *b, long size, int nv, aw_skel_block_t *out);
/* The header checks only (the loader ran AW_SkelBlockParse once): for the renderer, per draw. */
int AW_SkelBlockHead (const unsigned char *b, long size, int nv, aw_skel_block_t *out);
/* 1 when every vertex's bones exist in a table of `bones` bones. */
int AW_SkelBlockFits (const aw_skel_block_t *block, int bones);
/* aw_skel_load.c: the table at a game path, loaded once and kept; NULL when it cannot be read (said once). */
const aw_skel_table_t *AW_SkelTableFor (const char *name);
/* Every loaded table given back; the next lookup loads it again (the caller first flushes the models that point into
 * them). The bytes given back. */
unsigned long AW_SkelTablesRelease (void);
/* r_alias.c: the posed frames given back (the large pose cache freed, the kept slots emptied). The bytes freed. */
unsigned long R_AliasPoseCacheRelease (void);
/* aw_skel_release.c: registers the release of both with aw_fastrelease.c (run before a large block is sized from the
 * free Fast RAM: a room's growth, the CHIM cache banks) */
void AW_SkelReleaseInit (void);
/* A carried item's tag row (aw_items.h: origin x y z in the model's space, Quake pitch yaw roll in degrees) from
 * its bone's posed matrix (AW_SkelPose) and the actor's own scale (weight, weight, height x the map scale), as
 * tools/npc_items.py bone_tags writes it for a baked model: a skeletal actor needs no tag file
 * (SKEL-ITEM-TAGS-52). The rotation is taken orthonormal (the bones' are: the scale is the actor's, applied here). */
void AW_SkelBoneTag (const float bone[3][4], const float actor_scale[3], float tag6[6]);
/* out = m * in (column form). */
void AW_SkelTransform (const float m[3][4], const float in[3], float out[3]);
/* c = a * b (column form 3 x 4, b applied first). */
void AW_SkelConcat (const float a[3][4], const float b[3][4], float c[3][4]);

#endif
