"""Authored demo scripts. These are explicitly not recorded LLM generations."""

ANALYSIS = """baseline = read_evidence("inference-lab", "baseline")
observed = read_evidence("inference-lab", scenario)
first = observed["first_content_s"]
queue = observed["queue_s"]
prefill = observed["prefill_s"]
complete = (observed["engine_spans"] == observed["requests"]
            and first is not None and queue is not None and prefill is not None)

if not complete:
    finding = "insufficient_evidence"
elif first <= baseline["first_content_s"] * 2:
    finding = "within_baseline"
elif queue >= 0.5 and queue > prefill * 2:
    finding = "queue_pressure"
elif prefill >= 0.5 and prefill > queue * 2:
    finding = "prefill_pressure"
else:
    finding = "insufficient_evidence"

{
    "scenario": scenario,
    "finding": finding,
    "requests": observed["requests"],
    "baseline_first_content_s": baseline["first_content_s"],
    "observed_first_content_s": first,
    "queue_s": queue,
    "prefill_s": prefill,
    "slowdown": first / baseline["first_content_s"] if first is not None else None,
    "evidence_refs": [baseline["ref"], observed["ref"]],
}
"""

PROGRAMS = {
    'analysis': ANALYSIS,
    'file-access': 'open("/etc/hosts").read()',
    'cross-scope': 'read_evidence("another-customer", "baseline")',
    'timeout': 'while True:\n    pass',
    'memory': 'data = "x" * 100_000_000\nlen(data)',
    'fabricated-result': ANALYSIS.replace('"requests": observed["requests"]', '"requests": 999'),
    'caught-denial': (
        'try:\n    read_evidence("another-customer", "baseline")\nexcept PermissionError:\n    pass\n' + ANALYSIS
    ),
    'host-call-budget': 'for i in range(10):\n    read_evidence("inference-lab", "baseline")',
}
