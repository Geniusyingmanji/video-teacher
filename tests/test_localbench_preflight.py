import pytest

from localbench.preflight import command_plan,inspect_cases,scoring_protocol


def case(id_='a'):
    return {'id':id_,'prompt_text':'Explain a concept.','task_type':'explanation',
            'target_duration_s':60,'pedagogical_target_audience':'high school',
            'audio_narration_required':True,'expected_concepts':['private reference']}


def test_preflight_checks_full_lesson_without_calling_a_model():
    r=inspect_cases([case()],['a'])[0]
    assert not r['errors'] and r['review_notes']
    row=case();row['target_duration_s']=3;row['audio_narration_required']=False
    assert len(inspect_cases([row],['a'])[0]['errors'])==2
    with pytest.raises(ValueError):inspect_cases([case()],['missing'])
    with pytest.raises(ValueError):inspect_cases([case()],['a','a'])


def test_handoff_commands_keep_dataset_ids_and_budgets_separate_arguments(tmp_path):
    config={'model':'qwen3.8-flash','render_workers':2,'api_workers':4,'generation_max_calls':16}
    commands=command_plan(config,tmp_path/'dataset with space.jsonl',['a'],tmp_path/'batch')
    assert str(tmp_path/'dataset with space.jsonl') in commands['generation']
    assert commands['generation'][commands['generation'].index('--max-calls')+1]=='16'
    assert 'qwen3.8-flash' in commands['evaluation']


def test_reference_contract_handoff_selects_explicit_experiment(tmp_path):
    directory=tmp_path/'contracts with spaces'
    c=command_plan({'reference_contracts':str(directory)},tmp_path/'data.jsonl',['a'],tmp_path/'out')
    assert c['evaluation'][c['evaluation'].index('--reference-contracts')+1]==str(directory)
    assert '--reference-contracts' not in c['generation']


def test_semantic_handoff_keeps_protocol_and_commands_consistent(tmp_path):
    config={'reference_contracts':str(tmp_path/'contracts'),
            'semantic_outcomes':True,'scoring_protocol':'localbench-ten-dimensions-dev14-integer-r4+reference-contract-v1+semantic-outcomes-v1'}
    commands=command_plan(config,tmp_path/'data.jsonl',['a'],tmp_path/'out')
    assert '--semantic-outcomes' in commands['evaluation']
    assert '--semantic-outcomes' not in commands['generation']
    with pytest.raises(ValueError,match='differs'):
        command_plan({**config,'scoring_protocol':'localbench-ten-dimensions-dev14-integer-r4+reference-contract-v1'},
                     tmp_path/'data.jsonl',['a'],tmp_path/'out')


def test_semantic_protocol_needs_contract_and_boolean_flag():
    with pytest.raises(ValueError,match='requires'):
        scoring_protocol({'semantic_outcomes':True})
    with pytest.raises(ValueError,match='boolean'):
        scoring_protocol({'semantic_outcomes':'false'})
    assert scoring_protocol({})=='localbench-ten-dimensions-dev14-integer-r4'
