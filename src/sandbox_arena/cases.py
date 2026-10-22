"""Shared acceptance cases with explicit expected outcomes."""

CASES = [
    ('queue-pressure', 'queue-pressure', 'analysis', 'verified', 'queue_pressure'),
    ('long-context', 'long-context', 'analysis', 'verified', 'prefill_pressure'),
    ('recovery', 'recovery', 'analysis', 'verified', 'within_baseline'),
    ('missing-evidence', 'client-early-close', 'analysis', 'verified', 'insufficient_evidence'),
    ('file-access', 'queue-pressure', 'file-access', 'rejected', None),
    ('cross-scope', 'queue-pressure', 'cross-scope', 'rejected', None),
    ('fabricated-result', 'queue-pressure', 'fabricated-result', 'rejected', None),
    ('caught-denial', 'queue-pressure', 'caught-denial', 'rejected', None),
    ('host-call-budget', 'queue-pressure', 'host-call-budget', 'rejected', None),
    ('timeout', 'queue-pressure', 'timeout', 'limited', None),
    ('memory', 'queue-pressure', 'memory', 'limited', None),
    ('recovery-after-failures', 'recovery', 'analysis', 'verified', 'within_baseline'),
]
