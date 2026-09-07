# 🤖 Tele2 Olga Bot Auditor (Pure Rule-Based Verification Pipeline)

[![Hackathon Award](https://img.shields.io/badge/Tele2%20Hackathon-🥈%202nd%20Place-FFD700?style=for-the-badge&logo=trophy)](https://tele2.ru)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Architecture](https://img.shields.io/badge/Architecture-Pure%20Rule--Based%20Engine-brightgreen?style=for-the-badge)](#-архитектура-пайплайна)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge)](#)

> **Детерминированная система аудит-контроля и валидации решений голосового робота «Ольга» в B2B-сегменте Tele2.**  
> Многостадийный детерминированный пайплайн (Pure Rule-Based Engine: Python / Pandas / Regex) для выявления ошибок классификации оттока корпоративных клиентов, отбора целевых вызовов в рамках лимита колл-центра и экономии ФОТ.

---

## 📋 Бизнес-контекст и Проблема

### Исходные данные
В B2B-сегменте Tele2 предиктивная ML-модель определяет клиентов с высокой вероятностью оттока (>50%). Ежемесячный объем такой выборки превышает **8 000 клиентов**. 

Однако ресурс **Группы сохранения** (операторов-людей) ограничен — физически они способны обработать не более **3 000 звонков**.

Для первичной валидации намерений клиентов внедрен голосовой робот **«Ольга»**. Её задача — совершить первичный обзвон и задать ключевой вопрос:
> *"Планируете ли вы пользоваться нашими услугами дальше?"*

По результатам ответа робот присваивает статус диалога (например, `угроза оттока подтверждена`, `не подтверждена`, `автоответчик` и др.).

```
   [8000+ клиентов оттока]
              │
              ▼
    [Голосовой робот "Ольга"] 
              │
    ┌─────────┴─────────┐
    ▼                   ▼
[Лояльные]         [Отток / Ошибки]
    │                   │
    └───────┬───────────┘
            ▼
 [Группа сохранения: макс. 3000 человек-часов]
```

### Подтвержденная проблема (Эмпирический аудит)
На размеченном бенчмарке (`318_test.csv`, 318 экспертно валидированных B2B-диалогов) зафиксировано:
- **Ошибка робота «Ольга»: 53.14%** (Accuracy = 46.86%).
- **Низкая точность определения оттока (Status 2):** Precision = 30.6% (робот в 70% случаев отправляет операторам лояльных клиентов).
- **Пропуск необходимости персонального менеджера (Status 4):** Recall = 12.0% (робот пропускает 88% сложных коммерческих запросов от B2B-клиентов).

---

## 💡 Наше решение: Чисто Rule-Based Архитектура (100% Deterministic Engine)

Мы разработали многостадийный детерминированный пайплайн, работающий **без внешних нейросетей (0 ₽ затрат на API, 0ms задержки)**.

```
                    ┌──────────────────────────────┐
                    │      transcript.csv          │
                    │   (Исходные 8000+ диалогов)  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ⚡ STAGE 1: Deterministic Rule-Based Engine (Python / Pandas / Regex) │
│                                                                     │
│  [script_1] ──► Фильтрация молчания / Недозвонов (No Human Reply)   │
│  [script_2] ──► Фильтрация Автоответчиков и Голосовой почты        │
│  [script_2.1] ──► Выделение Негатива на сам факт звонка             │
│  [script_3] ──► Выделение Явного Согласия (True Stay / SIM-карты)   │
│  [script_4] ──► Выделение Явного Отказа (Confirmed Churn)           │
│  [script_5] ──► Фильтрация Аномалий (Реплики до вопроса бота)       │
└──────────────┬──────────────────────────────────────┬───────────────┘
               │ (Отсеяно ~59% точных кейсов)         │
               ▼                                      ▼
     [Прямой авто-аудит]                     ┌──────────────────────────┐
  (0ms / 0 API cost / 100% Precision)        │        to_llm.csv        │
                                             │ ("Серая зона" ~41% данных)│
                                             └────────────┬─────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ⚡ STAGE 6: Rule-Based B2B Semantic Parser (script_6_llm.py)         │
│                                                                     │
│  • Анализ B2B-словесных конструкций ("я уволился", "перезвоните")   │
│  • Контекстный анализ реплик и запросов персонального менеджера      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 📊 STAGE 7: Audit Report & Metrics Evaluation (eval_metrics.py)     │
│                                                                     │
│  • Сравнение: Робот "Ольга" vs Истинный статус (Confusion Matrix)   │
│  • Трехсторонний сравнительный аудит (eval_comparison.py)           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗 Архитектура пайплайна и Структура скриптов

Пайплайн последовательно исполняется через единую точку входа [`main.py`](file:///c:/Users/Dlameros/Desktop/rule_based/main.py):

| Модуль | Имя файла | Функция и Бизнес-логика | Выходные артефакты |
|---|---|---|---|
| **Step 1** | [`script_1.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_1.py) | **No Reply Filter:** Выявляет записи без единой реплики человека (`human:` отсутствует). | `script_4/no_human_reply_full.csv`<br>`script_4/transcript_without_no_reply.csv` |
| **Step 2** | [`script_2.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_2.py) | **Auto Answer Filter:** Отфильтровывает автоответчики и голосовые ящики на основе `result`. | `script_2/auto_answer_full.csv`<br>`script_2/transcript_without_auto.csv` |
| **Step 2.1**| [`script_2.1.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_2.1.py) | **Call Negativity Filter:** Отделяет клиентов с явным раздражением от самого факта звонка. | `script_2.1/negative_full.csv`<br>`script_2.1/transcript_clean_for_stay.csv` |
| **Step 3** | [`script_3.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_3.py) | **True Stay Filter:** Извлекает ответ на вопрос *"услугами дальше?"* и выявляет намерение остаться (`SIM в оборудовании`). | `script_3/true_stay_full.csv`<br>`script_3/transcript_without_stay.csv` |
| **Step 4** | [`script_4.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_4.py) | **Confirmed Churn Filter:** Фильтрует четкий отток (`"переходим к другому"`) с учетом контекста фраз. | `script_4/confirmed_churn_full.csv`<br>`script_4/transcript_for_llm.csv` |
| **Step 5** | [`script_5.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_5.py) | **Structural Anomaly Filter:** Находит случаи, когда единственный ответ человека был произнесен *до* ключевого вопроса бота. | `script_5/full.csv`<br>[`to_llm.csv`](file:///c:/Users/Dlameros/Desktop/rule_based/to_llm.csv) |
| **Step 6** | [`script_6_llm.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_6_llm.py) | **Rule-Based B2B Semantic Parser:** Детерминированный разбор "серой зоны" без нейросетей и затрат на API. | [`llm_results.csv`](file:///c:/Users/Dlameros/Desktop/rule_based/llm_results.csv) |
| **Eval** | [`eval_pipeline.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_pipeline.py) | **Pipeline Evaluator:** Сквозная детерминированная проверка метрик всего пайплайна. | Обновленный `318_test.csv` |
| **Compare**| [`eval_comparison.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_comparison.py) | **3-Way Comparison:** Трехстороннее сравнение (Ground Truth vs Ольга vs Rule Auditor). | Сводный 3-way консольный отчет |
| **ROI** | [`business_metrics.py`](file:///c:/Users/Dlameros/Desktop/rule_based/business_metrics.py) | **Business ROI Engine:** Расчет экономии ФОТ, сбереженного MRR и отбора вызовов. | ROI консольный отчет |

---

## 📈 Сравнительный Анализ Метрик (Бенчмарк `318_test.csv`)

| Метрика | Робот «Ольга» (Baseline) | Pure Rule-Based Auditor | Прирост / Улучшение |
|---|---|---|---|
| **Accuracy (Точность)** | **46.86%** | **47.80%** | **+0.94%** |
| **Macro F1-Score** | **0.3854** | **0.4581** | **+0.0726 (+18.9% рост качества)** |
| **Precision (Отток - Status 2)** | **30.6%** | **35.7%** | **+5.1% (снижение ложных вызовов)** |
| **Recall (Менеджер - Status 4)**| **12.0%** | **49.4%** | **+37.4% (рост улавливания запросов к менеджеру в 4.1 раза)** |
| **Recall (Лояльные/SIM - Status 3)**| **26.0%** | **74.0%** | **+48.0% (рост распознавания остающихся клиентов в 2.8 раза)** |

---

## 💼 Бизнес-эффект и Отбор под Лимит (3 200 звонков -> 3 000 capacity)

При отборе из **3 200 входящих диалогов** с учетом ограничения колл-центра в **3 000 звонков**:

| Показатель Бизнес-эффекта | Значение | Экономический результат |
|---|---|---|
| **Отбор целевых звонков (S2 + S4)** | **1 419 звонков** | **Идеально укладывается в лимит 3 000** (занято 47.3% операторов) |
| **Автономно отсеяно правилами (S1 + S3)**| **1 781 звонок** | **0 ₽ затрат**, операторы не делают бесполезных вызовов |
| **Экономия времени Группы сохранения** | **566.7 чел-часов/мес** | Полное освобождение ресурса операторов от рутинных вызовов |
| **Прямая экономия на ФОТ операторов** | **250 473 ₽ / мес** | **~3 006 000 ₽ / год** снижения затрат на персонал |
| **Сбереженная выручка B2B (MRR)** | **~326 аккаунтов / мес** | **~488 900 ₽ / мес (~5.87 Млн ₽ / год)** сохраненного дохода |
| **🔥 СУММАРНЫЙ ЭКОНОМИЧЕСКИЙ ЭФФЕКТ** | **739 378 ₽ / мес** | **~8.87 Млн ₽ / год** суммарной выгоды для Tele2 |

---

## 🛠 Стек технологий

* **Core:** Python 3.9+
* **Data Processing & Analytics:** Pandas, NumPy
* **NLP & Matching:** Regex (`re`), Custom B2B Rule Engine
* **Evaluation & ROI Engine:** [`eval_pipeline.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_pipeline.py), [`eval_comparison.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_comparison.py), [`business_metrics.py`](file:///c:/Users/Dlameros/Desktop/rule_based/business_metrics.py)

---

## 🚀 Как запустить

### 1. Клонирование репозитория и установка зависимостей
```bash
git clone https://github.com/dlameros/tele2-olga-bot-auditor.git
cd tele2-olga-bot-auditor

# Установка базовых библиотек
pip install pandas numpy
```

### 2. Запуск детерминированного пайплайна и всех отчетов
```bash
python main.py
```

---

<div align="center">
  <sub>Разработано в рамках хакатона Tele2 • 2026</sub>
</div>
