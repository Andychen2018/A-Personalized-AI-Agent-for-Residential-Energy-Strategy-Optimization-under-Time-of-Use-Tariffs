import os
import pandas as pd
import json


def get_appliance_list_from_csv(csv_path: str = "./output/02_event_segments/02_appliance_event_segments_id.csv"):
    while not os.path.exists(csv_path):
        print(f"⚠️ File not found: {csv_path}")
        csv_path = input("Please enter the CSV file path: ").strip()

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Failed to read the file: {e}")
        return

    required_columns = {"appliance_name", "appliance_ID", "is_reschedulable"}
    if not required_columns.issubset(df.columns):
        print(f"❌ Missing required columns: {required_columns - set(df.columns)}")
        return



    appliance_counts = df["appliance_name"].value_counts()
    appliance_names = appliance_counts.index.tolist()
    appliance_ids = sorted(df["appliance_ID"].unique().tolist())
    id_to_name_df = df.drop_duplicates(subset=["appliance_ID"])[["appliance_ID", "appliance_name"]]
    id_to_name_dict = dict(zip(id_to_name_df["appliance_ID"], id_to_name_df["appliance_name"]))

    dedup_df = df.drop_duplicates(subset=["appliance_ID"])[["appliance_ID", "appliance_name", "is_reschedulable"]]
    shiftable_df = dedup_df[dedup_df["is_reschedulable"] == True]
    non_shiftable_df = dedup_df[dedup_df["is_reschedulable"] == False]

    shiftable_ids = sorted(shiftable_df["appliance_ID"].tolist())
    non_shiftable_ids = sorted(non_shiftable_df["appliance_ID"].tolist())
    shiftable_names = shiftable_df["appliance_name"].tolist()
    non_shiftable_names = non_shiftable_df["appliance_name"].tolist()
    shiftable_map = dict(zip(shiftable_ids, shiftable_names))
    non_shiftable_map = dict(zip(non_shiftable_ids, non_shiftable_names))

    summary_dict = {
        "appliance_names": appliance_names,
        "appliance_counts": appliance_counts.to_dict(),  # ✅ fix: convert Series to dict
        "appliance_ids": appliance_ids,
        "id_to_name": id_to_name_dict,
        "reschedulable_ids": shiftable_ids,
        "reschedulable_names": shiftable_names,
        "non_reschedulable_ids": non_shiftable_ids,
        "non_reschedulable_names": non_shiftable_names,
        "shiftable_map": shiftable_map,
        "non_shiftable_map": non_shiftable_map,
    }

    save_dir = "./output/04_appliance_summary/"
    os.makedirs(save_dir, exist_ok=True)
    with open(os.path.join(save_dir, "appliance_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary_dict, f, indent=2, ensure_ascii=False)

    with open(os.path.join(save_dir, "shiftable_map.json"), "w", encoding="utf-8") as f:
        json.dump(shiftable_map, f, indent=2, ensure_ascii=False)

    return summary_dict





