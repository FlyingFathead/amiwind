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
// console.c

#ifdef NeXT
#include <libc.h>
#endif
#if defined(__STORM__) || defined(__VBCC__)
#include <stdio.h>
#else
#ifndef _MSC_VER
#include <unistd.h>
#endif
#include <fcntl.h>
#endif
#include "quakedef.h"
#include "aw_remote.h"

void Con_Linefeed (void);

int 		con_linewidth;
int con_fullscreen;

float		con_cursorspeed = 4;

#define		CON_TEXTSIZE	16384

qboolean 	con_forcedup;		// because no entities to refresh

int			con_totallines;		// total lines in console scrollback
int			con_backscroll;		// lines up from bottom to display
int			con_current;		// where next message will be printed
int			con_x;				// offset in current line for next print
char		*con_text=0;

cvar_t		con_notifytime = {"con_notifytime","3"};		//seconds

#define	NUM_CON_TIMES 4
float		con_times[NUM_CON_TIMES];	// realtime time the line was generated
								// for transparent notify lines

int			con_vislines;

qboolean	con_debuglog;

#define		MAXCMDLINE	256
extern	char	key_lines[32][MAXCMDLINE];
extern	int		edit_line;
extern	int		history_line;
extern	int		key_linepos;


qboolean	con_initialized;

int			con_notifylines;		// scan lines to clear for notify lines

extern void M_Menu_Main_f (void);

/*
================
Con_ToggleConsole_f
================
*/
void Con_ToggleConsole_f (void)
{
	if (key_dest == key_console)
	{
		if (cls.state == ca_connected)
		{
			key_dest = key_game;
			key_lines[edit_line][1] = 0;	// clear any typing
			key_linepos = 1;
		}
		else
		{
			M_Menu_Main_f ();
		}
	}
	else {
		con_fullscreen=0;key_dest = key_console;
		AW_PhotoConsoleReminder();	// F10 in photo mode says how to leave it
	}
	// AmiWind (CONSOLE-HISTORY-EMPTY-32): Up starts from the newest command
	// each time the console opens or closes, not from where the last
	// history walk stopped
	history_line = edit_line;

	SCR_EndLoadingPlaque ();
	memset (con_times, 0, sizeof(con_times));
}

/* F10: half, full, closed. Escape still uses the direct close toggle. */
void Con_CycleConsole_f(void) {
    if(key_dest==key_console && !con_fullscreen){
        con_fullscreen=1;SCR_EndLoadingPlaque();Con_ClearNotify();
    }else Con_ToggleConsole_f();
}
void Con_ToggleFullscreen_f(void) {
    con_fullscreen=(key_dest==key_console)?!con_fullscreen:1;
    key_dest=key_console;SCR_EndLoadingPlaque();Con_ClearNotify();
}
int Con_ScrollPage(void) {
    int n=con_vislines/AW_ConsoleCharHeight()-3;return n>1?n:1;
}
int Con_ScrollMax(void) {
    int n=con_totallines-con_vislines/AW_ConsoleCharHeight()-1;
    return n>0?n:0;
}

/*
================
Con_Clear_f
================
*/
void Con_Clear_f (void)
{
	if (con_text)
		Q_memset (con_text, ' ', CON_TEXTSIZE);
}


/*
================
Con_ClearNotify
================
*/
void Con_ClearNotify (void)
{
	int		i;

	for (i=0 ; i<NUM_CON_TIMES ; i++)
		con_times[i] = 0;
}


/*
================
Con_MessageMode_f
================
*/
extern qboolean team_message;

void Con_MessageMode_f (void)
{
	key_dest = key_message;
	team_message = false;
}


/*
================
Con_MessageMode2_f
================
*/
void Con_MessageMode2_f (void)
{
	key_dest = key_message;
	team_message = true;
}


/*
================
Con_CheckResize

If the line width has changed, reformat the buffer.
================
*/
void Con_CheckResize (void)
{
    int width,oldwidth,oldlines,i,j,length,row,oldcurrent,oldx,lastx=0;
    char tbuf[CON_TEXTSIZE];
    width=vid.width/AW_ConsoleCharWidth()-2;
    if(width<1)width=38;
    if(width>MAXCMDLINE-2)width=MAXCMDLINE-2;
    if(width==con_linewidth)return;
    oldwidth=con_linewidth;oldlines=con_totallines;oldcurrent=con_current;oldx=con_x;
    memcpy(tbuf,con_text,CON_TEXTSIZE);
    con_linewidth=width;con_totallines=CON_TEXTSIZE/width;
    memset(con_text,' ',CON_TEXTSIZE);con_current=con_totallines-1;con_x=0;
    /* Rewrap whole old rows, keeping their right-hand text and newest history.
     * Blank padding is discarded; original soft wraps remain line boundaries. */
    if(oldwidth>0 && oldlines>0)for(i=0;i<oldlines;i++) {
        row=(oldcurrent+1+i)%oldlines;
        length=oldwidth;while(length>0 && tbuf[row*oldwidth+length-1]==' ')length--;
        if(!length)continue;
        con_x=0;Con_Linefeed();
        for(j=0;j<length;j++) {
            if(con_x==width){con_x=0;Con_Linefeed();}
            con_text[(con_current%con_totallines)*width+con_x++]=tbuf[row*oldwidth+j];
        }
        lastx=con_x;con_x=0;
    }
    if(oldx>0)con_x=lastx<width?lastx:0;
    Con_ClearNotify();con_backscroll=0;
}


/*
================
Con_Init
================
*/
void Con_Init (void)
{
#define MAXGAMEDIRLEN	1000
	char	temp[MAXGAMEDIRLEN+1];
	char	*t2 = "/qconsole.log";

	con_debuglog = COM_CheckParm("-condebug");

	if (con_debuglog)
	{
		if (strlen (com_gamedir) < (MAXGAMEDIRLEN - strlen (t2)))
		{
			sprintf (temp, "%s%s", com_gamedir, t2);
#if defined(__STORM__) || defined(__VBCC__)
			remove (temp);
#else
			unlink (temp);
#endif
		}
	}

	con_text = Hunk_AllocName (CON_TEXTSIZE, "context");
	Q_memset (con_text, ' ', CON_TEXTSIZE);
	con_linewidth = -1;
	Con_CheckResize ();

	Con_Printf ("Console initialized.\n");

//
// register our commands
//
	Cvar_RegisterVariable (&con_notifytime);

	Cmd_AddCommand ("toggleconsole", Con_ToggleConsole_f);
    Cmd_AddCommand ("aw_console_cycle", Con_CycleConsole_f);
	Cmd_AddCommand ("aw_console_fullscreen", Con_ToggleFullscreen_f);
	Cmd_AddCommand ("messagemode", Con_MessageMode_f);
	Cmd_AddCommand ("messagemode2", Con_MessageMode2_f);
	Cmd_AddCommand ("clear", Con_Clear_f);
	con_initialized = true;
}


/*
===============
Con_Linefeed
===============
*/
void Con_Linefeed (void)
{
	if(con_backscroll>0 && con_backscroll<Con_ScrollMax())con_backscroll++;
	con_x = 0;
	con_current++;
	Q_memset (&con_text[(con_current%con_totallines)*con_linewidth]
	, ' ', con_linewidth);
}

/*
================
Con_Print

Handles cursor positioning, line wrapping, etc
All console printing must go through this in order to be logged to disk
If no console is visible, the notify window will pop up.
================
*/
void Con_Print (char *txt)
{
	int		y;
	int		c, l;
	static int	cr;
	int		mask;

	if (txt[0] == 1)
	{
		mask = 128;		// go to colored text
		S_LocalSound ("misc/talk.wav");
	// play talk wav
		txt++;
	}
	else if (txt[0] == 2)
	{
		mask = 128;		// go to colored text
		txt++;
	}
	else
		mask = 0;


	while ( (c = *txt) )
	{
	// count word length
		for (l=0 ; l< con_linewidth ; l++)
			if ( txt[l] <= ' ')
				break;

	// word wrap
		if (l != con_linewidth && (con_x + l > con_linewidth) )
			con_x = 0;

		txt++;

		if (cr)
		{
			con_current--;
			cr = false;
		}


		if (!con_x)
		{
			Con_Linefeed ();
		// mark time for transparent overlay
			if (con_current >= 0)
				con_times[con_current % NUM_CON_TIMES] = realtime;
		}

		switch (c)
		{
		case '\n':
			con_x = 0;
			break;

		case '\r':
			con_x = 0;
			cr = 1;
			break;

		default:	// display character and advance
			y = con_current % con_totallines;
			con_text[y*con_linewidth+con_x] = c | mask;
			con_x++;
			if (con_x >= con_linewidth)
				con_x = 0;
			break;
		}

	}
}


/*
================
Con_DebugLog
================
*/
void Con_DebugLog(char *file, char *fmt, ...)
{
    va_list argptr;
    static char data[1024];
#if defined(__STORM__) || defined(__VBCC__)
    FILE *fd;
#else
    int fd;
#endif

    va_start(argptr, fmt);
    vsprintf(data, fmt, argptr);
    va_end(argptr);
#if defined(__STORM__) || defined(__VBCC__)
    fd = fopen (file, "a");
    fwrite (data, 1, strlen(data), fd);
    fclose (fd);
#else
    fd = open(file, O_WRONLY | O_CREAT | O_APPEND, 0666);
    if (fd < 0)
        return;
    /* The Amiga C library does not honour O_APPEND: without this seek every
     * message overwrote the start of the file (REMOTE-CONSOLE-APPEND-31). */
    lseek(fd, 0, SEEK_END);
    write(fd, data, strlen(data));
    close(fd);
#endif
}


/*
================
Con_Printf

Handles cursor positioning, line wrapping, etc
================
*/
#define	MAXPRINTMSG	4096
// FIXME: make a buffer size safe vsprintf?
void Con_Printf (char *fmt, ...)
{
	va_list		argptr;
	char		msg[MAXPRINTMSG];
	static qboolean	inupdate;

	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);

// also echo to debugging console
	Sys_Printf ("%s", msg);

// log all messages to file
	if (con_debuglog)
		Con_DebugLog(va("%s/qconsole.log",com_gamedir), "%s", msg);
	else if (AW_RemoteLogging ())
		Con_DebugLog((char *)AW_RemoteConsoleLog (), "%s", msg);

	if (!con_initialized)
		return;

	if (cls.state == ca_dedicated)
		return;		// no graphics mode

// write it to the scrollable buffer
	Con_Print (msg);

// update the screen if the console is displayed
	if (cls.signon != SIGNONS && !scr_disabled_for_loading )
	{
	// protect against infinite loop if something in SCR_UpdateScreen calls
	// Con_Printd
		if (!inupdate)
		{
			inupdate = true;
			SCR_UpdateScreen ();
			inupdate = false;
		}
	}
}

/*
================
Con_DPrintf

A Con_Printf that only shows up if the "developer" cvar is set
================
*/
void Con_DPrintf (char *fmt, ...)
{
	va_list		argptr;
	char		msg[MAXPRINTMSG];

	if (!developer.value)
		return;			// don't confuse non-developers with techie stuff...

	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);

	Con_Printf ("%s", msg);
}


/*
==================
Con_SafePrintf

Okay to call even when the screen can't be updated
==================
*/
void Con_SafePrintf (char *fmt, ...)
{
	va_list		argptr;
	char		msg[1024];
	int			temp;

	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);

	temp = scr_disabled_for_loading;
	scr_disabled_for_loading = true;
	Con_Printf ("%s", msg);
	scr_disabled_for_loading = temp;
}


/*
==============================================================================

DRAWING

==============================================================================
*/


/*
================
Con_DrawInput

The input line scrolls horizontally if typing goes beyond the right edge
================
*/
void Con_DrawInput (void)
{
	int		y;
	int		i;
	char	*text;

	if (key_dest != key_console && !con_forcedup)
		return;		// don't draw anything

	// AmiWind terminal line editor: the cursor sits inside the line, so draw
	// from a copy and leave the text after the cursor in place; the cursor
	// blinks over the character under it
	if (Key_ConsoleTerminal ())
	{
		char	line[MAXCMDLINE+1];
		int		len, start;
		Q_strcpy (line, key_lines[edit_line]);
		len = Q_strlen (line);
		for (i=len ; i<MAXCMDLINE ; i++)
			line[i] = ' ';
		line[MAXCMDLINE] = 0;
		if ((int)(realtime*con_cursorspeed)&1)
			line[key_linepos] = 11;
		else if (key_linepos >= len)
			line[key_linepos] = 10;
		start = key_linepos >= con_linewidth ? 1 + key_linepos - con_linewidth : 0;
		y = con_vislines-2*AW_ConsoleCharHeight();
		for (i=0 ; i<con_linewidth && start+i<MAXCMDLINE ; i++)
			AW_ConsoleCharacter ((i+1)*AW_ConsoleCharWidth(), y, line[start+i]);
		return;
	}

	text = key_lines[edit_line];

// add the cursor frame
	text[key_linepos] = 10+((int)(realtime*con_cursorspeed)&1);

// fill out remainder with spaces
	for (i=key_linepos+1 ; i< con_linewidth ; i++)
		text[i] = ' ';

//	prestep if horizontally scrolling
	if (key_linepos >= con_linewidth)
		text += 1 + key_linepos - con_linewidth;

// draw it
	y = con_vislines-2*AW_ConsoleCharHeight();

	for (i=0 ; i<con_linewidth ; i++)
		AW_ConsoleCharacter ((i+1)*AW_ConsoleCharWidth(), y, text[i]);

// remove cursor
	key_lines[edit_line][key_linepos] = 0;
}


/*
================
Con_DrawNotify

Draws the last few lines of output transparently over the game top
================
*/
void Con_DrawNotify (void)
{
	int		x, v;
	char	*text;
	int		i;
	float	time;
	extern char chat_buffer[];

	v = 0;
	for (i= con_current-NUM_CON_TIMES+1 ; i<=con_current ; i++)
	{
		if (i < 0)
			continue;
		time = con_times[i % NUM_CON_TIMES];
		if (time == 0)
			continue;
		time = realtime - time;
		if (time > con_notifytime.value)
			continue;
		text = con_text + (i % con_totallines)*con_linewidth;

		clearnotify = 0;
		scr_copytop = 1;

		for (x = 0 ; x < con_linewidth ; x++)
			AW_ConsoleCharacter ((x+1)*AW_ConsoleCharWidth(), v, text[x]);

		v += AW_ConsoleCharHeight();
	}


	if (key_dest == key_message)
	{
		clearnotify = 0;
		scr_copytop = 1;

		x = 0;

		Draw_String (8, v, "say:");
		while(chat_buffer[x])
		{
			Draw_Character ( (x+5)<<3, v, chat_buffer[x]);
			x++;
		}
		Draw_Character ( (x+5)<<3, v, 10+((int)(realtime*con_cursorspeed)&1));
		v += 8;
	}

	if (v > con_notifylines)
		con_notifylines = v;
}

/*
================
Con_DrawConsole

Draws the console with the solid background
The typing input line at the bottom should only be drawn if typing is allowed
================
*/
void Con_DrawConsole (int lines, qboolean drawinput)
{
	int				i, x, y;
	int				rows;
	char			*text;
	int				j;

	if (lines <= 0)
		return;

// draw the background
	Draw_ConsoleBackground (lines);

// draw the text
	con_vislines = lines;

	rows = lines/AW_ConsoleCharHeight()-2;		// rows of text to draw
	y = lines - (rows+2)*AW_ConsoleCharHeight();	// may start slightly negative

	for (i= con_current - rows + 1 ; i<=con_current ; i++, y+=AW_ConsoleCharHeight() )
	{
		j = i - con_backscroll;
		if (j<0)
			j = 0;
		text = con_text + (j % con_totallines)*con_linewidth;

		for (x=0 ; x<con_linewidth ; x++)
			AW_ConsoleCharacter ((x+1)*AW_ConsoleCharWidth(), y, text[x]);
	}

// draw the input prompt, user text, and cursor if desired
	if (drawinput)
		Con_DrawInput ();
}


/*
==================
Con_NotifyBox
==================
*/
void Con_NotifyBox (char *text)
{
	double		t1, t2;

// during startup for sound / cd warnings
	Con_Printf("\n\n\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n");

	Con_Printf (text);

	Con_Printf ("Press a key.\n");
	Con_Printf("\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n");

	key_count = -2;		// wait for a key down and up
	key_dest = key_console;

	do
	{
		t1 = Sys_FloatTime ();
		SCR_UpdateScreen ();
		Sys_SendKeyEvents ();
		t2 = Sys_FloatTime ();
		realtime += t2-t1;		// make the cursor blink
	} while (key_count < 0);

	Con_Printf ("\n");
	key_dest = key_game;
	realtime = 0;				// put the cursor back to invisible
}
