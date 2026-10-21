/* aw_planetype.h: plane type at load (CHIM-PLANE-TYPE-ALL-SLANTED-46).
 *
 * Quake's fast paths (BoxOnPlaneSide, SV_HullPointContents, SV_RecursiveHullCheck, the renderer's
 * clip and node tests) use p[type] - dist instead of a dot product when type < 3 (PLANE_X/Y/Z). The
 * CHIM converter writes type 3 for every plane, so axial planes never took them. A plane whose
 * normal is exactly +X, +Y or +Z gets its axis here. Point tests (hull contents, traces, node sides)
 * give identical results: the dot product with such a normal is exactly that coordinate. BoxOnPlaneSide
 * differs only for a box that exactly touches the plane (its axial branch is Quake's own behaviour for
 * the axial planes of every id map). A negative axis normal stays as stored (Quake's axial types assume
 * a positive normal). */
#ifndef AW_PLANETYPE_H
#define AW_PLANETYPE_H

static int AW_PlaneType (const float *normal, int stored)
{
	int axis;
	if (stored < 3)
		return stored;
	for (axis = 0 ; axis < 3 ; axis++)
		if (normal[axis] == 1.0f && normal[(axis+1)%3] == 0.0f && normal[(axis+2)%3] == 0.0f)
			return axis;
	return stored;
}

#endif
