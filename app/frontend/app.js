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
    model: "",
    models: []
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
      state.chat.model = typeof parsed.chat.model === "string" ? parsed.chat.model : "";
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
    state.chat.model = "";
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
      model: state.chat.model
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
  persistState();
  applyModelOptions();
}

function buildRequestPayload(prompt) {
  const context = recentContextText();
  return {
    user_input: prompt,
    context,
    risk_tolerance: state.chat.risk_tolerance,
    max_questions: 2,
    model: state.chat.model || undefined
  };
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
  const response = await apiJSON("POST", "/api/assistant/respond", payload);
  const sessionId = response?.data?.session_id;
  if (typeof sessionId === "string" && sessionId.trim()) {
    updateSessionId(sessionId);
  }
  return response?.data?.assistant || null;
}

async function runStream(payload) {
  const response = await fetch("/api/assistant/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": state.chat.session_id
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

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    while (true) {
      const boundary = buffer.indexOf("\n\n");
      if (boundary === -1) {
        break;
      }
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
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
        continue;
      }
      if (event === "error") {
        throw new Error(data?.message || "Assistant stream failed.");
      }
    }
  }

  if (!donePayload) {
    throw new Error("Assistant stream ended without done event.");
  }

  const sessionId = donePayload?.session_id;
  if (typeof sessionId === "string" && sessionId.trim()) {
    updateSessionId(sessionId);
  }
  return donePayload?.assistant || null;
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
  persistState();

  const payload = buildRequestPayload(prompt);
  state.chat.pending = "";
  renderChat();

  let assistant = null;
  try {
    assistant = await runStream(payload);
  } catch (_streamError) {
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
  applyHelpVisibility();
  updateHelpChecklistUi();
  if (!state.welcomeSeen) {
    setWelcomeOpen(true);
  }
  await runWithBusy("Loading model catalog...", loadModels);
}

init().catch(handleError);
