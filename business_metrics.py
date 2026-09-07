import pandas as pd
import numpy as np
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_pure_ai_agent_roi(
    dataset_size=3200,
    call_center_capacity=3000,
    avg_call_duration_min=5.0,
    operator_hourly_rate_rub=450.0
):
    """
    Computes strict factual operational impact for Tele2 Rule-Based Auditor
    without extrapolations or invented revenue assumptions.
    """
    # Factual filtering ratio from benchmark evaluation (177 / 318 = 55.66%)
    filtered_ratio = 177.0 / 318.0
    selected_ratio = 141.0 / 318.0

    filtered_calls_monthly = int(round(dataset_size * filtered_ratio))   # ~1,781 calls
    selected_calls_monthly = int(round(dataset_size * selected_ratio))   # ~1,419 calls

    # Labor hours saved from filtering non-actionable calls
    hours_saved_monthly = (filtered_calls_monthly * avg_call_duration_min) / 60.0  # 148.4 hours
    monthly_fot_savings_rub = hours_saved_monthly * operator_hourly_rate_rub       # ~66,788 ₽ / month
    annual_fot_savings_rub = monthly_fot_savings_rub * 12.0                      # ~801,450 ₽ / year

    return {
        "dataset_size": dataset_size,
        "call_center_capacity": call_center_capacity,
        "filtered_calls_monthly": filtered_calls_monthly,
        "selected_calls_monthly": selected_calls_monthly,
        "hours_saved_monthly": hours_saved_monthly,
        "monthly_fot_savings_rub": monthly_fot_savings_rub,
        "annual_fot_savings_rub": annual_fot_savings_rub,
        "api_cost_rub": 0.0
    }

def print_pure_ai_agent_roi_report(roi):
    print("=" * 75)
    print("⚡ TELE2 B2B RULE-BASED AUDITOR: ФАКТИЧЕСКИЙ ОПЕРАЦИОННЫЙ ЭФФЕКТ")
    print("=" * 75)
    print(f"Входной поток диалогов 'серая зона'  : {roi['dataset_size']:,} звонков/мес")
    print(f"Лимит мощности колл-центра / операторов: {roi['call_center_capacity']:,} звонков/мес")
    print("-" * 75)
    print(f"📞 Отправлено операторам (S2 + S4) : {roi['selected_calls_monthly']:,} целевых звонков (44.3%)")
    print(f"⚡ Автономно отсеяно правилами (S1 + S3): {roi['filtered_calls_monthly']:,} звонков/мес (55.7%)")
    print(f"⏱ Сбережено рабочего времени        : {roi['hours_saved_monthly']:,.1f} чел-часов/мес")
    print(f"💰 Прямая экономия ФОТ операторов   : {roi['monthly_fot_savings_rub']:,.2f} ₽/мес ({roi['annual_fot_savings_rub']:,.2f} ₽/год)")
    print(f"💳 Затраты на нейросети / API        : 0.00 ₽ (100% Локальный Python Rule Engine)")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    roi = calculate_pure_ai_agent_roi()
    print_pure_ai_agent_roi_report(roi)
