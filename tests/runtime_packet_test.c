#include <stdio.h>
#include "terrain_packet.h"

int main(int argc, char **argv)
{
    uint8_t buffer[1025];
    uint8_t *packet = buffer + 1; /* Deliberately unaligned input. */
    mwad_terrain terrain;
    FILE *file;
    size_t size;
    unsigned x, y;
    uint8_t saved;
    if (argc != 2) return 1;
    file = fopen(argv[1], "rb");
    if (!file) return 2;
    size = fread(packet, 1, 1024, file);
    fclose(file);
    if (!mwad_terrain_open(packet, size, &terrain)) return 3;
    if (terrain.chunk_x != -8 || terrain.chunk_y != -36) return 4;
    if (terrain.packet_bytes != size) return 5;
    for (y = 0; y < terrain.side; ++y) {
        for (x = 0; x < terrain.side; ++x) {
            int32_t expected = ((int32_t)y - (int32_t)x) * (terrain.spacing / 128) * 8;
            if (mwad_terrain_height(&terrain, x, y) != expected) return 6;
        }
    }
    for (y = 0; y < terrain.side - 1u; ++y)
        for (x = 0; x < terrain.side - 1u; ++x)
            if (mwad_terrain_material(&terrain, x, y) != 7) return 7;
    if (mwad_terrain_open(packet, size - 1, &terrain)) return 8;
    saved = packet[0]; packet[0] = 0;
    if (mwad_terrain_open(packet, size, &terrain)) return 9;
    packet[0] = saved; packet[size - 1] = 1;
    if (mwad_terrain_open(packet, size, &terrain)) return 10;
    return 0;
}
