/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg tp with no argument (v0.0.57, TP-PICKER-57): every named settlement of the island in the console-font list
 * box (aw_listbox.c), searchable as you type; choosing one runs the existing coordinate teleport (dbg tp X Y Z).
 * The rows are the builder's table id1/tp-places.lut (tools/tp_places_lut.py, AWTP1: the exterior cell names of
 * the game's data and each place's arrival on the street): read when the box opens, freed when it closes, so
 * nothing stays resident. Without the table (an older disk) the caller opens the scene picker, as before.
 */
#include "quakedef.h"
#include "aw_listbox.h"
#include "aw_tryalloc.h"

#define TABLE_MAX (AW_TP_HEADER+1024L*AW_TP_ROW)   /* 82 places on Vvardenfell; room for Solstheim and more */
static const char path[]="tp-places.lut";
static unsigned char *table;
static long rows;
static char label_buf[AW_TP_NAME];

static const char *label(void *ctx,int row){
    aw_tp_place_t p;(void)ctx;
    if(!table || row<0 || row>=rows)return "";
    AW_TpPlacesRow(table,row,&p);
    memcpy(label_buf,p.name,sizeof(label_buf));
    return label_buf;
}
static void chosen(void *ctx,int row){
    aw_tp_place_t p;char command[64];(void)ctx;
    if(!table || row<0 || row>=rows)return;
    AW_TpPlacesRow(table,row,&p);
    if(AW_TpPlacesCommand(&p,command,sizeof(command))<0)return;
    Con_Printf("Teleport: %s\n",p.name);
    Cbuf_AddText(command);
}
static void closed(void *ctx){
    (void)ctx;free(table);table=NULL;rows=0;
}
int AW_TpPlacesOpen(void){
    FILE *f=NULL;long size;aw_listbox_spec_t s;
    if(AW_ListBoxActive())return 1;
    size=COM_FOpenFile((char *)path,&f);
    if(size<AW_TP_HEADER || size>TABLE_MAX || !f){
        if(f)fclose(f);
        Con_DPrintf("Teleport list: %s not on this disk\n",path);
        return 0;
    }
    if(!(table=(unsigned char *)AW_TryMalloc((unsigned long)size))){fclose(f);Con_Printf("Teleport list: not enough memory.\n");return 0;}
    if((long)fread(table,1,(size_t)size,f)!=size || (rows=AW_TpPlacesRows(table,size))<1){
        fclose(f);Con_Printf("Teleport list: %s is not AWTP1\n",path);closed(NULL);return 0;
    }
    fclose(f);
    memset(&s,0,sizeof(s));
    s.title="Teleport to a settlement";s.count=(int)rows;s.label=label;s.chosen=chosen;s.closed=closed;
    if(!AW_ListBoxOpen(&s)){closed(NULL);return 0;}
    Con_DPrintf("Teleport list: %ld places, %ld bytes while open\n",rows,size);
    return 1;
}
