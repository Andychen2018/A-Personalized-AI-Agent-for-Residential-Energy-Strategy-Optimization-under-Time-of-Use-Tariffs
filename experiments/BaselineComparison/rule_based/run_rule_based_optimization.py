#!/usr/bin/env python3
"""
基于规则的优化系统 - 只优化每个电器编号最小的事件
每个家庭单独计时，仿照gurobi的保存格式和费用计算方式
"""

import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from first_event_optimizer import FirstEventOptimizer

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RuleBasedProcessor:
    def __init__(self, tariff_config_path: str):
        self.optimizer = FirstEventOptimizer(tariff_config_path)
        logger.info("基于规则的处理器初始化完成")

    def get_all_houses(self, data_dir: str) -> Dict[str, List[str]]:
        """获取所有house列表"""
        houses = {"Economy_7": [], "Economy_10": []}

        for tariff_type in ["Economy_7", "Economy_10"]:
            tariff_dir = os.path.join(data_dir, tariff_type)
            if os.path.exists(tariff_dir):
                house_dirs = [d for d in os.listdir(tariff_dir) if d.startswith('house')]
                houses[tariff_type] = sorted(house_dirs, key=lambda x: int(x.replace('house', '')))

        logger.info(f"找到的house:")
        logger.info(f"  Economy_7: {len(houses['Economy_7'])} houses")
        logger.info(f"  Economy_10: {len(houses['Economy_10'])} houses")

        return houses

    def load_all_events(self, house_id: str) -> pd.DataFrame:
        """加载房屋的所有事件数据 - 仿照gurobi方式"""
        current_dir = os.getcwd()
        while not os.path.exists(os.path.join(current_dir, "output", "02_event_segments")):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
            current_dir = parent_dir

        events_file = os.path.join(current_dir, "output", "02_event_segments", house_id, f"02_appliance_event_segments_id_{house_id}.csv")

        if not os.path.exists(events_file):
            raise FileNotFoundError(f"事件数据文件不存在: {events_file}")

        events_df = pd.read_csv(events_file)
        events_df['start_time'] = pd.to_datetime(events_df['start_time'])
        events_df['end_time'] = pd.to_datetime(events_df['end_time'])

        return events_df

    def calculate_complete_costs(self, house_id: str, tariff_type: str, optimization_results: List[Dict]) -> Dict:
        """计算完整的费用（所有事件） - 仿照gurobi方式"""
        logger.info(f"开始计算完整费用: {house_id} ({tariff_type})")

        try:
            # 加载数据
            power_df = self.optimizer.load_power_data(house_id)
            all_events_df = self.load_all_events(house_id)

            # 创建优化结果映射
            optimization_map = {}
            for opt_result in optimization_results:
                optimization_map[opt_result['event_id']] = opt_result

            # 计算所有事件的费用
            all_event_costs = []
            total_original_cost = 0.0
            total_optimized_cost = 0.0

            processed_events = 0
            failed_events = 0

            for idx, event in all_events_df.iterrows():
                try:
                    # 获取功率曲线
                    power_profile = self.optimizer.get_event_power_profile(event, power_df)

                    if not power_profile:
                        failed_events += 1
                        continue

                    # 计算原始成本
                    original_cost = self.optimizer.calculate_event_cost(power_profile, tariff_type)
                    total_original_cost += original_cost

                    # 检查是否有优化结果（只有编号最小的事件才会被优化）
                    event_id = event['event_id']
                    if event_id in optimization_map:
                        # 第一事件：使用优化后的成本
                        opt_result = optimization_map[event_id]
                        optimized_cost = opt_result['optimized_cost']
                        is_optimized = True
                        optimized_start = opt_result['optimized_start_time']
                        optimized_end = opt_result['optimized_end_time']
                        cost_savings = original_cost - optimized_cost
                        savings_percentage = (cost_savings / original_cost * 100) if original_cost > 0 else 0
                        event_type = "first_event_optimized"
                    else:
                        # 其他事件：成本不变
                        optimized_cost = original_cost
                        is_optimized = False
                        optimized_start = event['start_time']
                        optimized_end = event['end_time']
                        cost_savings = 0.0
                        savings_percentage = 0.0

                        # 判断事件类型
                        if event['is_reschedulable']:
                            event_type = "reschedulable_not_optimized"
                        else:
                            event_type = "non_reschedulable"

                    total_optimized_cost += optimized_cost

                    # 处理列名差异：全事件数据用appliance_ID，过滤数据用appliance_id
                    appliance_id_value = event.get('appliance_ID', event.get('appliance_id', 'Unknown'))

                    all_event_costs.append({
                        'event_id': event['event_id'],
                        'appliance_name': event['appliance_name'],
                        'appliance_id': appliance_id_value,
                        'is_reschedulable': event['is_reschedulable'],
                        'is_optimized': is_optimized,
                        'event_type': event_type,
                        'original_start_time': event['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'original_end_time': event['end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'optimized_start_time': optimized_start.strftime('%Y-%m-%d %H:%M:%S'),
                        'optimized_end_time': optimized_end.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration_minutes': event['duration(min)'],
                        'original_cost': original_cost,
                        'optimized_cost': optimized_cost,
                        'cost_savings': cost_savings,
                        'savings_percentage': savings_percentage,
                        'power_profile_points': len(power_profile)
                    })

                    processed_events += 1

                except Exception as e:
                    logger.warning(f"处理事件 {event['event_id']} 时出错: {e}")
                    failed_events += 1
                    continue

            # 计算总体统计
            total_savings = total_original_cost - total_optimized_cost
            overall_savings_percentage = (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0

            result = {
                'house_id': house_id,
                'tariff_type': tariff_type,
                'total_events': len(all_event_costs),
                'optimized_events': len([e for e in all_event_costs if e['is_optimized']]),
                'total_original_cost': total_original_cost,
                'total_optimized_cost': total_optimized_cost,
                'total_savings': total_savings,
                'overall_savings_percentage': overall_savings_percentage,
                'all_event_costs': all_event_costs
            }

            return result

        except Exception as e:
            logger.error(f"计算完整费用时出错: {e}")
            return None

    def save_results_gurobi_style(self, optimization_results: List[Dict], complete_result: Dict, house_id: str, tariff_type: str):
        """仿照gurobi格式保存结果"""
        # 创建结果目录 - 修正为outputs（复数）
        results_dir = os.path.join("outputs", tariff_type, house_id)
        os.makedirs(results_dir, exist_ok=True)

        # 1. 保存优化结果CSV (仿照gurobi格式)
        csv_data = []
        for result in optimization_results:
            csv_data.append({
                'event_id': result['event_id'],
                'appliance_name': result['appliance_name'],
                'appliance_id': result['appliance_id'],
                'original_start_time': result['original_start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'original_end_time': result['original_end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'optimized_start_time': result['optimized_start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'optimized_end_time': result['optimized_end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': result['duration_minutes'],
                'original_cost': result['original_cost'],
                'optimized_cost': result['optimized_cost'],
                'cost_savings': result['cost_savings'],
                'savings_percentage': result['savings_percentage'],
                'is_shifted': result['is_shifted']
            })

        csv_file = os.path.join(results_dir, f"optimization_results_{house_id}_{tariff_type}.csv")
        csv_df = pd.DataFrame(csv_data)
        csv_df.to_csv(csv_file, index=False)

        # 2. 保存详细的所有事件费用CSV (仿照gurobi格式)
        csv_data = complete_result['all_event_costs']
        csv_df = pd.DataFrame(csv_data)
        csv_file = os.path.join(results_dir, f"complete_cost_analysis_{house_id}_{tariff_type}.csv")
        csv_df.to_csv(csv_file, index=False)

        # 3. 保存汇总统计JSON (仿照gurobi格式)
        summary = {k: v for k, v in complete_result.items() if k != 'all_event_costs'}
        summary['processing_timestamp'] = datetime.now().isoformat()

        json_file = os.path.join(results_dir, f"cost_summary_{house_id}_{tariff_type}.json")
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"    结果已保存到: {results_dir} (仿照gurobi格式)")

    def save_optimization_results_only(self, optimization_results: List[Dict], house_id: str, tariff_type: str):
        """只保存优化结果，不计算费用"""
        # 创建结果目录 - 保存到指定路径
        results_dir = os.path.join("/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results", tariff_type, house_id)
        os.makedirs(results_dir, exist_ok=True)

        # 保存优化结果CSV
        csv_file = os.path.join(results_dir, f"optimization_results_{house_id}_{tariff_type}.csv")
        results_df = pd.DataFrame(optimization_results)
        results_df.to_csv(csv_file, index=False)

        # 保存简单的汇总JSON
        summary = {
            'house_id': house_id,
            'tariff_type': tariff_type,
            'total_optimized_events': len(optimization_results),
            'optimization_timestamp': datetime.now().isoformat()
        }

        json_file = os.path.join(results_dir, f"optimization_summary_{house_id}_{tariff_type}.json")
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"    优化结果已保存到: {results_dir}")

    def process_single_house(self, house_id: str, tariff_type: str, data_dir: str) -> Dict:
        """处理单个house - 只进行事件迁移，不计算费用"""
        house_start_time = time.time()
        logger.info(f"🚀 开始处理: {house_id} ({tariff_type}) - 开始时间: {datetime.now().strftime('%H:%M:%S')}")

        try:
            # 运行第一事件优化（事件迁移）
            csv_file = os.path.join(data_dir, tariff_type, house_id, f"tou_filtered_{house_id}_{tariff_type}.csv")

            logger.info(f"  步骤: 第一事件优化（事件迁移）...")
            optimization_start_time = time.time()
            optimization_result = self.optimizer.optimize_single_file(csv_file, house_id, tariff_type)
            optimization_time = time.time() - optimization_start_time

            if optimization_result["status"] != "success":
                logger.error(f"  第一事件优化失败: {optimization_result['status']}")
                return {"status": "optimization_failed", "house_id": house_id, "tariff_type": tariff_type}

            # 保存结果到指定目录结构
            logger.info(f"  步骤: 保存结果...")
            save_start_time = time.time()
            self.save_optimization_results_only(optimization_result['optimization_results'], house_id, tariff_type)
            save_time = time.time() - save_start_time

            # 计算总处理时间
            total_processing_time = time.time() - house_start_time

            optimized_count = len(optimization_result['optimization_results'])
            logger.info(f"  ✅ {house_id} 处理完成: {optimized_count} 个事件已迁移")
            logger.info(f"  ⏱️ 时间: 优化 {optimization_time:.1f}s, 保存 {save_time:.1f}s, 总计 {total_processing_time:.1f}s")

            return {
                "status": "success",
                "house_id": house_id,
                "tariff_type": tariff_type,
                "optimized_events": optimized_count,
                "processing_time": total_processing_time
            }

        except Exception as e:
            logger.error(f"处理 {house_id} 时出错: {e}")
            return {"status": "error", "house_id": house_id, "tariff_type": tariff_type, "error": str(e)}

    def run_batch_processing(self, data_dir: str):
        """运行批量处理"""
        logger.info("🚀 开始基于规则的批量优化处理")

        # 获取所有house
        houses = self.get_all_houses(data_dir)

        all_results = []
        batch_start_time = time.time()

        # 按tariff类型处理
        for tariff_type in ["Economy_7", "Economy_10"]:
            if not houses[tariff_type]:
                logger.info(f"跳过 {tariff_type}: 没有找到house")
                continue

            logger.info(f"\n📊 开始处理 {tariff_type} ({len(houses[tariff_type])} houses)")
            tariff_start_time = time.time()

            for house_id in houses[tariff_type]:
                result = self.process_single_house(house_id, tariff_type, data_dir)
                all_results.append(result)

            tariff_time = time.time() - tariff_start_time
            logger.info(f"✅ {tariff_type} 处理完成，耗时: {tariff_time//60:.0f}m {tariff_time%60:.1f}s")

        total_batch_time = time.time() - batch_start_time

        # 统计结果
        successful_results = [r for r in all_results if r["status"] == "success"]
        failed_results = [r for r in all_results if r["status"] != "success"]

        logger.info(f"\n🎉 批量处理完成!")
        logger.info(f"  成功: {len(successful_results)} houses")
        logger.info(f"  失败: {len(failed_results)} houses")
        logger.info(f"  总耗时: {total_batch_time//3600:.0f}h {(total_batch_time%3600)//60:.0f}m {total_batch_time%60:.1f}s")

        if successful_results:
            total_optimized_events = sum(r["optimized_events"] for r in successful_results)
            logger.info(f"  总优化事件数: {total_optimized_events}")
            logger.info(f"  平均每个house优化事件数: {total_optimized_events/len(successful_results):.1f}")

def main():
    """主函数"""
    # 配置路径
    tariff_config_path = "../../../config/tariff_config.json"
    data_dir = "../flterted_data"

    # 创建处理器并运行完整批量处理
    processor = RuleBasedProcessor(tariff_config_path)
    processor.run_batch_processing(data_dir)

if __name__ == "__main__":
    main()