#ifndef MWAD_TERRAIN_PACKET_H
#define MWAD_TERRAIN_PACKET_H

#include <stddef.h>
#include <stdint.h>

/* Allocation-free view of one big-endian MWT0 packet. */
typedef struct {
    const uint8_t *heights;
    const uint8_t *materials;
    int32_t chunk_x;
    int32_t chunk_y;
    uint16_t side;
    uint16_t spacing;
    uint16_t height_scale;
    size_t packet_bytes;
} mwad_terrain;

int mwad_terrain_open(const uint8_t *data, size_t available, mwad_terrain *out);
int32_t mwad_terrain_height(const mwad_terrain *terrain, unsigned x, unsigned y);
unsigned mwad_terrain_material(const mwad_terrain *terrain, unsigned x, unsigned y);

#endif
