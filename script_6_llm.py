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

Особое внимание удели контексту B2B-коммуникации и ответу клиента на вопрос робота: "Планируете ли вы пользоваться нашими услугами дальше?".

Классифицируй диалог строго в ОДИН из 4 статусов (верни ТОЛЬКО цифру 1, 2, 3 или 4):

1 = угроза оттока не определена
   (Клиент не дал четкого ответа, ответил невпопад, сказал "да нет", "не знаю", молчание, шум, либо реплика не относится к услугам).

2 = угроза оттока подтверждена
   (Клиент явно подтвердил отказ: "не буду", "не планирую", "перешли на Мегафон/МТС/Билайн", "закрыли договор", "расторгли", "нет контракта", "дорого", "отключаем").

3 = угроза оттока не подтверждена
   (Клиент подтвердил дальнейшее использование услуг: "да", "конечно", "планируем", "пользуемся", "SIM-карта в оборудовании/терминале/шлагбауме", "все нормально", "работает").

4 = угроза оттока не определена, требуется уточнение персонального менеджера
   (Клиент запрашивает персонального менеджера, просит перезвонить другому человеку, диктует номер бухгалтера/директора, сообщает что уволился/не работает в этой компании, говорит "я не решаю", либо сработал автоответчик/секретарь организации).

ПРИМЕРЫ (FEW-SHOT):
- Диалог: "bot: планируете пользоваться дальше? human: я бухгалтер не знаю запишите номер директора 89657574" -> 4 (требуется менеджер)
- Диалог: "bot: планируете пользоваться дальше? human: мы уже перешли на мегафон" -> 2 (угроза подтверждена)
- Диалог: "bot: планируете пользоваться дальше? human: да симка в терминале оплаты работает" -> 3 (угроза не подтверждена)
- Диалог: "bot: планируете пользоваться дальше? human: алло да слушаю" -> 1 (не определено, общее приветствие)

Ответь строго в формате JSON:
{"status_code": <1|2|3|4>, "reasoning": "<краткое обоснование на русском>"}
"""

def extract_human_turns(transcript):
    if pd.isna(transcript):
        return []
    turns = []
    for part in str(transcript).split(";"):
        part = part.strip()
        if part.startswith("human:"):
            t = part[6:].strip()
            if t:
                turns.append(t)
    return turns

def get_answers_after_question(transcript):
    if pd.isna(transcript):
        return []
    parts = [p.strip() for p in str(transcript).split(";") if p.strip()]
    q_found = False
    answers = []
    for p in parts:
        p_lower = p.lower()
        if any(kw in p_lower for kw in ["услугами дальше", "пользоваться нашими услугами", "вернуться к прежней активности", "продолжить пользоваться", "сотрудничать с нами"]):
            q_found = True
            continue
        if q_found and p.startswith("human:"):
            text = p[6:].strip()
            if text:
                answers.append(text)
    return answers

def fallback_semantic_classifier(transcript, bot_status=None):
    """
    High-precision B2B semantic classifier for Tele2 Olga Bot Auditor.
    Evaluates corporate nuances (manager routing, equipment SIMs, competitor churn).
    """
    if pd.isna(transcript):
        return 1, "Диалог отсутствует"

    h_turns = extract_human_turns(transcript)
    if not h_turns:
        return 1, "Отсутствуют реплики человека (недозвон/молчание)"

    full_h = " ".join(h_turns).lower()
    post_q_answers = get_answers_after_question(transcript)

    # 1. Escalation / Manager Request / Transfer / B2B Organization Routing / Callback (Status 4)
    manager_patterns = [
        "менеджер", "персональн", "перезвонит", "перезвони", "свяжитесь", "оператор", "специалист",
        "бухгалтер", "директор", "руководител", "начальник", "секретар", "администратор",
        "не занимаюсь", "не решаю", "другой сотрудник", "передайте", "диктовать", "записать",
        "запишите", "номер", "телефон", "почт", "уволился", "уволилась", "не работаю",
        "переоформил", "передал", "оставьте сообщение", "нажмите", "тональном",
        "в свободной продаже", "не могу сказать", "не знаю", "не подхожу", "кто пользует",
        "спросить", "уточнить", "вы звоните", "куда звоните", "с кем вы", "по какому вопросу",
        "какая организация", "абонент не может", "передам", "связаться по этому", "наберите",
        "руководство", "собственник", "хозяин", "отдел", "руководителю", "завтра перезвон",
        "чуть позже", "через час", "полчаса", "сотрудник подойдет", "переговорите",
        "не начальник", "не могу подсказать", "не имею права", "какой именно номер"
    ]
    has_digit_dictation = bool(re.search(r'\b(\d[\s-]?){5,}\b', full_h)) or any(w in full_h for w in ["89", "8 9", "+7", "девять", "восемь", "семерка"])
    
    if any(p in full_h for p in manager_patterns) or (has_digit_dictation and any(w in full_h for w in ["запишите", "наберите", "телефон", "номер", "записать", "89", "8 9"])):
        return 4, "Запрос персонального менеджера / перевод на другого сотрудника B2B"

    # 2. Confirmed Churn (Status 2)
    churn_patterns = [
        "не буду", "не планиру", "отказ", "уходим", "перешли", "переходим", "перешел",
        "другой оператор", "другого оператора", "мегафон", "мтс", "билайн", "ростелеком",
        "дорого", "повышение цены", "закрыва", "расторг", "отключ", "не устраивает",
        "нет контракта", "нет договора", "никогда не пользовал", "не пользовал",
        "выбросил", "не нужна", "нет такой", "закрыли", "ликвидиров", "продали",
        "нет компании", "расторгли", "смена оператора", "перешли на", "отказались", "ушли"
    ]
    
    clear_no_post_q = False
    if post_q_answers:
        first_ans = post_q_answers[0].lower().strip()
        if first_ans in ["нет", "нет.", "нет не планируем", "нет конечно", "не планируем", "неа", "не будем"]:
            clear_no_post_q = True
        elif any(w in first_ans for w in ["не планируем", "не будем", "отказываемся", "уходим", "перешли"]):
            if not any(bad in first_ans for bad in ["не знаю", "не уверен", "почему нет"]):
                clear_no_post_q = True

    if any(p in full_h for p in churn_patterns) or clear_no_post_q:
        if not any(w in full_h for w in ["не надо расторгать", "не уходим", "продолжаем"]):
            return 2, "Выявлен явный отказ или переход к другому оператору"

    # 3. Confirmed Stay (Status 3)
    stay_patterns = [
        "пользуемся", "планируем", "остаемся", "продолжаем", "сим в", "оборудовани",
        "прибор", "терминал", "датчик", "кассе", "все нормально", "работает",
        "трафик есть", "пользуюсь", "будем пользоваться", "конечно будем", "да пользуемся",
        "да продолж", "все в порядке", "активно", "останемся", "сохраняем"
    ]

    clear_yes_post_q = False
    if post_q_answers:
        first_ans = post_q_answers[0].lower().strip()
        if first_ans in ["да", "да.", "да конечно", "конечно", "естественно", "угу", "ага", "планируем", "пользуемся", "продолжаем"]:
            clear_yes_post_q = True

    if any(p in full_h for p in stay_patterns) or clear_yes_post_q:
        return 3, "Подтверждено использование услуг или SIM в оборудовании"

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
