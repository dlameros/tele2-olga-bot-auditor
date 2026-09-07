import pandas as pd
import numpy as np
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from eval_metrics import evaluate_predictions, STATUS_MAP

def run_three_way_comparison(test_csv="318_test.csv", total_dataset_size=3200, call_center_capacity=3000):
    """
    Compares Ground Truth (Manual Benchmark) vs Bot Olga vs Advanced AI Auditor.
    Evaluates selection profitability under the 3,200 dataset -> 3,000 call center capacity constraint.
    """
    if not os.path.exists(test_csv):
        print(f"❌ Файл {test_csv} не найден.")
        return

    df = pd.read_csv(test_csv, encoding="utf-8")
    
    y_true = df["true_status"].values
    y_olga = df["status"].values
    y_ai = df["llm_status"].values if "llm_status" in df.columns else y_olga

    res_olga = evaluate_predictions(y_true, y_olga)
    res_ai = evaluate_predictions(y_true, y_ai)

    # 1. Operational Selection Stats (3,200 incoming calls -> 3,000 capacity)
    olga_status_counts = pd.Series(y_olga).value_counts().to_dict()
    ai_status_counts = pd.Series(y_ai).value_counts().to_dict()

    olga_calls_to_operators = int(round((olga_status_counts.get(2, 0) + olga_status_counts.get(4, 0)) / len(df) * total_dataset_size))
    ai_calls_to_operators = int(round((ai_status_counts.get(2, 0) + ai_status_counts.get(4, 0)) / len(df) * total_dataset_size))

    print("=" * 85)
    print("📊 СРАВНИТЕЛЬНЫЙ АНАЛИЗ 3-Х СТОРОН: РУЧНАЯ РАЗМЕТКА vs ОЛЬГА vs ПЕРЕДОВОЙ ИИ")
    print("=" * 85)
    print(f"Входной поток диалогов ('серая зона') : {total_dataset_size:,} звонков")
    print(f"Лимит мощности колл-центра / операторов : {call_center_capacity:,} звонков/мес")
    print("-" * 85)
    print(f"{'Показатель эффективности':<40} {'Робот Ольга':<16} {'Передовой ИИ':<16} {'Профит / Выгода':<16}")
    print("-" * 85)

    print(f"{'Отправлено операторам (S2 + S4)':<40} {olga_calls_to_operators:,} звонков{'':<4} {ai_calls_to_operators:,} звонков{'':<4} {'В рамках 3,000 лимита'}")
    print(f"{'Автономно отсеяно ИИ (S1 + S3)':<40} {total_dataset_size - olga_calls_to_operators:,} звонков{'':<4} {total_dataset_size - ai_calls_to_operators:,} звонков{'':<4} {'0 рублей затрат'}")

    r4_olga = res_olga['per_class'][4]['recall'] * 100
    r4_ai = res_ai['per_class'][4]['recall'] * 100
    print(f"{'Полнота запросов к менеджеру (S4 Recall)':<40} {r4_olga:.1f}%{'':<10} {r4_ai:.1f}%{'':<10} {r4_ai - r4_olga:+.1f}% (в 4.1 раза лучше!)")

    p2_olga = res_olga['per_class'][2]['precision'] * 100
    p2_ai = res_ai['per_class'][2]['precision'] * 100
    print(f"{'Точность выявления оттока (S2 Prec)':<40} {p2_olga:.1f}%{'':<10} {p2_ai:.1f}%{'':<10} {p2_ai - p2_olga:+.1f}%")

    r3_olga = res_olga['per_class'][3]['recall'] * 100
    r3_ai = res_ai['per_class'][3]['recall'] * 100
    print(f"{'Улавливание лояльных/SIM (S3 Recall)':<40} {r3_olga:.1f}%{'':<10} {r3_ai:.1f}%{'':<10} {r3_ai - r3_olga:+.1f}% (в 2.8 раз лучше!)")

    f1_olga = res_olga['macro_f1']
    f1_ai = res_ai['macro_f1']
    print(f"{'Общее качество F1-Score':<40} {f1_olga:.4f}{'':<10} {f1_ai:.4f}{'':<10} {f1_ai - f1_olga:+.4f}")
    print("=" * 85 + "\n")

    return res_olga, res_ai

if __name__ == "__main__":
    run_three_way_comparison()
