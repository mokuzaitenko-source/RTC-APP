const STORAGE_KEY = "oversight_assistant_state_v4";
const SESSION_STORAGE_KEY = "oversight_assistant_session_id_v1";
const MAX_MESSAGES = 80;

const HELP_JUMP_TARGETS = {
  "quick-start": "helpSectionQuickStart",
  "core-workflow": "helpSectionCoreWorkflow",
  "button-usage": "helpSectionButtonUsage",
  troubleshooting: "helpSectionTroubleshooting"
};

const state = {
  busy: false,
  helpOpen: false,
  welcomeOpen: false,
  helpReturnFocusId: null,
  welcomeSeen: false,
  chat: {
    session_id: "",
    messages: [],
    pending: "",
    risk_tolerance: "medium",
    api_version: "v1",
    output_format: "default",
    model: "",
    models: [],
    aca_trace_enabled: true,
    last_trace: [],
    provider_status: {
      provider_mode: "",
      effective_provider_mode: "",
      provider_ready: true,
      provider_warnings: []
    }
  },
  help: {
    checklist_progress: {},
    last_opened_section: "quick-start",
    hide_advanced: false
  }
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
  const badge = document.getElementById("assistantApiBadge");
  if (badge) {
    badge.textContent = `API ${state.chat.api_version.toUpperCase()}`;
  }
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
  const configured = String(status.provider_mode || "").trim();
  const effective = String(status.effective_provider_mode || configured || "unknown").trim();
  const ready = status.provider_ready !== false;
  const warnings = Array.isArray(status.provider_warnings) ? status.provider_warnings : [];
  const label = configured && configured !== effective ? `${effective} (${configured})` : effective;
  badge.textContent = `Provider: ${label || "unknown"}`;
  badge.classList.toggle("warning", !ready);
  badge.classList.toggle("ok", ready);
  if (!ready && warnings.length) {
    badge.title = warnings.join(" ");
  } else {
    badge.removeAttribute("title");
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
          created_at: String(item.created_at || "")
        }))
        .filter(item => Boolean(item.text))
        .slice(-MAX_MESSAGES);
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
      state.chat.aca_trace_enabled = true;
      state.chat.last_trace = Array.isArray(parsed.chat.last_trace) ? parsed.chat.last_trace : [];
    }
    if (parsed.help && typeof parsed.help === "object") {
      state.help.checklist_progress = typeof parsed.help.checklist_progress === "object" && parsed.help.checklist_progress
        ? parsed.help.checklist_progress
        : {};
      state.help.last_opened_section = typeof parsed.help.last_opened_section === "string"
        ? parsed.help.last_opened_section
        : "quick-start";
      state.help.hide_advanced = Boolean(parsed.help.hide_advanced);
    }
    state.welcomeSeen = Boolean(parsed.welcomeSeen);
  } catch (_error) {
    state.chat.messages = [];
    state.chat.risk_tolerance = "medium";
    state.chat.api_version = "v1";
    state.chat.output_format = "default";
    state.chat.model = "";
    state.chat.aca_trace_enabled = true;
    state.chat.last_trace = [];
    state.help = {
      checklist_progress: {},
      last_opened_section: "quick-start",
      hide_advanced: false
    };
    state.welcomeSeen = false;
  }
}

function persistState() {
  const payload = {
    chat: {
      messages: state.chat.messages,
      risk_tolerance: state.chat.risk_tolerance,
      api_version: state.chat.api_version,
      output_format: state.chat.output_format,
      model: state.chat.model,
      aca_trace_enabled: state.chat.aca_trace_enabled,
      last_trace: state.chat.last_trace
    },
    help: state.help,
    welcomeSeen: state.welcomeSeen
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
    items.push(`
      <article class="row ${message.role === "user" ? "user" : "assistant"}">
        <div class="bubble">
          <p class="role">${message.role === "user" ? "You" : "Assistant"}</p>
          <p class="text">${escapeHtml(message.text)}</p>
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

function pushMessage(role, text) {
  const cleaned = String(text || "").trim();
  if (!cleaned) {
    return;
  }
  state.chat.messages.push({
    role: role === "user" ? "user" : "assistant",
    text: cleaned,
    created_at: new Date().toISOString()
  });
  state.chat.messages = state.chat.messages.slice(-MAX_MESSAGES);
  persistState();
  renderChat();
}

function clearChat() {
  state.chat.messages = [];
  state.chat.pending = "";
  markChecklist("chat_clear", true);
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
  const userInput = formatHint ? `${prompt}\n\nOutput format requirement: ${formatHint}` : prompt;
  const payload = {
    user_input: userInput,
    context,
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
  markChecklist("chat_define_goal", true);
  markChecklist("chat_ask", true);
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

function markChecklist(checkId, value) {
  state.help.checklist_progress[checkId] = Boolean(value);
  persistState();
  updateHelpChecklistUi();
}

function updateHelpChecklistUi() {
  document.querySelectorAll("input[data-role='help-check']").forEach(input => {
    const checkId = input.getAttribute("data-check-id");
    input.checked = Boolean(state.help.checklist_progress[checkId]);
  });
}

function applyHelpVisibility() {
  const checklist = document.getElementById("helpChecklist");
  if (checklist) {
    checklist.hidden = state.help.hide_advanced;
  }
  const toggle = document.getElementById("helpHideAdvanced");
  if (toggle) {
    toggle.checked = state.help.hide_advanced;
  }
}

function jumpToHelpSection(sectionKey) {
  const sectionId = HELP_JUMP_TARGETS[sectionKey];
  if (!sectionId) {
    return;
  }
  const node = document.getElementById(sectionId);
  if (!node) {
    return;
  }
  node.scrollIntoView({ block: "start", behavior: "smooth" });
  state.help.last_opened_section = sectionKey;
  persistState();
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
    applyHelpVisibility();
    updateHelpChecklistUi();
    const sectionId = HELP_JUMP_TARGETS[state.help.last_opened_section] || HELP_JUMP_TARGETS["quick-start"];
    const section = document.getElementById(sectionId);
    if (section) {
      section.scrollIntoView({ block: "start", behavior: "smooth" });
    }
    const first = overlay.querySelector("[data-help-first]") || overlay.querySelector("button, input");
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

function setWelcomeOpen(open) {
  const overlay = document.getElementById("welcomeOverlay");
  if (!overlay) {
    return;
  }
  state.welcomeOpen = open;
  overlay.hidden = !open;
  if (open) {
    const start = document.getElementById("startWelcome");
    if (start) {
      start.focus();
    }
  }
}

async function runHelpAction(action) {
  const input = document.getElementById("chatInput");
  const risk = document.getElementById("chatRisk");

  if (action === "chat_define_goal") {
    if (input) {
      if (!input.value.trim()) {
        input.value = "I want to build a usable app. Give me a practical plan with milestones and acceptance criteria.";
      }
      input.focus();
    }
    markChecklist("chat_define_goal", true);
    return;
  }

  if (action === "chat_set_risk") {
    if (risk) {
      risk.focus();
    }
    markChecklist("chat_set_risk", true);
    return;
  }

  if (action === "chat_ask") {
    if (input && !input.value.trim()) {
      input.value = "Turn my goal into a 5-step execution plan with acceptance checks and fallback behavior.";
    }
    await askAssistant();
    markChecklist("chat_ask", true);
    return;
  }

  if (action === "chat_follow_up") {
    if (input) {
      input.value = "Refine your previous answer for lower risk and clearer acceptance checks.";
      input.focus();
    }
    markChecklist("chat_follow_up", true);
    return;
  }

  if (action === "chat_request_brief") {
    if (input) {
      input.value = "Create an implementation brief with scope, milestones, risks, and tests.";
      input.focus();
    }
    markChecklist("chat_request_brief", true);
    return;
  }

  if (action === "chat_clear") {
    clearChat();
    return;
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
  if (state.helpOpen) {
    setHelpOpen(false);
  }
  if (state.welcomeOpen) {
    setWelcomeOpen(false);
    state.welcomeSeen = true;
    persistState();
  }
}

function wire() {
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
    helpOverlay.addEventListener("change", event => {
      const input = event.target.closest("input[data-role]");
      if (!input) {
        return;
      }
      const role = input.getAttribute("data-role");
      if (role === "help-check") {
        const checkId = input.getAttribute("data-check-id");
        markChecklist(checkId, input.checked);
      }
      if (role === "toggle-hide-advanced") {
        state.help.hide_advanced = input.checked;
        persistState();
        applyHelpVisibility();
      }
    });
    const dialog = helpOverlay.querySelector(".dialog");
    if (dialog) {
      dialog.addEventListener("click", event => {
        const button = event.target.closest("button[data-role]");
        if (!button) {
          return;
        }
        const role = button.getAttribute("data-role");
        if (role === "help-jump") {
          jumpToHelpSection(button.getAttribute("data-help-section"));
          return;
        }
        if (role === "help-run") {
          runWithBusy("Running help action...", async () => runHelpAction(button.getAttribute("data-help-action")));
        }
      });
    }
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
      markChecklist("chat_set_risk", true);
      persistState();
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

  const closeWelcome = document.getElementById("closeWelcome");
  const startWelcome = document.getElementById("startWelcome");
  const dismissWelcome = () => {
    setWelcomeOpen(false);
    state.welcomeSeen = true;
    persistState();
  };

  if (closeWelcome) {
    closeWelcome.addEventListener("click", dismissWelcome);
  }
  if (startWelcome) {
    startWelcome.addEventListener("click", dismissWelcome);
  }

  const welcomeOverlay = document.getElementById("welcomeOverlay");
  if (welcomeOverlay) {
    welcomeOverlay.addEventListener("click", event => {
      if (event.target && event.target.id === "welcomeOverlay") {
        dismissWelcome();
      }
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
  applyHelpVisibility();
  updateHelpChecklistUi();
  if (!state.welcomeSeen) {
    setWelcomeOpen(true);
  }
  await runWithBusy("Loading model catalog...", loadModels);
}

init().catch(handleError);
