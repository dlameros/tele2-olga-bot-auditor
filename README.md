# 🤖 Tele2 Olga Bot Auditor (Verification & Fallback System)

[![Hackathon Award](https://img.shields.io/badge/Tele2%20Hackathon-🥈%202nd%20Place-FFD700?style=for-the-badge&logo=trophy)](https://tele2.ru)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Architecture](https://img.shields.io/badge/Architecture-Hybrid%20(Rule--Based%20%2B%20LLM)-brightgreen?style=for-the-badge)](#-архитектура-пайплайна)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge)](#)

> **Система аудит-контроля и валидации решений голосового робота «Ольга» в B2B-сегменте Tele2.**  
> Гибридный пайплайн (Rule-Based Engine + LLM Fallback) для выявления ошибок классификации оттока корпоративных клиентов, снижения нагрузки на группу сохранения и оптимизации дерева диалогов.

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

## 💡 Наше решение: Гибридная архитектура (Rule-Based + LLM)

Мы разработали двухстадийный гибридный пайплайн, сочетающий высокоскоростную детерминированную фильтрацию и семантический анализ через LLM.

```
                    ┌──────────────────────────────┐
                    │      transcript.csv          │
                    │   (Исходные 8000+ диалогов)  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ⚡ STAGE 1: Deterministic Rule-Based Engine (Python / Pandas / ReEx)│
│                                                                     │
│  [script_1] ──► Фильтрация молчания / Недозвонов (No Human Reply)   │
│  [script_2] ──► Фильтрация Автоответчиков и Голосовой почты        │
│  [script_2.1] ──► Выделение Негатива на сам факт звонка             │
│  [script_3] ──► Выделение Явного Согласия (True Stay / Сохранение)   │
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
│ 🧠 STAGE 2: LLM Fallback Analyzer (Zero-Shot / Few-Shot Reasoning)  │
│                                                                     │
│  [script_6_llm.py] ──► OpenAI / vLLM / Ollama API / Fallback Mode   │
│  • Анализ сарказма, сложных вводных конструкций ("Да нет наверно")   │
│  • Контекстный анализ реплик и запросов персонального менеджера      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 📊 STAGE 3 & 4: Audit Report & Metrics Evaluation (eval_metrics.py) │
│                                                                     │
│  • Сравнение: Робот "Ольга" vs Истинный статус (Confusion Matrix)   │
│  • Окончательный отчет аудит-контроля                               │
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
| **Step 6** | [`script_6_llm.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_6_llm.py) | **LLM Fallback Classification:** Разбор "серой зоны" через LLM API (OpenAI/Ollama/vLLM) или встроенный семантический модуль. | [`llm_results.csv`](file:///c:/Users/Dlameros/Desktop/rule_based/llm_results.csv) |
| **Eval** | [`eval_metrics.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_metrics.py) | **Metrics Evaluation:** Расчет Accuracy, Precision, Recall, F1 и Confusion Matrix на тестовом датасете. | Консольный аудит-отчет |

---

## 📈 Подтвержденные Метрики (Бенчмарк `318_test.csv`)

| Метрика | Робот «Ольга» (Baseline) | Hybrid Auditor (Rule + LLM) | Прирост / Улучшение |
|---|---|---|---|
| **Accuracy (Точность)** | **46.86%** | **49.37%** | **+2.51%** |
| **Error Rate (Ошибка)** | **53.14%** | **50.63%** | **-2.51%** |
| **Macro F1-Score** | **0.3854** | **0.4116** | **+0.0262 (+6.8% рост качества)** |
| **Precision (Отток - Status 2)** | **30.6%** | **38.5%** | **+7.9% (снижение ложных вызовов)** |
| **Recall (Менеджер - Status 4)**| **12.0%** | **44.6%** | **+32.6% (рост полноты перевода на менеджера в 3.7 раза)** |

---

## 💼 Бизнес-эффект и ROI в B2B-сегменте Tele2

При масштабировании системы на ежемесячный объем выборки оттока **8 000 B2B-клиентов**:

| Показатель Бизнес-эффекта | Значение | Экономический результат |
|---|---|---|
| **Отсев непрофильных звонков** | **3 600 звонков/мес** | Автоматическая обработка без участия операторов |
| **Экономия времени Группы сохранения** | **300.0 чел-часов/мес** | Освобождение ресурса операторов для сложных LTV-клиентов |
| **Прямая экономия ФОТ операторов** | **135 000 ₽ / мес** | **~1 620 000 ₽ / год** снижения затрат на фонд оплаты труда |
| **Оптимизация LLM API расходов** | **-59.0% затрат на AI** | Снижение стоимости обращений к LLM с $120/мес до $49.20/мес |
| **Спасенная выручка B2B (MRR)** | **~302 аккаунта / мес** | **~452 887 ₽ / мес (~5.43 Млн ₽ / год)** сбереженного дохода |
| **🔥 СУММАРНЫЙ ЭКОНОМИЧЕСКИЙ ЭФФЕКТ** | **594 400 ₽ / мес** | **~7.13 Млн ₽ / год** суммарной выгоды для компании |

---

## 🛠 Стек технологий

* **Core:** Python 3.9+
* **Data Processing & Analytics:** Pandas, NumPy
* **NLP & Matching:** Regex (`re`), Custom B2B Semantic Parsers
* **LLM Layer:** OpenAI API / GigaChat / YandexGPT / Local LLM (vLLM / Ollama) via [`script_6_llm.py`](file:///c:/Users/Dlameros/Desktop/rule_based/script_6_llm.py)
* **Evaluation & ROI Engine:** [`eval_pipeline.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_pipeline.py), [`eval_metrics.py`](file:///c:/Users/Dlameros/Desktop/rule_based/eval_metrics.py), [`business_metrics.py`](file:///c:/Users/Dlameros/Desktop/rule_based/business_metrics.py)

---

## 🚀 Как запустить

### 1. Клонирование репозитория и установка зависимостей
```bash
git clone https://github.com/dlameros/tele2-olga-bot-auditor.git
cd tele2-olga-bot-auditor

# Установка базовых библиотек
pip install pandas numpy openai
```

### 2. (Опционально) Настройка ключа LLM API
Если вы хотите использовать внешний API (OpenAI / vLLM / Ollama):
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```
*(При отсутствии ключа система автоматически задействует встроенный семантический LLM-эквивалент в автономном режиме)*.

### 3. Запуск полного пайплайна, метрик и бизнес-отчета ROI
```bash
python main.py
```

---

<div align="center">
  <sub>Разработано в рамках хакатона Tele2 • 2026</sub>
</div>
