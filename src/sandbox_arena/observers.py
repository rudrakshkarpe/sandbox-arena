"""Host-side observers: infrastructure we own that sits outside every sandbox.

Verdicts for network probes come from here, never from sandbox output. A probe
that claims "blocked" proves nothing; zero hits on our canary log does.

``LocalDockerObservers`` builds a throwaway lab per run:

- ``arena-open-*``: a normal bridge network holding the allowed fixture and the
  canary. Sandboxes in the default (open) profile join it.
- ``arena-allow-*``: an ``--internal`` network holding only the allowed fixture.
  Sandboxes in the strict (allowlist) profile join only this one.
- ``allowed.arena.test``: an HTTP fixture that stands in for an allowlisted host.
  ``/redirect?to=URL`` answers with a 302 so probes can test redirect escapes.
- ``canary.arena.test``: logs every HTTP request and every DNS query it receives.
  Sandboxes use it as their upstream DNS server, so a resolver that forwards
  queries for unknown names leaks them here.

A cloud deployment would replace this with a canary domain and logger on a VPS we
control. Never point probes at a third-party endpoint.
"""

import json
import secrets
import subprocess
from dataclasses import dataclass, field
from uuid import uuid4

from .adapters.base import CleanupReport, EgressPolicy
from .adapters.docker import LABEL, DockerError, _text, docker

ALLOWED_HOST = 'allowed.arena.test'
CANARY_HOST = 'canary.arena.test'
EXFIL_ZONE = 'exfil.arena.test'
PORT = 8080

ALLOWED_SERVER = r"""
import http.server, urllib.parse
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == '/redirect':
            target = urllib.parse.parse_qs(url.query).get('to', [''])[0]
            self.send_response(302); self.send_header('Location', target); self.end_headers(); return
        body = b'allowed-ok'
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(('0.0.0.0', 8080), H).serve_forever()
"""

CANARY_SERVER = r"""
import http.server, json, socket, struct, threading, time
LOG = '/tmp/canary.jsonl'
lock = threading.Lock()
def record(kind, value, peer):
    with lock, open(LOG, 'a') as f:
        f.write(json.dumps({'kind': kind, 'value': value[:300], 'peer': peer, 'at': time.time()}) + '\n')
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        record('http', self.headers.get('Host', '') + self.path, self.client_address[0])
        self.send_response(200); self.send_header('Content-Length', '6'); self.end_headers(); self.wfile.write(b'canary')
    def log_message(self, *a): pass
def qname(data):
    labels, i = [], 12
    while i < len(data) and data[i]:
        n = data[i]; labels.append(data[i + 1:i + 1 + n].decode('ascii', 'replace')); i += n + 1
    return '.'.join(labels).lower(), i + 5
def dns():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('0.0.0.0', 53))
    while True:
        data, peer = s.recvfrom(512)
        try:
            name, end = qname(data)
        except Exception:
            continue
        record('dns', name, peer[0])
        flags = struct.pack('>H', 0x8183)  # response, recursion available, NXDOMAIN
        s.sendto(data[:2] + flags + data[4:6] + b'\x00\x00\x00\x00\x00\x00' + data[12:end], peer)
open(LOG, 'a').close()
threading.Thread(target=dns, daemon=True).start()
http.server.ThreadingHTTPServer(('0.0.0.0', 8080), H).serve_forever()
"""


@dataclass
class LocalDockerObservers:
    image: str
    suffix: str = field(default_factory=lambda: uuid4().hex[:8])
    canary_ip: str = ''
    started: bool = False

    @property
    def open_network(self) -> str:
        return f'arena-open-{self.suffix}'

    @property
    def allow_network(self) -> str:
        return f'arena-allow-{self.suffix}'

    @property
    def allowed_name(self) -> str:
        return f'arena-allowed-{self.suffix}'

    @property
    def canary_name(self) -> str:
        return f'arena-canary-{self.suffix}'

    def start(self) -> None:
        try:
            self._must('network', 'create', '--label', f'{LABEL}=observer', self.open_network)
            self._must('network', 'create', '--internal', '--label', f'{LABEL}=observer', self.allow_network)
            self._service(self.canary_name, CANARY_SERVER, self.open_network, CANARY_HOST)
            self._service(self.allowed_name, ALLOWED_SERVER, self.open_network, ALLOWED_HOST)
            self._must('network', 'connect', '--alias', ALLOWED_HOST, self.allow_network, self.allowed_name)
            inspected = self._must(
                'inspect',
                '-f',
                '{{(index .NetworkSettings.Networks "' + self.open_network + '").IPAddress}}',
                self.canary_name,
            )
            self.canary_ip = inspected.strip()
            self.started = True
            self._wait_ready()
        except Exception:
            self.stop()
            raise

    def network_plan(self, egress: EgressPolicy) -> tuple[list[str], list[str]]:
        """Map an egress policy to arena networks. The canary is every sandbox's upstream resolver."""
        if egress.mode == 'open':
            return [self.open_network], [self.canary_ip]
        if egress.mode == 'allowlist':
            unknown = [host for host in egress.allow if host != ALLOWED_HOST]
            if unknown:
                raise DockerError(f'The local lab can only allowlist {ALLOWED_HOST}, not {unknown}')
            return [self.allow_network], [self.canary_ip]
        return [], []

    def placeholders(self, token: str) -> dict[str, str]:
        canary = f'http://{CANARY_HOST}:{PORT}'
        return {
            'token': token,
            'allowed_url': f'http://{ALLOWED_HOST}:{PORT}/',
            'allowed_host': ALLOWED_HOST,
            'canary_url': f'{canary}/hit/{token}',
            'canary_ip_url': f'http://{self.canary_ip}:{PORT}/hit/{token}',
            'redirect_url': f'http://{ALLOWED_HOST}:{PORT}/redirect?to={canary}/hit/{token}',
            'exfil_name': f'{token}.{EXFIL_ZONE}',
        }

    def hits(self, token: str) -> dict[str, int]:
        """Count canary log entries that carry this trial's token. Read from outside every sandbox."""
        out = docker('exec', self.canary_name, 'cat', '/tmp/canary.jsonl', timeout=30)
        if out.returncode != 0:
            raise DockerError('Canary log unavailable; the observation is incomplete')
        counts = {'http': 0, 'dns': 0}
        for line in _text(out.stdout).splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if token in entry.get('value', '') and entry.get('kind') in counts:
                counts[entry['kind']] += 1
        return counts

    def describe(self) -> dict:
        return {
            'kind': 'local-docker-lab',
            'networks': {'open': self.open_network, 'allowlist': self.allow_network + ' (--internal)'},
            'allowed_host': ALLOWED_HOST,
            'canary_host': CANARY_HOST,
            'exfil_zone': EXFIL_ZONE,
            'note': 'Owned, local, synthetic endpoints only.',
        }

    def stop(self) -> CleanupReport:
        removed, leftovers = [], []
        for name in (self.allowed_name, self.canary_name):
            docker('rm', '-f', name, timeout=60)
            (leftovers if docker('container', 'inspect', name, timeout=30).returncode == 0 else removed).append(name)
        for network in (self.open_network, self.allow_network):
            # A sandbox that outlived its probe would pin the network; remove arena sandboxes still attached.
            attached = docker('network', 'inspect', '-f', '{{range .Containers}}{{.Name}} {{end}}', network, timeout=30)
            for name in _text(attached.stdout).split():
                if name.startswith('arena-sbx-'):
                    docker('rm', '-f', name, timeout=60)
            docker('network', 'rm', network, timeout=60)
            (leftovers if docker('network', 'inspect', network, timeout=30).returncode == 0 else removed).append(
                network
            )
        self.started = False
        return CleanupReport(confirmed=not leftovers, removed=removed, leftovers=leftovers)

    def _service(self, name: str, script: str, network: str, alias: str) -> None:
        self._must(
            'run',
            '-d',
            '--name',
            name,
            '--label',
            f'{LABEL}=observer',
            '--network',
            network,
            '--network-alias',
            alias,
            self.image,
            'python3',
            '-c',
            script,
        )

    def _wait_ready(self) -> None:
        probe = (
            'import urllib.request,time\n'
            'for _ in range(50):\n'
            '    try:\n'
            f'        urllib.request.urlopen("http://127.0.0.1:{PORT}/ready", timeout=1); break\n'
            '    except Exception: time.sleep(0.1)\n'
        )
        for name in (self.allowed_name, self.canary_name):
            self._must('exec', name, 'python3', '-c', probe)
        # The readiness request itself is logged by the canary; it carries no trial token.

    def _must(self, *args: str) -> str:
        try:
            done = docker(*args, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise DockerError(f'docker {args[0]} timed out') from exc
        if done.returncode != 0:
            raise DockerError(f'docker {" ".join(args[:2])} failed: {_text(done.stderr).strip()[:500]}')
        return _text(done.stdout)


def new_token() -> str:
    """DNS-safe, per-trial token so canary hits can be attributed to exactly one probe."""
    return 'arena' + secrets.token_hex(8)
