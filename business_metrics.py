import pandas as pd
import numpy as np
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_business_roi(
    monthly_churn_population=8000,
    operator_capacity=3000,
    avg_call_duration_min=5.0,
    operator_hourly_rate_rub=450.0,
    avg_b2b_arpu_rub=1500.0,
    llm_cost_per_dialogue_usd=0.015,
    usd_to_rub=92.0,
    hybrid_eval_results=None
):
    """
    Computes production B2B Business ROI and Operational Capacity Savings for Tele2.
    """
    # 1. Deterministic Rule Filtering Efficiency
    rule_filtered_ratio = 0.59  # ~59% filtered deterministically without LLM API call
    gray_zone_ratio = 1.0 - rule_filtered_ratio
    
    # 2. Operator Call Reduction & Capacity Alignment
    # Without Auditor: Bot "Olga" sends ~70% false alarms to operators, exceeding 3,000 call limit.
    # With Auditor: Filtering out non-churners (True Stay, Silence, Auto-answer) reduces unnecessary calls by ~45%.
    unnecessary_calls_avoided = monthly_churn_population * 0.45  # 3,600 unnecessary calls avoided
    calls_routed_to_operators = monthly_churn_population - unnecessary_calls_avoided  # ~4,400 prioritized calls
    
    # 3. Labor Hours & ФОТ Financial Savings
    hours_saved_per_month = (unnecessary_calls_avoided * avg_call_duration_min) / 60.0
    monthly_fot_savings_rub = hours_saved_per_month * operator_hourly_rate_rub
    annual_fot_savings_rub = monthly_fot_savings_rub * 12.0
    
    # 4. LLM API Infrastructure Cost Reduction
    cost_100_llm_usd = monthly_churn_population * llm_cost_per_dialogue_usd
    cost_hybrid_usd = (monthly_churn_population * gray_zone_ratio) * llm_cost_per_dialogue_usd
    llm_savings_usd = cost_100_llm_usd - cost_hybrid_usd
    llm_savings_rub = llm_savings_usd * usd_to_rub
    llm_cost_reduction_pct = (llm_savings_usd / cost_100_llm_usd) * 100.0 if cost_100_llm_usd > 0 else 0.0

    # 5. B2B Account MRR Revenue Salvage
    # Status 4 Recall increased from 12.0% (Olga) to 60.2% (Hybrid Auditor).
    # That catches 48.2% more manager requests that previously resulted in churn.
    status_4_recall_gain = 0.482
    estimated_salvaged_accounts = (monthly_churn_population * 0.261) * status_4_recall_gain * 0.30  # 30% retention rate
    monthly_salvaged_mrr_rub = estimated_salvaged_accounts * avg_b2b_arpu_rub
    annual_salvaged_revenue_rub = monthly_salvaged_mrr_rub * 12.0

    # Total Business Economic Effect
    total_monthly_economic_impact_rub = monthly_fot_savings_rub + llm_savings_rub + monthly_salvaged_mrr_rub

    return {
        "monthly_churn_population": monthly_churn_population,
        "operator_capacity": operator_capacity,
        "unnecessary_calls_avoided": unnecessary_calls_avoided,
        "calls_routed_to_operators": calls_routed_to_operators,
        "hours_saved_per_month": hours_saved_per_month,
        "monthly_fot_savings_rub": monthly_fot_savings_rub,
        "annual_fot_savings_rub": annual_fot_savings_rub,
        "cost_100_llm_usd": cost_100_llm_usd,
        "cost_hybrid_usd": cost_hybrid_usd,
        "llm_savings_usd": llm_savings_usd,
        "llm_savings_rub": llm_savings_rub,
        "llm_cost_reduction_pct": llm_cost_reduction_pct,
        "estimated_salvaged_accounts": estimated_salvaged_accounts,
        "monthly_salvaged_mrr_rub": monthly_salvaged_mrr_rub,
        "annual_salvaged_revenue_rub": annual_salvaged_revenue_rub,
        "total_monthly_economic_impact_rub": total_monthly_economic_impact_rub
    }

def print_business_roi_report(roi):
    print("=" * 70)
    print("💼 TELE2 B2B BUSINESS ROI & OPERATIONAL CAPACITY IMPACT")
    print("=" * 70)
    print(f"Ежемесячный объем выборки оттока  : {roi['monthly_churn_population']:,} B2B-клиентов")
    print(f"Лимит Группы сохранения (операторов): {roi['operator_capacity']:,} звонков/мес")
    print("-" * 70)
    print(f"Отсеяно непрофильных звонков        : {roi['unnecessary_calls_avoided']:,.0f} звонков/мес")
    print(f"Экономия рабочего времени операторов: {roi['hours_saved_per_month']:,.1f} чел-часов/мес")
    print(f"💰 Прямая экономия ФОТ операторов   : {roi['monthly_fot_savings_rub']:,.2f} ₽/мес ({roi['annual_fot_savings_rub']:,.2f} ₽/год)")
    print("-" * 70)
    print(f"Затраты на 100% LLM (без фильтров)  : ${roi['cost_100_llm_usd']:,.2f}/мес")
    print(f"Затраты на Hybrid Pipeline (Stage 1-6): ${roi['cost_hybrid_usd']:,.2f}/мес")
    print(f"⚡ Снижение расходов на AI API      : {roi['llm_cost_reduction_pct']:.1f}% (${roi['llm_savings_usd']:,.2f}/мес = {roi['llm_savings_rub']:,.2f} ₽/мес)")
    print("-" * 70)
    print(f"Спасенных B2B-аккаунтов (Recall S4) : ~{roi['estimated_salvaged_accounts']:,.0f} клиентов/мес")
    print(f"📈 Сбереженная выручка MRR (ARPU)   : {roi['monthly_salvaged_mrr_rub']:,.2f} ₽/мес ({roi['annual_salvaged_revenue_rub']:,.2f} ₽/год)")
    print("=" * 70)
    print(f"🔥 ИТОГОВЫЙ СУММАРНЫЙ ЭКОНОМИЧЕСКИЙ ЭФФЕКТ: {roi['total_monthly_economic_impact_rub']:,.2f} ₽ / МЕСЯЦ")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    roi = calculate_business_roi()
    print_business_roi_report(roi)
