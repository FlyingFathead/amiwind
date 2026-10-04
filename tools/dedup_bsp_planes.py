#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Exact BSP29 plane-table deduplication; no geometric approximation or mesh cuts."""
import argparse,hashlib,json,math,os,struct
from pathlib import Path
from player_hull import lumps,pack_lumps

RECORD_SIZES={1:20,3:12,5:24,6:40,7:20,9:8,10:28,11:2,12:4,13:4,14:64}
REFERENCES={7:(20,'<H'),5:(24,'<i'),9:(8,'<i')}


def _validated_lumps(raw):
    data=lumps(raw)
    spans=[]
    for i in range(15):
        offset,size=struct.unpack_from('<ii',raw,4+8*i)
        if size:spans.append((offset,offset+size,i))
        if i in RECORD_SIZES and size%RECORD_SIZES[i]:raise ValueError('Malformed BSP record size in lump '+str(i))
    spans.sort()
    if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('Overlapping BSP lumps')
    count=len(data[1])//20
    for i,(x,y,z,d,kind) in enumerate(struct.iter_unpack('<4fi',data[1])):
        if not all(math.isfinite(v) for v in (x,y,z,d)) or (x==y==z==0) or kind not in range(6):
            raise ValueError('Invalid plane record '+str(i))
    for lump,(stride,fmt) in REFERENCES.items():
        for pos in range(0,len(data[lump]),stride):
            index=struct.unpack_from(fmt,data[lump],pos)[0]
            if index<0 or index>=count:raise ValueError('Plane index outside table in lump '+str(lump))
    return data


def dedup_bsp(raw):
    """Return a verified candidate and receipt; original bytes remain immutable."""
    original=_validated_lumps(raw);data=[bytearray(lump) for lump in original]
    lookup={};ordered=[];mapping=[]
    for pos in range(0,len(original[1]),20):
        plane=bytes(original[1][pos:pos+20])
        if plane not in lookup:lookup[plane]=len(ordered);ordered.append(plane)
        mapping.append(lookup[plane])
    changes={}
    for lump,(stride,fmt) in REFERENCES.items():
        changed=0
        for pos in range(0,len(data[lump]),stride):
            old=struct.unpack_from(fmt,data[lump],pos)[0];new=mapping[old]
            if fmt=='<H' and new>65535:raise ValueError('BSP29 face plane index overflow')
            struct.pack_into(fmt,data[lump],pos,new);changed+=int(old!=new)
        changes[str(lump)]=changed
    data[1]=bytearray(b''.join(ordered))
    duplicates=len(mapping)-len(ordered)
    candidate=raw if not duplicates else pack_lumps(data)
    target=_validated_lumps(candidate);checked={}
    for lump,(stride,fmt) in REFERENCES.items():
        width=struct.calcsize(fmt);count=0
        if len(target[lump])!=len(original[lump]):raise ValueError('Reference record count changed')
        for pos in range(0,len(target[lump]),stride):
            old=struct.unpack_from(fmt,original[lump],pos)[0];new=struct.unpack_from(fmt,target[lump],pos)[0]
            if original[1][old*20:old*20+20]!=target[1][new*20:new*20+20]:raise ValueError('Resolved plane bytes changed')
            if original[lump][pos+width:pos+stride]!=target[lump][pos+width:pos+stride]:raise ValueError('Non-plane record fields changed')
            count+=1
        checked[str(lump)]=count
    unchanged=[i for i in range(15) if i not in (1,5,7,9)]
    if any(original[i]!=target[i] for i in unchanged):raise ValueError('Unrelated BSP lump changed')
    return candidate,{'method':'full20-byte exact planes, first occurrence order','source_sha256':hashlib.sha256(raw).hexdigest(),'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'planes_before':len(mapping),'planes_after':len(ordered),'duplicates_removed':duplicates,'plane_lump_bytes_saved':duplicates*20,'file_bytes_before':len(raw),'file_bytes_after':len(candidate),'file_bytes_saved':len(raw)-len(candidate),'changed_plane_index_references':changes,'resolved_plane_records_checked':checked,'unchanged_lumps':unchanged,'non_plane_record_fields_exact':True,'entity_and_pool_bindings_exact':True,'PVS_exact':True,'node_children_and_model_hull_roots_exact':True,'byte_identical':candidate==raw,'scope':'Representation-only proof. No native loading, target appearance, overall memory fit or missing geometry fixes are claimed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sidecar = args.out.with_suffix('.plane-dedup.json')
    source_identity = os.path.normcase(str(args.source.resolve()))
    for path in (args.out, sidecar):
        if os.path.normcase(str(path.resolve())) == source_identity:
            parser.error('Output or receipt aliases source; input is never overwritten')
        if path.exists():
            parser.error('Fresh BSP output and receipt required: ' + str(path))
    candidate, receipt = dedup_bsp(args.source.read_bytes())
    receipt_text = json.dumps(receipt, indent=2) + '\n'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    created_output = False
    try:
        # Reserve both names exclusively before writing either payload. A path
        # appearing after the preflight cannot be overwritten.
        with args.out.open('xb') as output:
            created_output = True
            with sidecar.open('x', encoding='utf-8') as audit:
                output.write(candidate)
                audit.write(receipt_text)
    except FileExistsError:
        # A concurrent receipt creation can leave only our empty reservation.
        # Remove that known empty file, never the existing receipt or input.
        if created_output and args.out.stat().st_size == 0:
            args.out.unlink()
        parser.error('BSP output or receipt appeared concurrently; no existing file overwritten')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
