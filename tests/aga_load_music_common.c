/* SPDX-License-Identifier: GPL-2.0-or-later
 * Supply one synthetic search root to the actual COM_LoadFile implementation. */
#include "../engine/aga/src/common.c"
#include "../engine/aga/src/aw_fopenbuf.c"   /* com_fopen_buffer (TRADEHOUSE-LONG-FRAME-59) */
void AW_TestLoadPath(void){
 static searchpath_t path;
 memset(&path,0,sizeof(path));strcpy(path.filename,".");
 com_searchpaths=&path;strcpy(com_gamedir,".");
}
