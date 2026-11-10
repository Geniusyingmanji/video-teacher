"""Released TikZilla-8B-RL inference with model-card prompt and sampling."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='/root/models/TikZilla-8B-RL')
    parser.add_argument('--prompts', type=Path, default=Path(__file__).resolve().parents[1] / 'research/code2image_prompts.jsonl')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig, set_seed
    from detikzify.infer import TikzDocument
    report = {'method': 'author TikZilla-8B-RL checkpoint with model-card inference',
              'scope': 'six matched educational prompts; not full paper benchmark replication',
              'model': args.model, 'seed': args.seed,
              'prompt_sha256': hashlib.sha256(args.prompts.read_bytes()).hexdigest(),
              'environment': {k: importlib.metadata.version(k) for k in ['torch', 'transformers', 'accelerate']},
              'model_card_environment': {'torch': '2.5.1', 'transformers': '4.53.2', 'accelerate': '1.8.1'},
              'sampling': {'temperature': 1., 'top_p': .9, 'max_new_tokens': 2048}, 'cases': []}
    def save():
        (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    start = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map='auto')
    report['load_seconds'] = time.monotonic() - start
    eos = tokenizer.convert_tokens_to_ids('<|im_end|>')
    config = GenerationConfig(do_sample=True, temperature=1., top_p=.9, max_new_tokens=2048,
                              eos_token_id=eos, pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id or eos)
    for index, line in enumerate(args.prompts.read_text().splitlines()):
        case = json.loads(line)
        directory = args.out / case['id']
        directory.mkdir()
        prompt = ('Generate a complete LaTeX document that contains a TikZ figure according to the following requirements:\n'
                  + case['text'] + '\nWrap your code using \\documentclass[tikz]{standalone}, and include '
                  '\\begin{document}...\\end{document}. Only output valid LaTeX code with no extra text.')
        text = tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
                                             tokenize=False, add_generation_prompt=True)
        (directory / 'prompt.json').write_text(json.dumps({'case': case, 'actual_prompt': prompt, 'formatted_input': text}, indent=2))
        row = {'id': case['id'], 'seed': args.seed + index, 'content_review': 'pending'}
        start = time.monotonic()
        set_seed(args.seed + index)
        try:
            inputs = tokenizer([text], return_tensors='pt').to(model.device)
            with torch.inference_mode():
                output = model.generate(**inputs, generation_config=config)
            ids = output[0][len(inputs['input_ids'][0]):]
            response = tokenizer.decode(ids, skip_special_tokens=True)
            (directory / 'response.txt').write_text(response)
            row.update(generated_tokens=len(ids), ended_with_eos=int(ids[-1]) == eos,
                       truncated=len(ids) >= 2048 and int(ids[-1]) != eos)
            code = response.strip()
            if code.startswith('```'):
                code = code.split('\n', 1)[1].rsplit('```', 1)[0]
            document = TikzDocument(code)
            document.save(str(directory / 'figure.tex'))
            (directory / 'compile.log').write_text(document.log)
            row.update(compile_status=document.status, rasterizable=document.is_rasterizable,
                       has_content=document.has_content)
            if document.is_rasterizable:
                document.save(str(directory / 'figure.pdf'))
                document.save(str(directory / 'figure.png'), size=1200)
        except Exception as exc:
            row['error'] = repr(exc)
        row['seconds'] = time.monotonic() - start
        report['cases'].append(row)
        save()
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
