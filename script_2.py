# script_2.py
import pandas as pd
import os

def extract_human_replies_raw(transcript):
    """Извлекает оригинальные реплики человека как список."""
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

def remove_all_auto_by_olga(
    input_csv="script_1/transcript_without_no_reply.csv",
    output_dir="script_2",
    verbose=True
):
    """
    Удаляет ВСЕ записи, где result содержит 'автоответчик' (включая 'автоответчик Олег').
    Никаких дополнительных проверок — только по метке Ольги.
    """
    if verbose:
        print(f"Загрузка {input_csv}...")

    df = pd.read_csv(input_csv)

    required_cols = ["id", "result", "status", "call_status", "transcript"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует колонка: {col}")

    # Фильтрация: всё, что содержит "автоответчик" в result (регистронезависимо)
    mask_auto = df["result"].astype(str).str.contains("автоответчик", case=False, na=False)
    df_auto = df[mask_auto].copy().reset_index(drop=True)
    df_without_auto = df[~mask_auto].copy()

    if verbose:
        print(f"✅ Удалено автоответчиков: {len(df_auto)}")
        print(f"✅ Осталось для анализа: {len(df_without_auto)}")

    # Создаём папку
    os.makedirs(output_dir, exist_ok=True)

    # Пути
    auto_csv = os.path.join(output_dir, "auto_answer_full.csv")
    clean_csv = os.path.join(output_dir, "transcript_without_auto.csv")
    ids_txt = os.path.join(output_dir, "auto_answer_ids.txt")
    log_txt = os.path.join(output_dir, "auto_answer_log.txt")

    # Сохраняем автоответчики
    df_auto.to_csv(auto_csv, index=False, encoding="utf-8")

    # Сохраняем чистый файл
    df_without_auto.to_csv(clean_csv, index=False, encoding="utf-8")

    # Сохраняем ID
    ids_list = df_auto["id"].astype(str).tolist()
    with open(ids_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(ids_list))

    # Генерируем лог с репликами
    log_entries = []
    for idx, row in df_auto.iterrows():
        replies = extract_human_replies_raw(row["transcript"])
        replies_block = "\n  • " + "\n  • ".join(replies) if replies else "\n  • (нет реплик)"
        log_entry = f"""--- Запись {idx + 1} (ID: {row['id']}) ---
Реплики автоответчика:{replies_block}
----------------------------------------------------------------------"""
        log_entries.append(log_entry)

    with open(log_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))

    if verbose:
        print(f"📁 Удалённые автоответчики: {auto_csv}")
        print(f"✨ Чистый файл (без автоответчиков): {clean_csv}")
        print(f"🆔 ID автоответчиков: {ids_txt}")
        print(f"📄 Лог автоответчиков: {log_txt}")

    return df_auto, df_without_auto, ids_list, log_entries

if __name__ == "__main__":
    remove_all_auto_by_olga()