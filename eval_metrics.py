import pandas as pd
import numpy as np
import os
import sys

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

STATUS_MAP = {
    1: "угроза оттока не определена",
    2: "угроза оттока подтверждена",
    3: "угроза оттока не подтверждена",
    4: "угроза оттока не определена, требуется уточнение персонального менеджера"
}

STATUS_TO_CODE = {v: k for k, v in STATUS_MAP.items()}

def evaluate_predictions(y_true, y_pred, label_names=STATUS_MAP):
    """
    Computes Accuracy, Precision, Recall, F1 per class, Macro F1, and Confusion Matrix.
    """
    labels = list(label_names.keys())
    cm = pd.crosstab(
        pd.Series(y_true, name='True (Ground Truth)'),
        pd.Series(y_pred, name='Predicted (Model/Bot)'),
        dropna=False
    ).reindex(index=labels, columns=labels, fill_value=0)
    
    total = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / total if total > 0 else 0.0

    metrics_per_class = {}
    for code in labels:
        name = label_names[code]
        tp = cm.loc[code, code]
        fp = cm[code].sum() - tp
        fn = cm.loc[code].sum() - tp
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        support = (y_true == code).sum()
        
        metrics_per_class[code] = {
            "name": name,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support
        }
        
    macro_f1 = np.mean([m["f1"] for m in metrics_per_class.values()])
    
    return {
        "accuracy": accuracy,
        "error_rate": 1.0 - accuracy,
        "correct": correct,
        "total": total,
        "confusion_matrix": cm,
        "per_class": metrics_per_class,
        "macro_f1": macro_f1
    }

def print_evaluation_report(title, results):
    print("=" * 70)
    print(f"📊 {title.upper()}")
    print("=" * 70)
    print(f"Total Samples  : {results['total']}")
    print(f"Correct        : {results['correct']}")
    print(f"Accuracy       : {results['accuracy'] * 100:.2f}%")
    print(f"Error Rate     : {results['error_rate'] * 100:.2f}%")
    print(f"Macro F1-Score : {results['macro_f1']:.4f}")
    print("\n--- PER-CLASS METRICS ---")
    print(f"{'Code':<5} {'Status Name':<50} {'Prec':<7} {'Rec':<7} {'F1':<7} {'Supp':<5}")
    print("-" * 80)
    for code, m in results['per_class'].items():
        print(f"{code:<5} {m['name'][:48]:<50} {m['precision']:.3f}   {m['recall']:.3f}   {m['f1']:.3f}   {m['support']:<5}")
    
    print("\n--- CONFUSION MATRIX (Rows: True, Cols: Pred) ---")
    print(results['confusion_matrix'])
    print("=" * 70 + "\n")

def print_comparative_summary(bot_results, llm_results):
    print("=" * 70)
    print("🚀 AUDITOR VS BASELINE BOT 'OLGA' SUMMARY COMPARISON")
    print("=" * 70)
    print(f"{'Metric':<35} {'Bot Olga':<15} {'Hybrid Auditor':<15} {'Delta / Gain':<15}")
    print("-" * 75)
    
    acc_bot = bot_results['accuracy'] * 100
    acc_llm = llm_results['accuracy'] * 100
    print(f"{'Accuracy (Overall)':<35} {acc_bot:.2f}%{'':<8} {acc_llm:.2f}%{'':<8} {acc_llm - acc_bot:+.2f}%")
    
    err_bot = bot_results['error_rate'] * 100
    err_llm = llm_results['error_rate'] * 100
    print(f"{'Error Rate':<35} {err_bot:.2f}%{'':<8} {err_llm:.2f}%{'':<8} {err_llm - err_bot:+.2f}%")

    f1_bot = bot_results['macro_f1']
    f1_llm = llm_results['macro_f1']
    print(f"{'Macro F1-Score':<35} {f1_bot:.4f}{'':<9} {f1_llm:.4f}{'':<9} {f1_llm - f1_bot:+.4f}")

    p2_bot = bot_results['per_class'][2]['precision'] * 100
    p2_llm = llm_results['per_class'][2]['precision'] * 100
    print(f"{'Precision (Churn Confirmed S2)':<35} {p2_bot:.1f}%{'':<9} {p2_llm:.1f}%{'':<9} {p2_llm - p2_bot:+.1f}%")

    r4_bot = bot_results['per_class'][4]['recall'] * 100
    r4_llm = llm_results['per_class'][4]['recall'] * 100
    print(f"{'Recall (Manager Request S4)':<35} {r4_bot:.1f}%{'':<9} {r4_llm:.1f}%{'':<9} {r4_llm - r4_bot:+.1f}%")
    print("=" * 70 + "\n")

def run_evaluation(test_csv="318_test.csv"):
    if not os.path.exists(test_csv):
        print(f"❌ Benchmark file {test_csv} not found.")
        return
        
    df = pd.read_csv(test_csv, encoding="utf-8")
    
    # 1. Evaluate baseline Bot "Olga" status vs true_status
    y_true = df["true_status"].values
    y_bot = df["status"].values
    
    bot_results = evaluate_predictions(y_true, y_bot)
    print_evaluation_report("Baseline Evaluation: Bot 'Olga' vs Ground Truth", bot_results)
    
    # 2. Evaluate LLM / Pipeline status if available
    llm_results = None
    if "llm_status" in df.columns and df["llm_status"].notna().any():
        df_llm_eval = df[df["llm_status"].notna()]
        y_true_llm = df_llm_eval["true_status"].values
        y_pred_llm = df_llm_eval["llm_status"].astype(int).values
        llm_results = evaluate_predictions(y_true_llm, y_pred_llm)
        print_evaluation_report("Hybrid Auditor (Rule + LLM) vs Ground Truth", llm_results)
        
        print_comparative_summary(bot_results, llm_results)
        
        # 3. Compute Business ROI
        from business_metrics import calculate_business_roi, print_business_roi_report
        roi = calculate_business_roi(hybrid_eval_results=llm_results)
        print_business_roi_report(roi)

    return bot_results, llm_results

if __name__ == "__main__":
    run_evaluation()
