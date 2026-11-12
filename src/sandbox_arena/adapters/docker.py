"""Local Docker adapter: the first container-tier runtime.

Docker is free, runs on a laptop and lets us exercise the whole container/VM tier
(egress, DNS, secrets, cleanup) against infrastructure we own, before spending
credits on E2B or Modal or touching anyone else's platform.

It talks to the Docker CLI rather than adding an SDK dependency. Containers share
the host kernel, so results describe Docker's network and privilege controls, not
VM-grade isolation. Reports record that through ``isolation_class``.
"""

import os
import shutil
import subprocess
import time
from collections.abc import Callable
from uuid import uuid4

from .base import CleanupReport, Command, EgressPolicy, ExecResult, Handle, SandboxSpec, bounded

DEFAULT_IMAGE = 'python:3.12-slim'
LABEL = 'sandbox-arena.role'

# Returns (networks to attach, DNS servers) for an egress policy. Supplied by the
# observer harness so the adapter never hard-codes arena network names.
NetworkPlan = Callable[[EgressPolicy], tuple[list[str], list[str]]]


class DockerError(RuntimeError):
    pass


def docker(*args: str, timeout: float = 60, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    binary = shutil.which('docker')
    if binary is None:
        raise DockerError('Docker CLI not found on PATH')
    return subprocess.run(
        [binary, *args],
        input=stdin,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def docker_available() -> bool:
    try:
        return docker('version', '--format', '{{.Server.Version}}', timeout=10).returncode == 0
    except (DockerError, subprocess.TimeoutExpired, OSError):
        return False


def _text(raw: bytes) -> str:
    return raw.decode('utf-8', errors='replace')


class DockerAdapter:
    name = 'docker'
    isolation_class = 'container (shared host kernel)'
    capabilities = frozenset({'exec.shell', 'fs.read_write', 'net.egress_policy', 'multi.sandbox', 'limits.cpu_mem'})

    def __init__(self, image: str | None = None, network_plan: NetworkPlan | None = None):
        self.image = image or os.environ.get('ARENA_DOCKER_IMAGE', DEFAULT_IMAGE)
        self.network_plan = network_plan

    def version(self) -> str:
        server = docker('version', '--format', '{{.Server.Version}}', timeout=10)
        runtime = docker('info', '--format', '{{.DefaultRuntime}}', timeout=10)
        return f'docker {_text(server.stdout).strip()} runtime {_text(runtime.stdout).strip()} image {self.image}'

    def configuration(self, spec: SandboxSpec) -> list[str]:
        """Translate a spec into docker run flags. Exposed so reports can record the exact posture."""
        flags = [
            '--memory',
            f'{spec.memory_mb}m',
            '--cpus',
            str(spec.cpus),
            '--pids-limit',
            str(spec.pids_limit),
        ]
        if spec.hardened:
            # Strictest commonly documented posture for untrusted code in a plain container.
            flags += [
                '--cap-drop',
                'ALL',
                '--security-opt',
                'no-new-privileges',
                '--read-only',
                '--tmpfs',
                '/tmp:rw,size=64m',
                '--tmpfs',
                '/workspace:rw,size=64m,uid=1000,gid=1000',
                '--user',
                '1000:1000',
            ]
        return flags

    def create(self, spec: SandboxSpec) -> Handle:
        name = f'arena-sbx-{uuid4().hex[:12]}'
        networks, dns = self._networks(spec.egress)
        args = ['run', '-d', '--name', name, '--label', f'{LABEL}=sandbox', *self.configuration(spec)]
        args += ['--network', networks[0]] if networks else ['--network', 'none']
        for server in dns:
            args += ['--dns', server]
        for key, value in spec.env.items():
            args += ['--env', f'{key}={value}']
        args += [spec.image or self.image, 'python3', '-c', 'import time; time.sleep(3600)']
        started = docker(*args, timeout=spec.timeout_s)
        if started.returncode != 0:
            raise DockerError(f'docker run failed: {_text(started.stderr).strip()[:500]}')
        for extra in networks[1:]:
            connected = docker('network', 'connect', extra, name, timeout=30)
            if connected.returncode != 0:
                self.destroy(Handle(adapter=self.name, id=name))
                raise DockerError(f'network connect failed: {_text(connected.stderr).strip()[:500]}')
        return Handle(adapter=self.name, id=name, detail={'networks': ','.join(networks) or 'none'})

    def exec(self, handle: Handle, command: Command) -> ExecResult:
        started = time.perf_counter()
        try:
            done = docker('exec', handle.id, *command.argv, timeout=command.timeout_s)
        except subprocess.TimeoutExpired as exc:
            return ExecResult(
                exit_code=None,
                stdout=bounded(_text(exc.stdout or b'')),
                stderr=bounded(_text(exc.stderr or b'')),
                timed_out=True,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        return ExecResult(
            exit_code=done.returncode,
            stdout=bounded(_text(done.stdout)),
            stderr=bounded(_text(done.stderr)),
            duration_ms=(time.perf_counter() - started) * 1000,
        )

    def put_file(self, handle: Handle, path: str, data: bytes) -> None:
        # docker cp cannot write into tmpfs mounts on a read-only rootfs (the hardened profile),
        # so stream bytes through exec. Requires python3 in the image, like every probe.
        if not path.startswith('/'):
            raise ValueError('put_file needs an absolute file path')
        writer = 'import sys; open(sys.argv[1], "wb").write(sys.stdin.buffer.read())'
        done = docker('exec', '-i', handle.id, 'python3', '-c', writer, path, stdin=data, timeout=60)
        if done.returncode != 0:
            raise DockerError(f'put_file failed: {_text(done.stderr).strip()[:500]}')

    def get_file(self, handle: Handle, path: str) -> bytes:
        reader = 'import sys; sys.stdout.buffer.write(open(sys.argv[1], "rb").read())'
        done = docker('exec', handle.id, 'python3', '-c', reader, path, timeout=60)
        if done.returncode != 0:
            raise DockerError(f'get_file failed: {_text(done.stderr).strip()[:500]}')
        return done.stdout

    def destroy(self, handle: Handle) -> CleanupReport:
        docker('rm', '-f', handle.id, timeout=60)
        # Confirm with a fresh lookup instead of trusting the rm exit code.
        gone = docker('container', 'inspect', handle.id, timeout=30).returncode != 0
        return CleanupReport(
            confirmed=gone,
            removed=[f'container {handle.id}'] if gone else [],
            leftovers=[] if gone else [f'container {handle.id}'],
        )

    def _networks(self, egress: EgressPolicy) -> tuple[list[str], list[str]]:
        if egress.mode == 'deny_all':
            return [], []
        if self.network_plan is None:
            if egress.mode == 'allowlist':
                raise DockerError('An allowlist needs an observer network plan')
            return ['bridge'], []
        return self.network_plan(egress)
