/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/

#include "quakedef.h"
#include "aw_character.h"

// Mouse globals set by sys_amiga.c
extern int mouseX;
extern int mouseY;
extern qboolean mouse_has_moved;
extern qboolean V_ExplicitPitchCentering (void);

cvar_t	m_filter = {"m_filter","1"};

void IN_Init (void)
{
    Cvar_RegisterVariable (&m_filter);
}

void IN_Shutdown (void)
{

}

void IN_Commands (void)
{
    // NovaCoder's version removed joypad support - nothing to do here
}


static int old_mouse_x = 0;
static int old_mouse_y = 0;

/* Intuition supplies signed WORD deltas. Bound the accumulated total too:
 * x4 scaling is [-131072,131068], and the filter sum fits a 32-bit int. */
static int IN_AWMouseBound(int value) {
  if(value < -32768)return -32768;
  if(value > 32767)return 32767;
  return value;
}
static int IN_AWMouseSum(int pending, int delta) {
  pending=IN_AWMouseBound(pending);delta=IN_AWMouseBound(delta);
  if(delta>0 && pending>32767-delta)return 32767;
  if(delta<0 && pending< -32768-delta)return -32768;
  return pending+delta;
}
void IN_AWMouseReset(void) {
  mouseX=mouseY=0;mouse_has_moved=false;
  old_mouse_x=old_mouse_y=0;
}
void IN_AWMouseEvent(int dx, int dy) {
  dx=IN_AWMouseBound(dx);dy=IN_AWMouseBound(dy);
  /* UI movement must precede the next button in the SAME Intuition batch.
   * Apply each delta separately so clamping and drag order are preserved. */
  if(key_dest!=key_game){
    IN_AWMouseReset();
    if(AW_WorldUIActive())AW_WorldUIMouse(dx,dy);
    else if(key_dest==key_menu)AW_MenuMouse(dx,dy);
    return;
  }
  if(AW_ReaderActive()){IN_AWMouseReset();AW_ReaderMouse(dx,dy);return;}
  if(AW_CharacterActive()){IN_AWMouseReset();AW_CharacterMouse(dx,dy);return;}
  if(AW_GalleryModal()){IN_AWMouseReset();AW_GalleryMouse(dx,dy);return;}
  mouseX=IN_AWMouseSum(mouse_has_moved?mouseX:0,dx);
  mouseY=IN_AWMouseSum(mouse_has_moved?mouseY:0,dy);
  mouse_has_moved=true;
}

void IN_Move (usercmd_t *cmd) {

  int mouse_x, mouse_y, dx, dy;

  if (!mouse_has_moved) {
    /* +mlook is explicit input even when the user has not moved the mouse. */
    if (key_dest == key_game && !AW_ReaderActive() &&
        !AW_CharacterActive() && !AW_GalleryModal() &&
        (in_mlook.state & 1) && !V_ExplicitPitchCentering())
      V_StopPitchDrift ();
    return;
  }

  dx=mouseX;dy=mouseY;mouseX=mouseY=0;mouse_has_moved=false;
  /* Only gameplay deltas reach here. A context change discards them; it
   * must not reinterpret old view movement as motion in a newly opened UI. */
  if(key_dest!=key_game || AW_ReaderActive() || AW_CharacterActive() || AW_GalleryModal()){
    old_mouse_x=old_mouse_y=0;return;
  }

  if (m_filter.value)
  {
    mouse_x = ((dx * 4) + old_mouse_x) * 0.5;
    mouse_y = ((dy * 4) + old_mouse_y) * 0.5;
  }
  else
  {
   mouse_x = (dx * 4);
   mouse_y = (dy * 4);
  }

	old_mouse_x = (dx * 4);
	old_mouse_y = (dy * 4);

	mouse_x *= sensitivity.value;
	mouse_y *= sensitivity.value;


  /* add mouse X/Y movement to cmd */
  if ((in_strafe.state & 1) || (lookstrafe.value && (in_mlook.state & 1)))
    cmd->sidemove += m_side.value * mouse_x;
  else
    cl.viewangles[YAW] -= m_yaw.value * mouse_x;

  if (in_mlook.state & 1)
    V_StopPitchDrift ();

  if ((in_mlook.state & 1) && !(in_strafe.state & 1)) {
    cl.viewangles[PITCH] += m_pitch.value * mouse_y;
    if (cl.viewangles[PITCH] > 80)
      cl.viewangles[PITCH] = 80;
    if (cl.viewangles[PITCH] < -70)
      cl.viewangles[PITCH] = -70;
  } else {
    if ((in_strafe.state & 1) && noclip_anglehack)
      cmd->upmove -= m_forward.value * mouse_y;
    else
      cmd->forwardmove -= m_forward.value * mouse_y;
  }
}
