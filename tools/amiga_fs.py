#!/usr/bin/env python3
"""Check legacy root metadata; normalize only a known modern-field mismatch.

AmigaDOS DOS0..3 reserves root word -4. Some host formatters populate it with
DOS type (a DOS6/7 field), which old ROM validation can follow as a hash link.
This is not a general damaged-filesystem repair tool. Inputs are never edited
by the CLI: --fixed-copy writes a separate external image.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external


def legacy_root(data, dos_type, normalize=False):
    if dos_type not in range(0x444f5300,0x444f5304):
        raise ValueError('Only legacy DOS0..3 are supported by this check')
    if len(data)!=512:
        raise ValueError('Expected a 512-byte root block')
    words=list(struct.unpack('>128I',data))
    if words[0]!=2 or words[-1]!=1 or words[3]!=72 or sum(words)&0xffffffff:
        raise ValueError('Invalid root structure or checksum; do not apply this targeted fix')
    if words[1] or words[2] or words[4] or words[-3] or words[-2]:
        raise ValueError('Unexpected legacy root fields; requires separate investigation')
    marker=words[-4]
    if marker not in (0,dos_type):
        raise ValueError('Unknown root reserved value; requires separate investigation')
    if marker and not normalize:
        raise ValueError('Legacy root word -4 contains DOS marker '+hex(marker))
    if marker:
        words[-4]=0;words[5]=0;words[5]=(-sum(words))&0xffffffff
    return struct.pack('>128I',*words)


def check_image(path, normalize=False, partition=None):
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    from amitools.fs.block.BootBlock import BootBlock
    dev=BlkDevFactory().open(str(path),read_only=not normalize,
                             options={'part':partition} if partition else None)
    try:
        boot=BootBlock(dev);boot.read()
        raw=dev.read_block(boot.calc_root_blk)
        corrected=legacy_root(raw,boot.dos_type,normalize)
        changed=corrected!=raw
        if changed:dev.write_block(boot.calc_root_blk,corrected)
        legacy_root(dev.read_block(boot.calc_root_blk),boot.dos_type)
        return {'root_block':boot.calc_root_blk,'dos_type':hex(boot.dos_type),
                'legacy_reserved_field':0,'changed':changed}
    finally:dev.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('image',type=Path);p.add_argument('--partition')
    p.add_argument('--fixed-copy',type=Path,help='Create a corrected copy; refuse existing paths')
    a=p.parse_args()
    try:
        src=ensure_external(a.image,'disk input')
        if a.fixed_copy:
            dst=ensure_external(a.fixed_copy,'corrected disk copy')
            if src.resolve()==dst.resolve():raise ValueError('Input and output must differ')
            with dst.open('xb') as out,src.open('rb') as inp:shutil.copyfileobj(inp,out)
            result=check_image(dst,True,a.partition)
        else:result=check_image(src,False,a.partition)
        print(json.dumps(result,indent=2))
    except (OSError,ValueError) as e:p.exit(1,str(e)+'\n')

if __name__=='__main__':main()
