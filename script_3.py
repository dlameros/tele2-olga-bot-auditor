# script_2.py
import pandas as pd
import re
import os

def extract_human_text(transcript):
    if pd.isna(transcript):
        return ""
    parts = transcript.split(";")
    human_texts = []
    for part in parts:
        part = part.strip()
        if part.startswith("human:"):
            text = part[len("human:"):].strip()
            if text:
                human_texts.append(text)
    return " ".join(human_texts)

def extract_answer_to_usage(transcript):
    if pd.isna(transcript):
        return None
    parts = [p.strip() for p in transcript.split(";") if p.strip()]
    question_found = False
    for part in parts:
        if not question_found and "услугами дальше" in part:
            question_found = True
            continue
        if question_found and part.startswith("human:"):
            ans = part[len("human:"):].strip()
            return ans if ans else None
        if question_found and part.startswith("robot:"):
            continue
    return None

def classify_usage_answer_fixed(answer):
    if pd.isna(answer) or not str(answer).strip():
        return "no_answer"
    
    ans = str(answer).strip().lower()
    
    if any(w in ans for w in ["нет", "не буду", "не планирую", "отказ"]):
        return "churn"
    
    if any(m in ans for m in [
        "алло", "слушаю", "говорите", "добрый день", "здравствуйте",
        "спасибо", "в чем дело", "как вас зовут", "из какой организации",
        "повторите", "не соображу", "еще вопрос", "что нужно"
    ]):
        return "unclear"
    
    clean_affirmations = [
        "да", "да да", "да конечно", "конечно", "угу", "ага", "естественно",
        "планируем", "пользуемся", "остаёмся", "продолжаем", "собираемся"
    ]
    
    words = ans.split()
    if all(word in ["да", "угу", "ага", "конечно", "естественно", "планируем", "пользуемся"] for word in words):
        return "stay"
    
    if any(phrase in ans for phrase in clean_affirmations):
        if not any(bad in ans for bad in ["слушаю", "говорите", "повторите", "в чем", "организация"]):
            return "stay"
    
    return "unclear"

def extract_all_human_text(transcript):
    if pd.isna(transcript):
        return ""
    return " ".join([
        part[len("human:"):].strip()
        for part in transcript.split(";")
        if part.strip().startswith("human:") and part[len("human:"):].strip()
    ])

def has_usage_signals(text):
    if not isinstance(text, str):
        return False
    t = text.lower()
    return any(verb in t for verb in [
        "пользуюсь", "пользуемся", "пользуется", "пользуются",
        "планирую", "планируем", "планирует",
        "продолжаю", "продолжаем", "остаюсь", "остаёмся",
        "активен", "активны", "работает", "работают",
        "sim в", "в оборудовании", "в устройстве"
    ])

def extract_human_replies_raw(transcript):
    if pd.isna(transcript):
        return []
    replies = []
    for part in transcript.split(";"):
        part = part.strip()
        if part.startswith("human:"):
            text = part[len("human:"):].strip()
            if text:
                replies.append(text)
    return replies

def process_true_stay_with_logs(
    input_csv="script_2.1/transcript_clean_for_stay.csv",  # ← вход от script_4
    output_dir="script_3",
    verbose=True
):
    """
    Фильтрует остающихся по проверенной логике script_2.
    Возвращает файлы в папку script_2, включая transcript_without_stay.csv.
    """
    if verbose:
        print(f"Загрузка {input_csv}...")

    df = pd.read_csv(input_csv)

    required_cols = ["id", "status", "call_status", "transcript"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует колонка: {col}")

    # Фильтрация по статусу "не подтверждена" (как в оригинале)
    df_candidate = df[df['status'].str.contains("не подтверждена", case=False, na=False)].copy()

    if verbose:
        print(f"✅ Всего записей: {len(df)}")
        print(f"✅ Кандидаты (статус 'не подтверждена'): {len(df_candidate)}")

    # Применяем оригинальную логику
    df_candidate['human_text'] = df_candidate['transcript'].apply(extract_human_text)
    df_candidate['answer_to_usage'] = df_candidate['transcript'].apply(extract_answer_to_usage)
    df_candidate['intent'] = df_candidate['answer_to_usage'].apply(classify_usage_answer_fixed)
    df_candidate['human_full'] = df_candidate['transcript'].apply(extract_all_human_text)
    df_candidate['has_usage'] = df_candidate['human_full'].apply(has_usage_signals)

    df_candidate['is_true_stay'] = (
        (df_candidate['intent'] == 'stay') | 
        (df_candidate['has_usage'])
    )
    
    df_true_stay = df_candidate[df_candidate['is_true_stay']].copy().reset_index(drop=True)
    
    # Создаём файл БЕЗ остающихся: все записи из input_csv, кроме найденных остающихся
    stay_ids_set = set(df_true_stay['id'].astype(str))
    df_without_stay = df[~df['id'].astype(str).isin(stay_ids_set)].copy()

    if verbose:
        print(f"✅ Найдено 'остающихся': {len(df_true_stay)}")
        print(f"✅ Осталось для анализа уходящих: {len(df_without_stay)}")

    # Создаём папку
    os.makedirs(output_dir, exist_ok=True)

    # Пути к файлам
    stay_csv = os.path.join(output_dir, "true_stay_full.csv")
    without_stay_csv = os.path.join(output_dir, "transcript_without_stay.csv")
    ids_path = os.path.join(output_dir, "true_stay_ids.txt")
    log_path = os.path.join(output_dir, "true_stay_log.txt")

    # 1. Остающиеся (полные записи)
    df_true_stay.to_csv(stay_csv, index=False, encoding="utf-8")

    # 2. Файл БЕЗ остающихся — главный результат для следующих шагов!
    df_without_stay.to_csv(without_stay_csv, index=False, encoding="utf-8")

    # 3. Список ID остающихся
    ids_list = df_true_stay["id"].astype(str).tolist()
    with open(ids_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ids_list))

    # 4. Красивый лог
    log_entries = []
    for idx, row in df_true_stay.iterrows():
        human_replies = extract_human_replies_raw(row["transcript"])
        replies_block = "\n  • " + "\n  • ".join(human_replies) if human_replies else "\n  • (нет реплик)"
        answer = row["answer_to_usage"] or "(не найден)"

        log_entry = f"""--- Запись {idx + 1} (ID: {row['id']}) ---
Реплики человека:{replies_block}
Ответ на вопрос 'услугами дальше?': '{answer}'
Почему в 'остающихся':
  • ✅ Прямой позитивный ответ или сигнал использования (по логике script_2)
----------------------------------------------------------------------"""
        log_entries.append(log_entry)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))

    if verbose:
        print(f"📁 Остающиеся: {stay_csv}")
        print(f"✨ Файл БЕЗ остающихся: {without_stay_csv} ← ИСПОЛЬЗУЙТЕ ЭТОТ ФАЙЛ ДАЛЬШЕ")
        print(f"🆔 ID остающихся: {ids_path}")
        print(f"📄 Лог остающихся: {log_path}")

    return df_true_stay, df_without_stay, ids_list, log_entries

if __name__ == "__main__":
    process_true_stay_with_logs()