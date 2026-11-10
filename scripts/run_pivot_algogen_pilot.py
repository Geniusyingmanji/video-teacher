"""Run two author pipelines after the existing eight-video evaluation finishes."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'results/pivot_algogen_pilot_20261110'
REPORT = ROOT/'results/reports/pivot_algogen_pilot_20261110'
ADAPTER = ROOT/'research/reproduction_adapters'


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
    temp.replace(path)


def execute(method):
    folder = RUN/method
    folder.mkdir(exist_ok=True)
    source = Path('/root/research/PIVOT' if method == 'pivot' else '/root/research/ALGOGEN-lab')
    interpreter = Path('/root/pivot-env/bin/python' if method == 'pivot' else '/root/algogen-env/bin/python')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ADAPTER), str(source/'renderer'), str(source)]), OPENAI_API_KEY='local', SILICONFLOW_API_KEY='local',
        OPENAI_BASE_URL='http://127.0.0.1:8000/v1', REPRO_LOCAL_PORTS='8000,8001,8002,8003',
        REPRO_CHAT_LOG=str(folder/'calls'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1', PATH=str(interpreter.parent)+os.pathsep+os.environ['PATH'])
    # Do not use an inherited paid fallback provider.
    env.pop('ANTHROPIC_API_KEY', None)
    env.update(LAN_VIDEO_MODEL='qwen3.8-27b', LAN_VIDEO_LANGUAGE='en',
               LAN_VIDEO_OUTPUT_BASE=str(folder/'outputs'), LAN_VIDEO_API_LOG=str(folder/'author_api.jsonl'))
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    patch = subprocess.check_output(['git', '-C', str(source), 'diff'])
    (folder/'source.patch').write_bytes(patch)
    result = {'method': method, 'source': str(source), 'commit': commit,
        'source_patch_sha256': hashlib.sha256(patch).hexdigest(),
        'adapter_sha256': hashlib.sha256((ADAPTER/'sitecustomize.py').read_bytes()).hexdigest(),
        'model_substitution': 'All author chat models replaced by local Qwen3.8-27B; four replicas',
        'inference_adaptation': 'thinking disabled; omitted completion budget becomes 8192; existing budgets retained',
        'scope': 'one author-pipeline inference pilot; not original-model or full benchmark reproduction'}
    if method == 'pivot':
        command = [str(interpreter), '-u', '-m', 'video_tutor.cli', '--only', 'The determinant',
                   '--language', 'en', '--report', str(folder/'author_report.json')]
        result['dependency_fix'] = 'Author Manim 0.19.1 requires NumPy>=2; replace conflicting NumPy 1.26.4 pin with 2.2.6. edge-tts 7.2.8 returned 403; use verified 7.3.1.'
    else:
        command = [str(interpreter), '-u', 'run_pipeline.py', '--only', 'sorting_leetcode_179_seed_02',
                   '--case-root', str(folder/'outputs')]
        result['author_input'] = 'example/sorting_leetcode_179_seed_02.txt (Largest Number)'
        shutil.copy2(source/result['author_input'].split(' (')[0], folder/'input.txt')
    result['command'] = command
    versions = subprocess.check_output([str(interpreter), '-c',
        'import importlib.metadata,json;print(json.dumps({x:importlib.metadata.version(x) for x in ["manim","numpy","openai","pillow","scipy"]}))'], text=True)
    result['dependencies'] = json.loads(versions)
    dump(folder/'provenance.json', result)
    start = time.monotonic()
    with (folder/'run.log').open('a') as log:
        code = subprocess.run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    result.update(exit_code=code, seconds=time.monotonic()-start)
    videos = list((folder/'outputs').rglob('final.mp4' if method == 'pivot' else 'llm_video.mp4'))
    result['videos'] = []
    for video in videos:
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)], capture_output=True, text=True)
        decode = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], capture_output=True, text=True)
        row = {'source': str(video), 'probe': json.loads(probe.stdout) if probe.returncode == 0 else None,
               'decode_exit': decode.returncode, 'decode_error': decode.stderr,
               'sha256': hashlib.sha256(video.read_bytes()).hexdigest()}
        if probe.returncode == 0 and decode.returncode == 0:
            delivery = ROOT/'delivery/最终视频'/('PIVOT_试跑' if method == 'pivot' else 'ALGOGEN_试跑')
            delivery.mkdir(parents=True, exist_ok=True)
            destination = delivery/('行列式.mp4' if method == 'pivot' else '最大数排序.mp4')
            shutil.copy2(video, destination)
            row['delivered'] = str(destination)
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf',
                f'fps=1/{max(1,float(row["probe"]["format"]["duration"])/8)},scale=480:-1,tile=4x2',
                '-frames:v', '1', '-y', str(folder/'overview.jpg')], check=True)
        result['videos'].append(row)
    result['rendered_video'] = bool(result['videos'])
    result['quality_accepted'] = False
    result['acceptance_status'] = 'render/decode pilot only; full teaching-quality review still required'
    if method == 'pivot':
        sessions = []
        for p in (folder/'outputs').rglob('session.json'):
            sessions.append({'path': str(p), 'data': json.loads(p.read_text())})
        result['author_sessions'] = sessions
    else:
        result['author_aes_completed'] = bool(list((folder/'outputs').rglob('aes_result.json')))
    dump(folder/'result.json', result)
    REPORT.mkdir(parents=True, exist_ok=True)
    dump(REPORT/(method+'_result.json'), result)
    shutil.copy2(folder/'source.patch', REPORT/(method+'_source.patch'))
    if (folder/'overview.jpg').exists():
        shutil.copy2(folder/'overview.jpg', REPORT/(method+'_overview.jpg'))
    return result


def main():
    RUN.mkdir(exist_ok=True)
    dump(RUN/'state.json', {'stage': 'waiting_for_existing_evaluation', 'methods': ['pivot', 'algogen']})
    evaluation = ROOT/'results/code2video_eight_full_eval_20261110/eval/aggregate.json'
    deadline = time.monotonic()+21600
    while not evaluation.is_file():
        if time.monotonic()>deadline:
            raise RuntimeError('Existing evaluation did not finish; pilots not started')
        time.sleep(30)
    dump(RUN/'state.json', {'stage': 'running', 'methods': ['pivot', 'algogen'], 'started_at': time.time()})
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(execute, method): method for method in ['pivot', 'algogen']}
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                row = {'method': futures[future], 'error': repr(exc), 'rendered_video': False}
                dump(RUN/futures[future]/'result.json', row)
                results.append(row)
            dump(RUN/'results.json', results)
    dump(RUN/'state.json', {'stage': 'finished', 'methods_completed': len(results),
                           'methods_with_video': sum(r.get('rendered_video', False) for r in results)})
    dump(REPORT/'summary.json', results)
    subprocess.run(['git', 'add', str(REPORT)], cwd=ROOT, check=True)
    subprocess.run(['git', '-c', 'user.name=Codex', '-c', 'user.email=codex@openai.com', 'commit',
                    '-m', 'Record actual PIVOT and ALGOGEN pilot outcomes', '--', str(REPORT)], cwd=ROOT, check=True)
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
