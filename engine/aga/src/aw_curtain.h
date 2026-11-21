/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Ghostfence curtain's own scroll (GHOSTFENCE-NO-ANIMATION-46, GHOSTFENCE-PARTICLES-NOT-DRAWN-68 C2, v0.0.68).
 *
 * The curtain's meshes are three layers whose textures slide (an NiUVController each: two of Tx_GG_fence_01 at two
 * speeds, one of Tx_GG_fence_02, swaying sideways). The builder writes id1/world/curtain.awc (tools/ghostfence_effects.py
 * curtain_table): the layers' texture intensities (0..15), their motion as tables over the loop, a colour ramp per pulse
 * step and the checksums of the curtain textures as the CHIM stores hold them. With aw_curtain 1 the engine composes the
 * three layers into one 32 x 32 texture once a drawn frame (AW_CurtainCompose: three lookups and an add a texel, then
 * the ramp) and draws the curtain straight from it, instead of Quake's warp of its first layer (aw_curtain 0, the
 * default until the A/B stills).
 *
 * aw_curtain_rules.c holds the pure part (no engine state: the host test compiles it alone); aw_curtain.c the engine
 * glue (the setting, the file, the drawn block for d_edge.c). */
#ifndef AW_CURTAIN_H
#define AW_CURTAIN_H

#define AW_CURTAIN_MAGIC	"AWC1"
#define AW_CURTAIN_HEAD		28	/* tools/ghostfence_effects.py CURTAIN_HEAD */
#define AW_CURTAIN_SIZE		32	/* the composed texture's side; a power of two */
#define AW_CURTAIN_DRAWN	64	/* the turbulent drawing's texture side (d_scan.c Turbulent8) */
#define AW_CURTAIN_SOURCES	4
#define AW_CURTAIN_LAYERS	8
#define AW_CURTAIN_STEPS	64
#define AW_CURTAIN_PULSE_STEPS	16
#define AW_CURTAIN_LEVELS	128
#define AW_CURTAIN_PULSES	16
#define AW_CURTAIN_TEXTURES	16
#define AW_CURTAIN_BYTES	3584	/* the largest table read (the builder's: 2,866 bytes) */

typedef struct {
	int size, sources, layers, levels, pulses, textures, steps;
	unsigned long period_ms, pulse_ms;
	unsigned long hash[AW_CURTAIN_TEXTURES];
	int texture_size[AW_CURTAIN_TEXTURES];	/* 32: a tiled small texture, 64: drawn at its own size */
	const unsigned char *source[AW_CURTAIN_SOURCES];
	int layer_source[AW_CURTAIN_LAYERS];
	const signed char *u[AW_CURTAIN_LAYERS];
	const unsigned char *v[AW_CURTAIN_LAYERS];
	const unsigned char *pulse;
	const unsigned char *ramp;
} aw_curtain_t;

/* The table in RAW (BYTES long; kept by the caller) into OUT: 1 when it is whole and within the bounds above. */
int AW_CurtainParse (const unsigned char *raw, unsigned long bytes, aw_curtain_t *out);
/* FNV-1a 32 of N bytes (the builder's fnv1a) */
unsigned long AW_CurtainHash (const unsigned char *p, unsigned long n);
/* The table's texture with hash H: its own size (32 or 64), 0 for none. */
int AW_CurtainFind (const aw_curtain_t *c, unsigned long h);
/* The composed curtain at T_MS (AW_CurtainSize x itself palette indices into OUT): tools/ghostfence_effects.py
 * curtain_compose, the same integer steps. */
void AW_CurtainCompose (const aw_curtain_t *c, unsigned long t_ms, unsigned char *out);
/* The 64 x 64 block d_edge.c draws from: the composed texture tiled (SIZE 32: the texture was tiled from a 32 x 32
 * one, so its mapping repeats every 32 texels) or each texel doubled (SIZE 64: a texture drawn at its own size). */
void AW_CurtainBlock (const unsigned char *composed, int size, unsigned char *block);

/* aw_curtain.c: the setting and the hook (d_edge.c aw_curtain_block); called by AW_AtmosInit. */
void AW_CurtainInit (void);
/* aw_curtain.c: the image's table (read when first asked for), NULL without one; DemoWind's curtain effects */
const aw_curtain_t *AW_CurtainTable (void);

#endif
