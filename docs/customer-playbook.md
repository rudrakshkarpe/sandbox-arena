# Customer evaluation playbook

## Start with the customer's problem

**Prospect:** an inference platform team wants analysts to investigate latency without handing an agent a shell, database credential, or unrestricted telemetry export.

**Evaluation question:** can we let generated code compute over approved evidence, reject unsupported answers, and explain every failure to an engineer?

Ask these questions before opening the demo:

1. Which decision is slow today: incident triage, capacity planning, or customer support?
2. Where is the evidence, and who is allowed to read it? Is request-level data available?
3. What is unacceptable: incorrect numbers, tenant leakage, unpredictable cost, or an opaque failure?
4. Who will judge the result: platform engineering, security, the application owner, or all three?
5. What measurable result would justify the next evaluation stage?

Do not promise an MTTR reduction from this lab. First measure the customer's existing workflow, agree on a representative incident set, and compare end-to-end results with a human baseline.

## Ten-minute demo

**0:00 to 1:00.** State the problem and the agreed success criteria. Explain that the measurements are historical, the script is authored, and the sandbox execution is happening now. No GPU is running.

**1:00 to 3:00.** Run queue pressure. Inspect the code's two evidence reads. Show the measured queue p95 and slowdown against baseline. Explain why separate percentiles are not one request's timing components. A useful next step is inspecting individual traces before changing capacity.

**3:00 to 4:00.** Switch to long context. The leading signal changes to prefill. The operational next step is examining prompt length and prefill behavior, not assuming every slow response is caused by queueing. Recovery provides a control case.

**4:00 to 5:00.** Run early close. The system retains unknown engine measurements and refuses a causal diagnosis. This is where a confident narrative would be misleading.

**5:00 to 7:00.** Try fabricated numbers, cross-scope access, and caught denial. Explain the distinction between schema validation, host authorization, and source verification. Catching a Python exception does not erase the host audit.

**7:00 to 8:00.** Run the infinite loop, then a healthy investigation. Show the budget failure and fresh-session recovery. Explain that a worker's allocator budget is different from the host's RSS and total request deadline.

**8:00 to 9:00.** Inspect the trace ID and local JSONL. With hosted export explicitly configured and verified, use that same trace ID in Logfire to navigate the investigation, native Monty spans, host reads, and validator. If hosted access is unavailable, show local evidence and say so.

**9:00 to 10:00.** Run the acceptance suite and download a result. Agree on a next stage using a small, approved customer dataset. If demonstrating live generation, label the provider/model and show every failed attempt as well as successful ones.

## Agree on success criteria before the POC

| Criterion | Lab acceptance | Customer extension |
| --- | --- | --- |
| Numerical reliability | Computed fields match pinned evidence | Independently labeled incidents, tolerances, false-positive analysis |
| Data authority | Out-of-scope requests rejected, caught denials remain visible | Real identity, per-tenant server-side authorization, audited data adapter |
| Failure containment | Time/memory limits stop code; fresh runs succeed | OS isolation, process/RSS budgets, load and cancellation testing |
| Explainability | Trace connects execution, evidence reads and verification | Hosted ingestion and access controls verified with the customer's telemetry |
| Model usefulness | Not claimed by scripted cases | Held-out prompts, model/version recording, repair rate, cost, latency, refusals |

## Answer objections directly

**Why not just give the model a Python shell?** A general shell supplies capabilities this analysis does not need. Monty exposes only the host interactions we choose. The quality of those host interactions remains our responsibility.

**Why not ordinary Python for this fixed computation?** For these four fixed questions, ordinary trusted Python is simpler. Monty becomes relevant when the analyst needs to generate new computations over approved data. This lab makes that execution boundary visible without pretending the fixed policy requires an LLM.

**Why Pydantic as well as Monty?** Monty controls execution. Pydantic validates the output contract. Source verification checks whether well-formed output is also supported by the evidence. Each answers a different question.

**What does Logfire add?** Engineers can follow the complete investigation through execution, host reads and validation rather than seeing only a final error or generated paragraph. The local exporter demonstrates the actual OTel relationships before hosted integration.

**Does this prove prompt injection is solved?** No. It demonstrates specific denied capabilities and evidence checks. It does not evaluate a broad prompt-injection corpus or model behavior.

## Relevance to a solutions engineering portfolio

Present this as a repeatable technical evaluation: discovery questions, architecture tradeoffs, observable failures, measurable success criteria, and a reproducible handoff. Pair it with the original inference lab to show the complete path from real telemetry capture to controlled analysis.

Do not claim customer adoption, revenue impact, production reliability, or live model accuracy without evidence. The linked Pydantic role also has a hard PT-to-CET location/timezone requirement; portfolio quality does not establish eligibility.
