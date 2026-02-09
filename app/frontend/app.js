const STORAGE_KEY = "oversight_assistant_state_v4";
const SESSION_STORAGE_KEY = "oversight_assistant_session_id_v1";
const MAX_MESSAGES = 80;

const state = {
  busy: false,
  helpOpen: false,
  helpReturnFocusId: null,
  ui: {
    advanced_open: false
  },
  chat: {
    session_id: "",
    messages: [],
    pending: "",
    workflow_mode: "build",
    risk_tolerance: "medium",
    api_version: "v1",
    output_format: "default",
    model: "",
    models: [],
    aca_trace_enabled: false,
    last_trace: [],
    provider_status: {
      provider_mode: "",
      effective_provider_mode: "",
      provider_ready: true,
      provider_warnings: []
    }
  },
  help: {}
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function setStatus(text) {
  const node = document.getElementById("assistantStatusText");
  if (node) {
    node.textContent = text;
  }
}

function renderApiVersionUi() {
  const select = document.getElementById("chatApiVersion");
  if (select) {
    select.value = state.chat.api_version;
  }
}

function renderProviderStatus() {
  const badge = document.getElementById("assistantProviderBadge");
  if (!badge) {
    return;
  }
  const status = state.chat.provider_status || {};
  const effective = String(status.effective_provider_mode || status.provider_mode || "unknown").trim().toLowerCase();
  const ready = status.provider_ready !== false;
  const label = effective === "local" ? "Local" : "Cloud";
  badge.textContent = `Provider: ${label}`;
  badge.classList.toggle("warning", !ready);
  badge.classList.toggle("ok", ready);
  if (!ready) {
    badge.title = "Provider is not ready. Open Advanced to adjust mode/model.";
  } else {
    badge.removeAttribute("title");
  }
}

function renderWorkflowUi() {
  const workflow = state.chat.workflow_mode === "debug" ? "debug" : "build";
  const hasAssistantResponse = state.chat.messages.some(message => message.role === "assistant");

  const workflowSelect = document.getElementById("chatWorkflow");
  if (workflowSelect) {
    workflowSelect.value = workflow;
  }

  const input = document.getElementById("chatInput");
  if (input && !input.value.trim()) {
    if (workflow === "debug") {
      input.placeholder = "Issue: what is failing?\nExpected: what should happen?\nActual: what happens now?\nConstraints/Deadline: what must be respected?";
    } else {
      input.placeholder = "Goal: what do you want shipped?\nConstraints: scope/tools/time?\nDeadline: when does it need to be done?\nDone when: what result proves success?";
    }
  }

  const chipPrimary = document.getElementById("promptChipPrimary");
  const chipSecondary = document.getElementById("promptChipSecondary");

  if (workflow === "debug") {
    if (chipPrimary) {
      chipPrimary.textContent = "Debug now";
      chipPrimary.setAttribute(
        "data-prompt",
        "Debug this issue in strict format: 3 actions, 1 verification, 1 fallback."
      );
    }
    if (chipSecondary) {
      if (hasAssistantResponse) {
        chipSecondary.textContent = "Harden regression";
        chipSecondary.setAttribute(
          "data-prompt",
          "Refine your previous debug answer with stronger regression checks and a safer fallback, while keeping strict 3+1+1."
        );
      } else {
        chipSecondary.textContent = "Capture signals";
        chipSecondary.setAttribute(
          "data-prompt",
          "Give me the first debug signals to capture, then provide a strict 3+1+1 debug plan."
        );
      }
    }
  } else {
    if (chipPrimary) {
      chipPrimary.textContent = "Strict 3+1+1";
      chipPrimary.setAttribute(
        "data-prompt",
        "Turn this into a strict execution plan with 3 actions, 1 verification, and 1 fallback."
      );
    }
    if (chipSecondary) {
      if (hasAssistantResponse) {
        chipSecondary.textContent = "Refine previous";
        chipSecondary.setAttribute(
          "data-prompt",
          "Refine your previous answer to tighten acceptance checks and lower-risk fallback while keeping strict 3+1+1."
        );
      } else {
        chipSecondary.textContent = "Scope quickly";
        chipSecondary.setAttribute(
          "data-prompt",
          "Ask me one clarifying question if needed, then return a strict 3+1+1 plan."
        );
      }
    }
  }
}

function generateSessionId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `s_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function ensureSessionId() {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing && existing.trim()) {
    state.chat.session_id = existing.trim();
    return;
  }
  const created = generateSessionId();
  state.chat.session_id = created;
  localStorage.setItem(SESSION_STORAGE_KEY, created);
}

function updateSessionId(sessionId) {
  const cleaned = String(sessionId || "").trim();
  if (!cleaned) {
    return;
  }
  if (state.chat.session_id === cleaned) {
    return;
  }
  state.chat.session_id = cleaned;
  localStorage.setItem(SESSION_STORAGE_KEY, cleaned);
}

function loadState() {
  ensureSessionId();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw);
    if (parsed.chat && typeof parsed.chat === "object") {
      const messages = Array.isArray(parsed.chat.messages) ? parsed.chat.messages : [];
      state.chat.messages = messages
        .filter(item => item && typeof item === "object")
        .map(item => ({
          role: item.role === "user" ? "user" : "assistant",
          text: String(item.text || "").trim(),
          created_at: String(item.created_at || ""),
          message_id: String(item.message_id || ""),
          useful: item.useful === "yes" || item.useful === "no" ? item.useful : null
        }))
        .filter(item => Boolean(item.text))
        .slice(-MAX_MESSAGES);
      state.chat.workflow_mode = ["build", "debug"].includes(parsed.chat.workflow_mode)
        ? parsed.chat.workflow_mode
        : "build";
      state.chat.risk_tolerance = ["low", "medium", "high"].includes(parsed.chat.risk_tolerance)
        ? parsed.chat.risk_tolerance
        : "medium";
      state.chat.api_version = ["v1", "v2"].includes(parsed.chat.api_version)
        ? parsed.chat.api_version
        : "v1";
      state.chat.output_format = [
        "default",
        "concise_plan",
        "implementation_brief",
        "debugging_checklist"
      ].includes(parsed.chat.output_format)
        ? parsed.chat.output_format
        : "default";
      state.chat.model = typeof parsed.chat.model === "string" ? parsed.chat.model : "";
      state.chat.aca_trace_enabled = typeof parsed.chat.aca_trace_enabled === "boolean"
        ? parsed.chat.aca_trace_enabled
        : false;
      state.chat.last_trace = Array.isArray(parsed.chat.last_trace) ? parsed.chat.last_trace : [];
    }
    if (parsed.ui && typeof parsed.ui === "object") {
      state.ui.advanced_open = Boolean(parsed.ui.advanced_open);
    }
  } catch (_error) {
    state.chat.messages = [];
    state.chat.workflow_mode = "build";
    state.chat.risk_tolerance = "medium";
    state.chat.api_version = "v1";
    state.chat.output_format = "default";
    state.chat.model = "";
    state.chat.aca_trace_enabled = false;
    state.chat.last_trace = [];
    state.ui.advanced_open = false;
    state.help = {};
  }
}

function persistState() {
  const payload = {
    ui: state.ui,
    chat: {
      messages: state.chat.messages,
      workflow_mode: state.chat.workflow_mode,
      risk_tolerance: state.chat.risk_tolerance,
      api_version: state.chat.api_version,
      output_format: state.chat.output_format,
      model: state.chat.model,
      aca_trace_enabled: state.chat.aca_trace_enabled,
      last_trace: state.chat.last_trace
    }
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function syncBusyUi() {
  document.querySelectorAll("button").forEach(button => {
    const allowBusy = button.dataset.allowBusy === "true";
    if (state.busy && !allowBusy) {
      button.setAttribute("disabled", "disabled");
    } else {
      button.removeAttribute("disabled");
    }
  });
}

async function runWithBusy(label, fn) {
  if (state.busy) {
    return;
  }
  state.busy = true;
  setStatus(label);
  syncBusyUi();
  let ok = false;
  try {
    await fn();
    ok = true;
  } catch (error) {
    handleError(error);
  } finally {
    state.busy = false;
    syncBusyUi();
    if (ok) {
      setStatus("Ready.");
    }
  }
}

function renderChat() {
  const thread = document.getElementById("chatThread");
  if (!thread) {
    return;
  }
  const items = [];
  for (const message of state.chat.messages) {
    const messageId = escapeHtml(message.message_id || "");
    const usefulYesClass = message.useful === "yes" ? " active" : "";
    const usefulNoClass = message.useful === "no" ? " active" : "";
    const assistantActions = message.role === "assistant"
      ? `
      <div class="bubble-actions">
        <button type="button" class="mini-btn${usefulYesClass}" data-role="feedback" data-mid="${messageId}" data-value="yes">Useful</button>
        <button type="button" class="mini-btn${usefulNoClass}" data-role="feedback" data-mid="${messageId}" data-value="no">Needs work</button>
        <button type="button" class="mini-btn" data-role="refine" data-mid="${messageId}">Refine this</button>
      </div>
      `
      : "";
    items.push(`
      <article class="row ${message.role === "user" ? "user" : "assistant"}">
        <div class="bubble">
          <p class="role">${message.role === "user" ? "You" : "Assistant"}</p>
          <p class="text">${escapeHtml(message.text)}</p>
          ${assistantActions}
        </div>
      </article>
    `);
  }
  if (state.chat.pending) {
    items.push(`
      <article class="row assistant">
        <div class="bubble">
          <p class="role">Assistant</p>
          <p class="text">${escapeHtml(state.chat.pending)}<span class="streaming-caret" aria-hidden="true"></span></p>
        </div>
      </article>
    `);
  }
  if (!items.length) {
    thread.innerHTML = `
      <div class="empty">
        Start by describing what you want to build, fix, or plan.
        The assistant will stream a response and keep session context.
      </div>
    `;
  } else {
    thread.innerHTML = items.join("");
  }
  thread.scrollTop = thread.scrollHeight;

  const risk = document.getElementById("chatRisk");
  if (risk) {
    risk.value = state.chat.risk_tolerance;
  }
  const traceToggle = document.getElementById("chatTraceToggle");
  if (traceToggle) {
    traceToggle.checked = Boolean(state.chat.aca_trace_enabled);
  }
  const formatPreset = document.getElementById("chatFormatPreset");
  if (formatPreset) {
    formatPreset.value = state.chat.output_format;
  }
  renderApiVersionUi();
  renderWorkflowUi();
}

function renderTrace() {
  const panel = document.getElementById("acaTracePanel");
  const list = document.getElementById("acaTraceList");
  if (!panel || !list) {
    return;
  }
  const enabled = Boolean(state.chat.aca_trace_enabled);
  panel.hidden = !enabled;
  if (!enabled) {
    list.innerHTML = "";
    return;
  }
  const trace = Array.isArray(state.chat.last_trace) ? state.chat.last_trace : [];
  if (!trace.length) {
    list.innerHTML = `<li class="trace-item">No trace yet. Ask assistant with ACA Trace enabled.</li>`;
    return;
  }
  list.innerHTML = trace.map(item => {
    const moduleId = escapeHtml(item?.module_id || "?");
    const moduleName = escapeHtml(item?.module_name || "unknown");
    const status = escapeHtml(item?.status || "pass");
    const tier = escapeHtml(item?.tier || "tier3_operational");
    const detail = escapeHtml(item?.detail || "");
    return `
      <li class="trace-item">
        <div class="trace-meta">
          <span>${moduleId}</span>
          <span>${moduleName}</span>
          <span>${status}</span>
          <span>${tier}</span>
        </div>
        <div>${detail}</div>
      </li>
    `;
  }).join("");
}

function renderAdvancedDrawer() {
  const drawer = document.getElementById("assistantAdvancedDrawer");
  const toggle = document.getElementById("assistantAdvancedToggle");
  if (drawer) {
    drawer.hidden = !state.ui.advanced_open;
  }
  if (toggle) {
    toggle.setAttribute("aria-expanded", state.ui.advanced_open ? "true" : "false");
    toggle.textContent = "Settings";
  }
}

function pushMessage(role, text) {
  const cleaned = String(text || "").trim();
  if (!cleaned) {
    return;
  }
  const messageId = (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function")
    ? globalThis.crypto.randomUUID()
    : `m_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  state.chat.messages.push({
    role: role === "user" ? "user" : "assistant",
    text: cleaned,
    created_at: new Date().toISOString(),
    message_id: messageId,
    useful: null
  });
  state.chat.messages = state.chat.messages.slice(-MAX_MESSAGES);
  persistState();
  renderChat();
}

function setMessageFeedback(messageId, useful) {
  if (!messageId || (useful !== "yes" && useful !== "no")) {
    return;
  }
  let updated = false;
  state.chat.messages = state.chat.messages.map(message => {
    if (message.message_id !== messageId || message.role !== "assistant") {
      return message;
    }
    updated = true;
    return { ...message, useful };
  });
  if (updated) {
    persistState();
    renderChat();
    setStatus(useful === "yes" ? "Marked as useful." : "Marked as needs work.");
  }
}

function buildRefinePrompt(messageId) {
  const source = state.chat.messages.find(message => message.message_id === messageId && message.role === "assistant");
  const contextLine = source ? `Previous answer focus: ${source.text.split("\n")[0].slice(0, 120)}` : "Previous answer needs refinement.";
  return [
    "Refine your previous answer to be more actionable.",
    "Keep strict format: 3 actions + 1 verification + 1 fallback.",
    "Tighten acceptance checks and provide a safer fallback.",
    contextLine
  ].join(" ");
}

function clearChat() {
  state.chat.messages = [];
  state.chat.pending = "";
  persistState();
  renderChat();
  setStatus("Chat cleared.");
}

function recentContextText(limit = 12) {
  const turns = state.chat.messages.slice(-limit);
  if (!turns.length) {
    return "";
  }
  return turns.map(turn => `${turn.role}: ${turn.text}`).join("\n");
}

function presetInstruction() {
  if (state.chat.output_format === "concise_plan") {
    return "Return a concise 5-step plan with one acceptance check per step.";
  }
  if (state.chat.output_format === "implementation_brief") {
    return "Return an implementation brief with scope, milestones, risks, and tests.";
  }
  if (state.chat.output_format === "debugging_checklist") {
    return "Return a debugging checklist with hypotheses, checks, and expected signals.";
  }
  return "";
}

function workflowInstruction() {
  if (state.chat.workflow_mode === "debug") {
    return "Focus on debug execution: root-cause hypotheses, checks, expected signals, patch order, and regression tests.";
  }
  return "Focus on build execution: milestones, acceptance checks, dependencies, and fallback steps.";
}

function isV2AssistantPayload(payload) {
  return Boolean(payload && typeof payload === "object" && payload.aca_version === "4.1");
}

function normalizeAssistantPayload(payload) {
  if (isV2AssistantPayload(payload)) {
    return {
      mode: payload.mode === "clarify" ? "clarify" : "plan_execute",
      recommended_questions: Array.isArray(payload.recommended_questions) ? payload.recommended_questions : [],
      candidate_response: String(payload.final_message || ""),
      decision_graph: Array.isArray(payload.decision_graph) ? payload.decision_graph : [],
      module_outputs: payload.module_outputs && typeof payload.module_outputs === "object" ? payload.module_outputs : {},
      fallback: payload.fallback && typeof payload.fallback === "object" ? payload.fallback : {},
      safety: payload.safety && typeof payload.safety === "object" ? payload.safety : {},
      quality: payload.quality && typeof payload.quality === "object" ? payload.quality : {}
    };
  }
  return payload;
}

function formatAssistantMessage(assistant) {
  if (!assistant || typeof assistant !== "object") {
    return "No assistant output was returned.";
  }
  if (assistant.mode === "clarify") {
    const questions = Array.isArray(assistant.recommended_questions)
      ? assistant.recommended_questions
      : [];
    if (!questions.length) {
      return String(assistant.candidate_response || "I need clarification before proceeding.");
    }
    const lines = ["I need a few clarifications:"];
    questions.forEach((q, idx) => lines.push(`${idx + 1}. ${q}`));
    if (assistant.candidate_response) {
      lines.push("", String(assistant.candidate_response));
    }
    return lines.join("\n");
  }
  const plan = Array.isArray(assistant.plan) ? assistant.plan.map(item => String(item || "").trim()).filter(Boolean) : [];
  if (plan.length === 5) {
    const candidate = String(assistant.candidate_response || "").trim();
    const decision = candidate.split("\n").find(line => line.toLowerCase().startsWith("decision:")) || "Decision: Execute this plan.";
    return [
      decision,
      "",
      "Next actions:",
      `1. ${plan[0]}`,
      `2. ${plan[1]}`,
      `3. ${plan[2]}`,
      "",
      "Verification:",
      `4. ${plan[3]}`,
      "",
      "Fallback:",
      `5. ${plan[4]}`
    ].join("\n");
  }
  return String(assistant.candidate_response || "Plan generated.");
}

async function apiJSON(method, path, body, extraHeaders = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Session-ID": state.chat.session_id,
    ...(state.chat.aca_trace_enabled ? { "X-ACA-Trace": "1" } : {}),
    ...extraHeaders
  };
  const options = { method, headers };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload?.error?.message || `Request failed: ${response.status}`);
  }
  return payload;
}

function applyModelOptions() {
  const select = document.getElementById("chatModel");
  if (!select) {
    return;
  }
  const models = state.chat.models || [];
  select.innerHTML = models.map(model => `<option value="${escapeHtml(model)}">${escapeHtml(model)}</option>`).join("");
  if (state.chat.model && models.includes(state.chat.model)) {
    select.value = state.chat.model;
  } else if (models.length) {
    state.chat.model = models[0];
    select.value = state.chat.model;
    persistState();
  }
}

async function loadModels() {
  const payload = await apiJSON("GET", "/api/assistant/models");
  const data = payload?.data || {};
  const models = Array.isArray(data.models) ? data.models.filter(item => typeof item === "string" && item.trim()) : [];
  state.chat.models = models;
  if (!state.chat.model) {
    state.chat.model = typeof data.default_model === "string" ? data.default_model : "";
  }
  if (state.chat.model && !models.includes(state.chat.model) && models.length) {
    state.chat.model = models[0];
  }
  state.chat.provider_status = {
    provider_mode: String(data.provider_mode || "").trim(),
    effective_provider_mode: String(data.effective_provider_mode || "").trim(),
    provider_ready: data.provider_ready !== false,
    provider_warnings: Array.isArray(data.provider_warnings) ? data.provider_warnings : []
  };
  persistState();
  applyModelOptions();
  renderProviderStatus();
}

function buildRequestPayload(prompt) {
  const context = recentContextText();
  const formatHint = presetInstruction();
  const workflowHint = workflowInstruction();
  const contextParts = [];
  if (context) {
    contextParts.push(context);
  }
  if (workflowHint) {
    contextParts.push(`Workflow directive: ${workflowHint}`);
  }
  if (formatHint) {
    contextParts.push(`Output format requirement: ${formatHint}`);
  }
  const payload = {
    user_input: prompt,
    context: contextParts.length ? contextParts.join("\n\n") : undefined,
    risk_tolerance: state.chat.risk_tolerance,
    max_questions: 1,
    model: state.chat.model || undefined
  };
  if (state.chat.api_version === "v2") {
    payload.trace = Boolean(state.chat.aca_trace_enabled);
  }
  return payload;
}

function findSseBoundary(buffer) {
  const crlf = buffer.indexOf("\r\n\r\n");
  const lf = buffer.indexOf("\n\n");
  if (crlf === -1) {
    return { index: lf, length: 2 };
  }
  if (lf === -1) {
    return { index: crlf, length: 4 };
  }
  if (crlf < lf) {
    return { index: crlf, length: 4 };
  }
  return { index: lf, length: 2 };
}

function parseSseFrame(rawFrame) {
  const lines = rawFrame.split(/\r?\n/);
  let event = "message";
  const dataLines = [];
  for (const line of lines) {
    if (!line.trim()) {
      continue;
    }
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (!dataLines.length) {
    return null;
  }
  const text = dataLines.join("\n");
  let data;
  try {
    data = JSON.parse(text);
  } catch (_error) {
    data = { value: text };
  }
  return { event, data };
}

async function runFallbackRespond(payload) {
  const useV2 = state.chat.api_version === "v2";
  const endpoint = useV2 ? "/api/assistant/respond-v2" : "/api/assistant/respond";
  const response = await apiJSON("POST", endpoint, payload);
  const data = response?.data || {};

  if (useV2) {
    const sessionId = data?.session_id;
    if (typeof sessionId === "string" && sessionId.trim()) {
      updateSessionId(sessionId);
    }
    if (state.chat.aca_trace_enabled && Array.isArray(data?.trace)) {
      state.chat.last_trace = data.trace;
      persistState();
      renderTrace();
    }
    return normalizeAssistantPayload(data);
  }

  const sessionId = data?.session_id;
  if (typeof sessionId === "string" && sessionId.trim()) {
    updateSessionId(sessionId);
  }
  if (state.chat.aca_trace_enabled && Array.isArray(data?.aca_trace)) {
    state.chat.last_trace = data.aca_trace;
    persistState();
    renderTrace();
  }
  return normalizeAssistantPayload(data?.assistant || null);
}

async function runStream(payload) {
  const useV2 = state.chat.api_version === "v2";
  const endpoint = useV2 ? "/api/assistant/stream-v2" : "/api/assistant/stream";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": state.chat.session_id,
      ...(state.chat.aca_trace_enabled ? { "X-ACA-Trace": "1" } : {})
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload = null;
  let tracePayload = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    while (true) {
      const boundary = findSseBoundary(buffer);
      if (boundary.index === -1) {
        break;
      }
      const frame = buffer.slice(0, boundary.index);
      buffer = buffer.slice(boundary.index + boundary.length);
      const parsed = parseSseFrame(frame);
      if (!parsed) {
        continue;
      }
      const { event, data } = parsed;
      if (event === "meta") {
        if (data && typeof data.session_id === "string" && data.session_id.trim()) {
          updateSessionId(data.session_id);
        }
        continue;
      }
      if (event === "delta") {
        const text = typeof data?.text === "string" ? data.text : "";
        if (text) {
          state.chat.pending += text;
          renderChat();
        }
        continue;
      }
      if (event === "done") {
        donePayload = data;
        if (!useV2 && state.chat.aca_trace_enabled && Array.isArray(data?.aca_trace)) {
          tracePayload = data.aca_trace;
        }
        if (useV2 && state.chat.aca_trace_enabled && Array.isArray(data?.trace)) {
          tracePayload = data.trace;
        }
        continue;
      }
      if (event === "trace") {
        if (state.chat.aca_trace_enabled && data && typeof data === "object") {
          tracePayload.push(data);
        }
        continue;
      }
      if (event === "checkpoint") {
        if (state.chat.aca_trace_enabled && data && typeof data === "object") {
          tracePayload.push({
            module_id: data.module_id || "?",
            module_name: data.module_name || "checkpoint",
            status: data.status || "pass",
            tier: data.tier || "tier3_operational",
            detail: data.detail || "checkpoint",
            timestamp: new Date().toISOString()
          });
        }
        continue;
      }
      if (event === "error") {
        throw new Error(data?.message || "Assistant stream failed.");
      }
    }
  }

  if (!donePayload) {
    throw new Error("Assistant stream ended without done event. Falling back to non-stream response.");
  }

  const sessionId = useV2 ? donePayload?.session_id : donePayload?.session_id;
  if (typeof sessionId === "string" && sessionId.trim()) {
    updateSessionId(sessionId);
  }
  if (state.chat.aca_trace_enabled) {
    state.chat.last_trace = tracePayload;
    persistState();
    renderTrace();
  }
  if (useV2) {
    return normalizeAssistantPayload(donePayload);
  }
  return normalizeAssistantPayload(donePayload?.assistant || null);
}

async function askAssistant() {
  const input = document.getElementById("chatInput");
  if (!input) {
    return;
  }
  const prompt = input.value.trim();
  if (!prompt) {
    throw new Error("Type a message before asking the assistant.");
  }

  pushMessage("user", prompt);
  input.value = "";
  if (state.chat.aca_trace_enabled) {
    state.chat.last_trace = [];
    renderTrace();
  }
  persistState();

  const payload = buildRequestPayload(prompt);
  state.chat.pending = "";
  renderChat();

  let assistant = null;
  try {
    assistant = await runStream(payload);
  } catch (streamError) {
    setStatus(`Streaming degraded: ${streamError.message}`);
    assistant = await runFallbackRespond(payload);
  }

  state.chat.pending = "";
  renderChat();
  pushMessage("assistant", formatAssistantMessage(assistant));
}

function setHelpOpen(open) {
  const overlay = document.getElementById("helpOverlay");
  if (!overlay) {
    return;
  }
  state.helpOpen = open;
  overlay.hidden = !open;
  if (open) {
    const active = document.activeElement;
    state.helpReturnFocusId = active && active.id ? active.id : "assistantOpenHelp";
    const first = overlay.querySelector("button, input");
    if (first) {
      first.focus();
    }
  } else {
    const target = state.helpReturnFocusId ? document.getElementById(state.helpReturnFocusId) : null;
    const fallback = document.getElementById("assistantOpenHelp");
    if (target) {
      target.focus();
    } else if (fallback) {
      fallback.focus();
    }
  }
}

function handleError(error) {
  const message = error?.message || "Unknown error.";
  setStatus(`Error: ${message}`);
  state.chat.pending = "";
  renderChat();
  pushMessage("assistant", `I hit an error: ${message}`);
  renderTrace();
}

function onGlobalKeydown(event) {
  if (event.key !== "Escape") {
    return;
  }
  if (state.ui.advanced_open) {
    state.ui.advanced_open = false;
    persistState();
    renderAdvancedDrawer();
  }
  if (state.helpOpen) {
    setHelpOpen(false);
  }
}

function wire() {
  const assistantAdvancedToggle = document.getElementById("assistantAdvancedToggle");
  if (assistantAdvancedToggle) {
    assistantAdvancedToggle.addEventListener("click", () => {
      state.ui.advanced_open = !state.ui.advanced_open;
      persistState();
      renderAdvancedDrawer();
    });
  }

  const assistantOpenHelp = document.getElementById("assistantOpenHelp");
  if (assistantOpenHelp) {
    assistantOpenHelp.addEventListener("click", () => setHelpOpen(true));
  }

  const closeHelp = document.getElementById("closeHelp");
  if (closeHelp) {
    closeHelp.addEventListener("click", () => setHelpOpen(false));
  }

  const helpOverlay = document.getElementById("helpOverlay");
  if (helpOverlay) {
    helpOverlay.addEventListener("click", event => {
      if (event.target && event.target.id === "helpOverlay") {
        setHelpOpen(false);
      }
    });
  }

  const chatForm = document.getElementById("chatForm");
  if (chatForm) {
    chatForm.addEventListener("submit", event => {
      event.preventDefault();
      runWithBusy("Assistant is thinking...", askAssistant);
    });
    chatForm.addEventListener("click", event => {
      const button = event.target.closest("button[data-role='chat-prompt']");
      if (!button) {
        return;
      }
      const prompt = button.getAttribute("data-prompt") || "";
      const input = document.getElementById("chatInput");
      if (!input) {
        return;
      }
      input.value = prompt;
      input.focus();
    });
    const chatInput = document.getElementById("chatInput");
    if (chatInput) {
      chatInput.addEventListener("keydown", event => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
          event.preventDefault();
          runWithBusy("Assistant is thinking...", askAssistant);
        }
      });
    }
  }

  const chatThread = document.getElementById("chatThread");
  if (chatThread) {
    chatThread.addEventListener("click", event => {
      const button = event.target.closest("button[data-role]");
      if (!button) {
        return;
      }
      const role = button.getAttribute("data-role");
      const messageId = button.getAttribute("data-mid") || "";
      if (role === "feedback") {
        const value = button.getAttribute("data-value");
        setMessageFeedback(messageId, value === "yes" ? "yes" : "no");
        return;
      }
      if (role === "refine") {
        const input = document.getElementById("chatInput");
        if (!input) {
          return;
        }
        input.value = buildRefinePrompt(messageId);
        input.focus();
        runWithBusy("Refining response...", askAssistant);
      }
    });
  }

  const chatClear = document.getElementById("chatClear");
  if (chatClear) {
    chatClear.addEventListener("click", clearChat);
  }

  const risk = document.getElementById("chatRisk");
  if (risk) {
    risk.addEventListener("change", () => {
      const value = risk.value;
      state.chat.risk_tolerance = ["low", "medium", "high"].includes(value) ? value : "medium";
      persistState();
    });
  }

  const workflow = document.getElementById("chatWorkflow");
  if (workflow) {
    workflow.addEventListener("change", () => {
      const mode = workflow.value === "debug" ? "debug" : "build";
      state.chat.workflow_mode = mode;
      if (mode === "debug" && state.chat.output_format === "default") {
        state.chat.output_format = "debugging_checklist";
      } else if (mode === "build" && state.chat.output_format === "debugging_checklist") {
        state.chat.output_format = "default";
      }
      persistState();
      renderWorkflowUi();
      renderChat();
    });
  }

  const model = document.getElementById("chatModel");
  if (model) {
    model.addEventListener("change", () => {
      state.chat.model = model.value;
      persistState();
    });
  }

  const apiVersion = document.getElementById("chatApiVersion");
  if (apiVersion) {
    apiVersion.addEventListener("change", () => {
      state.chat.api_version = apiVersion.value === "v2" ? "v2" : "v1";
      persistState();
      renderApiVersionUi();
    });
  }

  const formatPreset = document.getElementById("chatFormatPreset");
  if (formatPreset) {
    formatPreset.addEventListener("change", () => {
      const allowed = ["default", "concise_plan", "implementation_brief", "debugging_checklist"];
      state.chat.output_format = allowed.includes(formatPreset.value)
        ? formatPreset.value
        : "default";
      persistState();
    });
  }

  const traceToggle = document.getElementById("chatTraceToggle");
  if (traceToggle) {
    traceToggle.addEventListener("change", () => {
      state.chat.aca_trace_enabled = traceToggle.checked;
      if (!state.chat.aca_trace_enabled) {
        state.chat.last_trace = [];
      }
      persistState();
      renderTrace();
    });
  }

  document.addEventListener("keydown", onGlobalKeydown);
}

async function init() {
  loadState();
  wire();
  syncBusyUi();
  renderChat();
  renderTrace();
  renderAdvancedDrawer();
  renderWorkflowUi();
  await runWithBusy("Loading model catalog...", loadModels);
}

init().catch(handleError);
