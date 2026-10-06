/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_INTERIOR_LIGHT_POLICY_H
#define AW_INTERIOR_LIGHT_POLICY_H
#include <string.h>
/* AW_Interior supplies the runtime scene classification, including caves,
 * ships, tombs and sectioned interiors. The authored dark test room is exempt
 * even when entered directly rather than through its explicit debug mode. */
static __inline__ int AW_GameplayInteriorLightPolicy(const char *name,int interior)
{
    return interior && name && strcmp(name,"torchtest");
}
#endif
