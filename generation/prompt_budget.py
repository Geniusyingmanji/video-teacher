"""Local token budgeting with conservative multimodal reserves and bounded diagnostics."""
from functools import lru_cache
from pathlib import Path
import os


@lru_cache(maxsize=2)
def tokenizer(path):
    from tokenizers import Tokenizer
    return Tokenizer.from_file(path)


def request_budget(text, output_tokens, image_count=0):
    path = os.environ.get('LOCAL_TOKENIZER_PATH', '/root/models/Qwen3.8-27B/tokenizer.json')
    if not Path(path).is_file():
        raise ValueError('Local tokenizer required for exact request budgeting: ' + path)
    count = len(tokenizer(path).encode(text).ids)
    # Server image processor caps longest_edge at 262144 pixels; 2048 per image
    # deliberately over-reserves visual tokens plus message/template overhead.
    reserved = 1024 + 2048 * image_count
    limit = int(os.environ.get('LOCAL_CONTEXT_LENGTH', '32768'))
    available = limit - count - reserved
    if available < min(output_tokens, 1024):
        raise ValueError(f'Prompt budget exceeded before API call: text={count}, reserved={reserved}, limit={limit}; compact supplemental context')
    return min(output_tokens, available), {'text_tokens': count, 'image_count': image_count,
        'reserved_tokens': reserved, 'max_context_tokens': limit, 'output_tokens': min(output_tokens, available)}
