/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The stdio buffer of the next file COM_FOpenFile opens from a directory (common.c; 0: its 16 KiB). A caller that only
 * binary-searches a file (aw_inventory.c: focus.awf's contents, owners and references) sets a small one around its
 * open, so a search step reads a few hundred bytes instead of refilling 16 KiB (TRADEHOUSE-LONG-FRAME-59). Its own file
 * so that common.c and aw_inventory.c each link without the other (the native tests). */
int com_fopen_buffer;
