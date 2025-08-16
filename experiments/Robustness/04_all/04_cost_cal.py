#!/usr/bin/env python3
"""
P06 Cost Calculator

在不修改其它代码的前提下：
- 读取 p_054_event_splitter 产出的 migrated/non_migrated 事件文件
- 结合 01_preprocessed 的每分钟瞬时功率，按所选电价方案的区间将能量/费用分摊
- 未迁移事件计算一次（原始时间窗）
- 成功迁移事件计算两次（迁移前：original，迁移后：scheduled）
- 支持批处理/单户两层选择；支持 UK(Economy_7/Economy_10)、TOU_D(按季节)、Germany_Variable
- 缺失分钟功率按0处理

输出：output/06_cost_cal/
  UK/Economy_7/houseX/{migrated_costs.csv, non_migrated_costs.csv}
  UK/Economy_10/houseX/{...}
  TOU_D/{winter,summer}/houseX/{...}
  Germany_Variable/houseX/{...}

成本计算：
  每分钟能量(Wh) = Power(W)/60；每档能量(kWh) = sum(Wh)/1000；费用 = kWh * rate
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
import pandas as pd

# 🎯 修改为鲁棒性实验路径配置
BASE_DIR = "/home/deep/TimeSeries/Agent_V2"
OUTPUT_BASE = os.path.join(BASE_DIR, 'output')
ROBUSTNESS_OUTPUT_BASE = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/output"

# 输入路径：使用04_all实验的噪声功率数据
PREPROC_BASE = os.path.join(ROBUSTNESS_OUTPUT_BASE, '01_preprocessed')

# 输出路径：使用鲁棒性实验路径
SPLIT_BASE = os.path.join(ROBUSTNESS_OUTPUT_BASE, '05_event_split')
COST_BASE = os.path.join(ROBUSTNESS_OUTPUT_BASE, '06_cost_cal')

TARIFF_CFG = os.path.join(BASE_DIR, 'config', 'tariff_config.json')
TOU_D_CFG = os.path.join(BASE_DIR, 'config', 'TOU_D.json')
GER_VAR_CFG = os.path.join(BASE_DIR, 'config', 'Germany_Variable.json')

# -------------- 基础工具 --------------

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _load_json_robust(path: str) -> dict:
    """健壮地读取 JSON：去BOM、去 // 注释、去尾随逗号"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()

        # 去除 BOM
        if text and text[0] == '\ufeff':
            text = text.lstrip('\ufeff')

        # 去除 // 注释
        text = re.sub(r"//[^\n\r]*", "", text)
        # 去除 /**/ 注释（简单处理，不跨多层嵌套）
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        # 去除尾随逗号：,\s*} 或 ,\s*]
        text = re.sub(r",\s*([}\]])", r"\1", text)

        try:
            return json.loads(text)
        except Exception:
            # 再次尝试：压缩多余空白
            text2 = "\n".join([line.rstrip() for line in text.splitlines() if line.strip()])
            return json.loads(text2)
    except Exception as e:
        print(f"❌ JSON 文件读取失败 {path}: {e}")
        raise


def list_houses() -> List[str]:
    houses = []
    if os.path.exists(PREPROC_BASE):
        for d in os.listdir(PREPROC_BASE):
            if d.startswith('house') and os.path.isdir(os.path.join(PREPROC_BASE, d)):
                houses.append(d)
    def hnum(h):
        try: return int(h.replace('house',''))
        except: return 1<<30
    return sorted(houses, key=hnum)


# -------------- 电价区间解析 --------------

def time_to_minutes(t: str) -> int:
    h, m = map(int, t.split(':'))
    return h*60 + m


def build_uk_periods(tariff: str) -> List[Tuple[int,int,float,int]]:
    """返回[(start_min, end_min, rate, level_id)]，跨午夜时段拆分为两段(简化处理)。"""
    cfg = _load_json_robust(TARIFF_CFG)
    periods = cfg[tariff]['periods']
    # 获取唯一费率并映射level: 低价为level 0，高价为level 1
    rates = sorted({p['rate'] for p in periods})
    rate_to_level = {r:i for i,r in enumerate(rates)}
    out = []
    for p in periods:
        s = time_to_minutes(p['start']); e = time_to_minutes(p['end']); rate = p['rate']
        level = rate_to_level[rate]
        if s < e:
            out.append((s,e,rate,level))
        else:
            out.append((s,24*60,rate,level))
            out.append((0,e,rate,level))
    return out


def build_tou_d_periods(season: str) -> List[Tuple[int,int,float,int]]:
    cfg = _load_json_robust(TOU_D_CFG)
    blocks = cfg['TOU_D']['seasonal_rates'][season]['time_blocks']
    rates = sorted({b['rate'] for b in blocks})
    rate_to_level = {r:i for i,r in enumerate(rates)}
    out = []
    for b in blocks:
        s = time_to_minutes(b['start']); e = time_to_minutes(b['end']); rate = b['rate']
        level = rate_to_level[rate]
        if s < e:
            out.append((s,e,rate,level))
        else:
            out.append((s,24*60,rate,level)); out.append((0,e,rate,level))
    return out


def build_germany_periods() -> List[Tuple[int,int,float,int]]:
    cfg = _load_json_robust(GER_VAR_CFG)
    blocks = cfg['Germany_Variable']['time_blocks']
    out = []
    for i,b in enumerate(blocks):
        s = time_to_minutes(b['start']); e = time_to_minutes(b['end']); rate = b['rate']
        if s < e:
            out.append((s,e,rate,i))
        else:
            out.append((s,24*60,rate,i)); out.append((0,e,rate,i))
    return out


def minute_level_info(ts: pd.Timestamp, periods: List[Tuple[int,int,float,int]]) -> Tuple[int,float,int]:
    m = ts.hour*60 + ts.minute
    for s,e,rate,level in periods:
        if s <= m < e:
            return level, rate, m
    # 若未匹配，取最后一档
    s,e,rate,level = periods[-1]
    return level, rate, m


# -------------- 功率时间序列读取 --------------

_preproc_cache: Dict[str, pd.DataFrame] = {}
# 缓存：house -> { 'id_to_name':{}, 'event_to_id':{}, 'power_cols':set([...]) }
_house_maps_cache: Dict[str, Dict] = {}

def load_power_timeseries(house_id: str) -> pd.DataFrame:
    if house_id in _preproc_cache:
        return _preproc_cache[house_id]
    path = os.path.join(PREPROC_BASE, house_id, f"01_perception_alignment_result_{house_id}_noisy.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Power series not found: {path}")
    df = pd.read_csv(path)
    # 识别时间列：优先 'timestamp' 其次首列
    time_col = None
    for c in ['timestamp','time','datetime','DateTime','date_time']:
        if c in df.columns:
            time_col = c; break
    if time_col is None:
        time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col]).copy()
    df = df.sort_values(time_col).set_index(time_col)
    _preproc_cache[house_id] = df
    return df


def slice_power(df_power: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, appliance_col: str) -> pd.Series:
    # 半开区间 [start, end)，按分钟取值；缺失按0
    rng = pd.date_range(start=start, end=end, freq='min', inclusive='left')
    if appliance_col not in df_power.columns:
        return pd.Series(0.0, index=rng)
    s = df_power[appliance_col].reindex(rng)
    return s.fillna(0.0)


# -------------- 事件费用计算 --------------

def _load_house_maps(house_id: str) -> Dict:
    """读取本户映射：
    - id_to_name: 来自 02_behavior_modeling/02_1_appliance_shiftable_label_house{n}.csv
    - event_to_id: 来自 02_event_segments/02_appliance_event_segments_id_house{n}.csv
    - power_cols: 01_preprocessed 的列集合
    """
    if house_id in _house_maps_cache:
        return _house_maps_cache[house_id]
    maps = {'id_to_name': {}, 'event_to_id': {}, 'power_cols': set()}
    # id->name
    path_label = os.path.join(OUTPUT_BASE, '02_behavior_modeling', house_id, f'02_1_appliance_shiftable_label_{house_id}.csv')
    if os.path.exists(path_label):
        try:
            df = pd.read_csv(path_label)
            if {'ApplianceID','ApplianceName'}.issubset(df.columns):
                for _, r in df[['ApplianceID','ApplianceName']].iterrows():
                    maps['id_to_name'][str(r['ApplianceID'])] = str(r['ApplianceName'])
        except Exception:
            pass
    # event->id
    path_ev = os.path.join(OUTPUT_BASE, '02_event_segments', house_id, f'02_appliance_event_segments_id_{house_id}.csv')
    if os.path.exists(path_ev):
        try:
            df = pd.read_csv(path_ev, usecols=['event_id','appliance_ID'])
            for _, r in df.iterrows():
                maps['event_to_id'][str(r['event_id'])] = str(r['appliance_ID'])
        except Exception:
            pass
    # power columns
    try:
        df_power = load_power_timeseries(house_id)
        maps['power_cols'] = set(map(str, df_power.columns))
    except Exception:
        maps['power_cols'] = set()
    _house_maps_cache[house_id] = maps
    return maps


def _normalize_name(s: str) -> str:
    s = s or ''
    s = s.strip()
    # 去掉括号及内容、去掉 Site 后缀、大小写统一
    s = re.sub(r'\([^)]*\)', '', s)
    s = s.replace('Site', '').strip()
    return s.lower()


def _resolve_power_column(house_id: str, event_row: pd.Series, df_power: pd.DataFrame) -> Optional[str]:
    maps = _load_house_maps(house_id)
    cols = list(df_power.columns)
    cols_norm = {c: _normalize_name(str(c)) for c in cols}

    name = str(event_row.get('appliance_name', '')).strip()
    ev_id = str(event_row.get('event_id', ''))
    app_id = event_row.get('appliance_ID')
    if pd.isna(app_id):
        app_id = None
    app_id = str(app_id) if app_id is not None else None
    if (not app_id) and ev_id and ev_id in maps['event_to_id']:
        app_id = maps['event_to_id'][ev_id]

    # 1) 直接用名称匹配
    if name in cols:
        return name
    nname = _normalize_name(name)
    for c, cn in cols_norm.items():
        if nname and cn == nname:
            return c
    for c, cn in cols_norm.items():
        if nname and (nname in cn or cn in nname) and len(nname) >= 3:
            return c

    # 2) 用ID匹配
    if app_id:
        if app_id in cols:
            return app_id
        mapped = maps['id_to_name'].get(app_id)
        if mapped and mapped in cols:
            return mapped
        if mapped:
            nm = _normalize_name(mapped)
            for c, cn in cols_norm.items():
                if cn == nm or (nm in cn or cn in nm):
                    return c

    # 3) 回退：None
    return None


def calc_event_costs(house_id: str,
                     _tariff: str,
                     event_row: pd.Series,
                     when: str,
                     periods: List[Tuple[int,int,float,int]],
                     season: str=None) -> Dict:
    """when: 'original' 或 'scheduled'；返回能量/费用分档明细
    修复：使用事件记录的能耗，不依赖时间序列数据，确保迁移前后功耗一致"""

    # 获取事件的基本信息
    if when == 'original':
        start = pd.to_datetime(event_row['original_start_time'])
        end = pd.to_datetime(event_row['original_end_time'])
    else:
        start = pd.to_datetime(event_row['scheduled_start_time'])
        end = pd.to_datetime(event_row['scheduled_end_time'])

    # 使用事件记录的能耗和持续时间，而不是时间序列数据
    try:
        event_energy_w = float(event_row.get('energy(W)', 0))  # 事件总能耗(W)
        if pd.isna(event_energy_w):
            event_energy_w = 0.0
    except (ValueError, TypeError):
        event_energy_w = 0.0

    try:
        event_duration_min = float(event_row.get('duration(min)', 0))  # 事件持续时间(分钟)
        if pd.isna(event_duration_min):
            event_duration_min = 0.0
    except (ValueError, TypeError):
        event_duration_min = 0.0

    # 如果没有能耗数据，尝试从时间计算或从时间序列获取
    if event_energy_w == 0:
        if event_duration_min == 0:
            # 如果持续时间也没有，从开始结束时间计算
            try:
                duration_td = end - start
                event_duration_min = duration_td.total_seconds() / 60.0
            except:
                event_duration_min = 0.0

        # 尝试从时间序列获取功率数据
        if event_duration_min > 0:
            try:
                df_power = load_power_timeseries(house_id)
                power_col = _resolve_power_column(house_id, event_row, df_power)
                if power_col:
                    series_w = slice_power(df_power, start, end, power_col)
                    event_energy_w = float(series_w.sum())
                    # 更新持续时间为实际数据点数
                    if len(series_w) > 0:
                        event_duration_min = len(series_w)
            except:
                pass

    # 按时间段分配能耗到不同电价级别
    per_level = {}  # level -> {'minutes': n, 'sumW': x, 'kWh': y, 'cost': z, 'rate': r}

    if event_duration_min > 0:
        # 计算每分钟的平均功率
        avg_power_per_minute = event_energy_w / event_duration_min

        # 按分钟遍历事件时间段，分配到不同电价级别
        current_time = start
        duration_int = max(1, int(round(event_duration_min)))  # 至少1分钟，避免0分钟事件
        for _ in range(duration_int):
            level, rate, _ = minute_level_info(current_time, periods)
            d = per_level.setdefault(level, {'minutes':0, 'sumW':0.0, 'kWh':0.0, 'cost':0.0, 'rate':rate})
            d['minutes'] += 1
            d['sumW'] += avg_power_per_minute
            current_time += pd.Timedelta(minutes=1)

    # 计算各级别的kWh和费用
    total_kwh = 0.0
    total_cost = 0.0
    for lev, d in per_level.items():
        d['kWh'] = d['sumW']/60.0/1000.0  # W -> kWh
        d['cost'] = d['kWh'] * d['rate']
        total_kwh += d['kWh']
        total_cost += d['cost']

    # 获取所有可能的级别（从periods中推断）
    all_levels = set(level for _, _, _, level in periods)

    # 扁平化输出
    app = event_row.get('appliance_name', '')
    flat = {
        'event_id': event_row['event_id'],
        'appliance_name': app,
        'when': when,
        'season': season or '',
        'start_time': start,
        'end_time': end,
        'minutes': max(1, int(round(event_duration_min))),  # 确保至少1分钟
        'total_W': event_energy_w,  # 使用事件记录的总能耗
        'total_cost': total_cost,
    }

    # 为所有级别填充数据，确保没有空值
    for lev in sorted(all_levels):
        if lev in per_level:
            d = per_level[lev]
            flat[f'level_{lev}_minutes'] = d['minutes']
            flat[f'level_{lev}_W'] = d['sumW']
            flat[f'level_{lev}_rate'] = d['rate']
            flat[f'level_{lev}_cost'] = d['cost']
        else:
            # 填充空值为0，但费率需要从periods中获取
            rate = next((r for _, _, r, l in periods if l == lev), 0.0)
            flat[f'level_{lev}_minutes'] = 0
            flat[f'level_{lev}_W'] = 0.0
            flat[f'level_{lev}_rate'] = rate
            flat[f'level_{lev}_cost'] = 0.0
    return flat


def process_house_tariff(house_id: str, tariff: str, scope: str):
    """scope: 对UK为'Economy_7'/'Economy_10'; 对TOU_D为'winter'/'summer'; 对Germany为'All'"""
    # 读取事件文件
    if tariff in ['Economy_7','Economy_10']:
        # 🎯 鲁棒性实验：不使用UK子目录
        in_dir = os.path.join(SPLIT_BASE, scope, house_id)
        out_dir = os.path.join(COST_BASE, scope, house_id)
        periods = build_uk_periods(scope)
        seasons = [None]
    elif tariff == 'TOU_D':
        in_dir = os.path.join(SPLIT_BASE, 'TOU_D', scope, house_id)
        out_dir = os.path.join(COST_BASE, 'TOU_D', scope, house_id)
        periods = build_tou_d_periods(scope)
        seasons = [scope]
    elif tariff == 'Germany_Variable':
        in_dir = os.path.join(SPLIT_BASE, 'Germany_Variable', house_id)
        out_dir = os.path.join(COST_BASE, 'Germany_Variable', house_id)
        periods = build_germany_periods()
        seasons = [None]
    else:
        raise ValueError('Unsupported tariff')

    migrated_path = os.path.join(in_dir, 'migrated_events.csv')
    non_migrated_path = os.path.join(in_dir, 'non_migrated_events.csv')
    if not os.path.exists(migrated_path) or not os.path.exists(non_migrated_path):
        raise FileNotFoundError(f"Missing input CSV in {in_dir}")

    df_mig = pd.read_csv(migrated_path)
    df_non = pd.read_csv(non_migrated_path)

    ensure_dir(out_dir)

    # 非迁移：计算一次 original，为每个事件添加区间电价分解列
    non_records: List[Dict] = []
    for _, row in df_non.iterrows():
        rec = calc_event_costs(house_id, tariff, row, when='original', periods=periods, season=seasons[0])
        non_records.append(rec)
    df_non_out = pd.DataFrame(non_records)
    df_non_out.to_csv(os.path.join(out_dir, 'non_migrated_costs.csv'), index=False)

    # 成功迁移：计算 original 和 scheduled，为每个事件添加迁移前后的区间电价分解列
    mig_records: List[Dict] = []
    for _, row in df_mig.iterrows():
        rec_o = calc_event_costs(house_id, tariff, row, when='original', periods=periods, season=seasons[0])
        rec_s = calc_event_costs(house_id, tariff, row, when='scheduled', periods=periods, season=seasons[0])
        # 合并为单行：orig_/sched_前缀区分迁移前后
        merged = {
            'event_id': row['event_id'],
            'appliance_name': row['appliance_name'],
        }
        for k,v in rec_o.items():
            if k in ['event_id','appliance_name']: continue
            merged[f'orig_{k}'] = v
        for k,v in rec_s.items():
            if k in ['event_id','appliance_name']: continue
            merged[f'sched_{k}'] = v
        mig_records.append(merged)
    df_mig_out = pd.DataFrame(mig_records)
    df_mig_out.to_csv(os.path.join(out_dir, 'migrated_costs.csv'), index=False)

    # 简要统计
    stats = {
        'house_id': house_id,
        'scope': scope,
        'non_total': int(len(df_non_out)),
        'non_W': float(df_non_out['total_W'].sum() if 'total_W' in df_non_out else 0.0),
        'non_cost': float(df_non_out['total_cost'].sum() if 'total_cost' in df_non_out else 0.0),
        'mig_total': int(len(df_mig_out)),
        'mig_orig_W': float(df_mig_out.filter(like='orig_total_W').sum().sum()),
        'mig_sched_W': float(df_mig_out.filter(like='sched_total_W').sum().sum()),
        'mig_orig_cost': float(df_mig_out.filter(like='orig_total_cost').sum().sum()),
        'mig_sched_cost': float(df_mig_out.filter(like='sched_total_cost').sum().sum()),
    }

    return stats


def calc_standard_cost(house_id: str, tariff_group: str) -> Dict:
    """计算Standard费用（假设所有事件都按固定费率计算）"""
    # 读取所有事件（未迁移+成功迁移）
    all_events = []

    if tariff_group == 'UK':
        # 🎯 鲁棒性实验：UK的两种电价方案，不使用UK子目录
        for sub_tariff in ['Economy_7', 'Economy_10']:
            non_path = os.path.join(SPLIT_BASE, sub_tariff, house_id, 'non_migrated_events.csv')
            mig_path = os.path.join(SPLIT_BASE, sub_tariff, house_id, 'migrated_events.csv')

            if os.path.exists(non_path):
                df_non = pd.read_csv(non_path)
                all_events.extend(df_non.to_dict('records'))
            if os.path.exists(mig_path):
                df_mig = pd.read_csv(mig_path)
                all_events.extend(df_mig.to_dict('records'))
            break  # 只需要读取一次事件数据

    elif tariff_group == 'TOU_D':
        # TOU_D的两个季节
        for season in ['winter', 'summer']:
            non_path = os.path.join(SPLIT_BASE, 'TOU_D', season, house_id, 'non_migrated_events.csv')
            mig_path = os.path.join(SPLIT_BASE, 'TOU_D', season, house_id, 'migrated_events.csv')

            if os.path.exists(non_path):
                df_non = pd.read_csv(non_path)
                all_events.extend(df_non.to_dict('records'))
            if os.path.exists(mig_path):
                df_mig = pd.read_csv(mig_path)
                all_events.extend(df_mig.to_dict('records'))

    elif tariff_group == 'Germany_Variable':
        non_path = os.path.join(SPLIT_BASE, 'Germany_Variable', house_id, 'non_migrated_events.csv')
        mig_path = os.path.join(SPLIT_BASE, 'Germany_Variable', house_id, 'migrated_events.csv')

        if os.path.exists(non_path):
            df_non = pd.read_csv(non_path)
            all_events.extend(df_non.to_dict('records'))
        if os.path.exists(mig_path):
            df_mig = pd.read_csv(mig_path)
            all_events.extend(df_mig.to_dict('records'))

    # 计算总能耗和Standard费用
    total_energy_w = 0.0
    for event in all_events:
        try:
            energy_w = float(event.get('energy(W)', 0))
            if pd.isna(energy_w):
                energy_w = 0.0
            total_energy_w += energy_w
        except (ValueError, TypeError):
            continue

    total_energy_kwh = total_energy_w / 1000.0 / 60.0

    # 根据电价方案选择Standard/Base费率（从配置文件读取）
    try:
        if tariff_group == 'TOU_D':
            # config/TOU_D.json: 节点 TOU_D_Base.rate
            cfg = _load_json_robust(TOU_D_CFG)
            standard_rate = float(cfg.get('TOU_D_Base', {}).get('rate', 0.60))
        elif tariff_group == 'UK':
            # config/tariff_config.json: 节点 Standard.rate
            cfg = _load_json_robust(TARIFF_CFG)
            standard_rate = float(cfg.get('Standard', {}).get('rate', 0.3))
        elif tariff_group == 'Germany_Variable':
            # config/Germany_Variable.json: 优先 Germany_Variable_Base.rate；否则 Germany_Variable.default_rate
            cfg = _load_json_robust(GER_VAR_CFG)
            standard_rate = cfg.get('Germany_Variable_Base', {}).get('rate')
            if standard_rate is None:
                standard_rate = cfg.get('Germany_Variable', {}).get('default_rate', 0.3)
            standard_rate = float(standard_rate)
        else:
            standard_rate = 0.3  # 默认
    except Exception:
        # 配置读取失败时的兜底
        if tariff_group == 'TOU_D':
            standard_rate = 0.60
        elif tariff_group == 'UK':
            standard_rate = 0.3
        elif tariff_group == 'Germany_Variable':
            standard_rate = 0.34
        else:
            standard_rate = 0.3

    standard_cost = total_energy_kwh * standard_rate

    return {
        'house_id': house_id,
        'total_events': len(all_events),
        'total_energy_kwh': total_energy_kwh,
        'standard_cost': standard_cost
    }


def create_total_cost_summary(all_stats: List[Dict], tariff_group: str):
    """创建总费用对比表格"""
    if not all_stats:
        return

    # 按家庭分组统计
    house_summary = {}
    for stat in all_stats:
        house_id = stat['house_id']
        scope = stat['scope']

        if house_id not in house_summary:
            house_summary[house_id] = {}

        house_summary[house_id][scope] = {
            'non_cost': stat['non_cost'],
            'mig_before_cost': stat['mig_orig_cost'],
            'mig_after_cost': stat['mig_sched_cost'],
            'total_energy_kwh': (stat['non_W'] + stat['mig_orig_W']) / 1000.0 / 60.0
        }

    print(f"\n📊 Total Cost Comparison - {tariff_group}")
    print("="*150)

    if tariff_group == 'UK':
        header = f"{'House':8} {'Standard':>12} {'Economy_7':>12} {'Economy_7':>12} {'Economy_10':>12} {'Economy_10':>12} {'Total':>12}"
        subheader = f"{'ID':8} {'Cost':>12} {'Before':>12} {'After':>12} {'Before':>12} {'After':>12} {'Energy(kWh)':>12}"
        print(header)
        print(subheader)
        print("-"*150)

        # 按数字顺序排序 house ID
        def house_sort_key(house_id):
            try:
                return int(house_id.replace('house', ''))
            except:
                return 999  # 非标准格式的放到最后

        for house_id in sorted(house_summary.keys(), key=house_sort_key):
            # 计算Standard费用
            std_info = calc_standard_cost(house_id, tariff_group)

            e7_before = house_summary[house_id].get('Economy_7', {}).get('non_cost', 0) + house_summary[house_id].get('Economy_7', {}).get('mig_before_cost', 0)
            e7_after = house_summary[house_id].get('Economy_7', {}).get('non_cost', 0) + house_summary[house_id].get('Economy_7', {}).get('mig_after_cost', 0)
            e10_before = house_summary[house_id].get('Economy_10', {}).get('non_cost', 0) + house_summary[house_id].get('Economy_10', {}).get('mig_before_cost', 0)
            e10_after = house_summary[house_id].get('Economy_10', {}).get('non_cost', 0) + house_summary[house_id].get('Economy_10', {}).get('mig_after_cost', 0)

            print(f"{house_id:8} {std_info['standard_cost']:12.2f} {e7_before:12.2f} {e7_after:12.2f} {e10_before:12.2f} {e10_after:12.2f} {std_info['total_energy_kwh']:12.3f}")

    elif tariff_group == 'TOU_D':
        header = f"{'House':8} {'Standard':>12} {'Combined':>12} {'Combined':>12} {'Total':>12}"
        subheader = f"{'ID':8} {'Cost':>12} {'Before':>12} {'After':>12} {'Energy(kWh)':>12}"
        print(header)
        print(subheader)
        print("-"*150)

        # 按数字顺序排序 house ID
        def house_sort_key(house_id):
            try:
                return int(house_id.replace('house', ''))
            except:
                return 999  # 非标准格式的放到最后

        for house_id in sorted(house_summary.keys(), key=house_sort_key):
            std_info = calc_standard_cost(house_id, tariff_group)

            # 合并两个季节的费用
            winter_before = house_summary[house_id].get('winter', {}).get('non_cost', 0) + house_summary[house_id].get('winter', {}).get('mig_before_cost', 0)
            winter_after = house_summary[house_id].get('winter', {}).get('non_cost', 0) + house_summary[house_id].get('winter', {}).get('mig_after_cost', 0)
            summer_before = house_summary[house_id].get('summer', {}).get('non_cost', 0) + house_summary[house_id].get('summer', {}).get('mig_before_cost', 0)
            summer_after = house_summary[house_id].get('summer', {}).get('non_cost', 0) + house_summary[house_id].get('summer', {}).get('mig_after_cost', 0)

            # 计算合并后的总费用
            combined_before = winter_before + summer_before
            combined_after = winter_after + summer_after

            print(f"{house_id:8} {std_info['standard_cost']:12.2f} {combined_before:12.2f} {combined_after:12.2f} {std_info['total_energy_kwh']:12.3f}")

    elif tariff_group == 'Germany_Variable':
        header = f"{'House':8} {'Standard':>12} {'Variable':>12} {'Variable':>12} {'Total':>12}"
        subheader = f"{'ID':8} {'Cost':>12} {'Before':>12} {'After':>12} {'Energy(kWh)':>12}"
        print(header)
        print(subheader)
        print("-"*150)

        # 按数字顺序排序 house ID
        def house_sort_key(house_id):
            try:
                return int(house_id.replace('house', ''))
            except:
                return 999  # 非标准格式的放到最后

        for house_id in sorted(house_summary.keys(), key=house_sort_key):
            std_info = calc_standard_cost(house_id, tariff_group)

            var_before = house_summary[house_id].get('All', {}).get('non_cost', 0) + house_summary[house_id].get('All', {}).get('mig_before_cost', 0)
            var_after = house_summary[house_id].get('All', {}).get('non_cost', 0) + house_summary[house_id].get('All', {}).get('mig_after_cost', 0)

            print(f"{house_id:8} {std_info['standard_cost']:12.2f} {var_before:12.2f} {var_after:12.2f} {std_info['total_energy_kwh']:12.3f}")

    print("-"*150)


def summarize(all_stats: List[Dict]):
    if not all_stats:
        print("No stats.")
        return

    # 按电价方案分组
    grouped_stats = {}
    for st in all_stats:
        scope = st['scope']
        if scope not in grouped_stats:
            grouped_stats[scope] = []
        grouped_stats[scope].append(st)

    # 为每个电价方案显示单独的表格
    for scope, stats_list in grouped_stats.items():
        print(f"\n📊 P06 Cost Summary - {scope}")
        print("="*120)
        header = f"{'House':8} {'Non-Migrated':>12} {'Non-Migrated':>12} {'Non-Migrated':>12} {'Migrated':>8} {'Before':>12} {'After':>12} {'Before':>12} {'After':>12}"
        subheader = f"{'ID':8} {'Events':>12} {'Energy(kWh)':>12} {'Cost':>12} {'Events':>8} {'Energy(kWh)':>12} {'Energy(kWh)':>12} {'Cost':>12} {'Cost':>12}"
        print(header)
        print(subheader)
        print("-"*120)

        totals = {k:0.0 for k in ['non_total','non_W','non_cost','mig_total','mig_orig_W','mig_sched_W','mig_orig_cost','mig_sched_cost']}

        for st in stats_list:
            # 转换W到kWh显示 (W/1000/60 = kWh)
            non_kwh = st['non_W'] / 1000.0 / 60.0
            orig_kwh = st['mig_orig_W'] / 1000.0 / 60.0
            sched_kwh = st['mig_sched_W'] / 1000.0 / 60.0

            print(f"{st['house_id']:8} {st['non_total']:12d} {non_kwh:12.3f} {st['non_cost']:12.2f} {st['mig_total']:8d} {orig_kwh:12.3f} {sched_kwh:12.3f} {st['mig_orig_cost']:12.2f} {st['mig_sched_cost']:12.2f}")

            for k in totals:
                totals[k] += st[k]

        print("-"*120)
        # 总计行也转换单位
        total_non_kwh = totals['non_W'] / 1000.0 / 60.0
        total_orig_kwh = totals['mig_orig_W'] / 1000.0 / 60.0
        total_sched_kwh = totals['mig_sched_W'] / 1000.0 / 60.0
        print(f"{'TOTAL':8} {int(totals['non_total']):12d} {total_non_kwh:12.3f} {totals['non_cost']:12.2f} {int(totals['mig_total']):8d} {total_orig_kwh:12.3f} {total_sched_kwh:12.3f} {totals['mig_orig_cost']:12.2f} {totals['mig_sched_cost']:12.2f}")


def create_tou_d_combined_summary(all_stats: List[Dict]):
    """创建 TOU_D 的合并汇总和对比表格"""
    if not all_stats:
        return

    # 按家庭分组统计
    house_summary = {}
    for stat in all_stats:
        house_id = stat['house_id']
        season = stat['scope']  # 'winter' 或 'summer'

        if house_id not in house_summary:
            house_summary[house_id] = {'winter': {}, 'summer': {}}

        house_summary[house_id][season] = {
            'non_cost': stat['non_cost'],
            'non_W': stat['non_W'],
            'mig_before_cost': stat['mig_orig_cost'],
            'mig_after_cost': stat['mig_sched_cost'],
            'mig_before_W': stat['mig_orig_W'],
            'mig_after_W': stat['mig_sched_W'],
            'non_events': stat['non_total'],
            'mig_events': stat['mig_total']
        }

    # 第三个表：Cost Summary - TOU_D（合并冬夏）
    print(f"\n📊 Cost Summary - TOU_D (Combined Winter + Summer)")
    print("="*120)
    header = f"{'House':8} {'Non-Migrated':>12} {'Non-Migrated':>12} {'Non-Migrated':>12} {'Migrated':>8} {'Before':>12} {'After':>12} {'Before':>12} {'After':>12}"
    subheader = f"{'ID':8} {'Events':>12} {'Energy(kWh)':>12} {'Cost':>12} {'Events':>8} {'Energy(kWh)':>12} {'Energy(kWh)':>12} {'Cost':>12} {'Cost':>12}"
    print(header)
    print(subheader)
    print("-"*120)

    # 按数字顺序排序 house ID
    def house_sort_key(house_id):
        try:
            return int(house_id.replace('house', ''))
        except:
            return 999

    totals = {k:0.0 for k in ['non_events','non_W','non_cost','mig_events','mig_orig_W','mig_sched_W','mig_orig_cost','mig_sched_cost']}

    for house_id in sorted(house_summary.keys(), key=house_sort_key):
        house_data = house_summary[house_id]

        # 合并冬夏数据
        combined_non_events = house_data.get('winter', {}).get('non_events', 0) + house_data.get('summer', {}).get('non_events', 0)
        combined_non_W = house_data.get('winter', {}).get('non_W', 0) + house_data.get('summer', {}).get('non_W', 0)
        combined_non_cost = house_data.get('winter', {}).get('non_cost', 0) + house_data.get('summer', {}).get('non_cost', 0)

        combined_mig_events = house_data.get('winter', {}).get('mig_events', 0) + house_data.get('summer', {}).get('mig_events', 0)
        combined_mig_before_W = house_data.get('winter', {}).get('mig_before_W', 0) + house_data.get('summer', {}).get('mig_before_W', 0)
        combined_mig_after_W = house_data.get('winter', {}).get('mig_after_W', 0) + house_data.get('summer', {}).get('mig_after_W', 0)
        combined_mig_before_cost = house_data.get('winter', {}).get('mig_before_cost', 0) + house_data.get('summer', {}).get('mig_before_cost', 0)
        combined_mig_after_cost = house_data.get('winter', {}).get('mig_after_cost', 0) + house_data.get('summer', {}).get('mig_after_cost', 0)

        # 转换W到kWh显示
        non_kwh = combined_non_W / 1000.0 / 60.0
        before_kwh = combined_mig_before_W / 1000.0 / 60.0
        after_kwh = combined_mig_after_W / 1000.0 / 60.0

        print(f"{house_id:8} {combined_non_events:12d} {non_kwh:12.3f} {combined_non_cost:12.2f} {combined_mig_events:8d} {before_kwh:12.3f} {after_kwh:12.3f} {combined_mig_before_cost:12.2f} {combined_mig_after_cost:12.2f}")

        # 累计到总计
        totals['non_events'] += combined_non_events
        totals['non_W'] += combined_non_W
        totals['non_cost'] += combined_non_cost
        totals['mig_events'] += combined_mig_events
        totals['mig_orig_W'] += combined_mig_before_W
        totals['mig_sched_W'] += combined_mig_after_W
        totals['mig_orig_cost'] += combined_mig_before_cost
        totals['mig_sched_cost'] += combined_mig_after_cost

    print("-"*120)
    # 总计行
    total_non_kwh = totals['non_W'] / 1000.0 / 60.0
    total_before_kwh = totals['mig_orig_W'] / 1000.0 / 60.0
    total_after_kwh = totals['mig_sched_W'] / 1000.0 / 60.0
    print(f"{'TOTAL':8} {int(totals['non_events']):12d} {total_non_kwh:12.3f} {totals['non_cost']:12.2f} {int(totals['mig_events']):8d} {total_before_kwh:12.3f} {total_after_kwh:12.3f} {totals['mig_orig_cost']:12.2f} {totals['mig_sched_cost']:12.2f}")

    # 第四个表：Total Cost Comparison - TOU_D
    create_tou_d_total_cost_comparison(house_summary)


def create_tou_d_total_cost_comparison(house_summary: Dict):
    """创建 TOU_D 的总费用对比表格，包含季节判断逻辑"""
    print(f"\n📊 Total Cost Comparison - TOU_D")
    print("="*120)
    header = f"{'House':8} {'Standard':>12} {'Combined':>12} {'Combined':>12} {'Total':>12}"
    subheader = f"{'ID':8} {'Cost':>12} {'Before':>12} {'After':>12} {'Energy(kWh)':>12}"
    print(header)
    print(subheader)
    print("-"*120)

    # 按数字顺序排序 house ID
    def house_sort_key(house_id):
        try:
            return int(house_id.replace('house', ''))
        except:
            return 999

    for house_id in sorted(house_summary.keys(), key=house_sort_key):
        house_data = house_summary[house_id]

        # 计算合并的 Before/After 费用
        combined_before = house_data.get('winter', {}).get('non_cost', 0) + house_data.get('winter', {}).get('mig_before_cost', 0) + \
                         house_data.get('summer', {}).get('non_cost', 0) + house_data.get('summer', {}).get('mig_before_cost', 0)
        combined_after = house_data.get('winter', {}).get('non_cost', 0) + house_data.get('winter', {}).get('mig_after_cost', 0) + \
                        house_data.get('summer', {}).get('non_cost', 0) + house_data.get('summer', {}).get('mig_after_cost', 0)

        # 计算总能耗
        total_energy_w = house_data.get('winter', {}).get('non_W', 0) + house_data.get('winter', {}).get('mig_before_W', 0) + \
                        house_data.get('summer', {}).get('non_W', 0) + house_data.get('summer', {}).get('mig_before_W', 0)
        total_energy_kwh = total_energy_w / 1000.0 / 60.0

        # 计算 Standard Cost（使用 TOU_D_Base 费率）
        try:
            cfg = _load_json_robust(TOU_D_CFG)
            standard_rate = float(cfg.get('TOU_D_Base', {}).get('rate', 0.60))
        except:
            standard_rate = 0.60

        standard_cost = total_energy_kwh * standard_rate

        print(f"{house_id:8} {standard_cost:12.2f} {combined_before:12.2f} {combined_after:12.2f} {total_energy_kwh:12.3f}")

    print("-"*120)


def run_interactive():
    print("🎯 P06 Cost Calculator - 区间电价费用计算")
    print("="*60)

    # 第一层：电价方案选择
    while True:
        print("\n选择电价方案 (Tariff Scheme):")
        print("  1) UK (Economy_7 + Economy_10) [默认]")
        print("  2) TOU_D (Winter + Summer)")
        print("  3) Germany_Variable")
        g = input("Enter 1-3 (默认1): ").strip()
        if not g:  # 默认选择
            g = '1'
            print(f"使用默认选项: {g} - UK (Economy_7 + Economy_10)")
        if g in {'1','2','3'}: break
        print("❌ Invalid.")

    # 直接使用默认选项，不需要用户再选择
    uk_choice = '3'      # Both Economy_7 and Economy_10
    season_choice = '3'  # Both Winter and Summer

    # 第二层：处理范围
    while True:
        print("\n选择处理范围 (Scope):")
        print("  1) 单个家庭 (Single house) [默认]")
        print("  2) 批处理 (All houses)")
        s = input("Enter 1-2 (默认1): ").strip()
        if not s:  # 默认选择
            s = '1'
            print(f"使用默认选项: {s} - 单个家庭 (Single house)")
        if s in {'1','2'}: break
        print("❌ Invalid.")

    houses = list_houses()
    if s == '1':
        hid = input("输入House ID (e.g., house1): ").strip()
        if hid not in houses:
            print(f"❌ House {hid} not found.")
            return
        targets = [hid]
    else:
        # 批处理：固定 house1~house21，排除 house12 和 house14
        targets = [f"house{i}" for i in range(1, 22) if i not in (12, 14)]
        print(f"📦 批处理目标: {', '.join(targets)}")

    # 需要处理的tariff/scope列表
    tasks: List[Tuple[str,str]] = []  # (tariff, scope)
    if g == '1':  # UK
        if uk_choice == '1':
            tasks += [('Economy_7','Economy_7')]
        elif uk_choice == '2':
            tasks += [('Economy_10','Economy_10')]
        else:  # Both
            tasks += [('Economy_7','Economy_7'), ('Economy_10','Economy_10')]
    elif g == '2':  # TOU_D
        if season_choice == '1':
            tasks += [('TOU_D','winter')]
        elif season_choice == '2':
            tasks += [('TOU_D','summer')]
        else:  # Both
            tasks += [('TOU_D','winter'), ('TOU_D','summer')]
    elif g == '3':  # Germany_Variable
        tasks += [('Germany_Variable','All')]

    # 显示处理计划
    total_tasks = len(targets) * len(tasks)
    print(f"\n🚀 开始处理 {len(targets)} 个家庭，{len(tasks)} 个电价方案，共 {total_tasks} 个任务")

    all_stats: List[Dict] = []
    task_count = 0

    for hid in targets:
        for tariff, scope in tasks:
            task_count += 1
            print(f"\n📊 [{task_count}/{total_tasks}] 处理 {hid} - {tariff}/{scope}...")

            try:
                st = process_house_tariff(hid, tariff, scope)
                all_stats.append(st)
                print(f"✅ 完成 {hid} - {tariff}/{scope}")

            except FileNotFoundError as e:
                print(f"⚠️  跳过 {hid} {tariff}/{scope}: 文件未找到")
            except Exception as e:
                print(f"❌ 错误 {hid} {tariff}/{scope}: {e}")

    # 对 TOU_D 进行特殊处理
    if g == '2':  # TOU_D
        # 先显示分季节的汇总
        summarize(all_stats)
        # 然后显示合并的 TOU_D 汇总和对比
        create_tou_d_combined_summary(all_stats)
    else:
        # UK 和 Germany_Variable 的常规处理
        summarize(all_stats)

        # 添加总费用对比表格
        if all_stats:
            tariff_group = None
            if g == '1':
                tariff_group = 'UK'
            elif g == '3':
                tariff_group = 'Germany_Variable'

            if tariff_group:
                create_total_cost_summary(all_stats, tariff_group)


def run_robustness_experiment():
    """运行约束解析错误鲁棒性实验 - 费用计算"""
    print("🚀 约束解析错误鲁棒性实验 - Cost Calculator")
    print("=" * 60)

    # 固定参数：5个目标家庭，2个电价类型
    target_houses = ["house1", "house2", "house3", "house20", "house21"]
    tasks = [('Economy_7', 'Economy_7'), ('Economy_10', 'Economy_10')]

    print(f"🎯 目标家庭: {', '.join(target_houses)}")
    print(f"🎯 电价类型: Economy_7, Economy_10")
    print(f"🎯 计算迁移和未迁移事件的费用")

    # 显示处理计划
    total_tasks = len(target_houses) * len(tasks)
    print(f"\n🚀 开始处理 {len(target_houses)} 个家庭，{len(tasks)} 个电价方案，共 {total_tasks} 个任务")

    all_stats: List[Dict] = []
    task_count = 0

    for hid in target_houses:
        print(f"\n🏠 处理 {hid}...")

        for tariff, scope in tasks:
            task_count += 1
            print(f"   📊 [{task_count}/{total_tasks}] 处理 {tariff}...")

            try:
                st = process_house_tariff(hid, tariff, scope)
                all_stats.append(st)

                # 显示处理结果
                migrated_cost = st.get('migrated_total_cost', 0)
                non_migrated_cost = st.get('non_migrated_total_cost', 0)
                total_cost = migrated_cost + non_migrated_cost

                print(f"      ✅ 完成 {tariff}")
                print(f"         迁移事件费用: £{migrated_cost:.2f}")
                print(f"         未迁移事件费用: £{non_migrated_cost:.2f}")
                print(f"         总费用: £{total_cost:.2f}")

            except FileNotFoundError as e:
                print(f"      ⚠️ 跳过 {tariff}: 文件未找到")
            except Exception as e:
                print(f"      ❌ 错误 {tariff}: {e}")

    # 显示汇总结果
    print(f"\n📊 费用计算汇总:")
    print("=" * 60)
    summarize(all_stats)

    # 创建UK总费用对比表格
    if all_stats:
        create_total_cost_summary(all_stats, 'UK')

    return all_stats

if __name__ == '__main__':
    # 鲁棒性实验模式：直接运行无交互版本
    run_robustness_experiment()

