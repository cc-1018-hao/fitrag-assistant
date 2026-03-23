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

if (window.location?.origin?.startsWith("http")) {
  baseUrlInput.value = window.location.origin;
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b91c1c" : "";
}

function renderCitations(citations) {
  citationsEl.innerHTML = "";
  for (const c of citations || []) {
    const card = document.createElement("div");
    card.className = "citation";
    card.innerHTML = `
      <h3>[${c.id}] ${c.title}</h3>
      <p>${c.section || ""} ${c.publish_date ? `· ${c.publish_date}` : ""}</p>
      <p>${c.snippet || ""}</p>
      ${c.url ? `<a href="${c.url}" target="_blank" rel="noreferrer">Open Source</a>` : ""}
    `;
    citationsEl.appendChild(card);
  }
}

async function runQuery() {
  const baseUrl = baseUrlInput.value.trim().replace(/\/+$/, "");
  const query = questionInput.value.trim();
  if (!query) {
    setStatus("Please enter a question.", true);
    return;
  }

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
        top_k_retrieval: 5,
        max_sub_queries: 3
      })
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`API ${resp.status}: ${text}`);
    }

    const data = await resp.json();
    const generated = data.generated_answer || {};

    summaryEl.textContent = generated.summary || "No summary.";
    intentEl.textContent = data.preprocess?.intent || "-";
    strategyEl.textContent = data.adaptive_plan?.strategy || "-";
    confidenceEl.textContent = generated.confidence ?? "-";
    answerMarkdownEl.textContent = generated.answer_markdown || "";
    renderCitations(generated.citations || []);

    resultEl.classList.remove("hidden");
    setStatus("Done.");
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    askBtn.disabled = false;
  }
}

askBtn.addEventListener("click", runQuery);
