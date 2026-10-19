# meshoptimizer (vendored subset)

_Last updated with AmiWind v0.0.36 (11 October 2026)._

Upstream: https://github.com/zeux/meshoptimizer, release v1.3 (tag archive `v1.3.tar.gz`, SHA-256
ca4f47d451201593904b9e3067fa54b65db94bc34ab5173864950862b748a145). Licence: MIT (LICENSE.md, Arseny Kapoulkine).

Only the files the mesh simplifier needs are kept, unchanged: `src/meshoptimizer.h`, `src/simplifier.cpp`,
`src/allocator.cpp` and `LICENSE.md`. `tools/meshopt.py` compiles them with the C++ compiler of the build
environment the first time a build asks for them (no download, no prebuilt binary) and calls
`meshopt_simplify` through ctypes. Used by the CHIM mesh method `meshopt+merge` (docs/chim/MESH_METHODS.md).

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| LICENSE.md | 1,079 | f03037ca7bad1e3eb7f4a63fa6084a8baabd5ba30d3c239a9a7f35705d873e26 |
| allocator.cpp | 607 | d2cc48691fe2f4c6d097bf7a766389cfb7f83ca14a5f747e3944332656d02254 |
| meshoptimizer.h | 109,292 | e3688ef553f603391747895a5c221ef1528574cc7f8173782417a96cb531f61b |
| simplifier.cpp | 107,217 | 719303b6970398631e30724e8eebc6cd2e7e08b67fe8ab7cbf7eecafdaa08616 |
