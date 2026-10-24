# SPDX-License-Identifier: GPL-3.0-only
"""Script sound names to the converted files of the media catalogue, by index, never by copying audio.

Three kinds of names, three lookups:
  PlaySound*/PlayLoopSound*/StopSound/GetSoundPlaying "id"  -> the SOUN record id -> its file (FNAM) -> the
      catalogue's converted file (sound/pool/a<hash>.wav, tools/prepare_media_assets.py)
  Say "Vo\\...mp3" "text"                                   -> the voice file under Sound -> the converted file
  StreamMusic "Special/x.mp3"                              -> the file under Music -> the soundtrack's track number
      (tools/prepare_music.py, music/trackNN.mws)

Each name that does not resolve gets a reason: 'no SOUN record' (a name mismatch the map could not repair),
'missing source' (the game data has no such file), 'not converted' (the file exists but the catalogue has no
converted output for it, e.g. a quick build that left voices out), or 'not in the soundtrack'. Mismatches the map
repairs are kept with a note: a SOUN id written with other spacing, a file path whose case, slashes or extension
differ (the game falls back from .wav to .mp3, prepare_media_assets.resolve_sound).
"""
import json
from pathlib import Path

RATE = 11025


def _key(path):
    return path.replace('\\', '/').strip().casefold()


class MediaMap:
    def __init__(self, data, catalogue, soundtrack=None):
        """data: GameData; catalogue: the media stage's media-coverage.json (dict); soundtrack: music/soundtrack.json."""
        self.data = data
        self.entries = {}
        for row in catalogue.get('entries', []):
            if row.get('category') in ('effects', 'voices') and row.get('source'):
                self.entries[_key(row['source'])] = row
        self.excluded = set(catalogue.get('excluded') or ())
        self.inventory = set(self.entries)
        self.tracks = {}
        for t in (soundtrack or {}).get('tracks', []):
            self.tracks[_key(t['source'])] = t
        self.sounds_by_spacing = {' '.join(k.split()): k for k in data.sounds}
        self.notes = []

    @classmethod
    def from_files(cls, data, catalogue_path, soundtrack_path=None):
        catalogue = json.loads(Path(catalogue_path).read_text(encoding='utf-8'))
        soundtrack = json.loads(Path(soundtrack_path).read_text(encoding='utf-8')) if soundtrack_path else None
        return cls(data, catalogue, soundtrack)

    def _file(self, requested):
        """(catalogue row or None, how, reason) for a file path under Data Files ('sound/...')."""
        key = _key(requested)
        candidates = [(key, None)]
        if key.endswith('.wav'):
            candidates.append((key[:-4] + '.mp3', 'requested .wav, the game plays the .mp3'))
        elif key.endswith('.mp3'):
            candidates.append((key[:-4] + '.wav', 'requested .mp3, the data has the .wav'))
        for candidate, how in candidates:
            row = self.entries.get(candidate)
            if row is None:
                continue
            if row.get('status') != 'included':
                return None, how, 'not converted'
            return row, how, None
        return None, None, 'missing source'

    def _row(self, row, how, original, kind):
        out = {'resolved': True, 'path_pool': row['path'], 'seconds': (row.get('frames') or 0) / RATE,
               'source': row['source']}
        if how:
            out['note'] = how
            self.notes.append((kind, original, how))
        if _key(original) != row['source'] and not how:
            out['note'] = 'case or slashes differ'
        return out

    def sound(self, name):
        key = name.casefold()
        soun = self.data.sounds.get(key)
        fixed = None
        if soun is None:
            spaced = self.sounds_by_spacing.get(' '.join(key.split()))
            if spaced is not None:
                soun, fixed = self.data.sounds[spaced], 'id spacing differs from the SOUN record'
        if soun is None:
            return {'id': name, 'resolved': False, 'reason': 'no SOUN record', 'volume': 255, 'min': 0, 'max': 0}
        base = {'id': name, 'soun': soun['id'], 'file': soun['file'], 'volume': soun['volume'], 'min': soun['min'],
                'max': soun['max']}
        row, how, reason = self._file('sound/' + soun['file'])
        if row is None:
            base.update(resolved=False, reason=reason)
            return base
        base.update(self._row(row, how, 'sound/' + soun['file'], 'sound'))
        if fixed:
            base['note'] = fixed + ('; ' + base['note'] if base.get('note') else '')
            self.notes.append(('sound', name, fixed))
        return base

    def voice(self, path):
        row, how, reason = self._file('sound/' + path)
        if row is None:
            if reason == 'not converted' and 'voices' in self.excluded:
                reason = 'not converted (voices left out of this build)'
            return {'path': path, 'resolved': False, 'reason': reason}
        out = {'path': path}
        out.update(self._row(row, how, 'sound/' + path, 'voice'))
        return out

    def music(self, path):
        key = _key('music/' + path)
        track = self.tracks.get(key)
        how = None
        if track is None:
            name = key.rsplit('/', 1)[-1]
            hits = [t for k, t in self.tracks.items() if k.rsplit('/', 1)[-1] == name]
            if len(hits) == 1:
                track, how = hits[0], 'found by file name in another music folder'
        if track is None:
            return {'path': path, 'resolved': False, 'reason': 'not in the soundtrack', 'track': 255}
        number = int(track['file'][5:7])
        out = {'path': path, 'resolved': True, 'track': number, 'source': track['source'],
               'seconds': track.get('seconds', 0)}
        if how:
            out['note'] = how
            self.notes.append(('music', path, how))
        return out
