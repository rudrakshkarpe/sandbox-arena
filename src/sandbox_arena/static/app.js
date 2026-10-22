const $ = (id) => document.getElementById(id);
let catalog, lastResult;
const titles = {
  queue_pressure: "Queue pressure is the leading signal.",
  prefill_pressure: "Prefill is the leading signal.",
  within_baseline: "Latency is within the baseline policy.",
  insufficient_evidence: "There is not enough evidence to diagnose.",
};
const seconds = (value) =>
  value === null ? "Unknown" : `${value.toFixed(3)} s`;
function text(tag, content, className) {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}
function resetCode() {
  $("code").value = catalog.programs[$("challenge").value];
}
async function requestRun(payload) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok)
    throw new Error(
      `Request failed (${response.status}). Check the local server.`,
    );
  return response.json();
}
function render(result) {
  lastResult = result;
  const attempt = result.attempts.at(-1),
    a = attempt.analysis;
  $("empty").hidden = true;
  $("result").hidden = false;
  $("status").textContent = attempt.status.toUpperCase();
  $("outcome-label").textContent = a
    ? "SOURCE CHECK PASSED"
    : "NO DIAGNOSIS ACCEPTED";
  $("outcome-label").textContent += ` / ${result.scenario} / ${result.mode}`;
  $("finding").textContent = a
    ? titles[a.finding]
    : {
        limited: "Execution stopped at its budget.",
        rejected: "The host rejected this run.",
        error: "The program could not complete.",
      }[attempt.status];
  $("message").textContent = attempt.message;
  $("timing").textContent =
    `${attempt.elapsed_ms.toFixed(1)} ms · execution + verification`;
  $("metrics").replaceChildren();
  $("bars").replaceChildren();
  $("metrics").hidden = !a;
  $("chart").hidden = !a;
  if (a) {
    [
      [seconds(a.observed_first_content_s), "Observed p95 first content"],
      [
        a.slowdown === null ? "Unknown" : `${a.slowdown.toFixed(1)}×`,
        "Relative to baseline",
      ],
      [String(a.requests), "Recorded requests"],
    ].forEach(([value, label]) => {
      const item = text("div", "", "metric");
      item.append(text("strong", value), text("span", label));
      $("metrics").append(item);
    });
    const values = [
      ["Baseline", a.baseline_first_content_s],
      ["First content", a.observed_first_content_s],
      ["Queue", a.queue_s],
      ["Prefill", a.prefill_s],
    ];
    const max = Math.max(...values.map(([, v]) => v ?? 0), 0.001);
    values.forEach(([label, value]) => {
      const row = text("div", "", "bar-row");
      const meter = document.createElement("meter");
      meter.max = max;
      meter.value = value ?? 0;
      meter.setAttribute("aria-label", `${label}: ${seconds(value)}`);
      row.append(text("span", label), meter, text("b", seconds(value)));
      $("bars").append(row);
    });
  }
  $("audit").replaceChildren();
  attempt.audit.forEach((event) => {
    const row = text("li", "");
    row.append(
      text(
        "b",
        event.allowed ? "ALLOW" : "DENY",
        event.allowed ? "" : "denied",
      ),
      text("span", `${event.operation}: ${event.detail}`),
    );
    $("audit").append(row);
  });
  if (!attempt.audit.length)
    $("audit").append(text("li", "No host capability was called."));
  $("trace-id").textContent = attempt.trace_id;
  $("trace-tree").replaceChildren();
  $("trace-tree").hidden = true;
  $("caveat").textContent = result.caveat;
  $("json").textContent = JSON.stringify(result, null, 2);
}
function busy(state) {
  $("run").disabled = state;
  $("evaluate").disabled = state;
}
$("run").addEventListener("click", async () => {
  busy(true);
  $("status").textContent = "RUNNING";
  try {
    const payload = {
      scenario: $("scenario").value,
      challenge: $("challenge").value,
    };
    if ($("code").value !== catalog.programs[payload.challenge])
      payload.code = $("code").value;
    render(await requestRun(payload));
  } catch (error) {
    lastResult = null;
    $("status").textContent = "ERROR";
    $("empty").hidden = true;
    $("result").hidden = false;
    $("finding").textContent = "Run failed";
    $("message").textContent = error.message;
    $("outcome-label").textContent = "NO RESULT RECEIVED";
    $("metrics").hidden = true;
    $("chart").hidden = true;
    $("audit").replaceChildren();
    $("trace-id").textContent = "Unavailable";
    $("timing").textContent = "";
    $("json").textContent = "No response available.";
  } finally {
    busy(false);
  }
});
$("reset").addEventListener("click", resetCode);
$("challenge").addEventListener("change", resetCode);
$("code").addEventListener("keydown", (event) => {
  if (
    (event.ctrlKey || event.metaKey) &&
    event.key === "Enter" &&
    !$("run").disabled
  )
    $("run").click();
});
$("download").addEventListener("click", () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `monty-run-${lastResult.run_id}.json`;
  a.click();
  URL.revokeObjectURL(url);
});
$("inspect-trace").addEventListener("click", async () => {
  if (!lastResult) return;
  const tree = $("trace-tree");
  const requestedId = lastResult.attempts.at(-1).trace_id;
  tree.hidden = false;
  tree.textContent = "Loading completed spans…";
  try {
    const response = await fetch(`/api/traces/${requestedId}`);
    if (!response.ok)
      throw new Error("Trace unavailable in the recent-span buffer.");
    const { spans } = await response.json();
    if (lastResult?.attempts.at(-1).trace_id !== requestedId) return;
    const byId = new Map(spans.map((span) => [span.span_id, span]));
    tree.replaceChildren();
    spans.forEach((span) => {
      let parent = byId.get(span.parent_id),
        depth = 0;
      while (parent && depth < 8) {
        depth++;
        parent = byId.get(parent.parent_id);
      }
      const row = text("div", "", "trace-row");
      row.append(
        text("span", `${"  ".repeat(depth)}${span.name}`, "span-name"),
        text("span", `${span.duration_ms.toFixed(2)} ms`),
      );
      tree.append(row);
    });
    tree.append(
      text(
        "p",
        "Completed OTel spans from this process. Native Monty session, run and call spans retain their real parent relationships. Recent buffer: 2,000 spans.",
        "fine",
      ),
    );
  } catch (error) {
    tree.textContent = error.message;
  }
});
$("evaluate").addEventListener("click", async () => {
  busy(true);
  $("eval-grid").replaceChildren();
  let passed = 0;
  const cases = [
    ["queue-pressure", "analysis", "verified", "queue_pressure"],
    ["long-context", "analysis", "verified", "prefill_pressure"],
    ["recovery", "analysis", "verified", "within_baseline"],
    ["client-early-close", "analysis", "verified", "insufficient_evidence"],
    ...[
      "file-access",
      "cross-scope",
      "fabricated-result",
      "caught-denial",
      "host-call-budget",
    ].map((c) => ["queue-pressure", c, "rejected", null]),
    ...["timeout", "memory"].map((c) => ["queue-pressure", c, "limited", null]),
    ["recovery", "analysis", "verified", "within_baseline"],
  ];
  try {
    for (const [scenario, challenge, expected, finding] of cases) {
      $("eval-summary").textContent = `Running ${scenario} / ${challenge}…`;
      const response = await requestRun({ scenario, challenge });
      const result = response.attempts.at(-1);
      const ok =
        result.status === expected &&
        (!finding || result.analysis?.finding === finding);
      if (ok) passed++;
      const row = text("div", "");
      row.append(
        text("span", challenge === "analysis" ? scenario : challenge),
        text("b", ok ? "PASS" : "FAIL", ok ? "pass" : "fail"),
      );
      $("eval-grid").append(row);
    }
    $("eval-summary").textContent =
      `${passed} / ${cases.length} passed. Scripted checks only; no model quality claim.`;
  } catch (error) {
    $("eval-summary").textContent = error.message;
  } finally {
    busy(false);
  }
});
busy(true);
fetch("/api/catalog")
  .then((response) => {
    if (!response.ok) throw new Error("Catalog unavailable");
    return response.json();
  })
  .then((data) => {
    catalog = data;
    resetCode();
    $("source").href = data.source;
    $("capture").textContent = data.capture_id;
    busy(false);
  })
  .catch((error) => {
    busy(true);
    $("status").textContent = error.message;
  });
