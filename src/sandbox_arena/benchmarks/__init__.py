"""Versioned, capability-aware workloads. Payloads are executed only by Monty."""

from importlib.resources import files

from pydantic import BaseModel

UPSTREAM_COMMIT = 'c07127e731ec14e55f93dee767977bf00bb76dce'
UPSTREAM = f'https://github.com/nibzard/ai-sandbox-benchmark/blob/{UPSTREAM_COMMIT}/tests/'


class Workload(BaseModel):
    id: str
    name: str
    category: str
    description: str
    code: str
    expected: object = None
    expected_status: str = 'ok'
    requires: list[str] = ['python-subset']
    source: str | None = None
    version: str = '1'
    adapted: bool = False


def payload(name: str) -> str:
    return files(__package__).joinpath(f'{name}.py.txt').read_text()


WORKLOADS = {
    item.id: item
    for item in [
        Workload(
            id='primes-10',
            name='First ten primes',
            category='Compute',
            description='Trial division, a list, and a reduction. A small deterministic compute baseline.',
            code=payload('primes_10'),
            expected={'primes': [2, 3, 5, 7, 11, 13, 17, 19, 23, 29], 'sum': 129, 'average': 12.9},
            source=UPSTREAM + 'test_calculate_primes.py',
            adapted=True,
        ),
        Workload(
            id='primes-1000',
            name='Primes through 1,000',
            category='Compute',
            description='A larger trial-division workload. Checks all 168 primes through their count and sum.',
            code=payload('primes_1000'),
            expected={'count': 168, 'sum': 76127},
            source=UPSTREAM + 'test_improved_calculate_primes.py',
            adapted=True,
        ),
        Workload(
            id='tool-access',
            name='Approved tool access',
            category='Capabilities',
            description='Read a bounded fixture through an explicitly permitted host function.',
            code="rows = read_fixture()\n{'total': sum(row['value'] for row in rows), 'rows': len(rows)}",
            expected={'total': 60, 'rows': 3},
            requires=['python-subset', 'host-callbacks'],
        ),
        Workload(
            id='time-limit',
            name='Runaway loop',
            category='Boundaries',
            description='An infinite loop should hit its execution limit. A limited result passes this check.',
            code='while True:\n    pass',
            expected_status='limited',
        ),
        Workload(
            id='filesystem',
            name='Filesystem boundary',
            category='Boundaries',
            description='Attempt to read a synthetic forbidden path. The OS callback must deny the request.',
            code="from pathlib import Path\nPath('/sandbox-lab/forbidden.txt').read_text()",
            expected_status='denied',
            requires=['python-subset', 'os-policy'],
        ),
    ]
}

EXAMPLES = [
    {
        'id': 'hello',
        'name': 'Hello, Monty',
        'code': "print('Hello from an isolated session')\n{'answer': 6 * 7, 'runtime': 'Monty'}",
    },
    *[{'id': w.id, 'name': w.name, 'code': w.code} for w in WORKLOADS.values()],
    {'id': 'memory', 'name': 'Memory limit', 'code': 'values = [0] * 20_000_000\nlen(values)'},
]
