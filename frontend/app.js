const askBtn = document.getElementById("askBtn");
const baseUrlInput = document.getElementById("baseUrl");
const questionInput = document.getElementById("question");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const summaryEl = document.getElementById("summary");
const intentEl = document.getElementById("intent");
const strategyEl = document.getElementById("strategy");
const confidenceEl = document.getElementById("confidence");
const answerMarkdownEl = document.getElementById("answerMarkdown");
const citationsEl = document.getElementById("citations");
const citationFiltersEl = document.getElementById("citationFilters");
const bookCountEl = document.getElementById("bookCount");
const paperCountEl = document.getElementById("paperCount");
const webCountEl = document.getElementById("webCount");
const saveProfileBtn = document.getElementById("saveProfileBtn");
const copyPlanBtn = document.getElementById("copyPlanBtn");
const downloadPlanBtn = document.getElementById("downloadPlanBtn");
const weeklyChecksEl = document.getElementById("weeklyChecks");
const profileHeight = document.getElementById("profileHeight");
const profileWeight = document.getElementById("profileWeight");
const profileAge = document.getElementById("profileAge");
const profileGoal = document.getElementById("profileGoal");

let latestAnswerMarkdown = "";
let latestCitations = [];
let activeFilter = "all";
const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const PROFILE_KEY = "fitrag_profile_v1";
const WEEK_KEY = "fitrag_week_checks_v1";

if (window.location?.origin?.startsWith("http")) {
  baseUrlInput.value = window.location.origin;
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b91c1c" : "";
}

function badgeClass(sourceType) {
  const t = (sourceType || "unknown").toLowerCase();
  if (t === "book") return "book";
  if (t === "paper") return "paper";
  if (t === "website") return "website";
  return "unknown";
}

function updateSourceCounters(citations) {
  const counts = { book: 0, paper: 0, website: 0 };
  for (const c of citations || []) {
    const t = (c.source_type || "unknown").toLowerCase();
    if (counts[t] !== undefined) counts[t] += 1;
  }
  bookCountEl.textContent = counts.book;
  paperCountEl.textContent = counts.paper;
  webCountEl.textContent = counts.website;
}

function filteredCitations(citations) {
  if (activeFilter === "all") return citations || [];
  return (citations || []).filter((c) => (c.source_type || "unknown").toLowerCase() === activeFilter);
}

function renderCitations(citations) {
  const list = filteredCitations(citations);
  citationsEl.innerHTML = "";
  for (const c of list) {
    const card = document.createElement("div");
    card.className = "citation";
    card.innerHTML = `
      <div class="citation-head">
        <h3>[${c.id}] ${c.title}</h3>
        <span class="badge ${badgeClass(c.source_type)}">${(c.source_type || "unknown").toUpperCase()}</span>
      </div>
      <p>${c.section || ""} ${c.publish_date ? `· ${c.publish_date}` : ""}</p>
      <p>${c.authors || ""} ${c.venue ? `· ${c.venue}` : ""}</p>
      ${c.doi ? `<p>DOI: ${c.doi}</p>` : ""}
      <p>${c.snippet || ""}</p>
      ${c.url ? `<a href="${c.url}" target="_blank" rel="noreferrer">Open Source</a>` : ""}
    `;
    citationsEl.appendChild(card);
  }
  updateSourceCounters(citations);
}

function loadProfile() {
  try {
    const p = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
    profileHeight.value = p.height || "";
    profileWeight.value = p.weight || "";
    profileAge.value = p.age || "";
    profileGoal.value = p.goal || "";
  } catch {
    // ignore
  }
}

function saveProfile() {
  const payload = {
    height: profileHeight.value.trim(),
    weight: profileWeight.value.trim(),
    age: profileAge.value.trim(),
    goal: profileGoal.value.trim()
  };
  localStorage.setItem(PROFILE_KEY, JSON.stringify(payload));
  setStatus("Profile saved.");
}

function appendProfileContext(query) {
  try {
    const p = JSON.parse(localStorage.getItem(PROFILE_KEY) || "{}");
    const parts = [];
    if (p.height) parts.push(`height ${p.height} cm`);
    if (p.weight) parts.push(`weight ${p.weight} kg`);
    if (p.age) parts.push(`age ${p.age}`);
    if (p.goal) parts.push(`goal ${p.goal}`);
    if (parts.length === 0) return query;
    return `${query}\n\nProfile context: ${parts.join(", ")}.`;
  } catch {
    return query;
  }
}

function copyPlan() {
  if (!latestAnswerMarkdown) {
    setStatus("No plan to copy yet.", true);
    return;
  }
  navigator.clipboard.writeText(latestAnswerMarkdown).then(
    () => setStatus("Plan copied to clipboard."),
    () => setStatus("Copy failed.", true)
  );
}

function downloadPlan() {
  if (!latestAnswerMarkdown) {
    setStatus("No plan to download yet.", true);
    return;
  }
  const blob = new Blob([latestAnswerMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "fitrag-plan.md";
  a.click();
  URL.revokeObjectURL(url);
  setStatus("Plan downloaded.");
}

function loadWeeklyChecks() {
  let done = [];
  try {
    done = JSON.parse(localStorage.getItem(WEEK_KEY) || "[]");
    if (!Array.isArray(done)) done = [];
  } catch {
    done = [];
  }
  weeklyChecksEl.innerHTML = "";
  weekDays.forEach((d, i) => {
    const btn = document.createElement("button");
    btn.className = "week-day" + (done.includes(i) ? " done" : "");
    btn.textContent = d;
    btn.addEventListener("click", () => {
      const set = new Set(done);
      if (set.has(i)) set.delete(i);
      else set.add(i);
      done = Array.from(set).sort((a, b) => a - b);
      localStorage.setItem(WEEK_KEY, JSON.stringify(done));
      loadWeeklyChecks();
    });
    weeklyChecksEl.appendChild(btn);
  });
}

async function runQuery() {
  const baseUrl = baseUrlInput.value.trim().replace(/\/+$/, "");
  const queryRaw = questionInput.value.trim();
  if (!queryRaw) {
    setStatus("Please enter a question.", true);
    return;
  }

  const query = appendProfileContext(queryRaw);

  askBtn.disabled = true;
  setStatus("Generating...");
  resultEl.classList.add("hidden");

  try {
    const resp = await fetch(`${baseUrl}/chat/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: "web-demo-session",
        query,
        top_k_context_turns: 6,
        top_k_retrieval: 6,
        max_sub_queries: 3
      })
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`API ${resp.status}: ${text}`);
    }

    const data = await resp.json();
    const generated = data.generated_answer || {};

    latestAnswerMarkdown = generated.answer_markdown || "";
    latestCitations = generated.citations || [];
    activeFilter = "all";
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    document.querySelector('.filter-btn[data-filter="all"]')?.classList.add("active");
    citationFiltersEl.classList.remove("hidden");

    summaryEl.textContent = generated.summary || "No summary.";
    intentEl.textContent = data.preprocess?.intent || "-";
    strategyEl.textContent = data.adaptive_plan?.strategy || "-";
    confidenceEl.textContent = generated.confidence ?? "-";
    answerMarkdownEl.textContent = latestAnswerMarkdown;
    renderCitations(latestCitations);

    resultEl.classList.remove("hidden");
    setStatus("Done.");
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    askBtn.disabled = false;
  }
}

askBtn.addEventListener("click", runQuery);
saveProfileBtn.addEventListener("click", saveProfile);
copyPlanBtn.addEventListener("click", copyPlan);
downloadPlanBtn.addEventListener("click", downloadPlan);

for (const chip of document.querySelectorAll(".chip")) {
  chip.addEventListener("click", () => {
    questionInput.value = chip.getAttribute("data-q") || "";
    questionInput.focus();
  });
}

for (const btn of document.querySelectorAll(".filter-btn")) {
  btn.addEventListener("click", () => {
    activeFilter = btn.getAttribute("data-filter") || "all";
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderCitations(latestCitations);
  });
}

loadProfile();
loadWeeklyChecks();

