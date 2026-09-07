# script_5.py
import pandas as pd
import os

# Единый пул ключевых формулировок вопроса (как в script_6.py)
QUESTION_PATTERNS = [
    "планируете ли вы пользоваться нашими услугами дальше",
    "вы планируете пользоваться услугами t2 дальше",
    "пользуетесь услугами дальше",
    "услугами дальше",
    "пользоваться нашими услугами дальше",
    "продолжите пользоваться нашими услугами"
]

def format_full_dialogue(transcript):
    """Выводит полный диалог: bot и human."""
    if pd.isna(transcript):
        return "[ПУСТО]"
    lines = []
    for part in transcript.split(";"):
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
            lines.append(f"[???]   {part}")
    return "\n".join(lines) if lines else "[ДИАЛОГ ОТСУТСТВУЕТ]"

def is_single_human_phrase_no_answer(transcript):
    """
    Возвращает True, если:
      - есть РОВНО ОДНА реплика от человека,
      - бот ЗАДАЛ ключевой вопрос (по точным формулировкам),
      - и эта human-реплика была ДО вопроса.
    """
    if pd.isna(transcript):
        return False

    parts = [p.strip() for p in transcript.split(";") if p.strip()]
    human_parts = [i for i, p in enumerate(parts) if p.startswith("human:")]
    
    # Только одна реплика от человека
    if len(human_parts) != 1:
        return False

    human_index = human_parts[0]

    # Ищем позицию, где бот впервые задаёт ключевой вопрос
    question_index = None
    for i, part in enumerate(parts):
        if part.startswith(("bot:", "robot:")):
            bot_text = part.split(":", 1)[1].strip().lower()
            for pattern in QUESTION_PATTERNS:
                if pattern in bot_text:
                    question_index = i
                    break
        if question_index is not None:
            break

    if question_index is None:
        return False  # Вопрос не задан → не подходит

    # Человек ответил ДО того, как был задан вопрос → не является ответом
    if human_index < question_index:
        return True

    return False

def process_no_answer_only(
    input_csv="script_4/transcript_for_llm.csv",
    output_dir="script_5",
    verbose=True
):
    if verbose:
        print(f"Загрузка {input_csv}...")

    df = pd.read_csv(input_csv)
    required_cols = ["id", "result", "status", "transcript"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует колонка: {col}")

    # Применяем исправленный фильтр
    df["is_single_no_answer"] = df["transcript"].apply(is_single_human_phrase_no_answer)
    df_target = df[df["is_single_no_answer"]].copy().reset_index(drop=True)

    if verbose:
        print(f"✅ Записи с одной фразой ДО вопроса (и без ответа): {len(df_target)}")

    os.makedirs(output_dir, exist_ok=True)

    # Сохраняем
    df_target.to_csv(os.path.join(output_dir, "full.csv"), index=False, encoding="utf-8")
    with open(os.path.join(output_dir, "ids.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(df_target["id"].astype(str).tolist()))

    # Лог
    logs = []
    for idx, row in df_target.iterrows():
        dialogue = format_full_dialogue(row["transcript"])
        logs.append(
            f"""--- Запись {idx + 1} (ID: {row['id']}) ---
Полный диалог:
{dialogue}
----------------------------------------------------------------------
"""
        )
    with open(os.path.join(output_dir, "log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(logs))

    # Остальные записи
    clean_df = df[~df["is_single_no_answer"]].copy().reset_index(drop=True)
    clean_path = os.path.join("to_llm.csv")
    clean_df.to_csv(clean_path, index=False, encoding="utf-8")

    if verbose:
        print(f"\n📁 Результат сохранён в: {output_dir}/")
        print(f"✨ Чистый файл для следующего этапа: {clean_path}")
        print(f"   Осталось записей: {len(clean_df)}")

    return df_target, clean_df

if __name__ == "__main__":
    process_no_answer_only()