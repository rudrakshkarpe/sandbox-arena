"""Loopback demo UI. No paid model endpoint or production authentication implied."""

from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .evidence import CAPTURE, CAPTURE_SHA256, SOURCE_URL, record
from .models import RunRequest, RunResult
from .programs import PROGRAMS
from .sandbox import LIMITS, make_pool
from .service import run
from .telemetry import trace_summary


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        with make_pool() as pool:
            app.state.pool = pool
            yield

    app = FastAPI(title='Monty Incident Lab', lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    @app.middleware('http')
    async def local_only(request: Request, call_next):
        if request.method == 'POST':
            origin = request.headers.get('origin')
            expected = f'{request.url.scheme}://{request.headers.get("host")}'
            if origin is not None and origin != expected:
                return JSONResponse({'detail': 'Cross-origin execution is disabled'}, status_code=403)
            if request.headers.get('content-type', '').split(';')[0] != 'application/json':
                return JSONResponse({'detail': 'Use application/json'}, status_code=415)
            # Bound actual streamed bytes, including requests without Content-Length.
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 64_000:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
        )
        return response

    static = files('monty_incident_lab').joinpath('static')
    app.mount('/static', StaticFiles(directory=str(static)), name='static')

    @app.get('/')
    def index():
        return FileResponse(str(static.joinpath('index.html')))

    @app.get('/api/catalog')
    def catalog():
        return {
            'programs': PROGRAMS,
            'limits': LIMITS,
            'source': SOURCE_URL,
            'capture_id': CAPTURE['capture']['capture_id'],
            'capture_sha256': CAPTURE_SHA256,
            'records': {name: record(name) for name in CAPTURE['scenarios']},
        }

    @app.post('/api/run', response_model=RunResult)
    def investigate(request: RunRequest):
        try:
            return run(app.state.pool, request)
        except TimeoutError as exc:
            raise HTTPException(503, 'All sandbox workers are busy. Try again shortly.') from exc

    @app.get('/api/traces/{trace_id}')
    def get_trace(trace_id: str):
        if len(trace_id) != 32 or any(char not in '0123456789abcdef' for char in trace_id):
            raise HTTPException(422, 'Expected a 32-character hexadecimal trace ID')
        spans = trace_summary(trace_id)
        if not spans:
            raise HTTPException(404, 'Trace is no longer in the local recent-span buffer')
        return {'trace_id': trace_id, 'spans': spans}

    return app
