"""Build a local contact sheet from verified videos for manual inspection."""
import io
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
if __name__ == '__main__':
    for result in json.loads((HERE / 'verified_results.json').read_text()):
        if not result.get('complete'):
            continue
        duration = float(result['ffprobe']['format']['duration'])
        sheet = Image.new('RGB', (854, 540), 'white')
        draw = ImageDraw.Draw(sheet)
        for index, fraction in enumerate((.15, .4, .65, .9)):
            timestamp = duration * fraction
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(timestamp),
                '-i', result['video'], '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                capture_output=True, check=True).stdout
            frame = Image.open(io.BytesIO(raw)).convert('RGB').resize((427, 240))
            x, y = (index % 2) * 427, (index // 2) * 270
            sheet.paste(frame, (x, y))
            draw.text((x+8, y+244), f'{result["source_case_id"]}  t={timestamp:.1f}s', fill='black')
        sheet.save(HERE / f'preview_{result["source_case_id"]}.png')
