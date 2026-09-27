# Legacy filesystem revalidation fault

## Confirmed cause

The owner reported `Error validating AMIWIND / Block 1146049281 out of range`.
The decimal block value is `0x444f5301`, the DOS1 filesystem marker. The shipped
v0.0.11-dev2 HDF had that value at root-block longword -4 (byte 496), despite
being a legacy FFS/DOS1 volume. This is a defect in our image-building pipeline.

The host formatter (amitools 0.8.1) sets a modern filesystem-type field when
creating every volume. That location is reserved in the legacy root structure.
The root checksum was valid and normal file reads and boots passed; neither
payload readback nor the general host filesystem scan caught the incompatibility.

The primary [AmigaDOS root-block documentation](https://wiki.amigaos.net/wiki/DCFS_and_LNFS_Low_Level_Data_Structures)
describes the reserved fields and the bitmap flag that requests revalidation.
The paired native experiment is the decisive evidence for this particular image.

## Reproduction and fix

1. Copy the released dev2 HDF. Keep its payload intact and set only the root
   bitmap-valid flag to zero, updating the checksum.
2. Boot under FS-UAE 3.1.66 / A1200 KS3.1 40.68. The exact owner requester appears.
3. Make another copy; zero root longword -4, recompute the checksum and again
   mark the bitmap invalid. It revalidates and boots into the scene.
4. The bad copy remains bitmap-invalid; the corrected copy is marked valid by
   the native filesystem after revalidation. No ROM/controller change is needed.

We do not know what originally dirtied the owner's image. An interrupted write
is one possibility, not an established cause. Re-extracting a clean archive
hides the latent field defect until validation is needed again.

`tools/amiga_fs.py` now checks the legacy structure/checksum and zeroes only the
known DOS-type mismatch during image creation. It leaves bitmap state alone;
it does not falsely declare a damaged volume valid. Unknown root contents,
invalid checksums and modern formats are rejected. Both the AGA FFS and earlier
A500 OFS image builders apply the check to new outputs. Old ZIPs stay immutable.

## Check or make a targeted corrected copy

Requires the documented amitools dependency, installed on the host:

```sh
python3 tools/amiga_fs.py /private/old.hdf --partition DH0
python3 tools/amiga_fs.py /private/old.hdf --partition DH0 --fixed-copy /private/corrected.hdf
```

The CLI never edits its input and refuses existing output paths or outputs
inside the public repository. The second command is a targeted compatibility
repair, not a general recovery tool for already damaged payloads or allocation
maps. Prefer rebuilding/re-extracting the corrected checkpoint where possible.

Regression gates include synthetic legacy roots, valid-checksum normalization,
unknown-corruption rejection, full HDF payload readback, and native forced
revalidation followed by scene use, clean quit and relaunch. ROM/emulator hashes
and the final gate results are in [checkpoint-010](CHECKPOINT_010_VALIDATION.md).
