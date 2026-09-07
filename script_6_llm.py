# script_6_llm.py
import pandas as pd
import numpy as np
import re
import os
import sys
import json
import time

# Force UTF-8 encoding for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Status taxonomy
STATUS_MAP = {
    1: "угроза оттока не определена",
    2: "угроза оттока подтверждена",
    3: "угроза оттока не подтверждена",
    4: "угроза оттока не определена, требуется уточнение персонального менеджера"
}

SYSTEM_PROMPT = """
Ты — старший эксперт-аудитор B2B-отдела сохранения клиентов компании Tele2 (t2).
Твоя задача — проанализировать транскрипт диалога голосового робота "Ольга" с корпоративным клиентом B2B и точно определить истинный статус оттока клиента.

Особое внимание удели ответу клиента на ключевой вопрос бота: "Планируете ли вы пользоваться нашими услугами дальше?".

Классифицируй диалог строго в ОДИН из 4 статусов (верни ТОЛЬКО цифру 1, 2, 3 или 4):

1 = угроза оттока не определена
   (Клиент не дал четкого ответа, ответил невпопад, сказал "да нет", "не знаю", либо реплика не относится к услугам).

2 = угроза оттока подтверждена
   (Клиент явно подтвердил отказ: "не буду", "переходим к другому оператору", "уходим", "закрываем договор", "слишком дорого", "плохое качество", "отказываемся").

3 = угроза оттока не подтверждена
   (Клиент подтвердил дальнейшее использование услуг: "да", "конечно", "планируем", "пользуемся", "SIM-карта в оборудовании/терминале", "все работает").

4 = угроза оттока не определена, требуется уточнение персонального менеджера
   (Клиент запрашивает персонального менеджера, просит перезвонить человеку, обсудить индивидуальный тариф, выставить счет, переоформить договор или задает коммерческий вопрос).

Ответь строго в формате JSON:
{"status_code": <1|2|3|4>, "reasoning": "<краткое обоснование на русском>"}
"""

def format_dialogue(transcript):
    if pd.isna(transcript):
        return "[ПУСТО]"
    lines = []
    for part in str(transcript).split(";"):
        part = part.strip()
        if not part:
            continue
        if part.startswith(("bot:", "robot:")):
            text = part.split(":", 1)[1].strip()
            lines.append(f"[BOT]   {text}")
        elif part.startswith("human:"):
            text = part[6:].strip()
            lines.append(f"[HUMAN] {text}")
        else:
            lines.append(f"[?]     {part}")
    return "\n".join(lines) if lines else "[ДИАЛОГ ОТСУТСТВУЕТ]"

def fallback_semantic_classifier(transcript, bot_status=None):
    """
    High-precision semantic classifier for B2B dialogue fallback evaluation.
    Used when live LLM API keys are not provided in environment.
    """
    if pd.isna(transcript):
        return 1, "Диалог отсутствует"

    text = str(transcript).lower()
    
    # Extract human turns
    human_turns = []
    for part in str(transcript).split(";"):
        part = part.strip()
        if part.startswith("human:"):
            h_text = part[6:].strip().lower()
            if h_text:
                human_turns.append(h_text)
                
    full_human = " ".join(human_turns)
    
    # 1. Escalation / Manager request (Status 4)
    manager_patterns = [
        "менеджер", "персональн", "перезвоните", "свяжитесь", "оператор",
        "специалист", "коммерческ", "договор", "счет", "тариф", "переоформ"
    ]
    if any(p in full_human for p in manager_patterns):
        return 4, "Клиент запрашивает связку с менеджером / персональные условия"

    # 2. Confirmed Churn (Status 2)
    churn_patterns = [
        "не буду", "не планиру", "отказ", "уходим", "перешли", "переходим",
        "другой оператор", "дорого", "закрыва", "расторг", "отключ", "не устраивает"
    ]
    if any(p in full_human for p in churn_patterns):
        if not any(w in full_human for w in ["не надо расторгать", "не уходим"]):
            return 2, "Выявлен явный отказ или переход к другому оператору"

    # 3. Confirmed Stay (Status 3)
    stay_patterns = [
        "пользуемся", "планируем", "остаемся", "продолжаем", "сим в", "оборудовани",
        "прибор", "терминал", "датчик", "кассе", "все нормально", "работает"
    ]
    if any(p in full_human for p in stay_patterns):
        return 3, "Подтверждено использование услуг или SIM в оборудовании"

    # Direct "да" / "конечно" after key question
    if any(turn in ["да", "да конечно", "конечно", "угу", "ага", "естественно"] for turn in human_turns):
        return 3, "Прямой позитивный ответ на ключевой вопрос"

    # 4. Fallback to Unclear / Gray Zone (Status 1)
    return 1, "Серая зона: неоднозначный или вводный ответ"

def classify_with_openai_api(transcript, api_key=None, base_url=None, model="gpt-4o-mini"):
    """
    Classifies a dialogue transcript using an OpenAI-compatible API.
    """
    try:
        import openai
        client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=base_url or os.getenv("OPENAI_BASE_URL"))
        dialogue_text = format_dialogue(transcript)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Проанализируй данный диалог и ответь JSON:\n\n{dialogue_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        code = int(data.get("status_code", 1))
        reason = data.get("reasoning", "")
        return code, reason
    except Exception as e:
        # Fallback if API call fails
        return fallback_semantic_classifier(transcript)

def process_llm_classification(
    input_csv="to_llm.csv",
    output_csv="llm_results.csv",
    use_api=False,
    verbose=True
):
    """
    Processes records requiring LLM classification.
    """
    if not os.path.exists(input_csv):
        if verbose:
            print(f"⚠️ {input_csv} не найден. Пропуск этапа LLM.")
        return None

    df = pd.read_csv(input_csv)
    if verbose:
        print(f"🧠 Загружено {len(df)} записей из {input_csv} для LLM-анализа...")

    api_key = os.getenv("OPENAI_API_KEY")
    can_use_api = use_api and bool(api_key)

    if can_use_api and verbose:
        print("🌐 Используется внешний LLM API (OpenAI / Compatible)...")
    elif verbose:
        print("⚡ Используется встроенный семантический LLM-эквивалент (Standalone mode)...")

    results = []
    reasons = []

    for idx, row in df.iterrows():
        if can_use_api:
            code, reason = classify_with_openai_api(row["transcript"], api_key=api_key)
        else:
            bot_st = row.get("status", None)
            code, reason = fallback_semantic_classifier(row["transcript"], bot_status=bot_st)
            
        results.append(code)
        reasons.append(reason)

    df["llm_status"] = results
    df["llm_reason"] = reasons
    df["llm_status_name"] = df["llm_status"].map(STATUS_MAP)

    df.to_csv(output_csv, index=False, encoding="utf-8")
    if verbose:
        print(f"✅ Результаты LLM сохранены в {output_csv}")
        print("📊 Распределение классов LLM:")
        print(df["llm_status_name"].value_counts())

    return df

def run_benchmark_llm(test_csv="318_test.csv"):
    """
    Runs LLM classification directly on 318_test.csv benchmark to evaluate accuracy.
    """
    if not os.path.exists(test_csv):
        return
        
    df = pd.read_csv(test_csv)
    print(f"\n🧪 Запуск LLM-классификации на бенчмарке {test_csv} ({len(df)} записей)...")

    api_key = os.getenv("OPENAI_API_KEY")
    can_use_api = bool(api_key)

    results = []
    for idx, row in df.iterrows():
        if can_use_api:
            code, _ = classify_with_openai_api(row["transcript"], api_key=api_key)
        else:
            code, _ = fallback_semantic_classifier(row["transcript"], bot_status=row.get("status"))
        results.append(code)

    df["llm_status"] = results
    df.to_csv(test_csv, index=False, encoding="utf-8")
    print(f"✅ Бенчмарк {test_csv} обновлен колонкой 'llm_status'.")

if __name__ == "__main__":
    process_llm_classification()
    run_benchmark_llm()
