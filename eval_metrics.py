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

def run_evaluation(test_csv="318_test.csv"):
    if not os.path.exists(test_csv):
        print(f"❌ Benchmark file {test_csv} not found.")
        return
        
    df = pd.read_csv(test_csv)
    
    # 1. Evaluate baseline Bot "Olga" status vs true_status
    y_true = df["true_status"].values
    y_bot = df["status"].values
    
    bot_results = evaluate_predictions(y_true, y_bot)
    print_evaluation_report("Baseline Evaluation: Bot 'Olga' vs Ground Truth", bot_results)
    
    # 2. Evaluate LLM status if available
    if "llm_status" in df.columns and df["llm_status"].notna().any():
        df_llm_eval = df[df["llm_status"].notna()]
        y_true_llm = df_llm_eval["true_status"].values
        y_pred_llm = df_llm_eval["llm_status"].astype(int).values
        llm_results = evaluate_predictions(y_true_llm, y_pred_llm)
        print_evaluation_report("Hybrid Auditor (Rule + LLM) vs Ground Truth", llm_results)
    
    return bot_results

if __name__ == "__main__":
    run_evaluation()
