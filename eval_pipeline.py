import pandas as pd
import numpy as np
import os
import sys

# UTF-8 output configuration
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from script_1 import has_no_human_reply
from script_3 import extract_answer_to_usage, classify_usage_answer_fixed, extract_all_human_text, has_usage_signals
from script_4 import is_clear_churn, extract_answer_to_usage as extract_answer_to_usage_churn
from script_5 import is_single_human_phrase_no_answer
from script_6_llm import fallback_semantic_classifier, classify_with_openai_api
from eval_metrics import evaluate_predictions, STATUS_MAP

def run_hybrid_pipeline_on_dataframe(df, use_api=False):
    """
    Executes the complete multi-stage hybrid pipeline (Rule Stages 1-5 + LLM Stage 6)
    on a DataFrame containing dialogue transcripts.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    can_use_api = use_api and bool(api_key)
    
    predictions = []
    reasons = []
    stages_triggered = []

    for idx, row in df.iterrows():
        tr = str(row.get("transcript", ""))
        st = row.get("status", None)
        res_str = str(row.get("result", ""))
        
        # --- Stage 1: Silence / No Human Reply Filter ---
        if has_no_human_reply(tr):
            predictions.append(1)
            reasons.append("Stage 1: Отсутствуют реплики человека (недозвон)")
            stages_triggered.append("Stage 1 (No Reply)")
            continue

        # --- Stage 2: Auto Answer Filter ---
        if "автоответчик" in res_str.lower():
            predictions.append(1)
            reasons.append("Stage 2: Детекция автоответчика по метке системы")
            stages_triggered.append("Stage 2 (Auto Answer)")
            continue

        # --- Stage 2.1: Call Negativity Filter ---
        if "негатив клиента от звонка" in str(st).lower():
            predictions.append(1)
            reasons.append("Stage 2.1: Негатив от факта звонка")
            stages_triggered.append("Stage 2.1 (Call Negativity)")
            continue

        # --- Stage 3: True Stay Intent Filter ---
        ans_usage = extract_answer_to_usage(tr)
        intent = classify_usage_answer_fixed(ans_usage)
        human_full = extract_all_human_text(tr)
        has_usage = has_usage_signals(human_full)
        if (intent == 'stay') or has_usage:
            predictions.append(3)
            reasons.append("Stage 3: Подтверждение намерения остаться / SIM в оборудовании")
            stages_triggered.append("Stage 3 (True Stay)")
            continue

        # --- Stage 4: Confirmed Churn Intent Filter ---
        ans_churn = extract_answer_to_usage_churn(tr)
        if is_clear_churn(ans_churn):
            predictions.append(2)
            reasons.append("Stage 4: Четкий подтвержденный отказ")
            stages_triggered.append("Stage 4 (Confirmed Churn)")
            continue

        # --- Stage 5: Structural Dialogue Anomaly Filter ---
        if is_single_human_phrase_no_answer(tr):
            predictions.append(1)
            reasons.append("Stage 5: Реплика человека произнесена до ключевого вопроса")
            stages_triggered.append("Stage 5 (Anomaly Filter)")
            continue

        # --- Stage 6: LLM Fallback Classifier (Gray Zone) ---
        if can_use_api:
            code, reason = classify_with_openai_api(tr, api_key=api_key)
        else:
            code, reason = fallback_semantic_classifier(tr, bot_status=st)
            # If fallback classifier returns 1 and Olga had a valid non-zero status, check clarifying questions
            if code == 1 and st in [1, 2, 3, 4]:
                if any(cq in tr.lower() for cq in ["какую фирму", "какую организацию", "каким номером", "какой номер", "что за услуги", "куда звоните"]):
                    code = 1
                else:
                    code = st
                    reason = "Stage 6 Smart Prior: сохранен исходный статус ответа"

        predictions.append(code)
        reasons.append(f"Stage 6 (LLM Fallback): {reason}")
        stages_triggered.append("Stage 6 (LLM)")

    df_res = df.copy()
    df_res["pipeline_status"] = predictions
    df_res["pipeline_reason"] = reasons
    df_res["pipeline_stage"] = stages_triggered
    df_res["pipeline_status_name"] = df_res["pipeline_status"].map(STATUS_MAP)

    return df_res

def evaluate_full_pipeline(test_csv="318_test.csv"):
    if not os.path.exists(test_csv):
        print(f"❌ Файл бенчмарка {test_csv} не найден.")
        return None

    df = pd.read_csv(test_csv, encoding="utf-8")
    print(f"🔄 Выполнение полного гибридного пайплайна (Stages 1-6) на {len(df)} записях бенчмарка...")

    df_evaluated = run_hybrid_pipeline_on_dataframe(df)

    y_true = df_evaluated["true_status"].values
    y_pred = df_evaluated["pipeline_status"].values

    results = evaluate_predictions(y_true, y_pred)
    
    # Save back to benchmark file
    df_evaluated["llm_status"] = df_evaluated["pipeline_status"]
    df_evaluated.to_csv(test_csv, index=False, encoding="utf-8")
    
    print("✅ Оценка полного гибридного пайплайна завершена. Бенчмарк обновлен.")
    return results, df_evaluated

if __name__ == "__main__":
    evaluate_full_pipeline()
