#!/usr/bin/env python3
"""
监控计算进度并生成最终的费用汇总表格
"""

import time
import os
import json
import subprocess
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_completion_status():
    """检查所有计算是否完成"""
    results_path = "/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results"
    
    status = {
        'Economy_7': {'shifted': 0, 'unshifted': 0, 'total': 19},
        'Economy_10': {'shifted': 0, 'unshifted': 0, 'total': 19}
    }
    
    for tariff_type in ['Economy_7', 'Economy_10']:
        tariff_dir = f"{results_path}/{tariff_type}"
        if os.path.exists(tariff_dir):
            for i in range(1, 21):  # house1 to house20
                house_dir = f"{tariff_dir}/house{i}"
                if os.path.exists(house_dir):
                    # 检查已迁移事件文件
                    shifted_file = f"{house_dir}/cost_calculation_summary_house{i}_{tariff_type}.json"
                    if os.path.exists(shifted_file):
                        status[tariff_type]['shifted'] += 1
                    
                    # 检查未迁移事件文件
                    unshifted_file = f"{house_dir}/unshifted_events_cost_summary_house{i}_{tariff_type}.json"
                    if os.path.exists(unshifted_file):
                        status[tariff_type]['unshifted'] += 1
    
    return status

def generate_final_table():
    """生成最终的费用汇总表格"""
    try:
        logger.info("生成最终费用汇总表格...")
        result = subprocess.run(
            ['python', 'generate_cost_summary_table.py'],
            cwd='/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based',
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("费用汇总表格生成成功")
            print(result.stdout)
            return True
        else:
            logger.error(f"费用汇总表格生成失败: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"生成费用汇总表格时出错: {e}")
        return False

def main():
    """主监控循环"""
    logger.info("开始监控计算进度...")
    
    last_status = None
    check_interval = 30  # 30秒检查一次
    
    while True:
        status = check_completion_status()
        
        # 如果状态发生变化，打印更新
        if status != last_status:
            logger.info("=== 计算进度更新 ===")
            for tariff_type in ['Economy_7', 'Economy_10']:
                shifted_progress = f"{status[tariff_type]['shifted']}/{status[tariff_type]['total']}"
                unshifted_progress = f"{status[tariff_type]['unshifted']}/{status[tariff_type]['total']}"
                logger.info(f"{tariff_type}:")
                logger.info(f"  已迁移事件: {shifted_progress}")
                logger.info(f"  未迁移事件: {unshifted_progress}")
            
            last_status = status.copy()
        
        # 检查是否全部完成
        all_complete = True
        for tariff_type in ['Economy_7', 'Economy_10']:
            if (status[tariff_type]['shifted'] < status[tariff_type]['total'] or 
                status[tariff_type]['unshifted'] < status[tariff_type]['total']):
                all_complete = False
                break
        
        if all_complete:
            logger.info("🎉 所有计算已完成！")
            logger.info("正在生成最终费用汇总表格...")
            
            # 等待一下确保文件写入完成
            time.sleep(5)
            
            # 生成最终表格
            if generate_final_table():
                logger.info("✅ 最终费用汇总表格已生成完成！")
                break
            else:
                logger.error("❌ 费用汇总表格生成失败，请手动运行 generate_cost_summary_table.py")
                break
        
        # 等待下次检查
        time.sleep(check_interval)

if __name__ == "__main__":
    main()
