"""Process-local stop-token guard for a diagnosed structured-decoding failure."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
from types import SimpleNamespace

from eval.judges import gpt55


def guard_config(token_ids):
    if not token_ids:
        return None
    if any(type(i) is not int or i < 0 for i in token_ids):
        raise ValueError('structured stop-token IDs must be nonnegative integers')
    ids = sorted(set(token_ids))
    return {'version': 'structured-stop-token-guard-v1', 'stop_token_ids': ids,
            'logit_bias': {str(i): -100 for i in ids},
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope': 'new json_schema requests; cached validated facts retain original provenance'}


@contextmanager
def structured_stop_token_guard(token_ids):
    """Workers are isolated processes; restore the client factory after each case."""
    config = guard_config(token_ids)
    if config is None:
        yield
        return
    original = gpt55.configured_client

    def factory():
        client = original()
        def create(**kwargs):
            if (kwargs.get('response_format') or {}).get('type') == 'json_schema':
                kwargs = {**kwargs, 'logit_bias': {
                    **(kwargs.get('logit_bias') or {}), **config['logit_bias']}}
            return client.chat.completions.create(**kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    gpt55.configured_client = factory
    try:
        yield
    finally:
        gpt55.configured_client = original
