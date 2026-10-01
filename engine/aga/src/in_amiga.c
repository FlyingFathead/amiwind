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

void IN_Move (usercmd_t *cmd) {

  int mouse_x, mouse_y;

  if (!mouse_has_moved)
    return;

  // Consume pending movement while console is open without turning the player.
  mouse_has_moved = false;
  if(key_dest != key_game){
    if(key_dest==key_menu)AW_MenuMouse(mouseX,mouseY);
    old_mouse_x=old_mouse_y=0;return;
  }

  if(AW_ReaderActive()){AW_ReaderMouse(mouseX,mouseY);old_mouse_x=old_mouse_y=0;return;}
  if(AW_CharacterActive()){AW_CharacterMouse(mouseX,mouseY);old_mouse_x=old_mouse_y=0;return;}
  if(AW_GalleryModal()){AW_GalleryMouse(mouseX,mouseY);old_mouse_x=old_mouse_y=0;return;}

  if (m_filter.value)
  {
    mouse_x = ((mouseX << 2) + old_mouse_x) * 0.5;
    mouse_y = ((mouseY << 2) + old_mouse_y) * 0.5;
  }
  else
  {
   mouse_x = (mouseX << 2);
   mouse_y = (mouseY << 2);
  }

	old_mouse_x = (mouseX << 2);
	old_mouse_y = (mouseY << 2);

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
