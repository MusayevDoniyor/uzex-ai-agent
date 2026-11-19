"""
Lightweight Sample Database Generator for UZEX AI Agent.
Generates a realistic SQLite database (uzex.db) with 1,000+ representative records
in under 1 second for instant local testing, CI/CD, and demonstrations without needing the 26MB archive.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "uzex.db"))

def build_sample_database(target_path: str = DB_PATH):
    print(f"Generating high-fidelity sample database at: {target_path}...")
    if os.path.exists(target_path):
        os.remove(target_path)

    conn = sqlite3.connect(target_path)
    cur = conn.cursor()

    # 1. BROKERS
    cur.execute("""
        CREATE TABLE brokers (
            broker_code TEXT PRIMARY KEY,
            name TEXT,
            inn TEXT,
            region TEXT
        );
    """)
    brokers_data = [
        ("BK001", "ORIENT BROKER SERVICE MCHJ", "305112233", "Toshkent shahri"),
        ("BK002", "CAPITAL TRADE BROKER MCHJ", "306223344", "Samarqand viloyati"),
        ("BK003", "ASIA COMMODITY BROKERS MCHJ", "307334455", "Farg'ona viloyati"),
        ("BK004", "SILK ROAD INVEST MCHJ", "308445566", "Navoiy viloyati"),
        ("BK005", "GLOBAL TRADE BROKERAGE MCHJ", "309556677", "Buxoro viloyati")
    ]
    cur.executemany("INSERT INTO brokers VALUES (?, ?, ?, ?);", brokers_data)

    # 2. PARTICIPANTS
    cur.execute("""
        CREATE TABLE participants (
            inn TEXT PRIMARY KEY,
            name TEXT,
            region TEXT,
            activity_type TEXT,
            role TEXT,
            vat_payer TEXT
        );
    """)
    participants_data = [
        ("201112233", "QIZILQUMSEMENT AJ", "Navoiy viloyati", "Qurilish materiallari ishlab chiqarish", "Sotuvchi", "Ha"),
        ("202223344", "OHANGARONSEMENT AJ", "Toshkent viloyati", "Sement va bog'lovchi materiallar", "Sotuvchi", "Ha"),
        ("203334455", "O'ZBEKNEFTGAZ AJ", "Toshkent shahri", "Neft-gaz mahsulotlari", "Sotuvchi", "Ha"),
        ("204445566", "TOSHKENT DON MAHSULOTLARI AJ", "Toshkent shahri", "G'alla va un mahsulotlari", "Sotuvchi", "Ha"),
        ("205556677", "XORAZM SHAKAR MCHJ", "Xorazm viloyati", "Oziq-ovqat ishlab chiqarish", "Sotuvchi", "Ha"),
        ("301112233", "BUILDING MEGA TECH MCHJ", "Toshkent shahri", "Bino va inshootlar qurilishi", "Xaridor", "Ha"),
        ("302223344", "AGRO GRAIN LOGISTICS MCHJ", "Samarqand viloyati", "Qishloq xo'jaligi savdosi", "Xaridor", "Ha"),
        ("303334455", "PETROL AUTO DISPATCH MCHJ", "Farg'ona viloyati", "Yoqilg'i quyish shoxobchalari", "Xaridor", "Ha"),
        ("304445566", "PREMIUM CONFECTIONERY MCHJ", "Andijon viloyati", "Qandolatchilik korxonasi", "Xaridor", "Ha")
    ]
    cur.executemany("INSERT INTO participants VALUES (?, ?, ?, ?, ?, ?);", participants_data)

    # 3. USD RATES
    cur.execute("""
        CREATE TABLE usd_rates (
            rate_date TEXT PRIMARY KEY,
            rate REAL
        );
    """)
    # 2022 to 2026 daily rates
    usd_rows = []
    base_rate = 10800.0
    start_dt = datetime(2022, 1, 1)
    for day in range(1800):
        dt = start_dt + timedelta(days=day)
        rate = round(base_rate + (day * 1.2) + random.uniform(-15, 15), 2)
        usd_rows.append((dt.strftime("%Y-%m-%d"), rate))
    cur.executemany("INSERT INTO usd_rates VALUES (?, ?);", usd_rows)

    # 4. CONTRACTS
    cur.execute("""
        CREATE TABLE contracts (
            contract_number INTEGER PRIMARY KEY,
            product_name TEXT,
            brand TEXT,
            size TEXT,
            sort TEXT,
            product_type TEXT,
            product_class TEXT,
            tn_ved_code TEXT,
            product_group TEXT,
            product_category TEXT,
            industry TEXT,
            unit TEXT,
            lot_size INTEGER,
            currency TEXT,
            base_price REAL,
            deposit_percent TEXT,
            delivery_basis TEXT,
            region TEXT,
            warehouse_address TEXT,
            auction_type TEXT,
            contract_type TEXT,
            contract_form TEXT,
            payment_days INTEGER,
            delivery_days INTEGER,
            packaging TEXT,
            seller_inn TEXT,
            registration_date TEXT,
            valid_until TEXT
        );
    """)
    contracts_data = [
        (1001, "Portlendsement PC400-D20", "Qizilqum", "50kg", "1-nav", "Sement", "Bog'lovchi", "2523290000", "Qurilish", "Sement", "Qurilish sanoati", "tn", 50, "UZS", 620000.0, "10%", "EXW", "Navoiy viloyati", "Navoiy sh., Sement zavodi", "Spot", "Ichki", "Standart", 5, 10, "Qop", "201112233", "2022-01-10", "2026-12-31"),
        (1002, "Avtomobil benzini AI-92", "Buxoro NQIZ", "Standard", "Oliy", "Yoqilg'i", "Neft mahsuloti", "2710124500", "Yoqilg'i-energetika", "Benzin", "Neft-gaz", "tn", 60, "UZS", 9500000.0, "10%", "FCA", "Buxoro viloyati", "Qorovulbozor", "Spot", "Ichki", "Standart", 3, 5, "Sisterna", "203334455", "2022-02-15", "2026-12-31"),
        (1003, "Oq shakar (Saxaroza 99.7%)", "Xorazm", "50kg", "1-nav", "Shakar", "Oziq-ovqat", "1701991000", "Qishloq xo'jaligi", "Shakar", "Oziq-ovqat sanoati", "tn", 20, "UZS", 8400000.0, "10%", "EXW", "Xorazm viloyati", "Xonqa tumani", "Spot", "Ichki", "Standart", 5, 7, "Qop", "205556677", "2022-03-01", "2026-12-31"),
        (1004, "3-sinf bug'doy", "O'zdon", "Standard", "3-sinf", "Don", "G'alla", "1001990000", "Qishloq xo'jaligi", "G'alla", "Agrosanoat", "tn", 40, "UZS", 3100000.0, "5%", "EXW", "Toshkent shahri", "Sirg'ali don ombori", "Spot", "Ichki", "Standart", 3, 10, "Nasipnoy", "204445566", "2022-01-15", "2026-12-31"),
        (1005, "Portlendsement PC500", "Ohangaron", "50kg", "Oliy", "Sement", "Bog'lovchi", "2523290000", "Qurilish", "Sement", "Qurilish sanoati", "tn", 50, "UZS", 740000.0, "10%", "EXW", "Toshkent viloyati", "Ohangaron sh.", "Spot", "Ichki", "Standart", 5, 10, "Qop", "202223344", "2022-04-01", "2026-12-31")
    ]
    cur.executemany("INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", contracts_data)

    # 5. DEALS (1,200 representative deals across 2022-2026)
    cur.execute("""
        CREATE TABLE deals (
            deal_number INTEGER PRIMARY KEY,
            deal_date TEXT,
            deal_time TEXT,
            auction_type TEXT,
            quantity INTEGER,
            deal_sum REAL,
            start_price REAL,
            contract_number INTEGER,
            product_name TEXT,
            lot_size INTEGER,
            unit TEXT,
            region TEXT,
            contract_type TEXT,
            contract_form TEXT,
            deal_status TEXT,
            seller_inn TEXT,
            buyer_inn TEXT,
            seller_broker TEXT,
            buyer_broker TEXT,
            payment_date TEXT,
            delivery_date TEXT,
            delivered INTEGER,
            volume_units REAL,
            unit_price REAL
        );
    """)

    deals = []
    deal_num = 100001
    contract_choices = [
        (1001, "Portlendsement PC400-D20", "tn", 50, 620000.0, "Navoiy viloyati", "201112233", "301112233"),
        (1002, "Avtomobil benzini AI-92", "tn", 60, 9500000.0, "Buxoro viloyati", "203334455", "303334455"),
        (1003, "Oq shakar (Saxaroza 99.7%)", "tn", 20, 8400000.0, "Xorazm viloyati", "205556677", "304445566"),
        (1004, "3-sinf bug'doy", "tn", 40, 3100000.0, "Toshkent shahri", "204445566", "302223344"),
        (1005, "Portlendsement PC500", "tn", 50, 740000.0, "Toshkent viloyati", "202223344", "301112233")
    ]
    statuses = ["Bajarilgan", "Bajarilgan", "Bajarilgan", "Yangi", "Bekor qilingan"]

    for yr in [2022, 2023, 2024, 2025, 2026]:
        deals_count = 250 if yr < 2026 else 200
        for _ in range(deals_count):
            c_num, p_name, unit, lot, sprice, region, s_inn, b_inn = random.choice(contract_choices)
            qty = random.randint(1, 10)
            vol = qty * lot
            price_variance = random.uniform(0.98, 1.08)
            u_price = round(sprice * price_variance, 2)
            d_sum = round(vol * u_price, 2)
            month = random.randint(1, 12 if yr < 2026 else 10)
            day = random.randint(1, 28)
            deal_date = f"{yr}-{month:02d}-{day:02d}"
            deal_time = f"{random.randint(9, 17):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
            status = random.choice(statuses)
            s_broker = random.choice(["BK001", "BK002", "BK004"])
            b_broker = random.choice(["BK001", "BK003", "BK005"])

            deals.append((
                deal_num,
                deal_date,
                deal_time,
                "Spot",
                qty,
                d_sum,
                sprice,
                c_num,
                p_name,
                lot,
                unit,
                region,
                "Ichki",
                "Standart",
                status,
                s_inn,
                b_inn,
                s_broker,
                b_broker,
                deal_date,
                deal_date,
                1 if status == "Bajarilgan" else 0,
                vol,
                u_price
            ))
            deal_num += 1

    cur.executemany("INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", deals)

    # 6. INDEXES
    indexes = [
        "CREATE INDEX idx_deals_date ON deals(deal_date);",
        "CREATE INDEX idx_deals_product ON deals(product_name);",
        "CREATE INDEX idx_deals_seller ON deals(seller_inn);",
        "CREATE INDEX idx_deals_buyer ON deals(buyer_inn);",
        "CREATE INDEX idx_deals_contract ON deals(contract_number);",
        "CREATE INDEX idx_deals_status ON deals(deal_status);",
        "CREATE INDEX idx_deals_region ON deals(region);",
        "CREATE INDEX idx_contracts_seller ON contracts(seller_inn);",
        "CREATE INDEX idx_contracts_pname ON contracts(product_name);",
        "CREATE INDEX idx_participants_name ON participants(name);",
        "CREATE INDEX idx_brokers_code ON brokers(broker_code);"
    ]
    for idx_sql in indexes:
        cur.execute(idx_sql)

    conn.commit()
    conn.close()

    print(f"Sample database built successfully: {len(deals)} deals, {len(contracts_data)} contracts.")

if __name__ == "__main__":
    build_sample_database()
