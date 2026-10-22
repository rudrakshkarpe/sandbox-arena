import pytest

from sandbox_arena.playground_models import RunSpec
from sandbox_arena.playground_runner import MontyProvider
from sandbox_arena.scenario_catalog import PACKS, catalog_entries, load_catalog, pack_digest
from sandbox_arena.scenario_verifier import checks_pass, verify_probe


def test_catalog_is_stable_and_content_addressed():
    assert load_catalog() == PACKS
    for entry in catalog_entries():
        assert entry['sha256'] == pack_digest(PACKS[entry['id']])


@pytest.mark.parametrize('pack', PACKS.values(), ids=PACKS.keys())
def test_bundled_scenario_observations(pool, pack):
    spec = RunSpec(code='0', allow_fixture=pack.allow_fixture, timeout_ms=pack.timeout_ms, memory_mb=pack.memory_mb)
    provider = MontyProvider(pool)
    for probe in pack.probes:
        sample = provider.execute(spec, probe.code, probe.id, 1, False).model_dump()
        checks = verify_probe(probe, sample)
        assert checks_pass(checks), (pack.id, probe.id, checks, sample)
