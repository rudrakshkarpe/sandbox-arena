import pytest

from sandbox_arena.sandbox import make_pool
from sandbox_arena.telemetry import configure


@pytest.fixture(scope='session', autouse=True)
def telemetry(tmp_path_factory):
    path = tmp_path_factory.mktemp('telemetry') / 'traces.jsonl'
    configure(path)
    return path


@pytest.fixture(scope='session')
def pool():
    with make_pool() as value:
        yield value
