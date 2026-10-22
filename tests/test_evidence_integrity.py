import pytest

from sandbox_arena.evidence_integrity import checksum_valid, digest, seal


def test_checksum_detects_payload_changes_and_has_stable_key_order():
    assert digest({'a': 1, 'b': 2}) == digest({'b': 2, 'a': 1})
    report = seal({'samples': [{'result': 42}]})
    assert checksum_valid(report)
    assert seal(report) == report
    report['samples'][0]['result'] = 0
    assert not checksum_valid(report)
    assert not checksum_valid({'integrity': None})


def test_nonfinite_values_cannot_be_sealed():
    with pytest.raises(ValueError):
        digest({'result': float('nan')})
