import asyncio
import re
import json
import time
from typing import Dict, Any, Tuple, Optional, List
import httpx
from config import GEMINI_API_KEY, GROQ_API_KEY, DEFAULT_GEMINI_MODEL, FALLBACK_GEMINI_MODELS
from db import db_client
from schema_desc import SCHEMA_PROMPT
from rule_fallback import rule_based_sql_fallback


try:
    from google import genai
    GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception:
    GENAI_CLIENT = None


UZBEK_MARKERS = [
    "o‘", "o'", "g‘", "g'", "sh", "ch", "qancha", "qaysi", "necha", "kim", 
    "yil", "yilda", "bitim", "shartnoma", "sotuvchi", "xaridor", "narx", "summa",
    "viloyat", "tuman", "bekor", "eng ko'p", "eng kam", "hajm", "dollarda", "so'mda",
    "bo'yicha", "haqida", "qilingan", "tuzilgan", "sotgan", "olgan"
]

DOMAIN_KEYWORDS = [
    # Uzbek Latin
    "bitim", "shartnoma", "sotuvchi", "xaridor", "broker", "narx", "summa", "hajm",
    "tovar", "mahsulot", "stir", "inn", "dollar", "so'm", "som", "eksport", "import",
    "spot", "forvard", "fyuchers", "auksion", "bekor", "bajarilgan", "to'langan", "yangi",
    "sement", "shakar", "bug'doy", "paxta", "benzin", "dizel", "gaz", "alyuminiy",
    "mis", "armatura", "selitra", "karbamid", "un", "moy", "kompaniya", "viloyat", "ombor",
    # Russian Cyrillic
    "сделк", "контракт", "договор", "продавец", "покупатель", "брокер", "цена", "стоимост",
    "сумма", "объем", "товар", "продукт", "инн", "стир", "курс", "доллар", "сум", "экспорт",
    "спот", "форвард", "фьючерс", "аукцион", "аннулирован", "исполнен", "оплачен", "новый",
    "цемент", "сахар", "пшениц", "хлопок", "бензин", "дизел", "газ", "алюмин", "мед",
    "арматур", "селитр", "карбамид", "мука", "масло", "компани", "предприяти", "регион", "склад",
    # Uzbek Cyrillic
    "битим", "шартнома", "сотувчи", "харидор", "нарх", "ҳажм", "бекор", "сўм"
]

def detect_language(text: str) -> str:
    text_lower = text.lower()
    score = sum(1 for m in UZBEK_MARKERS if m in text_lower)
    return "uz" if score >= 1 else "ru"

def is_domain_question(query: str) -> bool:
    """Checks if the query is related to commodity exchange, transactions, goods, companies, or brokers."""
    q = query.lower()
    
    # Check for broker codes (e.g., BK001, BK120)
    if re.search(r'\bbk\d{1,4}\b', q):
        return True
    # Check for 9-digit INN
    if re.search(r'\b\d{9}\b', q):
        return True
    # Check for contract number format (6-digit starting with 10)
    if re.search(r'\b10\d{4}\b', q):
        return True
    # Check for keywords
    if any(k in q for k in DOMAIN_KEYWORDS):
        return True
    # Check for exchange years
    if any(yr in q for yr in ["2022", "2023", "2024", "2025", "2026"]):
        return True
        
    return False

def clean_sql(raw: str) -> str:
    """Extracts SQL statement from LLM output."""
    raw = raw.strip()
    match = re.search(r'```(?:sql)?\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if match:
        raw = match.group(1).strip()
    select_idx = raw.upper().find("SELECT")
    if select_idx != -1:
        raw = raw[select_idx:]
    return raw.strip().rstrip(';')

async def generate_sql_gemini(prompt: str) -> Optional[str]:
    """Generates SQL query using Gemini Async API with fast timeout and fallback."""
    global GENAI_CLIENT
    if not GEMINI_API_KEY:
        return None

    if GENAI_CLIENT is None:
        try:
            from google import genai
            GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"Failed to create GenAI client: {e}")
            return None

    models_to_try = [DEFAULT_GEMINI_MODEL] + FALLBACK_GEMINI_MODELS
    full_prompt = f"{SCHEMA_PROMPT}\n\nUser Question:\n{prompt}\n\nSQL Query:"

    for model_name in models_to_try:
        try:
            # 8-second timeout so it never hangs
            response = await asyncio.wait_for(
                GENAI_CLIENT.aio.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config={"temperature": 0.0, "max_output_tokens": 600}
                ),
                timeout=8.0
            )
            if response and response.text:
                sql = clean_sql(response.text)
                if sql.upper().startswith("SELECT"):
                    return sql
        except Exception as e:
            print(f"Gemini model {model_name} failed ({type(e).__name__}): {e}")
            continue

    return None


async def generate_sql_groq(prompt: str) -> Optional[str]:
    """Fallback SQL generation using Groq API."""
    if not GROQ_API_KEY:
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "qwen-2.5-coder-32b",
            "messages": [
                {"role": "system", "content": SCHEMA_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 800
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=data)
            if resp.status_code == 200:
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                return clean_sql(content)
    except Exception as e:
        print(f"Groq API error: {e}")
    return None

def format_number(val: Any) -> str:
    if isinstance(val, float):
        if val >= 1_000_000_000_000:
            return f"{val:,.2f}".replace(",", " ") + f" ({val/1e12:.2f} trln)"
        elif val >= 1_000_000_000:
            return f"{val:,.2f}".replace(",", " ") + f" ({val/1e9:.2f} mlrd)"
        elif val >= 1_000_000:
            return f"{val:,.2f}".replace(",", " ") + f" ({val/1e6:.2f} mln)"
        return f"{val:,.2f}".replace(",", " ")
    elif isinstance(val, int):
        return f"{val:,}".replace(",", " ")
    return str(val) if val is not None else "-"

COLUMN_LABELS_UZ = {
    "name": "Kompaniya nomi",
    "total_sales_sum": "Umumiy savdo summasi",
    "deals_count": "Bitimlar soni",
    "total_sum": "Umumiy summa",
    "total_sum_uzs": "Umumiy summa (soʻmda)",
    "cancelled_count": "Bekor qilingan bitimlar soni",
    "cancelled_sum": "Bekor qilingan summa",
    "payment_days": "Toʻlov muddati (kun)",
    "delivery_days": "Yetkazib berish muddati (kun)",
    "base_price": "Bazaviy narx",
    "currency": "Valyuta",
    "warehouse_address": "Ombor manzili",
    "product_name": "Tovar nomi",
    "contract_number": "Shartnoma raqami",
    "inn": "STIR (INN)",
    "region": "Viloyat / Hudud",
    "activity_type": "Faoliyat turi",
    "role": "Roli",
    "vat_payer": "QQS toʻlovchi",
    "unit_price": "Birlik narxi",
    "volume_units": "Hajm (birlikda)"
}

COLUMN_LABELS_RU = {
    "name": "Наименование компании",
    "total_sales_sum": "Общая сумма продаж",
    "deals_count": "Количество сделок",
    "total_sum": "Общая сумма",
    "total_sum_uzs": "Общая сумма (в сумах)",
    "cancelled_count": "Количество аннулированных сделок",
    "cancelled_sum": "Сумма аннулированных сделок",
    "payment_days": "Срок оплаты (дней)",
    "delivery_days": "Срок поставки (дней)",
    "base_price": "Базисная цена",
    "currency": "Валюта",
    "warehouse_address": "Адрес склада",
    "product_name": "Наименование товара",
    "contract_number": "Номер контракта",
    "inn": "ИНН",
    "region": "Регион",
    "activity_type": "Вид деятельности",
    "role": "Роль",
    "vat_payer": "Плательщик НДС",
    "unit_price": "Цена за единицу",
    "volume_units": "Объем (в единицах)"
}

def get_label(col: str, lang: str) -> str:
    col_clean = col.lower().strip()
    mapping = COLUMN_LABELS_UZ if lang == "uz" else COLUMN_LABELS_RU
    return mapping.get(col_clean, col.replace("_", " ").title())

def deterministic_format(columns: List[str], rows: List[List[Any]], lang: str, query: str) -> str:
    """Fast, accurate, deterministic response builder with polished labels."""
    if not rows:
        return (
            "Taqdim etilgan maʼlumotlar bazasida bu soʻrov boʻyicha maʼlumot topilmadi."
            if lang == "uz" else
            "В предоставленных данных информация по данному запросу отсутствует."
        )

    # Single value result (e.g. COUNT, SUM, AVG)
    if len(rows) == 1 and len(columns) == 1:
        val = rows[0][0]
        col = columns[0]
        f_val = format_number(val)
        if "count" in col.lower():
            return f"Soʻrov boʻyicha jami **{f_val}** ta bitim topildi." if lang == "uz" else f"По вашему запросу найдено всего **{f_val}** сделок."
        elif "sum" in col.lower():
            unit = "soʻm" if "usd" not in col.lower() else "USD"
            return f"Umumiy summa: **{f_val} {unit}**." if lang == "uz" else f"Общая сумма: **{f_val} {unit}**."
        elif "avg" in col.lower():
            return f"Oʻrtacha koʻrsatkich: **{f_val}**." if lang == "uz" else f"Средний показатель: **{f_val}**."
        return f"Natija: **{f_val}**." if lang == "uz" else f"Результат: **{f_val}**."

    # Single row multi-column result
    if len(rows) == 1:
        lines = ["**Tahlil natijasi:**\n" if lang == "uz" else "**Результат анализа:**\n"]
        for col, val in zip(columns, rows[0]):
            f_val = format_number(val)
            label = get_label(col, lang)
            lines.append(f"• **{label}:** {f_val}")
        return "\n".join(lines)

    # Multi-row table result (up to 10 rows)
    title = f"Topilgan natijalar ({len(rows)} ta):" if lang == "uz" else f"Найденные результаты ({len(rows)}):"
    lines = [f"**{title}**\n"]
    for i, r in enumerate(rows[:10], 1):
        item_parts = []
        for col_name, val in zip(columns, r):
            f_val = format_number(val)
            label = get_label(col_name, lang)
            item_parts.append(f"{label}: **{f_val}**")
        lines.append(f"{i}. " + " | ".join(item_parts))

    if len(rows) > 10:
        more = f"\n_...va yana {len(rows)-10} ta yozuv_" if lang == "uz" else f"\n_...и еще {len(rows)-10} записей_"
        lines.append(more)

    return "\n".join(lines)


async def format_answer_gemini(query: str, sql: str, columns: list, rows: list, lang: str) -> Optional[str]:
    """Uses Gemini Async to format the final grounded answer with timeout."""
    global GENAI_CLIENT
    if not GEMINI_API_KEY:
        return None

    if GENAI_CLIENT is None:
        try:
            from google import genai
            GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            return None

    lang_instruction = (
        "Javobni O'ZBEK tilida, aniq, qisqa va faktlarga tayangan holda bering. Raqamlarni aniq ko'rsating."
        if lang == "uz" else
        "Ответьте на РУССКОМ языке, четко, кратко, строго на основе приведенных данных. Указывайте точные цифры."
    )

    data_preview = {
        "columns": columns,
        "row_count": len(rows),
        "rows": rows[:10]
    }

    prompt = f"""
Siz UZEX birja tahlilchisi agentsiz.
Foydalanuvchi savoli: "{query}"

Bajarilgan SQL so'rov:
{sql}

Baza natijalari:
{json.dumps(data_preview, ensure_ascii=False, indent=2)}

QOIDALAR:
1. {lang_instruction}
2. Faqat taqdim etilgan ma'lumotlarga tayaning! Hech narsani o'zingizdan to'qimang.
3. Katta raqamlarni chiroyli formatda bering (masalan: 1 250 000 000 so'm yoki 1,25 mlrd so'm).
4. Kompaniya nomi, STIR yoki shartnoma raqami bo'lsa, ularni aniq ko'rsating.
"""

    models_to_try = [DEFAULT_GEMINI_MODEL] + FALLBACK_GEMINI_MODELS
    for model_name in models_to_try:
        try:
            response = await asyncio.wait_for(
                GENAI_CLIENT.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"temperature": 0.2, "max_output_tokens": 800}
                ),
                timeout=7.0
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini formatting model {model_name} failed: {e}")
            continue

    return None


class AgentEngine:
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()
        # Normalize apostrophe variations (oʻ, gʻ, o', g', o’, g’)
        user_query = re.sub(r"[ʻ’‘`´ʹ′]", "'", user_query.strip())
        lang = detect_language(user_query)


        # 1. Domain Check
        if not is_domain_question(user_query):
            refusal = (
                "Taqdim etilgan maʼlumotlar bazasida bu mavzu boʻyicha maʼlumot mavjud emas. "
                "Agent faqat OʻzRTXB (UZEX) spot, forvard va fyuchers bitimlari boʻyicha savollarga javob beradi."
                if lang == "uz" else
                "В предоставленной базе данных информация по данной теме отсутствует. "
                "Агент отвечает только на вопросы по сделкам товарно-сырьевой биржи (УзРТСБ/UZEX)."
            )
            return {
                "answer": refusal,
                "sql": None,
                "data": [],
                "columns": [],
                "language": lang,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "status": "out_of_domain"
            }

        # 2. SQL Generation
        sql = await generate_sql_gemini(user_query)
        if not sql:
            sql = await generate_sql_groq(user_query)
        if not sql:
            sql = rule_based_sql_fallback(user_query)


        if not sql:
            no_sql = (
                "Kechirasiz, soʻrov boʻyicha SQL tahlilini amalga oshirib boʻlmadi. Iltimos, savolni aniqroq bering."
                if lang == "uz" else
                "К сожалению, не удалось сформировать поисковый запрос к базе данных. Пожалуйста, уточните вопрос."
            )
            return {
                "answer": no_sql,
                "sql": None,
                "data": [],
                "columns": [],
                "language": lang,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "status": "sql_generation_failed"
            }

        # 3. Database Execution
        exec_res = db_client.execute_query(sql)

        # Retry logic if SQL failed
        if not exec_res["success"] and GEMINI_API_KEY:
            retry_prompt = (
                f"{SCHEMA_PROMPT}\n\nThe previous SQL query failed with error:\n"
                f"SQL: {sql}\nError: {exec_res['error']}\n\n"
                f"Please fix the SQL query for user question: '{user_query}'\nNew SQL Query:"
            )
            retry_sql = await generate_sql_gemini(retry_prompt)
            if retry_sql and retry_sql != sql:
                sql = retry_sql
                exec_res = db_client.execute_query(sql)

        # 4. Handle Empty Results (Zero Hallucination Guard)
        if exec_res["success"] and len(exec_res["rows"]) == 0:
            refusal = (
                "Taqdim etilgan birja maʼlumotlarida bu soʻrov boʻyicha maʼlumot topilmadi."
                if lang == "uz" else
                "В предоставленных биржевых данных информация по данному запросу отсутствует."
            )
            return {
                "answer": refusal,
                "sql": sql,
                "data": [],
                "columns": exec_res["columns"],
                "language": lang,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "status": "no_data_found"
            }

        if not exec_res["success"]:
            refusal = (
                f"Maʼlumotlar bazasida qidirishda xatolik yuz berdi: {exec_res['error']}"
                if lang == "uz" else
                f"Ошибка выполнения запроса к базе данных: {exec_res['error']}"
            )
            return {
                "answer": refusal,
                "sql": sql,
                "data": [],
                "columns": [],
                "language": lang,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "status": "execution_error"
            }

        # 5. Format Answer (LLM with deterministic fallback)
        formatted_answer = await format_answer_gemini(
            user_query, sql, exec_res["columns"], exec_res["rows"], lang
        )
        if not formatted_answer:
            formatted_answer = deterministic_format(exec_res["columns"], exec_res["rows"], lang, user_query)

        elapsed = round(time.time() - start_time, 2)
        return {
            "answer": formatted_answer,
            "sql": sql,
            "data": exec_res["rows"],
            "columns": exec_res["columns"],
            "row_count": len(exec_res["rows"]),
            "language": lang,
            "elapsed_seconds": elapsed,
            "status": "success"
        }

engine = AgentEngine()
