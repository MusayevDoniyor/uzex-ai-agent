const form = document.querySelector("#ask-form");
const question = document.querySelector("#question");
const answerCard = document.querySelector("#answer-card");
const askButton = document.querySelector("#ask-button");
const buttonLabel = document.querySelector("#button-label");
const charCount = document.querySelector("#char-count");
let loadingTimer;
let uiLanguage = localStorage.getItem("uzex-language") || "uz";
let lastQuestion = "";

const i18n = {
  uz: {
    heroLine1: "Birja ma'lumotlari,", heroLine2: "aniq javoblar.", heroCopy: "UZEX savdo ma'lumotlarini rus yoki o'zbek tilida so'rang. AI savolni tushunadi, xavfsiz so'rov tuzadi va javobni faqat berilgan dataset asosida tekshiradi.",
    trustVerified: "Manba bilan tekshirilgan", trustFast: "Tezkor javob", trustLanguages: "RU / UZ", askKicker: "ASK THE DATA", askTitle: "Savolingizni yozing", questionLabel: "Savol", questionPlaceholder: "Masalan: 2025-yilda nechta bitim bo'lgan?", tryLabel: "Sinab ko'ring", promptYear: "2025 statistikasi", promptRegions: "Top 3 hudud", promptDeal: "Сделка №100001", askButton: "Javobni ko'rish", emptyTitle: "Javob shu yerda chiqadi", emptyCopy: "Savol bering — biz datasetdan topamiz.", coverageKicker: "DATASET COVERAGE", coverageTitle: "Biz nimani bilamiz?", verified: "✓ verified", deals: "bitimlar", realRecords: "real UZEX records", contracts: "shartnomalar", participants: "ishtirokchilar", brokers: "brokerlar", coverageRange: "Qamrov", howKicker: "HOW IT WORKS", howTitle: "Har bir javobning yo'li", flowAi: "AI tushunadi", flowAiCopy: "RU / UZ savolni tahlil qiladi", flowSql: "SQL tekshiradi", flowSqlCopy: "Faqat ruxsat etilgan query", flowData: "Dataset javob beradi", flowDataCopy: "Manba va tezlik ko'rsatiladi", footerCopy: "Javoblar berilgan UZEX datasetiga asoslangan",
    checking: "Ma'lumotlar tekshirilmoqda", stageAi: "AI savolni UZEX datasetiga moslashtiryapti", stageSql: "Ruxsat etilgan SQL query tuzilyapti", stageVerify: "Natija va dalillar tekshirilmoqda", buttonLoading: "Tekshirilmoqda...", shortSummary: "QISQA XULOSA", answerTime: "Javob vaqti", recordsInFilter: "filterdagi yozuv", shown: "ko'rsatilgan natija", source: "UZEX dataset bilan tekshirilgan", noAnswer: "Javob topilmadi.", requestError: "So'rov bajarilmadi", requestErrorCopy: "Internet yoki server bilan bog'lanib bo'lmadi.", queryLabels: { get_deal: "Bitim ma'lumoti", get_contract: "Shartnoma ma'lumoti", aggregate_deals: "Statistik tahlil", search_deals: "Bitimlar qidiruvi", search_participant: "Ishtirokchi qidiruvi", get_broker: "Broker ma'lumoti", get_exchange_rate: "Valyuta kursi" }, groupLabels: { year: "Yillar", month: "Oylar", region: "Hududlar", product: "Mahsulotlar", status: "Statuslar", currency: "Valyutalar", seller: "Sotuvchilar", buyer: "Xaridorlar" }, chartTop: "Eng yuqori natijalar", chartTrend: "Dinamikasi", metricDeal: "bitim", metricValue: "qiymat", calculated: "UZEX datasetdan hisoblangan"
  },
  ru: {
    heroLine1: "Биржевые данные,", heroLine2: "точные ответы.", heroCopy: "Задавайте вопросы о торгах UZEX на русском или узбекском. AI понимает вопрос, строит безопасный запрос и проверяет ответ только по предоставленному набору данных.",
    trustVerified: "Проверено источником", trustFast: "Быстрый ответ", trustLanguages: "RU / UZ", askKicker: "СПРОСИТЕ ДАННЫЕ", askTitle: "Напишите вопрос", questionLabel: "Вопрос", questionPlaceholder: "Например: сколько сделок было в 2025 году?", tryLabel: "Попробуйте", promptYear: "Статистика 2025", promptRegions: "Топ-3 региона", promptDeal: "Сделка №100001", askButton: "Получить ответ", emptyTitle: "Ответ появится здесь", emptyCopy: "Задайте вопрос — мы найдём его в данных.", coverageKicker: "ОБЪЁМ ДАННЫХ", coverageTitle: "Что мы знаем?", verified: "✓ проверено", deals: "сделок", realRecords: "реальные записи UZEX", contracts: "контрактов", participants: "участников", brokers: "брокеров", coverageRange: "Период", howKicker: "КАК ЭТО РАБОТАЕТ", howTitle: "Путь каждого ответа", flowAi: "AI понимает", flowAiCopy: "Анализирует вопрос на RU / UZ", flowSql: "SQL проверяет", flowSqlCopy: "Только разрешённый запрос", flowData: "Данные отвечают", flowDataCopy: "Источник и скорость видны", footerCopy: "Ответы основаны на предоставленных данных UZEX",
    checking: "Проверяем данные", stageAi: "AI связывает вопрос с набором UZEX", stageSql: "Строим разрешённый SQL-запрос", stageVerify: "Проверяем результат и доказательства", buttonLoading: "Проверяем...", shortSummary: "КРАТКИЙ ИТОГ", answerTime: "Время ответа", recordsInFilter: "записей в фильтре", shown: "показано результатов", source: "Проверено по данным UZEX", noAnswer: "Ответ не найден.", requestError: "Запрос не выполнен", requestErrorCopy: "Не удалось подключиться к интернету или серверу.", queryLabels: { get_deal: "Данные сделки", get_contract: "Данные контракта", aggregate_deals: "Статистический анализ", search_deals: "Поиск сделок", search_participant: "Поиск участника", get_broker: "Данные брокера", get_exchange_rate: "Курс валюты" }, groupLabels: { year: "Годы", month: "Месяцы", region: "Регионы", product: "Товары", status: "Статусы", currency: "Валюты", seller: "Продавцы", buyer: "Покупатели" }, chartTop: "Лучшие результаты", chartTrend: "Динамика", metricDeal: "сделки", metricValue: "значение", calculated: "Рассчитано по данным UZEX"
  }
};

const copy = () => i18n[uiLanguage];
const translate = (key) => i18n[uiLanguage][key] || key;
const languageCopy = (language) => i18n[language] || i18n.uz;

function applyLanguage() {
  document.documentElement.lang = uiLanguage;
  document.querySelectorAll("[data-i18n]").forEach((element) => { element.textContent = translate(element.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => { element.placeholder = translate(element.dataset.i18nPlaceholder); });
  document.querySelectorAll(".locale-btn").forEach((button) => { const active = button.dataset.language === uiLanguage; button.classList.toggle("is-active", active); button.setAttribute("aria-pressed", String(active)); });
  buttonLabel.textContent = translate("askButton");
  if (!question.value) question.placeholder = translate("questionPlaceholder");
  const tables = window.datasetTables;
  if (tables?.deals) setMetaValue("#live-label", `${formatNumber(tables.deals)} ${translate("deals")}`);
}

const formatNumber = (value, language = uiLanguage) => new Intl.NumberFormat(language === "ru" ? "ru-RU" : "uz-UZ").format(value ?? 0);
const formatDuration = (value) => {
  if (value === null || value === undefined) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${value} ms`;
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

function setLoading(loading) {
  askButton.disabled = loading;
  answerCard.classList.toggle("is-loading", loading);
  answerCard.classList.remove("is-empty", "has-error");
  if (loading) {
    buttonLabel.textContent = translate("buttonLoading");
    answerCard.setAttribute("aria-busy", "true");
    answerCard.innerHTML = `<div class="loading-skeleton" role="status" aria-label="${escapeHtml(translate("checking"))}"><div class="loading-head"><span class="loading-mark">✦</span><div class="loading-copy"><strong>${escapeHtml(translate("checking"))}</strong><small id="loading-stage">${escapeHtml(translate("stageAi"))}</small></div><span class="loading-live">LIVE</span></div><div class="skeleton-preview"><span class="skeleton-line skeleton-title"></span><span class="skeleton-line"></span><span class="skeleton-line skeleton-short"></span></div><div class="skeleton-chart" aria-hidden="true"><span></span><span></span><span></span></div><div class="loading-chips"><span></span><span></span><span></span></div></div>`;
    const stages = [
      translate("stageAi"), translate("stageSql"), translate("stageVerify"),
    ];
    let stageIndex = 0;
    loadingTimer = window.setInterval(() => {
      stageIndex = (stageIndex + 1) % stages.length;
      const stage = document.querySelector("#loading-stage");
      if (stage) stage.textContent = stages[stageIndex];
    }, 950);
  } else {
    window.clearInterval(loadingTimer);
    answerCard.removeAttribute("aria-busy");
    buttonLabel.textContent = translate("askButton");
  }
}

function labelForQuery(type, language = uiLanguage) {
  return languageCopy(language).queryLabels[type] || (language === "ru" ? "Ответ по данным UZEX" : "UZEX dataset javobi");
}

function renderEvidence(evidence, language = uiLanguage) {
  const evidenceKeys = ["deal_number", "contract_number", "trade_date", "product", "region", "status", "amount", "currency", "delivery_date", "delivered", "seller_broker", "buyer_broker"];
  const allowed = Object.entries(evidence || {}).filter(([key, value]) => evidenceKeys.includes(key) && value !== null && value !== undefined && value !== "");
  if (!allowed.length) return "";
  const labels = language === "ru" ? { deal_number: "Сделка", contract_number: "Контракт", trade_date: "Дата", product: "Товар", region: "Регион", status: "Статус", amount: "Сумма", currency: "Валюта", delivery_date: "Поставка", delivered: "Доставлено", seller_broker: "Брокер продавца", buyer_broker: "Брокер покупателя" } : { deal_number: "Bitim", contract_number: "Shartnoma", trade_date: "Sana", product: "Mahsulot", region: "Hudud", status: "Status", amount: "Summa", currency: "Valyuta", delivery_date: "Yetkazish sanasi", delivered: "Yetkazildi", seller_broker: "Sotuvchi brokeri", buyer_broker: "Xaridor brokeri" };
  return `<div class="evidence-grid">${allowed.slice(0, 8).map(([key, value]) => `<div><span>${escapeHtml(labels[key] || key)}</span><b>${escapeHtml(value)}</b></div>`).join("")}</div>`;
}

function renderAggregateVisual(payload) {
  const series = payload.evidence?.series;
  if (!Array.isArray(series) || !series.length) return "";
  const group = payload.evidence?.group_by?.[0];
  const localized = languageCopy(payload.language);
  const groupLabels = localized.groupLabels;
  const metricLabel = payload.evidence?.metric === "count" ? localized.metricDeal : localized.metricValue;
  if (!group) {
    return `<div class="metric-highlight"><span>${escapeHtml(metricLabel)}</span><strong>${formatNumber(series[0].value, payload.language)}</strong><small>${escapeHtml(localized.calculated)}</small></div>`;
  }
  if (group === "year" || group === "month") return renderTrendVisual(payload, series, groupLabels[group]);
  const max = Math.max(...series.map((item) => Number(item.value) || 0), 1);
  const bars = series.slice(0, 7).map((item, index) => {
    const width = Math.max(7, Math.round(((Number(item.value) || 0) / max) * 100));
    const rank = String(index + 1).padStart(2, "0");
    return `<div class="chart-row chart-tone-${index + 1}" style="--row-index:${index}"><span class="chart-rank">${rank}</span><div class="chart-label" title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</div><div class="chart-track"><span style="width:${width}%"></span></div><b class="chart-value">${formatNumber(item.value, payload.language)}</b></div>`;
  }).join("");
  const chartHint = localized.chartTop;
  return `<div class="chart-block"><div class="chart-heading"><span>${escapeHtml(groupLabels[group] || group)}</span><small>${chartHint}</small></div>${bars}</div>`;
}

function renderTrendVisual(payload, series, title) {
  const values = series.map((item) => Number(item.value) || 0);
  const width = 620;
  const height = 170;
  const left = 24;
  const right = 18;
  const top = 16;
  const bottom = 31;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const xStep = series.length > 1 ? (width - left - right) / (series.length - 1) : 0;
  const points = series.map((item, index) => {
    const x = left + index * xStep;
    const y = top + (1 - ((Number(item.value) || 0) - min) / range) * (height - top - bottom);
    return { x, y, label: item.label, value: item.value };
  });
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const area = `${path} L${points.at(-1).x.toFixed(1)},${height - bottom} L${points[0].x.toFixed(1)},${height - bottom} Z`;
  const dots = points.map((point, index) => `<circle class="trend-dot" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="4" style="--dot-delay:${index * 90}ms"><title>${escapeHtml(point.label)}: ${formatNumber(point.value, payload.language)}</title></circle>`).join("");
  const labels = points.map((point) => `<text x="${point.x.toFixed(1)}" y="${height - 10}" text-anchor="middle">${escapeHtml(point.label)}</text>`).join("");
  const hint = languageCopy(payload.language).chartTrend;
  return `<div class="trend-block"><div class="chart-heading"><span>${escapeHtml(title)}</span><small>${hint}</small></div><svg class="trend-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)} trend chart"><defs><linearGradient id="trend-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#5ee7d0" stop-opacity=".28"/><stop offset="1" stop-color="#5ee7d0" stop-opacity="0"/></linearGradient></defs><path class="trend-area" d="${area}"/><path class="trend-path" d="${path}"/>${dots}${labels}</svg></div>`;
}

function renderAnswer(payload) {
  answerCard.classList.remove("is-loading", "is-empty", "has-error");
  const localized = languageCopy(payload.language);
  const rowLabel = payload.language === "ru" ? "записей в фильтре" : "ta yozuv filterda";
  const shownLabel = payload.language === "ru" ? "показано" : "ko'rsatilgan";
  const grouped = payload.evidence?.group_by?.length;
  const rows = payload.rows_matched !== null && payload.rows_matched !== undefined ? `<span>${formatNumber(payload.rows_matched, payload.language)} ${rowLabel}${grouped && payload.evidence.groups_returned ? ` · ${formatNumber(payload.evidence.groups_returned, payload.language)} ${shownLabel}` : ""}</span>` : "";
  const sqlHtml = payload.sql ? `<div class="sql-provenance" style="margin:14px 0;padding:10px 14px;background:rgba(10,16,36,0.9);border:1px solid rgba(94,231,208,0.25);border-radius:8px;font-family:'DM Mono',monospace;font-size:0.75rem;color:#5ee7d0;overflow-x:auto;line-height:1.4;"><span style="color:#8e9ab9;display:block;margin-bottom:4px;font-size:0.65rem;letter-spacing:0.06em;text-transform:uppercase;">🔍 Baza SQL soʻrovi (Grounding Provenance):</span><code>${escapeHtml(payload.sql)}</code></div>` : "";
  answerCard.innerHTML = `<div class="answer-topline"><div><span class="answer-label">${payload.language === "ru" ? "ОТВЕТ" : "JAVOB"}</span><span class="query-type">${escapeHtml(labelForQuery(payload.query_type, payload.language))}</span></div><span class="answer-time"><small>${escapeHtml(localized.answerTime)}</small> ⚡ ${escapeHtml(formatDuration(payload.latency_ms))}</span></div><div class="answer-summary"><span>${escapeHtml(localized.shortSummary)}</span><p class="answer-text">${escapeHtml(payload.answer || localized.noAnswer)}</p></div>${sqlHtml}${renderAggregateVisual(payload)}${renderEvidence(payload.evidence, payload.language)}<div class="answer-footer"><span class="source-check">✓ ${escapeHtml(localized.source)}</span>${rows}</div>`;
}

function renderError(message) {
  answerCard.classList.remove("is-loading", "is-empty");
  answerCard.classList.add("has-error");
  answerCard.innerHTML = `<div class="error-state"><span>!</span><div><strong>${escapeHtml(translate("requestError"))}</strong><small>${escapeHtml(message || translate("requestErrorCopy"))}</small></div></div>`;
}

async function ask(value) {
  const text = (value ?? question.value).trim();
  if (!text || askButton.disabled) return;
  lastQuestion = text;
  question.value = text;
  charCount.textContent = text.length;
  setLoading(true);
  try {
    const response = await fetch("/api/ask", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ question: text, language: uiLanguage }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Server error");
    renderAnswer(payload);
  } catch (error) {
    renderError(error.message || "Internet yoki server bilan bog'lanib bo'lmadi.");
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", (event) => { event.preventDefault(); ask(); });
question.addEventListener("input", () => { charCount.textContent = question.value.length; });
question.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); ask(); } });
document.querySelectorAll(".prompt").forEach((button) => button.addEventListener("click", () => ask(button.dataset.question)));
document.querySelectorAll(".locale-btn").forEach((button) => button.addEventListener("click", () => {
  const nextLanguage = button.dataset.language;
  if (nextLanguage === uiLanguage) return;
  uiLanguage = nextLanguage;
  localStorage.setItem("uzex-language", uiLanguage);
  applyLanguage();
  // Refresh the visible answer so prose and labels cannot remain in the old language.
  if (lastQuestion && !askButton.disabled) ask(lastQuestion);
}));

function setMetaValue(selector, value) {
  const element = document.querySelector(selector);
  if (!element) return;
  element.classList.remove("is-skeleton", "meta-skeleton-text");
  element.removeAttribute("aria-label");
  element.textContent = value;
}

async function loadMeta() {
  const coveragePanel = document.querySelector("#coverage-panel");
  try {
    const response = await fetch("/api/meta");
    if (!response.ok) throw new Error("Metadata request failed");
    const payload = await response.json();
    const tables = payload.coverage?.tables || {};
    window.datasetTables = tables;
    setMetaValue("#deal-count", formatNumber(tables.deals));
    setMetaValue("#contract-count", formatNumber(tables.contracts));
    setMetaValue("#participant-count", formatNumber(tables.participants));
    setMetaValue("#broker-count", formatNumber(tables.brokers));
    setMetaValue("#date-range", `${payload.coverage.date_from} — ${payload.coverage.date_to}`);
    setMetaValue("#live-label", `${formatNumber(tables.deals)} ${translate("deals")}`);
  } catch (_) {
    setMetaValue("#deal-count", "—");
    setMetaValue("#contract-count", "—");
    setMetaValue("#participant-count", "—");
    setMetaValue("#broker-count", "—");
    setMetaValue("#date-range", "—");
    setMetaValue("#live-label", uiLanguage === "ru" ? "Помощник онлайн" : "Live assistant");
  } finally {
    coveragePanel?.removeAttribute("aria-busy");
  }
}

applyLanguage();
loadMeta();
