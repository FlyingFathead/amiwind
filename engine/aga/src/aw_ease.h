/* SPDX-License-Identifier: GPL-2.0-or-later
 * The one easing curve of the camera moves (docs/CAMERA_MARKS.md "Pan" and "Track", docs/HALLOWEEN.md): the
 * smoothstep, slow in and slow out, with no jump in its value or its slope. The Halloween director eases each shot's
 * progress with it (aw_halloween_rules.c AW_HalloweenShot); dbg cam pan and dbg cam track ease the speed of their
 * start and stop with it (aw_cam_rules.c AW_CamShotTravel: the speed rises along the curve, the distance covered is
 * its area). Header only: no state, nothing to link. */
#ifndef AW_EASE_H
#define AW_EASE_H

/* T 0..1 (clamped) -> 0..1, slope 0 at both ends. */
static __inline__ float AW_EaseSmooth(float t)
{
    if (!(t > 0))
        return 0;
    if (t > 1)
        return 1;
    return t * t * (3 - 2 * t);
}
/* The area under AW_EaseSmooth from 0 to T (clamped 0..1): T^3 - T^4/2, 1/2 at T = 1. A speed that rises along the
 * curve over E seconds to V covers V * E * AW_EaseSmoothArea(t / E) by time t. */
static __inline__ float AW_EaseSmoothArea(float t)
{
    if (!(t > 0))
        return 0;
    if (t > 1)
        t = 1;
    return t * t * t * (1 - t / 2);
}
#endif
