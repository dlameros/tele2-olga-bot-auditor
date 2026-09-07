# script_4.py
import pandas as pd
import re
import os

def extract_all_human_replies(transcript):
    """Возвращает список всех реплик человека."""
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

def extract_answer_to_usage(transcript):
    """Извлекает первую реплику human после фразы 'услугами дальше?'."""
    if pd.isna(transcript):
        return None
    parts = [p.strip() for p in transcript.split(";") if p.strip()]
    question_found = False
    for part in parts:
        if not question_found and "услугами дальше" in part:
            question_found = True
            continue
        if question_found and part.startswith("human:"):
            return part[len("human:"):].strip()
        if question_found and part.startswith("robot:"):
            continue
    return None

def is_clear_churn(answer):
    """Проверяет, является ли ответ ЧЁТКИМ отказом (с учётом контекста)."""
    if not answer or not str(answer).strip():
        return False
    ans = str(answer).strip().lower()

    # === 1. Исключаем двусмысленные/позитивные фразы ===
    stay_or_unclear_phrases = [
        "да нет", "нет да", "не знаю", "не уверен", "пока да", "вроде да",
        "пользуемся", "планируем", "остаёмся", "активен", "всё нормально",
        "продолжаем", "не меняем", "трафик есть", "договор активен"
    ]
    if any(phrase in ans for phrase in stay_or_unclear_phrases):
        return False

    # === 2. Проверяем "нет" в контексте ===
    if "нет" in ans:
        # Если "нет" относится к отсутствию договора/трафика — не отказ
        if re.search(r"нет\s+(договора|контракта|номера|трафика|услуги|симки)", ans):
            return False
        # Если рядом есть позитивные слова — не отказ
        if re.search(r"(да|пользуемся|планируем|активен|остаёмся)", ans):
            return False
        # Чистое "нет" без контекста — отказ
        if ans in ["нет", "нет.", "нет!"]:
            return True
        # Если "нет" — часть явного отказа
        if any(neg in ans for neg in ["не буду", "не планирую", "отказываюсь"]):
            return True
        # Иначе — не считаем за чёткий отказ
        return False

    # === 3. Явные причины ухода ===
    churn_phrases = [
        "дорого", "повышение цены", "не устраивает тариф",
        "не устраивает качество", "меняем оператора", "переходим к другому",
        "уходим", "смена провайдера", "закрываем договор", "отключаем",
        "не довольны", "недовольны", "жалоба", "проблема с качеством"
    ]
    if any(phrase in ans for phrase in churn_phrases):
        return True

    return False

def process_confirmed_churn(
    input_csv="script_3/transcript_without_stay.csv",
    output_dir="script_4",
    verbose=True
):
    """
    Удаляет ТОЛЬКО тех с 'угроза оттока подтверждена', у кого ЧЁТКИЙ отказ.
    """
    if verbose:
        print(f"Загрузка {input_csv}...")

    df = pd.read_csv(input_csv)

    required = ["id", "status", "result", "call_status", "transcript"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Отсутствует колонка: {col}")

    # Фильтр по статусу "подтверждена"
    mask_status = df["status"].astype(str).str.contains("угроза оттока подтверждена", case=False, na=False)
    df_churn_candidates = df[mask_status].copy()

    if verbose:
        print(f"Кандидаты (статус 'подтверждена'): {len(df_churn_candidates)}")

    # Извлекаем ответ на ключевой вопрос
    df_churn_candidates["answer_to_usage"] = df_churn_candidates["transcript"].apply(extract_answer_to_usage)

    # Оставляем ТОЛЬКО чёткие отказы (с исправленной логикой)
    df_churn_confirmed = df_churn_candidates[
        df_churn_candidates["answer_to_usage"].apply(is_clear_churn)
    ].copy().reset_index(drop=True)

    # Удаляем из основного файла
    churn_ids_set = set(df_churn_confirmed["id"].astype(str))
    df_for_llm = df[~df["id"].astype(str).isin(churn_ids_set)].copy()

    if verbose:
        print(f"✅ Подтверждённых уходящих (чёткий отказ): {len(df_churn_confirmed)}")
        print(f"✅ Осталось для LLM: {len(df_for_llm)}")

    os.makedirs(output_dir, exist_ok=True)

    churn_csv = os.path.join(output_dir, "confirmed_churn_full.csv")
    for_llm_csv = os.path.join(output_dir, "transcript_for_llm.csv")
    churn_ids = os.path.join(output_dir, "confirmed_churn_ids.txt")
    log_txt = os.path.join(output_dir, "confirmed_churn_log.txt")

    df_churn_confirmed.to_csv(churn_csv, index=False, encoding="utf-8")
    df_for_llm.to_csv(for_llm_csv, index=False, encoding="utf-8")

    ids_list = df_churn_confirmed["id"].astype(str).tolist()
    with open(churn_ids, "w", encoding="utf-8") as f:
        f.write("\n".join(ids_list))

    # Генерация лога (с аннотацией ответа)
    log_entries = []
    for idx, row in df_churn_confirmed.iterrows():
        human_replies = extract_all_human_replies(row["transcript"])
        answer = row["answer_to_usage"] or "(не найден)"

        annotated_replies = []
        for rep in human_replies:
            if rep == answer:
                annotated_replies.append(f"→ {rep}  ← ответ на 'услугами дальше?'")
            else:
                annotated_replies.append(rep)

        replies_block = "\n  • " + "\n  • ".join(annotated_replies) if annotated_replies else "\n  • (нет реплик)"
        log_entry = f"""--- Запись {idx + 1} (ID: {row['id']}) ---
Реплики человека:{replies_block}
----------------------------------------------------------------------"""
        log_entries.append(log_entry)

    with open(log_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))

    if verbose:
        print(f"📁 Подтверждённые уходящие: {churn_csv}")
        print(f"✨ Файл для LLM: {for_llm_csv}")
        print(f"🆔 ID уходящих: {churn_ids}")
        print(f"📄 Лог уходящих: {log_txt}")

    return df_churn_confirmed, df_for_llm, ids_list, log_entries

if __name__ == "__main__":
    process_confirmed_churn()