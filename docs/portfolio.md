# How to present this work

## A concise introduction

I built two connected labs around an inference team's investigation workflow. The first captures real streaming inference and verifies distributed traces in Logfire. The second lets Python execute in Monty over a deliberately narrow evidence interface, then checks the computed result against the source measurements.

The Monty demo includes incomplete evidence, fabricated output, denied host access, time and memory limits, and fresh-session recovery. It has a no-credentials demonstration path, an optional Pydantic AI code-generation path, local OpenTelemetry evidence, and repeatable Pydantic Evals cases. The accompanying runbook explains what to ask a customer, what to demonstrate, and which claims the evidence does not support.

## Walk through the evidence

| Capability | Where to show it |
| --- | --- |
| Understanding the customer's decision | Discovery questions and agreed criteria in the customer playbook |
| Python and AI integration | Typed code proposal, Monty execution, host capability and independent validator |
| Observability debugging | Real parent-child spans connecting analysis, worker execution and host reads |
| Evaluation design | Explicit expected findings, failure cases, incomplete-evidence handling and exported results |
| Repeatable demonstration | Locked dependencies, laptop UI, CLI, CI and a ten-minute runbook |
| Engineering judgment | Honest distinction between fixed-policy arithmetic and open-ended model reasoning |
| Upstream involvement | [Monty splitlines contribution](https://github.com/pydantic/monty/pull/1106) with a focused compatibility regression |

The original [Logfire Inference Lab](https://github.com/rudrakshkarpe/logfire-inference-lab) provides the separate real-GPU capture and hosted trace verification. Do not imply that this Monty repository has repeated those GPU measurements or verified its own hosted ingestion unless a new run records that evidence.

## Before using it in an application

Record a short walkthrough in your own words. Show one successful investigation, one unsupported result, and one denied capability. Explain which layer makes each decision. Be ready to modify a threshold, inspect the trace, and discuss how you would replace the public fixture with a customer-authorized data adapter.

The [Pre-Sales Solutions Engineer role](https://pydantic.dev/jobs/pre-sales-solutions-engineer) has a hard living-and-working timezone requirement between PT and CET. Confirm your eligibility separately. This portfolio demonstrates relevant work; it does not establish location eligibility or guarantee an interview.
