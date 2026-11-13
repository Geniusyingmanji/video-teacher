from pathlib import Path

import pytest
from PIL import Image,ImageDraw

from localbench.region_review import verify_saved_frames
from localbench.verification import final_color_crop


def test_redecoded_video_rejects_changed_legacy_frame_without_hash_field(tmp_path,monkeypatch):
    from localbench import region_review
    im=Image.new('RGB',(16,12),'#80a0e0');path=tmp_path/'frame.jpg';im.save(path,quality=88)
    packet={'video_path':'fake_video','frames':[{'id':'F00','frame_index':0,'path':str(path)}]}
    monkeypatch.setattr(region_review.imageio_ffmpeg,'read_frames',lambda *a,**k:iter([{'size':(16,12)},im.tobytes()]))
    assert set(verify_saved_frames(packet))=={'F00'}
    Image.new('RGB',(16,12),'black').save(path,quality=88)
    with pytest.raises(ValueError,match='does not match actual'):verify_saved_frames(packet)


def test_color_crop_ignores_colored_title_and_lower_teaching_panel():
    im=Image.new('RGB',(400,300),'white');draw=ImageDraw.Draw(im)
    draw.rectangle((10,5,390,15),fill='blue')
    draw.rectangle((10,260,390,280),fill='blue')
    draw.line((140,100,230,150),fill='purple',width=3)
    bbox=final_color_crop(im)
    assert 100<bbox[0]<140 and 230<bbox[2]<270
    assert bbox[1]>=30 and bbox[3]<219
