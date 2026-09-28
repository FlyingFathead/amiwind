# Apply v0.0.20

Exact incremental base: GitHub main commit
`3305c9861718553acdbec76f825bfad884e0bb94` (v0.0.19, including the README/media
corrections). This is not the earlier frozen v0.0.19 release ZIP. Use the full
source ZIP for other baselines. Both source ZIPs have one `amiwind/` root.
No baseline paths are deleted. Retain local work before overlaying any update.

This release adds the quieter ship-ambience mixer gain, incident register,
coordinate-on behavior, corrected FS-UAE option and two array-bounds fixes.
Rebuild the playable image to apply the per-channel mixer gain; updating public
source alone does not modify an existing HDF. The matching private playable
contains the rebuilt runtime and original converted audio and must remain private.
The ship-exit and dock/menu freezes remain unresolved.

The accompanying handoff contains package hashes, validation results and the
owner's apply/publication workflow. Previous release archives remain immutable.

## Host-tool packaging revision 2

The separately named `AmiWind-v0.0.20-public-source-r2.zip` and
`AmiWind-v0.0.20-public-incremental-r2.zip` add the portable FS-UAE launcher,
its synthetic tests and documentation. The incremental base remains the exact
v0.0.19 commit above; it includes the v0.0.20 maintenance changes as well.
The runtime remains v0.0.20. The private `-private-playable-r2.zip` adds the
launcher beside the unchanged HDF. See FS-UAE-LAUNCHER.md for use.
