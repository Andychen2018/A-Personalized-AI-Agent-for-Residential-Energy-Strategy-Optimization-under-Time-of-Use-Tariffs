import pandas as pd
import os

def add_event_id(
    input_csv: str = "./output/02_event_segments/02_appliance_event_segments.csv",
    output_csv: str = "./output/02_event_segments/02_appliance_event_segments_id.csv"
) -> pd.DataFrame:
    print("Next, we will assign a unique identifier 'event_id' to each detected appliance operation event...")
    
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"❌ Input file not found: {input_csv}")
    
    df = pd.read_csv(input_csv, parse_dates=["start_time", "end_time"])

    # Add date column
    df["date"] = df["start_time"].dt.date.astype(str)

    # Generate cumulative index per (appliance_name, date) group
    df["event_index"] = df.groupby(["appliance_name", "date"]).cumcount() + 1

    # Generate event_id, e.g., Washer_2024-06-01_01
    df["event_id"] = (
        df["appliance_name"].str.replace(" ", "_") + "_" +
        df["date"] + "_" +
        df["event_index"].astype(str).str.zfill(2)
    )

    # Add reschedulable flag
    df["is_reschedulable"] = df["Shiftability"].apply(
        lambda x: True if x.strip().lower() == "shiftable" else False
    )

    # Reorder columns
    df = df[[ 
        "event_id", "appliance_name", "appliance_ID", "Shiftability",
        "start_time", "end_time", "duration(min)", "energy(W)", "is_reschedulable"
    ]]

    # Save result
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"✅ The event log with event_id has been saved to: {output_csv}")
    
    print("Note: Each event_id is a unique identifier that includes appliance name, date, and event index.")
    print("Here are the first 10 rows of the result:")
    print(df.head(10))

    return df







