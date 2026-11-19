#!/usr/bin/env python3
"""
UZEX AI Agent - Interactive Command Line Interface (CLI)
Provides an instant, elegant terminal interface to query UZEX market data.
"""

import sys
import os
import asyncio
import time
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine import engine
from db import db_client

# ANSI styling helpers
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RED = "\033[31m"
RESET = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
╔════════════════════════════════════════════════════════════════╗
║             🏛️  UZEX AI AGENT — TERMINAL CLI REPL              ║
║    Uzbek Republican Commodity Exchange Market Intelligence     ║
╚════════════════════════════════════════════════════════════════╝{RESET}
{DIM}Type questions in Uzbek, Russian, or English.
Commands: {BOLD}.help{RESET}{DIM}, {BOLD}.stats{RESET}{DIM}, {BOLD}.commodities{RESET}{DIM}, {BOLD}.brokers{RESET}{DIM}, {BOLD}.exit{RESET}
"""

def print_help():
    print(f"""
{BOLD}Available Commands:{RESET}
  {CYAN}.stats{RESET}        - Display high-level market KPI summary
  {CYAN}.commodities{RESET}  - List top commodities by trading turnover
  {CYAN}.brokers{RESET}      - List top broker offices by transaction volume
  {CYAN}.clear{RESET}        - Clear terminal screen
  {CYAN}.help{RESET}         - Show this guidance
  {CYAN}.exit{RESET} / {CYAN}quit{RESET} - Exit the CLI

{BOLD}Sample Questions:{RESET}
  • 2025-yilda eng ko'p sement sotgan kompaniya va qancha summaga?
  • BK001 brokeri orqali qancha bitim tuzilgan?
  • №100050 shartnoma holati qanday?
  • Какова средняя цена бензина АИ-92 в 2024 году?
""")

def display_stats():
    sql = """
    SELECT 
        COUNT(*) AS total_deals,
        ROUND(SUM(deal_sum), 2) AS total_turnover,
        COUNT(DISTINCT product_name) AS unique_products,
        MIN(deal_date) AS min_date,
        MAX(deal_date) AS max_date
    FROM deals;
    """
    res = db_client.execute_query(sql)
    if res["success"] and res["rows"]:
        r = res["rows"][0]
        turnover_str = f"{r[1]:,.2f} UZS".replace(",", " ") if r[1] else "0 UZS"
        print(f"\n{GREEN}{BOLD}📊 UZEX Market KPI Summary:{RESET}")
        print(f"  • Total Deals:     {BOLD}{r[0]:,}{RESET}")
        print(f"  • Total Turnover:  {BOLD}{turnover_str}{RESET}")
        print(f"  • Unique Products: {BOLD}{r[2]}{RESET}")
        print(f"  • Date Coverage:   {BOLD}{r[3]} to {r[4]}{RESET}")
        print(f"  • Query Latency:   {DIM}{res['elapsed_ms']}ms{RESET}\n")

def display_commodities():
    sql = """
    SELECT 
        product_name,
        COUNT(*) AS deals_count,
        ROUND(SUM(deal_sum), 2) AS total_turnover
    FROM deals
    GROUP BY product_name
    ORDER BY total_turnover DESC
    LIMIT 5;
    """
    res = db_client.execute_query(sql)
    if res["success"]:
        print(f"\n{GREEN}{BOLD}🌾 Top Traded Commodities:{RESET}")
        print(f"  {'Commodity':<35} | {'Deals':<8} | {'Turnover (UZS)':<20}")
        print("  " + "-" * 70)
        for row in res["rows"]:
            sum_str = f"{row[2]:,.0f}".replace(",", " ")
            print(f"  {row[0]:<35} | {row[1]:<8} | {sum_str:<20}")
        print()

def display_brokers():
    sql = """
    SELECT 
        b.broker_code,
        b.name,
        COUNT(*) AS deals_count,
        ROUND(SUM(d.deal_sum), 2) AS total_turnover
    FROM deals d
    JOIN brokers b ON (d.seller_broker = b.broker_code OR d.buyer_broker = b.broker_code)
    GROUP BY b.broker_code
    ORDER BY total_turnover DESC
    LIMIT 5;
    """
    res = db_client.execute_query(sql)
    if res["success"]:
        print(f"\n{GREEN}{BOLD}🏢 Top Brokerage Firms:{RESET}")
        print(f"  {'Code':<8} | {'Broker Name':<32} | {'Deals':<8} | {'Turnover (UZS)':<20}")
        print("  " + "-" * 75)
        for row in res["rows"]:
            sum_str = f"{row[3]:,.0f}".replace(",", " ")
            print(f"  {row[0]:<8} | {row[1]:<32} | {row[2]:<8} | {sum_str:<20}")
        print()

async def execute_question(question: str):
    q = question.strip()
    if not q:
        return
    print(f"\n{DIM}Processing query...{RESET}")
    res = await engine.process_query(q)

    lang = res.get("language", "uz")
    elapsed = res.get("elapsed_seconds", 0)
    sql = res.get("sql")
    status = res.get("status", "unknown")
    answer = res.get("answer", "")

    # Header metadata
    print(f"{CYAN}Language:{RESET} {lang.upper()}  |  {CYAN}Status:{RESET} {status}  |  {CYAN}Latency:{RESET} {elapsed}s")

    # SQL preview
    if sql:
        print(f"\n{YELLOW}{BOLD}Verified SQL:{RESET}\n{DIM}{sql}{RESET}")

    # Answer
    print(f"\n{GREEN}{BOLD}Answer:{RESET}\n{answer}\n")

    # Data preview if rows returned
    data = res.get("data", [])
    columns = res.get("columns", [])
    if data and len(data) > 1:
        print(f"{DIM}Preview ({len(data)} rows returned):{RESET}")
        header = " | ".join(str(c) for c in columns[:5])
        print(f"{DIM}{header}{RESET}")
        for r in data[:3]:
            row_str = " | ".join(str(v) for v in r[:5])
            print(f"  {row_str}")
        print()

async def repl_loop():
    print(BANNER)
    while True:
        try:
            prompt_input = input(f"{BOLD}{CYAN}uzex>{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Goodbye!{RESET}")
            break

        if not prompt_input:
            continue
        elif prompt_input in (".exit", "exit", "quit", ".quit"):
            print(f"{DIM}Goodbye!{RESET}")
            break
        elif prompt_input == ".help":
            print_help()
        elif prompt_input == ".stats":
            display_stats()
        elif prompt_input == ".commodities":
            display_commodities()
        elif prompt_input == ".brokers":
            display_brokers()
        elif prompt_input == ".clear":
            os.system("cls" if os.name == "nt" else "clear")
        else:
            await execute_question(prompt_input)

def main():
    if len(sys.argv) > 1:
        # One-shot mode: python cli.py "question"
        one_shot_q = " ".join(sys.argv[1:])
        asyncio.run(execute_question(one_shot_q))
    else:
        asyncio.run(repl_loop())

if __name__ == "__main__":
    main()
