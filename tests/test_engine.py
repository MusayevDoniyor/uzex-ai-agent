"""
Comprehensive Test Suite for UZEX AI Agent & MCP Server.
Verifies language detection, domain gating, SQL injection prevention,
database integrity, and MCP tool handlers.
"""

import os
import json
import asyncio

from engine import detect_language, is_domain_question, is_conversational, engine
from db import db_client, py_like
import mcp_server

def test_language_detection():
    # Uzbek Latin
    assert detect_language("2025-yilda sement narxi qanday o'zgargan?") == "uz"
    assert detect_language("Bug'doy bo'yicha eng yirik bitim qaysi?") == "uz"
    assert detect_language("BK001 brokeri orqali qilingan bitimlar") == "uz"

    # Russian Cyrillic
    assert detect_language("Какова средняя цена бензина АИ-92 в 2024 году?") == "ru"
    assert detect_language("Сколько сделок заключено в Навоийской области?") == "ru"
    assert detect_language("Топ продавцов сахара за 2025 год") == "ru"

def test_domain_guardrails():
    # Valid domain questions
    assert is_domain_question("Sement bo'yicha bitimlar soni") is True
    assert is_domain_question("BK001 brokeri orqali qilingan savdolar") is True
    assert is_domain_question("STIR 201112233 bo'yicha ma'lumot") is True
    assert is_domain_question("100050 shartnoma holati") is True
    assert is_domain_question("2025-yildagi eksport operatsiyalari") is True

    # Out of domain questions
    assert is_domain_question("Toshkentda bugun ob-havo qanday?") is False
    assert is_domain_question("Menga qiziqarli ertak aytib ber") is False
    assert is_domain_question("Python dasturlash tilini qanday o'rganish mumkin?") is False
    assert is_domain_question("Futbol bo'yicha oxirgi yangiliklar qanaqa?") is False

def test_conversational_detection():
    assert is_conversational("Salom") is True
    assert is_conversational("Assalomu alaykum") is True
    assert is_conversational("Привет, как дела?") is True
    assert is_conversational("Sen kimsan?") is True

def test_sql_injection_and_security_prevention():
    # Only SELECT statements must be allowed
    res_drop = db_client.execute_query("DROP TABLE deals;")
    assert res_drop["success"] is False
    assert "Security check failed" in res_drop["error"]

    res_delete = db_client.execute_query("DELETE FROM participants WHERE inn = '201112233';")
    assert res_delete["success"] is False
    assert "Security check failed" in res_delete["error"]

    res_update = db_client.execute_query("UPDATE deals SET deal_sum = 0;")
    assert res_update["success"] is False
    assert "Security check failed" in res_update["error"]

    # Valid SELECT query must succeed
    res_select = db_client.execute_query("SELECT COUNT(*) AS total FROM deals;")
    assert res_select["success"] is True
    assert len(res_select["rows"]) == 1

def test_py_like_pattern_matching():
    # Substring wildcard %text%
    assert py_like("%sement%", "Portlendsement PC400") is True
    assert py_like("%sement%", "Avtomobil benzini") is False

    # Prefix wildcard text%
    assert py_like("2025%", "2025-08-14") is True
    assert py_like("2025%", "2024-08-14") is False

    # Suffix wildcard %text
    assert py_like("%AJ", "OHANGARONSEMENT AJ") is True
    assert py_like("%AJ", "ORIENT BROKER MCHJ") is False

    # Case insensitivity
    assert py_like("%SEMENT%", "portlendsement pc500") is True

def test_sample_database_integrity():
    # Verify tables exist and have records
    tables = ["deals", "contracts", "participants", "brokers", "usd_rates"]
    for tbl in tables:
        res = db_client.execute_query(f"SELECT COUNT(*) FROM {tbl};")
        assert res["success"] is True, f"Failed querying {tbl}: {res.get('error')}"
        count = res["rows"][0][0]
        assert count > 0, f"Table {tbl} is empty"

    # Verify deals count >= 1000
    res_deals = db_client.execute_query("SELECT COUNT(*) FROM deals;")
    assert res_deals["rows"][0][0] >= 1000

    # Verify USD rates count >= 1000
    res_rates = db_client.execute_query("SELECT COUNT(*) FROM usd_rates;")
    assert res_rates["rows"][0][0] >= 1000

def test_mcp_tools():
    async def _test():
        # Test USD rate tool
        rate_res = await mcp_server.handle_get_usd_exchange_rate({"date": "2025-05-15"})
        assert "1 USD =" in rate_res
        assert "2025-05-15" in rate_res

        # Test Deal Lookup tool
        deal_res = await mcp_server.handle_lookup_deal({"deal_number": 100001})
        deal_data = json.loads(deal_res)
        assert deal_data["deal_number"] == 100001
        assert "product_name" in deal_data
        assert "deal_sum" in deal_data

        # Test Commodity Trends tool
        trends_res = await mcp_server.handle_get_commodity_trends({"product_name": "sement", "year": 2025})
        trends_data = json.loads(trends_res)
        assert isinstance(trends_data, list)
        assert len(trends_data) > 0
        assert "total_deals" in trends_data[0]

    asyncio.run(_test())

def test_engine_conversation_and_domain_gating():
    async def _test():
        # Small talk
        conv_res = await engine.process_query("Salom")
        assert conv_res["status"] == "conversation"
        assert "Assalomu alaykum" in conv_res["answer"] or "👋" in conv_res["answer"]

        # Out of domain
        ood_res = await engine.process_query("Python dasturlash tilini qanday o'rganish mumkin?")
        assert ood_res["status"] == "out_of_domain"
        assert "UZEX" in ood_res["answer"] or "mavjud emas" in ood_res["answer"]

        # Domain query via rule fallback (works deterministically without LLM API key)
        deal_rule_res = await engine.process_query("BK001 broker orqali qancha bitim tuzilgan?")
        assert deal_rule_res["status"] == "success"
        assert deal_rule_res["sql"] is not None
        assert "BK001" in deal_rule_res["sql"]

    asyncio.run(_test())

def test_analytics_api_endpoints():
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)

    # 1. /health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # 2. /api/meta
    res_meta = client.get("/api/meta")
    assert res_meta.status_code == 200
    assert "tables" in res_meta.json()["coverage"]

    # 3. /api/stats/overview
    res_overview = client.get("/api/stats/overview")
    assert res_overview.status_code == 200
    ov_data = res_overview.json()
    assert ov_data["total_deals"] > 0
    assert ov_data["total_turnover_uzs"] > 0
    assert ov_data["unique_products"] > 0

    # 4. /api/commodities
    res_comm = client.get("/api/commodities?limit=5")
    assert res_comm.status_code == 200
    comm_data = res_comm.json()
    assert "commodities" in comm_data
    assert len(comm_data["commodities"]) > 0
    assert "product_name" in comm_data["commodities"][0]

    # 5. /api/brokers/top
    res_brokers = client.get("/api/brokers/top?limit=5")
    assert res_brokers.status_code == 200
    br_data = res_brokers.json()
    assert "brokers" in br_data
    assert len(br_data["brokers"]) > 0
    assert "broker_code" in br_data["brokers"][0]

