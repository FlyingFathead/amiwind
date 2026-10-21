/* SPDX-License-Identifier: GPL-2.0-or-later
 * File aliases (IMAGE-DUPLICATE-FILES-46): common.c reads the table tools/payload_share.py writes
 * (argv[1]): every alias resolves to its stored name, case-insensitively; stored names and other names
 * resolve to nothing; a table out of order (argv[2]) or malformed gives no aliases at all. */
#include "quakedef.h"
#include <assert.h>
static char heap[1 << 16];
static int used;
void *Hunk_AllocName (int size, char *name)
{
	void *p = heap + used;
	(void)name;
	used += (size + 15) & ~15;
	assert (used <= (int)sizeof(heap));
	return p;
}
void Con_Printf (char *fmt, ...) {(void)fmt;}
static char *load (const char *path, int *bytes)
{
	FILE *f = fopen (path, "rb");
	char *text;
	long n;
	assert (f && !fseek (f, 0, SEEK_END) && (n = ftell (f)) > 0 && !fseek (f, 0, SEEK_SET));
	text = malloc (n + 1);
	assert (text && fread (text, 1, n, f) == (size_t)n);
	fclose (f);
	text[n] = 0;
	*bytes = (int)n;
	return text;
}
int main (int argc, char **argv)
{
	char *text, *copy;
	int bytes, i;
	assert (argc == 3);
	text = load (argv[1], &bytes);
	assert (COM_ParseFileAliases (text, bytes) == 4);
	assert (!strcmp (COM_FileAliasTarget ("progs/a_b.mdl"), "progs/target.mdl"));
	assert (!strcmp (COM_FileAliasTarget ("PROGS/AB.MDL"), "progs/target.mdl"));
	assert (!strcmp (COM_FileAliasTarget ("progs/a_c.mdl"), "progs/target.mdl"));
	assert (!strcmp (COM_FileAliasTarget ("sound/npc/y.wav"), "sound/pool/x.wav"));
	assert (!COM_FileAliasTarget ("progs/target.mdl") && !COM_FileAliasTarget ("progs/a_d.mdl"));
	assert (!COM_FileAliasTarget ("") && !COM_FileAliasTarget ("zzz"));
	free (text);
	text = load (argv[2], &bytes);
	assert (COM_ParseFileAliases (text, bytes) == 0 && !COM_FileAliasTarget ("progs/a_b.mdl"));
	free (text);
	/* Damaged tables: truncated, a bad index, a missing count: nothing is aliased. */
	text = load (argv[1], &bytes);
	for (i = 1 ; i < bytes ; i += 7) {
		copy = malloc (bytes + 1);
		memcpy (copy, text, bytes + 1);
		copy[i] = 0;
		assert (COM_ParseFileAliases (copy, i) == 0 || i == bytes);
		free (copy);
	}
	copy = malloc (bytes + 1);
	memcpy (copy, text, bytes + 1);
	*strrchr (copy, '\t') = ' ';
	assert (COM_ParseFileAliases (copy, bytes) == 0);
	free (copy);
	free (text);
	printf ("file-alias: builder table read, case-insensitive, ordered, damaged tables ignored\n");
	return 0;
}
