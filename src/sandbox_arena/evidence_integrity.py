"""Portable checksums detect changes; they do not authenticate the report author."""

import hashlib
import hmac
import json


def digest(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def seal(record: dict) -> dict:
    payload = {key: value for key, value in record.items() if key != 'integrity'}
    return {
        **payload,
        'integrity': {'algorithm': 'sha256', 'canonicalization': 'arena-json-v1', 'digest': digest(payload)},
    }


def checksum_valid(record: dict) -> bool:
    integrity = record.get('integrity', {})
    if not isinstance(integrity, dict) or integrity.get('algorithm') != 'sha256':
        return False
    if integrity.get('canonicalization') != 'arena-json-v1' or not isinstance(integrity.get('digest'), str):
        return False
    try:
        expected = digest({key: value for key, value in record.items() if key != 'integrity'})
        return hmac.compare_digest(expected, integrity['digest'])
    except ValueError, TypeError, RecursionError:
        return False
