import csv
import os
import sqlite3
import sys
import time
import zipfile
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'uzex_spot_data'))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, 'uzex.db'))

# Auto-extract from zip if data folder is missing
if not os.path.exists(DATA_DIR):
    zip_path = os.path.join(BASE_DIR, 'uzex_spot_data.zip')
    if not os.path.exists(zip_path):
        # Check parent dir
        parent_zip = os.path.abspath(os.path.join(BASE_DIR, '..', 'uzex_spot_data_actual.zip'))
        if os.path.exists(parent_zip):
            zip_path = parent_zip

    if os.path.exists(zip_path):
        print(f"Extracting {zip_path} into {BASE_DIR}...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BASE_DIR)
        print("Extracted successfully.")



def parse_date(d_str):
    if not d_str or not d_str.strip():
        return None
    d_str = d_str.strip()
    try:
        # Expected DD.MM.YYYY
        parts = d_str.split('.')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    except Exception:
        pass
    return d_str

def parse_float(val):
    if not val or not val.strip():
        return None
    # Remove all spaces (thousands separators)
    clean = val.replace(' ', '').replace('\xa0', '').strip()
    try:
        return float(clean)
    except Exception:
        return None

def parse_int(val):
    if not val or not val.strip():
        return None
    clean = val.replace(' ', '').replace('\xa0', '').strip()
    try:
        return int(float(clean))
    except Exception:
        return None

def build_database():
    start_time = time.time()
    print(f"Connecting to {DB_PATH}...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Optimizations for fast batch inserts
    cur.execute("PRAGMA journal_mode = OFF;")
    cur.execute("PRAGMA synchronous = 0;")
    cur.execute("PRAGMA cache_size = 100000;")

    # 1. BROKERS
    print("Loading brokers.csv...")
    cur.execute("""
        CREATE TABLE brokers (
            broker_code TEXT PRIMARY KEY,
            name TEXT,
            inn TEXT,
            region TEXT
        );
    """)
    with open(os.path.join(DATA_DIR, 'brokers.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        broker_rows = [
            (r['Код брокера'].strip(), r['Наименование'].strip(), r['ИНН'].strip(), r['Регион'].strip())
            for r in reader
        ]
        cur.executemany("INSERT INTO brokers VALUES (?, ?, ?, ?);", broker_rows)
    print(f"  Loaded {len(broker_rows)} brokers.")

    # 2. PARTICIPANTS
    print("Loading participants.csv...")
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
    with open(os.path.join(DATA_DIR, 'participants.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        part_rows = [
            (
                r['ИНН'].strip(),
                r['Наименование'].strip(),
                r['Регион'].strip(),
                r['Вид деятельности'].strip(),
                r['Роль'].strip(),
                r['Плательщик НДС'].strip()
            )
            for r in reader
        ]
        cur.executemany("INSERT INTO participants VALUES (?, ?, ?, ?, ?, ?);", part_rows)
    print(f"  Loaded {len(part_rows)} participants.")

    # 3. USD RATES
    print("Loading usd_rates.csv...")
    cur.execute("""
        CREATE TABLE usd_rates (
            rate_date TEXT PRIMARY KEY,
            rate REAL
        );
    """)
    with open(os.path.join(DATA_DIR, 'usd_rates.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        usd_rows = [
            (parse_date(r['Дата']), parse_float(r['Курс']))
            for r in reader
        ]
        cur.executemany("INSERT INTO usd_rates VALUES (?, ?);", usd_rows)
    print(f"  Loaded {len(usd_rows)} USD rates.")

    # 4. CONTRACTS
    print("Loading contracts.csv...")
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
    with open(os.path.join(DATA_DIR, 'contracts.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        contract_rows = []
        for r in reader:
            contract_rows.append((
                parse_int(r['Номер контракта']),
                r['Наименование продукта'].strip(),
                r['Марка товара'].strip(),
                r['Размер товара'].strip(),
                r['Сорт товара'].strip(),
                r['Тип товара'].strip(),
                r['Класс товара'].strip(),
                r['Код ТН ВЭД'].strip(),
                r['Группа товара'].strip(),
                r['Категория товара'].strip(),
                r['Отрасль промышленности'].strip(),
                r['Единица измерения'].strip(),
                parse_int(r['Лот']),
                r['Валюта'].strip(),
                parse_float(r['Базисная цена']),
                r['Сумма залога'].strip(),
                r['Базис поставки'].strip(),
                r['Регион'].strip(),
                r['Адрес склада'].strip(),
                r['Тип торгов'].strip(),
                r['Тип контракта'].strip(),
                r['Форма контракта'].strip(),
                parse_int(r['Срок оплаты']),
                parse_int(r['Срок поставки']),
                r['Упаковка'].strip(),
                r['ИНН продавца'].strip(),
                parse_date(r['Дата регистрации']),
                parse_date(r['Действует до'])
            ))
        cur.executemany("INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", contract_rows)
    print(f"  Loaded {len(contract_rows)} contracts.")

    # 5. DEALS (all 5 years merged)
    print("Loading deals (2022-2026)...")
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

    total_deals = 0
    deal_files = [f"deals_{y}.csv" for y in [2022, 2023, 2024, 2025, 2026]]
    batch = []
    batch_size = 50000

    for df in deal_files:
        fpath = os.path.join(DATA_DIR, df)
        print(f"  Processing {df}...")
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                qty = parse_int(r['Количество'])
                lot = parse_int(r['Лот'])
                dsum = parse_float(r['Сумма сделки'])
                sprice = parse_float(r['Стартовая цена'])
                
                vol = (qty * lot) if (qty is not None and lot is not None) else None
                uprice = (dsum / vol) if (dsum is not None and vol is not None and vol > 0) else None

                batch.append((
                    parse_int(r['Номер сделки']),
                    parse_date(r['Дата сделки']),
                    r['Время сделки'].strip(),
                    r['Тип торгов'].strip(),
                    qty,
                    dsum,
                    sprice,
                    parse_int(r['Номер контракта']),
                    r['Наименование товара'].strip(),
                    lot,
                    r['Единица измерения'].strip(),
                    r['Регион'].strip(),
                    r['Тип контракта'].strip(),
                    r['Форма контракта'].strip(),
                    r['Состояние сделки'].strip(),
                    r['ИНН продавца'].strip(),
                    r['ИНН покупателя'].strip(),
                    r['Брокер продавца'].strip(),
                    r['Брокер покупателя'].strip(),
                    parse_date(r['Дата оплаты']),
                    parse_date(r['Дата поставки']),
                    parse_int(r['Поставлено']),
                    vol,
                    uprice
                ))

                if len(batch) >= batch_size:
                    cur.executemany("INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", batch)
                    total_deals += len(batch)
                    print(f"    Inserted {total_deals:,} deals so far...")
                    batch = []

    if batch:
        cur.executemany("INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", batch)
        total_deals += len(batch)

    print(f"  Total deals loaded: {total_deals:,}")

    # 6. CREATE INDEXES
    print("Creating indexes...")
    indexes = [
        "CREATE INDEX idx_deals_date ON deals(deal_date);",
        "CREATE INDEX idx_deals_product ON deals(product_name);",
        "CREATE INDEX idx_deals_seller ON deals(seller_inn);",
        "CREATE INDEX idx_deals_buyer ON deals(buyer_inn);",
        "CREATE INDEX idx_deals_contract ON deals(contract_number);",
        "CREATE INDEX idx_deals_status ON deals(deal_status);",
        "CREATE INDEX idx_deals_region ON deals(region);",
        "CREATE INDEX idx_deals_ctype ON deals(contract_type);",
        "CREATE INDEX idx_contracts_seller ON contracts(seller_inn);",
        "CREATE INDEX idx_contracts_pname ON contracts(product_name);",
        "CREATE INDEX idx_participants_name ON participants(name);",
        "CREATE INDEX idx_brokers_code ON brokers(broker_code);"
    ]
    for idx_sql in indexes:
        cur.execute(idx_sql)

    conn.commit()
    conn.close()

    db_size = os.path.getsize(DB_PATH) / 1024 / 1024
    elapsed = time.time() - start_time
    print(f"\nSUCCESS! Database created in {elapsed:.1f}s.")
    print(f"File size: {db_size:.2f} MB at {DB_PATH}")

if __name__ == '__main__':
    build_database()
