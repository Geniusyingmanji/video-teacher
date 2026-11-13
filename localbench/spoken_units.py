"""Measured, ordered speech units for instruction-synchronized generated actions."""
from __future__ import annotations

import math
import wave
from pathlib import Path


def validate(scene):
    units = scene.get('spoken_units')
    if not isinstance(units, list) or not 1 <= len(units) <= 8:
        raise ValueError('spoken_units requires 1..8 units')
    ids = set()
    for unit in units:
        if not isinstance(unit, dict) or set(unit) != {'id','text'}:
            raise ValueError('speech unit requires exactly id and text')
        name, text = unit['id'], unit['text']
        if not isinstance(name,str) or not name or name in ids or Path(name).name != name or name in {'.','..'}:
            raise ValueError('invalid/duplicate speech unit id')
        if not isinstance(text,str) or not text.strip():
            raise ValueError('speech unit text must be nonempty')
        ids.add(name)
    if ' '.join(' '.join(u['text'] for u in units).split()) != ' '.join(scene['narration'].split()):
        raise ValueError('speech units must exactly partition scene narration')
    return units


def synthesize(scene, directory, rate, tts, output):
    from .tts import synthesize_speech
    from .pipeline import spoken_text
    from .provenance import file_hash
    units = validate(scene)
    records, payloads = [], []
    offset = 0
    for index, unit in enumerate(units):
        sub = Path(directory)/f'unit_{index:02d}'
        sub.mkdir(parents=True,exist_ok=True)
        text_path, audio_path = sub/'narration.txt', sub/'speech.wav'
        text_path.write_text(spoken_text({**scene,'narration':unit['text']}))
        synthesize_speech(text_path,audio_path,rate,tts)
        with wave.open(str(audio_path)) as wav:
            if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth()) != (24000,1,2):
                raise ValueError('speech units must be normalized mono 24 kHz PCM')
            count = wav.getnframes()
            payloads.append(wav.readframes(count))
        if count <= 0:
            raise ValueError('empty speech unit')
        records.append({'id':unit['id'],'start_s':offset/24000,'end_s':(offset+count)/24000,
                        'audio_sha256':file_hash(audio_path), 'text':unit['text']})
        offset += count
    with wave.open(str(output),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
        wav.writeframes(b''.join(payloads))
    return records


def validate_timing(scene):
    units = validate(scene)
    records = scene.get('spoken_unit_timing')
    if not isinstance(records,list) or [u.get('id') for u in records] != [u['id'] for u in units]:
        raise ValueError('missing or mismatched measured speech unit timing')
    previous = 0.0
    for unit, record in zip(units,records):
        a,b = record.get('start_s'),record.get('end_s')
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in (a,b)) or not 0 <= a < b <= scene['duration_s']:
            raise ValueError('speech unit interval outside scene')
        if abs(a-previous)>1/24000 or unit['text'] != record.get('text'):
            raise ValueError('speech unit timing/text no longer matches scene')
        previous=b
    return records
