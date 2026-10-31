/* aw_skel_load.c: the shared animation tables skeletal models name (aw_skel.h), each loaded once by its path and
 * kept for the session: one table serves every humanoid (docs/MODULAR_NPCS.md, "Runtime method C"). A table that
 * cannot be read or is invalid says so once on the console; its models then draw their rest frame. */
#include "quakedef.h"
#include "aw_skel.h"
#include "aw_tryalloc.h"
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
/* The toolchain's malloc never returns NULL: when exec has no block for it, its allocator (libc malloc.o,
 * MemMap::alloc) stores through the NULL AllocMem gave it and stops on TRAP #7, a Software Failure #80000027
 * (SKEL-16MB-TRAP-52: the female table at 16 MB of Fast RAM). A table is only asked for when the largest free block
 * holds it with room to spare; otherwise it is refused as unreadable and its models draw their rest frame. */
#define AW_SKEL_ALLOC_SPARE	65536L
static void *table_alloc (long size)
{
	long largest = (long)AvailMem (MEMF_LARGEST);
	if (largest < size + 4 + AW_SKEL_ALLOC_SPARE)
	{
		Con_Printf ("Animation table: no memory for %ld bytes (largest free block %ld)\n", size, largest);
		return NULL;
	}
	return AW_TryMalloc (size);
}
#else
#define table_alloc(size)	AW_TryMalloc (size)
#endif

/* 24: the three humanoid tables and their views, and the creatures on their own or appended tables (one each) that a
 * window or a room shows at once (8 before the creature tables, CREATURE-TABLES-54) */
#define AW_SKEL_TABLES	24

static struct {
	char			name[AW_SKEL_TABLE_NAME];
	unsigned char	*data;
	long			size;
	aw_skel_table_t	table;
	int				failed;
} tables[AW_SKEL_TABLES];

/* ---- paged frames (WALK-CYCLES-57) ----
 * A table is held as its index (header, bones, groups, keys, base keys: 39 KB of the common table's 602 KB) and its
 * frames are read from the file in chunks of AW_SKEL_CHUNK the first time a pose needs one, then kept with the table:
 * a town whose people idle, turn, walk and run holds those groups' frames, not the 139 groups (deaths, attacks,
 * spellcasts, swims) nobody plays there. A chunk read is AW_SKEL_CHUNK x row bytes (3 KB for the common table), at the
 * moment an actor first poses a frame of it; the pose cache (r_alias.c) keeps the posed vertices as before. Frame 0's
 * row is read with the index and stands in for a chunk that cannot be read. aw_skel_paged 0: the previous method (the
 * whole file in one block), for the next table loaded. Rule: docs/MODULAR_NPCS.md "Paged animation frames". */
#define AW_SKEL_CHUNK	16
typedef struct {
	FILE			*f;
	long			rows;			/* the file position of frame 0's row */
	int				row, frames, chunks;
	unsigned char	**chunk;		/* chunks pointers, NULL until read */
	unsigned char	*row0;
	int				said;
} aw_skel_pages_t;
int aw_skel_paged = 1;
static unsigned long paged_held, paged_disk;	/* frame bytes read and kept / frame bytes in the paged files */

static void pages_free (aw_skel_pages_t *p)
{
	int c;
	if (!p)
		return;
	if (p->chunk)
	{
		for (c=0 ; c<p->chunks ; c++)
			if (p->chunk[c])
				free (p->chunk[c]);
		free (p->chunk);
	}
	if (p->row0)
		free (p->row0);
	if (p->f)
		fclose (p->f);
	free (p);
}

static const unsigned char *paged_row (const aw_skel_table_t *t, int frame)
{
	aw_skel_pages_t *p = (aw_skel_pages_t *)t->pages;
	int c, n;
	unsigned char *buf;
	if (!p || frame < 0 || frame >= p->frames)
		return p ? p->row0 : NULL;
	c = frame / AW_SKEL_CHUNK;
	if (!p->chunk[c])
	{
		n = p->frames - c * AW_SKEL_CHUNK;
		if (n > AW_SKEL_CHUNK)
			n = AW_SKEL_CHUNK;
		buf = table_alloc ((long)n * p->row);
		if (!buf || fseek (p->f, p->rows + (long)c * AW_SKEL_CHUNK * p->row, SEEK_SET) ||
			fread (buf, 1, (size_t)n * p->row, p->f) != (size_t)n * p->row)
		{
			if (buf)
				free (buf);
			if (!p->said)
				Con_Printf ("Animation table: frames %d.. could not be read; frame 0 stands in\n", c * AW_SKEL_CHUNK);
			p->said = 1;
			return p->row0;
		}
		p->chunk[c] = buf;
		paged_held += (unsigned long)n * p->row;
	}
	return p->chunk[c] + (long)(frame - c * AW_SKEL_CHUNK) * p->row;
}

/* "dbg animkit": the frame bytes held against the frame bytes on disk of the paged tables, and the index bytes */
void AW_SkelTablesBytes (unsigned long *held, unsigned long *disk, unsigned long *index)
{
	int i;
	*held = paged_held;
	*disk = paged_disk;
	*index = 0;
	for (i=0 ; i<AW_SKEL_TABLES ; i++)
		if (tables[i].data)
			*index += (unsigned long)tables[i].size;
}

/* Every table given back (aw_skel_release.c, before a room takes Fast RAM): the next lookup loads it again from its
 * file. The caller has flushed every model that points into them. Returns the bytes given back. */
unsigned long AW_SkelTablesRelease (void)
{
	unsigned long given = paged_held;
	int i;
	for (i=0 ; i<AW_SKEL_TABLES ; i++)
		if (tables[i].data)
		{
			free (tables[i].data);
			given += (unsigned long)tables[i].size;
			pages_free ((aw_skel_pages_t *)tables[i].table.pages);	/* a view's pages are its file's: data NULL */
		}
	memset (tables, 0, sizeof(tables));
	paged_held = paged_disk = 0;
	return given;
}

/* The table at NAME's open file F (SIZE bytes) as its index and paged frames; 0 when it cannot be (said by the caller) */
static int load_paged (int i, FILE *f, int size)
{
	unsigned char head[AW_SKEL_HEADER + AW_SKEL_TABLE_NAME];
	long have = size < (int)sizeof(head) ? size : (long)sizeof(head), index, start = ftell (f);
	aw_skel_pages_t *p;
	if (start < 0 || fread (head, 1, (size_t)have, f) != (size_t)have || (index = AW_SkelIndexBytes (head, have)) < 0 ||
		index > size || !(tables[i].data = table_alloc (index)))
		return 0;
	tables[i].size = index;
	memcpy (tables[i].data, head, (size_t)(have < index ? have : index));
	if ((index > have && fread (tables[i].data + have, 1, (size_t)(index - have), f) != (size_t)(index - have)) ||
		!AW_SkelParseIndex (tables[i].data, index, size, &tables[i].table) || tables[i].table.own_frames < 1 ||
		!(p = (aw_skel_pages_t *)table_alloc (sizeof(*p))))
		return 0;
	memset (p, 0, sizeof(*p));
	tables[i].table.pages = p;
	p->f = f;
	p->rows = start + index;
	p->row = tables[i].table.row;
	p->frames = tables[i].table.own_frames;
	p->chunks = (p->frames + AW_SKEL_CHUNK - 1) / AW_SKEL_CHUNK;
	if (!(p->chunk = (unsigned char **)table_alloc ((long)p->chunks * (long)sizeof(*p->chunk))) ||
		!(p->row0 = table_alloc (p->row > 0 ? p->row : 1)))
		return 0;
	memset (p->chunk, 0, (size_t)p->chunks * sizeof(*p->chunk));
	if (p->row > 0 && fread (p->row0, 1, (size_t)p->row, f) != (size_t)p->row)
		return 0;
	tables[i].table.row_of = paged_row;
	paged_disk += (unsigned long)p->frames * (unsigned long)p->row;
	return 1;
}

/* model.c's generic alias loader (aw_alias_skel_link, ANIMKIT-COVERAGE-35): the skeletal block BLOCK (SIZE bytes, in
 * the model's own memory after H) linked to its table as the alias stream links it (model_alias_stream.inc); 1 and
 * *frames the table's frames, 0 when the block or its table does not fit (the model keeps its rest frame). */
int AW_SkelLinkAlias (aliashdr_t *h, byte *block, long size, int verts, int *frames);
int AW_SkelLinkAlias (aliashdr_t *h, byte *block, long size, int verts, int *frames)
{
	aw_skel_block_t b;
	const aw_skel_table_t *table;
	if (!AW_SkelBlockParse (block, size, verts, &b) || !(table = AW_SkelTableFor (b.table)) ||
		table->frames != b.frames || !AW_SkelBlockFits (&b, table->bones))
	{
		Con_Printf ("Skeletal model (generic loader): animation table missing or not matching, rest pose\n");
		return 0;
	}
	h->aw_skel = (int)(block - (byte *)h);
	h->aw_skel_table = table;
	*frames = b.frames;
	return 1;
}

const aw_skel_table_t *AW_SkelTableFor (const char *name)
{
	int i, size;
	FILE *f;
	for (i=0 ; i<AW_SKEL_TABLES && tables[i].name[0] ; i++)
		if (!strcmp (tables[i].name, name))
			return tables[i].failed ? NULL : &tables[i].table;
	if (i == AW_SKEL_TABLES)
		return NULL;		/* more tables than any game has: refuse quietly, the rest frame draws */
	strncpy (tables[i].name, name, AW_SKEL_TABLE_NAME - 1);
	{
		/* "progs/humanoid.awsk|f": a view of a table, its file loaded once with the table's (SKEL-TABLE-SHARED-
		 * FEMALE-52: the female groups live in the common table as "f:..."); its lookups try "f:" + name first */
		const char *bar = strchr (name, '|');
		if (bar)
		{
			char file[AW_SKEL_TABLE_NAME];
			const aw_skel_table_t *of;
			int n = (int)(bar - name), k;
			/* "progs/humanoid.awsk|d|f": several prefixes in order (DANCER-OWN-ANIM-IGNORED-53), "d:f:" */
			if (n <= 0 || n >= AW_SKEL_TABLE_NAME || !bar[1] || strstr (bar, "||") || bar[strlen (bar) - 1] == '|' ||
				strlen (bar + 1) + 2 > AW_SKEL_PREFIX || strchr (bar, ':'))
			{
				tables[i].failed = 1;
				Con_Printf ("Animation table %s: not a table view\n", name);
				return NULL;
			}
			memcpy (file, name, n);
			file[n] = 0;
			if (!(of = AW_SkelTableFor (file)))
			{
				tables[i].failed = 1;
				return NULL;
			}
			tables[i].table = *of;
			tables[i].table.prefix[0] = 0;
			for (k=1 ; ; k++)
			{
				if (!bar[k] || bar[k] == '|')
				{
					strcat (tables[i].table.prefix, ":");
					if (!bar[k])
						break;
					continue;
				}
				{
					char c[2] = {bar[k], 0};
					strcat (tables[i].table.prefix, c);
				}
			}
			return &tables[i].table;
		}
	}
	size = COM_FOpenFile ((char *)name, &f);
	if (!f || size <= 0)
	{
		tables[i].failed = 1;
		Con_Printf ("Animation table %s: not found\n", name);
		return NULL;
	}
	if (aw_skel_paged)
	{
		/* the index now, the frames when posed (the file stays open with the table) */
		if (!load_paged (i, f, size))
		{
			aw_skel_pages_t *p = (aw_skel_pages_t *)tables[i].table.pages;
			if (p)
			{
				p->f = NULL;
				pages_free (p);
			}
			if (tables[i].data)
				free (tables[i].data);
			tables[i].data = NULL;
			tables[i].table.pages = NULL;
			fclose (f);
			tables[i].failed = 1;
			Con_Printf ("Animation table %s: unreadable or invalid\n", name);
			return NULL;
		}
	}
	else
	{
		tables[i].data = table_alloc (size);
		tables[i].size = size;
		if (!tables[i].data || fread (tables[i].data, 1, size, f) != (size_t)size ||
			!AW_SkelParse (tables[i].data, size, &tables[i].table))
		{
			fclose (f);
			tables[i].failed = 1;
			Con_Printf ("Animation table %s: unreadable or invalid\n", name);
			return NULL;
		}
		fclose (f);
	}
	if (tables[i].table.base_name[0])
	{
		/* an appended table (version 3, CREATURE-APPENDED-TABLE-54): its base loaded once, shared (the creature's own
		 * file holds only its own groups; every other group is the base's) */
		char base[AW_SKEL_TABLE_NAME];
		const aw_skel_table_t *of;
		strcpy (base, tables[i].table.base_name);
		of = strcmp (base, name) ? AW_SkelTableFor (base) : NULL;
		if (!of || !AW_SkelAppend (&tables[i].table, of))
		{
			free (tables[i].data);
			tables[i].data = NULL;
			pages_free ((aw_skel_pages_t *)tables[i].table.pages);
			tables[i].table.pages = NULL;
			tables[i].failed = 1;
			Con_Printf ("Animation table %s: its base %s is missing or does not fit\n", name, base);
			return NULL;
		}
	}
	return &tables[i].table;
}
