#!/usr/bin/env python3
"""
UZEX AI Agent - Model Context Protocol (MCP) Server
Enables Claude Code, Cursor, Codex, and Agensi to query Uzbek Commodity Exchange (UZEX) market data.
Protocol: MCP JSON-RPC 2.0 over stdio
"""

import sys
import json
import asyncio
import logging
import re
from typing import Dict, Any, Optional

from db import db_client
from engine import engine

logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("uzex-mcp")

TOOLS = [
    {
        "name": "query_uzex_market",
        "description": (
            "Ask analytical questions in natural language (Uzbek, Russian, English) about UZEX "
            "commodity exchange spot and futures trades (2022-2026), commodity prices, trading volumes, "
            "buyer/seller companies, and broker transactions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question (e.g. '2025-yilda eng koʻp sement sotgan kompaniya', 'Какова средняя цена бензина АИ-92 в 2024 году?')"
                },
                "language": {
                    "type": "string",
                    "enum": ["uz", "ru", "en"],
                    "description": "Preferred response language (default: uz)",
                    "default": "uz"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "lookup_deal",
        "description": "Retrieve comprehensive details for a specific UZEX trade transaction by deal number.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "deal_number": {
                    "type": "integer",
                    "description": "Unique numeric identifier of the trade deal (e.g. 100001)"
                }
            },
            "required": ["deal_number"]
        }
    },
    {
        "name": "get_commodity_trends",
        "description": "Get monthly trading volume, average price, and transaction count for a commodity (e.g. sement, bug'doy, paxta, benzin).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Commodity name in Uzbek or Russian (e.g. 'sement', 'цемент', 'bug''doy', 'бензин')"
                },
                "year": {
                    "type": "integer",
                    "description": "Optional 4-digit filter year (e.g. 2024, 2025, 2026)"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_usd_exchange_rate",
        "description": "Get the official Central Bank of Uzbekistan (CBU) USD/UZS exchange rate for a given date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (e.g. '2025-05-15')"
                }
            },
            "required": ["date"]
        }
    }
]

async def handle_query_uzex_market(args: Dict[str, Any]) -> str:
    question = args.get("question", "").strip()
    if not question:
        return "Error: 'question' argument is required."
    res = await engine.process_query(question)
    output = res.get("answer", "No response generated.")
    if res.get("sql"):
        output += f"\n\n**Generated SQL:**\n```sql\n{res['sql']}\n```"
    if res.get("elapsed_seconds"):
        output += f"\n*Query executed in {res['elapsed_seconds']}s*"
    return output

async def handle_lookup_deal(args: Dict[str, Any]) -> str:
    deal_num = args.get("deal_number")
    if deal_num is None:
        return "Error: 'deal_number' argument is required."
    try:
        deal_num_int = int(deal_num)
    except (ValueError, TypeError):
        return f"Error: Invalid deal number '{deal_num}'."

    sql = (
        f"SELECT d.deal_number, d.deal_date, d.product_name, d.quantity, d.lot_size, "
        f"d.volume_units, d.unit_price, d.deal_sum, "
        f"d.contract_type, d.deal_status, d.seller_inn, p1.name AS seller_name, "
        f"d.buyer_inn, p2.name AS buyer_name, d.seller_broker, d.buyer_broker "
        f"FROM deals d "
        f"LEFT JOIN participants p1 ON d.seller_inn = p1.inn "
        f"LEFT JOIN participants p2 ON d.buyer_inn = p2.inn "
        f"WHERE d.deal_number = {deal_num_int} LIMIT 1;"
    )
    res = db_client.execute_query(sql)
    if not res["success"]:
        return f"Database error: {res['error']}"
    if not res["rows"]:
        return f"No deal found with deal_number {deal_num_int}."

    row = dict(zip(res["columns"], res["rows"][0]))
    return json.dumps(row, indent=2, ensure_ascii=False)

async def handle_get_commodity_trends(args: Dict[str, Any]) -> str:
    prod = args.get("product_name", "").strip()
    if not prod:
        return "Error: 'product_name' argument is required."
    year = args.get("year")
    year_filter = f"AND deal_date LIKE '{int(year)}%'" if year else ""

    clean_prod = prod.replace("'", "''").lower()
    sql = f"""
    SELECT 
        substr(deal_date, 1, 7) AS month,
        COUNT(*) AS total_deals,
        ROUND(SUM(volume_units), 2) AS total_volume_units,
        ROUND(AVG(unit_price), 2) AS avg_unit_price,
        ROUND(SUM(deal_sum), 2) AS total_sum
    FROM deals
    WHERE lower(product_name) LIKE '%{clean_prod}%' {year_filter}
    GROUP BY substr(deal_date, 1, 7)
    ORDER BY month DESC
    LIMIT 24;
    """
    res = db_client.execute_query(sql)
    if not res["success"]:
        return f"Database error: {res['error']}"
    if not res["rows"]:
        return f"No transaction trends found for commodity '{prod}'."

    records = [dict(zip(res["columns"], r)) for r in res["rows"]]
    return json.dumps(records, indent=2, ensure_ascii=False)

async def handle_get_usd_exchange_rate(args: Dict[str, Any]) -> str:
    d = args.get("date", "").strip()
    if not d:
        return "Error: 'date' argument is required."
    clean_d = re.sub(r'[^0-9\-]', '', d)
    sql = f"SELECT rate_date, rate FROM usd_rates WHERE rate_date = '{clean_d}' LIMIT 1;"
    res = db_client.execute_query(sql)
    if not res["success"]:
        return f"Database error: {res['error']}"
    if not res["rows"]:
        # Fallback to closest available rate
        fallback_sql = f"SELECT rate_date, rate FROM usd_rates ORDER BY ABS(julianday(rate_date) - julianday('{clean_d}')) LIMIT 1;"
        fb_res = db_client.execute_query(fallback_sql)
        if fb_res["success"] and fb_res["rows"]:
            return f"Exact date {clean_d} not found. Closest rate on {fb_res['rows'][0][0]}: 1 USD = {fb_res['rows'][0][1]:,} UZS."
        return f"No USD rate data available for date '{clean_d}'."

    row = res["rows"][0]
    return f"Official CBU exchange rate on {row[0]}: 1 USD = {row[1]:,} UZS."

TOOL_HANDLERS = {
    "query_uzex_market": handle_query_uzex_market,
    "lookup_deal": handle_lookup_deal,
    "get_commodity_trends": handle_get_commodity_trends,
    "get_usd_exchange_rate": handle_get_usd_exchange_rate,
}

async def process_json_rpc(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "uzex-ai-agent-mcp",
                    "version": "1.0.0"
                }
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS
            }
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)

        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Unknown tool: '{tool_name}'"}],
                    "isError": True
                }
            }

        try:
            res_text = await handler(args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": res_text}],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error executing tool '{tool_name}': {str(e)}"}],
                    "isError": True
                }
            }
    else:
        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found."
                }
            }
        return None

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "test"):
        print("UZEX MCP Server: Self-test mode")
        print(f"Available tools: {[t['name'] for t in TOOLS]}")
        rate = asyncio.run(handle_get_usd_exchange_rate({"date": "2025-01-15"}))
        print(f"Test get_usd_exchange_rate: {rate}")
        deal = asyncio.run(handle_lookup_deal({"deal_number": 100001}))
        print(f"Test handle_lookup_deal: {deal[:60]}...")
        trends = asyncio.run(handle_get_commodity_trends({"product_name": "Sement", "year": 2025}))
        print(f"Test handle_get_commodity_trends: {trends[:60]}...")
        print("Self-test passed successfully!")
        return

    # Standard MCP JSON-RPC 2.0 loop over stdio
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        try:
            req = json.loads(text)
            resp = asyncio.run(process_json_rpc(req))
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error handling message: {e}")

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
