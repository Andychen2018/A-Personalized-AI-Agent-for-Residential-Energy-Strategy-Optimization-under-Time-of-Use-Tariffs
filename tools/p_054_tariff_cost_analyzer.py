import pandas as pd
import json
import os
from datetime import datetime, time, timedelta

# --- 辅助函数：加载功率数据 ---
def load_power_data(power_data_path: str):
    """
    加载并预处理每分钟功率数据。
    
    Args:
        power_data_path (str): 每分钟功率数据CSV文件的路径。

    Returns:
        pd.DataFrame: 包含功率数据的DataFrame，'Time' 列已设置为 datetime 对象并作为索引。
                      如果加载失败，返回 None。
    """
    try:
        print(f"Loading power data file: {power_data_path}")
        # print(f"正在加载功率数据文件：{power_data_path}")
        power_df = pd.read_csv(power_data_path)
        
        # 确保 'Time' 列是 datetime 对象并设置为索引 (使用大写的 'Time')
        if 'Time' in power_df.columns:
            power_df['Time'] = pd.to_datetime(power_df['Time'])
            power_df = power_df.set_index('Time')
            # 确保索引是按时间排序的，以便高效查询
            power_df = power_df.sort_index()
            print("Power data loaded successfully.")
            # print("功率数据加载成功。")
            return power_df
        else:
            print("Error: Column 'Time' not found in the power data file. Please check the column names.")
            # print("错误：功率数据文件中未找到 'Time' 列。请检查列名。")
            return None
    except FileNotFoundError as e:
        print(f"Error: Power data file not found. Please check the path. {e}")
        # print(f"错误：功率数据文件未找到。请检查路径是否正确。 {e}")
        return None
    except Exception as e:
        print(f"Error occurred while loading power data: {e}")
        # print(f"加载功率数据时发生错误：{e}") # 更具体一些的错误提示
        return None

# --- 辅助函数：获取特定时间的电价 (保持不变) ---
def get_rate_for_time(current_time: datetime, price_plan: dict, plan_type: str) -> float:
    """
    根据时间、电价计划类型和配置获取每分钟的电价。

    Args:
        current_time (datetime): 当前时间点。
        price_plan (dict): 电价计划配置字典。
        plan_type (str): 电价计划类型 ('Standard', 'Economy_7', 'Economy_10')。

    Returns:
        float: 对应时间点对应的电价（$/kWh）。
    """
    plan_config = price_plan.get(plan_type)
    if not plan_config:
        # print(f"警告：未找到电价计划 '{plan_type}' 的配置。将使用默认高费率（0.4）。")
        return 0.4 # 默认一个高费率，以防配置缺失

    if plan_config['type'] == 'flat':
        return plan_config['rate']
    elif plan_config['type'] == 'time_based':
        current_time_obj = current_time.time() # 获取时间部分 (e.g., 13:06:00)
        is_low_rate = False
        for low_period_str in plan_config.get('low_periods', []):
            start_str, end_str = low_period_str
            # 将字符串时间转换为 time 对象
            low_start_time = datetime.strptime(start_str, "%H:%M").time()
            low_end_time = datetime.strptime(end_str, "%H:%M").time()

            # 检查当前时间是否在低费率时段内
            if low_start_time <= low_end_time: # 正常情况，如 01:00 到 06:00
                if low_start_time <= current_time_obj < low_end_time:
                    is_low_rate = True
                    break
            else: # 跨午夜的情况，如 20:00 到 02:00
                if current_time_obj >= low_start_time or current_time_obj < low_end_time:
                    is_low_rate = True
                    break
        
        if is_low_rate:
            return plan_config['low_rate']
        else:
            return plan_config['high_rate']
    return 0.0 # 默认值，以防未知类型

# --- 核心费用计算函数 (保持不变) ---
def calculate_cost_from_power_series(
    power_values_series: pd.Series, 
    start_time_for_rate_lookup: str, 
    price_plan: dict,
    plan_type: str
) -> float:
    """
    根据给定的功率序列和查找费率的时间段计算总费用。

    Args:
        power_values_series (pd.Series): 该事件每分钟的功率值序列（例如，原始事件的功率）。
        start_time_for_rate_lookup (str): 用于确定费率的开始时间字符串（通常是迁移后的开始时间）。
        price_plan (dict): 电价计划配置字典。
        plan_type (str): 电价计划类型 ('Standard', 'Economy_7', 'Economy_10')。

    Returns:
        float: 该时间段的总费用。
    """
    total_cost = 0.0
    
    current_rate_lookup_time = pd.to_datetime(start_time_for_rate_lookup)

    for power_at_minute in power_values_series:
        try:
            power_at_minute = float(power_at_minute) if power_at_minute is not None else 0.0
        except (ValueError, TypeError):
            power_at_minute = 0.0 

        if power_at_minute > 0: 
            power_kw = power_at_minute / 1000.0 
            rate = get_rate_for_time(current_rate_lookup_time, price_plan, plan_type) 

            minute_cost = rate * power_kw * (1/60) 
            total_cost += minute_cost
        
        current_rate_lookup_time += pd.Timedelta(minutes=1) 

    return total_cost

# --- 统计分析函数 (调整 total_costs 结构) ---
def analyze_costs(
    non_shifted_e7_df: pd.DataFrame,
    non_shifted_e10_df: pd.DataFrame,
    shifted_e7_df: pd.DataFrame,
    shifted_e10_df: pd.DataFrame
) -> dict:
    """
    对计算后的费用数据进行统计分析。

    Args:
        non_shifted_e7_df (pd.DataFrame): 非迁移Economy_7事件的DataFrame。
        non_shifted_e10_df (pd.DataFrame): 非迁移Economy_10事件的DataFrame。
        shifted_e7_df (pd.DataFrame): 迁移Economy_7事件的DataFrame。
        shifted_e10_df (pd.DataFrame): 迁移Economy_10事件的DataFrame。

    Returns:
        dict: 包含所有统计结果的字典。
    """
    analysis_results = {}

    # 1. Economy_7 和 Economy_10 在事件迁移前后的总花费 (修正逻辑，增加 overall_cost_before_migration 和 overall_cost_after_migration)
    print("\n--- Generating total cost summary ---")

    # print("\n--- 正在生成总花费统计 ---")
    total_costs = {
        "Economy_7": {
            "Non_shifted_total_cost": non_shifted_e7_df['cost'].sum() if 'cost' in non_shifted_e7_df.columns else 0.0,
            "Shifted_original_total_cost": shifted_e7_df['original_cost'].sum() if 'original_cost' in shifted_e7_df.columns else 0.0,
            "Shifted_after_migration_total_cost": shifted_e7_df['shifted_cost'].sum() if 'shifted_cost' in shifted_e7_df.columns else 0.0,
        },
        "Economy_10": {
            "Non_shifted_total_cost": non_shifted_e10_df['cost'].sum() if 'cost' in non_shifted_e10_df.columns else 0.0,
            "Shifted_original_total_cost": shifted_e10_df['original_cost'].sum() if 'original_cost' in shifted_e10_df.columns else 0.0,
            "Shifted_after_migration_total_cost": shifted_e10_df['shifted_cost'].sum() if 'shifted_cost' in shifted_e10_df.columns else 0.0,
        }
    }
    
    # 计算并添加 overall_cost_before_migration 和 overall_cost_after_migration
    # Economy_7
    e7_non_shifted_cost = total_costs["Economy_7"]["Non_shifted_total_cost"]
    e7_shifted_original_cost = total_costs["Economy_7"]["Shifted_original_total_cost"]
    e7_shifted_after_migration_cost = total_costs["Economy_7"]["Shifted_after_migration_total_cost"]

    total_costs["Economy_7"]["overall_cost_before_migration"] = e7_non_shifted_cost + e7_shifted_original_cost
    total_costs["Economy_7"]["overall_cost_after_migration"] = e7_non_shifted_cost + e7_shifted_after_migration_cost

    # Economy_10
    e10_non_shifted_cost = total_costs["Economy_10"]["Non_shifted_total_cost"]
    e10_shifted_original_cost = total_costs["Economy_10"]["Shifted_original_total_cost"]
    e10_shifted_after_migration_cost = total_costs["Economy_10"]["Shifted_after_migration_total_cost"]

    total_costs["Economy_10"]["overall_cost_before_migration"] = e10_non_shifted_cost + e10_shifted_original_cost
    total_costs["Economy_10"]["overall_cost_after_migration"] = e10_non_shifted_cost + e10_shifted_after_migration_cost

    analysis_results["total_costs"] = total_costs
    print("Total cost summary completed.")
    # print("总花费统计完成。")

    # 2. Economy_7 和 Economy_10 在事件迁移前后各个电器的总花费 (保持不变)
    print("\n--- Generating appliance-level cost summary ---")
    # print("\n--- 正在生成按电器划分的总花费统计 ---")
    appliance_costs = {
        "Economy_7": {
            "Non_shifted": non_shifted_e7_df.groupby('appliance_ID')['cost'].sum().to_dict() if 'cost' in non_shifted_e7_df.columns else {},
            "Shifted_original": shifted_e7_df.groupby('appliance_ID')['original_cost'].sum().to_dict() if 'original_cost' in shifted_e7_df.columns else {},
            "Shifted_after_migration": shifted_e7_df.groupby('appliance_ID')['shifted_cost'].sum().to_dict() if 'shifted_cost' in shifted_e7_df.columns else {},
        },
        "Economy_10": {
            "Non_shifted": non_shifted_e10_df.groupby('appliance_ID')['cost'].sum().to_dict() if 'cost' in non_shifted_e10_df.columns else {},
            "Shifted_original": shifted_e10_df.groupby('appliance_ID')['original_cost'].sum().to_dict() if 'original_cost' in shifted_e10_df.columns else {},
            "Shifted_after_migration": shifted_e10_df.groupby('appliance_ID')['shifted_cost'].sum().to_dict() if 'shifted_cost' in shifted_e10_df.columns else {},
        }
    }
    analysis_results["appliance_costs"] = appliance_costs
    print("Appliance-level cost summary completed.")
    # print("按电器划分的总花费统计完成。")

    # 3. Economy_7 和 Economy_10 在事件迁移前后按照月份统计，每个月前后的总花费 (保持不变)
    print("\n--- Generating monthly cost summary ---")
    # print("\n--- 正在生成按月份划分的总花费统计 ---")
    monthly_costs = {
        "Economy_7": {},
        "Economy_10": {}
    }

    # Helper to process monthly data for a given DataFrame
    def process_monthly_data(df, start_col, cost_col): 
        if cost_col not in df.columns or df.empty: 
            return {}
        
        df_copy = df.copy() 
        df_copy[start_col] = pd.to_datetime(df_copy[start_col])
        df_copy['month'] = df_copy[start_col].dt.to_period('M') 
        
        monthly_sum = df_copy.groupby('month')[cost_col].sum().to_dict()
        return {str(k): v for k, v in monthly_sum.items()}

    # Economy_7 Monthly Costs
    monthly_costs["Economy_7"]["Non_shifted"] = process_monthly_data(
        non_shifted_e7_df, 'start_time', 'cost'
    )
    monthly_costs["Economy_7"]["Shifted_original"] = process_monthly_data(
        shifted_e7_df, 'original_start_time', 'original_cost'
    )
    monthly_costs["Economy_7"]["Shifted_after_migration"] = process_monthly_data(
        shifted_e7_df, 'shifted_start_datetime', 'shifted_cost'
    )

    # Economy_10 Monthly Costs
    monthly_costs["Economy_10"]["Non_shifted"] = process_monthly_data(
        non_shifted_e10_df, 'start_time', 'cost'
    )
    monthly_costs["Economy_10"]["Shifted_original"] = process_monthly_data(
        shifted_e10_df, 'original_start_time', 'original_cost'
    )
    monthly_costs["Economy_10"]["Shifted_after_migration"] = process_monthly_data(
        shifted_e10_df, 'shifted_start_datetime', 'shifted_cost'
    )
    analysis_results["monthly_costs"] = monthly_costs
    print("Monthly cost summary completed.")
    # print("按月份划分的总花费统计完成。")
    
    return analysis_results

# --- 主处理函数：计算所有事件文件的费用 ---
def calculate_all_event_costs(
    power_data_path: str = './output/01_preprocessed/01_perception_alignment_result.csv',
    price_plan_path: str = './config/tariff_config.json',
    non_shifted_e7_path: str = './output/06_tariff/Non_shifted_event_Economy_7.csv',
    non_shifted_e10_path: str = './output/06_tariff/Non_shifted_event_Economy_10.csv',
    shifted_e7_path: str = './output/06_tariff/Shifted_event_Economy_7.csv',
    shifted_e10_path: str = './output/06_tariff/Shifted_event_Economy_10.csv',
    output_dir_for_costs: str = './output/07_cost_analysis/' 
):
    """
    加载所有事件文件，计算其费用，并将包含费用列的DataFrame保存到新的CSV文件。

    Args:
        power_data_path (str): 每分钟功率数据CSV文件的路径。
        price_plan_path (str): 电价配置文件JSON的路径。
        non_shifted_e7_path (str): Non_shifted_event_Economy_7.csv 文件的路径。
        non_shifted_e10_path (str): Non_shifted_event_Economy_10.csv 文件的路径。
        shifted_e7_path (str): Shifted_event_Economy_7.csv 文件的路径。
        shifted_e10_path (str): Shifted_event_Economy_10.csv 文件的路径。
        output_dir_for_costs (str): 保存输出费用CSV文件的目录。

    Returns:
        tuple: (non_shifted_e7_df, non_shifted_e10_df, shifted_e7_df, shifted_e10_df)
               返回处理后的DataFrames，以便后续进行统计分析。
    """
    
    os.makedirs(output_dir_for_costs, exist_ok=True) 
    print("--- Loading shared data ---")    
    # print("--- 正在加载共享数据 ---")
    try:
        power_data_df = load_power_data(power_data_path)
        if power_data_df is None:
            print("❌ Failed to load power data. Terminating cost calculation.")
            # print("功率数据加载失败，终止费用计算。")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        with open(price_plan_path, 'r') as f:
            price_plan = json.load(f)
        print("✅ Tariff configuration loaded successfully.")
        # print("电价计划加载成功。")
    except FileNotFoundError as e:
        print(f"❌ File not found while loading shared data. Please check the file path. {e}")
        # print(f"错误：加载共享文件时未找到。请检查文件路径是否正确。 {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        print(f"❌ Error occurred while loading shared data: {e}")
        # print(f"加载共享数据时发生错误：{e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    processed_non_shifted_e7_df = pd.DataFrame()
    processed_non_shifted_e10_df = pd.DataFrame()
    processed_shifted_e7_df = pd.DataFrame()
    processed_shifted_e10_df = pd.DataFrame()

    # print("\n--- 处理 Non_shifted_event 文件 ---")
    print("\n--- Processing Non_shifted_event files ---")
    for file_path, plan_type in [
        (non_shifted_e7_path, 'Economy_7'),
        (non_shifted_e10_path, 'Economy_10')
    ]:
        try:
            # print(f"正在处理 {os.path.basename(file_path)}...")
            print(f"Processing {os.path.basename(file_path)}...")
            df = pd.read_csv(file_path)
            
            required_cols = ['appliance_ID', 'start_time', 'end_time']
            if not all(col in df.columns for col in required_cols):
                missing_cols = [col for col in required_cols if col not in df.columns]
                # print(f"错误：文件 {os.path.basename(file_path)} 缺少关键列：{', '.join(missing_cols)}。无法计算费用。")
                print(f"❌ Error: File {os.path.basename(file_path)} is missing required columns: {', '.join(missing_cols)}. Unable to calculate cost.")
                if plan_type == 'Economy_7':
                    processed_non_shifted_e7_df = pd.DataFrame()
                else:
                    processed_non_shifted_e10_df = pd.DataFrame()
                continue

            df['cost'] = df.apply(
                lambda row: calculate_cost_from_power_series(
                    power_data_df.loc[pd.to_datetime(row['start_time']):pd.to_datetime(row['end_time']) - pd.Timedelta(minutes=1), row['appliance_ID']],
                    row['start_time'], 
                    price_plan, plan_type
                ) if row['appliance_ID'] in power_data_df.columns else 0.0, 
                axis=1
            )
            
            output_file = os.path.join(output_dir_for_costs, os.path.basename(file_path)) 
            df.to_csv(output_file, index=False)
            print(f"{len(df)} rows of data have been calculated and saved to: {output_file}")
            print(f"Displaying the first 5 rows of {os.path.basename(file_path)} for verification:")
            print(df.head(5))
            # print(f"{len(df)} 行数据已计算费用，并保存到：{output_file}")
            # print(f"显示 {os.path.basename(file_path)} 前5行数据以验证：")
            # print(df.head(5))

            if plan_type == 'Economy_7':
                processed_non_shifted_e7_df = df
            else:
                processed_non_shifted_e10_df = df

        except FileNotFoundError:
            print(f"Warning: File {os.path.basename(file_path)} not found, skipping processing.")
            # print(f"警告：文件 {os.path.basename(file_path)} 未找到，跳过处理。")
        except KeyError as e:
            # print(f"错误：处理 {os.path.basename(file_path)} 时缺少关键列 {e}。请检查文件内容。")
            print(f"Error: Missing key column {e} when processing {os.path.basename(file_path)}. Please check the file content.")
            if plan_type == 'Economy_7':
                processed_non_shifted_e7_df = pd.DataFrame()
            else:
                processed_non_shifted_e10_df = pd.DataFrame()
        except Exception as e:
            # print(f"处理 {os.path.basename(file_path)} 时发生错误：{e}")
            print(f"An error occurred while processing {os.path.basename(file_path)}: {e}")
            if plan_type == 'Economy_7':
                processed_non_shifted_e7_df = pd.DataFrame()
            else:
                processed_non_shifted_e10_df = pd.DataFrame()


    # print("\n--- 处理 Shifted_event 文件 ---")
    print("\n--- Processing Shifted_event files ---")
    for file_path, plan_type in [
        (shifted_e7_path, 'Economy_7'),
        (shifted_e10_path, 'Economy_10')
    ]:
        try:
            # print(f"正在处理 {os.path.basename(file_path)}...")
            print(f"Processing {os.path.basename(file_path)}...")
            df = pd.read_csv(file_path)

            required_cols = ['appliance_ID', 'original_start_time', 'original_end_time', 
                             'shifted_start_datetime', 'shifted_end_datetime']
            if not all(col in df.columns for col in required_cols):
                missing_cols = [col for col in required_cols if col not in df.columns]
                print(f"Error: File {os.path.basename(file_path)} is missing required columns: {', '.join(missing_cols)}. Cannot calculate cost.")
                # print(f"错误：文件 {os.path.basename(file_path)} 缺少关键列：{', '.join(missing_cols)}。无法计算费用。")
                if plan_type == 'Economy_7':
                    processed_shifted_e7_df = pd.DataFrame()
                else:
                    processed_shifted_e10_df = pd.DataFrame()
                continue
            
            def get_original_power_series(row):
                appliance_id = row['appliance_ID']
                original_start_dt = pd.to_datetime(row['original_start_time'])
                original_end_dt = pd.to_datetime(row['original_end_time'])
                
                if appliance_id not in power_data_df.columns:
                    return pd.Series([0.0]) 
                
                power_series = power_data_df.loc[original_start_dt : original_end_dt - pd.Timedelta(minutes=1), appliance_id]
                
                if power_series.empty:
                    duration_minutes = int((original_end_dt - original_start_dt).total_seconds() / 60)
                    return pd.Series([0.0] * max(1, duration_minutes)) 
                return power_series.astype(float) 


            df['original_cost'] = df.apply(
                lambda row: calculate_cost_from_power_series(
                    get_original_power_series(row),
                    row['original_start_time'], 
                    price_plan, plan_type
                ), axis=1
            )

            df['shifted_cost'] = df.apply(
                lambda row: calculate_cost_from_power_series(
                    get_original_power_series(row), 
                    row['shifted_start_datetime'], 
                    price_plan, plan_type
                ), axis=1
            )
            
            output_file = os.path.join(output_dir_for_costs, os.path.basename(file_path)) 
            df.to_csv(output_file, index=False)
            # print(f"{len(df)} 行数据已计算原始费用和迁移后费用，并保存到：{output_file}")
            # print(f"显示 {os.path.basename(file_path)} 前5行数据以验证：")
            print(f"{len(df)} rows of data have been calculated for original and shifted costs and saved to: {output_file}")
            print(f"Displaying the first 5 rows of {os.path.basename(file_path)} for verification:")        
            print(df.head(5))

            if plan_type == 'Economy_7':
                processed_shifted_e7_df = df
            else:
                processed_shifted_e10_df = df

        except FileNotFoundError:
            print(f"⚠️ File not found: {os.path.basename(file_path)}, skipping processing.")
            # print(f"警告：文件 {os.path.basename(file_path)} 未找到，跳过处理。")
        except KeyError as e:
            print(f"❌ Error: Missing required column {e} while processing {os.path.basename(file_path)}. Please check the file content.")
            # print(f"错误：处理 {os.path.basename(file_path)} 时缺少关键列 {e}。请检查文件内容。")
            if plan_type == 'Economy_7':
                processed_shifted_e7_df = pd.DataFrame()
            else:
                processed_shifted_e10_df = pd.DataFrame()
        except Exception as e:
            print(f"❌ An error occurred while processing {os.path.basename(file_path)}: {e}")
            # print(f"处理 {os.path.basename(file_path)} 时发生错误：{e}")
            if plan_type == 'Economy_7':
                processed_shifted_e7_df = pd.DataFrame()
            else:
                processed_shifted_e10_df = pd.DataFrame()


    # print("\n所有费用计算任务已成功完成！")
    print("\n✅ All cost calculation tasks have been successfully completed!")
    return processed_non_shifted_e7_df, processed_non_shifted_e10_df, \
           processed_shifted_e7_df, processed_shifted_e10_df

def process():
    POWER_DATA_PATH = './output/01_preprocessed/01_perception_alignment_result.csv'
    PRICE_PLAN_PATH = './config/tariff_config.json' 
    NON_SHIFTED_E7_INPUT_PATH = './output/06_tariff/Non_shifted_event_Economy_7.csv' 
    NON_SHIFTED_E10_INPUT_PATH = './output/06_tariff/Non_shifted_event_Economy_10.csv' 
    SHIFTED_E7_INPUT_PATH = './output/06_tariff/Shifted_event_Economy_7.csv' 
    SHIFTED_E10_INPUT_PATH = './output/06_tariff/Shifted_event_Economy_10.csv' 
    
    COST_OUTPUT_DIRECTORY = './output/07_cost_analysis/'

    non_shifted_e7, non_shifted_e10, shifted_e7, shifted_e10 = calculate_all_event_costs(
        power_data_path=POWER_DATA_PATH,
        price_plan_path=PRICE_PLAN_PATH,
        non_shifted_e7_path=NON_SHIFTED_E7_INPUT_PATH,
        non_shifted_e10_path=NON_SHIFTED_E10_INPUT_PATH,
        shifted_e7_path=SHIFTED_E7_INPUT_PATH,
        shifted_e10_path=SHIFTED_E10_INPUT_PATH,
        output_dir_for_costs=COST_OUTPUT_DIRECTORY 
    )

    if not non_shifted_e7.empty or not non_shifted_e10.empty or \
       not shifted_e7.empty or not shifted_e10.empty:
        # print("\n--- 正在进行统计分析 ---")
        print("\n--- Performing statistical analysis ---")
        analysis_results = analyze_costs(
            non_shifted_e7, non_shifted_e10, shifted_e7, shifted_e10
        )

        # 打印只包含 total_costs 和 appliance_costs 的部分
        # print("\n--- 费用统计结果 (控制台输出部分) ---")
        print("\n--- Cost analysis results (console output) ---")
        display_results = {
            "total_costs": analysis_results.get("total_costs", {}),
            "appliance_costs": analysis_results.get("appliance_costs", {})
        }
        print(json.dumps(display_results, indent=4, ensure_ascii=False))
        
        # 保存完整的统计结果到文件
        output_stats_file = os.path.join(COST_OUTPUT_DIRECTORY, 'cost_analysis_summary.json')
        with open(output_stats_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=4, ensure_ascii=False)
        # print(f"\n完整统计结果已保存到：{output_stats_file}")
        print(f"\n✅ Full statistical results saved to: {output_stats_file}")
    else:
        # print("\n跳过统计分析，因为所有DataFrame都为空或未成功处理。")
         print("\n⚠️ Skipping statistical analysis because all DataFrames are empty or failed to process.")



if __name__ == "__main__":
    process()
