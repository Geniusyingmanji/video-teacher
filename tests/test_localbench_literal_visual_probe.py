import json

import pytest
from PIL import Image, ImageDraw

from localbench.literal_visual_probe import crop_pixels, messages, validate


def test_outside_caption_change_cannot_change_crop(tmp_path):
    a=Image.new('RGB',(100,80),'white');draw=ImageDraw.Draw(a)
    draw.line((15,15,40,30),fill='black',width=2)
    b=a.copy();ImageDraw.Draw(b).rectangle((0,60,99,79),fill='red')
    assert crop_pixels(a,[10,10,50,40],3).tobytes()==crop_pixels(b,[10,10,50,40],3).tobytes()
    c=a.copy();ImageDraw.Draw(c).line((15,20,40,20),fill='black',width=2)
    assert crop_pixels(a,[10,10,50,40],3).tobytes()!=crop_pixels(c,[10,10,50,40],3).tobytes()


@pytest.mark.parametrize('box',[[-1,0,5,5],[0,0,101,10],[5,5,5,10],[0.0,0,5,5]])
def test_invalid_box_does_not_silently_pad_or_clip(box):
    with pytest.raises(ValueError):crop_pixels(Image.new('RGB',(100,80)),box,3)


def test_observer_request_does_not_forward_reference_or_caption(tmp_path):
    path=tmp_path/'crop.jpg';Image.new('RGB',(10,10),'white').save(path)
    frame={'id':'F_CROP','time_s':4.5,'path':str(path),'caption':'SECRET_CAPTION',
           'reference':'SECRET_REFERENCE','score':1,'source_code':'SECRET_CODE'}
    request=messages(frame,'C','LG')
    serialized=json.dumps(request)
    assert not any(x in serialized for x in ['SECRET_CAPTION','SECRET_REFERENCE','SECRET_CODE'])
    assert json.loads(request[1]['content'][0]['text'])['start_label']=='C'


def test_unclear_not_converted_to_a_defect_or_direction():
    row={'stroke_class':'unclear','width_trend':'unclear','observations':['Marks too small to separate.'],
         'uncertainty':'Cannot resolve stroke geometry.'}
    assert validate(row)==row
    with pytest.raises(ValueError):validate({**row,'width_trend':'widens_toward_end'})
    with pytest.raises(ValueError):validate({**row,'score':1})
