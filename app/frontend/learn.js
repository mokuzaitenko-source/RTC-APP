const COACH_STORAGE_KEY = "rtc_coach_state_v1";
const COACH_SESSION_KEY = "rtc_coach_session_v1";
const MAX_MESSAGES = 120;

const COACH_CONTEXT = [
  "You are my software engineering career coach.",
  "Be direct, practical, and numbers-first.",
  "Prioritize simple systems that are good enough today and evolve with measured demand.",
  "Use short checklists and concrete acceptance criteria.",
  "Focus on helping me get hired with portfolio evidence and interview readiness.",
].join(" ");

const state = {
  busy: false,
  session_id: "",
  focus: "job_search",
  asks: 0,
  useful: 0,
  checklist: {},
  messages: [],
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function setStatus(text) {
  const status = document.getElementById("coachStatus");
  if (status) {
    status.textContent = text;
  }
}

function generateSessionId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `coach_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function ensureSessionId() {
  const existing = localStorage.getItem(COACH_SESSION_KEY);
  if (existing && existing.trim()) {
    state.session_id = existing.trim();
    return;
  }
  const created = generateSessionId();
  state.session_id = created;
  localStorage.setItem(COACH_SESSION_KEY, created);
}

function loadState() {
  ensureSessionId();
  try {
    const raw = localStorage.getItem(COACH_STORAGE_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw);
    state.focus = typeof parsed.focus === "string" ? parsed.focus : "job_search";
    state.asks = Number.isFinite(parsed.asks) ? Math.max(0, parsed.asks) : 0;
    state.useful = Number.isFinite(parsed.useful) ? Math.max(0, parsed.useful) : 0;
    state.checklist = parsed.checklist && typeof parsed.checklist === "object" ? parsed.checklist : {};
    state.messages = Array.isArray(parsed.messages)
      ? parsed.messages
          .filter(item => item && typeof item === "object")
          .map(item => ({
            role: item.role === "user" ? "user" : "assistant",
            text: String(item.text || "").trim(),
          }))
          .filter(item => Boolean(item.text))
          .slice(-MAX_MESSAGES)
      : [];
  } catch (_error) {
    state.focus = "job_search";
    state.asks = 0;
    state.useful = 0;
    state.checklist = {};
    state.messages = [];
  }
}

function persistState() {
  const payload = {
    focus: state.focus,
    asks: state.asks,
    useful: state.useful,
    checklist: state.checklist,
    messages: state.messages.slice(-MAX_MESSAGES),
  };
  localStorage.setItem(COACH_STORAGE_KEY, JSON.stringify(payload));
}

function renderMetrics() {
  const asks = document.getElementById("metricAsks");
  const useful = document.getElementById("metricUseful");
  if (asks) {
    asks.textContent = String(state.asks);
  }
  if (useful) {
    useful.textContent = String(state.useful);
  }
}

function renderChecklist() {
  document.querySelectorAll("input[data-role='coach-check']").forEach(input => {
    const id = input.getAttribute("data-check-id") || "";
    input.checked = Boolean(state.checklist[id]);
  });
}

function renderThread() {
  const thread = document.getElementById("coachThread");
  if (!thread) {
    return;
  }
  if (!state.messages.length) {
    thread.innerHTML = `
      <div class="empty">
        Start here: ask for a 90-minute learning block, then execute it and return with your results.
      </div>
    `;
    return;
  }
  thread.innerHTML = state.messages
    .map(
      message => `
        <article class="row ${message.role === "user" ? "user" : "assistant"}">
          <div class="bubble">
            <p class="role">${message.role === "user" ? "You" : "Coach"}</p>
            <p class="text">${escapeHtml(message.text)}</p>
          </div>
        </article>
      `
    )
    .join("");
  thread.scrollTop = thread.scrollHeight;
}

function pushMessage(role, text) {
  const cleaned = String(text || "").trim();
  if (!cleaned) {
    return;
  }
  state.messages.push({
    role: role === "user" ? "user" : "assistant",
    text: cleaned,
  });
  state.messages = state.messages.slice(-MAX_MESSAGES);
  persistState();
  renderThread();
}

function recentContext(limit = 10) {
  const turns = state.messages.slice(-limit);
  if (!turns.length) {
    return "";
  }
  return turns.map(turn => `${turn.role}: ${turn.text}`).join("\n");
}

function coachFocusHint() {
  const focus = state.focus;
  if (focus === "project_impact") {
    return "Focus on measurable business impact and portfolio storytelling.";
  }
  if (focus === "backend_skills") {
    return "Focus on API design, testing, reliability, and debugging depth.";
  }
  if (focus === "frontend_skills") {
    return "Focus on UI quality, accessibility, and interaction reliability.";
  }
  if (focus === "system_design") {
    return "Focus on simple architecture, scaling triggers, and tradeoff clarity.";
  }
  if (focus === "interview_prep") {
    return "Focus on mock interviews, STAR stories, and communication quality.";
  }
  return "Focus on job search execution, applications, and daily consistency.";
}

function buildPayload(prompt) {
  const context = [COACH_CONTEXT, coachFocusHint(), `Recent context:\n${recentContext() || "(none)"}`].join("\n\n");
  return {
    user_input: prompt,
    context,
    risk_tolerance: "medium",
    max_questions: 1,
  };
}

async function apiJSON(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": state.session_id,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload?.error?.message || `Request failed: ${response.status}`);
  }
  return payload;
}

function setBusy(busy) {
  state.busy = busy;
  document.querySelectorAll("button").forEach(button => {
    if (busy) {
      button.setAttribute("disabled", "disabled");
    } else {
      button.removeAttribute("disabled");
    }
  });
}

async function askCoach(promptOverride) {
  const input = document.getElementById("coachInput");
  if (!input) {
    return;
  }
  const prompt = typeof promptOverride === "string" ? promptOverride.trim() : input.value.trim();
  if (!prompt) {
    throw new Error("Type a question before asking.");
  }

  pushMessage("user", prompt);
  input.value = "";
  state.asks += 1;
  persistState();
  renderMetrics();
  setStatus("Coach is thinking...");
  setBusy(true);

  try {
    const payload = buildPayload(prompt);
    const response = await apiJSON("POST", "/api/assistant/respond", payload);
    const assistant = response?.data?.assistant || {};
    const reply = String(assistant.candidate_response || "").trim() || "No response returned.";
    pushMessage("assistant", reply);
    setStatus("Ready. Mark useful if this helped, then ask follow-up.");
  } finally {
    setBusy(false);
  }
}

function markUseful() {
  state.useful += 1;
  persistState();
  renderMetrics();
  setStatus("Logged. Keep building evidence and measurable progress.");
}

function clearChat() {
  state.messages = [];
  persistState();
  renderThread();
  setStatus("Chat cleared. Ask for your next learning block.");
}

function wire() {
  const form = document.getElementById("coachForm");
  if (form) {
    form.addEventListener("submit", event => {
      event.preventDefault();
      askCoach().catch(error => setStatus(`Error: ${error.message}`));
    });
    form.addEventListener("click", event => {
      const button = event.target.closest("button[data-role='coach-prompt']");
      if (!button) {
        return;
      }
      const prompt = button.getAttribute("data-prompt") || "";
      askCoach(prompt).catch(error => setStatus(`Error: ${error.message}`));
    });
  }

  const clear = document.getElementById("coachClear");
  if (clear) {
    clear.addEventListener("click", clearChat);
  }

  const useful = document.getElementById("markUseful");
  if (useful) {
    useful.addEventListener("click", markUseful);
  }

  const focus = document.getElementById("coachFocus");
  if (focus) {
    focus.value = state.focus;
    focus.addEventListener("change", () => {
      state.focus = focus.value;
      persistState();
      setStatus(`Focus set to ${state.focus}. Ask for a targeted block.`);
    });
  }

  document.querySelectorAll("input[data-role='coach-check']").forEach(input => {
    input.addEventListener("change", () => {
      const id = input.getAttribute("data-check-id") || "";
      state.checklist[id] = input.checked;
      persistState();
    });
  });
}

function init() {
  loadState();
  renderMetrics();
  renderChecklist();
  renderThread();
  wire();
}

init();
