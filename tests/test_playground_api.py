import json
import time

import pytest
from fastapi.testclient import TestClient

from monty_incident_lab.web import create_app


def wait_done(client, run_id):
    for _ in range(200):
        record = client.get(f'/api/playground/runs/{run_id}').json()
        if record['status'] in {'completed', 'cancelled', 'failed'}:
            return record
        time.sleep(0.02)
    pytest.fail('Run did not finish')


def test_api_persistence_events_and_validation(tmp_path):
    database = tmp_path / 'runs.db'
    with TestClient(create_app(database=database)) as client:
        assert client.get('/').status_code == 200
        assert client.get('/incident-lab').status_code == 200
        assert 'Submit Python' in client.get('/docs').text
        catalog = client.get('/api/playground/catalog').json()
        assert len(catalog['benchmarks']) == 5
        spec = {'mode': 'benchmark', 'benchmark_ids': ['primes-10', 'primes-1000'], 'iterations': 3, 'warmups': 1}
        response = client.post('/api/playground/runs', json=spec)
        assert response.status_code == 202
        run_id = response.json()['id']
        record = wait_done(client, run_id)
        assert record['status'] == 'completed'
        assert len(record['samples']) == 8
        assert all(s['passed'] == 3 and s['p95_ms'] is None for s in record['summaries'])
        exported = client.get(f'/api/playground/runs/{run_id}/export')
        assert exported.json() == record
        listed = client.get('/api/playground/runs?limit=1').json()
        assert listed[0]['id'] == run_id and 'samples' not in listed[0]
        assert client.get('/api/playground/runs?offset=1').json() == []
        assert client.get('/api/playground/runs?limit=101').status_code == 422
        assert 'attachment' in exported.headers['content-disposition']
        events = client.get(f'/api/playground/runs/{run_id}/events', headers={'Last-Event-ID': '2'})
        parsed = [json.loads(line[6:]) for line in events.text.splitlines() if line.startswith('data: ')]
        assert parsed[0]['id'] == 3 and parsed[-1]['type'] == 'completed'
        assert client.post('/api/playground/runs', json={'code': '1', 'iterations': 51}).status_code == 422
        assert (
            client.post('/api/playground/runs', json={'mode': 'benchmark', 'benchmark_ids': ['missing']}).status_code
            == 422
        )
        assert (
            client.post(
                '/api/playground/runs', json={'code': '1'}, headers={'Origin': 'https://evil.example'}
            ).status_code
            == 403
        )
        assert client.get('/api/playground/runs/missing').status_code == 404
    with TestClient(create_app(database=database)) as client:
        assert client.get(f'/api/playground/runs/{run_id}').json()['status'] == 'completed'
