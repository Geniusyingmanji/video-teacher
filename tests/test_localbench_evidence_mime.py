import base64

from PIL import Image
import pytest

from localbench.evidence import image_content


@pytest.mark.parametrize('fmt,mime',[('PNG','image/png'),('JPEG','image/jpeg'),('WEBP','image/webp')])
def test_actual_bytes_determine_mime_without_reencoding_or_changing_evidence_id(tmp_path,fmt,mime):
    path=tmp_path/'misleading.jpg'
    Image.new('RGB',(12,12),'red').save(path,format=fmt)
    parts=image_content({'id':'F_TARGET','time_s':4.5,'path':path})
    url=parts[1]['image_url']['url']
    assert url.startswith(f'data:{mime};base64,')
    assert base64.b64decode(url.split(',',1)[1])==path.read_bytes()
    assert parts[0]['text']=='F_TARGET at 4.500 seconds'


def test_unsupported_image_not_silently_mislabeled_jpeg(tmp_path):
    path=tmp_path/'bad.jpg'
    Image.new('RGB',(12,12),'red').save(path,format='BMP')
    with pytest.raises(ValueError,match='JPEG, PNG or WebP'):
        image_content({'id':'F00','time_s':0,'path':path})
