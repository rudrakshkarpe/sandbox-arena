"""End-to-end VM-tier runs on a local Docker daemon. Skipped when Docker or the image is unavailable."""

import os

import pytest

from sandbox_arena.adapters.base import Command, SandboxSpec
from sandbox_arena.adapters.docker import DockerAdapter, docker, docker_available
from sandbox_arena.observers import LocalDockerObservers
from sandbox_arena.vm_runner import VM_PACKS, run_vm_pack, verify_vm_report

IMAGE = os.environ.get('ARENA_DOCKER_IMAGE', 'python:3.12-slim')


def image_present() -> bool:
    return docker_available() and docker('image', 'inspect', IMAGE, timeout=30).returncode == 0


pytestmark = pytest.mark.skipif(not image_present(), reason=f'Docker daemon or image {IMAGE} unavailable')


@pytest.fixture(scope='module')
def lab():
    observers = LocalDockerObservers(image=IMAGE)
    observers.start()
    adapter = DockerAdapter(image=IMAGE, network_plan=observers.network_plan)
    yield adapter, observers
    assert observers.stop().confirmed


def test_adapter_conformance_create_exec_files_destroy(lab):
    adapter, _ = lab
    handle = adapter.create(SandboxSpec(hardened=True))
    try:
        result = adapter.exec(handle, Command(argv=('python3', '-c', 'print(6 * 7)')))
        assert result.exit_code == 0 and result.stdout.strip() == '42'
        adapter.put_file(handle, '/tmp/probe.txt', b'evidence')
        assert adapter.get_file(handle, '/tmp/probe.txt') == b'evidence'
        who = adapter.exec(handle, Command(argv=('python3', '-c', 'import os; print(os.getuid())')))
        assert who.stdout.strip() == '1000'
    finally:
        assert adapter.destroy(handle).confirmed


@pytest.mark.parametrize(('profile', 'outcome'), [('strict', 'expected_observed'), ('default', 'unexpected_observed')])
def test_egress_deny_gap_between_profiles(lab, profile, outcome):
    adapter, observers = lab
    record = run_vm_pack(VM_PACKS['egress-deny'], adapter, observers, profile)
    assert record['assessment']['outcome'] == outcome
    assert verify_vm_report(record)['evidence_consistent']


def test_mounted_runtime_socket_is_reported():
    """Mutation check: the secret pack must catch a sandbox that can reach the container runtime."""
    if not os.path.exists('/var/run/docker.sock'):
        pytest.skip('No local runtime socket to mount')
    observers = LocalDockerObservers(image=IMAGE)
    observers.start()
    try:

        class SocketMountingAdapter(DockerAdapter):
            def configuration(self, spec):
                return [*super().configuration(spec), '-v', '/var/run/docker.sock:/var/run/docker.sock']

        adapter = SocketMountingAdapter(image=IMAGE, network_plan=observers.network_plan)
        record = run_vm_pack(VM_PACKS['secret-exposure'], adapter, observers, 'default')
        assert record['assessment']['outcome'] == 'unexpected_observed'
    finally:
        assert observers.stop().confirmed
