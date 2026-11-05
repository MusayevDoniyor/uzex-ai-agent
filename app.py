import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from engine import engine
from config import TELEGRAM_BOT_TOKEN, PORT, HOST
import uvicorn

bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    # Start bot if token is provided
    if TELEGRAM_BOT_TOKEN:
        try:
            from bot import start_bot_polling
            bot_task = asyncio.create_task(start_bot_polling())
            print("Telegram Bot task started successfully.")
        except Exception as e:
            print(f"Failed to start Telegram Bot: {e}")
    yield
    if bot_task:
        bot_task.cancel()

app = FastAPI(
    title="UZEX AI Agent",
    description="Intelligent AI Agent for UZEX Commodity Exchange Spot Registry",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "UZEX AI Agent"}

@app.post("/api/query")
async def api_query(req: QueryRequest):
    result = await engine.process_query(req.query)
    return JSONResponse(result)

INDEX_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UZEX AI Agent — Birja bitimlari tahlili</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0C1033;
      --card: #141B4D;
      --card-border: rgba(201, 211, 255, 0.15);
      --neon: #3DF08A;
      --blue: #3A55C8;
      --text: #FFFFFF;
      --text-muted: #AEBCF3;
      --mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 1.5rem 2rem;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(12, 16, 51, 0.8);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1.25rem;
      font-weight: 700;
    }
    .brand-badge {
      background: var(--neon);
      color: #0C1033;
      font-size: 0.75rem;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
      font-family: var(--mono);
    }
    main {
      flex: 1;
      max-width: 900px;
      width: 100%;
      margin: 0 auto;
      padding: 2.5rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }
    .hero {
      text-align: center;
    }
    .hero h1 {
      font-size: 2.25rem;
      line-height: 1.2;
      margin-bottom: 0.75rem;
    }
    .hero h1 span { color: var(--neon); }
    .hero p {
      color: var(--text-muted);
      font-size: 1rem;
      max-width: 600px;
      margin: 0 auto;
    }
    .chat-card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.5rem;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .input-box {
      display: flex;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }
    textarea {
      flex: 1;
      background: #090D28;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1rem;
      color: var(--text);
      font-size: 1rem;
      font-family: inherit;
      resize: vertical;
      min-height: 70px;
      outline: none;
      transition: border-color 0.2s;
    }
    textarea:focus { border-color: var(--neon); }
    button.send-btn {
      background: var(--neon);
      color: #0C1033;
      border: none;
      border-radius: 12px;
      padding: 0 1.75rem;
      font-weight: 700;
      font-size: 1rem;
      cursor: pointer;
      transition: transform 0.15s, background 0.15s;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    button.send-btn:hover { background: #55f399; transform: translateY(-1px); }
    button.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1.5rem;
    }
    .pill {
      background: rgba(201, 211, 255, 0.08);
      border: 1px solid var(--card-border);
      padding: 0.4rem 0.8rem;
      border-radius: 20px;
      font-size: 0.82rem;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s;
    }
    .pill:hover {
      background: rgba(61, 240, 138, 0.15);
      border-color: var(--neon);
      color: var(--neon);
    }
    .response-area {
      display: none;
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--card-border);
    }
    .response-title {
      font-size: 0.85rem;
      font-family: var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--neon);
      margin-bottom: 0.75rem;
      display: flex;
      justify-content: space-between;
    }
    .answer-text {
      font-size: 1.05rem;
      line-height: 1.6;
      white-space: pre-wrap;
      color: #FFFFFF;
      background: #090D28;
      padding: 1.25rem;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .sql-box {
      margin-top: 1rem;
      background: #07091B;
      border-radius: 8px;
      padding: 0.75rem 1rem;
      font-family: var(--mono);
      font-size: 0.85rem;
      color: #AEBCF3;
      overflow-x: auto;
      border: 1px solid var(--card-border);
    }
    .loading-spinner {
      display: none;
      align-items: center;
      gap: 0.5rem;
      color: var(--neon);
      font-family: var(--mono);
      font-size: 0.9rem;
      margin-top: 1rem;
    }
    footer {
      text-align: center;
      padding: 1.5rem;
      color: rgba(174, 188, 243, 0.5);
      font-size: 0.85rem;
      border-top: 1px solid var(--card-border);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>UZEX AI Agent</span>
      <span class="brand-badge">Saralash 2026</span>
    </div>
    <div style="font-family: var(--mono); font-size: 0.85rem; color: var(--neon);">
      500 000 bitim bazasi
    </div>
  </header>

  <main>
    <div class="hero">
      <h1>Birja maʼlumotlari boʻyicha <span>aniq AI-javoblar</span></h1>
      <p>500 000 ta birja bitimi, shartnomalar, ishtirokchilar va dollar kursi boʻyicha oʻzbek va rus tillarida tahlil.</p>
    </div>

    <div class="chat-card">
      <div class="suggestions">
        <div class="pill" onclick="setQuery('2025-yilda eng koʻp sement sotgan kompaniya va qancha summaga?')">Sement boʻyicha yetakchi (2025)</div>
        <div class="pill" onclick="setQuery('2024-yil avgust oyidagi eksport bitimlarining soʻmdagi umumiy hajmi qancha?')">Eksport bitimlari (soʻmda)</div>
        <div class="pill" onclick="setQuery('Qancha bitim bekor qilingan (annulirovan)?')">Bekor qilingan bitimlar</div>
        <div class="pill" onclick="setQuery('BK001 broker orqali qancha bitim tuzilgan?')">Broker statistikasi</div>
      </div>

      <div class="input-box">
        <textarea id="queryInput" placeholder="Savolingizni oʻzbek yoki rus tilida yozing..."></textarea>
        <button class="send-btn" id="sendBtn" onclick="sendQuery()">Yuborish</button>
      </div>

      <div class="loading-spinner" id="loading">
        <span>Maʼlumotlar bazasi tahlil qilinmoqda...</span>
      </div>

      <div class="response-area" id="responseArea">
        <div class="response-title">
          <span>Javob</span>
          <span id="timingBadge"></span>
        </div>
        <div class="answer-text" id="answerText"></div>
        <div class="sql-box" id="sqlBox"></div>
      </div>
    </div>
  </main>

  <footer>
    UZEX AI Hackathon 2026 · Saralash bosqichi · Aniq maʼlumotlarga asoslangan AI-agent
  </footer>

  <script>
    function setQuery(text) {
      document.getElementById('queryInput').value = text;
      sendQuery();
    }

    async function sendQuery() {
      const q = document.getElementById('queryInput').value.trim();
      if (!q) return;

      const sendBtn = document.getElementById('sendBtn');
      const loading = document.getElementById('loading');
      const respArea = document.getElementById('responseArea');
      const ansText = document.getElementById('answerText');
      const sqlBox = document.getElementById('sqlBox');
      const timingBadge = document.getElementById('timingBadge');

      sendBtn.disabled = true;
      loading.style.display = 'flex';
      respArea.style.display = 'none';

      try {
        const res = await fetch('/api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q })
        });
        const data = await res.json();

        ansText.textContent = data.answer;
        if (data.sql) {
          sqlBox.style.display = 'block';
          sqlBox.textContent = "SQL: " + data.sql;
        } else {
          sqlBox.style.display = 'none';
        }
        timingBadge.textContent = data.elapsed_seconds ? data.elapsed_seconds + "s" : "";
        respArea.style.display = 'block';
      } catch (err) {
        ansText.textContent = "Xatolik yuz berdi: " + err.message;
        respArea.style.display = 'block';
      } finally {
        sendBtn.disabled = false;
        loading.style.display = 'none';
      }
    }

    document.getElementById('queryInput').addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuery();
      }
    });
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(INDEX_HTML)

if __name__ == "__main__":
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
