/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Ghostfence curtain's table and compose (aw_curtain.h): pure, no engine state (tests/test_ghostfence_effects.py
 * builds it alone and checks it against the builder's Python twin, tools/ghostfence_effects.py curtain_compose). */
#include <string.h>
#include "aw_curtain.h"

static unsigned le16 (const unsigned char *p) {return (unsigned)p[0] | ((unsigned)p[1] << 8);}
static unsigned long le32 (const unsigned char *p)
{
	return (unsigned long)p[0] | ((unsigned long)p[1] << 8) | ((unsigned long)p[2] << 16) | ((unsigned long)p[3] << 24);
}

unsigned long AW_CurtainHash (const unsigned char *p, unsigned long n)
{
	unsigned long h = 0x811C9DC5UL;
	while (n--)
		h = ((h ^ *p++) * 0x01000193UL) & 0xFFFFFFFFUL;
	return h;
}

int AW_CurtainParse (const unsigned char *raw, unsigned long bytes, aw_curtain_t *out)
{
	unsigned long at, need;
	int i;
	memset (out, 0, sizeof(*out));
	if (!raw || bytes < AW_CURTAIN_HEAD || memcmp (raw, AW_CURTAIN_MAGIC, 4) || le16 (raw + 4) != 1)
		return 0;
	out->size = (int)le16 (raw + 6);
	out->sources = (int)le16 (raw + 8);
	out->layers = (int)le16 (raw + 10);
	out->levels = (int)le16 (raw + 12);
	out->pulses = (int)le16 (raw + 14);
	out->textures = (int)le16 (raw + 16);
	out->steps = (int)le16 (raw + 18);
	out->period_ms = le32 (raw + 20);
	out->pulse_ms = le32 (raw + 24);
	if (out->size != AW_CURTAIN_SIZE || out->sources < 1 || out->sources > AW_CURTAIN_SOURCES || out->layers < 1 ||
		out->layers > AW_CURTAIN_LAYERS || out->levels < 2 || out->levels > AW_CURTAIN_LEVELS || out->pulses < 1 ||
		out->pulses > AW_CURTAIN_PULSES || out->textures < 0 || out->textures > AW_CURTAIN_TEXTURES ||
		out->steps < 1 || out->steps > AW_CURTAIN_STEPS || !out->period_ms || !out->pulse_ms ||
		out->period_ms > 3600000UL || out->pulse_ms > 3600000UL)
		return 0;
	need = AW_CURTAIN_HEAD + 8UL * out->textures + (unsigned long)out->sources * out->size * out->size +
		(unsigned long)out->layers * (2 + 2 * out->steps) + AW_CURTAIN_PULSE_STEPS + (unsigned long)out->pulses * out->levels;
	if (need != bytes)
		return 0;
	at = AW_CURTAIN_HEAD;
	for (i = 0; i < out->textures; i++, at += 8)
	{
		out->hash[i] = le32 (raw + at);
		out->texture_size[i] = (int)le16 (raw + at + 4);
		if (out->texture_size[i] != AW_CURTAIN_SIZE && out->texture_size[i] != AW_CURTAIN_DRAWN)
			return 0;
	}
	for (i = 0; i < out->sources; i++, at += (unsigned long)out->size * out->size)
		out->source[i] = raw + at;
	for (i = 0; i < out->layers; i++)
	{
		out->layer_source[i] = raw[at];
		if (out->layer_source[i] >= out->sources)
			return 0;
		out->u[i] = (const signed char *)(raw + at + 2);
		out->v[i] = raw + at + 2 + out->steps;
		at += 2 + 2 * out->steps;
	}
	out->pulse = raw + at;
	for (i = 0; i < AW_CURTAIN_PULSE_STEPS; i++)
		if (out->pulse[i] >= out->pulses)
			return 0;
	at += AW_CURTAIN_PULSE_STEPS;
	out->ramp = raw + at;
	/* every summed level a texel can reach has its ramp entry: 15 a layer at most */
	for (i = 0; i < out->sources; i++)
	{
		int k;
		for (k = 0; k < out->size * out->size; k++)
			if (out->source[i][k] * out->layers >= out->levels)
				return 0;
	}
	return 1;
}

int AW_CurtainFind (const aw_curtain_t *c, unsigned long h)
{
	int i;
	for (i = 0; c && i < c->textures; i++)
		if (c->hash[i] == h)
			return c->texture_size[i];
	return 0;
}

void AW_CurtainCompose (const aw_curtain_t *c, unsigned long t_ms, unsigned char *out)
{
	int mask = c->size - 1, x, y, l, step, du[AW_CURTAIN_LAYERS], dv[AW_CURTAIN_LAYERS];
	unsigned long t = t_ms % c->period_ms;
	const unsigned char *ramp;
	step = (int)(t * (unsigned long)c->steps / c->period_ms);
	ramp = c->ramp + (unsigned long)c->pulse[(t_ms % c->pulse_ms) * AW_CURTAIN_PULSE_STEPS / c->pulse_ms] * c->levels;
	for (l = 0; l < c->layers; l++)
	{
		du[l] = c->u[l][step] & mask;
		dv[l] = c->v[l][step] & mask;
	}
	for (y = 0; y < c->size; y++)
		for (x = 0; x < c->size; x++)
		{
			int s = 0;
			for (l = 0; l < c->layers; l++)
				s += c->source[c->layer_source[l]][((y + dv[l]) & mask) * c->size + ((x + du[l]) & mask)];
			out[y * c->size + x] = ramp[s];
		}
}

void AW_CurtainBlock (const unsigned char *composed, int size, unsigned char *block)
{
	int x, y;
	for (y = 0; y < AW_CURTAIN_DRAWN; y++)
		for (x = 0; x < AW_CURTAIN_DRAWN; x++)
			block[y * AW_CURTAIN_DRAWN + x] = size == AW_CURTAIN_DRAWN ?
				composed[(y >> 1) * AW_CURTAIN_SIZE + (x >> 1)] :
				composed[(y & (AW_CURTAIN_SIZE - 1)) * AW_CURTAIN_SIZE + (x & (AW_CURTAIN_SIZE - 1))];
}
