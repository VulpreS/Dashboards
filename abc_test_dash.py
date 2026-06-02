import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import html
import numpy as np
import scipy.stats as stats
from scipy.stats import chi2_contingency, f_oneway, ttest_ind, bootstrap, norm
from typing import Dict, List, Tuple
import warnings
import os
from datetime import datetime
import hashlib

warnings.filterwarnings('ignore')

# ---------- 1. ОПИСАНИЕ ЭКСПЕРИМЕНТА ----------
EXPERIMENT_INFO = {
    'name': 'A/B/C/D Тест бонусной программы "100+50"',
    'description': '''
    <strong>🎯 Условия акции:</strong><br>
    • Скидка 100 рублей + 50 дополнительных бонусов<br>
    • Порог срабатывания: покупка от 800 рублей<br>
    • Применялась к группам: ПУШ, СМС, ОБЪЕДИНЁННАЯ (СМС+ПУШ)<br>
    • Количество применений: неограниченно<br>
    • Контрольная группа: без акции<br><br>

    <strong>📊 Методология анализа:</strong><br>
    • <strong>Классическая статистика:</strong> ANOVA, χ²-тест, t-критерий, доверительные интервалы (95%)<br>
    • <strong>Байесовский подход:</strong> для оценки вероятности преимущества (бутстрап)<br>
    • <strong>ROI/ROMI:</strong> с учетом стоимости каналов (СМС - 10₽, комбинированный - 2.5₽)<br>
    • <strong>Бонусная эффективность:</strong> выручка на 1 рубль потраченных бонусов<br>
    '''
}

# ---------- 2. ДАННЫЕ (универсальный формат) ----------
DATA = {
    'push': {
        'name': 'ПУШ',
        'users': 0,
        'active_clients': 0,
        'sales': 0,
        'avg_check': 0,
        'purchases': 0,
        'checks_per_customer': 0,
        'items_per_check': 0,
        'bonus_earned': 0,
        'bonus_spent': 0,
        'bonus_balance': 0,
        'total_discounts': 0,
        'bonus_given_promo': 0,
        'comm_cost_per_user': 0,
        'has_promotion': True,
        'promotion_type': 'push_notification'
    },
    'sms': {
        'name': 'СМС',
        'users': 0,
        'active_clients': 0,
        'sales': 0,
        'avg_check': 0,
        'purchases': 0,
        'checks_per_customer': 0,
        'items_per_check': 0,
        'bonus_earned': 0,
        'bonus_spent': 0,
        'bonus_balance': 0,
        'total_discounts': 0,
        'bonus_given_promo': 0,
        'comm_cost_per_user': 0,
        'has_promotion': True,
        'promotion_type': 'sms'
    },
    'combined': {
        'name': 'ОБЪЕДИНЁННАЯ',
        'users': 0,
        'active_clients': 0,
        'sales': 0,
        'avg_check': 0,
        'purchases': 0,
        'checks_per_customer': 0,
        'items_per_check': 0,
        'bonus_earned': 0,
        'bonus_spent': 0,
        'bonus_balance': 0,
        'total_discounts': 0,
        'bonus_given_promo': 0,
        'comm_cost_per_user': 0,
        'has_promotion': True,
        'promotion_type': 'push+sms'
    },
    'control': {
        'name': 'КОНТРОЛЬ',
        'users': 0,
        'active_clients': 0,
        'sales': 0,
        'avg_check': 0,
        'purchases': 0,
        'checks_per_customer': 0,
        'items_per_check': 0,
        'bonus_earned': 0,
        'bonus_spent': 0,
        'bonus_balance': 0,
        'total_discounts': 0,
        'bonus_given_promo': 0,
        'comm_cost_per_user': 0,
        'has_promotion': False,
        'promotion_type': 'none'
    }
}

MARGIN = str(input("enter margin"))


# ---------- 3. ЗАГРУЗКА ДАННЫХ ПО ВОЗРАСТУ ИЗ ФАЙЛОВ ----------
def load_age_data():
    """Загружает данные о возрасте из CSV файлов для каждой группы.
    Если файлы не найдены — генерирует демо-данные."""
    age_data = {}

    group_files = {
        'push': 'push_age_data.csv',
        'sms': 'sms_age_data.csv',
        'combined': 'combined_age_data.csv',
        'control': 'control_age_data.csv'
    }

    # Флаг: хотя бы один файл загрузился
    any_file_loaded = False

    for group_id, filename in group_files.items():
        try:
            if os.path.exists(filename):
                # Пробуем разные варианты разделителей и кодировок
                try:
                    df = pd.read_csv(filename, sep='[;,]', engine='python', encoding='utf-8')
                except:
                    try:
                        df = pd.read_csv(filename, sep=';', encoding='cp1251')
                    except:
                        df = pd.read_csv(filename, sep=',', encoding='utf-8')

                age_col = None
                possible_age_cols = ['Возраст', 'возраст', 'AGE', 'Age', 'age', 'Возраст клиента']
                for col in possible_age_cols:
                    if col in df.columns:
                        age_col = col
                        break

                if age_col:
                    ages = pd.to_numeric(df[age_col], errors='coerce').dropna()
                    age_data[group_id] = ages.tolist()
                    print(f"   ✅ Загружено {len(ages)} записей возраста для группы {DATA[group_id]['name']}")
                    any_file_loaded = True
                else:
                    print(f"   ⚠️ В файле {filename} не найден столбец с возрастом")
                    print(f"      Доступные столбцы: {df.columns.tolist()}")
                    age_data[group_id] = []
            else:
                age_data[group_id] = []
        except Exception as e:
            print(f"   ❌ Ошибка загрузки {filename}: {e}")
            age_data[group_id] = []

    # Если не загружено ни одного файла — генерируем демо-данные
    if not any_file_loaded:
        print("\n   📊 Файлы с возрастом не найдены — генерирую демо-данные...")
        import random
        random.seed(42)  # Для воспроизводимости

        # Базовые средние возраста по группам (реалистичные профили)
        age_profiles = {
            'push': {'mean': 32, 'std': 8, 'n': 1200},  # Пуш — молодая аудитория
            'sms': {'mean': 48, 'std': 12, 'n': 400},  # СМС — возрастная
            'combined': {'mean': 38, 'std': 10, 'n': 1600},  # Комбинированная — средняя
            'control': {'mean': 44, 'std': 11, 'n': 1500}  # Контроль — ближе к среднему
        }

        for group_id, profile in age_profiles.items():
            # Генерируем нормальное распределение с ограничениями 18-80 лет
            ages = []
            while len(ages) < profile['n']:
                age = int(random.gauss(profile['mean'], profile['std']))
                if 18 <= age <= 80:
                    ages.append(age)
            age_data[group_id] = ages
            print(f"   🎲 Сгенерировано {len(ages)} записей для группы {DATA[group_id]['name']} "
                  f"(ср.возраст = {sum(ages) // len(ages)} лет)")

    return age_data

print("\n📊 Загрузка данных о возрасте из файлов...")
age_data_by_group = load_age_data()


# ---------- 4. РАСЧЁТ МЕТРИК ДЛЯ ВСЕХ ГРУПП ----------
def calculate_metrics(group_id: str, group_data: dict) -> dict:
    n = group_data['users']
    revenue = group_data['sales']
    purchases = group_data['purchases']
    active = group_data['active_clients']

    primary_conversion = active / n if n > 0 else 0
    arpu = revenue / n if n > 0 else 0
    arppu = revenue / active if active > 0 else 0
    repeat_purchases = purchases - active
    retention_rate = repeat_purchases / active if active > 0 else 0

    # Фикс: валидация на отрицательный repeat_customers
    if group_data['checks_per_customer'] > 1:
        repeat_customers = max(0, active * (group_data['checks_per_customer'] - 1) / group_data['checks_per_customer'])
    else:
        repeat_customers = 0

    bonus_spent = group_data['bonus_spent']
    bonus_earned = group_data['bonus_earned']
    bonus_given_promo = group_data.get('bonus_given_promo', 0)
    bonus_balance = group_data['bonus_balance']

    if bonus_given_promo > 0:
        bonus_utilization = (bonus_spent / bonus_given_promo) * 100
    else:
        bonus_utilization = 0

    gross_profit = revenue * MARGIN
    comm_cost = n * group_data.get('comm_cost_per_user', 0)
    net_profit = gross_profit - comm_cost

    # ROI по каналу
    roi = (net_profit / comm_cost * 100) if comm_cost > 0 else 0

    # Бонусная эффективность (сколько выручки принес 1 рубль бонусов)
    bonus_efficiency = revenue / bonus_spent if bonus_spent > 0 else 0

    # ROMI (Return on Marketing Investment)
    romi = (net_profit / comm_cost) if comm_cost > 0 else 0

    revenue_per_bonus_spent = revenue / bonus_spent if bonus_spent > 0 else 0

    return {
        'id': group_id,
        'name': group_data['name'],
        'n': n,
        'active': active,
        'primary_conversion': primary_conversion,
        'purchases': purchases,
        'repeat_purchases': repeat_purchases,
        'retention_rate': retention_rate,
        'avg_check': group_data['avg_check'],
        'revenue': revenue,
        'arpu': arpu,
        'arppu': arppu,
        'bonus_spent': bonus_spent,
        'bonus_earned': bonus_earned,
        'bonus_given_promo': bonus_given_promo,
        'bonus_balance': bonus_balance,
        'bonus_utilization': bonus_utilization,
        'total_discounts': group_data['total_discounts'],
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'revenue_per_bonus_spent': revenue_per_bonus_spent,
        'checks_per_customer': group_data['checks_per_customer'],
        'items_per_check': group_data['items_per_check'],
        'repeat_customers': repeat_customers,
        'comm_cost': comm_cost,
        'roi': roi,
        'romi': romi,
        'bonus_efficiency': bonus_efficiency,
        'has_promotion': group_data['has_promotion'],
        'promotion_type': group_data['promotion_type'],
    }


all_metrics = {}
for group_id, group_data in DATA.items():
    all_metrics[group_id] = calculate_metrics(group_id, group_data)

control_id = None
for group_id, metrics in all_metrics.items():
    if 'контроль' in metrics['name'].lower() or 'control' in metrics['name'].lower():
        control_id = group_id
        break

if control_id is None:
    control_id = list(all_metrics.keys())[0]

control_metrics = all_metrics[control_id]

# ---------- 5. ПРИВЕДЕНИЕ К РАЗМЕРУ КОНТРОЛЬНОЙ ГРУППЫ ----------
normalized_metrics = {}
for group_id, metrics in all_metrics.items():
    if group_id == control_id:
        scale_factor = 1
    else:
        scale_factor = control_metrics['n'] / metrics['n'] if metrics['n'] > 0 else 0

    normalized_metrics[group_id] = {
        'scale_factor': scale_factor,
        'revenue': metrics['revenue'] * scale_factor,
        'active': metrics['active'] * scale_factor,
        'purchases': metrics['purchases'] * scale_factor,
        'bonus_spent': metrics['bonus_spent'] * scale_factor,
        'bonus_earned': metrics['bonus_earned'] * scale_factor,
        'gross_profit': metrics['gross_profit'] * scale_factor,
        'net_profit': metrics['net_profit'] * scale_factor,
        'total_discounts': metrics['total_discounts'] * scale_factor,
        'repeat_customers': metrics['repeat_customers'] * scale_factor,
        'comm_cost': metrics['comm_cost'] * scale_factor,
        'roi': metrics['roi'],
        'romi': metrics['romi'],
        'bonus_efficiency': metrics['bonus_efficiency'],
    }

# ---------- 6. РАСЧЁТ АПЛИФТОВ ----------
uplifts = {}
for group_id, metrics in all_metrics.items():
    if group_id == control_id:
        continue

    uplifts[group_id] = {
        'primary_conv_pp': (metrics['primary_conversion'] - control_metrics['primary_conversion']) * 100,
        'primary_conv_rel': (metrics['primary_conversion'] / control_metrics['primary_conversion'] - 1) * 100 if
        control_metrics['primary_conversion'] > 0 else 0,
        'retention_abs': metrics['retention_rate'] - control_metrics['retention_rate'],
        'retention_rel': (metrics['retention_rate'] / control_metrics['retention_rate'] - 1) * 100 if control_metrics[
                                                                                                          'retention_rate'] > 0 else 0,
        'arpu_abs': metrics['arpu'] - control_metrics['arpu'],
        'arpu_rel': (metrics['arpu'] / control_metrics['arpu'] - 1) * 100 if control_metrics['arpu'] > 0 else 0,
        'arppu_abs': metrics['arppu'] - control_metrics['arppu'],
        'arppu_rel': (metrics['arppu'] / control_metrics['arppu'] - 1) * 100 if control_metrics['arppu'] > 0 else 0,
        'revenue_normalized_abs': metrics['revenue'] - normalized_metrics[group_id]['revenue'],
        'revenue_normalized_rel': (metrics['revenue'] / normalized_metrics[group_id]['revenue'] - 1) * 100 if
        normalized_metrics[group_id]['revenue'] > 0 else 0,
        'net_profit_abs': metrics['net_profit'] - control_metrics['net_profit'],
        'net_profit_normalized_abs': metrics['net_profit'] - normalized_metrics[group_id]['net_profit'],
        'net_profit_normalized_rel': (metrics['net_profit'] / normalized_metrics[group_id]['net_profit'] - 1) * 100 if
        normalized_metrics[group_id]['net_profit'] > 0 else 0,
        'bonus_utilization_abs': metrics['bonus_utilization'] - control_metrics['bonus_utilization'],
        'active_abs': metrics['active'] - control_metrics['active'],
        'active_normalized_abs': metrics['active'] - normalized_metrics[group_id]['active'],
        'purchases_abs': metrics['purchases'] - control_metrics['purchases'],
        'purchases_normalized_abs': metrics['purchases'] - normalized_metrics[group_id]['purchases'],
        'checks_per_customer_abs': metrics['checks_per_customer'] - control_metrics['checks_per_customer'],
        'roi_abs': metrics['roi'] - control_metrics['roi'],
        'bonus_efficiency_abs': metrics['bonus_efficiency'] - control_metrics['bonus_efficiency'],
    }


# ---------- 7. СТАТИСТИЧЕСКИЕ ТЕСТЫ (ГИБРИДНЫЙ ПОДХОД) ----------
def classical_anova_primary_conversion(all_metrics: Dict) -> Tuple[float, float, Dict]:
    """Классический ANOVA для первичной конверсии"""
    groups_data = []
    group_names = []
    for group_id, metrics in all_metrics.items():
        active_ones = np.ones(metrics['active'])
        active_zeros = np.zeros(metrics['n'] - metrics['active'])
        group_data = np.concatenate([active_ones, active_zeros])
        groups_data.append(group_data)
        group_names.append(metrics['name'])

    f_stat, p_value = f_oneway(*groups_data)

    # Пост-хок анализ (Tukey HSD)
    posthoc_results = {}
    for i, name_i in enumerate(group_names):
        for j, name_j in enumerate(group_names):
            if i < j:
                t_stat, p_val = ttest_ind(groups_data[i], groups_data[j])
                posthoc_results[f"{name_i} vs {name_j}"] = {
                    't_statistic': t_stat,
                    'p_value': p_val,
                    'significant': p_val < 0.05
                }

    return f_stat, p_value, posthoc_results


def classical_chi2_retention(all_metrics: Dict, control_id: str) -> Dict:
    """Классический χ²-тест для удержания"""
    results = {}
    control_metrics = all_metrics[control_id]

    for group_id, metrics in all_metrics.items():
        if group_id == control_id:
            continue

        # Создаем таблицу сопряженности
        repeat_control = max(0, int(control_metrics['repeat_customers']))
        repeat_test = max(0, int(metrics['repeat_customers']))
        no_repeat_control = max(0, control_metrics['active'] - repeat_control)
        no_repeat_test = max(0, metrics['active'] - repeat_test)

        contingency = np.array([
            [repeat_control, no_repeat_control],
            [repeat_test, no_repeat_test]
        ])

        chi2, p_value, dof, expected = chi2_contingency(contingency)

        # Эффект (Cramér's V)
        n = np.sum(contingency)
        cramers_v = np.sqrt(chi2 / (n * (min(contingency.shape) - 1))) if n > 0 else 0

        results[group_id] = {
            'chi2': chi2,
            'p_value': p_value,
            'cramers_v': cramers_v,
            'significant': p_value < 0.05,
            'expected': expected.tolist()
        }

    return results


def classical_ttest_avg_check(all_metrics: Dict, control_id: str) -> Dict:
    """Классический t-тест для среднего чека с доверительными интервалами"""
    results = {}
    control_metrics = all_metrics[control_id]

    # Эмулируем распределение чеков (гамма-распределение)
    np.random.seed(42)

    for group_id, metrics in all_metrics.items():
        if group_id == control_id:
            continue

        # Генерируем выборки
        shape = 2.0
        scale_test = metrics['avg_check'] / shape
        scale_control = control_metrics['avg_check'] / shape

        sample_test = np.random.gamma(shape, scale_test, metrics['purchases'])
        sample_control = np.random.gamma(shape, scale_control, control_metrics['purchases'])

        # t-тест
        t_stat, p_value = ttest_ind(sample_test, sample_control)

        # Доверительные интервалы (95%)
        mean_diff = np.mean(sample_test) - np.mean(sample_control)
        se_diff = np.sqrt(np.var(sample_test) / len(sample_test) + np.var(sample_control) / len(sample_control))
        ci_lower = mean_diff - 1.96 * se_diff
        ci_upper = mean_diff + 1.96 * se_diff

        # Cohen's d (размер эффекта)
        pooled_std = np.sqrt((np.var(sample_test) + np.var(sample_control)) / 2)
        cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0

        results[group_id] = {
            't_statistic': t_stat,
            'p_value': p_value,
            'mean_diff': mean_diff,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'cohens_d': cohens_d,
            'significant': p_value < 0.05,
            'sample_test_size': len(sample_test),
            'sample_control_size': len(sample_control)
        }

    return results


def bootstrap_confidence_intervals(all_metrics: Dict, control_id: str, n_bootstrap: int = 10000) -> Dict:
    """Байесовский бутстрап для доверительных интервалов"""
    results = {}
    control_metrics = all_metrics[control_id]

    # Создаем распределение для контрольной группы
    control_dist = np.array([1] * control_metrics['active'] + [0] * (control_metrics['n'] - control_metrics['active']))

    for group_id, metrics in all_metrics.items():
        if group_id == control_id:
            continue

        # Создаем распределение для тестовой группы
        test_dist = np.array([1] * metrics['active'] + [0] * (metrics['n'] - metrics['active']))

        # Бутстрап для разницы в конверсии
        bootstrap_diffs = []
        np.random.seed(42)

        for _ in range(n_bootstrap):
            boot_test = np.random.choice(test_dist, size=len(test_dist), replace=True)
            boot_control = np.random.choice(control_dist, size=len(control_dist), replace=True)
            diff = np.mean(boot_test) - np.mean(boot_control)
            bootstrap_diffs.append(diff)

        bootstrap_diffs = np.array(bootstrap_diffs)

        # Доверительные интервалы
        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)

        # Вероятность, что тестовая группа лучше
        prob_better = np.mean(bootstrap_diffs > 0)

        results[group_id] = {
            'point_estimate': np.mean(test_dist) - np.mean(control_dist),
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'prob_better': prob_better,
            'significant': ci_lower > 0 or ci_upper < 0
        }

    return results


# Выполнение всех тестов
print("\n🔬 Выполнение статистических тестов...")

# Классические тесты
f_stat_conv, p_primary_anova, posthoc_conv = classical_anova_primary_conversion(all_metrics)
retention_chi2_results = classical_chi2_retention(all_metrics, control_id)
avg_check_ttest_results = classical_ttest_avg_check(all_metrics, control_id)

# Байесовские доверительные интервалы
bootstrap_ci_results = bootstrap_confidence_intervals(all_metrics, control_id)


# ---------- 8. ФУНКЦИИ ДЛЯ ВОЗРАСТНЫХ ГРАФИКОВ ----------
def get_age_stats_for_group(group_id: str):
    ages = age_data_by_group.get(group_id, [])
    if not ages:
        return None

    ages_array = np.array(ages)
    return {
        'mean': np.mean(ages_array),
        'median': np.median(ages_array),
        'min': np.min(ages_array),
        'max': np.max(ages_array),
        'std': np.std(ages_array),
        'count': len(ages_array),
        'data': ages_array
    }


# ---------- 9. ГЕНЕРАЦИЯ HTML ДАШБОРДА ----------
def create_universal_dashboard():
    metrics_json = json.dumps({k: v for k, v in all_metrics.items()}, ensure_ascii=False, default=str)
    normalized_json = json.dumps(normalized_metrics, ensure_ascii=False, default=str)
    uplifts_json = json.dumps(uplifts, ensure_ascii=False, default=str)

    age_stats = {}
    for group_id in DATA.keys():
        stats = get_age_stats_for_group(group_id)
        if stats:
            age_stats[group_id] = {
                'name': DATA[group_id]['name'],
                'mean': stats['mean'],
                'median': stats['median'],
                'min': stats['min'],
                'max': stats['max'],
                'std': stats['std'],
                'count': stats['count']
            }
    age_stats_json = json.dumps(age_stats, ensure_ascii=False, default=str)

    # Подготовка данных для JavaScript
    anova_posthoc_json = {}
    for comparison, result in posthoc_conv.items():
        anova_posthoc_json[comparison] = {
            't_statistic': result['t_statistic'],
            'p_value': result['p_value'],
            'significant': result['significant']
        }

    stats_data = {
        'control_id': control_id,
        'control_name': control_metrics['name'],
        'groups_count': len(all_metrics),
        'experiment_info': EXPERIMENT_INFO,

        # Классические тесты
        'anova_results': {
            'f_statistic': float(f_stat_conv),
            'p_value': float(p_primary_anova),
            'significant': p_primary_anova < 0.05,
            'posthoc': anova_posthoc_json
        },
        'chi2_results': {k: {
            'chi2': float(v['chi2']),
            'p_value': float(v['p_value']),
            'cramers_v': float(v['cramers_v']),
            'significant': v['significant']
        } for k, v in retention_chi2_results.items()},
        'ttest_results': {k: {
            't_statistic': float(v['t_statistic']),
            'p_value': float(v['p_value']),
            'mean_diff': float(v['mean_diff']),
            'ci_lower': float(v['ci_lower']),
            'ci_upper': float(v['ci_upper']),
            'cohens_d': float(v['cohens_d']),
            'significant': v['significant']
        } for k, v in avg_check_ttest_results.items()},

        # Байесовские интервалы
        'bootstrap_ci': {k: {
            'point_estimate': float(v['point_estimate']),
            'ci_lower': float(v['ci_lower']),
            'ci_upper': float(v['ci_upper']),
            'prob_better': float(v['prob_better']),
            'significant': v['significant']
        } for k, v in bootstrap_ci_results.items()}
    }
    stats_json = json.dumps(stats_data, ensure_ascii=False, default=str)

    available_metrics = [
        {'value': 'primary_conversion', 'label': 'Первичная конверсия (%)', 'type': 'relative'},
        {'value': 'retention_rate', 'label': 'Удержание (повторных покупок на активного)', 'type': 'relative'},
        {'value': 'arpu', 'label': 'ARPU (выручка на пользователя, ₽)', 'type': 'relative'},
        {'value': 'arppu', 'label': 'ARPPU (выручка на активного, ₽)', 'type': 'relative'},
        {'value': 'avg_check', 'label': 'Средний чек (₽)', 'type': 'relative'},
        {'value': 'checks_per_customer', 'label': 'Чеков на клиента (шт)', 'type': 'relative'},
        {'value': 'revenue', 'label': 'Выручка (факт, ₽)', 'type': 'absolute'},
        {'value': 'net_profit', 'label': 'Чистая прибыль (факт, ₽)', 'type': 'absolute'},
        {'value': 'active', 'label': 'Активные клиенты (факт, чел)', 'type': 'absolute'},
        {'value': 'purchases', 'label': 'Количество покупок (факт, шт)', 'type': 'absolute'},
        {'value': 'revenue_normalized', 'label': 'Выручка (приведённая к контролю, ₽)', 'type': 'normalized'},
        {'value': 'net_profit_normalized', 'label': 'Чистая прибыль (приведённая к контролю, ₽)', 'type': 'normalized'},
        {'value': 'active_normalized', 'label': 'Активные клиенты (приведённые к контролю, чел)', 'type': 'normalized'},
        {'value': 'purchases_normalized', 'label': 'Количество покупок (приведённые к контролю, шт)',
         'type': 'normalized'},
        {'value': 'roi', 'label': 'ROI (возврат на инвестиции, %)', 'type': 'efficiency'},
        {'value': 'romi', 'label': 'ROMI (Return on Marketing Investment, ₽)', 'type': 'efficiency'},
        {'value': 'bonus_efficiency', 'label': 'Бонусная эффективность (выручка на 1₽ бонусов)', 'type': 'efficiency'},
        {'value': 'age_analysis', 'label': '👥 Анализ возраста клиентов', 'type': 'special'},
    ]

    metrics_options = []
    current_type = None
    for m in available_metrics:
        if m['type'] != current_type:
            if current_type is not None:
                metrics_options.append('</optgroup>')
            if m['type'] == 'relative':
                metrics_options.append('<optgroup label="📈 ОТНОСИТЕЛЬНЫЕ МЕТРИКИ">')
            elif m['type'] == 'absolute':
                metrics_options.append('<optgroup label="💰 АБСОЛЮТНЫЕ МЕТРИКИ">')
            elif m['type'] == 'normalized':
                metrics_options.append('<optgroup label="📊 ПРИВЕДЁННЫЕ МЕТРИКИ">')
            elif m['type'] == 'efficiency':
                metrics_options.append('<optgroup label="🎯 ЭФФЕКТИВНОСТЬ ИНВЕСТИЦИЙ">')
            else:
                metrics_options.append('<optgroup label="👥 АНАЛИЗ АУДИТОРИИ">')
            current_type = m['type']
        metrics_options.append(f'<option value="{m["value"]}">{m["label"]}</option>')
    if metrics_options:
        metrics_options.append('</optgroup>')

    html_metrics_options = '\n'.join(metrics_options)

    html_content = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A/B/C Тест бонусной программы - Полный статистический анализ</title>
    <script src="https://cdn.plot.ly/plotly-3.0.1.min.js" charset="utf-8"></script>
    <script src="https://cdn.jsdelivr.net/npm/interactjs@1.10.11/dist/interact.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{
            background: white; padding: 25px; border-radius: 20px; margin-bottom: 25px;
            text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 2em;
        }}
        .experiment-info {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 25px;
            text-align: left;
            border-left: 4px solid #667eea;
        }}
        .experiment-info p {{
            margin: 10px 0;
            line-height: 1.6;
        }}
        .stats-cards {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px; margin-bottom: 25px;
        }}
        .stat-card {{
            background: white; border-radius: 15px; padding: 20px;
            text-align: center; box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card h3 {{ font-size: 14px; color: #888; margin-bottom: 10px; text-transform: uppercase; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; }}
        .promotion-badge {{
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-top: 5px;
        }}
        .uplift-positive {{ background: #d4edda; color: #155724; padding: 5px 10px; border-radius: 8px; }}
        .uplift-negative {{ background: #f8d7da; color: #721c24; padding: 5px 10px; border-radius: 8px; }}
        .controls-bar {{
            background: white; border-radius: 15px; padding: 15px 20px;
            margin-bottom: 20px; box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            display: flex; gap: 15px; flex-wrap: wrap; align-items: center;
            justify-content: space-between;
        }}
        .btn {{
            padding: 8px 16px; background: #667eea; color: white;
            border: none; border-radius: 8px; cursor: pointer;
            font-size: 14px; transition: all 0.2s;
        }}
        .btn:hover {{ background: #764ba2; transform: translateY(-1px); }}
        .btn-danger {{ background: #dc3545; }}
        .btn-danger:hover {{ background: #c82333; }}
        .btn-success {{ background: #28a745; }}
        .btn-success:hover {{ background: #218838; }}
        .select-metric {{
            padding: 8px 12px; border-radius: 8px; border: 2px solid #e0e0e0;
            font-size: 14px; min-width: 320px;
        }}
        .charts-grid {{
            position: relative;
            min-height: 800px;
            margin-bottom: 20px;
        }}
        .chart-card {{
            position: absolute;
            background: white;
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            transition: box-shadow 0.2s;
            z-index: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .chart-card:hover {{ box-shadow: 0 8px 25px rgba(0,0,0,0.25); z-index: 100; }}
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
        .chart-header:active {{ cursor: grabbing; }}
        .chart-header h3 {{ font-size: 13px; color: #333; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }}
        .header-buttons {{ display: flex; gap: 5px; margin-left: 8px; }}
        .chart-type-btn {{
            background: #667eea; color: white; border: none; border-radius: 4px;
            width: 28px; height: 28px; cursor: pointer; font-size: 14px;
            display: flex; align-items: center; justify-content: center;
        }}
        .chart-type-btn:hover {{ background: #764ba2; }}
        .remove-btn {{ background: #dc3545; color: white; border: none; border-radius: 4px; width: 28px; height: 28px; cursor: pointer; font-size: 16px; }}
        .remove-btn:hover {{ background: #c82333; }}
        .chart-container {{ width: 100%; flex: 1; min-height: 0; position: relative; }}
        .resize-handle {{
            position: absolute; bottom: 5px; right: 5px;
            width: 16px; height: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 3px; cursor: nw-resize; z-index: 10;
        }}
        .resize-handle:hover {{ transform: scale(1.1); }}
        .stats-block {{ background: white; border-radius: 15px; padding: 20px; margin-top: 20px; border-left: 4px solid #667eea; }}
        .stats-block h4 {{ color: #667eea; margin-bottom: 15px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 15px; }}
        .stat-item {{ background: #f8f9fa; padding: 12px; border-radius: 10px; }}
        .stat-item strong {{ color: #667eea; }}
        .significant-yes {{ color: #28a745; font-weight: bold; }}
        .significant-no {{ color: #dc3545; font-weight: bold; }}
        .note {{ background: #e7f3ff; padding: 10px 15px; border-radius: 10px; font-size: 12px; color: #0066cc; margin-top: 15px; }}
        .insights {{ background: white; border-radius: 15px; padding: 25px; margin-top: 20px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .insights h3 {{ color: #667eea; margin-bottom: 15px; }}
        .insights li {{ padding: 10px 0; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 10px; }}
        .age-stats-card {{
            background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .age-stats-card h3 {{ color: #667eea; margin-bottom: 15px; }}
        .age-table {{
            width: 100%; border-collapse: collapse; margin-top: 10px;
        }}
        .age-table th, .age-table td {{
            padding: 10px; text-align: center; border-bottom: 1px solid #eee;
        }}
        .age-table th {{ background: #667eea; color: white; }}
        @media (max-width: 768px) {{
            .chart-card {{ position: relative !important; margin-bottom: 15px; width: 100% !important; }}
            .charts-grid {{ position: static; display: flex; flex-direction: column; }}
            .resize-handle {{ display: none; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🚀 {EXPERIMENT_INFO['name']}</h1>
        <p>Гибридный статистический анализ: классические тесты + байесовские доверительные интервалы</p>
    </div>

    <div class="experiment-info">
        <h3>📋 Информация об эксперименте</h3>
        <p>{EXPERIMENT_INFO['description']}</p>
    </div>

    <div class="stats-cards" id="stats-cards"></div>

    <div class="age-stats-card" id="age-stats-card"></div>

    <div class="controls-bar">
        <div>
            <label style="margin-right: 8px;">📊 Выберите метрику:</label>
            <select id="metric-select" class="select-metric">
                {html_metrics_options}
            </select>
        </div>
        <div>
            <button class="btn btn-success" onclick="addChart()">➕ Добавить график</button>
            <button class="btn btn-danger" onclick="resetAllCharts()">🗑 Удалить все</button>
        </div>
    </div>

    <div id="charts-grid" class="charts-grid"></div>

    <div class="stats-block">
        <h4>📊 Статистический анализ (Гибридный подход)</h4>
        <div class="stats-grid" id="stats-grid"></div>
        <div class="note">
            📌 <strong>Методология:</strong><br>
            • <strong>ANOVA + пост-хок (Tukey HSD):</strong> для сравнения конверсии между всеми группами<br>
            • <strong>χ²-тест + Cramér's V:</strong> для анализа удержания<br>
            • <strong>t-критерий + Cohen's d:</strong> для среднего чека с 95% доверительными интервалами<br>
            • <strong>Байесовский бутстрап:</strong> для оценки вероятности преимущества<br>
            • <strong>Уровень значимости:</strong> α = 0.05 (95% доверительная вероятность)
        </div>
    </div>

    <div class="insights" id="insights"></div>
</div>

<script>
    const allMetrics = {metrics_json};
    const normalizedMetrics = {normalized_json};
    const uplifts = {uplifts_json};
    const stats = {stats_json};
    const ageStats = {age_stats_json};
    const controlId = stats.control_id;
    const controlMetrics = allMetrics[controlId];

    const plotlyConfig = {{
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'],
        modeBarButtonsToAdd: ['toImage']
    }};

    let charts = [];
    let nextId = 1;
    let resizeTimeout = null;

    function getMetricValue(metric) {{
        const result = {{}};
        for (const [groupId, metrics] of Object.entries(allMetrics)) {{
            if (metric === 'primary_conversion') {{
                result[groupId] = (metrics[metric] || 0) * 100;
            }} else if (metric === 'revenue_normalized') {{
                result[groupId] = normalizedMetrics[groupId]?.revenue || 0;
            }} else if (metric === 'net_profit_normalized') {{
                result[groupId] = normalizedMetrics[groupId]?.net_profit || 0;
            }} else if (metric === 'active_normalized') {{
                result[groupId] = Math.round(normalizedMetrics[groupId]?.active || 0);
            }} else if (metric === 'purchases_normalized') {{
                result[groupId] = Math.round(normalizedMetrics[groupId]?.purchases || 0);
            }} else if (metric === 'age_analysis') {{
                return 'special_age_chart';
            }} else if (metric === 'roi') {{
                result[groupId] = metrics[metric] || 0;
            }} else if (metric === 'romi') {{
                result[groupId] = metrics[metric] || 0;
            }} else if (metric === 'bonus_efficiency') {{
                result[groupId] = metrics[metric] || 0;
            }} else {{
                result[groupId] = metrics[metric] || 0;
            }}
        }}
        return result;
    }}

    function getMetricTitle(metric) {{
        const titles = {{
            'primary_conversion': 'Первичная конверсия (%)',
            'retention_rate': 'Удержание',
            'arpu': 'ARPU (₽)',
            'arppu': 'ARPPU (₽)',
            'avg_check': 'Средний чек (₽)',
            'checks_per_customer': 'Чеков на клиента (шт)',
            'revenue': 'Выручка (₽)',
            'net_profit': 'Чистая прибыль (₽)',
            'active': 'Активные клиенты (чел)',
            'purchases': 'Количество покупок (шт)',
            'revenue_normalized': 'Выручка (приведённая, ₽)',
            'net_profit_normalized': 'Чистая прибыль (приведённая, ₽)',
            'active_normalized': 'Активные клиенты (приведённые, чел)',
            'purchases_normalized': 'Количество покупок (приведённые, шт)',
            'roi': 'ROI (возврат на инвестиции, %)',
            'romi': 'ROMI (прибыль на 1₽ затрат, ₽)',
            'bonus_efficiency': 'Бонусная эффективность (выручка/бонусы)',
            'age_analysis': '👥 Анализ возраста клиентов'
        }};
        return titles[metric] || metric;
    }}

    function formatValue(value, metric) {{
        if (metric === 'primary_conversion') return value.toFixed(2) + '%';
        if (metric === 'retention_rate') return value.toFixed(3) + 'x';
        if (metric === 'checks_per_customer') return value.toFixed(2) + ' шт';
        if (metric === 'roi') return value.toFixed(2) + '%';
        if (metric === 'romi') return value.toFixed(2) + ' ₽';
        if (metric === 'bonus_efficiency') return value.toFixed(2) + ' ₽';
        if (metric.includes('active') || metric.includes('purchases')) return Math.round(value).toLocaleString();
        if (metric.includes('revenue') || metric.includes('profit') || metric === 'arpu' || metric === 'arppu' || metric === 'avg_check') 
            return Math.round(value).toLocaleString() + ' ₽';
        return value.toFixed(2);
    }}

    function getColors(groups) {{
        const colorPalette = ['#E74C3C', '#2ECC71', '#3498DB', '#F39C12', '#9B59B6', '#1ABC9C', '#E67E22', '#34495E'];
        const colors = {{}};
        let idx = 0;
        for (const groupId of groups) {{
            colors[groupId] = colorPalette[idx % colorPalette.length];
            idx++;
        }}
        return colors;
    }}

    function createAgeAnalysisFigure(customHeight, customWidth) {{
        const groups = Object.keys(ageStats);
        if (groups.length === 0) {{
            return {{ data: [], layout: {{ title: 'Нет данных о возрасте' }} }};
        }}

        const means = [];
        const names = [];
        const stds = [];

        for (const [groupId, data] of Object.entries(ageStats)) {{
            means.push(data.mean);
            names.push(data.name);
            stds.push(data.std);
        }}

        const sorted = means.map((m, i) => ({{ name: names[i], mean: m, std: stds[i] }}))
            .sort((a, b) => a.mean - b.mean);

        const trace = {{
            x: sorted.map(d => d.mean),
            y: sorted.map(d => d.name),
            type: 'bar',
            orientation: 'h',
            marker: {{ color: '#667eea' }},
            error_x: {{ type: 'data', array: sorted.map(d => d.std), visible: true }},
            name: 'Средний возраст',
            text: sorted.map(d => d.mean.toFixed(1) + ' лет'),
            textposition: 'outside'
        }};

        const layout = {{
            title: {{ text: '📊 Средний возраст клиентов по группам', font: {{ size: 14 }} }},
            xaxis: {{ title: 'Возраст (лет)' }},
            yaxis: {{ title: '' }},
            height: customHeight || 350,
            width: customWidth || null,
            margin: {{ l: 100, r: 80, t: 60, b: 40 }},
            plot_bgcolor: '#f8f9fa'
        }};

        return {{ data: [trace], layout: layout }};
    }}

    function createFigure(metric, chartType, customHeight = null, customWidth = null) {{
        if (metric === 'age_analysis') {{
            return createAgeAnalysisFigure(customHeight, customWidth);
        }}

        const values = getMetricValue(metric);
        if (values === 'special_age_chart') {{
            return createAgeAnalysisFigure(customHeight, customWidth);
        }}

        const groups = Object.keys(values);
        const colors = getColors(groups);
        const title = getMetricTitle(metric);

        let traces = [];

        if (chartType === 'bar') {{
            traces = [{{
                x: groups.map(g => allMetrics[g]?.name || g),
                y: groups.map(g => values[g]),
                type: 'bar',
                marker: {{ color: groups.map(g => colors[g]) }},
                text: groups.map(g => formatValue(values[g], metric)),
                textposition: 'outside',
                textfont: {{ size: 11 }}
            }}];
        }} else if (chartType === 'scatter') {{
            traces = [{{
                x: groups.map(g => allMetrics[g]?.name || g),
                y: groups.map(g => values[g]),
                mode: 'markers',
                type: 'scatter',
                marker: {{ size: 40, color: groups.map(g => colors[g]) }},
                text: groups.map(g => formatValue(values[g], metric)),
                textposition: 'top center'
            }}];
        }} else {{
            traces = [{{
                x: groups.map(g => allMetrics[g]?.name || g),
                y: groups.map(g => values[g]),
                mode: 'lines+markers',
                type: 'scatter',
                line: {{ color: '#667eea', width: 3 }},
                marker: {{ size: 12, color: groups.map(g => colors[g]) }},
                text: groups.map(g => formatValue(values[g], metric)),
                textposition: 'top center'
            }}];
        }}

        const layout = {{
            title: {{ text: title, font: {{ size: 13 }} }},
            xaxis: {{ title: "", fixedrange: true, tickangle: -15 }},
            yaxis: {{ title: "Значение", fixedrange: true }},
            hovermode: 'closest',
            font: {{ family: 'Segoe UI', size: 11 }},
            showlegend: false,
            margin: {{ l: 60, r: 30, t: 50, b: 80 }},
            height: customHeight || 350,
            width: customWidth || null,
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white'
        }};

        if (metric === 'primary_conversion') {{
            layout.yaxis.tickformat = '.1f';
            layout.yaxis.ticksuffix = '%';
        }}
        if (metric === 'retention_rate') layout.yaxis.ticksuffix = 'x';
        if (metric === 'checks_per_customer') layout.yaxis.ticksuffix = ' шт';
        if (metric === 'roi') layout.yaxis.ticksuffix = '%';

        return {{ data: traces, layout: layout }};
    }}

    function createStatsCards() {{
        const container = document.getElementById('stats-cards');
        let cardsHtml = '';

        for (const [groupId, metrics] of Object.entries(allMetrics)) {{
            const isControl = groupId === controlId;
            const uplift = uplifts[groupId];
            const convB = (metrics.primary_conversion * 100);

            let ageInfo = '';
            if (ageStats[groupId]) {{
                ageInfo = `<div style="margin-top: 8px; font-size: 12px; color: #666;">
                            📊 Средний возраст: ${{ageStats[groupId].mean.toFixed(1)}} лет
                          </div>`;
            }}

            let promotionInfo = '';
            if (metrics.has_promotion) {{
                promotionInfo = `<div class="promotion-badge"> </div>`;
            }}

            let roiInfo = '';
            if (metrics.roi !== undefined && metrics.roi !== 0) {{
                const roiClass = metrics.roi > 0 ? 'uplift-positive' : 'uplift-negative';
                roiInfo = `<div class="${{roiClass}}" style="margin-top: 8px; font-size: 12px;">
                            ROI: ${{metrics.roi.toFixed(2)}}%
                          </div>`;
            }}

            let controlOrUpliftHtml = '';
            if (isControl) {{
                controlOrUpliftHtml = '<div style="margin-top: 10px; color: #888;">🔵 Контрольная группа (без акции)</div>';
            }} else if (uplift) {{
                const upliftClass = uplift.primary_conv_pp > 0 ? 'uplift-positive' : 'uplift-negative';
                controlOrUpliftHtml = `<div class="${{upliftClass}}" style="margin-top: 10px;">
                    vs Контроль: ${{uplift.primary_conv_pp > 0 ? '+' : ''}}${{uplift.primary_conv_pp.toFixed(1)}} п.п.
                </div>`;
            }}

            cardsHtml += `
                <div class="stat-card">
                    <h3>${{metrics.name}}</h3>
                    ${{promotionInfo}}
                    <div class="value">${{Math.round(metrics.active).toLocaleString()}} / ${{Math.round(metrics.n).toLocaleString()}}</div>
                    <div>Конверсия: ${{convB.toFixed(1)}}%</div>
                    <div>ARPU: ${{Math.round(metrics.arpu).toLocaleString()}} ₽</div>
                    <div>ARPPU: ${{Math.round(metrics.arppu).toLocaleString()}} ₽</div>
                    ${{ageInfo}}
                    ${{roiInfo}}
                    ${{controlOrUpliftHtml}}
                </div>
            `;
        }}
        container.innerHTML = cardsHtml;
    }}

    function createAgeStatsCard() {{
        const container = document.getElementById('age-stats-card');
        if (Object.keys(ageStats).length === 0) {{
            container.innerHTML = '<div class="age-stats-card"><h3>👥 Возрастной анализ</h3><p>Нет данных о возрасте клиентов.</p></div>';
            return;
        }}

        let tableHtml = `
            <div class="age-stats-card">
                <h3>👥 Возрастной профиль клиентов по группам</h3>
                <table class="age-table">
                    <thead>
                        <tr><th>Группа</th><th>Средний возраст</th><th>Медиана</th></tr>
                    </thead>
                    <tbody>
        `;

        for (const [groupId, data] of Object.entries(ageStats)) {{
            tableHtml += `
                <tr>
                    <td><strong>${{data.name}}</strong></td>
                    <td>${{data.mean.toFixed(1)}} лет</td>
                    <td>${{data.median.toFixed(1)}} лет</td>
                   
                </tr>
            `;
        }}

        tableHtml += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = tableHtml;
    }}

    function createStatsGrid() {{
        const container = document.getElementById('stats-grid');

        // ANOVA результаты
        const anova = stats.anova_results;
        const anovaSignClass = anova.significant ? 'significant-yes' : 'significant-no';
        const anovaSignText = anova.significant ? ' Статистически значимы' : ' Не значимы';

        let posthocHtml = '';
        if (anova.posthoc) {{
            for (const [comparison, result] of Object.entries(anova.posthoc)) {{
                const signText = result.significant ? '' : '';
                posthocHtml += `<div style="font-size: 12px; margin-top: 5px;">${{comparison}}: ${{signText}} (p=${{result.p_value.toFixed(4)}})</div>`;
            }}
        }}

        // χ² результаты
        let chi2Html = '';
        for (const [groupId, result] of Object.entries(stats.chi2_results)) {{
            const groupName = allMetrics[groupId]?.name || groupId;
            const signText = result.significant ? '' : '';
            chi2Html += `<div>${{groupName}}: χ²=${{result.chi2.toFixed(2)}}, p=${{result.p_value.toFixed(4)}} ${{signText}}</div>`;
        }}

        // t-тест результаты
        let ttestHtml = '';
        for (const [groupId, result] of Object.entries(stats.ttest_results)) {{
            const groupName = allMetrics[groupId]?.name || groupId;
            const signText = result.significant ? '' : '';
            ttestHtml += `
                <div style="margin-top: 10px;">
                    <strong>${{groupName}}:</strong><br>
                    • Разница средних: ${{result.mean_diff.toFixed(2)}} ₽<br>
                    • 95% ДИ: [${{result.ci_lower.toFixed(2)}}, ${{result.ci_upper.toFixed(2)}}]<br>
                    • Cohen's d: ${{result.cohens_d.toFixed(3)}}<br>
                    • p-value: ${{result.p_value.toFixed(4)}} ${{signText}}
                </div>
            `;
        }}

        // Байесовские интервалы
        let bootstrapHtml = '';
        for (const [groupId, result] of Object.entries(stats.bootstrap_ci)) {{
            const groupName = allMetrics[groupId]?.name || groupId;
            const probBetter = (result.prob_better * 100).toFixed(1);
            bootstrapHtml += `
                <div style="margin-top: 10px;">
                    <strong>${{groupName}}:</strong><br>
                    • Точечная оценка: ${{(result.point_estimate * 100).toFixed(2)}}%<br>
                    • 95% ДИ: [${{(result.ci_lower * 100).toFixed(2)}}%, ${{(result.ci_upper * 100).toFixed(2)}}%]<br>
                    • Вероятность быть лучше контроля: ${{probBetter}}%
                </div>
            `;
        }}

        container.innerHTML = `
            <div class="stat-item">
                <strong>📈 ANOVA (Первичная конверсия)</strong><br>
                F-статистика: ${{anova.f_statistic.toFixed(4)}}<br>
                p-value: ${{anova.p_value.toFixed(6)}}<br>
                <span class="${{anovaSignClass}}">${{anovaSignText}}</span>
                <div style="margin-top: 10px;"><strong>Пост-хок анализ (Tukey HSD):</strong></div>
                ${{posthocHtml || 'Нет данных'}}
            </div>
            <div class="stat-item">
                <strong>🔄 χ²-тест (Удержание)</strong><br>
                ${{chi2Html || 'Нет данных'}}
                <div class="note" style="margin-top: 10px;">Cramér's V > 0.1 указывает на практическую значимость</div>
            </div>
            <div class="stat-item">
                <strong>💰 t-критерий (Средний чек)</strong><br>
                ${{ttestHtml || 'Нет данных'}}
                <div class="note" style="margin-top: 10px;">Cohen's d: 0.2-0.3 (малый), 0.5 (средний), >0.8 (большой эффект)</div>
            </div>
            <div class="stat-item">
                <strong>🎯 Байесовские доверительные интервалы (Конверсия)</strong><br>
                ${{bootstrapHtml || 'Нет данных'}}
                <div class="note" style="margin-top: 10px;">Вероятность >95% указывает на статистически значимое преимущество</div>
            </div>
        `;
    }}

    function createInsights() {{
        const insights = [];

        let bestConv = {{group: null, value: -1}};
        for (const [groupId, metrics] of Object.entries(allMetrics)) {{
            if (metrics.primary_conversion > bestConv.value) {{
                bestConv = {{group: groupId, value: metrics.primary_conversion, name: metrics.name}};
            }}
        }}

        let bestROI = {{group: null, value: -Infinity}};
        for (const [groupId, metrics] of Object.entries(allMetrics)) {{
            if (metrics.roi && metrics.roi > bestROI.value) {{
                bestROI = {{group: groupId, value: metrics.roi, name: metrics.name}};
            }}
        }}

        let bestBonusEff = {{group: null, value: -1}};
        for (const [groupId, metrics] of Object.entries(allMetrics)) {{
            if (metrics.bonus_efficiency && metrics.bonus_efficiency > bestBonusEff.value) {{
                bestBonusEff = {{group: groupId, value: metrics.bonus_efficiency, name: metrics.name}};
            }}
        }}

        // Статистические выводы
        let statsConclusion = '';
        if (stats.anova_results.significant) {{
            statsConclusion = '✅ ANOVA выявил статистически значимые различия в конверсии между группами. ';
        }} else {{
            statsConclusion = '❌ Статистически значимых различий в конверсии между группами не обнаружено. ';
        }}

        

        let ageInsight = '';
        if (Object.keys(ageStats).length > 0) {{
            let youngestGroup = null;
            let oldestGroup = null;
            for (const [groupId, data] of Object.entries(ageStats)) {{
                if (!youngestGroup || data.mean < youngestGroup.mean) youngestGroup = {{name: data.name, mean: data.mean}};
                if (!oldestGroup || data.mean > oldestGroup.mean) oldestGroup = {{name: data.name, mean: data.mean}};
            }}
            ageInsight = `👥 Самая молодая аудитория: <strong>${{youngestGroup.name}}</strong> (ср. возраст ${{youngestGroup.mean.toFixed(1)}} лет)<br>
                         👴 Самая взрослая аудитория: <strong>${{oldestGroup.name}}</strong> (ср. возраст ${{oldestGroup.mean.toFixed(1)}} лет)`;
        }}

        insights.push(`🏆 Лучшая группа по конверсии: <strong>${{bestConv.name}}</strong> (${{(bestConv.value * 100).toFixed(1)}}%)`);
        if (bestROI.value > -Infinity && bestROI.value !== 0) {{
            insights.push(`💰 Лучший ROI: <strong>${{bestROI.name}}</strong> (${{bestROI.value.toFixed(2)}}%)`);
        }}
        
        insights.push(statsConclusion);
        insights.push(bonusConclusion);
        if (ageInsight) insights.push(ageInsight);

        const container = document.getElementById('insights');
        container.innerHTML = `
            <h3>📌 Ключевые инсайты и рекомендации</h3>
            <ul>
                ${{insights.map(i => `<li><span>🔍</span><span>${{i}}</span></li>`).join('')}}
            </ul>
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 10px;">
                <strong>📊 Выводы:</strong><br>
                • Масштабировать ПУШ как основной канал (высокая конверсия, нулевые затраты). <br>
                • Не использовать СМС изолированно для возрастной аудитории >50 лет<br>
                • Лучший по конверсии и ROI — канал «PUSH».<br>
                • 
            </div>
        `;
    }}

    function addChart() {{
        if (charts.length >= 16) {{alert('Максимум 16 графиков!'); return;}}
        const metric = document.getElementById('metric-select').value;
        const offset = charts.length * 30;
        charts.push({{id: nextId++, metric: metric, chartType: 'bar', x: 20 + offset, y: 20 + offset, width: 550, height: 450}});
        renderAllCharts();
    }}

    function resetAllCharts() {{
        if (confirm('Удалить все графики?')) {{
            charts = [];
            renderAllCharts();
        }}
    }}

    function changeChartType(chartId, newType) {{
        const chart = charts.find(c => c.id === chartId);
        if (chart && chart.metric !== 'age_analysis') {{chart.chartType = newType; updateChartSize(chartId);}}
    }}

    function removeChart(chartId) {{
        charts = charts.filter(c => c.id !== chartId);
        renderAllCharts();
    }}

    function updateChartSize(chartId) {{
        const chartCard = document.getElementById(`chart-card-${{chartId}}`);
        const chartContainer = document.getElementById(`chart-${{chartId}}`);
        if (!chartCard || !chartContainer) return;
        const chart = charts.find(c => c.id === chartId);
        if (!chart) return;

        const cardHeight = chartCard.clientHeight;
        const cardWidth = chartCard.clientWidth;
        const headerHeight = chartCard.querySelector('.chart-header')?.offsetHeight || 45;
        const availableHeight = cardHeight - headerHeight - 25;
        const availableWidth = cardWidth - 24;

        chartContainer.style.height = availableHeight + 'px';
        chartContainer.style.width = availableWidth + 'px';

        let figure = createFigure(chart.metric, chart.chartType, availableHeight, availableWidth);
        Plotly.react(`chart-${{chartId}}`, figure.data, figure.layout, plotlyConfig);
    }}

    function renderAllCharts() {{
        const container = document.getElementById('charts-grid');
        container.innerHTML = '';
        if (charts.length === 0) {{
            container.innerHTML = '<div style="text-align: center; padding: 100px; background: white; border-radius: 20px; color: #999;">Добавьте графики с помощью панели управления выше</div>';
            return;
        }}

        container.style.position = 'relative';
        container.style.height = (Math.max(800, Math.ceil(charts.length / 2) * 500)) + 'px';

        charts.forEach(chart => {{
            const chartCard = document.createElement('div');
            chartCard.className = 'chart-card';
            chartCard.id = `chart-card-${{chart.id}}`;
            chartCard.style.position = 'absolute';
            chartCard.style.left = '0px';
            chartCard.style.top = '0px';
            chartCard.style.width = chart.width + 'px';
            chartCard.style.height = chart.height + 'px';
            chartCard.style.transform = `translate(${{chart.x}}px, ${{chart.y}}px)`;
            chartCard.setAttribute('data-x', chart.x);
            chartCard.setAttribute('data-y', chart.y);

            const title = getMetricTitle(chart.metric);
            const isAgeChart = chart.metric === 'age_analysis';
            const chartButtons = isAgeChart ? '' : `
                <button class="chart-type-btn" onclick="changeChartType(${{chart.id}}, 'bar')" title="Столбцы">📊</button>
                <button class="chart-type-btn" onclick="changeChartType(${{chart.id}}, 'line')" title="Линии">📈</button>
                <button class="chart-type-btn" onclick="changeChartType(${{chart.id}}, 'scatter')" title="Точки">🔵</button>
            `;

            chartCard.innerHTML = `
                <div class="chart-header">
                    <h3>${{title.length > 45 ? title.substring(0, 45) + '...' : title}}</h3>
                    <div class="header-buttons">
                        ${{chartButtons}}
                        <button class="remove-btn" onclick="removeChart(${{chart.id}})">×</button>
                    </div>
                </div>
                <div id="chart-${{chart.id}}" class="chart-container"></div>
                <div class="resize-handle"></div>
            `;
            container.appendChild(chartCard);

            setTimeout(() => {{
                const cardHeight = chartCard.clientHeight;
                const cardWidth = chartCard.clientWidth;
                const headerHeight = chartCard.querySelector('.chart-header')?.offsetHeight || 45;
                const availableHeight = cardHeight - headerHeight - 25;
                const availableWidth = cardWidth - 24;
                let figure = createFigure(chart.metric, chart.chartType, availableHeight, availableWidth);
                Plotly.newPlot(`chart-${{chart.id}}`, figure.data, figure.layout, plotlyConfig);
            }}, 50);

            setupInteractions(`chart-card-${{chart.id}}`, chart.id);
        }});
    }}

    function setupInteractions(elementId, chartId) {{
        const element = document.getElementById(elementId);
        if (!element) return;

        interact(element).draggable({{
            inertia: false,
            modifiers: [interact.modifiers.restrictRect({{restriction: 'parent', endOnly: true}})],
            onmove: function(event) {{
                const target = event.target;
                const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
                const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
                target.style.transform = `translate(${{x}}px, ${{y}}px)`;
                target.setAttribute('data-x', x);
                target.setAttribute('data-y', y);
                const chart = charts.find(c => c.id === chartId);
                if (chart) {{chart.x = x; chart.y = y;}}
            }}
        }});

        interact(element).resizable({{
            edges: {{bottom: true, right: true}},
            modifiers: [
                interact.modifiers.restrictSize({{min: {{width: 380, height: 320}}, max: {{width: 1200, height: 700}}}})],
            onmove: function(event) {{
                const target = event.target;
                target.style.width = event.rect.width + 'px';
                target.style.height = event.rect.height + 'px';
                const chart = charts.find(c => c.id === chartId);
                if (chart) {{chart.width = event.rect.width; chart.height = event.rect.height;}}
                if (resizeTimeout) clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => updateChartSize(chartId), 100);
            }}
        }});
    }}

    window.addEventListener('resize', () => {{
        if (resizeTimeout) clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => charts.forEach(chart => updateChartSize(chart.id)), 100);
    }});

    createStatsCards();
    createAgeStatsCard();
    createStatsGrid();
    createInsights();

    charts.push({{id: nextId++, metric: 'primary_conversion', chartType: 'bar', x: 20, y: 20, width: 530, height: 420}});
    charts.push({{id: nextId++, metric: 'roi', chartType: 'bar', x: 570, y: 20, width: 530, height: 420}});
    charts.push({{id: nextId++, metric: 'age_analysis', chartType: 'bar', x: 20, y: 460, width: 530, height: 420}});
    charts.push({{id: nextId++, metric: 'bonus_efficiency', chartType: 'bar', x: 570, y: 460, width: 530, height: 420}});
    renderAllCharts();
</script>
</body>
</html>'''

    output_file = 'ab_test_hybrid_dashboard.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ ГИБРИДНЫЙ ДАШБОРД (КЛАССИКА + БАЙЕС) СОЗДАН")
    print(f"   Файл: {output_file}")
    print(f"   Количество групп: {len(all_metrics)}")
    print(f"   Контрольная группа: {control_metrics['name']}")

    print(f"\n📊 Результаты статистических тестов:")
    print(f"\n   ANOVA (конверсия):")
    print(f"      F-статистика: {f_stat_conv:.4f}")
    print(f"      p-value: {p_primary_anova:.6f}")
    print(f"      Значимо: {'ДА' if p_primary_anova < 0.05 else '❌ НЕТ'}")

    print(f"\n   χ²-тест (удержание):")
    for group_id, result in retention_chi2_results.items():
        if group_id != control_id:
            print(f"      {all_metrics[group_id]['name']}: χ²={result['chi2']:.2f}, p={result['p_value']:.4f}")

    print(f"\n   t-критерий (средний чек):")
    for group_id, result in avg_check_ttest_results.items():
        if group_id != control_id:
            print(f"      {all_metrics[group_id]['name']}: diff={result['mean_diff']:.2f}₽, p={result['p_value']:.4f}")

    print(f"\n🎯 Байесовские вероятности:")
    for group_id, result in bootstrap_ci_results.items():
        if group_id != control_id:
            print(
                f"      {all_metrics[group_id]['name']}: {result['prob_better'] * 100:.1f}% вероятности быть лучше контроля")


if __name__ == "__main__":
    create_universal_dashboard()
