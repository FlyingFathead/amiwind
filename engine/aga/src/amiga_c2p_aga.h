#ifndef AMIGA_C2P_H
#define AMIGA_C2P_H

/*       
void  *c2p8_reloc(register __a0 struct BitMap *bitmap);
void  c2p8_deinit(register __a0 void *c2p);
void  c2p8(register __a0 void *c2p,
		register __a1 struct BitMap *bmp,
		register __a2 UBYTE *chunky,
		register __d0 ULONG size);
*/        
                        
         
void *c2p8_reloc_stub(struct BitMap *bitmap) {

    register void *_return __asm("d0");
    
    register struct BitMap *_bitmap __asm("a0") = bitmap;    
 
    __asm("jsr _c2p8_reloc" : : "r" (_return), "r" (_bitmap) : "d1", "d2", "d3", "d4", "d5", "d6", "d7", "a1", "a2", "a3", "a4", "cc", "memory");    
    
    return _return;
}

static inline void c2p8_deinit_stub(void *c2p) {

    register void *_c2p __asm("a0") = c2p;

    __asm("jsr _c2p8_deinit" : : "r" (_c2p) : "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "a1", "a2", "a3", "a4", "cc", "memory");
}

static inline void c2p8_stub(void *c2p, struct BitMap *bitmap, UBYTE *chunky, ULONG size) {
    
    register ULONG _size __asm("d0") = size;
    
    register void *_c2p __asm("a0") = c2p;
    register struct BitMap *_bitmap __asm("a1") = bitmap;
    register UBYTE *_chunky __asm("a2") = chunky;
      
   __asm("jsr _c2p8" : : "r" (_size), "r" (_c2p), "r" (_bitmap), "r" (_chunky) : "d1", "d2", "d4", "d6", "d7", "a3", "a4", "cc", "memory");
}                     
    
                         


#endif //  AMIGA_C2P_H

