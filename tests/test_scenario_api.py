from fastapi.testclient import TestClient
from test_playground_api import wait_done

from sandbox_arena.web import create_app


def test_catalog_discovery_and_scenario_execution(tmp_path):
    with TestClient(create_app(database=tmp_path / 'runs.db')) as client:
        catalog = client.get('/api/playground/catalog').json()
        assert len(catalog['scenarios']) == 18
        detail = client.get('/api/playground/scenarios/caught-denial').json()
        assert detail['sha256'] and detail['limitation']
        assert client.get('/api/playground/scenarios/unknown').status_code == 404
        response = client.post(
            '/api/playground/runs', json={'mode': 'scenario', 'scenario_id': 'caught-denial', 'iterations': 1}
        )
        assert response.status_code == 202
        record = wait_done(client, response.json()['id'])
        assert record['assessment']['outcome'] == 'expected_observed'
        assert record['integrity']['digest']


def test_verification_and_replay_api_preserve_lineage(tmp_path):
    with TestClient(create_app(database=tmp_path / 'runs.db')) as client:
        source_id = client.post(
            '/api/playground/runs', json={'mode': 'scenario', 'scenario_id': 'fixture-permission', 'iterations': 1}
        ).json()['id']
        source = wait_done(client, source_id)
        assert client.get(f'/api/playground/runs/{source_id}/verify').json()['verified']
        response = client.post(f'/api/playground/runs/{source_id}/replay', json={})
        assert response.status_code == 202
        replay = wait_done(client, response.json()['id'])
        assert replay['replay_of']['run_id'] == source_id
        assert replay['spec'] == source['spec']
        assert client.post('/api/playground/runs/missing/replay', json={}).status_code == 404
        assert (
            client.post(
                f'/api/playground/runs/{source_id}/replay', json={}, headers={'Origin': 'https://evil.example'}
            ).status_code
            == 403
        )
        custom = client.post('/api/playground/runs', json={'code': '42'}).json()['id']
        wait_done(client, custom)
        assert client.post(f'/api/playground/runs/{custom}/replay', json={}).status_code == 409
