import json
import pytest

from localbench.common import ROOT
from localbench.prepare import normalize
from localbench.run import select_cases


def test_full_selection_includes_every_discipline():
    path = ROOT / 'data/tasks.jsonl'
    all_cases = select_cases(path, suite='all')
    core_cases = select_cases(path, suite='core')
    assert len(all_cases) == 400
    assert {row['id'] for row in all_cases} == {row['id'] for row in core_cases}
    assert len({row['discipline_canonical'] for row in all_cases}) == 13
    assert sum(row['discipline_canonical'] == 'sports' for row in core_cases) == 25
    assert {row['benchmark_scope'] for row in all_cases} == {'candidate'}


def test_regeneration_keeps_sports_in_same_scope():
    path = ROOT / 'data/source_tasks.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    sports = next(row for row in rows if row['discipline'] == 'sports')
    mathematics = next(row for row in rows if row['discipline'] == 'mathematics')
    assert normalize(sports)['benchmark_scope'] == normalize(mathematics)['benchmark_scope'] == 'candidate'


def test_num_defaults_to_full_bank_and_batches_are_stable_and_disjoint():
    path = ROOT / 'data/tasks.jsonl'
    all_cases = select_cases(path, suite='all')
    assert len(select_cases(path)) == 3
    assert select_cases(path, num=10) == all_cases[:10]
    assert select_cases(path, num=10, offset=10) == all_cases[10:20]
    assert select_cases(path, num=400) == all_cases
    assert select_cases(path, num=10) == select_cases(path, num=10)


def test_num_respects_explicit_ids_and_smoke_scope():
    path = ROOT / 'data/tasks.jsonl'
    ids = ['chem_exp_01', 'math_exp_02', 'cs_exp_01']
    assert [r['id'] for r in select_cases(path, ids=ids, num=1, offset=1)] == ['math_exp_02']
    assert len(select_cases(path, suite='smoke', num=2)) == 2
    with pytest.raises(ValueError, match='only 3 cases'):
        select_cases(path, suite='smoke', num=4)


@pytest.mark.parametrize('options', [
    {'num': 0}, {'num': -1}, {'num': True}, {'num': 401},
    {'num': 2, 'offset': -1}, {'num': 2, 'offset': 399}, {'offset': 3},
])
def test_invalid_batches_fail_instead_of_silently_running_a_different_count(options):
    with pytest.raises(ValueError):
        select_cases(ROOT / 'data/tasks.jsonl', **options)
