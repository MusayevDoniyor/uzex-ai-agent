---
name: uzex-commodity-analytics
description: Natural language analytics and market intelligence agent for the Uzbek Republican Commodity Exchange (UZEX / O'zRTXB) spot and futures trade registry (2022–2026). Supports querying transactions, prices, commodity volumes, market participants (INN/STIR), brokers, and official CBU USD exchange rates.
---

# UZEX Commodity Analytics AI Agent Skill

## Overview
This skill equips autonomous AI agents (Claude Code, Cursor, Codex, Gemini, Agensi) with deep market intelligence capabilities across the **Uzbek Republican Commodity Exchange (UZEX / O'zRTXB)**. It enables agents to inspect, analyze, and aggregate over 500,000 spot and futures transactions spanning 2022 to 2026.

## Available MCP Tools

When interacting with the UZEX MCP Server (`mcp_server.py`), agents have access to the following 4 tools:

1. `query_uzex_market(question: string, language: string)`
   - **Purpose**: Answer analytical market questions in natural language (Uzbek, Russian, English).
   - **Returns**: Factual answer, verified SQL query, and execution telemetry.
   - **Example**: `{"question": "2025-yilda eng koʻp sement sotgan kompaniya va qancha summaga?"}`

2. `lookup_deal(deal_number: integer)`
   - **Purpose**: Retrieve full transactional card and party details for a specific deal.
   - **Returns**: JSON object with deal date, product, volume, unit price, total sum, seller/buyer INN and names, and broker codes.
   - **Example**: `{"deal_number": 100001}`

3. `get_commodity_trends(product_name: string, year: integer)`
   - **Purpose**: Retrieve aggregated monthly trends (total deals, volume, average unit price, total turnover).
   - **Returns**: Array of monthly aggregates ordered chronologically.
   - **Example**: `{"product_name": "sement", "year": 2025}`

4. `get_usd_exchange_rate(date: string)`
   - **Purpose**: Look up the official Central Bank of Uzbekistan (CBU) USD/UZS exchange rate for any date from 2022 to 2026.
   - **Returns**: Exchange rate formatted in UZS per 1 USD.
   - **Example**: `{"date": "2024-08-15"}`

---

## Database Architecture & Entities

The underlying SQLite database contains 5 normalized tables:

### 1. `deals` (Spot & Futures Transactions)
- `deal_number` (INTEGER, PK): Unique transaction identifier.
- `deal_date` (TEXT, YYYY-MM-DD): Trade execution date (2022-01-03 to 2026-10-30).
- `deal_time` (TEXT, HH:MM:SS): Trade execution timestamp.
- `auction_type` (TEXT): Auction mechanism (`Английский аукцион`, `Обратный аукцион`, `Двусторонний аукцион`).
- `quantity` (INTEGER): Number of lots traded.
- `deal_sum` (REAL): Total contract value.
- `start_price` (REAL): Opening bid price.
- `contract_number` (INTEGER): FK to `contracts.contract_number`.
- `product_name` (TEXT): Commodity description (e.g. `Портландцемент ПЦ400-Д20`, `Топливо дизельное Марка ДТ-Л-К5`).
- `lot_size` (INTEGER): Units per lot.
- `unit` (TEXT): Measurement unit (`килограмм`, `тонна`, `литр`, `штука`, `куб.метр`).
- `region` (TEXT): Warehouse location (`Toshkent shahri`, `Samarqand viloyati`, etc.).
- `contract_type` (TEXT): `Внутренний` (Domestic in UZS) or `Экспортный` (Export in USD).
- `contract_form` (TEXT): `Спот`, `Форвард`, `Фьючерс`.
- `deal_status` (TEXT): `Исполнен`, `Оплачен`, `Ждёт оплату`, `Новый`, `Аннулирован(Не оплачен)`.
- `seller_inn` (TEXT): 9-digit tax ID of seller (FK to `participants.inn`).
- `buyer_inn` (TEXT): 9-digit tax ID of buyer (FK to `participants.inn`).
- `seller_broker` (TEXT): Broker office code (FK to `brokers.broker_code`, e.g. `BK001`).
- `buyer_broker` (TEXT): Broker office code (FK to `brokers.broker_code`, e.g. `BK002`).
- `volume_units` (REAL): Precalculated physical volume (`quantity * lot_size`).
- `unit_price` (REAL): Price per single physical unit (`deal_sum / volume_units`).

### 2. `contracts` (Specification Cards)
- `contract_number` (INTEGER, PK): Specification number.
- `product_name`, `brand`, `size`, `sort`, `product_type`, `product_class`, `industry`.
- `tn_ved_code` (TEXT): HS / Customs classification code.
- `currency` (TEXT): `Узбекский сум` or `Доллар США`.
- `base_price` (REAL), `deposit_percent` (TEXT), `delivery_basis` (TEXT: `EXW`, `FCA`, etc.).
- `payment_days`, `delivery_days`.

### 3. `participants` (Companies & Enterprises)
- `inn` (TEXT, PK): 9-digit INN/STIR.
- `name` (TEXT): Registered company name.
- `region` (TEXT): Registration region.
- `activity_type` (TEXT): Industry sector.
- `role` (TEXT): `Продавец` or `Покупатель`.
- `vat_payer` (TEXT): `Да` or `Нет`.

### 4. `brokers` (Brokerage Firms)
- `broker_code` (TEXT, PK): e.g. `BK001` to `BK120`.
- `name` (TEXT): Registered broker office name.
- `region` (TEXT): Operating region.

### 5. `usd_rates` (CBU Official Daily Currency Rates)
- `rate_date` (TEXT, PK, YYYY-MM-DD): Date from 2022-01-01 to 2026-10-30.
- `rate` (REAL): Central Bank official exchange rate (UZS per 1 USD).

---

## Domain Rules & SQL Patterns

### 1. Physical Trade Volume
Always sum `volume_units` (or `quantity * lot_size`):
```sql
SELECT SUM(volume_units) FROM deals WHERE product_name LIKE '%цемент%';
```

### 2. Export Turnover in National Currency (UZS)
Export deals are denominated in USD (`contract_type = 'Экспортный'`). Convert by joining `usd_rates`:
```sql
SELECT SUM(d.deal_sum * u.rate) AS total_uzs
FROM deals d
JOIN usd_rates u ON d.deal_date = u.rate_date
WHERE d.contract_type = 'Экспортный' AND d.deal_date BETWEEN '2024-08-01' AND '2024-08-31';
```

### 3. Broker Activity
Brokers can represent either the selling or buying side:
```sql
SELECT COUNT(*) AS deals_count, SUM(deal_sum) AS turnover
FROM deals
WHERE seller_broker = 'BK001' OR buyer_broker = 'BK001';
```

### 4. Fuzzy Commodity Matching
UZEX trade names are primarily cataloged in Russian or bilingual descriptions. Always use case-insensitive matching:
- **Cement**: `product_name LIKE '%цемент%' OR product_name LIKE '%sement%'`
- **Wheat/Grain**: `product_name LIKE '%пшениц%' OR product_name LIKE '%bug''doy%'`
- **Cotton**: `product_name LIKE '%хлопок%' OR product_name LIKE '%paxta%'`
- **Fuel/Gasoline**: `product_name LIKE '%бензин%'`
- **Sugar**: `product_name LIKE '%сахар%' OR product_name LIKE '%shakar%'`

---

## Zero-Hallucination & Security Contract

1. **Strict Grounding**: The agent never fabricates transaction numbers, prices, or company rankings. If the database returns 0 rows, the agent reports that no transactions exist for the requested criteria.
2. **Read-Only Inviolability**: Only `SELECT` statements are permitted. `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or `PRAGMA` queries are strictly rejected by the query engine.
3. **Language Matching**: Always reply in the exact language of the user prompt (Uzbek for Uzbek, Russian for Russian, English for English).
