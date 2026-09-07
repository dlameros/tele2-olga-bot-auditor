import subprocess
import sys
import os

# Set UTF-8 encoding for current process and child processes
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

print("🚀 Starting Tele2 Olga Bot Auditor (Pure Deterministic Rule-Based Pipeline)...\n")

# Запуск script_1.py (No Reply Filter)
subprocess.run([sys.executable, "script_1.py"])

# Запуск script_2.py & script_2.1.py (Auto Answer & Negativity Filters)
subprocess.run([sys.executable, "script_2.py"])
subprocess.run([sys.executable, "script_2.1.py"])

# Запуск script_3.py (True Stay Intent Filter)
subprocess.run([sys.executable, "script_3.py"])

# Запуск script_4.py (Confirmed Churn Intent Filter)
subprocess.run([sys.executable, "script_4.py"])

# Запуск script_5.py (Structural Dialogue Anomaly Filter & export to_llm.csv)
subprocess.run([sys.executable, "script_5.py"])

# Запуск script_6_llm.py (Rule-Based Semantic Classifier Stage 6)
subprocess.run([sys.executable, "script_6_llm.py"])

# Запуск eval_pipeline.py (Full Multi-Stage Benchmark Evaluator)
print("\n🧪 Running full multi-stage benchmark pipeline evaluation...")
subprocess.run([sys.executable, "eval_pipeline.py"])

# Запуск eval_comparison.py (3-Way Comparison: Ground Truth vs Olga vs Rule Auditor)
print("\n📊 Running 3-Way Benchmark Comparison & Operational Selection analysis...")
subprocess.run([sys.executable, "eval_comparison.py"])

# Запуск eval_metrics.py (Benchmark Evaluation & Error Analysis & Business ROI)
print("\n💼 Running final benchmark evaluation & Pure Rule-Based ROI report...")
subprocess.run([sys.executable, "eval_metrics.py"])

print("\n✨ Pipeline execution complete! Audit artifacts, Rule Engine metrics, and Business ROI ready.")