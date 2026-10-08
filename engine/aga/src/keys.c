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

/* Native raw keys, including extended PC/Amiga keyboard navigation.
 * Values follow the SDK libraries/keymap.h definitions. */
int Key_AmigaRaw(int raw) {
    static const int xlate[0x68] = {
    '`', '1', '2', '3', '4', '5', '6', '7',
    '8', '9', '0', '-', '=', '\\', 0, '0',
    'q', 'w', 'e', 'r', 't', 'y', 'u', 'i',
    'o', 'p', K_F11, K_F12, 0, '0', '2', '3',
    'a', 's', 'd', 'f', 'g', 'h', 'j', 'k',
    'l', ';', '\'', K_ENTER, 0, '4', '5', '6',
    '<', 'z', 'x', 'c', 'v', 'b', 'n', 'm',
    ',', '.', '/', 0, '.', '7', '8', '9',
    K_SPACE, K_BACKSPACE, K_TAB, K_ENTER, K_ENTER, K_ESCAPE, K_DEL,
    0, 0, 0, '-', 0, K_UPARROW, K_DOWNARROW, K_RIGHTARROW, K_LEFTARROW,
    K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8,
    K_F9, K_F10, '(', ')', '/', '*', '=', K_PAUSE,
    K_SHIFT, K_SHIFT, 0, K_CTRL, K_ALT, K_ALT, 0, 0
};
    raw&=0x7f;
    /* FS-UAE's classic layout sends PageDown as Right Amiga. The supplied
     * preset instead uses its explicit unused-key actions 68/69. */
    if(raw==0x48 || raw==0x68)return K_PGUP;
    if(raw==0x49 || raw==0x69)return K_PGDN;
    if(raw==0x70)return K_HOME;
    if(raw==0x71)return K_END;
    /* FS-UAE has no action for 0x70/0x71; the supplied preset sends PC Home
     * and End as its unused-key actions 6a/6c (KEYS-AMIGA-EDIT-32). */
    if(raw==0x6a)return K_HOME;
    if(raw==0x6c)return K_END;
    return raw<0x68?xlate[raw]:0;
}


/*

key up events are sent even if in console mode

*/


#define		MAXCMDLINE	256
char	key_lines[32][MAXCMDLINE];
int		key_linepos;
int		shift_down=false;
static int caps_down;
int		key_lastpress;

int		edit_line=0;
int		history_line=0;

/* AmiWind terminal line editor (aw_console_mode, default on). The edit line
 * stays a terminated string; key_linepos is the cursor inside it. The line
 * being typed is kept while the history is browsed (console_draft), and the
 * history is saved in the game directory after each new entry. */
static cvar_t aw_console_mode={"aw_console_mode","1",true,false,1};
static char console_draft[MAXCMDLINE];
static char history_path[MAX_OSPATH];
#define HISTORY_FILE "console-history.txt"

keydest_t	key_dest;

int		key_count;			// incremented every key event

char	*keybindings[256];
qboolean	consolekeys[256];	// if true, can't be rebound while in console
qboolean	menubound[256];	// if true, can't be rebound while in menu
int		keyshift[256];		// key to map to if shift held down in console
int		key_repeats[256];	// if > 1, it is autorepeating
qboolean	keydown[256];

/* Intuition qualifiers are authoritative, even after a lost key-up event.
 * Values are from the NDK devices/inputevent.h; Amiga keys are not Ctrl.
 * Called outside the input.device interrupt, before dispatching raw input. */
void Key_AmigaQualifiers(unsigned int qualifier)
{
    int shift=(qualifier&3)!=0,control=(qualifier&8)!=0,alt=(qualifier&48)!=0;
    if(keydown[K_SHIFT]!=shift || shift_down!=shift)Key_Event(K_SHIFT,shift);
    if(keydown[K_CTRL]!=control)Key_Event(K_CTRL,control);
    if(keydown[K_ALT]!=alt)Key_Event(K_ALT,alt);
    caps_down=(qualifier&4)!=0;
}

typedef struct
{
    char	*name;
    int		keynum;
} keyname_t;

keyname_t keynames[] =
{
    {"TAB", K_TAB},
    {"ENTER", K_ENTER},
    {"ESCAPE", K_ESCAPE},
    {"SPACE", K_SPACE},
    {"BACKSPACE", K_BACKSPACE},
    {"UPARROW", K_UPARROW},
    {"DOWNARROW", K_DOWNARROW},
    {"LEFTARROW", K_LEFTARROW},
    {"RIGHTARROW", K_RIGHTARROW},

    {"ALT", K_ALT},
    {"CTRL", K_CTRL},
    {"SHIFT", K_SHIFT},

    {"F1", K_F1},
    {"F2", K_F2},
    {"F3", K_F3},
    {"F4", K_F4},
    {"F5", K_F5},
    {"F6", K_F6},
    {"F7", K_F7},
    {"F8", K_F8},
    {"F9", K_F9},
    {"F10", K_F10},
    {"F11", K_F11},
    {"F12", K_F12},

    {"INS", K_INS},
    {"DEL", K_DEL},
    {"PGDN", K_PGDN},
    {"PGUP", K_PGUP},
    {"HOME", K_HOME},
    {"END", K_END},

    {"MOUSE1", K_MOUSE1},
    {"MOUSE2", K_MOUSE2},
    {"MOUSE3", K_MOUSE3},

    {"JOY1", K_JOY1},
    {"JOY2", K_JOY2},
    {"JOY3", K_JOY3},
    {"JOY4", K_JOY4},

    {"AUX1", K_AUX1},
    {"AUX2", K_AUX2},
    {"AUX3", K_AUX3},
    {"AUX4", K_AUX4},
    {"AUX5", K_AUX5},
    {"AUX6", K_AUX6},
    {"AUX7", K_AUX7},
    {"AUX8", K_AUX8},
    {"AUX9", K_AUX9},
    {"AUX10", K_AUX10},
    {"AUX11", K_AUX11},
    {"AUX12", K_AUX12},
    {"AUX13", K_AUX13},
    {"AUX14", K_AUX14},
    {"AUX15", K_AUX15},
    {"AUX16", K_AUX16},
    {"AUX17", K_AUX17},
    {"AUX18", K_AUX18},
    {"AUX19", K_AUX19},
    {"AUX20", K_AUX20},
    {"AUX21", K_AUX21},
    {"AUX22", K_AUX22},
    {"AUX23", K_AUX23},
    {"AUX24", K_AUX24},
    {"AUX25", K_AUX25},
    {"AUX26", K_AUX26},
    {"AUX27", K_AUX27},
    {"AUX28", K_AUX28},
    {"AUX29", K_AUX29},
    {"AUX30", K_AUX30},
    {"AUX31", K_AUX31},
    {"AUX32", K_AUX32},

    {"PAUSE", K_PAUSE},

    {"MWHEELUP", K_MWHEELUP},
    {"MWHEELDOWN", K_MWHEELDOWN},
    {"ALT+M", K_ALTM},

    {"SEMICOLON", ';'},	// because a raw semicolon seperates commands

    {NULL,0}
};

/*
==============================================================================

            LINE TYPING INTO THE CONSOLE

==============================================================================
*/


/*
====================
Key_Console

Interactive line editing and console scrollback
====================
*/
int Key_ConsoleTerminal(void)
{
    char *s=aw_console_mode.string;
    if(!Q_strcasecmp(s,"true") || !Q_strcasecmp(s,"on") || !Q_strcasecmp(s,"yes"))return 1;
    if(!Q_strcasecmp(s,"false") || !Q_strcasecmp(s,"off") || !Q_strcasecmp(s,"no"))return 0;
    return aw_console_mode.value!=0;
}

/* Saved history: one command per line, oldest first, the ring's 31 entries.
 * Written whole (a few KiB at most) only when Enter adds an entry. */
static void console_history_write(void)
{
    FILE *f;int i,line;
    if(!history_path[0])return;
    f=fopen(history_path,"w");
    if(!f)return;
    for(i=1;i<32;i++){
        line=(edit_line+i)&31;
        if(key_lines[line][1])fprintf(f,"%s\n",key_lines[line]+1);
    }
    fclose(f);
}

static void console_history_read(void)
{
    FILE *f;char text[MAXCMDLINE+2];int total=0,skip,n=0,len;
    if(!history_path[0] || !(f=fopen(history_path,"r")))return;
    while(fgets(text,sizeof text,f))total++;
    skip=total>31?total-31:0;
    rewind(f);
    while(n<31 && fgets(text+1,sizeof text-1,f)){
        if(skip>0){skip--;continue;}
        len=strlen(text+1);
        while(len && (text[len]=='\n' || text[len]=='\r'))text[len--]=0;
        if(!text[1])continue;
        text[0]=']';text[MAXCMDLINE-1]=0;
        strcpy(key_lines[n++],text);
    }
    fclose(f);
    if(!n)return;
    edit_line=history_line=n;
    key_lines[edit_line][0]=']';key_lines[edit_line][1]=0;key_linepos=1;
}

void Key_ConsoleInit(const char *dir)
{
    Cvar_RegisterVariable(&aw_console_mode);
    if(strlen(dir)+strlen(HISTORY_FILE)+2>sizeof history_path)return;
    sprintf(history_path,"%s/%s",dir,HISTORY_FILE);
    console_history_read();
}

/* Terminal line editing: the cursor moves without deleting, typing inserts,
 * Delete removes at the cursor, Home/End (Ctrl+A/Ctrl+E) jump, Ctrl+U/Ctrl+K
 * cut to the start/end, Up/Down browse the history and Down past the newest
 * entry returns the line that was being typed. Empty and repeated lines are
 * not stored. */
static void console_terminal_key(int key)
{
    char *line=key_lines[edit_line],*cmd;int len=strlen(line),stored,i;
    if(key_linepos>len)key_linepos=len;
    if(key_linepos<1)key_linepos=1;
    if(keydown[K_CTRL]){
        if(key>='A' && key<='Z')key+='a'-'A';
        if(key=='a')key=K_HOME;
        else if(key=='e')key=K_END;
        else if(key=='u'){memmove(line+1,line+key_linepos,len-key_linepos+1);key_linepos=1;return;}
        else if(key=='k'){line[key_linepos]=0;return;}
        else if(key>=32 && key<127)return;	// no other Ctrl letters type
    }
    if(shift_down && (key==K_HOME || key==K_END)){	// Shift+Home/End: scrollback ends
        con_backscroll=key==K_HOME?Con_ScrollMax():0;
        return;
    }
    switch(key){
    case K_ENTER:
        Cbuf_AddText(line+1);
        Cbuf_AddText("\n");
        Con_Printf("%s\n",line);
        stored=line[1] && strcmp(line,key_lines[(edit_line-1)&31]);
        if(stored)edit_line=(edit_line+1)&31;
        history_line=edit_line;
        key_lines[edit_line][0]=']';key_lines[edit_line][1]=0;key_linepos=1;
        console_draft[0]=0;
        if(stored)console_history_write();
        if(cls.state==ca_disconnected)SCR_UpdateScreen();
        return;
    case K_TAB:
        cmd=Cmd_CompleteCommand(line+1);
        if(!cmd)cmd=Cvar_CompleteVariable(line+1);
        if(cmd && Q_strlen(cmd)+3<MAXCMDLINE){
            Q_strcpy(line+1,cmd);
            key_linepos=Q_strlen(cmd)+1;
            line[key_linepos++]=' ';
            line[key_linepos]=0;
        }
        return;
    case K_LEFTARROW:
        if(key_linepos>1)key_linepos--;
        return;
    case K_RIGHTARROW:
        if(key_linepos<len)key_linepos++;
        return;
    case K_HOME:
        key_linepos=1;
        return;
    case K_END:
        key_linepos=len;
        return;
    case K_BACKSPACE:
        if(key_linepos>1){memmove(line+key_linepos-1,line+key_linepos,len-key_linepos+1);key_linepos--;}
        return;
    case K_DEL:
        if(key_linepos<len)memmove(line+key_linepos,line+key_linepos+1,len-key_linepos);
        return;
    case K_UPARROW:
        i=history_line;
        do i=(i-1)&31; while(i!=edit_line && !key_lines[i][1]);
        if(i==edit_line)return;	// no older entry
        if(history_line==edit_line)strcpy(console_draft,line);
        history_line=i;
        memmove(line,key_lines[history_line],strlen(key_lines[history_line])+1);	// another ring slot
        key_linepos=Q_strlen(line);
        return;
    case K_DOWNARROW:
        if(history_line==edit_line)return;
        do history_line=(history_line+1)&31; while(history_line!=edit_line && !key_lines[history_line][1]);
        if(history_line==edit_line){
            if(console_draft[0])strcpy(line,console_draft);
            else{line[0]=']';line[1]=0;}
        }
        else memmove(line,key_lines[history_line],strlen(key_lines[history_line])+1);
        key_linepos=Q_strlen(line);
        return;
    case K_PGUP:case K_MWHEELUP:
        con_backscroll+=key==K_MWHEELUP?2:Con_ScrollPage();
        if(con_backscroll>Con_ScrollMax())con_backscroll=Con_ScrollMax();
        return;
    case K_PGDN:case K_MWHEELDOWN:
        con_backscroll-=key==K_MWHEELDOWN?2:Con_ScrollPage();
        if(con_backscroll<0)con_backscroll=0;
        return;
    }
    if(key<32 || key>126)return;	// non printable
    if(len<MAXCMDLINE-1){
        memmove(line+key_linepos+1,line+key_linepos,len-key_linepos+1);
        line[key_linepos++]=key;
    }
}

void Key_Console (int key)
{
    char	*cmd;
    if(shift_down && key==K_UPARROW)key=K_PGUP;
    if(shift_down && key==K_DOWNARROW)key=K_PGDN;
    if(Key_ConsoleTerminal()){console_terminal_key(key);return;}

    if (key == K_ENTER)
    {
        Cbuf_AddText (key_lines[edit_line]+1);	// skip the >
        Cbuf_AddText ("\n");
        Con_Printf ("%s\n",key_lines[edit_line]);
        edit_line = (edit_line + 1) & 31;
        history_line = edit_line;
        key_lines[edit_line][0] = ']';
        key_linepos = 1;
        if (cls.state == ca_disconnected)
            SCR_UpdateScreen ();	// force an update, because the command
                                    // may take some time
        return;
    }

    if (key == K_TAB)
    {	// command completion
        cmd = Cmd_CompleteCommand (key_lines[edit_line]+1);
        if (!cmd)
            cmd = Cvar_CompleteVariable (key_lines[edit_line]+1);
        if (cmd)
        {
            Q_strcpy (key_lines[edit_line]+1, cmd);
            key_linepos = Q_strlen(cmd)+1;
            key_lines[edit_line][key_linepos] = ' ';
            key_linepos++;
            key_lines[edit_line][key_linepos] = 0;
            return;
        }
    }

    if (key == K_BACKSPACE || key == K_LEFTARROW)
    {
        if (key_linepos > 1)
            key_linepos--;
        return;
    }

    if (key == K_UPARROW)
    {
        /* AmiWind (CONSOLE-HISTORY-EMPTY-32): search from a copy and stay
         * on the oldest entry. id's code jumped to slot edit_line+1, which is
         * an empty line until all 32 slots have been used, and every further
         * Up then stayed on that empty line. */
        int line = history_line;
        do
        {
            line = (line - 1) & 31;
        } while (line != edit_line
                && !key_lines[line][1]);
        if (line == edit_line)
            return;	// no older entry
        history_line = line;
        Q_strcpy(key_lines[edit_line], key_lines[history_line]);
        key_linepos = Q_strlen(key_lines[edit_line]);
        return;
    }

    if (key == K_DOWNARROW)
    {
        if (history_line == edit_line) return;
        do
        {
            history_line = (history_line + 1) & 31;
        }
        while (history_line != edit_line
            && !key_lines[history_line][1]);
        if (history_line == edit_line)
        {
            key_lines[edit_line][0] = ']';
            key_linepos = 1;
        }
        else
        {
            Q_strcpy(key_lines[edit_line], key_lines[history_line]);
            key_linepos = Q_strlen(key_lines[edit_line]);
        }
        return;
    }

    if (key == K_PGUP || key==K_MWHEELUP)
    {
        con_backscroll += key==K_MWHEELUP?2:Con_ScrollPage();
        if (con_backscroll > Con_ScrollMax())
            con_backscroll = Con_ScrollMax();
        return;
    }

    if (key == K_PGDN || key==K_MWHEELDOWN)
    {
        con_backscroll -= key==K_MWHEELDOWN?2:Con_ScrollPage();
        if (con_backscroll < 0)
            con_backscroll = 0;
        return;
    }

    if (key == K_HOME)
    {
        con_backscroll = Con_ScrollMax();
        return;
    }

    if (key == K_END)
    {
        con_backscroll = 0;
        return;
    }

    if (key < 32 || key > 127)
        return;	// non printable

    if (key_linepos < MAXCMDLINE-1)
    {
        key_lines[edit_line][key_linepos] = key;
        key_linepos++;
        key_lines[edit_line][key_linepos] = 0;
    }

}

//============================================================================

char chat_buffer[32];
qboolean team_message = false;

void Key_Message (int key)
{
    static int chat_bufferlen = 0;

    if (key == K_ENTER)
    {
        if (team_message)
            Cbuf_AddText ("say_team \"");
        else
            Cbuf_AddText ("say \"");
        Cbuf_AddText(chat_buffer);
        Cbuf_AddText("\"\n");

        key_dest = key_game;
        chat_bufferlen = 0;
        chat_buffer[0] = 0;
        return;
    }

    if (key == K_ESCAPE)
    {
        key_dest = key_game;
        chat_bufferlen = 0;
        chat_buffer[0] = 0;
        return;
    }

    if (key < 32 || key > 127)
        return;	// non printable

    if (key == K_BACKSPACE)
    {
        if (chat_bufferlen)
        {
            chat_bufferlen--;
            chat_buffer[chat_bufferlen] = 0;
        }
        return;
    }

    if (chat_bufferlen == 31)
        return; // all full

    chat_buffer[chat_bufferlen++] = key;
    chat_buffer[chat_bufferlen] = 0;
}

//============================================================================


/*
===================
Key_StringToKeynum

Returns a key number to be used to index keybindings[] by looking at
the given string.  Single ascii characters return themselves, while
the K_* names are matched up.
===================
*/
int Key_StringToKeynum (char *str)
{
    keyname_t	*kn;

    if (!str || !str[0])
        return -1;
    if (!str[1])
        return str[0];

    for (kn=keynames ; kn->name ; kn++)
    {
        if (!Q_strcasecmp(str,kn->name))
            return kn->keynum;
    }
    return -1;
}

/*
===================
Key_KeynumToString

Returns a string (either a single ascii char, or a K_* name) for the
given keynum.
FIXME: handle quote special (general escape sequence?)
===================
*/
char *Key_KeynumToString (int keynum)
{
    keyname_t	*kn;
    static	char	tinystr[2];

    if (keynum == -1)
        return "<KEY NOT FOUND>";
    if (keynum > 32 && keynum < 127)
    {	// printable ascii
        tinystr[0] = keynum;
        tinystr[1] = 0;
        return tinystr;
    }

    for (kn=keynames ; kn->name ; kn++)
        if (keynum == kn->keynum)
            return kn->name;

    return "<UNKNOWN KEYNUM>";
}


/*
===================
Key_SetBinding
===================
*/
void Key_SetBinding (int keynum, char *binding)
{
    char	*new;
    int		l;

    if (keynum == -1)
        return;

// free old bindings
    if (keybindings[keynum])
    {
        Z_Free (keybindings[keynum]);
        keybindings[keynum] = NULL;
    }

// allocate memory for new binding
    l = Q_strlen (binding);
    new = Z_Malloc (l+1);
    Q_strcpy (new, binding);
    new[l] = 0;
    keybindings[keynum] = new;
}

/*
===================
Key_Unbind_f
===================
*/
void Key_Unbind_f (void)
{
    int		b;

    if (Cmd_Argc() != 2)
    {
        Con_Printf ("unbind <key> : remove commands from a key\n");
        return;
    }

    b = Key_StringToKeynum (Cmd_Argv(1));
    if (b==-1)
    {
        Con_Printf ("\"%s\" isn't a valid key\n", Cmd_Argv(1));
        return;
    }

    Key_SetBinding (b, "");
}

void Key_Unbindall_f (void)
{
    int		i;

    for (i=0 ; i<256 ; i++)
        if (keybindings[i])
            Key_SetBinding (i, "");
}


/*
===================
Key_Bind_f
===================
*/
void Key_Bind_f (void)
{
    int			i, c, b;
    char		cmd[1024];

    c = Cmd_Argc();

    if (c != 2 && c != 3)
    {
        Con_Printf ("bind <key> [command] : attach a command to a key\n");
        return;
    }
    b = Key_StringToKeynum (Cmd_Argv(1));
    if (b==-1)
    {
        Con_Printf ("\"%s\" isn't a valid key\n", Cmd_Argv(1));
        return;
    }

    if (c == 2)
    {
        if (keybindings[b])
            Con_Printf ("\"%s\" = \"%s\"\n", Cmd_Argv(1), keybindings[b] );
        else
            Con_Printf ("\"%s\" is not bound\n", Cmd_Argv(1) );
        return;
    }

// copy the rest of the command line
    cmd[0] = 0;		// start out with a null string
    for (i=2 ; i< c ; i++)
    {
        if (i > 2)
            strcat (cmd, " ");
        strcat (cmd, Cmd_Argv(i));
    }

    Key_SetBinding (b, cmd);
}

/*
============
Key_WriteBindings

Writes lines containing "bind key value"
============
*/
void Key_WriteBindings (FILE *f)
{
    int		i;

    fprintf(f,"// AmiWind key bindings. Engine settings are in config.cfg.\nunbindall\n");
    for (i=0 ; i<256 ; i++)
        if (keybindings[i])
            if (*keybindings[i])
                fprintf (f, "bind \"%s\" \"%s\"\n", Key_KeynumToString(i), keybindings[i]);
}


/*
===================
Key_Init
===================
*/
/* Restore defaults missing from older saved configurations, preserving custom slots. */
void AW_ControlsMigrate(void)
{
    int key;char *binding;
    for(key='1';key<='3';key++){
        binding=keybindings[key];
        if(binding && (!strcmp(binding,"aw_drawdistance 450") ||
           !strcmp(binding,"aw_drawdistance 540") || !strcmp(binding,"aw_drawdistance 700") ||
           !strcmp(binding,"aw_drawdistance 1000")))Key_SetBinding(key,"");
    }
    if(!keybindings['j'] || !*keybindings['j'])Key_SetBinding('j',"aw_journal");
    if(!keybindings['m'] || !*keybindings['m'])Key_SetBinding('m',"aw_worldmap");
    if(!keybindings[K_UPARROW] || !*keybindings[K_UPARROW])Key_SetBinding(K_UPARROW,"+forward");
    if(!keybindings[K_DOWNARROW] || !*keybindings[K_DOWNARROW])Key_SetBinding(K_DOWNARROW,"+back");
}

void Key_Init (void)
{
    int		i;

    for (i=0 ; i<32 ; i++)
    {
        key_lines[i][0] = ']';
        key_lines[i][1] = 0;
    }
    key_linepos = 1;

//
// init ascii characters in console mode
//
    for (i=32 ; i<128 ; i++)
        consolekeys[i] = true;
    consolekeys[K_ENTER] = true;
    consolekeys[K_TAB] = true;
    consolekeys[K_LEFTARROW] = true;
    consolekeys[K_RIGHTARROW] = true;
    consolekeys[K_UPARROW] = true;
    consolekeys[K_DOWNARROW] = true;
    consolekeys[K_BACKSPACE] = true;
    consolekeys[K_PGUP] = true;
    consolekeys[K_PGDN] = true;
    consolekeys[K_SHIFT] = true;
    consolekeys[K_MWHEELUP] = true;
    consolekeys[K_MWHEELDOWN] = true;
    // AmiWind: the terminal line editor's keys (classic mode ignores Delete
    // and uses Home/End for the scrollback, as id's Key_Console does)
    consolekeys[K_DEL] = true;
    consolekeys[K_HOME] = true;
    consolekeys[K_END] = true;
    consolekeys['`'] = false;
    consolekeys['~'] = false;

    for (i=0 ; i<256 ; i++)
        keyshift[i] = i;
    for (i='a' ; i<='z' ; i++)
        keyshift[i] = i - 'a' + 'A';
    keyshift['1'] = '!';
    keyshift['2'] = '@';
    keyshift['3'] = '#';
    keyshift['4'] = '$';
    keyshift['5'] = '%';
    keyshift['6'] = '^';
    keyshift['7'] = '&';
    keyshift['8'] = '*';
    keyshift['9'] = '(';
    keyshift['0'] = ')';
    keyshift['-'] = '_';
    keyshift['='] = '+';
    keyshift[','] = '<';
    keyshift['.'] = '>';
    keyshift['/'] = '?';
    keyshift['<'] = '>';
    keyshift[';'] = ':';
    keyshift['\''] = '"';
    keyshift['['] = '{';
    keyshift[']'] = '}';
    keyshift['`'] = '~';
    keyshift['\\'] = '|';

    menubound[K_ESCAPE] = true;
    for (i=0 ; i<12 ; i++)
        menubound[K_F1+i] = true;

//
// register our functions
//
    Cmd_AddCommand ("bind",Key_Bind_f);
    Cmd_AddCommand("aw_controls_migrate",AW_ControlsMigrate);
    Cmd_AddCommand ("unbind",Key_Unbind_f);
    Cmd_AddCommand ("unbindall",Key_Unbindall_f);


}

/*
===================
Key_Event

Called by the system between frames for both key up and key down events
Should NOT be called during an interrupt!
===================
*/
void Key_Event (int key, qboolean down)
{
    char	*kb;
    char	cmd[1024];

    /* A named chord uses the same editable binding and save path as keys.
     * Console typing and modal panels keep the literal M. */
    if(key=='m' && ((down && key_dest==key_game && keydown[K_ALT]) ||
                   (!down && keydown[K_ALTM])))key=K_ALTM;
    keydown[key] = down;

    if (!down)
        key_repeats[key] = 0;

    key_lastpress = key;
    key_count++;
    if (key_count <= 0)
    {
        return;		// just catching keys for Con_NotifyBox
    }

// update auto-repeat status
    if (down)
    {
        key_repeats[key]++;
        if (key != K_BACKSPACE && key != K_PAUSE && key_repeats[key] > 1
            && !(key_dest == key_console && Key_ConsoleTerminal()
                 && (key == K_LEFTARROW || key == K_RIGHTARROW || key == K_DEL)))
        {
            return;	// ignore most autorepeats
        }

    }

    if (key == K_SHIFT)
        shift_down = down;

    if (AW_MovieKey(key,down)) return;
    if (AW_WorldUIKey(key,down)) return;

    /* Physical Amiga raw key 0 maps to grave (Finnish host: section key).
     * F10 is a layout-independent fallback on the Amiga keyboard. */
    if (key == '`' || key == K_F10) {
        if(down)Cbuf_AddText(shift_down?"aw_console_fullscreen\n":"aw_console_cycle\n");
        return;
    }

    /* Music history controls are handled before ordinary game bindings. */
    if (AW_GalleryKey(shift_down?keyshift[key]:key,down,shift_down,keydown[K_CTRL])) return;
    if (down && AW_TravelKey(shift_down?keyshift[key]:key)) return;
    if (down && AW_WaitKey(shift_down?keyshift[key]:key)) return;
    if (down && AW_IntroKey(shift_down?keyshift[key]:key)) return;

    if (down && key_dest == key_game && keydown[K_SHIFT] && key == 'v') {
        Cbuf_AddText("aw_viewdistance_cycle\n");return;
    }

    if (down && key_dest == key_game && keydown[K_SHIFT] &&
        (key == K_F5 || key == K_F6)) {
        Cbuf_AddText(key == K_F5 ? "aw_music_previous\n" : "aw_music_next\n");
        return;
    }


//
// handle escape specialy, so the user can never unbind it
//
    if (key == K_ESCAPE)
    {
        if (!down)
            return;
        switch (key_dest)
        {
        case key_message:
            Key_Message (key);
            break;
        case key_menu:
            M_Keydown (key);
            break;
        case key_console:
            Cbuf_AddText("toggleconsole\n");
            break;
        case key_game:
            M_ToggleMenu_f ();
            break;
        default:
            Sys_Error ("Bad key_dest");
        }
        return;
    }

//
// key up events only generate commands if the game key binding is
// a button command (leading + sign).  These will occur even in console mode,
// to keep the character from continuing an action started before a console
// switch.  Button commands include the kenum as a parameter, so multiple
// downs can be matched with ups
//
    if (!down)
    {
        kb = keybindings[key];
        if (kb && kb[0] == '+')
        {
            sprintf (cmd, "-%s %ld\n", kb+1, (long)key);
            Cbuf_AddText (cmd);
        }
        if (keyshift[key] != key)
        {
            kb = keybindings[keyshift[key]];
            if (kb && kb[0] == '+')
            {
                sprintf (cmd, "-%s %ld\n", kb+1, (long)key);
                Cbuf_AddText (cmd);
            }
        }
        return;
    }

//
// during demo playback, most keys bring up the main menu
//
    if (cls.demoplayback && down && consolekeys[key] && key_dest == key_game)
    {
        M_ToggleMenu_f ();
        return;
    }

//
// if not a consolekey, send to the interpreter no matter what mode is
//
    if ( (key_dest == key_menu && menubound[key])
    || (key_dest == key_console && !consolekeys[key]
        && !(key == K_CTRL && Key_ConsoleTerminal()))	// Ctrl edits the line
    || (key_dest == key_game && ( !con_forcedup || !consolekeys[key] ) ) )
    {
        kb = keybindings[key];
        /* Console scroll and modal controls consume keys before this point.
         * Warning earlier adds new console lines for every unbound wheel
         * tick, including ticks already clamped at either scroll boundary. */
        if (key >= 200 && !kb)
            Con_Printf ("%s is unbound, hit F4 to set.\n", Key_KeynumToString (key) );
        if (kb)
        {
            if (kb[0] == '+')
            {	// button commands add keynum as a parm
                sprintf (cmd, "%s %ld\n", kb, (long)key);
                Cbuf_AddText (cmd);
            }
            else
            {
                Cbuf_AddText (kb);
                Cbuf_AddText ("\n");
            }
        }
        return;
    }

    if (!down)
        return;		// other systems only care about key down events

    if ((key>='a' && key<='z') ? (shift_down!=caps_down) : shift_down)
    {
        key = keyshift[key];
    }

    switch (key_dest)
    {
    case key_message:
        Key_Message (key);
        break;
    case key_menu:
        M_Keydown (key);
        break;

    case key_game:
    case key_console:
        Key_Console (key);
        break;
    default:
        Sys_Error ("Bad key_dest");
    }
}


/*
===================
Key_ClearStates
===================
*/
void Key_ClearStates (void)
{
    int		i;
    shift_down=false;
    caps_down=false;

    for (i=0 ; i<256 ; i++)
    {
        keydown[i] = false;
        key_repeats[i] = 0;
    }
}
