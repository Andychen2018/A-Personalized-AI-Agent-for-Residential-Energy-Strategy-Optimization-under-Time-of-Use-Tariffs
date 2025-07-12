import pandas as pd
import json
import os

def process_event_data(
    original_events_path: str = './output/02_event_segments/02_appliance_event_segments_id.csv',
    economy_7_resolved_path: str = './output/05_scheduling/heuristic_Economy_7_resolved.csv',
    economy_10_resolved_path: str = './output/05_scheduling/heuristic_Economy_10_resolved.csv',
    appliance_summary_path: str = './output/04_appliance_summary/appliance_summary.json',
    output_dir: str = './output/06_tariff/'
):
    """
    Process event data based on given CSV and JSON files, generating non-shifted and shifted event files.
    All file paths have default values relative to the current working directory.

    Args:
        original_events_path (str): Path to original event CSV file.
        economy_7_resolved_path (str): Path to Economy 7 resolved event CSV file.
        economy_10_resolved_path (str): Path to Economy 10 resolved event CSV file.
        appliance_summary_path (str): Path to appliance summary JSON file containing id_to_name mapping.
        output_dir (str): Directory for saving output files.
    """

    os.makedirs(output_dir, exist_ok=True)

    try:
        print("Loading data files...")
        original_events_df = pd.read_csv(original_events_path)
        economy_7_df = pd.read_csv(economy_7_resolved_path)
        economy_10_df = pd.read_csv(economy_10_resolved_path)

        with open(appliance_summary_path, 'r') as f:
            appliance_summary = json.load(f)
        id_to_name_map = appliance_summary.get('id_to_name', {})
        name_to_id_map = {v: k for k, v in id_to_name_map.items()}
        print("All data files loaded successfully.")

    except FileNotFoundError as e:
        print(f"Error: File not found. Please check the file path. {e}")
        return
    except Exception as e:
        print(f"An error occurred while loading data: {e}")
        return

    print("\nGenerating Non_shifted_event files...")
    event_ids_to_remove_7 = economy_7_df['event_id'].unique()
    event_ids_to_remove_10 = economy_10_df['event_id'].unique()

    non_shifted_economy_7_df = original_events_df.copy()
    print("Original rows:", len(non_shifted_economy_7_df))
    non_shifted_economy_10_df = original_events_df.copy()
    print("Original rows:", len(non_shifted_economy_10_df))

    non_shifted_economy_7_df = non_shifted_economy_7_df[
        ~non_shifted_economy_7_df['event_id'].isin(event_ids_to_remove_7)
    ]
    print("Remaining after removing Economy 7 events:", len(non_shifted_economy_7_df))

    non_shifted_economy_10_df = non_shifted_economy_10_df[
        ~non_shifted_economy_10_df['event_id'].isin(event_ids_to_remove_10)
    ]
    print("Remaining after removing Economy 10 events:", len(non_shifted_economy_10_df))

    non_shifted_economy_7_df.to_csv(os.path.join(output_dir, 'Non_shifted_event_Economy_7.csv'), index=False)
    non_shifted_economy_10_df.to_csv(os.path.join(output_dir, 'Non_shifted_event_Economy_10.csv'), index=False)

    print(f"Non_shifted_event_Economy_7.csv saved to: {os.path.join(output_dir, 'Non_shifted_event_Economy_7.csv')}")
    print(f"Non_shifted_event_Economy_10.csv saved to: {os.path.join(output_dir, 'Non_shifted_event_Economy_10.csv')}")

    print("\nGenerating Shifted_event files (with appliance_ID)...")

    def get_appliance_id(appliance_name):
        return name_to_id_map.get(appliance_name, None)

    shifted_economy_7_df = economy_7_df.copy()
    shifted_economy_7_df['appliance_ID'] = shifted_economy_7_df['appliance_name'].apply(get_appliance_id)
    cols_7 = shifted_economy_7_df.columns.tolist()
    if 'appliance_name' in cols_7 and 'appliance_ID' in cols_7:
        appliance_name_idx = cols_7.index('appliance_name')
        cols_7.insert(appliance_name_idx + 1, cols_7.pop(cols_7.index('appliance_ID')))
        shifted_economy_7_df = shifted_economy_7_df[cols_7]

    shifted_economy_10_df = economy_10_df.copy()
    shifted_economy_10_df['appliance_ID'] = shifted_economy_10_df['appliance_name'].apply(get_appliance_id)
    cols_10 = shifted_economy_10_df.columns.tolist()
    if 'appliance_name' in cols_10 and 'appliance_ID' in cols_10:
        appliance_name_idx = cols_10.index('appliance_name')
        cols_10.insert(appliance_name_idx + 1, cols_10.pop(cols_10.index('appliance_ID')))
        shifted_economy_10_df = shifted_economy_10_df[cols_10]

    shifted_economy_7_df.to_csv(os.path.join(output_dir, 'Shifted_event_Economy_7.csv'), index=False)
    print(f"Shifted_event_Economy_7 has {len(shifted_economy_7_df)} rows and is saved as Shifted_event_Economy_7.csv")

    print("Preview of first 5 rows of Shifted_event_Economy_7:")
    print(shifted_economy_7_df.head(5))

    shifted_economy_10_df.to_csv(os.path.join(output_dir, 'Shifted_event_Economy_10.csv'), index=False)
    print(f"Shifted_event_Economy_10 has {len(shifted_economy_10_df)} rows and is saved as Shifted_event_Economy_10.csv")

    print("Preview of first 5 rows of Shifted_event_Economy_10:")
    print(shifted_economy_10_df.head(5))

    print(f"Shifted_event_Economy_7.csv saved to: {os.path.join(output_dir, 'Shifted_event_Economy_7.csv')}")
    print(f"Shifted_event_Economy_10.csv saved to: {os.path.join(output_dir, 'Shifted_event_Economy_10.csv')}")

    print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    process_event_data()




































