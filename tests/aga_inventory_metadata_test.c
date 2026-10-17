/* SPDX-License-Identifier: GPL-3.0-only */
#include "quakedef.h"
#include "aw_inventory.h"
#include <assert.h>
static unsigned char row[512];
static int multirow;
static int corrupt_header;
static void u32(unsigned char *p,unsigned n){int i;for(i=0;i<4;i++)p[i]=(n>>(8*i))&255;}
static void real(unsigned char *p,float value){unsigned bits;memcpy(&bits,&value,4);u32(p,bits);}
int __wrap_COM_FOpenFile(char *path,FILE **out){
    FILE *f=tmpfile();int i,n=multirow?7:1;
    static const char *ids[]={"aardvark","common_pants_01","fixture_sword","gold_001","ring_keley","steel longsword","steel_shield"};
    unsigned char item[512];assert(f && !strcmp(path,"inventory/items.awi"));
    for(i=0;i<137;i++)fputc(0,f);
    fputs(corrupt_header?"AWI1":"AWI2",f);fputc(n,f);fputc(0,f);fputc(0,f);fputc(0,f);
    for(i=0;i<n;i++){
        memcpy(item,row,512);if(multirow){memset(item,0,64);strcpy((char *)item,ids[i]);}
        assert(fwrite(item,1,512,f)==512);
    }
    fseek(f,137,SEEK_SET);*out=f;return 8+n*512;
}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
int main(void){
    aw_inventory_item_t out,prior;unsigned char pristine[512];int i;
    memset(row,0,sizeof(row));strcpy((char *)row,"fixture_sword");strcpy((char *)row+64,"Fixture sword");
    u32(row+160,AW_INV_WEAPON);u32(row+176,1U<<AW_SLOT_RIGHT);u32(row+180,7);
    strcpy((char *)row+184,"progs/inv/fixture.mdl");u32(row+440,2);u32(row+444,5);
    u32(row+448,2);u32(row+452,14);u32(row+456,1);u32(row+460,20);u32(row+464,4);u32(row+468,18);
    real(row+172,12);real(row+472,1);real(row+476,1.35f);real(row+480,900);
    assert(AW_InventoryRead("fixture_sword",&out));assert(out.damage[5]==18 && out.health==900);
    prior=out;memcpy(pristine,row,sizeof(row));
    for(i=472;i<=484;i+=4){real(row+i,NAN);assert(!AW_InventoryRead("fixture_sword",&out));assert(!memcmp(&prior,&out,sizeof(out)));memcpy(row,pristine,512);}
    real(row+476,INFINITY);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    u32(row+448,256);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    u32(row+448,15);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    u32(row+440,10);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    u32(row+444,27);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    u32(row+488,3);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    strcpy((char *)row+184,"../escape.mdl");assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    assert(AW_InventoryRead("fixture_sword",&out) && out.enchant_kind==0 && out.charge_max==0);
    strcpy((char *)row+312,"heal_minor");row[496]=AW_ENCH_USED;real(row+500,20);
    assert(AW_InventoryRead("fixture_sword",&out) && out.enchant_kind==AW_ENCH_USED && out.charge_max==20);
    row[496]=5;assert(!AW_InventoryRead("fixture_sword",&out));row[496]=AW_ENCH_USED;
    row[497]=1;assert(!AW_InventoryRead("fixture_sword",&out));row[497]=0;
    row[511]=1;assert(!AW_InventoryRead("fixture_sword",&out));row[511]=0;
    real(row+500,NAN);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);
    real(row+500,3);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512);   /* charge without a kind */
    row[496]=AW_ENCH_USED;real(row+500,3);assert(!AW_InventoryRead("fixture_sword",&out));memcpy(row,pristine,512); /* no enchantment */
    assert(AW_InventoryRead("fixture_sword",&out));assert(!memcmp(&prior,&out,sizeof(out)));
    corrupt_header=1;assert(!AW_InventoryRead("fixture_sword",&out));assert(!memcmp(&prior,&out,sizeof(out)));
    corrupt_header=0;multirow=1;
    /* Link common.c: the real Quake helper is an equality test in both orders. */
    assert(Q_strcasecmp("a","z")==-1 && Q_strcasecmp("z","a")==-1);
    assert(AW_InventoryCompare("a","z")<0 && AW_InventoryCompare("z","a")>0);
    assert(AW_InventoryCompare("MiXeD","mixed")==0);
    {
        static const char *keys[]={"aardvark","COMMON_PANTS_01","fixture_sword","GOLD_001","ring_keley","STEEL LONGSWORD","steel_shield"};
        for(i=0;i<7;i++){assert(AW_InventoryRead(keys[i],&out));assert(AW_InventoryCompare(keys[i],out.id)==0);}
        prior=out;
        assert(!AW_InventoryRead("0_missing",&out));
        assert(!AW_InventoryRead("fixture_sword_suffix",&out));
        assert(!AW_InventoryRead("zz_missing",&out));
        assert(!memcmp(&prior,&out,sizeof(out)));
    }
    return 0;
}
