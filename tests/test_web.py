import pytest
from fastapi.testclient import TestClient

from monty_incident_lab.web import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def test_ui_and_api(client):
    assert client.get('/').status_code == 200
    assert client.get('/static/app.js').status_code == 200
    response = client.post('/api/run', json={'scenario': 'long-context'})
    assert response.status_code == 200
    assert response.json()['attempts'][0]['analysis']['finding'] == 'prefill_pressure'
    trace_id = response.json()['attempts'][0]['trace_id']
    trace = client.get(f'/api/traces/{trace_id}').json()
    assert any(span['name'] == 'session {script_name}' for span in trace['spans'])
    assert all('attributes' not in span and 'resource' not in span for span in trace['spans'])
    assert client.get('/api/traces/invalid').status_code == 422
    assert client.get('/api/traces/' + '0' * 32).status_code == 404


def test_request_boundaries(client):
    assert client.post('/api/run', json={'scenario': 'not-a-scenario'}).status_code == 422
    assert client.post('/api/run', json={'scope': 'another-customer'}).status_code == 422
    assert client.post('/api/run', json={'code': 'x' * 12_001}).status_code == 422
    assert (
        client.post('/api/run', content=b'x' * 64_001, headers={'Content-Type': 'application/json'}).status_code == 413
    )
    assert client.post('/api/run', json={}, headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert client.get('/', headers={'Host': 'untrusted.example'}).status_code == 400
    assert client.post('/api/run', content='{}').status_code == 415
