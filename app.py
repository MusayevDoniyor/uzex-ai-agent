import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import TELEGRAM_BOT_TOKEN, PORT, HOST
from engine import engine

bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    if TELEGRAM_BOT_TOKEN:
        try:
            from bot import start_bot_polling
            bot_task = asyncio.create_task(start_bot_polling())
            print("Telegram Bot worker started successfully.")
        except Exception as e:
            print(f"Failed to start Telegram Bot worker: {e}")
    yield
    if bot_task:
        bot_task.cancel()

app = FastAPI(
    title="UZEX AI Hackathon Assistant",
    description="Intelligent Data Assistant for UZEX Spot Trade Transactions (2022–2026)",
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

# Mount static files
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

class AskRequest(BaseModel):
    question: str
    language: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    language: Optional[str] = None

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database_ready": True,
        "environment": "production"
    }

@app.get("/api/meta")
def get_meta():
    return {
        "source": "UZEX supplied exchange dataset",
        "languages": ["ru", "uz"],
        "coverage": {
            "ready": True,
            "tables": {
                "deals": 500000,
                "contracts": 6616,
                "participants": 14392,
                "brokers": 120,
                "usd_rates": 1765
            },
            "date_from": "2022-01-03",
            "date_to": "2026-10-30",
            "years": [
                {"year": "2022", "deals": 84299},
                {"year": "2023", "deals": 93985},
                {"year": "2024", "deals": 106647},
                {"year": "2025", "deals": 115763},
                {"year": "2026", "deals": 99306}
            ]
        },
        "capabilities": [
            "Deal and contract lookup",
            "Counts and totals by year, region, product and status",
            "Participants, brokers and USD rates"
        ]
    }

def build_ask_payload(res: Dict[str, Any], requested_lang: Optional[str] = None) -> Dict[str, Any]:
    lang = requested_lang or res.get("language") or "uz"
    data = res.get("data", [])
    columns = res.get("columns", [])
    sql = res.get("sql")
    elapsed = res.get("elapsed_seconds", 0)
    latency_ms = int(elapsed * 1000)

    # Determine query type
    query_type = "aggregate_deals"
    evidence: Dict[str, Any] = {
        "metric": "value",
        "group_by": [],
        "series": [],
        "groups_returned": 0
    }

    if sql:
        evidence["sql"] = sql

    # If rows exist, build series for chart/visual
    if data and len(columns) >= 2:
        # e.g. [name, total_sales_sum] or [region, count]
        series = []
        for row in data[:15]:
            label = str(row[0])
            val = row[1]
            try:
                val_num = float(val) if val is not None else 0
            except (ValueError, TypeError):
                val_num = 0
            series.append({"label": label, "value": val_num})
        evidence["series"] = series
        evidence["group_by"] = [columns[0]]
        evidence["metric"] = "sum_amount" if "sum" in columns[-1].lower() else "count"
        evidence["groups_returned"] = len(series)
    elif data and len(columns) == 1:
        # Single aggregate e.g. count or sum
        val = data[0][0]
        try:
            val_num = float(val) if val is not None else 0
        except (ValueError, TypeError):
            val_num = 0
        col_name = columns[0].lower()
        metric_name = "count" if "count" in col_name else "sum_amount"
        label = "Bitimlar soni" if metric_name == "count" else "Umumiy summa"
        if lang == "ru":
            label = "Количество сделок" if metric_name == "count" else "Общая сумма"
        evidence["series"] = [{"label": label, "value": val_num}]
        evidence["metric"] = metric_name
        evidence["groups_returned"] = 1

    # Check for single contract / deal lookup evidence
    if len(columns) > 3 and len(data) == 1:
        row_dict = dict(zip(columns, data[0]))
        for k in ["deal_number", "contract_number", "product_name", "deal_date", "deal_sum", "deal_status"]:
            if k in row_dict:
                evidence[k] = row_dict[k]
        query_type = "get_deal" if "deal_number" in row_dict else "get_contract"

    rows_matched = res.get("row_count") or (len(data) if data else 0)

    return {
        "answer": res["answer"],
        "language": lang,
        "query_type": query_type,
        "rows_matched": rows_matched,
        "evidence": evidence,
        "latency_ms": latency_ms,
        "sql": sql,
        "data_source": "UZEX supplied exchange dataset"
    }

@app.post("/api/ask")
async def api_ask(req: AskRequest):
    res = await engine.process_query(req.question)
    payload = build_ask_payload(res, req.language)
    return JSONResponse(payload)

@app.post("/api/query")
async def api_query(req: QueryRequest):
    res = await engine.process_query(req.query)
    payload = build_ask_payload(res, req.language)
    return JSONResponse(payload)

@app.get("/", response_class=HTMLResponse)
def index():
    tmpl_path = os.path.join(BASE_DIR, "templates", "index.html")
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>UZEX AI Hackathon Assistant is running.</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
