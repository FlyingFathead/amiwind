/* SPDX-License-Identifier: GPL-2.0-or-later
 * WEREWOLF-TABLES-STAY-LOADED-68 (v0.0.68): one animation table given back on its own by the real table store
 * (engine/aga/src/aw_skel_load.c AW_SkelTableRelease) and loaded again by the next lookup, into the same slot. On the
 * builder's tables (tools/skeletal_actor.py write_table, tools/creature_tables.py to_appended), written by
 * tests/test_werewolf_change.py into the folder given as the argument: a paged table of 100 frames (the werewolf's
 * part: 7 chunks of 16 frames), a view of it ("|f"), a second table and an appended table resting on that one. 51 times:
 * the table loaded, every frame posed (every chunk read), kept while a model is on it or on its view, given back (its
 * index, the frames read, its open file and its view), not held after; the store's index bytes, frame bytes and open
 * files as before the first load; the table loaded again into the same slot poses the same; the other tables
 * untouched. A table an appended table rests on, a view's name and a table never loaded are not given back. Fails on
 * the engine before v0.0.68: the store had no way to give one table back (every table kept for the session). */
#include "quakedef.h"
#include "aw_skel.h"
#include <assert.h>
#include <math.h>

long AW_SkelTableRelease (const char *name, int (*in_use) (const aw_skel_table_t *t));
unsigned long AW_SkelTablesRelease (void);
void AW_SkelTablesBytes (unsigned long *held, unsigned long *disk, unsigned long *index);

static const char *dir;
static int opens, closes;
int COM_FOpenFile (char *name, FILE **file)
{
    char path[512];
    long size;
    snprintf (path, sizeof(path), "%s/%s", dir, name);
    *file = fopen (path, "rb");
    if (!*file)
        return -1;
    opens++;
    fseek (*file, 0, SEEK_END);
    size = ftell (*file);
    fseek (*file, 0, SEEK_SET);
    return (int)size;
}
int __real_fclose (FILE *f);
int __wrap_fclose (FILE *f);
int __wrap_fclose (FILE *f)
{
    closes++;
    return __real_fclose (f);
}
void Con_Printf (char *fmt, ...)
{
    va_list a;
    va_start (a, fmt);
    vprintf (fmt, a);
    va_end (a);
}

/* the table a loaded model points into (aw_view.c asks its model table; here one model at most) */
static const aw_skel_table_t *model_on;
static int in_use (const aw_skel_table_t *t) {return t == model_on;}

/* every frame posed (a paged table reads each of its chunks); the sum of one bone's world matrix over the frames */
static double pose_all (const aw_skel_table_t *t)
{
    static float world[AW_SKEL_MAX_BONES][3][4];
    double sum = 0;
    int f, r, c;
    for (f=0 ; f<t->frames ; f++)
    {
        AW_SkelPose (t, (float)f, world);
        for (r=0 ; r<3 ; r++)
            for (c=0 ; c<4 ; c++)
                sum += world[t->bones - 1][r][c] * (1 + f % 7);
    }
    return sum;
}

int main (int argc, char **argv)
{
    const aw_skel_table_t *human, *beast, *wolf, *view, *first = NULL, *first_view = NULL;
    unsigned long held0, disk0, index0, held, disk, index;
    double human_pose, wolf_pose = 0, pose;
    long given;
    int cycle, open0;
    assert (argc == 2);
    dir = argv[1];
    /* the tables that stay: a table and an appended table resting on it (a creature on the humanoid table) */
    human = AW_SkelTableFor ("progs/human.awsk");
    beast = AW_SkelTableFor ("progs/beast.awsk");
    assert (human && beast && beast->more == human && human->row_of && human->pages);
    human_pose = pose_all (human);
    pose_all (beast);
    AW_SkelTablesBytes (&held0, &disk0, &index0);
    open0 = opens - closes;
    printf ("before: index %lu bytes, frames %lu of %lu bytes read, %d files open\n", index0, held0, disk0, open0);
    assert (open0 == 2 && held0 > 0 && held0 == disk0);
    for (cycle=0 ; cycle<51 ; cycle++)
    {
        wolf = AW_SkelTableFor ("progs/wolf.awsk");
        view = AW_SkelTableFor ("progs/wolf.awsk|f");
        assert (wolf && view && wolf->frames == 100 && view->frames == 100 && !strcmp (view->prefix, "f:"));
        assert (wolf->pages && wolf->row_of && opens - closes == open0 + 1);
        if (!first)
        {
            first = wolf;
            first_view = view;
        }
        /* loaded again into its own slot (a pointer kept by a caller still means this table) and its view too */
        assert (wolf == first && view == first_view);
        pose = pose_all (wolf);
        if (!cycle)
            wolf_pose = pose;
        assert (fabs (pose - wolf_pose) < 1e-6 * (1 + fabs (wolf_pose)));
        AW_SkelTablesBytes (&held, &disk, &index);
        assert (index > index0 && held == held0 + (unsigned long)wolf->frames * (unsigned long)wolf->row &&
                disk == disk0 + (unsigned long)wolf->frames * (unsigned long)wolf->row);
        if (!cycle)
            printf ("loaded and every frame posed: index %lu bytes, frames %lu of %lu bytes read, %d files open\n", index,
                    held, disk, opens - closes);
        /* kept while a model is on it or on its view: nothing given back */
        model_on = wolf;
        assert (AW_SkelTableRelease ("progs/wolf.awsk", in_use) == -1);
        model_on = view;
        assert (AW_SkelTableRelease ("progs/wolf.awsk", in_use) == -1);
        AW_SkelTablesBytes (&held, &disk, &index);
        assert (held == held0 + (unsigned long)wolf->frames * (unsigned long)wolf->row && opens - closes == open0 + 1);
        /* no model on it: given back, the index and every frame read, its file closed, its view with it */
        model_on = NULL;
        given = AW_SkelTableRelease ("progs/wolf.awsk", in_use);
        assert (given > 0 && (unsigned long)given == (index - index0) + (held - held0));
        AW_SkelTablesBytes (&held, &disk, &index);
        if (!cycle)
            printf ("given back: %ld bytes; index %lu bytes, frames %lu of %lu bytes read, %d files open\n", given, index,
                    held, disk, opens - closes);
        assert (index == index0 && held == held0 && disk == disk0 && opens - closes == open0);
        assert (AW_SkelTableRelease ("progs/wolf.awsk", in_use) == 0);    /* not held now */
        /* the other tables untouched */
        assert (AW_SkelTableFor ("progs/human.awsk") == human && AW_SkelTableFor ("progs/beast.awsk") == beast);
        assert (fabs (pose_all (human) - human_pose) < 1e-9 * (1 + fabs (human_pose)));
    }
    printf ("after 51 loads and 51 give-backs: index %lu bytes, frames %lu of %lu bytes read, %d files open (%d opened, "
            "%d closed)\n", index, held, disk, opens - closes, opens, closes);
    /* the base of an appended table, a view's name and a table never loaded: nothing given back */
    assert (AW_SkelTableRelease ("progs/human.awsk", in_use) == -1);
    assert (AW_SkelTableRelease ("progs/wolf.awsk|f", in_use) == 0);
    assert (AW_SkelTableRelease ("progs/none.awsk", in_use) == 0);
    /* a view asked first after the give-back loads its table again */
    view = AW_SkelTableFor ("progs/wolf.awsk|f");
    assert (view == first_view && AW_SkelTableFor ("progs/wolf.awsk") == first && opens - closes == open0 + 1);
    /* the whole store given back (aw_skel_release.c, before a room) still closes every file */
    AW_SkelTablesRelease ();
    AW_SkelTablesBytes (&held, &disk, &index);
    assert (opens == closes && !held && !disk && !index);
    wolf = AW_SkelTableFor ("progs/wolf.awsk");
    assert (wolf && fabs (pose_all (wolf) - wolf_pose) < 1e-6 * (1 + fabs (wolf_pose)));
    AW_SkelTablesRelease ();
    printf ("whole store given back after: %d files opened, %d closed\n", opens, closes);
    assert (opens == closes);
    return 0;
}
