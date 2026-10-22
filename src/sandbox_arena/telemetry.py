"""Local OpenTelemetry evidence, with explicitly enabled hosted Logfire export."""

import os
import threading
from collections import deque
from pathlib import Path

import logfire
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

_recent_spans: deque[dict] = deque(maxlen=2000)
_recent_lock = threading.Lock()


def trace_summary(trace_id: str) -> list[dict]:
    """Public-safe projection: no code, data values, resource IDs or local paths."""
    with _recent_lock:
        return sorted(
            [span.copy() for span in _recent_spans if span['trace_id'] == trace_id],
            key=lambda span: span['start_ns'],
        )


class JsonlExporter(SpanExporter):
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.Lock()

    def export(self, spans):
        with self.lock, self.path.open('a') as stream:
            for span in spans:
                stream.write(span.to_json(indent=None) + '\n')
                with _recent_lock:
                    _recent_spans.append(
                        {
                            'name': span.name[:120],
                            'scope': span.instrumentation_scope.name,
                            'trace_id': f'{span.context.trace_id:032x}',
                            'span_id': f'{span.context.span_id:016x}',
                            'parent_id': f'{span.parent.span_id:016x}' if span.parent else None,
                            'start_ns': span.start_time,
                            'duration_ms': round((span.end_time - span.start_time) / 1_000_000, 3),
                        }
                    )
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def configure(path: Path, *, export: bool = False) -> None:
    if export and not os.environ.get('LOGFIRE_TOKEN'):
        raise ValueError('LOGFIRE_TOKEN is required when hosted export is enabled')
    # Monty's Rust spans obey RUST_LOG independently of the Python SDK.
    # Scope this process-local override to the pool, preserving unrelated filters.
    os.environ['RUST_LOG'] = f'{os.environ.get("RUST_LOG", "warn")},monty_pool=info'
    logfire.configure(
        service_name='sandbox-arena',
        send_to_logfire=export,
        console=False,
        additional_span_processors=[SimpleSpanProcessor(JsonlExporter(path))],
    )
    # Real native session, feed and host-call spans, not a simulated timeline.
    # This records code and public fixture values. See docs/security.md before adapting.
    logfire.instrument_monty()
    logfire.instrument_pydantic_ai()
