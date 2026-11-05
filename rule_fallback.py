import re
from typing import Optional

def normalize_text(text: str) -> str:
    return re.sub(r"[ʻ’‘`´ʹ′]", "'", text)

def rule_based_sql_fallback(query: str) -> Optional[str]:
    """
    Fallback deterministic SQL generator for common query patterns
    when LLM APIs hit 429 quota limits or rate-limiting.
    """
    q = normalize_text(query.lower())

    # 1. Broker statistics (e.g. "BK001 broker orqali qancha bitim tuzilgan?")
    broker_match = re.search(r'\b(bk\d{1,4})\b', q)
    if broker_match:
        bcode = broker_match.group(1).upper()
        return f"SELECT COUNT(*) AS deals_count, SUM(deal_sum) AS total_sum FROM deals WHERE seller_broker = '{bcode}' OR buyer_broker = '{bcode}';"

    # 2. Specific contract lookup (e.g. "№100050 shartnoma...")
    contract_match = re.search(r'\b(10\d{4})\b', q)
    if contract_match and any(k in q for k in ["shartnoma", "контракт", "kartochka"]):
        cnum = int(contract_match.group(1))
        return f"SELECT contract_number, product_name, payment_days, delivery_days, currency, base_price, warehouse_address FROM contracts WHERE contract_number = {cnum};"

    # 3. Specific company by INN / STIR (e.g. "STIR 915688255...")
    inn_match = re.search(r'\b(\d{9})\b', q)
    if inn_match and any(k in q for k in ["stir", "inn", "инн", "kompaniya", "компани"]):
        inn = inn_match.group(1)
        return f"SELECT inn, name, region, activity_type, role, vat_payer FROM participants WHERE inn = '{inn}';"

    # 4. Cancelled deals (e.g. "Qancha bitim bekor qilingan (annulirovan)?")
    if any(k in q for k in ["bekor", "аннулирован"]):
        return "SELECT COUNT(*) AS cancelled_count, SUM(deal_sum) AS cancelled_sum FROM deals WHERE deal_status = 'Аннулирован(Не оплачен)';"

    # 5. Top cement seller (e.g. "2025-yilda eng ko'p sement sotgan kompaniya va qancha summaga?")
    if ("sement" in q or "цемент" in q) and any(k in q for k in ["eng ko'p", "eng kop", "больше всего", "лидер"]):
        year = "2025"
        for yr in ["2022", "2023", "2024", "2025", "2026"]:
            if yr in q:
                year = yr
                break
        return (
            f"SELECT p.name, SUM(d.deal_sum) AS total_sales_sum "
            f"FROM deals AS d JOIN participants AS p ON d.seller_inn = p.inn "
            f"WHERE d.deal_date BETWEEN '{year}-01-01' AND '{year}-12-31' AND d.product_name LIKE '%цемент%' "
            f"GROUP BY p.name ORDER BY total_sales_sum DESC LIMIT 1;"
        )

    # 6. Top wheat/grain seller/buyer
    if ("bug'doy" in q or "пшениц" in q) and any(k in q for k in ["eng ko'p", "eng kop", "больше всего"]):
        year = "2024"
        for yr in ["2022", "2023", "2024", "2025", "2026"]:
            if yr in q:
                year = yr
                break
        return (
            f"SELECT p.name, SUM(d.deal_sum) AS total_sales_sum "
            f"FROM deals AS d JOIN participants AS p ON d.seller_inn = p.inn "
            f"WHERE d.deal_date BETWEEN '{year}-01-01' AND '{year}-12-31' AND d.product_name LIKE '%пшениц%' "
            f"GROUP BY p.name ORDER BY total_sales_sum DESC LIMIT 1;"
        )

    # 7. Export deals in UZS (e.g. "2024-yil avgust oyidagi eksport bitimlarining so'mdagi umumiy hajmi qancha?")
    if "eksport" in q or "экспорт" in q:
        month_map = {
            "yanvar": "01", "январ": "01",
            "fevral": "02", "феврал": "02",
            "mart": "03", "март": "03",
            "aprel": "04", "апрел": "04",
            "may": "05", "май": "05",
            "iyun": "06", "июн": "06",
            "iyul": "07", "июл": "07",
            "avgust": "08", "август": "08",
            "sentabr": "09", "сентябр": "09",
            "oktabr": "10", "октябр": "10",
            "noyabr": "11", "ноябр": "11",
            "dekabr": "12", "декабр": "12"
        }
        matched_month = None
        for m_name, m_num in month_map.items():
            if m_name in q:
                matched_month = m_num
                break
        matched_year = "2024"
        for yr in ["2022", "2023", "2024", "2025", "2026"]:
            if yr in q:
                matched_year = yr
                break

        if matched_month:
            return (
                f"SELECT SUM(d.deal_sum * u.rate) AS total_sum_uzs "
                f"FROM deals AS d JOIN usd_rates AS u ON d.deal_date = u.rate_date "
                f"WHERE d.contract_type = 'Экспортный' AND d.deal_date BETWEEN '{matched_year}-{matched_month}-01' AND '{matched_year}-{matched_month}-31';"
            )
        else:
            return (
                f"SELECT SUM(d.deal_sum * u.rate) AS total_sum_uzs "
                f"FROM deals AS d JOIN usd_rates AS u ON d.deal_date = u.rate_date "
                f"WHERE d.contract_type = 'Экспортный' AND d.deal_date BETWEEN '{matched_year}-01-01' AND '{matched_year}-12-31';"
            )

    return None

