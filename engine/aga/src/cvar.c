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
// cvar.c -- dynamic variable tracking

#include "quakedef.h"
#include "aw_boolean.h"

cvar_t	*cvar_vars;
char	*cvar_null_string = "";

/*
============
Cvar_FindVar
============
*/
cvar_t *Cvar_FindVar (char *var_name)
{
    cvar_t	*var;

    for (var=cvar_vars ; var ; var=var->next)
        if (!Q_strcmp (var_name, var->name))
            return var;

    return NULL;
}

/*
============
Cvar_VariableValue
============
*/
float	Cvar_VariableValue (char *var_name)
{
    cvar_t	*var;

    var = Cvar_FindVar (var_name);
    if (!var)
        return 0;
    return Q_atof (var->string);
}


/*
============
Cvar_VariableString
============
*/
char *Cvar_VariableString (char *var_name)
{
    cvar_t *var;

    var = Cvar_FindVar (var_name);
    if (!var)
        return cvar_null_string;
    return var->string;
}


/*
============
Cvar_CompleteVariable
============
*/
char *Cvar_CompleteVariable (char *partial)
{
    cvar_t		*cvar;
    int			len;

    len = Q_strlen(partial);

    if (!len)
        return NULL;

// check functions
    for (cvar=cvar_vars ; cvar ; cvar=cvar->next)
        if (!Q_strncmp (partial,cvar->name, len))
            return cvar->name;

    return NULL;
}


/*
============
Cvar_Set
============
*/
void Cvar_Set (char *var_name, char *value)
{
    cvar_t	*var;
    qboolean changed;

    var = Cvar_FindVar (var_name);
    if (!var)
    {	// there is an error in C code if this happens
        Con_Printf ("Cvar_Set: variable %s not found\n", var_name);
        return;
    }

    /* Normalized sound/light levels use the ordinary archived config path.
     * Clamp direct console/config input as well as their UI/command paths. */
    if (!strcmp(var_name, "effectsvolume") || !strcmp(var_name, "dialoguevolume") ||
        !strcmp(var_name, "aw_torch_strength"))
    {
        float gain = Q_atof(value);
        if (!(gain >= 0)) value = "0";
        else if (gain > 1) value = "1";
    }
    changed = Q_strcmp(var->string, value);

    Z_Free (var->string);	// free the old value string

    var->string = Z_Malloc (Q_strlen(value)+1);
    Q_strcpy (var->string, value);
    var->value = Q_atof (var->string);
    if (var->server && changed)
    {
        if (sv.active)
            SV_BroadcastPrintf ("\"%s\" changed to \"%s\"\n", var->name, var->string);
    }
}

/*
============
Cvar_SetValue
============
*/
void Cvar_SetValue (char *var_name, float value)
{
    char	val[32];
    int		intpart;
    int		fracpart;

    // AmigaOS sprintf doesn't support %f, so convert manually
    intpart = (int)value;
    fracpart = (int)((value - intpart) * 1000000);  // 6 decimal places

    if (fracpart < 0)
        fracpart = -fracpart;

    // Remove trailing zeros for cleaner output
    if (fracpart == 0)
        sprintf(val, "%ld", (long)intpart);
    else
        sprintf(val, "%ld.%06ld", (long)intpart, (long)fracpart);

    Cvar_Set (var_name, val);
}


/*
============
Cvar_RegisterVariable

Adds a freestanding variable to the variable list.
============
*/
void Cvar_RegisterVariable (cvar_t *variable)
{
    char	*oldstr;

// first check to see if it has allready been defined
    if (Cvar_FindVar (variable->name))
    {
        Con_Printf ("Can't register variable %s, allready defined\n", variable->name);
        return;
    }

// check for overlap with a command
    if (Cmd_Exists (variable->name))
    {
        Con_Printf ("Cvar_RegisterVariable: %s is a command\n", variable->name);
        return;
    }

// copy the value off, because future sets will Z_Free it
    oldstr = variable->string;
    variable->string = Z_Malloc (Q_strlen(variable->string)+1);
    Q_strcpy (variable->string, oldstr);
    variable->value = Q_atof (variable->string);

// link the variable in
    variable->next = cvar_vars;
    cvar_vars = variable;
}

/*
============
Cvar_Command

Handles variable inspection and changing from the console
============
*/
qboolean	Cvar_Command (void)
{
    cvar_t			*v;

// check variables
    v = Cvar_FindVar (Cmd_Argv(0));
    /* quiet aliases of aw_seethrough_material (earlier names of the same setting) */
    if (!v && (!Q_strcasecmp(Cmd_Argv(0),"aw_seethrough") || !Q_strcasecmp(Cmd_Argv(0),"aw_fence")))
        v = Cvar_FindVar ("aw_seethrough_material");
    if (!v)
        return false;

    /* aw_seethrough_material (d_fence.c, ROOM-DECAL-ALPHA-62): cobwebs, hanging moss and leaves are drawn with
     * their see-through parts instead of solid rectangles. 0 off, 1 on (the default), 2 on and also from behind;
     * on/off = 1/0. No value prints the current value and the list. aw_fence_twosided 1 stays the old name of 2. */
    if(!strcmp(v->name,"aw_seethrough_material")) {
        static const char *fence_methods[3]={"off (see-through textures drawn as solid rectangles)",
                                              "on: cobwebs, hanging moss and leaves drawn with their see-through parts (the default)",
                                              "on, and also seen from behind"};
        int value=-1;
        if(Cmd_Argc()==2){
            char *s=Cmd_Argv(1);value=AW_ParseBoolean(s);
            if(value<0 && s[0]>='0' && s[0]<='2' && !s[1])value=s[0]-'0';
        }
        if(Cmd_Argc()!=2 || value<0){
            int cur=(int)v->value;if(cur<0||cur>2)cur=1;
            Con_Printf("aw_seethrough_material is %d: %s\n",cur,fence_methods[cur]);
            Con_Printf("  0 = %s\n  1 = %s\n  2 = %s\n",fence_methods[0],fence_methods[1],fence_methods[2]);
            Con_Printf("  (seen from behind can also be built in: build option --chim-fence-twosided-faces mirror)\n");
            return true;
        }
        Cvar_SetValue(v->name,value);
        return true;
    }

// perform a variable print or set
    if (Cmd_Argc() == 1)
    {
        Con_Printf ("\"%s\" is \"%s\"\n", v->name, v->string);
        return true;
    }

    if(!strcmp(v->name,"aw_poly_budget_over_cap") && Q_strcasecmp(Cmd_Argv(1),"auto")) {
        char *end;long cap=strtol(Cmd_Argv(1),&end,10);
        if(*end || cap<666 || cap>1024){Con_Printf("aw_poly_budget_over_cap requires auto or an integer from 666 to 1024 triangles.\n");return true;}
    }
    /* aw_cull selects a far test 0..7 (aw_fog.c); on/off keep their meaning:
     * on = the far plane alone (1, "Full"), off = none; the default is 4 (Strong).
     * Plus 8 the fog rule, plus 16 whole-structure cuts, plus 32 no large-room face cut (0..63; quakedef.h AW_CULL_*). */
    if(!strcmp(v->name,"aw_cull")) {
        char *s=Cmd_Argv(1);int value=AW_ParseBoolean(s);
        if(value<0 && s[0]>='0' && s[0]<='9' && (!s[1] || (s[1]>='0' && s[1]<='9' && !s[2]))){
            value=s[1]?(s[0]-'0')*10+s[1]-'0':s[0]-'0';
            if(value>AW_CULL_MAX)value=-1;
        }
        if(Cmd_Argc()!=2 || value<0){Con_Printf("aw_cull: 0..7 or on/off (on = 1, the default; 7 = debug view), +8 fog rule, +16 whole-structure cuts, +32 no large-room face cut\n");return true;}
        Cvar_SetValue(v->name,value);
        return true;
    }
    if(AW_BooleanCvar(v->name)) {
        int value=AW_ParseBoolean(Cmd_Argv(1));
        if(Cmd_Argc()!=2 || value<0) {
            Con_Printf("Boolean value required: on/off, true/false, 1/0\n");
            return true;
        }
        Cvar_SetValue(v->name,value);
    } else Cvar_Set (v->name, Cmd_Argv(1));
    return true;
}


/*
============
Cvar_WriteVariables

Writes lines containing "set variable value" for all variables
with the archive flag set to true.
============
*/
void Cvar_WriteVariables (FILE *f)
{
    cvar_t	*var;

    for (var = cvar_vars ; var ; var = var->next)
        if (var->archive)
            fprintf (f, "%s \"%s\"\n", var->name, var->string);
}
