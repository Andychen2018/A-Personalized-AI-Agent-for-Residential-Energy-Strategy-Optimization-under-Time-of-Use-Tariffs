import re
import os
import json
import pandas as pd
from typing import Dict, Tuple
from tools.llm_proxy import GPTProxyClient

# 路径配置
SHIFT_DICT_PATH = "./config/appliance_shiftability_dict.json"
THRESHOLD_DICT_PATH = "./config/device_threshold_dict.json"
OUTPUT_PATH = "./output/02_behavior_modeling/02_1_appliance_shiftable_label.csv"

# 1. 加载 shiftability 词典
def load_shiftable_dict(json_path: str) -> Dict[str, Dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 2. 加载设备默认阈值字典
def load_threshold_dict(json_path: str) -> Dict[str, Dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 3. 从用户输入中通过 LLM 提取 Appliance1~9 名称映射（中文）
def extract_appliance_names_via_llm(user_text: str, llm_client: GPTProxyClient) -> Dict[str, str]:
    prompt = f"""
You are a professional assistant. Extract the appliance names for Appliance1 to Appliance9 from the user's household appliance description.
Number them in order of appearance as Appliance1 ~ Appliance9.

Important requirements:
1. Only return valid JSON format
2. Do not add any explanation or other text
3. JSON must be valid, and keys must use double quotes
4. JSON content must start with ```json and end with ```

Return format example:
```json
{{"Appliance1": "Refrigerator", "Appliance2": "Washing Machine", "Appliance3": "Air Conditioner"}}
```

User input description:
{user_text}

Please strictly follow the above requirements and return JSON：
"""

    response = llm_client.chat([
        {"role": "system", "content": "You are an assistant skilled at extracting appliance number mappings from descriptions."},
        {"role": "user", "content": prompt}
    ])
    # 提取 markdown 格式的 json
    json_str = response['content'].strip("```json")
    try:
        mapping = json.loads(json_str)
        return {k: v for k, v in mapping.items() if re.match(r"Appliance[1-9]$", k)}
    except Exception as e:
        print("⚠️ Failed to parse LLM response. Raw content:")
        # print("⚠️ LLM 响应解析失败，原始内容：")
        print(response)
        return {}

# 4. 查询 shiftability（优先查本地字典，否则调用 LLM 获取英文名+类型）
def infer_shiftability(name_input: str, shift_dict: Dict[str, Dict], llm_client: GPTProxyClient) -> Tuple[str, str, str]:
    """
    Priority: match shift_dict by English name (key); otherwise match aliases or Chinese name; fallback to LLM if all fail.

    """
    # """
    # 优先用英文名（主键）匹配 shift_dict，否则使用 aliases 和中文名匹配；都失败则 fallback 到 LLM 判断。
    # """
    normalized_input = name_input.strip().lower()

    # 构建查找表： alias / 中文名 / 英文名（主键） → 标准英文名
    name_lookup = {}

    for eng_name, props in shift_dict.items():
        key_eng = eng_name.strip().lower()
        name_lookup[key_eng] = (eng_name, props["shiftability"], "dict")

        # 处理 aliases
        for alias in props.get("aliases", []):
            key_alias = alias.strip().lower()
            if key_alias and key_alias not in name_lookup:
                name_lookup[key_alias] = (eng_name, props["shiftability"], "dict")

        # 处理中文名
        if "chinese_name" in props:
            key_cn = props["chinese_name"].strip().lower()
            if key_cn and key_cn not in name_lookup:
                name_lookup[key_cn] = (eng_name, props["shiftability"], "dict")

    # ✅ 字典匹配成功
    if normalized_input in name_lookup:
        return name_lookup[normalized_input]

    # ❌ fallback to LLM
    print(f"⚠️ No match found in local dictionary. Falling back to LLM to determine shiftability: {name_input}")
    # print(f"⚠️ 未匹配到本地字典，调用 LLM 判断 shiftability: {name_input}")

    prompt = (
        f"Appliance Chinese name: {name_input}.\n"
        "Please determine whether it belongs to one of the following three categories: Shiftable, Non-shiftable, or Base.\n"
        "Also return the English name of the appliance.\n"
        "Important requirements:\n"
        "1. Only return valid JSON format\n"
        "2. Do not add any explanation or other text\n"
        "3. JSON must be valid, and keys must use double quotes\n"
        "4. JSON content must start with ```json and end with ```\n"
        "Return format example:\n"
        "```json\n"
        "{\"english_name\": \"Refrigerator\", \"shiftability\": \"Non-shiftable\"}\n"
        "```\n"
    )

    response = llm_client.chat([
        {"role": "system", "content": "You are an assistant skilled at appliance semantic judgment, able to provide English names and shiftability."},
        {"role": "user", "content": prompt}
    ])

    try:
        json_str = response['content'].strip("```json").strip()
        if not json_str:
            print("⚠️ LLM response content is empty and cannot be parsed.")
            # print("⚠️ LLM 响应内容为空，无法解析。")
            return "Unknown", "Unknown", "llm"
        result = json.loads(json_str)
        eng_name = result.get("english_name", "Unknown")
        shift = result.get("shiftability", "Unknown").capitalize()
        if shift not in {"Shiftable", "Non-shiftable", "Base"}:
            shift = "Unknown"
        return eng_name, shift, "llm"
    except Exception as e:
        print("⚠️ Unable to parse LLM response:", response)
        # print("⚠️ 无法解析 LLM 响应：", response)
        return "Unknown", "Unknown", "llm"



# 5. 获取设备的 Pmin, Tmin（支持分类默认值）
def get_threshold_for_device(eng_name: str, shiftability: str, threshold_dict: Dict[str, Dict]) -> Tuple[float, int, str]:
    for key in threshold_dict:
        if key.lower() == eng_name.lower():
            val = threshold_dict[key]
            return val.get("Pmin", 2.0), val.get("Tmin", 1), "dict"

    if shiftability == "Base":
        return 1.0, 5, "base-default"

    return 2.0, 1, "default"

# 6. 主流程函数 - 单个家庭处理
def identify_appliance_shiftability_single(user_text: str, house_id: str, output_dir: str = "./output/02_behavior_modeling/") -> pd.DataFrame:
    """
    Process shiftability identification for a single household

    Args:
        user_text: User description of appliances
        house_id: House identifier (e.g., "house1")
        output_dir: Output directory

    Returns:
        DataFrame with shiftability results
    """
    # Create house-specific output directory
    house_output_dir = os.path.join(output_dir, house_id)
    os.makedirs(house_output_dir, exist_ok=True)

    output_path = os.path.join(house_output_dir, f"02_1_appliance_shiftable_label_{house_id}.csv")

    print(f"🔍 Processing {house_id.upper()} appliance shiftability identification...")
    print("Based on the appliance names provided, I will determine whether their operation periods can be adjusted. This characteristic is called 'Shiftability'. Please wait a moment...")

    llm_client = GPTProxyClient()
    shift_dict = load_shiftable_dict(SHIFT_DICT_PATH)
    threshold_dict = load_threshold_dict(THRESHOLD_DICT_PATH)
    name_map = extract_appliance_names_via_llm(user_text, llm_client)

    results = []
    for aid, name_cn in name_map.items():
        eng_name, shift, source = infer_shiftability(name_cn, shift_dict, llm_client)
        Pmin, Tmin, threshold_source = get_threshold_for_device(eng_name, shift, threshold_dict)

        results.append({
            "ApplianceID": aid,
            "ApplianceName": eng_name,
            "ChineseName": name_cn,
            "Shiftability": shift,
            "Pmin": Pmin,
            "Tmin": Tmin,
            "Source": source,
            "ThresholdSource": threshold_source
        })

    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False)
    print(f"✅ The shiftability label table for {house_id.upper()} has been saved to: {output_path}")
    print(f"Here is the shiftability identification result for {house_id.upper()}:")
    print(df)
    return df


# 7. 批量处理函数
def batch_identify_appliance_shiftability(house_appliances_dict: dict, output_dir: str = "./output/02_behavior_modeling/") -> dict:
    """
    Batch process shiftability identification for multiple households

    Args:
        house_appliances_dict: Dictionary mapping house_id to appliance description
        output_dir: Output directory

    Returns:
        Dictionary mapping house_id to result DataFrame
    """
    results = {}
    failed_houses = []

    print(f"🚀 Starting batch shiftability identification for {len(house_appliances_dict)} households...")
    print("=" * 80)

    for i, (house_id, appliance_text) in enumerate(house_appliances_dict.items(), 1):
        try:
            print(f"\n[{i}/{len(house_appliances_dict)}] Processing {house_id}...")

            df_result = identify_appliance_shiftability_single(
                user_text=appliance_text,
                house_id=house_id,
                output_dir=output_dir
            )

            results[house_id] = df_result
            print(f"✅ {house_id} completed successfully!")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch shiftability identification completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for failed_house in failed_houses:
            print(f"  - {failed_house}")

    return results


# 8. 兼容性函数 - 保持向后兼容
def identify_appliance_shiftability(user_text: str) -> pd.DataFrame:
    """
    Legacy function for backward compatibility
    """
    return identify_appliance_shiftability_single(user_text, "default", "./output/02_behavior_modeling/")
