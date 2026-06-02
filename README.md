# 📊 Аналитические дашборды для бонусной программы

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3.0+-green.svg)](https://plotly.com/)
[![Pandas](https://img.shields.io/badge/Pandas-1.3+-red.svg)](https://pandas.pydata.org/)

Интерактивные веб-дашборды для анализа ключевых показателей эффективности (KPI) и A/B/C/D-тестирования бонусной программы. Включает классическую статистику и байесовские методы.

## 🎯 Возможности

### 📈 KPI Дашборд
- **Два режима анализа**: базовый (1 показатель) и расширенный (2+ показателей)
- **Динамические графики**: линейные, столбчатые, точечные диаграммы
- **Drag & Drop интерфейс**: перемещение и изменение размеров графиков
- **Группировка метрик**: структурированный выбор показателей по категориям
- **Фильтрация по датам**: глобальные и индивидуальные периоды

### 🔬 A/B/C/D Тест-дашборд
- **Гибридная статистика**: классические тесты + байесовский подход
- **Автоматический расчет**:
  - ANOVA с пост-хок анализом (Tukey HSD)
  - χ²-тест с Cramér's V для удержания
  - t-критерий с Cohen's d и доверительными интервалами
  - Байесовский бутстрап (10,000 итераций)
- **Метрики эффективности**: ROI, ROMI, бонусная эффективность
- **Возрастной анализ**: распределение клиентов по группам
- **Аплифты**: абсолютные и относительные приросты vs контроль

## 📁 Структура проекта

Dashboards/
├── kpi_dashboard.py # Генератор KPI дашборда
├── ab_test_dashboard.py # Генератор A/B/C/D тест-дашборда
├── requirements.txt # Зависимости
├── data/
│ ├── data.xlsx # Исходные данные (KPI)
│ ├── push_age_data.csv # Возрастные данные (опционально)
│ ├── sms_age_data.csv
│ ├── combined_age_data.csv
│ └── control_age_data.csv
└── outputs/
├── kpi_dashboard_dual_mode.html
└── ab_test_hybrid_dashboard.html

##Примеры 
*представленые данные носят исключительно ознакомительный характер.

<img width="1896" height="915" alt="image" src="https://github.com/user-attachments/assets/b0f3d14d-70bf-42eb-848f-4dbf8d71be03" />
<img width="1901" height="918" alt="image" src="https://github.com/user-attachments/assets/d680f6c0-83d4-471f-9dd4-859d22363875" />
<img width="1910" height="890" alt="image" src="https://github.com/user-attachments/assets/e5d344d5-52e3-4774-9a71-53d8481984ca" />


