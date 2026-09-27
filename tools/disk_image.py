"""Make a KS 1.3 OFS hard disk with small partitions and verified contents."""
import hashlib
from pathlib import Path
import subprocess
from amiga_fs import check_image

PARTITION_MIB = 32
PAYLOAD_LIMIT = 28 * 1024 * 1024


def music_layout(tracks):
    """Preserve playlist order, leaving room for OFS and directory overhead."""
    partitions = [{"device": "DH0", "volume": "MWBOOT", "tracks": []}]
    used = 0
    for track in tracks:
        size = track["bytes"]
        if size <= 0 or size > PAYLOAD_LIMIT:
            raise ValueError("A music file exceeds the small-partition payload budget")
        if used + size > PAYLOAD_LIMIT:
            i = len(partitions)
            partitions.append({"device": f"DH{i}", "volume": f"MWMUSIC{i}", "tracks": []})
            used = 0
        partitions[-1]["tracks"].append(track["file"])
        used += size
    return partitions


def music_paths(layout):
    return {name: f"{part['volume']}:music/{name}"
            for part in layout for name in part["tracks"]}


def write_hdf(out, version, layout, xdftool, rdbtool):
    out = Path(out)
    image = out / f"MorrowindDemo-v{version}.hdf"
    # 64 sectors/cylinder, 512-byte blocks; one cylinder holds the RDB.
    cylinders = 1 + len(layout) * PARTITION_MIB * 32
    command = [rdbtool, str(image), "create", f"chs={cylinders},1,64", "+", "init"]
    partition_images = []
    files = []
    for index, part in enumerate(layout):
        path = out / f"partition-{index}.hdf"
        partition_images.append(path)
        disk_files = [("music/" + name, out / "music" / name) for name in part["tracks"]]
        args = [xdftool, str(path), "create", f"size={PARTITION_MIB}Mi", "+", "format", part["volume"], "ofs",
                "+", "makedir", "music"]
        if index == 0:
            args += ["+", "boot", "install", "+", "makedir", "c", "+", "makedir", "s"]
            disk_files += [("c/MorrowindDemo", out / "MorrowindDemo"),
                           ("s/startup-sequence", out / "startup-sequence")]
        for name, original in disk_files:
            args += ["+", "write", str(original), name]
            files.append((part["device"], name, original))
        subprocess.run(args, check=True, capture_output=True)
        command += ["+", "addimg", str(path), "name=" + part["device"], f"bootable={int(index == 0)}", "pri=0"]
    for part_image in partition_images:check_image(part_image,normalize=True)
    subprocess.run(command, check=True, capture_output=True)
    check = out / "disk-readback.tmp"
    for device, name, original in files:
        subprocess.run([xdftool, str(image), "open", "part=" + device, "+", "read", name, str(check)],
                       check=True, capture_output=True)
        if hashlib.sha256(check.read_bytes()).digest() != hashlib.sha256(original.read_bytes()).digest():
            raise ValueError(f"Disk readback differs: {device}:{name}")
        check.unlink()
    for path in partition_images:
        path.unlink()
    storage = {"container": "RDB", "filesystem": "OFS", "block_bytes": 512,
               "geometry": {"cylinders": cylinders, "heads": 1, "sectors": 64},
               "partition_mib": PARTITION_MIB, "partitions": layout}
    return {"name": image.name, "bytes": image.stat().st_size,
            "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}, storage
