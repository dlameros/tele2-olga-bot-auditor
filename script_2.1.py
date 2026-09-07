# script_3.py
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

def remove_negative_clients(
    input_csv="script_2/transcript_without_auto.csv",
    output_dir="script_2.1",
    verbose=True
):
    """
    Удаляет все записи со статусом 'негатив клиента от звонка'.
    """
    if verbose:
        print(f"Загрузка {input_csv}...")

    df = pd.read_csv(input_csv)

    required_cols = ["id", "status", "result", "call_status", "transcript"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует колонка: {col}")

    # Фильтр: точное совпадение с "негатив клиента от звонка" (регистронезависимо)
    mask_negative = df["status"].astype(str).str.contains(
        r"негатив клиента от звонка", 
        case=False, 
        na=False,
        regex=False
    )
    
    df_negative = df[mask_negative].copy().reset_index(drop=True)
    df_clean = df[~mask_negative].copy()

    if verbose:
        print(f"✅ Удалено негативных записей: {len(df_negative)}")
        print(f"✅ Осталось для анализа остающихся: {len(df_clean)}")

    # Создаём папку
    os.makedirs(output_dir, exist_ok=True)

    # Пути к файлам
    neg_csv = os.path.join(output_dir, "negative_full.csv")
    clean_csv = os.path.join(output_dir, "transcript_clean_for_stay.csv")
    neg_ids = os.path.join(output_dir, "negative_ids.txt")
    log_txt = os.path.join(output_dir, "negative_log.txt")

    # 1. Сохраняем удалённые записи
    df_negative.to_csv(neg_csv, index=False, encoding="utf-8")

    # 2. Сохраняем чистый файл (без автоответчиков и без негатива)
    df_clean.to_csv(clean_csv, index=False, encoding="utf-8")

    # 3. Сохраняем ID
    ids_list = df_negative["id"].astype(str).tolist()
    with open(neg_ids, "w", encoding="utf-8") as f:
        f.write("\n".join(ids_list))

    # 4. Генерируем лог с репликами человека
    log_entries = []
    for idx, row in df_negative.iterrows():
        replies = extract_human_replies_raw(row["transcript"])
        replies_block = "\n  • " + "\n  • ".join(replies) if replies else "\n  • (нет реплик)"
        log_entry = f"""--- Запись {idx + 1} (ID: {row['id']}) ---
status: {row['status']}
result: {row['result']}
Реплики человека:{replies_block}
----------------------------------------------------------------------"""
        log_entries.append(log_entry)

    with open(log_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))

    if verbose:
        print(f"📁 Негативные записи: {neg_csv}")
        print(f"✨ Чистый файл для анализа остающихся: {clean_csv}")
        print(f"🆔 ID негативных клиентов: {neg_ids}")
        print(f"📄 Лог негативных записей: {log_txt}")

    return df_negative, df_clean, ids_list, log_entries

if __name__ == "__main__":
    remove_negative_clients()