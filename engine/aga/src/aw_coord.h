/* aw_coord.h: how positions travel in messages (CHIM-FRAME-COORD-RANGE-33).
 *
 * Quake sends every coordinate (origins, entity updates, sounds, particles, static entities) as a 16-bit
 * integer of eighths of a unit, so a position wraps past about +/-4,096 units; the engine keeps a frame's
 * player area within AW_COORD_BOUND of its origin.
 *
 * Wide coordinates (the default since v0.0.36, so all of Vivec fits one CHIM frame) send 24 bits of 1/256 units
 * instead: +/-32,768 units, the range of the BSP node and leaf bounds, one byte more per coordinate. The protocol
 * number changes with it (PROTOCOL_VERSION), so a narrow and a wide engine never read each other's messages or
 * demos. Saved games store positions as text and are not affected. AW_COORD_NARROW (make
 * EXTRA_DEFINES=-DAW_COORD_NARROW; tools/build.py --coord-range narrow) keeps Quake's 16-bit eighths, the method
 * before v0.0.36. AW_EXP_WIDECOORD, the switch of the v0.0.36 spike, still selects wide.
 *
 * Pure functions on bytes: the host test (tests/test_coord_wide_native.py) compiles this header alone.
 */
#ifndef AW_COORD_H
#define AW_COORD_H

#if defined(AW_COORD_NARROW) && defined(AW_EXP_WIDECOORD)
#error "AW_COORD_NARROW and AW_EXP_WIDECOORD select different coordinate ranges"
#endif

#ifndef AW_COORD_NARROW
#define AW_COORD_BYTES 3
#define AW_COORD_BOUND 32000      /* player areas, arrivals and spawn checks (aw_world.c, aw_spawn.c, aw_scene.c) */
#define AW_COORD_PROTOCOL 1015    /* PROTOCOL_VERSION of a wide-coordinate engine (Quake's is 15) */
#else
#define AW_COORD_BYTES 2
#define AW_COORD_BOUND 4000
#define AW_COORD_PROTOCOL 15
#endif

/* 24-bit coordinates: round to 1/256 unit, clamp to the representable range (no wrap), little-endian. */
#define AW_COORD24_MAX 8388607L
#define AW_COORD24_MIN (-8388608L)

static __inline__ void AW_Coord24Encode (float f, unsigned char *out)
{
	double scaled = (double)f * 256.0;
	long v;
	if (!(scaled == scaled))
		scaled = 0.0;                                   /* NaN travels as 0 */
	if (scaled >= (double)AW_COORD24_MAX)
		v = AW_COORD24_MAX;
	else if (scaled <= (double)AW_COORD24_MIN)
		v = AW_COORD24_MIN;
	else
		v = (long)(scaled < 0 ? scaled - 0.5 : scaled + 0.5);
	out[0] = (unsigned char)(v & 0xff);
	out[1] = (unsigned char)((v >> 8) & 0xff);
	out[2] = (unsigned char)((v >> 16) & 0xff);
}

static __inline__ float AW_Coord24Decode (const unsigned char *in)
{
	long v = (long)in[0] | ((long)in[1] << 8) | ((long)in[2] << 16);
	if (v & 0x800000L)
		v -= 0x1000000L;
	return (float)((double)v / 256.0);
}

#endif
