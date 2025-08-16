#!/usr/bin/env python3
"""
时间不确定性扰动实验数据生成器
对所有可迁移事件的开始和结束时间加入±5分钟的随机偏移
同时更新相关的价格水平和优化潜力字段
"""

import os
import pandas as pd
import numpy as np
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import ast

class TimingUncertaintyGenerator:
    def __init__(self):
        self.base_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties"
        self.original_data_dir = os.path.join(self.base_dir, "Original_data/UK")
        self.error_data_dir = os.path.join(self.base_dir, "Error_data/UK")
        
        # 目标房屋和电价类型
        self.target_houses = ["house1", "house2", "house3", "house20", "house21"]
        self.tariff_types = ["Economy_7", "Economy_10"]
        
        # 时间扰动参数
        self.max_time_offset = 5  # ±5分钟
        
        # 电价时段定义
        self.tariff_schedules = {
            "Economy_7": {
                "low_price_periods": [("00:30", "07:30")],
                "description": "Economy 7 - Low price: 00:30-07:30"
            },
            "Economy_10": {
                "low_price_periods": [("01:00", "06:00"), ("13:00", "16:00"), ("20:00", "22:00")],
                "description": "Economy 10 - Low price: 01:00-06:00, 13:00-16:00, 20:00-22:00"
            }
        }
        
        # 设置随机种子以确保可重现性
        random.seed(42)
        np.random.seed(42)
        
        # 扰动日志
        self.perturbation_log = {}
    
    def time_to_minutes(self, time_str):
        """将时间字符串转换为分钟数（从00:00开始）"""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.hour * 60 + time_obj.minute
        except:
            return 0
    
    def minutes_to_time(self, minutes):
        """将分钟数转换为时间字符串"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    def is_in_low_price_period(self, time_str, tariff_type):
        """检查时间是否在低价时段"""
        time_minutes = self.time_to_minutes(time_str)
        
        for start_str, end_str in self.tariff_schedules[tariff_type]["low_price_periods"]:
            start_minutes = self.time_to_minutes(start_str)
            end_minutes = self.time_to_minutes(end_str)
            
            # 处理跨天的情况
            if start_minutes <= end_minutes:
                if start_minutes <= time_minutes <= end_minutes:
                    return True
            else:  # 跨天情况
                if time_minutes >= start_minutes or time_minutes <= end_minutes:
                    return True
        
        return False
    
    def get_price_level(self, time_str, tariff_type):
        """获取时间点的价格水平 (0=低价, 1=高价)"""
        return 0 if self.is_in_low_price_period(time_str, tariff_type) else 1
    
    def calculate_price_profile(self, start_time, end_time, tariff_type):
        """计算事件的价格水平分布"""
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        # 按分钟计算价格水平
        current_time = start_dt
        price_levels = []
        
        while current_time < end_dt:
            time_str = current_time.strftime("%H:%M")
            price_level = self.get_price_level(time_str, tariff_type)
            price_levels.append(price_level)
            current_time += timedelta(minutes=1)
        
        # 统计价格水平分布
        low_price_minutes = price_levels.count(0)
        high_price_minutes = price_levels.count(1)
        
        # 构建价格分布字典
        price_profile = {
            "0": low_price_minutes,
            "1": high_price_minutes
        }
        
        # 计算主要价格水平（占用时间更多的价格水平）
        primary_price_level = 0 if low_price_minutes >= high_price_minutes else 1
        
        # 获取开始和结束时间的价格水平
        start_price_level = self.get_price_level(start_dt.strftime("%H:%M"), tariff_type)
        end_price_level = self.get_price_level(end_dt.strftime("%H:%M"), tariff_type)
        
        # 计算优化潜力（低价时段占比）
        total_minutes = low_price_minutes + high_price_minutes
        optimization_potential = low_price_minutes / total_minutes if total_minutes > 0 else 0.0
        
        return price_profile, primary_price_level, start_price_level, end_price_level, optimization_potential
    
    def apply_timing_perturbation(self, start_time, end_time, duration_min):
        """对事件时间应用±5分钟的随机扰动"""
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        # 生成±5分钟的随机偏移
        start_offset = random.randint(-self.max_time_offset, self.max_time_offset)
        end_offset = random.randint(-self.max_time_offset, self.max_time_offset)
        
        # 应用偏移
        new_start_dt = start_dt + timedelta(minutes=start_offset)
        new_end_dt = end_dt + timedelta(minutes=end_offset)
        
        # 确保持续时间合理（允许轻微变化）
        actual_duration = (new_end_dt - new_start_dt).total_seconds() / 60
        
        # 如果持续时间变化过大，调整结束时间
        if abs(actual_duration - duration_min) > 3:  # 允许±3分钟的持续时间变化
            new_end_dt = new_start_dt + timedelta(minutes=duration_min)
        
        # 确保时间不会跨到前一天或后一天
        if new_start_dt.date() != start_dt.date():
            new_start_dt = start_dt.replace(hour=0, minute=0, second=0)
        
        if new_end_dt.date() != end_dt.date():
            new_end_dt = end_dt.replace(hour=23, minute=59, second=0)
        
        new_start_time = new_start_dt.strftime("%Y-%m-%d %H:%M:%S")
        new_end_time = new_end_dt.strftime("%Y-%m-%d %H:%M:%S")
        new_duration = (new_end_dt - new_start_dt).total_seconds() / 60
        
        return new_start_time, new_end_time, new_duration, start_offset, end_offset
    
    def process_house_data(self, tariff_type, house_id):
        """处理单个房屋的数据"""
        print(f"  🏠 处理 {house_id}...")
        
        # 输入文件路径
        input_file = os.path.join(
            self.original_data_dir, 
            tariff_type, 
            house_id, 
            f"tou_filtered_{house_id}_{tariff_type}.csv"
        )
        
        # 输出目录和文件路径
        output_dir = os.path.join(self.error_data_dir, tariff_type, house_id)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"tou_filtered_{house_id}_{tariff_type}.csv")
        
        if not os.path.exists(input_file):
            print(f"    ⚠️ 输入文件不存在: {input_file}")
            return
        
        # 读取原始数据
        try:
            df = pd.read_csv(input_file)
            print(f"    📊 读取 {len(df)} 个事件")
        except Exception as e:
            print(f"    ❌ 读取文件失败: {e}")
            return
        
        # 初始化扰动统计
        house_log = {
            "total_events": len(df),
            "reschedulable_events": 0,
            "perturbed_events": 0,
            "perturbations": []
        }
        
        # 处理每个事件
        for idx, row in df.iterrows():
            # 只对可重新调度的事件应用扰动
            if row['is_reschedulable'] == True:
                house_log["reschedulable_events"] += 1
                
                # 应用时间扰动
                new_start, new_end, new_duration, start_offset, end_offset = self.apply_timing_perturbation(
                    row['start_time'], row['end_time'], row['duration(min)']
                )
                
                # 重新计算价格相关字段
                price_profile, primary_price, start_price, end_price, opt_potential = self.calculate_price_profile(
                    new_start, new_end, tariff_type
                )
                
                # 更新数据
                df.at[idx, 'start_time'] = new_start
                df.at[idx, 'end_time'] = new_end
                df.at[idx, 'duration(min)'] = new_duration
                df.at[idx, 'price_level_profile'] = json.dumps(price_profile)
                df.at[idx, 'primary_price_level'] = primary_price
                df.at[idx, 'start_price_level'] = start_price
                df.at[idx, 'end_price_level'] = end_price
                df.at[idx, 'optimization_potential'] = opt_potential
                
                # 记录扰动
                house_log["perturbations"].append({
                    "event_id": row['event_id'],
                    "appliance_name": row['appliance_name'],
                    "original_start": row['start_time'],
                    "original_end": row['end_time'],
                    "new_start": new_start,
                    "new_end": new_end,
                    "start_offset_min": start_offset,
                    "end_offset_min": end_offset,
                    "duration_change": new_duration - row['duration(min)']
                })
                
                house_log["perturbed_events"] += 1
        
        # 保存扰动后的数据
        try:
            df.to_csv(output_file, index=False)
            print(f"    ✅ 保存扰动数据: {output_file}")
            print(f"    📈 扰动统计: {house_log['perturbed_events']}/{house_log['reschedulable_events']} 可调度事件被扰动")
        except Exception as e:
            print(f"    ❌ 保存文件失败: {e}")
            return
        
        # 记录到总日志
        if tariff_type not in self.perturbation_log:
            self.perturbation_log[tariff_type] = {}
        self.perturbation_log[tariff_type][house_id] = house_log
    
    def generate_timing_uncertainties(self):
        """生成所有房屋的时间不确定性数据"""
        print("🚀 开始生成时间不确定性扰动数据...")
        print("="*80)
        print(f"📋 扰动参数: ±{self.max_time_offset}分钟随机偏移")
        print(f"🏠 目标房屋: {', '.join(self.target_houses)}")
        print(f"💰 电价类型: {', '.join(self.tariff_types)}")
        print()
        
        # 确保输出目录存在
        os.makedirs(self.error_data_dir, exist_ok=True)
        
        # 处理每种电价类型
        for tariff_type in self.tariff_types:
            print(f"💰 处理 {tariff_type}:")
            print(f"   {self.tariff_schedules[tariff_type]['description']}")
            
            # 处理每个房屋
            for house_id in self.target_houses:
                self.process_house_data(tariff_type, house_id)
            
            print()
        
        # 保存扰动日志
        log_file = os.path.join(self.error_data_dir, "timing_perturbation_log.json")
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.perturbation_log, f, indent=2, ensure_ascii=False, default=str)
            print(f"📁 扰动日志已保存: {log_file}")
        except Exception as e:
            print(f"❌ 保存日志失败: {e}")
        
        # 生成扰动统计报告
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """生成扰动统计报告"""
        print("\n📊 时间不确定性扰动统计报告:")
        print("="*80)
        
        total_events = 0
        total_reschedulable = 0
        total_perturbed = 0
        
        for tariff_type in self.tariff_types:
            print(f"\n💰 {tariff_type}:")
            print("-"*60)
            
            tariff_events = 0
            tariff_reschedulable = 0
            tariff_perturbed = 0
            
            for house_id in self.target_houses:
                if tariff_type in self.perturbation_log and house_id in self.perturbation_log[tariff_type]:
                    house_data = self.perturbation_log[tariff_type][house_id]
                    
                    events = house_data['total_events']
                    reschedulable = house_data['reschedulable_events']
                    perturbed = house_data['perturbed_events']
                    
                    print(f"   🏠 {house_id}: {perturbed}/{reschedulable} 事件扰动 (总事件: {events})")
                    
                    tariff_events += events
                    tariff_reschedulable += reschedulable
                    tariff_perturbed += perturbed
            
            print(f"   📈 {tariff_type} 汇总: {tariff_perturbed}/{tariff_reschedulable} 事件扰动 (总事件: {tariff_events})")
            
            total_events += tariff_events
            total_reschedulable += tariff_reschedulable
            total_perturbed += tariff_perturbed
        
        print(f"\n🏆 总体统计:")
        print(f"   总事件数: {total_events}")
        print(f"   可调度事件数: {total_reschedulable}")
        print(f"   扰动事件数: {total_perturbed}")
        print(f"   扰动率: {total_perturbed/total_reschedulable*100:.1f}%" if total_reschedulable > 0 else "   扰动率: 0%")
        print(f"   时间偏移范围: ±{self.max_time_offset}分钟")

def main():
    """主函数"""
    generator = TimingUncertaintyGenerator()
    
    try:
        generator.generate_timing_uncertainties()
        print("\n✅ 时间不确定性扰动数据生成完成！")
        return True
    except Exception as e:
        print(f"\n❌ 生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
