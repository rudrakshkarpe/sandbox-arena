from fastapi.testclient import TestClient

from sandbox_arena.web import create_app
from test_playground_api import wait_done


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
