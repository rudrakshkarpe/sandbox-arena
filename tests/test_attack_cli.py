import json
from argparse import Namespace

import pytest

from sandbox_arena.attack_cli import dispatch, read_report


def test_attack_verify_and_replay_cli(tmp_path, capsys):
    path = tmp_path / 'report.json'
    assert dispatch(Namespace(command='attack', scenario_id='caught-denial', iterations=1, output=path)) == 0
    source = read_report(path)
    assert dispatch(Namespace(command='verify', report=path)) == 0
    replay = tmp_path / 'replay.json'
    assert dispatch(Namespace(command='replay', report=path, output=replay)) == 0
    assert read_report(replay)['replay_of']['run_id'] == source['id']
    source['samples'][0]['result'] = 99
    path.write_text(json.dumps(source))
    assert dispatch(Namespace(command='verify', report=path)) == 1
    capsys.readouterr()


@pytest.mark.parametrize('content', ['[]', '{"a":1,"a":2}', '{"a":NaN}'])
def test_ambiguous_report_files_are_rejected(tmp_path, content):
    path = tmp_path / 'invalid.json'
    path.write_text(content)
    with pytest.raises(ValueError):
        read_report(path)
