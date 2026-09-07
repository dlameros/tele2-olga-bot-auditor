import pandas as pd
import numpy as np
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_pure_ai_agent_roi(
    monthly_churn_population=8000,
    avg_call_duration_min=5.0,
    operator_hourly_rate_rub=450.0,
    avg_b2b_arpu_rub=1500.0,
    llm_cost_per_dialogue_usd=0.015,
    usd_to_rub=92.0
):
    """
    Computes Autonomous AI Agent ROI (Fully replacing human verification operators).
    """
    # 1. Total Manual Operator Cost (Without AI Agent)
    total_operator_hours_needed = (monthly_churn_population * avg_call_duration_min) / 60.0  # 666.7 hours
    total_manual_fot_cost_rub = total_operator_hours_needed * operator_hourly_rate_rub      # 300,000 ₽ / month
    
    # 2. Autonomous AI Agent Automation Rate
    # AI Agent autonomously classifies 85% of cases (Status 1, 2, 3) without human intervention.
    ai_autonomous_ratio = 0.85
    human_vip_escalation_ratio = 0.15
    
    calls_handled_by_ai = monthly_churn_population * ai_autonomous_ratio       # 6,800 calls auto-processed
    calls_handled_by_human = monthly_churn_population * human_vip_escalation_ratio # 1,200 VIP manager calls
    
    # 3. Direct Operator Labor Savings
    hours_saved_by_ai = (calls_handled_by_ai * avg_call_duration_min) / 60.0  # 566.7 hours saved
    monthly_fot_savings_rub = hours_saved_by_ai * operator_hourly_rate_rub     # 255,000 ₽ / month
    annual_fot_savings_rub = monthly_fot_savings_rub * 12.0                   # 3,060,000 ₽ / year
    
    # 4. AI Agent Infrastructure Cost (Hybrid Rule + LLM Routing)
    # 59% filtered deterministically by python engine ($0), 41% routed to LLM API
    llm_calls = monthly_churn_population * 0.41
    monthly_llm_cost_usd = llm_calls * llm_cost_per_dialogue_usd              # $49.20 / month
    monthly_llm_cost_rub = monthly_llm_cost_usd * usd_to_rub                  # ~4,526 ₽ / month
    
    # Net Operational Automation Savings
    net_monthly_operational_savings_rub = monthly_fot_savings_rub - monthly_llm_cost_rub

    # 5. Salvaged B2B Revenue (AI Agent catches 3.7x more Manager Escalations)
    salvaged_b2b_accounts_monthly = monthly_churn_population * 0.261 * 0.446 * 0.35  # ~326 accounts saved
    monthly_salvaged_mrr_rub = salvaged_b2b_accounts_monthly * avg_b2b_arpu_rub       # ~489,000 ₽ / month
    annual_salvaged_revenue_rub = monthly_salvaged_mrr_rub * 12.0                      # ~5.87 Million ₽ / year

    # Total Business Impact
    total_monthly_economic_impact_rub = net_monthly_operational_savings_rub + monthly_salvaged_mrr_rub
    total_annual_economic_impact_rub = total_monthly_economic_impact_rub * 12.0

    return {
        "monthly_churn_population": monthly_churn_population,
        "total_manual_fot_cost_rub": total_manual_fot_cost_rub,
        "calls_handled_by_ai": calls_handled_by_ai,
        "calls_handled_by_human": calls_handled_by_human,
        "hours_saved_by_ai": hours_saved_by_ai,
        "monthly_fot_savings_rub": monthly_fot_savings_rub,
        "annual_fot_savings_rub": annual_fot_savings_rub,
        "monthly_llm_cost_usd": monthly_llm_cost_usd,
        "monthly_llm_cost_rub": monthly_llm_cost_rub,
        "net_monthly_operational_savings_rub": net_monthly_operational_savings_rub,
        "salvaged_b2b_accounts_monthly": salvaged_b2b_accounts_monthly,
        "monthly_salvaged_mrr_rub": monthly_salvaged_mrr_rub,
        "annual_salvaged_revenue_rub": annual_salvaged_revenue_rub,
        "total_monthly_economic_impact_rub": total_monthly_economic_impact_rub,
        "total_annual_economic_impact_rub": total_annual_economic_impact_rub
    }

def print_pure_ai_agent_roi_report(roi):
    print("=" * 75)
    print("🤖 TELE2 B2B AUTONOMOUS AI AGENT ROI (FULL HUMAN OPERATOR REPLACEMENT)")
    print("=" * 75)
    print(f"Общий выборка оттока B2B            : {roi['monthly_churn_population']:,} клиентов/мес")
    print(f"Затраты на ручной обзвон (без ИИ)   : {roi['total_manual_fot_cost_rub']:,.2f} ₽/мес")
    print("-" * 75)
    print(f"⚡ Автономно обработано ИИ-агентом   : {roi['calls_handled_by_ai']:,.0f} звонков/мес (85%)")
    print(f"👤 Передано персональным менеджерам : {roi['calls_handled_by_human']:,.0f} VIP-кейсов/мес (15%)")
    print(f"⏱ Сбережено рабочего времени        : {roi['hours_saved_by_ai']:,.1f} чел-часов/мес")
    print(f"💰 Прямая экономия на персонале    : {roi['monthly_fot_savings_rub']:,.2f} ₽/мес ({roi['annual_fot_savings_rub']:,.2f} ₽/год)")
    print(f"💳 Затраты на инфраструктуру ИИ-агента: {roi['monthly_llm_cost_rub']:,.2f} ₽/мес (${roi['monthly_llm_cost_usd']:.2f}/мес)")
    print(f"✅ ЧИСТАЯ ЭКОНОМИЯ НА АВТОМАТИЗАЦИИ : {roi['net_monthly_operational_savings_rub']:,.2f} ₽/мес")
    print("-" * 75)
    print(f"Спасенных B2B-аккаунтов (Recall S4) : ~{roi['salvaged_b2b_accounts_monthly']:,.0f} аккаунтов/мес")
    print(f"📈 Сбереженная выручка MRR (ARPU)   : {roi['monthly_salvaged_mrr_rub']:,.2f} ₽/мес ({roi['annual_salvaged_revenue_rub']:,.2f} ₽/год)")
    print("=" * 75)
    print(f"🔥 ПОЛНЫЙ ЭКОНОМИЧЕСКИЙ ЭФФЕКТ ИИ-АГЕНТА: {roi['total_monthly_economic_impact_rub']:,.2f} ₽ / МЕСЯЦ ({roi['total_annual_economic_impact_rub']:,.2f} ₽ / ГОД)")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    roi = calculate_pure_ai_agent_roi()
    print_pure_ai_agent_roi_report(roi)
