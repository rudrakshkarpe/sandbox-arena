"""Replay only installed, unchanged scenarios from checksum-consistent reports."""

from .evidence_integrity import checksum_valid
from .playground_models import RunSpec
from .scenario_catalog import PACKS, pack_digest


def replay_spec(record: dict) -> RunSpec:
    if record.get('status') not in {'completed', 'cancelled', 'interrupted', 'failed'}:
        raise ValueError('Only terminal runs can be replayed')
    if not checksum_valid(record):
        raise ValueError('The source report checksum is missing or invalid')
    spec = RunSpec.model_validate(record.get('spec'))
    if spec.mode != 'scenario':
        raise ValueError('Replay currently supports scenario runs only')
    pack = PACKS[spec.scenario_id]
    if record.get('scenario') != pack.model_dump(mode='json') or record.get('scenario_sha256') != pack_digest(pack):
        raise ValueError('The recorded scenario does not match the installed version')
    return spec


def lineage(record: dict) -> dict:
    return {'run_id': record['id'], 'report_sha256': record['integrity']['digest']}
