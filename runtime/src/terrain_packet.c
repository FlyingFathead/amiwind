#include "terrain_packet.h"

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static uint32_t read_u32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16)
        | ((uint32_t)p[2] << 8) | p[3];
}

static int32_t read_i32(const uint8_t *p)
{
    uint32_t value = read_u32(p);
    if (value <= UINT32_C(0x7fffffff)) return (int32_t)value;
    return -1 - (int32_t)(UINT32_MAX - value);
}

int mwad_terrain_open(const uint8_t *data, size_t available, mwad_terrain *out)
{
    uint16_t side, spacing;
    uint32_t payload, expected;
    size_t size, i;
    if (!data || !out || available < 24) return 0;
    if (data[0] != 'M' || data[1] != 'W' || data[2] != 'T' || data[3] != '0') return 0;
    if (read_u16(data + 4) != 1 || read_u16(data + 18) != 8) return 0;
    side = read_u16(data + 6);
    spacing = read_u16(data + 16);
    if (side != 3 && side != 5 && side != 9 && side != 17) return 0;
    if ((uint32_t)spacing * (side - 1u) != 2048u) return 0;
    payload = read_u32(data + 20);
    expected = 2u * (uint32_t)side * side + (uint32_t)(side - 1u) * (side - 1u);
    if (payload != expected) return 0;
    size = (size_t)((24u + expected + 31u) & ~31u);
    if (available < size) return 0;
    for (i = 24u + expected; i < size; ++i) if (data[i]) return 0;
    out->heights = data + 24;
    out->materials = data + 24 + 2u * side * side;
    out->chunk_x = read_i32(data + 8);
    out->chunk_y = read_i32(data + 12);
    out->side = side;
    out->spacing = spacing;
    out->height_scale = 8;
    out->packet_bytes = size;
    return 1;
}

/* Call only after a successful open; out-of-range access returns zero. */
int32_t mwad_terrain_height(const mwad_terrain *terrain, unsigned x, unsigned y)
{
    uint16_t value;
    int32_t signed_value;
    if (!terrain || x >= terrain->side || y >= terrain->side) return 0;
    value = read_u16(terrain->heights + 2u * (y * terrain->side + x));
    signed_value = value < 32768u ? (int32_t)value : (int32_t)value - 65536;
    return signed_value * terrain->height_scale;
}

unsigned mwad_terrain_material(const mwad_terrain *terrain, unsigned x, unsigned y)
{
    unsigned side;
    if (!terrain || terrain->side < 2) return 0;
    side = terrain->side - 1u;
    if (x >= side || y >= side) return 0;
    return terrain->materials[y * side + x];
}
