import asyncio
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Add directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import engine, is_domain_question, detect_language
from db import db_client

async def run_tests():
    print("=== TEST 1: Language Detection ===")
    assert detect_language("2025-yilda qaysi kompaniya ko'p sement sotgan?") == "uz"
    assert detect_language("Какая компания продала больше всего цемента?") == "ru"
    print("Language detection: PASS")

    print("\n=== TEST 2: Domain Check ===")
    assert is_domain_question("Sement narxi qancha bo'lgan?") == True
    assert is_domain_question("What is the capital of France?") == False
    print("Domain check: PASS")

    print("\n=== TEST 3: Direct SQL Query via DBClient ===")
    sql = "SELECT product_name, COUNT(*) as cnt FROM deals GROUP BY product_name ORDER BY cnt DESC LIMIT 3;"
    res = db_client.execute_query(sql)
    print(f"Status: {res['success']}, Execution time: {res['elapsed_ms']}ms")
    for r in res['rows']:
        print("  Row:", r)
    assert res['success'] == True
    assert len(res['rows']) == 3
    print("Direct SQL Query: PASS")

    print("\n=== TEST 4: Security Check (Dangerous keyword blocking) ===")
    bad_sql = "DROP TABLE deals;"
    bad_res = db_client.execute_query(bad_sql)
    assert bad_res['success'] == False
    print("Security injection guard: PASS - Successfully blocked:", bad_res['error'])

    print("\n=== TEST 5: Out of domain processing ===")
    out_res = await engine.process_query("Bugun ob-havo qanday bo'ladi?")
    print("Out of domain answer:", out_res['answer'])
    assert out_res['status'] == "out_of_domain"
    print("Out of domain handling: PASS")

    print("\nALL LOCAL TESTS PASSED SUCCESSFULLY! 🚀")

if __name__ == '__main__':
    asyncio.run(run_tests())
