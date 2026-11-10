"""Run the author's Planner/Coder/Critic flow without project lesson contracts.

Local Qwen replaces the author's API models; sampled frames replace native
video input. This reproduces the available method with explicit substitutions.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'research/code2video/Code2Video'
sys.path[:0] = [str(ROOT), str(SOURCE / 'src')]


class LoggedAPI:
    """Module-level callable so author process workers can serialize it."""
    def __init__(self, directory, ports=(8000,)):
        self.directory = Path(directory)
        self.ports = tuple(ports)

    def __call__(self, prompt, max_tokens=10000):
        from openai import OpenAI
        name = uuid.uuid4().hex
        (self.directory / (name + '.prompt.txt')).write_text(prompt)
        port = self.ports[int(name, 16) % len(self.ports)]
        (self.directory / (name + '.endpoint.json')).write_text(json.dumps({'port': port}))
        result = OpenAI(base_url=f'http://127.0.0.1:{port}/v1', api_key='local', timeout=600,
                        max_retries=1).chat.completions.create(
            model='qwen3.8-27b', messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_tokens, temperature=.6,
            extra_body={'chat_template_kwargs': {'enable_thinking': False}})
        (self.directory / (name + '.response.json')).write_text(result.model_dump_json(indent=2))
        if result.choices[0].finish_reason == 'length':
            raise RuntimeError('Local model output truncated; increase max_tokens')
        usage = result.usage.model_dump() if result.usage else {}
        return result, usage


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--topic', default='Linear transformations and matrices')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--ports', type=int, nargs='+')
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=args.resume)
    os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '')
    os.environ['LOCAL_BASE_URL'] = f'http://127.0.0.1:{args.port}/v1'
    os.environ['LOCAL_MODEL'] = 'qwen3.8-27b'
    from agent import TeachingVideoAgent, RunConfig
    import agent as module
    from generation.local_critic import request as critic
    module.request_gemini_video_img = critic
    calls = args.out / 'calls'
    calls.mkdir(exist_ok=args.resume)
    # Keep the released algorithm and prompts. Optional external icon retrieval
    # is disabled because no Iconfinder credential is configured.
    cfg = RunConfig(api=LoggedAPI(calls.resolve(), args.ports or [args.port]), use_feedback=True, use_assets=False,
                    max_fix_bug_tries=3, max_regenerate_tries=3,
                    max_feedback_gen_code_tries=2, max_mllm_fix_bugs_tries=2,
                    feedback_rounds=2)
    folder = SOURCE / 'src/CASES' / args.out.name
    backup = None
    if args.resume and folder.exists():
        backup = args.out / ('resume_snapshot_' + uuid.uuid4().hex)
        shutil.copytree(folder, backup)
    report = {'method': 'Code2Video author Planner/Coder/Critic with local model substitution',
              'topic': args.topic, 'source_commit': subprocess.check_output(
                  ['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip(),
              'source_diff_sha256': hashlib.sha256(subprocess.check_output(
                  ['git', '-C', str(SOURCE), 'diff'])).hexdigest(),
              'substitutions': ['Qwen3.8-27B for author API models', '8 ordered frames for native video Critic input'],
              'project_lesson_contract': False, 'project_narration_or_scoring': False,
              'optional_assets': False, 'retry_limits': {'fix': 3, 'regenerate': 3, 'critic': 2},
              'scope': 'one author-listed topic; not original API-model or full MMMC benchmark replication'}
    (args.out / 'source.patch').write_bytes(subprocess.check_output(['git', '-C', str(SOURCE), 'diff']))
    start = time.monotonic()
    previous = args.out / 'report.json'
    if previous.exists():
        previous.rename(args.out / ('report.previous.' + uuid.uuid4().hex + '.json'))
    try:
        instance = TeachingVideoAgent(0, args.topic, folder=folder, cfg=cfg)
        report['output_dir'] = str(instance.output_dir)
        if args.resume:
            instance.generate_outline()
            instance.generate_storyboard()
            reused = []
            for section in instance.sections:
                optimized = instance.output_dir / 'optimized_videos' / f'{section.id}_optimized.mp4'
                if optimized.is_file():
                    instance.section_videos[section.id] = str(optimized)
                    reused.append(section.id)
                    continue
                code = instance.output_dir / f'{section.id}.py'
                if code.is_file():
                    instance.section_codes[section.id] = code.read_text()
                else:
                    instance.generate_section_code(section)
                instance.render_section(section)
            report['reused_sections'] = reused
            report['resume_snapshot'] = str(backup) if backup else None
            video = instance.merge_videos() if len(instance.section_videos) == len(instance.sections) else None
        else:
            video = instance.GENERATE_VIDEO()
        report.update(video=video, sections=len(instance.sections), rendered_sections=len(instance.section_videos),
                      token_usage=instance.token_usage,
                      complete=bool(video and Path(video).is_file() and instance.sections and
                                    len(instance.sections) == len(instance.section_videos)))
    except Exception as exc:
        report.update(complete=False, error=repr(exc))
    report['seconds'] = time.monotonic() - start
    (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
