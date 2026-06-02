import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import html
from collections import defaultdict

# ---------- 1. ЗАГРУЗКА ДАННЫХ ----------
filepath = '.xlsx'

# Читаем весь файл
df_all = pd.read_excel(filepath, header=None)

# Заголовки (даты) на строке 2 (индекс 2), начиная с колонки 3
headers_row = df_all.iloc[2, 3:].tolist()
dates = []
for h in headers_row:
    if pd.notna(h) and h != 'Источник':
        try:
            if isinstance(h, (pd.Timestamp, datetime)):
                dates.append(h)
            else:
                dates.append(pd.to_datetime(h))
        except:
            pass

# Собираем данные
data_dict = {}
current_group = None

for idx in range(3, len(df_all)):
    row = df_all.iloc[idx]

    col1 = row.iloc[1] if pd.notna(row.iloc[1]) else None
    col2 = row.iloc[2] if pd.notna(row.iloc[2]) else None

    if pd.notna(col1):
        current_group = col1

    values = []
    for i, date in enumerate(dates):
        val = row.iloc[3 + i] if (3 + i) < len(row) else None
        values.append(val)

    if pd.notna(col2):
        key = (current_group if current_group else 'Общие', col2)
        data_dict[key] = values

# Принудительно добавляем строки
forced_indicators = ['АКБ (год/все) %', 'АКБ (месяц/год) %', 'Пересчет доли АК факт (реконструкция), %',
                     'План АК, %', 'Отклонение АК факт от плана, п.п.%']

for idx, indicator in enumerate(forced_indicators):
    row_idx = 9 + idx
    if row_idx < len(df_all):
        row = df_all.iloc[row_idx]
        values = []
        for i in range(len(dates)):
            val = row.iloc[3 + i] if (3 + i) < len(row) else None
            values.append(val)
        if any(pd.notna(v) for v in values):
            key = ('Клиентская База', indicator)
            data_dict[key] = values

# Преобразуем в длинный формат
long_rows = []
for (group, indicator), values in data_dict.items():
    for i, date in enumerate(dates):
        if i < len(values) and pd.notna(values[i]):
            val = values[i]
            if pd.notna(val):
                try:
                    numeric_val = float(val)
                except (ValueError, TypeError):
                    numeric_val = val

                long_rows.append({
                    'Бонусная карта': group,
                    'Показатель': indicator,
                    'Дата': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'Значение': numeric_val
                })

df_long = pd.DataFrame(long_rows)
df_long['Полный показатель'] = df_long['Бонусная карта'].astype(str) + ' → ' + df_long['Показатель'].astype(str)
df_long['Значение'] = pd.to_numeric(df_long['Значение'], errors='coerce')
df_long = df_long.dropna(subset=['Значение'])

# Сохраняем данные в JSON
data_json = df_long.to_json(orient='records', date_format='iso')
metrics_list = sorted(df_long['Полный показатель'].unique())

# Создаем структуру групп для организованного отображения
groups_structure = defaultdict(list)
for metric in metrics_list:
    if ' → ' in metric:
        group, indicator = metric.split(' → ', 1)
        groups_structure[group].append({
            'full_name': metric,
            'indicator': indicator
        })
    else:
        groups_structure['Прочее'].append({
            'full_name': metric,
            'indicator': metric
        })

# Сортируем группы и показатели внутри групп
groups_structure = dict(sorted(groups_structure.items()))
for group in groups_structure:
    groups_structure[group] = sorted(groups_structure[group], key=lambda x: x['indicator'])

# Получаем список всех дат
all_dates = sorted(df_long['Дата'].unique())
min_date = all_dates[0]
max_date = all_dates[-1]


# ---------- 2. СОЗДАНИЕ ОФЛАЙН HTML ДАШБОРДА С ДВУМЯ РЕЖИМАМИ ----------
def create_offline_dashboard():
    # Создаем HTML для структурированного выбора метрик
    def build_structured_metrics_html():
        html_parts = []
        for group, metrics in groups_structure.items():
            # Заголовок группы
            group_id = f"group_{group.replace(' ', '_').replace('→', '').replace('&', '').replace('(', '').replace(')', '').replace(',', '')}"
            html_parts.append(f'''
            <div class="metric-group">
                <div class="metric-group-header" onclick="toggleGroup('{group_id}')">
                    <span class="group-toggle" id="{group_id}-toggle">▼</span>
                    <span class="group-name">📁 {html.escape(group)}</span>
                    <span class="group-count">({len(metrics)})</span>
                    <div class="group-actions">
                        <button class="group-select-all" onclick="event.stopPropagation(); selectGroupAll('{group_id}')">✅ Выбрать все</button>
                        <button class="group-clear-all" onclick="event.stopPropagation(); clearGroupAll('{group_id}')">❌ Очистить</button>
                    </div>
                </div>
                <div class="metric-group-content" id="{group_id}">
            ''')

            for metric in metrics:
                escaped_name = html.escape(metric['full_name'])
                short_name = html.escape(metric['indicator'][:60] + ('...' if len(metric['indicator']) > 60 else ''))
                html_parts.append(f'''
                    <label class="metric-checkbox">
                        <input type="checkbox" value="{escaped_name}" data-group="{group_id}">
                        <span class="checkbox-custom"></span>
                        <span class="metric-name" title="{escaped_name}">{short_name}</span>
                    </label>
                ''')

            html_parts.append('</div></div>')

        return ''.join(html_parts)

    # Формируем чекбоксы для базового режима (выпадающий список)
    select_options = '\n'.join([f'<option value="{html.escape(m)}">{html.escape(m)}</option>' for m in metrics_list])

    # Структурированные метрики для расширенного режима
    structured_metrics_html = build_structured_metrics_html()

    html_content = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI Бонусной программы - Дашборд</title>
    <script src="https://cdn.plot.ly/plotly-3.0.1.min.js" charset="utf-8"></script>
    <script src="https://cdn.jsdelivr.net/npm/interactjs@1.10.11/dist/interact.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            padding: 20px;
            overflow-x: auto;
        }}

        .container {{
            max-width: 100%;
            margin: 0 auto;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 1.8em;
            margin-bottom: 8px;
        }}

        .mode-switch {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 20px;
        }}

        .mode-btn {{
            padding: 10px 25px;
            font-size: 16px;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
        }}

        .mode-btn.active {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: transparent;
        }}

        .mode-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}

        .controls {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: none;
        }}

        .controls.active {{
            display: block;
        }}

        .control-group {{
            margin-bottom: 15px;
        }}

        .control-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }}

        select, input {{
            width: 100%;
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }}

        select:focus, input:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .metrics-structure {{
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            background: #fafbfc;
            max-height: 500px;
            overflow-y: auto;
        }}

        .metric-group {{
            border-bottom: 1px solid #e9ecef;
        }}

        .metric-group:last-child {{
            border-bottom: none;
        }}

        .metric-group-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 15px;
            background: #f8f9fa;
            cursor: pointer;
            user-select: none;
            transition: background 0.2s;
            border-left: 4px solid #667eea;
        }}

        .metric-group-header:hover {{
            background: #e9ecef;
        }}

        .group-toggle {{
            font-size: 12px;
            color: #667eea;
            font-weight: bold;
            width: 20px;
        }}

        .group-name {{
            font-weight: 600;
            color: #333;
            flex: 1;
        }}

        .group-count {{
            font-size: 12px;
            color: #868e96;
            background: #e9ecef;
            padding: 2px 8px;
            border-radius: 20px;
        }}

        .group-actions {{
            display: flex;
            gap: 8px;
        }}

        .group-select-all, .group-clear-all {{
            padding: 4px 10px;
            font-size: 11px;
            border-radius: 15px;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .group-select-all {{
            background: #d4f5d4;
            color: #2b8c2b;
        }}

        .group-select-all:hover {{
            background: #b8e6b8;
        }}

        .group-clear-all {{
            background: #ffe0e0;
            color: #c92a2a;
        }}

        .group-clear-all:hover {{
            background: #ffcccc;
        }}

        .metric-group-content {{
            padding: 10px 15px 15px 35px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 8px;
            background: white;
        }}

        .metric-group-content.collapsed {{
            display: none;
        }}

        .metric-checkbox {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 10px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 13px;
        }}

        .metric-checkbox:hover {{
            background: #f1f3f5;
        }}

        .metric-checkbox input {{
            display: none;
        }}

        .checkbox-custom {{
            width: 18px;
            height: 18px;
            border: 2px solid #adb5bd;
            border-radius: 4px;
            background: white;
            transition: all 0.2s;
            flex-shrink: 0;
        }}

        .metric-checkbox input:checked + .checkbox-custom {{
            background: #667eea;
            border-color: #667eea;
            position: relative;
        }}

        .metric-checkbox input:checked + .checkbox-custom::after {{
            content: '✓';
            color: white;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }}

        .metric-name {{
            color: #495057;
            line-height: 1.3;
            word-break: break-word;
        }}

        .selected-metrics {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
            padding: 12px;
            background: #e7f3ff;
            border-radius: 10px;
            min-height: 60px;
            border: 1px dashed #667eea;
        }}

        .metric-tag {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            max-width: 300px;
        }}

        .metric-tag button {{
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            padding: 0 5px;
            font-size: 16px;
            opacity: 0.8;
        }}

        .metric-tag button:hover {{
            opacity: 1;
        }}

        .row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}

        .button-group {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}

        button {{
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            font-weight: 500;
        }}

        button:hover {{
            background: #764ba2;
            transform: translateY(-1px);
        }}

        .btn-add {{
            background: #28a745;
        }}

        .btn-add:hover {{
            background: #218838;
        }}

        .btn-reset {{
            background: #dc3545;
        }}

        .btn-reset:hover {{
            background: #c82333;
        }}

        .btn-global {{
            background: #17a2b8;
        }}

        .btn-global:hover {{
            background: #138496;
        }}

        .charts-grid {{
            position: relative;
            min-height: 600px;
            margin-bottom: 20px;
        }}

        .chart-card {{
            position: absolute;
            background: white;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            transition: box-shadow 0.2s;
            z-index: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .chart-card:hover {{
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            z-index: 100;
        }}

        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
            cursor: grab;
            flex-shrink: 0;
        }}

        .chart-header:active {{
            cursor: grabbing;
        }}

        .chart-header h3 {{
            font-size: 12px;
            color: #333;
            margin: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
        }}

        .header-buttons {{
            display: flex;
            gap: 5px;
            margin-left: 8px;
        }}

        .chart-type-btn {{
            background: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            width: 28px;
            height: 28px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .remove-btn {{
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 4px;
            width: 28px;
            height: 28px;
            cursor: pointer;
            font-size: 16px;
        }}

        .chart-period {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #e0e0e0;
            font-size: 11px;
            flex-shrink: 0;
        }}

        .chart-period input {{
            flex: 1;
            padding: 4px 6px;
            font-size: 11px;
        }}

        .chart-container {{
            width: 100%;
            flex: 1;
            min-height: 0;
            position: relative;
        }}

        .resize-handle {{
            position: absolute;
            bottom: 5px;
            right: 5px;
            width: 16px;
            height: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 3px;
            cursor: nw-resize;
            z-index: 10;
        }}

        .stats-panel {{
            background: white;
            padding: 15px;
            border-radius: 15px;
            margin-top: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}

        .stat-item {{
            padding: 8px;
            background: #f8f9fa;
            border-radius: 6px;
            font-size: 12px;
        }}

        .stat-item strong {{
            color: #667eea;
        }}

        .search-box {{
            width: 100%;
            padding: 10px 12px;
            margin-bottom: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
        }}

        .search-box:focus {{
            border-color: #667eea;
            outline: none;
        }}

        @media (max-width: 768px) {{
            .chart-card {{
                position: relative !important;
                margin-bottom: 15px;
                width: 100% !important;
            }}
            .charts-grid {{
                position: static;
                display: flex;
                flex-direction: column;
            }}
            .resize-handle {{
                display: none;
            }}
            .metric-group-content {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KPI Бонусной программы</h1>
            <p>Анализ ключевых показателей эффективности</p>
        </div>

        <div class="mode-switch">
            <button class="mode-btn active" onclick="switchMode('single')">📈 Базовый режим (1 показатель)</button>
            <button class="mode-btn" onclick="switchMode('multi')">📊 Расширенный режим (2+ показателя)</button>
        </div>

        <!-- Базовый режим -->
        <div id="single-mode" class="controls active">
            <div class="row">
                <div class="control-group">
                    <label>📌 Показатель для добавления:</label>
                    <select id="metric-select-single">
                        {select_options}
                    </select>
                </div>
            </div>
            <div class="row">
                <div class="control-group">
                    <label>🌍 Глобальный период:</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="date" id="global-start-single" value="{min_date}">
                        <span>—</span>
                        <input type="date" id="global-end-single" value="{max_date}">
                    </div>
                </div>
            </div>
            <div class="button-group">
                <button onclick="addSingleChart()" class="btn-add">➕ Добавить график</button>
                <button onclick="applyGlobalPeriodSingle()" class="btn-global">🌍 Применить ко всем</button>
                <button onclick="resetAllSingle()" class="btn-reset">🗑 Удалить все</button>
            </div>
        </div>

        <!-- Расширенный режим -->
        <div id="multi-mode" class="controls">
            <div class="control-group">
                <label>📌 Выберите показатели для графика:</label>
                <input type="text" id="metrics-search" class="search-box" placeholder="🔍 Поиск показателей...">
                <div class="metrics-structure" id="metrics-structure">
                    {structured_metrics_html}
                </div>
                <div class="selected-metrics" id="selected-metrics">
                    <small style="color: #999;">Выберите показатели для нового графика</small>
                </div>
            </div>
            <div class="row">
                <div class="control-group">
                    <label>🌍 Глобальный период:</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="date" id="global-start-multi" value="{min_date}">
                        <span>—</span>
                        <input type="date" id="global-end-multi" value="{max_date}">
                    </div>
                </div>
            </div>
            <div class="button-group">
                <button onclick="addMultiChart()" class="btn-add">➕ Добавить график с выбранными</button>
                <button onclick="applyGlobalPeriodMulti()" class="btn-global">🌍 Применить ко всем</button>
                <button onclick="resetAllMulti()" class="btn-reset">🗑 Удалить все</button>
            </div>
        </div>

        <div id="charts-grid" class="charts-grid"></div>

        <div id="stats-panel" class="stats-panel" style="display: none;">
            <h4>📊 Статистика по графикам</h4>
            <div id="stats-grid" class="stats-grid"></div>
        </div>
    </div>

    <script>
        const chartData = {data_json};
        const metricsList = {json.dumps(metrics_list)};
        const globalMinDate = '{min_date}';
        const globalMaxDate = '{max_date}';

        let singleCharts = [];
        let multiCharts = [];
        let currentMode = 'single';
        let nextSingleId = 1;
        let nextMultiId = 1;
        let selectedMetricsForNew = [];

        const plotlyConfig = {{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines', 'toImage']
        }};

        function formatValue(value, metric) {{
            if (metric.includes('%')) return value.toFixed(2) + '%';
            if (metric.includes('руб') || metric.includes('бонус') || metric.includes('сумма')) return value.toLocaleString('ru-RU', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + ' ₽';
            return value.toLocaleString('ru-RU', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
        }}

        function filterDataByDateRange(data, startDate, endDate) {{
            return data.filter(d => d['Дата'] >= startDate && d['Дата'] <= endDate);
        }}

        function getMetricData(metric, startDate, endDate) {{
            let filteredData = chartData.filter(d => d['Полный показатель'] === metric);
            filteredData.sort((a, b) => new Date(a['Дата']) - new Date(b['Дата']));
            return filterDataByDateRange(filteredData, startDate, endDate);
        }}

        function toggleGroup(groupId) {{
            const content = document.getElementById(groupId);
            const toggle = document.getElementById(groupId + '-toggle');
            if (content) {{
                content.classList.toggle('collapsed');
                toggle.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
            }}
        }}

        function selectGroupAll(groupId) {{
            const checkboxes = document.querySelectorAll('#' + groupId + ' input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = true);
            updateSelectedMetrics();
        }}

        function clearGroupAll(groupId) {{
            const checkboxes = document.querySelectorAll('#' + groupId + ' input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = false);
            updateSelectedMetrics();
        }}

        function updateSelectedMetrics() {{
            const checkboxes = document.querySelectorAll('#metrics-structure input[type="checkbox"]');
            selectedMetricsForNew = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
            const container = document.getElementById('selected-metrics');
            if (selectedMetricsForNew.length === 0) {{
                container.innerHTML = '<small style="color: #999;">Выберите показатели для нового графика</small>';
            }} else {{
                container.innerHTML = selectedMetricsForNew.map(metric => 
                    `<div class="metric-tag">${{metric.length > 60 ? metric.substring(0, 57) + '...' : metric}}<button onclick="removeMetricFromSelection('${{metric.replace(/'/g, "\\\\'")}}')">×</button></div>`
                ).join('');
            }}
        }}

        function removeMetricFromSelection(metric) {{
            const checkbox = document.querySelector('#metrics-structure input[value="' + metric.replace(/"/g, '&quot;') + '"]');
            if (checkbox) {{ checkbox.checked = false; updateSelectedMetrics(); }}
        }}

        function searchMetrics() {{
            const searchTerm = document.getElementById('metrics-search').value.toLowerCase();
            const groups = document.querySelectorAll('.metric-group');
            groups.forEach(group => {{
                const groupName = group.querySelector('.group-name').textContent.toLowerCase();
                const metrics = group.querySelectorAll('.metric-checkbox');
                let hasVisible = false;
                metrics.forEach(metric => {{
                    const metricName = metric.querySelector('.metric-name').textContent.toLowerCase();
                    const isVisible = groupName.includes(searchTerm) || metricName.includes(searchTerm);
                    metric.style.display = isVisible ? 'flex' : 'none';
                    if (isVisible) hasVisible = true;
                }});
                group.style.display = hasVisible ? 'block' : 'none';
            }});
        }}

        function createSingleFigure(data, metric, chartType, customHeight = null, customWidth = null) {{
            if (!data || data.length === 0) {{
                return {{data: [{{x: [0], y: [0], type: 'scatter', mode: 'text', text: ['Нет данных за период'], textfont: {{size: 14, color: '#999'}}}}], layout: {{title: {{text: metric, font: {{size: 12}}}}, height: customHeight || 300, width: customWidth || null, xaxis: {{visible: false, fixedrange: true}}, yaxis: {{visible: false, fixedrange: true}}, margin: {{l: 40, r: 20, t: 40, b: 40}}}}}};
            }}
            const dates = data.map(d => d['Дата']);
            const values = data.map(d => d['Значение']);
            let trace = chartType === 'bar' 
                ? {{x: dates, y: values, type: 'bar', marker: {{color: '#667eea'}}, text: values.map(v => formatValue(v, metric)), textposition: 'outside'}}
                : chartType === 'scatter'
                    ? {{x: dates, y: values, mode: 'markers', type: 'scatter', marker: {{size: 7, color: '#ff6b6b'}}}}
                    : {{x: dates, y: values, mode: 'lines+markers', type: 'scatter', line: {{width: 2, color: '#667eea'}}, marker: {{size: 5, color: '#ff6b6b'}}}};
            return {{data: [trace], layout: {{title: {{text: metric, font: {{size: 11}}}}, xaxis: {{title: "Дата", tickangle: -45, fixedrange: true}}, yaxis: {{title: "Значение", fixedrange: true, tickformat: metric.includes('%') ? '.2f' : '', ticksuffix: metric.includes('%') ? '%' : ''}}, hovermode: 'closest', margin: {{l: 50, r: 20, t: 40, b: 70}}, height: customHeight, width: customWidth}}}};
        }}

        const colors = ['#667eea', '#ff6b6b', '#51cf66', '#ffd43b', '#ff8787', '#20c997', '#a9e34b', '#f06595', '#5f3dc4', '#94d82d'];

        function createMultiFigure(metrics, startDate, endDate, chartType, customHeight = null, customWidth = null) {{
            const traces = [];
            let hasData = false;
            metrics.forEach((metric, idx) => {{
                const data = getMetricData(metric, startDate, endDate);
                if (data && data.length > 0) {{
                    hasData = true;
                    const dates = data.map(d => d['Дата']);
                    const values = data.map(d => d['Значение']);
                    if (chartType === 'bar') {{
                        traces.push({{x: dates, y: values, name: metric.substring(0, 40), type: 'bar', marker: {{color: colors[idx % colors.length]}}, text: values.map(v => formatValue(v, metric)), textposition: 'outside'}});
                    }} else if (chartType === 'scatter') {{
                        traces.push({{x: dates, y: values, name: metric.substring(0, 40), mode: 'markers', type: 'scatter', marker: {{size: 8, color: colors[idx % colors.length]}}}});
                    }} else {{
                        traces.push({{x: dates, y: values, name: metric.substring(0, 40), mode: 'lines+markers', type: 'scatter', line: {{width: 2, color: colors[idx % colors.length]}}, marker: {{size: 6, color: colors[idx % colors.length]}}}});
                    }}
                }}
            }});
            if (!hasData) {{
                return {{data: [{{x: [0], y: [0], type: 'scatter', mode: 'text', text: ['Нет данных за период']}}], layout: {{title: 'Нет данных', height: customHeight || 300, width: customWidth}}}};
            }}
            return {{data: traces, layout: {{title: {{text: `Сравнение ${{metrics.length}} показателей`, font: {{size: 11}}}}, xaxis: {{title: "Дата", tickangle: -45, fixedrange: true}}, yaxis: {{title: "Значение", fixedrange: true}}, hovermode: 'x unified', legend: {{orientation: 'h', yanchor: 'bottom', y: -0.3, xanchor: 'center', x: 0.5, font: {{size: 9}}}}, margin: {{l: 50, r: 20, t: 40, b: 100}}, height: customHeight, width: customWidth}}}};
        }}

        function addSingleChart() {{
            if (singleCharts.length >= 12) {{ alert('Максимум 12 графиков!'); return; }}
            const metric = document.getElementById('metric-select-single').value;
            const offset = singleCharts.length * 30;
            singleCharts.push({{id: nextSingleId++, metric: metric, chartType: 'line', startDate: document.getElementById('global-start-single').value, endDate: document.getElementById('global-end-single').value, x: 20 + offset, y: 20 + offset, width: 550, height: 400}});
            renderAllCharts();
        }}

        function applyGlobalPeriodSingle() {{
            const globalStart = document.getElementById('global-start-single').value;
            const globalEnd = document.getElementById('global-end-single').value;
            singleCharts.forEach(chart => {{ chart.startDate = globalStart; chart.endDate = globalEnd; updateChartSize(chart.id, false); }});
            updateStats();
        }}

        function resetAllSingle() {{
            if (confirm('Удалить все графики в базовом режиме?')) {{ singleCharts = []; renderAllCharts(); }}
        }}

        function addMultiChart() {{
            if (selectedMetricsForNew.length === 0) {{ alert('Выберите хотя бы один показатель!'); return; }}
            if (multiCharts.length >= 12) {{ alert('Максимум 12 графиков!'); return; }}
            const offset = multiCharts.length * 30;
            multiCharts.push({{id: nextMultiId++, metrics: [...selectedMetricsForNew], chartType: 'line', startDate: document.getElementById('global-start-multi').value, endDate: document.getElementById('global-end-multi').value, x: 20 + offset, y: 20 + offset, width: 650, height: 450}});
            renderAllCharts();
        }}

        function applyGlobalPeriodMulti() {{
            const globalStart = document.getElementById('global-start-multi').value;
            const globalEnd = document.getElementById('global-end-multi').value;
            multiCharts.forEach(chart => {{ chart.startDate = globalStart; chart.endDate = globalEnd; updateChartSize(chart.id, true); }});
            updateStats();
        }}

        function resetAllMulti() {{
            if (confirm('Удалить все графики в расширенном режиме?')) {{ multiCharts = []; renderAllCharts(); }}
        }}

        function changeChartType(chartId, newType, isMulti) {{
            const charts = isMulti ? multiCharts : singleCharts;
            const chart = charts.find(c => c.id === chartId);
            if (chart) {{ chart.chartType = newType; updateChartSize(chartId, isMulti); }}
        }}

        function applyIndividualPeriod(chartId, isMulti) {{
            const charts = isMulti ? multiCharts : singleCharts;
            const chart = charts.find(c => c.id === chartId);
            if (chart) {{
                chart.startDate = document.getElementById(`start-${{chartId}}`).value;
                chart.endDate = document.getElementById(`end-${{chartId}}`).value;
                updateChartSize(chartId, isMulti);
                updateStats();
            }}
        }}

        function removeChart(chartId, isMulti) {{
            if (isMulti) multiCharts = multiCharts.filter(c => c.id !== chartId);
            else singleCharts = singleCharts.filter(c => c.id !== chartId);
            renderAllCharts();
        }}

        function updateChartSize(chartId, isMulti) {{
            const chartCard = document.getElementById(`chart-card-${{chartId}}`);
            const chartContainer = document.getElementById(`chart-${{chartId}}`);
            if (!chartCard || !chartContainer) return;
            const charts = isMulti ? multiCharts : singleCharts;
            const chartObj = charts.find(c => c.id === chartId);
            if (!chartObj) return;
            const availableHeight = chartCard.clientHeight - (chartCard.querySelector('.chart-header')?.offsetHeight || 45) - (chartCard.querySelector('.chart-period')?.offsetHeight || 55) - 20;
            const availableWidth = chartCard.clientWidth - 20;
            chartContainer.style.height = availableHeight + 'px';
            let figure = isMulti 
                ? createMultiFigure(chartObj.metrics, chartObj.startDate, chartObj.endDate, chartObj.chartType, availableHeight, availableWidth)
                : createSingleFigure(getMetricData(chartObj.metric, chartObj.startDate, chartObj.endDate), chartObj.metric, chartObj.chartType, availableHeight, availableWidth);
            Plotly.react(`chart-${{chartId}}`, figure.data, figure.layout, plotlyConfig);
        }}

        function updateStats() {{
            const statsPanel = document.getElementById('stats-panel');
            const statsGrid = document.getElementById('stats-grid');
            const allCharts = [...singleCharts, ...multiCharts];
            if (allCharts.length === 0) {{ statsPanel.style.display = 'none'; return; }}
            statsPanel.style.display = 'block';
            statsGrid.innerHTML = allCharts.map(chart => {{
                let html = `<div class="stat-item"><strong>📊 График #${{chart.id}}</strong><br>`;
                if (chart.metric) {{
                    const data = getMetricData(chart.metric, chart.startDate, chart.endDate);
                    if (data.length > 0) {{
                        const values = data.map(d => d['Значение']);
                        const mean = values.reduce((a,b) => a + b, 0) / values.length;
                        html += `📌 ${{chart.metric.substring(0, 50)}}<br>📈 ${{data.length}} точек | Сред: ${{formatValue(mean, chart.metric)}} | Мин: ${{formatValue(Math.min(...values), chart.metric)}} | Макс: ${{formatValue(Math.max(...values), chart.metric)}}`;
                    }}
                }} else if (chart.metrics) {{
                    html += `📌 ${{chart.metrics.length}} показателя:<br>`;
                    chart.metrics.forEach(metric => {{
                        const data = getMetricData(metric, chart.startDate, chart.endDate);
                        if (data.length > 0) {{
                            const values = data.map(d => d['Значение']);
                            const mean = values.reduce((a,b) => a + b, 0) / values.length;
                            html += `<div style="margin-left: 10px;">• ${{metric.substring(0, 40)}}: ${{formatValue(mean, metric)}}</div>`;
                        }}
                    }});
                }}
                return html + `</div>`;
            }}).join('');
        }}

        function renderAllCharts() {{
            const container = document.getElementById('charts-grid');
            container.innerHTML = '';
            const allCharts = [...singleCharts, ...multiCharts];
            if (allCharts.length === 0) {{
                container.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">Добавьте графики с помощью панели управления</div>';
                updateStats();
                return;
            }}
            container.style.height = Math.max(600, (Math.ceil(allCharts.length / 2) * 500)) + 'px';
            allCharts.forEach(chart => {{
                const isMulti = !!chart.metrics;
                const chartCard = document.createElement('div');
                chartCard.className = 'chart-card';
                chartCard.id = `chart-card-${{chart.id}}`;
                chartCard.style.cssText = `position:absolute; left:0; top:0; width:${{chart.width || (isMulti ? 650 : 550)}}px; height:${{chart.height || (isMulti ? 450 : 400)}}px; transform:translate(${{chart.x || 20}}px, ${{chart.y || 20}}px);`;
                chartCard.innerHTML = `
                    <div class="chart-header"><h3>${{isMulti ? `📈 Сравнение: ${{chart.metrics.length}} показателя` : (chart.metric || '').substring(0, 60)}}</h3>
                        <div class="header-buttons">
                            <button class="chart-type-btn" onclick="changeChartType(${{chart.id}}, 'line', ${{isMulti}})">📈</button>
                            <button class="chart-type-btn" onclick="changeChartType(${{chart.id}}, 'bar', ${{isMulti}})">📊</button>
                            <button class="chart-type-btn" onclick="changeChartType(${{chart.id}}, 'scatter', ${{isMulti}})">🔵</button>
                            <button class="remove-btn" onclick="removeChart(${{chart.id}}, ${{isMulti}})">×</button>
                        </div>
                    </div>
                    <div id="chart-${{chart.id}}" class="chart-container"></div>
                    <div class="chart-period">
                        <input type="date" id="start-${{chart.id}}" value="${{chart.startDate}}"><span>—</span>
                        <input type="date" id="end-${{chart.id}}" value="${{chart.endDate}}">
                        <button onclick="applyIndividualPeriod(${{chart.id}}, ${{isMulti}})">Применить</button>
                    </div>
                    <div class="resize-handle"></div>
                `;
                container.appendChild(chartCard);
                setTimeout(() => updateChartSize(chart.id, isMulti), 50);
                setupInteractions(`chart-card-${{chart.id}}`, chart.id, isMulti);
            }});
            updateStats();
        }}

        function setupInteractions(elementId, chartId, isMulti) {{
            const element = document.getElementById(elementId);
            if (!element) return;
            interact(element).draggable({{
                inertia: false,
                modifiers: [interact.modifiers.restrictRect({{ restriction: 'parent', endOnly: true }})],
                onmove: function (event) {{
                    const x = (parseFloat(event.target.getAttribute('data-x')) || 0) + event.dx;
                    const y = (parseFloat(event.target.getAttribute('data-y')) || 0) + event.dy;
                    event.target.style.transform = `translate(${{x}}px, ${{y}}px)`;
                    event.target.setAttribute('data-x', x);
                    event.target.setAttribute('data-y', y);
                    const charts = isMulti ? multiCharts : singleCharts;
                    const chart = charts.find(c => c.id == chartId);
                    if (chart) {{ chart.x = x; chart.y = y; }}
                }}
            }}).resizable({{
                edges: {{ bottom: true, right: true }},
                modifiers: [interact.modifiers.restrictSize({{ min: {{ width: 450, height: 350 }}, max: {{ width: 1400, height: 800 }} }})],
                onmove: function (event) {{
                    event.target.style.width = event.rect.width + 'px';
                    event.target.style.height = event.rect.height + 'px';
                    const charts = isMulti ? multiCharts : singleCharts;
                    const chart = charts.find(c => c.id == chartId);
                    if (chart) {{ chart.width = event.rect.width; chart.height = event.rect.height; }}
                    updateChartSize(chartId, isMulti);
                }}
            }});
        }}

        function switchMode(mode) {{
            currentMode = mode;
            document.getElementById('single-mode').classList.toggle('active', mode === 'single');
            document.getElementById('multi-mode').classList.toggle('active', mode === 'multi');
            document.querySelectorAll('.mode-btn').forEach((btn, i) => btn.classList.toggle('active', (i === 0 && mode === 'single') || (i === 1 && mode === 'multi')));
        }}

        document.getElementById('metrics-search').addEventListener('input', searchMetrics);
        document.querySelectorAll('#metrics-structure input[type="checkbox"]').forEach(cb => cb.addEventListener('change', updateSelectedMetrics));
        renderAllCharts();
    </script>
</body>
</html>'''

    output_file = 'kpi_dashboard_dual_mode.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ ДАШБОРД СОЗДАН")
    print(f"   Файл: {output_file}")
    print(f"   Количество метрик: {len(metrics_list)}")
    print(f"   Количество групп: {len(groups_structure)}")


create_offline_dashboard()
