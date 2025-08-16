

import os
import json
import glob
from typing import Dict, List, Tuple
import pandas as pd

# 🎯 功率测量噪声鲁棒性实验路径配置
BASE_DIR = "/home/deep/TimeSeries/Agent_V2"
EXPERIMENT_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
NOISE_OUTPUT_BASE = os.path.join(EXPERIMENT_DIR, 'output')

# 输入路径：使用噪声实验的事件分割结果
SEGMENTS_BASE = os.path.join(NOISE_OUTPUT_BASE, '02_event_segments')

# 输出路径：使用噪声实验路径
SCHEDULED_BASE = os.path.join(NOISE_OUTPUT_BASE, '05_Collision_Resolved_Scheduling')
COST_CAL_BASE = os.path.join(NOISE_OUTPUT_BASE, '05_event_split')

TOU_D_CONFIG = os.path.join(BASE_DIR, 'config', 'TOU_D.json')


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def list_houses_from_segments() -> List[str]:
    houses = []
    if os.path.exists(SEGMENTS_BASE):
        for name in os.listdir(SEGMENTS_BASE):
            if name.startswith('house') and os.path.isdir(os.path.join(SEGMENTS_BASE, name)):
                houses.append(name)
    # 数字升序
    def hnum(h):
        try:
            return int(h.replace('house', ''))
        except Exception:
            return 1 << 30
    return sorted(houses, key=hnum)


def load_full_events(house_id: str) -> pd.DataFrame:
    """🎯 已弃用 - 加载原始所有事件，但应该使用TOU过滤结果"""
    path = os.path.join(SEGMENTS_BASE, house_id, f"02_appliance_event_segments_id_{house_id}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Full events file not found: {path}")
    df = pd.read_csv(path)
    # 标准化字段
    if 'start_time' in df.columns:
        df['start_time'] = pd.to_datetime(df['start_time'])
    if 'end_time' in df.columns:
        df['end_time'] = pd.to_datetime(df['end_time'])
    return df


def load_tou_filtered_events(tariff_name: str, house_id: str) -> pd.DataFrame:
    """🎯 加载TOU过滤后的可调度事件作为基准"""
    # 构建TOU过滤结果文件路径
    tou_filter_dir = os.path.join(NOISE_OUTPUT_BASE, '04_tou_optimization_filter')

    if tariff_name in ['Economy_7', 'Economy_10']:
        path = os.path.join(tou_filter_dir, 'UK', tariff_name, house_id, f'tou_filtered_{house_id}_{tariff_name}.csv')
    elif tariff_name == 'TOU_D':
        # TOU_D需要特殊处理，这里先用winter作为示例
        path = os.path.join(tou_filter_dir, 'TOU_D', 'winter', house_id, f'tou_filtered_{house_id}_TOU_D.csv')
    elif tariff_name == 'Germany_Variable':
        path = os.path.join(tou_filter_dir, 'Germany_Variable', house_id, f'tou_filtered_{house_id}_Germany_Variable.csv')
    else:
        raise ValueError(f"Unsupported tariff: {tariff_name}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"TOU filtered events file not found: {path}")

    df = pd.read_csv(path)

    # 🎯 只返回可调度的事件 (is_reschedulable=True)
    if 'is_reschedulable' in df.columns:
        df = df[df['is_reschedulable'] == True].copy()

    # 标准化字段
    if 'start_time' in df.columns:
        df['start_time'] = pd.to_datetime(df['start_time'])
    if 'end_time' in df.columns:
        df['end_time'] = pd.to_datetime(df['end_time'])

    return df


def load_scheduled_events(tariff_name: str, house_id: str) -> pd.DataFrame:
    """加载调度事件文件 - 使用鲁棒性实验路径结构"""
    # 🎯 修改路径结构：鲁棒性实验中不使用UK子目录
    if tariff_name in ['Economy_7', 'Economy_10']:
        path = os.path.join(SCHEDULED_BASE, tariff_name, house_id, 'scheduled_events.csv')
    elif tariff_name == 'TOU_D':
        path = os.path.join(SCHEDULED_BASE, 'TOU_D', house_id, 'scheduled_events.csv')
    elif tariff_name == 'Germany_Variable':
        path = os.path.join(SCHEDULED_BASE, 'Germany_Variable', house_id, 'scheduled_events.csv')
    else:
        raise ValueError(f"Unsupported tariff: {tariff_name}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Scheduled events file not found: {path}")

    df = pd.read_csv(path)
    # 标准化字段
    if 'scheduled_start_time' in df.columns:
        df['scheduled_start_time'] = pd.to_datetime(df['scheduled_start_time'])
    if 'scheduled_end_time' in df.columns:
        df['scheduled_end_time'] = pd.to_datetime(df['scheduled_end_time'])
    if 'original_start_time' in df.columns:
        df['original_start_time'] = pd.to_datetime(df['original_start_time'])
    if 'original_end_time' in df.columns:
        df['original_end_time'] = pd.to_datetime(df['original_end_time'])
    return df


def tou_d_month_to_season(month: int) -> str:
    try:
        with open(TOU_D_CONFIG, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        months_summer = set(cfg['TOU_D']['seasonal_rates']['summer']['months'])
        months_winter = set(cfg['TOU_D']['seasonal_rates']['winter']['months'])
        if month in months_summer:
            return 'summer'
        if month in months_winter:
            return 'winter'
    except Exception:
        pass
    return 'unknown'


def split_events_for_house(tariff_name: str, house_id: str) -> Dict[str, Dict[str, str]]:
    """为某个house输出迁移/未迁移事件CSV，返回生成的文件路径。
    返回结构：{ scope_key: { 'migrated': path, 'non_migrated': path, 'stats': {...} } }
    scope_key：
      - UK: 'Economy_7' 或 'Economy_10'
      - TOU_D: 'winter' 或 'summer'
      - Germany_Variable: 'All'
    """
    # 🎯 不再使用原始事件，而是根据电价方案加载TOU过滤结果
    results: Dict[str, Dict[str, str]] = {}

    def make_join(df_sched_success: pd.DataFrame, scope_key: str, out_dir: str, tariff_name: str):
        ensure_dir(out_dir)

        # 🎯 加载原始所有事件作为基准
        df_all_events = load_full_events(house_id)

        # 🎯 加载TOU过滤后的可调度事件用于能量信息合并
        df_tou_filtered = load_tou_filtered_events(tariff_name, house_id)

        # 基础列检查
        if 'event_id' not in df_all_events.columns:
            raise ValueError("All events file missing 'event_id' column")

        # 成功迁移的事件列表
        migrated_ids = set(df_sched_success['event_id'].tolist())

        # migrated: 合并能量信息（从TOU过滤结果获取）
        df_migrated = df_sched_success[['event_id', 'appliance_name', 'original_start_time', 'original_end_time',
                                        'scheduled_start_time', 'scheduled_end_time', 'schedule_status']].copy()
        df_migrated = df_migrated.merge(
            df_tou_filtered[['event_id', 'duration(min)', 'energy(W)']], on='event_id', how='left'
        )

        # 🎯 non-migrated: 所有原始事件 - 成功迁移的事件
        df_non_migrated = df_all_events[~df_all_events['event_id'].isin(migrated_ids)].copy()
        # 统一字段名
        if 'start_time' in df_non_migrated.columns:
            df_non_migrated.rename(columns={'start_time': 'original_start_time', 'end_time': 'original_end_time'}, inplace=True)
        # 输出
        migrated_path = os.path.join(out_dir, 'migrated_events.csv')
        non_migrated_path = os.path.join(out_dir, 'non_migrated_events.csv')
        df_migrated.to_csv(migrated_path, index=False)
        df_non_migrated.to_csv(non_migrated_path, index=False)
        # 🎯 统计 - 使用原始所有事件作为总数
        stats = {
            'house_id': house_id,
            'scope': scope_key,
            'total_events': int(len(df_all_events)),  # 所有原始事件总数
            'migrated': int(len(df_migrated)),
            'non_migrated': int(len(df_non_migrated)),
        }
        results[scope_key] = {
            'migrated': migrated_path,
            'non_migrated': non_migrated_path,
            'stats': stats,
        }

    if tariff_name in ['Economy_7', 'Economy_10']:
        # 🎯 鲁棒性实验：UK方案直接处理，不使用UK子目录
        df_sched = load_scheduled_events(tariff_name, house_id)
        df_success = df_sched[df_sched['schedule_status'] == 'SUCCESS'].copy()
        out_dir = os.path.join(COST_CAL_BASE, tariff_name, house_id)
        make_join(df_success, tariff_name, out_dir, tariff_name)

    elif tariff_name == 'TOU_D':
        df_sched = load_scheduled_events('TOU_D', house_id)
        for season in ['winter', 'summer']:
            df_success = df_sched[(df_sched['schedule_status'] == 'SUCCESS') & (df_sched['season'] == season)].copy()
            # 非迁移部分需按季节划分：用开始时间月份映射
            df_full_season = df_full.copy()
            if 'start_time' in df_full_season.columns:
                months = pd.to_datetime(df_full_season['start_time']).dt.month
                df_full_season = df_full_season[months.apply(lambda m: tou_d_month_to_season(int(m)) == season)].copy()
            # 对应季节范围内的migrated集合做差集
            migrated_ids = set(df_success['event_id'].tolist())
            df_migrated = df_success[['event_id', 'appliance_name', 'original_start_time', 'original_end_time',
                                      'scheduled_start_time', 'scheduled_end_time', 'schedule_status', 'season']].copy()
            df_migrated = df_migrated.merge(
                df_full[['event_id', 'duration(min)', 'energy(W)']], on='event_id', how='left'
            )
            df_non_migrated = df_full_season[~df_full_season['event_id'].isin(migrated_ids)].copy()
            if 'start_time' in df_non_migrated.columns:
                df_non_migrated.rename(columns={'start_time': 'original_start_time', 'end_time': 'original_end_time'}, inplace=True)
            out_dir = os.path.join(COST_CAL_BASE, 'TOU_D', season, house_id)
            ensure_dir(out_dir)
            migrated_path = os.path.join(out_dir, 'migrated_events.csv')
            non_migrated_path = os.path.join(out_dir, 'non_migrated_events.csv')
            df_migrated.to_csv(migrated_path, index=False)
            df_non_migrated.to_csv(non_migrated_path, index=False)
            stats = {
                'house_id': house_id,
                'scope': season,
                'total_events': int(len(df_full_season)),
                'migrated': int(len(df_migrated)),
                'non_migrated': int(len(df_non_migrated)),
            }
            results[season] = {
                'migrated': migrated_path,
                'non_migrated': non_migrated_path,
                'stats': stats,
            }

    elif tariff_name == 'Germany_Variable':
        df_sched = load_scheduled_events('Germany_Variable', house_id)
        df_success = df_sched[df_sched['schedule_status'] == 'SUCCESS'].copy()
        out_dir = os.path.join(COST_CAL_BASE, 'Germany_Variable', house_id)
        make_join(df_success, 'All', out_dir, 'Germany_Variable')

    else:
        raise ValueError(f"Unsupported tariff: {tariff_name}")

    return results


def summarize_results(all_results: Dict[str, Dict[str, Dict]]):
    # 打印统计表
    print("\n📋 Event Split Summary Table:")
    print("=" * 108)
    header = f"{'House':8} {'Scope':10} {'Total':>8} {'Migrated':>10} {'Non-Mig':>10}"
    print(header)
    print("-" * len(header))
    total_all = 0
    total_mig = 0
    total_non = 0
    for house_id, scopes in all_results.items():
        for scope_key, data in scopes.items():
            st = data['stats']
            print(f"{st['house_id']:8} {st['scope']:10} {st['total_events']:8d} {st['migrated']:10d} {st['non_migrated']:10d}")
            total_all += st['total_events']
            total_mig += st['migrated']
            total_non += st['non_migrated']
    print("-" * len(header))
    print(f"{'TOTAL':8} {'ALL':10} {total_all:8d} {total_mig:10d} {total_non:10d}")


def run_splitter_interactive():
    print("🎯 P055 Event Splitter - Create migrated/non-migrated CSVs")
    print("=" * 60)

    # 第一次选择：电价方案组
    while True:
        print("\n请选择电价方案 (Tariff Group):")
        print("  1) UK (Economy_7 + Economy_10)")
        print("  2) TOU_D (Seasonal: winter/summer)")
        print("  3) Germany_Variable")
        print("  4) All")
        t_choice = input("Enter 1-4: ").strip()
        if t_choice in {"1", "2", "3", "4"}:
            break
        print("❌ Invalid choice. Try again.")

    # 第二次选择：处理范围
    while True:
        print("\n请选择处理范围 (Scope):")
        print("  1) 单个家庭 (Single house)")
        print("  2) 批处理 (All houses)")
        s_choice = input("Enter 1-2: ").strip()
        if s_choice in {"1", "2"}:
            break
        print("❌ Invalid choice. Try again.")

    # 确定房屋列表
    houses = list_houses_from_segments()
    if s_choice == "1":
        print("\n可选房屋：", ", ".join(houses[:10]), ("..." if len(houses) > 10 else ""))
        hid = input("请输入House ID (如 house1): ").strip()
        if hid not in houses:
            print(f"❌ House {hid} not found in segments. Abort.")
            return
        target_houses = [hid]
    else:
        target_houses = houses

    # 需要处理的tariff列表
    tariff_list: List[str]
    if t_choice == "1":
        tariff_list = ['Economy_7', 'Economy_10']
    elif t_choice == "2":
        tariff_list = ['TOU_D']
    elif t_choice == "3":
        tariff_list = ['Germany_Variable']
    else:
        tariff_list = ['Economy_7', 'Economy_10', 'TOU_D', 'Germany_Variable']

    # 执行
    overall_results: Dict[str, Dict[str, Dict]] = {}
    for house_id in target_houses:
        overall_results[house_id] = {}
        for tariff in tariff_list:
            try:
                res = split_events_for_house(tariff, house_id)
                overall_results[house_id].update(res)
                # 简要提示生成的文件
                for scope_key, data in res.items():
                    print(f"✅ {house_id} [{tariff}/{scope_key}] -> {os.path.relpath(data['migrated'], BASE_DIR)}, {os.path.relpath(data['non_migrated'], BASE_DIR)}")
            except FileNotFoundError as e:
                print(f"⚠️  Skip {house_id}/{tariff}: {e}")
            except Exception as e:
                print(f"❌  Error {house_id}/{tariff}: {e}")

    summarize_results(overall_results)


def run_robustness_experiment():
    """运行约束解析错误鲁棒性实验 - 事件分割"""
    print("🚀 约束解析错误鲁棒性实验 - Event Splitter")
    print("=" * 60)

    # 固定参数：5个目标家庭，2个电价类型
    target_houses = ["house1", "house2", "house3", "house20", "house21"]
    tariff_list = ['Economy_7', 'Economy_10']

    print(f"🎯 目标家庭: {', '.join(target_houses)}")
    print(f"🎯 电价类型: {', '.join(tariff_list)}")
    print(f"🎯 分割迁移和未迁移事件")

    # 执行事件分割
    overall_results: Dict[str, Dict[str, Dict]] = {}

    for house_id in target_houses:
        print(f"\n🏠 处理 {house_id}...")
        overall_results[house_id] = {}

        for tariff in tariff_list:
            print(f"   📋 处理 {tariff}...")

            try:
                res = split_events_for_house(tariff, house_id)
                overall_results[house_id].update(res)

                # 显示生成的文件
                for scope_key, data in res.items():
                    migrated_file = os.path.relpath(data['migrated'], BASE_DIR)
                    non_migrated_file = os.path.relpath(data['non_migrated'], BASE_DIR)
                    print(f"      ✅ {scope_key}:")
                    print(f"         迁移事件: {migrated_file}")
                    print(f"         未迁移事件: {non_migrated_file}")

            except FileNotFoundError as e:
                print(f"      ⚠️ 跳过 {house_id}/{tariff}: {e}")
            except Exception as e:
                print(f"      ❌ 错误 {house_id}/{tariff}: {e}")

    # 显示汇总结果
    print(f"\n📊 事件分割汇总:")
    print("=" * 60)
    summarize_results(overall_results)

    return overall_results

if __name__ == '__main__':
    # 鲁棒性实验模式：直接运行无交互版本
    run_robustness_experiment()

