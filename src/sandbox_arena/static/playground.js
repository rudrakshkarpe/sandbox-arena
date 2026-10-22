const $ = (id) => document.getElementById(id);
const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const terminal = new Set(["completed", "cancelled", "failed", "interrupted"]);
const names = {
  playground: "Playground",
  benchmarks: "Benchmarks",
  history: "Run history",
  methodology: "Methodology",
};
const state = {
  catalog: null,
  record: null,
  records: {},
  busy: false,
  tab: "output",
  stream: null,
  selected: new Set(["primes-10", "primes-1000"]),
};
let toastTimer;

function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 6500);
}
async function api(path, options = {}) {
  const response = await fetch(`/api/playground${path}`, options);
  if (!response.ok) {
    let body;
    try {
      body = await response.json();
    } catch {
      body = {};
    }
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg).join("; ")
      : body.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json();
}
const post = (path, body = {}) =>
  api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
const ms = (value) => (value == null ? "—" : value.toFixed(3));
function navigate() {
  const view =
    location.hash.slice(1) in names ? location.hash.slice(1) : "playground";
  document.querySelectorAll(".view").forEach((el) => {
    el.hidden = el.id !== `view-${view}`;
  });
  document.querySelectorAll("[data-view]").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
    if (el.dataset.view === view) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  $("breadcrumb").textContent = names[view];
  document.title = `${names[view]} · Sandbox Arena`;
  if (view === "history")
    refreshHistory().catch((error) => toast(error.message));
  updatePolicy();
}
window.addEventListener("hashchange", navigate);

function editorChanged() {
  const code = $("code").value;
  $("line-numbers").textContent = Array.from(
    { length: code.split("\n").length },
    (_, i) => i + 1,
  ).join("\n");
  $("char-count").textContent = `${code.length.toLocaleString()} / 12,000`;
  $("example").value =
    state.catalog?.examples.find((example) => example.code === code)?.id ||
    "custom";
  try {
    localStorage.setItem("sandbox-arena-draft", code);
  } catch {
    /* Storage is optional. */
  }
}
$("code").addEventListener("input", editorChanged);
$("code").addEventListener("scroll", () => {
  $("line-numbers").scrollTop = $("code").scrollTop;
});
$("code").addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    const editor = $("code");
    editor.setRangeText(
      "    ",
      editor.selectionStart,
      editor.selectionEnd,
      "end",
    );
    editorChanged();
  }
});
$("example").addEventListener("change", () => {
  const example = state.catalog.examples.find(
    (item) => item.id === $("example").value,
  );
  if (example) {
    $("code").value = example.code;
    editorChanged();
  }
});
function policy() {
  return {
    timeout_ms: Number($("timeout").value),
    memory_mb: Number($("memory").value),
    allow_fixture: $("fixture").checked,
  };
}
function updatePolicy() {
  const spec = policy();
  $("timeout-label").textContent = `${spec.timeout_ms} ms`;
  $("suite-policy-label").textContent =
    `${spec.timeout_ms} ms · ${spec.memory_mb} MB · fixture ${spec.allow_fixture ? "allowed" : "denied"}`;
}
["timeout", "memory", "fixture"].forEach((id) =>
  $(id).addEventListener("input", updatePolicy),
);
function busy(value) {
  state.busy = value;
  $("run-code").disabled = value || !state.catalog;
  $("run-suite").disabled =
    value || !state.catalog || state.selected.size === 0;
  $("cancel").hidden = !value || state.record?.spec.mode !== "playground";
  $("suite-cancel").hidden = !value || state.record?.spec.mode !== "benchmark";
}
function acceptRecord(record) {
  if (
    state.record?.id === record.id &&
    state.record.events.length > record.events.length
  )
    return;
  state.record = record;
  state.records[record.spec.mode] = record;
  if (record.spec.mode === "benchmark") renderSuite();
  else renderResult();
}
async function launch(spec) {
  if (state.busy) return;
  busy(true);
  try {
    const { id } = await post("/runs", spec);
    state.record = null;
    acceptRecord(await api(`/runs/${id}`));
    busy(true);
    follow(id);
  } catch (error) {
    busy(false);
    toast(error.message);
  }
}
function follow(id) {
  state.stream?.close();
  const stream = new EventSource(`/api/playground/runs/${id}/events`);
  state.stream = stream;
  let failures = 0;
  stream.onmessage = async ({ data }) => {
    failures = 0;
    const event = JSON.parse(data);
    if (event.type === "trial_started")
      $("suite-progress").textContent = event.message;
    if (["trial_finished", "started", ...terminal].includes(event.type)) {
      try {
        acceptRecord(await api(`/runs/${id}`));
      } catch (error) {
        toast(error.message);
      }
    }
    if (terminal.has(event.type)) {
      stream.close();
      busy(false);
      refreshHistory().catch((error) => toast(error.message));
    }
  };
  stream.onerror = async () => {
    try {
      const record = await api(`/runs/${id}`);
      acceptRecord(record);
      if (terminal.has(record.status)) {
        stream.close();
        busy(false);
      }
    } catch {
      failures += 1;
      if (failures >= 3) {
        stream.close();
        busy(false);
        toast(
          "Connection lost. The run may still be executing. Check Run history after reconnecting.",
        );
      }
    }
  };
}
$("run-code").addEventListener("click", () =>
  launch({ mode: "playground", code: $("code").value, ...policy() }),
);
document.addEventListener("keydown", (event) => {
  if (
    (event.metaKey || event.ctrlKey) &&
    event.key === "Enter" &&
    !$("view-playground").hidden
  ) {
    event.preventDefault();
    if (!state.busy && state.catalog) $("run-code").click();
  }
});
$("run-suite").addEventListener("click", () => {
  if (!$("iterations").reportValidity() || !$("warmups").reportValidity())
    return;
  launch({
    mode: "benchmark",
    benchmark_ids: [...state.selected],
    iterations: Number($("iterations").value),
    warmups: Number($("warmups").value),
    ...policy(),
  });
});
async function cancel() {
  if (!state.record) return;
  try {
    const result = await post(`/runs/${state.record.id}/cancel`);
    toast(result.message);
  } catch (error) {
    toast(error.message);
  }
}
$("cancel").addEventListener("click", cancel);
$("suite-cancel").addEventListener("click", cancel);

document.querySelectorAll("[data-result-tab]").forEach((button) =>
  button.addEventListener("click", () => {
    state.tab = button.dataset.resultTab;
    document
      .querySelectorAll("[data-result-tab]")
      .forEach((tab) =>
        tab.setAttribute("aria-selected", String(tab === button)),
      );
    renderResult();
  }),
);
function renderResult() {
  const record = state.records.playground;
  if (!record || record.spec.mode !== "playground") return;
  $("run-status").textContent = record.status;
  $("export").hidden = false;
  $("export").href = `/api/playground/runs/${record.id}/export`;
  const sample = record.samples.at(-1);
  $("metrics").hidden = !sample;
  if (sample) {
    $("run-status").textContent =
      record.status === "completed" ? sample.status : record.status;
    $("metrics").innerHTML = [
      ["Setup", sample.setup_ms],
      ["Execution", sample.execution_ms],
      ["Cleanup", sample.cleanup_ms],
      ["Total", sample.total_ms],
    ]
      .map(
        ([label, value]) =>
          `<div class="metric"><span>${label}</span><strong>${ms(value)} <small>ms</small></strong></div>`,
      )
      .join("");
  }
  if (state.tab === "events") {
    $("result-content").innerHTML = record.events
      .map(
        (event) =>
          `<div class="event-row"><span class="event-index">${String(event.id).padStart(2, "0")}</span><time>${escape(event.at ? new Date(event.at).toLocaleTimeString() : "")}</time><span>${escape(event.message)}</span></div>`,
      )
      .join("");
  } else if (state.tab === "policy") {
    $("result-content").innerHTML = sample?.audit.length
      ? sample.audit
          .map(
            (event) =>
              `<div class="event-row"><span class="${event.allowed ? "pass" : "fail"}">${event.allowed ? "ALLOWED" : "DENIED"}</span><span>${escape(event.operation)}</span><span class="muted">${escape(event.layer)}</span></div>`,
          )
          .join("")
      : '<div class="empty-state"><div><strong>No host operations recorded.</strong><p>Try the approved tool or filesystem boundary example to inspect a policy decision.</p></div></div>';
  } else if (sample) {
    $("result-content").innerHTML =
      `${sample.error ? `<div class="output-label">${escape(sample.status)}</div><pre class="output-error">${escape(sample.error)}</pre>` : ""}${sample.stdout ? `<div class="output-label">STANDARD OUTPUT · CAPPED AT 4 KiB</div><pre>${escape(sample.stdout)}</pre>` : ""}<div class="output-label">RETURN VALUE${sample.result_truncated ? " · TRUNCATED" : ""}</div><pre>${escape(JSON.stringify(sample.result, null, 2))}</pre><div class="field-hint">Custom code output is observed, not independently verified. Session discarded after execution.</div>`;
  } else {
    $("result-content").innerHTML =
      `<div class="empty-state"><span class="empty-icon">⌁</span><div><strong>${escape(record.status === "failed" ? "The runner could not complete this job." : "Preparing your isolated session…")}</strong><p>Inspect the timeline for execution events.</p></div></div>`;
  }
}
function renderBenchmarks() {
  $("benchmark-list").innerHTML = state.catalog.benchmarks
    .map(
      (workload) =>
        `<article class="benchmark-card"><input type="checkbox" id="benchmark-${escape(workload.id)}" data-workload="${escape(workload.id)}" ${state.selected.has(workload.id) ? "checked" : ""}><div><label for="benchmark-${escape(workload.id)}"><h2>${escape(workload.name)}</h2></label><p>${escape(workload.description)}</p><details><summary>Inspect workload & provenance</summary><pre>${escape(workload.code)}</pre><p>Version ${escape(workload.version)} · Expected outcome: ${escape(workload.expected_status)}${workload.source ? `<br>Adapted from <a href="${escape(workload.source)}" target="_blank" rel="noreferrer">pinned upstream source ↗</a>. Timer wrappers removed; structured results added. Apache-2.0.` : "<br>Authored for Sandbox Arena."}</p></details></div><span class="category">${escape(workload.category)}</span></article>`,
    )
    .join("");
  document.querySelectorAll("[data-workload]").forEach((input) =>
    input.addEventListener("change", () => {
      if (input.checked) state.selected.add(input.dataset.workload);
      else state.selected.delete(input.dataset.workload);
      busy(state.busy);
    }),
  );
}
function workloadName(id) {
  return state.catalog?.benchmarks.find((w) => w.id === id)?.name || id;
}
function renderSuite() {
  const record = state.records.benchmark;
  if (!record || record.spec.mode !== "benchmark") return;
  $("benchmark-results").hidden = false;
  $("suite-status").textContent = record.status;
  $("suite-export").href = `/api/playground/runs/${record.id}/export`;
  const measured = record.samples.filter((s) => !s.warmup).length;
  const target = record.spec.iterations * record.spec.benchmark_ids.length;
  $("suite-progress").textContent =
    `${measured} / ${target} measured trials · ${record.samples.filter((s) => s.warmup).length} warmups · ${record.status}`;
  $("summary-table").innerHTML =
    "<table><thead><tr><th>Workload</th><th>Checks</th><th>Median</th><th>P95</th><th>Range (ms)</th></tr></thead><tbody>" +
    record.summaries
      .map(
        (row) =>
          `<tr><td>${escape(workloadName(row.workload_id))}</td><td class="numeric ${row.failed ? "fail" : "pass"}">${row.passed}/${row.samples}</td><td class="numeric">${ms(row.median_ms)} ms</td><td class="numeric">${row.p95_ms == null ? "—" : ms(row.p95_ms) + " ms"}</td><td class="numeric">${ms(row.min_ms)} – ${ms(row.max_ms)}</td></tr>`,
      )
      .join("") +
    "</tbody></table>";
  $("sample-chart").innerHTML = record.summaries
    .map((row) => {
      const samples = record.samples.filter(
        (s) => s.workload_id === row.workload_id && !s.warmup,
      );
      const max = Math.max(...samples.map((s) => s.execution_ms), 0.001);
      const points = samples.map((s, i) => [
        12 + (samples.length > 1 ? i / (samples.length - 1) : 0.5) * 576,
        67 - (s.execution_ms / max) * 54,
      ]);
      return `<div class="sample-series"><div class="sample-series-label"><span>${escape(workloadName(row.workload_id))}</span><span>0 – ${ms(max)} ms</span></div><svg viewBox="0 0 600 80" preserveAspectRatio="none" role="img" aria-label="${escape(workloadName(row.workload_id))} execution timings"><path class="chart-grid" d="M0 67H600 M0 40H600 M0 13H600"/><polyline class="chart-line" points="${points.map((p) => p.join(",")).join(" ")}"/>${points.map((p, i) => `<circle class="chart-dot" cx="${p[0]}" cy="${p[1]}" r="2.5"><title>Trial ${i + 1}: ${ms(samples[i].execution_ms)} ms · ${samples[i].verdict}</title></circle>`).join("")}</svg></div>`;
    })
    .join("");
}
async function refreshHistory() {
  const runs = await api("/runs");
  $("history-count").textContent = runs.length;
  $("history-list").innerHTML = runs.length
    ? runs
        .map(
          (run) =>
            `<div class="history-row"><div><strong>${run.spec.mode === "benchmark" ? `${run.spec.benchmark_ids.length} benchmark${run.spec.benchmark_ids.length > 1 ? "s" : ""}` : "Playground execution"}</strong><small>${escape(run.id.slice(0, 12))} · Monty</small></div><span>${escape(new Date(run.created_at).toLocaleString())}</span><span class="tag">${escape(run.status)}</span><button data-open-run="${escape(run.id)}">Inspect ↗</button></div>`,
        )
        .join("")
    : '<div class="result-content"><div class="empty-state"><span class="empty-icon">◷</span><div><strong>A clean slate.</strong><p>Your first run will appear here with its configuration and evidence.</p></div></div></div>';
  document.querySelectorAll("[data-open-run]").forEach((button) =>
    button.addEventListener("click", async () => {
      if (state.busy) {
        toast("Finish or stop the current run before opening another record.");
        return;
      }
      try {
        const record = await api(`/runs/${button.dataset.openRun}`);
        state.record = null;
        $("timeout").value = record.spec.timeout_ms;
        $("memory").value = record.spec.memory_mb;
        $("fixture").checked = record.spec.allow_fixture;
        updatePolicy();
        if (record.spec.mode === "playground") {
          $("code").value = record.spec.code;
          editorChanged();
          location.hash = "playground";
        } else {
          state.selected = new Set(record.spec.benchmark_ids);
          renderBenchmarks();
          $("iterations").value = record.spec.iterations;
          $("warmups").value = record.spec.warmups;
          location.hash = "benchmarks";
        }
        acceptRecord(record);
        busy(!terminal.has(record.status));
        if (!terminal.has(record.status)) follow(record.id);
      } catch (error) {
        toast(error.message);
      }
    }),
  );
}
$("refresh-history").addEventListener("click", () =>
  refreshHistory().catch((error) => toast(error.message)),
);

async function init() {
  navigate();
  try {
    state.catalog = await api("/catalog");
    $("runtime-version").textContent = `v${state.catalog.provider.version}`;
    $("runtime-status").innerHTML = '<span class="dot"></span> Ready';
    $("suite-count").textContent = state.catalog.benchmarks.length;
    $("example").innerHTML =
      '<option value="custom">Custom / saved draft</option>' +
      state.catalog.examples
        .map(
          (example) =>
            `<option value="${escape(example.id)}">${escape(example.name)}</option>`,
        )
        .join("");
    let draft;
    try {
      draft = localStorage.getItem("sandbox-arena-draft");
    } catch {
      /* Storage is optional. */
    }
    $("code").value = draft ?? state.catalog.examples[0].code;
    editorChanged();
    renderBenchmarks();
    busy(false);
    await refreshHistory();
  } catch (error) {
    $("connection-error").hidden = false;
    $("connection-error").textContent =
      `Could not connect to the local runner: ${error.message}. Start the server and reload this page.`;
    $("runtime-status").textContent = "Unavailable";
  }
}
init();
