#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Private registration pages, dialogue and birthsign art from owned inputs."""
import argparse
from html.parser import HTMLParser
import io
import hashlib
import os
import tempfile
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import records,subrecords,string,BSA
from mwad.npc import load_master,text
from mwad.paths import child_ci,resolve_data_files,ensure_external
from mwad import font_sources
from npc_geometry import Assets
from prepare_ui import pack_truetype, pack_font
from build_font_options import INK_MODES, add_font_options, resolve_font_options


class BookText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in ('p','br','div'):self.parts.append('\n')
    def handle_data(self,data):self.parts.append(data)
    def value(self):return re.sub(r'\n{3,}','\n\n',''.join(self.parts).replace('\r','')).strip()


def _write_generated(path, payload):
    """Replace one generated output only after its complete bytes are written."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".paper-font-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_paper_font(data_files, scene, bitmap_paper_ink="filled"):
    """Keep the preferred TTF, or bake the approved paper-only bitmap candidate.

    The normal book12/magic12 assets remain the small-UI font sources. The
    optional paper12 asset is selected only inside the native paper renderer.
    """
    if bitmap_paper_ink not in INK_MODES:
        raise ValueError("Bitmap paper ink must be filled or original")
    data_files = resolve_data_files(data_files)
    scene = ensure_external(Path(scene), "reading conversion")
    gfx = scene / "id1/gfx"
    gfx.mkdir(parents=True, exist_ok=True)
    fonts = font_sources.discover(data_files)
    magic = fonts["magic"]
    payload = None
    ttf_error = None
    if magic["ttf_path"] is not None:
        try:
            payload = pack_truetype(magic["ttf_path"], 12)
        except (OSError, ValueError) as exc:
            ttf_error = str(exc)
            print(f"[warning] Preferred paper TTF could not be converted safely: {ttf_error}", flush=True)
    if payload is not None:
        source = magic["ttf_path"]
        mode = "ttf"
        treatment = "not applied (TTF)"
        asset = "gfx/book12.awf"
        output = gfx / "book12.awf"
        legacy = payload
        stale = [gfx / "paper12.awf"]
    elif magic["bitmap_ready"]:
        source = magic["bitmap_path"]
        mode = "bitmap-fallback" if ttf_error else "bitmap"
        treatment = bitmap_paper_ink
        legacy = pack_font(source, 12)
        payload = pack_font(source, 12, paper_ink="filled") if treatment == "filled" else legacy
        # The correction changes coverage only: preserve all 256 metrics and size.
        if payload[:2056] != legacy[:2056] or len(payload) != len(legacy):
            raise ValueError("Paper correction changed font metrics or payload size")
        asset = "gfx/paper12.awf" if treatment == "filled" else "gfx/magic12.awf"
        output = gfx / "paper12.awf" if treatment == "filled" else None
        # A rerun must not retain a TTF or filled asset from the previous choice.
        stale = [gfx / "book12.awf"]
        if output is None:
            stale.append(gfx / "paper12.awf")
        for warning in font_sources.fallback_warnings(fonts):
            print("[warning] " + warning, flush=True)
    else:
        reason = f" TTF conversion error: {ttf_error}." if ttf_error else ""
        raise ValueError(
            "No usable Magic Cards paper font: provide BookArt/Magic Cards.ttf "
            "or the complete Fonts/Magic_Cards_Regular.fnt + TEX pair." + reason)
    report = {
        "format": "AmiWind paper font conversion 1",
        "source_mode": mode,
        "source": source.relative_to(data_files).as_posix(),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "atlas_sha256": (hashlib.sha256(magic["atlas_path"].read_bytes()).hexdigest()
                         if mode != "ttf" else None),
        "requested_bitmap_paper_ink": bitmap_paper_ink,
        "effective_paper_ink": treatment,
        "runtime_asset": asset,
        "generated_asset": asset if output is not None else None,
        "expected_awf_sha256": hashlib.sha256(payload).hexdigest(),
        "ordinary_awf_sha256": hashlib.sha256(legacy).hexdigest(),
        "awf_bytes": len(payload),
        "size_px": 12,
        "ttf_error": ttf_error,
        "dialogue_and_menu_assets_changed": False,
    }
    if output is not None:
        _write_generated(output, payload)
    for old in stale:
        old.unlink(missing_ok=True)
    _write_generated(gfx / "paper-font-conversion.json",
                     (json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(f"[font] Paper source: {report['source']} ({mode})", flush=True)
    print(f"[font] Bitmap paper ink: {treatment}; reading uses {asset}", flush=True)
    if output is None:
        print("[font] Original paper treatment: magic12.awf is supplied by the UI conversion stage.", flush=True)
    print("[font] Dialogue/menu font coverage unchanged.", flush=True)
    return report


def prepare(data_files,scene,bitmap_paper_ink="filled"):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'reading conversion')
    font_report=prepare_paper_font(data_files,scene,bitmap_paper_ink)
    master=child_ci(data_files,'Morrowind.esm');assets=Assets(data_files,BSA(child_ci(data_files,'Morrowind.bsa')))
    dest=scene/'id1/reading';dest.mkdir(exist_ok=True)
    palette=(scene/'id1/gfx/palette.lmp').read_bytes();pal=Image.new('P',(1,1));pal.putpalette(palette)
    def art(path,out,size):
        raw=assets.read(path);im=Image.open(io.BytesIO(raw)).convert('RGB').resize(size,Image.Resampling.BOX)
        (dest/out).write_bytes(b'AWI1'+struct.pack('<HH',*size)+im.quantize(palette=pal,dither=Image.Dither.NONE).tobytes())
    def page(out,title,source):
        parser=BookText();parser.feed(source)
        raw=(title+'\n'+parser.value()).encode('cp1252')+b'\0'
        if len(raw)>8192:raise ValueError('Reading page exceeds bounded text budget')
        (dest/(out+'.txt')).write_bytes(raw)
    signs=[]
    for tag,flags,raw in records(master.read_bytes()):
        if tag not in ('BSGN','BOOK'):continue
        f=dict(subrecords(raw));identifier=string(f['NAME']).casefold()
        if tag=='BSGN':signs.append((identifier,f))
        elif identifier in ('chargen statssheet','bk_a1_1_directionscaiuscosades'):
            page('papers' if identifier=='chargen statssheet' else 'directions',string(f['FNAM']),string(f['TEXT']))
    kinds,_,topics=load_master(master)
    for i,(identifier,f) in enumerate(sorted(signs)):
        path='textures/'+str(PurePosixPath(string(f['TNAM']).replace('\\','/')).with_suffix('.dds'))
        art(path,f'birth{i:02d}.awi',(96,112))
        page(f'birth{i:02d}',string(f['FNAM']),string(f.get('DESC',b'')))
    art('textures/scroll.dds','paper.awi',(300,150))
    for topic,stem in [('greeting 1','captain_greeting'),('duties','captain_duties')]:
        candidates=[f for f in topics[topic] if text(f,'ONAM').casefold()=='chargen captain' and
                    ('removeitem' if topic=='greeting 1' else 'additem') in text(f,'BNAM').casefold()]
        if len(candidates)!=1:raise ValueError('Ambiguous captain dialogue branch: '+topic)
        page(stem,'Sellus Gravius',text(candidates[0],'NAME').replace('%name',text(kinds['NPC_']['chargen captain'],'FNAM')))
    return {'birthsign_images':len(signs),
            'book_font':font_report['runtime_asset'], 'paper_font':font_report}



if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    add_font_options(p)
    a=p.parse_args()
    try:
        options=resolve_font_options(a)
        print(json.dumps(prepare(a.data_files,a.scene,options["bitmap_paper_ink"]),indent=2))
    except (OSError, ValueError) as exc:
        p.exit(1, f"Error: {exc}\n")
