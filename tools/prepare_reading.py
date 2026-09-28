#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Private registration pages, dialogue and birthsign art from owned inputs."""
import argparse
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import struct
import sys
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import records,subrecords,string,BSA
from mwad.npc import load_master,text
from mwad.paths import child_ci,resolve_data_files,ensure_external
from npc_geometry import Assets
from prepare_ui import pack_truetype


class BookText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in ('p','br','div'):self.parts.append('\n')
    def handle_data(self,data):self.parts.append(data)
    def value(self):return re.sub(r'\n{3,}','\n\n',''.join(self.parts).replace('\r','')).strip()


def prepare(data_files,scene):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'reading conversion')
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
        path='textures/'+str(Path(string(f['TNAM']).replace('\\','/')).with_suffix('.dds'))
        art(path,f'birth{i:02d}.awi',(96,112))
        page(f'birth{i:02d}',string(f['FNAM']),string(f.get('DESC',b'')))
    art('textures/scroll.dds','paper.awi',(300,150))
    for topic,stem in [('greeting 1','captain_greeting'),('duties','captain_duties')]:
        candidates=[f for f in topics[topic] if text(f,'ONAM').casefold()=='chargen captain' and
                    ('removeitem' if topic=='greeting 1' else 'additem') in text(f,'BNAM').casefold()]
        if len(candidates)!=1:raise ValueError('Ambiguous captain dialogue branch: '+topic)
        page(stem,'Sellus Gravius',text(candidates[0],'NAME').replace('%name',text(kinds['NPC_']['chargen captain'],'FNAM')))
    # Keep the existing bitmap menu font. This optional extra atlas is only for
    # reading pages; no source font is bundled in the public repository.
    try:font=child_ci(child_ci(data_files,'BookArt'),'Magic Cards.ttf')
    except FileNotFoundError:font=None
    if font:(scene/'id1/gfx/book12.awf').write_bytes(pack_truetype(font,12))
    return {'birthsign_images':len(signs),'book_font':'owned TTF to AWF1' if font else 'existing bitmap fallback'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.scene),indent=2))
