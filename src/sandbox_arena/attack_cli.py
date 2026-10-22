"""Credential-free scenario execution and offline report verification."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .playground_models import RunSpec
from .playground_runner import MontyProvider, Runner, RunStore
from .sandbox import make_pool
from .scenario_catalog import catalog_entries
from .scenario_reports import verify_report


def read_report(path: Path) -> dict:
    def reject_constant(value):
        raise ValueError(f'Non-finite JSON constant: {value}')

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    with path.open('rb') as stream:
        raw = stream.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError('Report exceeds the 8 MB input limit')
    result = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique_keys)
    if not isinstance(result, dict):
        raise ValueError('Report must be a JSON object')
    return result


def execute(spec: RunSpec | None = None, source: dict | None = None) -> dict:
    with TemporaryDirectory(prefix='sandbox-arena-') as directory, make_pool() as pool:
        runner = Runner(MontyProvider(pool), RunStore(Path(directory) / 'runs.db'))
        try:
            run_id = runner.replay(source) if source is not None else runner.submit(spec)
            runner.executor.shutdown(wait=True)
            return runner.store.get(run_id)
        finally:
            runner.close()


def register(commands):
    commands.add_parser('scenarios', help='List versioned scenario packs as JSON')
    attack = commands.add_parser('attack', help='Execute a bounded, authored scenario pack')
    attack.add_argument('scenario_id')
    attack.add_argument('--iterations', type=int, default=3)
    attack.add_argument('--output', type=Path, default=Path('artifacts/scenario.json'))
    verify = commands.add_parser('verify', help='Verify a report offline without executing its code')
    verify.add_argument('report', type=Path)
    replay = commands.add_parser('replay', help='Replay an unchanged installed scenario from a report')
    replay.add_argument('report', type=Path)
    replay.add_argument('--output', type=Path, default=Path('artifacts/replay.json'))


def dispatch(args) -> int:
    if args.command == 'scenarios':
        print(json.dumps(catalog_entries(), indent=2))
        return 0
    if args.command == 'verify':
        result = verify_report(read_report(args.report))
        print(json.dumps(result, indent=2))
        return 0 if result['verified'] else 1
    if args.command == 'replay':
        record = execute(source=read_report(args.report))
    else:
        record = execute(RunSpec(mode='scenario', scenario_id=args.scenario_id, iterations=args.iterations))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'report': str(args.output), **verify_report(record)}, indent=2))
    return 0 if verify_report(record)['verified'] else 1
