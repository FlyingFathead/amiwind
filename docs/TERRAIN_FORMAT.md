# Experimental terrain packets, version 1

`terrain.mwt` concatenates independently readable packets. `terrain-index.json`
provides PC-side offsets; a compact runtime index is not implemented. Numbers
are big-endian. All packets are padded with zeroes to a 32-byte boundary.
This layout is experimental and can change before any runtime is released.

| Offset | Type | Meaning |
| --- | --- | --- |
| 0 | 4 bytes | ASCII `MWT0` |
| 4 | uint16 | Format version, 1 |
| 6 | uint16 | Vertex count along one side, N |
| 8 | int32 | Global chunk X |
| 12 | int32 | Global chunk Y |
| 16 | uint16 | Horizontal sample spacing in source world units |
| 18 | uint16 | Height scale, 8 source world units |
| 20 | uint32 | Payload bytes, excluding header and padding |
| 24 | N × N int16 | Absolute height divided by 8; row-major south to north |
| following | (N−1) × (N−1) uint8 | Source terrain material ID per quad |

Each chunk covers 2,048 × 2,048 source world units. Its southwest corner is
`(chunk_x * 2048, chunk_y * 2048)`. One original 8,192-unit exterior cell becomes
4 × 4 chunks. Edge vertices are duplicated. Selected vertices retain exact
source heights, but detail between vertices is discarded; no adaptive error
bound or LOD stitching is implemented.

Stride 2 gives N=9: 24-byte header + 162-byte heights + 64-byte materials +
6-byte padding = 256 bytes. Each chunk describes 128 triangles if every quad is
split in two. No triangle list is stored; topology is implicit.

Material bytes are **not palette colours**. Nonzero IDs correspond to the
source LTEX index plus one. Zero denotes the default material. `materials.json`
maps the used IDs to source texture references. The exporter samples the material
at each quad's centre; texture blending, vertex colour tinting and palette
baking are future work. The preview uses analytical height colouring instead.

Missing terrain, fractional or overflowing packed heights, and material IDs
above 255 are rejected. The parser validates record bounds, BSA data bounds and
the master header's record count. Duplicate exterior cells and object IDs are
rejected; plugin override semantics and moved references are unsupported.
