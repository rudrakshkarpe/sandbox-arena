import argparse
import json
from pathlib import Path
from typing import get_args

import logfire

from .agent import run_live
from .evaluation import evaluate
from .models import RunRequest, Scenario
from .programs import PROGRAMS
from .sandbox import make_pool
from .service import run
from .telemetry import configure


def main():
    parser = argparse.ArgumentParser(description='Run the Sandbox Arena workbench and Monty examples.')
    parser.add_argument('--export-logfire', action='store_true', help='Explicitly export traces using LOGFIRE_TOKEN')
    parser.add_argument('--traces', type=Path, default=Path('artifacts/traces.jsonl'))
    commands = parser.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve', help='Start the local sandbox workbench')
    serve.add_argument('--port', type=int, default=8022)
    evaluation = commands.add_parser('evaluate', help='Execute deterministic Pydantic Evals cases')
    evaluation.add_argument('--output', type=Path, default=Path('artifacts/evaluation.json'))
    evaluation.add_argument('--model', help='Run the four evidence cases with a live model, up to eight requests')
    investigation = commands.add_parser('run', help='Run one investigation')
    investigation.add_argument('--scenario', choices=get_args(Scenario), default='queue-pressure')
    investigation.add_argument('--challenge', choices=PROGRAMS, default='analysis')
    investigation.add_argument('--model', help='Explicit opt-in to a paid live model, e.g. openai:MODEL_ID')
    investigation.add_argument('--output', type=Path, default=Path('artifacts/run.json'))
    args = parser.parse_args()
    if args.command == 'run' and args.model and args.challenge != 'analysis':
        parser.error('Live generation supports analysis only; adversarial cases are scripted')
    configure(args.traces, export=args.export_logfire)
    try:
        if args.command == 'serve':
            import uvicorn

            from .web import create_app

            uvicorn.run(create_app(), host='127.0.0.1', port=args.port)
        elif args.command == 'evaluate':
            if not evaluate(args.output, model=args.model):
                raise SystemExit(1)
        else:
            with make_pool() as pool:
                result = (
                    run_live(pool, args.scenario, args.model)
                    if args.model
                    else run(pool, RunRequest(scenario=args.scenario, challenge=args.challenge))
                )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.model_dump_json(indent=2) + '\n')
            print(json.dumps(result.model_dump(), indent=2))
            if result.attempts[-1].status != 'verified':
                raise SystemExit(1)
    finally:
        logfire.force_flush()


if __name__ == '__main__':
    main()
