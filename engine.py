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

CONVERSATIONAL_WORDS = [
    "salom", "assalom", "qalesan", "qalaysan", "yaxshimisan", "tinchmisiz", "nima gap",
    "qandaysiz", "zo'r", "zor", "yaxshi", "rahmat", "charchama", "ha", "yo'q", "yoq", "ok",
    "gaplashaylik", "sen kimsan", "kim yaratgan", "vazifang", "nima qila olasan", "tushundim",
    "привет", "здравствуй", "добрый день", "как дела", "отлично", "хорошо", "спасибо", "кто ты"
]

def detect_language(text: str) -> str:
    """Accurately detects language based on script and characters."""
    text_clean = text.strip()
    if re.search(r'[ўқғҳЎҚҒҲ]', text_clean):
        return 'uz'
    cyrillic_chars = len(re.findall(r'[а-яА-ЯёЁ]', text_clean))
    latin_chars = len(re.findall(r'[a-zA-Z]', text_clean))
    if cyrillic_chars > latin_chars:
        return 'ru'
    return 'uz'

def is_conversational(query: str) -> bool:
    q = query.lower()
    return any(w in q for w in CONVERSATIONAL_WORDS) or len(q.split()) <= 2 and not any(k in q for k in DOMAIN_KEYWORDS)

def is_domain_question(query: str) -> bool:
    q = query.lower()
    if re.search(r'\bbk\d{1,4}\b', q):
        return True
    if re.search(r'\b\d{9}\b', q):
        return True
    if re.search(r'\b10\d{4}\b', q):
        return True
    if any(k in q for k in DOMAIN_KEYWORDS):
        return True
    if any(yr in q for yr in ["2022", "2023", "2024", "2025", "2026"]):
        return True
    return False

def clean_sql(raw: str) -> str:
    raw = raw.strip()
    match = re.search(r'```(?:sql)?\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if match:
        raw = match.group(1).strip()
    select_idx = raw.upper().find("SELECT")
    if select_idx != -1:
        raw = raw[select_idx:]
    return raw.strip().rstrip(';')

async def chat_with_ai(query: str, lang: str) -> str:
    """Natural, intelligent conversation using Gemini Flash Lite."""
    global GENAI_CLIENT
    if GENAI_CLIENT is None and GEMINI_API_KEY:
        try:
            from google import genai
            GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            pass

    system_prompt = (
        "Siz Oʻzbekiston respublika tovar-xom ashyo birjasi (UZEX) AI Hackathon 2026 uchun yaratilgan "
        "aqlli, professional va samimiy AI-agentsiz. Foydalanuvchi bilan tabiiy, doʻstona tilda gaplashing. "
        "Siz 2022–2026 yillardagi 500 000 ta birja bitimi, shartnomalar, tovarlar (sement, paxta, bugʻdoy va h.k.), "
        "brokerlar va dollar kurslari boʻyicha aniq tahliliy maʼlumot bera olasiz. "
        "Foydalanuvchi qaysi tilda yozsa, oʻsha tilda (oʻzbek yoki rus) qisqa, jonli va samimiy javob bering."
    )

    models_to_try = [DEFAULT_GEMINI_MODEL] + FALLBACK_GEMINI_MODELS
    for model_name in models_to_try:
        try:
            full_prompt = f"{system_prompt}\n\nFoydalanuvchi: {query}\nJavob:"
            resp = await asyncio.wait_for(
                GENAI_CLIENT.aio.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config={"temperature": 0.6, "max_output_tokens": 400}
                ),
                timeout=6.0
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            continue

    # Fallback if no LLM responded
    return (
        "👋 Assalomu alaykum! Hammasi ajoyib, rahmat. Men UZEX birja bitimlari (2022–2026) boʻyicha AI-agentman. "
        "Birja savdolari, shartnomalar yoki tovarlar haqida istalgan savolingizni berishingiz mumkin!"
        if lang == "uz" else
        "👋 Здравствуйте! Я AI-агент по сделкам биржи UZEX (2022–2026 гг.). Задайте мне любой вопрос о биржевых торгах, товарах или контрактах!"
    )

async def generate_sql_gemini(prompt: str) -> Optional[str]:
    """Generates SQL query using Gemini Async API."""
    global GENAI_CLIENT
    if not GEMINI_API_KEY:
        return None

    if GENAI_CLIENT is None:
        try:
            from google import genai
            GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            return None

    models_to_try = [DEFAULT_GEMINI_MODEL] + FALLBACK_GEMINI_MODELS
    full_prompt = f"{SCHEMA_PROMPT}\n\nUser Question:\n{prompt}\n\nSQL Query:"

    for model_name in models_to_try:
        try:
            response = await asyncio.wait_for(
                GENAI_CLIENT.aio.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config={"temperature": 0.0, "max_output_tokens": 600}
                ),
                timeout=7.0
            )
            if response and response.text:
                sql = clean_sql(response.text)
                if sql.upper().startswith("SELECT"):
                    return sql
        except Exception as e:
            continue

    return None

async def format_answer_gemini(query: str, sql: str, columns: list, rows: list, lang: str) -> Optional[str]:
    """Generates a rich, natural, professional market analyst brief using Gemini."""
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
        "Javobni OʻZBEK tilida, professional birja tahlilchisi sifatida, toʻliq va chiroyli jumlalar bilan tushuntirib bering. "
        "Raqamlarni aniq va tushunarli keltiring (masalan: 81 238 709 705 soʻm yoki taxminan 81.24 milliard soʻm)."
        if lang == "uz" else
        "Ответьте на РУССКОМ языке как профессиональный биржевой аналитик, полными связными предложениями. "
        "Приведите точные цифры и поясните их (например, 81 238 709 705 сумов или около 81.24 млрд сумов)."
    )

    data_preview = {
        "columns": columns,
        "row_count": len(rows),
        "rows": rows[:10]
    }

    prompt = f"""
Siz Oʻzbekiston respublika tovar-xom ashyo birjasi (UZEX) rasmiy tahlilchisisiz.
Foydalanuvchi savoli: "{query}"

Bajarilgan SQL soʻrov:
{sql}

Baza natijalari:
{json.dumps(data_preview, ensure_ascii=False, indent=2)}

QOIDALAR:
1. {lang_instruction}
2. Faqat taqdim etilgan maʼlumotlarga tayaning! Hech qanday raqam toʻqimang.
3. Shartnoma raqami, kompaniya nomi yoki STIR mavjud boʻlsa, albatta koʻrsating.
4. Javobingiz quruq roʻyxat emas, balki tabiiy va mazmunli tahliliy hisobot boʻlsin.
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
                timeout=8.0
            )
            if response and response.text:
                return response.text.strip()
        except Exception:
            continue

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

def deterministic_format(columns: List[str], rows: List[List[Any]], lang: str, query: str) -> str:
    """Fallback deterministic response builder."""
    if not rows:
        return (
            "Taqdim etilgan maʼlumotlar bazasida bu soʻrov boʻyicha maʼlumot topilmadi."
            if lang == "uz" else
            "В предоставленных данных информация по данному запросу отсутствует."
        )

    if len(rows) == 1 and len(columns) == 1:
        val = rows[0][0]
        f_val = format_number(val)
        return (
            f"Tahlil natijasiga koʻra, jami koʻrsatkich: **{f_val}**."
            if lang == "uz" else
            f"Согласно анализу данных, общий показатель составил: **{f_val}**."
        )

    lines = ["**Tahlil natijalari:**\n" if lang == "uz" else "**Результаты анализа:**\n"]
    for i, r in enumerate(rows[:10], 1):
        parts = [f"{col}: **{format_number(val)}**" for col, val in zip(columns, r)]
        lines.append(f"{i}. " + " | ".join(parts))
    return "\n".join(lines)

class AgentEngine:
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()
        user_query = re.sub(r"[ʻ’‘`´ʹ′]", "'", user_query.strip())
        lang = detect_language(user_query)

        # 1. Natural Conversation / Small Talk Check
        if is_conversational(user_query) and not is_domain_question(user_query):
            chat_reply = await chat_with_ai(user_query, lang)
            return {
                "answer": chat_reply,
                "sql": None,
                "data": [],
                "columns": [],
                "language": lang,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "status": "conversation"
            }

        # 2. Domain Check
        if not is_domain_question(user_query):
            refusal = (
                "Taqdim etilgan birja maʼlumotlar bazasida bu mavzu boʻyicha maʼlumot mavjud emas. "
                "Agent faqat OʻzRTXB (UZEX) 2022–2026 yillardagi birja bitimlari boʻyicha savollarga javob beradi."
                if lang == "uz" else
                "В предоставленной биржевой базе данных информация по данной теме отсутствует. "
                "Агент отвечает только на вопросы по сделкам биржи УзРТСБ (UZEX) за 2022–2026 гг."
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

        # 3. SQL Generation (Gemini with Rule Fallback)
        sql = await generate_sql_gemini(user_query)
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

        # 4. Database Execution
        exec_res = db_client.execute_query(sql)

        # 5. Handle Empty Results (Zero Hallucination Guard)
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

        # 6. Format Answer (AI-powered analytical summary)
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
