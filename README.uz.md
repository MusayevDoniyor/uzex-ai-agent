# 🏛️ UZEX AI Agent — OʻzRTXB Birja Bitimlari Tahlili

**UZEX AI Hackathon 2026** saralash bosqichi uchun ishlab chiqilgan tahliliy AI-agent.
Tizim Oʻzbekiston respublika tovar-xom ashyo birjasining 2022–2026 yillardagi **500 000 ta birja bitimi**, shartnoma kartochkalari, savdo ishtirokchilari, brokerlar va kunlik AQSh dollari kurslari asosida ishlaydi.

🌐 **English README:** [README.md](README.md)  
🌐 **GitHub:** [https://github.com/MusayevDoniyor/uzex-ai-agent](https://github.com/MusayevDoniyor/uzex-ai-agent)

---

## ⚡ Asosiy Imkoniyatlar

1. **Aniq va faktlarga asoslangan (Zero Hallucination Guarantee):**
   - Agent javoblarni faqatgina SQL orqali maʼlumotlar bazasidan olingan haqiqiy yozuvlar asosida shakllantiradi.
   - Agar soʻralgan maʼlumot bazada mavjud boʻlmasa (masalan, roʻyxatda yoʻq tovar yoki korxona), agent qatʼiy ravishda:
     - 🇺🇿 *"Taqdim etilgan birja maʼlumotlarida bu soʻrov boʻyicha maʼlumot topilmadi."*
     - 🇷🇺 *"В предоставленных биржевых данных информация по данному запросу отсутствует."*
     deb javob qaytaradi va hech qachon raqam toʻqimaydi.

2. **Ikki tilli (Bilingual RU + UZ) va Koʻp provayderli LLM arxitekturasi:**
   - Oʻzbek va rus tillaridagi savollarni tabiiy tushunadi va savol berilgan tilda mukammal javob beradi.
   - Asosiy LLM: Google Gemini (`gemini-2.5-flash-lite`, `gemini-2.5-flash`).
   - Rezerv LLM: Groq Llama-3.3-70B (`llama-3.3-70b-versatile`).
   - Deterministik qoidali zaxira moduli (Rule-based Fallback) API limiti oshganda ham javob beradi.

3. **Model Context Protocol (MCP) Serveri:**
   - Claude Code, Cursor, Codex va Agensi.io agentlari toʻgʻridan-toʻgʻri UZEX tahlil vositalarini chaqira oladi.
   - 4 ta asosiy vosita: `query_uzex_market`, `lookup_deal`, `get_commodity_trends`, `get_usd_exchange_rate`.

4. **Yuqori tezlik (High Performance):**
   - 500 000 ta qatordan iborat bazada murakkab agregatsiya va JOIN soʻrovlari **80–120 millisekundda** bajariladi.
   - Umumiy javob qaytish vaqti: **1–3 soniya** (komissiya talabidagi 90 soniyadan ancha tez).

5. **Shaffoflik va asoslanganlik (Data Provenance):**
   - Har bir javob tagida bajarilgan aniq SQL soʻrov va sarflangan vaqt koʻrsatiladi.

---

## 🏗️ Tizim Arxitekturasi

```mermaid
flowchart TD
    User["👤 Foydalanuvchi / Agent / API\n(Telegram, Web, MCP, Claude/Cursor)"] --> Router["🌐 Til va Domen Tekshiruvi"]
    Router --> Prompt["📋 Sxema va Few-shot Generator"]
    Prompt --> LLM{"🧠 LLM Provayderi"}
    LLM -->|Asosiy| Gemini["Google Gemini\n(gemini-2.5-flash-lite)"]
    LLM -->|Rezerv (429 / Timeout)| Groq["Groq Cloud\n(llama-3.3-70b)"]
    LLM -->|API mavjud bo'lmasa| RuleEngine["⚙️ Deterministik Qoidalar Zaxirasi"]
    Gemini --> Validator["🛡️ Xavfsizlik Tekshiruvi (Read-only SELECT)"]
    Groq --> Validator
    RuleEngine --> Validator
    Validator --> DB[("🗄️ SQLite Ma'lumotlar Bazasi\n500 000 ta bitim + 12 ta indeks")]
    DB -->|Natija 0 ta bo'lsa| Refusal["🚫 Qat'iy Rad Javobi (No Hallucination)"]
    DB -->|Natija topilsa| Formatter["📝 Natijani Formatlash + Asoslar"]
    Refusal --> Response["💬 Yakuniy Javob"]
    Formatter --> Response
    Response --> User
```

---

## 📊 Maʼlumotlar Bazasi Tuzilishi

* `deals`: 500 000 ta bitim (2022–2026 yillar). Maydonlar: raqam, sana, vaqt, auksion turi, hajm, summa, narx, shartnoma, tovar, oʻlchov birligi, viloyat, holat, sotuvchi/xaridor STIR, brokerlar, toʻlov/yetkazish sanalari.
* `contracts`: 6 616 ta shartnoma kartochkasi. Tovar guruhi, toifasi, TIFT kodi (TN VED), toʻlov va yetkazib berish kunlari, garov foizi, ombor manzili.
* `participants`: 14 392 ta kompaniya (sotuvchilar va xaridorlar). Nomi, STIR, viloyati, faoliyat turi, QQS toʻlovchi maqomi.
* `brokers`: 120 ta brokerlik idorasi (kod, nom, STIR, viloyat).
* `usd_rates`: 1 765 kunlik Markaziy bank dollar kursi (eksport bitimlarini soʻmga oʻgirish uchun).

---

## 🚀 Ishga Tushirish

### 1. Talablar:
- Python 3.10+
- Google Gemini API Key yoki Groq API Key

### 2. Oʻrnatish:
```bash
git clone https://github.com/MusayevDoniyor/uzex-ai-agent.git
cd uzex-ai-agent
pip install -r requirements.txt
```

### 3. Maʼlumotlar bazasini tayyorlash:
**Variant A: Tezkor sinov (CI/CD va mahalliy testlar uchun, <1 soniya):**
```bash
python build_sample_db.py
```

**Variant B: Toʻliq 500 000 bitimli haqiqiy baza (15 soniya):**
```bash
python build_db.py
```

### 4. Sozlamalar (`.env` fayli):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here (ixtiyoriy)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here (ixtiyoriy)
PORT=8000
```

### 5. MCP Serverini ishga tushirish (Claude Code / Cursor uchun):
```bash
python mcp_server.py
```

### 6. Veb-servisni ishga tushirish:
```bash
python app.py
```
Brauzerda oching: `http://localhost:8000` (Swagger hujjatlari: `http://localhost:8000/docs`).

### 7. Avtotestlarni yurgazish:
```bash
pytest tests/ -v
```

---

## 🧪 Misol Savollar

| Savol turi | Savol matni | Kutilgan natija |
| :--- | :--- | :--- |
| **Broker tahlili** | `BK001 brokeri orqali jami qancha bitim tuzilgan?` | Bitimlar soni va jami soʻmdagi aylanma |
| **Yetakchi sotuvchi** | `2025-yilda eng koʻp sement sotgan kompaniya qaysi?` | Kompaniya nomi va umumiy savdo summasi |
| **Shartnoma kartochkasi** | `№100050 shartnoma boʻyicha toʻlov va yetkazib berish muddati qancha?` | Toʻlov kunlari, yetkazish kunlari va ombor manzili |
| **Eksport aylanmasi** | `2024-yil avgust oyidagi eksport bitimlarining soʻmdagi umumiy hajmi qancha?` | USD bitimlar Markaziy bank kursi bilan hisoblangan soʻm summasi |
| **Bekor qilinganlar** | `Qancha bitim bekor qilingan (annulirovan)?` | Bekor qilingan bitimlar soni va umumiy summasi |
| **Bazada yoʻq maʼlumot** | `Oltin narxi bugun qancha boʻldi?` | Qatʼiy rad javobi (hech qanday gallyutsinatsiyasiz) |

---

## 📄 Litsenziya
MIT License — Doniyor Musayev.
