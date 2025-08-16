#!/usr/bin/env python3
"""
批量处理所有家庭的完整费用计算
按Economy_7和Economy_10分别处理，结果保存到./results/目录
"""

import pandas as pd
import json
import os
import glob
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from cost_calculator import CompleteCostCalculator
from gurobi_optimizer import CorrectedOptimizationSystem

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, tariff_config_path: str):
        """
        初始化批量处理器
        
        Args:
            tariff_config_path: 电价配置文件路径
        """
        self.optimizer = CorrectedOptimizationSystem(tariff_config_path)
        self.calculator = CompleteCostCalculator(tariff_config_path)
        
        logger.info("批量处理器初始化完成")
    
    def get_all_houses(self, data_dir: str) -> Dict[str, List[str]]:
        """获取所有house的列表"""
        houses = {"Economy_7": [], "Economy_10": []}
        
        for tariff_type in ["Economy_7", "Economy_10"]:
            tariff_dir = os.path.join(data_dir, tariff_type)
            if not os.path.exists(tariff_dir):
                continue
            
            house_dirs = glob.glob(os.path.join(tariff_dir, "house*"))
            for house_dir in house_dirs:
                house_id = os.path.basename(house_dir)
                csv_file = os.path.join(house_dir, f"tou_filtered_{house_id}_{tariff_type}.csv")
                
                if os.path.exists(csv_file):
                    houses[tariff_type].append(house_id)
        
        logger.info(f"找到的house数量:")
        logger.info(f"  Economy_7: {len(houses['Economy_7'])} 个")
        logger.info(f"  Economy_10: {len(houses['Economy_10'])} 个")
        
        return houses
    
    def process_single_house(self, house_id: str, tariff_type: str, data_dir: str) -> Dict:
        """处理单个house"""
        house_start_time = time.time()
        logger.info(f"开始处理: {house_id} ({tariff_type})")

        try:
            # 步骤1: 运行Gurobi优化
            csv_file = os.path.join(data_dir, tariff_type, house_id, f"tou_filtered_{house_id}_{tariff_type}.csv")

            logger.info(f"  步骤1: Gurobi优化...")
            optimization_start_time = time.time()
            optimization_result = self.optimizer.optimize_single_file(csv_file, house_id, tariff_type)
            optimization_time = time.time() - optimization_start_time

            if optimization_result["status"] != "success":
                logger.error(f"  Gurobi优化失败: {optimization_result['status']}")
                return {"status": "optimization_failed", "house_id": house_id, "tariff_type": tariff_type}

            # 步骤2: 计算完整费用
            logger.info(f"  步骤2: 完整费用计算...")
            cost_calculation_start_time = time.time()
            complete_result = self.calculator.calculate_complete_costs(house_id, tariff_type)
            cost_calculation_time = time.time() - cost_calculation_start_time

            if complete_result is None:
                logger.error(f"  完整费用计算失败")
                return {"status": "cost_calculation_failed", "house_id": house_id, "tariff_type": tariff_type}

            # 步骤3: 保存到指定目录
            logger.info(f"  步骤3: 保存结果...")
            save_start_time = time.time()
            self.save_to_results_directory(complete_result, house_id, tariff_type)
            save_time = time.time() - save_start_time

            # 计算总处理时间
            total_processing_time = time.time() - house_start_time

            # 时间统计
            timing_stats = {
                "optimization_time_seconds": round(optimization_time, 2),
                "cost_calculation_time_seconds": round(cost_calculation_time, 2),
                "save_time_seconds": round(save_time, 2),
                "total_processing_time_seconds": round(total_processing_time, 2),
                "optimization_time_formatted": f"{optimization_time//60:.0f}m {optimization_time%60:.1f}s",
                "cost_calculation_time_formatted": f"{cost_calculation_time//60:.0f}m {cost_calculation_time%60:.1f}s",
                "save_time_formatted": f"{save_time//60:.0f}m {save_time%60:.1f}s",
                "total_processing_time_formatted": f"{total_processing_time//60:.0f}m {total_processing_time%60:.1f}s"
            }

            logger.info(f"  ✅ {house_id} 处理完成: 总节约 ${complete_result['total_savings']:.2f} ({complete_result['overall_savings_percentage']:.2f}%)")
            logger.info(f"  ⏱️ 时间统计:")
            logger.info(f"     - 优化调度: {timing_stats['optimization_time_formatted']}")
            logger.info(f"     - 费用计算: {timing_stats['cost_calculation_time_formatted']}")
            logger.info(f"     - 保存结果: {timing_stats['save_time_formatted']}")
            logger.info(f"     - 总计时间: {timing_stats['total_processing_time_formatted']}")
            
            return {
                "status": "success",
                "house_id": house_id,
                "tariff_type": tariff_type,
                "total_events": complete_result['total_events'],
                "total_original_cost": complete_result['total_original_cost'],
                "total_optimized_cost": complete_result['total_optimized_cost'],
                "total_savings": complete_result['total_savings'],
                "overall_savings_percentage": complete_result['overall_savings_percentage'],
                "reschedulable_events": complete_result['reschedulable_events'],
                "optimized_events": complete_result['optimized_events'],
                "timing_stats": timing_stats
            }
            
        except Exception as e:
            logger.error(f"  处理 {house_id} 时出错: {e}")
            return {"status": "error", "house_id": house_id, "tariff_type": tariff_type, "error": str(e)}
    
    def save_to_results_directory(self, complete_result: Dict, house_id: str, tariff_type: str):
        """保存结果到./results/目录"""
        # 创建结果目录
        results_dir = os.path.join("results", tariff_type, house_id)
        os.makedirs(results_dir, exist_ok=True)
        
        # 保存详细的所有事件费用CSV
        csv_data = complete_result['all_event_costs']
        csv_df = pd.DataFrame(csv_data)
        csv_file = os.path.join(results_dir, f"complete_cost_analysis_{house_id}_{tariff_type}.csv")
        csv_df.to_csv(csv_file, index=False)
        
        # 保存汇总统计JSON
        summary = {k: v for k, v in complete_result.items() if k != 'all_event_costs'}
        summary['processing_timestamp'] = datetime.now().isoformat()
        
        json_file = os.path.join(results_dir, f"cost_summary_{house_id}_{tariff_type}.json")
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"    结果已保存到: {results_dir}")
    
    def process_all_houses(self, data_dir: str):
        """处理所有house"""
        batch_start_time = time.time()
        logger.info("开始批量处理所有house...")

        # 获取所有house列表
        all_houses = self.get_all_houses(data_dir)

        # 处理结果统计
        all_results = []
        tariff_timing = {}

        # 处理Economy_7
        logger.info(f"\n🔵 开始处理 Economy_7 ({len(all_houses['Economy_7'])} 个house)")
        e7_start_time = time.time()
        for i, house_id in enumerate(all_houses['Economy_7']):
            logger.info(f"  进度: {i+1}/{len(all_houses['Economy_7'])}")
            result = self.process_single_house(house_id, "Economy_7", data_dir)
            all_results.append(result)
        e7_time = time.time() - e7_start_time
        tariff_timing["Economy_7"] = {
            "time_seconds": round(e7_time, 2),
            "time_formatted": f"{e7_time//3600:.0f}h {(e7_time%3600)//60:.0f}m {e7_time%60:.1f}s",
            "houses_count": len(all_houses["Economy_7"]),
            "avg_time_per_house": round(e7_time / len(all_houses["Economy_7"]), 2) if all_houses["Economy_7"] else 0
        }

        # 处理Economy_10
        logger.info(f"\n🟢 开始处理 Economy_10 ({len(all_houses['Economy_10'])} 个house)")
        e10_start_time = time.time()
        for i, house_id in enumerate(all_houses['Economy_10']):
            logger.info(f"  进度: {i+1}/{len(all_houses['Economy_10'])}")
            result = self.process_single_house(house_id, "Economy_10", data_dir)
            all_results.append(result)
        e10_time = time.time() - e10_start_time
        tariff_timing["Economy_10"] = {
            "time_seconds": round(e10_time, 2),
            "time_formatted": f"{e10_time//3600:.0f}h {(e10_time%3600)//60:.0f}m {e10_time%60:.1f}s",
            "houses_count": len(all_houses["Economy_10"]),
            "avg_time_per_house": round(e10_time / len(all_houses["Economy_10"]), 2) if all_houses["Economy_10"] else 0
        }

        # 计算总时间
        total_batch_time = time.time() - batch_start_time

        # 保存总体统计
        self.save_overall_statistics(all_results, tariff_timing, total_batch_time)

        # 显示时间统计
        logger.info("\n⏱️ 批量处理时间统计:")
        logger.info(f"  Economy_7: {tariff_timing['Economy_7']['time_formatted']} (平均 {tariff_timing['Economy_7']['avg_time_per_house']:.1f}s/house)")
        logger.info(f"  Economy_10: {tariff_timing['Economy_10']['time_formatted']} (平均 {tariff_timing['Economy_10']['avg_time_per_house']:.1f}s/house)")
        logger.info(f"  总计时间: {total_batch_time//3600:.0f}h {(total_batch_time%3600)//60:.0f}m {total_batch_time%60:.1f}s")

        logger.info("🎉 所有house处理完成!")
    
    def save_overall_statistics(self, all_results: List[Dict], tariff_timing: Dict, total_batch_time: float):
        """保存总体统计"""
        logger.info("保存总体统计...")

        # 分类统计
        successful_results = [r for r in all_results if r["status"] == "success"]

        economy_7_results = [r for r in successful_results if r["tariff_type"] == "Economy_7"]
        economy_10_results = [r for r in successful_results if r["tariff_type"] == "Economy_10"]
        
        # 计算统计数据
        def calculate_stats(results, tariff_name):
            if not results:
                return None
            
            return {
                "tariff_type": tariff_name,
                "total_houses": len(results),
                "total_events": sum(r["total_events"] for r in results),
                "total_reschedulable_events": sum(r["reschedulable_events"] for r in results),
                "total_optimized_events": sum(r["optimized_events"] for r in results),
                "total_original_cost": sum(r["total_original_cost"] for r in results),
                "total_optimized_cost": sum(r["total_optimized_cost"] for r in results),
                "total_savings": sum(r["total_savings"] for r in results),
                "average_savings_percentage": sum(r["overall_savings_percentage"] for r in results) / len(results),
                "min_savings_percentage": min(r["overall_savings_percentage"] for r in results),
                "max_savings_percentage": max(r["overall_savings_percentage"] for r in results)
            }
        
        # 生成统计报告
        overall_stats = {
            "processing_timestamp": datetime.now().isoformat(),
            "total_houses_processed": len(all_results),
            "successful_houses": len(successful_results),
            "failed_houses": len(all_results) - len(successful_results),
            "economy_7_stats": calculate_stats(economy_7_results, "Economy_7"),
            "economy_10_stats": calculate_stats(economy_10_results, "Economy_10"),
            "timing_statistics": {
                "total_batch_time_seconds": round(total_batch_time, 2),
                "total_batch_time_formatted": f"{total_batch_time//3600:.0f}h {(total_batch_time%3600)//60:.0f}m {total_batch_time%60:.1f}s",
                "tariff_timing": tariff_timing
            },
            "detailed_results": all_results
        }
        
        # 保存总体统计
        os.makedirs("results", exist_ok=True)
        
        # JSON格式
        json_file = "results/overall_statistics.json"
        with open(json_file, 'w') as f:
            json.dump(overall_stats, f, indent=2)
        
        # CSV格式（简化版）
        csv_data = []
        for result in successful_results:
            row_data = {
                "House_ID": result["house_id"],
                "Tariff_Type": result["tariff_type"],
                "Total_Events": result["total_events"],
                "Reschedulable_Events": result["reschedulable_events"],
                "Optimized_Events": result["optimized_events"],
                "Original_Cost": result["total_original_cost"],
                "Optimized_Cost": result["total_optimized_cost"],
                "Total_Savings": result["total_savings"],
                "Savings_Percentage": result["overall_savings_percentage"]
            }

            # 添加时间统计（如果存在）
            if "timing_stats" in result:
                timing = result["timing_stats"]
                row_data.update({
                    "Optimization_Time_Seconds": timing["optimization_time_seconds"],
                    "Cost_Calculation_Time_Seconds": timing["cost_calculation_time_seconds"],
                    "Total_Processing_Time_Seconds": timing["total_processing_time_seconds"]
                })

            csv_data.append(row_data)
        
        csv_df = pd.DataFrame(csv_data)
        csv_file = "results/overall_summary.csv"
        csv_df.to_csv(csv_file, index=False)
        
        logger.info(f"总体统计已保存:")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"  CSV: {csv_file}")
        
        # 打印汇总信息
        if overall_stats["economy_7_stats"]:
            e7_stats = overall_stats["economy_7_stats"]
            logger.info(f"\n📊 Economy_7 汇总:")
            logger.info(f"  处理house数: {e7_stats['total_houses']}")
            logger.info(f"  总事件数: {e7_stats['total_events']:,}")
            logger.info(f"  总节约: ${e7_stats['total_savings']:.2f}")
            logger.info(f"  平均节约率: {e7_stats['average_savings_percentage']:.2f}%")
        
        if overall_stats["economy_10_stats"]:
            e10_stats = overall_stats["economy_10_stats"]
            logger.info(f"\n📊 Economy_10 汇总:")
            logger.info(f"  处理house数: {e10_stats['total_houses']}")
            logger.info(f"  总事件数: {e10_stats['total_events']:,}")
            logger.info(f"  总节约: ${e10_stats['total_savings']:.2f}")
            logger.info(f"  平均节约率: {e10_stats['average_savings_percentage']:.2f}%")


def main():
    """主函数"""
    print("🚀 批量处理所有家庭的完整费用计算")
    print("=" * 80)
    
    # 配置路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tariff_config = os.path.join(base_dir, "tariff_config.json")
    data_dir = os.path.join(os.path.dirname(base_dir), "flterted_data")
    
    # 创建批量处理器
    processor = BatchProcessor(tariff_config)
    
    # 处理所有house
    processor.process_all_houses(data_dir)
    
    print("\n🎉 批量处理完成!")
    print("📁 结果保存在 ./results/ 目录下")
    print("   - ./results/Economy_7/house*/")
    print("   - ./results/Economy_10/house*/")
    print("   - ./results/overall_statistics.json")
    print("   - ./results/overall_summary.csv")


if __name__ == "__main__":
    main()
