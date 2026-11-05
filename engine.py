import re
import json
import time
from typing import Dict, Any, Tuple, Optional
import httpx
from config import GEMINI_API_KEY, GROQ_API_KEY, DEFAULT_GEMINI_MODEL
from db import db_client
from schema_desc import SCHEMA_PROMPT

# Import Google GenAI
try:
    from google import genai
    from google.genai import types
    GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception:
    GENAI_CLIENT = None

UZBEK_MARKERS = [
    "o‘", "o'", "g‘", "g'", "sh", "ch", "qancha", "qaysi", "necha", "kim", 
    "yil", "yilda", "bitim", "shartnoma", "sotuvchi", "xaridor", "narx", "summa",
    "viloyat", "tuman", "bekor", "eng ko'p", "eng kam", "hajm", "dollarda", "so'mda"
]

def detect_language(text: str) -> str:
    text_lower = text.lower()
    score = sum(1 for m in UZBEK_MARKERS if m in text_lower)
    return "uz" if score >= 1 else "ru"

def clean_sql(raw: str) -> str:
    """Extracts SQL statement from LLM output."""
    raw = raw.strip()
    match = re.search(r'```(?:sql)?\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if match:
        raw = match.group(1).strip()
    # Remove leading/trailing non-SELECT text
    select_idx = raw.upper().find("SELECT")
    if select_idx != -1:
        raw = raw[select_idx:]
    return raw.strip().rstrip(';')

def is_domain_question(query: str) -> bool:
    """Checks if the query is related to commodity exchange, transactions, goods, companies, or brokers."""
    q = query.lower()
    keywords = [
        "сделк", "контракт", "битим", "шартнома", "товар", "продукт", "цена", "нарх",
        "сумма", "объем", "hajm", "инн", "stir", "брокер", "продавец", "покупатель",
        "сотувчи", "харидор", "курс", "доллар", "экспорт", "спот", "форвард", "фьючерс",
        "регион", "вилоят", "цемент", "sement", "сахар", "shakar", "пшениц", "bug'doy",
        "пахта", "хлопок", "газ", "бензин", "дизел", "карбамид", "аукцион", "2022", "2023",
        "2024", "2025", "2026", "состояние", "ҳолат", "тн вэд", "lot", "лот"
    ]
    return any(k in q for k in keywords)

async def generate_sql_gemini(prompt: str, model_name: str = DEFAULT_GEMINI_MODEL) -> Optional[str]:
    """Generates SQL query using Gemini API."""
    global GENAI_CLIENT
    if not GEMINI_API_KEY:
        return None
        
    try:
        if GENAI_CLIENT is None:
            from google import genai
            GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
            
        full_prompt = f"{SCHEMA_PROMPT}\n\nUser Question:\n{prompt}\n\nSQL Query:"
        response = GENAI_CLIENT.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config={"temperature": 0.0, "max_output_tokens": 800}
        )
        if response and response.text:
            return clean_sql(response.text)
    except Exception as e:
        print(f"Gemini API error: {e}")
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

async def format_answer_gemini(query: str, sql: str, columns: list, rows: list, lang: str) -> Optional[str]:
    """Uses Gemini to format the final grounded answer in UZ or RU."""
    global GENAI_CLIENT
    if not GEMINI_API_KEY:
        return None
    try:
        if GENAI_CLIENT is None:
            from google import genai
            GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)

        lang_instruction = (
            "Javobni O'ZBEK tilida, aniq, qisqa va faktlarga tayangan holda bering. Raqamlarni aniq ko'rsating."
            if lang == "uz" else
            "Ответьте на РУССКОМ языке, четко, кратко, строго на основе приведенных данных. Указывайте точные цифры."
        )

        data_preview = {
            "columns": columns,
            "row_count": len(rows),
            "rows": rows[:15]
        }

        prompt = f"""
Siz UZEX birja tahlilchisi agentsiz.
Foydalanuvchi savoli: "{query}"

Bajarilgan SQL so'rov:
{sql}

Ma'lumotlar bazasidan olingan natijalar:
{json.dumps(data_preview, ensure_ascii=False, indent=2)}

QOIDALAR:
1. {lang_instruction}
2. Faqat taqdim etilgan ma'lumotlarga tayaning! Hech narsani o'zingizdan to'qimang.
3. Katta raqamlarni chiroyli formatda bering (masalan: 1 250 000 000 so'm yoki 1,25 mlrd so'm).
4. Agar natijada kompaniya nomi, STIR yoki shartnoma raqami bo'lsa, ularni aniq ko'rsating.
"""
        response = GENAI_CLIENT.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config={"temperature": 0.2, "max_output_tokens": 1000}
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"Gemini Answer Formatter error: {e}")
    return None

def fallback_format_table(columns: list, rows: list, lang: str) -> str:
    """Deterministic fallback formatter if LLM is unavailable."""
    if not rows:
        return (
            "Taqdim etilgan maʼlumotlar bazasida bu soʻrov boʻyicha maʼlumot topilmadi."
            if lang == "uz" else
            "В предоставленных данных информация по данному запросу отсутствует."
        )
    
    header = "Topilgan natijalar:" if lang == "uz" else "Найденные результаты:"
    lines = [f"**{header}**\n"]
    for i, r in enumerate(rows[:10], 1):
        item_parts = []
        for col_name, val in zip(columns, r):
            if isinstance(val, (int, float)):
                formatted_val = f"{val:,.2f}".replace(",", " ") if isinstance(val, float) else f"{val:,}".replace(",", " ")
            else:
                formatted_val = str(val) if val is not None else "-"
            item_parts.append(f"{col_name}: **{formatted_val}**")
        lines.append(f"{i}. " + " | ".join(item_parts))
    
    if len(rows) > 10:
        more = f"\n_...va yana {len(rows)-10} ta yozuv_" if lang == "uz" else f"\n_...и еще {len(rows)-10} записей_"
        lines.append(more)
        
    return "\n".join(lines)

class AgentEngine:
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()
        user_query = user_query.strip()
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

        # 5. Format Answer
        formatted_answer = await format_answer_gemini(
            user_query, sql, exec_res["columns"], exec_res["rows"], lang
        )
        if not formatted_answer:
            formatted_answer = fallback_format_table(exec_res["columns"], exec_res["rows"], lang)

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
