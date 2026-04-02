const ASK_STEPS = [
  { label: "解析问题上下文...", pct: 16 },
  { label: "执行混合检索...", pct: 42 },
  { label: "生成可执行计划...", pct: 72 },
  { label: "渲染结果与证据...", pct: 90 }
];

const STORAGE_KEYS = {
  profile: "fit_assistant_profile_v2",
  tracking: "fit_assistant_tracking_v2",
  history: "fit_assistant_history_v2",
  session: "fit_assistant_session_v1"
};

const dom = {
  askBtn: document.getElementById("askBtn"),
  baseUrlInput: document.getElementById("baseUrlInput"),
  questionInput: document.getElementById("questionInput"),
  statusText: document.getElementById("statusText"),
  progressBar: document.getElementById("progressBar"),
  resultSection: document.getElementById("resultSection"),
  summaryText: document.getElementById("summaryText"),
  intentText: document.getElementById("intentText"),
  strategyText: document.getElementById("strategyText"),
  confidenceText: document.getElementById("confidenceText"),
  safetyAlerts: document.getElementById("safetyAlerts"),
  weeklyPlan: document.getElementById("weeklyPlan"),
  actionItems: document.getElementById("actionItems"),
  nutritionTargets: document.getElementById("nutritionTargets"),
  citationsBox: document.getElementById("citationsBox"),
  markdownPreview: document.getElementById("markdownPreview"),
  evidenceCount: document.getElementById("evidenceCount"),
  freshCount: document.getElementById("freshCount"),
  historyCount: document.getElementById("historyCount"),
  saveProfileBtn: document.getElementById("saveProfileBtn"),
  copyMdBtn: document.getElementById("copyMdBtn"),
  downloadMdBtn: document.getElementById("downloadMdBtn"),
  downloadJsonBtn: document.getElementById("downloadJsonBtn"),
  addTrackBtn: document.getElementById("addTrackBtn"),
  trackDate: document.getElementById("trackDate"),
  trackWeight: document.getElementById("trackWeight"),
  trackWaist: document.getElementById("trackWaist"),
  trackAdherence: document.getElementById("trackAdherence"),
  trackingList: document.getElementById("trackingList"),
  trackingInsight: document.getElementById("trackingInsight"),
  historyBox: document.getElementById("historyBox"),
  adjustNoteInput: document.getElementById("adjustNoteInput")
};

const profileFields = {
  age: document.getElementById("ageInput"),
  sex: document.getElementById("sexInput"),
  height_cm: document.getElementById("heightInput"),
  weight_kg: document.getElementById("weightInput"),
  activity_level: document.getElementById("activityInput"),
  training_experience: document.getElementById("experienceInput"),
  primary_goal: document.getElementById("goalInput"),
  days_per_week: document.getElementById("daysInput"),
  session_minutes: document.getElementById("minutesInput"),
  diet_preference: document.getElementById("dietInput"),
  injuries: document.getElementById("injuryInput"),
  equipment: document.getElementById("equipmentInput")
};

const state = {
  activeFilter: "all",
  selectedAdjustment: "none",
  latestMarkdown: "",
  latestResponse: null,
  latestPayload: null,
  latestQuery: "",
  latestCitations: [],
  progressTimer: null
};

function nowIsoDate() {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}

function toNum(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function splitCommaText(value) {
  return String(value || "")
    .split(/[,，]/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function getSessionId() {
  const existing = localStorage.getItem(STORAGE_KEYS.session);
  if (existing) return existing;
  const sid = `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(STORAGE_KEYS.session, sid);
  return sid;
}

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function setStatus(text, level = "info") {
  dom.statusText.textContent = text;
  if (level === "error") {
    dom.statusText.style.color = "#ff9f97";
  } else if (level === "success") {
    dom.statusText.style.color = "#85f6d6";
  } else if (level === "warn") {
    dom.statusText.style.color = "#ffd99b";
  } else {
    dom.statusText.style.color = "";
  }
}

function startProgress() {
  clearInterval(state.progressTimer);
  let index = 0;
  dom.progressBar.style.width = "6%";
  setStatus("开始构建计划...");
  state.progressTimer = setInterval(() => {
    if (index >= ASK_STEPS.length) return;
    const step = ASK_STEPS[index];
    dom.progressBar.style.width = `${step.pct}%`;
    setStatus(step.label);
    index += 1;
  }, 750);
}

function finishProgress(success) {
  clearInterval(state.progressTimer);
  dom.progressBar.style.width = success ? "100%" : "0%";
}

function inferBaseUrl() {
  const origin = window.location?.origin || "";
  if (origin.startsWith("http")) {
    dom.baseUrlInput.value = origin;
  }
}

function getProfilePayload() {
  const profile = {
    age: toNum(profileFields.age.value),
    sex: profileFields.sex.value || null,
    height_cm: toNum(profileFields.height_cm.value),
    weight_kg: toNum(profileFields.weight_kg.value),
    activity_level: profileFields.activity_level.value || "moderate",
    training_experience: profileFields.training_experience.value || "intermediate",
    primary_goal: profileFields.primary_goal.value || "general_fitness"
  };

  const hasData = Object.values(profile).some((v) => v !== null && v !== "" && v !== "general_fitness");
  return hasData ? profile : null;
}

function getConstraintPayload() {
  const constraints = {
    days_per_week: toNum(profileFields.days_per_week.value) || 4,
    session_minutes: toNum(profileFields.session_minutes.value) || 60,
    equipment: splitCommaText(profileFields.equipment.value),
    injuries: splitCommaText(profileFields.injuries.value),
    diet_preference: profileFields.diet_preference.value.trim() || null
  };
  return constraints;
}

function getAdjustmentPayload() {
  const note = dom.adjustNoteInput.value.trim();
  return {
    adjustment_type: state.selectedAdjustment || "none",
    note
  };
}

function saveProfileToLocal() {
  const profile = {
    age: profileFields.age.value,
    sex: profileFields.sex.value,
    height_cm: profileFields.height_cm.value,
    weight_kg: profileFields.weight_kg.value,
    activity_level: profileFields.activity_level.value,
    training_experience: profileFields.training_experience.value,
    primary_goal: profileFields.primary_goal.value,
    days_per_week: profileFields.days_per_week.value,
    session_minutes: profileFields.session_minutes.value,
    diet_preference: profileFields.diet_preference.value,
    injuries: profileFields.injuries.value,
    equipment: profileFields.equipment.value
  };
  saveJson(STORAGE_KEYS.profile, profile);
  setStatus("个人画像已保存。", "success");
}

function loadProfileFromLocal() {
  const profile = loadJson(STORAGE_KEYS.profile, {});
  Object.keys(profileFields).forEach((k) => {
    if (profile[k] !== undefined && profile[k] !== null) {
      profileFields[k].value = profile[k];
    }
  });
}

function getFriendlyApiError(text) {
  const lower = String(text || "").toLowerCase();
  if (lower.includes("openai_api_key")) {
    return "后端缺少模型 API Key，请在服务端环境变量里设置后重启。";
  }
  if (lower.includes("failed to fetch")) {
    return "无法连接后端服务。请确认 API 已启动且地址正确。";
  }
  if (lower.includes("cors")) {
    return "跨域被拦截。建议前后端同域部署，或在后端放开 CORS。";
  }
  if (lower.includes("429")) {
    return "模型接口限流，请稍后重试。";
  }
  return `请求失败：${text}`;
}

function getRiskHint(queryText) {
  const q = String(queryText || "").toLowerCase();
  if (["胸痛", "晕", "黑蒙", "昏厥", "numbness", "chest pain", "faint"].some((k) => q.includes(k))) {
    return "检测到可能高风险症状，建议优先线下医疗评估。是否继续生成一般训练建议？";
  }
  return "";
}

function buildPayload(queryText) {
  return {
    session_id: getSessionId(),
    query: queryText,
    top_k_context_turns: 6,
    top_k_retrieval: 6,
    max_sub_queries: 3,
    user_profile: getProfilePayload(),
    constraints: getConstraintPayload(),
    adjustment: getAdjustmentPayload()
  };
}

function updateTopStats(citations) {
  const list = citations || [];
  dom.evidenceCount.textContent = list.length;
  dom.freshCount.textContent = list.filter((c) => String(c.freshness_level || "").toLowerCase() === "fresh").length;
  const history = loadJson(STORAGE_KEYS.history, []);
  dom.historyCount.textContent = history.length;
}

function renderSummary(response) {
  const generated = response.generated_answer || {};
  dom.summaryText.textContent = generated.summary || "暂无摘要。";
  dom.intentText.textContent = response.preprocess?.intent || "-";
  dom.strategyText.textContent = response.adaptive_plan?.strategy || "-";
  dom.confidenceText.textContent = generated.confidence ?? "-";
}

function renderSafety(alerts) {
  dom.safetyAlerts.innerHTML = "";
  const list = Array.isArray(alerts) ? alerts : [];
  if (list.length === 0) {
    const div = document.createElement("div");
    div.className = "alert-item low";
    div.textContent = "无明显风险信号。";
    dom.safetyAlerts.appendChild(div);
    return;
  }
  list.forEach((a) => {
    const div = document.createElement("div");
    const level = String(a.risk_level || "low").toLowerCase();
    div.className = `alert-item ${level}`;
    div.textContent = `[${level}] ${a.message} -> ${a.action}`;
    dom.safetyAlerts.appendChild(div);
  });
}

function renderWeeklyPlan(weeklyPlan) {
  dom.weeklyPlan.innerHTML = "";
  const plans = Array.isArray(weeklyPlan) ? weeklyPlan : [];
  if (plans.length === 0) {
    dom.weeklyPlan.innerHTML = "<p>暂无周计划，请补充画像后重新生成。</p>";
    return;
  }

  plans.forEach((d) => {
    const card = document.createElement("div");
    card.className = "week-card";
    const refs = (d.citation_ids || []).map((id) => `<button class="link-pill citation-link-btn" data-cite="${id}">引用${id}</button>`).join("");
    card.innerHTML = `
      <div class="week-head">
        <strong>${d.day}</strong>
        <span>${d.focus} · ${d.duration_minutes}分钟</span>
      </div>
      <ul>${(d.plan || []).map((x) => `<li>${x}</li>`).join("")}</ul>
      <div class="citation-links">${refs}</div>
    `;
    dom.weeklyPlan.appendChild(card);
  });
}

function renderActionItems(actionItems) {
  dom.actionItems.innerHTML = "";
  const list = Array.isArray(actionItems) ? actionItems : [];
  if (list.length === 0) {
    dom.actionItems.innerHTML = "<p>暂无行动项。</p>";
    return;
  }
  list.forEach((item, idx) => {
    const card = document.createElement("div");
    card.className = "action-card";
    const priority = String(item.priority || "medium").toLowerCase();
    const refs = (item.citation_ids || [])
      .map((id) => `<button class="link-pill citation-link-btn" data-cite="${id}">#${id}</button>`)
      .join("");

    card.innerHTML = `
      <div class="action-top">
        <p class="action-title">${idx + 1}. ${item.title || "未命名项"}</p>
        <span class="priority ${priority}">${priority}</span>
      </div>
      <span class="action-domain">${item.domain || "general"}</span>
      <p class="action-detail">${item.detail || ""}</p>
      <div class="citation-links">${refs}</div>
    `;
    dom.actionItems.appendChild(card);
  });
}

function renderNutritionTargets(targets) {
  dom.nutritionTargets.innerHTML = "";
  if (!targets) {
    dom.nutritionTargets.innerHTML = "<p>暂无营养目标。</p>";
    return;
  }
  const cards = [
    ["热量", `${targets.calories_kcal || 0}`, "kcal/天"],
    ["蛋白", `${targets.protein_g || 0}`, "g/天"],
    ["碳水", `${targets.carbs_g || 0}`, "g/天"],
    ["脂肪", `${targets.fat_g || 0}`, "g/天"],
    ["饮水", `${targets.hydration_ml || 0}`, "ml/天"]
  ];

  cards.forEach((x) => {
    const div = document.createElement("div");
    div.className = "nutri-card";
    div.innerHTML = `<strong>${x[1]}</strong><span>${x[0]} · ${x[2]}</span>`;
    dom.nutritionTargets.appendChild(div);
  });

  const note = document.createElement("p");
  note.className = "nutri-note";
  note.textContent = targets.note || "";
  dom.nutritionTargets.appendChild(note);
}

function badgeClass(type) {
  const t = String(type || "unknown").toLowerCase();
  if (t === "paper") return "paper";
  if (t === "book") return "book";
  if (t === "website") return "website";
  return "unknown";
}

function freshnessClass(level) {
  const x = String(level || "unknown").toLowerCase();
  if (x === "fresh") return "fresh";
  if (x === "recent") return "recent";
  if (x === "classic") return "classic";
  return "unknown";
}

function filteredCitations(citations) {
  const list = Array.isArray(citations) ? citations : [];
  const f = state.activeFilter;
  if (f === "all") return list;
  if (f === "fresh") return list.filter((x) => String(x.freshness_level || "").toLowerCase() === "fresh");
  return list.filter((x) => String(x.source_type || "unknown").toLowerCase() === f);
}

function renderCitations(citations) {
  state.latestCitations = citations || [];
  dom.citationsBox.innerHTML = "";
  const list = filteredCitations(citations);
  if (list.length === 0) {
    dom.citationsBox.innerHTML = "<p>当前筛选条件下无证据。</p>";
    updateTopStats(citations);
    return;
  }

  list.forEach((c) => {
    const scorePct = Math.round((Number(c.quality_score || 0) || 0) * 100);
    const card = document.createElement("div");
    card.className = "citation-card";
    card.id = `citation-${c.id}`;
    card.innerHTML = `
      <div class="citation-head">
        <p class="citation-title">[${c.id}] ${c.title || "Untitled"}</p>
        <div class="badges">
          <span class="badge ${badgeClass(c.source_type)}">${(c.source_type || "unknown").toUpperCase()}</span>
          <span class="badge ${freshnessClass(c.freshness_level)}">${c.freshness_level || "unknown"}</span>
        </div>
      </div>
      <p class="citation-meta">${c.authors || "-"} ${c.venue ? "· " + c.venue : ""} ${c.publish_date ? "· " + c.publish_date : ""}</p>
      <p class="citation-meta">质量分: ${scorePct}/100 · ${c.evidence_note || ""}</p>
      ${c.doi ? `<p class="citation-meta">DOI: ${c.doi}</p>` : ""}
      <p class="citation-meta">${c.snippet || ""}</p>
      ${c.url ? `<a class="citation-link" href="${c.url}" target="_blank" rel="noreferrer">打开原文</a>` : ""}
    `;
    dom.citationsBox.appendChild(card);
  });

  updateTopStats(citations);
}

function highlightCitation(id) {
  const target = document.getElementById(`citation-${id}`);
  if (!target) {
    setStatus(`引用 #${id} 不在当前筛选中，先切换到“全部”查看。`, "warn");
    return;
  }
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.add("highlight");
  setTimeout(() => target.classList.remove("highlight"), 1200);
}

function saveHistory(query, response) {
  const history = loadJson(STORAGE_KEYS.history, []);
  const generated = response.generated_answer || {};
  history.unshift({
    id: Date.now(),
    ts: new Date().toLocaleString(),
    query,
    summary: generated.summary || "",
    intent: response.preprocess?.intent || "-",
    confidence: generated.confidence ?? "-"
  });
  const clipped = history.slice(0, 20);
  saveJson(STORAGE_KEYS.history, clipped);
  renderHistory();
}

function renderHistory() {
  const history = loadJson(STORAGE_KEYS.history, []);
  dom.historyBox.innerHTML = "";
  if (history.length === 0) {
    dom.historyBox.innerHTML = "<p>暂无历史计划。</p>";
    updateTopStats(state.latestCitations);
    return;
  }
  history.forEach((h) => {
    const btn = document.createElement("button");
    btn.className = "history-btn";
    btn.innerHTML = `
      <div>${h.query}</div>
      <small>${h.ts} · intent=${h.intent} · conf=${h.confidence}</small>
    `;
    btn.addEventListener("click", () => {
      dom.questionInput.value = h.query;
      dom.questionInput.focus();
      setStatus("已载入历史问题，点击“生成计划”可复用。");
    });
    dom.historyBox.appendChild(btn);
  });
  updateTopStats(state.latestCitations);
}

function renderTracking() {
  const entries = loadJson(STORAGE_KEYS.tracking, []);
  dom.trackingList.innerHTML = "";
  if (entries.length === 0) {
    dom.trackingList.innerHTML = "<p>暂无追踪数据。</p>";
    dom.trackingInsight.textContent = "建议每周至少记录 2 次体重与训练完成度。";
    return;
  }
  entries.slice().reverse().forEach((e) => {
    const row = document.createElement("div");
    row.className = "track-row";
    row.textContent = `${e.date} | 体重 ${e.weight || "-"} kg | 腰围 ${e.waist || "-"} cm | 完成度 ${e.adherence || "-"}/5`;
    dom.trackingList.appendChild(row);
  });
  dom.trackingInsight.textContent = buildTrackingInsight(entries);
}

function buildTrackingInsight(entries) {
  if (entries.length < 2) return "记录已保存，继续积累一周后可自动给出趋势建议。";
  const sorted = entries.slice().sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const wDiff = (Number(last.weight || 0) - Number(first.weight || 0)).toFixed(1);
  const waistDiff = (Number(last.waist || 0) - Number(first.waist || 0)).toFixed(1);
  const avgAdh = (
    sorted.reduce((s, x) => s + Number(x.adherence || 0), 0) / Math.max(1, sorted.length)
  ).toFixed(2);

  return `趋势：体重变化 ${wDiff} kg，腰围变化 ${waistDiff} cm，平均完成度 ${avgAdh}/5。若连续2周无变化，建议微调热量 ±100~150 kcal。`;
}

function addTrackingEntry() {
  const date = dom.trackDate.value || nowIsoDate();
  const weight = dom.trackWeight.value.trim();
  const waist = dom.trackWaist.value.trim();
  const adherence = dom.trackAdherence.value.trim();
  if (!weight && !waist && !adherence) {
    setStatus("请至少填写一个追踪字段。", "warn");
    return;
  }
  const entries = loadJson(STORAGE_KEYS.tracking, []);
  entries.push({ date, weight, waist, adherence });
  saveJson(STORAGE_KEYS.tracking, entries.slice(-90));
  dom.trackWeight.value = "";
  dom.trackWaist.value = "";
  dom.trackAdherence.value = "";
  renderTracking();
  setStatus("追踪记录已添加。", "success");
}

function payloadHasProfile() {
  return Boolean(getProfilePayload());
}

async function runQuery(trigger = "manual") {
  const queryText = dom.questionInput.value.trim();
  if (!queryText) {
    setStatus("请先输入问题。", "error");
    return;
  }

  if (!payloadHasProfile()) {
    setStatus("建议先填写画像信息，计划会更准确。", "warn");
  }

  const riskHint = getRiskHint(queryText);
  if (riskHint && trigger !== "adjust") {
    const keepGoing = window.confirm(riskHint);
    if (!keepGoing) {
      setStatus("已取消生成。", "warn");
      return;
    }
  }

  const baseUrl = dom.baseUrlInput.value.trim().replace(/\/+$/, "");
  const payload = buildPayload(queryText);
  state.latestPayload = payload;
  state.latestQuery = queryText;

  dom.askBtn.disabled = true;
  startProgress();
  dom.resultSection.classList.add("hidden");

  try {
    const resp = await fetch(`${baseUrl}/chat/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`API ${resp.status}: ${text}`);
    }

    const data = await resp.json();
    state.latestResponse = data;
    state.latestMarkdown = data.generated_answer?.answer_markdown || "";
    finishProgress(true);

    renderSummary(data);
    renderSafety(data.generated_answer?.safety_alerts || []);
    renderWeeklyPlan(data.generated_answer?.weekly_plan || []);
    renderActionItems(data.generated_answer?.action_items || []);
    renderNutritionTargets(data.generated_answer?.nutrition_targets || null);
    renderCitations(data.generated_answer?.citations || []);
    dom.markdownPreview.textContent = state.latestMarkdown || "暂无 Markdown。";

    dom.resultSection.classList.remove("hidden");
    saveHistory(queryText, data);
    setStatus("计划生成完成。你可以直接点击行动项中的引用查看依据。", "success");
  } catch (err) {
    finishProgress(false);
    setStatus(getFriendlyApiError(err?.message || String(err)), "error");
  } finally {
    dom.askBtn.disabled = false;
  }
}

function copyMarkdown() {
  if (!state.latestMarkdown) {
    setStatus("没有可复制的 Markdown。", "warn");
    return;
  }
  navigator.clipboard.writeText(state.latestMarkdown).then(
    () => setStatus("Markdown 已复制。", "success"),
    () => setStatus("复制失败，请稍后重试。", "error")
  );
}

function downloadFile(filename, content, contentType) {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadMarkdown() {
  if (!state.latestMarkdown) {
    setStatus("没有可下载的 Markdown。", "warn");
    return;
  }
  downloadFile("fitness-plan.md", state.latestMarkdown, "text/markdown;charset=utf-8");
  setStatus("Markdown 已下载。", "success");
}

function downloadJsonReport() {
  if (!state.latestResponse) {
    setStatus("暂无可导出的报告。", "warn");
    return;
  }
  const report = {
    exported_at: new Date().toISOString(),
    query: state.latestQuery,
    payload: state.latestPayload,
    response: state.latestResponse,
    tracking: loadJson(STORAGE_KEYS.tracking, [])
  };
  downloadFile("fitness-plan-report.json", JSON.stringify(report, null, 2), "application/json;charset=utf-8");
  setStatus("JSON 报告已下载。", "success");
}

function bindEvents() {
  dom.askBtn.addEventListener("click", () => runQuery("manual"));
  dom.saveProfileBtn.addEventListener("click", saveProfileToLocal);
  dom.copyMdBtn.addEventListener("click", copyMarkdown);
  dom.downloadMdBtn.addEventListener("click", downloadMarkdown);
  dom.downloadJsonBtn.addEventListener("click", downloadJsonReport);
  dom.addTrackBtn.addEventListener("click", addTrackingEntry);

  document.querySelectorAll(".quick-query").forEach((btn) => {
    btn.addEventListener("click", () => {
      dom.questionInput.value = btn.getAttribute("data-q") || "";
      dom.questionInput.focus();
    });
  });

  document.querySelectorAll(".adjust-chip").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const val = btn.getAttribute("data-adjust") || "none";
      state.selectedAdjustment = val;
      document.querySelectorAll(".adjust-chip").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");

      if (dom.questionInput.value.trim()) {
        setStatus(`已切换调整模式：${val}，正在基于当前问题重算计划...`);
        await runQuery("adjust");
      } else {
        setStatus(`已设置调整模式：${val}。输入问题后点击“生成计划”。`);
      }
    });
  });

  document.querySelectorAll(".filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.activeFilter = btn.getAttribute("data-filter") || "all";
      document.querySelectorAll(".filter-chip").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      renderCitations(state.latestCitations);
    });
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.classList.contains("citation-link-btn")) {
      const citeId = Number(target.getAttribute("data-cite"));
      if (!Number.isFinite(citeId)) return;
      state.activeFilter = "all";
      document.querySelectorAll(".filter-chip").forEach((x) => x.classList.remove("active"));
      const allBtn = document.querySelector('.filter-chip[data-filter="all"]');
      allBtn?.classList.add("active");
      renderCitations(state.latestCitations);
      setTimeout(() => highlightCitation(citeId), 80);
    }
  });
}

function bootstrap() {
  inferBaseUrl();
  loadProfileFromLocal();
  renderHistory();
  renderTracking();
  dom.trackDate.value = nowIsoDate();
  bindEvents();
  setStatus("填写画像并输入问题后，点击“生成计划”。");
}

bootstrap();
