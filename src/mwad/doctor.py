"""Read-only installation inventory; no copying or content extraction."""
from .paths import child_ci, resolve_data_files, ensure_external


def folder_inventory(path):
    if path is None or not path.is_dir():
        return {"present": False, "files": 0, "bytes": 0}
    count = size = 0
    for p in path.rglob("*"):
        if p.is_file():
            p = ensure_external(p, "audio input")
            count += 1
            size += p.stat().st_size
    return {"present": True, "files": count, "bytes": size}


def doctor(path):
    data = resolve_data_files(path)
    esm, bsa = child_ci(data, "Morrowind.esm"), child_ci(data, "Morrowind.bsa")
    sound = child_ci(data, "Sound", required=False)
    voice = child_ci(sound, "Vo", required=False) if sound and sound.is_dir() else None
    return {"data_files": str(data), "terrain_inputs_present": True,
            "esm_bytes": esm.stat().st_size, "bsa_bytes": bsa.stat().st_size,
            "music": folder_inventory(child_ci(data, "Music", required=False)),
            "sound": folder_inventory(sound), "voices": folder_inventory(voice),
            "scope": "Presence and size inventory only. Mod load order and loose overrides are not applied."}
