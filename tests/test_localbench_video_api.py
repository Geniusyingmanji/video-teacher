import json

import httpx
import pytest
from PIL import Image

from localbench.services import Service, ServicePool
from localbench.video_api import VideoAPI, VideoService
from localbench.source_scene import bind_source, render_source


def api(tmp_path, handler, **kwargs):
    pool = ServicePool(tmp_path/'api', max_calls=10, max_tokens=1000)
    ledger = pool.client(Service('planner', 'https://provider.test/v1', 'PRIVATE_TEST_KEY'))
    service = VideoService('video-model', 'https://provider.test/tasks',
                           'https://provider.test/tasks/{task_id}', 'PRIVATE_VIDEO_KEY', **kwargs)
    result = VideoAPI(service, ledger, max_seconds=10)
    result.http.close()
    result.http = httpx.Client(transport=httpx.MockTransport(handler))
    return result


def test_native_task_resume_and_download_do_not_resubmit_or_leak_key(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        if request.method == 'POST':
            return httpx.Response(200, json={'id': 'task-1'})
        if request.url.host == 'cdn.test':
            assert 'authorization' not in request.headers
            return httpx.Response(200, content=b'fixture-only-not-real-video')
        return httpx.Response(200, json={'status': 'succeeded', 'content': {'video_url': 'https://cdn.test/output'},
                                       'usage': {'completion_tokens': 20, 'total_tokens': 20}})
    client = api(tmp_path, handler)
    p = client.generate('lesson', 5, tmp_path/'shot')
    assert client.generate('lesson', 5, tmp_path/'shot') == p
    assert [r.method for r in calls] == ['POST', 'GET', 'GET']
    assert 'PRIVATE_VIDEO_KEY' not in (tmp_path/'shot/task.json').read_text()
    assert 'PRIVATE_VIDEO_KEY' not in (tmp_path/'api/usage.jsonl').read_text()
    with pytest.raises(ValueError, match='budget'):
        client.generate('second lesson', 6, tmp_path/'another-shot')


def test_ambiguous_submission_never_automatically_reposts(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout('network interrupted')
    client = api(tmp_path, handler)
    with pytest.raises(RuntimeError, match='outcome unknown'):
        client.generate('lesson', 5, tmp_path/'shot')
    with pytest.raises(RuntimeError, match='outcome unknown'):
        client.generate('lesson', 5, tmp_path/'shot')
    assert len(calls) == 1
    assert json.loads((tmp_path/'shot/task.json').read_text())['state'] == 'submission_unknown'


def test_pending_receipt_resumes_by_query_only(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        if request.method == 'POST': return httpx.Response(200, json={'id': 'task-1'})
        raise httpx.ReadTimeout('query interrupted')
    client = api(tmp_path, handler)
    with pytest.raises(httpx.ReadTimeout): client.generate('lesson', 5, tmp_path/'shot')
    assert json.loads((tmp_path/'shot/task.json').read_text())['task_id'] == 'task-1'
    with pytest.raises(httpx.ReadTimeout): client.generate('lesson', 5, tmp_path/'shot')
    assert [r.method for r in calls] == ['POST', 'GET', 'GET']


def test_wan3_protocol_and_credential_host_validation():
    service = VideoService('wan3.0-video', 'https://provider.test/submit',
                           'https://provider.test/tasks/{task_id}', 'key', protocol='wan3')
    body = service.request('visual', 5, 'data:image/png;base64,fixture')
    assert body['input']['media'][0]['type'] == 'first_frame'
    assert body['parameters']['duration'] == 5
    with pytest.raises(ValueError, match='credential host'):
        VideoService('video', 'https://provider.test/submit', 'https://other.test/{task_id}', 'key')


def test_general_source_annotations_preserve_input_and_reject_paths(tmp_path):
    source = tmp_path/'source.png'; Image.new('RGB', (640, 360), 'white').save(source)
    original = source.read_bytes()
    scene = {'title': 'A public diagram', 'caption': 'Locate the relevant region.',
             'teaching_lines': ['Follow the marked relationship.'],
             'source_annotations': [{'type': 'arrow', 'x': .2, 'y': .2, 'x2': .7, 'y2': .7}]}
    original_scene = {**scene, 'source_annotations': []}
    plan = bind_source({'source_edits': [], 'scenes': [original_scene, scene]}, {'local_path': str(source)}, allow_overlays=True)
    rendered, issues = render_source(plan['scenes'][1], .5, index=1, total=2, mode='code')
    assert rendered.size == (1600, 900) and issues == []
    assert source.read_bytes() == original
    scene['source_annotations'] = [{'type': 'image', 'path': '/private/file'}]
    with pytest.raises(ValueError, match='unsupported source annotation'):
        bind_source({'source_edits': [], 'scenes': [scene]}, {'local_path': str(source)}, allow_overlays=True)


def test_source_label_style_tracks_original_pixels_and_bounds(tmp_path):
    import copy
    import numpy as np
    from localbench.source_scene import validate_annotations, VIEWPORT
    source = tmp_path/'map.png'; Image.new('RGB', (1600, 900), 'white').save(source)
    blank = {'title': 'Map', 'caption': 'Locate the country.', 'teaching_lines': ['Inspect the label.'],
             'source_annotations': []}
    label = {'type': 'text', 'x': .5, 'y': .5, 'text': 'Kingdom', 'color': '#000000',
             'font_size': 22, 'align': 'center', 'stroke_width': 0}
    widths = []
    for styled in (True, False):
        mark = dict(label)
        if not styled: mark.pop('font_size')
        plan = bind_source({'source_edits': [], 'scenes': [copy.deepcopy(blank),
                           {**copy.deepcopy(blank), 'source_annotations': [mark]}]},
                           {'local_path': str(source)}, allow_overlays=True)
        frame, issues = render_source(plan['scenes'][1], .5, index=1, total=2, mode='code')
        assert issues == []
        pixels = np.asarray(frame.crop(VIEWPORT))
        yy, xx = np.where((pixels == 0).all(axis=2))
        assert len(xx) > 0
        widths.append(xx.max()-xx.min())
        assert abs((xx.min()+xx.max())/2 - (VIEWPORT[2]-VIEWPORT[0])/2) < 5
    assert widths[0] < .7 * widths[1]
    for change in ({'font_size': float('nan')}, {'font_size': True}, {'stroke_width': -1}, {'align': 'unsafe'}):
        with pytest.raises(ValueError): validate_annotations([{**label, **change}])
    overflow = {**label, 'x': 0, 'align': 'right'}
    plan = bind_source({'source_edits': [], 'scenes': [copy.deepcopy(blank),
                       {**copy.deepcopy(blank), 'source_annotations': [overflow]}]},
                       {'local_path': str(source)}, allow_overlays=True)
    _, issues = render_source(plan['scenes'][1], .5, index=1, total=2, mode='code')
    assert any(x['kind'] == 'source_annotation_text_overflow' for x in issues)
