"""CLI for the container/VM tier: list packs, run them locally on Docker, verify reports offline."""

import json
import os
from pathlib import Path

from .attack_cli import read_report
from .vm_runner import VM_PACKS, run_vm_pack, verify_vm_report, vm_pack_digest

EXIT = {'expected_observed': 0, 'unexpected_observed': 3}


def register(commands):
    commands.add_parser('vm-scenarios', help='List container/VM-tier scenario packs as JSON')
    attack = commands.add_parser('vm-attack', help='Run a VM-tier pack on a local Docker sandbox')
    attack.add_argument('scenario_id', choices=sorted(VM_PACKS) + ['all'])
    attack.add_argument('--profile', choices=['default', 'strict', 'both'], default='both')
    attack.add_argument('--iterations', type=int, default=1)
    attack.add_argument('--image', default=os.environ.get('ARENA_DOCKER_IMAGE'), help='Image with python3')
    attack.add_argument('--output-dir', type=Path, default=Path('artifacts/vm'))
    verify = commands.add_parser('vm-verify', help='Verify a VM-tier report offline without executing code')
    verify.add_argument('report', type=Path)


def dispatch(args) -> int:
    if args.command == 'vm-scenarios':
        print(
            json.dumps(
                [{**p.model_dump(mode='json'), 'sha256': vm_pack_digest(p)} for p in VM_PACKS.values()], indent=2
            )
        )
        return 0
    if args.command == 'vm-verify':
        result = verify_vm_report(read_report(args.report))
        print(
            json.dumps(
                {key: value for key, value in result.items() if key != 'assessment'}
                | {'outcome': result['assessment']['outcome']},
                indent=2,
            )
        )
        return EXIT.get(result['assessment']['outcome'], 1) if result['evidence_consistent'] else 1

    from .adapters.docker import DockerAdapter, docker_available
    from .observers import LocalDockerObservers

    if not docker_available():
        raise OSError('Docker daemon not reachable. Start Docker Desktop (or dockerd) and retry.')
    adapter = DockerAdapter(image=args.image)
    observers = LocalDockerObservers(image=adapter.image)
    adapter.network_plan = observers.network_plan
    pack_ids = sorted(VM_PACKS) if args.scenario_id == 'all' else [args.scenario_id]
    profiles = ['default', 'strict'] if args.profile == 'both' else [args.profile]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary, worst = [], 0
    observers.start()
    try:
        for pack_id in pack_ids:
            for profile in profiles:
                record = run_vm_pack(VM_PACKS[pack_id], adapter, observers, profile, args.iterations)
                path = args.output_dir / f'{pack_id}.{profile}.json'
                path.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
                outcome = record['assessment']['outcome']
                summary.append({'pack': pack_id, 'profile': profile, 'outcome': outcome, 'report': str(path)})
                worst = max(worst, EXIT.get(outcome, 1))
    finally:
        lab = observers.stop()
    print(json.dumps({'adapter': adapter.version(), 'lab_cleanup_confirmed': lab.confirmed, 'runs': summary}, indent=2))
    return worst
