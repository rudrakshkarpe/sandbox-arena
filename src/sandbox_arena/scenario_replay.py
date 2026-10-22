"""Replay only installed, unchanged scenarios from checksum-consistent reports."""

import re

from .evidence_integrity import checksum_valid
from .playground_models import RunSpec
from .scenario_catalog import PACKS, pack_digest


def replay_spec(record: dict) -> RunSpec:
    if record.get('schema_version') != '1.0':
        raise ValueError('Unsupported report schema')
    if not isinstance(record.get('id'), str) or not re.fullmatch(r'[0-9a-f]{32}', record['id']):
        raise ValueError('Invalid source run identity')
    if not isinstance(record.get('status'), str) or record.get('status') not in {
        'completed',
        'cancelled',
        'interrupted',
        'failed',
    }:
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
