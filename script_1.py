# script_4.py
import pandas as pd
import os

def has_no_human_reply(transcript):
    """Возвращает True, если в транскрипте нет ни одной реплики 'human:'."""
    if pd.isna(transcript):
        return True
    return "human:" not in str(transcript)

def generate_no_reply_artifacts(
    input_csv="transcript.csv",
    output_dir="script_4",
    verbose=True
):
    """
    Генерирует 4 артефакта:
      1. no_human_reply_full.csv — записи без ответа человека
      2. no_reply_ids.txt        — их ID
      3. no_reply_log.txt        — красивый лог
      4. transcript_without_no_reply.csv — исходный файл БЕЗ недозвонов
    Все файлы сохраняются в папку script_4.
    """
    if verbose:
        print(f"Загрузка {input_csv}...")

    df = pd.read_csv(input_csv)

    required_cols = ["id", "status", "call_status", "transcript"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует обязательная колонка: {col}")

    # Определяем маску для "недозвонов" (человек не ответил)
    mask_no_reply = df["transcript"].apply(has_no_human_reply)
    df_no_reply = df[mask_no_reply].copy().reset_index(drop=True)
    df_without_no_reply = df[~mask_no_reply].copy()  # ← основной фильтр: оставить только тех, кто ответил

    if verbose:
        print(f"✅ Найдено {len(df_no_reply)} записей: человек не ответил ни разу.")
        print(f"✅ Осталось {len(df_without_no_reply)} записей с ответом человека.")

    # Создаём папку
    os.makedirs(output_dir, exist_ok=True)

    # Пути к файлам
    csv_no_reply = os.path.join(output_dir, "no_human_reply_full.csv")
    ids_path = os.path.join(output_dir, "no_reply_ids.txt")
    log_path = os.path.join(output_dir, "no_reply_log.txt")
    csv_clean = os.path.join(output_dir, "transcript_without_no_reply.csv")

    # 1. Недозвоны — полные записи
    df_no_reply.to_csv(csv_no_reply, index=False, encoding="utf-8")
    if verbose:
        print(f"📁 Недозвоны сохранены: {csv_no_reply}")

    # 2. ID недозвонов
    ids_list = df_no_reply["id"].astype(str).tolist()
    with open(ids_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ids_list))
    if verbose:
        print(f"🆔 ID недозвонов: {ids_path}")

    # 3. Лог недозвонов
    log_entries = []
    for idx, row in df_no_reply.iterrows():
        transcript_display = row['transcript'] if pd.notna(row['transcript']) else "(пусто)"
        log_entry = f"""--- Запись {idx + 1} (ID: {row['id']}) ---
status: {row['status']}
call_status: {row['call_status']}
transcript: {transcript_display}
Причина включения:
  • 📞 Человек не ответил ни разу — реплики 'human:' отсутствуют
----------------------------------------------------------------------"""
        log_entries.append(log_entry)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))
    if verbose:
        print(f"📄 Лог недозвонов: {log_path}")

    # 4. ✨ Чистый файл БЕЗ недозвонов
    df_without_no_reply.to_csv(csv_clean, index=False, encoding="utf-8")
    if verbose:
        print(f"✨ Основной файл БЕЗ недозвонов: {csv_clean}")

    return df_no_reply, ids_list, log_entries, df_without_no_reply

if __name__ == "__main__":
    generate_no_reply_artifacts()