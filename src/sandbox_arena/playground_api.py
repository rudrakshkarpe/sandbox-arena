"""Local playground endpoints. All execution goes through the bounded runner."""

import asyncio
import json
from importlib.metadata import version

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .benchmarks import EXAMPLES, WORKLOADS
from .playground_models import RunSpec
from .playground_runner import CAPABILITIES, TERMINAL
from .scenario_catalog import PACKS, catalog_entries, pack_digest
from .scenario_reports import verify_report


def router() -> APIRouter:
    api = APIRouter(prefix='/api/playground')

    def find(request, run_id):
        result = request.app.state.runner.store.get(run_id)
        if result is None:
            raise HTTPException(404, 'Run not found')
        return result

    @api.get('/catalog')
    def catalog():
        return {
            'provider': {
                'id': 'monty',
                'name': 'Pydantic Monty',
                'version': version('pydantic-monty'),
                'capabilities': CAPABILITIES,
            },
            'scenarios': catalog_entries(),
            'examples': EXAMPLES,
            'benchmarks': [w.model_dump() for w in WORKLOADS.values()],
            'limits': {'iterations': 50, 'warmups': 5, 'timeout_ms': 500, 'memory_mb': 32, 'code_chars': 12_000},
        }

    @api.get('/scenarios/{scenario_id}')
    def scenario(scenario_id: str):
        pack = PACKS.get(scenario_id)
        if pack is None:
            raise HTTPException(404, 'Scenario not found')
        return {**pack.model_dump(mode='json'), 'sha256': pack_digest(pack)}

    @api.post('/runs', status_code=202)
    def create_run(spec: RunSpec, request: Request):
        try:
            run_id = request.app.state.runner.submit(spec)
        except OverflowError as exc:
            raise HTTPException(429, str(exc)) from exc
        return {'id': run_id}

    @api.get('/runs')
    def list_runs(request: Request, limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
        return request.app.state.runner.store.list(limit=limit, offset=offset)

    @api.get('/runs/{run_id}')
    def get_run(run_id: str, request: Request):
        return find(request, run_id)

    @api.post('/runs/{run_id}/cancel')
    def cancel_run(run_id: str, request: Request):
        find(request, run_id)
        request.app.state.runner.cancel(run_id)
        return {'message': 'Cancellation requested. The current bounded trial will finish before stopping.'}

    @api.get('/runs/{run_id}/verify')
    def verify_run(run_id: str, request: Request):
        record = find(request, run_id)
        if record['spec']['mode'] != 'scenario':
            raise HTTPException(422, 'Verification requires a scenario run')
        return verify_report(record)

    @api.post('/runs/{run_id}/replay', status_code=202)
    def replay_run(run_id: str, request: Request):
        try:
            return {'id': request.app.state.runner.replay(find(request, run_id))}
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except OverflowError as exc:
            raise HTTPException(429, str(exc)) from exc

    @api.get('/runs/{run_id}/export')
    def export_run(run_id: str, request: Request):
        record = find(request, run_id)
        return JSONResponse(
            record, headers={'Content-Disposition': f'attachment; filename="sandbox-run-{record["id"]}.json"'}
        )

    @api.get('/runs/{run_id}/events')
    async def events(run_id: str, request: Request):
        find(request, run_id)
        try:
            last_id = max(0, int(request.headers.get('last-event-id', '0')))
        except ValueError as exc:
            raise HTTPException(422, 'Invalid event cursor') from exc

        async def stream():
            cursor = last_id
            while not await request.is_disconnected():
                record = find(request, run_id)
                for event in record['events']:
                    if event['id'] > cursor:
                        cursor = event['id']
                        yield f'id: {cursor}\ndata: {json.dumps(event)}\n\n'
                if record['status'] in TERMINAL:
                    break
                yield ': keepalive\n\n'
                await asyncio.sleep(0.15)

        return StreamingResponse(
            stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    return api
