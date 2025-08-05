import os
import json
import pandas as pd

# 导入工具函数
from Agent_V2.tools.p_042_user_constraints_bak import generate_default_constraints, revise_constraints_by_llm
from tools.p_044_tou_optimization_filter import process_and_mask_events

# 文件路径常量
EVENT_PATH = "./output/02_event_segments/02_appliance_event_segments_id.csv"
CONSTRAINT_PATH = "./output/04_user_constraints/appliance_constraints_revise_by_llm.json"
INTERMEDIATE_PATH = "./output/04_user_constraints/shiftable_event_filtered_by_duration.csv"

def print_event_statistics(df, stage_name):
    """打印事件统计信息"""
    print(f"📊 {stage_name}:")
    print(f"   总事件数: {len(df)}")
    
    if 'is_reschedulable' in df.columns:
        reschedulable = len(df[df['is_reschedulable'] == True])
        print(f"   可重新调度事件数: {reschedulable}")
    
    # 按电器类型统计
    if 'appliance_name' in df.columns:
        shiftable_appliances = ['Washing Machine', 'Tumble Dryer', 'Dishwasher']
        for appliance in shiftable_appliances:
            count = len(df[df['appliance_name'] == appliance])
            if count > 0:
                print(f"   {appliance}: {count} 个事件")

def step1_generate_default_constraints_wrapper():
    """
    步骤1: 生成默认约束
    - 基于appliance_summary.json中的电器列表
    - 为所有电器生成默认约束规则
    - 保存到config/appliance_constraints.json和output/04_user_constraints/appliance_constraints.json
    """
    print("🔧 步骤1: 生成默认电器约束...")
    
    # 检查是否需要生成默认约束
    default_constraint_path = "./output/04_user_constraints/appliance_constraints.json"
    if not os.path.exists(default_constraint_path):
        print("📋 生成默认约束文件...")
        result = generate_default_constraints()
        if result:
            print("✅ 默认约束文件生成完成")
        else:
            print("❌ 默认约束文件生成失败")
            return False
    else:
        print("📋 默认约束文件已存在，跳过生成")
    
    return True

def step2_revise_constraints_by_instruction(user_instruction: str):
    """
    步骤2: 根据用户指令修订约束
    - 调用LLM解析用户自然语言指令
    - 基于默认约束进行修改
    - 只针对Shiftability为Shiftable的电器进行约束修改
    - 保存到appliance_constraints_revise_by_llm.json
    """
    print("🧠 步骤2: 根据用户指令修订约束...")
    print(f"用户指令: {user_instruction}")
    
    # 调用LLM解析用户指令并修订约束
    success = revise_constraints_by_llm(user_instruction)
    
    if success:
        print("✅ 约束已根据用户指令修订")
        return True
    else:
        print("⚠️  LLM约束解析失败，将使用默认约束")
        # 如果LLM失败，复制默认约束作为fallback
        default_path = "./output/04_user_constraints/appliance_constraints.json"
        if os.path.exists(default_path):
            with open(default_path, 'r', encoding='utf-8') as f:
                default_constraints = json.load(f)
            with open(CONSTRAINT_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_constraints, f, indent=2, ensure_ascii=False)
            print("✅ 已使用默认约束作为备选方案")
        return False

def step3_filter_by_min_duration():
    """
    步骤3: 按最小持续时间过滤事件
    - 从02_appliance_event_segments_id.csv中提取Shiftability为Shiftable的事件
    - 所有Shiftable事件的is_reschedulable初始设为True
    - 根据约束中的min_duration对事件进行过滤
    - 将小于最小时间的事件的is_reschedulable改为False
    - 保存到shiftable_event_filtered_by_duration.csv
    """
    print("⏱️  步骤3: 按最小持续时间过滤事件...")
    
    # 强制重新生成：删除旧的中间文件
    if os.path.exists(INTERMEDIATE_PATH):
        os.remove(INTERMEDIATE_PATH)
        print(f"🗑️  删除旧文件: {os.path.basename(INTERMEDIATE_PATH)}")
    
    # 读取事件数据
    if not os.path.exists(EVENT_PATH):
        print(f"❌ 事件文件不存在: {EVENT_PATH}")
        return False
    
    full_df = pd.read_csv(EVENT_PATH, parse_dates=["start_time", "end_time"])
    
    # 提取Shiftability为Shiftable的事件
    shiftable_df = full_df[full_df["Shiftability"] == "Shiftable"].copy()
    
    # 初始化所有Shiftable事件的is_reschedulable为True
    shiftable_df["is_reschedulable"] = True
    
    print(f"📊 提取的可移动电器事件:")
    print(f"   总可移动事件数: {len(shiftable_df)}")
    
    # 读取约束配置
    if not os.path.exists(CONSTRAINT_PATH):
        print(f"❌ 约束文件不存在: {CONSTRAINT_PATH}")
        return False
    
    with open(CONSTRAINT_PATH, "r", encoding="utf-8") as f:
        constraint_dict = json.load(f)

    # 根据min_duration过滤事件
    filtered_count = 0
    for idx, row in shiftable_df.iterrows():
        appliance_name = row["appliance_name"]
        min_duration = constraint_dict.get(appliance_name, {}).get("min_duration", 0)
        
        if row["duration(min)"] <= min_duration:
            shiftable_df.at[idx, "is_reschedulable"] = False
            filtered_count += 1

    # 确保目录存在并保存结果
    os.makedirs(os.path.dirname(INTERMEDIATE_PATH), exist_ok=True)
    shiftable_df.to_csv(INTERMEDIATE_PATH, index=False)
    
    print(f"✅ 持续时间过滤完成:")
    print(f"   过滤掉的短时事件: {filtered_count} 个")
    print(f"   剩余可调度事件: {len(shiftable_df[shiftable_df['is_reschedulable'] == True])} 个")
    print(f"   结果保存到: {os.path.basename(INTERMEDIATE_PATH)}")
    
    print_event_statistics(shiftable_df, "After min_duration filtering")
    return True

def step4_apply_tariff_masks(test_mode=False):
    """
    步骤4: 应用电价掩码
    - 基于持续时间过滤后的事件
    - 根据事件所在时间区间的电价进行分析
    - 比较是否有更低价格的时间区间可供迁移
    - 只针对is_reschedulable为True的事件进行筛选
    - 添加价格相关列：price_level_profile, primary_price_level, start_price_level, end_price_level, optimization_potential
    - 生成最终的电价掩码文件
    """
    print("💰 步骤4: 应用电价掩码...")
    
    # 根据模式选择相应的电价方案
    if test_mode:
        # 测试模式：处理 TOU_D 和 Germany_Variable
        tariff_configs = [
            ("TOU_D", "./config/TOU_D.json"),
            ("Germany_Variable", "./config/Germany_Variable.json")
        ]
        print("🧪 测试模式：处理 TOU_D 和 Germany_Variable 电价方案")
    else:
        # 主流程模式：只处理 Economy_7 和 Economy_10
        tariff_configs = [
            ("Economy_7", "./config/tariff_config.json"),
            ("Economy_10", "./config/tariff_config.json")
        ]
        print("🏠 主流程模式：处理 Economy_7 和 Economy_10 电价方案")
    
    output_files = []
    
    for tariff_name, config_path in tariff_configs:
        if not os.path.exists(config_path):
            print(f"⚠️ Config file not found: {config_path}, skipping {tariff_name}")
            continue
            
        print(f"\n🔄 Processing {tariff_name} tariff...")
        
        # 为新的区间电价创建专门的输出目录
        if tariff_name in ["TOU_D", "Germany_Variable"]:
            output_dir = f"./output/04_user_constraints/{tariff_name}/"
        else:
            output_dir = "./output/04_user_constraints/"
        
        # 强制重新生成：删除旧的输出文件
        expected_output_path = os.path.join(output_dir, f"shiftable_event_masked_{tariff_name}.csv")
        if os.path.exists(expected_output_path):
            os.remove(expected_output_path)
            print(f"🗑️  删除旧文件: {os.path.basename(expected_output_path)}")
            
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 调用核心过滤函数
            final_path = process_and_mask_events(
                event_csv_path=INTERMEDIATE_PATH,
                constraint_json_path=CONSTRAINT_PATH,
                tariff_name=tariff_name,
                tariff_config_path=config_path,
                output_dir=output_dir
            )
            
            print(f"✅ 重新生成文件: {os.path.basename(final_path)}")
            output_files.append(final_path)
            
            # 读取并显示统计信息
            df_tariff = pd.read_csv(final_path)
            print_event_statistics(df_tariff, f"After {tariff_name} tariff filtering")
            
            # 显示价格优化统计
            reschedulable_events = df_tariff[df_tariff['is_reschedulable'] == True]
            if len(reschedulable_events) > 0:
                avg_optimization_potential = reschedulable_events['optimization_potential'].mean()
                print(f"   平均优化潜力: {avg_optimization_potential:.2f}")
            
        except Exception as e:
            print(f"❌ Error processing {tariff_name}: {e}")
    
    print(f"\n✅ 电价掩码应用完成，生成了 {len(output_files)} 个文件")
    return output_files

def filter_events_by_constraints_and_tariff(user_instruction: str = None, test_mode: bool = False):
    """
    对外主函数：执行完整约束分析与事件筛选流程

    完整流程：
    1. 加载事件数据和电器信息
    2. 生成默认约束（基于电器列表）
    3. 解析用户指令并修订约束（LLM解析）
    4. 按最小持续时间过滤事件
    5. 应用电价掩码进行价格优化分析

    Args:
        user_instruction: 用户约束指令（自然语言）
        test_mode: False=主流程模式(Economy_7&Economy_10), True=测试模式(TOU_D&Germany_Variable)

    Returns:
        dict: 包含处理状态、模式、输出文件等信息的结果字典
    """
    print("🔄 开始约束分析与事件筛选流程...")
    print("="*80)

    # 如果没有提供用户指令，使用默认指令
    if user_instruction is None:
        user_instruction = (
            "For Washing Machine, Tumble Dryer, and Dishwasher:\n"
            "- Replace the default forbidden operating time with 23:30 to 06:00 (next day);\n"
            "- Set latest_finish to 14:00 of the next day (i.e., 38:00);\n"
            "- Ignore all events shorter than 5 minutes.\n"
            "Keep all other appliances with default scheduling rules."
        )

    # 执行完整流程
    try:
        # 步骤1: 生成默认约束
        if not step1_generate_default_constraints_wrapper():
            return {"status": "failed", "error": "Failed to generate default constraints"}

        # 步骤2: 根据用户指令修订约束
        llm_success = step2_revise_constraints_by_instruction(user_instruction)

        # 步骤3: 按最小持续时间过滤事件
        if not step3_filter_by_min_duration():
            return {"status": "failed", "error": "Failed to filter events by duration"}

        # 步骤4: 应用电价掩码
        output_files = step4_apply_tariff_masks(test_mode=test_mode)

        # 构建返回结果
        result = {
            "status": "success",
            "mode": "test_mode" if test_mode else "main_mode",
            "processed_tariffs": ["TOU_D", "Germany_Variable"] if test_mode else ["Economy_7", "Economy_10"],
            "output_files": output_files,
            "llm_parsing_success": llm_success,
            "user_instruction_applied": user_instruction is not None,
            "intermediate_files": {
                "constraints": CONSTRAINT_PATH,
                "filtered_events": INTERMEDIATE_PATH
            }
        }

        print("\n✅ 约束分析与事件筛选流程完成！")

        return result

    except Exception as e:
        error_msg = f"流程执行失败: {str(e)}"
        print(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}

def activate_test_mode_tariffs(user_instruction: str = None):
    """
    激活测试模式电价方案 (TOU_D & Germany_Variable)

    这个函数专门用于处理测试模式的电价方案，确保：
    1. 结果文件存储在正确的子目录中
    2. 为后续的费用计算提供正确的文件路径
    3. 与主流程模式完全分离

    Args:
        user_instruction: 用户约束指令

    Returns:
        dict: 测试模式处理结果
    """
    print("🧪 激活测试模式电价方案 (TOU_D & Germany_Variable)")
    print("="*80)

    result = filter_events_by_constraints_and_tariff(
        user_instruction=user_instruction,
        test_mode=True
    )

    if result["status"] == "success":
        print("\n📁 测试模式文件存储位置:")
        for file_path in result["output_files"]:
            print(f"   {file_path}")

        # 验证文件是否在正确的子目录中
        expected_dirs = ["TOU_D", "Germany_Variable"]
        for expected_dir in expected_dirs:
            expected_file = f"./output/04_user_constraints/{expected_dir}/shiftable_event_masked_{expected_dir}.csv"
            if os.path.exists(expected_file):
                print(f"✅ {expected_dir} 文件已正确存储")
            else:
                print(f"⚠️  {expected_dir} 文件未找到: {expected_file}")

    return result

if __name__ == "__main__":
    # 测试主流程模式
    print("🧪 测试 test_func_5_int.py 主流程模式")
    result = filter_events_by_constraints_and_tariff(test_mode=False)
    print("\n📋 主流程模式结果:")
    print(f"   状态: {result['status']}")
    print(f"   处理的电价方案: {result['processed_tariffs']}")
    print(f"   输出文件数: {len(result['output_files'])}")

    print("\n" + "="*50)

    # 测试测试模式
    print("🧪 测试测试模式")
    test_result = activate_test_mode_tariffs()
    print("\n📋 测试模式结果:")
    print(f"   状态: {test_result['status']}")
    print(f"   处理的电价方案: {test_result['processed_tariffs']}")
    print(f"   输出文件数: {len(test_result['output_files'])}")
