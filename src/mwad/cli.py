import argparse
import json
import struct
import re
from pathlib import Path
from .paths import init_workspace, setup_workspace, read_workspace, ensure_external


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mwad", description="Morrowind Amiga prototype tools; all game data stays outside the repository.")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="Remember the original game folder in an external workspace")
    setup.add_argument("--data-files", required=True, type=Path)
    setup.add_argument("--workspace", required=True, type=Path)
    setup.add_argument("--target", choices=("a500", "a1200"), default="a500")
    convert = commands.add_parser("convert", help="Build and verify the selected terrain prototype from a configured workspace")
    convert.add_argument("--workspace", required=True, type=Path)
    convert.add_argument("--name", default="seyda-neen")
    convert.add_argument("--center", type=int, nargs=2, default=[-2, -9], metavar=("X", "Y"))
    convert.add_argument("--radius", type=int, default=1)
    convert.add_argument("--stride", type=int, choices=(1, 2, 4, 8), default=2)
    init = commands.add_parser("init-workspace", help="Create an empty external data workspace")
    init.add_argument("path", type=Path)
    doc = commands.add_parser("doctor", help="Inspect installed game files without changing them")
    doc.add_argument("--data-files", type=Path, required=True)
    audit = commands.add_parser("audit", help="Convert an exterior region to experimental terrain packets")
    audit.add_argument("--data-files", type=Path, required=True)
    audit.add_argument("--out", type=Path, required=True)
    audit.add_argument("--center", type=int, nargs=2, default=[-2, -9], metavar=("X", "Y"))
    audit.add_argument("--radius", type=int, default=1)
    audit.add_argument("--stride", type=int, choices=(1, 2, 4, 8), default=2)
    audit.add_argument("--dialogue-search", default="", help="Optional case-insensitive text match; results go only to external output")
    check = commands.add_parser("verify", help="Compare exported packet data with decoded source grids")
    check.add_argument("area", type=Path)
    preview = commands.add_parser("preview", help="Render a PC inspection image; requires the preview extra")
    preview.add_argument("area", type=Path)
    preview.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            print(json.dumps(setup_workspace(args.workspace, args.data_files, args.target), indent=2))
        elif args.command == "convert":
            from .audit import audit, json_write
            from .verify import verify
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", args.name):
                raise ValueError("Output name must use lowercase letters, digits, hyphens or underscores")
            workspace, state = read_workspace(args.workspace)
            if "data_files" not in state or state.get("target") not in ("a500", "a1200"):
                raise ValueError("Run setup with the original game folder first")
            output = ensure_external(workspace / "generated" / args.name, "converted data")
            audit(Path(state["data_files"]), output, args.center, args.radius, args.stride)
            checked = verify(output)
            json_write(output / "conversion.json", {"format": 1, "target": state["target"],
                       "scope": "terrain prototype; target profile records intent, not measured performance",
                       "verification": checked})
        elif args.command == "init-workspace":
            print(json.dumps(init_workspace(args.path), indent=2))
        elif args.command == "doctor":
            from .doctor import doctor
            print(json.dumps(doctor(args.data_files), indent=2))
        elif args.command == "audit":
            from .audit import audit
            audit(args.data_files, args.out, args.center, args.radius, args.stride, args.dialogue_search)
        elif args.command == "verify":
            from .verify import verify
            verify(args.area)
        elif args.command == "preview":
            try:
                from .preview import preview
            except ImportError:
                parser.exit(1, "Preview dependencies missing. Install this checkout with: python -m pip install -e '.[preview]'\n")
            preview(args.area, args.output)
            print(json.dumps({"preview": str(args.output)}))
    except (ValueError, OSError, struct.error, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
